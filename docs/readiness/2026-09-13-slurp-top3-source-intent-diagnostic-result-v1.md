# Current source intent accuracy and candidate headroom

Date: 2026-09-13. Status: completed owner-directed diagnostic; recommend retaining candidate alternatives for a matched joint-decision test. Do not promote a Top-1 lock or claim that a candidate-based system is already effective.

## Scope and preserved failure

The owner requested current intent accuracy before choosing the recovery design. The source-quality read was registered before loading references. This limited read supersedes the earlier quality hold only for source diagnosis. The 1,000-response common source remains ABORTED because 333 rows violate its fixed-three-unique contract. All raw entries, repeats, costs, original registration, and failure state remain unchanged. No production candidate projection, new source generation, or full successor flight has been admitted.

Measure the first raw proposed canonical intent and membership of the reference intent among all raw proposals. Repetition never adds coverage. These are measurements of this hypothesis-source prompt, not of a separately optimized Top-1 policy or the complete agentic system. The governed offline loader verified 8,690 devel recording records; only the pre-registered 1,000 IDs enter analysis. No references enter runtime, knowledge construction, or a model request.

## Primary and secondary results

| Population | Rows | Top-1 accuracy | Speaker CI90 | Candidate coverage | Speaker CI90 | Coverage headroom | Paired speaker CI90 |
|---|---:|---:|---|---:|---|---:|---|
| NEW500 | 500 | 77.80% (389) | [75.00, 80.64] | 90.00% (450) | [88.11, 91.86] | +12.20 pp (61) | [10.04, 14.40] |
| OLD500 | 500 | 72.80% (364) | [69.64, 76.00] | 86.40% (432) | [84.12, 88.63] | +13.60 pp (68) | [11.31, 15.93] |
| DEV1000 | 1000 | 75.30% (753) | [73.12, 77.56] | 88.20% (882) | [86.76, 89.62] | +12.90 pp (129) | [11.35, 14.39] |

NEW500 is the primary, historically exposed discovery population, not fresh holdout data. Resample whole speakers with the shared paired analysis function, 10,000 draws, seed 20260913, and 90% intervals. Reuse the same draws for the paired headroom statistic. Candidate coverage is an oracle ceiling for selection restricted to the available IDs; it is not achieved final intent or slot accuracy.

On NEW500, the first proposal is wrong on 111 rows. The correct intent remains among later proposals on 61 of those rows (54.95% of first-proposal errors), while 50 rows contain no correct candidate. Across all 1,000 rows, the corresponding counts are 247 errors, 129 potentially recoverable within the proposals (52.23%), and 118 absent candidates.

## Natural and equal-scenario weighting

| Population | Natural Top-1 | Equal-scenario Top-1 | Natural coverage | Equal-scenario coverage | Equal-scenario headroom |
|---|---:|---:|---:|---:|---:|
| NEW500 | 77.80% | 74.85% | 90.00% | 90.97% | 16.12 pp |
| OLD500 | 72.80% | 72.87% | 86.40% | 86.46% | 13.59 pp |
| DEV1000 | 75.30% | 74.36% | 88.20% | 88.07% | 13.71 pp |

Equal-scenario numbers are descriptive point estimates. NEW500 includes small scenario strata, including two audio rows and nine cooking rows; do not interpret the equal weighting as a separately powered result.

## Observed candidate width

| Population | Distinct IDs | Rows | Top-1 accuracy | Speaker CI90 | Candidate coverage | Remaining absent rows |
|---|---:|---:|---:|---|---:|---:|
| NEW500 | 1 | 115 | 91.30% | [87.10, 95.16] | 91.30% | 10 |
| NEW500 | 2 | 60 | 73.33% | [63.79, 82.35] | 88.33% | 7 |
| NEW500 | 3 | 325 | 73.85% | [69.91, 77.84] | 89.85% | 33 |
| DEV1000 | 1 | 215 | 91.63% | [88.78, 94.39] | 91.63% | 18 |
| DEV1000 | 2 | 118 | 67.80% | [61.34, 74.36] | 89.83% | 12 |
| DEV1000 | 3 | 667 | 71.36% | [68.38, 74.38] | 86.81% | 88 |

