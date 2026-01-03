"""ArXiv search and paper retrieval tool."""

import logging
from typing import List, Dict, Optional
from datetime import datetime
import xml.etree.ElementTree as ET
import aiohttp

logger = logging.getLogger(__name__)


class ArxivSearchTool:
    """Arxiv search and paper retrieval tool for MCP server"""

    def __init__(self):
        self.base_url = "https://export.arxiv.org/api/query"
        self.headers = {"User-Agent": "MCP-Search-Server/1.0 (Educational purpose)"}

    async def search(
        self, query: str, max_results: int = 10, sort_by: str = "relevance"
    ) -> Optional[List[Dict]]:
        """
        Search arxiv papers

        Args:
            query: Search query (supports arxiv query syntax)
            max_results: Maximum number of results to return
            sort_by: Sort method - 'relevance', 'lastUpdatedDate', 'submittedDate'

        Returns:
            List of dicts with paper metadata or None if error
        """
        params = {
            "search_query": query,
            "start": 0,
            "max_results": max_results,
            "sortBy": sort_by,
            "sortOrder": "descending",
        }

        try:
            logger.info(f"Searching arXiv for: {query}")
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.base_url, params=params, headers=self.headers, timeout=15
                ) as response:
                    response.raise_for_status()
                    text = await response.text()

            papers = self._parse_response(text)

            if not papers:
                logger.warning(f"No arXiv papers found for: {query}")
                return None

            logger.info(f"Found {len(papers)} arXiv papers for: {query}")
            return papers

        except Exception as e:
            logger.error(f"ArXiv search error for '{query}': {e}")
            return None

    async def search_by_category(
        self, category: str, query: str = None, max_results: int = 10
    ) -> Optional[List[Dict]]:
        """
        Search papers in specific category

        Args:
            category: arXiv category (e.g., 'cs.AI', 'cs.LG', 'stat.ML')
            query: Optional additional query terms
            max_results: Maximum number of results

        Returns:
            List of papers or None if error
        """
        search_query = f"cat:{category}"
        if query:
            search_query += f" AND all:{query}"

        return await self.search(search_query, max_results)

    async def search_recent(
        self, category: str = None, days: int = 7, max_results: int = 10
    ) -> Optional[List[Dict]]:
        """
        Search recent papers

        Args:
            category: Optional category filter
            days: Number of days to look back
            max_results: Maximum results

        Returns:
            List of recent papers or None if error
        """
        query = "all:*"
        if category:
            query = f"cat:{category}"

        return await self.search(query, max_results, sort_by="submittedDate")

    async def get_paper(self, arxiv_id: str) -> Optional[Dict]:
        """
        Get detailed information about specific paper by arXiv ID

        Args:
            arxiv_id: arXiv paper ID (e.g., '2301.12345' or 'cs.AI/0601001')

        Returns:
            Dict with full paper metadata or None if error
        """
        params = {"id_list": arxiv_id, "max_results": 1}

        try:
            logger.info(f"Fetching arXiv paper: {arxiv_id}")
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.base_url, params=params, headers=self.headers, timeout=10
                ) as response:
                    response.raise_for_status()
                    text = await response.text()

            papers = self._parse_response(text)

            if papers:
                logger.info(f"Successfully fetched paper: {arxiv_id}")
                return papers[0]
            else:
                logger.warning(f"Paper not found: {arxiv_id}")
                return None

        except Exception as e:
            logger.error(f"Error fetching paper '{arxiv_id}': {e}")
            return None

    async def get_summary(self, arxiv_id: str) -> Optional[str]:
        """
        Get paper abstract/summary

        Args:
            arxiv_id: arXiv paper ID

        Returns:
            Abstract text or None if error
        """
        paper = await self.get_paper(arxiv_id)
        if paper:
            return paper.get("abstract", "")
        return None

    def _parse_response(self, xml_text: str) -> List[Dict]:
        """Parse arXiv API XML response"""
        papers = []

        try:
            root = ET.fromstring(xml_text)

            # Define namespace
            ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

            for entry in root.findall("atom:entry", ns):
                paper = self._parse_entry(entry, ns)
                if paper:
                    papers.append(paper)

        except ET.ParseError as e:
            logger.error(f"XML parsing error: {e}")

        return papers

    def _parse_entry(self, entry, ns) -> Dict:
        """Parse single paper entry from XML"""
        try:
            # Extract ID (last part of the URL)
            id_elem = entry.find("atom:id", ns)
            paper_id = id_elem.text.split("/")[-1] if id_elem is not None else "unknown"

            # Extract basic info
            title_elem = entry.find("atom:title", ns)
            title = self._clean_text(title_elem.text) if title_elem is not None else "No title"

            summary_elem = entry.find("atom:summary", ns)
            abstract = (
                self._clean_text(summary_elem.text) if summary_elem is not None else "No abstract"
            )

            # Extract authors
            authors = []
            for author in entry.findall("atom:author", ns):
                name_elem = author.find("atom:name", ns)
                if name_elem is not None:
                    authors.append(name_elem.text)

            # Extract dates
            published_elem = entry.find("atom:published", ns)
            published = (
                self._parse_date(published_elem.text) if published_elem is not None else None
            )

            updated_elem = entry.find("atom:updated", ns)
            updated = self._parse_date(updated_elem.text) if updated_elem is not None else None

            # Extract categories
            categories = []
            for category in entry.findall("atom:category", ns):
                term = category.get("term")
                if term:
                    categories.append(term)

            # Extract links
            pdf_link = None
            abs_link = None
            for link in entry.findall("atom:link", ns):
                if link.get("title") == "pdf":
                    pdf_link = link.get("href")
                elif link.get("type") == "text/html":
                    abs_link = link.get("href")

            # Extract primary category
            primary_category_elem = entry.find("arxiv:primary_category", ns)
            primary_category = (
                primary_category_elem.get("term") if primary_category_elem is not None else None
            )

            # Extract comment
            comment_elem = entry.find("arxiv:comment", ns)
            comment = comment_elem.text if comment_elem is not None else None

            return {
                "id": paper_id,
                "title": title,
                "abstract": abstract,
                "authors": authors,
                "published": published,
                "updated": updated,
                "categories": categories,
                "primary_category": primary_category,
                "pdf_url": pdf_link,
                "abs_url": abs_link,
                "comment": comment,
                "source": "arxiv",
            }

        except Exception as e:
            logger.error(f"Error parsing paper entry: {e}")
            return None

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        # Remove extra whitespace and newlines
        return " ".join(text.split())

    def _parse_date(self, date_str: str) -> str:
        """Parse and format date"""
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d")
        except Exception:
            return date_str


# Global instance
_arxiv_tool = ArxivSearchTool()


# Exported async functions
async def search_arxiv(
    query: str, max_results: int = 10, sort_by: str = "relevance"
) -> Optional[List[Dict]]:
    """Search arxiv papers"""
    return await _arxiv_tool.search(query, max_results, sort_by)


async def search_arxiv_by_category(
    category: str, query: str = None, max_results: int = 10
) -> Optional[List[Dict]]:
    """Search papers in specific category"""
    return await _arxiv_tool.search_by_category(category, query, max_results)


async def search_arxiv_recent(
    category: str = None, days: int = 7, max_results: int = 10
) -> Optional[List[Dict]]:
    """Search recent papers"""
    return await _arxiv_tool.search_recent(category, days, max_results)


async def get_arxiv_paper(arxiv_id: str) -> Optional[Dict]:
    """Get detailed information about specific paper"""
    return await _arxiv_tool.get_paper(arxiv_id)


async def get_arxiv_summary(arxiv_id: str) -> Optional[str]:
    """Get paper abstract/summary"""
    return await _arxiv_tool.get_summary(arxiv_id)
