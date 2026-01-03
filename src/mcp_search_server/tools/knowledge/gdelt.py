"""GDELT news search tool."""

import asyncio
import logging
from typing import List, Dict, Optional
import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class GdeltNewsSearchTool:
    """GDELT news search tool for MCP server"""

    def __init__(self):
        try:
            from gdeltdoc import GdeltDoc, Filters

            self.GdeltDoc = GdeltDoc
            self.Filters = Filters
            self.gd = GdeltDoc()
            self.available = True
        except ImportError:
            logger.warning("gdeltdoc not installed. GDELT tool disabled.")
            self.available = False

    async def search(
        self,
        query: str,
        timespan: str = "1d",
        max_results: int = 10,
        country: str = None,
        domain: str = None,
    ) -> Optional[List[Dict]]:
        """
        Search news articles using GDELT

        Args:
            query: Search query (keyword)
            timespan: Time span for search (e.g., '1d', '7d', '1m')
            max_results: Maximum number of results
            country: Filter by source country code (optional)
            domain: Filter by domain (optional)

        Returns:
            List of dicts with article metadata or None if error
        """
        if not self.available:
            logger.error("GDELT tool not available (gdeltdoc not installed)")
            return None

        try:
            logger.info(f"Searching GDELT for: {query} (timespan: {timespan})")

            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            articles = await loop.run_in_executor(
                None, self._search_sync, query, timespan, max_results, country, domain
            )

            return articles

        except Exception as e:
            logger.error(f"GDELT search error for '{query}': {e}")
            return None

    def _search_sync(
        self, query: str, timespan: str, max_results: int, country: str = None, domain: str = None
    ) -> Optional[List[Dict]]:
        """Synchronous search (called in executor)"""
        # Build filters
        f = self.Filters(keyword=query, timespan=timespan, num_records=max_results)

        if country:
            f.country = country
        if domain:
            f.domain = domain

        # Search articles
        articles_df = self.gd.article_search(f)

        if articles_df.empty:
            logger.warning(f"No GDELT articles found for: {query}")
            return None

        # Convert DataFrame to list of dicts
        articles = []
        for _, row in articles_df.iterrows():
            articles.append(
                {
                    "title": row["title"],
                    "url": row["url"],
                    "domain": row["domain"],
                    "country": row.get("sourcecountry", "unknown"),
                    "date": str(row["seendate"]),
                    "source": "gdelt",
                }
            )

        logger.info(f"Found {len(articles)} GDELT articles for: {query}")
        return articles

    async def search_with_content(
        self, query: str, timespan: str = "1d", max_results: int = 10
    ) -> Optional[List[Dict]]:
        """
        Search articles and retrieve full text content

        Args:
            query: Search query
            timespan: Time span for search
            max_results: Maximum number of results

        Returns:
            List of articles with full text or None if error
        """
        articles = await self.search(query, timespan, max_results)

        if not articles:
            return None

        logger.info(f"Retrieving full text for {len(articles)} articles")

        for article in articles:
            content = await self.get_article_content(article["url"])
            article["content"] = content
            article["has_content"] = content is not None

        return articles

    async def get_article_content(self, url: str, max_length: int = 2000) -> Optional[str]:
        """
        Extract article text from URL

        Args:
            url: Article URL
            max_length: Maximum content length (0 = full text)

        Returns:
            Article text or None if error
        """
        try:
            logger.info(f"Extracting content from: {url}")

            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    response.raise_for_status()
                    html = await response.text()

            # Parse with BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")

            # Remove unwanted elements
            for tag in soup(["script", "style", "nav", "header", "footer"]):
                tag.decompose()

            # Get text
            text = soup.get_text()

            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = " ".join(chunk for chunk in chunks if chunk)

            if not text:
                logger.warning(f"No text extracted from: {url}")
                return None

            # Truncate if needed
            if max_length > 0 and len(text) > max_length:
                text = text[:max_length] + "..."

            logger.info(f"Successfully extracted {len(text)} chars from: {url}")
            return text

        except Exception as e:
            logger.warning(f"Failed to extract content from '{url}': {e}")
            return None

    async def search_by_country(
        self, query: str, country: str, timespan: str = "7d", max_results: int = 10
    ) -> Optional[List[Dict]]:
        """
        Search news from specific country

        Args:
            query: Search query
            country: Country code (e.g., 'US', 'UK', 'RU')
            timespan: Time span
            max_results: Maximum results

        Returns:
            List of articles or None if error
        """
        return await self.search(query, timespan, max_results, country=country)

    async def search_recent(
        self, query: str, hours: int = 24, max_results: int = 10
    ) -> Optional[List[Dict]]:
        """
        Search recent news (last N hours)

        Args:
            query: Search query
            hours: Number of hours to look back
            max_results: Maximum results

        Returns:
            List of recent articles or None if error
        """
        # Convert hours to GDELT timespan format
        if hours <= 24:
            timespan = f"{hours}h"
        else:
            days = hours // 24
            timespan = f"{days}d"

        return await self.search(query, timespan, max_results)


# Global instance
_gdelt_tool = GdeltNewsSearchTool()


# Exported async functions
async def search_gdelt(
    query: str, timespan: str = "1d", max_results: int = 10, country: str = None, domain: str = None
) -> Optional[List[Dict]]:
    """Search news articles using GDELT"""
    return await _gdelt_tool.search(query, timespan, max_results, country, domain)


async def search_gdelt_with_content(
    query: str, timespan: str = "1d", max_results: int = 10
) -> Optional[List[Dict]]:
    """Search articles and retrieve full text content"""
    return await _gdelt_tool.search_with_content(query, timespan, max_results)


async def search_gdelt_by_country(
    query: str, country: str, timespan: str = "7d", max_results: int = 10
) -> Optional[List[Dict]]:
    """Search news from specific country"""
    return await _gdelt_tool.search_by_country(query, country, timespan, max_results)


async def search_gdelt_recent(
    query: str, hours: int = 24, max_results: int = 10
) -> Optional[List[Dict]]:
    """Search recent news"""
    return await _gdelt_tool.search_recent(query, hours, max_results)


async def get_gdelt_content(url: str, max_length: int = 2000) -> Optional[str]:
    """Extract article text from URL"""
    return await _gdelt_tool.get_article_content(url, max_length)
