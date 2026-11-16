"""The Stage 1 conformance checks (ECMA-430 clauses 5-7, ECMA-431 clauses 6-6.1).

Every check names its requirement id (requirements.yaml). Each is run once per implementation by run_suite.py;
a check that does not apply to an implementation (it has no message model, no server, no client builder) is n/a.
"""
from __future__ import annotations

import json

from stage1.harness.adapters import UPLOAD_TEXT
from stage1.harness.checks import (
    BASE,
    Ctx,
    Fail,
    NA,
    check,
    intact,
    lower_keys,
    msg,
    sub,
    submessages_of,
    tokens_of,
)

CONV = sub("token", "conversation_abc", "c-123")
AUTH = sub("token", "authentication_x", "secret-456")


def _echo_or_ack(ctx: Ctx, app: str, body: dict):
    return ctx.server().post(app, body)


# =============================================================== G1 any case (clause 5)
@check("C01", "E430-5-case-insensitive", "G1", "Field names in any capitalisation are accepted (Format/Subformat/Content, FORMAT, MessageType)",
       also=("E430-5.3-format-key-case",), kind="accept")
def c01(ctx: Ctx):
    ctx.accept([
        {"Format": "text", "Subformat": "English", "Content": "Hi"},
        {"FORMAT": "text", "SUBFORMAT": "English", "CONTENT": "Hi"},
        {"MessageType": "chat", "format": "text", "subformat": "English", "content": "Hi"},
    ], reader_ok=True, keep_intact=False)


@check("C02", "E430-5-case-insensitive", "G1", "Values are matched without regard to case (format 'TEXT', subformat 'english')", kind="accept")
def c02(ctx: Ctx):
    ctx.accept([
        {"format": "TEXT", "subformat": "ENGLISH", "content": "Hi"},
        {"format": "Text", "subformat": "english", "content": "Hi", "submessages": [{"format": "TOKEN", "subformat": "Conversation_1", "content": "c"}]},
    ], reader_ok=True, keep_intact=False)


@check("C03", "E430-5-case-insensitive", "G1", "Capitalised names in submessages (Label, Format, Subformat, Content) are accepted and kept",
       also=("E430-5.2.1-label-key",), kind="accept")
def c03(ctx: Ctx):
    ctx.accept([{**BASE, "submessages": [{"Label": "a", "Format": "text", "Subformat": "English", "Content": "x"}]}], keep_intact=True)


# =============================================================== G2 required and optional fields (5.1-5.2)
@check("C04", "E430-5.1.2-format-required", "G2", "A message without format is rejected", also=("E430-5.3-format-key-case",), kind="reject")
def c04(ctx: Ctx):
    ctx.reject([{"subformat": "English", "content": "Hi"}])


@check("C05", "E430-5.1.3-subformat-required", "G2", "A message without subformat is rejected", kind="reject")
def c05(ctx: Ctx):
    ctx.reject([{"format": "text", "content": "Hi"}])


@check("C06", "E430-5.1.4-content-required", "G2", "A message without content is rejected", kind="reject")
def c06(ctx: Ctx):
    ctx.reject([{"format": "text", "subformat": "English"}])


@check("C07", "E430-5.1.1-messagetype-optional", "G2", "A message without MessageType is accepted; with MessageType 'chat' (a value other than control) it is accepted as a data message and kept",
       also=("E430-5.1.1-other-values-data",), kind="accept")
def c07(ctx: Ctx):
    ctx.accept([BASE, msg(messagetype="chat")], reader_ok=True, keep_intact=True)


@check("C08", "E430-5.1.1-messagetype-string", "G2", "A MessageType that is not a string is rejected", kind="reject")
def c08(ctx: Ctx):
    ctx.reject([msg(messagetype=7), msg(messagetype=["control"])])


@check("C09", "E430-5.1.5-submessages-array", "G2", "submessages that is not an array is rejected", kind="reject")
def c09(ctx: Ctx):
    ctx.reject([msg(submessages={"format": "text"}), msg(submessages="x")])


