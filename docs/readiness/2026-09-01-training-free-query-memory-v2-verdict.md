# Training-free query memory v2 — discovery support failed

Date: 2026-09-01. Status: **DISCOVERY CONSUMED; HOLDOUT NOT READ**. Experiment:
`SAEA-SN-MF-TFRL-QUERY-MEMORY-V2`. Policy artifact:
`docs/checks/speech-aware-evidence-acquisition/2026-09-01-training-free-query-memory/policy-v2.json`
(file SHA-256 `ffdc8cb88ddbfea7e40f4dfd2284272e53e05d0511f70206e6e4cbe215fc1110`;
self-hash `a442bd85a9ac8235e047be737f4c97bace443063654b46d133f3702476495026`).

## Verdict

The discovery support gate **FAILED**. The query-vector representation removed the observed harm
at its selected high-similarity boundary, but the independent support fold did not meet the
pre-registered coverage floor. The separate holdout command remains mechanically blocked, and
DEV-500-NEW400 rewards were not opened by this experiment.

The frozen-cell replay passed every fidelity condition before the policy table was read: 100 of 100
retain/dispatch decisions reproduced, 37 of 37 dispatched supplies matched exactly, the committed
72 of 100 score reproduced, eight vectorized recalls matched the registered recall function, and
900 cosine probes matched the locked knowledge-policy implementation. Query vectors had the
registered dimension 1,024. The offline guard recorded zero connection attempts.

## Discovery numbers

The locked baseline dispatched 37 of the 100 DEV-100 round-4 trajectories. Whole utterance groups
produced 26 tuning decision points and 11 reserved discovery-gate points. The registered selection
rule chose `k = 1` and minimum cosine `0.95`.

| fold | contacts suppressed | correct answers lost | harmful stops | gate result |
|---|---:|---:|---:|---|
| tuning | 3 of 26 (11.54%) | 0 | 0 | admissible |
| support | 1 of 11 (9.09%) | 0 | 0 | fail — minimum was 2 stops |

The result is informative in both directions. At minimum cosine 0.90, the nearest-neighbor rule
suppressed four tuning contacts but lost one correct answer. Raising the boundary to 0.95 removed
that harm while retaining three neutral stops. Raising it to 0.99 removed every stop. The selected
boundary was therefore the only registered `k = 1` point with zero observed tuning harm and a
non-zero efficiency gain, but its safe neighborhood did not cover enough of the support fold.

## Interpretation

The raw query vector carries useful information that the v1 scalar telemetry discarded: it changed
the tuning frontier from 12 saved contacts with four lost answers to three saved contacts with no
lost answers. It is not, by itself, a supported controller. One safe support stop cannot establish
the registered minimum coverage, and the gate is not relaxed after observing the result.

This failure does not weaken the locked BLEND result. The controller sat above that baseline, never
changed its policy or knowledge bytes, never widened dispatch, and never imputed either action's
reward. It also does not reopen the failed E108/T500 route.

## Next admissible iteration

Any next DEV-100 iteration must add a runtime-visible evidence-state component or a pre-registered
stability procedure; it must not lower the zero-harm or minimum-coverage gates. Because both v1 and
v2 have now exposed their DEV-100 support folds, those folds cannot be represented as fresh support
for a controller designed after reading these results. A successor must label the reused DEV-100
surface as exploratory, freeze its complete rule before any larger held-out read, and keep NEW400
closed until that rule has an honest, pre-registered authorization boundary.

No v2 threshold may be re-read on NEW400, and the failed grid is not silently extended.
