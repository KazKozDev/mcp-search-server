"""DuckDuckGo search implementation using Selenium for MCP server."""

import asyncio
import logging
import time
import tempfile
from typing import Dict, List, Optional

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

from ..cache_store import get_cached_json, set_cached_json
from ..config_loader import (
    get_cache_ttl_seconds,
    get_dedupe_enabled,
    get_normalize_urls_enabled,
    get_results_max_per_domain,
    get_title_similarity_threshold,
)
from ..result_utils import dedupe_and_limit_results

logger = logging.getLogger(__name__)


def _contains_cyrillic(text: str) -> bool:
    """Check if text contains Cyrillic characters."""
    return any("\u0400" <= ch <= "\u04ff" for ch in text)


def _default_region_for_query(query: str) -> str:
    """Determine default region based on query."""
    return "ru-ru" if _contains_cyrillic(query) else "wt-wt"


class DuckDuckGoSeleniumSearcher:
    """Selenium-based DuckDuckGo searcher that avoids blocking."""

    def __init__(self, headless: bool = True, timeout: int = 30):
        """Initialize the Selenium searcher."""
        self.headless = headless
        self.timeout = timeout
        self.driver = None
        self._temp_dir = tempfile.mkdtemp()

    def _setup_driver(self) -> webdriver.Chrome:
        """Set up Chrome WebDriver with anti-detection options."""
        chrome_options = Options()

        if self.headless:
            chrome_options.add_argument("--headless")

        # Set window size
        chrome_options.add_argument("--window-size=1920,1080")

        # Use realistic user agent
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        # Additional options for stability and anti-detection
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)

        # Initialize driver
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=chrome_options
        )

        # Execute CDP commands to prevent detection
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
        )

        driver.set_page_load_timeout(self.timeout)

        return driver

    def _extract_search_result(self, element, _position: int) -> Optional[Dict]:
        """Extract search result from a web element."""
        try:
            # Get full text
            full_text = element.text
            if not full_text:
                return None

            lines = full_text.split("\n")

            # Extract title (usually first line)
            title = lines[0] if lines else "No title"

            # Extract URL
            url = None

            # Try to find <a> elements with different approaches
            a_elements = element.find_elements(By.TAG_NAME, "a")
            for a in a_elements:
                href = a.get_attribute("href")
                if href and not href.startswith("javascript") and "duckduckgo.com" not in href:
                    url = href
                    break

            # Try specific selectors for links if not found
            if not url:
                link_selectors = [
                    "a.result__a",
                    "a.result-link",
                    "a.result__url",
                    "a[data-testid='result-title-a']",
                    "a.eVNpHGjtxRBq_gLOfGDr",
                    "a[data-testid='result-title-link']",
                ]

                for selector in link_selectors:
                    try:
                        link_element = element.find_element(By.CSS_SELECTOR, selector)
                        href = link_element.get_attribute("href")
                        if (
                            href
                            and not href.startswith("javascript")
                            and "duckduckgo.com" not in href
                        ):
                            url = href
                            break
                    except NoSuchElementException:
                        continue

            # Extract snippet
            snippet_parts = []
            import re

            url_pattern = re.compile(r"^(https?://|www\.)")

            for line in lines[1:]:
                if line and not url_pattern.match(line) and line != title:
                    # Skip short timestamps or domain names
                    if not re.match(r"^\d+[hmd]$", line.strip()) and len(line.strip()) > 2:
                        snippet_parts.append(line)

            snippet = " ".join(snippet_parts) if snippet_parts else "No snippet available"

            if not url:
                return None

            return {
                "title": title,
                "url": url,
                "snippet": snippet,
                "source": "duckduckgo_selenium",
            }

        except Exception as e:
            logger.debug(f"Error extracting result: {str(e)}")
            return None

    async def search(
        self, query: str, limit: int = 10, _region: Optional[str] = None
    ) -> List[Dict]:
        """Search DuckDuckGo using Selenium."""
        start_time = time.time()

        try:
            logger.info(f"Searching DuckDuckGo with Selenium for: {query}")

            # Set up driver if not already done
            if not self.driver:
                self.driver = self._setup_driver()

            # Navigate to DuckDuckGo
            self.driver.get("https://duckduckgo.com/")

            # Find search box
            search_box = None
            for selector in ["searchbox_input", "q"]:
                try:
                    if selector == "searchbox_input":
                        search_box = WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((By.ID, selector))
                        )
                    else:
                        search_box = WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((By.NAME, selector))
                        )
                    break
                except TimeoutException:
                    continue

            if not search_box:
                raise TimeoutException("Could not find search box")

            # Enter search query
            search_box.clear()
            search_box.send_keys(query)
            search_box.send_keys(Keys.RETURN)

            # Wait for results
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located(
                        (
                            By.CSS_SELECTOR,
                            ".react-results--main, .serp__results, article, .result",
                        )
                    )
                )
            except TimeoutException:
                logger.warning("Timed out waiting for search results")

            # Scroll to load more results
            for i in range(3):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                await asyncio.sleep(1.5)

            # Scroll back to top
            self.driver.execute_script("window.scrollTo(0, 0);")
            await asyncio.sleep(0.5)

            # Extract results
            results = []

            # Try different selectors
            result_selectors = [
                "article",
                ".result__body",
                ".nrn-react-div article",
                ".result",
                "div[data-testid='result']",
                ".react-results--main .react-results--result",
                ".react-results--main article",
                ".react-results--main .result",
                ".react-results--main .web-result",
                ".web-result",
            ]

            search_elements = []
            for selector in result_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        search_elements = elements
                        logger.debug(f"Found {len(elements)} results with selector: {selector}")
                        break
                except Exception:
                    continue

            # Process results
            for i, element in enumerate(search_elements[:limit], 1):
                result = self._extract_search_result(element, i)
                if result:
                    results.append(result)

            search_time = time.time() - start_time
            logger.info(f"Found {len(results)} results in {search_time:.2f}s")

            return results

        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            return []

    def close(self):
        """Close the browser and clean up resources."""
        try:
            if self.driver:
                self.driver.quit()
        except Exception as e:
            logger.warning(f"Error closing WebDriver: {e}")
        self.driver = None

    def __del__(self):
        """Cleanup on deletion."""
        self.close()


