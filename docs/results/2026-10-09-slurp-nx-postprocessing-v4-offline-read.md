# R0.4 / E4 post-processing v4, offline: A2 selects five deterministic rules for +0.98 pp [+0.21, +1.74]; the single Fold-A read gives +1.67 [+0.81, +2.50], so v4 is a LOCK CANDIDATE. Over v4, the multi-sample support filter adds +0.84 to +1.11 on ROLL-3 and is not resolved on ROLL-1 (DESCRIPTIVE)

Read 2026-10-09 by the analysis agent (Claude Opus 5.5) for the NX programme
(`docs/readiness/2026-10-09-slurp-nx-node-extreme-programme-v1.md`, round R0.4 / deliverable E4). Worktree
`/home/chao/saea-worktrees/fable-nx-postproc`, branch `fable/nx-postproc`, based on master `e5adeb3b2`.

The driver is `scripts/analysis/slurp_nx_postproc_v4_search.py` (sha256
`31ea97e1faf0403be2f9bfdcad31be7f1390fd4c2227d9039192849dfc2da7d5`). All outputs are under
`$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-NX-POSTPROC-V4-SEARCH-V1/`.

**Contacts.**

- None of the following: model, server, tokenizer, encoder, embedder, network, GPU or paid API.
- Two registered-scorer-on-copy runs, both CPU and both identity proofs: `slurp-slu-official` on the A2 v4 column
  and `slurp-slu-official-train` on the Fold-A v4 column. Each reproduced the in-process number to 1e-6.

**Gold and text discipline.**

- Gold entered offline only, on the scoring side, through the governed loader `data.slurp.load_slurp_split`
  (`devel`, `train`). The test split was not read.
- No utterance text, transcript, gold value, filler or model output is printed or persisted in the reports or in
  this note. The two derived copies sit under the analysis root because the scorer needs them; they never enter the
  repository.

**Status: DESCRIPTIVE.** These are development numbers (owner decisions 28 and 86), never a test claim. Nothing is
admitted by this note: the lock is the owner's decision.

## 0. Answer in five lines

1. **Part A (single sample, temperature 0).** The best rule set on A2 adds **+0.98 pp official pooled SLU-F1
   [+0.21, +1.74]** to the sealed COMP-1b delivered column, which already carries normaliser v3. The rule set is
   v3, then determiner strip, then o'clock strip, then the scope rule, then type-by-intent support (< 1 %), then
   explicit-empty (< 10 %). Intent changes on 0 rows.
2. **The single Fold-A read** of exactly that ordered list gives **+1.67 pp [+0.81, +2.50]**. The CI95 lower bound
   is above 0, so **v4 is a lock candidate**. The registered scorer reproduces the column at 65.279373, against
   63.6095 delivered.
3. **Value-in-supply is a strong signal but a harmful rule.** P(exact | in supply) is 0.76 against 0.32 when not in
   supply. Dropping the not-in-supply entities still costs -7.9 pp, because 162 exact entities are not in the
   supply.
4. **Part B, support filter over v4 (same samples).** On ROLL-3 (DEV, PLAN policy) it adds +0.84 [+0.19, +1.49] at
   2-of-3 and +1.11 [+0.33, +1.91] at 3-of-5. On ROLL-1 (R01C) it adds +0.42 [-0.32, +1.16] at 2-of-3 and +0.48
   [-0.41, +1.37] at 3-of-5, which is not resolved. 3-of-3 harms in both pools.
5. **Cost.** On review-off, k samples add 100(k-1) Solver calls per 100 rows. Over v4 that buys 0.12 to 0.42 pp per
   100 extra calls. The Reviewer loop costs +410 calls for 0 raw repairs. v4 itself is free.

## 1. Inputs and identities

