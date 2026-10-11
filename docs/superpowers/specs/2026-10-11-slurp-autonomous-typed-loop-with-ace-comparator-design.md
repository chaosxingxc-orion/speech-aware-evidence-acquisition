# SLURP autonomous typed loop with the ACE comparator (decision 263-A): engineering design

Author: Claude Opus 5.5 (design agent, on the coordinator's brief and two owner-guidance addenda relayed by the
coordinator, Fable 5.1), 2026-10-11, branch `opus/263-spec` (base master `ee5e4f521`). Status: DESIGN, model-free.
No model, server, tokenizer, encoder, GPU, dataset or network contact was made. Nothing here registers a cell or
authorises a flight: decision 263 is PROPOSED (`docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`,
last section). This spec makes registration immediate if the owner rules 263-A. Every claim about code or record
cites a file. External-paper mechanics for SkillOpt, DGM and RRSI are the coordinator's summaries of 2026-10-11, quoted
as given and to be checked against the papers at registration. ACE mechanics are from arXiv 2510.04618 as read in
`docs/readiness/2026-10-11-slurp-tfrl-lineage-and-algorithm-baseline-analysis-v1.md` sections 1 and 3.

## 0. Answer first

- **Loop.** Three iterations on TRAIN Fold B (`SLURP-EVO-FOLD-B-V2`, 1,080 rows). Each iteration is one same-flight
  supply-variant cell on lock v2.2 with these Solver arms: `lock` (delivering, last), `aa` (twin), `par` (the
  accumulated typed parent, from iteration 2 on), `typ` (the typed child) and `ace` (the ACE playbook column).
  Delivery-rule candidates are read OFFLINE over the sealed columns (0 GPU).
- **Iteration 1.** Its class is credit-driven selective knowledge augmentation from TRAIN (owner, 2026-10-11): a
  slot-card supply plus exemplar-stratum composite, with anti-pattern guards read offline (section 2.1).
- **Proposer.** The frozen core in its text-only seam. It reads aggregate tables only and emits a JSON candidate
  under a closed schema enforced by `json_schema` on the wire. A deterministic validator accepts or refuses it, and
  the validator also computes the predicted effect. The model proposes and never judges.
- **ACE.** Generator, reflector and curator as published, with one change: helpful/harmful counters and playbook
  acceptance are computed by the same script objective. It runs under the same proposer model, the same tables and
  the same token allowance.
- **Selection and confirmation.** Fold B selects with the instrument. Fold A confirms once (`lock`, `aa`, final typed
  state, final ACE state). DEV-2000-ADDED reads the composed system the same way.
- **Budget.** About 8.1 GPU-h planned, with an 11 GPU-h ceiling including one recovery (section 5.5).
- **Before any flight.** Six model-free engineering items are needed (section 9). Two of them are the S1 spec's
  E-S1 and E-S2, which are still unbuilt: `rails/consumption_module.py:600-603` refuses every non-template column
  under review-off.

## 1. Roles and the objective (owner guidance, 2026-10-11)

### 1.1 Five roles, each with one owner

| role | what it is here | owner | code (reused / new) |
| --- | --- | --- | --- |
| (a) LEARNING ELEMENTS | the typed system state. It is a set of hash-pinned artefacts: exemplar release, slot-card release, supply knob values, delivery-rule list and scope lists (section 2). Nothing else is learnable. | data | `knowledge/slurp/...` releases; `prepared/SAEA-SLURP-TFRL-*` tables |
| (b) OBSERVE | sealed per-arm trajectories, the official scorer on copies, process metrics | deterministic | `scripts/analysis/stage3_rollout_score.py --mode supply-variants` (`:2272`), `reproduction/slurp_scoring.py`, `analysis/slurp_process_metrics.py` |
| (c) ANALYSE AND INTEGRATE | per-row typed credit, contrast tables, exchange rates, archive update | deterministic | `analysis/sealed_credit/{credit,row_states,estimate,accept}.py`, `scripts/analysis/slurp_nx_exchange_rates.py`, `slurp_nx_solver_column_read.py` (E-S2), new `scripts/analysis/tfrl_contrast_tables.py` |
| (d) REFLECT AND PROPOSE | emits ONE candidate per operator class (typed arm) or delta items (ACE arm), schema-bound | model, text-only | new `rails/tfrl_typed_proposer.py`, `rails/tfrl_ace_material.py` on the construction-material seam (`core/flight/runtime.py:815-840`) |
| (e) ITERATE | validation, archive, parent choice, package derivation, launch sequence | deterministic driver + instrument | new `scripts/flights/tfrl/` (section 7) |

Role (c) may optionally ask the model to summarise tables into hypotheses. This design does not do that: the
hypothesis field of the candidate schema is a closed enum (section 3.2), so no model summary is ever needed.

### 1.2 The objective is a script (hard invariant I-OBJ)

Every acceptance, selection, credit, counter and predicted-effect figure comes from one of three sources:
- the official SLURP scorer (`reproduction/slurp_scoring.py`, registered TRAIN sibling `slurp-slu-official-train`);
- deterministic readers over sealed bytes (`stage3_paired_read.py`, the whole-utterance cluster bootstrap, 10,000
  draws, seed 20260915);
- the exchange-rate table.

No model output is ever read as a score, a verdict or a counter. The validator recomputes the predicted effect and
ignores any number the model writes; the schema has no numeric effect field at all. GRPO's discipline is the analogy:
the reward is scripted and the policy only proposes. The ACE departures that follow from I-OBJ are listed in section 4.4.

### 1.3 The RSI shape: archive, edit, empirical validation, parent choice

The loop takes its shape from the recursive-self-improvement family the owner named. From DGM (2505.22954) it takes an
archive of agents, parent sampling and empirical validation. From AlphaEvolve-style search it takes evolutionary edits
of a program. From SkillOpt (2605.23904) it takes a frozen target, an optimiser model, bounded patch edits, a
rejected-edit buffer, a meta update and a held-out gate. The "program" here is the TYPED SYSTEM STATE.

