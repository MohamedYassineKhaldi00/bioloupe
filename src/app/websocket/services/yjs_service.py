from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

import y_py as Y
from redis.asyncio import Redis

if TYPE_CHECKING:
    from collections.abc import Iterable

logger = logging.getLogger(__name__)


class YjsService:
    """Manages Y.js documents for collaborative editing."""

    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.documents: dict[str, Y.YDoc] = {}
        self._last_activity: dict[str, datetime] = {}
        self._doc_locks: dict[str, asyncio.Lock] = {}

    def _get_lock(self, material_id: str) -> asyncio.Lock:
        """Get or create lock for material."""
        if material_id not in self._doc_locks:
            self._doc_locks[material_id] = asyncio.Lock()
        return self._doc_locks[material_id]

    def _ydoc_key(self, material_id: str) -> str:
        """Redis key for Y.js document state."""
        return f"ydoc:{material_id}"

    def _activity_key(self, material_id: str) -> str:
        """Redis key for last activity timestamp."""
        return f"ydoc:activity:{material_id}"

    async def get_or_create_document(
        self,
        material_id: str
    ) -> Y.YDoc:
        """Get cached document or create new one."""
        async with self._get_lock(material_id):
            if material_id in self.documents:
                self._last_activity[material_id] = (
                    datetime.now(timezone.utc)
                )
                return self.documents[material_id]

            key = self._ydoc_key(material_id)
            state = await self.redis.get(key)

            if state:
                doc = Y.YDoc()
                Y.apply_update(doc, bytes.fromhex(state))
                logger.info(f"Restored Y.js document: {material_id}")
            else:
                doc = Y.YDoc()
                logger.info(f"Created new Y.js document: {material_id}")

            self.documents[material_id] = doc
            self._last_activity[material_id] = (
                datetime.now(timezone.utc)
            )

            return doc

    async def save_document_state(self, material_id: str) -> None:
        """Persist document state to Redis."""
        async with self._get_lock(material_id):
            doc = self.documents.get(material_id)
            if not doc:
                return

            state = Y.encode_state_as_update(doc)
            key = self._ydoc_key(material_id)
            await self.redis.set(key, state.hex())

            activity_key = self._activity_key(material_id)
            now = datetime.now(timezone.utc).isoformat()
            await self.redis.set(activity_key, now)

            logger.debug(f"Saved Y.js document: {material_id}")

    async def apply_update(
        self,
        material_id: str,
        update: bytes
    ) -> bytes:
        """Apply update from client to document."""
        doc = await self.get_or_create_document(material_id)

        async with self._get_lock(material_id):
            Y.apply_update(doc, update)
            self._last_activity[material_id] = (
                datetime.now(timezone.utc)
            )

        await self.save_document_state(material_id)

        return Y.encode_state_vector(doc)

    async def get_state_vector(self, material_id: str) -> bytes:
        """Get current state vector for document."""
        doc = await self.get_or_create_document(material_id)
        return Y.encode_state_vector(doc)

    async def get_missing_updates(
        self,
        material_id: str,
        client_state_vector: bytes
    ) -> bytes:
        """Get updates client is missing."""
        doc = await self.get_or_create_document(material_id)
        return Y.encode_state_as_update(doc, client_state_vector)

    async def cleanup_document(self, material_id: str) -> None:
        """Remove document from memory after persisting."""
        if material_id in self.documents:
            await self.save_document_state(material_id)
            async with self._get_lock(material_id):
                del self.documents[material_id]
                self._last_activity.pop(material_id, None)
            logger.info(f"Cleaned up Y.js document: {material_id}")

    async def cleanup_inactive_documents(
        self,
        inactive_threshold: int = 600
    ) -> int:
        """Remove documents inactive for threshold seconds."""
        now = datetime.now(timezone.utc)
        to_cleanup: list[str] = []

        for material_id, last_activity in self._last_activity.items():
            delta = (now - last_activity).total_seconds()
            if delta > inactive_threshold:
                to_cleanup.append(material_id)

        for material_id in to_cleanup:
            await self.cleanup_document(material_id)

        if to_cleanup:
            logger.info(
                f"Cleaned up {len(to_cleanup)} inactive documents"
            )

        return len(to_cleanup)

    async def save_all_documents(self) -> int:
        """Save all active documents to Redis."""
        count = 0
        for material_id in list(self.documents.keys()):
            try:
                await self.save_document_state(material_id)
                count += 1
            except Exception as e:
                logger.error(
                    f"Failed to save document {material_id}: {e}",
                    exc_info=True
                )
        return count

    async def get_document_size(self, material_id: str) -> int:
        """Get document size in bytes."""
        doc = self.documents.get(material_id)
        if not doc:
            return 0

        state = Y.encode_state_as_update(doc)
        return len(state)

    async def get_active_document_ids(self) -> Iterable[str]:
        """Get list of active document IDs."""
        return self.documents.keys()
