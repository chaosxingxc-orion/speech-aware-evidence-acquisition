# SLURP mechanism synthesis: what produced every gain and every harm of Stage 2 and Stage 3, and where the large-scale phase should spend GPU

Date: 2026-09-27. Author: Claude Opus 5.5, analysis track of owner decision 163 (row 163 of
`docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`), worktree
`/home/chao/saea-worktrees/fable-synthesis`, branch `fable/synthesis`; every cited file was read at master `610cd583` (the branch is rebased
onto the current master before each commit).

**Status: DESCRIPTIVE.** This note decides nothing, admits nothing, authorises no flight and registers
no cell. The ranking in section 5 is a ranking, not a decision (owner decision 139). Every number is a
development number on an exposed TRAIN or DEV roster (owner decisions 28 and 86) and is never a test
claim, a superiority claim or a generalisation claim.

**Model-free.** Zero model, tokenizer, encoder, embedder, ASR, scorer, server, network and GPU contacts.
Nothing under `SPEECHRL_DATA_DIR` was opened: every number is transcribed from a committed verdict,
read note, receipt or owner-decision row, cited by a source key that section 9 resolves to its path.
The only numbers produced here are arithmetic on transcribed numbers (Wilson intervals, differences
along a chain, row counts converted to points at 1 row = 0.0926 pp on the 1,080-row Fold A), and each
is marked "computed here". No utterance text, transcript, gold string, delivered answer or knowledge
body appears anywhere.

**One source is not on master at `610cd583`** and is cited by branch and commit: the combined-commit
offline read (`fable/commit`, `71bf3b0f`). The KPROBE value m = 24 of 55 is quoted from COMP-1's
expected-effect declaration on master [KPB]; no KPROBE read note is on master yet. The machine twin of section 1 is
`docs/results/2026-09-27-slurp-mechanism-synthesis/mechanism-table.json` (same rows, same sources).

## 0. The answer in ten lines

1. Every admitted SLURP gain came from **row-matched knowledge delivered to the node that makes the
   decision**, keyed by the row's own speech: the slot schema (KC-S1b), speech-keyed fillers (KU-S3),
   speech-keyed exemplars (M1: the key is 62 % of its gain), the date/time contract (M4b), and the
   agreement term that moves utterance-to-utterance evidence into Perception's intent retrieval (AGREE,
   intent +3.33 [+1.57, +5.09] against its in-chain A/A). The rest are deterministic delivery repairs
   (label projection, the M3 normaliser) that align output conventions with the scorer.
2. Every harm measured outside the noise band came from a **form change without row-matched content** or
   from a broken delivery shape: the knowledge-index form (twin -9.97 SLU), constant tool rendering
   (-9.17 intent, 137 unparseable rows), candidate narrowing (-11.74 SLU), removing the schema's examples,
   the discriminative-value rendering, and the delta stores' form cost on strata they did not cover.
3. The **control plane is null as built**: review on/off/1/primitives, NCP L1, the Acquisition node and
   tool availability all sit inside the band, because the loop revises about 5-6 % of wrong answers,
   repairs about equal harms, and the Reviewer is instructed to call a tool that no longer exists.
4. **Sampling cannot fix intent** (90.5 % of DEV rows keep one intent across five samples; any-sample
   intent +1.74 over the mean); it exposes entity variance (oracle +6.55 / +7.95 SLU) that no rule and
   no self-selection has been able to rank.
5. **Learned text deltas (TF-GRPO, GEPA, gating) reached every row and moved nothing measurable**; the
   rig's between-flight offset (up to +1.87 pp at n = 625) is larger than their effect, and it is a
   serving property of np4 batching with the prompt cache (np1 cache-off: 50 of 50 byte-identical).

## 1. The mechanism table

One row per SLURP cell with a sealed read, in three eras. `family` codes: KC knowledge content
supplied; KR knowledge retrieval / key; CF consumption form; NP node program / control; SA sampling /
aggregation / selection; TF training-free RL learned deltas; EN engineering (delivery, rendering,
serving, repair); OB observation (media / transcript supply); SY whole system against direct
(composite); IN instrument (null, A/A, probe). `CI` is the interval level the source used (the
DEV-1000 era used CI90, later cells CI95). `instrument` flags the reading under the corrected
measurement instrument (`docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md`):

| flag | meaning |
| --- | --- |
| ok | stands: the effect is far outside the cross-flight band, or it was read offline / over one sealed pool, or against an in-chain A/A |
| cons | the recorded word is already consistent with the corrected instrument (NEUTRAL, NULL, not proven) |
| RR-harm | re-read: "HARMFUL" by interval width against a sealed cross-flight comparator with no in-chain A/A becomes "not distinguishable from flight variance" |
| RR-gain | re-read: a gain claim whose size sits inside the cross-flight band (bar about 2.5 pp at n = 1,080, about 3 pp at n = 500-625) with no in-chain A/A keeps its direction only |
| RR-part | re-read in part: the large term stands, the smaller named term is inside the band (section 6 names it) |
| corr | already corrected by the instrument note, section 4 |
| n/a | no effectiveness contrast (instrument, probe, structural or engineering closure) |

### 1.1 Era A -- Stage 2 on DEV-1000 (closed-list pipeline and the first native systems)

