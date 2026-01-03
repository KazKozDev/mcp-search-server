"""
Async link parser with multiple fallback methods and robust error handling.
Supports: Trafilatura, Readability, Newspaper3k, BeautifulSoup, Selenium
Features: Retry logic, caching, metadata extraction, boilerplate removal
"""

import asyncio
import hashlib
import json
import logging
import random
import re
import ssl
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any
from urllib.parse import urlparse

import aiohttp
import certifi
from bs4 import BeautifulSoup
from newspaper import Article
from readability import Document

logger = logging.getLogger(__name__)

# Trafilatura - one of the best content extraction libraries
try:
    import trafilatura
    from trafilatura.settings import use_config

    TRAFILATURA_AVAILABLE = True
except ImportError:
    TRAFILATURA_AVAILABLE = False

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager

    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

# Undetected ChromeDriver - bypasses most bot detection
try:
    import undetected_chromedriver as uc

    UNDETECTED_AVAILABLE = True
except ImportError:
    UNDETECTED_AVAILABLE = False

# Rotate User-Agents to reduce blocking
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

# Maximum content size to download (5MB)
MAX_CONTENT_SIZE = 5 * 1024 * 1024

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY_BASE = 1.0  # Base delay in seconds, will be exponentially increased

# Selenium configuration
SELENIUM_TIMEOUT = 30  # Timeout for page load
USE_SELENIUM_FOR_403 = True  # Try Selenium when getting 403 errors

# Cache configuration
ENABLE_CACHE = True
CACHE_TTL_HOURS = 24  # Cache results for 24 hours
_content_cache: Dict[str, Tuple[Any, datetime]] = {}


@dataclass
class ArticleMetadata:
    """Structured article metadata."""

    title: Optional[str] = None
    author: Optional[str] = None
    date: Optional[str] = None
    description: Optional[str] = None
    language: Optional[str] = None
    url: Optional[str] = None
    content: str = ""
    method: str = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_text(self, include_metadata: bool = True) -> str:
        """Format as readable text with optional metadata header."""
        parts = []
        if include_metadata:
            if self.title:
                parts.append(f"# {self.title}")
            meta_parts = []
            if self.author:
                meta_parts.append(f"Author: {self.author}")
            if self.date:
                meta_parts.append(f"Date: {self.date}")
            if meta_parts:
                parts.append(" | ".join(meta_parts))
            if parts:
                parts.append("")  # Empty line before content
        parts.append(self.content)
        return "\n".join(parts)


def _get_cache_key(url: str) -> str:
    """Generate cache key for URL."""
    return hashlib.md5(url.encode()).hexdigest()


def _get_from_cache(url: str) -> Optional[ArticleMetadata]:
    """Get cached result if exists and not expired."""
    if not ENABLE_CACHE:
        return None

    cache_key = _get_cache_key(url)
    if cache_key in _content_cache:
        result, timestamp = _content_cache[cache_key]
        if datetime.now() - timestamp < timedelta(hours=CACHE_TTL_HOURS):
            logger.debug(f"Cache hit for {url}")
            return result
        else:
            # Expired, remove from cache
            del _content_cache[cache_key]
    return None


def _set_cache(url: str, result: ArticleMetadata) -> None:
    """Store result in cache."""
    if not ENABLE_CACHE:
        return

    cache_key = _get_cache_key(url)
    _content_cache[cache_key] = (result, datetime.now())

    # Limit cache size (keep last 1000 entries)
    if len(_content_cache) > 1000:
        oldest_key = min(_content_cache, key=lambda k: _content_cache[k][1])
        del _content_cache[oldest_key]


def get_random_user_agent() -> str:
    """Get a random User-Agent string."""
    return random.choice(USER_AGENTS)


def create_ssl_context() -> ssl.SSLContext:
    """Create a secure SSL context with certifi certificates."""
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    return ssl_context


def create_chrome_driver(headless: bool = True):
    """Create a Chrome WebDriver with stealth settings to avoid detection."""
    if not SELENIUM_AVAILABLE:
        raise ImportError("Selenium is not available")

    chrome_options = ChromeOptions()

    if headless:
        chrome_options.add_argument("--headless=new")

    # Stealth settings to avoid bot detection
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    # Random user agent
    user_agent = get_random_user_agent()
    chrome_options.add_argument(f"user-agent={user_agent}")

    # Additional settings to appear more like a real browser
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--dns-prefetch-disable")
    chrome_options.add_argument("--ignore-certificate-errors")

    # Set preferences to avoid detection
    prefs = {
        "profile.default_content_setting_values.notifications": 2,
        "profile.default_content_settings.popups": 0,
    }
    chrome_options.add_experimental_option("prefs", prefs)

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        # Execute CDP commands to hide webdriver
        driver.execute_cdp_cmd(
            "Network.setUserAgentOverride",
            {"userAgent": user_agent.replace("HeadlessChrome", "Chrome")},
        )
        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        return driver
    except Exception as e:
        logger.error(f"Failed to create Chrome driver: {e}")
        raise


