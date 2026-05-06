from __future__ import annotations

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import yaml
import os


class Settings(BaseSettings):
    # ─── LLM ─────────────────────────────────────────────────────────
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    default_llm: str = "openai"   # openai | anthropic
    openai_model: str = "gpt-4o"
    anthropic_model: str = "claude-3-7-sonnet-20250219"
    llm_max_tokens: int = 4096
    llm_temperature: float = 0.7

    # ─── Image ───────────────────────────────────────────────────────
    dalle_model: str = "dall-e-3"
    image_storage_path: str = "storage/images"

    # ─── Tistory OAuth 2.0 ───────────────────────────────────────────
    tistory_app_id: str = ""
    tistory_secret_key: str = ""
    tistory_access_token: str = ""
    tistory_blog_name: str = ""
    tistory_callback_url: str = "http://localhost:8000/callback"
    tistory_default_category_id: int = 1
    tistory_visibility: int = 3      # 0: 비공개, 3: 공개

    # ─── Database ────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://techblog:password@localhost:5432/techblog"

    # ─── Redis ───────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ─── Google APIs ─────────────────────────────────────────────────
    google_analytics_property_id: str = ""
    google_search_console_credentials: str = ""

    # ─── Notifications ───────────────────────────────────────────────
    slack_webhook_url: Optional[str] = None

    # ─── Blog Behavior ───────────────────────────────────────────────
    posts_per_day: int = 2
    min_word_count: int = 1500
    target_word_count: int = 2500
    max_retry_count: int = 3
    topics_per_run: int = 5
    human_review_max_retries: int = 3

    # ─── Monitoring ──────────────────────────────────────────────────
    prometheus_port: int = 8001
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "extra": "allow"}


def load_yaml_settings(path: str = "config/settings.yaml") -> dict:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


settings = Settings()
yaml_config = load_yaml_settings()
