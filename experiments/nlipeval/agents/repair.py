"""One repair for a disallowed action (stage 08a, B6).

`turn_with_action_check(agent, messages, purpose, allowed, tolerated)` plays one agent turn. If the
parsed reply uses an action that is not allowed in the current state, the agent gets one message
("Your reply used action `x`, which is not allowed now. Allowed: ... Reply again.") and one more
call, logged with purpose `repair`. If the repaired reply is still not allowed, no turn is returned
and the result carries `error_type == "action_failure"` (the session ends `error_model`).

`tolerated` actions are not repaired: the harness handles them as protocol slips (for example a
server `execute` where `restate` is expected). They are not named in the repair message.
"""

from __future__ import annotations

import json
from typing import Any

ACTION_REPAIR_TEMPLATE = (
    "Your reply used action `{action}`, which is not allowed now. Allowed: {allowed}. Reply again."
)


def _merge_usage(a: dict | None, b: dict | None) -> dict:
    out: dict[str, Any] = {}
    for k in ("prompt_tokens", "completion_tokens", "reasoning_tokens"):
        va, vb = (a or {}).get(k), (b or {}).get(k)
        out[k] = None if va is None and vb is None else (va or 0) + (vb or 0)
    return out


def turn_with_action_check(agent: Any, messages: list[dict], purpose: str,
                           allowed: tuple[str, ...] | None, tolerated: tuple[str, ...] = ()) -> tuple[Any, Any]:
    """Return (turn, result). `agent.n_action_repairs` counts the repair messages sent."""
    turn, res = agent.turn(messages, purpose=purpose)
    if turn is None or allowed is None or turn.action in allowed or turn.action in tolerated:
        return turn, res

    agent.n_action_repairs += 1
    shown = ", ".join(f"`{a}`" for a in allowed)
    fix = messages + [
        {"role": "assistant", "content": json.dumps(turn.raw)},
        {"role": "user", "content": ACTION_REPAIR_TEMPLATE.format(action=turn.action, allowed=shown)},
    ]
    turn2, res2 = agent.turn(fix, purpose="repair")
    res2.usage = _merge_usage(res.usage, res2.usage)
    if turn2 is None:
        return None, res2
    if turn2.action not in allowed and turn2.action not in tolerated:
        res2.error_type = "action_failure"
        res2.error = (f"action {turn2.action!r} not allowed after repair (first reply {turn.action!r}); "
                      f"allowed: {', '.join(allowed)}")
        return None, res2
    return turn2, res2
