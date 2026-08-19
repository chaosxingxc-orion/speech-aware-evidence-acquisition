# P-A2T abstention-asymmetry 2×2 — FLIGHT RECEIPT (2026-08-19)

Registered probe `SAEA-PROBE-a2t-abst-44`, execution profile `bounded-discovery-probe`.
Preregistration: `docs/readiness/2026-08-19-a2t-abst-preregistration-REGISTERED.md`. Machinery:
`rails.probes.a2t_abst_flight` (flown at study commit `b748ae5`, tree clean throughout).

**This flight produced no read.** Every response row was written to `outputs.jsonl` for the
separately-registered one-shot read mission (`analysis.a2t_abst_read`) and was never opened, scored,
or interpreted here. Everything in this directory is operational or structural: request counts,
cell counts, latencies, hashes, cost. No response text, no abstention flag, no verdict.

| Field | Value |
|---|---|
| Run id | `SAEA-PROBE-a2t-abst-44` |
| Attempt | `attempt-20260819T160757Z-9425ce` |
| Status | `COMPLETED` (error `None`) |
| Run dir | `$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-a2t-abst-44/attempt-20260819T160757Z-9425ce` |
| Study commit | `b748ae5`, tree clean at takeoff and at `client.close()` |
| Split identity | `e1d751e6c76e49d087620842ba17c34e432a4602169dc2b93ee7e0a529ca332c` (the frozen A2T 400 discovery split) |
| Config hash | `9b363f920c490d40e08507b29eac7cf5aea70f40703d21fe6d6f7b6395e46778` |
| Protocol hash | `47c502be32601b35c7166d40cc1ad03bef88bc85ce061da301c3bd19f05a7668` |
| Trace manifest hash | `75979faa4d29a1a318ffdb551c374216cd0cdfdf0bbe6a04cff433779cdcf4d3` |

## 1. No committed flight config — how identity was bound instead

The 2026-08-19 registration wave landed this probe's machinery and preregistration **without** a
`configs/probes/g0-binding/*.json` binding, and a flying agent must not create one mid-session (it
would dirty the tree for the whole flight — the same reason the Stage-2c precedent gives for not
composing config fragments). Every probe-identity value in this flight's hashed `values` bundle was
therefore sourced from something already committed or already frozen, never hand-typed policy:

- machinery constants `A2T_ABST_CELLS`, `ABST_N`, `DEFAULT_SEED` — the cells, the draw size, the seed;
- the consumed A0 read's published artifact
  `docs/checks/speech-aware-evidence-acquisition/2026-08-18-pa2t-a0-read/headroom.json` — the 120-id
  headroom list, the consumed A0 `attempt_dir`, and the split identity hash (the same literal path
  every committed A2T flight config carries under `headroom_manifest`);
- `rails.probes.a2t_pop_flight.SPLIT_IDENTITY_HASH` — the committed pinned constant the artifact's
  own hash is checked against, fail-closed, so a drifted artifact cannot silently redefine the split.

The registered ceilings (60 / 500 / 0.15) come from the preregistration's section 3 and are
cross-checked cell-by-cell against the live exposure-ledger row by the pre-flight, which requires
**equality** with the preregistration and **coverage** of the plan.

## 2. Draw, tool-removal plan and silence swaps

Seeded flat draw (`seeded_abst_draw`, seed 20260807, n=11) over the frozen 120-id headroom list,
deterministic across repeated derivation and fully inside that list:

```
tier1_direct:001242            tier3_multi_intent:001251      tier3_multi_intent:003153
tier1_direct:001607            tier3_multi_intent:002915      tier7_multiturn:000554
tier3_multi_intent:000078      tier3_multi_intent:002986      tier8_intent_blending:000065
tier3_multi_intent:000419                                     tier8_intent_blending:000696
```

Structural note the read should carry: the registered draw is **flat, not tier-stratified**, and
this particular seed landed 6 of 11 on `tier3_multi_intent` (which holds 29 of the 120 headroom
ids), 2 on `tier1_direct`, 2 on `tier8_intent_blending`, 1 on `tier7_multiturn`. Four of the eight
A0 tiers are unrepresented. That is the registered design at n=11, not a defect — but any
cell-rate read at this n is a tier3-weighted sample and should say so.

