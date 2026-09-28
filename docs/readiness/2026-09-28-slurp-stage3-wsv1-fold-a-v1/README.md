# Cell W-SV-1: the first same-flight supply-variant cell (owner decision 172)

Registered before contact 2026-09-28 at study commit `6cb6086de`; both cells **held**.
Nothing here authorises a flight, a flip or an admission entry. Development numbers only (owner decisions 28 and 86).
This README replaces the 2026-09-28 finding note (registration BLOCKED on an uncited 13-ceiling "first" program);
the fragment `configs/policy/phase-native-candidates-review-revise-variants3first-v1.json` has since landed on master and is registered in
`src/speech_aware_evidence_acquisition/rails/controllers.py`.

**What W-SV-1 is.** The retained AGREE arm (`SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1`, official SLU-F1 65.16 / intent 85.83 on TRAIN Fold A)
with exactly two registered changes:

1. **The program switch -- the ONLY base change besides the variants block.** `policy`
   `phase-native-candidates-review-revise-v1` (ceiling 11) -> `phase-native-candidates-review-revise-variants3first-v1` (ceiling 13 = 11 + (K - 1),
   K = 3 counting the twin). The two fragments differ only in `program_id` and `max_contacts`; the Solver stays
   UNCITED (`response_format_id` null). The ruling states that the delivering arm A's request bytes must equal the
   AGREE arm's; proven below the way the knowledge wave's shared A/A was proven, they do so **only modulo two
   program-identity fields** the model-visible request text carries: the program id (with the node's global
   invocation index) inside every quoted prior contact id, and `remaining_model_contacts` in the task-state block
   (13 minus spent against 11 minus spent, so +2 on every contact of the episode, Perception included). No
   configuration of this program can remove them; an exact AGREE-byte A needs an engineering change (not rendering
   the program id / the ceiling into the prompt), which is the coordinator's call. The within-flight read is
   unaffected: A, B and T share the same program and the same state, and T's wire bytes equal A's (AT2).
2. **The variants block** `native_episode.roles.solver.supply_variants`, `arm_visits: "first"` (arms fan out only
   at the first Solver visit; a revisit contacts A alone; B and T never reach the Reviewer, the Planner or the
   delivered text):

| arm | order | role | overrides | max_supplied_items |
| --- | ---: | --- | --- | ---: |
| `b-exk30` | 0 | knob-tail (B) | `fuse_coverage.c` 30, `fuse_coverage.m` 30, `fuse_coverage.top_l` 30, `k` 30 | 68 |
| `t-twin` | 1 | twin of `a-base` (T) | none | 58 |
| `a-base` | 2 | delivering (A) | none | 58 |

`fit_estimate`: slot 24576, completion ceiling 512, base prompt 10266,
80 tokens per supplied item -- all MEASURED on the sealed AGREE arm (below).
B is the VAR-1 `exk30` construction: the knob path `knowledge_stores.train-exemplars.phase_supply.solver.{k, fuse_coverage.m, fuse_coverage.c, fuse_coverage.top_l}`
20 -> 30, exactly the leaves `configs/baseline/slurp-native-stage3-var1-ex-k30-r01c-baseline-v1.json` moved
(`scripts/flights/batch/var1_repin_exk30.sh`, `docs/readiness/2026-09-24-slurp-stage3-var1-v1`).

**Estimand and claim.** The Solver-local answer under each supply at the FIRST Solver visit, never the delivered
full-system answer. `measurement_design` `same-flight-supply-variant`; claim ceiling **`nominated`** (Q6 ruling:
a nomination only sends the construction to a full-system read against an in-chain A/A).

**Primary metric.** Official pooled SLU-F1 of the column, intent accuracy the guard (decision 115's shape: the
exemplar supply carries slot annotations, so the knob is not an intent-only mechanism).

**Declared expectation and the bar.** From the measured analogue only (row 139): VAR-1's exk30 arm against the
in-chain request-identical replicate PLANR moved SLU-F1 by **+0.09 pp CI95 [-1.47, +1.60]**
(docs/results/2026-09-27-slurp-mechanism-synthesis/mechanism-table.json (row C7: 'vs PLANR: ... K30 +0.09 [-1.47, +1.60]') from docs/results/2026-09-25-slurp-var1-complete-evidence.md (exk30 vs plan +1.95 [0.48, 3.45]; planr vs plan +1.87 [0.41, 3.36]; so exk30 vs the in-chain replicate PLANR is +0.09)). `expected_effect_pp` 0.09. The design's provisional floor
(`scripts/checks/stage3_effect_floor_check.py`, design `same-flight-supply-variant`, ROLL-AA anchor) is
**0.735 x sqrt(200 / 1080) = 0.3163 pp SLU** (0.0000 pp intent) at n = 1080. The expectation sits
BELOW it, so `claims_benefit` is **false** (a benefit declaration would be refused, `effect-below-floor`,
blocking). The read's bar is the **twin null** measured in this flight -- |T minus A offset| + its CI95
half-width, per metric -- reported beside the provisional floor; this cell is also the instrument's first
measurement of that null. `tuning_roster` `none`, `read_roster` `SLURP-EVO-FOLD-A-V2`; `aa_arm_id` `t-twin`;
`variant_cost` +2 Solver contacts per row, +6169.057 speech seconds per flight
(2 x the Fold A total 3084.5284375 s).

