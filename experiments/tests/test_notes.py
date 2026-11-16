"""P3 notes (B2): every back-quoted name or value in a version's notes exists in that version's excerpt,
and the notes never contrast with other versions."""

import json
import re
from pathlib import Path

import pytest

from nlipeval.agents.prompts import NOTES_DIR, SPECS_DIR, _load_notes

CASES = sorted((p.parent.name, p.stem) for p in NOTES_DIR.glob("*/v*.md") if not p.name.endswith(".sources.md"))
BAD_WORDS = re.compile(r"\b(earlier|later|previous|newer|older|unlike|instead of|no longer|now required|not `)", re.I)


def _present(token: str, text: str) -> bool:
    for cand in (token, json.dumps(token)[1:-1], token.lower(), f'"{token}"'):
        if cand in text:
            return True
    return False


def test_every_version_has_notes():
    from nlipeval.tasks.generate import VERSIONS
    want = {(api, v) for api in VERSIONS for v in VERSIONS[api]["client_versions"]}
    assert want <= set(CASES)
    assert len(CASES) == 14


@pytest.mark.parametrize("api,version", CASES)
def test_notes_names_exist_in_excerpt(api, version):
    excerpt = (SPECS_DIR / api / f"{version}.json").read_text(encoding="utf-8")
    notes = _load_notes(api, version)
    missing = [t for t in re.findall(r"`([^`]+)`", notes) if not _present(t, excerpt)]
    assert not missing, f"{api} {version}: names not in the excerpt: {missing}"


@pytest.mark.parametrize("api,version", CASES)
def test_notes_have_no_contrast(api, version):
    notes = _load_notes(api, version)
    assert not BAD_WORDS.search(notes), BAD_WORDS.search(notes).group(0)
    assert (NOTES_DIR / api / f"{version}.sources.md").exists()


def test_missing_notes_is_an_error():
    with pytest.raises(FileNotFoundError):
        _load_notes("L1", "v9.9.9")
