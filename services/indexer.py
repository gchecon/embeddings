import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from config import settings
from database import postgres, qdrant_client
from services import chunker, embedder, language_detector, pdf_extractor


ProgressCallback = Callable[[str, int, int, str], None]


def index_directory(directory: str, on_progress: ProgressCallback | None = None) -> dict:
    pdf_files = _find_pdfs(directory)
    total = len(pdf_files)
    done = 0
    skipped = 0
    errors = 0

    for pdf_path in pdf_files:
        file_name = Path(pdf_path).name
        try:
            result = _index_file(pdf_path)
            if result == "skipped":
                skipped += 1
            done += 1
        except Exception as exc:
            errors += 1
            done += 1
            if on_progress:
                on_progress(file_name, done, total, f"error: {exc}")
            continue

        if on_progress:
            status = "skipped" if result == "skipped" else "indexed"
            on_progress(file_name, done, total, status)

    return {"total": total, "skipped": skipped, "errors": errors, "indexed": total - skipped - errors}


def _find_pdfs(directory: str) -> list[str]:
    result = []
    for root, _, files in os.walk(directory):
        for f in files:
            if f.lower().endswith(".pdf"):
                result.append(os.path.join(root, f))
    return result


def _index_file(pdf_path: str) -> str:
    file_hash = postgres.compute_file_hash(pdf_path)

    existing = postgres.find_by_hash(file_hash)
    if existing:
        return "skipped"

    extracted = pdf_extractor.extract(pdf_path)
    language = language_detector.detect_language(extracted.full_text)

    with open(pdf_path, "rb") as f:
        pdf_data = f.read()

    original_name = Path(pdf_path).name
    doc_id = postgres.insert_document(
        original_name=original_name,
        file_hash=file_hash,
        file_path=pdf_path,
        language=language,
        page_count=extracted.page_count,
        pdf_data=pdf_data,
    )

    chunks = chunker.chunk_pages(extracted.pages)
    total_chunks = len(chunks)
    timestamp = datetime.now(timezone.utc).isoformat()

    points: list[dict] = []
    texts = [c.text for c in chunks]
    vectors = embedder.embed_passages(texts)

    for idx, (chunk, vector) in enumerate(zip(chunks, vectors)):
        points.append({
            "id": qdrant_client.make_point_id(),
            "vector": vector,
            "payload": {
                "text": chunk.text,
                "embedding_model": settings.EMBEDDING_MODEL,
                "timestamp": timestamp,
                "chunk_index": chunk.chunk_index,
                "total_chunks": total_chunks,
                "original_name": original_name,
                "file_hash": file_hash,
                "file_path": pdf_path,
                "language": language,
                "document_id": doc_id,
                "page_start": chunk.page_start,
                "page_end": chunk.page_end,
                "title": extracted.title,
                "author": extracted.author,
                "year": extracted.year,
            },
        })

    qdrant_client.upsert_points(points)
    return "indexed"
