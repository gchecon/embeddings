# PDF Embedding System — CLAUDE.md

## Visão geral

Sistema web em Flask/Python para indexação semântica de documentos PDF. Extrai texto (incluindo OCR de imagens), armazena os PDFs íntegros no PostgreSQL e os embeddings no Qdrant, com metadados completos. Permite busca semântica por prompt e visualização do PDF original no navegador.

## Stack técnica

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.12+ |
| Gerenciador de pacotes | `uv` |
| Web framework | Flask |
| Banco relacional | PostgreSQL (PDF íntegro + metadados) |
| Banco vetorial | Qdrant |
| Modelo de embeddings | `jinaai/jina-embeddings-v3` via `sentence-transformers` |
| Extração de PDF | `PyMuPDF` (fitz) |
| OCR de imagens | `pytesseract` + Tesseract OCR instalado no sistema |
| Detecção de idioma | `langdetect` |
| Variáveis de ambiente | `python-dotenv` via `config.py` |

## Decisões de arquitetura confirmadas

| Ponto | Decisão |
|---|---|
| OCR engine | `pytesseract` + Tesseract instalado no sistema |
| Seleção de diretório | Campo de texto com caminho absoluto do servidor |
| Abertura de PDF | Na página inicial do chunk via `#page=N` |
| Autenticação | Sem login (uso local) |
| GPU | `device="cuda"` com fallback automático para `cpu` |
| Atualização de arquivo | Reprocessar e substituir se hash diferente |
| Coleção Qdrant | Única: `pdf_embeddings` |
| Infraestrutura | Qdrant via Docker Compose; PostgreSQL externo (credenciais no `.env`) |

---

## Estrutura de diretórios

```
embeddings/
├── .env                    # variáveis de ambiente (não versionar)
├── .env.example            # template do .env
├── docker-compose.yml      # sobe o Qdrant
├── pyproject.toml          # dependências uv
├── CLAUDE.md
├── config.py               # carrega .env e expõe constantes
├── app.py                  # entry point Flask
├── database/
│   ├── postgres.py         # conexão e operações no PostgreSQL
│   ├── qdrant_client.py    # conexão e operações no Qdrant
│   └── schema.sql          # DDL de referência da tabela documents
├── services/
│   ├── pdf_extractor.py    # extração de texto + OCR com PyMuPDF
│   ├── chunker.py          # chunking com overlapping
│   ├── embedder.py         # geração de embeddings com Jina v3
│   ├── indexer.py          # orquestrador: extrai → chunk → embed → persiste
│   └── language_detector.py
├── routes/
│   ├── upload.py           # POST /scan — inicia varredura de diretório
│   ├── search.py           # GET /search — busca semântica
│   ├── pdf_viewer.py       # GET /pdf/<doc_id> — serve PDF do PostgreSQL
│   ├── progress.py         # GET /progress — SSE de progresso
│   └── browse.py           # GET /browse — navegador de diretórios do servidor (para o modal de seleção)
├── templates/
│   ├── base.html
│   ├── index.html          # página principal: seleção de diretório + modal de navegação
│   ├── search.html         # página de busca e resultados
│   └── viewer.html         # página de visualização do PDF
└── static/
    └── js/
        ├── progress.js     # consome SSE e atualiza UI (device, progresso, relatório final)
        └── browse.js       # consome /browse e alimenta o modal de seleção de diretório
```

## Docker Compose (Qdrant apenas)

```yaml
# docker-compose.yml
services:
  qdrant:
    image: qdrant/qdrant:latest
    container_name: qdrant
    ports:
      - "6333:6333"
      - "6334:6334"   # gRPC (opcional)
    volumes:
      - qdrant_data:/qdrant/storage
    restart: unless-stopped

volumes:
  qdrant_data:
```

Subir com:
```bash
docker compose up -d
```

O PostgreSQL é externo e gerenciado de forma independente. Suas credenciais de acesso são configuradas exclusivamente via `.env`.

## Variáveis de ambiente (.env)

```dotenv
# Chunking
CHUNK_SIZE=1000
CHUNK_OVERLAP=200

# PostgreSQL externo — ajustar conforme ambiente
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=pdf_store
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secret
POSTGRES_CONNECT_TIMEOUT=30

# Qdrant (Docker Compose — porta exposta localmente)
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=pdf_embeddings

# Cache do HuggingFace (deixar vazio para usar o padrão ~/.cache/huggingface)
HF_HOME=

# Timeout de download do HuggingFace em segundos (aumentar em redes lentas ou com proxy)
HF_HUB_DOWNLOAD_TIMEOUT=120

# Proxy corporativo para downloads do HuggingFace (deixar vazio se não houver proxy)
HTTP_PROXY=
HTTPS_PROXY=
NO_PROXY=localhost,127.0.0.1

# Modelo de embeddings
EMBEDDING_MODEL=jinaai/jina-embeddings-v3
EMBEDDING_DEVICE=cuda          # ou "cpu"
EMBEDDING_DIM=1024
EMBEDDING_BATCH_SIZE=4
# Threads do PyTorch (0 = todos os núcleos; 2 recomendado para uso em desktop, evita travar a máquina)
TORCH_NUM_THREADS=2
# Pausa em segundos entre arquivos indexados, para aliviar CPU/rede (0 desativa)
INDEXING_PAUSE_SECONDS=0.5

# Flask
FLASK_SECRET_KEY=troque-isto
FLASK_DEBUG=false
```