| # | cell | family | what changed | roster | comparator / null | delta intent pp [CI] | delta SLU-F1 pp [CI] | CI | verdict as recorded | replicated | instrument | src |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A1 | SLURP-CL-BASE | CF+KC | the legal label inventory placed in the direct prompt (closed list) | DEV-1000 (1,000) | sealed M0 arm; no null yet | +17.80 [+15.70, +19.90] | -1.10 pooled; per-row slot -1.70 [-2.94, -0.48] | CI90 | BASELINE LOCKED | byte-for-byte re-flight = own null (A8) | ok | CLB, LED |
| A2 | SLURP-PROJ-V2 | EN | deterministic legal-label projection of the sealed answers (offline) | DEV-1000 | v1 projection, same sealed outputs | +1.50 [+1.0, +2.1] | 0.00 by construction | CI90 | RE-LOCKED (a repair: 15 saves / 0 harms, one stratum) | offline | ok | PRJ, LED |
| A3 | KC-S1b | KC | per-intent TRAIN slot schema on a separate slot contact | DEV-1000; NEW500 per-row | closed-list baseline; KC-S1a equal-contact control | 0.00 by construction | pooled 35.80 -> 44.35 (+8.55); NEW500 per-row +10.11 [+8.11, +12.19]; vs KC-S1a +10.02 [+8.01, +12.10] | CI90 | ADMITTED | numerically reproduced, not re-flown | ok | KCS, LED |
| A4 | KC-S1a | NP | a second slot-only contact, no schema (equal-contact control) | DEV-1000 NEW500 | closed-list baseline | 0.00 by construction | per-row +0.09 [-0.20, +0.38] | CI90 | NULL | - | cons | KCS, LED |
| A5 | KU-S1c | NP | two-contact draft-revise program, no knowledge | DEV-1000 | closed-list baseline | +1.50 [+0.30, +2.70] (revise contact alone +0.30 [-0.40, +1.00]) | +0.12 | CI90 | REPORTED (control, no gate) | - | RR-gain | KU1, LED |
| A6 | EVO-S1 round 1 | TF | slot-schema evolution loop (propose, fold A select, fold B confirm) | TRAIN folds (120 targeted rows) | incumbent A_0 through the same harness | - | targeted +2.50 [-0.000, +5.417] | CI90 | REJECT (lower bound exactly 0); 28.1 % of byte-identical requests returned different text | - | cons | EVO, LED |
| A7 | TAIL2S | OB | 2.0 s silence appended to the delivered clip | DEV-1000 | re-locked closed-list comparator; imported +-0.60, then own null | +1.30 [+0.19, +2.43] | non-inferior (LB +0.15) | CI90 | NOT ADMITTED (harness HARMFUL: 5 of 18 scenarios lose) | - | RR-gain | T2S, LED |
| A8 | SLURP-NULL | IN | byte-identical re-flight of the comparator | DEV-1000 | itself | +0.50 [-0.40, +1.43] | +0.29 [-0.91, +1.45] | CI90 | NONE (instrument): 11 of 11 metrics moved up under a pure null | - | n/a | NUL, LED |
| A9 | SLURP-LOGPROB | NP | decode-confidence (min token logprob) as an error judge | DEV-1000 | fixed AUROC / precision bars | AUROC 0.6935 [0.6660, 0.7202]; precision@86 51.16 % vs bar 72.09 % | - | CI90 | NOT ADMITTED; loses to the free legality judge | - | n/a | LGP, LED |
| A10 | KV-0 | CF | the five examples removed from the KC-S1b slot schema | DEV-1000 | KC-S1b | 0 by construction | official micro 41.75 (KC-S1b 44.35) | - | HARMFUL (family report: keep the example-bearing base) | - | ok | KV, LED |
| A11 | KV-2 (+twin) | KC | TRAIN vocabulary cards in the slot contact | DEV-1000 NEW500 per-row | KV-0 and a form twin | 0 by construction | vs KV-0 +7.16 [+5.24, +9.12]; vs twin +1.71 [+0.13, +3.27]; rotating stratum -1.38 | CI90 | NOT ADMITTED (twin gate) | - | RR-part | KV, LED |
| A12 | KV-1 (+twin) | KC | TRAIN-derived slot type descriptions | DEV-1000 NEW500 per-row | KV-0 and a form twin | 0 by construction | vs KV-0 -0.87 [-2.12, +0.31] | CI90 | NULL_COMPATIBLE | - | cons | KV, LED |
| A13 | KV-3 (+twin) | KC | TRAIN exemplars in the slot contact | DEV-1000 NEW500 per-row | KV-0 and a form twin | 0 by construction | vs KV-0 +0.52 [-0.75, +1.80] | CI90 | NULL_COMPATIBLE | - | cons | KV, LED |
| A14 | KU-S3 max256 | KR+KC | speech-keyed TRAIN slot fillers as typed content | DEV-1000 NEW500 per-row | matched control; form twin (other row's key) | joined-intent protection passes | speech - twin +3.65 [+1.60, +5.70]; twin - control +2.98 [+1.35, +4.67]; speech - control +6.64 [+4.65, +8.63] | CI90 | ADMITTED_COMPONENT | independent repeat PASS | RR-part | KU3, LED |
| A15 | KU-S4N G2 | KR | intent candidate NARROWING before the answer | NEW500 | aligned control | -2.20 [-5.08, +0.82] | micro -11.74 [-15.18, -8.16] | CI90 | HOLD_NONINFERIORITY_FAILED | - | ok | KU4, LED |
| A16 | G6 live intent+slots | NP | live intent and slot contacts on speech | NEW500 | control recovery arm | scenario guard fails | positive slot evidence | CI90 | NOT_FULLY_ADMITTED | program-matched follow-up (A17) | cons | G6, LED |
| A17 | program-matched follow-up | NP | the G6 program against a program-matched control | NEW500 | matched control | -0.2 | row-F1 CI90 crosses zero | CI90 | SYSTEM_NOT_ADMITTED | - | cons | PMF, LED |
| A18 | discriminative values (span pair) | CF | discriminative value rendering of the slot knowledge | NEW500 | historical form | - | row-F1 -6.06 | CI90 | NEGATIVE_COMPONENT_NOT_SELECTED | - | ok | DSV, LED |
| A19 | task agent (compact frame) replication | SY | compact-frame task agent vs direct, replicated | NEW500 | direct (same family) | +4.20 (CI90 > 0) | micro +2.99 (CI90 > 0) | CI90 | PRIMARY POSITIVE, exploratory working baseline | yes (replication of the 09-11 family) | RR-part | TAR, LED |
| A20 | role coverage (matched) | CF | role-coverage matched treatment | NEW500 | matched control | -2.20 (CI90 < 0) | micro -0.54 (unresolved) | CI90 | DO_NOT_ADOPT (intent negative) | - | RR-harm | RCV, LED |
| A21 | fixed Whisper evidence | OB | a fixed ASR transcript supplied before revision | NEW500 / DEV-1000 | observation control | -0.80 | NEW500 micro +0.83 [-1.10, +2.84] | CI90 | EFFECTIVENESS_NOT_ESTABLISHED | - | cons | WHS, TTS, LED |
| A22 | native system vs direct | SY | native Perception / Solver / Reviewer / Planner system vs one direct request | DEV-1000 NEW500 | direct, same resident process | 72.4 -> 78.6, +6.2 [+3.41, +9.17] | 36.25 -> 50.68, +14.43 [+11.21, +17.59] | CI90 | EXPLORATORY_SYSTEM_CANDIDATE | yes (A23) | ok | NAT, LED |
| A23 | max512 dual-store base replication | SY | the retained dual-store native agent vs direct, replicated | DEV-1000 NEW500 | direct | - | 35.89 -> 50.69, +14.80 [+11.52, +18.01] | CI90 | REPLICATED useful base | yes | ok | DSR, TTS, LED |

### 1.2 Era B -- Stage 2, the native agent on TRAIN Fold A (1,080 rows)

| # | cell | family | what changed | roster | comparator / null | delta intent pp [CI] | delta SLU-F1 pp [CI] | CI | verdict as recorded | replicated | instrument | src |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B1 | TRAIN-A anchor vs direct | SY | dual-store native agent (anchor) vs the released direct max512 arm | TRAIN Fold A (1,080) | released direct anchor 33.885 / 73.70 | +4.26 [+2.15, +6.46] | +14.65 [+11.79, +17.51] | CI95 | anchor released (48.53 / 77.96) | DEV pair A22/A23 | ok | DIR, ANC, LED |
| B2 | maximum-five candidates | KR | Perception candidate width 3 -> 5 | Fold A | anchor | 842 -> 837 correct rows | +0.09 [-1.36, +1.65] | CI95 | NOT_ADVANCED | - | cons | C5, TTS, LED |
| B3 | broad / factored knowledge | KR+KC | broad K60 supply plus factored rendering | Fold A | anchor | 842 -> 841 correct rows | -0.90 [-2.61, +0.78] | CI95 | NOT_ADVANCED | - | cons | BFK, TTS |
| B4 | typed-context package | CF | typed role context + structured review + target lookup | Fold A | direct (complete) | - | - | - | CLOSED: aborted twice (one Reviewer request 24,878 tokens > 24,576 slot); no quality read | - | n/a | LED, TTS |
| B5 | B0 / B0r review loop off | NP | Reviewer and Planner removed (Perception -> Solver -> delivery) | Fold A | anchor; imported 0.92, then B0r own null 1.1218 / 1.0051 | -0.37 [-1.53, +0.82] | +0.13 [-1.15, +1.45] | CI95 | HARMFUL by width (twice); loop changed <= 2 of 1,080 delivered intents | B0r = own null | RR-harm | B0, B0R, LED |
| B6 | B4b slot store v2 (M4b) | KC | date / time slot-contract revision | Fold A | sealed anchor | +0.56 [-0.71, +1.82] | +2.55 [+1.13, +3.98]; replicate +1.54 [+0.30, +2.93] | CI95 | ADMITTED -> REPLICATED | yes, both passes vs the same sealed anchor | RR-gain | B4B, B4BR, LED |
| B7 | B1 exemplars k20 (M1) + B1r | KR+KC | speech-keyed top-20 TRAIN exemplars supplied to the Solver | Fold A | sealed anchor | +2.22 [+0.74, +3.71]; B1r +2.13 [+0.81, +3.38] | +12.61 [+10.54, +14.60]; B1r +13.70 [+11.64, +15.73] | CI95 | ADMITTED -> REPLICATED | yes (B1r, request-identical) | RR-part | B1, B1R, LED |
| B8 | B1 derangement twin | KR | same exemplar supply keyed by ANOTHER row's speech vector | Fold A | B1 and anchor | B1 - twin +2.04 [+0.49, +3.78]; twin - anchor +0.19 [-1.03, +1.39] | B1 - twin +7.83 [+5.85, +9.75]; twin - anchor +4.77 [+3.20, +6.36] | CI95 | decomposition: key 62 % / presence 38 % of the SLU gain | - | RR-part | B1T, LED |
| B9 | B5e (M1 + M4b) | KC | early combination of M1 and M4b | Fold A | anchor; B1 | vs B1 -0.09 [-1.51, +1.38] | 62.34; vs B1 +1.20 [-0.11, +2.48]; vs anchor +13.80 [+11.77, +15.80] | CI95 | combination NEUTRAL (decision 25 addendum) | - | RR-gain | B5E, B5A, LED |
| B10 | B2 v3 grouped samples N=5 (M2) | SA | five Solver samples committed as a group | Fold A | anchor | +0.83 [-0.30, +1.88] | +0.06 [-1.46, +1.60] | CI95 | NEUTRAL (spurious mentions 362 -> 303, omissions up) | - | cons | B2, LED |
| B11 | B8a delivery normaliser (M3) | EN | projection v3 executed inside the agent (label rule + filler surface normalisation) | Fold A; node ON vs OFF on the same sealed arms | same sealed arm, node off (offline) | anchor +1.39 [+0.71, +2.04]; B1 +1.57 | anchor +3.46 [+2.78, +4.18]; B1 +1.53 [+1.05, +2.03] | CI95 | ADMITTED as a surface-convention repair (symmetric scorer moves <= +0.16) | three arms, offline | ok | B8A, A1, LED |
| B12 | B7a v2 NCP L1 | CF+NP | template-built structured context at every node boundary | Fold A | anchor | -0.65 [-2.18, +0.87] | -0.31 [-1.81, +1.12] | CI95 | HARMFUL by width; +11.6 % GPU-h, 59 revisions vs 6 | - | RR-harm | B7A, LED |
| B13 | B4a v2 general_quirky fallback | KR | catch-all fallback candidate + intent-boundaries v2 | Fold A | anchor | +0.74 [-0.30, +1.75] | -0.70 [-2.29, +0.89] | CI95 | HARMFUL by width; fallback appended on 1,052 rows, selected on 0 | - | RR-harm | B4A, LED |
| B14 | EFF-1 constant tool rendering | EN | Reviewer tools array rendered into every role's system message | Fold A | anchor | -9.17 [-11.64, -6.79] | -4.39 [-6.69, -2.17] | CI95 | HARMFUL (measured): 145 tool-call-shaped Solver answers, 137 unparseable rows | - | ok | EFF, LED |
| B15 | B8b-anchor Reviewer slot audit | KC+NP | deterministic slot-audit block attached to the Reviewer | Fold A | anchor | +1.20 [-0.19, +2.59] | +0.87 [-0.63, +2.37] | CI95 | NEUTRAL (every metric positive; +13.5 % GPU-h) | - | cons | B8B, LED |
| B16 | B1-notool (0-B) | EN | Reviewer task-contract tool withdrawn | Fold A | B1 | -0.19 [-1.33, +0.91] | +0.99 [-0.59, +2.50] | CI95 | NEUTRAL; prefill per row -69 %, GPU-h 3.851 -> 1.611 | - | cons | B1N, LED |
| B17 | IDX knowledge index + pointers | CF | index-centred context assembly (constant index, pointer block, bounded expansion) | Fold A | B1-notool | -2.41 [-4.56, -0.32] | -7.37 [-9.72, -4.80] | CI95 | HARMFUL (measured on SLU) | - | RR-part | IDX, LED |
| B18 | IDXT index twin | CF | the same index form with deranged content | Fold A | B1-notool; IDX | +0.19 [-2.00, +2.31]; content IDX - IDXT -2.59 [-4.33, -0.86] | -9.97 [-12.46, -7.32]; content IDX - IDXT +2.60 [+0.80, +4.49] | CI95 | HARMFUL as a control: the loss is the FORM | - | RR-part | IDT, LED |
| B19 | PLAN (v2.0 lock arm) | SY | M1 + M4b + M3 + retired toolkit + E13 / E20 / E22 as one arm | Fold A | B1-notool | +2.22 [+0.92, +3.56] | +1.50 [-0.04, +3.24] | CI95 | NEUTRAL (intent 'proven', SLU unproven); 63.63 / 82.22 | PLANr (B20) | RR-gain | PLN, LCK, LED |
| B20 | PLANr | IN | request-identical replicate of PLAN | Fold A | PLAN | +0.28 [-0.74, +1.25] | +0.17 [-1.11, +1.38] | CI95 | REPLICATED; v2.0 LOCKED; own null h 1.2485 / 0.9943 | - | n/a | PLR, LCK, LED |
| B21 | B9a-rec Acquisition node | NP | kind (a) knowledge re-query node | Fold A | PLAN | 0.00 [-1.10, +1.08] | +0.26 [-1.19, +1.60] | CI95 | NON-INFERIORITY NOT PROVEN; inert (18 ACQUIRE, 0 items returned) | - | cons | B9A, LED |
| B22 | B6 PLAN vs direct | SY | the locked plan vs the bare core, same chain | DEV-2000-ADDED (1,000) | direct 38.09 / 61.7 | +14.90 [+11.78, +18.03] | +27.30 [+24.05, +30.50] | CI95 | DESCRIPTIVE (65.40 / 76.6; replicate 65.15 / 76.8) | PLANr on DEV (CELL-3 chain) | ok | B6, BNK, LED |
| B23 | R-PRIM Reviewer primitives | NP | Reviewer verdict as a closed primitive vocabulary | Fold A | PLAN | -0.09 [-1.16, +0.94] | +0.58 [-0.82, +1.80] | CI95 | NEUTRAL; parse 100 %, ACCEPT 1,073 of 1,091, REVISE recall 0.017 | - | cons | RPM, LED |
| B24 | P1 Reviewer 3 -> 1 | NP | Reviewer max_iterations 3 -> 1 | Fold A | R-PRIM | +0.09 [-0.69, +0.90] | -0.15 [-1.38, +1.24] | CI95 | NEUTRAL (near no-op: 11 rows had a second visit) | - | cons | P1, LED |
| B25 | P0 review loop off | NP | Reviewer 0 / Planner 0 on the locked plan | Fold A | R-PRIM | -0.56 [-1.60, +0.52] | -0.36 [-1.45, +0.78] | CI95 | NEUTRAL; contacts 4.03 -> 2.00 per row | - | cons | P0, LED |

### 1.3 Era C -- Stage 3 (R01C 625, TRAIN Fold A 1,080, DEV-2000-ADDED 1,000)

| # | cell | family | what changed | roster | comparator / null | delta intent pp [CI] | delta SLU-F1 pp [CI] | CI | verdict as recorded | replicated | instrument | src |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C1 | ADV-1 semantic advantage | TF | system-level advantage statements over ROLL-1 groups | R01C 225 disagreeing rows | - | - | - | - | STRUCTURAL PASS (no effect claim) | - | n/a | ADV, LED |
| C2 | CELL-1 (TF-GRPO deltas v1r) | TF | 379 node-targeted deltas applied to the locked plan | Fold A | sealed PLAN (no in-chain A/A) | -0.74 [-2.17, +0.57]; twin +0.09 | -0.48 [-2.18, +1.24]; twin -0.44 | CI95 | NEUTRAL by width | - | cons | CL1, INS, LED |
| C3 | CELL-2 (v2 retained deltas) | TF | 200 retained deltas (per-scenario frontier retention) | Fold A | sealed PLAN (no in-chain A/A) | -0.09 [-1.22, +0.96]; twin -0.93 | +0.64 [-0.76, +1.92]; twin +0.05 | CI95 | NEUTRAL by width; per-scenario content gains +7 to +15 pp reported | - | RR-gain | CL2, GEN, LED |
| C4 | CELL-1-GEPA | TF | 448 GEPA reflective-proposer deltas | Fold A | sealed PLAN (no in-chain A/A) | -0.09 [-1.54, +1.32]; twin -0.28 | -0.04 [-1.58, +1.39]; twin -0.76 | CI95 | NEUTRAL by width | - | cons | GEP, INS, LED |
| C5 | CELL-3 scenario-gated deltas | TF | coverage-gated application of the v2 store | DEV-2000-ADDED | sealed PLAN; in-chain PLANr own null | 0.00 [-1.01, +1.00] | -1.44 [-2.88, -0.05]; twin +0.38 | CI95 | HARMFUL by rule -> 'not distinguishable from flight variance' (instrument sec. 4) | PLANr -0.25 | corr | CL3, CL3D, INS, LED |
| C6 | ROLL-AA within-flight A/A | IN | two greedy passes of the locked plan inside one flight | R01C 200 | itself | 0 of 200 intent flips | -0.284 [-1.096, +0.373]; 91.5 % byte-identical | CI95 | h_within 0.735 (SLU) / 0.000 (intent) | - | n/a | RAA, INS |
| C7 | VAR-1 (K10 / K30 / DIV / K16C5 / PLANR) | KR+KC | exemplar budget 10 / 30, diverse exemplars, Perception k16 + 5 candidates | R01C 625 | PLANR (in-chain request-identical replicate) | PLAN 70.56, PLANR 69.28, K10 69.76, K30 70.72, DIV 70.88, K16C5 70.88 | vs PLANR: K10 +0.07 [-1.48, +1.58], K30 +0.09 [-1.47, +1.60], DIV -1.70 [-3.39, -0.06], K16C5 -1.71 [-3.37, -0.07]; PLANR - PLAN +1.87 [+0.41, +3.36] | CI95 | NO ADMISSION; measured the cross-flight A/A floor | PLANR | RR-harm | VR1, INS, LED |
| C8 | VAR-2 supply variants | SA | per-row supply-variant interleaving at the Solver | R01C | - | - | - | - | ENGINEERING-CLOSED, no number (cumulative supply 40 > bound 38) | - | n/a | VR2, LED |
| C9 | ROLL-1 + AGG offline read | SA | five T 0.7 Solver samples; 13 delivery rules read offline | R01C 625 (sealed pool) | mean single sample, same pool | mean single 70.18; flown 70.56 | medoid +0.03 [-0.63, +0.71]; support s3 +1.40 [+0.55, +2.29]; flown commit +1.62 [+0.77, +2.51]; oracle +6.55 [+5.56, +7.56] | CI95 | aggregation route CLOSED (decision 112): edits are FP suppression already flown; nil on the 225 disagreeing rows | offline | ok | AGG, DEC |
| C10 | VERIFY-1 self-selection | SA | the core chooses one of its five sealed samples | R01C 625 | mean single sample, same pool | +0.544 [+0.032, +1.088] | +0.70 [-0.26, +1.65] | CI95 | BENEFIT NOT PROVEN (the only non-noise Stage-3 intent signal before AGREE) | - | ok | VFY, INS, LED |
| C11 | combined-commit offline read | SA | 29 delivery / commit rules incl. legality prune and per-field composition | R01C 625 (sealed pool) | flown plurality-support commit | self-selection agrees with plurality on 615 of 625 | best +0.117 [-0.87, +0.99]; 15 rules clear the floor as LOSSES; per-field ceiling +0.036 over whole-answer | CI95 | 0 of 29 as a gain; commit line closed | offline | ok | COM, HND |
| C12 | F10 empty-answer demonstrations | CF+KC | explicit empty-answer form in the exemplar view | R01C 625 | in-chain control arm (no A/A) | 70.72 -> 70.88 | +0.34 [-1.42, +2.29]; empty-gold FP -22 vs non-empty FN +13 | CI95 | BENEFIT_NOT_PROVEN, CLOSED | - | cons | F10, LED |
| C13 | evidence-path tools availability | NP+EN | native lookup schemas exposed to the Reviewer (0 calls made) | R01C 625 | in-chain control arm (no A/A) | -0.64, CI90 [-2.24, +0.96] | +0.54 [-0.88, +2.00] | CI95 | NOT QUALIFIED; input-isolation defect (prefix changed on all 625) | - | cons | EVP, LED |
| C14 | system memory family (batch001 / 002, event credit, group update) | TF | whole-system semantic memory learned from 4-input batches | 4 TRAIN inputs x 4 trajectories | empty memory | - | no demonstrated gain (one draw 59.78 -> 53.53) | - | CONSTRUCTION DIAGNOSTIC; learner credited tool events that never happened | - | n/a | MEM, MEV, LED |
| C15 | DET np1 cache-off pair | IN | the locked plan twice on one slot, prompt cache off | Fold A 50 | itself | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0]; 50 of 50 byte-identical | CI95 | DESCRIPTIVE: the band is an np4 serving property; np1 4.2x slower | - | n/a | DET, LED |
| C16 | ROLL-3 DEV pool | SA | five T 0.7 samples of the locked form on the evaluation roster | DEV-2000-ADDED 1,000 (sealed pool) | - | per-sample mean 75.76; any-sample 77.5 (+1.74); one intent on 90.5 % of rows | per-sample 61.94-64.01; oracle 71.06 | - | DESCRIPTIVE: intent errors are systematic across samples | - | n/a | RL3, INS, LED |
| C17 | CONV conversion probe | KR | AGREE treatment on the 70 rows whose gold boundary it newly delivers | Fold A 70 (gold-selected) | sealed PLAN answers | m = 32 of 70 = 45.71 % [34.57, 57.30] (Wilson) | - | CI95 | DESCRIPTIVE (form proof, no pooled claim) | AGREE flown conversion 32 of 72 (44.4 %) | n/a | CNV, AGR, LED |
| C18 | KPROBE conversion probe | KR | centroid boundary key on the 55 rows whose gold boundary it newly delivers | Fold A 55 (gold-selected) | sealed PLAN answers | m = 24 of 55 = 43.64 % [31.37, 56.73] (Wilson, computed here) | - | CI95 | DESCRIPTIVE (form proof) | - | n/a | KPB, CMP |
| C19 | AGREE (agreement term) | KR | exemplar-intent agreement fused into Perception's boundary ranking (w_agree 1.0, recall k 60, 8-1-8) | Fold A 1,080 | in-chain A/A (w_agree 0.0), same campaign | 82.50 -> 85.83, +3.33 [+1.57, +5.09] (67 saves / 31 harms) | 63.31 -> 65.16, +1.85 [+0.23, +3.47] | CI95 | ADMITTED on Fold A, pending fresh-roster replication; retained into COMP-1 (decision 161) | pending (COMP-1 DEV round) | ok | AGR, DEC |


