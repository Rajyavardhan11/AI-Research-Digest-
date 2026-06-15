from __future__ import annotations

import logging
from datetime import UTC, datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from config import settings
from database.db import SessionLocal
from database.models import DigestRun
from digest_email.sender import (
    get_active_subscribers,
    send_digest,
    send_test_email,
    sync_subscribers_to_db,
)
from pipeline.compiler import compile_digest
from pipeline.filter import filter_top_papers
from pipeline.summarizer import summarize_all
from scrapers import scrape_arxiv, scrape_devto, scrape_hackernews

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()
WEEKDAY_MAP = {
    "monday": "mon",
    "tuesday": "tue",
    "wednesday": "wed",
    "thursday": "thu",
    "friday": "fri",
    "saturday": "sat",
    "sunday": "sun",
}


def _deduplicate(papers: list[dict]) -> list[dict]:
    seen: set[str] = set()
    unique: list[dict] = []
    for paper in papers:
        url = paper.get("url", "")
        if not url or url in seen:
            continue
        seen.add(url)
        unique.append(paper)
    return unique


def run_digest_pipeline(session: Session | None = None, send_emails: bool = True) -> dict:
    owns_session = session is None
    db = session or SessionLocal()
    run = DigestRun(topic=settings.digest_topic, status="running")
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        sync_subscribers_to_db(db)

        scraped = (
            scrape_arxiv(settings.digest_topic, max_results=20)
            + scrape_hackernews(settings.digest_topic, max_results=10)
            + scrape_devto(settings.digest_topic, max_results=10)
        )
        unique_papers = _deduplicate(scraped)
        selected = filter_top_papers(unique_papers, settings.digest_topic, settings.max_papers)
        summarized = summarize_all(selected)
        now = datetime.now(UTC)
        html = compile_digest(summarized, now)
        subscribers = get_active_subscribers()
        subject = f"🤖 AI Research Digest — Week of {now:%B %d, %Y}"
        email_result = (
            send_digest(html, subject, subscribers) if send_emails else {"sent": 0, "failed": 0, "errors": []}
        )

        run.papers_scraped = len(unique_papers)
        run.papers_selected = len(summarized)
        run.papers_sent = [paper.get("title", "Untitled") for paper in summarized]
        run.subscribers_count = len(subscribers)
        run.status = "success"
        db.commit()

        logger.info(
            "Sent digest: %s papers to %s subscribers",
            len(summarized),
            len(subscribers),
        )
        return {
            "papers": summarized,
            "html": html,
            "email_result": email_result,
            "run_id": run.id,
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("Digest pipeline failed")
        run.status = "failed"
        run.error_message = str(exc)
        db.commit()
        send_test_email(
            f"<p>Digest pipeline failed at {datetime.now(UTC).isoformat()}.</p><pre>{exc}</pre>",
            settings.admin_email,
        )
        raise
    finally:
        if owns_session:
            db.close()


def start_scheduler() -> None:
    if scheduler.running:
        return

    day_of_week = WEEKDAY_MAP.get(settings.schedule_day, settings.schedule_day)
    trigger = CronTrigger(day_of_week=day_of_week, hour=settings.schedule_hour, minute=0)
    scheduler.add_job(run_digest_pipeline, trigger=trigger, id="weekly-digest", replace_existing=True)
    scheduler.start()
    job = scheduler.get_job("weekly-digest")
    logger.info("Scheduler started. Next run: %s", job.next_run_time if job else "unknown")
