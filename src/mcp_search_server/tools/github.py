"""GitHub search tool for public repositories and code."""

import asyncio
import logging
from typing import List, Dict, Optional
import base64
import aiohttp

logger = logging.getLogger(__name__)


class GitHubSearchTool:
    """GitHub search tool for public repositories and code (No auth required)"""

    def __init__(self):
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "MCP-Search-Server/1.0",
        }
        self.request_delay = 2.0

    async def search_repositories(
        self, query: str, sort: str = "stars", max_results: int = 5
    ) -> Optional[List[Dict]]:
        """
        Search public repositories

        Args:
            query: Search query (e.g. "LLM agents language:python")
            sort: Sort field ('stars', 'forks', 'updated')
            max_results: Max repos to return

        Returns:
            List of repository metadata
        """
        # Rate limiting
        await asyncio.sleep(self.request_delay)

        params = {"q": query, "sort": sort, "order": "desc", "per_page": max_results}

        try:
            logger.info(f"Searching GitHub repos: {query}")
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/search/repositories",
                    params=params,
                    headers=self.headers,
                    timeout=10,
                ) as response:
                    if response.status == 403:
                        logger.warning("GitHub API rate limit exceeded")
                        return None

                    response.raise_for_status()
                    data = await response.json()

            repos = []
            for item in data.get("items", []):
                repos.append(
                    {
                        "name": item["name"],
                        "full_name": item["full_name"],
                        "description": item["description"],
                        "url": item["html_url"],
                        "stars": item["stargazers_count"],
                        "language": item["language"],
                        "updated_at": item["updated_at"][:10],
                        "source": "github_repo",
                    }
                )

            logger.info(f"Found {len(repos)} repositories")
            return repos

        except Exception as e:
            logger.error(f"GitHub repo search error: {e}")
            return None

    async def get_repo_readme(self, full_name: str) -> Optional[str]:
        """
        Get README content for a repository

        Args:
            full_name: 'owner/repo' string

        Returns:
            README content text
        """
        await asyncio.sleep(self.request_delay)

        try:
            logger.info(f"Fetching README for: {full_name}")
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/repos/{full_name}/readme", headers=self.headers, timeout=10
                ) as response:
                    if response.status == 404:
                        return None

                    response.raise_for_status()
                    data = await response.json()

            # Decode content
            if data.get("encoding") == "base64":
                content = base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
                return content

            return None

        except Exception as e:
            logger.error(f"Error fetching README: {e}")
            return None

    async def get_repo_files(self, full_name: str, path: str = "") -> Optional[List[str]]:
        """
        List files in repository directory

        Args:
            full_name: 'owner/repo'
            path: Directory path (empty for root)

        Returns:
            List of filenames
        """
        await asyncio.sleep(self.request_delay)

        try:
            url = f"{self.base_url}/repos/{full_name}/contents/{path}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers, timeout=10) as response:
                    if response.status != 200:
                        return None

                    items = await response.json()

            if isinstance(items, list):
                return [item["name"] for item in items]
            return []

        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return None

    async def get_file_content(self, full_name: str, path: str) -> Optional[str]:
        """
        Get raw content of a specific file

        Args:
            full_name: 'owner/repo'
            path: File path

        Returns:
            File content
        """
        await asyncio.sleep(self.request_delay)

        try:
            # Use raw.githubusercontent.com for better reliability
            url = f"https://raw.githubusercontent.com/{full_name}/master/{path}"

            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 404:
                        url = f"https://raw.githubusercontent.com/{full_name}/main/{path}"
                        async with session.get(url, timeout=10) as response2:
                            if response2.status == 200:
                                return await response2.text()
                            # Fallback to API
                            return await self._get_file_content_api(full_name, path)

                    if response.status == 200:
                        return await response.text()

            # Fallback to API
            return await self._get_file_content_api(full_name, path)

        except Exception as e:
            logger.error(f"Error fetching file content: {e}")
            return None

    async def _get_file_content_api(self, full_name: str, path: str) -> Optional[str]:
        """Fallback to API if raw content fails"""
        try:
            url = f"{self.base_url}/repos/{full_name}/contents/{path}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("encoding") == "base64":
                            return base64.b64decode(data["content"]).decode(
                                "utf-8", errors="ignore"
                            )
            return None
        except Exception:
            return None


# Global instance
_github_tool = GitHubSearchTool()


# Exported async functions
async def search_github_repos(
    query: str, sort: str = "stars", max_results: int = 5
) -> Optional[List[Dict]]:
    """Search public repositories"""
    return await _github_tool.search_repositories(query, sort, max_results)


async def get_github_readme(full_name: str) -> Optional[str]:
    """Get README content for a repository"""
    return await _github_tool.get_repo_readme(full_name)


async def list_github_files(full_name: str, path: str = "") -> Optional[List[str]]:
    """List files in repository directory"""
    return await _github_tool.get_repo_files(full_name, path)


async def get_github_file(full_name: str, path: str) -> Optional[str]:
    """Get raw content of a specific file"""
    return await _github_tool.get_file_content(full_name, path)
