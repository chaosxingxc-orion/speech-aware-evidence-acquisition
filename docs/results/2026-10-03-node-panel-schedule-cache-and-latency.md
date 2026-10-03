# Complete node scheduling comparison: engineering route not promoted

The registered complete family demonstrates that resident prefix caching works, but the tested global node schedule loses valuable same-input cross-node reuse. Root does not promote the 160-job global barrier or the before-speech layout. Keep the legacy trajectory layout as an engineering reference, not a newly proven superior policy. This is a descriptive small-panel engineering disposition; no stable efficacy, formal harm/no-harm, global optimum or learning conclusion is made.

All 16 members independently FINALIZED 20 rows with verified seals, exactly one successful complete official score each and zero failed scoring jobs. Root signed SAEA-SLURP-NODE-PANEL-SCHEDULE-N20-READ-V1 after qualification. The complete-family reader exited zero at 2026-10-03T23:25:13.447721Z, adding no model, tokenizer or scorer contact. There are 320 trajectories over the same 20 exposed TRAIN inputs and 2,072 uniquely matched actual server task/slot assignments. [Qualification](../receipts/continuation/2026-10-03-node-panel-schedule-n20-family-qualified.json), [scientific evidence](../receipts/continuation/2026-10-03-node-panel-schedule-n20-scientific-read.json) and the [registered recipe](../readiness/2026-10-03-node-panel-schedule-n20-entry-v2/analysis-recipe-v1.json) retain custody.

## What was tested

Eight ordinary 20-job trajectory flights ran sequentially, followed by one eight-owner 160-job panel. Each schedule includes legacy and before-speech layouts, each with two primary/A-A pairs. Every role retains its own text and legal context; all four slots remain available. The panel finishes all current-node inference before the next node starts. CPU-only next-node preparation overlaps completed 20-job groups. The audit verifies all seven stage barriers and 768 overlapping preparation events. The requested stage schedule was implemented correctly.

The panel did not retain 160 engine KV snapshots. Pending requests, local trace spooling and prepared next-node messages are not a KV state bank. Identical audio, packets, queries, votes, knowledge, frozen Omni, scorer and legal tool/revision contracts were retained. The frozen worker is dd765815218eb7d9207701c130ae5ed9f802dab8. The original four-slot server was not restarted or purged; no explicit KV warmup, save or restore was introduced.

## Cache mechanism and measured node cost

In pinned llama.cpp commit 04ccc72a2207347ca76161b93fd9d846dd0a8675, server-context.cpp:3334-3336 computes the selected slot's longest common token prefix; lines 3532-3565 retain that prefix and discard the unmatched suffix. A node name change does not itself evict a cache. An early token difference prevents reuse of the later suffix, even if later text has the same meaning. Different role instructions can still share an earlier identical serialized speech/evidence/history prefix. Node independence does not require incompatible tokens at the front.

The live session enables resident cache_prompt but uses --cache-ram 0, --no-cache-idle-slots and --slot-prompt-similarity 0. It has no external RAM prompt-state bank or configured disk slot action path. Four slots cannot preserve a distinct live KV history for every one of 160 jobs. In legacy trajectory execution, Solver, Reviewer and Planner each have 148 calls whose immediate actual slot predecessor is another node of the same sample. The global panel mostly replaces that with another sample of the same node, trading long same-sample prefixes for short static prefixes.

These are per-contact means across all visits, including revisions. Prefill/decode are observed request timings under concurrent serving, not exclusive GPU compute; output lengths and load differ. Do not sum overlapping request durations into wall time.

