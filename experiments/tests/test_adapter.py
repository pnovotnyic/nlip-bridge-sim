"""Offline tests for nlipeval.models.adapter, using a fake OpenAI-compatible server."""

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest
import yaml

from nlipeval.models.adapter import ModelAdapter

SCHEMA = {"type": "object", "required": ["a"], "properties": {"a": {"type": "string", "enum": ["x", "y"]}}}


class Fake:
    def __init__(self):
        self.replies = []  # list of (status, content) consumed in order; last repeats
        self.requests = []
        self.headers = []
        self.reasoning = {}  # message field name -> value added to every reply, e.g. {"reasoning": "..."}
        self.delay_s = []  # per-request sleep before replying, consumed in order


def _make_server(fake):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            fake.requests.append(body)
            fake.headers.append(dict(self.headers))
            status, content = fake.replies.pop(0) if len(fake.replies) > 1 else fake.replies[0]
            if fake.delay_s:
                time.sleep(fake.delay_s.pop(0))
            payload = ({"id": "1", "object": "chat.completion", "created": 0, "model": body["model"],
                        "choices": [{"index": 0, "finish_reason": "stop",
                                     "message": {"role": "assistant", "content": content, **fake.reasoning}}],
                        "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8,
                                  "completion_tokens_details": {"reasoning_tokens": 2}}}
                       if status == 200 else {"error": {"message": "boom", "type": "x"}})
            data = json.dumps(payload).encode()
            try:
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):  # client timed out and left
                pass

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


@pytest.fixture
def env(tmp_path, monkeypatch):
    fake = Fake()
    srv = _make_server(fake)
    monkeypatch.setenv("FAKE_URL", f"http://127.0.0.1:{srv.server_port}/v1")
    monkeypatch.setenv("FAKE_KEY", "secret-key-123")
    cfg = {"rungs": {
        "R1": {"provider": "fake", "model": "m1", "base_url_env": "FAKE_URL", "api_key_env": "FAKE_KEY",
               "headers": {"RITS_API_KEY": "${FAKE_KEY}"}, "params": {"temperature": 0.5},
               "extra_body": {"reasoning_effort": "medium"}, "max_concurrency": 2, "timeout_s": 5},
        "R2": {"provider": "fake", "model": "m2", "base_url_env": "FAKE_URL", "api_key_env": "FAKE_KEY",
               "params": {}, "system_role_supported": False, "max_concurrency": 1, "timeout_s": 5},
    }}
    cfg_path = tmp_path / "models.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg))
    ad = ModelAdapter(cfg_path, tmp_path / "run", retry_base_delay_s=0.01)
    yield ad, fake, tmp_path / "run"
    srv.shutdown()


def _log(run: Path):
    return [json.loads(line) for line in (run / "calls.jsonl").read_text().splitlines()]


def test_plain_call_logs_and_sends_settings(env):
    ad, fake, run = env
    fake.replies = [(200, "hello")]
    r = ad.call("R1", "SYS", [{"role": "user", "content": "hi"}], purpose="compose", session_id="s1")
    assert r.ok and r.text == "hello" and r.usage["reasoning_tokens"] == 2
    req = fake.requests[0]
    assert req["temperature"] == 0.5 and req["reasoning_effort"] == "medium"
    assert req["messages"][0] == {"role": "system", "content": "SYS"}
    assert {k.lower(): v for k, v in fake.headers[0].items()}["rits_api_key"] == "secret-key-123"
    rec = _log(run)[0]
    assert rec["schema_version"] == "1" and rec["purpose"] == "compose" and rec["call_index"] == 1
    assert (run / "prompts" / f"{rec['system_prompt_hash']}.txt").read_text() == "SYS"
    assert "secret-key-123" not in (run / "calls.jsonl").read_text()


def test_cache_hit_and_distinct_keys(env):
    ad, fake, _ = env
    fake.replies = [(200, "one")]
    m = [{"role": "user", "content": "q"}]
    a = ad.call("R1", "S", m, session_id="s")
    b = ad.call("R1", "S", m, session_id="s")
    assert not a.cached and b.cached and len(fake.requests) == 1
    fake.replies = [(200, "two")]
    c = ad.call("R1", "S", [{"role": "user", "content": "other"}], session_id="s")
    d = ad.call("R1", "S", m, session_id="s", attempt=2)  # new attempt = new key
    assert c.text == "two" and not d.cached and len(fake.requests) == 3


def test_retry_on_429_then_success(env):
    ad, fake, run = env
    fake.replies = [(429, ""), (503, ""), (200, "ok")]
    r = ad.call("R1", "S", [{"role": "user", "content": "q"}], session_id="s")
    assert r.ok and r.retries == 2 and len(fake.requests) == 3
    assert [a["http_status"] for a in _log(run)[0]["attempts"]] == [429, 503, 200]


def test_no_retry_on_400_and_max_four_attempts(env):
    ad, fake, _ = env
    fake.replies = [(400, "")]
    r = ad.call("R1", "S", [{"role": "user", "content": "a"}], session_id="s")
    assert r.error_type == "http_400" and len(fake.requests) == 1
    fake.requests.clear()
    fake.replies = [(500, "")]
    r = ad.call("R1", "S", [{"role": "user", "content": "b"}], session_id="s")
    assert r.error_type == "http_500" and len(fake.requests) == 4 and r.retries == 3


