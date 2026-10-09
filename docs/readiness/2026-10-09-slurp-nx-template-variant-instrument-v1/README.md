# NX node-template variant instrument (E1/E2): usage, example and offline proof

Date: 2026-10-09. Branch `fable/nx-harness`. Programme: `docs/readiness/2026-10-09-slurp-nx-node-extreme-programme-v1.md`
(C0.2, C1 items E1 and E2). Design: `docs/superpowers/specs/2026-10-09-slurp-nx-node-template-variant-instrument-design.md`.
Everything here is model-free: no model, server, tokenizer, GPU, network or paid-API contact was made, and no cell is
registered.

## 1. What it is

A same-flight NODE-TEMPLATE variant instrument. One node (the Solver first) is contacted K times over the SAME
`QueryState` and the SAME supplied evidence; each non-delivering arm overrides exactly one thing, the node's
`phase_material.<role>.instruction_template` (a hash-pinned path under `probes/`); the delivering arm is last, carries no
override, and so renders the locked plan's request byte for byte (invariant I7). It is the E42 supply-variant form
with the varied axis moved from SUPPLY to INSTRUCTION: the same group slot, the same single contact batch, the same
settle rule, the same bundle invariant I7v, the same ceiling term (`base + K - 1`), a new receipt version
(`saea-supply-variant-arms-v4`) that adds each arm's resolved template pin. The reader E2
(`scripts/analysis/slurp_nx_solver_column_read.py`) scores the arms paired per row against the delivering arm.

## 2. Declaration schema

Compiled form, in the baseline fragment (`native_episode.roles.solver.template_variants`):

```json
{"node": "solver",
 "arms": [
   {"arm_id": "t1", "instruction_template": {"relpath": "configs/probes/nx/solver-t1.txt", "sha256": "<64 hex>"},
    "template_tokens": 410},
   {"arm_id": "t2", "instruction_template": {"relpath": "configs/probes/nx/solver-t2.txt", "sha256": "<64 hex>"},
    "template_tokens": 395},
   {"arm_id": "lock", "deliver": true, "template_tokens": 380}],
 "max_supplied_items": 48,
 "fit_estimate": {"slot_tokens": 24576, "completion_ceiling": 640,
                  "base_prompt_tokens": 9600, "tokens_per_supplied_item": 120}}
```

