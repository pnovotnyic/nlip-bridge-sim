"""Registry and helpers for the Stage 1 conformance checks.

A check is a function `fn(ctx)` that returns normally (pass), raises `Fail` (fail) or raises `NA` (does not apply).
It names the requirement it tests (`req`, a key of requirements.yaml) and may list further requirements it covers
(`also`). Evidence for each run is the implementation's trace of every call made while the check ran.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

from stage1.harness.adapters import Impl, Parse

GROUPS = {
    "G1": "5 Field names and values in any case",
    "G2": "5.1–5.2 Required and optional fields",
    "G3": "5.3 Formats and subformats",
    "G4": "6.1 Initial request answered with NLIP",
    "G5": "6.2 Token submessages returned unchanged",
    "G6": "6.2.1–6.2.2 Reserved token prefixes",
    "G7": "6.3 Control message answered with control",
    "G8": "6.4 Out-of-band transfer",
    "G9": "7 and ECMA-431 Transport and HTTP binding",
}


class Fail(Exception):
    pass


class NA(Exception):
    pass


@dataclass
class Check:
    id: str
    req: str
    group: str
    title: str
    fn: Callable
    also: tuple = ()
    note: str = ""
    reading: str = ""  # "" | "ambiguous" (outcome depends on how the standard is read) | "application" (depends on the test application)
    kind: str = "behaviour"  # accept: valid input must be accepted and kept; reject: invalid input must be rejected; behaviour


CHECKS: list[Check] = []


def check(cid: str, req: str, group: str, title: str, also: tuple = (), note: str = "", kind: str = "behaviour", reading: str = ""):
    def deco(fn):
        assert all(c.id != cid for c in CHECKS), cid
        CHECKS.append(Check(cid, req, group, title, fn, tuple(also), note, reading, kind))
        return fn

    return deco


# ----------------------------------------------------------------------------- helpers
def lower_keys(d):
    return {k.lower(): v for k, v in d.items()} if isinstance(d, dict) else d


def _eq_ci(a, b):
    return a.lower() == b.lower() if isinstance(a, str) and isinstance(b, str) else a == b


def intact(inp: dict, out: dict) -> str | None:
    """None if `out` carries everything `inp` had (extra trailing submessages in `out` are allowed), else the reason."""
    a, b = lower_keys(inp), lower_keys(out)
    for k in ("format", "subformat"):
        if k in a and not _eq_ci(a[k], b.get(k)):
            return f"{k} changed: {a[k]!r} -> {b.get(k)!r}"
    if "content" in a and a["content"] != b.get("content"):
        return f"content changed: {a['content']!r} -> {b.get('content')!r}"
    if a.get("messagetype") is not None and not _eq_ci(a["messagetype"], b.get("messagetype")):
        return f"MessageType changed: {a['messagetype']!r} -> {b.get('messagetype')!r}"
    sa, sb = a.get("submessages") or [], b.get("submessages") or []
    if len(sb) < len(sa):
        return f"submessages lost: {len(sa)} sent, {len(sb)} back"
    for i, (x, y) in enumerate(zip(sa, sb)):
        x, y = lower_keys(x), lower_keys(y)
        for k in ("format", "subformat"):
            if not _eq_ci(x.get(k), y.get(k)):
                return f"submessage {i} {k} changed: {x.get(k)!r} -> {y.get(k)!r}"
        if x.get("content") != y.get("content"):
            return f"submessage {i} content changed: {x.get('content')!r} -> {y.get('content')!r}"
        if x.get("label") != y.get("label"):
            return f"submessage {i} label changed: {x.get('label')!r} -> {y.get('label')!r}"
    return None


def submessages_of(body: dict) -> list[dict]:
    """First submessage followed by the others, keys lower-cased."""
    b = lower_keys(body)
    first = {k: b.get(k) for k in ("format", "subformat", "content")}
    return [first, *[lower_keys(s) for s in (b.get("submessages") or [])]]


def tokens_of(body: dict) -> list[dict]:
    return [s for s in submessages_of(body) if isinstance(s.get("format"), str) and s["format"].lower() == "token"]


@dataclass
class Route:
    name: str
    parse: Callable[[Any], Parse]
    can_reject: bool = True


class Ctx:
    def __init__(self, impl: Impl, chk: Check):
        self.impl, self.chk = impl, chk
        self.detail: list[str] = []

    # ---- roles
    def routes(self, reader_ok: bool = False) -> list[Route]:
        """Ways to hand a message to the implementation and see whether it is accepted."""
        out = []
        if self.impl.model is not None:
            out.append(Route("model", self.impl.model.parse))
        if self.impl.server is not None:
            out.append(Route("server", self.impl.server.parse))
        if not out and reader_ok and self.impl.reader is not None:
            out.append(Route("reader", self._reader_parse, can_reject=False))
        if not out:
            raise NA(f"{self.impl.label} has no message model, no server and no response reader for this check")
        return out

    def _reader_parse(self, obj) -> Parse:
        r = self.impl.reader.receive("text", obj)
        want = lower_keys(obj).get("content") if isinstance(obj, dict) else None
        ok = bool(r.get("accepted")) and r.get("value") == want
        return Parse(ok, None, f"read {r.get('value')!r}, expected {want!r}" if not ok else "")

    def server(self):
        if self.impl.server is None:
            raise NA(f"{self.impl.label} is not a server (no HTTP end-point to test)")
        return self.impl.server

    def builder(self):
        if self.impl.builder is None:
            raise NA(f"{self.impl.label} has no client code that builds requests")
        return self.impl.builder

    def model(self):
        if self.impl.model is None:
            raise NA(f"{self.impl.label} has no message model")
        return self.impl.model

    # ---- assertions
    def accept(self, vectors: list, reader_ok: bool = False, keep_intact: bool = True) -> None:
        problems = []
        for r in self.routes(reader_ok):
            for v in vectors:
                p = r.parse(v)
                if not p.accepted:
                    problems.append(f"[{r.name}] rejected {json.dumps(v)}: {p.detail[:160]}")
                elif keep_intact and p.out is not None and r.name != "reader":
                    why = intact(v, p.out)
                    if why:
                        problems.append(f"[{r.name}] accepted but {why}")
        if problems:
            raise Fail("; ".join(problems))

    def reject(self, vectors: list) -> None:
        problems = []
        routes = [r for r in self.routes() if r.can_reject]
        if not routes:
            raise NA("a response reader cannot reject messages")
        for r in routes:
            for v in vectors:
                p = r.parse(v)
                if p.accepted:
                    problems.append(f"[{r.name}] accepted {json.dumps(v)}")
        if problems:
            raise Fail("; ".join(problems))

    def expect(self, cond: bool, msg: str) -> None:
        if not cond:
            raise Fail(msg)


BASE = {"format": "text", "subformat": "English", "content": "Hello"}


def msg(**kw) -> dict:
    return {**BASE, **kw}


def sub(fmt, subfmt, content, label=None) -> dict:
    d = {"format": fmt, "subformat": subfmt, "content": content}
    if label is not None:
        d = {"label": label, **d}
    return d
