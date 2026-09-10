# KU-S3 independent max256 component repeat decision

Decision: **PASS the inherited component-repeat criterion.** On the historically exposed NEW500, both preregistered entity metrics have positive scenario-stratified CI90 lower bounds against the retained no-retrieval control and the retained form twin. The repeat-versus-original-treatment intervals cross zero, so this report makes no equivalence conclusion.

This is an independent-process repeat. Its control and form-twin comparisons reuse sealed historical artifacts, so the cross-process limitation remains part of the result. Exact raw response agreement with the original treatment is 771 of 1,000 rows (77.1%); 229 rows differ.

## Scoring and delivery identity

The raw repeat is a slot-stage component output. The registered model-free delivery copies scenario and action from the same sealed direct predecessor used by KC-S1b and takes entities from the repeat. It preserves the raw parent and adds no model contact. The complete derived roster was scored once through the registered slurp-slu-official scorer with per-sample retention. The official evaluator commit is 8eb16545762be97ace75334109d73824217311f1, and its port identity check passed with absolute differences of zero.

The two decision metrics are entity-only. slot_f1_exact_f1 uses exact entity type/filler counts. slu_f1_f1 combines word-distance and character-distance entity TP/FP/FN. The deterministic intent join changes neither metric. Scenario, action, and intent fields are view-dependent and are excluded from every contrast in this report; mixed-view intent comparisons are prohibited.

The one complete official score contains 1,000 rows. Its aggregate anchors are: strict entity span F1 0.365307, official entity-distance SLU-F1 0.497847, scenario accuracy 0.810, action accuracy 0.739, and intent accuracy 0.714. The latter three describe only the joined delivery and are not compared with raw historical score views.

Generation used 1,000 model contacts and 2,884.7936875 speech seconds. The externally integrated generation cost is **0.14171674399309686 GPU-hours**. Delivery, saved-score comparison, and byte-agreement analysis each used zero model, encoder, tokenizer, scorer, and reference contacts. Official scoring invoked the full scorer exactly once.

## Population-level results

All values below are percentage-point changes, repeat minus comparator. Natural is the frozen scenario-stratified row bootstrap; equal-scenario is the unweighted mean of the observed scenario deltas; speaker is the separately reported speaker-cluster sensitivity. S/H/T gives saves, harms, and ties at row level.

| Population | Contrast | Metric | Natural point and CI90 | Equal-scenario | Speaker point and CI90 | S/H/T |
| --- | --- | --- | --- | ---: | --- | --- |
| NEW500 | Repeat minus original treatment | Strict entity slot F1 | +0.543 [-0.762, +1.857] | +1.067 | +0.543 [-0.605, +1.775] | 14/12/474 |
| NEW500 | Repeat minus original treatment | Official entity-distance SLU-F1 | +0.544 [-0.665, +1.768] | +1.060 | +0.544 [-0.440, +1.612] | 21/12/467 |
| NEW500 | Repeat minus retained control | Strict entity slot F1 | +5.790 [+3.873, +7.785] | +6.522 | +5.790 [+3.843, +7.825] | 41/12/447 |
| NEW500 | Repeat minus retained control | Official entity-distance SLU-F1 | +7.181 [+5.223, +9.159] | +7.659 | +7.181 [+5.317, +9.138] | 61/14/425 |
| NEW500 | Repeat minus retained form twin | Strict entity slot F1 | +2.750 [+0.717, +4.847] | +2.472 | +2.750 [+0.805, +4.657] | 34/21/445 |
| NEW500 | Repeat minus retained form twin | Official entity-distance SLU-F1 | +4.198 [+2.140, +6.247] | +3.947 | +4.198 [+2.283, +6.192] | 49/28/423 |
| OLD500 | Repeat minus original treatment | Strict entity slot F1 | -0.553 [-1.500, +0.360] | -0.551 | -0.553 [-1.481, +0.366] | 8/10/482 |
| OLD500 | Repeat minus original treatment | Official entity-distance SLU-F1 | -0.841 [-1.834, +0.093] | -0.831 | -0.841 [-1.886, +0.131] | 12/17/471 |
| OLD500 | Repeat minus retained control | Strict entity slot F1 | +3.344 [+1.507, +5.150] | +3.409 | +3.344 [+1.286, +5.451] | 40/17/443 |
| OLD500 | Repeat minus retained control | Official entity-distance SLU-F1 | +4.111 [+2.299, +5.955] | +4.182 | +4.111 [+2.108, +6.123] | 52/24/424 |
| OLD500 | Repeat minus retained form twin | Strict entity slot F1 | +1.304 [-0.496, +3.067] | +1.352 | +1.304 [-0.913, +3.465] | 32/19/449 |
| OLD500 | Repeat minus retained form twin | Official entity-distance SLU-F1 | +1.467 [-0.295, +3.255] | +1.519 | +1.467 [-0.604, +3.568] | 41/31/428 |
| DEV1000 | Repeat minus original treatment | Strict entity slot F1 | -0.005 [-0.839, +0.799] | +0.086 | -0.005 [-0.812, +0.834] | 22/22/956 |
| DEV1000 | Repeat minus original treatment | Official entity-distance SLU-F1 | -0.149 [-0.952, +0.642] | -0.115 | -0.149 [-0.891, +0.584] | 33/29/938 |
| DEV1000 | Repeat minus retained control | Strict entity slot F1 | +4.567 [+3.205, +5.942] | +4.575 | +4.567 [+3.139, +5.982] | 81/29/890 |
| DEV1000 | Repeat minus retained control | Official entity-distance SLU-F1 | +5.646 [+4.292, +7.046] | +5.609 | +5.646 [+4.203, +7.061] | 113/38/849 |
| DEV1000 | Repeat minus retained form twin | Strict entity slot F1 | +2.027 [+0.684, +3.399] | +1.971 | +2.027 [+0.759, +3.294] | 66/40/894 |
| DEV1000 | Repeat minus retained form twin | Official entity-distance SLU-F1 | +2.832 [+1.482, +4.201] | +2.751 | +2.832 [+1.641, +4.044] | 90/59/851 |

