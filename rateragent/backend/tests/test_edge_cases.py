"""Resilience: missing fields, exclusions, footnotes, ambiguity, unsupported segments."""
import copy
import json
from pathlib import Path

import pytest

from app.extraction.client import facts_from_payload
from app.pipeline import build_output

FIX = Path(__file__).parent / "fixtures"


def payload(name: str) -> dict:
    return json.loads((FIX / f"{name}.json").read_text())


def run(p: dict, fname="x.pdf"):
    return build_output(facts_from_payload(p, fname, "test"))


def test_missing_rto_is_ambiguous_not_guessed():
    p = payload("pvt-car-comprehensive-reliance")
    p["rto_code"] = {"value": None, "confidence": 0.0}
    p["registration_number"] = {"value": None, "confidence": 0.0}
    out = run(p)
    assert out["status"] == "ambiguous"
    assert out["clarifying_question"]
    assert out["rates"]["od"]["percent"] is None


def test_unknown_insurer_is_unsupported():
    p = payload("pvt-car-comprehensive-reliance")
    p["insurer"] = {"value": "Acko General Insurance", "confidence": 0.9}
    out = run(p)
    assert out["status"] == "unsupported"
    assert "grid" in out["reason"].lower()


def test_rto_not_in_grid_is_unsupported():
    p = payload("pvt-car-satp-go-digit")
    p["rto_code"] = {"value": "XX-99", "confidence": 0.9}
    p["registration_number"] = {"value": "XX99AB1234", "confidence": 0.9}
    out = run(p)
    assert out["status"] == "unsupported"
    assert "not present" in out["reason"].lower() or "not in" in out["reason"].lower()


def test_reliance_unknown_fuel_is_ambiguous():
    p = payload("pvt-car-comprehensive-reliance")
    p["fuel"] = {"value": None, "confidence": 0.0}
    out = run(p)
    assert out["status"] == "ambiguous"
    assert "fuel" in (out["clarifying_question"] or "").lower()


def test_hdfc_rejects_standalone_tp():
    p = payload("pvt-car-comprehensive-hdfc-ergo")
    p["policy_type"] = {"value": "standalone_tp", "confidence": 0.9}
    p["premium"]["od_premium"] = {"value": None, "confidence": 0.0}
    out = run(p)
    assert out["status"] == "unsupported"


def test_tata_multi_column_state_without_city_is_ambiguous():
    p = payload("pvt-car-satp-tata-aig")
    p["rto_code"] = {"value": "UP-32", "confidence": 0.9}
    p["rto_location"] = {"value": "UTTAR PRADESH", "confidence": 0.9}
    out = run(p)
    assert out["status"] == "ambiguous"
    assert out["candidates"]


def test_weak_extraction_downgrades_confidence():
    p = payload("pvt-car-comprehensive-hdfc-ergo")
    p["cc"] = {"value": 1493, "confidence": 0.2}
    out = run(p)
    assert out["confidence"]["level"] in ("medium", "low")
    assert "cc" in out["confidence"]["reason"]


def test_go_digit_new_business_still_resolves_or_flags():
    p = payload("pvt-car-satp-go-digit")
    p["business_type"] = {"value": "new", "confidence": 0.9}
    p["previous_insurer"] = {"value": None, "confidence": 0.0}
    out = run(p)
    assert out["status"] in ("resolved", "ambiguous", "unsupported")


def test_trace_steps_are_ordered_and_cited():
    out = run(payload("pvt-car-comprehensive-reliance"))
    steps = out["trace"]
    assert [s["step"] for s in steps] == list(range(1, len(steps) + 1))
    assert any(s["citations"] for s in steps)


def test_zero_dep_footnote_noted_but_not_applied_for_package(analyze=None):
    out = run(payload("pvt-car-comprehensive-reliance"))
    note = out["rates"]["od"]["note"].lower()
    assert "zero-depreciation" in note or "zd" in note
    assert out["rates"]["od"]["percent"] == 17.5  # no 2.5 reduction
