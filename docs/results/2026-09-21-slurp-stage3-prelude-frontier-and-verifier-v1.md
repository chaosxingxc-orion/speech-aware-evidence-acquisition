# SLURP Stage-3 prelude: the module frontier and the verifier measurement

Date: 2026-09-21. Author: the Stage-3 prelude read. Owner decisions **73(b)**, **74** and **75** of
2026-09-21. Execution profile `model-free-check`.

**Exposure.** Zero model, tokenizer, encoder, ASR, server, GPU, paid-API and network contacts. The
only scorer invocations are the registered model-free `slurp-slu-official-train` scorings, every one
of them over a **copy** of sealed bytes written under this read's own output root
(`SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-PRELUDE-V1/`). No sealed file was opened for writing,
moved or renamed; no run directory, exposure-ledger row, harness-admission receipt or results ledger
was edited by this read. No utterance text, transcript, gold filler or model output is printed or
persisted anywhere in this document or in its artefacts: it reports counts, rates, scenario names,
percentages and content hashes only. Gold entered exactly where it always enters — inside the
registered scorer.

**Claim boundary.** Development numbers only (owner decision 28). Every number is the official SLURP
`evaluate.py` at its pinned commit on **TRAIN Fold A**, 1,080 rows, roster
`docs/receipts/rosters/slurp-evo-fold-a-v2.json`
(`1fe7908c31396774d7535fdf37bd791762215c324999d66ed7beb9e7b2f9033d`), 125 speaker clusters, 18
scenarios of 60, 523 headset / 557 far-field. TRAIN Fold A is an exposed discovery roster. Nothing
here is a test claim, a superiority claim or a generalisation claim, and nothing here is comparable
with a published baseline. This document registers nothing, arms nothing and decides nothing; it
measures.

**Regeneration.** Every table below is produced by one of two commands, from a clean checkout at or
after `51c7ec4d`, with `PYTHONDONTWRITEBYTECODE=1` and `PYTHONPATH=<repo>/src`:

```bash
# Part A -- tables A1 to A4
python scripts/analysis/slurp_module_frontier.py --stage all \
    --data-root "$SPEECHRL_DATA_DIR" \
    --out-dir "$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-PRELUDE-V1/frontier"
python scripts/analysis/slurp_module_frontier.py --self-check --data-root "$SPEECHRL_DATA_DIR"

# Part B -- tables B1 to B5
python scripts/analysis/slurp_verifier_measurement.py --stage all \
    --data-root "$SPEECHRL_DATA_DIR" --repo-root . \
    --lock-path ../../docs/datasets.lock.json \
    --out-dir "$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-PRELUDE-V1/verifier"
python scripts/analysis/slurp_verifier_measurement.py --self-check --data-root "$SPEECHRL_DATA_DIR"
```

Both scripts take `--stage collect|frontier|report` and `--stage reviewer|rollouts|report`
respectively (owner decision 58: analyses run by script, every table regenerable by stage). The
machine-readable artefacts are `frontier/collect.json`, `frontier/frontier.json`,
`verifier/reviewer.json` and `verifier/rollouts.json`; the Markdown twins of the tables are
`frontier/frontier-tables.md` and `verifier/verifier-tables.md`.

---

## PART A — the effect-cost Pareto frontier of the SLURP module table

### A.0 The one methodological rule, stated before any number

The decided cells do **not** share a comparator. B0, B0r, B2 v3, B4a v2, B4b, B4b-rep, B7a v2,
B8b-anchor and EFF-1 are read against the sealed dual-store anchor
(`SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1`); B5e and B1-notool are read against
cell B1's arm (`SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TRAIN-FOLD-A-RECOVERY-V2`); IDX and IDXT are
read against cell B1-notool (`SAEA-SLURP-NATIVE-EXEMPLARS-K20-NOTOOL-V1`); and B8a is read against
its own OFF side on three different bases. **Deltas measured against different comparators are never
chained in this document.**

The frontier is therefore built on each arm's **absolute** official
`slurp-slu-official-train` number, which is legitimate for exactly one reason: every arm scored the
**same** 1,080-row roster with the **same** registered scorer, once, through a complete manifest. The
per-cell delta and its CI95 live in a separate table (A2), each beside the comparator it was measured
against and beside the margin regime it was judged under. Four margin regimes are in play and the
table names them: the DEV1000 import (SLU 1.18 / intent 0.92, cell B0's first pass only), cell B0r's
own null (**1.1218 / 1.0051**, every anchor-based cell), cell B4b-rep's own null (1.3222 / 1.0682,
its own output), and cell B1r's own null (**1.2350 / 1.2212**, every B1-based cell).

