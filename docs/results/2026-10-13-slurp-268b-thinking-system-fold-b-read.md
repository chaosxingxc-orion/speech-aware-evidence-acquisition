# Cell 268-B, the locked SLURP system on the Thinking core, TRAIN Fold B: TRANSFERS-ABOVE-BAR (SLU-F1 +7.15 pp [+5.08, +9.26], intent +2.31 pp [+0.56, +4.07] over the same system on the Instruct core); decision 299 A trigger met 3/3 -> REBUILD-BASE-ON-THINKING

Read 2026-10-13 by Claude Opus 5.5 (results-note agent, on the coordinator's brief, Fable 5.1) in the worktree
`opus/268b-results-note` (base master `23d52cb73`). Model-free: this note opened no model, server, encoder, embedder,
tokenizer or GPU, ran no scorer and wrote nothing under the data root. It reads the outputs of the registered read
`SAEA-SLURP-SYSTEM-THINKING-CORE-FOLD-B-READ-V1` (`read.json`, `README.md`, `smoke-decode-cost.json`), the 268-B
package (`docs/readiness/2026-10-12-slurp-system-thinking-core-fold-b-v1/`), the registry and the exposure ledger. It
computes nothing anew except ratios and sums of numbers printed in those files (marked "derived"). No utterance text,
transcript, gold label, model output or reasoning text was read, printed or persisted.

**Status: DESCRIPTIVE, development numbers on TRAIN Fold B (`SLURP-EVO-FOLD-B-V2`, n = 1,080, discovery role; owner
decisions 28 and 86). Never a test claim. `claims_benefit` is false on every cell** (`stage3_measurement` in
`registered-facts-v1.json`). The read measures whether a core lever (the Thinking core, +11.90 pp SLU on the bare form,
266-E) transfers to the locked system. It is not an admission and not a system-level, superiority, generalisation or
paper-scale claim (`analysis-recipe-v1.json`, `claim_boundary`).

Ledger entry (owner decision 268 B). The locked system (lock v2.2 + v4g, program `phase-native-module-v1-c2`, the same
knowledge supply) flown on the Thinking core beats the same system on the Instruct core by +7.15 pp SLU-F1 and +2.31 pp
intent on TRAIN Fold B, above the 2.5 pp cross-flight bar and outside the in-chain twin offset. It keeps 60.1 % of the
bare-core Thinking delta. Every contact completed (0 cap hits, 0 empty answers, 0 reasoning markers), but the reasoning
budget forced the close on 18 % of Perception and 44-46 % of Solver contacts, and the cost per arm overran the amended
ceiling.

## 1. Headline and verdict

Source: `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-SYSTEM-THINKING-CORE-FOLD-B-READ-V1/read.json` (schema
`saea-slurp-system-thinking-core-read-v1`, status "PREREGISTERED-READ (development numbers; never a test claim;
claims_benefit false)"). Interval: utterance-cluster bootstrap, 10,000 draws, seed 20261011, CI95.

| metric | Instruct lock (i3) | bare Thinking | Thinking system (lock) | twin (aa) | d_system (pp) | CI95 | twin offset (pp) [CI95] | vs bare (pp) [CI95] |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| official pooled SLU-F1 % | 64.45 | 45.39 | **71.61** | 72.75 | **+7.15** | [+5.08, +9.26] | +1.15 [-0.09, +2.42] | +26.21 [+23.84, +28.64] |
| intent % | 82.69 | 76.76 | **85.00** | 84.91 | **+2.31** | [+0.56, +4.07] | -0.09 [-1.30, +1.11] | +8.24 [+6.20, +10.37] |

- **Arms.** Instruct lock = the lock column of loop iteration 3 (`SAEA-SLURP-STAGE3-TFRL-LOOP-I3-FOLD-B-V1`, same roster,
  same system). Bare Thinking = 266-E (`SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-V1`). d_system = Thinking system lock
  minus Instruct lock; twin offset o = aa minus lock; vs bare = Thinking system lock minus bare Thinking.
- **Transfer share.** d_system / the bare 266-E delta = 7.15 / 11.90 = **60.1 %** (`transfer_share_of_bare_delta`).
- **Intent saves / harms / ties** (per row): lock vs Instruct lock 59 / 34 / 987; aa vs lock 20 / 21 / 1,039; lock vs
  bare Thinking 114 / 25 / 941.
- **Delivered content.** Empty content / no JSON object / reasoning leak: lock 0 / 0 / 0, aa 0 / 0 / 0, Instruct lock
  0 / 0 / 0, bare Thinking 36 / 36 / 0. Scorer parse failures: lock 0, aa 0, Instruct lock 3, bare Thinking 36.
  `reasoning_marker_total` 0.

**Verdict: TRANSFERS-ABOVE-BAR.** The reader's preregistered word (`scripts/analysis/slurp_system_thinking_core_read.py`;
rule fixed in the package README "Read rule (preregistered)" before any contact). Words: HARM (d <= -2.5 pp and CI95 hi
< -|o|); TRANSFERS-ABOVE-BAR (all four rows below); PARTIAL (CI95 lo > |o| but below the bar or the intent guard
fails); NO-TRANSFER otherwise.