@check("C10", "E430-5.1.5-order-significant", "G2", "Submessages come back in the order they were sent",
       also=("E430-5.1.5-submessages-array", "E430-5.1.4-content-represented"), kind="accept")
def c10(ctx: Ctx):
    body = msg(submessages=[sub("text", "French", "un"), sub("structured", "json", {"k": [1, 2]}), sub("token", "conversation_a", "c"), sub("binary", "image/png", "AAEC"), sub("location", "gps", "1.0,2.0")])
    ctx.accept([body], keep_intact=True)


@check("C11", "E430-5.2.1-label-string", "G2", "A Label that is not a string is rejected", also=("E430-5.2.1-label-key",), kind="reject")
def c11(ctx: Ctx):
    ctx.reject([msg(submessages=[{"label": 1, "format": "text", "subformat": "English", "content": "x"}])])


@check("C12", "E430-5.2.2-format-required", "G2", "A submessage without format is rejected", kind="reject")
def c12(ctx: Ctx):
    ctx.reject([msg(submessages=[{"subformat": "English", "content": "x"}])])


@check("C13", "E430-5.2.3-subformat-required", "G2", "A submessage without subformat is rejected", kind="reject")
def c13(ctx: Ctx):
    ctx.reject([msg(submessages=[{"format": "text", "content": "x"}])])


@check("C14", "E430-5.2.4-content-required", "G2", "A submessage without content is rejected", kind="reject")
def c14(ctx: Ctx):
    ctx.reject([msg(submessages=[{"format": "text", "subformat": "English"}])])


@check("C15", "E430-5.1.4-content-represented", "G2", "Content of type number, array, boolean and null is accepted and kept (Annex A, informative)",
       note="Annex A allows string, number, object, array, boolean and null as Content; Table 1 describes most formats as strings.", kind="accept", reading="ambiguous")
def c15(ctx: Ctx):
    ctx.accept([msg(format="generic", subformat="acme", content=5), msg(format="generic", subformat="acme", content=[1, "a"]),
                msg(format="generic", subformat="acme", content=True), msg(format="generic", subformat="acme", content=None)], keep_intact=True)


# =============================================================== G3 formats and subformats (5.3)
@check("C16", "E430-5.3-format-values", "G3", "A format outside Table 1 is rejected (a first-level message with format 'error' or 'bogus')",
       note="Table 1 lists text, token, structured, binary, location, generic.", kind="reject", reading="ambiguous")
def c16(ctx: Ctx):
    ctx.reject([msg(format="error", subformat="text"), msg(format="bogus")])


@check("C17", "E430-5.3-format-values", "G3", "A submessage with format 'error' is rejected", kind="reject", reading="ambiguous")
def c17(ctx: Ctx):
    ctx.reject([msg(submessages=[sub("error", "text", "boom")])])


@check("C18", "E430-5.3-format-values", "G3", "Every format of Table 1 is accepted, with its content intact",
       also=("E430-5.3-location-subformat", "E430-5.3-binary-content", "E430-5.3-binary-encoding", "E430-5.1.4-content-represented"), kind="accept")
def c18(ctx: Ctx):
    ctx.accept([
        msg(),
        msg(format="token", subformat="conversation_1", content="c"),
        msg(format="structured", subformat="json", content={"a": [1, {"b": None}], "c": True}),
        msg(format="structured", subformat="uri", content="https://example.com/x"),
        msg(format="binary", subformat="image/png", content="iVBORw0KGgo="),
        msg(format="binary", subformat="audio/.mp3", content="AAEC"),
        msg(format="location", subformat="text", content="Hursley, UK"),
        msg(format="location", subformat="GPS", content="51.0,-1.4"),
        msg(format="generic", subformat="acme-ext", content="x"),
    ], keep_intact=True)


@check("C19", "E430-5-json-types", "G3", "Text that is not JSON, and JSON that is not an object, are rejected", kind="reject")
def c19(ctx: Ctx):
    problems = []
    n = 0
    for name, role in (("model", ctx.impl.model), ("server", ctx.impl.server)):
        if role is None:
            continue
        fn = getattr(role, "parse_json", None) or getattr(role, "parse_text", None)
        if fn is None:
            continue
        for text in ('{"format": "text", "subformat": "English", "content": ', "[1, 2]", '"just a string"', "not json"):
            n += 1
            if fn(text).accepted:
                problems.append(f"[{name}] accepted {text!r}")
    if not n:
        raise NA(f"{ctx.impl.label} has no way to parse JSON text")
    if problems:
        raise Fail("; ".join(problems))


