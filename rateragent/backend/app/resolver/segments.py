"""Vehicle make/model -> insurer segment classification.

Insurer grids bucket cars into vendor-specific segments. There is no segment
sheet in the Tata AIG workbook, so this module returns a *candidate list* from a
small curated table plus CC/body heuristics. The resolver looks up every
candidate; if they all yield the same rate the answer is still ``resolved`` (the
ambiguity collapses), otherwise it is ``ambiguous`` with the candidates shown.
"""
from __future__ import annotations

from ..extraction.normalize import is_luxury_make

# Curated model -> Tata-AIG-style segment. Deliberately small; extend as needed.
_MODEL_SEGMENT: dict[str, str] = {
    "alto": "Mini", "kwid": "Mini", "s-presso": "Mini", "spresso": "Mini",
    "eon": "Mini", "santro": "Mini", "zen estilo": "Mini", "estilo": "Mini",
    "nano": "Mini", "redi-go": "Mini", "redigo": "Mini",
    "swift": "Compact", "baleno": "Compact", "i20": "Compact", "polo": "Compact",
    "grand i10": "Compact", "i10": "Compact", "figo": "Compact", "jazz": "Compact",
    "tiago": "Compact", "altroz": "Compact", "glanza": "Compact", "wagon r": "Compact",
    "wagonr": "Compact", "celerio": "Compact", "ignis": "Compact",
    "dzire": "Mid Size", "amaze": "Mid Size", "aura": "Mid Size", "xcent": "Mid Size",
    "city": "Mid Size", "verna": "Mid Size", "ciaz": "Mid Size", "rapid": "Mid Size",
    "vento": "Mid Size", "virtus": "Mid Size", "slavia": "Mid Size", "tigor": "Mid Size",
    "creta": "MPV SUV", "seltos": "MPV SUV", "nexon": "MPV SUV", "brezza": "MPV SUV",
    "venue": "MPV SUV", "sonet": "MPV SUV", "kiger": "MPV SUV", "magnite": "MPV SUV",
    "bolero": "MPV SUV", "scorpio": "MPV SUV", "xuv300": "MPV SUV", "xuv500": "MPV SUV",
    "xuv700": "MPV SUV", "thar": "MPV SUV", "innova": "MPV SUV", "ertiga": "MPV SUV",
    "fortuner": "MPV SUV", "harrier": "MPV SUV", "safari": "MPV SUV", "hector": "MPV SUV",
    "bolero neo": "MPV SUV",
}

TATA_SEGMENTS = ["Mini", "Compact", "Mid Size", "MPV SUV", "High End", "Ultra High End"]


def tata_segment_candidates(make: str | None, model: str | None, cc: int | None,
                            body_type: str | None) -> tuple[list[str], str]:
    """Return (candidate_segments, explanation)."""
    model_l = (model or "").strip().lower()
    body_l = (body_type or "").strip().lower()

    for key, seg in sorted(_MODEL_SEGMENT.items(), key=lambda kv: -len(kv[0])):
        if key in model_l:
            return [seg], f"model '{model}' matched curated entry '{key}' -> {seg}"

    if is_luxury_make(make):
        return ["High End", "Ultra High End"], f"make '{make}' is a luxury marque"

    if any(t in body_l for t in ("suv", "muv", "mpv")):
        return ["MPV SUV"], f"body type '{body_type}' -> MPV SUV"

    if cc is None:
        return ["Mini", "Compact", "Mid Size"], "no model match and CC unknown -> hatch/sedan candidates"
    if cc < 1000:
        return ["Mini", "Compact"], f"CC {cc} < 1000 -> Mini/Compact"
    if cc <= 1400:
        return ["Compact", "Mid Size"], f"CC {cc} in 1000-1400 -> Compact/Mid Size"
    if cc <= 1800:
        return ["Mid Size", "MPV SUV"], f"CC {cc} in 1400-1800 -> Mid Size/MPV SUV"
    return ["MPV SUV", "High End"], f"CC {cc} > 1800 -> MPV SUV/High End"
