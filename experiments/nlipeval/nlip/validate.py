"""Validator for NLIP messages. `validate(obj)` returns `(ok, violations)`; every violation names a requirement id
from stage1/requirements.yaml. The validator works on the decoded JSON, so that wrong types and missing fields can
be reported (a typed model cannot represent them).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from nlipeval.nlip.message import FORMATS

BINARY_SUBFORMAT = re.compile(r"^(audio|image|sensor|generic)/\.?[^/\s]+$", re.IGNORECASE)


@dataclass(frozen=True)
class Violation:
    requirement_id: str
    path: str
    detail: str

    def __str__(self) -> str:
        return f"{self.requirement_id} at {self.path or '/'}: {self.detail}"


def _ci(d: dict, path: str, out: list[Violation]) -> dict:
    low: dict = {}
    for k, v in d.items():
        lk = k.lower()
        if lk in low:
            out.append(Violation("E430-5-case-insensitive", path, f"keys {k!r} and another key differ only in case"))
        low[lk] = v
    return low


def _check_submessage(d: Any, path: str, out: list[Violation], first: bool) -> None:
    if not isinstance(d, dict):
        out.append(Violation("E430-5.1.5-submessages-array", path, "a submessage must be a JSON object"))
        return
    f = _ci(d, path, out)
    ids = (
        ("E430-5.1.2-format-required", "E430-5.1.3-subformat-required", "E430-5.1.4-content-required")
        if first
        else ("E430-5.2.2-format-required", "E430-5.2.3-subformat-required", "E430-5.2.4-content-required")
    )
    for key, rid in zip(("format", "subformat", "content"), ids):
        if key not in f:
            out.append(Violation(rid, path, f"required field {key!r} is missing"))
    if "label" in f and not isinstance(f["label"], str) and not first:
        out.append(Violation("E430-5.2.1-label-string", path, "label must be a string"))
    fmt, sub = f.get("format"), f.get("subformat")
    if "format" in f:
        if not isinstance(fmt, str):
            out.append(Violation(ids[0], path, "format must be a string"))
            fmt = None
        elif fmt.lower() not in FORMATS:
            out.append(Violation("E430-5.3-format-values", path, f"format {fmt!r} is not one of {', '.join(FORMATS)}"))
            fmt = None
    if "subformat" in f and not isinstance(sub, str):
        out.append(Violation(ids[1], path, "subformat must be a string"))
        sub = None
    if fmt is None or sub is None:
        return
    low = fmt.lower()
    if low == "binary" and not BINARY_SUBFORMAT.match(sub):
        out.append(Violation("E430-5.3-binary-content", path, f"binary subformat {sub!r} is not <audio|image|sensor|generic>/<encoding>"))
    elif low == "token" and not sub:
        out.append(Violation("E430-5.3-token-subformat", path, "token subformat must begin with a prefix"))


def validate(obj: Any) -> tuple[bool, list[Violation]]:
    out: list[Violation] = []
    if not isinstance(obj, dict):
        return False, [Violation("E430-5-json-types", "", "a message must be a JSON object")]
    f = _ci(obj, "", out)
    _check_submessage(obj, "", out, first=True)
    if "messagetype" in f and not isinstance(f["messagetype"], str):
        out.append(Violation("E430-5.1.1-messagetype-string", "", "MessageType must be a string"))
    if "submessages" in f:
        subs = f["submessages"]
        if not isinstance(subs, list):
            out.append(Violation("E430-5.1.5-submessages-array", "submessages", "submessages must be an array"))
        else:
            for i, s in enumerate(subs):
                _check_submessage(s, f"submessages[{i}]", out, first=False)
    return not out, out
