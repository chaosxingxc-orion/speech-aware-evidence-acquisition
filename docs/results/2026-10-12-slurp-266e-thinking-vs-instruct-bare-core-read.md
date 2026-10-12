# Cell 266-E, the bare-core read on TRAIN Fold B: Qwen3-Omni-30B-A3B-Thinking vs -Instruct (Q4_K_M, direct-only, no knowledge, no tools): RESOLVED-ABOVE-BAR (SLU-F1 +11.90 pp [+9.34, +14.52], intent +4.35 pp [+2.08, +6.62]); the bare Thinking core is still 18.95 pp SLU under the locked system on the Instruct core

Read 2026-10-12 by Claude Opus 5.5 (results-note agent, on the coordinator's brief, Fable 5.1) in the worktree
`opus/266e-results-note` (base master `af3501390`). Model-free: this note opened no model, server, encoder, embedder,
tokenizer or GPU, ran no scorer and wrote nothing under the data root. It reads the outputs of the registered read
`SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-VS-INSTRUCT-READ-V1` (`read.json`, `smoke-decode-cost.json`), the sealed run
manifests of the three arms and the smoke, the 266-E package, the registry and the exposure ledger. Section 5 has a few
extra figures that `read.json` does not carry: the cap-hit rows per scenario, the three arms on the cap-hit subset and
on its complement, and the Thinking token statistics without the cap-hit rows. They were computed with the reader's
own functions (`scripts/analysis/slurp_direct_fold_b_core_read.py`: `load_arm`, `roster_maps`, `paired_contrasts`,
`_pooled`, `_mean_field`; seed 20261011, 10,000 draws). The same call reproduces the headline of `read.json` to the
fourth decimal. Delivered text was reduced to an empty flag at load time and then dropped. No utterance text,
transcript, gold label, model output or reasoning text was printed or persisted. Only counts, rates, deltas, ids,
hashes, scenario names and token statistics appear below.

**DESCRIPTIVE.** These are development numbers on TRAIN Fold B (`SLURP-EVO-FOLD-B-V2`, n = 1,080, discovery role;
owner decisions 28 and 86). `claims_benefit` is false on every cell (`stage3_measurement` in the preregistration,
section 2). This is a capability measurement of two cores under one fixed bare form. It makes no system claim, no
admission, no test claim and no paper-scale claim (preregistration section 6). The Thinking model is admitted for this
read only (decision 266-E).

Ledger entry (decision 262, clause d: "266-E: the core-capability read"). On the bare direct-only form, the Thinking
core beats the Instruct core well above the cross-flight bar on SLURP SLU and intent. The swap closes about 39 % of
the SLU gap between the bare Instruct core and the locked system on the Instruct core.

## 1. Headline and verdict

Source: `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-VS-INSTRUCT-READ-V1/read.json`
(schema `saea-slurp-direct-fold-b-core-read-v1`, status "PREREGISTERED-READ (development numbers; never a test claim)").

| metric | Instruct | Instruct replicate | Thinking | d = Thinking - mean(Instruct, replicate), pp [CI95] | twin offset o = replicate - Instruct, pp [CI95] |
| --- | ---: | ---: | ---: | --- | --- |
| official pooled SLU-F1 % | 33.40 | 33.58 | **45.39** | **+11.90 [+9.34, +14.52]** | +0.18 [-1.16, +1.50] |
| intent % (`scenario_action_exact`) | 72.87 | 71.94 | **76.76** | **+4.35 [+2.08, +6.62]** | -0.93 [-1.85, 0.00] |

Intent saves / harms / ties (per-row `scenario_action_exact`):

| pair | saves | harms | ties |
| --- | ---: | ---: | ---: |
| Thinking vs Instruct | 103 | 61 | 916 |
| Thinking vs replicate | 109 | 57 | 914 |
| replicate vs Instruct | 8 | 18 | 1,054 |

The Instruct A/A pair differs on 26 of 1,080 rows. Thinking differs from either Instruct pass on 164 to 166 rows.

**Verdict: RESOLVED-ABOVE-BAR.** This is the reader's preregistered word, and the rule was fixed before contact
(preregistration section 3; `verdict()` in the reader). It reads on SLU-F1 only:

| condition | value | threshold | result |
| --- | ---: | ---: | --- |
| d >= bar | +11.90 pp | 2.5 pp | PASS |
| CI95 lower bound of d > abs(o) | +9.34 pp | 0.18 pp | PASS |
| reasoning-leak count, all three arms | 0 | 0 | PASS |

**Where the bar comes from.** The 24 GB card holds one core, so the two cores cannot share a flight. The design is
therefore `cross-flight-with-in-chain-replicate`. The Instruct arm flies twice in one chain on one session, as an arm
and a request-identical replicate, and Thinking is read against the mean of the two. The measurement instrument
(`docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md`, rule 3 and floor table 2d) admits a
cross-flight contrast only with that in-chain A/A, and only for large effects. It puts the bar at about 2.5 pp at
n = 1,080. Decision 266-E adopts it: "a stronger core is expected to show more than that or the line closes". The
measured A/A offset here, +0.18 pp SLU, sits well inside the bar. Intent is not part of the verdict rule. It clears the
same test anyway: CI lower bound +2.08 > abs(o) 0.93.

The verdict is not a cap artefact. Only the 36 cap-hit rows lose on Thinking's side. On the 1,044 rows where Thinking
delivered an answer, the contrast is larger: SLU +12.53 [+9.86, +15.17], intent +6.27 [+4.12, +8.43] (section 5).
The preregistration requires the full-roster number to be the reported one, with abstentions counted and never
adjusted away.

## 2. What was flown

| cell | run / attempt | flight commit | serving session | contacts / speech seconds | status |
| --- | --- | --- | --- | --- | --- |
| Instruct arm | `SAEA-SLURP-DIRECT-ONLY-FOLD-B-INSTRUCT-V1` / `attempt-slurp-direct-only-fold-b-instruct-generation-rec1-v1` | `c9edf3244` | `serving-slurp-native-candidate-five-train-a-np4-v1` (receipt sha `9dd26fd4...`) | 1,080 / 3,154.80 | COMPLETED, dirt empty |
| Instruct replicate | `SAEA-SLURP-DIRECT-ONLY-FOLD-B-INSTRUCT-REPLICATE-V1` / `attempt-slurp-direct-only-fold-b-instruct-replicate-generation-v1` | `c9edf3244` | same (`9dd26fd4...`) | 1,080 / 3,154.80 | COMPLETED, dirt empty |
| Thinking smoke (rec1) | `SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-SMOKE-4-V1` / `...-smoke-4-generation-rec1-v1` | `5daf057f8` | `serving-slurp-thinking-direct-fold-b-np4-max8192-v1` (receipt sha `e268b22e...`) | 4 / 9.94 | COMPLETED; decode cost only, never scored |
| Thinking arm (rec1) | `SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-V1` / `attempt-slurp-direct-only-fold-b-thinking-generation-rec1-v1` | `a069b0ee1` | `serving-slurp-thinking-direct-fold-b-np4-max8192-v1` (receipt sha `258205bf...`) | 1,080 / 3,154.80 | COMPLETED, dirt empty |

- **Times.** Seal times come from the countersigned READ row (`docs/exposure-ledger.md`): Instruct arm 2026-10-11T22:18Z,
  replicate 22:35Z, Thinking arm 2026-10-12T07:58Z. The run manifests' `created_at` reads 22:10:15Z, 22:33:18Z and
  07:53:26Z. The smoke rec1 manifest reads 2026-10-12T00:21:15Z. The registry gives the Instruct pair's wall times as
  21:57-22:18Z and 22:19-22:35Z. It says the Thinking arm was flying "since 06:01Z" and had sealed 302 rows by 06:31Z.
- **Form.** Both cores fly the sealed direct-only form: `phase-direct-only-v1`, the shared controller, `FlightRuntime`,
  OpenJiuwen and the `slurp-direct-max512` instruction. One contact per row; no knowledge supply
  (`evidence_source = none`); 0 tool calls. Prompt tokens are byte-for-byte the same size on all three arms: 2,460,404
  in total, 2,278.15 per contact (run manifests `cost`; `read.json` `prompt_tokens_per_contact_mean`). The knowledge pin
  is the fold-excluded view `...-tfrl-folds-v1` (sha `9c64e8ec...`). It changes no request bytes and only has to pass
  the runner's roster guard (section 7).
- **Cores and geometry.** Instruct: fragment `q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1`
  (completion cap 512) with the promoted EVO-FOLDS-V2 Instruct speech packets. Thinking: fragment
  `q4km-thinking-mmproj-free-slurp-direct-fold-b-np4-ctx24k-max8192-v1` (c 98,304, np 4, 24,576 tokens per slot, cap
  8,192, q8_0 KV, `--reasoning-format deepseek`, transport guard `refuse-think-marker-in-content`). It uses its own
  packet root, `/home/chao/feat-cache/slurp-q4km-packets-thinking-gpu-afdaeff6`, made by the GPU encoder pass
  `SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-PACKETS-GPU-V1` (1,076 cold rows in 164.5 s = 0.155 s per row; 1,080 packets
  promoted, receipt `ef409ef4...`; registry 13:55Z entry). Both cores run llama.cpp build `04ccc72a`.
- **Recoveries.** Each of the three cells used its single recovery (section 7). The Instruct arm aborted on the
  knowledge-roster guard. The smoke crashed on an empty answer at cap 2,048. The Thinking arm aborted at the exposure
  gate on a stale FIT row. The Instruct replicate flew on its first attempt.
- **Cost.**

  | arm | completion tokens total | per contact | latency seconds total | s per contact mean / p50 / p99 | slot-normalised GPU-h (sum / 4 slots) |
  | --- | ---: | ---: | ---: | --- | ---: |
  | Instruct | 27,065 | 25.1 | 925.5 | 0.86 / 0.80 / 2.04 | 0.064 |
  | replicate | 27,078 | 25.1 | 1,134.7 | 1.05 / 0.96 / 2.08 | 0.079 |
  | Thinking | 1,114,562 | 1,032.0 | 24,572.2 | 22.75 / 12.24 / 198.84 | **1.71** |

  `read.json` labels the 1.71 as "projection_gpu_hours". For a full 1,080-row arm, though, it is the measured latency
  sum divided by the 4 slots, so it assumes the slots stayed saturated. Its "upper_gpu_hours" of 14.9 is p99 x 1,080 / 4.
  That is a bound by construction, not a measurement. The wall time from the registry's 06:01Z start to the manifest's
  07:53Z is about 1.9 h, against a registered ceiling of 4.5 GPU-h. Per contact, Thinking costs 26.5x the Instruct
  latency and 41x its completion tokens.

## 3. The contrast and its noise model

- **Estimand.** d = SLU-F1(Thinking) minus the mean of SLU-F1(Instruct) and SLU-F1(replicate). Each term is pooled micro
  over the resampled ids from the per-sample counts of the official scorer `slurp-slu-official-train` (word and char
  tp / fp / fn groups, `pooled_f1`). Intent is the per-row mean of `scenario_action_exact`. The twin offset is
  o = replicate - Instruct (preregistration section 3).
- **Interval.** An utterance-cluster bootstrap with 10,000 draws, seed 20261011 and percentile CI95
  (`analysis.paired.resampled_statistic` with `cluster_of`). On this roster every row is its own utterance (1,080
  clusters for 1,080 rows), so the cluster bootstrap is a paired row bootstrap. Within each draw, all three arms are
  resampled on the same ids.
- **What the A/A pair says.** The two Instruct passes are request-identical and differ only by the flight, at the same
  session and commit. They land 0.18 pp apart on SLU (CI [-1.16, +1.50]) and 0.93 pp apart on intent (CI
  [-1.85, 0.00]; 8 saves / 18 harms). That is the within-chain, same-core noise the verdict guards against. The
  Thinking delta is 66 times the SLU offset and 4.7 times the intent offset.
- **What the design cannot remove.** The Thinking arm flew in another session about 8 hours later (06:01Z against 22:18Z), at another flight
  commit (`a069b0ee1` against `c9edf3244`). Session-level drift between those two sessions is not measured by the A/A
  pair, which shares one session. The 2.5 pp bar exists to cover that, and the observed delta is 4.8 times the bar.

## 4. Per scenario

Source: `read.json` `per_scenario` (18 scenarios from the roster's stratum, 60 rows each). The delta is Thinking minus
the mean of the two Instruct passes, each pooled inside the scenario. The table shows no per-scenario CIs: the reader
does not compute them, and at n = 60 each scenario is a descriptive cell. The cap-hit column comes from this note's
recomputation (section 5).

| scenario | n | SLU Instruct / repl. / Thinking % | SLU delta pp | intent Instruct / repl. / Thinking % | intent delta pp | Thinking cap hits |
| --- | ---: | --- | ---: | --- | ---: | ---: |
| alarm | 60 | 19.12 / 20.84 / 47.06 | +27.08 | 91.67 / 91.67 / 90.00 | -1.67 | 2 |
| audio | 60 | 28.99 / 23.02 / 55.95 | +29.95 | 73.33 / 71.67 / 80.00 | +7.50 | 3 |
| calendar | 60 | 24.00 / 23.62 / 40.90 | +17.09 | 68.33 / 66.67 / 76.67 | +9.17 | 0 |
| cooking | 60 | 50.83 / 48.08 / 71.19 | +21.74 | 68.33 / 68.33 / 65.00 | -3.33 | 2 |
| datetime | 60 | 18.65 / 23.41 / 54.32 | **+33.29** | 93.33 / 93.33 / 90.00 | -3.33 | 0 |
| email | 60 | 39.29 / 37.30 / 47.05 | +8.75 | 81.67 / 80.00 / 83.33 | +2.50 | 1 |
| general | 60 | 14.78 / 14.08 / 26.56 | +12.13 | 31.67 / 30.00 / 15.00 | **-15.83** | 4 |
| iot | 60 | 59.97 / 61.52 / 58.11 | **-2.64** | 86.67 / 86.67 / 85.00 | -1.67 | 4 |
| lists | 60 | 42.77 / 45.91 / 35.50 | **-8.84** | 81.67 / 83.33 / 81.67 | -0.83 | 2 |
| music | 60 | 31.50 / 30.81 / 20.37 | **-10.79** | 76.67 / 78.33 / 65.00 | **-12.50** | 3 |
| news | 60 | 24.53 / 24.45 / 35.65 | +11.16 | 85.00 / 85.00 / 85.00 | 0.00 | 1 |
| play | 60 | 41.27 / 42.28 / 47.45 | +5.67 | 18.33 / 16.67 / 76.67 | **+59.17** | 1 |
| qa | 60 | 49.75 / 51.69 / 56.30 | +5.58 | 68.33 / 68.33 / 75.00 | +6.67 | 6 |
| recommendation | 60 | 41.07 / 37.90 / 39.78 | +0.29 | 53.33 / 46.67 / 76.67 | +26.67 | 1 |
| social | 60 | 17.66 / 13.64 / 25.32 | +9.67 | 73.33 / 71.67 / 76.67 | +4.17 | 3 |
| takeaway | 60 | 39.94 / 41.03 / 49.71 | +9.22 | 83.33 / 81.67 / 81.67 | -0.83 | 1 |
| transport | 60 | 19.70 / 22.02 / 45.35 | +24.49 | 80.00 / 80.00 / 81.67 | +1.67 | 2 |
| weather | 60 | 23.67 / 25.11 / 47.76 | +23.37 | 96.67 / 95.00 / 96.67 | +0.83 | 0 |
| **natural mixture** (pooled roster) | 1,080 | | **+11.90** | | **+4.35** | 36 |
| **equal scenario** (mean of 18) | | | **+12.07** | | **+4.35** | |

The roster has 60 rows in every scenario. The natural mixture and the equal-scenario weighting therefore agree on
intent exactly. They differ on SLU only because pooled F1 weights a scenario by its slot mass.

**The sign pattern.**

- **SLU.**
  - 14 of 18 scenarios gain more than 5 pp.
  - The largest gains are in the time- and entity-heavy scenarios: datetime +33.3, audio +29.9, alarm +27.1,
    transport +24.5, weather +23.4, cooking +21.7.
  - Thinking loses in three: music -10.8, lists -8.8, iot -2.6. Recommendation is flat (+0.3).
  - In each of these four the Instruct baseline is 31-62 %, at or above its roster level of 33 %. Music is the only
    scenario where Thinking also loses intent.
- **Intent.**
  - The gains are concentrated in two scenarios where the Instruct core is weak: play +59.2 (18 % -> 77 %) and
    recommendation +26.7.
  - Thinking loses in general (-15.8: 31 % -> 15 %) and music (-12.5).
  - Six further scenarios lose 0.8-3.3 pp (alarm, cooking, datetime, iot, lists, takeaway); five of them sit at an
    Instruct intent of 82-93 %.
- **Mixed signs.** A blanket "Thinking is better" does not describe the result. On the play and recommendation side the
  Thinking core resolves the intent the Instruct core confuses. On general and music it changes the intent decision
  for the worse. These are the scenarios where SLURP's intent inventory overlaps the most (general vs qa / play,
  music vs play / audio). This note does not test that reading. A per-intent confusion table would.
- **Cap hits do not explain the losses.** The cap hits are spread over 15 scenarios. They cluster in qa (6), general
  (4) and iot (4), not in music (3) or lists (2). Had Thinking answered the 3 music cap-hit rows at the Instruct
  intent rate on cap-hit rows (about 51 %, section 5), it would recover about 1.5 of music's 7.5 net lost intent rows.

## 5. The Thinking answer distribution

Source: `read.json` `thinking_answer_length`, `thinking_empty_completion_receipts`, `delivered_content`,
`scorer_parse_failures`, `cost`, plus this note's recomputation (marked).

| item | Instruct | replicate | Thinking |
| --- | ---: | ---: | ---: |
| rows | 1,080 | 1,080 | 1,080 |
| empty delivered content | 0 | 0 | **36** |
| no JSON object in content | 0 | 0 | 36 |
| scorer parse failures (`parsed` = 0) | 0 | 0 | 36 |
| reasoning-leak markers in content | 0 | 0 | 0 |
| `saea-empty-completion-v1` receipts | -- | -- | 36 (`cap_hit` 36, `finish_reason` length 36) |

- **Thinking completion tokens per contact.** These come from the trace's COST channel and include the reasoning
  tokens, which the server routes to `reasoning_content`; the transport never reads it. Mean 1,032.0, p10 232, p50 584,
  p90 1,898, p99 8,192, max 8,192. The cap of 8,192 was hit on **36 of 1,080 rows (3.33 %)**.
- **Without the cap-hit rows** (1,044 rows; recomputed here). Mean 785.1, p50 557.5, p90 1,641.3, p99 3,609.9, max 7,694.
  The distribution has a long tail and a separate runaway mass: no delivering row needed more than 7,694 tokens, and
  every cap-hit row spent exactly 8,192 (receipt `completion_tokens` 8,192 on 36 / 36).
- **What the 36 rows are** (recomputed here).
  - The same 36 ids are empty-content, no-object and scorer-unparsed. Each one carries an empty-completion receipt at
    `finish_reason` length.
  - They are abstentions by truncation. The core spent its entire budget reasoning and delivered no content. Under
    decision 199 (empty is legal) and the preregistration they are sealed as receipted empty answers and scored as
    such, never re-asked or adjusted.
  - They are 36 distinct utterances in 15 scenarios: qa 6; general 4; iot 4; audio 3; music 3; social 3; alarm 2;
    cooking 2; lists 2; transport 2; email 1; news 1; play 1; recommendation 1; takeaway 1. Calendar, datetime and
    weather have none.
- **What the abstentions cost** (recomputed here).

  | subset | n | SLU Instruct / repl. / Thinking % | SLU d pp | intent Instruct / repl. / Thinking % | intent d pp |
  | --- | ---: | --- | ---: | --- | ---: |
  | cap-hit rows | 36 | 43.58 / 44.80 / 0.00 | -44.19 | 50.00 / 52.78 / 0.00 | -51.39 |
  | the other rows | 1,044 | 33.16 / 33.33 / 45.77 | +12.53 [+9.86, +15.17] | 73.66 / 72.61 / 79.41 | +6.27 [+4.12, +8.43] |
  | all | 1,080 | 33.40 / 33.58 / 45.39 | +11.90 [+9.34, +14.52] | 72.87 / 71.94 / 76.76 | +4.35 [+2.08, +6.62] |

  The cap-hit rows are not easy rows: the Instruct core gets only half their intents right (50.0 / 52.8 % against
  72-73 % overall). Including them shrinks the contrast by 0.63 pp SLU (+12.53 -> +11.90) and 1.92 pp intent
  (+6.27 -> +4.35). The verdict holds with or without them. The subset rows are descriptive. The preregistered
  number is the full-roster row.
- **Smoke versus arm.** The smoke rec1 (`smoke-decode-cost.json`, 4 rows) measured 1 cap hit of 4, a mean of 2,613
  tokens, 41.4 s per contact and a projection of 3.11 GPU-h (upper 6.99). The arm measured 3.3 % cap hits, 1,032 tokens,
  22.75 s per contact and 1.71 GPU-h. Four rows overstated the cost by about 1.8x, as expected when one runaway row is a
  quarter of the sample. The 4.5 GPU-h ceiling was never approached.
- **Reasoning stays out of the answer.** There were 0 leak markers in the sealed delivered text of all three arms
  (reader count), and the transport guard never fired (no flight stopped).

## 6. Reading against the system

The locked system on the Instruct core, on the same TRAIN Fold B roster:

- The R6-P1 delivering lock column, lock v2.2 + v4g, reads **SLU-F1 64.34 / intent 82.41** (registry section "265
  coverage pre-read"; `docs/results/2026-10-11-slurp-tfrl-coverage-preread-fold-b-offline.md`).
- The iteration-1 TFRL column's lock arm reads 64.00 / 82.31 (`docs/results/2026-10-11-slurp-tfrl-loop-i1-fold-b-column-read.md`,
  section 3).

Those columns fly the module program (`phase-native-module-v1-c4`: Perception and Solver contacts, knowledge supply,
the v4g normaliser). The rows below are cross-flight, cross-program arithmetic with no paired CI.

| comparison (Fold B, n = 1,080) | SLU-F1 pp | intent pp |
| --- | ---: | ---: |
| bare Instruct (mean of the two passes, 33.49 / 72.41) -> system on Instruct (R6-P1 lock, 64.34 / 82.41) | **+30.85** | **+10.00** |
| bare Instruct -> bare Thinking (this read, paired) | **+11.90** | **+4.35** |
| bare Thinking (45.39 / 76.76) -> system on Instruct | +18.95 | +5.65 |

Measured against the system's own lift over the bare core, the core swap recovers about 39 % of the SLU gap
(11.90 / 30.85) and about 44 % of the intent gap (4.35 / 10.00).

**What 266-E answers.** It asks whether CORE capability, and not the system, is the binding constraint (registry,
decision 266 option E). On the bare form the answer is: core capability is a real, large lever. The Thinking core
moves the bare SLU 4.8 times the cross-flight bar, mostly through slot values in time-, device- and entity-heavy
scenarios. The pre-read attributed the remaining SLU mass to core-side failures: values TRAIN never shows, and values
supplied but not used. A stronger core does move numbers of that kind on the bare form. On the bare form, though, the
gain is smaller than what the locked system already adds on the weaker core. The system is not dominated by the core
swap.

**What it does not answer.**

- **Transfer.** It does not show whether the locked system transfers to the Thinking core, nor whether the gains add
  up. "The system is core-agnostic by design" is a design statement in decision 266-E, not a measurement. A system
  column on the Thinking core would be a new cell under a new owner decision, because 266-E admits the Thinking model
  for this read only. Three measured facts bear on such a cell:
  - The system form sends at least two contacts per row (Perception and Solver) with longer prompts than the
    2,278-token direct prompt. At the measured 22.75 s per contact, a 1,080-row system column would cost a multiple
    of this arm's 1.71 GPU-h. That is an extrapolation, not a measurement.
  - The 3.3 % runaway-reasoning abstentions would recur per contact. The cap, the slot budget and the abstention rate
    under longer system prompts are unmeasured.
  - The intent losses in general and music would meet a Solver contract tuned on the Instruct core.
- **Core versus encoder.** "Core" here means the decoder together with its own audio encoder. The two mmproj files
  differ in 748 of 860 tensors (package Finding 1), so each arm runs its own speech packets. This read cannot separate
  the audio tower from the reasoning decoder.
- **Cap asymmetry.** The Instruct arm runs at completion cap 512 and the Thinking arm at 8,192. The Instruct cap does
  not bind: mean 25.1 completion tokens and 0 empty rows on both passes.
- **Scope.** This is no claim on DEV, test, A2T or Earnings. The carriers stay held (decision 242), and the numbers
  are development numbers.

Under the preregistration, NOT RESOLVED or HARM would have closed the Thinking-core line. RESOLVED-ABOVE-BAR keeps it
open. What flies next on it is the owner's decision.

## 7. Defects and lapses found during the campaign

Each item below is from the registry (`docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`, the 266-E
entries of 2026-10-11 and 2026-10-12), the package README / preregistration recovery sections, or the exposure
ledger at `af3501390`.

| # | what | root cause | fix | cost |
| --- | --- | --- | --- | --- |
| 1 | Instruct speech packets invalid for Thinking | mmproj audio tensors differ (748 of 860 not byte-identical) | own Thinking packet root; supersedes the reuse assumption (owner question answered: "Reuse: no") | one extra encoder pass |
| 2 | Thinking packets encoded on the CPU at 16-19 s per row | the preprocess fragment copied the CPU sidecar geometry (`-ngl 0 --no-mmproj-offload`); the owner ruled the rate unacceptable; the CPU pass was stopped at 11:50Z after 50 Fold B rows | GPU fragment `q4km-thinking-feature-preprocess-gpu-np1-v1`, new run id `...-THINKING-PACKETS-GPU-V1`; 0.155 s per row measured | about 15 min of CPU encode discarded (smoke 76.6 s, 50 rows in 799 s); CPU and GPU outputs are not mixed |
| 3 | CPU packet pass, start 1 refused / smoke attempt failed | row GPU cap 0.0 vs plan 1.0 (corrected to 1.0); the driver never created the Thinking legacy cache directory | d8822f64f (driver creates the cache roots, `--check-ledger` compares GPU hours) | 4 encoder rows (9.94 s) in the failed attempt |
| 4 | Thinking session start failed after a successful GPU encode | the serving runtime resolves the GGUF under the ext4 working-copy path, and only the E-drive archive existed | ext4 working copy made, sha-verified against the lock; Instruct restored 13:48:03Z | one swap window |
| 5 | **Instruct arm pre-contact abort** (20:07:46Z, `77b2283e9`, 0 calls) | the four 266-E baselines were derived from the DEV / test direct-only form and pinned the FULL-TRAIN knowledge view (50,628 source rows, every Fold B id inside); the runner's roster guard runs even when the program supplies no evidence | ead664100: all four baselines pin the fold-excluded view `...-tfrl-folds-v1` (37,407 rows, 0 Fold A / B ids); unit test on pin and disjointness; Instruct rec1 | the Instruct arm's one recovery; about 1.5 h GPU idle |
| 6 | **Smoke wave crash on an empty answer** (21:49Z, `c9edf3244`, 4 calls) | (a) cap 2,048 was below the Thinking trace on 1 of 4 rows; (b) the harness raised on an empty final content (`AgentStateArtifact.content must be a non-empty string`) instead of receipting it (decision 199) | 59d33fd26: the empty answer at the cap is sealed as the explicit empty-phase marker plus a `saea-empty-completion-v1` receipt; only a receipted contact may deliver empty bytes; the Instruct path is request-identical (test-pinned) | the smoke's one recovery; 4 calls / 9.94 s spent |
| 7 | **Cap amendment 2,048 -> 8,192** | pre-authorised by README Finding 3 for the decode-cost sign-off ("one re-registration") | new fragment `...-max8192-v1` and session `...-np4-max8192-v1`; Thinking arm GPU ceiling 3.0 -> 4.5; signed off at 00:23:16Z (marker naming 8192) | -- |
| 8 | **Thinking arm pre-contact abort** (00:25:21Z, `5daf057f8`, 0 calls): "execution plan claims 4.5 gpu hours but only 3.0 were pre-registered" | the coordinator's in-place amendment at the sign-off raised the generation row to 4.5 but left the live phase-fit row `...-THINKING-FIT-V1` at 3.0, and the gate reads the FIT-inclusive pre-registration | Thinking arm rec1 with both rows at 4.5 natively; 507629001 adds the blocking finding `row-gpu-under-plan` to `flight_registration_check.py` | the arm's one recovery; one more flip |
| 9 | **Ledger lapse of the amendment** (verified in `docs/exposure-ledger.md` at `af3501390`) | the superseded row `SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-FIT-V1` carries the note "AMENDED 2026-10-11T23:30:53Z ... GPU-hour ceiling 3.0 -> 4.5" while its gpu cell still reads **3.0**: the note claims an edit the cell never received. This is the root of #8. | superseded by the rec1 FIT row; the new gate catches the class | record only |

**Open in the ledger at `af3501390`** (observed; nothing changed here):

- The READ row `SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-VS-INSTRUCT-READ-V1` is countersigned (08:01:46Z) and still at
  `consumed = no`, although the read has run. The coordinator's closure is pending.
- The serving row `SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-SERVING-V1` (0.3 GPU-h) still reads "REGISTERED (DRAFT, root
  countersignature pending)", although Thinking sessions were started several times (20:41Z, 23:38Z and the arm's
  window). This note does not decide whether a session start needs a countersigned row. It records that the row is
  unsigned.
