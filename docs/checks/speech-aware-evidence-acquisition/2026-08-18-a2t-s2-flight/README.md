# P-A2T Stage-2 supply probe — FLOWN

Date: 2026-08-18. Run id: `SAEA-PROBE-a2t-s2-120`. Profile: `bounded-discovery-probe`.
Status: **FLOWN — all four arms complete. NO RESULT HAS BEEN READ.**

This is the flight receipt for the registered Stage-2 supply probe
(`docs/readiness/2026-08-18-pa2t-stage2-preregistration-REGISTERED.md`): on the 120
Audio2Tool samples where the frozen core already selects the correct tool but fails the
full call, does prompt-level supply of tool-schema knowledge convert failures into exact
matches — and is the effect knowledge or format?

The exposure row `SAEA-PROBE-a2t-s2-120` **stays `consumed=no`**. Reading these outputs is
a separately-registered one-shot read mission with its own pinned, pre-reviewed read suite;
this flight wrote `outputs.jsonl` and never opened it.

## What flew

| Arm | Supply (prompt-level, per sample) | n | requests |
|---|---|---|---|
| `S1p` | self-supplied roster: the registry row(s) of the tool(s) the core ITSELF named in its own A0 response | 120 | 120 |
| `S2` | diluted: correct row(s) + seeded distractors, total roster fixed at 9 | 120 | 120 |
| `S4` | deranged: exactly ONE wrong tool's row, fixed-point-free Sattolo mapping over tool identity | 120 | 120 |
| `N0r` | noise floor: zero-supply re-fly (full 152-row registry, byte-identical to A0) | 40 | 40 |

Seed `20260807` throughout. Order per sample: S1p, S2, S4 over the 120 sorted headroom ids,
then the 40 N0r requests.

## Flight outcome

One attempt, no resume needed, exit 0.

| | |
|---|---|
| Attempt id | `attempt-20260818T124955Z-84b944` |
| Run dir | `$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-a2t-s2-120/attempt-20260818T124955Z-84b944` |
| Status | `COMPLETED` |
| Requests flown | **400 / 400** — 0 failures, 0 retries, 0 replays |
| Rows written | `outputs.jsonl` **400** rows: `S1p` 120, `S2` 120, `S4` 120, `N0r` 40 (matches the registration exactly; 400 distinct `(arm, sample_id)` pairs) |
| Wall (flight loop) | 4.6 min (12:52:14Z → 12:56:51Z) |
| Wall (GPU-occupied, from llama-server spawn) | 6.9 min = **0.116 h** of the 1.0 h ceiling |
| Calls metered | **400** of the 420 planned / 450 registered |
| Speech audio metered | **2110.47 s** of the 3000 planned / 3500 registered |
| Throughput | ~86–115 req/min (peak 115), mean 0.61 s/request over the whole flight |
| Mean latency by arm | `S4` 0.334 s, `S1p` 0.615 s, `S2` 0.974 s, `N0r` 1.061 s |
| Tokens | prompt 699,303; completion 11,875 |
| Trace manifest hash | `9db80af6b47a59111e1641124732ae5bf82105b6dddbeb447a53ee9f28c6ed87` |
| Umbrella lock sha256 (returned by the gate) | `b588f3641ae1d1774fb7652c8978acf25eda7dcbc45a34a898d5471bce5b2e42` |
| Feature cache delta | **zero** — 480 entries / 243 M before and after, 0 encode lines in the server log across all 400 requests |
| GPU | idle P8/180 MHz before; P2–P4 / 232 MHz, 92–98 % util, 59–86 W, 58–60 °C during; back to idle P8/180 MHz, 381 MiB after |

