from sentence_transformers import SentenceTransformer

from config import settings

_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(
            settings.EMBEDDING_MODEL,
            device=_resolve_device(),
            trust_remote_code=True,
        )
    return _model


def embed_passages(texts: list[str]) -> list[list[float]]:
    model = get_model()
    vectors = model.encode(
        texts,
        task="retrieval.passage",
        normalize_embeddings=True,
        batch_size=settings.EMBEDDING_BATCH_SIZE,
        show_progress_bar=False,
    )
    return vectors.tolist()


def embed_query(text: str) -> list[float]:
    model = get_model()
    vector = model.encode(
        text,
        task="retrieval.query",
        normalize_embeddings=True,
    )
    return vector.tolist()


def _resolve_device() -> str:
    if settings.EMBEDDING_DEVICE == "cuda":
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
        except ImportError:
            pass
        return "cpu"
    return settings.EMBEDDING_DEVICE
