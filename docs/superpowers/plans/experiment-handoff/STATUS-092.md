# Status 092: healthy recovery and held agentic successor

Date: 2026-09-14. Continue OWNER-CANDIDATE-COVERAGE-026.

## Current service and experiment

Fresh read-only verification at 2026-09-14T07:01:27.423435+00:00 found the restored service
healthy and the sole TRAIN Fold A recovery still OPENED. Boot identity remains
66947d87-43d2-4860-9766-11060b2e6bb6. Server PID 767 and campaign PID 2124 remain the existing owners.
No restart, model reload, geometry change or replay occurred during this continuation.

The frozen runtime remains clean 826a77c7bd9030ccbc25f2b74cd6fa4ed69db561
at /home/chao/saea-worktrees/slurp-train-anchor-cuda-recovery-v1.
The service uses four slots of 24,576 context (98,304 total), max512, frozen Q4_K_M
weights and preprocessed speech feature packets, with no mmproj.
At this observation 4 of four slots were busy.
Charged model calls were 1964; this is not a completed-sample count.
The complete roster remains 1,080 TRAIN A records. No partial quality was read.

The trailing 600-second monitor window contains 53 utilization readings,
with mean 89.96%,
range 57--99% and all four slots busy in
40 readings.
Do not interpret this as constant 100% utilization.

Bound progress and validation receipt:
DATA/coordination/slurp-native-dual-store-train-fold-a-anchor-recovery-v1/
runtime-progress-and-successor-preparation-v3.json
SHA-256: 3014b2060e573728ddc46defd54bb5d7a19a18998bd308fb81e0e12fe83951bb.

## Reviewed shared successor preparation

Root prepared a held complete-system TRAIN successor with a distinct max12 program,
pinned Perception/Solver/Reviewer/Planner prompts, one optional candidate refresh,
latest candidate-associated slot knowledge, and selective contract/Whisper tools.
Only Reviewer has tool authority; Solver retains final task-answer authority.
This configuration is not an admitted experiment or campaign.

Root implemented optional local-tool scheduling in the existing shared executor.
A selected local analytical action releases its sample's model slot before waiting
for one shared CPU worker. The next model contact reacquires a slot and carries
complete history. Legacy configurations retain stable per-trajectory slot affinity.
Started tools drain through repeated cancellation; cancelled queued tools never run.
No additional inference service or fixed ASR preprocessing is introduced.

Root reviewed and integrated two delegated implementations:
- Receipt-bound C0/C1 diagnostics. C0 is the first actual Perception; C1 is the last
  actual Perception before the delivered Solver. Zero refresh uses the same source.
  Report coverage, recovered/lost sets, common-covered resolution and final accuracy.
  Never use candidate union, final-answer reconstruction or reference-label feedback
  to manufacture candidates. Explicit null configuration is rejected.
- A hash-bound optional Whisper CPU thread envelope. Enforce positive CPU limits,
  refuse an aggregate envelope above eight, set Torch limits before lazy model load,
  and verify them before subsequent decoding. Omitted configuration stays legacy.

Implementation checkout:
 /home/chao/saea-worktrees/native-refresh-tools-successor-v1
Implementation head before this status: e262c9188467fe5d311dd67aa5e89c5ff36d732e.
Root implementation commit: 62912d24.
Reviewed integrations: 3a88a159, 7ab23d07, fae06b74, e262c918.
Integrated validation: 370 model-free tests passed in WSL; Ruff, diff and engineering
checks passed. No real model, ASR or scorer contact was made by this preparation.
The active frozen runtime was not updated.

Read the three English readiness notes:
- 2026-09-14-native-refresh-tools-train-successor-held-v1.md
- 2026-09-14-native-candidate-stage-projections-v1.md
- 2026-09-14-whisper-cpu-thread-envelope-v1.md

## Next execution boundary

Keep the sole unchanged recovery running. Preserve the original CUDA illegal-access
failure and its five charged calls. A second failure closes this flight; never
restart or replay automatically.

The campaign owns one complete official TRAIN score and finalization. Use only
postseal-handoff-recipe-v2.md, SHA-256
f7028cd3250a6d30f30684d17fb4ae2b70adfa6043931ba8b76316080175b51a.
Verify full ordered 1,080-row custody, manifest COMPLETED, attempt FINALIZED and
queue scored before reading quality. Wrap the attached first score without invoking
the scorer again, then construct actual native reward links and TRAIN diagnostics.
Retain the diagnostics checkout at 8f35ae1f for the currently pinned recipe.

Root then decides whether and how to admit the held successor from complete TRAIN A
evidence. Bind the actual TRAIN audio view, pinned CPU tool protocol, runtime resource
envelope, generation/fit/tool plans, budgets and preparation receipts. The proposed
max12 ceilings are bounds, not targets or granted authorization. Keep Fold B untouched.
Evaluate whole-system native quality and candidate-stage diagnostics; group-relative
optimization still requires actual complete paired TRAIN trajectories.
