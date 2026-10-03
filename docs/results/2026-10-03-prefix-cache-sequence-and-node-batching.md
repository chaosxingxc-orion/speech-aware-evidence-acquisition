# Source-bound prefix-cache, warm-state and batching diagnosis

This supplement uses the already authorized complete eight-member context matrix. It adds no model, tokenizer, scorer, proposer or cache-management contacts. Preserve the original report, READ authority and all frozen worker bytes. It supersedes only the original report's unknown actual-slot assignment: all 1,030 assignments are now independently verified from server task logs.

## Evidence and scope

The running custom llama.cpp source is commit `04ccc72a2207347ca76161b93fd9d846dd0a8675`, with tracked server sources unchanged. The archived server-log prefix, original wire bodies and numerical evidence are hash-bound in `coordination/context-matrix-cache-sequence-owner227-v1/cache-mechanism-and-admission-groups-v2.json`. Its pinned offline audit script rederives every timing signature and immediate slot predecessor. Exact evaluated/generated token counts plus both timing values to log-rounding tolerance identify exactly one server task per request; no nearest-time matching. All actual/requested slots agree, all prior slot tasks released before the successor, and all 1,030 releases report `truncated=0`.

No full-slot purge, prompt clear, memory-pressure allocation failure, checkpoint-forced full recomputation, context shift, RAM cache size/token eviction or prompt save/load event appears in the bounded matrix log interval. Trace-level suffix removals were not enabled: the suffix mechanism is established from pinned source, actual cache counters, first differing request blocks and speech decode logs, not an invented per-token debug dump.

## What invalidates the reused prefix

`server-common.cpp:480` compares exact token prefixes; speech placeholders additionally require matching packet-derived chunk identity and token length. Chunk identity is stable packet SHA plus ordinal (`server-common.cpp:973`). A role name is not a cache key. `server-context.cpp:3334` finds the common prefix, line3535 retains it, and line3565 removes KV from the divergence onward. Ordinary slot release/reset preserves prompt/KV; it does not empty the cache on every call.

With the original layout and trajectory affinity, 225 same-sample successor calls retain the speech/evidence prefix and skip speech-feature decoder evaluation. With whole role text before speech, all216 same-sample successor calls first differ in user content block0; cached length falls to2526 for Solver/Reviewer or2529 for Planner, and each evaluates the speech feature again. With role slots, every493 within-run slot successor is another sample; original layout first differs in the speech descriptor. Before-speech role layout retains only its role-specific static beginning;90 successors first differ in the dynamic role-query text and164 in the following speech descriptor.

Across the complete family, the server logs805 speech-feature decoder evaluations. Only the original trajectory configuration skips them on same-sample continuation. These calls reuse pre-extracted features: they do not rerun the speech encoder. Speech is a small portion of the invalidated suffix; the much larger evidence/history text is also recomputed. Do not attribute the whole delay to speech.

## Measured costs

LT means original layout with trajectory slots; BT means whole role text before speech with trajectory slots; LR and BR use permanent role slots. P/A are each configuration's own two runs. Timing sums overlap under model batching and are not exclusive GPU work. Processing slots mean active server task intervals, not GPU utilization.

| Member | Contacts | Evaluated input tokens | Summed prefill seconds | Mean processing slots /4 | Mean sample seconds |
|---|---:|---:|---:|---:|---:|
| LT-P | 131 | 198,450 | 101.90 | 3.44 | 89.02 |
| LT-A | 134 | 204,993 | 101.84 | 3.44 | 106.52 |
| BT-P | 125 | 958,443 | 540.80 | 3.67 | 233.07 |
| BT-A | 131 | 1,004,737 | 518.84 | 3.70 | 261.04 |
| LR-P | 122 | 864,942 | 397.86 | 2.50 | 265.36 |
| LR-A | 125 | 910,279 | 423.99 | 2.44 | 286.16 |
| BR-P | 131 | 943,856 | 434.88 | 2.14 | 319.11 |
| BR-A | 131 | 954,994 | 437.07 | 2.23 | 315.83 |

The cached prefixes are working; they are not all evicted. Original trajectory input recomputation is about199k/205k tokens, versus865k-1,005k in the other configurations. Permanent role slots also reduce observed processing-slot occupancy. These observations explain mechanisms but do not isolate every second of sample delay: output length, batching, tool/FIT work and waiting also vary.

| Member | Solver prefill ms/contact | Reviewer prefill ms/contact | Planner prefill ms/contact |
|---|---:|---:|---:|
| LT-P | 1725.81 | 306.48 | 336.00 |
| LT-A | 1649.62 | 268.09 | 394.52 |
| BT-P | 5427.06 | 4248.97 | 5211.56 |
| BT-A | 4621.35 | 4197.36 | 4566.74 |
| LR-P | 3385.63 | 3941.55 | 4018.24 |
| LR-A | 3450.42 | 3992.56 | 4289.91 |
| BR-P | 3338.13 | 3774.15 | 4301.81 |
| BR-A | 3372.30 | 3896.51 | 4248.04 |

## Warmup and first versus later groups

The matrix admission explicitly inherited uncontrolled cache state and prohibited extra warmup/reset/save/restore. Prepared supply warm verification checks existing immutable artifacts; warm FIT revalidates existing capacity artifacts without endpoints. Cold capacity FIT uses formatting/tokenization, not a generation prefill. The driver's `prelaunch-ok` field `warmup=registered-model-work-only` is not a prefix-warming call. Do not equate these preparation meanings of warm with resident decoder KV.

