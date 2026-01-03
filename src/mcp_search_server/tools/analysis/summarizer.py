"""
Advanced text summarization with multiple strategies.
Works without API keys - uses TF-IDF (NLTK) or heuristic fallback.
"""

import logging
import re
from typing import Optional, Dict
from collections import Counter

logger = logging.getLogger(__name__)

try:
    import nltk
    from nltk.corpus import stopwords
    from nltk.tokenize import sent_tokenize, word_tokenize

    HAS_NLTK = True
    try:
        nltk.data.find("tokenizers/punkt")
    except LookupError:
        nltk.download("punkt", quiet=True)
    try:
        nltk.data.find("corpora/stopwords")
    except LookupError:
        nltk.download("stopwords", quiet=True)
except ImportError:
    HAS_NLTK = False
    logger.info("NLTK not installed. Using heuristic summarization.")

# Optional: Transformers for abstractive summarization (SLOW, large download)
try:
    from transformers import pipeline

    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False


class AdvancedSummarizerTool:
    """
    Advanced multi-strategy summarization system.

    Strategies (in priority order):
    1. Extractive TF-IDF (NLTK) — fast, good quality, no API keys
    2. Extractive + Keyword scoring — hybrid approach
    3. Simple heuristic — ultra-fast fallback
    4. Abstractive (BART) — optional, requires transformers library

    Note: Abstractive summarization is disabled by default because:
    - Large model download (~1.6GB for BART)
    - Slow inference on CPU
    - High memory usage

    Use extractive methods for production (fast, good results).
    """

    def __init__(self, enable_abstractive: bool = False):
        self.enable_abstractive = enable_abstractive
        self.abstractive = None

        if enable_abstractive and HAS_TRANSFORMERS:
            self._load_abstractive_model()

    def _load_abstractive_model(self):
        """Load BART model (optional, large download)."""
        try:
            logger.info("Loading BART model (this may take a while on first run)...")
            self.abstractive = pipeline(
                "summarization",
                model="facebook/bart-large-cnn",
                device=-1,  # CPU (use device=0 for GPU)
            )
            logger.info("Abstractive model loaded.")
        except Exception as e:
            logger.warning(f"Failed to load BART model: {e}")
            self.abstractive = None

    async def summarize(
        self,
        text: str,
        strategy: str = "auto",
        max_length: int = 200,
        min_length: int = 60,
        compression_ratio: float = 0.3,
    ) -> Optional[Dict]:
        """
        Summarize text using specified strategy.

        Args:
            text: Original text
            strategy: "auto", "extractive_tfidf", "extractive_keyword", "heuristic", "abstractive"
            max_length: Max output tokens (for abstractive only)
            min_length: Min output tokens (for abstractive only)
            compression_ratio: Target ratio (0.3 = 30% of original)

        Returns:
            Dict with 'summary', 'method', 'stats'
        """
        if not text or not text.strip():
            return None

        # Clean and validate input
        text = self._clean_text(text)
        if not text:
            return None

        logger.info(f"Summarizing {len(text)} chars with strategy: {strategy}")

        # Auto strategy selection
        if strategy == "auto":
            if self.abstractive and len(text) < 5000:
                strategy = "abstractive"
            elif HAS_NLTK:
                strategy = "extractive_tfidf"
            else:
                strategy = "heuristic"

        # Execute strategy
        if strategy == "abstractive" and self.abstractive:
            return self._abstractive_summarize(text, max_length, min_length)
        elif strategy == "extractive_tfidf":
            return self._extractive_tfidf(text, compression_ratio)
        elif strategy == "extractive_keyword":
            return self._extractive_keyword(text, compression_ratio)
        else:
            return self._heuristic_summary(text)

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        # Remove URLs
        text = re.sub(r"http\S+|www\S+", "", text)
        # Remove emails
        text = re.sub(r"\S+@\S+", "", text)
        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _extractive_tfidf(self, text: str, compression_ratio: float) -> Dict:
        """
        Extractive summarization using TF-IDF scoring.
        Fast, good quality, no external dependencies (except NLTK).
        """
        if not HAS_NLTK:
            return self._heuristic_summary(text)

        try:
            sentences = sent_tokenize(text)
            if len(sentences) <= 2:
                return {
                    "summary": text,
                    "method": "extractive-tfidf-short",
                    "stats": {"sentences": len(sentences)},
                }

            # Calculate word frequencies (TF)
            stop_words = set(stopwords.words("english"))
            word_freq = Counter()

            for sent in sentences:
                words = word_tokenize(sent.lower())
                words = [w for w in words if w.isalnum() and w not in stop_words]
                word_freq.update(words)

            # Normalize frequencies
            max_freq = max(word_freq.values()) if word_freq else 1

            # Score each sentence
            sentence_scores = {}
            for sent in sentences:
                words = word_tokenize(sent.lower())
                words = [w for w in words if w.isalnum() and w not in stop_words]

                # Sum of normalized word frequencies
                score = sum(word_freq[w] / max_freq for w in words)
                sentence_scores[sent] = score

            # Select top N sentences
            target_count = max(1, int(len(sentences) * compression_ratio))
            top_sentences = sorted(sentence_scores, key=sentence_scores.get, reverse=True)[
                :target_count
            ]

            # Maintain original order
            summary = " ".join(s for s in sentences if s in top_sentences)

            return {
                "summary": summary,
                "method": "extractive-tfidf",
                "stats": {
                    "sentences_original": len(sentences),
                    "sentences_summary": len(top_sentences),
                    "compression_ratio": f"{compression_ratio * 100:.0f}%",
                    "chars_original": len(text),
                    "chars_summary": len(summary),
                },
            }
        except Exception as e:
            logger.warning(f"TF-IDF extraction failed: {e}")
            return self._heuristic_summary(text)

    def _extractive_keyword(self, text: str, compression_ratio: float) -> Dict:
        """
        Extractive summarization with entity/keyword scoring.
        Prioritizes sentences with proper nouns and important terms.
        """
        if not HAS_NLTK:
            return self._heuristic_summary(text)

        try:
            sentences = sent_tokenize(text)
            if len(sentences) <= 2:
                return {
                    "summary": text,
                    "method": "extractive-keyword-short",
                    "stats": {"sentences": len(sentences)},
                }

            # Extract entities (capitalized words = likely proper nouns)
            stop_words = set(stopwords.words("english"))
            entities = set()

            for sent in sentences:
                words = sent.split()
                for word in words:
                    # Proper noun heuristic
                    if (
                        word
                        and word[0].isupper()
                        and word not in {"The", "A", "An", "This", "That", "These", "Those"}
                    ):
                        entities.add(word.lower())

            # Score sentences
            sentence_scores = {}
            for sent in sentences:
                sent_lower = sent.lower()
                # Entity matches (weighted 2x)
                entity_score = sum(1 for e in entities if e in sent_lower) * 2
                # Content word count
                word_score = len([w for w in sent.split() if w.lower() not in stop_words])

                sentence_scores[sent] = entity_score + word_score

            # Select top sentences
            target_count = max(1, int(len(sentences) * compression_ratio))
            top_sentences = sorted(sentence_scores, key=sentence_scores.get, reverse=True)[
                :target_count
            ]

            # Maintain order
            summary = " ".join(s for s in sentences if s in top_sentences)

            return {
                "summary": summary,
                "method": "extractive-keyword",
                "stats": {
                    "sentences_original": len(sentences),
                    "sentences_summary": len(top_sentences),
                    "entities_found": len(entities),
                    "compression_ratio": f"{compression_ratio * 100:.0f}%",
                    "chars_original": len(text),
                    "chars_summary": len(summary),
                },
            }
        except Exception as e:
            logger.warning(f"Keyword extraction failed: {e}")
            return self._heuristic_summary(text)

    def _heuristic_summary(self, text: str) -> Dict:
        """
        Ultra-simple fallback: first + middle + last sentences.
        Works without any dependencies.
        """
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())

        if len(sentences) <= 3:
            return {
                "summary": text,
                "method": "heuristic-full",
                "stats": {"sentences": len(sentences), "chars": len(text)},
            }

        # Take first, middle, last
        first = sentences[0]
        middle = sentences[len(sentences) // 2]
        last = sentences[-1]

        summary = f"{first} {middle} {last}"

        return {
            "summary": summary,
            "method": "heuristic-3sent",
            "stats": {
                "sentences_original": len(sentences),
                "sentences_summary": 3,
                "chars_original": len(text),
                "chars_summary": len(summary),
            },
        }

    def _abstractive_summarize(self, text: str, max_length: int, min_length: int) -> Dict:
        """
        Neural abstractive summarization using BART.
        Optional, requires transformers library and large model download.
        """
        if not self.abstractive:
            logger.warning("Abstractive model not loaded. Falling back to extractive.")
            return self._extractive_tfidf(text, 0.3)

        try:
            # BART has 1024 token limit (~4000 chars)
            max_chars = 4000
            if len(text) > max_chars:
                # Take beginning + middle + end
                chunk_size = max_chars // 3
                text = (
                    text[:chunk_size]
                    + " ... "
                    + text[len(text) // 2 - chunk_size // 2 : len(text) // 2 + chunk_size // 2]
                    + " ... "
                    + text[-chunk_size:]
                )

            result = self.abstractive(
                text, max_length=max_length, min_length=min_length, do_sample=False
            )

            summary_text = result[0]["summary_text"].strip()

            return {
                "summary": summary_text,
                "method": "abstractive-bart",
                "stats": {
                    "input_chars": len(text),
                    "output_chars": len(summary_text),
                    "compression": f"{len(summary_text) / len(text) * 100:.1f}%",
                },
            }
        except Exception as e:
            logger.warning(f"Abstractive summarization failed: {e}")
            return self._extractive_tfidf(text, 0.3)


# Global summarizer instance (extractive only by default)
_summarizer = AdvancedSummarizerTool(enable_abstractive=False)


async def summarize_text(text: str, strategy: str = "auto", compression_ratio: float = 0.3) -> Dict:
    """
    Summarize text using best available method.

    Args:
        text: Text to summarize
        strategy: "auto", "extractive_tfidf", "extractive_keyword", "heuristic"
        compression_ratio: Target compression (0.3 = 30% of original)

    Returns:
        Dict with 'summary', 'method', 'stats'
    """
    return await _summarizer.summarize(
        text=text, strategy=strategy, compression_ratio=compression_ratio
    )
