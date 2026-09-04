# SLURP official-scorer alignment, zero contact (2026-09-04)

Exposure row: `SAEA-SLURP-MF-SCORING-ALIGNMENT-V1` (`docs/exposure-ledger.md`). Profile
`model-free-check`, reference-reading on the `devel` split identity only. **Zero model, GPU, tool,
embedding, network and audio contacts.**

## Split discipline

`split_id="devel"`, `allow_heldout=False`. The held-out `test` split is never named, loaded or
scored. The devel split resolves to **2,033 sentences / 8,690 recordings** under `slurp_real`;
`data.slurp._AUDIO_SUBDIR_FOR_SPLIT` maps `devel` to `slurp_real` only, so **zero SLURP-synt rows**
can enter by construction (the 69,253-file `slurp_synth` tree is unreachable from this split id).

**Microphone channel.** SLURP encodes the channel in the filename: `audio-<epoch>-headset.flac`
is the close-range headset take and `audio-<epoch>.flac` the far-field mic-array take of the same
sentence. Devel is **4,173 headset / 4,517 far-field**. No channel filtering was ever applied, and
every roster is close to that natural proportion:

| roster | headset (close-range) | far-field | total |
|---|---|---|---|
| devel (whole split) | 4,173 (48.0 %) | 4,517 (52.0 %) | 8,690 |
| DEV-1000 | 478 (47.8 %) | 522 (52.2 %) | 1,000 |
| DEV-500 | 236 (47.2 %) | 264 (52.8 %) | 500 |
| DEV-500-NEW400 | 194 (48.5 %) | 206 (51.5 %) | 400 |

**These are not headset-only (easier) rosters.** `channel-breakdown.json` in this directory carries
the per-channel accuracy of every arm.

## Evaluator

The real, unmodified official `scripts/evaluation/evaluate.py` at pinned commit
`8eb16545762be97ace75334109d73824217311f1`, run as a subprocess from
`$SPEECHRL_DATA_DIR/repos/slurp/scripts/evaluation` in its own pinned environment
`~/.venvs/slurp-official-eval` (never modified), with `--average micro --errors --table-layout csv`.
Reached through the registered `slurp-slu-official` scorer, which additionally runs this study's
per-sample port (`reproduction.slurp_scoring`) over the same rows and asserts numeric identity
(tolerance 1e-6) before returning. **All six arms passed the identity check** (max |diff| 1.1e-16).

## Two blockers found on the sealed artifacts (reported, not patched)

1. **No run manifest.** The August SLURP flights (`SAEA-DEV1000-BASELINE-LOCK`,
   `SAEA-DEV500-CONFIRMATORY`) predate the canonical `core.flight.FlightRuntime.seal` contract.
   Their attempt directories contain `flight-state.json`, `arm*-outputs.jsonl`, `execution-plan.json`
   and trace artifacts, but **no `*.run-manifest.json`**. `core.scoring_batch` refuses any job whose
   manifest is not a `*.run-manifest.json`, so the verified batch path is inapplicable to this
   carrier's sealed August artifacts. Nothing was fabricated to work around it.
2. **Row shape.** Those flights write `final_response_text`; every registered scorer (including
   `slurp-slu-official`) reads `text`. The scorer therefore cannot consume the sealed bytes
   directly. `rescore.py` writes a 1:1 **key-rename projection** —
   `{"sample_id": <unchanged>, "text": <the sealed final_response_text verbatim>}` — records the
   SHA-256 of both the sealed source and the projection, and scores the projection. No response
   text is altered, no row added or dropped.

## The N-predicted hazard, demonstrated on this repository's own data

`evaluate.py` pairs with `if gold_id in pred_examples:` — a gold row with no prediction never
touches TP/FP/FN and only triggers a stderr warning. `rescore.json`'s
`skip_hazard_demonstration` block proves it here: the same 1,000 DEV-1000 M0 predictions scored
against the **whole 8,690-recording devel gold set** print exactly the roster-scoped numbers
(scenario 0.7000 / action 0.6150 / intent 0.5360 / SLU-F1 0.3690 / entities 0.2194) while
**7,690 gold rows go unscored and unpenalised**. Every arm below therefore states
`n_gold_roster`, `n_predicted` and an `unanswered_counted_wrong` variant.

## Official `evaluate.py` results (micro), per sealed arm

All values are the official script's own `F-Measure` column, in percent. For the three
single-label blocks (scenario / action / intent) micro P = R = F1 = accuracy.

