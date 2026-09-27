# Verdict reclassification under the corrected measurement instrument (owner decision 166)

Date: 2026-09-27. Author: Claude Opus 5.5, records pass for owner decision 166, worktree
`/home/chao/saea-worktrees/fable-reclass`, branch `fable/reclass`.

**Status: RECORDS PASS.** This note re-reads recorded verdicts; it flies nothing, registers no cell, admits
nothing and authorises no flight. It edits no verdict note: every verdict note stays as written, and the
reclassification is carried by this note and by annotations in `docs/results/stage2-results-ledger.md` and
`.json`. Every number is a development number on an exposed TRAIN or DEV roster (owner decisions 28 and 86),
never a test, superiority or generalisation claim.

**Model-free.** Zero model, tokenizer, encoder, embedder, ASR, scorer, server, network and GPU contacts; nothing
under `SPEECHRL_DATA_DIR` was opened. Every number is transcribed from a committed verdict, read note, receipt or
owner-decision row named in the item's source; the only arithmetic here compares a transcribed effect with a
transcribed floor, and each comparison is written out in the table.

**The owner's instruction (decision 166, 2026-09-27, translated):** "Do not completely overturn ChatGPT's
earlier work; although he did not follow your rules, state our experiment rules explicitly to him in the handoff
document. Where a conclusion is usable but the experiment non-rigorous, keep it provisionally; where both the
conclusion and the experiment are unacceptable, adjust it." The rules are written out for the ChatGPT side in
`docs/handoff/EXPERIMENT-RULES-FOR-CHATGPT.md`.

## 0. The answer

1. **57 items re-read: 30 KEEP, 16 KEEP-PROVISIONAL, 11 ADJUST.** An item is one recorded
   verdict, or one named claim inside a verdict where the synthesis or this pass separated it (for example "the
   intent part of M1", or "the per-scenario content gains of CELL-2").
2. **Every ADJUST is a loss or a gain the rig cannot see, recorded as if it could.** Eight are HARMFUL or loss
   readings whose effect sits inside the applicable floor (B0, B0r, B7a v2, B4a v2, role coverage, CELL-3, IDX's
   intent part, the Audio2Tool staged control), two are per-stratum readings used as evidence (the delta cells'
   per-scenario content gains, the silence tail's harness HARMFUL), and one is an admission granted inside the
   Earnings-21 own null (the self-constrained draft refresh). The status words are changed in place in the
   ledgers with the original word and date kept before the arrow; no row is deleted.
3. **No ADJUST re-opens a closed line and none reverses a plan decision.** In every case the disposition the
   verdict drove (keep the review loop, close B4c, close the L1 family, close the delta-application line, keep
   KC-E1f, do not adopt role coverage) holds for a different reason: inertness, cost, or the absence of a
   readable benefit.
4. **The decisions that rested on a now-provisional or adjusted verdict** are 6, 9, 13, 25, 32, 110, 111, 113,
   and 143 / 161 (section 5). Decision 110 is the one whose premise is withdrawn outright: the per-scenario
   content gains of CELL-2 are not evidence, and the cell it designed (CELL-3) is itself re-read as
   not distinguishable from flight variance. Decision 111 stands, on the absence of a demonstrated benefit
   across four cells, as the instrument note already said.
5. **ChatGPT's session is almost entirely KEEP (11 of 12 items).** Its VAR-1 read was the first in the record to
   read a variant against an in-chain A/A and name the offset, and that correction became rule 3 of the
   instrument; VERIFY-1 is the one offset-free positive intent read of Stage 3; its null verdicts (F10, evidence
   path, the system-learning batches) claim nothing the rig cannot see. The one provisional item is F10's
   mechanism counts. The Codex session is 18 KEEP, 7 KEEP-PROVISIONAL and 3 ADJUST; its native system
   (+14.4 pp SLU over direct, three flights) is the foundation every later cell stands on.

## 1. How each verdict was re-read

### 1.1 The instrument

`docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md` is binding for every Stage-3 claim from
2026-09-26 and is applied here to the whole record. Its floors (section 2d):

| design | n | CI95 half-width (SLU) | flight offset it carries |
| --- | ---: | ---: | --- |
| offline read over one sealed sample pool | 625 | 0.67 | none |
| two passes inside one flight (A/A) | 200 | 0.735 (intent 0.000) | none |
| cross-flight A/A, R01C construction roster | 625 | 1.474 (intent 1.760) | +1.87 SLU / -1.28 intent measured |
| cross-flight A/A, TRAIN Fold A | 1,080 | 1.2485 (intent 0.9943) | +0.17 / +0.28 measured |
| cross-flight A/A, DEV-2000-ADDED | 1,000 | 1.2525 (intent 1.1520) | -0.25 / +0.20 measured |
| terminal feedback on 4-16 trajectories | 4-16 | not readable | dominant |

Rule 3: a cross-flight arm is read only against an in-chain request-identical replicate, and a gain is admitted
only when its CI95 lower bound is above zero and the delta exceeds the replicate's measured offset plus that
offset's half-width. Rule 4: never claim from a single cross-flight contrast against an older sealed comparator
with no in-chain replicate. Rule 5: under about 200 rows is a form proof. DET (2026-09-27, np1 with the prompt
cache off, 50 of 50 rows byte-identical across two flights) locates the between-flight band in the np4 serving
geometry; the AGREE error-source read (`docs/results/2026-09-27-slurp-agree-arm-error-sources.md`, section 1.1) measures
it at row level: three sealed flights of the same plan deliver byte-identical boundary blocks on all 1,080 Fold A
rows and still disagree on intent on 27-33 rows per pair, about 15 saves and 15 harms for a no-op arm.

### 1.2 The bars used

A cell without an in-chain A/A is held to the rule-3 bar scaled to its row count exactly as
`scripts/checks/stage3_effect_floor_check.py` scales it (square root of anchor n over n, from the anchor nearest
in log n; anchors 3.0 pp at 625 and 2.5 pp at 1,080):

| rows | bar (pp) | where it applies |
| ---: | ---: | --- |
| 60 | 9.7 | one scenario stratum of Fold A |
| 355 | 3.98 | CELL-3's gate-closed split |
| 500 | 3.35 | NEW500 / OLD500 reads of the DEV-1000 era |
| 625 | 3.00 | R01C |
| 1,000 | 2.60 | DEV-1000, DEV-2000-ADDED |
| 1,080 | 2.50 | TRAIN Fold A |
| 4,000 | 1.30 | Audio2Tool union-4000 (a SLURP-derived bar; Audio2Tool has none of its own) |

A cell WITH an in-chain A/A is held to |offset| + half-width of that A/A instead (CELL-3: 0.25 + 1.2525 = 1.50;
AGREE: 0.28 + 0.9943 = 1.27 on intent; VAR-1: 1.87 + 1.474 = 3.34). The same bound read in the other direction
decides whether a claimed LOSS is distinguishable from flight variance: a HARMFUL reading is a claim, and it
needs the same evidence a gain does. The DEV-1000 era reported CI90 intervals; the bars compare point estimates,
so the interval level does not change a class.

Two other carriers carry their own floors. **Earnings-21**'s own null is the same request flown twice (a
cross-flight A/A over all 44 calls): corpus WER half-width 0.058, PERSON 0.250, ORG 0.356, non-entity 0.065,
numeric 0.157 (`docs/readiness/2026-09-08-e21-own-null-replicate-v1-verdict.md`), so an Earnings-21 effect many
times those widths is read as measured even against a historical arm. **Audio2Tool** has no own null
(A2T-NULL NOT MEASURED; A2T-AA is registered under decision 144), so every Audio2Tool effect is provisional until
that floor exists. The **DEV-1000 closed-list era** had its own byte-identical re-flight (SLURP-NULL): intent
+0.50 [-0.40, +1.43] with half-width 0.92, micro SLU-F1 half-width 1.18, scenario 0.8255, and 11 of 11 metrics
moving the same way with nothing changed; its per-scenario intent moved -5.13 to +5.41.

### 1.3 The classes and the conventions

- **KEEP**: conclusion and experiment sound under today's rules. **A null verdict (NEUTRAL, NULL, NOT ADMITTED,
  NOT QUALIFIED, BENEFIT NOT PROVEN, NOT ADVANCED) is KEEP whatever its design's power**: a wider band only makes
  "not established" truer. The instrument note read CELL-1, CELL-2 and CELL-1-GEPA's NEUTRAL labels the same way.
