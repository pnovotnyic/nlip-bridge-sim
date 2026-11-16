"""Stage 03b: measure the prompt excerpts in tokens, on each rung's own tokenizer, in two serialisations.

    uv run python -m nlipeval.tasks.prompt_sizes R2 R3 R4 R1    # writes results/specs/prompt_excerpt_sizes.csv

Tokens are the `prompt_tokens` the endpoint reports for a one-token chat call, minus the same figure for an
empty excerpt (the chat-template overhead), so the number is the excerpt's own size. Rows already in the CSV are kept
(rungs can be measured one at a time).
"""
from __future__ import annotations

import csv
import sys
from concurrent.futures import ThreadPoolExecutor

import openai

from nlipeval.models.adapter import ModelAdapter, _create_with_deadline, load_env
from nlipeval.tasks.specs import PROMPT_DIR, RESULTS, SERIALISATIONS, VERSIONS, prompt_excerpts

ROOT = RESULTS.parents[1]
CSV = RESULTS / "prompt_excerpt_sizes.csv"
FIELDS = ["api", "version", "serialisation", "rung", "tokens"]


def _prompt_tokens(ad: ModelAdapter, rung: str, text: str) -> int:
    client = ad._client(rung)
    c = ad.cfg[rung]
    for attempt in range(3):
        try:
            req = dict(model=c["model"], messages=[{"role": "user", "content": text}], max_tokens=1,
                       **({"extra_body": c["extra_body"]} if c.get("extra_body") else {}))
            return _create_with_deadline(client, req, 120).usage.prompt_tokens
        except (openai.APITimeoutError, openai.APIConnectionError, openai.InternalServerError):
            if attempt == 2:
                raise
    raise AssertionError


def measure(rungs: list[str]) -> None:
    load_env(ROOT / ".env")
    prompt_excerpts()
    ad = ModelAdapter(ROOT / "config" / "models.yaml", ROOT / "data" / "smoke" / "sizes")
    rows = list(csv.DictReader(open(CSV))) if CSV.exists() else []
    rows = [r for r in rows if r["rung"] not in rungs]
    jobs = [(api, v, how, ext) for api, c in VERSIONS.items() for v, _, _ in c["versions"] for how, ext in SERIALISATIONS.items()]
    for rung in rungs:
        base = _prompt_tokens(ad, rung, "x")  # template overhead plus one token
        workers = ad.cfg[rung].get("max_concurrency", 1)

        def one(j, rung=rung):
            api, v, how, ext = j
            text = (PROMPT_DIR / api / f"{v}.{ext}").read_text()
            return dict(api=api, version=v, serialisation=how, rung=rung, tokens=_prompt_tokens(ad, rung, text) - base + 1)

        with ThreadPoolExecutor(workers) as ex:
            rows += list(ex.map(one, jobs))
        print(rung, "measured", len(jobs), flush=True)
        with open(CSV, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(sorted(rows, key=lambda r: (r["rung"], r["api"], r["version"], r["serialisation"])))


if __name__ == "__main__":
    measure(sys.argv[1:] or ["R1", "R2", "R3", "R4"])
