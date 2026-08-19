# P-FEW routing few-shot form probe — FLIGHT RECEIPT (2026-08-19)

Registered probe `SAEA-PROBE-pfew-180`, execution profile `bounded-discovery-probe`.
Preregistration: `docs/readiness/2026-08-19-pfew-preregistration-REGISTERED.md`. Machinery:
`rails.probes.pfew_flight` (flown at study commit `2c09392`, tree clean throughout).
Arc: probe 1 of the routing-tier × filling-tier program (2026-08-19 owner second-arc design order).

**This flight produced no read.** Every response row was written to `outputs.jsonl` for the
separately-registered one-shot read mission (`analysis.pfew_read`) and was never opened, scored, or
interpreted here. Everything in this directory is operational or structural: request counts, demo
counts, latencies, hashes, cost. No response text, no mapped label, no accuracy, no verdict.

| Field | Value |
|---|---|
| Run id | `SAEA-PROBE-pfew-180` |
| Attempt | `attempt-20260819T233312Z-480fed` |
| Status | `COMPLETED` (error `None`) |
| Run dir | `$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pfew-180/attempt-20260819T233312Z-480fed` |
| Study commit | `2c09392`, tree clean at takeoff and at `client.close()` |
| Split identity | `fc9de436eba5aba120ecf07ee112765cd4ac0609150e0aaf36f4d44c9c5b5ee5` (the SAME frozen 60 SLURP devel samples the consumed P-SLU/P-KEY/P-TRAP flights used) |
| Config hash | `c7b49eed72b86ab2daa9302a2e2c58dea26b7835a0ed0001cc89595b85370f92` |
| Protocol hash | `d67887ba618632fa0c9f4007ed52562e9ffdb9d8953ac467374aefdbd4ca4cef` |
| Trace manifest hash | `ad630a506346de77ae619a701d104a33828f8ed2b185c0ecfa21dd2be597b7ae` |
| Demo binding sha256 | `b0479cf63d168f1575b2aaf95c8dd3d902ccdc444639d5e279a74be876627b8b` |

No committed `configs/probes/g0-binding` flight config exists for this probe: the 2026-08-19
second-arc registration wave landed the preregistration, the machinery and the pinned read suite
without one, and a flying agent must not create one mid-session (it would dirty the tree for the
whole flight). Every identity and budget value the launcher used is therefore sourced from a place
that was already committed — the machinery's own module constants, the frozen sample manifest and
roster table, and the exposure-ledger row's own registered ceilings — exactly the documented
arrangement the archived P-A2T whole-population launcher used. See `launcher/flight_identity.py`.

## 1. Binding phase (offline, zero model calls)

Preregistration section 2 fixes the demo assignments per sample at binding and hash-pins them;
section 5 requires TRAIN-split-only demo content under a binding-time fail-closed devel-exclusion
check. The chain ran verbatim:

```
rails.probes.pfew_flight.load_train_demo_pool(lock, root)     # raw governed train.jsonl, TEXT ONLY
  -> rails.probes.pfew_flight.build_demo_binding(seed=20260807)
```

`load_train_demo_pool` opens no audio file and never reads `devel`/`test`/`train_synthetic`; it
reads the same raw `train.jsonl` the legal roster table was itself mined from, because
`data.slurp.SlurpRecord` deliberately excludes sentence text.

The binding is deterministic from `(train pool, canonical labels, target sample set, seed)`:
`binding.py` produced it once as its own reviewable step, the pre-flight re-derived it and matched,
and the launcher re-derived it a third time and **refused to fly unless the machinery's own
`DemoBinding.sha256` equalled the reviewed one**. All three agree at `b0479cf6…`.

