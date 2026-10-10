# Cell VER-1c: the R1 c3 Solver template column on TRAIN Fold A, the verdict source of the VER-1 rule (owner decision 257, decision 258 option A) -- HELD

Registered 2026-10-10, before any contact, by `scripts/flights/ver/ver1c_derive_cells.py` and
`scripts/flights/ver/ver1c_write_registration.py`. HELD: nothing here authorises a flip, a flight or an admission entry. Decision 258
(option A) is PROPOSED, not ratified; the ledger rows are DRAFT until root countersigns them.

## What it is

The VER-1 rule contains the c3 presence verdict (the Solver, under the R1 `r1-c3` template, answered no entity after v4g) gated by the
pre-Solver signature N1 >= 0.2. On TRAIN Fold B the verdict came from the NX R1 flights; on TRAIN Fold A no c3 column exists. VER-1c is
an E1 same-flight Solver-template column on `SLURP-EVO-FOLD-A-V2` (1,080 rows) with ONE candidate arm:

| arm | role | template |
| --- | --- | --- |
| `r1-c3` | the candidate: explicit empty-entity decision (decision 199) | `configs/probes/nx/solver/r1/r1-c3.txt`, sha256 `89b81e97c0c8d5377eff2892fac548ac83fd6a24f61ceb25396a57196bb262dc` -- the SAME bytes the NX R1 iteration-1 cell flew (checked against `docs/readiness/2026-10-09-slurp-nx-r1-solver-candidates-v1/README.md` by `ver1c_family.candidate_pins`) |
| `aa` | the in-chain twin, `replicate_of lock` | the locked template |
| `lock` | the delivering arm, last | `configs/probes/slurp_native_role_solver_v2.txt` (untemplated) |

Base: the COMP-1b composition (agree-vote-seed + centroid-boundary-key ON) as a consumption-module block on lock v2.2 (v4g at delivery),
Reviewer loop OFF, no tool schema on any role; the Fold A pins are those of the committed COMP-1b Fold A fragments. The arm is a
VERDICT SOURCE, not a nomination: `same-flight-node-column`, `template_variants {node solver, candidate_arms 1, twin true}`,
`claims_benefit` false, expected effect 0.0 pp, `stage3_algorithm` `none` (as the R1 cells). The delivering arm is the lock, so the
delivered answer is unchanged (invariant I7).

## Contact arithmetic

E1: ceiling = base + (K - 1) with base 2 (Perception 1 + Solver 1) and K = 3 arms (`r1-c3`, `aa`, `lock`) = 4; program
`phase-native-module-v1-c4` (a registered family member). Per row: 1 Perception + 3 Solver contacts. Arm: 1,080 x 4 = 4,320 generation
calls; FIT 1,080 x 4 x 4 = 17,280 (structural); speech seconds `ceil(roster audio x 4)` = 12,339. Smoke: 16 calls; FIT 64. GPU hours
planned 1.8 (arm; the R1 iteration-1 plan was 3.5 for 8,640), 1.0 (smoke).

`template_frame` (`max_supplied_items` 55, `fit_estimate` base 2,000 / 235 per item / completion 512 / slot 24,576, `twin` true) and the
`r1-c3` token count (434) are the R1 iteration-1 fit measure's, which was MEASURED on the COMP-1b Fold A first Solver visits
(`docs/readiness/2026-10-09-slurp-nx-r1-solver-fold-b-v1/fit-measure-v1.json`, source run `SAEA-SLURP-STAGE3-COMP1B-FOLD-A-V1`): the
r1-c3 arm prompt estimate is 15,359 against the 20,990 limit. They are therefore the measured numbers of THIS roster, not a proxy. No new
tokenizer pass is made at registration (a tokenizer pass is a server contact).

## Exposure disclosure

The R1 candidates were authored from AGGREGATE contrast tables computed on TRAIN Fold A (the R1 tuning roster), which is this cell's read
roster; the c3 template was then measured on Fold B. The rule it feeds was fixed on Fold B. The Fold A read is a confirmation of the RULE
on a roster the rule's thresholds never saw, but not an independent roster for the c3 TEMPLATE's authoring tables. The measurement block
names the rule's tuning roster (Fold B) because naming Fold A would raise a blocking `tuning-read-overlap`; the disclosure text is in the
block's note, the preregistration and the ledger rows.

## Order of operations (root)

countersign the four DRAFT flight rows (the READ row stays a draft until the seal) -> `scripts/flights/ver/ver1c_mint_receipt.py` ->
merge the engineering branch (no concurrent flip; no other experiment in flight) -> `scripts/flights/ver/ver1c_flip.sh` ->
`scripts/flights/refresh_registered_plan_pins.py` -> flip again -> `scripts/flights/ver/ver1c_dry_run.py` (root: needs the data root) ->
`scripts/flights/ver/ver1c_batch_chain.sh`. `--allow-output-change` must never be passed. After the seal, the READ recipe scores the three
arms once each (`stage3_rollout_score.py --mode supply-variants`), which writes the supply-variants files that
`scripts/analysis/slurp_ver1_offline.py --verdict-run` reads (see the VER-1b README, "The combined read").

## Open items

* No wrapper script for the READ yet: `scripts/analysis/nx_r1_read.sh` is R1-specific (run ids, seven arms); one is cloned at
  countersign time. The composer needs only the supply-variants scores, produced by the first stage.
* Whether the Fold A c3 verdict-empty row count matches the Fold B figures of the R1 flights is reported by the READ; it gates nothing.
