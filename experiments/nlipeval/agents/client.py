"""Client agent (stage 06).

`ClientAgent.turn(messages)` calls the model and returns a parsed `ClientTurn`.
The agent maintains the system prompt; the caller owns the message history.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from nlipeval.agents.schemas import CLIENT_SCHEMA
from nlipeval.models.adapter import ModelAdapter, Result


@dataclass
class ClientTurn:
    action: str                   # request | answer | confirm | correct | abort | final
    message: str
    final: dict | None = None     # present only when action == "final"
    raw: dict = field(default_factory=dict)  # the full parsed object


def _extract_client_turn(result: Result) -> ClientTurn | None:
    """Return a `ClientTurn` from a successful, schema-valid model result, or None."""
    if not result.ok or result.parsed is None:
        return None
    d = result.parsed
    return ClientTurn(
        action=d.get("action", ""),
        message=d.get("message", ""),
        final=d.get("final"),
        raw=d,
    )


class ClientAgent:
    """Wraps the model adapter for the client side of a session."""

    def __init__(
        self,
        adapter: ModelAdapter,
        rung: str,
        system_prompt: str,
        session_id: str,
    ) -> None:
        self.adapter = adapter
        self.rung = rung
        self.system_prompt = system_prompt
        self.session_id = session_id
        self._call_count = 0
        self.n_action_repairs = 0   # B6: repair messages sent for a disallowed action

    def turn(
        self,
        messages: list[dict],
        purpose: str = "compose",
    ) -> tuple[ClientTurn | None, Result]:
        """Call the model and return (turn, result).

        `turn` is None when the model call failed or the reply did not parse.
        """
        self._call_count += 1
        result = self.adapter.call(
            self.rung,
            self.system_prompt,
            messages,
            schema=CLIENT_SCHEMA,
            purpose=purpose,
            session_id=self.session_id,
            role="client",
        )
        return _extract_client_turn(result), result

    @property
    def call_count(self) -> int:
        return self._call_count
