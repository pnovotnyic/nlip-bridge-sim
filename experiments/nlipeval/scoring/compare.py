"""Comparison and normalisation rules for NLIP evaluation scoring (stage 07).

Rules matching bob_plan/07-scoring-and-analysis-code.md and data-contract.md §2.6:
  1. Normalise path parameters, JSON key order, absent vs null optional fields,
     phone numbers to E.164, IP addresses to canonical form, times within tolerance,
     and unordered lists (e.g. connectivity) as sets.
  2. Request correctness (score.py): exactly one call accepted by the backend that matches a gold
     alternative; rejected calls do not count. Refusal tasks are judged by the last call's status and code.
  3. Harmful call: accepted call matching no gold alternative on material_fields, or
     executed call on a declined task.
  The device is never compared in the body: the backend's `resolved_device` and `identifiers_consistent`
  judge executed calls, and `resolve_device_offline` resolves planned calls that were not executed (07b C4).
  4. Response understanding: client_final matches gold_client_answer (status, and field by field for done).
"""

from __future__ import annotations

import datetime
import ipaddress
import re
from typing import Any
from urllib.parse import unquote

DEFAULT_TIME_TOLERANCE_S = 5.0
DEFAULT_DURATION_TOLERANCE_S = 0.0


# --------------------------------------------------------------------------- normalisation helpers

def normalize_phone(val: Any) -> str:
    """Remove spaces, hyphens, dots and parentheses. A missing leading "+" is NOT added: a number without
    it is not E.164 and does not match one with it (07b C8)."""
    if not isinstance(val, str):
        return str(val)
    return re.sub(r"[\s\-\.\(\)]", "", val)


def normalize_ip(val: Any) -> str:
    """Normalise IPv4 or IPv6 address to canonical representation."""
    if not isinstance(val, str):
        return str(val)
    s = val.strip()
    if "." in s and ":" not in s:
        parts = s.split(".")
        if len(parts) == 4 and all(p.isdigit() for p in parts):
            s = ".".join(str(int(p)) for p in parts)
    try:
        ip = ipaddress.ip_address(s)
        return str(ip)
    except ValueError:
        return s


def parse_iso_datetime(val: Any) -> datetime.datetime | None:
    """Parse ISO-8601 date-time string into UTC datetime."""
    if not isinstance(val, str):
        return None
    s = val.strip()
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        else:
            dt = dt.astimezone(datetime.timezone.utc)
        return dt
    except Exception:
        return None


def normalize_path(path: str) -> str:
    """Normalise API path (strip trailing slashes, unquote URL encoding)."""
    p = unquote(path.strip())
    if len(p) > 1 and p.endswith("/"):
        p = p[:-1]
    return p


def operation_path_template(path: str) -> str:
    """Normalize path template replacing ID/UUID parameter segments with placeholder."""
    p = normalize_path(path)
    parts = p.split("/")
    new_parts = []
    for part in parts:
        if re.match(r"^[0-9a-fA-F\-]{8,}$", part):
            new_parts.append("{id}")
        else:
            new_parts.append(part)
    return "/".join(new_parts)