- **KEEP-PROVISIONAL**: the conclusion is usable (a direction that nothing contradicts, a disposition that holds
  for a stated reason), the experiment is below today's rules; the exact rule missed and the flight or read that
  would settle it are named. "Direction only" means the sign is supported, usually by a repetition, and the size
  is not.
- **ADJUST**: the conclusion and the experiment are both unacceptable: a harm or a gain claimed inside the floor
  that applies to it, or a per-stratum reading used as evidence. The new word is written in place in the
  ledgers, after the original word and its date.
- **Closed lines stay closed.** Where the settling action is "none", the line is closed or superseded and a
  re-read would matter only if the owner re-opened it; where a settling action is named, it is owed only if its
  question still matters (it is never scheduled by this note, decision 139).
- **Sessions** are attributed from the commit record: the Codex session runs from the file-based handoff "from
  Fable5.1 to Codex" (2026-09-09 06:16Z) to the Fable 5.1 takeover commit (2026-09-17 01:18Z); the ChatGPT session
  from the VAR-1 evidence commit (2026-09-25 08:48Z) to the last ChatGPT design commit (2026-09-26 13:45Z), after
  which Fable 5.1 landed the uncommitted ChatGPT work (`15c13a00`). VAR-1 flew under a Fable 5.1 registration
  and was read by the ChatGPT session; it is counted with the ChatGPT session. ChatGPT's readiness design notes
  are designs, not results, and are not classified (section 7).

## 2. Counts per class

| session | KEEP | KEEP-PROVISIONAL | ADJUST | items |
| --- | ---: | ---: | ---: | ---: |
| Fable 5.1 (first tenure, to 2026-09-09) | 1 | 1 | 1 | 3 |
| Codex session (2026-09-09 to 2026-09-16) | 18 | 7 | 3 | 28 |
| Fable 5.1 (2026-09-17 to 2026-09-24) | 0 | 6 | 7 | 13 |
| ChatGPT session (2026-09-25 to 2026-09-26) | 11 | 1 | 0 | 12 |
| Claude Opus 5.5 (2026-09-27) | 0 | 1 | 0 | 1 |
| **all** | **30** | **16** | **11** | **57** |

The two Fable 5.1 tenures carry 8 of the 11 ADJUST items: the HARMFUL-by-width
convention and the per-scenario premise of decision 110 were the coordinator's, not ChatGPT's.

## 3. The full table

Each row: what was recorded, the class, the effect against the floor that applies to it, the rule missed, and
what would settle it. Sources are the verdict notes named in the ledgers' rows and in the JSON twin's
`reclassification_2026_09_27.items[].source`.

### A. Verdicts recorded as HARMFUL, or read as losses

| id | claim (session) | recorded | class | effect against the applicable floor | rule missed | settling |
| --- | --- | --- | --- | --- | --- | --- |
| A1 | B0 review loop off, first pass (Fable 5.1 (2026-09-17 to 2026-09-24)) | HARMFUL by the preregistered rule (intent CI95 lower bound -1.53 below an imported 0.92 pp margin) | **ADJUST** -> NOT DISTINGUISHABLE FROM FLIGHT VARIANCE; the loop-inertness finding stands | intent -0.37 [-1.53, +0.82], SLU +0.13 [-1.15, +1.45] at n = 1,080 against the sealed anchor: both points inside the roster's own null (B0r h 1.0051 / 1.1218) and far inside the 2.50 pp bar; 22 saves / 26 harms beside the 77 rows whose delivered intent changes between two byte-identical passes (B0r) | HARMFUL declared by interval width on a nil point estimate; imported margin; one cross-flight contrast against a sealed anchor with no in-chain A/A (rule 4) | none owed: P0 (2026-09-23) re-read review-off on the locked plan as NEUTRAL and decision 105 keeps the pruning line closed; a re-opening reads it as a no-harm item under decision 127 |
| A2 | B0r re-decision v2 under the TRAIN A own null (Fable 5.1 (2026-09-17 to 2026-09-24)) | HARMFUL (intent lower bounds -1.527 / -1.313 against -1.0051; SLU -1.150 once) | **ADJUST** -> NOT DISTINGUISHABLE FROM FLIGHT VARIANCE; B0r's own-null measurement (h 1.1218 / 1.0051) stands as an instrument | loop-off minus anchor on the two passes: intent -0.37 / -0.28, SLU +0.13 / +0.10; every point inside h (1.0051 / 1.1218) and inside the 2.50 bar; the failure is interval width only, and both passes share one anchor realisation | HARMFUL by width (the rule treated a non-inferiority failure as a harm); no in-chain A/A for the anchor leg | none owed (as A1); the loop stayed in the plan, so no plan decision rested on the word |
| A3 | B7a v2 Node Context Policy L1 (Fable 5.1 (2026-09-17 to 2026-09-24)) | HARMFUL by the registered rule (interval width, not measured loss); L1 family closed | **ADJUST** -> NOT DISTINGUISHABLE FROM FLIGHT VARIANCE; costs more for no measured benefit, not admitted | SLU -0.31 [-1.81, +1.12], intent -0.65 [-2.18, +0.87] at n = 1,080 against the sealed anchor: points inside the margins 1.1218 / 1.0051 and inside the 2.50 bar. Stands: 5.21 contacts per row, +11.6 % GPU-h, +7.8 % prompt tokens, 59 revisions against 6 | HARMFUL by width; one cross-flight contrast against a sealed anchor, no in-chain A/A | none owed; B7r / B7c stay closed (decision 32); a re-opening flies a no-harm read with an in-chain A/A |
| A4 | B4a v2 general_quirky fallback + intent-boundaries v2 (Fable 5.1 (2026-09-17 to 2026-09-24)) | HARMFUL by the registered rule (SLU lower bound -2.29 against -1.1218); fallback never chosen | **ADJUST** -> NOT DISTINGUISHABLE FROM FLIGHT VARIANCE; inert (appended on 1,052 rows, selected on 0), not admitted | intent +0.74 [-0.30, +1.75], SLU -0.70 [-2.29, +0.89] at n = 1,080: both points inside the margins and the 2.50 bar. Stands: +30 % prompt tokens, +39 % GPU-h | HARMFUL by width; one cross-flight contrast against a sealed anchor, no in-chain A/A | none owed; B4c stays closed (decision 9 required B4a to admit, which fails under either reading) |
| A5 | Role coverage, matched treatment (Codex session (2026-09-09 to 2026-09-16)) | DO_NOT_ADOPT_INTENT_NEGATIVE_ENTITY_UNRESOLVED (NEW500 intent -2.20, CI90 [-3.95, -0.42]) | **ADJUST** -> DO NOT ADOPT (no benefit shown); INTENT LOSS NOT DISTINGUISHABLE FROM FLIGHT VARIANCE | /-2.20/ < 3.35 pp (the bar at n = 500); SLU micro -0.54 [-2.55, +1.34]; the DEV-1000 byte-identical re-flight moved 11 of 11 metrics in one direction with nothing changed | one cross-flight pair with no A/A; not one factor (170 plan texts differ between the arms) | none; the package is closed and superseded by the native system (E18-E20) |
| A6 | CELL-3 scenario-gated deltas on DEV-2000-ADDED (Fable 5.1 (2026-09-17 to 2026-09-24)) | HARMFUL on the SLU guard by the registered rule (-1.44 [-2.88, -0.05]) | **ADJUST** -> NOT DISTINGUISHABLE FROM FLIGHT VARIANCE (instrument section 4, now carried on the status word) | in-chain replicate PLAN vs PLANr on the same roster: offset -0.25, h 1.2525, so the bound is 0.25 + 1.2525 = 1.50 > 1.44; intent 0.00 [-1.01, +1.00]; the 355 gate-closed rows, whose prompts were byte-identical to PLAN's, read -2.20 [-4.38, -0.03] | a loss inside the in-chain replicate's offset-plus-half-width was read as HARMFUL (rule 3 read in the harm direction) | none; decision 111 closed the application line on the absence of a demonstrated benefit across four cells and stands |
| A7 | VAR-1 EX-DIV and PER-K16C5 against PLANR (ChatGPT session (2026-09-25 to 2026-09-26)) | numbers only (-1.70 [-3.39, -0.06] / -1.71 [-3.37, -0.07] vs PLANR); family NO ADMISSION; never called harms | **KEEP** | against PLAN the same arms read +0.17 / +0.16; the family's own in-chain A/A (PLANR - PLAN) is +1.87 with h 1.474, bound 3.34 > 1.71: the -1.70 / -1.71 are the A/A offset, not harms, which is what the note reported | none: the one Stage-3 family that flew its own in-chain A/A | none |

