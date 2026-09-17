"""Unit tests for URL metadata extraction, media parsing, and tag inference."""
import pytest
from app.extractor import detect_link_type, extract_domain, extract_youtube_id, infer_tags
from app.models import LinkType


def test_detect_link_type():
    assert detect_link_type("https://github.com/NousResearch/hermes-agent") == LinkType.GITHUB
    assert detect_link_type("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == LinkType.VIDEO
    assert detect_link_type("https://youtu.be/dQw4w9WgXcQ") == LinkType.VIDEO
    assert detect_link_type("https://arxiv.org/abs/1706.03762") == LinkType.PAPER
    assert detect_link_type("https://x.com/user/status/123456") == LinkType.X_POST
    assert detect_link_type("https://www.producthunt.com/posts/example") == LinkType.TOOL
    assert detect_link_type("https://example.com/blog/my-post") == LinkType.ARTICLE


def test_extract_domain():
    assert extract_domain("https://www.example.com/article/123") == "example.com"
    assert extract_domain("http://github.com/torvalds/linux") == "github.com"
    assert extract_domain("https://news.ycombinator.com") == "news.ycombinator.com"


def test_extract_youtube_id():
    assert extract_youtube_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_youtube_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_youtube_id("https://www.youtube.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_youtube_id("https://example.com/not-youtube") is None


def test_infer_tags():
    tags = infer_tags(
        url="https://github.com/pytorch/pytorch",
        title="PyTorch Machine Learning Library",
        summary="Deep learning neural network library written in Python and C++.",
        entry_type=LinkType.GITHUB,
    )
    assert "open-source" in tags
    assert "dev-tools" in tags
    assert "ai" in tags
    assert "python" in tags
