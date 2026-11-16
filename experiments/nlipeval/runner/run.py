"""Main runner: `python -m nlipeval.runner.run --matrix config/runs/<name>.yaml` (stage 06).

Reads a matrix YAML, starts the backends, runs sessions concurrently per rung, and writes
the four log files (manifest.json, sessions.jsonl, calls.jsonl, wire.jsonl).

The session key is (task_id, rung, prompt, condition, attempt). Keys already in
sessions.jsonl are skipped (resumable).

Budget guard: stops cleanly once `budget_calls` model calls have been made.
Schema warm-up: before the first real session, sends one short call per JSON schema per rung.
Scoring as you go: calls the scorer (stage 07) every 50 sessions if available.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib
import json
import os
import platform
import subprocess
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"
TASKS_DIR = ROOT / "tasks"
DATA_DIR = ROOT / "data" / "runs"
SERVING_FILE = ROOT / ".backends" / "serving.json"
RUNS_REGISTRY = ROOT / "data" / "RUNS.md"

SCHEMA_VERSION = "1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def _sha256_dir(d: Path, glob: str = "**/*") -> str:
    h = hashlib.sha256()
    for p in sorted(d.rglob("*") if glob == "**/*" else d.glob(glob)):
        if p.is_file():
            h.update(p.name.encode())
            h.update(p.read_bytes())
    return h.hexdigest()


# --------------------------------------------------------------------------- package versions

def _package_versions() -> dict[str, str]:
    try:
        from importlib.metadata import packages_distributions, version
        pkgs = {}
        for name in ("openai", "httpx", "fastapi", "uvicorn", "jsonschema", "yaml", "openapi_core"):
            try:
                pkgs[name] = version(name)
            except Exception:
                pkgs[name] = "unknown"
        return pkgs
    except Exception:
        return {}


# --------------------------------------------------------------------------- task loading

def _parts(matrix: dict) -> list[dict]:
    """A matrix is one part, or a list of `parts`, each with its own task_filter, rungs, prompts, conditions."""
    return matrix.get("parts") or [matrix]


def _load_tasks(matrix: dict) -> list[dict]:
    """Load task instances matching the matrix filter (the union over its parts)."""
    out: dict[str, dict] = {}
    for part in _parts(matrix):
        for t in _load_part_tasks(part, bool(matrix.get("allow_round_b", False))):
            out[t["task_id"]] = t
    return list(out.values())


def _load_part_tasks(matrix: dict, allow_round_b: bool) -> list[dict]:
    task_filter = matrix.get("task_filter", {})
    apis = task_filter.get("apis") or ["L1", "L2", "L3"]
    client_versions = task_filter.get("client_versions")   # list, or a dict api -> list
    pilot_only = task_filter.get("pilot_only", False)
    main_only = task_filter.get("main_only", False)
    intent_ids = task_filter.get("intent_ids")
    pilot_round = task_filter.get("pilot_round")          # "A" | "B" | None
    per_api_limit = task_filter.get("per_api_limit")      # max intents per API (first in sorted order)

    tasks = []
    for api in apis:
        cv_api = client_versions.get(api) if isinstance(client_versions, dict) else client_versions
        seen_intents: list[str] = []
        for p in sorted((TASKS_DIR / api).glob("*.json")):
            task = json.loads(p.read_text())
            if pilot_round and task.get("pilot_round") != pilot_round:
                continue
            if cv_api and task["client_version"] not in cv_api:
                continue
            if pilot_only and not task.get("pilot"):
                continue
            if main_only and task.get("pilot"):
                continue
            if intent_ids and task["intent_id"] not in intent_ids:
                continue
            if per_api_limit is not None:
                if task["intent_id"] not in seen_intents:
                    if len(seen_intents) >= per_api_limit:
                        continue
                    seen_intents.append(task["intent_id"])
            tasks.append(task)
    if not allow_round_b and any(t.get("pilot_round") == "B" for t in tasks):
        raise SystemExit("Round-B tasks are reserved: the matrix needs allow_round_b: true "
                         "(only stage 08 step 5 sets it).")
    return tasks


# --------------------------------------------------------------------------- R1 pre-flight check

def _check_r1_serving(cfg_rungs: dict) -> dict:
    """Verify that the R1 Ollama instance matches the frozen config and is loaded."""
    if not SERVING_FILE.exists():
        raise SystemExit(
            f"R1 pre-flight: {SERVING_FILE} does not exist. "
            "Run scripts/start_ollama_r1.sh first."
        )
    serving = json.loads(SERVING_FILE.read_text())
    r1_cfg = cfg_rungs.get("R1", {})
    expected = r1_cfg.get("serving", {})
    actual = serving.get("variables", {})
    mismatches = {k: (expected[k], actual.get(k)) for k in expected if actual.get(k) != expected[k]}
    if mismatches:
        raise SystemExit(f"R1 serving mismatch: {mismatches}")

    # check `ollama ps` for the model
    model_name = r1_cfg.get("model", "nlip-qwen3-4b")
    ollama_ps = serving.get("ollama_ps", "")
    if model_name not in ollama_ps:
        raise SystemExit(
            f"R1 pre-flight: model {model_name!r} not found in ollama ps output:\n{ollama_ps}"
        )
    if "65536" not in ollama_ps:
        raise SystemExit(
            f"R1 pre-flight: context 65536 not found in ollama ps output:\n{ollama_ps}"
        )
    return serving


# --------------------------------------------------------------------------- session key

def _session_key(task_id: str, rung: str, prompt: str, condition: str, attempt: int) -> str:
    return f"{task_id}|{rung}|{prompt}|{condition}|{attempt}"


def _load_done_keys(sessions_path: Path) -> set[str]:
    done = set()
    if not sessions_path.exists():
        return done
    for line in sessions_path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
            key = _session_key(
                rec["task_id"], rec["client_rung"], rec["prompt"],
                rec["condition"], rec["attempt"]
            )
            done.add(key)
        except Exception:
            pass
    return done


# --------------------------------------------------------------------------- logging helpers

class _Logger:
    """Thread-safe append-to-jsonl with a lock."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()

    def write(self, record: dict) -> None:
        line = json.dumps({"schema_version": SCHEMA_VERSION, **record}, ensure_ascii=False)
        with self._lock, open(self.path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def write_many(self, records: list[dict]) -> None:
        lines = [json.dumps({"schema_version": SCHEMA_VERSION, **r}, ensure_ascii=False) for r in records]
        with self._lock, open(self.path, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")


# --------------------------------------------------------------------------- budget guard

class _Budget:
    def __init__(self, limit: int) -> None:
        self._limit = limit
        self._used = 0
        self._lock = threading.Lock()

    def consume(self, n: int = 1) -> bool:
        """Returns True if budget is still available after consumption."""
        with self._lock:
            self._used += n
            return self._used <= self._limit

    @property
    def exhausted(self) -> bool:
        with self._lock:
            return self._used >= self._limit


# --------------------------------------------------------------------------- schema warm-up

def _warmup(adapter: Any, rungs: list[str], answer_schemas: list[dict]) -> None:
    """Send one short call per schema per rung to prime JSON schema compilation."""
    from nlipeval.agents.schemas import CLIENT_SCHEMA, SERVER_SCHEMA

    schemas = [CLIENT_SCHEMA, SERVER_SCHEMA] + answer_schemas
    warmup_msg = [{"role": "user", "content": "Reply with an empty JSON object: {}"}]
    for rung in rungs:
        for schema in schemas:
            try:
                adapter.call(
                    rung, "Warm-up call.", warmup_msg,
                    schema=schema, purpose="warmup", session_id="warmup",
                )
            except Exception:
                pass  # warm-up failures are non-fatal


# --------------------------------------------------------------------------- session runner

def _run_one(
    task: dict,
    rung: str,
    prompt: str,
    condition: str,
    attempt: int,
    run_id: str,
    adapter: Any,
    backend_urls: dict[str, str],
    cfg_rungs: dict,
    wall_time_limit_s: float,
) -> tuple[dict, list[dict]]:
    """Run one session and return (session_record, wire_records)."""
    from nlipeval.agents.client import ClientAgent
    from nlipeval.agents.prompts import render_client, render_server
    from nlipeval.agents.server import ServerAgent
    from nlipeval.runner.session import SessionConfig, run_session

    api = task["api"]
    server_version = task["server_version"]

    client_system = render_client(task, prompt, condition)
    server_system = render_server(api, server_version, prompt, condition)

    max_call = getattr(adapter, "max_call_seconds", None)
    nlip_http_timeout_s = (max_call(rung) + 30.0) if max_call else 60.0

    def _play(limit_s: float):
        session_id = str(uuid.uuid4())
        client_agent = ClientAgent(adapter, rung, client_system, session_id)
        server_agent = ServerAgent(adapter, rung, server_system, session_id)
        cfg = SessionConfig(
            rung=rung,
            prompt=prompt,
            condition=condition,
            attempt=attempt,
            run_id=run_id,
            client_agent=client_agent,
            server_agent=server_agent,
            backend_urls=backend_urls,
            wall_time_limit_s=limit_s,
            session_id=session_id,
            nlip_http_timeout_s=nlip_http_timeout_s,
            price_per_million=cfg_rungs.get(rung, {}).get("price_usd_per_million"),
        )
        return cfg, run_session(task, cfg)

    cfg, outcome = _play(wall_time_limit_s)
    timeout_rerun = None
    if outcome.termination == "timeout":
        # B8: a session timeout is re-run once with twice the limit; a second timeout stays a failure.
        timeout_rerun = {"first_session_id": outcome.session_id, "first_limit_s": wall_time_limit_s,
                         "first_wall_seconds": outcome.wall_seconds, "limit_s": 2 * wall_time_limit_s}
        cfg, outcome = _play(2 * wall_time_limit_s)

    # compute cost for R5
    cost_usd = None
    price = cfg.price_per_million
    if price and outcome.tokens:
        inp = outcome.tokens.get("client_in") or 0 + (outcome.tokens.get("server_in") or 0)
        out = outcome.tokens.get("client_out") or 0 + (outcome.tokens.get("server_out") or 0)
        cost_usd = (inp * price.get("input", 0) + out * price.get("output", 0)) / 1_000_000

    session_record = {
        "run_id": run_id,
        "session_id": outcome.session_id,
        "attempt": attempt,
        "task_id": task["task_id"],
        "api": task["api"],
        "operation": task["operation"],
        "client_version": task["client_version"],
        "server_version": task["server_version"],
        "versions_behind": task["versions_behind"],
        "breaking_crossed": task["breaking_crossed"],
        "change_tags_request": task.get("change_tags_request", []),
        "change_tags_response": task.get("change_tags_response", []),
        "pilot": task["pilot"],
        "client_rung": rung,
        "server_rung": rung,
        "prompt": prompt,
        "condition": condition,
        "started_utc": outcome.started_utc,
        "ended_utc": outcome.ended_utc,
        "wall_seconds": outcome.wall_seconds,
        "termination": outcome.termination,
        "n_interactions": outcome.n_interactions,
        "n_questions": outcome.n_questions,
        "n_corrections": outcome.n_corrections,
        "n_restatements": outcome.n_restatements,
        "n_server_retries": outcome.n_server_retries,
        "n_protocol_slips": outcome.n_protocol_slips,
        "timeout_rerun": timeout_rerun,
        "plans": [
            {"turn": p.turn, "action": p.action,
             "plan": p.plan, "asked_fields": p.asked_fields, "client_reply": p.client_reply}
            for p in outcome.plans
        ],
        "executed_calls": [
            {"method": e.method, "path": e.path, "body": e.body,
             "status": e.status, "response_body": e.response_body, "ts": e.ts}
            for e in outcome.executed_calls
        ],
        "client_final": outcome.client_final,
        "calls_client": outcome.calls_client,
        "calls_server": outcome.calls_server,
        "tokens": outcome.tokens,
        "cost_usd": cost_usd,
        "errors": outcome.errors,
    }

    wire_records = [
        {**rec, "run_id": run_id}
        for rec in outcome.wire_log
    ]

    return session_record, wire_records


# --------------------------------------------------------------------------- main

def run(matrix_path: Path, dry_run: bool = False) -> None:
    matrix = yaml.safe_load(matrix_path.read_text())
    run_id = matrix.get("run_id") or (
        datetime.now(timezone.utc).strftime("%Y%m%d-%H%M") + "-stage6-" + matrix.get("label", "run")
    )

    cfg_rungs = yaml.safe_load((CONFIG_DIR / "models.yaml").read_text())["rungs"]
    parts = _parts(matrix)
    rungs = sorted({r for part in parts for r in part.get("rungs", matrix.get("rungs", []))})
    prompts_list = sorted({x for part in parts for x in part.get("prompts", ["P2"])})
    conditions = sorted({x for part in parts for x in part.get("conditions", ["NLIP", "NLIP-0"])})
    attempt = matrix.get("attempt", 1)
    concurrency_per_rung = matrix.get("concurrency", {r: cfg_rungs[r].get("max_concurrency", 1) for r in rungs})
    budget_calls = matrix.get("budget_calls", 10_000)
    matrix_limit_s = matrix.get("wall_time_limit_s")      # optional override of the per-rung session_limit_s
    stage = matrix.get("stage", "stage6")

    # R5 guard
    if "R5" in rungs and stage != "stage14":
        raise SystemExit("R5 is only allowed in stage 14 runs. Set stage: stage14 in the matrix file.")

    # R1 pre-flight
    serving_info: dict | None = None
    if "R1" in rungs:
        serving_info = _check_r1_serving(cfg_rungs)

    run_dir = DATA_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # load env
    from nlipeval.models.adapter import ModelAdapter, load_env
    load_env(ROOT / ".env")

    adapter = ModelAdapter(CONFIG_DIR / "models.yaml", run_dir)

    # load tasks
    tasks = _load_tasks(matrix)
    if not tasks:
        raise SystemExit("No tasks matched the filter.")

    # collect backend URLs
    backend_state_file = ROOT / ".backends" / "state.json"
    if backend_state_file.exists():
        bs = json.loads(backend_state_file.read_text())
        backend_urls = {api: p["url"] for api, p in bs.get("processes", {}).items()}
    else:
        # start backends
        from nlipeval.backends.launcher import up
        procs = up("127.0.0.1", None, run_dir)
        backend_urls = {api: p["url"] for api, p in procs.items()}

    # collect unique answer schemas for warm-up
    answer_schemas: list[dict] = []
    seen_schemas: set[str] = set()
    for t in tasks:
        s = t.get("client_answer_schema")
        if s:
            key = json.dumps(s, sort_keys=True)
            if key not in seen_schemas:
                seen_schemas.add(key)
                answer_schemas.append(s)

    # write manifest
    from nlipeval.agents.prompts import prompts_hash
    manifest = {
        "run_id": run_id,
        "stage": stage,
        "created_utc": _utc_now(),
        "git_commit": _git_commit(),
        "config_hash": _sha256_dir(CONFIG_DIR),
        "prompts_hash": prompts_hash(),
        "tasks_hash": _sha256_dir(TASKS_DIR),
        "world_hash": _sha256_dir(CONFIG_DIR / "world"),
        "specs_hash": _sha256_dir(ROOT / "specs"),
        "models": {r: {
            "provider": cfg_rungs[r]["provider"],
            "model": cfg_rungs[r]["model"],
            "params": cfg_rungs[r].get("params"),
            "structured_output_mode": cfg_rungs[r].get("structured_output_mode"),
        } for r in rungs},
        "matrix": matrix,
        "budget_calls": budget_calls,
        "host": platform.node(),
        "python_version": sys.version,
        "packages": _package_versions(),
        "serving": serving_info,
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

    if dry_run:
        n = sum(len(_load_part_tasks(pt, bool(matrix.get("allow_round_b", False)))) * len(pt.get("rungs", matrix.get("rungs", []))) * len(pt.get("prompts", ["P2"])) * len(pt.get("conditions", ["NLIP", "NLIP-0"])) for pt in parts)
        print(f"Dry run: {run_id}, {len(tasks)} tasks, {n} sessions, rungs {rungs}")
        return

    sessions_log = _Logger(run_dir / "sessions.jsonl")
    wire_log = _Logger(run_dir / "wire.jsonl")
    budget = _Budget(budget_calls)
    done_keys = _load_done_keys(run_dir / "sessions.jsonl")
    completed_since_score = [0]
    lock = threading.Lock()

    # schema warm-up
    print(f"[{run_id}] warming up {len(rungs)} rungs × {2 + len(answer_schemas)} schemas…")
    _warmup(adapter, rungs, answer_schemas)

    # build session list
    sessions_to_run: list[tuple] = []
    queued: set[str] = set()
    for part in parts:
        part_tasks = _load_part_tasks(part, bool(matrix.get("allow_round_b", False)))
        for t in part_tasks:
            for rung in part.get("rungs", matrix.get("rungs", [])):
                # R1 always at concurrency 1; we ensure this via the semaphore in adapter
                for prompt in part.get("prompts", ["P2"]):
                    for cond in part.get("conditions", ["NLIP", "NLIP-0"]):
                        key = _session_key(t["task_id"], rung, prompt, cond, attempt)
                        if key not in done_keys and key not in queued:
                            queued.add(key)
                            sessions_to_run.append((t, rung, prompt, cond, attempt))

    total = len(sessions_to_run)
    print(f"[{run_id}] {total} sessions to run ({len(done_keys)} already done)…")
    done_count = [0]

    def _work(item: tuple) -> None:
        if budget.exhausted:
            return
        t, rung, prompt, cond, att = item
        try:
            rec, wires = _run_one(
                t, rung, prompt, cond, att, run_id, adapter,
                backend_urls, cfg_rungs,
                matrix_limit_s or cfg_rungs[rung].get("session_limit_s", 1200.0),
            )
        except Exception as e:
            # harness-level failures are still recorded
            rec = {
                "run_id": run_id, "session_id": str(uuid.uuid4()), "attempt": att,
                "task_id": t["task_id"], "api": t["api"], "operation": t["operation"],
                "client_version": t["client_version"], "server_version": t["server_version"],
                "versions_behind": t["versions_behind"], "breaking_crossed": t["breaking_crossed"],
                "change_tags_request": [], "change_tags_response": [], "pilot": t["pilot"],
                "client_rung": rung, "server_rung": rung, "prompt": prompt, "condition": cond,
                "started_utc": _utc_now(), "ended_utc": _utc_now(), "wall_seconds": 0.0,
                "termination": "error_harness",
                "n_interactions": 0, "n_questions": 0, "n_corrections": 0,
                "n_restatements": 0, "n_server_retries": 0, "n_protocol_slips": 0, "timeout_rerun": None,
                "plans": [], "executed_calls": [], "client_final": None,
                "calls_client": 0, "calls_server": 0,
                "tokens": {"client_in": None, "client_out": None,
                           "server_in": None, "server_out": None, "reasoning": None},
                "cost_usd": None, "errors": [f"harness exception: {e}"],
            }
            wires = []
        sessions_log.write(rec)
        if wires:
            wire_log.write_many(wires)

        budget.consume(rec.get("calls_client", 0) + rec.get("calls_server", 0))
        with lock:
            done_count[0] += 1
            completed_since_score[0] += 1
            n = done_count[0]
            if n % 10 == 0 or n == total:
                elapsed = time.monotonic()
                rate = n / max(elapsed - 1, 1)
                eta = (total - n) / max(rate, 0.001)
                print(f"  [{run_id}] {n}/{total} done  rate={rate:.1f}/s  ETA={eta/60:.0f}min")
            if completed_since_score[0] >= 50 or n == total:
                completed_since_score[0] = 0
                _try_score(run_dir)

    # dispatch with per-rung concurrency
    # Group sessions by rung to control concurrency
    from concurrent.futures import ThreadPoolExecutor
    rung_sessions: dict[str, list] = {r: [] for r in rungs}
    for item in sessions_to_run:
        rung_sessions[item[1]].append(item)

    futures = []
    executors: list[ThreadPoolExecutor] = []
    for rung in rungs:
        conc = concurrency_per_rung.get(rung, cfg_rungs.get(rung, {}).get("max_concurrency", 1))
        ex = ThreadPoolExecutor(max_workers=conc, thread_name_prefix=f"rung-{rung}")
        executors.append(ex)
        for item in rung_sessions[rung]:
            futures.append(ex.submit(_work, item))

    for f in as_completed(futures):
        f.result()  # re-raise exceptions

    for ex in executors:
        ex.shutdown(wait=True)

    print(f"[{run_id}] done. Sessions: {done_count[0]}. Run dir: {run_dir}")
    _update_runs_registry(run_id, run_dir, stage, done_count[0])


def _try_score(run_dir: Path) -> None:
    try:
        scorer = importlib.import_module("nlipeval.scoring.score")
        scorer.score_incremental(run_dir)
    except Exception:
        pass  # scorer not yet implemented (stage 07)


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except Exception:
        return None


def _update_runs_registry(run_id: str, run_dir: Path, stage: str, n_sessions: int) -> None:
    RUNS_REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    sessions_path = run_dir / "sessions.jsonl"
    calls_path = run_dir / "calls.jsonl"
    sha_sessions = _sha256_file(sessions_path) if sessions_path.exists() else ""
    sha_calls = _sha256_file(calls_path) if calls_path.exists() else ""
    commit = _git_commit() or "unknown"
    row = (
        f"| {run_id} | {stage} | {_utc_now()[:10]} | {commit[:7]} "
        f"| {'smoke' if stage == 'smoke' else 'valid'} | {n_sessions} | {sha_sessions[:8]} | {sha_calls[:8]} |\n"
    )
    if not RUNS_REGISTRY.exists():
        RUNS_REGISTRY.write_text(
            "# Run registry\n\n"
            "| run_id | stage | date | git_commit | status | sessions | sha_sessions | sha_calls |\n"
            "|--------|-------|------|-----------|--------|----------|-------------|----------|\n"
        )
    with open(RUNS_REGISTRY, "a") as f:
        f.write(row)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--matrix", required=True, type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    run(args.matrix, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
