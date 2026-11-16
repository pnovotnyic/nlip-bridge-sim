"""Launcher for the three mock backends (stage 04).

    uv run python -m nlipeval.backends.launcher up   [--run-dir DIR] [--base-port N] [--host H]
    uv run python -m nlipeval.backends.launcher down
    uv run python -m nlipeval.backends.launcher status

`up` starts L1, L2 and L3 as separate processes (ports from config/world/service.yaml, or --base-port,
--base-port+1, --base-port+2), waits until all three answer, and records the process IDs in
`.backends/state.json`. `down` stops them. Every request is logged to `<run-dir>/backend.jsonl`.

One process in the foreground: `python -m nlipeval.backends.launcher serve L2 --port 9102 --run-dir DIR`.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import httpx
import uvicorn

from nlipeval.backends.world import ROOT, World

STATE_FILE = ROOT / ".backends" / "state.json"
APIS = ("L1", "L2", "L3")


def make_app(api: str, run_dir: Path | None, world: World | None = None):
    if api == "L1":
        from nlipeval.backends.l1_reachability import make_backend
    elif api == "L2":
        from nlipeval.backends.l2_location import make_backend
    elif api == "L3":
        from nlipeval.backends.l3_qod import make_backend
    else:
        raise SystemExit(f"unknown API {api}")
    return make_backend(world, run_dir).build_app()


def serve(api: str, host: str, port: int, run_dir: Path | None) -> None:
    uvicorn.run(make_app(api, run_dir), host=host, port=port, log_level="warning")


def _ports(base_port: int | None) -> dict[str, int]:
    if base_port is not None:
        return {api: base_port + i for i, api in enumerate(APIS)}
    return World().ports


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def up(host: str, base_port: int | None, run_dir: Path | None, timeout: float = 30.0) -> dict:
    if STATE_FILE.exists():
        old = json.loads(STATE_FILE.read_text())
        if any(_alive(p["pid"]) for p in old["processes"].values()):
            raise SystemExit("backends are already running; run `down` first")
    ports = _ports(base_port)
    procs: dict[str, dict] = {}
    for api in APIS:
        cmd = [sys.executable, "-m", "nlipeval.backends.launcher", "serve", api, "--host", host,
               "--port", str(ports[api])]
        if run_dir:
            cmd += ["--run-dir", str(run_dir)]
        p = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             start_new_session=True)
        procs[api] = {"pid": p.pid, "port": ports[api], "url": f"http://{host}:{ports[api]}"}
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({"host": host, "run_dir": str(run_dir) if run_dir else None,
                                      "processes": procs}, indent=2))
    deadline = time.time() + timeout
    pending = set(APIS)
    while pending and time.time() < deadline:
        for api in list(pending):
            try:
                if httpx.get(procs[api]["url"] + "/__admin/health", timeout=1.0).status_code == 200:
                    pending.discard(api)
            except httpx.HTTPError:
                pass
        time.sleep(0.2)
    if pending:
        down()
        raise SystemExit(f"backends did not start in {timeout:.0f} s: {sorted(pending)}")
    return procs


def down() -> list[str]:
    if not STATE_FILE.exists():
        return []
    state = json.loads(STATE_FILE.read_text())
    stopped = []
    for api, p in state["processes"].items():
        if _alive(p["pid"]):
            try:
                os.killpg(p["pid"], signal.SIGTERM)
            except OSError:
                os.kill(p["pid"], signal.SIGTERM)
            stopped.append(api)
    deadline = time.time() + 10
    while time.time() < deadline and any(_alive(p["pid"]) for p in state["processes"].values()):
        time.sleep(0.1)
    for p in state["processes"].values():
        if _alive(p["pid"]):
            os.kill(p["pid"], signal.SIGKILL)
    STATE_FILE.unlink(missing_ok=True)
    return stopped


def status() -> dict:
    if not STATE_FILE.exists():
        return {}
    state = json.loads(STATE_FILE.read_text())
    return {api: {**p, "alive": _alive(p["pid"])} for api, p in state["processes"].items()}


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("up", "serve"):
        s = sub.add_parser(name)
        s.add_argument("--host", default="127.0.0.1")
        s.add_argument("--run-dir", type=Path, default=None, help="directory that receives backend.jsonl")
        if name == "up":
            s.add_argument("--base-port", type=int, default=None)
        else:
            s.add_argument("api", choices=APIS)
            s.add_argument("--port", type=int, required=True)
    sub.add_parser("down")
    sub.add_parser("status")
    a = ap.parse_args(argv)
    if a.cmd == "up":
        for api, p in up(a.host, a.base_port, a.run_dir).items():
            print(f"{api}  {p['url']}  pid {p['pid']}")
    elif a.cmd == "serve":
        serve(a.api, a.host, a.port, a.run_dir)
    elif a.cmd == "down":
        print("stopped: " + (", ".join(down()) or "nothing running"))
    else:
        print(json.dumps(status(), indent=2))


if __name__ == "__main__":
    main()
