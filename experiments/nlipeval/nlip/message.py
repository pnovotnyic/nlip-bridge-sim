"""NLIP message model (ECMA-430 clause 5).

* Field names are accepted in any case (clause 5) and always written in lower case.
* Field values are kept exactly as given (clause 5 says case is not relevant to them, so receivers compare them
  without case, but nothing is rewritten).
* Fields the model does not know (for example `control`, or `label` on the first submessage) are kept in `extra`
  so that a message is written back intact.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

FORMATS = ("text", "token", "structured", "binary", "location", "generic")
RESERVED_PREFIXES = ("authentication", "conversation")
MESSAGE_KEYS = ("messagetype", "format", "subformat", "content", "submessages")
SUBMESSAGE_KEYS = ("label", "format", "subformat", "content")


class NLIPError(ValueError):
    """A message is not a valid NLIP message. `violations` is a list of `validate.Violation`."""

    def __init__(self, violations):
        self.violations = list(violations)
        super().__init__("; ".join(f"{v.requirement_id}: {v.detail}" for v in self.violations))


def lower_keys(d: dict) -> dict:
    """Return `d` with lower-case keys. Raises KeyError if two keys differ only in case."""
    out: dict = {}
    for k, v in d.items():
        lk = k.lower() if isinstance(k, str) else k
        if lk in out:
            raise KeyError(f"keys differ only in case: {k!r}")
        out[lk] = v
    return out


def _same(a: Any, b: Any) -> bool:
    return a.lower() == b.lower() if isinstance(a, str) and isinstance(b, str) else False


@dataclass
class Submessage:
    format: str
    subformat: str
    content: Any
    label: str | None = None
    extra: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict) -> "Submessage":
        d = lower_keys(d)
        known = {k: d[k] for k in SUBMESSAGE_KEYS if k in d}
        extra = {k: v for k, v in d.items() if k not in SUBMESSAGE_KEYS}
        return cls(known.get("format"), known.get("subformat"), known.get("content"), known.get("label"), extra)

    def to_dict(self) -> dict:
        out = {}
        if self.label is not None:
            out["label"] = self.label
        out.update({"format": self.format, "subformat": self.subformat, "content": self.content})
        out.update(self.extra)
        return out

    @property
    def is_token(self) -> bool:
        return _same(self.format, "token")


@dataclass
class Message:
    format: str
    subformat: str
    content: Any
    messagetype: str | None = None
    submessages: list[Submessage] | None = None
    extra: dict = field(default_factory=dict)

    # ------------------------------------------------------------------ construction
    @classmethod
    def from_dict(cls, d: Any, check: bool = True) -> "Message":
        if check:
            from nlipeval.nlip.validate import validate

            ok, violations = validate(d)
            if not ok:
                raise NLIPError(violations)
        d = lower_keys(d)
        subs = d.get("submessages")
        known = {k: d[k] for k in MESSAGE_KEYS if k in d}
        extra = {k: v for k, v in d.items() if k not in MESSAGE_KEYS}
        return cls(
            known.get("format"),
            known.get("subformat"),
            known.get("content"),
            known.get("messagetype"),
            [Submessage.from_dict(s) for s in subs] if isinstance(subs, list) else None,
            extra,
        )

    @classmethod
    def from_json(cls, text: str | bytes, check: bool = True) -> "Message":
        from nlipeval.nlip.validate import Violation

        try:
            obj = json.loads(text)
        except ValueError as e:
            raise NLIPError([Violation("E430-5-json-types", "", f"not valid JSON: {e}")]) from e
        return cls.from_dict(obj, check)

    @classmethod
    def text(cls, content: str, language: str = "English", **kw) -> "Message":
        return cls("text", language, content, **kw)

    # ------------------------------------------------------------------ output
    def to_dict(self) -> dict:
        out: dict = {}
        if self.messagetype is not None:
            out["messagetype"] = self.messagetype
        out.update({"format": self.format, "subformat": self.subformat, "content": self.content})
        out.update(self.extra)
        if self.submessages is not None:
            out["submessages"] = [s.to_dict() for s in self.submessages]
        return out

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    # ------------------------------------------------------------------ helpers
    @property
    def is_control(self) -> bool:
        """Control by MessageType (5.1.1) or by a boolean `control` field (6.3); see requirements.yaml."""
        return self.control_by_type or self.control_by_field

    @property
    def control_by_type(self) -> bool:
        return _same(self.messagetype, "control")

    @property
    def control_by_field(self) -> bool:
        return self.extra.get("control") is True

    def all_submessages(self) -> list[Submessage]:
        """The first submessage followed by the others, in order (the order is significant, 5.1.5)."""
        first = Submessage(self.format, self.subformat, self.content, None, {})
        return [first, *(self.submessages or [])]

    def tokens(self) -> list[Submessage]:
        """Token submessages in order, not counting the first submessage."""
        return [s for s in (self.submessages or []) if s.is_token]

    def add_token(self, subformat: str, content: str) -> None:
        self.submessages = [*(self.submessages or []), Submessage("token", subformat, content)]

    def with_authentication(self, token: str, suffix: str = "") -> "Message":
        """Add an authentication token (reserved prefix 'authentication', 6.2.2)."""
        self.add_token("authentication" + (f"_{suffix}" if suffix else ""), token)
        return self

    def with_conversation(self, token: str, suffix: str = "") -> "Message":
        """Add a conversation token (reserved prefix 'conversation', 6.2.1)."""
        self.add_token("conversation" + (f"_{suffix}" if suffix else ""), token)
        return self

    def find_token(self, prefix: str) -> Submessage | None:
        """First token (in the first submessage or in submessages) whose subformat starts with `prefix`."""
        for s in self.all_submessages():
            if s.is_token and isinstance(s.subformat, str) and s.subformat.lower().startswith(prefix.lower()):
                return s
        return None

    def texts(self, language: str | None = "english") -> list[str]:
        """Content of text submessages (all languages if `language` is None), in order."""
        return [
            s.content
            for s in self.all_submessages()
            if _same(s.format, "text") and isinstance(s.content, str) and (language is None or _same(s.subformat, language))
        ]


def reserved_prefix(subformat: str) -> str | None:
    """'authentication' or 'conversation' if the token subformat begins with that reserved prefix (6.2.1, 6.2.2)."""
    if not isinstance(subformat, str):
        return None
    low = subformat.lower()
    for p in RESERVED_PREFIXES:
        if low.startswith(p):
            return p
    return None
