# Stage 03: protocol conformance (Stage 1 of the paper)

Status: **closed** (stage 03b, 2026-11-13). Nothing was reported to the NLIP projects: no issues, no pull requests. Petr passes the findings on through TC56 using `reports/deviations-for-maintainers.md`; Dinesh reviews the readings with `reports/review-readings-A1-A7.md`.

## What was done

1. **Standards.** Fetched ECMA-430 and ECMA-431 (1st edition, December 2025) from ecma-international.org and extracted the text with `pdftotext -raw`. Files and checksums are in `stage1/standards/` (`SHA256SUMS`):

   | File | SHA-256 |
   |---|---|
   | `ECMA-430_1st_edition_december_2025.pdf` | `3f14553a…62b5a` |
   | `ECMA-431_1st_edition_december_2025.pdf` | `4f4d0a0a…95393b` |

2. **Requirements.** `stage1/requirements.yaml` holds 58 requirements, each with the clause, the verbatim quote (a test checks the quote against the extracted text) and a testability class: yes 38, partly 8, no 12. Strength words: must 50, should 7, shall 1.
3. **Pinned implementations** (`stage1/IMPLEMENTATIONS.yaml`, installed by `stage1/setup.sh` into git-ignored `stage1/vendor/` and `stage1/venvs/`):

   | Implementation | Pinned commit |
   |---|---|
   | `nlip_sdk` 0.1.3 | `b3a6e845773af2c0c2b9e885abe8e4f6ab313dcc` |
   | `nlip_server` 0.1.3 | `acdbfc1a0dd1288675128ecc10c9809ec884f51e` |
   | examples (TypeScript client `nlip_client_pwa_ts`) | `a96488f9c849889cbab34123048834ed54c5558f` |

4. **Our implementation.** `nlipeval/nlip/{message,validate,transport}.py`, written from the standards only (25 tests in `tests/test_nlip.py`).
5. **Conformance suite.** 49 checks, C01–C49, in `stage1/tests/checks_def.py`; the harness is in `stage1/harness/`. Every requirement marked testable "yes" has at least one check (`tests/test_stage1_requirements.py`). Each implementation is driven through an adapter: `nlip_sdk` in-process, `nlip_server` over HTTP and TLS, the TypeScript client under Node with `fetch` redirected, ours in-process and over HTTP.
6. **Interoperability.** A 20-message script (M01–M20) between three clients and two servers (`stage1/harness/interop.py`).
7. **Results.** `results/stage1/conformance.csv` (one row per check and implementation), `conformance_detail.csv` (adds clause, group, title and reading), `interop.csv`, `interop_detail.csv`, `deviations.md` (raw evidence of the three deviations) and one log per check under `results/stage1/logs/`.

Rerun: `cd experiments && bash stage1/setup.sh && uv run python -m stage1.harness.run_suite && uv run python -m stage1.harness.interop && uv run python -m stage1.harness.deviations && uv run python -m stage1.harness.tables`.

## Table 1. Headline: checks that do not depend on an ambiguous reading

*Regenerated in stage 03b (decisions S2 and S3); the CSV files are unchanged.* The headline counts only the 32 checks that depend neither on an open reading of the standard nor on what the application built on the library does. The 17 flagged checks are in Table 1A. Cells show passed / applicable; "n/a" = the check does not apply to that implementation (for example, `nlip_sdk` is a library and has no HTTP end-point). Nothing is blocked.

**The headline for `nlip_server` uses the minimal application** (`stage1/apps/nlip_server_ack.py`, which answers "ok"), because that measures what the *library* guarantees. The last column uses the library's own example application (an echo application) and is explained in footnote 1.

| Clause group | Checks | `nlip_sdk` | `nlip_server` (minimal app) | TypeScript client | Our implementation | `nlip_server` with the library's own example application¹ |
| --- | ---: | --- | --- | --- | --- | --- |
| 5 Field names and values in any case | 3 | 1/3 | 1/3 | 1/2 | 3/3 | 1/3 |
| 5.1–5.2 Required and optional fields | 11 | 11/11 | 11/11 | 1/1 | 11/11 | 11/11 |
| 5.3 Formats and subformats | 6 | 4/6 | 3/4 | 2/3 | 6/6 | 3/4 |
| 6.1 Initial request answered with NLIP | 2 | n/a | 1/1 | 1/1 | 2/2 | 1/1 |
| 6.2 Token submessages returned unchanged | — | n/a | n/a | n/a | n/a | n/a |
| 6.2.1–6.2.2 Reserved token prefixes | 3 | 1/3 | n/a | n/a | 3/3 | n/a |
| 6.3 Control message answered with control | — | n/a | n/a | n/a | n/a | n/a |
| 6.4 Out-of-band transfer | 1 | n/a | n/a | 0/1 | 1/1 | n/a |
| 7 and ECMA-431 Transport and HTTP binding | 6 | n/a | 4/5 | 1/1 | 6/6 | 4/5 |
| **Total** | 32 | **17/23** | **20/24** | **6/9** | **32/32** | **20/24** |

