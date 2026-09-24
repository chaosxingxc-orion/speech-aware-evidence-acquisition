# Readiness package: SAEA-SLURP-STAGE3-GEPA-R01-V1

Status: **HELD**. This package registers the engineering for Stage-3 layer A's **GEPA arm** -- it
does not authorize a flight, a readiness flip, or an admission entry. Design note:
`docs/superpowers/specs/2026-09-24-slurp-stage3-gepa-arm-design.md`. Parent specification:
`docs/superpowers/specs/2026-09-22-stage3-tfrl-base-loop-engineering.md`, section "The GEPA and ACE
arms".

Stage-3 algorithm (owner decision 101): **`gepa-reflective-pareto-v1`** (GEPA, arXiv:2507.19457),
operators `credit_assignment` + `update`. Declared as `stage3_algorithm` in
`configs/experiment/slurp-native-stage3-gepa-r01-v1.json` and checked by
`scripts/checks/stage3_algorithm_label_check.py`.

## What this cell is

One reflective contact per **(scenario, node) group**. The contact is shown that scenario's
worst-outcome and best-outcome ROLL-1 rows -- disjoint halves of the ranked list, at most 6 each --
with their whole sealed trajectories and construction gold, plus the node's **current released
delta statements** for that scenario, and is asked to revise and extend that node's guidance in one
to five `NODE / DELTA-KIND / TARGET / STATEMENT` blocks, all naming that group's node.

ADV-1 assigns credit per ROW and states what made one row's best sample better than its worst. GEPA
assigns credit per SCENARIO and mutates the instruction text. That is the whole difference, and it
is the difference the CELL-1 read asked for: NEUTRAL overall (SLU -0.48 [-2.18, +1.24]) with large
and opposite per-scenario effects (audio +8.9, weather +8.3 against general -12.4, alarm -6.8).

