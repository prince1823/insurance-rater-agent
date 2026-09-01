"""Blob storage for uploaded policy PDFs.

Uses Supabase Storage when configured (survives redeploys); otherwise falls back
to a local directory for dev/test.
"""
from __future__ import annotations

import os
from pathlib import Path

from ..config import get_settings

_s = get_settings()
_supabase = None


def _client():
    global _supabase
    if _supabase is None:
        from supabase import create_client

        _supabase = create_client(_s.supabase_url, _s.supabase_service_key)
    return _supabase


def put(key: str, data: bytes, content_type: str = "application/pdf") -> str:
    if _s.use_supabase_storage:
        _client().storage.from_(_s.supabase_bucket).upload(
            key, data, {"content-type": content_type, "upsert": "true"}
        )
        return key
    path = Path(_s.local_blob_dir) / key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return key


def get(key: str) -> bytes:
    if _s.use_supabase_storage:
        return _client().storage.from_(_s.supabase_bucket).download(key)
    return (Path(_s.local_blob_dir) / key).read_bytes()


def public_or_signed_url(key: str) -> str | None:
    if _s.use_supabase_storage:
        try:
            res = _client().storage.from_(_s.supabase_bucket).create_signed_url(key, 3600)
            return res.get("signedURL") or res.get("signed_url")
        except Exception:
            return None
    return None