## Complete per-scenario results

Each table is descriptive at the observed scenario level. Means and deltas are percentage points. Counts remain paired row-level saves, harms, and ties.

### NEW500 — Strict entity slot F1

| Scenario | n | Repeat minus original: original / repeat / delta / S-H-T | Repeat minus control: control / repeat / delta / S-H-T | Repeat minus twin: twin / repeat / delta / S-H-T |
| --- | ---: | --- | --- | --- |
| alarm | 30 | 15.222 / 20.778 / +5.556 / 2-0-28 | 12.222 / 20.778 / +8.556 / 3-1-26 | 10.556 / 20.778 / +10.222 / 4-0-26 |
| audio | 2 | 0.000 / 0.000 / +0.000 / 0-0-2 | 0.000 / 0.000 / +0.000 / 0-0-2 | 0.000 / 0.000 / +0.000 / 0-0-2 |
| calendar | 33 | 18.947 / 19.957 / +1.010 / 1-1-31 | 24.502 / 19.957 / -4.545 / 0-2-31 | 21.472 / 19.957 / -1.515 / 0-1-32 |
| cooking | 9 | 55.556 / 55.556 / +0.000 / 0-0-9 | 33.333 / 55.556 / +22.222 / 2-0-7 | 55.556 / 55.556 / +0.000 / 0-0-9 |
| datetime | 33 | 41.414 / 35.354 / -6.061 / 0-2-31 | 24.242 / 35.354 / +11.111 / 4-0-29 | 33.333 / 35.354 / +2.020 / 4-3-26 |
| email | 33 | 20.202 / 21.717 / +1.515 / 1-0-32 | 23.737 / 21.717 / -2.020 / 0-1-32 | 23.232 / 21.717 / -1.515 / 1-1-31 |
| general | 33 | 12.121 / 12.121 / +0.000 / 0-0-33 | 3.030 / 12.121 / +9.091 / 3-0-30 | 10.101 / 12.121 / +2.020 / 3-2-28 |
| iot | 33 | 35.354 / 38.384 / +3.030 / 1-0-32 | 38.384 / 38.384 / +0.000 / 0-0-33 | 33.838 / 38.384 / +4.545 / 2-1-30 |
| lists | 32 | 9.375 / 9.375 / +0.000 / 0-0-32 | 6.250 / 9.375 / +3.125 / 1-0-31 | 9.375 / 9.375 / +0.000 / 0-0-32 |
| music | 23 | 13.043 / 13.043 / +0.000 / 0-0-23 | 8.696 / 13.043 / +4.348 / 1-0-22 | 8.696 / 13.043 / +4.348 / 1-0-22 |
| news | 32 | 28.646 / 23.438 / -5.208 / 0-2-30 | 14.583 / 23.438 / +8.854 / 4-1-27 | 16.146 / 23.438 / +7.292 / 3-1-28 |
| play | 32 | 28.646 / 28.646 / +0.000 / 0-0-32 | 30.938 / 28.646 / -2.292 / 1-2-29 | 31.771 / 28.646 / -3.125 / 0-1-31 |
| qa | 32 | 45.312 / 48.438 / +3.125 / 1-0-31 | 35.938 / 48.438 / +12.500 / 4-0-28 | 39.062 / 48.438 / +9.375 / 3-0-29 |
| recommendation | 32 | 53.854 / 51.771 / -2.083 / 1-3-28 | 47.604 / 51.771 / +4.167 / 2-1-29 | 46.042 / 51.771 / +5.729 / 3-1-28 |
| social | 33 | 42.626 / 42.626 / +0.000 / 0-0-33 | 31.515 / 42.626 / +11.111 / 5-1-27 | 41.414 / 42.626 / +1.212 / 3-4-26 |
| takeaway | 12 | 13.889 / 30.556 / +16.667 / 2-0-10 | 13.889 / 30.556 / +16.667 / 2-0-10 | 30.556 / 30.556 / +0.000 / 1-1-10 |
| transport | 33 | 36.999 / 42.698 / +5.700 / 4-2-27 | 31.732 / 42.698 / +10.967 / 7-2-24 | 36.277 / 42.698 / +6.421 / 4-2-27 |
| weather | 33 | 29.293 / 25.253 / -4.040 / 1-2-30 | 21.717 / 25.253 / +3.535 / 2-1-30 | 27.778 / 25.253 / -2.525 / 2-3-28 |

