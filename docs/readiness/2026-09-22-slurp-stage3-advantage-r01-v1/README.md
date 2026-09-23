# Readiness package: SAEA-SLURP-STAGE3-ADVANTAGE-R01-V1

Status: **HELD**. This package registers the engineering for Stage-3 S3-4 (the semantic-advantage
contact ADV-1) -- it does not authorize a flight, a readiness flip, or an admission entry. Source
spec: `docs/superpowers/specs/2026-09-22-stage3-tfrl-base-loop-engineering.md` section S3-4;
design: `docs/superpowers/specs/2026-09-21-slurp-stage3-training-free-rl-design.md` section 2 step 4
(owner decision 82).

Stage-3 algorithm (owner decision 101): **`tfgrpo-semantic-advantage-v1`** (Training-Free GRPO,
arXiv:2510.08191), operator `credit_assignment` -- this cell produces the group-relative semantic
advantage statement and nothing else; the update and its application are S3-5 and CELL-1. Declared as
`stage3_algorithm` in `configs/experiment/slurp-native-stage3-advantage-r01-v1.json` and checked by
`scripts/checks/stage3_algorithm_label_check.py`.

## What this cell is

One `construction-advantage-text` contact per row S3-3 selects as disagreeing within its N=5 ROLL-1
rollout group (`analysis/SAEA-SLURP-STAGE3-ROLLOUT-R01-SCORE-V1/pairs.json`). The contact is shown
the row's best and worst rollout sample answers (custodied model outputs, never receipted) and the
row's own construction gold (owner decision 82; the `construction-proposer-text` precedent), and
answers in a fixed three-line form:

```
DELTA-KIND: <intent-boundary | slot-contract | exemplar-note>
TARGET: <scenario_action or slot type>
STATEMENT: <<=40 words>
```

parsed by `rails.stage3_advantage.parse_advantage_statement` (closed-form, line-keyed, never raises;
an illegal statement is retained and marked, dropped only at S3-5 curation).

## Engineering delivered here

