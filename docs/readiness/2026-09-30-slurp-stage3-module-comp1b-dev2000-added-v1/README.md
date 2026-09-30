# The consumption module's first end-to-end cell: COMP-1b as a module block on lock v2.1 (DEV-2000-ADDED)

Registered before contact 2026-09-30 at study commit `aa053a2ea` (migration step 6 of
`docs/superpowers/specs/2026-09-29-slurp-consumption-module-design.md`; owner decisions 195, 196 and 204); all three cells **held**. Nothing here authorises a flight, a flip or an
admission entry.

**Does it need to fly?** This cell does NOT need to fly for the module's end-to-end proof: the byte proof (m6) shows its composed policy blocks equal cell A2's flown arm bytes except the one lock-v2.1 Reviewer pin, and its A/A equals the lock-v2.1 bytes. What a flight would add is (a) the first measured lock-v2.1 A/A on DEV-2000-ADDED and (b) a same-roster re-flight of the admitted COMP-1b bytes under the module on lock v2.1. Whether that is worth about 3.4 GPU-h is the coordinator's decision.

**Why.** Migration step 6 re-expresses new registrations as module blocks. The first composed component list is COMP-1b
(`agree-vote-seed` + `centroid-boundary-key`), admitted by the A2 read ([`docs/results/2026-09-30-slurp-a2-comp1b-dev2000-read.md`](../../../docs/results/2026-09-30-slurp-a2-comp1b-dev2000-read.md)):
intent +4.60 pp CI95 [+2.58, +6.73], official SLU-F1 +0.53 pp [-1.04, +2.09] against the in-chain A/A (A2 REPLICATED and ADMITTED, lock v2.0 bytes). Lock v2.1 ([`docs/results/2026-09-30-slurp-v2-1-lock-v1.md`](../../../docs/results/2026-09-30-slurp-v2-1-lock-v1.md)) is the base of every cell registered after A2 sealed.

**What it is.** The evidence-consumption module saea-evidence-consumption-module-v1 (profile slurp) compiled onto lock v2.1 (owner decision 204: the v2.0 lock with ONE pin moved, the Reviewer template probes/slurp_native_role_reviewer_v1_g5_v1.txt) with COMP-1b's two components ON -- agree-vote-seed (w_agree 1.0, recall k 60, delivered 8-1-8, THIS roster's vote table SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-DEV2000-ADDED-V1) and centroid-boundary-key (SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1) -- and every other catalogued component OFF. Every policy block is the compiler's output; the roster pins are DEV-2000-ADDED's own. Each cell's baseline fragment DECLARES `native_episode.consumption_module`; the loader
(`rails.native_episode_config`) refuses the config unless its policy blocks are exactly what the block compiles to.
Derived by `scripts/flights/module/derive_slurp_module_comp1bdev_cells.py`.

**The byte proof (AT-M6, `python -B scripts/analysis/module_equivalence_proof.py --at m0 m6`).** Each cell's own block compiles to its own composed
hash; compiled onto cell A2's own fragments, it differs from A2's policy blocks at exactly these leaves:

| cell | experiment | composed hash | rebuilt == own | policy leaves differing from the A2 counterpart |
| --- | --- | --- | --- | --- |
| arm | `slurp-native-stage3-module-comp1b-dev2000-added-v1` | `1f1208d9540051d4...` | True | `phase_material.reviewer.instruction_template` |
| smoke | `slurp-native-stage3-module-comp1b-dev2000-added-smoke-4-v1` | `67d8be44ead7d882...` | True | `phase_material.reviewer.instruction_template` |
| aa | `slurp-native-stage3-module-comp1b-aa-dev2000-added-v1` | `4772f6811c7b71fb...` | True | `knowledge_stores.intent-boundaries.phase_supply.perception.k`, `phase_material.reviewer.instruction_template` |

