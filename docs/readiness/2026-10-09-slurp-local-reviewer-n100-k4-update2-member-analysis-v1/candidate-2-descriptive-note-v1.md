# Reviewer update2 candidate-2: independently qualified descriptive read

Root read checked at 2026-10-09T04:17:17.307989+00:00. The original member independently finalized 100 inputs with a verified seal, one successful complete official score and zero failed jobs. The exact member READ is separately signed; both original reader layers exited zero. No scoring, model or tokenizer contact was repeated. This is a single-member description: no sibling or historical contrast, selection, policy change or learner export.

Source report: `/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/analysis/local-reviewer-n100-k4-update2-candidate-2-descriptive-v1/report.json`; SHA-256 `58cc13783ce2f9907fd68b47c444bc455c7af5088f0972ecc776c7a379daaf05`.

Official pooled SLU-F1: 0.6076142343; intent: 82/100; reliable completion: 100/100. Equal-scenario descriptive F1: 0.5462088289. Contacts: 529 model and 0 tool.

## Process statistics

| Metric | Numerator / observed denominator | Eligible | Unknown | Observed rate | Wilson 95% interval | Missing bounds |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| draft_entity_correct | 41/82 | 100 | 18 | 0.5000 | [0.3942, 0.6058] | [0.4100, 0.5900] |
| draft_full_correct | 34/100 | 100 | 0 | 0.3400 | [0.2546, 0.4372] | [0.3400, 0.3400] |
| draft_parsed | 82/100 | 100 | 0 | 0.8200 | [0.7333, 0.8830] | [0.8200, 0.8200] |
| empty_gold_false_fill | 12/34 | 34 | 0 | 0.3529 | [0.2149, 0.5209] | [0.3529, 0.3529] |
| entity_harm_given_revision | 1/13 | 13 | 0 | 0.0769 | [0.0137, 0.3331] | [0.0769, 0.0769] |
| entity_repair_after_alarm | 1/7 | 7 | 0 | 0.1429 | [0.0257, 0.5131] | [0.1429, 0.1429] |
| entity_repair_given_revision | 1/15 | 15 | 0 | 0.0667 | [0.0119, 0.2982] | [0.0667, 0.0667] |
| final_entity_correct | 46/97 | 100 | 3 | 0.4742 | [0.3777, 0.5727] | [0.4600, 0.4900] |
| final_full_correct | 38/100 | 100 | 0 | 0.3800 | [0.2910, 0.4779] | [0.3800, 0.3800] |
| final_parsed | 97/100 | 100 | 0 | 0.9700 | [0.9155, 0.9897] | [0.9700, 0.9700] |
| full_harm_given_revision | 1/10 | 10 | 0 | 0.1000 | [0.0179, 0.4042] | [0.1000, 0.1000] |
| full_repair_given_revision | 4/33 | 33 | 0 | 0.1212 | [0.0482, 0.2733] | [0.1212, 0.1212] |
| handoff_visibility_given_valid_review | 99/99 | 99 | 0 | 1.0000 | [0.9626, 1.0000] | [1.0000, 1.0000] |
| review_alarm_precision | 7/11 | 20 | 9 | 0.6364 | [0.3538, 0.8483] | [0.3500, 0.8000] |
| review_error_detection | 7/41 | 41 | 0 | 0.1707 | [0.0853, 0.3126] | [0.1707, 0.1707] |
| review_false_alarm | 4/41 | 41 | 0 | 0.0976 | [0.0386, 0.2255] | [0.0976, 0.0976] |
| review_miss | 34/41 | 41 | 0 | 0.8293 | [0.6874, 0.9147] | [0.8293, 0.8293] |
| review_valid | 99/100 | 100 | 0 | 0.9900 | [0.9455, 0.9982] | [0.9900, 0.9900] |
| revision_after_alarm | 15/20 | 20 | 0 | 0.7500 | [0.5313, 0.8881] | [0.7500, 0.7500] |
| revision_of_correct_draft | 10/34 | 34 | 0 | 0.2941 | [0.1683, 0.4617] | [0.2941, 0.2941] |

Observed-case rates retain their own denominator; unknown states are not silently treated as correct. The fixed-N local primary below uses every input. The review indicators describe agreement with offline correctness, not the semantic validity of criticism or causal node contribution.

## Raw model revision and deterministic delivery

| Stage | Target | Wrong to correct | Correct to wrong | Net repairs | Stable correct | Stable wrong | Unknown |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| model_revision | entity | 1 | 1 | 0 | 40 | 40 | 18 |
| model_revision | full | 4 | 1 | 3 | 33 | 62 | 0 |
| postprocessing | entity | 2 | 0 | 2 | 44 | 51 | 3 |
| postprocessing | full | 1 | 0 | 1 | 37 | 62 | 0 |

The registered raw entity model-revision primary is 0/100: 1 known repairs minus 1 known harms. The 18 unknown transitions contribute zero to this fixed-N primary and remain explicit. The raw endpoint is first raw Solver answer to selected raw Solver answer; the first answer is after any within-visit tools.

The selected raw answer to final delivery is a separate deterministic postprocessing stage. Final-delivery conditional repair/harm rates and raw model-revision transitions use different endpoints and must not be substituted for each other. An initial unknown state becoming a known correct state is not a verified wrong-to-correct model repair.

## Knowledge availability boundary

- candidate_coverage_given_card: 92/98, unknown 0.
- gold_intent_card_in_initial_request: 98/100, unknown 0.
- gold_intent_in_initial_candidates: 92/100, unknown 0.

These measures separately report own-intent card presence in the actual initial Perception request and gold-intent coverage in the initial candidate set. They do not prove semantic consumption, raw retrieval-pool recall, or entity-type/value support; no gold is added to runtime.

