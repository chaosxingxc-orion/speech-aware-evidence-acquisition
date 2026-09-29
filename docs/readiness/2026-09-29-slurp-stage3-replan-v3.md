# Stage-3 re-plan v3: the next experiment rounds and the training-free RL changes (2026-09-29)

Author: Fable 5.1 (root coordinator; planning, decomposition, review). Supersedes
`docs/readiness/2026-09-27-slurp-stage3-replan-v2.md` (kept in place as the record). Inputs: the 2026-09-29 result notes
under `docs/results/` (same-flight floor re-calibration, W-SV-1 and W4-SV column reads, sealed-credit inner loop run 1,
SLU consumption headroom offline, COMP-1 resume-3 seal-abort diagnosis, filler c01/c02 pool read, RANKVIS probe), the
2026-09-28 node information-gain ledger, and owner decisions 181-194 (registry
`docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`). Every number is a development number (decisions 28,
86) and is quoted from the file named beside it; nothing here authorises a flight, a flip or an admission.

## 1. What the survey and the instrument settle

1. **The instrument is now measured, not provisional.** Cross-flight designs cost 2.5 pp at n = 1,080 (instrument note
   `docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md`). Same-flight floors, per metric under owner
   decision 190: intent 0.65 pp and SLU-F1 1.49 pp at n = 1,080 (`scripts/checks/stage3_effect_floor_check.py`, sources
   `docs/results/2026-09-29-slurp-same-flight-floor-recalibration.md` -- W-SV-1 contrast half-widths intent 0.5093 / SLU
   1.4866 -- and `docs/results/2026-09-29-slurp-w4sv-fold-a-column-read.md` -- intent 0.65); shadow-relisten cells are
   floored on SLU only; `primary_metric_key` is required on benefit-claiming same-flight cells from 2026-09-30. Twin
   nulls: intent offset +0.00 on W-SV-1 and +0.09 on W4-SV; SLU twin offset +0.37 (half-width 0.5324) on W-SV-1 and
   +0.43 on W4-SV (same two notes).
2. **W-SV-1 (Solver train-exemplars k 30) is inert**: SLU-F1 -0.46 pp CI95 [-1.85, +1.12] against a twin null of
   +0.37 (`docs/results/2026-09-29-slurp-wsv1-fold-a-column-read.md`).
3. **W4-SV (slot-convention release swap) is not resolvable**: SLU-F1 -0.15 pp CI95 [-1.40, +1.11] against a twin null of
   +0.43; with W4, two reads under the floor. The rule-card slot-convention line is CLOSED (owner decision 191).
4. **Inner loop run 1 nominates nothing under decision 190**: its k = 10 candidate (+0.48 pp intent) sits under the
   re-calibrated floor (`docs/results/2026-09-29-slurp-sealed-credit-inner-loop-run-1.md`). The same note re-derives the
   node ledger's decision structure: P(Solver first answer correct | Perception rank 1) 97.57 %, rank 2 26.98 %.
5. **SLU headroom**: no SLU mechanism reaches the 1.5 pp registration bar of decision 192 at a measured conversion (best
   composition about 1.28 pp); consumption is 214 of 407 items, and 107 of the 229 undetermined items already had the
   gold value supplied; W5's expected effect is 0.15 pp, so its line is closed by the coordinator; a deterministic
   do-not-tag scope rule reads +1.04 [+0.53, +1.57] pp offline, replicate +0.93
   (`docs/results/2026-09-29-slurp-slu-consumption-headroom-offline.md`). Its admission bar is the open decision 195.
6. **The named blank for 95**: gold is off the Perception list on 83 of the 153 wrong AGREE rows, 49 of them still in the
   boundary block (`docs/results/2026-09-28-slurp-node-information-gain-ledger.md`). This boundary-recall gap is not
   addressed by any registered cell.
7. **Closed lines** (do not re-fly): everything closed in v2, plus rule-card slot conventions (191), W5 slot-side
   retrieval (192, coordinator; the owner may reopen) and the Reviewer TF-RL second round for now (188, deferred).

**Engineering landed since v2** (all merged on master): the P-SV presentation/min_candidates wiring and the contrast-pair
table v2 (ruling O7; 1035 of 1078 P-SV-1 rows covered, 96.0 %,
`docs/readiness/2026-09-29-slurp-stage3-psv1-fold-b-v1/registered-facts-v1.json`); the branch-seed fix and its re-pin
identity fix (merges d81b8ad45, 4b1283e0b); the E4-1 seal-invariant fix (b286d8974, merge 109538e87); the shared
`read_lib.sh` countersign-gate loader (merge 3adf05958); the `__pycache__` purge before every re-pin pass (ead01140e); the
per-metric floors of decision 190 (merge c2f1be08a).