### B. Gains recorded above what the instrument can see

| id | claim (session) | recorded | class | effect against the applicable floor | rule missed | settling |
| --- | --- | --- | --- | --- | --- | --- |
| B1 | M4b slot store v2 (B4b and its replicate) (Fable 5.1 (2026-09-17 to 2026-09-24)) | ADMITTED (+2.55 [+1.13, +3.98]) -> REPLICATED (+1.54 [+0.30, +2.93]) | **KEEP-PROVISIONAL** | first pass 2.55 against the 2.50 bar (+0.05), lower bound 1.13 inside it; replicate 1.54 < 2.50; both against ONE sealed anchor realisation; a third same-sign reading inside B5e (+1.20, B4); mechanism counts carry the direction (time-slot FN mass -32.9, filler-distance mass -28 %) | no in-chain A/A (both passes read against one sealed anchor, rule 4); the replicate's effect is inside the band | only if the size matters: the lock minus slot store v2 against an in-chain A/A (about 3.5 GPU-h per arm); the v2.0 lock does not depend on M4b's size |
| B2 | PLAN arm: intent +2.22 read as 'proven' (Fable 5.1 (2026-09-17 to 2026-09-24)) | NEUTRAL (SLU +1.50 unproven); intent +2.22 [+0.92, +3.56] 'proven' | **KEEP-PROVISIONAL** | +2.22 < 2.50 bar at n = 1,080, one contrast against the older sealed B1-notool arm; the plan's intent level is reproduced by PLANr (82.50) and by the AGREE A/A (82.50) against B1-notool's 80.00, so the direction is supported; 'proven' is withdrawn | rule 4 (a single cross-flight contrast against an older sealed comparator) | none owed: the v2.0 lock rests on PLANr's replication, not on this increment; B6 (+14.90 intent over direct on DEV-2000-ADDED) is the system read |
| B3 | M1 speech-keyed exemplars: the intent part (B1, B1r, B1 minus twin) (Fable 5.1 (2026-09-17 to 2026-09-24)) | ADMITTED -> REPLICATED; intent +2.22 / +2.13 / +2.04 | **KEEP-PROVISIONAL** | intent +2.22 [+0.74, +3.71], +2.13 [+0.81, +3.38], twin term +2.04 [+0.49, +3.78]: each below the 2.50 bar, all against one sealed anchor; direction repeated by a request-identical replicate. The SLU part is KEEP: +12.61 / +13.70 / +7.83 are 5.0x / 5.5x / 3.1x the bar | no in-chain A/A; intent effect inside the band | none owed; decisions 18 and 37 rest on the SLU terms, which stand |
| B4 | B5e: M4b's share inside the combination (Fable 5.1 (2026-09-17 to 2026-09-24)) | combination NEUTRAL (decision 25 addendum); M4b share +1.20 recorded as 'beneficial, unproven' | **KEEP-PROVISIONAL** | +1.20 [-0.11, +2.48] over the sealed B1 arm: below the 2.50 bar with a CI crossing zero; readable only as a third same-sign reading of M4b (B1) | one cross-flight contrast against a sealed arm, no A/A; effect inside the band | none (the combination question closed with the lock) |
| B5 | IDX knowledge index: the intent 'measured loss' (Fable 5.1 (2026-09-17 to 2026-09-24)) | HARMFUL, both guards a measured loss (intent -2.41 [-4.56, -0.32]) | **ADJUST** -> intent loss NOT DISTINGUISHABLE FROM FLIGHT VARIANCE; the cell's HARMFUL stands on SLU (-7.37 [-9.72, -4.80], 2.9x the bar) and the twin's form loss (-9.97) stands | /-2.41/ < 2.50 bar at n = 1,080; one contrast against the sealed B1-notool arm, no A/A | a loss inside the band read as measured | none; the index line is closed on its SLU form loss |
| B6 | IDX minus IDXT content term (Fable 5.1 (2026-09-17 to 2026-09-24)) | content +2.60 SLU / -2.59 intent (IDX minus its derangement twin) | **KEEP-PROVISIONAL** | +2.60 [+0.80, +4.49] SLU and -2.59 [-4.33, -0.86] intent sit 0.10 / 0.09 beyond the 2.50 bar with bounds far inside it; two flights, no A/A between them: direction only | no in-chain A/A; effect at the bar | none (line closed) |
| B7 | KU-S1c draft-revise control: intent +1.50 (Fable 5.1 (first tenure, to 2026-09-09)) | REPORTED, NEVER DECIDED; intent +1.50 CI90 [+0.30, +2.70], +1.20 of it the control turn | **KEEP-PROVISIONAL** | +1.50 at n = 1,000 against the 2.60 bar and against the DEV-1000 A/A's own bound (offset +0.50 + h 0.92 = 1.42); the revise contact's +0.30 [-0.40, +1.00] is inside every floor | one cross-flight contrast, no in-chain A/A | none (the closed-list pipeline is superseded); the netting convention it introduced stays as method |

### C. Per-scenario and per-stratum claims