| RSI element | this design | kept / changed |
| --- | --- | --- |
| archive of agents (DGM) | `archive-i<t>.json`: every state ever built. A state records `state_id`, its parent, its artefact hashes, the operator applied, its status (`accepted` / `refused` / `proposed-not-flown` / `invalid`), its credit vector (SLU and intent delta vs `lock`, and vs `par` from iteration 2 on, with CI95; per-scenario 18-row table; empty vs non-empty gold) and the predicted effect | kept |
| parent selection with diversity (DGM samples by score and inverse child count) | deterministic: parent = the accepted state maximising `LB_slu(state - lock) - 0.25 pp x n_children(state)`; ties go to fewer changed artefacts. A parent with two refused children of one operator class has that class masked for the next proposal | kept, made deterministic |
| edit = one component, bounded (SkillOpt patch ops under a textual learning rate L_t from 4 to 2) | one candidate edits exactly ONE component with at most L_t operator applications: L_1 = 2, L_2 = L_3 = 1 | kept, typed |
| skill document (SkillOpt, 300-2,000 tokens of prose) | the typed state. Prose supply pays a per-row form cost here (D2: twins reproduce arms, `docs/results/2026-09-26-slurp-stage3-locked-tfrl-academic-baseline-v1.md` 3.1) | changed |
| rejected-edit buffer | the archive's refused siblings and their per-stratum tables, rendered to the proposer as aggregate tables (section 3.3) | kept |
| meta update (optimiser-side, never shipped) | `proposer-meta-i<t>.json`: per operator class, the count proposed / valid / flown / accepted / refused and the mean realised minus predicted pp. Shown to the proposer only, never to any node | kept |
| held-out gate (SkillOpt: strict improvement, ties rejected, no noise model) | the instrument: same-flight column with a twin and a CI95 rule (section 5.3); Fold A = the final transfer check | changed: a noise model is mandatory (`docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md` 2b) |
| scoring = native hard score, no LLM judge (SkillOpt) | official scorer only (I-OBJ) | kept |
| regularisers against benchmark overfitting and drift (RRSI 2609.24972) | utterance-hash cross-fit for fitted thresholds; per-stratum tables; fresh-roster Fold A then DEV; `par` re-measured in every flight | kept |
| heterogeneous domains need more than one skill (SkillOpt limitation) | the per-scenario scope operator (section 2, class `scope`) | kept |
| self-editing arbitrary code / prompts (DGM, coding agents) | FORBIDDEN. The operator set is closed and typed; no node prompt, template, note contract or code is editable (decision 245; NX C3 in `docs/readiness/2026-10-09-slurp-nx-node-extreme-programme-v1.md`) | deliberately not allowed |

The archive makes refused candidates useful in two ways. They stay in the archive as negative evidence in the next
tables. They also count against their parent's diversity term.

### 1.4 The proposer model: a design question (owner guidance dimension 1)

| option | model | where it runs | constraint on file | assessment |
| --- | --- | --- | --- | --- |
| (i) | the frozen Qwen3-Omni-30B-A3B instruct core, text-only seam `construction-proposer-text` | the resident np4 serving session, between flights; 22 contacts per iteration at most, minutes | none new; decision 255 as ruled | **recommended for 263** |
| (ii) | Qwen3-Omni-30B-A3B-THINKING Q4_K_M (umbrella `docs/datasets.lock.json` key `qwen3-omni-30b-a3b-thinking-gguf-q4km`, entries near lines 1017-1048) | GPU only in a serving gap. The card is 24 GB with about 22.6 GB resident for the serving core (memory `gpu-parked-during-cpu-steps`), so the two never co-reside. On CPU the full Q4 model in host RAM is forbidden beside a GPU flight and blocks the 12 GB host-free serving-start guard (WSL cap 44 GB; repo memories `host-memory-kill-hazard`, `cpu-sidecar-blocks-serving-restart`) | lock note: "pre-download only ... NOT admitted for any flight"; thinking decode lengths exceed the 512-640 completion ceilings, so it needs its own geometry registration | ablation after 263, not inside it |
| (iii) | a separate local text-strong model on CPU | CPU, only with no serving session resident (same host-RAM rule) | needs a new asset lock entry, receipt and D2 arm | not recommended now |

Why (i) inside 263: fairness. Both the typed arm and ACE use the same optimiser, so the comparison isolates the
update form (D1-D7), not optimiser strength. SkillOpt's ablation (a target-matched optimiser recovers 56-74 % of a
frontier optimiser's gain) says the same-model seam is a reasonable first optimiser. It also says a stronger local
optimiser is worth a later, separately registered ablation; option (ii) is the candidate for that.

**An offline proposer is not a "second answering LLM"** (study `CLAUDE.md`, research boundary):
- It never receives audio. The seam is text-only (`e0/d2_leakage.py:91-135`).
- It never sees an evaluation row, and it answers no scored row.
- Its only output is an artefact. That artefact is validated against a closed schema, hash-pinned and enters a later
  flight only through registered config. This is the same argument `e0/d2_leakage.py` states at the field
  declaration ("its output is an ARTIFACT ... never an answer to a scored row").
- Final-answer authority stays with the serving core.

**What every proposer contact must log:**
- an exposure-ledger row in `docs/exposure-ledger.md`, written before the result is read;
- the GGUF per-file SHA-256 and llama.cpp build commit (the runtime receipt);
- the rendered-instruction SHA-256 (material receipt; no text);
- the contrast-tables SHA-256 and the archive SHA-256;
- decoding (temperature 0, pinned seed) and the serving geometry.

**Owner ruling needed:** 263-A must state that decision 255's "frozen core's text-only seam" covers both the typed
proposer and the ACE reflector. Option (ii) needs a decision-255 amendment of its own (a second model file on an
offline-only arm) and is not requested here.

## 2. The typed operator set and its artefacts

A candidate edits ONE component. The read column says how its effect is read: OFFLINE means 0 GPU at the 0.67 pp floor
(`docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md` 2c). SF means a same-flight Solver supply-variant
arm.

| class / operator | artefact it changes (pinned) | existing code that varies it (precedent) | read |
| --- | --- | --- | --- |
| construction / `exemplar-selection` | a SELECTION release of `train-exemplars` (`knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars/`, snapshot `4c498dc0...`). Per scenario, a selector from a closed enum `{all, entity-free-only, slot-bearing-only, drop-slot-bearing-if-entity-free-share>=theta}`, with theta in {0.4, 0.5, 0.6, 0.7, 0.8}. Values are byte-identical to the parent; the facet-vector file stays a superset | B1 exemplars (+12.61); P-N1 builder pattern (S1 spec section 6.3 item 7); `scripts/build_slurp_stage3_r01_excluded_exemplar_store.py` | SF via `release_swap` (`rails/supply_variants.py:293`) |
| construction / `slot-card-subset` | a release of `slot-contracts` (`knowledge/slurp/semantic/slot-contracts-v2/`): per named intent, drop listed slot types from its card | B4b slot store v2 (+2.55); W4 cards (closed, decision 191: the proposer may not re-author card TEXT, only subset types) | SF via `release_swap` |
| construction / `key-source` | the centroid key view (intent-boundaries, Perception first-phase supply) | COMP-1b, K6p | **DISABLED in 263.** A Solver arm cannot vary the first phase (`parse_supply_variant_knob` refusal, S1 spec section 1.1), review-off refuses branch columns (`rails/consumption_module.py:600-603`), and P-SV-4 closed the intent levers |
| supply / `knob-set` | Solver knob tails `train-exemplars.phase_supply.solver.{k, fuse_coverage.m, .c, .top_l}` and `slot-contracts.candidate_supply.solver.max_candidates` (1-2), positive integers | M1 k (W-SV-1 k30 -0.46; VAR-1 k10 +0.07), EX-DIV, VAR-2 (`SUPPLY_VARIANT_KNOB_TAILS`) | SF via `overrides` |
| supply / per-scenario k | -- | none: knob tails are global | **DEFERRED** (needs a scenario-conditioned knob table; not in 263) |
| delivery / `deliver-rule` | the delivery-rule list appended after v4g. The model names a rule FAMILY of the v4g grammar (`fx-article`, `fx-oclock`, `fx-month-ordinal`, `scope`, `ti0`, `ti1`, `vs-type`, `vs-any`, `ee5`, `ee10`, with or without the Wilson guard; `scripts/analysis/slurp_nx_postproc_v4_search.py` docstring, `rails/delivery_normalisers.py:1093-1180`) and its target types / intents. **Thresholds are fitted by the script** on one utterance-hash half of Fold B and read on the other (cross-fit) | v4g (+1.55 Fold B, +0.98 A2), the c3 x N1 gate, VER-1 | OFFLINE, over every sealed column (`lock`, `par`, `typ`, `ace`) via `slurp_nx_postproc_v4_apply.py --apply` |
| scope / `scope-restrict` | the scenario applicability list of one entry, either a delivery rule (offline) or a slot card (a release whose card `associated_facet_ids` are restricted; the cards are candidate-bound, `rails/knowledge_stores.py` `context_supply` / `candidate_supply` routes) | v4g scope rule and per-intent guards; CELL-3 scenario gate (the form) | delivery: OFFLINE; card: SF via `release_swap` |

