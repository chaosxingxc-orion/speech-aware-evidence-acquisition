# Item E42: per-row supply-variant interleaving inside ONE campaign (family VAR-2)

Model-free engineering item. Zero model, tokenizer, encoder, server or network contact; no cell
registered, no ledger row written, no receipt minted, nothing flipped. Branch `fable/var2`.

## 1. Why, in one paragraph

Cell ROLL-AA (`docs/results/2026-09-24-slurp-stage3-roll-aa-within-flight-null-read.md`, board route
F2) compared the locked v2.0 plan against itself INSIDE one flight: with byte-identical prompts at
temperature 0 the delivered answer repeats on 91.5 % of rows, the delivered intent never changes, and
the paired per-row half-width is **h_within = 0.735 pp SLU / 0.000 pp intent at n = 200**. The SAME
identity flown as two separate campaigns reads about **1.25 pp**. The diffuseness the program has been
paying for is therefore a BETWEEN-flight phenomenon. A construction variant compared per row inside one
campaign is read at roughly a third of the cross-flight floor, which is what makes the construction
optimisation space of handoff section 7.1 searchable. The VAR-1 family flies one campaign per variant
and pays the between-flight penalty in full. This item is the harness capability that removes it, and
it is the engineering half of board route **F12**.

## 2. The form

One node, K arms, one episode, one row: the SAME node is contacted K times over the SAME `QueryState`,
each contact composed over a DIFFERENT declared knowledge-supply construction, and the episode delivers
exactly ONE of them.

It is the grouped Solver sampler (item E2) with the varied axis moved from DECODING to SUPPLY:

| | item E2 (grouped samples) | item E42 (supply variants) |
| --- | --- | --- |
| what varies | `temperature` / `seed` per sample | the SUPPLIED EVIDENCE per arm |
| composed at | `reproduction.ojw.native_request.compose_solver_sample_decoding_params` | `rails.runner`'s binding provider (`supply_variant_messages`) |
| delivered text | the COMMIT policy's aggregate of N samples | the delivering arm's OWN response text |
| invariant I7 | needs an explicit `solver_group` exception and an I7g re-derivation | holds with **no new exception** |
| custody field | `solver_group` | `supply_variants` |

### 2.1 The configuration surface

On the baseline fragment, under `native_episode.roles.solver`:

```json
"supply_variants": {
  "arms": [
    {"arm_id": "exk10", "max_supplied_items": 38,
     "overrides": {"knowledge_stores.train-exemplars.phase_supply.solver.k": 10,
                   "knowledge_stores.train-exemplars.phase_supply.solver.fuse_coverage.m": 10,
                   "knowledge_stores.train-exemplars.phase_supply.solver.fuse_coverage.c": 10,
                   "knowledge_stores.train-exemplars.phase_supply.solver.fuse_coverage.top_l": 10}},
    {"arm_id": "exk30", "max_supplied_items": 58, "overrides": {"...k": 30, "...m": 30, "...c": 30, "...top_l": 30}},
    {"arm_id": "exdiv", "max_supplied_items": 48, "overrides": {"...fuse_coverage.c": 4}},
    {"arm_id": "plan",  "deliver": true, "max_supplied_items": 48}
  ],
  "fit_estimate": {"slot_tokens": 24576, "completion_ceiling": 640,
                   "base_prompt_tokens": 9600, "tokens_per_supplied_item": 120}
}
```

Exact keys. Block: `arms`, `fit_estimate`. Arm row: `arm_id` and `max_supplied_items` required,
`deliver` and `overrides` optional. `fit_estimate`: `slot_tokens`, `completion_ceiling`,
`base_prompt_tokens`, `tokens_per_supplied_item` — every one a MEASURED, pinned number read off an
already-sealed cell, never a guess computed by the rail.

The admitted knob paths, and nothing else
(`rails.supply_variants.SUPPLY_VARIANT_KNOB_TAILS`):

* `knowledge_stores.<store>.phase_supply.<phase>.k`
* `knowledge_stores.<store>.phase_supply.<phase>.fuse_coverage.m` | `.c` | `.top_l`
* `knowledge_stores.<store>.candidate_supply.<phase>.max_candidates`

