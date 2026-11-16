"""Stage 1 interoperability: a fixed 20-message script exchanged between every client and every server.

    uv run python -m stage1.harness.interop

Clients: an nlip_sdk-based client (messages built and read with nlip_sdk; the HTTP POST is made by the harness,
because the nlip_client package is not one of the pinned repositories), the TypeScript example client (real
network.ts code, with fetch pointed at the server), and our client (nlipeval.nlip.transport.NLIPClient).
Servers: nlip_server running its own echo application, and our server running the echo handler.

A message "gets through intact" when the client could build it, the server answered, the answer meets what the
standard requires for that kind of message (see JUDGE), and the client could read the answer.
"""
from __future__ import annotations

import csv
import json
import sys

import httpx

from nlipeval.nlip.message import Message, Submessage
from nlipeval.nlip.transport import NLIPClient
from nlipeval.nlip.validate import validate
from stage1.harness.adapters import RESULTS, ROOT, UPLOAD_TEXT, build_impls
from stage1.harness.checks import intact, lower_keys, submessages_of, tokens_of

CONV_ID = "conv-42"

SCRIPT = {
    "M01": ("data", "text, English"),
    "M02": ("data", "text with non-ASCII characters"),
    "M03": ("data", "text, French subformat"),
    "M04": ("data", "structured/json, nested content"),
    "M05": ("data", "text with a binary (image) submessage"),
    "M06": ("data", "three submessages in order: text, structured/json, location/gps, with labels"),
    "M07": ("data", "conversation token"),
    "M08": ("data", "authentication token"),
    "M09": ("data", "conversation and authentication token together"),
    "M10": ("data", "token with a free subformat (group_7)"),
    "M11": ("data", "conversation, turn 1 (token sent)"),
    "M12": ("data", "conversation, turn 2 (same token)"),
    "M13": ("data", "conversation, turn 3 (same token)"),
    "M14": ("control", "control message (MessageType control)"),
    "M15": ("upload", "control request for an out-of-band upload end-point"),
    "M16": ("control_field", "control message (field control=true)"),
    "M17": ("invalid", "error case: a message without content"),
    "M18": ("language", "structured message in a programming language (COBOL)"),
    "M19": ("data", "location/gps"),
    "M20": ("data", "text of 100 000 characters"),
}


def judge(mid: str, req: dict, status: int, resp) -> str | None:
    """None if the exchange is acceptable, else the reason."""
    kind = SCRIPT[mid][0]
    if kind == "invalid":
        return None if 400 <= status <= 499 else f"an invalid message was answered with HTTP {status}, not a 4xx status"
    if not (200 <= status <= 299) or not isinstance(resp, dict):
        return f"HTTP {status}, body {str(resp)[:100]}"
    r = lower_keys(resp)
    if kind == "data":
        return intact(req, resp)
    if kind == "control":
        return None if str(r.get("messagetype", "")).lower() == "control" else f"answer is not a control message (MessageType {r.get('messagetype')!r})"
    if kind == "control_field":
        return None if r.get("control") is True else "answer does not carry control=true"
    if kind == "upload":
        if str(r.get("messagetype", "")).lower() != "control":
            return f"answer is not a control message (MessageType {r.get('messagetype')!r})"
        has = [x for x in submessages_of(resp) if str(x.get("format", "")).lower() == "structured" and str(x.get("subformat", "")).lower() == "uri"]
        return None if has else "no structured/uri submessage in the answer"
    if kind == "language":
        return None if str(r.get("format", "")).lower() == "text" else f"answered with format {r.get('format')!r}, not text"
    raise ValueError(kind)


OPTIONAL = ("messagetype", "label", "submessages")


def drop_null_optionals(body: dict) -> dict:
    out = {k: v for k, v in body.items() if not (k.lower() in OPTIONAL and v is None)}
    if isinstance(out.get("submessages"), list):
        out["submessages"] = [{k: v for k, v in x.items() if not (k.lower() in OPTIONAL and v is None)} if isinstance(x, dict) else x for x in out["submessages"]]
    return out


# ----------------------------------------------------------------------------- clients: produce (request, status, response, read_problem)
class SdkClient:
    key = "nlip_sdk"

    def __init__(self, impl):
        self.m = impl.model

    def run(self, mid: str, base: str):
        req = self.m.interop_build(mid) if mid != "M17" else None
        if req is None:
            return None, "the client has no way to build this message"
        r = httpx.post(base + "/nlip", json=req, timeout=30, follow_redirects=True)
        body = r.json() if r.headers.get("content-type", "").startswith("application/json") else None
        problem = None
        if 200 <= r.status_code <= 299 and isinstance(body, dict):
            rd = self.m.interop_read(body)
            if not rd["accepted"]:
                problem = f"the client could not read the answer: {rd['error']}"
        return (req, r.status_code, body, problem), None


