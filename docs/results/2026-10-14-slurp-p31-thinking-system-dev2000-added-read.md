# P3.1, the locked SLURP system on the Thinking core, DEV-2000-ADDED replicate: NOMINATED (SLU-F1 +7.52 pp [+5.46, +9.62], intent +2.50 pp [+1.00, +4.07] over the same system on the Instruct core); Fold B contrast replicated (share 1.05); decision 299 A conditions 3/3 on this roster -> REBUILD-BASE-ON-THINKING

Read 2026-10-14 by Claude Opus 5.5 (results-note agent, on the coordinator's brief, Fable 5.1) in the worktree
`opus/p31-results-note` (base master `8132badd8`). Model-free: this note opened no model, server, encoder, embedder,
tokenizer or GPU, ran no scorer and wrote nothing under the data root. It reads the outputs of the registered read
`SAEA-SLURP-SYSTEM-THINKING-CORE-DEV2000-ADDED-READ-V1` (`read.json`, `README.md`, `smoke-decode-cost.json`), the P3.1
package (`docs/readiness/2026-10-13-slurp-system-thinking-core-dev2000-added-v1/`), the registry and the exposure
ledger. It computes nothing anew except ratios, sums and differences of numbers printed in those files (marked
"derived"). No utterance text, transcript, gold label, model output or reasoning text was read, printed or persisted.

**Status: PREREGISTERED-READ, development numbers on DEV-2000-ADDED (`SLURP-DEV-2000-ADDED-V1`, n = 1,000, dev role;
owner decisions 28 and 86). Never a test claim. `claims_benefit` is false on every cell** (`stage3_measurement` in
`registered-facts-v1.json`). The read replicates on a roster the Thinking core has never seen the 268-B Fold B finding
(the locked system on the Thinking core beats the same system on the Instruct core). It is not an admission and not a
system-level, superiority, generalisation, held-out, confirmatory or paper-scale claim (`analysis-recipe-v1.json`,
`claim_boundary`); nothing is locked by the read itself (`what_is_not_here`).

Ledger entry (registry step P3.1, decision 299 A). The locked system (lock v2.2 + v4g, program
`phase-native-module-v1-c2`, the parent's full-TRAIN knowledge view) flown on the Thinking core beats the same system on
the Instruct core by +7.52 pp SLU-F1 and +2.50 pp intent on DEV-2000-ADDED, outside the in-chain twin offset on SLU and
above the 2.5 pp cross-flight bar. It reproduces 105 % of the 268-B Fold B contrast (+7.15). Every contact completed
(0 cap hits, 0 empty answers, 0 reasoning markers); the reasoning budget forced the close on 16-17 % of Perception and
46-47 % of Solver contacts; the cost per arm stayed under the registered ceiling. The twin's intent offset is itself
resolved above zero (+1.60 pp), so the intent part of the contrast is not cleanly attributable.

## 1. Headline and verdict

Source: `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-SYSTEM-THINKING-CORE-DEV2000-ADDED-READ-V1/read.json` (schema
`saea-slurp-system-thinking-core-dev-read-v1`, status "PREREGISTERED-READ (development numbers; never a test claim;
claims_benefit false)"). Interval: utterance-cluster bootstrap, 10,000 draws, seed 20261011, CI95.

| metric | Instruct lock (NX R5 composed) | bare Instruct | Thinking system (lock) | twin (aa) | d_system (pp) | CI95 | twin offset (pp) [CI95] | vs bare Instruct (pp) [CI95] |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| official pooled SLU-F1 % | 67.18 | 38.09 | **74.69** | 74.08 | **+7.52** | [+5.46, +9.62] | -0.61 [-1.88, +0.69] | +36.60 [+33.28, +39.86] |
| intent % | 82.00 | 61.70 | **84.50** | 86.10 | **+2.50** | [+1.00, +4.07] | **+1.60 [+0.60, +2.67]** | +22.80 [+19.84, +25.97] |

- **Arms.** Instruct lock = the sealed NX R5 composed cell on the same roster
  (`SAEA-SLURP-STAGE3-NX-R5-COMPOSED-DEV2000-ADDED-V1`, lock v2.2 + v4g on the Instruct core, study commit `9a0a3384b`;
  the package's derivation parent and the comparator column). Bare Instruct = `SAEA-SLURP-DIRECT-MAX512-DEV2000-ADDED-V1`
  (direct-only form, max512). **No bare Thinking core exists on this roster** (`comparators.bare_thinking_core` "none on
  this roster"; package prerequisite 6), so the "vs bare" column orients against the bare *Instruct* core and is not
  comparable to 268-B's "vs bare Thinking" column. d_system = Thinking system lock minus Instruct lock; twin offset o = aa
  minus lock; vs bare = Thinking system lock minus bare Instruct.
- **Replication of Fold B.** d_system SLU +7.52 on DEV against +7.15 on Fold B: **share 1.05**
  (`replication_of_fold_b`). Intent +2.50 against +2.31 (derived from the 268-B note).
- **Intent saves / harms / ties** (per row): lock vs Instruct lock 44 / 19 / 937; aa vs lock 21 / 5 / 974; lock vs bare
  Instruct 248 / 20 / 732.
- **Delivered content.** Empty content / no JSON object / reasoning leak: 0 / 0 / 0 on every arm (lock, aa, Instruct
  lock, bare Instruct; 1,000 rows each). Scorer parse failures: lock 0, aa 0, Instruct lock 1, bare Instruct 1.
  `reasoning_marker_total` 0.

**Verdict: NOMINATED.** The reader's preregistered word (`scripts/analysis/slurp_system_thinking_core_dev_read.py`; rule
fixed in the package README "Read rule (preregistered)" before any contact and restated in the registry "P3.1 LAUNCHED"
(17:25Z)). Words: NOMINATED (all three rows below); HARM (d <= -2.5 pp and CI95 hi < -|o|); NOT-NOMINATED otherwise.

| condition | value | threshold | result |
| --- | ---: | ---: | --- |
| CI95 lower bound of d_system SLU > abs(twin offset) | +5.46 pp | 0.61 pp | PASS |
| intent CI95 lower bound >= -intent guard | +1.00 pp | -0.65 pp | PASS |
| delivered reasoning markers (lock, aa) | 0 | 0 | PASS |

**Reported beside the word, not part of it** (`reported_beside_the_word`): the point against the 2.5 pp cross-flight bar
is met (`point_vs_cross_flight_bar` true; +7.52 is 3.0 times the bar and the CI95 lower bound +5.46 is 2.2 times it,
derived); the decision-299 conditions on this roster are met 3 / 3 (section 6).

**Design.** `cross-flight-with-in-chain-replicate` (measurement instrument
`docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md`). One 24 GB card holds one core, so the Instruct
and Thinking systems cannot share a flight. The Thinking system flew twice in one chain on one session at one flight
commit (lock and its request-identical twin aa); the twin offset is the same-core noise the verdict guards against.
Session drift between the Instruct NX R5 flight and this chain is not measured by the twin; the 2.5 pp bar covers it.

**The intent twin offset is resolved (a limitation, not a verdict input).** The twin was registered to look for no
effect (`expected_effect_pp` 0.0), yet aa minus lock on intent is +1.60 pp [+0.60, +2.67] (21 saves / 5 harms over
1,000 rows). This is the in-flight A/A variability of intent at n = 1,000 on the Thinking core at np4; its cause is not
measured here. Consequences: (i) the intent d_system lower bound (+1.00) does not exceed the intent twin offset (1.60),
so the +2.50 pp intent gain over the Instruct system is not attributable to the core beyond same-core noise; only the
guard (not worse than -0.65 pp) is claimed for intent; (ii) the SLU twin offset (-0.61 [-1.88, +0.69]) is what the
verdict rule uses, and it is unresolved. On Fold B the offsets were the other way round (SLU +1.15, intent -0.09).

## 2. What was flown

| cell | run id / attempt | flight commit | contacts / speech-audio s | seal | summed call latency |
| --- | --- | --- | --- | --- | --- |
| smoke (4 rows) | `SAEA-SLURP-STAGE3-THINKING-SYSTEM-DEV2000-ADDED-SMOKE-4-V1` | `37b0ed0aa` | 8 / 16.3 | 2026-10-13 17:25:50Z | 0.12 h (decode cost only, never scored) |
| Thinking system arm (lock) | `SAEA-SLURP-STAGE3-THINKING-SYSTEM-DEV2000-ADDED-LOCK-V1` / `attempt-slurp-native-stage3-thinking-system-dev2000-added-lock-generation-v1` | `37b0ed0aa` | 2,000 / 5,967.1 | 2026-10-14 02:35:33Z | **35.07 h** |
| in-chain twin (aa) | `SAEA-SLURP-STAGE3-THINKING-SYSTEM-DEV2000-ADDED-AA-V1` / `attempt-slurp-native-stage3-thinking-system-dev2000-added-aa-generation-v1` | `37b0ed0aa` | 2,000 / 5,967.1 | 2026-10-14 11:42:24Z | **35.62 h** |

Sources: exposure-ledger rows of the three cells (CONSUMED notes: manifest COMPLETED, attempt FINALIZED for lock and aa);
registry "P3.1 LAUNCHED" (17:25Z); `read.json` `nodes_by_arm`. Summed call latency is slot-hours, not wall-clock GPU-h.

- **System.** The sealed Instruct NX R5 composed cell on DEV-2000-ADDED, byte for byte, except the model fragment, the
  speech-packet promotion receipt, the preflight deferral to the exact native contact gate, the FIT identities and the
  cell's own first-phase supply (package README "What is registered"): lock v2.2 + v4g post-processing, program
  `phase-native-module-v1-c2` (Perception + Solver, 2 contacts per row, review off, no supply arm, no column), the
  parent's full-TRAIN knowledge view (DEV rows are disjoint from TRAIN by construction), roster
  `configs/dataset/slurp-speech-native-dev2000-added.json` (split `ee6c43cd...`). The core is the one factor.
- **Core and session.** Model fragment `q4km-thinking-mmproj-free-slurp-module-fold-b-np4-ctx24k-budget3072-max4096-v1`,
  session `serving-slurp-thinking-module-fold-b-np4-budget3072-max4096-v1` (both reused unchanged from 268-B), swap
  target **`think-budget-np4`** (4 slots, 24,576 tokens per slot). DEV Thinking speech packets encoded in the swap window
  (row `SAEA-SLURP-DEV2000-ADDED-THINKING-PACKETS-GPU-V1`; 1,000 rows at 0.114 s per row, 0 failed) and promoted
  additively into the Thinking packet root as `DEV-2000-ADDED-promotion.json` (sha `1a6dca3a...`; registry 17:25Z).
- **Thinking knobs.** Identical to 268-B: reasoning budget **3,072** tokens + answer reserve 1,024 = completion cap
  **4,096**; forced-close message pinned; `reasoning_context_policy` **`drop-reasoning-v1`**; every node thinks;
  temperature 0, seed 20260913; one answer-only fallback per node; reasoning bytes projected to hash-and-stats only
  (decision 286).
- **Wall time.** Not given directly in the files read. The chain was serial on one session (smoke, sign-off, lock, aa),
  so seal-to-seal spans bound each arm from above: lock at most 9 h 10 min (smoke seal 17:25:50Z to lock seal 02:35:33Z,
  including the sign-off wait), aa at most 9 h 07 min (lock seal to aa seal); at least about 1.82 rows/min per arm
  (derived), consistent with the 1.84 rows/min the ceilings were planned from.
- **Cost, stated plainly.** Summed latency / 4 slots = **about 8.8-8.9 slot-normalised GPU-h per arm** (lock 35.07 / 4 =
  8.77, aa 35.62 / 4 = 8.91, derived; the node sums in `read.json` give 4.05 + 4.72 = 8.77 and 4.04 + 4.86 = 8.90).
  The registered ceiling is **11.8 GPU-h per arm** (from measured 4-slot throughput, `ceil_0.1(rows / 1.84 / 60 x 1.3)`;
  package prerequisite 4). **Both arms stayed under it** (74-75 % of the ceiling, derived). Mean 63.1 s (lock) and
  64.1 s (aa) per contact (derived: summed latency x 3,600 / 2,000).

## 3. Per scenario

Source: `read.json` `per_scenario` (13 scenarios present on this roster; scenario taken from the governed devel loader at
read time). d_system is the Thinking system lock minus the Instruct lock inside the scenario. No per-scenario CIs: the
reader does not compute them. **Scenarios with n < 10 (datetime 9, recommendation 6, social 4) are unresolved and
reported for completeness only**; news (n = 20) is barely better.

| scenario | n | SLU Instruct lock / Thinking lock / aa / bare % | SLU d_system pp | intent Instruct lock / Thinking lock / aa / bare % | intent d_system pp | SLU vs bare pp |
| --- | ---: | --- | ---: | --- | ---: | ---: |
| calendar | 221 | 71.50 / 80.11 / 78.46 / 32.99 | +8.61 | 81.45 / 84.16 / 85.52 / 67.42 | +2.71 | +47.12 |
| datetime (unresolved, n < 10) | 9 | 75.00 / 88.89 / 88.89 / 0.00 | +13.89 | 77.78 / 77.78 / 77.78 / 77.78 | 0.00 | +88.89 |
| email | 96 | 59.06 / 67.17 / 65.66 / 30.00 | +8.11 | 86.46 / 91.67 / 91.67 / 81.25 | +5.21 | +37.17 |
| general | 62 | 34.82 / 49.91 / 47.20 / 27.46 | +15.10 | 43.55 / 43.55 / 50.00 / 32.26 | 0.00 | +22.45 |
| iot | 57 | 71.24 / 75.43 / 74.96 / 48.83 | +4.20 | 87.72 / 96.49 / 94.74 / 89.47 | +8.77 | +26.61 |
| lists | 52 | 57.18 / 74.45 / 79.65 / 43.54 | **+17.27** | 88.46 / 92.31 / 92.31 / 90.38 | +3.85 | +30.91 |
| news | 20 | 67.50 / 85.70 / 80.81 / 16.28 | +18.20 | 95.00 / 100.00 / 95.00 / 90.00 | +5.00 | +69.42 |
| play | 203 | 59.38 / 65.24 / 66.75 / 46.08 | +5.85 | 83.25 / 84.24 / 86.21 / 20.20 | +0.99 | +19.16 |
| qa | 157 | 68.66 / 72.31 / 71.01 / 55.45 | +3.64 | 77.71 / 79.62 / 82.80 / 63.06 | +1.91 | +16.86 |
| recommendation (unresolved, n < 10) | 6 | 0.00 / 0.00 / 0.00 / 0.00 | 0.00 | 100.00 / 100.00 / 100.00 / 33.33 | 0.00 | 0.00 |
| social (unresolved, n < 10) | 4 | 81.08 / 88.89 / 67.42 / 0.00 | +7.81 | 75.00 / 50.00 / 75.00 / 100.00 | **-25.00** | +88.89 |
| transport | 48 | 79.29 / 81.58 / 81.19 / 24.68 | **+2.29** | 93.75 / 95.83 / 97.92 / 79.17 | +2.08 | +56.90 |
| weather | 65 | 72.59 / 82.70 / 85.08 / 19.36 | +10.11 | 96.92 / 98.46 / 98.46 / 96.92 | +1.54 | +63.34 |
| **natural mixture** (pooled roster) | 1,000 | 67.18 / 74.69 / 74.08 / 38.09 | **+7.52** | 82.00 / 84.50 / 86.10 / 61.70 | **+2.50** | **+36.60** |
| **equal scenario** (mean of 13) | | | **+8.85** | | **+0.54** | **+43.67** |

Scenario sizes are unequal (4 to 221 rows), so the two weightings differ. The equal-scenario intent figure (+0.54) is
dominated by social's -25.00, which is one row of four; without social the mean of the other 12 scenarios is +2.67
(derived from the table). The equal-scenario SLU and vs-bare figures are likewise lifted by the n < 10 scenarios
(datetime +13.89, social +7.81 SLU; +88.89 vs bare on both).

**The sign pattern (descriptive).**

- **SLU.** 12 of 13 scenarios gain; no scenario loses; recommendation is 0.00 on every arm (n = 6). Among the 10
  scenarios with n >= 10 the largest gains are news +18.2 (n = 20), lists +17.3, general +15.1, weather +10.1; the
  smallest are transport +2.3, qa +3.6 and iot +4.2. The two large scenarios, calendar (+8.6, n = 221) and play (+5.9,
  n = 203), carry 42 % of the roster (derived).
- **Intent.** 9 of 13 gain, 3 are tied (datetime, general, recommendation), 1 loses (social, -25.00 = one row of four).
  The largest resolved gain is iot +8.77; general stays tied at 43.55 % on both cores.
- **Against 268-B (Fold B).** On Fold B the Thinking system lost SLU in music (-4.20) and transport (-0.52); music is
  absent from this roster and transport gains +2.29 here. lists (+24.77 on Fold B, +17.27 here), general (+12.07,
  +15.10) and weather (+17.75, +10.11) are large on both rosters. This note does not test why.
- **Twin spread.** Per-scenario aa minus lock SLU, n >= 10 only, ranges from -4.88 (news, n = 20) to +5.20 (lists)
  (derived from the table); single-scenario deltas of that size are inside same-core noise at these sizes.

## 4. Node tables

Source: `read.json` `nodes_by_arm`. Wire completion tokens include the reasoning tokens. The cap is 4,096 on every node.
Forced close = the reasoning budget (3,072) closed the think block and the node answered from the reserve (the decision
273 mechanism).

**lock** (`SAEA-SLURP-STAGE3-THINKING-SYSTEM-DEV2000-ADDED-LOCK-V1`)

| node | contacts | cap hits | length finishes | empty | no JSON | forced closes | completion tokens mean / p50 / p99 (max) | prompt tokens mean | s per contact mean / p50 / p99 | slot-normalised GPU-h |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- | ---: |
| Perception | 1,000 | 0 | 0 | 0 | 0 | 174 (17.4 %) | 1,993.1 / 1,853.5 / 3,195.0 (3,203) | 3,578.3 | 58.34 / 54.18 / 103.00 | 4.05 |
| Solver | 1,000 | 0 | 0 | 0 | 0 | 457 (45.7 %) | 2,071.1 / 2,358.5 / 3,151 (3,169) | 8,996.0 | 67.92 / 72.68 / 119.07 | 4.72 |

**aa** (`SAEA-SLURP-STAGE3-THINKING-SYSTEM-DEV2000-ADDED-AA-V1`)

| node | contacts | cap hits | length finishes | empty | no JSON | forced closes | completion tokens mean / p50 / p99 (max) | prompt tokens mean | s per contact mean / p50 / p99 | slot-normalised GPU-h |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- | ---: |
| Perception | 1,000 | 0 | 0 | 0 | 0 | 158 (15.8 %) | 1,961.9 / 1,864 / 3,194 (3,218) | 3,578.3 | 58.18 / 54.53 / 104.17 | 4.04 |
| Solver | 1,000 | 0 | 0 | 0 | 0 | 473 (47.3 %) | 2,102.4 / 2,631 / 3,150 (3,168) | 9,033.0 | 70.05 / 81.80 / 120.10 | 4.86 |

Percentages derived (forced closes / 1,000). Every finish reason is `stop` (2,000 / 2,000 per arm); `marker_in_content`
is 0 on every node. The completion p99 sits about 900-950 tokens under the cap on every node: the budget plus the answer
reserve keep every task finished, never an empty answer at the cap. Against Fold B (268-B lock: Perception 17.6 %, Solver
45.9 % forced closes; 58.34 / 67.15 s per contact) the node profile is nearly unchanged; the DEV Solver prompt is about
430 tokens longer on the mean (8,996.0 vs 8,563.6, derived).

## 5. The smoke

Source: `smoke-decode-cost.json` (schema `saea-slurp-system-thinking-core-dev-read-smoke-v1`, "DECODE-COST PER NODE (no
score, no read)"); exposure-ledger smoke row.

- **Smoke** `SAEA-SLURP-STAGE3-THINKING-SYSTEM-DEV2000-ADDED-SMOKE-4-V1` (flight commit `37b0ed0aa`, 4 rows / 8 contacts on
  `think-budget-np4`, sealed trace `40f7dd15...`): Perception 0 cap hits, 0 empty, 4 `stop`, 1 forced close, completion
  p50 2,412.5 / max 3,132, prompt mean 3,581.5, 61.17 s per contact; Solver 0 cap hits, 0 empty, 4 `stop`, 1 forced
  close, completion p50 1,936 / max 3,120, prompt mean 7,066.5, 47.17 s per contact. No reasoning marker, no JSON
  failure.
- **Projection vs plan.** 7.52 slot-normalised GPU-h per 1,000-row pass (node sum) against the registered 11.8 ceiling;
  expected wall 9.06 h at the measured 1.84 rows/min. No sign-off amendment was needed (the ceiling came from measured
  4-slot throughput, the lesson of the 268-B overrun).
- **Smoke vs arm.** The arms measured 8.77 / 8.90 GPU-h against the smoke's 7.52 (about 1.17-1.18x, derived): Perception per
  contact was close (58 s vs 61 s), Solver slower at four slots (68-70 s vs 47 s), the same direction as 268-B but
  smaller, and well inside the ceiling.

## 6. Decision 299 A conditions on this roster: 3 / 3 -> REBUILD-BASE-ON-THINKING (reported beside the word)

Source: `read.json` `reported_beside_the_word.decision_299_conditions_on_this_roster`; registry "Owner rulings 297-300".

Decision 299 A (ruled 2026-10-12) was defined on the 268 Fold B column; the reader re-evaluates its three conditions on
DEV-2000-ADDED as a consistency report: (i) paired SLU resolved and point estimate >= +1.5 pp, (ii) intent not worse by
more than 0.65 pp, (iii) Thinking completion rate (no cap hit, no empty answer) >= 99 %.

| condition | value | threshold | met |
| --- | ---: | ---: | --- |
| SLU resolved and above point | point +7.52 pp; CI95 lo +5.46 (> 0 and > twin offset 0.61) | point >= 1.5 pp; CI lo > 0 | yes |
| intent guard | intent CI95 lo +1.00 pp | not worse than -0.65 pp | yes |
| completion rate | 1.0000 (2,000 lock contacts, 0 incomplete) | >= 0.99 | yes |

**Met 3 / 3. Direction: REBUILD-BASE-ON-THINKING**, the same direction the 268-B read fired. It is reported beside the
verdict word and is not part of it. The reader's note string on this block reads "development reading on TRAIN Fold B;
never a benefit claim (the benefit bar stays bar_pp)": the "TRAIN Fold B" wording is carried over from the 268-B reader;
the numbers in the block are the DEV-2000-ADDED ones (see "Not verified here").

## 7. What follows (registered next steps, not results)

Per the P3.1 read rule (package README; registry "P3.1 LAUNCHED" 17:25Z and the P3 plan of record 16:20Z), a NOMINATED
read makes **the Thinking system (budget 3,072 / cap 4,096 / `drop-reasoning-v1`) the SLURP lock candidate v3.0**,
replicated on Fold B and DEV; ruling 304 locks those decoding knobs. Nothing more follows from the read itself. The
coordinator's registered sequence:

1. **NX-T R1**, the per-node thinking-policy column on the Thinking base (ruling 304: which nodes need thinking at all;
   arms both-on, both-on-twin, perception-off, solver-off, both-off on TRAIN Fold B, n = 1,080; package
   `docs/readiness/2026-10-13-slurp-nxt-r1-thinking-policy-fold-b-v1/`), built and merged and HELD behind P3.1 (registry
   20:05Z). It is the first node-level round of the SLURP training-free optimisation on the Thinking base that ruling 307
   puts before the carrier baselines (P3.2 / P3.3) and the SOTA redo (P3.5).
2. **The successor-3 test read** under the allowance signed 2026-10-13 (ruling 301 A,
   `docs/receipts/owner/2026-10-13-slurp-test-sample-allowance-successor-3.json`): the Thinking system lock arm only on the
   3,010-row sample, comparator the sealed successor-2 v2.2 test read, declared twin offset = this read's DEV twin offset
   (no in-chain replicate on the test sample; the limitation is stated in that read).

Each step needs its own registration and countersignature; this note authorises nothing.

## 8. Caveats

- **DEV-2000-ADDED development numbers.** Decision 28: DEV numbers are development numbers, never a test claim. The
  roster was already exposed by earlier cells (B6, PLANr, CELL-3, ROLL-3, A2, NX R5 composed and the offline v4 / v4g
  reads; exposure-ledger rows), though never to the Thinking core.
- **The Instruct comparator is a different flight.** d_system is cross-flight: the Instruct NX R5 composed column flew
  at study commit `9a0a3384b` on another session and day; the twin measures same-session noise only. The verdict rests on
  the CI95 lower bound against the twin offset, with the 2.5 pp bar covering session drift; d_system's CI lower bound
  (+5.46) is 2.2 times the bar (derived).
- **Intent attribution.** The twin's intent offset is resolved above zero (+1.60 [+0.60, +2.67]); the intent d_system
  lower bound (+1.00) sits below it, so the intent gain over the Instruct system is within same-core A/A variability.
  Only the intent guard holds as a finding.
- **No bare Thinking core on DEV.** The orientation column is the bare Instruct core, so no transfer share of a bare
  Thinking delta can be computed on this roster (268-B: 60.1 % on Fold B).
- **The budget binds.** Forced closes hit 15.8-17.4 % of Perception and 45.7-47.3 % of Solver contacts (31.6 % of all
  lock contacts, derived). What a larger budget, or no thinking on one node, would buy is unmeasured here (NX-T R1 asks
  the second question).
- **Small scenarios.** Three scenarios have fewer than 10 rows and one has 20; scenario-level signs there are not
  evidence. Five Fold B scenarios (alarm, audio, cooking, music, takeaway) are absent from this roster's per-scenario
  table.
- **One core, one encoder.** "Thinking core" means the Thinking decoder with its own audio tower and its own packets;
  this read cannot separate the two.
- **Twin as a separate cell.** The in-row c3 twin could not be compiled (package prerequisite 3); the twin is a second
  request-identical c2 pass, which doubles the per-row cost of the control.

## 9. What is NOT claimed

No benefit claim (`claims_benefit` false on every cell), no admission and no lock by this read: the lock candidate
v3.0 is a registry consequence of the preregistered rule, not a claim of this note. No test or held-out claim, no claim
on Audio2Tool or Earnings, no superiority or SOTA claim (285 stays deferred until the Thinking base is locked), no
generalisation claim and no paper-scale claim. No claim that the Thinking system is the best configuration of the
Thinking core: the system was carried over unchanged from the Instruct core. No claim about the content of the
reasoning, which is neither stored nor read (decision 286). No attribution of the intent gain beyond the guard. The
299 A direction is a direction for engineering work, not evidence of a benefit.

## 10. Records read

- Read: `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-SYSTEM-THINKING-CORE-DEV2000-ADDED-READ-V1/{read.json, README.md,
  smoke-decode-cost.json}`. Sealed hashes in `read.json`: lock scores `4452a573...`, outputs `52b0367c...`, manifest
  `3dff6014...`, trace `d897a3cd...`; aa scores `6f7bd0fa...`, outputs `7d43f045...`, manifest `beb7f340...`, trace
  `bab6a4a1...`; Instruct lock scores `281b9ab4...`; bare Instruct scores `847d932b...`.
- Package: `docs/readiness/2026-10-13-slurp-system-thinking-core-dev2000-added-v1/{README.md, registered-facts-v1.json,
  analysis-recipe-v1.json}`.
- Registry: `docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`, sections "P3 programme under decision
  299 A" (16:20Z), "P3.1 LAUNCHED" (17:25Z), "Owner rulings 301-306 and the priority correction 307" (17:40Z) and "NX-T
  R1 built and merged, HELD behind P3.1" (20:05Z).
- Exposure ledger: the smoke, lock, aa (CONSUMED notes) and READ rows (countersigned 2026-10-14T11:44:45Z) as of master
  `8132badd8`.
- Precedent: `docs/results/2026-10-13-slurp-268b-thinking-system-fold-b-read.md` (Fold B +7.15 / +2.31).

**Not verified here.**

- Wall-clock start and end of each arm: the files read give seal times only; the wall spans in section 2 are upper
  bounds from seal-to-seal intervals.
- GPU-active hours from the monitor; only summed latency is given.
- The reader's 299 block note says "TRAIN Fold B": a carried-over string, not checked against the reader source; the
  block's numbers match the DEV contrast.
- No registry section records the P3.1 READ as of master `8132badd8`; the NOMINATED word is taken from `read.json`,
  `README.md` and the commit subject of `8132badd8`.
