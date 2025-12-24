import requests
import logging
from bs4 import BeautifulSoup
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class WikipediaSearchTool:
    """Wikipedia search and content retrieval tool for multi-agent research system"""
    
    def __init__(self, default_lang: str = 'en'):
        self.default_lang = default_lang
        self.headers = {
            'User-Agent': 'MultiAgentResearchSystem/1.0 (Educational purpose)'
        }
    
    def search(self, query: str, lang: str = None, max_results: int = 5) -> Optional[List[Dict]]:
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
            'action': 'query',
            'generator': 'search',
            'gsrsearch': query,
            'gsrlimit': max_results * 2,  # Request more to filter out disambiguation
            'prop': 'extracts|info|categories',
            'exintro': True,
            'explaintext': True,
            'exsentences': 4,
            'inprop': 'url',
            'cllimit': 10,
            'format': 'json'
        }
        
        try:
            logger.info(f"Searching Wikipedia for: {query} (lang: {lang})")
            response = requests.get(search_url, params=params, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            pages = data.get('query', {}).get('pages', {})
            if not pages:
                logger.warning(f"No Wikipedia results found for: {query}")
                return None
            
            results = []
            for page_id, page in pages.items():
                # Filter out disambiguation pages
                if self._is_disambiguation(page):
                    continue
                
                extract = page.get('extract', '').strip()
                extract = ' '.join(extract.split())  # Normalize whitespace
                
                results.append({
                    'title': page.get('title', ''),
                    'extract': extract if extract else 'No description available',
                    'url': page.get('fullurl', ''),
                    'pageid': page.get('pageid', 0),
                    'source': 'wikipedia'
                })
            
            # Sort by title and limit results
            results = sorted(results, key=lambda x: x['title'])[:max_results]
            logger.info(f"Found {len(results)} Wikipedia articles for: {query}")
            return results if results else None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Wikipedia search error for '{query}': {e}")
            return None
    
    def get_content(self, title: str, lang: str = None) -> Optional[Dict]:
        """
        Get full article content with sections and related articles
        
        Args:
            title: Article title
            lang: Language code (default: 'en')
            
        Returns:
            Dict with 'title', 'url', 'sections', 'related' or None if error
        """
        lang = lang or self.default_lang
        url = f"https://{lang}.wikipedia.org/wiki/{requests.utils.quote(title)}"
        
        try:
            logger.info(f"Fetching Wikipedia article: {title}")
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Get title
            header = soup.find('h1', {'id': 'firstHeading'})
            title_text = header.get_text() if header else title
            
            # Parse content
            sections = self._parse_content(soup)
            
            # Get related articles
            related = self._get_related_articles(title, lang)
            
            result = {
                'title': title_text,
                'url': url,
                'sections': sections,
                'related': related,
                'source': 'wikipedia'
            }
            
            logger.info(f"Successfully fetched article: {title} ({len(sections)} sections)")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch Wikipedia article '{title}': {e}")
            return None
    
    def get_summary(self, title: str, lang: str = None) -> Optional[str]:
        """
        Get article summary (first section only)
        
        Args:
            title: Article title
            lang: Language code
            
        Returns:
            Summary text or None if error
        """
        article = self.get_content(title, lang)
        if not article or not article.get('sections'):
            return None
        
        # Return first section content
        first_section = article['sections'][0]
        return '\n'.join(first_section.get('content', []))
    
    def _is_disambiguation(self, page: Dict) -> bool:
        """Check if page is a disambiguation page"""
        # Check categories
        categories = page.get('categories', [])
        for cat in categories:
            cat_title = cat.get('title', '').lower()
            if 'disambig' in cat_title or 'disambiguation' in cat_title:
                return True
        
        # Check extract text
        extract = page.get('extract', '').lower()
        disambiguation_markers = [
            'may refer to:',
            'may stand for:',
            'can refer to:',
            'disambiguation page'
        ]
        return any(marker in extract for marker in disambiguation_markers)
    
    def _parse_content(self, soup) -> List[Dict]:
        """Parse article content into sections"""
        content_div = soup.find('div', {'id': 'mw-content-text'})
        if not content_div:
            return []
        
        # Remove unwanted elements
        for tag in content_div.find_all(['table', 'script', 'style', 'sup']):
            tag.decompose()
        
        sections = []
        current_section = {'title': 'Introduction', 'content': []}
        
        for element in content_div.find_all(['p', 'h2', 'h3', 'ul', 'ol']):
            if element.name == 'h2':
                if current_section['content']:
                    sections.append(current_section)
                
                span = element.find('span', {'class': 'mw-headline'})
                section_title = span.get_text() if span else element.get_text()
                current_section = {'title': section_title.strip(), 'content': []}
                
            elif element.name == 'h3':
                span = element.find('span', {'class': 'mw-headline'})
                if span:
                    current_section['content'].append(f"\n{span.get_text()}\n")
                    
            elif element.name == 'p':
                text = element.get_text().strip()
                if text and len(text) > 30:
                    current_section['content'].append(text)
                    
            elif element.name in ['ul', 'ol']:
                for li in element.find_all('li', recursive=False):
                    text = li.get_text().strip()
                    if text:
                        current_section['content'].append(f"• {text[:300]}")
        
        if current_section['content']:
            sections.append(current_section)
        
        return sections
    
    def _get_related_articles(self, title: str, lang: str) -> List[str]:
        """Get related articles via links"""
        api_url = f"https://{lang}.wikipedia.org/w/api.php"
        
        params = {
            'action': 'query',
            'titles': title,
            'prop': 'links',
            'pllimit': 30,
            'plnamespace': 0,
            'format': 'json'
        }
        
        try:
            response = requests.get(api_url, params=params, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            pages = data.get('query', {}).get('pages', {})
            links = []
            
            for page_id, page in pages.items():
                for link in page.get('links', []):
                    link_title = link.get('title', '')
                    # Filter out service pages
                    if ':' not in link_title and len(link_title) > 2:
                        links.append(link_title)
            
            return links[:15]
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to get related articles for '{title}': {e}")
            return []


# Tool registration function for your registry
def register_tool(registry):
    """Register Wikipedia tool in the tool registry"""
    wiki_tool = WikipediaSearchTool(default_lang='en')
    
    registry.register('wikipedia_search', wiki_tool.search)
    registry.register('wikipedia_content', wiki_tool.get_content)
    registry.register('wikipedia_summary', wiki_tool.get_summary)
    
    logger.info("Registered Wikipedia tools: search, content, summary")
