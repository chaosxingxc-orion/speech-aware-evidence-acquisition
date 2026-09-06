# Earnings-22 DEV semantic error scan -- per-arm tables

Taxonomy `saea-e22-error-taxonomy-v1`, normalizer `whisper-english-v20240930`, exposure row `SAEA-E22-MF-SEMANTIC-ERROR-SCAN-V1`. Dev split only; the six ESB test calls are not read.

## Arm A -- this study's verbatim instruction, system message before the audio

Corpus WER 17.5648 %, 10330 error spans, identity gate reproduced: True.

### Category mass

| category | spans | error mass | share % | WER points | NONE | LOW | HIGH |
|---|---|---|---|---|---|---|---|
| format-convention | 290 | 342 | 1.883 | 0.3307 | 290 | 0 | 0 |
| reference-convention | 752 | 903 | 4.971 | 0.8731 | 752 | 0 | 0 |
| segmentation-artifact | 2269 | 3746 | 20.621 | 3.622 | 2269 | 0 | 0 |
| named-entity | 874 | 1174 | 6.463 | 1.1351 | 0 | 0 | 874 |
| domain-term | 155 | 233 | 1.283 | 0.2253 | 0 | 144 | 11 |
| model-behaviour | 1405 | 5462 | 30.067 | 5.2812 | 337 | 935 | 133 |
| acoustic-misrecognition | 1051 | 1400 | 7.707 | 1.3537 | 128 | 791 | 132 |
| other | 3534 | 4906 | 27.006 | 4.7436 | 1649 | 1611 | 274 |

### Rule mass

| rule | spans | error mass | WER points |
|---|---|---|---|
| model-behaviour/runaway-tail | 1087 | 4635 | 4.4816 |
| segmentation-artifact/boundary-continuation | 1288 | 1775 | 1.7163 |
| segmentation-artifact/neighbour-bleed | 496 | 1419 | 1.372 |
| acoustic-misrecognition/string-near | 1051 | 1400 | 1.3537 |
| other/substituted-content-word | 1023 | 1285 | 1.2425 |
| named-entity/call-inventory | 874 | 1174 | 1.1351 |
| other/inserted-content-word | 532 | 1168 | 1.1293 |
| other/inserted-function-word | 636 | 739 | 0.7145 |
| other/deleted-content-word | 330 | 610 | 0.5898 |
| other/deleted-function-word | 495 | 562 | 0.5434 |
| other/function-word-swap | 518 | 542 | 0.5241 |
| segmentation-artifact/boundary-onset | 423 | 490 | 0.4738 |
| reference-convention/reference-repetition | 345 | 376 | 0.3636 |
| model-behaviour/hypothesis-repetition | 196 | 279 | 0.2698 |
| reference-convention/false-start-stem | 249 | 275 | 0.2659 |
| model-behaviour/runaway-head | 56 | 263 | 0.2543 |
| format-convention/merge-compound | 233 | 260 | 0.2514 |
| domain-term/pinned-lexicon | 155 | 233 | 0.2253 |
| model-behaviour/truncation | 35 | 222 | 0.2147 |
| reference-convention/redacted-region | 98 | 177 | 0.1711 |
| segmentation-artifact/boundary-partial-word | 62 | 62 | 0.0599 |
| format-convention/stray-punctuation-token | 37 | 37 | 0.0358 |
| model-behaviour/non-english-script | 27 | 33 | 0.0319 |
| reference-convention/discourse-single | 33 | 33 | 0.0319 |
| format-convention/numeric-equal | 9 | 32 | 0.0309 |
| model-behaviour/hypothesis-loop | 4 | 30 | 0.029 |
| reference-convention/empty-reference | 8 | 18 | 0.0174 |
| format-convention/symbol-only | 10 | 12 | 0.0116 |
| reference-convention/backchannel-variant | 10 | 10 | 0.0097 |
| reference-convention/discourse-phrase | 5 | 10 | 0.0097 |
| reference-convention/filler-token | 4 | 4 | 0.0039 |
| format-convention/whisper-refold | 1 | 1 | 0.001 |

### Semantic impact

