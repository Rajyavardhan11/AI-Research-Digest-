from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from database.db import get_db
from database.models import DigestRun, Subscriber
from digest_email.sender import add_subscriber, remove_subscriber
from scheduler import run_digest_pipeline, scheduler

router = APIRouter()


class SubscriberCreate(BaseModel):
    email: EmailStr
    name: str


@router.get("/", response_class=HTMLResponse)
def admin_dashboard(db: Session = Depends(get_db)) -> str:
    runs = db.query(DigestRun).order_by(DigestRun.created_at.desc()).limit(10).all()
    subscribers_count = db.query(Subscriber).filter(Subscriber.active.is_(True)).count()
    next_run = scheduler.get_job("weekly-digest").next_run_time if scheduler.get_job("weekly-digest") else None

    rows = "".join(
        f"<tr><td>{run.run_date:%Y-%m-%d %H:%M}</td><td>{run.papers_selected}</td><td>{run.subscribers_count}</td><td>{run.status}</td></tr>"
        for run in runs
    )
    next_run_text = next_run.isoformat() if next_run else "Not scheduled"
    return f"""
    <html>
      <body style="font-family:system-ui;padding:32px;background:#f8fafc;color:#0f172a;">
        <div style="max-width:900px;margin:0 auto;">
          <h1>AI Research Digest Admin</h1>
          <p>Next scheduled run: {next_run_text}</p>
          <p>Total subscribers: {subscribers_count}</p>
          <form method="post" action="/api/trigger">
            <button style="padding:12px 18px;border:none;border-radius:10px;background:#0f172a;color:white;cursor:pointer;">Trigger Now</button>
          </form>
          <h2 style="margin-top:32px;">Recent Runs</h2>
          <table style="width:100%;border-collapse:collapse;background:white;">
            <thead><tr><th>Date</th><th>Papers</th><th>Subscribers</th><th>Status</th></tr></thead>
            <tbody>{rows}</tbody>
          </table>
        </div>
      </body>
    </html>
    """


@router.post("/api/trigger")
def trigger_pipeline(db: Session = Depends(get_db)) -> dict:
    result = run_digest_pipeline(session=db, send_emails=True)
    return {"status": "running", "message": "Digest pipeline started", "run_id": result["run_id"]}


@router.get("/api/preview", response_class=HTMLResponse)
def preview_digest(db: Session = Depends(get_db)) -> str:
    result = run_digest_pipeline(session=db, send_emails=False)
    return result["html"]


@router.post("/api/subscribers")
def create_subscriber(payload: SubscriberCreate, db: Session = Depends(get_db)) -> dict:
    return add_subscriber(db, payload.email, payload.name)


@router.delete("/api/subscribers/{email}")
def delete_subscriber(email: str, db: Session = Depends(get_db)) -> dict:
    return remove_subscriber(db, email)


@router.get("/api/history")
def get_history(db: Session = Depends(get_db)) -> list[dict]:
    runs = db.query(DigestRun).order_by(DigestRun.created_at.desc()).all()
    return [
        {
            "id": run.id,
            "run_date": run.run_date.isoformat() if isinstance(run.run_date, datetime) else str(run.run_date),
            "topic": run.topic,
            "papers_scraped": run.papers_scraped,
            "papers_selected": run.papers_selected,
            "papers_sent": run.papers_sent,
            "subscribers_count": run.subscribers_count,
            "status": run.status,
            "error_message": run.error_message,
        }
        for run in runs
    ]
