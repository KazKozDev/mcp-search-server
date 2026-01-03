"""
Bayesian credibility scoring for web sources with advanced features.
No API keys required - uses WHOIS, domain analysis, and citation networks.
"""

import logging
import re
import math
from typing import Dict, List
from urllib.parse import urlparse
from collections import defaultdict
from datetime import datetime

logger = logging.getLogger(__name__)

# Optional WHOIS for real domain age checking
try:
    import whois

    HAS_WHOIS = True
except ImportError:
    HAS_WHOIS = False
    logger.info("python-whois not installed. Using heuristic domain age.")


class BayesianCredibilityEngine:
    """
    Advanced Bayesian credibility scoring with:
    - Prior probabilities by domain category
    - 30+ signal features (URL, content, metadata)
    - Real domain age via WHOIS
    - Citation network with PageRank
    - Bayesian updating from outcomes
    - Uncertainty quantification
    - No API keys required
    """

    def __init__(self):
        # Prior probabilities for document credibility by category
        self.priors = {
            "academic": 0.88,
            "news": 0.75,
            "code": 0.80,
            "forum": 0.45,
            "blog": 0.50,
            "government": 0.85,
            "unknown": 0.50,
        }

        # Signal likelihood functions (learned)
        self.signal_likelihoods = defaultdict(
            lambda: {
                "given_high": 0.7,  # P(signal | credible)
                "given_low": 0.3,  # P(signal | not credible)
            }
        )

        # Domain-specific belief updates
        self.domain_beliefs = defaultdict(lambda: {"credible": 1, "not_credible": 1})

        # Citation graph (documents linking to/from each other)
        self.citation_network = defaultdict(lambda: {"cites": [], "cited_by": []})

        # PageRank scores cache
        self.pagerank_scores = {}

        # Domain age cache (WHOIS lookups are slow)
        self.domain_age_cache = {}

    async def score_document(
        self,
        url: str,
        title: str = None,
        abstract: str = None,
        full_text: str = None,
        metadata: Dict = None,
        citations_to: List[str] = None,
        citations_from: List[str] = None,
        outcome: float = None,  # Ground truth (0-1) for learning
    ) -> Dict:
        """
        Bayesian credibility assessment with epistemic uncertainty.

        Args:
            url: Document URL
            title, abstract, full_text: Content
            metadata: Structured data
            citations_to: URLs this doc cites
            citations_from: URLs that cite this doc
            outcome: Optional ground truth for Bayesian update

        Returns:
            Credibility score with uncertainty bounds
        """
        metadata = metadata or {}

        # 1) Extract continuous signal features
        features = await self._extract_features(url, title, abstract, full_text, metadata)

        # 2) Get prior from domain category
        category = self._categorize_domain(self._extract_domain(url))
        prior = self.priors.get(category, 0.50)

        # 3) Calculate likelihood from signals
        likelihood_high, likelihood_low = self._calculate_likelihoods(features)

        # 4) Bayesian update: P(credible | signals)
        posterior = self._bayesian_update(prior, likelihood_high, likelihood_low)

        # 5) Incorporate citation network influence with PageRank
        network_adjustment = self._network_influence_with_pagerank(
            url, citations_to, citations_from
        )
        posterior = 0.80 * posterior + 0.20 * network_adjustment

        # 6) Calculate credible interval (epistemic uncertainty)
        uncertainty = self._estimate_uncertainty(features, posterior)
        lower_bound = max(0.0, posterior - uncertainty)
        upper_bound = min(1.0, posterior + uncertainty)

        # 7) If we have outcome, update beliefs
        if outcome is not None:
            self._bayesian_update_from_outcome(category, features, outcome)

        return {
            "url": url,
            "domain": self._extract_domain(url),
            "category": category,
            "credibility_score": round(posterior, 3),
            "confidence_interval": (round(lower_bound, 3), round(upper_bound, 3)),
            "uncertainty": round(uncertainty, 3),
            "prior": round(prior, 3),
            "likelihood_ratio": round(likelihood_high / max(0.01, likelihood_low), 2),
            "pagerank": round(self.pagerank_scores.get(url, 0.0), 4),
            "signals": {k: round(v, 3) for k, v in features.items()},
            "recommendation": self._get_recommendation(posterior, uncertainty),
        }

    # ======== FEATURE EXTRACTION ========

    async def _extract_features(
        self,
        url: str,
        title: str,
        abstract: str,
        full_text: str,
        metadata: Dict,
    ) -> Dict[str, float]:
        """Extract high-dimensional feature vector (continuous values 0-1)."""
        features = {}

        # URL features
        domain = self._extract_domain(url)
        features["domain_age_signal"] = await self._get_real_domain_age(domain)
        features["domain_reputation"] = self._domain_reputation_score(domain)
        features["https_secure"] = 1.0 if url.startswith("https://") else 0.0
        features["domain_entropy"] = self._calculate_domain_entropy(domain)
        features["subdomain_depth"] = self._measure_subdomain_depth(domain)

        # Title features
        if title:
            features["title_formality"] = self._measure_formality(title)
            features["title_specificity"] = self._measure_specificity(title)
            features["title_sentiment_neutrality"] = self._measure_neutrality(title)
            features["title_length_norm"] = min(1.0, len(title) / 100)

        # Abstract features
        if abstract:
            features["abstract_completeness"] = self._measure_abstract_quality(abstract)
            features["methodology_clarity"] = self._detect_methodology(abstract)
            features["results_presence"] = self._detect_results(abstract)
            features["limitations_acknowledgment"] = self._detect_limitations(abstract)

        # Full text features
        if full_text:
            features["text_depth"] = self._measure_text_depth(full_text)
            features["evidence_density"] = self._measure_evidence_density(full_text)
            features["reference_quality"] = self._measure_reference_quality(full_text)
            features["logical_coherence"] = self._measure_coherence(full_text)

        # Metadata features
        features.update(self._extract_metadata_features(metadata))

        # Normalize all features to [0, 1]
        return {k: max(0.0, min(1.0, v)) for k, v in features.items()}

    async def _get_real_domain_age(self, domain: str) -> float:
        """
        Get REAL domain age using WHOIS lookup (cached).
        Falls back to heuristic if WHOIS unavailable.
        """
        if domain in self.domain_age_cache:
            return self.domain_age_cache[domain]

        if not HAS_WHOIS:
            # Fallback to heuristic
            score = self._estimate_domain_age_heuristic(domain)
            self.domain_age_cache[domain] = score
            return score

        try:
            # WHOIS lookup
            w = whois.whois(domain)
            creation_date = w.creation_date

            if creation_date:
                # Handle list of dates (some WHOIS return multiple)
                if isinstance(creation_date, list):
                    creation_date = creation_date[0]

                # Calculate age in years
                age_days = (datetime.utcnow() - creation_date).days
                age_years = age_days / 365.25

                # Score: older = more credible
                if age_years > 10:
                    score = 1.0
                elif age_years > 5:
                    score = 0.85
                elif age_years > 2:
                    score = 0.65
                elif age_years > 1:
                    score = 0.45
                else:
                    score = 0.25

                logger.info(f"WHOIS: {domain} is {age_years:.1f} years old (score: {score})")
                self.domain_age_cache[domain] = score
                return score

        except Exception as e:
            logger.debug(f"WHOIS lookup failed for {domain}: {e}")

        # Fallback
        score = self._estimate_domain_age_heuristic(domain)
        self.domain_age_cache[domain] = score
        return score

    def _estimate_domain_age_heuristic(self, domain: str) -> float:
        """Heuristic domain age estimation (fallback)."""
        established_domains = [
            "nature.com",
            "arxiv.org",
            "pubmed.ncbi.nlm.nih.gov",
            "bbc.com",
            "reuters.com",
            "github.com",
            "wikipedia.org",
            "nytimes.com",
            "theguardian.com",
            "ieee.org",
            "acm.org",
        ]
        return 1.0 if any(d in domain for d in established_domains) else 0.5

    def _domain_reputation_score(self, domain: str) -> float:
        """Reputation based on domain type indicators."""
        score = 0.7  # Base score

        # TLD reputation
        if domain.endswith(".edu"):
            score += 0.15
        if domain.endswith(".gov"):
            score += 0.20
        if domain.endswith(".org"):
            score += 0.05
        if ".ac." in domain:  # Academic (e.g., .ac.uk)
            score += 0.15

        # Suspicious TLDs
        suspicious_tlds = [".xyz", ".top", ".click", ".loan", ".win"]
        if any(domain.endswith(tld) for tld in suspicious_tlds):
            score -= 0.30

        return min(1.0, max(0.0, score))

    def _calculate_domain_entropy(self, domain: str) -> float:
        """
        Calculate Shannon entropy of domain name.
        Lower entropy = more memorable/established.
        """
        if not domain:
            return 0.5

        # Calculate character frequency
        from collections import Counter

        freq = Counter(domain)
        length = len(domain)

        # Shannon entropy
        entropy = -sum((count / length) * math.log2(count / length) for count in freq.values())

        # Normalize: typical domains have entropy 2.5-4.0
        normalized = entropy / 4.0

        # Invert: lower entropy = higher credibility
        return 1.0 - min(1.0, normalized)

    def _measure_subdomain_depth(self, domain: str) -> float:
        """
        Measure subdomain nesting depth.
        Deep nesting often indicates phishing/spam.
        """
        parts = domain.split(".")
        depth = len(parts) - 2  # Subtract TLD and main domain

        if depth <= 0:
            return 1.0  # No subdomain
        elif depth == 1:
            return 0.9  # One subdomain (common, e.g., www)
        elif depth == 2:
            return 0.6  # Two subdomains (less common)
        else:
            return 0.3  # Deep nesting (suspicious)

    def _measure_formality(self, text: str) -> float:
        """Measure formal language level."""
        formal_words = [
            "however",
            "furthermore",
            "moreover",
            "consequently",
            "analysis",
            "investigation",
            "methodology",
            "hypothesis",
            "demonstrates",
            "indicates",
            "suggests",
            "reveals",
        ]
        matches = sum(1 for w in formal_words if w in text.lower())
        return min(1.0, matches / 5)

    def _measure_specificity(self, text: str) -> float:
        """High specificity = more credible."""
        numbers = len(re.findall(r"\d+", text))
        quotes = text.count('"')
        return min(1.0, (numbers + quotes) / 10)

    def _measure_neutrality(self, text: str) -> float:
        """Detect sensational language."""
        sensational = [
            "shocking",
            "amazing",
            "unbelievable",
            "viral",
            "insane",
            "you won't believe",
            "doctors hate",
            "one weird trick",
            "mind-blowing",
            "incredible",
            "secret",
            "they don't want you to know",
        ]
        negativity = sum(1 for s in sensational if s in text.lower())
        return 1.0 - min(1.0, negativity / 3)

    def _measure_abstract_quality(self, abstract: str) -> float:
        """Proper abstracts are 100-300 words."""
        word_count = len(abstract.split())
        if 100 < word_count < 300:
            return 1.0
        elif 50 < word_count < 500:
            return 0.7
        else:
            return 0.3

    def _detect_methodology(self, text: str) -> float:
        """Detect methodology description."""
        match = len(
            re.findall(
                r"\b(method|approach|design|study|experiment|procedure|protocol)\b", text, re.I
            )
        )
        return min(1.0, match / 3)

    def _detect_results(self, text: str) -> float:
        """Detect results/findings."""
        match = len(
            re.findall(r"\b(result|finding|show|demonstrate|conclude|find|observe)\b", text, re.I)
        )
        return min(1.0, match / 3)

    def _detect_limitations(self, text: str) -> float:
        """Credible papers acknowledge limitations."""
        match = len(
            re.findall(
                r"\b(limit|caveat|future work|further research|constraint|weakness)\b", text, re.I
            )
        )
        return min(1.0, match / 2)

    def _measure_text_depth(self, text: str) -> float:
        """Deeper = more credible."""
        length = len(text)
        if length > 10000:
            return 1.0
        elif length > 3000:
            return 0.8
        elif length > 500:
            return 0.5
        else:
            return 0.2

    def _measure_evidence_density(self, text: str) -> float:
        """Presence of numbers, data, statistics."""
        data = len(re.findall(r"\d+\.?\d*%|\d+:\d+|\(.*\d.*\)", text))
        return min(1.0, data / 20)

    def _measure_reference_quality(self, text: str) -> float:
        """Count and normalize references."""
        refs = len(re.findall(r"\[\d+\]|et al\.|doi:|arxiv:", text, re.I))
        return min(1.0, refs / 30)

    def _measure_coherence(self, text: str) -> float:
        """Measure logical flow with transition words."""
        transitions = len(
            re.findall(
                r"\b(however|therefore|consequently|moreover|furthermore|thus|hence)\b", text, re.I
            )
        )
        return min(1.0, transitions / 10)

    def _extract_metadata_features(self, meta: Dict) -> Dict[str, float]:
        """Extract structured metadata features."""
        features = {}

        # Year recency
        year = meta.get("year")
        if year:
            current = datetime.utcnow().year
            age = current - int(year)
            if age <= 2:
                features["recent"] = 1.0
            elif age <= 10:
                features["recent"] = 0.6
            else:
                features["recent"] = 0.3

        # Peer review
        features["peer_reviewed"] = 1.0 if meta.get("is_peer_reviewed") else 0.3

        # Authors
        authors = meta.get("authors") or []
        if isinstance(authors, list):
            features["multi_author"] = min(1.0, len(authors) / 5)

        # Citations
        citations = meta.get("citations") or 0
        features["citation_impact"] = min(1.0, math.log10(citations + 1) / 3)

        # DOI
        features["has_doi"] = 1.0 if meta.get("doi") else 0.5

        return features

    # ======== BAYESIAN LOGIC ========

    def _calculate_likelihoods(self, features: Dict[str, float]) -> tuple:
        """
        Calculate P(features | credible) and P(features | not credible).
        Uses learned signal likelihoods.
        """
        likelihood_high = 1.0
        likelihood_low = 1.0

        for signal, value in features.items():
            # Get learned likelihood
            if signal in self.signal_likelihoods:
                p_high = self.signal_likelihoods[signal]["given_high"]
                p_low = self.signal_likelihoods[signal]["given_low"]
            else:
                # Default: assume signals are informative
                p_high = value + 0.2
                p_low = (1 - value) * 0.8

            likelihood_high *= max(0.01, p_high)
            likelihood_low *= max(0.01, p_low)

        return likelihood_high, likelihood_low

    def _bayesian_update(
        self,
        prior: float,
        likelihood_high: float,
        likelihood_low: float,
    ) -> float:
        """
        Bayes' rule: P(credible | signals) =
            P(signals | credible) * P(credible) / P(signals)
        """
        numerator = likelihood_high * prior
        denominator = (likelihood_high * prior) + (likelihood_low * (1 - prior))

        if denominator < 1e-10:
            return prior

        posterior = numerator / denominator
        return max(0.0, min(1.0, posterior))

    def _estimate_uncertainty(self, features: Dict[str, float], posterior: float) -> float:
        """
        Epistemic uncertainty based on:
        - Number of signals (more signals = less uncertainty)
        - Feature variance (uniform features = more uncertainty)
        """
        n_signals = len(features)
        max_signals = 25

        # Variance of features
        if features:
            mean = sum(features.values()) / len(features)
            variance = sum((v - mean) ** 2 for v in features.values()) / len(features)
        else:
            variance = 0.5

        # Combine
        signal_confidence = n_signals / max_signals
        variance_confidence = 1.0 - variance

        total_confidence = 0.6 * signal_confidence + 0.4 * variance_confidence
        uncertainty = (1.0 - total_confidence) * 0.15  # Max 15% uncertainty

        return uncertainty

    # ======== CITATION NETWORK & PAGERANK ========

    def _network_influence_with_pagerank(
        self,
        url: str,
        citations_to: List[str] = None,
        citations_from: List[str] = None,
    ) -> float:
        """
        Incorporate citation network with PageRank algorithm.
        High-credibility sources citing you = boost.
        You citing credible sources = boost.
        """
        # Update citation graph
        if citations_to:
            self.citation_network[url]["cites"] = citations_to
            for cited in citations_to:
                if url not in self.citation_network[cited]["cited_by"]:
                    self.citation_network[cited]["cited_by"].append(url)

        if citations_from:
            self.citation_network[url]["cited_by"] = citations_from
            for citing in citations_from:
                if url not in self.citation_network[citing]["cites"]:
                    self.citation_network[citing]["cites"].append(url)

        # Compute PageRank for this subgraph (if enough nodes)
        if len(self.citation_network) > 3:
            self._compute_pagerank()

        # Get PageRank score for this URL
        pagerank = self.pagerank_scores.get(url, 0.15)  # Default 0.15 (damping factor)

        # Basic network score
        cites_count = len(citations_to) if citations_to else 0
        cited_by_count = len(citations_from) if citations_from else 0

        base_score = 0.5
        base_score += 0.1 * min(1.0, cites_count / 10)  # Citing others
        base_score += 0.2 * min(1.0, cited_by_count / 5)  # Being cited

        # Combine with PageRank
        network_score = 0.6 * base_score + 0.4 * min(1.0, pagerank * 3)

        return min(1.0, network_score)

    def _compute_pagerank(self, damping=0.85, iterations=20):
        """
        Compute PageRank for citation network.
        Simple iterative algorithm (no external dependencies).
        """
        nodes = list(self.citation_network.keys())
        n = len(nodes)

        if n == 0:
            return

        # Initialize scores
        scores = {node: 1.0 / n for node in nodes}

        for _ in range(iterations):
            new_scores = {}

            for node in nodes:
                # Get incoming citations
                incoming = self.citation_network[node]["cited_by"]

                # PageRank formula
                rank_sum = 0.0
                for citing_node in incoming:
                    if citing_node in scores:
                        outgoing_count = len(self.citation_network[citing_node]["cites"])
                        if outgoing_count > 0:
                            rank_sum += scores[citing_node] / outgoing_count

                new_scores[node] = (1 - damping) / n + damping * rank_sum

            scores = new_scores

        # Update cache
        self.pagerank_scores.update(scores)

    def _bayesian_update_from_outcome(
        self,
        category: str,
        features: Dict[str, float],
        outcome: float,
    ):
        """Learn from ground truth outcome using Bayesian updating."""
        # Update domain beliefs
        if outcome > 0.7:
            self.domain_beliefs[category]["credible"] += 1
        else:
            self.domain_beliefs[category]["not_credible"] += 1

        # Update signal likelihoods
        for signal, value in features.items():
            if outcome > 0.7:
                # This signal correlates with credibility
                self.signal_likelihoods[signal]["given_high"] *= 1.05
                self.signal_likelihoods[signal]["given_low"] *= 0.95
            else:
                # This signal correlates with low credibility
                self.signal_likelihoods[signal]["given_high"] *= 0.95
                self.signal_likelihoods[signal]["given_low"] *= 1.05

    # ======== HELPERS ========

    def _categorize_domain(self, domain: str) -> str:
        patterns = {
            "academic": [
                "arxiv",
                "pubmed",
                "nature",
                "scholar",
                "springer",
                "ieee",
                ".edu",
                ".ac.",
            ],
            "news": ["bbc", "reuters", "nytimes", "guardian", "ft.com", "apnews", "cnn"],
            "code": ["github", "gitlab", "stackoverflow", "bitbucket"],
            "forum": ["reddit", "ycombinator", "discourse"],
            "blog": ["medium", "substack", "wordpress", "blogspot"],
            "government": [".gov", "gov.uk", "europa.eu"],
        }
        for cat, patterns_list in patterns.items():
            if any(p in domain for p in patterns_list):
                return cat
        return "unknown"

    def _extract_domain(self, url: str) -> str:
        try:
            parsed = urlparse(url)
            host = parsed.netloc.lower()
            return host[4:] if host.startswith("www.") else host
        except Exception:
            return url.lower()

    def _get_recommendation(self, score: float, uncertainty: float) -> str:
        if score > 0.85 and uncertainty < 0.10:
            return "✓✓ Excellent source"
        elif score > 0.70:
            return "✓ Good source, verify key claims"
        elif score > 0.50:
            return "⚠ Use with caution"
        else:
            return "✗ Limited credibility"


# Global engine instance
_credibility_engine = BayesianCredibilityEngine()


async def assess_source_credibility(
    url: str,
    title: str = None,
    content: str = None,
    metadata: Dict = None,
) -> Dict:
    """
    Assess credibility of a web source.

    Args:
        url: Source URL
        title: Document title
        content: Full text content
        metadata: Structured metadata

    Returns:
        Credibility assessment with score and recommendation
    """
    return await _credibility_engine.score_document(
        url=url, title=title, full_text=content, metadata=metadata
    )
