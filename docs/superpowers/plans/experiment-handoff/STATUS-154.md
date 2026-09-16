# STATUS-154: system tool-call failure and completed two-track diagnosis

Date: 2026-09-16. Root owns attribution, repair review and scientific decisions.
Supersede STATUS-153 for execution state. Preserve the frozen f3189ce2 execution source.

## Actual execution state

The campaign exited1 at2026-09-16T10:39:50Z.
- Direct recovery: FINALIZED; all1080 generation outputs and one full1080-row official score.
  Score values remain unread under the paired-release rule.
- Original system attempt: ABORTED after507 model contacts and1080.81575 repeated speech
  seconds. Contacts are not completed samples. No complete generation manifest or score.
- Resident decoder service364846 and monitor364981 remained alive. At10:47:34Z GPU
  utilization was0%, four slots idle, memory22976MiB. Do not report an active GPU flight.
- Preserve decoder-only prepared-feature c98304/np4/max512 geometry, no mmproj.
  No server restart or automatic experiment replay is needed or authorized by this note.

## Named failure

Root verified exception metadata and the shared source. Reviewer returned multiple
analytical tool calls in one completion, although the request set parallel_tool_calls=false.
The source proves at least two calls; the exact count is not established here.
The one-action guard in rails/runner.py:2033-2035 rejected before tool dispatch and
settlement. OpenJiuwen reported the ability error and proceeded to the next model request.
The shared request bridge then found the previous tool-bearing completion unsettled and
raised "native tool request has no source-bound observation" at1696-1703.

This is a shared tool-cardinality/rejected-action settlement defect. It is not evidence
that the context compiler caused a task-quality regression, and it is not an observed
machine restart, memory failure or GPU service exit. Do not read partial answers or
change scientific values from this failure.

Root triage receipt:
DATA/coordination/slurp-typed-context-vs-direct-v1/root-system-failure-triage-v1.json,
SHA256192b20f5aa20d959b5f23f43a05b04dffd16ebd73e518b659a665ea0bb124d3b.
Terminal observer receipt SHA2569d0177d3f5219286e10c061ce2dbf22701e1393365eeba57916e88a99813bf64.

The earlier sole recovery concerned the direct source binding; it completed.
This is the original system attempt's first failure. Any system recovery requires
separate registration after bounded proof, preserving the original failed attempt.
No recovery has been admitted or started by this document.

## Completed offline evidence

Root joined three already released full1080 TRAIN A sources, with every ID, ordering,
saved intent score and known category total verified. No new scorer/model/tool contact.
- Anchor:143 candidate misses,95 covered-but-wrong intents,525 correct-intent/entity errors.
- Maximum-five:129,114,519 respectively; no established full-task gain.
- Broad/factored:133,106,540 respectively; full-task gain gate failed.
- Across all three:100 persistent candidate misses,60 persistent covered-but-wrong
  intents,426 persistent correct-intent/entity errors and232 persistently exact rows.
These are descriptive intersections, not recoverable-gain estimates or causal factors.

See docs/results/2026-09-16-slurp-coverage-gap-numeric-inventory.md for all18 strata,
source hashes and pair transitions. Natural sample and equal-scenario count weights
coincide on this balanced roster. Pooled official SLU remains a separate metric.
Gold intent names, candidate rank, competing labels and parsed flags are absent from
these saved projections; they were not inferred or filled with new reference reads.

See docs/results/2026-09-16-slurp-knowledge-construction-consumption-inventory.md and
docs/results/2026-09-16-slurp-two-track-evidence-synthesis.md.
The context compiler filters role history, not all accumulated knowledge values.
Global slot cards still include all authored intent-role bindings. Current Planner
actions are ACCEPT/REVISE; acoustic acquisition and candidate refresh are not enabled.
Do not claim the entire role-specific information workspace or adaptive speech tools
are implemented and validated.

## Next sequence

1. Root prove the shared rejected-tool-action lifecycle with deterministic cases:
   valid single action, rejected multi-action, source-bound error feedback, final-report
   reserve and no extra tool execution. Preserve single-action semantics and original bytes.
2. Bind and review the smallest repair. Register any permitted system recovery separately;
   do not regenerate or rescore the completed direct arm without a named necessity.
   Prove comparison compatibility and service identity, run required capacity checks.
3. Only after a complete system source and first full score, authorize the paired read.
   Root assess official SLU, all18 strata, candidate inclusion, conditional intent/slots,
   draft/final saves and harms, and real information received/used.
4. If the package passes, perform exact-roster matched replication before adding a
   mechanism. Otherwise name a failing interface and select one bounded successor.
5. Keep SLURP as the sole active dataset. E21/Audio2Tool expansion and algorithmic
   training-free RL remain later. Closed maximum-five, broad/factored and fixed-Whisper
   experiments are not untested ideas to rerun.

No new owner scientific choice is required for bounded diagnosis and repair proof.
Escalate only a concrete change to experiment scope, recovery allowance, tool permissions
or comparison semantics. Root owns interpretation; assistants may extract evidence.
