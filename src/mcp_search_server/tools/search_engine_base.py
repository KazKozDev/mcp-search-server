"""Base class for search engines."""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class SearchEngineBase(ABC):
    """Base class for all search engines."""

    def __init__(self, name: str):
        """
        Initialize search engine.

        Args:
            name: Name of the search engine
        """
        self.name = name
        self.available = True

    @abstractmethod
    async def search(
        self,
        query: str,
        max_results: int = 10,
        timelimit: Optional[str] = None,
    ) -> Optional[List[Dict]]:
        """
        Perform search.

        Args:
            query: Search query
            max_results: Maximum number of results
            timelimit: Time filter ('d', 'w', 'm', 'y')

        Returns:
            List of search results or None if error
        """
        pass

    @abstractmethod
    async def search_news(
        self,
        query: str,
        max_results: int = 10,
        timelimit: Optional[str] = None,
    ) -> Optional[List[Dict]]:
        """
        Perform news search.

        Args:
            query: Search query
            max_results: Maximum number of results
            timelimit: Time filter ('d', 'w', 'm')

        Returns:
            List of news results or None if error
        """
        pass

    def format_result(self, title: str, url: str, snippet: str, **kwargs) -> Dict:
        """
        Format search result to unified structure.

        Args:
            title: Result title
            url: Result URL
            snippet: Result snippet/description
            **kwargs: Additional fields

        Returns:
            Formatted result dict
        """
        result = {
            "title": title,
            "url": url,
            "snippet": snippet,
            "source": self.name,
        }
        result.update(kwargs)
        return result

    async def is_available(self) -> bool:
        """
        Check if search engine is available.

        Returns:
            True if available, False otherwise
        """
        return self.available
