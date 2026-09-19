# Cell B8a: the delivery-time normaliser node (module M3 inside the agent), TRAIN A

Status: **ADMITTED** (model-free read ADMITTED; four-row smoke structural PASS, closed at study commit e79ce296). On both gating bases the delivery node
`saea-deliver-normalise-v3` raises the **official, unprojected** pooled SLU-F1 with a CI95 lower
bound far above zero and raises intent as well: on the sealed dual-store anchor **48.5336 ->
51.9946**, **+3.4609 pp** CI95 **[+2.7814, +4.1797]**, intent **+1.3889** [+0.7128, +2.0409]; on
cell B1's recovery arm **61.1394 -> 62.6672**, **+1.5278 pp** CI95 **[+1.0537, +2.0282]**, intent
**+1.5741** [+0.7821, +2.4575]. The reported third base, cell B5e, moves **62.3351 -> 63.7757**,
**+1.4406** [+1.0004, +1.9154], intent **+1.7593** [+1.0820, +2.4678]. Every one of the four
registered clauses passes on both gating bases, no scenario's intent CI95 upper bound lies below
zero (0 of 18 on all three contrasts), owner decision 17's diagnostic flags nothing, and the
HARMFUL clause does not fire anywhere. **Intent is harmed on zero rows of any arm** (saves / harms
15/0, 17/0, 19/0). Root: the B8a paired-read agent, 2026-09-19, at study commit `cc765b7c`.
Preregistration: `docs/readiness/2026-09-19-slurp-b8a-deliver-normalise-v1-preregistration.md`
(section 8, rule fixed before any number was read). Recipe:
`docs/readiness/2026-09-19-slurp-b8a-deliver-normalise-v1/analysis-recipe-v1.json`. Margins: the
TRAIN A own null of cell B0r, **h_SLU = 1.1218 pp** and **h_intent = 1.0051 pp** at CI95
(`docs/results/2026-09-17-slurp-b0-review-off-redecision-v2.md`).

Authority: **owner decision 27 of 2026-09-19** (cell B8a, and non-GPU work in parallel with GPU
work), **owner directive 26 of 2026-09-18** ("analyses into nodes"), **owner decision 23**
(the bar and every final evaluation read the official, unprojected number), **owner decision 25**
(the HARMFUL form), **owner decision 7** (projection v3 as the fixed post-processing; about 2.5 pp
of the 64-point bar is representation alignment), **owner decision 14** (the TRAIN symmetric
sibling), **owner decision 17** (net harmed rows per scenario), all in
`docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`. Engineering: item **E11**.

## What this read is, and what it is not

**Zero model, tokenizer, encoder, ASR, server and paid-API contacts.** No flight was launched, no
serving session was touched, no run directory was written, and no sealed file was opened for
writing, moved or renamed. The node is pure, deterministic and makes no contact of any kind, so
for any sealed OFF arm its ON arm is that arm's own bytes after one offline transform: the two
arms are **perfectly paired**, the same 1,080 rows, the same requests, the same model responses,
one deterministic rewrite apart. **No interval below contains any decoding noise.**

The one factor is module **M3** -- the SLURP USE projection v3 (the label rule `R_action`, then the
registered legal-label projection v2, then the filler normalisation P2: case, whitespace,
punctuation, meridiem, numeric words, **no** support filter) -- applied **once** to the accepted
answer immediately before delivery, by the same two functions
(`rails.slurp_projection_v3.project_slu_label_v3`, `.normalize_filler_p2`) the v3 SCORER applies.
Nothing about the model, the prompts, the knowledge, the role graph or any request byte changes.
Since item E4 the same rule has lived in the scorer, where the official scorer credits none of it;
this cell moves **who performs it** into the episode.

## Provenance

Every hash below was recomputed from the file before it was read, and every sealed hash the recipe
pins was re-derived and matched before any table was opened.

| Artifact | SHA-256 |
| --- | --- |
| anchor `scores.json` | `7360876322488e5fda689fcafda00e90da2ebf559e5a35e635c550f940202b47` |
| anchor `run-manifest.json` | `049ac230e536bc6c8fe45bc847756ba486c4904e9c7602c698157f78d70c0152` |
| anchor `outputs.jsonl` (sealed, and the byte-identical OFF copy) | `d87d71e8fa0fe93b45d5c6817ba125b016d8d91f44a14309171dd0f3a64270d8` |
| cell B1 `scores.json` | `a7105b328509a8bd00c4678fd076e9be4d242b6189bb82bbd290bd596e3c9078` |
| cell B1 `run-manifest.json` | `b07ed553ff9f78b8e3ead6797bb66fb92a1820793b8aa5061576c6f66aa1a8ad` |
| cell B1 `outputs.jsonl` (sealed, and the OFF copy) | `db9cd6329b0837d8f120f153556c951a68969da167d245d695eb35916237deca` |
| cell B5e `scores.json` | `aeed7ad9b7fe44e74c4b9e65470e0d96429637ccaa4655c9185515568a70d7b9` |
| cell B5e `run-manifest.json` | `1d827e31bd26e65e1327ec8c81dc96ebb55cd470692b339ab5323fcea1c86808` |
| cell B5e `outputs.jsonl` (sealed, and the OFF copy) | `3d861012bfbbf267d47023d069e5ccfe0442a3212cb3bd855e100eb8475751a6` |
| node-ON `outputs.jsonl`, anchor | `f161c2745d2c48aa9e8d086b01b93e9da2e2e53067543eaece886077485a84a8` |
| node-ON `outputs.jsonl`, cell B1 | `876e9f7337bbaef6dcb2f093177d1f87e79eff26bea6a8548cca310d9651de3f` |
| node-ON `outputs.jsonl`, cell B5e | `5c04a3c9913818ad21ec3186bee2043412162848d41cd92c9569a2f92618f381` |
| node-ON official score, anchor | `db937bd24e3ca20b179128a39ee580c804d61d8712a1c5cba4c638370b6fe5c7` |
| node-ON official score, cell B1 | `c9e45600f375808b810bc1c21b47e4eaff9c245adf0c98c437f8b55efdb01180` |
| node-ON official score, cell B5e | `7451e0322606edd36ab08bf96fffa0793f58b4a00e3265bdfdd0b5ba4fb6ffb9` |
| roster `docs/receipts/rosters/slurp-evo-fold-a-v2.json` | `1fe7908c31396774d7535fdf37bd791762215c324999d66ed7beb9e7b2f9033d` |
| roster metadata (speaker clusters, scenario strata) | `07f4cd83b83d83d65500a328e0a38421ede575195c63ae118def0d1006c14e34` |
| analysis recipe | `61127762df762c55b33b5e6c6f017dc0e4cc6d08a257b6635250a7d21159eaf2` |
| sealed-inputs registration | `7b9de7f2b7797943fc2342885c726207ac07f16a4db50e9a7fcc44c40cef4ef9` |
| preregistration (current bytes, after the 2026-09-19 re-pin) | `b72440eb1431a5c110b14be84b85c0eb003e78e43853e37cf6c0aade21ffa346` |
| readiness runbook (current bytes) | `c5565bbd716815e87ed16aa0f5587a02de9d0ca99524ad061c3d2d27d9d0899d` |
| read driver `src/speech_aware_evidence_acquisition/analysis/b8a_delivery_node_read.py` | `5f67b695d2945303b9c008bc138791bd9a91c34195f1de296219d4ea974d1c20` |
| paired read `analysis/SAEA-SLURP-B8A-DELIVERY-NODE-READ-V1/score-contrasts.json` | `af79e7b5886f9de878c0a3fe42ac5c94da63c72e658ac0dc61f32bf2cef1c35a` |
| its `README.md` | `ffb5d2ee94800311093108234aa3e40306a3858af12a3257fa6f1c22ee7493dd` |
| `per-scenario-tables.json` | `80b2298d38f454f03b0d59579274d2c06dbdde64f07e588901034f6d37299319` |
| `node-diagnostics.json` | `4337d6f6ef7f67ea8ae4badc3d40e69c7828a9ec029914fc0d5618ced6ddecfd` |
| `slot-diagnostics.json` | `2bc782449cb376015ecfa97c0b7077ed26fa3a3521a07ae259e0a3141f3c9729` |
| `symmetric-contrasts.json` | `34813947e1ca60fe757457005da59b550bdad5cf7fc462f4d2d562b221d63d52` |
| `replay-provenance.json` | `ec300ecc9dc6f317f415fdd9e71b156f13454614a8b259234c90080c432d932d` |

