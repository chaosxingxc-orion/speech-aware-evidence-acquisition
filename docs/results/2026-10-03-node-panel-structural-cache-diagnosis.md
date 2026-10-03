# Whole-panel node stages: completed structural and cache diagnosis

The separately registered recovery completed at 2026-10-03T19:35:06Z. Two independent four-row members ran through the shared runtime in seven whole-panel node stages. All 53 model requests, 53 actual-request FIT receipts (212 tokenizer endpoints), 15 valid visible Reviewer handoffs and eight Omni terminal deliveries passed the structural audit. Both original generation bundles verify. The engineering attempts intentionally remain OPENED with completed generation manifests and one deferred score specification each; no official scoring or task-quality read occurred.

The failed first proof remains immutable. Its missing output materialization was a root implementation defect, corrected and regression-tested before this sole registered recovery. No original attempt was completed retroactively, resealed or scored. See the [completion receipt](../receipts/continuation/2026-10-03-node-panel-structural-recovery1-complete.json) for source and artifact hashes and the [correction](../readiness/2026-10-03-node-panel-worker-materialization-v1/README.md).

## Mechanism and structural observations

The mechanism is to retain each node's independent compatible prefix across all requests in that stage, using all four inference slots. CPU prefetch supports this schedule; it is not the cache mechanism. A hypothetical 8x20 stage contains 160 independent jobs, not a concatenated prompt. Each owner retains its own data, budget, output and trace. Different nodes keep independent contexts; compatible cross-node tokens may be reused where they actually match. No prompt equality, permanent role slot, server cache reset, KV save/restore or new serving geometry was imposed.

Eight calls each ran Perception, Solver, Reviewer and Planner in round0; seven continuing jobs each ran Solver, Reviewer and Planner in round1. All preceding-stage inference and final next-stage preparation completed before the next model stage began. Twenty-two preparation callbacks overlapped other groups' preceding-stage work. All 53 requested slots matched unique actual server task assignments using exact token counts and both rounded timing values. No release was truncated. Local trace spooling completed within its declared per-record/per-owner bounds; these bounds do not limit total process RSS.

## Reuse, separated by immediate slot predecessor

There were 25 same-node slot successors: 18 changed-input and seven repeated-input calls. The remaining 28 followed a node switch or a task outside this proof. Report the repeated-input cases separately: their 5,805-9,404 retained tokens include speech/history, beyond the approximately 2,750-2,880-token static node prefix. Those seven cases skipped speech-feature decoder evaluation. All 18 changed-input successors decoded their different speech features and evaluated their unmatched suffixes.

| Node | Changed-input same-node calls | Retained tokens | Mean prefill seconds | Switch/external calls | Mean prefill seconds |
|---|---:|---:|---:|---:|---:|
| perception | 4 | 2763 | 0.495 | 4 | 1.756 |
| solver | 4 | 2778-2783 | 2.852 | 8 | 6.112 |
| reviewer | 6 | 2754-2759 | 2.822 | 8 | 6.485 |
| planner | 4 | 2876-2881 | 4.581 | 8 | 9.346 |

These are descriptive groups within a tiny structural run, not matched causal comparisons. Context lengths, generated outputs, batching and predecessor states differ. The switch group generally retains 2,526 tokens (Planner: 2,529), so changed-input static node reuse adds only a few hundred tokens in these current prompts. The larger prefill-time difference cannot be attributed entirely to those added tokens.

No cache-size/token eviction, context-shift, purging or eviction message appears in the bounded joined server interval. This supports working resident prefix reuse and does not establish that every suffix remained resident. Earlier token divergence still invalidates subsequent KV. The request counters and speech decode events show that suffix evaluation continues. No explicit prefix warmup occurred; earlier registered requests supplied inherited slot state. Tokenizer FIT and warm prepared-supply verification are not KV prefill.

## Node and original sample timing

| Node | Calls | Mean prefill seconds/call | Mean generation seconds/call | Mean client transport seconds/call |
|---|---:|---:|---:|---:|
| perception | 8 | 1.126 | 3.000 | 4.291 |
| solver | 15 | 4.201 | 5.885 | 10.622 |
| reviewer | 15 | 4.597 | 12.452 | 17.787 |
| planner | 15 | 6.396 | 1.121 | 8.788 |

Original admission-to-terminal sample mean was **153.561s**. The first admitted job took 156.010s and the remaining seven averaged 153.211s. The first fixed group of four averaged 162.550s; the second averaged 144.573s. These groups are admission groups, not controlled cold/warm trials.

The original submission-to-terminal mean was **189.606s**. Per-owner preparation/start waiting is retained in that measure (first-owner pre-execution wait 36.042s). Do not divide panel makespan by eight and call it sample latency. Node timings overlap under server batching and cannot be added as exclusive GPU time. The seven node-stage spans and all preparation/queue timestamps remain in the pinned acceptance receipt.

The Reviewer has the largest observed mean generation time, 12.452s/call. Cache tuning affects prefill, while output work and global-stage waiting remain material. Fewer switches alone do not prove lower sample latency. A whole-panel barrier can delay an otherwise ready sample, especially as the panel grows.

## Next measurement boundary

Structural acceptance closes the shared-runtime ownership, barrier, output materialization and original-timing checks for this proof. It does not qualify an optimized policy or establish lower latency, unchanged business performance, stable learning or 160-job scaling. The four inputs are reused from the existing optimization pool; no new independent evaluation is implied. No actual knowledge call occurred in this proof; local tool branches retain their existing offline/capacity evidence only.

Before adopting this schedule, prospectively register a same-roster, same-prompt trajectory-versus-node-panel comparison with its own A/A controls and exact family READ. Keep ordering/initial inherited cache exposure explicit. Report original submission/admission timing, first and subsequent groups, ready-to-start waiting, prefill and output tokens/time, complete-family official quality, intent and reliable completion. Separate changed-input static-prefix reuse from same-input history reuse. If both request layouts are compared, hold scheduling constant within each layout contrast rather than attributing their combined change to caching. A panel's barrier cost is part of its outcome, never removed from timing.

Any full 8x20 measurement must actually retain eight independent owners and 160 jobs; this eight-job proof is not a substitute. Review the resulting engineering/cost/quality evidence before scaling. Root227 permits bounded20/50/100/200 work, but this closure receipt itself admits no next flight. Learning remains HELD, the heartbeat remains PAUSED, and no subagent is used. Return to the owner before8x400. Preserve other-carrier holds and the current completed queue and worker until a separate normal transition is recorded.

At19:39Z, the driver task had exited successfully, STOP and the flight lease were absent, no generator/scorer/driver remained, the original serving process/session identity matched, and Windows free memory was17.059GiB. The adjacent telemetry showed a healthy idle four-slot service. This is a completion observation, not a promise about future resource state.
