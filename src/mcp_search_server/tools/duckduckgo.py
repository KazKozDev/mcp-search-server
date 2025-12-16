"""DuckDuckGo search implementation for MCP server."""
import asyncio
import hashlib
import json
import logging
import os
import random
import urllib.parse
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import aiohttp
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

from ..cache_store import get_cached_json, set_cached_json
from ..config_loader import (
    get_cache_ttl_seconds,
    get_dedupe_enabled,
    get_normalize_urls_enabled,
    get_results_max_per_domain,
    get_title_similarity_threshold,
)
from ..result_utils import dedupe_and_limit_results
from ..utils import with_rate_limit

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.join(os.path.expanduser("~"), ".mcp-search-cache")
CACHE_EXPIRATION = timedelta(hours=24)

if not os.path.exists(CACHE_DIR):
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
    except Exception as e:
        logger.error(f"Failed to create cache directory: {e}")

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]


def _contains_cyrillic(text: str) -> bool:
    return any("\u0400" <= ch <= "\u04FF" for ch in text)


def _default_region_for_query(query: str) -> str:
    return "ru-ru" if _contains_cyrillic(query) else "wt-wt"


def _accept_language_for_region(region: Optional[str], query: str) -> str:
    if (region and region.lower().startswith("ru")) or _contains_cyrillic(query):
        return "ru-RU,ru;q=0.9,en;q=0.7"
    return "en-US,en;q=0.9"