| id | claim (session) | recorded | class | effect against the applicable floor | rule missed | settling |
| --- | --- | --- | --- | --- | --- | --- |
| C1 | CELL-1 / CELL-2 / CELL-1-GEPA per-scenario content gains and arm-minus-twin terms (Fable 5.1 (2026-09-17 to 2026-09-24)) | content gains +7 to +15 pp where the store has reach (news +7.4, alarm +4.2, qa +4.2, weather +4.1 SLU); arm - twin +0.59 / +0.83 (CELL-2), +0.73 / +0.19 (GEPA) | **ADJUST** -> NOT EVIDENCE (strata and twin terms of cross-flight contrasts, no CI, no A/A); the NEUTRAL status words stand | a 60-row stratum's bar is 3.0 x sqrt(625/60) = 9.7 pp; the DEV-1000 pure A/A moved per-scenario intent by -5.13 to +5.41; CELL-3's byte-identical 355-row split moved -2.20; the twin terms (<= 0.83) are inside the 2.50 bar; the pooled arms were -0.48 / +0.64 / -0.04 | per-stratum reads of a cross-flight contrast used as evidence; no in-chain A/A | none; decision 110 rested on this reading and its cell (CELL-3) is A6; the line is closed (decision 111) |
| C2 | CELL-3 fresh-roster loss diagnostic (Fable 5.1 (2026-09-17 to 2026-09-24)) | gated rows -2.20 vs PLANr +0.61 (noise); store part -0.35 pp above its null; harm diffuse over 120 values; no Fold A -> DEV transfer; perfect-gate bound about PLAN | **KEEP-PROVISIONAL** | the noise reading (about +-2 pp on 355-row splits; bar 3.98 at n = 355) and the perfect-gate bound (an offline computation over sealed arms) stand; the -0.35 store part and the per-scenario 'no transfer' comparison are far below any floor and are not readable | sub-floor attributions reported beside a sound noise measurement | none (line closed) |
| C3a | SLURP silence tail: scientific status (Fable 5.1 (first tenure, to 2026-09-09)) | NOT ADMITTED (intent +1.30 CI90 [+0.19, +2.43] did not clear +0.60) | **KEEP** | +1.30 at n = 1,000 is below the 2.60 bar and below the DEV-1000 A/A bound 1.42: no readable gain, so NOT ADMITTED holds under today's rules too | none for the null verdict | none |
| C3b | SLURP silence tail: harness HARMFUL and the 'redistribution' reading (Fable 5.1 (first tenure, to 2026-09-09)) | harness-admission HARMFUL, barred from every default plan; 'a redistribution with a positive sum' (5 scenarios lose, worst takeaway -10.26 on 39 rows = 4 harms) | **ADJUST** -> NOT DISTINGUISHABLE FROM FLIGHT VARIANCE (not admitted for want of a readable gain; not barred for harm) | the scenario guard's CI90 lower bound -0.69 failed an IMPORTED 0.60 margin, while SLURP's own scenario half-width is 0.8255; per-scenario losses on 39-60 rows sit inside the -5.13 to +5.41 swing of the DEV-1000 pure A/A | imported margin; per-stratum sign rule treated as evidence | none owed; docs/receipts/harness-admission.json is not edited by this documents-only pass, and the coordinator supersedes its entry only if the owner wants the tail re-admissible |
| C4 | KV-2 vocabulary cards against their form twin (Codex session (2026-09-09 to 2026-09-16)) | NOT_ADMITTED_ROTATING_TWIN_GATE_FAILED; vs KV-0 +7.16, vs twin +1.71 | **KEEP** | vs KV-0 +7.16 [+5.24, +9.12] (2.1x the 3.35 bar at n = 500) stands; vs the twin +1.71 [+0.13, +3.27] is inside the bar, so NOT ADMITTED holds; the named reason (a rotating-stratum sign, one stratum -1.38) is not evidence, the pooled twin contrast carries the non-admission | none for the null verdict (the named gate was a stratum sign) | none (KV line closed) |

### D. Borderline positives

| id | claim (session) | recorded | class | effect against the applicable floor | rule missed | settling |
| --- | --- | --- | --- | --- | --- | --- |
| D1 | KU-S3 speech-keyed fillers (ADMITTED_COMPONENT and its independent repeat) (Codex session (2026-09-09 to 2026-09-16)) | ADMITTED_COMPONENT; PASS_COMPONENT_REPEAT | **KEEP-PROVISIONAL** | speech - twin +3.65 [+1.60, +5.70] and repeat - twin +4.20 [+2.14, +6.25] (per-row, n = 500, CI90) clear the 3.35 bar by 0.30 / 0.85, their lower bounds do not; repeat - original +0.54 [-0.67, +1.77] is a request-identical replicate whose bound 0.54 + 1.22 = 1.76 both clear | the replicate did not fly in the twin's chain; n = 500 | none owed: the component was absorbed into M1, whose speech-key term (+7.83 SLU) is 3.1x the Fold A bar |
| D2 | Compact-frame task agent (v1 and its replication) (Codex session (2026-09-09 to 2026-09-16)) | v1 INTENT_SIGNAL (+2.60); replication PRIMARY_INTENT_AND_ENTITY_POSITIVE (+4.20 / +2.99) | **KEEP-PROVISIONAL** | replication intent +4.20 [+2.33, +5.97] clears the 3.35 bar (stands); official micro SLU +2.99 [+1.06, +4.91] is below it (direction only); v1's +2.60 [+0.69, +4.40] is below the bar and repeated in direction by the replication | no in-chain A/A; the SLU half inside the band | none (superseded by the native system, E18-E20) |
| D3 | AGREE agreement term on TRAIN Fold A (Claude Opus 5.5 (2026-09-27)) | ADMITTED on TRAIN Fold A, pending fresh-roster replication | **KEEP-PROVISIONAL** | intent +3.33 [+1.57, +5.09] against its in-chain A/A; A/A - PLAN offset +0.28 + h 0.9943 = 1.27 < 3.33 and 3.33 > 2.50: rule 3 met; 67 saves / 31 harms against about 15 / 15 between identical flights (27-33 intent disagreements per pair); SLU guard +1.85 [+0.23, +3.47] | roster reused for selection and reading: the weight grid was chosen by the retrieval-rank diagnostic over Fold A gold, and the read is on Fold A | the COMP-1 DEV-2000-ADDED round (decision 161), already registered |

### E. Every other result of the Codex session (2026-09-09 to 2026-09-16)

