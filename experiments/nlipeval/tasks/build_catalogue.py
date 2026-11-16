"""Stage 02: build the field-level change catalogue (specs/changes/<api>.yaml).

The lineage of every field is authored below as *concepts* (a field followed through the versions) and *events*
(what changed between two consecutive versions). The generator then derives, for every client version against the
server version, one catalogue entry per concept, and VERIFIES the authoring:

* every path claimed to exist at a version resolves in that version's OpenAPI file (line number recorded);
* every path claimed absent does not resolve;
* every piece of evidence is found, either in the `oasdiff changelog` output of that step or in the spec text;
* a path that differs between client and server must be explained by an event.

Run from experiments/:  uv run python -m nlipeval.tasks.build_catalogue
"""
from __future__ import annotations

import functools
import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from yaml.nodes import MappingNode, ScalarNode, SequenceNode

from nlipeval.tasks.specs import SPECS, VERSIONS

KINDS = ["unchanged", "renamed", "restructured", "unit_format", "newly_required", "changed_meaning", "removed", "added_optional"]
REVIEWED_DATE = "2026-11-13"
CHANGED_MEANING = (
    "a field or value that still exists, under the same or a similar name, whose interpretation changed, "
    "so that a field-for-field mapping goes wrong without any error."
)
# primary kind of an entry = the most disruptive kind among those crossed
PRIORITY = ["removed", "changed_meaning", "restructured", "newly_required", "unit_format", "renamed", "added_optional", "unchanged"]

# --------------------------------------------------------------------------- operations per version
OPS: dict[str, dict[str, dict[str, tuple[str, str]]]] = {
    "L1": {
        "retrieveReachability": {
            "v0.5.1": ("post", "/connectivity"),
            "v0.6.0": ("post", "/retrieve"),
            "v1.0.0": ("post", "/retrieve"),
        }
    },
    "L2": {"verifyLocation": {v: ("post", "/verify") for v in ["v0.1.0", "v0.2.0", "v1.0.0", "v2.0.0", "v3.0.0"]}},
    "L3": {
        "createSession": {v: ("post", "/sessions") for v in ["v0.8.1", "v0.9.0", "v0.10.0", "v0.11.0", "v1.0.0", "v1.1.0"]},
        "getSession": {v: ("get", "/sessions/{sessionId}") for v in ["v0.8.1", "v0.9.0", "v0.10.0", "v0.11.0", "v1.0.0", "v1.1.0"]},
        "deleteSession": {v: ("delete", "/sessions/{sessionId}") for v in ["v0.8.1", "v0.9.0", "v0.10.0", "v0.11.0", "v1.0.0", "v1.1.0"]},
    },
}


# --------------------------------------------------------------------------- authoring vocabulary
def od(a: str, b: str, text: str) -> tuple:
    """Evidence: a substring of one `oasdiff changelog a b` line."""
    return ("od", a, b, text)


def gr(version: str, literal: str, after: str | None = None) -> tuple:
    """Evidence: a literal text in the spec of `version`, searched after the first line matching regex `after`."""
    return ("gr", version, literal, after)


@dataclass
class Event:
    step: tuple[str, str]
    kinds: list[str]
    note: str
    evidence: list[tuple]


def E(a: str, b: str, kinds: list[str], note: str, *evidence: tuple) -> Event:
    for k in kinds:
        assert k in KINDS and k != "unchanged", k
    assert evidence, f"event {a}->{b} has no evidence"
    return Event((a, b), kinds, note, list(evidence))


@dataclass
class Concept:
    cid: str
    direction: str  # request | response
    ops: list[str]
    paths: list[tuple[str, str | None]]  # (from_version, path); None = absent from that version on
    events: list[Event] = field(default_factory=list)
    echo: bool = False  # the same field is echoed in the response of the operations in `echo_ops`
    echo_ops: list[str] = field(default_factory=list)
    element: str = "field"  # field | operation | path_parameter
    unchanged_note: str = ""

    def path_at(self, versions: list[str], v: str) -> str | None:
        cur = None
        for fv, p in self.paths:
            if fv is None or versions.index(fv) <= versions.index(v):
                cur = p
        return cur


def C(cid, direction, ops, paths, events=(), **kw) -> Concept:
    if isinstance(paths, str):
        paths = [(None, paths)]
    return Concept(cid, direction, list(ops), list(paths), list(events), **kw)


