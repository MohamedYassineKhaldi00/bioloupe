from __future__ import annotations

import os
from ...app.core.exceptions import StorageException
from ...app.core.storage_config import STORAGE_LIMITS
from ...app.models.material import MaterialType

ALLOWED_TYPES: dict[MaterialType, dict[str, set[str]]] = {
    MaterialType.paper: {
        "extensions": {".pdf"},
        "content_types": {"application/pdf"},
    },
    MaterialType.sequence: {
        "extensions": {".fasta", ".fa", ".fna", ".gb", ".gbk"},
        "content_types": {
            "application/octet-stream",
            "text/plain",
            "chemical/seq-na-fasta",
        },
    },
    MaterialType.image: {
        "extensions": {".png", ".jpg", ".jpeg", ".tif", ".tiff"},
        "content_types": {"image/png", "image/jpeg", "image/tiff"},
    },
    MaterialType.experiment: {
        "extensions": {".csv", ".tsv", ".xlsx"},
        "content_types": {
            "text/csv",
            "text/tab-separated-values",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        },
    },
    MaterialType.note: {
        "extensions": {".md", ".txt"},
        "content_types": {"text/markdown", "text/plain"},
    },
}


def validate_file(filename: str, content_type: str, size_bytes: int, material_type: MaterialType) -> None:
    if size_bytes > STORAGE_LIMITS.max_file_size_bytes:
        raise StorageException("File exceeds maximum size")

    ext = os.path.splitext(filename)[1].lower()
    allowed = ALLOWED_TYPES.get(material_type)
    if not allowed:
        raise StorageException("Unsupported material type")

    if ext not in allowed["extensions"]:
        raise StorageException("Invalid file extension for material type")

    if content_type not in allowed["content_types"]:
        raise StorageException("Invalid content type for material type")
