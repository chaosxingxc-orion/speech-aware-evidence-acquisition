# Reviewer update2 control: independently qualified descriptive read

Root read completed and reviewed at 2026-10-09T03:52:26.193891+00:00. The original control independently FINALIZED100 inputs, with a verified seal, exactly one successful complete official score and zero failed jobs. Its exact descriptive READ was separately countersigned. The unchanged reader exited0; no score was replayed. This note contains no sibling or historical contrast, local selection or learner export.

Official pooled SLU-F1 is0.6208597782, intent83/100, and reliable completion100/100. Equal-scenario descriptive F1 is0.5895586574. The run used601 model contacts and zero tool calls.

## Process observations and denominators

| Metric | Numerator / observed denominator | Eligible | Unknown | Observed rate |
| --- | ---: | ---: | ---: | ---: |
| draft_entity_correct | 44/87 | 100 | 13 | 0.5057 |
| draft_full_correct | 38/100 | 100 | 0 | 0.3800 |
| draft_parsed | 87/100 | 100 | 0 | 0.8700 |
| empty_gold_false_fill | 12/34 | 34 | 0 | 0.3529 |
| entity_harm_given_revision | 0/26 | 26 | 0 | 0.0000 |
| entity_repair_after_alarm | 1/28 | 28 | 0 | 0.0357 |
| entity_repair_given_revision | 1/28 | 28 | 0 | 0.0357 |
| final_entity_correct | 51/100 | 100 | 0 | 0.5100 |
| final_full_correct | 43/100 | 100 | 0 | 0.4300 |
| final_parsed | 100/100 | 100 | 0 | 1.0000 |
| full_harm_given_revision | 0/22 | 22 | 0 | 0.0000 |
| full_repair_given_revision | 4/45 | 45 | 0 | 0.0889 |
| handoff_visibility_given_valid_review | 98/98 | 98 | 0 | 1.0000 |
| review_alarm_precision | 28/44 | 57 | 13 | 0.6364 |
| review_error_detection | 28/43 | 43 | 0 | 0.6512 |
| review_false_alarm | 16/42 | 44 | 2 | 0.3810 |
| review_miss | 15/43 | 43 | 0 | 0.3488 |
| review_valid | 98/100 | 100 | 0 | 0.9800 |
| revision_after_alarm | 57/57 | 57 | 0 | 1.0000 |
| revision_of_correct_draft | 22/38 | 38 | 0 | 0.5789 |

The first raw Solver answer parses in87/100 inputs. Entity correctness is44 known correct,43 known incorrect and13 unknown;44/87 is an observed-case ratio, not44/100 or proof that missing states are correct. First raw full-answer correctness is38/100 under its separate parsing convention. The original report preserves Wilson intervals and missing bounds.

The review detects28/43 known entity errors and misses15/43. Alarm precision is28/44 among known eligible states;57 inputs have an alarm, including13 unknown first-entity states. False alarms are16/42 observed among44 known-correct eligible drafts, with two review states unknown. Preserve16/44 to18/44 missing bounds; do not silently remove those two inputs. Valid review is98/100 and visible handoff is98/98 eligible valid reviews. All57 alarmed inputs undergo revision;22/38 initially full-correct inputs also undergo revision.

The registered raw entity model-revision net is0/100:0 known wrong-to-correct,0 known correct-to-wrong, and13 unknown entity transitions. Unknowns contribute zero to that fixed-N primary and remain reported. Raw full-answer model revision has3 repairs and0 harms. The final-delivery conditional entity repair metric of1/28 uses a different endpoint and cannot replace raw model-revision credit.

The selected raw entity state has48 known correct entries before deterministic postprocessing; postprocessing repairs3/52 and harms0/48, delivering51/100. Raw initial unknown states prevent interpreting the increase44 to48 as four proven model entity repairs. Full-answer postprocessing repairs2 and harms0, yielding43/100 final exact full answers. Final empty-gold false filling is12/34. All final answers parse, which does not erase the initial13 unknown entity states.

An own-intent card appears in the actual initial Perception request for98/100 inputs, and the candidate set contains the gold intent for93/100 (93/98 conditional on card presence). This measures card presence/candidate coverage, not semantic consumption, raw retrieval-pool recall or verified entity-type/value coverage. No gold content is supplied at runtime by this diagnostic.

## Per-scenario description