An accumulated state may change at most two stores (`train-exemplars`, `slot-contracts`) by release swap.
`SupplyVariantReleaseSwap` (`rails/supply_variants.py:293`) repoints ONE store per arm today, so iteration 1's
composite (2.1) needs E-T6: a `release_swaps` list of at most one swap per distinct store, receipt schema v5, built
before the flight commit is frozen (R3). Without E-T6 the validator refuses a second-store swap. Knob edits and
delivery and scope rules compose freely.

### 2.1 Iteration 1 operator class: credit-driven selective knowledge augmentation from TRAIN (owner, 2026-10-11)

The owner asked to "selectively expand and add knowledge from the training set, based on the evaluation metric and the
bad cases". This is iteration 1's class. Because the composite edits two components under L_1 = 2, it is the one
declared exception to "one component per candidate".

**Record facts, all Fold A unless noted:**
- Existence is not the gap. Knowledge absent from the store: 2 items in 2,705 rows
  (`docs/results/2026-09-26-slurp-knowledge-coverage-and-failure-mode-attribution.md`).
- Supply is the gap. Items in TRAIN's value list but not supplied (class E4): 40 items, oracle 2.33 pp
  (`docs/results/2026-09-29-slurp-slu-consumption-headroom-offline.md`).
- Intent misses are rank misses. The gold intent's median rank on intent-wrong rows is 13 / 10 / 14, against 1 on
  correct rows, and widening k is refuted (`docs/results/2026-09-26-slurp-intent-retrieval-rank-diagnostic.md`).
- Conversion is partial. The agreement vote converts 45.7 % of newly delivered gold entries
  (`docs/results/2026-09-27-slurp-conv-probe-read.md`).
- Some misses are unreachable. 35 of the 70 S2a.1 not-in-supply MISSING items are not in the transcript either, so
  knowledge cannot reach them (`docs/results/2026-09-30-slurp-s2a1-missing-slot-recall-ceiling-offline.md`).
- Exchange rate: +0.062 pp per recovered MISSING entity (exchange-rate note section 4).
- Negative precedent: contrast-pair exemplars LOWERED Perception recall
  (`docs/results/2026-09-29-slurp-psv1-fold-b-branch-read.md`).
- False fill on empty-gold rows (about 40 % of rows) is the largest single loss. v4g's rate guard (`ee10` + Wilson,
  `rails/delivery_normalisers.py:1170-1178`) is the existing negative-knowledge rule.

| operator | what it does | artefact | builders / precedent | read |
| --- | --- | --- | --- | --- |
| (a) `slot-card-supply` | For the failing (slot type x scenario) cells of the credit table (E4 class, Fold B), promote TRAIN value-list entries of those types into the capped card window. `max_values_per_candidate` 16 and `max_total_values` 28 are not knob tails (S1 spec 1.2), so the edit is a REORDERING inside an alternate release, never a cap change | `slot-contracts` alternate release (slot store view) + its supply fragment pin | `rails/semantic_knowledge_build.py` `saea-authored-slot-contracts-v1`, released by `core/semantic_knowledge_preparation.py`; views `scripts/build_slurp_knowledge_index_view.py`; B4b (+2.55); K8 card selection (`scripts/analysis/slurp_w1_card_selection_measurement.py`) | SF |
| (b) `exemplar-stratum` | For failing (scenario x intent) strata, re-weight by a per-stratum keep-quota selection (no re-encode) or targeted expansion with TRAIN rows outside the evaluation folds that the size-pool omitted. Per-scenario k is DEFERRED (global knob tails), so weighting is carried by the view | `train-exemplars` alternate release (exemplar index view) | `scripts/build_slurp_exemplar_pool_assets.py`, `scripts/build_slurp_stage3_r01_excluded_exemplar_store.py` (selection), `scripts/build_slurp_exemplar_twin_vectors.py` (vectors), `rails/knowledge_build.py` `saea-kb-distmodel-v1` / `build_knowledge_snapshot`; B1 (+12.61), M1 k | SF |
| (c) `anti-pattern-guard` | Per-scenario negative knowledge learned from TRAIN statistics: an entity-rate or type-by-intent guard per scenario, extending v4g's rate guard; RIZZ anti-patterns | a delivery-rule table (`prepared/SAEA-SLURP-TFRL-GUARDS-I1-V1/`) | `scripts/build_slurp_v4_train_statistics.py`; the v4g search grammar | OFFLINE, 0 GPU |

**Fold hygiene.**
- Content is mined only from TRAIN minus Fold A, Fold B, DEV and R01/R01C. Every builder re-proves disjointness at run
  time, as `build_slurp_v4_train_statistics.py` does.
- The Fold B bad cases choose only WHICH strata are edited, as aggregate cells. They never supply content.
- Fold B selects, Fold A confirms, DEV composes.

**0-GPU pre-read (must move before the column is registered).** Run `scripts/analysis/tfrl_augmentation_coverage.py`
over the sealed Fold B lock column. It reuses the offline re-retrieval of `analysis/fusion_form_offline_gate.py` and the
coverage logic of `scripts/analysis/slurp_knowledge_coverage_and_failure_mode_attribution.py` and
`slurp_s2a1_recall_ceiling.py`. It counts bad-case rows whose gold entry or value becomes PRINTED in the arm's supply
under (a)+(b) and not under the lock.
- Rows unreachable by knowledge (not in the transcript) are excluded.
- Rows that lose a print are netted.
- The pre-read refuses the candidate if newly printed bad-case items x 0.457 x 0.062 + (b)'s predicted share is below
  +1.5 pp.

