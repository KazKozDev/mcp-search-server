import requests
import logging
import time
from typing import List, Dict, Optional
import base64

logger = logging.getLogger(__name__)


class GitHubSearchTool:
    """GitHub search tool for public repositories and code (No auth required)"""
    
    def __init__(self):
        self.base_url = "https://api.github.com"
        self.headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'MultiAgentResearchSystem/1.0'
        }
        self.last_request_time = 0
        # GitHub public API limit is 10 requests per minute (~6s delay)
        # We'll use 2s delay and handle rate limits gracefully
        self.request_delay = 2.0 
    
    def _rate_limit(self):
        """Simple rate limiting"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.request_delay:
            time.sleep(self.request_delay - time_since_last_request)
        
        self.last_request_time = time.time()
    
    def search_repositories(self, query: str, sort: str = "stars", 
                          max_results: int = 5) -> Optional[List[Dict]]:
        """
        Search public repositories
        
        Args:
            query: Search query (e.g. "LLM agents language:python")
            sort: Sort field ('stars', 'forks', 'updated')
            max_results: Max repos to return
            
        Returns:
            List of repository metadata
        """
        self._rate_limit()
        
        params = {
            'q': query,
            'sort': sort,
            'order': 'desc',
            'per_page': max_results
        }
        
        try:
            logger.info(f"Searching GitHub repos: {query}")
            response = requests.get(
                f"{self.base_url}/search/repositories",
                params=params,
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 403:
                logger.warning("GitHub API rate limit exceeded")
                return None
                
            response.raise_for_status()
            data = response.json()
            
            repos = []
            for item in data.get('items', []):
                repos.append({
                    'name': item['name'],
                    'full_name': item['full_name'],
                    'description': item['description'],
                    'url': item['html_url'],
                    'stars': item['stargazers_count'],
                    'language': item['language'],
                    'updated_at': item['updated_at'][:10],
                    'source': 'github_repo'
                })
            
            logger.info(f"Found {len(repos)} repositories")
            return repos
            
        except Exception as e:
            logger.error(f"GitHub repo search error: {e}")
            return None
    
    def get_repo_readme(self, full_name: str) -> Optional[str]:
        """
        Get README content for a repository
        
        Args:
            full_name: 'owner/repo' string
            
        Returns:
            README content text
        """
        self._rate_limit()
        
        try:
            logger.info(f"Fetching README for: {full_name}")
            response = requests.get(
                f"{self.base_url}/repos/{full_name}/readme",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 404:
                return None
                
            response.raise_for_status()
            data = response.json()
            
            # Decode content
            if data.get('encoding') == 'base64':
                content = base64.b64decode(data['content']).decode('utf-8', errors='ignore')
                return content
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching README: {e}")
            return None
    
    def get_repo_files(self, full_name: str, path: str = "") -> Optional[List[str]]:
        """
        List files in repository directory
        
        Args:
            full_name: 'owner/repo'
            path: Directory path (empty for root)
            
        Returns:
            List of filenames
        """
        self._rate_limit()
        
        try:
            url = f"{self.base_url}/repos/{full_name}/contents/{path}"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code != 200:
                return None
                
            items = response.json()
            if isinstance(items, list):
                return [item['name'] for item in items]
            return []
            
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return None
            
    def get_file_content(self, full_name: str, path: str) -> Optional[str]:
        """
        Get raw content of a specific file
        
        Args:
            full_name: 'owner/repo'
            path: File path
            
        Returns:
            File content
        """
        self._rate_limit()
        
        try:
            # Use raw.githubusercontent.com for better reliability
            url = f"https://raw.githubusercontent.com/{full_name}/master/{path}"
            # Try main branch if master fails
            
            response = requests.get(url, timeout=10)
            if response.status_code == 404:
                url = f"https://raw.githubusercontent.com/{full_name}/main/{path}"
                response = requests.get(url, timeout=10)
                
            if response.status_code == 200:
                return response.text
                
            # Fallback to API
            return self._get_file_content_api(full_name, path)
            
        except Exception as e:
            logger.error(f"Error fetching file content: {e}")
            return None

    def _get_file_content_api(self, full_name: str, path: str) -> Optional[str]:
        """Fallback to API if raw content fails"""
        try:
            url = f"{self.base_url}/repos/{full_name}/contents/{path}"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('encoding') == 'base64':
                    return base64.b64decode(data['content']).decode('utf-8', errors='ignore')
            return None
        except:
            return None

# Register tool
def register_tool(registry):
    gh_tool = GitHubSearchTool()
    
    registry.register('github_search_repos', gh_tool.search_repositories)
    registry.register('github_get_readme', gh_tool.get_repo_readme)
    registry.register('github_list_files', gh_tool.get_repo_files)
    registry.register('github_get_file', gh_tool.get_file_content)
    
    logger.info("Registered GitHub tools: search_repos, get_readme, list_files, get_file")