### NEW500 — Official entity-distance SLU-F1

| Scenario | n | Repeat minus original: original / repeat / delta / S-H-T | Repeat minus control: control / repeat / delta / S-H-T | Repeat minus twin: twin / repeat / delta / S-H-T |
| --- | ---: | --- | --- | --- |
| alarm | 30 | 34.613 / 38.552 / +3.939 / 2-0-28 | 33.390 / 38.552 / +5.162 / 4-0-26 | 30.390 / 38.552 / +8.162 / 4-0-26 |
| audio | 2 | 0.000 / 0.000 / +0.000 / 0-0-2 | 0.000 / 0.000 / +0.000 / 0-0-2 | 0.000 / 0.000 / +0.000 / 0-0-2 |
| calendar | 33 | 29.861 / 33.870 / +4.009 / 4-1-28 | 36.923 / 33.870 / -3.053 / 3-4-26 | 32.675 / 33.870 / +1.194 / 3-3-27 |
| cooking | 9 | 63.059 / 63.059 / +0.000 / 0-0-9 | 40.837 / 63.059 / +22.222 / 2-0-7 | 55.556 / 63.059 / +7.504 / 1-0-8 |
| datetime | 33 | 56.558 / 50.498 / -6.061 / 0-2-31 | 33.512 / 50.498 / +16.986 / 7-0-26 | 45.992 / 50.498 / +4.505 / 6-4-23 |
| email | 33 | 23.210 / 26.363 / +3.153 / 3-0-30 | 26.868 / 26.363 / -0.505 / 1-1-31 | 24.964 / 26.363 / +1.399 / 3-1-29 |
| general | 33 | 15.654 / 15.654 / +0.000 / 0-0-33 | 6.563 / 15.654 / +9.091 / 3-0-30 | 13.634 / 15.654 / +2.020 / 3-2-28 |
| iot | 33 | 45.940 / 46.801 / +0.861 / 1-0-32 | 45.206 / 46.801 / +1.595 / 1-0-32 | 39.657 / 46.801 / +7.144 / 3-1-29 |
| lists | 32 | 15.188 / 15.188 / +0.000 / 0-0-32 | 12.063 / 15.188 / +3.125 / 2-0-30 | 15.188 / 15.188 / +0.000 / 0-0-32 |
| music | 23 | 15.960 / 15.960 / +0.000 / 0-0-23 | 12.728 / 15.960 / +3.231 / 1-0-22 | 14.053 / 15.960 / +1.907 / 1-0-22 |
| news | 32 | 43.306 / 38.098 / -5.208 / 0-2-30 | 24.793 / 38.098 / +13.304 / 7-1-24 | 27.624 / 38.098 / +10.473 / 5-1-26 |
| play | 32 | 36.885 / 36.885 / +0.000 / 0-0-32 | 39.910 / 36.885 / -3.024 / 1-2-29 | 41.617 / 36.885 / -4.732 / 0-2-30 |
| qa | 32 | 49.637 / 52.762 / +3.125 / 1-0-31 | 40.262 / 52.762 / +12.500 / 4-0-28 | 43.387 / 52.762 / +9.375 / 3-0-29 |
| recommendation | 32 | 60.403 / 58.304 / -2.099 / 1-3-28 | 56.159 / 58.304 / +2.145 / 2-1-29 | 51.454 / 58.304 / +6.850 / 3-2-27 |
| social | 33 | 51.003 / 51.003 / +0.000 / 0-0-33 | 37.048 / 51.003 / +13.955 / 7-1-25 | 45.706 / 51.003 / +5.297 / 4-5-24 |
| takeaway | 12 | 25.460 / 42.126 / +16.667 / 2-0-10 | 25.460 / 42.126 / +16.667 / 2-0-10 | 42.126 / 42.126 / +0.000 / 1-1-10 |
| transport | 33 | 45.800 / 53.212 / +7.412 / 5-1-27 | 41.130 / 53.212 / +12.082 / 8-3-22 | 47.385 / 53.212 / +5.827 / 4-3-26 |
| weather | 33 | 42.358 / 35.633 / -6.725 / 2-3-28 | 23.247 / 35.633 / +12.386 / 6-1-26 | 31.511 / 35.633 / +4.122 / 5-3-25 |