### A.1 Where the numbers come from

| Quantity | Source, per cell |
| --- | --- |
| absolute official SLU-F1 and intent, the delta and its CI95, the per-scenario tables | that cell's own sealed paired read, `SPEECHRL_DATA_DIR/analysis/<dir>/score-contrasts.json`, at the JSON pointer `collect.json` records per row; cross-checked against the same directory's `per-scenario-tables.json` where one exists (**0 mismatches at 1e-9 across every cell that has both**) |
| GPU hours per 1,080 rows | the arm's own sealed `flight-receipts.json`, `stages.seal.serving_monitor_summary.active_seconds / 3600` — the definition every SLURP verdict's cost block uses |
| contacts per row, client prompt tokens | the same receipt's `stages.seal.cost` block (`calls_used`, `prompt_tokens_total`) |
| prefilled tokens per row | the cell's own verdict where one measured it (EFF-1, B1-notool, IDX, IDXT, B1r) or the consolidated efficiency note for B1 and B4b; otherwise the manifest's **client prompt tokens per row**, explicitly flagged as a PROXY |
| status | the cell's verdict note, or `docs/receipts/harness-admission.json` where the receipt is the authority |

Two cells have no flight receipt of their own and carry a pinned transcription instead: the sealed
**anchor** attempt (its cost is the figure cell B2 v3's verdict read from the run) and the released
**direct** anchor. Two cells are E10 mode-A resumes whose receipt covers only the resumed attempt and
therefore **understates** their run-cumulative cost: **B4b-rep** (500 of 1,080 rows flown in the
attempt read here; run-cumulative 5,423 contacts) and **B8b-anchor** (702 flown, 378 kept under I7r
custody; run-cumulative 3.8464 GPU hours over 5,822 contacts). Both are flagged in table A1 and
neither reaches the frontier under either figure.

### A.2 Tables A1-A4

The four tables are generated verbatim by

```bash
python scripts/analysis/slurp_module_frontier.py --stage all --data-root "$SPEECHRL_DATA_DIR"
```

and are reproduced in `SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-PRELUDE-V1/frontier/frontier-tables.md`.
Their content is summarised and interpreted below; the generated file is the authority for the exact
digits.

**Table A1 — absolute official numbers and cost, the plane the frontier lives on.**

| Cell | Status | Official SLU | Official intent | GPU-h / 1,080 | Contacts / row | Prefilled tok / row | Token basis |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| B8a (B5e base) | ADMITTED (reported base) | 63.78 | 81.85 | 3.8709 | 5.014 | 46,796.0 | PROXY |
| B8a (B1 base) | ADMITTED | 62.67 | 81.76 | 3.6819 | 5.023 | 45,730.5 | PROXY |
| B5e | NEUTRAL vs B1 (decision-25 addendum) | 62.34 | 80.09 | 3.8709 | 5.014 | 46,796.0 | PROXY |
| B1r | REPLICATED | 62.23 | 80.09 | 3.8507 | 5.040 | 26,071.9 | measured |
| **B1-notool** | NON-INFERIORITY NOT PROVEN | **62.13** | 80.00 | **1.6108** | 4.104 | **8,019.8** | measured |
| B1 | ADMITTED | 61.14 | 80.19 | 3.6819 | 5.023 | 25,933.0 | measured |
| IDX | HARMFUL | 54.76 | 77.59 | 1.3340 | 4.181 | 3,379.1 | measured |
| B1-twin *(control)* | COMPARATOR | 53.30 | 78.15 | 3.6369 | 5.027 | 45,615.2 | PROXY |
| IDXT *(control)* | HARMFUL (CONTROL) | 52.16 | 80.19 | 1.2474 | 4.221 | 2,795.7 | measured |
| B8a (anchor base) | ADMITTED | 51.99 | 79.35 | 3.3880 | 5.016 | 42,591.0 | PROXY |
| B4b | ADMITTED | 51.09 | 78.52 | 3.4651 | 5.006 | 26,197.0 | measured |
| B4b-rep | REPLICATED and ADMITTED | 50.07 | 78.61 | 1.7430 † | 2.316 † | 21,257.2 | PROXY |
| B8b-anchor | NEUTRAL | 49.40 | 79.17 | 2.6253 † | 3.524 † | 32,470.1 | PROXY |
| B0 | HARMFUL | 48.67 | 77.59 | 1.0540 | 2.000 | 12,328.7 | PROXY |
| B0r | HARMFUL | 48.63 | 77.69 | 1.0588 | 2.000 | 12,357.6 | PROXY |
| B2 v3 | NEUTRAL (NI not proven) | 48.60 | 78.80 | 3.7139 | 9.081 | 78,282.3 | PROXY |
| B7a v2 | HARMFUL | 48.22 | 77.31 | 3.7809 | 5.205 | 45,913.4 | PROXY |
| B4a v2 | HARMFUL | 47.83 | 78.70 | 4.7210 | 5.011 | 55,349.3 | PROXY |
| EFF-1 | HARMFUL | 44.14 | 68.80 | 1.8433 | 4.901 | 10,127.2 | measured |

† resume attempt only; understates the run-cumulative cost (section A.1).

**Table A2 — each cell against its own comparator.** Reproduced in full in the generated file. The
headline rows: B1 +12.61 [+10.54, +14.60] and B1r +13.70 [+11.64, +15.73] against the anchor; B4b
+2.55 [+1.13, +3.98] and its replicate +1.54 [+0.30, +2.93] against the anchor; B5e +1.20
[-0.11, +2.48] against B1; B1-notool +0.99 [-0.59, +2.50] against B1; IDX **-7.37 [-9.72, -4.80]**
and IDXT **-9.97 [-12.46, -7.32]** against B1-notool; EFF-1 **-4.39 [-6.69, -2.17]** against the
anchor; B8a's node ON minus OFF +3.46 / +1.53 / +1.44 on the anchor, B1 and B5e bases.

**Table A3 — the frontier.** On the GPU-hour plane the frontier, cheapest first, is

> **B0** (1.054 GPU-h, 48.67) → **IDXT** (1.247, 52.16) → **IDX** (1.334, 54.76) →
> **B1-notool** (1.611, 62.13) → **B8a on the B1 base** (3.682, 62.67) →
> **B8a on the B5e base** (3.871, 63.78)

and on the prefilled-token plane it is IDXT (2,796 tok/row) → IDX (3,379) → **B1-notool** (8,020) →
B1r (26,072) → B8a on B1 (45,731) → B8a on B5e (46,796).

**The knee is B1-notool on both planes** (scaled chord distance 0.490 and 0.523 respectively; the
definition is stated in the script and in table A3: min-max scale both axes over the frontier, join
the frontier's cheapest and most effective points with a chord, and take the frontier point of
greatest perpendicular distance from it). Everything the programme currently has that is worth more
than 62 official SLU costs at least 3.68 GPU hours per 1,080 rows **except** B1-notool, which reaches
62.13 at 1.61 — **58 % less GPU time and 69 % fewer prefilled tokens than B1r at a difference of
-0.10 official SLU**.

**The dominated cells** — cells for which some other cell is at least as good on official SLU and at
least as cheap, with at least one strict:

| Cell | Dominated by (GPU-hour plane) |
| --- | --- |
| B0r | B0 |
| B4b-rep | B1-notool, IDX, IDXT |
| EFF-1 | B0, B0r, B1-notool, B4b-rep, IDX, IDXT |
| B8b-anchor | B1-notool, B4b-rep, IDX, IDXT |
| B8a (anchor base) | B1-notool, IDX, IDXT |
| B4b | B1-notool, B8a (anchor base), IDX, IDXT |
| B1-twin | B1-notool, IDX |
| B1 | B1-notool, B8a (B1 base) |
| B2 v3 | twelve cells, including every cheaper one |
| B7a v2 | thirteen cells |
| B1r | B8a (B1 base) |
| B5e | B8a (B1 base), B8a (B5e base) |
| B4a v2 | seventeen cells — every other cell on the plane |

**Table A4 — per scenario.** Every cell read here carries an 18-scenario table (18 of 18 scenarios
available on all 19 rows of the plane), read from the same sealed paired read and cross-checked
against `per-scenario-tables.json` with **zero** mismatches. Frontier membership over the 18
scenarios: B0 18 (trivially — the cheapest point is always on a frontier), B1-notool 14, IDX 11,
IDXT 11, B0r 10, B8a on B1 8, B1r 7, B8a on B5e 5, B1 2, B5e 1, B1-twin 1, B8a on the anchor 1.

**Seven cells are on no scenario's frontier at all**: **B2 v3, B4a v2, B4b, B4b-rep, B7a v2,
B8b-anchor and EFF-1.** That is the strongest single statement this plane supports: it is not that
these modules are weak on the pooled number and strong somewhere; there is no stratum on which any of
them is worth its cost.

### A.3 What the frontier says, and what it does not

1. **The cheap end of the frontier is entirely the September efficiency work.** IDXT, IDX and
   B1-notool are the three cheapest points above 48 SLU, and all three came from the tool-withdrawal
   and index line, not from any knowledge module. The single largest cost lever measured anywhere in
   the table is the withdrawal of the Reviewer's task-contract tool: 5.04 → 4.10 contacts per row,
   26,072 → 8,020 prefilled tokens per row, 3.85 → 1.61 GPU hours, at -0.10 official SLU.

2. **The index cell bought its remaining cost with effect it could not afford.** IDX goes from 8,020
   to 3,379 prefilled tokens per row and from 1.61 to 1.33 GPU hours — and loses 7.37 official SLU
   [-9.72, -4.80]. The derangement twin decomposes that loss and the decomposition is unkind to the
   mechanism: IDXT, which has the **same rendering** with **deranged content**, loses **9.97**
   [-12.46, -7.32], i.e. *more* than the arm. The index's **form** costs about ten points and its
   **content** recovers about 2.6 of them. What failed is the rendering, not the knowledge.

3. **The review loop is the largest unpriced cost on the plane, and part B is about it.** The anchor
   spends 3 of its 5.02 contacts per row on the Reviewer and the Planner. Cell B0 removes them
   entirely, costs 2.00 contacts and 1.054 GPU hours against the anchor's 5.016 and 3.388 — **69 % of
   the anchor's GPU time is the review loop** — and the official number moves by **+0.13 pp
   [-1.15, +1.45]** on SLU and **-0.37 pp [-1.53, +0.82]** on intent. B0 was read HARMFUL on the
   intent clause, and that verdict stands as written; but it was a width failure at a nil point
   estimate, and the plane says plainly that two thirds of the base's inference budget currently buys
   an effect the roster cannot distinguish from zero.

4. **What the frontier cannot decide.** It cannot rank a NEUTRAL against an ADMITTED cell: admission
   is a statement about a delta against a comparator at a margin, and the plane is a statement about
   absolutes against cost. A cell can sit on the frontier and still be HARMFUL against its own
   comparator (IDX and IDXT both do). It cannot price the compositions nobody flew: the M3 delivery
   node is a pure zero-contact function that has been measured on three bases, and arming it on the
   **B1-notool** base — which the frontier says is the knee — would plausibly land near 63.6 official
   SLU at 1.61 GPU hours, but that composition **has never been flown and that number is a
   derivation, not a measurement**. It cannot correct the two resume cells' understated cost. And it
   says nothing about DEV, Fold B or the test split.

---

## PART B — the verifier measurement

### B.0 The question, and the frame it is asked in

The base spends **three of its five contacts per row** on a verifier: the Reviewer visits and the
Planner routes ACCEPT or REVISE on what they say. Cell B2 v3 bought a second kind of test-time
compute — five Solver samples per row, aggregated by a registered plurality/support commit. Part A
has just priced both: the review loop is 69 % of the anchor's GPU time, and B2 v3 is the single most
expensive cell on the plane (9.08 contacts and 78,282 client prompt tokens per row) and on no
scenario's frontier.

The frame is the programme's own literature commons
(`wiki/survey/workbench/training-free-rl-2026-09-21/README.md`, section 4). Brown et al.
(arXiv:2407.21787, 2024) separate **coverage** — some sample is correct — from **selection** — the
committed sample is correct — and report that majority voting and reward models plateau long before
coverage does, absent an automatic verifier. Chen et al. (arXiv:2403.02419, 2024) report that Vote
and Filter-Vote can rise and then **fall** in the number of LM calls, because more calls help easy
queries and hurt hard ones. Section 4(f) of that commons already names the action this part
executes: *measure the Reviewer ensemble's selection precision directly against the official scorer,
because a verifier below the noise floor makes extra samples cost-only.*

### B.1 Selection precision and recall of the route

Method, in one paragraph. For each of the three arms the **initial** Solver draft is identified by
the first `solver`-stage role visit's own `response_text_sha256` in the row's sealed native episode
receipt. Where that hash equals the row's delivered `response_text_sha256`, the delivered text **is**
the initial draft, byte for byte — 1,077 of 1,080 rows on the anchor, 1,076 on B1, 1,055 on
B1-notool. Only the remainder is recovered from the sealed trace, and each recovered text is
re-hashed against the receipt's own hash before it is used. The complete 1,080-row draft copy is then
scored **once**, through `core.base.SCORERS.resolve("slurp-slu-official-train")` over the copy, never
over a sealed run directory — the same invocation `core.scoring_batch` makes inside its own job
process, and the same path `analysis.b8a_delivery_node_read` takes.

**Table B1 — the route as a verifier.** "Precision" is P(the draft was wrong | the route was
REVISE). "Recall" is P(the route was REVISE | the draft was wrong). Wrongness is full-task exactness:
the intent exact **and** the entity set exact on the official counts.

| Arm | Reviewer contacts | Rows routed REVISE | Revisions executed | Drafts wrong | REVISE & wrong | **Precision** | **Recall** | Saves | Harms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| anchor | 2,167 | 5 (0.46 %) | 5 | 763 (70.6 %) | 4 | **80.0 %** | **0.52 %** | 0 | 0 |
| B1 | 2,171 | 7 (0.65 %) | 7 | 640 (59.3 %) | 7 | **100.0 %** | **1.09 %** | 1 | 0 |
| B1-notool | 1,112 | 40 (3.70 %) | 40 | 635 (58.8 %) | 33 | **82.5 %** | **5.20 %** | 3 | 4 |

**Table B2 — what the loop actually moved.** Official per-row counts, draft against delivered.

| Arm | Metric | Draft correct | Delivered correct | Net | Saves | Harms |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| anchor | intent exact | 843 | 842 | **-1** | 0 | 1 |
| anchor | entity set exact | 379 | 379 | 0 | 0 | 0 |
| anchor | full task exact | 317 | 317 | **0** | 0 | 0 |
| B1 | intent exact | 866 | 866 | 0 | 1 | 1 |
| B1 | entity set exact | 509 | 511 | +2 | 2 | 0 |
| B1 | full task exact | 440 | 441 | **+1** | 1 | 0 |
| B1-notool | intent exact | 863 | 864 | +1 | 3 | 2 |
| B1-notool | entity set exact | 514 | 514 | 0 | 4 | 4 |
| B1-notool | full task exact | 445 | 444 | **-1** | 3 | 4 |

And on the pooled official number, draft against delivered: anchor **48.4569 → 48.5336**
(+0.077 pp), B1 **61.0801 → 61.1394** (+0.059 pp), B1-notool **62.0279 → 62.1295** (+0.102 pp).
The anchor's numbers reproduce the sealed 2026-09-16 review-stage attribution field for field (843 →
842 on intent with zero saves and one harm; 379 / 379 entity-set exact; 317 / 317 full-task exact;
five REVISE rows) — that is this script's `--self-check`, and it passes.

