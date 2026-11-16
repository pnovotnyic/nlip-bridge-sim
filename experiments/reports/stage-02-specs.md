# Stage 02: pinned specifications, breaking changes and change catalogue

Status: **done, catalogue is a DRAFT awaiting Petr's review** (2026-11-13).

## What was done

1. Pinned all 14 API versions plus the QoS Profiles file (15 files) at their release tags: `specs/<api>/<version>.yaml`, with `specs/MANIFEST.yaml` (repository, tag, path, commit SHA, SHA-256, licence). All 15 validate as OpenAPI 3.0.3 (`openapi-spec-validator`).
2. Counted breaking changes with `oasdiff` 1.33.0 (version asserted in code): `results/specs/breaking_changes.csv`.
3. Computed `breaking_crossed` for every (API, client version): `results/specs/breaking_crossed.csv`.
4. Generated resolved interface excerpts: `specs/excerpts/<api>/<version>.yaml`, sizes in `results/specs/excerpt_sizes.csv`.
5. Wrote the change catalogue `specs/changes/{L1,L2,L3}.yaml` and the reader `nlipeval/tasks/changes.py`.
6. Tests: `tests/test_specs_catalogue.py` (22 tests in the suite pass; 5 live tests deselected).

Code: `nlipeval/tasks/specs.py` (fetch, diff, excerpts) and `nlipeval/tasks/build_catalogue.py` (catalogue). Rebuild with `uv run python -m nlipeval.tasks.specs all && uv run python -m nlipeval.tasks.build_catalogue`.

## Versions pinned

| API | Version | Repo tag | File | Commit | SHA-256 (first 12) |
|---|---|---|---|---|---|
| L1 | v0.5.1 | DeviceStatus `v0.5.1` | `device-status.yaml` | `5628f9a859` | `7fa4e4943b25` |
| L1 | v0.6.0 | DeviceStatus `r1.2` | `device-reachability-status.yaml` | `9911d1aeea` | `9ecd700f9e6c` |
| L1 | v1.0.0 | DeviceStatus `r2.2` | `device-reachability-status.yaml` | `555e31fa6d` | `1e2d02aca243` |
| L2 | v0.1.0 | DeviceLocation `v0.1.0` | `location.yaml` | `78a819477d` | `d08198648d61` |
| L2 | v0.2.0 | DeviceLocation `v0.2.0` | `location-verification.yaml` | `81278ecdbb` | `39dcc1ca8515` |
| L2 | v1.0.0 | DeviceLocation `r1.2` | `location-verification.yaml` | `1be9b2a3ec` | `e0f26c89845f` |
| L2 | v2.0.0 | DeviceLocation `r2.2` | `location-verification.yaml` | `33a646d81f` | `702f084fad36` |
| L2 | v3.0.0 | DeviceLocation `r3.2` | `location-verification.yaml` | `bc17ceeb4e` | `a48d9d7d916d` |
| L3 | v0.8.1 | QualityOnDemand `v0.8.1` | `qod-api.yaml` | `90e15efbe7` | `eda929770670` |
| L3 | v0.9.0 | QualityOnDemand `v0.9.0` | `qod-api.yaml` | `ce226d5446` | `e5fbb702900f` |
| L3 | v0.10.0 | QualityOnDemand `v0.10.0` | `qod-api.yaml` | `9d72c4b576` | `4e9f5d967f29` |
| L3 | v0.11.0 | QualityOnDemand `r1.2` | `quality-on-demand.yaml` | `2f7706b453` | `a2ea805f344c` |
| L3 | v1.0.0 | QualityOnDemand `r2.2` | `quality-on-demand.yaml` | `8f3edd5f40` | `5b677a658143` |
| L3 | v1.1.0 | QualityOnDemand `r3.2` | `quality-on-demand.yaml` | `9cb179fd3b` | `b50893bacfee` |
| L3 | v1.1.0 (QoS Profiles) | QualityOnDemand `r3.2` | `qos-profiles.yaml` | `9cb179fd3b` | `12d7130e6342` |

Full values are in `specs/MANIFEST.yaml`. The `info.version` of every file equals the version in the table (asserted in code). Notes:

