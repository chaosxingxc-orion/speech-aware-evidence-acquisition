# Cell COMP-1 on DEV-2000-ADDED: the composed arm's fresh-roster replication

Registered before contact 2026-09-27 at study commit `09f1b31e` (owner decision 161, with 138 and
152); all three cells **held**. Nothing here authorises a flight, a flip or an admission entry.

**Why.** Owner decision 161 admits AGREE into COMP-1 pending the DEV replication, and
`docs/results/2026-09-27-verdict-reclassification.md` (row D3, KEEP-PROVISIONAL) says the COMP-1 DEV-2000-ADDED round settles it.

**THE EXPECTATION IS NOT DECLARED, ON PURPOSE.** `stage3_measurement.SAEA-SLURP-STAGE3-COMP1-DEV2000-ADDED-V1.expected_effect_pp` is the
literal string `TO-BE-DECLARED-BY-COORDINATOR-FROM-THE-COMP-1-FOLD-A-READ` in both places the gate reads (`registered-facts-v1.json`, canonical, and the fence of
`../2026-09-27-slurp-stage3-comp-1-dev2000-added-v1-preregistration.md`). Owner decision 139 forbids an if-then on unread results and the COMP-1 Fold A arm has not
flown. Until the coordinator replaces the string in both places, `scripts/checks/stage3_effect_floor_check.py` refuses
the arm as `unparsable-declaration`; that is the intended state, exactly the state COMP-1 Fold A was registered in.

**What it is.** Cell COMP-1's plan bytes (`docs/readiness/2026-09-27-slurp-stage3-comp-1-fold-a-v1`) with only the roster moved, exactly as the sealed
DEV-2000-ADDED plan arm `SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1` (cell B6) moved the locked plan: cell COMP-1's composed plan with only the roster moved: the locked v2.0 plan as the sealed DEV-2000-ADDED plan arm flew it + (1) the agreement term as AGREE carries it (w_agree 1.0 over the exemplar-intent vote, recall k 60, delivered 8-1-8; the vote table is this roster's own SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-DEV2000-ADDED-V1) + (2) the centroid boundary key as KPROBE pins it (facet_source prepared/SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1/facets.jsonl) + (3) the citation contract (policy phase-native-candidates-review-revise-cited-v1, Solver response_format_id saea-solver-cited-answer-v1, instruction probes/slurp_native_role_solver_cited_v1.txt, deliver_normaliser saea-deliver-cited-answer-normalise-v3-v1) + (4) nothing else. Proven in
`registered-facts-v1.json` (`the_composition.is_comp1_fold_a`): every composed-config path on which this arm differs
from the COMP-1 Fold A arm is a path on which the DEV plan arm differs from the locked Fold A plan, this roster's own
agreement-table pin, bookkeeping, or the fragment's own block; `composed_config_diffs` proves arm vs A/A = the three
factor groups alone and A/A vs DEV plan = `k` 8 -> 60 alone.

**One roster-bound artifact is new.** The agreement table is a function of the roster's own sealed speech vectors, so
the Fold A table cannot be reused: `SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-DEV2000-ADDED-V1` was built model-free in this registration by
`scripts/build_slurp_intent_exemplar_agreement.py` against the sealed DEV plan cell (same builder, vote store, vote phase and target store as the
Fold A table): 1,000 rows, 20 votes each, 0 self-excluded exemplars, 0 rows with no vote, 59 facets ever voted for;
artifact sha256 `283bd9f58025b98a7c92f3b5f3495fce1e4b352bae52a3fc62bb8781b79e92d8`, receipt `d675d3ead30142fc23aef2564aaad06c7720512f3dd76f3f10e92d1f4b9951e2`. Its DRAFT model-free
ledger row is part of this package.

**Reused exactly as ROLL-3 / CELL-3 / B6 reuse them.** Roster `docs/receipts/rosters/slurp-dev-2000-added-v1.json` (`SLURP-DEV-2000-ADDED-V1`), split identity
`ee6c43cd4dd8fc2a583d2dd053e799c2d002efa3755fcd092ba7c7565431bf67`, split role `dev`; the DEV-2000-ADDED speech query vectors, alias and promoted packets
(`DEV-2000-ADDED-promotion.json`) as the sealed DEV plan arm pins them; scorer `slurp-slu-official` (the DEV sibling, never
`-train`); the smoke's four rows and split identity `fee83441e514473dc4ab798f8554882bc5753c7fc4924eda0e72c7af7ed51ef0` are cell ROLL-3's smoke's.

**Knowledge exclusion (no knowledge read here was built from a DEV-2000-ADDED row).** Proof file: the roster receipt
`docs/receipts/rosters/slurp-dev-2000-added-v1.json` `disjointness_proof` (`shared_with_train_construction_recordings` 0, `non_devel_ids_added` 0,
`shared_with_test_recordings` 0). The train-exemplars store is the TRAIN-built parent pool every DEV package read; the
agreement table's vote pool is that store and its self-exclusion MEASURED 0 excluded exemplars on all 1,000 rows
(`prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-DEV2000-ADDED-V1/receipt.json`); the centroid keys come from the R01-excluded construction-TRAIN pool (8,554 TRAIN utterances,
`prepared/SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1/receipt.json`), a subset of the same pool. Stores and releases are the DEV plan arm's, unchanged.

