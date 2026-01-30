from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Any


def enrich_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Enrich payload with computed fields (content_preview, indexed_at)"""
    enriched = dict(payload)

    if payload.get("content_preview") is None:
        # Attempt to compute a preview from 'metadata' if available
        content = None
        # If metadata has 'abstract' or 'text' keys, use them
        md = payload.get("metadata") or {}
        content = md.get("abstract") or md.get("text")
        if content:
            enriched["content_preview"] = content[:500]

    if enriched.get("indexed_at") is None:
        enriched["indexed_at"] = datetime.now(timezone.utc).isoformat()

    return enriched