@check("C20", "E430-5.3-process-all-fields", "G3", "A text/English message is processed, in any case spelling of the language",
       also=("E430-5.3-token-subformat",), kind="accept")
def c20(ctx: Ctx):
    ctx.accept([msg(subformat="English"), msg(subformat="english"), msg(subformat="ENGLISH")], reader_ok=True, keep_intact=True)


@check("C21", "E430-5.3-binary-content", "G3", "A binary subformat whose content type is not audio, image, sensor or generic is rejected",
       note="Only the four values listed in Table 1 are used; the table's own 'video/.mp3' example contradicts its text (see requirements.yaml).", kind="reject")
def c21(ctx: Ctx):
    ctx.reject([msg(format="binary", subformat="document/pdf", content="AAEC")])


@check("C22", "E430-5.3-structured-unknown-language", "G3", "A structured message in a programming language the end-point does not support is answered with a text message",
       also=("E430-6.1-server-response",), reading="application")
def c22(ctx: Ctx):
    s = ctx.server()
    r = s.post("ack", msg(format="structured", subformat="cobol", content="DISPLAY 'HELLO'."))
    ctx.expect(r.status == 200 and isinstance(r.body, dict), f"HTTP {r.status}")
    ctx.expect(str(lower_keys(r.body).get("format", "")).lower() == "text", f"answered with format {lower_keys(r.body).get('format')!r}, not text")
    ctx.expect("cobol" in str(r.body).lower() or "support" in str(r.body).lower() or "understood" in str(r.body).lower(),
               "the text answer does not tell the peer that the language is not understood or supported")


@check("C47", "E430-5.3-format-values", "G3", "Every message the implementation builds uses a format of Table 1 (text, token, structured, binary, location, generic)",
       note="Sender side of 'The format field must have one of the values described in Table 1'.")
def c47(ctx: Ctx):
    role = next((r for r in (ctx.impl.builder, ctx.impl.model) if r is not None and hasattr(r, "build")), None)
    if role is None:
        raise NA(f"{ctx.impl.label} has no code that builds messages")
    allowed = {"text", "token", "structured", "binary", "location", "generic"}
    built, bad = 0, []
    for kind in ("text", "image", "auth_token", "conv_token", "control_upload", "error"):
        try:
            body = role.build(kind)["body"]
        except NotImplementedError:
            continue
        built += 1
        for x in submessages_of(body):
            if str(x.get("format", "")).lower() not in allowed:
                bad.append(f"{kind}: format {x.get('format')!r}")
    ctx.expect(built, "nothing could be built")
    ctx.expect(not bad, "builds messages with a format outside Table 1: " + "; ".join(bad))


@check("C48", "E430-5.3-binary-content", "G3", "Binary submessages the implementation builds have a subformat <audio|image|sensor|generic>/<encoding>",
       note="Sender side of the binary subformat rule; the SDK writes 'image/png', the TypeScript client writes 'png'.")
def c48(ctx: Ctx):
    role = next((r for r in (ctx.impl.builder, ctx.impl.model) if r is not None and hasattr(r, "build")), None)
    if role is None:
        raise NA(f"{ctx.impl.label} has no code that builds messages")
    try:
        body = role.build("image")["body"]
    except NotImplementedError:
        raise NA("no code that builds a binary message")
    bins = [x for x in submessages_of(body) if str(x.get("format", "")).lower() == "binary"]
    ctx.expect(bins, f"no binary submessage in {json.dumps(body)}")
    import re

    bad = [x["subformat"] for x in bins if not re.match(r"^(audio|image|sensor|generic)/\.?[^/\s]+$", str(x["subformat"]), re.I)]
    ctx.expect(not bad, f"binary subformat {bad} is not <content>/<encoding>")


