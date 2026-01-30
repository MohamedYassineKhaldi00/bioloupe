from __future__ import annotations

from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Material, Session, Team, User


async def gather_autocomplete_terms(db: AsyncSession, prefix: str, limit: int = 5) -> List[str]:
    if not prefix:
        return []

    pattern = f"{prefix}%"
    suggestions: List[str] = []
    probes = [
        (select(User.full_name).where(User.full_name.ilike(pattern)), "full_name"),
        (select(Team.name).where(Team.name.ilike(pattern)), "name"),
        (select(Session.title).where(Session.title.ilike(pattern)), "title"),
        (select(Material.title).where(Material.title.ilike(pattern)), "title"),
    ]

    for stmt, _name in probes:
        stmt = stmt.limit(limit)
        result = await db.execute(stmt)
        suggestions.extend([row[0] for row in result.all() if row and row[0]])
        if len(suggestions) >= limit * len(probes):
            break

    unique = []
    seen = set()
    for term in suggestions:
        normalized = term.strip()
        if normalized and normalized.lower() not in seen:
            seen.add(normalized.lower())
            unique.append(normalized)
        if len(unique) >= limit:
            break

    return unique
