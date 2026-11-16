"""Driver for nlip_sdk (run with stage1/venvs/sdk/bin/python). One JSON request per line on stdin, one reply per line.

ops: parse {obj} | build {kind} | recognise {subformat} | info
"""
import json
import sys

from nlip_sdk.nlip import AllowedFormats, NLIP_Factory, NLIP_Message, NLIP_SubMessage, ReservedTokens


def build(kind):
    if kind == "text":
        return NLIP_Factory.create_text("hello")
    if kind == "control_upload":  # the SDK's own helper for control messages
        return NLIP_Factory.create_control("request upload url")
    if kind == "image":
        return NLIP_Factory.create_image("AAEC", "png")
    if kind in ("auth_token", "conv_token"):
        m = NLIP_Factory.create_text("hello")
        (m.add_authentication_token if kind == "auth_token" else m.add_conversation_token)("tok123")
        return m
    if kind == "error":
        return NLIP_Factory.create_error_code("something failed")
    raise NotImplementedError(kind)


CONV_ID = "conv-42"
UPLOAD_TEXT = "Please send me an end-point for large uploads."


def interop(mid):
    """The interoperability messages as nlip_sdk builds them (public API only). None = cannot be built."""
    if mid == "M01":
        return NLIP_Factory.create_text("Hello, world")
    if mid == "M02":
        return NLIP_Factory.create_text("Grüße, 世界 — ✓")
    if mid == "M03":
        return NLIP_Factory.create_text("Bonjour le monde", language="French")
    if mid == "M04":
        return NLIP_Factory.create_json({"order": {"id": 17, "items": [{"sku": "a", "qty": 2}, {"sku": "b", "qty": None}], "paid": True}})
    if mid == "M05":
        m = NLIP_Factory.create_text("what is this")
        m.add_image("AAEC", "png")
        return m
    if mid == "M06":
        m = NLIP_Factory.create_text("Guten Tag", language="German")
        m.add_json({"k": [1, 2]}, label="two")
        m.add_location_gps("51.0,-1.4", label="three")
        return m
    if mid == "M07":
        m = NLIP_Factory.create_text("hi")
        m.add_conversation_token(CONV_ID)
        return m
    if mid == "M08":
        m = NLIP_Factory.create_text("hi")
        m.add_authentication_token("secret-1")
        return m
    if mid == "M09":
        m = NLIP_Factory.create_text("hi")
        m.add_conversation_token(CONV_ID)
        m.add_authentication_token("secret-1")
        return m
    if mid == "M10":
        m = NLIP_Factory.create_text("hi")
        m.add_submessage(NLIP_SubMessage(format=AllowedFormats.token, subformat="group_7", content="g-9"))
        return m
    if mid in ("M11", "M12", "M13"):
        m = NLIP_Factory.create_text(f"turn {int(mid[1:]) - 10}")
        m.add_conversation_token(CONV_ID)
        return m
    if mid == "M14":
        return NLIP_Factory.create_control("query policies")
    if mid == "M15":
        return NLIP_Factory.create_control(UPLOAD_TEXT)
    if mid == "M18":
        return NLIP_Factory.create_structured("DISPLAY 'HELLO'.", "cobol")
    if mid == "M19":
        return NLIP_Factory.create_location_gps("51.0,-1.4")
    if mid == "M20":
        return NLIP_Factory.create_text("x" * 100000)
    return None  # M16 (a control field), M17 (an invalid message): the SDK has no way to build them


def handle(req):
    op = req["op"]
    if op == "parse":
        try:
            m = NLIP_Message.model_validate(req["obj"])
            return {"accepted": True, "out": m.to_dict()}
        except Exception as e:  # pydantic.ValidationError
            return {"accepted": False, "error": str(e).splitlines()[0] + " | " + " ".join(str(e).splitlines()[1:3])}
    if op == "parse_json":
        try:
            m = NLIP_Message.model_validate_json(req["text"])
            return {"accepted": True, "out": m.to_dict()}
        except Exception as e:
            return {"accepted": False, "error": str(e).splitlines()[0]}
    if op == "extract":
        m = NLIP_Message.model_validate(req["obj"])
        return {"conv": m.extract_conversation_token(), "auth": m.extract_authentication_token()}
    if op == "interop_build":
        m = interop(req["mid"])
        return {"out": None if m is None else m.to_dict()}
    if op == "interop_read":
        try:
            return {"accepted": True, "out": NLIP_Message.model_validate(req["obj"]).to_dict()}
        except Exception as e:
            return {"accepted": False, "error": str(e).splitlines()[0]}
    if op == "build":
        return {"out": build(req["kind"]).to_dict()}
    if op == "recognise":
        sub = req["subformat"]
        return {"auth": ReservedTokens.is_auth(sub), "conv": ReservedTokens.is_conv(sub)}
    if op == "info":
        return {"formats": [m.value for m in AllowedFormats], "reserved": {k.name: k.value for k in ReservedTokens}}
    raise ValueError(op)


for line in sys.stdin:
    try:
        out = handle(json.loads(line))
    except Exception as e:
        out = {"driver_error": f"{type(e).__name__}: {e}"}
    print(json.dumps(out), flush=True)
