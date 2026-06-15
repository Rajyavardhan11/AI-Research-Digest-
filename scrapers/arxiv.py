from __future__ import annotations

import logging
from urllib.parse import quote_plus

import feedparser
import httpx

logger = logging.getLogger(__name__)


def scrape_arxiv(topic: str, max_results: int = 20) -> list[dict]:
    search_url = f"https://arxiv.org/search/?searchtype=all&query={quote_plus(topic)}&start=0"
    rss_url = "http://arxiv.org/rss/cs.AI"
    entries: list[dict] = []
    seen_urls: set[str] = set()

    try:
        httpx.get(search_url, timeout=10.0)
        response = httpx.get(rss_url, timeout=10.0, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("ArXiv scrape failed: %s", exc)
        return []

    feed = feedparser.parse(response.text)
    for entry in feed.entries[: max_results * 2]:
        url = entry.get("link", "")
        if not url or url in seen_urls:
            continue

        seen_urls.add(url)
        authors = [author.get("name", "") for author in entry.get("authors", []) if author.get("name")]
        summary = entry.get("summary", "").strip().replace("\n", " ")
        entries.append(
            {
                "title": entry.get("title", "Untitled"),
                "authors": authors,
                "abstract": summary[:500],
                "url": url,
                "published": entry.get("published", ""),
                "source": "arxiv",
            }
        )
        if len(entries) >= max_results:
            break

    return entries
