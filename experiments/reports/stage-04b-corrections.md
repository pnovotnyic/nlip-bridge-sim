# Stage 04b corrections: review-driven adjustments and R1 performance evaluation

Status: **done** (2026-11-13).

This report summarizes the corrections and benchmarks carried out for Stage 04b following the review of stages 03b and 04, incorporating decisions taken on 13 November 2026.

---

## 1. Summary of Changes and Files

The adjustments span three main areas: backend identifier validation, catalogue-based breaking change metrics, and Ollama R1 execution optimization.

### A. Backends: Device Identifier Consistency
- **L1 (Device Reachability Status v1.0.0):** Handled the case where a request supplies several device identifiers belonging to different devices. If a mismatch is detected, the backend responds with a `422 IDENTIFIER_MISMATCH` as specified in `specs/L1/v1.0.0.yaml` (lines 438–448). If they match, or if only one is provided, the standard success behavior is maintained.
- **L2 and L3:** Continued the "first identifier wins" policy (checking `phoneNumber`, then `ipv4Address`, then `ipv6Address`) because they define no mismatch code.
- **Data Logging:** Added two new fields to every `backend.jsonl` entry for L1, L2, and L3:
  - `resolved_device`: The device's world ID (e.g. `D07`) or `null`.
  - `identifiers_consistent`: `true` if all identifiers supplied belong to that device, `false` if they are mismatched, and `null` if no device was resolved.
- **Files Modified:**
  - `experiments/nlipeval/backends/l1_reachability.py` (L1 identifier consistency check and `422 IDENTIFIER_MISMATCH`)
  - `experiments/nlipeval/backends/l2_location.py` (L2 logging updates)
  - `experiments/nlipeval/backends/l3_qod.py` (L3 logging updates)
  - `experiments/reports/schema-changes.md` (Recorded schema fields)
  - `experiments/reports/stage-04-backends.md` (Updated choices and tables)
  - `experiments/tests/test_backends.py` (Added tests for mismatch validation and log fields; verified specification error codes)

### B. Specifications: Catalogue-Based Breaking Changes
- **Catalogue Metric:** Implemented a method to count fine-grained, field-level and value-level breaking changes from the change catalogue.
- **Files Modified:**
  - `experiments/nlipeval/tasks/changes.py` (Implemented the function to count catalogue-based breaking changes)
  - `experiments/nlipeval/tasks/specs.py` (Integrated catalogue metrics build steps)
  - `experiments/results/specs/catalogue_breaking_crossed.csv` (Exported results table)
  - `experiments/tests/test_specs_catalogue.py` (Verified that the current server version yields 0 changes and that L1 v0.5.1 counts moved reachability operation field changes)
  - `experiments/reports/stage-02-specs.md` (Added the side-by-side comparison section)

### C. R1 Serving and Benchmarks
- **Serving Script:** Wrote a robust initialization script `scripts/start_ollama_r1.sh` that safely terminates any GUI/CLI Ollama instances, reads model serving defaults from `experiments/config/models.yaml`, spawns `ollama serve` under a background process, preloads the `nlip-qwen3-4b` model with an infinite `keep_alive`, and writes runtime parameters to a git-ignored `experiments/.backends/serving.json`.
- **Alternating Test Script:** Wrote `experiments/scripts/test_alternating.py` to evaluate the real-world client/server call pattern on the R1 model.
- **Files Modified/Created:**
  - `scripts/start_ollama_r1.sh` (Ollama serving starter)
  - `experiments/scripts/test_alternating.py` (Alternating pattern test)
  - `experiments/config/models.yaml` (Updated R1 `max_concurrency` and `OLLAMA_NUM_PARALLEL` to 1)

---

## 2. Breaking-Change Measures Side-by-Side

To support Figure 3, the three metrics are compared below for each (API, client version):

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

