import logging
import time
from typing import List, Dict, Optional
from datetime import datetime
from Bio import Entrez, Medline

logger = logging.getLogger(__name__)


class PubMedSearchTool:
    """PubMed search tool using Biopython Entrez (No auth required)"""
    
    def __init__(self, email: str = "researcher@example.com"):
        """
        Initialize PubMed tool
        
        Args:
            email: Email address (required by NCBI policy)
        """
        self.email = email
        Entrez.email = email
        self.last_request_time = 0
        # NCBI limit without API key is 3 requests/second
        # We'll use 0.5s delay to be safe
        self.request_delay = 0.5
    
    def _rate_limit(self):
        """Simple rate limiting"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.request_delay:
            time.sleep(self.request_delay - time_since_last_request)
        
        self.last_request_time = time.time()
    
    def search(self, query: str, max_results: int = 10, sort: str = "relevance") -> Optional[List[Dict]]:
        """
        Search PubMed articles
        
        Args:
            query: Search query (e.g. "LLM in medicine")
            max_results: Max articles to return
            sort: 'relevance', 'pub_date', 'journal', 'title'
            
        Returns:
            List of article metadata
        """
        self._rate_limit()
        
        try:
            logger.info(f"Searching PubMed: {query}")
            
            # Step 1: Search for IDs
            handle = Entrez.esearch(
                db="pubmed",
                term=query,
                retmax=max_results,
                sort=sort
            )
            record = Entrez.read(handle)
            handle.close()
            
            id_list = record.get("IdList", [])
            
            if not id_list:
                logger.warning("No PubMed results found")
                return None
            
            # Step 2: Fetch article details
            return self.get_details(id_list)
            
        except Exception as e:
            logger.error(f"PubMed search error: {e}")
            return None
    
    def get_details(self, id_list: List[str]) -> Optional[List[Dict]]:
        """
        Fetch details for specific PubMed IDs
        
        Args:
            id_list: List of PubMed IDs (PMID)
            
        Returns:
            List of detailed article metadata
        """
        self._rate_limit()
        
        try:
            logger.info(f"Fetching details for {len(id_list)} articles")
            
            handle = Entrez.efetch(
                db="pubmed",
                id=id_list,
                rettype="medline",
                retmode="text"
            )
            records = Medline.parse(handle)
            
            articles = []
            for record in records:
                articles.append({
                    'title': record.get('TI', 'No title'),
                    'abstract': record.get('AB', 'No abstract'),
                    'authors': record.get('AU', []),
                    'journal': record.get('JT', 'Unknown journal'),
                    'pub_date': record.get('DP', 'Unknown date'),
                    'pmid': record.get('PMID'),
                    'doi': record.get('LID', '').replace(' [doi]', ''),
                    'keywords': record.get('OT', []),
                    'url': f"https://pubmed.ncbi.nlm.nih.gov/{record.get('PMID')}/",
                    'source': 'pubmed'
                })
            
            handle.close()
            return articles
            
        except Exception as e:
            logger.error(f"Error fetching details: {e}")
            return None
    
    def get_abstract(self, pmid: str) -> Optional[str]:
        """Get abstract for a specific article"""
        details = self.get_details([pmid])
        if details:
            return details[0].get('abstract')
        return None


# Register tool
def register_tool(registry):
    # Try importing Biopython, warn if missing
    try:
        import Bio
    except ImportError:
        logger.warning("Biopython not installed. PubMed tool disabled. Install with: pip install biopython")
        return

    pubmed_tool = PubMedSearchTool()
    
    registry.register('pubmed_search', pubmed_tool.search)
    registry.register('pubmed_get_details', pubmed_tool.get_details)
    registry.register('pubmed_get_abstract', pubmed_tool.get_abstract)
    
    logger.info("Registered PubMed tools: search, get_details, get_abstract")
