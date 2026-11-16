"""Change tags and `catalogue_breaking_crossed` of one task instance (stage 05, rewritten in stage 07b A9).

The tags follow what the instance exercises, not what its intent could use:

- request tags: catalogue entries (direction `request`) whose client path occurs in the client's native request
  (any leaf or object on the way to a leaf), or whose server path occurs in the primary gold call;
- response tags: catalogue entries (direction `response`) whose client path occurs in `gold_client_answer.result`.
  An entry written `path=VALUE` matches only when the field has that value. A declined instance has no response tags.
  An `unrepresentable` answer has no result; its only response tag is the entry of the field that cannot be expressed
  (L2 `verificationResult`);
- phone entries lose `unit_format` when the native phone number has the same form as the gold one (07b A10).

`catalogue_breaking_crossed` is the number of distinct catalogue entries with a breaking kind that sit behind the
instance's own tags, counted over request and response together.
"""
from __future__ import annotations

from typing import Any

from nlipeval.tasks import changes

BREAKING = {"renamed", "restructured", "unit_format", "newly_required", "changed_meaning", "removed"}
UNREPRESENTABLE_FIELD = {"L2": "verificationResult"}


def paths(obj: Any, prefix: str = "") -> tuple[dict[str, Any], set[str]]:
    """Leaf paths with their values, and every path (leaf or object) on the way.

    A list of objects contributes `path[].key`; a list of scalars is a leaf.
    """
    leaves: dict[str, Any] = {}
    every: set[str] = set()

    def walk(o: Any, p: str) -> None:
        if isinstance(o, dict):
            for k, v in o.items():
                q = f"{p}.{k}" if p else k
                every.add(q)
                walk(v, q)
        elif isinstance(o, list) and o and all(isinstance(x, dict) for x in o):
            q = p + "[]"
            for x in o:
                walk(x, q)
        else:
            if p:
                leaves[p] = o

    walk(obj, prefix)
    return leaves, every


def _is_phone(entry: dict) -> bool:
    return any(isinstance(entry.get(k), str) and entry[k].endswith(("phoneNumber", "msisdn"))
               for k in ("client_path", "server_path"))


def _kinds(entry: dict, native_leaves: dict[str, Any], gold_leaves: dict[str, Any]) -> set[str]:
    kinds = {k for k in entry["kinds"] if k in changes.TAG_KINDS}
    if "unit_format" in kinds and _is_phone(entry) and entry["direction"] == "request":
        native = native_leaves.get(entry.get("client_path") or "")
        gold = gold_leaves.get(entry.get("server_path") or "")
        if native is None or native == gold:
            kinds.discard("unit_format")
    return kinds


def _split_value(path: str) -> tuple[str, str | None]:
    if "=" in path:
        p, v = path.split("=", 1)
        return p, v
    return path, None


def matched_entries(
    api: str,
    client_version: str,
    operation: str,
    native_body: Any,
    gold_body: Any,
    answer: dict,
    server_version: str,
) -> tuple[list[tuple[dict, set[str]]], list[tuple[dict, set[str]]]]:
    """(request, response) lists of (catalogue entry, kinds that apply to this instance)."""
    if client_version == server_version:
        return [], []
    native_leaves, native_all = paths(native_body or {})
    gold_leaves, gold_all = paths(gold_body or {})
    if operation in ("getSession", "deleteSession"):
        native_all = native_all | {"sessionId"}
    native_all = native_all | set(native_leaves)
    gold_all = gold_all | set(gold_leaves)

    req: list[tuple[dict, set[str]]] = []
    for e in changes.entries(api, client_version, operation, "request"):
        cp, sp = e["client_path"], e["server_path"]
        # an entry written "POST /path" is the operation's own path: every native request crosses it
        hit = (cp is not None and (cp in native_all or " " in cp)) or (sp is not None and sp in gold_all)
        if hit:
            req.append((e, _kinds(e, native_leaves, gold_leaves)))

    resp: list[tuple[dict, set[str]]] = []
    status = answer["status"]
    result = answer.get("result")
    if status == "done" and result is not None:
        res_leaves, res_all = paths(result)
        res_all = res_all | set(res_leaves)
        for e in changes.entries(api, client_version, operation, "response"):
            cp = e["client_path"]
            if cp is None:
                continue
            p, v = _split_value(cp)
            if p not in res_all:
                continue
            if v is not None and str(res_leaves.get(p)) != v:
                continue
            resp.append((e, {k for k in e["kinds"] if k in changes.TAG_KINDS}))
    elif status == "unrepresentable" and api in UNREPRESENTABLE_FIELD:
        field = UNREPRESENTABLE_FIELD[api]
        for e in changes.entries(api, client_version, operation, "response"):
            if e["client_path"] == field:
                resp.append((e, {k for k in e["kinds"] if k in changes.TAG_KINDS}))
    return req, resp


def instance_tags(
    api: str,
    client_version: str,
    operation: str,
    native_body: Any,
    gold_body: Any,
    answer: dict,
    server_version: str,
) -> dict[str, Any]:
    req, resp = matched_entries(api, client_version, operation, native_body, gold_body, answer, server_version)

    def kinds(ms: list[tuple[dict, set[str]]]) -> list[str]:
        s: set[str] = set().union(*(k for _, k in ms)) if ms else set()
        return [k for k in changes.TAG_KINDS if k in s]

    breaking = sum(1 for _, k in req + resp if k & BREAKING)
    return {
        "change_tags_request": kinds(req),
        "change_tags_response": kinds(resp),
        "catalogue_breaking_crossed": breaking,
    }
