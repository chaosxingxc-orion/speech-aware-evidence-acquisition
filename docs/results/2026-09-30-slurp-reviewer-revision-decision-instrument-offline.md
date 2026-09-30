# SLURP Reviewer-routed revision as a decision instrument: the route does not find the oracle's rows (precision 0.05-0.29, below the 0.33 bar in every pool), so close the Solver-node blank (DESCRIPTIVE, offline)

Date: 2026-09-30. Read id `SAEA-SLURP-REVIEWER-REVISION-INSTRUMENT-OFFLINE-V1`, recipe
`slurp-reviewer-revision-instrument-offline-v1`. Written by Claude Opus 5.5 (analysis agent; coordinator ruling R2 on
`docs/superpowers/specs/2026-09-30-solver-intent-decision-mechanism-design.md`, Fable 5.1) in worktree
`fable/revisioninstr` (base master `be18200c7`, which already carries `fable/solverdecision`).

**Status: DESCRIPTIVE.** These are development numbers on TRAIN Fold A and TRAIN Fold B, both construction rosters
(owner decisions 28 and 86). The note makes no test, generalisation or superiority claim. The verdict word belongs to
the coordinator (decision 139).

**Contacts: zero of every kind.** The read made no model, server, tokenizer, encoder, embedder, GPU, network or
paid-API contact, and ran no official-scorer subprocess. The sealed per-row official intent flags were read only to
cross-check the parsed delivered answer. `core.flight.cli` and `lease_cli` were not invoked. Gold entered only offline,
through the governed TRAIN loader `data.slurp.load_slurp_split`. No utterance text, note text, exemplar body, gold
value, Reviewer text or model output is printed or persisted. The outputs hold only ids, counts, rates, AUCs, pp and
hashes.

**Driver and outputs.**

- Driver: `scripts/analysis/slurp_reviewer_revision_instrument.py`, sha256
  `474ee8605170c35d3526a18c8bc8f08d24ac248b46f5a60142184161932df798`. It imports the oracle driver
  `scripts/analysis/slurp_solver_decision_oracle.py` (sha256 `feed18d1...d4d43a`, unmodified) for its row-state
  primitives: `classify`, `dedupe`, `rank_of`, `split_half`, `auc`, `score_margin`, `f1_threshold`, `scenario_of`,
  `CFG` and the REV-TFRL-1 anchor. Answers are parsed with the credit table's `parse_answer`
  (`scripts/analysis/slurp_reviewer_credit_table.py`, unmodified), which applies the runtime delivery projection and
  then the official parse.
- Unit test on fakes: `tests/unit/test_slurp_reviewer_revision_instrument.py` (9 passed).
- Machine outputs: `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-REVIEWER-REVISION-INSTRUMENT-OFFLINE-V1/` (`report.json`,
  `tables.md`, `content-sha256.json`). Every number below comes from `report.json` unless it is marked "derived".
- `--check` re-derived both files. They were IDENTICAL apart from `generated_at`. Content hashes, with
  `generated_at` removed: `report.json` `0bfd19d884ca15f2f8ee0ab861f279a4bec9e0ba6dc1d53801611a8285e652f9`, `tables.md`
  `a827332ccc10ec1835059b771be13e068cc0de51247a84cf029479d5014aa1e3`. Wall time 2.6 min, peak memory 0.96 GB.
  `inputs` lists 43 hashed files.

## 0. Pools, definitions and custody

**Pools.** The read covers every COMPLETED full-roster (1,080-row) Fold A / Fold B pool whose phase artefact carries
Perception, Planner, Reviewer and Solver states. That is 13 Fold A pools and 3 Fold B pools [`pools`]:

- REV-TFRL-1 arm (`revtfrl`), which flew the contrastive Reviewer instruction;
- its in-chain A/A (`revtfrl_aa`);
- AGREE (`agree`), AGREE A/A (`agree_aa`) and the wave A/A (`wave_aa`);
- G5 (`g5`), COMP-1 A/A (`comp1_aa`) and COMP-1b (`comp1b`);
- W1-CARDSEL, W3, W4, W4-SV and W-SV-1;
- the P-SV-1/2/3 level-2 episodes (`psv1-3`, Fold B).

Excluded [`excluded`]:

