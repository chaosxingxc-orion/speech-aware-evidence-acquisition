# Earnings-22 ESB short-form: per-call table

Run `SAEA-E22-ESB-SHORTFORM-ALIGNMENT-V1`, attempt `attempt-20260905T044432Z-8f23ee`, study commit `7f5d2837`. Paper-facing scorer `asr-wer-esb-whisper`, corpus aggregation (total S+D+I over total reference words).

| call | utterances | audio s | ref words | S | D | I | corpus WER % (Whisper) | mean per-utt % | corpus WER % (saea-scoring-v1) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 4432298 | 351 | 2527.4 | 5948 | 448 | 154 | 716 | **22.159** | 30.181 | 25.983 |
| 4450488 | 508 | 4269.9 | 8694 | 387 | 157 | 683 | **14.113** | 19.541 | 20.383 |
| 4470290 | 178 | 1584.8 | 3566 | 265 | 89 | 343 | **19.546** | 23.595 | 24.639 |
| 4479741 | 473 | 3499.8 | 8436 | 362 | 175 | 689 | **14.533** | 30.127 | 19.611 |
| 4483338 | 619 | 4024.3 | 11516 | 478 | 213 | 1049 | **15.109** | 28.848 | 20.212 |
| 4485244 | 606 | 3588.4 | 10759 | 296 | 160 | 1132 | **14.760** | 33.178 | 19.027 |
| **all six** | **2735** | **19494.6** | **48919** | **2236** | **948** | **4612** | **15.937** | **28.129** | **20.896** |

Equal-call weighting (mean of the six per-call corpus figures): **16.703 %**. Natural mixture (the corpus figure above): **15.937 %**.

## By utterance duration (Whisper normalizer, corpus)

| decile | seconds | utterances | ref words | corpus WER % |
|---:|---|---:|---:|---:|
| 1 | 0.22-1.34 | 273 | 815 | 52.761 |
| 2 | 1.34-2.54 | 274 | 1792 | 27.734 |
| 3 | 2.54-3.68 | 273 | 2473 | 27.295 |
| 4 | 3.70-4.80 | 274 | 3181 | 21.566 |
| 5 | 4.82-6.12 | 273 | 3955 | 17.016 |
| 6 | 6.12-7.46 | 274 | 4779 | 17.117 |
| 7 | 7.46-8.98 | 273 | 5643 | 13.255 |
| 8 | 9.00-11.02 | 274 | 6789 | 12.535 |
| 9 | 11.02-14.04 | 273 | 7987 | 13.559 |
| 10 | 14.06-36.36 | 274 | 11505 | 11.604 |

Longer than 20 s: 74 utterances, 3810 reference words, corpus WER 11.653 %. At most 20 s: 2661 utterances, 45109 reference words, corpus WER 16.298 %.

## The three clamped utterances

| id | cut seconds | published end | decoded parent | ref words | WER % |
|---|---:|---:|---:|---:|---:|
| 4432298-351 | 19.060 | 2643.920 | 2643.840 | 16 | 18.750 |
| 4470290-178 | 13.104 | 1627.060 | 1626.984 | 20 | 10.000 |
| 4483338-619 | 8.636 | 4159.980 | 4159.896 | 12 | 16.667 |

