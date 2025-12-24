"""Enhanced DuckDuckGo search implementation using duckduckgo_search library."""

import asyncio
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Import cache and config utilities
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


def _contains_cyrillic(text: str) -> bool:
    """Check if text contains Cyrillic characters."""
    return any("\u0400" <= ch <= "\u04ff" for ch in text)


def _default_region_for_query(query: str) -> str:
    """Determine default region based on query."""
    return "ru-ru" if _contains_cyrillic(query) else "wt-wt"


class DuckDuckGoSearchTool:
    """Enhanced DuckDuckGo search tool with anti-blocking features"""

    def __init__(self, proxy: str = None):
        """
        Initialize DuckDuckGo search tool

        Args:
            proxy: Optional proxy (http/https/socks5)
        """
        try:
            from ddgs import DDGS
            self.DDGS = DDGS
            self.available = True
        except ImportError:
            # Try old package name for backwards compatibility
            try:
                from duckduckgo_search import DDGS
                self.DDGS = DDGS
                self.available = True
                logger.warning("Using deprecated duckduckgo_search. Please upgrade to ddgs package.")
            except ImportError:
                logger.warning("ddgs package not installed. DDG tool disabled.")
                self.available = False
                return

        self.proxy = proxy

    async def search(self, query: str, max_results: int = 10, region: str = "us-en",
                     timelimit: str = None, safesearch: str = "moderate") -> Optional[List[Dict]]:
        """
        Search DuckDuckGo

        Args:
            query: Search query
            max_results: Maximum number of results
            region: Region code (e.g., 'us-en', 'uk-en', 'ru-ru')
            timelimit: Time filter ('d' day, 'w' week, 'm' month, 'y' year)
            safesearch: Safe search level ('on', 'moderate', 'off')

        Returns:
            List of search results or None if error
        """
        if not self.available:
            logger.error("DuckDuckGo tool not available")
            return None

        try:
            logger.info(f"Searching DuckDuckGo for: {query} (region: {region})")

            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                self._search_sync,
                query,
                max_results,
                region,
                safesearch,
                timelimit
            )

            if not results:
                logger.warning(f"No DuckDuckGo results found for: {query}")
                return None

            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    'title': result.get('title', ''),
                    'url': result.get('href', ''),
                    'snippet': result.get('body', ''),
                    'source': 'duckduckgo'
                })

            logger.info(f"Found {len(formatted_results)} DuckDuckGo results for: {query}")
            return formatted_results

        except Exception as e:
            logger.error(f"DuckDuckGo search error for '{query}': {e}")
            return None

    def _search_sync(self, query: str, max_results: int, region: str,
                     safesearch: str, timelimit: str = None) -> List[Dict]:
        """Synchronous search (called in executor)"""
        try:
            with self.DDGS(proxy=self.proxy, timeout=10) as ddgs:
                results = list(ddgs.text(
                    query,
                    region=region,
                    safesearch=safesearch,
                    timelimit=timelimit,
                    max_results=max_results
                ))
            return results
        except Exception as e:
            logger.error(f"DDG sync search error: {e}")
            # Fallback without region
            try:
                with self.DDGS(proxy=self.proxy, timeout=10) as ddgs:
                    return list(ddgs.text(query, max_results=max_results))
            except:
                return []

    async def search_news(self, query: str, max_results: int = 10,
                          region: str = "us-en", timelimit: str = "m") -> Optional[List[Dict]]:
        """
        Search DuckDuckGo News

        Args:
            query: Search query
            max_results: Maximum number of results
            region: Region code
            timelimit: Time filter ('d', 'w', 'm')

        Returns:
            List of news results or None if error
        """
        if not self.available:
            return None

        try:
            logger.info(f"Searching DuckDuckGo News for: {query}")

            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                self._search_news_sync,
                query,
                max_results,
                region,
                timelimit
            )

            if not results:
                logger.warning(f"No DuckDuckGo news found for: {query}")
                return None

            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    'title': result.get('title', ''),
                    'url': result.get('url', ''),
                    'snippet': result.get('body', ''),
                    'date': result.get('date', ''),
                    'source_name': result.get('source', ''),
                    'source': 'duckduckgo_news'
                })

            logger.info(f"Found {len(formatted_results)} DuckDuckGo news for: {query}")
            return formatted_results

        except Exception as e:
            logger.error(f"DuckDuckGo news search error for '{query}': {e}")
            return None

    def _search_news_sync(self, query: str, max_results: int, region: str, timelimit: str) -> List[Dict]:
        """Synchronous news search (called in executor)"""
        try:
            with self.DDGS(proxy=self.proxy, timeout=10) as ddgs:
                results = list(ddgs.news(
                    query,
                    region=region,
                    timelimit=timelimit,
                    max_results=max_results
                ))
            return results
        except Exception as e:
            logger.error(f"DDG news sync search error: {e}")
            return []


# Global instance
_ddg_tool = DuckDuckGoSearchTool()


# Main search function with caching
async def search_duckduckgo(
    query: str,
    limit: int = 10,
    timelimit: Optional[str] = None,
    mode: str = "web",
    region: Optional[str] = None,
    no_cache: bool = False,
) -> List[Dict]:
    """
    Search DuckDuckGo with caching support.

    Args:
        query: Search query
        limit: Maximum number of results
        timelimit: Time limit filter ('d', 'w', 'm', 'y')
        mode: Search mode (web or news)
        region: Region for search
        no_cache: Disable caching

    Returns:
        List of search results
    """
    effective_region = region or _default_region_for_query(query)
    cache_key = f"mode={mode}|region={effective_region}|timelimit={timelimit}|q={query}"

    # Check cache first
    if HAS_CACHE:
        cache_kind = "news" if mode == "news" else "web"
        cached_results = get_cached_json(
            cache_key, get_cache_ttl_seconds(cache_kind), no_cache=no_cache
        )
        if cached_results is not None:
            logger.info(f"Using cached results for '{cache_key}'")
            return cached_results[:limit]

    # Perform search
    if mode == "news":
        results = await _ddg_tool.search_news(query, limit, effective_region, timelimit or "m")
    else:
        results = await _ddg_tool.search(query, limit, effective_region, timelimit)

    if not results:
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
    if HAS_CACHE:
        set_cached_json(cache_key, results, no_cache=no_cache)

    return results[:limit]
