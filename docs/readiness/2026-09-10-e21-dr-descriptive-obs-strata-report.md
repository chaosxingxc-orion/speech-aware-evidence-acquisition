# E21 DR retrospective descriptive OBS geometry strata

This report is retrospective and descriptive. The primary DR results were already known before this calculation. It does not rerun scoring or bootstrap intervals, and it does not alter any primary admission gate.

The frozen geometry receipt passed all 44 calls and 1,593 DR windows: SHA-256 3549a0a9cfcce25ef8114d73834f93b668984b7998313d8234b869606b048b20.

Fixed content-free variables are overlap-weighted mean full-unit duration (<=4, >4-8, >8-16, >16 seconds), turn-boundary end-cut overlap share (0, >0-0.5, >0.5), and strict internal boundaries (0, 1-4, >=5). Speaker dominance remains separately preserved.

Each delta is delivery minus historical direct in percentage points. Negative error-rate deltas favor the delivery. Numeric accuracy is unavailable in all strata because its saved numerator and denominator are whole-call bags that cannot be assigned faithfully to windows.

## overlap_weighted_mean_full_unit_duration_seconds

| Bin | Windows | Delivery | WER delta pp | PERSON delta pp | Nonentity delta pp | Insertion delta pp | Numeric |
|---|---:|---|---:|---:|---:|---:|---|
| <=4 | 0 | Unit constrained | unavailable | unavailable | unavailable | unavailable | unavailable whole-call bag |
| <=4 | 0 | Unit free | unavailable | unavailable | unavailable | unavailable | unavailable whole-call bag |
| <=4 | 0 | Self constrained | unavailable | unavailable | unavailable | unavailable | unavailable whole-call bag |
| <=4 | 0 | Self free | unavailable | unavailable | unavailable | unavailable | unavailable whole-call bag |
| >4-8 | 5 | Unit constrained | -1.5237 | +0.0000 | -1.5154 | +0.1510 | unavailable whole-call bag |
| >4-8 | 5 | Unit free | -1.8340 | +0.0000 | -1.4726 | -0.5803 | unavailable whole-call bag |
| >4-8 | 5 | Self constrained | +0.0000 | +0.0000 | +0.0000 | +0.0000 | unavailable whole-call bag |
| >4-8 | 5 | Self free | +0.0000 | +0.0000 | +0.0000 | +0.0000 | unavailable whole-call bag |
| >8-16 | 32 | Unit constrained | +0.0487 | +2.1474 | +0.4313 | -0.5266 | unavailable whole-call bag |
| >8-16 | 32 | Unit free | +2.2826 | -0.8386 | +1.3324 | +1.0629 | unavailable whole-call bag |
| >8-16 | 32 | Self constrained | -0.0315 | -2.5000 | +0.0000 | +0.0000 | unavailable whole-call bag |
| >8-16 | 32 | Self free | -0.0646 | -2.5000 | +0.0172 | -0.0321 | unavailable whole-call bag |
| >16 | 1556 | Unit constrained | -1.0919 | +1.7827 | -0.0351 | -1.0755 | unavailable whole-call bag |
| >16 | 1556 | Unit free | +5.6116 | +2.8140 | +1.3261 | +4.2903 | unavailable whole-call bag |
| >16 | 1556 | Self constrained | -0.0051 | -0.0706 | -0.0044 | -0.0006 | unavailable whole-call bag |
| >16 | 1556 | Self free | -0.0005 | -0.1059 | -0.0100 | +0.0094 | unavailable whole-call bag |

## turn_boundary_end_cut_overlap_share

