"""Reliance General Insurance -- Private Car commission resolver.

Grid shape: ``RTO List`` maps an RTO code -> (region city, zone). The
``PRIVATE CAR COMP, SAOD & STP`` sheet is a Zone x RTO-region table with fuel
columns (Petrol/Bifuel vs Diesel/EV) plus SA-OD and STP columns. Footnotes in
column H override the table (e.g. < 1000 cc => 5 points lower).
"""
from __future__ import annotations

from . import base
from .common import ResolvedInput, best_match, confidence_from, load_rulepack, require

FILE_KEY = "reliance"


def resolve(inp: ResolvedInput) -> base.ResolverResult:
    pack = load_rulepack(FILE_KEY)
    fname = pack["file"]
    tb = base.TraceBuilder()

    # 1. RTO -> zone + region city ------------------------------------------------
    rto_code = str(require(inp, "rto_code", "RTO code"))
    zmap = pack["rto_zone_map"]
    entry = zmap.get(rto_code) or zmap.get(rto_code.replace("-", "")) or zmap.get(rto_code.replace("-", "-0"))
    if entry is None:
        raise base.Unresolvable(
            "unsupported",
            f"RTO code {rto_code} is not present in the Reliance 'RTO List' sheet, so its "
            f"zone / region cannot be determined.",
        )
    zone = entry["zone"]
    region_city = entry.get("region_city")
    c_zone = base.Citation(fname, entry["cells"]["zone"], "xlsx", zone)
    c_city = base.Citation(fname, entry["cells"]["region_city"], "xlsx", region_city)
    tb.add(
        "Map RTO code to Reliance zone",
        f"RTO {rto_code} -> region city '{region_city}', zone '{zone}' via the 'RTO List' sheet.",
        [inp.policy_cite("rto_code"), c_zone, c_city],
    )

    # 2. Locate the Zone x region rate row --------------------------------------
    rows = [r for r in pack["pvt_car_rows"] if (r["zone"] or "").upper() == zone.upper()]
    if not rows:
        raise base.Unresolvable("unsupported", f"No Reliance private-car rate rows for zone '{zone}'.")

    def region_score(r: dict) -> float:
        tokens = [t.strip() for t in r["rto_region"].replace("/", ",").split(",")]
        _, score, _ = best_match(region_city or "", tokens + [r["rto_region"]], threshold=0)
        return score

    ranked = sorted(rows, key=region_score, reverse=True)
    top = ranked[0]
    top_score = region_score(top)
    if region_city and top_score < 60:
        raise base.Unresolvable(
            "ambiguous",
            f"Region city '{region_city}' (zone {zone}) does not clearly match any Reliance "
            f"rate row.",
            candidates=[{"rto_region": r["rto_region"], "row": r["row"]} for r in ranked[:4]],
        )
    if len(ranked) > 1 and abs(region_score(ranked[1]) - top_score) < 1e-6 and top_score < 90:
        raise base.Unresolvable(
            "ambiguous",
            f"Region city '{region_city}' matches multiple Reliance rate rows equally.",
            candidates=[{"rto_region": r["rto_region"], "row": r["row"]} for r in ranked[:4]],
        )
    row = top
    tb.add(
        "Select the Zone x region rate row",
        f"Zone '{zone}' + region '{region_city}' -> grid row '{row['rto_region']}' (row {row['row']}).",
        [base.Citation(fname, row["cells"]["rto_region"], "xlsx", row["rto_region"])],
    )

    # 3. Choose the fuel / section column -------------------------------------
    fuel = inp.fuel
    pt = inp.policy_type
    footnote_cites = [
        base.Citation(fname, f["cell"], "xlsx", None, f["text"]) for f in pack["footnotes"]
    ]

    if pt == "standalone_tp":
        od = base.RateComponent(applicable=False, note="stand-alone TP policy has no OD component")
        stp = row["stp"]
        tp = base.RateComponent(True, _num(stp), "TP / net premium",
                                "Reliance publishes STP payout in column F")
        tb.add("Read STP rate",
               f"Stand-alone TP: STP column = {stp} -> {_num(stp)}%.",
               [base.Citation(fname, row["cells"]["stp"], "xlsx", stp)])
        cites = tb.citations + footnote_cites
        lvl, why = confidence_from(inp)
        return base.ResolverResult("resolved", "Reliance", fname, od, tp, tb.steps, cites, lvl, why)

    if pt == "standalone_od":
        col_key, col_val = "sa_od", row["sa_od"]
        col_note = "SA OD column (E)"
    elif fuel in ("diesel", "electric"):
        col_key, col_val = "diesel_ev_comp", row["diesel_ev_comp"]
        col_note = "Diesel/EV comprehensive column (D)"
    elif fuel in ("petrol", "cng", "lpg", "hybrid"):
        col_key, col_val = "petrol_bifuel_comp", row["petrol_bifuel_comp"]
        col_note = "Petrol/Bifuel comprehensive column (C)"
    else:
        raise base.Unresolvable(
            "ambiguous",
            "Fuel type is unknown; Reliance needs Petrol/Bifuel vs Diesel/EV to pick the OD column.",
            clarifying_question="What is the fuel type of the vehicle?",
        )

    base_od = _num(col_val)
    tb.add(
        "Read the base OD commission",
        f"Fuel '{fuel}', {inp.policy_type} -> {col_note} = {col_val} -> {base_od}%.",
        [base.Citation(fname, row["cells"][col_key], "xlsx", col_val)],
    )

    # 4. Apply footnote overrides ------------------------------------------
    adjusted = base_od
    adj_notes = []
    lt1000 = next((f for f in pack["footnotes"] if "1000 CC" in f["text"] or "1000CC" in f["text"]), None)
    if inp.cc is not None and inp.cc < 1000 and lt1000:
        adjusted -= 5.0
        adj_notes.append(f"CC {inp.cc} < 1000: −5 points ({lt1000['text']})")
        tb.add("Apply < 1000 cc footnote",
               f"Engine {inp.cc} cc < 1000 -> subtract 5 points: {base_od}% -> {adjusted}%.",
               [inp.policy_cite("cc"), base.Citation(fname, lt1000["cell"], "xlsx", None, lt1000["text"])])
    elif inp.cc is None:
        adj_notes.append("CC not extracted; the < 1000 cc footnote could not be evaluated")

    zd_note = next((f for f in pack["footnotes"] if "ZD" in f["text"]), None)
    if inp.zero_depreciation and zd_note:
        adj_notes.append(
            f"Policy carries Zero-Depreciation cover. Footnote '{zd_note['text']}' reduces the "
            f"rate by 2.5 points only for *stand-alone ZD* policies; this is a package policy "
            f"with ZD as an add-on, so no reduction is applied."
        )

    od = base.RateComponent(True, round(adjusted, 4), "OD premium",
                            "; ".join(adj_notes) if adj_notes else "")
    stp = row["stp"]
    tp = base.RateComponent(True, _num(stp), "TP / net premium",
                            "package policy; Reliance STP column applies to the TP component")
    tb.add("Read TP (STP) rate",
           f"STP column = {stp} -> {_num(stp)}% on the TP component.",
           [base.Citation(fname, row["cells"]["stp"], "xlsx", stp)])

    lvl, why = confidence_from(inp)
    cites = tb.citations + footnote_cites
    return base.ResolverResult("resolved", "Reliance", fname, od, tp, tb.steps, cites, lvl, why)


def _num(v) -> float | None:
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    # grid stores percentages as whole numbers (e.g. 22.5) already
    return round(f, 4)
