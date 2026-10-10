# NX Perception template column instrument (E1/E2 for the Perception node): usage, example and offline proof

Date: 2026-10-10. Branch `fable/nx-e1-perception`. Owner decision 239 (move the empty-entity decision to the
PRECEDING node; programme round R6). Builds on `docs/readiness/2026-10-09-slurp-nx-template-variant-instrument-v1/README.md`
(the Solver form) and `docs/superpowers/specs/2026-10-09-slurp-nx-node-template-variant-instrument-design.md`.
Everything here is model-free: no model, server, tokenizer, GPU, network or paid-API contact was made, and no cell is
registered.

## 1. What it is

A same-flight NODE-TEMPLATE variant instrument at the PERCEPTION node. One cell declares K Perception
instruction-template arms at the one Perception visit. Each non-delivering arm overrides exactly one thing, the
Perception node's `phase_material.perception.instruction_template` (a hash-pinned path under `probes/`), and is followed
by ITS OWN first-visit Solver contact, rendered over that arm's own note (level 2). The delivering arm is the locked
Perception template and the locked Solver path, last and untemplated (invariant I7); a twin `replicate_of` the
delivering arm is the within-flight A/A and is REQUIRED.

It is not a second mechanism. `roles.perception.template_variants` is parsed with the Solver form's own parser
(`rails.supply_variants.parse_template_variants`, so every E1 refusal applies) and converted by
`parse_perception_template_variants` into the existing LEVEL-2 `PerceptionBranchGroup`, whose branches carry the template
as their only axis. The branch mechanism therefore supplies, unchanged: the contact mapping (branch `i` is Perception
contact `i` and Solver contact `i`), the level-2 view (`_perception_branch_solver_view`: the arm's own note in the sealed
Perception state of the exposed history and compilers, and the Solver-phase supply re-resolved from that note), the
settle logic, the receipt custody, bundle invariant I7v, the seal-time refusal "note differs but Solver rendering equals
A's" and the resume replay. What is new: the template axis on a branch, receipt schema
`saea-perception-branch-arms-v4`, the Perception material builders, the per-branch framework query and instruction, the
module column and the reader.

## 2. Declaration schema

Compiled form, in the baseline fragment (`native_episode.roles.perception.template_variants`):

```json
{"node": "perception",
 "arms": [
   {"arm_id": "p1", "instruction_template": {"relpath": "configs/probes/nx/perception-p1.txt", "sha256": "<64 hex>"},
    "template_tokens": 410},
   {"arm_id": "p2", "instruction_template": {"relpath": "configs/probes/nx/perception-p2.txt", "sha256": "<64 hex>"},
    "template_tokens": 395},
   {"arm_id": "aa", "replicate_of": "lock"},
   {"arm_id": "lock", "deliver": true, "template_tokens": 380}],
 "max_supplied_items": 48,
 "fit_estimate": {"slot_tokens": 24576, "completion_ceiling": 640,
                  "base_prompt_tokens": 9600, "tokens_per_supplied_item": 120}}
```

Keys are the Solver form's: `node` (must be `perception`, the role the block sits on); `arms` (1 to 6 candidate arms each
with an `instruction_template` pin and `template_tokens`; the LAST arm is the delivering arm `deliver: true` with its own
locked template's `template_tokens` and no pin; EXACTLY ONE twin `{"arm_id", "replicate_of": "<delivering id>"}`);
`max_supplied_items`; `fit_estimate` (the four measured numbers, `base_prompt_tokens` excluding the template). The role
must also carry `phase_material.perception.instruction_template` (the locked template the delivering arm renders). The
level is fixed at 2.

### Example: a 3-template Perception cell on TRAIN Fold B

Two candidate templates against the locked one, with the required twin, review-off graph (Perception then Solver), 1,080
rows. The fit numbers are the E42 documents' illustrative figures for the 24,576-token slot, NOT measured for this cell
(section 6).

1. Module form (`native_episode.consumption_module`, review-off lock layer, `profile: slurp`):

