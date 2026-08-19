# P-TRAP self-percept trap probe — FLIGHT RECEIPT (2026-08-19)

Registered probe `SAEA-PROBE-ptrap-120`, execution profile `bounded-discovery-probe`.
Preregistration: `docs/readiness/2026-08-19-ptrap-preregistration-REGISTERED.md` (including its
2026-08-19 section-6 calibration amendment). Committed binding:
`configs/probes/g0-binding/ptrap-flight.json`. Machinery:
`rails.probes.ptrap_flight` (flown at study commit `3ab9e9b`, tree clean throughout).

**This flight produced no read.** Every response row was written to `outputs.jsonl` for the
separately-registered one-shot read mission (`analysis.ptrap_read`) and was never opened, scored, or
interpreted here. Everything in this directory is operational or structural: request counts, K
counts, latencies, hashes, cost. No response text, no capture flag, no verdict.

| Field | Value |
|---|---|
| Run id | `SAEA-PROBE-ptrap-120` |
| Attempt | `attempt-20260819T155046Z-98efbd` |
| Status | `COMPLETED` (error `None`) |
| Run dir | `$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-ptrap-120/attempt-20260819T155046Z-98efbd` |
| Study commit | `3ab9e9b`, tree clean at takeoff and at `client.close()` |
| Split identity | `fc9de436eba5aba120ecf07ee112765cd4ac0609150e0aaf36f4d44c9c5b5ee5` (the SAME frozen 60 SLURP devel samples the consumed P-SLU/P-KEY flights used) |
| Config hash | `75b5b0be185718ac45c526786b00be52f89b175307b3ac1830f477fe2d84256b` |
| Protocol hash | `5af8033b8574023ec8e6319c127b8086b8f4209105e11ca275b57bc722965f37` |
| Trace manifest hash | `6ff81cea4151add64b951a62f04b2a9167b7fdd41c7d4438f865bcceeac890b1` |
| Trap binding hash | `cc80ffd0b7b538dbc515911702b045b9b701e9858cef29dd3c1592473fe4c19c` |

## 1. Binding phase (offline, zero model calls)

The preregistration makes the trap CONTENT itself derived data: every appended roster entry is one
of the core's OWN model-generated wrong values from the consumed zero-supply A0 attempt. Sourcing it
is therefore the registered binding step, not a result read. The chain the committed flight config's
`phases.binding` prescribes ran verbatim:

```
analysis.ptrap_read.harvest_a0_wrong_values(
    $SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pslu-n60/attempt-20260818T010218Z-4c97cb,
    analysis.pslu_read.load_gold_by_sample_id(...))
  -> rails.probes.ptrap_flight.build_trap_sets(k_cap=5, seed=20260807)
```

The binding is deterministic from `(consumed attempt, seed)`: `binding.py` produced it once as its
own reviewable step, the pre-flight re-derived it and matched the hash, and the launcher re-derived
it a third time and **refused to fly unless its hash equalled the reviewed one**. All three agree at
`cc80ffd0…`.

Structural result (`trap-binding-stats.json`, full table in the attempt dir's `trap-binding.json`,
which carries model-generated text and stays outside Git):

| Quantity | Value |
|---|---|
| Samples | 60 |
| A0 wrong values harvested (total, deduplicated per sample) | 91 |
| Samples whose A0 response emitted ZERO wrong values | 5 |
| Candidates dropped by the fail-closed gold zero-overlap check | **42 (V1), 8 (V2)** |
| V1 appended entries actually flown | 49 |
| V2 appended entries actually flown | 49 |
| V1 K distribution (K → n samples) | `{0: 28, 1: 18, 2: 11, 3: 3}` |
| V2 K distribution (K → n samples) | `{0: 28, 1: 18, 2: 11, 3: 3}` |
| **K = 0 samples (excluded from the capture denominator)** | **28** |
| **Common denominator (V1 K ≥ 1)** | **32** |
| Samples where V2 was shorter than V1 (donor pool dry) | 0 |
| V2 donor breadth | 31 distinct origin samples across 49 entries |

Two facts the read mission must carry. First, the K=0 exclusion is much larger than the harvest
alone suggests: only 5 samples produced no wrong value at all, but the gold zero-overlap check —
the preregistration's own hard rule that no appended entry may equal (post-normalization) any gold
slot value of its target sample, across any type — removed a further 42 V1 candidates, leaving
**28 of 60 samples with K=0** and a **common denominator of 32**. Second, the registered raw-difference
floor for ACOUSTIC-MEDIATED (≥ 6) is therefore evaluated against 32, not 60; the pre-read
reachability statement section 6 mandates is where that has to be stated, and this receipt supplies
its ingredients rather than pre-empting it.

Binding invariants, all machine-checked twice (pre-flight, then again by
`validate_ptrap_flight_summary` at the end of the flight over the rows actually produced):

