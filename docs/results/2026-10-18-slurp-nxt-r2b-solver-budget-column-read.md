# NX-T R2b, the Solver reasoning-budget raise on the Thinking core (TRAIN Fold B, n = 1,080): solver-6144 NEEDS-NO-MORE-BUDGET (SLU-F1 -0.81 [-2.19, +0.57], intent -0.56 [-1.67, +0.56]) at 1.37x the row cost; the Solver still forced-closes 37.8 % of contacts at 6,144 against 40.1 % at 3,072; development numbers, claims_benefit false

Read 2026-10-18 by Claude Opus 5.5 (results-note agent, on the coordinator's brief) in the worktree branch
`worktree-agent-ab650c2c3204ec293` (base master `310e23ae0`). Model-free: this note opened no model, server, encoder,
embedder, tokenizer, scorer or GPU, and wrote nothing under the data root. It reads the aggregate files of the registered
read `SAEA-SLURP-NXT-R2B-SOLVER-BUDGET-FOLD-B-READ-V1` (`read.json`, its `README.md`, `columns/score-summary.json`,
`columns/render-manifest.json` and the two score receipts), the registration package
`docs/readiness/2026-10-17-slurp-nxt-r2b-solver-budget-fold-b-v1/`, the reader
`scripts/analysis/slurp_nxt_r2b_solver_budget_column_read.py` (a thin entry over
`scripts/analysis/slurp_nxt_thinking_budget_column_read.py`), the exposure-ledger rows of cell NXT-R2B and the registry
sections named in section 8. For the cross-flight agreement table (section 2.6) it opened the `per_sample` arrays of the
official column score files of this read and of the NX-T R1 read and counted rows by `sample_id` and numeric score flags
only. No utterance text, transcript, gold value, slot filler, model output or reasoning text was read, printed or persisted;
only counts, rates, pp, CIs, ids and hashes appear. Numbers marked "derived" are ratios, sums or differences of numbers
printed in those files.

**Status: DESCRIPTIVE, development numbers on TRAIN Fold B (`SLURP-EVO-FOLD-B-V2`, n = 1,080, discovery role; owner
decisions 28 and 86). Never a test claim. `claims_benefit` is false.** `read.json` `status` verbatim: "PREREGISTERED-READ
(development numbers; never a test claim; claims_benefit false)". This is a one-node budget column on the selection fold
(owner rulings 323 and 325 A), not an admission, a lock or a benefit claim (`analysis-recipe-v1.json`, `claim_boundary`:
"No benefit, system-level, superiority, generalisation, held-out, confirmatory or paper-scale claim.").

## 0. Answer in five lines

1. **Word: NEEDS-NO-MORE-BUDGET.** Raising the Solver's reasoning budget 3,072 -> 6,144 (cap 4,096 -> 7,168) moves SLU-F1 **-0.81 pp [-2.19, +0.57]** and intent **-0.56 pp [-1.67, +0.56]** (17 saves / 23 harms) against the delivering lock form (72.74 SLU / 85.37 intent -> 71.93 / 84.81); no resolved gain, no resolved harm, the point estimate inside the declared A/A offset |o| = 1.15 pp.
2. **Forced closes persist at the doubled budget:** the Solver hits its budget on **433 / 1,080 (40.1 %)** contacts at 3,072 and on **408 / 1,080 (37.8 %)** at 6,144; mean completion 2,018 -> 3,292 tokens (+63 %, derived), p90 3,131 -> 6,203 (budget + 59 both times), 0 cap hits on either arm. Doubling the budget let about 25 net contacts finish on their own; the rest ran to the new budget.
3. **Cost: 1.37x a delivering row** (169.2 vs 123.1 s per row; 12.69 vs 9.23 GPU-h per 1,080-row lock flight) for no resolved score change; the Solver contact itself takes 108.95 vs 64.10 s (1.70x, derived).
4. **The Perception node, identical request form in both arms, is an in-flight A/A-like readout:** forced closes **199 vs 213** (18.4 % vs 19.7 %), mean completion 2,015 vs 2,044 tokens, 58.96 vs 60.24 s per contact, identical mean prompt (3,589.6 tokens). The Solver's forced-close drop (-25) is under twice this same-form swing (+14).
5. **The delivering arm reproduces R1 both-on cross-flight** (72.74 / 85.37 vs 72.35 / 85.74; 48 intent-discordant rows vs 24 for R1's in-flight twin); every lock-form reading on this roster now spans 71.61-72.75 SLU. Consequence: the Solver budget of the v3.0 lock candidate stays 3,072 (ruling 323), and the non-terminating 38-40 % of Solver reasoning is a target for the USE-node instruction-template round (ruling 326 A), not for budget.

## 1. Identities

| item | value |
| --- | --- |
| cells | smoke `slurp-native-stage3-nxt-r2b-solver-budget-fold-b-smoke-4-v1` (run `SAEA-SLURP-STAGE3-NXT-R2B-SOLVER-BUDGET-FOLD-B-SMOKE-4-V1`); column `slurp-native-stage3-nxt-r2b-solver-budget-fold-b-v1` (run `SAEA-SLURP-STAGE3-NXT-R2B-SOLVER-BUDGET-FOLD-B-V1`, attempt `attempt-slurp-native-stage3-nxt-r2b-solver-budget-fold-b-generation-v1`, FIT run `...-FOLD-B-FIT-V1`); read run `SAEA-SLURP-NXT-R2B-SOLVER-BUDGET-FOLD-B-READ-V1`, recipe `slurp-nxt-r2b-solver-budget-fold-b-read-v1` |
| authority | owner rulings 323 and 325 A (2026-10-17), 313 A (2026-10-14: no twin, declared offset), 304/307; registered 2026-10-17T13:47:05Z, root countersigned 13:47:08Z at study commit `c878ec3d1` |
| system | the 268-B Thinking lock cell (lock v2.2, plain review-off COMP-1b module graph) plus the Perception `thinking_variants` block and a cell-level thinking policy; program `phase-native-module-v1-c4` (4 contacts per row: 2 arms x Perception + Solver) |
| core and session | Qwen3-Omni-30B-A3B-Thinking Q4_K_M, decoder-only build `04ccc72a`; fragment `q4km-thinking-mmproj-free-slurp-module-fold-b-np4-ctx24k-budget3072-max7168-v1`; session `serving-slurp-thinking-module-fold-b-np4-budget3072-max7168-v1` (swap target `think-budget7168-np4`, 4 slots x 24,576 tokens, q8_0 KV, `--reasoning-format deepseek`) |
| arms (declared order, delivering last; no twin) | `solver-6144`: Perception 3,072 / cap 4,096, Solver **6,144 / cap 7,168**; `budget-3072` (DELIVERING, the 268-B lock form): both nodes 3,072 / cap 4,096. Both: `drop-reasoning-v1`, temperature 0, seed 20260913, the registered forced-close message. Not shared: each arm's Solver reads its own arm's Perception note |
| roster | `SLURP-EVO-FOLD-B-V2`, `docs/receipts/rosters/slurp-evo-fold-b-v2.json` sha256 `47b89b9e33b1aed553ad94a1819acba6ac8837130ca546c33219d91a1ab944a8`, split identity `4407794c4a5d2e8883d93fdf242deb33c0987405d62e05a7d8416f5251a3484a`, 1,080 rows, 18 scenarios x 60; roster-ids sha256 `ba605650...` (score receipts) |
| scorer | `slurp-slu-official-train` (pinned official `evaluate.py`), one complete scoring per arm column (`score-summary.json` `contacts.scorer` = 2); 0 parse failures, 0 absent rows, 0 empty, 0 no-JSON, 0 reasoning leaks in 1,080 delivered answers |
| resampling | paired utterance-cluster bootstrap, 10,000 draws, seed 20261015, CI95 |
| seal | manifest sha256 `00380c2f6128c4f0aa521fddf3726838e1d3994dca3c4bbeaba22a98852a4588`; outputs `3fa94a4a225be3114808dae2a24045610fefa90ae32a374e37e3ba27fe034a39`; trace `62603d0272d5b2010240777a2e9e3de026dc8124a94db4fff11a84ca1de0349d`; sealed delivered scores `e3f93c83...`; config hash `2965d392...` |
| flight | flight commit `cdd6cd95b` (ext4 flip, 2026-10-17T13:51:47Z); chain 1 started 13:53:02Z and aborted at the serving swap (`UnicodeDecodeError` in the swap step; `CHAIN_NXT2B_EXIT rc=6` 13:53:55Z; no contact); chain 2 started 13:57:38Z; smoke sealed 14:04:49Z (16 contacts); driver `arm` 14:25:05Z; column sealed 2026-10-18T12:31:00Z; `CHAIN_NXT2B_EXIT rc=0` 12:34:22Z |
| exposure | column row CONSUMED (sealed): 4,320 contacts, 12,619.2 speech-audio seconds, 87.67 summed call-latency hours, manifest COMPLETED, attempt FINALIZED (ceiling 8,640 calls / 25,239 s / 27.6 GPU-h); smoke row 16 contacts / 40.7 s / 0.28 h; rows closed in `a177f5d6f`. READ row countersigned in `310e23ae0` (commit time 2026-10-18T14:39:33Z) |
| read sequence | columns stage 14:37:41-14:38:26Z (prints no number), countersign commit 14:39:33Z, `read.json` written 14:40:02Z (file mtimes, UTC) |

## 2. Results

### 2.1 The contrast

| arm | Perception / Solver budget (cap) | SLU-F1 % | SLU delta pp [CI95] | intent % | intent delta pp [CI95] | intent saves / harms / ties | absent rows | word |
| --- | --- | ---: | --- | ---: | --- | --- | ---: | --- |
| budget-3072 (delivering) | 3,072 (4,096) / 3,072 (4,096) | 72.74 | -- | 85.37 | -- | -- | 0 | -- |
| solver-6144 | 3,072 (4,096) / **6,144 (7,168)** | 71.93 | **-0.81 [-2.19, +0.57]** | 84.81 | **-0.56 [-1.67, +0.56]** | 17 / 23 / 1,040 | 0 | **NEEDS-NO-MORE-BUDGET** |

Full precision (`contrast.versus_delivering.solver-6144`): SLU -0.8067 [-2.1869, +0.5733] (half-width 1.38), intent
-0.5556 [-1.6667, +0.5556] (half-width 1.11). Official counts (`score-summary.json`): SLU-F1 TP 1,586 / FP 671.48 / FN
517.48 (delivering) vs 1,574 / 702.25 / 526.25 (solver-6144); exact entities 627 / 394 / 317 vs 617 / 415 / 327; intent
correct 922 vs 916; scenario 89.07 vs 89.26 %; action 86.39 vs 86.20 %. Derived, solver-6144 minus delivering: SLU TP -12,
FP **+30.77**, FN +8.77. The longer reasoning adds a few false slot predictions; it does not recover missed ones.

### 2.2 The word, with the rule quoted

Reader rule (`slurp_nxt_r2b_solver_budget_column_read.py` docstring and `analysis-recipe-v1.json` `word_rules`; first rule
that applies; |o| = 1.15 pp, "owner decision 313 A: the larger of the two measured same-core A/A offsets (no twin flies)"):

- **GAIN**: "SLU CI95 lower bound above +|o| (the raised Solver budget RAISES the score beyond the declared A/A width)".
- **HARM**: "SLU CI95 upper bound below -|o| (the raised budget loses more than the declared A/A width)".
- **NEEDS-NO-MORE-BUDGET**: "SLU CI95 upper bound <= +1.49 pp and intent CI95 upper bound <= +0.65 pp (decision 190 floors): any gain is inside the design's own resolution, so the raise buys no resolved gain and the delivering budget is enough".
- **UNRESOLVED**: "none of the above".

Applying it: GAIN needs -2.19 > +1.15 (no). HARM needs +0.57 < -1.15 (no). NEEDS-NO-MORE-BUDGET needs +0.57 <= 1.49 (yes)
and +0.56 <= 0.65 (yes) -> **NEEDS-NO-MORE-BUDGET**, which `read.json` `node_words.words.solver-6144.word` states. The
intent condition holds by a narrow margin: the upper bound +0.5556 pp is 6 rows of 1,080; the floor 0.65 pp is 7.02 rows
(derived), so one more row in the bootstrap's upper quantile would still pass and two would not.

### 2.3 Per scenario (18 scenarios x 60 rows; point deltas, no scenario CI in the read)

| scenario | n | SLU budget-3072 % | SLU solver-6144 % | SLU d pp | intent budget-3072 % | intent solver-6144 % | intent d pp |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| alarm | 60 | 75.33 | 73.19 | -2.14 | 88.33 | 88.33 | +0.00 |
| audio | 60 | 75.96 | 68.18 | -7.77 | 86.67 | 85.00 | -1.67 |
| calendar | 60 | 72.82 | 72.44 | -0.38 | 80.00 | 81.67 | +1.67 |
| cooking | 60 | 76.47 | 70.83 | -5.64 | 90.00 | 86.67 | -3.33 |
| datetime | 60 | 80.71 | 79.70 | -1.01 | 95.00 | 91.67 | -3.33 |
| email | 60 | 73.08 | 74.80 | +1.72 | 93.33 | 91.67 | -1.67 |
| general | 60 | 58.90 | 56.33 | -2.57 | 38.33 | 36.67 | -1.67 |
| iot | 60 | 75.25 | 77.26 | +2.01 | 91.67 | 95.00 | +3.33 |
| lists | 60 | 64.45 | 68.41 | +3.96 | 88.33 | 88.33 | +0.00 |
| music | 60 | 58.94 | 48.77 | -10.17 | 80.00 | 81.67 | +1.67 |
| news | 60 | 71.85 | 74.48 | +2.63 | 88.33 | 90.00 | +1.67 |
| play | 60 | 59.36 | 60.07 | +0.71 | 80.00 | 76.67 | -3.33 |
| qa | 60 | 77.53 | 71.23 | -6.30 | 86.67 | 81.67 | -5.00 |
| recommendation | 60 | 62.47 | 68.59 | +6.12 | 85.00 | 90.00 | +5.00 |
| social | 60 | 73.42 | 74.54 | +1.13 | 90.00 | 90.00 | +0.00 |
| takeaway | 60 | 72.29 | 68.56 | -3.72 | 86.67 | 86.67 | +0.00 |
| transport | 60 | 75.08 | 74.62 | -0.46 | 90.00 | 85.00 | -5.00 |
| weather | 60 | 85.11 | 84.28 | -0.83 | 98.33 | 100.00 | +1.67 |

| weighting | SLU d pp (solver-6144 - budget-3072) | intent d pp |
| --- | ---: | ---: |
| natural mixture (primary) | -0.81 | -0.56 |
| equal-scenario | -1.26 | -0.56 (derived; equal n per scenario, so equal to the natural mixture) |

Counts (derived): SLU down / up in 11 / 7 scenarios; intent down / up / flat in 8 / 6 / 4. The equal-scenario SLU delta is
more negative than the natural mixture because music (-10.17) carries 1/18 of the weight (-0.57 pp of the mean, derived);
music is also the scenario where R1's in-flight A/A twin moved most (+13.93 pp, R1 note section 6), so a 60-row scenario
delta of this size is within the twin swing this core shows. The two weightings agree in sign; neither resolves a change.

### 2.4 Decode and forced closes, per node per arm (all 1,080 rows; `arms_nodes`)

| arm | node | budget / cap | contacts | completion tokens mean / p50 / p90 / p99 / max | finish | cap hits | **forced closes (share)** | empty / no JSON / markers | reasoning chars mean | prompt tokens mean | s per contact mean / p50 / p99 |
| --- | --- | --- | ---: | --- | --- | ---: | ---: | --- | ---: | ---: | --- |
| budget-3072 | perception | 3,072 / 4,096 | 1,080 | 2,014.6 / 1,898.5 / 3,137.1 / 3,192 / 3,203 | stop 1,080 | 0 | **199 (18.4 %)** | 0 / 0 / 0 | 8,931 | 3,589.6 | 58.96 / 54.70 / 106.98 |
| budget-3072 | solver | 3,072 / 4,096 | 1,080 | 2,017.8 / 1,949.5 / 3,131.0 / 3,144.2 / 3,156 | stop 1,080 | 0 | **433 (40.1 %)** | 0 / 0 / 0 | 8,391 | 8,475.2 | 64.10 / 58.93 / 118.50 |
| solver-6144 | perception | 3,072 / 4,096 | 1,080 | 2,044.0 / 1,936.0 / 3,138.0 / 3,194 / 3,228 | stop 1,080 | 0 | **213 (19.7 %)** | 0 / 0 / 0 | 9,066 | 3,589.6 | 60.24 / 57.19 / 108.50 |
| solver-6144 | solver | **6,144 / 7,168** | 1,080 | 3,291.6 / 2,203.5 / 6,203.0 / 6,218 / 6,234 | stop 1,080 | 0 | **408 (37.8 %)** | 0 / 0 / 0 | 13,771 | 8,494.0 | 108.95 / 68.78 / 236.87 |

Every node: 1,080 contacts and 1,080 wire records, 1,080 with reasoning characters, 0 `finish_reason = length`, 0 think
markers in content, `reasoning_marker_total` 0, `unattributed_contacts` 0.

Reading it plainly (all derived from the table):

- **Solver, budget raised.** Forced closes 433 -> 408 (-25 contacts, -2.31 pp of share); 94 % of the 3,072 forced-close count is still forced at 6,144. The p90 completion sits at budget + 59 tokens in both arms (3,131 = 3,072 + 59; 6,203 = 6,144 + 59): the upper tail moved with the budget instead of ending under it. The median moved only +254 tokens (1,949.5 -> 2,203.5): most contacts finish well under 3,072 either way. Mean completion +1,273.8 tokens (+63 %), reasoning characters +64 %, seconds per contact +70 %. No contact reached the 7,168 cap.
- **Perception, same request form in both arms (A/A-like).** Same budget, cap, prompt (mean 3,589.6 tokens in both) and seed; the two arms' Perception contacts are independent requests in one flight. They differ by 14 forced closes (199 vs 213, +1.30 pp), +29.4 mean completion tokens and +1.28 s per contact. That is the size of request-identical jitter on this np4 serving geometry; the Solver's -25 forced closes is 1.8x it. The Solver prompts differ by 18.8 tokens on the mean (8,475.2 vs 8,494.0) because each arm's Solver reads its own arm's Perception note.
- **Against R1's decode sample (cross-flight, descriptive).** R1's both-on Solver forced-closed 19 / 51 (37.3 %) on its 51-row rec2 sample; here 433 / 1,080 (40.1 %) on the full roster, and the 268-B note had 44-46 %. R1's Perception forced-closed 1-2 / 51 (2-4 %) on that sample, against 18.4-19.7 % here on all 1,080 rows: the R1 51-row sample understated Perception's budget pressure (R1 note section 9 flags the sample).

### 2.5 Throughput (the efficiency deliverable; `throughput`)

| arm | s per row | rows per minute (4 slots) | GPU-h per 1,080-row lock flight | at the 1.84 rows/min reference | cost in delivering rows (measured / registered) | saving vs delivering |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| budget-3072 | 123.1 | 1.95 | 9.23 | 8.26 | 1.00 / 1.0 | 0.0 % |
| solver-6144 | 169.2 | 1.42 | **12.69** | 11.35 | **1.37 / 1.57** | **-37.5 %** |

One flight measured **21.92 GPU-h** (= 87.67 summed slot-hours / 4, matching the ledger's closure text, derived) against
the registered expected 21.22 and ceiling 27.6; measured arm mix 2.37 delivering rows per row vs registered 2.57 (ratio
0.92). The registered cost 1.57 was the declared upper envelope (README prerequisite 6: only forced-close contacts can
grow); the measured 1.37 sits under it. Wall time from the driver start (14:25:05Z) to the seal (12:31:00Z) is 22 h 06 min
(derived). The delivering arm's 123.1 s per row is above R1's 110.0 s (51-row sample) and close to the 268-B lock arm's
"about 9.4 GPU-h" per pass (package README).

### 2.6 The delivering arm against R1 both-on (cross-flight; descriptive only, not a contrast)

Both are the 268-B lock form on the same 1,080 rows, flown in different flights (R1 rec2 at `e4092610b` on the max4096
session, kept rows from rec1; R2b at `cdd6cd95b` on the max7168 session with the same request parameters).

| comparison (a vs b) | SLU-F1 a / b | intent correct a / b | intent: a-only / b-only correct (discordant rows) | rows with exact slot F1 = 1: a-only / b-only |
| --- | --- | --- | --- | --- |
| R2b budget-3072 vs R1 both-on (cross-flight, same form) | 72.74 / 72.35 | 922 / 926 | 22 / 26 (48) | 34 / 35 (69) |
| R1 both-on-twin vs R1 both-on (in-flight A/A twin) | 72.23 / 72.35 | 926 / 926 | 12 / 12 (24) | 26 / 26 (52) |
| R2b solver-6144 vs R2b budget-3072 (this read's contrast) | 71.93 / 72.74 | 916 / 922 | 17 / 23 (40) | 35 / 39 (74) |
| R2b solver-6144 vs R1 both-on (cross-flight) | 71.93 / 72.35 | 916 / 926 | 23 / 33 (56) | 31 / 36 (67) |

(Counts from `per_sample.scenario_action_exact` and `per_sample.slot_f1_exact_f1` over 1,080 common sample ids, all
rows parsed; the in-flight row reproduces `read.json`'s 17 saves / 23 harms.) Level agreement: SLU +0.39 pp and intent
-0.37 pp (4 rows) cross-flight. The lock form has now been read five times on this roster: 71.61 (268-B lock), 72.75 (268-B
twin), 72.35 (R1 both-on), 72.23 (R1 twin), 72.74 (R2b delivering) SLU, a span of 1.14 pp; intent 84.91-85.74. The
solver-6144 arm's 71.93 / 84.81 sits inside the SLU span and 1 row under its intent span. The cross-flight same-form
discordance (48 intent rows) is twice the in-flight twin's (24); the budget contrast's 40 discordant rows sit between the
two.

## 3. Interpretation (stated, not claimed)

- **Untruncating the Solver does not move the score.** Ruling 323 read R1's 19 / 51 forced closes as "the Solver's reasoning is truncated" and asked whether finished reasoning would help. At 6,144 tokens the reasoning mostly did not finish: 408 / 1,080 contacts still ran to the budget, and the score moved -0.81 pp SLU (inside the declared A/A width) at 1.37x the cost. Under the registered word the delivering budget is enough; per ruling 323 ("Its read decides the Solver budget of the v3.0 lock candidate") the v3.0 lock candidate keeps the Solver at 3,072 / 4,096.
- **What forced-close persistence implies: reasoning that does not terminate is not budget-limited.** The Solver's completion distribution is bimodal in effect: a majority that ends naturally (p50 about 1,950-2,200 tokens, nearly unchanged) and a 38-40 % tail that runs to whatever budget is set (p90 = budget + 59 at both budgets). Doubling the budget converted about 25 contacts (net, within roughly twice the same-form jitter) from forced to natural termination. So for most of the tail the binding condition is not the length of the reasoning that the task needs; it is that the reasoning does not converge to a stop. The forced-close message at 3,072 already ends that reasoning about as well as letting it run to 6,144 does (no resolved score difference, 30.8 more weighted false slot predictions at 6,144). The read does not open reasoning text, so whether the tail is re-verification, oscillation between candidates or repetition is not measured here.
- **Implication for the next USE-node round (ruling 326 A: Solver instruction-template column, K <= 6 arms, TRAIN Fold B).** The lever on the non-terminating tail is the instruction, not the budget. Candidate template arms the read points to: a reasoning-termination instruction (state the evidence once, commit, do not re-verify a settled slot), a decide-once instruction for the intent (choose from the shortlist once, then fill slots), and an explicit stop condition tied to the output contract. Each such arm should carry the Solver forced-close share and seconds per contact as a pre-declared mechanism readout beside SLU-F1 and intent: a template that cuts the 40 % tail without a resolved loss is an efficiency result on its own (the forced-close tail is where the Solver's seconds are), and a template that ends reasoning earlier AND lifts the score would be the first evidence that the tail's reasoning is harmful rather than merely unfinished. The column stays at the delivering 3,072 budget; the raised-cap session is not needed for it.
- **What it does not mean.** No admission, no lock change beyond keeping the registered Solver budget, no benefit, generalisation or test claim; one roster, the selection fold; `claims_benefit` false.

## 4. Limits

- **Development numbers on TRAIN Fold B, never a test claim** (owner decisions 28 and 86). One roster (`SLURP-EVO-FOLD-B-V2`), the fold the Thinking system and R1 were read on; no Fold A, DEV or test read of this column exists. `claims_benefit` is false.
- **No twin; the null is declared.** Owner decision 313 A: the words use |o| = 1.15 pp SLU (268-B cross-flight twin) rather than an in-flight twin. R1's in-flight twin was much tighter (|o| = 0.12); with |o| = 0.12 the word would be unchanged (the SLU interval still straddles both +0.12 and -0.12, and the NEEDS-NO-MORE-BUDGET floors do not depend on |o|) (derived).
- **NEEDS-NO-MORE-BUDGET is "no resolved gain", not "no effect".** The SLU interval [-2.19, +0.57] includes losses up to 2.19 pp; the word says the raise buys no resolved gain at the decision-190 floors, and the intent condition passes by about one row (section 2.2).
- **Forced closes are counted, not linked to correctness.** `read.json` carries per-node forced-close counts but no per-row forced-close x correctness table, so this note cannot say whether forced-close rows score worse, or whether the 25 rows that finished naturally at 6,144 gained or lost. A model-free follow-up over the sealed trace and the per-sample scores could tabulate it.
- **Independent chains.** Each arm's Solver reads its own Perception note; the Solver contrast therefore includes Perception jitter (section 2.4: +14 forced closes, +29 mean tokens on identical requests).
- **Cross-flight comparisons are descriptive.** Section 2.6 compares different flights, sessions (max4096 vs max7168 fragment, same server arguments) and, for R1, kept-plus-flown attempts; it is not a contrast and carries no interval.
- **Ledger stamp discrepancy (record, not a defect of the read).** The READ row's text says "root countersigned 2026-10-18T14:45:00Z"; the countersign commit `310e23ae0` is timed 14:39:33Z and `read.json` was written 14:40:02Z (UTC mtime). The commit precedes the read, so the registered order (countersign, then read) holds by the commit time; the 14:45:00Z text stamp is later than both and should be read as approximate.
- **Chain 1 abort.** The first chain (13:53:02Z) aborted at the serving swap with a UTF-8 decode error in the swap step (rc = 6, no contact); it was not investigated here.

## 5. Pointers (sha256)

Analysis root `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-NXT-R2B-SOLVER-BUDGET-FOLD-B-READ-V1/`:

| file | sha256 |
| --- | --- |
| `read.json` (schema `saea-nxt-r2b-solver-budget-column-read-v1`) | `1f73482f781219b49ae39abe8a7c93a659ba025500713b9871d611f4f1cfeba7` |
| `README.md` | `cbd547c6e35b72cf7d010cb81080f7ed0c905e395f915719beca444e266c1554` |
| `smoke-decode-cost.json` | `3d11865d263f28f855ff2b33ffbbb947d9cae4095779c982bc4dc0cd7274857d` |
| `columns/score-summary.json` | `7e28c43062bea349b06ae21a8436851120dd3bc2a89981e361ebe08b3a982802` |
| `columns/render-manifest.json` | `73b2ffaa711c92334d71f2fa6275d8cc79950d5fa84628a368c728ffb7d6290f` |
| `columns/arm-budget-3072-slurp-slu-official-train-scores.json` | `e7dc5acd1d74a183d17204b9c0ff7b0c29a71a7f629cb67d6b7cbd902a36b3d2` |
| `columns/arm-solver-6144-slurp-slu-official-train-scores.json` | `35a637102864696accfc19c5de7bd3d0023695a5b6a64dd46a8ae8690935deae` |
| `columns/arm-budget-3072-first-visit-outputs.jsonl` | `a889ab183a97972e3c568e9c6dd6f5095719a593efff6238b33c3e90f319f7db` |
| `columns/arm-solver-6144-first-visit-outputs.jsonl` | `74889beb5a4c5e5ac5c078c7424a394a224618b096ed4da63754d1a8e3bc5247` |

Repository (bytes at `310e23ae0`):

| file | sha256 |
| --- | --- |
| `docs/readiness/2026-10-17-slurp-nxt-r2b-solver-budget-fold-b-v1/README.md` | `2ffc2bd64962fcf702e9980ef0bf7182c29e5abd558405ef23057623a1360cb2` |
| `.../analysis-recipe-v1.json` | `6eef0a7fdd733b130cc51cce566fe4145e71044429874f70ab62c1c32c834e2b` |
| `.../registered-facts-v1.json` | `e507b0777dd48218e508d90b4bd5c879ee2a0b527cfda11a92227fa59f1b2f98` |
| `.../generation-plan-registered-v1.json` | `36089ac1d4146d5231af1e47fc6b5c35dba918173f2e266fcf7d652cc8444965` |
| `.../protocol-registered-v1.json` | `3d9b7a264028aebc141b17748cf346a7f12af241e3075346d3a612653861a3cb` |
| `scripts/analysis/slurp_nxt_r2b_solver_budget_column_read.py` | `027acd802468dbf29b5d114696c16efc26f2d37d348e786179689c3e69bdee95` |
| `scripts/analysis/slurp_nxt_thinking_budget_column_read.py` | `0b88f152e2f3e84a92ae0830966b00385114e6659ec137655b7e23313e58bcab` |
| `scripts/flights/nx/nxt_r2b_family.py` | `3d6e10ab4145f1161c593a624fe3d95b252701da3deb8dc7c048b324b4891ed4` |
| `scripts/flights/nx/nxt_r2b_arms.json` | `9f240aab5c2155c46826f3f8257dd0fad73f65a9dd50617ca1a6669d834d960f` |
| `docs/receipts/rosters/slurp-evo-fold-b-v2.json` | `47b89b9e33b1aed553ad94a1819acba6ac8837130ca546c33219d91a1ab944a8` |

Registry `docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`, sections "Owner rulings 323 and 324",
"Owner rulings 325-327" and "NX-T R2 rec2 (328) REGISTERED and queued behind R2b". Exposure-ledger section "Cell NXT-R2B".
Related notes: `docs/results/2026-10-17-slurp-nxt-r1-thinking-policy-column-read.md` (R1: Solver NEEDS-THINKING, 19 / 51
forced closes), `docs/results/2026-10-13-slurp-268b-thinking-system-fold-b-read.md` (the 268-B lock arm and the declared
offset).
