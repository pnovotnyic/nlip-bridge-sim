"""Live smoke tests for the five rungs (stage 01, step 6).

    uv run python -m nlipeval.models.smoke R1 R2 ...   # writes results/stage01/smoke_<rung>.json

Tests: 1 chat, 2 system prompt honoured, 3 structured output (first mode that works 5/5),
4 long context (20,000-token prompt, fact at the start), 5 latency and safe concurrency.
Raw calls go to data/smoke/<rung>/calls.jsonl (git-ignored).
"""

from __future__ import annotations

import json
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from nlipeval.models.adapter import STRUCTURED_MODES, ModelAdapter, load_env

ROOT = Path(__file__).resolve().parents[2]
MAX_TOKENS = 6000  # generous: reasoning tokens count against it
SECRET = "TANGO-4417"

SCHEMA = {
    "type": "object", "required": ["action", "target"], "additionalProperties": False,
    "properties": {
        "action": {"type": "string", "enum": ["verify", "retrieve", "create"]},
        "target": {"type": "object", "required": ["device", "radius_m"], "additionalProperties": False,
                   "properties": {"device": {"type": "object", "required": ["phoneNumber"],
                                             "properties": {"phoneNumber": {"type": "string"}}},
                                  "radius_m": {"type": "integer"}}}}}

_WORDS = ("alpha river stone window garden signal copper meadow harbor lantern quiet engine "
          "paper orbit velvet thunder marble coastal ribbon summit pocket anchor violet timber "
          "mirror canyon bridge ember falcon island jungle kettle ladder magnet needle oyster").split()


def _filler(n_words: int, salt: int) -> str:
    import random
    rnd = random.Random(salt)
    return " ".join(rnd.choice(_WORDS) for _ in range(n_words))


def _med(xs):
    return round(statistics.median(xs), 2) if xs else None


