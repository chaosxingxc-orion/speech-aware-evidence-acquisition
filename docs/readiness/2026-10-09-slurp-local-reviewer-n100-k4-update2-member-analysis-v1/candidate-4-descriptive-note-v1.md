# Reviewer update2 candidate-4: independently qualified descriptive read

Root read checked at 2026-10-09T04:47:17.770598+00:00. The original member independently finalized 100 inputs with a verified seal, one successful complete official score and zero failed jobs. The exact member READ is separately signed; both original reader layers exited zero. No scoring, model or tokenizer contact was repeated. This is a single-member description: no sibling or historical contrast, selection, policy change or learner export.

Source report: `/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/analysis/local-reviewer-n100-k4-update2-candidate-4-descriptive-v1/report.json`; SHA-256 `ea4c0fb994a82606faeb2d26bf3b75cacd8f408ccc4880905460a9031f28309b`.

Official pooled SLU-F1: 0.6255597763; intent: 85/100; reliable completion: 100/100. Equal-scenario descriptive F1: 0.5611341215. Contacts: 526 model and 0 tool.

## Process statistics

| Metric | Numerator / observed denominator | Eligible | Unknown | Observed rate | Wilson 95% interval | Missing bounds |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| draft_entity_correct | 42/86 | 100 | 14 | 0.4884 | [0.3855, 0.5922] | [0.4200, 0.5600] |
| draft_full_correct | 34/100 | 100 | 0 | 0.3400 | [0.2546, 0.4372] | [0.3400, 0.3400] |
| draft_parsed | 86/100 | 100 | 0 | 0.8600 | [0.7786, 0.9147] | [0.8600, 0.8600] |
| empty_gold_false_fill | 10/34 | 34 | 0 | 0.2941 | [0.1683, 0.4617] | [0.2941, 0.2941] |
| entity_harm_given_revision | 0/16 | 16 | 0 | 0.0000 | [0.0000, 0.1936] | [0.0000, 0.0000] |
| entity_repair_after_alarm | 0/1 | 1 | 0 | 0.0000 | [0.0000, 0.7935] | [0.0000, 0.0000] |
| entity_repair_given_revision | 1/12 | 12 | 0 | 0.0833 | [0.0149, 0.3539] | [0.0833, 0.0833] |
| final_entity_correct | 51/100 | 100 | 0 | 0.5100 | [0.4135, 0.6058] | [0.5100, 0.5100] |
| final_full_correct | 42/100 | 100 | 0 | 0.4200 | [0.3280, 0.5179] | [0.4200, 0.4200] |
| final_parsed | 100/100 | 100 | 0 | 1.0000 | [0.9630, 1.0000] | [1.0000, 1.0000] |
| full_harm_given_revision | 0/12 | 12 | 0 | 0.0000 | [0.0000, 0.2425] | [0.0000, 0.0000] |
| full_repair_given_revision | 8/30 | 30 | 0 | 0.2667 | [0.1418, 0.4445] | [0.2667, 0.2667] |
| handoff_visibility_given_valid_review | 100/100 | 100 | 0 | 1.0000 | [0.9630, 1.0000] | [1.0000, 1.0000] |
| review_alarm_precision | 1/4 | 4 | 0 | 0.2500 | [0.0456, 0.6994] | [0.2500, 0.2500] |
| review_error_detection | 1/44 | 44 | 0 | 0.0227 | [0.0040, 0.1181] | [0.0227, 0.0227] |
| review_false_alarm | 3/42 | 42 | 0 | 0.0714 | [0.0246, 0.1901] | [0.0714, 0.0714] |
| review_miss | 43/44 | 44 | 0 | 0.9773 | [0.8819, 0.9960] | [0.9773, 0.9773] |
| review_valid | 100/100 | 100 | 0 | 1.0000 | [0.9630, 1.0000] | [1.0000, 1.0000] |
| revision_after_alarm | 4/4 | 4 | 0 | 1.0000 | [0.5101, 1.0000] | [1.0000, 1.0000] |
| revision_of_correct_draft | 12/34 | 34 | 0 | 0.3529 | [0.2149, 0.5209] | [0.3529, 0.3529] |

Observed-case rates retain their own denominator; unknown states are not silently treated as correct. The fixed-N local primary below uses every input. The review indicators describe agreement with offline correctness, not the semantic validity of criticism or causal node contribution.

## Raw model revision and deterministic delivery

| Stage | Target | Wrong to correct | Correct to wrong | Net repairs | Stable correct | Stable wrong | Unknown |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| model_revision | entity | 0 | 0 | 0 | 42 | 44 | 14 |
| model_revision | full | 7 | 0 | 7 | 34 | 59 | 0 |
| postprocessing | entity | 2 | 0 | 2 | 49 | 49 | 0 |
| postprocessing | full | 1 | 0 | 1 | 41 | 58 | 0 |

The registered raw entity model-revision primary is 0/100: 0 known repairs minus 0 known harms. The 14 unknown transitions contribute zero to this fixed-N primary and remain explicit. The raw endpoint is first raw Solver answer to selected raw Solver answer; the first answer is after any within-visit tools.

The selected raw answer to final delivery is a separate deterministic postprocessing stage. Final-delivery conditional repair/harm rates and raw model-revision transitions use different endpoints and must not be substituted for each other. An initial unknown state becoming a known correct state is not a verified wrong-to-correct model repair.

## Knowledge availability boundary

- candidate_coverage_given_card: 93/98, unknown 0.
- gold_intent_card_in_initial_request: 98/100, unknown 0.
- gold_intent_in_initial_candidates: 93/100, unknown 0.