| condition | value | threshold | result |
| --- | ---: | ---: | --- |
| d_system SLU >= bar (cross-flight) | +7.15 pp | 2.5 pp | PASS |
| CI95 lower bound of d_system SLU > abs(twin offset) | +5.08 pp | 1.15 pp | PASS |
| intent CI95 lower bound >= -intent guard | +0.56 pp | -0.65 pp | PASS |
| delivered reasoning markers (lock, aa) | 0 | 0 | PASS |

**Design.** `cross-flight-with-in-chain-replicate` (measurement instrument
`docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md`). One 24 GB card holds one core, so the Instruct
and Thinking systems cannot share a flight. The Thinking system flew twice in one chain on one session at one flight
commit (lock and its request-identical twin aa); the twin offset is the same-core noise the verdict guards against.
Session drift between the Instruct i3 flight and this chain is not measured by the twin; the 2.5 pp bar covers it, and
the observed d_system is 2.9 times the bar (derived).

## 2. What was flown

| cell | run id / attempt | flight commit | contacts / speech-audio s | seal | summed call latency |
| --- | --- | --- | --- | --- | --- |
| smoke (4 rows) | `SAEA-SLURP-STAGE3-THINKING-SYSTEM-FOLD-B-SMOKE-4-V1` | `c112da11b` | 8 / -- | 2026-10-12 19:55Z | -- (decode cost only, never scored) |
| Thinking system arm (lock) | `SAEA-SLURP-STAGE3-THINKING-SYSTEM-FOLD-B-LOCK-V1` / `attempt-slurp-native-stage3-thinking-system-fold-b-lock-generation-v1` | `be7878fc6` | 2,160 / 6,310 | 2026-10-13 05:58Z | **37.65 h** |
| in-chain twin (aa) | `SAEA-SLURP-STAGE3-THINKING-SYSTEM-FOLD-B-AA-V1` / `attempt-slurp-native-stage3-thinking-system-fold-b-aa-generation-v1` | `be7878fc6` | 2,160 / 6,309.6 | 2026-10-13 15:38:31Z | **37.82 h** |

Sources: registry sections "268-B smoke read and sign-off amendment" (20:10Z) and "268-B lock arm SEALED" (06:05Z);
exposure-ledger aa row (CONSUMED note); `read.json` `nodes_by_arm`.

- **System.** The loop's plain lock arm, byte for byte, except the core: lock v2.2 + v4g post-processing, program
  `phase-native-module-v1-c2` (Perception + Solver, 2 contacts per row, no supply arm, no tool schema, no Reviewer or
  Planner, `max_revisions` 0), the loop's Fold B knowledge pools (fold-excluded, `9c64e8ec...`), roster
  `docs/receipts/rosters/slurp-evo-fold-b-v2.json`. The core is the one factor (package prohibitions).
