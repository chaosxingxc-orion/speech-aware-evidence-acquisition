# Cell P-SV-1: phase-2 same-flight Perception branches on TRAIN Fold B (owner decisions 184, 186, 188)

Registered before contact 2026-09-29 at study commit `f33e8a0f2` (branch `fable/branchseeds`);
both cells **held**. Nothing here authorises a flight, a flip or an admission entry. Development numbers only.

**The question.** At the one Perception visit of every TRAIN Fold B row, does rendering the branch's rank-1/rank-2 candidate pair as a top-2 contrast block (top2-contrast-v1) move the level-2 branch Solver column's official intent accuracy beyond the in-flight twin's null, read against the delivering branch A (AGREE's Perception evidence as flown) in the same flight?

**The base and the three registered changes.** The retained AGREE arm (`SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1`) with:
(1) the Fold A -> Fold B re-target the filler family used (dataset `slurp-speech-native-evo-fold-b-1080`, roster
`docs/receipts/rosters/slurp-evo-fold-b-v2.json`, the two speech-query pins copied from `configs/baseline/slurp-native-stage3-filler-fold-b-c01-baseline-v1.json`, the agreement table
`prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-B-V1/agreement.jsonl` (`06990a86`, ledger row `SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-B-V1`, cited not
re-registered), the preparation receipts); (2) the program switch `phase-native-candidates-review-revise-v1` (11) -> `phase-native-candidates-review-revise-pbranch3-l2-v1`
(15 = 11 + 2 (K - 1)); (3) the branch block `native_episode.roles.perception.branches` (level 2):

| branch | order | role | axis | max_supplied_items |
| --- | ---: | --- | --- | ---: |
| `b-top2contrast` | 0 | B | `presentation_id` top2-contrast-v1 | 12 |
| `t-twin` | 1 | twin of `a-agree` (T) | none | 10 |
| `a-agree` | 2 | delivering (A) | none | 10 |

`fit_estimate`: slot 24576, completion 512, base prompt 2577,
149 tokens per supplied item -- MEASURED on the sealed AGREE arm's 1,080 Perception contacts
(`scripts/flights/psv/psv_fit_measure.py`; realised Perception prompt 2642-3769
tokens, 8 boundary items max, widest item 895 characters,
6.023 characters per token); branch estimates {"a_and_twin": 4067, "min_candidates": 4067, "top2_contrast": 4365} against the
20990-token prompt limit.

**Contrast-pair table pinned (V2, 2026-09-29, ruling O7).** The `top2-contrast-v1` renderer reads the model-free contrast-pair table built by `scripts/build_slurp_intent_contrast_pairs.py --pair-scope all-pairs`: `prepared/SAEA-SLURP-PERCEPTION-CONTRAST-PAIRS-V2/table-v1.json` (data root), sha256 `0d74fdb6aae70bff82abbd52355fe34b58cf646fe36a80016220ba1e714a7e34`, receipt `docs/receipts/knowledge/slurp-perception-contrast-pairs-v2.json` (sha256 `c6fd04260b00ec6fdfaebd0e5ecc1a5f1edcb76ac30f06dbeaf08c1c0b437ac8`; 1,710 pairs written / 60 skipped of 1,770, insufficient pool support; every unordered pair of distinct intents above the floor, roster-agnostic, from the R01/Fold-A/Fold-B-excluded TRAIN pool). The pin sits on the branch (`b-top2contrast.contrast_pairs`) and the runtime verifies the file's bytes against it before any contact. It replaces the nearest-rival V1 pin (`19bf2487`, 48 pairs), which covered 415/1078 (38.5%) of this seed's rows against V2's 1035/1078 (96.0%) (`scripts/analysis/slurp_contrast_pair_coverage.py`). Registered in `registered-facts-v1.json` (`contrast_pair_table`).

**Branch-seed coverage (disclosed before countersigning, 2026-09-29).** The B branch's pinned `prepared_seed` (`prepared/SAEA-SLURP-STAGE3-PSV1-FOLD-B-V1/perception-branch-seeds-v2.json`) carries seeds for 1,078 of the 1,080 Fold B rows: the two remaining Fold B rows have zero boundary recall for every column (A, B and T alike), a property of the data rather than of the branch.

