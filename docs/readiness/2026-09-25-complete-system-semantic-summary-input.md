# Complete-system semantic summary input

Status: model-free source preparation for the scholarly baseline, not an
executed Training-Free GRPO update. The active candidate-recovery GPU pair and
its frozen worker are unchanged.

## Why this bridge is needed

The pinned upstream updater reads only
json.loads(item.trajectories)[0]["trajectory"]. A carrier adapter that puts
one role in each top-level entry would show the summary model only Perception.
The new shared analysis.system_semantic_trajectory module puts one complete
executed episode into that first entry. It does not replace the upstream
summary, group comparison, experience operations, consolidation or evaluation
stages with a numeric bandit.

## Exact source and representation

materialize_semantic_trajectories consumes the existing verified native source
and its score-free whole-system export. It prepares every ordered discovery
row, including finite interruptions and abstentions. Each episode retains:

- Every actual actor request field and response, with source record identity.
- Every role visit, repeated review contact, revision and interrupted visit.
- Decoded exact wire response text where recorded, including tool-call output
  and finish reason; both record and original byte hashes remain bound.
- Recorded tool attempts/results/rejections, source trace order, runtime control
  events, proposal/policy custody, delivery rule and delivered bytes.

Equal request-field values share a content-pool entry. This is lossless
deduplication, not summarization, truncation or selection of successful steps.
A reader can reconstruct every request payload. Unavailable instrumentation
stays unavailable. The source artifacts are never rewritten.

Only actual actor records and named runtime control fields are materialized.
Post-hoc annotation fields, attached scores and reference answers are not
copied into this input. The original task instruction remains in the request
fields. Original speech identity is retained, but the updater has not heard
audio merely because an audio hash is present. This is a trace-based semantic
input; any later audio observation needs its own declared request and contact.

## Group identity and feedback separation

The adapter reuses the same initial speech identity function as the complete
rollout grouping reader. Add the registered round and split identity. The
resulting raw_question grouping key differs for distinct recordings with the
same task instruction, while retaining the same key across policy variants of
the same input in a round. Run/attempt identity still distinguishes episodes.

tfgrpo_summary_fields prepares only raw_question, trajectories, an empty
correct_answer and an empty reasoning field. It deliberately is not a complete
upstream EvaluationSample: it supplies no default reward and cannot activate a
learning loop. Numeric official terminal feedback must be joined separately
through the already verified system feedback/group path. Do not coerce signed
utility to success, apply the upstream binary mixed-group filter unchanged, or
use given_ground_truth=False as a reward-preserving adaptation.

The prepared document states learning_authorized=false. A discovery split
alone is not permission for learning or for a model-facing update. A future
registration must bind construction sources, updater prompts, permitted memory
locations, action-space parity, feedback visibility, retry and capacity limits,
and the full update/reexecution loop. Summary/experience model contacts must
use the authorized frozen local core through the shared service and execution
plan; this module creates no model client or service.

## Evidence and remaining boundary

The pinned upstream summary expression was extracted with Python AST and
executed against three synthetic complete/finite/abstention episodes. It
returned the entire prepared episode in every case. No upstream package was
imported, and no summary model, scorer or research artifact was contacted.

Tests also drive the ordinary OpenJiuwen graph with synthetic model transport,
checking both candidate modes and four role interruptions. Additional cases
verify exact request reconstruction, shared content references, recording/split/
round identity, unchanged sources, rejected source mutations, and exclusion of
synthetic offline reference annotations.

This completes the summary carrier representation only. It does not admit a
semantic update, qualify a system action, reopen the closed semantic-delta line,
or prove any RL improvement. Use the current complete-system pair's terminal
evidence to choose the next scientific action; register a semantic algorithm
comparison only after its full same-space cycle is concrete.

## Validation record

118 related tests and all nine offline repository checks passed in WSL.
The source-expression audit rehashed the pinned upstream file before extracting
its AST; the three recorded cases returned the complete episode unchanged.
The test suite additionally covers the actual shared synthetic graph, both
candidate proposal modes, four role interruptions, annotation exclusion and
legacy rollout grouping. Research model and official scorer contacts added: 0.

Receipt: docs/receipts/continuation/2026-09-25-system-semantic-trajectory-preparation.json.

## Shared runtime successor

The [shared runtime connection](2026-09-25-system-summary-shared-runtime.md)
now consumes this complete-episode representation through prepared ORG state
and the existing artifact request path. Its current speech-feature arm also
attaches the original sample speech, an explicit multimodal input adaptation.
The earlier representation proof above remains unchanged; it is not evidence
of text-only inference or an executed full semantic update cycle.
