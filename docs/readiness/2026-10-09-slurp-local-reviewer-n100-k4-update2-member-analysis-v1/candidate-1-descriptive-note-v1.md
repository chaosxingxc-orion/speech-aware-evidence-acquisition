# Reviewer update2 candidate-1: independently qualified descriptive read

Root read checked at 2026-10-09T04:13:14.487833+00:00. The original member independently finalized 100 inputs with a verified seal, one successful complete official score and zero failed jobs. The exact member READ is separately signed; both original reader layers exited zero. No scoring, model or tokenizer contact was repeated. This is a single-member description: no sibling or historical contrast, selection, policy change or learner export.

Source report: `/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/analysis/local-reviewer-n100-k4-update2-candidate-1-descriptive-v1/report.json`; SHA-256 `91230b5b8b61efcc1f4aafe2d5f922b6f86b2605036e9e8af9738ba88e929fb8`.

Official pooled SLU-F1: 0.6176962668; intent: 84/100; reliable completion: 100/100. Equal-scenario descriptive F1: 0.5538225150. Contacts: 610 model and 0 tool.

## Process statistics

| Metric | Numerator / observed denominator | Eligible | Unknown | Observed rate | Wilson 95% interval | Missing bounds |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| draft_entity_correct | 37/84 | 100 | 16 | 0.4405 | [0.3392, 0.5469] | [0.3700, 0.5300] |
| draft_full_correct | 32/100 | 100 | 0 | 0.3200 | [0.2367, 0.4166] | [0.3200, 0.3200] |
| draft_parsed | 84/100 | 100 | 0 | 0.8400 | [0.7558, 0.8990] | [0.8400, 0.8400] |
| empty_gold_false_fill | 11/34 | 34 | 0 | 0.3235 | [0.1913, 0.4916] | [0.3235, 0.3235] |
| entity_harm_given_revision | 0/20 | 20 | 0 | 0.0000 | [0.0000, 0.1611] | [0.0000, 0.0000] |
| entity_repair_after_alarm | 2/26 | 26 | 0 | 0.0769 | [0.0214, 0.2414] | [0.0769, 0.0769] |
| entity_repair_given_revision | 2/34 | 34 | 0 | 0.0588 | [0.0163, 0.1909] | [0.0588, 0.0588] |
| final_entity_correct | 48/100 | 100 | 0 | 0.4800 | [0.3846, 0.5768] | [0.4800, 0.4800] |
| final_full_correct | 40/100 | 100 | 0 | 0.4000 | [0.3094, 0.4980] | [0.4000, 0.4000] |
| final_parsed | 100/100 | 100 | 0 | 1.0000 | [0.9630, 1.0000] | [1.0000, 1.0000] |
| full_harm_given_revision | 0/17 | 17 | 0 | 0.0000 | [0.0000, 0.1843] | [0.0000, 0.0000] |
| full_repair_given_revision | 7/53 | 53 | 0 | 0.1321 | [0.0655, 0.2484] | [0.1321, 0.1321] |
| handoff_visibility_given_valid_review | 99/99 | 99 | 0 | 1.0000 | [0.9626, 1.0000] | [1.0000, 1.0000] |
| review_alarm_precision | 26/31 | 34 | 3 | 0.8387 | [0.6737, 0.9291] | [0.7647, 0.8529] |
| review_error_detection | 26/46 | 47 | 1 | 0.5652 | [0.4225, 0.6979] | [0.5532, 0.5745] |
| review_false_alarm | 5/37 | 37 | 0 | 0.1351 | [0.0591, 0.2798] | [0.1351, 0.1351] |
| review_miss | 20/46 | 47 | 1 | 0.4348 | [0.3021, 0.5775] | [0.4255, 0.4468] |
| review_valid | 99/100 | 100 | 0 | 0.9900 | [0.9455, 0.9982] | [0.9900, 0.9900] |
| revision_after_alarm | 34/34 | 34 | 0 | 1.0000 | [0.8985, 1.0000] | [1.0000, 1.0000] |
| revision_of_correct_draft | 17/32 | 32 | 0 | 0.5312 | [0.3645, 0.6913] | [0.5312, 0.5312] |

Observed-case rates retain their own denominator; unknown states are not silently treated as correct. The fixed-N local primary below uses every input. The review indicators describe agreement with offline correctness, not the semantic validity of criticism or causal node contribution.

## Raw model revision and deterministic delivery

| Stage | Target | Wrong to correct | Correct to wrong | Net repairs | Stable correct | Stable wrong | Unknown |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| model_revision | entity | 2 | 1 | 1 | 36 | 45 | 16 |
| model_revision | full | 7 | 1 | 6 | 31 | 61 | 0 |
| postprocessing | entity | 3 | 0 | 3 | 45 | 52 | 0 |
| postprocessing | full | 2 | 0 | 2 | 38 | 60 | 0 |

The registered raw entity model-revision primary is 1/100: 2 known repairs minus 1 known harms. The 16 unknown transitions contribute zero to this fixed-N primary and remain explicit. The raw endpoint is first raw Solver answer to selected raw Solver answer; the first answer is after any within-visit tools.

The selected raw answer to final delivery is a separate deterministic postprocessing stage. Final-delivery conditional repair/harm rates and raw model-revision transitions use different endpoints and must not be substituted for each other. An initial unknown state becoming a known correct state is not a verified wrong-to-correct model repair.

## Knowledge availability boundary

- candidate_coverage_given_card: 92/98, unknown 0.
- gold_intent_card_in_initial_request: 98/100, unknown 0.
- gold_intent_in_initial_candidates: 92/100, unknown 0.