**Measurement.** `measurement_design` `same-flight-perception-variant` (the spelling `scripts/checks/stage3_effect_floor_check.py` and
`scripts/checks/flight_registration_check.py` register; the spec's section 4 says `same-flight-perception-branch`,
and the gate comment flags the reconciliation), level 2, claim **`nominated`**, `aa_arm_id` `t-twin`,
`tuning_roster` `SLURP-EVO-FOLD-A-V2`, `read_roster` `SLURP-EVO-FOLD-B-V2`. Primary: official intent accuracy of the level-2 branch Solver column (primary): B (top2-contrast-v1) minus A, with gold-on-list and gold rank in the branch note beside; guard SLU-F1 of the same column; the delivered row is A and identical by construction at the request level (reported, never contrasted).
Expected effect **0.0** (nominated); ceiling the 42 wrong delivered rows with gold at Perception rank 2 on Fold A (3.89 pp of 1,080; 63 rank-2 rows overall, 5.83 pp level-1 top1 ceiling), docs/results/2026-09-28-slurp-node-information-gain-ledger.md. Conversion basis: rank-2 -> rank-1 promotion rate under a top-2 contrast is UNMEASURED; the node ledger's conversion of gold at Perception rank 2 is 26.98 % and at rank 1 97.57 % (row 139: no prior, so the declaration is 0.0 nominated with the ceiling beside).
Provisional floor 0.3163 pp; the bar is the twin null. `variant_cost`: +2 Perception and +2 Solver contacts per
row, +12619.19 speech seconds per flight (2 x row audio per non-A branch).

## Decision rule (fixed here)

SAME-FLIGHT PERCEPTION-BRANCH READ (owner decision 184; level 2; claim ceiling 'nominated', ruling O1). Per branch (a-agree delivering, b-top2contrast, t-twin): the sealed branch note's candidate list gives gold's rank (1/2/3/absent), top1 and present offline (gold enters only offline); the branch's level-2 first-visit Solver answer is rendered through the delivered row's normaliser and projection and scored ONCE with slurp-slu-official-train (score_complete_derived_copy); A's column is A's own first Solver answer. Every contrast is a paired ROW bootstrap (cluster key sample_id, 10,000 draws, seed 20260929); the utterance-level number is reported beside and never gates. (1) THE TWIN NULL: T minus A per metric; the bar = |T - A offset| + its CI95 half-width, reported beside the provisional floor 0.3163 pp. (2) THE CONTRAST: b-top2contrast minus A on the level-2 branch Solver column's official intent accuracy (primary). NOMINATED iff the intent CI95 lower bound is above zero AND the point delta exceeds the twin's intent bar AND the SLU-F1 CI95 lower bound of the same column is not below minus the twin's SLU bar (guard). BRANCH-LOCAL HARM iff the intent CI95 upper bound is below zero and the point magnitude exceeds the twin bar. Otherwise NOT NOMINATED. Reported beside, never gating: gold-on-list and mean gold rank of the B note vs A and T, the conversion P(correct | gold rank r in the branch note) against the ledger's 97.57 / 26.98 / 12.0 %, the rows where top2-contrast-v1 rendered nothing (presentation_skip_reason, ruling O5), and the delivered row (identical by construction). A nomination sends the composed policy to a full-system cross-flight read against an in-chain A/A; it admits nothing.

## Fit (core.flight.cli check, held)

| cell | phase | decision | rendered (4 B/token) | operational margin | physical margin |
| --- | --- | --- | ---: | ---: | ---: |
| arm | perception | ALLOW | 19452 | 1492 | 4564 |
| arm | reviewer | ALLOW | 19316 | 1628 | 4700 |
| arm | planner | ALLOW | 19255 | 1689 | 4761 |
| arm | solver | COMPACT_REQUIRED | 21281 | -337 | 2735 |
| arm | blockers | null | | | |
| arm | perception, top2-contrast branch (estimate) | margin 4564 - 448 | | | 4116 |
| smoke | perception | ALLOW | 19448 | 1516 | 4588 |
| smoke | reviewer | ALLOW | 19311 | 1653 | 4725 |
| smoke | planner | ALLOW | 19250 | 1714 | 4786 |
| smoke | solver | COMPACT_REQUIRED | 21276 | -312 | 2760 |
| smoke | blockers | null | | | |
| smoke | perception, top2-contrast branch (estimate) | margin 4588 - 448 | | | 4140 |

The first Solver visit's realised prompt on the AGREE arm was 5003-14426 tokens;
a branch Solver contact carries a branch note of the same shape in place of A's.

## Sequence

(1) Root countersigns the four DRAFT flight rows (the READ row `SAEA-SLURP-STAGE3-PSV1-FOLD-B-BRANCH-READ-V1` stays draft until the seal) and mints
`coordination/slurp-stage3-psv1-fold-b-v1/root-admission-v1.json` with `scripts/flights/psv/psv_mint_receipt.py psv1`. (2) `bash scripts/flights/psv/psv_flip.sh`
(loop form, both P-SV cells, one HEAD). (3) `bash scripts/flights/psv/batch_chain_psv.sh` on slurp-np4 through the batch
driver (P-SV-1 then P-SV-2, each smoke first). (4) `bash scripts/flights/psv/psv_read.sh psv1`.

**Budgets.** Arm 16,200 generation contacts (1,080 x 15), 64,800 FIT
endpoints, 47,322 speech seconds, 16.4 GPU hours; smoke
60 / 240 / 153 / 1.0.
Expected spend about 8.06 contacts per row (AGREE's 4.06 + 4).
