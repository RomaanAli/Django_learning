import logging
import math
from typing import List, Optional

from fastembed import TextEmbedding

logger = logging.getLogger(__name__)

EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSIONS = 384

_model: Optional[TextEmbedding] = None


def get_embedding_model() -> TextEmbedding:
    """
    Lazy-loads the lightweight ONNX-based FastEmbed model once in-memory.
    """
    global _model
    if _model is None:
        logger.info("Initializing FastEmbed model: %s", EMBEDDING_MODEL_NAME)
        _model = TextEmbedding(model_name=EMBEDDING_MODEL_NAME)
    return _model


def _normalize_vector(vector: List[float]) -> List[float]:
    """
    Validates vector length and ensures L2-normalization.
    """
    if len(vector) != EMBEDDING_DIMENSIONS:
        raise ValueError(
            f"Expected vector length {EMBEDDING_DIMENSIONS}, got {len(vector)}"
        )

    norm_sq = sum(v * v for v in vector)
    norm = math.sqrt(norm_sq)

    # If already normalized within tolerance (1.0 +/- 0.001), return as is
    if 0.999 <= norm <= 1.001:
        return vector

    if norm > 0.0:
        return [v / norm for v in vector]
    return [0.0] * EMBEDDING_DIMENSIONS


def get_text_embedding(text: str, **kwargs) -> List[float]:
    """
    Generates a single 384-dimensional normalized vector for a single text.
    kwargs accepted for backwards compatibility (e.g. hf_token).
    """
    cleaned_text = (text or "").strip()
    if not cleaned_text:
        return [0.0] * EMBEDDING_DIMENSIONS

    model = get_embedding_model()
    embeddings_gen = model.embed([cleaned_text])
    raw_vec = next(embeddings_gen)

    vector = [float(x) for x in raw_vec]
    return _normalize_vector(vector)


def get_batch_embeddings(
    texts: List[str],
    batch_size: int = 16,
    **kwargs,
) -> List[List[float]]:
    """
    Generates 384-dimensional normalized vectors for a batch of texts.
    kwargs accepted for backwards compatibility (e.g. hf_token, pause_between_batches).
    """
    if not texts:
        return []

    model = get_embedding_model()
    embeddings_gen = model.embed(texts, batch_size=batch_size)

    results: List[List[float]] = []
    for raw_vec in embeddings_gen:
        vec = [float(x) for x in raw_vec]
        results.append(_normalize_vector(vec))

    return results
