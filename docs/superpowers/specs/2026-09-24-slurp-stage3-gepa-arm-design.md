# Stage-3 layer A, the GEPA arm -- design note

Author: the GEPA registration agent (Claude Opus 5), worktree `/home/chao/saea-worktrees/fable-gepa`,
branch `fable/gepa`, base master `4c2e09c9`. Date: 2026-09-24. Status: **DESIGN + ENGINEERING +
HELD REGISTRATION**. No contact is authorised by this document; every cell it registers is `held`
and no decision receipt exists.

Parent specification: `docs/superpowers/specs/2026-09-22-stage3-tfrl-base-loop-engineering.md`,
section "The GEPA and ACE arms" and "Algorithm labels, decision 101". Family record:
`core.base.STAGE3_ALGORITHMS["gepa-reflective-pareto-v1"]` (GEPA, arXiv:2507.19457), operators
`credit_assignment`, `update`, `selection`. Gate: `scripts/checks/stage3_algorithm_label_check.py`.

## 1. What the arm is, in ten lines

1. Owner decision 101 runs several training-free RL families on the SAME ROLL-1 rollouts and the
   SAME locked plan; each releases its own delta-store version and is read as its own CELL arm
   against the sealed PLAN under the same rule, the same own null and the same derangement twin.
2. Training-Free GRPO (cell ADV-1, store `stage3-deltas-v1r`, cell CELL-1) assigns credit
   **per row**: one contact per disagreeing row states what made that row's best rollout sample
   better than its worst.
3. GEPA assigns credit **per scenario** and mutates **the instruction text**: one contact per
   (scenario, node) group is shown that scenario's worst- and best-outcome rows with their whole
   sealed trajectories, plus the node's current delta statements, and proposes one to five revised
   or new statements for that node.
4. The motivation is the CELL-1 read itself: NEUTRAL overall (SLU -0.48 [-2.18, +1.24]) with large
   and opposite per-scenario effects (audio +8.9, weather +8.3 against general -12.4, alarm -6.8).
   A per-row proposer cannot see that structure; a scenario-level reflective proposer is the
   natural next family and is the one GEPA names.
5. Selection is NOT re-invented. Decision 83's per-scenario frontier rule, already implemented in
   `scripts/build_slurp_stage3_delta_retention.py`, is the selection operator: it decides which
   INHERITED v1r rows survive into the GEPA store, read off the CELL-1 arm's own per-scenario
   table. New GEPA rows inherit their scenario's decision and their own per-row outcome is read at
   CELL-1-GEPA.
6. The release path is unchanged: the same curator rules (append-only, exact-normalised and token
   Jaccard >= 0.8 dedup, provenance merge, six-token transcript containment), the same store id
   `stage3-deltas`, the same per-node `context_supply` route, the same derangement twin.
7. Budget: **68 contacts** (17 scenarios x 4 nodes; `music` has no eligible row), one contact per
   group, about **0.2 GPU-h** at the resident np4 geometry, registered under a 1.0 GPU-h ceiling.
8. The contact is TEXT ONLY on the existing construction-visible arm `construction-advantage-text`;
   the only gold it sees is the construction gold of R01C rows, under owner decision 82 and the
   `_require_construction_role_for_visible_targets` gate.
9. Nothing about the evaluated population moves: CELL-1-GEPA reads TRAIN Fold A exactly as CELL-1
   did, against the same sealed PLAN comparator.
10. This document registers the form. The verdict is read at CELL-1-GEPA and nowhere here.

## 2. The group

A **group** is one SCENARIO x one NODE. The four nodes are the phase names of the locked plan's
episode, in program order: `perception`, `solver`, `reviewer`, `planner`.

**Eligible rows.** Exactly the rows S3-3's `pairs.json` carries an available `trajectory` block
for: the 225 disagreeing rows of the sealed ROLL-1 rollout over R01C. A row whose five rollout
samples agreed has no best/worst contrast and no sealed trajectory, and nothing here rebuilds one
from the trace. `music` contributes zero such rows (0 of 27 R01C rows disagreed) and is therefore
EXCLUDED from the group set, with its reason recorded in the artifact -- there is nothing for a
reflective proposer to read. 17 scenarios x 4 nodes = **68 groups**.

