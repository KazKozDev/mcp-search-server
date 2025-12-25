"""Browser-based search engine using Playwright for JavaScript rendering."""

import logging
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Try to import Playwright
try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
    logger.warning(
        "Playwright not installed. Browser-based engines (Brave, Startpage) will be disabled. "
        "Install with: pip install playwright && playwright install chromium"
    )


class BrowserEngine:
    """Base class for browser-based search engines using Playwright."""

    def __init__(self, name: str, base_url: str):
        """
        Initialize browser engine.

        Args:
            name: Engine name
            base_url: Base search URL
        """
        self.name = name
        self.base_url = base_url
        self.available = HAS_PLAYWRIGHT
        self.timeout = 10000  # 10 seconds

    async def search_with_browser(self, url: str, wait_for_selector: str = "body") -> Optional[str]:
        """
        Fetch page using headless browser.

        Args:
            url: URL to fetch
            wait_for_selector: CSS selector to wait for

        Returns:
            HTML content or None if error
        """
        if not self.available:
            logger.error(f"{self.name}: Playwright not available")
            return None

        try:
            async with async_playwright() as p:
                # Try Firefox first (more stable on macOS), fallback to Chromium
                try:
                    browser = await p.firefox.launch(
                        headless=True,
                        firefox_user_prefs={
                            "dom.webdriver.enabled": False,
                            "useAutomationExtension": False,
                        },
                    )
                    logger.debug(f"{self.name}: Using Firefox browser")
                except Exception as firefox_error:
                    logger.warning(
                        f"{self.name}: Firefox failed ({firefox_error}), trying Chromium"
                    )
                    browser = await p.chromium.launch(
                        headless=True,
                        args=[
                            "--disable-blink-features=AutomationControlled",
                            "--disable-dev-shm-usage",
                            "--no-sandbox",
                        ],
                    )
                    logger.debug(f"{self.name}: Using Chromium browser")

                # Create context with realistic settings
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080},
                    locale="en-US",
                    extra_http_headers={
                        "Accept-Language": "en-US,en;q=0.9",
                    },
                )

                # Open page
                page = await context.new_page()

                # Navigate and wait for content
                await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)

                # Wait for specific selector
                try:
                    await page.wait_for_selector(wait_for_selector, timeout=5000)
                except PlaywrightTimeout:
                    logger.warning(f"Timeout waiting for selector '{wait_for_selector}'")

                # Get HTML content
                html = await page.content()

                # Close browser
                await context.close()
                await browser.close()

                return html

        except Exception as e:
            logger.error(f"{self.name}: Browser error: {e}")
            return None

    def parse_html(
        self,
        html: str,
        result_selector: str,
        title_selector: str,
        url_selector: str,
        snippet_selector: str,
        max_results: int,
    ) -> List[Dict]:
        """
        Parse HTML and extract search results.

        Args:
            html: HTML content
            result_selector: CSS selector for result containers
            title_selector: CSS selector for titles (relative to result)
            url_selector: CSS selector for URLs (relative to result)
            snippet_selector: CSS selector for snippets (relative to result)
            max_results: Maximum number of results

        Returns:
            List of parsed results
        """
        try:
            soup = BeautifulSoup(html, "html.parser")
            results = []

            # Find all result containers
            result_divs = soup.select(result_selector)[:max_results]

            for div in result_divs:
                try:
                    # Extract title and URL
                    title_elem = div.select_one(title_selector)
                    if not title_elem:
                        continue

                    title = title_elem.get_text(strip=True)

                    # Get URL - might be in href or data attribute
                    url_elem = div.select_one(url_selector)
                    if not url_elem:
                        continue

                    url = url_elem.get("href") or url_elem.get("data-url", "")

                    # Extract snippet
                    snippet_elem = div.select_one(snippet_selector)
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                    if url and title:
                        results.append(
                            {
                                "title": title,
                                "url": url,
                                "snippet": snippet,
                                "source": self.name,
                            }
                        )

                except Exception as e:
                    logger.debug(f"Error parsing result: {e}")
                    continue

            return results

        except Exception as e:
            logger.error(f"Error parsing HTML: {e}")
            return []
