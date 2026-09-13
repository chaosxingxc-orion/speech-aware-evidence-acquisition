# Native TRAIN trajectory projection, version 2

Status: implemented and validated with synthetic, source-bound TRAIN bundles. This is
an offline projection capability, not a proposal flight, memory admission, or
completed training-free optimization cycle. The active DEV1000 replication stays
on its frozen runtime commit 532d8788a3cedca45fd9b81bde81b08fad4a22ec.

## Problem and resulting behavior

The previous projection copied the canonical native framework control envelope
into model-facing text. Real envelopes contain private sample/contact identities,
so the downstream identity guard rejected them. The legacy synthetic fixture had
no control content and did not exercise this path. Reading response text alone
also omitted structured function calls and their observed results.

The shared projection now reads the actual native completion receipts and uses
the same source-envelope and local-tool-sequence validator as runtime transport.
It exposes each role's initial query, system instruction, actual available tool
schemas, chosen function and arguments, source-bound tool returns, and the selected
Solver response. Calls and evidence references receive candidate-local labels.
A result appears only in requests whose observed history contains it, and must
join an earlier actual model call in the same candidate trajectory.

Keep the raw source manifests, responses, traces, and official score outputs
unchanged. Produce a separate saea-training-proposal-contexts-v2 artifact with
model-context hashes, exact reward/source bindings, and a reader implementation
fingerprint. Existing non-native trajectory fields and runtime wire semantics
remain unchanged. A native completion without its canonical framework envelope
is rejected instead of silently losing its tool semantics.

## Boundaries and information retained

- Consume only the already verified TRAIN construction cohort through the shared
  reward-link and group-relative feedback entry points.
- Keep native numeric outcome vectors and their conflicting dimensions; do not
  invent a scalar reward or a cost penalty.
- Preserve function arguments, candidate IDs, candidate order, task schemas,
  explanatory rules, contrasts, and observed evidence content.
- Strip tool-result custody metadata such as source URIs and file hashes from
  model-facing content. Preserve selected knowledge references with local labels
  and attach the same labels explicitly to the corresponding evidence blocks.
- Keep custody, source IDs, manifest paths, and reward identity outside the model
  context. Refuse embedded forbidden IDs rather than rewriting free text.
- Report speech feature availability/count without pretending a packet descriptor
  is a decoded transcript. This text proposal context does not itself load audio.
- Reject missing, foreign, duplicate, noncanonical, or orphan response/completion
  joins and changed source returns. Rehashing a framework message cannot change
  the dispatcher's counted tool result.
- Preserve the existing one-call-per-result native contract. Supporting multiple
  simultaneous calls requires a separate shared runtime change.

## Verification and next use

Root integration validation passed 259 tests across the combined changes.
The focused validation covers reward links, group-relative feedback, legacy and
native proposal contexts, runtime native history, and framework history. New
fixtures use canonical contacts for Perception, Solver, Reviewer, and Planner,
two bound tool sources/continuations, a Solver revision, and the final Solver
selection before later Reviewer/Planner contacts. No model, tokenizer, encoder,
analytical tool, or official scorer was contacted by these tests.

The next optimization seam is a configuration-driven frozen-core proposal role
and provisional-record materialization, followed by disjoint TRAIN selection and
a real admission writer. Provisional records must not be relabeled as admitted
merely to evaluate them. DEV replication errors remain analysis material and must
not become TRAIN correction rules or examples.
