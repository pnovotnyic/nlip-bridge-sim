# Deviations found in the NLIP reference code: summary for the NLIP maintainers

*Draft for Petr to pass on through TC56. Nothing has been sent, and no issue or pull request has been opened.*

**What was tested.** The reference code was checked against the requirements of ECMA-430 (NLIP, 1st edition, December 2025) and ECMA-431 (HTTP binding). The findings below are those the checks confirmed by a direct call. Raw output for each is in `experiments/results/stage1/deviations.md`; the checks are in `experiments/stage1/tests/checks_def.py` (cited as C01 to C49). The requirement text is quoted from the standard as extracted in `experiments/stage1/standards/`.

**Pinned commits.**

| Code | Repository | Commit | Version |
|---|---|---|---|
| `nlip_sdk` | `nlip-project/nlip_sdk` | `b3a6e845773af2c0c2b9e885abe8e4f6ab313dcc` | 0.1.3 |
| `nlip_server` | `nlip-project/nlip_server` | `acdbfc1a0dd1288675128ecc10c9809ec884f51e` | 0.1.3 |
| TypeScript PWA client | `nlip-project/examples`, `nlip_client_pwa_ts` | `a96488f9c849889cbab34123048834ed54c5558f` | n/a |

**How to run a reproduction.** Install the pinned commit (`bash experiments/stage1/setup.sh` does it into `experiments/stage1/venvs/`). The `nlip_server` snippets use the application below, which answers every message with the text "ok" so that only the library's own behaviour is seen:

```python
# app.py: run with `uvicorn app:app --port 8000`
from nlip_sdk.nlip import NLIP_Factory
from nlip_server.server import NLIP_Session, SafeApplication, setup_server

class S(NLIP_Session):
    def execute(self, msg): return NLIP_Factory.create_text("ok")
class A(SafeApplication):
    def create_session(self): return S()
app = setup_server(A())
```

Where a finding depends on a reading of the standard that is open, it says so. Seven such readings are listed in `reports/review-readings-A1-A7.md`.

---

## `nlip_sdk`

### D1. Capitalised field names are rejected

- **Requirement** (ECMA-430, clause 5, `E430-5-case-insensitive`): "Capitalization is not relevant to the name or value of the field."
- **Checks:** C01, C03 (fail in `nlip_sdk` and in `nlip_server`).
- **Reproduction** (`nlip_sdk` at the pinned commit):

  ```python
  from nlip_sdk.nlip import NLIP_Message
  NLIP_Message.model_validate({"format": "text", "subformat": "English", "content": "Hi"})   # accepted
  NLIP_Message.model_validate({"Format": "text", "Subformat": "English", "Content": "Hi"})   # ValidationError: 3 validation errors, "Field required"
  ```

- **Observed:** values in any case (`"Text"`, `"ENGLISH"`) are accepted; field names in any case other than lowercase are not. Because `nlip_server` uses the SDK's model, it answers HTTP 422 to a capitalised message.
- **Reading dependence:** none. The sentence applies to "the name" of a field.

### D2. The reserved token prefix is `authorization`, not `authentication`

- **Requirement** (ECMA-430, 5.3 Table 1 and 6.2.2, `E430-6.2.2-auth-reserved-prefix`): Table 1 says "Two prefixes are reserved namely 'authentication' and 'conversation'"; 6.2.2: "A submessage with format 'token' and subformat beginning with 'authentication' is intended to exchange authentication credentials with communicating end-points."
- **Checks:** C31, C33, C34 (fail in `nlip_sdk`; C34 also fails in `nlip_server`).
- **Reproduction:**

  ```python
  from nlip_sdk.nlip import NLIP_Factory, ReservedTokens
  ReservedTokens.auth.value                     # 'authorization'
  m = NLIP_Factory.create_text("hello"); m.add_authentication_token("tok123")
  m.submessages[0].subformat                    # 'authorization'  (the standard says 'authentication')
  ```

  `is_auth('authentication')` and `is_auth('authentication_x')` return False; `is_auth('authorization_x')` returns True.
- **Reading dependence:** none. Table 1 and 6.2.2 both use the word "authentication".

### D3. A format `error` that is not in Table 1; the first-level format is not checked

- **Requirement** (ECMA-430, 5.3, `E430-5.3-format-values`): "The format field must have one of the values described in Table 1", which lists text, token, structured, binary, location and generic.
- **Checks:** C47 (what the SDK builds: fail); C16 and C17 (what the SDK accepts: fail, but these two depend on a reading, see below).
- **Reproduction:**

  ```python
  from nlip_sdk.nlip import NLIP_Factory, NLIP_Message, AllowedFormats
  [f.value for f in AllowedFormats]   # ['text','token','structured','binary','location','error','generic']
  NLIP_Factory.create_error_code("x").model_dump(exclude_none=True)   # {'format': 'error', 'subformat': 'text', 'content': 'x'}
  NLIP_Message.model_validate({"format": "bogus", "subformat": "text", "content": "x"})   # accepted
  ```

- **Reading dependence:** the sender side (the SDK builds a message with format `error`) is a direct reading of the sentence. Whether a receiver must *reject* an unknown format is not said (reading A7).

### Other `nlip_sdk` observations (not counted as deviations)

- `add_token` with a token type that is not reserved raises a `TypeError`: it calls `add_submessage(self, submsg)` with the wrong signature.
- Unknown fields (for example `control`) are dropped on a round trip.
- Content must be a string or an object; number, array, boolean and null are rejected (C15; Annex A is informative; reading A2).