- **L1 v0.5.1** is the combined `device-status.yaml` (connectivity + roaming + subscriptions). v0.6.0 and v1.0.0 are the separate `device-reachability-status.yaml`. The first L1 step is therefore partly an API split.
- **L3 v0.8.1 to v0.10.0** come from the `qod-api.yaml` file at tags `v0.8.1`, `v0.9.0`, `v0.10.0`; from v0.11.0 on the file is `quality-on-demand.yaml` (releases r1.2, r2.2, r3.2). The tag `v0.10.1` also exists; it is not used (not in the plan).
- At every release the QoS Profiles file is a separate API. Only the v1.1.0 one is pinned, as the plan says.

## Breaking changes (`oasdiff` 1.33.0)

| API | From | To | All changes | ERR (breaking) | WARN |
|---|---|---|---|---|---|
| L1 | v0.5.1 | v0.6.0 | 38 | 6 | 0 |
| L1 | v0.6.0 | v1.0.0 | 46 | 2 | 28 |
| L2 | v0.1.0 | v0.2.0 | 33 | 7 | 5 |
| L2 | v0.2.0 | v1.0.0 | 13 | 0 | 1 |
| L2 | v1.0.0 | v2.0.0 | 29 | 1 | 20 |
| L2 | v2.0.0 | v3.0.0 | 6 | 0 | 2 |
| L3 | v0.8.1 | v0.9.0 | 82 | 4 | 15 |
| L3 | v0.9.0 | v0.10.0 | 67 | 2 | 11 |
| L3 | v0.10.0 | v0.11.0 | 103 | 10 | 23 |
| L3 | v0.11.0 | v1.0.0 | 165 | 5 | 121 |
| L3 | v1.0.0 | v1.1.0 | 33 | 0 | 14 |

**Comparison with the earlier run.** ERR counts match exactly: L1 6, 2; L2 7, 0, 1, 0; L3 4, 2, 10, 5, 0 (a test asserts this). Nothing was adjusted.

**What the ERR counts contain (worth knowing).**

- Most ERR items are whole-API, not about the fields the tasks use. L1 v0.5.1 to v0.6.0 (6 ERR) is the removal of the combined API's `/connectivity`, `/roaming` and `/subscriptions*` paths. L2 v1.0.0 to v2.0.0 (1 ERR) is only an added pattern on the `x-correlator` header. The ERR count is therefore an approximate measure of the breaking changes that matter for the tasks.
- The catalogue (below) is the field-level measure. Figure 3 uses `breaking_crossed`, Figure 4 uses the catalogue.

`breaking_crossed` (client version to server version), from `results/specs/breaking_crossed.csv`:

| API | Client version (versions behind: crossed) |
|---|---|
| L1 | v0.5.1 (2: 8), v0.6.0 (1: 2), v1.0.0 (0: 0) |
| L2 | v0.1.0 (4: 8), v0.2.0 (3: 1), v1.0.0 (2: 1), v2.0.0 (1: 0), v3.0.0 (0: 0) |
| L3 | v0.8.1 (5: 21), v0.9.0 (4: 17), v0.10.0 (3: 15), v0.11.0 (2: 5), v1.0.0 (1: 0), v1.1.0 (0: 0) |

**Consequence for Stage 3.** Several steps carry no ERR (L2 one and three versions behind has 0 and 1; L3 one behind has 0). A "versions behind" axis and a "breaking changes crossed" axis are therefore not interchangeable, which Figure 3 is designed to show.

### Comparison of the three breaking-change measures

To support the analysis in Figure 3, we have three different measures of breaking changes side by side, per (API, client version):
- **Whole API (`breaking_crossed`)**: Sum of all ERR-level `oasdiff` breaking changes across the entire specification between the client and server versions.
- **Operations used (`breaking_crossed_ops`)**: The same count, but restricted specifically to the endpoints and operations used by our task suite (using `oasdiff --match-path`).
- **Catalogue (`catalogue_breaking_crossed`)**: Fine-grained, field-level and value-level count of entries in our change catalogue that carry a breaking change kind (`renamed`, `restructured`, `unit_format`, `newly_required`, `changed_meaning`, or `removed`).

