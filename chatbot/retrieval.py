import logging
from typing import Any, Dict, List, Optional

from pgvector.django import CosineDistance

from chatbot.embeddings import get_text_embedding
from chatbot.models import KnowledgeChunk

logger = logging.getLogger(__name__)

DISTANCE_THRESHOLD = 0.70


def retrieve_relevant_chunks(
    query: str,
    top_k: int = 4,
    distance_threshold: float = DISTANCE_THRESHOLD,
) -> Dict[str, Any]:
    cleaned_query = (query or "").strip()
    if not cleaned_query:
        return {
            "chunks": [],
            "best_distance": None,
            "has_relevant_match": False,
        }

    query_vector = get_text_embedding(cleaned_query)

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

