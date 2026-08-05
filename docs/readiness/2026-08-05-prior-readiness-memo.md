# Prior readiness memo (per-axis, model-free)

Status: TEMPLATE — filled by the lane-A readiness survey; owner picks the R1
baseline from the completed OVERALL table. No model touch is involved in
filling this memo.

Contract basis: consolidated contract §4 (candidate lines: ConEC/contextual
ASR, RECOVER-style 1-best correction, Siskos entity resolution,
FlexCTC/TurboBias biasing); design spec §5 (per-axis inventory; three outcome
classes). A line that cannot run inside the API-only frozen-core boundary is
recorded as `INCONCLUSIVE_BASELINE_NOT_READY` — that record is itself
structural-gap evidence (design spec §6 source 3) and must be copied into
`docs/innovation-candidates.md`.

## Entry format (one table row per prior line, per axis section)

| field | meaning |
|---|---|
| line | paper/system name + year |
| axis | OBS / ORG / SUPPLY / USE (one primary) |
| runnable revision | exact repo URL + commit, or `NONE` |
| license | license of code + any shipped data |
| boundary compatibility | RUNNABLE_AS_ARM / RUNNABLE_R1_FULL / NOT_READY(reason) |
| scorer alignment | how its reported metric maps onto saea-scoring-v1 |
| visible fields | which D2 arm shape it needs |
| not-runnable reason | exact blocker, or `-` |

## OBS (X1 anchor candidates)

(fill)

## ORG / SUPPLY (X2 anchor candidates)

(fill)

## USE (X3 anchor candidates)

(fill)

## OVERALL — R1 full-protocol candidate ranking

(fill; owner decision recorded here with date)
