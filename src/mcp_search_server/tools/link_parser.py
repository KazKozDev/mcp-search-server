"""
Async link parser with multiple fallback methods.
"""

import asyncio
import logging
import re
from typing import Tuple
from urllib.parse import urlparse

import aiohttp
from bs4 import BeautifulSoup
from newspaper import Article
from readability import Document

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


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
            return all([result.scheme, result.netloc])
        except Exception as e:
            logger.error(f"Error validating URL {url}: {e}")
            return False


async def method1_bs4_async(url: str, session: aiohttp.ClientSession) -> str:
    """Parse main content from URL using BeautifulSoup (async)."""
    logger.debug(f"Method 1 (BeautifulSoup) attempting: {url}")
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=7)) as response:
            response.raise_for_status()
            html = await response.text()

        loop = asyncio.get_event_loop()
        content = await loop.run_in_executor(None, _parse_bs4, html, url)
        return content

    except asyncio.TimeoutError:
        logger.warning(f"Timeout in method1_bs4 for {url}")
        return "Error: Timeout"
    except Exception as e:
        logger.error(f"Error in method1_bs4 for {url}: {e}")
        return f"Error: {str(e)}"


def _parse_bs4(html: str, url: str) -> str:
    """CPU-bound BeautifulSoup parsing."""
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all(
        ["script", "style", "nav", "header", "footer", "aside", "form", "button", "input"]
    ):
        tag.decompose()

    article_content = ""

    article_tag = soup.find("article")
    if article_tag:
        for p in article_tag.find_all("p"):
            article_content += p.get_text(separator="\n", strip=True) + "\n\n"
        if article_content.strip():
            return article_content.strip()

    content_divs = soup.find_all(
        "div",
        class_=lambda c: c
        and any(
            key in c.lower() for key in ["content", "article", "main", "body", "post", "entry"]
        ),
    )
    for div in content_divs:
        for p in div.find_all("p"):
            article_content += p.get_text(separator="\n", strip=True) + "\n\n"
        if article_content.strip():
            return article_content.strip()

    if not article_content:
        paragraphs = soup.find_all("p")
        for p in paragraphs:
            article_content += p.get_text(separator="\n", strip=True) + "\n\n"

    return article_content.strip()


async def method2_newspaper_async(url: str) -> str:
    """Parse content using Newspaper3k (runs in executor)."""
    logger.debug(f"Method 2 (Newspaper3k) attempting: {url}")
    try:
        loop = asyncio.get_event_loop()
        content = await loop.run_in_executor(None, _newspaper_parse, url)
        return content
    except Exception as e:
        logger.error(f"Error in method2_newspaper for {url}: {e}")
        return f"Error: {str(e)}"


def _newspaper_parse(url: str) -> str:
    """CPU-bound Newspaper parsing."""
    try:
        article = Article(url)
        article.download()
        article.parse()
        return article.text.strip() if article.text else ""
    except Exception as e:
        raise e


async def method3_readability_async(url: str, session: aiohttp.ClientSession) -> str:
    """Parse content using Readability (async)."""
    logger.debug(f"Method 3 (Readability) attempting: {url}")
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=7)) as response:
            response.raise_for_status()
            html = await response.text()

        loop = asyncio.get_event_loop()
        content = await loop.run_in_executor(None, _readability_parse, html)
        return content

    except asyncio.TimeoutError:
        logger.warning(f"Timeout in method3_readability for {url}")
        return "Error: Timeout"
    except Exception as e:
        logger.error(f"Error in method3_readability for {url}: {e}")
        return f"Error: {str(e)}"


def _readability_parse(html: str) -> str:
    """CPU-bound Readability parsing."""
    doc = Document(html)
    content_html = doc.summary()
    soup = BeautifulSoup(content_html, "html.parser")
    clean_text = soup.get_text(separator="\n", strip=True)
    clean_text = re.sub(r"\n{2,}", "\n\n", clean_text)
    return clean_text.strip()


async def compare_methods_async(url: str) -> Tuple[str, str]:
    """
    Compare parsing methods with early exit optimization.
    Returns: (content, method_used)
    """
    logger.debug(f"Comparing parsing methods for {url}")

    connector = aiohttp.TCPConnector(ssl=False)
    headers = {"User-Agent": USER_AGENT}

    async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
        readability_result = await method3_readability_async(url, session)
        if (
            readability_result
            and not readability_result.startswith("Error")
            and len(readability_result) > 500
        ):
            logger.info(f"Early exit: readability gave {len(readability_result)} chars for {url}")
            return readability_result, "readability"

        newspaper_result = await method2_newspaper_async(url)
        if (
            newspaper_result
            and not newspaper_result.startswith("Error")
            and len(newspaper_result) > 500
        ):
            logger.info(f"Early exit: newspaper gave {len(newspaper_result)} chars for {url}")
            return newspaper_result, "newspaper"

        bs4_result = await method1_bs4_async(url, session)
        if bs4_result and not bs4_result.startswith("Error") and len(bs4_result) > 200:
            logger.info(f"Selected bs4: {len(bs4_result)} chars for {url}")
            return bs4_result, "bs4"

        results = {
            "readability": readability_result,
            "newspaper": newspaper_result,
            "bs4": bs4_result,
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

    patterns_to_remove = [
        r"Subscribe to.*",
        r"Read also:.*",
        r"Share.*",
        r"Comments.*",
        r"Copyright ©.*",
        r"\d+ comments.*",
        r"Advertisement.*",
        r"Loading comments.*",
        r"Cookie Policy.*",
        r"Privacy Policy.*",
        r"Follow us on.*",
        r"Sign up for.*",
    ]

    for pattern in patterns_to_remove:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE | re.MULTILINE)

    lines = text.split("\n")
    meaningful_lines = []

    for line in lines:
        line_stripped = line.strip()
        if len(line_stripped) > 25 or "." in line_stripped:
            meaningful_lines.append(line)

    text = "\n\n".join(meaningful_lines).strip()
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
            return re.sub(r"\n{3,}", "\n\n", content.strip())

        return cleaned_content if cleaned_content else "Error: Content empty after cleaning"

    except Exception as e:
        error_msg = f"Critical error extracting {url}: {str(e)}"
        logger.exception(error_msg)
        return f"Error: {error_msg}"
