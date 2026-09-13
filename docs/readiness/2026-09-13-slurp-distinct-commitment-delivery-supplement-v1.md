# Distinct commitment raw delivery diagnostic supplement

Status: complete, model-free supplement. Preserve both v1 and v2 outputs and the unchanged primary inconclusive SLU verdict. The initial delivered-text attempt counters are not raw proposal counters; use the source-verified flags below.

Output: /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/analysis/SAEA-SLURP-DISTINCT-COMMITMENT-PAIRED-ANALYSIS-V1/conditional-diagnostics-v2.json
SHA-256: a9fdac614352a767719694d893b65f8431914daff4874d3ecb696636d296a17b
Runner code: 0bc53729; shared slurp_topn_diagnostics_cli and the already registered diagnostic config. Root verified source, branches, every scenario table, observed-width tables and per-scenario width tables match v1 exactly. No model, encoder, tokenizer, backend or scorer contact was added.

| Population | Arm | n | Refused | Illegal intent | Malformed response | Outside shortlist | Attempted switch from fixed first |
|---|---|---:|---:|---:|---:|---:|---:|
| NEW500 | closed_joint | 500 | 5 | 4 | 1 | 0 | not applicable |
| NEW500 | hard_first | 500 | 7 | 6 | 1 | 0 | 19 |
| OLD500 | closed_joint | 500 | 10 | 9 | 1 | 0 | not applicable |
| OLD500 | hard_first | 500 | 11 | 10 | 1 | 0 | 37 |
| DEV1000 | closed_joint | 1000 | 15 | 13 | 2 | 0 | not applicable |
| DEV1000 | hard_first | 1000 | 18 | 16 | 2 | 0 | 56 |

All raw phase diagnostics were available. Hypothesis-state-invalid counts were zero. Outside-shortlist zero is now supported by the preserved delivery flags, rather than inferred from empty refused deliveries.

The hard-first phase explicitly instructs the model to preserve candidate one and its delivery rule enforces that commitment. Its 56 attempted switches are instruction deviations, not successful independent rescues. The joint phase explicitly permits choice among supplied candidates. Different commitment instructions and matched delivery rules are the intended intervention; both retain the same phase program, source and candidate contracts.

The 15 joint refusals explain only part of the 231 incorrect final intents across DEV1000. They cannot explain the much larger unresolved entity partition. Keep selection, extraction and delivery errors separate. Neither these counts nor the source-relative rescue counts establish a full-system advantage.

Full width and per-scenario raw flag tables remain in the v2 artifact. This supplement closes the pending raw-proposal caveat in the conditional-result-v1 report without rewriting that record.