```json
{"review_loop": "off",
 "columns": [
   {"column_id": "p1", "kind": "template", "node": "perception",
    "template": {"relpath": "configs/probes/nx/perception-p1.txt", "sha256": "<64 hex>"}, "template_tokens": 410},
   {"column_id": "p2", "kind": "template", "node": "perception",
    "template": {"relpath": "configs/probes/nx/perception-p2.txt", "sha256": "<64 hex>"}, "template_tokens": 395}],
 "template_frame": {"max_supplied_items": 48, "delivering_template_tokens": 380, "twin": true,
                    "fit_estimate": {"slot_tokens": 24576, "completion_ceiling": 640,
                                     "base_prompt_tokens": 9600, "tokens_per_supplied_item": 120}}}
```

   (plus the usual `module_id`, `profile`, `components`). It compiles, through the carrier hook
   `perception_template_variant_frame` (SLURP: delivering arm `lock`, twin `aa`), to the block above and to `policy`
   `phase-native-module-v1-c8`. Template columns naming the Perception node and template columns naming the Solver cannot
   share a block (one fan-out per flight), and neither can sit beside Perception-branch columns. `twin: false` is refused
   at compile time.
2. Measurement block (readiness package `registered-facts-v*.json`, a preregistration fence or the fragment):

```json
{"stage3_measurement": {
   "measurement_design": "same-flight-node-column",
   "expected_effect_pp": 2.0, "rows": 1080, "primary_metric_key": "slu",
   "primary_metric": "level-2 Solver normalised exact-set per row (node-local); effect quoted on delivered SLU-F1 via E3",
   "claims_benefit": true,
   "template_variants": {"node": "perception", "candidate_arms": 2, "twin": true},
   "tuning_roster": "<Fold B roster id>", "read_roster": "<Fold B roster id>"}}
```

   `stage3_effect_floor_check.py` now admits `perception` in the `template_variants` summary and reads the design at the
   same borrowed same-flight contrast floor as the Solver form (SLU 1.49 pp at n = 1,080).
3. Run: roster = TRAIN Fold B (1,080 rows); contacts per row 8 (Perception 4, Solver 4); requests 8,640.

## 3. Contact arithmetic and FIT rule

Each arm is one Perception contact and one level-2 Solver contact, so the group adds TWO contacts per non-delivering arm
to the review-off base:

* **Ceiling.** `base + 2 (K - 1)` with `perception_branch_ceiling(level=2)`, K counting every arm (candidates, twin,
  delivering). Review-off base 2, K = 4: 2 + 6 = 8. The program id must carry that ceiling (the loader asserts
  `program.max_contacts == ceiling`; the module family `phase-native-module-v1-c2` to `-c24` covers it). Six candidates
  plus twin plus lock (K = 8) give 2 + 14 = 16.
* **Plan budget.** `planned_model_calls >= rows x ceiling` and `planned_speech_audio_seconds` likewise: every Perception
  and every Solver contact re-sends the speech packet, so the unarmed 2 x row audio becomes `ceiling x` row audio
  (`2 (K - 1) x` extra). Example: 1,080 x 8 = 8,640 model calls.
* **Pre-flight fit.** For every Perception arm, `base_prompt_tokens + template_tokens + max_supplied_items x
  tokens_per_supplied_item` must not exceed `slot - reserve - completion_ceiling - special reserve` (20,862 tokens at the
  24,576 slot with the 640-token completion ceiling). It covers the Perception contacts. The level-2 Solver contacts are
  measured by the existing realised `native_contact_fit` gate at dispatch like any contact; each carries its own
  re-resolved supply, so the Solver-side bound is the realised one, not the estimate.
* **Realised fit.** Every arm request is measured by `native_contact_fit` at dispatch.

## 4. Refusals (all before any contact)

Each has a unit test (`tests/unit/test_perception_template_variants.py`). The Solver form's table (design note section
3) applies to the shared parser: a supply knob, release swap or per-arm bound on a template arm (`overrides`,
`release_swap`, `knobs`, `max_supplied_items`); an unknown arm key or block key; a template outside `configs/probes/`,
absolute, `..`-traversing or with a bad digest; a candidate with no pin; the delivering arm or the twin carrying a pin;
missing `template_tokens`; a duplicate template path or digest; a candidate equal to the node's locked template; more than
6 candidates; a delivering arm that is not last; a variant declared on a node other than the one named, or on the
Reviewer or Planner. Added for the Perception form:

