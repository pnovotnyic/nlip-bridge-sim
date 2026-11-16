"""Read the change catalogue (specs/changes/<api>.yaml).

Given the fields a task uses, `change_tags` returns the kinds of change crossed in each direction.
Only the six kinds listed in the data contract are returned as tags (`unchanged` and `added_optional` are not).
"""
from __future__ import annotations

import functools

import yaml

from nlipeval.tasks.specs import SPECS

TAG_KINDS = ("renamed", "restructured", "unit_format", "newly_required", "changed_meaning", "removed")


@functools.cache
def load(api: str) -> dict:
    return yaml.safe_load((SPECS / "changes" / f"{api}.yaml").read_text())


def entries(api: str, client_version: str, operation: str | None = None, direction: str | None = None) -> list[dict]:
    """All catalogue entries for a client version, optionally filtered by operation and direction."""
    doc = load(api)["client_versions"]
    if client_version not in doc:
        raise KeyError(f"{api}: unknown client version {client_version!r}")
    return [
        e
        for e in doc[client_version]["entries"]
        if (operation is None or operation in e["operations"]) and (direction is None or e["direction"] == direction)
    ]


def _prefix_match(used: str, path: str | None) -> bool:
    return path is not None and (path == used or path.startswith(used + ".") or path.startswith(used + "[]"))


def change_tags(
    api: str,
    client_version: str,
    operation: str,
    request_fields: list[str],
    response_fields: list[str],
) -> dict[str, list[str]]:
    """Kinds of change crossed by the fields a task uses.

    `request_fields` / `response_fields` are paths in the *client's* version (e.g. "ueId.msisdn", "qos").
    A used path selects every catalogue entry whose client path equals it or lies below it, so using the
    object `ueId` selects all of its members. A used path that has no catalogue entry raises KeyError, so
    that a task can never silently be tagged as unchanged.
    """
    out = {}
    for direction, used_fields in (("request", request_fields), ("response", response_fields)):
        es = entries(api, client_version, operation, direction)
        kinds: set[str] = set()
        for used in used_fields:
            hits = [e for e in es if _prefix_match(used, e["client_path"]) or _prefix_match(used, e["server_path"])]
            if not hits:
                raise KeyError(f"{api} {client_version} {operation} {direction}: no catalogue entry for {used!r}")
            for e in hits:
                kinds.update(e["kinds"])
        out[direction] = [k for k in TAG_KINDS if k in kinds]
    return out


def catalogue_breaking_counts(
    api: str,
    client_version: str,
    operations: list[str] | None = None,
) -> tuple[int, int, int]:
    """Returns (total, request, response) breaking change counts from the catalogue.

    Counts are restricted to the operations used by the tasks.
    Breaking kinds include any of: renamed, restructured, unit_format, newly_required, changed_meaning, removed.
    """
    if operations is None:
        if api == "L1":
            operations = ["retrieveReachability"]
        elif api == "L2":
            operations = ["verifyLocation"]
        elif api == "L3":
            operations = ["createSession", "getSession", "deleteSession"]
        else:
            operations = []

    es_req = []
    es_res = []
    for op in operations:
        es_req.extend(entries(api, client_version, operation=op, direction="request"))
        es_res.extend(entries(api, client_version, operation=op, direction="response"))

    unique_req = {id(e): e for e in es_req}.values()
    unique_res = {id(e): e for e in es_res}.values()

    breaking_kinds = {"renamed", "restructured", "unit_format", "newly_required", "changed_meaning", "removed"}

    req_count = sum(1 for e in unique_req if any(k in breaking_kinds for k in e["kinds"]))
    res_count = sum(1 for e in unique_res if any(k in breaking_kinds for k in e["kinds"]))

    all_unique = {id(e): e for e in list(unique_req) + list(unique_res)}.values()
    total_count = sum(1 for e in all_unique if any(k in breaking_kinds for k in e["kinds"]))

    return total_count, req_count, res_count
