"""Reddit search tool using public JSON API."""

import asyncio
import logging
import random
from typing import List, Dict, Optional
from datetime import datetime
import aiohttp

logger = logging.getLogger(__name__)


class RedditSearchTool:
    """Reddit search tool using public JSON API (No auth required)"""

    def __init__(self):
        self.base_url = "https://www.reddit.com"
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        ]
        self.request_delay = 2.0

    def _get_headers(self) -> Dict:
        """Get headers with random User-Agent"""
        return {"User-Agent": random.choice(self.user_agents), "Accept": "application/json"}

    async def search(
        self,
        query: str,
        subreddit: str = None,
        limit: int = 10,
        sort: str = "relevance",
        time_filter: str = "all",
    ) -> Optional[List[Dict]]:
        """
        Search Reddit posts

        Args:
            query: Search query
            subreddit: Optional subreddit to search in (e.g. "LocalLLaMA")
            limit: Max results (max 100)
            sort: 'relevance', 'hot', 'top', 'new', 'comments'
            time_filter: 'hour', 'day', 'week', 'month', 'year', 'all'

        Returns:
            List of posts metadata
        """
        await asyncio.sleep(self.request_delay)

        try:
            if subreddit:
                url = f"{self.base_url}/r/{subreddit}/search.json"
                params = {
                    "q": query,
                    "restrict_sr": "on",
                    "limit": limit,
                    "sort": sort,
                    "t": time_filter,
                }
            else:
                url = f"{self.base_url}/search.json"
                params = {"q": query, "limit": limit, "sort": sort, "t": time_filter}

            logger.info(f"Searching Reddit: {query} (subreddit: {subreddit})")

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, params=params, headers=self._get_headers(), timeout=10
                ) as response:
                    if response.status == 429:
                        logger.warning("Reddit API rate limit exceeded")
                        return None

                    response.raise_for_status()
                    data = await response.json()

            posts = []
            for child in data.get("data", {}).get("children", []):
                post = child.get("data", {})
                selftext = post.get("selftext", "")
                posts.append(
                    {
                        "title": post.get("title"),
                        "subreddit": post.get("subreddit"),
                        "author": post.get("author"),
                        "score": post.get("score"),
                        "num_comments": post.get("num_comments"),
                        "url": f"https://www.reddit.com{post.get('permalink')}",
                        "text": (
                            selftext[:500] + "..." if selftext and len(selftext) > 500 else selftext
                        ),
                        "created_utc": datetime.fromtimestamp(post.get("created_utc", 0)).strftime(
                            "%Y-%m-%d"
                        ),
                        "source": "reddit",
                    }
                )

            logger.info(f"Found {len(posts)} Reddit posts")
            return posts

        except Exception as e:
            logger.error(f"Reddit search error: {e}")
            return None

    async def get_post_comments(self, url: str, limit: int = 10) -> Optional[List[Dict]]:
        """
        Get comments for a specific post

        Args:
            url: Full post URL or permalink
            limit: Max comments to return

        Returns:
            List of comments
        """
        await asyncio.sleep(self.request_delay)

        try:
            # Ensure URL ends with .json
            if not url.endswith(".json"):
                # Handle cases with query parameters
                if "?" in url:
                    base, query = url.split("?", 1)
                    if not base.endswith("/"):
                        base += "/"
                    url = f"{base}.json?{query}"
                else:
                    if not url.endswith("/"):
                        url += "/"
                    url += ".json"

            logger.info(f"Fetching comments from: {url}")

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self._get_headers(), timeout=10) as response:
                    if response.status != 200:
                        return None

                    data = await response.json()

            # Reddit returns a list: [post_data, comments_data]
            if not isinstance(data, list) or len(data) < 2:
                return None

            comments = []
            comments_data = data[1].get("data", {}).get("children", [])

            for child in comments_data[:limit]:
                comment = child.get("data", {})
                # Skip "more" objects (pagination)
                if comment.get("kind") == "more":
                    continue

                comments.append(
                    {
                        "author": comment.get("author"),
                        "body": comment.get("body"),
                        "score": comment.get("score"),
                        "created_utc": datetime.fromtimestamp(
                            comment.get("created_utc", 0)
                        ).strftime("%Y-%m-%d"),
                    }
                )

            return comments

        except Exception as e:
            logger.error(f"Error fetching comments: {e}")
            return None

    async def get_subreddit_hot(self, subreddit: str, limit: int = 10) -> Optional[List[Dict]]:
        """Get hot posts from a subreddit"""
        await asyncio.sleep(self.request_delay)

        try:
            url = f"{self.base_url}/r/{subreddit}/hot.json"
            params = {"limit": limit}

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, params=params, headers=self._get_headers(), timeout=10
                ) as response:
                    response.raise_for_status()
                    data = await response.json()

            posts = []
            for child in data.get("data", {}).get("children", []):
                post = child.get("data", {})
                posts.append(
                    {
                        "title": post.get("title"),
                        "score": post.get("score"),
                        "url": f"https://www.reddit.com{post.get('permalink')}",
                        "source": "reddit_hot",
                    }
                )

            return posts
        except Exception:
            return None


# Global instance
_reddit_tool = RedditSearchTool()


# Exported async functions
async def search_reddit(
    query: str,
    subreddit: str = None,
    limit: int = 10,
    sort: str = "relevance",
    time_filter: str = "all",
) -> Optional[List[Dict]]:
    """Search Reddit posts"""
    return await _reddit_tool.search(query, subreddit, limit, sort, time_filter)


async def get_reddit_comments(url: str, limit: int = 10) -> Optional[List[Dict]]:
    """Get comments for a specific post"""
    return await _reddit_tool.get_post_comments(url, limit)


async def get_reddit_hot(subreddit: str, limit: int = 10) -> Optional[List[Dict]]:
    """Get hot posts from a subreddit"""
    return await _reddit_tool.get_subreddit_hot(subreddit, limit)