The full composed-config diffs against A2 (`registered-facts-v1.json`, `composed_config_diffs`) add only the module
declaration block, bookkeeping (`native_contact_fit` ids, `prepared_phase_supply`, `what_this_is`, the smoke's
`fragment_kind`) and the experiment fragment's own block. The A/A's recall k moves 60 -> 8 because A2's A/A carried k 60
at w_agree 0 (a proven supply no-op, digest `d57ee9d6...`) and the module's OFF arm is the lock (k 8). AT-M0 now targets
lock v2.1 (cell G5's flown hashes) and keeps the v2.0 case beside it.

**In-chain A/A.** `slurp-native-stage3-module-comp1b-aa-dev2000-added-v1` = the module's OFF arm (every component off) on lock v2.1 -- the first lock-v2.1 A/A;
the campaign plan `configs/campaign/slurp-native-stage3-module-comp1b-dev2000-added-v1.json` flies it and then the arm (instrument rule 3).

**Measurement.** `cross-flight-with-in-chain-replicate`, n = 1,000, intent primary (`primary_metric_key: intent`),
`claims_benefit: true`, claim `nominated`, `expected_effect_pp` **4.6** (the A2 read's intent point, measured on
lock v2.0 bytes), official SLU-F1 the guard at this roster's own null h_SLU 1.2525 (h_intent
1.152); bar about 2.6 pp at n = 1,000.

**Runs.** `SAEA-SLURP-STAGE3-MODULE-COMP1B-DEV2000-ADDED-V1` / `SAEA-SLURP-STAGE3-MODULE-COMP1B-DEV2000-ADDED-FIT-V1`; `SAEA-SLURP-STAGE3-MODULE-COMP1B-AA-DEV2000-ADDED-V1` / `SAEA-SLURP-STAGE3-MODULE-COMP1B-AA-DEV2000-ADDED-FIT-V1`; `SAEA-SLURP-STAGE3-MODULE-COMP1B-DEV2000-ADDED-SMOKE-4-V1` / `SAEA-SLURP-STAGE3-MODULE-COMP1B-DEV2000-ADDED-SMOKE-4-FIT-V1`. READ `SAEA-SLURP-STAGE3-MODULE-COMP1B-DEV2000-ADDED-PAIRED-ANALYSIS-V1`.

**If the coordinator decides to fly it.** (1) Root countersigns the seven DRAFT rows (arm, arm FIT, A/A, A/A FIT, smoke,
smoke FIT, READ) and mints `coordination/slurp-stage3-module-comp1b-dev2000-added-v1/root-admission-v1.json` with `scripts/flights/module/module_comp1bdev_mint_receipt.py` (six
eligible run ids). (2) `scripts/flights/module/module_comp1bdev_flip.sh` re-pins smoke, A/A and arm until the package
converges at one HEAD; each re-minted supply must reproduce its expected output digest. (3)
`scripts/flights/module/batch_chain_module_comp1bdev.sh` queues the smoke then the A/A + arm campaign on the np4 session
(decision 77). (4) After both seals the READ row is countersigned and `bash scripts/flights/module/module_comp1bdev_read.sh`
reads it.

**Not authorised.** No flight before the coordinator's decision and steps 1-2; no re-flying of any sealed cell; no test,
DEV-1000 or Fold B contact; no policy change outside the declared block.

## Coordinator ruling (Fable 5.1, 2026-09-30)

The byte proof `scripts/analysis/module_equivalence_proof.py --at m6` (arm == cell A2 except the G5 Reviewer
instruction template; in-chain A/A == lock v2.1; the smoke equal to the arm but for its smoke bookkeeping) is
accepted as the consumption module's first end-to-end proof (merge `9ccf62e2`; m0, m1, m2, m4 and m6 all `ok`).
The cells stay **HELD** and are **NOT queued**: the GPU priorities are the milestone test-sample read (owner
decision 207) and P-SV-4 (owner decision 208). A measured lock-v2.1 A/A on DEV-2000-ADDED is deferred until a composed
read on lock v2.1 needs it. No countersignature, mint, flip or re-pin follows from this ruling.