## The decision rule (fixed here)

SAME-FLIGHT COLUMN READ (owner decision 172; claim ceiling 'nominated', Q6 ruling). Every column -- a-base (the delivering arm's first-visit column), b-exk30 and t-twin -- is rendered from the sealed first Solver visit through the delivered row's normaliser and projection (the render refuses on any acceptance-test AT1 failure) and scored ONCE with slurp-slu-official-train through core.scoring_batch.score_complete_derived_copy; each contrast is a paired ROW bootstrap (cluster key sample_id, 10,000 draws, seed 20260928). (1) THE TWIN NULL: t-twin minus a-base on official pooled SLU-F1 (primary) and intent accuracy (guard); the bar on each metric is |twin offset| + the twin's CI95 half-width (the same law as the cross-flight in-chain A/A), reported beside the provisional floor 0.3163 pp SLU / 0.0000 pp intent (scripts/checks/stage3_effect_floor_check.py, design same-flight-supply-variant: 0.735 x sqrt(200 / 1080)). (2) THE KNOB: b-exk30 minus a-base. NOMINATED iff the SLU-F1 CI95 lower bound is above zero AND the SLU-F1 point delta exceeds the twin bar AND the intent CI95 lower bound is not below minus the twin's intent bar. SOLVER-LOCAL HARM iff the SLU-F1 (or intent) CI95 upper bound is below zero and the point delta's magnitude exceeds that metric's twin bar. Otherwise NOT NOMINATED (within the twin null). A nomination claims nothing at system level: it only sends the exk30 construction to a full-system read against an in-chain A/A. The utterance-level number is reported beside the row-level one and never gates (Q4). Every verdict carries the per-scenario table in both weightings.

## Columns

| column | what | file under `<data root>/runs/SAEA-SLURP-STAGE3-WSV1-FOLD-A-V1/attempt-slurp-native-stage3-wsv1-fold-a-generation-v1/supply-variants/` |
| --- | --- | --- |
| `a-base` | the delivering arm's first-visit column (LEFT of both contrasts) | `arm-a-base-slurp-slu-official-train-scores.json` |
| `b-exk30` | the exk30 column (RIGHT of the knob contrast) | `arm-b-exk30-slurp-slu-official-train-scores.json` |
| `t-twin` | the twin column (RIGHT of the null contrast) | `arm-t-twin-slurp-slu-official-train-scores.json` |

`scripts/flights/wsv1/wsv1_read.sh` refuses unless the READ row `SAEA-SLURP-STAGE3-WSV1-FOLD-A-COLUMN-READ-V1` is root countersigned, renders and scores the three columns once
(`scripts/analysis/stage3_rollout_score.py --mode supply-variants`), then runs
`scripts/analysis/stage3_paired_read.py --left-column a-base --right-column b-exk30` and `--right-column t-twin`.

## Arm A's byte identity (the wave shared-A/A method)

Verdict **IDENTICAL_MODULO_PROGRAM_IDENTITY** (`docs/readiness/2026-09-28-slurp-stage3-wsv1-fold-a-v1/arm-a-proof-v1.json`, tool `scripts/flights/wsv1/wsv1_arm_a_proof.py`, 120 rows dispatched serially against a fake POST under one common scratch run id, zero model/server/tokenizer/encoder/scorer contacts).

| proof | result |
| --- | --- |
| composed config: differing leaves by class | {"bookkeeping": 40, "program-switch": 1, "supply-pin": 2, "variants-block": 17}; request-affecting [] |
| prepared first-phase supply output = AGREE registered and committed | True (`eab5c61e92a47c1723c478f2b7914abade6152b195f676d7d32251f3d18884ae`) |
| arm A first Solver POST body = AGREE first Solver POST body, exactly | 0 / 120 rows (AGREE first Solver contacts 120) |
| the same, after mapping the program id / invocation index in quoted contact ids and masking remaining_model_contacts | 120 / 120 rows |
| twin T POST body = arm A (AT2) | 120 / 120 |
| arm B POST body = arm A (expected to differ: the k-30 supply) | 0 / 120 |
| every other contact mapped across programs (Perception, Reviewer, Planner, revisit Solver) | 0 / 543 identical exactly, 543 / 543 after the same normalisation, 0 unpaired; by role {"perception": {"contacts": 120, "normalised_identical": 120, "post_body_identical": 0}, "planner": {"contacts": 181, "normalised_identical": 181, "post_body_identical": 0}, "reviewer": {"contacts": 181, "normalised_identical": 181, "post_body_identical": 0}, "solver": {"contacts": 61, "normalised_identical": 61, "post_body_identical": 0}} |
| arm A vs AGREE first Solver: payload (custody) leaf classes differing, first 12 rows | {"evidence_provenance[].relpath": 12, "history[].contact_id": 12, "history[].content": 12, "history[].content_sha256": 12, "history[].producer_policy_id": 12, "history[].state_id": 12, "key_representation_id": 12, "matcher_policy_id": 12, "request_id": 12}; POST body leaf classes {"messages[].content[].text": 12} |

## Fit

Fit numbers are MEASURED, never placeholders (the VAR-2 lesson): scripts/flights/wsv1/wsv1_fit_measure.py read the sealed AGREE arm (its first Solver contact on every one of the 1080 rows; the delivering arm A renders that request up to the two program-identity fields, a few characters): supplied items min/mean/max 29/40.889/52, exemplar items 20 on every row, non-exemplar max 32, 5.0067 characters per token (least squares over every Solver contact), widest exemplar item 396 characters -> tokens_per_supplied_item 80, base_prompt_tokens 10266 (max over rows of prompt minus items x per-item, so base + items x per-item bounds every realised first Solver prompt; realised max 14426). Bounds: A and T 58 (measured max + 6 headroom -- the candidate-keyed stores follow Perception's output), B 68 (non-exemplar max + headroom + 30). Parser estimates: A/T 14906, B 15706 tokens, against a prompt limit of about 20,9xx at the 24,576 slot; the realistic widest B request (widest realised + 10 mean exemplars) is 14614 tokens. The preflight (core.flight.cli check, placeholder 4-bytes-per-token counter) is folded in 'fit'; under the armed compact-or-abstain policy a COMPACT_REQUIRED preflight with a non-negative PHYSICAL margin proceeds, and only a negative physical margin refuses.

| cell | phase | decision | rendered (4 B/token) | operational margin | physical margin |
| --- | --- | --- | ---: | ---: | ---: |
| arm | perception | ALLOW | 19453 | 1508 | 4580 |
| arm | reviewer | ALLOW | 19316 | 1645 | 4717 |
| arm | planner | ALLOW | 19256 | 1705 | 4777 |
| arm | solver | COMPACT_REQUIRED | 21281 | -320 | 2752 |
| arm | blockers | null | | | |
| smoke | perception | ALLOW | 19452 | 1509 | 4581 |
| smoke | reviewer | ALLOW | 19316 | 1645 | 4717 |
| smoke | planner | ALLOW | 19255 | 1706 | 4778 |
| smoke | solver | COMPACT_REQUIRED | 21281 | -320 | 2752 |
| smoke | blockers | null | | | |

The preflight renders one representative request per phase, the delivering arm's (it knows no arms), at the slot of 24,576 tokens; the k-30 column's Solver request is that request plus what the re-cap adds on the wire (B's POST body minus A's, measured by the arm-A proof):

| cell | Solver decision (delivering column, check) | physical margin, delivering column | k-30 adds (4 B/token, representative row) | **k-30 column physical margin** (representative row / widest delta) |
| --- | --- | ---: | ---: | ---: |
| arm | COMPACT_REQUIRED | 2752 | 386 | **2366** / 2264 |
| smoke | COMPACT_REQUIRED | 2752 | 386 | **2366** / 2264 |

## Files

| file | what it holds |
| --- | --- |
| `../2026-09-28-slurp-stage3-wsv1-fold-a-v1-preregistration.md` | the preregistration, with the `stage3_measurement` fence |
| `registered-facts-v1.json` | every model-free fact; the CANONICAL `stage3_measurement` |
| `arm-a-proof-v1.json` | the arm-A byte-identity proof |
| `protocol-registered-v1.json` | identities, hashes, the rule |
| `generation-plan-registered-v1.json` / `fit-plan-registered-v1.json` | the arm's plans |
| `smoke-generation-plan-registered-v1.json` / `smoke-fit-plan-registered-v1.json` | the smoke's plans |
| `analysis-recipe-v1.json` | the column read; `run_ids.read` = `SAEA-SLURP-STAGE3-WSV1-FOLD-A-COLUMN-READ-V1` |
| `root-admission-draft-v1.json` | the receipt root mints with `scripts/flights/wsv1/wsv1_mint_receipt.py` |

**Sequence.** (1) Root countersigns the four DRAFT flight rows (the READ row stays draft until the seal and is
countersigned before any column score is opened) and mints `coordination/slurp-stage3-wsv1-fold-a-v1/root-admission-v1.json` with
`scripts/flights/wsv1/wsv1_mint_receipt.py`. (2) Flip with `scripts/flights/wsv1/wsv1_flip.sh` (smoke, then arm,
one converging loop; minted supplies must reproduce the AGREE digests). (3) `scripts/flights/wsv1/batch_chain_wsv1.sh`
on the slurp-np4 session through the batch driver (smoke, then the one-arm campaign; decision 77). (4) `scripts/flights/wsv1/wsv1_read.sh`.

**Budgets.** Arm 14,040 generation contacts (1,080 x 13), 56,160 FIT endpoints,
40,099 speech seconds, 14.2 GPU hours; smoke
52 / 208 / 138 / 1.0 --
the AGREE arithmetic at ceiling 13. Expected spend about 6.06 contacts per row (AGREE's 4.06 + 2).
