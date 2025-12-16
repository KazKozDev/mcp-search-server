"""DuckDuckGo vertical searches (images/videos)."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from duckduckgo_search import DDGS

from ..cache_store import get_cached_json, set_cached_json
from ..config_loader import get_cache_ttl_seconds

logger = logging.getLogger(__name__)


async def search_images(
    query: str,
    *,
    limit: int = 10,
    region: Optional[str] = None,
    safesearch: str = "moderate",
    no_cache: bool = False,
) -> List[Dict[str, Any]]:
    """Search images using DuckDuckGo via ddg library."""
    ttl = get_cache_ttl_seconds("web")
    cache_key = f"ddg_images|q={query}|limit={limit}|region={region}|safesearch={safesearch}"
    cached = get_cached_json(cache_key, ttl_seconds=ttl, no_cache=no_cache)
    if isinstance(cached, list):
        return cached[:limit]

    results: List[Dict[str, Any]] = []
    try:
        with DDGS() as ddgs:
            items = ddgs.images(
                query,
                max_results=limit,
                region=region,
                safesearch=safesearch,
            )
            for item in items:
                results.append(
                    {
                        "title": item.get("title", ""),
                        "url": item.get("url", "") or item.get("image", ""),
                        "snippet": item.get("source", ""),
                        "image": item.get("image", ""),
                        "thumbnail": item.get("thumbnail", ""),
                        "source": "duckduckgo_images",
                    }
                )
    except Exception as exc:
        logger.debug(f"DDG images search failed: {exc}")
        return []

    set_cached_json(cache_key, results, no_cache=no_cache)
    return results[:limit]


async def search_videos(
    query: str,
    *,
    limit: int = 10,
    region: Optional[str] = None,
    timelimit: Optional[str] = None,
    safesearch: str = "moderate",
    no_cache: bool = False,
) -> List[Dict[str, Any]]:
    """Search videos using DuckDuckGo via ddg library."""
    ttl = get_cache_ttl_seconds("web")
    cache_key = f"ddg_videos|q={query}|limit={limit}|region={region}|timelimit={timelimit}|safesearch={safesearch}"
    cached = get_cached_json(cache_key, ttl_seconds=ttl, no_cache=no_cache)
    if isinstance(cached, list):
        return cached[:limit]

    results: List[Dict[str, Any]] = []
    try:
        with DDGS() as ddgs:
            items = ddgs.videos(
                query,
                max_results=limit,
                region=region,
                timelimit=timelimit,
                safesearch=safesearch,
            )
            for item in items:
                results.append(
                    {
                        "title": item.get("title", ""),
                        "url": item.get("content", "") or item.get("href", ""),
                        "snippet": item.get("description", "") or item.get("publisher", ""),
                        "duration": item.get("duration", ""),
                        "published": item.get("published", ""),
                        "source": "duckduckgo_videos",
                    }
                )
    except Exception as exc:
        logger.debug(f"DDG videos search failed: {exc}")
        return []

    set_cached_json(cache_key, results, no_cache=no_cache)
    return results[:limit]
