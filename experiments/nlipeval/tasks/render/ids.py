"""Identifier helpers shared by the three renderers (stage 05, corrected in stage 07b).

Every device identifier is derived from the device number `n` of the world (D01..D30):
phone `+990100NNNN`, public IPv4 `192.0.2.n` with port `40000+n`, private IPv4 `203.0.113.n`,
IPv6 `2001:db8:a:<n hex>::1`, NAI `devNNN@nlipeval.example`.

Gold devices (07b A1, A2): the gold call carries only what the client can know.
- phone and IPv6: the identifier;
- IPv4: `publicAddress` + `publicPort` (both are in the intent text). An alternative that also has
  `privateAddress` exists only where the client's native request contains it;
- NAI-only intents: the identifier from the client's facts, plus an alternative with both identifiers.
"""
from __future__ import annotations

NAI_ONLY = "network_access_identifier"

# Versions whose phone pattern allows numbers without "+" and whose native request omits it for
# intents whose number mod 4 is 1 or 2 (08a D11, which replaces the even-number rule of 07b A10).
PHONE_WITHOUT_PLUS = {("L1", "v0.5.1"), ("L2", "v0.1.0"), ("L3", "v0.8.1")}


def num(device_id: str) -> int:
    return int(device_id[1:])


def phone(n: int, plus: bool = True) -> str:
    return ("+" if plus else "") + f"990100{n:04d}"


def public_ipv4(n: int) -> str:
    return f"192.0.2.{n}"


def private_ipv4(n: int) -> str:
    return f"203.0.113.{n}"


def public_port(n: int) -> int:
    return 40000 + n


def ipv6(n: int) -> str:
    return f"2001:db8:a:{n:x}::1"


def nai(n: int) -> str:
    return f"dev{n:03d}@nlipeval.example"


def intent_number(intent: dict) -> int:
    return int(intent["id"][1:])


def phone_plus(api: str, version: str, intent: dict) -> bool:
    """Whether the native request carries the phone number with its leading "+"."""
    if (api, version) in PHONE_WITHOUT_PLUS and intent_number(intent) % 4 in (1, 2):
        return False
    return True


def fact(intent: dict, name: str) -> str | None:
    for f in intent.get("client_facts", []):
        if f["fact"] == name:
            return f["value"]
    return None


def server_form_device(intent: dict, *, plus: bool = True, private: bool = False) -> dict:
    """`device` object in server form (device / phoneNumber / ipv4Address / ...) for the intent's own identifier."""
    p = intent["params"]
    n = num(p["device_id"])
    ident = p["identifier"]
    if ident == "phone_number":
        return {"phoneNumber": phone(n, plus)}
    if ident == "ipv4_with_port":
        v4 = {"publicAddress": public_ipv4(n)}
        if private:
            v4["privateAddress"] = private_ipv4(n)
        v4["publicPort"] = public_port(n)
        return {"ipv4Address": v4}
    if ident == "ipv6":
        return {"ipv6Address": ipv6(n)}
    if ident == NAI_ONLY:
        return {"networkAccessIdentifier": nai(n)}
    raise ValueError(f"Unknown identifier type: {ident!r}")


def fact_device(intent: dict) -> dict:
    """The second identifier of an NAI-only intent, taken from the client's facts."""
    v = fact(intent, "phone_number")
    if v is not None:
        return {"phoneNumber": v}
    v = fact(intent, "ipv6_address")
    if v is not None:
        return {"ipv6Address": v}
    raise ValueError(f"{intent['id']}: NAI-only intent without a second identifier in its facts")


def gold_devices(intent: dict, *, native_has_private: bool) -> list[dict]:
    """Acceptable `device` objects of the gold call, primary first."""
    ident = intent["params"]["identifier"]
    if ident == NAI_ONLY:
        second = fact_device(intent)
        both = {**second, "networkAccessIdentifier": nai(num(intent["params"]["device_id"]))}
        return [second, both]
    primary = server_form_device(intent)
    out = [primary]
    if ident == "ipv4_with_port" and native_has_private:
        out.append(server_form_device(intent, private=True))
    return out


def gold_device_field(intent: dict) -> str | None:
    """Server path of the second identifier of an NAI-only intent, or None."""
    if intent["params"].get("identifier") != NAI_ONLY:
        return None
    return "device.phoneNumber" if fact(intent, "phone_number") is not None else "device.ipv6Address"
