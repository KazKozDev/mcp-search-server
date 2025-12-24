import logging
from typing import List, Dict, Optional
from gdeltdoc import GdeltDoc, Filters
from newspaper import Article

logger = logging.getLogger(__name__)


class GdeltNewsSearchTool:
    """GDELT news search tool for multi-agent research system"""
    
    def __init__(self):
        self.gd = GdeltDoc()
    
    def search(self, query: str, timespan: str = "1d", max_results: int = 10, 
               country: str = None, domain: str = None) -> Optional[List[Dict]]:
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
        try:
            logger.info(f"Searching GDELT for: {query} (timespan: {timespan})")
            
            # Build filters
            f = Filters(
                keyword=query,
                timespan=timespan,
                num_records=max_results
            )
            
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
                articles.append({
                    'title': row['title'],
                    'url': row['url'],
                    'domain': row['domain'],
                    'country': row.get('sourcecountry', 'unknown'),
                    'date': str(row['seendate']),
                    'source': 'gdelt'
                })
            
            logger.info(f"Found {len(articles)} GDELT articles for: {query}")
            return articles
            
        except Exception as e:
            logger.error(f"GDELT search error for '{query}': {e}")
            return None
    
    def search_with_content(self, query: str, timespan: str = "1d", 
                           max_results: int = 10) -> Optional[List[Dict]]:
        """
        Search articles and retrieve full text content
        
        Args:
            query: Search query
            timespan: Time span for search
            max_results: Maximum number of results
            
        Returns:
            List of articles with full text or None if error
        """
        articles = self.search(query, timespan, max_results)
        
        if not articles:
            return None
        
        logger.info(f"Retrieving full text for {len(articles)} articles")
        
        for article in articles:
            content = self.get_article_content(article['url'])
            article['content'] = content
            article['has_content'] = content is not None
        
        return articles
    
    def get_article_content(self, url: str, max_length: int = 2000) -> Optional[str]:
        """
        Extract article text from URL using newspaper3k
        
        Args:
            url: Article URL
            max_length: Maximum content length (0 = full text)
            
        Returns:
            Article text or None if error
        """
        try:
            logger.info(f"Extracting content from: {url}")
            
            article = Article(url)
            article.download()
            article.parse()
            
            text = article.text
            
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
    
    def search_by_country(self, query: str, country: str, timespan: str = "7d", 
                         max_results: int = 10) -> Optional[List[Dict]]:
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
        return self.search(query, timespan, max_results, country=country)
    
    def search_recent(self, query: str, hours: int = 24, max_results: int = 10) -> Optional[List[Dict]]:
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
        
        return self.search(query, timespan, max_results)


# Tool registration function for your registry
def register_tool(registry):
    """Register GDELT tool in the tool registry"""
    gdelt_tool = GdeltNewsSearchTool()
    
    registry.register('gdelt_search', gdelt_tool.search)
    registry.register('gdelt_search_with_content', gdelt_tool.search_with_content)
    registry.register('gdelt_search_by_country', gdelt_tool.search_by_country)
    registry.register('gdelt_search_recent', gdelt_tool.search_recent)
    registry.register('gdelt_get_content', gdelt_tool.get_article_content)
    
    logger.info("Registered GDELT tools: search, search_with_content, search_by_country, search_recent, get_content")
