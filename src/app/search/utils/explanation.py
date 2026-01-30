from __future__ import annotations

from typing import Iterable, Sequence


def build_similarity_explanation(tags_a: Sequence[str] | None, tags_b: Sequence[str] | None, score: float) -> dict[str, object]:
    set_a = set(tags_a or [])
    set_b = set(tags_b or [])
    shared = sorted(set_a & set_b)
    reason = "vector similarity"
    if shared:
        reason = "shared tags"
    return {
        "shared_tags": shared,
        "embedding_similarity": score,
        "why": reason,
    }
