"""Deterministic resolver contract: types shared by every insurer module.

The resolver is intentionally *not* an LLM. Given ``PolicyFacts`` and a compiled
rulepack it walks an explicit, ordered pipeline. Every lookup appends a
``TraceStep`` carrying the exact ``Citation`` (file + sheet + cell/range, or
file + page + row) and the raw value read. A step that cannot find a match does
not guess: it raises ``Unresolvable`` with a status of ``unsupported`` or
``ambiguous`` and a human reason.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

Status = Literal["resolved", "unsupported", "ambiguous"]
ConfidenceLevel = Literal["high", "medium", "low"]


@dataclass
class Citation:
    source: str  # file name, e.g. "Reliance Broking Premier  FEB 26 Grid.xlsx"
    locator: str  # "PRIVATE CAR COMP, SAOD & STP!C11"  or  "page 1"  or "page 1, table row 4"
    kind: Literal["xlsx", "pdf", "policy"] = "xlsx"
    value: Optional[object] = None  # the raw value read at that locator
    note: str = ""

    def as_dict(self) -> dict:
        return {
            "source": self.source,
            "locator": self.locator,
            "kind": self.kind,
            "value": self.value,
            "note": self.note,
        }


@dataclass
class TraceStep:
    step: int
    title: str
    detail: str
    citations: list[Citation] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "step": self.step,
            "title": self.title,
            "detail": self.detail,
            "citations": [c.as_dict() for c in self.citations],
        }


@dataclass
class RateComponent:
    applicable: bool
    percent: Optional[float] = None
    basis: str = ""  # e.g. "OD premium", "Net premium"
    note: str = ""

    def as_dict(self) -> dict:
        return {
            "applicable": self.applicable,
            "percent": self.percent,
            "basis": self.basis,
            "note": self.note,
        }


@dataclass
class ResolverResult:
    status: Status
    insurer: str
    grid_file: str
    od: RateComponent
    tp: RateComponent
    trace: list[TraceStep]
    citations: list[Citation]
    confidence_level: ConfidenceLevel
    confidence_reason: str
    reason: str = ""  # populated for unsupported / ambiguous
    clarifying_question: Optional[str] = None
    candidates: list[dict] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "status": self.status,
            "insurer": self.insurer,
            "grid_file": self.grid_file,
            "rates": {"od": self.od.as_dict(), "tp": self.tp.as_dict()},
            "trace": [s.as_dict() for s in self.trace],
            "citations": [c.as_dict() for c in self.citations],
            "confidence": {
                "level": self.confidence_level,
                "reason": self.confidence_reason,
            },
            "reason": self.reason,
            "clarifying_question": self.clarifying_question,
            "candidates": self.candidates,
        }


class Unresolvable(Exception):
    """Raised by a resolver step when the evidence cannot support an answer."""

    def __init__(
        self,
        status: Status,
        reason: str,
        *,
        clarifying_question: Optional[str] = None,
        candidates: Optional[list[dict]] = None,
    ):
        super().__init__(reason)
        self.status = status
        self.reason = reason
        self.clarifying_question = clarifying_question
        self.candidates = candidates or []


class TraceBuilder:
    def __init__(self) -> None:
        self._steps: list[TraceStep] = []
        self._citations: list[Citation] = []

    def add(self, title: str, detail: str, citations: Optional[list[Citation]] = None) -> None:
        cites = citations or []
        self._steps.append(TraceStep(len(self._steps) + 1, title, detail, cites))
        self._citations.extend(cites)

    @property
    def steps(self) -> list[TraceStep]:
        return self._steps

    @property
    def citations(self) -> list[Citation]:
        return self._citations