- COMP-1 and RELISTEN: seal-only attempts with no agent states;
- ROLL-2: a grouped-sample Solver form, so its first answer is not comparable;
- every partial roster: CONV-70, DET-50 A/B, RANKVIS-119, KPROBE-55 and FILLER-180 x 6.

**Definitions.**

- **First answer:** the first `phase:solver` state.
- **REVISE:** the Planner route after the first Reviewer visit is `REVISE`.
- **Revised answer:** the second Solver state.
- **Delivered answer:** the last Solver state.
- **Oracle classes:** the oracle's `classify` applied to the first answer and the deduplicated first Perception note.
  - *Positive:* the note has at least 2 candidates, the Solver kept note rank 1, and gold is at note rank 2 or 3.
  - *Negative:* the Solver kept rank 1 and rank 1 is gold.
  - *Cost row:* the Solver kept rank 1 and gold is off the note.
- **Conversion:** among REVISE-routed positives, the share whose delivered answer is gold.
- **Harm:** among REVISE-routed rows whose first answer was right on intent, the share whose delivered answer is
  wrong.
- **Loop net:** the delivered answer minus the first answer on intent, over the whole roster. Its CI is a paired
  bootstrap clustered by `sample_id` (10,000 draws, seed 20260929).

**Custody** [`checks`]:

- The parsed delivered intent agrees with the sealed official intent flag on **1,080 / 1,080** rows in all 16 pools.
- The parse differs from the oracle's parse in one respect: the oracle parsed the first answer raw, while this read
  applies the delivery projection first. The first pick is the same under both parses on 1,044-1,061 rows per pool.
  As a result, positive counts differ from the oracle's by 0-3 rows (for example AGREE 62 here and 59 in the oracle).
- The boundary margin is recomputed through the production constructor, mirroring the oracle's closure. Its
  recomputed block equals the sealed block on 1,080 / 1,080 rows in 13 pools, and the margin is used only there. In
  `agree_aa`, `comp1_aa` and `g5` it matches only 254 rows, because those pools flew a pre-AGREE retrieval. There
  the margin is unavailable and only its model-visible twin, the exemplar-vote difference, is read.
- 0 exemplar keys are unresolved.
- A Reviewer route is present on 1,066-1,080 rows per pool.

## 1. Reach, conversion, harm and net per pool

[`pools.<pool>.reach`, `conversion_delivered`, `loop_net_delivered_minus_first`; `pooled.<group>`]

