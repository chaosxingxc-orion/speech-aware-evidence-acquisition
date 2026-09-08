# MF-9 — the SLURP slot-filling gap audit (2026-09-08)

Row id `SAEA-SLURP-MF9-SLOT-GAP-AUDIT-V1`, profile `model-free-check`.
**Zero model, GPU, tool, embedding, network and audio-decode contacts. Zero paid spend.**
Note: `docs/readiness/2026-09-08-mf9-slurp-slot-gap-audit-v1.md`.
Generator: `scripts/mf9_slurp_slot_gap_audit.py` (subcommands `decompose`, `projection`, `schema`,
`headroom`, `ladder`).
Module: `src/speech_aware_evidence_acquisition/reproduction/slurp_value_projection.py`
(`slurp-value-projection-v1`), 21 unit tests in `tests/unit/test_slurp_value_projection.py`.

The one subprocess this audit runs is the **pinned official SLURP `evaluate.py`** (commit
`8eb1654…311f1`, `~/.venvs/slurp-official-eval`, used and never modified) — the scorer, never a
model. The arm under the microscope is the ADMITTED KC-S1b
(`SAEA-SLURP-KC-S1B-SLOTS-SCHEMA-DEV1000-V1`, attempt `attempt-20260906T025102Z-af6b04`, sealed
manifest sha256 `088c9307…fe08`), SLU-F1 **44.35** on DEV-1000.

## Headline

| question | answer |
|---|---|
| 1. loss decomposition | The corpus loss mass **2,123.085** closes exactly over four categories: **missing gold 45.41 %**, **surface form 25.96 %**, **spurious 20.16 %**, **wrong type / right value 8.48 %**, and **intent errors 0.00 %**. Ceilings: answering every missing mention is **+31.40**, perfect normalization **+7.49**, no spurious **+5.60**, no type swap **+4.72**. `date`, `place_name` and `time` carry **32.70 %** of the loss between them |
| 1a. the intent counterfactual | Substituting the GOLD `(scenario, action)` into the same sealed entity outputs moves intent 32.10 → **99.70** and SLU-F1 by **0.0000** — the official script feeds SLU-F1 the distance blocks alone. The only channel intent has is block selection: **51 of 950** gold mentions have a type the sent block omitted and the gold intent's block lists |
| 2. value-projection judge | Best honest operating point `normalized` τ = 0.20: SLU-F1 44.35 → **45.09 (+0.74)**, Word-F1 +1.13, **entities strict +3.31**, 41 values changed on 40 rows, **32 saves / 1 harm**, CI90 **[+0.45, +0.87]** pooled and **[+0.47, +1.10]** NEW500. **NOT a re-lock candidate** — the bar was 1 point |
| 3. schema conformance | **914 of 1,000 rows fully conform**; 3 unparsed, 72 carry a block-illegal type (73 of 682 mentions), 11 repeat a type, and **0 mentions violate the 55-type vocabulary**. Suppressing block-illegal mentions is **+0.62** corpus micro but **−0.47 pp** paired (12 harms) because **8** of them matched gold and **81** gold mentions carry a type no block listed |
| 3. constrained decoding | **AVAILABLE and wired end to end**, one config key (`response_format_id`), with citations on both sides including the pinned llama.cpp `04ccc72a` where `json_schema` carries `grammar` as an alias. **Per-sample is not reachable**: `resolve_response_formats` never sees a sample. Ceiling for the structural module: **+0.81** |
| 4. value headroom | **76.21 %** of DEV gold values occur verbatim in the TRAIN filler set of their own type; MF-8's partition **inverts** (utterance-local 82.31 % against standing 72.27 %). KU-S3's speech-keyed top-5 already carries **390 of 950** gold mentions — filler recall **41.90 / 43.46**, reproducing MF-7b exactly — for an oracle ceiling of **58.06**. Same-speaker slot exemplars exist on **95.65 %** of (row, type) pairs; **333 of 1,000 rows carry no gold slot at all** |
| 5. the ladder | Priced, not preregistered. Only rung 1 is measured. Ceiling per GPU-hour orders re-ask (199) > retrieval (68.5) > intent narrowing (20.2) > constrained decoding (4.0); admission order puts **KU-S3 first**. Gated by the **schema judge alone** the re-ask reaches **403.5** ceiling-gain per GPU-hour at 72 % precision on 8.6 % of rows. Solving recall alone caps at **78.04**, which is the published gold-transcript NLU line |

## Identity anchors, fail-closed

Every read raises rather than reports if the sealed bytes stop reproducing a published verdict.
All held:

* KC-S1b entities strict / Word-F1 / Char-F1 / **SLU-F1** = 31.37 / 41.58 / 47.51 / **44.35**,
  from the sealed manifest through `core.scoring_batch` **and** from a re-emitted canonical
  prediction envelope — identical;
* SLU-F1 rebuilt from the port's own per-sample TP/FP/FN ingredients: **44.3503**;
* KC-S1b's prompt-fit schema-block accounting: **42** fallback rows over **58** distinct intents,
  and every one of the 42 ids matches its per-row flag;
* MF-7b filler recall@5 from the sealed KU-S3 floats: **43.46** NEW500, **41.90** pooled,
  40.21 OLD500.

## Boundary

The held-out `test` split is never named, loaded, hashed or scored. **No devel `sentence` string
is read anywhere** — `data.slurp.load_slurp_split` does not carry one. DEV gold **entity
annotations** enter only on the **scoring side**, exactly where the official scorer already reads
them, as a metric ingredient and an audit statistic — never as a mechanism input. The
value-projection inventory is mined from **TRAIN alone** and its loader refuses any other split by
name.

## Files

| file | content |
|---|---|
| `loss-decomposition.json` | question 1: the four-category attribution, per-type table (53 types), per-category ceilings, the gold-intent counterfactual, the block-selection channel |
| `value-projection.json` | question 2: the two rule families over eight thresholds, official numbers, paired CI90 on three populations, branch counts, worked examples |
| `schema-conformance.json` | question 3: conformance counts, what the violating rows lose, the two suppression counterfactuals, and the constrained-decoding source reading with file:line citations |
| `value-headroom.json` | question 4: verbatim TRAIN coverage per type, the KU-S3 retrieved-top-5 ceiling, same-speaker slot-exemplar availability |
| `improvement-ladder.json` | question 5: the judges and their precision, the six priced rungs, per-judge re-ask ceilings, the published lines |
