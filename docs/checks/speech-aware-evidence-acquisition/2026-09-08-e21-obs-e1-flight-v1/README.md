# OBS-E1 flight receipt — `SAEA-E21-OBS-E1-SPEAKER-TURN-UNITS-V1`

**RESULT: REJECTED (HARM), under section 6 of the preregistration exactly as written.** Corpus WER
improved by **+1.0487 points, CI90 [+0.9253, +1.1745]**; ConEC-mirror PERSON entity WER — the metric
this cell was aimed at — moved the wrong way by **−2.0912 points, CI90 [−3.1701, −1.0978]**, and the
HARM branch fires on `CI90 UB(ΔPERSON) < 0`.

**This directory records the FLIGHT and its reads. The verdict, its reasoning and its claim surface
live in `docs/readiness/2026-09-08-e21-obs-speaker-turn-units-v1-verdict.md`.**

| | |
|---|---|
| exposure row | `SAEA-E21-OBS-E1-SPEAKER-TURN-UNITS-V1` (`bounded-discovery-probe`), registered and committed at study commit `979a730e` BEFORE the first contact |
| owner GO | 2026-09-07, umbrella Decision 4 |
| preregistration | `docs/readiness/2026-09-07-e21-obs-speaker-turn-units-v1-preregistration.md`, with its 2026-09-08 and 2026-09-08 (v2) addenda |
| comparator | `SAEA-E21-FULL44-DIRECT-BASELINE-V2`, attempt `attempt-20260904T233816Z-bcd338` |
| attempt | `attempt-20260908T150858Z-c597a8`, manifest `COMPLETED` and `FINALIZED`, study commit `979a730e`, `study_repo_dirt` empty |
| identity | config `4e5549ee9eed…`, protocol `39b7cc2c4b07…`, split `fcc1b0bc…d69e`, unit plan `0f5f0139…8eb03b` |
| serving | ATTACHED to the coordinator's resident session `e21-np6-c36864-20260908` (receipt sha256 `de3ff630…e7fc`), `-c 36864 -np 6`, 6 slots × 6,144, port 8080 loopback; started no server and stopped none |
| MLflow | `8a49e159c12e4f16951ac4b24a6ba73c` |

## What flew

5,122 speaker-turn units over the 44 frozen `earnings21-original` discovery calls, against the
comparator's 1,593 fixed 90-second windows. One factor moves — the transport unit — and everything
else is the comparator's byte for byte. 141,345.852687 s of cut audio (identical to the comparator's
to the digit) and 151,589.852687 s delivered (the difference is 5,122 × 2.0 s of digital silence
tail). Realized 1.0657 GPU-h of 3.4 planned and 4.0 registered; 5,122 calls of 5,635 planned and
6,000 registered; paid API spend 0. Throughput 51.529 units/min, realized realtime 36.84×, wall
99.4 min. Three units saturated the 1,024-token decode cap; zero were skipped. One attempt, no
recovery re-registration.

## Two gates that ran before any score file was opened

**Identity anchor: PASS.** The comparator reproduces its sealed 8.19952 / 22.48886 / 4.73038 /
90.73351 / 0.02780 through this verdict's own instrument.

**Section 6's byte-level falsifier: PASS on 44 of 44 calls, zero failures.** Concatenating each
call's delivered unit slices with the 2.0-second tails removed reproduces that call's committed
`saea-diarization-v1` `audio_sha256` exactly, and every per-unit span, tail, byte count, hash chain
and OBS trace field holds across all 5,122 units. `flight/falsifier.json`.

## Contents

| path | what it is |
|---|---|
| `flight/falsifier.json` | section 6's falsifier, per call and per unit, plus the prompt/completion token distribution and the saturation list |
| `flight/flight-receipt.json` | the sealed run: identity, plan, split, transport unit per call, tokens, cost, throughput, serving and monitor summary, artifact hashes |
| `flight/rescore-bundles.json`, `flight/jobs.jsonl`, `flight/batch-summary.json` | the four one-scorer re-scoring bundles and their `core.scoring_batch` run (4 of 4 succeeded, one complete verified manifest per process, never sharded) |
| `flight/verified-score-read.json` | the four agentic metrics collapsed into one verified score read |
| `verdict/result-summary.json` | the paired read: identity anchor, per-metric intervals, the section 6 decision, the guards against the Earnings-21 own-null half-widths, the per-call table, the strata and the unit-grain distribution |
| `verdict/per-call-table.md` | all 44 calls, with units, cut and delivered seconds, and every metric |
| `verdict/common-refinement.json` | section 4's preregistered SECONDARY read: both arms charged to the sealed 90-second window grid by reference index, 1,593 rows, saves/harms/ties and per-window strata |

## Code

`scripts/e21_obs_e1_falsifier.py`, `scripts/e21_obs_e1_flight_receipt.py`,
`scripts/e21_obs_e1_common_refinement.py`, `scripts/build_e21_obs_e1_verdict.py`,
`scripts/render_e21_obs_e1_per_call_table.py`. Every statistic comes out of the registered
instruments (`analysis.paired.resampled_statistic` at seed 20260903 / 10,000 replicates / CI90,
`analysis.e21_window_pairing`, `core.scoring_batch`), reached through
`scripts/build_e21_tail2s_verdict.py` so that this cell and the null replicate it is read against
come out of one dialect rather than two.

## Not authorized by this receipt

Discovery data. No superiority, generality, published-comparison or Stage-3 claim, and no
paper-facing effectiveness claim at all (n = 44 clusters is below the program's `n >= 400` rule). No
Earnings-22 contact, no fstalign install, no diarizer re-run, no speaker naming, and no OBS-E1b
contact-matched control — that arm is named as the follow-up and is deliberately not registered.
