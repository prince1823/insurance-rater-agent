"""End-to-end: PDF bytes -> extracted facts -> deterministic rate -> output contract."""
from __future__ import annotations

from typing import Optional

from .extraction.schema import PolicyFacts
from .resolver import registry
from .resolver.common import ResolvedInput


def _fact(fv, label: str) -> dict:
    return {
        "field": label,
        "value": fv.value if fv.is_present() else None,
        "page": fv.evidence.page,
        "snippet": fv.evidence.snippet,
        "confidence": round(fv.evidence.confidence, 3),
    }


def _facts_view(f: PolicyFacts, inp: ResolvedInput) -> dict:
    return {
        "insurer": _fact(f.insurer, "insurer"),
        "previous_insurer": _fact(f.previous_insurer, "previous insurer"),
        "business_type": {"field": "business type", "value": inp.business_type,
                          "derivation": "same insurer current & previous => renewal; "
                                        "different named previous => rollover"},
        "policy_type": {"field": "policy type", "value": inp.policy_type},
        "make": _fact(f.make, "make"),
        "model": _fact(f.model, "model"),
        "fuel": {**_fact(f.fuel, "fuel"), "normalised": inp.fuel},
        "cc": _fact(f.cc, "engine cc"),
        "rto_code": {**_fact(f.rto_code, "RTO code"), "normalised": inp.rto_code},
        "rto_location": _fact(f.rto_location, "RTO location"),
        "manufacture_year": _fact(f.manufacture_year, "manufacture year"),
        "registration_year": _fact(f.registration_year, "registration year"),
        "vehicle_age_years": {"field": "vehicle age (years)", "value": inp.vehicle_age_years},
        "ncb_percent": _fact(f.ncb_percent, "NCB %"),
        "zero_depreciation": _fact(f.zero_depreciation, "zero depreciation cover"),
        "premium_breakup": {
            "od_premium": _fact(f.premium.od_premium, "OD premium"),
            "tp_premium": _fact(f.premium.tp_premium, "TP premium"),
            "net_premium": _fact(f.premium.net_premium, "net premium"),
            "total_premium": _fact(f.premium.total_premium, "total premium (incl GST)"),
        },
    }


def _commission_amounts(rr, inp: ResolvedInput) -> dict:
    out = {}
    if rr.od.applicable and rr.od.percent is not None and inp.od_premium:
        out["od"] = round(inp.od_premium * rr.od.percent / 100, 2)
    if rr.tp.applicable and rr.tp.percent is not None:
        basis = inp.net_premium if "net" in rr.tp.basis.lower() else inp.tp_premium
        if basis:
            out["tp"] = round(basis * rr.tp.percent / 100, 2)
    return out


def build_output(facts: PolicyFacts) -> dict:
    rr, inp = registry.resolve(facts)
    dedup: list[dict] = []
    seen = set()
    for c in rr.citations:
        k = (c.source, c.locator)
        if k not in seen:
            seen.add(k)
            dedup.append(c.as_dict())

    return {
        "status": rr.status,
        "insurer": rr.insurer,
        "grid_file": rr.grid_file,
        "policy_type": inp.policy_type,
        "business_type": inp.business_type,
        "facts": _facts_view(facts, inp),
        "rates": {"od": rr.od.as_dict(), "tp": rr.tp.as_dict()},
        "commission_amounts_inr": _commission_amounts(rr, inp),
        "confidence": {"level": rr.confidence_level, "reason": rr.confidence_reason},
        "reason": rr.reason,
        "clarifying_question": rr.clarifying_question,
        "candidates": rr.candidates,
        "citations": dedup,
        "trace": [s.as_dict() for s in rr.trace],
        "extraction": {"model": facts.model_used, "notes": facts.notes, "source_file": facts.source_file},
    }