**Ranking (chosen and documented).** Rows are ranked by their rollout **group mean** official
SLU-F1 (`per_row.json` `group_mean_slu_f1_f1`), ascending, ties by `sample_id`. The mean of the
five samples is the row's OUTCOME under the one scorer id every number in the artifact comes from
(`slurp-slu-official-projected-v3-train`), and separating good outcomes from bad ones is exactly
what the reflector is asked to do. The two alternatives are selectable (`--rank-metric`) and are
not the default:

* `disagreement` (best minus worst) measures WITHIN-row variance, not outcome quality: its "worst"
  rows are the least stable rather than the least correct.
* the DELIVERED score is unusable in this seal at all. The sealed ROLL-1 run scored the delivered
  answer under `slurp-slu-official-train` while S3-3 scored the samples under
  `slurp-slu-official-projected-v3-train`; the ADV-1 registration already records that
  `delivered_below_best` is vacuous for exactly this reason, and comparing across scorer ids is not
  a measurement.

**K = 6.** Each group shows the K worst and the K best rows of its scenario, de-duplicated,
worst-first. A scenario with fewer than 2K eligible rows shows all of them once. Measured
distribution over the 68 groups: 12 rows (44 groups), 11 rows (8), 10 rows (4), 6 rows (4), 2 rows
(4), 1 row (4). 173 distinct rows are shown in total, all of them R01C construction rows and 173 of
the same 225 rows ADV-1 already showed gold for.

**The current instruction text.** A released v1r row belongs to (scenario, node) when its
`node_target` is that node and at least one of its `associated_facet_ids` is an intent of that
scenario (the facet ids are `<scenario>_<action>` under the S3-5 revision v1r `source-intent`
rule). The slice is ranked by `prior_score` descending, `value_id` ascending, and capped at 12. The
prepared artifact pins the SELECTED value ids in order, so the flight-time renderer renders exactly
those rows in exactly that order and never re-derives the slice. 8 of the 68 groups carry no
statement at all; their contact is a pure "propose new" and the template says so in words rather
than showing an empty section.

**The carrier row.** `core.flight.FlightRuntime` makes exactly one contact per FLOWN ROW for a
construction-visible arm, so a group needs one row id to be the flight's row: its CARRIER. The
carrier is an identity anchor and nothing else -- the contact is text-only, no packet is opened,
and the material is the whole group. Carrier `i` of a scenario (`i` indexing the four nodes in
program order) is the `i`-th row of that scenario's ordered group, so the four carriers of a
scenario are distinct and each is a row whose own gold the contact already shows. A scenario with
fewer than four eligible rows tops up from its OWN remaining R01C rows in ascending `sample_id`;
5 of the 68 carriers are such top-ups (`general` 3, `audio` 2) and are recorded with
`carrier_from: "roster-topup"`. A top-up carrier's gold is NOT shown: it is not a group row.

## 3. The contact

One contact per group, on the EXISTING construction-visible arm `construction-advantage-text`,
through the EXISTING text-only one-contact dispatch
(`core.flight.runtime._run_construction_proposer`). A third arm was deliberately not created: it
would need its own D2 receipt (`e0.d2_leakage._construction_visibility` is a strict
bare-core-plus-one-field equality) and would carry the identical field set. What separates the two
cells is the PROGRAM, which is what the material and reader dispatch key on.

* Program `phase-stage3-gepa-v1` (`configs/policy/phase-stage3-gepa-v1.json`): one phase named
  `gepa`, `knowledge: "none"`, `max_contacts: 1`, `stop_rule: always-run-full-program`.
* System message: the literal bytes of `configs/probes/slurp_stage3_gepa_system_v1.txt`, declared
  as a LITERAL `task_instruction` (the ADV-1 repair of 2026-09-23, option A: `core.instructions`
  renders a template only through a registered fill with a `{tool_schemas}` placeholder, which a
  static system message has no use for).
* Per-group instruction: `configs/probes/slurp_stage3_gepa_v1.txt`, five placeholders
  (`{scenario}`, `{node}`, `{current_deltas}`, `{worst_rows}`, `{best_rows}`), filled by
  `rails.stage3_gepa.render_gepa_instruction`.
* Each row block is rendered by `rails.stage3_gepa.render_group_row_block` from parts produced by
  ADV-1's OWN four renderers (`render_candidate_list`, `render_rollout_answer`,
  `render_construction_gold`, `render_reviewer_verdicts`, `render_planner_route`), so a trajectory
  reads identically in both arms and neither arm owns a second copy of the grammar.
* Response format `stage3-gepa-proposal-v1` (`rails.stage3_gepa.stage3_gepa_response_format_v1`):
  one to FIVE blocks, each `{node, delta_kind, target, statement}` with the same closed node and
  delta-kind vocabularies ADV-1's v2 format uses.
