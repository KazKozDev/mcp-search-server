"""RSS/Atom search tools."""

from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Any, Dict, List, Optional

import aiohttp
import feedparser

from ..cache_store import get_cached_json, set_cached_json
from ..config_loader import (
    get_cache_ttl_seconds,
    get_dedupe_enabled,
    get_normalize_urls_enabled,
    get_results_max_per_domain,
    get_rss_sources,
    get_title_similarity_threshold,
)
from ..result_utils import dedupe_and_limit_results

logger = logging.getLogger(__name__)


def _clean_html(text: str) -> str:
    if not text:
        return ""
    no_tags = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", no_tags).strip()


def _match_query(query: str, haystack: str) -> bool:
    q = (query or "").strip().lower()
    if not q:
        return False

    h = (haystack or "").lower()
    terms = [t for t in re.split(r"\s+", q) if t]
    return all(t in h for t in terms)


async def list_news_sources(
    region: Optional[str] = None, language: Optional[str] = None
) -> List[Dict[str, Any]]:
    """List RSS sources from config."""
    sources = get_rss_sources()
    output: List[Dict[str, Any]] = []

    for src in sources:
        if not isinstance(src, dict):
            continue
        if region and str(src.get("region", "")).lower() != region.lower():
            continue
        if language and str(src.get("language", "")).lower() != language.lower():
            continue
        output.append(
            {
                "id": str(src.get("id", "")),
                "name": str(src.get("name", "")),
                "url": str(src.get("url", "")),
                "region": str(src.get("region", "")),
                "language": str(src.get("language", "")),
            }
        )

    return output


async def _fetch_text(url: str, *, timeout_seconds: int = 10) -> Optional[str]:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=timeout_seconds)
            ) as resp:
                if resp.status != 200:
                    return None
                return await resp.text()
    except Exception as exc:
        logger.debug(f"RSS fetch failed for {url}: {exc}")
        return None


def _parse_feed(xml_text: str) -> feedparser.FeedParserDict:
    return feedparser.parse(xml_text)


async def search_rss(
    query: str,
    *,
    limit: int = 10,
    region: Optional[str] = None,
    sources: Optional[List[str]] = None,
    no_cache: bool = False,
) -> List[Dict[str, Any]]:
    """Search RSS/Atom feeds for a query.

    Args:
        query: Search query.
        limit: Maximum number of results.
        region: Optional region filter for sources.
        sources: Optional list of source IDs to search.
        no_cache: Disable cache.

    Returns:
        List of result dicts.
    """
    selected_sources = await list_news_sources(region=region)
    if sources:
        wanted = {s.lower() for s in sources}
        selected_sources = [s for s in selected_sources if s.get("id", "").lower() in wanted]

    ttl = get_cache_ttl_seconds("rss")
    cache_key = f"rss|region={region}|sources={','.join(sorted([s.get('id','') for s in selected_sources]))}|q={query}|limit={limit}"
    cached = get_cached_json(cache_key, ttl_seconds=ttl, no_cache=no_cache)
    if isinstance(cached, list):
        return cached[:limit]

    fetch_jobs: List[tuple[Dict[str, Any], asyncio.Task[Optional[str]]]] = []
    for src in selected_sources:
        url = str(src.get("url", ""))
        if not url:
            continue
        fetch_jobs.append((src, asyncio.create_task(_fetch_text(url))))

    raw_feeds = await asyncio.gather(*[task for _, task in fetch_jobs], return_exceptions=True)

    results: List[Dict[str, Any]] = []
    for (src, _), raw in zip(fetch_jobs, raw_feeds):
        if isinstance(raw, Exception) or not raw:
            continue

        loop = asyncio.get_event_loop()
        parsed = await loop.run_in_executor(None, _parse_feed, raw)
        entries = getattr(parsed, "entries", []) or []

        for entry in entries:
            title = str(entry.get("title", "")).strip()
            link = str(entry.get("link", "")).strip()
            summary = _clean_html(str(entry.get("summary", "")))

            if not title or not link:
                continue

            blob = f"{title} {summary}"
            if not _match_query(query, blob):
                continue

            published = str(entry.get("published", ""))
            published_ts: Optional[int] = None
            if entry.get("published_parsed"):
                try:
                    published_ts = int(time.mktime(entry["published_parsed"]))
                except Exception:
                    published_ts = None

            results.append(
                {
                    "title": title,
                    "url": link,
                    "snippet": summary,
                    "source": f"rss:{src.get('id','')}",
                    "published": published,
                    "published_ts": published_ts,
                }
            )

    results.sort(key=lambda r: (r.get("published_ts") or 0), reverse=True)

    if get_dedupe_enabled():
        results = dedupe_and_limit_results(
            results,
            max_per_domain=get_results_max_per_domain(),
            similarity_threshold=get_title_similarity_threshold(),
            normalize_urls=get_normalize_urls_enabled(),
        )

    set_cached_json(cache_key, results, no_cache=no_cache)
    return results[:limit]
