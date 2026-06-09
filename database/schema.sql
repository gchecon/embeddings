-- Executar conectado ao banco "postgres" (ou qualquer banco existente)
CREATE DATABASE pdf_store
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.UTF-8'
    LC_CTYPE = 'en_US.UTF-8'
    TEMPLATE = template0;

-- Conectar ao banco criado antes de executar o restante
\c pdf_store

CREATE TABLE IF NOT EXISTS documents (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    original_name TEXT        NOT NULL,
    file_hash     CHAR(64)    NOT NULL UNIQUE,   -- SHA-256
    file_path     TEXT        NOT NULL,
    language      TEXT,
    page_count    INT,
    created_at    TIMESTAMPTZ DEFAULT now(),
    pdf_data      BYTEA       NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_documents_hash ON documents(file_hash);
