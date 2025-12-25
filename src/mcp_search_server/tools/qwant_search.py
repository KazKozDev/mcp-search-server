"""Qwant Search engine implementation (European search engine, API-like endpoint)."""

import asyncio
import logging
from typing import List, Dict, Optional
import httpx

from .search_engine_base import SearchEngineBase

logger = logging.getLogger(__name__)


class QwantSearchEngine(SearchEngineBase):
    """Qwant Search engine using their quasi-public API."""

    def __init__(self):
        super().__init__("qwant")
        self.base_url = "https://api.qwant.com/v3/search/web"
        self.news_url = "https://api.qwant.com/v3/search/news"
        self.timeout = 10

    async def search(
        self,
        query: str,
        max_results: int = 10,
        timelimit: Optional[str] = None,
    ) -> Optional[List[Dict]]:
        """
        Search using Qwant.

        Args:
            query: Search query
            max_results: Maximum number of results
            timelimit: Time filter (not fully supported by Qwant)

        Returns:
            List of search results or None if error
        """
        try:
            logger.info(f"Searching Qwant for: {query}")

            # Build URL parameters
            params = {
                "q": query,
                "count": min(max_results, 50),  # Qwant max is 50
                "locale": "en_US",
                "offset": 0,
                "device": "desktop",
            }

            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None, self._search_sync, query, max_results, params
            )

            if not results:
                logger.warning(f"No Qwant results found for: {query}")
                return None

            logger.info(f"Found {len(results)} Qwant results for: {query}")
            return results

        except Exception as e:
            logger.error(f"Qwant search error for '{query}': {e}")
            return None

    def _search_sync(self, query: str, max_results: int, params: Dict) -> List[Dict]:
        """Synchronous search (called in executor)."""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.qwant.com/",
                "Origin": "https://www.qwant.com",
            }

            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                response = client.get(self.base_url, params=params, headers=headers)
                response.raise_for_status()
                data = response.json()

            results = []

            # Parse Qwant API response
            if "data" in data and "result" in data["data"]:
                items = data["data"]["result"].get("items", [])

                for item in items[:max_results]:
                    try:
                        title = item.get("title", "")
                        url = item.get("url", "")
                        desc = item.get("desc", "")

                        if url and title:
                            results.append(
                                self.format_result(
                                    title=title,
                                    url=url,
                                    snippet=desc,
                                )
                            )

                    except Exception as e:
                        logger.debug(f"Error parsing Qwant result: {e}")
                        continue

            return results

        except Exception as e:
            logger.error(f"Qwant sync search error: {e}")
            return []

    async def search_news(
        self,
        query: str,
        max_results: int = 10,
        timelimit: Optional[str] = None,
    ) -> Optional[List[Dict]]:
        """
        Search news using Qwant.

        Args:
            query: Search query
            max_results: Maximum number of results
            timelimit: Time filter

        Returns:
            List of news results or None if error
        """
        try:
            logger.info(f"Searching Qwant News for: {query}")

            params = {
                "q": query,
                "count": min(max_results, 50),
                "locale": "en_US",
                "offset": 0,
            }

            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None, self._search_news_sync, query, max_results, params
            )

            if not results:
                logger.warning(f"No Qwant news found for: {query}")
                return None

            logger.info(f"Found {len(results)} Qwant news for: {query}")
            return results

        except Exception as e:
            logger.error(f"Qwant news search error for '{query}': {e}")
            return None

    def _search_news_sync(self, query: str, max_results: int, params: Dict) -> List[Dict]:
        """Synchronous news search."""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.qwant.com/",
                "Origin": "https://www.qwant.com",
            }

            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                response = client.get(self.news_url, params=params, headers=headers)
                response.raise_for_status()
                data = response.json()

            results = []

            # Parse Qwant News API response
            if "data" in data and "result" in data["data"]:
                items = data["data"]["result"].get("items", [])

                for item in items[:max_results]:
                    try:
                        title = item.get("title", "")
                        url = item.get("url", "")
                        desc = item.get("desc", "")
                        date = item.get("date", "")
                        media = item.get("media", "")

                        if url and title:
                            results.append(
                                self.format_result(
                                    title=title,
                                    url=url,
                                    snippet=desc,
                                    date=date,
                                    source_name=media,
                                    source="qwant_news",
                                )
                            )

                    except Exception as e:
                        logger.debug(f"Error parsing Qwant news result: {e}")
                        continue

            return results

        except Exception as e:
            logger.error(f"Qwant news sync search error: {e}")
            return []