- **Core and session.** Model fragment `q4km-thinking-mmproj-free-slurp-module-fold-b-np4-ctx24k-budget3072-max4096-v1`,
  session `serving-slurp-thinking-module-fold-b-np4-budget3072-max4096-v1`, swap target **`think-budget-np4`** (4 slots,
  24,576 tokens per slot), Thinking speech packets `slurp-q4km-packets-thinking-gpu-afdaeff6` (promotion receipt
  `ef409ef4...`).
- **Thinking knobs.** Reasoning budget **3,072** tokens + answer reserve 1,024 = completion cap **4,096**; forced-close
  message pinned by hash; `reasoning_context_policy` **`drop-reasoning-v1`** (no reasoning is delivered, scored or
  carried to another node); every node thinks; temperature 0, seed 20260913; one answer-only fallback per node. Reasoning
  bytes are projected out at the transport before sealing (decision 286 = C, policy `hash-and-stats-only-v1`): the sealed
  trace keeps only `reasoning_content_sha256`, character and token counts, `forced_close` and `finish_reason`.
- **Wall time.** Lock 9 h 46 min (1.84 rows/min, registry 06:05Z). The twin started 05:58:52Z and sealed 15:38:31Z
  (9 h 40 min, derived).
- **Cost, stated plainly.** Summed latency / 4 slots = **about 9.4 slot-normalised GPU-h per arm** (lock 37.65 / 4 =
  9.41; aa 37.82 / 4 = 9.46; the node sums in `read.json` give 9.41 and 9.45). The amended registered ceiling is **8.4
  GPU-h per arm**. **Both arms overran it by about 1.0 GPU-h (about 12 %).** No runtime abort fired: the ledger's GPU
  cell is a pre-registered ceiling and the seal records summed latency, not wall-clock GPU-h. The smoke projection was
  6.42 GPU-h per pass; the measured cost is about 1.46x that (derived), which the registry attributes to 4-slot
  contention the 4-row smoke could not see. The registry commits the next Thinking registration to plan from a
  measured 4-slot throughput run.

## 3. Per scenario

Source: `read.json` `per_scenario` (18 scenarios, 60 rows each). d_system is the Thinking system lock minus the Instruct
lock inside the scenario. No per-scenario CIs: the reader does not compute them, and at n = 60 each scenario is a
descriptive cell.

| scenario | n | SLU Instruct lock / Thinking lock / aa % | SLU d_system pp | intent Instruct lock / Thinking lock % | intent d_system pp | SLU vs bare pp |
| --- | ---: | --- | ---: | --- | ---: | ---: |
| alarm | 60 | 68.87 / 76.19 / 75.30 | +7.31 | 90.00 / 90.00 | 0.00 | +29.13 |
| audio | 60 | 59.46 / 75.94 / 77.78 | +16.47 | 75.00 / 81.67 | +6.67 | +19.99 |
| calendar | 60 | 60.87 / 73.71 / 77.28 | +12.84 | 81.67 / 83.33 | +1.67 | +32.81 |
| cooking | 60 | 64.41 / 71.91 / 72.80 | +7.49 | 88.33 / 85.00 | -3.33 | +0.71 |
| datetime | 60 | 75.00 / 79.54 / 75.71 | +4.55 | 95.00 / 95.00 | 0.00 | +25.22 |
| email | 60 | 73.74 / 73.86 / 73.21 | +0.12 | 93.33 / 93.33 | 0.00 | +26.81 |
| general | 60 | 41.83 / 53.90 / 55.25 | +12.07 | 36.67 / 41.67 | +5.00 | +27.34 |
| iot | 60 | 71.52 / 72.11 / 74.94 | +0.60 | 78.33 / 88.33 | +10.00 | +14.01 |
| lists | 60 | 46.03 / 70.80 / 68.67 | **+24.77** | 83.33 / 90.00 | +6.67 | +35.29 |
| music | 60 | 56.25 / 52.04 / 55.67 | **-4.20** | 76.67 / 78.33 | +1.67 | +31.67 |
| news | 60 | 64.20 / 70.91 / 70.04 | +6.70 | 93.33 / 90.00 | -3.33 | +35.26 |
| play | 60 | 56.15 / 58.69 / 58.83 | +2.54 | 81.67 / 83.33 | +1.67 | +11.25 |
| qa | 60 | 65.23 / 75.79 / 77.79 | +10.56 | 81.67 / 83.33 | +1.67 | +19.49 |
| recommendation | 60 | 67.45 / 67.66 / 68.29 | +0.21 | 80.00 / 85.00 | +5.00 | +27.88 |
| social | 60 | 64.86 / 69.06 / 73.27 | +4.20 | 86.67 / 91.67 | +5.00 | +43.74 |
| takeaway | 60 | 54.89 / 69.70 / 68.36 | +14.81 | 90.00 / 86.67 | -3.33 | +19.99 |
| transport | 60 | 75.17 / 74.65 / 77.03 | **-0.52** | 78.33 / 85.00 | +6.67 | +29.29 |
| weather | 60 | 65.61 / 83.35 / 84.48 | +17.75 | 98.33 / 98.33 | 0.00 | +35.59 |
| **natural mixture** (pooled roster) | 1,080 | 64.45 / 71.61 / 72.75 | **+7.15** | 82.69 / 85.00 | **+2.31** | **+26.21** |
| **equal scenario** (mean of 18) | | | **+7.68** | | **+2.31** | **+25.86** |

