"""Structured policy facts produced by the extraction step.

Every fact carries an ``Evidence`` object (page + verbatim snippet + a model
self-reported confidence) so the resolver and the UI can cite exactly where a
value came from and downgrade the overall result when a driver fact is weak.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

FuelType = Literal["petrol", "diesel", "cng", "lpg", "electric", "hybrid", "unknown"]
PolicyType = Literal["comprehensive", "standalone_tp", "standalone_od", "unknown"]
BusinessType = Literal["new", "renewal", "rollover", "unknown"]


class Evidence(BaseModel):
    page: Optional[int] = Field(None, description="1-indexed PDF page")
    snippet: str = Field("", description="verbatim text supporting the value")
    confidence: float = Field(0.0, ge=0.0, le=1.0)


class FactValue(BaseModel):
    value: Optional[object] = None
    evidence: Evidence = Evidence()

    def is_present(self) -> bool:
        return self.value not in (None, "", "NA", "N/A")


class PremiumBreakup(BaseModel):
    od_premium: FactValue = FactValue()  # net OD premium (after NCB, incl OD add-ons)
    tp_premium: FactValue = FactValue()  # basic TP / liability premium
    net_premium: FactValue = FactValue()  # total net premium (OD + TP + PA, pre-tax)
    total_premium: FactValue = FactValue()  # premium incl. GST


class PolicyFacts(BaseModel):
    insurer: FactValue = FactValue()
    previous_insurer: FactValue = FactValue()
    business_type: FactValue = FactValue()  # value in BusinessType
    policy_type: FactValue = FactValue()  # value in PolicyType

    make: FactValue = FactValue()
    model: FactValue = FactValue()
    fuel: FactValue = FactValue()  # value in FuelType
    cc: FactValue = FactValue()  # engine cubic capacity, int
    registration_number: FactValue = FactValue()
    rto_code: FactValue = FactValue()  # e.g. "HR-26", "UP-16", "DL-9C"
    rto_location: FactValue = FactValue()  # free text city/state as printed
    manufacture_year: FactValue = FactValue()
    registration_year: FactValue = FactValue()
    vehicle_age_years: FactValue = FactValue()
    body_type: FactValue = FactValue()
    seating_capacity: FactValue = FactValue()

    ncb_percent: FactValue = FactValue()
    zero_depreciation: FactValue = FactValue()  # bool: policy carries ZD / nil-dep cover
    premium: PremiumBreakup = PremiumBreakup()

    # populated by the extraction client, not the model
    source_file: str = ""
    model_used: str = ""
    notes: list[str] = []

    def driver_confidence(self, fields: list[str]) -> float:
        """Minimum confidence across the named driver facts that are present."""
        vals = []
        for f in fields:
            fv = getattr(self, f, None)
            if isinstance(fv, FactValue) and fv.is_present():
                vals.append(fv.evidence.confidence)
        return min(vals) if vals else 0.0