### Why the measures disagree:
1. **Whole API vs. Operations used:** Whole API counts (`breaking_crossed`) include paths and features our tasks do not execute (such as L1's removal of `/roaming` and `/subscriptions*` at v0.6.0).
2. **Operations used vs. Catalogue:**
   - **Catalogue is field-level and value-level:** For L3 v0.8.1, the catalogue registers 45 breaking changes compared to 14 from `oasdiff` operations used. This is because a single parent struct change (like `ueId` to `device`) resolves to many separate, fine-grained, fully-tracked field-level changes (e.g. `device.phoneNumber`, `device.ipv4Address`).
   - **Catalogue handles path renames:** For L1 v0.5.1, the operation was renamed from `/connectivity` to `/retrieve`. `oasdiff` treats this as a complete path removal and addition, failing to cross-reference their schemas. The catalogue explicitly maps field lineage across path renames.
   - **Catalogue captures semantic value-level breaking changes:** For L2 v2.0.0, the catalogue records 2 breaking changes while `oasdiff` reports 0. This is because the catalogue captures semantic value-level removals (e.g., removing `UNKNOWN` from `verificationResult` at v3.0.0), which structural schema comparisons miss.

---

## 3. R1 Alternating Call Performance and Decisions

### Alternating-Pattern Results (Rounds 2-10, discarding Cache-Warming Round 1)

All measurements are given in seconds.

| Metric | `OLLAMA_NUM_PARALLEL=1` | `OLLAMA_NUM_PARALLEL=2` |
|---|---|---|
| **Client Call Latency (Median)** | **11.41 s** | 11.80 s |
| **Client Call Latency (Mean)** | 11.31 s | 11.87 s |
| **Server Call Latency (Median)** | **14.72 s** | 15.57 s |
| **Server Call Latency (Mean)** | 14.65 s | 15.53 s |
| **Total Round Latency (Mean)** | **25.96 s** | 27.40 s |

### Serving Decisions
- **`NUM_PARALLEL`:** The rules state we keep `NUM_PARALLEL=2` only if a round takes at least 20% *less* time than with 1. In practice, `NUM_PARALLEL=2` was **slower** (27.40s mean round latency vs 25.96s for `NUM_PARALLEL=1`). Therefore, we decide to keep **`OLLAMA_NUM_PARALLEL=1`**.
- **`max_concurrency`:** In both cases, concurrency 2 gave no throughput gain, so R1 will run at **`max_concurrency: 1`**.
- **Model config update:** `experiments/config/models.yaml` was updated to set `max_concurrency: 1` and `OLLAMA_NUM_PARALLEL: "1"`.
- **Smoke Tests:** With these settings, R1's smoke tests 1–4 were executed and **passed 100% successfully**:
  - `1_chat`: passed (pong)
  - `2_system_prompt`: passed (BANANA)
  - `3_structured`: passed (json_schema mode selected, 5/5 valid)
  - `4_long_context`: passed (TANGO-4417 under 20k token context)

---

## 4. Realistic R1 Timing Projections for Stages 09 and 10

These are the first realistic projections for R1's execution time, utilizing the measured medians (Client: 11.41s, Server: 14.72s; Round: 26.13s) and the exact session counts from the stage planning files.

### A. Session and Call Breakdown
- **Stage 09 (Stage 2 Runs):** 180 sessions total for R1 (90 instances × 2 conditions).
- **Stage 10 (Stage 3 Runs):** 990 sessions total for R1 (Blocks 1–4 pooled).
- **Total Sessions across Stages 09 & 10:** **1,170 sessions**.
- At approximately **6 calls per session** (consisting of 3 client-style calls and 3 server-style calls):
  - **Total Client Calls:** 3,510 calls.
  - **Total Server Calls:** 3,510 calls.
  - **Total Calls:** **7,020 calls**.

### B. Projected Execution Duration
Using the median call latencies for the Client (11.41s) and Server (14.72s):
- **Client execution time:** 3,510 calls × 11.41 s = 40,049.1 s
- **Server execution time:** 3,510 calls × 14.72 s = 51,667.2 s
- **Total Projected Time:** 91,716.3 s = **25.48 hours**

*(Note: If calculated using the overall mean call duration of 12.98s, the projection is 7,020 × 12.98s = 91,119.6s = **25.31 hours**).*

R1's continuous queue must be allocated a dedicated run of approximately **25.5 hours** to complete Stages 09 and 10.