Model-free diagnostics that feed sections 2-5 but are not cells: the bad-case bank [BNK], the
general-scenario diagnostic [GEN], the CELL-3 loss diagnostic [CL3D], the candidate-support,
trajectory, acquisition-requery, decision-state and group-feedback audits [CSD, TRJ, REQ, DSA, GRP],
the intent-error decomposition [IED], the label-ceiling audit [ILC], the retrieval-rank diagnostic
[IRR], the knowledge-base pruning measurement [KBP], the coverage and failure-mode attribution [KCF],
the gold-position read [GPS], the Reviewer/Planner global-state audit [RPG], the supply dedup
measurement [DDP], the `train_synthetic` analysis [TSY], the boundary-key diagnostic [BKC], the M1
compression analysis [M1C] and the throughput baseline [TPT].

## 2. The pattern

### 2.1 Where every admitted gain came from

| family | cells | the gain | why the evidence says it worked |
| --- | --- | --- | --- |
| KC: the label space in the prompt | A1 | intent +17.80 [+15.70, +19.90] over M0 [CLB] | the core cannot answer in a label space it is not shown; 80.5 % of an earlier retrieval cell's intent margin was reproduced by the inventory alone [CLB, LED] |
| KC: slot knowledge on the slot decision | A3, A11 | KC-S1b pooled SLU +8.55; the equal-contact control KC-S1a +0.09 [KCS]; KV-2 cards +7.16 over KV-0 [KV] | the content, not the extra contact: the same second look without a schema is worth nothing [KCS] |
| KR+KC: speech-keyed TRAIN evidence | A14, B7, B8 | KU-S3 speech key +3.65 [+1.60, +5.70] over its form twin [KU3]; M1 +12.61 / +13.70 SLU, key share +7.83 [+5.85, +9.75] (62 %) [B1T, B1R] | M1 is **convention transfer**: 213 of its 277 saves changed only slots (76.9 %), and 133 of the 154 newly correct fillers are printed verbatim in the block (86.4 %) [M1C]; the exemplars move the delivered intent toward the neighbour vote by only +1.3 pp [M1C] |
| KC: a representation contract for a failing slot class | B6 | M4b +2.55 [+1.13, +3.98], replicated +1.54 [+0.30, +2.93] [B4B, B4BR] | the named mechanism moves in the counts: date omissions 81 -> 77 -> 76, filler distance 814 -> 751 -> 749 [B4BR] |
| KR: utterance-space evidence at intent retrieval | C19 (probe C17) | AGREE intent +3.33 [+1.57, +5.09], SLU guard +1.85 [+0.23, +3.47] vs in-chain A/A [AGR] | delivery of the gold boundary on the 191 PLAN intent-wrong rows 86 -> 156; 32 of the 72 newly delivered wrong rows converted (44.4 %, CONV predicted 45.71 %); a further 35 saves on rows delivered in both flights, where the term reorders the eight entries; 60 of the 67 saves land on the two intent-error classes [AGR, CNV] |
| SY: the system around the core | A22, A23, B1, B22 | native system +14.43 / +14.80 SLU on NEW500 [NAT, DSR]; anchor +14.65 SLU / +4.26 intent on Fold A [DIR]; locked plan +27.30 SLU / +14.90 intent on DEV-2000-ADDED [B6] | composite: retrieved slot knowledge plus a candidate-bound answer; no component attribution inside these contrasts |
| EN: deterministic delivery repair | A2, B11 | projection v2 intent +1.50 (15 saves / 0 harms, one stratum) [PRJ]; M3 +3.46 SLU / +1.39 intent on the anchor, +1.53 on B1 [B8A] | aligns the output with the scorer's conventions; about three quarters is case alignment the symmetric scorer scores at zero (moves at most +0.16) [A1, B8A] |

