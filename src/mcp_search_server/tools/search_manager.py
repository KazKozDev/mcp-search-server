"""Search manager with smart fallback logic."""

import logging
from typing import List, Dict, Optional

from .duckduckgo import DuckDuckGoSearchTool

logger = logging.getLogger(__name__)


class SearchManager:
    """
    Manages multiple search engines with smart fallback.

    Currently uses DuckDuckGo as primary engine.
    """

    def __init__(self, min_results: int = 3):
        """
        Initialize search manager.

        Args:
            min_results: Minimum number of results before trying fallback
        """
        self.min_results = min_results

        # Initialize search engines
        self.engines = {
            "duckduckgo": DuckDuckGoSearchTool(),
        }

        # Fallback order
        self.fallback_order = ["duckduckgo"]

        logger.info(f"SearchManager initialized with engines: {self.fallback_order}")

    async def search(
        self,
        query: str,
        max_results: int = 10,
        timelimit: Optional[str] = None,
        mode: str = "web",
    ) -> Optional[List[Dict]]:
        """
        Search with smart fallback.

        Args:
            query: Search query
            max_results: Maximum number of results
            timelimit: Time filter ('d', 'w', 'm', 'y')
            mode: Search mode ('web' or 'news')

        Returns:
            List of search results or None if all engines fail
        """
        all_results = []
        engines_tried = []

        for engine_name in self.fallback_order:
            try:
                engine = self.engines.get(engine_name)
                if not engine:
                    continue

                logger.info(
                    f"Trying {engine_name} for query: '{query}' (mode={mode}, tried={engines_tried})"
                )
                engines_tried.append(engine_name)

                # Call appropriate search method
                if mode == "news":
                    # Check if engine supports news search
                    if hasattr(engine, "search_news"):
                        results = await engine.search_news(
                            query=query,
                            max_results=max_results,
                            timelimit=timelimit,
                        )
                    else:
                        # For DuckDuckGo, use the existing search method
                        if engine_name == "duckduckgo":
                            from .duckduckgo import _ddg_tool

                            results = await _ddg_tool.search_news(
                                query=query,
                                max_results=max_results,
                                timelimit=timelimit or "m",
                            )
                        else:
                            results = None
                else:
                    # Web search
                    if hasattr(engine, "search"):
                        results = await engine.search(
                            query=query,
                            max_results=max_results,
                            timelimit=timelimit,
                        )
                    else:
                        # For DuckDuckGo, use existing search method
                        if engine_name == "duckduckgo":
                            from .duckduckgo import _ddg_tool

                            results = await _ddg_tool.search(
                                query=query,
                                max_results=max_results,
                                timelimit=timelimit,
                            )
                        else:
                            results = None

                if results and len(results) > 0:
                    all_results.extend(results)
                    logger.info(
                        f"{engine_name} returned {len(results)} results (total: {len(all_results)})"
                    )

                    # Check if we have enough results
                    if len(all_results) >= self.min_results:
                        logger.info(
                            f"Got enough results ({len(all_results)} >= {self.min_results}), "
                            f"stopping fallback chain"
                        )
                        break
                else:
                    logger.warning(f"{engine_name} returned no results for '{query}'")

            except Exception as e:
                logger.error(f"Error with {engine_name}: {e}")
                continue

        if not all_results:
            logger.error(f"All search engines failed for query: '{query}' (tried: {engines_tried})")
            return None

        # Remove duplicates by URL while preserving order
        seen_urls = set()
        unique_results = []
        for result in all_results:
            url = result.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(result)

        logger.info(
            f"Search complete: {len(unique_results)} unique results from engines: {engines_tried}"
        )

        return unique_results[:max_results]

    async def search_with_engine(
        self,
        query: str,
        engine: str,
        max_results: int = 10,
        timelimit: Optional[str] = None,
        mode: str = "web",
    ) -> Optional[List[Dict]]:
        """
        Search using specific engine (no fallback).

        Args:
            query: Search query
            engine: Engine name ('duckduckgo', 'brave', 'startpage')
            max_results: Maximum number of results
            timelimit: Time filter
            mode: Search mode

        Returns:
            List of search results or None if error
        """
        engine_obj = self.engines.get(engine)
        if not engine_obj:
            logger.error(f"Unknown search engine: {engine}")
            return None

        logger.info(f"Using {engine} for query: '{query}' (mode={mode})")

        try:
            if mode == "news":
                if hasattr(engine_obj, "search_news"):
                    return await engine_obj.search_news(
                        query=query,
                        max_results=max_results,
                        timelimit=timelimit,
                    )
                elif engine == "duckduckgo":
                    from .duckduckgo import _ddg_tool

                    return await _ddg_tool.search_news(
                        query=query,
                        max_results=max_results,
                        timelimit=timelimit or "m",
                    )
            else:
                if hasattr(engine_obj, "search"):
                    return await engine_obj.search(
                        query=query,
                        max_results=max_results,
                        timelimit=timelimit,
                    )
                elif engine == "duckduckgo":
                    from .duckduckgo import _ddg_tool

                    return await _ddg_tool.search(
                        query=query,
                        max_results=max_results,
                        timelimit=timelimit,
                    )

        except Exception as e:
            logger.error(f"Error searching with {engine}: {e}")
            return None


# Global search manager instance
_search_manager = SearchManager(min_results=3)