- Arm `construction-advantage-text` registered beside `construction-proposer-text`
  (`src/speech_aware_evidence_acquisition/e0/d2_leakage.py` `ARM_VISIBLE_FIELDS`;
  `src/speech_aware_evidence_acquisition/contracts/identifiers.py` `CONSTRUCTION_VISIBLE_ARMS`) --
  same field set as the proposer arm (bare-core's ten fields plus `construction_targets`), so the
  SAME gate (`contracts.gate_exposure._require_construction_role_for_visible_targets`) and the same
  D2 invariant (`e0.d2_leakage._construction_visibility`) cover it with no further code change.
- Phase program `phase-stage3-advantage-v1` (`configs/policy/phase-stage3-advantage-v1.json`, one
  phase named `advantage`, `max_contacts` 1, `stop_rule` `always-run-full-program`) registered into
  `core.base.AGENT_CONTROLLERS` by `rails.controllers.register_phase_programs_v1`.
- Response format `stage3-advantage-statement-v1` (a JSON-schema structured-decoding thunk mirroring
  the three-line form's fields) registered into `core.base.RESPONSE_FORMATS` by
  `rails.controllers.register_response_formats_v1`.
- `rails.stage3_advantage`: the parser, the `pairs.json` loader (pinned by SHA-256, bound to the
  rollout run id), the instruction renderer (the ONLY place best/worst answers and gold are combined
  into text -- never receipted), and the response-format thunk.
- Instruction templates `configs/probes/slurp_stage3_advantage_system_v1.txt` (static system message)
  and `configs/probes/slurp_stage3_advantage_v1.txt` (the per-row control turn, filled at flight time
  by a caller-supplied `material_for_phase`), both pinned in `configs/probes/manifest.json`.
- Cell fragments `configs/baseline/slurp-native-stage3-advantage-baseline-v1.json` and
  `configs/experiment/slurp-native-stage3-advantage-r01-v1.json` (run ids
  `SAEA-SLURP-STAGE3-ADVANTAGE-R01-V1` / `-FIT-V1`), `allowed_execution_stages` `check`/`worker`/
  `campaign`, `readiness.state` `held`.
- The ADV-1 runbook `scripts/flights/batch/adv1_prepare.sh` with its helper
  `scripts/flights/batch/adv1_prepare_steps.py`, and the fill map `fill-after-roll1-seal.json`
  beside this README (both added with the R01C re-pointing below).

## R01C re-pointing (2026-09-22)

These fragments were written before the clean construction subset R01C existed. Cell ROLL-1 now
flies **R01C** -- `SLURP-STAGE3-CONSTRUCTION-R01C`, 625 rows, a PURE SELECTION of R01 with zero
contacts (`scripts/build_slurp_stage3_construction_clean_subset.py`), coordinator decision 102
pending owner confirmation -- so ADV-1's candidate pool is R01C and every S3-1 pin here is R01C's.
Filled from committed bytes in this pass:

| what | value |
| --- | --- |
| dataset fragment (both cells, `population`) | `slurp-speech-native-stage3-construction-r01c` |
| roster receipt | `docs/receipts/rosters/slurp-stage3-construction-r01c.json` sha256 `e8abc65b...3eeddd`, with the parent R01 receipt beside it, in the BASELINE's `preparation_source_receipts` |
| sample source | cell ROLL-1, run `SAEA-SLURP-STAGE3-ROLLOUT-R01-V1`, attempt `attempt-slurp-native-stage3-rollout-r01-generation-v1` (`advantage_pairs.rollout_run_id` / `rollout_attempt_id`) |
| plan numbers | `planned_model_calls` 625 (the ceiling: one contact per R01C row until pairs.json names the disagreeing ones), `planned_speech_audio_seconds` **0**, `planned_gpu_hours` 1.0; `generation_budget.target` 213 |
| budget caps | `generation_calls_cap` 625, `fit_endpoint_calls_cap` 1,875 = 625 x (0 speech packets + 3 endpoints), `repeated_speech_audio_seconds_cap` 0, `native_task_contract_calls_cap` 0 |

Two structural corrections came with it:

- **The roster requirement moved out of `readiness.requirements`.**
  `core.flight.campaign.declared_readiness` resolves every readiness requirement BENEATH THE DATA
  ROOT and refuses a path that escapes it, so a repository receipt could never have been checked
  there. The R01C roster receipt is now pinned by hash in the baseline's
  `preparation_source_receipts` (the ROLL-1 precedent), and the one remaining requirement is S3-3's
  `pairs.json`, which is data-root relative.
- **The placeholder decision requirement was removed.** `core.flight.repin
  ._upsert_decision_requirement` inserts the real one at the readiness flip; a placeholder entry
  left beside it carries no `expected_decision_id` and would refuse the campaign at load. This is
  what the registered ROLL-1 cell states in its own readiness reason.

**Speech seconds are 0 on purpose.** The engineering spec's prose says the contact "sees the row's
speech"; the D2 freeze binds `construction-advantage-text` to bare-core's ten identity/text fields
plus `construction_targets` and nothing else, so `core.model.transport` forces `text_only` for this
arm and no audio part or speech-feature packet is ever opened. The baseline's `modality_note`
carries the full reading; owner decision 82 and the D2 invariant are the authority.

## What is left for root

Everything still open is in `fill-after-roll1-seal.json` beside this README: the exact JSON path of
every remaining `PENDING_` token, the artefact that produces its value and the field to copy. In
summary:

- `PENDING_S3_3_PAIRS_JSON_RELPATH` / `_SHA256` -- S3-3's `pairs.json`, which does not exist until
  cell ROLL-1 seals.
- `PENDING_S3_3_DISAGREEING_ROW_COUNT` -- `pairs.json`'s own `count`. Expected about 213 (the S3-3
  dry run's 0.3398 disagreement-pair rate over 625 rows,
  `docs/readiness/2026-09-22-slurp-stage3-rollout-r01-v1/s3-3-dry-run-receipt-v1.json`); the
  registered ceiling is R01C's whole 625.
- `PENDING_S3_3_DISAGREEING_SPLIT_ID` / `_SPLIT_IDENTITY_HASH` -- the disagreeing-row population's
  own identity. **`construction-advantage-text` is a construction-visible arm**, so
  `contracts.gate_exposure._require_construction_role_for_visible_targets` refuses the model touch
  unless the cell's split identity is that of a COMMITTED `roster_role='construction'` receipt of
  carrier `slurp`. Root therefore commits
  `docs/receipts/rosters/slurp-stage3-advantage-r01c-disagreeing-v1.json` -- a pure selection of
  R01C over exactly the disagreeing rows, zero contacts, the `SLURP-EVO-S1-PROPOSER-R01` precedent
  -- before the flip. `adv1_prepare.sh` writes and verifies it.
- `PENDING_ROOT_SELECTION` -- the resident serving session for the proposer geometry
  `q4km-mmproj-free-speech-native-np4-proposer-max1536`. No committed twin exists for that geometry
  (`configs/experiment/slurp-evo-s1-proposer-r01.json` declares no session at all), so it stays
  root's choice. CELL-1's own session was NOT left pending: its model fragment is byte-identical to
  cell PLAN's and ROLL-1's.
- The `populations` block (`core.flight.repin` cross-checks inlined ids against the recomputed
  split identity) is inserted by the same runbook pass.
- The decision requirement, minted and inserted by `scripts/flights/repin_cell.py --set-ready`.

`rails.stage3_advantage.build_advantage_instruction_for_row` is the reusable per-row unit a future
launcher's `core.flight.FlightRuntime.bind_phase_program_material` override would call once these
artifacts exist; wiring that override end to end is left to that launcher (module docstring of
`rails/stage3_advantage.py`).

## The runbook

`scripts/flights/batch/adv1_prepare.sh` -- run by ROOT after cell ROLL-1 seals, model-free
(the S3-3 stages score COPIES of already-sealed samples through the registered official scorer; no
model, encoder, tokenizer, GPU or network contact). `ADV1_DRY=1` is the default and prints every
mutating command line; `ADV1_DRY=0` performs them. It never flips readiness, mints a decision
receipt or touches `docs/exposure-ledger.md`.

```
MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 ADV1_DRY=0 REPO=<checkout> \
  bash scripts/flights/batch/adv1_prepare.sh
```

which runs, in order:

```
python scripts/analysis/stage3_rollout_score.py --run SAEA-SLURP-STAGE3-ROLLOUT-R01-V1 \
    --attempt attempt-slurp-native-stage3-rollout-r01-generation-v1 \
    --roster docs/receipts/rosters/slurp-stage3-construction-r01c.json \
    --analysis-root "$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-ROLLOUT-R01-SCORE-V1" \
    --scorer-id slurp-slu-official-projected-v3-train --repo-root "$REPO" \
    --data-root "$SPEECHRL_DATA_DIR" --stage {render,score,pairs}
python scripts/flights/batch/adv1_prepare_steps.py --repo-root "$REPO" --write roster \
    --pairs "$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-ROLLOUT-R01-SCORE-V1/pairs.json" \
    --pairs-relpath analysis/SAEA-SLURP-STAGE3-ROLLOUT-R01-SCORE-V1/pairs.json \
    --roster-out docs/receipts/rosters/slurp-stage3-advantage-r01c-disagreeing-v1.json
python scripts/flights/batch/adv1_prepare_steps.py --repo-root "$REPO" --write report \
    --pairs <same> --pairs-relpath <same> --values-out <coordination>/adv1-fill-values.json \
    --experiment configs/experiment/slurp-native-stage3-advantage-r01-v1.json
python scripts/flights/batch/roll1_fill_placeholders.py \
    --fragments configs/experiment/slurp-native-stage3-advantage-r01-v1.json \
                configs/baseline/slurp-native-stage3-advantage-baseline-v1.json \
    --values <coordination>/adv1-fill-values.json --by "<provenance>" \
    --occurrence-policy at-least-one
```

Then commit the two fragments plus the new roster receipt, and re-pin with
`scripts/flights/repin_cell.py`. The delta store that consumes this cell's seal is the sibling
runbook `scripts/flights/batch/adv1_to_deltas.sh` (package
`docs/readiness/2026-09-22-slurp-stage3-delta-cell-r01-v1/`).

## Proof obligations covered by tests (`tests/unit/test_stage3_advantage.py`)

- The gate refuses a non-construction roster for `construction-advantage-text`, using the real
  `contracts.gate_exposure` gate (not a fake).
- The rendered instruction (best/worst answers + gold) is never present in any `receipt()`/`as_json()`
  output this module returns -- only identities, counts and digests are.
- Parser cases: all three legal `DELTA-KIND` values; an illegal kind; a >40-word statement; missing
  keys; a repeated key; non-string input -- every case returns a populated, non-raising result.
- `pairs.json` loading: SHA-256 pin mismatch refused; `rollout_run_id` mismatch refused; malformed
  rows refused; a well-formed file loads and indexes by `sample_id`.
- `phase-stage3-advantage-v1` loads through `rails.controllers.default_phase_program` with exactly
  one phase, `max_contacts` 1, and the registered response format id.
- `tests/unit/test_roll1_fill_placeholders.py`: the substitution tool's ROLL-1 contract is unchanged
  by the `--fragments` / `--occurrence-policy` arguments these packages need, a token matching
  nothing anywhere is still refused, and a fragment with no `stage3_pending_placeholders` block does
  not grow one.

## S3-4s amendment: the SYSTEM-level v2 contact (owner decision 106, 2026-09-23)

Owner ruling (translated): *"roll out as much information as possible; we are doing SYSTEM-level
optimisation, not the optimisation of a single module."* This package is still **HELD** and nothing
below authorises a flight, a flip or an admission entry. Cell ROLL-1 is **not** re-flown: its sealed
episode receipts already custody every contact of every node, so the trajectory is rebuilt model-free
from the seal.

**What changed in this package**

| Before (S3-4, v1) | After (S3-4s, v2) |
| --- | --- |
| `policy` `phase-stage3-advantage-v1` | `policy` `phase-stage3-advantage-v2` (`configs/policy/phase-stage3-advantage-v2.json`) |
| `task_instruction_template` `probes/slurp_stage3_advantage_system_v1.txt` | `probes/slurp_stage3_advantage_system_v2.txt` |
| `phase_material.advantage.instruction_template` `probes/slurp_stage3_advantage_v1.txt` | `probes/slurp_stage3_advantage_v2.txt` |
| `response_format_id` `stage3-advantage-statement-v1` | `stage3-advantage-statement-v2` |
| one three-line statement | one to three four-line blocks, `NODE` / `DELTA-KIND` / `TARGET` / `STATEMENT` |
| parser `parse_advantage_statement` | parser `parse_advantage_statements_v2` (reads the four-line form AND the registered JSON shape) |

A program and its fragment must agree on a phase's output contract (`rails.phase_material`), so the
v2 response format needs its own program rather than a mutation of v1's. **v1 stays reachable, byte
for byte**: its probe, its program, its response format and its parser are untouched.

**What the contact now sees** (rendered into the instruction only, never receipted; the D2 field set
is UNCHANGED -- `construction_targets` still carries only this row's own construction gold):

1. the Perception candidate list, in the order the Perception node proposed it;
2. ANSWER A (best) and ANSWER B (worst), the two custodied rollout samples;
3. the DELIVERED answer with the Reviewer's verdict labels and the Planner's route;
4. the construction gold.

All four come from S3-3's `pairs.json` `trajectory` block plus the sealed rollout outputs; the
renderer is `rails.stage3_advantage.render_advantage_instruction_v2` /
`build_advantage_instruction_for_row_v2`.

**`pairs.json` is now `pairs_schema` `saea-stage3-rollout-pairs-v2`.** Per disagreeing row it carries
a `trajectory` block: the Perception candidate ids (first-occurrence distinct, with the raw count) and
whether the construction gold intent is among them; the best/worst sample indices with their rendered
answer hashes and their sealed contact hashes; the delivered path (Reviewer verdict labels and
dispositions per review visit, Planner action labels, revision count, delivery kind,
`delivered_below_best`); and per-node completion tokens, finish reasons and truncation flags. Ids,
labels, counts and hashes only. The pre-existing `pairs` array is unchanged and a `rows` array in the
exact shape `load_advantage_pairs` reads is written beside it.

**Two honest limits, for root to close**

1. **The gold intent.** The committed R01/R01C roster receipts annotate `stratum` (the SCENARIO), not
   `scenario_action`, so "was the gold intent among the candidates" cannot be answered from them.
   Pass `ADV1_GOLD_INTENTS=<path>` (a model-free `{sample_id: "<scenario>_<action>"}` JSON map over
   the construction roster) to `scripts/flights/batch/adv1_prepare.sh`. Without it the field reads
   `gold_intent_known: false` / `gold_intent_in_candidates: null` and the summary says
   `gold_intent_source: "unavailable"` -- reported, never guessed.
2. **The Reviewer verdict labels.** Cell ROLL-1's `native_episode` fragment arms neither
   `reviewer_verdict` (item E37) nor `role_context`, so its sealed receipt carries no
   `reviewer_verdicts` key and no candidate-projection audit. The trajectory therefore re-derives the
   verdict label from the sealed Reviewer response with the registered closed-vocabulary parser
   (`rails.review_primitives.parse_review_primitive`) -- the same reading the armed path would have
   sealed -- and the candidate ids from the sealed Perception response, both through the attempt's own
   `<run_id>.trace.jsonl`. The block names its source in `reviewer_verdict_source` / `reading`. With
   `--trace none`, or with no trace file beside the seal, every trace-derived field reads absent with
   a reason instead of a value.

**Tests**: `tests/unit/test_stage3_advantage_v2.py` (the multi-block parser on legal, illegal and
mixed responses; the JSON shape; the committed template's placeholders; registration beside v1) and
`tests/unit/test_stage3_rollout_trajectory.py` (a synthetic sealed receipt + trace fixture; the
candidate list, the delivered path, the per-node tokens and truncation flags; no text in either
written file; idempotency; the `rows` view loads through `load_advantage_pairs`).

## First launch REFUSED, recovery re-registration (2026-09-23)

The smoke cell `slurp-native-stage3-advantage-r01-smoke-4-v1` was **refused at its first contact**,
**before any model call was spent**. The attempt
`attempt-slurp-native-stage3-advantage-r01-smoke-4-v1-generation` was opened and carries **zero
contacts**; it is left in place as the record of the refused launch.

**The refusal.** `core/model/transport.py` `render_request_with_receipt`:

```
FrozenCoreError: speech feature request query_source must be 'speech_features'
```

**Root cause.** The composed model fragment
`q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1` declares
`prompt_order: speech-query-prefix-v2` (it is the resident np4 serving geometry). The ADV-1 dispatch
is the **text-only construction** path -- `core.flight.runtime._run_construction_proposer` ->
`rails.core_client.FrozenCoreClient.complete(..., text_only_sample_id=...)` ->
`core.policies.build_arm_payload` -- which sends the D2-frozen construction field set: the rendered
instruction as the system message, an **empty** user content list, `construction_targets`, and
**none** of the five speech-feature fields. The renderer had no branch for that pair, so the
speech-feature branch refused on its first rail. `prompt_order` travels inside the **compared**
session identity (`model_fragment_sha256` hashes the whole fragment;
`core.session.serving.SERVING_IDENTITY_FIELDS`), so a sibling fragment declaring a text prompt order
could not have attached to the resident session `serving-slurp-native-candidate-five-train-a-np4-v1`
at all -- the repair belongs in the renderer.

**The repair.** A dedicated text-only construction branch in
`core/model/transport.py`: under a speech prompt order, a construction-visible payload renders
exactly as the `evidence-first-system-v2` branch renders it (system instruction, empty user content,
zero audio parts, zero speech packets), and its render receipt carries
`text_only_construction: true` with the reason. A construction-visible payload that ALSO carries a
speech-feature field, a media part or a non-empty `history` is refused by name -- that combination is
undefined. Every other payload under a speech order keeps its refusals, in the same order. Covered by
`tests/unit/test_llama_server_transport.py` (the render, the receipt, the equality against the
`evidence-first-system-v2` branch, the ordered speech refusals, the fail-closed pairs, and an
end-to-end test that renders the payloads `FlightRuntime.wire_check` actually builds for this arm
under the flown fragment's own `prompt_order`).

**Recovery re-registration.** This is the **one** root-diagnosed recovery re-registration the failure
rule allows for this flight. The smoke generation cell's attempt id becomes
`attempt-slurp-native-stage3-advantage-r01-smoke-4-v1-generation-recovery`
(`configs/experiment/slurp-native-stage3-advantage-r01-smoke-4-v1.json`, and `smoke_attempt_id` in
`scripts/flights/batch/batch_chain_adv1.sh`). **Unchanged:** the fit attempt id, both of the arm's
attempt ids, both run ids, the population, the roster receipts, the templates, the response format,
the caps and the decision rule. Budgets stay **run-cumulative** across every attempt of the run id,
so the refused attempt's zero contacts count against the same 4-contact ceiling. The readiness states
and the registered plan/protocol documents are untouched here; the coordinator re-pins both cells in
one cycle with `scripts/flights/batch/adv1_flip_both.sh`.
