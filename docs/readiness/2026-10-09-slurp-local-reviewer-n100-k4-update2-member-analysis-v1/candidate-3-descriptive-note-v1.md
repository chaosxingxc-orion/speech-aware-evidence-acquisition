# Reviewer update2 candidate-3: independently qualified descriptive read

Root read checked at 2026-10-09T04:29:38.091223+00:00. The original member independently finalized 100 inputs with a verified seal, one successful complete official score and zero failed jobs. The exact member READ is separately signed; both original reader layers exited zero. No scoring, model or tokenizer contact was repeated. This is a single-member description: no sibling or historical contrast, selection, policy change or learner export.

Source report: `/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/analysis/local-reviewer-n100-k4-update2-candidate-3-descriptive-v1/report.json`; SHA-256 `2013b2ce64373ed42901cfefd069addc5ab61afeec847aaba4cedfa1837591c7`.

Official pooled SLU-F1: 0.5986874872; intent: 83/100; reliable completion: 100/100. Equal-scenario descriptive F1: 0.5299156693. Contacts: 634 model and 0 tool.

## Process statistics

| Metric | Numerator / observed denominator | Eligible | Unknown | Observed rate | Wilson 95% interval | Missing bounds |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| draft_entity_correct | 37/83 | 100 | 17 | 0.4458 | [0.3436, 0.5527] | [0.3700, 0.5400] |
| draft_full_correct | 33/100 | 100 | 0 | 0.3300 | [0.2456, 0.4269] | [0.3300, 0.3300] |
| draft_parsed | 83/100 | 100 | 0 | 0.8300 | [0.7445, 0.8911] | [0.8300, 0.8300] |
| empty_gold_false_fill | 15/34 | 34 | 0 | 0.4412 | [0.2888, 0.6055] | [0.4412, 0.4412] |
| entity_harm_given_revision | 1/25 | 25 | 0 | 0.0400 | [0.0071, 0.1954] | [0.0400, 0.0400] |
| entity_repair_after_alarm | 4/38 | 38 | 0 | 0.1053 | [0.0417, 0.2413] | [0.1053, 0.1053] |
| entity_repair_given_revision | 4/38 | 38 | 0 | 0.1053 | [0.0417, 0.2413] | [0.1053, 0.1053] |
| final_entity_correct | 44/98 | 100 | 2 | 0.4490 | [0.3543, 0.5475] | [0.4400, 0.4600] |
| final_full_correct | 37/100 | 100 | 0 | 0.3700 | [0.2818, 0.4678] | [0.3700, 0.3700] |
| final_parsed | 98/100 | 100 | 0 | 0.9800 | [0.9300, 0.9945] | [0.9800, 0.9800] |
| full_harm_given_revision | 1/23 | 23 | 0 | 0.0435 | [0.0077, 0.2099] | [0.0435, 0.0435] |
| full_repair_given_revision | 5/55 | 55 | 0 | 0.0909 | [0.0395, 0.1958] | [0.0909, 0.0909] |
| handoff_visibility_given_valid_review | 92/92 | 92 | 0 | 1.0000 | [0.9599, 1.0000] | [1.0000, 1.0000] |
| review_alarm_precision | 38/59 | 75 | 16 | 0.6441 | [0.5166, 0.7540] | [0.5067, 0.7200] |
| review_error_detection | 38/43 | 46 | 3 | 0.8837 | [0.7552, 0.9493] | [0.8261, 0.8913] |
| review_false_alarm | 21/33 | 37 | 4 | 0.6364 | [0.4662, 0.7781] | [0.5676, 0.6757] |
| review_miss | 5/43 | 46 | 3 | 0.1163 | [0.0507, 0.2448] | [0.1087, 0.1739] |
| review_valid | 92/100 | 100 | 0 | 0.9200 | [0.8500, 0.9589] | [0.9200, 0.9200] |
| revision_after_alarm | 68/75 | 75 | 0 | 0.9067 | [0.8197, 0.9541] | [0.9067, 0.9067] |
| revision_of_correct_draft | 23/33 | 33 | 0 | 0.6970 | [0.5266, 0.8262] | [0.6970, 0.6970] |

Observed-case rates retain their own denominator; unknown states are not silently treated as correct. The fixed-N local primary below uses every input. The review indicators describe agreement with offline correctness, not the semantic validity of criticism or causal node contribution.

## Raw model revision and deterministic delivery

| Stage | Target | Wrong to correct | Correct to wrong | Net repairs | Stable correct | Stable wrong | Unknown |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| model_revision | entity | 1 | 1 | 0 | 36 | 45 | 17 |
| model_revision | full | 4 | 1 | 3 | 32 | 63 | 0 |
| postprocessing | entity | 3 | 0 | 3 | 41 | 54 | 2 |
| postprocessing | full | 1 | 0 | 1 | 36 | 63 | 0 |

The registered raw entity model-revision primary is 0/100: 1 known repairs minus 1 known harms. The 17 unknown transitions contribute zero to this fixed-N primary and remain explicit. The raw endpoint is first raw Solver answer to selected raw Solver answer; the first answer is after any within-visit tools.

The selected raw answer to final delivery is a separate deterministic postprocessing stage. Final-delivery conditional repair/harm rates and raw model-revision transitions use different endpoints and must not be substituted for each other. An initial unknown state becoming a known correct state is not a verified wrong-to-correct model repair.

## Knowledge availability boundary

- candidate_coverage_given_card: 92/98, unknown 0.
- gold_intent_card_in_initial_request: 98/100, unknown 0.
- gold_intent_in_initial_candidates: 92/100, unknown 0.

