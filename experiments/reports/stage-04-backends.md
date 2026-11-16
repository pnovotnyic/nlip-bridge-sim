# Stage 04: mock API backends and the world they serve

Date: 2026-11-13. Branch `bob/experiments`. Tests: `uv run pytest` gives 147 passed (33 of them in `tests/test_backends.py`).

## What was done

Three FastAPI applications, one per API at its current version, built on one shared core (`nlipeval/backends/core.py`).
For every request the core: reads `X-Eval-Session` and `X-Eval-Clock`, validates the request against the pinned
specification with `openapi-core`, calls the handler, validates the response against the same specification, and appends one line to `backend.jsonl`.
A response that fails validation is replaced by `500 BACKEND_BUG`, so a backend bug cannot pass unnoticed.

| File | Content |
|---|---|
| `config/world/devices.yaml` | 40 devices D01–D40 |
| `config/world/qos_profiles.yaml` | 6 QoS profiles (single source for the backend and the profile table) |
| `config/world/sessions.yaml` | 10 existing QoD sessions, on D31–D40 |
| `config/world/service.yaml` | default clock, ports, address ranges, location rules |
| `nlipeval/backends/world.py` | loader, consistency check (`World.check()`), `world_hash` |
| `nlipeval/backends/core.py` | validation, error mapping, per-session state, logging, admin endpoints |
| `nlipeval/backends/identify.py` | device identification shared by the three APIs |
| `nlipeval/backends/l1_reachability.py`, `l2_location.py`, `l3_qod.py` | the handlers |
| `nlipeval/backends/profile_table.py` | renders the profile table for the L3 server prompt |
| `nlipeval/backends/launcher.py` | `up`, `down`, `status`, `serve` |
| `tests/test_backends.py` | 33 tests |

`world_hash` (SHA-256 of the four world files, in name order) is `2a5fc6dd450eac44c6b002ac8360e14d815ed804e2a694341971ffacf805990e` at the time of writing. It is returned by `GET /__admin/health` and must go into each run's `manifest.json`.
The world files may change until the freeze (stage 08).

## Starting and stopping

```bash
cd experiments
uv run python -m nlipeval.backends.launcher up --run-dir data/runs/<run_id>     # L1 :9101, L2 :9102, L3 :9103
uv run python -m nlipeval.backends.launcher status
uv run python -m nlipeval.backends.launcher down
```

`--base-port N` moves the three ports to N, N+1, N+2. Process IDs are kept in `.backends/state.json` (git-ignored).
`<run-dir>/backend.jsonl` receives every request. Without `--run-dir` nothing is logged.

## Endpoints

| API | Base path | Implemented | Not implemented (answer `404 NOT_FOUND`) |
|---|---|---|---|
| L1 Device Reachability Status v1.0.0 | `/device-reachability-status/v1` | `POST /retrieve` | – |
| L2 Location Verification v3.0.0 | `/location-verification/v3` | `POST /verify` | – |
| L3 Quality-on-Demand v1.1.0 | `/quality-on-demand/v1` | `POST /sessions`, `GET /sessions/{sessionId}`, `DELETE /sessions/{sessionId}` | `POST /sessions/{id}/extend`, `POST /retrieve-sessions`, the QoS Profiles API (no task uses them) |

Admin endpoints, on every backend, never shown to agents: `GET /__admin/health`, `POST /__admin/reset[?session=ID]`, `GET /__admin/state?session=ID`.

Request headers: `X-Eval-Session` (state key; `default` if absent), `X-Eval-Clock` (RFC 3339; the clock for every time in the response, default `2026-12-01T12:00:00Z`; stage 05 sets one per task), `x-correlator` (echoed).

## World summary

| Item | Count |
|---|---|
| Devices | 40 (phone numbers `+9901000001`–`+9901000040`; see "Synthetic identifiers") |
| Reachability: DATA+SMS / DATA only / SMS only / not reachable | 16 / 8 / 8 / 8 |
| Devices with a stored location | 35 |
| Devices with no known location | 5 (D03, D11, D19, D27, D35) |
| Devices whose stored fix is old and the network cannot refresh it (`fresh_available: false`) | 6 |
| Stored location ages (s): 30 / 45 / 120 / 600 / 3600 / 86400 | 6 / 6 / 7 / 5 / 7 / 4 |
| QoS profiles ACTIVE / INACTIVE / DEPRECATED | 4 / 1 / 1 |
| Existing QoD sessions AVAILABLE / UNAVAILABLE (DURATION_EXPIRED, NETWORK_TERMINATED) | 8 / 2 (1 + 1) |