**What this says.** The verifier's **precision is high and its recall is a rounding error.** When the
Planner does route REVISE, the draft really was wrong four times in five (anchor), seven times in
seven (B1) and four times in five (B1-notool). But it routes REVISE on 0.46 % to 3.70 % of rows
against a wrong-draft base rate of **59 % to 71 %**, so it catches between **one in two hundred** and
**one in twenty** of the answers that needed catching. The three contacts per row that pay for it
move the official pooled number by **+0.06 to +0.10 pp** — an order of magnitude inside the roster's
own-null half-width of 1.1218 / 1.2350 pp. The loop is not wrong; it is **almost never invoked**, and
when it is invoked it changes the delivered answer's correctness on 0 to 8 rows of 1,080.

**Withdrawing the tool made the verifier eight times more willing to act, and it did not help.**
B1-notool routes REVISE on 40 rows against B1's 7 — the Reviewer answers on its first contact instead
of spending one on a tool round trip — and the extra 33 revisions produce 3 saves against 4 harms on
full-task exactness. More verifier activity at the same verifier quality buys noise.

### B.2 Coverage against selection on the B2 v3 rollouts

**The licence, checked before any coverage number was read.** Each of the five sealed samples per row
is rendered back to the canonical answer payload `analysis.native_commit_replay.replay_row` writes,
and the registered commit policy `saea-commit-plurality-support-v1` at min_support 3 / char-F1 0.8 is
re-applied offline to the same sealed samples. That replay reproduces the sealed delivered answer's
official count fields on **1,080 of 1,080 rows**, and scores **48.5977** official pooled SLU-F1
against the arm's own sealed 48.5977. Custody: 1,080 rows, five samples each, 29 malformed samples of
5,400 (0.54 %) over 13 rows, no row malformed on all five. Sample-agreement histogram 5/5 on 1,012
rows, 4/5 on 26, 3/5 on 33, 2/5 on 6, 1/5 on 3 — reproducing cell B2 v3's own diagnostic exactly.