The one-distinct-ID subgroup is associated with higher accuracy in these observed responses, but still contains 10 errors among 115 NEW500 rows and 18 among 215 pooled rows. It is an output characteristic under a fixed-three prompt, not a calibrated confidence estimate, an intentional abstention, or a validated dynamic-width policy. Scenario composition and request difficulty may explain some association. Do not derive an automatic accept rule from these same outcomes.

## Scenario tables

### NEW500

| Scenario | Rows | Top-1 correct | Top-1 accuracy | Covered | Coverage | Potential recovery | Absent |
|---|---:|---:|---:|---:|---:|---:|---:|
| alarm | 30 | 27 | 90.00% | 29 | 96.67% | 2 | 1 |
| audio | 2 | 1 | 50.00% | 2 | 100.00% | 1 | 0 |
| calendar | 33 | 23 | 69.70% | 30 | 90.91% | 7 | 3 |
| cooking | 9 | 3 | 33.33% | 9 | 100.00% | 6 | 0 |
| datetime | 33 | 31 | 93.94% | 33 | 100.00% | 2 | 0 |
| email | 33 | 19 | 57.58% | 30 | 90.91% | 11 | 3 |
| general | 33 | 12 | 36.36% | 22 | 66.67% | 10 | 11 |
| iot | 33 | 30 | 90.91% | 33 | 100.00% | 3 | 0 |
| lists | 32 | 26 | 81.25% | 31 | 96.88% | 5 | 1 |
| music | 23 | 18 | 78.26% | 20 | 86.96% | 2 | 3 |
| news | 32 | 25 | 78.12% | 29 | 90.62% | 4 | 3 |
| play | 32 | 26 | 81.25% | 28 | 87.50% | 2 | 4 |
| qa | 32 | 26 | 81.25% | 28 | 87.50% | 2 | 4 |
| recommendation | 32 | 28 | 87.50% | 29 | 90.62% | 1 | 3 |
| social | 33 | 23 | 69.70% | 24 | 72.73% | 1 | 9 |
| takeaway | 12 | 10 | 83.33% | 11 | 91.67% | 1 | 1 |
| transport | 33 | 30 | 90.91% | 31 | 93.94% | 1 | 2 |
| weather | 33 | 31 | 93.94% | 31 | 93.94% | 0 | 2 |

### OLD500

| Scenario | Rows | Top-1 correct | Top-1 accuracy | Covered | Coverage | Potential recovery | Absent |
|---|---:|---:|---:|---:|---:|---:|---:|
| alarm | 28 | 25 | 89.29% | 25 | 89.29% | 0 | 3 |
| audio | 28 | 21 | 75.00% | 23 | 82.14% | 2 | 5 |
| calendar | 28 | 23 | 82.14% | 25 | 89.29% | 2 | 3 |
| cooking | 28 | 9 | 32.14% | 24 | 85.71% | 15 | 4 |
| datetime | 28 | 25 | 89.29% | 26 | 92.86% | 1 | 2 |
| email | 28 | 23 | 82.14% | 26 | 92.86% | 3 | 2 |
| general | 28 | 6 | 21.43% | 14 | 50.00% | 8 | 14 |
| iot | 28 | 22 | 78.57% | 25 | 89.29% | 3 | 3 |
| lists | 28 | 23 | 82.14% | 27 | 96.43% | 4 | 1 |
| music | 28 | 17 | 60.71% | 21 | 75.00% | 4 | 7 |
| news | 28 | 21 | 75.00% | 22 | 78.57% | 1 | 6 |
| play | 28 | 21 | 75.00% | 23 | 82.14% | 2 | 5 |
| qa | 28 | 19 | 67.86% | 26 | 92.86% | 7 | 2 |
| recommendation | 28 | 21 | 75.00% | 24 | 85.71% | 3 | 4 |
| social | 27 | 21 | 77.78% | 25 | 92.59% | 4 | 2 |
| takeaway | 27 | 20 | 74.07% | 24 | 88.89% | 4 | 3 |
| transport | 27 | 23 | 85.19% | 27 | 100.00% | 4 | 0 |
| weather | 27 | 24 | 88.89% | 25 | 92.59% | 1 | 2 |

### DEV1000