# --------------------------------------------------------------------------- spec navigation (YAML node tree, with lines)
class SpecDoc:
    def __init__(self, api: str, version: str):
        self.file = SPECS / api / f"{version}.yaml"
        self.rel = f"specs/{api}/{version}.yaml"
        self.text = self.file.read_text()
        self.lines = self.text.splitlines()
        self.root = yaml.compose(self.text)

    @staticmethod
    def mget(node, key):
        if not isinstance(node, MappingNode):
            return None
        for k, v in node.value:
            if isinstance(k, ScalarNode) and k.value == key:
                return v
        return None

    def deref(self, node):
        for _ in range(20):
            ref = self.mget(node, "$ref")
            if ref is None or not ref.value.startswith("#/"):
                return node
            cur = self.root
            for part in ref.value[2:].split("/"):
                cur = self.mget(cur, part.replace("~1", "/").replace("~0", "~"))
            node = cur
        raise RuntimeError("ref loop")

    def op_schema(self, method: str, path: str, direction: str):
        item = self.mget(self.mget(self.root, "paths"), path)
        op = self.mget(item, method) if item is not None else None
        if op is None:
            return None
        if direction == "request":
            holder = self.mget(op, "requestBody")
        else:
            holder = None
            resp = self.mget(op, "responses")
            for k, v in (resp.value if resp is not None else []):
                if str(k.value).startswith("2"):
                    holder = v
                    break
        holder = self.deref(holder) if holder is not None else None
        content = self.mget(holder, "content") if holder is not None else None
        js = self.mget(content, "application/json") if content is not None else None
        sch = self.mget(js, "schema") if js is not None else None
        return sch

    def find_prop(self, schema, name, seen):
        schema = self.deref(schema)
        if schema is None or id(schema) in seen:
            return None
        seen.add(id(schema))
        props = self.mget(schema, "properties")
        if props is not None:
            for k, v in props.value:
                if k.value == name:
                    return k, v
        for kw in ("allOf", "oneOf", "anyOf"):
            seq = self.mget(schema, kw)
            if isinstance(seq, SequenceNode):
                for item in seq.value:
                    r = self.find_prop(item, name, seen)
                    if r:
                        return r
        disc = self.mget(schema, "discriminator")
        mapping = self.mget(disc, "mapping") if disc is not None else None
        if mapping is not None:
            for _, target in mapping.value:
                if target.value.startswith("#/"):
                    r = self.find_prop(MappingNode("tag:yaml.org,2002:map", [(ScalarNode("tag:yaml.org,2002:str", "$ref"), target)]), name, seen)
                    if r:
                        return r
        return None

    def locate(self, schema, path: str):
        """Resolve 'a.b[].c' below `schema`. Returns the 1-based line of the final property key, or None."""
        node, line = schema, None
        for tok in path.split("."):
            is_arr = tok.endswith("[]")
            name = tok[:-2] if is_arr else tok
            r = self.find_prop(node, name, set())
            if r is None:
                return None
            k, node = r
            line = k.start_mark.line + 1
            if is_arr:
                node = self.mget(self.deref(node), "items")
                if node is None:
                    return None
        return line

    def grep(self, literal: str, after: str | None):
        start = 0
        if after:
            for i, ln in enumerate(self.lines):
                if re.search(after, ln):
                    start = i
                    break
            else:
                return None
        for i in range(start, len(self.lines)):
            if literal in self.lines[i]:
                return i + 1, self.lines[i].strip()
        return None

    def has_path(self, method: str, path: str) -> int | None:
        paths = self.mget(self.root, "paths")
        for k, v in paths.value:
            if k.value == path and self.mget(v, method) is not None:
                return k.start_mark.line + 1
        return None


@functools.cache
def spec(api: str, version: str) -> SpecDoc:
    return SpecDoc(api, version)


@functools.cache
def changelog(api: str, a: str, b: str) -> str:
    r = subprocess.run(
        ["oasdiff", "changelog", str(SPECS / api / f"{a}.yaml"), str(SPECS / api / f"{b}.yaml"), "--format", "json"],
        capture_output=True,
        text=True,
        check=True,
    )
    return "\n".join(x["text"] for x in json.loads(r.stdout or "[]"))


def check_evidence(api: str, ev: tuple) -> str:
    if ev[0] == "od":
        _, a, b, text = ev
        if text not in changelog(api, a, b):
            raise AssertionError(f"{api}: oasdiff {a}->{b} has no line containing {text!r}")
        return f"oasdiff changelog {a} -> {b}: {text}"
    _, v, literal, after = ev
    hit = spec(api, v).grep(literal, after)
    if hit is None:
        raise AssertionError(f"{api}: {v} has no line containing {literal!r} (after {after!r})")
    return f"{spec(api, v).rel}:{hit[0]}: {hit[1][:110]}"


