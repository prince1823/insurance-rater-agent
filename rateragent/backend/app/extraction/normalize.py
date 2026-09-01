"""Canonicalisation helpers shared by extraction and resolvers.

Pure functions, no I/O. These turn the messy strings printed on policy documents
into the small controlled vocabularies the resolvers expect.
"""
from __future__ import annotations

import datetime as _dt
import json
import re
from pathlib import Path

_RTO_STATE = json.loads((Path(__file__).resolve().parent.parent / "data" / "rto_state.json").read_text())

FUEL_SYNONYMS = {
    "petrol": "petrol", "mpfi": "petrol", "gasoline": "petrol",
    "diesel": "diesel", "hsd": "diesel",
    "cng": "cng", "petrol+cng": "cng", "bi-fuel": "cng", "bifuel": "cng", "petrol/cng": "cng",
    "lpg": "lpg", "petrol+lpg": "lpg",
    "electric": "electric", "ev": "electric", "battery": "electric", "bev": "electric",
    "hybrid": "hybrid", "phev": "hybrid", "strong hybrid": "hybrid",
}

_LUXURY_MAKES = {
    "bmw", "mercedes", "mercedes-benz", "mercedes benz", "audi", "jaguar", "land rover",
    "volvo", "porsche", "lexus", "mini", "bentley", "maserati", "ferrari", "lamborghini",
    "rolls royce", "rolls-royce", "aston martin",
}


def norm_fuel(raw: str | None) -> str:
    if not raw:
        return "unknown"
    s = re.sub(r"\s+", " ", str(raw)).strip().lower()
    if s in FUEL_SYNONYMS:
        return FUEL_SYNONYMS[s]
    for key, val in FUEL_SYNONYMS.items():
        if key in s:
            return val
    return "unknown"


def norm_rto_code(raw: str | None) -> str | None:
    """'HR-26-FB-8239' / 'HR26FB8239' / 'DL 9C AB 2893' -> 'HR-26' / 'DL-9C'."""
    if not raw:
        return None
    s = str(raw).upper().strip()
    s = s.replace(" ", "").replace("-", "")
    m = re.match(r"^([A-Z]{2})(\d{2})", s)          # standard: 2 letters + 2 digits
    if not m:
        m = re.match(r"^([A-Z]{2})(\d[A-Z])", s)    # Delhi style: 1 digit + 1 letter (DL-9C)
    if not m:
        m = re.match(r"^([A-Z]{2})(\d)", s)         # 2 letters + 1 digit
    if not m:
        return None
    return f"{m.group(1)}-{m.group(2)}"


def rto_state(rto_code: str | None) -> str | None:
    if not rto_code:
        return None
    prefix = rto_code.split("-")[0].upper()
    return _RTO_STATE.get(prefix)


def norm_business_type(current_insurer: str | None, previous_insurer: str | None,
                       stated: str | None = None) -> str:
    """Challenge rule: same insurer current & previous => renewal.
    Different named previous insurer => rollover. No previous => new. Else unknown.
    """
    cur = _canon_insurer(current_insurer)
    prev = _canon_insurer(previous_insurer)
    if cur and prev:
        return "renewal" if cur == prev else "rollover"
    if stated:
        s = stated.lower()
        for t in ("renewal", "rollover", "roll over", "new"):
            if t in s:
                return "rollover" if "roll" in t else ("renewal" if "renew" in t else "new")
    if previous_insurer and str(previous_insurer).strip().upper() not in ("", "NA", "N/A", "NONE"):
        return "rollover"
    return "unknown"


def _canon_insurer(name: str | None) -> str | None:
    if not name:
        return None
    s = re.sub(r"[^a-z ]", "", str(name).lower())
    s = re.sub(r"\b(general|insurance|company|limited|ltd|co|the|india)\b", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s or None


def norm_policy_type(stated: str | None, has_od_premium: bool, has_tp_premium: bool,
                     title: str | None = None) -> str:
    blob = " ".join(x for x in (stated, title) if x).lower()
    if any(k in blob for k in ("liability only", "stand-alone tp", "standalone tp", "satp", "act only")):
        return "standalone_tp"
    if any(k in blob for k in ("stand-alone od", "saod", "own damage only")):
        return "standalone_od"
    if any(k in blob for k in ("comprehensive", "package", "bundled")):
        return "comprehensive"
    if has_od_premium and has_tp_premium:
        return "comprehensive"
    if has_tp_premium and not has_od_premium:
        return "standalone_tp"
    return "unknown"


def vehicle_age_years(manufacture_year: int | None, registration_year: int | None,
                      as_of: _dt.date | None = None) -> int | None:
    as_of = as_of or _dt.date.today()
    base = registration_year or manufacture_year
    if not base or base < 1980 or base > as_of.year + 1:
        return None
    return max(0, as_of.year - base)


def to_int(v) -> int | None:
    if v is None:
        return None
    try:
        return int(round(float(str(v).replace(",", "").strip())))
    except (ValueError, TypeError):
        return None


def to_float(v) -> float | None:
    if v is None:
        return None
    try:
        return float(str(v).replace(",", "").replace("₹", "").strip())
    except (ValueError, TypeError):
        return None


def is_luxury_make(make: str | None) -> bool:
    return bool(make) and make.strip().lower() in _LUXURY_MAKES
