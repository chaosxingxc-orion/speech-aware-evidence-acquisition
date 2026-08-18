# P-A2T Stage-2c form-robustness probe — FLOWN

Date: 2026-08-18. Run id: `SAEA-PROBE-a2t-s2c-120`. Profile: `bounded-discovery-probe`.
Status: **FLOWN — all three arms complete. NO RESULT HAS BEEN READ.**

This is the flight receipt for the registered Stage-2c form-robustness probe
(`docs/readiness/2026-08-18-pa2t-stage2c-preregistration-REGISTERED.md`), which asks whether
Stage-2b B1's zero-margin CONFIRMED-CUT (8/120 conversion, 2 induced) survives presentation
perturbation and the augmenting position, on the SAME 120 headroom ids Stage-2/2b flew:

- **C1 (permuted, replacing).** B1's exact content — the correct tool's row(s) with
  `argument_defaults` STRIPPED — rendered with a seeded permutation of each row's JSON field
  order and its `argument_constraints` clause order, deterministic from `(seed, sample_id)`.
- **C2 (verbalized, replacing).** B1's exact content with `argument_constraints` rewritten as
  English prose sentences covering the SAME clauses (a small deterministic function, no LLM).
- **C3 (augmented right row).** A0's EXACT full 152-row registry PLUS B1's own content
  appended under Stage-2b's hash-pinned "particularly relevant" header — the direct right-row
  contrast to B2's wrong-row augment, and the deployment reading.

The exposure row `SAEA-PROBE-a2t-s2c-120` **stays `consumed=no`**. Reading these outputs is a
separately-registered one-shot read mission with its own pinned, pre-reviewed read suite
(`analysis.a2t_s2c_read`, committed at `59c6fa5`); this flight wrote `outputs.jsonl` and never
opened it.

## What flew

| Arm | Supply (prompt-level, per sample) | n | requests |
|---|---|---|---|
| `C1` | stripped row(s), seeded permutation of field order and constraint-clause order | 120 | 120 |
| `C2` | stripped row(s), constraints verbalized as English prose (same content, original order) | 120 | 120 |
| `C3` | full 152-row registry + pinned header + stripped row(s) appended (correct tool present twice) | 120 | 120 |

Seed `20260807`. Order per sample: `C1` then `C2` then `C3` over the 120 sorted headroom ids.

### Mapping reuse, not re-derivation

Every arm's per-sample content is loaded **verbatim** out of Stage-2's own already-written
`SAEA-PROBE-a2t-s2-120.arm-plan.json` (attempt `attempt-20260818T124955Z-84b944`) via
`analysis.a2t_s2_read.load_arm_plan`: all three C-arms source their roster from its
`s1p_tool_names` — the SAME mapping Stage-2b's B1 arm already sourced. No C-arm touches
`s4_tool_name` / `s4_derangement` at all, and no new randomization decides WHICH tool is
supplied — the seed only permutes C1's presentation. **Stage-2's `outputs.jsonl` was never
opened** — the arm-plan file is the sanctioned mapping surface.

## Flight outcome

One attempt, no resume needed, exit 0.

| | |
|---|---|
| Attempt id | `attempt-20260818T175018Z-0d3363` |
| Run dir | `$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-a2t-s2c-120/attempt-20260818T175018Z-0d3363` |
| Status | `COMPLETED` (receipt `error: null`) |
| Requests flown | **360 / 360** — 0 failures, 0 retries, 0 replays |
| Rows written | `outputs.jsonl` **360** rows: `C1` 120, `C2` 120, `C3` 120 (matches the registration exactly; 360 distinct `(arm, sample_id)` pairs, no completeness warning) |
| Wall (flight loop) | 5.7 min (17:52:04Z → 17:57:45Z) |
| Wall (GPU-occupied, from llama-server spawn) | 7.4 min = **0.124 h** of the 0.75 h ceiling (16.5 %) |
| Calls metered | **360** of the 380 planned / 400 registered |
| Speech audio metered | **1905.85 s** of the 2621 planned / 3000 registered |
| Throughput | mean **63.4 req/min** over the whole flight (~81 early) |
| Mean latency by arm | `C1` 1.031 s, `C2` 0.634 s, `C3` 1.157 s |
| Tokens | prompt 1,672,839; completion 14,946; `tool_calls` 0 |
| Trace manifest hash | `eb49ea6c732c37adde2801a0f2d5378fc91f825d92450dbbcbf92f59c0d0d48d` |
| Umbrella lock sha256 (returned by the gate) | `b588f3641ae1d1774fb7652c8978acf25eda7dcbc45a34a898d5471bce5b2e42` |
| Feature cache delta | **zero** — 480 entries / 243 M before and after, directory mtime unchanged (2026-08-18 02:36:43 -0400, pre-flight), **0 encode lines** in the server log across all 360 requests |
| GPU | idle P8 / 180–202 MHz, ~493 MiB before; P2–P4 / 232 MHz, 44–93 % util, 52–77 W, 46–59 °C during; back to idle P8 / 180 MHz, 485 MiB after |

