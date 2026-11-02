import logging
from typing import Any, Dict, List, Optional
from pgvector.django import CosineDistance
from sentence_transformers import SentenceTransformer

from chatbot.models import KnowledgeChunk

logger = logging.getLogger(__name__)

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
_embed_model: Optional[SentenceTransformer] = None

# Distance threshold: Cosine distance > 0.70 corresponds to cosine similarity < 0.30
DISTANCE_THRESHOLD = 0.70


def get_embedding_model() -> SentenceTransformer:
    global _embed_model
    if _embed_model is None:
        _embed_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _embed_model


def retrieve_relevant_chunks(
    query: str,
    top_k: int = 4,
    distance_threshold: float = DISTANCE_THRESHOLD,
) -> Dict[str, Any]:
    """
    Takes a user query, computes its embedding using all-MiniLM-L6-v2,
    queries KnowledgeChunk with pgvector CosineDistance, and returns top_k chunks.

    Returns:
        dict with:
            - 'chunks': list of dicts (title, content, source_url, distance, similarity)
            - 'best_distance': float or None
            - 'has_relevant_match': bool (True if best_distance <= distance_threshold)
    """
    cleaned_query = (query or "").strip()
    if not cleaned_query:
        return {
            "chunks": [],
            "best_distance": None,
            "has_relevant_match": False,
        }

    model = get_embedding_model()
    query_vector = model.encode(cleaned_query).tolist()

    qs = KnowledgeChunk.objects.annotate(
        distance=CosineDistance("embedding", query_vector)
    ).order_by("distance")[:top_k]

    results: List[Dict[str, Any]] = []
    best_distance: Optional[float] = None

    for chunk in qs:
        d = float(chunk.distance)
        if best_distance is None:
            best_distance = d

        results.append({
            "id": chunk.id,
            "source_type": chunk.source_type,
            "source_id": chunk.source_id,
            "title": chunk.title,
            "content": chunk.content,
            "source_url": chunk.source_url,
            "distance": round(d, 4),
            "similarity": round(1.0 - d, 4),
        })

    has_relevant_match = bool(
        best_distance is not None and best_distance <= distance_threshold
    )

    return {
        "chunks": results,
        "best_distance": round(best_distance, 4) if best_distance is not None else None,
        "has_relevant_match": has_relevant_match,
    }

