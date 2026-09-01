import json
from pathlib import Path

import pytest

from app.extraction.client import facts_from_payload
from app.pipeline import build_output

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def load_facts(name: str):
    payload = json.loads((FIXTURE_DIR / f"{name}.json").read_text())
    return facts_from_payload(payload, f"{name}.pdf", "fixture")


@pytest.fixture
def analyze():
    def _run(name: str):
        return build_output(load_facts(name))
    return _run
