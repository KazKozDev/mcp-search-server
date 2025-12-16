"""PDF Parser Tool - Extract text from PDF files."""

import logging
import aiohttp
import io

logger = logging.getLogger(__name__)


async def parse_pdf(url: str, max_chars: int = 50000) -> str:
    """
    Extract text from a PDF file.

    Args:
        url: URL of the PDF file
        max_chars: Maximum characters to extract

    Returns:
        Extracted text content
    """
    try:
        pdf_library = None
        try:
            import PyPDF2  # noqa: F401

            pdf_library = "pypdf2"
        except ImportError:
            try:
                import pdfplumber  # noqa: F401

                pdf_library = "pdfplumber"
            except ImportError:
                logger.error("No PDF parsing library found. Install PyPDF2 or pdfplumber.")
                return "Error: No PDF parsing library installed"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status != 200:
                    logger.warning(f"Failed to download PDF: {url} (status: {response.status})")
                    return f"Error: Failed to download PDF (status: {response.status})"

                pdf_data = await response.read()

        if pdf_library == "pypdf2":
            return await _parse_with_pypdf2(pdf_data, max_chars)
        elif pdf_library == "pdfplumber":
            return await _parse_with_pdfplumber(pdf_data, max_chars)

        return "Error: No PDF library available"

    except Exception as e:
        logger.error(f"Error parsing PDF {url}: {e}")
        return f"Error: {str(e)}"


async def _parse_with_pypdf2(pdf_data: bytes, max_chars: int) -> str:
    """Parse PDF using PyPDF2."""
    import PyPDF2

    try:
        pdf_file = io.BytesIO(pdf_data)
        pdf_reader = PyPDF2.PdfReader(pdf_file)

        text_parts = []
        total_chars = 0

        for page_num in range(len(pdf_reader.pages)):
            if total_chars >= max_chars:
                break

            page = pdf_reader.pages[page_num]
            page_text = page.extract_text()

            if page_text:
                text_parts.append(page_text)
                total_chars += len(page_text)

        full_text = "\n\n".join(text_parts)

        if len(full_text) > max_chars:
            full_text = full_text[:max_chars] + "... [truncated]"

        logger.info(f"Extracted {len(full_text)} chars from PDF using PyPDF2")
        return full_text

    except Exception as e:
        logger.error(f"PyPDF2 parsing failed: {e}")
        return f"Error: PyPDF2 parsing failed - {str(e)}"


async def _parse_with_pdfplumber(pdf_data: bytes, max_chars: int) -> str:
    """Parse PDF using pdfplumber."""
    import pdfplumber

    try:
        pdf_file = io.BytesIO(pdf_data)

        text_parts = []
        total_chars = 0

        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                if total_chars >= max_chars:
                    break

                page_text = page.extract_text()

                if page_text:
                    text_parts.append(page_text)
                    total_chars += len(page_text)

        full_text = "\n\n".join(text_parts)

        if len(full_text) > max_chars:
            full_text = full_text[:max_chars] + "... [truncated]"

        logger.info(f"Extracted {len(full_text)} chars from PDF using pdfplumber")
        return full_text

    except Exception as e:
        logger.error(f"pdfplumber parsing failed: {e}")
        return f"Error: pdfplumber parsing failed - {str(e)}"
