# NLIP evaluation experiments

Code, runs and scoring for the NLIP evaluation. The plan is in `../bob_plan/` (start with `00-overview.md`).

## Setup

Requires [uv](https://docs.astral.sh/uv/) and Python 3.12 (uv fetches it).

```bash
cd experiments
uv sync          # creates .venv from pyproject.toml / uv.lock (all versions pinned)
uv run pytest
```

Credentials go in `experiments/.env` (never committed); see `.env.example` (added in stage 01, step 2).

## Starting Ollama for R1

R1 (`nlip-qwen3-4b`, derived from `qwen3:4b`; see `config/Modelfile.qwen3-4b-nlip`) is served by Ollama on the Mac. The settings are in `config/models.yaml` under `rungs.R1.serving`. They are read by Ollama when it starts, so **quit the Ollama menu-bar app first** (it starts its own server without them), then:

```bash
OLLAMA_FLASH_ATTENTION=1 OLLAMA_KV_CACHE_TYPE=q8_0 OLLAMA_NUM_PARALLEL=2 OLLAMA_KEEP_ALIVE=-1 ollama serve
```

Check with `ollama ps` (context 65536, 100% GPU, "Forever") and by reading the `server config` line in the server log. Change `max_concurrency` for R1 in `config/models.yaml` together with `OLLAMA_NUM_PARALLEL`; they must match.

## Mock backends (stage 04)

```bash
uv run python -m nlipeval.backends.launcher up --run-dir data/runs/<run_id>    # L1 :9101, L2 :9102, L3 :9103
uv run python -m nlipeval.backends.launcher down
```

Details, world files and error codes: `reports/stage-04-backends.md`.

## Layout

See `../bob_plan/00-overview.md` §6. Progress is tracked in `STATUS.md`.