### OLD500 — Strict entity slot F1

| Scenario | n | Repeat minus original: original / repeat / delta / S-H-T | Repeat minus control: control / repeat / delta / S-H-T | Repeat minus twin: twin / repeat / delta / S-H-T |
| --- | ---: | --- | --- | --- |
| alarm | 28 | 12.143 / 13.571 / +1.429 / 1-0-27 | 15.714 / 13.571 / -2.143 / 1-1-26 | 15.714 / 13.571 / -2.143 / 1-1-26 |
| audio | 28 | 0.000 / 0.000 / +0.000 / 0-0-28 | 3.571 / 0.000 / -3.571 / 0-1-27 | 3.571 / 0.000 / -3.571 / 0-1-27 |
| calendar | 28 | 9.524 / 9.524 / +0.000 / 0-0-28 | 9.524 / 9.524 / +0.000 / 0-0-28 | 11.905 / 9.524 / -2.381 / 0-1-27 |
| cooking | 28 | 29.762 / 29.762 / +0.000 / 0-0-28 | 16.667 / 29.762 / +13.095 / 4-0-24 | 19.048 / 29.762 / +10.714 / 3-0-25 |
| datetime | 28 | 26.667 / 26.667 / +0.000 / 0-0-28 | 24.286 / 26.667 / +2.381 / 1-0-27 | 27.857 / 26.667 / -1.190 / 1-1-26 |
| email | 28 | 9.524 / 9.524 / +0.000 / 1-1-26 | 8.929 / 9.524 / +0.595 / 1-1-26 | 9.524 / 9.524 / +0.000 / 0-0-28 |
| general | 28 | 14.286 / 16.667 / +2.381 / 1-0-27 | 14.286 / 16.667 / +2.381 / 2-1-25 | 11.310 / 16.667 / +5.357 / 3-0-25 |
| iot | 28 | 30.952 / 27.381 / -3.571 / 0-1-27 | 30.952 / 27.381 / -3.571 / 0-1-27 | 30.952 / 27.381 / -3.571 / 0-1-27 |
| lists | 28 | 14.286 / 14.286 / +0.000 / 0-0-28 | 14.286 / 14.286 / +0.000 / 0-0-28 | 14.286 / 14.286 / +0.000 / 0-0-28 |
| music | 28 | 7.143 / 7.143 / +0.000 / 0-0-28 | 9.524 / 7.143 / -2.381 / 0-1-27 | 7.143 / 7.143 / +0.000 / 0-0-28 |
| news | 28 | 23.810 / 17.857 / -5.952 / 0-2-26 | 10.714 / 17.857 / +7.143 / 2-0-26 | 23.810 / 17.857 / -5.952 / 1-3-24 |
| play | 28 | 33.333 / 28.571 / -4.762 / 0-2-26 | 28.571 / 28.571 / +0.000 / 0-0-28 | 30.952 / 28.571 / -2.381 / 0-1-27 |
| qa | 28 | 21.429 / 21.429 / +0.000 / 0-0-28 | 17.857 / 21.429 / +3.571 / 1-0-27 | 17.857 / 21.429 / +3.571 / 1-0-27 |
| recommendation | 28 | 10.357 / 12.143 / +1.786 / 1-1-26 | 14.524 / 12.143 / -2.381 / 1-2-25 | 15.714 / 12.143 / -3.571 / 1-2-25 |
| social | 27 | 58.025 / 57.407 / -0.617 / 1-1-25 | 45.062 / 57.407 / +12.346 / 6-1-20 | 50.000 / 57.407 / +7.407 / 6-3-18 |
| takeaway | 27 | 16.296 / 15.062 / -1.235 / 1-1-25 | 14.444 / 15.062 / +0.617 / 3-2-22 | 15.679 / 15.062 / -0.617 / 3-2-22 |
| transport | 27 | 37.302 / 37.302 / +0.000 / 0-0-27 | 33.034 / 37.302 / +4.268 / 6-4-17 | 19.577 / 37.302 / +17.725 / 7-0-20 |
| weather | 27 | 51.852 / 52.469 / +0.617 / 2-1-24 | 23.457 / 52.469 / +29.012 / 12-2-13 | 47.531 / 52.469 / +4.938 / 5-3-19 |