All three manifests are `COMPLETED`, each pins the score bytes this read used, and each carries
split identity `61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6`, role
`discovery`, scorer `slurp-slu-official-train` at evaluator commit
`8eb16545762be97ace75334109d73824217311f1`. Population: 1,080 rows, 125 speaker clusters, 18
scenarios of 60, 523 headset and 557 far-field rows; 1,080 rows in and 1,080 out on every arm and
every side, no row dropped and no `sample_id` invented. The full input and output hash tables -- 35
inputs and 29 outputs, including the copies, the replays and every score file -- are in that
analysis directory's `README.md`.

**The driver** is `src/speech_aware_evidence_acquisition/analysis/b8a_delivery_node_read.py`, an
adapted copy of two sealed precedent drivers whose estimator calls are reproduced byte for byte:
`analysis/SAEA-SLURP-B5E-COMBINATION-PAIRED-ANALYSIS-V1/b5e_paired_read.py`
(`0f5a60a8eb15c2ae641718c817ea103d2b456a17dd94ba3a4c9ae63db737db59`) and
`analysis/SAEA-SLURP-B2-SAMPLES5-PAIRED-ANALYSIS-V1/b2_paired_read.py`
(`8f101c9ae5c07728ddcdd8af59a5cc375e5918dcc6fcbfc3dfb7773941393bba`). Only the arm list (three
OFF/ON pairs), the node stages and the decision block are new;
`analysis.null_calibration_cli.rows_for`, `analysis.null_calibration.pooled_f1`,
`analysis.paired.resampled_statistic` and `analysis.paired.paired_contrast` are unchanged. Paired
whole-speaker cluster bootstrap over the roster's 125 speakers, **10,000 draws, seed 20260915**,
CI95 for the clauses and CI90 for diagnostics as percentiles of the same retained replicate
sequence; sensitivity the paired scenario-stratified row bootstrap (18 scenarios of 60) on the same
draws and seed. Every table is reported in both the natural-mixture and the equal-scenario
weighting. `analysis.score_compare_cli` is deliberately not the runner: it hard-codes ci_level 0.90
and DEV population names.

## The STOP condition, closed before any contrast was computed

**PASSED -- 27 checks, zero failures.**

1. **The three sealed OFF arms reproduce their registered official aggregates** to better than
   0.005 pp: anchor **48.5336 / 77.9630** against 48.53 / 77.96; cell B1 **61.1394 / 80.1852**
   against 61.14 / 80.19; cell B5e **62.3351 / 80.0926** against 62.34 / 80.09.
2. **The three node-ON arms reproduce the registered projection v3 aggregates**, which is what
   section 6 of the preregistration predicted exactly: anchor **51.9946 / 79.3519** against 51.99 /
   79.35; cell B1 **62.6672 / 81.7593** against 62.67 / 81.76; cell B5e **63.7757 / 81.8519**
   against 63.78 / 81.85.
3. **1,080 rows in and 1,080 out per arm**, the same ids as the roster on both sides, none
   invented; `analysis.null_calibration.pooled_f1` reproduces each of the six arm-sides' own
   official pooled SLU and span F1 from its per-sample rows to better than 1e-6 (12 of 12 checks).

Two further checks were run beyond the registered three, and both hold. The registered **v3 SCORER
over each OFF copy** re-derives the same projected numbers a second, independent way (51.9946 /
79.3519, 62.6672 / 81.7593, 63.7757 / 81.8519 -- identical to the ON official numbers). And the
**v3 scorer over each ON copy is a no-op**: it changes 0 labels on all three arms and 0 fillers on
cell B1 and cell B5e, 1 filler on the anchor (the one recorded non-fixed-point row, below), and the
resulting numbers are bit-identical to the ON official numbers. The node has already done the
scorer's work.

## Triple equality -- the licence for reading this admission without a flight

For each arm, on every parsed row, the prediction triple `(scenario, action, entities)` parsed back
out of the node's delivered text is **byte-identical** to the triple the v3 SCORER builds from the
same row, and every unparsed row is delivered byte-identically with `applied: false`.

| base | parsed rows compared | mismatches | unparsed, delivered verbatim | registration said |
| --- | ---: | ---: | ---: | --- |
| anchor | 1,073 | **0** | 7 | 1,073 / 0 |
| cell B1 | 1,076 | **0** | 4 | 1,076 / 0 |
| cell B5e | 1,079 | **0** | 1 | 1,079 / 0 |

The official SLU number of a set of rows is a pure function of those triples and the fixed gold, so
the official number of a node-ON arm **is** the v3-projected number of the sealed arm --
identically, not to two decimal places. STOP clause 2 is that identity measured through the scorer.

## Node ON minus OFF -- the three contrasts (percentage points, delta = ON minus OFF)

### Anchor base (GATING)

