import threading
import time

import pytest
import uvicorn

from nlipeval.nlip.message import Message, NLIPError, Submessage, reserved_prefix
from nlipeval.nlip.transport import NLIPClient, create_app, echo_handler
from nlipeval.nlip.validate import validate


# ------------------------------------------------------------------ message
def test_lowercase_output_and_any_case_input():
    m = Message.from_dict({"Format": "Text", "SubFormat": "English", "CONTENT": "Hi", "MessageType": "Control"})
    d = m.to_dict()
    assert set(d) == {"messagetype", "format", "subformat", "content"}
    assert d["format"] == "Text" and d["messagetype"] == "Control"  # values are never rewritten
    assert m.is_control and m.control_by_type


def test_roundtrip_keeps_everything():
    src = {
        "messagetype": "ping",
        "format": "text",
        "subformat": "english",
        "content": "x",
        "control": True,
        "submessages": [
            {"label": "a", "format": "token", "subformat": "conversation_1", "content": "c1"},
            {"format": "structured", "subformat": "json", "content": {"k": [1, None, True]}},
            {"format": "binary", "subformat": "image/.png", "content": "AAEC"},
        ],
    }
    out = Message.from_json(Message.from_dict(src).to_json()).to_dict()
    assert out["submessages"] == src["submessages"] and out["control"] is True
    assert [s["subformat"] for s in out["submessages"]] == ["conversation_1", "json", "image/.png"]


def test_reject_invalid():
    with pytest.raises(NLIPError) as e:
        Message.from_dict({"format": "text", "content": "x"})
    assert e.value.violations[0].requirement_id == "E430-5.1.3-subformat-required"
    with pytest.raises(NLIPError):
        Message.from_json("not json")


def test_reserved_prefix():
    assert reserved_prefix("Authentication_x") == "authentication"
    assert reserved_prefix("conversation") == "conversation"
    assert reserved_prefix("authorization") is None and reserved_prefix(3) is None


# ------------------------------------------------------------------ validator
@pytest.mark.parametrize(
    "obj,rid",
    [
        ({"subformat": "english", "content": "x"}, "E430-5.1.2-format-required"),
        ({"format": "text", "content": "x"}, "E430-5.1.3-subformat-required"),
        ({"format": "text", "subformat": "english"}, "E430-5.1.4-content-required"),
        ({"format": "error", "subformat": "text", "content": "x"}, "E430-5.3-format-values"),
        ({"format": 3, "subformat": "e", "content": "x"}, "E430-5.1.2-format-required"),
        ({"format": "text", "subformat": "e", "content": "x", "messagetype": 1}, "E430-5.1.1-messagetype-string"),
        ({"format": "text", "subformat": "e", "content": "x", "submessages": {}}, "E430-5.1.5-submessages-array"),
        ({"format": "text", "subformat": "e", "content": "x", "submessages": [{"format": "text", "subformat": "e"}]}, "E430-5.2.4-content-required"),
        ({"format": "text", "subformat": "e", "content": "x", "submessages": [{"label": 1, "format": "text", "subformat": "e", "content": "y"}]}, "E430-5.2.1-label-string"),
        ({"format": "binary", "subformat": "video/mp3", "content": "x"}, "E430-5.3-binary-content"),
        ({"format": "text", "Format": "text", "subformat": "e", "content": "x"}, "E430-5-case-insensitive"),
    ],
)
def test_validator_reports_requirement(obj, rid):
    ok, v = validate(obj)
    assert not ok and rid in {x.requirement_id for x in v}


@pytest.mark.parametrize(
    "obj",
    [
        {"Format": "TEXT", "Subformat": "English", "Content": "x"},
        {"format": "token", "subformat": "conversation_9.2.3.5", "content": "t"},
        {"format": "structured", "subformat": "python", "content": "print(1)"},
        {"format": "binary", "subformat": "audio/.bmp", "content": "x"},
        {"format": "location", "subformat": "GPS", "content": "1,2"},
        {"format": "generic", "subformat": "acme", "content": {"a": 1}},
        {"format": "text", "subformat": "en", "content": None, "submessages": []},
    ],
)
def test_validator_accepts(obj):
    assert validate(obj) == (True, [])


# ------------------------------------------------------------------ transport (real HTTP on a local port)
@pytest.fixture(scope="module")
def server():
    app = create_app(echo_handler, upload_url="http://127.0.0.1:9/upload")
    cfg = uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning")
    srv = uvicorn.Server(cfg)
    t = threading.Thread(target=srv.run, daemon=True)
    t.start()
    for _ in range(100):
        if srv.started:
            break
        time.sleep(0.05)
    port = srv.servers[0].sockets[0].getsockname()[1]
    yield f"http://127.0.0.1:{port}"
    srv.should_exit = True
    t.join(5)


def test_conversation_and_echo(server):
    c = NLIPClient(server)
    r1 = c.send(Message.text("hello"))
    conv = r1.find_token("conversation")
    assert conv is not None and r1.texts() == ["hello"]
    m = Message.text("again")
    m.add_token("authentication_k", "secret")
    r2 = c.send(m)
    assert r2.find_token("conversation").content == conv.content
    assert r2.find_token("authentication").content == "secret"
    assert all(w["ok"] for w in c.wire)


def test_control_and_upload(server):
    c = NLIPClient(server)
    r = c.send(Message.text("hi", messagetype="control"))
    assert r.control_by_type
    r = c.send(Message.text("request upload url", messagetype="control"))
    assert (r.format, r.subformat, r.messagetype) == ("structured", "uri", "control")
    m = Message.text("x", extra={"control": True})
    assert c.send(m).control_by_field


def test_invalid_and_unknown_language(server):
    c = NLIPClient(server)
    c.http.post(c.url, json={"format": "text"})
    assert c.http.post(c.url, json={"format": "text"}).status_code == 400
    r = c.send(Message("structured", "cobol", "DISPLAY 'X'."))
    assert r.format == "text" and "cobol" in r.content
    assert c.http.get(c.url).status_code == 405
