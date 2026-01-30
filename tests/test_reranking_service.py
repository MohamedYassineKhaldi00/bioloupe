from datetime import datetime, timedelta

from app.services.reranking_service import ReRankingService


def test_rerank_by_recency_orders_recent_first():
    now = datetime.utcnow()
    older = {"material_id": "old", "score": 0.9, "indexed_at": (now - timedelta(days=90)).isoformat() + "Z"}
    recent = {"material_id": "new", "score": 0.8, "indexed_at": (now - timedelta(days=1)).isoformat() + "Z"}

    svc = ReRankingService()
    out = svc.rerank_by_recency([older, recent], recency_weight=0.3)
    # Ensure recent item has higher adjusted score than older one
    scores = {item["material_id"]: item["score"] for item in out}
    assert scores["new"] > scores["old"]