| Metric | OFF | ON | Delta | Speaker CI95 | Speaker CI90 | Scenario-stratified CI95 | Equal-scenario |
| --- | ---: | ---: | ---: | --- | --- | --- | ---: |
| Official pooled SLU-F1 | 48.53 | 51.99 | **+3.46** | [+2.78, +4.18] | [+2.88, +4.06] | [+2.79, +4.15] | +3.38 |
| Intent (scenario+action) | 77.96 | 79.35 | **+1.39** | [+0.71, +2.04] | [+0.81, +1.94] | [+0.83, +2.04] | +1.39 |
| Scenario | 84.81 | 85.46 | +0.65 | [+0.18, +1.12] | [+0.22, +1.04] | [+0.19, +1.20] | +0.65 |
| Action | 79.26 | 80.65 | +1.39 | [+0.72, +2.04] | [+0.82, +1.94] | [+0.83, +2.04] | +1.39 |
| Official pooled span F1 | 29.50 | 40.30 | **+10.81** | [+8.70, +12.90] | [+9.05, +12.55] | [+8.75, +12.93] | +9.61 |
| Exact slot F1 (row mean) | 19.02 | 25.53 | +6.51 | [+5.19, +7.79] | [+5.38, +7.59] | [+5.18, +7.93] | +6.51 |
| Official SLU-F1 (row mean) | 30.29 | 32.97 | +2.68 | [+2.14, +3.22] | [+2.23, +3.14] | [+2.17, +3.22] | +2.68 |

| per-row metric | saves | harms | ties | exact two-sided McNemar p |
| --- | ---: | ---: | ---: | --- |
| intent | 15 | **0** | 1,065 | 6.104e-05 |
| scenario | 8 | 1 | 1,071 | 3.906e-02 |
| action | 15 | **0** | 1,065 | 6.104e-05 |
| exact slot F1 | 92 | 2 | 986 | 4.510e-25 |
| row SLU-F1 | 128 | 3 | 949 | 2.754e-34 |

### Cell B1 base (GATING)

| Metric | OFF | ON | Delta | Speaker CI95 | Speaker CI90 | Scenario-stratified CI95 | Equal-scenario |
| --- | ---: | ---: | ---: | --- | --- | --- | ---: |
| Official pooled SLU-F1 | 61.14 | 62.67 | **+1.53** | [+1.05, +2.03] | [+1.12, +1.94] | [+1.04, +2.05] | +1.43 |
| Intent (scenario+action) | 80.19 | 81.76 | **+1.57** | [+0.78, +2.46] | [+0.90, +2.31] | [+0.93, +2.22] | +1.57 |
| Scenario | 86.39 | 87.13 | +0.74 | [+0.20, +1.30] | [+0.29, +1.20] | [+0.19, +1.30] | +0.74 |
| Action | 81.39 | 82.96 | +1.57 | [+0.77, +2.46] | [+0.89, +2.32] | [+0.93, +2.31] | +1.57 |
| Official pooled span F1 | 48.43 | 52.65 | **+4.22** | [+2.81, +5.72] | [+3.02, +5.48] | [+2.80, +5.77] | +4.00 |
| Exact slot F1 (row mean) | 31.35 | 34.09 | +2.74 | [+1.85, +3.65] | [+1.99, +3.50] | [+1.79, +3.79] | +2.74 |
| Official SLU-F1 (row mean) | 40.15 | 41.20 | +1.05 | [+0.71, +1.40] | [+0.77, +1.34] | [+0.70, +1.43] | +1.05 |

| per-row metric | saves | harms | ties | exact two-sided McNemar p |
| --- | ---: | ---: | ---: | --- |
| intent | 17 | **0** | 1,063 | 1.526e-05 |
| scenario | 9 | 1 | 1,070 | 2.148e-02 |
| action | 17 | **0** | 1,063 | 1.526e-05 |
| exact slot F1 | 39 | 3 | 1,038 | 5.632e-09 |
| row SLU-F1 | 56 | 4 | 1,020 | 9.085e-13 |

### Cell B5e base (REPORTED, never gating)

| Metric | OFF | ON | Delta | Speaker CI95 | Speaker CI90 | Scenario-stratified CI95 | Equal-scenario |
| --- | ---: | ---: | ---: | --- | --- | --- | ---: |
| Official pooled SLU-F1 | 62.34 | 63.78 | **+1.44** | [+1.00, +1.92] | [+1.07, +1.83] | [+0.96, +1.95] | +1.37 |
| Intent (scenario+action) | 80.09 | 81.85 | **+1.76** | [+1.08, +2.47] | [+1.19, +2.35] | [+1.11, +2.50] | +1.76 |
| Scenario | 86.39 | 87.31 | +0.93 | [+0.38, +1.50] | [+0.46, +1.41] | [+0.37, +1.57] | +0.93 |
| Action | 81.39 | 83.15 | +1.76 | [+1.09, +2.50] | [+1.18, +2.37] | [+1.11, +2.50] | +1.76 |
| Official pooled span F1 | 49.82 | 53.55 | **+3.74** | [+2.45, +5.10] | [+2.65, +4.88] | [+2.45, +5.15] | +3.58 |
| Exact slot F1 (row mean) | 31.94 | 34.45 | +2.52 | [+1.68, +3.37] | [+1.81, +3.22] | [+1.60, +3.51] | +2.52 |
| Official SLU-F1 (row mean) | 41.01 | 42.01 | +1.00 | [+0.68, +1.33] | [+0.73, +1.28] | [+0.64, +1.38] | +1.00 |

| per-row metric | saves | harms | ties | exact two-sided McNemar p |
| --- | ---: | ---: | ---: | --- |
| intent | 19 | **0** | 1,061 | 3.815e-06 |
| scenario | 11 | 1 | 1,068 | 6.348e-03 |
| action | 19 | **0** | 1,061 | 3.815e-06 |
| exact slot F1 | 36 | 3 | 1,041 | 3.609e-08 |
| row SLU-F1 | 49 | 5 | 1,026 | 3.891e-10 |

## The rule, applied unchanged

