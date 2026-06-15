from __future__ import annotations

from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from config import settings

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "digest_email" / "templates"


def compile_digest(papers: list[dict], run_date: datetime) -> str:
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("digest.html")
    formatted_date = run_date.strftime("%B %d, %Y")
    return template.render(
        papers=papers,
        run_date=formatted_date,
        topic=settings.digest_topic,
        total_count=len(papers),
        unsubscribe_url=f"{settings.app_base_url.rstrip('/')}/unsubscribe",
    )