**Predicted effect.** If all 40 E4-class items were supplied, about 18 would convert (45.7 %); at +0.062 pp each that is
about +1.1 pp SLU-F1. The intent side is unmeasured. That is why the iteration-1 candidate is the COMPOSITION (a)+(b):
(a) alone cannot clear decision 192's 1.5 pp predicted bar. Fold B counts replace the Fold A figures at the pre-read.
(c) is read offline and accepted on its own criterion (3.4).

**Identity consequences.**
- New alternates in the base change the composed config and protocol hash, so each iteration is a new cell.
  Registered plan pins are refreshed after every flip (memory `registered-plan-pins-after-flip`).
- A content-rewriting view must rebind its source hashes (memory `level2-note-sha-binding-2026-10-10`).
- Targeted expansion needs a registered ENCODE preparation (an embedder contact with a ledger row) and a superset
  facet-vector file. The lock arm's pinned file then changes bytes, so P-ACE-0's byte-identity proof must also show the
  `lock` request is unchanged. A pure selection needs neither.
- E-T1/E-T2 touch `core/flight/runtime.py`, one of the five files the prepared-supply identity pins
  (`core/flight/repin.py:1-12`). They merge before the freeze, and every ready cell is re-pinned once.

## 3. The proposer seam

### 3.1 Contact and material

- **Cell family.** `slurp-native-stage3-tfrl-proposer-i<t>-v1` (typed) and `slurp-native-stage3-tfrl-ace-reflector-i<t>-v1`
  (ACE). Both are text-only on the `construction-proposer-text` arm (`contracts/identifiers.py:62`) and carry no audio
  part.
- **Carrier rows.** Each contact is carried by one carrier row of a committed construction-role sub-roster of Fold B.
  Fold B is `roster_role: construction`, split role `discovery` (`docs/receipts/rosters/slurp-evo-fold-b-v2.json`), so
  `contracts/gate_exposure.py:191-227` admits it. This is the GEPA precedent:
  `docs/receipts/rosters/slurp-stage3-gepa-r01c-carriers-v1.json` and `rails/stage3_gepa_material.py` ("one instruction
  per GROUP, carried by that group's CARRIER row").
  - Typed proposer: 3 carriers, one per enabled class (construction, supply, delivery+scope).
  - ACE reflector: 18 carriers, one per scenario.
  - New roster receipts `slurp-tfrl-proposer-fold-b-carriers-i<t>-v1.json` are drawn by a seeded rule from Fold B's
    first row per scenario, under the construction-roster builder pattern.
- **Material.** New program ids `phase-tfrl-typed-proposer-v1` and `phase-tfrl-ace-reflector-v1`, dispatched in
  `FlightRuntime`'s construction-material resolver beside `phase-stage3-gepa-v1` (`core/flight/runtime.py:815-840`).
  - The renderers live in `rails/tfrl_typed_proposer.py` and `rails/tfrl_ace_material.py`. They render the pinned
    tables (3.3), the archive digest and, for ACE only, the current playbook items.
  - Receipts seal ids, counts and digests only (the `GepaContact.as_json` discipline).
  - The `construction_targets` field stays empty: the contact needs no per-row gold, only aggregates.
- **Instruction artefact.** `configs/probes/tfrl/typed-proposer-v1.txt` and `configs/probes/tfrl/ace-reflector-v1.txt`,
  sha256-pinned in the fragment. They are written once, before iteration 1, and never edited between iterations.
- **Grammar on the wire.** New response-format ids `saea-tfrl-typed-candidate-v1` and `saea-ace-delta-items-v1` send
  `response_format: {type: json_schema, json_schema: {schema}}`. `core/model/adapter.py:235-260` already validates
  that form; it is the form the Perception note contract `slurp-intent-hypotheses-v1` uses. Completion ceiling 1,024;
  temperature 0; one contact per carrier; no re-sampling.

### 3.2 Candidate schema `saea-tfrl-typed-candidate-v1` (no free-text field)

```json
{"schema": "saea-tfrl-typed-candidate-v1", "iteration": 1, "parent_state_id": "s0-lock-v2.2",
 "operator_class": "construction|supply|delivery|scope",
 "operator": "exemplar-selection|slot-card-subset|knob-set|deliver-rule|scope-restrict",
 "target": {"failure_class": "SPURIOUS|MISSING|WRONG-TYPE|BOUNDARY|NEAR|WRONG-VALUE|FORMAT|EMPTY-GOLD-FILL",
            "slot_types": ["<enum: TRAIN slot types>"], "scenarios": ["<enum: 18 scenarios>"],
            "value_in_supply": "E1|E2|E3|none|any"},
 "hypothesis_code": "<enum: fewer-copied-pairs|more-printed-values|type-inventory|empty-signal|rule-filter|scope-narrow>",
 "applications": [ "<1..L_t objects, shape fixed by operator>" ]}
```

Application shapes:

| operator | shape |
| --- | --- |
| `exemplar-selection` | `{"scenario", "selector", "theta"}` |
| `slot-card-subset` | `{"intent", "drop_types": [...]}` |
| `knob-set` | `{"tail", "value"}`; integer, range-checked against the admissible ranges of S1 spec section 1.2 |
| `deliver-rule` | `{"family", "guard": "none|wilson", "types": [...], "intents": [...]}`; no threshold, the script fits it |
| `scope-restrict` | `{"entry_kind": "deliver-rule|slot-card", "entry_id", "scenarios": [...]}` |

Every enum is generated from pinned TRAIN tables. Closed enums mean the schema cannot carry utterance text, a filler
or a number the model invents.

### 3.3 Tables (the only content the proposer reads)

New `scripts/analysis/tfrl_contrast_tables.py` writes the tables. It is deterministic, counts and rates only, and writes
`tables-i<t>.json` + `tables-i<t>.md` under `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-TFRL-TABLES-I<t>-V1/`, pinned by
sha256 in the next proposer fragment. It reuses:
- the class x slot-type x value-in-supply cube of `slurp_nx_exchange_rates.py` (`docs/results/2026-10-09-slurp-nx-exchange-rates-offline.md`
  section 6, the NX C3 input), extended by a scenario axis;
- per-arm node metrics from `slurp_nx_solver_column_read.py` (E-S2: supply columns);
- official per-arm columns from `stage3_rollout_score.py --mode supply-variants` and `stage3_paired_read.py`;
- the archive (credit vectors of every state, refused siblings included) and the meta summary.

Cells with fewer than 3 rows are reported as "<3", so a cell cannot single out a row. Iteration 1's tables come from
the already-sealed lock v2.2 greedy sample on Fold B (`SAEA-SLURP-STAGE3-VER1A-SAMPLES-FOLD-B-V1`, sample 0 = today's
delivery; `docs/results/2026-10-11-slurp-ver1-verification-layer-fold-b-fold-a-read.md`), at 0 GPU.

### 3.4 Validation (deterministic, `rails/tfrl_typed_proposer.validate_candidate`)

The validator refuses, by name, all of the following:
- an unparsable or non-schema answer, or an enum value outside the pinned tables;
- more than L_t applications, or an application on a DISABLED or DEFERRED operator;
- a class masked by the diversity rule;
- a second release-store swap (section 2);
- a knob outside its admissible range;
- a selection that would empty a scenario's pool (an empty supply is legal per decision 199; an emptied pool
  disables recall and is refused);
