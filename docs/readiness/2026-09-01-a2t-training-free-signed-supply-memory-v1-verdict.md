# Audio2Tool signed-supply memory v1 — structural state is live but reward-inseparable

Date: 2026-09-01. Status: **RETROSPECTIVE SCREEN FAILED; NO PROSPECTIVE CONTACT
AUTHORIZED**. Experiment: `SAEA-A2T-MF-TFRL-SIGNED-SUPPLY-MEMORY-V1`.
Artifact:
`docs/checks/speech-aware-evidence-acquisition/2026-09-01-training-free-a2t-supply-memory/policy-v1.json`.
Artifact self-hash: `99c19db3f1adfde2c86b6c9ebfc4c18fc3dc58fe2ccfde22a78c679a408ca7c6`.
File SHA-256: `a42b826cc92edd4715017a1f17d09fde9b18f8f9a41ab0a5c603f2124fa66aed`.

## Verdict

The action-support surface is real, but the registered runtime structure does not separate useful
from harmful supply. Both exact-cell reward memories defaulted to `STOP_DIRECT` on all 217 samples.
They therefore saved zero of the eight known conversions, harmed zero samples, made zero second
contacts, and produced zero exact-match gain with grouped CI90 `[0.0, 0.0]`. The conjunctive
promotion screen failed. No prospective approximately-100-sample run, G2 opening, baseline change,
or model contact is authorized.

This is not another inert-state failure. The coarse representation has six live classes and the
detailed representation has 18. The failure is reward inseparability inside the live classes. In
the coarse state, seven of eight saves and 31 of 36 harms occupy the same 138-sample
`single/all-known/exact` cell. In the detailed state, those seven saves remain colocated with 18
harms in the 76-sample `single/all-known/exact/one/one` cell. The remaining save sits in a
13-sample unresolved-signature/two-key cell that also contains two harms. No registered cell has
both at least two saves and zero harms, so the all-stop result follows from the frozen rule rather
than from a software defect.

## Fidelity and efficiency

All source checks passed: 400 unique A0 rows, 120 B1 rows, 97 R1 rows, 217 of 217 supplied-tool
labels identical to the original A0-selected tool labels, 208 query groups with eight repeated
groups isolated as units, and the published signed aggregate reproduced at eight saves and 36
harms. Fifteen of 152 registry signatures are explicitly unresolved; none is guessed.

The first validation attempt exposed an evaluation-efficiency defect: the legacy A0 reader reloads
the full expected-call manifest once per scored row. The registered evaluator now reuses that
reader's structural receipt checks and performs one shared frozen-scorer pass for the paired
surface. Runtime fell from an unfinished I/O-bound pass exceeding 74 seconds to 12.3 seconds on the
first completed run and 11.7 seconds on the diagnostic rerun. Official scoring semantics did not
change. The focused suite passes 33 tests with 82% targeted line coverage.

## Interpretation and next admissible change

Blind supply is strongly negative on this support surface: always stop yields 97 exact matches,
whereas always supply yields 69, a net loss of 28. V1 demonstrates that call count, registry
resolution, argument-key relation, schema arity, and supplied-key count are insufficient for safe
targeting. Relaxing support, save, or harm thresholds after this result is inadmissible because it
would simply expose the mixed-return cells.

One bounded successor is scientifically motivated: add the selected registry row's already-visible
`domain` and `category` as a state abstraction while keeping the exact same memory rule, grouped
folds, gates, actions, rewards, and default. Those semantic schema fields may separate the mixed
one-argument cell without using tool identity, transcript, gold, or outcome fields. That successor
must be registered before any domain/category-to-return relation is read. If it also defaults to
stop or mixes saves with harms, this static logged Audio2Tool surface is exhausted and the next
valid information source must be prospective self-consistency or another runtime observation, not
another threshold search.

No model, embedding, tokenizer, HTTP, socket, audio, or GPU contact occurred. The 183 tool-selection
failures, every unexposed Audio2Tool population, FINAL60, test annotations, and future turns remain
closed.
