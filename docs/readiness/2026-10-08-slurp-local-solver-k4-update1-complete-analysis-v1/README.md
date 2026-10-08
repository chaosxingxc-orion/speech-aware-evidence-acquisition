# Solver local K4 update1: complete root interpretation

Root read: 2026-10-08T18:02:14.808647+00:00. Owner227. The same100-input development roster; four candidates plus control/A/A. All600 original trajectories independently finalized and sealed; each member has one successful official score and no failed jobs. All original scores are reused, never replayed.

Candidate1 is the exploratory proposal with the highest registered raw entity-correct point estimate. The unchanged control remains the fixed parent. A/A ties candidate1 on the primary and exceeds its raw full-answer correctness, so superiority over the unchanged version remains unresolved. This does not introduce an A/A veto or change the prospective local endpoint.

| Member | Raw entity correct /100 | Raw full correct /100 | Final empty false fill /34 | Final nonempty exact /66 | Official SLU-F1 | Intent | Completion | Nonfirst mean s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| control | 47 | 43 | 9 | 24 | 0.5751 | 0.85 | 1.00 | 17.45 |
| control-aa | 49 | 43 | 7 | 24 | 0.6016 | 0.86 | 1.00 | 17.90 |
| candidate-1 | 49 | 42 | 3 | 20 | 0.5485 | 0.85 | 1.00 | 17.64 |
| candidate-2 | 47 | 42 | 8 | 25 | 0.5988 | 0.87 | 1.00 | 17.97 |
| candidate-3 | 47 | 41 | 10 | 26 | 0.6082 | 0.85 | 1.00 | 18.10 |
| candidate-4 | 48 | 41 | 9 | 25 | 0.5973 | 0.84 | 1.00 | 18.05 |

The empty false-fill metric uses final parsed answers. Every empty-gold final answer parsed. Candidate1 has one unparsed nonempty draft/final answer; other members parse completely. Invalid or missing raw outputs count as incorrect in the registered primary. Final nonempty known exact-correct count is derived by subtracting known correct empty cases from known final exact entity correctness, retaining its missing case as non-correct over all66 cases. It is not a raw-first-answer metric. Candidate1 improves final empty behavior while losing nonempty final exact cases; official F1 also declines. Candidate3 has the highest F1 point estimate, but does not improve the registered raw-entity primary.

Candidate1 minus control official F1: -2.66 percentage points,95% interval[-9.26,+3.72]. Candidate3 minus control:+3.31 points, interval[-0.74,+7.40]. Same-request A/A minus control:+2.64 points. These F1 intervals do not establish a raw-primary confidence interval. No stable improvement, formal system adoption, generalization or learning advantage is established.

Each member used200 model contacts and no tool calls. Timing remains a secondary engineering measure. Runtime sampling stays temperature0/fixed seed; realized A/A variability is reported.

## Per-scenario official SLU-F1

| Scenario | N | control | control-aa | candidate-1 | candidate-2 | candidate-3 | candidate-4 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| alarm | 5 | 0.7778 | 0.7816 | 0.7059 | 0.8421 | 0.8421 | 0.9000 |
| audio | 9 | 0.6667 | 1.0000 | 1.0000 | 1.0000 | 0.6667 | 1.0000 |
| calendar | 8 | 0.5906 | 0.5906 | 0.6487 | 0.5906 | 0.5906 | 0.5814 |
| cooking | 7 | 0.4242 | 0.5657 | 0.5657 | 0.5657 | 0.5657 | 0.5657 |
| datetime | 4 | 0.5678 | 0.5678 | 0.5455 | 0.6667 | 0.5678 | 0.6667 |
| email | 3 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| general | 8 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| iot | 5 | 0.5000 | 0.8000 | 0.5000 | 0.5000 | 0.4000 | 0.4000 |
| lists | 8 | 0.6076 | 0.5647 | 0.5890 | 0.6575 | 0.6575 | 0.6575 |
| music | 5 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| news | 5 | 0.9091 | 0.8734 | 0.7656 | 0.9091 | 0.8000 | 0.7656 |
| play | 5 | 0.3240 | 0.2837 | 0.2778 | 0.4278 | 0.3974 | 0.3390 |
| qa | 5 | 0.7542 | 0.7542 | 0.6979 | 0.6979 | 0.7542 | 0.7542 |
| recommendation | 4 | 0.7586 | 0.7586 | 0.7586 | 0.8461 | 0.7395 | 0.8461 |
| social | 3 | 0.5138 | 0.5895 | 0.5895 | 0.5138 | 0.5895 | 0.5895 |
| takeaway | 5 | 0.7007 | 0.7724 | 0.5153 | 0.6051 | 0.7724 | 0.7257 |
| transport | 5 | 0.4298 | 0.4298 | 0.2076 | 0.3762 | 0.4491 | 0.3762 |
| weather | 6 | 0.7692 | 0.7692 | 0.5455 | 0.6667 | 0.7692 | 0.5455 |

## Equal-scenario summary

| Member | Macro F1 | Macro intent | Macro completion |
| --- | ---: | ---: | ---: |
| control | 0.5163 | 0.8711 | 1.0000 |
| control-aa | 0.5612 | 0.8854 | 1.0000 |
| candidate-1 | 0.4951 | 0.8669 | 1.0000 |
| candidate-2 | 0.5481 | 0.8934 | 1.0000 |
| candidate-3 | 0.5312 | 0.8719 | 1.0000 |
| candidate-4 | 0.5396 | 0.8600 | 1.0000 |

## Continuation

Reviewer original K4 N100 is running independently through the serial GPU task. It receives no Solver feedback or template changes. The Solver monitor was deleted at its original terminal; the Reviewer15minute monitor will be deleted at its original terminal. Preserve source b4086484 and all original controls/outputs.

The next Solver local update should address empty suppression versus real-entity coverage, using only a separately qualified and prospectively registered own aggregate projection. One update contains K candidate records; controls are reference records. No such learning export or new proposal has occurred in this record. Keep the fixed parent and all non-Solver material unchanged. A later combined check is still required; source isolation does not prove behavioral independence.

Exact evidence: `docs/receipts/continuation/2026-10-08-local-solver-k4-complete-reviewer-launched-v1.json` and `aggregate-summary-v1.json`. The full cross-carrier goal remains active and incomplete.
