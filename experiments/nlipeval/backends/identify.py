"""Device identification shared by the three backends.

The harness always acts as a two-legged client, so the `device` object is the only way to identify the
subject. Rules, each from the specifications' "Identifying the device from the access token" section
and the `Device` / `DeviceResponse` schemas:

- no `device` object        -> 422 MISSING_IDENTIFIER;
- several identifiers       -> the implementation selects ONE (order: phoneNumber, ipv4Address, ipv6Address)
                               and returns it in the response `device`; the others are not compared
                               ("No error should be returned if the identifiers are otherwise valid");
- only networkAccessIdentifier -> 422 UNSUPPORTED_IDENTIFIER (the specifications say the NAI is not supported);
- the selected identifier matches no device -> 404 IDENTIFIER_NOT_FOUND.
"""
from __future__ import annotations

from nlipeval.backends.core import Ctx, Err
from nlipeval.backends.world import Device

SELECTION_ORDER = ("phoneNumber", "ipv4Address", "ipv6Address")


def check_consistency(world, device: Device, dev: dict) -> bool:
    if "phoneNumber" in dev:
        if device.phone_number != dev["phoneNumber"]:
            return False
    if "ipv4Address" in dev:
        v4 = dev["ipv4Address"]
        if v4.get("publicAddress") != device.public_address:
            return False
        if "publicPort" in v4 and v4["publicPort"] is not None and v4["publicPort"] != device.public_port:
            return False
        if "privateAddress" in v4 and v4["privateAddress"] is not None and v4["privateAddress"] != device.private_address:
            return False
    if "ipv6Address" in dev:
        if world.by_ipv6(dev["ipv6Address"]) != device:
            return False
    if "networkAccessIdentifier" in dev:
        if device.network_access_identifier != dev["networkAccessIdentifier"]:
            return False
    return True


def resolve_device(ctx: Ctx) -> tuple[Device, dict | None]:
    """Returns (device, echo). `echo` is the `device` object for the response, or None when only one
    identifier was given (the response then omits `device`)."""
    dev = (ctx.body or {}).get("device") if isinstance(ctx.body, dict) else None
    if not dev:
        raise Err(422, "MISSING_IDENTIFIER", "The device cannot be identified.")
    chosen = next((k for k in SELECTION_ORDER if k in dev), None)
    if chosen is None:   # only networkAccessIdentifier
        raise Err(422, "UNSUPPORTED_IDENTIFIER", "The identifier provided is not supported.")
    w = ctx.world
    if chosen == "phoneNumber":
        found = w.by_phone(dev["phoneNumber"])
    elif chosen == "ipv4Address":
        v4 = dev["ipv4Address"]
        found = w.by_ipv4(v4["publicAddress"], v4.get("publicPort"), v4.get("privateAddress"))
    else:
        found = w.by_ipv6(dev["ipv6Address"])
    if found is None:
        raise Err(404, "IDENTIFIER_NOT_FOUND", "Device identifier not found.")
    
    consistent = check_consistency(w, found, dev)
    ctx.resolved_device = found.id
    ctx.identifiers_consistent = consistent

    if not consistent and ctx.api == "L1":
        raise Err(422, "IDENTIFIER_MISMATCH", "Provided identifiers are not consistent.")

    echo = {chosen: dev[chosen]} if len(dev) > 1 else None
    return found, echo
