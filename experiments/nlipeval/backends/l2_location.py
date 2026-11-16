"""L2 mock backend: Location Verification v3.0.0 (specs/L2/v3.0.0.yaml).

POST /location-verification/v3/verify

THE GEOMETRIC RULE (written down here and in reports/stage-04-backends.md)
-------------------------------------------------------------------------
Two circles on the Earth's surface, treated as planar discs of radius in metres:

- R, the requested area: centre = request `area.center`, radius = request `area.radius`;
- N, the network's estimate: centre = the device's stored position, radius = its `accuracy_m`.

d = great-circle (haversine) distance between the centres, in metres. Then, in this order:

1. d + rN <= rR   (N lies inside R)            -> TRUE      ("fully contained within the requested area")
2. d >= rR + rN   (no overlap)                  -> FALSE     ("does not overlap ... at all")
3. otherwise                                    -> PARTIAL   ("partially overlaps, or fully contains the
                                                              requested area (because it is larger)")
   matchRate = round(100 * area(R ∩ N) / area(N)), clamped to 1..99 (the MatchRate schema range).
   This is the specification's definition (R ∩ N) / N * 100. area(R ∩ N) is the standard two-circle lens
   area; if R lies inside N it is area(R).

Two circles that touch from outside (d == rR + rN) do not overlap: FALSE.

Error order (first match wins; every code is in the 400, 422 or 404 response of the specification):
Circle schema (400) -> device (MISSING_IDENTIFIER, UNSUPPORTED_IDENTIFIER, 404 IDENTIFIER_NOT_FOUND) ->
radius below `min_radius_m` (INVALID_AREA) -> centre outside the coverage box (AREA_NOT_COVERED) ->
location (see below).

`maxAge` (seconds), read as the specification's "Max Age" definition says:
- absent: any age is acceptable; the response carries `lastLocationTime` = clock - stored age;
- present and the stored age <= maxAge: the stored fix is used, `lastLocationTime` as above;
- present and the stored age > maxAge (maxAge=0 means "a fresh calculation"): if the device has
  `fresh_available`, the network computes a fresh fix: same position, `lastLocationTime` = clock;
  otherwise 422 LOCATION_VERIFICATION.UNABLE_TO_FULFILL_MAX_AGE, whatever the verification result would be;
- the device has no known location: with maxAge present, UNABLE_TO_FULFILL_MAX_AGE ("older than the
  specified maxAge or not known at all"); without maxAge, UNABLE_TO_LOCATE ("the network cannot locate
  the device").
"""
from __future__ import annotations

import math
from datetime import timedelta
from pathlib import Path

from nlipeval.backends.core import ApiDef, Backend, Ctx, Err, Result
from nlipeval.backends.identify import resolve_device
from nlipeval.backends.world import World, fmt_ts


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float, radius: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dlmb = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * radius * math.asin(min(1.0, math.sqrt(a)))


def lens_area(d: float, r1: float, r2: float) -> float:
    """Area of the intersection of two discs with radii r1, r2 whose centres are d apart."""
    if d >= r1 + r2:
        return 0.0
    if d <= abs(r1 - r2):
        return math.pi * min(r1, r2) ** 2
    a1 = math.acos((d * d + r1 * r1 - r2 * r2) / (2 * d * r1))
    a2 = math.acos((d * d + r2 * r2 - r1 * r1) / (2 * d * r2))
    return (r1 * r1 * (a1 - math.sin(2 * a1) / 2)) + (r2 * r2 * (a2 - math.sin(2 * a2) / 2))


def classify(d: float, r_req: float, r_net: float) -> tuple[str, int | None]:
    """The location rule: returns (TRUE|FALSE|PARTIAL, matchRate or None)."""
    if d + r_net <= r_req:
        return "TRUE", None
    if d >= r_req + r_net:
        return "FALSE", None
    rate = round(100 * lens_area(d, r_req, r_net) / (math.pi * r_net ** 2))
    return "PARTIAL", max(1, min(99, rate))


def verify(ctx: Ctx) -> Result:
    body = ctx.body
    area = body["area"]
    ctx.check_schema("Circle", area)   # openapi-core does not follow the Area discriminator
    dev, echo = resolve_device(ctx)
    radius = area["radius"]
    lat, lon = area["center"]["latitude"], area["center"]["longitude"]
    rules = ctx.world.location_rules
    if radius < rules["min_radius_m"]:
        raise Err(422, "LOCATION_VERIFICATION.INVALID_AREA", "The requested area is too small")
    cov = rules["coverage"]
    if not (cov["lat_min"] <= lat <= cov["lat_max"] and cov["lon_min"] <= lon <= cov["lon_max"]):
        raise Err(422, "LOCATION_VERIFICATION.AREA_NOT_COVERED", "Unable to cover the requested area")

    loc = dev.location
    max_age = body.get("maxAge")
    if loc is None:
        if max_age is not None:
            raise Err(422, "LOCATION_VERIFICATION.UNABLE_TO_FULFILL_MAX_AGE",
                      "Unable to provide expected freshness for location")
        raise Err(422, "LOCATION_VERIFICATION.UNABLE_TO_LOCATE", "The network is unable to locate the device")
    age = loc.age_s
    if max_age is not None and age > max_age:
        if not loc.fresh_available:
            raise Err(422, "LOCATION_VERIFICATION.UNABLE_TO_FULFILL_MAX_AGE",
                      "Unable to provide expected freshness for location")
        age = 0   # fresh calculation

    d = haversine_m(lat, lon, loc.latitude, loc.longitude, ctx.world.location_rules["earth_radius_m"])
    result, rate = classify(d, radius, loc.accuracy_m)
    out: dict = {"verificationResult": result, "lastLocationTime": fmt_ts(ctx.clock - timedelta(seconds=age))}
    if rate is not None:
        out["matchRate"] = rate
    if echo:
        out["device"] = echo
    return Result(200, out, {"device": dev.id, "distance_m": round(d, 1), "result": result, "matchRate": rate})


API = ApiDef(api="L2", spec="L2/v3.0.0.yaml", base_path="/location-verification/v3",
             routes=[("POST", "/verify", verify)], allows_out_of_range=True)


def make_backend(world: World | None = None, run_dir: Path | None = None) -> Backend:
    return Backend(API, world, run_dir)