| pool | REVISE rows | positives | REVISE on positives | recall | precision (all REVISE) | conversion, gold r2 ; r3 | conversion | harm | loop net rows | loop net pp [CI95] |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- |
| REV-TFRL-1 (contrastive) | 464 | 60 | 44 | **0.733** | **0.095** | 7/31 ; 0/13 | **0.159** | 0.043 (15/349) | −1 | −0.09 [−1.11, +0.93] |
| REV-TFRL-1 A/A | 34 | 60 | 6 | 0.100 | 0.176 | 1/3 ; 2/3 | 0.500 | 0.188 (3/16) | +2 | +0.19 [−0.28, +0.74] |
| AGREE | 23 | 62 | 3 | 0.048 | 0.130 | 1/2 ; 1/1 | 0.667 | 0.214 (3/14) | −1 | −0.09 [−0.46, +0.28] |
| AGREE A/A | 32 | 49 | 4 | 0.082 | 0.125 | 1/4 ; 0/0 | 0.250 | 0.154 (2/13) | +2 | +0.19 [−0.28, +0.65] |
| wave A/A | 29 | 69 | 5 | 0.072 | 0.172 | 1/4 ; 0/1 | 0.200 | 0.125 (2/16) | +1 | +0.09 [−0.28, +0.56] |
| G5 | 31 | 56 | 3 | 0.054 | 0.097 | 1/2 ; 0/1 | 0.333 | 0.091 (1/11) | +5 | +0.46 [0.00, +0.93] |
| COMP-1 A/A | 42 | 52 | 2 | 0.038 | 0.048 | 0/2 ; 0/0 | 0.000 | 0.136 (3/22) | +4 | +0.37 [−0.19, +0.93] |
| COMP-1b | 17 | 68 | 4 | 0.059 | 0.235 | 1/3 ; 0/1 | 0.250 | 0.143 (1/7) | 0 | 0.00 [−0.28, +0.28] |
| W1-CARDSEL | 29 | 66 | 7 | 0.106 | 0.241 | 2/5 ; 1/2 | 0.429 | 0.067 (1/15) | +2 | +0.19 [−0.19, +0.56] |
| W3 | 17 | 68 | 5 | 0.074 | 0.294 | 0/4 ; 0/1 | 0.000 | 0.100 (1/10) | −1 | −0.09 [−0.28, 0.00] |
| W4 | 23 | 60 | 4 | 0.067 | 0.174 | 0/1 ; 1/3 | 0.250 | 0.400 (6/15) | −5 | −0.46 [−1.02, 0.00] |
| W4-SV | 20 | 61 | 4 | 0.066 | 0.200 | 0/3 ; 1/1 | 0.250 | 0.091 (1/11) | +2 | +0.19 [−0.19, +0.56] |
| W-SV-1 | 24 | 63 | 3 | 0.048 | 0.125 | 0/2 ; 0/1 | 0.000 | 0.000 (0/12) | +1 | +0.09 [0.00, +0.28] |
| P-SV-1 (B) | 26 | 78 | 5 | 0.064 | 0.192 | 2/3 ; 1/2 | 0.600 | 0.300 (3/10) | +2 | +0.19 [−0.28, +0.74] |
| P-SV-2 (B) | 28 | 74 | 3 | 0.041 | 0.107 | 3/3 ; 0/0 | 1.000 | 0.059 (1/17) | +5 | +0.46 [0.00, +0.93] |
| P-SV-3 (B) | 24 | 79 | 3 | 0.038 | 0.125 | 2/3 ; 0/0 | 0.667 | 0.091 (1/11) | +3 | +0.28 [−0.09, +0.74] |
| **pooled, all 16** | 863 | 1,025 | 105 | 0.102 | **0.122** [0.10, 0.15] | 22/75 ; 7/30 | **0.276** [0.20, 0.37] | 0.080 (44/549) | +21 | +0.12 [−0.02, +0.27] |
| **pooled, 15 standard forms** | 399 | 965 | 61 | 0.063 | **0.153** [0.12, 0.19] | 15/44 ; 7/17 | **0.361** [0.25, 0.49] | 0.145 (29/200) | +22 | +0.14 [+0.01, +0.27] |
| pooled, Fold A standard (12) | 321 | 734 | 50 | 0.068 | 0.156 [0.12, 0.20] | 8/35 ; 6/15 | 0.280 [0.17, 0.42] | 0.148 (24/162) | +12 | +0.09 [−0.05, +0.24] |
| pooled, Fold B (3) | 78 | 231 | 11 | 0.048 | 0.141 [0.08, 0.24] | 7/9 ; 1/2 | 0.727 [0.43, 0.90] | 0.132 (5/38) | +10 | +0.31 [+0.03, +0.59] |

Proportion intervals are Wilson CI95. Pooled rows sum pools that share a roster, so they are not independent
replicates. The pooled loop-net CI clusters every pool's copy of a `sample_id` together.

- **The standard Reviewer barely reaches the oracle's rows.** It routes REVISE on 3.8-10.6 % of positives, against
  0.8-1.8 % of negatives [`reach.revise_rate_positive / _negative`]. Of its REVISE routes, 4.8-29.4 % are oracle
  positives. The rest land on first-right rows (7-22 per pool), cost rows (1-16) and rows where the Solver had
  already switched (0-6).
- **The contrastive Reviewer reaches the rows but converts badly.** REV-TFRL-1 routes 44 of 60 positives
  (recall 0.73), at a precision of 0.095 over 464 routes. Only 7 of the 44 convert (0.159). Gold at note rank 3
  converts 0 / 13. Its loop net is −1 row, which reproduces the REV-TFRL-1 read (intent repairs 14 / breaks 15).
  The 0.159 on the oracle's positives sits below the 0.185 anchor the oracle borrowed. The anchor's 10 / 54 counted
  INT-SHORTLIST visits under the credit table's entity-aware classes; this read's REV-TFRL-1 row is
  `repairable_first_wrong_gold_on_note` 10 / 55.
- **Where the standard route does fire on a positive, conversion is higher (pooled 22 / 61 = 0.36) but the n is
  tiny.** Per pool it is 0-7 routed positives, and every standard-pool conversion CI spans at least 0.4 in width
  [`conversion_ci95`]. The total gain of routed positives is 0-3 rows per standard pool
  [`loop_net_rows_on_oracle_positives`].