@check("C49", "E430-5.1.1-messagetype-string", "G2", "The server's answer is a valid NLIP message: no null where a field is optional (MessageType string, submessages array)",
       also=("E430-6.1-server-response", "E430-5.1.5-submessages-array"), reading="ambiguous",
       note="Annex A (informative) types MessageType as string and Submessages as array, so null is not allowed; a tolerant receiver might accept null for an absent field.")
def c49(ctx: Ctx):
    from nlipeval.nlip.validate import validate

    r = ctx.server().post("ack", BASE)
    ctx.expect(r.status == 200 and isinstance(r.body, dict), f"HTTP {r.status}")
    ok, v = validate(r.body)
    ctx.expect(ok, "the answer is not a valid NLIP message: " + "; ".join(str(x) for x in v))


# =============================================================== G4 initial request (6.1)
@check("C23", "E430-6.1-server-response", "G4", "A first request with a first submessage is answered with an NLIP message (format, subformat, content)",
       also=("E430-6.1-client-first-submessage", "E430-7.3-endpoint"))
def c23(ctx: Ctx):
    s = ctx.server()
    r = s.post("ack", BASE)
    ctx.expect(r.status == 200, f"HTTP {r.status}")
    ctx.expect(isinstance(r.body, dict), "the answer is not a JSON object")
    b = lower_keys(r.body)
    ctx.expect(all(k in b for k in ("format", "subformat", "content")), f"the answer lacks a first submessage: {sorted(b)}")


@check("C24", "E430-6.1-client-first-submessage", "G4", "The client's first request contains the first submessage (format, subformat, content)")
def c24(ctx: Ctx):
    b = ctx.builder().build("text")["body"]
    ctx.expect(all(k in lower_keys(b) for k in ("format", "subformat", "content")), f"request is {json.dumps(b)}")


# =============================================================== G5 token submessages returned unchanged (6.2)
@check("C25", "E430-6.2-token-echo", "G5", "A conversation token sent in a submessage is returned with identical format, subformat and content",
       also=("E430-6.2.1-token-opaque",), reading="application")
def c25(ctx: Ctx):
    s = ctx.server()
    r = s.post("ack", msg(submessages=[CONV]))
    ctx.expect(r.status == 200 and isinstance(r.body, dict), f"HTTP {r.status}")
    back = [(t["format"].lower(), t["subformat"], t["content"]) for t in tokens_of(r.body)]
    ctx.expect(("token", "conversation_abc", "c-123") in back, f"tokens in the answer: {back}")


@check("C26", "E430-6.2-token-echo", "G5", "An authentication token sent in a submessage is returned unchanged", reading="application")
def c26(ctx: Ctx):
    s = ctx.server()
    r = s.post("ack", msg(submessages=[AUTH]))
    ctx.expect(r.status == 200 and isinstance(r.body, dict), f"HTTP {r.status}")
    back = [(t["subformat"], t["content"]) for t in tokens_of(r.body)]
    ctx.expect(("authentication_x", "secret-456") in back, f"tokens in the answer: {back}")


@check("C27", "E430-6.2-multiple-tokens", "G5", "Several tokens sent at once (conversation, authentication, free subformat) are all returned unchanged",
       also=("E430-6.2-free-subformat",), reading="application")
def c27(ctx: Ctx):
    s = ctx.server()
    sent = [CONV, AUTH, sub("token", "group_7", "g-9")]
    r = s.post("ack", msg(submessages=sent))
    ctx.expect(r.status == 200 and isinstance(r.body, dict), f"HTTP {r.status}")
    back = {(t["subformat"], t["content"]) for t in tokens_of(r.body)}
    missing = [(t["subformat"], t["content"]) for t in sent if (t["subformat"], t["content"]) not in back]
    ctx.expect(not missing, f"not returned: {missing}")


