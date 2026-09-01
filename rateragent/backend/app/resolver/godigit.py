"""Go Digit -- Private Car stand-alone-TP commission resolver.

Grid shape: ``4W  RTO`` maps an RTO code -> a TP cluster. ``4W SATP`` is a
Cluster x Segment x Age table where Segment is a fuel+CC band string
("Petrol<1000", "Diesel>1500", ...). The rate ("Max CD2") is stored as a
fraction.
"""
from __future__ import annotations

import re

from . import base
from .common import ResolvedInput, confidence_from, load_rulepack, require

FILE_KEY = "godigit"
_DECLINE = {"all_india_decline"}


def resolve(inp: ResolvedInput) -> base.ResolverResult:
    pack = load_rulepack(FILE_KEY)
    fname = pack["file"]
    tb = base.TraceBuilder()

    if inp.policy_type == "comprehensive":
        raise base.Unresolvable(
            "unsupported",
            "This resolver covers the Go Digit stand-alone-TP ('4W SATP') grid only; the "
            "supplied comprehensive/package grid sheet is not modelled.",
        )

    # 1. RTO -> TP cluster ---------------------------------------------------
    rto_code = str(require(inp, "rto_code", "RTO code"))
    key = rto_code.replace("-", "").upper()
    entry = pack["rto_cluster_map"].get(key)
    if entry is None:
        raise base.Unresolvable(
            "unsupported",
            f"RTO code {rto_code} is not present in the Go Digit '4W  RTO' mapping sheet.",
        )
    cluster = entry["tp_cluster"]
    tb.add(
        "Map RTO code to Go Digit TP cluster",
        f"RTO {rto_code} -> TP cluster '{cluster}' via the '4W  RTO' sheet (4WTP column).",
        [inp.policy_cite("rto_code"),
         base.Citation(fname, entry["cells"]["tp_cluster"], "xlsx", cluster)],
    )
    if cluster and cluster.lower() in _DECLINE:
        raise base.Unresolvable("unsupported", f"Cluster '{cluster}' is an all-India decline; no TP rate is offered.")

    rows = [r for r in pack["satp_rows"] if r["cluster"].strip().lower() == (cluster or "").strip().lower()]
    if not rows:
        raise base.Unresolvable("unsupported", f"No '4W SATP' rows for cluster '{cluster}'.")

    # 2. Choose the fuel + CC band segment --------------------------------
    fuel = inp.fuel
    fuel_prefix = {"petrol": "Petrol", "diesel": "Diesel", "cng": "CNG", "lpg": "CNG"}.get(fuel)
    if fuel_prefix is None:
        raise base.Unresolvable(
            "ambiguous",
            f"Fuel '{fuel}' has no Go Digit SATP segment band (grid covers Petrol/Diesel/CNG).",
            clarifying_question="What is the fuel type of the vehicle?",
        )
    fuel_rows = [r for r in rows if r["segment"].lower().startswith(fuel_prefix.lower())]
    if not fuel_rows:
        raise base.Unresolvable(
            "unsupported",
            f"Cluster '{cluster}' has no '{fuel_prefix}' segment row in the '4W SATP' grid.",
        )

    seg_row = _pick_cc_band(fuel_rows, inp.cc)
    if seg_row is None:
        raise base.Unresolvable(
            "ambiguous",
            f"Engine CC ({inp.cc}) does not resolve to a single {fuel_prefix} band for cluster "
            f"'{cluster}'.",
            clarifying_question="What is the exact engine cubic capacity (cc)?",
            candidates=[{"segment": r["segment"], "row": r["row"], "rate": r["rate"]} for r in fuel_rows],
        )

    # 3. Age band --------------------------------------------------------
    age_rows = [r for r in fuel_rows if r["segment"] == seg_row["segment"]]
    chosen = _pick_age(age_rows, inp.vehicle_age_years)
    if chosen is None:
        raise base.Unresolvable(
            "ambiguous",
            f"Vehicle age could not be matched to a Go Digit age band for segment "
            f"'{seg_row['segment']}'.",
            clarifying_question="What is the vehicle's age in years (or its registration date)?",
            candidates=[{"segment": r["segment"], "age": r["age"], "rate": r["rate"], "row": r["row"]} for r in age_rows],
        )
    tb.add(
        "Select Cluster x Segment x Age row",
        f"Cluster '{cluster}', segment '{chosen['segment']}' (fuel {fuel}, {inp.cc} cc), "
        f"age band '{chosen['age']}' (vehicle age {inp.vehicle_age_years}) -> row {chosen['row']}.",
        [inp.policy_cite("cc"), inp.policy_cite("vehicle_age_years"),
         base.Citation(fname, chosen["cells"]["rate"], "xlsx", chosen["rate"])],
    )

    note = chosen.get("note")
    if note and "decline" in note.lower():
        raise base.Unresolvable("unsupported", f"Grid note declines this segment: '{note}'.")

    rate_pct = round(float(chosen["rate"]) * 100, 4)
    extra_cites = []
    if note:
        extra_cites.append(base.Citation(fname, chosen["cells"]["note"], "xlsx", note))
        tb.add("Apply grid note", f"Note on the matched row: '{note}'.", extra_cites[-1:])

    tb.add(
        "Return TP commission",
        f"'Max CD2' = {chosen['rate']} -> {rate_pct}% on the TP (net) premium. "
        f"OD is not applicable for a stand-alone TP policy.",
        [base.Citation(fname, chosen["cells"]["rate"], "xlsx", chosen["rate"])],
    )

    od = base.RateComponent(applicable=False, note="stand-alone TP policy: no OD component")
    tp = base.RateComponent(True, rate_pct, "TP / net premium", (note or ""))
    lvl, why = confidence_from(inp)
    return base.ResolverResult("resolved", "Go Digit", fname, od, tp, tb.steps, tb.citations + extra_cites, lvl, why)


_BAND_RE = re.compile(r"(<|>|)\s*(\d{3,4})(?:\s*-\s*(\d{3,4}))?")


def _band_bounds(segment: str) -> tuple[float, float]:
    """'Petrol<1000' -> (0,1000); 'Petrol>1000' -> (1000,inf); 'Petrol 1000-1500' -> (1000,1500);
    'Petrol' -> (0,inf)."""
    m = _BAND_RE.search(segment)
    if not m:
        return (0.0, float("inf"))
    op, lo, hi = m.group(1), int(m.group(2)), m.group(3)
    if hi:
        return (float(lo), float(hi))
    if op == "<":
        return (0.0, float(lo))
    if op == ">":
        return (float(lo), float("inf"))
    return (0.0, float("inf"))


def _pick_cc_band(rows: list[dict], cc: int | None):
    uniq = {r["segment"]: r for r in rows}
    if len(uniq) == 1:
        return next(iter(uniq.values()))
    if cc is None:
        return None
    hits = []
    for seg, r in uniq.items():
        lo, hi = _band_bounds(seg)
        if lo <= cc < hi or (hi == float("inf") and cc >= lo):
            hits.append((hi - lo, r))
    if not hits:
        return None
    hits.sort(key=lambda t: t[0])  # narrowest band wins
    return hits[0][1]


def _pick_age(rows: list[dict], age: int | None):
    for r in rows:
        if (r["age"] or "All").strip().lower() == "all":
            return r
    if age is None:
        return None
    for r in rows:
        a = (r["age"] or "").replace(" ", "")
        if a.startswith("<") and age < int(re.sub(r"\D", "", a)):
            return r
        if a.startswith(">") and age > int(re.sub(r"\D", "", a)):
            return r
    return None