**The six individually scored sides.** Official pooled SLU-F1: sample 0 **46.1301**, sample 1
**46.8987**, sample 2 **47.3146**, sample 3 **48.2415**, sample 4 **45.4772**, committed
**48.5977**. The five samples differ by **2.76 pp** among themselves at temperature 0.7, and the
commit lands **0.36 pp above the best of them**.

**Table B3 — coverage against selection, pooled, N = 5.** Coverage@k is the unbiased estimator
`1 - C(n-c, k)/C(n, k)`. Selection is the sealed delivered answer's own official correctness; on this
arm the registered commit *is* the plurality vote, so **selection and majority vote are one number**.
"Selection efficiency" is (selection - coverage@1) / (coverage@5 - coverage@1): the share of the
available headroom the selector actually captures. Every stratum holds exactly 60 rows, so the
equal-scenario weighting is numerically identical to the natural mixture here.

| Metric | cov@1 | cov@2 | cov@3 | cov@4 | cov@5 | **selection** | cov@5 - selection | selection - cov@1 | efficiency |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| intent exact | 78.20 | 79.16 | 79.63 | 79.91 | 80.09 | **78.80** | **+1.30** | +0.59 | 31.4 % |
| entity set exact | 32.85 | 39.61 | 43.55 | 46.07 | 47.78 | **37.59** | **+10.19** | +4.74 | 31.8 % |
| full task exact | 27.61 | 33.06 | 36.31 | 38.37 | 39.72 | **30.83** | **+8.89** | +3.22 | 26.6 % |