Throughput ran ~9x the Stage-1 A0 baseline (86–115 req/min vs A0's measured 10.5): three of
the four arms carry 1–9 registry rows instead of all 152, the audio feature cache was fully
warm from A0, and `N0r`'s identical 152-row prefix hit llama-server's longest-common-prefix
slot cache on all 40 requests (mean 1.06 s despite a ~12.6k-token prefill). The registered
1.0 GPU-h ceiling was never approached: the flight used 11.6 % of it.

### For the read mission

- Run id `SAEA-PROBE-a2t-s2-120`, attempt id `attempt-20260818T124955Z-84b944`.
- `outputs.jsonl` rows carry `{arm, sample_id, supplied_tool, response, timing}` — scoring
  is the read mission's job, exactly as `analysis.a2t_read` scores an already-written
  attempt.
- The seeded arm construction is recorded in the run dir as
  `SAEA-PROBE-a2t-s2-120.arm-plan.json` (per-sample S1p/S2 rosters, the S4 derangement and
  the N0r draw) and is independently reproducible from `(headroom, seed 20260807, registry)`.
- The A0 comparator is the consumed read at `ec25706`
  (`2026-08-18-pa2t-a0-read/`, attempt `attempt-20260818T055500Z-res315`).

## Pre-flight (all model-free, all green)

| Precondition | Result |
|---|---|
| Tree clean for the whole run | clean at `15bee10` before launch, during flight, and at finalize |
| Bytecode hygiene | 0 `.pyc` under `src/`; `PYTHONDONTWRITEBYTECODE=1` in `launcher/env.sh` |
| Suite sanity | `tests/unit/test_a2t_s2_flight.py` + `test_a2t_s2_flight_config.py` — **52 passed** |
| Headroom manifest | 120 ids, schema `saea-a2t-a0-headroom-v1`, attempt dir `attempt-20260818T055500Z-res315` |
| S1' tool source | DERIVED from the consumed A0 attempt's own `outputs.jsonl` via `analysis.a2t_read.load_attempt_rows` + `reproduction.toolcall_scoring.parse_tool_calls_text` — never gold, never a new contact. 120/120 derived; 45 samples carry >1 distinct tool (the tier3/tier8 multi-intent minority) |
| Arm construction | S4 derangement over **54 distinct tool identities**, 0 fixed points, **0** samples supplied one of their own selections; S2 roster sizes exactly `{9: 120}`; S1p roster sizes `{1: 75, 2: 27, 3: 18}` |
| N0r draw | 40 ids, tier-proportional largest-remainder: 8/6/9/1/4/4/3/5 over tiers 1–8 (headroom 23/17/29/3/12/12/8/16) |
| Split identity | receipt hash `e1d751e6…332c` matches the flight config, the headroom manifest and the ledger cell verbatim (64-hex) |
| Media | 120/120 headroom media present, 24000 Hz uniform |
| D1 media identity | `verify_media_identity('audio2tool')` **PASS** on all 120 headroom samples; unlisted sample id correctly refused (`GateClosed`) |
| Exposure row | exactly 1 row, `consumed=no`, `bounded-discovery-probe` / `discovery`, registers 450 / 3500 / 1.0 |
| ExecutionPlan | validates as `bounded-discovery-probe` / `discovery`, calls 420 / audio 3000 s / 1.0 GPU-h; config hash `c8d05b6f…`, protocol hash `ae3744a8…` |
| Payload binding | builds over the 120 headroom ids only (tighter than the full 400) |
| Gate dry-run | **AUTHORIZED** (umbrella lock sha256 `b588f364…`) |
| Feature cache | `/home/chao/feat-cache/audio2tool-q4km` **warm from the A0 flight**: 480 entries / 243 M before launch |

## Metered audio: 3 passes, not 1

Every `S1p`/`S2`/`S4` request re-sends its sample's own audio, so the metered load is
`3 x 635.28` (one pass over the 120) `+ 204.62` (the N0r 40) = **2110.47 s**, not one pass.
The plan carries 3000 s (refined DOWN from the registered 3500): the worst case inside the
420-call budget is 2110.47 + 20 retries each bounded by the headroom set's own longest item
(35.71 s) = 2824.7 s, so 3000 is the smallest round ceiling that cannot be crossed before
the call budget stops the run.

## The `-np 1` delta still applies

The committed model fragment carries `-c 49152 -np 4` = **12288 tokens per slot**. Three of
this probe's four arms carry narrowed rosters (S1p ~410–1270 chars, S2 ~2800–3570, S4
~370–575), but `N0r` is a byte-identical zero-supply re-fly carrying the FULL 152-row
registry — **50,413 chars, ~12.6k estimated tokens** before audio and before output — which
would overflow a 12288-token slot and make the noise-floor arm unflyable. `-np 1` gives the
single sequence the whole 49152 (worst-case sequence ~14.1k tokens), is memory-neutral, and
costs no throughput because `FrozenCoreClient` issues requests strictly sequentially.
`_apply_np_delta` fails closed if the fragment ever stops carrying exactly one `-np 4` pair.

## Discipline held

- **No result read.** The launcher prints only request index, arm, sample id, latency,
  ok/fail and response LENGTH. `outputs.jsonl` is written and never opened.
- **Two hard operational ceilings** enforced before the request that would cross them:
  450 requests (counted on the TOTAL index, replays included) and 1.0 h of CUMULATIVE wall
  clock measured from llama-server spawn (`--prior-wall-seconds` carries an earlier
  attempt's spend into a resume, so the registered GPU-h ceiling stays honest).
- **Fail-closed resume**: every response appended to `responses.jsonl` keyed by request
  index and the sha256 of that request's own canonical messages; a replay whose rebuilt
  hash disagrees refuses rather than proceeding.
- **Completeness check** on the written rows (per-arm counts and distinct `(arm, sample_id)`
  pairs) without touching response content.

## Files

- `launcher/` — the complete flight launcher, pre-flight, D1 probe, measurement and shells
- `preflight-split-measurement.log` / `.json` — model-free plan construction and audio load
- `preflight-d1-probe.log` — D1 media identity PASS on all 120 plus negative control
- `preflight-tests.log` — the 52-test machinery suite
- `preflight.log` — the full pre-flight, green on every axis including the gate dry-run
- `flight.log` — the operational health log of the flight itself
- `gpu-health.log` — GPU samples before, during and after
- `flight-receipt.json` — status, hashes, per-arm counts, cost, wall, close receipt
- `execution-plan.json` / `config-values.json` / `session-receipt.json` — run identity,
  the llama.cpp binary sha256 and both GGUF sha256s
- `MANIFEST.sha256` — hashes of everything above
