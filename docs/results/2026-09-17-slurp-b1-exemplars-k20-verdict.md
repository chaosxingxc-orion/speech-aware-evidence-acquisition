# Cell B1 verdict: module M1, twenty speech-keyed TRAIN exemplars supplied to the Solver, on TRAIN A

Status: **ADMITTED pending the twin.** Every clause of the preregistered rule that can be read today
passes -- pooled SLU +12.61 pp with a CI95 lower bound of +10.54 pp above zero, intent non-inferior
and in fact above the 1.0051 pp TRAIN A own null at +2.22 [+0.74, +3.71], the now-registered TRAIN
symmetric scorer agreeing in sign, and no scenario losing intent beyond the null band -- but the
rule's ADMITTED clause also requires a positive CI95 against the **derangement twin**, and the twin
has not flown. Under owner decision 8 of 2026-09-17 the positive arm CI95 is exactly the trigger:
**the twin flies next.** Root: the B1 paired-read agent, 2026-09-17. Program:
`docs/superpowers/specs/2026-09-16-slurp-v2-base-program-design.md` (module M1, cell B1).
Preregistration: `docs/readiness/2026-09-17-slurp-b1-exemplars-k20-anchor-v2-preregistration.md`
(sections 5-7, fixed before contact), with the one allowed recovery registered in
`docs/readiness/2026-09-17-slurp-b1-exemplars-k20-anchor-v2-recovery-v1.md`. Margins: the TRAIN A
own null of cell B0r, **h_SLU = 1.1218 pp** and **h_intent = 1.0051 pp** at CI95
(`docs/results/2026-09-17-slurp-b0-review-off-redecision-v2.md`).

## What flew: two attempts, one of them aborted

**Attempt 1, ABORTED.** Run SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TRAIN-FOLD-A-V2, attempt
attempt-slurp-native-exemplars-k20-anchor-train-fold-a-generation-v2, flight commit `ecc6ecea`, died
at 2026-09-17T09:52:35Z on the first row whose Planner routed `REVISE`: the re-entered Solver re-ran
its prepared phase supply, the decision re-selected the same twenty `train-exemplars` values, and
`rails.controllers.EvidenceAgentController._acquired_ids` refused them (`NativeEpisodeError`
`[100054]`, component `solver_1_input`). **420 generation calls, 911.865938 repeated speech seconds,
84 complete rows and 420 request-fit receipts (1,680 FIT endpoints)** are durably spent, preserved
read-only and **never scored**; no partial quality read was taken and none is permitted. Those two
exposure rows are closed. The fix is `rails.controllers.restrict_repeat_visit_supply` (commit
`f2595f4c`, merged `cfbb5f8b`, item E3c) with `tests/unit/test_phase_supply_repeat_visit.py`; the
recovery note is the one root-diagnosed re-registration section 11 of the preregistration allows, and
it changed nothing but bookkeeping -- same roster, same split identity, same role graph, same three
stores, same caps, same session, same decision rule.

**Attempt 2, the recovery, FINALIZED.** Run SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TRAIN-FOLD-A-RECOVERY-V2,
attempt attempt-slurp-native-exemplars-k20-anchor-train-fold-a-generation-recovery-v2, manifest
COMPLETED at study commit a35630c081827cb2d038a4ef314305b69b867627, composed config
`114b791752e160ed0f409fedf12d034b3cc05a8789b4423d1700cc6cb7df000c`, protocol
`c66d507d1ae03c081d04a72dda7b5be28c29d7d5d22e4f196c38e5912211da2d` -- both equal to the values the
recovery note registers -- attached to session `serving-slurp-native-candidate-five-train-a-np4-v1`,
profile `bounded-discovery-probe`. One store moved against the sealed dual-store anchor's own
committed baseline: `knowledge_stores` gained `train-exemplars`, plain top-k = 20 over the 9,354-facet
annotated-exemplar pool (release `171aa4a8...`, snapshot content hash `4c498dc0...`), keyed by the
row's own sealed Fold A full-utterance speech vector in the `content` dimension, supplied to the
Solver as typed content blocks and never as instruction text.