| impact | spans | error mass | share % | WER points |
|---|---|---|---|---|
| NONE | 5425 | 7734 | 42.574 | 7.478 |
| LOW | 3481 | 7866 | 43.301 | 7.6057 |
| HIGH | 1424 | 2566 | 14.125 | 2.4811 |

### Per call

| call | ref words | corpus WER % | agentic error rate % | pts format-convention | pts reference-convention | pts segmentation-artifact | pts named-entity | pts domain-term | pts model-behaviour | pts acoustic-misrecognition | pts other |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 4453225 | 11304 | 20.2937 | 1.1146 | 0.1858 | 1.9285 | 3.2997 | 0.575 | 0.3362 | 6.2633 | 1.8135 | 5.8917 |
| 4469088 | 11493 | 19.8556 | 2.0186 | 0.2871 | 1.2355 | 4.1504 | 0.9397 | 0.2088 | 6.9347 | 1.0876 | 5.0117 |
| 4470684 | 10862 | 14.2976 | 1.2152 | 0.2578 | 0.7918 | 3.6642 | 0.6997 | 0.1381 | 5.1188 | 0.9667 | 2.6607 |
| 4474506 | 11534 | 14.9471 | 1.5086 | 0.4075 | 0.6936 | 3.6067 | 0.6676 | 0.1301 | 3.9275 | 1.2658 | 4.2483 |
| 4479944 | 10882 | 23.6629 | 2.9958 | 0.2573 | 0.193 | 3.9607 | 1.553 | 0.3951 | 7.2321 | 2.0493 | 8.0224 |
| 4481952 | 9827 | 17.1161 | 1.7605 | 0.2748 | 1.4043 | 4.0094 | 1.2822 | 0.2442 | 5.0168 | 1.3636 | 3.5209 |
| 4482383 | 9763 | 14.2579 | 1.6388 | 0.6146 | 0.5019 | 3.0319 | 1.3008 | 0.0205 | 4.0971 | 1.2906 | 3.4006 |
| 4482613 | 9168 | 22.9385 | 4.8757 | 0.6108 | 0.5672 | 3.7413 | 2.9341 | 0.5236 | 4.2103 | 1.9634 | 8.3879 |
| 4483937 | 8680 | 15.4724 | 1.3249 | 0.1843 | 0.8065 | 3.6175 | 0.8986 | 0.0461 | 5.1382 | 1.0023 | 3.7788 |
| 4485192 | 9910 | 12.2906 | 1.0595 | 0.2624 | 0.4743 | 3.0676 | 0.7972 | 0.2018 | 4.3996 | 0.6963 | 2.3915 |

### Per clip duration

| bucket | utterances | ref words | corpus WER % | pts format-convention | pts reference-convention | pts segmentation-artifact | pts named-entity | pts domain-term | pts model-behaviour | pts acoustic-misrecognition | pts other |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0-1s | 504 | 1268 | 71.6877 | 1.2618 | 2.6814 | 19.5584 | 4.2587 | 0.3155 | 23.1073 | 2.5237 | 17.9811 |
| 1-2s | 482 | 2461 | 41.9342 | 0.6501 | 1.1784 | 10.7273 | 3.0882 | 0.1219 | 9.6709 | 2.2755 | 14.2219 |
| 2-4s | 1163 | 10172 | 28.6276 | 0.3048 | 1.1699 | 7.1077 | 2.4184 | 0.3146 | 7.7074 | 1.7401 | 7.8647 |
| 4-8s | 1991 | 31065 | 19.0472 | 0.2768 | 0.7565 | 4.1172 | 1.0913 | 0.1964 | 6.4059 | 1.2361 | 4.967 |
| 8-16s | 1625 | 45298 | 13.2081 | 0.3069 | 0.8543 | 2.2407 | 0.7771 | 0.2009 | 4.0002 | 1.2627 | 3.5653 |
| 16s+ | 273 | 13159 | 10.7379 | 0.4104 | 0.7523 | 1.6491 | 0.8131 | 0.3192 | 2.6218 | 1.3603 | 2.8118 |

### Four-bin gap estimate

