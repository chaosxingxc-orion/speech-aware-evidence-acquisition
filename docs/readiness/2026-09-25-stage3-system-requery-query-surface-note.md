# Post-hoc query-surface diagnostic

The full-context E36b replay produced nonempty results on most rows. Before
interpreting that as useful information, inspect query selectivity on the same
hash-pinned sources. This is a post-hoc descriptive extension of
SAEA-SLURP-STAGE3-SYSTEM-REQUERY-READ-V1, not another retrieval trial.

Count strict JSON tool_call objects and literal protocol markers in normalized
Reviewer states; distinguish them from executed tool events. Detect when splitting
the tool_call filter retains call as a lexical key, and when the hypothetical
ACQUIRE action survives as a key. Count concentration of returned evidence sets.
Keep raw queries, source answers and knowledge text out of the derived artifact.
No gold, scoring, reranking, model or network contact; no policy fitting or
admission from these diagnostic associations.

Entry: scripts/analysis/system_acquisition_query_surface.py. Output is immutable
query-surface-v2.json beside the completed availability replay. Preserve the original
replay, which is independently pinned; report this extension as post-hoc.

The original query-surface.json is preserved. Its ACQUIRE count was a retained
term count; v2 additionally recomputes the review-only filter to attribute whether
the hypothetical plan introduced it. All 139/143 retained cases were introduced
by that hypothetical action. No retrieval is re-executed for this correction.
