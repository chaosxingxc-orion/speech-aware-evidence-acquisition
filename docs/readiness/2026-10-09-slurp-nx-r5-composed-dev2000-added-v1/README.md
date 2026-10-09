# NX Stage J round R5: the composed read (review-off COMP-1b + v4g, lock v2.2) on DEV-2000-ADDED

Registered before contact 2026-10-09 at study commit `4434a89b71cc9ff6de4ac502b8aa6a6d521f5893` (programme `docs/readiness/2026-10-09-slurp-nx-node-extreme-programme-v1.md` C2 R5 and F1
Stage J; decision 238 PROPOSED in `docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`; module step 7 `docs/readiness/2026-10-09-slurp-module-step7-v4g-default-v1.md`); both new cells **held**. Nothing here
authorises a flight, a flip or an admission entry.

**Status.** HELD. Decision 238 (close Stage S at the Solver node, compose Stage J = R5) is PROPOSED, not ruled, and the R1 iteration-2 verdict (does the Solver template enter the composition?) is pending. This package registers the composition decision A names WITHOUT a new Solver template; if the iteration-2 pick is delivered it is a swap (see the README), not a new cell.

## 1. The design

Two cells fly in ONE campaign chain on DEV-2000-ADDED (1,000 rows each, one official score each) after a four-row smoke:

1. the in-chain REPLICATE `slurp-native-stage3-module-comp1b-aa-dev2000-added-v1` (run `SAEA-SLURP-STAGE3-MODULE-COMP1B-AA-DEV2000-ADDED-V1`) -- the HELD module OFF-arm cell, reused AS
   REGISTERED (its own package `docs/readiness/2026-09-30-slurp-stage3-module-comp1b-dev2000-added-v1`, its own two DRAFT ledger rows, its own receipt). Module profile slurp, lock
   v2.1, every component off, full graph, delivery normaliser v3. Its recomposed config and protocol hashes equal the module
   package's registered ones (`registered-facts-v1.json`, `replicate_reuse`).
2. the COMPOSED arm `slurp-native-stage3-nx-r5-composed-dev2000-added-v1` (run `SAEA-SLURP-STAGE3-NX-R5-COMPOSED-DEV2000-ADDED-V1`, FIT `SAEA-SLURP-STAGE3-NX-R5-COMPOSED-DEV2000-ADDED-FIT-V1`; smoke `slurp-native-stage3-nx-r5-composed-dev2000-added-smoke-4-v1`, run
   `SAEA-SLURP-STAGE3-NX-R5-COMPOSED-DEV2000-ADDED-SMOKE-4-V1`): The evidence-consumption module saea-evidence-consumption-module-v1 (profile slurp) compiled onto lock v2.2 (module step 7: lock v2.1 with the delivery normaliser saea-deliver-normalise-v4g, version 1) with the Reviewer loop OFF (review_loop off: Perception then Solver, Planner and Reviewer iterations 0, max_revisions 0, no tool schema on any role; the compiled program phase-native-module-v1-c2, ceiling 2) and COMP-1b's two components ON -- agree-vote-seed (w_agree 1.0, recall k 60, THIS roster's vote table SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-DEV2000-ADDED-V1) and centroid-boundary-key (SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1) -- every other catalogued component OFF (no citation contract, no scope-rule stage, no re-listen, no Perception column, no template column). The Solver instruction template is the locked configs/probes/slurp_native_role_solver_v2.txt (sha256 18bff5c5...). Every policy block is the module compiler's output; the roster pins are DEV-2000-ADDED's own.

The composed cell is the HELD module COMP-1b cell with exactly these policy leaves moved (compiler output, proven in
`registered-facts-v1.json` `composed_config_diffs`, `anything_else` empty):

- `native_episode.consumption_module.lock`
- `native_episode.consumption_module.review_loop`
- `native_episode.deliver_normaliser.normaliser`
- `native_episode.max_revisions`
- `native_episode.review_loop`
- `native_episode.roles.planner.max_iterations`
- `native_episode.roles.reviewer.max_iterations`
- `phase_tools`
- `policy`