## config.py

`config.py` é o único lugar que lê o `.env`. Todos os outros módulos importam de `config`, nunca usam `os.environ` diretamente.

```python
# padrão esperado
from config import settings
settings.CHUNK_SIZE      # int
settings.QDRANT_HOST     # str
```

## Schema PostgreSQL

```sql
CREATE TABLE documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    original_name   TEXT NOT NULL,
    file_hash       CHAR(64) NOT NULL UNIQUE,  -- SHA-256
    file_path       TEXT NOT NULL,             -- caminho físico original no disco
    language        TEXT,                      -- código ISO 639-1, ex.: "pt", "en"
    page_count      INT,
    created_at      TIMESTAMPTZ DEFAULT now(),
    pdf_data        BYTEA NOT NULL             -- PDF íntegro para reconstrução
);

CREATE INDEX idx_documents_hash ON documents(file_hash);
```

O campo `pdf_data` armazena o PDF completo em bytes. A rota `/pdf/<doc_id>` lê esse campo e serve com `Content-Type: application/pdf`, permitindo visualização inline e download.

## Schema Qdrant — payload por ponto

Campos obrigatórios do spec do projeto + campos do item 13 do `Docs/Manual.md`:

```python
payload = {
    # --- spec do projeto ---
    "text":             str,   # texto do chunk
    "embedding_model":  str,   # ex.: "jinaai/jina-embeddings-v3"
    "timestamp":        str,   # ISO 8601 UTC do momento do embedding
    "chunk_index":      int,   # número sequencial do chunk (base 0)
    "total_chunks":     int,   # total de chunks do documento
    "original_name":    str,   # nome original do arquivo em disco
    "file_hash":        str,   # SHA-256 do arquivo (64 hex chars)
    "file_path":        str,   # caminho físico original no disco
    "language":         str,   # código ISO 639-1, ex.: "pt", "en"
    # --- ligação com PostgreSQL ---
    "document_id":      str,   # UUID do registro na tabela documents
    # --- metadados de localização no PDF (item 13 do Manual.md) ---
    "page_start":       int,   # página onde o chunk começa (base 1)
    "page_end":         int,   # página onde o chunk termina (base 1)
    # --- metadados do documento (item 13 do Manual.md) ---
    "title":            str,   # título extraído dos metadados do PDF (ou nome do arquivo)
    "author":           str,   # autor extraído dos metadados do PDF (ou "" se ausente)
    "year":             int,   # ano do documento (metadados PDF; fallback: ano de modificação do arquivo)
}
```

O campo `document_id` é a chave de ligação entre Qdrant e PostgreSQL. Os campos `page_start`/`page_end` permitem abrir o PDF diretamente na página correta ao clicar num chunk. `title`, `author` e `year` são extraídos de `fitz.Document.metadata` e permitem filtros e citação nos resultados de busca.

## Fluxo de indexação (`indexer.py`)

```
antes de tudo:
  0. resolver device (embedder.get_device_info(): cuda + nome da GPU, ou cpu) e emitir evento SSE "start"

para cada PDF encontrado no diretório (recursivo):
  1. calcular SHA-256 do arquivo
  2. verificar se hash já existe em documents.file_hash
     → se sim: pular (status "skipped")
     → se não: continuar
  3. extrair texto por página com PyMuPDF
     - texto nativo da página
     - para cada imagem na página: OCR com pytesseract
  4. detectar idioma principal (langdetect sobre texto completo)
  5. salvar PDF íntegro + metadados no PostgreSQL → obtém document_id
  6. aplicar chunking com CHUNK_SIZE e CHUNK_OVERLAP
  7. para cada chunk:
     a. gerar embedding com task="retrieval.passage"
     b. montar payload conforme schema acima
     c. inserir no Qdrant
  8. contar tokens efetivamente enviados ao modelo (embedder.count_tokens) e o tempo gasto no arquivo
  9. emitir evento SSE de progresso (arquivo, status, chunks, tokens, tempo)

ao final:
  10. emitir evento SSE "summary" com totais (indexados/pulados/erros, chunks, tokens, tempo total)
```

