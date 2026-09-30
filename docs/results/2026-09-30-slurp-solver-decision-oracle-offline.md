# SLURP Solver intent-decision oracle: the decision is readable (AUC about 0.78), the conversion is not measured high enough to pay for it (DESCRIPTIVE, offline)

Date: 2026-09-30. Read id `SAEA-SLURP-SOLVER-DECISION-ORACLE-OFFLINE-V1`, recipe
`slurp-solver-decision-oracle-offline-v1`. Written by Claude Opus 5.5 (analysis agent, coordinator's brief, Fable 5.1)
in worktree `fable/solverdecision` (base master `a2f6baab6`). The design that uses these numbers is
`docs/superpowers/specs/2026-09-30-solver-intent-decision-mechanism-design.md`.

**Status: DESCRIPTIVE.** Development numbers on TRAIN Fold A and TRAIN Fold B, both construction rosters (owner
decisions 28 and 86). No test, generalisation or superiority claim. The verdict word belongs to the coordinator
(decision 139).

**Contacts: zero of every kind.** No model, server, tokenizer, encoder, embedder, GPU, network or paid-API contact.
No official-scorer subprocess: the sealed per-row column scores were read only to cross-check the parsed picks.
`core.flight.cli` and `lease_cli` were not invoked. Gold entered only offline, through the governed TRAIN loader
`data.slurp.load_slurp_split`. No utterance text, note text, exemplar body, gold value or model output is printed or
persisted: ids, counts, rates, AUCs, pp and hashes only.

**Driver and outputs.**

- Driver: `scripts/analysis/slurp_solver_decision_oracle.py`, sha256
  `feed18d1f2d8a508b1f3d18a68beb18525b2904aa25e956f14e1b9c7b0d4d43a`.
- Unit test on fakes: `tests/unit/test_slurp_solver_decision_oracle.py` (10 passed).
- Machine outputs: `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-SOLVER-DECISION-ORACLE-OFFLINE-V1/` (`report.json`,
  `tables.md`, `content-sha256.json`). Every number below is quoted from `report.json` unless marked "derived".
- `--check` re-derived both files IDENTICAL apart from `generated_at`. Content hashes (with `generated_at` removed):
  `report.json` `853c97f8bc64bcfebe4d16192f6a37e2bec218b553f3f0052a28c0e846abb2d5`, `tables.md`
  `075f3b7d51fb6741ccd729a241565f0bec60f1c36ccc9c72a58e2afe18963ad3`. Wall time 2.7 min, peak memory 1.1 GB.

## 0. Pools, definitions and custody

| pool | fold | Solver pick read from | note read from | twin |
| --- | --- | --- | --- | --- |
| AGREE `SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1` | A | first `phase:solver` state (`phases.json` `783299f1...`) | sealed Perception state | wave A/A `SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1` first Solver: a CROSS-flight replicate with its own Perception note (equal note on 752 of 1,080 rows) |
| COMP-1b `SAEA-SLURP-STAGE3-COMP1B-FOLD-A-V1` | A | first Solver state (`079bcf18...`) | sealed Perception state | none |
| W-SV-1 `SAEA-SLURP-STAGE3-WSV1-FOLD-A-V1` | A | `arm-a-base` first-visit column | delivered Perception state | `t-twin` column: same note, same supply |
| W4-SV `SAEA-SLURP-STAGE3-W4SV-FOLD-A-V1` | A | `arm-a-agree` first-visit column | delivered Perception state | `t-twin` column: same note, same supply |
| P-SV-1 / P-SV-2 / P-SV-3 (`-PSV1/2/3-FOLD-B-V1`) | B | `arm-a-agree` first-visit column (level 2) | branch A's sealed note (`branch_candidates`) | `t-twin`: its own Perception note and its own Solver |

- **Decision population.** Rows whose note lists two or more candidates and whose Solver KEPT note rank 1.
- **Positive** (the oracle's flippable row): gold at note rank 2 or 3. **Negative:** gold at note rank 1 (a
  re-decision can only cost). **Cost row:** gold off the note (a re-decision over the note cannot reach it).
- **Ceiling:** every row with gold at note rank 2 or 3 and a wrong Solver pick (including the few picks that left
  rank 1 for another wrong intent).
- **Signals** (section 2) are computed per row. The boundary margin is recomputed through the production
  constructor from the pinned vectors and agreement table. The recomputed depth-8 block equals the sealed block on
  **1,080 / 1,080** rows in every pool [`checks`].
- **Custody checks.** Parsed picks agree with the sealed official intent flag on 1,080 / 1,080 rows for every column
  arm (A and T of W-SV-1, W4-SV, P-SV-1/2/3). The W-SV A column equals the flight's own first Solver state on 1,055
  (W-SV-1) and 1,053 (W4-SV) rows; the column, not the phase state, is used. Exemplar width is 20 on 1,080 / 1,080
  rows; 0 exemplar keys are unresolved.
- **The agreement table and the delivered exemplars carry the same decision.** Among the note's candidates, the
  agreement-share argmax equals the exemplar-vote argmax on **1,080 / 1,080** rows in every pool
  [`*_note_rows_agreement_argmax_equals_vote_argmax`]. The Solver already sees those 20 exemplars with their labels.

## 1. The oracle ceiling and the decision set

[`pools.<pool>.ceiling_*`, `decision_set`]

| pool | ceiling rows | ceiling pp | of which the Solver kept r1 | decision rows (pos + neg) | positives | negatives | cost rows | b = pos / (decision + cost) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| AGREE | 68 | 6.30 | 59 | 900 | 59 | 841 | 69 | 0.061 |
| COMP-1b | 75 | 6.94 | 67 | 925 | 67 | 858 | 64 | 0.068 |
| W-SV-1 | 65 | 6.02 | 63 | 910 | 63 | 847 | 79 | 0.064 |
| W4-SV | 62 | 5.74 | 61 | 915 | 61 | 854 | 69 | 0.062 |
| P-SV-1 | 81 | 7.50 | 78 | 914 | 78 | 836 | 78 | 0.079 |
| P-SV-2 | 80 | 7.41 | 74 | 892 | 74 | 818 | 85 | 0.076 |
| P-SV-3 | 82 | 7.59 | 79 | 886 | 79 | 807 | 77 | 0.082 |

**A perfect decision with perfect conversion would flip 62-82 rows (5.7-7.6 pp).** That is the whole second blank.

**The Solver already leaves rank 1 on its own, with high precision and low recall** (derived from
`gold_rank_x_pick`: picks of note rank 2 or 3, right / all):

| pool | spontaneous switches right / all | precision | recall over all rank-2/3 gold rows |
| --- | --- | ---: | ---: |
| AGREE | 20 / 27 | 0.74 | 20 / 88 = 0.23 |
| COMP-1b | 16 / 24 | 0.67 | 16 / 91 = 0.18 |
| W-SV-1 | 21 / 30 | 0.70 | 21 / 86 = 0.24 |
| W4-SV | 24 / 38 | 0.63 | 24 / 86 = 0.28 |
| P-SV-1 | 18 / 38 | 0.47 | 18 / 99 = 0.18 |
| P-SV-2 | 21 / 40 | 0.53 | 21 / 101 = 0.21 |
| P-SV-3 | 27 / 51 | 0.53 | 27 / 109 = 0.25 |

## 2. Which signals separate positives from negatives

AUC = P(signal of a positive > signal of a negative), ties one half; row-bootstrap CI95, 10,000 draws, seed
20260930. Below 0.5 means positives carry the SMALLER value. [`pools.<pool>.auc`]

| signal (model-visible today?) | AGREE | COMP-1b | W-SV-1 | W4-SV | P-SV-1 | P-SV-2 | P-SV-3 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| note candidate count (yes) | 0.54 [0.48, 0.59] | 0.54 [0.49, 0.58] | 0.52 [0.46, 0.57] | 0.50 [0.45, 0.56] | 0.47 [0.42, 0.53] | 0.45 [0.39, 0.51] | 0.46 [0.40, 0.51] |
| **boundary margin s(r1) − s(r2)** (no: order only) | **0.20** [0.16, 0.24] | **0.24** [0.20, 0.29] | **0.22** [0.17, 0.27] | **0.21** [0.17, 0.25] | **0.22** [0.18, 0.26] | **0.23** [0.18, 0.27] | **0.23** [0.18, 0.27] |
| note r1 is not block rank 1 (yes) | 0.60 [0.54, 0.66] | 0.56 [0.51, 0.62] | 0.57 [0.51, 0.62] | 0.55 [0.50, 0.61] | 0.61 [0.55, 0.66] | 0.57 [0.52, 0.62] | 0.59 [0.54, 0.64] |
| **agreement share r1 − r2** (no: pinned table) | **0.21** [0.16, 0.25] | **0.24** [0.20, 0.29] | **0.23** [0.18, 0.28] | **0.22** [0.18, 0.27] | **0.23** [0.19, 0.28] | **0.24** [0.19, 0.29] | **0.24** [0.20, 0.29] |
| **exemplar votes r1 − r2** (yes) | **0.21** [0.16, 0.26] | **0.25** [0.20, 0.29] | **0.23** [0.19, 0.28] | **0.22** [0.18, 0.27] | **0.23** [0.19, 0.28] | **0.24** [0.20, 0.29] | **0.24** [0.20, 0.29] |
| exemplar votes for r1 (yes) | 0.21 [0.16, 0.25] | 0.24 [0.20, 0.29] | 0.24 [0.19, 0.29] | 0.22 [0.17, 0.27] | 0.23 [0.19, 0.28] | 0.25 [0.20, 0.30] | 0.24 [0.19, 0.29] |
| exemplar votes for r2 (yes) | 0.73 [0.68, 0.78] | 0.72 [0.67, 0.77] | 0.72 [0.67, 0.77] | 0.72 [0.66, 0.77] | 0.70 [0.64, 0.75] | 0.71 [0.66, 0.77] | 0.70 [0.64, 0.75] |
| exemplar winner is r2 (yes) | 0.56 [0.51, 0.61] | 0.53 [0.49, 0.57] | 0.53 [0.49, 0.58] | 0.52 [0.48, 0.57] | 0.55 [0.51, 0.60] | 0.54 [0.50, 0.59] | 0.55 [0.51, 0.59] |
| r1 and r2 share the scenario (yes) | 0.47 [0.41, 0.54] | 0.45 [0.39, 0.51] | 0.45 [0.39, 0.52] | 0.46 [0.40, 0.52] | 0.46 [0.40, 0.52] | 0.48 [0.42, 0.54] | 0.46 [0.40, 0.51] |
| r1 scenario, cross-fitted rate (yes) | 0.57 [0.49, 0.66] | 0.60 [0.53, 0.67] | 0.55 [0.48, 0.62] | 0.54 [0.47, 0.62] | 0.65 [0.59, 0.72] | 0.64 [0.57, 0.70] | 0.59 [0.52, 0.65] |
| entity-free share of the 20 exemplars (yes) | 0.59 [0.51, 0.66] | 0.53 [0.46, 0.60] | 0.54 [0.46, 0.61] | 0.54 [0.46, 0.61] | 0.55 [0.48, 0.61] | 0.53 [0.46, 0.60] | 0.52 [0.46, 0.59] |
| twin picked differently (no: second sample) | 0.54 [0.51, 0.59] | -- | 0.50 [0.50, 0.50] | 0.51 [0.50, 0.53] | 0.50 [0.50, 0.50] | 0.50 [0.50, 0.50] | 0.50 [0.50, 0.50] |

- **One family of signals separates, and it is one signal.** The boundary margin, the agreement difference and the
  exemplar-vote difference all read 0.20-0.25 (inverted 0.75-0.80), with overlapping CIs in every pool. The agreement
  and vote argmaxes coincide on every row (section 0).
- **Nothing else is strong.** Note size, shared scenario and the entity-free share sit at 0.45-0.59 with CIs touching
  0.5. "Perception re-ranked the block" reads 0.55-0.61; the r1 scenario 0.54-0.65.
- **The same-flight twins are byte-level repeats of the pick.** The W-SV Solver twins disagree with A on 0 and 2 of
  1,080 rows; the P-SV Perception+Solver twins on 0, 1 and 2. Only the cross-flight replicate (AGREE vs wave A/A)
  disagrees on 28 rows: 10.2 % of positives against 1.5 % of negatives [`binary_rates.twin_dis`].

## 3. The best two-signal rule under cross-fit

Halves by sha256(utterance id). On each half, every pair of signals is fitted (logistic, standardised) and ranked by
its in-half AUC; the best pair's model is applied to the other half. Operating points: the in-half F1 threshold and
in-half call-rate thresholds (5 / 10 / 20 % of decision rows), applied out of half. "Called" includes cost rows (gold
off the note), because a call on them costs a contact and cannot help. [`rule_all_signals`, `rule_model_visible_signals`]

| pool | pairs chosen (half 0 / half 1) | out-of-half AUC | 10 % call rate: called / TP / FP / cost / precision | 20 %: called / TP / FP / precision |
| --- | --- | ---: | --- | --- |
| AGREE | note count + margin / r1 votes + r1 scenario | 0.67 | 73 / 13 / 45 / 15 / 0.18 | 151 / 22 / 95 / 0.15 |
| COMP-1b | note count + r1 votes / r1 votes + r1 scenario | 0.70 | 83 / 12 / 49 / 22 / 0.14 | 209 / 29 / 142 / 0.14 |
| W-SV-1 | margin + re-ranked / margin + agreement | 0.76 | 97 / 18 / 60 / 19 / 0.19 | 195 / 29 / 128 / 0.15 |
| W4-SV | re-ranked + r1 votes / margin + winner is r2 | 0.78 | 129 / 19 / 82 / 28 / 0.15 | 232 / 35 / 151 / 0.15 |
| P-SV-1 | margin + r1 scenario (both halves) | 0.80 | 111 / 24 / 65 / 22 / 0.22 | 218 / 42 / 138 / 0.19 |
| P-SV-2 | margin + agreement / margin + r1 scenario | 0.76 | 118 / 25 / 71 / 22 / 0.21 | 203 / 32 / 129 / 0.16 |
| P-SV-3 | margin + agreement / margin + r1 scenario | 0.77 | 125 / 27 / 78 / 20 / 0.22 | 228 / 44 / 144 / 0.19 |

The model-visible-only rule (without the margin, the agreement table and the twin) is within 0.02-0.06 AUC of it:
0.69 / 0.70 / 0.75 / 0.72 / 0.80 / 0.74 / 0.78. At the best point, a 5 % call rate on P-SV-2, precision is 0.29
including cost rows. **The best offline rule reaches 2.1-3.9 times the base rate at its best call rate, never above 0.3 precision.**

**What the evidence pack would say if followed.** On the rows where the exemplar-vote (equivalently, agreement)
favourite among the note's candidates is not the Solver's kept r1, following the evidence would move gold onto
10-13 rows and take it off 73-85 [`evidence_follow_counterfactual`]:

| pool | evidence disagrees with r1 | evidence pick is gold | r1 is gold | neither | net rows if followed |
| --- | ---: | ---: | ---: | ---: | ---: |
| AGREE | 105 | 12 | 73 | 20 | −61 |
| COMP-1b | 105 | 11 | 79 | 15 | −68 |
| W-SV-1 | 110 | 10 | 76 | 24 | −66 |
| W4-SV | 115 | 11 | 82 | 22 | −71 |
| P-SV-1 | 112 | 13 | 85 | 14 | −72 |
| P-SV-2 | 102 | 12 | 79 | 11 | −67 |
| P-SV-3 | 113 | 11 | 81 | 21 | −70 |

**The Solver is already right to overrule its exemplars about seven times out of eight when they disagree.** A pack
of votes and exemplar counts re-presents evidence the Solver has already weighed. It is informative about WHERE to
look (the AUCs), but not about WHICH candidate is right (this table).

## 4. Conversion: the binding term

A decision is worth only what the re-decision converts. Three measured anchors exist; none was measured on this read's
exact rows [`anchors`, `pools.<pool>.anchored`]:

| anchor | conversion on positives | harm on negatives | source |
| --- | ---: | ---: | --- |
| same-flight Solver twin (W-SV-1 + W4-SV pooled) | 0.008 (1 / 124) | 0.0006 (1 / 1,701) | this read |
| cross-flight replicate (AGREE vs wave A/A; own note) | 0.085 (5 / 59) | 0.016 (13 / 841) | this read |
| Reviewer-routed second Solver contact (REV-TFRL-1 arm) | 0.185 (10 / 54 revised INT-SHORTLIST visits) | 0.049 (8 / 164 revised CORRECT visits) | `2026-09-28-slurp-revtfrl-1-fold-a-read.md` section 4, quoted |

The 0.65 pp same-flight intent floor at n = 1,080 is 7.02 rows; the 2.5 pp cross-flight bar is 27 rows.

| pool | perfect decision at 0.085 / 0.185: rows (pp) | best rule at 0.185 / 0.049, best call rate: rows | precision needed at 0.185 / 0.049 for 7.02 rows, recall 0.5 / 0.7 / 1.0 |
| --- | --- | --- | --- |
| AGREE | 5.76 (0.53) / 12.59 (1.17) | +0.63 (5 %) | unreachable / 0.56 / 0.37 |
| COMP-1b | 6.35 (0.59) / 13.89 (1.29) | −0.17 (10 %) | unreachable / 0.49 / 0.35 |
| W-SV-1 | 5.51 (0.51) / 12.04 (1.12) | +0.41 (10 %) | unreachable / 0.61 / 0.39 |
| W4-SV | 5.25 (0.49) / 11.48 (1.06) | −0.19 (5 %) | unreachable / 0.68 / 0.40 |
| P-SV-1 | 6.86 (0.64) / 15.00 (1.39) | +1.27 (10 %) | 0.81 / 0.44 / 0.33 |
| P-SV-2 | 6.78 (0.63) / 14.81 (1.37) | +1.32 (5 %) | 0.83 / 0.45 / 0.33 |
| P-SV-3 | 6.95 (0.64) / 15.19 (1.41) | +1.20 (10 %) | 0.78 / 0.44 / 0.33 |

- **At the twin conversions, even a perfect decision cannot reach the floor** (at most 6.95 rows at 0.085).
- **At the REV-TFRL-1 conversion, a perfect decision clears it (11.5-15.2 rows), but the best offline rule nets at
  most +1.32 rows (0.12 pp).** The floor needs a decision precision of about 0.44-0.68 at recall 0.7, or 0.33-0.40 at
  full recall. The offline rules reach 0.14-0.22 at a 10 % call rate.
- **Only one measured decision-maker reaches the needed precision: the Solver's own spontaneous switches**, at 0.47-0.74
  (section 1), but at recall 0.18-0.28.

## What this note does not claim

- It does not measure a re-decision's conversion on these rows. The three anchors are borrowed. REV-TFRL-1's rows are
  INT-SHORTLIST visits under a contrastive Reviewer form, not this oracle's positives, and its 10 / 54 carries a wide
  interval.
- It does not predict what a model-declared confidence would score. No sealed output carries one.
- The target encoding of the r1 scenario and the pair selection are cross-fitted. In-half AUCs are in `report.json`
  and are selected numbers.
- The evidence-follow table is a counterfactual upper bound. Directive 206 bars a system-applied swap.
- Every number is a TRAIN development number. Nothing is nominated or admitted.

## Method and reproduce

- **Files read.** Full hashes in `report.json` `inputs` (42 entries): the phases, first-visit outputs, column scores
  and branch receipts of the seven pools, the wave A/A phases, the boundary snapshot `5520b844...`, both facet files,
  both query-vector files, both agreement tables, the exemplar pool `fcb5506c...`, and three baseline configs.
- **Picks.** Parsed in memory with `reproduction.slurp_scoring.parse_slu_response`; only the intent pick is kept.
- **Notes.** Phase notes are deduplicated in order; branch notes come through `slurp_perception_branch_read.branch_candidates`.

```bash
PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=4 python scripts/analysis/slurp_solver_decision_oracle.py \
    --data-root "$SPEECHRL_DATA_DIR" --lock /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=4 python scripts/analysis/slurp_solver_decision_oracle.py --check \
    --data-root "$SPEECHRL_DATA_DIR" --lock /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
```
