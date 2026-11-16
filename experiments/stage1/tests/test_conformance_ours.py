"""Our implementation passes every conformance check (the reference implementations are run by run_suite.py)."""
import pytest

import stage1.tests.checks_def  # noqa: F401
from stage1.harness.adapters import build_impls
from stage1.harness.checks import CHECKS
from stage1.harness.run_suite import run_one


@pytest.fixture(scope="module")
def ours():
    impls = build_impls(["ours"])
    yield impls[0]
    for i in impls:
        i.close()


@pytest.mark.parametrize("chk", CHECKS, ids=[c.id for c in CHECKS])
def test_ours_passes(ours, chk):
    outcome, detail = run_one(ours, chk)
    assert outcome == "pass", f"{chk.id} {chk.req}: {outcome} {detail}"
