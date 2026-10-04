# K16 structural timing observations

All sixteen original branches completed four structural samples each. These are source-bound engineering observations, not scientific efficacy, speedup or policy-selection evidence. No official score or optimizer export is included. Keep all original branches for the separately registered N20 comparison.

## Measurement boundaries

Sample elapsed time is original admission-to-settled-workflow wall time, including model/tool waits, actual-request FIT and cleanup. Data preparation, final persistence and scoring are excluded. First means first admitted, not first finished. Four samples fill four slots; no samples remain after the first four admissions, so this family cannot estimate steady subsequent-wave latency.

Node values are per-model-contact means, including revisits. Client transport, server prefill and server decode have distinct boundaries; do not add them together. Contact totals are not sample wall time or isolated GPU time. Cache reuse is token-weighted observed input reuse; it does not identify an eviction cause, guarantee residency or prove task quality.

## Sample wall time

| Branch | Samples | All mean (s) | First admitted (s) | Remaining three mean (s) | After first four admissions |
| --- | ---: | ---: | ---: | ---: | --- |
| 01 | 4 | 25.830 | 21.159 | 27.387 | Not observed |
| 02 | 4 | 33.069 | 24.550 | 35.909 | Not observed |
| 03 | 4 | 49.789 | 62.429 | 45.576 | Not observed |
| 04 | 4 | 43.664 | 36.443 | 46.071 | Not observed |
| 05 | 4 | 23.542 | 21.747 | 24.140 | Not observed |
| 06 | 4 | 28.202 | 23.850 | 29.653 | Not observed |
| 07 | 4 | 59.300 | 69.463 | 55.912 | Not observed |
| 08 | 4 | 40.915 | 34.704 | 42.985 | Not observed |
| 09 | 4 | 25.185 | 25.054 | 25.229 | Not observed |
| 10 | 4 | 28.165 | 23.256 | 29.801 | Not observed |
| 11 | 4 | 49.984 | 59.526 | 46.804 | Not observed |
| 12 | 4 | 47.565 | 37.928 | 50.777 | Not observed |
| 13 | 4 | 22.235 | 22.111 | 22.276 | Not observed |
| 14 | 4 | 28.244 | 24.445 | 29.511 | Not observed |
| 15 | 4 | 60.047 | 67.945 | 57.414 | Not observed |
| 16 | 4 | 41.146 | 32.331 | 44.084 | Not observed |

## Per-node model contact time

All contacts have observed timing values in this family. Means retain every contact, including revision visits.

