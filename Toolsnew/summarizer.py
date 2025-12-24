import logging
import re
from typing import Optional, Dict, List
from collections import Counter

logger = logging.getLogger(__name__)

try:
    from transformers import pipeline
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False

try:
    import nltk
    from nltk.corpus import stopwords
    from nltk.tokenize import sent_tokenize, word_tokenize
    HAS_NLTK = True
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt', quiet=True)
    try:
        nltk.data.find('corpora/stopwords')
    except LookupError:
        nltk.download('stopwords', quiet=True)
except ImportError:
    HAS_NLTK = False


class AdvancedSummarizerTool:
    """
    Advanced multi-strategy summarization system.
    
    Strategies (in priority order):
    1. Abstractive (BART/PEGASUS) — neural, best quality
    2. Extractive TF-IDF — fast, no GPU needed
    3. Extractive + Keyword scoring — hybrid
    4. Simple heuristic — fallback
    """
    
    def __init__(self, model_name: str = "facebook/bart-large-cnn"):
        self.model_name = model_name
        self.abstractive = None
        self.load_abstractive_model()
    
    def load_abstractive_model(self):
        """Load BART/PEGASUS model from HuggingFace."""
        if not HAS_TRANSFORMERS:
            logger.warning("transformers not installed")
            return
        
        try:
            logger.info(f"Loading model: {self.model_name}")
            self.abstractive = pipeline(
                "summarization",
                model=self.model_name,
                device=-1  # CPU (use device=0 for GPU)
            )
            logger.info("Abstractive model loaded.")
        except Exception as e:
            logger.warning(f"Failed to load model: {e}. Using extractive fallback.")
            self.abstractive = None
    
    def summarize(
        self,
        text: str,
        strategy: str = "auto",
        max_length: int = 200,
        min_length: int = 60,
        compression_ratio: float = 0.3
    ) -> Optional[Dict]:
        """
        Summarize text using specified strategy.
        
        Args:
            text: Original text
            strategy: "auto", "abstractive", "extractive_tfidf", "extractive_keyword", "heuristic"
            max_length: Max output tokens (for abstractive)
            min_length: Min output tokens (for abstractive)
            compression_ratio: Target ratio of summary/original (for extractive)
            
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
        
        # Auto strategy selection based on text length and available models
        if strategy == "auto":
            if self.abstractive and len(text) < 5000:
                strategy = "abstractive"
            elif HAS_NLTK:
                strategy = "extractive_tfidf"
            else:
                strategy = "heuristic"
        
        # Execute strategy
        if strategy == "abstractive":
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
        text = re.sub(r'http\S+|www\S+', '', text)
        # Remove emails
        text = re.sub(r'\S+@\S+', '', text)
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def _abstractive_summarize(
        self,
        text: str,
        max_length: int,
        min_length: int
    ) -> Dict:
        """Neural abstractive summarization (BART/PEGASUS)."""
        if not self.abstractive:
            return self._extractive_tfidf(text, 0.3)
        
        try:
            # Truncate if needed (BART has 1024 token limit)
            max_chars = 1024 * 4
            if len(text) > max_chars:
                # Take beginning + middle + end to preserve context
                chunk_size = max_chars // 3
                text = (
                    text[:chunk_size] + 
                    " ... " + 
                    text[len(text)//2 - chunk_size//2: len(text)//2 + chunk_size//2] +
                    " ... " +
                    text[-chunk_size:]
                )
            
            result = self.abstractive(
                text,
                max_length=max_length,
                min_length=min_length,
                do_sample=False
            )
            
            return {
                'summary': result[0]['summary_text'].strip(),
                'method': 'abstractive-bart',
                'stats': {
                    'input_chars': len(text),
                    'output_chars': len(result[0]['summary_text']),
                    'compression': f"{len(result[0]['summary_text'])/len(text)*100:.1f}%"
                }
            }
        except Exception as e:
            logger.warning(f"Abstractive summarization failed: {e}")
            return self._extractive_tfidf(text, 0.3)
    
    def _extractive_tfidf(self, text: str, compression_ratio: float) -> Dict:
        """Extractive summarization using TF-IDF scoring."""
        if not HAS_NLTK:
            return self._heuristic_summary(text)
        
        try:
            sentences = sent_tokenize(text)
            if len(sentences) <= 2:
                return {'summary': text, 'method': 'extractive-tfidf-single'}
            
            # Calculate TF-IDF for each sentence
            stop_words = set(stopwords.words('english'))
            
            # Tokenize and score
            sentence_scores = {}
            word_freq = Counter()
            
            for sent in sentences:
                words = word_tokenize(sent.lower())
                words = [w for w in words if w.isalnum() and w not in stop_words]
                word_freq.update(words)
            
            # Normalize and score sentences
            max_freq = max(word_freq.values()) if word_freq else 1
            
            for sent in sentences:
                words = word_tokenize(sent.lower())
                words = [w for w in words if w.isalnum() and w not in stop_words]
                
                score = sum(word_freq[w]/max_freq for w in words)
                sentence_scores[sent] = score
            
            # Select top sentences (maintaining order)
            target_count = max(1, int(len(sentences) * compression_ratio))
            top_sentences = sorted(sentence_scores, key=sentence_scores.get, reverse=True)[:target_count]
            
            # Maintain original order
            summary = ' '.join(s for s in sentences if s in top_sentences)
            
            return {
                'summary': summary,
                'method': 'extractive-tfidf',
                'stats': {
                    'sentences_original': len(sentences),
                    'sentences_summary': len(top_sentences),
                    'compression_ratio': f"{compression_ratio*100:.0f}%"
                }
            }
        except Exception as e:
            logger.warning(f"TF-IDF extraction failed: {e}")
            return self._heuristic_summary(text)
    
    def _extractive_keyword(self, text: str, compression_ratio: float) -> Dict:
        """Extractive + keyword entity scoring (hybrid approach)."""
        if not HAS_NLTK:
            return self._heuristic_summary(text)
        
        try:
            sentences = sent_tokenize(text)
            if len(sentences) <= 2:
                return {'summary': text, 'method': 'extractive-keyword-single'}
            
            # Extract key entities (capital words, likely proper nouns)
            stop_words = set(stopwords.words('english'))
            entities = set()
            
            for sent in sentences:
                words = sent.split()
                for word in words:
                    # Proper noun heuristic
                    if word[0].isupper() and word not in {'The', 'A', 'An', 'This', 'That'}:
                        entities.add(word.lower())
            
            # Score sentences: contains entity + has content words
            sentence_scores = {}
            for sent in sentences:
                sent_lower = sent.lower()
                entity_score = sum(1 for e in entities if e in sent_lower)
                word_score = len([w for w in sent.split() if w not in stop_words])
                sentence_scores[sent] = entity_score * 2 + word_score
            
            # Select top sentences
            target_count = max(1, int(len(sentences) * compression_ratio))
            top_sentences = sorted(sentence_scores, key=sentence_scores.get, reverse=True)[:target_count]
            
            # Maintain order
            summary = ' '.join(s for s in sentences if s in top_sentences)
            
            return {
                'summary': summary,
                'method': 'extractive-keyword',
                'stats': {
                    'entities_found': len(entities),
                    'sentences_selected': len(top_sentences),
                    'compression_ratio': f"{compression_ratio*100:.0f}%"
                }
            }
        except Exception as e:
            logger.warning(f"Keyword extraction failed: {e}")
            return self._heuristic_summary(text)
    
    def _heuristic_summary(self, text: str) -> Dict:
        """Ultra-simple fallback: first + last sentences + middle."""
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        
        if len(sentences) <= 3:
            return {
                'summary': text,
                'method': 'heuristic-full'
            }
        
        # First sentence + middle + last sentence
        first = sentences[0]
        middle = sentences[len(sentences)//2] if len(sentences) > 1 else ""
        last = sentences[-1]
        
        summary = f"{first} {middle} {last}"
        
        return {
            'summary': summary,
            'method': 'heuristic-3sent',
            'stats': {
                'sentences_original': len(sentences),
                'sentences_summary': 3
            }
        }


def register_tool(registry):
    """Register advanced summarizer."""
    tool = AdvancedSummarizerTool()
    
    registry.register('summarize', tool.summarize)
    
    logger.info(
        "Registered advanced summarizer. "
        f"Abstractive available: {tool.abstractive is not None}. "
        f"NLTK available: {HAS_NLTK}"
    )