| base | clause | value | threshold | passes |
| --- | --- | ---: | ---: | --- |
| anchor (GATING) | 1. official pooled SLU CI95 lower > 0 | **+2.7814** | > 0 | **YES** |
| anchor (GATING) | 2. intent CI95 lower > -h_intent | **+0.7128** | > -1.0051 | **YES** |
| anchor (GATING) | 3. no scenario intent CI95 upper < 0 | 0 of 18 | 0 | **YES** |
| anchor (GATING) | 4. decision-17 diagnostic reported | 0 scenarios flagged | reported | **YES** |
| anchor (GATING) | HARMFUL (decision 25 Method B) | SLU point +3.4609, upper +4.1797; intent point +1.3889, upper +2.0409 | point < -h or CI95 upper < 0 | **no** |
| B1 (GATING) | 1. official pooled SLU CI95 lower > 0 | **+1.0537** | > 0 | **YES** |
| B1 (GATING) | 2. intent CI95 lower > -h_intent | **+0.7821** | > -1.0051 | **YES** |
| B1 (GATING) | 3. no scenario intent CI95 upper < 0 | 0 of 18 | 0 | **YES** |
| B1 (GATING) | 4. decision-17 diagnostic reported | 0 scenarios flagged | reported | **YES** |
| B1 (GATING) | HARMFUL (decision 25 Method B) | SLU point +1.5278, upper +2.0282; intent point +1.5741, upper +2.4575 | point < -h or CI95 upper < 0 | **no** |
| B5e (reported) | 1. official pooled SLU CI95 lower > 0 | +1.0004 | > 0 | YES |
| B5e (reported) | 2. intent CI95 lower > -h_intent | +1.0820 | > -1.0051 | YES |
| B5e (reported) | 3. no scenario intent CI95 upper < 0 | 0 of 18 | 0 | YES |
| B5e (reported) | 4. decision-17 diagnostic reported | 0 scenarios flagged | reported | YES |
| B5e (reported) | HARMFUL (decision 25 Method B) | SLU point +1.4406, upper +1.9154; intent point +1.7593, upper +2.4678 | point < -h or CI95 upper < 0 | no |

**MODEL-FREE READ: ADMITTED; smoke pending.** Read exactly once, from one complete score per
arm-side; no repeat-to-pass, no re-scoring, no second estimator, no re-weighting after seeing a
number. Non-inferiority is not merely proven, it is not at issue: every clause-2 lower bound is
**positive**, so intent is superior rather than non-inferior on all three bases.

**The interval is unusually tight and this verdict says why rather than treating it as extra
evidence.** The ON and OFF arms are the same sealed rows one deterministic transform apart, so the
paired bootstrap carries **no decoding noise at all** -- only the row-to-row variation of the rule's
own effect. The CI95 half-widths are 0.6991 / 0.4872 / 0.4575 pp on pooled SLU and 0.6640 / 0.8377 /
0.6929 pp on intent, against a request-identical own null of 1.1218 / 1.0051 pp. Cell B0r's margins
were calibrated on two passes that **do** differ by decoding noise, so they are conservative here.
A narrow interval is a property of the pairing, not a stronger result.

**Where the bar stands, as a fact and not as a claim.** This cell is a one-factor module admission,
not a bar attempt (owner decisions 19, 20, 23). With the node, the anchor reads 51.9946 official
pooled SLU, cell B1 62.6672 and cell B5e 63.7757; **none clears 64.00**, cell B5e coming closest at
0.2243 pp short. All three clear the 78.00 intent bar (79.35 / 81.76 / 81.85). Nothing here is
"replicated on the same roster".

## The TRAIN symmetric view beside the official delta (owner decisions 7 and 14; never a gate)

| base | official pooled SLU delta | symmetric pooled SLU delta | symmetric CI95 | share of the official gain | official intent delta | symmetric intent delta |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| anchor | **+3.4609** | **+0.1581** | [+0.0423, +0.3033] | **4.6 %** | +1.3889 | +1.3889 |
| cell B1 | **+1.5278** | **+0.0245** | [+0.0000, +0.0797] | **1.6 %** | +1.5741 | +1.5741 |
| cell B5e | **+1.4406** | **+0.0000** | [+0.0000, +0.0000] | **0.0 %** | +1.7593 | +1.7593 |

Symmetric pooled SLU: anchor 52.0887 -> 52.2469, cell B1 62.9742 -> 62.9987, cell B5e 64.1760 ->
64.1760 (unchanged to every digit). Symmetric span F1 moves +0.6483 / +0.1030 / +0.0000.

**This table is the honest centre of the verdict, and it has two halves that must not be merged.**

*The entity half is representation alignment, and the symmetric scorer says so.* The official
pooled SLU-F1 is an entity metric: it pools the official word- and character-distance blocks and
never reads a label. Its whole gain here comes from the filler half, P2 -- and the symmetric scorer,
which normalises the gold and the prediction alike, scores **95.4 % to 100 %** of that gain at
zero. Owner decision 7 named about 2.5 pp of the 64-point bar as representation alignment rather
than capability; this read measures exactly that quantity, on three bases, and shows that the
system now performs the alignment for itself instead of being charged for not performing it. The
sealed anchor's own alignment charge was +3.56 pp (official 48.53 against symmetric 52.09,
`docs/results/2026-09-17-slurp-train-symmetric-reread-v1.md`); the node recovers **+3.46** of it.
**The node adds no capability on the entity side. It moves who writes the filler the way the corpus
writes it.**

*The label half is not discounted by the symmetric view.* The symmetric normaliser touches fillers
and never a label, so its intent delta equals the official one **exactly** on all three bases
(+1.3889 / +1.5741 / +1.7593). The `R_action` and legal-label-v2 repairs turn an illegal or
mis-split `(scenario, action)` pair into the legal pair the closed 60-id inventory already contains
-- the inventory the task contract renders into the prompt on every row. That gain is not a
representation artefact of the official scorer, and no scoring view here discounts it. It is
nevertheless a *repair of the system's own output*, not new understanding, and this verdict does
not call it capability either.

## Every scenario (natural mixture; equal-scenario mean in the last row)

`net harmed` is owner decision 17's diagnostic (harms minus saves on intent), flagged at five or
more. `beyond band` is a scenario whose own paired intent CI95 upper bound lies below zero.

### Node ON minus OFF on the anchor base