### OLD500 — Official entity-distance SLU-F1

| Scenario | n | Repeat minus original: original / repeat / delta / S-H-T | Repeat minus control: control / repeat / delta / S-H-T | Repeat minus twin: twin / repeat / delta / S-H-T |
| --- | ---: | --- | --- | --- |
| alarm | 28 | 15.724 / 16.100 / +0.376 / 1-0-27 | 18.789 / 16.100 / -2.689 / 1-1-26 | 18.789 / 16.100 / -2.689 / 1-1-26 |
| audio | 28 | 3.775 / 3.775 / +0.000 / 0-0-28 | 3.571 / 3.775 / +0.204 / 1-1-26 | 5.108 / 3.775 / -1.332 / 0-2-26 |
| calendar | 28 | 22.696 / 22.132 / -0.564 / 0-1-27 | 22.612 / 22.132 / -0.481 / 0-1-27 | 24.814 / 22.132 / -2.682 / 0-2-26 |
| cooking | 28 | 44.222 / 40.328 / -3.893 / 0-2-26 | 28.170 / 40.328 / +12.158 / 5-1-22 | 31.230 / 40.328 / +9.098 / 4-2-22 |
| datetime | 28 | 32.557 / 30.643 / -1.913 / 0-1-27 | 30.747 / 30.643 / -0.104 / 1-1-26 | 34.318 / 30.643 / -3.675 / 1-2-25 |
| email | 28 | 28.100 / 26.960 / -1.140 / 1-2-25 | 19.037 / 26.960 / +7.923 / 4-1-23 | 22.734 / 26.960 / +4.226 / 2-1-25 |
| general | 28 | 16.763 / 18.225 / +1.462 / 1-0-27 | 16.763 / 18.225 / +1.462 / 2-1-25 | 12.711 / 18.225 / +5.514 / 3-0-25 |
| iot | 28 | 33.494 / 29.923 / -3.571 / 0-1-27 | 33.494 / 29.923 / -3.571 / 0-1-27 | 33.494 / 29.923 / -3.571 / 0-1-27 |
| lists | 28 | 24.089 / 24.089 / +0.000 / 0-0-28 | 24.089 / 24.089 / +0.000 / 0-0-28 | 24.089 / 24.089 / +0.000 / 0-0-28 |
| music | 28 | 13.977 / 13.977 / +0.000 / 0-0-28 | 15.238 / 13.977 / -1.261 / 0-2-26 | 14.547 / 13.977 / -0.570 / 0-1-27 |
| news | 28 | 37.643 / 31.691 / -5.952 / 0-2-26 | 22.072 / 31.691 / +9.619 / 3-0-25 | 37.905 / 31.691 / -6.214 / 2-4-22 |
| play | 28 | 39.454 / 37.746 / -1.708 / 0-2-26 | 39.432 / 37.746 / -1.685 / 1-2-25 | 40.788 / 37.746 / -3.042 / 1-2-25 |
| qa | 28 | 34.381 / 34.381 / +0.000 / 0-0-28 | 30.810 / 34.381 / +3.571 / 1-0-27 | 30.810 / 34.381 / +3.571 / 1-0-27 |
| recommendation | 28 | 18.985 / 19.123 / +0.137 / 1-1-26 | 21.503 / 19.123 / -2.381 / 1-2-25 | 22.694 / 19.123 / -3.571 / 1-2-25 |
| social | 27 | 62.236 / 64.740 / +2.504 / 2-1-24 | 48.582 / 64.740 / +16.158 / 7-1-19 | 53.525 / 64.740 / +11.215 / 7-3-17 |
| takeaway | 27 | 37.052 / 35.618 / -1.434 / 3-2-22 | 37.820 / 35.618 / -2.203 / 4-3-20 | 37.404 / 35.618 / -1.786 / 5-5-17 |
| transport | 27 | 42.170 / 44.040 / +1.870 / 1-0-26 | 36.393 / 44.040 / +7.647 / 8-4-15 | 26.125 / 44.040 / +17.915 / 8-0-19 |
| weather | 27 | 55.500 / 54.374 / -1.126 / 2-2-23 | 23.457 / 54.374 / +30.917 / 13-2-12 | 49.436 / 54.374 / +4.938 / 5-3-19 |