Every scenario has 60 rows, so the two weightings agree on intent exactly; they differ on SLU only through pooled
F1's slot mass.

**The sign pattern (descriptive).**

- **SLU.** 16 of 18 scenarios gain; 12 gain more than 4 pp. The largest are lists +24.8, weather +17.7, audio +16.5,
  takeaway +14.8, calendar +12.8, general +12.1, qa +10.6. Two lose: music -4.2 and transport -0.5. Email,
  recommendation and iot are flat (+0.1 to +0.6).
- **Intent.** 11 of 18 gain, 4 are tied (alarm, datetime, email, weather; all at 90-98 % on Instruct), 3 lose 3.33 pp
  each (cooking, news, takeaway: 2 rows of 60 each, all at an Instruct intent of 88-93 %). The largest gain is iot
  +10.0.
- **Against 266-E.** On the bare form Thinking lost SLU in music, lists and iot and lost intent heavily in general
  (-15.8) and music (-12.5). Inside the system, lists turns into the largest SLU gain, general intent gains +5.0 and
  music intent gains +1.7; music remains the one scenario where Thinking loses SLU on both forms. This note does not
  test why.
- **Twin spread.** Per-scenario aa minus lock SLU ranges from -3.83 (datetime) to +4.21 (social) (derived from the
  table); single-scenario deltas of that size are inside same-core noise at n = 60.

## 4. Node tables

Source: `read.json` `nodes_by_arm`. Wire completion tokens include the reasoning tokens. The cap is 4,096 on every node.
Forced close = the reasoning budget (3,072) closed the think block and the node answered from the reserve.

**lock** (`SAEA-SLURP-STAGE3-THINKING-SYSTEM-FOLD-B-LOCK-V1`)

| node | contacts | cap hits | length finishes | empty | no JSON | forced closes | completion tokens p50 / p99 (max) | prompt tokens mean | s per contact mean / p50 / p99 | slot-normalised GPU-h |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- | ---: |
| Perception | 1,080 | 0 | 0 | 0 | 0 | 190 (17.6 %) | 1,964.5 / 3,193 (3,242) | 3,589.6 | 58.34 / 55.71 / 102.85 | 4.38 |
| Solver | 1,080 | 0 | 0 | 0 | 0 | 496 (45.9 %) | 2,407.5 / 3,146 (3,167) | 8,563.6 | 67.15 / 71.02 / 114.64 | 5.04 |

**aa** (`SAEA-SLURP-STAGE3-THINKING-SYSTEM-FOLD-B-AA-V1`)

