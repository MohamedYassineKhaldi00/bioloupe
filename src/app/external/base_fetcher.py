from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from typing import List, Dict, Any, Optional
import httpx

class BaseFetcher(ABC):
    def __init__(
        self,
        base_url: str,
        rate_limit: float,
        timeout: int = 30,
        max_retries: int = 3
    ):
        self.base_url = base_url
        self.rate_limit = rate_limit
        self.timeout = timeout
        self.max_retries = max_retries
        self.client = httpx.AsyncClient(timeout=timeout)
        self._last_request_time = 0.0

    async def _rate_limited_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        await self._wait_for_rate_limit()

        for attempt in range(self.max_retries):
            try:
                response = await self.client.request(method, url, **kwargs)
                response.raise_for_status()
                return response
            except httpx.HTTPError:
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)
            except Exception:
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)

        raise Exception("Max retries exceeded")

    async def _wait_for_rate_limit(self):
        loop = asyncio.get_event_loop()
        current_time = loop.time()
        time_since_last = current_time - self._last_request_time

        if time_since_last < self.rate_limit:
            await asyncio.sleep(self.rate_limit - time_since_last)

        self._last_request_time = loop.time()

    @abstractmethod
    async def search(
        self,
        query: str,
        start_date: Optional[Any] = None,
        end_date: Optional[Any] = None,
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def fetch_by_id(self, publication_id: str) -> Dict[str, Any]:
        pass

    async def close(self):
        await self.client.aclose()
