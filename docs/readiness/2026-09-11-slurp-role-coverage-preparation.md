# Selected TRAIN intent-role coverage: implementation and preparation

Authority: OWNER-DISCRIMINATIVE-VALUES-021 and the active continuation goal.
The implementation uses the existing registered knowledge builder, renderer,
retriever and shared experiment runtime. No new controller, tool-level answerer,
encoder or experiment framework is introduced.

## Decision-relevant knowledge and its limits

A useful value connects an unresolved task decision to grounded evidence.
Role coverage can direct attention to a possibly missed entity. A stronger
contrastive value would specify what separates competing roles or labels and
when that distinction applies; coverage alone does not yet do that.

SLURP knowledge may contain task roles, label boundaries and faithful surface-form
examples. Audio2Tool knowledge needs native tool capabilities, parameter meaning,
required inputs and compatibility boundaries, built from its isolated construction
partition. E21/E22 ASR knowledge needs legitimate term/entity distinctions and their
acoustic or contextual evidence; a plausible topic association must not overwrite
what was spoken. These task-specific contents may share the same source-bound
supply interface. Validated conditional correction procedures belong to memory;
a TRAIN corpus or a plausible rule is not automatically validated memory.

## Shared implementation

Select --view slot-fillers --value-format intent-role-coverage in the existing
scripts/build_knowledge_snapshot.py CLI. --lock-path explicitly binds the umbrella
lock when running from an isolated WSL worktree; the historical default layout
continues to work. Historical snapshot bytes and receipts were not rewritten.

The new value retains its local observed_intent and observed_slot_examples, then
adds same-intent selected-utterance support. Count each utterance once regardless
of recording or mention count. Empty annotations are explicitly counted as
unannotated; role support is neither required-slot evidence nor proof of absence.

The added provenance reference hashes the sorted complete same-intent selected
utterance membership. It complements the original local anchor references.
Every member remains reconstructible from the snapshot's value identities and
task targets; source inputs and the frozen snapshot hash bind the content.

## Completed verification

- The focused WSL suite passed 94 tests, including unchanged formats, renderer
  round trips, deterministic builds, exclusion, empty annotations, duplicate
  identity refusal and canonical-intent validation.
- Measured changed executable-line coverage: 95.45% for the shared builder
  and 80% for the CLI lock-path change.
- The existing engineering base check and git whitespace check passed.
- The shared CLI built all 11,514 governed TRAIN utterances and 60 intents.
- Root independently checked all 11,514 aggregate values and membership references.
  All facets, source rosters, local frames, anchor associations and priors match
  the control snapshot. Only content and added aggregate provenance differ.
- Added content ranges from 304 to 544 UTF-8 bytes per value, mean 437.935.
  This is an input-volume measurement, not tokenizer fit or a quality result.

Detailed receipts remain under DATA coordination:
slurp-intent-role-coverage-model-free-build-registration-v1.json,
slurp-intent-role-coverage-root-verification-v1.json,
slurp-intent-role-coverage-tests-v1.log,
slurp-intent-role-coverage-coverage-v1.json, and
slurp-role-coverage-engineering-check-v1.log.

The earlier test invocation that selected the canonical checkout through shell
variable expansion is not counted as validation. The passing suite explicitly
imported this isolated worktree. Existing duplicate-ID rejection is reused
before sampling; no duplicate validator was added.

The matched protocol and analysis template are prospective. Aggregate verification
does not establish runtime request matching, capacity or task improvement.
Preparation, fake-wire receipts and actual worker fit must establish those
successive facts. No new model, tokenizer, encoder or embedding contact has
occurred during construction or the verification reported here.
