# Root structural review: independent role contexts and original sample timing

Recorded: 2026-10-03T13:43:33.585350+00:00

Both configurations completed four structural-only rows. No task-quality or comparative-performance conclusion is authorized. The cache state was inherited and no reset, warmup, save or restore was performed.

| Configuration | Model contacts | Mean sample seconds | First admitted sample seconds | Remaining-sample mean seconds | Batch wall / sample seconds |
|---|---:|---:|---:|---:|---:|
| legacy-role | 25 | 69.391 | 50.253 | 75.771 | 20.593 |
| before-speech-role | 25 | 72.158 | 64.523 | 74.703 | 23.063 |

Timing spans admission to settled workflow, including internal waits and actual-request FIT. Preparation, final persistence and scoring are outside this boundary. Batch wall per sample describes throughput, not individual latency. First admission is not a proven cold start; remaining admissions are not guaranteed warm.

The next matrix must measure official SLU-F1, intent and reliable completion alongside these timings. Keep each role independently editable. Treat cache reuse as a diagnostic, and judge any quality/latency tradeoff explicitly.

## Original per-node timings

Server prefill and generation times have different boundaries from client transport time. These are arithmetic means per contact, not per-sample wall times. Reuse is token-weighted original input reuse; final resident tokens are excluded.

| Configuration | Node | Contacts | Mean client seconds | Mean prefill seconds | Mean generation seconds | Input reuse |
|---|---|---:|---:|---:|---:|---:|
| legacy-role | perception | 4 | 9.329 | 0.566 | 8.736 | 63.13% |
| legacy-role | solver | 7 | 4.826 | 2.985 | 1.527 | 25.44% |
| legacy-role | reviewer | 7 | 9.070 | 3.609 | 5.055 | 25.27% |
| legacy-role | planner | 7 | 6.064 | 4.113 | 0.058 | 24.54% |
| before-speech-role | perception | 4 | 7.176 | 0.575 | 6.574 | 67.57% |
| before-speech-role | solver | 7 | 4.693 | 3.020 | 1.467 | 26.31% |
| before-speech-role | reviewer | 7 | 11.509 | 3.346 | 8.073 | 25.90% |
| before-speech-role | planner | 7 | 6.103 | 4.193 | 0.052 | 25.99% |

The measured reuse rates alone do not determine sample latency. In these two small proofs, the ordering of overall means differs from the ordering of means excluding first admission. Reviewer generation duration also differs. Preserve all observations and compare complete replicated task quality and latency before selecting a configuration; do not select the preferred metric after seeing values.