¹ The echo application returns the request it receives. It therefore passes some token checks only because it echoes them, not because the library handles tokens. It is shown for comparison and is not part of the headline. On the unflagged checks it gives the same result as the minimal application (20/24).

The headline excludes only the checks flagged `ambiguous` or `application`. Some unflagged checks also rest on a reading, but one the standard supports with a reasonable reading: A3 (binary subformat, C18, C21, C48), A4 (language spelling, C20), A6 (rejecting a missing required field, C04–C06, C12–C14, C42). They are listed with their readings in `reports/review-readings-A1-A7.md`; if a reviewer rules differently, those counts change.

### Table 1A. Checks that depend on a reading or on the application

| Check | Depends on | `nlip_sdk` | `nlip_server` (minimal app) | TypeScript client | Our implementation | `nlip_server` with the library's own example application¹ | What it checks |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C15 | reading A2 | **fail** | **fail** | n/a | pass | **fail** | Content of type number, array, boolean and null is accepted and kept (Annex A, informative) |
| C49 | Annex A typing (informative) | n/a | **fail** | n/a | pass | **fail** | The server's answer is a valid NLIP message: no null where a field is optional (MessageType string, submessages array) |
| C16 | reading A7 | **fail** | **fail** | n/a | pass | **fail** | A format outside Table 1 is rejected (a first-level message with format 'error' or 'bogus') |
| C17 | reading A7 | **fail** | **fail** | n/a | pass | **fail** | A submessage with format 'error' is rejected |
| C22 | application behaviour | n/a | **fail** | n/a | pass | **fail** | A structured message in a programming language the end-point does not support is answered with a text message |
| C25 | application behaviour | n/a | **fail** | n/a | pass | pass | A conversation token sent in a submessage is returned with identical format, subformat and content |
| C26 | application behaviour | n/a | **fail** | n/a | pass | pass | An authentication token sent in a submessage is returned unchanged |
| C27 | application behaviour | n/a | **fail** | n/a | pass | pass | Several tokens sent at once (conversation, authentication, free subformat) are all returned unchanged |
| C28 | application behaviour | n/a | **fail** | n/a | pass | pass | A token in the first submessage (the message itself is a token) is returned |
| C29 | application behaviour | n/a | **fail** | n/a | pass | **fail** | Tokens sent with capitalised names and values are returned with the same content |
| C30 | application behaviour | n/a | n/a | n/a | pass | n/a | A token the end-point created itself (conversation token on a first request) is not an error and, if sent back, is returned |
| C46 | application behaviour | n/a | pass | n/a | pass | pass | A token with the bare subformat 'conversation' is returned unchanged |
| C34 | application behaviour | **fail** | **fail** | n/a | pass | pass | A token with subformat 'authentication_x' is found as the authentication token and returned unmodified |
| C35 | reading A1 + application behaviour | n/a | **fail** | n/a | pass | pass | A message with MessageType 'control' is answered with a message with MessageType 'control' |
| C36 | reading A1 | n/a | **fail** | n/a | pass | **fail** | A message with the field control=true is answered with a message with control=true |
| C38 | application behaviour | n/a | **fail** | n/a | pass | **fail** | A control request for large uploads is answered with a control message holding a structured/uri submessage |
| C39 | application behaviour | n/a | **fail** | n/a | pass | **fail** | The URI in the answer is a well-formed URL on a different port than the NLIP end-point |

Totals for the flagged checks and for all 49 checks:

| | `nlip_sdk` | `nlip_server` (minimal app) | TypeScript client | Our implementation | `nlip_server` with the library's own example application¹ |
| --- | --- | --- | --- | --- | --- |
| Flagged checks only (passed / applicable) | 0/4 | 1/16 | n/a | 17/17 | 7/16 |
| All 49 checks (passed / applicable) | 17/27 | 21/40 | 6/9 | 49/49 | 27/40 |

Outcomes in full, all 49 checks:

| Implementation | pass | fail | n/a | blocked |
| --- | ---: | ---: | ---: | ---: |
| `nlip_sdk` | 17 | 10 | 22 | 0 |
| `nlip_server` (minimal app) | 21 | 19 | 9 | 0 |
| `nlip_server` (own echo app) | 27 | 13 | 9 | 0 |
| TypeScript client | 6 | 3 | 40 | 0 |
| Our implementation | 49 | 0 | 0 | 0 |

