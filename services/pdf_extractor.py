from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMuPDF
import pytesseract
from PIL import Image


@dataclass
class PageText:
    page_number: int  # base 1
    text: str


@dataclass
class ExtractedDocument:
    pages: list[PageText] = field(default_factory=list)
    full_text: str = ""
    page_count: int = 0
    title: str = ""
    author: str = ""
    year: int = 0


def extract(pdf_path: str) -> ExtractedDocument:
    doc = fitz.open(pdf_path)
    meta = doc.metadata or {}

    title = meta.get("title") or Path(pdf_path).stem
    author = meta.get("author") or ""
    year = _extract_year(meta, pdf_path)

    pages: list[PageText] = []
    for page in doc:
        text = page.get_text("text") or ""
        text += _ocr_images(page)
        pages.append(PageText(page_number=page.number + 1, text=text.strip()))

    full_text = "\n".join(p.text for p in pages)

    return ExtractedDocument(
        pages=pages,
        full_text=full_text,
        page_count=len(pages),
        title=title,
        author=author,
        year=year,
    )


def _ocr_images(page: fitz.Page) -> str:
    texts: list[str] = []
    for img_info in page.get_images(full=True):
        xref = img_info[0]
        try:
            base_image = page.parent.extract_image(xref)
            img = Image.frombytes(
                "RGB",
                (base_image["width"], base_image["height"]),
                base_image["image"],
                "raw",
                base_image["colorspace"],
            )
            texts.append(pytesseract.image_to_string(img))
        except Exception:
            pass
    return "\n".join(texts)


def _extract_year(meta: dict, pdf_path: str) -> int:
    for key in ("creationDate", "modDate"):
        value = meta.get(key, "")
        if value and len(value) >= 6:
            try:
                # PDF date format: D:YYYYMMDDHHmmSS
                raw = value.lstrip("D:").lstrip("d:")
                return int(raw[:4])
            except (ValueError, IndexError):
                pass
    try:
        return int(Path(pdf_path).stat().st_mtime // (365.25 * 24 * 3600) + 1970)
    except Exception:
        return 0
