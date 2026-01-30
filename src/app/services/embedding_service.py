from __future__ import annotations

import numpy as np
from typing import Optional


class EmbeddingService:
    async def embed_paper(self, title: str, abstract: Optional[str], full_text: Optional[str]) -> np.ndarray:
        # Default placeholder embedding (deterministic zeros) — intended to be overridden by real provider adapter
        return np.zeros(768, dtype=float)

    async def embed_sequence(self, sequence: str, sequence_type: str) -> np.ndarray:
        return np.zeros(768, dtype=float)

    async def embed_image(self, image_bytes: bytes) -> np.ndarray:
        return np.zeros(768, dtype=float)

    async def embed_text(self, text: str) -> np.ndarray:
        return np.zeros(768, dtype=float)
