"""Stage 07b (B12): size of every rendered system prompt, in tokens, on each rung's own tokenizer.

    uv run python -m nlipeval.agents.prompt_sizes R2 R3 R4 R1    # writes results/prompts/prompt_sizes.csv

One row per distinct rendered system prompt:
- server: (api, current server version) x (P1, P2, P3, NLIP-0);
- client: (api, client version) x (P1, P2, P3, NLIP-0), rendered for the first main instance of each
  (api, client version). The client prompt also holds the intent, facts and answer schema, so it varies a
  little between instances of one version; `chars_min` and `chars_max` give that spread.

Tokens are the `prompt_tokens` the endpoint reports for a `max_tokens: 1` chat call, as the harness sends it
(system prompt plus the user turn "Begin the session."), minus the same figure for a one-word system prompt.
R1 reports `prompt_eval_count` as `prompt_tokens` through Ollama's OpenAI endpoint. Columns for rungs not
measured in this call are kept from the existing file.
"""
from __future__ import annotations

import csv
import json
import sys
from concurrent.futures import ThreadPoolExecutor

import openai

from nlipeval.agents.prompts import ROOT, render_client, render_server
from nlipeval.models.adapter import ModelAdapter, _create_with_deadline, load_env
from nlipeval.runner.session import START_MESSAGE
from nlipeval.tasks.generate import VERSIONS

CSV = ROOT / "results" / "prompts" / "prompt_sizes.csv"
RUNGS = ["R1", "R2", "R3", "R4"]
VARIANTS = ["P1", "P2", "P3", "NLIP-0"]
FIELDS = ["role", "api", "version", "prompt", "chars", "chars_min", "chars_max"] + RUNGS


def _render(role: str, api: str, version: str, variant: str, task: dict | None) -> str:
    cond, pt = ("NLIP-0", "P2") if variant == "NLIP-0" else ("NLIP", variant)
    if role == "server":
        return render_server(api, version, pt, cond)
    return render_client(task, pt, cond)


def _prompt_tokens(ad: ModelAdapter, rung: str, system: str) -> int:
    client = ad._client(rung)
    c = ad.cfg[rung]
    req, _ = ad._build_request(rung, system, [{"role": "user", "content": START_MESSAGE}], None, None, 1)
    for attempt in range(3):
        try:
            return _create_with_deadline(client, req, 120).usage.prompt_tokens
        except (openai.APITimeoutError, openai.APIConnectionError, openai.InternalServerError):
            if attempt == 2:
                raise
    raise AssertionError


def _jobs() -> list[dict]:
    index = list(csv.DictReader(open(ROOT / "tasks" / "INDEX.csv")))
    jobs = []
    for api, spec in VERSIONS.items():
        for variant in VARIANTS:
            text = _render("server", api, spec["server"], variant, None)
            jobs.append(dict(role="server", api=api, version=spec["server"], prompt=variant, text=text,
                             chars=len(text), chars_min=len(text), chars_max=len(text)))
        for cv in spec["client_versions"]:
            rows = [r for r in index if r["api"] == api and r["client_version"] == cv and r["pilot"] == "False"]
            tasks = [json.loads((ROOT / "tasks" / api / f"{r['task_id']}.json").read_text()) for r in rows]
            for variant in VARIANTS:
                texts = [_render("client", api, cv, variant, t) for t in tasks]
                lens = [len(t) for t in texts]
                jobs.append(dict(role="client", api=api, version=cv, prompt=variant, text=texts[0],
                                 chars=lens[0], chars_min=min(lens), chars_max=max(lens)))
    return jobs


def measure(rungs: list[str]) -> list[dict]:
    load_env(ROOT / ".env")
    ad = ModelAdapter(ROOT / "config" / "models.yaml", ROOT / "data" / "smoke" / "sizes")
    jobs = _jobs()
    old = {(r["role"], r["api"], r["version"], r["prompt"]): r
           for r in (csv.DictReader(open(CSV)) if CSV.exists() else [])}
    for rung in rungs:
        base = _prompt_tokens(ad, rung, "x")
        with ThreadPoolExecutor(ad.cfg[rung].get("max_concurrency", 1)) as ex:
            toks = list(ex.map(lambda j, rung=rung: _prompt_tokens(ad, rung, j["text"]) - base + 1, jobs))
        for j, t in zip(jobs, toks):
            j[rung] = t
        print(rung, "measured", len(jobs), flush=True)
    rows = []
    for j in jobs:
        key = (j["role"], j["api"], j["version"], j["prompt"])
        row = {k: j.get(k) for k in FIELDS}
        for rung in RUNGS:
            if row[rung] is None and key in old:
                row[rung] = old[key].get(rung) or None
        rows.append(row)
    CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    return rows


if __name__ == "__main__":
    measure(sys.argv[1:] or RUNGS)