These measures separately report own-intent card presence in the actual initial Perception request and gold-intent coverage in the initial candidate set. They do not prove semantic consumption, raw retrieval-pool recall, or entity-type/value support; no gold is added to runtime.

## Per-scenario description

| Scenario | N | Official F1 | Intent | Raw entity correct | Raw entity unknown | Final entity correct / observed | Final entity unknown | Empty false fill / eligible |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| alarm | 5 | 0.9000 | 0.8000 | 1 | 2 | 3/5 | 0 | not eligible |
| audio | 9 | 0.5000 | 0.5556 | 6 | 1 | 7/9 | 0 | 2/8 |
| calendar | 8 | 0.6044 | 1.0000 | 3 | 0 | 3/8 | 0 | 0/2 |
| cooking | 7 | 0.5354 | 0.5714 | 2 | 2 | 2/6 | 1 | 1/1 |
| datetime | 4 | 0.4584 | 1.0000 | 1 | 1 | 1/4 | 0 | 0/1 |
| email | 3 | 0.0000 | 1.0000 | 1 | 0 | 1/3 | 0 | 2/3 |
| general | 8 | 0.2500 | 0.5000 | 3 | 1 | 3/8 | 0 | 4/6 |
| iot | 5 | 0.4000 | 1.0000 | 1 | 2 | 2/5 | 0 | 2/3 |
| lists | 8 | 0.7059 | 0.8750 | 4 | 0 | 5/8 | 0 | 0/3 |
| music | 5 | 0.0000 | 1.0000 | 2 | 1 | 1/5 | 0 | 3/4 |
| news | 5 | 0.9091 | 0.8000 | 3 | 0 | 4/5 | 0 | 0/1 |
| play | 5 | 0.5117 | 0.8000 | 1 | 0 | 1/5 | 0 | not eligible |
| qa | 5 | 0.6198 | 0.8000 | 1 | 3 | 2/4 | 1 | not eligible |
| recommendation | 4 | 0.7586 | 1.0000 | 2 | 2 | 3/4 | 0 | 0/1 |
| social | 3 | 0.5138 | 0.6667 | 1 | 0 | 1/3 | 0 | 1/1 |
| takeaway | 5 | 0.7557 | 1.0000 | 2 | 1 | 2/5 | 0 | not eligible |
| transport | 5 | 0.4491 | 1.0000 | 0 | 1 | 0/5 | 0 | not eligible |
| weather | 6 | 0.6667 | 1.0000 | 3 | 0 | 3/6 | 0 | not eligible |

Small strata are descriptive and do not establish stratum-specific superiority.

## Per-scenario review indicators

| Scenario | Error detection | Unknown detection | False alarm | Unknown false alarm | Alarm precision | Unknown alarm correctness |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| alarm | 2/2 | 0 | 1/1 | 0 | 2/3 | 2 |
| audio | 2/2 | 0 | 0/4 | 2 | 2/2 | 1 |
| calendar | 5/5 | 0 | 2/3 | 0 | 5/7 | 0 |
| cooking | 3/3 | 0 | 2/2 | 0 | 3/5 | 2 |
| datetime | 2/2 | 0 | 0/1 | 0 | 2/2 | 1 |
| email | 2/2 | 0 | 0/1 | 0 | 2/2 | 0 |
| general | 3/3 | 1 | 1/1 | 2 | 3/4 | 1 |
| iot | 2/2 | 0 | 1/1 | 0 | 2/3 | 1 |
| lists | 4/4 | 0 | 1/4 | 0 | 4/5 | 0 |
| music | 1/1 | 1 | 2/2 | 0 | 1/3 | 1 |
| news | 2/2 | 0 | 2/3 | 0 | 2/4 | 0 |
| play | 4/4 | 0 | 1/1 | 0 | 4/5 | 0 |
| qa | 1/1 | 0 | 1/1 | 0 | 1/2 | 3 |
| recommendation | not eligible | 0 | 1/2 | 0 | 0/1 | 2 |
| social | 2/2 | 0 | 1/1 | 0 | 2/3 | 0 |
| takeaway | 1/1 | 1 | 2/2 | 0 | 1/3 | 1 |
| transport | 2/4 | 0 | not eligible | 0 | 2/2 | 1 |
| weather | 0/3 | 0 | 3/3 | 0 | 0/3 | 0 |

## Secondary timing

First admitted input: 52.728s. All-input mean: 35.584s; nonfirst mean: 35.411s; p95: 52.462s. Batch wall/input: 8.947s is amortized throughput, not input latency. Mean pre-admission wait: 419.848s, reported separately. First/nonfirst grouping is not proof of cold/warm cache state.

| Role | Visits | Mean client s | Mean prefill s | Mean decode s | Reused input fraction |
| --- | ---: | ---: | ---: | ---: | ---: |
| perception | 100 | 6.853 | 0.671 | 5.898 | 0.6310 |
| planner | 178 | 0.990 | 0.410 | 0.267 | 0.9517 |
| reviewer | 178 | 8.871 | 0.455 | 8.192 | 0.9439 |
| solver | 178 | 4.584 | 2.024 | 2.162 | 0.6263 |

The full Reviewer family must independently qualify and its exact root READ must be signed before contrasts, local selection or learning. Preserve the active worker, templates, knowledge, data, official scorer, resource policy and peer-module isolation.

## Independent descriptive audit

GPT-6 Astra Ultra independently checked this original aggregate member report, its stage denominators, missingness, scenario totals and timing. The descriptive note required no factual correction. Raw model revision (one entity repair and one harm) remains distinct from final-delivery conditional repair and deterministic postprocessing. This audit authorizes no sibling contrast, adoption or learner export.