**Common cause.** Every one of these adds information the core did not have *for this row* (a legal
label set, a slot schema, the closest TRAIN utterances and their fillers, a representation contract for
dates and times, a better-ranked intent entry) at the node that decides, or it repairs the form of the
delivered answer deterministically. None of them changes how the nodes are wired.

### 2.2 Where every harm came from

Harms measured outside the band (a CI95 upper bound below zero well beyond the cross-flight offset):

| cell | loss | what the change did to the node's input or output |
| --- | --- | --- |
| B14 EFF-1 | intent -9.17 [-11.64, -6.79], SLU -4.39 [-6.69, -2.17] [EFF] | a tools array in every system message made the Solver answer with a tool-call-shaped string on 145 of 1,092 contacts; 137 rows unparseable. The delivery shape broke, not the reasoning: on the 938 rows both arms parsed the delta is +0.03 SLU / +0.21 intent [EFF] |
| B17 / B18 IDX, IDXT | SLU -7.37; twin -9.97 [-12.46, -7.32] [IDX, IDT] | the loss is the FORM (twin minus base); terse index lines were read but misled (expanded-stratum precision 0.67 -> 0.52) [IDX] |
| A15 KU-S4N | SLU micro -11.74 [-15.18, -8.16] (CI90) [KU4] | candidate NARROWING removed options before the answer |
| A10 KV-0 | 41.75 against KC-S1b 44.35 [KV] | the schema's examples removed |
| A18 discriminative values | row-F1 -6.06 [DSV, LED] | a re-rendering of the slot knowledge |
| C2-C4 delta stores on uncovered strata | `general` intent -10.00 (CELL-1), -6.67 (CELL-2), twin -11.67 [GEN] | every row carried a supply; strata the store did not cover paid a form cost that the derangement twin reproduces [GEN] |

**Common cause.** Each changed the form, volume or shape of what a node reads, or removed options,
without adding evidence matched to the row -- or it broke the output contract. The core is sensitive to
form: a block it cannot use costs accuracy even when it is correct (the IDXT twin carries correct
content in the wrong place and loses 9.97 points).

The other "HARMFUL" words in the record (B0/B0r, B7a v2, B4a v2, role coverage, CELL-3) were decided by
interval width or inside the cross-flight band; section 6 re-reads them as not distinguishable.

### 2.3 Why the control plane is null

Review loop off (B5, B25), Reviewer 3 -> 1 (B24), primitive verdicts (B23), NCP L1 (B12), the
Acquisition node (B21), Reviewer tool availability (C13), the live intent/slot programs (A16, A17) and
the no-knowledge second contact (A4, A5) all read inside the band. The sealed trajectories say why:

- The loop rarely acts. Of the wrong first Solver answers on R01C, 29 of 481 (PLAN) and 26 of 478
  (PLANR) received an actual revision (6.03 % / 5.44 %); revisions repaired 2 / 7 and newly broke 2 / 4
  answers [TRJ]. R-PRIM's parseable verdict accepted 1,073 of 1,091 visits and its REVISE recall is
  0.017 against 598 wrong rows [RPM]. On the anchor the loop changed at most 2 of 1,080 delivered
  intents [B0].
- When it acts it cannot deliver: the Reviewer's verdicts steer nothing, the Planner can only route,
  and the ACCEPT route delivers the latest Solver draft [GPS].
- It is misinstructed: 52 of the Reviewer's 82 instruction tokens (63 %) order a task-contract tool
  retired as item E25, against 0 tool schemas in 2,590 contacts [RPG, DEC row 135]; 319 / 313 Reviewer
  states parse as a top-level `tool_call` JSON and that protocol text then became the Acquisition
  query (E36b replay) [REQ]; the system-memory learner credited tool events that never happened [MEV].
- The one form that added row-relevant content at the Reviewer (B8b slot audit) read positive on every
  metric and unproven (+0.87 / +1.20) at +13.5 % GPU hours [B8B].

### 2.4 What sampling, aggregation and selection can and cannot do

- Intent: ROLL-3's five T 0.7 samples on DEV-2000-ADDED keep one intent on 90.5 % of rows; any-sample
  intent is 77.5 against a per-sample mean of 75.76 (+1.74) [RL3]. Intent errors are systematic, so no
  selection among samples can move intent materially. VERIFY-1's self-selection intent +0.544
  [+0.032, +1.088] is real but small [VFY].
