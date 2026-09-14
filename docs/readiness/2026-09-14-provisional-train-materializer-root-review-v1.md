# Provisional TRAIN materialization: root integration

Root reviewed the source-bound materializer and required explicit protocol and
decision cross-bindings plus an integration test using the real bundle verifier
and real TRAIN feedback/context reconstruction. The corrected author commit is
a17b6397246bed662bb78b3f7d65eef8460619d4, integrated in the inactive worktree
as 5b7fdbf423b9cd5c21cbf0afe2a0cec0eadc0d35. No active runtime changed.

The shared model-free entry point is
python -m speech_aware_evidence_acquisition.core.provisional_candidate_materialization.
Pass --config, --config-sha256 and --data-root. Use explicit PYTHONPATH for the
frozen caller worktree; do not reinstall the shared editable environment.

The configuration pins a finalized typed proposal bundle, exact reconstructed
TRAIN contexts, source-binding list, construction roster, protocol binding and
materialization decision. The protocol binds the actual verified runtime
protocol hash, run ID and source files. Its file hash is a separate identity.
The decision binds the same bundle and authorizes materialize-all-provisionally
with no selection and no admission.

The materializer preserves every sample, empty proposal list, option association
and within-response order. It recovers real source and reward pointers from the
hidden bindings and creates provisional ExperienceRecords under
DATA/provisional/experience-candidates. It refuses an exceeded bound instead of
truncating or selecting. Input guards run before publication and afterward.
The original proposal outputs and admitted memory catalog are unchanged.

Author validation: 19 focused tests and 198 relevant combined tests, Ruff and
engineering-base checks passed. Root independently ran the integrated
materializer and memory tests: 35 passed in 1.24 seconds. The whole-path fixture
uses genuine shared verification and reconstructed synthetic reward sources.
Changing the actual attempt state to OPENED refuses materialization and does
not publish a new artifact. No real model, tokenizer, GPU, scorer, speech tool,
audio decode or quality result was contacted.

This completes a source-to-provisional-record engineering seam. No real proposal
has yet been generated or materialized, no candidate has been evaluated, and no
memory has been admitted. Next freeze a compact candidate/relevance policy,
evaluate through a distinct TRAIN-only candidate boundary, and write admission
only from the actual registered evaluation decision. Do not pass provisional
records through the admitted loader by changing their status.

A follow-up source-interface audit found that provisional references used candidate labels while the existing admitted-source verifier expects canonical reward-link references. Root corrected the materializer to use the same shared hash-to-reference helper as admitted source verification, before any real candidate materialization. Candidate labels remain in the exact prepared bindings; no provenance is discarded or admission granted. The integrated materializer, memory and source-verification selection passed 67 tests. This correction changes future prepared implementation identity; do not edit any earlier hash-pinned artifact in place.