The full per-check matrix (49 rows, with the requirement, reading and outcome for each implementation) can be printed with `uv run python -m stage1.harness.tables`; the evidence for every cell is in `results/stage1/logs/<implementation>/<check>.log` and in the `evidence` column of `conformance.csv`.

## Table 2. Interoperability

A fixed script of 20 messages (M01–M20; the list is in `interop_detail.csv`). Cells show messages that gave the expected exchange / 20. "Not built" means the client has no code that can produce the message; it is counted as not ok, and shown separately.

| Client ↓ · Server → | `nlip_server` (own echo app) | Our server (echo handler) |
| --- | --- | --- |
| `nlip_sdk` client | 16/20 (2 not built) | 18/20 (2 not built) |
| TypeScript example client | 4/20 (15 not built) | 4/20 (15 not built) |
| Our client | 17/20 | 20/20 |

Per message (ok / **fail** / not built). Columns: `nlip_sdk` client, TypeScript client and our client, each against `nlip_server` then against our server.

| Message | What | sdk→nlip_server | sdk→ours | ts→nlip_server | ts→ours | ours→nlip_server | ours→ours |
| --- | --- | --- | --- | --- | --- | --- | --- |
| M01 | text, English | ok | ok | ok | ok | ok | ok |
| M02 | text with non-ASCII characters | ok | ok | ok | ok | ok | ok |
| M03 | text, French subformat | ok | ok | not built | not built | ok | ok |
| M04 | structured/json, nested content | ok | ok | not built | not built | ok | ok |
| M05 | text with a binary (image) submessage | ok | ok | ok | **fail** | ok | ok |
| M06 | three submessages in order, with labels | ok | ok | not built | not built | ok | ok |
| M07 | conversation token | ok | ok | not built | not built | ok | ok |
| M08 | authentication token | ok | ok | not built | not built | ok | ok |
| M09 | conversation and authentication token together | ok | ok | not built | not built | ok | ok |
| M10 | token with a free subformat | ok | ok | not built | not built | ok | ok |
| M11 | conversation, turn 1 | ok | ok | not built | not built | ok | ok |
| M12 | conversation, turn 2 (same token) | ok | ok | not built | not built | ok | ok |
| M13 | conversation, turn 3 (same token) | ok | ok | not built | not built | ok | ok |
| M14 | control message (MessageType control) | ok | ok | not built | not built | ok | ok |
| M15 | control request for an out-of-band upload end-point | **fail** | ok | not built | not built | **fail** | ok |
| M16 | control message (field `control: true`) | not built | not built | **fail** | ok | **fail** | ok |
| M17 | error case: a message without content | not built | not built | not built | not built | ok | ok |
| M18 | structured message in COBOL | **fail** | ok | not built | not built | **fail** | ok |
| M19 | location/gps | ok | ok | not built | not built | ok | ok |
| M20 | text of 100 000 characters | ok | ok | ok | ok | ok | ok |

Notes:

- M05 (ts→ours): the TypeScript client sends the binary subformat `png`; our server rejects it with HTTP 400 (ECMA-430 5.3 needs `<content type>/<encoding>`, for example `image/png`).
- M16 (ts→nlip_server): the client sends `control: true`; the answer does not carry it back.
- The `nlip_sdk` client row uses the SDK's message model and the harness's `httpx`; the `nlip_client` package is not one of the three pinned repositories (see judgement calls).

## Confirmed deviations

All three were confirmed by direct calls against the pinned commits; every line of raw output is in `results/stage1/deviations.md`. They match the three marked † in `docs/expected-results-v2.md`.

### D1. `nlip_sdk` rejects capitalised field names

- **Requirement:** `E430-5-case-insensitive`, ECMA-430 clause 5: capitalisation is not relevant to the name or value of a field.
- **Evidence:** `NLIP_Message.model_validate({"format":"text","subformat":"English","content":"Hi"})` is accepted. `{"Format":…,"Subformat":…,"Content":…}` and the upper-case form are rejected with "3 validation errors … Field required". Values in any case (`"Text"`, `"ENGLISH"`) are accepted. `nlip_server` returns HTTP 422 for the capitalised message, because it uses the SDK's model.
- **Checks:** C01, C03 (fail in `nlip_sdk` and both `nlip_server` configurations).

### D2. `nlip_sdk` reserves `authorization`, not `authentication`

