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

## What is left for root (PENDING_ placeholders)

Every `PENDING_*` token in the two cell fragments names a sibling deliverable that does not exist in
this worktree yet:

- `PENDING_S3_1_*`: the S3-1 construction roster receipt, its dataset fragment and its split identity
  hash (`docs/receipts/rosters/slurp-stage3-construction-r01.json`).
- `PENDING_S3_3_*`: S3-3's `pairs.json` (relpath, SHA-256, disagreeing-row count) and the S3-2 rollout
  run id it is bound to.
- `PENDING_ROOT_DECISION_ID` / `PENDING_ROOT_SELECTION`: a root decision receipt admitting ADV-1 to a
  flight, and the serving session it is to run under.

`rails.stage3_advantage.build_advantage_instruction_for_row` is the reusable per-row unit a future
launcher's `core.flight.FlightRuntime.bind_phase_program_material` override would call once these
artifacts exist; wiring that override end to end is left to that launcher (module docstring of
`rails/stage3_advantage.py`).

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
