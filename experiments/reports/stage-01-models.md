# Stage 01 report: environment, project skeleton and model access

Date: 2026-11-13. Branch: `bob/experiments`. Status: **all five rungs pass smoke tests 1-4; waiting for Petr to confirm the step 7 settings.**

## What was done

1. **Project** in `experiments/`: Python 3.12 (uv), 15 dependencies pinned to exact versions in [`pyproject.toml`](../pyproject.toml), `uv.lock` committed, directory layout as in the overview §6.
2. **Credentials**: `.env.example` lists the names; `.env` (git-ignored, mode 600) holds the values. `data/runs/` and `data/smoke/` are git-ignored.
3. **[`config/models.yaml`](../config/models.yaml)**: one entry per rung, with the exact model, endpoint variables, headers, parameters, structured-output mode, concurrency, timeout and context size.
4. **R1**: `qwen3:4b` pulled (digest `359d7dd4bcda`, Q4_K_M, 4.0B parameters, native context 262,144). A derived Ollama model `nlip-qwen3-4b` fixes `num_ctx` at 65536 (raised from 32768 in stage 02, see `reports/stage-02-specs.md`) and the model-card sampling defaults ([`config/Modelfile.qwen3-4b-nlip`](../config/Modelfile.qwen3-4b-nlip)). `ollama ps` confirms context 65536 on 100% GPU.
5. **Adapter** [`nlipeval/models/adapter.py`](../nlipeval/models/adapter.py): `call(rung, system, messages, schema, purpose, session_id)`.
   - One OpenAI SDK client per endpoint; per-endpoint concurrency limit.
   - Retries on 429, 5xx, timeouts and connection errors: at most 4 tries, exponential backoff, every try recorded in `attempts`. No retry on other 4xx.
   - Every call goes to `calls.jsonl` (data contract §2.3, plus `attempts`, `cached`, `error_type`); system prompts are stored once by hash.
   - Disk cache keyed by SHA-256 of (rung, model, full request, schema, mode, attempt); entries are checked against their own key; errors are never cached.
   - Structured output in three modes (`json_schema`, `json_object`, `prompt`), always validated with `jsonschema`; one logged repair call (`purpose: repair`); then a `parse_failure`.
   - Refusals and content-filter stops are recorded as `error_type: refusal`. There is no fallback to another model.
   - Fallback flag `system_role_supported: false` prepends the system text to the first user message (not needed by any rung).
6. **Tests**: [`tests/test_adapter.py`](../tests/test_adapter.py) (10 offline tests against a fake OpenAI-compatible server: logging, key redaction, cache keys, retries, the 4-attempt limit, the three structured modes, repair, the system-role fallback). [`tests/test_models_smoke.py`](../tests/test_models_smoke.py) checks the live results. `uv run pytest`: 15 passed.
7. **Smoke tests** [`nlipeval/models/smoke.py`](../nlipeval/models/smoke.py); results in [`results/stage01/smoke_R*.json`](../results/stage01/). Raw calls are in `data/smoke/<rung>/calls.jsonl` (git-ignored).

## Results per rung

| | R1 | R2 | R3 | R4 | R5 |
|---|---|---|---|---|---|
| Model sent | `nlip-qwen3-4b` (from `qwen3:4b`) | `google/gemma-4-12B-it` | `openai/gpt-oss-20b` | `deepseek-ai/DeepSeek-V3.2` | `aws/claude-opus-5-5` |
| Endpoint type | Ollama, OpenAI-compatible, local | RITS (vLLM) | RITS (vLLM) | RITS (vLLM) | LiteLLM proxy |
| Auth | dummy key | header `RITS_API_KEY` | header `RITS_API_KEY` | header `RITS_API_KEY` | `Authorization: Bearer` |
| 1 Chat | pass | pass | pass | pass | pass |
| 2 System prompt honoured | pass | pass | pass | pass | pass |
| 3 Structured output (first mode with 5/5) | `json_schema` | `json_schema` | `json_schema` | `json_schema` | `json_schema` |
| 4 Long context (about 20,000 tokens, fact at start) | pass (19,643 tokens) | pass (19,514) | pass (19,996) | pass (19,852) | pass (19,902) |
| Median seconds, 4,000-token prompt, up to 300 tokens out | 14.8 | 5.8 | 1.8 | 28.0 | 6.5 |
| Median seconds, structured call | 11.9 | 1.2 | 1.7 | 4.6 | 5.6 |
| Concurrency without 429 or errors | 2 (tested 1, 2) | 8 | 8 | 8 | 8 |
| Concurrency set in config | 1 | 4 | 4 | 4 | 4 |
| Settings sent | temperature 0.6, top_p 0.95, seed 0 | temperature 1.0, top_p 0.95, seed 0 | temperature 1.0, top_p 1.0, seed 0, `reasoning_effort: medium` | temperature 1.0, top_p 0.95, seed 0 | no sampling parameters; `reasoning_effort: medium` |
| Thinking | on by default, as served | not applicable | `reasoning_effort` medium | as served; replies carry `reasoning: null` | on; effort medium |
| Reported reasoning tokens | none | 0 | none | none | 0 |

Concurrency was tested up to 8 on the hosted endpoints and up to 2 on the Mac; none returned 429. The tests did not go beyond 8.