@check("C28", "E430-6.2-token-echo", "G5", "A token in the first submessage (the message itself is a token) is returned", reading="application")
def c28(ctx: Ctx):
    s = ctx.server()
    r = s.post("ack", {"format": "token", "subformat": "conversation_abc", "content": "c-123"})
    ctx.expect(r.status == 200 and isinstance(r.body, dict), f"HTTP {r.status}")
    back = [(t["subformat"], t["content"]) for t in tokens_of(r.body)]
    ctx.expect(("conversation_abc", "c-123") in back, f"tokens in the answer: {back}")


@check("C29", "E430-6.2-token-echo", "G5", "Tokens sent with capitalised names and values are returned with the same content",
       also=("E430-5-case-insensitive",), reading="application")
def c29(ctx: Ctx):
    s = ctx.server()
    r = s.post("ack", msg(submessages=[{"Format": "Token", "Subformat": "Conversation_abc", "Content": "Mixed-Case-Id"}]))
    ctx.expect(r.status == 200 and isinstance(r.body, dict), f"HTTP {r.status}")
    back = [t["content"] for t in tokens_of(r.body)]
    ctx.expect("Mixed-Case-Id" in back, f"tokens in the answer: {tokens_of(r.body)}")


@check("C30", "E430-6.2-token-echo", "G5", "A token the end-point created itself (conversation token on a first request) is not an error and, if sent back, is returned",
       note="Second half: a token created by the server and sent by the client comes back again.", reading="application")
def c30(ctx: Ctx):
    s = ctx.server()
    r1 = s.post("ack", BASE)
    ctx.expect(r1.status == 200 and isinstance(r1.body, dict), f"first request: HTTP {r1.status}")
    made = tokens_of(r1.body)
    if not made:
        raise NA("the end-point creates no token of its own on a first request (nothing to send back)")
    r2 = s.post("ack", msg(submessages=[{k: v for k, v in made[0].items() if k != "label" or v is not None}]))
    ctx.expect(r2.status == 200 and isinstance(r2.body, dict), f"second request: HTTP {r2.status}")
    back = [(t["subformat"], t["content"]) for t in tokens_of(r2.body)]
    ctx.expect((made[0]["subformat"], made[0]["content"]) in back, f"sent {made[0]}, got back {back}")


@check("C46", "E430-6.2.1-conversation-prefix", "G5", "A token with the bare subformat 'conversation' is returned unchanged",
       also=("E430-6.2-token-echo",), note="The form nlip_sdk itself creates; C25 uses the prefix form conversation_<id>.", reading="application")
def c46(ctx: Ctx):
    s = ctx.server()
    r = s.post("ack", msg(submessages=[sub("token", "conversation", "bare-77")]))
    ctx.expect(r.status == 200 and isinstance(r.body, dict), f"HTTP {r.status}")
    back = [(t["subformat"], t["content"]) for t in tokens_of(r.body)]
    ctx.expect(("conversation", "bare-77") in back, f"tokens in the answer: {back}")


# =============================================================== G6 reserved token prefixes (6.2.1, 6.2.2)
@check("C31", "E430-6.2.2-auth-reserved-prefix", "G6", "The subformat 'authentication_x' is recognised as an authentication token",
       also=("E430-5.3-token-subformat",))
def c31(ctx: Ctx):
    m = ctx.model()
    r = m.recognise("authentication_x")
    ctx.expect(r["auth"] is True, f"recognised as authentication: {r['auth']}")
    ctx.expect(m.recognise("Authentication")["auth"] is True, "bare 'Authentication' not recognised")


@check("C32", "E430-6.2.1-conversation-prefix", "G6", "The subformats 'conversation' and 'conversation_9.2.3.5' are recognised as conversation tokens")
def c32(ctx: Ctx):
    m = ctx.model()
    ctx.expect(m.recognise("conversation")["conv"] is True, "bare 'conversation' not recognised")
    ctx.expect(m.recognise("conversation_9.2.3.5")["conv"] is True, "'conversation_9.2.3.5' not recognised")


@check("C33", "E430-6.2.2-auth-reserved-prefix", "G6", "The token the implementation builds for authentication uses the subformat 'authentication'")
def c33(ctx: Ctx):
    b = ctx.model().build("auth_token")["body"]
    subs = [t["subformat"] for t in tokens_of(b)]
    ctx.expect(subs and subs[0].lower().startswith("authentication"), f"the authentication token is sent with subformat {subs}")


