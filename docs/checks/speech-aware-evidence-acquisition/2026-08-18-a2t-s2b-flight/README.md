# P-A2T Stage-2b follow-up probe — FLOWN

Date: 2026-08-18. Run id: `SAEA-PROBE-a2t-s2b-120`. Profile: `bounded-discovery-probe`.
Status: **FLOWN — both arms complete. NO RESULT HAS BEEN READ.**

This is the flight receipt for the registered Stage-2b follow-up
(`docs/readiness/2026-08-18-pa2t-stage2b-preregistration-REGISTERED.md`), which asks two
independent questions on the SAME 120 headroom ids Stage-2 flew:

- **Q-A (corruption channel).** `B1` re-flies S1p's exact self-supplied roster with
  `argument_defaults` STRIPPED — schema structure and constraints only, no values. If the
  Stage-2 corruption survives the strip it is not the default values that cause it.
- **Q-B (schema vs knowledge, with a MISLEAD overlay).** `B2` sends A0's full 152-row
  registry PLUS the Stage-2-deranged wrong row appended under a hash-pinned "particularly
  relevant" header. The correct tool stays PRESENT, so a drop isolates attention/schema
  pressure rather than missing knowledge.

The exposure row `SAEA-PROBE-a2t-s2b-120` **stays `consumed=no`**. Reading these outputs is a
separately-registered one-shot read mission with its own pinned, pre-reviewed read suite
(`analysis.a2t_s2b_read`, committed at `d85a025`); this flight wrote `outputs.jsonl` and never
opened it.

## What flew

| Arm | Supply (prompt-level, per sample) | n | requests |
|---|---|---|---|
| `B1` | nodefaults: S1p's EXACT reused roster, rendered with `argument_defaults` stripped | 120 | 120 |
| `B2` | augmented wrong row: A0's full 152-row registry + pinned header + the Stage-2-deranged wrong row (correct tool still present) | 120 | 120 |

Seed `20260807`. Order per sample: `B1` then `B2` over the 120 sorted headroom ids.

### Mapping reuse, not re-derivation

Both arms' per-sample content is loaded **verbatim** out of Stage-2's own already-written
`SAEA-PROBE-a2t-s2-120.arm-plan.json` (attempt `attempt-20260818T124955Z-84b944`) via
`analysis.a2t_s2_read.load_arm_plan`: `B1`'s roster from its `s1p_tool_names`, `B2`'s wrong
row from its `s4_tool_name`. No new randomization happens anywhere in this flight.
**Stage-2's `outputs.jsonl` was never opened** — the arm-plan file is the sanctioned mapping
surface. `build_flight_plan` re-checks the reused derangement's global and per-sample
no-fixed-point invariants anyway (defense-in-depth on a verbatim reuse).

## Flight outcome

One attempt, no resume needed, exit 0.

| | |
|---|---|
| Attempt id | `attempt-20260818T153859Z-8da515` |
| Run dir | `$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-a2t-s2b-120/attempt-20260818T153859Z-8da515` |
| Status | `COMPLETED` (receipt `error: null`) |
| Requests flown | **240 / 240** — 0 failures, 0 retries, 0 replays |
| Rows written | `outputs.jsonl` **240** rows: `B1` 120, `B2` 120 (matches the registration exactly; 240 distinct `(arm, sample_id)` pairs, no completeness warning) |
| Wall (flight loop) | 5.3 min (15:40:47Z → 15:46:02Z) |
| Wall (GPU-occupied, from llama-server spawn) | 7.1 min = **0.118 h** of the 0.5 h ceiling |
| Calls metered | **240** of the 260 planned / 280 registered |
| Speech audio metered | **1270.56 s** of the 1985 planned / 2000 registered |
| Throughput | mean **45.6 req/min** over the whole flight (peak ~69 early) |
| Mean latency by arm | `B1` 1.243 s, `B2` 1.365 s |
| Tokens | prompt 1,638,764; completion 9,632; `tool_calls` 0 |
| Trace manifest hash | `d90ccfc002419531e710cac0ff21ed6eb4750177cb61f84852abd93611b92833` |
| Umbrella lock sha256 (returned by the gate) | `b588f3641ae1d1774fb7652c8978acf25eda7dcbc45a34a898d5471bce5b2e42` |
| Feature cache delta | **zero** — 480 entries / 243 M before and after, **0 encode lines** in the server log across all 240 requests |
| GPU | idle P8 / 180 MHz, 254 MiB before; P2–P4 / 232 MHz, 75–94 % util, 51–74 W, 53–60 °C during; back to idle P8 / 180 MHz, 254 MiB after |

