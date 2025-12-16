"""Result enrichment utilities (fetch previews for top results)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List

from .cache_store import get_cached_json, set_cached_json
from .config_loader import get_cache_ttl_seconds
from .tools.link_parser import extract_content_from_url
from .utils import with_rate_limit

logger = logging.getLogger(__name__)


def _preview_text(text: str, max_chars: int) -> str:
    if not text:
        return ""
    trimmed = text.strip()
    if len(trimmed) <= max_chars:
        return trimmed
    return trimmed[:max_chars].rstrip() + "..."


@with_rate_limit("web_parser")
async def _fetch_preview(url: str, *, max_chars: int, no_cache: bool) -> str:
    ttl = get_cache_ttl_seconds("enrich")
    cache_key = f"enrich|url={url}|max_chars={max_chars}"
    cached = get_cached_json(cache_key, ttl_seconds=ttl, no_cache=no_cache)
    if isinstance(cached, str) and cached:
        return cached

    content = await extract_content_from_url(url)
    if not content or content.startswith("Error"):
        return ""

    preview = _preview_text(content, max_chars=max_chars)
    if preview:
        set_cached_json(cache_key, preview, no_cache=no_cache)
    return preview


async def enrich_results(
    results: List[Dict[str, Any]],
    *,
    top_k: int = 3,
    max_chars: int = 600,
    no_cache: bool = False,
    max_concurrent: int = 3,
) -> List[Dict[str, Any]]:
    """Enrich top results with a `preview` field.

    Args:
        results: Result dicts containing at least `url`.
        top_k: How many top results to enrich.
        max_chars: Max preview size.
        no_cache: Disable cache.
        max_concurrent: Concurrency limit.

    Returns:
        New list of results with optional `preview`.
    """
    if top_k <= 0 or not results:
        return results

    semaphore = asyncio.Semaphore(max_concurrent)

    async def run_one(idx: int, url: str) -> tuple[int, str]:
        async with semaphore:
            try:
                preview = await _fetch_preview(url, max_chars=max_chars, no_cache=no_cache)
                return idx, preview
            except Exception as exc:
                logger.debug(f"Enrich failed for {url}: {exc}")
                return idx, ""

    jobs = []
    for idx, item in enumerate(results[:top_k]):
        url = str(item.get("url", ""))
        if not url:
            continue
        jobs.append(run_one(idx, url))

    previews = await asyncio.gather(*jobs, return_exceptions=False)

    out = [dict(r) for r in results]
    for idx, preview in previews:
        if preview:
            out[idx]["preview"] = preview

    return out
