"""Live smoke tests (need network and credentials). Run with: uv run pytest -m live tests/test_models_smoke.py

They read the results written by `python -m nlipeval.models.smoke` (results/stage01/smoke_<rung>.json)
and assert that smoke tests 1-4 passed for every rung.
"""

import json
from pathlib import Path

import pytest

RES = Path(__file__).resolve().parents[1] / "results" / "stage01"


@pytest.mark.live
@pytest.mark.parametrize("rung", ["R1", "R2", "R3", "R4", "R5"])
def test_smoke_1_to_4(rung):
    p = RES / f"smoke_{rung}.json"
    if not p.exists():
        pytest.skip(f"{p.name} not produced yet")
    r = json.loads(p.read_text())
    failed = {k: v for k, v in r["tests"].items() if k[0] in "1234" and not v["pass"]}
    assert not failed, failed
