# Bayesian Credibility Assessment Tool

## Overview

Advanced source credibility scoring system using Bayesian inference, domain analysis, and citation network algorithms. **No API keys required.**

## Features

### 1. Real Domain Age via WHOIS
- Automatic WHOIS lookup for accurate domain registration dates
- Age-based credibility scoring (older = more established)
- Caching to minimize lookup delays
- Graceful fallback to heuristic if WHOIS unavailable

### 2. 30+ Signal Features
- **URL signals**: Domain age, reputation, HTTPS, entropy, subdomain depth
- **Content signals**: Formality, specificity, neutrality, evidence density
- **Metadata signals**: Peer review, citations, DOI, author count, recency
- **Text analysis**: Methodology, results, limitations, references, coherence

### 3. Citation Network with PageRank
- Builds citation graph from document links
- Computes PageRank scores iteratively (no external dependencies)
- High-credibility sources citing you = credibility boost
- Citing credible sources = credibility boost

### 4. Bayesian Inference
- Category-specific priors (academic=0.88, news=0.75, forum=0.45)
- Likelihood estimation from signals
- Posterior probability calculation
- Real-time learning from outcomes

### 5. Uncertainty Quantification
- Epistemic uncertainty estimation
- Confidence intervals (e.g., 0.75 ± 0.08)
- Based on signal count and variance

## Usage

### Basic Assessment
```python
result = await assess_source_credibility(
    url="https://nature.com/articles/123"
)
```

### With Title and Content (Recommended)
```python
result = await assess_source_credibility(
    url="https://arxiv.org/abs/2301.00234",
    title="Deep Learning for Medical Imaging",
    content="Full article text here...",
    metadata={
        "year": 2023,
        "authors": ["Smith, J.", "Doe, A."],
        "citations": 42,
        "doi": "10.1234/arxiv.2301.00234",
        "is_peer_reviewed": True
    }
)
```

### Response Format
```json
{
    "url": "https://arxiv.org",
    "domain": "arxiv.org",
    "category": "academic",
    "credibility_score": 0.896,
    "confidence_interval": [0.823, 0.969],
    "uncertainty": 0.073,
    "prior": 0.88,
    "likelihood_ratio": 12.4,
    "pagerank": 0.0,
    "signals": {
        "domain_age_signal": 1.0,
        "domain_reputation": 0.85,
        "https_secure": 1.0,
        "peer_reviewed": 1.0,
        ...
    },
    "recommendation": "✓✓ Excellent source"
}
```

## Scoring Interpretation

### Score Ranges
- **0.85-1.0**: ✓✓ Excellent source
- **0.70-0.85**: ✓ Good source, verify key claims
- **0.50-0.70**: ⚠ Use with caution
- **0.0-0.50**: ✗ Limited credibility

### Categories & Priors
- **Academic** (0.88): arxiv, pubmed, nature, .edu, .ac.
- **News** (0.75): bbc, reuters, nytimes, guardian
- **Code** (0.80): github, gitlab, stackoverflow
- **Government** (0.85): .gov, gov.uk
- **Forum** (0.45): reddit, ycombinator
- **Blog** (0.50): medium, substack, wordpress
- **Unknown** (0.50): other domains

## Advanced Features

### Domain Age Analysis
```python
# With python-whois installed (optional)
# Automatically checks domain registration date
# Example: nature.com registered in 1995 → score 1.0

# Without python-whois
# Falls back to known domains heuristic
```

### Citation Network
```python
# Build citation graph
result1 = await assess_source_credibility(
    url="https://paper1.com",
    citations_to=["https://arxiv.org", "https://nature.com"]
)

result2 = await assess_source_credibility(
    url="https://paper2.com",
    citations_from=["https://paper1.com"]
)

# PageRank computed automatically
# paper1 cites credible sources → boost
# paper2 cited by paper1 → boost
```

### Real-time Learning
```python
# Provide ground truth outcomes to improve accuracy
result = await assess_source_credibility(
    url="https://example.com",
    outcome=0.9  # 0-1: actual credibility (from manual review)
)
# Engine updates signal likelihoods and domain beliefs
```

## Technical Details

### Signal Features (30+)