# --------------------------------------------------------------------------- the lineage, per API
def l1() -> list[Concept]:
    V1, V2, V3 = "v0.5.1", "v0.6.0", "v1.0.0"
    op = ["retrieveReachability"]
    PH = [
        E(V1, V2, ["unit_format"], "Phone number pattern tightened: '+' now mandatory and no leading 0 (^\\+?[0-9]{5,15}$ -> ^\\+[1-9][0-9]{4,14}$).",
          gr(V1, "pattern: '^\\+?[0-9]{5,15}$'"), gr(V2, "pattern: '^\\+[1-9][0-9]{4,14}$'")),
    ]
    return [
        C("operation", "request", op, [(V1, "POST /connectivity"), (V2, "POST /retrieve")],
          [E(V1, V2, ["renamed"], "Path changed from POST /connectivity (operationId getConnectivityStatus) to POST /retrieve (getReachabilityStatus); the combined device-status API was split.",
             od(V1, V2, "api path removed without deprecation"), gr(V2, "/retrieve:"))],
          element="operation"),
        C("device", "request", op, "device", [E(V1, V2, [], "device was required in v0.5.1 and is optional from v0.6.0 (relaxation, no client change needed).", gr(V1, "- device"))]),
        C("device.phoneNumber", "request", op, "device.phoneNumber", PH),
        C("device.networkAccessIdentifier", "request", op, "device.networkAccessIdentifier"),
        C("device.ipv4Address.publicAddress", "request", op, "device.ipv4Address.publicAddress"),
        C("device.ipv4Address.privateAddress", "request", op, "device.ipv4Address.privateAddress"),
        C("device.ipv4Address.publicPort", "request", op, "device.ipv4Address.publicPort"),
        C("device.ipv6Address", "request", op, "device.ipv6Address"),
        C("status.value", "response", op,
          [(V1, "connectivityStatus"), (V2, "reachabilityStatus"), (V3, "reachable")],
          [E(V1, V2, ["renamed"], "connectivityStatus renamed to reachabilityStatus (same three values CONNECTED_DATA / CONNECTED_SMS / NOT_CONNECTED).",
             gr(V1, "connectivityStatus:", r"^\s+required:"), gr(V2, "reachabilityStatus:", r"^\s+required:")),
           E(V2, V3, ["restructured"],
             "The three-valued enum is replaced by a boolean `reachable` plus an optional `connectivity` list (DATA / SMS). "
             "Fixed rule for the old value (used by the stage 05 answer renderer): data present gives CONNECTED_DATA; "
             "SMS only gives CONNECTED_SMS; not reachable gives NOT_CONNECTED.",
             od(V2, V3, "removed the required property `reachabilityStatus` from the response"), od(V2, V3, "added the required property `reachable` to the response"))]),
        C("status.connectivity", "response", op,
          [(V1, "connectivityStatus"), (V2, "reachabilityStatus"), (V3, "connectivity[]")],
          [E(V1, V2, ["renamed"], "connectivityStatus renamed to reachabilityStatus.", gr(V2, "reachabilityStatus:", r"^\s+required:")),
           E(V2, V3, ["restructured"], "The channel information (data / SMS) moves into the optional `connectivity` array.",
             od(V2, V3, "added the optional property `connectivity` to the response"))]),
        C("lastStatusTime", "response", op, [(V1, None), (V2, "lastStatusTime")],
          [E(V1, V2, ["added_optional"], "lastStatusTime (date-time) appears in the response from v0.6.0; optional.", gr(V2, "lastStatusTime:", r"^\s+required:"))]),
    ]