* Parser of record `rails.stage3_gepa.parse_gepa_proposal`: a closed-form, total, line-keyed
  sibling of `parse_advantage_statements_v2` that also reads the JSON shape. It adds exactly one
  invariant: a contact is addressed to ONE node, so a block naming a different node is RETAINED and
  marked illegal rather than silently routed into another node's slice. Illegal blocks are never
  repaired and never dropped by the parser; curation drops them, counted.

**REVISED versus NEW is decided by the curator, not by a self-report.** The block form carries no
"this revises delta X" field, because a self-report is exactly the kind of claim a frozen core can
get wrong and nothing downstream could check. A proposal whose normalised text matches an existing
store row under the curator's own rule (exact normalised text, then token Jaccard >= 0.8) IS a
revision: it is absorbed into the survivor and its provenance is merged. Anything else is new. That
is the rule the store already runs on, applied unchanged.

## 4. Selection: decision 83, reused as the operator

GEPA's selection operator is the per-scenario Pareto frontier over per-row scores. In this
repository that rule is already written, preregistered and implemented:
`scripts/build_slurp_stage3_delta_retention.py` (decision 83) -- RETIRE when every targeted scenario
is harmed beyond its own derived null band, KEEP when any targeted scenario gains beyond it, and
decide everything else by the prefilled-token frontier slope through the arm.

The GEPA curation therefore runs that CLI over the **CELL-1 read** and uses its `retired_value_ids`
as `--retire-value-ids` against predecessor `authored-stage3-deltas-v1r.json`. Inherited rows
survive or retire by the frontier; the GEPA proposals are appended on top; and the new rows'
own per-row outcome is read at CELL-1-GEPA, one iteration later, by the same rule. Nothing about the
rule is re-tuned for this family -- that is the point of running three families against one
selection operator.

The retention document is written to the GEPA arm's OWN prepared directory
(`prepared/SAEA-SLURP-STAGE3-DELTAS-GEPA-V1/retention-gepa-v1.json`) and never reads or writes the
`stage3-deltas-v2` artifacts of the sibling CELL-2 line. Because the inputs and the rule are
identical, its `retired_value_ids` are EXPECTED to equal the v2 line's; that is a cross-check, not a
dependency, and the runbook prints both counts.

## 5. Budgets