| Schedule | Layout | Node | Calls | Input tokens | Reused tokens | Evaluated tokens | Prefill s | Decode s | Client s |
|---|---|---|---|---|---|---|---|---|---|
| trajectory | legacy | perception | 80 | 4003.8 | 2526.0 | 1477.8 | 0.650 | 5.463 | 6.333 |
| trajectory | legacy | solver | 148 | 10898.5 | 7085.0 | 3813.6 | 1.820 | 1.967 | 4.141 |
| trajectory | legacy | reviewer | 148 | 10983.1 | 10638.8 | 344.2 | 0.245 | 7.970 | 8.337 |
| trajectory | legacy | planner | 148 | 11312.7 | 10747.4 | 565.3 | 0.368 | 0.207 | 0.827 |
| trajectory | before-speech | perception | 80 | 4003.8 | 2526.0 | 1477.8 | 1.039 | 10.682 | 12.057 |
| trajectory | before-speech | solver | 143 | 11068.7 | 2526.0 | 8542.7 | 4.720 | 4.730 | 10.118 |
| trajectory | before-speech | reviewer | 143 | 11157.4 | 2526.0 | 8631.4 | 4.367 | 20.727 | 25.624 |
| trajectory | before-speech | planner | 143 | 11509.6 | 2529.0 | 8980.6 | 4.184 | 0.313 | 4.810 |
| panel | legacy | perception | 80 | 4003.8 | 2526.0 | 1477.8 | 0.624 | 4.073 | 4.902 |
| panel | legacy | solver | 147 | 10708.1 | 2526.0 | 8182.1 | 4.197 | 7.307 | 13.253 |
| panel | legacy | reviewer | 147 | 10792.7 | 2526.0 | 8266.7 | 3.474 | 13.847 | 17.688 |
| panel | legacy | planner | 147 | 11122.4 | 2526.0 | 8596.4 | 9.235 | 1.341 | 12.816 |
| panel | before-speech | perception | 80 | 4003.8 | 2751.2 | 1252.7 | 0.616 | 3.332 | 4.175 |
| panel | before-speech | solver | 146 | 11158.5 | 2766.8 | 8391.7 | 4.270 | 7.902 | 13.651 |
| panel | before-speech | reviewer | 146 | 11249.0 | 2744.1 | 8504.9 | 3.576 | 14.763 | 18.570 |
| panel | before-speech | planner | 146 | 11608.7 | 2859.4 | 8749.2 | 8.862 | 1.304 | 12.439 |

Legacy Reviewer reuse falls from 10,638.8 to 2,526.0 tokens, evaluated input rises from 344.2 to 8,266.7, and mean prefill rises from 0.245 to 3.474 seconds. Legacy Planner reuse falls from 10,747.4 to 2,526.0 tokens. Before-speech steady same-node groups retain about 2,754-2,881 tokens: those extra static tokens are useful, but they do not replace the long same-input prefix lost at a node switch.

All 2,072 requests uniquely match actual server tasks. None of the checked capacity-pressure patterns (cache size limit, cache token limit, context shift, evict, purging) occurs in the finite family scope, server-log lines 450806-472568. This supports prefix divergence/resident replacement as the observed explanation. It does not prove all forms of eviction impossible or absent from all server history. Request suffix truncation differs from removing an entry from an external cache bank.

The first measured call already retained 2,526 tokens from a predecessor outside the family. First-four admissions are not a proven cold batch; later admissions are not automatically warm. Prepared-supply warm verification is not engine KV warmup. This design does not establish separate cold-start or explicit warmup benefit.

## End-to-end latency and equal workload cost

Each row is the mean of four equal-size 20-row members. First is the first admitted roster member, not the first to finish; non-first excludes exactly that member. First-four and after-four use original admission order without trimming slow samples.

| Schedule | Layout | All samples s | First s | Non-first s | First four s | After four s |
|---|---|---|---|---|---|---|
| trajectory | legacy | 92.190 | 53.207 | 94.241 | 35.558 | 106.348 |
| trajectory | before-speech | 232.967 | 109.632 | 239.458 | 80.461 | 271.093 |
| panel | legacy | 2953.887 | 3182.424 | 2941.858 | 2806.581 | 2990.713 |
| panel | before-speech | 3166.481 | 3410.762 | 3153.624 | 3125.312 | 3176.773 |

The panel admits 160 jobs to shared barriers while an ordinary member dispatches 20. The admitted-to-terminal means capture that schedule's waiting, but their large ratio is not a matched service-speed ratio. Do not label 92 versus 2,954 seconds a 32-fold GPU slowdown. The first sample can finish after many others when its revision branch waits for later global stages.

| Equal 160-trajectory measure | Sequential trajectory workload | One global node panel |
|---|---|---|
| Original runtime dispatch windows | 41.928 min (sum of eight windows) | 61.689 min (one common origin) |
| Model contacts | 1033 | 1039 |
| Generation-stage wall | 45.163 min | 63.815 min (maximum overlapping owner window) |

Observed runtime-dispatch cost is 1.471 times sequential (47.1% longer). This is equal-workload throughput cost, not mean sample latency; it excludes inter-experiment admission, scoring and work outside dispatch. Every panel owner shares original batch_started_ns=415808880011636; do not sum their overlapping durations. The workloads ran in a fixed order, not as independently repeated scheduling trials.