| Branch | Node | Contacts | Client mean (s) | Prefill mean (s) | Decode mean (s) | Input reuse |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 01 | Perception | 4 | 4.516 | 1.029 | 2.812 | 62.7% |
| 01 | Solver | 6 | 8.694 | 2.342 | 4.808 | 57.1% |
| 01 | Reviewer | 6 | 2.681 | 0.389 | 2.169 | 92.8% |
| 01 | Planner | 6 | 0.528 | 0.384 | 0.099 | 92.6% |
| 02 | Perception | 4 | 4.417 | 1.535 | 2.660 | 59.5% |
| 02 | Solver | 5 | 9.848 | 3.733 | 4.253 | 31.0% |
| 02 | Reviewer | 5 | 4.805 | 0.356 | 4.348 | 92.9% |
| 02 | Planner | 5 | 5.736 | 4.747 | 0.336 | 20.2% |
| 03 | Perception | 4 | 4.582 | 1.792 | 2.644 | 59.5% |
| 03 | Solver | 5 | 12.314 | 4.625 | 6.066 | 22.5% |
| 03 | Reviewer | 5 | 16.718 | 4.180 | 11.882 | 22.2% |
| 03 | Planner | 5 | 4.237 | 4.027 | 0.170 | 21.0% |
| 04 | Perception | 4 | 4.497 | 1.647 | 2.646 | 62.7% |
| 04 | Solver | 4 | 14.885 | 5.376 | 7.682 | 23.5% |
| 04 | Reviewer | 4 | 14.428 | 4.666 | 8.792 | 23.5% |
| 04 | Planner | 4 | 6.712 | 4.445 | 0.408 | 22.8% |
| 05 | Perception | 4 | 4.713 | 1.086 | 2.955 | 62.7% |
| 05 | Solver | 5 | 9.818 | 2.789 | 5.130 | 50.3% |
| 05 | Reviewer | 5 | 1.887 | 0.378 | 1.444 | 92.8% |
| 05 | Planner | 5 | 0.560 | 0.372 | 0.103 | 92.8% |
| 06 | Perception | 4 | 4.495 | 1.289 | 2.900 | 59.5% |
| 06 | Solver | 4 | 10.802 | 3.365 | 5.164 | 34.8% |
| 06 | Reviewer | 4 | 5.161 | 0.351 | 4.687 | 92.7% |
| 06 | Planner | 4 | 4.692 | 3.585 | 0.044 | 21.0% |
| 07 | Perception | 4 | 4.639 | 1.809 | 2.689 | 59.5% |
| 07 | Solver | 6 | 12.299 | 5.210 | 5.698 | 21.8% |
| 07 | Reviewer | 6 | 14.925 | 4.300 | 9.970 | 21.5% |
| 07 | Planner | 6 | 6.955 | 5.648 | 0.643 | 20.4% |
| 08 | Perception | 4 | 4.514 | 1.787 | 2.618 | 62.7% |
| 08 | Solver | 4 | 15.091 | 5.131 | 7.911 | 24.8% |
| 08 | Reviewer | 4 | 14.256 | 4.194 | 9.475 | 24.8% |
| 08 | Planner | 4 | 4.042 | 3.228 | 0.213 | 24.0% |
| 09 | Perception | 4 | 5.148 | 1.160 | 3.229 | 62.7% |
| 09 | Solver | 5 | 9.483 | 2.992 | 4.426 | 49.5% |
| 09 | Reviewer | 5 | 2.734 | 0.381 | 2.282 | 93.1% |
| 09 | Planner | 5 | 0.829 | 0.530 | 0.187 | 92.8% |
| 10 | Perception | 4 | 4.273 | 1.382 | 2.690 | 59.5% |
| 10 | Solver | 4 | 10.564 | 3.242 | 5.180 | 35.1% |
| 10 | Reviewer | 4 | 4.150 | 0.377 | 3.616 | 92.5% |
| 10 | Planner | 4 | 5.804 | 4.655 | 0.215 | 21.3% |
| 11 | Perception | 4 | 4.603 | 1.506 | 2.840 | 59.5% |
| 11 | Solver | 5 | 14.224 | 5.089 | 7.520 | 22.5% |
| 11 | Reviewer | 5 | 13.822 | 3.994 | 9.350 | 22.2% |
| 11 | Planner | 5 | 5.682 | 4.432 | 0.286 | 21.1% |
| 12 | Perception | 4 | 4.783 | 1.599 | 2.622 | 62.7% |
| 12 | Solver | 5 | 12.005 | 5.106 | 5.031 | 23.4% |
| 12 | Reviewer | 5 | 12.884 | 4.323 | 7.536 | 23.6% |
| 12 | Planner | 5 | 6.366 | 5.210 | 0.517 | 22.7% |
| 13 | Perception | 4 | 4.554 | 1.026 | 2.940 | 62.7% |
| 13 | Solver | 4 | 10.759 | 3.496 | 4.821 | 36.5% |
| 13 | Reviewer | 4 | 2.971 | 0.377 | 2.485 | 93.0% |
| 13 | Planner | 4 | 0.568 | 0.354 | 0.105 | 92.6% |
| 14 | Perception | 4 | 4.620 | 1.319 | 2.944 | 59.5% |
| 14 | Solver | 4 | 10.489 | 3.274 | 4.989 | 35.1% |
| 14 | Reviewer | 4 | 6.066 | 0.363 | 5.591 | 92.6% |
| 14 | Planner | 4 | 4.098 | 3.728 | 0.244 | 21.2% |
| 15 | Perception | 4 | 4.655 | 1.514 | 2.886 | 59.5% |
| 15 | Solver | 6 | 11.904 | 4.811 | 5.752 | 21.7% |
| 15 | Reviewer | 6 | 17.040 | 3.612 | 12.387 | 21.4% |
| 15 | Planner | 6 | 5.390 | 4.311 | 0.158 | 20.4% |
| 16 | Perception | 4 | 4.621 | 1.247 | 2.687 | 62.7% |
| 16 | Solver | 4 | 13.849 | 5.389 | 6.255 | 24.2% |
| 16 | Reviewer | 4 | 14.457 | 5.434 | 7.783 | 24.3% |
| 16 | Planner | 4 | 4.671 | 3.643 | 0.282 | 23.5% |

## Source custody

The root-only sources below bind original request/response records, all64 terminal deliveries,76 valid visible Reviewer handoffs,292 model contacts and292 actual-request FIT receipts. Official scorer contacts:0. Rendering adds no model, tokenizer or scorer contact.

- `structural-acceptance-v1.json`: SHA-256 `16172a371d9c80d03525fd7f4810c96e1178613fbb454060edadbfade0f6f5e3`; retained in `coordination/context-template-k16-structural-owner227-v1`.
- `root-node-timing-v1.json`: SHA-256 `7ac276e3fd33c6e65562e427604914a07c57c91c53d8f6c254d4ef0b80195a3a`; retained in `coordination/context-template-k16-structural-owner227-v1`.
- `root-sample-timing-v1.json`: SHA-256 `7199d573f70a244d66c02fb50b790304b260f2aca1158b6cc2ae092bc04f1620`; retained in `coordination/context-template-k16-structural-owner227-v1`.
