# Same-flight supply-variant instrument: design

Author: design agent (Fable 5.1), 2026-09-27, branch `fable/svinst`. Status: DESIGN, no code. Authority:
owner decision 172 (2026-09-27), which re-authorises `supply_variants` as an engineering-base
INSTRUMENT for (a) same-flight A/B reads and (b) evidence-varied rollouts for the sealed-credit
inner loop (`sealed-credit-system-policy-v1`). VAR-2 as a MECHANISM stays closed. Zero model,
server or GPU contact was made to write this.

## 0. What already exists (read, not assumed)

Item E42 is merged and much of the instrument is already in the tree:

- `rails/supply_variants.py::parse_supply_variants` parses `roles.solver.supply_variants`
  (2 to 8 arms, the delivering arm last and override-free, no identical override sets, no
  first-phase knob, fail-closed fit). Knobs are limited to `SUPPLY_VARIANT_KNOB_TAILS`:
  `phase_supply.<phase>.{k, fuse_coverage.m|c|top_l}` and `candidate_supply.<phase>.max_candidates`.
- `core/flight/runtime.py::FlightRuntime._supply_variant_binding` builds one router per arm over
  the same composite snapshot; `rails/runner.py` resolves arms in `settle`, refuses a delivering arm
  that diverges from the row's own supply, and seals the receipt through
  `rails/native_episode_receipt.py::validate_supply_variant_receipt`.
- `core/bundle/outputs.py` already has invariant **I7v** (`SUPPLY_VARIANT_INVARIANT`,
  `_verify_supply_variant_trace_binding`). It binds every arm contact of every Solver visit to its
  trace pair, and the row's identity to the final delivering-arm contact. The instrument note's
  "outputs.py must learn `supply_variants`" (section 3, rule 2) is therefore half done. What is
  still missing is per-arm scoring custody and a paired read over arm columns (section 3).
- `scripts/analysis/stage3_rollout_score.py::render_supply_variant_first_visit` renders one
  complete first-visit column per arm. `score_supply_variant_copies` scores each column once through
  `core/scoring_batch.py::score_complete_derived_copy`, which binds the parent bundle, roster,
  scorer and copy hash.
- `rails/candidate_semantic_supply.py` has **no** `supply_variants` reference. An arm reaches it
  only through the rebuilt router. `CandidateSemanticSupplySpec` refuses
  `max_candidates > DEFAULT_MAX_SLURP_CANDIDATES` (3) unless the projection policy is the
  configurable one. COMP-1 uses the fixed bounded policy, so on COMP-1 an arm can only
  **lower** `max_candidates`.

Two E42 attempts closed VAR-2 (`docs/results/2026-09-25-slurp-var2-closed-engineering-failure.md`).
The second died because arm `exk10` carried 40 cumulative items against a declared
`max_supplied_items` of 38 on a revision visit. The fit bound covered one visit, but the arm fanned
out on every visit.

## 1. The two uses and what each needs

**(a) Same-flight A/B read.** Two supply constructions answer the same row inside one flight, read
paired per row. It needs a declared arm pair, an in-flight A/A (section 4), one complete official
score per arm column, and a paired read over columns instead of run directories. The estimand is the **Solver-local answer under that supply at the first Solver visit**. It is not
the delivered full-system answer, because non-delivering arms never reach the Reviewer or Planner.
`render_supply_variant_first_visit` already labels its columns "first Solver visit local arm
outputs; not full-system returns".

**(b) Evidence-varied rollouts.** One sealed flight on a tuning roster carries K evidence
constructions per row at temperature 0. Owner decision 172 records that temperature sampling is
exhausted: 90.5 % of rows keep one intent across five samples. Use (b) needs the same custody as
(a), plus per-arm citation custody feeding a per-node credit table (section 5). It makes no claim,
so it needs no A/A arm.

**Out of reach for both:** any Perception-phase variant. The agreement term (`w_agree`) and the
centroid boundary key of COMP-1 are both Perception supply. A first-phase selection is seeded once
into the row's initial `QueryState` and is refused by name
(`parse_supply_variant_knob`, refusal 8). `rank_weights`, `facet_source` and `query_source` are not
knob tails either. A same-flight read of those needs an episode-level fork (open question Q1).

## 2. Runtime contract

**One row, K contacts, I7 intact.** Keep E42's form. The delivering arm is last and
override-free, so its request is the locked plan's request by construction. The row's
`request_id`, `request_sha256` and `response_sha256` are the delivering contact's. The delivered
text is that contact's response, or the registered normaliser's output over it (I7n, which COMP-1
declares: `deliver_normaliser = saea-deliver-cited-answer-normalise-v3-v1`). No arm output enters
the delivered text or any later node. I7, I7n and I7v all hold, and no grouped commit exists (the
bundle already refuses `supply_variants` beside `solver_group` in `_verify_outputs_trace_binding`).

