"""Tata AIG -- Private Car commission resolver.

Grid shape: the ``Pvtcar`` sheet is a long key table
(Type/Segment x Business Type x Fuel x Section x NCB x Add-On) whose value
columns are RTO cluster-cities (AHMEDABAD ... DELHI ... VISHAKAPATNAM). SATP %
applies on Net premium; Package/SAOD % on OD premium. Rates are fractions.
"""
from __future__ import annotations

from ..extraction.normalize import rto_state
from . import base
from .common import ResolvedInput, best_match, confidence_from, load_rulepack, require
from .segments import tata_segment_candidates

FILE_KEY = "tataaig"

# States whose premium territory is a single Tata cluster column.
_STATE_COLUMN = {
    "haryana": "HARYANA", "goa": "GOA", "kerala": "KERALA", "bihar": "BIHAR",
    "jharkhand": "JHARKHAND", "chandigarh": "CHANDIGARH", "uttarakhand": "UTTARAKHAND",
    "himachal pradesh": "Himachal Pradesh", "jammu and kashmir": "Jammu & Kashmir",
    "chhattisgarh": "Chhattisgarh", "andhra pradesh": "Andra Pradesh",
    "telangana": "Telengana", "delhi": "DELHI", "odisha": "ROOD",
}
# States split into multiple columns -> need a city to disambiguate.
_STATE_MULTI = {
    "uttar pradesh": ["UP1", "UP2", "UP3"],
    "rajasthan": ["JAIPUR", "RJ1", "RJ2", "RJ3", "RJ4", "RJ5"],
    "madhya pradesh": ["INDORE", "MP1", "MP2", "MP3"],
    "punjab": ["PB1", "PB2"],
    "karnataka": ["BANGALORE", "KA1", "KA2"],
    "maharashtra": ["MUMBAI", "PUNE", "NAGPUR", "ROM1", "ROM2", "ROM3", "ROM4"],
    "gujarat": ["AHMEDABAD", "SURAT", "RAJKOT", "Vadodara", "ROGJ"],
    "west bengal": ["KOLKATA", "ROWB", "ROWB2"],
    "tamil nadu": ["CHENNAI", "COIMBATORE", "ROTN"],
}
_FUEL_MAP = {"petrol": "Petrol", "diesel": "Diesel", "cng": "CNG", "lpg": "CNG",
            "electric": "Electric", "hybrid": "Petrol"}


def resolve(inp: ResolvedInput) -> base.ResolverResult:
    pack = load_rulepack(FILE_KEY)
    fname = pack["file"]
    cols = pack["cluster_columns"]
    tb = base.TraceBuilder()

    # 1. RTO -> cluster-city column ---------------------------------------
    column, col_trace = _resolve_column(inp, cols)
    tb.add("Map RTO to Tata AIG cluster column", col_trace,
           [inp.policy_cite("rto_location") if inp.rto_location else inp.policy_cite("rto_code")])

    # 2. Section --------------------------------------------------------
    section = {"comprehensive": "Package", "standalone_od": "SAOD",
              "standalone_tp": "SATP"}.get(inp.policy_type)
    if section is None:
        raise base.Unresolvable("ambiguous", "Policy type (comprehensive vs SATP) is unknown.",
                                clarifying_question="Is this a comprehensive/package policy or a stand-alone third-party policy?")

    # 3. Fuel --------------------------------------------------------
    fuel = _FUEL_MAP.get(inp.fuel)
    if fuel is None:
        raise base.Unresolvable("ambiguous", f"Fuel '{inp.fuel}' cannot be matched to a Tata AIG fuel key.",
                                clarifying_question="What is the fuel type of the vehicle?")

    # 4. Segment candidates -------------------------------------------
    seg_candidates, seg_why = tata_segment_candidates(inp.make, inp.model, inp.cc, inp.facts.body_type.value if inp.facts else None)
    tb.add("Classify vehicle segment", f"{seg_why}. Candidate segment(s): {seg_candidates}.",
           [inp.policy_cite("model")])

    # 5. Business type candidates ------------------------------------
    biz_candidates = _biz_candidates(inp)
    tb.add("Determine business type",
           f"Extracted business type '{inp.business_type}' (previous insurer "
           f"{inp.previous_insurer or 'not stated'}). Grid business-type candidate(s): {biz_candidates}.",
           [inp.policy_cite("previous_insurer")])

    # 6. Gather matching rows ---------------------------------------
    def ncb_ok(row_ncb: str) -> bool:
        r = (row_ncb or "All").lower()
        if r == "all":
            return True
        want_yes = bool(inp.ncb_percent and inp.ncb_percent > 0)
        return (r == "yes") == want_yes

    def addon_ok(row_addon: str) -> bool:
        r = (row_addon or "All").lower()
        if r == "all":
            return True
        return (r == "yes") == bool(inp.zero_depreciation)

    matches = [
        r for r in pack["pvtcar_rows"]
        if r["segment"] in seg_candidates
        and r["section"] == section
        and (r["business_type"] in biz_candidates)
        and _fuel_row_ok(r["fuel"], fuel)
        and ncb_ok(r["ncb"]) and addon_ok(r["addon"])
        and column in r["rates"]
    ]
    if not matches:
        # try the 'Other Than Diesel' fallback row
        matches = [
            r for r in pack["pvtcar_rows"]
            if r["segment"] in seg_candidates and r["section"] == section
            and r["business_type"] in biz_candidates and (r["fuel"] or "").lower() == "other than diesel"
            and ncb_ok(r["ncb"]) and addon_ok(r["addon"]) and column in r["rates"]
        ]
    if not matches:
        raise base.Unresolvable(
            "unsupported",
            f"No Tata AIG '{section}' row for segment {seg_candidates}, fuel '{fuel}', "
            f"business type {biz_candidates}, column '{column}'.",
        )

    col_letter = cols[column]
    priced = []
    for r in matches:
        val = r["rates"][column]
        priced.append((r, round(float(val) * 100, 4), f"{pack['rate_sheet']}!{col_letter}{r['row']}"))

    distinct = sorted({p[1] for p in priced})
    if len(distinct) > 1:
        raise base.Unresolvable(
            "ambiguous",
            f"Tata AIG rate depends on facts that are not uniquely determined "
            f"(segment {seg_candidates} / business type {biz_candidates}); candidate rates: {distinct}.",
            clarifying_question="What is the vehicle's exact model segment and the business type (renewal/rollover/new)?",
            candidates=[
                {"segment": r["segment"], "business_type": r["business_type"], "fuel": r["fuel"],
                 "ncb": r["ncb"], "addon": r["addon"], "rate_percent": pct, "cell": cell}
                for r, pct, cell in priced
            ],
        )

    rate_pct = distinct[0]
    chosen = priced[0]
    collapsed = ""
    if len({r["segment"] for r, _, _ in priced}) > 1 or len({r["business_type"] for r, _, _ in priced}) > 1:
        collapsed = (f"segment/business-type ambiguity collapsed: every candidate "
                     f"({', '.join(sorted({r['segment']+'/'+r['business_type'] for r,_,_ in priced}))}) "
                     f"gives {rate_pct}%")
    tb.add(
        "Look up the commission cell",
        f"Section '{section}', fuel '{fuel}', column '{column}' -> {rate_pct}% "
        f"({chosen[2]}). " + (collapsed or ""),
        [base.Citation(fname, cell, "xlsx", pct) for _, pct, cell in priced],
    )

    gcites = [base.Citation(fname, g["cell"], "xlsx", None, g["text"])
              for g in pack["guidelines"] if "premium" in g["text"].lower()][:2]

    if section == "SATP":
        od = base.RateComponent(applicable=False, note="stand-alone TP policy: no OD component")
        tp = base.RateComponent(True, rate_pct, "Net premium",
                                "Tata AIG guideline: SATP % applies on Net Premium")
    elif section == "SAOD":
        od = base.RateComponent(True, rate_pct, "OD premium")
        tp = base.RateComponent(False, note="stand-alone OD policy: no TP component")
    else:
        od = base.RateComponent(True, rate_pct, "OD premium",
                                "Tata AIG guideline: Package % applies on OD premium")
        tp = base.RateComponent(True, 0.0, "TP premium",
                                "Tata AIG Pvtcar grid pays commission on OD premium only for package policies")

    lvl, why = confidence_from(inp, "segment inferred from model, not an insurer table" if len(seg_candidates) > 1 and not collapsed else "")
    return base.ResolverResult("resolved", "Tata AIG", fname, od, tp, tb.steps, tb.citations + gcites, lvl, why, reason=collapsed)


