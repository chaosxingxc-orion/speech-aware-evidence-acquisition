# SLURP base v2.0: LOCK record (owner decisions 30 trigger b, 38, 57 option b, 78, 85, 86)

Recorded 2026-09-22 by the coordinator (Fable 5.1). Development numbers only (decisions 28 and 86).
This record supersedes `docs/results/2026-09-20-slurp-v2-provisional-lock-v1.md`.

## 1. The evidence

| cell | run | official pooled SLU-F1 | intent | GPU hours per 1,080 | verdict |
| --- | --- | ---: | ---: | ---: | --- |
| PLAN (the default plan flown as one arm on the tool-free B1 base) | `SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1`, sealed at e367a629 | **63.6304** | **82.2222** | 1.758 | NEUTRAL vs B1-notool (intent +2.22 [+0.92, +3.56] proven; SLU +1.50 [-0.04, +3.24] unproven); `docs/results/2026-09-21-slurp-plan-v2-lock-arm-verdict.md` |
| PLANr (its request-identical replicate) | `SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-REPLICATE-V1`, sealed at e367a629 | 63.8048 | 82.5000 | 1.665 | REPLICATED: +0.17 [-1.11, +1.38] / +0.28 [-0.74, +1.25] vs PLAN; `docs/results/2026-09-22-slurp-planr-v2-lock-replicate-verdict.md` |

Decision 30's trigger (b) fired on 2026-09-20 (three consecutive one-factor cells NEUTRAL or HARMFUL);
decision 57 (b) says the plan flown is the plan locked; decision 78 made PLAN + PLANr the seal path.
The pair replicates within the plan's own null on both guards, with no scenario losing beyond its
band, identical trajectories (0 tool calls, 0 compactions, 0 ReAct exhaustions) and the replicate on
both Pareto planes.

## 2. What is locked

**The v2.0 base is cell PLAN's fragment as flown,**
`configs/baseline/slurp-native-default-plan-lock-baseline-v1.json` at flight commit e367a629 (the
default plan `configs/baseline/slurp-native-dual-store-train-fold-a-default-plan-v1.json` carries the
same decided keys):

| module | key | status |
| --- | --- | --- |
| M1 speech-keyed TRAIN exemplar supply, k = 20 (`train-exemplars`) | `knowledge_stores.train-exemplars` + `phase_supply.solver` | ADMITTED (B1, B1r) |
| M4b slot-contract cards v2 | `knowledge_stores.slot-contracts -> slot-contracts-v2` | ADMITTED (B4b, B4b-rep) |
| M3 delivery normaliser node v3 | `native_episode.deliver_normaliser = saea-deliver-normalise-v3` | ADMITTED (B8a) |
| the Reviewer's native toolkit | `phase_tools` absent | RETIRED (B1-notool NEUTRAL, decision 61) |
| E13 finite completion | `native_episode.finite_completion_policy = deliver-latest-or-abstain` | declaration |
| E22 ReAct exhaustion | `native_episode.react_exhaustion_policy = continue-without-answer` | declaration |
| E20 context fit | `native_episode.context_fit_policy = compact-or-abstain` | declaration |
| review loop | Perception 1 / Solver 1 / Reviewer 3 / Planner 1, `max_revisions` 1, `review_loop` on | as flown (pruning = decision 85's first Stage-3 cells) |
| geometry | np4, 24,576-token slots, max 512 completion tokens, session `serving-slurp-native-candidate-five-train-a-np4-v1` | decision 78: np4 stays |

**Lock numbers (TRAIN Fold A, 1,080 rows, official `evaluate.py` at 8eb16545):** SLU-F1 **63.63**,
intent **82.22** (PLAN, the sealed comparator of every Stage-3 cell); replicate 63.80 / 82.50.

**The plan's own null (decision 38), from the PLAN / PLANr contrast:** h_SLU **1.2485**,
h_intent **0.9943**. Every cell whose comparator is the sealed PLAN arm reads at these margins; B1r's
1.2350 / 1.2212 remain the margins for B1-based comparators only.

**Cost of the locked base:** 4.1 contacts per row, about 8,350 prefilled tokens per row, 1.66 to
1.76 GPU hours per 1,080 rows at np4 (projected 13,078-row test read: about 21 GPU hours).

## 3. What the lock changes

- Stage 2 (SLURP) is sealed on the module side: no further module admission cell on SLURP before
  Stage 3 except the two seal flights still owed by decision 78 -- B9a (the Acquisition node, one
  recovery after item E36) and B6 (the fresh-roster direct-versus-plan read on DEV-2000-ADDED,
  decisions 34 / 35 / 79 / 88) -- and base lock v3 (decisions 42 / 43).
- Every Stage-3 cell (training-free RL over knowledge content and context-engineering dimensions;
  the pruning cells of decision 85; the primitive-verdict cell of decision 84) is one factor on this
  fragment, read against the sealed PLAN arm at the plan's own null, with the frontier row
  (decision 75) and both weightings on every verdict.
- The provisional lock's numbers (B5e + the v3 node applied model-free, 63.78 / 81.85) are retired
  as a comparator; PLANr against them: SLU +0.03 [-1.35, +1.41], intent +0.65 [-0.52, +1.86].

## 4. What is not claimed

No development bar exists (decision 86): the 64 / 78 figures are test-set targets read once after
Stage 3 (decision 29), never a statement about these numbers. No superiority, generalisation,
component-causal, cross-carrier, geometry or paper-scale claim; TRAIN Fold A is an exposed discovery
roster; nothing here is comparable with a published TEST baseline. The lock is a headroom lock on
the development roster (decision 30), not a quality certificate.
