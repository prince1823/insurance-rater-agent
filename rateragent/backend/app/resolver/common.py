"""Shared plumbing for the deterministic resolvers."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Optional

from rapidfuzz import fuzz

from ..config import RULEPACK_DIR
from ..extraction.schema import PolicyFacts
from . import base

DRIVER_FACT_CONF_FLOOR = 0.55  # below this a driver fact is "weak"


@lru_cache
def load_rulepack(name: str) -> dict:
    path = Path(RULEPACK_DIR) / f"{name}.json"
    return json.loads(path.read_text())


@dataclass
class ResolvedInput:
    """Flat, resolver-friendly view of the extracted facts."""

    insurer: Optional[str] = None
    previous_insurer: Optional[str] = None
    business_type: str = "unknown"
    policy_type: str = "unknown"
    make: Optional[str] = None
    model: Optional[str] = None
    fuel: str = "unknown"
    cc: Optional[int] = None
    rto_code: Optional[str] = None
    rto_location: Optional[str] = None
    manufacture_year: Optional[int] = None
    vehicle_age_years: Optional[int] = None
    ncb_percent: Optional[float] = None
    zero_depreciation: bool = False
    od_premium: Optional[float] = None
    tp_premium: Optional[float] = None
    net_premium: Optional[float] = None
    facts: Optional[PolicyFacts] = None
    weak_fields: list[str] = field(default_factory=list)

    def policy_cite(self, field_name: str, fallback_page: int | None = None) -> base.Citation:
        src = (self.facts.source_file if self.facts else "policy.pdf")
        page = fallback_page
        snippet = ""
        if self.facts is not None:
            fv = getattr(self.facts, field_name, None)
            if fv is not None and getattr(fv, "evidence", None) is not None:
                page = fv.evidence.page or page
                snippet = fv.evidence.snippet
        loc = f"page {page}" if page else "policy schedule"
        return base.Citation(source=src, locator=loc, kind="policy",
                             value=getattr(getattr(self.facts, field_name, None), "value", None),
                             note=snippet[:160])


def require(inp: ResolvedInput, field_name: str, label: str) -> object:
    val = getattr(inp, field_name, None)
    if val in (None, "", "unknown"):
        raise base.Unresolvable(
            "ambiguous",
            f"Required policy fact '{label}' could not be extracted from the document.",
            clarifying_question=f"What is the {label} for this policy?",
        )
    return val


def best_match(query: str, choices: list[str], threshold: float = 82.0) -> tuple[Optional[str], float, list[tuple[str, float]]]:
    """Token-set fuzzy match. Returns (best or None, score, ranked candidates)."""
    if not query:
        return None, 0.0, []
    scored = sorted(
        ((c, fuzz.token_set_ratio(query.lower(), c.lower())) for c in choices),
        key=lambda t: t[1],
        reverse=True,
    )
    if scored and scored[0][1] >= threshold:
        return scored[0][0], scored[0][1], scored[:5]
    return None, (scored[0][1] if scored else 0.0), scored[:5]


def confidence_from(inp: ResolvedInput, extra_reason: str = "") -> tuple[str, str]:
    reasons = []
    level = "high"
    if inp.weak_fields:
        level = "medium"
        reasons.append(f"low-confidence extraction for: {', '.join(inp.weak_fields)}")
    if inp.fuel == "unknown":
        level = "medium"
        reasons.append("fuel type not stated on the schedule")
    elif inp.facts is not None and inp.facts.fuel.is_present() and inp.facts.fuel.evidence.confidence < 0.7:
        level = "medium" if level == "high" else level
        reasons.append("fuel type not printed on the schedule; inferred from make/model")
    if extra_reason:
        if level == "high":
            level = "medium"
        reasons.append(extra_reason)
    if not reasons:
        reasons.append("all driver facts extracted with high confidence and matched grid keys exactly")
    return level, "; ".join(reasons)