@check("C34", "E430-6.2.2-auth-return-unmodified", "G6", "A token with subformat 'authentication_x' is found as the authentication token and returned unmodified",
       also=("E430-6.2.1-conversation-prefix",), reading="application")
def c34(ctx: Ctx):
    if ctx.impl.server is not None:
        r = ctx.server().post("ack", msg(submessages=[AUTH, CONV]))
        ctx.expect(r.status == 200 and isinstance(r.body, dict), f"HTTP {r.status}")
        back = [(t["subformat"], t["content"]) for t in tokens_of(r.body)]
        ctx.expect(("authentication_x", "secret-456") in back, f"tokens in the answer: {back}")
        return
    r = ctx.model().extract(msg(submessages=[AUTH, CONV]))
    ctx.expect(r["auth"] == "secret-456", f"authentication token read as {r['auth']!r}")
    ctx.expect(r["conv"] == "c-123", f"conversation token read as {r['conv']!r}")


# =============================================================== G7 control (6.3)
CTRL_TYPE = msg(messagetype="control", content="query policies")
CTRL_FIELD = {"control": True, "format": "text", "subformat": "English", "content": "query policies"}


def _is_control_answer(body: dict, by: str) -> bool:
    b = lower_keys(body)
    if by == "type":
        return str(b.get("messagetype", "")).lower() == "control"
    return b.get("control") is True


@check("C35", "E430-6.3-control-response", "G7", "A message with MessageType 'control' is answered with a message with MessageType 'control'",
       also=("E430-5.1.1-control-reserved",), reading="application")
def c35(ctx: Ctx):
    r = ctx.server().post("ack", CTRL_TYPE)
    ctx.expect(r.status == 200 and isinstance(r.body, dict), f"HTTP {r.status}")
    ctx.expect(_is_control_answer(r.body, "type"), f"the answer is not a control message: {json.dumps(r.body)}")


@check("C36", "E430-6.3-control-response", "G7", "A message with the field control=true is answered with a message with control=true",
       note="The second reading of 6.3 (a 'control field'); see the ambiguity noted in requirements.yaml.", reading="ambiguous")
def c36(ctx: Ctx):
    r = ctx.server().post("ack", CTRL_FIELD)
    ctx.expect(r.status == 200 and isinstance(r.body, dict), f"HTTP {r.status}")
    ctx.expect(_is_control_answer(r.body, "field"), f"the answer does not carry control=true: {json.dumps(r.body)}")


# =============================================================== G8 out-of-band transfer (6.4)
@check("C37", "E430-6.4-request-control", "G8", "The request for an upload end-point is a message with MessageType 'control'",
       also=("E430-6.4-request-text",))
def c37(ctx: Ctx):
    b = ctx.builder().build("control_upload")["body"]
    lb = lower_keys(b)
    ctx.expect(str(lb.get("messagetype", "")).lower() == "control", f"the client's request is {json.dumps(b)}")
    first = submessages_of(b)[0]
    ctx.expect(str(first.get("format", "")).lower() == "text", "the request does not include a text format request")


@check("C38", "E430-6.4-response-control-uri", "G8", "A control request for large uploads is answered with a control message holding a structured/uri submessage",
       also=("E430-6.1-server-response",), reading="application")
def c38(ctx: Ctx):
    s = ctx.server()
    if not s.has_upload:
        r = s.post("ack", msg(messagetype="control", content=UPLOAD_TEXT))
        ctx.expect(r.status == 200 and isinstance(r.body, dict), f"HTTP {r.status}")
        b = lower_keys(r.body)
        found = [x for x in submessages_of(r.body) if str(x.get("format", "")).lower() == "structured" and str(x.get("subformat", "")).lower() == "uri"]
        raise Fail(f"no structured/uri submessage in the answer (MessageType {b.get('messagetype')!r}): {json.dumps(r.body)}")
    r = s.post("ack", msg(messagetype="control", content=UPLOAD_TEXT))
    ctx.expect(r.status == 200 and isinstance(r.body, dict), f"HTTP {r.status}")
    ctx.expect(_is_control_answer(r.body, "type"), f"the answer is not a control message: {json.dumps(r.body)}")
    found = [x for x in submessages_of(r.body) if str(x.get("format", "")).lower() == "structured" and str(x.get("subformat", "")).lower() == "uri"]
    ctx.expect(found, f"no structured/uri submessage: {json.dumps(r.body)}")


