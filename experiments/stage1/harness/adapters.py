"""Implementations under test, and the roles each one has.

An `Impl` has any of:
  model    parse / parse_json / formats / recognise / extract    (a message model or validator)
  builder  build(kind) -> {"body", "url", ...}                    (client code that builds requests)
  reader   receive(kind, obj)                                     (client code that reads a response)
  server   an HTTP end-point started in a subprocess              (echo app, ack app, TLS variant)
A check that finds none of the roles it needs reports n/a.
"""
from __future__ import annotations

import json
import os
import socket
import ssl
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from nlipeval.nlip.message import FORMATS, Message, NLIPError, Submessage, reserved_prefix
from nlipeval.nlip.validate import validate

S1 = Path(__file__).resolve().parents[1]
ROOT = S1.parent
RESULTS = ROOT / "results" / "stage1"
VENVS = S1 / "venvs"
UPLOAD_TEXT = "Please send me an end-point for large uploads."


@dataclass
class Parse:
    accepted: bool
    out: dict | None = None
    detail: str = ""


@dataclass
class Reply:
    status: int
    body: Any
    text: str
    http_version: str = ""
    redirected: bool = False
    final_url: str = ""
    location: str = ""


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Impl:
    def __init__(self, key: str, label: str):
        self.key, self.label = key, label
        self.model = self.builder = self.reader = self.server = None
        self.trace: list[str] = []
        self.blocked: str | None = None

    def log(self, line: str) -> None:
        self.trace.append(line)

    def close(self) -> None:
        for r in (self.model, self.builder, self.reader, self.server):
            if r is not None and hasattr(r, "close"):
                r.close()


# ----------------------------------------------------------------------------- line-protocol drivers
class LineDriver:
    def __init__(self, cmd: list[str]):
        self.p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1)

    def call(self, **req) -> dict:
        self.p.stdin.write(json.dumps(req) + "\n")
        self.p.stdin.flush()
        while True:
            line = self.p.stdout.readline()
            if not line:
                raise RuntimeError("driver exited")
            if line.strip().startswith("{"):
                return json.loads(line)

    def close(self):
        try:
            self.p.stdin.close()
            self.p.wait(5)
        except Exception:
            self.p.kill()


class SdkModel:
    def __init__(self, impl: Impl):
        self.impl = impl
        self.d = LineDriver([str(VENVS / "sdk" / "bin" / "python"), str(S1 / "drivers" / "sdk_driver.py")])

    def _p(self, r) -> Parse:
        return Parse(r["accepted"], r.get("out"), r.get("error", ""))

    def parse(self, obj) -> Parse:
        r = self.d.call(op="parse", obj=obj)
        self.impl.log(f"nlip_sdk NLIP_Message.model_validate({json.dumps(obj)}) -> {json.dumps(r)}")
        return self._p(r)

    def parse_json(self, text: str) -> Parse:
        r = self.d.call(op="parse_json", text=text)
        self.impl.log(f"nlip_sdk NLIP_Message.model_validate_json({text!r}) -> {json.dumps(r)}")
        return self._p(r)

    def formats(self) -> list[str]:
        r = self.d.call(op="info")
        self.impl.log(f"nlip_sdk AllowedFormats -> {r['formats']}")
        return r["formats"]

    def recognise(self, subformat: str) -> dict:
        r = self.d.call(op="recognise", subformat=subformat)
        self.impl.log(f"nlip_sdk ReservedTokens.is_auth/is_conv({subformat!r}) -> {json.dumps(r)}")
        return r

    def extract(self, obj) -> dict:
        r = self.d.call(op="extract", obj=obj)
        self.impl.log(f"nlip_sdk extract_*_token({json.dumps(obj)}) -> {json.dumps(r)}")
        return r

    def build(self, kind: str) -> dict:
        r = self.d.call(op="build", kind=kind)
        self.impl.log(f"nlip_sdk build {kind} -> {json.dumps(r)}")
        return {"body": r["out"]}

    def interop_build(self, mid: str):
        return self.d.call(op="interop_build", mid=mid)["out"]

    def interop_read(self, obj) -> dict:
        return self.d.call(op="interop_read", obj=obj)

    def close(self):
        self.d.close()