def test_errors_are_not_cached(env):
    ad, fake, _ = env
    fake.replies = [(400, "")]
    ad.call("R1", "S", [{"role": "user", "content": "a"}], session_id="s")
    fake.replies = [(200, "fine")]
    r = ad.call("R1", "S", [{"role": "user", "content": "a"}], session_id="s")
    assert r.ok and not r.cached


def test_structured_json_schema_and_json_object_and_prompt_modes(env):
    ad, fake, _ = env
    m = [{"role": "user", "content": "q"}]
    fake.replies = [(200, '{"a":"x"}')]
    r = ad.call("R1", "S", m, SCHEMA, session_id="s", structured_mode="json_schema")
    assert r.parse_ok and r.parsed == {"a": "x"}
    assert fake.requests[-1]["response_format"]["type"] == "json_schema"
    fake.replies = [(200, '```json\n{"a":"y"}\n```')]
    r = ad.call("R1", "S", m, SCHEMA, session_id="s2", structured_mode="json_object")
    assert r.parse_ok and fake.requests[-1]["response_format"] == {"type": "json_object"}
    assert "JSON Schema" in fake.requests[-1]["messages"][0]["content"]
    fake.replies = [(200, '<think>hm</think>{"a":"x"}')]
    r = ad.call("R1", "S", m, SCHEMA, session_id="s3", structured_mode="prompt")
    assert r.parse_ok and "response_format" not in fake.requests[-1]


def test_repair_call_once_then_ok(env):
    ad, fake, run = env
    fake.replies = [(200, '{"a":"nope"}'), (200, '{"a":"x"}')]
    r = ad.call("R1", "S", [{"role": "user", "content": "q"}], SCHEMA, session_id="s", structured_mode="prompt")
    assert r.parse_ok and r.parsed == {"a": "x"} and r.repair_calls == 1
    log = _log(run)
    assert [x["purpose"] for x in log] == ["compose", "repair"] and log[1]["repair_of"] == 1
    assert "not valid against this schema" in fake.requests[1]["messages"][-1]["content"]


def test_repair_fails_gives_parse_failure(env):
    ad, fake, run = env
    fake.replies = [(200, "not json")]
    r = ad.call("R1", "S", [{"role": "user", "content": "q"}], SCHEMA, session_id="s", structured_mode="prompt")
    assert not r.ok and r.error_type == "parse_failure" and len(fake.requests) == 2
    assert len(_log(run)) == 2


def test_system_role_fallback(env):
    ad, fake, _ = env
    fake.replies = [(200, "ok")]
    ad.call("R2", "SYSTEXT", [{"role": "user", "content": "hello"}], session_id="s")
    msgs = fake.requests[0]["messages"]
    assert len(msgs) == 1 and msgs[0]["content"].startswith("SYSTEXT") and msgs[0]["content"].endswith("hello")


def test_missing_mode_raises(env):
    ad, _, _ = env
    with pytest.raises(ValueError):
        ad.call("R1", "S", [{"role": "user", "content": "q"}], SCHEMA, session_id="s")


@pytest.mark.parametrize("field", ["reasoning", "reasoning_content"])
def test_reasoning_text_logged(env, field):
    ad, fake, run = env
    fake.reasoning = {field: "step by step"}
    fake.replies = [(200, "answer")]
    r = ad.call("R1", "S", [{"role": "user", "content": field}], session_id="s")
    assert r.text == "answer" and r.reasoning_text == "step by step"
    assert r.usage["completion_tokens"] == 3  # token counts unchanged
    assert _log(run)[0]["reasoning_text"] == "step by step"
    again = ad.call("R1", "S", [{"role": "user", "content": field}], session_id="s")  # served from cache
    assert again.cached and again.reasoning_text == "step by step"


def test_reasoning_text_null_when_absent(env):
    ad, fake, run = env
    fake.replies = [(200, "answer")]
    r = ad.call("R1", "S", [{"role": "user", "content": "q"}], session_id="s")
    assert r.reasoning_text is None and _log(run)[0]["reasoning_text"] is None


def test_first_attempt_uses_short_timeout_then_rung_timeout(env, monkeypatch):
    import nlipeval.models.adapter as adapter_mod
    ad, fake, run = env
    monkeypatch.setattr(adapter_mod, "FIRST_ATTEMPT_TIMEOUT_S", 0.3)
    fake.replies = [(200, "late"), (200, "ok")]
    fake.delay_s = [1.0]  # the first request outlasts the first-attempt timeout
    r = ad.call("R1", "S", [{"role": "user", "content": "slow"}], session_id="s")
    assert r.ok and r.retries == 1
    att = _log(run)[0]["attempts"]
    assert [a["timeout_s"] for a in att] == [0.3, 5]
    assert att[0]["error"].startswith("timeout")


def test_create_with_deadline_bounds_a_stalled_call():
    import time as _t
    import httpx
    import openai
    import pytest
    from nlipeval.models.adapter import _create_with_deadline

    class Stalled:
        base_url = "http://x"

        class chat:  # noqa: N801
            class completions:  # noqa: N801
                @staticmethod
                def create(**kw):
                    _t.sleep(30)

    t0 = _t.monotonic()
    with pytest.raises(openai.APITimeoutError):
        _create_with_deadline(Stalled, {}, 0.2)  # type: ignore[arg-type]
    assert _t.monotonic() - t0 < 6
