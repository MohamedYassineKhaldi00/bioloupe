from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Dict, Any


class ReRankingService:
    def rerank_by_recency(self, results: List[Dict[str, Any]], recency_weight: float = 0.3) -> List[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        for result in results:
            indexed_at = result.get("indexed_at")
            recency_score = 0.0
            if indexed_at:
                try:
                    iso = indexed_at
                    if iso.endswith("Z"):
                        # make offset explicit for fromisoformat
                        iso = iso.replace("Z", "+00:00")
                    ia = datetime.fromisoformat(iso)
                    if ia.tzinfo is None:
                        ia = ia.replace(tzinfo=timezone.utc)
                    days_old = (now - ia).days
                    recency_score = 1.0 / (1.0 + days_old / 30.0)
                except Exception:
                    recency_score = 0.0

            original_score = result.get("score", 0.0)
            result["score"] = (1 - recency_weight) * original_score + recency_weight * recency_score
            result["recency_score"] = recency_score

        return sorted(results, key=lambda x: x["score"], reverse=True)