- no V1 K exceeds `TRAP_K_CAP` = 5 (observed max 3);
- no V2 K exceeds that same sample's own V1 K (length-matched; 0 shrinks);
- every V2 entry is fixed-point-free (`origin_sample_id` ≠ its target), by pool construction;
- every V1 entry's `origin_sample_id` equals its own target (the self-percept property);
- no appended entry — V1 or V2 — equals a gold slot value of its own target sample.

## 2. Flight

One `llama-server` session, receipt-pinned binary, spawned as a child of this flight's own wrapper.

| Field | Value |
|---|---|
| Arms | `V1` (self-percept trap) then `V2` (cross-percept control), per sample |
| Requests | **120 flown, 0 replayed, 0 failed** |
| Rows by arm | `{"V1": 60, "V2": 60}`; 120 distinct (arm, sample_id) pairs |
| Per-arm K distribution in `outputs.jsonl` | V1 `{0:28, 1:18, 2:11, 3:3}`, V2 `{0:28, 1:18, 2:11, 3:3}` — identical to the binding |
| Base roster | the frozen A3-form 100-entry train-only roster, reused byte-identically |
| Mean latency | V1 1.048 s, V2 1.038 s |
| Flight wall | 2.1 min; GPU-occupied 4.0 min |
| llama-server argv | `-c 49152 -np 4 -fa on -ngl 999 -ctk q8_0 -ctv q8_0` — the committed fragment's own, UNCHANGED (no `-np 1` delta: a 100+K-entry roster fits a 12288-token slot, and the registration pins the decode config to the consumed P-SLU flights) |

## 3. Spend against the registered ceilings

| Column | Planned | Spent | Registered ceiling | Headroom |
|---|---|---|---|---|
| Core calls | 120 | **120** | 140 | 20 |
| Metered speech-audio seconds | 1000 | **364.52** | 1000 | 635.48 |
| GPU hours | 0.3 | **0.066** | 0.3 | 0.234 |

Prior durable spend on this run id was 0 at takeoff, so the run-total feasibility check passed with
full headroom. Token accounting: 88,955 prompt / 7,815 completion; 0 tool calls.

## 4. Hygiene evidence

- **Runtime pins**: llama.cpp build commit `5d9dfcb58ea860295da8fc93c7b5bed9e2c71151`; binary sha256
  `097c96ec…c68` matches the receipt pin and the Stage-2 precedent pin; both GGUF files match their
  receipt pins byte-count and sha256 (`gguf-verify.log`).
- **Feature cache**: `/home/chao/feat-cache/slurp-q4km` held 63 entries before and 63 after, with an
  UNCHANGED directory mtime (2026-08-17), and the server log contains **zero** lines matching
  `encoding` — the campaign's standing proof that every audio feature was a cache hit. The legacy
  `q4km` cache (34,350 entries) and the `audio2tool-q4km` cache (480 entries) were both untouched.
- **D3 gate**: `PYTHONDONTWRITEBYTECODE=1` throughout; zero `__pycache__`/`*.pyc` under the frozen
  scoring package before and after.
- **Suite**: the full suite ran once at session start — **2846 passed, 9 skipped**
  (`preflight-pytest.log`).
- **Processes**: no orphan `llama-server` before or after; the server was a child of this flight's
  own wrapper and exited with it.
- **Tree**: clean at `3ab9e9b` at takeoff, during the flight, and at `client.close()`.

## 5. Exposure ledger

Row `SAEA-PROBE-ptrap-120` keeps **`consumed = no`**. This flight spent the requests; the row is
consumed only when the single registered one-shot read executes. A FLOWN note recording this
attempt, its spend and its binding hash was appended to the row's own note cell.

## 6. Files

| File | What it is |
|---|---|
| `README.md` | this receipt |
| `launcher/` | every file that produced the flight (env, binding, identity, pre-flight, launcher, post-flight, wrappers) |
| `session-precheck.log` | session-start environment probe (GPU, caches, orphans, disk) |
| `preflight-pytest.log` | the full suite, run once for all three probes in this session |
| `binding.log` | the offline binding step's own output |
| `trap-binding-stats.json` | STRUCTURAL binding record (K distribution, K=0 ids, exclusion counts). The full trap table carries model-generated text and stays in the attempt dir, never in Git |
| `preflight.log` | pre-flight (split identity, roster, media, binding invariants, ledger, budgets) |
| `gguf-verify.log` | binary + per-file GGUF sha256 against the runtime receipt |
| `flight.log` | operational flight log (request index, arm, latency, response LENGTH only) |
| `postflight.log` | post-flight structural verification |
| `flight-receipt.json` | the launcher's own receipt (identity, cost, per-arm counts, binding stats, session pins) |
| `execution-plan.json` | the validated `ExecutionPlan` |
| `config-values.json` | the hashed config values bundle |
| `session-receipt.json` | the llama-server session receipt |
| `MANIFEST.sha256` | sha256 over every file above |
