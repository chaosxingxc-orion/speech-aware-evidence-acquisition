# Reviewer local K4 update1: complete fixed-N100 analysis

Refresh stamp: 2026-10-08T19:43:08.710740+00:00.

All six original members completed independently with verified seals, exactly one successful official complete score each, zero failed score jobs, and the exact countersigned family READ. The original offline reader exited zero. The original driver and Windows wrapper exited zero, and the experiment-scoped monitor was deleted. No scoring was replayed.

Root retains the unchanged full-seed parent. Candidate-2 is an exploratory tie-break choice because its false-alarm rate is lower; its raw entity net repair is zero, the same as both controls and candidate-3. No candidate improves the registered primary. This is one completed local update. The prospectively registered two-update review rule remains in force.

| Member | Raw entity repair / harm / unknown | Primary net / fixed N | False alarms | Error detection | Official F1 | Intent | Non-first mean seconds |
| --- | --- | --- | --- | --- | --- | --- | --- |
| control | 0 / 0 / 19 | 0/100 | 11/37 (unknown 1) | 23/42 (unknown 1) | 0.614669 | 0.83 | 33.513 |
| control-aa | 0 / 0 / 20 | 0/100 | 17/39 (unknown 1) | 27/41 (unknown 0) | 0.607226 | 0.82 | 34.547 |
| candidate-1 | 1 / 3 / 20 | -2/100 | 15/42 (unknown 0) | 27/38 (unknown 0) | 0.620262 | 0.84 | 29.677 |
| candidate-2 | 0 / 0 / 16 | 0/100 | 3/42 (unknown 0) | 2/42 (unknown 0) | 0.631729 | 0.82 | 25.519 |
| candidate-3 | 0 / 0 / 20 | 0/100 | 17/41 (unknown 0) | 32/38 (unknown 1) | 0.609012 | 0.80 | 30.468 |
| candidate-4 | 0 / 1 / 18 | -1/100 | 15/45 (unknown 0) | 29/37 (unknown 0) | 0.624890 | 0.85 | 32.219 |

Raw entity correctness that cannot be parsed remains unknown and contributes zero to the registered fixed-N primary. Conditional detection and false-alarm rates use their known eligible denominators; these are reported separately, not substituted for the fixed-N primary. Complete Wilson intervals, missingness bounds, alarm precision, stage transitions, contacts and token totals remain in the aggregate JSON. Workflow completion is not task correctness or parse validity.

Candidate-3 detects many known errors (32/38) without positive raw entity net repair. Candidate-2 has fewer false alarms (3/42) but detects only 2/42 known errors. This indicates a detection-versus-actionability tradeoff, not a successful repair policy. Candidate-1 has one raw entity repair and three harms. Deterministic postprocessing adds 2, 5, 2 and 3 entity repairs for candidates 1 through 4 respectively; these are not model repair credit. Ordinary alarm-to-final repair statistics include a different endpoint and must not be substituted for the raw model measure.

Candidate-2 official F1 is 0.631729 versus control 0.614669 and A/A 0.607226. Its difference versus control is approximately +0.01706 with a paired 95% interval spanning zero. Every candidate-versus-control F1 interval spans zero. Neither the F1 point estimate nor shorter latency changes the registered primary. Raw-primary uncertainty is not inferred from F1 intervals. The system reran upstream roles; it does not claim identical upstream outputs or isolated causal Reviewer effects.

## Natural mixture and equal-stratum reporting

| Member | Natural F1 | Equal-stratum F1 | Natural intent | Equal-stratum intent | Completion | Model calls |
| --- | --- | --- | --- | --- | --- | --- |
| control | 0.614669 | 0.530894 | 0.830000 | 0.853814 | 1.00 | 595 |
| control-aa | 0.607226 | 0.541803 | 0.820000 | 0.839925 | 1.00 | 628 |
| candidate-1 | 0.620262 | 0.524747 | 0.840000 | 0.860758 | 1.00 | 613 |
| candidate-2 | 0.631729 | 0.565801 | 0.820000 | 0.834987 | 1.00 | 520 |
| candidate-3 | 0.609012 | 0.557954 | 0.800000 | 0.822884 | 1.00 | 583 |
| candidate-4 | 0.624890 | 0.550011 | 0.850000 | 0.867923 | 1.00 | 625 |

## Complete per-stratum table

All stratum values are descriptive; small strata do not establish subgroup benefit. Each cell is official F1 / intent accuracy.

