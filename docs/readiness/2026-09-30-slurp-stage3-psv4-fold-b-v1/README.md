# Cell P-SV-4: phase-2 same-flight Perception branches on TRAIN Fold B (owner decisions 184, 186, 188)

Registered before contact 2026-09-30 at study commit `2df3fcf0d3e6797a98dc4b030e3caaf3f1811656` (branch `fable/keysource`);
this cell **held**. Nothing here authorises a flight, a flip or an admission entry. Development numbers only.

**Purpose (the retrieval-key recall read, 2026-09-30).** No key built from pinned vectors reaches +4 pp presence; one key changes rank QUALITY: K6p, the centred centroid + agreement key under production admission, lifts gold to boundary-block rank 1 on +22 (Fold A) / +26 (Fold B) rows over the centroid + agreement key, about +1.1 pp implied intent on both folds (docs/results/2026-09-30-slurp-retrieval-key-recall-offline.md). This cell reads that effect as a same-flight level-2 Solver column (the note: a note-only level-1 branch would not show a rank-1 conversion effect), through the new key_source Perception-branch axis: B re-keys the boundary retrieval with the two pinned K6p artifacts, everything else as A. The same-flight intent floor (0.65 pp at n = 1,080, owner decision 190) makes a ~1.1 pp effect readable as a column; the cross-flight floor (2.5 pp) would not.

**The question.** At the one Perception visit of every TRAIN Fold B row, does re-keying the boundary retrieval with K6p (the centred centroid key and the centred speech queries, agreement unchanged -- a key_source swap inside the branch's own pre-flight router, nothing else) move the level-2 branch Solver column's official intent accuracy beyond the in-flight twin's null, read against the delivering branch A (AGREE's Perception evidence as flown) in the same flight?

**The base and the three registered changes.** The retained AGREE arm (`SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1`) with:
(1) the Fold A -> Fold B re-target the filler family used (dataset `slurp-speech-native-evo-fold-b-1080`, roster
`docs/receipts/rosters/slurp-evo-fold-b-v2.json`, the two speech-query pins copied from `configs/baseline/slurp-native-stage3-filler-fold-b-c01-baseline-v1.json`, the agreement table
`prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-B-V1/agreement.jsonl` (`06990a86`, ledger row `SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-B-V1`, cited not
re-registered), the preparation receipts); (2) the program switch `phase-native-candidates-review-revise-v1` (11) -> `phase-native-candidates-review-revise-pbranch3-l2-v1`
(15 = 11 + 2 (K - 1)); (3) the branch block `native_episode.roles.perception.branches` (level 2):

| branch | order | role | axis | max_supplied_items |
| --- | ---: | --- | --- | ---: |
| `b-k6p` | 0 | B | `key_source` K6p (`facet_source` prepared/SAEA-SLURP-CENTRED-CENTROID-KEY-V1/key-v1.jsonl (`98533f82`), `query_source` prepared/SAEA-SLURP-CENTRED-QUERIES-V1/fold-b/query-vectors-speech-segments.jsonl (`6b056fef`); agreement unchanged) | 10 |
| `t-twin` | 1 | twin of `a-agree` (T) | none | 10 |
| `a-agree` | 2 | delivering (A) | none | 10 |

`fit_estimate`: slot 24576, completion 512, base prompt 2577,
149 tokens per supplied item -- MEASURED on the sealed AGREE arm's 1,080 Perception contacts
(`scripts/flights/psv/psv_fit_measure.py`; realised Perception prompt 2642-3769
tokens, 8 boundary items max, widest item 895 characters,
6.023 characters per token); branch estimates {"a_and_twin": 4067, "boundary_depth": 4663, "key_source": 4067, "min_candidates": 4067, "top2_contrast": 4365} against the
20990-token prompt limit.

