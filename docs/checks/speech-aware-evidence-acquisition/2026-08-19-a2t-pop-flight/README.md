# P-A2T whole-population regression arm — FLIGHT RECEIPT (2026-08-19)

Registered probe `SAEA-PROBE-a2t-pop-194`, execution profile `bounded-discovery-probe`.
Preregistration: `docs/readiness/2026-08-19-a2t-pop-preregistration-REGISTERED.md` (adversarial-panel
Finding 3, refuter-corrected scoping). Machinery: `rails.probes.a2t_pop_flight` (flown at study
commit `c08c112`, tree clean throughout).

**This flight produced no read.** Every response row was written to `outputs.jsonl` for the
separately-registered one-shot read mission (`analysis.a2t_pop_read`) and was never opened, scored,
or interpreted here. Everything in this directory is operational or structural: request counts, arm
counts, latencies, hashes, cost. No response text, no EM value, no regression count.

| Field | Value |
|---|---|
| Run id | `SAEA-PROBE-a2t-pop-194` |
| Attempt | `attempt-20260819T162625Z-b3257c` |
| Status | `COMPLETED` (error `None`) |
| Run dir | `$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-a2t-pop-194/attempt-20260819T162625Z-b3257c` |
| Study commit | `c08c112`, tree clean at takeoff and at `client.close()` |
| Split identity | `e1d751e6c76e49d087620842ba17c34e432a4602169dc2b93ee7e0a529ca332c` (the frozen A2T 400 discovery split) |
| Config hash | `ae5b3d5e79bf83ba5dcceaafc42394e98c151d4da3650d9169eb09fba52b00ab` |
| Protocol hash | `48593086cd1ba2c3f2508ef2072d9d02c62e4208e5d63439eec7df0cb6d23d48` |
| Trace manifest hash | `bea4f8fe86b929dfed20a86b81f885e02ccda3911928de76aa5ebfe9c92ff4c7` |

## 1. No committed flight config — how identity was bound instead

Like its sibling abstention probe, this probe's machinery and preregistration landed in the
2026-08-19 wave **without** a `configs/probes/g0-binding/*.json` binding, and a flying agent must
not create one mid-session. Run identity was bound only from already-committed or already-frozen
sources: the machinery constants `A2T_POP_ARMS` / `EM_CORRECT_N` / `DEFAULT_SEED` /
`SPLIT_IDENTITY_HASH`, and the consumed A0 read's published artifact
`docs/checks/speech-aware-evidence-acquisition/2026-08-18-pa2t-a0-read/headroom.json` loaded through
the machinery's **own** `load_headroom_source` and checked by the machinery's **own** fail-closed
`assert_split_identity_hash_pinned`. The registered ceilings (220 / 2000 / 0.5) come from the
preregistration's section 4 and were cross-checked cell-by-cell against the live exposure-ledger row
for **equality** with the preregistration and **coverage** of the plan.

## 2. Roster derivation — the 97, sourced not curated

Preregistration section 2 forbids re-scoring or hand-curating this population: the roster is derived
by `derive_em_correct_ids`, which reuses `analysis.a2t_read.load_attempt_rows` / `score_row` — the
exact frozen scorer the Stage-2 headroom list itself was built on — over the **same** consumed A0
attempt `attempt-20260818T055500Z-res315`, filtering for the complementary predicate
`tool_accuracy == 1.0 AND exact_match == 1.0`. That is a read of an already-flown, already-consumed
attempt, not a new model contact, and this receipt records only counts.

| Quantity | Value |
|---|---|
| EM-correct roster derived | **97** ids — the machinery's fail-closed `expected_n=97` check passed |
| Deterministic across two independent derivations | yes (pre-flight ran it twice) |
| Overlap with the consumed 120-id headroom set | **0** — the EM==1 and EM==0 partitions are disjoint, as they must be |
| Population accounting | 97 EM-correct + 120 headroom = **217 tool-correct** of the frozen 400 |
| Excluded | **183 tool-selection failures** — EM cannot regress there and no gold-free supply-row rule exists for them (recorded limitation, prereg section 1, carried on every citation) |
| R1 supplied-tool count distribution | `{1 tool: 94 samples, 2 tools: 3}` |
| Distinct supplied tools across the 97 | 51 |
| R1 B1-form render size | 219–596 chars, versus the full 152-row registry's 50,291 — every R1 roster strictly shorter (machine-checked) |