| bin | error mass | share % | WER points |
|---|---|---|---|
| scoring-convention | 360 | 1.982 | 0.3481 |
| missing-pre-meeting-context | 1407 | 7.745 | 1.3604 |
| core-capability | 5027 | 27.673 | 4.8606 |
| task-definition | 11372 | 62.6 | 10.9956 |

## Arm B -- the Qwen3-Omni model-card ASR prompt, system message before the audio

Corpus WER 18.3944 %, 10470 error spans, identity gate reproduced: True.

### Category mass

| category | spans | error mass | share % | WER points | NONE | LOW | HIGH |
|---|---|---|---|---|---|---|---|
| format-convention | 280 | 326 | 1.714 | 0.3152 | 280 | 0 | 0 |
| reference-convention | 862 | 1043 | 5.483 | 1.0085 | 862 | 0 | 0 |
| segmentation-artifact | 2375 | 3865 | 20.316 | 3.7371 | 2375 | 0 | 0 |
| named-entity | 866 | 1182 | 6.213 | 1.1429 | 0 | 0 | 866 |
| domain-term | 151 | 233 | 1.225 | 0.2253 | 0 | 142 | 9 |
| model-behaviour | 1374 | 5834 | 30.667 | 5.6409 | 308 | 914 | 152 |
| acoustic-misrecognition | 1038 | 1395 | 7.333 | 1.3488 | 120 | 790 | 128 |
| other | 3524 | 5146 | 27.05 | 4.9757 | 1613 | 1638 | 273 |

### Rule mass

| rule | spans | error mass | WER points |
|---|---|---|---|
| model-behaviour/runaway-tail | 1067 | 4563 | 4.412 |
| segmentation-artifact/boundary-continuation | 1364 | 1874 | 1.812 |
| segmentation-artifact/neighbour-bleed | 513 | 1433 | 1.3856 |
| other/inserted-content-word | 543 | 1397 | 1.3508 |
| acoustic-misrecognition/string-near | 1038 | 1395 | 1.3488 |
| other/substituted-content-word | 1047 | 1329 | 1.285 |
| named-entity/call-inventory | 866 | 1182 | 1.1429 |
| model-behaviour/runaway-head | 66 | 734 | 0.7097 |
| other/inserted-function-word | 625 | 725 | 0.701 |
| other/deleted-content-word | 321 | 599 | 0.5792 |
| other/deleted-function-word | 476 | 559 | 0.5405 |
| other/function-word-swap | 512 | 537 | 0.5192 |
| reference-convention/reference-repetition | 451 | 503 | 0.4864 |
| segmentation-artifact/boundary-onset | 438 | 498 | 0.4815 |
| reference-convention/false-start-stem | 246 | 274 | 0.2649 |
| model-behaviour/hypothesis-repetition | 180 | 258 | 0.2495 |
| format-convention/merge-compound | 224 | 246 | 0.2379 |
| domain-term/pinned-lexicon | 151 | 233 | 0.2253 |
| model-behaviour/truncation | 36 | 222 | 0.2147 |
| reference-convention/redacted-region | 99 | 184 | 0.1779 |
| segmentation-artifact/boundary-partial-word | 60 | 60 | 0.058 |
| format-convention/stray-punctuation-token | 36 | 36 | 0.0348 |
| reference-convention/discourse-single | 34 | 34 | 0.0329 |
| format-convention/numeric-equal | 9 | 31 | 0.03 |
| model-behaviour/hypothesis-loop | 4 | 30 | 0.029 |
| model-behaviour/non-english-script | 21 | 27 | 0.0261 |
| reference-convention/empty-reference | 10 | 19 | 0.0184 |
| reference-convention/discourse-phrase | 7 | 14 | 0.0135 |
| format-convention/symbol-only | 10 | 12 | 0.0116 |
| reference-convention/backchannel-variant | 11 | 11 | 0.0106 |
| reference-convention/filler-token | 4 | 4 | 0.0039 |
| format-convention/whisper-refold | 1 | 1 | 0.001 |

### Semantic impact