| Refusal | Raised by |
| --- | --- |
| no twin, or two twins | `parse_perception_template_variants` |
| `roles.perception.template_variants` beside `roles.perception.branches` | loader |
| beside a Solver `supply_variants` or `template_variants` group (two fan-outs) | loader |
| beside `native_episode.knowledge_index`, `knowledge_value_rendering`, `finite_supply_policy` or a Perception-reobserving acquisition | loader (the branch group's own refusals) |
| a node without `phase_material.perception.instruction_template` | loader |
| program ceiling differing from `base + 2 (K - 1)` | loader |
| a pinned file missing or hashing to another digest; a rendered template embedding protected knowledge | `FlightRuntime._template_variant_materials` |
| builders missing, extra, or bound with no group | `rails.runner` binding check |
| a sealed receipt whose templates differ from the declared ones | `rails.runner` seal check; `validate_perception_branch_receipt` (v4: the template is a B branch's only axis; A and the twin carry none) |
| a template branch whose note differs from A's but whose Solver rendering equals A's, or a twin whose rendering differs from A's | `rails.runner` seal (the 2026-10-09 level-2 guard, group-generic; tested for a template branch) |
| a level-2 group beside a Solver supply with no branch resolver, or a resolver with no group | `rails.runner` binding check (unchanged) |

## 5. Reader (E2 for the Perception node)

`scripts/analysis/slurp_nx_perception_column_read.py` reads the sealed arm columns. Per arm, paired per row against the
delivering arm, with a whole-utterance cluster bootstrap (10,000 draws, seed 20260915) and the paired Wilson read of the
discordant rows:

1. the Perception note metrics the P-SV branch reader already reads (`slurp_perception_branch_read`): gold intent on the
   list, gold rank (1/2/3/4+/absent), top-1, list size, `note_parse_status`, and the contact's own prompt tokens;
2. the optional entity-presence verdict: `entity_presence` in `{present, none, unsure}` and an optional integer
   `heard_values` on the note. A note without the key is `absent` (the key is not part of the registered note schema; a
   template that asks for it is what makes it appear), a wrong value is `invalid`. Reported: precision and recall of `none`
   against the empty-gold label, of `present` against non-empty gold, the unsure rate, the mean `heard_values` by gold
   class, and the paired per-row `none`-on-empty, `none`-on-non-empty and `present`-on-non-empty indicators;
3. the level-2 Solver column of each arm (normalised exact-set primary, empty-gold false fill, non-empty exact, per slot
   type), through `slurp_nx_solver_column_read` functions, not re-implemented.

Gold (intent and entities) enters only through the governed SLURP loaders and the test split is refused; no utterance
text, note body, filler or model output is printed or persisted (a note is parsed in memory). The loader verifies every
branch's Perception and Solver trace pair against the sealed contact digests and refuses a receipt that is not a level-2 v4
template receipt.

## 6. Offline proof

`tests/unit/test_perception_template_variants.py::test_four_rows_walk_the_production_graph_with_each_arm_rendering_its_own_template_and_note`
runs the production native graph, request renderer and state sealer over four rows with arms p1, p2, aa (twin), lock, all
answered by canned text through the same fake-transport harness the E1 and level-2 render proofs use, and asserts per row:
eight requests (four Perception, then four Solver); p1's and p2's Perception request carries its own template text, the
twin's and lock's the locked one; p1's Solver request carries p1's note (and the supply that note implies) and not lock's,
p2's carries p2's, the twin's equals lock's; the Solver instruction is the locked one in every arm; custody is lock's alone;
the sealed receipt is v4 with the declared templates and passes `validate_perception_branch_receipt`; and, against an
UNARMED four-row run under the same plan, lock's Perception request and lock's Solver request are the unarmed plan's
(every wire field, the history and the instruction up to the contact id and the bounded limits text), 4/4 rows.
Further proofs: the sealed rows pass the runtime's `_canonical_output_rows` and the bundle's I7v verifier; a column forced
to replicate A is refused at seal by name; the dry-run walk and the review-off rehearsal profile admit the group; a v4
block replays as v4 for seal-only resume; the module column compiles and verifies; the reader runs on synthetic sealed
records.

### Verification run (2026-10-10, WSL `Ubuntu-24.04`, worktree only)

See the hand-off report for the verbatim output. Summary: the new and the neighbouring suites
(`test_perception_template_variants`, `test_slurp_nx_perception_column_read`,
`test_consumption_module_perception_template_columns`, `test_template_variants_*`,
`test_perception_branch_level2_render`, `test_consumption_module*`, `test_slurp_nx_solver_column_read`,
`test_stage3_effect_floor_node_column`, `test_engineering_base_check`) give `400 passed, 1 failed`; the one failure,
`test_consumption_module_step6.py::test_the_module_cells_are_held_and_fly_in_one_campaign` (cells read `ready`, not
`held`), fails identically on the unchanged master checkout. Full `tests/unit`: `4 failed, 24735 passed, 10 skipped, 2 errors`; the same six test ids (`test_consumption_module_step6`, `test_filler_family::test_disjointness_proof_is_complete_and_zero`, `test_natural_source_compatibility::test_actual_reviewed_full_runtime_ast`, `test_nx_r5_cell_registration`, `test_obs_loop_policy`, `test_serving_resource_guard`) fail or error on the unchanged master checkout. Gates: `engineering_base_check.py` PASS,
`finite_completion_policy_check.py` PASS (576 in-scope plans), `stage3_effect_floor_check.py` PASS (0 blocking),
`tool_catalog_check.py` PASS, `stage3_algorithm_label_check.py` PASS.

## 7. What remains

1. **The first registered cell, R6.** Author and pin the Perception templates from the node contrast tables, put them under
   `configs/probes/`, hash them, measure `template_tokens` and the four `fit_estimate` numbers on the cell's own
   `native_contact_fit` pass at the new ceiling, register the cell on the TRAIN Fold B roster with its in-chain twin and the
   E3-derived declared effect on file before flight (decision 192).
2. **Re-pin.** This change edits `core/flight/runtime.py` (whose hash enters every prepared artifact's
   `sources.implementation`), `rails/runner.py`, `rails/supply_variants.py`, `rails/native_episode_receipt.py` and others:
   merging makes every pinned ready cell fail "prepared artifact identity mismatch" until the loop-form
   `scripts/flights/repin_cell.py` pass runs at the flight commit. The coordinator names the merge point.
3. **`entity_presence` in the note.** The registered Perception note schema (`slurp-intent-hypotheses-v1`) has no such key
   and `parse_perception_branch_note` ignores it, so a template that asks for the verdict gets it only if the model
   emits it; the response format is deliberately not widened (an arm may not change the node's response format). Whether
   the R6 templates ask for it in free note text or the note schema is extended is a design call for the cell.
4. **Flight-owned checks.** `flight_registration_check.py` has no node-column findings yet; the node-column floor is
   borrowed from the supply-variant contrast floor until a node-column cell measures its own twin null.
5. **Resume of a partly flown run.** The seal-only replay keeps a v4 block as v4 (tested on a synthetic block); the E10
   trace-replay resume (`core/flight/resume.py`) is not exercised on a template group.
6. **The dry-run walk** covers each Perception arm's instruction; the level-2 Solver columns are a runner statement
   proven by the live proof, not walked model-free by the dry run.
7. **Scorers** downstream of a sealed Perception template column (`stage3_rollout_score` perception-branches mode,
   `stage3_paired_read.py`) read the receipt through `validate_perception_branch_receipt` but have not been exercised on
   a v4 run.

## 8. Files

Source: `rails/supply_variants.py`, `rails/native_episode_receipt.py`, `rails/native_episode_config.py`, `rails/runner.py`,
`rails/consumption_module.py`, `rails/adapters/slurp_module_hooks.py`, `core/flight/runtime.py`,
`reproduction/ojw/native_supply_variants.py`, `analysis/native_episode_dry_run.py`, `analysis/native_graph_rehearsal.py`.
Gates and tools: `scripts/checks/stage3_effect_floor_check.py`, `scripts/analysis/slurp_nx_perception_column_read.py`.
Tests: `tests/unit/test_perception_template_variants.py`, `test_consumption_module_perception_template_columns.py`,
`test_slurp_nx_perception_column_read.py`, plus small edits to `test_template_variants_live.py`,
`test_template_variants_flight.py` and `test_consumption_module_carrier_transfer.py`.