class OursClient:
    key = "ours"

    def run(self, mid: str, base: str):
        c = NLIPClient(base)
        try:
            kind = SCRIPT[mid][0]
            if kind == "invalid":
                req = {"format": "text", "subformat": "English"}
                status, body = c.post_raw(req)
                return (req, status, body, None), None
            m = self.build(mid)
            req = m.to_dict()
            resp = c.send(m, track=False)
            body = c.wire[-1]["body"]
            # a tolerant reader: JSON null for an absent optional field (MessageType, Label, Submessages) is read as absent.
            # Whether a sender may write such nulls is recorded separately, by check C49.
            problem = None
            if 200 <= c.last_status <= 299 and isinstance(body, dict):
                ok, v = validate(drop_null_optionals(body))
                problem = None if ok else "the client could not read the answer: " + "; ".join(str(x) for x in v)
            return (req, c.last_status, body, problem), None
        finally:
            c.close()

    @staticmethod
    def build(mid: str) -> Message:
        t = lambda s, **k: Message.text(s, **k)
        if mid == "M01": return t("Hello, world")
        if mid == "M02": return t("Grüße, 世界 — ✓")
        if mid == "M03": return t("Bonjour le monde", language="French")
        if mid == "M04": return Message("structured", "json", {"order": {"id": 17, "items": [{"sku": "a", "qty": 2}, {"sku": "b", "qty": None}], "paid": True}})
        if mid == "M05":
            m = t("what is this"); m.submessages = [Submessage("binary", "image/png", "AAEC")]; return m
        if mid == "M06":
            m = t("Guten Tag", language="German")
            m.submessages = [Submessage("structured", "json", {"k": [1, 2]}, label="two"), Submessage("location", "gps", "51.0,-1.4", label="three")]
            return m
        if mid == "M07": return t("hi").with_conversation(CONV_ID)
        if mid == "M08": return t("hi").with_authentication("secret-1")
        if mid == "M09": return t("hi").with_conversation(CONV_ID).with_authentication("secret-1")
        if mid == "M10":
            m = t("hi"); m.add_token("group_7", "g-9"); return m
        if mid in ("M11", "M12", "M13"): return t(f"turn {int(mid[1:]) - 10}").with_conversation(CONV_ID)
        if mid == "M14": return t("query policies", messagetype="control")
        if mid == "M15": return t(UPLOAD_TEXT, messagetype="control")
        if mid == "M16": return t("query policies", extra={"control": True})
        if mid == "M18": return Message("structured", "cobol", "DISPLAY 'HELLO'.")
        if mid == "M19": return Message("location", "gps", "51.0,-1.4")
        if mid == "M20": return t("x" * 100000)
        raise ValueError(mid)


class TsClientRunner:
    key = "ts_client"
    BUILDS = {"M01": ("text", "Hello, world"), "M02": ("text", "Grüße, 世界 — ✓"), "M05": ("image", None), "M16": ("upload", None), "M20": ("text", "x" * 100000)}

    def __init__(self, impl):
        self.c = impl.builder

    def run(self, mid: str, base: str):
        if mid not in self.BUILDS:
            return None, "the client has no code that builds this message"
        kind, text = self.BUILDS[mid]
        r = self.c.send(kind, base, text)
        req, status, raw = r.get("sent"), r.get("status"), r.get("response")
        try:
            body = json.loads(raw) if raw else None
        except ValueError:
            body = None
        problem = None
        if kind == "text" and not r["accepted"]:
            problem = f"the client failed: {r.get('error')}"
        elif kind == "text" and isinstance(body, dict) and r.get("value") != body.get("content"):
            problem = f"the client returned {str(r.get('value'))[:40]!r}, the answer's content was {str(body.get('content'))[:40]!r}"
        return (req, status, body, problem), None


def run_interop(include=None) -> list[dict]:
    impls = {i.key: i for i in build_impls(include or ["nlip_sdk", "nlip_server", "nlip_server_echo", "ts_client", "ours"])}
    clients = [SdkClient(impls["nlip_sdk"]), TsClientRunner(impls["ts_client"]), OursClient()]
    servers = [("nlip_server", impls["nlip_server_echo"].server.procs["echo"], "nlip_server (own echo application)"), ("ours", impls["ours"].server.procs["echo"], "our server (echo handler)")]
    rows, detail = [], []
    log_dir = RESULTS / "logs" / "interop"
    log_dir.mkdir(parents=True, exist_ok=True)
    try:
        for c in clients:
            for sk, proc, slabel in servers:
                lines, fails, ok, nb = [], [], 0, 0
                for mid in SCRIPT:
                    res, why = c.run(mid, proc.url)
                    if res is None:
                        outcome, reason = "not built", why
                        req = status = body = None
                    else:
                        req, status, body, problem = res
                        reason = judge(mid, req, status, body) or problem
                        outcome = "ok" if reason is None else "fail"
                    ok += outcome == "ok"
                    nb += outcome == "not built"
                    if outcome != "ok":
                        fails.append(f"{mid}: {reason}")
                    lines.append(f"{mid} [{SCRIPT[mid][1]}] {outcome}" + (f": {reason}" if reason else "") + f"\n   request : {json.dumps(req)[:400]}\n   HTTP {status}: {json.dumps(body)[:400]}")
                    detail.append({"client": c.key, "server": sk, "message": mid, "description": SCRIPT[mid][1], "outcome": outcome, "reason": reason or ""})
                (log_dir / f"{c.key}__{sk}.log").write_text(f"client {c.key} -> server {slabel}\n\n" + "\n".join(lines) + "\n")
                rows.append({"client": c.key, "server": sk, "messages_ok": ok, "messages_total": len(SCRIPT), "failures": " | ".join(fails), "not_built": nb})
    finally:
        for i in impls.values():
            i.close()
    RESULTS.mkdir(parents=True, exist_ok=True)
    with open(RESULTS / "interop.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["client", "server", "messages_ok", "messages_total", "failures"], extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    with open(RESULTS / "interop_detail.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["client", "server", "message", "description", "outcome", "reason"])
        w.writeheader()
        w.writerows(detail)
    return rows


if __name__ == "__main__":
    for r in run_interop():
        print(f"{r['client']:10} -> {r['server']:12} {r['messages_ok']}/{r['messages_total']}  (not built: {r['not_built']})")
        for f in r["failures"].split(" | "):
            if f:
                print("     ", f[:170])