**Three cells, one chain.** `configs/campaign/slurp-native-stage3-comp1-dev2000-added-v1.json` carries the A/A **and** the arm (instrument rule 4); the four-row smoke is
outside the plan and never scored. The A/A's own prepared supply **reproduces the sealed DEV comparator's output
digest `d57ee9d6212bd3dc10762f84ec6ff1e8368b0b1a1e80fed9f9fbc81147fc5a19`** (999 rows seeded, 7970 ids -- one row admits no
written-key entry at tau 0.0, as in the sealed arm). The arm's supply: output `ecca16a276a9a4a35b6b5e0a765d30ab2b3ee893e3bc617c5ae2c3e7c51b7d08`
(1000 rows, 8000 ids); the smoke's `d5ec9b1516cb6b389d39aebec32b2b700b663ff21d15303a4789893415e3e083`. Gold-free delivery change: the
arm's boundary selection differs from the A/A's on 991 of 1000 rows.

**Per-class attribution (owner decision 138), fixed before contact.** `attribution-classes-v1.json`, derived model-free by
`scripts/flights/comp1dev/comp1dev_attribution_classes.py`, carries the five COMP-1 Fold A classes over the 232 intent-wrong rows of the
sealed DEV plan arm, with the Fold A predicates (cell CONV's for the agreement set, cell KPROBE's for the centroid set). Gold
is read on the scoring side only, from the bad-case bank roster `dev2000-added` (`analysis/SLURP-PLAN-BAD-CASE-BANK-V1/bank.jsonl`,
the file and access pattern the Fold A script uses). The single-factor selections are rebuilt through the production
constructor, which reproduces the A/A's and the arm's prepared supplies on 1,000 of 1,000 rows. The file holds counts and per-class id-list hashes only,
and the read re-runs the derivation and must reproduce every hash. Counts: delivered-but-wrong 83, newly-by-both 68,
newly-by-agree 26, newly-by-centroid 15, catch-all 40 (Fold A: 86 / 47 / 23 / 8 / 27); composed delivery 193 of 232.
Membership only: a delivery count is never a correctness count.

**Measurement.** `cross-flight-with-in-chain-replicate`, roster DEV-2000-ADDED, n = 1,000, own null h_intent 1.1520 /
h_SLU 1.2525 (`docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md` section 2d, the B6 pair), intent primary, official SLU-F1 the guard, bar about
2.6 pp at n = 1,000 (docs/results/2026-09-27-verdict-reclassification.md).

**Budgets and cost.** Per generation cell 11000 contacts (1,000 x 11), 44000 FIT endpoints,
6000 native task-contract calls, 32819 s repeated speech, 12.0 GPU hours (fit-inclusive cap), one
official score; smoke 44 / 176 / 90 s / 1.0 GPU hour. Caps total
25.0 GPU hours; ESTIMATE about 3.5-4.0 GPU hours for the chain (the sealed DEV plan arm realised
1.655 GPU hours at 4.07 contacts per row).

| file | what it holds |
| --- | --- |
| `../2026-09-27-slurp-stage3-comp-1-dev2000-added-v1-preregistration.md` | the preregistration, with the `stage3_measurement` fence (placeholder) |
| `registered-facts-v1.json` | every model-free fact, the proofs, the CANONICAL `stage3_measurement`, open items |
| `protocol-registered-v1.json` | identities, hashes, budgets, the decision rule, the claim boundary |
| `generation-plan-registered-v1.json` / `fit-plan-registered-v1.json` | the arm's plans |
| `aa-generation-plan-registered-v1.json` / `aa-fit-plan-registered-v1.json` | the in-chain A/A's plans |
| `smoke-generation-plan-registered-v1.json` / `smoke-fit-plan-registered-v1.json` | the smoke's plans |
| `analysis-recipe-v1.json` | the read (`scripts/flights/read_paired_cell.sh`, READ run `SAEA-SLURP-STAGE3-COMP1-DEV2000-ADDED-PAIRED-ANALYSIS-V1`, analysis root `analysis/SAEA-SLURP-STAGE3-COMP1-DEV2000-ADDED-PAIRED-ANALYSIS-V1`) |
| `attribution-classes-v1.json` | the per-class attribution membership (decision 138): counts and id-list hashes, fixed before contact |
| `root-admission-draft-v1.json` | the decision receipt root mints with `scripts/flights/comp1dev/comp1dev_mint_receipt.py` |

**Declare, mint, flip, queue.** (1) The coordinator declares `expected_effect_pp` from the COMP-1 Fold A read in both
places and commits. (2) Root countersigns the nine DRAFT exposure rows and mints `coordination/slurp-stage3-comp1-dev2000-added-v1/root-admission-v1.json` (decision id
`slurp-stage3-comp1-dev2000-added-admission-v1`, six eligible run ids) with `scripts/flights/comp1dev/comp1dev_mint_receipt.py`. (3)
`scripts/flights/comp1dev/comp1dev_flip.sh` re-pins smoke, A/A and arm until the package converges at one HEAD (it
refuses while the placeholder stands; the A/A's re-minted supply must again be `d57ee9d6...`). (4)
`scripts/flights/comp1dev/batch_chain_comp1dev.sh` queues the smoke, then the A/A + arm campaign, on the np4 session
(decision 77). (5) After both seals, the READ row is countersigned and `bash scripts/flights/read_paired_cell.sh docs/readiness/2026-09-27-slurp-stage3-comp-1-dev2000-added-v1` reads it.

**Not authorised.** No flight before steps 1-3; no re-flying of the DEV plan arm; no test, DEV-1000 or Fold B contact;
no fourth factor; the citation part is never reported as a gain.
