# Reviewer update2 control-aa: independently qualified descriptive read

Root read checked at 2026-10-09T04:13:14.471190+00:00. The original member independently finalized 100 inputs with a verified seal, one successful complete official score and zero failed jobs. The exact member READ is separately signed; both original reader layers exited zero. No scoring, model or tokenizer contact was repeated. This is a single-member description: no sibling or historical contrast, selection, policy change or learner export.

Source report: `/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/analysis/local-reviewer-n100-k4-update2-control-aa-descriptive-v1/report.json`; SHA-256 `00debd5c63e9d73771338e54bbfa849cccee6856203955f163fce6bc10a220a4`.

Official pooled SLU-F1: 0.6165515656; intent: 85/100; reliable completion: 100/100. Equal-scenario descriptive F1: 0.5326554302. Contacts: 607 model and 0 tool.

## Process statistics

| Metric | Numerator / observed denominator | Eligible | Unknown | Observed rate | Wilson 95% interval | Missing bounds |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| draft_entity_correct | 42/84 | 100 | 16 | 0.5000 | [0.3954, 0.6046] | [0.4200, 0.5800] |
| draft_full_correct | 36/100 | 100 | 0 | 0.3600 | [0.2727, 0.4576] | [0.3600, 0.3600] |
| draft_parsed | 84/100 | 100 | 0 | 0.8400 | [0.7558, 0.8990] | [0.8400, 0.8400] |
| empty_gold_false_fill | 10/34 | 34 | 0 | 0.2941 | [0.1683, 0.4617] | [0.2941, 0.2941] |
| entity_harm_given_revision | 1/23 | 23 | 0 | 0.0435 | [0.0077, 0.2099] | [0.0435, 0.0435] |
| entity_repair_after_alarm | 1/26 | 26 | 0 | 0.0385 | [0.0068, 0.1889] | [0.0385, 0.0385] |
| entity_repair_given_revision | 1/30 | 30 | 0 | 0.0333 | [0.0059, 0.1667] | [0.0333, 0.0333] |
| final_entity_correct | 47/100 | 100 | 0 | 0.4700 | [0.3751, 0.5671] | [0.4700, 0.4700] |
| final_full_correct | 40/100 | 100 | 0 | 0.4000 | [0.3094, 0.4980] | [0.4000, 0.4000] |
| final_parsed | 100/100 | 100 | 0 | 1.0000 | [0.9630, 1.0000] | [1.0000, 1.0000] |
| full_harm_given_revision | 1/20 | 20 | 0 | 0.0500 | [0.0089, 0.2361] | [0.0500, 0.0500] |
| full_repair_given_revision | 4/49 | 49 | 0 | 0.0816 | [0.0322, 0.1919] | [0.0816, 0.0816] |
| handoff_visibility_given_valid_review | 96/96 | 96 | 0 | 1.0000 | [0.9615, 1.0000] | [1.0000, 1.0000] |
| review_alarm_precision | 26/42 | 57 | 15 | 0.6190 | [0.4681, 0.7500] | [0.4561, 0.7193] |
| review_error_detection | 26/42 | 42 | 0 | 0.6190 | [0.4681, 0.7500] | [0.6190, 0.6190] |
| review_false_alarm | 16/39 | 42 | 3 | 0.4103 | [0.2708, 0.5658] | [0.3810, 0.4524] |
| review_miss | 16/42 | 42 | 0 | 0.3810 | [0.2500, 0.5319] | [0.3810, 0.3810] |
| review_valid | 96/100 | 100 | 0 | 0.9600 | [0.9016, 0.9843] | [0.9600, 0.9600] |
| revision_after_alarm | 55/57 | 57 | 0 | 0.9649 | [0.8808, 0.9903] | [0.9649, 0.9649] |
| revision_of_correct_draft | 20/36 | 36 | 0 | 0.5556 | [0.3958, 0.7046] | [0.5556, 0.5556] |

Observed-case rates retain their own denominator; unknown states are not silently treated as correct. The fixed-N local primary below uses every input. The review indicators describe agreement with offline correctness, not the semantic validity of criticism or causal node contribution.

## Raw model revision and deterministic delivery

| Stage | Target | Wrong to correct | Correct to wrong | Net repairs | Stable correct | Stable wrong | Unknown |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| model_revision | entity | 0 | 1 | -1 | 41 | 42 | 16 |
| model_revision | full | 3 | 1 | 2 | 35 | 61 | 0 |
| postprocessing | entity | 3 | 0 | 3 | 44 | 53 | 0 |
| postprocessing | full | 2 | 0 | 2 | 38 | 60 | 0 |

The registered raw entity model-revision primary is -1/100: 0 known repairs minus 1 known harms. The 16 unknown transitions contribute zero to this fixed-N primary and remain explicit. The raw endpoint is first raw Solver answer to selected raw Solver answer; the first answer is after any within-visit tools.

The selected raw answer to final delivery is a separate deterministic postprocessing stage. Final-delivery conditional repair/harm rates and raw model-revision transitions use different endpoints and must not be substituted for each other. An initial unknown state becoming a known correct state is not a verified wrong-to-correct model repair.

## Knowledge availability boundary

- candidate_coverage_given_card: 92/98, unknown 0.
- gold_intent_card_in_initial_request: 98/100, unknown 0.
- gold_intent_in_initial_candidates: 92/100, unknown 0.

These measures separately report own-intent card presence in the actual initial Perception request and gold-intent coverage in the initial candidate set. They do not prove semantic consumption, raw retrieval-pool recall, or entity-type/value support; no gold is added to runtime.