class TsClient:
    def __init__(self, impl: Impl, node: str, src: Path):
        self.impl = impl
        self.d = LineDriver([node, str(S1 / "drivers" / "ts_driver.mjs"), str(src)])

    def build(self, kind: str) -> dict:
        r = self.d.call(op="build", kind=kind)
        self.impl.log(f"ts_client build {kind} -> {json.dumps(r)}")
        if r.get("out") is None:
            raise NotImplementedError(f"the TypeScript client has no code that builds a '{kind}' request")
        return {"body": r["out"], "url": r.get("url"), "method": r.get("method"), "headers": r.get("headers")}

    def receive(self, kind: str, obj) -> dict:
        r = self.d.call(op="receive", kind=kind, obj=obj)
        self.impl.log(f"ts_client reads {json.dumps(obj)} via {kind} -> {json.dumps(r)}")
        return r

    def send(self, kind: str, target: str, text: str | None = None) -> dict:
        r = self.d.call(op="send", kind=kind, target=target, text=text)
        self.impl.log(f"ts_client send {kind} to {target} -> {json.dumps(r)}")
        return r

    def close(self):
        self.d.close()


class OursModel:
    def __init__(self, impl: Impl):
        self.impl = impl

    def parse(self, obj) -> Parse:
        ok, v = validate(obj)
        out = Message.from_dict(obj, check=False).to_dict() if ok else None
        self.impl.log(f"ours validate({json.dumps(obj)}) -> ok={ok} {[str(x) for x in v]}")
        return Parse(ok, out, "; ".join(str(x) for x in v))

    def parse_json(self, text: str) -> Parse:
        try:
            m = Message.from_json(text)
            self.impl.log(f"ours Message.from_json({text!r}) -> accepted")
            return Parse(True, m.to_dict())
        except NLIPError as e:
            self.impl.log(f"ours Message.from_json({text!r}) -> {e}")
            return Parse(False, None, str(e))

    def formats(self) -> list[str]:
        return list(FORMATS)

    def recognise(self, subformat: str) -> dict:
        p = reserved_prefix(subformat)
        r = {"auth": p == "authentication", "conv": p == "conversation"}
        self.impl.log(f"ours reserved_prefix({subformat!r}) -> {r}")
        return r

    def extract(self, obj) -> dict:
        m = Message.from_dict(obj, check=False)
        a, c = m.find_token("authentication"), m.find_token("conversation")
        r = {"conv": c.content if c else None, "auth": a.content if a else None}
        self.impl.log(f"ours find_token({json.dumps(obj)}) -> {r}")
        return r

    def build(self, kind: str) -> dict:
        if kind == "text":
            m = Message.text("hello")
        elif kind == "control_upload":
            m = Message.text(UPLOAD_TEXT, messagetype="control")
        elif kind == "image":
            m = Message.text("what is this")
            m.submessages = [Submessage("binary", "image/png", "AAEC")]
        elif kind == "auth_token":
            m = Message.text("hello").with_authentication("tok123")
        elif kind == "conv_token":
            m = Message.text("hello").with_conversation("tok123")
        else:
            raise NotImplementedError(kind)
        from nlipeval.nlip.transport import NLIPClient

        c = NLIPClient("http://localhost")  # the request line our client uses: httpx post(json=...)
        self.impl.log(f"ours build {kind} -> POST {c.url} {m.to_json()}")
        return {"body": m.to_dict(), "url": c.url, "method": "POST", "headers": {"Content-Type": "application/json"}}

    def receive(self, kind: str, obj) -> dict:
        try:
            m = Message.from_dict(obj)
        except NLIPError as e:
            self.impl.log(f"ours reads {json.dumps(obj)} -> rejected {e}")
            return {"accepted": False, "error": str(e)}
        value = m.content
        self.impl.log(f"ours reads {json.dumps(obj)} -> {value!r}")
        return {"accepted": True, "value": value}


