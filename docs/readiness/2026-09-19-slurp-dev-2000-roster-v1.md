# SLURP DEV-2000 development roster, v1 (owner decision 34, 2026-09-19)

Model-free build: zero model, tokenizer, encoder, ASR and server contacts; the offline guard recorded
0 outbound connection attempts in every receipt, and nothing under `SPEECHRL_DATA_DIR/runs`,
`/attempts`, `/locks` or the serving session was touched.

## What was built

| Artifact | Path |
| --- | --- |
| Full roster (2,000 rows) | `docs/receipts/rosters/slurp-dev-2000-v1.json` |
| Added rows only (1,000 rows; the comparators bind this) | `docs/receipts/rosters/slurp-dev-2000-added-v1.json` |
| Runtime view for the added rows | `configs/dataset/slurp-speech-native-dev2000-added.json` |
| Disjointness proof | `docs/checks/speech-aware-evidence-acquisition/2026-09-19-slurp-dev-2000-roster/disjointness.json` |
| Media inventory, CPU throughput and the packet plan | `docs/checks/speech-aware-evidence-acquisition/2026-09-19-slurp-dev-2000-packets/{media-inventory,packet-preparation-plan}.json` |
| Generators | `scripts/build_slurp_dev2000_roster.py`, `scripts/build_dev2000_added_runtime_view.py` |

Identity hashes (`data.splits.split_identity_hash` over LF-joined, sorted, carrier-prefixed ids, the
convention every `ExecutionPlan` carries): `SLURP-DEV-2000-V1`
`c4cc1cda7cc1ee50cf959fa3c26cef3d848475dba8cde4e301e59ff89225e3fd`, `SLURP-DEV-2000-ADDED-V1`
`ee6c43cd4dd8fc2a583d2dd053e799c2d002efa3755fcd092ba7c7565431bf67`, runtime view
`6968a0564699968f1615bb98b45d2f0ccf179dd0a04351b2871bc096a9052477`.

## The drawing rule

Seed 20260919, through `core.roster.freeze_roster`, `exclude_groups` keyed by utterance so an
excluded utterance takes all of its recordings with it.

1. **Stage 1 — 500 rows.** `SLURP-DEV-500-B-V1`'s exact recordings, verbatim.
2. **Stage 2 — 413 rows.** The whole remaining eligible utterance pool, one recording each; each
   per-scenario quota equals that scenario's surviving capacity, so no quota choice is made.
3. **Stage 3 — 87 rows.** Second recordings of stage-1/stage-2 utterances, apportioned by
   `core.roster.mixture_quotas` against the full devel mixture and capped by capacity; no utterance
   reaches three.

Added half: 1,000 recordings over 913 utterances; DEV-2000 = 2,000 recordings over 1,913
utterances, 5,868.32 s of speech.

### Why not "1,000 fresh utterances, DEV-1000's rule"

`devel` holds 8,690 recordings of 2,033 utterances. DEV-1000 (1,000), FINAL60 (60) and the historic
probe-60 (60) consume 1,120, leaving **913**. A 1,000-row addition of never-used utterances is
arithmetically impossible, and DEV-1000's equal-per-scenario allocation is infeasible on the
remainder (alarm, audio, cooking, music and takeaway are drained to zero). Three deviations are
recorded in both receipts' `deviations` block and need an owner ruling before the flights:

* **DEV2000-D1** — `SLURP-DEV-500-B-V1`, frozen 2026-09-05 as a *reserved, unopened* rung-3
  replication roster, is absorbed. Its 500 recordings are taken **verbatim**, so it survives as an
  exact sub-table and its 500-row read stays recoverable — but it stops being reserved the moment
  these comparators fly. Holding it back leaves 413 utterances in 9 of 18 scenarios.
* **DEV2000-D2** — 87 of the 913 added utterances contribute a second recording; paired analyses
  must cluster by `utterance_id`. The alternative is a 913-row addition (DEV-1913).
* **DEV2000-D3** — the added half follows the natural devel mixture, not DEV-1000's equal-per-
  scenario shape; report DEV-2000 verdicts under both weightings (2026-09-03 reporting rule).

## Counts per stratum (scenario)

| scenario | DEV-1000 | added | DEV-2000 |
| --- | ---: | ---: | ---: |
| calendar | 61 | 221 | 282 |
| play | 60 | 203 | 263 |
| qa | 60 | 157 | 217 |
| email | 61 | 96 | 157 |
| weather | 60 | 65 | 125 |
| general | 61 | 62 | 123 |
| iot | 61 | 57 | 118 |
| lists | 60 | 52 | 112 |
| transport | 60 | 48 | 108 |
| news | 60 | 20 | 80 |
| datetime | 61 | 9 | 70 |
| recommendation | 60 | 6 | 66 |
| social | 60 | 4 | 64 |
| alarm / audio / cooking / music / takeaway (pool drained by the ladder) | 58 / 30 / 37 / 51 / 39 | 0 each | unchanged |
| **total** | **1000** | **1000** | **2000** |

Channel (not a draw stratum in either half): DEV-1000 478 headset / 522 far-field, added 460 / 540,
DEV-2000 938 / 1,062.

