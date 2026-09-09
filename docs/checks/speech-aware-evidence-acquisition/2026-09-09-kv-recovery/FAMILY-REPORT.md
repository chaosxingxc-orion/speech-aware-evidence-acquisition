# Historical KV family recovery (2026-09-09)

Retain the example-bearing KC-S1b base for KU-S3. KV-0 is harmful, and the already-completed successor flights lack the prerequisite admission. Their results remain useful retrospective evidence, not newly authorized modules. No model contact or official scoring was added.

| Contrast, NEW500 | Official delta pp | Scenario CI90 pp | Speaker CI90 pp | Normalized delta pp | Equal-scenario official delta pp |
|---|---:|---|---|---:|---:|
| kv1_minus_kv0 | -0.8692 | [-2.1192, 0.3139] | [-2.1613, 0.3608] | -0.8196 | -1.1617 |
| kv1_minus_kv1t | -0.8279 | [-1.8792, 0.1663] | [-1.9478, 0.2308] | -0.7714 | -0.6805 |
| kv2_minus_kv0 | 7.1593 | [5.2446, 9.1233] | [5.0049, 9.5915] | 7.1618 | 5.7974 |
| kv2_minus_kv2t | 1.7140 | [0.1340, 3.2683] | [-0.0853, 3.5981] | 1.5236 | 2.0611 |
| kv3_minus_kv0 | 0.5213 | [-0.7519, 1.8013] | [-0.9302, 2.1154] | 0.4735 | 0.4615 |
| kv3_minus_kv3t | 0.8759 | [-0.4927, 2.2687] | [-0.6411, 2.4865] | 0.6848 | 1.3229 |

The inherited primary uses scenario-stratified paired bootstrap; speaker-clustered intervals are a separately labelled recovery sensitivity. Both use the shared implementation, 10,000 resamples, seed 20260903. NEW500 is historically exposed. The source JSON also retains separate DEV1000 and OLD500 estimates.

KV-2 has a positive original official twin contrast on NEW500, but its matched rotating stratum has delta -1.3766 pp (official) and -1.5497 pp (normalized), failing the inherited positive-sign guard. That stratum has 324 rows and is descriptive under the owner minimum 400 rule. The full-roster gain cannot be claimed as an isolated benefit of correct card content. The speaker-clustered full NEW500 twin interval also includes zero. Do not replace the preregistered rule with the sensitivity after seeing results.

KV-1 and KV-3 have primary intervals spanning zero against both KV-0 and their twins. These null-compatible observations are not equivalence or noninferiority conclusions. No new KV replication or redesign enters the current GPU queue.

Observation is unchanged across this family. ORG builds frozen TRAIN views; no runtime retriever is added in these KV cells. The active difference is USE-side instruction material. KV-2 pooled twins have unequal input volume; KV-3 twins match by measurement rather than construction. Those are explanation limits, not adjusted-away nuisances.

| Run | Rows | Parsed | Admitted outputs | Official micro F1 % | Normalized micro F1 % | Model calls | Prompt tokens | Completion tokens | Sum latency seconds |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| kv0 | 1000 | 998 | 1000 | 41.7535 | 42.5444 | 1000 | 2774082 | 22725 | 1509.267 |
| kv1 | 1000 | 997 | 1000 | 40.3058 | 41.0639 | 1000 | 3211393 | 24880 | 2147.927 |
| kv1t | 1000 | 998 | 1000 | 40.4887 | 41.2044 | 1000 | 3211258 | 24514 | 2252.128 |
| kv2 | 1000 | 998 | 1000 | 47.9102 | 48.7216 | 1000 | 4438995 | 27791 | 3886.393 |
| kv2t | 1000 | 997 | 1000 | 46.3149 | 47.2390 | 1000 | 4265703 | 27700 | 3574.558 |
| kv3 | 1000 | 997 | 1000 | 41.4408 | 42.1165 | 1000 | 2921785 | 18536 | 1639.602 |
| kv3t | 1000 | 997 | 1000 | 41.0980 | 41.8035 | 1000 | 2911623 | 18093 | 1573.731 |

Each run used 2,884.7936875 audio seconds and reports zero tool calls in its generation cost record. Sum of request latencies is not GPU wall time; historical preparation/tokenizer contacts are not included in this cost table. Retry, saturation and schema-fallback counters are not exposed by the inspected score/manifest products and remain explicitly unavailable. Do not infer zero. The original trace bindings are preserved for further deterministic extraction.

