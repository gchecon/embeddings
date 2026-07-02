import logging

import torch
from sentence_transformers import SentenceTransformer

from config import settings

_model: SentenceTransformer | None = None


class _SuppressTorchDtypeWarning(logging.Filter):
    """O config.json do modelo Jina v3 usa o campo legado `torch_dtype`,
    o que dispara um warning interno do transformers a cada load/save de
    config. Não temos controle sobre esse config.json, então filtramos
    apenas essa mensagem específica (demais warnings continuam visíveis)."""

    def filter(self, record: logging.LogRecord) -> bool:
        return "torch_dtype" not in record.getMessage()


# Filtro de Logger só é consultado no logger onde o warning é emitido
# (não nos ancestrais, durante a propagação), então precisa ser anexado
# diretamente aos loggers de origem, não só ao logger raiz "transformers".
for _logger_name in ("transformers", "transformers.configuration_utils", "transformers.modeling_utils"):
    logging.getLogger(_logger_name).addFilter(_SuppressTorchDtypeWarning())


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        # Limita threads de CPU para não travar a máquina durante a indexação
        if settings.TORCH_NUM_THREADS > 0:
            torch.set_num_threads(settings.TORCH_NUM_THREADS)
        _model = SentenceTransformer(
            settings.EMBEDDING_MODEL,
            device=_resolve_device(),
            trust_remote_code=True,
        )
    return _model


def get_device_info() -> dict:
    """Retorna o device efetivamente usado pelo modelo e, se for GPU, seu nome."""
    model = get_model()
    device = str(model.device)
    gpu_name = None
    if device.startswith("cuda") and torch.cuda.is_available():
        try:
            gpu_name = torch.cuda.get_device_name(model.device)
        except Exception:
            gpu_name = None
    return {"device": "cuda" if device.startswith("cuda") else "cpu", "gpu_name": gpu_name}


def count_tokens(texts: list[str]) -> int:
    """Conta os tokens efetivamente enviados ao modelo (após truncamento)."""
    if not texts:
        return 0
    model = get_model()
    features = model.tokenize(texts)
    attention_mask = features.get("attention_mask")
    if attention_mask is not None:
        return int(attention_mask.sum().item())
    return sum(len(ids) for ids in features["input_ids"])


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