| API | Client version | Versions behind | Whole API (`breaking_crossed`) | Operations used (`breaking_crossed_ops`) | Catalogue (`catalogue_breaking_crossed`) |
|---|---|---|---|---|---|
| L1 | v0.5.1 | 2 | 8 | 3 | 4 |
| L1 | v0.6.0 | 1 | 2 | 2 | 2 |
| L1 | v1.0.0 | 0 | 0 | 0 | 0 |
| L2 | v0.1.0 | 4 | 8 | 8 | 13 |
| L2 | v0.2.0 | 3 | 1 | 1 | 3 |
| L2 | v1.0.0 | 2 | 1 | 1 | 2 |
| L2 | v2.0.0 | 1 | 0 | 0 | 2 |
| L2 | v3.0.0 | 0 | 0 | 0 | 0 |
| L3 | v0.8.1 | 5 | 21 | 14 | 45 |
| L3 | v0.9.0 | 4 | 17 | 11 | 13 |
| L3 | v0.10.0 | 3 | 15 | 9 | 13 |
| L3 | v0.11.0 | 2 | 5 | 3 | 2 |
| L3 | v1.0.0 | 1 | 0 | 0 | 2 |
| L3 | v1.1.0 | 0 | 0 | 0 | 0 |

#### Where they disagree, and why