| id | claim (session) | recorded | class | effect against the applicable floor | rule missed | settling |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | KV-0 examples-free base (Codex session (2026-09-09 to 2026-09-16)) | HARMFUL; retain KC-S1b | **KEEP-PROVISIONAL** | official micro 44.35 -> 41.75 (-2.60) against the earlier sealed KC-S1b flight at n = 1,000: exactly at the 2.60 bar and above the DEV-1000 A/A bound on micro (0.29 + 1.18 = 1.47); no paired interval for KV-0 vs KC-S1b is reported | one cross-flight contrast against an older sealed comparator; no paired CI | none (KV line closed; the retained base was later superseded by the native plan) |
| E2 | KV-1, KV-3 and the three KV twins (Codex session (2026-09-09 to 2026-09-16)) | NULL_COMPATIBLE (KV-1, KV-3); COMPARATOR_ONLY (twins) | **KEEP** | KV-1 - KV-0 -0.87 [-2.12, +0.31], KV-3 - KV-0 +0.52 [-0.75, +1.80]: inside the 3.35 bar, null verdicts | none for null verdicts | none |
| E3 | KU-S4N G2 intent-candidate narrowing (Codex session (2026-09-09 to 2026-09-16)) | HOLD_NONINFERIORITY_FAILED | **KEEP** | micro -11.74 [-15.18, -8.16] (CI90, n = 500) is 3.5x the 3.35 bar, upper bound beyond it: a measured loss | none | none |
| E4 | Reproduction audit of the first-tenure results (Codex session (2026-09-09 to 2026-09-16)) | NUMERICALLY_REPRODUCED (16,560 statistical fields agree) | **KEEP** | zero-contact recomputation; no effect claim | none | none |
| E5 | E21 draft refresh, unit-constrained and unit-free deliveries (Codex session (2026-09-09 to 2026-09-16)) | REJECTED (both) | **KEEP** | unit-constrained PERSON -1.78 [-2.81, -0.85] against the E21 own-null PERSON half-width 0.250 (7.1x); unit-free corpus WER -5.55 [-5.98, -5.13] against 0.058; the E21 own null is the same request flown twice (a cross-flight A/A), so the carrier's band is measured | none | none |
| E6 | E21 draft refresh, self-constrained delivery (Codex session (2026-09-09 to 2026-09-16)) | ADMITTED_AS_DISCOVERY_REFRESH_IMPROVEMENT (small effect; does not replace KC-E1f) | **ADJUST** -> NOT DISTINGUISHABLE FROM THE EARNINGS-21 OWN NULL (no improvement readable; KC-E1f stays) | corpus WER 8.1995 -> 8.1940 (+0.0056 pp, 20 errors in 359,765 words) against the own-null half-width 0.058 (10x larger); PERSON +0.137 (4 of 2,917 mentions) against 0.250; the note itself says both gain intervals overlap the own-null bands | an admission granted inside the carrier's own same-request null | none (Earnings moved to FlightRuntime, E35) |
| E7 | E21 draft refresh, self-free delivery (Codex session (2026-09-09 to 2026-09-16)) | NULL_NO_DEMONSTRATED_WER_GAIN | **KEEP** | corpus WER +0.0017 [-0.053, +0.087] inside h 0.058: null | none | none |
| E8 | E21 loop packets (judge targeting) (Codex session (2026-09-09 to 2026-09-16)) | RETAIN_KC_E1F_SYSTEM_FLOOR_FAILED | **KEEP** | judge - twin PERSON +1.47 [+0.85, +2.14] (5.9x h 0.250); judge - historical KC-E1f PERSON -1.71 [-2.56, -0.89] (6.9x h); the comparison with a historical sealed arm is rule 4's shape, but the effect is far outside the carrier's measured cross-flight band | none material | none |
| E9 | G6 live intent and slot contacts (Codex session (2026-09-09 to 2026-09-16)) | NOT_FULLY_ADMITTED_GUARD_FAILED (positive slot evidence; scenario point guard -0.2 failed) | **KEEP-PROVISIONAL** | row SLU-F1 +3.26 [+1.09, +5.50] (CI90, NEW500) sits 0.09 below the 3.35 bar: slot evidence is direction only; the failing guard is a point-estimate guard (scenario -0.2 against SLURP's own scenario half-width 0.8255), not a margin | point-estimate guard in place of a non-inferiority margin; no in-chain A/A | none (superseded by the program-matched follow-up and the native system) |
| E10 | E21 offline direct-then-KC-E1f system (Codex session (2026-09-09 to 2026-09-16)) | SYSTEM_NOT_ADMITTED_INSERTION_GUARD_FAILED (PERSON +3.39; five extra insertions) | **KEEP-PROVISIONAL** | PERSON +3.39 [+2.45, +4.40] is 13.6x the own-null half-width 0.250 and stands; corpus WER +0.046 [+0.033, +0.059] is inside h 0.058; the refusal rests on a point guard (+5 insertions of 10,336; rate -0.0014 [-0.0032, +0.0003]) that the note itself calls not a calibrated non-inferiority test | point-estimate guard in place of a margin at the carrier's own null | zero GPU, only if the owner re-opens the Earnings offline repair: re-read the sealed pair's insertion and non-entity rates against the E21 own null (non-entity h 0.06475) |
| E11 | Program-matched live follow-up (Codex session (2026-09-09 to 2026-09-16)) | SYSTEM_NOT_ADMITTED_PRIMARY_AND_INTENT_GUARD_FAILED | **KEEP** | row-F1 CI90 crosses zero and intent -0.2 is inside every floor: a null verdict; the 'intent guard failed' half is a point-guard artefact and is not needed for the refusal | none for the null verdict | none |
| E12 | Discriminative value rendering (span pair) (Codex session (2026-09-09 to 2026-09-16)) | NEGATIVE_COMPONENT_NOT_SELECTED | **KEEP** | row-F1 -6.06 [-8.60, -3.87] (CI90, n = 500) is 1.8x the 3.35 bar with the upper bound beyond it; micro -3.91 | none | none |
| E13 | Audio2Tool native system recovery: headline (Codex session (2026-09-09 to 2026-09-16)) | SYSTEM_NOT_ADMITTED_KNOWLEDGE_NOT_ESTABLISHED | **KEEP** | knowledge - direct -0.30 [-1.12, +0.51] and knowledge - stage control +0.65 [-0.10, +1.43] (97.5 %) both miss the +1.0 threshold: null verdicts; the tool-accuracy decline (-3.475) is reported on a carrier with no measured own null | none for the null verdict (Audio2Tool has no own null: A2T-NULL NOT MEASURED) | none |
| E14 | Audio2Tool native system recovery: 'the staged control is a harmful package' (Codex session (2026-09-09 to 2026-09-16)) | staged control - direct -0.95 exact match, exploratory CI90 below zero: 'a harmful package in this run' | **ADJUST** -> NOT DISTINGUISHABLE FROM FLIGHT VARIANCE (Audio2Tool has no floor of its own; -0.95 is inside the scaled SLURP bar) | n = 4,000 rows in 2,097 query clusters; the rule-3 bar scaled to 4,000 rows is 1.30 pp and 0.95 is inside it; no Audio2Tool A/A exists | a harm claimed on an uncalibrated carrier from one cross-flight contrast | A2T-AA (decision 144) supplies the carrier's floor; re-read offline only if the staged form is re-opened |
| E15 | Fixed Whisper evidence (Codex session (2026-09-09 to 2026-09-16)) | EFFECTIVENESS_NOT_ESTABLISHED | **KEEP** | NEW500 micro +0.83 [-1.10, +2.84] and intent -0.80 inside the 3.35 bar: null; the 'secondary full-roster intent negative' wording is not readable | none for the null verdict | none |
| E16 | Native system vs direct on DEV-1000, its reboot recovery and the max512 base replication (Codex session (2026-09-09 to 2026-09-16)) | EXPLORATORY_SYSTEM_CANDIDATE; recovery pass; REPLICATED useful base | **KEEP** | NEW500 micro +14.43 [+11.21, +17.59], +14.30 [+11.24, +17.50], +14.80 [+11.52, +18.01] (CI90): 4.3x-4.4x the 3.35 bar, three flights; intent +6.2 [+3.41, +9.17] is 1.9x | none | none |
| E17 | TRAIN Fold A native anchor (Codex session (2026-09-09 to 2026-09-16)) | COMPLETE_TRAIN_CONSTRUCTION_ANCHOR (48.53 / 77.96) | **KEEP** | levels, no contrast; the later direct release (+14.65 [+11.79, +17.51]) is 5.9x the 2.50 bar | none | none |
| E18 | Distinct (delayed) commitment (Codex session (2026-09-09 to 2026-09-16)) | SLU inconclusive; positive paired evidence for intent | **KEEP-PROVISIONAL** | intent +2.80 [+1.24, +4.33] on NEW500 (0.55 below the 3.35 bar) and +3.60 [+1.86, +5.47] on OLD500 (0.25 above); pooled SLU +0.01 [-1.29, +1.39] null | no in-chain A/A; intent effect at the bar | none (superseded) |
| E19 | Audio2Tool native role base on union-4000 (Codex session (2026-09-09 to 2026-09-16)) | PRIMARY_GAIN_TOOL_GUARD_FAILED_NOT_ADOPTED (+4.05 exact; tool accuracy -3.60) | **KEEP-PROVISIONAL** | primary exact +4.05 [+2.96, +5.16] (CI95, 4,000 rows, 2,097 query clusters) is 3.1x the scaled bar 1.30 and tool accuracy -3.60 is 2.8x it, but Audio2Tool has no measured A/A and the refusal used a non-negative point guard, not a margin | no carrier own null or in-chain A/A; point guard | A2T-AA (decision 144, registered), then a zero-GPU re-read of the sealed pair against its offset |
| E20 | Audio2Tool attributions and engineering proof (candidate attribution, ordered action, primary parameter, parameter value evidence, role engineering proof) (Codex session (2026-09-09 to 2026-09-16)) | descriptive / engineering | **KEEP** | no effect claim | none | none |
| E21 | Maximum-five candidates and broad / factored knowledge on Fold A (Codex session (2026-09-09 to 2026-09-16)) | NOT_ADVANCED (both) | **KEEP** | +0.09 [-1.36, +1.65] and -0.90 [-2.61, +0.78] inside the 2.50 bar: null verdicts | none for null verdicts | none |
| E22 | Typed-context package (Codex session (2026-09-09 to 2026-09-16)) | CLOSED_SECOND_FAILURE_NO_FURTHER_RECOVERY (engineering; no read) | **KEEP** | no quality read | none | none |
| E23 | SLURP descriptive diagnostics of 2026-09-13 to 2026-09-16 (conditional commitment decomposition, top-3 source intent diagnostic, TRAIN A entity-loss attribution, review-stage attribution, review-context provenance, coverage-gap inventory, construction / consumption inventory, slot-binding footprint, temporal slot diagnosis, two-track synthesis) (Codex session (2026-09-09 to 2026-09-16)) | descriptive | **KEEP** | no effect claim; any cell number they carry is re-read in that cell's own item | none | none |
| E24 | Engineering results of 2026-09-10 to 2026-09-13 (E21 feature preparation, artifact result kind, native speech-tool engineering and recovery, native candidate source, role-request integration, TRAIN feedback bridge, bounded Perception proof, knowledge-fix dry run, role GPU proof, top-3 source and successor engineering) (Codex session (2026-09-09 to 2026-09-16)) | engineering proofs | **KEEP** | no effect claim | none | none |

### F. Every result of the ChatGPT session (2026-09-25 to 2026-09-26)

| id | claim (session) | recorded | class | effect against the applicable floor | rule missed | settling |
| --- | --- | --- | --- | --- | --- | --- |
| F1 | VAR-1 family read and its correction against PLANR (ChatGPT session (2026-09-25 to 2026-09-26)) | NO ADMISSION; CONSTRUCTION READ, NO STABLE WINNER | **KEEP** | K10 / K30 +0.07 / +0.09 over PLANR against an A/A offset of +1.87 (h 1.474); the note's own correction ('reading a variant against PLAN instead of PLANR repeats the coordinator's own error') is adopted into the instrument law | none | none |
| F2 | VERIFY-1 self-selection (recovery flight) (ChatGPT session (2026-09-25 to 2026-09-26)) | BENEFIT NOT PROVEN; NO SYSTEM ADMISSION; intent guard passes | **KEEP** | the comparator is the mean of the same sealed samples, so the design carries no flight offset: SLU +0.70 [-0.26, +1.65] fails the benefit gate (offline floor 0.67); intent +0.544 [+0.032, +1.088] excludes zero against a within-flight intent floor of 0.000 | none | none |
| F3 | VAR-2 closure after its sole recovery (ChatGPT session (2026-09-25 to 2026-09-26)) | ENGINEERING-CLOSED, NO EFFECTIVENESS RESULT | **KEEP** | no number; one-recovery rule obeyed | none | none |
| F4 | F10 empty-answer form: headline (ChatGPT session (2026-09-25 to 2026-09-26)) | BENEFIT_NOT_PROVEN; NOT_QUALIFIED; CLOSED | **KEEP** | +0.34 [-1.42, +2.29] at n = 625 against the 3.00 bar: null; the pair was a fresh in-chain control and treatment with no A/A, so the closure records that the design could not have seen an effect below about 3 pp | none for the null verdict (no in-chain A/A; the law post-dates the flight) | none |
| F5 | F10 mechanism counts ('the mechanism did what it was designed to do') (ChatGPT session (2026-09-25 to 2026-09-26)) | empty-gold FP 142 -> 120 (-22; QA -21) against non-empty FN 384 -> 397 (+13): a specificity / omission trade-off | **KEEP-PROVISIONAL** | entity sets flip on 7.5 % of rows between two passes inside ONE flight and about 28 % of raw outputs differ across flights, so counts of 13-22 over 625 rows sit inside the cross-flight churn: direction only | mechanism counts read from a cross-flight pair with no in-chain A/A | none unless re-opened; then same-flight paired (supply_variants, once core/bundle/outputs.py learns it) or offline over a sealed pool |
| F6 | Evidence-path tools availability (ChatGPT session (2026-09-25 to 2026-09-26)) | NOT QUALIFIED (input-isolation defect named; zero tool calls) | **KEEP** | SLU +0.54 [-0.88, +2.00] and intent -0.64 CI90 [-2.24, +0.96] at n = 625 inside the 3.00 bar: null; the note names its own prefix defect (all 625 first-Perception requests differ) and says it measures an availability policy, not an invoked tool | none for the null verdict (no in-chain A/A; the defect is disclosed) | none |
| F7 | Complete-system group feedback and trajectory attribution over PLAN / PLANR (ChatGPT session (2026-09-25 to 2026-09-26)) | COMPLETE DIAGNOSTIC; NO POLICY UPDATE OR EFFECTIVENESS CLAIM | **KEEP** | descriptive; its 131 utility differences are between request-identical PLAN and PLANR episodes, i.e. they are the A/A band itself, which is consistent with the note's refusal to infer node credit from them | none | none |
| F8 | Acquisition re-query, pre-Solver decision state and candidate-support diagnostics (ChatGPT session (2026-09-25 to 2026-09-26)) | model-free construction diagnostics; no system-gain verdict | **KEEP** | no effect claim | none | none |
| F9 | System-learning batch001 family (resource and learning diagnostic, no-update closure, provisional memory created not evaluated), summary001, comparison001, group-update001 format, batch-synthesis001 rejection, event-credit001 (ChatGPT session (2026-09-25 to 2026-09-26)) | structural / diagnostic statuses (e.g. OBSERVED ERRORS IN SEMANTIC CREDIT, NO QUALIFIED UPDATE) | **KEEP** | 4 inputs x 4 trajectories: form proofs under rule 5; no benefit claimed; the structural findings (credit given for tool events that never happened, invalid memory plans, summary fidelity limits) do not depend on n | none (form proofs, declared as such) | none |
| F10 | Memory batch002 consumption (ChatGPT session (2026-09-25 to 2026-09-26)) | NO DEMONSTRATED TASK IMPROVEMENT | **KEEP** | 4 distinct TRAIN inputs x 4 trajectories per arm: a form proof under rule 5; the one-draw 59.78 -> 53.53 is not readable and the note claims no efficacy | none (form proof) | none |
| F11 | Engineering: rollout batch / prefix capacity baseline and the memory resource-receipt defect (ChatGPT session (2026-09-25 to 2026-09-26)) | engineering | **KEEP** | no effect claim | none | none |

