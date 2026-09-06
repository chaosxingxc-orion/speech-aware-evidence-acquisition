# EVO-A1 fold flight products — the two folds are now flyable

Model-free, zero contacts, no GPU. Exposure row
`SAEA-SN-MF-A2T-EVO-FOLD-SUPPLEMENTS-V2`. Generators
`scripts/build_a2t_evo_fold_flight_products.py` (the flight-roster receipts and the probe-sample
views) and `scripts/build_a2t_semantic_agentloop_d1_supplement.py --roster` (the two D1 media
supplements); receipt shapes `analysis/a2t_evo_rosters.py`. Outbound connection attempts: **0**.

Authority: `docs/readiness/2026-09-06-a2t-evo-a1-description-evolution-v1-preregistration.md`
section 12 item 4, which named exactly these three artifacts per speech-bearing roster and recorded
that none of them existed. The rosters themselves are
`SAEA-SN-MF-A2T-EVO-FOLD-ROSTERS-V2` (`docs/receipts/rosters/a2t-evo-fold-{a,b}-v2.json`), the
owner's 2026-09-06 RELAXED-with-sentinels re-freeze.

## What landed

| fold | rows | reward / sentinel / background | blocks | audio s | longest | flight-roster receipt |
|---|---:|---|---:|---:|---:|---|
| A | 424 | 284 / 20 / 120 | 269 | 2,016.519 | 39.634 | `flight-roster-receipt-fold-a.json` |
| B | 418 | 284 / 14 / 120 | 300 | 1,950.418 | 53.771 | `flight-roster-receipt-fold-b.json` |

| fold | probe-sample view | new ids | already covered | D1 media supplement | media bytes |
|---|---|---:|---:|---|---:|
| A | `docs/receipts/probe-samples/a2t-evo-fold-a-v2.json` | 322 | 102 | `docs/receipts/artifacts/d1-a2t-evo-fold-a-v2.json` | 96,811,580 |
| B | `docs/receipts/probe-samples/a2t-evo-fold-b-v2.json` | 291 | 127 | `docs/receipts/artifacts/d1-a2t-evo-fold-b-v2.json` | 93,638,454 |

The already-covered ids resolve through `a2t-construction-800-v1.json`, the identity view of
`A2T-CONSTRUCTION-800-V1` — a frozen construction roster that has never been flown. A probe-sample
receipt repeating them would be refused as a duplicate, so each new receipt is ADDITIVE and carries
only the ids no committed receipt covers yet. Both folds resolve completely: 424 / 424 and
418 / 418 inside `data.audio2tool`'s frozen-receipt universe, which the two new receipts grow from
5,274 to 5,887 identities with zero duplicates.

Dataset fragments: `configs/dataset/audio2tool-evo-fold-a-424.json` and
`configs/dataset/audio2tool-evo-fold-b-418.json`, on the `a2t_calibration_*` key contract, so both
folds fly through `scripts/flights/run_calibration_cell.py` and the same `FlightRuntime` with no
new code path.

## The gate was actually run, offline

`contracts.gate_media_identity.verify_media_identity("audio2tool", ...)` was called through a real
`FrozenCoreGate.for_study_repo` binding — the committed E0 closure receipt, the pinned
`receipts/runtime-q4km-featcache-04ccc72a.json`, the study exposure ledger and the umbrella lock —
with each fold's own supplement configured by path and SHA-256, and every row of that fold offered
at once:

* fold A: **PASS on all 424 rows**;
* fold B: **PASS on all 418 rows**;
* negative control on both: an unlisted sample id (`tier1_direct:999999`) bound to a real
  media path was **refused** (`GateClosed`), so the pass is not a vacuous one.

No model, server, tokenizer or scorer was started, and `CUDA_VISIBLE_DEVICES` was empty throughout.

## One binding decision, recorded rather than inherited

`tier7_multiturn` rows bind the **FIRST** user turn — `audio_paths[0]` of the released
`Tier7Dataset._get_audio_paths`, the row the three sealed official-population rosters and the 4,000
final read fly. `data.audio2tool._entry_media` reads `chat_history[-1]` instead (the P1 scaffold's
final-turn binding, a protocol-fidelity gap its own module docstring records), and on **all 92**
tier-7 rows of the two folds the two resolve to different wavs. The folds follow the official rule,
so a fold's selection signal is measured on the same kind of utterance as the population the loop
must transfer to. `analysis.a2t_evo_capacity.measured_media_facts` is where that choice lives, and
it is also why `audio_seconds` here is the wav header's `frames / sample_rate` rather than the
manifest's three-decimal `duration` cell: the D1 supplement is built from headers and refuses a
disagreement above 1e-6.

## Contact surface

Wav bytes hashed and wav container headers read for frame count and sample rate; the released tier
manifests read for `id`, `path` / `chat_history` turn `path` and `role`, and `domain` for the
aggregate stratum counts. No query text, no `tool_name`, no `expected_tool_call`, no annotation, no
prior output, no score. The per-row gold tool the frozen construction receipt legally records is
deliberately **not** copied into the flight-roster receipt, because that is the file the flight
entry point reads to build its samples; the counts travel as aggregates instead.

## What this does NOT do

It grants no contact authority. The preregistration is still a DRAFT, `A_0` is still open, the
curve roster is still unchosen, and the loop's five run ids have no exposure rows, so
`rails.evolution.check_ledger_budget` refuses to emit a round fragment and
`scripts/run_a2t_evolution_round.py --round 1` cannot leave `--plan-only`. The round-1 proposer
anchors' own `d1-a2t-evo-proposer-r01` supplement is therefore NOT built here: it needs the
proposer roster that the `propose` step writes, and that step is blocked on the ledger.