class DuckDuckGoSearcher:
    """Async DuckDuckGo searcher."""

    def __init__(self, use_cache: bool = True):
        self.use_cache = use_cache

    def get_random_user_agent(self) -> str:
        """Return a random User-Agent."""
        return random.choice(USER_AGENTS)

    def get_cache_path(self, cache_key: str) -> str:
        """Get the cache file path for a cache key."""
        query_hash = hashlib.md5(cache_key.encode()).hexdigest()
        return os.path.join(CACHE_DIR, f"{query_hash}.json")

    def get_cached_results(self, cache_key: str) -> Optional[List[Dict]]:
        """Get cached results if not expired."""
        if not self.use_cache:
            return None

        cache_path = self.get_cache_path(cache_key)
        if not os.path.exists(cache_path):
            return None

        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached_data = json.load(f)

            cached_time = datetime.fromisoformat(cached_data["timestamp"])
            if datetime.now() - cached_time > CACHE_EXPIRATION:
                logger.debug(f"Cache for '{cache_key}' has expired.")
                return None

            logger.info(f"Using cached results for '{cache_key}'")
            return cached_data["results"]
        except Exception as e:
            logger.warning(f"Error reading cache: {e}")
            return None

    def save_to_cache(self, cache_key: str, results: List[Dict]) -> None:
        """Save search results to cache."""
        if not self.use_cache or not results:
            return

        cache_path = self.get_cache_path(cache_key)
        try:
            cache_data = {
                "query": cache_key,
                "timestamp": datetime.now().isoformat(),
                "results": results,
            }
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            logger.debug(f"Results for '{cache_key}' saved to cache")
        except Exception as e:
            logger.warning(f"Error saving to cache: {e}")

    @with_rate_limit("duckduckgo")
    async def search(self, query: str, limit: int = 10, region: Optional[str] = None) -> List[Dict]:
        """Search DuckDuckGo for the given query."""
        effective_region = region or _default_region_for_query(query)

        cache_key = f"mode=web|region={effective_region}|q={query}"

        cached_results = self.get_cached_results(cache_key)
        if cached_results is not None:
            return cached_results[:limit]

        logger.info(f"Searching DuckDuckGo for: {query} (region={effective_region})")
        results = await self._search_html_version(query, effective_region)

        if not results:
            logger.info("HTML version failed, trying lite version")
            results = await self._search_lite_version(query, effective_region)

        if results:
            self.save_to_cache(cache_key, results)
        else:
            logger.warning(f"No results found for query: {query}")

        return results[:limit]

    async def _search_html_version(self, query: str, region: str) -> List[Dict]:
        """Search using the HTML version of DuckDuckGo."""
        encoded_query = urllib.parse.quote(query)
        encoded_region = urllib.parse.quote(region)
        url = f"https://duckduckgo.com/html/?q={encoded_query}&kl={encoded_region}"

        html_content = await self._make_request(url, accept_language=_accept_language_for_region(region, query))
        return self._extract_html_results(html_content) if html_content else []

    async def _search_lite_version(self, query: str, region: str) -> List[Dict]:
        """Search using the lite version of DuckDuckGo."""
        encoded_query = urllib.parse.quote(query)
        encoded_region = urllib.parse.quote(region)
        url = f"https://lite.duckduckgo.com/lite/?q={encoded_query}&kl={encoded_region}"

        html_content = await self._make_request(url, accept_language=_accept_language_for_region(region, query))
        return self._extract_lite_results(html_content) if html_content else []

    async def _make_request(
        self, url: str, max_retries: int = 3, accept_language: str = "en-US,en;q=0.9"
    ) -> Optional[str]:
        """Make an HTTP request with retries."""
        retry_count = 0

        while retry_count < max_retries:
            try:
                await asyncio.sleep(random.uniform(0.5, 1.5))
                user_agent = self.get_random_user_agent()
                headers = {
                    "User-Agent": user_agent,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": accept_language,
                    "Referer": "https://duckduckgo.com/",
                }

                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)
                    ) as response:
                        if response.status == 200:
                            text = await response.text()
                            if any(
                                term in text.lower()
                                for term in ["captcha", "blocked", "too many requests"]
                            ):
                                logger.warning("CAPTCHA or blocking detected. Retrying...")
                                retry_count += 1
                                await asyncio.sleep(2**retry_count + random.uniform(0.5, 1.5))
                                continue
                            return text
                        elif response.status == 429 or response.status >= 500:
                            logger.warning(f"Got status code {response.status}. Retrying...")
                            retry_count += 1
                            await asyncio.sleep(2**retry_count + random.uniform(0.5, 1.5))
                        else:
                            logger.error(f"Error: status code {response.status}")
                            return None

            except asyncio.TimeoutError:
                logger.warning(f"Request timeout for {url}")
                retry_count += 1
                await asyncio.sleep(2**retry_count)
            except Exception as e:
                logger.error(f"Request error for {url}: {e}")
                return None

        logger.error(f"Failed to make request to {url} after {max_retries} retries")
        return None

    def _extract_html_results(self, html_content: Optional[str]) -> List[Dict]:
        """Extract search results from HTML version."""
        if not html_content:
            return []
        results = []
        try:
            soup = BeautifulSoup(html_content, "html.parser")

            selectors_to_try = [
                "div.result",
                "div.results_links_deep",
                "div.web-result",
                "article.result",
            ]
            result_elements = []
            for selector in selectors_to_try:
                result_elements = soup.select(selector)
                if result_elements:
                    logger.debug(f"Found {len(result_elements)} results with: {selector}")
                    break

            if not result_elements:
                logger.warning("No result elements found")
                return []

            for result_container in result_elements:
                title_el = result_container.select_one("h2 a, a.result__a")
                snippet_el = result_container.select_one(".result__snippet, a.result__snippet")
                link_el = title_el

                if title_el and link_el:
                    title = title_el.get_text(strip=True)
                    raw_link = link_el.get("href")

                    if raw_link:
                        if "duckduckgo.com" in raw_link:
                            parsed_url = urllib.parse.urlparse(raw_link)
                            qs = urllib.parse.parse_qs(parsed_url.query)
                            link = qs.get("uddg", [""])[0] or qs.get("u", [""])[0]
                        else:
                            link = raw_link

                        snippet = snippet_el.get_text(strip=True) if snippet_el else ""

                        if title and link:
                            results.append({
                                "title": title,
                                "url": link,
                                "snippet": snippet,
                                "source": "duckduckgo"
                            })

        except Exception as e:
            logger.error(f"Error extracting HTML results: {e}")
        return results

    def _extract_lite_results(self, html_content: Optional[str]) -> List[Dict]:
        """Extract search results from the lite version."""
        if not html_content:
            return []
        results = []
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            rows = soup.select('tr')

            for row in rows:
                link_tag = row.find('a', href=True)
                if link_tag and link_tag.get_text(strip=True):
                    title = link_tag.get_text(strip=True)
                    link = link_tag['href']

                    if link.startswith("/") or "duckduckgo.com" in link:
                        continue

                    snippet_parts = [
                        td.get_text(strip=True) for td in row.find_all('td') if not td.find('a')
                    ]
                    snippet = " ".join(snippet_parts).strip()

                    if title and link:
                        results.append({
                            "title": title,
                            "url": link,
                            "snippet": snippet,
                            "source": "duckduckgo"
                        })

        except Exception as e:
            logger.error(f"Error extracting Lite results: {e}")
        return results


