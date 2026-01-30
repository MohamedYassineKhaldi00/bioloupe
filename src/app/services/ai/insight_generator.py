"""Automated insight generation service."""

from __future__ import annotations

import logging
from typing import Any

from app.services.ai.trend_detector import TrendDetector
from app.services.ai.gap_analyzer import GapAnalyzer

logger = logging.getLogger(__name__)


class InsightGenerator:
    """Generate automated insights from session activity."""

    def __init__(
        self,
        trend_detector: TrendDetector | None = None,
        gap_analyzer: GapAnalyzer | None = None,
    ):
        self.trend_detector = trend_detector or TrendDetector()
        self.gap_analyzer = gap_analyzer or GapAnalyzer()

    async def generate_session_insights(
        self,
        session_id: str,
        time_window_days: int,
        db: Any,
        qdrant_service: Any,
    ) -> list[dict[str, Any]]:
        """
        Generate comprehensive insights from session activity.

        Includes trend detection, gap analysis, and recommendations.
        """
        insights = []

        # Detect trends
        trends = await self.trend_detector.detect_trends(
            session_id, time_window_days, db
        )
        insights.extend(trends)

        # Find gaps
        gaps = await self.gap_analyzer.find_gaps(session_id, db, qdrant_service)
        insights.extend(gaps)

        # Sort by confidence
        insights.sort(key=lambda x: x.get("confidence", 0), reverse=True)

        return insights

    async def generate_weekly_digest(
        self, session_id: str, db: Any, qdrant_service: Any
    ) -> dict[str, Any]:
        """Generate weekly digest of interesting findings."""
        insights = await self.generate_session_insights(
            session_id=session_id,
            time_window_days=7,
            db=db,
            qdrant_service=qdrant_service,
        )

        # Group by type
        trends = [i for i in insights if "trend" in i.get("type", "")]
        gaps = [i for i in insights if "gap" in i.get("type", "")]

        return {
            "period": "weekly",
            "trends": trends,
            "gaps": gaps,
            "summary": self._generate_summary(insights),
        }

    def _generate_summary(self, insights: list[dict[str, Any]]) -> str:
        """Generate text summary of insights."""
        if not insights:
            return "No significant insights this period"

        top_insight = insights[0]
        return f"Key insight: {top_insight.get('insight', 'Analysis complete')}"
