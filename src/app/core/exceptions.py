from __future__ import annotations

from fastapi import HTTPException, status


class BioLoupeException(HTTPException):
    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST) -> None:
        super().__init__(status_code=status_code, detail=message)


class DatabaseException(BioLoupeException):
    pass


class VectorDBException(BioLoupeException):
    pass


class StorageException(BioLoupeException):
    pass


class CacheException(BioLoupeException):
    pass


class ResourceNotFound(BioLoupeException):
    def __init__(self, resource: str, resource_id: str) -> None:
        super().__init__(f"{resource} with id {resource_id} not found", status_code=404)


class PermissionDenied(BioLoupeException):
    def __init__(self, message: str = "Permission denied") -> None:
        super().__init__(message, status_code=403)


class TeamNotFound(ResourceNotFound):
    def __init__(self, team_id: str) -> None:
        super().__init__("Team", team_id)


class SessionNotFound(ResourceNotFound):
    def __init__(self, session_id: str) -> None:
        super().__init__("Session", session_id)


class MaterialNotFound(ResourceNotFound):
    def __init__(self, material_id: str) -> None:
        super().__init__("Material", material_id)


class InvitationExpired(BioLoupeException):
    def __init__(self) -> None:
        super().__init__("Invitation expired", status_code=400)


class InvitationInvalid(BioLoupeException):
    def __init__(self) -> None:
        super().__init__("Invalid invitation token", status_code=400)
