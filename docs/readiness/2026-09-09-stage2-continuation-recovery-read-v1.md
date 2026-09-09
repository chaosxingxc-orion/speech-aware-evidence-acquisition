# Registered Stage-2 continuation recovery reads

Authority: OWNER-CONTINUATION-002. Recorded before result inspection, 2026-09-09.
Profile: model-free-check. Every read has zero model, tokenizer, encoder, tool/network
contacts, zero speech decoding and zero GPU budget. No new execution roster is drawn.

## Input and order

1. SAEA-SLURP-NULL-NEW500-CALIBRATION-RECOVERY-V1: existing official/normalized
   per-sample score products for the direct/null pair named in the own-null preregistration.
   Read pinned DEV-1000 and NEW500 metadata and metadata-only speaker/scenario mapping.
   Verify score/batch/manifest/source bindings; never invoke a scorer. Missing fields stop.
2. Freeze the resulting source-pinned calibration receipt before opening KV treatments.
3. SAEA-SLURP-KV-FAMILY-RECOVERY-READ-V1: the seven attempts enumerated in the existing
   owner-recovery runtime snapshot, their existing complete score batches and original
   sealed direct/KC-S1b comparators. Verify hashes and roster, preserve all rows/failures.
   Search existing Git/doc metadata for a prior KV0 prerequisite verdict before concluding
   that it is missing. Do not create an earlier decision or alter the seven manifests.

## Frozen analysis

Use CONTINUATION-PLAN.md Result recovery, calibration and decisions verbatim.
Null-only calibration uses NEW500, paired speaker-cluster bootstrap 10000 draws,
seed 20260903, CI90, directed replicate-minus-comparator. Match each metric to its own
estimand; micro uses aggregate word/character TP/FP/FN, never mean row F1.
Operational margin is the unrounded CI half-width. Save source and output hashes.

KV is already flown. Apply original preregistered NEW500 per-row decisions as historical
rule evaluations, record absent decision evidence and process/estimator mismatches,
and label any reconciled decision or aligned-null sensitivity as retrospective.
Report OLD500 and pooled DEV1000, scenario tables, natural/equal-stratum weighting,
saves/harms/ties, intent identity, calls and process/config differences.
Never promote a result by swapping intervals or margins after seeing treatments.
Do not call NEW500 unexposed. Do not rerun or rescore to reconstruct history.

## Output and accounting

Save English summaries, machine-readable calibration/contrasts/source hashes, and
update the existing results ledger and exposure rows only after each registered read.
Large per-row products stay under SPEECHRL_DATA_DIR; repository outputs are compact
aggregate evidence. No model/GPU/encoder/tokenizer service is started by these reads.
