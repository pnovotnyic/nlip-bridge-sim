# Review of the readings A1–A7 of ECMA-430 / ECMA-431

*For Dinesh (TC56). About 30 minutes. Prepared in stage 03b (decision S5).*

**Why this review.** Our implementation of NLIP (`nlipeval/nlip/`) and the 49 conformance checks (`stage1/tests/checks_def.py`) were written by the same author, from the standards only. Our implementation passes 49/49, which shows that the checks and the implementation agree. It does not show that the reading of the standard is right. The seven places where the text allows more than one reading are the places where that matters.

**What to do.** For each ambiguity below, please fill in the last column: *agree* (our reading is the intended one), *other* (give the reading the committee intends), or *open* (the committee has not decided). If you rule differently, the checks listed for it must be changed, and the numbers in the paper move with them.

**Where the numbers sit.** The headline conformance table counts 32 checks. The 17 checks flagged `ambiguous` or `application` in the suite are shown apart (`reports/stage-03-conformance.md`, Table 1A). The checks below are marked: **flagged** (outside the headline) or *in the headline* (inside it, so a different ruling would change the headline).

Quotes are verbatim from `stage1/standards/ECMA-430.raw.txt`.

---

## A1. Control: a field, or a message type?

**Quoted text.**

- 5.1.1: "The value of 'control' is reserved and indicates a message that is used to negotiate control parameters."
- 6.3 (title "Requests containing control field"): "If a NLIP end-point receives a message which has the control field set to true, it must respond with a NLIP Message with control field set to true."
- 6.4: "This must be a message with the MessageType field set to 'control'".

**Readings possible.**

1. One mechanism: a message is a control message when `MessageType` is `control`. "The control field set to true" in 6.3 is loose wording for that.
2. Two mechanisms: `MessageType: control` (5.1.1 and 6.4) and a separate boolean field `control: true` (6.3). A first-level `control` field does not appear in 5.1.
3. One mechanism, the boolean field, and 5.1.1/6.4 are the loose ones.

**Reading used.** Reading 1 for the answer rule; both forms are *tested* (C35 for `MessageType`, C36 for the boolean), and our validator accepts the boolean field as an unknown field. Our server answers a `MessageType: control` message with `MessageType: control`. The request for an upload end-point (6.4) uses `MessageType`.

**Checks that depend on it.**

| Check | What it tests | Status |
|---|---|---|
| C35 | `MessageType: control` is answered with `MessageType: control` | flagged (also application-dependent) |
| C36 | `control: true` is answered with `control: true` | flagged |
| C37 | the client's upload request is a `MessageType: control` message | *in the headline* (fails for the TypeScript client, which sends `control: true`) |
| C38, C39 | the answer to the upload request is a control message with a `structured/uri` submessage | flagged (application-dependent) |

**Related finding.** `nlip_server` answers neither form with a control message (S-1 in `reports/deviations-for-maintainers.md`).

| Your verdict (agree / other / open) | Intended reading, if other |
|---|---|
| | |

---

## A2. Which JSON types may `content` have?

**Quoted text.**

- 5.1.4: "It must be represented as specified by the format and subformat field."
- Table 1 describes the content of text, token and location as text or a string, and structured content as `json, uri, xml, html` or code.
- Annex A (informative): `"Content": {"type": ["string", "number", "object", "array", "boolean", "null"]}`.

**Readings possible.**

1. Annex A is the type of `content` everywhere: any JSON value.
2. The format and subformat decide: a `text` message holds a string, `structured/json` holds any JSON value, and so on. Annex A is the union.

**Reading used.** Reading 1 for acceptance: the validator accepts every JSON type for `content` (C15). It does not check the type against the format.

**Checks that depend on it.** C15 (flagged: number, array, boolean and null are accepted and kept). C10 and C18 use nested JSON in `structured/json` content only, which both readings accept.

**Related finding.** `nlip_sdk` rejects content that is not a string or an object.

| Your verdict (agree / other / open) | Intended reading, if other |
|---|---|
| | |

---

## A3. The binary subformat

**Quoted text.** Table 1, `binary`, subformat `<content>/<encoding>`:

"The subformat field must have content as one of the values of audio, image, sensor, or generic. The encoding must be specific content encoding, e.g. bmp or jpeg for audio, mp3/mov for video etc. A sender may include a . as prefix for encoding. Valid values for subformat include are audio/bmp, audio/.bmp, video/.mp3, generic/.zip etc."

**The conflict.** The list of content types has no `video`, but the examples `video/.mp3` and "mp3/mov for video" use it. "bmp or jpeg for audio" looks like a slip, since both are image encodings. The set of valid encodings is not given.

**Readings possible.**

1. The four listed content types are the only ones allowed; `video/.mp3` is a slip.
2. The examples are right and `video` is allowed (perhaps the list is incomplete).
3. Any `<x>/<y>` form is allowed.

**Reading used.** Reading 1. The validator accepts `audio|image|sensor|generic` followed by `/` and an encoding (with an optional leading `.`), and rejects anything else (for example `document/pdf`). Any encoding is accepted.

**Checks that depend on it.** C21 (a content type outside the four is rejected), C48 (what an implementation builds has the form `<content>/<encoding>`), C18 (accepts `image/png` and `audio/.mp3`). All three are *in the headline*. A ruling for reading 2 or 3 would change C21 for every implementation (`nlip_sdk` currently accepts `document/pdf`, which fails C21 under reading 1).

