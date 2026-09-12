# Audio2Tool native system comparison: first bounded assembly

Status: prospective design and preparation-only configuration. No generation is
admitted by this document or the current fragments.

## Question and comparisons

Test whether a shared frozen-core system improves native speech-to-tool-call
quality, and whether supplying discriminative knowledge improves the same stage
program. Use the existing 4,000-row discovery union: 500 rows per native tier,
all original recordings, and all 152 legal tools. Preserve the four long source
recordings and the released first-user-turn interpretation of tier 7.

| Arm | Live work per sample | Primary comparison |
|---|---|---|
| Direct | One complete native answer | System reference |
| Stage control | Provisional native answer, then final native answer | Stage organization versus direct |
| Knowledge | Same two phases, with one fixed registered knowledge action between them | Incremental knowledge contribution versus stage control; complete system versus direct |

Each arm generates its own state. The first phase returns a provisional answer
in the native output format; it is not a free-form reasoning transcript. The
knowledge action is scripted, not an adaptive tool-selection policy. Native
benchmark tool calls are answer outputs, not external actions executed by this
research system. The final frozen core retains answer authority.

## Freeze knowledge construction and consumption

Use the sealed native snapshot semantic hash
ccf5d93f14afa2393fc3e988a1e00c877c73e48b13b9ca0c6bde2f390093d276.
Its file hash is separately
6abf2ceacd2fb87242a5e9d15f4c468306feafe8e9bfe3e10fbb0be31800eb8e.
Keep all 152 full values, with four schema-only tools and explicit positive
native/public scope. Do not promote absent examples into prohibitions.

Use the complete sealed speech-segment queries and matching positive passage
keys. Set k=8, tau=0, cosine weight=1, prior/agreement weights=0, content only,
no exposed facet text, and the existing supply filter with c=m=top_l=8.
Max-over-segment recall preserves evidence availability; it does not resolve
chronological applicability. Supply the selected full values without
post-result selection or label-space pruning. This first comparison identifies
the knowledge package contribution, not a pure value-content effect.
A later content-only comparison must freeze keys, selected IDs and predecessor.

Use the same active official compact task instruction and call-string output
contract in all three arms. Opt in to task_contract_source=active-instruction
to prevent appending the legacy full registry after the compact registry.
Legacy fragments keep their original behavior. The new direct reference is a
shared-controller baseline with explicit CONTROL state and packet prompt order;
it is not a byte-identical replay of the historical raw-audio published-protocol
request. Record that distinction beside the historical and paper columns.

## Service, capacity and bounded exposure

The initial serving candidate is decoder-only, c98304/np3, 32768 tokens per
slot, max1024, fixed seed and temperature zero. It adds a third concurrent slot
while preserving each complete request window. Root resident allocation succeeded on September 12 at 04:57 UTC on the 24 GB GPU;
the service reports three slots with 32768 tokens each. If startup cannot allocate this geometry, stop
dispatch and preserve the failed startup; root may prospectively bind the
entire still-unstarted comparison to the retained c65536/np2 candidate.
No worker or campaign automatically restarts or substitutes a service. Promote existing complete
Qwen speech features only after source and provenance verification; never use
Nemotron retrieval vectors as Qwen input features. Keep one resident service
and one exclusive experiment lease. No child starts a replacement service.

The three-arm generation target is 20,000, with a combined 21,000 ceiling:
4,000/4,200 direct and 8,000/8,400 each two-phase arm. Prospective actual-fit
endpoint ceilings are 12,001, 24,002 and 24,002. The declared family ceilings
are 125,000 charged speech seconds and 10 utilization-integral GPU hours,
including fitting. These are this flight's prospective limits, not reinstated
global research caps. Final plans and exposure rows must bind finalized
config/source hashes before any endpoint or model contact.

Check actual shared requests over the complete roster, including all speech
chunks, full native contracts, selected values, real predecessor states,
CONTROL/ORG metadata and max1024. Enforce the inherited 8192-token reserve through the existing
prompt_fit_multiple=4/3: required tokens must not exceed 24576 in each 32768-token
slot. The receipt margin is after that multiplier; also report the physical
slot-minus-required-token margin. Fit phase two after phase-one state exists;
use the full-roster phase barrier. No synthetic padding substitutes for
this final check. If the group does not fit, revise geometry prospectively
before generation rather than truncate audio, prune tools or shorten output.

Prepare on CPU before loading, then hand off ready same-geometry arms
immediately after sealing. Score each complete manifest once in the background;
keep semantic result inspection closed until all three are sealed. Record
10-second utilization, power, memory, slot and throughput measurements.
A resident model is not evidence of full GPU utilization.

## Native evaluation and decision

Keep official tool accuracy, exact match and macro parameter precision,
recall and F1 beside the repository ordered-call and micro-slot metrics.
Report all eight tiers and native domains, natural-mixture and equal-tier
weighting, input amounts, contacts, failed/empty/saturated/fallback outcomes,
and corrected versus newly damaged samples. Include the pinned paper Table 3
column without claiming identical model or population conditions.

The principal estimands are paired exact-match differences for knowledge versus
direct and knowledge versus stage control. Stage control versus direct is a
mechanism attribution. Use the frozen decision table in configs/analysis/a2t-native-system-decision-v1.json:
paired cross-tier query_idx clusters, 10,000 replicates, seed 20260912, two
Bonferroni-adjusted 97.5-percent primary intervals, and a gain threshold of
the smaller of one percentage point and ten percent of nonnegative published
headroom. A comparator already above the paper reference has a zero headroom
threshold; do not turn the reference into an unattainable absolute gate.
Natural and equal-tier results must agree on a promising system; equal-domain
weighting is a sensitivity analysis. Tool accuracy and macro parameter-F1
must have nonnegative point deltas, which is not a noninferiority claim. Do not infer quality from
retrieval similarity, source coverage, length or self-reported confidence.
A promising first comparison requires a same-roster reproduction before
adopting a new effective mechanism. Preserve uncertainty and negative results.

## Remaining admission work

The generic source-qualified promotion is sealed: all 4,000 source recordings
have verified complete packets, including the four long recordings, with zero
new encoding contacts. The source-audio/packet identity bridge is implemented
and tested. The first shared recall preparation covers all 4,000 rows.

All three shared fake wire checks passed. The final operational campaign-stage
allowlist is set and the corresponding recall refresh is sealed with identical outputs. Preserve
the first preparation as a separate artifact; its absence of campaign-stage
permission is a configuration-identity difference, not a retrieval change.
Final wire, preparation and scientific admission receipts are bound, and the six
structured generation/fit plans are registered for the shared campaign. A preparation receipt does not admit generation.

The value criterion is source-grounded decision discrimination. The current
frozen cards include public and native role-to-argument mappings, scoped task
forms and nearby tool meanings. Some Avoid text merely lists neighboring tools;
that is weaker than an explicit supported distinguishing condition. Preserve
this limitation in component attribution. Do not rewrite the frozen values in
response to this comparison's outcomes. A later value-content contrast must
hold retrieved keys and predecessor state fixed, and assess corrections,
new errors and unchanged difficult cases separately.