class AsyncLinkParser:
    """
    Asynchronous link parser with multiple extraction methods:
    1. BeautifulSoup (fast, simple HTML)
    2. Newspaper3k (article-focused)
    3. Readability (content extraction)
    """

    def __init__(self, timeout: int = 10, max_content_length: int = 500000):
        self.timeout = timeout
        self.max_content_length = max_content_length

    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Check if the given string is a valid URL."""
        if not url:
            return False
        try:
            result = urlparse(url)
            # Check for valid scheme and netloc
            if result.scheme not in ("http", "https"):
                return False
            if not result.netloc or len(result.netloc) < 3:
                return False
            # Basic check for valid domain
            if "." not in result.netloc and result.netloc != "localhost":
                return False
            return True
        except Exception as e:
            logger.error(f"Error validating URL {url}: {e}")
            return False


async def fetch_html_with_retry(
    url: str, session: aiohttp.ClientSession, timeout: int = 10, max_retries: int = MAX_RETRIES
) -> Tuple[Optional[str], Optional[str]]:
    """
    Fetch HTML content with retry logic and proper error handling.

    Returns: (html_content, error_message)
    """
    last_error = None

    for attempt in range(max_retries):
        try:
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=timeout),
                allow_redirects=True,
                max_redirects=5,
            ) as response:
                # Handle rate limiting
                if response.status == 429:
                    retry_after = response.headers.get(
                        "Retry-After", str(RETRY_DELAY_BASE * (2**attempt))
                    )
                    wait_time = min(float(retry_after), 30)  # Cap at 30 seconds
                    logger.warning(
                        f"Rate limited on {url}, waiting {wait_time}s (attempt {attempt + 1})"
                    )
                    await asyncio.sleep(wait_time)
                    continue

                # Handle server errors with retry
                if response.status >= 500:
                    wait_time = RETRY_DELAY_BASE * (2**attempt)
                    logger.warning(
                        f"Server error {response.status} on {url}, retrying in {wait_time}s"
                    )
                    await asyncio.sleep(wait_time)
                    continue

                response.raise_for_status()

                # Check content length before downloading
                content_length = response.headers.get("Content-Length")
                if content_length and int(content_length) > MAX_CONTENT_SIZE:
                    return None, f"Content too large: {content_length} bytes"

                # Check content type
                content_type = response.headers.get("Content-Type", "")
                if not any(
                    ct in content_type.lower()
                    for ct in ["text/html", "application/xhtml", "text/plain"]
                ):
                    if "application/pdf" in content_type.lower():
                        return None, "PDF content detected - use PDF parser"
                    if not content_type or "text" not in content_type.lower():
                        logger.warning(f"Unexpected content type: {content_type}")

                # Read content with size limit
                chunks = []
                total_size = 0
                async for chunk in response.content.iter_chunked(8192):
                    total_size += len(chunk)
                    if total_size > MAX_CONTENT_SIZE:
                        logger.warning(f"Content exceeded size limit for {url}")
                        break
                    chunks.append(chunk)

                # Detect encoding
                html_bytes = b"".join(chunks)
                encoding = response.charset or "utf-8"

                # Try to decode with detected encoding, fallback to utf-8 with errors='replace'
                try:
                    html = html_bytes.decode(encoding)
                except (UnicodeDecodeError, LookupError):
                    try:
                        html = html_bytes.decode("utf-8", errors="replace")
                    except Exception:
                        html = html_bytes.decode("latin-1", errors="replace")

                return html, None

        except asyncio.TimeoutError:
            last_error = "Timeout"
            wait_time = RETRY_DELAY_BASE * (2**attempt)
            if attempt < max_retries - 1:
                logger.warning(
                    f"Timeout on {url}, retrying in {wait_time}s (attempt {attempt + 1})"
                )
                await asyncio.sleep(wait_time)
        except aiohttp.ClientResponseError as e:
            last_error = f"HTTP {e.status}: {e.message}"
            if e.status in (401, 403, 404):
                # Don't retry on auth/not found errors
                break
            wait_time = RETRY_DELAY_BASE * (2**attempt)
            if attempt < max_retries - 1:
                await asyncio.sleep(wait_time)
        except aiohttp.ClientError as e:
            last_error = str(e)
            wait_time = RETRY_DELAY_BASE * (2**attempt)
            if attempt < max_retries - 1:
                logger.warning(f"Client error on {url}: {e}, retrying in {wait_time}s")
                await asyncio.sleep(wait_time)
        except Exception as e:
            last_error = str(e)
            logger.error(f"Unexpected error fetching {url}: {e}")
            break

    return None, f"Error after {max_retries} attempts: {last_error}"


async def method1_bs4_async(url: str, session: aiohttp.ClientSession) -> str:
    """Parse main content from URL using BeautifulSoup (async)."""
    logger.debug(f"Method 1 (BeautifulSoup) attempting: {url}")

    html, error = await fetch_html_with_retry(url, session, timeout=10)
    if error:
        return f"Error: {error}"

    try:
        loop = asyncio.get_running_loop()
        content = await loop.run_in_executor(None, _parse_bs4, html, url)
        return content
    except Exception as e:
        logger.error(f"Error parsing with BS4 for {url}: {e}")
        return f"Error: {str(e)}"


def _parse_bs4(html: str, url: str) -> str:
    """CPU-bound BeautifulSoup parsing with improved content extraction."""
    soup = BeautifulSoup(html, "html.parser")

    # Remove unwanted elements
    unwanted_tags = [
        "script",
        "style",
        "nav",
        "header",
        "footer",
        "aside",
        "form",
        "button",
        "input",
        "noscript",
        "iframe",
        "svg",
        "video",
        "audio",
        "canvas",
        "map",
        "object",
        "embed",
    ]
    for tag in soup.find_all(unwanted_tags):
        tag.decompose()

    # Remove elements with common ad/navigation classes
    ad_classes = [
        "ad",
        "ads",
        "advertisement",
        "sidebar",
        "menu",
        "navigation",
        "comment",
        "social",
        "share",
    ]
    for element in soup.find_all(class_=lambda c: c and any(ad in c.lower() for ad in ad_classes)):
        element.decompose()

    article_content = ""

    # Try to find article content with priority order
    # 1. <article> tag
    article_tag = soup.find("article")
    if article_tag:
        for p in article_tag.find_all("p"):
            article_content += p.get_text(separator="\n", strip=True) + "\n\n"
        if article_content.strip():
            return article_content.strip()

    # 2. <main> tag
    main_tag = soup.find("main")
    if main_tag:
        for p in main_tag.find_all("p"):
            article_content += p.get_text(separator="\n", strip=True) + "\n\n"
        if article_content.strip():
            return article_content.strip()

    # 3. Content divs with semantic class names
    content_divs = soup.find_all(
        "div",
        class_=lambda c: c
        and any(
            key in c.lower()
            for key in ["content", "article", "main", "body", "post", "entry", "text"]
        ),
    )
    for div in content_divs:
        for p in div.find_all("p"):
            article_content += p.get_text(separator="\n", strip=True) + "\n\n"
        if article_content.strip():
            return article_content.strip()

    # 4. Fallback to all paragraphs
    if not article_content:
        paragraphs = soup.find_all("p")
        for p in paragraphs:
            text = p.get_text(separator="\n", strip=True)
            # Filter out very short paragraphs (likely navigation/buttons)
            if len(text) > 30:
                article_content += text + "\n\n"

    return article_content.strip()


async def method2_newspaper_async(url: str, session: aiohttp.ClientSession) -> str:
    """Parse content using Newspaper3k (async-safe version)."""
    logger.debug(f"Method 2 (Newspaper3k) attempting: {url}")
    try:
        # Fetch HTML using our robust async method first
        html, error = await fetch_html_with_retry(url, session, timeout=10)
        if error:
            return f"Error: {error}"

        loop = asyncio.get_running_loop()
        content = await loop.run_in_executor(None, _newspaper_parse_html, html, url)
        return content
    except Exception as e:
        logger.error(f"Error in method2_newspaper for {url}: {e}")
        return f"Error: {str(e)}"


def _newspaper_parse_html(html: str, url: str) -> str:
    """CPU-bound Newspaper parsing from pre-fetched HTML."""
    try:
        article = Article(url)
        article.set_html(html)
        article.parse()
        return article.text.strip() if article.text else ""
    except Exception as e:
        raise e


def _newspaper_parse_with_metadata(html: str, url: str) -> ArticleMetadata:
    """CPU-bound Newspaper parsing with metadata extraction."""
    try:
        article = Article(url)
        article.set_html(html)
        article.parse()

        return ArticleMetadata(
            title=article.title if article.title else None,
            author=", ".join(article.authors) if article.authors else None,
            date=article.publish_date.isoformat() if article.publish_date else None,
            description=article.meta_description if article.meta_description else None,
            content=article.text.strip() if article.text else "",
            url=url,
            method="newspaper",
        )
    except Exception as e:
        raise e


def _newspaper_parse(url: str) -> str:
    """CPU-bound Newspaper parsing (legacy, with download)."""
    try:
        article = Article(url)
        article.download()
        article.parse()
        return article.text.strip() if article.text else ""
    except Exception as e:
        raise e


async def method0_trafilatura_async(
    url: str, session: aiohttp.ClientSession
) -> Tuple[str, Optional[ArticleMetadata]]:
    """
    Parse content using Trafilatura - the best method for article extraction.
    Returns: (content, metadata)
    """
    if not TRAFILATURA_AVAILABLE:
        return "Error: Trafilatura not available", None

    logger.debug(f"Method 0 (Trafilatura) attempting: {url}")

    html, error = await fetch_html_with_retry(url, session, timeout=10)
    if error:
        return f"Error: {error}", None

    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, _trafilatura_parse, html, url)
        return result
    except Exception as e:
        logger.error(f"Error parsing with Trafilatura for {url}: {e}")
        return f"Error: {str(e)}", None


def _trafilatura_parse(html: str, url: str) -> Tuple[str, Optional[ArticleMetadata]]:
    """CPU-bound Trafilatura parsing with metadata extraction."""
    try:
        # Configure trafilatura for best quality extraction
        config = use_config()
        config.set("DEFAULT", "EXTRACTION_TIMEOUT", "30")

        # First try to get metadata in JSON format
        metadata_result = trafilatura.extract(
            html,
            url=url,
            include_comments=False,
            include_tables=True,
            include_images=False,
            include_links=False,
            output_format="json",
            with_metadata=True,
            favor_precision=True,
            config=config,
        )

        metadata = None
        content = ""

        if metadata_result:
            try:
                meta_dict = json.loads(metadata_result)
                content = meta_dict.get("raw_text", "") or meta_dict.get("text", "")
                metadata = ArticleMetadata(
                    title=meta_dict.get("title"),
                    author=meta_dict.get("author"),
                    date=meta_dict.get("date"),
                    description=meta_dict.get("description"),
                    language=meta_dict.get("language"),
                    content=content.strip(),
                    url=url,
                    method="trafilatura",
                )
            except json.JSONDecodeError:
                pass

        # Fallback to plain text extraction if JSON failed
        if not content:
            content = (
                trafilatura.extract(
                    html,
                    url=url,
                    include_comments=False,
                    include_tables=True,
                    include_images=False,
                    include_links=False,
                    output_format="txt",
                    with_metadata=False,
                    favor_precision=True,
                    config=config,
                )
                or ""
            )

        if not metadata:
            metadata = ArticleMetadata(content=content.strip(), url=url, method="trafilatura")

        return content.strip(), metadata

    except Exception as e:
        logger.error(f"Trafilatura parse error: {e}")
        raise


async def method3_readability_async(url: str, session: aiohttp.ClientSession) -> str:
    """Parse content using Readability (async)."""
    logger.debug(f"Method 3 (Readability) attempting: {url}")

    html, error = await fetch_html_with_retry(url, session, timeout=10)
    if error:
        return f"Error: {error}"

    try:
        loop = asyncio.get_running_loop()
        content = await loop.run_in_executor(None, _readability_parse, html)
        return content
    except Exception as e:
        logger.error(f"Error parsing with Readability for {url}: {e}")
        return f"Error: {str(e)}"


async def method4_selenium_async(url: str) -> str:
    """Parse content using Selenium for JS-heavy or bot-protected sites."""
    if not SELENIUM_AVAILABLE:
        return "Error: Selenium not available"

    logger.debug(f"Method 4 (Selenium) attempting: {url}")

    try:
        loop = asyncio.get_running_loop()
        content = await loop.run_in_executor(None, _selenium_parse, url)
        return content
    except Exception as e:
        logger.error(f"Error in method4_selenium for {url}: {e}")
        return f"Error: {str(e)}"


def _selenium_parse(url: str) -> str:
    """CPU/IO-bound Selenium parsing."""
    driver = None
    try:
        logger.info(f"[SELENIUM] Starting driver for {url}")
        driver = create_chrome_driver(headless=True)
        driver.set_page_load_timeout(SELENIUM_TIMEOUT)
        # Set script timeout
        driver.set_script_timeout(SELENIUM_TIMEOUT)

        logger.info(f"[SELENIUM] Loading page: {url}")

        # Use 'eager' page load strategy for faster results
        try:
            driver.get(url)
            logger.info("[SELENIUM] Page loaded successfully")
        except Exception as e:
            # Sometimes timeout happens but page is loaded
            if "timeout" not in str(e).lower():
                logger.error(f"[SELENIUM] Failed to load page: {e}")
                raise
            logger.warning(f"[SELENIUM] Timeout during page load, continuing anyway: {e}")

        # Wait for body to be present with longer timeout
        logger.info("[SELENIUM] Waiting for body element")
        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            logger.info("[SELENIUM] Body element found")
        except Exception as e:
            logger.warning(f"[SELENIUM] Body not found, continuing: {e}")

        # Give JavaScript time to render (adaptive wait)
        logger.info("[SELENIUM] Waiting for JavaScript rendering")
        time.sleep(2)

        # Scroll to load lazy content
        logger.info("[SELENIUM] Scrolling to load lazy content")
        try:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(0.5)
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(0.5)
        except Exception as e:
            logger.warning(f"[SELENIUM] Scrolling failed: {e}")

        # Get page source
        logger.info("[SELENIUM] Extracting page source")
        html = driver.page_source

        if not html or len(html) < 100:
            logger.error(f"[SELENIUM] Empty or too short HTML: {len(html) if html else 0} bytes")
            raise ValueError("Empty or too short HTML content")

        logger.info(f"[SELENIUM] HTML extracted: {len(html)} bytes")

        # Parse with BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")

        # Remove unwanted elements
        unwanted_tags = [
            "script",
            "style",
            "nav",
            "header",
            "footer",
            "aside",
            "form",
            "button",
            "input",
            "noscript",
            "iframe",
            "svg",
        ]
        for tag in soup.find_all(unwanted_tags):
            tag.decompose()

        # Try to find main content
        content = ""

        # Priority 1: article tag
        article = soup.find("article")
        if article:
            content = article.get_text(separator="\n", strip=True)

        # Priority 2: main tag
        if not content:
            main = soup.find("main")
            if main:
                content = main.get_text(separator="\n", strip=True)

        # Priority 3: content divs
        if not content:
            content_divs = soup.find_all(
                "div",
                class_=lambda c: c
                and any(
                    key in c.lower() for key in ["content", "article", "main", "post", "entry"]
                ),
            )
            for div in content_divs:
                text = div.get_text(separator="\n", strip=True)
                if len(text) > len(content):
                    content = text

        # Priority 4: all paragraphs
        if not content or len(content) < 100:
            paragraphs = soup.find_all("p")
            content = "\n\n".join(
                [p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 30]
            )

        # Clean up
        content = re.sub(r"\n{3,}", "\n\n", content)
        content = re.sub(r" {2,}", " ", content)

        result = content.strip()
        if len(result) < 50:
            raise ValueError(f"Content too short: {len(result)} chars")

        return result

    except Exception as e:
        logger.error(f"Selenium parse error for {url}: {e}")
        raise
    finally:
        if driver:
            try:
                driver.quit()
            except Exception as e:
                logger.warning(f"Error closing driver: {e}")


async def method5_undetected_async(url: str) -> str:
    """Parse content using Undetected ChromeDriver - bypasses most bot detection."""
    if not UNDETECTED_AVAILABLE:
        return "Error: undetected-chromedriver not available"

    logger.debug(f"Method 5 (Undetected ChromeDriver) attempting: {url}")

    try:
        loop = asyncio.get_running_loop()
        content = await loop.run_in_executor(None, _undetected_parse, url)
        return content
    except Exception as e:
        logger.error(f"Error in method5_undetected for {url}: {e}")
        return f"Error: {str(e)}"


def _undetected_parse(url: str) -> str:
    """CPU/IO-bound Undetected ChromeDriver parsing - best for bot-protected sites."""
    driver = None
    try:
        logger.info(f"[UNDETECTED] Starting driver for {url}")

        # Create undetected Chrome options
        options = uc.ChromeOptions()
        # Don't use headless - it's often detected
        # options.add_argument('--headless=new')
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--start-maximized")

        # Create driver with specific version to avoid detection
        driver = uc.Chrome(options=options, version_main=None, use_subprocess=True)
        driver.set_page_load_timeout(30)

        logger.info(f"[UNDETECTED] Loading page: {url}")
        driver.get(url)

        # Random human-like delay
        wait_time = random.uniform(4, 7)
        logger.info(f"[UNDETECTED] Waiting {wait_time:.1f}s for content (human-like)")
        time.sleep(wait_time)

        # Scroll like a human
        try:
            driver.execute_script("window.scrollTo(0, 500);")
            time.sleep(random.uniform(0.5, 1.5))
            driver.execute_script("window.scrollTo(0, 1000);")
            time.sleep(random.uniform(0.5, 1.5))
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(random.uniform(0.5, 1.0))
        except Exception:
            pass

        # Get page source
        logger.info("[UNDETECTED] Extracting content")
        html = driver.page_source

        if not html or len(html) < 100:
            logger.error(f"[UNDETECTED] Empty or too short HTML: {len(html) if html else 0} bytes")
            raise ValueError("Empty or too short HTML content")

        logger.info(f"[UNDETECTED] HTML extracted: {len(html)} bytes")

        # Parse with BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")

        # Remove unwanted elements
        for tag in soup.find_all(
            [
                "script",
                "style",
                "nav",
                "header",
                "footer",
                "aside",
                "form",
                "button",
                "input",
                "noscript",
                "iframe",
                "svg",
            ]
        ):
            tag.decompose()

        # Try to find main content
        content = ""

        # Priority 1: article tag
        article = soup.find("article")
        if article:
            content = article.get_text(separator="\n", strip=True)

        # Priority 2: main tag
        if not content or len(content) < 100:
            main = soup.find("main")
            if main:
                content = main.get_text(separator="\n", strip=True)

        # Priority 3: divs with content-related classes
        if not content or len(content) < 100:
            content_divs = soup.find_all(
                "div",
                class_=lambda c: c
                and any(
                    key in c.lower()
                    for key in ["content", "article", "main", "post", "entry", "story"]
                ),
            )
            for div in content_divs:
                text = div.get_text(separator="\n", strip=True)
                if len(text) > len(content):
                    content = text

        # Priority 4: all paragraphs
        if not content or len(content) < 100:
            paragraphs = soup.find_all("p")
            content = "\n\n".join(
                [p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 30]
            )

        # Clean up
        content = re.sub(r"\n{3,}", "\n\n", content)
        content = re.sub(r" {2,}", " ", content)

        result = content.strip()
        if len(result) < 50:
            raise ValueError(f"Content too short: {len(result)} chars")

        logger.info(f"[UNDETECTED] Success: extracted {len(result)} chars")
        return result

    except Exception as e:
        logger.error(f"[UNDETECTED] Parse error for {url}: {e}")
        raise
    finally:
        if driver:
            try:
                driver.quit()
                logger.info("[UNDETECTED] Driver closed")
            except Exception as e:
                logger.warning(f"[UNDETECTED] Error closing driver: {e}")


def _readability_parse(html: str) -> str:
    """CPU-bound Readability parsing with improved text extraction."""
    doc = Document(html)
    content_html = doc.summary()
    soup = BeautifulSoup(content_html, "html.parser")

    # Try to extract text more intelligently
    paragraphs = []
    for element in soup.find_all(["p", "h1", "h2", "h3", "h4", "h5", "h6", "li"]):
        text = element.get_text(separator=" ", strip=True)
        if text and len(text) > 10:
            paragraphs.append(text)

    if paragraphs:
        clean_text = "\n\n".join(paragraphs)
    else:
        clean_text = soup.get_text(separator="\n", strip=True)

    # Clean up excessive whitespace
    clean_text = re.sub(r"\n{3,}", "\n\n", clean_text)
    clean_text = re.sub(r" {2,}", " ", clean_text)

    return clean_text.strip()


async def compare_methods_async(url: str) -> Tuple[str, str]:
    """
    Compare parsing methods with early exit optimization.
    Returns: (content, method_used)
    """
    logger.debug(f"Comparing parsing methods for {url}")

    # Create SSL context and connector
    ssl_context = create_ssl_context()
    connector = aiohttp.TCPConnector(
        ssl=ssl_context, limit=10, limit_per_host=5, ttl_dns_cache=300, enable_cleanup_closed=True
    )

    # Enhanced headers to appear more like a real browser
    headers = {
        "User-Agent": get_random_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }

    # Cookie jar for session management
    cookie_jar = aiohttp.CookieJar()

    async with aiohttp.ClientSession(
        headers=headers,
        connector=connector,
        cookie_jar=cookie_jar,
        timeout=aiohttp.ClientTimeout(total=30),
    ) as session:
        # Try Trafilatura first - usually gives best results for articles
        trafilatura_result = ""
        trafilatura_metadata = None
        if TRAFILATURA_AVAILABLE:
            try:
                result = await method0_trafilatura_async(url, session)
                # Handle both tuple and string returns
                if isinstance(result, tuple):
                    trafilatura_result, trafilatura_metadata = result
                else:
                    trafilatura_result = result

                if (
                    trafilatura_result
                    and not trafilatura_result.startswith("Error")
                    and len(trafilatura_result) > 300
                ):
                    logger.info(
                        f"Early exit: trafilatura gave {len(trafilatura_result)} chars for {url}"
                    )
                    return trafilatura_result, "trafilatura"
            except Exception as e:
                logger.warning(f"Trafilatura failed: {e}")
                trafilatura_result = f"Error: {e}"

        # Try readability second
        readability_result = await method3_readability_async(url, session)
        if (
            readability_result
            and not readability_result.startswith("Error")
            and len(readability_result) > 500
        ):
            logger.info(f"Early exit: readability gave {len(readability_result)} chars for {url}")
            return readability_result, "readability"

        # Try newspaper third
        newspaper_result = await method2_newspaper_async(url, session)
        if (
            newspaper_result
            and not newspaper_result.startswith("Error")
            and len(newspaper_result) > 500
        ):
            logger.info(f"Early exit: newspaper gave {len(newspaper_result)} chars for {url}")
            return newspaper_result, "newspaper"

        # Try BeautifulSoup as last resort
        bs4_result = await method1_bs4_async(url, session)
        if bs4_result and not bs4_result.startswith("Error") and len(bs4_result) > 200:
            logger.info(f"Selected bs4: {len(bs4_result)} chars for {url}")
            return bs4_result, "bs4"

        # Check if we got 403 errors and should try undetected/Selenium
        selenium_result = ""
        undetected_result = ""

        if USE_SELENIUM_FOR_403:
            # Check if all methods failed with 403 or similar bot-detection errors
            has_403_or_blocked = any(
                "403" in str(result)
                or "Forbidden" in str(result)
                or "blocked" in str(result).lower()
                for result in [trafilatura_result, readability_result, newspaper_result, bs4_result]
            )

            if has_403_or_blocked:
                # Try undetected-chromedriver first (best for bot detection bypass)
                if UNDETECTED_AVAILABLE:
                    logger.info(
                        f"Detected bot protection, trying Undetected ChromeDriver for {url}"
                    )
                    undetected_result = await method5_undetected_async(url)
                    if (
                        undetected_result
                        and not undetected_result.startswith("Error")
                        and len(undetected_result) > 200
                    ):
                        logger.info(
                            f"Undetected ChromeDriver success: {len(undetected_result)} chars for {url}"
                        )
                        return undetected_result, "undetected"

                # Fallback to regular Selenium if undetected failed
                if SELENIUM_AVAILABLE and (
                    not undetected_result or undetected_result.startswith("Error")
                ):
                    logger.info(f"Trying regular Selenium for {url}")
                    selenium_result = await method4_selenium_async(url)
                    if (
                        selenium_result
                        and not selenium_result.startswith("Error")
                        and len(selenium_result) > 200
                    ):
                        logger.info(f"Selenium success: {len(selenium_result)} chars for {url}")
                        return selenium_result, "selenium"

        # Select the best result from what we have
        results = {
            "trafilatura": trafilatura_result,
            "readability": readability_result,
            "newspaper": newspaper_result,
            "bs4": bs4_result,
            "undetected": undetected_result,
            "selenium": selenium_result,
        }

        best_result = ""
        best_method = "none"
        best_length = 0

        for method, result in results.items():
            if result and not result.startswith("Error") and len(result) > best_length:
                best_result = result
                best_method = method
                best_length = len(result)

        if best_result:
            logger.info(f"Selected {best_method} (longest): {best_length} chars for {url}")
            return best_result, best_method

        logger.warning(f"All methods failed for {url}")
        return readability_result or "Error: All methods failed", "failed"


def clean_text(text: str) -> str:
    """Clean extracted text from unwanted elements."""
    if not text or text.startswith("Error"):
        return text

    text = re.sub(r"\n{2,}", "\n\n", text.strip())

    # Patterns to remove (common noise in web pages)
    patterns_to_remove = [
        r"Subscribe to.*?(?:\n|$)",
        r"Read also:.*?(?:\n|$)",
        r"Share this.*?(?:\n|$)",
        r"Share on.*?(?:\n|$)",
        r"\d+ comments?.*?(?:\n|$)",
        r"Comments \(\d+\).*?(?:\n|$)",
        r"Advertisement.*?(?:\n|$)",
        r"Loading comments.*?(?:\n|$)",
        r"Cookie Policy.*?(?:\n|$)",
        r"Privacy Policy.*?(?:\n|$)",
        r"Terms of (?:Service|Use).*?(?:\n|$)",
        r"Follow us on.*?(?:\n|$)",
        r"Sign up for.*?(?:\n|$)",
        r"Newsletter.*?(?:\n|$)",
        r"Copyright ©.*?(?:\n|$)",
        r"All rights reserved.*?(?:\n|$)",
        r"Related articles?:?.*?(?:\n|$)",
        r"Recommended for you.*?(?:\n|$)",
        r"More from.*?(?:\n|$)",
        r"You might also like.*?(?:\n|$)",
        r"Click here to.*?(?:\n|$)",
        r"Join our.*?(?:\n|$)",
    ]

    for pattern in patterns_to_remove:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE | re.MULTILINE)

    lines = text.split("\n")
    meaningful_lines = []

    for line in lines:
        line_stripped = line.strip()
        # Keep lines that are substantial or contain sentences
        if len(line_stripped) > 25 or (len(line_stripped) > 10 and "." in line_stripped):
            meaningful_lines.append(line)

    text = "\n\n".join(meaningful_lines).strip()

    # Final cleanup
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)

    return text


async def extract_content_from_url(url: str) -> str:
    """
    Main async function to extract content from URL.

    Args:
        url: URL to extract content from

    Returns:
        Extracted and cleaned text content
    """
    logger.info(f"Extracting content from: {url}")

    if not url or not AsyncLinkParser.is_valid_url(url):
        error_msg = f"Invalid URL: {url}"
        logger.error(error_msg)
        return f"Error: {error_msg}"

    # Check cache first
    cached = _get_from_cache(url)
    if cached:
        logger.info(f"Returning cached content for {url}")
        return cached.content

    try:
        content, method_used = await compare_methods_async(url)
        original_length = len(content) if content else 0

        logger.info(f"Extracted {original_length} chars from {url} using {method_used}")

        if not content or content.startswith("Error"):
            return content or "Error: No content extracted"

        cleaned_content = clean_text(content)
        cleaned_length = len(cleaned_content)

        logger.info(f"Cleaned content: {original_length} -> {cleaned_length} chars")

        if cleaned_length < 200 and original_length > 1000:
            logger.warning("Cleaning too aggressive, using original")
            final_content = re.sub(r"\n{3,}", "\n\n", content.strip())
        else:
            final_content = (
                cleaned_content if cleaned_content else "Error: Content empty after cleaning"
            )

        # Cache the result
        if not final_content.startswith("Error"):
            _set_cache(url, ArticleMetadata(content=final_content, url=url, method=method_used))

        return final_content

    except Exception as e:
        error_msg = f"Critical error extracting {url}: {str(e)}"
        logger.exception(error_msg)
        return f"Error: {error_msg}"


async def extract_article_with_metadata(url: str) -> ArticleMetadata:
    """
    Extract article content with full metadata (title, author, date, etc.).

    Args:
        url: URL to extract content from

    Returns:
        ArticleMetadata object with content and metadata
    """
    logger.info(f"Extracting article with metadata from: {url}")

    if not url or not AsyncLinkParser.is_valid_url(url):
        return ArticleMetadata(content=f"Error: Invalid URL: {url}", url=url, method="failed")

    # Check cache first
    cached = _get_from_cache(url)
    if cached:
        logger.info(f"Returning cached article for {url}")
        return cached

    # Create session
    ssl_context = create_ssl_context()
    connector = aiohttp.TCPConnector(
        ssl=ssl_context, limit=10, limit_per_host=5, ttl_dns_cache=300, enable_cleanup_closed=True
    )

    headers = {
        "User-Agent": get_random_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    cookie_jar = aiohttp.CookieJar()

    async with aiohttp.ClientSession(
        headers=headers,
        connector=connector,
        cookie_jar=cookie_jar,
        timeout=aiohttp.ClientTimeout(total=30),
    ) as session:
        # Try Trafilatura first - it provides the best metadata extraction
        if TRAFILATURA_AVAILABLE:
            trafilatura_content, metadata = await method0_trafilatura_async(url, session)
            if metadata and metadata.content and len(metadata.content) > 200:
                # Clean the content
                metadata.content = clean_text(metadata.content)
                _set_cache(url, metadata)
                logger.info(
                    f"Extracted article with metadata using trafilatura: {len(metadata.content)} chars"
                )
                return metadata

        # Fallback to newspaper which also provides good metadata
        html, error = await fetch_html_with_retry(url, session, timeout=10)
        if not error and html:
            try:
                loop = asyncio.get_running_loop()
                metadata = await loop.run_in_executor(
                    None, _newspaper_parse_with_metadata, html, url
                )
                if metadata and metadata.content and len(metadata.content) > 200:
                    metadata.content = clean_text(metadata.content)
                    _set_cache(url, metadata)
                    logger.info(
                        f"Extracted article with metadata using newspaper: {len(metadata.content)} chars"
                    )
                    return metadata
            except Exception as e:
                logger.error(f"Newspaper metadata extraction failed: {e}")

        # Final fallback to regular extraction
        content, method = await compare_methods_async(url)
        cleaned_content = (
            clean_text(content) if content and not content.startswith("Error") else content
        )

        result = ArticleMetadata(
            content=cleaned_content or "Error: No content extracted", url=url, method=method
        )

        if not cleaned_content.startswith("Error"):
            _set_cache(url, result)

        return result
