from __future__ import annotations

import json
from typing import Optional
from app.db.redis_client import get_redis
from app.schemas.task_schemas import TaskProgress, TaskStatus, TaskResult


class TaskService:
    def __init__(self):
        self._redis = get_redis()

    async def set_progress(self, task_id: str, current: int, total: int, message: Optional[str] = None) -> bool:
        key = f"task:progress:{task_id}"
        payload = TaskProgress(task_id=task_id, status="PROGRESS", current=current, total=total, message=message).dict()
        await self._redis.set(key, json.dumps(payload))
        return True

    async def get_progress(self, task_id: str) -> Optional[TaskProgress]:
        key = f"task:progress:{task_id}"
        val = await self._redis.get(key)
        if not val:
            return None
        data = json.loads(val)
        return TaskProgress(**data)

    async def set_result(self, task_id: str, result: dict) -> bool:
        key = f"task:result:{task_id}"
        payload = TaskResult(task_id=task_id, status="COMPLETED", result=result).dict()
        await self._redis.set(key, json.dumps(payload))
        return True

    async def get_result(self, task_id: str) -> Optional[TaskResult]:
        key = f"task:result:{task_id}"
        val = await self._redis.get(key)
        if not val:
            return None
        data = json.loads(val)
        return TaskResult(**data)

    async def set_status(self, task_id: str, status: str, message: Optional[str] = None) -> bool:
        key = f"task:status:{task_id}"
        payload = TaskStatus(task_id=task_id, status=status, message=message).dict()
        await self._redis.set(key, json.dumps(payload))
        return True

    async def get_status(self, task_id: str) -> Optional[TaskStatus]:
        key = f"task:status:{task_id}"
        val = await self._redis.get(key)
        if not val:
            return None
        data = json.loads(val)
        return TaskStatus(**data)