| Bin | Windows | Delivery | WER delta pp | PERSON delta pp | Nonentity delta pp | Insertion delta pp | Numeric |
|---|---:|---|---:|---:|---:|---:|---|
| 0 | 1174 | Unit constrained | -1.2130 | +1.4735 | -0.0883 | -1.1245 | unavailable whole-call bag |
| 0 | 1174 | Unit free | +5.6599 | +2.5707 | +1.0933 | +4.5725 | unavailable whole-call bag |
| 0 | 1174 | Self constrained | -0.0046 | -0.0526 | -0.0045 | +0.0004 | unavailable whole-call bag |
| 0 | 1174 | Self free | -0.0160 | -0.0526 | -0.0360 | +0.0181 | unavailable whole-call bag |
| >0-0.5 | 363 | Unit constrained | -0.6925 | +1.9394 | +0.1334 | -0.9011 | unavailable whole-call bag |
| >0-0.5 | 363 | Unit free | +5.1863 | +2.3190 | +1.9472 | +3.2661 | unavailable whole-call bag |
| >0-0.5 | 363 | Self constrained | -0.0092 | -0.3333 | -0.0040 | -0.0035 | unavailable whole-call bag |
| >0-0.5 | 363 | Self free | +0.0344 | -0.4444 | +0.0597 | -0.0178 | unavailable whole-call bag |
| >0.5 | 56 | Unit constrained | -0.6728 | +6.3849 | +0.1416 | -0.9145 | unavailable whole-call bag |
| >0.5 | 56 | Unit free | +5.7151 | +8.4070 | +1.8480 | +3.6412 | unavailable whole-call bag |
| >0.5 | 56 | Self constrained | +0.0000 | +0.0000 | +0.0000 | +0.0000 | unavailable whole-call bag |
| >0.5 | 56 | Self free | +0.0524 | +0.0000 | +0.0626 | -0.0091 | unavailable whole-call bag |

## strict_internal_unit_boundary_count

| Bin | Windows | Delivery | WER delta pp | PERSON delta pp | Nonentity delta pp | Insertion delta pp | Numeric |
|---|---:|---|---:|---:|---:|---:|---|
| 0 | 6 | Unit constrained | -33.4842 | unavailable | +7.4074 | -41.1765 | unavailable whole-call bag |
| 0 | 6 | Unit free | -21.6643 | unavailable | +4.1667 | -26.5423 | unavailable whole-call bag |
| 0 | 6 | Self constrained | +0.0000 | unavailable | +0.0000 | +0.0000 | unavailable whole-call bag |
| 0 | 6 | Self free | +0.0000 | unavailable | +0.0000 | +0.0000 | unavailable whole-call bag |
| 1-4 | 1243 | Unit constrained | -1.2220 | +0.7997 | -0.0938 | -1.1161 | unavailable whole-call bag |
| 1-4 | 1243 | Unit free | +5.7637 | +1.9398 | +1.2161 | +4.5721 | unavailable whole-call bag |
| 1-4 | 1243 | Self constrained | -0.0061 | -0.1029 | -0.0051 | +0.0000 | unavailable whole-call bag |
| 1-4 | 1243 | Self free | -0.0098 | -0.1029 | -0.0275 | +0.0158 | unavailable whole-call bag |
| >=5 | 344 | Unit constrained | -0.4227 | +4.0035 | +0.2541 | -0.8200 | unavailable whole-call bag |
| >=5 | 344 | Unit free | +4.8081 | +4.3911 | +1.7185 | +3.0269 | unavailable whole-call bag |
| >=5 | 344 | Self constrained | -0.0037 | -0.2053 | -0.0015 | -0.0025 | unavailable whole-call bag |
| >=5 | 344 | Self free | +0.0267 | -0.3080 | +0.0519 | -0.0165 | unavailable whole-call bag |

## Provenance

- Geometry receipt: /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/coordination/e21-dr-obs-v3-geometry-audit.json; SHA-256 3549a0a9cfcce25ef8114d73834f93b668984b7998313d8234b869606b048b20.
- Saved window metadata: /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/analysis/SAEA-E21-DR-PACKETS-SAVED-SCORE-ANALYSIS-V1/window-metadata.json; SHA-256 1c5a7c34e208a4148aa1d2d92f97f2116667285cd77dccdaa5ac990335046e75.
- Saved call metadata: /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/analysis/SAEA-E21-DR-PACKETS-SAVED-SCORE-ANALYSIS-V1/call-metadata.json; SHA-256 5631d6fee9ba032f95abdabf2f9ec9e7fc680b6fe9deb48cc37e50d72a12af23.
- Machine-readable artifact: /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/coordination/e21-dr-descriptive-obs-strata-v1.json; SHA-256 42aaf144762d9ff1259b421b16b59ac07ac921f2c7caf8a734249375a269817a.

The artifact records pooled saved numerator and denominator counts for WER, PERSON, nonentity, and insertion in every bin and delivery.
