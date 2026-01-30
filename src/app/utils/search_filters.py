from __future__ import annotations

from typing import Dict, Any, Optional
from qdrant_client.http import models as rest


def build_qdrant_filter(filters: Optional[Dict[str, Any]]) -> Optional[dict]:
    if not filters:
        return None

    must = []

    def _add_match(key: str, value: Any) -> None:
        try:
            must.append(rest.FieldCondition(key=key, match=rest.MatchValue(value=value)))
        except Exception:
            must.append({"key": key, "match": {"value": value}})

    def _add_range(key: str, start: Any, end: Any) -> None:
        try:
            must.append(rest.FieldCondition(key=key, range=rest.Range(gte=start, lte=end)))
        except Exception:
            must.append({"key": key, "range": {"gte": start, "lte": end}})

    if "session_id" in filters:
        _add_match("session_id", filters["session_id"]) 

    if "team_id" in filters:
        _add_match("team_id", filters["team_id"]) 

    if "modality" in filters:
        _add_match("modality", filters["modality"]) 

    if "source" in filters:
        _add_match("source", filters["source"]) 

    if "date_range" in filters:
        dr = filters["date_range"]
        _add_range("indexed_at", dr.get("start"), dr.get("end"))

    # prefer typed Filter when available, otherwise return a plain dict structure
    try:
        return rest.Filter(must=must) if must else None
    except Exception:
        return {"must": must} if must else None