| node | contacts | cap hits | length finishes | empty | no JSON | forced closes | completion tokens p50 / p99 (max) | prompt tokens mean | s per contact mean / p50 / p99 | slot-normalised GPU-h |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- | ---: |
| Perception | 1,080 | 0 | 0 | 0 | 0 | 189 (17.5 %) | 1,943.5 / 3,192 (3,246) | 3,589.6 | 59.12 / 56.08 / 102.56 | 4.43 |
| Solver | 1,080 | 0 | 0 | 0 | 0 | 470 (43.5 %) | 2,130.0 / 3,144 (3,167) | 8,552.5 | 66.93 / 68.75 / 116.04 | 5.02 |

Percentages derived (forced closes / 1,080). Every finish reason is `stop` (2,160 / 2,160 per arm); `marker_in_content`
is 0 on every node. The completion p99 sits 900-950 tokens under the cap on every node: the budget plus the answer
reserve did what the owner's directive asked (Thinking finishes every task, never an empty answer at the cap), in
contrast to the bare 266-E arm at cap 8,192 with 36 abstentions at the cap.

## 5. The smoke and the sign-off amendment

Source: `smoke-decode-cost.json` (schema `saea-slurp-system-thinking-core-read-smoke-v1`, "DECODE-COST PER NODE (no
score, no read)"); registry 20:10Z.

- **Smoke** `SAEA-SLURP-STAGE3-THINKING-SYSTEM-FOLD-B-SMOKE-4-V1` (flight commit `c112da11b`, 4 rows / 8 contacts on
  `think-budget-np4`, sealed trace `ab1b90e3...`): Perception 0 cap hits, 0 empty, 4 `stop`, 1 forced close, completion
  p50 2,014.5 / max 3,196, prompt mean 3,607.75, 50.32 s per contact; Solver 0 cap hits, 0 empty, 4 `stop`, 1 forced
  close, completion p50 1,436 / max 3,121, prompt mean 8,446.5, 35.31 s per contact. No reasoning marker, no JSON
  failure.
- **Projection vs plan.** 6.42 slot-normalised GPU-h per 1,080-row pass against the registered 5.1 ceiling (3.89
  expected x 1.3). The pre-smoke model took E[min(reasoning, 3,072)] = 848 tokens from the bare 266-E COST channel; on
  the system prompts the core reasoned about 1,985 (Perception) / 1,768 (Solver) tokens, about twice as long with 8-15k
  tokens of knowledge in view.
- **Sign-off amendment** (commit `7b50fdbab`, mirrored on every bound row before any arm contact): the family GPU model
  was replaced by the smoke-measured per-contact seconds; **lock and aa ceilings 5.1 -> 8.4 GPU-h** on the generation and
  FIT rows and plans; the package was regenerated and the decision receipt re-minted (sha `b8c6c172...`; the 5.1 receipt
  kept beside it as superseded). Decoding knobs unchanged (budget 3,072, cap 4,096). Sign-off marker written 20:03Z;
  the smoke is not re-flown (one-shot attempt). The owner's 268 B brief had quoted about 3.9 GPU-h per pass; the
  registry records the 1.65x difference rather than re-asking (decision 298 A).
- **Smoke vs arm.** The arm measured 58-59 s (Perception) and 67 s (Solver) per contact against the smoke's 50 s and
  35 s. Four rows under-stated the cost this time, the opposite of 266-E, where four rows over-stated it 1.8x.

## 6. Decision 299 A trigger: 3 / 3 -> REBUILD-BASE-ON-THINKING

Source: `read.json` `p3_trigger_299`; registry "Owner rulings 297-300" (15:25Z).

Decision 299 A (ruled 2026-10-12): on the 268 Fold B column, system-on-Thinking vs system-on-Instruct, (i) paired SLU
resolved and point estimate >= +1.5 pp, (ii) intent not worse by more than 0.65 pp, (iii) Thinking completion rate (no
cap hit, no empty answer) >= 99 %. All three -> the engineering base is rebuilt around Thinking; two of three -> Thinking
on SLURP only, carriers stay on Instruct, plus one DEV replicate.