- The superseded CPU packets row `...-THINKING-PACKETS-V1` reads `consumed = no`, although its attempts made encoder
  contacts: 4 rows in the failed smoke and 50 Fold B rows before the stop. The row notes record the first 4. The
  50-row stop appears only in the registry and in the GPU row's text.
- The superseded first-attempt FIT rows `...-THINKING-FIT-V1` and `...-THINKING-SMOKE-4-FIT-V1` read `consumed = no`.
  They are superseded by rec1 rows, which matches the "one row per run id" precedent.

## 8. Records read

- Read: `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-VS-INSTRUCT-READ-V1/{read.json, README.md,
  smoke-decode-cost.json, smoke-decode-cost.md}`. Sealed hashes in `read.json`: Instruct scores `15c0736c...`, replicate
  scores `e621b76f...`, Thinking scores `cebe54ba...`, Thinking outputs `70f46211...`, Thinking manifest `827dc5e3...`.
- Reader (read only, and used as a library for section 5): `scripts/analysis/slurp_direct_fold_b_core_read.py`;
  `scripts/flights/direct/direct_fb_family.py` (`CELLS`, `ROSTER`).
- Runs (manifests and `cost` blocks; outputs reduced to empty flags; scores numeric fields only; trace COST channel and
  empty-completion receipts only): `$SPEECHRL_DATA_DIR/runs/SAEA-SLURP-DIRECT-ONLY-FOLD-B-{INSTRUCT,INSTRUCT-REPLICATE,
  THINKING,THINKING-SMOKE-4}-V1/`.
