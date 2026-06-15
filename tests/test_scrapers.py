from __future__ import annotations

import httpx

from scrapers.arxiv import scrape_arxiv
from scrapers.devto import scrape_devto
from scrapers.hackernews import scrape_hackernews


class MockResponse:
    def __init__(self, text: str = "", json_data=None, status_code: int = 200):
        self.text = text
        self._json = json_data
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=None)

    def json(self):
        return self._json


def test_scrape_arxiv_returns_normalized_entries(monkeypatch):
    rss = """
    <rss><channel><item>
      <title>AI Paper</title>
      <link>https://arxiv.org/abs/1234.5678</link>
      <description>Interesting abstract</description>
      <pubDate>Today</pubDate>
    </item></channel></rss>
    """

    monkeypatch.setattr(
        httpx,
        "get",
        lambda url, timeout=10.0, follow_redirects=False: MockResponse(text=rss),
    )
    papers = scrape_arxiv("ai", max_results=5)
    assert papers
    assert papers[0]["source"] == "arxiv"
    assert "title" in papers[0]
    assert "url" in papers[0]


def test_scrape_hackernews_filters_by_score(monkeypatch):
    hits = {
        "hits": [
            {"title": "Keep", "points": 80, "num_comments": 12, "url": "https://example.com", "created_at": "now"},
            {"title": "Skip", "points": 10, "num_comments": 1, "url": "https://skip.com", "created_at": "now"},
        ]
    }

    def fake_get(url, timeout=10.0, follow_redirects=False):
        if "algolia" in url:
            return MockResponse(json_data=hits)
        return MockResponse(text="<html><body>Useful article body</body></html>")

    monkeypatch.setattr(httpx, "get", fake_get)
    papers = scrape_hackernews("ai", max_results=5)
    assert len(papers) == 1
    assert papers[0]["title"] == "Keep"


def test_scrape_devto_handles_api_errors_gracefully(monkeypatch):
    def fake_get(url, timeout=10.0):
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(httpx, "get", fake_get)
    assert scrape_devto("ai", max_results=5) == []
