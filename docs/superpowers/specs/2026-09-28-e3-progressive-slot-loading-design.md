# E3: progressive slot loading at the Solver -- design

Author: design agent (Claude Opus 5.5), 2026-09-28, branch `fable/e3design` (base `cfa85e05`). Status: DESIGN,
no code, nothing registered. Authority: owner decision 180 as briefed by the coordinator (not yet recorded in
`docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md` at `cfa85e05`). Zero model, server,
tokenizer, scorer and GPU contacts. Every number is a development number on TRAIN Fold A (decisions 28, 86).

## 1. Mechanism and node-gain claim

**Today** the Solver receives every candidate-bound slot card (12.9 per row, about 5,400 tokens, 91.1 %
serving neither delivered nor gold types) and decides intent, types, values and extents in one contact. The
knowledge is present but unused: the type card was delivered on 644 of 660 error items; 157 missed values are
in TRAIN's list; M1 already printed the gold value for 90 of 173 MISSING items (W5); W4 delivered the complete
closed-type lists in card form and closed-type FN stayed 46 -> 46 (W4 read, section 6).

**E3** splits the slot decision into two contacts:

1. **Stage 1, slot-types node.** From the speech, the Perception candidates with their distinctions (the
   row's speech note) and a type index grouped by candidate intent, it decides which slot TYPES are spoken.
   The empty list is legal. No values, no intent.
2. **Stage 2, the Solver (answer authority).** Only the chosen types get their full card from
   `slot-contracts-w4-v1` (K2 closed values, K3 do-not-tag scope, K4 span extent); other candidate-bound
   types stay index lines. The Solver decides intent and entities; its response is delivered (I7 unchanged).

**Node-gain claim (USE plane, Solver node).** Stage 1 buys precision through an explicit presence decision
(SPURIOUS: 253 items, isolated 8.46 pp). Stage 2 buys value and extent binding for the opened types
(closed-type MISSING/WRONG-VALUE, section 2; BOUNDARY 75 items, 2.88 pp). Perception, boundary and exemplar
channels do not move; intent is the guard. Era-A precedent: KC-S1b, a separate slot contact with a per-intent
schema, +8.55 SLU against an equal-contact control at +0.09; KV-2 vocabulary cards +1.71 over their twin.

## 2. Closed types

The closed-type rule is LOO value coverage >= 0.90 over the R01-excluded pool (W4 tables). The rule uses no
Fold A byte, and it yields five types:

| type | values listed (W4) | LOO | AGREE FN (omit / wrong / swap) | error-source items | isolated pp | W4 FN, A/A -> arm |
| --- | ---: | ---: | --- | --- | ---: | --- |
| `order_type` | 9 | 0.907 | 18 (14 / 2 / 2) | MISSING 14, SPURIOUS 4, WRONG-TYPE 2, BOUNDARY 1, WRONG-VALUE 1 | 1.24 | 20 -> 19 |
| `transport_type` | 8 | 0.986 | 15 (15 / 0 / 0) | MISSING 14, WRONG-TYPE 1 | 0.94 | 18 -> 18 |
| `timeofday` | 11 | 0.984 | 4 (3 / 1 / 0) | MISSING 3, SPURIOUS 3, BOUNDARY 1 | 0.30 | 4 -> 5 |
| `meal_type` | 3 | 1.000 | 4 (3 / 1 / 0) | MISSING 3, NEAR 1, SPURIOUS 1 | 0.25 | 4 -> 4 |
| `transport_agency` | 3 | 0.967 | 0 (FP 1) | none | -- | 0 -> 0 |

**Chosen:** the four types that carry mass, `order_type`, `transport_type`, `timeofday` and `meal_type`.
Together they hold 41 FN and 34 of the 173 MISSING items. `transport_agency` rides along because its W4 card
already carries its list. The set is fixed by the rule and not by Fold A mass, so `tuning_roster` can be
`"none"`.

**Ceiling.** The 33 closed-type omissions whose value is listed give +2.00 pp SLU (span +2.41) on 32 rows.
The semi-closed extension (`house_place`'s 17-value list, `date`, `time`) is deferred.

## 3. Protocol, tokens, contacts

**Stage 1** is a new optional role kind `slot_types` under module key `native_episode.progressive_slots` =
`{schema, failure_policy: "full-card-fallback", max_types: 6}` (precedent: E18's optional `acquisition`
role), phase `slot-types` after `perception` in program
`phase-native-candidates-slot-types-review-revise-v1` (ceiling 12).

- **Format** `slurp-slot-types-v1`: `{"types":[...]}`, legal names, deduplicated, at most 6, possibly empty.
- **Request:** byte-identical to the AGREE Solver request up to the slot-card block (system, task context,
  speech packet, candidates with distinctions, boundary entries, 20 exemplars); then the type index (each
  candidate-bound type: name plus its v2 card's first extraction-cue sentence verbatim; no values, no
  formats); then `probes/slurp_native_role_slot_types_v1.txt` ("list the types whose value is spoken; empty
  when none; no values; no intent").
- **Runs once** before the first Solver visit; revisions reuse its list. An unparseable or illegal answer
  falls back: stage 2 renders the AGREE block byte-identically, counted.
- **Custody:** sealed as its own contact, never an agent state in Reviewer/Planner history (the NCP
  cleaning-contact precedent).

**Stage 2:** `candidate_supply.solver` gains `type_state_phase: "slot-types"` and render policy
`expand-chosen-index-rest-v1`; the instruction `probes/slurp_native_role_solver_progressive_v1.txt` is
solver v2 plus two sentences: the stage-1 list is a loading decision, not a whitelist (index types stay
legal); for an expanded closed type use a listed value's spoken form within its scope and extent.

**Tokens (projected; `native_contact_fit` measures before registration).** Assumptions: AGREE slot block
~5,440 tokens (27,900 characters at 5.13 per token, audit 3.1); 12 index lines x ~22 tokens; ~1 expanded W4
card of ~400 tokens (0.95 predicted entities per row); ~80 tokens stage-2 echo, ~120 stage-1 instruction.

| quantity | AGREE (wave A/A, measured) | W1 (measured) | E3 (projected) |
| --- | ---: | ---: | ---: |
| Solver prompt per contact | 10,228 | 9,103 | ~5,530 |
| Reviewer / Planner per contact | 10,204 / 10,339 | 9,079 / 9,217 | ~5,430 / ~5,560 |
| stage-1 prompt per row | -- | -- | ~5,170 |
| prompt tokens per row | 35,061 | 31,682 (-3,380) | ~25,700 (-9,400 vs AGREE, -6,000 vs W1) |
| completion per row | 245.9 | 249.0 | ~276 (+~30 from stage 1) |
| contacts per 1,080 rows | 4,393 | 4,401 | ~5,473 (+1,080, +24.6 %) |
| speech-audio seconds | 12,557 | 12,571 | ~15,642 (+3,084.5) |

Reviewer and Planner render the stage-2 block (keeps W1's prefix-cache property; Q4). **Prefill** depends on
block order: with the slot block last, stage 1 prefills the AGREE Solver prefix minus ~4,700 and stage 2
~800, about -3,500 per row (from 8,762); worst case +5,200. Task 0 settles it. **Contacts:** ceiling 11 -> 12,
`planned_model_calls` 12,960; GPU-h is decode-bound, projected within +-15 % of 1.74.

## 4. Measurement design

**Decision: E3 is a program change, read full-system against an in-chain A/A; it cannot be a supply
variant.** An arm is one contact at a `max_iterations`-1 Solver with the same instruction, differing only by a
knob tail or release swap (instrument spec section 2); stage 1 adds a contact, a format and a template, and
instrument section 5 sends program changes straight to the cross-flight read. The alternative -- stage 2's
vocabulary as a release swap of a single-stage Solver -- is **W4 itself**, already re-registered as the
instrument's first cell (content in monolithic form): E3's content control, not duplicated.

**Cell E3** (`SAEA-SLURP-STAGE3-E3-PROGSLOT-FOLD-A-V1`):

- **base:** the AGREE arm bytes (uncited Solver);
- **replicate:** in-chain A/A `SAEA-SLURP-STAGE3-E3-AA-FOLD-A-V1`, an AGREE replicate in the same chain;
- **rows:** TRAIN Fold A, 1,080;
- **stage3_measurement:** `measurement_design` `cross-flight-with-in-chain-replicate`, `admission`
  `no-harm`, `expected_effect_pp` 0.0, `claims_benefit` false, `harm_margin_pp_by_metric` `{slu_f1: 1.2485
  (primary), intent_accuracy: 0.9943 (guard)}`;
- **rosters:** `tuning_roster` `"none"`, `read_roster` `"SLURP-EVO-FOLD-A-V2"` (split `61b0f062...`);
- **stage3_algorithm:** `none`.

**Why 0.0.** The ceiling is 2.00 pp. The measured conversion rates give:

| rate | source | E3 projection |
| --- | --- | ---: |
| 0.2471 | M1 delivered-filler conversion | 0.49 pp |
| 0.0044-0.0073 pp per item | M4b analogue, x 41 closed FN | 0.18-0.30 pp |
| 0 | W4's measured closed-type conversion in card form (46 -> 46) | 0 |

All three sit below the 2.5 pp bar and the 1.2485 floor. Stage 1's precision claim has no measured
conversion either.

**Pre-registered mechanism reads (descriptive, W4 section 6 form):** closed-type TP/FP/FN; entity classes;
K2/K3/K4 classes; stage-1 type recall and precision against gold types (offline); empty-list rate on the 414
gold-empty rows; stage-2 types outside the stage-1 list; fallback count; the frontier row.

**E3b (conditional, after E3 reads no-harm).** A `same-flight-supply-variant` cell inside the E3 program:

- **arms at the stage-2 visit:** A (delivering) uses the W4 release; B is a `release_swap` to
  `slot-contracts-v2`, the same progressive form without the new content; plus a twin of A;
- **settings:** `arm_visits: "first"`, ceiling 14, claim `nominated`.

E3b reads content under progressive form at about the 0.7 pp floor. Beside the W4 column (content under
monolithic form), it isolates the consumption thesis.

## 5. Hazards

**Form change** (synthesis section 2.2). Every harm measured outside the band changed what a node reads
without adding row-matched evidence, removed options, or broke the output contract. E3 touches each pattern:

| E3 element | the harm it echoes |
| --- | --- |
| index lines | IDXT: terse lines misled, -9.97 on the form twin |
| expanding only the chosen types | KU-S4N narrowing, -11.74 |
| re-rendering | A18, -6.06 |
| a new response format | EFF-1, 137 unparseable rows |

Mitigations: index lines quote the card's own cue; stage 1 never restricts legality; the empty set stays
legal; `full-card-fallback`; the four-row smoke asserts parse and fit. W4's MISSING +14 warns that scope text
raises omissions, so the mechanism read reports MISSING first.

**Review loop.**

- A revision visit must re-resolve the byte-identical stage-2 supply (the B1 phase-supply revisit refusal)
  and must never re-run stage 1.
- The Reviewer template still orders the retired task-contract tool; E3 leaves the template untouched and
  reports it.
- Declare `finite_completion_policy` `"deliver-latest-or-abstain"` and `react_exhaustion_policy`
  `"continue-without-answer"`.

**Throughput.** Contacts +24.6 %, and stage 2 waits on stage 1 within the row. `rails/dispatch_slot_fill.py`
is serving-slot scheduling (recall prefetch, role-input offload, gc freeze), not SLURP slot filling; its
`recall_prefetch` stays valid (the exemplar recall is stage-1 independent) and `role_input_offload` must cover
the new role's builder. Cap stage-1 completion at 64 tokens (E39 per-role cap).

**Circularity.** No knob is fitted to Fold A, but the design is motivated by Fold A error tables (Q3).

## 6. Implementation plan

(ID) marks an identity-bound file: its hash enters `sources.implementation`, or the instrument spec's merge
set B treats it so. Such files land only at a re-pin point the coordinator names, after COMP-1's resume
seals.

**Merge set A (model-free, now).**

1. **Task 0:** read the sealed AGREE Solver request block order from trace custody (hashes and offsets only)
   to settle the prefill case; count index-line and expanded-card characters from the released snapshots.
2. **Format** `slurp-slot-types-v1` in `rails/slurp_candidate_contracts.py`, registered in
   `rails/controllers.py::register_response_formats_v1`; `tests/unit/test_slot_types_format.py`.
3. **Templates** `configs/probes/slurp_native_role_slot_types_v1.txt`,
   `slurp_native_role_solver_progressive_v1.txt`.
4. **Program** `configs/policy/phase-native-candidates-slot-types-review-revise-v1.json` (ceiling 12),
   registered in `rails/controllers.py::_PROGRAM_CONFIG_FILENAMES`.
5. **Read** `scripts/analysis/slurp_e3_mechanism_read.py`, reusing W4's `entity_items` unmodified.

**Merge set B (identity-bound, at the re-pin point).**

6. **Config.** In `rails/native_episode_config.py` (ID): the optional `slot_types` role and the
   `progressive_slots` module, both-or-neither, with the ceiling +1 once. Refuse it beside `samples >= 2`,
   role tools or `supply_variants`, until E3b's ruling.
7. **Runner.** In `rails/runner.py` (ID): the stage-1 contact before the first Solver visit, its seal
   record, fallback, revision reuse, exclusion from history, and `role_input_offload` coverage.
8. **Supply.** In `rails/candidate_semantic_supply.py` (ID): `type_state_phase` and
   `expand-chosen-index-rest-v1`. `rails/kb_policy.py` stays untouched (its Stage-2A digest lock).
9. **Seal.** In `core/flight/runtime.py` (ID), `core/bundle/outputs.py` and
   `rails/native_episode_receipt.py`: a new invariant I7s that binds the stage-1 contact to the row and the
   stage-2 expanded ids to its parsed list.
10. **Registration** (coordinator): E3, smoke-4 and A/A fragments; readiness package with
    `registered-facts-v1.json` `stage3_measurement`; measured `native_contact_fit` at ceiling 12; four-row
    dry run; exposure-ledger rows before contact.

**Tests:** `tests/unit/test_progressive_slots_config.py` (ceiling, refusals);
`tests/unit/test_progressive_slot_supply.py` (expanded = chosen intersect bound; index covers the rest;
fallback byte-equal to the AGREE block; revisit byte-identical); an AT6-style seal-path test; a no-arming test
that every committed config composes to its prior hash.

**Gates after each task.** `pytest`, `engineering_base_check.py` (the role lives in the shared controller;
no `rails/probes/` module; every policy id resolves), `stage3_effect_floor_check.py`,
`flight_registration_check.py`, `stage3_algorithm_label_check.py`, `finite_completion_policy_check.py`,
`results_ledger_check.py`, `handoff_freshness_check.py`.

## 7. Open questions for the coordinator

- **Q1.** 34 of the 41 closed-type FN are omissions, which are stage-1 failures. Should the four closed lists
  (about 70 tokens) also sit in the stage-1 index as presence cues? Recommendation: no for E3 (it keeps the
  owner's split); carry it as an E3b arm if E3 reads no-harm.
- **Q2.** Base AGREE, uncited, or COMP-1, cited, if COMP-1 is admitted before E3 registers? The cited
  contract would apply to stage 2 only.
- **Q3.** Read roster: Fold A (`tuning_roster "none"`, with the Fold-A-motivated design stated) or a roster
  free of design-level circularity (DEV-2000-ADDED, or Fold B once it has an A/A)?
- **Q4.** Should Reviewer and Planner receive the stage-2 rendering (recommended: prefix cache, W1
  precedent) or the full AGREE block?
- **Q5.** E3b: accept a `release_swap` on a candidate-supply store keyed on stage-1 state? And may a variant
  flight's delivered column also carry E3's no-harm read (one flight saved; the gate allows one design per
  run id)?
- **Q6.** Record decision 180 in the decisions file before registration.