Throughput ran ~40 % above Stage-2b's 45.6 req/min despite the same per-sample alternation
against a registry-sized prefill: two of the three arms here are tiny (~280–300 tokens), so
per sample the flight pays one C3 prefill (~12.9k tokens, mean 1.157 s) against two sub-second
requests, where Stage-2b paid one B2 prefill against a single B1. C3's mean latency (1.157 s)
lands slightly below B2's own 1.365 s. The cost is entirely prefill compute — the audio
feature cache stayed fully warm throughout (0 encode lines). The registered 0.75 GPU-h
ceiling was never approached: the flight used 16.5 % of it.

## Pre-flight (all model-free, all green)

| Precondition | Result |
|---|---|
| Tree clean for the whole run | clean at `59c6fa5` before launch, during flight, and at finalize |
| Bytecode hygiene | 0 `.pyc` under `src/`; `PYTHONDONTWRITEBYTECODE=1` in `launcher/env.sh` |
| Suite sanity | FULL suite **2374 passed, 9 skipped**; `tests/unit/test_a2t_s2c_flight.py` **29 passed** + `test_a2t_s2c_flight_config.py` **8 passed** |
| Headroom manifest | 120 ids, attempt dir `attempt-20260818T055500Z-res315` — the SAME ids Stage-2/2b flew, no new sample identity |
| Reused Stage-2 arm plan | loaded, seed `20260807` matches the flight config, 120 headroom ids, 120 `s1p_tool_names` (s4/derangement present but unused by any C-arm) |
| Arm construction | C-arm roster sizes `min 1 / max 3`, 75/120 single-tool (matches S1p's/B1's own shape verbatim) |
| Pinned C3 header | sha256 `befe65146a5abaa18b7d3446dfcdfeb5ed665f73e5b8564ba8b7d6916a71ebdf` — Stage-2b's own `B2_HIGHLIGHT_HEADER` constant, reused directly, unchanged |
| Split identity | receipt hash `e1d751e6…332c` matches the flight config, the headroom manifest and the ledger cell verbatim (64-hex) |
| Media | 120/120 headroom media present, 24000 Hz uniform |
| D1 media identity | `verify_media_identity('audio2tool')` **PASS** on all 120 headroom samples; unlisted sample id correctly refused (`GateClosed`) |
| Exposure row | exactly 1 row, `consumed=no`, `bounded-discovery-probe` / `discovery`, registers 400 / 3000 / 0.75 |
| ExecutionPlan | validates as `bounded-discovery-probe` / `discovery`, calls 380 / audio 2621 s / 0.75 GPU-h; config hash `54a4617c…`, protocol hash `a805d906…` |
| Payload binding | builds over the 120 headroom ids only (tighter than the full 400) |
| Gate dry-run | **AUTHORIZED** (umbrella lock sha256 `b588f364…`) |
| Feature cache | `/home/chao/feat-cache/audio2tool-q4km` **warm from the A0, Stage-2 and Stage-2b flights**: 480 entries before launch |
| Model resolution | ext4-only: `-m /home/chao/models/…-q4km/…Q4_K_M.gguf`, `--mmproj /home/chao/models/…/mmproj-…bf16.gguf`, binary `/home/chao/llama.cpp-featcache/build/bin/llama-server` |
| Binary + GGUF identity | binary sha256 `097c96ec…121c68` verified by hand pre-flight (precheck.log) and again at session spawn; both GGUF sha256s (`0751c279…`, `f0dfe825…`) verified by full-hash pre-flight pass and pinned in the session receipt |

## Metered audio: 3 passes, not 1

