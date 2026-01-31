"""Seed or update the demo user/team/session for local development.

Run with:
  .\.venv\Scripts\Activate.ps1 ; $env:PYTHONPATH=".\src" ; python .\scripts\seed_demo.py
"""
from __future__ import annotations

import asyncio
import os
from uuid import uuid4

# Ensure local defaults if env vars are missing
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./bioloupe.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("ENVIRONMENT", "development")

from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.base import async_session_maker
from app.models.user import User
from app.models.team import Team
from app.models.session import Session
from app.services.team_service import TeamService
from app.services.session_service import SessionService


async def ensure_demo() -> None:
    settings = get_settings()
    async with async_session_maker() as db:
        # User
        result = await db.execute(select(User).where(User.email == settings.demo_email))
        demo_user = result.scalar_one_or_none()
        if not demo_user:
            demo_user = User(
                id=uuid4(),
                email=settings.demo_email,
                hashed_password=hash_password(settings.demo_password),
                full_name=settings.demo_full_name,
                is_active=True,
                is_verified=True,
            )
            db.add(demo_user)
            await db.flush()
            print(f"Created demo user: {settings.demo_email}")
        else:
            demo_user.hashed_password = hash_password(settings.demo_password)
            demo_user.full_name = settings.demo_full_name
            demo_user.is_active = True
            demo_user.is_verified = True
            await db.flush()
            print(f"Updated demo user: {settings.demo_email}")

        # Team
        team_result = await db.execute(select(Team).where(Team.name == settings.demo_team_name))
        demo_team = team_result.scalar_one_or_none()
        if not demo_team:
            team_service = TeamService(db)
            demo_team = await team_service.create_team(
                settings.demo_team_name,
                "Demo team created by manual seeder",
                str(demo_user.id),
            )
            print(f"Created demo team: {settings.demo_team_name}")

        # Session
        session_result = await db.execute(select(Session).where(Session.title == settings.demo_session_title))
        demo_session = session_result.scalar_one_or_none()
        if not demo_session:
            session_service = SessionService(db)
            demo_session = await session_service.create_session(
                type(
                    "T",
                    (),
                    {
                        "team_id": str(demo_team.id),
                        "title": settings.demo_session_title,
                        "description": "This is a demo session to help you explore BioLoupe.",
                        "topic_tags": ["demo"],
                    },
                )(),
                str(demo_user.id),
            )
            print(f"Created demo session: {settings.demo_session_title}")

        await db.commit()


if __name__ == "__main__":
    asyncio.run(ensure_demo())