Decoding, knowledge stores, geometry (slurp-np4, session `serving-slurp-native-candidate-five-train-a-np4-v1`) and the roster pins are the module cell's own.

## 2. The swap point (the R1 iteration-2 pick)

The ONE-LINE swap point is `SOLVER_TEMPLATE_PIN` in `scripts/flights/nx/nx_r5_family.py` (today `configs/probes/slurp_native_role_solver_v2.txt`). If the R1 iteration-2 pick (`r1-i2-c*`, pinned under `configs/probes/nx/solver/r1/`) is NOMINATED and confirmed on Fold A, the coordinator changes that one line (and `SOLVER_TEMPLATE_SHA`) and re-runs `derive_slurp_nx_r5_cells.py` and `write_slurp_nx_r5_registration.py`. CAUTION, stated honestly: the module has NO registered composition today that delivers a non-locked Solver instruction template (the only components that write the Solver template are `solver-citation-contract`, refused on lock v2.2, and the slot-lookup opportunity, which is a tool path); the derive script therefore REFUSES any other value, by design. The swap needs a registered module step first (a lock layer or a `solver-template` leaf, like step 7), which is a code change outside this registration.

## 3. Is the replicate request-identical to the sealed A2 flight? NO, in two named leaves

`python -B scripts/analysis/module_equivalence_proof.py --at m0 m6` holds (`ok: true`). The replicate differs from the sealed A2 in-chain A/A
(`SAEA-SLURP-STAGE3-COMP1-AA-DEV2000-ADDED-V1`) by exactly `phase_material.reviewer.instruction_template` (the lock-v2.1 G5 Reviewer template, read no-harm / no-gain by `docs/results/2026-09-30-slurp-v2-1-lock-v1.md`) and
`knowledge_stores.intent-boundaries.phase_supply.perception.k` (60 -> 8, a proven supply no-op at w_agree 0, output digest `d57ee9d6...`); it is not the sealed A2 ARM either (that arm
has COMP-1b on). So the replicate is the instrument of the sealed A2 flight's BASE arm, and replicate-minus-A2-A/A is the flight-to-flight
offset measured on the same roster and rows, including those two leaves. The composed arm is review-off, so the Reviewer template
never renders on it; the composed-minus-A2-arm contrast is read beyond that offset (`docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md` rule 3).

## 4. Budgets (by analogy with the review-off cells)

| item | composed arm | composed smoke | replicate (as registered) |
| --- | ---: | ---: | ---: |
| rows | 1,000 | 4 | 1,000 |
| contacts per row (exact) | 2 | 2 | 11 ceiling (A2 flew 4.07) |
| generation calls cap | 2,000 | 8 | 11,000 |
| FIT endpoint cap (structural: rows x 2 x 4) | 8,000 | 32 | 44,000 |
| repeated speech-audio seconds cap | 5,968 | 17 | 32,819 |
| planned GPU hours (FIT inclusive) | 1.5 | 1.0 | 12.0 |

The chain total is the sum of the replicate's and the composed arm's caps. Measured A2 rates: the sealed arm 4,050 and the A/A 4,068
contacts per 1,000 rows (1.70 and 1.65 GPU-h); the composed arm's 2,000 contacts are exact.

## 5. The measurement and the three verdict meanings

`cross-flight-with-in-chain-replicate`, n = 1,000, primary official pooled SLU-F1 (`primary_metric_key: slu`), intent the guard,
`admission: no-harm`, `claims_benefit: false`, `harm_margin_pp 2.5` (not tighter than the cross-flight sampling floor
1.2525), bar 2.5 pp. Declared `expected_effect_pp` **+0.07**, honestly from the record:
review-off minus full graph -1.48 [-5.33, +2.72] (N100 read, unresolved) plus the v4g delivered gain
+1.55 [+0.81, +2.33] (offline, TRAIN Fold B lock column; applies to the composed side only in the delivered
contrast). That is far under the bar, so the cell claims NO benefit: its claim is **no loss at about half the contacts plus the v4g
delivered gain**.

