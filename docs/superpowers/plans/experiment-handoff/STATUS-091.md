# Status 091: recovery continues; optional refresh capability reviewed

Date: 2026-09-14. Continue OWNER-CANDIDATE-COVERAGE-026.

## Live experiment

The sole unchanged TRAIN Fold A recovery remains OPENED and generating.
The resident service is serving-slurp-native-train-a-recovery-np4-v1, server PID767.
Campaign PID2124 / tool session3387 and service tool session32418 remain live.
The monitor tool session is58863. The boot remains
66947d87-43d2-4860-9766-11060b2e6bb6.

The frozen runtime is /home/chao/saea-worktrees/slurp-train-anchor-cuda-recovery-v1
at clean826a77c7bd9030ccbc25f2b74cd6fa4ed69db561. Do not edit or update it.
The service retains four slots of24576 context, total98304, max512, frozen Q4_K_M
weights, no mmproj, and preprocessed speech packets. No service restart or geometry
change occurred in this continuation. Keep the healthy service resident.

At the bound progress observation, charged model contacts were
888.
This is not a completed-sample count. The last ten-minute monitor sample window had
53 samples, mean utilization90.02%, range0--98%, and four busy slots in44 samples.
The last sample was98% with all four slots busy. Do not describe this as constant100%.

Preserve the aborted original source and its CUDA illegal-access evidence. There
were five original charged calls, one response and no complete result. The present
recovery is the only recovery allowed for this flight. Another failure closes it;
do not restart or replay automatically.

Progress and validation receipt:
DATA/coordination/slurp-native-dual-store-train-fold-a-anchor-recovery-v1/
runtime-progress-and-refresh-preparation-v2.json
SHA-256:87884aa0240db3c7d0877596b4485061d723a2c9677832bea8cc3e99e10441d9.

## Correct post-seal handoff

The campaign itself drains one official TRAIN score with complete per-sample
statistics and finalizes the attempt. After campaign completion, verify manifest
status COMPLETED, attempt state FINALIZED and queue state scored before reading
quality. Never run a second score-batch, score or finalize.

Use postseal-handoff-recipe-v2.md, SHA-256
f7028cd3250a6d30f30684d17fb4ae2b70adfa6043931ba8b76316080175b51a
in the same coordination directory. V1 was corrected and superseded.
Wrap the attached first score with zero scorer invocations and the actual attempt
ID as fallback cell_id. Build actual native trajectory reward links, then the
reviewed TRAIN stage diagnostics. The diagnostics checkout
/home/chao/saea-worktrees/slurp-native-system-diagnostics-v1 remains clean8f35ae1f.
The source checkout remains826a77c7. Keep Fold B untouched.

## Offline capability completed

Root implemented optional Planner-controlled candidate refresh using the existing
OpenJiuwen graph and shared runner, with actual-request fit, finite counts, only-Solver
delivery and source-bound receipt verification. A delegated implementation added
latest candidate source selection and bounded append-only knowledge supply; root
reviewed and integrated it, preserving legacy defaults.

Prepared checkout: /home/chao/saea-worktrees/native-candidate-refresh-v1.
Implementation commits:36494832,78139a89,8bd8d2b7.
190 integrated tests passed; after final targeted refinements,65 affected tests passed.
Ruff and the engineering-base check passed. No extra real model, ASR, scorer, or GPU
contact was made for this preparation. The running experiment does not use this code.

Read docs/readiness/2026-09-14-native-candidate-refresh-shared-interface-v1.md.
Before an enhanced flight, complete initial/post-refresh diagnostic projections bound
to actual Perception contacts and register a distinct program/prompt/config/fit plan
with the appropriate increased ceiling. The incumbent remains max11; its comparable
one-refresh successor would require max12 under the same role limits.
Choose the successor using the complete TRAIN A evidence, not partial results.
Do not silently change the incumbent's prompts or enable a new mechanism mid-flight.