## Disjointness (all proven, receipt `.../2026-09-19-slurp-dev-2000-roster/disjointness.json`)

Every `shared_with_*` field is **0**: added vs DEV-1000 (recordings and utterances), vs FINAL60, vs
the historic probe-60, vs the test split (by recording id against the frozen enumeration), and vs
all eight committed TRAIN construction rosters (fold A/B v1+v2, exemplars v1+v2, the EVO-S1 proposer
roster, the native-tools engineering four). No added id falls outside the frozen devel enumeration,
and no added utterance carries more than two recordings (87 do).

Text-level check (digest only, method from `scripts/build_slurp_evo_decontamination.py`; no sentence
and no n-gram is written anywhere): against the 11,514-utterance TRAIN construction text pool the
added half has **1** exact-sentence match and **113 of 913** utterances sharing a word 6-gram; the
sealed half, measured identically, has **1** and **111 of 1,000** — no new contamination class.

## Packets — prerequisites complete, encode NOT run

A speech packet here is an **encoder product**: the pipeline
(`scripts/slurp_evo_fold_preprocess.py`, precedent `SAEA-SN-DEV1000-PREPROCESS`) first drives a CPU
llama-server sidecar carrying the decoder and the bf16 mmproj with one contact per row, then
promotes the warm cache entries. That first phase is a model contact a model-free mission may not
make, so **no packets were promoted**; measured, **0 of 1,000** added rows are warm in the legacy
cache `/home/chao/feat-cache/slurp-q4km`, so all 1,000 need the encode pass.

Everything model-free is committed: the runtime view (per-row media relpath, SHA-256, header
duration, sample rate, packet id), the D1-closure proof (1,000 of 1,000 covered, no supplement
needed), and CPU throughput at 8 workers — media inventory 1,000 files in 2.01 s (497.6 files/s,
1,484.7 audio-seconds per wall-second, 27.0 MiB/s), cache-key pass 1,000 files in 1.20 s (834.9
files/s); 56,878,956 bytes, 2,983.53 s of speech. `ffmpeg` was not installed and no media byte was
rewritten. The plan names the **existing served root**
`/home/chao/feat-cache/slurp-q4km-packets-04ccc72a` with an **additive-only** write (new
`slurp/devel/<id>/` directories plus a new `DEV-2000-ADDED-promotion.json`): no file the resident
session already serves is modified. Full isolation instead means a new root
(`slurp-dev2000-added-packets-04ccc72a`) and a service restart to move
`LLAMA_SPEECH_FEATURE_ROOT`.

## The two comparator flights the coordinator registers next

Both bind `SLURP-DEV-2000-ADDED-V1` (`ee6c43cd…`) through
`configs/dataset/slurp-speech-native-dev2000-added.json`, on the added 1,000 rows only — the sealed
half already has its outputs and is never re-flown.

| Arm | Contacts | Expected cost (scaled from the sealed DEV-1000 runs) |
| --- | --- | --- |
| Direct baseline (`direct-only` phase program, same harness) | 1 per row = 1,000 | ~2,984 speech-seconds, ~1,102 s summed latency, ≈0.31 h wall at np4; plan envelope 1,000 calls / 3,500 audio-s / 1.0 GPU-h |
| Dual-store anchor | ≈5.04 per row ≈ 5,040 model + ~1,007 tool | ~15,050 speech-seconds, ~44,000 s summed latency, ≈3.1 h wall at np4; plan envelope 11,000 calls / 44,000 audio-s / 12.0 GPU-h |

Measured basis: `SAEA-SLURP-DIRECT-MAX512-DEV1000-BASE-REPLICATION-V1` (1,000 calls, 2,884.79
audio-s, 1,066.11 s latency) and `SAEA-SLURP-NATIVE-DUAL-STORE-DEV1000-BASE-REPLICATION-V1` (5,040
calls, 1,007 tool calls, 14,552.03 audio-s, 42,577.34 s latency); the added half carries 3.4 % more
speech.

**One-shot rule.** These two comparators fly **once** on the added rows and are never re-flown. A
later mechanism is compared against those sealed per-row outputs, not against a fresh comparator
pass. Both need packets first (see above) and a resume-capable registration (decision 22).

## Open items for the coordinator

1. Owner ruling on DEV2000-D1/D2/D3 before the comparators fly.
2. The encode + promote pass (1,000 contacts, CPU sidecar, GPU-free) under its own plan.
3. No exposure row was appended to `docs/exposure-ledger.md` (zero contacts, and the live campaign is
   appending to that file). If one is wanted: `SAEA-SN-MF-SLURP-DEV2000-ROSTER-V1 |
   model-free-check | 0 calls | 0 audio-s | 0 GPU-h`, scope "slurp devel, identity only, 1,000 added
   recordings", evidence the two receipts above.

## Reproduce

In WSL2 with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD/src CUDA_VISIBLE_DEVICES=`, run
`python scripts/build_slurp_dev2000_roster.py --write`, then
`python scripts/build_dev2000_added_runtime_view.py --write`. Deterministic: sorted items, canonical
JSON, seed 20260919; `core.roster.write_roster` refuses to overwrite an existing receipt.