## Per-scenario description

| Scenario | N | Official F1 | Intent | Raw entity correct | Raw entity unknown | Final entity correct / observed | Final entity unknown | Empty false fill / eligible |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| alarm | 5 | 0.8421 | 1.0000 | 1 | 2 | 2/5 | 0 | not eligible |
| audio | 9 | 0.4000 | 0.5556 | 7 | 2 | 7/9 | 0 | 1/8 |
| calendar | 8 | 0.6358 | 1.0000 | 2 | 0 | 2/8 | 0 | 1/2 |
| cooking | 7 | 0.4565 | 0.4286 | 2 | 3 | 2/6 | 1 | 1/1 |
| datetime | 4 | 0.5302 | 1.0000 | 1 | 2 | 1/4 | 0 | 1/1 |
| email | 3 | 0.0000 | 1.0000 | 1 | 0 | 1/3 | 0 | 2/3 |
| general | 8 | 0.2222 | 0.6250 | 3 | 1 | 3/8 | 0 | 4/6 |
| iot | 5 | 0.8000 | 1.0000 | 1 | 2 | 4/5 | 0 | 1/3 |
| lists | 8 | 0.5647 | 0.8750 | 4 | 2 | 4/8 | 0 | 0/3 |
| music | 5 | 0.0000 | 0.8000 | 3 | 0 | 3/5 | 0 | 1/4 |
| news | 5 | 0.9091 | 0.8000 | 3 | 0 | 4/5 | 0 | 0/1 |
| play | 5 | 0.5221 | 0.6000 | 1 | 1 | 1/4 | 1 | not eligible |
| qa | 5 | 0.6525 | 0.8000 | 2 | 2 | 2/4 | 1 | not eligible |
| recommendation | 4 | 0.8187 | 1.0000 | 3 | 0 | 3/4 | 0 | 0/1 |
| social | 3 | 0.5895 | 0.6667 | 2 | 0 | 2/3 | 0 | 0/1 |
| takeaway | 5 | 0.7724 | 1.0000 | 2 | 0 | 2/5 | 0 | not eligible |
| transport | 5 | 0.4491 | 1.0000 | 0 | 1 | 0/5 | 0 | not eligible |
| weather | 6 | 0.6667 | 1.0000 | 3 | 0 | 3/6 | 0 | not eligible |

Small strata are descriptive and do not establish stratum-specific superiority.

## Per-scenario review indicators

| Scenario | Error detection | Unknown detection | False alarm | Unknown false alarm | Alarm precision | Unknown alarm correctness |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| alarm | 0/2 | 0 | 0/1 | 0 | not eligible | 0 |
| audio | not eligible | 0 | 1/7 | 0 | 0/1 | 1 |
| calendar | 0/6 | 0 | 0/2 | 0 | not eligible | 0 |
| cooking | 0/2 | 0 | 0/2 | 0 | unavailable (0 observed; 2 eligible) | 2 |
| datetime | 0/1 | 0 | 0/1 | 0 | unavailable (0 observed; 2 eligible) | 2 |
| email | 1/2 | 0 | 0/1 | 0 | 1/1 | 0 |
| general | 1/4 | 0 | 0/3 | 0 | 1/1 | 1 |
| iot | 1/2 | 0 | 1/1 | 0 | 1/2 | 0 |
| lists | 0/2 | 0 | 0/4 | 0 | not eligible | 0 |
| music | 1/2 | 0 | 0/3 | 0 | 1/1 | 0 |
| news | 0/2 | 0 | 0/3 | 0 | not eligible | 0 |
| play | 0/3 | 0 | 0/1 | 0 | unavailable (0 observed; 1 eligible) | 1 |
| qa | 1/1 | 0 | 0/2 | 0 | 1/1 | 2 |
| recommendation | 1/1 | 0 | 0/3 | 0 | 1/1 | 0 |
| social | 0/1 | 0 | 0/2 | 0 | not eligible | 0 |
| takeaway | 0/3 | 0 | 1/2 | 0 | 0/1 | 0 |
| transport | 1/4 | 0 | not eligible | 0 | 1/1 | 0 |
| weather | 0/3 | 0 | 1/3 | 0 | 0/1 | 0 |

## Secondary timing

First admitted input: 44.954s. All-input mean: 27.161s; nonfirst mean: 26.981s; p95: 44.954s. Batch wall/input: 6.854s is amortized throughput, not input latency. Mean pre-admission wait: 318.714s, reported separately. First/nonfirst grouping is not proof of cold/warm cache state.

| Role | Visits | Mean client s | Mean prefill s | Mean decode s | Reused input fraction |
| --- | ---: | ---: | ---: | ---: | ---: |
| perception | 100 | 8.037 | 0.658 | 7.185 | 0.6310 |
| planner | 143 | 1.056 | 0.442 | 0.274 | 0.9559 |
| reviewer | 143 | 5.442 | 0.528 | 4.380 | 0.9420 |
| solver | 143 | 5.365 | 2.636 | 2.225 | 0.5294 |

The full Reviewer family must independently qualify and its exact root READ must be signed before contrasts, local selection or learning. Preserve the active worker, templates, knowledge, data, official scorer, resource policy and peer-module isolation.

Independent GPT-6 Astra Ultra audit matched the complete single-member aggregate, all eighteen strata, stage endpoints, fixed-N primary and timing. Workflow completion 100/100 does not establish successful parsing: final parsing is 97/100. The three final unknown entity states occur in cooking (2/6 observed correct, 7 eligible), play (1/4, 5 eligible), and qa (2/4, 5 eligible). The audit made no peer comparison, selection or learning export.