| Scenario | N | Official F1 | Intent | Raw entity correct | Raw entity unknown | Final entity correct | Empty false fill / eligible |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| alarm | 5 | 0.8421 | 0.8000 | 1 | 0 | 2 | 0/0 |
| audio | 9 | 1.0000 | 0.5556 | 8 | 1 | 9 | 0/8 |
| calendar | 8 | 0.6034 | 1.0000 | 3 | 0 | 3 | 0/2 |
| cooking | 7 | 0.5657 | 0.5714 | 2 | 3 | 3 | 1/1 |
| datetime | 4 | 0.5678 | 1.0000 | 2 | 1 | 2 | 0/1 |
| email | 3 | 0.0000 | 1.0000 | 0 | 0 | 0 | 3/3 |
| general | 8 | 0.2500 | 0.5000 | 3 | 1 | 3 | 4/6 |
| iot | 5 | 0.8000 | 1.0000 | 3 | 2 | 4 | 1/3 |
| lists | 8 | 0.6076 | 0.8750 | 4 | 2 | 5 | 0/3 |
| music | 5 | 0.0000 | 0.8000 | 2 | 0 | 2 | 2/4 |
| news | 5 | 0.9091 | 0.8000 | 2 | 1 | 4 | 0/1 |
| play | 5 | 0.4901 | 0.8000 | 1 | 0 | 1 | 0/0 |
| qa | 5 | 0.7003 | 1.0000 | 3 | 1 | 3 | 0/0 |
| recommendation | 4 | 0.7586 | 1.0000 | 3 | 0 | 3 | 0/1 |
| social | 3 | 0.5138 | 0.6667 | 1 | 0 | 1 | 1/1 |
| takeaway | 5 | 0.7724 | 1.0000 | 2 | 0 | 2 | 0/0 |
| transport | 5 | 0.4619 | 1.0000 | 1 | 1 | 1 | 0/0 |
| weather | 6 | 0.7692 | 1.0000 | 3 | 0 | 3 | 0/0 |

Each stratum contains3-9 inputs. These counts are descriptive and do not support stratum-specific superiority or causal node credit.

## Per-scenario review indicators

| Scenario | Error detection | False alarms, observed | Unknown false-alarm outcomes |
| --- | ---: | ---: | ---: |
| alarm | 2/4 | 0/1 | 0 |
| audio | not eligible | 1/8 | 0 |
| calendar | 4/5 | 1/3 | 0 |
| cooking | 1/2 | 2/2 | 0 |
| datetime | 1/1 | 1/2 | 0 |
| email | 3/3 | not eligible | 0 |
| general | 4/4 | 1/1 | 2 |
| iot | not eligible | 0/3 | 0 |
| lists | 2/2 | 0/4 | 0 |
| music | 2/3 | 1/2 | 0 |
| news | 2/2 | 1/2 | 0 |
| play | 3/4 | 0/1 | 0 |
| qa | 1/1 | 2/3 | 0 |
| recommendation | 1/1 | 2/3 | 0 |
| social | 0/2 | 1/1 | 0 |
| takeaway | 0/3 | 1/2 | 0 |
| transport | 1/3 | 1/1 | 0 |
| weather | 1/3 | 1/3 | 0 |

These rates describe agreement with offline correctness indicators, not the semantic validity of a criticism or a causal Reviewer contribution.

## Secondary timing

First admitted input:32.104s. All-input mean:33.894s; nonfirst mean:33.912s; p95:59.192s. Batch wall/input:8.507s is amortized throughput, not input latency. Pre-admission wait remains separate. First/nonfirst grouping is not proof of cold/warm cache state.

| Role | Visits | Mean client s | Mean prefill s | Mean decode s | Reused input fraction |
| --- | ---: | ---: | ---: | ---: | ---: |
| perception | 100 | 6.791 | 0.694 | 5.885 | 0.6280 |
| planner | 167 | 1.041 | 0.426 | 0.283 | 0.9507 |
| reviewer | 167 | 9.303 | 0.286 | 8.840 | 0.9693 |
| solver | 167 | 4.386 | 2.119 | 1.901 | 0.6030 |

The original independent Reviewer family remains in progress. Root may analyze other independently qualified completed members, but full-family comparison, candidate selection and learning feedback remain closed until every configured member and the exact family READ qualify. No policy, data, knowledge, scorer, active worker or resource policy changes follow this single-member note.

Independent GPT-6 Astra Ultra audit confirmed this descriptive reading and its missing-state/endpoint distinctions. The audit consumed only this authorized aggregate report and did not compare or export peer outcomes.