async def search_duckduckgo(
    query: str,
    limit: int = 10,
    timelimit: Optional[str] = None,
    mode: str = "web",
    region: Optional[str] = None,
    no_cache: bool = False,
) -> List[Dict]:
    """
    Search DuckDuckGo with optional time filter.

    Args:
        query: Search query
        limit: Maximum number of results
        timelimit: Time limit filter - 'd' (day), 'w' (week), 'm' (month), 'y' (year), None (all time)

    Returns:
        List of search results
    """
    effective_region = region or _default_region_for_query(query)
    cache_key = f"mode={mode}|region={effective_region}|timelimit={timelimit}|q={query}"

    # Check cache first
    cache_kind = "news" if mode == "news" else "web"
    cached_results = get_cached_json(cache_key, get_cache_ttl_seconds(cache_kind), no_cache=no_cache)
    if cached_results is not None:
        logger.info(f"Using cached results for '{cache_key}'")
        return cached_results[:limit]

    if mode == "news":
        try:
            logger.info(
                f"Searching DuckDuckGo News with library (timelimit={timelimit}, region={effective_region}): {query}"
            )
            results: List[Dict] = []
            with DDGS() as ddgs:
                search_results = ddgs.news(
                    query,
                    max_results=limit,
                    timelimit=timelimit,
                    region=effective_region,
                )
                for result in search_results:
                    results.append(
                        {
                            "title": result.get("title", ""),
                            "url": result.get("url", "")
                            or result.get("link", "")
                            or result.get("href", ""),
                            "snippet": result.get("body", "") or result.get("excerpt", ""),
                            "source": "duckduckgo_news",
                        }
                    )
            if get_dedupe_enabled():
                results = dedupe_and_limit_results(
                    results,
                    max_per_domain=get_results_max_per_domain(),
                    similarity_threshold=get_title_similarity_threshold(),
                    normalize_urls=get_normalize_urls_enabled(),
                )
            set_cached_json(cache_key, results, no_cache=no_cache)
            return results[:limit]
        except Exception as e:
            logger.warning(f"News library search failed, falling back to web HTML: {e}")

    # Try using the official library first if timelimit is specified (web mode)
    if timelimit and mode == "web":
        try:
            logger.info(
                f"Searching DuckDuckGo with library (timelimit={timelimit}, region={effective_region}): {query}"
            )
            results = []
            with DDGS() as ddgs:
                search_results = ddgs.text(
                    query, max_results=limit, timelimit=timelimit, region=effective_region
                )
                for result in search_results:
                    results.append({
                        "title": result.get("title", ""),
                        "url": result.get("href", ""),
                        "snippet": result.get("body", ""),
                        "source": "duckduckgo"
                    })
            if get_dedupe_enabled():
                results = dedupe_and_limit_results(
                    results,
                    max_per_domain=get_results_max_per_domain(),
                    similarity_threshold=get_title_similarity_threshold(),
                    normalize_urls=get_normalize_urls_enabled(),
                )
            set_cached_json(cache_key, results, no_cache=no_cache)
            return results[:limit]
        except Exception as e:
            logger.warning(f"Library search failed, falling back to HTML: {e}")

    # Fallback to HTML scraping
    searcher = DuckDuckGoSearcher(use_cache=False)
    results = await searcher.search(query, limit, region=effective_region)
    if get_dedupe_enabled():
        results = dedupe_and_limit_results(
            results,
            max_per_domain=get_results_max_per_domain(),
            similarity_threshold=get_title_similarity_threshold(),
            normalize_urls=get_normalize_urls_enabled(),
        )
    set_cached_json(cache_key, results, no_cache=no_cache)
    return results[:limit]
