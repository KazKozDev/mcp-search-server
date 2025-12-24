"""Enhanced Wikipedia search implementation combining both approaches."""

import logging
import re
from typing import Dict, List, Any, Optional
from urllib.parse import quote
import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class WikipediaSearchTool:
    """Enhanced Wikipedia search and content retrieval tool"""

    def __init__(self, default_lang: str = "en"):
        try:
            from mcp_search_server import __version__

            user_agent = (
                f"mcp-search-server/{__version__} (+https://github.com/KazKozDev/mcp-search-server)"
            )
        except Exception:
            user_agent = "MCP-Search-Server/1.0"

        self.default_lang = default_lang
        self.headers = {"User-Agent": user_agent}

    async def search(
        self, query: str, lang: str = None, max_results: int = 5
    ) -> Optional[List[Dict]]:
        """
        Search Wikipedia articles with extracts (filters out disambiguation pages)

        Args:
            query: Search query
            lang: Language code (default: 'en')
            max_results: Maximum number of results to return

        Returns:
            List of dicts with 'title', 'extract', 'url', 'pageid' or None if error
        """
        lang = lang or self.default_lang
        search_url = f"https://{lang}.wikipedia.org/w/api.php"

        params = {
            "action": "query",
            "generator": "search",
            "gsrsearch": query,
            "gsrlimit": max_results * 2,  # Request more to filter out disambiguation
            "prop": "extracts|info|categories",
            "exintro": "1",
            "explaintext": "1",
            "exsentences": 4,
            "inprop": "url",
            "cllimit": 10,
            "format": "json",
        }

        try:
            logger.info(f"Searching Wikipedia for: {query} (lang: {lang})")

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    search_url, params=params, headers=self.headers, timeout=10
                ) as response:
                    response.raise_for_status()
                    data = await response.json()

            pages = data.get("query", {}).get("pages", {})
            if not pages:
                logger.warning(f"No Wikipedia results found for: {query}")
                return None

            results = []
            for page_id, page in pages.items():
                # Filter out disambiguation pages
                if self._is_disambiguation(page):
                    continue

                extract = page.get("extract", "").strip()
                extract = " ".join(extract.split())  # Normalize whitespace

                results.append(
                    {
                        "title": page.get("title", ""),
                        "extract": extract if extract else "No description available",
                        "snippet": extract[:200] + "..." if len(extract) > 200 else extract,
                        "url": page.get("fullurl", ""),
                        "pageid": page.get("pageid", 0),
                        "source": "wikipedia",
                    }
                )

            # Sort by title and limit results
            results = sorted(results, key=lambda x: x["title"])[:max_results]
            logger.info(f"Found {len(results)} Wikipedia articles for: {query}")
            return results if results else None

        except Exception as e:
            logger.error(f"Wikipedia search error for '{query}': {e}")
            return None

    async def get_content(self, title: str, lang: str = None) -> Optional[Dict]:
        """
        Get full article content with sections and related articles

        Args:
            title: Article title
            lang: Language code (default: 'en')

        Returns:
            Dict with 'title', 'url', 'sections', 'related' or None if error
        """
        lang = lang or self.default_lang
        url = f"https://{lang}.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}"

        try:
            logger.info(f"Fetching Wikipedia article: {title}")

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers, timeout=10) as response:
                    response.raise_for_status()
                    html = await response.text()

            soup = BeautifulSoup(html, "html.parser")

            # Get title
            header = soup.find("h1", {"id": "firstHeading"})
            title_text = header.get_text() if header else title

            # Parse content
            sections = self._parse_content(soup)

            # Get related articles
            related = await self._get_related_articles(title, lang)

            result = {
                "title": title_text,
                "url": url,
                "sections": sections,
                "related": related,
                "source": "wikipedia",
            }

            logger.info(f"Successfully fetched article: {title} ({len(sections)} sections)")
            return result

        except Exception as e:
            logger.error(f"Failed to fetch Wikipedia article '{title}': {e}")
            return None

    async def get_summary(self, title: str, lang: str = None) -> Dict[str, Any]:
        """
        Get article summary (compatible with old API)

        Args:
            title: Article title
            lang: Language code

        Returns:
            Summary dict with title, extract, url, etc.
        """
        lang = lang or self.default_lang

        try:
            logger.info(f"Getting Wikipedia summary for: {title}")
            summary_data = await self._get_page_extract(title, lang, intro_only=True)
            return summary_data

        except Exception as direct_error:
            logger.debug(f"Direct lookup failed: {str(direct_error)}, trying search")

            # Fallback to search
            search_results = await self.search(title, lang, max_results=1)

            if search_results:
                actual_title = search_results[0]["title"]
                logger.info(f"Using search result: {actual_title}")
                summary_data = await self._get_page_extract(actual_title, lang, intro_only=True)
                return summary_data
            else:
                raise ValueError(f"No Wikipedia article found for '{title}'")

    async def _get_page_extract(
        self, title: str, lang: str, intro_only: bool = False
    ) -> Dict[str, Any]:
        """Get the extract (text content) of a Wikipedia page"""
        api_url = f"https://{lang}.wikipedia.org/w/api.php"

        params = {
            "action": "query",
            "prop": "extracts|info|pageimages|categories|revisions",
            "exintro": "1" if intro_only else "0",
            "explaintext": "1",
            "titles": title,
            "format": "json",
            "inprop": "url",
            "redirects": "1",
            "piprop": "thumbnail",
            "pithumbsize": "300",
            "cllimit": "20",
            "rvprop": "timestamp",
            "rvlimit": "1",
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(
                api_url, params=params, headers=self.headers, timeout=10
            ) as response:
                response.raise_for_status()
                data = await response.json()

        pages = data.get("query", {}).get("pages", {})

        if "-1" in pages and "missing" in pages["-1"]:
            raise Exception(f"Wikipedia article '{title}' not found")

        page_id = next(iter(pages.keys()))
        page = pages[page_id]

        page_title = page.get("title", title)
        page_url = page.get(
            "fullurl",
            f"https://{lang}.wikipedia.org/wiki/{quote(page_title.replace(' ', '_'))}",
        )
        extract = page.get("extract", "")

        thumbnail = None
        if isinstance(page.get("thumbnail"), dict):
            thumbnail = page.get("thumbnail", {}).get("source")

        categories: List[str] = []
        if isinstance(page.get("categories"), list):
            for cat in page.get("categories", []):
                title_raw = cat.get("title", "") if isinstance(cat, dict) else ""
                if title_raw.startswith("Category:"):
                    title_raw = title_raw.replace("Category:", "", 1)
                if title_raw:
                    categories.append(title_raw)

        last_updated = ""
        if isinstance(page.get("revisions"), list) and page["revisions"]:
            last_updated = page["revisions"][0].get("timestamp", "")

        sections: List[Dict[str, Any]] = []
        try:
            sections_data = await self._get_page_sections(page_title, lang)
            sections = sections_data
        except Exception as exc:
            logger.debug(f"Failed to fetch sections for '{page_title}': {exc}")

        word_count = len(extract.split()) if extract else 0
        page_length = int(page.get("length", 0) or 0)

        return {
            "title": page_title,
            "pageid": int(page_id),
            "url": page_url,
            "language": lang,
            "extract": extract,
            "summary": extract if intro_only else extract[:500] + "...",
            "thumbnail": thumbnail,
            "categories": categories,
            "sections": sections,
            "last_updated": last_updated,
            "word_count": word_count,
            "page_length": page_length,
        }

    async def _get_page_sections(self, title: str, lang: str) -> List[Dict[str, Any]]:
        """Get page sections"""
        api_url = f"https://{lang}.wikipedia.org/w/api.php"

        params = {
            "action": "parse",
            "page": title,
            "prop": "sections",
            "format": "json",
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(
                api_url, params=params, headers=self.headers, timeout=10
            ) as response:
                response.raise_for_status()
                data = await response.json()

        raw_sections = data.get("parse", {}).get("sections", [])
        sections: List[Dict[str, Any]] = []

        if not isinstance(raw_sections, list):
            return sections

        for section in raw_sections:
            if not isinstance(section, dict):
                continue
            try:
                sections.append(
                    {
                        "title": section.get("line", ""),
                        "level": int(section.get("level", 1) or 1),
                        "index": int(section.get("index", 0) or 0),
                        "anchor": section.get("anchor", ""),
                    }
                )
            except Exception:
                continue

        return sections

    def _is_disambiguation(self, page: Dict) -> bool:
        """Check if page is a disambiguation page"""
        # Check categories
        categories = page.get("categories", [])
        for cat in categories:
            cat_title = cat.get("title", "").lower()
            if "disambig" in cat_title or "disambiguation" in cat_title:
                return True

        # Check extract text
        extract = page.get("extract", "").lower()
        disambiguation_markers = [
            "may refer to:",
            "may stand for:",
            "can refer to:",
            "disambiguation page",
        ]
        return any(marker in extract for marker in disambiguation_markers)

    def _parse_content(self, soup) -> List[Dict]:
        """Parse article content into sections"""
        content_div = soup.find("div", {"id": "mw-content-text"})
        if not content_div:
            return []

        # Remove unwanted elements
        for tag in content_div.find_all(["table", "script", "style", "sup"]):
            tag.decompose()

        sections = []
        current_section = {"title": "Introduction", "content": []}

        for element in content_div.find_all(["p", "h2", "h3", "ul", "ol"]):
            if element.name == "h2":
                if current_section["content"]:
                    sections.append(current_section)

                span = element.find("span", {"class": "mw-headline"})
                section_title = span.get_text() if span else element.get_text()
                current_section = {"title": section_title.strip(), "content": []}

            elif element.name == "h3":
                span = element.find("span", {"class": "mw-headline"})
                if span:
                    current_section["content"].append(f"\n{span.get_text()}\n")

            elif element.name == "p":
                text = element.get_text().strip()
                if text and len(text) > 30:
                    current_section["content"].append(text)

            elif element.name in ["ul", "ol"]:
                for li in element.find_all("li", recursive=False):
                    text = li.get_text().strip()
                    if text:
                        current_section["content"].append(f"• {text[:300]}")

        if current_section["content"]:
            sections.append(current_section)

        return sections

    async def _get_related_articles(self, title: str, lang: str) -> List[str]:
        """Get related articles via links"""
        api_url = f"https://{lang}.wikipedia.org/w/api.php"

        params = {
            "action": "query",
            "titles": title,
            "prop": "links",
            "pllimit": 30,
            "plnamespace": 0,
            "format": "json",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    api_url, params=params, headers=self.headers, timeout=10
                ) as response:
                    response.raise_for_status()
                    data = await response.json()

            pages = data.get("query", {}).get("pages", {})
            links = []

            for page_id, page in pages.items():
                for link in page.get("links", []):
                    link_title = link.get("title", "")
                    # Filter out service pages
                    if ":" not in link_title and len(link_title) > 2:
                        links.append(link_title)

            return links[:15]

        except Exception as e:
            logger.warning(f"Failed to get related articles for '{title}': {e}")
            return []

    def _clean_html(self, text: str) -> str:
        """Clean HTML tags and entities from text."""
        import html as html_module

        text = re.sub(r"<[^>]+>", " ", text)
        text = html_module.unescape(text)
        text = re.sub(r"\s+", " ", text).strip()
        return text


# Global instance
_wikipedia_tool = WikipediaSearchTool()


# Exported async functions (compatible with old API)
async def search_wikipedia(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Search Wikipedia.

    Args:
        query: Search query
        limit: Maximum number of results

    Returns:
        List of Wikipedia search results
    """
    results = await _wikipedia_tool.search(query, max_results=limit)
    if not results:
        return []

    # Convert to old format
    formatted_results = []
    for result in results:
        formatted_results.append(
            {
                "title": result["title"],
                "snippet": result.get("snippet", result.get("extract", "")[:200]),
                "url": result["url"],
                "pageid": result["pageid"],
                "size": 0,  # Not available in new API
                "wordcount": 0,  # Not available in new API
            }
        )
    return formatted_results


async def get_wikipedia_summary(title: str) -> Dict[str, Any]:
    """
    Get Wikipedia article summary.

    Args:
        title: Article title

    Returns:
        Article summary data
    """
    return await _wikipedia_tool.get_summary(title)


async def get_wikipedia_content(title: str, lang: str = "en") -> Optional[Dict]:
    """
    Get full article content with sections

    Args:
        title: Article title
        lang: Language code

    Returns:
        Full article content
    """
    return await _wikipedia_tool.get_content(title, lang)
