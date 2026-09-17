# SLURP TRAIN A direct anchor: release and paired read against the retained agent

Status: RELEASED 2026-09-17 under owner decision 3 of 2026-09-16
(`docs/superpowers/plans/experiment-handoff/OWNER-FABLE-TAKEOVER-2026-09-16.md`). Root: Fable 5.1.
The direct run was finalized and officially scored once on 2026-09-16 and held unread under the
closed typed-context pair's release contract; the owner released it as the TRAIN A direct anchor.
This read added zero model, tokenizer, encoder, ASR, scorer or server contacts. Exploratory
TRAIN evidence on an exposed roster; no held-out or paper claim.

## Identity of the released direct arm

| Field | Value |
| --- | --- |
| Run / attempt | SAEA-SLURP-DIRECT-MAX512-TRAIN-FOLD-A-SOURCE-RECOVERY-V1 / attempt-slurp-direct-max512-train-fold-a-source-recovery-generation-v1 (FINALIZED, manifest COMPLETED) |
| Source / config / protocol | study commit f3189ce2667a45b1c0c9633e510747ae914118bd; config hash 2fb85dee608e48604a36eca09c2bb00ea9d8890f32e3fb41793e58b3fc564c18; protocol hash 707f3b65ae125239d6365e6551ff2a133568e10173ccea20696d72e97cf794b6 |
| Arm | `speech-feature-query`, policy `phase-direct-only-v1`, closed-list direct prompt with the full TRAIN ontology, max 512 output tokens, temperature 0, one contact per row |
| Roster / split | SLURP-EVO-FOLD-A-V2, 1,080 recordings, 125 speakers, 18 scenarios x 60; split identity 61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6; role discovery |
| Serving | attached to session serving-slurp-native-candidate-five-train-a-np4-v1 (frozen Q4_K_M, decoder-only, c98304 np4, prepared packets); no restart |
| Actual cost | 1,080 contacts, 3,084.528 repeated speech seconds, prompt tokens 2,459,915, completion tokens 26,764, generation wall 450.6 s (mean latency 1.10 s, 4 slots), preprocess 13.0 s, scoring 156.4 s |
| Scorer | slurp-slu-official-train (slurp-official-8eb16545, evaluator commit 8eb16545), identity check passed, 1,080/1,080 parsed |
| Score file | SAEA-SLURP-DIRECT-MAX512-TRAIN-FOLD-A-SOURCE-RECOVERY-V1.scores.json, SHA-256 7840a959fe4f43928fda0e0cacfe8c0ee4200116bfcd269bfe3451b59da29c38; run manifest 546109055a373b358c43d36878c532b95784ee5d73d07f011c5fa3ea3d7ce11e; outputs 5c182ddfc81effe2465fb58f052842538f22ead3601355dbe77427c937decd61 |

Official aggregate (natural mixture): pooled SLU-F1 33.885 %, intent (scenario+action) 73.704 %,
scenario 82.685 %, action 75.093 %, pooled span F1 21.098 %.

## Paired read: retained agent minus released direct, same 1,080 rows

Agent arm: SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1 (score file SHA-256
7360876322488e5fda689fcafda00e90da2ebf559e5a35e635c550f940202b47; 5,417 contacts; 7 malformed
rows retained). Paired whole-speaker cluster bootstrap, 10,000 draws, seed 20260915; deltas in
percentage points; pooled SLU and pooled span F1 use the shared `pooled_f1` count statistic, which
reproduces both arms' official aggregates to 1e-12.

| Metric | Estimand | Direct | Agent | Delta | Speaker CI95 | Speaker CI90 | Equal-scenario delta |
| --- | --- | ---: | ---: | ---: | --- | --- | ---: |
| Official pooled SLU-F1 | pooled count F1 | 33.89 | 48.53 | +14.65 | [+11.79, +17.51] | [+12.27, +17.05] | +13.10 |
| Intent (scenario+action) | per-row mean | 73.70 | 77.96 | +4.26 | [+2.15, +6.46] | [+2.50, +6.10] | +4.26 |
| Scenario accuracy | per-row mean | 82.69 | 84.81 | +2.13 | [-0.10, +4.51] | [+0.24, +4.13] | +2.13 |
| Action accuracy | per-row mean | 75.09 | 79.26 | +4.17 | [+1.84, +6.65] | [+2.20, +6.23] | +4.17 |
| Official pooled span F1 | pooled count F1 | 21.10 | 29.50 | +8.40 | [+5.18, +11.65] | [+5.72, +11.11] | +7.60 |
| Exact slot F1 | per-row mean | 10.72 | 19.02 | +8.30 | [+6.26, +10.46] | [+6.56, +10.09] | +8.30 |
| Official SLU-F1 | per-row mean | 16.06 | 30.29 | +14.23 | [+12.16, +16.52] | [+12.49, +16.14] | +14.23 |