| item | value |
| --- | --- |
| A2 (select) | `SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-V1` / `attempt-slurp-native-stage3-comp1b-dev2000-added-generation-v1`, DEV-2000-ADDED, 1,000 rows / 913 utterances, scorer `slurp-slu-official`; official SLU-F1 65.9327, intent 81.50 |
| Fold A (confirm) | `SAEA-SLURP-STAGE3-COMP1B-FOLD-A-V1` / `attempt-slurp-native-stage3-comp1b-fold-a-generation-v1`, 1,080 rows / 1,080 utterances, scorer `slurp-slu-official-train`; official SLU-F1 63.6095, intent 85.6481 |
| ROLL-1 | `SAEA-SLURP-STAGE3-ROLLOUT-R01-V1` (R01C, 625 rows), copies and scores in `analysis/SAEA-SLURP-STAGE3-ROLLOUT-R01-SCORE-V1`, scorer `slurp-slu-official-projected-v3-train` |
| ROLL-3 | `SAEA-SLURP-STAGE3-ROLL-3-DEV2000-ADDED-V1` (DEV-2000-ADDED, 1,000 rows), copies and scores in `analysis/SAEA-SLURP-STAGE3-ROLL-3-DEV2000-ADDED-READ-V1`, scorer `slurp-slu-official-projected-v3` |
| TRAIN statistics | one pool only: `size-pool-annotated-exemplars-minus-r01` (content `6eaa03ae...`), the R5 pool behind the scope-rule table: TRAIN minus Fold A, Fold B, R01 and R01C, 8,554 exemplars, 59 intents, 360 (intent, type) bindings. Disjointness is re-proved at run time: 0 utterances shared with the Fold A and R01C rosters |
| scope table | `prepared/SAEA-SLURP-SCOPE-RULE-TABLE-V1/table-v1.json` `fcff0c42...` (the registered stage's pin) |
| supply (Part A) | the row's rendered exemplars and supplied slot-contract cards from `<run>.phases.json` (A2 `4dc4cb80...`), resolved through the M1 snapshot `4c498dc0...` and slot-contracts-v2 `a48ed83e...`; 0 unresolved exemplar keys |
| estimator | paired whole-utterance cluster bootstrap, 10,000 draws, seed 20260915, numpy `default_rng`, percentile CI95. It is the aggregation read's estimator with the cluster lifted from row to SLURP utterance id. Part B on R01C (625 distinct utterances) is also run row-clustered as a control |

**Reproduction gates.**

- **A2 and Fold A.** All 1,000 and 1,080 delivered rows reproduce their sealed per-sample official fields exactly
  (9 count fields and intent exact) through `reproduction.slurp_scoring.score_slu`.
- **ROLL-1 and ROLL-3.** All 5 x 625 and 5 x 1,000 sample-rows reproduce their sealed projected-v3 per-sample
  scores. Each sample text goes through the registered `saea-deliver-normalise-v3`, then the parser.
- **Precedent controls.** The scope rule alone reads +0.4899, the same point as the COMP-2 stage-column read. The
  ROLL-1 support filter at 3-of-5 reads 59.2799 / +1.3993 with row-cluster CI95 [+0.5499, +2.2925], which is the
  published +1.40 [+0.55, +2.29] to the digit.

## 2. Part A on A2: every rule alone

Rules are applied after the sealed v3 column. Deltas are against that column. "Dropped" counts are split against
gold, offline, into spurious, exact and other matched.

| rule | what it does (TRAIN source = R5 pool) | dSLU pp | CI95 | rows edited | dropped (spur / exact / other) | fillers changed | row saves / harms |
| --- | --- | ---: | --- | ---: | --- | ---: | --- |
| fx-article | strips a leading determiner where SLURP annotation excludes it. That is 73 (type, word) pairs where the span includes a word that precedes it in the utterance in < 10 % of >= 10 cases | +0.13 | [-0.00, +0.29] | 18 | 0 | 18 | 6 / 3 |
| fx-oclock | strips a trailing "o'clock" from a time filler (TRAIN: 0 included / 5 excluded) | +0.03 | [-0.04, +0.14] | 2 | 0 | 2 | 1 / 1 |
| fx-month-ordinal | changes month + cardinal day to the ordinal (TRAIN: 44 ordinal / 34 cardinal) | **-0.08** | **[-0.16, -0.02]** | 5 | 0 | 5 | 0 / 5 |
| scope | `saea-deliver-scope-rule-v1` | +0.49 | [-0.04, +1.04] | 61 | 37 / 5 / 22 | 0 | 29 / 25 |
| ti0 | drops an entity whose type never occurs under the delivered intent | +0.30 | [-0.14, +0.73] | 35 | 22 / 7 / 7 | 0 | 18 / 9 |
| ti1 | drops an entity whose type occurs in < 1 % of the intent's exemplars | +0.31 | [-0.21, +0.84] | 50 | 30 / 11 / 10 | 0 | 26 / 14 |
| vs-type | drops an entity whose (type, value) is not printed in the supplied exemplars | **-7.92** | **[-10.29, -5.59]** | 428 | 160 / 162 / 179 | 0 | 116 / 254 |
| vs-any | drops an entity whose value is printed nowhere in the supply | **-8.15** | **[-10.35, -6.03]** | 380 | 128 / 147 / 156 | 0 | 92 / 237 |
| ee5 | empties a row whose intent carries entities in < 5 % of TRAIN (2 intents) | -0.03 | [-0.10, 0.00] | 1 | 0 / 0 / 1 | 0 | 0 / 1 |
| ee10 | the same at < 10 % (4 intents) | +0.08 | [-0.04, +0.21] | 5 | 3 / 0 / 2 | 0 | 3 / 1 |

**Explicit-empty (owner decision 199).** No rule ever adds an entity: a delivered empty list stays empty. The
"drop on a < 5 % intent" rule the brief names fires on 1 row of A2 and costs -0.03. The < 10 % variant fires on 5
rows and gains +0.08.

**Type-by-intent (the A1 harm).** The A1 audit (`2026-09-17-slurp-a1-use-projection-audit-v1.md`) rejected the
support filter on the B-era arm: DEV1000 went negative, and cooking and recommendation lost. On COMP-1b A2 it is
positive alone but not resolved. Inside the combination its marginal is +0.26 pp. The Fold-A read below is the
guard: cooking -0.61 and recommendation +1.58 there.

### 2a. The value-in-supply signal against gold (A2, 1,088 delivered entities)

| signal | in supply | not in supply | P(exact given in) | P(exact given not in) | exact entities covered by "in" | spurious entities that are "not in" | precision of a not-in drop (share spurious) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| (type, value) printed in the exemplars | 587 | 501 | 0.758 | 0.323 | 0.733 | 0.643 | 0.319 |
| value printed anywhere (exemplars, any type, or a card) | 657 | 431 | 0.700 | 0.341 | 0.758 | 0.514 | 0.297 |

The signal separates well, by more than 2x on P(exact). It is still not a drop rule. About a quarter of the exact
entities (162 of 607) are values the supply never printed. A drop removes about 2 non-spurious entities for every
spurious one. It is therefore a candidate KEEP signal, for example to protect an entity from another drop rule, and
an R1 Solver template input ("value in supply, not used"). It is not a deletion rule.

## 3. Part A on A2: the combination search and the selection

**The grid.** It holds 431 non-empty combinations: three fx toggles x scope x {-, ti0, ti1} x {-, vs-type, vs-any} x
{-, ee5, ee10}. Each member is applied in the fixed order fx-article, fx-oclock, fx-month-ordinal, scope, ti, vs,
ee.

**The selection rule.** It was declared in the driver before any number was read:

1. take the maximum A2 point delta (ties go to fewer rules);
2. remove passengers, meaning any member whose removal does not lower the point, repeatedly.

**What the rule picked.** The argmax was fx-article + fx-oclock + scope + ti1 + ee10. Pruning removed nothing.

| rank | combination | dSLU pp | CI95 |
| ---: | --- | ---: | --- |
| **1 (selected)** | **fx-article, fx-oclock, scope, ti1, ee10** | **+0.98** | **[+0.21, +1.74]** |
| 2 | fx-article, scope, ti1, ee10 | +0.94 | [+0.18, +1.72] |
| 3 | fx-article, fx-oclock, scope, ti0, ee10 | +0.93 | [+0.22, +1.64] |
| 4 | fx-article, fx-oclock, scope, ti1 | +0.92 | [+0.16, +1.68] |
| 6 | fx-article, scope, ti0, ee10 | +0.89 | [+0.18, +1.60] |
| 8 | fx-article, scope, ti1 | +0.88 | [+0.11, +1.65] |
| -- | scope + ti1 | +0.77 | [+0.01, +1.52] |
| -- | fx-article + fx-oclock + scope | +0.64 | [+0.08, +1.19] |
| -- | scope alone (the COMP-2 stage, re-read here) | +0.49 | [-0.04, +1.04] |

**Selected column on A2.**

| quantity | value |
| --- | --- |
| official SLU-F1 | 65.9327 -> **66.9098** (registered scorer on the copy: 66.909793, copy `2104239a...`) |
| span-F1 | +1.98 pp |
| intent | 81.50 -> 81.50, 0 rows changed |
| edits | 124 rows edited, 20 fillers rewritten, 111 entities dropped (64 spurious / 15 exact / 32 other) |
| per-row | saves 60 / harms 42 |
| member marginals (point with all five minus point without that member) | scope +0.43, ti1 +0.26, fx-article +0.11, ee10 +0.06, fx-oclock +0.04 |

**Per scenario (A2, natural mixture +0.98, equal-scenario +0.10).**

| scenario | rows | rows edited | delta pp |
| --- | ---: | ---: | ---: |
| calendar | 221 | 26 | +0.38 |
| play | 203 | 18 | +1.86 |
| qa | 157 | 22 | +0.32 |
| email | 96 | 11 | -0.62 |
| weather | 65 | 5 | +2.00 |
| general | 62 | 16 | +2.34 |
| iot | 57 | 5 | -1.84 |
| lists | 52 | 6 | +1.51 |
| transport | 48 | 2 | +1.15 |
| news | 20 | 2 | -0.16 |
| datetime | 9 | 2 | -5.58 |
| recommendation | 6 | 0 | 0.00 |
| social | 4 | 0 | 0.00 |

**Winner's curse.** 431 combinations were read on one roster, so the selected point is optimistic. That is why the
lock decision rests on the single Fold-A read, not on A2.

## 4. The single Fold-A confirmation

The command was run once and the driver refuses a second run:
`--confirm --rules fx-article,fx-oclock,scope,ti1,ee10 --score-copy`.

| quantity | value |
| --- | --- |
| **dSLU (official pooled)** | **+1.67 pp, CI95 [+0.81, +2.50]** (1,080 utterance clusters) |
| official SLU-F1 | 63.6095 -> 65.2794 (registered `slurp-slu-official-train` on the copy: 65.279373, copy `68de6975...`) |
| span-F1 | +1.90 pp |
| intent | 85.6481 -> 85.6481, 0 rows changed |
| edits | 130 rows edited, 9 fillers rewritten, 129 entities dropped (83 spurious / 20 exact / 26 other) |
| per-row | saves 77 / harms 34 |
| **lock rule (Fold-A CI95 lower bound > 0)** | **MET: v4 is a lock candidate** |

**Per scenario (Fold A, 60 rows each, natural +1.67, equal-scenario +0.93).**

- **Gains (13):** alarm +6.15, lists +5.74, general +4.60, music +3.30, iot +3.24, qa +3.07, play +2.39,
  news +2.30, calendar +1.68, recommendation +1.58, weather +1.22, datetime +0.79, transport +0.73.
- **Losses (5):** **audio -17.47** (9 rows edited), social -0.84, cooking -0.61, takeaway -0.60, email -0.48.

**Honest scope of the confirmation.**

- **Prior exposure of Fold A.** Fold A is not virgin to these rules. The scope rule's Fold-A rehearsal (+1.35,
  COMP-2 rehearsal) and the COMP-1b Fold-A reads already exposed this roster. What is new here is the five-rule
  combination, read once.
