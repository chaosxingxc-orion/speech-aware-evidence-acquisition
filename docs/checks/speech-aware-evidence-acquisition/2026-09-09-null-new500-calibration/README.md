# NEW500 null-only calibration

Registered read: SAEA-SLURP-NULL-NEW500-CALIBRATION-RECOVERY-V1.
Authority: OWNER-CONTINUATION-002. Source config committed at de117e74 before execution.

Verified 500 historically exposed rows and 115 speaker clusters. Zero model, encoder, tokenizer and scorer calls.

The primary uses paired speaker-cluster bootstrap, 10,000 draws, seed base 20260903. Metric offsets follow the shared paired implementation. Unrounded values in calibration.json are authoritative.

| Metric | Null delta (pp) | CI90 (pp) | Operational NI margin (pp) |
|---|---:|---|---:|
| action_exact | 0.200000 | [-1.212121, 1.680751] | 1.446436 |
| scenario_action_exact | 0.600000 | [-0.622100, 1.904863] | 1.263481 |
| scenario_exact | 0.600000 | [-0.576923, 1.807365] | 1.192144 |
| slu_f1_f1 | 0.114773 | [-1.298067, 1.467771] | 1.382919 |
| slu_f1_micro | 0.086809 | [-1.820006, 1.940045] | 1.880026 |

These are noise-derived operational margins, not practical equivalence tolerances. Historical pooled margins remain unchanged. For future KU-S4 efficacy the intent lower bound must exceed max(1.4341, aligned null upper bound), which is 1.9048627925746557 pp. NI and two-sided equivalence are distinct predicates.

Both official and normalized scorer tables, per-scenario natural/equal-weight summaries and all source bindings are in calibration.json. This receipt was frozen before KV treatment scores were opened. It does not admit a mechanism.
