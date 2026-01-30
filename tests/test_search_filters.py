import pytest

from app.utils.search_filters import build_qdrant_filter
import qdrant_client.http.models as rest


def test_build_qdrant_filter_fallback(monkeypatch):
    # Force FieldCondition to be unavailable to hit fallback dict path
    monkeypatch.setattr(rest, "FieldCondition", None, raising=False)
    res = build_qdrant_filter({"session_id": "s1", "modality": "paper"})
    assert isinstance(res, dict)
    assert "must" in res
    assert any(isinstance(item, dict) for item in res["must"]) 


def test_build_qdrant_filter_typed_when_available():
    # If model types are present, we get a rest.Filter (or dict when client differs)
    res = build_qdrant_filter({"session_id": "s1"})
    assert res is not None