These measures separately report own-intent card presence in the actual initial Perception request and gold-intent coverage in the initial candidate set. They do not prove semantic consumption, raw retrieval-pool recall, or entity-type/value support; no gold is added to runtime.

## Per-scenario description

| Scenario | N | Official F1 | Intent | Raw entity correct | Raw entity unknown | Final entity correct / observed | Final entity unknown | Empty false fill / eligible |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| alarm | 5 | 0.9000 | 0.8000 | 2 | 0 | 3/5 | 0 | not eligible |
| audio | 9 | 0.7895 | 0.5556 | 8 | 1 | 8/9 | 0 | 0/8 |
| calendar | 8 | 0.6044 | 1.0000 | 3 | 0 | 3/8 | 0 | 0/2 |
| cooking | 7 | 0.6692 | 0.7143 | 2 | 3 | 3/7 | 0 | 1/1 |
| datetime | 4 | 0.5678 | 1.0000 | 2 | 0 | 2/4 | 0 | 0/1 |
| email | 3 | 0.0000 | 1.0000 | 0 | 0 | 0/3 | 0 | 3/3 |
| general | 8 | 0.2857 | 0.6250 | 4 | 1 | 4/8 | 0 | 3/6 |
| iot | 5 | 0.5000 | 1.0000 | 0 | 3 | 3/5 | 0 | 1/3 |
| lists | 8 | 0.4932 | 0.8750 | 4 | 0 | 4/8 | 0 | 0/3 |
| music | 5 | 0.0000 | 0.8000 | 3 | 0 | 3/5 | 0 | 1/4 |
| news | 5 | 0.9091 | 0.8000 | 3 | 0 | 4/5 | 0 | 0/1 |
| play | 5 | 0.4901 | 0.8000 | 1 | 1 | 1/5 | 0 | not eligible |
| qa | 5 | 0.7003 | 1.0000 | 1 | 2 | 3/5 | 0 | not eligible |
| recommendation | 4 | 0.7225 | 1.0000 | 3 | 0 | 3/4 | 0 | 0/1 |
| social | 3 | 0.5138 | 0.6667 | 1 | 0 | 1/3 | 0 | 1/1 |
| takeaway | 5 | 0.7724 | 1.0000 | 1 | 2 | 2/5 | 0 | not eligible |
| transport | 5 | 0.5158 | 1.0000 | 1 | 1 | 1/5 | 0 | not eligible |
| weather | 6 | 0.6667 | 1.0000 | 3 | 0 | 3/6 | 0 | not eligible |

Small strata are descriptive and do not establish stratum-specific superiority.

## Per-scenario review indicators

| Scenario | Error detection | Unknown detection | False alarm | Unknown false alarm | Alarm precision | Unknown alarm correctness |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| alarm | 0/3 | 0 | 0/2 | 0 | not eligible | 0 |
| audio | not eligible | 0 | 0/8 | 0 | not eligible | 0 |
| calendar | 0/5 | 0 | 0/3 | 0 | not eligible | 0 |
| cooking | 0/2 | 0 | 1/2 | 0 | 0/1 | 0 |
| datetime | 1/2 | 0 | 0/2 | 0 | 1/1 | 0 |
| email | 0/3 | 0 | not eligible | 0 | not eligible | 0 |
| general | 0/3 | 0 | 0/4 | 0 | not eligible | 0 |
| iot | 0/2 | 0 | not eligible | 0 | not eligible | 0 |
| lists | 0/4 | 0 | 0/4 | 0 | not eligible | 0 |
| music | 0/2 | 0 | 0/3 | 0 | not eligible | 0 |
| news | 0/2 | 0 | 0/3 | 0 | not eligible | 0 |
| play | 0/3 | 0 | 1/1 | 0 | 0/1 | 0 |
| qa | 0/2 | 0 | 0/1 | 0 | not eligible | 0 |
| recommendation | 0/1 | 0 | 0/3 | 0 | not eligible | 0 |
| social | 0/2 | 0 | 0/1 | 0 | not eligible | 0 |
| takeaway | 0/2 | 0 | 0/1 | 0 | not eligible | 0 |
| transport | 0/3 | 0 | 0/1 | 0 | not eligible | 0 |
| weather | 0/3 | 0 | 1/3 | 0 | 0/1 | 0 |

## Secondary timing

First admitted input: 44.034s. All-input mean: 26.458s; nonfirst mean: 26.281s; p95: 44.984s. Batch wall/input: 6.671s is amortized throughput, not input latency. Mean pre-admission wait: 310.452s, reported separately. First/nonfirst grouping is not proof of cold/warm cache state.

| Role | Visits | Mean client s | Mean prefill s | Mean decode s | Reused input fraction |
| --- | ---: | ---: | ---: | ---: | ---: |
| perception | 100 | 7.728 | 0.697 | 6.606 | 0.6310 |
| planner | 142 | 0.954 | 0.380 | 0.312 | 0.9571 |
| reviewer | 142 | 4.201 | 0.527 | 3.305 | 0.9404 |
| solver | 142 | 6.233 | 2.730 | 2.740 | 0.5296 |

The full Reviewer family must independently qualify and its exact root READ must be signed before contrasts, local selection or learning. Preserve the active worker, templates, knowledge, data, official scorer, resource policy and peer-module isolation.

## Independent descriptive audit

GPT-6 Astra Ultra independently verified the original report hash, every note table, stage denominators, missingness, all scenario sums and timing. No factual correction was required. Zero raw entity repairs and seven raw full-answer repairs are distinct outcomes; neither the highest pooled F1 point nor a low alarm rate changes the registered local primary. This descriptive audit itself activates no policy or learner export.