Structural result (`demo-binding-stats.json`; the full per-sample table carries TRAIN transcript
text and stays in the attempt dir's `demo-binding.json`, outside Git):

| Quantity | Value |
|---|---|
| Samples | 60 |
| Canonical scenario labels | 18 (roster-table keys, never the ceiling-tier ontology miner) |
| **Seeded GLOBAL skew label** | **`audio`** |
| FS-NONE demos per sample | 0 |
| FS-BAL demos per sample | 4, all four labels distinct on every one of the 60 |
| FS-SKEW demos per sample | 4, all four carrying `audio` on every one of the 60 |
| FS-BAL demo slots filled | 240 from **236 distinct TRAIN donors** |
| FS-SKEW demo slots filled | 240 from **165 distinct TRAIN donors** |
| FS-BAL label usage across the 240 slots | `alarm 15, audio 13, calendar 9, cooking 9, datetime 14, email 13, general 20, iot 14, lists 11, music 12, news 11, play 13, qa 11, recommendation 17, social 16, takeaway 14, transport 14, weather 14` |
| TRAIN pool coverage | all 18 canonical labels have ≥ 211 candidates (min `cooking` 211, max `calendar` 1688) |

**The skew label was chosen before any gold was read.** The preregistration's wording is
"the SAME seeded wrong-for-most-samples label"; a per-sample "wrong for THIS sample" choice would
require that sample's own gold scenario at binding time, which the study's research boundary
forbids. The registered legal resolution `build_demo_binding` implements — and which this flight
executed — is one seeded label drawn once, globally, from the 18 canonical labels with zero gold
input. It landed on `audio`. For whichever samples `audio` happens to *be* the gold scenario, the
capture concept is undefined, and the pinned read suite's own `compute_skew_capture` excludes them
from its denominator as disclosed accounting. This flight does not know, and did not look up, how
many those are.

Binding invariants, all machine-checked twice (pre-flight, then again by
`validate_pfew_flight_summary` at the end of the flight over the rows actually produced):

- every FS-BAL row carries exactly 4 demos with 4 distinct canonical labels;
- every FS-SKEW row carries exactly 4 demos, all under the one global skew label;
- every demo id is TRAIN-namespaced (`slurp:train:NNNNNN`);
- every demo label lies inside the canonical 18;
- **no demo's `slurp_id` collides with a target devel utterance id** — the fail-closed
  devel-exclusion check, re-run in the pre-flight independently of `build_demo_binding`'s own copy.

## 2. Supply composition (verified offline before the first request)

| Arm | Template | Items | Prompt chars |
|---|---|---|---|
| `FS-NONE` | `pslu-s2-a1r-phase1-closed-set-v1` | 0 | 432 |
| `FS-BAL` | `pfew-FS-BAL-fewshot-v1` | 4 | 743 |
| `FS-SKEW` | `pfew-FS-SKEW-fewshot-v1` | 4 | 734 |

FS-NONE's prompt block is **byte-identical** to the reused A1′r closed-set phase-1 packet
(`rails.probes.pslu_s2_flight.closed_set_phase1_supply_packet`), and both few-shot arms *prepend*
their demo block ahead of that same reused instruction text rather than re-typing it — both checked
in the pre-flight. Single-phase throughout: this probe measures the ROUTER, so no phase-2 supply
was ever assembled.

## 3. Flight

One `llama-server` session, receipt-pinned binary, spawned as a child of this flight's own wrapper.

| Field | Value |
|---|---|
| Arms | three contiguous blocks: `FS-NONE` → `FS-BAL` → `FS-SKEW`, 60 samples each |
| Requests | **180 flown, 0 replayed, 0 failed** |
| Rows by arm | `{"FS-BAL": 60, "FS-NONE": 60, "FS-SKEW": 60}`; **180 distinct (arm, sample_id) pairs** |
| Demo counts in `outputs.jsonl` | FS-NONE `{0: 60}`, FS-BAL `{4: 60}`, FS-SKEW `{4: 60}` — identical to the binding |
| Mean latency | FS-NONE 0.801 s, FS-BAL 0.808 s, FS-SKEW 0.825 s |
| Throughput | ~71 req/min |
| Flight wall | 2.5 min; GPU-occupied 6.4 min (server spawn+load 21.8 s) |
| llama-server argv | `-c 49152 -np 4 -fa on -ngl 999 -ctk q8_0 -ctv q8_0` — the committed fragment's own, UNCHANGED (the s2/P-TRAP precedent; nothing here approaches the 12288-token per-slot budget, and the registration pins the decode config to the consumed P-SLU flights) |
| Decoding params | `{"temperature": 0, "seed": 20260803, "max_tokens": 1024}` (the batch-executor-only `id_slot` sentinel dropped, as in every sibling rails flight) |

## 4. Spend against the registered ceilings

| Column | Planned | Spent | Registered ceiling | Headroom |
|---|---|---|---|---|
| Core calls | 180 | **180** | 200 | 20 |
| Metered speech-audio seconds | 700 | **546.78** | 700 | 153.22 |
| GPU hours | 0.25 | **0.106** | 0.25 | 0.144 |

Metered audio is 182.26 s (one pass over the frozen 60 — the identical figure the consumed
P-SLU/P-KEY/P-TRAP passes recorded) × 3 arms = 546.78 s. Prior durable spend on this run id was 0
at takeoff, so the run-total feasibility check passed with full headroom. Token accounting:
53,466 prompt / 6,716 completion; 0 tool calls.

## 5. Hygiene evidence

- **Runtime pins**: llama.cpp build commit `5d9dfcb58ea860295da8fc93c7b5bed9e2c71151`; binary sha256
  `097c96ec…c68` matches the receipt pin; both GGUF files match their receipt pins on byte count and
  sha256 (`gguf-verify.log`).
- **Feature cache**: `/home/chao/feat-cache/slurp-q4km` held 63 entries before and 63 after, with an
  UNCHANGED directory mtime (2026-08-17), and the server log contains **zero** lines matching
  `encoding` — the campaign's standing proof that every audio feature was a cache hit. The legacy
  `q4km` cache (34,350 entries) and the `audio2tool-q4km` cache (490 entries) were both untouched.
- **D3 gate**: `PYTHONDONTWRITEBYTECODE=1` throughout; zero `__pycache__`/`*.pyc` under the frozen
  scoring package before and after.
- **Suite**: the full suite ran once at session start — **3008 passed, 9 skipped**
  (`preflight-pytest.log`).
- **Processes**: no orphan `llama-server` before or after; the server was a child of this flight's
  own wrapper and exited with it, GPU memory back to 18 MiB.
- **Tree**: clean at `2c09392` at takeoff, during the flight, and at `client.close()`. A parallel
  session was observed running `pytest -q` (read-only) during the flight; the tree stayed clean.

## 6. Exposure ledger

Row `SAEA-PROBE-pfew-180` keeps **`consumed = no`**. This flight spent the requests; the row is
consumed only when the single registered one-shot read (`analysis.pfew_read`) executes. A FLOWN note
recording this attempt, its spend and its demo-binding hash was appended to the row's own note cell.

## 7. Files

| File | What it is |
|---|---|
| `README.md` | this receipt |
| `launcher/` | every file that produced the flight (env, binding, identity, pre-flight, launcher, post-flight, wrappers) |
| `session-precheck.log` | session-start environment probe (GPU, caches, orphans, disk) |
| `preflight-pytest.log` | the full suite, run once for all three probes in this session |
| `binding.log` | the offline binding step's own output |
| `demo-binding-stats.json` | STRUCTURAL binding record (K distributions, label usage, donor breadth, pool coverage). The full per-sample demo table carries TRAIN transcript text and stays in the attempt dir, never in Git |
| `preflight.log` | pre-flight (split identity, roster, media, binding invariants, packet composition, ledger, budgets) |
| `gguf-verify.log` | binary + per-file GGUF sha256 against the runtime receipt |
| `flight.log` | operational flight log (request index, arm, latency, response LENGTH only) |
| `postflight.log` | post-flight structural verification |
| `flight-receipt.json` | the launcher's own receipt (identity, cost, per-arm counts, binding stats, session pins) |
| `execution-plan.json` | the validated `ExecutionPlan` |
| `config-values.json` | the hashed config values bundle |
| `session-receipt.json` | the llama-server session receipt |
| `MANIFEST.sha256` | sha256 over every file above |
