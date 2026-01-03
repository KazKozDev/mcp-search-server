"""Social platforms and code repository tools."""

from .github import search_github_repos as search_github, get_github_readme
from .reddit import search_reddit, get_reddit_comments

__all__ = [
    "search_github",
    "get_github_readme",
    "search_reddit",
    "get_reddit_comments",
]
