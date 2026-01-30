import re
from datetime import datetime, timezone

from app.services.vector_enrichment import enrich_payload


def test_enrich_sets_content_preview_from_metadata():
    payload = {"material_id": "m1", "session_id": "s1", "team_id": "t1", "modality": "paper", "metadata": {"abstract": "A" * 600}}
    enriched = enrich_payload(payload)
    assert "content_preview" in enriched
    assert len(enriched["content_preview"]) == 500


def test_enrich_sets_indexed_at_iso():
    payload = {"material_id": "m1", "session_id": "s1", "team_id": "t1", "modality": "paper"}
    enriched = enrich_payload(payload)
    assert "indexed_at" in enriched
    # basic ISO format check
    assert re.match(r"\d{4}-\d{2}-\d{2}T", enriched["indexed_at"])
    # parseable
    dt = datetime.fromisoformat(enriched["indexed_at"].replace("Z", "+00:00"))
    assert dt.tzinfo is not None