**The coverage-selection gap is the finding.** On full-task exactness the frozen core already
produced a correct answer on **39.72 %** of rows somewhere in its five samples, and the system
delivered a correct answer on **30.83 %**. **8.89 pp of correct answers were generated and thrown
away** — 96 rows of 1,080. The selector captures **26.6 %** of the headroom sampling opened. And the
number that should decide the N question: **the committed answer at N = 5 (30.83) is below the
oracle over just two samples (33.06).** Five samples plus this selector is worth less than two
samples plus a perfect one.

The entity half is where both the headroom and the loss live (gap +10.19 pp); intent has almost no
headroom to begin with (coverage@5 80.09 against a single sample's 78.20), which is consistent with
cell B2 v3's own reading that the mechanism moves labels up by about the own null's width and moves
entities down.

**Table B4 — per scenario, full-task exactness.** Generated in full in
`verifier/verifier-tables.md`. The shape: selection efficiency ranges from **-48.1 %** (`calendar`)
to **100 %** (`email`), and **three strata have a negative efficiency** — `calendar` -48.1 %,
`datetime` -17.6 %, `takeaway` -4.2 % — meaning the commit delivers a *worse* answer than a random
single sample would. That is Chen et al.'s non-monotonicity appearing per stratum rather than per
call count: more samples help some strata and hurt others, and the pooled +3.22 pp is a sum of
+15.0/+16.7 pp headroom strata and strata where sampling is actively harmful. The largest unclaimed
headroom sits in `news` (+18.33 pp gap), `takeaway` (+16.67), `alarm` and `lists` (+15.00 each) and
`calendar`/`datetime` (+13.33 each).

### B.3 Every confidence-like signal the receipts carry

**Table B5 — ranked by AUROC.**

| Signal | Arm | Target | AUROC | Distinct values |
| --- | --- | --- | ---: | ---: |
| sample-agreement count (1..5) | B2 v3 | delivered intent correct | **0.573** | 5 |
| sample-agreement count (1..5) | B2 v3 | delivered full task correct | **0.535** | 5 |
| sample-agreement count (1..5) | B2 v3 | delivered entity set correct | **0.523** | 5 |
| the REVISE route itself | B1-notool | the draft is wrong (full task) | 0.518 | 2 |
| Reviewer iteration count | B1-notool | the draft is wrong (full task) | 0.516 | 3 |
| Reviewer iteration count / route | B1 | the draft is wrong (full task) | 0.505 | 2 |
| Reviewer iteration count / route | anchor | the draft is wrong (full task) | 0.501 | 2 |

Accuracy by agreement level on the delivered intent: 5/5 on 1,012 rows → 824 correct (**81.4 %**);
4/5 on 26 → 10 (38.5 %); 3/5 on 33 → 11 (33.3 %); 2/5 on 6 → 3 (50.0 %); 1/5 on 3 → 3 (100 %). The
81.4 % / 39.7 % split between unanimous and non-unanimous rows is real and free, but it is **not a
ranker**: 93.7 % of rows are unanimous, so the signal is almost constant and its AUROC is 0.573 on
its best target and 0.535 on the one that matters.

**Three plain statements about confidence.**

1. **There is no usable confidence signal in the current receipts.** The best one — sample agreement
   — needs five samples to exist and then ranks correctness at AUROC 0.535 on full-task exactness.
   For comparison the base's own logprob probe was NOT ADMITTED at min-token AUROC 0.69, which was
   already judged below the bar (`docs/results/2026-09-09-slurp-logprob-judge-probe-v1-verdict.md`);
   sample agreement is *worse* than the signal the programme already refused.
2. **The route and the Reviewer iteration count carry essentially no information**: AUROC 0.501 to
   0.518 on three arms. They are near-constant by construction — the Planner says ACCEPT on 95.6 % to
   99.5 % of rows — and a near-constant signal cannot rank.
3. **The Reviewer's own findings cannot be ranked at all.**
   `rails.review_findings.parse_review_findings` fails on **2,167 of 2,167** anchor Reviewer outputs
   (`docs/results/2026-09-17-slurp-node-context-audit-v1.md`, section 6). There is no finding count,
   no severity, no citation set. The Reviewer emits prose and nothing in the harness reads it. **This
   is the single cheapest thing to fix before any further verifier work**, because until it is fixed
   the programme cannot measure Reviewer issue-detection recall at all — only the Planner's route,
   which is what this part measured instead.

### B.4 What N and what Reviewer iteration count the numbers support

Stated plainly, and stated as what these numbers support rather than as a plan.

**N.** The measurements do **not** support raising N, and they do not support keeping N = 5 either.
The binding constraint is the **selector**, not the sample budget: selection efficiency is 26.6 % on
full-task exactness, and the committed answer at N = 5 is *below* the oracle over two samples. Buying
more samples multiplies a headroom the current commit cannot convert. Concretely:

- **N = 1 is the defensible default today** on the anchor base. Cell B2 v3 is NEUTRAL against the
  anchor (+0.06 pp [-1.46, +1.60]) at 1.81× the contacts and 1.10× the GPU hours, and part A puts it
  on no scenario's frontier.
- **If N is spent, spend it adaptively and low.** 93.7 % of rows are unanimous across five samples,
  so an escalation rule — draw 2, stop on agreement, escalate to 5 on disagreement — would cost about
  **2.2 samples per row** instead of 5 and would change the committed answer on the 6.3 % of rows
  where the samples disagree at all. That is a Snell-style compute-optimal allocation and it is an
  *unflown hypothesis*: the numbers here support registering it as a cell, not adopting it.
- **Per stratum, N is not one number.** Three strata (`calendar`, `datetime`, `takeaway`) have a
  negative selection efficiency and should be at N = 1 until a better selector exists; the strata
  worth sampling *if* the selector improves are the ones with both a large gap and a non-trivial
  efficiency: `iot` (+8.33 pp gap at 55.4 % efficiency), `audio` (+11.67 at 35.2 %), `news` (+18.33
  at 9.8 %), `weather` and `transport` (+10.00 at ~30 %).
- **No N claim is separable from temperature.** The greedy-repeat twin never flew, so nothing here
  distinguishes "five samples at temperature 0.7" from "five greedy repeats", and any N
  recommendation inherits that gap.

**Reviewer iterations.** The measurements support **not buying more review, and reporting the current
review budget as unjustified on this roster**. Three contacts per row, 69 % of the anchor's GPU time,
produce a route that fires on 0.46 % to 3.70 % of rows against a 59-71 % wrong-draft base rate, moves
the delivered answer's full-task correctness by **0 to ±1 rows of 1,080**, and moves the pooled
official number by +0.06 to +0.10 pp — an order of magnitude inside the own-null width. Withdrawing
the tool raised the route rate eightfold and bought 3 saves against 4 harms.

What that does **not** license: it does not license removing the Reviewer. Cell B0 removed the whole
loop and was read **HARMFUL** on the intent clause, and that verdict stands; the six mandatory nodes
are owner decision 43. What the numbers support is the narrower and sharper statement: **the review
loop's iteration count is not the lever — its output format is.** A Reviewer whose verdict does not
parse cannot be measured, cannot be gated on, and cannot select. The ordered next steps these numbers
support are (i) make the Reviewer emit a parseable verdict and re-measure selection precision and
recall against this same instrument; (ii) only then decide the iteration count; (iii) do not raise N
until (i) has moved selection efficiency off 27 %.

---

## Caveats, in one place

Every one of these is a limit of the measurement, not a hedge about it.

1. **The frontier is built on point estimates and carries no interval.** The own-null half-width on
   this roster is 1.1218 pp (anchor configuration) or 1.2350 pp (M1 configuration). B1-notool
   (62.13), B1r (62.23) and B5e (62.34) are **within one own-null width of each other**: their
   ordering on the effect axis is not a measured difference, and no ranking among them should be read
   from this document. What the plane does support is the *cost* separation, which is not a sampling
   quantity at all: 1.61 against 3.85 against 3.87 GPU hours.

2. **Deltas are never chained.** Cells read against different comparators (anchor, B1, B1-notool,
   own-OFF) appear together only on the absolute plane. A cell can be on the frontier and HARMFUL
   against its own comparator; IDX and IDXT both are.

3. **"Prefilled tokens per row" is a proxy on 12 of the 19 rows.** Seven cells (B1, B1r, B4b, EFF-1,
   B1-notool, IDX, IDXT) have a figure a verdict actually measured from the serving monitor. For the
   rest the column carries the manifest's **client prompt tokens per row**, which is a different and
   systematically much larger quantity (it counts every token sent, cached or not). Table A1 flags
   every proxy row and the GPU-hour plane — where no row is a proxy — is the primary plane.

4. **Two cells' cost is the resumed attempt's, not the run's.** B4b-rep (500 of 1,080 rows in the
   attempt read) and B8b-anchor (702 flown, 378 kept) understate their run-cumulative cost. Neither
   reaches the frontier under either figure, so the conclusion is unaffected; the numbers in table A1
   are still not comparable to a single-attempt cell's.