- an estimated per-arm prompt over the live slot with the 3,072 reserve (`SupplyVariantFitEstimate`,
  `rails/supply_variants.py:377`);
- a candidate byte-identical to its parent or to an archived state.

**Predicted effect (decision 192).** The script computes it, never the model:
- For construction and supply candidates: run the offline re-retrieval at zero encoder contacts over pinned vectors
  (`analysis/fusion_form_offline_gate.py`; S1 spec section 6.3 item 6). This gives newly printed and un-printed gold
  pairs by class. Multiply them by the M1 printing conversion 0.2471 and the class exchange rates: +0.062 per MISSING
  recovered, +0.029 per SPURIOUS removed, +0.091 per wrong entity repaired, +0.033 per emptied false-fill row
  (exchange-rate note section 4).
- A candidate under +1.5 pp predicted SLU-F1 is refused (decision 192) and logged as `refused-prediction`.
- Delivery and scope-on-rule candidates are not predicted. They are MEASURED offline, cross-fitted, and accepted on
  CI95-LB > 0 and a point >= 0.67 pp: the v4g/VER-1 criterion, which `docs/results/2026-10-11-slurp-ver1-verification-layer-fold-b-fold-a-read.md`
  item 1 states.

**Retries.** A refused answer is re-rendered at most twice in the same iteration, with the refusal table appended. That
costs one further contact per retry; this is the rejected-edit buffer inside the epoch. If nothing valid comes back,
the class has no candidate for that iteration.

**Selection among valid candidates.** The column carries the valid SF candidate with the highest predicted pp. The
other valid candidates are archived as `proposed-not-flown`.

**Hand-author fallback.** A person may write the same JSON. It passes the identical validator and is labelled
`proposer: hand-author:<role>` in the archive, the read and the curve. It is used only if the owner orders it for an
iteration; it is never a silent substitute.

### 3.5 Exposure rows per proposer contact

Rows are drafted by the writer and countersigned by the coordinator before the first contact, in the
`docs/exposure-ledger.md` form of the GEPA proposal cells. Each row records:
- the carrier roster id and split identity, and the plan id;
- `planned_model_calls` = carriers x (1 + 2 retries), run-cumulative (memory `plan-budget-is-run-cumulative`);
- audio seconds 0;
- the arm, the tables and archive sha256, the instruction sha256, the model files hash and the geometry;
- the statement "aggregates of TRAIN Fold B credit; no per-row gold, no utterance text, no output text".

## 4. The ACE comparator column (`ace-grow-refine-v1`)

### 4.1 Instantiation

| ACE role (arXiv 2510.04618) | here |
| --- | --- |
| generator | the lock v2.2 Solver, rendering the current playbook. Its trajectories are the sealed `ace` column of the previous iteration; iteration 1 uses the lock's VER-1a column, as for the typed arm |
| reflector | the frozen core, text-only, one contact per scenario. It reads that scenario's typed credit tables for the `ace` column (3.3) and the current playbook items with their counters. It may write free-text items, because that IS the baseline |
| curator | a deterministic incremental delta merge, never a whole-view rewrite (4.2) |
| playbook | a pinned store `ace-playbook` (release `knowledge/slurp/semantic/ace-playbook-i<t>/`, built by `rails/semantic_knowledge_build.py` policy `saea-authored-stage3-deltas-v1`, `scripts/build_slurp_stage3_delta_store.py`), routed `context_supply` to the Solver. The `lock`, `aa`, `par` and `typ` arms see the empty release `ace-playbook-i0` (zero values); `ace` swaps to `ace-playbook-i<t>` |

**Item schema (`saea-ace-delta-items-v1`, paper fields):** `{"item_id", "section":
"strategy|pitfall|format-rule", "scope": {"scenarios": [...], "slot_types": [...]}, "text": "<= 400 chars ASCII",
"helpful": int, "harmful": int, "provenance": [...]}`.
- The reflector emits at most 3 `add` items per contact; it never emits counters or ids.
- `item_id = ace:i<t>:<sha256(normalised text)[:12]>`.
- Text passes the decontamination gate of `rails/proposer.py`:
  - no sample identifier (`_carries_sample_identifier`, `:256`);
  - no word 6-gram shared with Fold A / DEV query text (`load_evaluation_ngram_digests`, `:331`);
  - ASCII only.

### 4.2 Curator (deterministic)

1. **Grow.** Append the new valid items. Version t = version t-1 verbatim plus the new rows.
2. **De-duplicate** with the S3-5 rule (`docs/superpowers/specs/2026-09-22-stage3-tfrl-base-loop-engineering.md`
   S3-5): exact normalised text, then token Jaccard >= 0.8 against every earlier item. The later item is dropped and
   its provenance is merged into the survivor. Departure from the paper: its semantic-embedding de-dup would need an
   extra embedder contact.
3. **Counters, by script (I-OBJ).** For each item and each row in the item's scope, compare per-row official credit
   in the sealed `ace` column with the same row in the `lock` column. `helpful += 1` where `ace` is higher and
   `harmful += 1` where it is lower. Departure from the paper: there the model judges helpful/harmful. The departure
   is made so both arms are judged by the same objective.
4. **Refine.** Remove an item once it has `harmful - helpful >= 3` over at least 10 scoped rows.
5. **Order and cap.** Order items by `helpful - harmful`, then by id, and truncate at the token allowance (4.3).

Acceptance of the playbook state is by the instrument (5.3), exactly as for the typed arm. What is compared is the
proposer and update FORM, not the judge.

### 4.3 Token budget parity

Every non-twin arm has the same per-row ceiling on supplied tokens:
- **Allowance.** `T_cap` = the lock's measured p99 supplied tokens on Fold B plus `A` = 1,880 tokens. `A` is 8 items
  x 235 tokens per supplied item, the NX fit frame (S1 spec section 1.1: `max_supplied_items` 55,
  `tokens_per_supplied_item` 235).
- **Who uses it.** The ACE playbook spends `A` on prose items. The typed arm may spend it on, for example, a larger k.
- **Enforcement.** (1) The arm's `max_supplied_items` and `fit_estimate` in the supply column (E-S1). (2) The curator
  truncates by token count, measured on the serving tokenizer at the FIT step (a `/tokenize` call, zero generation).
  (3) The 4-row dry run refuses an arm over `T_cap`.