Throughput ran roughly half Stage-2's (45.6 vs 86–115 req/min) for a structural reason, not a
fault: Stage-2 flew its full-registry `N0r` arm as one contiguous 40-request block, so every
one of those requests hit llama-server's longest-common-prefix slot cache. Stage-2b
**alternates** `B1` (a ~279-token nodefaults roster) with `B2` (a ~12.7k-token full-registry
prefill) on every single sample, so each `B2` prefill is evicted by the `B1` request that
follows it and must be recomputed. The cost is entirely prefill compute — the audio feature
cache stayed fully warm throughout (0 encode lines). The registered 0.5 GPU-h ceiling was
never approached: the flight used 23.5 % of it.

## Pre-flight (all model-free, all green)

| Precondition | Result |
|---|---|
| Tree clean for the whole run | clean at `d85a025` before launch, during flight, and at finalize |
| Bytecode hygiene | 0 `.pyc` under `src/`; `PYTHONDONTWRITEBYTECODE=1` in `launcher/env.sh` |
| Suite sanity | `tests/unit/test_a2t_s2b_flight.py` **20 passed** + `test_a2t_s2b_flight_config.py` **8 passed** = **28 passed** |
| Headroom manifest | 120 ids, attempt dir `attempt-20260818T055500Z-res315` — the SAME ids Stage-2 flew, no new sample identity |
| Reused Stage-2 arm plan | loaded, seed `20260807` matches the flight config, 120 headroom ids, 120 `s1p_tool_names`, 120 `s4_tool_name`, derangement over 54 distinct tool identities |
| Arm construction | `B1` roster sizes `min 1 / max 3`, 75/120 single-tool (matches S1p's own shape verbatim); 0 global fixed points, 0 per-sample fixed points |
| Pinned B2 header | sha256 `befe65146a5abaa18b7d3446dfcdfeb5ed665f73e5b8564ba8b7d6916a71ebdf` — unchanged from the committed constant |
| Split identity | receipt hash `e1d751e6…332c` matches the flight config, the headroom manifest and the ledger cell verbatim (64-hex) |
| Media | 120/120 headroom media present, 24000 Hz uniform |
| D1 media identity | `verify_media_identity('audio2tool')` **PASS** on all 120 headroom samples; unlisted sample id correctly refused (`GateClosed`) |
| Exposure row | exactly 1 row, `consumed=no`, `bounded-discovery-probe` / `discovery`, registers 280 / 2000 / 0.5 |
| ExecutionPlan | validates as `bounded-discovery-probe` / `discovery`, calls 260 / audio 1985 s / 0.5 GPU-h; config hash `8820275b…`, protocol hash `ff642e87…` |
| Payload binding | builds over the 120 headroom ids only (tighter than the full 400) |
| Gate dry-run | **AUTHORIZED** (umbrella lock sha256 `b588f364…`) |
| Feature cache | `/home/chao/feat-cache/audio2tool-q4km` **warm from the A0 and Stage-2 flights**: 480 entries before launch |
| Model resolution | ext4-only: `-m /home/chao/models/…-q4km/…Q4_K_M.gguf`, `--mmproj /home/chao/models/…/mmproj-…bf16.gguf`, binary `/home/chao/llama.cpp-featcache/build/bin/llama-server` |

## Metered audio: 2 passes, not 1

`B1` and `B2` each re-send their sample's own audio, so the metered load is `2 x 635.28` (one
pass over the 120) = **1270.56 s**, not one pass. The plan carries 1985 s: the worst case
inside the 260-call budget is 1270.56 + 20 retries each bounded by the headroom set's own
longest item (35.71 s) = **1984.84 s**, which is why 1985 is the smallest plan ceiling that
cannot be crossed before the call budget stops the run — and it stays under the registered
2000.