5. **The anchor and the direct baseline have no flight receipt of their own** and their cost is a
   pinned transcription from cell B2 v3's verdict.

6. **The greedy-repeat twin of cell B2 v3 does not exist and this read did not invent one.** Owner
   decision 8, restated by decision 15, launches the twin only on a positive arm CI95, and B2 v3's
   arm read -1.4598. The script asserts the absence rather than assuming it. Consequence: **nothing
   here separates what temperature 0.7 bought from what five greedy repeats plus the same aggregation
   would have bought**, and every coverage number below is a property of the sampled arm only.

7. **The route is not the Reviewer's recommendation.** Part B measures the Planner's ACCEPT/REVISE
   route against the draft's official correctness. A Planner action need not equal the Reviewer's
   recommendation, and the Reviewer's own findings parse on 0 of 2,167 anchor outputs
   (`docs/results/2026-09-17-slurp-node-context-audit-v1.md`, section 6). There is therefore **no
   measurement of Reviewer issue-detection recall anywhere in this document**, and there cannot be
   one until the Reviewer emits something a parser can read.

8. **The rollout coverage numbers are scored on rendered answers.** Each sealed sample's
   `parsed_answer` is rendered back to the canonical payload
   `analysis.native_commit_replay.replay_row` writes, and a malformed sample is rendered as the empty
   answer (never correct under any metric). The licence for that round trip is stated and checked in
   the script: re-applying the registered commit policy offline to the same sealed samples must
   reproduce the sealed delivered answer's own official count fields on every row.

