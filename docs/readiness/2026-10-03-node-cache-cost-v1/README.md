# Source-bound cache cost measurement

This optional shared analysis exporter reads exact preserved HTTP responses from a verified complete native episode. It changes no request, transport normalization, scheduler, serving configuration or scoring behavior. The owner paused the 30-minute SLURP heartbeat; it remains paused. Independent 10-second telemetry remains active.

## Measurement contract

`analysis.system_cache_cost.export_system_cache_cost` reuses the complete trajectory verifier, preserves every contact (including terminal and interrupted visits), and joins raw response bytes to request/sample identities and source hashes. It emits numeric metadata and identity references only. Request slot IDs are recorded as requested, not asserted as actual server assignment; -1 means automatic selection, null means absent.

- Reused input uses `usage.prompt_tokens_details.cached_tokens`, the Responses API equivalent, or `timings.cache_n`.
- Evaluated input uses `timings.prompt_n`; prompt and generation durations come from their separate timing fields.
- Legacy `tokens_cached` remains final slot residency. It is never substituted for reused input. Summed residency snapshots are not peak or allocated memory.
- Missing values remain null. Observed sums have coverage counts; complete totals require every contact to carry that measurement. Zero is measured zero.
- Duplicate JSON keys, nonfinite/negative or mistyped counts, conflicting aliases, changed hashes and misbound wire records fail closed.
- Full-family READ authorization remains the caller's responsibility. This helper grants no optimizer export, scientific read, flight or cache-policy admission.

## Verification

Tests were written first and failed for the missing module; slot-custody tests then failed before implementation. The completed scoped suite passes 87 tests, including complete, terminal and interrupted source exports, unavailable metadata and wire corruption. New module statement coverage is 95%. Engineering base, harness admission and scoped Ruff checks pass.

The real-file proof rechecked the signed round5 READ, all eight completed member operational gates and all original sealed sources from frozen406eda8cc. It exported every one of 1,009 model contacts without modifying any source, generating requests, tokenizing, scoring or exporting optimizer feedback. The original READ row remains unchanged.

| Role | Contacts | Recorded input tokens | Reused input tokens | Reuse fraction |
|---|---:|---:|---:|---:|
| Perception |160|640,616|404,160|63.09%|
| Solver |283|3,058,705|1,916,399|62.65%|
| Reviewer |283|3,065,995|2,968,460|96.82%|
| Planner |283|3,160,444|2,999,256|94.90%|
| Total |1,009|9,925,760|8,288,275|83.50%|

All contacts expose actual reused/evaluated input and timing fields. None exposes the legacy final-residency field; that column remains unavailable. Summed prompt processing is841,601.497ms and summed generation is3,880,912.259ms. Concurrent request timing sums are not campaign wall time or an estimated attainable speedup. These descriptive observations do not compare scheduling policies, attribute quality, establish cold/warm controls or prove a learning gain.

## Next engineering boundary

Keep current trajectory affinity as the default. Develop a separately versioned, opt-in node/prefix-family allocator and test its mutual exclusion, cancellation and release behavior offline. Register a small structural and capacity proof before any real cache experiment. Compare unchanged requests before combining node affinity with role-text changes, preserving A/A and full-family scoring. Retention benefits must be weighed against loss of the current speech/evidence prefix reuse and queue contention. Do not change any frozen round6 source or use this root report as blind/learning proposer feedback. Human review remains required before8x400.