## Progresso em tempo real

Usar **Server-Sent Events (SSE)** na rota `GET /progress` com `text/event-stream`. O frontend consome o stream com `EventSource` e atualiza uma barra de progresso. O estado de progresso é mantido em memória (dicionário global ou Redis se escalar).

O callback `ProgressCallback` (`services/indexer.py`) recebe um único `dict` (não argumentos posicionais), repassado por `push_event(event: dict)` em `routes/progress.py`. Tipos de evento emitidos por `index_directory`:

```
# 1x no início, antes de processar qualquer arquivo
data: {"status": "start", "total": 47, "device": "cuda", "gpu_name": "NVIDIA GeForce RTX 3080"}

# 1x por arquivo processado
data: {"file": "relatorio.pdf", "done": 3, "total": 47, "status": "indexed", "elapsed_seconds": 4.21, "chunks": 12, "tokens": 3456}
data: {"file": "outro.pdf", "done": 4, "total": 47, "status": "skipped", "elapsed_seconds": 0.01}
data: {"file": "corrompido.pdf", "done": 5, "total": 47, "status": "error", "error": "...", "elapsed_seconds": 0.3}

# 1x no final, com os totais da indexação (emitido por routes/upload.py a partir do retorno de index_directory)
data: {"status": "summary", "total": 47, "indexed": 40, "skipped": 5, "errors": 2, "total_chunks": 512, "total_tokens": 128000, "total_time_seconds": 312.5, "device": "cuda", "gpu_name": "NVIDIA GeForce RTX 3080"}

# 1x ao encerrar o stream
data: {"status": "done"}
```

## Rota de busca

`GET /search?q=<prompt>&limit=10`

1. Gerar embedding da query com `task="retrieval.query"`
2. Consultar Qdrant com `query_points`, `limit=limit`
3. Retornar lista de chunks ordenados por score, com link para `/pdf/<document_id>?page=<page_number>`

## Visualização do PDF

- Rota `GET /pdf/<document_id>` lê `pdf_data` do PostgreSQL e retorna com `Content-Type: application/pdf` e `Content-Disposition: inline`
- Aceita query param `?page=<n>` — o template `viewer.html` usa um `<iframe>` ou `<embed>` apontando para essa rota; o scroll até a página é feito via fragmento de URL (`#page=<n>`) que o leitor de PDF do navegador interpreta
- O PDF pode ser aberto direto no `<iframe>` (visualização) ou baixado

## Dependências principais (pyproject.toml)

```toml
[project]
name = "pdf-embedding-system"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "flask",
    "python-dotenv",
    "psycopg[binary]",
    "qdrant-client",
    "sentence-transformers",
    "transformers",
    "torch",
    "pymupdf",
    "pytesseract",
    "langdetect",
    "Pillow",
    "einops",       # exigido pelo código remoto (trust_remote_code) do Jina v3
]
```

Instalar com:
```bash
uv sync
```

Rodar a aplicação:
```bash
uv run flask --app app.py run --debug
```

## Convenções de código

- Português nos comentários e docstrings; inglês nos nomes de variáveis, funções e classes
- `config.py` é a única interface com `.env`
- Nenhum módulo importa `os.environ` diretamente
- Hash de arquivo: SHA-256 em hex (64 caracteres)
- Timestamps: sempre UTC, formato ISO 8601
- IDs no Qdrant: UUID v4 string (mesmo `document_id` do PostgreSQL para o primeiro chunk; chunks subsequentes têm UUID próprio)
- Não duplicar código entre `postgres.py` e `qdrant_client.py`; lógica de negócio fica em `services/`

## Modelo de embeddings — notas

- Dimensão padrão: **1024** (não reduzir inicialmente)
- Distância: **COSINE** com `normalize_embeddings=True`
- Tarefa de indexação: `task="retrieval.passage"`
- Tarefa de busca: `task="retrieval.query"`
- O modelo usa `trust_remote_code=True` (obrigatório para Jina v3)
- Não misturar modelos na mesma coleção Qdrant
- Ver `Docs/Manual.md` para referência detalhada do modelo
- `embedder.get_device_info()` expõe o device efetivo (`cuda`/`cpu`) e o nome da GPU (via `torch.cuda.get_device_name`), usado no relatório de indexação
- `embedder.count_tokens()` conta os tokens realmente enviados ao modelo (via `model.tokenize()`, já truncados), usado para o relatório de tokens por documento
- `embedder.py` filtra o warning `` `torch_dtype` is deprecated! Use `dtype` instead! `` dos loggers `transformers.configuration_utils`/`transformers.modeling_utils`. Causa: o `config.json` publicado pelo modelo no Hub usa o campo legado `torch_dtype`, fora do nosso controle — não remover o filtro achando que é warning morto