Notes on how the settings were checked:
- **R3**: `reasoning_effort` has a clear effect. For the same question it gave 359, 730 and 5,322 completion tokens for low, medium and high (2.2 s, 3.9 s, 29 s). It is fixed at `medium`.
- **R5**: the proxy accepts `reasoning_effort` (low, medium and high all returned 200), but its effect was small in a quick check (260 to 468 completion tokens for one question, with no consistent trend). It is fixed at `medium`. The proxy also accepts `temperature`; it is not sent, as the plan requires.
- **R1**: `keep_alive` cannot be set per request through Ollama's OpenAI-compatible endpoint. During the stage I loaded the model with `keep_alive: -1` (`ollama ps` shows "Forever"). For the runs, start Ollama with `OLLAMA_KEEP_ALIVE=-1` or send the same warm-up request.

## Run-time and cost estimate

Call counts from stages 09 and 10: about 4,500 (stage 2) plus about 36,000 (stage 3) model calls over five rungs, which is about **8,100 calls per rung** (the overview says about 9,000). Time is calls × the measured 4,000-token median latency ÷ concurrency. It is only a first estimate: real calls have different prompt and reply sizes, and these latencies are single-user figures.

| Rung | Seconds per call | Concurrency | Estimated wall time for 8,100 calls |
|---|---|---|---|
| R1 | about 15 | 1 | about 34 hours |
| R2 | 5.8 | 4 | about 3.3 hours |
| R3 | 1.8 | 4 | about 1 hour |
| R4 | 28 | 4 (8 is possible) | about 16 hours (about 8 hours at 8) |
| R5 | 6.5 | 4 | about 3.7 hours |

R1 is the long pole, as the plan says. On the Mac, two parallel short calls finished in 2.7 s against 1.8 s for one, so concurrency 2 may give about 1.4 times the throughput; it was only measured with tiny prompts, and `max_concurrency` is left at 1 until the pilot shows whether long prompts gain from it (which would cut R1 to about 24 hours). The plan's stage 3 order starts R1 first and keeps it running.

**R5 cost at list price ($4 / $20 per million input / output tokens)** depends on token counts per call, which are unknown until the harness exists. With an assumed 2,000 to 5,000 input and 300 to 600 output tokens per call over 8,100 calls:

| Case | Input tokens | Output tokens | Cost |
|---|---|---|---|
| Low (2,000 in / 300 out) | 16.2 M | 2.4 M | about $114 |
| Middle (3,000 in / 400 out) | 24.3 M | 3.2 M | about $162 |
| High (5,000 in / 600 out) | 40.5 M | 4.9 M | about $259 |

The provider's billing may differ from list price. The proxy reported 0 reasoning tokens, so hidden thinking, if billed, could make real cost higher. A better figure will be possible after the pilot (stage 08).

## Deviations and problems

- **Python**: the Mac has Python 3.13 only; uv installed CPython 3.12.13 for the project.
- **R1 model name**: the model sent is the derived `nlip-qwen3-4b`, not `qwen3:4b`, to fix `num_ctx`. The manifest should record both (`base_model`, `base_model_digest` are in `models.yaml`).
- **RITS authentication**: `Authorization: Bearer` returns 403; RITS needs the header `RITS_API_KEY`. The OpenAI SDK sends it as a default header.
- **RITS model URLs**: the gpt-oss endpoint slug is `gpt-oss-20b-a100`, and the DeepSeek slug is `deepseek-v3-2`.
- **Cold starts**: the first request to Gemma took 47 seconds, and `GET /models` on Gemma and gpt-oss timed out. Later requests were fast (see the table).
- **R4 stalls on a new schema**: two early smoke runs of R4 stalled for more than 5 minutes on their first `json_schema` request, and a direct request with the same schema timed out at 40 seconds, while `json_object` with the same prompt answered. A later run of the same requests answered in about 4.6 s each with no retries. My guess is a slow first compilation of the schema on the server, cached afterwards, but I have not confirmed it. It matters for the harness, because every new schema may stall the first call. The adapter timeout (300 s) with up to 4 tries covers it, at a cost in time.
- **Smoke test fixes**: the first long-context prompts were too short (14,500 to 18,700 tokens for R2 and R3). The test now calibrates words per token on the model's own tokenizer and rescales once, so the prompt is at least 19,500 tokens. All five rungs were then re-run with the final code. One R1 run crashed because I deleted its cache folder while it was running; it was re-run.
- **Reasoning tokens**: only R2 and R5 report `reasoning_tokens` (both 0); R1, R3 and R4 report none. Reasoning cost for those rungs is inside `completion_tokens` only if the provider counts it there; I did not verify this.

## Open questions for Petr

1. **Confirm the step 7 settings** (this closes the stage): the sampling parameters in the table, `reasoning_effort: medium` for R3 and R5, thinking left on as served for R1 and R4, and no sampling parameters for R5.
2. **R1 thinking**: the median is about 15 s per call on short prompts, below the plan's 60 s threshold, so I am not asking to switch thinking off. One 20,000-token call took 75 s. Real runs may be slower once prompts are long; the pilot will show it.
3. **Concurrency**: should R2 to R5 run at 4 (current config) or 8 (tested without errors)? R4 would finish in about half the time at 8.
4. **Key hygiene**: the RITS and LiteLLM keys were pasted into the chat. Rotate them if the conversation is stored or shared.
5. **R1 time**: about 34 hours of Mac time is a lot. Is the Mac available that long, or should R1 start early (the plan allows it)?
