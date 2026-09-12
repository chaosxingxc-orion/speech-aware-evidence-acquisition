# TRAIN reward lineage: accepted shared implementation validation

Date: September12,2026. Root replaced the unaccepted draft and completed source-backed
semantic review before acceptance. The active GPU experiment checkout was not edited.

## Accepted behavior

Build reward links only from a COMPLETED, FINALIZED source bundle, its complete saved
native score receipt and an exactly matching construction roster. SLURP additionally
requires TRAIN sample identities and a TRAIN scorer. Keep all twelve native intent,
exact-slot and word/character sufficient-statistic fields; do not replace pooled
micro F1 with row-mean F1 or allow arbitrary answer-bearing numeric projections.

Associate every model request, normalized response and successful control contact by
exact identity. Preserve unanswered attempted requests in the trajectory without
crediting them as successful contacts. Validate typed query/sample identities,
runtime contact waves, selected final contact, final output, review phase response,
phase tool source response and posthoc runtime identity. Support both separate
phase execution and the continuous program's single runtime-use record.

Retain ordered OBS/ORG/SUPPLY/USE events, tool-manifest identities, reviews and
provenance hashes. These bindings do not themselves prove causal component contribution.
Keep ExperienceSource.response_sha256 as the final-text hash and preserve the wire
response hash separately. Rehash common large artifacts once per build, not per row.

Use build_experience_sources for freshly verified source files or
verify_experience_sources for saved links. Both perform source-bound verification
for the complete roster. RewardLink.validate checks stored integrity only; a
self-consistent object hash is not authoritative verification. The misleading
per-object conversion method was removed before this API was accepted.

## Validation evidence

-48 focused tests pass, including real general bundle verification and complete-score
receipt verification over synthetic fixtures. No verifier was mocked.
-Separate and continuous layouts, overlapping sample IDs, cross-sample/phase
substitutions, altered sources, failed attempts, selected-final drift and
self-consistent forged links are covered.
-128 tests pass across reward links, memory records/runtime, score receipts,
phase tools and phase runner.
-Branch-inclusive reward_links module coverage is85 percent.
-The engineering-base check passes.
-An independent read-only review closed the two original semantic findings and the
continuous-layout compatibility issue. Root accepted the final implementation.

The pytest coverage plugin was absent; the installed coverage module generated the
coverage report successfully. All checks ran in WSL with CUDA hidden and the explicit
isolated source path. No experimental model, tokenizer or production scorer ran.

Validation receipt: /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/coordination/training-reward-links-validation-v1.json
SHA256: fb934868608bf6a28da264d5b2cd40cc4f2c98dfebc4951b57ccc566319db92f

## Remaining lifecycle

This completes the shared source-to-native-feedback binding, not a training-free
optimization result. Create-only artifact I/O is being added separately. A legal
gold-free proposal projection, disjoint candidate selection, frozen admission and
task evaluation are still required. The existing gold-bearing construction proposer
cannot be reused unchanged for corrective-memory proposals. Keep provisional and
rejected proposals outside the admitted runtime memory catalog.