- **Headroom.** Slot 24,576, reserve 3,072 (memory `fit-gate-live-slot-reserve`), Solver prompt 10-11k
  (lineage note P5). ACE's reported 18k-token contexts do not fit, so the cap is binding by design.

### 4.4 What ACE is given that the paper does not have, and why that is fair

ACE receives four things beyond the paper:
- typed per-row credit tables, as its execution feedback. The paper uses execution signals; the official scorer is
  that signal here (P2);
- a hard token cap (D6). Without it the playbook could not fly in the slot;
- script-computed counters (I-OBJ);
- the same three iterations and the same optimiser model as the typed arm.

ACE keeps its own update form: free-text items and global inclusion, with no key (D3) and no typed operator. The
measured differences are therefore D1 (reflector), D2 (prose), D3 (no key) and D7 (scope). That is the comparison
decision 263 asks for.

**The ACE column violates decision 245** (free text into the Solver prompt) **by design**. 263-A must rule it a
non-delivering comparator that can never be locked.

### 4.5 Labels

- `core/stage3_algorithms.py:289-302` (`ace-grow-refine-v1`): the citation moves from "see design spec section 6" to
  `arXiv:2510.04618`; the status stays `planned` until the first ACE column seals.
- The reflector cells carry `stage3_algorithm {id: ace-grow-refine-v1, operators_used: [update, selection]}`.
- The typed proposer cells carry `{id: sealed-credit-system-policy-v1, operators_used: [credit_assignment, update]}`.
- The iteration cell holds two algorithms in one fragment, so E-T5 adds an optional `columns` key `{arm_id:
  algorithm_id}` to the label. It is validated by `validate_stage3_algorithm_label` (`:448`), with `_KNOWN_LABEL_KEYS`
  extended. The cell id is `sealed-credit-system-policy-v1` and `columns.ace = ace-grow-refine-v1`.
- `scripts/checks/stage3_algorithm_label_check.py` then accepts the cell.

## 5. The per-iteration cell

### 5.1 Identity and arms

| item | value |
| --- | --- |
| cell / experiment | `slurp-native-stage3-tfrl-loop-i<t>-fold-b-v1` / `SAEA-SLURP-STAGE3-TFRL-LOOP-I<t>-FOLD-B-V1` (+ `-FIT-`, `-SMOKE-4-`, `-COLUMN-READ-`) |
| base | the review-off module on lock v2.2 (`rails/adapters/slurp_module_hooks.py:117` `CURRENT_LOCK`; `slurp_module_lock_v2_2.py`: v2.1 + v4g), uncited Solver |
| program | `phase-native-module-v1-c<2+K-1>`: c5 at iteration 1 (K = 4), c6 at iterations 2-3 (K = 5) |
| arms (`roles.solver.supply_variants`, `arm_visits: first`) | `typ` (overrides and/or `release_swap`); `par` (the accumulated parent state, from iteration 2); `ace` (`release_swap` to `ace-playbook-i<t>`); `aa` (`replicate_of: lock`); `lock` (delivering, last, no override) |
| delivery and scope rules | not arms: read offline over every column |

Under the `release_swap` limit, the `par` and `typ` arms carry one store swap each, plus knob overrides. A delivery
rule in the accumulated state is applied offline to `par` and `typ` alike.

### 5.2 Contacts and cost

The record gives the rates:
- lock v2.2 = 2.0 contacts per row (`docs/results/2026-10-10-slurp-nx-r5-composed-dev2000-added-read.md` item 2);
- each supply-variant arm adds one Solver contact per row (`rails/supply_variants.py` ceiling `base + (K - 1)`);
- R1 i1 flew 8 contacts per row on 1,080 rows in 2 h 16 m 54 s (S1 spec section 6.2), about 0.285 GPU-h per contact
  per row.

| step | contacts / row | contacts | GPU-h |
| --- | ---: | ---: | ---: |
| iteration 1 column (Perception + lock, aa, typ, ace) | 5 | 5,400 | 1.43 |
| iterations 2, 3 (+ par) | 6 | 6,480 each | 1.71 each |
| proposer + reflector contacts (21-63, text-only), smokes | -- | <= 100 | 0.1 per iteration |
| Fold A confirmation (lock, aa, typed final, ACE final) | 5 | 5,400 | 1.43 |
| DEV-2000-ADDED composed read (same arms, 1,000 rows) | 5 | 5,000 | 1.32 |
| **planned total** | | | **about 8.1** |
| **ceiling with one recovery** | | | **11** |

### 5.3 Selection rule (preregistered in `tfrl-loop-protocol-v1.json` before iteration 1)

All figures are official pooled micro SLU-F1 and joint intent, paired per row, whole-utterance cluster bootstrap. An SF
child X is ACCEPTED iff all five conditions hold:
- (a) the CI95 lower bound of X - `lock` is above 0;
- (b) the point of X - `lock` is at least 1.49 pp, the decision-190 SLU floor at n = 1,080 (`stage3_effect_floor_check.py`
  `same-flight-supply-variant`);
- (c) the point of X - `lock` exceeds `aa` - `lock` in the same flight;
- (d) from iteration 2: the point of X - `par` is above 0, strictly (SkillOpt's ties-rejected rule, on top of the noise
  model);
- (e) intent guard: at most 7 rows whose official intent correctness differs from `lock` in the losing direction
  (0.65 pp).

The per-scenario (18) and empty / non-empty-gold tables are reported with every verdict and gate nothing. Equal-stratum
weighting is reported beside the natural mixture.

An offline delivery or scope candidate is accepted on its cross-fitted CI95-LB > 0 and point >= 0.67 pp, over the
column of the state it edits.

The ACE state is accepted by the same rule (a)-(e), with `par` read as the previous ACE state. ACE "accepted" means
only that its next playbook grows from this one. A refused ACE state is still the generator for the next reflection,
as in the paper; the archive marks it refused.

### 5.4 State, stop, the curve

- **Cumulative state.** An accepted child becomes the archive's candidate parent. A refused one is archived as a
  sibling with its tables, and the proposer sees it next time.
- **Stop.** Exactly three iterations, whatever happens. No early stop and no extension.
- **The curve.** Two series per arm, typed and ACE, each with three points:
  - the realised Fold B delta of the best accepted state vs `lock` after iteration t;
  - the column delta of every flown candidate, accepted or not.
  A refused iteration repeats the previous accepted level. It is plotted, not dropped.
- **Claim rule (decision 263).** The typed loop's cumulative state vs `lock` has CI-LB > 0 on Fold A. ACE is reported
  either way.

### 5.5 Fold A confirmation and the DEV composed read

