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