1. **Whole API vs. Operations used**: Whole API counts are always greater than or equal to operations used. This is because `breaking_crossed` counts breaking changes across paths and features that our tasks do not touch (e.g., L1's removal of `/roaming` and `/subscriptions*` paths at v0.6.0).
2. **Operations used vs. Catalogue**:
   - **Catalogue tracks fine-grained, field-level details**: For L3 v0.8.1, the catalogue count (45) is significantly higher than the operations-used count (14). This is because a single parent change in `oasdiff` (like the restructure of `ueId` to `device`) resolves to many fine-grained field-level entries in the catalogue (e.g., `device.phoneNumber`, `device.ipv4Address`, etc.), each of which is verified and counted separately.
   - **Catalogue handles operation renames where `oasdiff` fails**: For L1 v0.5.1, the operation was renamed from `POST /connectivity` to `POST /retrieve`. Since the path changed completely, `oasdiff`'s per-operation counts cannot compare the sub-schemas across versions (as the old path is deleted and a new one is added). The catalogue explicitly maps the lineage of the fields across the rename, tracking changes (like `connectivityStatus` to `reachabilityStatus` restructure/rename) that `oasdiff`'s path-matching filters miss.
   - **Catalogue captures semantic value-level breaking changes**: For L2 v2.0.0, `oasdiff` shows 0 breaking changes on the used paths, but the catalogue shows 2. This is because the catalogue records semantic breaking changes (such as the value-level change of removing `UNKNOWN` from `verificationResult` at v3.0.0, or `lastLocationTime` becoming newly required) which `oasdiff`'s structural schema checks either miss or classify differently.

## Excerpts

Each excerpt keeps only the operations the tasks use, with every `$ref` resolved and all descriptions kept (YAML):

- L1: retrieve reachability (`POST /connectivity` at v0.5.1, `POST /retrieve` later);
- L2: `POST /verify`;
- L3: create (`POST /sessions`), get and delete (`/sessions/{sessionId}`); no extend, no `retrieve-sessions`;
- L3 QoS Profiles at v1.1.0: `retrieve-qos-profiles` and `qos-profiles/{name}`, stored as `specs/excerpts/L3/qos-profiles-v1.1.0.yaml` (separately, because only the server agent needs it).

Callbacks and security schemes are dropped. Discriminated sub-schemas (for example L2's `Circle` area and L3's credential types) are inlined under `x-discriminator-subtypes`, because otherwise they would be lost: OpenAPI discriminator mappings are plain strings.

Sizes (characters; tokens are approximate, chars / 4):

| API | v (oldest) | ... | current |
|---|---|---|---|
| L1 | v0.5.1: 11k chars, 2.9k tok | v0.6.0: 25.8k, 6.5k | v1.0.0: 22.1k, 5.5k |
| L2 | v0.1.0: 8.2k, 2.0k | v1.0.0: 28.6k, 7.1k | v3.0.0: 34.8k, 8.7k |
| L3 | v0.8.1: 43.0k, 10.7k | v0.11.0: 105.8k, 26.4k | v1.1.0: 118.3k, 29.6k |
| L3 QoS Profiles | | | v1.1.0: 84.9k, 21.2k |

**Context window for R1 (resolved).**

- chars / 4 over-estimated. Measured with R1's own tokenizer, the L3 v1.1.0 excerpt is 20,705 tokens and the QoS Profiles excerpt is 14,372. Together they are about 35k, which does not fit R1's former 32,768 window once the prompt and output are added.
- Petr confirmed there is memory, so R1's `num_ctx` is now **65536** (`config/Modelfile.qwen3-4b-nlip`, `config/models.yaml`). The derived model `nlip-qwen3-4b` was rebuilt; `ollama ps` shows context 65536, 12 GB, 100% GPU. R1 smoke tests 1-4 were re-run and pass.
- R2 to R5 have 131k to 200k contexts, so they are not affected. The excerpts are unchanged, with all descriptions kept.

## Change catalogue (DRAFT)

`specs/changes/<api>.yaml`: for each client version, one entry per field (and per operation or path parameter where it changed) with `client_path`, `server_path` (null if absent), `direction`, `kind` (the most disruptive kind), `kinds` (all kinds crossed), `note`, `evidence`, and `operations`. Marked `status: draft`.

**How evidence is checked.** The catalogue is generated, not hand-written per version: each field's lineage is authored once, as events between consecutive versions, and the generator derives all client-versus-server entries. While building, the generator asserts that:

- every path claimed at the client and server version resolves in that version's OpenAPI file (the line number is recorded in the evidence);
- a path claimed absent is not in the spec;
- every evidence item (an `oasdiff changelog` line or a literal spec line) is found, and is cited with its line number;
- every differing client/server path is explained by an event.

Any mismatch raises an error, so the catalogue cannot contain unverified claims. Entry counts: L1 11, L2 16 to 17, L3 46 to 47 per client version. No entry lacks evidence (tested).

**Entries per kind** (primary kind per entry; request and response entries together):

| API | Client v | Behind | Entries | renamed | restructured | unit_format | newly_required | changed_meaning | removed | added_optional | unchanged |
|---|---|---|---|---|---|---|---|---|---|---|---|
| L1 | v0.5.1 | 2 | 11 | 1 | 2 | 1 | 0 | 0 | 0 | 1 | 6 |
| L1 | v0.6.0 | 1 | 11 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 9 |
| L2 | v0.1.0 | 4 | 16 | 2 | 6 | 1 | 3 | 1 | 0 | 3 | 0 |
| L2 | v0.2.0 | 3 | 17 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 13 |
| L2 | v1.0.0 | 2 | 17 | 0 | 0 | 0 | 1 | 1 | 0 | 1 | 14 |
| L2 | v2.0.0 | 1 | 17 | 0 | 0 | 0 | 1 | 1 | 0 | 1 | 14 |
| L3 | v0.8.1 | 5 | 47 | 23 | 5 | 6 | 8 | 2 | 1 | 1 | 1 |
| L3 | v0.9.0 | 4 | 47 | 0 | 3 | 4 | 5 | 0 | 1 | 1 | 33 |
| L3 | v0.10.0 | 3 | 47 | 0 | 3 | 4 | 5 | 0 | 1 | 1 | 33 |
| L3 | v0.11.0 | 2 | 46 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 44 |
| L3 | v1.0.0 | 1 | 46 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 44 |

The server-version rows (0 versions behind) are all `unchanged` and are omitted above. A client's primary kind hides the other kinds crossed; the reader uses all `kinds`.

**The plan's known examples, checked against the files.** All were confirmed by the specs unless noted.

- **L3**
  - `ueId` to `device`, `asId` to `applicationServer`, `qos` (enum) to `qosProfile` (string), and `uePorts` / `asPorts` to `devicePorts` / `applicationServerPorts`: confirmed (v0.8.1 to v0.9.0).
  - `notificationUrl` / `notificationAuthToken` to `webhook.*` (v0.9.0) to `sink` / `sinkCredential` (v0.11.0): confirmed.
    - **Meaning of the URL changed: `changed_meaning`.** In v0.8.1 the callback is `{$request.body#/notificationUrl}/notifications`, so the value is a base URL and `/notifications` is appended. From v0.9.0 the callback is the URL exactly as given. The v0.8.1 spec has an explicit `/notifications` path to show this. The event payload also changes (SESSION_TERMINATED to QOS_STATUS_CHANGED, then CloudEvents); that part is outside the request fields and is only noted.
    - Also at v1.1.0: `sink` must match `^https://.+$`.
  - `duration` becomes required at v0.11.0: confirmed. It also loses its default and its maximum of 86400.
  - Device IPv4: needs `publicAddress` plus `privateAddress` or `publicPort` from **v0.9.0** (confirmed); v0.8.1's `ueId.ipv4addr` allowed an address/mask form.
  - `id` to `sessionId` (v0.9.0): confirmed.
  - `startedAt` / `expiresAt` Unix seconds to date-time: confirmed at v0.11.0 (the plan did not give the version).
- **L2**
  - Latitude, longitude and accuracy (km) become an area with a centre and a radius in metres: confirmed (v0.1.0 to v0.2.0). `accuracy` to `radius` is tagged `restructured`, `unit_format` and `changed_meaning`, since the circle now defines the verified region.
  - Boolean to TRUE / FALSE / PARTIAL / UNKNOWN with a `matchRate`: confirmed (v0.2.0).
  - UNKNOWN is removed at v3.0.0, with the case becoming error 422 `LOCATION_VERIFICATION.UNABLE_TO_LOCATE`: confirmed.
  - `lastLocationTime` becomes required at v3.0.0: confirmed.
- **L1**
  - Path `/connectivity` to `/retrieve`: confirmed (v0.6.0).
  - `connectivityStatus` to `reachabilityStatus` (v0.6.0): confirmed.
  - `reachable` plus a `connectivity` list at v1.0.0: confirmed. Tagged `restructured` and `changed_meaning`, because three values collapse into a boolean and a list.

**Reader.** `nlipeval.tasks.changes.change_tags(api, client_version, operation, request_fields, response_fields)` returns `{"request": [...], "response": [...]}` using the six tag kinds of the data contract (`unchanged` and `added_optional` are not tags). A used object path selects all its members; a field with no entry raises `KeyError`, so a task can never be silently tagged as unchanged. `entries(...)` returns the raw entries.

## Deviations and judgement calls

1. **Catalogue is generated from authored lineage,** not typed per version. This keeps request and response entries consistent and lets every claim be machine-checked; the cost is that the lineage in `build_catalogue.py` is the thing to review.
2. **Response entries for echoed fields** (L3 `getSession` and `createSession` responses) reuse the request lineage and say so in the note.
3. **Value-level entry for L2 UNKNOWN.** The plan lists the `UNKNOWN` removal as a change; it is a value, not a field, so it has its own entry `verificationResult=UNKNOWN`. The `verificationResult` entry itself stays `unchanged` from v2.0.0.
4. **Relaxations are recorded but carry no tag** (for example `device` becoming optional, L1 and L2 `device`, `maxAge` minimum removed), because the plan's kinds have no "relaxed" kind.
5. **Only the operations the tasks use** are in the catalogue. Subscriptions, roaming, geofencing, `extend` and `retrieve-sessions` are not.

## Questions for Petr

1. **Catalogue review.** Please review `specs/changes/*.yaml`, especially: (i) the `changed_meaning` tags (L3 `notificationUrl`, L2 `accuracy` to `radius`, L1 `reachable`); (ii) whether `accuracy` to `radius` should also be `unit_format` (km to m) as well as `restructured`; (iii) the choice not to tag relaxations.
2. **Tag by every kind or by the hardest kind?** The reader returns every kind crossed (a client one step behind can have several). The handoff lists "tag by hardest kind" as an open question; I kept every kind so either analysis is possible.
3. **L3 `v0.10.1`.** A patch tag exists between v0.10.0 and r1.2; the plan skips it. Confirm that v0.10.0 is right.

## Files

- `specs/MANIFEST.yaml`, `specs/L1|L2|L3/*.yaml`, `specs/excerpts/**`, `specs/changes/{L1,L2,L3}.yaml`
- `results/specs/breaking_changes.csv`, `breaking_crossed.csv`, `excerpt_sizes.csv`
- `nlipeval/tasks/specs.py`, `nlipeval/tasks/build_catalogue.py`, `nlipeval/tasks/changes.py`
- `tests/test_specs_catalogue.py`