The primary paired table is mean per-row F1, whereas the standard-score table is complete-manifest micro F1. They must never be interchanged. NEW500 strict entity, word and character mean-F1 guards, official and normalized, are retained in family-bookkeeping.json. Per-entity-type tables were not retained by these inspected products; no new scorer invocation is performed to manufacture them.

Per-scenario primary tables follow for every contrast. Equal-scenario weighting gives each displayed scenario the same weight; natural-mixture weighting follows its N.

## kv1_minus_kv0: NEW500 official per-row SLU-F1

| Scenario | N | Left mean % | Right mean % | Delta pp | Saves | Harms | Ties |
|---|---:|---:|---:|---:|---:|---:|---:|
| alarm | 30 | 28.0907 | 30.4853 | 2.3947 | 2 | 0 | 28 |
| audio | 2 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 2 |
| calendar | 33 | 28.0787 | 25.0484 | -3.0303 | 0 | 1 | 32 |
| cooking | 9 | 63.0592 | 51.9481 | -11.1111 | 0 | 1 | 8 |
| datetime | 33 | 32.5460 | 32.8989 | 0.3529 | 1 | 0 | 32 |
| email | 33 | 20.1611 | 21.7172 | 1.5561 | 1 | 1 | 31 |
| general | 33 | 6.5630 | 3.5327 | -3.0303 | 0 | 1 | 32 |
| iot | 33 | 39.7635 | 31.8089 | -7.9545 | 0 | 3 | 30 |
| lists | 32 | 9.8011 | 12.0630 | 2.2619 | 1 | 0 | 31 |
| music | 23 | 12.7283 | 12.7283 | 0.0000 | 0 | 0 | 23 |
| news | 32 | 26.2451 | 26.1093 | -0.1359 | 0 | 1 | 31 |
| play | 32 | 36.0886 | 36.8852 | 0.7966 | 1 | 0 | 31 |
| qa | 32 | 49.6373 | 52.7623 | 3.1250 | 1 | 0 | 31 |
| recommendation | 32 | 52.4764 | 50.4544 | -2.0221 | 0 | 1 | 31 |
| social | 33 | 23.2079 | 25.9368 | 2.7289 | 4 | 2 | 27 |
| takeaway | 12 | 11.5707 | 11.5707 | 0.0000 | 0 | 0 | 12 |
| transport | 33 | 25.8828 | 22.0705 | -3.8123 | 0 | 2 | 31 |
| weather | 33 | 12.1359 | 9.1056 | -3.0303 | 0 | 1 | 32 |

## kv1_minus_kv1t: NEW500 official per-row SLU-F1

| Scenario | N | Left mean % | Right mean % | Delta pp | Saves | Harms | Ties |
|---|---:|---:|---:|---:|---:|---:|---:|
| alarm | 30 | 26.1105 | 30.4853 | 4.3748 | 2 | 0 | 28 |
| audio | 2 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 2 |
| calendar | 33 | 25.0484 | 25.0484 | 0.0000 | 0 | 0 | 33 |
| cooking | 9 | 51.9481 | 51.9481 | 0.0000 | 0 | 0 | 9 |
| datetime | 33 | 39.5726 | 32.8989 | -6.6737 | 0 | 3 | 30 |
| email | 33 | 24.5900 | 21.7172 | -2.8728 | 0 | 2 | 31 |
| general | 33 | 3.5327 | 3.5327 | 0.0000 | 0 | 0 | 33 |
| iot | 33 | 31.8089 | 31.8089 | 0.0000 | 0 | 0 | 33 |
| lists | 32 | 12.0630 | 12.0630 | 0.0000 | 0 | 0 | 32 |
| music | 23 | 12.7283 | 12.7283 | 0.0000 | 0 | 0 | 23 |
| news | 32 | 29.2343 | 26.1093 | -3.1250 | 0 | 1 | 31 |
| play | 32 | 36.0886 | 36.8852 | 0.7966 | 1 | 0 | 31 |
| qa | 32 | 52.7623 | 52.7623 | 0.0000 | 0 | 0 | 32 |
| recommendation | 32 | 51.4960 | 50.4544 | -1.0417 | 0 | 1 | 31 |
| social | 33 | 24.8429 | 25.9368 | 1.0939 | 3 | 3 | 27 |
| takeaway | 12 | 11.5707 | 11.5707 | 0.0000 | 0 | 0 | 12 |
| transport | 33 | 20.8103 | 22.0705 | 1.2602 | 2 | 1 | 30 |
| weather | 33 | 15.1662 | 9.1056 | -6.0606 | 0 | 2 | 31 |