- **Fold A** (`SLURP-EVO-FOLD-A-V2`, split identity `61b0f062...`): one attempt, every rule fixed.
  - Arms: `lock`, `aa`, the typed final state, the ACE final state.
  - The offline delivery rules are applied with the thresholds fitted on Fold B. They are not re-fitted.
  - Exposure disclosure: Fold A has prior exposure from VER-1b/1c, COMP-1b, W-SV-1 and others.
- **DEV-2000-ADDED** (`docs/receipts/rosters/slurp-dev-2000-added-v1.json`): the same four arms, same-flight. The `aa`
  column is the in-chain A/A, as an in-flight twin, which is stronger than the cross-flight replicate the 2026-09-26
  instrument requires (rule 3), because no flight offset enters.
  - Claim ceiling `nominated` (`stage3_effect_floor_check.py` docstring: `same-flight-supply-variant` "may claim only
    nominated").
  - Lock admission (v2.3) after 263 needs the composed state on the delivered path. That is a cross-flight cell with an
    in-chain replicate at the 2.5 pp bar, or an owner ruling that accepts the same-flight DEV read; see 8, R4.

## 6. Checks and gates

Every iteration, confirmation and proposer cell must pass the following gates:

| gate | what it needs from these cells |
| --- | --- |
| `scripts/checks/stage3_effect_floor_check.py` | `stage3_measurement`: `measurement_design: same-flight-supply-variant`, `primary_metric_key: slu`, `rows: 1080` (DEV 1000), `expected_effect_pp` = the validator's prediction (>= 1.5; else `claims_benefit: false`, never true below the floor), `claims_benefit: true`, `nomination_rule: official-column`. Proposer cells: `form-proof`, `claims_benefit: false` (fewer than 200 rows, rule 5) |
| `finite_completion_policy_check.py` | `native_episode.finite_completion_policy: "deliver-latest-or-abstain"` and `react_exhaustion_policy: "continue-without-answer"` on every iteration cell and its smoke |
| `harness_admission_check.py`, `engineering_base_check.py` | no new module under `rails/probes/`; no new controller or `TaskAdapter` subclass; every `policy` / `evidence_source` / `scorers` value resolves in `core.base`; new program ids and response formats registered |
| `stage3_algorithm_label_check.py` | labels as in 4.5 (E-T5) |
| `flight_registration_check.py --cell <id> --campaign-plan <plan>` | per cell before launch, including the registered-supply-binding gate (plan copies equal the minted `prepared_phase_supply`) |
| `results_ledger_check.py`, `handoff_freshness_check.py`, `experiment_handoff_check.py`, `derived_media_confinement_check.py` | ledger rows and the handoff refresh after each read |

**Launch sequence per cell** (memories `registered-plan-pins-after-flip`, `flip-scripts-must-be-loop-form`,
`gpu-flights-via-batch-driver-2026-09-21`):
1. countersign the exposure rows (coordinator);
2. mint the decision receipt (`tfrl_mint_receipt.py`, `module_alloff_mint_receipt.py` pattern);
3. run the loop-form flip (`scripts/flights/batch/repin_loop_generic.sh` + `tfrl_repin_cell.sh`);
4. `scripts/flights/refresh_registered_plan_pins.py --package <dir>`, then commit;
5. flip again (ledger hashes converge; memory `flip-convergence-needs-two-passes`);
6. gates;
7. queue wrapper `tfrl_batch_chain.sh`;
8. `SAEA-Batch-Driver` (PowerShell `saea_task.ps1`).

**New tests** (`tests/`):

| test | what it proves |
| --- | --- |
| `test_tfrl_typed_candidate_schema.py` | every refusal of 3.4 by name; enums generated from pinned tables; no free-text path |
| `test_tfrl_predicted_effect.py` | synthetic re-retrieval counts x rates = the expected pp; the 1.5 pp refusal |
| `test_tfrl_archive_parent_choice.py` | determinism; diversity penalty; class masking after two refused children; ties |
| `test_tfrl_ace_curator.py` | grow-only; verbatim predecessor; Jaccard 0.8 merge with provenance; script counters; prune; token truncation; decontamination refusals |
| `test_tfrl_contrast_tables.py` | counts-only output; "<3" suppression; a sha-stable re-run |
| `test_consumption_module_supply_columns.py` | E-S1: compile byte-identity of the all-off block; ceiling term; delivering arm last; twin without swap; refusal beside template / branch columns |
| `test_tfrl_material_resolver.py` | text-only (zero audio parts); receipts carry no text; the construction-role gate on the carrier roster |
| `test_stage3_algorithm_columns_label.py` | E-T5 |
| a 4-row dry run through `runtime.seal()` with the real parsers (memory `e1-seal-path-lesson-2026-10-09`) | `lock` request byte-identical to an UNARMED lock v2.2 run at the same ceiling, including the empty `ace-playbook-i0` route rendering zero bytes (proof P-ACE-0); every swap resolves its alternate (I7v); supply-variant receipt v3 |

## 7. The autonomous driver

The driver is `scripts/flights/tfrl/tfrl_loop_driver.py`, a deterministic CLI with three subcommands. It is
model-free; GPU steps go through the batch driver only.

| subcommand | steps |
| --- | --- |
| `close --iter t` | (1) verify the seal of iteration t (`batch_inspect.py`); (2) score the columns (`stage3_rollout_score.py --mode supply-variants`, one complete job per column, never sharded); (3) paired reads and offline delivery cross-fit (`slurp_nx_postproc_v4_apply.py`); (4) apply the 5.3 rule; (5) update `archive-i<t>.json` and `proposer-meta-i<t>.json`; (6) choose the parent (1.3); (7) build `tables-i<t+1>`; (8) run the ACE curator on the sealed reflector output of iteration t to produce `ace-playbook-i<t+1>`; (9) write the proposer and reflector packages for t+1 (from a derive script, `derive_slurp_tfrl_proposer_cells.py`, after the pattern of `scripts/flights/module/derive_e21_alloff_wirecheck_successors.py`: copy the parent fragment, change identities and pins only) |
| (GPU, batch driver) | the proposer + reflector cells (about 10 minutes) |
| `open --iter t+1` | (1) parse and validate the sealed proposer answers (3.4), with retries as registered follow-up cells; (2) build the candidate artefact (selection release, card release or knob set) model-free, under a `model-free-check` tool row; (3) run the offline re-retrieval prediction; (4) derive the iteration-(t+1) package (`derive_slurp_tfrl_iteration_cells.py` + `write_slurp_tfrl_iteration_registration.py`, NX R1 writer pattern); (5) run the fit measure (`nx_r1_fit_measure.py`-style); (6) run the dry run and gates; (7) draft the exposure rows |
| `status` | archive digest, curve so far, next human action |

**Human steps, which are signatures, not choices:**
- the coordinator countersigns the exposure rows (twice per iteration: proposer cells and column cell);
- the decision receipts are minted;
- the flip runs;
- the coordinator or owner starts `SAEA-Batch-Driver` from PowerShell. The session never launches flights itself
  (decision 77).

**How the loop stays autonomous in the paper's sense.** Every choice is a function of sealed bytes under the
preregistered `tfrl-loop-protocol-v1.json`: candidate, threshold, parent, acceptance, counters and stop. Its sha256 is
pinned in every iteration fragment, and `tfrl_loop_driver.py` refuses to run if the protocol hash changes. The
countersign attests conformance only. A human who declines to sign STOPs the loop, which is recorded as a stop. They
cannot substitute a candidate; the only exception is the labelled hand-author fallback, which needs an owner order.
One experiment is in flight at a time; at most one recovery re-registration per flight (study `CLAUDE.md`).

## 8. Risks and open questions

| id | risk / question | recommendation |
| --- | --- | --- |
| R1 | **The typed loop may stall at the 1.5 pp predicted bar.** S1's six supply arms predicted at most +0.20 pp at measured conversions (`docs/superpowers/specs/2026-10-09-slurp-nx-stage-s1-supply-round-design.md` section 2) | Keep the bar (decision 192). Allow the two retries. If no SF candidate clears, the iteration still flies `lock` / `aa` / `par` / `ace`, the typed point repeats, and delivery candidates are still read offline at 0 GPU. Owner choice in 263-A: a class with nothing above the bar may fly its top valid candidate as `claims_benefit: false` measurement (S1 option 1), never acceptable |
| R2 | **Token parity between prose and typed supply** | One `T_cap` for every arm, measured on the tokenizer (4.3). Report per-arm supplied tokens beside every delta. A typed edit that spends less is not topped up |
| R3 | **Identity re-pins when `runtime.py` or `rails/` change** (memories `artifact-identity-binds-implementation`, `repin-clobbers-foreign-preparation`) | Merge every engineering item before iteration 1 and freeze one flight commit for all five GPU cells. Iterations change only data releases and fragments, never code. A needed code fix stops the loop: one re-registration, then a 4-row proof |
| R4 | **The instrument's cross-flight bar for the DEV read** (rule 3: about 2.5 pp at n of about 1,000, in-chain replicate) | Read DEV same-flight with the in-flight `aa` (no offset; floor 1.49 / 0.65), claim `nominated`. Admission to lock v2.3 needs one delivered-path cell: cross-flight + replicate at 2.5 pp, or an owner ruling that a same-flight DEV read suffices for a supply-only state. Owner question |
| R5 | **Proposer decoding noise.** DET: np1 with cache off was 50/50 byte-identical; np4 is not (memory `det-np1-determinism-result-2026-09-27`) | Treat the sealed answer as the artefact. No re-sampling or best-of-N over proposals, since that would be credit from decoding noise (S3). Record the geometry. np1 would cost a serving swap and host-memory risk for 22-60 contacts; not worth it |
| R6 | **Selection-roster reuse.** Fold B is read three times, so the winner's curse applies (R1-i2 caveat) | Re-measure `par` in every flight; cross-fit thresholds; confirm on Fold A once, then DEV. Fold A prior exposure is disclosed |
| R7 | **What "the curve" is when a candidate is refused** | Plot the accepted-level series with flat steps, plus every flown child's own delta. Refusals are points, not gaps (5.4) |
| R8 | **ACE might be advantaged or handicapped by the script counters** | This is a declared departure. Also report the paper's literal form, model-judged counters, as an offline counterfactual ordering over the same items, never flown |
| R9 | **Decision 245 vs the ACE column** | 263-A rules ACE a non-delivering, never-lockable comparator |
| R10 | **Interference across scenarios (D7)** | Report per-scenario harm. The scope operator is the typed remedy; 18-row tables go with every verdict |

## 9. Build plan

Steps 1-9 are model-free; GPU steps come last. **[OWNER]** marks a gate.

1. **[OWNER]** Rule 263-A, including:
   - proposer option (i) under decision 255;
   - the ACE comparator exemption from decision 245;
   - R1's measurement option (yes or no);
   - R4's DEV admission path.
2. Write and pin `docs/readiness/2026-10-??-slurp-tfrl-loop-v1/tfrl-loop-protocol-v1.json`: rules 5.3, the parent
   choice, L_t, `T_cap`, the curator constants and the stop rule.
3. **E-S1**: the `supply` column kind + `supply_frame` + `alternates` passthrough in `rails/consumption_module.py` (S1
   spec section 1.3.1). **E-S2**: supply columns in `slurp_nx_solver_column_read.py` and `slurp_nx_postproc_v4_apply.py
   --column`.
4. **E-T1**: `rails/tfrl_typed_proposer.py` (render, schema, validator, prediction hook). **E-T2**:
   `rails/tfrl_ace_material.py` + the curator + the `ace-playbook` store releases (`i0` empty). Register the two
   program ids, the two response formats and the resolver dispatch in `core/flight/runtime.py`.
5. **E-T3**: `scripts/analysis/tfrl_contrast_tables.py` and the cross-fitted delivery-family threshold fitter (from
   `slurp_nx_postproc_v4_search.py`). **E-T4**: archive / meta / parent modules under `analysis/sealed_credit/` (reuse
   `accept.py`, `policy_space.py`). **E-T5**: the label `columns` key and the ACE citation update in
   `core/stage3_algorithms.py`. **E-T6**: multi-store `release_swaps` in `rails/supply_variants.py` (receipt v5,
   I7v per store), and the iteration-1 view builders and coverage pre-read of section 2.1.
6. Build `scripts/flights/tfrl/`: the loop driver, derive and registration writers, carrier-roster builder, mint, repin
   and flip scripts, and the batch chain. Write the tests of section 6. Pass all gates. Merge, then freeze the flight
   commit (R3).
7. Iteration-1 tables from the sealed VER-1a sample 0 (0 GPU), plus the section-2.1 coverage pre-read for the
   proposed (a)+(b) composite. It must clear +1.5 pp predicted before the column is packaged. Package the proposer and reflector cells i1 and draft
   their exposure rows.
8. **[OWNER/coordinator signature]** Countersign; then mint, flip, pin refresh, flip, gates and queue.
9. **GPU**: proposer + reflector i1 (about 0.1 h). Then `open --iter 1`, the candidate artefacts, the predictions, the
   package, the 4-row dry run (P-ACE-0, I7, I7v) and the gates.
10. **[signature]** Then **GPU**: the iteration-1 column (about 1.43 h). Then `close --iter 1` at 0 GPU.
11. Repeat steps 9-10 for iterations 2 and 3 (about 1.81 h each, including the proposer).
12. **[signature]** Then **GPU**: the Fold A confirmation (about 1.43 h). Read under the fixed rules.
13. **[signature]** Then **GPU**: the DEV-2000-ADDED composed read (about 1.32 h). Then the results note with the
    curve, the ACE comparison, the per-stratum tables and the published SOTA rows beside the repo numbers (decision
    252 clause 3).
14. **[OWNER]** Rule the lock-admission path (R4) for any nominated typed state.