| condition | value | threshold | met |
| --- | ---: | ---: | --- |
| SLU resolved and above point | point +7.15 pp; CI95 lo +5.08 (> 0 and > twin offset 1.15) | point >= 1.5 pp; CI lo > 0 | yes |
| intent guard | intent CI95 lo +0.56 pp | not worse than -0.65 pp | yes |
| completion rate | 1.0000 (2,160 lock contacts, 0 incomplete) | >= 0.99 | yes |

**Met 3 / 3. Direction: REBUILD-BASE-ON-THINKING.** The reader notes: "development reading on TRAIN Fold B; never a
benefit claim (the benefit bar stays bar_pp)".

What it triggers (registry "268-B READ" 15:50Z, on master at `32cebe703`; P3 of the registry plan "branch on 268";
299 A, 285 and 286):

- Thinking speech packets for every carrier (Audio2Tool, Earnings-21, Earnings-22) through the Thinking mmproj, GPU
  encode, since the Thinking audio tower differs from the Instruct one;
- the SLURP lock and the carrier all-off / direct baselines re-registered and re-read on the Thinking core; per-node
  thinking policy, budget and throughput re-optimised;
- serving geometry planned from measured 4-slot throughput (1.84 rows/min at np4 x 24,576 with budget 3,072), not from
  a 4-row smoke;
- **a DEV-2000-ADDED replicate of the Thinking system before any lock** (decision 28: Fold B numbers are development
  numbers), and a DEV read before any new test allowance (registry P3);
- the SOTA comparison redone on the Thinking base once it is locked (285 deferred until then; the comparator table
  stays a survey asset).

The trigger opens this work; it does not authorise a flight. Each step needs its own registration.

## 7. Launch defects found and fixed before the first contact

Source: registry "268 launch: three launch defects" (19:55Z); fixes in `22bdee18d` and `16082c1a2`.

| # | defect | cause | fix |
| --- | --- | --- | --- |
| 1 | **WSLENV carried the retired data root** | a Windows user variable `SPEECHRL_DATA_DIR` (E: path) is shared into every WSL session via `WSLENV`; after the cut-over every flip and serving start was refused, and the 19:14Z mint wrote the decision receipt onto a stray E: directory | user variable set to the hot root; stray receipt parked as `root-admission-v1.stray-env-20261012T1914Z.json`; receipt re-minted on the hot root (sha `3cf64523...`); rule: sessions started before the change set the variable on every wsl call |
| 2 | **Hollow ext4 flip wrapper** | with the receipt absent the flip script exited 6, `flip_loop` saw HEAD unchanged and called it converged, `flight_registration_check --cell` failed on all three cells, yet `flip_package_ext4.sh` printed `FLIP_CHAIN_DONE rc=0` | `22bdee18d`: the wrapper fails on a refused flip script (HEAD unchanged with rc != 0 is not convergence) and on any gate FAIL (exit 7, master not fast-forwarded) |
| 3 | **Preflight placeholder over-count** | `core.flight.cli check` refused smoke and lock with `COMPACT_REQUIRED ... physical_margin_tokens -817`: the model-free preflight counts the JSON payload at 4 bytes per token and rendered the Solver at **21,269** "tokens", while the exact native gate at the wire measured the same Instruct-lock requests at max **14,641** (Solver), with `context_compaction = null` on all 8,640 i3 contacts | `16082c1a2`: the three cells declare `preflight_budget_mode = defer-to-native-contact-fit` (the estimate is recorded, admission is decided by the exact per-contact gate), accepted under `compact-or-abstain` as under `raise`; neither silently truncates; wire fit 14,641 + 4,096 + 28 + 3,072 = 21,837 < 24,576 |

## 8. Caveats

- **TRAIN Fold B only.** One roster, development numbers, discovery role. No DEV, Fold A, test, Audio2Tool or Earnings
  number exists for the Thinking system.