Read in ONE chain: the replicate then the composed arm (campaign plan configs/campaign/slurp-native-stage3-nx-r5-composed-dev2000-added-v1.json). PRIMARY: official pooled SLU-F1 (slurp-slu-official), paired per utterance cluster (10,000 draws, seed 20260915), composed minus the sealed A2 arm (SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-V1). GUARD: intent (scenario_action exact), same contrast. OFFSET o: replicate minus the sealed A2 in-chain A/A (SAEA-SLURP-STAGE3-COMP1-AA-DEV2000-ADDED-V1), same metrics. THE BAR: 2.5 pp at n = 1,000 (instrument rule 3). NOMINATED iff the CI95 lower bound of (composed minus A2) on SLU-F1 is above |o| (beyond the replicate offset) AND the point estimate is at or above the 2.5 pp bar AND the intent guard shows no HARM; this is NOT expected (declared effect +0.07 pp) and would be a surprise to replicate before any use. NEUTRAL iff the CI95 lower bound of (composed minus A2) on SLU-F1 and on intent is at or above -2.5 pp (the preregistered harm margin) and the read is neither NOMINATED nor HARM: the composition keeps the full-graph accuracy within what a cross-flight read can see at about half the contacts -- still an efficiency result, never reported as a gain. HARM iff the CI95 upper bound of (composed minus A2) on SLU-F1 or on intent is below -|o| (a resolved loss beyond the flight offset, owner decision 25). A read whose lower bound is under -2.5 pp while neither HARM nor NOMINATED is UNRESOLVED (the design cannot rule out a margin loss) and is reported as such, not as NEUTRAL. Reported beside, CONTEXT ONLY and never the bar: composed minus the in-chain replicate (the whole composition against its same-chain base, intent and SLU-F1, with no offset correction needed); composed minus the sealed A2 in-chain A/A; the same contrasts with the v4g normaliser applied offline to the A2 and replicate columns so all columns are compared under v4g (isolating graph and supply from the normaliser); per-scenario tables in natural-mixture and equal-stratum weightings; the cost table. The verdict word is the coordinator's (owner decision 139).

What the words mean here:

- **NOMINATED** -- composed minus the sealed A2 arm has an SLU-F1 CI95 lower bound above the replicate offset and a point at or above the
  bar, with intent unharmed. Not expected; it would be a surprise to replicate, and it is the only word that authorises talking about a gain.
- **NEUTRAL** -- both contrasts' CI95 lower bounds are within the 2.5 pp margin and nothing is resolved either way: the
  composition keeps the full graph's accuracy within what a cross-flight read can see at about half the calls. Still an efficiency result.
- **HARM** -- the CI95 upper bound of composed minus A2 (SLU-F1 or intent) is below -|offset|: a resolved loss beyond the flight offset.
  A read that is neither but whose lower bound is under -2.5 pp is UNRESOLVED and is reported as such.

Declared exception to item D3, not hidden: the v4 rule set (fx-article, fx-oclock, scope, ti1, ee10) that saea-deliver-normalise-v4g extends was SELECTED offline on the A2 DEV pool (431 combinations + 10 single rules on DEV-2000-ADDED, COMP-1b delivered column; docs/results/2026-10-09-slurp-nx-postprocessing-v4-offline-read.md), which is this cell's read roster; it was confirmed on TRAIN Fold A, its guards were located on Fold A and checked on A2, and the lock was confirmed on TRAIN Fold B (docs/results/2026-10-09-slurp-postprocessing-v4g-lock-v1.md). The v4g delivered gain on this roster is therefore in-sample for the rule choice and descriptive only; the declared expectation quotes the Fold B confirmation. `tuning_roster` lists the rosters the composition's own constants were chosen on
(the construction pool, Fold A) and the `tuning_exception` field of the measurement block carries the v4 selection, because naming the read roster
in `tuning_roster` would make the launch gate report a blocking `tuning-read-overlap` that no registration can clear. The coordinator may rule
otherwise.

## 6. The read