Every slot's first matrix request already reused at least2526 tokens. In the before-speech role A/A run, the initial four role-slot requests reused2763/2746/2722/2844 respectively from the preceding same-layout run. The hot in-slot prefix exists and survives calls, but an earlier mismatch makes its following KV invalid. Additional one-time warmup cannot prevent recurring mismatches.

There is no controlled empty-cache first batch here. The executor permits16 in-flight sample workflows on4 slots. The following groups use admission order (first4 versus remaining16); they are not separate synchronous model batches or proven cold/warm waves. Sample intervals include internal waiting, actual-request FIT and cleanup; pre-admission waiting is separately retained.

| Member | First4 mean seconds | Remaining16 mean seconds | Five admission groups of4, mean seconds |
|---|---:|---:|---|
| LT-P | 36.79 | 102.08 | 36.79, 57.82, 91.86, 128.69, 129.93 |
| LT-A | 43.04 | 122.38 | 43.04, 74.72, 123.11, 152.04, 139.66 |
| BT-P | 73.46 | 272.97 | 73.46, 123.62, 247.93, 356.59, 363.74 |
| BT-A | 77.21 | 306.99 | 77.21, 173.33, 280.96, 386.44, 387.24 |
| LR-P | 96.10 | 307.68 | 96.10, 209.54, 293.96, 388.89, 338.32 |
| LR-A | 94.83 | 334.00 | 94.83, 189.12, 385.50, 408.66, 352.71 |
| BR-P | 198.39 | 349.29 | 198.39, 294.69, 377.09, 453.78, 271.61 |
| BR-A | 169.32 | 352.46 | 169.32, 296.44, 416.73, 413.09, 283.59 |

All later-group means exceed first-group means. This rejects the simple descriptive story that only the first group is slow and all later work becomes cheap; it does not estimate causal warmup cost. Queue waiting and continuing suffix recomputation remain. Prospective timing must keep cohort-release-to-terminal, workflow admission-to-terminal, per-node ready/queue/start/finish, original prefill/decode, slot residency and first/subsequent node-batch groups separate. Never redefine admission later to hide barrier time. Throughput (batch makespan/count) is not mean sample latency.

## RAM cache and active management

The actual service uses cache_prompt, cache-ram0, no-cache-idle-slots, slot-prompt-similarity0 and explicit slot IDs. Hot per-slot KV reuse remains enabled; the secondary RAM prompt-state archive is disabled. With this exact selection path, there is no RAM save/restore. In this source, enabling RAM cache alone while keeping explicit slot IDs and zero similarity does not activate `update_cache`. Do not generalize that explicit IDs always bypass caching: a nonzero similarity path can request an update.

When admitted and enabled, automatic save/load stores sequence state, selects an improving matching prefix, restores it, and prunes old entries on byte/token limits (`server-task.cpp:1601-1787`). Such storage can preserve multiple matching branches, but cannot reuse KV after an earlier changed token as though the changed context were identical. Explicit save/restore would need separate custom speech-token metadata compatibility, source identity, measured I/O and resource proofs. No cache endpoint or serving change was made here.

## Root disposition: implement bounded node batches

The latest direct owner instruction requests space-for-time execution: retain each sample's intermediate state, let all four slots process the current node for a bounded cohort, then feed each sample's own outputs to its next node. This is materially different from the measured permanent-role-slot design, which gives each role only one slot and interleaves samples at that role. The measured failure of that routing does not disprove node batching.

Implement this as an opt-in scheduler in the existing OpenJiuwen/shared native runtime. Preserve independent node text, request semantics, source-bound handoffs, per-sample tool decisions, revision loops, contact accounting and Omni terminal custody. A batch may complete a node's tool loop before progressing; completed or branched samples must not deadlock a barrier. All live workers settle on failure; no new cohort or hidden retry follows failure. Keep bounded CPU intermediate storage and the8/12.5GiB floors. No increased slot/context geometry is implied.

Expected opportunities are fewer role-prefix switches, four slots available to the active role, and reuse of sufficiently long exact static node prefixes. Current cross-sample prefixes are short (about2526-2881 tokens), so a throughput or latency win is a testable hypothesis, not guaranteed. Broader barriers can increase first-answer/sample delay. Node batching alone also does not retain every sample's long KV across nodes; four slots cannot hold every node-by-sample branch. Preserve useful independent contexts rather than forcing prompt equality to improve a metric.

First prove this scheduler offline, including conditional branches, local tools, cancellation, finite completion, same request bytes apart from allowed scheduling identity, and truthful timing. Then separately register capacity/structural proofs and a small same-pool repeated comparison before scaling. Record any actual prefix warming as an explicit measured step and charge its time/contacts; tokenizer calls are not warmup. Compare the existing trajectory schedule with bounded node batches, not another permanent-role mapping. Cross-experiment node co-scheduling remains a future prospective design: preserve separate attempts/results and no sharing of generated answers or future learning feedback.

The already prepared per-role-tool/Reviewer-history candidates remain HELD and are not launched while this scheduler is being established. Learning remains HELD; heartbeat remains PAUSED; no subagents. Return to the owner before8x400. No formal benefit, no-harm, stable learning or independent validation claim is made by this20-input diagnostic. Official quality and reliability remain mandatory alongside sample latency; see the unchanged complete-family scientific report.