**Branch-seed not yet prepared.** The B branch carries no `prepared_seed` pin: `core.flight.cli prepare-branch-seeds` has not run for this cell (left to root at the flip, per the readiness gate's `branch-seed-unpinned` finding).

**Measurement.** `measurement_design` `same-flight-perception-variant` (the spelling `scripts/checks/stage3_effect_floor_check.py` and
`scripts/checks/flight_registration_check.py` register; the spec's section 4 says `same-flight-perception-branch`,
and the gate comment flags the reconciliation), level 2, claim **`nominated`**, `aa_arm_id` `t-twin`,
`tuning_roster` `SLURP-EVO-FOLD-A-V2`, `read_roster` `SLURP-EVO-FOLD-B-V2`. Primary: official intent accuracy of the level-2 branch Solver column (primary): B (key_source K6p: the centred centroid key and the centred Fold B speech queries, agreement unchanged) minus A, with gold-on-list (present) and gold rank in the branch note beside; guard SLU-F1 of the same column; the delivered row is A and identical by construction at the request level (reported, never contrasted).
Expected effect **1.1** (nominated; `claims_benefit` true); ceiling the +26 net Fold B rows K6p lifts to boundary-block rank 1 over the centroid + agreement key (815 vs 789 of 1,080; Fold A +22, 845 vs 823), an offline model-free read of sealed vectors (docs/results/2026-09-30-slurp-retrieval-key-recall-offline.md), reproduced from the two pinned artifacts by scripts/analysis/slurp_k6p_artifact_proof.py (proof.json sha256 ad34e12f). Conversion basis: implied intent +11.6 rows of 1,080 on Fold B (+11.5 on Fold A; +5.0 to +6.6 in each of the four utterance halves), the note's analogue: rows lifted to block rank 1 are assumed to convert like today's rank-1 rows (P-SV-1 a-agree's rank-conditional conversions on Fold B). expected_effect_pp 1.1 = 11.6 / 1,080 rounded. Presence cost -0.7 / +0.2 pp (Fold A / Fold B); against the description key the P-SV cells fly as A, the presence change is 0 / +14 rows, so the flown A is a stricter comparator than cent_agree on rank and a looser one on presence. Rows lifted may be harder than today's rank-1 rows: the declaration is a registered expectation, never a claim. DISCLOSURE: the key family was chosen offline over the sealed vectors of BOTH folds (15 families compared; K6p carries no tuned parameter beyond the flown weights, and its centring statistics come from the Fold-B-disjoint R01C roster), so TRAIN Fold B is not a clean held-out roster for the key CHOICE; the registered tuning roster stays Fold A, and Fold B is read only through this flight's own same-flight columns.
Provisional floor 0.6500 pp (intent, primary, owner decision 190); the bar is the twin null. `variant_cost`: +2 Perception and +2 Solver contacts per
row, +12619.19 speech seconds per flight (2 x row audio per non-A branch).

## Decision rule (fixed here)

SAME-FLIGHT PERCEPTION-BRANCH READ (owner decision 184; level 2; claim ceiling 'nominated', ruling O1). Per branch (a-agree delivering, b-k6p, t-twin): the sealed branch note's candidate list gives gold's rank (1/2/3/absent), top1 and present offline (gold enters only offline); the branch's level-2 first-visit Solver answer is rendered through the delivered row's normaliser and projection and scored ONCE with slurp-slu-official-train (score_complete_derived_copy); A's column is A's own first Solver answer. Every contrast is a paired ROW bootstrap (cluster key sample_id, 10,000 draws, seed 20260929); the utterance-level number is reported beside and never gates. (1) THE TWIN NULL: T minus A per metric; the bar = |T - A offset| + its CI95 half-width, reported beside the design's own provisional floor per metric (owner decision 190; stage3_measurement.provisional_floor_pp -- intent 0.6500 pp, SLU 1.4900 pp). (2) THE CONTRAST: b-k6p (key_source K6p: the centred centroid key and the centred Fold B speech queries, agreement unchanged) minus A on the level-2 branch Solver column's official intent accuracy (primary). NOMINATED iff the intent CI95 lower bound is above zero AND the point delta exceeds the twin's intent bar AND the SLU-F1 CI95 lower bound of the same column is not below minus the twin's SLU bar (guard). BRANCH-LOCAL HARM iff the intent CI95 upper bound is below zero and the point magnitude exceeds the twin bar. Otherwise NOT NOMINATED. Reported beside, never gating: gold-on-list (present) and mean gold rank of the B note vs A and T, gold at supplied-block rank 1 (the note's mechanism: +26 rows expected on Fold B), the conversion P(correct | gold rank r in the branch note) against the ledger's 97.57 / 26.98 / 12.0 %, and the delivered row (identical by construction). A nomination sends the composed policy to a full-system cross-flight read against an in-chain A/A; it admits nothing.

## Fit (core.flight.cli check, held)

PENDING: core.flight.cli check not yet folded in.

The first Solver visit's realised prompt on the AGREE arm was 5003-14426 tokens;
a branch Solver contact carries a branch note of the same shape in place of A's.

## Sequence

(1) Root countersigns the four DRAFT flight rows (the READ row `SAEA-SLURP-STAGE3-PSV4-FOLD-B-BRANCH-READ-V1` stays draft until the seal) and mints
`coordination/slurp-stage3-psv4-fold-b-v1/root-admission-v1.json` with `scripts/flights/psv/psv_mint_receipt.py psv4`. (2) `bash scripts/flights/psv/psv_flip.sh psv4`
(loop form, converges at one HEAD; naming psv4 explicitly leaves any sibling P-SV cell's own flip untouched). (3)
`bash scripts/flights/psv/batch_chain_psv.sh psv4` on slurp-np4 through the batch driver (smoke first, then the
one-cell arm campaign). (4) `bash scripts/flights/psv/psv_read.sh psv4`.

**Budgets.** Arm 16,200 generation contacts (1,080 x 15), 64,800 FIT
endpoints, 47,322 speech seconds, 16.4 GPU hours; smoke
60 / 240 / 153 / 1.0.
Expected spend about 8.06 contacts per row (AGREE's 4.06 + 4).

## Coordinator ruling (Fable 5.1, 2026-09-30)

The K6p selection disclosure above is **accepted, with a stated consequence**. The key was chosen
among the candidate keys of the recall-key note (eight, K1-K8, in
`docs/results/2026-09-30-slurp-retrieval-key-recall-offline.md`; the disclosure above counts 15
families across that comparison -- the consequence below holds for either count) using gold-derived
rank counts on **both** folds. K6p carries no tuned parameter, and its centring statistics come from
the R01C roster, which is disjoint from both folds; the choice itself, however, saw Fold B. The
Fold B read therefore carries a **selection bias of unknown size**.

Consequences, binding on this package:

1. P-SV-4 reads with claim ceiling **`nominated`** (unchanged from the registration); no reading of
   this cell may exceed it.
2. A NOMINATED verdict does not admit `key-source:k6p` into the module. It requires **replication on
   a fresh roster (DEV-2000-ADDED)** first -- the standing same-roster-then-fresh rule. Only a
   replicated nomination lets the `key-source:k6p` component enter the module.
3. The flip (Sequence step 2) waits for **owner decision 208**; the cell stays HELD until then.