| impact | spans | error mass | share % | WER points |
|---|---|---|---|---|
| NONE | 5558 | 7884 | 41.442 | 7.6231 |
| LOW | 3484 | 7894 | 41.495 | 7.6327 |
| HIGH | 1428 | 3246 | 17.063 | 3.1386 |

### Per call

| call | ref words | corpus WER % | agentic error rate % | pts format-convention | pts reference-convention | pts segmentation-artifact | pts named-entity | pts domain-term | pts model-behaviour | pts acoustic-misrecognition | pts other |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 4453225 | 11304 | 23.3015 | 1.1766 | 0.23 | 2.0612 | 3.4147 | 0.5662 | 0.345 | 8.4395 | 1.8224 | 6.4225 |
| 4469088 | 11493 | 20.5951 | 2.0795 | 0.2784 | 1.5314 | 4.3157 | 0.9223 | 0.1914 | 7.1261 | 1.0528 | 5.1771 |
| 4470684 | 10862 | 14.4909 | 1.3349 | 0.267 | 0.9759 | 3.5445 | 0.7457 | 0.1473 | 5.0911 | 0.9851 | 2.7343 |
| 4474506 | 11534 | 15.2852 | 1.5433 | 0.3555 | 0.8063 | 3.8495 | 0.6936 | 0.1647 | 3.8668 | 1.1878 | 4.361 |
| 4479944 | 10882 | 23.8283 | 3.005 | 0.2389 | 0.2114 | 4.1628 | 1.6909 | 0.3676 | 7.4619 | 1.9849 | 7.71 |
| 4481952 | 9827 | 17.0143 | 1.679 | 0.2646 | 1.5468 | 4.1111 | 1.2517 | 0.2748 | 4.5385 | 1.3738 | 3.6532 |
| 4482383 | 9763 | 13.838 | 1.5569 | 0.5838 | 0.6043 | 3.1957 | 1.2906 | 0.0819 | 3.6874 | 1.2496 | 3.1445 |
| 4482613 | 9168 | 23.2875 | 4.6902 | 0.5672 | 0.5563 | 3.8285 | 2.9559 | 0.4799 | 4.483 | 2.0942 | 8.3224 |
| 4483937 | 8680 | 19.3894 | 1.3018 | 0.1267 | 0.8986 | 3.7327 | 0.7949 | 0.0461 | 6.947 | 1.0369 | 5.8065 |
| 4485192 | 9910 | 12.6337 | 1.1201 | 0.2624 | 0.7265 | 3.1282 | 0.7871 | 0.1413 | 4.3391 | 0.6963 | 2.553 |

### Per clip duration

| bucket | utterances | ref words | corpus WER % | pts format-convention | pts reference-convention | pts segmentation-artifact | pts named-entity | pts domain-term | pts model-behaviour | pts acoustic-misrecognition | pts other |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0-1s | 504 | 1268 | 78.3123 | 1.1041 | 2.9968 | 20.2681 | 4.2587 | 0.5521 | 28.7066 | 3.5489 | 16.877 |
| 1-2s | 482 | 2461 | 44.1284 | 0.6095 | 1.4222 | 11.215 | 3.4539 | 0.2032 | 11.0524 | 2.113 | 14.0593 |
| 2-4s | 1163 | 10172 | 32.5108 | 0.2949 | 1.2977 | 6.9996 | 2.3201 | 0.3932 | 10.8238 | 1.6221 | 8.7593 |
| 4-8s | 1991 | 31065 | 20.2833 | 0.2865 | 0.882 | 4.3747 | 1.1138 | 0.1803 | 6.7343 | 1.2876 | 5.4241 |
| 8-16s | 1625 | 45298 | 13.0403 | 0.2627 | 0.989 | 2.3114 | 0.7727 | 0.1876 | 3.7198 | 1.2473 | 3.5498 |
| 16s+ | 273 | 13159 | 10.8671 | 0.4484 | 0.8815 | 1.6263 | 0.8435 | 0.304 | 2.4318 | 1.2767 | 3.0549 |

### Four-bin gap estimate

