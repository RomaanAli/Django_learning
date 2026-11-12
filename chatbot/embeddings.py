import logging
import math
import time
from typing import Any, List, Optional, Union

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
HF_FEATURE_EXTRACTION_URL = (
    "https://router.huggingface.co/hf-inference/models/"
    "sentence-transformers/all-MiniLM-L6-v2/pipeline/feature-extraction"
)


def pool_and_normalize_vector(raw_item: Any) -> List[float]:
    """
    Shared helper: converts raw Hugging Face feature-extraction response for ONE
    text chunk into exactly one 384-dimensional L2-normalized vector.

    Order of operations:
      a. Log/print the raw shape received.
      b. If already flat list of 384 numbers, use it.
      c. If list of token vectors ([tokens, 384]), mean-pool across tokens.
      d. L2-normalize (divide each component by sqrt(sum of squares)).
      e. Assert len(vector) == 384.
      f. Return plain Python list of floats.
    """
    if not isinstance(raw_item, list) or len(raw_item) == 0:
        raise ValueError(f"Expected non-empty list from embedding API, got: {type(raw_item)}")

    if isinstance(raw_item[0], (int, float)):
        raw_shape = f"[flat, {len(raw_item)}]"
        logger.info("Raw embedding shape: %s", raw_shape)
        if len(raw_item) != 384:
            raise ValueError(f"Expected flat vector of length 384, but got length {len(raw_item)} (shape {raw_shape})")
        vector = [float(x) for x in raw_item]

    elif isinstance(raw_item[0], list):
        if len(raw_item) == 1 and isinstance(raw_item[0][0], list):
            return pool_and_normalize_vector(raw_item[0])

        num_tokens = len(raw_item)
        token_dim = len(raw_item[0]) if num_tokens > 0 else 0
        raw_shape = f"[{num_tokens} tokens, {token_dim}]"
        logger.info("Raw embedding shape: %s", raw_shape)

        if token_dim != 384:
            raise ValueError(f"Expected token vector of length 384, but got length {token_dim} (shape {raw_shape})")

        vector = [0.0] * 384
        for token_vec in raw_item:
            if len(token_vec) != 384:
                raise ValueError(f"Token vector dimension mismatch: expected 384, got {len(token_vec)}")
            for j in range(384):
                vector[j] += float(token_vec[j])

        for j in range(384):
            vector[j] /= num_tokens

    else:
        raise ValueError(f"Unexpected data type in embedding: {type(raw_item[0])}")

    norm_sq = sum(v * v for v in vector)
    norm = math.sqrt(norm_sq)
    if norm > 0.0:
        vector = [v / norm for v in vector]
    else:
        vector = [0.0] * 384

    assert len(vector) == 384, f"Final vector length assertion failed: expected 384, got {len(vector)}"
    return vector


def request_hf_embeddings(inputs: Union[str, List[str]], hf_token: str) -> Any:
    """
    Calls the Hugging Face Inference API with 60s timeout and up to 3 retries
    on 503 (model loading) or 504 (timeout).
    """
    clean_token = (hf_token or "").strip()
    if not clean_token:
        raise ValueError("HF token is wrong or missing")

    headers = {
        "Authorization": f"Bearer {clean_token}",
        "Content-Type": "application/json",
    }
    payload = {"inputs": inputs}

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(
                HF_FEATURE_EXTRACTION_URL,
                headers=headers,
                json=payload,
                timeout=60,
            )

            if response.status_code == 200:
                return response.json()

            if response.status_code == 401:
                raise RuntimeError("HF token is wrong or missing")

            if response.status_code == 404:
                raise RuntimeError(f"Hugging Face endpoint not found: {HF_FEATURE_EXTRACTION_URL}")

            if response.status_code == 403:
                raise RuntimeError(
                    "HF token has insufficient permissions. Ensure your token has "
                    "'Make calls to Inference Providers' enabled on Hugging Face."
                )

            if response.status_code in (503, 504):
                if attempt < max_retries:
                    time.sleep(attempt * 4)
                    continue
                raise RuntimeError(
                    f"Hugging Face server busy (HTTP {response.status_code}) after {max_retries} retries."
                )

            raise RuntimeError(
                f"Hugging Face API returned HTTP {response.status_code}: {response.text[:200]}"
            )

        except requests.Timeout:
            if attempt < max_retries:
                time.sleep(attempt * 4)
                continue
            raise RuntimeError(f"Hugging Face API request timed out after {max_retries} attempts.")
        except requests.RequestException as e:
            if attempt < max_retries:
                time.sleep(attempt * 4)
                continue
            raise RuntimeError(f"Hugging Face API network error: {e}") from e

    raise RuntimeError("Failed to get response from Hugging Face API.")


def get_text_embedding(text: str, hf_token: Optional[str] = None) -> List[float]:
    """
    Generates a single 384-dimensional normalized vector for a single text query.
    Used by chatbot/retrieval.py.
    """
    token = hf_token if hf_token is not None else getattr(settings, "HF_TOKEN", "")
    token = (token or "").strip()
    if not token:
        raise ValueError("HF token is wrong or missing")

    raw_data = request_hf_embeddings(text, token)
    return pool_and_normalize_vector(raw_data)


def get_batch_embeddings(
    texts: List[str],
    hf_token: Optional[str] = None,
    batch_size: int = 10,
    pause_between_batches: float = 0.5,
) -> List[List[float]]:
    """
    Generates embeddings for a list of texts in small batches (default 10)
    with a short pause between batches.
    Used by chatbot/management/commands/build_chatbot_index.py.
    """
    token = hf_token if hf_token is not None else getattr(settings, "HF_TOKEN", "")
    token = (token or "").strip()
    if not token:
        raise ValueError("HF token is wrong or missing")

    all_embeddings: List[List[float]] = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        try:
            raw_batch = request_hf_embeddings(batch, token)
        except Exception as e:
            raise RuntimeError(f"Failed to generate embeddings for batch starting at chunk index {i}: {e}") from e

        if not isinstance(raw_batch, list) or len(raw_batch) != len(batch):
            raise ValueError(f"Expected batch output of {len(batch)} items, got: {type(raw_batch)}")

        for idx, item in enumerate(raw_batch):
            try:
                vec = pool_and_normalize_vector(item)
                all_embeddings.append(vec)
            except Exception as e:
                chunk_num = i + idx
                preview = (batch[idx][:40] + "...") if len(batch[idx]) > 40 else batch[idx]
                raise RuntimeError(f"Failed to pool/normalize chunk {chunk_num} ('{preview}'): {e}") from e

        if pause_between_batches > 0 and (i + batch_size) < len(texts):
            time.sleep(pause_between_batches)

    return all_embeddings

