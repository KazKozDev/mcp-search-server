"""Utility functions for MCP Search Server."""

import asyncio
import time
from typing import Any, Callable, Dict, List
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple rate limiter to prevent API bans."""

    def __init__(self, calls_per_second: float = 2.0):
        """
        Initialize rate limiter.

        Args:
            calls_per_second: Maximum number of calls per second
        """
        self.calls_per_second = calls_per_second
        self.min_interval = 1.0 / calls_per_second
        self.last_call: Dict[str, float] = {}

    async def acquire(self, key: str = "default"):
        """
        Acquire permission to make a call.

        Args:
            key: Identifier for rate limiting (e.g., domain name)
        """
        now = time.time()
        last = self.last_call.get(key, 0)
        time_since_last = now - last

        if time_since_last < self.min_interval:
            wait_time = self.min_interval - time_since_last
            logger.debug(f"Rate limiting {key}: waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)

        self.last_call[key] = time.time()


# Global rate limiters for different services
rate_limiters = {
    "duckduckgo": RateLimiter(calls_per_second=1.0),
    "wikipedia": RateLimiter(calls_per_second=2.0),
    "web_parser": RateLimiter(calls_per_second=3.0),
    "pdf": RateLimiter(calls_per_second=1.0),
}


def get_rate_limiter(service: str) -> RateLimiter:
    """Get rate limiter for a service."""
    return rate_limiters.get(service, RateLimiter(calls_per_second=1.0))


async def run_parallel(*tasks: Callable, max_concurrent: int = 3) -> List[Any]:
    """
    Run multiple async tasks in parallel with concurrency limit.

    Args:
        *tasks: Async callables to execute
        max_concurrent: Maximum concurrent tasks

    Returns:
        List of results (or exceptions)
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async def wrapped_task(task_func):
        async with semaphore:
            try:
                return await task_func()
            except Exception as e:
                logger.error(f"Task failed: {e}")
                return {"error": str(e)}

    results = await asyncio.gather(*[wrapped_task(task) for task in tasks], return_exceptions=True)

    return results


async def run_parallel_searches(
    query: str, search_functions: List[tuple[str, Callable]], max_concurrent: int = 3
) -> Dict[str, Any]:
    """
    Run multiple search functions in parallel.

    Args:
        query: Search query
        search_functions: List of (name, search_func) tuples where search_func takes query as arg
        max_concurrent: Maximum concurrent searches

    Returns:
        Dict mapping search names to results
    """
    logger.info(f"Running {len(search_functions)} searches in parallel for: {query}")

    semaphore = asyncio.Semaphore(max_concurrent)

    async def run_search(name: str, func: Callable):
        async with semaphore:
            start = time.time()
            try:
                result = await func(query)
                duration = time.time() - start
                logger.info(f"{name} completed in {duration:.2f}s")
                return (name, result)
            except Exception as e:
                duration = time.time() - start
                logger.error(f"{name} failed after {duration:.2f}s: {e}")
                return (name, {"error": str(e)})

    # Run all searches in parallel
    tasks = [run_search(name, func) for name, func in search_functions]
    results_list = await asyncio.gather(*tasks, return_exceptions=True)

    # Convert to dict
    results_dict = {}
    for item in results_list:
        if isinstance(item, tuple) and len(item) == 2:
            name, result = item
            results_dict[name] = result
        elif isinstance(item, Exception):
            logger.error(f"Task exception: {item}")
            results_dict[f"error_{len(results_dict)}"] = {"error": str(item)}

    return results_dict


def with_rate_limit(service: str):
    """Decorator to add rate limiting to async functions."""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            limiter = get_rate_limiter(service)
            await limiter.acquire(service)
            return await func(*args, **kwargs)

        return wrapper

    return decorator


async def retry_with_backoff(
    func: Callable, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 10.0
) -> Any:
    """
    Retry an async function with exponential backoff.

    Args:
        func: Async function to retry
        max_retries: Maximum retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds

    Returns:
        Result from successful call

    Raises:
        Last exception if all retries fail
    """
    last_exception = None

    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            last_exception = e

            if attempt < max_retries - 1:
                delay = min(base_delay * (2**attempt), max_delay)
                logger.warning(f"Retry {attempt + 1}/{max_retries} after {delay:.1f}s. Error: {e}")
                await asyncio.sleep(delay)
            else:
                logger.error(f"All {max_retries} retries failed: {e}")

    raise last_exception


def measure_time(func):
    """Decorator to measure and log execution time."""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start
            logger.info(f"{func.__name__} completed in {duration:.2f}s")
            return result
        except Exception as e:
            duration = time.time() - start
            logger.error(f"{func.__name__} failed after {duration:.2f}s: {e}")
            raise

    return wrapper
