# PDF Embedding System

Sistema web para indexação semântica de documentos PDF. Extrai texto (incluindo OCR de imagens), armazena os PDFs íntegros no PostgreSQL e os embeddings no Qdrant, com busca semântica por linguagem natural e visualização do PDF original diretamente no navegador.

## Funcionalidades

- **Indexação recursiva** — aponta um diretório e todos os PDFs são processados automaticamente
- **OCR integrado** — imagens dentro dos PDFs são lidas via Tesseract
- **Deduplicação por SHA-256** — arquivos já indexados são ignorados; se o conteúdo mudar, são reprocessados
- **Busca semântica** — embedding da query comparado aos chunks via similaridade de cosseno
- **Progresso em tempo real** — barra de progresso via Server-Sent Events (SSE)
- **Visualização no browser** — abre o PDF diretamente na página do chunk encontrado

## Stack

| Camada | Tecnologia |
|---|---|
| Camada               | Tecnologia                                        |
|----------------------|---------------------------------------------------|
| Web framework        | Flask                                             |
| Banco relacional     | PostgreSQL — PDFs íntegros + metadados            |
| Banco vetorial       | Qdrant                                            |
| Modelo de embeddings | `jinaai/jina-embeddings-v3` (1024 dims, COSINE)   |
| Extração de PDF      | PyMuPDF                                           |
| OCR                  | pytesseract + Tesseract OCR                       |
| Detecção de idioma   | langdetect                                        |
| Gerenciador de pacotes | uv                                              |

## Requisitos

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Docker (para o Qdrant)
- PostgreSQL (externo)
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) instalado no sistema

## Instalação

```bash
# 1. Clone o repositório
git clone https://github.com/gchecon/embeddings.git
cd embeddings

# 2. Instale as dependências
uv sync

# 3. Configure as variáveis de ambiente
cp .env.example .env
# Edite .env com as credenciais do PostgreSQL e demais configurações

# 4. Suba o Qdrant via Docker
docker compose up -d
```

## Configuração (`.env`)

```dotenv
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=pdf_store
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secret

QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=pdf_embeddings

EMBEDDING_MODEL=jinaai/jina-embeddings-v3
EMBEDDING_DEVICE=cuda  # ou "cpu"
EMBEDDING_DIM=1024
EMBEDDING_BATCH_SIZE=16

CHUNK_SIZE=1000
CHUNK_OVERLAP=200

FLASK_SECRET_KEY=troque-isto
FLASK_DEBUG=false
```

## Uso

```bash
uv run flask --app app.py run --debug
```

Acesse `http://localhost:5000`.

1. **Indexar** — informe o caminho absoluto de um diretório na página inicial e clique em *Escanear*
2. **Buscar** — vá para `/search`, digite sua pergunta e veja os chunks mais relevantes com score de similaridade
3. **Visualizar** — clique em *Abrir PDF* para abrir o documento na página exata do chunk

## Estrutura do projeto

```
├── app.py                  # entry point Flask
├── config.py               # lê .env e expõe constantes
├── database/
│   ├── postgres.py         # operações no PostgreSQL
│   └── qdrant_client.py    # operações no Qdrant
├── services/
│   ├── pdf_extractor.py    # extração de texto + OCR
│   ├── chunker.py          # chunking com overlapping
│   ├── embedder.py         # geração de embeddings Jina v3
│   ├── indexer.py          # orquestrador do fluxo de indexação
│   └── language_detector.py
├── routes/
│   ├── upload.py           # POST /scan
│   ├── search.py           # GET /search
│   ├── pdf_viewer.py       # GET /pdf/<doc_id>
│   └── progress.py         # GET /progress (SSE)
├── templates/              # HTML (Jinja2)
├── static/js/progress.js   # cliente SSE
├── docker-compose.yml      # Qdrant
└── pyproject.toml
```