## kv2_minus_kv0: NEW500 official per-row SLU-F1

| Scenario | N | Left mean % | Right mean % | Delta pp | Saves | Harms | Ties |
|---|---:|---:|---:|---:|---:|---:|---:|
| alarm | 30 | 28.0907 | 32.7345 | 4.6438 | 2 | 1 | 27 |
| audio | 2 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 2 |
| calendar | 33 | 28.0787 | 39.4617 | 11.3831 | 5 | 0 | 28 |
| cooking | 9 | 63.0592 | 48.2443 | -14.8148 | 0 | 2 | 7 |
| datetime | 33 | 32.5460 | 50.3567 | 17.8107 | 8 | 0 | 25 |
| email | 33 | 20.1611 | 20.7071 | 0.5460 | 1 | 0 | 32 |
| general | 33 | 6.5630 | 9.5933 | 3.0303 | 1 | 0 | 32 |
| iot | 33 | 39.7635 | 37.8695 | -1.8939 | 1 | 2 | 30 |
| lists | 32 | 9.8011 | 14.1464 | 4.3452 | 2 | 0 | 30 |
| music | 23 | 12.7283 | 14.0526 | 1.3243 | 1 | 0 | 22 |
| news | 32 | 26.2451 | 38.2243 | 11.9792 | 5 | 0 | 27 |
| play | 32 | 36.0886 | 36.0886 | 0.0000 | 0 | 0 | 32 |
| qa | 32 | 49.6373 | 43.3873 | -6.2500 | 0 | 2 | 30 |
| recommendation | 32 | 52.4764 | 59.7681 | 7.2917 | 3 | 0 | 29 |
| social | 33 | 23.2079 | 45.5761 | 22.3682 | 11 | 1 | 21 |
| takeaway | 12 | 11.5707 | 19.9040 | 8.3333 | 1 | 0 | 11 |
| transport | 33 | 25.8828 | 29.1838 | 3.3010 | 5 | 2 | 26 |
| weather | 33 | 12.1359 | 43.0906 | 30.9547 | 12 | 0 | 21 |

## kv2_minus_kv2t: NEW500 official per-row SLU-F1

| Scenario | N | Left mean % | Right mean % | Delta pp | Saves | Harms | Ties |
|---|---:|---:|---:|---:|---:|---:|---:|
| alarm | 30 | 32.6265 | 32.7345 | 0.1080 | 1 | 2 | 27 |
| audio | 2 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 2 |
| calendar | 33 | 37.9896 | 39.4617 | 1.4722 | 1 | 1 | 31 |
| cooking | 9 | 40.8369 | 48.2443 | 7.4074 | 1 | 1 | 7 |
| datetime | 33 | 37.9494 | 50.3567 | 12.4073 | 6 | 2 | 25 |
| email | 33 | 21.5597 | 20.7071 | -0.8526 | 1 | 1 | 31 |
| general | 33 | 6.5630 | 9.5933 | 3.0303 | 1 | 0 | 32 |
| iot | 33 | 43.9301 | 37.8695 | -6.0606 | 0 | 2 | 31 |
| lists | 32 | 12.0630 | 14.1464 | 2.0833 | 1 | 0 | 31 |
| music | 23 | 12.7283 | 14.0526 | 1.3243 | 1 | 0 | 22 |
| news | 32 | 40.3982 | 38.2243 | -2.1739 | 0 | 1 | 31 |
| play | 32 | 36.0886 | 36.0886 | 0.0000 | 0 | 0 | 32 |
| qa | 32 | 46.5123 | 43.3873 | -3.1250 | 0 | 1 | 31 |
| recommendation | 32 | 55.6014 | 59.7681 | 4.1667 | 2 | 0 | 30 |
| social | 33 | 30.0520 | 45.5761 | 15.5241 | 9 | 2 | 22 |
| takeaway | 12 | 11.5707 | 19.9040 | 8.3333 | 1 | 0 | 11 |
| transport | 33 | 37.9639 | 29.1838 | -8.7801 | 0 | 4 | 29 |
| weather | 33 | 40.8561 | 43.0906 | 2.2345 | 3 | 2 | 28 |