| arm | roster | n gold | n predicted | gold rows skipped | unparsed responses | scenario | action | **intent (scen_act)** | entities (strict) | Word-F1 | Char-F1 | **SLU-F1** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| DEV-1000 M0 (direct) | DEV-1000 | 1000 | 1000 | 0 | 5 | 70.00 | 61.50 | **53.60** | 21.94 | 34.66 | 39.46 | **36.90** |
| DEV-1000 BLEND (locked cell) | DEV-1000 | 1000 | 1000 | 0 | 2 | 83.90 | 77.60 | **75.70** | 27.27 | 39.41 | 44.24 | **41.69** |
| DEV-500 M0 (direct) | DEV-500 | 500 | 500 | 0 | 3 | 68.20 | 61.40 | **51.80** | 19.16 | 33.25 | 38.18 | **35.54** |
| DEV-500 BLEND | DEV-500 | 500 | 500 | 0 | 0 | 81.00 | 74.20 | **71.80** | 22.64 | 36.82 | 41.65 | **39.09** |
| DEV-500 RANDRET (negative control) | DEV-500-NEW400 | 400 | 400 | 0 | 1 | 71.25 | 62.75 | **56.50** | 18.58 | 33.62 | 38.50 | **35.89** |
| DEV-500 RANDICL (negative control) | DEV-500-NEW400 | 400 | 400 | 0 | 3 | 64.50 | 56.00 | **47.00** | 23.10 | 35.06 | 40.55 | **37.60** |

No arm has a gold row without a prediction, so `unanswered_counted_wrong` equals the official
number in every row above. The two 400-row control arms were flown on the `DEV-500-NEW400`
sub-roster (`docs/receipts/probe-samples/DEV-500-NEW400.json`, identity
`36c778da…898b`), verified here to be exactly the 400 ids they answered — they are **not**
500-row arms with 100 refusals.

### Identity anchor against the sealed lock read

`docs/checks/speech-aware-evidence-acquisition/2026-08-25-dev1000-lock-read/read-verdict.json`
recorded pooled DEV-1000 correctness (`scenario_action_exact`) M0 0.536 / BLEND 0.757 through the
per-sample port. The official `evaluate.py` intent (scen_act) column reproduces both exactly
(53.60 / 75.70), so the official scorer and the study's own correctness definition agree on this
carrier with no adjustment.

### Per-channel intent (scen_act) accuracy

Computed by `channel-breakdown.py` with the same per-sample port the official scorer agreed with
(`channel-breakdown.json`). Headset is the close-range take, far-field the mic-array take.

| arm | headset n | headset intent % | far-field n | far-field intent % | far-field − headset |
|---|---|---|---|---|---|
| DEV-1000 M0 | 478 | 51.05 | 522 | 55.94 | +4.89 |
| DEV-1000 BLEND | 478 | 75.10 | 522 | 76.25 | +1.14 |
| DEV-500 M0 | 236 | 49.15 | 264 | 54.17 | +5.01 |
| DEV-500 BLEND | 236 | 70.34 | 264 | 73.11 | +2.77 |
| DEV-500 RANDRET | 194 | 54.64 | 206 | 58.25 | +3.61 |
| DEV-500 RANDICL | 194 | 48.45 | 206 | 45.63 | -2.82 |

Far-field is **not** the harder channel here: it is 1–5 points *better* on five of six arms. The
frozen core's SLURP errors are dominated by label choice, not by acoustics, so no part of these
numbers comes from sitting on an easier microphone subset.

## Alignment against the published brackets (owner rule, 2026-09-04)

Every published row below is a **trained** system on the **official test split** (2,974 sentences /
13,078 recordings) unless marked otherwise; ours are **zero-shot, prompt-only, one frozen
Q4_K_M core** on **devel** rosters. No published prompt-only SLU-F1 computed with this script
exists for any audio LLM, so **no like-for-like 3-point target exists on this carrier**; the
classifications below are cross-system readings, not reproductions.

Intent (scen_act) accuracy, %:

| ours | published row | source | delta (ours − published) | verdict under the 3-point rule |
|---|---|---|---|---|
| DEV-1000 BLEND 75.70 | Gold/HerMiT upper bound 84.84 | SLURP Table 7 (gold transcripts) | −9.14 | not aligned (below) |
| DEV-1000 BLEND 75.70 | Multi-SLURP/HerMiT 78.33 | SLURP Table 7 (strong ASR→NLU pipeline) | −2.63 | **aligned** |
| DEV-1000 BLEND 75.70 | Google/SF-ID 72.06 | SLURP Table 7 (weak commercial pipeline) | +3.64 | **aligned-better** |
| DEV-1000 BLEND 75.70 | ChatGPT on oracle transcripts, 0-shot 79.25 | He & Garner arXiv:2305.13512 (prompt-only, 60 intents) | −3.55 | not aligned (below, by 0.55) |
| DEV-1000 BLEND 75.70 | ChatGPT on Whisper ASR, 10-shot 72.89 | same | +2.81 | **aligned** |
| DEV-1000 M0 53.60 | Google/SF-ID 72.06 | SLURP Table 7 (weakest published pipeline) | −18.46 | not aligned (below) |
| DEV-1000 M0 53.60 | Multi-SLURP/HerMiT 78.33 | SLURP Table 7 | −24.73 | not aligned (below) |

