from __future__ import annotations

from datetime import datetime

from pipeline.compiler import compile_digest
from pipeline.filter import filter_top_papers
from pipeline.summarizer import summarize_all, summarize_paper
from scheduler import run_digest_pipeline


def sample_papers() -> list[dict]:
    return [
        {
            "title": "Paper One",
            "authors": ["A. Researcher"],
            "abstract": "Paper one abstract",
            "url": "https://example.com/paper-1",
            "published": "2026-01-01",
            "source": "arxiv",
        },
        {
            "title": "Paper Two",
            "authors": [],
            "abstract": "Paper two abstract",
            "url": "https://example.com/paper-2",
            "published": "2026-01-02",
            "source": "devto",
        },
    ]


def test_filter_returns_max_results():
    selected = filter_top_papers(sample_papers(), "ai", max_results=1)
    assert len(selected) == 1


def test_summarizer_adds_enriched_fields():
    summarized = summarize_paper(sample_papers()[0])
    assert "summary" in summarized
    assert "key_insight" in summarized
    assert "difficulty" in summarized


def test_compiler_renders_valid_html():
    html = compile_digest(summarize_all(sample_papers()), datetime(2026, 1, 1))
    assert "AI Research Digest" in html
    assert "Paper One" in html


def test_full_pipeline_runs_end_to_end(db_session):
    result = run_digest_pipeline(session=db_session, send_emails=False)
    assert len(result["papers"]) >= 1
    assert "<html" in result["html"].lower()