9. **The B2 v3 sample custody is the FINAL Solver visit's.** On the 11 rows the Planner sent back for
   revision, the five sealed samples are the revised visit's, not the initial one's. Coverage on
   those rows is therefore coverage after a revision, not before it.

10. **Selection and majority vote are the same number on this arm.** The registered commit policy is
    a plurality vote over the intent plus a support filter over the entities, so its output *is* the
    delivered answer. There is no third, independent "majority vote" estimate to report, and the
    document says so rather than manufacturing one.

11. **The coverage numbers exist for one arm and one base only.** Grouped Solver sampling was flown
    once, on the **anchor** base. There are no rollouts on the B1 base, none on B1-notool, and none
    at any N other than 5. Every coverage, selection and efficiency number in part B.2 is a property
    of that one configuration, and the frontier's knee (B1-notool) has never been sampled at all.

12. **The coverage-selection gap is an upper bound on what a perfect selector could recover, not a
    promise.** Coverage@5 is an oracle over the five samples that were drawn; it is not reachable by
    any selector that does not see the gold, and no selector measured here comes near it.

13. **Selection precision and recall rest on five, seven and forty positive rows.** The anchor's
    80.0 % precision is 4 of 5 and the B1 arm's 100 % is 7 of 7. These are exact counts of a rare
    event, not estimates with useful intervals, and no confidence interval is attached to them
    anywhere in this document.

14. **AUROC on a near-constant signal is close to meaningless in both directions.** The route takes
    two values and one of them covers 95.6-99.5 % of rows; the 0.501-0.518 readings say the signal
    cannot rank, not that a differently-shaped route could not.

15. **Development numbers only.** TRAIN Fold A, one read, no repeat. Nothing here has been measured
    on Fold B, DEV-500, DEV-1000, DEV-2000 or the test split, and no number in this document may be
    compared with a published SLURP baseline (owner decision 28).