| scenario | n | OFF SLU | ON SLU | delta | OFF intent | ON intent | delta | intent CI95 | net harmed | flag | beyond band |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- | --- |
| alarm | 60 | 52.66 | 64.88 | **+12.21** | 83.33 | 83.33 | +0.00 | [+0.00, +0.00] | +0 | no | no |
| audio | 60 | 47.75 | 50.64 | +2.89 | 76.67 | 76.67 | +0.00 | [+0.00, +0.00] | +0 | no | no |
| calendar | 60 | 48.38 | 52.21 | +3.83 | 75.00 | 75.00 | +0.00 | [+0.00, +0.00] | +0 | no | no |
| cooking | 60 | 62.47 | 62.74 | +0.27 | 85.00 | 85.00 | +0.00 | [+0.00, +0.00] | +0 | no | no |
| datetime | 60 | 59.52 | 73.03 | **+13.52** | 83.33 | 83.33 | +0.00 | [+0.00, +0.00] | +0 | no | no |
| email | 60 | 36.64 | 39.44 | +2.80 | 85.00 | 85.00 | +0.00 | [+0.00, +0.00] | +0 | no | no |
| general | 60 | 15.45 | 15.45 | +0.00 | 36.67 | 36.67 | +0.00 | [+0.00, +0.00] | +0 | no | no |
| iot | 60 | 55.53 | 56.51 | +0.98 | 86.67 | 86.67 | +0.00 | [+0.00, +0.00] | +0 | no | no |
| lists | 60 | 43.55 | 43.55 | +0.00 | 83.33 | 83.33 | +0.00 | [+0.00, +0.00] | +0 | no | no |
| music | 60 | 34.53 | 34.64 | +0.11 | 76.67 | 76.67 | +0.00 | [+0.00, +0.00] | +0 | no | no |
| news | 60 | 44.24 | 47.49 | +3.25 | 80.00 | 80.00 | +0.00 | [+0.00, +0.00] | +0 | no | no |
| play | 60 | 46.82 | 49.82 | +3.00 | 58.33 | 83.33 | **+25.00** | [+14.55, +35.14] | -15 | no | no |
| qa | 60 | 57.04 | 62.24 | +5.20 | 75.00 | 75.00 | +0.00 | [+0.00, +0.00] | +0 | no | no |
| recommendation | 60 | 49.75 | 51.11 | +1.36 | 90.00 | 90.00 | +0.00 | [+0.00, +0.00] | +0 | no | no |
| social | 60 | 34.74 | 35.63 | +0.89 | 66.67 | 66.67 | +0.00 | [+0.00, +0.00] | +0 | no | no |
| takeaway | 60 | 48.84 | 52.32 | +3.48 | 85.00 | 85.00 | +0.00 | [+0.00, +0.00] | +0 | no | no |
| transport | 60 | 51.34 | 54.83 | +3.50 | 86.67 | 86.67 | +0.00 | [+0.00, +0.00] | +0 | no | no |
| weather | 60 | 53.81 | 57.44 | +3.63 | 90.00 | 90.00 | +0.00 | [+0.00, +0.00] | +0 | no | no |
| **equal-scenario mean** | 18 | | | **+3.38** | | | **+1.39** | | | | |

### Node ON minus OFF on the cell B1 base

| scenario | n | OFF SLU | ON SLU | delta | OFF intent | ON intent | delta | intent CI95 | net harmed | flag | beyond band |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- | --- |
| alarm | 60 | 65.28 | 69.26 | +3.98 | 81.67 | 85.00 | +3.33 | [+0.00, +7.32] | -2 | no | no |
| audio | 60 | 60.35 | 60.35 | +0.00 | 78.33 | 78.33 | +0.00 | [+0.00, +0.00] | +0 | no | no |
| calendar | 60 | 64.16 | 66.50 | +2.34 | 78.33 | 80.00 | +1.67 | [+0.00, +5.56] | -1 | no | no |
| cooking | 60 | 64.74 | 64.74 | +0.00 | 88.33 | 88.33 | +0.00 | [+0.00, +0.00] | +0 | no | no |
| datetime | 60 | 69.80 | 75.11 | **+5.30** | 88.33 | 88.33 | +0.00 | [+0.00, +0.00] | +0 | no | no |
| email | 60 | 57.93 | 60.75 | +2.82 | 83.33 | 83.33 | +0.00 | [+0.00, +0.00] | +0 | no | no |
| general | 60 | 20.41 | 20.41 | +0.00 | 43.33 | 43.33 | +0.00 | [+0.00, +0.00] | +0 | no | no |
| iot | 60 | 64.30 | 65.05 | +0.75 | 88.33 | 88.33 | +0.00 | [+0.00, +0.00] | +0 | no | no |
| lists | 60 | 53.45 | 53.45 | +0.00 | 85.00 | 85.00 | +0.00 | [+0.00, +0.00] | +0 | no | no |
| music | 60 | 48.87 | 49.06 | +0.19 | 78.33 | 78.33 | +0.00 | [+0.00, +0.00] | +0 | no | no |
| news | 60 | 60.85 | 65.01 | +4.16 | 83.33 | 83.33 | +0.00 | [+0.00, +0.00] | +0 | no | no |
| play | 60 | 49.94 | 51.99 | +2.05 | 60.00 | 83.33 | **+23.33** | [+14.29, +32.14] | -14 | no | no |
| qa | 60 | 58.16 | 58.82 | +0.66 | 75.00 | 75.00 | +0.00 | [+0.00, +0.00] | +0 | no | no |
| recommendation | 60 | 68.67 | 68.98 | +0.31 | 90.00 | 90.00 | +0.00 | [+0.00, +0.00] | +0 | no | no |
| social | 60 | 57.33 | 57.10 | **-0.23** | 75.00 | 75.00 | +0.00 | [+0.00, +0.00] | +0 | no | no |
| takeaway | 60 | 60.43 | 61.46 | +1.03 | 85.00 | 85.00 | +0.00 | [+0.00, +0.00] | +0 | no | no |
| transport | 60 | 62.79 | 63.70 | +0.90 | 90.00 | 90.00 | +0.00 | [+0.00, +0.00] | +0 | no | no |
| weather | 60 | 73.93 | 75.43 | +1.50 | 91.67 | 91.67 | +0.00 | [+0.00, +0.00] | +0 | no | no |
| **equal-scenario mean** | 18 | | | **+1.43** | | | **+1.57** | | | | |

### Node ON minus OFF on the cell B5e base

| scenario | n | OFF SLU | ON SLU | delta | OFF intent | ON intent | delta | intent CI95 | net harmed | flag | beyond band |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- | --- |
| alarm | 60 | 72.87 | 74.67 | +1.79 | 88.33 | 88.33 | +0.00 | [+0.00, +0.00] | +0 | no | no |
| audio | 60 | 59.88 | 59.88 | +0.00 | 83.33 | 83.33 | +0.00 | [+0.00, +0.00] | +0 | no | no |
| calendar | 60 | 63.41 | 64.19 | +0.78 | 76.67 | 76.67 | +0.00 | [+0.00, +0.00] | +0 | no | no |
| cooking | 60 | 64.52 | 64.52 | +0.00 | 86.67 | 86.67 | +0.00 | [+0.00, +0.00] | +0 | no | no |
| datetime | 60 | 71.41 | 77.96 | **+6.55** | 90.00 | 90.00 | +0.00 | [+0.00, +0.00] | +0 | no | no |
| email | 60 | 65.29 | 68.35 | +3.06 | 88.33 | 88.33 | +0.00 | [+0.00, +0.00] | +0 | no | no |
| general | 60 | 17.42 | 17.42 | +0.00 | 38.33 | 38.33 | +0.00 | [+0.00, +0.00] | +0 | no | no |
| iot | 60 | 66.75 | 66.75 | +0.00 | 88.33 | 88.33 | +0.00 | [+0.00, +0.00] | +0 | no | no |
| lists | 60 | 59.44 | 59.44 | +0.00 | 86.67 | 86.67 | +0.00 | [+0.00, +0.00] | +0 | no | no |
| music | 60 | 47.67 | 47.85 | +0.18 | 73.33 | 78.33 | +5.00 | [+0.00, +10.94] | -3 | no | no |
| news | 60 | 59.67 | 63.66 | +3.99 | 81.67 | 81.67 | +0.00 | [+0.00, +0.00] | +0 | no | no |
| play | 60 | 54.45 | 57.11 | +2.67 | 61.67 | 88.33 | **+26.67** | [+16.95, +37.93] | -16 | no | no |
| qa | 60 | 59.17 | 60.64 | +1.46 | 75.00 | 75.00 | +0.00 | [+0.00, +0.00] | +0 | no | no |
| recommendation | 60 | 67.05 | 67.37 | +0.32 | 90.00 | 90.00 | +0.00 | [+0.00, +0.00] | +0 | no | no |
| social | 60 | 55.84 | 55.63 | **-0.21** | 71.67 | 71.67 | +0.00 | [+0.00, +0.00] | +0 | no | no |
| takeaway | 60 | 56.97 | 58.52 | +1.54 | 83.33 | 83.33 | +0.00 | [+0.00, +0.00] | +0 | no | no |
| transport | 60 | 65.52 | 65.98 | +0.46 | 85.00 | 85.00 | +0.00 | [+0.00, +0.00] | +0 | no | no |
| weather | 60 | 74.10 | 76.09 | +1.99 | 93.33 | 93.33 | +0.00 | [+0.00, +0.00] | +0 | no | no |
| **equal-scenario mean** | 18 | | | **+1.37** | | | **+1.76** | | | | |