@check("C39", "E430-6.4-response-endpoint", "G8", "The URI in the answer is a well-formed URL on a different port than the NLIP end-point",
       also=("E431-6.1-upload-port",), reading="application")
def c39(ctx: Ctx):
    from urllib.parse import urlparse

    s = ctx.server()
    r = s.post("ack", msg(messagetype="control", content=UPLOAD_TEXT))
    found = [x for x in submessages_of(r.body) if str(x.get("format", "")).lower() == "structured" and str(x.get("subformat", "")).lower() == "uri"] if isinstance(r.body, dict) else []
    if not found:
        raise Fail("there is no upload URI to check (see C38)")
    u = urlparse(str(found[0]["content"]))
    ctx.expect(u.scheme in ("http", "https") and u.hostname, f"not a URL: {found[0]['content']!r}")
    ctx.expect(u.port is not None and u.port != s.procs["ack"].port, f"upload port {u.port} equals the NLIP port {s.procs['ack'].port}")


# =============================================================== G9 transport and HTTP binding
@check("C40", "E431-6-post", "G9", "POST /nlip with an NLIP message returns 2xx and a JSON body", also=("E431-6-tcp-port", "E430-7.3-endpoint"))
def c40(ctx: Ctx):
    r = ctx.server().post("ack", BASE)
    ctx.expect(200 <= r.status <= 299, f"HTTP {r.status}")
    ctx.expect(isinstance(r.body, dict), "the body is not a JSON object")


@check("C41", "E431-6-url-path", "G9", "The end-point is /nlip: POST to '/nlip' (no trailing slash) is answered directly, without a redirect")
def c41(ctx: Ctx):
    r = ctx.server().post("ack", BASE, path="/nlip", follow=False)
    ctx.expect(not (300 <= r.status <= 399), f"HTTP {r.status}: redirect to {r.location}")
    ctx.expect(200 <= r.status <= 299, f"HTTP {r.status}")


@check("C42", "E431-6-post", "G9", "An invalid NLIP message is answered with an HTTP 4xx status and is not processed",
       note="The binding defines no status codes; any 4xx is accepted.")
def c42(ctx: Ctx):
    r = ctx.server().post("ack", {"format": "text"})
    ctx.expect(400 <= r.status <= 499, f"HTTP {r.status}: {r.text[:100]}")


@check("C43", "E431-6-post", "G9", "The client posts JSON with Content-Type application/json to the NLIP end-point",
       note="The binding does not define the content type; application/json is what the Python server and the clients use.")
def c43(ctx: Ctx):
    b = ctx.builder().build("text")
    ctx.expect(str(b.get("method", "")).upper() == "POST", f"method {b.get('method')!r}")
    ctx.expect(str(b.get("url", "")).rstrip("/").endswith("/nlip"), f"url {b.get('url')!r}")
    ct = {k.lower(): v for k, v in (b.get("headers") or {}).items()}.get("content-type", "")
    ctx.expect("application/json" in ct, f"content-type {ct!r}")


@check("C44", "E431-6-http-version", "G9", "The end-point works over HTTP/1.1 or HTTP/2")
def c44(ctx: Ctx):
    r = ctx.server().post("ack", BASE)
    ctx.expect(r.http_version in ("HTTP/1.1", "HTTP/2"), f"protocol {r.http_version!r}")


@check("C45", "E430-7.1-encrypted", "G9", "The same application serves NLIP over TLS (https)",
       note="TLS is a property of the base transfer protocol; the application is run behind uvicorn with a self-signed certificate.")
def c45(ctx: Ctx):
    r = ctx.server().post("tls", BASE)
    ctx.expect(200 <= r.status <= 299 and isinstance(r.body, dict), f"HTTP {r.status}")
