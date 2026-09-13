# SLURP distinct candidate commitment: conditional diagnostics

Status: descriptive decomposition of the sealed comparison. Preserve the primary verdict: overall SLU remains inconclusive; the intent component has a positive paired contrast. This report does not introduce a new gate or authorize a new model contact.

## Sources and interpretation

- Shared diagnostic artifact: /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/analysis/SAEA-SLURP-DISTINCT-COMMITMENT-PAIRED-ANALYSIS-V1/conditional-diagnostics-v1.json; SHA-256 9d92ca29f9ae733dbf827979f68e3103f0f9c01f6e3a79d77223f24f1ded83a2.
- Runner code: 33d8db2f, isolated WSL worktree slurp-distinct-analysis-root-binding-v1.
- Entry: python -m speech_aware_evidence_acquisition.analysis.slurp_topn_diagnostics_cli, with configs/analysis/slurp-distinct-commitment-diagnostics-v1.json.
- Read authority: 2026-09-13-slurp-distinct-commitment-read-release-v1.json. The source remains a verified derivation of the ABORTED original source attempt.
- New model, encoder, tokenizer and scorer contacts: zero. Reuse the complete official score receipts.
- Retain actual ordered candidate sets of widths one, two and three; do not pad, relabel width as confidence, or treat coverage as realized gain.
- Entity exactness uses official exact-match FP=0 and FN=0, including empty/empty entities. It is a diagnostic exact-set property, not the official pooled SLU micro F1.
- The existing aggregate attempt fields inspect delivered text. Do not interpret a zero there as zero raw out-of-shortlist proposals. A separately source-verified delivery-flag supplement is pending; this does not affect the counts below.

## Primary NEW500 decomposition

For the closed-joint branch, the following categories are disjoint and exhaust all 500 rows:

| Location | Count | Interpretation |
|---|---:|---|
| Gold intent absent from actual candidates | 50 | A closed candidate selector cannot recover these rows |
| Gold present, final intent not correct | 53 | Selection or delivery remains unresolved despite candidate coverage |
| Final intent correct, entity set not exact | 236 | Correct intent alone does not close entity extraction |
| Final intent correct, entity set exact | 161 | Joint exact success in this descriptive partition |

Gold inclusion is 450/500 (90.0%); closed-joint selects correctly on 397/450 covered rows (88.22%). Source rank one is correct on 389/500 rows. Against that source, joint rescues 17 and harms 9, a net 8; these are not the paired hard-versus-joint 20 saves and 6 harms. Hard-first ends at 383/500 after its own delivery losses.

The candidate list exposes a useful selection opportunity. It does not eliminate cascade errors: 50 rows are outside the set, and 53 covered rows still fail final intent selection or delivery. Nor does a selected correct intent establish slot quality.

## Population and candidate-width tables

### NEW500

| Measure | Source / hard-first | Closed-joint |
|---|---:|---:|
| Source rank-one / candidate coverage | 389/500 | 450/500 |
| Delivered correct intent | 383 | 397 |
| Candidate present but not selected | 67 | 53 |
| Intent correct and entity exact | 151 | 161 |
| Intent correct and entity inexact | 232 | 236 |
| Source-relative rescues / harms | 0 / 6 | 17 / 9 |
| Refused deliveries | 7 | 5 |

| Actual width | n | Gold included | Hard correct | Joint correct | Joint intent correct, entity inexact |
|---:|---:|---:|---:|---:|---:|
| 1 | 115 | 105 | 102 | 104 | 71 |
| 2 | 60 | 53 | 43 | 47 | 29 |
| 3 | 325 | 292 | 238 | 246 | 136 |

### NEW500 scenario decomposition

| Scenario | n | Gold included | Hard correct | Joint correct | Joint intent and entities exact | Joint intent correct, entities inexact |
|---|---:|---:|---:|---:|---:|---:|
| alarm | 30 | 29 | 27 | 27 | 11 | 16 |
| audio | 2 | 2 | 1 | 1 | 1 | 0 |
| calendar | 33 | 30 | 23 | 25 | 3 | 22 |
| cooking | 9 | 9 | 3 | 5 | 4 | 1 |
| datetime | 33 | 33 | 31 | 30 | 11 | 19 |
| email | 33 | 30 | 19 | 23 | 10 | 13 |
| general | 33 | 22 | 12 | 13 | 10 | 3 |
| iot | 33 | 33 | 30 | 31 | 17 | 14 |
| lists | 32 | 31 | 26 | 29 | 16 | 13 |
| music | 23 | 20 | 18 | 18 | 12 | 6 |
| news | 32 | 29 | 25 | 27 | 9 | 18 |
| play | 32 | 28 | 21 | 20 | 8 | 12 |
| qa | 32 | 28 | 26 | 27 | 18 | 9 |
| recommendation | 32 | 29 | 27 | 27 | 12 | 15 |
| social | 33 | 24 | 23 | 24 | 4 | 20 |
| takeaway | 12 | 11 | 10 | 10 | 2 | 8 |
| transport | 33 | 31 | 30 | 30 | 6 | 24 |
| weather | 33 | 31 | 31 | 30 | 7 | 23 |

### OLD500

| Measure | Source / hard-first | Closed-joint |
|---|---:|---:|
| Source rank-one / candidate coverage | 364/500 | 432/500 |
| Delivered correct intent | 354 | 372 |
| Candidate present but not selected | 78 | 60 |
| Intent correct and entity exact | 150 | 160 |
| Intent correct and entity inexact | 204 | 212 |
| Source-relative rescues / harms | 0 / 10 | 24 / 16 |
| Refused deliveries | 11 | 10 |