| | arm | smoke |
| --- | --- | --- |
| contacts (`generation_calls_cap` = target) | 68 | 4 |
| `fit_endpoint_calls_cap` = contacts x (0 packets + 3 endpoints) | 204 | 12 |
| `planned_speech_audio_seconds` (ceiling from the carriers' roster rows) | 293 | 27 |
| `native_task_contract_calls_cap` | 0 | 0 |
| `official_complete_scoring_jobs` | 0 | 0 |
| `planned_gpu_hours` (ceiling; point estimate about 0.2) | 1.0 | 1.0 |

Ceilings are bounds, never targets, and budgets are run-cumulative across every attempt of a run
id. The speech-second figure is a positive declaration the execution contract requires; the arm is
text-only under the D2 freeze, so the realised speech seconds are expected to read 0 <= the ceiling.

## 6. The construction-visible gate and the leakage rule

* The arm is `construction-advantage-text`, already in `contracts.CONSTRUCTION_VISIBLE_ARMS`. The
  gate `contracts.gate_exposure._require_construction_role_for_visible_targets` refuses the touch
  unless the FLYING cell's own `split_identity_hash` is that of a committed
  `roster_role == "construction"` roster of carrier `slurp` on a `discovery` split. The 68 carriers
  therefore carry their own committed receipt
  `docs/receipts/rosters/slurp-stage3-gepa-r01c-carriers-v1.json` (a pure selection of R01C, zero
  contacts, the ADV-1 precedent), and the four smoke rows carry theirs.
* **Every row whose gold is rendered is an R01C construction row.** The 173 distinct group rows are
  items of the same committed parent receipt `slurp-stage3-construction-r01c.json`, and the groups
  builder refuses outright if any eligible row is not (`missing_roster` check). The gate checks the
  FLOWN split's identity; this check is what makes the SHOWN population's construction legality
  machine-proved rather than argued.
* `construction_targets` carries the group's rows and their gold. The client binds the UNION of
  every group's rows once, at construction, and each request names EXACTLY its own group's ordered
  rows, so a request can only ever NARROW what the core sees
  (`rails.core_client.FrozenCoreClient._selected_construction_targets` refuses an id the bound
  tuple does not carry).
* **No evaluation gold, no reference transcript, no future turn.** Nothing of this contact reaches
  an evaluated row: its output is an artifact that is curated, de-duplicated and released as a
  knowledge store, and the store's effect is measured on TRAIN Fold A at CELL-1-GEPA.
* **The delta statements shown are this study's own released text**, curated under the six-token
  transcript containment rule, so none of them repeats a construction transcript span. They are
  rendered into the instruction and nowhere else, and the same rule is applied again to every
  proposal at curation.
* **No text is sealed.** `GepaContact.as_json` records ids, counts and digests only: group id,
  scenario, node, carrier, the group's row ids, the current delta value ids, per-row answer/gold
  digests and label counts, and the prompt sha256 and length. The rendered instruction is never a
  receipt field.

## 7. What is sealed, and what the read is

The cell's PRIMARY DELIVERABLE is the sealed manifest of parsed proposal blocks. The decision rule
is STRUCTURAL ONLY and carries no gate number, exactly as ADV-1's does:

1. PARSE RATE -- the fraction of contacts whose response yields at least one LEGAL block, with its
   denominator.
2. NODE DISCIPLINE -- the count of blocks whose `NODE` differs from the group's node (the invariant
   only this arm's parser enforces). A contact form that drifts off its own node is a form defect.
3. ILLEGAL-BLOCK COUNT by the parser's own reason strings, retained and never repaired.
4. BLOCKS PER CONTACT -- the one-to-five distribution.
5. REVISION SHARE -- how many accepted proposals the curator absorbed into an existing row (a
   revision) against how many entered as new rows. This is the number that says whether a
   reflective proposer actually reflected on the text it was shown.
6. A clean seal with row accounting in = out.

No effectiveness claim is read here. The comparator, the margins and the twin all live at
CELL-1-GEPA (`SAEA-SLURP-STAGE3-DELTA-CELL-GEPA-R01-V1`), one factor on the locked plan against the
sealed PLAN arm at the plan's own null (h_SLU 1.2485 / h_intent 0.9943), with a derangement twin as
the form control -- identical in every respect to CELL-1 except the store it pins.

## 8. Claim boundary

* This cell measures nothing. It produces an artifact.
* CELL-1-GEPA measures the GEPA store against the sealed PLAN on TRAIN Fold A. A TRAIN A number is
  a development number (owner decision 86 / 28): it is never a paper claim, and the order of reads
  is TRAIN lock -> DEV confirmation -> the single test read (owner decisions 99 and 107).
* Nothing here compares GEPA against Training-Free GRPO. Three arms on one comparator and one own
  null make such a comparison POSSIBLE later; making it is a separate read with its own
  preregistration, and the two arms' CI95 intervals on the same population are what it would have
  to be built from.
* No production-scale implementation, no confirmatory campaign, no manuscript: those are Stage-3
  paper-repository work and this repository refuses the profile
  (`contracts.assert_execution_scope`).

## 9. Engineering, and the one shared file that moved

New, self-contained:

* `src/speech_aware_evidence_acquisition/rails/stage3_gepa.py` -- parser, renderers, response
  format, ids.
* `src/speech_aware_evidence_acquisition/rails/stage3_gepa_material.py` -- the third
  `construction_material_resolver` implementation; reuses ADV-1's renderers, sealed-custody reader
  and per-sample digest verification unchanged.
* `scripts/build_slurp_stage3_gepa_groups.py` -- the model-free group builder.
* `scripts/build_slurp_stage3_gepa_delta_rows.py` -- the model-free GEPA curator, a thin sibling of
  `scripts/build_slurp_stage3_delta_store.py` that imports its `curate`, its dedup rule, its facet
  rule, its containment rule and its document writers rather than restating them.
* `configs/policy/phase-stage3-gepa-v1.json`, `configs/probes/slurp_stage3_gepa_v1.txt`,
  `configs/probes/slurp_stage3_gepa_system_v1.txt`, the four cell fragments and the campaign plan.

Shared files that moved, minimally and additively:

* `rails/controllers.py` -- one phase-program file entry, one controller registration, one response
  format registration. No existing registration changes.
* `core/flight/runtime.py` -- two imports, one dispatch branch in `_default_construction_material`
  keyed on the composed `policy`, `GepaMaterial` added to the material `isinstance` tuple, one
  reader branch in `_construction_phase_material`, and one dispatch-kind label. No existing branch
  changes behaviour: every pre-existing arm and program takes exactly the path it took before.

**Re-pin obligation (stated, not deferred).** `core/flight/runtime.py` is hashed into every prepared
phase-supply artifact's identity (`FlightRuntime._phase_seed_inputs`
`sources.implementation.runtime`). Touching it invalidates every artifact prepared before this
commit -- the CELL-1 family's included. The coordinator's flip step re-pins them in one cycle
(`scripts/flights/repin_cell.py`); `--allow-output-change` must NEVER be passed, and their `output`
is expected to reproduce BYTE FOR BYTE because no selection path moved. `verify_prepared_artifacts`
reports a stale artifact read-only before a flight opens anything, so the failure mode is a refusal,
not a wrong flight.

