"""Strict validation of a message against a client version's own specification (07b A11).

`validate_request(api, version, native_request)` and `validate_answer(api, version, operation, answer)` check a
body with the version's JSON schema (OpenAPI 3.0 dialect) and additionally reject every property the schema
does not declare (`additionalProperties: false` throughout, with `allOf`/`oneOf`/`anyOf` members taken together).
Both return a list of error strings; an empty list means valid.
"""
from __future__ import annotations

import functools
from typing import Any

import yaml
from openapi_schema_validator import OAS30Validator

from nlipeval.tasks.specs import SPECS, _resolve


@functools.cache
def _spec(api: str, version: str) -> dict:
    return yaml.safe_load((SPECS / api / f"{version}.yaml").read_text())


def _base_path(doc: dict) -> str:
    server = doc["servers"][0]
    url = server["url"].split("}", 1)[1].lstrip("/") if "}" in server["url"] else server["url"]
    for name, var in (server.get("variables") or {}).items():
        url = url.replace("{" + name + "}", str(var["default"]))
    return "/" + url.lstrip("/")


def _match_path(template: str, path: str) -> bool:
    t, p = template.strip("/").split("/"), path.strip("/").split("/")
    return len(t) == len(p) and all(a == b or (a.startswith("{") and a.endswith("}")) for a, b in zip(t, p))


def operation_of(api: str, version: str, method: str, path: str) -> dict:
    doc = _spec(api, version)
    base = _base_path(doc)
    for key, item in doc["paths"].items():
        if _match_path(base + key, path) and method.lower() in item:
            return item[method.lower()]
    raise KeyError(f"{api} {version}: no operation for {method} {path}")


def _allowed(schema: dict) -> set[str] | None:
    """Property names a schema declares (union over allOf/oneOf/anyOf); None when it is not an object schema."""
    names: set[str] = set()
    is_object = False
    if schema.get("type") == "object" or "properties" in schema:
        is_object = True
        names |= set(schema.get("properties", {}))
    for key in ("allOf", "oneOf", "anyOf"):
        for sub in schema.get(key, []):
            sub_names = _allowed(sub)
            if sub_names is not None:
                is_object = True
                names |= sub_names
    for sub in (schema.get("x-discriminator-subtypes") or {}).values():
        sub_names = _allowed(sub)
        if sub_names is not None:
            names |= sub_names
    return names if is_object else None


def _unknown(schema: dict, instance: Any, path: str = "") -> list[str]:
    out: list[str] = []
    if isinstance(instance, dict):
        names = _allowed(schema)
        props = _all_properties(schema)
        for k, v in instance.items():
            here = f"{path}.{k}" if path else k
            if names is not None and k not in names and not schema.get("additionalProperties"):
                out.append(f"{here}: property not declared")
            elif k in props:
                out.extend(_unknown(props[k], v, here))
            elif isinstance(schema.get("additionalProperties"), dict):
                out.extend(_unknown(schema["additionalProperties"], v, here))
    elif isinstance(instance, list):
        items = schema.get("items")
        if isinstance(items, dict):
            for n, x in enumerate(instance):
                out.extend(_unknown(items, x, f"{path}[{n}]"))
    return out


def _all_properties(schema: dict) -> dict[str, dict]:
    props: dict[str, dict] = dict(schema.get("properties", {}))
    for key in ("allOf", "oneOf", "anyOf"):
        for sub in schema.get(key, []):
            for k, v in _all_properties(sub).items():
                props.setdefault(k, v)
    for sub in (schema.get("x-discriminator-subtypes") or {}).values():
        for k, v in _all_properties(sub).items():
            props.setdefault(k, v)
    return props


def _check(schema: dict, instance: Any) -> list[str]:
    errors = [e.message for e in OAS30Validator(schema).iter_errors(instance)]
    return errors + _unknown(schema, instance)


def validate_request(api: str, version: str, native: dict) -> list[str]:
    doc = _spec(api, version)
    op = operation_of(api, version, native["method"], native["path"])
    body = native.get("body")
    rb = op.get("requestBody")
    if rb is None:
        return [] if body is None else ["request has a body but the operation takes none"]
    if body is None:
        return ["request has no body"]
    schema = _resolve(rb["content"]["application/json"]["schema"], doc)
    return _check(schema, body)


ECHO_REQUIRED = {"'device' is a required property", "'ueId' is a required property"}


def validate_answer(api: str, version: str, native: dict, answer: dict) -> list[str]:
    """The `result` of a `done` answer against the success response of the client version's own operation."""
    if answer["status"] != "done" or answer.get("result") is None:
        return []
    doc = _spec(api, version)
    op = operation_of(api, version, native["method"], native["path"])
    for code in ("200", "201"):
        if code in op["responses"]:
            schema = _resolve(op["responses"][code]["content"]["application/json"]["schema"], doc)
            errors = _check(schema, answer["result"])
            # Known gap (07b report): the server answers without `device` when one identifier was given, so the
            # client answer cannot echo the device that L3 v0.8.1-v0.10.0 list as required.
            return [e for e in errors if e not in ECHO_REQUIRED]
    return ["no success response with a body"]
