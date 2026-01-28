from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import MaterialNotFound
from app.models import Material, MaterialType
from app.services.activity_service import ActivityService
from app.services.qdrant_service import QdrantService
from app.services.storage_service import StorageService
from app.utils.material_validators import validate_material_metadata
from app.utils.search import build_search_filter


class MaterialService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.activity = ActivityService(db)
        self.qdrant = QdrantService()
        self.storage = StorageService()

    async def create_material(self, data, user_id: str) -> Material:
        metadata = validate_material_metadata(data.material_type, data.metadata)
        material = Material(
            id=uuid.uuid4(),
            session_id=data.session_id,
            uploaded_by_id=user_id,
            material_type=data.material_type,
            title=data.title,
            metadata_=metadata,
            file_url=data.file_url,
        )
        self.db.add(material)
        await self.activity.log(data.session_id, user_id, "created", "material", str(material.id))
        await self.db.flush()
        return material

    async def update_material(self, material_id: str, data, user_id: str) -> Material:
        material = await self.get_material(material_id)
        if data.title is not None:
            material.title = data.title
        if data.metadata is not None:
            material.metadata_ = validate_material_metadata(material.material_type, data.metadata)
        await self.activity.log(material.session_id, user_id, "updated", "material", material_id)
        await self.db.flush()
        return material

    async def get_material(self, material_id: str) -> Material:
        material = await self.db.get(Material, material_id)
        if not material or material.deleted_at is not None:
            raise MaterialNotFound(material_id)
        return material

    async def soft_delete(self, material_id: str, user_id: str) -> None:
        material = await self.get_material(material_id)
        material.deleted_at = datetime.now(timezone.utc)
        await self.activity.log(material.session_id, user_id, "deleted", "material", material_id)
        await self.db.flush()

        if material.qdrant_point_id:
            await self.qdrant.delete_points("bioloupe_unified", [str(material.qdrant_point_id)])
        if material.file_url:
            bucket = self.storage.bucket_for_material(material.material_type)
            await self.storage.delete_object(bucket, material.file_url)

    async def restore(self, material_id: str, user_id: str) -> Material:
        material = await self.get_material(material_id)
        if material.deleted_at is None:
            return material
        if material.deleted_at < datetime.now(timezone.utc) - timedelta(days=30):
            raise MaterialNotFound(material_id)
        material.deleted_at = None
        await self.activity.log(material.session_id, user_id, "restored", "material", material_id)
        await self.db.flush()
        return material

    async def list_materials_paginated(
        self,
        session_id: str,
        material_type: MaterialType | None,
        skip: int,
        limit: int,
    ) -> tuple[list[Material], int]:
        query = select(Material).where(Material.session_id == session_id, Material.deleted_at.is_(None))
        if material_type:
            query = query.where(Material.material_type == material_type)
        total = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total_count = total.scalar_one()
        result = await self.db.execute(
            query.order_by(Material.updated_at.desc()).offset(skip).limit(limit)
        )
        return result.scalars().all(), total_count

    async def search_materials(self, query: str, session_id: str | None, material_type: MaterialType | None):
        search_filter = build_search_filter(Material, query, ["title"])
        stmt = select(Material).where(search_filter, Material.deleted_at.is_(None))
        if session_id:
            stmt = stmt.where(Material.session_id == session_id)
        if material_type:
            stmt = stmt.where(Material.material_type == material_type)
        result = await self.db.execute(stmt.order_by(Material.updated_at.desc()))
        return result.scalars().all()

    async def add_tags(self, material_id: str, tags: list[str], user_id: str) -> Material:
        material = await self.get_material(material_id)
        metadata = material.metadata_ or {}
        existing = set(metadata.get("tags", []))
        metadata["tags"] = sorted(existing.union(tags))
        material.metadata_ = metadata
        await self.activity.log(material.session_id, user_id, "updated", "material", material_id)
        await self.db.flush()
        return material

    async def remove_tags(self, material_id: str, tags: list[str], user_id: str) -> Material:
        material = await self.get_material(material_id)
        metadata = material.metadata_ or {}
        existing = set(metadata.get("tags", []))
        metadata["tags"] = sorted(existing.difference(tags))
        material.metadata_ = metadata
        await self.activity.log(material.session_id, user_id, "updated", "material", material_id)
        await self.db.flush()
        return material

    async def batch_update(self, updates: list, user_id: str) -> list[Material]:
        materials: list[Material] = []
        for item in updates:
            material = await self.get_material(item.material_id)
            material.metadata_ = validate_material_metadata(material.material_type, item.metadata)
            materials.append(material)
            await self.activity.log(material.session_id, user_id, "updated", "material", str(material.id))
        await self.db.flush()
        return materials

    async def material_stats(self, session_id: str) -> dict:
        total = await self.db.execute(
            select(func.count(Material.id)).where(
                Material.session_id == session_id,
                Material.deleted_at.is_(None),
            )
        )
        by_type = await self.db.execute(
            select(Material.material_type, func.count(Material.id))
            .where(Material.session_id == session_id, Material.deleted_at.is_(None))
            .group_by(Material.material_type)
        )
        return {
            "total": total.scalar_one(),
            "by_type": {str(row[0]): row[1] for row in by_type.all()},
        }