`C1`, `C2` and `C3` each re-send their sample's own audio, so the metered load is
`3 x 635.28` (one pass over the 120) = **1905.85 s**, not one pass. The plan carries 2621 s:
the worst case inside the 380-call budget is 1905.85 + 20 retries each bounded by the headroom
set's own longest item (35.71 s) = **2620.13 s**, which is why 2621 is the smallest plan
ceiling that cannot be crossed before the call budget stops the run — and it stays under the
registered 3000.

## The `-np 1` delta still applies

The committed model fragment carries `-c 49152 -np 4` = **12288 tokens per slot**. `C1`/`C2`
rosters are tiny (worst measured system prompts **1,117** and **1,184 chars**, ~280–300
tokens), but `C3` is the FULL 152-row registry plus the pinned header plus the appended
stripped row(s) — worst measured system prompt **51,471 chars, ~12.9k tokens** (A0's own is
50,413 chars; the delta is **+1,058 chars**) — which would overflow a 12288-token slot and
make `C3` unflyable. `-np 1` gives the single sequence the whole 49152 (worst-case sequence
~14.4k tokens), is memory-neutral, and costs no throughput because `FrozenCoreClient` issues
requests strictly sequentially. `_apply_np_delta` fails closed if the fragment ever stops
carrying exactly one `-np 4` pair.

## Discipline held

- **No result read.** The launcher prints only request index, arm, sample id, latency,
  ok/fail and response LENGTH. `outputs.jsonl` is written and never opened. Stage-2's
  `outputs.jsonl` was likewise never opened — only its `arm-plan.json`.
- **Two hard operational ceilings** enforced before the request that would cross them:
  400 requests (counted on the TOTAL index, replays included) and 0.75 h of CUMULATIVE wall
  clock measured from llama-server spawn (`--prior-wall-seconds` carries an earlier attempt's
  spend into a resume, so the registered GPU-h ceiling stays honest).
- **Fail-closed resume**: every response appended to `responses.jsonl` keyed by request index
  and the sha256 of that request's own canonical messages; a replay whose rebuilt hash
  disagrees refuses rather than proceeding.
- **Completeness check** on the written rows (per-arm counts and distinct `(arm, sample_id)`
  pairs) without touching response content.

## For the read mission

- Run id `SAEA-PROBE-a2t-s2c-120`, attempt id `attempt-20260818T175018Z-0d3363`.
- `outputs.jsonl` rows carry `{arm, sample_id, supplied_tool, response, timing}` — scoring is
  the read mission's job (`analysis.a2t_s2c_read`, `scripts/a2t_s2c_read.py`).
- The resolved arm construction is recorded in the run dir as
  `SAEA-PROBE-a2t-s2c-120.arm-plan.json`, carrying the reused Stage-2 arm-plan's path and
  sha256 alongside the per-sample correct-tool rosters every C-arm shares.
- Branch rules (ROBUST / FORM-FRAGILE / INCONCLUSIVE-C from C1+C2 jointly; the independent
  DEPLOY-AUGMENT overlay — DEPLOYABLE / CHANNEL-REOPENED / no flag — from C3 alone) are in
  the preregistration, section 3.

## Files

- `launcher/` — the complete flight launcher, pre-flight, D1 probe and shells
- `precheck.log` — environment precheck: no stale server, fresh run dir, binary + both GGUF
  full sha256s matching the receipt pins, warm cache, clean tree
- `preflight-split-measurement.json` — model-free plan construction, audio load and the
  measured per-arm prompt sizes
- `preflight-d1-probe.log` — D1 media identity PASS on all 120 plus negative control
- `preflight-tests.log` — the full suite (2374 passed) plus the 37 s2c machinery tests
- `preflight.log` — the full pre-flight, green on every axis including the gate dry-run
- `flight.log` — the operational health log of the flight itself
- `gpu-health.log` — GPU samples before, during and after
- `postcheck.log` — post-flight evidence: server down, featcache untouched, 0 encode lines,
  360-row outputs, tree still clean
- `flight-receipt.json` — status, hashes, per-arm counts, cost, wall, close receipt
- `execution-plan.json` / `config-values.json` / `session-receipt.json` — run identity, the
  llama.cpp binary sha256 and both GGUF sha256s
- `MANIFEST.sha256` — hashes of everything above
