"""FastAPI surface for the Insurance Rater Agent."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from .config import BACKEND_DIR, get_settings
from .extraction.client import extract_facts, facts_from_payload
from .pipeline import build_output
from .storage import blobs
from .storage.db import Run, SessionLocal, init_db

settings = get_settings()
app = FastAPI(title="Insurance Rater Agent", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FIXTURE_DIR = BACKEND_DIR / "tests" / "fixtures"


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "llm_configured": settings.llm_configured,
        "model": settings.openrouter_model,
        "storage": "supabase" if settings.use_supabase_storage else "local",
        "database": "postgres" if settings.database_url else "sqlite",
    }


@app.get("/")
def root() -> dict:
    return {"service": "insurance-rater-agent", "docs": "/docs", "endpoints": ["/analyze", "/runs", "/health"]}


@app.post("/analyze")
async def analyze(
    file: UploadFile | None = File(None),
    fixture: str | None = Query(None, description="dev only: use a bundled extraction fixture"),
) -> dict:
    if fixture:
        fp = FIXTURE_DIR / f"{fixture}.json"
        if not fp.exists():
            raise HTTPException(404, f"fixture '{fixture}' not found")
        payload = json.loads(fp.read_text())
        facts = facts_from_payload(payload, f"{fixture}.pdf", "fixture")
        pdf_bytes = _sample_pdf_bytes(fixture)
        filename = f"{fixture}.pdf"
    else:
        if file is None:
            raise HTTPException(400, "upload a PDF file or pass ?fixture=<name>")
        pdf_bytes = await file.read()
        filename = file.filename or "policy.pdf"
        if not pdf_bytes:
            raise HTTPException(400, "empty file")
        try:
            facts = await extract_facts(pdf_bytes, filename)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(502, f"extraction failed: {e}") from e

    output = build_output(facts)

    run = Run(
        filename=filename,
        status=output["status"],
        insurer=output.get("insurer") or "",
        model_used=facts.model_used,
        od_percent=_fmt(output["rates"]["od"]),
        tp_percent=_fmt(output["rates"]["tp"]),
        facts_json=facts.model_dump(),
        result_json=output,
        blob_key="",
    )
    with SessionLocal() as db:
        db.add(run)
        db.flush()
        run.blob_key = f"runs/{run.id}.pdf"
        if pdf_bytes:
            try:
                blobs.put(run.blob_key, pdf_bytes)
            except Exception as e:  # noqa: BLE001
                run.error = f"blob upload failed: {e}"
        db.commit()
        rid = run.id
        detail = run.detail()

    detail["result"]["run_id"] = rid
    return detail["result"] | {"run_id": rid, "created_at": detail["created_at"]}


@app.get("/runs")
def list_runs(limit: int = Query(100, le=500)) -> dict:
    with SessionLocal() as db:
        rows = db.query(Run).order_by(Run.created_at.desc()).limit(limit).all()
        return {"runs": [r.summary() for r in rows]}


@app.get("/runs/{run_id}")
def get_run(run_id: str) -> dict:
    with SessionLocal() as db:
        run = db.get(Run, run_id)
        if not run:
            raise HTTPException(404, "run not found")
        return run.detail()


@app.get("/runs/{run_id}/pdf")
def get_run_pdf(run_id: str):
    with SessionLocal() as db:
        run = db.get(Run, run_id)
        if not run or not run.blob_key:
            raise HTTPException(404, "pdf not found")
        key = run.blob_key
    try:
        data = blobs.get(key)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(404, f"pdf unavailable: {e}") from e
    return Response(content=data, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{run_id}.pdf"'})


def _fmt(rate: dict) -> str:
    if not rate.get("applicable"):
        return "n/a"
    return f"{rate['percent']}%" if rate.get("percent") is not None else "-"


def _sample_pdf_bytes(fixture: str) -> bytes:
    from .config import DATA_DIR

    cand = DATA_DIR / "sample-policies" / f"{fixture}.pdf"
    return cand.read_bytes() if cand.exists() else b""
