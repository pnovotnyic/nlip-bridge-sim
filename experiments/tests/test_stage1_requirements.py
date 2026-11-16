"""The requirements file is complete, verbatim, and every testable entry has a check."""
import re
from pathlib import Path

import yaml

S1 = Path(__file__).resolve().parents[1] / "stage1"


def _norm(s: str) -> str:
    s = re.sub(r"©\s*Ecma International\s*2025\s*\d*", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _reqs():
    return yaml.safe_load((S1 / "requirements.yaml").read_text())


def test_quotes_are_verbatim():
    doc = _reqs()
    texts = {k: _norm((S1 / "standards" / v["text"]).read_text()) for k, v in doc["standards"].items()}
    missing = [r["id"] for r in doc["requirements"] if _norm(r["quote"]) not in texts[r["standard"]]]
    assert not missing, missing


def test_requirement_fields():
    doc = _reqs()
    ids = [r["id"] for r in doc["requirements"]]
    assert len(ids) == len(set(ids))
    for r in doc["requirements"]:
        assert r["level"] in ("must", "shall", "should"), r["id"]
        assert r["target"] in ("message", "endpoint", "binding"), r["id"]
        assert r["testable"] in ("yes", "partly", "no"), r["id"]
        assert isinstance(r["implied"], bool) and "ambiguity" in r and r["clause"] and r["quote"]


def test_standards_checksums():
    import hashlib

    sums = dict(l.split()[::-1] for l in (S1 / "standards" / "SHA256SUMS").read_text().splitlines())
    for name, digest in sums.items():
        assert hashlib.sha256((S1 / "standards" / name).read_bytes()).hexdigest() == digest


def test_every_testable_requirement_has_a_check():
    import stage1.tests.checks_def  # noqa: F401
    from stage1.harness.checks import CHECKS

    covered = {c.req for c in CHECKS} | {r for c in CHECKS for r in c.also}
    ids = {r["id"] for r in _reqs()["requirements"]}
    assert covered <= ids, covered - ids
    missing = [r["id"] for r in _reqs()["requirements"] if r["testable"] in ("yes", "partly") and r["id"] not in covered]
    assert not missing, missing
    assert 35 <= len(CHECKS) <= 50
