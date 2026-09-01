"""Persistence for analysis runs.

A run row holds the uploaded PDF's blob key, the extracted facts, and the full
structured output (status, rates, citations, trace). Nothing analysis-related is
kept on the container's local disk, so history survives refreshes, restarts and
redeploys as long as ``DATABASE_URL`` points at a managed Postgres (Supabase).
When ``DATABASE_URL`` is unset the app uses a local SQLite file so it runs with
zero external services (used by tests and local dev).
"""
from __future__ import annotations

import datetime as _dt
import uuid

from sqlalchemy import JSON, DateTime, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from ..config import get_settings

_settings = get_settings()
_engine = create_engine(
    _settings.effective_database_url,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if _settings.effective_database_url.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[_dt.datetime] = mapped_column(DateTime, default=lambda: _dt.datetime.now(_dt.timezone.utc))
    filename: Mapped[str] = mapped_column(String(400))
    blob_key: Mapped[str] = mapped_column(String(400))
    status: Mapped[str] = mapped_column(String(20))
    insurer: Mapped[str] = mapped_column(String(120), default="")
    model_used: Mapped[str] = mapped_column(String(120), default="")
    od_percent: Mapped[str] = mapped_column(String(20), default="")
    tp_percent: Mapped[str] = mapped_column(String(20), default="")
    facts_json: Mapped[dict] = mapped_column(JSON)
    result_json: Mapped[dict] = mapped_column(JSON)
    error: Mapped[str] = mapped_column(Text, default="")

    def summary(self) -> dict:
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "filename": self.filename,
            "status": self.status,
            "insurer": self.insurer,
            "od_percent": self.od_percent,
            "tp_percent": self.tp_percent,
            "model_used": self.model_used,
        }

    def detail(self) -> dict:
        return {**self.summary(), "blob_key": self.blob_key, "result": self.result_json, "error": self.error}


def init_db() -> None:
    Base.metadata.create_all(_engine)
