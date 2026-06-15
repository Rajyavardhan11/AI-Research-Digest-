from __future__ import annotations

import json
import logging

import httpx

from config import settings

logger = logging.getLogger(__name__)


def _ollama_generate(prompt: str) -> str:
    response = httpx.post(
        f"{settings.ollama_base_url}/api/generate",
        json={"model": settings.ollama_model, "prompt": prompt, "stream": False},
        timeout=45.0,
    )
    response.raise_for_status()
    data = response.json()
    return data.get("response", "")


def summarize_paper(paper: dict) -> dict:
    prompt = (
        "Summarize this AI paper/article for a technical developer audience. "
        "Be concise and focus on: what problem it solves, the key approach, and why it matters. "
        "Max 3 sentences. Also return a short key_insight and difficulty label. "
        'Return ONLY JSON with keys "summary", "key_insight", and "difficulty".\n\n'
        f"Title: {paper.get('title', '')}\n"
        f"Abstract: {paper.get('abstract', '')}"
    )
    fallback = {
        **paper,
        "summary": paper.get("abstract", "Summary unavailable.")[:240] or "Summary unavailable.",
        "key_insight": "Worth tracking",
        "difficulty": "intermediate",
    }

    try:
        raw = _ollama_generate(prompt)
        payload = json.loads(raw)
        return {
            **paper,
            "summary": str(payload.get("summary") or fallback["summary"]),
            "key_insight": str(payload.get("key_insight") or fallback["key_insight"])[:120],
            "difficulty": str(payload.get("difficulty") or fallback["difficulty"]).lower(),
        }
    except (httpx.HTTPError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("Falling back during summarize step for %s: %s", paper.get("title"), exc)
        return fallback


def summarize_all(papers: list[dict]) -> list[dict]:
    summarized: list[dict] = []
    total = len(papers)
    for index, paper in enumerate(papers, start=1):
        logger.info("Summarizing %s/%s: %s", index, total, paper.get("title", "Untitled"))
        summarized.append(summarize_paper(paper))
    return summarized