**Domain Features:**
- `domain_age_signal`: WHOIS-based age (0-1)
- `domain_reputation`: TLD-based (.edu, .gov bonus)
- `https_secure`: HTTPS vs HTTP
- `domain_entropy`: Shannon entropy (lower = more memorable)
- `subdomain_depth`: Nesting depth (deep = suspicious)

**Content Features:**
- `title_formality`: Academic language detection
- `title_specificity`: Numbers, quotes, concrete claims
- `title_sentiment_neutrality`: Anti-sensationalism
- `text_depth`: Content length (longer = more credible)
- `evidence_density`: Statistics, data, citations
- `reference_quality`: References, DOIs, et al.
- `logical_coherence`: Transition words

**Metadata Features:**
- `recent`: Publication recency
- `peer_reviewed`: Peer review status
- `multi_author`: Number of authors
- `citation_impact`: Log-normalized citation count
- `has_doi`: DOI presence

### Bayesian Formula

```
P(credible | signals) = P(signals | credible) × P(credible) / P(signals)

Where:
- P(credible) = prior (category baseline)
- P(signals | credible) = product of signal likelihoods
- P(signals) = normalizing constant
```

### PageRank Algorithm

```python
# Iterative computation (20 iterations, damping=0.85)
for node in graph:
    rank[node] = (1-d)/N + d × Σ(rank[citing]/outlinks[citing])
```

### Uncertainty Estimation

```python
uncertainty = (1 - confidence) × 0.15

confidence = 0.6 × (signals/max_signals) + 0.4 × (1 - variance)
```

## Installation

### Required (always installed)
```bash
pip install mcp-search-server
```

### Optional (for WHOIS domain age)
```bash
pip install mcp-search-server[credibility]
# or
pip install python-whois
```

## Performance

- **Without WHOIS**: ~50ms per assessment
- **With WHOIS (first lookup)**: ~500-2000ms
- **With WHOIS (cached)**: ~50ms

Cache automatically stores domain ages to minimize WHOIS lookups.

## Examples

### Academic Paper
```python
result = await assess_source_credibility(
    url="https://arxiv.org/abs/2301.00234",
    title="Attention Is All You Need",
    metadata={"year": 2017, "citations": 50000, "is_peer_reviewed": True}
)
# Score: ~0.92 (Excellent source)
```

### News Article
```python
result = await assess_source_credibility(
    url="https://bbc.com/news/article-123",
    title="Breaking News: Major Discovery",
    content="Full article text..."
)
# Score: ~0.78 (Good source)
```

### Blog Post
```python
result = await assess_source_credibility(
    url="https://random-blog.com/clickbait-title",
    title="You Won't Believe This Amazing Trick!"
)
# Score: ~0.35 (Limited credibility)
# Low formality, sensational language, unknown domain
```

### Forum Discussion
```python
result = await assess_source_credibility(
    url="https://reddit.com/r/science/comments/xyz",
    content="Detailed discussion with references..."
)
# Score: ~0.55 (Use with caution)
# Forum baseline low, but quality content boosts it
```

## Integration with Search

Use credibility assessment to rank and filter search results:

```python
# Search web
results = await search_duckduckgo("climate change research")

# Assess credibility of top results
for result in results[:5]:
    credibility = await assess_source_credibility(
        url=result['url'],
        title=result['title'],
        content=result.get('snippet')
    )
    result['credibility_score'] = credibility['credibility_score']
    result['recommendation'] = credibility['recommendation']

# Sort by credibility
results.sort(key=lambda x: x.get('credibility_score', 0), reverse=True)
```

## Limitations

1. **WHOIS availability**: Some domains don't expose WHOIS data
2. **Content required**: Better accuracy with full text vs just URL
3. **Citation graph**: Requires multiple documents to compute PageRank
4. **Heuristic-based**: Some signals use pattern matching (not ML)
5. **No external validation**: No fact-checking APIs (all local)

## Future Enhancements (Requires API Keys)

These features are NOT yet implemented but could be added:

1. **Google Safe Browsing API**: Malware/phishing detection
2. **VirusTotal API**: Domain reputation checks
3. **Fact-checking APIs**: Snopes, FactCheck.org integration
4. **Author credibility**: Google Scholar H-index lookup
5. **Bias detection**: ML-based political bias scoring

See `INTEGRATION_SUMMARY.md` for implementation details.

## License

MIT License - See LICENSE file