| | value |
| --- | --- |
| groups = contacts | **68** (17 scenarios x 4 nodes; `music` has no eligible row) |
| distinct GROUP rows whose gold is shown | 173 (all R01C construction rows, 173 of ADV-1's own 225) |
| rows per group | 12 (44 groups), 11 (8), 10 (4), 6 (4), 2 (4), 1 (4) |
| current delta statements per group | 0 (8 groups) .. 12 (10 groups) |
| carriers drawn from the group / topped up from R01C | 63 / 5 |
| prompt size, rendered offline | min 2,477 / median 13,309 / max 16,281 CHARACTERS |
| GPU-h ceiling (point estimate ~0.2) | 1.0 |

## Engineering delivered here

- `src/speech_aware_evidence_acquisition/rails/stage3_gepa.py`: the closed-form proposal parser
  (`parse_gepa_proposal`, node-fixed, total, never raises), the renderers
  (`render_gepa_instruction`, `render_group_row_block`, `render_current_deltas`) and the registered
  response format `stage3-gepa-proposal-v1`.
- `src/speech_aware_evidence_acquisition/rails/stage3_gepa_material.py`: the third
  `construction_material_resolver` implementation. It **reuses** ADV-1's four row renderers, its
  sealed-custody reader and its per-sample digest verification unchanged, and verifies every pin it
  is handed (the groups artifact, `pairs.json`, the released authored-deltas document) before it
  renders a single contact.
- `scripts/build_slurp_stage3_gepa_groups.py`: the model-free group builder (ranking, disjoint
  halves, carrier assignment with R01C top-up, the per-(scenario, node) current-delta slice).
- `scripts/build_slurp_stage3_gepa_delta_rows.py`: the model-free GEPA curator, a thin sibling of
  `scripts/build_slurp_stage3_delta_store.py` that **imports** its `curate`, its dedup rule, its
  facet rule, its containment rule and its document writers rather than restating them.
- `configs/policy/phase-stage3-gepa-v1.json`, `configs/probes/slurp_stage3_gepa_v1.txt`,
  `configs/probes/slurp_stage3_gepa_system_v1.txt`, four cell fragments, the campaign plan, and the
  two construction-role roster receipts.
- Runbooks: `gepa_prepare.sh` (+ `gepa_prepare_steps.py`), `gepa_repin_arm.sh`,
  `gepa_repin_smoke.sh`, `gepa_flip_both.sh`, `batch_chain_gepa.sh`,
  `gepa_render_proposal_outputs.py`, `gepa_to_deltas.sh`, `gepa_dry_run.py`.
- Tests: `tests/unit/test_stage3_gepa.py` (29).

## The one shared file that moved, and the re-pin it obliges

`core/flight/runtime.py` gains two imports, one dispatch branch in `_default_construction_material`
keyed on the composed `policy`, `GepaMaterial` in the material `isinstance` tuple, one reader branch
in `_construction_phase_material` and one dispatch-kind label. All additive: every pre-existing arm
and program takes exactly the path it took before.

That file is hashed into **every** prepared phase-supply artifact's identity
(`FlightRuntime._phase_seed_inputs` `sources.implementation.runtime`), so this commit makes every
artifact prepared before it stale -- the CELL-1 family's included. The coordinator's flip step
re-pins them in one cycle; **`--allow-output-change` must never be passed**, and their `output` is
expected to reproduce byte for byte because no selection path moved.
`FlightRuntime.verify_prepared_artifacts` reports a stale artifact read-only before a flight opens
anything, so the failure mode is a refusal, not a wrong flight. The design note's section 9 records
why the alternative (hiding the dispatch in a rails module) was rejected.

## Registered documents

| document | what it pins |
| --- | --- |
| `generation-plan-registered-v1.json` | the 68-group arm |
| `fit-plan-registered-v1.json` | its fit identity (expected to be charged zero) |
| `smoke-generation-plan-registered-v1.json` | the four-row form smoke (one carrier per NODE) |
| `smoke-fit-plan-registered-v1.json` | the smoke's fit identity |
| `protocol-registered-v1.json` | the contact form, the leakage rule and the decision rule |
| `analysis-recipe-v1.json` | the six structural reads and where the EFFECT is read instead |
| `cell-1-gepa-diff-plan-v1.md` | what CELL-1-GEPA changes against CELL-1 (a diff plan, not fragments) |
| `stage3-deltas-gepa-v1-release-registration.template.json` | the store release, materialised with real digests by the runbook |
| `stage3-deltas-gepa-twin-v1-release-registration.template.json` | its derangement twin |

Preregistration: `docs/readiness/2026-09-24-slurp-stage3-gepa-r01-v1-preregistration.md`.
DRAFT exposure rows: the "SLURP Stage-3 GEPA arm" section at the end of `docs/exposure-ledger.md`
(four rows, none countersigned, all four cells `held`).

## Offline proofs run before this registration (zero contacts of any kind)

1. `tests/unit/test_stage3_gepa.py` -- 29 tests: the parser's totality and its node invariant, the
   registered program/controller/format, the renderer's placeholder refusal, the group builder's
   ranking / disjointness / carrier top-up / delta slice, the material's pin verification and
   custody-drift refusal, the resolver's program-keyed dispatch, the curation row shape and the
   REVISION absorption, and the existing twin builder's two invariants on a GEPA document.
2. `scripts/flights/batch/gepa_dry_run.py` -- ONE contact rendered from the real sealed ROLL-1
   custody, the real `pairs.json`, the real released deltas and the real governed gold, then run
   through the runtime's own message list, the client's reverse parser, the D2 field-set equality
   and the transport's own text-only construction gate. PASSED, zero problems.
3. The prompt-size scan over all 68 contacts (characters only; the FIT pass measures tokens).

## The four CELL-1 launch-defect lessons

| lesson | applies here? |
| --- | --- |
| shared readers | not reachable: no knowledge store, no live Perception state read; the candidate ids come from `pairs.json`'s sealed trajectory block |
| fit identities | not for this cell (it pins no prepared artifact); the obligation it creates for the CELL-1 family is above |
| empty selections | handled at the TEMPLATE: a group whose node carries no statement is told so in words; there is no `acquire` transition in a one-contact program |
| seeding once | not reachable: no store route, no phase supply, no bootstrap |

## Sequence for the coordinator

`merge` -> `mint` `coordination/slurp-stage3-delta-cell-gepa-r01-v1/root-admission-v1.json`
(decision id `slurp-stage3-gepa-r01-admission-v1`) -> `flip` with `gepa_flip_both.sh` (and re-pin
the CELL-1 family for the runtime change) -> `chain` with `batch_chain_gepa.sh` (smoke, then the
68-group arm) -> `curate` + `release` with `gepa_to_deltas.sh` -> register and fly **CELL-1-GEPA**
from `cell-1-gepa-diff-plan-v1.md`.

## Two populations: the flight's carriers and the store's group rows (appended 2026-09-24)

Appended after the first release attempt of `gepa_to_deltas.sh` was refused at step E. Nothing
above is rewritten; this section states the distinction the refusal exposed.

| | roster | rows | split identity | what pins it |
| --- | --- | --- | --- | --- |
| **flight population** | `docs/receipts/rosters/slurp-stage3-gepa-r01c-carriers-v1.json` | 68 | `86da42e2...` | `configs/experiment/slurp-native-stage3-gepa-r01-v1.json` `population`; the exposure gate |
| **store source population** | `docs/receipts/rosters/slurp-stage3-gepa-r01c-groups-v1.json` | 173 | `0d020435...` | the two release registrations' `permitted_roster` **and** `source_split_identity_hash` |

The flight makes one contact per CARRIER row, so the carriers are the flown identities. The
material a contact is shown is its GROUP's rows -- their sealed trajectories and their construction
gold -- so the rows an authored GEPA delta may cite are the union of the groups' `row_sample_ids`.
Five carriers are topped up from R01C and are shown in no group, so the two rosters are genuinely
different populations, not a relabelling of one.

`core.semantic_knowledge_preparation.prepare_semantic_knowledge_store` verifies a registration's
`permitted_roster` through `core.roster.read_roster` (a full `saea-roster-receipt-v1`, construction
role, right carrier) and then requires `permitted.split_identity_hash ==
registration.source_split_identity_hash` and `permitted.sample_ids` inside the construction scope.
The first attempt supplied a permitted roster synthesised inside
`gepa_render_proposal_outputs.py` with its `split_identity_hash` deliberately removed, against the
CARRIERS identity, and was refused twice over:

```
core.roster.RosterError: roster receipt split_identity_hash must be non-empty text
core.semantic_knowledge_preparation.SemanticKnowledgePreparationError:
    permitted_roster is not a verified roster
```

The fix is the ADV-1 discipline: the GROUP-ROWS roster is minted once as a committed, pure
selection of R01C (`scripts/flights/batch/gepa_prepare_steps.py groups-roster`), the renderer
copies that committed receipt byte for byte into `prepared/SAEA-SLURP-STAGE3-DELTAS-GEPA-V1/
permitted-roster.json` (cross-checking its items against the groups artifact), and the runbook
reads `source_split_identity_hash` out of that receipt rather than out of the experiment fragment.

## Ruling: the store's permitted roster is the ADV-1 disagreeing receipt (appended 2026-09-24)

Appended after the release step was refused a second time. Nothing above is rewritten; the section
above named two populations and made the 173 group rows the store's permitted roster, and this
section records the coordinator's ruling that replaces that last step.

With the group rows as the permitted roster, `core.driver prepare-semantic-knowledge` refused:

```
SemanticKnowledgePreparationError: authored delta source_sample_ids must be a subset of the
    permitted construction roster
```

The curated GEPA store is append-only over the released `stage3-deltas-v1r` (decision 83): 448 rows
= 248 new GEPA rows + 200 retained iteration-1 rows. Those 448 rows cite 201 distinct sample ids and
28 of them -- cited by 42 retained rows and by no new GEPA row -- lie outside the 173 group rows.
All 201 lie inside the committed ADV-1 disagreeing roster. The ruling is therefore the
precedent-exact one: the STORE's permitted roster is that ADV-1 receipt, exactly as
`stage3-deltas-v1r` and `stage3-deltas-v2` pin it, so `stage3-deltas-gepa-v1` shares its source
identity with the CELL-1 / CELL-2 stores rather than inventing a third one.

| | roster | rows | split identity | what pins it |
| --- | --- | --- | --- | --- |
| **flight population** | `docs/receipts/rosters/slurp-stage3-gepa-r01c-carriers-v1.json` | 68 | `86da42e2...` | `configs/experiment/slurp-native-stage3-gepa-r01-v1.json` `population`; the exposure gate |
| **contact material** | `docs/receipts/rosters/slurp-stage3-gepa-r01c-groups-v1.json` | 173 | `0d020435...` | committed as the record of what the contact was shown; printed by the runbook; a strict subset of the permitted roster |
| **store permitted roster** | `docs/receipts/rosters/slurp-stage3-advantage-r01c-disagreeing-v1.json` | 225 | `7c603857...` | the two release registrations' `permitted_roster` **and** `source_split_identity_hash`, exactly as v1r / v2 pin them |

Neither the carriers identity nor the groups identity is ever written into the store.
`scripts/flights/batch/gepa_render_proposal_outputs.py` still copies the permitted receipt byte for
byte, but its population check is now CONTAINMENT rather than equality: every group row must be
inside the receipt, so no GEPA-authored citation can escape it. The carriers receipt still fails
that check, and so does any receipt one group row short.