- **The audio loss.** The audio scenario loses -17.5 pp on its 60 rows. It is the one large per-stratum loss and
  must be read before the owner locks.
- **Equal-scenario size.** The A2 equal-scenario delta is only +0.10, so the pooled gain is carried by the large
  scenarios.

**Prediction check.** The programme predicted +1.0 to +1.4 for R0.4. A2 lands at +0.98 and Fold A at +1.67, so no
support filter is needed in Part A to reach the predicted range.

## 5. Part B: the multi-sample support filter, alone and over v4

**Pool policies.** ROLL-1 is cell ROLL-1's grouped v2.0 PLAN Solver on R01C. ROLL-3 is the same grouped PLAN form on
DEV-2000-ADDED. **Neither is COMP-1b**, and the two are never pooled.

**How the samples were drawn.** All five samples per row are temperature 0.7, with no greedy sample. The reference
is the precedent's R0-mean-single: the mean count matrix of the k single-sample arms, each projected by v3.

**The filter (R3).** Take the R1 medoid of the k samples. Drop each medoid entity that is supported by fewer than s
of the k samples, where support means the same type at character F1 >= 0.8. k = 3 uses samples 0..2.

**How to read the "+v4" columns.** "+v4" applies the selected Part-A list after the filter. "filter+v4 vs single+v4"
is the value of sampling once v4 is in place; it is the number that matters for the cost decision.