## Per-scenario description

| Scenario | N | Official F1 | Intent | Raw entity correct | Raw entity unknown | Final entity correct / observed | Final entity unknown | Empty false fill / eligible |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| alarm | 5 | 0.8421 | 0.8000 | 1 | 2 | 2/5 | 0 | not eligible |
| audio | 9 | 0.5000 | 0.5556 | 7 | 1 | 7/9 | 0 | 1/8 |
| calendar | 8 | 0.6621 | 1.0000 | 3 | 0 | 3/8 | 0 | 0/2 |
| cooking | 7 | 0.6692 | 0.7143 | 2 | 2 | 3/7 | 0 | 1/1 |
| datetime | 4 | 0.4259 | 1.0000 | 1 | 2 | 1/4 | 0 | 0/1 |
| email | 3 | 0.0000 | 1.0000 | 1 | 0 | 1/3 | 0 | 2/3 |
| general | 8 | 0.2500 | 0.6250 | 4 | 1 | 4/8 | 0 | 3/6 |
| iot | 5 | 0.5000 | 1.0000 | 1 | 3 | 3/5 | 0 | 1/3 |
| lists | 8 | 0.6076 | 0.8750 | 4 | 0 | 4/8 | 0 | 0/3 |
| music | 5 | 0.0000 | 0.8000 | 3 | 0 | 3/5 | 0 | 1/4 |
| news | 5 | 0.9091 | 0.8000 | 2 | 1 | 4/5 | 0 | 0/1 |
| play | 5 | 0.4901 | 0.8000 | 1 | 0 | 1/5 | 0 | not eligible |
| qa | 5 | 0.7003 | 1.0000 | 3 | 1 | 3/5 | 0 | not eligible |
| recommendation | 4 | 0.7395 | 1.0000 | 3 | 1 | 3/4 | 0 | 0/1 |
| social | 3 | 0.2569 | 0.6667 | 1 | 0 | 0/3 | 0 | 1/1 |
| takeaway | 5 | 0.6791 | 1.0000 | 1 | 1 | 1/5 | 0 | not eligible |
| transport | 5 | 0.5866 | 1.0000 | 1 | 1 | 1/5 | 0 | not eligible |
| weather | 6 | 0.7692 | 1.0000 | 3 | 0 | 3/6 | 0 | not eligible |

Small strata are descriptive and do not establish stratum-specific superiority.

## Per-scenario review indicators

| Scenario | Error detection | Unknown detection | False alarm | Unknown false alarm | Alarm precision | Unknown alarm correctness |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| alarm | 0/2 | 0 | 1/1 | 0 | 0/1 | 2 |
| audio | 0/1 | 0 | 0/6 | 1 | unavailable (0 observed; 1 eligible) | 1 |
| calendar | 5/5 | 0 | 1/3 | 0 | 5/6 | 0 |
| cooking | 3/3 | 0 | 1/2 | 0 | 3/4 | 2 |
| datetime | 1/1 | 0 | 0/1 | 0 | 1/1 | 2 |
| email | 2/2 | 0 | 0/1 | 0 | 2/2 | 0 |
| general | 3/3 | 0 | 1/2 | 2 | 3/4 | 1 |
| iot | 0/1 | 0 | 0/1 | 0 | unavailable (0 observed; 2 eligible) | 2 |
| lists | 3/4 | 0 | 0/4 | 0 | 3/3 | 0 |
| music | 1/2 | 0 | 0/3 | 0 | 1/1 | 0 |
| news | 2/2 | 0 | 1/2 | 0 | 2/3 | 1 |
| play | 2/4 | 0 | 1/1 | 0 | 2/3 | 0 |
| qa | 1/1 | 0 | 2/3 | 0 | 1/3 | 1 |
| recommendation | not eligible | 0 | 2/3 | 0 | 0/2 | 1 |
| social | 1/2 | 0 | 1/1 | 0 | 1/2 | 0 |
| takeaway | 0/3 | 0 | 1/1 | 0 | 0/1 | 1 |
| transport | 2/3 | 0 | 1/1 | 0 | 2/3 | 1 |
| weather | 0/3 | 0 | 3/3 | 0 | 0/3 | 0 |

## Secondary timing

First admitted input: 54.325s. All-input mean: 35.252s; nonfirst mean: 35.059s; p95: 58.444s. Batch wall/input: 8.877s is amortized throughput, not input latency. Mean pre-admission wait: 402.232s, reported separately. First/nonfirst grouping is not proof of cold/warm cache state.

| Role | Visits | Mean client s | Mean prefill s | Mean decode s | Reused input fraction |
| --- | ---: | ---: | ---: | ---: | ---: |
| perception | 100 | 6.468 | 0.654 | 5.650 | 0.6310 |
| planner | 169 | 0.950 | 0.425 | 0.242 | 0.9501 |
| reviewer | 169 | 10.210 | 0.297 | 9.691 | 0.9691 |
| solver | 169 | 4.375 | 2.130 | 1.908 | 0.6095 |

The full Reviewer family must independently qualify and its exact root READ must be signed before contrasts, local selection or learning. Preserve the active worker, templates, knowledge, data, official scorer, resource policy and peer-module isolation.

Independent GPT-6 Astra Ultra audit matched this member's numeric metrics, fixed-N primary, stage transitions, all eighteen strata and timing to the authorized original report. Zero observed denominators with positive eligibility are unavailable estimates, not inapplicable cases. The audit made no sibling comparison, selection or learning export.
