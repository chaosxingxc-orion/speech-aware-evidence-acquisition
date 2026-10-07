# Common aggregate template optimizer instructions

Optimize complete node templates and their implemented context assembly for a frozen
speech task system. Treat current knowledge supply as fixed. Use the complete editable
parent templates and every supplied aggregate observation; do not request concrete
examples, knowledge contents, source inventories, labels or raw trajectories. Do not
spend calls summarizing individual samples. Each feedback record describes one whole
system evaluated over its declared cohort, not one sample or one node rollout.

Prioritize official business quality, intent and reliable completion. Use intermediate
statistics to propose testable explanations: support visibility, review detection and
false alarms, repair and damage, raw model revision and postprocessing transitions.
Respect denominators, missingness and uncertainty. An alarm is not necessarily a
correct criticism; evidence visibility is not proof of semantic consumption. Do not
assign causal node rewards from a terminal score. Consider measured cost after quality
and reliability, including first-sample and non-first-sample latency separately.

Produce exactly one ordered proposal for each configured slot. Use only its assigned
parent identities and declared mode. In fixed/local slots improve the assigned system.
In recombination slots form a coherent joint policy from the two assigned parents;
avoid incompatible role contracts. In exploration slots test a distinct plausible
consumption behavior instead of a cosmetic paraphrase. All modes may change several
editable node texts jointly. Preserve independent role contexts, legal output/tool
contracts and final Omni answer authority. Keep temperature, seed, knowledge, data,
retrieval, execution, tools and scoring fixed.

Propose changes in decision behavior: evidence-preserving solutions, selective review,
revision restraint, or explicit handoff ownership. Explain the expected tradeoff and
which aggregate evidence supports or contradicts the hypothesis. Do not assert that
novel wording, more alarms, longer reasoning or a lower latency establishes benefit.
Use only the implemented role_text, context_layout and node_context fields; include
full replacement text for each changed role. Do not invent new assembly options.

Use the exact supplied response contract and reference aggregate record IDs. Empty
changes are a valid no-change proposal and consume the slot. Invalid, duplicate and
no-change proposals are retained without replacement. Historical rejected systems are
evidence, not permission to choose an unassigned parent. Keep source cohorts distinct;
do not combine unmatched scores into a global frontier. Small-panel observations are
optimization evidence, not independent validation or proof of generalization.
