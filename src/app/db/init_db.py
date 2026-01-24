from __future__ import annotations

import logging
from passlib.context import CryptContext
from sqlalchemy import select

from app.core.config import get_settings
from app.db.base import Base, async_session_maker, engine, verify_connection
from app.models import Team, TeamMember, TeamRole, User

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def init_db() -> None:
    await verify_connection()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_data()


async def seed_data() -> None:
    settings = get_settings()
    if not settings.seed_admin_email or not settings.seed_admin_password:
        return

    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.email == settings.seed_admin_email))
        existing = result.scalar_one_or_none()
        if existing:
            return

        admin = User(
            email=settings.seed_admin_email,
            hashed_password=pwd_context.hash(settings.seed_admin_password),
            full_name="BioLoupe Admin",
            is_active=True,
            is_verified=True,
        )
        session.add(admin)
        await session.flush()

        team = Team(name="BioLoupe Core", description="Default team", created_by_id=admin.id)
        session.add(team)
        await session.flush()

        membership = TeamMember(team_id=team.id, user_id=admin.id, role=TeamRole.owner)
        session.add(membership)

        await session.commit()
        logger.info("Seeded admin user", extra={"admin_id": str(admin.id)})
