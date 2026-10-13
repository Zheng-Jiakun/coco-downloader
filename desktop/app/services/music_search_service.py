# coding: utf-8
from app.models.music import MusicItem

from .providers import get_provider


def search_music(keyword: str, platform: str, limit: int = 20, offset: int = 0) -> list[MusicItem]:
    """Search music from the selected provider."""
    query = keyword.strip()
    if not query:
        return []

    provider = get_provider(platform)
    return provider.search(query, limit=limit, offset=offset)