| pool | k | arm | vs single | CI95 | entities dropped by the filter | filter+v4 vs single+v4 | CI95 | filter+v4 vs single |
| --- | ---: | --- | ---: | --- | ---: | ---: | --- | ---: |
| ROLL-3 (DEV) | 1..k | single + v4 | +1.08 (k=3) / +1.07 (k=5) | [+0.26, +1.90] / [+0.27, +1.87] | -- | -- | -- | -- |
| ROLL-3 | 3 | R1 medoid | +0.31 | [-0.27, +0.92] | -- | -- | -- | -- |
| ROLL-3 | 3 | support 2-of-3 | +1.46 | [+0.83, +2.08] | 90 | **+0.84** | **[+0.19, +1.49]** | +1.92 [+0.89, +2.95] |
| ROLL-3 | 3 | support 3-of-3 | -0.12 | [-1.29, +1.01] | 299 | -1.33 | [-2.46, -0.25] | -0.25 |
| ROLL-3 | 5 | R1 medoid | +0.21 | [-0.53, +0.97] | -- | -- | -- | -- |
| ROLL-3 | 5 | support 2-of-5 | +1.29 | [+0.59, +2.02] | 55 | +0.83 | [+0.07, +1.59] | +1.90 [+0.78, +3.02] |
| ROLL-3 | 5 | **support 3-of-5** | **+2.06** | **[+1.27, +2.88]** | 158 | **+1.11** | **[+0.33, +1.91]** | **+2.18 [+1.00, +3.38]** |
| ROLL-3 | 5 | support 4-of-5 | +1.22 | [+0.17, +2.30] | 288 | -0.02 | [-1.01, +0.97] | +1.05 |
| ROLL-1 (R01C) | 1..k | single + v4 | +1.49 (k=3) / +1.55 (k=5) | [+0.34, +2.63] / [+0.45, +2.65] | -- | -- | -- | -- |
| ROLL-1 | 3 | R1 medoid | +0.19 | [-0.36, +0.76] | -- | -- | -- | -- |
| ROLL-1 | 3 | support 2-of-3 | +0.97 | [+0.29, +1.69] | 59 | +0.42 | [-0.32, +1.16] | +1.91 [+0.52, +3.30] |
| ROLL-1 | 3 | support 3-of-3 | +0.02 | [-1.25, +1.29] | 221 | -1.24 | [-2.54, +0.03] | +0.25 |
| ROLL-1 | 5 | R1 medoid | +0.03 | [-0.64, +0.70] | -- | -- | -- | -- |
| ROLL-1 | 5 | support 2-of-5 | +0.46 | [-0.22, +1.12] | 25 | +0.47 | [-0.26, +1.21] | +2.02 [+0.67, +3.39] |
| ROLL-1 | 5 | support 3-of-5 (published +1.40) | +1.40 | [+0.52, +2.28] | 102 | +0.48 | [-0.41, +1.37] | +2.03 [+0.61, +3.49] |
| ROLL-1 | 5 | support 4-of-5 | +1.06 | [-0.08, +2.21] | 215 | -0.40 | [-1.52, +0.71] | +1.15 |

