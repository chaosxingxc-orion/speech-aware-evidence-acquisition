# Full-roster native candidate comparison

Date: 2026-09-16. Status: shared code verified; real analysis remains held until
complete source sealing, first official scoring and root quality release.

## Question and estimands

Compare initial candidate coverage and final intent decisions on the exact same roster.
Retain unavailable Perception and malformed/empty final deliveries. Never manufacture
candidates, remove failures or equate gold missing from a set with a final prediction
escaping that set.

Report gained, lost, retained and neither-covered counts. Report each arm's own-covered
accuracy separately from accuracy on the shared intersection of covered rows. Preserve
zero denominators as unavailable, not zero quality. Report actual candidate width
distributions and final membership as inside, outside or unavailable/invalid.
All scenario strata remain visible.

The pure CandidateDecisionRow and compare_candidate_decisions APIs in
analysis.candidate_decision_comparison validate the exact ordered roster and emit
descriptive tables plus numeric sufficient-count rows. They do not read data or resample.
The shared pooled_ratio_compare API supplies the existing whole-speaker bootstrap,
natural-mixture and equal-scenario summaries. No resampling implementation is duplicated.

## Shared source-bound entry point

Use analysis.native_candidate_comparison_cli with a pinned configuration:

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<analysis-checkout>/src \
      /home/chao/.venvs/speechrl/bin/python -B -m \
      speech_aware_evidence_acquisition.analysis.native_candidate_comparison_cli \
      --config <bound-config.json> --config-sha256 <sha256> \
      --output <new-comparison-artifact.json>

The configuration has schema saea-native-candidate-comparison-config-v1 and
execution_profile model-free-check. Bind both arms' manifest, phase artifact, recorded
clean source checkout, actual projection policy and complete saved-score receipt.
Use the same verified reference source and the existing exact sample/scenario/speaker
metadata. The source verifier, initial-stage projector, reference loader and score-receipt
verifier are the existing shared implementations.

A root release with schema saea-native-candidate-comparison-quality-release-v1 must
have status COMPLETE_SOURCES_RELEASED_FOR_REGISTERED_ANALYSIS and an exact manifests
mapping for left and right. Reject a mismatch before task-output or reference access.
Reject a noncomplete manifest before invoking the bundle reader. The shared verifier
also requires a finalized task answer and the recorded clean checkout.

Cross-check each saved official intent flag against its actual parsed final delivery.
Use the initial Perception projection for both coverage and final membership. An answer
outside initial candidates is an observed membership diagnostic; in a future refreshing
system it must not automatically be interpreted as a policy violation.

The output uses core.preparation's existing envelope: the diagnostic document is under
output, with an output_sha256 and pinned implementation/input identities. Reference labels,
candidate labels and raw answer strings are not exported in the report.

## Current maximum-five binding

The held template is outside Git:

coordination/slurp-candidate-five-v1/postseal-candidate-comparison-config-template-v1.json
SHA256 48b4c5f16d4d17b93f9a046ed83216ee78fc15d0c7c27c96054819a9b9411266.

It binds the existing anchor, reference source and exact 1080-row metadata with 125 speakers
and 18 scenarios. Actual frozen baseline metadata verifies maximum 3 and maximum 5 and their
respective projection policies. The treatment seal/score and paired-release pins are
explicitly unresolved; the template cannot execute as a valid configuration.

After full sealing and first scoring, write a separately pinned bound configuration.
Use 10000 bootstrap draws, seed 20260915 and CI90 for these diagnostics. The registered
official full-task micro-F1 comparison and CI95 advancement rule remain in the existing
score comparison; this sidecar neither rescales those metrics nor creates a new gate.
Preserve historical service-process differences. No new flight is admitted.

## Verification

Sixty-two related tests pass, including the existing pooled-ratio suite. Combined changed
source coverage is 87 percent: orchestration 81 percent, pure comparison 96 percent.
Ruff and engineering-base checks pass. Synthetic integration exercises preparation
persistence, exact score/output joins, unavailable and invalid rows, exact metadata,
both weighting schemes and the actual shared bootstrap. It rejects an unreleased pair,
partial manifest, wrong score, different roster, duplicate metadata and a confirmatory
source. Synthetic source/score readers are injected; the shared custody implementations
retain their existing independent tests. This is not a live A1 result.

Verification:
coordination/slurp-candidate-five-v1/root-candidate-comparison-verification-v1.json
SHA256 a34b75bfc37601c30458cce8d72752bc08f1db58ebc95501ec9fa621b05173dd.

No current treatment outcome, new gold record, aborted quality or Fold B reference was
read. No official rescore, model, analytical-tool, tokenizer, encoder or GPU contact
was added. The older fixed-split Top-N CLI remains unchanged.
