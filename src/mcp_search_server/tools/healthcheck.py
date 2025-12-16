"""Healthcheck tool for external providers."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict

from .duckduckgo import search_duckduckgo
from .link_parser import extract_content_from_url
from .rss_tool import list_news_sources, search_rss
from .wikipedia import search_wikipedia

logger = logging.getLogger(__name__)


async def healthcheck() -> Dict[str, Any]:
    """Run a lightweight healthcheck across providers."""

    async def _safe(name: str, coro, timeout: float = 12.0):
        try:
            result = await asyncio.wait_for(coro, timeout=timeout)
            return {"ok": True, "result": result}
        except Exception as exc:
            logger.debug(f"Healthcheck step {name} failed: {exc}")
            return {"ok": False, "error": str(exc)}

    checks: Dict[str, Any] = {}

    checks["duckduckgo_web"] = await _safe(
        "duckduckgo_web", search_duckduckgo("test", limit=1, mode="web", timelimit="d")
    )
    checks["duckduckgo_news"] = await _safe(
        "duckduckgo_news", search_duckduckgo("test", limit=1, mode="news", timelimit="d")
    )
    checks["wikipedia"] = await _safe("wikipedia", search_wikipedia("Python", limit=1))

    sources = await _safe("rss_sources", list_news_sources(region=None))
    checks["rss_sources"] = sources

    if sources.get("ok") and isinstance(sources.get("result"), list) and sources["result"]:
        checks["rss_search"] = await _safe(
            "rss_search", search_rss("test", limit=1, sources=[sources["result"][0]["id"]])
        )
    else:
        checks["rss_search"] = {"ok": False, "error": "No RSS sources configured"}

    checks["extract_webpage_content"] = await _safe(
        "extract_webpage_content", extract_content_from_url("https://example.com")
    )

    checks["overall_ok"] = all(
        isinstance(v, dict) and v.get("ok") for k, v in checks.items() if k != "overall_ok"
    )
    return checks
