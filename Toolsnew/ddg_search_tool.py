import logging
import time
import random
from typing import List, Dict, Optional
from ddgs import DDGS
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class DuckDuckGoSearchTool:
    """Advanced DuckDuckGo search tool with anti-blocking features"""
    
    def __init__(self, proxy: str = None):
        """
        Initialize DuckDuckGo search tool
        
        Args:
            proxy: Optional proxy (http/https/socks5)
        """
        self.proxy = proxy
        self.request_delay = 0.5  # 500ms delay between requests
        self.last_request_time = 0
        
        # User-Agent rotation pool
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0',
        ]
    
    def _rate_limit(self):
        """Implement rate limiting to avoid blocks"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.request_delay:
            sleep_time = self.request_delay - time_since_last_request
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _get_random_user_agent(self) -> str:
        """Get random user agent from pool"""
        return random.choice(self.user_agents)
    
    def _retry_on_failure(self, func, *args, max_retries: int = 3, **kwargs):
        """Retry function on failure with exponential backoff"""
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time:.2f}s: {e}")
                time.sleep(wait_time)
    
    def search(self, query: str, max_results: int = 10, region: str = "us-en", 
               timelimit: str = None, safesearch: str = "moderate") -> Optional[List[Dict]]:
        """
        Search DuckDuckGo
        
        Args:
            query: Search query
            max_results: Maximum number of results
            region: Region code (e.g., 'us-en', 'uk-en', 'ru-ru')
            timelimit: Time filter ('d' day, 'w' week, 'm' month, 'y' year)
            safesearch: Safe search level ('on', 'moderate', 'off')
            
        Returns:
            List of search results or None if error
        """
        self._rate_limit()
        
        try:
            logger.info(f"Searching DuckDuckGo for: {query} (region: {region})")
            
            def _search():
                with DDGS(proxy=self.proxy, timeout=10) as ddgs:
                    results = list(ddgs.text(
                        query,
                        region=region,
                        safesearch=safesearch,
                        timelimit=timelimit,
                        max_results=max_results
                    ))
                return results
            
            results = self._retry_on_failure(_search)
            
            if not results:
                # Fallback for some queries that might fail with specific regions
                def _search_fallback():
                    with DDGS(proxy=self.proxy, timeout=10) as ddgs:
                        return list(ddgs.text(query, max_results=max_results))
                results = self._retry_on_failure(_search_fallback)
            
            if not results:
                logger.warning(f"No DuckDuckGo results found for: {query}")
                return None
            
            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    'title': result.get('title', ''),
                    'url': result.get('href', ''),
                    'snippet': result.get('body', ''),
                    'source': 'duckduckgo'
                })
            
            logger.info(f"Found {len(formatted_results)} DuckDuckGo results for: {query}")
            return formatted_results
            
        except Exception as e:
            logger.error(f"DuckDuckGo search error for '{query}': {e}")
            return None
    
    def search_news(self, query: str, max_results: int = 10, 
                    region: str = "us-en", timelimit: str = "m") -> Optional[List[Dict]]:
        """
        Search DuckDuckGo News
        
        Args:
            query: Search query
            max_results: Maximum number of results
            region: Region code
            timelimit: Time filter ('d', 'w', 'm')
            
        Returns:
            List of news results or None if error
        """
        self._rate_limit()
        
        try:
            logger.info(f"Searching DuckDuckGo News for: {query}")
            
            def _search():
                with DDGS(proxy=self.proxy, timeout=10) as ddgs:
                    results = list(ddgs.news(
                        query,
                        region=region,
                        timelimit=timelimit,
                        max_results=max_results
                    ))
                return results
            
            results = self._retry_on_failure(_search)
            
            if not results:
                logger.warning(f"No DuckDuckGo news found for: {query}")
                return None
            
            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    'title': result.get('title', ''),
                    'url': result.get('url', ''),
                    'snippet': result.get('body', ''),
                    'date': result.get('date', ''),
                    'source_name': result.get('source', ''),
                    'source': 'duckduckgo_news'
                })
            
            logger.info(f"Found {len(formatted_results)} DuckDuckGo news for: {query}")
            return formatted_results
            
        except Exception as e:
            logger.error(f"DuckDuckGo news search error for '{query}': {e}")
            return None
    
    def search_with_content(self, query: str, max_results: int = 5, 
                           region: str = "us-en") -> Optional[List[Dict]]:
        """
        Search and fetch full page content
        
        Args:
            query: Search query
            max_results: Maximum number of results
            region: Region code
            
        Returns:
            List of results with full content or None if error
        """
        results = self.search(query, max_results, region)
        
        if not results:
            return None
        
        logger.info(f"Fetching content for {len(results)} results")
        
        for result in results:
            content = self.get_page_content(result['url'])
            result['content'] = content
            result['has_content'] = content is not None
            
            # Rate limit between content fetches
            self._rate_limit()
        
        return results
    
    def get_page_content(self, url: str, max_length: int = 5000) -> Optional[str]:
        """
        Extract text content from URL
        
        Args:
            url: Page URL
            max_length: Maximum content length (0 = full text)
            
        Returns:
            Page text or None if error
        """
        try:
            headers = {
                'User-Agent': self._get_random_user_agent(),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            }
            
            response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(['script', 'style', 'nav', 'header', 'footer']):
                script.decompose()
            
            # Get text
            text = soup.get_text()
            
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            if max_length > 0 and len(text) > max_length:
                text = text[:max_length] + "..."
            
            logger.info(f"Extracted {len(text)} chars from: {url}")
            return text
            
        except Exception as e:
            logger.warning(f"Failed to extract content from '{url}': {e}")
            return None
    
    def search_recent(self, query: str, max_results: int = 10, 
                     days: int = 1) -> Optional[List[Dict]]:
        """
        Search recent results
        
        Args:
            query: Search query
            max_results: Maximum results
            days: Number of days to look back
            
        Returns:
            List of recent results or None if error
        """
        # Map days to timelimit
        if days == 1:
            timelimit = 'd'
        elif days <= 7:
            timelimit = 'w'
        elif days <= 30:
            timelimit = 'm'
        else:
            timelimit = 'y'
        
        return self.search(query, max_results, timelimit=timelimit)
    
    def instant_answer(self, query: str) -> Optional[Dict]:
        """
        Get DuckDuckGo instant answer
        
        Args:
            query: Query for instant answer
            
        Returns:
            Instant answer data or None if not available
        """
        self._rate_limit()
        
        try:
            logger.info(f"Getting instant answer for: {query}")
            
            def _search():
                with DDGS(proxy=self.proxy, timeout=10) as ddgs:
                    # The 'answers' method was removed in recent versions of duckduckgo_search
                    # We'll use a regular search and look for an abstract if available
                    results = list(ddgs.text(query, max_results=1))
                return results[0].get('body') if results else None
            
            results = self._retry_on_failure(_search)
            
            if results:
                logger.info(f"Got instant answer for: {query}")
                return {
                    'answer': results,
                    'source': 'duckduckgo_instant'
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Instant answer error for '{query}': {e}")
            return None


# Tool registration function
def register_tool(registry):
    """Register DuckDuckGo tool in the tool registry"""
    ddg_tool = DuckDuckGoSearchTool()
    
    registry.register('ddg_search', ddg_tool.search)
    registry.register('ddg_search_news', ddg_tool.search_news)
    registry.register('ddg_search_with_content', ddg_tool.search_with_content)
    registry.register('ddg_search_recent', ddg_tool.search_recent)
    registry.register('ddg_instant_answer', ddg_tool.instant_answer)
    registry.register('ddg_get_content', ddg_tool.get_page_content)
    
    logger.info("Registered DuckDuckGo tools: search, news, with_content, recent, instant_answer, get_content")