## The `-np 1` delta still applies

The committed model fragment carries `-c 49152 -np 4` = **12288 tokens per slot**. `B1`'s
nodefaults rosters are tiny (worst measured system prompt **1,117 chars**, ~279 tokens), but
`B2` is the FULL 152-row registry plus the pinned header plus one appended row — worst
measured system prompt **50,929 chars, ~12.7k tokens** (A0's own is 50,413 chars; the
delta is **+516 chars**) — which would overflow a 12288-token slot and make `B2` unflyable.
`-np 1` gives the single sequence the whole 49152 (worst-case sequence ~14.3k tokens), is
memory-neutral, and costs no throughput because `FrozenCoreClient` issues requests strictly
sequentially. `_apply_np_delta` fails closed if the fragment ever stops carrying exactly one
`-np 4` pair.

## Discipline held

- **No result read.** The launcher prints only request index, arm, sample id, latency,
  ok/fail and response LENGTH. `outputs.jsonl` is written and never opened. Stage-2's
  `outputs.jsonl` was likewise never opened — only its `arm-plan.json`.
- **Two hard operational ceilings** enforced before the request that would cross them:
  280 requests (counted on the TOTAL index, replays included) and 0.5 h of CUMULATIVE wall
  clock measured from llama-server spawn (`--prior-wall-seconds` carries an earlier attempt's
  spend into a resume, so the registered GPU-h ceiling stays honest).
- **Fail-closed resume**: every response appended to `responses.jsonl` keyed by request index
  and the sha256 of that request's own canonical messages; a replay whose rebuilt hash
  disagrees refuses rather than proceeding.
- **Completeness check** on the written rows (per-arm counts and distinct `(arm, sample_id)`
  pairs) without touching response content.

## For the read mission

- Run id `SAEA-PROBE-a2t-s2b-120`, attempt id `attempt-20260818T153859Z-8da515`.
- `outputs.jsonl` rows carry `{arm, sample_id, supplied_tool, response, timing}` — scoring is
  the read mission's job (`analysis.a2t_s2b_read`, `scripts/a2t_s2b_read.py`).
- The resolved arm construction is recorded in the run dir as
  `SAEA-PROBE-a2t-s2b-120.arm-plan.json`, carrying the reused Stage-2 arm-plan's path and
  sha256 alongside the per-sample `B1` rosters and `B2` wrong tools.
- Branch rules (Q-A: CONFIRMED-CUT / NOT-DEFAULTS / INCONCLUSIVE-A; Q-B: SCHEMA-CONTRIBUTES /
  KNOWLEDGE-TIED / INCONCLUSIVE-B plus the independent MISLEAD overlay) are in the
  preregistration, section 1.

## Files

- `launcher/` — the complete flight launcher, pre-flight, D1 probe and shells
- `preflight-split-measurement.json` — model-free plan construction, audio load and the
  measured per-arm prompt sizes
- `preflight-d1-probe.log` — D1 media identity PASS on all 120 plus negative control
- `preflight-tests.log` — the 28-test machinery suite
- `preflight.log` — the full pre-flight, green on every axis including the gate dry-run
- `flight.log` — the operational health log of the flight itself
- `gpu-health.log` — GPU samples before, during and after
- `flight-receipt.json` — status, hashes, per-arm counts, cost, wall, close receipt
- `execution-plan.json` / `config-values.json` / `session-receipt.json` — run identity, the
  llama.cpp binary sha256 and both GGUF sha256s
- `MANIFEST.sha256` — hashes of everything above