| Artifact | SHA-256 |
| --- | --- |
| scores.json | a7105b328509a8bd00c4678fd076e9be4d242b6189bb82bbd290bd596e3c9078 |
| run-manifest.json | b07ed553ff9f78b8e3ead6797bb66fb92a1820793b8aa5061576c6f66aa1a8ad |
| outputs.jsonl | db9cd6329b0837d8f120f153556c951a68969da167d245d695eb35916237deca |
| paired read `analysis/SAEA-SLURP-B1-EXEMPLARS-K20-PAIRED-ANALYSIS-V1/score-contrasts.json` | a6430288b389f65b00951dd5a518ece285022977bae90e5d7ae39dde0af4c1a9 |
| paired read `.../README.md` | 61d81ee9400c356b51677786f9c3b74a5619d03371ee7bb8612e505344129658 |
| paired read driver `.../b1_paired_read.py` | 2644710aee90b62fa200aed847ddfda2544e776f4f59c57853e4fc7dd4479225 |

Rows: 1,080 scored, 1,076 parsed (4 malformed retained, against the anchor's 7 and the direct
anchor's 0). Comparators, never re-flown and never re-scored: the sealed anchor
SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1 (primary, scores `7360876322...`) and the
released direct anchor SAEA-SLURP-DIRECT-MAX512-TRAIN-FOLD-A-SOURCE-RECOVERY-V1 (secondary, scores
`7840a959fe...`). Paired whole-speaker cluster bootstrap, 10,000 draws, seed 20260915; sensitivity the
paired scenario-stratified row bootstrap on the same draws and seed. Before any table was read, both
comparators reproduced the aggregates the recovery analysis recipe registered before contact,
unprojected and under projection v3, to the hundredth of a point; that STOP condition PASSED.

### Cost and duty cycle

| Figure | B1 recovery | Anchor | Direct | Registered ceiling |
| --- | ---: | ---: | ---: | ---: |
| Generation contacts (per row) | 5,425 (5.023) | 5,417 (5.016) | 1,080 (1.00) | 11,880 (11) |
| Repeated speech seconds | 15,494.60 | 15,459.76 | 3,084.53 | 33,930 |
| Prompt / completion tokens | 49,388,949 / 255,524 | 45,998,267 / 255,153 | 2,459,915 / 26,764 | -- |
| Native task-contract tool calls | 1,084 | 1,082 | 0 | 6,480 |
| FIT receipts / endpoints | 5,425 / 21,700 | -- | -- | -- / 47,520 |
| GPU hours (monitor active seconds) | 3.6819 (13,254.97 s) | 3.3880 (12,196.65 s) | 0.0871 | 12.0 |
| Generation wall seconds | 13,894.2 | not in its receipts | 450.6 | -- |
| Slot occupancy; utilisation; parked | 0.877; 91.01 %; 0.045 | --; 88.73 %; 0.022 | 0.658; 55.66 %; 0.281 | -- |
| Mean latency (s); preprocess (s, workers) | 8.982; 10.01 at 8 | -- | 1.098; 13.03 at 8 | -- |
| Official scoring jobs (seconds) | 1 (166.22) | -- | -- | 1 |

Every registered ceiling held with room: 45.7 % of the contact ceiling, 45.7 % of the speech ceiling,
30.7 % of the GPU-hour ceiling, 45.7 % of the FIT-endpoint ceiling and 16.7 % of the task-contract
ceiling. The module adds prompt volume and not contacts, exactly as registered: **+3,390,682 prompt
tokens (+7.37 %) against the anchor for 8 more contacts** (the 8 extra are the two additional executed
revisions), and completion tokens move by +371. FIT: `every_request_fits = true`, minimum margin
**8,600 tokens** in the `reviewer` phase against the 24,576-token slot; the widest realized request
needed **15,976** tokens, inside the preregistration's section-9 upper bound of 16,465 and 489 tokens
below it. Duty cycle: 91.01 % mean utilisation, 0.877 slot occupancy, 4.5 % parked -- the arm ran the
GPU harder than the anchor did (88.73 %, 0.022 parked) and the whole flight cost 3.68 GPU hours.

## B1 minus the sealed anchor (percentage points)

| Metric | Anchor | B1 | Delta | Speaker CI95 | Speaker CI90 | Scenario-stratified CI90 | Equal-scenario | Direct |
| --- | ---: | ---: | ---: | --- | --- | --- | ---: | ---: |
| Official pooled SLU-F1 | 48.53 | 61.14 | **+12.61** | [+10.54, +14.60] | [+10.87, +14.28] | [+10.94, +14.27] | +12.13 | 33.89 |
| Intent (scenario+action) | 77.96 | 80.19 | **+2.22** | [+0.74, +3.71] | [+0.96, +3.47] | [+1.02, +3.43] | +2.22 | 73.70 |
| Scenario | 84.81 | 86.39 | +1.57 | [+0.57, +2.53] | [+0.73, +2.37] | [+0.65, +2.50] | +1.57 | 82.69 |
| Action | 79.26 | 81.39 | +2.13 | [+0.64, +3.56] | [+0.88, +3.36] | [+0.93, +3.33] | +2.13 | 75.09 |
| Pooled span F1 | 29.50 | 48.43 | **+18.93** | [+15.93, +21.76] | [+16.41, +21.32] | [+16.36, +21.52] | +18.02 | 21.10 |
| Exact slot F1 (row mean) | 19.02 | 31.35 | **+12.33** | [+10.38, +14.36] | [+10.64, +14.02] | [+10.59, +14.13] | +12.33 | 10.72 |
| SLU-F1 (row mean) | 30.29 | 40.15 | **+9.85** | [+8.19, +11.55] | [+8.42, +11.27] | [+8.49, +11.26] | +9.85 | 16.06 |

Saves / harms / ties with the exact two-sided McNemar p: intent 43 / 19 / 1,018 (**3.16e-3**);
scenario 28 / 11 / 1,041 (**9.47e-3**); action 42 / 19 / 1,019 (**4.44e-3**); exact slot F1
213 / 38 / 829 (**1.03e-30**); row SLU-F1 276 / 63 / 741 (**6.26e-33**). The scenario-stratified
sensitivity agrees everywhere: no interval changes sign, and none of the seven intervals contains
zero.

This is the first cell of the v2 program whose **label** metrics move at all. Read precisely: the
intent point estimate +2.22 exceeds the own-null half-width h_intent = 1.0051, its CI95 excludes
zero, and its sign test rejects at p = 3.2e-3 on 43 saves against 19 harms -- but its CI95 **lower**
bound is +0.74, which does not itself clear 1.0051. The honest statement is therefore "non-inferior,
and very likely a real intent gain", not "an intent gain beyond the own null at CI95". The same
reading holds for scenario (+1.57, lower bound +0.57) and action (+2.13, lower bound +0.64). The
dominant movement is on entities, where no such caution applies: pooled span F1 +18.93 and per-row
exact slot F1 +12.33 have lower bounds of +15.93 and +10.38, ten times h_span = 1.5586, and they are
the largest single-cell moves the program has recorded.

## B1 minus the released direct anchor (secondary)

Pooled SLU **+27.25** [+23.82, +30.70]; intent +6.48 [+4.09, +9.01]; scenario +3.70 [+1.54, +5.95];
action +6.30 [+3.89, +8.94]; pooled span F1 +27.33 [+23.22, +31.43]; exact slot F1 row mean +20.63
[+18.06, +23.38]; row SLU-F1 +24.09 [+21.62, +26.73]. Saves / harms: intent 138 / 68 (p = 1.2e-6),
row SLU-F1 405 / 54 (p = 1.4e-67). The system-over-direct margin grows from the anchor's +14.65 to
**+27.25** pooled SLU. One honest note on this secondary contrast: `alarm` is the single scenario
that loses intent beyond the band against the direct anchor (-10.00, CI95 [-17.02, -2.63], net
harmed 6 rows, owner decision 17's flag). The band is a clause of the rule only against the **sealed
anchor**, where nothing breaches; against the direct anchor it is reported, not gating.

## The rule, applied unchanged

| Clause | Requirement | Value | Margin | Passes |
| --- | --- | ---: | ---: | --- |
| 1, pooled SLU gain vs the anchor | CI95 lower bound of (B1 - anchor) > 0 | +10.5381 | 0 | **YES** |
| 1b, pooled SLU gain vs the twin | CI95 lower bound of (B1 - twin) > 0 | twin not flown | 0 | **NOT EVALUABLE** |
| 2, intent non-inferiority | CI95 lower bound > -1.0051 | +0.7407 | -1.0051 | **YES** |
| 3, normalised-scorer agreement | symmetric pooled SLU delta agrees in sign | +10.8854 vs +12.6058 | same sign | **YES** |
| 4, scenario band | no scenario's own paired intent delta has a CI95 upper bound below zero | 0 of 18 breaching | CI95 upper < 0 | **YES** |

None of the three HARMFUL triggers fires: the pooled SLU CI95 lower bound is +10.54, far above
-1.1218; the intent CI95 lower bound is +0.74, far above -1.0051; and no scenario breaches the band.
Owner decision 17's added diagnostic -- net harmed rows per scenario, flagged at five or more -- fires
on **no scenario** against the anchor: the worst net figure is +1 (alarm and email), and eleven
scenarios are net negative (fewer harms than saves). **Status ADMITTED pending the twin.** Read once,
from the single official score of the complete manifest; no repeat, no re-score, no row filtering.

One note on clause 3, because it is the first time the clause has been evaluable at all. The
preregistration recorded it as **not evaluable on TRAIN**: `slurp-slu-f1-normalized-v1` is bound to
the SLURP `devel` split and refuses TRAIN sample ids, and this read reproduces exactly that refusal
(`SlurpOfficialEvalError: outputs sample_id 'slurp:train:000007:audio--1504197557' is not part of
SLURP split 'devel'`). Owner decision 14 of 2026-09-17, taken after this preregistration was sealed,
registered the TRAIN sibling `slurp-slu-f1-normalized-v1-train`. That sibling is the owner's scorer,
not a substitute invented after the fact by this read, so the clause is evaluated under it and both
readings are reported: "not evaluable as registered" and "passes under the owner's TRAIN sibling".
The verdict would be unchanged if the clause were held at "not evaluable": the status turns on the
twin, not on clause 3.

## Every scenario (natural mixture; equal-scenario mean in the last row)

| Scenario | n | Anchor SLU | B1 SLU | Delta | Anchor intent | B1 intent | Delta | Intent CI95 | Net harmed | Flag | Beyond band |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- | --- |
| alarm | 60 | 52.66 | 65.28 | +12.61 | 83.33 | 81.67 | -1.67 | [-10.81, +10.53] | +1 | no | no |
| audio | 60 | 47.75 | 60.35 | +12.59 | 76.67 | 78.33 | +1.67 | [-6.45, +6.67] | -1 | no | no |
| calendar | 60 | 48.38 | 64.16 | +15.78 | 75.00 | 78.33 | +3.33 | [-3.23, +10.34] | -2 | no | no |
| cooking | 60 | 62.47 | 64.74 | +2.27 | 85.00 | 88.33 | +3.33 | [+0.00, +8.62] | -2 | no | no |
| datetime | 60 | 59.52 | 69.80 | +10.29 | 83.33 | 88.33 | +5.00 | [+0.00, +10.71] | -3 | no | no |
| email | 60 | 36.64 | 57.93 | **+21.29** | 85.00 | 83.33 | -1.67 | [-4.84, +0.00] | +1 | no | no |
| general | 60 | 15.45 | 20.41 | +4.95 | 36.67 | 43.33 | +6.67 | [-1.96, +14.93] | -4 | no | no |
| iot | 60 | 55.53 | 64.30 | +8.77 | 86.67 | 88.33 | +1.67 | [+0.00, +5.36] | -1 | no | no |
| lists | 60 | 43.55 | 53.45 | +9.90 | 83.33 | 85.00 | +1.67 | [+0.00, +5.77] | -1 | no | no |
| music | 60 | 34.53 | 48.87 | +14.34 | 76.67 | 78.33 | +1.67 | [-3.70, +7.55] | -1 | no | no |
| news | 60 | 44.24 | 60.85 | +16.61 | 80.00 | 83.33 | +3.33 | [+0.00, +9.09] | -2 | no | no |
| play | 60 | 46.82 | 49.94 | +3.11 | 58.33 | 60.00 | +1.67 | [-7.41, +12.31] | -1 | no | no |
| qa | 60 | 57.04 | 58.16 | **+1.12** | 75.00 | 75.00 | 0.00 | [+0.00, +0.00] | 0 | no | no |
| recommendation | 60 | 49.75 | 68.67 | +18.92 | 90.00 | 90.00 | 0.00 | [-6.56, +6.67] | 0 | no | no |
| social | 60 | 34.74 | 57.33 | **+22.59** | 66.67 | 75.00 | **+8.33** | [+1.79, +15.62] | -5 | no | no |
| takeaway | 60 | 48.84 | 60.43 | +11.59 | 85.00 | 85.00 | 0.00 | [+0.00, +0.00] | 0 | no | no |
| transport | 60 | 51.34 | 62.79 | +11.46 | 86.67 | 90.00 | +3.33 | [+0.00, +7.35] | -2 | no | no |
| weather | 60 | 53.81 | 73.93 | +20.12 | 90.00 | 91.67 | +1.67 | [+0.00, +5.66] | -1 | no | no |
| **equal-scenario mean** | 18 | | | **+12.13** | | | **+2.22** | | | | |

**All eighteen scenarios gain on pooled SLU; none loses.** The extremes are `social` **+22.59**,
`email` +21.29 and `weather` +20.12 at the top and `qa` **+1.12**, `cooking` +2.27 and `play` +3.11 at
the bottom. On intent, `social` gains 8.33 and `general` 6.67; only `alarm` and `email` lose, one row
each (-1.67), and neither is near the band. The equal-scenario weighting (+12.13 SLU, +2.22 intent)
is within half a point of the natural mixture (+12.61, +2.22), so the gain is not a stratum artifact:
it is broad, and the two scenarios that move least (`qa`, `cooking`) are the two whose exemplar
filler recall A2 already measured as weakest or whose answers are least entity-bearing.

## Projection v3 and the TRAIN symmetric view, beside the rule

Owner decision 7 of 2026-09-17 makes `slurp-slu-official-projected-v3-train` the fixed
post-processing of every official number; for cell B1 it is reported beside the rule and is not a
clause of it. Each arm's sealed `outputs.jsonl` was COPIED under the analysis directory and the
registered scorers read the copy; the sealed bytes were never opened for writing.

| Arm | v3 SLU | v3 intent | v3 scenario | v3 action | v3 span F1 | Labels / fillers changed |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| anchor | 51.99 | 79.35 | 85.46 | 80.65 | 40.30 | 20 / 195 |
| **B1** | **62.67** | **81.76** | **87.13** | **82.96** | **52.65** | 24 / **90** |
| direct | 34.31 | 75.37 | 84.17 | 75.93 | 23.24 | 47 / 36 |

v3 contrasts: B1 - anchor SLU **+10.67 [+8.55, +12.77]**, intent +2.41 [+1.14, +3.74], span F1
+12.35 [+9.43, +15.17]; B1 - direct SLU +28.35 [+24.90, +31.81], intent +6.39 [+4.09, +8.83], span F1
+29.42 [+25.62, +33.24]. The anchor's and the direct anchor's v3 readings reproduce the registered
51.99 / 79.35 / 85.46 / 80.65 / 40.30 and 34.31 / 75.37 / 84.17 / 75.93 / 23.24 exactly, which is
what licenses reading the arm's v3 number beside them. The projection **normalises 105 fewer fillers
under B1 than under the anchor (90 against 195)**: the arm needs less surface repair than the base,
so part of what the exemplars deliver is precisely the representation alignment that projection v3
otherwise has to supply. About 1.94 pp of the +12.61 official gain is that alignment; +10.67 pp
survives it.

Owner decision 14 of 2026-09-17 registered the TRAIN sibling `slurp-slu-f1-normalized-v1-train`, so
the symmetric column exists on this roster for the first time. It reproduces the addendum's registered
anchor and direct readings exactly (52.09 / 41.38 and 34.46 / 24.38,
`docs/results/2026-09-17-slurp-train-symmetric-reread-v1.md`).

| Arm | Official pooled SLU | Symmetric pooled SLU | Delta | Official span F1 | Symmetric span F1 | False merges |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| anchor | 48.53 | 52.09 | +3.56 | 29.50 | 41.38 | 34 |
| **B1** | **61.14** | **62.97** | **+1.83** | **48.43** | **54.51** | 34 |
| direct | 33.89 | 34.46 | +0.57 | 21.10 | 24.38 | 34 |

Symmetric contrasts: B1 - anchor SLU **+10.89 [+8.72, +13.00]**, intent +2.22 [+0.74, +3.71], span F1
+13.12 [+10.12, +16.04]; B1 - direct SLU +28.52 [+25.01, +31.99], span F1 +30.13 [+26.28, +33.98].
The sign agrees and the interval stays bounded away from zero, so clause 3 passes under the owner's
sibling. **About 1.72 pp of the +12.61 official gain is representation alignment and +10.89 pp is
not** -- and the direction is informative: the anchor needs +3.56 pp of symmetric repair while B1
needs only +1.83, which is the same fact the projection's filler counts show (195 fillers normalised
under the anchor, 90 under B1). The exemplars move the arm's surface forms toward the reference
before any normaliser is applied.

## The M1 diagnostics against the A2 audit's predictions

A2 (`docs/results/2026-09-17-slurp-a2-exemplar-headroom-audit-v1.md`) settled the availability side
and named the open question this cell answers: *union coverage is availability, not use.* The
instrument below is each arm's own sealed trace -- the first-Perception response projected through
`rails.slurp_intent_hypotheses.project_bounded_slurp_intent_hypotheses`, the flight's own recorded
`train-exemplars` value ids, and each arm's sealed delivered answer. The store's pinned snapshot
supplies the exemplar intents and fillers.

**The instrument reproduces A2 exactly where A2 measured the same thing.** The anchor's own candidate
coverage is **937 / 1,080 = 0.8676**, A2's number to four decimals; the anchor misses gold on **143**
rows, A2's 143; the twenty neighbours carry gold on **113** of those, A2's 113; union coverage is
**0.9722**, A2's 0.9722. Filler recall over the delivered exemplars is **0.5770** against A2's 0.566,
type recall **0.9590** against 0.960, and the echo statistic **0.7241** against 0.729 (0.8487 on rows
delivered correctly against A2's 0.867; 0.2196 on rows delivered wrongly against 0.225).

| Diagnostic | B1 | Anchor | A2's prediction |
| --- | ---: | ---: | ---: |
| Supplied exemplars per row | 20 on 1,080 / 1,080 rows; 4,990 distinct values of 9,354 | -- | k = 20 |
| Gold intent among the arm's own Perception candidates | 939 (0.8694) | 937 (0.8676) | 0.8676 |
| Delivered intent among the arm's own candidates | 1,044 (0.9667) | 1,051 (0.9731) | not predicted |
| Delivered intent correct | 866 (0.8019) | 842 (0.7796) | -- |
| **Solver escape to a neighbour intent** | **6 rows (0.56 %)**, 5 of them onto gold | -- | the B1 outcome A2 left open |
| Delivered intent outside candidates and exemplars | 30 | -- | -- |
| Delivered intent present among the twenty exemplar intents | 979 | -- | -- |
| Rows in A2's recovery set delivered correctly | **10 of 113** | **0 of 113** | 113 rows *available* |
| Delivered mentions echoing a supplied exemplar filler | 500 of 1,000 (0.500) | 265 of 910 (0.291) | base rate 0.291 |
| Gold-exact mentions | **501** | 340 | -- |
| ... of those, also present among the twenty | 357 | 204 | -- |

**A2's coverage lever is real but small; the gain is almost entirely convention transfer.** The
escape-to-neighbour-intent rate is **0.56 %** -- six rows of 1,080, five of which landed on gold. Of
A2's 113 *available* recovery rows the arm converts **10**; the anchor converts 0. The intent gain is
+24 net rows, so **about 40 % of it comes from the coverage lever and the rest from better selection
inside the candidate set the anchor already had**. Meanwhile the delivered-mention echo rate doubles
against the anchor's own base rate (0.500 against 0.291) and gold-exact mentions rise from 340 to
501. A2 predicted this shape in its own words -- "convention transfer, not coverage, is M1's weak
axis" was about filler recall saturating near 0.60; the delivered result inverts the emphasis:
**filler recall of 0.577 is enough to move 161 more mentions to exact**, because the exemplars teach
the *form* of an answer, not only its content.

Review loop, and the E3c path in flight:

| Quantity | B1 | Anchor |
| --- | ---: | ---: |
| Rows with a Planner REVISE token | 7 | 5 |
| Rows with a second Solver visit (revisions executed) | **7** | **5** |
| Rows whose intent changed across the revision | 3 | 2 |
| Exemplar acquire transitions per row | exactly 1 on 1,080 / 1,080 | n/a |

The anchor's registered baseline is five executed revisions and two intent changes in 1,080 rows, and
this read reproduces both. The arm executes seven. **Every one of those seven rows is a row the
pre-fix tree would have aborted on**, and the acquire-transition histogram is the proof the E3c fix
behaved as its tests said: the supply is consulted on both Solver entries and acquires exactly once,
on 1,080 of 1,080 rows.

Rendered exemplar volume, per row, from the pinned snapshot content the flight's own supply record
names: mean **1,874.4** characters, p50 1,807, p95 2,696, max **3,232** -- a chars/4 proxy of mean
468.6, p95 674.0, max **808.0** tokens. That reproduces A2's own content measurement (mean 1,876,
p95 2,715) rather than the preregistration's section-9 figure (mean 2,974.4, max 4,332 chars), because
the two count different things: A2 and this row count exemplar *content* characters, while the
preregistration measured the *rendered block* including each value's wire markup. The authority on
what actually reached the slot is the FIT receipt, and it says the widest realized request of the
whole flight needed 15,976 tokens against a 24,576-token slot.

## Entity mass against the anchor, by type

The official scorer's own matching, reconstructed from each arm's sealed outputs; every row's
reconstruction was checked against that row's sealed official `slu_f1` word and character counts, and
the per-type decomposition sums to each arm's official aggregate (max abs diff 6.8e-13). The types
with the largest absolute movement:

| Type | Rows with gold | Anchor FN | B1 FN | Delta | Anchor FP | B1 FP | Delta | Anchor TP | B1 TP | Exact mentions | Rows omitting |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| date | 135 | 203.58 | 129.35 | **-74.23** | 49.58 | 41.35 | -8.23 | 108 | 174 | 28 -> **66** of 138 | 81 -> **48** |
| media_type | 57 | 95.30 | 46.50 | **-48.80** | 35.30 | 32.50 | -2.80 | 38 | 82 | 8 -> **32** of 57 | 38 -> **16** |
| time | 72 | 116.34 | 68.07 | **-48.27** | 96.34 | 64.07 | **-32.27** | 110 | 116 | 8 -> **30** of 76 | 19 -> 15 |
| place_name | 92 | 108.35 | 71.36 | -36.99 | 88.35 | 85.36 | -2.99 | 150 | 160 | 30 -> 55 of 100 | 22 -> 17 |
| device_type | 15 | 9.14 | 8.58 | -0.57 | 71.14 | 32.58 | **-38.57** | 22 | 22 | 10 -> 10 of 15 | 4 -> 4 |
| event_name | 41 | 57.58 | 32.83 | -24.74 | 39.58 | 38.83 | -0.74 | 38 | 62 | 10 -> 20 of 41 | 22 -> 10 |
| list_name | 21 | 23.85 | 12.58 | -11.27 | 55.85 | 32.58 | -23.27 | 36 | 34 | 7 -> 15 of 22 | 3 -> 4 |
| business_type | 29 | 49.47 | 31.12 | -18.35 | 19.47 | 19.12 | -0.35 | 14 | 30 | 2 -> 12 of 29 | 22 -> 14 |
| food_type | 64 | 45.67 | 29.34 | -16.33 | 47.67 | 65.34 | **+17.67** | 104 | 118 | 38 -> 46 of 65 | 12 -> 5 |
| transport_type | 36 | 51.75 | 35.50 | -16.25 | 5.75 | 9.50 | +3.75 | 22 | 40 | 10 -> 18 of 36 | 25 -> 16 |
| relation | 15 | 32.00 | 17.61 | -14.39 | 0.00 | 11.61 | +11.61 | 0 | 18 | 0 -> 7 of 16 | 15 -> 6 |
| business_name | 51 | 72.19 | 59.20 | -13.00 | 74.19 | 71.20 | -3.00 | 76 | 82 | 8 -> 16 of 52 | 13 -> 10 |
| news_topic | 15 | 16.45 | 10.04 | -6.42 | 34.45 | 16.04 | -18.42 | 22 | 24 | 7 -> 7 of 15 | 4 -> 3 |
| timeofday | 17 | 14.86 | 4.86 | -10.00 | 8.86 | 16.86 | +8.00 | 20 | 30 | 9 -> 14 of 17 | 7 -> 2 |

Roster totals, all types: gold mentions 941 (fixed); predicted mentions 910 -> 1,000; exact mentions
**272 -> 470**; omitted mentions **393 -> 266**; spurious mentions 362 -> 325; filler-distance
(surface) mass **814.46 -> 534.14**. Summed over all 53 types the arm removes **394.16 points of
false-negative mass and 214.16 points of false-positive mass**, and 30 of 53 types cut FN mass. The
arm emits more, omits far less, is exact far more often *and* is closer when it is wrong. Three types
buy part of their FN reduction with new FP mass -- `food_type` (+17.67), `relation` (+11.61),
`timeofday` (+8.00) -- which is the same "the cards make the core emit where it was silent" pattern
cell B4b recorded, here driven by exemplars rather than by contract cards.

## The harness-admission consequence

On a positive verdict the module enters the harness-admission table under the `stores` switch class.
The entry this verdict supports:

- **module**: exemplar supply to the Solver (train-exemplars store)
- **class**: `stores`
- **key**: `knowledge_stores.train-exemplars`
- **on**: release `171aa4a82c2b15fff2c72e907ea80298be8d72309cca0d7367eb50debb042129`, snapshot content
  hash `4c498dc0282055b9fe036ed7e950af519bd48b5f26e76876d0250727196a72e9`
  (`knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars`), plain top-k = 20,
  `saea-fuse-supplyfilter-v1` at m = c = top_l = 20, `saea-rank-wcos-prior-agree-v1` with w_cos = 1,
  tau 0.0, keyed by the row's own sealed full-utterance speech vector in the `content` dimension
- **off (null form)**: the named store **absent** from the `knowledge_stores` mapping -- which is the
  `stores` class's own registered null (`rails.config_tables.is_stores_null_arm`), not a re-pin. The
  open point cell B4b had to raise, that its OFF arm was a release/snapshot re-pin rather than the
  class's null, does **not** arise here: the sealed anchor's committed baseline simply has no
  `train-exemplars` sub-block, and the two fragments differ in exactly that one top-level
  `knowledge_stores` entry.
- **evidence**: this verdict, the sealed score `a7105b32...`, the paired read `a6430288b389f65b00951dd5a518ece285022977bae90e5d7ae39dde0af4c1a9`
- **status**: the row is not written yet. The preregistered ADMITTED clause needs the twin, and the
  coordinator owns the admission receipt; `scripts/checks/harness_admission_check.py` is the oracle.
  This verdict neither writes the row nor edits the receipt.

## What is not claimed

- **No superiority, generalization, paper-scale or held-out claim.** TRAIN Fold A is an exposed
  discovery roster; nothing is said about Fold B, DEV-1000 or the test split, which stay unread.
- **The retrieval key is not yet separated from the exemplars.** The twin is the only instrument that
  distinguishes "the row's own speech found the right twenty neighbours" from "twenty real annotated
  exemplars of any kind teach the answer form". Until it flies, the honest statement is that *twenty
  annotated TRAIN exemplars supplied to the Solver in this configuration pay for themselves*, and
  nothing about the key. The twin is token-matched by construction and still carries twenty real
  annotated exemplars, so it is a retrieval-key control and not an information-free control.
- **No component-causal attribution below the store.** One store, one k, one fuse policy, one rank
  policy, one release. This cell cannot say which of those is load-bearing.
- **A2's availability numbers are not predictions of the delivered answer**, and this read says so
  with numbers: 113 rows were available through the coverage lever and 10 were converted.
- **Nothing about the review loop**, which is held identical to the anchor here; its own decision is
  `docs/results/2026-09-17-slurp-b0-review-off-verdict.md` plus the 2026-09-17 own-null re-decision.
  The two extra executed revisions are recorded, not attributed.
- **One pass.** The margins are cell B0r's own null, measured on the same roster and geometry but on
  a different configuration (review-off, two contacts per row), and the anchor leg is a single
  realization shared with every other cell built on it. The family rule of 2026-09-08 requires a
  replicate or a named root cause before a module is frozen. The size of this gain (+12.61 with a
  CI95 lower bound of +10.54, nine times h_SLU) makes a width artifact implausible, and the entity
  diagnostics give it a mechanism a batch-order difference cannot produce -- 198 more exact mentions,
  127 fewer omissions, 280 points of surface mass removed -- but "large" is not "replicated".
- **Nothing about the aborted attempt's 84 rows**, which were never scored and never read.
- The types outside the exemplars' own distribution that moved are recorded above and explicitly not
  attributed.

## The twin decision

**The twin flies next.** Owner decision 8 of 2026-09-17, restated by decision 15, makes a positive
arm CI95 against the base the trigger, and this arm's CI95 lower bound is +10.54 pp. The registered
twin is `SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TWIN-TRAIN-FOLD-A-V2` /
`attempt-slurp-native-exemplars-k20-anchor-twin-train-fold-a-generation-v2`, cell
`slurp-native-exemplars-k20-anchor-twin-train-fold-a-v2`, composed config
`f9b9d45e49c16e506f61e5ec292f4d3d54181d2f880e42bac3ebcdef3322e813`, protocol
`1bcfc79ff02991137363208344d43e8c8b045095711e17ff659d146154b35a73`. It is unflown, `consumed = no`,
readiness `held`, and it **must fly on the E3c-fixed code**: its role graph is the arm's, so its rows
will take the same REVISE route on roughly the same seven rows, and on the pre-fix tree it would
abort exactly as the arm's first attempt did. Its derangement is seeded (`seed 20260917`, vectors
`92e7f72e...`, 1,080 rows, 0 fixed points, one source vector delivered twice and one not at all, the
declared `cross_group_rows: 1`). Budget about 3.7 GPU hours at this geometry.

Until it seals, the status line above stands as written: **ADMITTED pending the twin**, with a
strictly positive interval on every one of the seven headline metrics and no guard failing on the
losing side.
