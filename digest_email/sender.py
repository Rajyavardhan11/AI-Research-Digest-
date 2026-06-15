from __future__ import annotations

import json
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from config import settings
from database.models import Subscriber

logger = logging.getLogger(__name__)

SUBSCRIBERS_PATH = Path(__file__).resolve().parent.parent / settings.subscribers_file


def load_subscribers() -> list[dict]:
    if not SUBSCRIBERS_PATH.exists():
        return []
    return json.loads(SUBSCRIBERS_PATH.read_text(encoding="utf-8"))


def save_subscribers(subscribers: list[dict]) -> None:
    SUBSCRIBERS_PATH.write_text(json.dumps(subscribers, indent=2), encoding="utf-8")


def get_active_subscribers() -> list[dict]:
    return [subscriber for subscriber in load_subscribers() if subscriber.get("active", True)]


def sync_subscribers_to_db(db: Session) -> None:
    for subscriber in load_subscribers():
        record = db.query(Subscriber).filter(Subscriber.email == subscriber["email"]).one_or_none()
        if record is None:
            db.add(
                Subscriber(
                    email=subscriber["email"],
                    name=subscriber.get("name", subscriber["email"]),
                    active=subscriber.get("active", True),
                )
            )
        else:
            record.name = subscriber.get("name", record.name)
            record.active = subscriber.get("active", True)
    db.commit()


def add_subscriber(db: Session, email: str, name: str) -> dict:
    subscribers = load_subscribers()
    existing = next((item for item in subscribers if item["email"] == email), None)
    if existing:
        existing["name"] = name
        existing["active"] = True
    else:
        subscribers.append({"email": email, "name": name, "active": True})
    save_subscribers(subscribers)

    record = db.query(Subscriber).filter(Subscriber.email == email).one_or_none()
    if record is None:
        db.add(Subscriber(email=email, name=name, active=True))
    else:
        record.name = name
        record.active = True
    db.commit()
    return {"success": True}


def remove_subscriber(db: Session, email: str) -> dict:
    subscribers = load_subscribers()
    for subscriber in subscribers:
        if subscriber["email"] == email:
            subscriber["active"] = False
    save_subscribers(subscribers)

    record = db.query(Subscriber).filter(Subscriber.email == email).one_or_none()
    if record is not None:
        record.active = False
        db.commit()
    return {"unsubscribed": True}


def _send_email(html_content: str, subject: str, to_email: str) -> None:
    if not settings.resend_api_key:
        raise RuntimeError("RESEND_API_KEY is not configured")

    from resend import Emails

    Emails.api_key = settings.resend_api_key
    Emails.send(
        {
            "from": settings.from_email,
            "to": [to_email],
            "subject": subject,
            "html": html_content,
        }
    )


def send_digest(html_content: str, subject: str, subscribers: list[dict]) -> dict:
    sent = 0
    failed = 0
    errors: list[str] = []

    for subscriber in subscribers:
        email = subscriber.get("email", "")
        if not email:
            continue
        try:
            _send_email(html_content, subject, email)
            sent += 1
        except Exception as exc:  # noqa: BLE001
            failed += 1
            error = f"{email}: {exc}"
            logger.error("Failed to send digest to %s: %s", email, exc)
            errors.append(error)

    return {"sent": sent, "failed": failed, "errors": errors}


def send_test_email(html_content: str, to_email: str) -> bool:
    try:
        _send_email(html_content, "🤖 AI Research Digest Preview", to_email)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to send test email: %s", exc)
        return False