**Notes on the table.**

- **Intent.** It moves only through the medoid choice: +0.05 to +0.34 pp on these arms. The filter never touches
  labels, and v4 never does either.
- **Overlap between filter and v4.** On ROLL-1, v4 alone captures most of what the filter bought: +1.55 against
  +1.40, on the same false-positive mass. The filter's increment over v4 is then not resolved.
- **On ROLL-3** the filter keeps a resolved increment over v4 at 2-of-3 and at 3-of-5.

### 5a. Cost model (review-off graph, per 100 rows)

**Call counts.**

- The grouped sampler (E2, `rails/native_episode_config.py`) fans out only the Solver visit, at k contacts per
  visit. Review-off (Perception -> Solver) therefore costs 100 + 100k calls per 100 rows: 200 at k = 1, 400 at
  k = 3, 600 at k = 5.
- The brief's "200 -> 200k" would also fan out Perception. If that is intended, every per-call rate below halves.

**Engineering constraint.** A grouped Solver currently forbids a `deliver_normaliser` node (the ROLL-3 config
records "a grouped Solver forbids one"). v4 after a commit policy needs one composed commit-then-normalise step.

| mechanism | extra calls / 100 rows | SLU gain (pp, CI95) | pp per 100 extra calls |
| --- | ---: | --- | ---: |
| **v4 (Part A), temperature 0** | **0** | A2 +0.98 [+0.21, +1.74]; Fold A **+1.67 [+0.81, +2.50]** | free |
| support 2-of-3 over v4, ROLL-3 | +200 | +0.84 [+0.19, +1.49] | 0.42 |
| support 2-of-3 over v4, ROLL-1 | +200 | +0.42 [-0.32, +1.16] | 0.21 (not resolved) |
| support 3-of-5 over v4, ROLL-3 | +400 | +1.11 [+0.33, +1.91] | 0.28 |
| support 3-of-5 over v4, ROLL-1 | +400 | +0.48 [-0.41, +1.37] | 0.12 (not resolved) |
| support 3-of-5 without v4, ROLL-3 / ROLL-1 | +400 | +2.06 / +1.40 | 0.51 / 0.35 |
| Reviewer -> Solver loop (N100 seed vs review-off, `2026-10-08-simple-consumption-n100-complete-family.md`) | +410 | +1.48 [-2.72, +5.33]; raw model entity repairs **0**, repair after a true alarm 1/32, false alarms 38 % | 0.36 point, not resolved, mechanism null |

