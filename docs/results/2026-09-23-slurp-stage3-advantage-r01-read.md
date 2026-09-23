# Cell ADV-1 structural read: the SYSTEM-level semantic-advantage contact on the 225 disagreeing ROLL-1 rows (Stage-3 S3-4 / S3-4s; owner decisions 82, 101, 106)

Read 2026-09-23 by the coordinator (Fable 5.1) from the sealed run `SAEA-SLURP-STAGE3-ADVANTAGE-R01-V1` / `attempt-slurp-native-stage3-advantage-r01-v1-generation` (FINALIZED at flight commit b9c9ff71, scheduled task SAEA-Batch-Chain-ADV1, 2026-09-23 10:48:55-10:52:37 UTC, one attempt, manifest COMPLETED; run-manifest sha256 `a63f9fdd20fff0d388ce13d24d86402f43b95acd896851c307d4c68befb1ae41`, outputs `9763f8ca6ce32d897b157197de32fa75c6b64e52c77b3f5f2fcf0c347156176e`). Algorithm label `tfgrpo-semantic-advantage-v1` (credit assignment). Counts only; no statement text, no gold, no utterance text. Structural read by the preregistration's decision rule (section 5): no effectiveness claim; the effect of the resulting deltas is read at CELL-1 against the sealed PLAN arm (decision 99 order).

## 1. Flight facts

| item | value |
| --- | --- |
| rows / contacts | 225 / 225 (one contact per row, ceiling 1) |
| four-row form smoke | `SAEA-SLURP-STAGE3-ADVANTAGE-R01-SMOKE-4-V1`, recovery attempt `...-smoke-4-v1-generation-recovery`, 4 / 4 rows, structural PASS, 10:48 UTC (the first launch at 09:35 UTC was refused by the transport before any contact; see the ledger row) |
| metered cost | prompt tokens 122,389; completion tokens 19,345; speech seconds metered 1,025.29 (the roster's audio, charged by `record_usage` although the contact is text-only and sends zero audio parts); about 0.07 GPU-h |
| serving | resident session `serving-slurp-native-candidate-five-train-a-np4-v1` (np4 x 24,576, max512), attached, never spawned or stopped; the construction-visible text payload rendered through the transport's dedicated text-only branch (item of 2026-09-23, commit d084fb08) |
| dispositions | none (no abstention, no truncation-triggered disposition) |

## 2. Parse (the decision rule)

| item | value |
| --- | --- |
| legal statement sets | **225 / 225 (100 %)**, all in the registered JSON form; illegal blocks 0 |
| blocks per row | 1: 130 rows; 2: 19 rows; 3: 76 rows; total 396 blocks |
| NODE distribution | perception 124, solver 159, reviewer 99, planner 14 |
| DELTA-KIND distribution | slot-contract 155, intent-boundary 121, reviewer-criterion 99, planner-rule 13, exemplar-note 6, perception-hint 2 |

Reading: the contact attributes 31 % of its statements to the Perception node and 25 % to the Reviewer, i.e. more than half of the credit assignment lands OUTSIDE the Solver — the system-level signal decision 106 asked for. `perception-hint` is rare (2) although Perception statements are common (124): the model expresses Perception-side lessons as intent-boundary statements, which the per-node route still delivers to the Perception phase only through the unconditional `perception-hint` list; the curation report of S3-5 must show how many Perception-node statements reach any node.

## 3. Records

Four exposure-ledger rows closed (`SAEA-SLURP-STAGE3-ADVANTAGE-R01-{SMOKE-4-,SMOKE-4-FIT-,,FIT-}V1`); next: S3-5 curation and release (`scripts/flights/batch/adv1_to_deltas.sh`) into `stage3-deltas-v1` and its twin, then CELL-1 + twin on TRAIN A against the sealed PLAN arm.