async def search_duckduckgo(
    query: str,
    limit: int = 10,
    timelimit: Optional[str] = None,
    mode: str = "web",
    region: Optional[str] = None,
    no_cache: bool = False,
) -> List[Dict]:
    """
    Search DuckDuckGo using Selenium.

    Args:
        query: Search query
        limit: Maximum number of results
        timelimit: Time limit filter (currently not supported with Selenium)
        mode: Search mode (web or news)
        region: Region for search
        no_cache: Disable caching

    Returns:
        List of search results
    """
    effective_region = region or _default_region_for_query(query)
    cache_key = f"mode={mode}|region={effective_region}|timelimit={timelimit}|q={query}"

    # Check cache first
    cache_kind = "news" if mode == "news" else "web"
    cached_results = get_cached_json(
        cache_key, get_cache_ttl_seconds(cache_kind), no_cache=no_cache
    )
    if cached_results is not None:
        logger.info(f"Using cached results for '{cache_key}'")
        return cached_results[:limit]

    # Create searcher and perform search
    searcher = DuckDuckGoSeleniumSearcher(headless=True, timeout=30)
    try:
        results = await searcher.search(query, limit, effective_region)

        # Apply deduplication if enabled
        if get_dedupe_enabled():
            results = dedupe_and_limit_results(
                results,
                max_per_domain=get_results_max_per_domain(),
                similarity_threshold=get_title_similarity_threshold(),
                normalize_urls=get_normalize_urls_enabled(),
            )

        # Cache results
        set_cached_json(cache_key, results, no_cache=no_cache)

        return results[:limit]

    finally:
        searcher.close()
