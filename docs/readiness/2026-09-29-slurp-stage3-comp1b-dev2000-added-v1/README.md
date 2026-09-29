# Cell A2: COMP-1b on DEV-2000-ADDED

Registered before contact 2026-09-29 at study commit `64ab71d14` (owner decision 198);
all three cells **held**. Nothing here authorises a flight, a flip or an admission entry.

**Why.** Owner decision 198 defines A2 as COMP-1b on the fresh DEV-2000-ADDED roster. The COMP-1b TRAIN Fold A read
([`docs/results/2026-09-29-slurp-comp1b-fold-a-read.md`](../../../docs/results/2026-09-29-slurp-comp1b-fold-a-read.md)): intent +3.80 pp CI95 [+1.94, +5.65], official pooled SLU-F1 -0.60 pp [-2.29, +1.07] against the in-chain A/A SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1 (n = 1,080); zero-gold entity emission 161 vs 162 rows; coordinator bar NOMINATED (intent), SLU non-inferiority open on width.

**Supersedes.** The COMP-1 DEV-2000-ADDED placeholder (`docs/readiness/2026-09-27-slurp-stage3-comp-1-dev2000-added-v1`), whose arm carried the citation
contract and the literal `TO-BE-DECLARED-...` expectation. Its arm and smoke fragments are now `superseded`; their
exposure rows carry a SUPERSEDED note; no file is deleted. The placeholder never flew.

**What it is.** A2 is COMP-1b's composed plan with only the roster moved, equivalently the superseded COMP-1 DEV-2000-ADDED placeholder with the citation contract reverted: the locked v2.0 plan as the sealed DEV-2000-ADDED plan arm flew it + (1) the agreement term (w_agree 1.0 over the exemplar-intent vote, recall k 60, delivered 8-1-8; this roster's own vote table SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-DEV2000-ADDED-V1) + (2) the centroid boundary key (facet_source prepared/SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1/facets.jsonl) + (3) NO citation contract: policy phase-native-candidates-review-revise-v1, Solver probes/slurp_native_role_solver_v2.txt, no response format, deliver_normaliser saea-deliver-normalise-v3 + (4) nothing else. Proven by `registered-facts-v1.json` (`composed_config_diffs`), a commuting square:
A2 vs the placeholder = the citation contract's four leaves alone; A2 vs the flown COMP-1b Fold A arm = exactly the
paths and values by which the placeholder differs from the flown COMP-1 Fold A arm (the roster re-target and this
roster's agreement-table pin); A2 vs its A/A = the agreement term and the centroid key alone. Derived by
`scripts/flights/comp1/derive_slurp_comp1bdev_cells.py`.

**In-chain A/A.** `slurp-native-stage3-comp1-aa-dev2000-added-v1` (the sealed DEV plan arm's bytes at recall k 60), the placeholder chain's own A/A,
carried in unchanged; the campaign plan `configs/campaign/slurp-native-stage3-comp1b-dev2000-added-v1.json` flies it and then the arm (instrument rule 3).

**Measurement.** `cross-flight-with-in-chain-replicate`, n = 1,000, intent primary, `expected_effect_pp` **3.8**
(the COMP-1b Fold A intent point), official SLU-F1 the guard at this roster's own null h_SLU 1.2525
(h_intent 1.152; docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md section 2d, row 'cross-flight A/A, DEV-2000-ADDED' (the B6 pair)); bar about 2.6 pp at n = 1,000.

**The none-hint column (decision 199) is NOT included.** The same-flight machinery (src/speech_aware_evidence_acquisition/rails/supply_variants.py) admits an arm that re-caps ONLY the supply-selection knobs of SUPPLY_VARIANT_KNOB_TAILS (phase_supply k, fuse_coverage m / c / top_l; candidate_supply max_candidates) or swaps ONE pinned alternate release; it refuses any other path by name before contact. N1 is neither: it is a per-row GATE on the exemplar supply's entity-free share that adds an explicit empty-entity instruction, i.e. new Solver content conditioned on a supply statistic -- no knob tail expresses it, and no pinned alternate release carries it. Expressing it would need new rails code. Separately, an arm group adds one non-delivering Solver contact per row at the first visit, which raises the run-cumulative contact ceiling (11 per row) and the fit envelope of the arm's own flight; the registration cannot prove that neutral for the delivered arm without a FIT measurement. A2 is therefore registered WITHOUT the column; N1 stays a candidate for its own registration once a rails variant kind exists for it.

**Runs.** `SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-V1` / `SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-FIT-V1`; `SAEA-SLURP-STAGE3-COMP1-AA-DEV2000-ADDED-V1` / `SAEA-SLURP-STAGE3-COMP1-AA-DEV2000-ADDED-FIT-V1`; `SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-SMOKE-4-V1` / `SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-SMOKE-4-FIT-V1`. READ `SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-PAIRED-ANALYSIS-V1`.

**Declare, mint, flip, queue.** (1) Root countersigns the DRAFT rows (arm, arm FIT, smoke, smoke FIT, READ; the A/A's
two rows) and mints `coordination/slurp-stage3-comp1b-dev2000-added-v1/root-admission-v1.json` with `scripts/flights/comp1/comp1bdev_mint_receipt.py` (six eligible run
ids). (2) `scripts/flights/comp1/comp1bdev_flip.sh` re-pins smoke, A/A and arm until the package converges at one
HEAD; each re-minted supply must reproduce its expected output digest. (3) `scripts/flights/comp1/batch_chain_comp1bdev.sh`
queues the smoke then the A/A + arm campaign on the np4 session (decision 77). (4) After both seals the READ row is
countersigned and `bash scripts/flights/comp1/comp1bdev_read.sh` reads it.

**Not authorised.** No flight before steps 1-2; no re-flying of the DEV plan arm; no test, DEV-1000 or Fold B contact;
no citation contract.