## 2. Does the route track the oracle's signals?

The first AUC below is the REVISE route (as a binary score) against the oracle label on positives and negatives
[`reach.route_auc_vs_oracle_label`]. The next three are signal AUCs against "REVISE routed", on decision rows
[`route_auc_by_signal_decision_rows`], with the same signals' AUCs against the oracle label beside them
[`label_auc_by_signal`]. Values below 0.5 mean that REVISE rows, or positives, carry the smaller value.

| pool | route vs oracle label | exemplar-vote diff r1 − r2: vs route / vs label | boundary margin: vs route / vs label | votes for r2: vs route / vs label |
| --- | ---: | --- | --- | --- |
| REV-TFRL-1 | 0.677 | 0.364 / 0.221 | 0.362 / 0.209 | 0.584 / 0.723 |
| REV-TFRL-1 A/A | 0.541 | 0.366 / 0.221 | 0.360 / 0.207 | 0.570 / 0.741 |
| AGREE | 0.517 | 0.311 / 0.213 | 0.321 / 0.201 | 0.621 / 0.717 |
| AGREE A/A | 0.533 | 0.299 / 0.126 | -- | 0.581 / 0.787 |
| wave A/A | 0.528 | 0.365 / 0.196 | 0.380 / 0.186 | 0.580 / 0.762 |
| G5 | 0.521 | 0.229 / 0.103 | -- | 0.528 / 0.776 |
| COMP-1 A/A | 0.510 | 0.261 / 0.124 | -- | 0.516 / 0.773 |
| COMP-1b | 0.525 | 0.386 / 0.249 | 0.390 / 0.248 | 0.516 / 0.713 |
| W1-CARDSEL | 0.545 | 0.408 / 0.211 | 0.398 / 0.201 | 0.504 / 0.737 |
| W3 | 0.532 | 0.383 / 0.264 | 0.366 / 0.245 | 0.537 / 0.682 |
| W4 | 0.526 | 0.357 / 0.226 | 0.365 / 0.213 | 0.565 / 0.724 |
| W4-SV | 0.526 | 0.449 / 0.224 | 0.434 / 0.211 | 0.519 / 0.716 |
| W-SV-1 | 0.518 | 0.361 / 0.233 | 0.329 / 0.219 | 0.538 / 0.724 |
| P-SV-1 | 0.526 | 0.408 / 0.234 | 0.394 / 0.218 | 0.495 / 0.698 |
| P-SV-2 | 0.512 | 0.463 / 0.243 | 0.456 / 0.226 | 0.459 / 0.714 |
| P-SV-3 | 0.513 | 0.390 / 0.243 | 0.369 / 0.226 | 0.557 / 0.695 |

- **The Reviewer is weakly aligned with the margin, not orthogonal to it.** In every pool, REVISE falls more often
  where the vote difference or margin is small (AUC 0.23-0.46 against the route). It does so more weakly than the
  oracle label does (0.10-0.26).
- **As a decider, the standard route sits at chance.** Its AUC against the oracle label is 0.51-0.55: it fires on
  too few rows to separate anything.
- **The contrastive form lifts the route AUC to 0.68, but only by firing on 38 % of negatives**
  [`revise_rate_negative` 0.379].
- The P-SV pools and W4-SV track the signal least (0.39-0.46).

## 3. Confidence proxies against the oracle (decision rows, implied net at the REV-TFRL-1 conversion 0.185 / harm 0.049)

Every flag is evaluated on the decision rows: positives, negatives and cost rows (cost rows count as calls).
Continuous flags use a threshold chosen on one sha256(utterance id) half and applied to the other. The "net" rule
picks the threshold that maximises implied net rows in-half; the "F1" rule is the oracle's F1 threshold
[`pools.<pool>.proxies`, `proxy_pooled`].

**Pooled over the 16 pools** [`proxy_pooled`]:

