# Registered review-off request capacity

The shared graph rehearsal and reachable-request FIT APIs accept the opt-in
`profile="review-off-v1"`. Declare the same value in the composed FIT and graph
configurations as top-level `native_graph_capacity_profile`. Omission means the
historical `legacy-four-path-v1`; selecting a different profile from the declared
one fails before endpoint authorization. Keep per-member policy, source, roster,
run/attempt and exposure pins in their existing registrations.

`rehearse_native_graph(runtime, session_path=..., respond=..., output=...,
profile="review-off-v1")` walks the production executor with synthetic replies.
Use `ReviewOffResponder(ordered_four_rows, two_released_slot_types, texts=...,
lookup=parsed.solver_tool_access is not None)` for structural proof. The plain
profile exercises four P/S-only deliveries. The lookup profile exercises opt-out,
empty lookup, rejected oversized call, and a legal maximum lookup, each followed
by a final answer. Captured receipts bind the accepted answer and tool source;
neither Reviewer nor Planner is contacted. Synthetic branch coverage does not
establish natural model tool use or utility.

For the separately registered reachable-request FIT identity, call
`fit_native_graph(runtime, output, policy=lease_policy, graph_factory=fresh_graph,
contact_cap=registered_cap, profile="review-off-v1")`. The graph has four rows from
the registered capacity roster. Released-source rankings select the longest
two-slot return and wide automatic supply. The plain profile uses one supply
mode and eight captured requests; the lookup profile uses two modes and eleven
requests per mode. Each actual captured body retains its 512-token completion
reserve and existing 2048-token structural reserve inside the 24576-token slot.
This is measured reachable stress, not an exhaustive certificate for arbitrary
future output strings. Every real generation request still requires native FIT.

Derive the guarded-tokenizer endpoint ceiling without contacting a tokenizer:

```python
from speech_aware_evidence_acquisition.analysis.native_graph_capacity import native_graph_capacity_budget

budget = native_graph_capacity_budget(values,
    slot_value_count=len(binding.store("slot-contracts").snapshot.values),
    intent_value_count=len(binding.store("intent-boundaries").snapshot.values),
    graph_rows=4, media_parts=1, profile="review-off-v1")
registered_cap = budget["contact_cap"]
```

The bound includes `/props`, every released-value ranking, bounded completion
and tool-call padding searches, and every `/apply-template` plus text-part
`/tokenize` call. With one speech marker, the bounds are total source-value count
plus 43 (plain), 127 (lookup), or 185 (historical default). Recompute from the
actual pinned source counts; do not copy an old numeric cap. A smaller review-off
registered cap is rejected before authorization. Actual endpoint counts remain
reported separately. The input and output bind the derived `endpoint_budget`.

The existing CLIs expose `--profile review-off-v1`:
`scripts/native_graph_capacity.py` also requires the separately registered
`--contact-cap` and `--graph-experiment`; `scripts/native_graph_rehearsal.py`
retains its two `--targets` arguments. The latter makes no network calls. This
contract creates no experiment admission or dispatch authority.
