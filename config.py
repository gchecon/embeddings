import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

# Aplicar variáveis de ambiente antes de qualquer import externo
_hf_home = os.getenv("HF_HOME", "")
if _hf_home:
    os.environ["HF_HOME"] = _hf_home

_hf_timeout = os.getenv("HF_HUB_DOWNLOAD_TIMEOUT", "")
if _hf_timeout:
    os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = _hf_timeout

for _proxy_var in ("HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY"):
    _val = os.getenv(_proxy_var, "")
    if _val:
        os.environ[_proxy_var] = _val
        os.environ[_proxy_var.lower()] = _val  # requests aceita minúsculo


@dataclass
class Settings:
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "1000"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "200"))

    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "pdf_store")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "")

    QDRANT_HOST: str = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT: int = int(os.getenv("QDRANT_PORT", "6333"))
    QDRANT_COLLECTION: str = os.getenv("QDRANT_COLLECTION", "pdf_embeddings")

    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "jinaai/jina-embeddings-v3")
    EMBEDDING_DEVICE: str = os.getenv("EMBEDDING_DEVICE", "cuda")
    EMBEDDING_DIM: int = int(os.getenv("EMBEDDING_DIM", "1024"))
    EMBEDDING_BATCH_SIZE: int = int(os.getenv("EMBEDDING_BATCH_SIZE", "4"))
    # 0 = sem limite (usa todos os núcleos); >0 = limita threads do PyTorch
    TORCH_NUM_THREADS: int = int(os.getenv("TORCH_NUM_THREADS", "2"))
    # Pausa em segundos entre arquivos indexados (alivia CPU/rede)
    INDEXING_PAUSE_SECONDS: float = float(os.getenv("INDEXING_PAUSE_SECONDS", "0.5"))

    POSTGRES_CONNECT_TIMEOUT: int = int(os.getenv("POSTGRES_CONNECT_TIMEOUT", "30"))

    FLASK_SECRET_KEY: str = os.getenv("FLASK_SECRET_KEY", "dev-only-secret")
    FLASK_DEBUG: bool = os.getenv("FLASK_DEBUG", "false").lower() == "true"

    @property
    def postgres_dsn(self) -> str:
        return (
            f"host={self.POSTGRES_HOST} "
            f"port={self.POSTGRES_PORT} "
            f"dbname={self.POSTGRES_DB} "
            f"user={self.POSTGRES_USER} "
            f"password={self.POSTGRES_PASSWORD} "
            f"connect_timeout={self.POSTGRES_CONNECT_TIMEOUT}"
        )


settings = Settings()