### DEV1000 — Strict entity slot F1

| Scenario | n | Repeat minus original: original / repeat / delta / S-H-T | Repeat minus control: control / repeat / delta / S-H-T | Repeat minus twin: twin / repeat / delta / S-H-T |
| --- | ---: | --- | --- | --- |
| alarm | 58 | 13.736 / 17.299 / +3.563 / 3-0-55 | 13.908 / 17.299 / +3.391 / 4-2-52 | 13.046 / 17.299 / +4.253 / 5-1-52 |
| audio | 30 | 0.000 / 0.000 / +0.000 / 0-0-30 | 3.333 / 0.000 / -3.333 / 0-1-29 | 3.333 / 0.000 / -3.333 / 0-1-29 |
| calendar | 61 | 14.621 / 15.168 / +0.546 / 1-1-59 | 17.627 / 15.168 / -2.459 / 0-2-59 | 17.080 / 15.168 / -1.913 / 0-2-59 |
| cooking | 37 | 36.036 / 36.036 / +0.000 / 0-0-37 | 20.721 / 36.036 / +15.315 / 6-0-31 | 27.928 / 36.036 / +8.108 / 3-0-34 |
| datetime | 61 | 34.645 / 31.366 / -3.279 / 0-2-59 | 24.262 / 31.366 / +7.104 / 5-0-56 | 30.820 / 31.366 / +0.546 / 5-4-52 |
| email | 61 | 15.301 / 16.120 / +0.820 / 2-1-58 | 16.940 / 16.120 / -0.820 / 1-2-58 | 16.940 / 16.120 / -0.820 / 1-1-59 |
| general | 61 | 13.115 / 14.208 / +1.093 / 1-0-60 | 8.197 / 14.208 / +6.011 / 5-1-55 | 10.656 / 14.208 / +3.552 / 6-2-53 |
| iot | 61 | 33.333 / 33.333 / +0.000 / 1-1-59 | 34.973 / 33.333 / -1.639 / 0-1-60 | 32.514 / 33.333 / +0.820 / 2-2-57 |
| lists | 60 | 11.667 / 11.667 / +0.000 / 0-0-60 | 10.000 / 11.667 / +1.667 / 1-0-59 | 11.667 / 11.667 / +0.000 / 0-0-60 |
| music | 51 | 9.804 / 9.804 / +0.000 / 0-0-51 | 9.150 / 9.804 / +0.654 / 1-1-49 | 7.843 / 9.804 / +1.961 / 1-0-50 |
| news | 60 | 26.389 / 20.833 / -5.556 / 0-4-56 | 12.778 / 20.833 / +8.056 / 6-1-53 | 19.722 / 20.833 / +1.111 / 4-4-52 |
| play | 60 | 30.833 / 28.611 / -2.222 / 0-2-58 | 29.833 / 28.611 / -1.222 / 1-2-57 | 31.389 / 28.611 / -2.778 / 0-2-58 |
| qa | 60 | 34.167 / 35.833 / +1.667 / 1-0-59 | 27.500 / 35.833 / +8.333 / 5-0-55 | 29.167 / 35.833 / +6.667 / 4-0-56 |
| recommendation | 60 | 33.556 / 33.278 / -0.278 / 2-4-54 | 32.167 / 33.278 / +1.111 / 3-3-54 | 31.889 / 33.278 / +1.389 / 4-3-53 |
| social | 60 | 49.556 / 49.278 / -0.278 / 1-1-58 | 37.611 / 49.278 / +11.667 / 11-2-47 | 45.278 / 49.278 / +4.000 / 9-7-44 |
| takeaway | 39 | 15.556 / 19.829 / +4.274 / 3-1-35 | 14.274 / 19.829 / +5.556 / 5-2-32 | 20.256 / 19.829 / -0.427 / 4-3-32 |
| transport | 60 | 37.135 / 40.270 / +3.135 / 4-2-54 | 32.317 / 40.270 / +7.952 / 13-6-41 | 28.762 / 40.270 / +11.508 / 11-2-47 |
| weather | 60 | 39.444 / 37.500 / -1.944 / 3-3-54 | 22.500 / 37.500 / +15.000 / 14-3-43 | 36.667 / 37.500 / +0.833 / 7-6-47 |