---

## `nlip_server`

All reproductions use the application above.

### S-1. A control message is not answered with a control message

- **Requirement** (ECMA-430, 6.3, `E430-6.3-control-response`): "If a NLIP end-point receives a message which has the control field set to true, it must respond with a NLIP Message with control field set to true."
- **Checks:** C35 (MessageType `control`) and C36 (field `control: true`); both fail with the minimal application.
- **Reproduction:**

  ```
  POST /nlip/  {"format":"text","subformat":"English","content":"q","messagetype":"control"}
  -> 200 {"messagetype":null,"format":"text","subformat":"english","content":"ok","label":null,"submessages":null}
  POST /nlip/  {"format":"text","subformat":"English","content":"q","control":true}
  -> 200 (the same body; the field `control` is dropped by the model)
  ```

- **Reading dependence:** yes, reading A1. Clause 6.3 speaks of a "control field", while 5.1.1 defines `control` as a value of MessageType. Both forms were tested, and neither is answered as control. With the library's echo application the MessageType form comes back only because the application returns its request.

### S-2. Token submessages are not returned (only the subformat `conversation` is)

- **Requirement** (ECMA-430, 6.2, `E430-6.2-token-echo`): "the end-point must include the same submessage with the exact same format, subformat and content in its response message to the peer end-point, except when the token was initially created by the end-point." Also 6.2.2, `E430-6.2.2-auth-return-unmodified`: "The other end-point is obligated to return the authentication token unmodified".
- **Checks:** C25 to C29, C34 (fail with the minimal application); C46 passes.
- **Reproduction:**

  ```
  POST /nlip/ {..., "submessages":[{"format":"token","subformat":"conversation","content":"t1"}]}      -> token returned
  POST /nlip/ {..., "submessages":[{"format":"token","subformat":"conversation_abc","content":"t1"}]}   -> "submessages": null
  POST /nlip/ {..., "submessages":[{"format":"token","subformat":"authentication_x","content":"t1"}]}   -> "submessages": null
  ```

  The server runs the request through `extract_conversation_token`, which matches the bare subformat only.
- **Reading dependence:** partly. Whether *the library* or *the application* is responsible for returning tokens is not stated; the checks are flagged `application`. With the library's echo application most of them pass, because it returns the whole request.

### S-3. `POST /nlip` answers with HTTP 307 to `/nlip/`

- **Requirement** (ECMA-431, clause 6, `E431-6-url-path`): "This end-point would be accessible using a URL defined as https://<server_name>:port/nlip."
- **Check:** C41 (fail).
- **Reproduction:**

  ```
  POST /nlip  {valid message}   -> 307, Location: http://<host>/nlip/
  ```

  A client that does not follow redirects on POST fails; the TypeScript client posts to `/nlip/` and so avoids it.
- **Reading dependence:** none for the path; a redirect is allowed by HTTP, but it is not mentioned in the binding.

### S-4. Optional fields are returned as `null`

- **Requirement** (ECMA-430, 5.1.1, `E430-5.1.1-messagetype-string`): "Its value must be a string as defined by ECMA-404"; 5.1.5: when present, `submessages` "must be represented as a array". Annex A (informative) types them the same way.
- **Check:** C49 (fail).
- **Reproduction:** every answer in the reproductions above contains `"messagetype": null, "label": null, "submessages": null`.
- **Reading dependence:** yes. Annex A is informative and says nothing about null; a tolerant receiver may accept null for an absent field. Our own client needed a tolerant reader (it drops nulls before validation).

### Also observed

- Capitalised field names give HTTP 422 (D1).
- No control or upload URI is offered (C38, C39); a structured message in a language the end-point does not support is answered with a structured message, not text (C22; 5.3 says "should").

---

## TypeScript client (`nlip_client_pwa_ts`, `src/components/network.ts`)

The code was run unmodified under Node, with `fetch` redirected from the hard-coded server address to the test server.

### T-1. The control request uses a `control: true` field

- **Requirement** (ECMA-430, 6.4, `E430-6.4-request-control`): "This must be a message with the MessageType field set to 'control'."
- **Check:** C37 (fail). See reading A1.
- **Where:** `requestUploadUrl()`, `network.ts` lines 293-299: `{control: true, format: 'text', subformat: 'english', content: 'request_upload_url'}`.

### T-2. The image request uses the binary subformat `png` (also `jpeg`, `gif`, `bmp`)

- **Requirement** (ECMA-430, 5.3 Table 1, `E430-5.3-binary-content`): the binary subformat is `<content>/<encoding>`, where the content is audio, image, sensor or generic.
- **Check:** C48 (fail); interoperability message M05 against a server that enforces the rule gets HTTP 400.
- **Where:** `sendImageMessage()`, `network.ts` lines 232-263: `subformat: imageFormat`, which is `mimeType.split('/')[1]`, so `png` and not `image/png`.

### T-3. The response reader reads lowercase field names only

- **Requirement:** ECMA-430 clause 5 (see D1).
- **Check:** C01 (1 of 2). The code reads `data.format`, `data.subformat` and `data.content`.

### Other

- The server address is hard-coded (`https://druid.eecs.umich.edu/nlip/`).
- The client builds only three kinds of request (text, image, control upload); for 40 of the 49 checks there is nothing to test.

---

## Not tested

`nlip_client_vite_ts` (a second web client in the examples repository) and the `nlip_client` Python package were not tested.
