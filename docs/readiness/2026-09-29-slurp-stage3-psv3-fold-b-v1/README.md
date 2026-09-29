# Cell P-SV-3: phase-2 same-flight Perception branches on TRAIN Fold B (owner decisions 184, 186, 188)

Registered before contact 2026-09-29 at study commit `0b50d47e51abecc41ca92f197c1324642d719a6d` (branch `fable/psv3`);
this cell **held**. Nothing here authorises a flight, a flip or an admission entry. Development numbers only.

**Purpose (coordinator, decision 180 consumption thesis; node-gain ledger).** Intent is decided at Perception's shortlist. Of the 153 wrong rows on Fold A, gold was off Perception's list on 83 (49 still inside the retrieved boundary block, 34 outside it). P-SV-2 (forced three candidates) tests whether the note can carry more of the in-block gold; P-SV-3 measures the boundary-supply DEPTH itself (how many boundary items Perception is shown) as a same-flight Perception-branch column: B is the same AGREE Perception supply with the boundary-supply depth raised one step (fuse_coverage.m and fuse_coverage.top_l, 8 -> 12, c unchanged), read primarily on `present` (gold on the branch's list), with official intent beside (docs/results/2026-09-28-slurp-node-information-gain-ledger.md, section 1.4 and section 5 item 1).

**The question.** At the one Perception visit of every TRAIN Fold B row, does raising the boundary-supply depth itself (fuse_coverage.m and fuse_coverage.top_l together, 8 -> 12, c unchanged) raise the share of rows whose gold intent is on Perception's list beyond the in-flight twin's null, read against the delivering branch A in the same flight, and what does the level-2 branch Solver make of the widened supply?

**The base and the three registered changes.** The retained AGREE arm (`SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1`) with:
(1) the Fold A -> Fold B re-target the filler family used (dataset `slurp-speech-native-evo-fold-b-1080`, roster
`docs/receipts/rosters/slurp-evo-fold-b-v2.json`, the two speech-query pins copied from `configs/baseline/slurp-native-stage3-filler-fold-b-c01-baseline-v1.json`, the agreement table
`prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-B-V1/agreement.jsonl` (`06990a86`, ledger row `SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-B-V1`, cited not
re-registered), the preparation receipts); (2) the program switch `phase-native-candidates-review-revise-v1` (11) -> `phase-native-candidates-review-revise-pbranch3-l2-v1`
(15 = 11 + 2 (K - 1)); (3) the branch block `native_episode.roles.perception.branches` (level 2):

| branch | order | role | axis | max_supplied_items |
| --- | ---: | --- | --- | ---: |
| `b-depth` | 0 | B | `overrides` {'knowledge_stores.intent-boundaries.phase_supply.perception.fuse_coverage.m': 12, 'knowledge_stores.intent-boundaries.phase_supply.perception.fuse_coverage.top_l': 12} | 14 |
| `t-twin` | 1 | twin of `a-agree` (T) | none | 10 |
| `a-agree` | 2 | delivering (A) | none | 10 |

`fit_estimate`: slot 24576, completion 512, base prompt 2577,
149 tokens per supplied item -- MEASURED on the sealed AGREE arm's 1,080 Perception contacts
(`scripts/flights/psv/psv_fit_measure.py`; realised Perception prompt 2642-3769
tokens, 8 boundary items max, widest item 895 characters,
6.023 characters per token); branch estimates {"a_and_twin": 4067, "boundary_depth": 4663, "min_candidates": 4067, "top2_contrast": 4365} against the
20990-token prompt limit.

**Branch-seed not yet prepared.** The B branch carries no `prepared_seed` pin: `core.flight.cli prepare-branch-seeds` has not run for this cell (left to root at the flip, per the readiness gate's `branch-seed-unpinned` finding).

**Measurement.** `measurement_design` `same-flight-perception-variant` (the spelling `scripts/checks/stage3_effect_floor_check.py` and
`scripts/checks/flight_registration_check.py` register; the spec's section 4 says `same-flight-perception-branch`,
and the gate comment flags the reconciliation), level 2, claim **`nominated`**, `aa_arm_id` `t-twin`,
`tuning_roster` `SLURP-EVO-FOLD-A-V2`, `read_roster` `SLURP-EVO-FOLD-B-V2`. Primary: gold-on-list (present) in the branch Perception note (primary, a presence measurement; owner decision 190's ruling-O4 framing extended to this axis): B (fuse_coverage.m and fuse_coverage.top_l raised together 8 -> 12, c unchanged at 1 -- the boundary-supply DEPTH itself, the inner loop's 'boundary_phase_supply +1 step') minus A; official intent accuracy of the level-2 branch Solver column reported beside, never gating; gold rank and list size beside.
Expected effect **0.0** (nominated); ceiling the 83 wrong rows with gold off Perception's list on Fold A entirely (7.69 pp presence ceiling): 49 of them still inside the retrieved boundary block but off the rendered list, 34 outside the block entirely, docs/results/2026-09-28-slurp-node-information-gain-ledger.md. Conversion basis: no conversion is claimed: raising the boundary-supply depth (fuse_coverage.m and fuse_coverage.top_l together, 8 -> 12, c unchanged) only changes what Perception is SHOWN, never the response contract or the presentation it renders from that supply; whether a newly shown item reaches top-1, appears on the note's candidate list, or changes the level-2 Solver's answer is UNMEASURED (row 139: no prior, so the declaration is 0.0 nominated with the ceiling beside).
Provisional floor 1.4900 pp (SLU, reference only -- primary_metric_key 'present' has no floor, owner decision 190); the bar is the twin null. `variant_cost`: +2 Perception and +2 Solver contacts per
row, +12619.19 speech seconds per flight (2 x row audio per non-A branch).

## Decision rule (fixed here)

SAME-FLIGHT PERCEPTION-BRANCH READ (owner decision 184; level 2; claim ceiling 'nominated', ruling O1). Per branch (a-agree delivering, b-depth, t-twin): the sealed branch note's candidate list gives gold's rank (1/2/3/absent), top1 and present offline (gold enters only offline); the branch's level-2 first-visit Solver answer is rendered through the delivered row's normaliser and projection and scored ONCE with slurp-slu-official-train (score_complete_derived_copy); A's column is A's own first Solver answer. Every contrast is a paired ROW bootstrap (cluster key sample_id, 10,000 draws, seed 20260929); the utterance-level number is reported beside and never gates. (1) THE TWIN NULL: T minus A per metric; the bar = |T - A offset| + its CI95 half-width, reported beside the design's own provisional floor per metric (owner decision 190; stage3_measurement.provisional_floor_pp -- intent 0.6500 pp, SLU 1.4900 pp). (2) PRESENCE: b-depth minus A on gold-on-list (present) in the branch note (primary, ruling O4). NOMINATED (as a presence change) iff the present CI95 lower bound is above zero AND the point delta exceeds the twin's present bar. Reported beside, never gating: official intent accuracy and SLU-F1 of the level-2 branch Solver column (B vs A vs T), list size, gold rank, and the conversion of gold at rank 3. A presence nomination opens no system claim: it only informs a later level-2 intent cell on the same pair.

## Fit (core.flight.cli check, held)

PENDING: core.flight.cli check not yet folded in.

The first Solver visit's realised prompt on the AGREE arm was 5003-14426 tokens;
a branch Solver contact carries a branch note of the same shape in place of A's.

## Sequence

(1) Root countersigns the four DRAFT flight rows (the READ row `SAEA-SLURP-STAGE3-PSV3-FOLD-B-BRANCH-READ-V1` stays draft until the seal) and mints
`coordination/slurp-stage3-psv3-fold-b-v1/root-admission-v1.json` with `scripts/flights/psv/psv_mint_receipt.py psv3`. (2) `bash scripts/flights/psv/psv_flip.sh psv3`
(loop form, converges at one HEAD; naming psv3 explicitly leaves any sibling P-SV cell's own flip untouched). (3)
`bash scripts/flights/psv/batch_chain_psv.sh psv3` on slurp-np4 through the batch driver (smoke first, then the
one-cell arm campaign). (4) `bash scripts/flights/psv/psv_read.sh psv3`.

**Budgets.** Arm 16,200 generation contacts (1,080 x 15), 64,800 FIT
endpoints, 47,322 speech seconds, 16.4 GPU hours; smoke
60 / 240 / 153 / 1.0.
Expected spend about 8.06 contacts per row (AGREE's 4.06 + 4).