def l2() -> list[Concept]:
    A, B, Cc, D, Ev = "v0.1.0", "v0.2.0", "v1.0.0", "v2.0.0", "v3.0.0"
    op = ["verifyLocation"]
    dev = E(A, B, ["renamed", "restructured"], "ueId is replaced by `device` (CAMARA common Device object).", od(A, B, "removed the request property `ueId`"), od(A, B, "added the new required request property `device`"))
    ph = E(B, Cc, ["unit_format"], "Phone number pattern tightened: '+' now mandatory and no leading 0.", od(B, Cc, "changed the pattern of the request property `device/phoneNumber`"))
    return [
        C("device", "request", op, [(A, "ueId"), (B, "device")], [dev,
          E(B, Cc, [], "device became optional in v1.0.0 (relaxation).", od(B, Cc, "the request property `device` became optional"))]),
        C("device.phoneNumber", "request", op, [(A, "ueId.msisdn"), (B, "device.phoneNumber")],
          [E(A, B, ["renamed"], "msisdn renamed to phoneNumber.", od(A, B, "removed the request property `ueId`")), ph]),
        C("device.networkAccessIdentifier", "request", op, [(A, "ueId.externalId"), (B, "device.networkAccessIdentifier")],
          [E(A, B, ["renamed"], "externalId renamed to networkAccessIdentifier.", od(A, B, "removed the request property `ueId`"))]),
        C("device.ipv4Address.publicAddress", "request", op, [(A, "ueId.ipv4Addr"), (B, "device.ipv4Address.publicAddress")],
          [E(A, B, ["restructured", "newly_required"],
             "ipv4Addr (a string) becomes an object; publicAddress is required and must be accompanied by privateAddress or publicPort.",
             od(A, B, "removed the request property `ueId`"), gr(B, "required: [publicAddress, privateAddress]"))]),
        C("device.ipv4Address.publicPort", "request", op, [(A, "uePort"), (B, "device.ipv4Address.publicPort")],
          [E(A, B, ["restructured"], "The separate uePort becomes device.ipv4Address.publicPort.", od(A, B, "removed the request property `uePort`"))]),
        C("device.ipv4Address.privateAddress", "request", op, [(A, None), (B, "device.ipv4Address.privateAddress")],
          [E(A, B, ["newly_required"], "Either privateAddress or publicPort must accompany publicAddress.", gr(B, "required: [publicAddress, privateAddress]"))]),
        C("device.ipv6Address", "request", op, [(A, "ueId.ipv6Addr"), (B, "device.ipv6Address")],
          [E(A, B, ["renamed"], "ipv6Addr renamed to ipv6Address.", od(A, B, "removed the request property `ueId`"))]),
        C("area.areaType", "request", op, [(A, None), (B, "area.areaType")],
          [E(A, B, ["newly_required"], "The area is a discriminated object; areaType is required and only CIRCLE exists.", od(A, B, "added the new required request property `area`"))]),
        C("area.center.latitude", "request", op, [(A, "latitude"), (B, "area.center.latitude")],
          [E(A, B, ["restructured"], "latitude moves into area.center.", od(A, B, "removed the request property `latitude`"), od(A, B, "added the new required request property `area`"))]),
        C("area.center.longitude", "request", op, [(A, "longitude"), (B, "area.center.longitude")],
          [E(A, B, ["restructured"], "longitude moves into area.center.", od(A, B, "removed the request property `longitude`"), od(A, B, "added the new required request property `area`"))]),
        C("area.radius", "request", op, [(A, "accuracy"), (B, "area.radius")],
          [E(A, B, ["restructured", "unit_format"],
             "accuracy (km, 2-200) becomes area.radius (metres): the verified region is now a circle around the centre, not a tolerance on a point. "
             "Both are numeric distances; the unit changes from km to m and the value moves into the area object.",
             od(A, B, "removed the request property `accuracy`"), gr(A, "Accuracy expected for location verification in km"), gr(B, "Expected accuracy for the verification in meters"))]),
        C("maxAge", "request", op, [(A, None), (B, "maxAge")],
          [E(A, B, ["added_optional"], "maxAge (seconds, minimum 60) appears in v0.2.0.", od(A, B, "added the new optional request property `maxAge`")),
           E(B, Cc, [], "The minimum of 60 is removed; maxAge=0 then means a fresh calculation and absence means any age.", od(B, Cc, "request property's min was unset"))]),
        C("verificationResult", "response", op, [(A, "verificationResult"), (B, "verificationResult")],
          [E(A, B, ["unit_format", "changed_meaning"],
             "boolean (true on match) becomes a string enum TRUE / FALSE / UNKNOWN / PARTIAL; PARTIAL has no boolean equivalent.",
             od(A, B, "response's property `type` changed from `boolean` to `string`"), od(A, B, "added the new `PARTIAL` enum value"))]),
        C("verificationResult=UNKNOWN", "response", op, [(A, None), (B, "verificationResult=UNKNOWN"), (Ev, None)],
          [E(A, B, [], "UNKNOWN (device cannot be located) is introduced as an enum value.", od(A, B, "added the new `UNKNOWN` enum value")),
           E(D, Ev, ["changed_meaning"], "The UNKNOWN value is removed at v3.0.0; the case becomes an HTTP 422 LOCATION_VERIFICATION.UNABLE_TO_LOCATE error. A client that waits for UNKNOWN never sees it.",
             od(D, Ev, "removed the `UNKNOWN` enum value from the `verificationResult`"), od(D, Ev, "added the new `LOCATION_VERIFICATION.UNABLE_TO_LOCATE` enum value"))],
          unchanged_note="UNKNOWN is a value of verificationResult, not a separate field."),
        C("lastLocationTime", "response", op, [(A, None), (B, "lastLocationTime")],
          [E(A, B, ["added_optional"], "lastLocationTime appears as optional in v0.2.0.", od(A, B, "added the optional property `lastLocationTime`")),
           E(D, Ev, ["newly_required"], "lastLocationTime becomes required at v3.0.0.", od(D, Ev, "the response property `lastLocationTime` became required"))]),
        C("matchRate", "response", op, [(A, None), (B, "matchRate")],
          [E(A, B, ["added_optional"], "matchRate (1-99) appears in v0.2.0; present only for PARTIAL.", od(A, B, "added the optional property `matchRate`"))]),
        C("device", "response", op, [(A, None), (D, None), (Ev, "device")],
          [E(D, Ev, ["added_optional"], "The response may echo the device that was used (v3.0.0).", od(D, Ev, "added the optional property `device` to the response"))]),
    ]