| Scenario | Rows | Top-1 correct | Top-1 accuracy | Covered | Coverage | Potential recovery | Absent |
|---|---:|---:|---:|---:|---:|---:|---:|
| alarm | 58 | 52 | 89.66% | 54 | 93.10% | 2 | 4 |
| audio | 30 | 22 | 73.33% | 25 | 83.33% | 3 | 5 |
| calendar | 61 | 46 | 75.41% | 55 | 90.16% | 9 | 6 |
| cooking | 37 | 12 | 32.43% | 33 | 89.19% | 21 | 4 |
| datetime | 61 | 56 | 91.80% | 59 | 96.72% | 3 | 2 |
| email | 61 | 42 | 68.85% | 56 | 91.80% | 14 | 5 |
| general | 61 | 18 | 29.51% | 36 | 59.02% | 18 | 25 |
| iot | 61 | 52 | 85.25% | 58 | 95.08% | 6 | 3 |
| lists | 60 | 49 | 81.67% | 58 | 96.67% | 9 | 2 |
| music | 51 | 35 | 68.63% | 41 | 80.39% | 6 | 10 |
| news | 60 | 46 | 76.67% | 51 | 85.00% | 5 | 9 |
| play | 60 | 47 | 78.33% | 51 | 85.00% | 4 | 9 |
| qa | 60 | 45 | 75.00% | 54 | 90.00% | 9 | 6 |
| recommendation | 60 | 49 | 81.67% | 53 | 88.33% | 4 | 7 |
| social | 60 | 44 | 73.33% | 49 | 81.67% | 5 | 11 |
| takeaway | 39 | 30 | 76.92% | 35 | 89.74% | 5 | 4 |
| transport | 60 | 53 | 88.33% | 58 | 96.67% | 5 | 2 |
| weather | 60 | 55 | 91.67% | 56 | 93.33% | 1 | 4 |

## Frequent confusion pairs

These counts identify candidate areas for construction-data investigation. They do not establish an acoustic, knowledge, or reasoning cause from label errors alone. Build or validate semantic rules using permitted TRAIN material and task definitions; never transfer these discovery reference answers into runtime evidence.

| Population | Reference intent | First proposed intent | Confused rows | All rows with reference intent | Correct intent retained among proposals |
|---|---|---|---:|---:|---:|
| NEW500 | email_query | email_querycontact | 8 | 16 | 8 |
| NEW500 | general_quirky | qa_factoid | 6 | 29 | 2 |
| NEW500 | calendar_set | calendar_query | 5 | 14 | 4 |
| NEW500 | cooking_recipe | cooking_query | 5 | 8 | 5 |
| NEW500 | news_query | qa_factoid | 4 | 32 | 2 |
| NEW500 | email_sendemail | email_querycontact | 3 | 13 | 3 |
| DEV1000 | cooking_recipe | cooking_query | 21 | 35 | 19 |
| DEV1000 | general_quirky | qa_factoid | 15 | 54 | 4 |
| DEV1000 | email_query | email_querycontact | 10 | 27 | 9 |
| DEV1000 | news_query | qa_factoid | 8 | 60 | 3 |
| DEV1000 | calendar_set | calendar_query | 6 | 25 | 5 |
| DEV1000 | music_query | qa_factoid | 5 | 28 | 2 |

## Root recommendation

1. Retain alternative intent hypotheses for the next matched decision comparison. A 22.2% first-proposal error rate on NEW500 and 12.2 percentage points of available candidate headroom do not support an irreversible Top-1 commitment. This is an evidence-based design choice, not an invented universal accuracy threshold.
2. Distinguish candidate representation from agent autonomy. A model-driven agent can keep several hypotheses, request intent discrimination or slot interpretation evidence, revise its preferred intent, and then answer. Top-N need not imply a rigid retrieval pipeline or mandatory tool calls.
3. Separate the two knowledge roles. Intent values should explain activation, exclusion, and neighboring-intent distinctions. Slot values should explain semantic roles, extraction and normalization rules, value constraints, and binding to the proposed intent. Slot evidence may contradict the first intent. Populate both from lawful construction material; the existing label/statistical catalog is not yet a mature semantic knowledge base.
4. First isolate whether allowing candidate reselection converts available headroom into better final intent and official slot-SLU quality, including damage to initially correct rows. Use the same candidate source, roster, speech input, evidence supply, serving geometry, controller, and delivery/scoring path; vary only commitment policy. This component comparison does not by itself establish a complete autonomous-tool system.
5. Then validate native, on-demand consumption of the independently versioned stores and audio tools. Measure actual successful acquisitions, evidence use, corrected errors, introduced errors, final task quality, and per-stratum results. A reviewer may flag high-confidence problems; the frozen core retains final answer authority.
6. Address absent candidates separately after the commitment question closes. On NEW500, 50 rows cannot be repaired by selection inside the current candidate set. A later explicitly registered expansion action can revisit the full 60-label space or request new speech evidence; do not silently add that mechanism to the closed-candidate comparison.
7. Preserve all 1,000 rows in a future recovery design. Do not discard the 333 duplicate-output rows, add arbitrary alternatives, label them high-confidence, or claim that a variable-width projection was originally fixed Top-3. A prospective, traceable at-most-three projection is the preferred recovery proposal, pending concrete recovery admission; it is not executed by this diagnostic.