Keys: `node` (must be the role the block sits on; `solver` today); `arms` (candidate arms carry an
`instruction_template` pin and `template_tokens`; the LAST arm is the delivering arm: `deliver: true`, its own locked
template's `template_tokens`, no template; an optional twin is `{"arm_id": ..., "replicate_of": "<delivering id>"}`);
`max_supplied_items` (one supply bound for every arm); `fit_estimate` (the four MEASURED numbers; `base_prompt_tokens`
excludes the instruction template). 1 to 6 candidate arms, plus the delivering arm, plus at most one twin (8 contacts
at most).

### Example: a 3-arm Solver cell on TRAIN Fold B

Two candidate templates against the locked one, no twin, review-off graph (Perception then Solver), 1,080 rows. The
fit numbers below are the figures the E42 documents use for the 24,576-token slot; they are ILLUSTRATIVE, not measured
for this cell (section 6).

1. Module form (`native_episode.consumption_module`, review-off lock layer, `profile: slurp`):

```json
{"review_loop": "off",
 "columns": [
   {"column_id": "t1", "kind": "template", "node": "solver",
    "template": {"relpath": "configs/probes/nx/solver-t1.txt", "sha256": "<64 hex>"}, "template_tokens": 410},
   {"column_id": "t2", "kind": "template", "node": "solver",
    "template": {"relpath": "configs/probes/nx/solver-t2.txt", "sha256": "<64 hex>"}, "template_tokens": 395}],
 "template_frame": {"max_supplied_items": 48, "delivering_template_tokens": 380, "twin": false,
                    "fit_estimate": {"slot_tokens": 24576, "completion_ceiling": 640,
                                     "base_prompt_tokens": 9600, "tokens_per_supplied_item": 120}}}
```

   (plus the usual `module_id`, `profile`, `components`). It compiles to the block above with the delivering arm id
   `lock` named by the carrier hook, and to `policy` `phase-native-module-v1-c4` (ceiling 2 + (3 - 1) = 4). With
   `"twin": true` the hook adds arm `aa` and the ceiling is 5.
2. Measurement block (readiness package `registered-facts-v*.json`, a preregistration fence or the fragment):

```json
{"stage3_measurement": {
   "measurement_design": "same-flight-node-column",
   "expected_effect_pp": 2.0, "rows": 1080, "primary_metric_key": "slu",
   "primary_metric": "raw entity exact-set per row (node-local); effect quoted on delivered SLU-F1 via E3",
   "claims_benefit": true,
   "template_variants": {"node": "solver", "candidate_arms": 2, "twin": false},
   "tuning_roster": "<Fold B roster id>", "read_roster": "<Fold B roster id>"}}
```

   `stage3_effect_floor_check.py` reads it at the same-flight contrast floor (SLU 1.49 pp at n = 1,080, borrowed from
   `same-flight-supply-variant`; a declared effect below it is `effect-below-floor`).
3. Run: roster = TRAIN Fold B (1,080 rows); contacts per row 4 (Perception 1, Solver 3); requests 4,320.

## 3. Refusals (all before any contact)

The full table is in the design note, section 3. In short, each of these is refused by name and each has a unit test:
a supply knob, release swap or per-arm bound on a template arm; any unknown arm key; a template outside `probes/`,
absolute, `..`-traversing or with a bad digest; a candidate with no pin; the delivering arm or the twin carrying a
pin; missing `template_tokens`; a duplicate template path or digest; a candidate equal to the node's locked template;
more than 6 candidates or 2 twins; a delivering arm that is not last; a variant declared on a node other than the
one named, or on a node outside `TEMPLATE_VARIANT_NODES`; `template_variants` beside `supply_variants` or the
knowledge index; a ceiling that differs from `base + (K - 1)`; a pinned file that is missing or hashes to another
digest; a rendered template that embeds protected knowledge payloads; material builders missing, extra or bound with
no group; an arm that changes the node's response format; a sealed receipt whose templates differ from the declared
ones.

## 4. FIT rule

Each arm is one metered contact, and mirrors how E42 adds arms to the plan's budget:

* **Ceiling.** Under `arm_visits: "first"` the group fans out once, so the graph ceiling is `base + (K - 1)`, K counting
  every arm (candidates, twin, delivering). The program id must carry that ceiling (the loader asserts
  `program.max_contacts == ceiling`); the module-family ids `phase-native-module-v1-c4` to `-c10` were added for the
  review-off ceilings.
* **Plan budget.** `planned_model_calls >= rows x ceiling` and `planned_speech_audio_seconds` likewise (every arm
  re-sends the speech packet at the first Solver visit: `(K - 1) x` row audio extra). The budget is run-cumulative.
  Example: 1,080 rows x ceiling 4 = 4,320 model calls (2 extra contacts per row against the review-off base).
* **Pre-flight fit.** For every arm, `base_prompt_tokens + template_tokens + max_supplied_items x tokens_per_supplied_item`
  must not exceed `slot - reserve - completion_ceiling - special reserve` (the registered E33 arithmetic).
* **Realised fit.** Every arm request is measured by the existing `native_contact_fit` gate at dispatch, like any contact.

## 5. Offline proof (4 rows, model-free)

`tests/unit/test_template_variants_live.py::test_four_rows_are_walked_model_free_through_the_production_graph` runs the
production native graph, the production request renderer and the production state sealer over four rows with a
four-arm group (two templates, a twin, the lock) answered by canned text (the SAME fake-transport harness the E42
proofs use), then repeats the four rows UNARMED at the same program ceiling and compares the delivering arm's request
to the unarmed plan's request row by row.

```
cd /home/chao/saea-worktrees/fable-nx-harness && source ~/.venvs/speechrl/bin/activate
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests/unit python -B -m pytest \
  tests/unit/test_template_variants_live.py -q -s -k "four_rows or dry_run" -p no:logging
```

Output summary (the test prints it):

```
NX-REHEARSAL-SUMMARY {"arms_per_row": ["t1","t2","aa","lock"], "contacts_per_row": [5,5,5,5],
  "delivering_request_identical_to_unarmed_plan": "4/4 rows", "model_free_requests": 20,
  "receipt_schema": "saea-supply-variant-arms-v4", "rows": 4,
  "templates": {"aa": null, "lock": null,
                "t1": {"relpath": "probes/nx/t1.txt", "sha256": "aaaa...a"},
                "t2": {"relpath": "probes/nx/t2.txt", "sha256": "bbbb...b"}}}
```

The dry-run walk (`analysis/native_episode_dry_run.py`, the contact-free per-node walk of a cell) produces, for the
Solver node of a synthetic row:

```
NX-DRYRUN-SUMMARY {"delivered_arm_id": "lock", "arms": [
  {"arm_id": "t1", "deliver": false, "instruction_template": {"relpath": "probes/nx/t1.txt", ...}, "instruction_sha256": "2691b9f6...", "supplied_item_count": 0},
  {"arm_id": "t2", "deliver": false, "instruction_template": {"relpath": "probes/nx/t2.txt", ...}, "instruction_sha256": "0cab4b3c...", "supplied_item_count": 0},
  {"arm_id": "aa", "deliver": false, "instruction_template": null, "instruction_sha256": "6c5891aa...", "supplied_item_count": 0},
  {"arm_id": "lock", "deliver": true, "instruction_template": null, "instruction_sha256": "6c5891aa...", "supplied_item_count": 0}]}
```

The delivering arm and the twin render the node's locked instruction (equal digests); each template arm renders its own.
The review-off rehearsal profile (`analysis/native_graph_rehearsal.rehearsal_profile`) admits a template group.

### Verification run (2026-10-09, WSL `Ubuntu-24.04`, worktree only)

* New and touched test files plus the neighbouring supply-variant, consumption-module, runner, dry-run, rehearsal and
  floor-gate suites: `545 passed`.
* Full `tests/unit`: `22 failed, 24423 passed, 10 skipped, 2 errors` before one fix; the 21 failures and 2 errors that
  remain are present on a pristine export of the base commit `e5adeb3b2` (same test ids), and the 22nd (an adapter line
  budget, `slurp_module_hooks.py` 261 > 260) was introduced by this change and fixed.
* Gates: `engineering_base_check.py` PASS, `tool_catalog_check.py` PASS (34 tools), `finite_completion_policy_check.py`
  PASS (575 in-scope plans), `stage3_effect_floor_check.py` PASS (0 blocking), `stage3_algorithm_label_check.py` PASS.

## 6. What remains

1. **The real FIT.** Measure, on the first cell's own `native_contact_fit` pass at the new ceiling, the four
   `fit_estimate` numbers and each template's `template_tokens`. The numbers in section 2 are illustrative.
2. **Author and pin the first cell's templates** from the node contrast tables (programme C3), put them under
   `configs/probes/`, hash them, and register the first cell (R1: Solver, TRAIN Fold B, 1,080 rows, in-chain twin) with
   the E3-derived declared effect on file before flight (decision 192).
3. **Re-pin.** This change edits `core/flight/runtime.py` (whose hash enters every prepared artifact's
   `sources.implementation`), `rails/runner.py`, `rails/supply_variants.py` and others: merging makes every pinned
   ready cell fail "prepared artifact identity mismatch" until the loop-form `scripts/flights/repin_cell.py` pass runs
   at the flight commit. The coordinator names the merge point.
4. **`flight_registration_check.py`** has no node-column findings yet (E42's `variant-cost-mismatch`,
   `aa-arm-missing`, claim ceiling `nominated`, roster overlap); `stage3_effect_floor_check.py` is extended.
5. **Other nodes.** The parser, materials builder and arm record are node-agnostic; admitting the Reviewer or Planner
   still needs `SupplyVariantRoleNode` generalised past `role_kind == "solver"`, the `latest_solver` receipt carry in
   `reproduction/ojw/native_episode.py`, and the Reviewer/Planner multi-iteration contact mapping (one arm is one
   contact).
6. **The floor** for `same-flight-node-column` is borrowed from the supply-variant contrast floor until a node-column
   cell measures its own twin null.
7. **Resume.** The E10 trace-replay resume (`core/flight/resume.py`) is not exercised for a template group; a
   partly-flown template run would need its arm contacts replayed in declared order before it is relied on.
8. **Scorers** downstream of a sealed template column (`stage3_rollout_score.render_supply_variant_first_visit`,
   `stage3_paired_read.py`) accept the receipt through `validate_supply_variant_receipt` but have not been exercised on
   a v4 run.

## 7. Files

Source: `rails/supply_variants.py`, `rails/native_episode_receipt.py`, `rails/native_episode_config.py`,
`rails/runner.py`, `rails/consumption_module.py`, `rails/adapters/slurp_module_hooks.py`, `rails/controllers.py`,
`reproduction/ojw/native_supply_variants.py`, `core/flight/runtime.py`, `analysis/native_episode_dry_run.py`,
`analysis/native_graph_rehearsal.py`. Gates and tools: `scripts/checks/stage3_effect_floor_check.py`,
`scripts/analysis/slurp_nx_solver_column_read.py`. Tests: `tests/unit/test_template_variants_rail.py`,
`test_template_variants_live.py`, `test_template_variants_flight.py`, `test_consumption_module_template_columns.py`,
`test_stage3_effect_floor_node_column.py`, `test_slurp_nx_solver_column_read.py`, plus small edits to
`test_native_episode_runner.py`, `test_rails_frozen_core_client.py`, `test_consumption_module.py` and
`test_consumption_module_carrier_transfer.py`.