| Stratum | N | control | control-aa | candidate-1 | candidate-2 | candidate-3 | candidate-4 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| alarm | 5 | 0.8421 / 0.8000 | 0.9000 / 0.8000 | 0.8421 / 0.8000 | 0.8235 / 0.6000 | 0.8421 / 0.8000 | 0.8421 / 0.8000 |
| audio | 9 | 0.5000 / 0.5556 | 0.5000 / 0.5556 | 0.4412 / 0.5556 | 0.5660 / 0.6667 | 0.6667 / 0.6667 | 0.4000 / 0.6667 |
| calendar | 8 | 0.5906 / 1.0000 | 0.5906 / 1.0000 | 0.6167 / 1.0000 | 0.6621 / 1.0000 | 0.6034 / 1.0000 | 0.5405 / 1.0000 |
| cooking | 7 | 0.5657 / 0.5714 | 0.5657 / 0.5714 | 0.5657 / 0.5714 | 0.5657 / 0.5714 | 0.6181 / 0.4286 | 0.6692 / 0.7143 |
| datetime | 4 | 0.5678 / 1.0000 | 0.5678 / 1.0000 | 0.5678 / 1.0000 | 0.6112 / 0.7500 | 0.4137 / 1.0000 | 0.5678 / 1.0000 |
| email | 3 | 0.0000 / 1.0000 | 0.0000 / 1.0000 | 0.0000 / 1.0000 | 0.0000 / 1.0000 | 0.0000 / 1.0000 | 0.0000 / 1.0000 |
| general | 8 | 0.0000 / 0.5000 | 0.2500 / 0.5000 | 0.3333 / 0.6250 | 0.2500 / 0.5000 | 0.2500 / 0.5000 | 0.2000 / 0.5000 |
| iot | 5 | 0.5000 / 1.0000 | 0.8000 / 1.0000 | 0.6076 / 1.0000 | 0.6667 / 1.0000 | 0.5714 / 1.0000 | 0.5000 / 1.0000 |
| lists | 8 | 0.5373 / 0.8750 | 0.6076 / 0.8750 | 0.6076 / 0.8750 | 0.6575 / 0.8750 | 0.7059 / 0.7500 | 0.6780 / 0.8750 |
| music | 5 | 0.0000 / 0.8000 | 0.0000 / 0.8000 | 0.0000 / 0.8000 | 0.0000 / 0.8000 | 0.0000 / 0.8000 | 0.0000 / 0.8000 |
| news | 5 | 0.9091 / 0.8000 | 0.8035 / 0.8000 | 0.8734 / 0.8000 | 0.9091 / 0.8000 | 0.9091 / 0.8000 | 0.8035 / 0.8000 |
| play | 5 | 0.5953 / 0.8000 | 0.4901 / 0.8000 | 0.5063 / 0.8000 | 0.4901 / 0.8000 | 0.4901 / 0.8000 | 0.4314 / 0.8000 |
| qa | 5 | 0.7542 / 1.0000 | 0.6979 / 1.0000 | 0.7334 / 1.0000 | 0.7542 / 1.0000 | 0.5243 / 0.6000 | 0.7003 / 1.0000 |
| recommendation | 4 | 0.7586 / 1.0000 | 0.5714 / 0.7500 | 0.6929 / 1.0000 | 0.7568 / 1.0000 | 0.8627 / 1.0000 | 0.7586 / 1.0000 |
| social | 3 | 0.5000 / 0.6667 | 0.5000 / 0.6667 | 0.0000 / 0.6667 | 0.5000 / 0.6667 | 0.6667 / 0.6667 | 0.6667 / 0.6667 |
| takeaway | 5 | 0.7170 / 1.0000 | 0.6015 / 1.0000 | 0.7724 / 1.0000 | 0.7724 / 1.0000 | 0.7724 / 1.0000 | 0.6202 / 1.0000 |
| transport | 5 | 0.4491 / 1.0000 | 0.4491 / 1.0000 | 0.5158 / 1.0000 | 0.4298 / 1.0000 | 0.3775 / 1.0000 | 0.6648 / 1.0000 |
| weather | 6 | 0.7692 / 1.0000 | 0.8571 / 1.0000 | 0.7692 / 1.0000 | 0.7692 / 1.0000 | 0.7692 / 1.0000 | 0.8571 / 1.0000 |

## Next bounded local work

Prepare one fresh Reviewer-only opportunity with four jointly designed templates, the unchanged parent and same N100 roster. Focus on whether a short, specific discrepancy and permitted correction can induce useful raw entity changes without damaging correct drafts. Preserve the existing response schema and other roles, knowledge, tools, sampling and scoring. The learner receives four complete own-module aggregate/template records and separately labelled controls only under a new exact projection registration. No raw cases, source inventories, Solver outcomes or feedback from milestone tests enter that proposal. No automatic scaling or system adoption follows this report.

The independent Solver opportunity3 already returned four valid templates and compiled them without changing non-Solver fields. Its canonical CPU preparation is separate from this completed Reviewer family. Keep GPU campaigns serial and CPU preparation/analysis parallel. The broad system optimization and cross-carrier goal remains active and incomplete; return to the human before 8x400.