Saves / harms / ties (agent recovers a direct failure / breaks a direct success) with the exact
two-sided McNemar p: intent 123 / 77 / 880, p = 1.4e-3; scenario 90 / 67 / 923, p = 7.9e-2; action
119 / 74 / 887, p = 1.5e-3; exact slot F1 157 / 43 / 880, p = 1.9e-16; per-row SLU-F1 302 / 76 /
702, p = 5.4e-33. The scenario-stratified bootstrap agrees with the speaker-clustered primary on
every metric. Scenario accuracy is the only metric whose CI95 crosses zero.

The TRAIN A pair matches the two sealed DEV1000 pairs of the same package (+14.30 and +14.80 pp
pooled SLU on NEW500; +14.62 on DEV1000): the agent's advantage over direct is stable across
rosters. Both arms remain far below the owner's bar (SLU-F1 >= 64, intent >= 78).

### Every scenario

| Scenario | n | Direct SLU | Agent SLU | Delta | Direct intent | Agent intent | Delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| alarm | 60 | 27.61 | 52.66 | +25.05 | 91.67 | 83.33 | -8.33 |
| audio | 60 | 43.27 | 47.75 | +4.49 | 75.00 | 76.67 | +1.67 |
| calendar | 60 | 35.69 | 48.38 | +12.69 | 81.67 | 75.00 | -6.67 |
| cooking | 60 | 44.14 | 62.47 | +18.33 | 61.67 | 85.00 | +23.33 |
| datetime | 60 | 33.38 | 59.52 | +26.13 | 90.00 | 83.33 | -6.67 |
| email | 60 | 23.33 | 36.64 | +13.31 | 85.00 | 85.00 | 0.00 |
| general | 60 | 14.81 | 15.45 | +0.64 | 46.67 | 36.67 | -10.00 |
| iot | 60 | 55.91 | 55.53 | -0.38 | 80.00 | 86.67 | +6.67 |
| lists | 60 | 46.52 | 43.55 | -2.97 | 90.00 | 83.33 | -6.67 |
| music | 60 | 36.90 | 34.53 | -2.36 | 68.33 | 76.67 | +8.33 |
| news | 60 | 29.98 | 44.24 | +14.26 | 80.00 | 80.00 | 0.00 |
| play | 60 | 42.56 | 46.82 | +4.27 | 26.67 | 58.33 | +31.67 |
| qa | 60 | 50.44 | 57.04 | +6.60 | 73.33 | 75.00 | +1.67 |
| recommendation | 60 | 31.97 | 49.75 | +17.77 | 63.33 | 90.00 | +26.67 |
| social | 60 | 11.61 | 34.74 | +23.13 | 63.33 | 66.67 | +3.33 |
| takeaway | 60 | 42.27 | 48.84 | +6.57 | 85.00 | 85.00 | 0.00 |
| transport | 60 | 22.01 | 51.34 | +29.32 | 71.67 | 86.67 | +15.00 |
| weather | 60 | 14.89 | 53.81 | +38.92 | 93.33 | 90.00 | -3.33 |

Pooled SLU falls in three scenarios (iot, music, lists) and intent falls in five (alarm, calendar,
datetime, lists, general). The agent's intent loss on `general` (46.67 -> 36.67) and the tiny SLU
gain there restate the program's named hole: the direct prompt answers `general` better than the
candidate pipeline does. Speaker clusters are unbalanced (1 to 56 rows per speaker, mean 8.64;
112 of 125 speakers span more than one scenario), which the cluster bootstrap absorbs.

## What this release is for

- The TRAIN A system-versus-direct claim of the SLURP v2 program (cell B5 compares the v2
  candidate to this anchor and to the retained agent on the same rows).
- A same-roster reference for the per-scenario holes the Phase A audits are sizing.

It does not change any historical verdict, does not reopen the closed typed-context pair, and is
not evidence about the program's later modules.

## Source custody

- `/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/analysis/SAEA-SLURP-TRAIN-A-DIRECT-ANCHOR-RELEASE-PAIRED-ANALYSIS-V1/score-contrasts.json`, SHA-256 fe1008ec97627b4b2358870543b4bb4d58a764211e9fa119f35e36f59ae800e5 (inputs pinned by hash, seed, draws, implementation hashes, model_calls 0).
- `.../roster-metadata.json` (sample id, scenario, speaker id, headset; no text), SHA-256 07f4cd83b83d83d65500a328e0a38421ede575195c63ae118def0d1006c14e34.
- `.../README.md`, SHA-256 bb96869ab23edcfbae1edf09956fe87088de5a52410291b95ae6fb5e7d7185b0.
- Roster `docs/receipts/rosters/slurp-evo-fold-a-v2.json`, SHA-256 1fe7908c31396774d7535fdf37bd791762215c324999d66ed7beb9e7b2f9033d.
- Estimators: `analysis.paired.paired_contrast`, `analysis.paired.resampled_statistic`,
  `analysis.null_calibration.pooled_f1` (the shared implementation; `score_compare_cli` was not
  used because it hard-codes CI90 and DEV population names).