def l3() -> list[Concept]:
    V = ["v0.8.1", "v0.9.0", "v0.10.0", "v0.11.0", "v1.0.0", "v1.1.0"]
    a, b, c, d, e, f = V
    cs = ["createSession"]
    cg = ["createSession", "getSession"]
    BASE = "BaseSessionInfo"
    out: list[Concept] = []

    def add(*args, **kw):
        out.append(C(*args, **kw))

    # ---- duration
    add("duration", "request", cs, "duration",
        [E(c, d, ["newly_required"], "Optional with a default and maximum of 86400 s in v0.8.1-v0.10.0; required, with no maximum, from v0.11.0.",
           gr(c, "maximum: 86400"), gr(d, "- duration", r"^    CreateSession:"), od(c, d, "added the required property `allOf[subschema #2]/duration` to the response"))],
        echo=True, echo_ops=cg)
    # ---- device
    add("device", "request", cs, [(a, "ueId"), (b, "device")],
        [E(a, b, ["renamed", "restructured"], "ueId is replaced by `device` (CAMARA common Device object).", od(a, b, "removed the request property `ueId`"), od(a, b, "added the new required request property `device`")),
         E(c, d, [], "device became optional in the request from v0.11.0 (relaxation).", od(c, d, "removed the request property `device`"))],
        echo=True, echo_ops=cg)
    PHN = E(c, d, ["unit_format"], "Phone number pattern tightened: '+' now mandatory and no leading 0.",
            gr(c, "pattern: '^\\+?[0-9]{5,15}$'", r"^    PhoneNumber:"), gr(d, "pattern: '^\\+[1-9][0-9]{4,14}$'", r"^    PhoneNumber:"))
    add("device.phoneNumber", "request", cs, [(a, "ueId.msisdn"), (b, "device.phoneNumber")],
        [E(a, b, ["renamed"], "msisdn renamed to phoneNumber.", od(a, b, "removed the request property `ueId`")), PHN], echo=True, echo_ops=cg)
    add("device.networkAccessIdentifier", "request", cs, [(a, "ueId.externalId"), (b, "device.networkAccessIdentifier")],
        [E(a, b, ["renamed"], "externalId renamed to networkAccessIdentifier.", od(a, b, "removed the request property `ueId`"))], echo=True, echo_ops=cg)
    add("device.ipv4Address.publicAddress", "request", cs, [(a, "ueId.ipv4addr"), (b, "device.ipv4Address.publicAddress")],
        [E(a, b, ["restructured", "unit_format", "newly_required"],
           "ipv4addr (a string, address or address/mask) becomes an object; publicAddress is required, must be a plain address (no mask) and must be accompanied by privateAddress or publicPort.",
           od(a, b, "removed the request property `ueId`"), gr(b, "required: [publicAddress, privateAddress]", r"^    DeviceIpv4Addr:"), gr(a, "address/mask")),
         E(b, c, [], "Pattern replaced by format: ipv4 (same accepted strings).", od(b, c, "the `device/ipv4Address/publicAddress` request property `format` changed from `none` to `ipv4`"))],
        echo=True, echo_ops=cg)
    add("device.ipv4Address.privateAddress", "request", cs, [(a, None), (b, "device.ipv4Address.privateAddress")],
        [E(a, b, ["newly_required"], "publicAddress must be accompanied by privateAddress or publicPort (anyOf).", gr(b, "required: [publicAddress, privateAddress]", r"^    DeviceIpv4Addr:")),
         E(b, c, [], "Pattern replaced by format: ipv4 (same accepted strings).", od(b, c, "the `device/ipv4Address/privateAddress` request property `format` changed from `none` to `ipv4`"))])
    add("device.ipv4Address.publicPort", "request", cs, [(a, None), (b, "device.ipv4Address.publicPort")],
        [E(a, b, ["newly_required"], "publicAddress must be accompanied by privateAddress or publicPort (anyOf).", gr(b, "required: [publicAddress, publicPort]", r"^    DeviceIpv4Addr:"))])
    add("device.ipv6Address", "request", cs, [(a, "ueId.ipv6addr"), (b, "device.ipv6Address")],
        [E(a, b, ["renamed"], "ipv6addr renamed to ipv6Address.", od(a, b, "removed the request property `ueId`")),
         E(b, c, [], "format: ipv6 added (no change in practice).", od(b, c, "the `device/ipv6Address` request property `format` changed from `none` to `ipv6`"))],
        echo=True, echo_ops=cg)
    # ---- application server
    add("applicationServer", "request", cs, [(a, "asId"), (b, "applicationServer")],
        [E(a, b, ["renamed"], "asId renamed to applicationServer.", od(a, b, "removed the request property `asId`"), od(a, b, "added the new required request property `applicationServer`"))],
        echo=True, echo_ops=cg)
    add("applicationServer.ipv4Address", "request", cs, [(a, "asId.ipv4addr"), (b, "applicationServer.ipv4Address")],
        [E(a, b, ["renamed"], "ipv4addr renamed to ipv4Address.", od(a, b, "removed the request property `asId`"))], echo=True, echo_ops=cg)
    add("applicationServer.ipv6Address", "request", cs, [(a, "asId.ipv6addr"), (b, "applicationServer.ipv6Address")],
        [E(a, b, ["renamed"], "ipv6addr renamed to ipv6Address.", od(a, b, "removed the request property `asId`"))], echo=True, echo_ops=cg)
    # ---- ports
    for old, new, why in (("uePorts", "devicePorts", "uePorts"), ("asPorts", "applicationServerPorts", "asPorts")):
        for leaf in ("ranges[].from", "ranges[].to", "ports"):
            ev = [E(a, b, ["renamed"], f"{old} renamed to {new}.", od(a, b, f"removed the request property `{why}`"), od(a, b, f"added the new optional request property `{new}`"))]
            add(f"{new}.{leaf}", "request", cs, [(a, f"{old}.{leaf}"), (b, f"{new}.{leaf}")], ev, echo=True, echo_ops=cg)
    # ---- QoS profile
    add("qosProfile", "request", cs, [(a, "qos"), (b, "qosProfile")],
        [E(a, b, ["renamed", "unit_format"],
           "qos (enum QOS_E / QOS_S / QOS_M / QOS_L) becomes qosProfile (free string naming a provider profile; the QOS_x names are only one allowed option). The valid names are provider-defined and listed by the QoS Profiles API.",
           od(a, b, "removed the request property `qos`"), od(a, b, "added the new required request property `qosProfile`"), gr(b, "Support for predefined profiles QOS_S, QOS_M, QOS_L, and QOS_E"))],
        echo=True, echo_ops=cg)
    # ---- notifications
    add("sink", "request", cs, [(a, "notificationUrl"), (b, "webhook.notificationUrl"), (d, "sink")],
        [E(a, b, ["renamed", "restructured", "changed_meaning"],
           "notificationUrl moves into a `webhook` object. Meaning changes: in v0.8.1 the provider calls <notificationUrl>/notifications (the value is a base URL); from v0.9.0 it calls the URL exactly as given.",
           gr(a, '"{$request.body#/notificationUrl}/notifications"'), gr(b, '"{$request.body#/webhook/notificationUrl}"'), od(a, b, "removed the request property `notificationUrl`")),
         E(c, d, ["renamed", "restructured"], "webhook.notificationUrl becomes the top-level `sink`.", gr(d, '"{$request.body#/sink}"')),
         E(e, f, ["unit_format"], "sink must now match ^https://.+$ (HTTPS only).", od(e, f, "added the pattern `^https:\\/\\/.+$` to the request property"))],
        echo=True, echo_ops=cg)
    add("sinkCredential.accessToken", "request", cs, [(a, "notificationAuthToken"), (b, "webhook.notificationAuthToken"), (d, "sinkCredential.accessToken")],
        [E(a, b, ["restructured"], "notificationAuthToken moves into the `webhook` object.", od(a, b, "removed the request property `notificationAuthToken`"), gr(b, "notificationAuthToken:", r"^        webhook:")),
         E(c, d, ["renamed", "restructured"], "webhook.notificationAuthToken becomes sinkCredential.accessToken (credentialType ACCESSTOKEN).", gr(d, "AccessTokenCredential:", r"^    SinkCredential:"))])
    add("sinkCredential.credentialType", "request", cs, [(a, None), (d, "sinkCredential.credentialType")],
        [E(c, d, ["newly_required"], "If a credential is supplied, credentialType is required and must be ACCESSTOKEN.", gr(d, "- credentialType", r"^    SinkCredential:"))])
    add("sinkCredential.accessTokenExpiresUtc", "request", cs, [(a, None), (d, "sinkCredential.accessTokenExpiresUtc")],
        [E(c, d, ["newly_required"], "If a credential is supplied, accessTokenExpiresUtc (RFC 3339 date-time) is required; no such field existed.", gr(d, "- accessTokenExpiresUtc", r"^    AccessTokenCredential:"))])
    add("sinkCredential.accessTokenType", "request", cs, [(a, None), (d, "sinkCredential.accessTokenType")],
        [E(c, d, ["newly_required"], "If a credential is supplied, accessTokenType (bearer) is required; no such field existed.", gr(d, "- accessTokenType", r"^    AccessTokenCredential:"))])
    # ---- response-only fields
    add("sessionId", "response", cg, [(a, "id"), (b, "sessionId")],
        [E(a, b, ["renamed"], "id renamed to sessionId.", od(a, b, "removed the required property `allOf[subschema #2]/id`"), od(a, b, "added the required property `allOf[subschema #2]/sessionId`"))])
    for fld in ("startedAt", "expiresAt"):
        add(fld, "response", cg, fld,
            [E(c, d, ["unit_format"], f"{fld} changes from Unix seconds (integer int64) to an RFC 3339 date-time string.",
               od(c, d, f"the `allOf[subschema #2]/{fld}` response's property `type/format` changed from `integer/int64` to `string/date-time`")),
             E(c, d, [], f"Response-side relaxation: from v0.11.0 {fld} is optional, so the server's response may omit it (the renderer and the scorer must accept its absence).",
               od(c, d, f"response property `allOf[subschema #2]/{fld}` became optional"))])
    add("qosStatus", "response", cg, [(a, None), (b, "qosStatus")],
        [E(a, b, ["newly_required"], "qosStatus (REQUESTED / AVAILABLE / UNAVAILABLE) is returned from v0.9.0; absent before.", od(a, b, "added the required property `allOf[subschema #2]/qosStatus`"))])
    add("statusInfo", "response", cg, [(a, None), (d, "statusInfo")],
        [E(c, d, ["added_optional"], "statusInfo (reason for UNAVAILABLE) appears in v0.11.0.", od(c, d, "added the optional property `allOf[subschema #2]/statusInfo`"))])
    add("messages", "response", cg, [(a, "messages"), (d, None)],
        [E(c, d, ["removed"], "messages (severity / description) is removed in v0.11.0; qosStatus and statusInfo carry the information.", od(c, d, "removed the optional property `allOf[subschema #2]/messages`"))])
    add("sessionId", "request", ["getSession", "deleteSession"], "sessionId", [], element="path_parameter")
    # response echoes are generated from `echo` concepts
    return out