## 4. The ADJUST items, with the reason

- **A1 B0 review loop off, first pass.** HARMFUL by the preregistered rule (intent CI95 lower bound -1.53 below an imported 0.92 pp margin) -> **NOT DISTINGUISHABLE FROM FLIGHT VARIANCE; the loop-inertness finding stands**. Why: intent -0.37 [-1.53, +0.82], SLU +0.13 [-1.15, +1.45] at n = 1,080 against the sealed anchor: both points inside the roster's own null (B0r h 1.0051 / 1.1218) and far inside the 2.50 pp bar; 22 saves / 26 harms beside the 77 rows whose delivered intent changes between two byte-identical passes (B0r).
- **A2 B0r re-decision v2 under the TRAIN A own null.** HARMFUL (intent lower bounds -1.527 / -1.313 against -1.0051; SLU -1.150 once) -> **NOT DISTINGUISHABLE FROM FLIGHT VARIANCE; B0r's own-null measurement (h 1.1218 / 1.0051) stands as an instrument**. Why: loop-off minus anchor on the two passes: intent -0.37 / -0.28, SLU +0.13 / +0.10; every point inside h (1.0051 / 1.1218) and inside the 2.50 bar; the failure is interval width only, and both passes share one anchor realisation.
- **A3 B7a v2 Node Context Policy L1.** HARMFUL by the registered rule (interval width, not measured loss); L1 family closed -> **NOT DISTINGUISHABLE FROM FLIGHT VARIANCE; costs more for no measured benefit, not admitted**. Why: SLU -0.31 [-1.81, +1.12], intent -0.65 [-2.18, +0.87] at n = 1,080 against the sealed anchor: points inside the margins 1.1218 / 1.0051 and inside the 2.50 bar. Stands: 5.21 contacts per row, +11.6 % GPU-h, +7.8 % prompt tokens, 59 revisions against 6.
- **A4 B4a v2 general_quirky fallback + intent-boundaries v2.** HARMFUL by the registered rule (SLU lower bound -2.29 against -1.1218); fallback never chosen -> **NOT DISTINGUISHABLE FROM FLIGHT VARIANCE; inert (appended on 1,052 rows, selected on 0), not admitted**. Why: intent +0.74 [-0.30, +1.75], SLU -0.70 [-2.29, +0.89] at n = 1,080: both points inside the margins and the 2.50 bar. Stands: +30 % prompt tokens, +39 % GPU-h.
- **A5 Role coverage, matched treatment.** DO_NOT_ADOPT_INTENT_NEGATIVE_ENTITY_UNRESOLVED (NEW500 intent -2.20, CI90 [-3.95, -0.42]) -> **DO NOT ADOPT (no benefit shown); INTENT LOSS NOT DISTINGUISHABLE FROM FLIGHT VARIANCE**. Why: |-2.20| < 3.35 pp (the bar at n = 500); SLU micro -0.54 [-2.55, +1.34]; the DEV-1000 byte-identical re-flight moved 11 of 11 metrics in one direction with nothing changed.
- **A6 CELL-3 scenario-gated deltas on DEV-2000-ADDED.** HARMFUL on the SLU guard by the registered rule (-1.44 [-2.88, -0.05]) -> **NOT DISTINGUISHABLE FROM FLIGHT VARIANCE (instrument section 4, now carried on the status word)**. Why: in-chain replicate PLAN vs PLANr on the same roster: offset -0.25, h 1.2525, so the bound is 0.25 + 1.2525 = 1.50 > 1.44; intent 0.00 [-1.01, +1.00]; the 355 gate-closed rows, whose prompts were byte-identical to PLAN's, read -2.20 [-4.38, -0.03].
- **B5 IDX knowledge index: the intent 'measured loss'.** HARMFUL, both guards a measured loss (intent -2.41 [-4.56, -0.32]) -> **intent loss NOT DISTINGUISHABLE FROM FLIGHT VARIANCE; the cell's HARMFUL stands on SLU (-7.37 [-9.72, -4.80], 2.9x the bar) and the twin's form loss (-9.97) stands**. Why: |-2.41| < 2.50 bar at n = 1,080; one contrast against the sealed B1-notool arm, no A/A.
- **C1 CELL-1 / CELL-2 / CELL-1-GEPA per-scenario content gains and arm-minus-twin terms.** content gains +7 to +15 pp where the store has reach (news +7.4, alarm +4.2, qa +4.2, weather +4.1 SLU); arm - twin +0.59 / +0.83 (CELL-2), +0.73 / +0.19 (GEPA) -> **NOT EVIDENCE (strata and twin terms of cross-flight contrasts, no CI, no A/A); the NEUTRAL status words stand**. Why: a 60-row stratum's bar is 3.0 x sqrt(625/60) = 9.7 pp; the DEV-1000 pure A/A moved per-scenario intent by -5.13 to +5.41; CELL-3's byte-identical 355-row split moved -2.20; the twin terms (<= 0.83) are inside the 2.50 bar; the pooled arms were -0.48 / +0.64 / -0.04.
- **C3b SLURP silence tail: harness HARMFUL and the 'redistribution' reading.** harness-admission HARMFUL, barred from every default plan; 'a redistribution with a positive sum' (5 scenarios lose, worst takeaway -10.26 on 39 rows = 4 harms) -> **NOT DISTINGUISHABLE FROM FLIGHT VARIANCE (not admitted for want of a readable gain; not barred for harm)**. Why: the scenario guard's CI90 lower bound -0.69 failed an IMPORTED 0.60 margin, while SLURP's own scenario half-width is 0.8255; per-scenario losses on 39-60 rows sit inside the -5.13 to +5.41 swing of the DEV-1000 pure A/A.
- **E6 E21 draft refresh, self-constrained delivery.** ADMITTED_AS_DISCOVERY_REFRESH_IMPROVEMENT (small effect; does not replace KC-E1f) -> **NOT DISTINGUISHABLE FROM THE EARNINGS-21 OWN NULL (no improvement readable; KC-E1f stays)**. Why: corpus WER 8.1995 -> 8.1940 (+0.0056 pp, 20 errors in 359,765 words) against the own-null half-width 0.058 (10x larger); PERSON +0.137 (4 of 2,917 mentions) against 0.250; the note itself says both gain intervals overlap the own-null bands.
- **E14 Audio2Tool native system recovery: 'the staged control is a harmful package'.** staged control - direct -0.95 exact match, exploratory CI90 below zero: 'a harmful package in this run' -> **NOT DISTINGUISHABLE FROM FLIGHT VARIANCE (Audio2Tool has no floor of its own; -0.95 is inside the scaled SLURP bar)**. Why: n = 4,000 rows in 2,097 query clusters; the rule-3 bar scaled to 4,000 rows is 1.30 pp and 0.95 is inside it; no Audio2Tool A/A exists.

