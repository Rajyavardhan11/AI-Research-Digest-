from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import digest_email.sender as sender_module
import scheduler as scheduler_module
from database.db import get_db
from database.models import Base
from main import app


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def mock_subscribers_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    subscribers_path = tmp_path / "subscribers.json"
    subscribers_path.write_text(
        json.dumps([{"email": "test@example.com", "name": "Test User", "active": True}]),
        encoding="utf-8",
    )
    monkeypatch.setattr(sender_module, "SUBSCRIBERS_PATH", subscribers_path)
    yield subscribers_path


@pytest.fixture(autouse=True)
def mock_ollama(monkeypatch: pytest.MonkeyPatch):
    filter_json = json.dumps({"selected_indices": [0, 1], "reasoning": "Top picks"})
    summary_json = json.dumps(
        {
            "summary": "A concise technical summary.",
            "key_insight": "Strong practical signal",
            "difficulty": "intermediate",
        }
    )

    def fake_generate(prompt: str) -> str:
        if "selected_indices" in prompt:
            return filter_json
        return summary_json

    monkeypatch.setattr("pipeline.filter._ollama_generate", fake_generate)
    monkeypatch.setattr("pipeline.summarizer._ollama_generate", fake_generate)


@pytest.fixture(autouse=True)
def mock_email(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(sender_module, "_send_email", lambda html_content, subject, to_email: None)


@pytest.fixture(autouse=True)
def mock_scrapers(monkeypatch: pytest.MonkeyPatch):
    papers = [
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
            "authors": ["B. Researcher"],
            "abstract": "Paper two abstract",
            "url": "https://example.com/paper-2",
            "published": "2026-01-02",
            "source": "devto",
        },
    ]
    monkeypatch.setattr(scheduler_module, "scrape_arxiv", lambda topic, max_results=20: papers[:1])
    monkeypatch.setattr(scheduler_module, "scrape_hackernews", lambda topic, max_results=10: [])
    monkeypatch.setattr(scheduler_module, "scrape_devto", lambda topic, max_results=10: papers[1:])