def _fuel_row_ok(row_fuel: str, want: str) -> bool:
    rf = (row_fuel or "").lower()
    if rf == want.lower():
        return True
    if want == "CNG" and rf in ("cng", "other than diesel"):
        return True
    if want == "Petrol" and rf in ("petrol", "other than diesel"):
        return True
    return False


def _biz_candidates(inp: ResolvedInput) -> list[str]:
    bt = inp.business_type
    if bt == "new":
        return ["Brand New"]
    if bt == "renewal":
        return ["Renewal"]
    if bt == "rollover":
        return ["Rollover"]
    age = inp.vehicle_age_years
    if age is not None and age <= 1:
        return ["Brand New", "Renewal", "Rollover"]
    return ["Renewal", "Rollover"]  # aged vehicle, unknown history: not brand new


def _resolve_column(inp: ResolvedInput, cols: dict) -> tuple[str, str]:
    names = list(cols.keys())
    loc = (inp.rto_location or "").strip()
    state = rto_state(inp.rto_code)

    # a) direct fuzzy match on the printed RTO location (often a city)
    if loc:
        for token in [loc] + [t.strip() for t in loc.replace("/", ",").replace("-", ",").split(",")]:
            hit, score, _ = best_match(token, names, threshold=90)
            if hit:
                return hit, f"RTO location '{loc}' matched cluster column '{hit}' (score {score:.0f})."

    # b) state -> single column
    if state and state.lower() in _STATE_COLUMN:
        col = _STATE_COLUMN[state.lower()]
        return col, f"RTO {inp.rto_code} -> state '{state}' -> single Tata cluster column '{col}'."

    # c) state -> multiple columns : try to disambiguate by city, else ambiguous
    if state and state.lower() in _STATE_MULTI:
        options = _STATE_MULTI[state.lower()]
        if loc:
            hit, score, _ = best_match(loc, options, threshold=88)
            if hit:
                return hit, f"RTO location '{loc}' -> cluster column '{hit}' within state '{state}'."
        raise base.Unresolvable(
            "ambiguous",
            f"State '{state}' maps to several Tata AIG cluster columns ({options}) and the "
            f"printed RTO location '{loc or 'n/a'}' does not identify one.",
            clarifying_question=f"Which cluster applies for this RTO in {state}: {', '.join(options)}?",
            candidates=[{"column": o} for o in options],
        )

    raise base.Unresolvable(
        "unsupported",
        f"RTO {inp.rto_code} / location '{loc or 'n/a'}' could not be mapped to any Tata AIG "
        f"cluster column.",
    )
