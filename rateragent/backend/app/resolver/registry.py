"""Insurer detection + dispatch to the right deterministic resolver."""
from __future__ import annotations

import datetime as _dt

from rapidfuzz import fuzz

from ..extraction import normalize as N
from ..extraction.schema import PolicyFacts
from . import base, godigit, hdfc_ergo, reliance, tataaig
from .common import DRIVER_FACT_CONF_FLOOR, ResolvedInput, load_rulepack

_RESOLVERS = {
    "reliance": reliance.resolve,
    "godigit": godigit.resolve,
    "tataaig": tataaig.resolve,
    "hdfc_ergo": hdfc_ergo.resolve,
}

DRIVER_FIELDS = ["insurer", "rto_code", "fuel", "cc", "policy_type"]


def _year_from_text(val) -> int | None:
    import re

    if val is None:
        return None
    m = re.search(r"(19|20)\d{2}", str(val))
    return int(m.group(0)) if m else None


def detect_insurer(facts: PolicyFacts) -> tuple[str | None, float, str]:
    name = N._canon_insurer(str(facts.insurer.value or "")) or ""
    src = N._canon_insurer(facts.source_file.replace("-", " ").replace("_", " ")) or ""
    best_key, best_score = None, 0.0
    for key in _RESOLVERS:
        pack = load_rulepack(key)
        for alias in pack.get("insurer_aliases", [pack["insurer"].lower()]):
            acanon = N._canon_insurer(alias) or alias
            score = max(
                fuzz.token_set_ratio(acanon, name),
                fuzz.partial_ratio(acanon, src) * 0.7,
            )
            if score > best_score:
                best_key, best_score = key, score
    reason = f"matched insurer '{facts.insurer.value}' -> {best_key} (score {best_score:.0f})"
    return (best_key if best_score >= 80 else None), best_score, reason


def build_input(facts: PolicyFacts) -> ResolvedInput:
    v = lambda fv: fv.value if fv.is_present() else None
    fuel = N.norm_fuel(v(facts.fuel))

    # RTO code: the registration number's prefix is structured and reliable; the
    # LLM's free-form rto_code field is flaky on scans. Prefer the reg-derived
    # value, fall back to the LLM value, and flag a mismatch as a weak fact.
    reg_rto = N.norm_rto_code(v(facts.registration_number))
    llm_rto = N.norm_rto_code(v(facts.rto_code))
    rto_code = reg_rto or llm_rto
    rto_mismatch = bool(reg_rto and llm_rto and reg_rto != llm_rto)
    if rto_mismatch:
        facts.notes.append(
            f"RTO code disagreement: registration number implies {reg_rto}, "
            f"extracted rto_code field said {llm_rto}; using {reg_rto}."
        )

    myear = N.to_int(v(facts.manufacture_year))
    ryear = N.to_int(v(facts.registration_year)) or _year_from_text(v(facts.registration_year)) \
        or _year_from_text(facts.registration_year.evidence.snippet)
    age = N.to_int(v(facts.vehicle_age_years)) or N.vehicle_age_years(myear, ryear)

    has_od = facts.premium.od_premium.is_present()
    has_tp = facts.premium.tp_premium.is_present()
    ptype = N.norm_policy_type(v(facts.policy_type), has_od, has_tp, facts.source_file)
    btype = N.norm_business_type(v(facts.insurer), v(facts.previous_insurer), v(facts.business_type))

    weak = []
    for f in DRIVER_FIELDS:
        fv = getattr(facts, f, None)
        if fv is not None and fv.is_present() and fv.evidence.confidence < DRIVER_FACT_CONF_FLOOR:
            weak.append(f)
    if rto_mismatch and "rto_code" not in weak:
        weak.append("rto_code")

    return ResolvedInput(
        insurer=v(facts.insurer),
        previous_insurer=v(facts.previous_insurer),
        business_type=btype,
        policy_type=ptype,
        make=v(facts.make),
        model=v(facts.model),
        fuel=fuel,
        cc=N.to_int(v(facts.cc)),
        rto_code=rto_code,
        rto_location=v(facts.rto_location),
        manufacture_year=myear,
        vehicle_age_years=age,
        ncb_percent=N.to_float(v(facts.ncb_percent)),
        zero_depreciation=bool(v(facts.zero_depreciation)),
        od_premium=N.to_float(v(facts.premium.od_premium)),
        tp_premium=N.to_float(v(facts.premium.tp_premium)),
        net_premium=N.to_float(v(facts.premium.net_premium)),
        facts=facts,
        weak_fields=weak,
    )


def resolve(facts: PolicyFacts) -> tuple[base.ResolverResult, ResolvedInput]:
    inp = build_input(facts)
    key, score, why = detect_insurer(facts)
    if key is None:
        rr = base.ResolverResult(
            "unsupported", str(facts.insurer.value or "unknown"), "",
            base.RateComponent(False), base.RateComponent(False),
            [base.TraceStep(1, "Detect insurer", why)], [], "low",
            "insurer could not be matched to a supported commission grid",
            reason=f"No supported grid for insurer '{facts.insurer.value}'. "
                   f"Supported: Reliance, Go Digit, Tata AIG, HDFC ERGO.",
        )
        return rr, inp
    try:
        rr = _RESOLVERS[key](inp)
    except base.Unresolvable as e:
        pack = load_rulepack(key)
        rr = base.ResolverResult(
            e.status, pack["insurer"], pack["file"],
            base.RateComponent(False), base.RateComponent(False),
            [base.TraceStep(1, "Resolution halted", e.reason)], [], "low",
            "evidence insufficient for a rate", reason=e.reason,
            clarifying_question=e.clarifying_question, candidates=e.candidates,
        )
    return rr, inp