| Your verdict (agree / other / open) | Intended reading, if other |
|---|---|
| | |

---

## A4. How the language is written in the `text` subformat

**Quoted text.**

- Table 1, `text`, subformat `<lang>`: "The subformat identifies the language that is being used for content."
- 5.3, last sentence: "All conforming end-points must support the processing of all fields, and support at least the text format field with the subformat of 'English'."
- Clause 5: "Capitalization is not relevant to the name or value of the field."

**Readings possible.**

1. The subformat is the English name of the language (`English`, `French`), compared without regard to case. A code such as `en` or `en-US` is a different value.
2. A language tag (`en`, `en-US`) is also, or only, valid.

**Reading used.** The subformat is any string, matched without regard to case; `English`, `english` and `ENGLISH` are all the same. We do not check the language name.

**Checks that depend on it.** C02 and C20 (`English` in three spellings is processed); both *in the headline*. A reading that excludes or adds code forms would not change them. M03 in the interoperability script uses `French`.

| Your verdict (agree / other / open) | Intended reading, if other |
|---|---|
| | |

---

## A5. `submessages`: "one or more", or may it be empty?

**Quoted text.**

- 5.1.5: "When present, it must be represented as a array defined by ECMA-404 consisting of one or more submessages."
- Annex A (informative): `"Submessages": {"type": "array", "items": {…}}`, with no minimum number of items.

**Readings possible.**

1. When the field is present it has at least one element; an empty array is invalid.
2. An empty array is valid (the schema allows it); "one or more" describes the usual case.

**Reading used.** Reading 2: the validator accepts an empty array. (We do not reject it.)

**Checks that depend on it.** None. The suite does not send an empty `submessages` array. C09 only checks that a non-array is rejected, which both readings agree on. **If you rule for reading 1, one check must be added.**

| Your verdict (agree / other / open) | Intended reading, if other |
|---|---|
| | |

---

## A6. What a receiver does with a message that lacks a required field

**Quoted text.** 5.1.2 to 5.1.4 and 5.2.2 to 5.2.4: "The format field is required." (and the same for `subformat` and `content`, in the first submessage and in every submessage). ECMA-431 clause 6 defines no HTTP status codes.

**Readings possible.**

1. The receiver must reject the message, with an error.
2. The standard only says the sender must include the field; what the receiver does is not specified (it may repair, ignore or reject).

**Reading used.** Reading 1: a message missing a required field is rejected. Over HTTP the checks accept any 4xx status and do not require a particular code or body.

**Checks that depend on it.** C04, C05, C06 (first submessage), C12, C13, C14 (submessages), C42 (HTTP 4xx for an invalid message). All seven are *in the headline*. All implementations tested pass them, so a different ruling would remove them from the table without changing who passes.

| Your verdict (agree / other / open) | Intended reading, if other |
|---|---|
| | |

---

## A7. Must a receiver reject a format that is not in Table 1?

**Quoted text.** 5.3: "The format field must have one of the values described in Table 1." Table 1 lists `text`, `token`, `structured`, `binary`, `location` and `generic`. Annex A (informative) has the same six in an `enum`.

**Readings possible.**

1. A receiver must reject any other value, such as `error` or `bogus`.
2. The sentence binds the *sender* only; what a receiver does with an unknown format is not specified (an end-point might ignore, pass on, or reject it).

**Reading used.** Reading 1 for the receiver (the validator rejects other values); and the sender side as it is written (an implementation must not build a message with another format).

**Checks that depend on it.**

| Check | What it tests | Status |
|---|---|---|
| C16 | a first-level message with format `error` or `bogus` is rejected | flagged |
| C17 | a submessage with format `error` is rejected | flagged |
| C47 | every message the implementation *builds* uses a format of Table 1 | *in the headline* (sender side; fails for `nlip_sdk`, which builds `error` messages) |

A ruling for reading 2 leaves C47 and finding D3 of the maintainers' summary intact: the SDK builds a format that is not in Table 1 whichever way the receiver rule is read.

| Your verdict (agree / other / open) | Intended reading, if other |
|---|---|
| | |

---

## One more point, outside A1–A7

**Null for an absent optional field (check C49).** 5.1.1 says that if `MessageType` is present "its value must be a string", and 5.1.5 that `submessages` is an array "when present". Annex A is informative and types them as `string` and `array`, with no mention of null. `nlip_server` writes `"messagetype": null, "label": null, "submessages": null` in every answer. Is an absent optional field to be omitted, or may it be sent as null?

Our reading: null is not a string or an array, so the field must be omitted. Our client therefore needed a tolerant reader. C49 is flagged and outside the headline.

| Your verdict (omit / null allowed / open) | Remark |
|---|---|
| | |

---

## Summary table

| Reading | Topic | Checks | In the headline? | Verdict |
|---|---|---|---|---|
| A1 | control field or message type | C35, C36, C38, C39 flagged; C37 in the headline | partly | |
| A2 | JSON types of `content` | C15 | flagged | |
| A3 | binary subformat | C18, C21, C48 | yes | |
| A4 | language spelling | C02, C20 | yes | |
| A5 | empty `submessages` | none | n/a | |
| A6 | missing required field | C04–C06, C12–C14, C42 | yes | |
| A7 | unknown format | C16, C17 flagged; C47 in the headline | partly | |
| (extra) | null for an absent optional field | C49 | flagged | |