## 5. Owner decisions that rested on a now-provisional or adjusted verdict

| decision | what it rested on | item | class | consequence now |
| --- | --- | --- | --- | --- |
| 6 (re-decide B0 under the TRAIN A own null) | B0's HARMFUL by width | A1, A2 | ADJUST | none to reverse: the path it opened measured the Fold A own null (kept as an instrument) and the loop stayed in the plan; P0 later read review-off as NEUTRAL on the locked plan |
| 9 (B4c flies only if B4a admits) | B4a v2's verdict | A4 | ADJUST | B4c stays closed unflown: B4a does not admit under either reading, and its fallback was selected on 0 rows |
| 13 (M4b's replication path) | B4b and its replicate | B1 | KEEP-PROVISIONAL | the plan keeps slot store v2; "replicated" now means two same-sign passes against one anchor, size unsettled |
| 18, 37 (M1 as speech-keyed supply; M1's replication) | B1, the twin, B1r | B3 | KEEP for SLU, KEEP-PROVISIONAL for intent | both rest on the SLU terms (+12.61, +13.70, +7.83), which stand |
| 25 (combination HARMFUL needs a measured loss; record any beneficial gain) | B5e | B4 | KEEP-PROVISIONAL | the NEUTRAL re-read stands; the recorded "beneficial" M4b share is direction only |
| 32 (if B7a v2 reads HARMFUL, close B7r / B7c and re-base B8b) | B7a v2's HARMFUL by width | A3 | ADJUST | closed lines stay closed (B7a still costs +11.6 % GPU-h for nothing measured); decision 32 was a pre-committed if-then of the kind decision 139 now forbids, recorded here and not reversed |
| 30, 86 and the v2.0 lock (`docs/results/2026-09-22-slurp-v2-lock-v1.md`) | PLAN, PLANr, M1, M4b, M3 | B1, B2, B3 | KEEP-PROVISIONAL parts | the lock stands: it rests on PLANr's request-identical replication and on M1's SLU term; PLAN's "intent proven" and M4b's size are provisional |
| 110 (iteration 3 = a scenario-gated application policy) | CELL-2's per-scenario content gains | C1 | ADJUST | the premise is withdrawn; the cell it designed is A6; the line is closed (111) |
| 111 (close the delta-application line) | CELL-3 HARMFUL plus three NEUTRAL cells | A6, C1 | ADJUST (CELL-3) | stands, on the absence of a demonstrated benefit across four cells (instrument section 4) |
| 113 (the Stage-3 record wording) | per-scenario content gains +7 to +15 pp; every Stage-3 arm "significantly above" B5e (CELL-2 +1.93 SLU [+0.56, +3.34] / +2.04 intent); iteration 1 -> 2 moved +1.12 / +0.65 | C1 | ADJUST (per-scenario), KEEP-PROVISIONAL (the rest) | the per-scenario sentence is withdrawn; "above B5e" is one cross-flight contrast against an older sealed comparator (rule 4) and belongs to the lock anyway (M3 alone moves B5e +1.44 [+1.00, +1.92] SLU offline); the iteration step is inside the band. The owner's instruction in 113 (a detailed account, never "no gain") is unaffected |
| 143, 161 (fly AGREE as a benefit claim; retain it into COMP-1) | CONV (KEEP) and AGREE | D3 | KEEP-PROVISIONAL | provisional by design; the fresh-roster read in COMP-1's DEV round settles it |
| Codex-session dispositions (not numbered in this registry) | role coverage; KV-0; G6; the E21 refresh, loop and offline cells; the Audio2Tool role base | A5, E1, E6, E8, E9, E10, E19 | mixed | none needs reversing: each line is closed or superseded (the compact frame by the native system, the E21 offline form by E35, Audio2Tool by A2T-AA and A2T-SYS-1) |

## 6. What the ChatGPT and Codex work contributes, and where it departed from the rules

**Kept, and load-bearing today.** The Codex session's native four-node system and its two replications (E16:
+14.43, +14.30, +14.80 pp SLU over direct on NEW500) are the system every Stage-2 and Stage-3 cell modifies. Its
KU-S3 speech-keyed fillers (D1) are the first evidence that the speech key carries the gain, later confirmed on
the native plan by M1's twin. Its measured negatives (discriminative values -6.06, KU-S4N narrowing -11.74, the
E21 unit refresh) stand as measured. The ChatGPT session's VAR-1 read (F1) is the first cell in the record that
read its variants against an in-chain A/A and named the offset; that correction is rule 3 of the instrument.
VERIFY-1 (F2) is the one Stage-3 read whose comparator carries no flight offset and whose intent interval excludes
zero. Its structural findings on system learning (F9: credit assigned to tool events that never happened, invalid
memory plans, summary fidelity limits) hold at any n.