## kv3_minus_kv0: NEW500 official per-row SLU-F1

| Scenario | N | Left mean % | Right mean % | Delta pp | Saves | Harms | Ties |
|---|---:|---:|---:|---:|---:|---:|---:|
| alarm | 30 | 28.0907 | 32.0360 | 3.9453 | 2 | 0 | 28 |
| audio | 2 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 2 |
| calendar | 33 | 28.0787 | 32.0969 | 4.0182 | 2 | 0 | 31 |
| cooking | 9 | 63.0592 | 63.0592 | 0.0000 | 0 | 0 | 9 |
| datetime | 33 | 32.5460 | 30.4817 | -2.0643 | 0 | 1 | 32 |
| email | 33 | 20.1611 | 24.5900 | 4.4289 | 2 | 0 | 31 |
| general | 33 | 6.5630 | 6.5630 | 0.0000 | 0 | 0 | 33 |
| iot | 33 | 39.7635 | 42.7938 | 3.0303 | 1 | 0 | 32 |
| lists | 32 | 9.8011 | 12.0630 | 2.2619 | 1 | 0 | 31 |
| music | 23 | 12.7283 | 12.7283 | 0.0000 | 0 | 0 | 23 |
| news | 32 | 26.2451 | 27.9185 | 1.6733 | 1 | 2 | 29 |
| play | 32 | 36.0886 | 36.8942 | 0.8056 | 2 | 0 | 30 |
| qa | 32 | 49.6373 | 43.3873 | -6.2500 | 0 | 2 | 30 |
| recommendation | 32 | 52.4764 | 55.5855 | 3.1091 | 2 | 1 | 29 |
| social | 33 | 23.2079 | 27.0539 | 3.8460 | 5 | 3 | 25 |
| takeaway | 12 | 11.5707 | 11.5707 | 0.0000 | 0 | 0 | 12 |
| transport | 33 | 25.8828 | 18.4149 | -7.4679 | 0 | 4 | 29 |
| weather | 33 | 12.1359 | 9.1056 | -3.0303 | 0 | 1 | 32 |

## kv3_minus_kv3t: NEW500 official per-row SLU-F1

| Scenario | N | Left mean % | Right mean % | Delta pp | Saves | Harms | Ties |
|---|---:|---:|---:|---:|---:|---:|---:|
| alarm | 30 | 31.6981 | 32.0360 | 0.3379 | 2 | 1 | 27 |
| audio | 2 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 2 |
| calendar | 33 | 27.0464 | 32.0969 | 5.0505 | 2 | 0 | 31 |
| cooking | 9 | 40.8369 | 63.0592 | 22.2222 | 2 | 0 | 7 |
| datetime | 33 | 32.8989 | 30.4817 | -2.4172 | 0 | 1 | 32 |
| email | 33 | 23.1914 | 24.5900 | 1.3986 | 1 | 0 | 32 |
| general | 33 | 3.5327 | 6.5630 | 3.0303 | 1 | 0 | 32 |
| iot | 33 | 31.8089 | 42.7938 | 10.9848 | 4 | 0 | 29 |
| lists | 32 | 12.0630 | 12.0630 | 0.0000 | 0 | 0 | 32 |
| music | 23 | 12.7283 | 12.7283 | 0.0000 | 0 | 0 | 23 |
| news | 32 | 26.8768 | 27.9185 | 1.0417 | 1 | 1 | 30 |
| play | 32 | 36.8852 | 36.8942 | 0.0090 | 1 | 0 | 31 |
| qa | 32 | 54.7587 | 43.3873 | -11.3715 | 0 | 4 | 28 |
| recommendation | 32 | 56.7527 | 55.5855 | -1.1672 | 1 | 2 | 29 |
| social | 33 | 21.9495 | 27.0539 | 5.1045 | 6 | 1 | 26 |
| takeaway | 12 | 19.9040 | 11.5707 | -8.3333 | 0 | 1 | 11 |
| transport | 33 | 20.4934 | 18.4149 | -2.0785 | 2 | 3 | 28 |
| weather | 33 | 9.1056 | 9.1056 | 0.0000 | 0 | 0 | 33 |
