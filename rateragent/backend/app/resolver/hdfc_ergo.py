"""HDFC ERGO -- Private Car commission resolver (PDF rate card).

Grid shape: two zone tables (Zone 1 / Zone 2). Rows are OD-GWP premium slabs;
columns are Package vs SAOD, each split Petrol / Non-Petrol and (for non-petrol)
NCB vs N-NCB. Zone comes from a state -> Zone-1/Zone-2 table. The grid has no
third-party column, so TP commission is 0%.
"""
from __future__ import annotations

from ..extraction.normalize import rto_state
from . import base
from .common import ResolvedInput, best_match, confidence_from, load_rulepack, require

FILE_KEY = "hdfc_ergo"


def resolve(inp: ResolvedInput) -> base.ResolverResult:
    pack = load_rulepack(FILE_KEY)
    fname = pack["file"]
    tb = base.TraceBuilder()

    if inp.policy_type == "standalone_tp":
        raise base.Unresolvable(
            "unsupported",
            "HDFC ERGO Private Car grid covers Package and SAOD (own-damage) commission only; "
            "a stand-alone TP policy has no applicable row.",
        )

    # 1. RTO -> state -> zone --------------------------------------------
    rto_code = str(require(inp, "rto_code", "RTO code"))
    state = rto_state(rto_code)
    if not state:
        raise base.Unresolvable("unsupported", f"Could not derive a state from RTO code {rto_code}.")
    smap = pack["state_zone_map"]
    entry = smap.get(state.upper())
    if entry is None:
        hit, _, _ = best_match(state, list(smap.keys()), threshold=88)
        entry = smap.get(hit) if hit else None
    if entry is None:
        raise base.Unresolvable("unsupported", f"State '{state}' is not in the HDFC ERGO zone table.")

    zone = str(entry["default"])
    zwhy = f"state '{state}' default zone {zone}"
    loc = (inp.rto_location or "")
    for zkey, znum in (("zone1_regions", "1"), ("zone2_regions", "2")):
        for region in entry.get(zkey, []):
            if region.lower() in loc.lower() or best_match(region, [loc], threshold=88)[0]:
                zone, zwhy = znum, f"RTO location '{loc}' matched '{region}' -> Zone {znum}"
    tb.add("Map RTO to HDFC ERGO zone",
           f"RTO {rto_code} -> {state} -> Zone {zone} ({zwhy}).",
           [inp.policy_cite("rto_code"),
            base.Citation(fname, pack["state_zone_map_page"], "pdf", zone, f"state {state}, page {entry.get('page')}")])

    # 2. Premium slab ---------------------------------------------------
    od_prem = inp.od_premium
    if od_prem is None:
        raise base.Unresolvable(
            "ambiguous",
            "The OD (own-damage) premium could not be extracted; the HDFC ERGO grid slab "
            "cannot be selected.",
            clarifying_question="What is the net Own Damage premium on the policy?",
        )
    slab = None
    for name, lo, hi in pack["slab_bounds"]:
        if od_prem >= lo and (hi is None or od_prem < hi):
            slab = name
            break
    tb.add("Select premium slab",
           f"OD GWP ₹{od_prem:,.0f} -> slab '{slab}'.",
           [inp.policy_cite("premium"),
            base.Citation(fname, "page 1, slab column", "pdf", slab)])

    # 3. Column: section / fuel / NCB ---------------------------------
    section = "saod" if inp.policy_type == "standalone_od" else "package"
    petrol_grid = inp.fuel in ("petrol", "electric", "hybrid", "unknown")  # footnote: EV/Hybrid in petrol grid
    ncb_flag = bool((inp.ncb_percent and inp.ncb_percent > 0) or inp.business_type == "new")
    if petrol_grid:
        col = f"{section}_petrol"
        col_note = "Petrol grid (footnote: EV & Hybrid use the Petrol grid)" if inp.fuel in ("electric", "hybrid") else "Petrol column"
    else:
        col = f"{section}_nonpetrol_{'ncb' if ncb_flag else 'nncb'}"
        col_note = f"Non-Petrol ({'NCB' if ncb_flag else 'N-NCB'}) column (footnote: Non-Petrol = Diesel/CNG/LPG)"

    rate = pack["rate_tables"][zone][slab][col]
    tb.add("Read the OD commission cell",
           f"Zone {zone}, slab '{slab}', {col_note} -> {rate}%.",
           [base.Citation(fname, f"{pack['rate_table_pages'][zone]}, row '{slab}', column '{col}'", "pdf", rate)])

    notes = []
    if inp.fuel == "unknown":
        notes.append("fuel type not printed on the schedule; treated via the Petrol grid pending confirmation")
    if inp.business_type == "new":
        notes.append("footnote: New Business is considered NCB")

    od = base.RateComponent(True, float(rate), "OD premium", "; ".join(notes))
    tp = base.RateComponent(
        True, 0.0, "TP premium",
        "HDFC ERGO Private Car grid has no third-party commission column; TP payout is 0%.",
    )
    tb.add("Third-party commission",
           "The HDFC ERGO Pvt Car grid publishes Package/SAOD (OD) rates only; TP = 0%.",
           [base.Citation(fname, "page 1 (no TP column present)", "pdf", 0.0)])

    fcites = [base.Citation(fname, f"page {f['page']}", "pdf", None, f["text"]) for f in pack["footnotes"]]
    lvl, why = confidence_from(inp)
    return base.ResolverResult("resolved", "HDFC ERGO", fname, od, tp, tb.steps, tb.citations + fcites, lvl, why)
