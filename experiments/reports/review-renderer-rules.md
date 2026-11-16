# Renderer rules — stage 05, corrected in stage 07b

One section per API. Each row is one catalogue entry or one gold-call rule that the renderers implement
(`nlipeval/tasks/render/{ids,l1,l2,l3}.py`, tags in `nlipeval/tasks/tags.py`).

## Derivability rules (07b)

Every gold answer must be reachable from what the agents are given. A leaf of a gold call is accepted only if it comes from:

1. **the intent text**: identifiers, ports, durations, ages, radii, coordinates, notification URLs;
2. **a client fact**: the second identifier of an NAI-only intent, a preference that decides between alternatives
   (L3 m01/m11 profile, L2 m30 age);
3. **the native request**: a value the client already sent, possibly renamed, moved or converted (km to m, boolean to enum);
4. **a constant fixed by the server interface**: `area.areaType = CIRCLE` is the only one. It is not in `missing_info`.

Nothing else may appear in a gold call. `privateAddress`, the world's reachability or location state, profile limits and
server-only field names are never gold values and never in facts. The test `test_every_gold_value_is_reachable` checks rule 1-4 on all 510
instances; `test_fact_lint` checks the facts.

Gold devices (`render/ids.py`):

| Identifier in the intent | Gold `device` | Alternatives |
|---|---|---|
| phone number | `phoneNumber` with "+" | none |
| IPv6 | `ipv6Address` | none |
| IPv4 + port | `ipv4Address{publicAddress, publicPort}` | one with `privateAddress` only where the native request has it (nowhere) |
| NAI only | the fact's identifier (phone or IPv6), gold status `done` | the same plus the NAI |

Phone numbers without "+": at L1 v0.5.1, L2 v0.1.0 and L3 v0.8.1 the patterns allow them, so the native request of even-numbered
intents has no "+". The gold keeps "+". `unit_format` is tagged only where the rendered form differs (so never at L2 v0.2.0, L3 v0.9.0 and
v0.10.0, where all native numbers have "+").

## L1 Device Reachability Status

**Server v1.0.0 | clients v0.5.1, v0.6.0.** Native paths: `/device-status/v0/connectivity` (v0.5.1), `/device-reachability-status/v0.6/retrieve` (v0.6.0).

| Entry | Direction | Version | Rule |
|---|---|---|---|
| `POST /connectivity` to `POST /retrieve` (renamed) | request | v0.5.1 | native path is the v0 path, the gold path is the v1 path |
| `device.phoneNumber` pattern (unit_format) | request | v0.5.1 | even-numbered intents: no "+" in the native request |
| `connectivityStatus` to `reachable`, `connectivity[]` | response | v0.5.1 | DATA present gives `CONNECTED_DATA`; SMS only gives `CONNECTED_SMS`; not reachable gives `NOT_CONNECTED` |
| `reachabilityStatus` to `reachable`, `connectivity[]` | response | v0.6.0 | same rule, `lastStatusTime` kept |
| any error | response | all | `declined`: no result because the service refused. NAI-only intents are `done` through the fact's identifier |

## L2 Location Verification

**Server v3.0.0 | clients v0.1.0, v0.2.0, v1.0.0, v2.0.0.** Native paths: `/location/v0/verify` (v0.1.0), `/location-verification/v0/verify` (v0.2.0).

| Entry | Direction | Version | Rule |
|---|---|---|---|
| `ueId` to `device`, `msisdn`, `externalId`, `ipv4Addr`, `ipv6Addr` | request | v0.1.0 | renamed, restructured; `msisdn` without "+" for even-numbered intents |
| `uePort` to `device.ipv4Address.publicPort` | request | v0.1.0 | the port is its own field: nothing is missing |
| `latitude`, `longitude` to `area.center.*` | request | v0.1.0 | moved |
| `accuracy` (km) to `area.radius` (m) | request | v0.1.0 | `accuracy = radius / 1000`; the minimum is 2 km, so every radius is at least 2000 m; **never clamped**: the renderer raises an error |
| `area.areaType` (newly_required) | request | v0.1.0 | server constant `CIRCLE`; not in `missing_info` |
| `maxAge` (added_optional) | request | v0.1.0 | absent from the native request; in `missing_info` (source `intent_text`) for the 5 intents with an age |
| `maxAge` minimum 60 | request | v0.2.0 | a native `maxAge: 0` is sent as 60; the gold has both alternatives |
| `verificationResult` boolean to enum | response | v0.1.0 | TRUE/FALSE to true/false; PARTIAL gives `unrepresentable` |
| UNABLE_TO_LOCATE | response | v0.1.0 | `unrepresentable`; the only response tag is the `verificationResult` entry |
| UNABLE_TO_LOCATE | response | v0.2.0 to v2.0.0 | `done` with `UNKNOWN`; the only response tag is `verificationResult=UNKNOWN` (changed_meaning) |
| UNABLE_TO_LOCATE | response | v3.0.0 | `declined` |
| UNABLE_TO_FULFILL_MAX_AGE, other errors | response | all | `declined`, no response tags |

L2 m30: fact "If a fresh reading is not possible, a reading up to one hour old is acceptable." The gold call has `maxAge: 3600`
(`missing_info` is `maxAge`, source `fact`). The expected path is a refused `maxAge: 0` call, then a revised call that is accepted.

## L3 Quality-on-Demand

**Server v1.1.0 | clients v0.8.1 to v1.0.0.** Native base paths: `/qod/v0` (v0.8.1, v0.9.0, v0.10.0), `/quality-on-demand/v0.11` (v0.11.0), `/quality-on-demand/v1` (v1.0.0).

| Entry | Direction | Version | Rule |
|---|---|---|---|
| `ueId`, `asId`, `uePorts`, `asPorts`, `qos` | request | v0.8.1 | renamed / restructured to server form; `ipv4addr` is a string, so the port cannot be carried |
| `device.ipv4Address.publicPort` (newly_required) | request | v0.8.1 | in `missing_info` (source `intent_text`) for IPv4 intents |
| `notificationUrl` | request | v0.8.1 | the callback is `<notificationUrl>/notifications`; the gold `sink` is the client's URL plus "/notifications" |
| `webhook.notificationUrl` | request | v0.9.0, v0.10.0 | native `webhook{notificationUrl}`; the gold `sink` is the same URL (the old renderer used `sink` here) |
| `sink` | request | v0.11.0, v1.0.0 | same field as at the server; checked field by field against v1.1.0 |
| `id`, `startedAt`/`expiresAt` Unix | response | v0.8.1 | `sessionId` becomes `id`; times in Unix seconds; no `qosStatus`; the answer does not echo the URL |
| `sessionId`, `webhook{notificationUrl}`, Unix times, `qosStatus` | response | v0.9.0, v0.10.0 | `webhook` instead of `sink` |
| `sink`, RFC 3339 times, `statusInfo` | response | v0.11.0 and later | as the server |
| delete (204) | response | all | `done` with `result: null` |
| gold profile | request | all | the native request has the intent's profile; the gold call differs only for m01/m11 (fact: use QOS_M for the full time) |

Native requests never contain `gold_profile`. `missing_info` for m01 and m11 is `qosProfile` (source `fact`).
