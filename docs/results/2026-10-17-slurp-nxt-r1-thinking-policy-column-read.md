# NX-T R1, the per-node thinking-policy column on the Thinking core (TRAIN Fold B, n = 1,080): Solver NEEDS-THINKING (SLU-F1 -7.11 [-8.97, -5.25]); Perception NO-RESOLVED-LOSS (-0.19 [-1.69, +1.29]) at 55 % of the row cost, without the extra word NOT-NEEDED-AT-THE-FLOOR; both-off NEEDS-THINKING (-9.18); development numbers, claims_benefit false

Read 2026-10-17 by Claude Opus 5.5 (results-note agent, on the coordinator's brief, Fable 5.1) in the worktree
`opus/nxt1-results-note` (base master `2b277fa3a`). Model-free: this note opened no model, server, encoder, embedder,
tokenizer, scorer or GPU, and wrote nothing under the data root. It reads the aggregate files of the registered read
`SAEA-SLURP-NXT-R1-THINKING-POLICY-FOLD-B-READ-V1` (`read.json`, its `README.md`, and `columns/score-summary.json` for the
per-arm official TP / FP / FN), the registration package
`docs/readiness/2026-10-13-slurp-nxt-r1-thinking-policy-fold-b-v1/`, its preregistration, the reader
`scripts/analysis/slurp_nxt_thinking_policy_column_read.py`, the family `scripts/flights/nx/nxt_r1_family.py`, the
exposure-ledger rows of cell NXT-R1 and the registry sections named in section 10. It opened no per-row output, score,
trace or checkpoint content. No utterance text, transcript, gold value, slot filler, model output or reasoning text was
printed or persisted; only counts, rates, pp, CIs, ids and hashes appear. Numbers marked "derived" are ratios, sums or
differences of numbers printed in those files.

**Status (verbatim from `read.json`): "PREREGISTERED-READ (development numbers; never a test claim; claims_benefit false)".**
This is a per-node ATTRIBUTION read on the selection fold, not a benefit claim, an admission or a lock (owner decisions 28,
86, 151, 301). The node words are the reader's, fixed at registration: **NEEDS-THINKING / NO-RESOLVED-LOSS / GAIN**, with
the extra word **NOT-NEEDED-AT-THE-FLOOR** attached to a NO-RESOLVED-LOSS arm only when both decision-190 floors hold.

## 0. Answer in eight lines

1. **Solver: NEEDS-THINKING.** Turning the Solver's reasoning off (perception thinking, solver no-think) costs SLU-F1 **-7.11 pp [-8.97, -5.25]** and intent **-1.94 [-3.33, -0.56]** against the delivering both-on arm (72.35 SLU / 85.74 intent).
2. **Perception: NO-RESOLVED-LOSS.** Turning Perception's reasoning off costs SLU-F1 **-0.19 [-1.69, +1.29]** and intent **-0.46 [-1.76, +0.83]**, at 60.7 s per row against 110.0 s (cost 0.55 of a both-on row). The reader did **not** attach NOT-NEEDED-AT-THE-FLOOR: the SLU lower bound -1.69 is under -1.49 and the intent lower bound -1.76 is under -0.65 (section 2). The registry entry of 10:37Z reads the extra word as awarded; the reader's own output says otherwise (`node_words.words.perception-off.extra_word` = null).
3. **Both nodes off: NEEDS-THINKING**, SLU **-9.18 [-11.24, -7.14]**, intent **-3.70 [-5.37, -2.04]**, at 6.4 s per row. The single-node losses add to 7.30 pp (derived) against 9.18 for both; the Solver arm carries 77 % of the both-off SLU loss (derived).
4. **In-flight A/A twin:** SLU **-0.12 [-1.44, +1.24]**, intent **0.00 [-0.93, +0.93]** (12 saves / 12 harms). |o| = 0.12 pp, the null the words are judged against; the external 268-B cross-flight twin offset (+1.15 SLU / -0.09 intent) is reported beside it and is not used in a word.
5. **Where the Solver loss sits (derived from the official counts):** solver-off minus both-on is TP -98, FP **+279.9**, FN +93.9 in the pooled counts behind official SLU-F1; exact entities 628 / 404 / 316 -> 585 / 540 / 359 (TP / FP / FN). The no-think Solver mostly adds false slot predictions. Perception-off moves the counts by TP -6, FP -4.5, FN +11.5.
6. **Decode, measured on the 51 rec2-flown rows only** (`arms_nodes.*.*.contacts` = 51): the thinking Solver at budget 3,072 forced-closes on **19 / 51** (both-on), **20 / 51** (twin) and **16 / 51** (perception-off) contacts, p90 completion 3,128-3,129 tokens; Perception forced closes 1-2 / 51. The no-think Solver answers in 26.2 tokens / 3.62 s mean (both-off) against 1,919.6 tokens / 62.21 s for the thinking Solver (both-on). 0 empty, 0 malformed JSON, 0 think markers and 0 reasoning characters on every no-think node; 0 reasoning leaks in the 1,080 delivered answers.
7. **One absent column:** the solver-off arm's no-think Solver ended on `finish_reason = length` at its 1,024-token cap on one flown row (`absent_reasons` `finite-completion:length` 1), scored as the canonical empty answer for that arm and counted, not fatal, under the merged fix `bac0bd551` (merge `60134738e`).
8. **History:** first attempt killed by a Windows Update restart (no trace; rec1 re-flown whole, ruling 309); rec1 stopped after 1,029 complete rows on the both-off arm's finite completion (harness defect); rec2 (ruling 320 B, mode-A resume) kept 1,029 rows and flew 51 (510 contacts), sealed 2026-10-17. The coordinator's R2 arm table is `perception-off-solver-3072` (the same-roster replicate) and `solver-2048`, registered at `2b277fa3a`.

## 1. Inputs, identities and the flight history

| item | value |
| --- | --- |
| cell | `slurp-native-stage3-nxt-r1-thinking-policy-fold-b-v1` (+ smoke `...-smoke-4-v1`); generation run `SAEA-SLURP-STAGE3-NXT-R1-THINKING-POLICY-FOLD-B-V1`, attempt `attempt-slurp-native-stage3-nxt-r1-thinking-policy-fold-b-generation-rec2-v1`; FIT run `SAEA-SLURP-STAGE3-NXT-R1-THINKING-POLICY-FOLD-B-FIT-REC2-V1`; read run `SAEA-SLURP-NXT-R1-THINKING-POLICY-FOLD-B-READ-V1` (recipe `slurp-nxt-r1-thinking-policy-fold-b-read-v1`) |
| system | the 268-B Thinking lock cell (lock v2.2, plain review-off COMP-1b module graph) with exactly one addition, the Perception `thinking_variants` block (receipt schema `saea-perception-branch-arms-v5`); program `phase-native-module-v1-c10` (10 = 2 + 2 x (5 - 1) contacts per row) |
| core and session | Qwen3-Omni-30B-A3B-Thinking Q4_K_M; model fragment `q4km-thinking-mmproj-free-slurp-module-fold-b-np4-ctx24k-budget3072-max4096-v1`; session `serving-slurp-thinking-module-fold-b-np4-budget3072-max4096-v1` (swap target `think-budget-np4`, 4 slots); its own Thinking packets of Fold B |
| thinking knobs | a thinking node: reasoning budget 3,072 + answer reserve 1,024 = completion cap 4,096, `drop-reasoning-v1`, temperature 0, seed 20260913, the registered forced-close message; a no-think node: `chat_template_kwargs` `{"enable_thinking": false}`, `max_tokens` 1,024, no budget |
| arms (declared order, delivering last) | `perception-off` (no-think / think), `solver-off` (think / no-think), `both-off` (no-think / no-think), `both-on-twin` (request-identical A/A copy of both-on), `both-on` (DELIVERING, the 268-B lock form). Shared by every arm: evidence, templates, QueryState, speech packet, knowledge supply, roster, model fragment, session. Not shared: each arm's Solver prompt carries that arm's own Perception note (independent chains) |
| roster | `SLURP-EVO-FOLD-B-V2`, `docs/receipts/rosters/slurp-evo-fold-b-v2.json` sha256 `47b89b9e...`, split identity `4407794c4a5d2e8883d93fdf242deb33c0987405d62e05a7d8416f5251a3484a`, 1,080 rows, 18 scenarios x 60 |
| scorer | `slurp-slu-official-train` (the pinned official `evaluate.py`); one complete official scoring per arm column (5 scorer jobs; `score-summary.json` `contacts.scorer` = 5); 0 scorer parse failures on every arm |
| resampling | paired utterance-cluster bootstrap, 10,000 draws, seed 20261013, CI95 |
| seal | rec2 generation manifest sha256 `a1912fa72682e86a92b2427084d297e0054a31e97b90e932659893856d334cd4`; outputs `c4cc81b74a6868db7d4ea63d304146cf4ce0da6330b4457c002e8dcd6ee249c4`; trace `38436d3f472fec770ef780ad69de038818d349b59f442817844dc1121d7d7299`; resume block kept 1,029 / flown 51 / partial 0, kept-id hash `461092f7...`, predecessor trace `3238cd8aedb50c8a142b15e321070ffc7cf2cd055088fdcb0aee83d8a0895835` |
| exposure | rec2 generation row: CONSUMED (sealed), 510 contacts, 1,464.7 speech-audio seconds, 4.83 summed call-latency hours, manifest COMPLETED, attempt FINALIZED, study commit `e4092610b`; run-cumulative caps 28,782 calls / 83,877 s; ceiling 41.4 GPU-h. READ row countersigned 2026-10-17T10:25:09Z |

**Flight history (from the registry and the package README; times UTC).**

| attempt | flight commit | what happened | spend (attempt record) |
| --- | --- | --- | --- |
| smoke-4 (`...-smoke-4-generation-v1`) | `37e177e3e` | sealed 2026-10-14 12:16Z, 40 contacts; every no-think node 0 reasoning characters, 0 markers, 0 empty, 0 malformed JSON; sign-off marker 12:18:33Z | 40 contacts |
| first column attempt (`...-generation-v1`) | `37e177e3e` | opened 12:18:45Z; killed by a Windows Update forced restart (System event log 1074, 15:29Z and 15:33Z). The trace sink buffered until the seal, so no trace existed and nothing could be replayed | 1,204 calls / 3,298.26 s; state OPENED |
| rec1 (`...-generation-rec1-v1`, ruling 309: systematic rectification; the cell's single recovery) | `8f9d8e1ee` | re-flown whole from 2026-10-14T17:14:43Z with per-row checkpoints; stopped 2026-10-15T22:33:00Z: the both-off arm's no-think Solver contact ended on `finish_reason = length` at the 1,024 cap, `FrozenCoreRoleFiniteCompletionError` left the branch fan-out before the twin and the delivering arm ran, and the level-2 fold raised `RailsRunnerError: perception branch 'both-off' sealed no level-2 Solver column`. The first such event in 2,058 earlier no-think Solver contacts (longest 66 tokens). 1,029 rows complete; the failing row's records were never flushed | 10,298 calls / 30,101.2 s; ABORTED |
| harness fix | `bac0bd551` (merged `60134738e`) | a finite completion on a NON-delivering branch is recorded as `solver_absent` + `absent_reason`, the fan-out continues, the renderer scores the column as the canonical empty answer, the readers count `absent_rows`; a finite completion on the DELIVERING arm still aborts by design | -- |
| rec2 (`...-generation-rec2-v1`, ruling 320 B: explicit owner exception to the one-recovery rule) | `e4092610b` | mode-A trace replay (mode B refused the `rails/runner.py` change): resume replay gate 1,029 checked / 0 failing / 0 sealed twice; attempt opened 09:06Z; 51 rows flown (the failing row among them), 510 contacts; sealed 10:23:53Z per the registry (10:22:16Z per the exposure-ledger closure text); then the column scorer refused once on a custody-hash check (request ids repeat across attempts; fixed `7df5c1cec` + test `4bba43420`), official column scoring 10:33Z, read 10:34Z | 510 contacts, 4.83 summed latency hours |

The rec1 STOP heading in the registry says "at row 1,031 of 1,080"; the root-cause section written an hour later (2026-10-15
23:55Z) corrects the count to 1,029 complete rows, 10,298 = 1,029 x 10 + 8 contacts, with the failing row the 1,030th.
This note uses the corrected count, which the package, the ledger row and the read's resume block all carry.

## 2. Definitions and the word rule

- **Contrast.** Each candidate arm and the twin minus the delivering `both-on` arm, paired per row on the same 1,080 rows, same flight. PRIMARY: official pooled SLU-F1 (natural mixture). SECONDARY: intent accuracy (`scenario_action` exact).
- **Null.** The in-flight twin offset |o| = |both-on-twin - both-on| on SLU = **0.1207 pp** (point -0.1207).
- **Words (reader `node_words`, lines 273-298, quoting the module docstring).** NEEDS-THINKING iff the SLU CI95 upper bound < -|o|; GAIN iff the SLU CI95 lower bound > |o|; otherwise NO-RESOLVED-LOSS. The extra word NOT-NEEDED-AT-THE-FLOOR is attached iff the word is NO-RESOLVED-LOSS **and** the SLU CI95 lower bound >= -1.49 pp **and** the intent CI95 lower bound >= -0.65 pp (`FLOOR_SLU_PP, FLOOR_INTENT_PP = 1.49, 0.65`, decision 190 node-column floors at n = 1,080).
- **Applying it.** solver-off: upper bound -5.25 < -0.12 -> NEEDS-THINKING. both-off: -7.14 < -0.12 -> NEEDS-THINKING. perception-off: upper bound +1.29 is not below -0.12, lower bound -1.69 is not above +0.12 -> NO-RESOLVED-LOSS; extra word: -1.69 < -1.49 (fails) and -1.76 < -0.65 (fails) -> **not attached**. `read.json` agrees: `node_words.words.perception-off.extra_word` is null for that arm, and the top-level key `extra_word` = "NOT-NEEDED-AT-THE-FLOOR" is the vocabulary constant the reader writes on every read (`read_stage`: `"extra_word": EXTRA_WORD`), not a verdict.
- **What the floors mean here.** The design was declared to resolve 1.49 pp SLU / 0.65 pp intent per node. The perception-off interval half-widths are 1.49 SLU and 1.30 intent (`ci95_half_width_pp`), so a Perception loss of up to 1.69 pp SLU or 1.76 pp intent is inside this read's interval. "No resolved loss" is what the read shows; "no loss at the floor" is not.

## 3. The contrast

| arm | Perception / Solver | SLU-F1 % | SLU delta pp [CI95] | intent % | intent delta pp [CI95] | intent saves / harms / ties | absent rows | s per row | GPU-h per 1,080-row pass | cost in both-on rows (registered) | word |
| --- | --- | ---: | --- | ---: | --- | --- | ---: | ---: | ---: | --- | --- |
| both-on (delivering) | think / think | 72.35 | -- | 85.74 | -- | -- | 0 | 110.0 | 8.25 | 1.00 (1.0) | -- |
| both-on-twin | think / think | 72.23 | -0.12 [-1.44, +1.24] | 85.74 | +0.00 [-0.93, +0.93] | 12 / 12 / 1,056 | 0 | 112.5 | 8.44 | 1.02 (1.0) | A/A twin |
| perception-off | no-think / think | 72.16 | **-0.19 [-1.69, +1.29]** | 85.28 | -0.46 [-1.76, +0.83] | 24 / 29 / 1,027 | 0 | 60.7 | 4.55 | 0.55 (0.6) | **NO-RESOLVED-LOSS** |
| solver-off | think / no-think | 65.24 | **-7.11 [-8.97, -5.25]** | 83.80 | -1.94 [-3.33, -0.56] | 18 / 39 / 1,023 | 1 | 51.3 | 3.84 | 0.47 (0.6) | **NEEDS-THINKING** |
| both-off | no-think / no-think | 63.16 | -9.18 [-11.24, -7.14] | 82.04 | -3.70 [-5.37, -2.04] | 22 / 62 / 996 | 0 | 6.4 | 0.48 | 0.06 (0.05) | NEEDS-THINKING |

Full precision (`contrast.versus_delivering`): twin SLU -0.1207 [-1.4419, +1.2357], intent 0.0000 [-0.9259, +0.9259];
perception-off SLU -0.1899 [-1.6930, +1.2906], intent -0.4630 [-1.7593, +0.8333]; solver-off SLU -7.1067 [-8.9698,
-5.2541], intent -1.9444 [-3.3333, -0.5556]; both-off SLU -9.1844 [-11.2437, -7.1405], intent -3.7037 [-5.3704, -2.0370].
The s/row, GPU-h and cost columns are measured on the 51 flown rows (section 5).

**Official counts behind the levels** (`columns/score-summary.json`, `official.raw`; FP and FN of SLU-F1 carry
`evaluate.py`'s fractional distance credits):

| arm | SLU-F1 TP | SLU-F1 FP | SLU-F1 FN | entities (exact) TP / FP / FN | entity span-F1 % | intent correct / 1,080 | scenario % | action % |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| both-on | 1,588 | 694.94 | 518.94 | 628 / 404 / 316 | 63.56 | 926 | 89.72 | 86.48 |
| both-on-twin | 1,588 | 697.61 | 523.61 | 631 / 400 / 313 | 63.90 | 926 | 90.00 | 86.57 |
| perception-off | 1,582 | 690.40 | 530.40 | 622 / 402 / 322 | 63.21 | 921 | 89.35 | 85.93 |
| solver-off | 1,490 | 974.83 | 612.83 | 585 / 540 / 359 | 56.55 | 905 | 88.24 | 84.81 |
| both-off | 1,466 | 1,061.95 | 647.95 | 567 / 584 / 377 | 54.13 | 886 | 87.41 | 83.15 |

Derived, arm minus both-on: twin TP 0 / FP +2.67 / FN +4.67; perception-off TP -6 / FP -4.54 / FN +11.46; solver-off TP
-98 / FP **+279.88** / FN +93.88; both-off TP -122 / FP **+367.01** / FN +129.01. The Solver's reasoning buys mostly
precision: without it the Solver emits about 280 more (weighted) false slot predictions on 1,080 rows. Perception-off
moves every count by less than 12 (FN +11.46 against the twin's +4.67); this note does not test that difference.

## 4. Decode statistics per arm and node (the 51 rec2-flown rows only)

Every `arms_nodes.<arm>.<node>.contacts` and `wire_records` value is **51**: the reader takes per-contact statistics from
the sealed trace of the attempt it reads, and the rec2 trace holds only the 51 flown rows' 510 contacts (51 x 5 arms x 2
nodes). The 1,029 kept rows' contacts live in the rec1 trace, which the decode tables do not read. These tables are
therefore a 51-row sample (the failing rec1 row included), not the column's 1,080 rows.

| arm | node | mode | contacts | cap | completion tokens mean / p50 / p90 / p99 / max | finish reasons | cap hits | forced closes | empty / no JSON / markers | contacts with reasoning chars | reasoning chars mean | prompt tokens mean | s per contact mean / p50 / p99 |
| --- | --- | --- | ---: | ---: | --- | --- | ---: | ---: | --- | ---: | ---: | ---: | --- |
| both-on | perception | think | 51 | 4,096 | 1,575.5 / 1,331 / 2,425 / 2,864.5 / 3,128 | stop 51 | 0 | 1 | 0 / 0 / 0 | 51 | 6,943 | 3,574.9 | 47.82 / 44.05 / 105.97 |
| both-on | solver | think | 51 | 4,096 | 1,919.6 / 1,693 / 3,128 / 3,130.5 / 3,131 | stop 51 | 0 | **19** | 0 / 0 / 0 | 51 | 7,980 | 9,153.4 | 62.21 / 47.49 / 123.81 |
| both-on-twin | perception | think | 51 | 4,096 | 1,608.4 / 1,447 / 2,463 / 3,133.5 / 3,137 | stop 51 | 0 | 2 | 0 / 0 / 0 | 51 | 7,071 | 3,574.9 | 47.28 / 42.22 / 94.21 |
| both-on-twin | solver | think | 51 | 4,096 | 1,897.4 / 2,023 / 3,129 / 3,136.0 / 3,139 | stop 51 | 0 | **20** | 0 / 0 / 0 | 51 | 7,817 | 9,153.4 | 65.20 / 66.73 / 127.76 |
| perception-off | perception | no-think | 51 | 1,024 | 91.6 / 91 / 95 / 107.5 / 108 | stop 51 | 0 | 0 | 0 / 0 / 0 | 0 | 0 | 3,578.9 | 3.47 / 3.17 / 8.75 |
| perception-off | solver | think | 51 | 4,096 | 1,557.0 / 989 / 3,128 / 3,130.5 / 3,131 | stop 51 | 0 | **16** | 0 / 0 / 0 | 51 | 6,555 | 11,378.8 | 57.25 / 39.52 / 128.23 |
| solver-off | perception | think | 51 | 4,096 | 1,599.6 / 1,421 / 2,506 / 3,148.0 / 3,166 | stop 51 | 0 | 2 | 0 / 0 / 0 | 51 | 6,987 | 3,574.9 | 47.86 / 41.42 / 98.89 |
| solver-off | solver | no-think | 51 | 1,024 | 45.4 / 23 / 35 / 533.5 / 1,024 | length 1, stop 50 | 1 | 0 | 0 / 0 / 0 | 0 | 0 | 9,136.3 | 3.40 / 2.53 / 23.49 |
| both-off | perception | no-think | 51 | 1,024 | 92.0 / 92 / 96 / 108.0 / 108 | stop 51 | 0 | 0 | 0 / 0 / 0 | 0 | 0 | 3,578.9 | 2.82 / 2.59 / 7.58 |
| both-off | solver | no-think | 51 | 1,024 | 26.2 / 23 / 35 / 45.0 / 47 | stop 51 | 0 | 0 | 0 / 0 / 0 | 0 | 0 | 11,397.0 | 3.62 / 3.60 / 6.68 |

Reading it plainly:

- **The thinking Solver is capacity-bound at 3,072.** Forced closes 19 / 51 (37 %, derived), 20 / 51 (39 %) and 16 / 51 (31 %) on the three arms whose Solver thinks; p90 completion sits at 3,128-3,129 tokens, 56-57 above the budget (derived: the forced-close message and the answer follow the budget). No contact reached the 4,096 cap. The 268-B note had 44-46 % Solver forced closes over 1,080 rows per arm; the 51-row sample here sits a little under that.
- **Perception reasons less and rarely hits the budget:** 1-2 / 51 forced closes, p50 1,331-1,447 tokens.
- **No-think works on the thinking-only checkpoint** (the package's prerequisite 1): every no-think node has 0 reasoning characters, 0 markers, 0 empty answers and 0 malformed JSON, as in the smoke. The one exception to `stop` is the solver-off Solver's single `length` finish at 1,024 tokens (cap hit 1, p99 533.5) -- the absent column of section 0, item 7. The both-off Solver, whose identical event stopped rec1, finished `stop` on all 51 flown rows, the failing row included (max 47 tokens).
- **Prompt length follows the upstream note:** a thinking-Perception arm's Solver prompt averages 9,136-9,153 tokens and a no-think-Perception arm's 11,379-11,397 (+2,225 to +2,261, derived), so the no-think Perception note is longer than the thinking one after `drop-reasoning-v1`. The read does not say why.

## 5. Throughput and cost

From the reader's `throughput` block: seconds per row = the arm's Perception plus Solver mean seconds per contact (the
51-row sample above); rows per minute at 4 slots; GPU-h per pass = 1,080 x s per row / 4 / 3,600 (slot-normalised).

| arm | s per row | rows per minute (4 slots) | cost in both-on rows | registered cost | GPU-h per 1,080-row pass |
| --- | ---: | ---: | ---: | ---: | ---: |
| both-on | 110.0 | 2.18 | 1.00 | 1.0 | 8.25 |
| both-on-twin | 112.5 | 2.13 | 1.02 | 1.0 | 8.44 |
| perception-off | 60.7 | 3.95 | **0.55** | 0.6 | **4.55** |
| solver-off | 51.3 | 4.68 | 0.47 | 0.6 | 3.84 |
| both-off | 6.4 | 37.26 | 0.06 | 0.05 | 0.48 |

Measured arm mix 3.10 both-on rows per row against the registered 3.25; one five-arm 1,080-row flight projects to 25.57
GPU-h at these seconds, against the registered 41.4 GPU-h ceiling (expected 31.8 at the registered 1.84 rows per
minute). The flights' own spend: the first attempt 1,204 calls / about 3 GPU-h (registry); rec1 10,298 calls over about
29.3 h of wall; rec2 510 contacts and 4.83 summed latency hours (about 1.2 slot-normalised GPU-h, derived). A 1,080-row
lock flight with Perception no-think would cost 4.55 against 8.25 GPU-h at these seconds (registry: "halves the row
cost").

## 6. Per scenario (18 scenarios x 60 rows; point deltas in pp vs both-on; no scenario CI in the read)

| scenario | n | SLU both-on % | SLU d twin | SLU d perception-off | SLU d solver-off | SLU d both-off | intent both-on % | intent d twin | intent d perception-off | intent d solver-off | intent d both-off |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| alarm | 60 | 72.04 | +1.98 | +3.09 | -6.24 | -13.54 | 90.00 | +0.00 | +0.00 | -1.67 | -3.33 |
| audio | 60 | 79.84 | +3.29 | -11.65 | -28.51 | -37.40 | 83.33 | -1.67 | +5.00 | -3.33 | -8.33 |
| calendar | 60 | 71.38 | +1.02 | +1.09 | -5.54 | -4.62 | 83.33 | -1.67 | -3.33 | +0.00 | +0.00 |
| cooking | 60 | 73.17 | +4.31 | -1.73 | -5.53 | -7.75 | 86.67 | +3.33 | +3.33 | +0.00 | +1.67 |
| datetime | 60 | 76.41 | +0.30 | +1.46 | -3.87 | -3.87 | 96.67 | -1.67 | -3.33 | +0.00 | -1.67 |
| email | 60 | 75.84 | -3.55 | +0.20 | -15.27 | -14.84 | 93.33 | +0.00 | +1.67 | +0.00 | +0.00 |
| general | 60 | 59.70 | -2.15 | -3.09 | -19.45 | -23.53 | 43.33 | -5.00 | +3.33 | -8.33 | -6.67 |
| iot | 60 | 79.09 | -4.62 | -3.75 | -6.37 | -12.25 | 90.00 | +1.67 | -3.33 | -5.00 | -10.00 |
| lists | 60 | 64.77 | +4.54 | -0.39 | -8.20 | -9.11 | 90.00 | +0.00 | +0.00 | -3.33 | -8.33 |
| music | 60 | 42.45 | +13.93 | +12.45 | -2.53 | -5.22 | 76.67 | +0.00 | +3.33 | +1.67 | -3.33 |
| news | 60 | 74.31 | -1.20 | -0.78 | -7.79 | -10.38 | 93.33 | -1.67 | -5.00 | -1.67 | -5.00 |
| play | 60 | 62.36 | -6.64 | -4.91 | -5.09 | -8.17 | 81.67 | +1.67 | -6.67 | -1.67 | -6.67 |
| qa | 60 | 76.44 | +0.15 | -2.19 | -9.17 | -10.03 | 88.33 | -1.67 | -1.67 | -6.67 | -5.00 |
| recommendation | 60 | 66.86 | -1.82 | +3.94 | -1.77 | -2.93 | 83.33 | +0.00 | +1.67 | +0.00 | -1.67 |
| social | 60 | 71.22 | -0.58 | +3.69 | -6.94 | -6.45 | 90.00 | +1.67 | +0.00 | -1.67 | -1.67 |
| takeaway | 60 | 71.13 | -3.32 | -1.21 | -10.29 | -7.12 | 86.67 | +1.67 | -1.67 | +0.00 | +1.67 |
| transport | 60 | 74.85 | +3.29 | +1.13 | +3.29 | -1.82 | 88.33 | +1.67 | -1.67 | -3.33 | -8.33 |
| weather | 60 | 85.02 | -0.26 | -3.04 | -9.25 | -12.97 | 98.33 | +1.67 | +0.00 | +0.00 | +0.00 |

**Weightings (SLU-F1 delta pp vs both-on).**

| arm | natural mixture (primary) | equal-scenario |
| --- | ---: | ---: |
| both-on-twin | -0.12 | +0.48 |
| perception-off | -0.19 | -0.32 |
| solver-off | -7.11 | -8.25 |
| both-off | -9.18 | -10.67 |

The equal-scenario weighting agrees in sign and order with the natural mixture on every arm. Counts (derived): SLU
deltas down / up in 9 / 9 scenarios for the twin, 10 / 8 for perception-off, 17 / 1 for solver-off (only transport up,
+3.29, equal to the twin's +3.29 there) and 18 / 0 for both-off. The twin's own per-scenario SLU deltas range from -6.64
(play) to +13.93 (music), so a single scenario's perception-off delta (from -11.65 in audio to +12.45 in music) is
within the swing the twin shows on 60 rows; only audio's -11.65 sits outside the twin's range, and this note does not
test it. The Solver loss is largest in audio (-28.51), general (-19.45) and email (-15.27).

## 7. What the read means, stated and not claimed

- **The Thinking system's gain lives at the Solver.** Taking the Solver's reasoning away costs 7.11 pp SLU-F1 and 1.94 pp intent with both intervals clear of the twin offset, and most of it is false slot predictions (section 3). Taking both nodes' reasoning away costs 9.18 pp, which is 1.29 pp under the 268-B Instruct-system level on the same roster if compared cross-flight (63.16 vs 64.45, derived; not a contrast) -- the no-think core on the same weights lands close to the Instruct system, as the registration expected (declared effect 7.15 pp; observed 9.18).
- **Perception's reasoning buys nothing this design resolves, at 55 % of the row cost.** perception-off is -0.19 [-1.69, +1.29] SLU and -0.46 [-1.76, +0.83] intent with 24 saves / 29 harms; a 1,080-row lock flight without Perception reasoning costs 4.55 instead of 8.25 GPU-h at the measured seconds. Because the extra word was not attached, the read does not show that any Perception loss is under the decision-190 floors; it shows only that none is resolved.
- **Solver reasoning is capacity-bound at the 3,072 budget**: 31-39 % forced closes on the 51-row sample, with p90 at the budget. The read cannot say whether a larger budget would help; it says the current budget is often exhausted.
- **What it does not mean:** no admission, no lock change, no benefit, generalisation or test claim; one roster, the selection fold; `claims_benefit` false.

## 8. Next (as the registry states it, 2026-10-17 10:37Z)

- **R2 arm table** (coordinator decision under the registered rule "R1's answer decides the arm table"; two candidates, no twin, decision 313 A): `perception-off-solver-3072` = {perception off, solver 3,072}, the same-roster REPLICATE of R1's cheapest no-loss form (if it reads CHEAPER-AT-NO-RESOLVED-LOSS it is the adoption candidate for the lock), and `solver-2048` = {perception 3,072, solver 2,048}, the one-node budget scan on the node that NEEDS thinking (cheaper direction only; the family clips budgets to [min, 3,072]). The default 1,536 / 2,048 both-node arms are dropped. Registered at `2b277fa3a` (`docs/readiness/2026-10-15-slurp-nxt-r2-thinking-budget-fold-b-v1/`: program `phase-native-module-v1-c6`, arm mix 2.46, expected 24.07 GPU-h, ceiling 31.3).
- **Owner item 323:** a Solver budget ABOVE 3,072 (e.g. 3,584 with answer reserve 512) is outside R2's registered range but is the direction the forced-close table points to; A: a one-arm R2b after R2 reads; B: fold it into the next node round.
- **Owner item 324:** adopt Perception no-think into the v3.0 lock candidate after the R2 replicate reads no loss (A), or require a Fold A confirm first (B; the coordinator recommends B: one 2-arm column, about 5 GPU-h, the lock rule of C0.6).
- **For the coordinator (this note's finding, not a registry statement):** the 10:37Z entry's heading and its line "Extra word NOT-NEEDED-AT-THE-FLOOR (Perception)" do not match the reader's output; the R2 package's prerequisite 1 keys the arm table on that extra word ("a node that reads NOT-NEEDED-AT-THE-FLOOR needs no budget scan"). The chosen table (a same-roster replicate of perception-off) is consistent with NO-RESOLVED-LOSS as well; item 324's adoption wording may want the corrected word.

## 9. Limitations

- **One roster, the selection fold.** n = 1,080 on TRAIN Fold B (`SLURP-EVO-FOLD-B-V2`), the fold the Thinking system was first read on (268-B). Development numbers only; no Fold A or DEV read of the node column exists.
- **The Perception interval is wider than the declared floors.** perception-off SLU CI95 lower bound -1.69 is below -1.49 and the intent lower bound -1.76 below -0.65; the reader therefore withheld NOT-NEEDED-AT-THE-FLOOR (section 2). The design resolves the Solver's loss, not the absence of a small Perception loss.
- **Attribution includes the downstream effect.** A non-delivering arm's Solver reads that arm's own Perception note (package prerequisite 2): perception-off measures Perception's thinking together with its effect on the Solver prompt (which is about 2,230 tokens longer, section 4).
- **Resume composition.** 1,029 of 1,080 rows were kept from the stopped rec1 attempt by mode-A trace replay and 51 were flown under rec2 at a different flight commit (`8f9d8e1ee` vs `e4092610b`) after the harness fix; the reader never separates kept and flown rows in a contrast. Every arm of a row was flown in the same attempt, so the pairing holds within each row.
- **Decode and throughput statistics are a 51-row sample** (section 4): forced-close rates, token counts, seconds per contact and the GPU-h projections come from the rec2-flown rows only.
- **One absent column.** The solver-off arm has 1 absent row (finite completion `length` at its 1,024 cap), scored zero for that arm. Its effect on the solver-off delta is bounded by one row of 1,080 and does not change the word.
- **The twin offset here vs the declared ones.** The in-flight twin reads -0.12 SLU / 0.00 intent (|o| = 0.12), much tighter than the external 268-B cross-flight offset (+1.15 SLU / -0.09 intent) the registration carried as the reference. The words use the in-flight value as registered; with |o| = 1.15 every word would be the same (solver-off and both-off upper bounds stay below -1.15; perception-off stays NO-RESOLVED-LOSS; derived).
- **Two recoveries.** rec2 is a second recovery under an explicit owner exception (ruling 320 B) to the package's one-recovery rule; the first attempt's 1,204 calls and rec1's 10,298 are spent and recorded but not read.

## 10. Pointers (sha256)

Analysis root `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-NXT-R1-THINKING-POLICY-FOLD-B-READ-V1/`:

| file | sha256 |
| --- | --- |
| `read.json` (schema `saea-nxt-r1-thinking-policy-column-read-v1`) | `36928d77639010548ee3680678d285cde11fe0c55084871b26b09df31d40f308` |
| `README.md` | `ec7e49ca0a30ba266923210187ecaedeca2d726ffe94896a453ec5bb7e8c3e47` |
| `columns/score-summary.json` | `798472e9c9fe5e0128bbac6befc463216cbfaa51621dc186a4be9e3af1c4f572` |
| `columns/render-manifest.json` | `64b136e887b9da56862984815799d35526c411160ee0788466c50bb7d403bf91` |
| `columns/arm-both-on-slurp-slu-official-train-scores.json` | `a30cfed828b449ae8747792873a80c1c3608793fd828f89e7d6ad3166f8c2c83` |
| `columns/arm-both-on-twin-slurp-slu-official-train-scores.json` | `a6767e0c3ff80bf09ffc4d0b27d036a9b90478a88489bea179c65cb04df6938c` |
| `columns/arm-perception-off-slurp-slu-official-train-scores.json` | `0ce88468bdbbc0ad9c93c132ce940885be94d9b6aad610adc7cc067e633f8080` |
| `columns/arm-solver-off-slurp-slu-official-train-scores.json` | `caa66587f3e64fc6f810d278b77122597d690f41306d93da0da85d27b3ab98cf` |
| `columns/arm-both-off-slurp-slu-official-train-scores.json` | `a2de04b60a2c0c44fc01792a3ddb78ef9b7488bde77590f3360000d6f7f07ee3` |

Repository (bytes at `2b277fa3a`):

| file | sha256 |
| --- | --- |
| `docs/readiness/2026-10-13-slurp-nxt-r1-thinking-policy-fold-b-v1/README.md` | `d59e64e5b15eb813436e6c5ca768e26817fac5932b3bf9a04efab95a5df63e70` |
| `.../analysis-recipe-v1.json` | `14df04b71b88415d7fd461c4c37d8bec5dd39ae96a1ee16054f46d326bb03c66` |
| `.../registered-facts-v1.json` | `5db426e364606d561ae4ed9f284ee77feae8460165ac63a9b01f123b4669ec6f` |
| `.../generation-plan-registered-rec2-v1.json` | `1146a0f7d6cd2ffde55d3950aebfb6ccfd4be9c473837608766b9f1932a8a6bb` |
| `.../protocol-registered-v1.json` | `b94a8924e1f122a932734c498c608dfd82dd6993d431b699eb7d000640afc87d` |
| `.../resume-replay-proof-rec2-v1.json` | `abff50155cc75fc8e3e96f326fc4f674502107592edea493ed140050160f4496` |
| `docs/readiness/2026-10-13-slurp-nxt-r1-thinking-policy-fold-b-v1-preregistration.md` | `76a6c24d1b45918463c16184e1ff171ee00e4e227e18e24e1c571a2ad840e97d` |
| `scripts/analysis/slurp_nxt_thinking_policy_column_read.py` | `752f1a6d50f31ffc029fd1e4f902fe73abbae480173eab434dcb1bfba52e278b` |
| `scripts/flights/nx/nxt_r1_family.py` | `c27dc8ad81a7df46c39b33385332ac83d0f78ed2cdaaf3ce8b95b11b439ac5c9` |
| `docs/receipts/rosters/slurp-evo-fold-b-v2.json` | `47b89b9e33b1aed553ad94a1819acba6ac8837130ca546c33219d91a1ab944a8` |

Registry `docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`, sections "NX-T R1 built and merged, HELD
behind P3.1" (2026-10-13 20:05Z), "NX-T R1 LAUNCHED" (2026-10-14 12:10Z), "NX-T R1 smoke signed off" (12:20Z),
"INCIDENT: Windows Update forced restart killed the NX-T R1 column" (15:55Z), "Owner rulings 308-311", "NX-T R1 rec1
column RE-FLYING" (17:20Z), "NX-T R1 rec1 column STOPPED at row 1,031 of 1,080" (2026-10-15 22:50Z), "NX-T R1 stop: root
cause, harness fix merged" (23:55Z), "Owner ruling 320 B" (2026-10-16), "NX-T R1 rec2 (320 B) registered in flight"
(2026-10-17 05:05Z), "NX-T R1 rec2 (320 B) FLYING since 09:05Z" (09:11Z) and "NX-T R1 READ" (10:37Z). Exposure-ledger
section "Cell NXT-R1" and its rec1 / rec2 recovery sections. Related notes:
`docs/results/2026-10-13-slurp-268b-thinking-system-fold-b-read.md` (the 268-B Fold B read and the external twin offset),
`docs/results/2026-10-14-slurp-p31-thinking-system-dev2000-added-read.md`,
`docs/results/2026-10-17-slurp-successor3-thinking-system-test-sample-read.md`.

**Not verified here.**

- The rec2 seal time: the registry says 10:23:53Z, the exposure-ledger closure text says 10:22:16Z; this note did not open the manifest to settle it.
- The first attempt's "about 3 GPU-h" and rec1's "29.3 h" are the registry's figures; the attempt records were not opened.
- Which flown row the solver-off absent column fell on, and whether it is the row that stopped rec1, is not in the aggregate files.