`bash scripts/flights/nx/nx_r5_read.sh` (after both seals and the READ row's countersignature): passes `vs-aa` (composed minus the in-chain replicate;
context), `vs-comparator` (composed minus the sealed A2 arm; the registered claim), `offset-replicate-vs-a2aa` and `composed-vs-a2aa`;
the offline v4g columns on the A2 arm, the A2 A/A and the replicate; `scripts/analysis/nx_r5_v4g_contrast.py` for every cross-flight
contrast under v4g with per-scenario tables (natural-mixture and equal-stratum) and the cost table. Whole-utterance clusters, 10,000
draws, seed 20260915. The verdict word is the coordinator's.

## 7. What the coordinator does next

1. Rule decision 238 and wait for the R1 iteration-2 verdict; if the Solver template is delivered, take the swap in section 2 (needs a module step).
2. Root countersigns the DRAFT rows of THIS package (arm, arm FIT, smoke, smoke FIT) and of the module package for the replicate (run and FIT);
   the READ row after both seals.
3. Mint BOTH receipts: `python scripts/flights/nx/nx_r5_mint_receipt.py` (this package) and
   `python scripts/flights/module/module_comp1bdev_mint_receipt.py` (the replicate's, whose eligible list already names it).
4. `bash scripts/flights/nx/nx_r5_flip.sh` (loop form; re-pins smoke, replicate, composed arm to ONE converged HEAD; expected first-phase
   supply digests in `registered-facts-v1.json` `prepared_supplies`; the replicate re-pin may rewrite the module package's hashes if the
   instrument merges moved them -- it is the coordinator's flip).
5. `bash scripts/flights/nx/batch_chain_nx_r5.sh` (smoke, then the two-cell campaign, decision 77). Dry run before: `python -B scripts/flights/nx/nx_r5_dry_run.py`.
6. After both seals: countersign the READ row and run the read.

## 8. Open items

1. The replicate is the base-arm instrument of the sealed A2 flight (section 3), not an A2-ARM twin; the registered claim compares the composed
   arm with the A2 ARM beyond that offset. If the coordinator wants an A2-arm twin as the replicate, that is a different (COMP-1b ON, review-on)
   cell and a different chain.
2. Module step 7 left `CURRENT_LOCK` at v2.1. This package names `lock: v2.2` explicitly, so `CURRENT_LOCK` need not move. WHAT
   `scripts/checks/harness_admission_check.py` REPORTS (it reads `docs/receipts/harness-admission.json`, never experiment fragments): on the
   tree as registered, PASS (19 modules; no R5 entry exists, so the pair is not tested). Probed on a scratch copy of the receipt (nothing
   committed): the existing `module` entry with its ON arm replaced by the composed block (lock v2.2, review off) is REFUSED -- "switch.on
   composes onto lock 'v2.2'; the two arms of one module entry sit on ONE lock"; with the OFF arm ALSO on v2.2 it is refused twice -- the OFF
   arm "names lock 'v2.2'; the OFF arm of a 'module' entry names its carrier's CURRENT lock ('v2.1')" and the falsifier must name the OFF arm's
   lock -- so an R5 `module`-class admission entry needs `CURRENT_LOCK` moved to v2.2 (its OFF arm and falsifier cells then on v2.2, and the
   existing entry's v2.1 falsifier cells re-derived), a registration decision for the coordinator. The same composed block on lock v2.1
   (review off, v3) is ACCEPTED as an ON arm. Nothing in this package depends on that entry: it only matters if R5 NOMINATES.
3. The Solver-template swap needs a registered module step first (README section 2).
4. The v4 tuning exception above.
5. The replicate's two DRAFT ledger rows and its receipt live in the module package: both packages are countersigned and minted.
6. The structural contacts-per-row claim (2.0 against about 4.05) is arithmetic from the program and the A2 read, confirmed only at the read.

**Not authorised.** No flight before decision 238 is ruled and steps 1-4 hold; no re-flying of any sealed cell; no test, DEV-1000, Fold A or
Fold B contact; no policy change outside the declared block; no scope-rule or citation-contract on this block.