| bin | error mass | share % | WER points |
|---|---|---|---|
| scoring-convention | 345 | 1.813 | 0.3336 |
| missing-pre-meeting-context | 1415 | 7.438 | 1.3682 |
| core-capability | 5257 | 27.634 | 5.083 |
| task-definition | 12007 | 63.115 | 11.6096 |

## Arm C -- the official request shape, no system message, instruction after the audio

Corpus WER 17.8896 %, 10472 error spans, identity gate reproduced: True.

### Category mass

| category | spans | error mass | share % | WER points | NONE | LOW | HIGH |
|---|---|---|---|---|---|---|---|
| format-convention | 266 | 290 | 1.567 | 0.2804 | 266 | 0 | 0 |
| reference-convention | 1909 | 2447 | 13.226 | 2.366 | 1909 | 0 | 0 |
| segmentation-artifact | 1624 | 2882 | 15.577 | 2.7866 | 1624 | 0 | 0 |
| named-entity | 829 | 1144 | 6.183 | 1.1061 | 0 | 0 | 829 |
| domain-term | 162 | 258 | 1.394 | 0.2495 | 0 | 155 | 7 |
| model-behaviour | 1086 | 4660 | 25.186 | 4.5058 | 148 | 791 | 147 |
| acoustic-misrecognition | 1026 | 1479 | 7.994 | 1.43 | 113 | 789 | 124 |
| other | 3570 | 5342 | 28.873 | 5.1652 | 1661 | 1641 | 268 |

### Rule mass

| rule | spans | error mass | WER points |
|---|---|---|---|
| model-behaviour/runaway-tail | 962 | 4111 | 3.9749 |
| reference-convention/reference-repetition | 1388 | 1701 | 1.6447 |
| acoustic-misrecognition/string-near | 1026 | 1479 | 1.43 |
| segmentation-artifact/neighbour-bleed | 434 | 1279 | 1.2367 |
| other/substituted-content-word | 977 | 1236 | 1.1951 |
| segmentation-artifact/boundary-continuation | 840 | 1208 | 1.168 |
| named-entity/call-inventory | 829 | 1144 | 1.1061 |
| other/deleted-content-word | 481 | 1037 | 1.0027 |
| other/deleted-function-word | 690 | 1034 | 0.9998 |
| other/inserted-content-word | 451 | 989 | 0.9563 |
| other/inserted-function-word | 490 | 551 | 0.5328 |
| other/function-word-swap | 481 | 495 | 0.4786 |
| segmentation-artifact/boundary-onset | 290 | 335 | 0.3239 |
| reference-convention/false-start-stem | 251 | 303 | 0.293 |
| model-behaviour/truncation | 39 | 267 | 0.2582 |
| domain-term/pinned-lexicon | 162 | 258 | 0.2495 |
| model-behaviour/runaway-head | 44 | 213 | 0.206 |
| format-convention/merge-compound | 189 | 195 | 0.1885 |
| reference-convention/discourse-phrase | 95 | 190 | 0.1837 |
| reference-convention/redacted-region | 90 | 153 | 0.1479 |
| model-behaviour/hypothesis-repetition | 41 | 69 | 0.0667 |
| segmentation-artifact/boundary-partial-word | 60 | 60 | 0.058 |
| format-convention/stray-punctuation-token | 57 | 57 | 0.0551 |
| reference-convention/discourse-single | 55 | 55 | 0.0532 |
| format-convention/numeric-equal | 10 | 28 | 0.0271 |
| reference-convention/empty-reference | 10 | 25 | 0.0242 |
| reference-convention/backchannel-variant | 15 | 15 | 0.0145 |
| format-convention/symbol-only | 9 | 9 | 0.0087 |
| reference-convention/filler-token | 5 | 5 | 0.0048 |
| format-convention/whisper-refold | 1 | 1 | 0.001 |

### Semantic impact

| impact | spans | error mass | share % | WER points |
|---|---|---|---|---|
| NONE | 5721 | 8259 | 44.638 | 7.9857 |
| LOW | 3376 | 7612 | 41.141 | 7.3601 |
| HIGH | 1375 | 2631 | 14.22 | 2.5439 |