**New: arm visits.** Add `supply_variants.arm_visits`, which is either `"every"` (today's
behaviour and the default, so existing forms stay byte-identical) or `"first"`. With `"first"`,
arms fan out only at the first Solver visit, and revisits contact the delivering arm alone. This:

- removes the cumulative-cardinality failure that closed VAR-2, because `max_supplied_items`
  bounds exactly one visit;
- matches the estimand, since the read uses first visits only;
- lowers cost.

Required changes for `"first"`:

- *Ceiling* (`rails/native_episode_config.py`, the `per_revision` formula near line 1713):
  `ceiling = base_ceiling + (K − 1)`, where `base_ceiling` is the one-arm program's. For COMP-1
  (`phase-native-candidates-review-revise-cited-v1`, `max_contacts` 11) with K = 2 or 3, the
  ceiling is 12 or 13. Each value needs its own program id and fragment, because the loader asserts
  `program.max_contacts ==` the graph ceiling.
- *Receipt*: the `supply_variants` block is sealed from the **first** Solver visit (today it is
  taken from the final visit). Add `arm_visits` and `visit_index: 0` to schema
  `saea-supply-variant-arms-v2`. Readers accept v1 unchanged.
- *I7v* (`_verify_supply_variant_trace_binding`): under v2, visit 0 carries K contacts in declared
  order, and every later visit carries exactly one contact, the delivering arm's. The row identity
  still binds to the final delivering contact. The delivering arm's ids must still form an ordered
  prefix of the final `QueryState.retrieved_value_ids`.

**Where the variant id lives.** In `NativeRoleContactContext.variant_arm_id`, which reaches the
trace through the role custody document only (`reproduction/ojw/native_request.py`, the conditional
`variant_arm_id` key; not the wire payload, so a twin's wire bytes equal the delivering arm's); in
the outputs row `supply_variants.arms[].{arm_id, contact_id, resolved_knobs, supplied_value_ids}`;
in the render manifest `arm_order`; and in the derived score receipt `column_binding.arm_id`.

**Exposure ledger.** One generation row per run id, as today. The `calls` column counts every arm
contact. Every arm re-sends the speech packet, so `speech audio seconds` grows by (K − 1) × row
audio for the first visit. The row notes state K, `arm_visits` and the ceiling. There is one READ
row per registered read run id. It covers every column contrast the recipe names, and it is
countersigned before any column score is opened, as `stage3_paired_read.py::run_package` already
enforces for arms.

**Plan budget.** `planned_model_calls >= rows × ceiling` (`rails/runner.py` near line 5481,
`planned_ceiling > plan.planned_model_calls`). Planned audio uses the same per-row product. The
budget is run-cumulative: `core/model/adapter.py` re-reads sibling attempts through
`prior_actual_usage` on every request. A recovery plan therefore covers prior durable spend plus
its own worst case.

**Fit gate.** `fit_estimate` keeps its four pinned numbers, and they must be MEASURED on the cell's
own `native_contact_fit` pass at the new ceiling. They are never placeholders like the VAR-2
fragment's round numbers. The runtime refusal (arm supplies more than `max_supplied_items`) stays.

## 3. Outputs, scoring and the paired read

**Sealed per arm.** The following is sealed per arm and already exists: contact id, request hash,
response text hash, resolved knobs, supplied value ids and count, all under the row's
`supply_variants`. The raw arm response stays in the trace only. Add one field:
`cited_value_ids` per arm when the Solver contract is `saea-solver-cited-answer-v1`, so use (b) can
credit per arm (section 5).

**Column rendering (the change that matters).** `render_supply_variant_first_visit` today parses
each arm's raw text with `reproduction.slurp_scoring.parse_slu_response`. The delivered column
instead goes through the registered delivery normaliser and the SLURP deliver projection. With the
cited-answer contract, the two renderings can disagree, so any arm-vs-delivered comparison would
partly measure the renderer. Required changes:

1. Render every arm column, including the delivering arm's first visit, through the same
   registered normaliser (`core.base.DELIVERY_NORMALISERS`) and projection as the delivered row.
2. Add a column-reproduction self-check. On every row with no revision visit, the delivering arm's
   rendered first-visit text must equal the sealed delivered `text` byte for byte. Any mismatch
   refuses the render, because it proves that columns and delivery are not the same function.

**Scoring.** Score once per complete arm column through `score_complete_derived_copy`. That
function already refuses a partial or duplicate roster column and binds the parent manifest hash.
This means one official scorer run per complete manifest per arm, never sharded. The delivered
row's own score remains the sealed `<run>.scores.json` from `core.scoring_batch`. The
`--mode supply-variants` scoring stays serial, as its docstring states.

