"""L1 mock backend: Device Reachability Status v1.0.0 (specs/L1/v1.0.0.yaml).

POST /device-reachability-status/v1/retrieve

World mapping (config/world/devices.yaml, `reachability.state`):

| state     | reachable | connectivity      |
|-----------|-----------|-------------------|
| DATA_SMS  | true      | ["DATA", "SMS"]   |
| DATA_ONLY | true      | ["DATA"]          |
| SMS_ONLY  | true      | ["SMS"]           |
| NONE      | false     | (absent)          |

`lastStatusTime` = clock minus the device's `last_status_age_s`. The "Not-Reachable" example in the
specification has no `connectivity`, so it is left out for unreachable devices.
"""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from nlipeval.backends.core import ApiDef, Backend, Ctx, Result
from nlipeval.backends.identify import resolve_device
from nlipeval.backends.world import World, fmt_ts

CONNECTIVITY = {"DATA_SMS": ["DATA", "SMS"], "DATA_ONLY": ["DATA"], "SMS_ONLY": ["SMS"], "NONE": None}


def retrieve(ctx: Ctx) -> Result:
    dev, _echo = resolve_device(ctx)
    body: dict = {"lastStatusTime": fmt_ts(ctx.clock - timedelta(seconds=dev.status_age_s)),
                  "reachable": dev.reach_state != "NONE"}
    conn = CONNECTIVITY[dev.reach_state]
    if conn:
        body["connectivity"] = conn
    return Result(200, body, {"device": dev.id, "state": dev.reach_state})


API = ApiDef(api="L1", spec="L1/v1.0.0.yaml", base_path="/device-reachability-status/v1",
             routes=[("POST", "/retrieve", retrieve)], allows_out_of_range=False)


def make_backend(world: World | None = None, run_dir: Path | None = None) -> Backend:
    return Backend(API, world, run_dir)