**Three readings of these tables, all descriptive.** (1) **The whole intent gain is one scenario.**
`play` moves +25.00 / +23.33 / +26.67 and every other scenario is exactly 0 except `alarm` and
`calendar` on the B1 base and `music` on the B5e base. The `R_action` rule repairs the
`play_*`-family split; nothing else in the label half fires on this roster. (2) **The entity gain
is broad but uneven.** On the anchor every scenario is flat or up, with `datetime` +13.52 and
`alarm` +12.21 carrying the mass, exactly as the A1 audit's per-scenario reading predicted. (3)
**The only negative cells anywhere are `social` on the two exemplar-carrying bases** (-0.23 and
-0.21 pooled SLU, intent flat): a P2 normalisation of a filler that the corpus writes with the
surface the model originally produced. Two cells at a fifth of a point, under a pooled interval of
+/-0.49, are noise of the rule's own shape rather than a finding.

## Diagnostics

### What the rule repaired, per arm

| base | rows | rows the rule repaired | label repairs | filler-repaired rows (entities) | unparsed, left byte-identical | rendering-suppressed | matches the registration |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| anchor | 1,080 | **191** | 20 | 174 (195) | 7 | 882 | **yes, every field** |
| cell B1 | 1,080 | **103** | 24 | 82 (90) | 4 | 973 | **yes, every field** |
| cell B5e | 1,080 | **102** | 31 | 75 (80) | 1 | 977 | **yes, every field** |

Every count reproduces the preregistration's section-6 table exactly, and the independent counts
the `analysis.deliver_normaliser_replay` provenance reports agree with this read's own row-by-row
pass on all six fields of all three arms.

**Rendering suppression is doing the work the preregistration said it would.** On 882 / 973 / 977
rows the rule repaired neither a label nor a filler, and the accepted answer was delivered
**verbatim** rather than re-rendered in canonical JSON. Without that suppression the ON arm would
have differed from its comparator on almost every row for reasons no verdict could read; with it,
`changed` means "the rule repaired this row" and the one factor is clean down to the byte.

**Label branches**, per arm (the branch the label half took on each parsed row):

| base | already-legal | `r-action` | `edit-distance` (v2 fallback) | unparsed |
| --- | ---: | ---: | ---: | ---: |
| anchor | 1,053 | 19 | 1 | 7 |
| cell B1 | 1,052 | 21 | 3 | 4 |
| cell B5e | 1,048 | 26 | 5 | 1 |

`R_action` is the dominant branch and the registered v2 fallback fires on 1, 3 and 5 rows. The
unparsed rows carry reason `unparsed` and are delivered byte-identically with `applied: false`:
an abstention or a malformed answer is never normalised, because there is no triple to project and
inventing one would be the node writing an answer rather than normalising one.

### Idempotence -- determinism holds everywhere, idempotence has one recorded exception

| base | rows | fixed points | non-fixed points |
| --- | ---: | ---: | ---: |
| anchor | 1,080 | 1,079 | **1** |
| cell B1 | 1,080 | 1,080 | 0 |
| cell B5e | 1,080 | 1,080 | 0 |

The preregistration recorded this before the read rather than letting it be discovered afterwards.
On one anchor row a `date` filler is not a fixed point of P2: the first application removes
punctuation and converts one numeric token to words, which changes the token boundaries so that a
second application converts a remaining digit as well; the third application is a fixed point.
**Invariant I7n requires the rule to be DETERMINISTIC -- the same input twice gives the same bytes --
and not idempotent**, so I7n is untouched, and the read is unaffected because the scorer applies P2
exactly once and so does the node. It is visible in exactly one place in this read: the v3 scorer
over the anchor's ON copy reports 1 changed filler where cell B1's and cell B5e's report 0, and the
resulting score is bit-identical either way. The E11 docstring's unqualified "idempotent by
construction" is proved on cell B1's and cell B5e's 2,160 rows and is **not** a general property;
`analysis.deliver_normaliser_replay`'s idempotence-witness use over a future ON arm may legitimately
report a small number of `changed: true` rows. Reported as an engineering finding; no code is
changed by this read.

### FN and FP mass by slot type, before and after the node

Reconstructed from each arm-side's own `outputs.jsonl` with the official scorer's own matching
(`analysis.slurp_entity_attribution._match_block` under the official word and character distances,
and `reproduction.slurp_scoring._exact_counts`). Every row's reconstruction was checked against
that row's own official `slu_f1` word and char tp/fp/fn before any table was built, and the
per-type decomposition closes on that side's official aggregate to better than 1e-6 on **all six
arm-sides**.

| base | total FN mass | total FP mass | exact mentions | types that moved | types that got worse |
| --- | ---: | ---: | ---: | ---: | ---: |
| anchor | **-150.32** | **-150.32** | **+100** | 16 | **0** |
| cell B1 | **-53.83** | **-53.83** | **+41** | 16 | **0** |
| cell B5e | **-49.94** | **-49.94** | **+36** | 17 | **0** |

FN and FP mass fall by exactly the same amount on every arm, because P2 converts distance-matched
near-misses into exact matches and never adds, deletes or retypes a mention: the node cannot change
the number of predicted entities. **No slot type gets worse on any base.** The largest movers:

