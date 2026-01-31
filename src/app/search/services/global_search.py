from __future__ import annotations

import asyncio
import logging
import time
from collections import Counter
from typing import Iterable

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import Material, Session as SessionModel, Team, User
from app.search.models.global_models import (
    FacetFilter,
    GlobalSearchEntity,
    GlobalSearchRequest,
    GlobalSearchResponse,
    GlobalSearchResult,
)
from app.search.services.search_analytics import SearchAnalyticsService
from app.search.utils.autocomplete import gather_autocomplete_terms
from app.services.cache_service import CacheService

logger = logging.getLogger(__name__)


class GlobalSearchService:
    def __init__(self, db: AsyncSession, analytics: SearchAnalyticsService, cache: CacheService | None = None) -> None:
        self._db = db
        self._analytics = analytics
        self._cache = cache or CacheService()
        self._settings = get_settings()

    async def search(self, request: GlobalSearchRequest) -> GlobalSearchResponse:
        start = time.monotonic()
        await self._analytics.record_query(request.query, [entity.value for entity in request.entities])
        cache_key = self._build_cache_key(request)
        cached = await self._cache.get(cache_key)
        if isinstance(cached, dict):
            return GlobalSearchResponse(**cached)

        tasks = []
        for entity in request.entities:
            if entity == GlobalSearchEntity.user:
                tasks.append(self._search_users(request))
            elif entity == GlobalSearchEntity.team:
                tasks.append(self._search_teams(request))
            elif entity == GlobalSearchEntity.session:
                tasks.append(self._search_sessions(request))
            elif entity == GlobalSearchEntity.material:
                tasks.append(self._search_materials(request))

        segments = await asyncio.gather(*tasks) if tasks else []
        combined: list[dict] = [item for segment in segments for item in segment]
        sorted_results = sorted(combined, key=lambda item: item["score"], reverse=True)
        paged = sorted_results[request.offset : request.offset + request.limit]
        facets = self._build_facets(combined)
        elapsed = int((time.monotonic() - start) * 1000)
        response = GlobalSearchResponse(
            results=[GlobalSearchResult(**item) for item in paged],
            total=len(sorted_results),
            facets=facets,
            elapsed_ms=elapsed,
        )
        await self._cache.set(cache_key, response.model_dump(), ttl=self._settings.search_cache_ttl_seconds)
        return response

    async def autocomplete(self, prefix: str, limit: int = 5) -> list[str]:
        return await gather_autocomplete_terms(self._db, prefix, limit)

    def _build_cache_key(self, request: GlobalSearchRequest) -> str:
        filters = request.filters.model_dump(exclude_none=True) if request.filters else {}
        entity_key = "+".join(sorted(entity.value for entity in request.entities))
        return f"search:global:{request.query.lower()}:{entity_key}:{filters}:{request.limit}:{request.offset}"

    def _build_facets(self, results: Iterable[dict]) -> dict[str, dict[str, int]]:
        entity_counter = Counter()
        material_counter = Counter()
        for row in results:
            entity_counter[row["entity_type"]] += 1
            if row["entity_type"] == GlobalSearchEntity.material.value:
                material_type = row.get("metadata", {}).get("material_type")
                if material_type:
                    material_counter[material_type] += 1
        return {
            "entity_type": dict(entity_counter),
            "material_type": dict(material_counter),
        }

    async def _search_users(self, request: GlobalSearchRequest) -> list[dict]:
        stmt = select(User).where(
            or_(User.full_name.ilike(f"%{request.query}%"), User.email.ilike(f"%{request.query}%"))
        )
        stmt = stmt.limit(request.limit)
        users = (await self._db.scalars(stmt)).all()
        return [self._map_user(user, request.query) for user in users]

    async def _search_teams(self, request: GlobalSearchRequest) -> list[dict]:
        stmt = select(Team).where(Team.name.ilike(f"%{request.query}%"))
        if request.filters and request.filters.team_id:
            stmt = stmt.where(Team.id == request.filters.team_id)
        stmt = stmt.limit(request.limit)
        teams = (await self._db.scalars(stmt)).all()
        return [self._map_team(team, request.query) for team in teams]

    async def _search_sessions(self, request: GlobalSearchRequest) -> list[dict]:
        stmt = select(SessionModel).where(
            or_(SessionModel.title.ilike(f"%{request.query}%"), SessionModel.description.ilike(f"%{request.query}%"))
        )
        if request.filters:
            stmt = self._apply_session_filters(stmt, request.filters)
        stmt = stmt.limit(request.limit)
        sessions = (await self._db.scalars(stmt)).all()
        return [self._map_session(session, request.query) for session in sessions]

    async def _search_materials(self, request: GlobalSearchRequest) -> list[dict]:
        stmt = select(Material).where(Material.title.ilike(f"%{request.query}%"))
        if request.filters:
            stmt = self._apply_material_filters(stmt, request.filters)
        stmt = stmt.limit(request.limit)
        materials = (await self._db.scalars(stmt)).all()
        return [self._map_material(material, request.query) for material in materials]

    def _apply_session_filters(self, stmt, filters: FacetFilter):
        if filters.team_id:
            stmt = stmt.where(SessionModel.team_id == filters.team_id)
        if filters.tags:
            stmt = stmt.where(SessionModel.topic_tags.contains(filters.tags))
        if filters.date_range:
            if filters.date_range.start:
                stmt = stmt.where(SessionModel.created_at >= filters.date_range.start)
            if filters.date_range.end:
                stmt = stmt.where(SessionModel.created_at <= filters.date_range.end)
        return stmt

    def _apply_material_filters(self, stmt, filters: FacetFilter):
        if filters.team_id:
            stmt = stmt.join(SessionModel).where(SessionModel.team_id == filters.team_id)
        if filters.material_type:
            stmt = stmt.where(Material.material_type == filters.material_type)
        if filters.date_range:
            if filters.date_range.start:
                stmt = stmt.where(Material.created_at >= filters.date_range.start)
            if filters.date_range.end:
                stmt = stmt.where(Material.created_at <= filters.date_range.end)
        return stmt

    def _score_text(self, value: str, query: str) -> float:
        normalized = value.lower()
        needle = query.lower()
        if normalized == needle:
            return 1.0
        if needle in normalized:
            return 0.6
        return 0.3

    def _map_user(self, user: User, query: str) -> dict:
        score = max(
            self._score_text(user.full_name, query),
            self._score_text(user.email, query),
        )
        return {
            "entity_type": GlobalSearchEntity.user.value,
            "id": str(user.id),
            "title": user.full_name,
            "description": user.email,
            "team_id": None,
            "score": score,
            "metadata": {"email": user.email},
            "explanation": {"match": "user"},
        }

    def _map_team(self, team: Team, query: str) -> dict:
        return {
            "entity_type": GlobalSearchEntity.team.value,
            "id": str(team.id),
            "title": team.name,
            "description": team.description,
            "team_id": None,
            "score": self._score_text(team.name, query),
            "metadata": {"description": team.description},
            "explanation": {"match": "team"},
        }

    def _map_session(self, session: SessionModel, query: str) -> dict:
        base = self._score_text(session.title, query)
        if session.description:
            base = max(base, self._score_text(session.description, query))
        return {
            "entity_type": GlobalSearchEntity.session.value,
            "id": str(session.id),
            "title": session.title,
            "description": session.description,
            "team_id": str(session.team_id),
            "score": base,
            "metadata": {"topic_tags": session.topic_tags},
            "explanation": {"match": "session"},
        }

    def _map_material(self, material: Material, query: str) -> dict:
        score = self._score_text(material.title, query)
        return {
            "entity_type": GlobalSearchEntity.material.value,
            "id": str(material.id),
            "title": material.title,
            "description": None,
            "team_id": None,
            "score": score,
            "metadata": {"material_type": material.material_type.value, "metadata": material.metadata_},
            "explanation": {"match": "material"},
        }