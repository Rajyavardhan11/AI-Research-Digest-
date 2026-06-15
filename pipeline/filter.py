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


def filter_top_papers(papers: list[dict], topic: str, max_results: int = 5) -> list[dict]:
    if len(papers) <= max_results:
        return papers[:max_results]

    prompt_lines = []
    for index, paper in enumerate(papers):
        prompt_lines.append(
            f"{index}. Title: {paper.get('title', '')}\nAbstract: {paper.get('abstract', '')}\n"
        )

    prompt = (
        f"You are curating a digest about {topic}. Select the top {max_results} items that are "
        "technically significant, novel, and relevant. Return ONLY valid JSON with keys "
        '"selected_indices" and "reasoning".\n\n'
        + "\n".join(prompt_lines)
    )

    try:
        raw = _ollama_generate(prompt)
        payload = json.loads(raw)
        indices = [idx for idx in payload.get("selected_indices", []) if isinstance(idx, int)]
        selected = [papers[idx] for idx in indices if 0 <= idx < len(papers)]
        return selected[:max_results] or papers[:max_results]
    except (httpx.HTTPError, ValueError, json.JSONDecodeError, KeyError) as exc:
        logger.warning("Falling back to first papers during filter step: %s", exc)
        return papers[:max_results]