| base | type | gold mentions | FN before -> after | FP before -> after | exact before -> after |
| --- | --- | ---: | ---: | ---: | ---: |
| anchor | `time` | 76 | 116.34 -> 65.88 (**-50.46**) | 96.34 -> 45.88 (-50.46) | 8 -> 41 (**+33**) |
| anchor | `place_name` | 100 | 108.35 -> 75.08 (-33.27) | 88.35 -> 55.08 (-33.27) | 30 -> 56 (+26) |
| anchor | `business_name` | 52 | 72.19 -> 54.63 (-17.56) | 74.19 -> 56.63 (-17.56) | 8 -> 18 (+10) |
| anchor | `date` | 138 | 203.58 -> 187.21 (-16.37) | 49.58 -> 33.21 (-16.37) | 28 -> 38 (+10) |
| anchor | `person` | 42 | 54.48 -> 44.38 (-10.10) | 58.48 -> 48.38 (-10.10) | 9 -> 15 (+6) |
| cell B1 | `time` | 76 | 68.07 -> 56.57 (-11.50) | 64.07 -> 52.57 (-11.50) | 30 -> 42 (+12) |
| cell B1 | `place_name` | 100 | 71.36 -> 61.31 (-10.05) | 85.36 -> 75.31 (-10.05) | 55 -> 63 (+8) |
| cell B1 | `person` | 42 | 45.16 -> 36.88 (-8.27) | 61.16 -> 52.88 (-8.27) | 12 -> 18 (+6) |
| cell B1 | `date` | 138 | 129.35 -> 121.08 (-8.26) | 41.35 -> 33.08 (-8.26) | 66 -> 70 (+4) |
| cell B5e | `time` | 76 | 54.39 -> 44.35 (-10.04) | 50.39 -> 40.35 (-10.04) | 39 -> 48 (+9) |
| cell B5e | `person` | 42 | 40.99 -> 33.88 (-7.11) | 52.99 -> 45.88 (-7.11) | 14 -> 19 (+5) |
| cell B5e | `place_name` | 100 | 68.85 -> 62.43 (-6.42) | 66.85 -> 60.43 (-6.42) | 58 -> 63 (+5) |
| cell B5e | `date` | 138 | 127.75 -> 121.61 (-6.15) | 49.75 -> 43.61 (-6.15) | 67 -> 70 (+3) |

`time` alone yields a third of the anchor's saving, and `place_name`, `business_name`, `date` and
`person` account for most of the rest -- the same ordering the A1 audit measured for P2, now
reproduced on three bases through the node rather than through the scorer. **`date` stays the
largest single residual loss on every base** (FN 187.21 of the anchor's remaining mass): a slot the
core never emitted cannot be normalised, and no delivery-time rule can fix an omission.

**The headroom shrinks as the base gets stronger, and the table shows why.** The anchor pays a
-150.32 FN-mass charge for surface mismatch; cell B1's exemplar supply has already taught the
system much of the corpus's surface convention, so only -53.83 is left for the node to recover, and
cell B5e's slot store removes a little more still (-49.94). The node's official gain falls from
+3.46 to +1.53 to +1.44 for the same reason. It is not a weaker rule on a stronger base; it is a
smaller alignment charge left to recover.

## What is not claimed

- **No superiority, generalization, paper-scale or held-out claim.** TRAIN Fold A is an exposed
  discovery roster; nothing is said about Fold B, DEV-1000 or the test split, which stay unread.
- **No claim that the node adds capability.** On the entity side it performs, inside the system, a
  representation alignment the official scorer charges for and the symmetric scorer scores at zero
  (95.4 % to 100 % of the pooled-SLU gain). Admitting the node moves **who** performs that
  alignment, not what the system understands. The label half is not discounted by the symmetric
  view, but it is a repair of the system's own illegal output against a closed list the prompt
  already carries, and this verdict does not call that capability either.
- **This is not a bar attempt**, and no base clears 64.00 official with the node. "Replicated on
  the same roster" (owner decision 1) is not claimed by anything here.
- **No claim about the rule itself.** Projection v3's content was decided by the A1 audit and fixed
  by item E4; nothing here re-estimates, re-tunes or re-selects it, and the support filter A1
  rejected stays rejected. That this read reproduces A1's own TRAIN A P2 interval ([+2.7814,
  +4.1797] against A1's [+2.781, +4.180]) is a reproduction, not a new estimate.
- **No component attribution below the rule.** The label half and the filler half move together and
  are admitted together; the per-half counts, the branch histogram and the per-type table are
  diagnostics, not separate admissions. That the label half's effect is confined to `play` on this
  roster is a property of this roster.
- **No claim of idempotence as a general property.** One anchor row is not a fixed point of P2 and
  is recorded above.
- **A structural smoke result is never a quality result**, and this quality result is not a
  structural one: nothing in this read shows the node executed *inside the agent*. That is the
  smoke's job and only the smoke's.
- **No claim about any later cell's comparator.** Section 4 of the preregistration fixes the
  default-plan consequence; every later cell owes its own statement of which side of the node its
  comparator sits on.
- **One read.** The rule was fixed before any number was seen and is applied exactly as registered.

## The harness-admission consequence (a proposal for the coordinator)

This verdict does not write `docs/receipts/harness-admission.json`; the receipt is the
coordinator's to close and `scripts/checks/harness_admission_check.py` is its oracle. The entry
this read supports, in the form the preregistration's section 3 fixed **before** any number was
read:

- **module**: delivery-time normaliser node (module M3 executed inside the agent: SLURP USE
  projection v3 -- `R_action`, then the registered legal-label projection v2, then filler
  normalisation P2 -- applied once to the accepted answer immediately before delivery, by the same
  two `rails.slurp_projection_v3` functions the v3 scorer applies)
- **carrier**: `slurp`
- **class**: **`episode`**
- **key**: `native_episode.deliver_normaliser`, the fourth and last entry of the closed allowlist
  `rails.config_tables.EPISODE_LEVEL_SWITCH_KEYS`
- **off**: `null` -- the key's absence. A delivery node is either absent or armed; there is no third
  shape (`rails.config_tables.is_episode_null_arm`).
- **on**: `{"normaliser": "saea-deliver-normalise-v3"}`
- **proof**:
  `tests/unit/test_config_table_module_switches.py::test_deliver_normaliser_is_one_episode_class_key`,
  supported by the E11 tests
  `tests/unit/test_deliver_normaliser_node.py::test_the_switch_key_is_on_the_closed_episode_allowlist`,
  `::test_the_off_arm_is_the_key_absent`,
  `tests/unit/test_native_episode_runner_deliver_normaliser.py::test_the_node_rewrites_only_what_is_delivered_and_no_request_byte`
  and
  `tests/unit/test_deliver_normaliser_sealed_replay.py::test_the_node_reproduces_the_v3_scorer_projection_on_every_sealed_row`
- **why_this_table**: it is a NODE of the episode, declared beside the roles it runs after and
  applied by `rails.runner` between the Planner's ACCEPT and the delivered answer -- not a per-phase
  request-table entry, and not the `run` class, whose zero-request-byte licence it does not claim
  even though it happens to move no request byte