# ----------------------------------------------------------------------------- servers
class ServerProc:
    def __init__(self, name: str, cmd: list[str], port: int, env: dict | None = None, tls: bool = False):
        (RESULTS / "logs" / "servers").mkdir(parents=True, exist_ok=True)
        self.name, self.port, self.tls = name, port, tls
        self.log_path = RESULTS / "logs" / "servers" / f"{name}.log"
        self.log_file = open(self.log_path, "w")
        self.p = subprocess.Popen(cmd, stdout=self.log_file, stderr=subprocess.STDOUT, env={**os.environ, **(env or {})})
        for _ in range(300):
            if self.p.poll() is not None:
                raise RuntimeError(f"{name} exited, see {self.log_path}")
            try:
                socket.create_connection(("127.0.0.1", port), 0.2).close()
                return
            except OSError:
                time.sleep(0.1)
        raise RuntimeError(f"{name} did not start, see {self.log_path}")

    @property
    def url(self) -> str:
        return f"{'https' if self.tls else 'http'}://localhost:{self.port}"

    def stop(self):
        self.p.terminate()
        try:
            self.p.wait(5)
        except subprocess.TimeoutExpired:
            self.p.kill()
        self.log_file.close()


def _uvicorn(python: str, app: str, port: int, app_dir: Path | None, ssl: tuple[Path, Path] | None = None) -> list[str]:
    cmd = [python, "-m", "uvicorn", app, "--host", "127.0.0.1", "--port", str(port), "--log-level", "info"]
    if app_dir:
        cmd += ["--app-dir", str(app_dir)]
    if ssl:
        cmd += ["--ssl-keyfile", str(ssl[0]), "--ssl-certfile", str(ssl[1])]
    return cmd


def make_cert(directory: Path) -> tuple[Path, Path]:
    key, crt, cfg = directory / "key.pem", directory / "cert.pem", directory / "openssl.cnf"
    directory.mkdir(parents=True, exist_ok=True)
    cfg.write_text("[req]\ndistinguished_name=dn\nx509_extensions=ext\nprompt=no\n[dn]\nCN=localhost\n[ext]\nsubjectAltName=DNS:localhost,IP:127.0.0.1\nbasicConstraints=CA:TRUE\n")
    subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", str(key), "-out", str(crt), "-days", "30", "-config", str(cfg)], check=True, capture_output=True)
    return key, crt


class Server:
    """Three processes: the echo app, the ack app and the ack app over TLS. `app` is 'echo' or 'ack' (or 'tls')."""

    def __init__(self, impl: Impl, procs: dict[str, ServerProc], cert: Path, has_upload: bool):
        self.impl, self.procs, self.cert, self.has_upload = impl, procs, cert, has_upload

    def post(self, app: str, body: Any, path: str = "/nlip", follow: bool = True, raw: bool = False) -> Reply:
        proc = self.procs[app]
        url = proc.url + path
        kw = {"content": body, "headers": {"content-type": "application/json"}} if raw else {"json": body}
        client = httpx.Client(timeout=15, follow_redirects=follow, verify=ssl.create_default_context(cafile=str(self.cert)) if proc.tls else True)
        try:
            r = client.post(url, **kw)
        finally:
            client.close()
        try:
            data = r.json()
        except ValueError:
            data = None
        hist = f" (after redirect from {r.history[0].url}: HTTP {r.history[0].status_code})" if r.history else ""
        self.impl.log(f"[{app}] POST {url} {body if raw else json.dumps(body)} -> HTTP {r.status_code} {r.http_version}{hist}{' Location: ' + r.headers['location'] if 'location' in r.headers else ''} {r.text[:500]}")
        return Reply(r.status_code, data, r.text, r.http_version, bool(r.history) or r.is_redirect, str(r.url), r.headers.get("location", ""))

    def _as_parse(self, r: Reply) -> Parse:
        ok = 200 <= r.status <= 299 and isinstance(r.body, dict)
        return Parse(ok, r.body if ok else None, f"HTTP {r.status}: {r.text[:150]}")

    def parse(self, obj) -> Parse:
        return self._as_parse(self.post("echo", obj))

    def parse_text(self, text: str) -> Parse:
        return self._as_parse(self.post("echo", text, raw=True))

    def close(self):
        for p in self.procs.values():
            p.stop()