**Reading.**

- **Per call, the support filter beats the Reviewer.** It has a resolved effect on DEV at 2-of-3 for half the
  Reviewer's calls. The Reviewer's +1.48 is not resolved, and its mechanism shows 0 raw repairs; the deterministic
  post-processing repaired 3/54 in that same panel.
- **Only on DEV.** The filter's increment over v4 is resolved only on DEV (ROLL-3, the PLAN policy). On R01C it is
  not.
- **Not measured: the k-sample increment over a temperature-0 single sample.** No pool holds a greedy sample beside
  temperature-0.7 samples, so this read cannot measure it. Both Part-B pools compare against a temperature-0.7
  single sample.
- **What a k = 3 decision needs.** It must come from a COMP-1b (or NX base) grouped pool that includes the greedy
  sample, read offline exactly like this.

## 6. Recommended v4 rule set (exact, ordered)

Proposed id `saea-deliver-normalise-v4`. Each step reads only the delivered answer, TRAIN statistics from the R5
pool, and the pinned scope table:

1. **`saea-deliver-normalise-v3`**, unchanged: label rule R_action then legal-label projection v2, then filler P2
   (case, whitespace, punctuation, meridiem, numeric words).
2. **fx-article.** For each entity of type t whose filler has >= 2 tokens and whose first token w is in {the, a,
   an, my, this, next, at, in, on, to, for, your, our}, strip w when (t, w) is in the TRAIN strip set. The strip
   set holds the pairs where pool spans include w in < 10 % of >= 10 cases in which w immediately precedes the span
   in the utterance (73 pairs on the R5 pool).