- Entities: the samples differ (pairwise entity-set flips 31.41 %, byte identity 61.46 % [RL3]) and the
  best-of-5 oracle is +6.55 [+5.56, +7.56] on R01C [AGG] and 71.06 against per-sample 61.94-64.01 on
  DEV [RL3]. No verbatim rule captures it (medoid +0.03 [-0.63, +0.71]); the rules that edit the answer
  (+1.40, +1.62) do so by pooled false-positive suppression, are nil on the 225 rows where the samples
  disagree, and are the commit ROLL-1 already flies [AGG]; 0 of 29 commit rules beat the flown commit
  as a gain and per-field composition is worth +0.036 [COM].
- Grouped sampling on the anchor (B2 v3) read +0.06 SLU: fewer spurious mentions (362 -> 303) paid for
  by more omissions [B2].

### 2.5 Why the learned-delta families could not show a gain

CELL-1, CELL-2 and CELL-1-GEPA (Fold A) and CELL-3 (DEV-2000-ADDED) supplied deltas to every row and
reached up to 93 % of rows at the Solver [GEP] without a pooled effect; per-delta outcomes were strongly
heterogeneous (Solver deltas +5 to +6.5 pp SLU on 100+ rows beside -4 to -5 pp) [CL1]. The CELL-3
diagnostic places the store's attributable part at -0.35 pp above its own null, diffuse over 120
values, with no Fold A -> DEV transfer and a perfect gate performing about like PLAN [CL3D]. The
instrument note gives the structural reason: a re-run costs one to three GPU hours and carries a flight
offset larger than the update's effect, so these loops climbed a gradient they could not see [INS
section 5]. The system-memory family learned from 4-input batches and is a set of form proofs by the
instrument's rule 5 [MEM, INS].

### 2.6 The instrument lesson

- Inside one np4 flight the locked plan is nearly deterministic: 91.5 % byte-identical, 0 of 200
  intent flips, h_within 0.735 SLU [RAA].
- Between two np4 flights, request-identical arms differ: +1.87 [+0.41, +3.36] SLU at n = 625 (with
  intent -1.28), +0.17 / +0.28 on Fold A, -0.25 on DEV [INS, VR1]; the AGREE A/A reproduced PLAN at
  +0.28 intent / -0.32 SLU with 823 of 1,080 answers byte-identical [AGR].
- On np1 with the prompt cache off, 50 of 50 rows are byte-identical across two flights [DET]: the
  offset is a property of four-slot continuous batching with the prompt cache over a q8_0 KV cache,
  not of the model or the harness.
- Sub-roster splits of a cross-flight contrast swing by about +-2 pp for free: CELL-3's 355 gated rows,
  which received byte-identical prompts, read -2.20 [-4.38, -0.03] against PLAN [CL3D]. A 60-row
  scenario stratum is noisier still: the DEV-1000 own null moved per-scenario intent by -5.13 to +5.41
  with nothing changed [LGP, NUL]. Per-scenario "gains" and "harms" of single cross-flight cells are
  therefore not evidence.
- The gold-selected conversion probe is the cheapest readable design for a retrieval-side intent
  mechanism, because an intent flip inside one flight is attributable (0 of 200): CONV cost 0.1239
  GPU-h and predicted 32 of 70 conversions, which the AGREE arm reproduced as 32 of 72 [CNV, AGR].

### 2.7 The mechanism explanation the evidence supports

1. **The core uses what it is given and cannot find what it is not given.** On Fold A the gold intent's
   boundary entry is among the delivered eight on 97.3 % of correct rows and on 45.0 % of intent-wrong
   rows [IRR]; on the anchor no uncovered row was finally correct (0 of 143) [ANC]. When the gold entry
   is newly delivered, 43.6-45.7 % of wrong rows convert [CNV, KPB]. The Solver is free over all 60
   intents and still beats its own neighbour vote by +4.8 pp [GPS, M1C].
2. **Intent error is a retrieval-key problem more than a reasoning or label problem.** 55.0 % (Fold A),
   55.4 % (R01C) and 64.2 % (DEV) of intent-wrong rows never received their gold boundary although the
   store holds it [KCF]; the missed gold is spread down the tail (median rank 10-14), so widening k buys
   little at high token cost (k 16 still misses over two thirds, +1,189 tokens per row) [IRR]. The
   written key is an 84-character description per intent [BKC]; gold is rank 1 on 4.7 % of Fold A
   intent-wrong rows under it and 23.0 % under a centroid of TRAIN utterances [BKC]; the exemplar vote
   (utterance-to-utterance) puts gold first on 76.1 % of all rows against 65.6 % for the boundary cosine
   [IRR]. More knowledge does not help (per-intent error rises with exemplar count, rho +0.265 [KCF]),
   pruning does not help [KBP], and the labels are not the limit (0.00 of Fold A's 17.78 error points
   unwinnable, 14.44 plainly ours, 3.33 on the catch-all) [ILC].
3. **Entity error is a use and representation problem, not an availability problem.** The slot
   contract for a missed type was delivered on 98.3 % of ENTITY-MIXED and 98.8 % of ENTITY-FN-ONLY items
   on Fold A (modes (iv)+(v)) [KCF]; mode (iii) budget exclusion is 0 of 2,705 rows [KCF]. On empty-gold
   rows the system emits entities on 114 of 191 (R01C) [TRJ] although 89.3 % of Fold A FP-only rows
   received at least one entity-free exemplar [KCF].
4. **Form costs are systematic.** A block the core cannot use costs points even when correct (IDXT),
   and the delta stores' form cost on uncovered strata is reproduced by their twins [IDT, GEN].
5. **The control loop has no lever** as built (section 2.3).

### 2.8 Where the evidence is thin

- AGREE is one flight on one roster, and that roster is the one on which the retrieval-rank read chose
  its weight grid [IRR]; the fresh-roster read (DEV-2000-ADDED, inside COMP-1 round 2) is owed before any
  claim (decision 161). Its CI95 lower bound (+1.57) sits below the ~2.5 pp design bar [AGR].
- CONV and KPROBE are gold-selected rosters of 70 and 55 rows; their conversion intervals are about
  +-11 to +-13 points (computed here for KPROBE: Wilson [31.37, 56.73] %).
- M4b's two passes share one sealed anchor; the second pass (+1.54) is inside the band [B4BR].
- KC-S1b and KU-S3 were read in the DEV-1000 closed-list pipeline, per-row, at n = 500; they were not
  re-read on the native plan as separate factors (M1 carries fillers, M4b and the slot contracts carry
  schema).
- Fold A has been exposed to every Stage-2/3 cell; DEV-2000-ADDED is the only fresh roster with reads
  (B6, CELL-3, ROLL-3). No per-scenario number in this record carries a CI.

## 3. Cumulative accounting on a common roster

TRAIN Fold A (1,080 rows, official unprojected scorer). Each step is the recorded paired contrast of
that cell against the named predecessor; the steps come from different flights and are **not
additive** (owner decision 23); each carries the cross-flight band of about +-1.25 pp (h 1.2485 / 0.9943
[PLR]) and a possible offset.

| step | arm | SLU-F1 | intent | step delta SLU [CI95] | step delta intent [CI95] | against | src |
| --- | --- | ---: | ---: | --- | --- | --- | --- |
| 0 | bare core, direct max512 | 33.885 | 73.70 | - | - | - | DIR |
| 1 | native dual-store agent (anchor) | 48.53 | 77.96 | +14.65 [+11.79, +17.51] | +4.26 [+2.15, +6.46] | direct | DIR |
| 2 | + M1 speech-keyed exemplars (B1) | 61.14 | 80.19 | +12.61 [+10.54, +14.60] | +2.22 [+0.74, +3.71] | anchor | B1, DEC |
| 2r | B1r (replicate) | 62.23 | 80.09 | +13.70 [+11.64, +15.73] | +2.13 [+0.81, +3.38] | anchor | B1R |
| 3 | + M4b (B5e) | 62.34 | 80.09 | +1.20 [-0.11, +2.48] | -0.09 [-1.51, +1.38] | B1 | B5E |
| 3a | + M3 node on B5e (offline) | 63.78 | 81.85 | +1.44 [+1.00, +1.92] | +1.76 | B5e, node off | B8A |
| 4 | Reviewer tool withdrawn on B1 (B1-notool) | 62.13 | 80.00 | +0.99 [-0.59, +2.50] | -0.19 [-1.33, +0.91] | B1 | B1N |
| 5 | PLAN = M1 + M4b + M3 + withdrawal (v2.0 lock) | 63.63 | 82.22 | +1.50 [-0.04, +3.24] | +2.22 [+0.92, +3.56] | B1-notool | PLN |
| 5r | PLANr (replicate) | 63.80 | 82.50 | +0.17 [-1.11, +1.38] | +0.28 [-0.74, +1.25] | PLAN | PLR |
| 6 | AGREE in-chain A/A (the lock's bytes) | 63.31 | 82.50 | -0.32 [-1.74, +1.14] | +0.28 [-0.74, +1.30] | PLAN | AGR |
| 7 | + agreement term (AGREE) | 65.16 | 85.83 | +1.85 [+0.23, +3.47] | +3.33 [+1.57, +5.09] | its A/A | AGR |

Computed here from the level columns: direct -> AGREE is **+31.27 SLU / +12.13 intent**. Split by the
level differences along the chain (cross-flight, not additive, reported only to show where the mass
sits):

| block | SLU | share | intent | share |
| --- | ---: | ---: | ---: | ---: |
| native agent around the core (0 -> 1) | +14.65 | 47 % | +4.26 | 35 % |
| speech-keyed exemplars M1 (1 -> 2) | +12.61 | 40 % | +2.23 | 18 % |
| lock composition M4b + M3 + withdrawal + E13/E20/E22 (2 -> 5) | +2.49 | 8 % | +2.03 | 17 % |
| agreement term (5 -> 7, against PLAN) | +1.53 | 5 % | +3.61 | 30 % |

Two readings follow, both descriptive. The SLU mass came from slot-side content (the native system's
slot contracts, copied exemplar fillers, the date/time contract) and a surface repair (M3 alone is
+1.53 on B1 offline [B8A], i.e. most of the 2 -> 5 SLU step may be convention). The intent mass came
from the system structure (a candidate-bound answer) and, most recently, from retrieval (AGREE is the
largest single intent step since the native system itself).

Other rosters, for orientation only (different scorers or rosters; never subtracted from the chain):
DEV-2000-ADDED direct 38.09 / 61.7 -> PLAN 65.40 / 76.6 (+27.30 [+24.05, +30.50] / +14.90 [+11.78,
+18.03]), PLANr 65.15 / 76.8 [B6, BNK]; R01C VAR1-PLAN 58.51 / 70.56 and PLANR 60.38 / 69.28 [VR1].
Distance to the owner's 95 % intent target (decision 137): Fold A after AGREE 9.17 points (about 99
rows, computed here); DEV-2000-ADDED at PLAN 18.40 points [IED]; the label ceiling is 100.0000 % on both
rosters [ILC].

