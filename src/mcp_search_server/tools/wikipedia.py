"""Wikipedia search implementation for MCP server."""

import logging
import re
from typing import Dict, List, Any
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)


class WikipediaTool:
    """Tool for searching and retrieving Wikipedia content."""

    def __init__(self, language: str = "en"):
        from mcp_search_server import __version__

        self.api_base_url = "https://{lang}.wikipedia.org/w/api.php"
        self.language = language
        self.headers = {
            "User-Agent": f"mcp-search-server/{__version__} (+https://github.com/KazKozDev/mcp-search-server)"
        }

    async def _make_api_request(self, lang: str, params: Dict) -> Dict:
        """Helper to make async Wikipedia API requests."""
        url = self.api_base_url.format(lang=lang)
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, headers=self.headers, timeout=15)
                response.raise_for_status()
                return response.json()
        except httpx.RequestError as e:
            raise ConnectionError(f"Failed to connect to Wikipedia ({lang}): {e}") from e
        except Exception as e:
            raise Exception(f"Error querying Wikipedia ({lang}): {e}") from e

    async def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search Wikipedia for articles matching a query."""
        logger.info(f"Searching Wikipedia for: {query}")

        if not query or not str(query).strip():
            raise Exception("Query cannot be empty")

        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "srlimit": limit,
        }

        data = await self._make_api_request(self.language, params)

        try:
            raw_results = data.get("query", {}).get("search", [])
            results = []

            for item in raw_results[:limit]:
                title = item.get("title", "")
                snippet = self._clean_html(item.get("snippet", ""))
                pageid = item.get("pageid", 0)

                results.append(
                    {
                        "title": title,
                        "snippet": snippet,
                        "pageid": pageid,
                        "url": f"https://{self.language}.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}",
                    }
                )

            return results

        except Exception as e:
            raise Exception(f"Error parsing Wikipedia results: {e}")

    async def get_summary(self, title: str) -> Dict[str, Any]:
        """Get a summary of a Wikipedia article."""
        logger.info(f"Getting Wikipedia summary for: {title}")

        try:
            summary_data = await self._get_page_extract(title, intro_only=True)
            return summary_data

        except Exception as direct_error:
            logger.debug(f"Direct lookup failed: {str(direct_error)}, trying search")

            search_results = await self.search(title, limit=1)

            if search_results:
                actual_title = search_results[0]["title"]
                logger.info(f"Using search result: {actual_title}")
                summary_data = await self._get_page_extract(actual_title, intro_only=True)
                return summary_data
            else:
                raise ValueError(f"No Wikipedia article found for '{title}'")

    async def _get_page_extract(self, title: str, intro_only: bool = False) -> Dict[str, Any]:
        """Get the extract (text content) of a Wikipedia page."""
        params = {
            "action": "query",
            "prop": "extracts|info",
            "exintro": "1" if intro_only else "0",
            "explaintext": "1",
            "titles": title,
            "format": "json",
            "inprop": "url",
            "redirects": "1",
        }

        data = await self._make_api_request(self.language, params)
        pages = data.get("query", {}).get("pages", {})

        if "-1" in pages and "missing" in pages["-1"]:
            raise Exception(f"Wikipedia article '{title}' not found")

        page_id = next(iter(pages.keys()))
        page = pages[page_id]

        page_title = page.get("title", title)
        page_url = page.get(
            "fullurl",
            f"https://{self.language}.wikipedia.org/wiki/{quote(page_title.replace(' ', '_'))}",
        )
        extract = page.get("extract", "")

        return {
            "title": page_title,
            "pageid": int(page_id),
            "url": page_url,
            "language": self.language,
            "extract": extract,
            "summary": extract if intro_only else extract[:500] + "...",
        }

    def _clean_html(self, text: str) -> str:
        """Clean HTML tags and entities from text."""
        import html as html_module

        text = re.sub(r"<[^>]+>", " ", text)
        text = html_module.unescape(text)
        text = re.sub(r"\s+", " ", text).strip()
        return text


async def search_wikipedia(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Search Wikipedia.

    Args:
        query: Search query
        limit: Maximum number of results

    Returns:
        List of Wikipedia search results
    """
    tool = WikipediaTool()
    return await tool.search(query, limit)


async def get_wikipedia_summary(title: str) -> Dict[str, Any]:
    """
    Get Wikipedia article summary.

    Args:
        title: Article title

    Returns:
        Article summary data
    """
    tool = WikipediaTool()
    return await tool.get_summary(title)
