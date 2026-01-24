from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CacheTTL:
    user_profile: int = 15 * 60
    session_metadata: int = 5 * 60
    team_member_list: int = 10 * 60
    embedding_results: int = 60 * 60
    search_results: int = 30 * 60


CACHE_TTLS = CacheTTL()
