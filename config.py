from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.2")
    resend_api_key: str = os.getenv("RESEND_API_KEY", "")
    from_email: str = os.getenv("FROM_EMAIL", "digest@yourdomain.com")
    digest_topic: str = os.getenv(
        "DIGEST_TOPIC", "artificial intelligence and machine learning"
    )
    max_papers: int = int(os.getenv("MAX_PAPERS", "5"))
    schedule_day: str = os.getenv("SCHEDULE_DAY", "monday").lower()
    schedule_hour: int = int(os.getenv("SCHEDULE_HOUR", "9"))
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///digest.db")
    admin_email: str = os.getenv("ADMIN_EMAIL", os.getenv("FROM_EMAIL", "digest@yourdomain.com"))
    app_base_url: str = os.getenv("APP_BASE_URL", "https://yourapp.com")
    subscribers_file: str = os.getenv("SUBSCRIBERS_FILE", "subscribers.json")


settings = Settings()
