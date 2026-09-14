# Owner decision: candidate coverage and parallel system optimization

Date: 2026-09-14. Source: the owner's explicit in-session selection.

English translation of the selected answer:
"Treat 95% as a key target while continuing system optimization in parallel."

Question context: the complete TRAIN A anchor has 86.75926% gold candidate
coverage and 525 correct-intent cases with nonexact entities. Root proposed
improving candidate coverage while also optimizing evidence-tool selection,
candidate verification, and slot correction through training-free system updates.

Apply this decision prospectively. Treat at least 95% candidate coverage as a
priority for the candidate module. Continue TRAIN-only system optimization
alongside that work; do not wait for coverage to reach 95% before preparing the
training-free cycle. Keep full-task performance as the system progression
criterion and preserve candidate-stage availability and conditional accuracy.

The decision does not alter the active recovery's roster, candidate width,
prompts, tools, knowledge, frozen source, budgets or limits. Preserve its sole
recovery contract. Freeze a selected rule candidate before any disjoint Fold B
evaluation; preserve all prior verdicts and exposure boundaries.