Intended use by stage 05: D01–D30 for tasks that create sessions or read reachability and location; D31–D40 carry the existing QoD sessions (get and delete tasks). Nothing stops a task using any device.

### Synthetic identifiers

- Phone numbers: `+990100NNNN`. The prefix `+990` is not assigned in E.164. The numbers match the CAMARA `PhoneNumber` pattern `^\+[1-9][0-9]{4,14}$`.
- IPv4: public addresses from `192.0.2.0/24` (D31–D40 reuse the public addresses of D01–D10, as under carrier-grade NAT; they differ by port and private address), private addresses from `203.0.113.0/24`, application servers expected in `198.51.100.0/24`.
- IPv6: each device owns the `/64` `2001:db8:a:<n in hex>::/64`. Any address inside it identifies the device. Application servers may use `2001:db8:b::/48`.
- Network access identifiers: `devNNN@nlipeval.example`.
- A test (`test_world_files_use_only_documented_ranges`) fails if a world file contains an address outside these ranges.

## Device identification (all three APIs)

The harness is always a two-legged client, so `device` is the only way to identify the subject.

| Request | Answer |
|---|---|
| no `device` | `422 MISSING_IDENTIFIER` |
| only `networkAccessIdentifier` | `422 UNSUPPORTED_IDENTIFIER` (all three specifications say this identifier is not usable yet) |
| one identifier | used; no `device` in the response |
| several identifiers | L2 & L3: the first of phoneNumber, ipv4Address, ipv6Address is used and returned in the response `device`; the others are not compared, as the `DeviceResponse` description requires.<br>L1: if all belong to the same device, that device is used. If they belong to different devices, `422 IDENTIFIER_MISMATCH` is returned. |
| identifier matches no device | `404 IDENTIFIER_NOT_FOUND` |

IPv4 identification needs every given component to match (`publicAddress`, and `publicPort` and/or `privateAddress`).

## L1: answers