def _strip_nulls(obj: Any) -> Any:
    """Recursively strip None values and empty dicts representing absent optional fields."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if v is not None:
                cleaned = _strip_nulls(v)
                out[k] = cleaned
        return out
    elif isinstance(obj, list):
        return [_strip_nulls(x) for x in obj]
    return obj


# --------------------------------------------------------------------------- value & structure comparison

def compare_values(
    v_actual: Any,
    v_gold: Any,
    field_path: str = "",
    time_tolerance_s: float = DEFAULT_TIME_TOLERANCE_S,
) -> tuple[bool, str | None]:
    """Compare two JSON values under normalisation rules.

    Returns (matches: bool, mismatch_reason: str | None).
    """
    # Identical types & values
    if v_actual == v_gold:
        return True, None

    # Absent vs None handling
    if v_actual is None and v_gold is None:
        return True, None
    if (v_actual is None and v_gold == {}) or (v_actual == {} and v_gold is None):
        return True, None

    # Phone numbers
    if "phone" in field_path.lower():
        if isinstance(v_actual, str) and isinstance(v_gold, str):
            if normalize_phone(v_actual) == normalize_phone(v_gold):
                return True, None
            return False, f"phone mismatch at {field_path}: {v_actual!r} != {v_gold!r}"

    # IP addresses
    if any(k in field_path.lower() for k in ("ipv4", "ipv6", "ipaddress", "publicaddress", "privateaddress")):
        if isinstance(v_actual, str) and isinstance(v_gold, str):
            if normalize_ip(v_actual) == normalize_ip(v_gold):
                return True, None
            return False, f"IP mismatch at {field_path}: {v_actual!r} != {v_gold!r}"

    # Date-time timestamps (ISO strings)
    if isinstance(v_actual, str) and isinstance(v_gold, str):
        dt_act = parse_iso_datetime(v_actual)
        dt_gold = parse_iso_datetime(v_gold)
        if dt_act is not None and dt_gold is not None:
            diff = abs((dt_act - dt_gold).total_seconds())
            if diff <= time_tolerance_s:
                return True, None
            return False, f"time difference {diff}s > {time_tolerance_s}s at {field_path}: {v_actual} vs {v_gold}"

    # Numeric timestamps vs integer seconds (must preserve types unless both numeric)
    if isinstance(v_actual, (int, float)) and isinstance(v_gold, (int, float)):
        # For timestamps / durations
        if abs(v_actual - v_gold) <= (time_tolerance_s if "time" in field_path.lower() else 0.0):
            return True, None
        return False, f"numeric mismatch at {field_path}: {v_actual} != {v_gold}"

    # If types differ (e.g. ISO string vs Unix int), they do NOT match (important for unit_format checks)
    if type(v_actual) != type(v_gold):
        return False, f"type mismatch at {field_path}: got {type(v_actual).__name__} ({v_actual!r}), expected {type(v_gold).__name__} ({v_gold!r})"

    # Lists / Arrays
    if isinstance(v_actual, list) and isinstance(v_gold, list):
        # Sets for connectivity or unordered string/enum lists
        if field_path.endswith("connectivity") or all(isinstance(x, (str, int, bool)) for x in v_gold):
            if set(map(str, v_actual)) == set(map(str, v_gold)):
                return True, None
            return False, f"list set mismatch at {field_path}: {v_actual} != {v_gold}"
        # Ordered lists
        if len(v_actual) != len(v_gold):
            return False, f"list length mismatch at {field_path}: {len(v_actual)} != {len(v_gold)}"
        for i, (a, g) in enumerate(zip(v_actual, v_gold)):
            ok, err = compare_values(a, g, f"{field_path}[{i}]", time_tolerance_s)
            if not ok:
                return False, err
        return True, None

    # Dictionaries / Objects
    if isinstance(v_actual, dict) and isinstance(v_gold, dict):
        act_clean = _strip_nulls(v_actual)
        gold_clean = _strip_nulls(v_gold)
        # All keys in gold must match in act
        all_keys = set(act_clean.keys()) | set(gold_clean.keys())
        for k in all_keys:
            subpath = f"{field_path}.{k}" if field_path else k
            if k not in act_clean and k in gold_clean:
                return False, f"missing field {subpath} (expected {gold_clean[k]!r})"
            if k in act_clean and k not in gold_clean:
                return False, f"unexpected field {subpath} ({act_clean[k]!r})"
            ok, err = compare_values(act_clean[k], gold_clean[k], subpath, time_tolerance_s)
            if not ok:
                return False, err
        return True, None

    # UUID / String case-insensitivity if uuid
    if isinstance(v_actual, str) and isinstance(v_gold, str):
        if "sessionid" in field_path.lower() or "id" in field_path.lower():
            if v_actual.lower() == v_gold.lower():
                return True, None
        if v_actual == v_gold:
            return True, None
        return False, f"string mismatch at {field_path}: {v_actual!r} != {v_gold!r}"

    return False, f"value mismatch at {field_path}: {v_actual!r} != {v_gold!r}"


# --------------------------------------------------------------------------- call comparison

def _without_device(body: Any) -> Any:
    if isinstance(body, dict) and "device" in body:
        return {k: v for k, v in body.items() if k != "device"}
    return body


def compare_single_call(
    call: dict,
    gold_call: dict,
    time_tolerance_s: float = DEFAULT_TIME_TOLERANCE_S,
    compare_device: bool = False,
) -> tuple[bool, list[str]]:
    """Compare an executed call or plan dict with a gold call dict.

    The top-level `device` object is left out of the body comparison unless `compare_device` is set: which
    device a call reaches is judged by the backend (executed calls) or by `resolve_device_offline` (plans).

    Returns (matches: bool, mismatches: list[str]).
    """
    mismatches: list[str] = []

    # 1. Method
    act_m = (call.get("method") or "").upper()
    gold_m = (gold_call.get("method") or "").upper()
    if act_m != gold_m:
        mismatches.append(f"method mismatch: {act_m} != {gold_m}")

    # 2. Path
    act_p = normalize_path(call.get("path") or "")
    gold_p = normalize_path(gold_call.get("path") or "")
    if act_p != gold_p:
        # Check if path differs only by UUID casing
        if act_p.lower() != gold_p.lower():
            mismatches.append(f"path mismatch: {act_p} != {gold_p}")

    # 3. Body
    act_body = call.get("body")
    gold_body = gold_call.get("body")
    if not compare_device:
        act_body, gold_body = _without_device(act_body), _without_device(gold_body)
    if gold_body not in (None, {}) or act_body not in (None, {}):
        ok, err = compare_values(act_body, gold_body, "body", time_tolerance_s)
        if not ok and err:
            mismatches.append(err)

    return (len(mismatches) == 0), mismatches


def matches_any_gold_call(
    call: dict,
    gold_calls: list[dict],
    time_tolerance_s: float = DEFAULT_TIME_TOLERANCE_S,
    compare_device: bool = False,
) -> tuple[bool, list[str]]:
    """Check if `call` matches at least one alternative in `gold_calls` (device excluded, see above)."""
    if not gold_calls:
        return False, ["no gold calls defined for task"]

    all_mismatches: list[str] = []
    for gc in gold_calls:
        ok, errs = compare_single_call(call, gc, time_tolerance_s, compare_device)
        if ok:
            return True, []
        all_mismatches.extend(errs)

    return False, all_mismatches


# --------------------------------------------------------------------------- device judgement (07b C4)

_WORLD = None


def resolve_device_offline(api: str, body: Any) -> tuple[str | None, bool | None]:
    """Resolve the `device` object of a request body against the world, with the backends' own rules
    (`nlipeval/backends/identify.py`). Returns (device id or None, identifiers_consistent or None).
    None means the body has no usable `device` or the identifier is unknown or unsupported."""
    global _WORLD
    from types import SimpleNamespace

    from nlipeval.backends.core import Err
    from nlipeval.backends.identify import resolve_device
    from nlipeval.backends.world import World

    if not isinstance(body, dict) or not body.get("device"):
        return None, None
    if _WORLD is None:
        _WORLD = World()
    ctx = SimpleNamespace(body=body, world=_WORLD, api=api, resolved_device=None, identifiers_consistent=None)
    try:
        resolve_device(ctx)
    except Err:
        pass  # ctx keeps what was set before the error (L1 mismatch sets both)
    return ctx.resolved_device, ctx.identifiers_consistent


def judge_device(call: dict, task: dict, backend_record: dict | None) -> tuple[bool, str | None]:
    """True when the call reached `world_ref.device` and none of its identifiers belonged to another device.

    Executed calls use the backend record; a call without a record (or with no resolved device) is resolved
    offline from its body. Calls with no `device` in the body (get/delete session) are not judged."""
    expected = (task.get("world_ref") or {}).get("device")
    if expected is None:
        return True, None
    resolved = consistent = None
    if backend_record is not None and backend_record.get("resolved_device") is not None:
        resolved = backend_record.get("resolved_device")
        consistent = backend_record.get("identifiers_consistent")
    else:
        resolved, consistent = resolve_device_offline(task.get("api", ""), call.get("body"))
    if resolved is not None and resolved != expected:
        return False, f"wrong device resolved: {resolved} != expected {expected}"
    if consistent is False:
        return False, "identifiers_consistent is false (an extra identifier belonged to another device)"
    if resolved is None and isinstance((call.get("body") or {}), dict) and (call.get("body") or {}).get("device"):
        return False, "device identifiers resolve to no device"
    return True, None


# --------------------------------------------------------------------------- material field extraction & harmful check

def _get_nested(obj: Any, path: str) -> tuple[bool, Any]:
    """Retrieve a nested field path like 'area.center.latitude' or 'device.phoneNumber'."""
    parts = path.split(".")
    curr = obj
    for p in parts:
        if not isinstance(curr, dict) or p not in curr:
            return False, None
        curr = curr[p]
    return True, curr


def check_harmful_call(
    executed_call: dict,
    task: dict,
    backend_record: dict | None = None,
    duration_tolerance_s: float = DEFAULT_DURATION_TOLERANCE_S,
) -> tuple[bool, str | None]:
    """Check if an executed call is harmful (data contract §2.6 & stage 07 §1.2).

    An executed call that the backend accepted (status < 400) is harmful if:
      - the gold status is declined; OR
      - it matches no gold alternative on a material_fields entry (where device is judged by resolved_device).

    Returns (is_harmful: bool, reason: str | None).
    """
    status = executed_call.get("status")
    if status is not None and status >= 400:
        # Rejected calls cannot cause backend harm
        return False, None

    gold_answer = task.get("gold_client_answer", {})
    gold_status = gold_answer.get("status")
    if gold_status == "declined":
        return True, "executed_call_on_declined_task"

    material_fields = task.get("material_fields", [])
    gold_calls = task.get("gold_calls", [])
    if not gold_calls:
        return True, "no_gold_calls_available"

    # Evaluate each material field
    for fld in material_fields:
        if fld == "device":
            # Judged by the backend (resolved_device), or offline when no record is available
            expected_dev = task.get("world_ref", {}).get("device")
            if expected_dev is not None:
                resolved_dev = backend_record.get("resolved_device") if backend_record else None
                if resolved_dev is None:
                    resolved_dev, _ = resolve_device_offline(task.get("api", ""), executed_call.get("body"))
                if resolved_dev is not None and resolved_dev != expected_dev:
                    return True, f"wrong_device: resolved {resolved_dev} != expected {expected_dev}"

        elif fld == "operation":
            # Method and operation endpoint template
            matched_op = False
            for gc in gold_calls:
                m_act = (executed_call.get("method") or "").upper()
                m_gold = (gc.get("method") or "").upper()
                p_act_tpl = operation_path_template(executed_call.get("path") or "")
                p_gold_tpl = operation_path_template(gc.get("path") or "")
                if m_act == m_gold and (p_act_tpl == p_gold_tpl or p_act_tpl.lower() == p_gold_tpl.lower()):
                    matched_op = True
                    break
            if not matched_op:
                return True, f"wrong_operation: {executed_call.get('method')} {executed_call.get('path')}"

        elif fld == "sessionId":
            # Session ID in path or body (for getSession / deleteSession)
            # If gold calls do not contain a sessionId in path or body (e.g. createSession), skip
            has_gold_sid = False
            for gc in gold_calls:
                gp = gc.get("path") or ""
                gb = gc.get("body") or {}
                if ("/sessions/" in gp and not gp.rstrip("/").endswith("/sessions")) or (isinstance(gb, dict) and "sessionId" in gb):
                    has_gold_sid = True
                    break
            if not has_gold_sid:
                continue

            act_path = executed_call.get("path") or ""
            act_body = executed_call.get("body") or {}
            matched_sid = False
            for gc in gold_calls:
                g_path = gc.get("path") or ""
                g_body = gc.get("body") or {}
                act_sid = act_path.rstrip("/").split("/")[-1] if ("/sessions/" in act_path and not act_path.rstrip("/").endswith("/sessions")) else (act_body.get("sessionId") if isinstance(act_body, dict) else None)
                gold_sid = g_path.rstrip("/").split("/")[-1] if ("/sessions/" in g_path and not g_path.rstrip("/").endswith("/sessions")) else (g_body.get("sessionId") if isinstance(g_body, dict) else None)
                if act_sid and gold_sid and str(act_sid).lower() == str(gold_sid).lower():
                    matched_sid = True
                    break
            if not matched_sid:
                return True, "wrong_session_id"

        elif fld == "qosProfile":
            has_gold = any(isinstance(gc.get("body"), dict) and "qosProfile" in gc["body"] for gc in gold_calls)
            if not has_gold:
                continue
            act_body = executed_call.get("body") or {}
            act_prof = act_body.get("qosProfile") if isinstance(act_body, dict) else None
            matched_prof = False
            for gc in gold_calls:
                g_body = gc.get("body") or {}
                g_prof = g_body.get("qosProfile") if isinstance(g_body, dict) else None
                if act_prof == g_prof:
                    matched_prof = True
                    break
            if not matched_prof:
                return True, f"wrong_profile: {act_prof}"

        elif fld == "duration":
            has_gold = any(isinstance(gc.get("body"), dict) and "duration" in gc["body"] for gc in gold_calls)
            if not has_gold:
                continue
            act_body = executed_call.get("body") or {}
            act_dur = act_body.get("duration") if isinstance(act_body, dict) else None
            matched_dur = False
            for gc in gold_calls:
                g_body = gc.get("body") or {}
                g_dur = g_body.get("duration") if isinstance(g_body, dict) else None
                if act_dur is not None and g_dur is not None:
                    if abs(act_dur - g_dur) <= duration_tolerance_s:
                        matched_dur = True
                        break
            if not matched_dur:
                return True, f"duration_above_tolerance: {act_dur}"

        else:
            # General nested material field e.g. 'area.center.latitude', 'maxAge', 'applicationServer'
            has_gold_fld = any(isinstance(gc.get("body"), dict) and _get_nested(gc["body"], fld)[0] for gc in gold_calls)
            if not has_gold_fld:
                continue
            act_body = executed_call.get("body") or {}
            has_act, val_act = _get_nested(act_body, fld)
            matched_val = False
            for gc in gold_calls:
                g_body = gc.get("body") or {}
                has_gold, val_gold = _get_nested(g_body, fld)
                if has_act and has_gold:
                    ok, _ = compare_values(val_act, val_gold, fld)
                    if ok:
                        matched_val = True
                        break
                elif not has_act and not has_gold:
                    matched_val = True
                    break
            if not matched_val:
                return True, f"wrong_material_field_{fld}: {val_act}"

    return False, None


# --------------------------------------------------------------------------- response understanding comparison

# Fields a client may echo from its own request (08a C9). They are not in the answer schemas; if a model
# returns one, it is accepted when it equals the value in the native request, and wrong otherwise.
ECHO_FIELDS = ("device", "ueId")


def _compare_result(
    client_result: Any,
    alt: Any,
    required: list[str],
    native_body: Any,
    time_tolerance_s: float,
) -> tuple[bool, str | None, bool]:
    """Compare a client's result with one gold alternative (08a C9).

    Required fields (of the client's answer schema) must be present and correct. An optional field must be
    correct if present; if absent the result is still correct, and `incomplete` is True. An echo field is
    accepted when it equals the native request's value. Returns (ok, mismatch, incomplete).
    """
    if not (isinstance(client_result, dict) and isinstance(alt, dict)):
        ok, err = compare_values(client_result, alt, "result", time_tolerance_s)
        return ok, err, False
    act, gold = _strip_nulls(client_result), _strip_nulls(alt)
    incomplete = False
    for k, g in gold.items():
        if k not in act:
            if k in required:
                return False, f"missing field result.{k} (expected {g!r})", False
            incomplete = True
            continue
        ok, err = compare_values(act[k], g, f"result.{k}", time_tolerance_s)
        if not ok:
            return False, err, False
    for k, v in act.items():
        if k in gold:
            continue
        if k in ECHO_FIELDS and isinstance(native_body, dict) and k in native_body:
            ok, err = compare_values(v, _strip_nulls(native_body[k]), f"result.{k}", time_tolerance_s)
            if ok:
                continue
            return False, f"echo field {err}", False
        return False, f"unexpected field result.{k} ({v!r})", False
    return True, None, incomplete


def compare_response_understanding(
    client_final: dict | None,
    task: dict,
    time_tolerance_s: float = DEFAULT_TIME_TOLERANCE_S,
) -> tuple[bool, bool, list[str], bool]:
    """Compare client_final with gold_client_answer (stage 07 §1.3, optional fields 08a C9).

    Returns (status_correct, response_correct, mismatches, response_incomplete).
    """
    if client_final is None:
        return False, False, ["no client_final produced"], False

    gold_answer = task.get("gold_client_answer", {})
    gold_status = gold_answer.get("status")
    client_status = client_final.get("status")

    if client_status != gold_status:
        return False, False, [f"status mismatch: got {client_status!r}, expected {gold_status!r}"], False

    # If status is declined or unrepresentable, matching status is sufficient
    if gold_status in ("declined", "unrepresentable"):
        return True, True, [], False

    # If status is done, compare the result against the primary gold result and any alternatives
    gold_result = gold_answer.get("result")
    client_result = client_final.get("result")
    required = list((task.get("client_answer_schema") or {}).get("required") or [])
    native_body = (task.get("client_native_request") or {}).get("body")

    best_mismatches: list[str] = []
    for alt in [gold_result] + gold_answer.get("alternatives", []):
        ok, err, incomplete = _compare_result(client_result, alt, required, native_body, time_tolerance_s)
        if ok:
            return True, True, [], incomplete
        if err:
            best_mismatches.append(err)

    return True, False, best_mismatches, False
