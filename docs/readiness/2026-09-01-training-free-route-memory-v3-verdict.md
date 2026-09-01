# Training-free route memory v3 — route state was inert

Date: 2026-09-01. Status: **MECHANICAL SCREEN PASSED; SCIENTIFIC PROMOTION
REFUSED; HOLDOUT NOT READ**. Experiment: `SAEA-SN-MF-TFRL-ROUTE-MEMORY-V3`.
Policy artifact:
`docs/checks/speech-aware-evidence-acquisition/2026-09-01-training-free-route-memory/policy-v3.json`
(file SHA-256 `a9fb245462387086a070be614b503898897f658fcb800e9245cd8c5d371f26c5`;
self-hash `c6008b19b8a1b7e816752b26fcb99de876f7604573284260a96181afb1b82c1b`).
The executing implementation was committed at `28399ebf`.

## Verdict

The pre-registered numeric stability screen passed, but the proposed route-state information
channel was **completely inert**. The v3 controller made exactly the same decisions as its fixed,
unconditioned v2 comparator. It therefore contributes no information gain and is not authorized for
holdout promotion. DEV-500-NEW400 was not opened.

This is a stricter scientific refusal than the artifact's mechanical boolean. The artifact is kept
unchanged as the execution record. A successor fail-closed guard now additionally refuses any route
policy whose route state has fewer than two live classes or whose stopped-id set is identical to the
fixed v2 comparator. That guard can only close an invalid promotion path; it cannot create a pass.

## Mechanical result

The frozen-cell replay passed every fidelity condition: 100 of 100 retain/dispatch decisions, 37 of
37 supplies, the committed 72 of 100 score, eight registered recall probes, and 900 cosine probes.
The offline guard recorded zero connection attempts.

Five-fold whole-utterance cross-fitting selected `k = 1` and minimum cosine `0.95`. It suppressed
four of 37 evidence contacts (10.81%) across three folds, with zero harmful stops and no primary
score change. The fixed v2 comparator suppressed the same four contacts, on the same sample ids, in
the same folds, with the same rewards. At cosine 0.90 both readings stopped five times and lost one
correct answer; at cosine 0.99 both stopped nowhere.

## Route-state liveness diagnosis

The execution artifact reports one live route class: `direct-unresolved`, 37 of 37. Inspection of
the frozen implementation showed that the loader passed `SampleReplay.direct_target`, which exists
only when the parsed direct target maps to a registered label facet. The preregistered contract was
broader: it specified the direct answer's parsed scenario/action target.

A bounded secondary correctness read over the same 37 already-exposed trajectories established:

| diagnostic | count |
|---|---:|
| direct responses parsed | 37 of 37 |
| raw parsed direct targets resolved | 37 of 37 |
| mapped `SampleReplay.direct_target` resolved | 0 of 37 |
| raw parsed direct target present anywhere in the fused route | 0 of 37 |

The implementation input therefore mislabeled the intended state. Correcting the mapping would not
rescue the mechanism: every trajectory would move together from `direct-unresolved` to
`direct-absent`. The intended route state also has zero entropy on this surface, so its conditioned
memory remains exactly the unconditioned v2 memory. No corrected replay or threshold search is
needed, because the decision equivalence follows deterministically from the 37-of-37 counts.

## Consequence

V3 does not supersede v2 and does not support a training-free RL contribution. It instead exposes a
useful engineering requirement: every proposed controller state channel must pass a liveness and
decision-attribution gate before a metric-only promotion gate may authorize a larger read.

The locked BLEND baseline and its knowledge bytes are unchanged. No model, embedding, tokenizer,
HTTP, socket, audio, or GPU contact occurred. DEV-1000-NEW500, FINAL60, SLURP test, and future turns
remain untouched. No v3 policy or threshold may be evaluated on NEW400.
