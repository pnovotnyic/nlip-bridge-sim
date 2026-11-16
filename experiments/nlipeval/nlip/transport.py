"""HTTP binding of NLIP (ECMA-431): a FastAPI server end-point and an httpx client.

Server (`create_app`):
* POST /nlip (and /nlip/) accepts an NLIP message and answers with an NLIP message (ECMA-431 clause 6, ECMA-430 6.1).
* Every incoming message is checked with `validate`; an invalid one is answered with HTTP 400 and an NLIP text message.
* Tokens (6.2): all token submessages of the request are returned unchanged and in order, unless the application
  already put a token with the same subformat in its response (it created or replaced that token itself).
* Conversation tokens (6.2.1): if the client sent none, the server creates `conversation_<id>`, and `ctx.state`
  is a dict that persists across requests carrying the same token.
* Control messages (5.1.1, 6.3): answered with a control message (MessageType `control`, and `control: true` if
  the request carried that field). A control request for large uploads (6.4) is answered with a structured/uri
  submessage when an `upload_url` is configured.
* Structured content whose subformat the server does not know is answered with a text message (5.3).

Client (`NLIPClient`): keeps the conversation token the server created, sends it back, returns the tokens it
should echo, and keeps a log of every wire message in `wire`, each checked with `validate`.
"""
from __future__ import annotations

import inspect
import json
import secrets
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from nlipeval.nlip.message import Message, NLIPError, Submessage, reserved_prefix
from nlipeval.nlip.validate import Violation, validate

KNOWN_STRUCTURED = ("json", "uri", "xml", "html")
NLIP_PATH = "/nlip"


@dataclass
class Context:
    conversation_id: str
    state: dict = field(default_factory=dict)


Handler = Callable[[Message, Context], "Message | Awaitable[Message]"]


def echo_handler(msg: Message, ctx: Context) -> Message:
    """Returns the request (a fresh copy). Used by the interoperability script."""
    return Message.from_dict(msg.to_dict(), check=False)


def ack_handler(msg: Message, ctx: Context) -> Message:
    """Answers every data message with the text 'ok'. Used by the conformance checks (nothing is echoed by the app)."""
    ctx.state["count"] = ctx.state.get("count", 0) + 1
    return Message.text("ok")


def _error(text: str, status: int = 400) -> JSONResponse:
    return JSONResponse(Message.text(text).to_dict(), status_code=status)


def create_app(handler: Handler = ack_handler, upload_url: str | None = None, issue_conversation: bool = True) -> FastAPI:
    app = FastAPI()
    app.state.conversations = {}

    async def endpoint(request: Request):
        raw = await request.body()
        try:
            obj = json.loads(raw)
        except ValueError:
            return _error("The request is not valid JSON.")
        ok, violations = validate(obj)
        if not ok:
            return _error("Invalid NLIP message: " + "; ".join(str(v) for v in violations))
        msg = Message.from_dict(obj, check=False)

        # ---- conversation token
        conv = msg.find_token("conversation")
        created_here = False
        if conv is not None:
            conv_id = str(conv.content)
        elif issue_conversation:
            conv_id = secrets.token_urlsafe(8)
            created_here = True
        else:
            conv_id = ""
        ctx = Context(conv_id, app.state.conversations.setdefault(conv_id, {}))

        # ---- the response
        if msg.is_control:
            resp = _control_response(msg, upload_url)
        elif msg.format.lower() == "structured" and msg.subformat.lower() not in KNOWN_STRUCTURED and not _supported(handler, msg):
            resp = Message.text(f"The structured subformat {msg.subformat!r} is not understood or supported by this end-point.")
        else:
            out = handler(msg, ctx)
            resp = await out if inspect.isawaitable(out) else out

        # ---- tokens: return the request's tokens, add ours
        have = {(s.subformat or "").lower() for s in resp.all_submessages() if s.is_token}
        echoed = [Submessage(s.format, s.subformat, s.content, s.label) for s in msg.all_submessages() if s.is_token and (s.subformat or "").lower() not in have]
        # the first submessage of the request may itself be a token; it is echoed as a submessage of the response
        if echoed:
            resp.submessages = [*(resp.submessages or []), *echoed]
        if created_here:
            resp.add_token(f"conversation_{conv_id}", conv_id)
        ok, violations = validate(resp.to_dict())
        assert ok, violations  # the server never sends an invalid message
        return JSONResponse(resp.to_dict())

    app.add_api_route(NLIP_PATH, endpoint, methods=["POST"])
    app.add_api_route(NLIP_PATH + "/", endpoint, methods=["POST"])
    return app


