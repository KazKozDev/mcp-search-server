"""PubMed search tool using Biopython Entrez."""

import asyncio
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class PubMedSearchTool:
    """PubMed search tool using Biopython Entrez (No auth required)"""

    def __init__(self, email: str = "researcher@example.com"):
        """
        Initialize PubMed tool

        Args:
            email: Email address (required by NCBI policy)
        """
        try:
            from Bio import Entrez, Medline

            self.Entrez = Entrez
            self.Medline = Medline
            self.email = email
            Entrez.email = email
            self.request_delay = 0.5  # NCBI limit: 3 req/sec, we use 0.5s to be safe
            self.available = True
        except ImportError:
            logger.warning("Biopython not installed. PubMed tool disabled.")
            self.available = False

    async def search(
        self, query: str, max_results: int = 10, sort: str = "relevance"
    ) -> Optional[List[Dict]]:
        """
        Search PubMed articles

        Args:
            query: Search query (e.g. "LLM in medicine")
            max_results: Max articles to return
            sort: 'relevance', 'pub_date', 'journal', 'title'

        Returns:
            List of article metadata
        """
        if not self.available:
            logger.error("PubMed tool not available (Biopython not installed)")
            return None

        await asyncio.sleep(self.request_delay)

        try:
            logger.info(f"Searching PubMed: {query}")

            # Step 1: Search for IDs (run in executor to avoid blocking)
            loop = asyncio.get_event_loop()
            id_list = await loop.run_in_executor(None, self._search_ids, query, max_results, sort)

            if not id_list:
                logger.warning("No PubMed results found")
                return None

            # Step 2: Fetch article details
            return await self.get_details(id_list)

        except Exception as e:
            logger.error(f"PubMed search error: {e}")
            return None

    def _search_ids(self, query: str, max_results: int, sort: str) -> List[str]:
        """Synchronous ID search (called in executor)"""
        handle = self.Entrez.esearch(db="pubmed", term=query, retmax=max_results, sort=sort)
        record = self.Entrez.read(handle)
        handle.close()
        return record.get("IdList", [])

    async def get_details(self, id_list: List[str]) -> Optional[List[Dict]]:
        """
        Fetch details for specific PubMed IDs

        Args:
            id_list: List of PubMed IDs (PMID)

        Returns:
            List of detailed article metadata
        """
        if not self.available:
            return None

        await asyncio.sleep(self.request_delay)

        try:
            logger.info(f"Fetching details for {len(id_list)} articles")

            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            articles = await loop.run_in_executor(None, self._fetch_details, id_list)

            return articles

        except Exception as e:
            logger.error(f"Error fetching details: {e}")
            return None

    def _fetch_details(self, id_list: List[str]) -> List[Dict]:
        """Synchronous detail fetching (called in executor)"""
        handle = self.Entrez.efetch(db="pubmed", id=id_list, rettype="medline", retmode="text")
        records = self.Medline.parse(handle)

        articles = []
        for record in records:
            articles.append(
                {
                    "title": record.get("TI", "No title"),
                    "abstract": record.get("AB", "No abstract"),
                    "authors": record.get("AU", []),
                    "journal": record.get("JT", "Unknown journal"),
                    "pub_date": record.get("DP", "Unknown date"),
                    "pmid": record.get("PMID"),
                    "doi": record.get("LID", "").replace(" [doi]", ""),
                    "keywords": record.get("OT", []),
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{record.get('PMID')}/",
                    "source": "pubmed",
                }
            )

        handle.close()
        return articles

    async def get_abstract(self, pmid: str) -> Optional[str]:
        """Get abstract for a specific article"""
        details = await self.get_details([pmid])
        if details:
            return details[0].get("abstract")
        return None


# Global instance
_pubmed_tool = PubMedSearchTool()


# Exported async functions
async def search_pubmed(
    query: str, max_results: int = 10, sort: str = "relevance"
) -> Optional[List[Dict]]:
    """Search PubMed articles"""
    return await _pubmed_tool.search(query, max_results, sort)


async def get_pubmed_details(id_list: List[str]) -> Optional[List[Dict]]:
    """Fetch details for specific PubMed IDs"""
    return await _pubmed_tool.get_details(id_list)


async def get_pubmed_abstract(pmid: str) -> Optional[str]:
    """Get abstract for a specific article"""
    return await _pubmed_tool.get_abstract(pmid)
