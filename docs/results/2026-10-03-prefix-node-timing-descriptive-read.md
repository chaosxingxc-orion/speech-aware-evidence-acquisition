# Descriptive node timing for the completed prefix panel

The same qualified four-member panel now has a per-node timing sidecar. This is a new read-only summary of existing sealed evidence under SAEA-SLURP-PREFIX-AFFINITY-N20-READ-V1, not another experiment, scorer call or optimizer export. All 509 contacts have server timing/token and client COST observations. Preserve the original cache export and scientific report unchanged.

## Contact-weighted measurements

The following descriptive means combine each schedule's two runs. Both runs use the same 20 exposed inputs; aggregation does not increase independent sample support. Model tool continuations and repeated node visits count separately as contacts.

| Node | Schedule | Contacts | Input reuse (%) | Prefill mean (s) | Decode mean (s) | Client transport mean (s) | Output tokens / contact |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| perception | trajectory | 40 | 63.09 | 0.698 | 5.986 | 6.971 | 124.65 |
| solver | trajectory | 70 | 62.53 | 1.948 | 2.216 | 4.493 | 36.49 |
| reviewer | trajectory | 70 | 96.81 | 0.279 | 8.743 | 9.274 | 164.30 |
| planner | trajectory | 70 | 94.92 | 0.412 | 0.201 | 0.898 | 2.83 |
| perception | role | 40 | 63.09 | 0.606 | 12.113 | 12.796 | 121.20 |
| solver | role | 73 | 23.76 | 3.313 | 2.101 | 5.650 | 30.55 |
| reviewer | role | 73 | 23.57 | 3.767 | 8.407 | 12.701 | 156.34 |
| planner | role | 73 | 22.86 | 4.078 | 0.096 | 7.161 | 2.79 |

The server records prefill and decode intervals. Client transport elapsed comes from the adapter's monotonic interval around the transport call, so it includes any work and waiting inside that transport. These boundaries differ: their subtraction is not a measured queue latency. Overlapping contact times cannot be summed to obtain system wall time or isolated GPU work.

## Observed latency distributions by independent run

Each cell below is p50 / p95 seconds. p50 is the median, p95 is the nearest-rank observation. They are descriptive contact distributions, not confidence intervals. Coverage, sums and source hashes are preserved in the sidecars. Missing future observations stay unknown, not zero.

| Run | Node | Contacts | Prefill p50 / p95 | Decode p50 / p95 | Client transport p50 / p95 |
| --- | --- | ---: | ---: | ---: | ---: |
| trajectory | perception | 20 | 0.598 / 1.232 | 5.106 / 8.879 | 5.927 / 9.959 |
| trajectory | solver | 36 | 1.527 / 4.346 | 0.970 / 14.664 | 3.356 / 16.795 |
| trajectory | reviewer | 36 | 0.220 / 1.025 | 7.425 / 19.898 | 7.814 / 20.227 |
| trajectory | planner | 36 | 0.323 / 1.133 | 0.080 / 1.684 | 0.485 / 3.336 |
| role | perception | 20 | 0.558 / 0.637 | 14.105 / 20.174 | 14.669 / 20.765 |
| role | solver | 37 | 3.475 / 4.672 | 0.590 / 9.353 | 4.531 / 12.689 |
| role | reviewer | 37 | 3.793 / 5.984 | 7.347 / 16.671 | 11.323 / 24.173 |
| role | planner | 37 | 4.056 / 5.360 | 0.081 / 0.134 | 7.079 / 11.692 |
| role-aa | perception | 20 | 0.553 / 0.933 | 11.780 / 19.178 | 12.331 / 19.697 |
| role-aa | solver | 36 | 3.456 / 4.558 | 0.625 / 7.397 | 4.716 / 11.077 |
| role-aa | reviewer | 36 | 3.901 / 5.131 | 6.703 / 18.825 | 10.281 / 23.041 |
| role-aa | planner | 36 | 3.986 / 8.595 | 0.073 / 0.158 | 7.015 / 10.097 |
| trajectory-aa | perception | 20 | 0.577 / 1.148 | 5.525 / 10.358 | 6.134 / 11.063 |
| trajectory-aa | solver | 34 | 1.893 / 4.611 | 1.264 / 9.771 | 3.559 / 12.883 |
| trajectory-aa | reviewer | 34 | 0.210 / 0.266 | 9.187 / 18.123 | 9.563 / 18.737 |
| trajectory-aa | planner | 34 | 0.329 / 1.007 | 0.074 / 1.582 | 0.484 / 3.643 |

## Interpretation

- Reviewer under trajectory scheduling already reuses about 97% of input. Its approximately 0.28-second prefill is much smaller than its 8.74-second decode. Shorter, more useful review handoffs and fewer unnecessary revisits are candidates for end-to-end optimization; these measurements do not prove such changes preserve quality.
- Planner's average prefill increases from about 0.41 to 4.08 seconds under the tested role scheduling. Its roughly three output tokens make input processing prominent. The longer client interval also includes unseparated transport work/waiting.
- Solver has material costs in both prefill and decode. Consider context relevance and the need for an additional revision together with terminal quality.
- Perception has identical input reuse under both schedules but substantially different decode timing. Scheduling, concurrency and batching affect observed intervals; cache reuse alone does not explain all latency.
- Generation wall intervals remain 195.68/195.50 seconds for trajectory and 505.81/496.49 for role. Full campaign timing, including preparation and scoring, is separately recorded in the original report and is not interchangeable with node timing.

The current query-first layout is the scope of this observation. It does not test node-specific invariant instructions placed ahead of variable sample content. Cache misses can be accepted when a prospectively registered policy improves the complete system's quality/cost trade-off. Do not add a cache-hit threshold to policy admission.

## Evidence and implementation

- [Original complete-family report, own repeats and full scenario support](2026-10-03-prefix-affinity-n20-descriptive-read.md).
- [Exact timing custody](../receipts/continuation/2026-10-03-node-timing-complete.json).
- [Owner context-space amendment](../receipts/owner/2026-10-03-context-space-and-node-timing-amendment.json).

The optional export_system_node_timing reader extends the existing analysis module, leaves export_system_cache_cost and all runtime request bytes unchanged, and requires a verified native episode source. It preserves each request's cache-contact hash and COST record hash. It contains no task answer text or quality measurements. Related tests: 98 passed; cache/timing module statement coverage 97%, all new exporter statements covered. No live sources, queue, service or frozen worker were edited. No model or scorer contacts were added.