The alternative -- hiding the dispatch inside `rails/stage3_advantage_material.py` so that
`runtime.py` never moves -- was considered and rejected: the phase READER lives in `runtime.py`, and
without touching it a GEPA response would be sealed under ADV-1's three-block reading, which marks
legal blocks 4 and 5 illegal. A misleading sealed receipt is worse than a re-pin cycle that the
coordinator's own sequence already performs.

## 10. The four CELL-1 launch-defect lessons, checked against this arm

| lesson (CELL-1 README) | applies here? |
| --- | --- |
| **Shared readers** -- one place answers "how does this plan read that phase's sealed output" | Not reachable: this cell composes no knowledge store and reads no Perception state at flight time. The Perception candidate IDS it shows are read model-free from `pairs.json`'s sealed trajectory block, never re-parsed from a live state. |
| **Fit identities** -- a prepared artifact is evidence only for the implementation that produced it | Applies to OTHER cells, not to this one: `phase-stage3-gepa-v1` declares `knowledge: "none"` and the baseline declares `evidence_source: "none"`, so this cell pins no prepared phase-supply artifact at all. The obligation it creates for the CELL-1 family is stated in section 9. |
| **Empty selections** -- a node slice that selects nothing must supply nothing | Applies in a different shape and is handled at the TEMPLATE, not at a supply step: a group whose node carries no current statement renders `(this node currently carries no statement for this scenario)` rather than an empty section, so the contact knows it is proposing from scratch. 8 of 68 groups are in that state. No `acquire` transition exists in this one-contact program. |
| **Seeding once** -- the unconditional first-phase route is composed exactly once | Not reachable: no store route, no phase supply, no bootstrap. |

## 11. Sequence for the coordinator

`merge` -> `mint` the admission decision receipt under
`coordination/slurp-stage3-delta-cell-gepa-r01-v1/root-admission-v1.json` -> `flip` both cells with
`scripts/flights/batch/gepa_flip_both.sh` (re-pins, and re-pins the CELL-1 family for the runtime
change) -> `chain` the flight with `scripts/flights/batch/batch_chain_gepa.sh` (smoke first, then
the 68-group arm) -> `curate` and `release` with `scripts/flights/batch/gepa_to_deltas.sh` ->
register and fly **CELL-1-GEPA** from the diff plan
`docs/readiness/2026-09-24-slurp-stage3-gepa-r01-v1/cell-1-gepa-diff-plan-v1.md`.

## 12. The store's permitted roster (appended 2026-09-24)

The delta store released from this arm pins the committed ADV-1 disagreeing receipt
`docs/receipts/rosters/slurp-stage3-advantage-r01c-disagreeing-v1.json` (225 rows, split identity
`7c603857...`) as its `permitted_roster` and `source_split_identity_hash` -- the precedent of
`stage3-deltas-v1r` and `stage3-deltas-v2`, whose registrations carry the same identity. The reason
is decision 83's append-only retention: the curated store is 248 new GEPA rows plus 200 retained
iteration-1 rows, and 42 of those retained rows cite 28 R01C rows that lie outside the 173 group
rows this arm's contacts were shown, so a permitted roster built from the group union would be
refused by `rails.semantic_knowledge_build` unless retained content were discarded. Sharing v1r's
source identity also keeps the GEPA store source-comparable with the CELL-1 / CELL-2 stores. The
group union stays a committed roster of its own
(`docs/receipts/rosters/slurp-stage3-gepa-r01c-groups-v1.json`) as the record of the contact
material, and `scripts/flights/batch/gepa_render_proposal_outputs.py` proves it is contained in the
permitted roster before copying that receipt byte for byte; the 68-row carriers receipt remains the
flight population and is never the store's roster.
