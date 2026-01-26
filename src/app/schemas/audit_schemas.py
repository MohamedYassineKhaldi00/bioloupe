from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from ...app.models.audit_log import AuditAction, ResourceType


class AuditLogResponse(BaseModel):
    id: uuid.UUID
    timestamp: datetime
    user_id: uuid.UUID | None
    ip_address: str
    user_agent: str | None
    action: AuditAction
    resource_type: ResourceType
    resource_id: str
    success: bool
    details: dict[str, Any] | None
    correlation_id: str

    model_config = {"from_attributes": True}


class AuditLogQueryParams(BaseModel):
    start_date: datetime | None = Field(None, description="Start date filter")
    end_date: datetime | None = Field(None, description="End date filter")
    user_id: uuid.UUID | None = Field(None, description="Filter by user ID")
    action: AuditAction | None = Field(None, description="Filter by action")
    resource_type: ResourceType | None = Field(
        None, description="Filter by resource type"
    )
    resource_id: str | None = Field(None, description="Filter by resource ID")
    success: bool | None = Field(None, description="Filter by success status")
    ip_address: str | None = Field(None, description="Filter by IP address")
    limit: int = Field(100, ge=1, le=1000, description="Maximum results")
    offset: int = Field(0, ge=0, description="Pagination offset")


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    total: int
    limit: int
    offset: int


class AuditExportFormat(str):
    JSON = "json"
    CSV = "csv"


class AuditExportRequest(BaseModel):
    format: str = Field(
        AuditExportFormat.JSON, description="Export format (json or csv)"
    )
    start_date: datetime | None = Field(None, description="Start date filter")
    end_date: datetime | None = Field(None, description="End date filter")
    user_id: uuid.UUID | None = Field(None, description="Filter by user ID")
    action: AuditAction | None = Field(None, description="Filter by action")
    resource_type: ResourceType | None = Field(
        None, description="Filter by resource type"
    )
    include_details: bool = Field(
        True, description="Include details in export"
    )