These measures separately report own-intent card presence in the actual initial Perception request and gold-intent coverage in the initial candidate set. They do not prove semantic consumption, raw retrieval-pool recall, or entity-type/value support; no gold is added to runtime.

## Per-scenario description

| Scenario | N | Official F1 | Intent | Raw entity correct | Raw entity unknown | Final entity correct / observed | Final entity unknown | Empty false fill / eligible |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| alarm | 5 | 0.9000 | 1.0000 | 1 | 3 | 3/5 | 0 | not eligible |
| audio | 9 | 0.5660 | 0.5556 | 7 | 1 | 7/9 | 0 | 1/8 |
| calendar | 8 | 0.6621 | 1.0000 | 3 | 0 | 3/8 | 0 | 0/2 |
| cooking | 7 | 0.5657 | 0.5714 | 1 | 4 | 3/7 | 0 | 1/1 |
| datetime | 4 | 0.5678 | 1.0000 | 2 | 2 | 2/4 | 0 | 0/1 |
| email | 3 | 0.0000 | 1.0000 | 0 | 0 | 0/3 | 0 | 3/3 |
| general | 8 | 0.2857 | 0.5000 | 3 | 1 | 4/8 | 0 | 3/6 |
| iot | 5 | 0.5000 | 1.0000 | 2 | 1 | 3/5 | 0 | 1/3 |
| lists | 8 | 0.6076 | 0.8750 | 4 | 0 | 5/8 | 0 | 0/3 |
| music | 5 | 0.0000 | 0.8000 | 3 | 0 | 3/5 | 0 | 1/4 |
| news | 5 | 0.9091 | 0.8000 | 3 | 0 | 4/5 | 0 | 0/1 |
| play | 5 | 0.3916 | 0.8000 | 0 | 0 | 0/5 | 0 | not eligible |
| qa | 5 | 0.7542 | 1.0000 | 0 | 4 | 3/5 | 0 | not eligible |
| recommendation | 4 | 0.7225 | 1.0000 | 3 | 0 | 3/4 | 0 | 0/1 |
| social | 3 | 0.7200 | 0.6667 | 1 | 0 | 1/3 | 0 | 1/1 |
| takeaway | 5 | 0.7007 | 1.0000 | 1 | 0 | 1/5 | 0 | not eligible |
| transport | 5 | 0.4491 | 1.0000 | 0 | 0 | 0/5 | 0 | not eligible |
| weather | 6 | 0.6667 | 1.0000 | 3 | 0 | 3/6 | 0 | not eligible |

Small strata are descriptive and do not establish stratum-specific superiority.

## Per-scenario review indicators

| Scenario | Error detection | Unknown detection | False alarm | Unknown false alarm | Alarm precision | Unknown alarm correctness |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| alarm | 0/1 | 0 | 0/1 | 0 | unavailable (0 observed; 1 eligible) | 1 |
| audio | 1/1 | 0 | 0/7 | 0 | 1/1 | 0 |
| calendar | 4/5 | 0 | 0/3 | 0 | 4/4 | 0 |
| cooking | 1/2 | 0 | 0/1 | 0 | 1/1 | 0 |
| datetime | not eligible | 0 | 1/2 | 0 | 0/1 | 1 |
| email | 0/3 | 0 | not eligible | 0 | not eligible | 0 |
| general | 3/4 | 0 | 0/3 | 0 | 3/3 | 1 |
| iot | 0/2 | 0 | 0/2 | 0 | not eligible | 0 |
| lists | 4/4 | 0 | 0/4 | 0 | 4/4 | 0 |
| music | 2/2 | 0 | 0/3 | 0 | 2/2 | 0 |
| news | 1/2 | 0 | 1/3 | 0 | 1/2 | 0 |
| play | 4/5 | 0 | not eligible | 0 | 4/4 | 0 |
| qa | 1/1 | 0 | not eligible | 0 | 1/1 | 0 |
| recommendation | 0/1 | 0 | 0/3 | 0 | not eligible | 0 |
| social | 1/1 | 1 | 1/1 | 0 | 1/2 | 0 |
| takeaway | 1/4 | 0 | 0/1 | 0 | 1/1 | 0 |
| transport | 3/5 | 0 | not eligible | 0 | 3/3 | 0 |
| weather | 0/3 | 0 | 2/3 | 0 | 0/2 | 0 |

## Secondary timing

First admitted input: 28.391s. All-input mean: 30.121s; nonfirst mean: 30.138s; p95: 45.253s. Batch wall/input: 7.578s is amortized throughput, not input latency. Mean pre-admission wait: 347.739s, reported separately. First/nonfirst grouping is not proof of cold/warm cache state.

| Role | Visits | Mean client s | Mean prefill s | Mean decode s | Reused input fraction |
| --- | ---: | ---: | ---: | ---: | ---: |
| perception | 100 | 7.439 | 0.714 | 6.356 | 0.6310 |
| planner | 170 | 1.049 | 0.393 | 0.318 | 0.9557 |
| reviewer | 170 | 5.404 | 0.420 | 4.710 | 0.9493 |
| solver | 170 | 5.206 | 2.259 | 2.416 | 0.6052 |

The full Reviewer family must independently qualify and its exact root READ must be signed before contrasts, local selection or learning. Preserve the active worker, templates, knowledge, data, official scorer, resource policy and peer-module isolation.

Independent GPT-6 Astra Ultra audit matched this member's numeric metrics, fixed-N primary, stage transitions, all eighteen strata and timing to the authorized original report. Zero observed denominators with positive eligibility are unavailable estimates, not inapplicable cases. The audit made no sibling comparison, selection or learning export.