- **Requirement:** `E430-6.2.2-auth-reserved-prefix`, ECMA-430 6.2 and 6.2.2: the reserved subformat prefix is `authentication`.
- **Evidence:** `ReservedTokens.auth = 'authorization'`. `is_auth('authentication')` and `is_auth('authentication_x')` return False; `is_auth('authorization_x')` returns True. `add_authentication_token('tok123')` emits subformat `authorization`. `extract_authentication_token` does not find an `authentication_x` token.
- **Checks:** C31, C33, C34 (fail in `nlip_sdk`); C34 also fails in `nlip_server` with the minimal app.

### D3. `nlip_sdk` has a format `error` that is not in Table 1, and does not validate the first-level format

- **Requirement:** `E430-5.3-format-values`, ECMA-430 5.3 Table 1: the formats are text, token, structured, binary, location and generic.
- **Evidence:** `AllowedFormats` = text, token, structured, binary, location, **error**, generic. `NLIP_Factory.create_error_code('something failed')` builds `{"format":"error","subformat":"text",…}`. A first-level message with `format: bogus` is accepted. A submessage with format `error` is accepted.
- **Checks:** C16, C17 (both marked ambiguous, because 5.3 does not say a receiver must reject an unknown format), C47 (what the SDK builds: fail).

Other `nlip_sdk` observations (not counted as deviations):

- `add_token` with a non-reserved token type crashes with a `TypeError` (it calls `add_submessage(self, submsg)` with a wrong signature).
- Unknown fields (for example `control`) are dropped on a round trip.
- Content must be a string or an object. Number, array, boolean and null are rejected (C15, ambiguous; see A2).
- A binary subformat such as `document/pdf` is accepted (C21).

## Findings on `nlip_server`

`nlip_server` was run in two configurations, because most token and control checks depend on what the application does: a **minimal app** that answers "ok" (`stage1/apps/nlip_server_ack.py`), and the library's **own echo app**. The first measures the library alone, the second shows what a user gets with the example application.

1. **Control messages are not answered with a control message** (C35, C36; 6.3). Tested for both readings, `messagetype: control` and `control: true`. In the minimal app the answer is a plain text "ok". With the echo app, `messagetype: control` is returned only because the app returns its request; the `control: true` form is still lost (the field is dropped by the model).
2. **Tokens.** The server runs the request through `extract_conversation_token`, which matches only the subformat `conversation`. With the minimal app: `conversation` is returned (echoed with `force_change`); `conversation_abc`, `authentication_x`, `authorization_x` and `group_7` are dropped (C25–C29, C34). With the echo app all except those with capitalised names are returned, but only because the app echoes the request.
3. **`POST /nlip` returns HTTP 307 to `/nlip/`** (C41; ECMA-431 clause 6 defines `/nlip`). A client that does not follow redirects on POST fails.
4. **Null fields in answers** (C49): every response contains `"messagetype": null`, `"label": null` and `"submessages": null`. Under Annex A, an optional field is absent or has its type; null is not allowed. Our client needed a tolerant reader to parse these answers.
5. **Structured message in a language the end-point does not support** (C22, M18): the answer is structured (echoed), not text.
6. **No upload end-point.** There is no control or upload URI (C38, C39, M15).
7. **Capitalised field names** give HTTP 422 (D1).

On the positive side: valid messages are answered with NLIP (C23), invalid ones with 4xx (C42), the service works over HTTP/1.1 and TLS (C44, C45), and ordering of submessages is kept (C10).

## Findings on the TypeScript client (`nlip_client_pwa_ts`, `src/components/network.ts`)

The code runs unmodified under Node, with `fetch` redirected.

1. **It builds only three kinds of request:** a text request, an image request and a control-upload request. For 40 of 49 checks there is nothing to test (n/a), and 15 of 20 interop messages cannot be built.
2. **The control request is a `control: true` field**, not `MessageType: control` (C37 fail; see A1 for the reading).
3. **The image request uses the binary subformat `png`**, not `image/png` (C48 fail, M05 against our server). Clause 5.3 requires `<audio|image|sensor|generic>/<encoding>`.
4. **The server address is hard-coded** (`https://druid.eecs.umich.edu/nlip/`). The harness redirects the call to the target.
5. **The response reader reads only lowercase field names** (C01: 1/2).
6. It posts JSON with Content-Type `application/json` to the end-point (C43 pass).

## Ambiguities in the standard

Recorded in `stage1/requirements.yaml`; the checks that depend on them carry `reading: ambiguous`.

