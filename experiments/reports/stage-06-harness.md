# Stage 06: NLIP harness and agents

## Deliverables

| Item | Location |
|---|---|
| Agent schemas | `nlipeval/agents/schemas.py` |
| Prompt templates | `prompts/client_P{1,2,3}.txt`, `prompts/server_P{1,2,3}.txt`, `prompts/client_NLIP0.txt`, `prompts/server_NLIP0.txt` |
| Prompt rendering | `nlipeval/agents/prompts.py` |
| Client agent | `nlipeval/agents/client.py` |
| Server agent + NLIP end-point | `nlipeval/agents/server.py` |
| Session state machines | `nlipeval/runner/session.py` |
| Matrix runner | `nlipeval/runner/run.py` |
| Matrix files | `config/runs/smoke-r3.yaml`, `config/runs/pilot.yaml`, `config/runs/stage2-main.yaml` (stage 07b) |
| Fake model for tests | `tests/fake_model.py` |
| Harness tests | `tests/test_harness.py` |
| P3 notes | `prompts/notes/<api>/<version>.md`, with `.sources.md` (spec line numbers per statement) |
| Prompt sizes (real tokenizers) | `results/prompts/prompt_sizes.csv`, `nlipeval/agents/prompt_sizes.py` |
| Review copy of the prompts | `reports/review-prompts.md` (`scripts/gen_review_prompts.py`) |
| Time and cost projection | `results/prompts/time_projection.csv`, `results/prompts/r5_cost.csv`, `scripts/project_time_cost.py` |

## State machines

### NLIP (interaction allowed)

```
1.  Client  request
2.  Server  ask | restate | decline
            if execute before confirm → treat as restate, log protocol_slip
3.  Client  answer (→ 2, +1 interaction)         only after an ask
            correct (→ 2, +1 interaction)        only after a restate
            confirm (→ 4, 0 interactions for first restate)
            abort   → termination: declined
            any other action after a restate → error_model (the reply is logged)
4.  Harness execute plan against backend
5.  Server  report
            restate (backend rejected) → 3, +1 interaction
6.  Client  final
7.  Limits  ≤5 interactions → max_interactions
            ≤30 model calls total
            wall-time limit
```

### NLIP-0 (no interaction)

```
1.  Client  request
2.  Server  execute | decline
            ask/restate → protocol_slip; take plan if present, else decline
3.  Harness execute plan against backend
            on 4xx: server may revise once (n_server_retries += 1)
4.  Server  report
5.  Client  final
```

### Error paths

| Termination | Trigger |
|---|---|
| `final` | Normal completion |
| `declined` | Server decline or client abort |
| `max_interactions` | ≥5 interactions or ≥30 model calls |
| `timeout` | Wall-time limit exceeded |
| `error_model` | Parse failure after repair, a refusal, or a reply that breaks the turn contract (stage 07b B8) |
| `error_harness` | Infrastructure failure: HTTP, timeout, connection, the backend or the inline NLIP server (stage 07b B8) |

A `timeout` is re-run once at twice the limit; the record carries `timeout_rerun`. A client whose last turn has no `final` object counts as a protocol slip and scores as no answer.

## Call counts per session type

| Condition | k (interactions) | Model calls |
|---|---|---|
| NLIP, k=0 (restate+confirm only) | 0 | 5 (request + server reply + confirm + server report + final) |
| NLIP, per additional interaction | +1 | +2 (client answer/correct + server reply) |
| NLIP-0 | 0 | 4 (request + server execute + server report + final) |

NLIP at k=0 is **5 calls**. NLIP with k interactions is **5 + 2k calls**. NLIP-0 is **4 calls**.

## Prompt sizes

Real tokenizer counts per rung are in `results/prompts/prompt_sizes.csv` (68 rows: server prompts per API at the current server version, client prompts per API and client version; P1, P2, P3 and NLIP-0). The counts are the `prompt_tokens` of a one-token call as the harness sends it, minus a one-word system prompt. The tables are in `reports/stage-07b-corrections.md`.

## Time and cost estimates

See `reports/stage-07b-corrections.md` (B12): time per rung for stages 08–10, and R5's cost for stage 14. They come from `scripts/project_time_cost.py`.

## Prompts hash

`7f0909b25c63335596d132311e986c32b05c9a3ea6e8e644b31f8d05574c0357`

## Architecture decisions

- **Backend→server communication bypasses the NLIP wire.** After the harness executes a plan, it calls the server agent directly with the backend outcome. This is the harness's privilege and avoids polluting the NLIP wire with infrastructure messages. Only natural-language messages between agents travel over the wire.

- **Inline server per session.** Each session starts its own uvicorn instance for the server agent. This is heavier than a shared server but ensures complete isolation between concurrent sessions and clean per-session conversation state.

- **Wire log from NLIPClient.** Wire messages are captured by `NLIPClient.wire` (which calls `validate()` on each message) and converted to the data contract format in the `run_session` finally block.

- **Conversation history.** Each agent keeps its own history. The client's history starts with the user turn "Begin the session."; its own earlier replies are assistant turns holding the JSON it sent, and the server's messages are user turns. The server's history is the same, mirrored, and the harness appends the backend report to it as a user turn. Without this, the smoke run's client treated each server message as a fresh prompt and answered "request" to a restatement (07b B11).
- **Plan path.** The server writes `plan.path` as the full request path: the base path of the `servers` URL followed by the operation path, starting with "/" and with no scheme or host. The prompts and `SERVER_SCHEMA` say so, and the harness posts the path unchanged to the backend. It does not repair a path. A wrong path is a rejected call and is scored as such.
- **One timeout rule.** `_create_with_deadline` bounds every HTTP try by wall-clock time. The client library's own timeout applies to each socket read, so a stalled connection held two runs open for more than 30 minutes; it is now reported as a timeout and retried like any other.
- **Resumability.** The session key `(task_id, rung, prompt, condition, attempt)` allows re-runs to skip completed sessions.

## Open questions

1. **Petr's reviews, before the pilot:** `reports/review-prompts.md` (the rendered prompts) and the 14 P3 notes (`prompts/notes/`, with `.sources.md`).
2. **R1 concurrency** is 1; stage 04b showed no throughput gain from concurrency 2.
3. **L1 v0.5.1 and v0.6.0, devices with both DATA and SMS.** The gold answer is `CONNECTED_DATA`, from a precedence rule that no text the agents are given states. In the smoke run an R3 client answered `unrepresentable` here. The task sheet should decide: keep the gold, accept either value, or make `unrepresentable` the gold for those instances (12 of 30 main instances at each of the two versions).
