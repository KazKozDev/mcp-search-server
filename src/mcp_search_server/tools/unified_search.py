"""Unified search interface with smart fallback."""

import logging
from typing import List, Dict, Optional

from .search_manager import _search_manager

logger = logging.getLogger(__name__)

# Import cache utilities if available
try:
    from ..cache_store import get_cached_json, set_cached_json
    from ..config_loader import (
        get_cache_ttl_seconds,
        get_dedupe_enabled,
        get_normalize_urls_enabled,
        get_results_max_per_domain,
        get_title_similarity_threshold,
    )
    from ..result_utils import dedupe_and_limit_results

    HAS_CACHE = True
except ImportError:
    HAS_CACHE = False
    logger.warning("Cache utilities not available")


async def search_with_fallback(
    query: str,
    limit: int = 10,
    timelimit: Optional[str] = None,
    mode: str = "web",
    engine: Optional[str] = None,
    no_cache: bool = False,
    use_fallback: bool = True,
) -> List[Dict]:
    """
    Unified search with smart fallback and caching.

    Args:
        query: Search query
        limit: Maximum number of results
        timelimit: Time limit filter ('d', 'w', 'm', 'y')
        mode: Search mode (web or news)
        engine: Specific engine to use (None = auto with fallback)
        no_cache: Disable caching
        use_fallback: Enable fallback to other engines if primary fails

    Returns:
        List of search results
    """
    # Build cache key
    cache_key = f"engine={engine or 'auto'}|mode={mode}|timelimit={timelimit}|q={query}"

    # Check cache first
    if HAS_CACHE and not no_cache:
        cache_kind = "news" if mode == "news" else "web"
        cached_results = get_cached_json(
            cache_key, get_cache_ttl_seconds(cache_kind), no_cache=no_cache
        )
        if cached_results is not None:
            logger.info(f"Using cached results for '{cache_key}'")
            return cached_results[:limit]

    # Perform search
    if engine:
        # Use specific engine without fallback
        logger.info(f"Using specific engine: {engine}")
        results = await _search_manager.search_with_engine(
            query=query,
            engine=engine,
            max_results=limit * 2,  # Request more for deduplication
            timelimit=timelimit,
            mode=mode,
        )
    elif use_fallback:
        # Use smart fallback
        logger.info("Using smart fallback search")
        results = await _search_manager.search(
            query=query,
            max_results=limit * 2,  # Request more for deduplication
            timelimit=timelimit,
            mode=mode,
        )
    else:
        # Default to DuckDuckGo only (backward compatible)
        logger.info("Using DuckDuckGo only (no fallback)")
        results = await _search_manager.search_with_engine(
            query=query,
            engine="duckduckgo",
            max_results=limit * 2,
            timelimit=timelimit,
            mode=mode,
        )

    if not results:
        logger.warning(f"No results found for query: '{query}'")
        return []

    # Apply deduplication if enabled
    if HAS_CACHE and get_dedupe_enabled():
        results = dedupe_and_limit_results(
            results,
            max_per_domain=get_results_max_per_domain(),
            similarity_threshold=get_title_similarity_threshold(),
            normalize_urls=get_normalize_urls_enabled(),
        )

    # Cache results
    if HAS_CACHE and not no_cache:
        set_cached_json(cache_key, results, no_cache=no_cache)

    return results[:limit]
