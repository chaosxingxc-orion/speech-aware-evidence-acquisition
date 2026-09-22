# SLURP base v2.0: PROVISIONAL lock record (owner decision 30 trigger b, decision 57)

> **SUPERSEDED 2026-09-22** by `docs/results/2026-09-22-slurp-v2-lock-v1.md` (the v2.0 LOCK on cell PLAN's fragment, replicated by PLANr). Kept as the record of the provisional lock; its numbers are no longer a comparator.

Recorded 2026-09-20 by the coordinator (Fable 5.1). Development numbers only (decision 28).

## 1. The trigger

Owner decision 30 locks v2.0 when three consecutive one-factor cells read NEUTRAL or HARMFUL. The streak:

| cell | verdict | official (SLU / intent) vs its comparator | read |
| --- | --- | --- | --- |
| B7a v2 (NCP L1) | HARMFUL (by width) | -0.31 [-1.81, +1.12] / -0.65 [-2.18, +0.87] vs the anchor | 2026-09-19 |
| B4a v2 (general_quirky fallback) | HARMFUL (by width; +39 % GPU-h) | -0.70 [-2.29, +0.89] / +0.74 [-0.30, +1.75] vs the anchor | 2026-09-19 |
| B8b-anchor (Reviewer slot audit) | NEUTRAL (all metrics positive, not CI95-proven; +13.5 % GPU-h) | +0.87 [-0.63, +2.37] / +1.20 [-0.19, +2.59] vs the anchor | 2026-09-20 |

Efficiency cells (EFF-1, B1-notool) do not count toward the streak. All three were decided by interval width
rather than direction; none reads a measured loss.

## 2. What is locked, provisionally

The best admitted combination is **B5e plus the delivery normaliser node** (modules M1 exemplar supply, M4b slot
store v2, M3 normaliser): official pooled SLU-F1 / intent **63.78 / 81.85** on TRAIN Fold A (B5e's sealed arm
`SAEA-SLURP-NATIVE-B5E-EXEMPLARS-K20-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-RECOVERY-V1` 62.34 / 80.09, the normaliser
applied at delivery as a model-free diagnostic). It is 0.22 SLU below the development bar (64 / 78, decision 23) and
above the intent bar. The SLURP default plan `configs/baseline/slurp-native-dual-store-train-fold-a-default-plan-v1.json`
already carries exactly these modules.

The lock is **provisional** under decision 57: the default plan has never flown as one arm, and the lock is final
only when the plan arm and its request-identical replicate have sealed (the combination's own null). Decision 57
puts the efficiency line first (0-B, the knowledge index and its twin, B9a), so the plan arm flies after those cells,
carrying whatever of them reads NEUTRAL-or-better.

## 3. What the provisional lock changes

* No new effectiveness one-factor cell is registered on the v2 base until the lock is final; the efficiency line and
  the engineering base (decisions 57, 59) continue.
* The base lock v3 document (decisions 42-44, 51) is written against this combination.
* Stage 3 (training-free RL) opens only after the final lock (decision 33).

## 4. What is not claimed

No test-split claim; no claim that the bar is met (0.22 SLU short); no claim about the plan arm's own number before
it flies; no claim that the three streak cells are harmful in mechanism -- each is a width verdict.
