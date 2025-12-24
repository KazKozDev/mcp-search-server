#!/usr/bin/env python3
"""Test script for credibility assessment tool."""

import asyncio
import sys
from src.mcp_search_server.tools.credibility import assess_source_credibility


async def test_academic_source():
    """Test academic source (should score high)."""
    print("\n=== Test 1: Academic Source (arXiv) ===")
    result = await assess_source_credibility(
        url="https://arxiv.org/abs/2301.00234",
        title="Deep Learning for Medical Imaging",
        metadata={"year": 2023, "is_peer_reviewed": True, "citations": 150}
    )

    print(f"URL: {result['url']}")
    print(f"Category: {result['category']}")
    print(f"Score: {result['credibility_score']} / 1.0")
    print(f"Confidence Interval: {result['confidence_interval']}")
    print(f"Recommendation: {result['recommendation']}")
    print(f"PageRank: {result['pagerank']}")
    print(f"Top 5 signals:")
    sorted_signals = sorted(result['signals'].items(), key=lambda x: x[1], reverse=True)[:5]
    for signal, value in sorted_signals:
        print(f"  - {signal}: {value:.3f}")

    assert result['credibility_score'] > 0.80, "Academic source should score > 0.80"
    assert result['category'] == 'academic', "Should be categorized as academic"
    print("✓ PASSED")


async def test_news_source():
    """Test news source (should score medium-high)."""
    print("\n=== Test 2: News Source (BBC) ===")
    result = await assess_source_credibility(
        url="https://bbc.com/news/article-123",
        title="Breaking News: Important Event"
    )

    print(f"URL: {result['url']}")
    print(f"Category: {result['category']}")
    print(f"Score: {result['credibility_score']} / 1.0")
    print(f"Recommendation: {result['recommendation']}")

    assert result['credibility_score'] > 0.60, "News source should score > 0.60"
    assert result['category'] == 'news', "Should be categorized as news"
    print("✓ PASSED")


async def test_blog_source():
    """Test blog source with sensational content (should score lower)."""
    print("\n=== Test 3: Blog Source with Sensational Content ===")
    result = await assess_source_credibility(
        url="https://random-clickbait-blog.xyz/shocking-secrets",
        title="You Won't Believe This Amazing Shocking Secret Doctors Don't Want You To Know!",
        content="""
        This is absolutely mind-blowing and viral! You'll never believe what happened!
        It's shocking, incredible, and amazing all at once. This one weird trick will change your life!
        No methodology, no studies, no evidence - just clickbait nonsense.
        """
    )

    print(f"URL: {result['url']}")
    print(f"Category: {result['category']}")
    print(f"Score: {result['credibility_score']} / 1.0")
    print(f"Recommendation: {result['recommendation']}")
    print(f"Neutrality score: {result['signals'].get('title_sentiment_neutrality', 0):.3f}")

    # With sensational content + suspicious TLD, should score lower
    assert result['credibility_score'] < 0.75, "Clickbait blog should score < 0.75"
    assert result['signals'].get('title_sentiment_neutrality', 1.0) < 0.3, "Should detect sensationalism"
    print("✓ PASSED")


async def test_github_source():
    """Test code repository source."""
    print("\n=== Test 4: GitHub Repository ===")
    result = await assess_source_credibility(
        url="https://github.com/torvalds/linux",
        title="Linux Kernel Repository"
    )

    print(f"URL: {result['url']}")
    print(f"Category: {result['category']}")
    print(f"Score: {result['credibility_score']} / 1.0")
    print(f"Recommendation: {result['recommendation']}")

    assert result['category'] == 'code', "Should be categorized as code"
    print("✓ PASSED")


async def test_with_full_content():
    """Test with full content and metadata."""
    print("\n=== Test 5: Full Content Analysis ===")
    result = await assess_source_credibility(
        url="https://nature.com/articles/nature12345",
        title="Climate Change Impact on Biodiversity",
        content="""
        This study investigates the impact of climate change on biodiversity.
        Our methodology involved analyzing data from 500 species across 50 ecosystems.
        Results demonstrate a significant correlation between temperature rise and species decline.
        However, this study has limitations including geographic scope and temporal constraints.
        Future research should expand to more diverse ecosystems.
        References: [1] Smith et al. 2020, doi:10.1038/nature.123
        """,
        metadata={
            "year": 2023,
            "authors": ["Smith, J.", "Doe, A.", "Brown, K."],
            "citations": 250,
            "doi": "10.1038/nature.12345",
            "is_peer_reviewed": True
        }
    )

    print(f"URL: {result['url']}")
    print(f"Category: {result['category']}")
    print(f"Score: {result['credibility_score']} / 1.0")
    print(f"Confidence Interval: {result['confidence_interval']}")
    print(f"Uncertainty: ±{result['uncertainty']}")
    print(f"Recommendation: {result['recommendation']}")

    # Should score high for quality academic content with full metadata
    assert result['credibility_score'] > 0.85, "High-quality academic content should score > 0.85"

    # Show detected signals
    print(f"Text depth: {result['signals'].get('text_depth', 0):.3f}")
    print(f"Reference quality: {result['signals'].get('reference_quality', 0):.3f}")
    print(f"Evidence density: {result['signals'].get('evidence_density', 0):.3f}")
    print(f"Peer reviewed: {result['signals'].get('peer_reviewed', 0):.3f}")
    print(f"Has DOI: {result['signals'].get('has_doi', 0):.3f}")
    print("✓ PASSED")


async def test_citation_network():
    """Test citation network capability (currently not exposed in wrapper)."""
    print("\n=== Test 6: Citation Network (Internal Feature) ===")
    print("Note: Citation network tracking is implemented in BayesianCredibilityEngine")
    print("but not yet exposed through the MCP tool wrapper.")
    print("Future enhancement: Add citations_to/citations_from parameters to MCP tool.")
    print("✓ SKIPPED (Feature exists but not exposed)")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Bayesian Credibility Assessment Tool")
    print("=" * 60)

    try:
        await test_academic_source()
        await test_news_source()
        await test_blog_source()
        await test_github_source()
        await test_with_full_content()
        await test_citation_network()

        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED!")
        print("=" * 60)
        return 0

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