def _supported(handler: Handler, msg: Message) -> bool:
    return bool(getattr(handler, "structured_subformats", ()) and msg.subformat.lower() in handler.structured_subformats)


def _control_response(msg: Message, upload_url: str | None) -> Message:
    wants_upload = any("upload" in t.lower() for t in msg.texts(None))
    if wants_upload and upload_url:
        resp = Message("structured", "uri", upload_url, messagetype="control")
    else:
        resp = Message.text("No control parameters are defined by this end-point.", messagetype="control")
    if msg.control_by_field:
        resp.extra["control"] = True
    return resp


# ----------------------------------------------------------------------------- client
class NLIPClient:
    def __init__(self, base_url: str, timeout: float = 30.0, client: httpx.Client | None = None, path: str = NLIP_PATH):
        self.url = base_url.rstrip("/") + path
        self.http = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self.conversation: Submessage | None = None
        self.server_tokens: list[Submessage] = []  # tokens created by the server, returned on the next request
        self.wire: list[dict] = []  # {"direction", "body", "ok", "violations"}

    def _log(self, direction: str, body: Any) -> None:
        ok, v = validate(body)
        self.wire.append({"direction": direction, "body": body, "ok": ok, "violations": [str(x) for x in v]})

    def send(self, msg: Message, track: bool = True) -> Message:
        if track:
            have = {(s.subformat or "").lower() for s in msg.tokens()}
            for t in self.server_tokens:
                if (t.subformat or "").lower() not in have:
                    msg.add_token(t.subformat, t.content)
        body = msg.to_dict()
        self._log("request", body)
        r = self.http.post(self.url, json=body)
        self.last_status = r.status_code
        data = r.json()
        self._log("response", data)
        resp = Message.from_dict(data, check=False)
        if track:
            mine = {(s.subformat or "").lower() for s in msg.tokens()}
            for s in resp.tokens():  # tokens the server created are returned on the next request (6.2)
                if (s.subformat or "").lower() not in mine:
                    self.server_tokens = [t for t in self.server_tokens if t.subformat.lower() != s.subformat.lower()] + [s]
        return resp

    def post_raw(self, body: Any) -> tuple[int, Any]:
        """POST any JSON body (also an invalid message) and return (status, decoded JSON or None). Both sides are logged."""
        self._log("request", body)
        r = self.http.post(self.url, json=body)
        try:
            data = r.json()
        except ValueError:
            data = None
        self._log("response", data)
        return r.status_code, data

    def request_upload_url(self) -> str:
        """6.4: ask for an out-of-band upload end-point with a control message; returns the URI from the answer."""
        resp = self.send(Message.text("Please send me an end-point for large uploads.", messagetype="control"), track=False)
        for s in resp.all_submessages():
            if s.format.lower() == "structured" and s.subformat.lower() == "uri":
                return str(s.content)
        raise NLIPError([Violation("E430-6.4-response-control-uri", "", "no structured/uri submessage in the answer")])

    def close(self) -> None:
        self.http.close()


def create_upload_app() -> FastAPI:
    """A stand-in for the large-upload end-point that `upload_url` points to (ECMA-431 6.1: another port)."""
    app = FastAPI()

    @app.post("/upload")
    async def upload(request: Request):
        return {"received_bytes": len(await request.body())}

    return app
