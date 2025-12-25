"""Brave Search engine implementation."""

import asyncio
import logging
from typing import List, Dict, Optional
import httpx
from bs4 import BeautifulSoup

from .search_engine_base import SearchEngineBase

logger = logging.getLogger(__name__)

# Try to import browser engine
try:
    from .browser_engine import BrowserEngine, HAS_PLAYWRIGHT
except ImportError:
    HAS_PLAYWRIGHT = False
    logger.warning("Browser engine not available")


class BraveSearchEngine(SearchEngineBase):
    """Brave Search engine using browser rendering when available."""

    def __init__(self):
        super().__init__("brave")
        self.base_url = "https://search.brave.com/search"
        self.timeout = 10
        self.use_browser = HAS_PLAYWRIGHT

        if self.use_browser:
            from .browser_engine import BrowserEngine

            self.browser = BrowserEngine("brave", self.base_url)
            logger.info("Brave: Using Playwright browser rendering")
        else:
            self.browser = None
            logger.info("Brave: Using HTTP requests (may be blocked)")

    async def search(
        self,
        query: str,
        max_results: int = 10,
        timelimit: Optional[str] = None,
    ) -> Optional[List[Dict]]:
        """
        Search using Brave Search.

        Args:
            query: Search query
            max_results: Maximum number of results
            timelimit: Time filter ('d', 'w', 'm', 'y')

        Returns:
            List of search results or None if error
        """
        try:
            logger.info(f"Searching Brave for: {query} (browser={self.use_browser})")

            # Build URL parameters
            params = {"q": query, "source": "web"}

            # Add time filter if provided
            if timelimit:
                time_map = {
                    "d": "pd",  # past day
                    "w": "pw",  # past week
                    "m": "pm",  # past month
                    "y": "py",  # past year
                }
                if timelimit in time_map:
                    params["tf"] = time_map[timelimit]

            # Use browser rendering if available
            if self.use_browser and self.browser:
                # Build full URL
                from urllib.parse import urlencode

                url = f"{self.base_url}?{urlencode(params)}"

                # Fetch with browser
                html = await self.browser.search_with_browser(
                    url, wait_for_selector='div[data-type="web"]'
                )

                if not html:
                    logger.warning("Brave browser fetch failed")
                    return None

                # Parse results with updated selectors
                results = self._parse_browser_results(html, max_results)

            else:
                # Fallback to HTTP requests
                loop = asyncio.get_event_loop()
                results = await loop.run_in_executor(
                    None, self._search_sync, query, max_results, params
                )

            if not results:
                logger.warning(f"No Brave results found for: {query}")
                return None

            logger.info(f"Found {len(results)} Brave results for: {query}")
            return results

        except Exception as e:
            logger.error(f"Brave search error for '{query}': {e}")
            return None

    def _parse_browser_results(self, html: str, max_results: int) -> List[Dict]:
        """Parse Brave search results from browser-rendered HTML."""
        try:
            soup = BeautifulSoup(html, "html.parser")
            results = []

            # Find web result containers (data-type="web")
            web_results = soup.find_all("div", {"data-type": "web"}, limit=max_results)

            for div in web_results:
                try:
                    # Extract title - look for div with 'title' class
                    title_elem = div.find("div", class_=lambda x: x and "title" in str(x).lower())
                    if not title_elem:
                        continue
                    title = title_elem.get_text(strip=True)

                    # Extract URL - find first external link
                    url_elem = div.find("a", href=True)
                    if not url_elem or not url_elem.get("href"):
                        continue
                    url = url_elem["href"]

                    # Extract snippet/description
                    desc_elem = div.find(
                        "div", class_=lambda x: x and "description" in str(x).lower()
                    )
                    snippet = desc_elem.get_text(strip=True) if desc_elem else ""

                    # Skip if missing essential data
                    if not url or not title:
                        continue

                    results.append(
                        self.format_result(
                            title=title,
                            url=url,
                            snippet=snippet,
                        )
                    )

                except Exception as e:
                    logger.debug(f"Error parsing Brave browser result: {e}")
                    continue

            return results

        except Exception as e:
            logger.error(f"Error parsing Brave browser HTML: {e}")
            return []

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
            }

            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                response = client.get(self.base_url, params=params, headers=headers)
                response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            results = []

            # Find search result containers
            result_divs = soup.find_all("div", class_="snippet", limit=max_results)

            for div in result_divs:
                try:
                    # Extract title
                    title_elem = div.find("span", class_="snippet-title")
                    if not title_elem:
                        continue
                    title = title_elem.get_text(strip=True)

                    # Extract URL
                    url_elem = div.find("a", class_="result-header")
                    if not url_elem or not url_elem.get("href"):
                        continue
                    url = url_elem["href"]

                    # Extract snippet
                    snippet_elem = div.find("p", class_="snippet-description")
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                    results.append(
                        self.format_result(
                            title=title,
                            url=url,
                            snippet=snippet,
                        )
                    )

                except Exception as e:
                    logger.debug(f"Error parsing Brave result: {e}")
                    continue

            return results

        except Exception as e:
            logger.error(f"Brave sync search error: {e}")
            return []

    async def search_news(
        self,
        query: str,
        max_results: int = 10,
        timelimit: Optional[str] = None,
    ) -> Optional[List[Dict]]:
        """
        Search news using Brave.

        Args:
            query: Search query
            max_results: Maximum number of results
            timelimit: Time filter

        Returns:
            List of news results or None if error
        """
        try:
            logger.info(f"Searching Brave News for: {query}")

            params = {"q": query, "source": "news"}

            if timelimit:
                time_map = {"d": "pd", "w": "pw", "m": "pm"}
                if timelimit in time_map:
                    params["tf"] = time_map[timelimit]

            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None, self._search_news_sync, query, max_results, params
            )

            if not results:
                logger.warning(f"No Brave news found for: {query}")
                return None

            logger.info(f"Found {len(results)} Brave news for: {query}")
            return results

        except Exception as e:
            logger.error(f"Brave news search error for '{query}': {e}")
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
            news_divs = soup.find_all("div", class_="card", limit=max_results)

            for div in news_divs:
                try:
                    # Extract title
                    title_elem = div.find("a", class_="result-header")
                    if not title_elem:
                        continue
                    title = title_elem.get_text(strip=True)
                    url = title_elem.get("href", "")

                    # Extract snippet
                    snippet_elem = div.find("p", class_="snippet-description")
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                    # Extract source
                    source_elem = div.find("span", class_="netloc")
                    source_name = source_elem.get_text(strip=True) if source_elem else ""

                    results.append(
                        self.format_result(
                            title=title,
                            url=url,
                            snippet=snippet,
                            source_name=source_name,
                            source="brave_news",
                        )
                    )

                except Exception as e:
                    logger.debug(f"Error parsing Brave news result: {e}")
                    continue

            return results

        except Exception as e:
            logger.error(f"Brave news sync search error: {e}")
            return []