### DEV1000 — Official entity-distance SLU-F1

| Scenario | n | Repeat minus original: original / repeat / delta / S-H-T | Repeat minus control: control / repeat / delta / S-H-T | Repeat minus twin: twin / repeat / delta / S-H-T |
| --- | ---: | --- | --- | --- |
| alarm | 58 | 25.494 / 27.713 / +2.219 / 3-0-55 | 26.341 / 27.713 / +1.372 / 5-1-52 | 24.790 / 27.713 / +2.923 / 5-1-52 |
| audio | 30 | 3.523 / 3.523 / +0.000 / 0-0-30 | 3.333 / 3.523 / +0.190 / 1-1-28 | 4.767 / 3.523 / -1.244 / 0-2-28 |
| calendar | 61 | 26.572 / 28.482 / +1.910 / 4-2-55 | 30.354 / 28.482 / -1.872 / 3-5-53 | 29.067 / 28.482 / -0.585 / 3-5-53 |
| cooking | 37 | 48.804 / 45.857 / -2.946 / 0-2-35 | 31.251 / 45.857 / +14.606 / 7-1-29 | 37.147 / 45.857 / +8.710 / 5-2-30 |
| datetime | 61 | 45.541 / 41.384 / -4.157 / 0-3-58 | 32.243 / 41.384 / +9.141 / 8-1-52 | 40.634 / 41.384 / +0.750 / 7-6-48 |
| email | 61 | 25.454 / 26.637 / +1.182 / 4-2-55 | 23.273 / 26.637 / +3.364 / 5-2-54 | 23.941 / 26.637 / +2.696 / 5-2-54 |
| general | 61 | 16.163 / 16.834 / +0.671 / 1-0-60 | 11.245 / 16.834 / +5.589 / 5-1-55 | 13.210 / 16.834 / +3.624 / 6-2-53 |
| iot | 61 | 40.227 / 39.054 / -1.173 / 1-1-59 | 39.830 / 39.054 / -0.777 / 1-1-59 | 36.828 / 39.054 / +2.225 / 3-2-56 |
| lists | 60 | 19.342 / 19.342 / +0.000 / 0-0-60 | 17.675 / 19.342 / +1.667 / 2-0-58 | 19.342 / 19.342 / +0.000 / 0-0-60 |
| music | 51 | 14.871 / 14.871 / +0.000 / 0-0-51 | 14.106 / 14.871 / +0.765 / 1-2-48 | 14.324 / 14.871 / +0.547 / 1-1-49 |
| news | 60 | 40.663 / 35.108 / -5.556 / 0-4-56 | 23.523 / 35.108 / +11.584 / 10-1-49 | 32.422 / 35.108 / +2.686 / 7-5-48 |
| play | 60 | 38.084 / 37.287 / -0.797 / 0-2-58 | 39.687 / 37.287 / -2.399 / 2-4-54 | 41.230 / 37.287 / -3.943 / 1-4-55 |
| qa | 60 | 42.518 / 44.184 / +1.667 / 1-0-59 | 35.851 / 44.184 / +8.333 / 5-0-55 | 37.518 / 44.184 / +6.667 / 4-0-56 |
| recommendation | 60 | 41.075 / 40.019 / -1.055 / 2-4-54 | 39.987 / 40.019 / +0.033 / 3-3-54 | 38.033 / 40.019 / +1.987 / 4-4-52 |
| social | 60 | 56.058 / 57.185 / +1.127 / 2-1-57 | 42.238 / 57.185 / +14.946 / 14-2-44 | 49.225 / 57.185 / +7.960 / 11-8-41 |
| takeaway | 39 | 33.485 / 37.620 / +4.135 / 5-2-32 | 34.017 / 37.620 / +3.603 / 6-3-30 | 38.857 / 37.620 / -1.236 / 6-6-27 |
| transport | 60 | 44.167 / 49.085 / +4.918 / 6-1-53 | 38.998 / 49.085 / +10.086 / 16-7-37 | 37.818 / 49.085 / +11.267 / 12-3-45 |
| weather | 60 | 48.272 / 44.067 / -4.205 / 4-5-51 | 23.341 / 44.067 / +20.725 / 19-3-38 | 39.577 / 44.067 / +4.489 / 10-6-44 |

