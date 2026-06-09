import hashlib
import uuid
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

from config import settings


@contextmanager
def get_conn():
    with psycopg.connect(settings.postgres_dsn, row_factory=dict_row) as conn:
        yield conn


def ensure_schema():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                original_name   TEXT NOT NULL,
                file_hash       CHAR(64) NOT NULL UNIQUE,
                file_path       TEXT NOT NULL,
                language        TEXT,
                page_count      INT,
                created_at      TIMESTAMPTZ DEFAULT now(),
                pdf_data        BYTEA NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_hash ON documents(file_hash)")
        conn.commit()


def find_by_hash(file_hash: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, original_name, file_path FROM documents WHERE file_hash = %s",
            (file_hash,),
        ).fetchone()
    return row


def insert_document(
    original_name: str,
    file_hash: str,
    file_path: str,
    language: str,
    page_count: int,
    pdf_data: bytes,
) -> str:
    doc_id = str(uuid.uuid4())
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO documents (id, original_name, file_hash, file_path, language, page_count, pdf_data)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (doc_id, original_name, file_hash, file_path, language, page_count, pdf_data),
        )
        conn.commit()
    return doc_id


def get_pdf_data(doc_id: str) -> bytes | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT pdf_data FROM documents WHERE id = %s",
            (doc_id,),
        ).fetchone()
    return bytes(row["pdf_data"]) if row else None


def delete_by_hash(file_hash: str) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM documents WHERE file_hash = %s", (file_hash,))
        conn.commit()


def compute_file_hash(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
