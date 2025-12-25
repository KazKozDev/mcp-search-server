"""Startpage Search engine implementation (Google proxy)."""

import asyncio
import logging
from typing import List, Dict, Optional
import httpx
from bs4 import BeautifulSoup

from .search_engine_base import SearchEngineBase

logger = logging.getLogger(__name__)


class StartpageSearchEngine(SearchEngineBase):
    """Startpage Search engine (privacy-focused Google proxy)."""

    def __init__(self):
        super().__init__("startpage")
        self.base_url = "https://www.startpage.com/sp/search"
        self.timeout = 10

    async def search(
        self,
        query: str,
        max_results: int = 10,
        timelimit: Optional[str] = None,
    ) -> Optional[List[Dict]]:
        """
        Search using Startpage.

        Args:
            query: Search query
            max_results: Maximum number of results
            timelimit: Time filter ('d', 'w', 'm', 'y')

        Returns:
            List of search results or None if error
        """
        try:
            logger.info(f"Searching Startpage for: {query}")

            # Build URL parameters
            params = {
                "query": query,
                "cat": "web",
                "language": "english",
            }

            # Add time filter if provided
            if timelimit:
                time_map = {
                    "d": "day",
                    "w": "week",
                    "m": "month",
                    "y": "year",
                }
                if timelimit in time_map:
                    params["with_date"] = time_map[timelimit]

            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None, self._search_sync, query, max_results, params
            )

            if not results:
                logger.warning(f"No Startpage results found for: {query}")
                return None

            logger.info(f"Found {len(results)} Startpage results for: {query}")
            return results

        except Exception as e:
            logger.error(f"Startpage search error for '{query}': {e}")
            return None

    def _search_sync(self, query: str, max_results: int, params: Dict) -> List[Dict]:
        """Synchronous search (called in executor)."""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
            }

            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                response = client.get(self.base_url, params=params, headers=headers)
                response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            results = []

            # Find search result containers
            # Startpage uses various class names
            result_divs = soup.find_all("div", class_=lambda x: x and "w-gl__result" in x)

            if not result_divs:
                # Try alternative selectors
                result_divs = soup.find_all("div", class_="result")

            for div in result_divs[:max_results]:
                try:
                    # Extract title and URL
                    title_elem = div.find("a", class_=lambda x: x and "w-gl__result-title" in x)
                    if not title_elem:
                        title_elem = div.find("h3")
                        if title_elem:
                            title_elem = title_elem.find("a")

                    if not title_elem:
                        continue

                    title = title_elem.get_text(strip=True)
                    url = title_elem.get("href", "")

                    # Extract snippet
                    snippet_elem = div.find("p", class_=lambda x: x and "w-gl__description" in x)
                    if not snippet_elem:
                        snippet_elem = div.find("p", class_="description")

                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                    if url and title:
                        results.append(
                            self.format_result(
                                title=title,
                                url=url,
                                snippet=snippet,
                            )
                        )

                except Exception as e:
                    logger.debug(f"Error parsing Startpage result: {e}")
                    continue

            return results

        except Exception as e:
            logger.error(f"Startpage sync search error: {e}")
            return []

    async def search_news(
        self,
        query: str,
        max_results: int = 10,
        timelimit: Optional[str] = None,
    ) -> Optional[List[Dict]]:
        """
        Search news using Startpage.

        Args:
            query: Search query
            max_results: Maximum number of results
            timelimit: Time filter

        Returns:
            List of news results or None if error
        """
        try:
            logger.info(f"Searching Startpage News for: {query}")

            params = {
                "query": query,
                "cat": "news",
                "language": "english",
            }

            if timelimit:
                time_map = {"d": "day", "w": "week", "m": "month"}
                if timelimit in time_map:
                    params["with_date"] = time_map[timelimit]

            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None, self._search_news_sync, query, max_results, params
            )

            if not results:
                logger.warning(f"No Startpage news found for: {query}")
                return None

            logger.info(f"Found {len(results)} Startpage news for: {query}")
            return results

        except Exception as e:
            logger.error(f"Startpage news search error for '{query}': {e}")
            return None

    def _search_news_sync(self, query: str, max_results: int, params: Dict) -> List[Dict]:
        """Synchronous news search."""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }

            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                response = client.get(self.base_url, params=params, headers=headers)
                response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            results = []

            # Find news result containers
            news_divs = soup.find_all("div", class_="result")

            for div in news_divs[:max_results]:
                try:
                    # Extract title and URL
                    title_elem = div.find("h3")
                    if title_elem:
                        title_elem = title_elem.find("a")

                    if not title_elem:
                        continue

                    title = title_elem.get_text(strip=True)
                    url = title_elem.get("href", "")

                    # Extract snippet
                    snippet_elem = div.find("p", class_="description")
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                    # Extract source
                    source_elem = div.find("span", class_="source")
                    source_name = source_elem.get_text(strip=True) if source_elem else ""

                    if url and title:
                        results.append(
                            self.format_result(
                                title=title,
                                url=url,
                                snippet=snippet,
                                source_name=source_name,
                                source="startpage_news",
                            )
                        )

                except Exception as e:
                    logger.debug(f"Error parsing Startpage news result: {e}")
                    continue

            return results

        except Exception as e:
            logger.error(f"Startpage news sync search error: {e}")
            return []
