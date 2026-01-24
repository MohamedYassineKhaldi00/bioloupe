from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StorageBuckets:
    papers: str = "bioloupe-papers"
    sequences: str = "bioloupe-sequences"
    images: str = "bioloupe-images"
    experimental_data: str = "bioloupe-experimental-data"
    temp: str = "bioloupe-temp"


@dataclass(frozen=True)
class StorageLimits:
    max_file_size_bytes: int = 500 * 1024 * 1024
    multipart_threshold_bytes: int = 100 * 1024 * 1024
    multipart_part_size_bytes: int = 10 * 1024 * 1024
    presign_expiry_seconds: int = 24 * 60 * 60


STORAGE_BUCKETS = StorageBuckets()
STORAGE_LIMITS = StorageLimits()