- **The Instruct comparator is a different flight.** d_system is cross-flight: the Instruct lock column flew in loop
  iteration 3 (another session, another day, another flight commit); the twin measures same-session noise only. The
  verdict rests on the 2.5 pp bar covering session drift; d_system's CI lower bound (+5.08) is twice the bar.
- **The budget binds.** Forced closes hit 17.5-17.6 % of Perception contacts and 43.5-45.9 % of Solver contacts
  (31.8 % of all lock contacts, derived). The completion guarantee holds because the budget cuts reasoning short on
  almost half of Solver contacts. What a larger budget would buy, and at what cost, is unmeasured here.
- **Cost.** About 9.4 slot-normalised GPU-h per 1,080-row arm, 12 % over the amended 8.4 ceiling and about 1.46x the
  smoke projection; mean 62.7 s per contact (derived: 37.65 h x 3,600 / 2,160). The brief's "1.5x the Instruct system
  per row" could not be sourced from the files this note reads (see "Not verified here").
- **One core, one encoder.** "Thinking core" means the Thinking decoder with its own audio tower and its own packets;
  this read cannot separate the two.
- **Twin as a separate cell.** The in-row c3 twin could not be compiled; the twin is a second request-identical c2 pass
  (package prerequisite 1), which doubles the per-row cost of the control.

## 9. What is NOT claimed

No benefit claim (`claims_benefit` false on every cell), no admission and no lock: nothing is locked by this read
(`what_is_not_here`). No test, DEV, Fold A or held-out claim, no claim on Audio2Tool or Earnings, no superiority or SOTA
claim (285 stays deferred), no generalisation claim and no paper-scale claim. No claim that the Thinking system is the
best configuration of the Thinking core: the system was carried over unchanged from the Instruct core. No claim about the
content of the reasoning, which is neither stored nor read (decision 286). The 299 A trigger is a direction for
engineering work, not evidence of a benefit.

## 10. Records read

- Read: `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-SYSTEM-THINKING-CORE-FOLD-B-READ-V1/{read.json, README.md,
  smoke-decode-cost.json, smoke-decode-cost.md}`. Sealed hashes in `read.json`: lock scores `d418c60d...`, outputs
  `6974cc8a...`, manifest `74470a8d...`, trace `abd59a00...`; aa scores `34acf09b...`, outputs `4abab089...`, manifest
  `5335b0b5...`, trace `2a11a689...`; Instruct lock scores `016be241...`; bare Thinking scores `cebe54ba...`.
- Package: `docs/readiness/2026-10-12-slurp-system-thinking-core-fold-b-v1/{README.md, registered-facts-v1.json,
  analysis-recipe-v1.json}`.
- Registry: `docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`, sections "Owner rulings 2026-10-12: 268
  B ...", "Owner input 2026-10-12 11:05Z ... 286 RULED", the 274 / P0-P5 plan, "Owner rulings 297-300", "268 launch:
  three launch defects" (19:55Z), "268-B smoke read and sign-off amendment" (20:10Z), "268-B lock arm SEALED" (06:05Z),
  and "268-B READ" (15:50Z), which landed on master at `32cebe703` after this note's base `23d52cb73` (read there with
  `git diff 23d52cb73 32cebe703`; its numbers agree with `read.json`).
- Exposure ledger: the 268-B aa row (CONSUMED note with 37.82 h, sealed 15:38:31Z) as of master `32cebe703`.
- Precedent and comparator context: `docs/results/2026-10-12-slurp-266e-thinking-vs-instruct-bare-core-read.md`,
  `docs/results/2026-10-12-slurp-tfrl-loop-three-iterations-read.md` (Instruct lock i3 64.45 / 82.69).

**Not verified here.**

- "Cost 1.5x the Instruct system per row": no file read here states it. The only 1.5x the sources carry is the registry's
  smoke-vs-4-slot contention factor (measured 9.4 vs projected 6.42 GPU-h, 1.46x). The Instruct system's per-arm
  slot-normalised GPU-h is not in these files (the i3 column's 2.48 GPU-active h covers a whole multi-arm column).
- GPU-active hours from the monitor; only summed latency and wall spans are given.