**Paired read** (`scripts/analysis/stage3_paired_read.py`). Today it loads two run directories
through `slurp_paired_roster_read.load_arm`. Add a column source: `ArmSpec` gains an optional
`column` (`arm_id`); `load_arm` with a column reads the derived score and its receipt instead of
`<run>.scores.json`; a pair is refused unless both columns carry the same
`parent_manifest_sha256`, the machine proof of "same flight". In package mode the recipe's
`arms.arm` / `arms.in_chain_replicate` / `arms.comparator` accept `{"run_id", "attempt_id",
"column"}`: `vs-aa` reads twin against delivering column, the gating pass treatment against
delivering column. The pair unit is the row (`sample_id`); the resampling cluster follows the
recipe's `resampling.unit` (`run_package`: `"row"` gives `sample_id`, else `utterance_id`).
Recommend `unit: "row"` with the utterance cluster reported beside it (Q4). The `--delivery`
extension reads Perception records shared by all arms, so it is skipped for column pairs.

## 4. Isolation and registration

- **No gold at runtime.** Arms re-cap selection knobs over released, hash-pinned stores.
  `_supply_variant_binding` refuses a different composite snapshot. Gold enters only on the scoring
  side.
- **Variant construction from TRAIN outside the read roster only.** Store content is not the
  hazard, because every arm shares one snapshot. The hazard is the choice of which knob values to
  fly, which is made on tuning rollouts (use b). The rule: the tuning roster and the read roster
  are disjoint by recording and by utterance id, and both exclude every knowledge-source id of the
  composite snapshot (the R01/R01C lesson: a TRAIN construction roster must exclude the exemplar
  pool and every card's `source_support`).
- **The A/A of this design.** Add `replicate_of: "<delivering arm id>"` to an arm row. A twin arm
  declares no overrides and must resolve exactly the delivering arm's ids. It is exempt from
  refusal 10 (identical override sets) and from the receipt rule "every non-delivering arm
  resolves at least one knob". Its wire payload equals the delivering arm's, which the test in
  section 7 proves. The twin is the delivering arm's greedy repeat in the same contact batch, the
  same construction as ROLL-AA. The existing null is 0.735 SLU and 0.000 intent at n = 200 (R01C,
  9 of 18 scenarios). It is roster-specific, and it is a per-row SLU mean, whereas
  `rails/supply_variants.py`'s own docstring warns that per-row and pooled estimands differ. So:
  - every instrument read declares the in-flight twin; or
  - the first instrument flight on a read roster is a twin-only A/A whose null is sealed before any
    treatment contrast (rule 6).
- **Registration fields.** In the cell's `stage3_measurement` block, keep the checker's existing
  key name `measurement_design`. The brief's `design` is Q2.
  - `measurement_design: "same-flight-supply-variant"` is a new `FLOOR_TABLE` entry in
    `scripts/checks/stage3_effect_floor_check.py`. Its floor is the twin null measured on the same
    estimand, with the ROLL-AA anchor provisional until then.
  - `tuning_roster` and `read_roster`: registered roster receipt paths, both required.
  - `aa_arm_id`: required unless `sealed_null_run_id` names a prior twin-only flight on this read
    roster.
- **The gate.** `scripts/checks/flight_registration_check.py::check_cell` gains five findings:
  `variant-design-missing` (baseline declares `supply_variants` without this design or
  `offline-sealed-pool`), `read-roster-mismatch` (`read_roster` split identity is not the cell's
  population), `tuning-read-overlap` (shared recording or utterance), `roster-knowledge-overlap`
  (either roster meets the snapshot's `source_sample_ids`), and `aa-arm-missing`.

## 5. The inner-loop use

A use-(b) cell is a rollout on the tuning roster with K ≤ 8 evidence arms, `arm_visits: "first"`,
and temperature 0. Its design is `offline-sealed-pool`, and `claims_benefit` is false. After the
seal:

1. **Score.** Score each arm column once (section 3).
2. **Build credit tables.** `analysis/citation_credit.py` today tables the delivering Solver
   contact's `supplied`, `cited` and `cited_correct` counts per `value_id`. Extend it to one table
   per arm (key `(arm_id, value_id)`). Correctness comes from that arm column's official per-row
   score. The per-node credit table for the Solver node is therefore "which construction, and which
   supplied entries under it, earned correct answers", computed over sealed bytes.
3. **Select offline.** Selection, acceptance and the next update run over the sealed pool at the
   offline floor. Selection is among the flown arms only: arm effects are not additive, so an
   unflown combination is never scored offline.

"Fly only the composed policy" then means that the next flight carries exactly **one**
non-delivering arm: the composed construction the loop selected, beside the locked delivering arm
and its twin, on the read roster. It never carries one flight per candidate. If the composed policy
changes anything outside the knob tails (Perception, rank weights, prompts), it cannot be an arm.
It then flies cross-flight with an in-chain replicate under rule 3, and must clear the roughly
2.5 pp bar.

## 6. What stays closed, and how the check tells them apart

VAR-2 the mechanism is any rule whose delivered answer or any downstream node depends on more than
one arm: a merge or commit over arm outputs at the Solver, an arm output shown to the
Reviewer/Planner, or a delivering arm chosen per row. The instrument is K arms whose outputs are
only sealed and scored, with the override-free last arm delivered verbatim.

Enforced by: `native_episode_config` refusal 13 (arms beside `samples >= 2`); the bundle's refusal
of `supply_variants` beside `solver_group`; I7v's "output identity is the final delivering arm
contact"; a new runner assertion that Reviewer and Planner inputs hash-bind only the delivering
arm's response; and `stage3_effect_floor_check` requiring a cell with `supply_variants` to declare
`same-flight-supply-variant` or `offline-sealed-pool` and a `stage3_algorithm` that is not a VAR-2
mechanism family.

## 7. Implementation plan (ordered)

1. **T1 gates** (no `rails/*` or runtime file; mergeable now): `scripts/checks/stage3_effect_floor_check.py`
   (new design), `scripts/checks/flight_registration_check.py` (five findings); tests in
   `tests/unit/test_stage3_effect_floor_check.py` and `test_flight_registration_check.py`, one
   synthetic cell per finding.
2. **T2 read side** (mergeable now): `scripts/analysis/stage3_rollout_score.py` (normalised
   column render, column-reproduction self-check, per-arm `cited_value_ids` from the trace),
   `analysis/citation_credit.py` (per-arm tables), `scripts/analysis/stage3_paired_read.py` and
   `slurp_paired_roster_read.py` (column source, same-parent refusal); keep
   `test_stage3_paired_read.py`'s no-extension byte-identity test green.
3. **T3 twin arm** (identity-bound): `rails/supply_variants.py`, `rails/native_episode_receipt.py`;
   a test that the twin's wire payload equals the delivering arm's.
4. **T4 `arm_visits: "first"`** (identity-bound): `rails/native_episode_config.py`,
   `rails/runner.py` (visit-0 fan-out and receipt, single-arm downstream assertion),
   `core/flight/runtime.py` (seal validation), `core/bundle/outputs.py` (I7v v2); program fragments
   `configs/policy/phase-native-candidates-review-revise-cited-variants2first-v1.json` (ceiling 12)
   and `-variants3first-v1` (13) registered in `rails/controllers.py`; extend
   `tests/unit/test_stage3_supply_variant_interleaving.py` with a revision visit at maximum
   reachable cardinality.
5. **T5 seal-path test**: a fake sealed run with arms and I7n through `verify_bundle`, column
   render, `score_complete_derived_copy` (stub scorer) and the column paired read (the
   grouped-commit lesson).
6. **T6 registration** (coordinator): dry run, `native_contact_fit` at the new ceiling with
   measured `fit_estimate`, four-row smoke, twin-only A/A.

Gates after each task: `pytest`, `engineering_base_check.py`, `stage3_effect_floor_check.py`,
`flight_registration_check.py`, `stage3_algorithm_label_check.py`.

**Re-pin point.** T3 and T4 change `rails/*` and `core/flight/runtime.py`, whose hashes enter every
prepared artifact's `sources.implementation`; merging them makes every pinned ready cell (COMP-1
aa and smoke are ready now) fail "prepared artifact identity mismatch". They land only at a
deliberate re-pin point: after COMP-1 seals, or with a planned loop-form re-pin of every ready cell
by `scripts/flights/repin_cell.py` at the flight commit. Neither `kb_policy.py` nor
`candidate_semantic_supply.py` needs a change.

## 8. Open questions for the coordinator

- **Q1.** Perception-phase supply (agreement term, centroid key), the program's live axis, cannot
  be an arm. Should an episode-level fork be designed as a separate item: K full episodes per row,
  interleaved in one campaign, with a new A/A that ROLL-AA does not measure?
- **Q2.** Field naming: the checker's existing key is `measurement_design`, but the brief says
  `stage3_measurement.design`. Keep the existing key, or migrate both?
- **Q3.** Should every read carry an in-flight twin (+1 contact per row), or should one twin-only
  flight per read roster seal the null?
- **Q4.** Resampling cluster: row (`sample_id`, the brief) or utterance (ROLL-3's whole-utterance
  bootstrap)? Pooled micro and per-row estimands gave 1.56 vs 1.19 on ROLL-3, and the design's floor
  must be stated in the estimand the verdict uses.
- **Q5.** On COMP-1, `max_candidates` can only be lowered (the fixed projection policy). Is that
  acceptable, or should the configurable projection be admitted for arms?
- **Q6.** Should a Solver-local first-visit effect ever qualify a system claim, or only nominate the
  composed policy for a full-system read?