**Where the work departed from today's rules** (named so the rules file can cite them, not to overturn them):

- a point-estimate guard used where a non-inferiority margin at the carrier's own null belongs (E9, E10, E11,
  E19);
- an admission granted inside the carrier's own null (E6);
- a loss claimed on a carrier with no floor (E14) or from one n = 500 pair that also changed 170 plan texts
  (A5);
- control / treatment pairs flown without an in-chain A/A (F4, F6; the law post-dates them by a day, and both
  verdicts stayed null, so neither is adjusted), and mechanism counts read from such a pair (F5);
- dated rulings recorded in separate notes instead of the numbered registry (re-entered as rows 115-125 at
  `2e6274eb`), and work left uncommitted in the shared tree (landed unchanged at `15c13a00`);
- a knowledge-construction design whose input overflowed the slot (decisions 126 and 130: the output schema was
  kept, the input is rebuilt) -- a design, not a result, so it carries no class here.

The coordinator's own departures are in the same table and outnumber these: HARMFUL by interval width (A1-A4,
A6), a per-scenario premise for a decision (C1, decision 110), AGREE's weight grid chosen on the roster it was
then read on (D3), READ rows registered after the seal for ROLL-3, AGREE and KPROBE, and ROLL-3's flight rows
flown while still marked draft (both recorded in `scripts/checks/flight_registration_check.py` on branch
`fable/launchgate`).

## 7. Not re-read in this pass

- Verdicts outside both lists: Audio2Tool's A2T-ORG-1 HARMFUL (2026-09-05; Audio2Tool has no own null, so re-read
  it when A2T-AA lands), the Earnings-21 KC-E1 / OBS-E1 rejections (decided against Earnings-21's own
  cross-flight null), and EFF-1's HARMFUL (intent -9.17 [-11.64, -6.79], 3.7x the Fold A bar: measured).
- ChatGPT's readiness design notes of 2026-09-25 and 2026-09-26 (finite policy, trajectory optimisation, terminal
  ratio objective, knowledge construction / consumption, task-specific stores and views, event-grounded credit,
  intent / slot coupling): designs carry no verdict; decisions 116 and 118-126 and 130 already rule on them.

## 8. Records and checks

- New: this note; `docs/handoff/EXPERIMENT-RULES-FOR-CHATGPT.md`.
- Annotated: `docs/results/stage2-results-ledger.md` (a routing section before "The rules this ledger follows";
  one appended line per affected continuation-table row, structured row and dated section; the ADJUST words
  changed in place with the original kept) and `docs/results/stage2-results-ledger.json` (a
  `reclassification_2026_09_27` field on every affected row and continuation entry, a top-level block of the same
  name carrying the counts and every item, the ADJUST status words changed in place, CELL-3's tally moved from
  rejected to neutral with SLURP's carrier summary updated to match, and a supersession note beside
  `stage3_measurement_instrument`).
- Not edited: every verdict note, the receipts (`docs/receipts/harness-admission.json` still says HARMFUL for the
  silence tail; C3b), the exposure ledger, the owner-decision registry (decision 166's row is the coordinator's
  to write), and `docs/handoff/HANDOFF-TO-CHATGPT.md` (the coordinator links the rules file from it).
- `scripts/checks/handoff_freshness_check.py` already fails on master (the newest result, the AGREE read, is
  newer than the handoff stamp), and this note is newer again: the handoff's usual in-place refresh clears it.

## 9. Sources

The item table cites one source per item; the JSON twin carries the same path in each item's `source`. Beyond
those: the mechanism synthesis (`docs/results/2026-09-27-slurp-mechanism-synthesis.md` section 6 and
`docs/results/2026-09-27-slurp-mechanism-synthesis/mechanism-table.json`); the AGREE error sources
(`docs/results/2026-09-27-slurp-agree-arm-error-sources.md` section 1.1); the instrument note; the DEV-1000 own null
(`docs/readiness/2026-09-09-slurp-own-null-replicate-v1-verdict.md`); the Earnings-21 own null
(`docs/readiness/2026-09-08-e21-own-null-replicate-v1-verdict.md`); the owner-decision registry
(`docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`, rows 6, 9, 13, 18, 25, 30, 32, 37, 86,
110-113, 115-126, 130, 139, 143, 144, 161); the DET read (`docs/results/2026-09-27-slurp-det-np1-pair-read.md`);
and the B8a normaliser read (`docs/results/2026-09-19-slurp-b8a-deliver-normalise-verdict.md`) for M3's offline
effect on B5e.