The earlier native direct result (73.2% NEW500 intent accuracy) used a different prompt and serving geometry. Do not subtract it from 77.8% here to claim a matched improvement.

## Artifacts and execution

- Registration: docs/readiness/2026-09-13-slurp-top3-source-intent-diagnostic-v1.json; SHA-256 fa6150660d3e0dc6922fd100403ae5d5e4f27194d87d8f8912f37a839b6ea56a.
- Aggregate diagnostic: /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/analysis/SAEA-SLURP-TOP3-SOURCE-INTENT-DIAGNOSTIC-V1/source-intent-diagnostic.json; SHA-256 c10dcb44936c8a6e92fd904732a28dbd5db25b0f92719d290e15dcd055b3e8bb.
- Offline per-row diagnostic: /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/analysis/SAEA-SLURP-TOP3-SOURCE-INTENT-DIAGNOSTIC-V1/source-intent-diagnostic.rows.jsonl; SHA-256 9bc6eb4521907dd733ac87460203133966170342b17160c6393ece75843b30e1.
- Preserved source trace SHA-256: e990f3db2bbf105a09c0d1cf5f7ce6c3f75e5d21814f549d376ec773496873cf.
- Analysis code commit: 586b082c692ea670a3b8f4bf52606ee9ddaa5a6c.
- Source contacts remain 1,000 generations and 3,001 actual-capacity endpoints. This analysis added zero model, tokenizer, encoder, ASR, GPU, or official scorer contacts.
- Verify raw HTTP response hashes separately from normalized transport-envelope hashes; they bind different byte representations. The initial analysis assertion equated them and stopped before reference loading. The corrected audit verifies both and matches the recorded model text and usage.
- Full successors remain unstarted. Keep the resident decoder service unchanged; no automatic restart or unregistered replacement work is authorized.

## Shared-entry reproduction closure

The config-driven shared analysis entry reproduced 462 numeric fields within absolute tolerance 1e-12, including every population and width-specific speaker interval, all scenario counts, and equal-scenario weighting. The preserved ABORTED attempt and raw trace hashes are unchanged. The shared path directly verifies the unsealed AttemptStore record, generation plan, source-quality release, and raw trace; it does not fabricate the run/trace manifests absent from this failed seal. Root validation passed 136 focused tests, Ruff, the engineering-base check, and diff checks. No official score or model/tool contact was added.

Run in WSL with the pinned checkout on PYTHONPATH:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/chao/saea-worktrees/slurp-top3-full-successors-v1/src /home/chao/.venvs/speechrl/bin/python -B -m speech_aware_evidence_acquisition.analysis.slurp_topn_diagnostics_cli --config /home/chao/saea-worktrees/slurp-top3-full-successors-v1/configs/analysis/slurp-top3-source-intent-diagnostic-v1.json --output /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/analysis/SAEA-SLURP-TOP3-SOURCE-INTENT-DIAGNOSTIC-V1/shared-entry-diagnostic-reproduction.json
```

Use a new output path; the entry refuses to overwrite an existing report. Implementation commit: 7d382f97. Config SHA-256: 1c4d96bc06530bb284845ae967a65e9cdcd0e4460e85b20da3ac6041f4cf60e9. Verification receipt: /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/analysis/SAEA-SLURP-TOP3-SOURCE-INTENT-DIAGNOSTIC-V1/shared-entry-verification-v1.json; SHA-256 dbe8efb2649ffb3a3c903fa1f5e68d1d7f69ff1a522b76220c1f138381331bff.

The independently versioned knowledge-store routing implementation also passed its 485-test worker suite and the root integration subset. It keeps model-facing evidence compact and full provenance in trace receipts. This is engineering readiness only; rich intent/slot knowledge releases and their task-quality effect are still pending.
