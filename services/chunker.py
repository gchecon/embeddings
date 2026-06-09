from dataclasses import dataclass

from config import settings
from services.pdf_extractor import PageText


@dataclass
class Chunk:
    text: str
    chunk_index: int
    page_start: int  # base 1
    page_end: int    # base 1


def chunk_pages(pages: list[PageText]) -> list[Chunk]:
    size = settings.CHUNK_SIZE
    overlap = settings.CHUNK_OVERLAP

    # Flatten pages into (char, page_number) pairs
    chars: list[tuple[str, int]] = []
    for page in pages:
        for ch in page.text:
            chars.append((ch, page.page_number))

    chunks: list[Chunk] = []
    start = 0
    index = 0

    while start < len(chars):
        end = min(start + size, len(chars))
        segment = chars[start:end]
        text = "".join(c for c, _ in segment).strip()
        if text:
            page_nums = [p for _, p in segment]
            chunks.append(
                Chunk(
                    text=text,
                    chunk_index=index,
                    page_start=min(page_nums),
                    page_end=max(page_nums),
                )
            )
            index += 1
        start += size - overlap

    return chunks