## 2. The rounds

One resident geometry at a time; SLURP only on the card (decision 187); filler rollouts on Fold B take every gap.

| # | round | reads against | status |
| --- | --- | --- | --- |
| R1 | P-SV-1 (top-2 contrast) and P-SV-2 (forced three-candidate list), TRAIN Fold B, level 2, claim `nominated` | twin null, floors of decision 190 | flying as SAEA-Queue-PSV (decision 193) |
| R2 | COMP-1 seal-only completion (0 GPU) + G5 | shared in-chain A/A; COMP-1 declared 3.23 | flipped at fd8a01fe1, queued as SAEA-Queue-SEALONLY behind P-SV (decision 189) |
| R3 | E4-1 seal-only completion (0 GPU) | pre-declared column gate on the READ row | receipt minted; flip refused on the parent-config residue; after the fix on fable/repinresume (decision 194) |
| R4 | COMP-1 / G5 read | in-chain A/A | after R2 seals |
| R5 | A2: COMP-1 replication on DEV-2000-ADDED (arm + A/A); expected effect declared from R4 only | in-chain A/A, h 1.1520 intent | placeholder package; the declaration is the floor check's one blocking finding until then |
| R6 | P-SV reads | twin null | after R1 seals |
| R7 | Composed Perception policy (top-2 contrast and/or forced-3, per R6) as the dev-admitted candidate; the scope rule enters here if decision 195 = B | DEV read of the composed arm | after R5 and R6 |
| R8 | Milestone test-sample read (decision 151) | -- | on the owner's go after a dev-admitted composed arm |
| R9 | E3 progressive slot loading | same-flight instrument | after the E4 reads |
| R10 | Inner loop run 2 on the P-SV, E4 and filler pools | floors of decision 190 | after R3 and R6 |
| R11 | Audio2Tool and Earnings rounds of v2 (C2, C3) | as v2 | after the SLURP lock (decision 187) |

No if-then on unread results (decision 139). Admission rule unchanged: an item enters COMP-2 (decision 138) only after
its predecessor is replicated or root-caused.

## 3. Training-free RL: shortfalls and changes

| shortfall (measured) | change | instantiated by |
| --- | --- | --- |
| Supply-side knobs are exhausted: W-SV-1 inert, W4/W4-SV under the floor, inner loop run 1 no nomination | Move the policy space to the deciding node's form: contrast and candidate-count actions at Perception | P-SV-1 / P-SV-2, then the composed Perception policy |
| SLU mass is consumption, not supply (107 of 229 undetermined items had the gold value supplied) | Register no SLU supply mechanism below the 1.5 pp offline prediction (decision 192); prefer deterministic node actions derived from offline diagnostics | the scope rule, subject to decision 195 |
| The inner loop tunes on the pools it has; its twelve pools share one decision structure | Feed run 2 with the new pools (P-SV branches, E4 shadow columns, filler) | R10 |
| Boundary recall: 83 off-list rows, 49 in the boundary block | Name it as the open blank for 95; no cell until a mechanism has an offline prediction above the floor | -- |
| Seal-only cells are treated as historical by the registration gate; their receipts are checked only by the flip scripts | Engineering item: the registration gate checks seal-only receipts directly | engineering base |

## 4. Coordinator checkpoints (script-run, not prose)

- Every launch: `flight_registration_check.py`, `cli check`, the offline gates, and the handoff freshness stamp.
- Before R3 flips: the parent-config residue fix is merged, and the E4-1 re-pin converges in two passes.
- Before R5 flips: the expected effect is declared from R4's read only, replacing the placeholder that the floor check
  blocks today.
- Before R7 registers: its `primary_metric_key` is declared (decision 190) and its components cite their own reads.

## 5. Decisions the owner is asked for

1. **Decision 195**: the bar for the deterministic do-not-tag scope rule (+1.04 pp offline). Option A: a normaliser-class
   form change read no-harm cross-flight on DEV-2000 (2.5 pp bar; it would not clear). Option B: a USE-layer
   deterministic node action admitted into the COMP-2 composed policy and read only inside the composed arm's DEV read.
   Recommended: B.
