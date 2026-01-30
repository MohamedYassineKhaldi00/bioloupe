from __future__ import annotations

from pydantic import BaseModel
from typing import Optional


class TaskStatus(BaseModel):
    task_id: str
    status: str
    message: Optional[str] = None


class TaskProgress(BaseModel):
    task_id: str
    status: str
    current: int
    total: int
    message: Optional[str] = None


class TaskResult(BaseModel):
    task_id: str
    status: str
    result: Optional[dict] = None
