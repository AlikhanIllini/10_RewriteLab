"""
Semantic search over past rewrite sessions using sentence-transformers.

Integrates A8 embedding work (all-MiniLM-L6-v2) into the Django app.
Users can search by meaning rather than exact keyword match.
"""

import logging
import numpy as np

from rewrites.models import RewriteSession, RewriteResult

logger = logging.getLogger(__name__)

EMBEDDING_MODEL_ID = "all-MiniLM-L6-v2"
_MODEL = None


def _get_model():
    """Lazy-load the sentence-transformer model and cache it in-process."""
    global _MODEL
    if _MODEL is not None:
        return _MODEL

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise ValueError(
            "sentence-transformers is not installed. "
            "Run: pip install sentence-transformers"
        ) from exc

    _MODEL = SentenceTransformer(EMBEDDING_MODEL_ID)
    return _MODEL


def _cosine_similarity(a, b):
    """Compute cosine similarity between two vectors."""
    dot = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))


def semantic_search_sessions(query: str, top_k: int = 5, user=None):
    """
    Search rewrite sessions by semantic similarity to the query.

    Args:
        query: The user's natural-language search query.
        top_k: Number of results to return.
        user: If provided, only search sessions belonging to this user.

    Returns:
        List of dicts with keys: session, score, matched_text
    """
    query = (query or "").strip()
    if not query:
        raise ValueError("Search query cannot be empty.")

    if len(query) < 3:
        raise ValueError("Search query must be at least 3 characters.")

    if len(query) > 2000:
        raise ValueError("Search query is too long (max 2000 characters).")

    model = _get_model()

    # Fetch sessions with their results
    qs = RewriteSession.objects.select_related("context", "tone").prefetch_related(
        "results"
    )
    if user and user.is_authenticated:
        qs = qs.filter(user=user)

    sessions = list(qs[:200])  # cap to avoid embedding too many at once

    if not sessions:
        return []

    # Build corpus: each session's original text + any rewrite texts
    corpus_items = []
    for session in sessions:
        corpus_items.append(
            {
                "session": session,
                "text": session.original_text,
                "source": "original",
            }
        )
        for result in session.results.all():
            corpus_items.append(
                {
                    "session": session,
                    "text": result.rewritten_text,
                    "source": f"rewrite_{result.version_label}",
                }
            )

    if not corpus_items:
        return []

    # Embed query and corpus
    corpus_texts = [item["text"] for item in corpus_items]

    try:
        query_embedding = model.encode(query, convert_to_numpy=True)
        corpus_embeddings = model.encode(corpus_texts, convert_to_numpy=True)
    except Exception as exc:
        logger.exception("Embedding computation failed")
        raise ValueError(f"Embedding computation failed: {exc}") from exc

    # Compute similarities
    scored = []
    for i, item in enumerate(corpus_items):
        score = _cosine_similarity(query_embedding, corpus_embeddings[i])
        scored.append({**item, "score": round(score, 4)})

    # Sort by score descending
    scored.sort(key=lambda x: x["score"], reverse=True)

    # Deduplicate by session (keep highest scoring match per session)
    seen_sessions = set()
    results = []
    for item in scored:
        sid = item["session"].pk
        if sid in seen_sessions:
            continue
        seen_sessions.add(sid)
        results.append(
            {
                "session": item["session"],
                "score": item["score"],
                "matched_text": item["text"][:200],
                "source": item["source"],
            }
        )
        if len(results) >= top_k:
            break

    return results
