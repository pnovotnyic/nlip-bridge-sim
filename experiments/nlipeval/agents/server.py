"""Server agent and NLIP end-point (stage 06).

`ServerAgent.turn(messages, purpose)` calls the model and returns a `ServerTurn`.

`make_server_app(agent, wire_log)` returns a FastAPI app that:
- accepts NLIP messages at POST /nlip;
- calls the agent;
- returns the agent's natural-language reply as an NLIP text message;
- maintains the multi-turn message history in the NLIP conversation state.

The structured JSON the agent returns stays inside the harness; only `ServerTurn.message`
travels on the wire.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

from nlipeval.agents.schemas import SERVER_SCHEMA
from nlipeval.models.adapter import ModelAdapter, Result
from nlipeval.nlip.message import Message
from nlipeval.nlip.transport import Context, create_app


@dataclass
class ServerTurn:
    action: str                       # ask | restate | execute | decline | report
    message: str
    plan: dict | None = None          # required with restate / execute
    asked_fields: list[str] | None = None  # required with ask
    raw: dict = field(default_factory=dict)


def _extract_server_turn(result: Result) -> ServerTurn | None:
    if not result.ok or result.parsed is None:
        return None
    d = result.parsed
    return ServerTurn(
        action=d.get("action", ""),
        message=d.get("message", ""),
        plan=d.get("plan"),
        asked_fields=d.get("asked_fields"),
        raw=d,
    )


class ServerAgent:
    """Wraps the model adapter for the server side of a session."""

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
        self.history: list[dict] | None = None   # set by the NLIP end-point on the first message

    def turn(
        self,
        messages: list[dict],
        purpose: str = "plan",
    ) -> tuple[ServerTurn | None, Result]:
        """Call the model and return (turn, result)."""
        self._call_count += 1
        result = self.adapter.call(
            self.rung,
            self.system_prompt,
            messages,
            schema=SERVER_SCHEMA,
            purpose=purpose,
            session_id=self.session_id,
            role="server",
        )
        return _extract_server_turn(result), result

    @property
    def call_count(self) -> int:
        return self._call_count


# --------------------------------------------------------------------------- NLIP end-point

# Per-conversation state stored inside the NLIP conversation context.
_MSG_HISTORY_KEY = "_server_messages"


def make_server_app(
    agent: ServerAgent,
    on_turn: Callable[[ServerTurn | None, Result, str], None] | None = None,
) -> Any:
    """Return a FastAPI app that wraps `agent` behind an NLIP end-point.

    Args:
        agent: the `ServerAgent` to call.
        on_turn: optional callback invoked after every model call with
            (server_turn_or_none, result, conversation_id).
            The harness uses this to capture the structured turn for logging.
    """

    async def handler(msg: Message, ctx: Context) -> Message:
        # Reconstruct the multi-turn history from the conversation state.
        history: list[dict] = ctx.state.setdefault(_MSG_HISTORY_KEY, [])
        agent.history = history     # the harness continues this conversation for report calls

        # The client's natural-language text is extracted from the NLIP message.
        client_texts = msg.texts("english") or msg.texts(None)
        client_text = " ".join(client_texts).strip() if client_texts else msg.content or ""

        history.append({"role": "user", "content": client_text})

        turn, result = agent.turn(list(history), purpose="plan")

        if on_turn is not None:
            on_turn(turn, result, ctx.conversation_id)

        if turn is None:
            # Model failure: return a minimal NLIP text error.
            resp_text = "Internal error: could not generate a response."
        else:
            resp_text = turn.message
            history.append({"role": "assistant", "content": json.dumps(turn.raw)})

        return Message.text(resp_text)

    return create_app(handler)
