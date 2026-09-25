# VERIFY-1 complete selection result and root decision

Status: completed TRAIN construction read; task benefit not established. No system admission.

## Scope and execution

The recovery completed 625/625 rows at 2026-09-25 09:04 UTC using 625 model calls.
Every choice parsed, every row used one contact, and no malformed source placeholder
was selected. The original zero-contact fit-count refusal remains preserved.
After generation, the reader needed two metadata fixes: accept the registered recovery
identity, and derive per-row contact counts from the already-verified request trace
rather than assuming ordinary output rows have a native-episode contact_count field.
No model call, official rescore, answer change, roster change or re-generation followed
these reader fixes. Twelve focused reader tests pass, including retry accounting and
missing/wrong trace bindings. The sealed result bytes remain unchanged.

## All-roster results

| Method | Official pooled SLU-F1 (%) | Intent (%) |
| --- | ---: | ---: |
| mean_single | 57.8807 | 70.1760 |
| sample0 | 58.2154 | 70.2400 |
| medoid | 57.9064 | 70.4000 |
| chosen | 58.5816 | 70.7200 |
| row_f1_oracle | 64.4664 | 70.0800 |
| utility_oracle | 66.6360 | 69.9200 |

Mean-single pools the expected official counts over five source samples; it is not
the mean of row F1 values. Oracles use labels offline and optimize the named row metric;
neither is an attainable runtime policy or a universal pooled-F1 upper bound.

Chosen minus mean-single is +0.7009 pp SLU-F1, CI95 [-0.2551, 1.6507].
Chosen minus medoid is +0.6751 pp, CI95 [-0.3923, 1.7348].
Intent is +0.5440 pp versus mean-single, CI95 [0.0320, 1.0880]; the registered
operational noninferiority guard passes. The primary SLU-F1 benefit gate does not.
These are paired utterance-cluster bootstrap intervals, 10,000 draws, seed 20260915.

## Diagnostics and interpretation

- All 625 remain primary. On 420 content-distinct rows the gain is +0.9973 pp,
  CI95 [-0.2734, 2.2731]; this does not establish reliable selection either.
- The 225 rows whose source row-F1 differs show +2.0621 pp versus mean-single,
  CI95 [0.3987, 3.7842]. This subset depends on labels and cannot be an online
  selection trigger or replace the all-roster primary question.
- All 205 identical-answer rows selected position 1. This is compatible with
  deterministic tie-breaking and is not by itself evidence of harmful position bias.
  Among content-distinct rows position 1 is still selected 170/420 times, but
  duplicates and unequal evidence can also matter; no causal position-effect claim.
- The selector realizes only a small part of the label-informed reference gap.
  That gap establishes possible answer diversity, not the ability to exploit it.
- Equal-scenario SLU-F1 is 54.2728 versus 53.6613 (+0.6115 pp).

Root decision: do not promote this selector, enlarge sampling, or automatically open
the evidence-driven Reviewer successor. Close VERIFY-1 as benefit not proven, not
as proof that all verification mechanisms are ineffective. Continue the independently
approved VAR-2 supply-action experiment and F10 representation test. A materially
different evidence-driven Reviewer needs an identified information deficit and a new
prospective design; do not tune this result into a passing gate.

VAR-2 side branches are local Solver actions. Complete-system validation must precede
the bandit construction rounds. Keep fresh DEV and test closed.

## Per-scenario table

| Scenario | n | chosen SLU-F1 | mean-single SLU-F1 | chosen intent | mean-single intent |
| --- | ---: | ---: | ---: | ---: | ---: |
| alarm | 26 | 65.5781 | 67.6412 | 88.4615 | 87.6923 |
| audio | 30 | 52.0740 | 52.5276 | 66.6667 | 67.3333 |
| calendar | 42 | 60.4127 | 58.0682 | 59.5238 | 59.5238 |
| cooking | 31 | 61.4181 | 59.5795 | 67.7419 | 67.7419 |
| datetime | 39 | 62.1852 | 61.8669 | 82.0513 | 82.5641 |
| email | 33 | 51.1334 | 50.1081 | 78.7879 | 75.7576 |
| general | 42 | 11.6599 | 12.5370 | 14.2857 | 12.3810 |
| iot | 33 | 63.1861 | 63.2539 | 72.7273 | 72.7273 |
| lists | 37 | 45.7978 | 46.0187 | 83.7838 | 83.2432 |
| music | 27 | 14.2857 | 17.0940 | 62.9630 | 62.9630 |
| news | 36 | 46.2467 | 48.0100 | 72.2222 | 71.1111 |
| play | 37 | 57.1196 | 52.7011 | 72.9730 | 73.5135 |
| qa | 38 | 52.0737 | 49.5983 | 57.8947 | 57.3684 |
| recommendation | 29 | 67.7287 | 61.8665 | 82.7586 | 81.3793 |
| social | 35 | 66.6740 | 66.7960 | 77.1429 | 75.4286 |
| takeaway | 37 | 62.5366 | 62.4282 | 75.6757 | 76.2162 |
| transport | 32 | 73.5919 | 71.6215 | 78.1250 | 76.8750 |
| weather | 41 | 63.2081 | 64.1868 | 92.6829 | 92.6829 |

## Provenance and cost

Derived report: $SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-VERIFY-1-RECOVERY-READ-V1/report.json.
Report SHA-256: a3f9d7c71dc44b309cd995063ad3a2e952b81960823ce9b05a39c2c5fbca7060.
Generation: 1,794,164 prompt tokens, 15,440 completion tokens.
Monitored active generation time: 0.08165 GPU hours; this is not total wall time
including fits, preparation, idle waits or analysis.
No ASR, encoder, network or paid API was used by the generation flight.
Authoritative source hashes and all subgroup intervals are in report.json.
OBS: original prepared speech. ORG/SUPPLY: five frozen answers with balanced
positions. USE: one explicit choice. This is not a new end-to-end system run.
