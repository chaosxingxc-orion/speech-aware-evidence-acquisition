# Preregistration: cell W3 -- intent contrast cards + a per-intent exemplar cap (TRAIN Fold A 1,080)

Registered before contact 2026-09-27T16:30:00.000000+00:00 at study commit `359df4c9` by the W3 registration agent
(worktree `/home/chao/saea-worktrees/fable-w3`, branch `fable/w3`). Owner decision 164. The package README
(`docs/readiness/2026-09-27-slurp-stage3-w3-contrast-fold-a-v1/README.md`) carries the evidence, the card format, the tuning table and the Fold A table; this note fixes
the question, the arms, the rule and the fence.

## The question

With the intent cards carrying TRAIN-derived contrast lines in place of boilerplate (no more tokens per card) and the Solver's exemplar block capped at 11 per intent (still 20 exemplars), do the official intent accuracy and pooled SLU-F1 on TRAIN Fold A 1,080 stay within the design's own null, read against the shared wave-1 in-chain A/A? A no-harm question, because no measured conversion applies (row 139).

## The arms

- **W3 arm** `SAEA-SLURP-STAGE3-W3-FOLD-A-V1` (cell `slurp-native-stage3-w3-fold-a-v1`, composed `7fb4ac8be839915f22540c8e0534fd6da39f8a1f3faee3afe43397c2888d8440`, protocol `7ab0b5e542e430f73a62654d80e702ecdcedab37227a27bdd843af6b0dfdb71f`):
  the retained AGREE arm with (W3a) the intent-boundaries store moves to intent-boundaries-contrast-v1: header, activation boundary, authored exclusion and card-specific limitations verbatim; the shared uncertainty sentence and the shared limitation bullet removed; a contrast section against the card's nearest TRAIN-centroid rivals added; and (W3b) the Solver's train-exemplars supply moves from saea-fuse-supplyfilter-v1 at k 20 to saea-fuse-supplyfilter-target-cap-v1: walk the pure-cosine ranking, take at most 11 exemplars per intent, stop at 20; admission depth and recall k 300.
- **Shared in-chain A/A** `SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1`: registered by the coordinator, flown in the same chain.
- **Comparator** `SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1` (sealed AGREE arm, official intent 85.8333 / SLU-F1
  65.1575): context beside the A/A, never re-flown, never the bar.
- **Four-row smoke** `SAEA-SLURP-STAGE3-W3-FOLD-A-SMOKE-4-V1`: form only, never scored.

## The rule

NO-HARM READ (owner decision 164 brief, row 139): against the SHARED wave-1 in-chain A/A SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1 flown in the same chain, the paired CI95 lower bound of the intent-accuracy delta (primary, decision 133) is not below -0.9943 pp AND the paired CI95 lower bound of the official pooled SLU-F1 delta (the guard) is not below -1.2485 pp -- each metric read at its own Fold A own-null half-width (docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md section 2d). HARMFUL: a measured loss on either metric (CI95 upper bound below zero, decision 25). A CI that includes zero and clears the margin is the admission. The cell is NEVER reported as a gain whatever the point estimate: no measured conversion applies to contrast text or to exemplar composition, so no expected effect is declared (decision 139). Every verdict carries the per-scenario table in both weightings, the frontier row (decision 75), the row-level attribution of the delta to the rows the contrast lines newly name and to the rows the cap newly gives a gold exemplar (membership fixed in offline-estimates-v1.json before contact), and the A/A's own delta against the sealed AGREE arm as the instrument's reading.

## The expectation

Row 139: an expectation may be declared only from a measured conversion analogue. The two measured conversions on this programme are DELIVERY conversions of the gold boundary card to Perception (CONV 32 of 70 = 0.457143, KPROBE 24 of 55 = 0.436364). W3a delivers nothing new -- the delivered set is the AGREE arm's own, byte for byte -- it changes what an already-delivered card SAYS, and no contrast text has ever been flown and read; W3b changes the composition of a block delivered to the SOLVER, a different node and channel from the one CONV measured. Neither analogue applies, so the cell is registered as a no-harm read and says so.

## The measurement fence

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-STAGE3-W3-FOLD-A-SMOKE-4-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "Four rows prove FORM and nothing else: that the contrast release loads, that the capped Solver block still delivers twenty exemplars, that every request fits and that the episode completes. Scored by no one, read by no one (instrument rule 5).",
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
labels and pinned vectors only, to tune the cap. No utterance text, gold string, knowledge body or model output is
committed. The shared A/A, the flip and the flight are the coordinator's.
