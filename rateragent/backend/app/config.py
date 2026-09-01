"""Runtime configuration, read from environment (12-factor)."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR.parent
REPO_DIR = BACKEND_DIR.parent
RULEPACK_DIR = APP_DIR / "rulepacks"


def _find_data_dir() -> Path:
    for cand in (REPO_DIR / "data", BACKEND_DIR / "data", Path("/data"), Path("data")):
        if cand.is_dir():
            return cand
    return REPO_DIR / "data"


DATA_DIR = _find_data_dir()


class Settings:
    # --- LLM extraction (OpenRouter, OpenAI-compatible) ---
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    openrouter_base_url: str = os.getenv(
        "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
    )
    # Configurable per the plan; default gpt-4o-mini as requested.
    openrouter_model: str = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    extraction_dpi: int = int(os.getenv("EXTRACTION_DPI", "150"))
    max_pages: int = int(os.getenv("EXTRACTION_MAX_PAGES", "8"))

    # --- Storage ---
    # Postgres (Supabase) connection string. If unset, falls back to local sqlite
    # so the app and tests run with zero external dependencies.
    database_url: str = os.getenv("DATABASE_URL", "").strip()
    sqlite_path: str = os.getenv("SQLITE_PATH", str(BACKEND_DIR / "local.db"))

    # Supabase Storage (object store for uploaded PDFs).
    supabase_url: str = os.getenv("SUPABASE_URL", "").strip()
    supabase_service_key: str = os.getenv("SUPABASE_SERVICE_KEY", "").strip()
    supabase_bucket: str = os.getenv("SUPABASE_BUCKET", "policy-pdfs")
    # Local blob dir used when Supabase Storage is not configured.
    local_blob_dir: str = os.getenv("LOCAL_BLOB_DIR", str(BACKEND_DIR / "blobs"))

    cors_origins: list[str] = [
        o.strip()
        for o in os.getenv("CORS_ORIGINS", "*").split(",")
        if o.strip()
    ]

    @property
    def effective_database_url(self) -> str:
        if self.database_url:
            # SQLAlchemy + psycopg3 dialect
            url = self.database_url
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+psycopg://", 1)
            elif url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+psycopg://", 1)
            return url
        return f"sqlite:///{self.sqlite_path}"

    @property
    def use_supabase_storage(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_key)

    @property
    def llm_configured(self) -> bool:
        return bool(self.openrouter_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
