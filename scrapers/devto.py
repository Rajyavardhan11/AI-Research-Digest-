from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)


def scrape_devto(topic: str, max_results: int = 10) -> list[dict]:
    del topic
    url = "https://dev.to/api/articles?tag=ai&per_page=10&top=7"
    try:
        response = httpx.get(url, timeout=10.0)
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Dev.to scrape failed: %s", exc)
        return []

    results: list[dict] = []
    for article in payload:
        if int(article.get("positive_reactions_count") or 0) <= 20:
            continue
        results.append(
            {
                "title": article.get("title", "Untitled"),
                "url": article.get("url", ""),
                "abstract": article.get("description", "") or "",
                "published": article.get("published_at", ""),
                "source": "devto",
            }
        )
        if len(results) >= max_results:
            break
    return results