- Package: `docs/readiness/2026-10-11-slurp-direct-only-fold-b-thinking-vs-instruct-v1/README.md` (Findings 1-3,
  checklists, the three recovery sections) and `docs/readiness/2026-10-11-slurp-direct-only-fold-b-thinking-vs-instruct-v1-preregistration.md`
  (sections 1-6, recoveries).
- Registry: `docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`, from "265 coverage pre-read" through
  "Loop iteration 2 CLOSED" (decision 266 and every 266-E entry).
- Instrument: `docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md` (rule 3, table 2d).
- System context: `docs/results/2026-10-11-slurp-tfrl-coverage-preread-fold-b-offline.md` (via the registry);
  `docs/results/2026-10-11-slurp-tfrl-loop-i1-fold-b-column-read.md` (sections 0, 3).
- Exposure ledger: every row matching `DIRECT-ONLY-FOLD-B` in `docs/exposure-ledger.md` at `af3501390`.
- Roster: `docs/receipts/rosters/slurp-evo-fold-b-v2.json` (ids, utterance ids and strata only, via `roster_maps`).

**Not verified here.**

- The Thinking arm's GPU-active hours from the monitor. Section 2 gives the slot-normalised latency sum and the wall
  span instead.
- The causes of the general and music intent losses (section 4).
- Whether the 36 runaway traces repeat on a re-flight. Each row was flown once on Thinking.
