# Complete-system analysis and incremental capability extensions

Keep the primary comparison between the frozen core's direct-only task call and
the complete native agent system. The owner approved gradual expansion of the
system arm according to experimental evidence on 2026-09-13. Do not resume the
withdrawn knowledge-supplied versus knowledge-withheld comparison.

## Preserve the current campaign

The direct and native DEV1000 runs use the frozen worktree at study commit
7ec4cf340206d52a2cf44f65cdda278352c43363. Keep its source and service geometry
unchanged through generation and scoring. The direct run completed exactly
1000 model calls and finalized with one complete official score job. The system
run remains in progress as of this note. Do not infer quality from either arm
until both complete scoring sources are verified and the root read release
is recorded.

The primary estimand, roster, intervals and interpretation remain those of
2026-09-13-slurp-direct-vs-native-system-analysis-recipe-v1.json. Candidate
coverage is diagnostic only; never filter the paired task-quality comparison
by candidate inclusion or width.

## Reuse the first complete finalization score

The campaign invokes core.scoring_batch with operation=finalize. That path
scores the complete manifest once, attaches the full score artifact to the
manifest, and records FINALIZED. Its include_per_sample output retains all
row statistics. It does not emit the separate complete-score receipt required
by the frozen analysis recipe, because the existing batch receipt writer only
runs for operation=score.

Do not invoke scoring again. Use the shared core.scoring_receipt module:

    python -B -m speech_aware_evidence_acquisition.core.scoring_receipt       --manifest ABSOLUTE_FINALIZED_MANIFEST       --output-dir FRESH_ANALYSIS_RECEIPT_DIRECTORY       --job-id ORIGINAL_FINALIZE_JOB_ID

Run it in WSL with an explicit PYTHONPATH to the reviewed source checkout.
The entry verifies the finalized bundle, reads its attached hash-bound scores,
checks all configured scorers and complete row coverage, and creates only a
new result envelope and receipt in a fresh directory. The entire saved score
mapping is preserved, including pooled sufficient counts and row statistics.
source-reuse.json records the original score and manifest hashes and zero new
scorer invocations. The original manifest, score artifact, answers, traces
and attempt state remain unchanged.

The resulting receipt is accepted by the existing complete-score verifier and
shared comparison entry. Pin both the new receipt and its source-reuse record
in the root read release. Report this as receipt reuse, never a second score
run or independent result. This format bridge changes no estimator or task
output.

Validation in WSL: 54 receipt, deferred-scoring and comparison tests passed;
Ruff and the engineering-base check passed. Synthetic reuse cases verify
unchanged original bytes, exact score preservation, complete receipt
verification, refusal of unfinalized or incomplete sources, wrong score hashes
and overwrite attempts.

## Choose the next system capability from errors

Use all-row task quality to assess each complete version. Use the following
diagnostics to select a bounded next change, without claiming that descriptive
partitions alone prove its cause:

- If gold intent is absent from the candidate set, inspect Perception's
  discriminative knowledge and whether Planner needs a controlled route to
  reopen candidate selection. A stronger slot filler cannot recover a label
  that the current closed candidate contract excludes.
- If gold is present but the joint Solver selects another intent, inspect
  distinguishing evidence and joint intent/slot consistency. Treat explanatory
  slot values as evidence about meaning, never as mandatory values that must
  have been spoken.
- If intent is correct but spoken values are wrong, assess whether concrete
  lexical uncertainty warrants optional Reviewer-selected live ASR. Preserve
  the original speech and sole-Solver answer authority.
- If review changes correct drafts into wrong answers or misses clear errors,
  inspect Reviewer findings, Planner choices and actual revisions. A native
  framework transition being available does not establish that the model uses
  it effectively.

The prospective live-speech configuration stays held. Source and checkpoint
verification is complete without inference, but activation still requires a
named error component, registered runtime bindings and a final execution
envelope. Prepare it in parallel; do not force it into the queue to keep the GPU
busy.

After analysis, retain positive, negative or inconclusive labels as observed.
Apply the inherited same-roster replication or named-component root-cause
rule before extending the mechanism. Do not require a large gain at every
version. The long-term optimization object is the system's decision policy,
knowledge consumption and evidence acquisition; a later training-free RL
stage must optimize those choices against complete task outcomes.