def build_impls(include: list[str] | None = None) -> list[Impl]:
    py = sys.executable
    include = include or ["nlip_sdk", "nlip_server", "nlip_server_echo", "ts_client", "ours"]
    impls: list[Impl] = []
    key, crt = make_cert(RESULTS / "tls")

    if "nlip_sdk" in include:
        i = Impl("nlip_sdk", "nlip_sdk")
        i.model = SdkModel(i)
        impls.append(i)

    if "nlip_server" in include:
        sp = str(VENVS / "server" / "bin" / "python")
        i = Impl("nlip_server", "nlip_server (minimal application)")
        procs = {}
        for name, app, ssl in (("echo", "nlip_server.echo:app", None), ("ack", "nlip_server_ack:app", None), ("tls", "nlip_server_ack:app", (key, crt))):
            port = free_port()
            procs[name] = ServerProc(f"nlip_server-{name}", _uvicorn(sp, app, port, S1 / "apps", ssl), port, tls=bool(ssl))
        i.server = Server(i, procs, crt, has_upload=False)
        impls.append(i)
        if "nlip_server_echo" in include:  # the library's own echo application, in every role
            i2 = Impl("nlip_server_echo", "nlip_server (its own echo application)")
            procs2 = {}
            for name, ssl in (("echo", None), ("ack", None), ("tls", (key, crt))):
                port = free_port()
                procs2[name] = ServerProc(f"nlip_server_echo-{name}", _uvicorn(sp, "nlip_server.echo:app", port, S1 / "apps", ssl), port, tls=bool(ssl))
            i2.server = Server(i2, procs2, crt, has_upload=False)
            impls.append(i2)

    if "ts_client" in include:
        i = Impl("ts_client", "TypeScript example client")
        node = subprocess.run(["which", "node"], capture_output=True, text=True).stdout.strip()
        src = S1 / "vendor" / "examples" / "nlip_client_pwa_ts" / "src" / "components" / "network.ts"
        if not node:
            i.blocked = "node is not installed"
        else:
            i.builder = i.reader = TsClient(i, node, src)
        impls.append(i)

    if "ours" in include:
        i = Impl("ours", "our implementation")
        up_port = free_port()
        upload = ServerProc("ours-upload", [py, "-m", "uvicorn", "stage1.apps.ours_upload:app", "--host", "127.0.0.1", "--port", str(up_port), "--log-level", "info"], up_port)
        env = {"NLIP_UPLOAD_URL": f"http://localhost:{up_port}/upload", "PYTHONPATH": str(ROOT)}
        procs = {"upload": upload}
        for name, app, ssl in (("echo", "stage1.apps.ours_echo:app", None), ("ack", "stage1.apps.ours_ack:app", None), ("tls", "stage1.apps.ours_ack:app", (key, crt))):
            port = free_port()
            procs[name] = ServerProc(f"ours-{name}", _uvicorn(py, app, port, None, ssl), port, env=env, tls=bool(ssl))
        i.model = i.builder = i.reader = OursModel(i)
        i.server = Server(i, {k: v for k, v in procs.items()}, crt, has_upload=True)
        impls.append(i)
    return impls
