# Worker-panel completion materialization correction

The two-member structural panel exited its model worker successfully, but the batch completion inspector stopped it at2026-10-03T19:02:11Z. Its22/25 model contacts and88/100 actual-request FIT endpoints are preserved. Both attempt records remain OPENED. Neither member has canonical output rows, a completed generation manifest or a prepared score specification. No official scoring occurred. This is a failed engineering proof.

Root omitted the existing `FlightRuntime.seal` stage when introducing worker-only panel mode. The method name was mistaken for official scoring/finalization: under the existing worker policy it actually writes complete generation artifacts and prepares a deferred score job. The panel inspector independently selected scored-arm mode for all members. Earlier mocked lifecycle tests encoded both mistakes. The original worker and all evidence remain immutable; do not reconstruct or finish its output artifacts.

The future coordinator calls `seal(defer_scoring=True)` after all member generations drain. The existing full panel path retains its original behavior. The worker remains OPENED with a complete verified generation bundle and one prepared score specification; no scorer executes. New worker inspection verifies the bundle, source commit, OPENED attempt, exact unscored receipt, pinned generation/job table and absence of score artifacts/stages. A preparation or materialization failure preserves evidence and cannot report successful completion.

Tests first reproduced four failures. Regression coverage now includes real FlightRuntime output/manifest/job materialization, closing the client, materialization failure under the panel lease, actual synthetic bundle inspection through the CLI, and fourteen custody corruptions. The native multi-owner/disk-trace suite remains included. All123 selected tests pass with three upstream deprecation warnings. Statement coverage is90.17% for campaign,98.21% for batch inspection and90.91% for panel inspection;lint,base,harness,handoff anddiff checks pass. [Pinned correction evidence](../../receipts/continuation/2026-10-03-node-panel-materialization-fix.json) retains collection limitations. No endpoint or real model call is needed for these tests.

## Recorded cache mechanism, limited to incident diagnosis

The preserved47 requests uniquely join their actual server tasks/slots by evaluated/generated token counts plus both original server timing values. Recorded callbacks cover eight initial requests for each of Perception,Solver,Reviewer,Planner,then five each for Solver,Reviewer,Planner revision. All global stage/preparation barriers hold in those records;18 preparation callbacks overlap prior-stage work in another group. This does not repair the missing completion artifacts.

Nineteen same-node slot successors reuse longer prefixes than the28 node-switch/external predecessors. Twelve of those19 change input;seven repeat input. Original node prefill averages below pool those conditions and are descriptive,not matched causal comparisons:

| Node | Same-node successor calls | Mean prefill seconds | Node-switch/external calls | Mean prefill seconds |
| --- | ---: | ---: | ---: | ---: |
| Perception |4|0.383|4|1.666|
| Solver |5|1.696|8|4.852|
| Reviewer |5|2.320|8|5.364|
| Planner |5|2.930|8|8.862|

No cache-limit,eviction,purge or context-shift message appears in the joined interval. Token-specific prefix matching still governs reuse: a node name does not establish equality. Node switching can invalidate the mismatching suffix without evicting the whole cache. Independent node contexts remain intact.

Original admission-to-terminal mean is109.514seconds;first admitted sample121.871seconds;remaining seven107.749seconds. First fixed group101.185seconds,second117.843seconds. Panel submission-to-terminal mean153.651seconds includes44.134seconds before execution. Report both origins rather than hiding setup behind an apparent speedup. Eight jobs reuse four input identities and have no controlled comparison or quality read. Do not claim stable acceleration,adoption or learning.

## Root disposition

[Exact disposition](root-disposition-v1.json) permits one prospective two-member four-row recovery after tests,registration,unchanged-request capacity transfer and clean frozen/live checks. Keep the original STOP and controls until root records that exact transition. No automatic retry,official scoring or next20 admission. Keep learning HELD,heartbeat PAUSED and root-only execution;return to the human before8x400.