Within the panel, first model callback to last model return spans 3,550.610 seconds. Seven stage walls sum to 3,539.020 seconds; gaps total 11.590 seconds. CPU prefetch works, but removing gaps alone cannot account for the larger workload difference. Mean panel submission-to-terminal time is 3,207.995 seconds versus 3,060.184 from admission, retaining about 147.811 seconds of preparation/admission wait. The first sequential finalize worker took 321.891 seconds while later workers were about 51-55 seconds; its cause is unestablished. Nested scoring timers are not additive.

## Official business outcomes and limits

Every member delivered 20/20 rows reliably with no abstention and zero knowledge calls. The following ranges are four individual official complete-run scores, not a new pooled score or independent sample. [Companion tables](2026-10-03-node-panel-schedule-strata-and-repeats.md) contain all run values, own repeats, registered paired intervals and all 13 strata with natural and equal-stratum summaries. No decision is based on a selected stratum.

| Schedule | Layout | Official SLU-F1 range % | Intent range % | Reliable completion |
|---|---|---|---|---|
| trajectory | legacy | 56.738-60.312 | 70.0-70.0 | 100% |
| trajectory | before-speech | 54.428-57.813 | 60.0-70.0 | 100% |
| panel | legacy | 53.674-61.015 | 70.0-70.0 | 100% |
| panel | before-speech | 48.383-55.141 | 50.0-70.0 | 100% |

Quality observations do not establish a benefit that justifies this observed latency cost. Twenty unique exposed inputs and one coupled panel cannot prove stable superiority, formal harm/no-harm or learning. Bootstrap intervals use 10,000 paired utterance resamples, seed 20261003, 95% confidence. They capture input variation under these observations, not unmeasured scheduling variance. Root retains all evidence without optimizer export or point-estimate policy adoption.

## Memory and genuine cache storage

Own panel preparation reached RSS high-water 25,514,640 KiB (about 24.33 GiB); the allocation's cause is unestablished. Among 40 ten-second observations available at the preparation checkpoint, Windows free memory had sampled minimum 8.507 GiB. This exceeds the 8 GiB running floor but is not a continuous-time guarantee or scaling margin. After completion, Windows free was 20.462 GiB at 23:15:36Z. No stale-task cause, cache flush or host-setting change is inferred or performed. Audit preparation object lifetime before increasing size.

The user's space-for-time hypothesis is distinct from the implemented schedule. It requires preserving actual compatible sequence state, not only request/output files. The pinned source supports optional RAM prompt save/load and explicit disk slot save/restore, but neither path was enabled or exercised here. RAM loading selects a better compatible prefix and consumes the saved entry; byte/effective-token bounds discard oldest entries while retaining at least one. With explicit slot selection and similarity zero, the automatic request-time cache-update branch is not triggered. Increasing a cache setting alone does not prove intended state preservation.

Disk slot actions wait for idle slots and require --slot-save-path. Multimodal checks and the fork's custom speech-feature state fidelity must be verified before use. Saving/restoring state also cannot make incompatible early role tokens into a reusable prefix. Source and binary identities plus exact code references are pinned in the scientific receipt.

## Root227 disposition and next engineering work

1. Keep learning and 50/100/200 scaling HELD. Do not promote the global 160-job barrier, force identical node prompts or activate before-speech placement. Preserve all workers, outputs and completed controls.
2. Use existing legacy trajectory execution as the engineering cost reference. Preserve node independence and reuse immutable speech/evidence and allowed history only where it really matches. Do not add irrelevant history or restrict instructions solely for cache hits.
3. Audit prefix affinity and actual resident/saved state lifecycle offline before another GPU comparison. Separate same-sample cross-node reuse, same-node different-sample reuse, inherited state and saved-state transfer. A bounded resident cohort and a genuine state-preserving schedule are distinct future hypotheses; neither is admitted or proven here.
4. Any state-saving prototype must measure state bytes, save/restore wall time, source/model/token/speech-feature identity, intended actual slot and restored prefix. Preserve full output reserves. Check that transfer plus preparation/queue cost is lower than avoided recomputation; prove terminal Omni custody before registered four-row structure and a complete small-panel quality/latency comparison.
5. Bound preprocessing object lifetime separately from KV. Report original mean/non-first/first-four latency, whole-workload cost, per-node prefill/decode/reuse, official SLU/intent and reliability. Root alone continues, heartbeat stays paused, and human review precedes 8x400.

This report adds no model/scorer contact, activates no runtime policy, and releases no held carrier. The engineering target is the most valuable valid prefix reuse under business quality and end-to-end cost, rather than grouping node names alone.