3. **fx-oclock.** On type time with >= 2 tokens, strip a final "o'clock" or "oclock" (TRAIN: included 0 of 5
   opportunities).
4. **scope.** Drop the indices `saea-deliver-scope-rule-v1` selects (pinned table `fcff0c42...`, >= 5 occurrences,
   >= 80 % untagged).
5. **ti1.** When the delivered intent `scenario_action` occurs in the pool, drop an entity whose type occurs in
   < 1 % of that intent's pool exemplars.
6. **ee10.** When the delivered intent occurs in the pool and < 10 % of its pool exemplars carry any entity, drop
   all entities. An empty list is never filled.

**Not adopted, with reasons.**

- fx-month-ordinal: harmful, -0.08 [-0.16, -0.02]. The TRAIN convention is speech-faithful, not canonical.
- vs-type and vs-any: harmful, -7.9 and -8.2.
- ti0: dominated by ti1.
- ee5: fires on 1 row, -0.03.

**Before a runtime registration.** The TRAIN statistics of steps 2, 3, 5 and 6 must be frozen as a pinned table,
as the scope table is.

A draft implementation, unregistered and with injected statistics, is committed separately on this branch:
`SlurpProjectionV4DeliveryNormaliser` in `rails/delivery_normalisers.py`, tests in
`tests/unit/test_deliver_normaliser_v4_draft.py`.

## 7. Reproduce (WSL, from the worktree; zero model contacts)

```bash
cd /home/chao/saea-worktrees/fable-nx-postproc && source ~/.venvs/speechrl/bin/activate
export SPEECHRL_DATA_DIR=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
# Part A, select on A2 (431 combinations + 10 single rules; one registered-scorer copy for the selected column)
PYTHONDONTWRITEBYTECODE=1 python -B scripts/analysis/slurp_nx_postproc_v4_search.py --select --score-copy
# Part A, the single Fold-A confirmation (refuses a second run)
PYTHONDONTWRITEBYTECODE=1 python -B scripts/analysis/slurp_nx_postproc_v4_search.py --confirm \
    --rules fx-article,fx-oclock,scope,ti1,ee10 --score-copy
# Part B (ROLL-1 with the row-cluster control, ROLL-3)
for a in "--pool roll1" "--pool roll1 --row-cluster" "--pool roll3"; do
  PYTHONDONTWRITEBYTECODE=1 python -B scripts/analysis/slurp_nx_postproc_v4_search.py --part B $a \
      --rules fx-article,fx-oclock,scope,ti1,ee10
done
```

| report (`analysis/SAEA-SLURP-NX-POSTPROC-V4-SEARCH-V1/...`) | sha256 |
| --- | --- |
| `select-a2/report.json` | `c2cded66a3f3ec1e3e4ecc04a3451e265c7e3d642864ed46444d4e68102ae553` |
| `confirm-fold-a/report.json` | `cfe315965b619ba93809a5abfbe1cb2bb8e0be1902aa83b760c598c7f34915e8` |
| `partb-roll1/report.json` | `ef96ebf1c37c24ccbc98c51c9d809ecc4caf1b2ee9059085bc804442ef09f9ba` |
| `partb-roll1-rowcluster/report.json` | `9f30a8adcba89d25c0d0f9984b2ad6be5b4774ded0f97717ae90eb4090b29967` |
| `partb-roll3/report.json` | `ed8f155c56cfcbd93690636423aff4668981b5f65ff674b11c7c9407d024ec49` |
