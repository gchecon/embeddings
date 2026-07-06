import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from config import settings
from database import postgres, qdrant_client
from services import chunker, embedder, language_detector, pdf_extractor


ProgressCallback = Callable[[dict], None]
CancelCheck = Callable[[], bool]


@dataclass
class FileIndexResult:
    status: str  # "indexed" ou "skipped"
    chunks: int = 0
    tokens: int = 0


def index_directory(
    directory: str,
    on_progress: ProgressCallback | None = None,
    should_cancel: CancelCheck | None = None,
) -> dict:
    pdf_files = _find_pdfs(directory)
    total = len(pdf_files)
    done = 0
    skipped = 0
    errors = 0
    total_chunks = 0
    total_tokens = 0
    cancelled = False

    device_info = embedder.get_device_info()
    started_at = time.perf_counter()

    if on_progress:
        on_progress({
            "status": "start",
            "total": total,
            "device": device_info["device"],
            "gpu_name": device_info["gpu_name"],
        })

    for pdf_path in pdf_files:
        if should_cancel and should_cancel():
            cancelled = True
            break

        file_name = Path(pdf_path).name
        file_started_at = time.perf_counter()
        try:
            result = _index_file(pdf_path)
            done += 1
        except Exception as exc:
            errors += 1
            done += 1
            if on_progress:
                on_progress({
                    "file": file_name,
                    "done": done,
                    "total": total,
                    "status": "error",
                    "error": str(exc),
                    "elapsed_seconds": round(time.perf_counter() - file_started_at, 2),
                })
            continue

        elapsed = round(time.perf_counter() - file_started_at, 2)
        if result.status == "skipped":
            skipped += 1
        else:
            total_chunks += result.chunks
            total_tokens += result.tokens

        if on_progress:
            on_progress({
                "file": file_name,
                "done": done,
                "total": total,
                "status": result.status,
                "elapsed_seconds": elapsed,
                "chunks": result.chunks,
                "tokens": result.tokens,
            })

        # Respiro entre arquivos para não saturar CPU/rede
        if result.status != "skipped":
            time.sleep(settings.INDEXING_PAUSE_SECONDS)

    total_time = round(time.perf_counter() - started_at, 2)

    return {
        "total": total,
        "done": done,
        "skipped": skipped,
        "errors": errors,
        "indexed": done - skipped - errors,
        "total_chunks": total_chunks,
        "total_tokens": total_tokens,
        "total_time_seconds": total_time,
        "device": device_info["device"],
        "gpu_name": device_info["gpu_name"],
        "cancelled": cancelled,
    }


def _find_pdfs(directory: str) -> list[str]:
    result = []
    for root, _, files in os.walk(directory):
        for f in files:
            if f.lower().endswith(".pdf"):
                result.append(os.path.join(root, f))
    return result


def _index_file(pdf_path: str) -> FileIndexResult:
    file_hash = postgres.compute_file_hash(pdf_path)

    existing = postgres.find_by_hash(file_hash)
    if existing:
        return FileIndexResult(status="skipped")

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
    total_tokens = embedder.count_tokens(texts)

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
    return FileIndexResult(status="indexed", chunks=total_chunks, tokens=total_tokens)
