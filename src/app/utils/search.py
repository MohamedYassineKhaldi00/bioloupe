from __future__ import annotations

from typing import Iterable
from sqlalchemy import func


def build_search_filter(model, search_term: str, search_fields: Iterable[str]):
    search_vector = func.to_tsvector(
        "english",
        func.concat_ws(" ", *[getattr(model, field) for field in search_fields]),
    )
    search_query = func.plainto_tsquery("english", search_term)
    return search_vector.op("@@")(search_query)
