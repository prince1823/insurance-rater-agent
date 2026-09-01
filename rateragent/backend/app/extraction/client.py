"""Policy-fact extraction from a (usually scanned) motor-policy PDF.

The LLM is used *only* here: PDF pages are rendered to images and sent to an
OpenRouter vision model with a strict JSON contract. Every field must come back
with a page number, a verbatim snippet and a confidence. All downstream rate
logic is deterministic Python.
"""
from __future__ import annotations

import base64
import json
import re
from typing import Any

import fitz  # PyMuPDF
import httpx

from ..config import get_settings
from .schema import Evidence, FactValue, PolicyFacts, PremiumBreakup

EXTRACTION_INSTRUCTIONS = """You are an insurance document analyst. Read this Indian motor
insurance policy (Certificate of Insurance cum Policy Schedule) and extract ONLY the facts
that affect broker commission. Return a single JSON object, no prose.

For every field return: {"value": <value or null>, "page": <1-indexed page or null>,
"snippet": "<verbatim text from the document>", "confidence": <0..1>}.

Rules:
- Use null when the document does not state a value. Do NOT guess RTO codes, premiums or CC.
- fuel: one of petrol|diesel|cng|lpg|electric|hybrid. If not printed but the make/model makes it
  near-certain (e.g. "Bolero Neo" is diesel), give your best value with confidence <= 0.6 and say
  so in the snippet ("fuel not printed; inferred from model").
- policy_type: "comprehensive" if it has both Own Damage and Third-Party sections/premium;
  "standalone_tp" for Liability Only / SATP / Act-only; "standalone_od" for SAOD.
- business_type: "renewal" if previous insurer == current insurer; "rollover" if a different
  previous insurer is named; "new" if explicitly new/no previous policy; else null.
- registration_number: the full vehicle registration mark exactly as printed, e.g. "UP78FZ1372",
  "DL 9C AB 2893", "HR-26-FB-8239". Read it digit by digit; do not normalise.
- rto_code: derive it from registration_number = its first two letters + the immediately following
  1-2 digits (and a trailing letter if present), e.g. UP78FZ1372 -> "UP-78", DL 9C AB 2893 ->
  "DL-9C", HR-26-FB-8239 -> "HR-26". NEVER infer the code from the RTO office city name.
- rto_location: the city/state text printed next to "RTO" / "RTO Location".
- cc: integer engine cubic capacity. ncb_percent: the No Claim Bonus % applied to THIS policy's
  OD premium (if the schedule shows two different NCB figures, use the one in the premium
  calculation and note the discrepancy in the snippet).
- premium: od_premium = net Own Damage premium (after NCB, incl OD add-ons); tp_premium = basic
  third-party / liability premium; net_premium = total net premium before GST; total_premium =
  amount including GST.
- zero_depreciation: true if the policy carries Zero Depreciation / Nil Depreciation cover.

JSON shape:
{
 "insurer": {...}, "previous_insurer": {...}, "business_type": {...}, "policy_type": {...},
 "make": {...}, "model": {...}, "fuel": {...}, "cc": {...}, "registration_number": {...},
 "rto_code": {...}, "rto_location": {...}, "manufacture_year": {...}, "registration_year": {...},
 "body_type": {...}, "seating_capacity": {...}, "ncb_percent": {...}, "zero_depreciation": {...},
 "premium": {"od_premium": {...}, "tp_premium": {...}, "net_premium": {...}, "total_premium": {...}}
}
"""

_SIMPLE_FIELDS = [
    "insurer", "previous_insurer", "business_type", "policy_type", "make", "model", "fuel",
    "cc", "registration_number", "rto_code", "rto_location", "manufacture_year",
    "registration_year", "vehicle_age_years", "body_type", "seating_capacity",
    "ncb_percent", "zero_depreciation",
]


def render_pages(pdf_bytes: bytes, dpi: int, max_pages: int) -> list[str]:
    """Return data: URIs for the first ``max_pages`` pages."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    uris = []
    for i, page in enumerate(doc):
        if i >= max_pages:
            break
        pix = page.get_pixmap(dpi=dpi)
        uris.append("data:image/png;base64," + base64.b64encode(pix.tobytes("png")).decode())
    doc.close()
    return uris


def _coerce(node: Any) -> FactValue:
    if not isinstance(node, dict):
        return FactValue(value=node, evidence=Evidence())
    return FactValue(
        value=node.get("value"),
        evidence=Evidence(
            page=node.get("page"),
            snippet=str(node.get("snippet") or "")[:400],
            confidence=float(node.get("confidence") or 0.0),
        ),
    )


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?|```$", "", text.strip()).strip()
    m = re.search(r"\{.*\}", text, re.DOTALL)
    return json.loads(m.group(0) if m else text)


def facts_from_payload(payload: dict, source_file: str, model_used: str) -> PolicyFacts:
    facts = PolicyFacts(source_file=source_file, model_used=model_used)
    for f in _SIMPLE_FIELDS:
        if f in payload:
            setattr(facts, f, _coerce(payload[f]))
    prem = payload.get("premium") or {}
    facts.premium = PremiumBreakup(
        od_premium=_coerce(prem.get("od_premium")),
        tp_premium=_coerce(prem.get("tp_premium")),
        net_premium=_coerce(prem.get("net_premium")),
        total_premium=_coerce(prem.get("total_premium")),
    )
    return facts


async def extract_facts(pdf_bytes: bytes, filename: str) -> PolicyFacts:
    s = get_settings()
    if not s.llm_configured:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set. Set it, or POST to /analyze with "
            "?fixture=<name> during development."
        )
    images = render_pages(pdf_bytes, s.extraction_dpi, s.max_pages)
    content: list[dict] = [{"type": "text", "text": EXTRACTION_INSTRUCTIONS}]
    for uri in images:
        content.append({"type": "image_url", "image_url": {"url": uri}})

    async with httpx.AsyncClient(timeout=180) as client:
        resp = await client.post(
            f"{s.openrouter_base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {s.openrouter_api_key}",
                "HTTP-Referer": "https://github.com/vaatun/insurance-rater-agent",
                "X-Title": "Insurance Rater Agent",
            },
            json={
                "model": s.openrouter_model,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [{"role": "user", "content": content}],
            },
        )
        resp.raise_for_status()
        data = resp.json()
    text = data["choices"][0]["message"]["content"]
    payload = _parse_json(text)
    facts = facts_from_payload(payload, filename, s.openrouter_model)
    facts.notes.append(f"extracted with {s.openrouter_model} over {len(images)} page image(s)")
    return facts