| World state | `reachable` | `connectivity` |
|---|---|---|
| DATA_SMS | true | `["DATA","SMS"]` |
| DATA_ONLY | true | `["DATA"]` |
| SMS_ONLY | true | `["SMS"]` |
| NONE | false | omitted (as in the specification's "Not-Reachable" example) |

`lastStatusTime` = clock minus the device's `last_status_age_s`.

## L2: the location rule

Two discs on the Earth's surface. R is the requested area (centre and `radius` from the request). N is the network's estimate (the device's stored position and `accuracy_m`).
d is the haversine distance between the centres in metres (sphere radius 6,371,008.8 m). In this order:

1. `d + rN <= rR` (N inside R): **TRUE**.
2. `d >= rR + rN` (the discs do not overlap; touching from outside counts as no overlap): **FALSE**.
3. Otherwise **PARTIAL**, with `matchRate = round(100 · area(R ∩ N) / area(N))`, clamped to 1–99 (the `MatchRate` schema range). This is the specification's definition. If R lies inside N, the intersection is the whole of R.

The same text is in the module docstring of `l2_location.py`.

Order of checks: `Circle` schema (400) → device → `radius < 1000 m` gives `INVALID_AREA` → centre outside the coverage box (lat 35–60, lon −12–25) gives `AREA_NOT_COVERED` → location.

`maxAge`, as the specification says:

| Situation | Answer |
|---|---|
| `maxAge` absent | stored fix used; `lastLocationTime` = clock − stored age |
| stored age ≤ `maxAge` | same |
| stored age > `maxAge` (including `maxAge=0`), network can refresh (`fresh_available`) | fresh fix: same position, `lastLocationTime` = clock |
| stored age > `maxAge`, network cannot refresh | `422 UNABLE_TO_FULFILL_MAX_AGE`, whatever the verification result would be |
| no known location, `maxAge` present | `422 UNABLE_TO_FULFILL_MAX_AGE` (spec line 20: "older … or not known at all") |
| no known location, `maxAge` absent | `422 UNABLE_TO_LOCATE` |

## L3: profile limits and session rules

| Profile | Status | Min duration | Max duration | Description |
|---|---|---|---|---|
| QOS_E | ACTIVE | 60 s | 1,800 s (30 min) | stable low latency for real-time traffic such as gaming and voice |
| QOS_S | ACTIVE | 60 s | 86,400 s (24 h) | light traffic with modest latency needs, such as messaging and telemetry |
| QOS_M | ACTIVE | 60 s | 7,200 s (2 h) | balanced latency and throughput for video calls and streaming |
| QOS_L | ACTIVE | 300 s | 14,400 s (4 h) | high throughput for large transfers and live video production |
| QOS_XL | INACTIVE | 300 s | 14,400 s | very high throughput for bulk uploads; not currently offered |
| voice | DEPRECATED | 60 s | 3,600 s | legacy voice profile; existing sessions continue, new sessions are refused |

`profile_table.py` renders exactly this file (`name | status | min duration | max duration | description`). `test_profile_table_and_backend_agree_on_every_profile` checks, for every profile, that the backend accepts the table's maximum, refuses maximum + 1 and minimum − 1, and refuses non-ACTIVE profiles.
The specification does not give minimum durations; the values here are our choice, applied to `duration` the same way as the maximum (the specification defines `minDuration` in the QoS Profiles API: "the shortest time period that this profile can be deployed").

`createSession` checks, in order: request schema → `sinkCredential` → `applicationServer` syntax → device → profile (exists, ACTIVE) → duration within the profile's range → conflict (same device, same application server and ports, session not deleted). It then creates the session with `qosStatus: AVAILABLE`, `startedAt` = clock, `expiresAt` = clock + `duration`, granted duration = requested duration.
`sink` is only validated (must be `https://`), never called. `sinkCredential` is never echoed back (as in the specification's examples). Deleting a session removes it; the flow is then free again. Deleting a session from the world file hides it in that eval session only.
Session IDs are `UUIDv5(namespace, "<eval session>:<counter>")`; world sessions keep the fixed IDs in `sessions.yaml`.

## Error codes used, with the line of the specification

All codes are taken from the response definitions of the pinned files. `test_error_codes_are_in_the_specifications` fails if a code used here is missing from the operation's response schemas.

| API | Status | Code | Raised when | Spec line |
|---|---|---|---|---|
| L1 | 400 | `INVALID_ARGUMENT` | request fails schema validation (bad address, empty `device`, bad JSON, wrong header) | `specs/L1/v1.0.0.yaml:324` |
| L1 | 404 | `IDENTIFIER_NOT_FOUND` | no device matches | `L1/v1.0.0.yaml:407` |
| L1 | 422 | `MISSING_IDENTIFIER` | no `device` | `L1/v1.0.0.yaml:440` |
| L1 | 422 | `UNSUPPORTED_IDENTIFIER` | only `networkAccessIdentifier` | `L1/v1.0.0.yaml:441` |
| L1 | 422 | `IDENTIFIER_MISMATCH` | several identifiers of different devices | `L1/v1.0.0.yaml:438` |
| L2 | 400 | `INVALID_ARGUMENT`, `OUT_OF_RANGE` | schema violation; `minimum`/`maximum` violation (e.g. latitude 95) | `L2/v3.0.0.yaml:516–517` |
| L2 | 404 | `IDENTIFIER_NOT_FOUND` | no device matches | `L2/v3.0.0.yaml:601` |
| L2 | 422 | `MISSING_IDENTIFIER`, `UNSUPPORTED_IDENTIFIER` | as L1 | `L2/v3.0.0.yaml:628–629` |
| L2 | 422 | `LOCATION_VERIFICATION.AREA_NOT_COVERED` | centre outside the coverage box | `L2/v3.0.0.yaml:631` |
| L2 | 422 | `LOCATION_VERIFICATION.INVALID_AREA` | radius below 1,000 m | `L2/v3.0.0.yaml:632` |
| L2 | 422 | `LOCATION_VERIFICATION.UNABLE_TO_FULFILL_MAX_AGE` | see `maxAge` table | `L2/v3.0.0.yaml:633` |
| L2 | 422 | `LOCATION_VERIFICATION.UNABLE_TO_LOCATE` | no known location, no `maxAge` | `L2/v3.0.0.yaml:634` |
| L3 | 400 | `INVALID_ARGUMENT`, `OUT_OF_RANGE` | schema violation; `minimum`/`maximum` violation (e.g. `duration` 0) | `specs/L3/v1.1.0.yaml:1035–1036` |
| L3 | 400 | `QUALITY_ON_DEMAND.DURATION_OUT_OF_RANGE` | duration outside the profile's range | `L3/v1.1.0.yaml:1038` |
| L3 | 400 | `INVALID_CREDENTIAL`, `INVALID_TOKEN`, `INVALID_SINK` | credential type not ACCESSTOKEN; token type not bearer; `sink` not `https://` | `L3/v1.1.0.yaml:1039–1041` |
| L3 | 404 | `IDENTIFIER_NOT_FOUND` | no device matches | `L3/v1.1.0.yaml:1247` |
| L3 | 404 | `NOT_FOUND` | unknown session (get, delete); unknown profile (see below) | `L3/v1.1.0.yaml:1220`, `:1246` |
| L3 | 409 | `CONFLICT` | same device and flow already has a session | `L3/v1.1.0.yaml:1279` |
| L3 | 422 | `MISSING_IDENTIFIER`, `UNSUPPORTED_IDENTIFIER` | as L1 | `L3/v1.1.0.yaml:1401–1402` |
| L3 | 422 | `QUALITY_ON_DEMAND.QOS_PROFILE_NOT_APPLICABLE` | profile exists but is INACTIVE or DEPRECATED | `L3/v1.1.0.yaml:1404` (rule text: line 83) |

Not used: `UNAUTHENTICATED`, `PERMISSION_DENIED`, `TOO_MANY_REQUESTS`, `QUOTA_EXCEEDED` (no authentication or rate limit in the mock), and the `SESSION_EXTENSION_NOT_ALLOWED` code (extend is not implemented).

## Choices the specifications leave open (for Petr's review)

1. **Unknown QoS profile gives `404 NOT_FOUND`.** The QoD v1.1.0 text names no code for a profile that does not exist, only `QOS_PROFILE_NOT_APPLICABLE` for one that exists but is not usable (line 83). `NOT_FOUND` is in the create operation's 404 response. The scorer should treat any 4xx for an unknown profile as the correct refusal.
2. **Sessions become `AVAILABLE` immediately.** The mock never returns `REQUESTED`, and sends no notification. Tasks therefore never need to wait.
3. **Minimum durations** are our values (see above).
4. **Same-flow conflict** compares application server and both port specifications by exact equality, not by overlap.
5. **Several device identifiers**: for L2 and L3, the first of phoneNumber, ipv4Address, ipv6Address is used. For L1, several identifiers that belong to different devices give `422 IDENTIFIER_MISMATCH`, while identifiers belonging to the same device succeed.
6. **L2 coverage box and minimum radius (1,000 m)** are our values. The `Circle.radius` description suggests "e.g. 1000 meters".
7. **`Area` and `SinkCredential` subschemas** are selected by `discriminator`, which `openapi-core` 0.23.1 does not follow. The handlers validate `Circle` and `AccessTokenCredential` explicitly against the same pinned specification (`Backend.check_schema`). The error codes and messages are the same as for any other schema violation.
8. **Error `message` text** for 400 responses is built from the validator's complaint (`field: reason`), truncated to 300 characters. The specification gives only a generic sentence.

## Deviations from the plan and additions to the data contract

- No deviations from the stage file. The QoS Profiles API (optional in the plan) is not implemented.
- `backend.jsonl` has the fields of data contract §2.5 and six additions, recorded in `reports/schema-changes.md`: `schema_version`, `clock`, `response_valid`, `response_errors`, `resolved_device`, `identifiers_consistent`.

## Problems

- `openapi-core` prints `UserWarning: Unsupported scheme type` for the `openIdConnect` security scheme. It is silenced in `core.py`; pytest still shows it 19 times from the test process (a harmless warning in the library, not our code).
- The launcher test starts three real processes on ports 19400–19402 and takes about 10 s.

## Done-when check

- All tests pass: `uv run pytest` gives 147 passed.
- Every response in the tests validates: `test_every_response_validates_and_is_logged` checks `response_valid` on all logged responses; the core turns any invalid response into a `500 BACKEND_BUG`, which the tests would catch.
- One command each starts and stops all three backends: `launcher up` and `launcher down` (checked by hand and by `test_launcher_http`).