## 4. What the negative results rule out, and what is under-explored

### 4.1 Closed lines -- do not re-fly

| line | evidence rows | why it is closed | what would reopen it |
| --- | --- | --- | --- |
| semantic-delta application (TF-GRPO, GEPA, gated) | C2-C5 | four cells, no pooled effect; content gains only where a store has reach, offset by a form cost elsewhere; no Fold A -> DEV transfer (decision 111) [CL1, CL2, GEP, CL3, CL3D] | an offline or same-flight design over sealed trajectories whose update is row-matched (retrieved) content [INS section 5] |
| knowledge index and pointer form | B17, B18 | the form loses 9.97 SLU; terse lines mislead (decision 72) [IDX, IDT] | nothing at the defaults; index content only as a retrieved, row-matched value |
| aggregation, commit and self-selection over samples | B10, C9-C11, C16 | verbatim selection null; edits are FP suppression already in the flown commit; per-field +0.036; intent systematic (decision 112) [AGG, COM, RL3] | a new ranking signal for entities (not intent) |
| candidate width and supply volume | B2, B3, C7, A15 | width 5, K60 broad, exemplar k 10 / 30, diversity and Perception k16 / c5 all inside the A/A band; narrowing harms [C5, BFK, VR1, KU4] | none: volume is not protective (per-intent rho +0.265 [KCF]) |
| knowledge-base pruning | KBP | refuted for removal: 2 of 60 keys net positive and both destroy correct work; greedy ceiling zero (decision 142) [KBP] | none |
| review-loop tuning and NCP L1 | B5, B12, B23-B25 | inside the band; the loop reaches about 5-6 % of wrong answers and repairs about equal harms [TRJ, RPM] | a review whose verdict can change the answer on evidence it names (not a retuning of this loop) |
| Acquisition as built (kind (a) re-query; E36b lexical search) | B21 | inert (18 ACQUIRE, 0 items) [B9A]; the replayed query is contaminated by `tool_call` protocol text [REQ] | a speech-plus-state query with the protocol text removed (decision 90) |
| tool rendering and tool availability | B14, C13 | constant rendering broke delivery; exposed tools were never called [EFF, EVP] | none |
| catch-all fallback candidate as appended | B13 | appended on 1,052 rows, selected on 0 [B4A] | a discriminative key or decision rule, not another candidate (section 4.2) |
| transcript supply, silence tail, logprob judge | A21, A7, A9 | not established / a redistribution inside the band / loses to the free legality judge [WHS, T2S, LGP] | none |
| `train_synthetic` expansion | TSY | 18 clean items, ceiling +0.83 / +0.59; 63 of 81 candidates are self-re-synthesis leakage (decisions 132, 136) [TSY, DEC] | the one test read showing entity weakness (decision 136) |
| memory learned from 4-input batches | C14 | form proofs only; the learner credited nonexistent tool events [MEM, MEV] | batches of at least 200 rows and the G5 instruction repaired first [INS rule 5, RPG] |
| per-row supply variants (VAR-2) | C8 | engineering-closed; a third attempt is forbidden [VR2] | a design whose bound covers the whole revision horizon [INS rule 2] |

### 4.2 Under-explored -- a positive signal that was never pushed

| signal | evidence | why it was never pushed | measured headroom (an oracle, not a forecast) |
| --- | --- | --- | --- |
| **relevance order at the rendering boundary** | exemplars are the cosine top-20 on 1,080 of 1,080 rows but rendered in lexicographic id order; Spearman between position and rank 0.007 [M1C]; AGREE's 35 saves on rows delivered in both flights come from re-ordering the eight entries [AGR] | never a cell; zero-token change | after AGREE, 89 Fold A rows have the gold boundary delivered and the intent still wrong (40 newly delivered + 49 delivered in both) = 8.2 pp (computed here from [AGR]) |
| **slot-side retrieval and filtering** | the candidate-conditioned slot view is built and registered but disabled (decision 125); it projects the whole store and never retrieves (decision 126); the slot-contract block is about 4,855 tokens per Solver contact on the B1 arm and 90.6 % of its characters are cards for slot types neither the core nor the annotation used [M1C] (5,359 tokens of slot-contract cards per first Solver contact on ROLL-2 [TPT]); KU-S3's speech key read +3.65 [KU3]; the staged fetch of slot exemplars keyed by speech plus the drafted intent (decision 47) never flew | the programme moved to intent after the lock | ENTITY-MIXED 193 / 195 rows, +17.4 / +16.5 SLU oracle on Fold A / DEV (decision 127 quoting [BNK]) |
| **an explicit empty-entity decision** | 114 of 191 empty-gold R01C rows emit entities [TRJ]; ENTITY-FP-ONLY 131 / 108 rows [BNK]; the support filter's +1.40 is FP suppression [AGG]; F10 made emptiness explicit and traded FP -22 for FN +13 [F10] | F10 closed on a pooled number; no row-level signal was used | the FP-only class is 12.1 % / 10.8 % of rows [BNK] |
| **utterance-space intent keys** | centroid key delivers gold on 71.2 % of Fold A intent-wrong rows vs 45.0 % written; an all-utterances key 88.0 % [BKC]; the agreement term realised most of it (156 of 191) [AGR] | the key file was rebuilt only for the KPROBE probe | COMP-1's composition delivers 162 of 191; of the 27 catch-all rows no single factor delivers, the composition reaches 5 [CMR] |
| **the catch-all intent** | `general_quirky` owns 25.5-31.4 % of not-delivered intent-wrong rows [IRR]; 3.33 of Fold A's 17.78 error points [ILC]; 36 distinct top-1 rivals [KBP]; AGREE moved `general` intent 40.00 -> 50.00 (7 saves / 1 harm) [AGR] | B4a added a candidate, not a decision rule | at most 3.33 pp intent on Fold A [ILC] |
| **discriminative boundary keys and bodies** | the 60 boundary bodies share a mean Jaccard word overlap of 0.6073 [KBP]; the key is an 84-character facet text, not the body [BKC]; top confusions are within-scenario pairs and the catch-all [BNK] | rewriting is a construction act with its own authority (decision 142) | the confusion pairs of [BNK] section 1a (7, 6, 4, 4, 4 rows ...) |
| **high-FN slot types beyond date/time** | FN rates order_type 77.3 %, audiobook_name 75.0 %, radio_name 65.2 %, song_name 63.6 %, business_name 57.4 %, date 45.8 % of 310 gold mentions [KCF section 5.2]; M4b's contract revision replicated on dates [B4BR] | M4b stopped at date and time | per-type FN mass (for example business_name 39 FN, date 142 FN over the two PLAN rosters [KCF]) |
| **Reviewer entity audit** | B8b positive on every metric (+0.87 / +1.20), saves above harms on all five per-row metrics [B8B] | read NEUTRAL, never re-flown on the locked plan | unknown |
| **entity headroom across samples** | oracle +6.55 on R01C [AGG], 71.06 vs 61.94-64.01 on DEV [RL3]; entity-set flips 31.41 % pairwise [RL3] | no signal ranks samples on entities | +6.55 / about +7 SLU, oracle |

## 5. Next mechanisms for the large-scale phase, ranked (a ranking, not a decision -- decision 139)

Ordered by expected intent / SLU gain per GPU hour, judged from the evidence rows named. "Headroom" is an
oracle bound or a row count from sealed reads, never a forecast. Costs: a Fold A arm has cost 1.67-1.88
GPU-h and its in-chain A/A about the same [PLR, AGR]; a DEV-2000-ADDED arm 1.65-1.75 [B6, CL3]; a
gold-selected conversion probe 0.12 [CNV]; an offline read over a sealed pool 0.