R1's roster is the core's **own** A0-selected tool rendered B1-form with `argument_defaults`
stripped (`render_b1_tool_schemas`, the same rendering Stage-2b's B1 arm used). On this population
the A0 selection *is* the correct tool by the population's defining criterion, so R1 is
self-supplied, deployment-legal and gold-free. R0 is A0's own zero-supply request rebuilt
byte-identically through `Audio2ToolAdapter.assemble_prompt(sample, None)`.

## 3. Flight

One `llama-server` session, receipt-pinned binary, spawned as a child of this flight's own wrapper.

| Field | Value |
|---|---|
| Arms | `R0` (zero-supply re-fly comparator) then `R1` (self-supplied B1-form row), per sample |
| Requests | **194 flown, 0 replayed, 0 failed** |
| Rows by arm | `{"R0": 97, "R1": 97}`; 194 distinct (arm, sample_id) pairs |
| Supplied-tool labels | R1 97/97 set, R0 97/97 `None` — the arm semantics hold row-by-row |
| Mean latency | R0 0.685 s, R1 0.786 s |
| Throughput | ~81 req/min sustained |
| Flight wall | 2.4 min; GPU-occupied 3.8 min |
| llama-server argv | `-c 49152 -np 1 -fa on -ngl 999 -ctk q8_0 -ctv q8_0` — the standing A2T `-np 4 → 1` delta, needed because R0 *is* A0's own full-152-row request (~12.6k tokens) and overflows a 12288-token slot |
| Derived media | none — both arms send real audio, and the post-flight confirms no slice tree exists for this run id |

## 4. Spend against the registered ceilings

| Column | Planned | Spent | Registered ceiling | Headroom |
|---|---|---|---|---|
| Core calls | 210 | **194** | 220 | 26 |
| Metered speech-audio seconds | 1538 (derived) | **1092.78** | 2000 | 907.22 |
| GPU hours | 0.5 | **0.063** | 0.5 | 0.437 |

`planned_speech_audio_seconds` was **derived, not hand-typed**: 2 arms × the measured one-pass
546.39 s + 16 retries × this population's longest item 27.79 s = 1538, computed by `flight_plan.py`
from the model-free `split-measurement.json` and refused automatically if it had exceeded the
registered 2000. Prior durable spend on this run id was 0 at takeoff. Token accounting: 1,311,780
prompt / 4,567 completion; 0 tool calls.

## 5. Hygiene evidence

- **Runtime pins**: llama.cpp build commit `5d9dfcb58ea860295da8fc93c7b5bed9e2c71151`; binary sha256
  `097c96ec…c68` and both GGUF sha256 match the runtime receipt (verified this session — same
  binary, same machine; see the P-TRAP archive's `gguf-verify.log`).
- **Feature cache**: `audio2tool-q4km` held 490 entries before and **490** after, with an unchanged
  directory mtime, and the server log contains **zero** `encoding` lines — every one of the 194
  requests hit an already-encoded feature, as expected for a population entirely inside the frozen
  400 the A0 flight warmed. The legacy `q4km` cache (34,350 entries) and the `slurp-q4km` cache (63
  entries) were both untouched.
- **D3 gate**: `PYTHONDONTWRITEBYTECODE=1` throughout; zero `__pycache__`/`*.pyc` under the frozen
  scoring package.
- **Suite**: the full suite ran once at session start — **2846 passed, 9 skipped**
  (`preflight-pytest.log`, archived with the P-TRAP flight).
- **Processes**: no orphan `llama-server` before or after; the server was a child of this flight's
  own wrapper and exited with it.
- **Tree**: clean at `c08c112` at takeoff, during the flight, and at `client.close()`.

## 6. Scope note carried forward

This flight measures nothing on its own. When the registered read executes, its Δreg is a
**97-sample** statement about the EM-regression-eligible population only; the 183 tool-selection
failures are excluded by construction and the whole-population net account
(conversions [8,10]/120 − Δreg, over 400) must carry that exclusion on every citation. R0 doubles as
this population's first EM-stability measurement, which is why it flew in-session rather than being
cited from a prior arm.

## 7. Exposure ledger

Row `SAEA-PROBE-a2t-pop-194` keeps **`consumed = no`**. This flight spent the requests; the row is
consumed only when the single registered one-shot read executes. A FLOWN note recording this
attempt, its spend and its structural facts was appended to the row's own note cell.

## 8. Files

| File | What it is |
|---|---|
| `README.md` | this receipt |
| `launcher/` | every file that produced the flight (env, identity, plan, measurement, pre-flight, launcher, post-flight, wrappers) |
| `measure.log` | the model-free split measurement and roster derivation |
| `split-measurement.json` | the derived 97-id roster, measured audio load, R1 render sizes |
| `preflight.log` | pre-flight (split identity, roster fail-closed check, disjointness, media, R1 invariants, ledger, budgets) |
| `flight.log` | operational flight log (request index, arm, latency, response LENGTH only) |
| `postflight.log` | post-flight structural verification |
| `arm-plan.json` | the resolved per-sample R1 tool names and the excluded-population note |
| `flight-receipt.json` | the launcher's own receipt (identity, cost, per-arm counts, session pins) |
| `execution-plan.json` | the validated `ExecutionPlan` |
| `config-values.json` | the hashed config values bundle |
| `session-receipt.json` | the llama-server session receipt |
| `MANIFEST.sha256` | sha256 over every file above |
