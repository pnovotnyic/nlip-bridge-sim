"""One adapter for all five models (R1-R5).

`ModelAdapter.call(rung, system, messages, schema=None, purpose=..., session_id=...)` returns a
`Result`. Every call is written to `calls.jsonl` (data contract 2.3); system prompts are stored once
by hash in `prompts/<hash>.txt` next to it. Responses are cached on disk by the SHA-256 of
(rung, model, request, schema, mode, attempt), so resumed runs do not repeat calls. API keys are
read from the environment and never logged.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import jsonschema
import openai
import yaml
from openai import OpenAI

SCHEMA_VERSION = "1"
MAX_ATTEMPTS = 4  # HTTP tries per call (1 try + 3 retries)
FIRST_ATTEMPT_TIMEOUT_S = 120  # first try only; later tries use the rung's timeout_s (stage 03b)
RETRY_BASE_DELAY_S = 2.0
STRUCTURED_MODES = ("json_schema", "json_object", "prompt")
_ENV_REF = re.compile(r"\$\{([A-Z0-9_]+)\}")

SCHEMA_INSTRUCTION = (
    "\n\nReply with a single JSON object that is valid against the JSON Schema below, "
    "and nothing else (no prose, no code fences).\nJSON Schema:\n"
)
REPAIR_TEMPLATE = (
    "Your last reply was not valid against this schema: {problem}; "
    "reply again with valid JSON only"
)


def load_env(path: str | Path) -> None:
    """Load KEY=VALUE lines into os.environ (existing variables win)."""
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


def _create_with_deadline(client: OpenAI, req: dict, timeout_s: float):
    """`chat.completions.create` with a wall-clock limit. The client's own timeout applies to each
    socket read, so a server that stalls or trickles bytes can hold a call open without limit; this
    bounds the whole try and reports it as an `APITimeoutError` (retried like any other timeout)."""
    box: dict[str, Any] = {}

    def work() -> None:
        try:
            box["resp"] = client.chat.completions.create(**req, timeout=timeout_s)
        except BaseException as e:  # noqa: BLE001 - re-raised in the caller's thread
            box["exc"] = e

    t = threading.Thread(target=work, daemon=True)
    t.start()
    t.join(timeout_s + 5)
    if t.is_alive():
        raise openai.APITimeoutError(request=httpx.Request("POST", str(client.base_url)))
    if "exc" in box:
        raise box["exc"]
    return box["resp"]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _ms(t0: float) -> int:
    return int((time.monotonic() - t0) * 1000)


def _sha256(obj: Any) -> str:
    data = obj if isinstance(obj, str) else json.dumps(obj, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def extract_json(text: str) -> Any:
    """Parse JSON from a reply; tolerate <think> blocks and code fences."""
    t = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    m = re.match(r"^```(?:json)?\s*(.*?)\s*```$", t, flags=re.S)
    if m:
        t = m.group(1)
    return json.loads(t)


def reasoning_of(msg: Any) -> str | None:
    """Reasoning text an endpoint returns outside `content` (Ollama `reasoning`, vLLM `reasoning_content`)."""
    for name in ("reasoning_content", "reasoning"):
        v = getattr(msg, name, None)
        if v is None and isinstance(getattr(msg, "model_extra", None), dict):
            v = msg.model_extra.get(name)
        if isinstance(v, str) and v:
            return v
    return None


@dataclass
class Result:
    text: str = ""
    reasoning_text: str | None = None
    parsed: Any = None
    parse_ok: bool | None = None  # None when no schema was requested
    usage: dict = field(default_factory=lambda: {
        "prompt_tokens": None, "completion_tokens": None, "reasoning_tokens": None})
    latency_ms: int = 0
    http_status: int | None = None
    retries: int = 0
    error: str | None = None
    error_type: str | None = None  # refusal | timeout | connection | http_<code> | parse_failure
    cached: bool = False
    call_index: int | None = None
    repair_calls: int = 0
    attempts: list = field(default_factory=list)
    rung: str = ""
    model: str = ""

    @property
    def ok(self) -> bool:
        return self.error is None and self.parse_ok is not False


class ModelAdapter:
    def __init__(self, config_path: str | Path, log_dir: str | Path,
                 cache_dir: str | Path | None = None, retry_base_delay_s: float = RETRY_BASE_DELAY_S):
        self.cfg = yaml.safe_load(Path(config_path).read_text())["rungs"]
        self.log_dir = Path(log_dir)
        (self.log_dir / "prompts").mkdir(parents=True, exist_ok=True)
        self.cache_dir = Path(cache_dir) if cache_dir else self.log_dir / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.calls_path = self.log_dir / "calls.jsonl"
        self.retry_base_delay_s = retry_base_delay_s
        self._clients: dict[str, OpenAI] = {}
        self._sems = {r: threading.BoundedSemaphore(c.get("max_concurrency", 1)) for r, c in self.cfg.items()}
        self._lock = threading.Lock()
        self._counters: dict[str, int] = {}

    # ------------------------------------------------------------------ clients
    def _client(self, rung: str) -> OpenAI:
        with self._lock:
            if rung not in self._clients:
                c = self.cfg[rung]
                base_url = os.environ.get(c["base_url_env"], "")
                if not base_url:
                    raise RuntimeError(f"{c['base_url_env']} is not set (needed for {rung})")
                key = os.environ.get(c["api_key_env"], "") if c.get("api_key_env") else "ollama"
                if not key:
                    raise RuntimeError(f"{c['api_key_env']} is not set (needed for {rung})")
                headers = {k: _ENV_REF.sub(lambda m: os.environ.get(m.group(1), ""), v)
                           for k, v in (c.get("headers") or {}).items()}
                self._clients[rung] = OpenAI(base_url=base_url, api_key=key, default_headers=headers,
                                             max_retries=0, timeout=c.get("timeout_s", 300))
            return self._clients[rung]

    # ------------------------------------------------------------------ request building
    def _build_request(self, rung: str, system: str, messages: list[dict], schema: dict | None,
                       mode: str | None, max_tokens: int | None) -> tuple[dict, str]:
        c = self.cfg[rung]
        sys_text = system
        if schema is not None and mode in ("json_object", "prompt"):
            sys_text = system + SCHEMA_INSTRUCTION + json.dumps(schema)
        msgs = [dict(m) for m in messages]
        if c.get("system_role_supported", True):
            msgs = [{"role": "system", "content": sys_text}] + msgs
        else:  # chat template without a system role: prepend to the first user message
            for m in msgs:
                if m["role"] == "user":
                    m["content"] = sys_text + "\n\n" + m["content"]
                    break
        req: dict[str, Any] = {"model": c["model"], "messages": msgs, **(c.get("params") or {})}
        if max_tokens is not None:
            req["max_tokens"] = max_tokens
        if schema is not None and mode == "json_schema":
            req["response_format"] = {"type": "json_schema",
                                      "json_schema": {"name": "response", "schema": schema}}
        elif schema is not None and mode == "json_object":
            req["response_format"] = {"type": "json_object"}
        if c.get("extra_body"):
            req["extra_body"] = dict(c["extra_body"])
        return req, sys_text

    def max_call_seconds(self, rung: str) -> float:
        """Worst-case seconds one `call()` can take: every HTTP try times out, with the back-off between
        tries, and then the repair call does the same (B9). The NLIP HTTP timeout is this plus 30 s."""
        rung_timeout = self.cfg[rung].get("timeout_s", 300)
        one = (min(FIRST_ATTEMPT_TIMEOUT_S, rung_timeout) + (MAX_ATTEMPTS - 1) * rung_timeout
               + sum(self.retry_base_delay_s * (2 ** i) for i in range(MAX_ATTEMPTS - 1)))
        return 2 * one

    # ------------------------------------------------------------------ cache
    def _cache_key(self, rung: str, req: dict, schema: dict | None, mode: str | None, attempt: int) -> str:
        return _sha256({"rung": rung, "model": self.cfg[rung]["model"], "request": req,
                        "schema": schema, "mode": mode, "attempt": attempt})

    def _cache_get(self, key: str) -> dict | None:
        p = self.cache_dir / f"{key}.json"
        if not p.exists():
            return None
        try:
            entry = json.loads(p.read_text())
        except json.JSONDecodeError:
            return None
        return entry if entry.get("key") == key else None  # never serve a different key

    def _cache_put(self, key: str, entry: dict) -> None:
        p = self.cache_dir / f"{key}.json"
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps({**entry, "key": key}))
        tmp.replace(p)

    # ------------------------------------------------------------------ HTTP with retries
    def _http(self, rung: str, req: dict) -> dict:
        """One logical request: up to MAX_ATTEMPTS tries. Returns a dict (never raises)."""
        client = self._client(rung)
        attempts: list[dict] = []
        out: dict[str, Any] = {"text": "", "reasoning_text": None, "usage": None, "http_status": None,
                               "error": None, "error_type": None, "attempts": attempts}
        rung_timeout = self.cfg[rung].get("timeout_s", 300)
        t_all = time.monotonic()
        with self._sems[rung]:
            for i in range(MAX_ATTEMPTS):
                t0 = time.monotonic()
                retryable = False
                timeout_s = min(FIRST_ATTEMPT_TIMEOUT_S, rung_timeout) if i == 0 else rung_timeout
                try:
                    resp = _create_with_deadline(client, req, timeout_s)
                    choice = resp.choices[0]
                    msg = choice.message
                    u = resp.usage
                    det = getattr(u, "completion_tokens_details", None) if u else None
                    out["usage"] = {
                        "prompt_tokens": getattr(u, "prompt_tokens", None),
                        "completion_tokens": getattr(u, "completion_tokens", None),
                        "reasoning_tokens": getattr(det, "reasoning_tokens", None) if det else None}
                    out["text"] = re.sub(r"<think>.*?</think>", "", msg.content or "", flags=re.S).strip()
                    out["reasoning_text"] = reasoning_of(msg)
                    out["http_status"] = 200
                    out["error"] = out["error_type"] = None
                    out["finish_reason"] = choice.finish_reason
                    if getattr(msg, "refusal", None) or choice.finish_reason == "content_filter":
                        out["error_type"] = "refusal"
                        out["error"] = f"refusal: {getattr(msg, 'refusal', None) or choice.finish_reason}"
                    attempts.append({"n": i + 1, "http_status": 200, "latency_ms": _ms(t0),
                                     "timeout_s": timeout_s})
                    break
                except openai.APIStatusError as e:
                    out["http_status"] = e.status_code
                    out["error"] = f"HTTP {e.status_code}: {str(e)[:500]}"
                    out["error_type"] = f"http_{e.status_code}"
                    retryable = e.status_code == 429 or e.status_code >= 500
                except openai.APITimeoutError as e:
                    out["http_status"], out["error"], out["error_type"] = None, f"timeout: {e}", "timeout"
                    retryable = True
                except openai.APIConnectionError as e:
                    out["http_status"], out["error"], out["error_type"] = None, f"connection: {e}", "connection"
                    retryable = True
                attempts.append({"n": i + 1, "http_status": out["http_status"], "error": out["error"],
                                 "latency_ms": _ms(t0), "timeout_s": timeout_s})
                if not retryable or i == MAX_ATTEMPTS - 1:
                    break
                time.sleep(self.retry_base_delay_s * (2 ** i))
        out["retries"] = len(attempts) - 1
        out["latency_ms"] = _ms(t_all)
        return out

    # ------------------------------------------------------------------ logging
    def _next_index(self, session_id: str) -> int:
        with self._lock:
            self._counters[session_id] = self._counters.get(session_id, 0) + 1
            return self._counters[session_id]

    def _store_prompt(self, text: str) -> str:
        h = _sha256(text)
        p = self.log_dir / "prompts" / f"{h}.txt"
        with self._lock:
            if not p.exists():
                p.write_text(text)
        return h

    def _log(self, rec: dict) -> None:
        line = json.dumps({"schema_version": SCHEMA_VERSION, **rec}, ensure_ascii=False)
        with self._lock, open(self.calls_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    # ------------------------------------------------------------------ public API
    def call(self, rung: str, system: str, messages: list[dict], schema: dict | None = None,
             purpose: str = "compose", session_id: str = "none", *, role: str = "client",
             attempt: int = 1, structured_mode: str | None = None, max_tokens: int | None = None,
             repair_of: int | None = None, allow_repair: bool = True) -> Result:
        c = self.cfg[rung]
        mode = (structured_mode or c.get("structured_output_mode")) if schema is not None else None
        if schema is not None and mode not in STRUCTURED_MODES:
            raise ValueError(f"No structured_output_mode for {rung}; pass structured_mode= one of {STRUCTURED_MODES}")
        req, sys_text = self._build_request(rung, system, messages, schema, mode, max_tokens)
        key = self._cache_key(rung, req, schema, mode, attempt)
        sys_hash = self._store_prompt(sys_text)
        index = self._next_index(session_id)
        started = _utc_now()

        entry = self._cache_get(key)
        cached = entry is not None
        if entry is None:
            entry = self._http(rung, req)
            if entry["error"] is None:
                self._cache_put(key, entry)

        res = Result(text=entry["text"], reasoning_text=entry.get("reasoning_text"),
                     usage=entry["usage"] or Result().usage,
                     latency_ms=entry.get("latency_ms", 0), http_status=entry["http_status"],
                     retries=entry.get("retries", 0), error=entry["error"], error_type=entry["error_type"],
                     cached=cached, call_index=index, rung=rung, model=c["model"],
                     attempts=entry.get("attempts") or [])

        problem = None
        if schema is not None and res.error is None:
            try:
                res.parsed = extract_json(res.text)
                jsonschema.validate(res.parsed, schema)
                res.parse_ok = True
            except (json.JSONDecodeError, jsonschema.ValidationError) as e:
                res.parsed, res.parse_ok = None, False
                problem = (e.message if isinstance(e, jsonschema.ValidationError) else f"not JSON ({e})")[:300]
        elif schema is not None:
            res.parse_ok = False

        self._log({
            "session_id": session_id, "call_index": index, "role": role, "purpose": purpose,
            "rung": rung, "provider": c["provider"], "model": c["model"],
            "params": {**(c.get("params") or {}), **({"max_tokens": max_tokens} if max_tokens else {}),
                       **(c.get("extra_body") or {}), "structured_mode": mode},
            "system_prompt_hash": sys_hash, "messages": messages,
            "raw_text": res.text, "reasoning_text": res.reasoning_text, "parsed": res.parsed, "parse_ok": res.parse_ok, "repair_of": repair_of,
            "usage": res.usage, "latency_ms": res.latency_ms, "started_utc": started,
            "http_status": res.http_status, "retries": res.retries, "error": res.error,
            "error_type": res.error_type, "cached": cached, "attempts": entry.get("attempts"),
            "attempt": attempt})

        if problem is not None and allow_repair:
            fix_msgs = messages + [{"role": "assistant", "content": res.text},
                                   {"role": "user", "content": REPAIR_TEMPLATE.format(problem=problem)}]
            rep = self.call(rung, system, fix_msgs, schema, "repair", session_id, role=role,
                            attempt=attempt, structured_mode=mode, max_tokens=max_tokens,
                            repair_of=index, allow_repair=False)
            rep.repair_calls = 1
            if rep.parse_ok:
                return rep
            res.error_type, res.error = "parse_failure", f"invalid against schema after repair: {problem}"
            res.repair_calls = 1
            return res
        if problem is not None:
            res.error_type, res.error = "parse_failure", f"invalid against schema: {problem}"
        return res
