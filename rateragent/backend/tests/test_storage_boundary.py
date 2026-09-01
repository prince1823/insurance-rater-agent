"""Storage boundary: a persisted run reloads identically from a brand-new
engine/session (simulating a container restart / redeploy)."""
import importlib
import json
from pathlib import Path

import pytest

FIX = Path(__file__).parent / "fixtures"


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "runs.db"))
    monkeypatch.setenv("LOCAL_BLOB_DIR", str(tmp_path / "blobs"))
    from app import config
    config.get_settings.cache_clear()
    import app.storage.db as db
    importlib.reload(db)
    db.init_db()
    return db


def _make_run(db, output, facts_json):
    run = db.Run(
        filename="pvt-car-satp-go-digit.pdf",
        blob_key="",
        status=output["status"],
        insurer=output["insurer"],
        od_percent="n/a",
        tp_percent="29.5%",
        facts_json=facts_json,
        result_json=output,
    )
    with db.SessionLocal() as s:
        s.add(run)
        s.flush()
        run.blob_key = f"runs/{run.id}.pdf"
        s.commit()
        return run.id


def test_run_persists_and_reloads_across_engine_restart(fresh_db):
    db = fresh_db
    from app.extraction.client import facts_from_payload
    from app.pipeline import build_output

    payload = json.loads((FIX / "pvt-car-satp-go-digit.json").read_text())
    facts = facts_from_payload(payload, "pvt-car-satp-go-digit.pdf", "test")
    output = build_output(facts)
    rid = _make_run(db, output, facts.model_dump())

    # simulate a redeploy: throw away the engine and rebuild from the same URL
    importlib.reload(db)
    with db.SessionLocal() as s:
        reloaded = s.get(db.Run, rid)
        assert reloaded is not None
        assert reloaded.result_json["rates"]["tp"]["percent"] == 29.5
        assert reloaded.result_json["status"] == "resolved"
        assert reloaded.blob_key == f"runs/{rid}.pdf"

    listing = None
    with db.SessionLocal() as s:
        listing = s.query(db.Run).order_by(db.Run.created_at.desc()).all()
    assert any(r.id == rid for r in listing)


def test_blob_roundtrip_local(fresh_db, tmp_path):
    import importlib

    import app.storage.blobs as blobs
    importlib.reload(blobs)
    blobs.put("runs/abc.pdf", b"%PDF-1.4 fake")
    assert blobs.get("runs/abc.pdf") == b"%PDF-1.4 fake"