| rank | mechanism | metric | evidence rows | headroom | design (floor) | GPU-h | why this rank |
| ---: | --- | --- | --- | --- | --- | ---: | --- |
| 1 | **fresh-roster replication of the agreement term** (COMP-1's DEV-2000-ADDED round, after the registered Fold A arm, declared +3.23 pp intent [CMP]) | intent | C19, C17; [IRR] section 3; [CMP] | on DEV the agree-1 term delivers gold on 78.0 % of the 232 intent-wrong rows vs 35.8 % (+42.2 points, about 98 rows computed here) against +36.6 on Fold A | cross-flight with in-chain A/A (bar about 2.5 pp at n = 1,000) | ~3.4 | the only mechanism with a gain that clears rule 3 on intent; replication is also the precondition for any claim (decisions 115, 161) and for the test-sample milestone (decision 151) |
| 2 | **rank-ordered, rank-visible rendering of the delivered boundary and exemplar blocks** | intent (selection given delivery) | B7 [M1C] (order discarded, Spearman 0.007), C19 (35 re-ordering saves), [GPS] | 89 delivered-but-wrong Fold A rows after AGREE (8.2 pp) | conversion probe on the delivered-but-wrong rows first (0.12), then arm + in-chain A/A | 0.1 + 3.5 | zero-token form change aimed at the largest remaining intent mass; the one form change in the record that ADDS a row-matched signal (rank) rather than volume |
| 3 | **slot-side retrieval**: enable the candidate-conditioned slot view with a retrieval / legality / top-k filter, plus speech-plus-candidate-keyed slot-filler exemplars | SLU-F1 (intent guard) | A3, A14, B7 [M1C], [KCF], decisions 47, 125, 126 | ENTITY-MIXED +17.4 / +16.5 SLU oracle; about nine tenths of a ~4.9k-token contract block is for unused slot types [M1C] | arm + in-chain A/A, SLU primary | ~3.5 | the one family (row-matched slot knowledge) with repeated admitted gains, now aimed at the largest SLU mass; also a prefill saving |
| 4 | **explicit empty-entity decision** fed by sample agreement on emptiness | SLU-F1 (FP) | B10, C9, C12, [TRJ], [BNK] | FP-only 12.1 % / 10.8 % of rows | OFFLINE first over the sealed ROLL-2 (Fold A) and ROLL-3 (DEV) pools (floor 0.51-0.67 pp [HND, INS]), a flight only if it clears | 0 (+3.5) | free to read; a positive signal (FP suppression) exists but has never been isolated from the whole-answer commit |
| 5 | **discriminative key and body rewrite for the confusion pairs and the catch-all** | intent | B13, C18, [KBP], [BKC], [BNK], [ILC], [CMP] | catch-all at most 3.33 pp; 22 of the 27 catch-all rows stay undelivered even under COMP-1 [CMR] | offline delivery read (0), conversion probe (0.1), then arm + A/A | 0.1 + 3.5 | bounded ceiling and a construction step first, but it attacks the rows COMP-1 cannot reach |
| 6 | **contract revision for the high-FN slot types** (M4b successor) | SLU-F1 | B6, [KCF] section 5.2 | per-type FN mass | arm + A/A | ~3.5 | the M4b mechanism replicated, but each type is small and the gain is SLU-only |
| 7 | **centroid key as its own factor** | intent | C18, [CMP] | +6 delivered rows over AGREE on the 191 (156 -> 162) [AGR, CMR]; x 0.436 is about 2.6 rows = 0.24 pp (computed here); COMP-1's own upper reading is 8 x 0.4364 x 0.0926 = 0.32 pp [CMP] | inside COMP-1 only; not separately readable at any floor | 0 marginal | nearly nested in the agreement term (47 of its 55 rows shared) |
| 8 | **Reviewer entity audit on the locked plan**, after G5 | SLU-F1 | B15, B23, [TRJ], [RPG] | unknown | arm + A/A | ~3.5 (+13.5 %) | the control loop's reach is the binding limit; low expected return until the loop can change answers |

**Multipliers, not gains** (each raises the gain per GPU hour of every row above): the dispatcher slot fill
(27.3 % of ROLL-2's slot capacity sat empty; up to +37.6 % contacts per GPU hour [TPT], decision 159);
P0 review-off (contacts per row 4.03 -> 2.00 at -0.36 / -0.56 unproven [P0]) once its no-harm is read
under decision 127; G5 (-51 tokens per Reviewer contact, 52.3 per row [G5]); and the conversion probe as the first read of every retrieval-side intent mechanism (0.12
GPU-h against about 3.5 for an arm, and it predicted AGREE's conversion within one row [CNV, AGR]).

## 6. Past verdicts to re-read against the corrected instrument

Rule 3 of the instrument: a cross-flight gain needs an in-chain A/A, a CI95 lower bound above zero and a
delta above that A/A's offset plus its half-width (about 2.5 pp at n = 1,080, about 3 pp at n = 625).
Rule 4: never claim from a single cross-flight contrast against an older sealed comparator. A "HARMFUL"
decided by interval width is the same reading turned around.

| cell | recorded | corrected reading | why |
| --- | --- | --- | --- |
| B5 B0 / B0r review off | HARMFUL (twice, by width) | not distinguishable from flight variance | point estimates -0.37 intent / +0.13 SLU; lower bounds crossed an own-null margin with no measured loss [B0, B0R] |
| B12 B7a v2 NCP L1 | HARMFUL by width | not distinguishable; the cost finding (+11.6 % GPU-h) stands | point estimates inside the margins [B7A] |
| B13 B4a v2 fallback | HARMFUL by width | not distinguishable; the inertness finding (0 selections) stands | [B4A] |
| A20 role coverage | DO_NOT_ADOPT, intent -2.20 negative CI90 | not distinguishable | n = 500 cross-flight, no A/A, inside the ~3 pp band [RCV] |
| C5 CELL-3 | HARMFUL | not distinguishable (already corrected, instrument section 4) | its own gated rows moved -2.20 on byte-identical prompts [CL3D] |
| C7 VAR-1 EX-DIV, PER-K16C5 | -1.70 / -1.71 vs PLANR with CI95 excluding zero | not a harm | both are +0.17 / +0.16 vs PLAN; the spread is the +1.87 A/A offset [VR1] |
| B6 M4b | ADMITTED -> REPLICATED (+2.55, +1.54) | direction supported, size uncertain | both passes vs one sealed anchor, no in-chain A/A; the second pass is inside the band; the date-omission counts carry the mechanism [B4B, B4BR] |
| B19 PLAN | intent +2.22 "proven" | not established | one cross-flight contrast vs the older B1-notool arm; below the ~2.5 bar (the lock itself does not depend on it) [PLN] |
| B7 / B8 M1 intent part | intent +2.22 / +2.13; B1 - twin intent +2.04 | direction only | below the ~2.5 bar; the SLU terms (+12.61, +13.70, +7.83) stand [B1, B1R, B1T] |
| B9 B5e | "M4b inside the combination +1.20 beneficial" | not readable | inside the band [B5E, B5A] |
| B17 / B18 IDX | intent -2.41 [-4.56, -0.32]; content IDX - IDXT +2.60 SLU / -2.59 intent | the intent loss and the content term are not readable; the SLU form loss (-7.37, twin -9.97) stands | [IDX, IDT] |
| C3 CELL-2 (and CELL-1, GEPA) | per-scenario content gains +7 to +15 pp; arm - twin +0.59 / +0.83 | not evidence | 60-row strata swing -5 to +5 under a pure null [LGP, NUL]; these splits were the premise of decision 110's gate, which then lost on its own gated rows [CL3D] |
| A7 TAIL2S | NOT ADMITTED because 5 of 18 scenarios lost | the pooled +1.30 and the per-scenario redistribution are both noise-compatible | [T2S, NUL] |
| A5 KU-S1c | intent +1.50 [+0.30, +2.70] | not readable | inside the band [KU1] |
| A11 KV-2 twin | +1.71 [+0.13, +3.27] | not readable; +7.16 over KV-0 stands | [KV] |
| A14 KU-S3 | speech - twin +3.65 [+1.60, +5.70] (per-row, n = 500) | borderline: at the ~3 pp band, repeated once | [KU3] |
| A19 task agent | micro +2.99 (CI90 > 0), replicated | borderline on SLU; intent +4.20 stands | [TAR] |
| C19 AGREE | ADMITTED on Fold A | consistent with rule 3 on intent (3.33 > A/A offset 0.28 + half-width 1.02, computed here from [AGR]); the SLU guard +1.85 is inside the band; one flight on the fit roster, replication owed | [AGR, IRR] |

## 7. Named capability list (what the system must acquire)

1. **Discriminative intent retrieval in utterance space** -- keys built from and fused with TRAIN
   utterances (partly built: the agreement term; the centroid key is registered in COMP-1).
2. **Consumption of delivered evidence in relevance order**, with the rank visible to the node (not
   built: blocks render in id order).
3. **Retrieved, candidate-conditioned slot knowledge** with a legality / top-k filter at the Solver
   (the view is built and disabled; retrieval and filtering are absent).
4. **An explicit decision that a row carries no entity**, fed by a row-level signal (absent).
5. **A catch-all intent decision** that is a rule over the evidence, not an extra candidate (absent).
6. **A review step that can change the answer on evidence it names**, with a correct instruction
   (G5) and a reach well above 6 % of wrong answers (absent as built).
7. **Measurement that can see sub-2.5-pp effects**: offline reads over sealed pools first, same-flight
   paired designs second (the `supply_variants` path is closed and `outputs.py` must learn it), an
   in-chain A/A for every cross-flight cell, and conversion probes for retrieval-side intent mechanisms.
8. **Throughput**: keep every slot loaded (decision 159) so each read costs fewer GPU hours.

## 8. Records and checks

- This note and its JSON twin are new files; no ledger row, exposure row, receipt or registration is
  written or amended. The results ledger is a transcription of verdicts and this note is not a verdict,
  so it adds no ledger heading.
- `scripts/checks/handoff_freshness_check.py` compares the handoff stamp with the newest
  `docs/results/*.md`; master already reads stale at `610cd583` (the newest results commit, `500973ed`, is
  2026-09-27T13:48:43Z against the stamp 2026-09-27T10:28:14Z [HND]), and merging this note moves the
  newest result date again, so the handoff stamp needs its usual refresh after the merge.

## 9. Sources

Every source key used above resolves here (paths relative to the study repository root unless a branch
is named).

| key | path |
| --- | --- |
| LED | `docs/results/stage2-results-ledger.md` |
| DEC | `docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md` |
| INS | `docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md` |
| CLB | `docs/readiness/2026-09-05-slurp-closed-list-direct-baseline-v1-verdict.md` |
| PRJ | `docs/readiness/2026-09-06-slurp-legal-label-projection-v2-verdict.md` |
| KCS | `docs/readiness/2026-09-05-slurp-slot-stage-kc-s1-v1-verdict.md` |
| KU1 | `docs/readiness/2026-09-05-slurp-consumption-ku-s1-v1-verdict.md` |
| EVO | `docs/readiness/2026-09-06-slurp-evo-s1-round-1-verdict.md` |
| T2S | `docs/readiness/2026-09-09-slurp-silence-tail-v1-verdict.md` |
| NUL | `docs/readiness/2026-09-09-slurp-own-null-replicate-v1-verdict.md` |
| LGP | `docs/readiness/2026-09-09-slurp-logprob-judge-probe-v1-verdict.md` |
| KV | `docs/checks/speech-aware-evidence-acquisition/2026-09-09-kv-recovery/FAMILY-REPORT.md` |
| KU3 | `docs/checks/speech-aware-evidence-acquisition/2026-09-10-ku-s3-max256-recovery-verdict/README.md` |
| KU4 | `docs/checks/speech-aware-evidence-acquisition/2026-09-10-ku-s4n-g2-readout/decision.json` |
| G6 | `docs/readiness/2026-09-10-slurp-live-intent-slots-result.md` |
| PMF | `docs/readiness/2026-09-11-slurp-program-matched-result.md` |
| DSV | `docs/readiness/2026-09-11-slurp-discriminative-values-result.md` |
| TAR | `docs/readiness/2026-09-11-slurp-task-agent-replication-result.md` |
| RCV | `docs/readiness/2026-09-11-slurp-role-coverage-result.md` |
| WHS | `docs/readiness/2026-09-12-slurp-fixed-whisper-result-v1.md` |
| NAT | `docs/readiness/2026-09-13-slurp-direct-vs-native-system-v1-verdict.md` |
| DSR | `docs/results/2026-09-14-slurp-dual-store-base-replication-verdict-v1.md` |
| ANC | `docs/results/2026-09-14-slurp-native-train-a-anchor.md` |
| DIR | `docs/results/2026-09-17-slurp-train-a-direct-anchor-release.md` |
| C5 | `docs/results/2026-09-16-slurp-candidate-five-train-a.md` |
| BFK | `docs/results/2026-09-16-slurp-broad-factored-train-a.md` |
| TTS | `docs/results/2026-09-16-slurp-two-track-evidence-synthesis.md` |
| B0 | `docs/results/2026-09-17-slurp-b0-review-off-verdict.md` |
| B0R | `docs/results/2026-09-17-slurp-b0-review-off-redecision-v2.md` |
| B4B | `docs/results/2026-09-17-slurp-b4b-slot-store-v2-verdict.md` |
| B4BR | `docs/results/2026-09-19-slurp-b4b-replicate-verdict.md` |
| B1 | `docs/results/2026-09-17-slurp-b1-exemplars-k20-verdict.md` |
| B1T | `docs/results/2026-09-18-slurp-b1-twin-verdict.md` |
| B1R | `docs/results/2026-09-19-slurp-b1-replicate-verdict.md` |
| M1C | `docs/results/2026-09-19-slurp-m1-exemplar-compression-analysis-v1.md` |
| B5E | `docs/results/2026-09-18-slurp-b5e-combination-verdict.md` |
| B5A | `docs/results/2026-09-18-slurp-b5e-combination-verdict-addendum-decision-25.md` |
| B2 | `docs/results/2026-09-19-slurp-b2-samples5-verdict.md` |
| B8A | `docs/results/2026-09-19-slurp-b8a-deliver-normalise-verdict.md` |
| A1 | `docs/results/2026-09-17-slurp-a1-use-projection-audit-v1.md` |
| B7A | `docs/results/2026-09-19-slurp-b7a-ncp-l1-anchor-v2-verdict.md` |
| B4A | `docs/results/2026-09-19-slurp-b4a-fallback-quirky-anchor-v2-verdict.md` |
| EFF | `docs/results/2026-09-19-slurp-eff1-tool-constant-verdict.md` |
| B8B | `docs/results/2026-09-19-slurp-b8b-anchor-reviewer-audit-verdict.md` |
| B1N | `docs/results/2026-09-20-slurp-b1-notool-verdict.md` |
| IDX | `docs/results/2026-09-21-slurp-idx-knowledge-index-verdict.md` |
| IDT | `docs/results/2026-09-21-slurp-idxt-knowledge-index-twin-verdict.md` |
| PLN | `docs/results/2026-09-21-slurp-plan-v2-lock-arm-verdict.md` |
| PLR | `docs/results/2026-09-22-slurp-planr-v2-lock-replicate-verdict.md` |
| LCK | `docs/results/2026-09-22-slurp-v2-lock-v1.md` |
| B9A | `docs/results/2026-09-22-slurp-b9a-rec-acquisition-node-verdict.md` |
| B6 | `docs/results/2026-09-22-slurp-b6-dev2000-added-direct-vs-plan-read.md` |
| RPM | `docs/results/2026-09-22-slurp-review-primitives-verdict.md` |
| P1 | `docs/results/2026-09-23-slurp-prune-reviewer1-verdict.md` |
| P0 | `docs/results/2026-09-23-slurp-prune-review-off-verdict.md` |
| ADV | `docs/results/2026-09-23-slurp-stage3-advantage-r01-read.md` |
| CL1 | `docs/results/2026-09-23-slurp-stage3-delta-cell-r01-verdict.md` |
| CL2 | `docs/results/2026-09-24-slurp-stage3-delta-cell-r02-verdict.md` |
| GEP | `docs/results/2026-09-24-slurp-stage3-delta-cell-gepa-r01-verdict.md` |
| CL3 | `docs/results/2026-09-24-slurp-stage3-delta-cell-r03-gate-verdict.md` |
| CL3D | `docs/results/2026-09-24-slurp-cell3-fresh-roster-loss-diagnostic.md` |
| GEN | `docs/results/2026-09-24-slurp-general-scenario-diagnostic.md` |
| RAA | `docs/results/2026-09-24-slurp-stage3-roll-aa-within-flight-null-read.md` |
| AGG | `docs/results/2026-09-24-slurp-sample-aggregation-offline-read.md` |
| BNK | `docs/results/2026-09-24-slurp-plan-bad-case-bank.md` |
| VR1 | `docs/results/2026-09-25-slurp-var1-complete-evidence.md` |
| VR2 | `docs/results/2026-09-25-slurp-var2-closed-engineering-failure.md` |
| VFY | `docs/results/2026-09-25-slurp-verify1-complete-evidence.md` |
| F10 | `docs/results/2026-09-25-slurp-f10-complete-verdict.md` |
| EVP | `docs/results/2026-09-25-slurp-evidence-path-system-verdict.md` |
| CSD | `docs/results/2026-09-25-slurp-candidate-support-diagnostic.md` |
| TRJ | `docs/results/2026-09-25-slurp-system-trajectory-attribution.md` |
| REQ | `docs/results/2026-09-25-slurp-system-acquisition-requery.md` |
| DSA | `docs/results/2026-09-25-slurp-system-decision-state-audit.md` |
| GRP | `docs/results/2026-09-25-slurp-system-group-feedback.md` |
| COM | branch fable/commit (71bf3b0f): docs/results/2026-09-26-slurp-combined-commit-offline-read.md |
| IED | `docs/results/2026-09-26-slurp-intent-error-decomposition.md` |
| ILC | `docs/results/2026-09-26-slurp-intent-label-ceiling-audit.md` |
| IRR | `docs/results/2026-09-26-slurp-intent-retrieval-rank-diagnostic.md` |
| KBP | `docs/results/2026-09-26-slurp-knowledge-base-pruning-measurement.md` |
| KCF | `docs/results/2026-09-26-slurp-knowledge-coverage-and-failure-mode-attribution.md` |
| GPS | `docs/results/2026-09-26-slurp-gold-position-and-solver-freedom-read.md` |
| RPG | `docs/results/2026-09-26-slurp-reviewer-planner-global-state-audit.md` |
| DDP | `docs/results/2026-09-26-slurp-supply-dedup-and-rerank-measurement.md` |
| TSY | `docs/results/2026-09-26-slurp-train-synthetic-efficient-use-analysis.md` |
| MEM | `docs/results/2026-09-26-system-memory-batch002-consumption-verdict.md` |
| MEV | `docs/results/2026-09-26-system-event-credit001-verdict.md` |
| BKC | `docs/results/2026-09-27-slurp-boundary-key-construction-diagnostic.md` |
| CNV | `docs/results/2026-09-27-slurp-conv-probe-read.md` |
| DET | `docs/results/2026-09-27-slurp-det-np1-pair-read.md` |
| RL3 | `docs/results/2026-09-27-slurp-roll-3-dev2000-added-pool-read.md` |
| TPT | `docs/results/2026-09-27-slurp-throughput-baseline-and-levers.md` |
| AGR | `docs/results/2026-09-27-slurp-agree-w1-fold-a-read.md` |
| CMP | `docs/readiness/2026-09-27-slurp-stage3-comp-1-fold-a-v1-preregistration.md` |
| KPB | `docs/readiness/2026-09-27-slurp-stage3-comp-1-fold-a-v1-preregistration.md (expected_effect_declaration: KPROBE 24 of 55)` |
| CMR | `docs/readiness/2026-09-27-slurp-stage3-comp-1-fold-a-v1/README.md` |
| HND | `docs/handoff/HANDOFF-TO-CHATGPT.md` |
| G5 | `docs/readiness/2026-09-27-slurp-stage3-g5-fold-a-v1-preregistration.md` |