- **A1. Control: field or message type?** 5.1.1 defines `MessageType` with the value `control`; 6.3 and 6.4 speak of a "control field". Our implementation accepts both and answers a `MessageType: control` message with `MessageType: control` (C35). C36 tests the other reading. The TypeScript client uses the field reading.
- **A2. Content types.** Table 1 describes content as strings; Annex A allows more JSON types (number, array, boolean, null). C15 follows Annex A (informative).
- **A3. Binary subformat example.** The example `video/.mp3` contradicts the list of content types (audio, image, sensor, generic).
- **A4. Language spelling.** The text subformat carries a language, but the spelling (English, en, en-US) is not defined.
- **A5. `submessages`.** "One or more" in the text, versus an empty array being valid in the schema.
- **A6. Missing required field.** The standard does not say what a receiver does when a required field is missing; the checks (C04–C06, C12–C14) take "reject" as the only sensible behaviour. ECMA-431 does not define status codes (see `E431-6-post`), so the checks accept any 4xx.
- **A7. Unknown format.** 5.3 lists the formats but does not say if an unknown one must be rejected (C16, C17).

## Judgement calls

1. **Readings and application dependence.** Checks marked `ambiguous` (C15, C16, C17, C36, C49) depend on an open reading; checks marked `application` (C22, C25–C29, C34, C35, C38, C39, C46) depend on the application built on the library. Since stage 03b they are left out of the headline (Table 1) and shown in Table 1A.
2. **Two `nlip_server` configurations.** The headline uses the minimal application (what the library guarantees); the library's own echo application is a footnote column (stage 03b, S2).
3. **49 checks, not 35–45.** I added checks where a requirement had two sides (for example, accepted and returned) rather than merge them. The coverage test accepts 35–50.
4. **The `nlip_sdk` client is driven through the harness's httpx**, not the `nlip_client` package, which is not one of the three pinned repositories. The result for the message model is not affected; the HTTP behaviour of that package is untested.
5. **`nlip_client_vite_ts` was not tested.** It is a second web client in the examples; I tested the PWA one only. See "Not tested" below.
6. **Tolerant reader in our client.** To read `nlip_server` answers (null optional fields) our client drops nulls before validation. A strict reader would count all `nlip_server` answers as invalid (C49). This is why our client reaches 17/20 against `nlip_server`.
7. **Our implementation is not independent in the strict sense.** It was written by the same author (me) as the checks, so 49/49 shows that the suite and the implementation agree, not that the reading is correct. The ambiguous checks are where that matters most.
8. **TLS.** Checks on TLS use a throw-away self-signed certificate made by the harness; the certificate is not committed.
9. **`python-multipart` is not installed**, so the upload stand-in in our server reads the raw body.

## Difference from the mock Table 1 in `docs/expected-results-v2.md`

The mock had 40 checks and 17/21 for the SDK, with the three † deviations. The real suite has 49 checks. The three deviations are confirmed, but the numbers differ: the SDK passes 17 of 27 applicable checks (17 of 23 without the ambiguous ones), `nlip_server` passes 21 or 27 of 40 depending on the application, and the TypeScript client can be tested on only 9 checks, not 29. The group "6.2.2 Reserved token prefixes" became "6.2.1–6.2.2" (4 checks). **The mock's numbers must not be quoted; use Table 1 above.**

## Not tested (decision S4)

- **`nlip_client_vite_ts`**, the second TypeScript client in the examples repository: not tested. Only `nlip_client_pwa_ts` was. Reason: it would add little to the findings, and time matters more (Petr's decision S4).
- **The `nlip_client` package** (the Python HTTP client): not tested, and not one of the three pinned repositories. The `nlip_sdk` client row in Table 2 uses the SDK's message model with the harness's `httpx`, so the HTTP behaviour of `nlip_client` is unknown.

The paper should mention both as untested.

## Decisions taken after review (stage 03b)

| Question in the first version | Decision | Where it went |
|---|---|---|
| How to report the deviations? | S1: tell the NLIP maintainers through TC56, and say in the paper that they were found at the pinned commits and reported. Nothing is sent by the harness or by Bob. | `reports/deviations-for-maintainers.md` |
| Which `nlip_server` configuration in the paper table? | S2: the minimal application; the echo application is a footnote. | Table 1 above |
| Do the ambiguous checks count in the headline? | S3: no. Headline `nlip_sdk` 17/23, `nlip_server` 20/24, TypeScript client 6/9. The readings A1–A7 are reported as a separate finding about the standard. | Tables 1 and 1A |
| Also test `nlip_client_vite_ts` and `nlip_client`? | S4: not now. | "Not tested" above |
| Our implementation was written by us | S5: Dinesh reviews readings A1–A7. | `reports/review-readings-A1-A7.md` |