| proxy | flagged | TP | FP | cost | precision | recall | mean implied net rows per pool | mean implied pp |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| (a2) cross-flight switching propensity > 0 (leave-this-pool-out, same fold) | 1,292 | 195 | 779 | 318 | 0.151 | 0.190 | −0.12 | −0.011 |
| (a2) switching propensity, cross-fit net threshold | 460 | 70 | 276 | 114 | 0.152 | 0.068 | −0.03 | −0.003 |
| (b) Reviewer REVISE route | 760 | 105 | 494 | 161 | 0.138 | 0.102 | −0.29 | −0.027 |
| (c) low boundary margin, cross-fit net (13 pools) | 1,458 | 175 | 1,043 | 240 | 0.120 | 0.202 | −1.42 | −0.132 |
| (c) low boundary margin, cross-fit F1 (13 pools) | 2,706 | 363 | 1,897 | 446 | 0.134 | 0.418 | −1.95 | −0.180 |
| (c') low exemplar-vote difference, cross-fit net | 1,438 | 225 | 931 | 282 | 0.157 | 0.220 | −0.23 | −0.022 |
| (c') low exemplar-vote difference, cross-fit F1 | 3,029 | 464 | 2,083 | 482 | 0.153 | 0.453 | −0.98 | −0.091 |
| (b) AND (c') net | 130 | 24 | 65 | 41 | 0.185 | 0.023 | +0.08 | +0.007 |
| perfect flag (reference) | 1,025 | 1,025 | 0 | 0 | 1.000 | 1.000 | +11.86 | +1.098 |

**(a1) The Solver's own switching** [`proxies.a1_own_switch`] flags no decision row, because the decision set is by
construction the set of rows where the Solver kept rank 1. On its own rows it is the precise re-decider the oracle
described: 29-51 switches per pool, 18-29 of them right (precision 0.47-0.79). It never touches a kept-r1 error.
Its cross-flight form (a2) asks whether the Solver switches on this row in another flight. That signal marks the
oracle's positives only weakly (label AUC 0.53-0.61, precision 0.15 pooled).

**Best cross-fitted flag per pool** (the maximum implied net over a2, b, c, c', b AND c'; derived from `proxies`):

| pool | best flag | flagged / TP / FP / cost | precision | implied net rows | implied pp |
| --- | --- | --- | ---: | ---: | ---: |
| G5 | (c') vote diff, net | 154 / 42 / 64 / 48 | 0.273 | +4.66 | +0.431 |
| COMP-1 A/A | (c') vote diff, net | 116 / 29 / 51 / 36 | 0.250 | +2.88 | +0.267 |
| AGREE A/A | (c') vote diff, net | 112 / 28 / 54 / 30 | 0.250 | +2.55 | +0.236 |
| P-SV-3 | (a2) propensity | 23 / 7 / 9 / 7 | 0.304 | +0.86 | +0.079 |
| W1-CARDSEL | (b) REVISE | 26 / 7 / 14 / 5 | 0.269 | +0.61 | +0.057 |
| W3 | (b) REVISE | 13 / 5 / 7 / 1 | 0.385 | +0.58 | +0.054 |
| P-SV-1 | (b) AND (c') | 7 / 3 / 1 / 3 | 0.429 | +0.51 | +0.047 |
| P-SV-2 | (a2) propensity | 34 / 7 / 18 / 9 | 0.206 | +0.42 | +0.039 |
| COMP-1b | (b) REVISE | 16 / 4 / 7 / 5 | 0.250 | +0.40 | +0.037 |
| REV-TFRL-1 A/A | (b) REVISE | 30 / 6 / 15 / 9 | 0.200 | +0.38 | +0.035 |
| W4-SV | (b) AND (c') | 4 / 2 / 1 / 1 | 0.500 | +0.32 | +0.030 |
| W-SV-1 | (a2) propensity, net | 14 / 4 / 9 / 1 | 0.286 | +0.30 | +0.028 |
| wave A/A | (b) REVISE | 25 / 5 / 14 / 6 | 0.200 | +0.24 | +0.022 |
| W4 | (b) REVISE | 19 / 4 / 12 / 3 | 0.211 | +0.16 | +0.014 |
| AGREE | (a2) propensity > 0 | 94 / 16 / 59 / 19 | 0.170 | +0.08 | +0.008 |
| REV-TFRL-1 | (a2) propensity, net | 11 / 2 / 7 / 2 | 0.182 | +0.03 | +0.003 |

Choosing the best flag per pool is itself a selection over five flags on the scored rows, so this column is an
optimistic ceiling. Even so, the best is +4.66 rows (0.43 pp) against the 7.02-row (0.65 pp) same-flight floor.

The three pools where the vote-difference flag nets +2.5 to +4.7 rows (G5, COMP-1 A/A, AGREE A/A) are the pools whose
sealed block the AGREE / COMP-1b recomputation does not reproduce (254 / 1,080 rows), which indicates a pre-AGREE
retrieval. There the vote difference separates positives much better (label AUC 0.10-0.13, against
0.20-0.26 elsewhere). Under the current AGREE retrieval, which is the production configuration, the same flag nets
−0.03 to −2.6 rows.

**Derived: the break-even precision.** At a measured conversion c and harm h, a flag pays only when
TP·c > FP·h, that is when precision excluding cost rows exceeds h / (c + h).

| conversion / harm pair | break-even precision (excl. cost) |
| --- | ---: |
| REV-TFRL-1 anchor 0.185 / 0.049 | 0.21 |
| 15 standard forms 0.361 / 0.145 (this read) | 0.29 |
| REV-TFRL-1 on oracle rows 0.159 / 0.043 (this read) | 0.21 |

The pooled proxies' precision excluding cost rows (derived from `proxy_pooled`, TP / (TP + FP)):

- (a2) propensity > 0: 0.20;
- (b) REVISE: 0.18;
- (c) margin: 0.14 (net) and 0.16 (F1);
- (c') vote difference: 0.19 (net) and 0.18 (F1);
- (b) AND (c'): 0.27.

Only the conjunction clears the 0.21 anchor break-even, and it does so at recall 0.023 (+0.08 rows per pool). None
clears the 0.29 standard-form break-even. The oracle's two-signal rules, at 0.14-0.22 including cost rows, sit in the
same band.

## 4. Verdict against the coordinator's thresholds (conversion >= 0.30 AND revise-decision precision >= 0.33)

[`pools.<pool>.verdict`, `pooled.<group>.verdict`]

| scope | conversion | clears 0.30 | precision | clears 0.33 | both |
| --- | ---: | --- | ---: | --- | --- |
| REV-TFRL-1 (contrastive) | 0.159 (7/44) | no | 0.095 | no | **no** |
| REV-TFRL-1 A/A | 0.500 (3/6) | yes (n 6) | 0.176 | no | **no** |
| AGREE | 0.667 (2/3) | yes (n 3) | 0.130 | no | **no** |
| AGREE A/A | 0.250 (1/4) | no | 0.125 | no | **no** |
| wave A/A | 0.200 (1/5) | no | 0.172 | no | **no** |
| G5 | 0.333 (1/3) | yes (n 3) | 0.097 | no | **no** |
| COMP-1 A/A | 0.000 (0/2) | no | 0.048 | no | **no** |
| COMP-1b | 0.250 (1/4) | no | 0.235 | no | **no** |
| W1-CARDSEL | 0.429 (3/7) | yes (n 7) | 0.241 | no | **no** |
| W3 | 0.000 (0/5) | no | 0.294 | no | **no** |
| W4 | 0.250 (1/4) | no | 0.174 | no | **no** |
| W4-SV | 0.250 (1/4) | no | 0.200 | no | **no** |
| W-SV-1 | 0.000 (0/3) | no | 0.125 | no | **no** |
| P-SV-1 | 0.600 (3/5) | yes (n 5) | 0.192 | no | **no** |
| P-SV-2 | 1.000 (3/3) | yes (n 3) | 0.107 | no | **no** |
| P-SV-3 | 0.667 (2/3) | yes (n 3) | 0.125 | no | **no** |
| pooled, all 16 | 0.276 [0.20, 0.37] | no | 0.122 [0.10, 0.15] | no | **no** |
| pooled, 15 standard forms | 0.361 [0.25, 0.49] | yes (point; CI spans 0.30) | 0.153 [0.12, 0.19] | no (CI upper end 0.19) | **no** |
| pooled, Fold B | 0.727 [0.43, 0.90] | yes (n 11) | 0.141 [0.08, 0.24] | no | **no** |

- **Precision fails everywhere.** No pool reaches 0.33. The highest is W3 at 0.294, and its conversion is 0 / 5.
  Restricted to decision rows, W3 reads 5 / 13 = 0.385 [`precision_in_decision_set`], still with zero conversion.
  Every pooled upper CI end sits at or below 0.24.
- **Conversion clears 0.30 only where n is 3-7 per pool, and in the 15-standard-form pool (0.361).** That pool's CI
  [0.25, 0.49] straddles the bar. The one form with real reach (contrastive, 44 routed positives) converts 0.159.
- **Implied whole-roster pp at the best flag under cross-fit:**
  - In the production-configured (AGREE-retrieval) pools, at most +0.08 pp.
  - Over all 16 pools, at most +0.43 pp (G5, pre-AGREE retrieval, the optimistic per-pool maximum).
  - Pooled means per pool are −0.18 to +0.007 pp.
  - **None clears 0.65 pp (7.02 rows).**
  - Only a perfect flag clears it: 9.07-14.63 rows (0.84-1.36 pp) at the REV-TFRL-1 rates, and no measured signal
    comes near perfect.
- **The measured loop is small and positive in the standard forms.** The 15-standard-form loop net is +22 rows,
  +0.14 pp [+0.01, +0.27] per flight: 51 saves against 29 harms [`pooled.standard_forms.loop_net`]. That equals the
  22 converted oracle positives, 0-3 per flight [`loop_net_rows_on_oracle_positives`]; the other 29 repairs are
  cancelled by the 29 breaks. At 0-3 rows per flight it sits about five times below the 7.02-row floor.

## What this note does not claim

- It does not measure what a model-DECLARED confidence would score. No sealed output carries one. The proxies are the
  best available stand-ins, and a declared flag could in principle behave differently from all of them.
- Conversion under a declared-confidence contract with a different re-decision form is not measured here. The
  re-decision measured is the sealed Reviewer -> Planner REVISE -> second Solver contact under the standard and the
  contrastive Reviewer forms.
- The pooled rows sum flights over the same rosters. They are not independent replicates, and per-pool conversions
  rest on 2-7 routed positives.
- The best-flag-per-pool table selects over five flags on the scored rows, so it is an optimistic ceiling. The
  thresholds themselves are cross-fitted.
- Delivered answers are parsed through the runtime delivery projection. This read's positive counts therefore differ
  from the oracle's raw-parse counts by 0-3 rows per pool (section 0).
- Every number is a TRAIN development number (decisions 28, 86). Nothing is nominated or admitted.

## Recommendation to the coordinator

**Close the Solver-node blank; do not register M-B stage 1.** The ruling-R2 gate needs revise-decision precision
>= 0.33. The measured Reviewer route reaches 0.05-0.29 per pool, 0.12 pooled over 16 pools [0.10, 0.15], and 0.15
over the 15 standard forms [0.12, 0.19]. No confidence proxy in the sealed data does better, whether switching
propensity, low margin, low vote difference or the route combined with low votes. Pooled, they sit at 0.12-0.19.
Conversion is 0.159 where the Reviewer has real reach (REV-TFRL-1, 7/44, rank-3 gold 0/13). It is 0.36 [0.25, 0.49]
where the Reviewer barely fires (61 routed positives over 15 flights). The best cross-fitted flag implies at most
+0.43 pp, and at most +0.08 pp in the production-configured pools, against a 0.65 pp floor.

Only one path could reopen the blank: a declared-confidence instrument whose flag reaches precision above
0.33 while converting above 0.30. Nothing measured here comes within about 0.1 of that precision, and the Solver's
precise self-correction (its own switches, 0.47-0.79) already happens without a flag.

## Method and reproduce

- **Files read.** Full hashes are in `report.json` `inputs` (43 entries): the phase artefact and sealed scores of each
  of the 16 pools, the boundary snapshot, both facet files, both query-vector files, both agreement tables, the
  exemplar pool and three baseline configs.
- **Master status observed at start.** `git status --porcelain` on master was empty (clean) at `589d70bfc`. During the
  read, master advanced to `be18200c7` (the `fable/solverdecision` merge by another agent). This branch was
  fast-forwarded to it before any edit.

```bash
PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=4 python scripts/analysis/slurp_reviewer_revision_instrument.py \
    --data-root "$SPEECHRL_DATA_DIR" --lock /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=4 python scripts/analysis/slurp_reviewer_revision_instrument.py --check \
    --data-root "$SPEECHRL_DATA_DIR" --lock /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider tests/unit/test_slurp_reviewer_revision_instrument.py
```