## Evidence bindings

| Artifact | Path | SHA-256 |
| --- | --- | --- |
| Raw repeat manifest | /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-SLURP-KU-S3A-INDEPENDENT-REPEAT-MAX256-V1/attempt-independent-s3a-repeat-v1/SAEA-SLURP-KU-S3A-INDEPENDENT-REPEAT-MAX256-V1.run-manifest.json | 9e66a5a90edac62ea26c2eaeb99e0cbe1c97207f5399d22e2b7d4ec1ed736008 |
| Raw repeat outputs | /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-SLURP-KU-S3A-INDEPENDENT-REPEAT-MAX256-V1/attempt-independent-s3a-repeat-v1/SAEA-SLURP-KU-S3A-INDEPENDENT-REPEAT-MAX256-V1.outputs.jsonl | 134b30b62a6e4042b38f004dd93f84a7f03853208d10d10ecce294022e9eff6f |
| Direct predecessor manifest | /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1/attempt-20260905T060424Z-2c5596/SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1.run-manifest.json | f908ff4c7b0267322b34c7bf2ca9ad29d6db97ee8bb3cf18bf8824a057ebc94c |
| Direct predecessor outputs | /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1/attempt-20260905T060424Z-2c5596/SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1.outputs.jsonl | 34fda7fa51410e0f4f7e8ba7c35f867c32f53c244de63af5386860486fcb885b |
| Joined derivative manifest | /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-SLURP-KU-S3A-INDEPENDENT-REPEAT-MAX256-V1/derived-inherited-intent-slots-v1/SAEA-SLURP-KU-S3A-INDEPENDENT-REPEAT-MAX256-V1--delivery-inherited-intent-slots-v1.run-manifest.json | 023f95e00a296febbc6fd4af94a1e04fbb28b7969fdd91029a24554ecd28aab4 |
| Complete official score | /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/analysis/SAEA-SLURP-KU-S3A-INDEPENDENT-REPEAT-MAX256-V1/official-scoring-v1/repeat.score.json | 6acd07639379fb770879522cfa24cd1d693eb4037127380cd699e693df72698a |
| Complete score receipt | /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/analysis/SAEA-SLURP-KU-S3A-INDEPENDENT-REPEAT-MAX256-V1/official-scoring-v1/repeat.complete-score-receipt.json | 2a241cafb7c094bf2bc4c5bb36f970af449a726d909a461761a94bb295ea1405 |
| Saved-score comparison config | /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/analysis/SAEA-SLURP-KU-S3A-INDEPENDENT-REPEAT-MAX256-V1/saved-score-comparison-v1/score-contrasts.config.json | 22ecbd6b4d67dbcc5df8872cc8e5fe6f6a9ef083abb5d10cd1038add94681462 |
| Saved-score comparison result | /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/analysis/SAEA-SLURP-KU-S3A-INDEPENDENT-REPEAT-MAX256-V1/saved-score-comparison-v1/score-contrasts.json | dade35f88b222a2120f26ba2a86c551642b4ef7cdfe207b984759d0e90834249 |
| Raw byte-agreement result | /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/analysis/SAEA-SLURP-KU-S3A-INDEPENDENT-REPEAT-MAX256-V1/saved-score-comparison-v1/byte-agreement.json | 9641afd0d23570dd8ebe99b402b7b159df30805d8a7607e5dec02b3a5663cddd |
| Generation cost closure | /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/coordination/slurp-s3-independent-repeat-seal-cost-handoff-v1.json | 4af3d846107e17657967bb3e663c6a38cc61a93438ffdd97904b4d5a358dd9b1 |

Frozen generation source: /home/chao/saea-worktrees/slurp-s3-independent-repeat at 683bd0ec4f050b3f270b3c4a1dd8171bc5d8f696. Frozen inherited-delivery and scoring source: /home/chao/saea-worktrees/slurp-inherited-delivery at 6fbacf77. The report source is based on master fa155bea37691bf9c711ee37bf5848febcf4fb98.

## Decision boundary

The repeat supports the inherited component direction against the retained control and form twin on NEW500. It does not establish process equivalence with the original treatment, a fresh same-process causal comparison, a held-out result, or a complete live intent-to-slots pipeline claim. No additional S3 bootstrap or scoring is required.