- **comparator**: each base's own sealed rows. The OFF arm is the comparator itself -- the sealed
  anchor `SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1` and cell B1's recovery arm
  `SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TRAIN-FOLD-A-RECOVERY-V2`, neither re-flown nor
  re-scored. No separate OFF cell was flown and none is needed: the node is deterministic and
  zero-contact, so the ON arm is computable from the OFF arm's own bytes.
- **status**: **ADMITTED**
- **status_basis**: the registered single-factor rule of the B8a preregistration section 8, applied
  unchanged. On the anchor base official pooled SLU-F1 48.5336 -> 51.9946, **+3.4609 pp CI95
  [+2.7814, +4.1797]**, intent 77.9630 -> 79.3519, **+1.3889 [+0.7128, +2.0409]**; on the cell B1
  base 61.1394 -> 62.6672, **+1.5278 [+1.0537, +2.0282]**, intent 80.1852 -> 81.7593, **+1.5741
  [+0.7821, +2.4575]**. Both clause-1 lower bounds clear zero and both clause-2 lower bounds are
  positive, so intent is superior rather than merely non-inferior. 0 of 18 scenarios breach the
  intent band and 0 reach owner decision 17's flag, on all three contrasts. The HARMFUL clause does
  not fire on either gating base. Intent is harmed on **zero** rows of any arm. Reported third base
  (cell B5e, never gating): +1.4406 [+1.0004, +1.9154], intent +1.7593 [+1.0820, +2.4678]. The
  TRAIN symmetric delta is +0.1581 / +0.0245 / +0.0000, i.e. **4.6 % / 1.6 % / 0.0 %** of the
  official pooled-SLU gain: the rest is the representation alignment owner decision 7 named, now
  performed by the system itself. The symmetric intent delta equals the official one exactly,
  because the normaliser touches fillers and never a label.
- **evidence**: this verdict; the three sealed scores `73608763...`, `a7105b32...`, `aeed7ad9...`;
  the paired read `SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-B8A-DELIVERY-NODE-READ-V1/` with
  `score-contrasts.json` `af79e7b5886f9de878c0a3fe42ac5c94da63c72e658ac0dc61f32bf2cef1c35a` and
  every other output hashed in its `README.md`; the four-row smoke run
  `SAEA-SLURP-NATIVE-B8A-DELIVER-NORMALISE-V3-EXEMPLARS-K20-SMOKE-4-V1` (see "Smoke" below, which
  the coordinator owns)
- **provisional**: `state` **UNMET** pending the smoke section below. The quality clause is closed
  by this read and needs no replicate -- the ON and OFF arms are the same sealed rows one
  deterministic transform apart, so there is no decoding noise for a replicate to price and a
  request-identical re-fly would reproduce these numbers exactly. What is **not** closed by a
  sealed-byte read is that the node executed *inside the agent*; that is the four-row smoke's
  single job, and the entry should not be written ADMITTED until the coordinator records its
  structural acceptance.
- **not_admitted_for**: any claim of added capability; any other roster, carrier, fold or split;
  any claim about the `slurp_projection_v3_delivery` seal-time key of item E4, which is a different
  module at a different seam and stays `held`; any paper-scale or generalisation claim.

### The default-plan consequence, fixed before the number was known

`scripts/checks/harness_admission_check.py` requires every ADMITTED or NEUTRAL module to appear in
at least one default plan for its carrier. The preregistration's section 4 therefore already fixed
what an ADMITTED reading means:

> the SLURP default plan
> (`configs/baseline/slurp-native-dual-store-train-fold-a-default-plan-v1.json`) gains the key
> `native_episode.deliver_normaliser = {"normaliser": "saea-deliver-normalise-v3"}`, and every
> later official SLURP number this program reports -- cells B7a, B7r, B8b, B4a, B8c, B5b, the v2.0
> lock, and any DEV-1000 or Fold B confirmation -- is produced by a system that contains the node.

That is the point of owner directive 26 and not a side effect. It also means later cells must state
their comparators carefully: **a cell registered against a sealed arm that pre-dates the node
compares a node-carrying arm against a node-free one, and its verdict must say so.** This verdict
fixes the consequence; it pre-authorises no later cell.

## Smoke (the coordinator's section, closed 2026-09-19)

Run `SAEA-SLURP-NATIVE-B8A-DELIVER-NORMALISE-V3-EXEMPLARS-K20-SMOKE-4-V1`, attempt `attempt-slurp-native-b8a-deliver-normalise-v3-exemplars-k20-smoke-4-generation-v1`, flown on the B1 recovery smoke base with the node armed and closed by the coordinator at study commit e79ce296 ("structural PASS: node receipt on 4/4 rows, sealed with I7n, 24/24 fits"): the `deliver_normaliser` receipt is present on 4 of 4 rows, the bundle sealed with the I7n custody invariant, every request fit (24 of 24 request-fit receipts), and the smoke's exposure-ledger rows (generation and fit) were closed with their actuals in the same commit. The smoke asserts structure only; the number of this cell is the model-free read above. Together they discharge the registered admission rule, so module M3 is ADMITTED and enters the SLURP default plan as `native_episode.deliver_normaliser` (section 4 of the preregistration).

## Exposure

**Zero model, tokenizer, encoder, ASR, server and paid-API contacts.** This read touched no serving
session, flight worktree, scheduled task or flight lock, launched no flight, and wrote no run
directory. The only scorer invocations are the registered model-free SLURP scorings -- **15 in
total**: the official `slurp-slu-official-train` over the three node-ON copies (the OFF official
numbers are the sealed `scores.json` files, re-verified by hash, and invoke no scorer), and
`slurp-slu-official-projected-v3-train` and `slurp-slu-f1-normalized-v1-train` over both sides of
all three arms. Each is one complete, never-sharded invocation over a COPY of an `outputs.jsonl`
written under
`SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-B8A-DELIVERY-NODE-READ-V1/`, or over the node's own replayed
copy of one; every OFF copy hash-matches its sealed source byte for byte. **The sealed bytes were
copied, never opened for writing**, and no sealed file was moved or renamed. The node replay
reports `model_calls: 0` on every arm. Gold was read only where the registered scorer and the
official `evaluate.py` already read it, and for the per-type slot decomposition; **no utterance
text, transcript, gold filler, predicted filler or model response text is printed or persisted
anywhere in this read or this verdict** -- ids, counts, hashes, scenario names, entity-type names,
branch names and scores only. No exposure-ledger row, harness-admission receipt, results ledger or
default plan was edited by this read. Execution profile `model-free-check`; the zero-contact
exposure row `SAEA-SLURP-B8A-DELIVER-NORMALISE-MODEL-FREE-READ-V1` was registered before the read
and is unchanged by it.
