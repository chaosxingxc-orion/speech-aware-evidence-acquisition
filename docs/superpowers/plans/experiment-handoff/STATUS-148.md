# STATUS-148: controlled Reviewer history is prepared, A1 remains in flight

Date: 2026-09-16. Root owns scientific analysis and next-experiment admission.
Supersedes STATUS-147 for engineering readiness and the live operational snapshot.

## Active GPU experiment

Continue the existing frozen SLURP maximum-five TRAIN A1080 campaign. At
2026-09-16T07:42:13.623226+00:00, server PID364846, monitor PID364981 and campaign PID365064
are alive. The latest monitor sample at 2026-09-16T07:42:03.010765+00:00 reports
server_ok=True, 4 busy slots of four,
96.0 percent instantaneous GPU utilization,
22976.0 MiB used, 96.0 W and
2736 requests. Requests are not completed samples.
No terminal or campaign-result receipt exists. No partial task quality is read.

Operational receipt under DATA:
coordination/slurp-candidate-five-v1/root-reviewer-history-preparation-boundary-v1.json,
SHA-256 60d50a6aa50cd8c546f989312dbb79a5bfb128f53777bf539071ee4e168db603.

Preserve sessions47342/50165/99915, the existing service, lease and frozen534c92e8
source. Do not restart, replay or change its requests. The current shared campaign
owns sealing and the first complete official scoring job; do not rescore.

## Track B engineering completed

Canonical commit5959356308a8c50093a49bebef69758cc5eb683f integrates the opt-in
Reviewer history scope and its held configuration. Read
docs/readiness/2026-09-16-slurp-reviewer-history-scope.md.

The Reviewer request retains original speech, current bound knowledge, the latest
complete Solver state and only the current visit's exact tool call/result chain.
It omits Perception candidate IDs/descriptions, older drafts and previous
Reviewer/Planner/tool history. Complete episode records and other roles retain
full history. The default remains unchanged.

This is a context-scope factor with an information-loss tradeoff. It is draft-visible,
not statistically independent. Current knowledge can reflect prior candidates.
No automatic issue-to-action routing was introduced; Planner decides, Solver answers.

The focused WSL suite passed128 tests, zero skips. The scope module has93 percent
line coverage and all50 added executable production lines were covered.
Ruff, engineering-base and diff checks passed. These are synthetic transport tests
without real model/tokenizer/ASR/encoder/scorer contacts. Real-request capacity and
quality are not yet verified.

Verification under DATA:
coordination/slurp-review-measurement-v1/root-reviewer-history-scope-verification-v2.json,
SHA-25637da455659bc5fa5a08f93808c9ef6e0858a73ddd52108c625d038a841092fb9.
It corrects only a changed-line coverage extraction error in preserved v1 metadata.

The option differs only by Reviewer history scope and descriptive text from the
existing, unrun structured-review v2 configuration. A historical-anchor comparison
would be a package effect. No experiment cell, execution plan or new model contact
is admitted by these configurations or this handoff. Do not silently combine it
with the separate no-example task-contract option or other new mechanisms.

## Next scientific decision

Track A: after complete A1 seal and its first saved official score, root releases
the paired comparison and binds the prepared candidate-analysis template. Report
candidate coverage, gained/lost inclusions, common/own-covered decision quality,
full task metrics and all18 scenarios. Preserve the registered10000 whole-speaker
bootstrap draws, seed20260915 and CI95 advancement rule. A positive lead requires
same-roster replication before claiming stable benefit.

Track B: use the released temporal diagnosis to investigate evidence-to-answer
completeness and source-derived slot boundaries. Already visible omission rules
or repeated card retrieval are not new information. Select one bounded next
contrast after A1's complete verdict; preparation availability does not choose it.

Keep SLURP as the sole active dataset. E21/Audio2Tool and twice-failed closed
flights remain held. Stable system benefit still requires a matched shared-harness
direct-model comparison. This engineering work is not training-free RL.
Preserve canonical untracked integration_native_finite.py and wsl$/.

## Latest owner refinement

The owner now prioritizes a shared role-context module that analyzes, cleans and normalizes
handoff information before role-specific supply. Read
docs/readiness/2026-09-16-role-context-compilation-contract.md.
The history-only filter is an implemented capability, not the automatically selected next
treatment. Preserve useful candidate alternatives as hypotheses; separate observations,
knowledge, current drafts and review declarations. Root has specified the shared integration
seam and validation contract. The complete typed compiler is not yet implemented or admitted.
This refinement does not change the running A1 source or create additional model contact.