### Per call

| call | ref words | corpus WER % | agentic error rate % | pts format-convention | pts reference-convention | pts segmentation-artifact | pts named-entity | pts domain-term | pts model-behaviour | pts acoustic-misrecognition | pts other |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 4453225 | 11304 | 21.5676 | 1.3447 | 0.1769 | 3.6536 | 2.3266 | 0.5485 | 0.4069 | 5.7059 | 1.9374 | 6.8117 |
| 4469088 | 11493 | 22.0047 | 2.1839 | 0.3306 | 4.2287 | 3.141 | 1.0267 | 0.261 | 5.2032 | 1.3922 | 6.4213 |
| 4470684 | 10862 | 13.8004 | 1.2797 | 0.2117 | 1.6387 | 2.5962 | 0.58 | 0.0921 | 4.8057 | 1.0403 | 2.8356 |
| 4474506 | 11534 | 15.2592 | 1.734 | 0.2601 | 2.1675 | 2.9218 | 0.7456 | 0.1907 | 3.2513 | 0.9017 | 4.8205 |
| 4479944 | 10882 | 20.5661 | 3.1336 | 0.193 | 0.2849 | 3.106 | 1.6817 | 0.4687 | 5.7894 | 1.8563 | 7.1862 |
| 4481952 | 9827 | 18.7646 | 1.6689 | 0.173 | 3.8872 | 3.2869 | 1.3127 | 0.2442 | 3.989 | 1.3534 | 4.5182 |
| 4482383 | 9763 | 15.4256 | 1.8232 | 0.6965 | 2.1919 | 2.151 | 1.352 | 0.0717 | 3.247 | 1.4545 | 4.261 |
| 4482613 | 9168 | 21.4769 | 4.3739 | 0.3599 | 0.8508 | 2.9341 | 2.5414 | 0.4581 | 4.7775 | 2.0615 | 7.4935 |
| 4483937 | 8680 | 15.7949 | 1.371 | 0.0806 | 1.9355 | 2.7304 | 0.6912 | 0.0806 | 4.6774 | 1.3134 | 4.2857 |
| 4485192 | 9910 | 13.6024 | 1.1705 | 0.333 | 2.4924 | 2.6438 | 0.7871 | 0.1917 | 3.4006 | 1.0394 | 2.7144 |

### Per clip duration

| bucket | utterances | ref words | corpus WER % | pts format-convention | pts reference-convention | pts segmentation-artifact | pts named-entity | pts domain-term | pts model-behaviour | pts acoustic-misrecognition | pts other |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0-1s | 504 | 1268 | 67.0347 | 1.4196 | 4.0221 | 18.5331 | 4.1798 | 0.5521 | 19.795 | 2.9968 | 15.5363 |
| 1-2s | 482 | 2461 | 36.1642 | 0.772 | 2.1942 | 8.5738 | 2.8444 | 0.4063 | 5.8919 | 2.1942 | 13.2873 |
| 2-4s | 1163 | 10172 | 27.1923 | 0.3244 | 2.5462 | 5.0039 | 2.2513 | 0.3539 | 6.4884 | 1.8384 | 8.3858 |
| 4-8s | 1991 | 31065 | 19.3111 | 0.2125 | 2.1375 | 3.2062 | 1.117 | 0.2543 | 5.6913 | 1.2876 | 5.4048 |
| 8-16s | 1625 | 45298 | 14.1618 | 0.2318 | 2.4416 | 1.6888 | 0.7837 | 0.1899 | 3.4505 | 1.3533 | 4.0223 |
| 16s+ | 273 | 13159 | 12.0222 | 0.3724 | 2.3786 | 1.2615 | 0.6839 | 0.304 | 2.0746 | 1.4211 | 3.5261 |

### Four-bin gap estimate

| bin | error mass | share % | WER points |
|---|---|---|---|
| scoring-convention | 315 | 1.703 | 0.3046 |
| missing-pre-meeting-context | 1402 | 7.578 | 1.3556 |
| core-capability | 5077 | 27.44 | 4.909 |
| task-definition | 11708 | 63.28 | 11.3205 |

