# SLURP discriminative-value scoring readiness

Status: model-free analysis template only. The two prospective generation cells remain held; this note authorizes no generation, score, or analysis run.

## Reusable shared entry

The exact reader is speech_aware_evidence_acquisition.analysis.score_compare_cli.run(config_path, output_path). CLI form:

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<analysis-checkout>/src SPEECHRL_DATA_DIR=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data /home/chao/.venvs/speechrl/bin/python -B -m speech_aware_evidence_acquisition.analysis.score_compare_cli --config <config.json> --output <output.json>

It accepts only execution_profile model-free-check. Each input binds a complete score document and exact sealed manifest. The reader verifies hashes, verifies the manifest, checks score-to-manifest identity, and refuses missing, extra, or duplicate sample IDs. Source: src/speech_aware_evidence_acquisition/analysis/score_compare_cli.py:125-176.

Use the root-owned docs/readiness/2026-09-11-slurp-discriminative-values-analysis.template.json. Replace every awaiting manifest, score, and complete-score-receipt hash only after the artifact seals. Use one contrast, control left and treatment right, scorer slurp-slu-official, and populations NEW500, OLD500, DEV1000.

Draft configuration hashes below record the audit-time state only; final registered plans bind completed preparation and readiness. Prospective configs:
- configs/experiment/slurp-discriminative-value-historical-v1.json, SHA-256 136b7833ab783496f7f929e2d01d822b7569e4f657d93751fa4076c544a593d8.
- configs/experiment/slurp-discriminative-value-span-v1.json, SHA-256 6d2da56681dde2811694cf4f888768c620e1bed35c97da754d193790a4de2ffe.
- Baseline fragment hashes: 162268d02129e2636367328413baab5644184d465ec8efb8f3162cbfc12ccf90 and d7d0c29536b04b3d62626e938b591b00584ae0ddbc07a79a04c399c9caf26436.

Both score bindings must use the same complete 1000-row roster and official scorer. Metadata is /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/analysis/SAEA-SLURP-NULL-NEW500-CALIBRATION-RECOVERY-V1/roster-metadata.json, SHA-256 2f0e52cd159296c026fa87a54563f88418875364b23a3aabf146c3f44403b59b. Its rows are keyed by sample ID and carry scenario and speaker. The frozen full and primary pins are DEV-1000 and DEV-1000-NEW500; OLD500 is full minus NEW500.

## Metrics and uncertainty

Keep slu_f1_f1; intent labels belong to the fixed predecessor and are not a fresh treatment outcome; seed 20260903; 10,000 replicates; CI90. Mean per-row F1 is slu_f1_f1. Add micro_metrics slu_f1_micro with TP/FP/FN fields slu_f1_word_{tp,fp,fn} plus slu_f1_char_{tp,fp,fn}. This is a separate pooled-count F1 estimand, never a row mean. Shared field names across different micro metrics are allowed; within one metric, groups must be nonempty, unique, and non-overlapping.

Mean metrics use score_compare_cli.compare, retaining scenario-stratified paired estimates and speaker-clustered sensitivity (score_compare_cli.py:110-122). Micro metrics use null_calibration.pooled_f1 and paired.resampled_statistic (score_compare_cli.py:15-78,198-206). Micro bootstrap uses the unchanged seed 20260903. Scenario is the grouping for per-stratum and equal-stratum tables; speaker is only the resampling cluster.

The generic analysis.pooled_ratio_compare.run(config_path, output_path) is for ratio tables already extracted; it expects id_field, expected_ids_count, metrics, groupings, and pinned JSON inputs. Its public compare_pooled_ratios API is at pooled_ratio_compare.py:194-284; its CLI schema and roster checks are at :331-390. It is not a replacement for the SLURP score-document reader.

## Readiness gates and boundaries

Before the model-free read, bind both complete single-phase slot manifests, both official score documents, and both complete-score receipts. Verify exactly the full 1000 IDs and required fields in each score. Use existing score stats only when manifest, scorer identity, roster, and row schema are hash-bound; do not infer missing or spurious rates from an unbound summary.

Report NEW500 primary, OLD500 secondary, and DEV1000 secondary with natural mixture and equal scenario weighting. The descriptive checks are positive-change and delivery-integrity observations, not non-inferiority, equivalence, or treatment-derived margins. No conclusion is available until both future manifests and one complete official score per arm are sealed and root releases the hash-bound read.

Implementation provenance is conditional: micro metrics add null_calibration.py; explicit scorer view aliases add null_calibration_cli.py. Without micro or view options, legacy implementation metadata shape and numerical behavior remain unchanged.
