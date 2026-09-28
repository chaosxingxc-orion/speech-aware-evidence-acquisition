# Preregistration: cell W3 as W3a alone -- intent contrast cards (TRAIN Fold A 1,080)

Registered before contact 2026-09-28T00:25:55.000000+00:00 at study commit `e9b4a8ee` by the W3 registration agent
(worktree `/home/chao/saea-worktrees/fable-waveaa`, branch `fable/waveaa`). Owner decision 164. The package README
(`docs/readiness/2026-09-27-slurp-stage3-w3-contrast-fold-a-v1/README.md`) carries the evidence, the card format, the tuning table and the Fold A table; this note fixes
the question, the arms, the rule and the fence. RE-REGISTERED 2026-09-28T00:25:55.000000+00:00 in place of the first registration
(W3a + W3b, study commit `701bd63a`): Coordinator ruling (Fable 5.1, 2026-09-27) under owner decision 164's one-change rule: the wave's W3 cell is re-derived as W3a ALONE -- the intent contrast cards with the Solver exemplar supply restored to exactly the AGREE arm's (no per-intent exemplar cap). W3b is dropped as a second change with no measured upside: (1) on Fold A the cap removes 0 wrong-intent pluralities on the 153 intent-wrong rows (docs/readiness/2026-09-27-slurp-stage3-w3-contrast-fold-a-v1/offline-estimates-v1.json fold_a_estimates.exemplar_cap.wrong_rows.wrong_plurality_removed); (2) on Fold B the chosen cap N = 11 scores GAIN 0 / HARM 0 (docs/readiness/2026-09-27-slurp-stage3-w3-contrast-fold-a-v1/offline-estimates-v1.json fold_b_tuning.table["11"]); (3) it changes 700 Solver blocks on the 927 rows the AGREE arm got right, lowering the gold exemplar count on 665 (docs/readiness/2026-09-27-slurp-stage3-w3-contrast-fold-a-v1/offline-estimates-v1.json fold_a_estimates.exemplar_cap.right_rows.block_changed / gold_count_down).

## The question

With the intent cards carrying TRAIN-derived contrast lines in place of boilerplate (no more tokens per card) and nothing else changed (W3a alone; the Solver exemplar block is the AGREE arm's own), do the official intent accuracy and pooled SLU-F1 on TRAIN Fold A 1,080 stay within the design's own null, read against the shared wave-1 in-chain A/A? A no-harm question, because no measured conversion applies (row 139).

## The arms

- **W3 arm** `SAEA-SLURP-STAGE3-W3-FOLD-A-V1` (cell `slurp-native-stage3-w3-fold-a-v1`, composed `55bf8f6c8b11d2134155e3e9187be679256696c23fa95fde69dc3035818b7ec2`, protocol `30e287d1cdad308f1521c00fe53fdbffa5b69a9a73901809e838b41d655c4564`):
  the retained AGREE arm with ONE change (W3a alone): the intent-boundaries store moves to intent-boundaries-contrast-v1: header, activation boundary, authored exclusion and card-specific limitations verbatim; the shared uncertainty sentence and the shared limitation bullet removed; a contrast section against the card's nearest TRAIN-centroid rivals added. The Solver exemplar supply is
  the AGREE arm's own; the first registration's per-intent cap (W3b) is dropped.
- **Shared in-chain A/A** `SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1`: registered by the coordinator, flown in the same chain.
- **Comparator** `SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1` (sealed AGREE arm, official intent 85.8333 / SLU-F1
  65.1575): context beside the A/A, never re-flown, never the bar.
- **Four-row smoke** `SAEA-SLURP-STAGE3-W3-FOLD-A-SMOKE-4-V1`: form only, never scored.

## The rule

NO-HARM READ (owner decision 164 brief, row 139): against the SHARED wave-1 in-chain A/A SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1 flown in the same chain, the paired CI95 lower bound of the intent-accuracy delta (primary, decision 133) is not below -0.9943 pp AND the paired CI95 lower bound of the official pooled SLU-F1 delta (the guard) is not below -1.2485 pp -- each metric read at its own Fold A own-null half-width (docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md section 2d). HARMFUL: a measured loss on either metric (CI95 upper bound below zero, decision 25). A CI that includes zero and clears the margin is the admission. The cell is NEVER reported as a gain whatever the point estimate: no measured conversion applies to contrast text, so no expected effect is declared (decision 139). Every verdict carries the per-scenario table in both weightings, the frontier row (decision 75), the row-level attribution of the delta to the rows the contrast lines newly name (membership fixed in offline-estimates-v1.json before contact), and the A/A's own delta against the sealed AGREE arm as the instrument's reading.

## The expectation

Row 139: an expectation may be declared only from a measured conversion analogue. The two measured conversions on this programme are DELIVERY conversions of the gold boundary card to Perception (CONV 32 of 70 = 0.457143, KPROBE 24 of 55 = 0.436364). W3a delivers nothing new -- the delivered set is the AGREE arm's own, byte for byte -- it changes what an already-delivered card SAYS, and no contrast text has ever been flown and read. The analogue does not apply, so the cell is registered as a no-harm read and says so. The 2026-09-27 re-registration as W3a alone keeps this declaration: the package declares no separate W3a number from a measured basis.

## The measurement fence

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-STAGE3-W3-FOLD-A-SMOKE-4-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "Four rows prove FORM and nothing else: that the contrast release loads, that every request fits and that the episode completes. Scored by no one, read by no one (instrument rule 5).",
      "primary_metric": "none (structural form only)",
      "rows": 4
    },
    "SAEA-SLURP-STAGE3-W3-FOLD-A-V1": {
      "admission": "no-harm",
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "harm_margin_pp": 1.2485,
      "harm_margin_pp_by_metric": {
        "intent_accuracy": 0.9943,
        "slu_f1": 1.2485
      },
      "measurement_design": "cross-flight-with-in-chain-replicate",
      "note": "A knowledge-content cell registered as a NO-HARM read because no measured conversion applies (row 139; registered-facts-v1.json expectation). The harm margin is the measured floor of this design at n = 1,080 -- the Fold A own-null half-width, SLU 1.2485 (the gate's single field) and intent 0.9943 (the primary metric's own, applied by the read). The delta is read against the SHARED wave-1 in-chain A/A SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1, registered by the coordinator and flown in the same chain (rule 3), never against the sealed AGREE arm alone. Never reported as a gain.",
      "primary_metric": "intent accuracy (scenario_action exact), official pooled SLU-F1 the non-inferiority guard (owner decision 133)",
      "replicate_run_id": "SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1",
      "rows": 1080
    }
  }
}
```

## Boundary

Development numbers only (owner decisions 28 and 86). No test-split or DEV read; TRAIN Fold B was read OFFLINE, gold
labels and pinned vectors only, to tune the cap that is no longer flown. No utterance text, gold string, knowledge body or model output is
committed. The shared A/A, the flip and the flight are the coordinator's.