def run_rung(rung: str) -> dict:
    load_env(ROOT / ".env")
    log_dir = ROOT / "data" / "smoke" / rung
    ad = ModelAdapter(ROOT / "config" / "models.yaml", log_dir, cache_dir=log_dir / "cache")
    cfg = ad.cfg[rung]
    out: dict = {"rung": rung, "model": cfg["model"], "provider": cfg["provider"],
                 "settings_sent": {"params": cfg.get("params"), "extra_body": cfg.get("extra_body"),
                                   "thinking": cfg.get("thinking")}, "tests": {}}
    sid = f"smoke-{rung}"
    t = out["tests"]

    # 1. one-line chat
    r = ad.call(rung, "You are a terse assistant.", [{"role": "user", "content": "Reply with exactly one word: pong"}],
                session_id=sid, max_tokens=MAX_TOKENS, attempt=1)
    t["1_chat"] = {"pass": r.ok and "pong" in r.text.lower(), "reply": r.text[:80], "error": r.error,
                   "latency_s": r.latency_ms / 1000, "usage": r.usage}

    # 2. system prompt honoured
    r = ad.call(rung, "Whatever the user asks, answer with the single word BANANA and nothing else.",
                [{"role": "user", "content": "What is 2 + 2?"}], session_id=sid, max_tokens=MAX_TOKENS)
    t["2_system_prompt"] = {"pass": r.ok and "banana" in r.text.lower(), "reply": r.text[:80], "error": r.error}

    # 3. structured output: json_schema -> json_object -> prompt, first with 5/5 valid (no repair allowed)
    modes: dict = {}
    chosen, lat = None, []
    ad_s = ModelAdapter(ROOT / "config" / "models.yaml", log_dir, cache_dir=log_dir / "cache")
    ad_s.cfg[rung]["timeout_s"] = 60  # a mode that hangs counts as failed
    for mode in STRUCTURED_MODES:
        ok, errs = 0, []
        for i in range(5):
            r = ad_s.call(rung, "You turn requests into a call description.",
                        [{"role": "user", "content": f"Verify that device +99900000{i:03d} is within 2000 metres of a place."}],
                        SCHEMA, session_id=sid + "-struct", structured_mode=mode, max_tokens=MAX_TOKENS, attempt=100 + i,
                        allow_repair=False)
            ok += bool(r.parse_ok)
            lat.append(r.latency_ms / 1000)
            if not r.parse_ok:
                errs.append((r.error or "")[:160])
            if r.error_type in ("timeout", "connection") or (r.error_type or "").startswith("http_"):
                break
        modes[mode] = {"valid": ok, "of": 5, "errors": errs[:2]}
        if ok == 5 and chosen is None:
            chosen = mode
            break
    t["3_structured"] = {"pass": chosen is not None, "chosen_mode": chosen, "modes": modes,
                         "median_latency_s": _med(lat)}

    # 4. long context: ~20,000-token prompt (calibrated on the model's own tokenizer), fact at the start
    probe = ad.call(rung, "Answer from the text you are given.",
                    [{"role": "user", "content": _filler(1000, 99)}], session_id=sid, max_tokens=1, attempt=400)
    per_word = (probe.usage.get("prompt_tokens") or 1000) / 1000
    words = int(20000 / max(per_word, 0.5))
    prompt = (f"Remember this: the access code is {SECRET}.\n\n" + _filler(words, 1) +
              "\n\nQuestion: what is the access code? Reply with the code only.")
    r = ad.call(rung, "Answer from the text you are given.", [{"role": "user", "content": prompt}],
                session_id=sid, max_tokens=MAX_TOKENS)
    pt = r.usage.get("prompt_tokens")
    if pt and pt < 19500:  # calibration was low: rescale once so the prompt really is about 20,000 tokens
        words = int(words * 20000 / pt)
        prompt = (f"Remember this: the access code is {SECRET}.\n\n" + _filler(words, 1) +
                  "\n\nQuestion: what is the access code? Reply with the code only.")
        r = ad.call(rung, "Answer from the text you are given.", [{"role": "user", "content": prompt}],
                    session_id=sid, max_tokens=MAX_TOKENS, attempt=401)
        pt = r.usage.get("prompt_tokens")
    t["4_long_context"] = {"pass": r.ok and SECRET in r.text and (pt or 0) >= 19000, "prompt_tokens_reported": pt,
                           "reply": r.text[:80], "error": r.error, "latency_s": r.latency_ms / 1000}

    # 5. latency (4,000-token prompt, 300-token reply) and concurrency
    lats, ctoks = [], []
    for i in range(3):
        p = f"Continue this text at length, in prose.\n\n{_filler(3000, 10 + i)}"
        r = ad.call(rung, "You continue texts.", [{"role": "user", "content": p}], session_id=sid,
                    max_tokens=300, attempt=200 + i)
        if r.error is None:
            lats.append(r.latency_ms / 1000)
            ctoks.append(r.usage.get("completion_tokens"))
    conc = {}
    levels = (1, 2) if rung == "R1" else (1, 2, 4, 8)
    ad2 = ModelAdapter(ROOT / "config" / "models.yaml", log_dir / "conc", retry_base_delay_s=0.5)
    for n in levels:
        ad2._sems[rung] = __import__("threading").BoundedSemaphore(n)

        def one(k, n=n):
            r = ad2.call(rung, "Be brief.", [{"role": "user", "content": f"Name one colour. ({n}-{k})"}],
                         session_id=f"conc-{n}-{k}", max_tokens=64, attempt=300)
            return r, sum(1 for a in r.attempts if a.get("http_status") == 429)
        t0 = time.monotonic()
        with ThreadPoolExecutor(n) as ex:
            res = list(ex.map(one, range(n)))
        conc[str(n)] = {"n_429": sum(x[1] for x in res), "errors": sum(1 for x in res if x[0].error),
                        "wall_s": round(time.monotonic() - t0, 2)}
        if conc[str(n)]["n_429"] or conc[str(n)]["errors"]:
            break
    safe = max((int(k) for k, v in conc.items() if not v["n_429"] and not v["errors"]), default=0)
    t["5_latency"] = {"median_latency_s_4k_prompt_300_tokens": _med(lats), "completion_tokens": ctoks,
                      "concurrency": conc, "safe_concurrency": safe}

    out["pass_1_to_4"] = all(t[k]["pass"] for k in ("1_chat", "2_system_prompt", "3_structured", "4_long_context"))
    return out


def main(rungs: list[str]) -> None:
    dest = ROOT / "results" / "stage01"
    dest.mkdir(parents=True, exist_ok=True)
    for rung in rungs:
        res = run_rung(rung)
        (dest / f"smoke_{rung}.json").write_text(json.dumps(res, indent=2))
        print(rung, "pass 1-4:", res["pass_1_to_4"], json.dumps({k: v.get("pass") for k, v in res["tests"].items()}))


if __name__ == "__main__":
    main(sys.argv[1:] or ["R1", "R2", "R3", "R4", "R5"])
