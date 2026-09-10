# G6 live SLURP complete-score and paired-analysis wiring

Status: held preparation only. This document creates no score job and does not read quality, references, or model outputs. The control delivery is sealed; the speech delivery remains in progress and has no bound manifest or score hash in the draft.

## Frozen inputs

- Control delivery manifest: DATA/runs/SAEA-SLURP-LIVE-INTENT-SLOTS-CONTROL-RECOVERY-V1/derived-live-intent-slots-control-recovery-delivery-v1/SAEA-SLURP-LIVE-INTENT-SLOTS-CONTROL-RECOVERY-V1--delivery-live-intent-slots-control-recovery-delivery-v1.run-manifest.json, SHA-256 668dd2449c07eeddbd09caf012cb0fbb6994794287459ca086da43c94dc33421.
- Control source: /home/chao/saea-worktrees/g6-live-recovery at c4dd9342422c2afc0309a19c5dfa328388e19adf.
- Expected speech run: SAEA-SLURP-LIVE-INTENT-SLOTS-SPEECH-V1, with delivery cell live-intent-slots-speech-delivery-v1.
- Speech source while generation runs: /home/chao/saea-worktrees/g6-prepared-recall at d9bfde24.
- Frozen analysis plan: docs/readiness/2026-09-10-slurp-live-system-v1/analysis-plan.json, SHA-256 646304a6540eda1483c8d92be7990f075edb0e9b420fef65960c103b58422ef0.

The draft config is docs/readiness/2026-09-10-slurp-live-system-v1/paired-score-analysis-draft.json. Its PENDING values are intentional and must refuse the read-only comparator until root binds the sealed speech manifest and both complete-score records.

## Score once after both derived manifests are complete

Create a two-line JSONL job file at DATA/analysis/SAEA-SLURP-LIVE-INTENT-SLOTS-PAIRED-ANALYSIS-V1/complete-score-jobs.jsonl. The rows use unique job identifiers control-delivery and speech-delivery and the two derived delivery manifest paths. Do not use raw phase parents. Do not add an operation field and do not use finalize for this already sealed recovery delivery.

Use the shared source checkout selected by root and run:

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/chao/saea-worktrees/g6-prepared-recall/src SPEECHRL_DATA_DIR=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data /home/chao/.venvs/speechrl/bin/python -B -m speech_aware_evidence_acquisition.core.driver.cli score-batch --jobs DATA/analysis/SAEA-SLURP-LIVE-INTENT-SLOTS-PAIRED-ANALYSIS-V1/complete-score-jobs.jsonl --output-dir DATA/analysis/SAEA-SLURP-LIVE-INTENT-SLOTS-PAIRED-ANALYSIS-V1/complete-score-batch --workers 1 --include-per-sample

The output directory must be new or empty. The shared batch runner verifies each manifest, invokes one complete official scoring process per delivery manifest, retains per-sample rows, and writes control-delivery.score.json, speech-delivery.score.json, their complete-score receipts, and batch-summary.json. It does not shard or average official scoring. Do not rerun either job if the output directory already records it.

## Bind and run the model-free paired read

After both jobs succeed, root must bind the five pending source values in the draft config: the speech delivery manifest SHA-256; the control and speech score SHA-256 values; and the control and speech complete-score receipt SHA-256 values. Record the resulting final config SHA-256 in the custody record. The score_compare_cli config uses the manifest and score bindings directly; the two complete-score receipt hashes remain required review evidence even though that reader takes score documents as inputs.

Then run the read-only shared comparator once:

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/chao/saea-worktrees/g6-prepared-recall/src SPEECHRL_DATA_DIR=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data /home/chao/.venvs/speechrl/bin/python -B -m speech_aware_evidence_acquisition.analysis.score_compare_cli --config docs/readiness/2026-09-10-slurp-live-system-v1/paired-score-analysis-draft.json --output DATA/analysis/SAEA-SLURP-LIVE-INTENT-SLOTS-PAIRED-ANALYSIS-V1/paired-contrasts.json

This comparison makes zero scorer calls. It returns the primary NEW500 paired speaker-cluster bootstrap with 10,000 draws and seed 20260903, plus scenario-stratified row sensitivity, natural-mixture strata, equal-scenario means, and OLD500 and DEV1000 reporting populations. It separately reports per-row mean SLU-F1 and pooled-count micro SLU-F1. Scenario, action, and joint scenario-action accuracy are included for the frozen nonnegative point-change guard.

No outcome conclusion is permitted before pair sealing, the two one-time official scores, hash binding, and owner review.