SLU-F1, %:

| ours | published row | source | delta | verdict |
|---|---|---|---|---|
| DEV-1000 BLEND 41.69 | Multi-SLURP/HerMiT 70.84 | SLURP Table 8 (best in the original paper) | −29.15 | not aligned (below) |
| DEV-1000 BLEND 41.69 | Google/SF-ID 64.02 | SLURP Table 8 (weakest published pipeline) | −22.33 | not aligned (below) |
| DEV-1000 M0 36.90 | Google/SF-ID 64.02 | SLURP Table 8 | −27.12 | not aligned (below) |
| DEV-1000 BLEND 41.69 | ChatGPT slot F1 12.03–13.35 | He & Garner (prompt-only slot filling) | +28.3 to +29.7 | **aligned-better** (different F1 definition; see caveat) |

Degraded-model floor rule: the weakest **published** SLURP system with official-script numbers is
Google/SF-ID (intent 72.06, SLU-F1 64.02). **BLEND clears that floor on intent (75.70 > 72.06) and
fails it on SLU-F1 (41.69 < 64.02). M0 fails both.** Every published floor here is a system
*trained on SLURP*; the only prompt-only published system (He & Garner's ChatGPT cascade) is
cleared on slot filling by a wide margin and missed on intent by 0.55 points against its
oracle-transcript 0-shot row.

Caveats that must travel with these tables:

1. **He & Garner's slot F1 is not this script's SLU-F1.** Their 12–13 % is a slot-filling F1 over
   60 intents on oracle transcripts; our 41.69 is the official `SLUF1` block (word- plus
   char-distance confusion matrices summed). Read the comparison as "prompt-only slot filling is
   the known collapse point, and this system is well above the one published prompt-only number",
   not as a matched metric.
2. **Devel vs test.** Every published row is the test split. The devel/test WER gap in the SLURP
   paper's own Table 5 is 0.1–0.5 points, so the splits are close, but they are not the same split.
3. **Roster shape.** DEV-1000/DEV-500 are scenario-stratified near-equal-per-scenario stress
   rosters (TVD 0.22–0.24 from the natural TRAIN mixture, recorded in
   `docs/checks/speech-aware-evidence-acquisition/2026-09-03-information-audit-slurp/`), not
   call-volume-weighted samples. The published tables are natural-mixture.
4. **Label space.** The paper never states an intent count; downstream work reports 60, 65 or 69.
   This study scores free-form `{scenario, action}` strings against gold strings — no closed label
   list is offered to the model, which is strictly harder than a 60-way classification prompt and
   far harder than AIR-Bench's 4-way MCQ (Qwen2.5-Omni 75.5, not this metric).
5. **BLEND is not a bare model.** It is the locked knowledge cell (retrieval + α-blend over a
   TRAIN-mined knowledge plane), i.e. this study's mechanism, not a baseline. The bare frozen core
   is M0.

## What a model contact would still be needed for

- **The official test split.** A prompt-only SLU-F1 on the 13,078-recording official test split,
  computed with this exact script, does not exist anywhere in the literature. Producing it would be
  the first of its kind — and it is the only way to make any SLURP number here directly comparable
  to Tables 7 and 8. It requires a preregistered confirmatory read (`allow_heldout=True`), which
  this repository's split discipline forbids without one.
- **A natural-mixture devel read.** Every sealed roster is equal-stratum. A call-volume-weighted
  devel sample would be needed before quoting a single "SLURP devel" number beside a
  natural-mixture published row.
- **A closed-label-list arm.** He & Garner's 79.25 % is a 60-way classification prompt. Matching
  their protocol needs a new arm that offers the model the label list.

## Files

- `rescore.json` — schema `saea-slurp-scoring-alignment-v1`: per-arm official block (all seven
  `evaluate.py` tables), port micro-aggregate, identity check, roster comparison, projection and
  source SHA-256, skip-hazard demonstration.
- `rescore.py` — the exact script that produced it.
- `channel-breakdown.json` (schema `saea-slurp-channel-breakdown-v1`) — per-microphone-channel
  scenario/action/intent accuracy for every arm, plus the devel and roster channel counts.
- `channel-breakdown.py` — the exact script that produced it.
- `MANIFEST.sha256` — SHA-256 of every file in this directory.