BUILDERS = {"L1": l1, "L2": l2, "L3": l3}
RESP_ROOT_NOTE = "Response entry derived from the request field of the same name (the response echoes it)."


def expand_echoes(concepts: list[Concept]) -> list[Concept]:
    res = []
    for k in concepts:
        res.append(k)
        if k.echo:
            res.append(Concept(k.cid, "response", k.echo_ops, k.paths, k.events, element=k.element, unchanged_note=k.unchanged_note))
    return res


# --------------------------------------------------------------------------- generation
def build(api: str) -> dict:
    versions = [v for v, _, _ in VERSIONS[api]["versions"]]
    server = VERSIONS[api]["server"]
    si = versions.index(server)
    concepts = expand_echoes(BUILDERS[api]())
    echo_pairs = {(k.cid, tuple(k.ops)) for k in concepts if k.direction == "response"}
    result = {}
    for ci, cv in enumerate(versions):
        entries = []
        for k in concepts:
            cpath, spath = k.path_at(versions, cv), k.path_at(versions, server)
            crossed = [ev for ev in k.events if ci <= versions.index(ev.step[0]) and versions.index(ev.step[1]) <= si]
            kinds = sorted({x for ev in crossed for x in ev.kinds}, key=PRIORITY.index)
            if cpath != spath and cv != server:
                # a differing path must be explained by an event that names a path-level kind
                if not (set(kinds) & {"renamed", "restructured", "removed", "added_optional", "newly_required", "changed_meaning"}):
                    raise AssertionError(f"{api} {k.cid}/{k.direction}: path {cpath!r} -> {spath!r} at {cv} not explained by events {kinds}")
            if cpath is None and spath is None:
                continue  # field exists in neither version
            value_level = "=" in k.cid  # a value of a field (e.g. verificationResult=UNKNOWN), not a field
            if cpath is not None and spath is None and "removed" not in kinds and not (value_level and "changed_meaning" in kinds):
                raise AssertionError(f"{api} {k.cid}: removed at server but no 'removed' event ({cv})")
            if cpath is None and spath is not None and not (set(kinds) & {"newly_required", "added_optional"}):
                raise AssertionError(f"{api} {k.cid}: absent at {cv} but no newly_required/added_optional event")
            # ---- verify path existence at client and server versions
            evidence = [check_evidence(api, ev) for e in crossed for ev in e.evidence]
            for ver, p, label in ((cv, cpath, "client"), (server, spath, "server")):
                if p is None or k.element != "field":
                    continue
                base = p.split("=")[0]
                lines = []
                for opid in k.ops:
                    m, path = OPS[api][opid][ver]
                    sch = spec(api, ver).op_schema(m, path, k.direction)
                    ln = spec(api, ver).locate(sch, base) if sch is not None else None
                    if ln is None:
                        raise AssertionError(f"{api} {ver} {opid} {k.direction}: path {p!r} not found in the spec")
                    lines.append(ln)
                evidence.append(f"{spec(api, ver).rel}:{lines[0]}: {label} `{p}`")
            for ver, p in ((cv, cpath), (server, spath)):  # absence checks
                pass
            if k.element == "operation":
                for ver, p in ((cv, cpath), (server, spath)):
                    m, pth = p.split(" ", 1)
                    ln = spec(api, ver).has_path(m.lower(), pth)
                    if ln is None:
                        raise AssertionError(f"{api} {ver}: operation {p} not found")
                    evidence.append(f"{spec(api, ver).rel}:{ln}: operation `{p}`")
            if k.element == "path_parameter":
                for ver in (cv, server):
                    hit = spec(api, ver).grep("name: sessionId", None)
                    evidence.append(f"{spec(api, ver).rel}:{hit[0]}: path parameter sessionId")
            if cpath is None:  # absent in the client: verify the absence
                for opid in k.ops:
                    m, path = OPS[api][opid][cv]
                    sch = spec(api, cv).op_schema(m, path, k.direction)
                    if sch is not None and spec(api, cv).locate(sch, spath.split("=")[0]) is not None:
                        raise AssertionError(f"{api} {cv}: {spath!r} unexpectedly present in the client spec")
            kind = kinds[0] if kinds else "unchanged"
            notes = [ev.note for ev in crossed if ev.note]
            if not notes and k.unchanged_note:
                notes = [k.unchanged_note]
            if k.direction == "response" and any(c.cid == k.cid and c.direction == "request" and c.echo for c in concepts):
                notes.append(RESP_ROOT_NOTE)
            entries.append(
                {
                    "operations": k.ops,
                    "direction": k.direction,
                    "element": k.element,
                    "client_path": cpath,
                    "server_path": spath,
                    "kind": kind,
                    "kinds": kinds or ["unchanged"],
                    "note": " ".join(notes) if notes else "No change between the client and the server version.",
                    "evidence": list(dict.fromkeys(evidence)),
                }
            )
        result[cv] = {"versions_behind": si - ci, "entries": entries}
    return {
        "status": "reviewed",
        "reviewed": REVIEWED_DATE,
        "note": "Generated by nlipeval/tasks/build_catalogue.py; evidence is machine-verified against the pinned specs. Reviewed in stage 03b (decisions D6-D8).",
        "kind_definitions": {"changed_meaning": CHANGED_MEANING},
        "api": api,
        "server_version": server,
        "client_versions": result,
    }


def main() -> None:
    out = SPECS / "changes"
    out.mkdir(exist_ok=True)
    for api in BUILDERS:
        doc = build(api)
        header = f"# `changed_meaning`: {CHANGED_MEANING}\n"
        (out / f"{api}.yaml").write_text(header + yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=140))
        n = {v: len(x["entries"]) for v, x in doc["client_versions"].items()}
        print(api, n)


if __name__ == "__main__":
    main()