| Actual width | n | Gold included | Hard correct | Joint correct | Joint intent correct, entity inexact |
|---:|---:|---:|---:|---:|---:|
| 1 | 100 | 92 | 89 | 90 | 64 |
| 2 | 58 | 53 | 36 | 42 | 21 |
| 3 | 342 | 287 | 229 | 240 | 127 |

### OLD500 scenario decomposition

| Scenario | n | Gold included | Hard correct | Joint correct | Joint intent and entities exact | Joint intent correct, entities inexact |
|---|---:|---:|---:|---:|---:|---:|
| alarm | 28 | 25 | 25 | 25 | 9 | 16 |
| audio | 28 | 23 | 21 | 23 | 15 | 8 |
| calendar | 28 | 25 | 23 | 23 | 9 | 14 |
| cooking | 28 | 24 | 9 | 16 | 12 | 4 |
| datetime | 28 | 26 | 24 | 23 | 10 | 13 |
| email | 28 | 26 | 23 | 23 | 6 | 17 |
| general | 28 | 14 | 6 | 8 | 6 | 2 |
| iot | 28 | 25 | 22 | 24 | 15 | 9 |
| lists | 28 | 27 | 23 | 26 | 14 | 12 |
| music | 28 | 21 | 17 | 16 | 14 | 2 |
| news | 28 | 22 | 21 | 20 | 8 | 12 |
| play | 28 | 23 | 13 | 13 | 11 | 2 |
| qa | 28 | 26 | 19 | 21 | 11 | 10 |
| recommendation | 28 | 24 | 20 | 20 | 6 | 14 |
| social | 27 | 25 | 21 | 21 | 4 | 17 |
| takeaway | 27 | 24 | 20 | 21 | 5 | 16 |
| transport | 27 | 27 | 23 | 24 | 4 | 20 |
| weather | 27 | 25 | 24 | 25 | 1 | 24 |

### DEV1000

| Measure | Source / hard-first | Closed-joint |
|---|---:|---:|
| Source rank-one / candidate coverage | 753/1000 | 882/1000 |
| Delivered correct intent | 737 | 769 |
| Candidate present but not selected | 145 | 113 |
| Intent correct and entity exact | 301 | 321 |
| Intent correct and entity inexact | 436 | 448 |
| Source-relative rescues / harms | 0 / 16 | 41 / 25 |
| Refused deliveries | 18 | 15 |

| Actual width | n | Gold included | Hard correct | Joint correct | Joint intent correct, entity inexact |
|---:|---:|---:|---:|---:|---:|
| 1 | 215 | 197 | 191 | 194 | 135 |
| 2 | 118 | 106 | 79 | 89 | 50 |
| 3 | 667 | 579 | 467 | 486 | 263 |

### DEV1000 scenario decomposition

| Scenario | n | Gold included | Hard correct | Joint correct | Joint intent and entities exact | Joint intent correct, entities inexact |
|---|---:|---:|---:|---:|---:|---:|
| alarm | 58 | 54 | 52 | 52 | 20 | 32 |
| audio | 30 | 25 | 22 | 24 | 16 | 8 |
| calendar | 61 | 55 | 46 | 48 | 12 | 36 |
| cooking | 37 | 33 | 12 | 21 | 16 | 5 |
| datetime | 61 | 59 | 55 | 53 | 21 | 32 |
| email | 61 | 56 | 42 | 46 | 16 | 30 |
| general | 61 | 36 | 18 | 21 | 16 | 5 |
| iot | 61 | 58 | 52 | 55 | 32 | 23 |
| lists | 60 | 58 | 49 | 55 | 30 | 25 |
| music | 51 | 41 | 35 | 34 | 26 | 8 |
| news | 60 | 51 | 46 | 47 | 17 | 30 |
| play | 60 | 51 | 34 | 33 | 19 | 14 |
| qa | 60 | 54 | 45 | 48 | 29 | 19 |
| recommendation | 60 | 53 | 47 | 47 | 18 | 29 |
| social | 60 | 49 | 44 | 45 | 8 | 37 |
| takeaway | 39 | 35 | 30 | 31 | 7 | 24 |
| transport | 60 | 58 | 53 | 54 | 10 | 44 |
| weather | 60 | 56 | 55 | 55 | 8 | 47 |

## Consequences for the next system

Use the framework to orchestrate Perception, Solver, Reviewer and Planner. Retain candidate coverage as the first-node diagnostic; let Solver select an intent jointly with its arguments. Keep the analytical tool surface in Reviewer and Planner.

Prioritize task-specific semantic value quality as a testable hypothesis. The existing compact catalog records candidate IDs and observed slot-type counts/shares; those statistics do not explain semantic roles, evidence spans, ambiguity or extraction rules. This is a verified representation limitation, not proof that missing explanations caused every slot error. Distinguish that limitation from acoustic recognition errors and output/delivery failures in future registered comparisons.

Construct intent boundaries and slot explanations independently from the already governed TRAIN pool. Do not turn exposed DEV failures into authored knowledge or memory rules. First register source authoring, then freeze and validate the two stores.

Finish the native framework-to-speech/tool-evidence adapter with a bounded engineering proof before registering a task-quality comparison. A graph-only or synthetic tool test cannot establish full agentic system gain. Keep the existing official scores and primary verdict unchanged.