**Tool-removal render (TW cells)**: every sample's correct tool came from
`derive_a0_selected_tools` over the consumed A0 attempt `attempt-20260818T055500Z-res315`
(self-supplied, deployment-legal, gold-free — on headroom ids the core's own A0 selection *is* the
correct tool by that set's defining criterion). Correct-tool count distribution `{1 tool: 3 samples,
2 tools: 4, 3 tools: 4}`, 14 distinct withheld tools. Every TW registry render is strictly shorter
than the full 152-row render (49,176–49,989 chars vs 50,291) — the machine check that the removal
actually removed something and nothing else changed. All 22 TW rows carry a withheld-tool label; the
22 TP rows carry none, as the cell semantics require.

**Silence swaps**: all 11 built through the established
`rails.silence_swap.build_silence_swap_slice` + `FrozenCoreClient.register_slice` path, each chained
to its real parent media's sha256 on disk, each matched in duration. 11/11 registered under
`derived/obs-slices/SAEA-PROBE-a2t-abst-44/` (2.7 MB).

One structural curiosity, fully accounted for: the swap set contains **10 distinct byte-streams, not
11**. `tier3_multi_intent:002986` and `tier7_multiturn:000554` have identical audio duration, and a
generated silent WAV is a pure function of (duration, sample rate), so their slices are
byte-identical (both 225,500 bytes, same sha256). They remain two separately registered slice
records, each chained to its own distinct real parent. This is exactly why the server log shows
**10** encode lines and the feature cache grew by **10** entries (480 → 490) for 11 swaps — the
eleventh was a cache hit on its twin. All 22 real-audio requests encoded nothing at all: the
`audio2tool-q4km` cache was already warm over the frozen 400 from the A0 flight.

## 3. Flight

One `llama-server` session, receipt-pinned binary, spawned as a child of this flight's own wrapper.

| Field | Value |
|---|---|
| Cells | `TP-A` → `TP-S` → `TW-A` → `TW-S`, per sample |
| Requests | **44 flown, 0 replayed, 0 failed** |
| Rows by cell | `{"TP-A": 11, "TP-S": 11, "TW-A": 11, "TW-S": 11}`; 44 distinct (cell, sample_id) pairs |
| Mean latency | TP-A 3.087 s, TP-S 0.312 s, TW-A 5.260 s, TW-S 0.187 s |
| Flight wall | 1.6 min; GPU-occupied 3.1 min |
| llama-server argv | `-c 49152 -np 1 -fa on -ngl 999 -ctk q8_0 -ctv q8_0` — the `-np 4 → 1` delta every A2T flight since A0 has applied, and this probe genuinely needs it: all four cells send a registry-sized system prompt (~12.6k tokens) that overflows a 12288-token slot |

Latency is reported because it is operational, not because it is a result; the read mission owns
every interpretation of what the cells produced.

## 4. Spend against the registered ceilings

| Column | Planned | Spent | Registered ceiling | Headroom |
|---|---|---|---|---|
| Core calls | 50 | **44** | 60 | 16 |
| Metered speech-audio seconds | 272 (derived) | **226.51** | 500 | 273.49 |
| GPU hours | 0.15 | **0.051** | 0.15 | 0.099 |

`planned_speech_audio_seconds` was **derived, not hand-typed**: 4 cells × the measured one-pass
56.63 s + 6 retries × the drawn set's longest item 7.42 s = 272, computed by `flight_plan.py` from
the model-free `split-measurement.json` and refused automatically if it had exceeded the registered
500. Silence-swap requests meter their matched parent's duration, so all four cells meter equally.
Prior durable spend on this run id was 0 at takeoff. Token accounting: 581,278 prompt / 1,393
completion; 0 tool calls.

## 5. Hygiene evidence

- **Runtime pins**: llama.cpp build commit `5d9dfcb58ea860295da8fc93c7b5bed9e2c71151`; binary sha256
  `097c96ec…c68` and both GGUF sha256 match the runtime receipt (verified this session, see the
  P-TRAP archive's `gguf-verify.log` — same binary, same session).
- **Feature cache**: `audio2tool-q4km` 480 → 490 entries, fully explained above; the legacy `q4km`
  cache (34,350 entries) and the `slurp-q4km` cache (63 entries) were both untouched.
- **D3 gate**: `PYTHONDONTWRITEBYTECODE=1` throughout; zero `__pycache__`/`*.pyc` under the frozen
  scoring package.
- **Suite**: the full suite ran once at session start — **2846 passed, 9 skipped**
  (`preflight-pytest.log`, shared with the P-TRAP archive).
- **Processes**: no orphan `llama-server` before or after; the server was a child of this flight's
  own wrapper and exited with it.
- **Tree**: clean at `b748ae5` at takeoff, during the flight, and at `client.close()`.

## 6. Exposure ledger

Row `SAEA-PROBE-a2t-abst-44` keeps **`consumed = no`**. This flight spent the requests; the row is
consumed only when the single registered one-shot read executes. A FLOWN note recording this
attempt, its spend and its structural facts was appended to the row's own note cell.

## 7. Files

| File | What it is |
|---|---|
| `README.md` | this receipt |
| `launcher/` | every file that produced the flight (env, identity, plan, measurement, pre-flight, launcher, post-flight, slice audit, wrappers) |
| `measure.log` | the model-free split measurement |
| `split-measurement.json` | measured draw + audio load; the input `flight_plan.py` derives the planned audio ceiling from |
| `preflight.log` | pre-flight (split identity, draw, media, tool-removal invariants, ledger, budgets) |
| `flight.log` | operational flight log (request index, cell, latency, response LENGTH only) |
| `postflight.log` | post-flight structural verification |
| `slice-audit.log` | per-swap byte sizes and sha256; the 10-encodes-for-11-swaps accounting |
| `cell-plan.json` | the resolved per-sample withheld tools and TW render lengths |
| `flight-receipt.json` | the launcher's own receipt (identity, cost, per-cell counts, swap map, session pins) |
| `execution-plan.json` | the validated `ExecutionPlan` |
| `config-values.json` | the hashed config values bundle |
| `session-receipt.json` | the llama-server session receipt |
| `MANIFEST.sha256` | sha256 over every file above |