These are exactly the knobs a VAR-1 cell varies across CELLS today (`configs/baseline/
slurp-native-stage3-var1-ex-k10|ex-k30|ex-div-r01c-baseline-v1.json`).

### 2.2 Why the delivering arm carries no overrides and comes LAST

Two invariants this form refuses to weaken:

1. **The delivered request is the locked plan's request, byte for byte.** The delivering arm is
   rendered from the episode's own `QueryState` with no arm-scoped view of any kind — it is not "a
   narrowing that reproduces the plan", it IS the ordinary path, so its bytes are identical *by
   construction* rather than by claim. That is what makes the delivering arm the read's baseline and
   the within-flight comparator of every other arm.
2. **Invariant I7 (the delivered text is a model response) holds with no new exception.** The
   delivering arm is the LAST arm of the group, so the role result's `actor_output` IS the last
   contact's own completion text and `rails.runner`'s existing delivery binding check ("native
   delivery is not bound to its actual source response") passes unchanged. A grouped Solver visit
   needs an explicit `solver_group` bypass there because its delivered text is an AGGREGATE; an arm
   group needs none, and no aggregation rule exists to audit.

### 2.3 Where an arm's own supply comes from, and where it is rendered

Flight-owned, exactly as `supply_for_phase` and `acquisition_requery` are — the runner never reaches
for a store of its own. `core.flight.runtime.FlightRuntime._supply_variant_binding` builds ONE
knowledge-store router per declared arm (the delivering arm included) from a copy of this cell's own
composed values with that arm's declared selection knobs re-capped, over the SAME released,
hash-pinned stores, the SAME composite snapshot and the SAME router options the delivering router was
built with. It refuses an arm whose rebuilt binding composes a different composite snapshot: an arm
re-caps a selection, it never changes the released knowledge.

Every arm's supply is resolved ONCE per visit, in `rails.runner`'s `settle`, against the SAME
`staged` context the row's ordinary supply step is resolved against. That position is load-bearing:
resolved later, at binding composition, the state already carries the node's own increment and a
route that excludes what is visible would answer a different question.

A NON-delivering arm's request is then composed over a `QueryState` **view**: the row's accumulated
ids with this node's own cumulative contribution removed and that arm's resolved selection in its
place (`rails.supply_variants.arm_supplied_value_ids`). The view is used for RENDERING only and never
for custody — no transition, no wave, no state and no hash edge reads it.

## 3. The refusals

Every one is raised by name BEFORE any contact.

### 3.1 In the rail (`rails.supply_variants.parse_supply_variants`)

| # | refusal |
| --- | --- |
| 1 | a block that is not an object with exactly `arms` and `fit_estimate`; `arms` not an ordered list of objects |
| 2 | an arm count outside 2..8 (one arm is a second spelling of no arms; 8 is the grouped sampler's own bound) |
| 3 | an arm row with unknown or missing keys |
| 4 | an arm id collision |
| 5 | zero or several arms carrying `deliver` |
| 6 | a delivering arm that is not the LAST arm, or that carries overrides |
| 7 | an override path this rail does not admit: outside `knowledge_stores`, an unknown route, an unknown knob, an undeclared store, a non-positive value |
| 8 | an override naming the program's FIRST phase — a first-phase selection is computed before the flight and seeded into each row's ONE initial `QueryState`, so it cannot differ between two arms of the same row however the request is composed |
| 9 | an override naming another node's phase — an arm may only re-cap the supply of its own node |
| 10 | two arms whose whole override set is identical (two spellings of one construction spend a contact per row and measure nothing) |
| 11 | an arm whose estimated prompt exceeds the live slot with the registered reserve (fail-closed; see 3.4) |

### 3.2 In the configuration loader (`rails.native_episode_config`)

| # | refusal |
| --- | --- |
| 12 | `supply_variants` on any role but the Solver — the node this program varies is the one whose output is DELIVERED |
| 13 | `supply_variants` beside `samples >= 2` — two fan-outs at one node make the visit's ONE contact batch ambiguous and its ceiling contribution the product of two independently declared knobs |
| 14 | `supply_variants` with `roles.solver.max_iterations != 1` — one arm is one CONTACT, and the arm of a contact is its invocation index modulo the arm count; a multi-iteration (ReAct) node would put several contacts under one arm and silently shift every later arm's identity |
| 15 | `supply_variants` beside role tool authority — a tool call would spend a second contact under one arm |
| 16 | `supply_variants` beside an armed `native_episode.knowledge_index` — the index REPLACES the very value blocks an arm varies and appends its own system suffix, so the two keys would each be rewriting the other's output with only one of them in custody |
| 17 | `supply_variants` on the acquisition role — it answers nothing and delivers nothing |
| 18 | a program whose `max_contacts` is not the arm-multiplied graph ceiling (§4) |

### 3.3 At runtime (`rails.runner`, `core.flight.runtime`)

| # | refusal |
| --- | --- |
| 19 | a declared group with no `supply_variant_for_phase` binding, and a binding with no declared group — one module, both directions |
| 20 | the DELIVERING arm resolving a different supply than this row's own supply step acquired at this node (§5.1) |
| 21 | arms settling out of their declared order |
| 22 | a supply-variant arm contact executing a tool |
| 23 | an arm whose selection re-supplies a value an earlier phase already made visible, or whose selection is not unique |
| 24 | an arm supplying more items than its declared `max_supplied_items` (the bound the fit refusal was computed against) |
| 25 | one contact carrying conflicting arm records; an arm sealing no recorded contact of its own; arm records composed but never sealed |
| 26 | a group declared on a cell with no named `knowledge_stores`; an arm override naming a path the composed values do not already declare; an arm whose rebuilt store binding composes a different composite snapshot |

### 3.4 The fail-closed prompt-fit refusal

The arithmetic is the existing one, applied to an estimate instead of a realised request. The live
slot minus the operational reserve (`rails.context_budget.serving_bound_reserve_tokens` — one eighth
of the slot, capped at the registered 8,192; 3,072 at the 24,576-token np4 geometry) minus the
completion ceiling minus the registered 2-token special reserve is what an arm's PROMPT may occupy.
An arm's estimate is `base_prompt_tokens + max_supplied_items * tokens_per_supplied_item`. Over the
limit, the configuration is refused, naming the arm and every number. `fit_estimate` is REQUIRED
whenever `supply_variants` is declared: the refusal is fail-closed by default, not opt-in. The runtime
half is refusal 24 — an arm that supplies more items than the bound its own estimate was computed
against dies rather than sending a prompt nobody budgeted.

## 4. The ceiling arithmetic

`rails.native_episode_config.load_native_episode_config`, one formula, extended by one factor:

```
ceiling      = perception.max_iterations
             + (max_revisions + 1) * per_revision
             + max_candidate_refreshes * perception.max_iterations
             + max_acquisitions_per_row * acquisition.max_iterations

per_revision = solver.max_iterations * solver.samples * solver.arms
             + reviewer.max_iterations
             + planner.max_iterations
             + cleaning contacts per revision
```

`solver.arms` is the Solver's registered supply-variant arm count and is **1** for every config that
declares no arm group, which reduces the formula to exactly its pre-E42 self. `samples >= 2` and an
arm group are refused together (refusal 13), so the product is never of two simultaneously non-unit
factors.

For the four-arm form on the locked v2.0 plan's role graph (perception 1, solver 1, reviewer 3,
planner 1, `max_revisions` 1):

```
per_revision = 1 * 1 * 4 + 3 + 1 = 8
ceiling      = 1 + (1 + 1) * 8   = 17
```

against the 11 the one-arm VAR-1/PLAN program declares. A new program id is therefore REQUIRED, never
a flag on the review-revise program — two program ids must never resolve to the same object when their
contact ceilings differ, and the loader asserts `program.max_contacts` equals the graph ceiling:

* `configs/policy/phase-native-candidates-review-revise-variants4-v1.json` — the SAME four phases, the
  SAME `stop_rule`, `max_contacts` **17**;
* registered in `rails/controllers.py` (`_PROGRAM_CONFIG_FILENAMES` + `register_phase_programs_v1`),
  exactly as `samples5` and `samples2` were.

A group of some other size needs its own id and its own fragment, exactly as `samples2` needed one
beside `samples5`.

## 5. Custody

### 5.1 The one divergence this form introduces, and how it is made checkable

For the DELIVERING arm the sealed `QueryState` describes its request exactly. For a NON-delivering arm
it does not: that arm's request carried its own resolved selection, which the episode's state never
claimed. That divergence IS this form's point (it is what buys the within-flight comparison), and the
repository has no verifier that would catch it either way — the protection in that direction is
structural, not asserted (both production renderers are pure functions of
`QueryState.retrieved_value_ids`; the only exact ordered check in the tree,
`analysis/native_intent_support.py`, is an offline C0-only diagnostic). So this item does not rely on
that silence. It declares the divergence and makes it checkable:

* **Every arm's request, resolved knobs, supplied value ids and item count are sealed under the arm's
  own id**, and the K contacts are recorded as ONE `AgentContactBatch` with
  `fanout_semantics="action_alternatives"` — so all K bind the SAME `query_state_sha256`, exactly as
  the K samples of a grouped Solver visit do. They are independent constructions of one draft, not a
  chain.
* **The delivering arm's byte identity is a LIVE, fail-closed statement.** `rails.runner`'s `settle`
  resolves the delivering arm through the flight's own independently-built router and refuses the row
  when that resolution differs from what this row's ordinary supply step acquired at this node
  (refusal 20). That is a re-derivation, not a restatement: a different router object, over the same
  released stores, reaching the same selection.
* **At the seal**, `core.flight.runtime` re-validates the arm custody against the RAW declared block
  (not the composed config), exactly as the grouped sample count is read there, and additionally
  requires the delivering arm's ids to be an ordered PREFIX of the row's own accumulated
  `retrieved_value_ids`. `rails.runner` deliberately does NOT pass that argument: at composition time
  the comparison would restate the composition rather than check it.

### 5.2 The receipt

`supply_variants`, a top-level sibling of `native_episode_receipt` and `solver_group` on the outputs
row, schema `saea-supply-variant-arms-v1`:

```
{"schema", "phase_id", "arm_count", "delivered_arm_id", "fit_estimate",
 "arms": [{"arm_index", "arm_id", "deliver", "contact_id", "resolved_knobs",
           "supplied_value_ids", "supplied_item_count", "max_supplied_items"}]}
```

Ids, labels and counts only — never a supplied value's text, never an utterance, never a gold label.

`resolved_knobs` is an ORDERED LIST of `{"path", "value"}`, not a mapping keyed by the dotted path.
Not cosmetic, and found by this item's own live test: the record travels the installed workflow
engine's node result, and that engine UNFLATTENS a mapping whose keys contain dots —
`{"a.b.c": 1}` arrives as `{"a": {"b": {"c": 1}}}`, which silently destroys the one thing the row
exists to state. A list of objects survives any such transport unchanged.

`rails.native_episode_receipt.validate_supply_variant_receipt` is the twin of
`validate_solver_group_receipt` and as strict: distinct declared arm ids, the delivering arm last,
exact field sets, every declared arm present exactly once in declared order, ascending `arm_index`,
each arm's `deliver` agreeing with the declaration, distinct contact ids, resolved knobs distinct and
path-ordered, the delivering arm resolving none and every other arm resolving at least one, unique
supplied ids, the count agreeing with the ids, the count within the arm's own bound, and — with a
state to compare — the delivering arm's ids opening it.

It is called from two places, mirroring `validate_solver_group_receipt`'s own call sites:
`rails.runner._invoke_native_role_episode` at sealing and `core.flight.runtime` at the flight seal.
The post-seal bundle path (`core/bundle/outputs.py`) is NOT wired in this item — see §8.

## 6. How a read consumes it

Unchanged scoring path. `scripts/analysis/stage3_rollout_score.py` already renders and scores K sides
of a row on COPIES and is K-generic: it never assumes the K sides differ by seed. Its
`render` → `score_copy` → `best_worst` chain reads the per-side text out of the sealed row, writes one
`sample-<index>-outputs.jsonl` per side plus a `render-manifest.json`, scores each side ONCE through
the dataset's registered scorer with the official identity check, and emits the row-paired
`per_row.json` / `pairs.json`.

For this form the per-side text is each arm's OWN sealed response, and the paired read is the arm's
delta against the DELIVERING arm on the same row, read against `h_within` (0.735 pp SLU / 0.000 pp
intent at n = 200; about 0.4 pp at n = 625 by the same per-row sd) instead of the 1.25 pp cross-flight
band. The arm's own identity — its `arm_id` and its `resolved_knobs` — comes from the row's
`supply_variants` block, which is what turns "side 2" into "exemplars k 30".

The reader-facing consequence: **the delivering arm is the baseline of the read, and it is the locked
plan's construction.** Every arm's number is a within-flight paired delta against a comparator that is
the plan itself, on the same row, in the same batch, over the same `QueryState`.

## 7. What this does NOT change

* **No existing episode form's bytes move.** Every branch of the mechanism is guarded by
  `role.supply_variants is None` / `request.context.variant_arm_id is None`, which is the state of
  every role and every contact of every form written before this item. The ceiling formula's new
  factor is 1. `NativeEpisodeRole.supply_variants`, `NativeEpisodeRunBinding.supply_variant_for_phase`,
  `NativeRoleContactContext.variant_arm_id`, `AgentLoopResult.supply_variants` and
  `DryRunNode.supply_variant_arms` are all declared LAST and defaulted, so every positional
  construction in the tree and in the tests composes exactly what it did.
  `role_request_bytes` gains its arm key CONDITIONALLY — absent when no arm is bound — so a pre-E42
  contact's role custody document is byte-identical.
* **No model fragment, no serving geometry, no decoding parameter.** None of them is addressable by a
  knob path this rail admits, and the two arms of one visit were compared field by field in the live
  test: `decoding_params`, `task_instruction`, `tool_schemas`, `speech_feature_parts`,
  `speech_packet_sha256`, `query_source`, `key_representation_id`, `matcher_policy_id`,
  `carrier_lock_key`, `media_relpath`, `audio_seconds`, `sample_rate_hz`, `sample_id` are equal; only
  `supplied_evidence` and `evidence_provenance` differ.
* **No prompt ORDER.** The arm view replaces which value ids are visible; the message structure
  (system, then the speech part, then `key` facet blocks, then `value` blocks) and the within-block
  order are the renderer's own, unchanged.
* **No released knowledge.** Every arm reads the same composite snapshot under the same pins; an arm
  whose rebuilt binding composes a different snapshot is refused.
* **No first-phase (Perception) variant.** A first-phase selection is computed before the flight and
  seeded into each row's ONE initial `QueryState`, so it cannot differ between two arms of one row.
  This is the one part of the task's sketch that is NOT clean to do, and it is refused by name
  (refusal 8) rather than half-implemented. A Perception-K variant remains a VAR-1-shaped cell, one
  campaign per K.
* **No claim.** This item registers no cell, writes no ledger row, mints no receipt and flies
  nothing. It adds a capability and its offline proofs.

## 8. Registration — `TODO-REGISTRATION`

`configs/baseline/slurp-native-stage3-var2-supply-variants-r01c-baseline-v1.json` is a DERIVED,
**UNREGISTERED** reference fragment. It is a byte-for-byte derivation of the VAR1-PLAN comparator
baseline plus exactly: the new `policy` (the 17-contact program), the `supply_variants` block, this
cell's own `native_contact_fit` identity pair, its two `speech_feature_*` identity ids, its
`what_this_is`, and its `prepared_phase_supply` pin. Everything else — every store pin, every
`native_episode` key, every `phase_material`, every preparation receipt — is the comparator's own
bytes, so the two files diff to the form and nothing else.

**TODO-REGISTRATION**, before this fragment may fly, in order:

1. an owner decision admitting the VAR-2 family and its roster;
2. an experiment fragment with its `cells` block, run id, attempt id and `execution_plan`, and a
   readiness package under `docs/readiness/`;
3. a minted `prepared_phase_supply` artifact — the fragment carries the placeholder
   `"sha256": "TODO-REGISTRATION-prepared-phase-supply-sha256"` and MUST be re-pinned by
   `scripts/flights/repin_cell.py` (which is also what refreshes the fit-run identity);
4. an exposure pre-registration row in `docs/exposure-ledger.md`;
5. a `native_contact_fit` pass at the 17-contact ceiling on the np4 ctx24k geometry, and the
   `fit_estimate` numbers replaced by that cell's own MEASURED base prompt and per-item token cost
   (the values in the fragment today are round placeholders chosen to exercise the arithmetic, not
   measurements);
6. a four-row smoke as the form proof, exactly as the first grouped Solver group had one;
7. the post-seal bundle wiring: `core/bundle/outputs.py` validates `solver_group` under invariant I7g
   and does not yet know about `supply_variants`. A sealed VAR-2 row would pass the bundle because the
   key is simply unread — that is a gap to close with its own invariant code before any VAR-2 number
   is reported, not a defect in this item's runtime custody.

The placeholder is a literal `TODO-REGISTRATION-` string and not a `PENDING_` token, deliberately: the
`PENDING_` vocabulary belongs to fragments inside a live registration workflow, and this one is not in
one.

## 9. Files

| file | what |
| --- | --- |
| `src/speech_aware_evidence_acquisition/rails/supply_variants.py` | NEW. The rail: arms, the knob vocabulary, every parse refusal, the fit arithmetic, the per-arm id arithmetic, the receipt builders |
| `src/speech_aware_evidence_acquisition/reproduction/ojw/native_supply_variants.py` | NEW. `SupplyVariantRoleNode` / `run_supply_variant_arms`, the structural twin of `native_group_solver` |
| `.../rails/native_episode_config.py` | the `supply_variants` role field, its loader parse, its refusals, the arm factor in the ceiling, `supply_variant_for_phase` on the run binding |
| `.../rails/native_episode_receipt.py` | `validate_supply_variant_receipt` |
| `.../rails/controllers.py` | `phase-native-candidates-review-revise-variants4-v1` registration |
| `.../rails/runner.py` | the live wiring: the arm contact context, `supply_variant_messages`, the per-visit arm resolution and the delivering-arm check in `settle`, the arm contact batch, the arm record reader, the seal-time validation, the `supply_variants` result field |
| `.../reproduction/ojw/native_roles.py` | `NativeRoleContactContext.variant_arm_id` |
| `.../reproduction/ojw/native_request.py` | the CONDITIONAL arm key in the role custody document |
| `.../reproduction/ojw/native_episode.py` | the graph builder admits the arm node at the solver position |
| `.../core/flight/runtime.py` | `_supply_variant_binding` (one router per arm), the kept router options, the seal-path validation and the sealed `supply_variants` field |
| `.../analysis/native_episode_dry_run.py` | `DryRunArm`, per-node arms, `supplied_counts_by_arm()`, `delivered_arm_id()`, the per-arm walk |
| `configs/policy/phase-native-candidates-review-revise-variants4-v1.json` | NEW. The 17-contact program |
| `configs/baseline/slurp-native-stage3-var2-supply-variants-r01c-baseline-v1.json` | NEW, UNREGISTERED. The four-arm reference form |
| `tests/unit/test_stage3_supply_variant_interleaving.py` | NEW. 70 tests across six layers |
| `tests/unit/test_native_episode_runner.py` | the shared harness binds the optional per-arm resolver |

## 10. The offline dry run

`analysis/native_episode_dry_run.py` walks every arm of the variant node, resolving each arm's supply
against the SAME staged context a flight resolves it against, and reports per arm the resolved knobs,
the supplied value ids and the item count — labels, ids and counts only. Two new report surfaces:
`supplied_value_counts_by_arm()` (`{phase: {arm id: count}}`, the dry run's per-arm table) and
`delivered_arm_id()`. The walk carries the same fail-closed delivering-arm check the runner does.

On the synthetic row the test module walks (`test_the_dry_run_walks_every_arm_of_a_synthetic_row`):

| node | arm | deliver | resolved knobs | supplied ids |
| --- | --- | --- | --- | ---: |
| solver | `wide` | no | `train-exemplars.phase_supply.solver.k = 30` | 1 |
| solver | `plan` | **yes** | — | 0 (= the row's own bootstrap, byte-identical) |
| perception | — | — | — | (no arms: the group fans out one node) |

A full walk of a REGISTERED VAR-2 cell on the released stores is available through the existing CLI
(`--experiment/--cell`) once the cell exists; an unregistered form deliberately has no experiment
fragment to name.
