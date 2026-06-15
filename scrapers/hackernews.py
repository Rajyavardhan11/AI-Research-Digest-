from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def _extract_preview_text(url: str) -> str:
    try:
        response = httpx.get(url, timeout=5.0, follow_redirects=True)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        text = " ".join(soup.stripped_strings)
        return text[:300]
    except (httpx.HTTPError, ValueError) as exc:
        logger.info("Skipping abstract fetch for %s: %s", url, exc)
        return ""


def scrape_hackernews(topic: str, max_results: int = 10) -> list[dict]:
    yesterday_ts = int((datetime.now(timezone.utc) - timedelta(days=1)).timestamp())
    url = (
        "https://hn.algolia.com/api/v1/search"
        f"?query={quote_plus(topic)}&tags=story&numericFilters=created_at_i>{yesterday_ts}"
    )
    try:
        response = httpx.get(url, timeout=10.0)
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Hacker News scrape failed: %s", exc)
        return []

    results: list[dict] = []
    for hit in payload.get("hits", []):
        score = int(hit.get("points") or 0)
        if score <= 50:
            continue
        article_url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
        results.append(
            {
                "title": hit.get("title", "Untitled"),
                "url": article_url,
                "score": score,
                "comments": int(hit.get("num_comments") or 0),
                "published": hit.get("created_at", ""),
                "abstract": _extract_preview_text(article_url),
                "source": "hackernews",
            }
        )
        if len(results) >= max_results:
            break
    return results
