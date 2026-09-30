# S2a ranker study: no ranker inside the contract reaches T >= 0.738 on perfect text at a false-candidate budget of 10 % or less (best 50 / 70); a stronger ASR is not justified by the S2a line alone (DESCRIPTIVE, offline)

Date: 2026-09-30. Read id `SAEA-SLURP-S2A-RANKER-STUDY-V1`, recipe `slurp-s2a-ranker-study-v1`. This read is input to
owner decision 212 ("pin a stronger ASR"). It follows the S2a.1 addendum
(`docs/results/2026-09-30-slurp-s2a1-missing-slot-recall-ceiling-offline.md`, section A.4), which named this bench
and its gate: contract T >= 0.738 (52 / 70) on the SLURP reference transcript. Written by Claude Opus 5.5, the analysis
agent on the coordinator's brief, in worktree `fable/ranker` (base master `72db56782`).

**Status: DESCRIPTIVE.** These are development numbers on TRAIN Fold B (tuning) and TRAIN Fold A (read), both
construction rosters (owner decisions 28 and 86). The note registers nothing, admits nothing and authorises no flight.
The verdict word belongs to the coordinator.

**Contacts: zero of every kind.** There were no core, server, tokenizer, encoder, embedder, Whisper, GPU, network or
scorer-subprocess contacts. The rankers are CPU-only scikit-learn models fitted in-process (4 BLAS threads, peak
5.3 GB, 24 min per run). `core.flight.cli`, `lease_cli`, re-pins, the queue, the flight worktree and the serving
session were not touched.

**Gold and text discipline.** Gold and reference sentences entered offline, on the scoring side and on the build side
only, through the governed TRAIN loaders `data.slurp.load_slurp_split` and `data.slurp.load_slurp_train_material`.
The devel and test splits were not read. No utterance text, transcript, gold value, span, feature string or model
output is printed or persisted: only ids, counts, rates, thresholds, slot TYPE names and hashes.

## 0. Method

**Driver.** The driver is `scripts/analysis/slurp_s2a1_recall_ceiling.py`, extended with a `--ranker` flag. The value
`trigram-lexicon` is the default and runs the S2a.1 read unchanged. The value `study` runs this read. The unit test
is `tests/unit/test_slurp_s2a1_recall_ceiling.py`, which now holds 15 synthetic tests, 5 of them new for the flag and
the study functions.

**The contract is unchanged.** One call `(row, slot_type t)` returns at most 3 spans (5 in the top-5 variant) of at
most 5 canonical tokens, under three conditions:

- no returned span touches a canonical occurrence of a delivered (draft) value;
- a span's score is its best free occurrence's score for type `t`, ranked by score, then earlier start, then shorter
  span;
- the result is empty unless the best score reaches the abstain threshold theta.

A hit is canonical token-tuple equality with the gold value. No gold enters at call time: the ranker sees the row's
transcript, its draft and the requested type only.

**How the rankers are built. TRAIN gold is used to BUILD the frozen tools, as it builds the slot store.**

- **Build set.** All real TRAIN utterances minus every utterance on the Fold A or Fold B roster, matched by
  `slurp_id` across recordings. That leaves 9,354 utterances.
- **Windows.** Every window of at most 5 canonical tokens of each build sentence is labelled with the slot type whose
  canonical gold value occupies it, or with "none". That gives 232,348 windows, 9,097 of them positive. 9,084 gold
  values were placed; 398 were not verbatim in their own sentence or were longer than 5 tokens.
- **Features.** Hashed features (2^18). "Span" features are the span's tokens, its first and last token, the whole
  string, a shape code and character trigrams. "Context" features are the two left and two right tokens (unigrams
  and bigrams), bags of three tokens on each side and sentence-boundary markers. The context features never include
  the span itself. The length is always a feature.
- **Scores.** P(type | window) from the fitted model.

**Ranker families** (the brief's numbering):

| # | ranker | what it is |
| --- | --- | --- |
| 1 | `lexicon-trigram-primary` / `-full-train` | S2a.1's max character-trigram Jaccard to the TRAIN values of type t (779 / 3,648 values) |
| 2 | `nb-span`, `lr-span` | type-conditioned span classifier (multinomial Naive Bayes, alpha 0.1; multinomial logistic regression) on span features |
| 3 | `lr-context`, `nb-span-context`, `lr-span-context` | context-aware: context features only (LR), or span plus context (NB, LR) |
| 4 | embedding ranker | **not run** (see section 4) |
| 5 | `fusion-lrctx-x-lexicon`, `fusion-lrctx-x-nbspan` | product fusion P[lr-span-context] x (s_other + eps)^w, with w on a grid of {0, 0.25, 0.5, 1, 2, 4} |

**Tuning uses Fold B only.** Fold A is read, never tuned on.

- **Threshold per budget.** For each ranker, transcript source and budget (2.3 %, 5 %, 10 %), theta is the lowest
  value whose false-candidate rate on Fold B is within the budget. The false-candidate rate is the non-empty rate over
  the Fold B rows with no MISSING item on the P-SV-2 AGREE arm (920 rows), times all 55 closed types.
- **Selection point.** The LR regularisation C (grid 0.3 / 1 / 3), the fusion weight w and the overall winner are
  chosen by Fold B reference hits on its 181 MISSING items, at the 5 % budget and top-3.
- **Chosen values.** C = 0.3 (`lr-span`, `lr-context`) and C = 1.0 (`lr-span-context`, 137 Fold B hits).
- **Fusion adds nothing.** Both fusions chose w = 0. Against the lexicon, every w tied at 137. Against NB, the hits
  fall monotonically to 126 as w rises. Both fusions therefore reduce to `lr-span-context`.

**Read (Fold A).**

- **Targets.** The 70 not-in-supply MISSING items of COMP-1b Fold A, each called with its gold type.
- **False-candidate rate.** The non-empty rate over the 908 Fold A rows with no MISSING item, times 55 types.
- **Transcripts.** Two sources are read: the SLURP reference sentence (perfect ASR, the gate's bench) and the pinned
  E5-0 Whisper large-v3 transcript (today's real-world number). For the Whisper column, the thresholds are refitted on
  Fold B Whisper.
- **The bound.** c <= T x 0.457 (CONV uptake), in items of 80, against the 27 / 80 and 18 / 80 lines.

**Stop checks.** All of them reproduced:

- S1: 189 MISSING items on 172 rows, 70 not in the supply;
- E5 containment: 707 / 941 and 718 / 944;
- S2a.1's no-threshold top-3 lexicon reads: primary 30 (reference) / 16 (Whisper); full TRAIN 43 / 24.

## 1. The ranker table (Fold A, 70 not-in-supply items)

Each cell reads **reference hits (Fold A FC rate) / Whisper hits (Fold A FC rate) / reference bound in items of 80**.
The budget columns use the Fold B-fitted theta. The "none" column has no threshold.

| ranker | k | FC budget 2.3 % | FC budget 5 % | FC budget 10 % | no threshold |
| --- | --- | --- | --- | --- | --- |
| lexicon-trigram-primary | 3 | 8 (1.6%) / 6 (2.3%) / 4.18 | 10 (4.5%) / 6 (4.3%) / 5.23 | 22 (9.1%) / 14 (8.8%) / 11.49 | 30 (78.8%) / 16 (78.4%) / 15.67 |
| lexicon-trigram-primary | 5 | 8 (1.6%) / 6 (2.3%) / 4.18 | 11 (4.5%) / 7 (4.3%) / 5.75 | 24 (9.1%) / 16 (8.8%) / 12.54 | 37 (78.8%) / 20 (78.4%) / 19.33 |
| lexicon-trigram-full-train | 3 | 24 (2.4%) / 12 (2.3%) / 12.54 | 26 (4.5%) / 14 (4.3%) / 13.58 | 31 (9.7%) / 17 (9.3%) / 16.2 | 43 (88.9%) / 24 (88.8%) / 22.47 |
| lexicon-trigram-full-train | 5 | 24 (2.4%) / 12 (2.3%) / 12.54 | 27 (4.5%) / 15 (4.3%) / 14.11 | 33 (9.7%) / 19 (9.3%) / 17.24 | 47 (88.9%) / 27 (88.8%) / 24.55 |
| nb-span | 3 | 29 (2.4%) / 16 (2.2%) / 15.15 | 33 (5.3%) / 16 (5.1%) / 17.24 | 40 (10.4%) / 20 (10.1%) / 20.9 | 51 (97.3%) / 27 (97.4%) / 26.65 |
| nb-span | 5 | 29 (2.4%) / 16 (2.2%) / 15.15 | 33 (5.3%) / 16 (5.1%) / 17.24 | 40 (10.4%) / 20 (10.1%) / 20.9 | 53 (97.3%) / 29 (97.4%) / 27.69 |
| nb-span-context | 3 | 37 (2.4%) / 19 (2.4%) / 19.33 | 38 (4.9%) / 20 (4.9%) / 19.85 | 42 (10.0%) / 22 (9.9%) / 21.94 | 49 (97.3%) / 26 (97.4%) / 25.6 |
| nb-span-context | 5 | 37 (2.4%) / 19 (2.4%) / 19.33 | 38 (4.9%) / 20 (4.9%) / 19.85 | 42 (10.0%) / 23 (9.9%) / 21.94 | 51 (97.3%) / 28 (97.4%) / 26.65 |
| lr-span | 3 | 39 (2.4%) / 20 (2.4%) / 20.37 | 43 (5.2%) / 24 (5.3%) / 22.47 | 46 (10.2%) / 25 (10.3%) / 24.03 | 54 (97.3%) / 30 (97.4%) / 28.21 |
| lr-span | 5 | 39 (2.4%) / 20 (2.4%) / 20.37 | 44 (5.2%) / 25 (5.3%) / 22.99 | 47 (10.2%) / 26 (10.3%) / 24.55 | 61 (97.3%) / 32 (97.4%) / 31.87 |
| lr-context | 3 | 26 (2.4%) / 10 (2.3%) / 13.58 | 33 (5.2%) / 15 (5.0%) / 17.24 | 38 (10.5%) / 18 (10.0%) / 19.85 | 51 (97.3%) / 25 (97.4%) / 26.65 |
| lr-context | 5 | 27 (2.4%) / 10 (2.3%) / 14.11 | 34 (5.2%) / 15 (5.0%) / 17.76 | 39 (10.5%) / 18 (10.0%) / 20.37 | 53 (97.3%) / 28 (97.4%) / 27.69 |
| **lr-span-context (winner)** | **3** | **43 (2.7%) / 23 (2.6%) / 22.47** | **45 (5.8%) / 23 (5.5%) / 23.51** | **49 (11.3%) / 26 (10.9%) / 25.6** | 55 (97.3%) / 30 (97.4%) / 28.73 |
| lr-span-context (winner) | 5 | 43 (2.7%) / 23 (2.6%) / 22.47 | 46 (5.8%) / 23 (5.5%) / 24.03 | 50 (11.3%) / 26 (10.9%) / 26.12 | 59 (97.3%) / 32 (97.4%) / 30.83 |
| fusion-lrctx-x-lexicon / -x-nbspan (w = 0) | 3 / 5 | identical to lr-span-context | | | |

**Reading the table.**

- **The gate.** It is 52 / 70 on the reference. Reading (a) is 27 / 80, which needs T >= 0.738. Reading (b)'s
  ceiling is 18 / 80, which is T <= 0.492.
- **Wilson CI95 for the winner on the reference.**
  - 43 / 70 = 0.614 [0.497, 0.720]
  - 45 / 70 = 0.643 [0.526, 0.745]
  - 49 / 70 = 0.700 [0.585, 0.795]
  - 50 / 70 = 0.714 [0.600, 0.807]
- **Wilson CI95 for the winner on Whisper.** 23 / 70 = 0.329 [0.230, 0.445] and 26 / 70 = 0.371 [0.268, 0.489].
- **The measured false-candidate rate overshoots the budget.** It is 2.7 % against 2.3 %, 5.8 % against 5 %, and
  11.3 % against 10 %. Each theta was fitted on Fold B and carried to Fold A, and these are the rates Fold A actually
  shows.

## 2. Winner and gate verdict

**Winner (Fold B selection): `lr-span-context`.** This is a multinomial logistic span-type classifier over span plus
context n-grams, with C = 1.0. The two fusions tie with it at w = 0, and ties go to the simpler ranker.

**On perfect text it roughly halves the distance to the gate, but it does not clear 0.738 at any stated budget.**

| operating point (reference) | hits / 70 | T | c at CONV, items of 80 | reaches 27 / 80 |
| --- | ---: | ---: | ---: | --- |
| S2a.1 contract (full-TRAIN lexicon, Youden theta 0.55) | 26 | 0.371 | 13.6 | no |
| winner, 2.3 % budget, top 3 (today's FC level) | 43 | 0.614 | 22.5 | no |
| winner, 5 % budget, top 3 | 45 | 0.643 | 23.5 | no |
| winner, 10 % budget, top 3 | 49 | 0.700 | 25.6 | no |
| winner, 10 % budget, top 5 (a contract change) | 50 | 0.714 | 26.1 | no |
| winner, no threshold, top 3 (FC 97 %) | 55 | 0.786 | 28.7 | yes |
| lr-span, no threshold, top 5 (FC 97 %) | 61 | 0.871 | 31.9 | yes (the perfect-ranker ceiling) |

- **The ranking itself is nearly solved.** With no threshold, `lr-span` at top 5 recovers all 61 eligible items, the
  perfect-ranker ceiling. The winner at top 3 recovers 55 of 61.
- **What binds is abstention.** Under a budget, the misses are items whose type probability is below the global
  theta: 18 of them at 2.3 % and 10 at 10 %.
- **Fold A misses for the winner at 5 %, top 3.** 45 hits, 15 below theta, 1 not in the top 3, 7 not in the
  reference, and 2 overlapping the draft.
- **The false-candidate rate the gate costs.** This is a diagnostic read on Fold A itself, so it is optimistic. The
  highest theta that still gives 52 hits costs the winner a Fold A false-candidate rate of **15.7 %** at top 3
  (0.21 spans per call) or **12.6 %** at top 5 (0.17 spans per call). `lr-span` would need 56.3 % (top 3) or 26.9 %
  (top 5), and no lexicon ranker reaches 52 at any threshold.
- **On Whisper, no ranker reaches 52 at any threshold,** because 35 of the 70 values are not in the transcript. The
  best Whisper cell is 32 / 70, with no threshold at top 5.
- **Top-5 costs almost nothing in false-candidate rate, and buys almost nothing.** The non-empty rate is the same by
  construction. The mean candidates per call rise slightly (0.149 against 0.145 at 10 %). The gain is +0 to +1 item
  under every budget. It pays only without a threshold, where the winner goes from 55 to 59.

**Per slot type (winner, 5 % budget, top 3).** Each cell is items: hits on the reference / hits on Whisper.

| type | items | reference hits | Whisper hits |
| --- | ---: | ---: | ---: |
| place_name | 13 | 13 | 6 |
| business_name | 7 | 4 | 1 |
| date | 5 | 3 | 2 |
| person | 5 | 3 | 2 |
| media_type | 4 | 2 | 2 |
| business_type | 3 | 3 | 3 |
| device_type | 3 | 1 | 0 |
| food_type | 3 | 2 | 1 |
| list_name | 3 | 3 | 1 |
| audiobook_name | 2 | 2 | 0 |
| time | 2 | 2 | 2 |
| artist_name | 2 | 0 | 0 |
| weather_descriptor | 2 | 1 | 1 |
| 16 single-item types | 16 | 6 | 2 |
| **total** | **70** | **45** | **23** |

**Families in brief.**

- **Context adds to span identity but does not replace it.** At 5 %: context-only LR 33, span-only LR 43,
  span-plus-context LR 45.
- **NB trails LR** in every mode.
- **Neither lexicon fuses usefully with the classifier.**
- **For the real (Whisper) tool today,** the winner doubles the S2a.1 contract number: 23 / 70 = 0.33 at 2.3 %,
  against 6 / 70 (primary) and 12 / 70 (full TRAIN). Its bound is 12.0 of 80, still under the 18 / 80 line, so
  reading (b) remains predicted on Whisper.

## 3. What it implies for decision 212

**The gate is not cleared.** No ranker inside the contract reaches T >= 0.738 on the reference transcript at a
false-candidate budget of 2.3 %, 5 % or 10 %. The best budgeted cell is 50 / 70 = 0.714 (10 %, top 5), which is 2
items short. The best contract-size cell (top 3) is 49 / 70 (10 %). At today's 2.3 % level it is 43 / 70.

The S2a.1 addendum's rule applies: if no ranker clears the gate on perfect text, no ASR choice can. On this read, then,
**a stronger ASR is not worth pinning for the S2a missing-slot line under the present contract and budgets.**

**What moved.** The ranker redesign turned the bottleneck from "the ranker" into "the abstention budget".

- **Perfect ASR with the new ranker** gives c <= 22.5-26.1 of 80. That is above reading (b)'s 18 / 80 line and below
  reading (a)'s 27 / 80. A probe on perfect text would land between the two readings, rather than being predicted
  closed.
- **The remaining distance is a policy parameter,** not an unknown. The gate needs about 13-16 % false candidates
  (optimistic, read on Fold A) against the 10 % maximum stated here.

**Two paths would reopen 212.** Either is the owner's call, not this note's.

1. **Authorise a larger false-candidate budget** (about 15 %, or about 13 % at top 5), and pair it with a stronger
   ASR. On Whisper today the winner reaches only 26 / 70 even at 10 %, and 35 of the 70 values are absent from the
   transcript. A stronger ASR would have to recover nearly all 28 recoverable (i) items (the S2a.1 addendum's split)
   for the perfect-text numbers above to carry over.
2. **Keep the budget, and look for a better-calibrated abstention before any ASR is pinned.** Per-type thresholds
   were not tried here, because 181 Fold B targets over 55 types would overfit. Nor was a larger build set (for
   example, TRAIN synthetic text). The bench and its `--check` are ready for either.

**What does not change.** The Whisper large-v3 tool with the winner stays below reading (b)'s 18 / 80 line at every
budget (12.0-13.6 of 80). S2a.2 and S2a.3 remain unjustified on the pinned transcript.

## 4. What this read does not claim

- **Family 4 (embedding) was not run.** Two local text/omni embedders are pinned in the lock:
  `qwen3-embedding-0.6b-gguf` and `lco-embedding-omni-3b-gguf`. Both are servable only through `llama-server`; the
  venv has no in-process `llama_cpp` binding. That is a tool-contact class that needs its own exposure-ledger row and
  a process beside the live serving session, and it is outside this read's zero-contact scope. If the coordinator
  wants it, it is a bounded CPU-only follow-up. It would need one exposure row, embeddings of about 0.3 M TRAIN
  windows plus the fold windows, and the same bench.
- **The false-candidate rate is measured over all 55 closed types** on rows where nothing is missing. The Solver
  chooses the type itself, so realistic exposure may be lower. That would move the budget, not the ranking.
- **These are Fold A construction-roster numbers (70 items; decisions 28 and 86).** The best-cell and FC-needed
  diagnostics read Fold A itself and are optimistic. They are not selections.
- **The build uses TRAIN gold** (minus both folds) to fit the frozen classifiers, as the slot store does. The runtime
  receives no gold.

## 5. Reproduce

```bash
# WSL, model-free, CPU only; about 24 min, peak 5.3 GB
PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONPATH=src python -B \
    scripts/analysis/slurp_s2a1_recall_ceiling.py --ranker study \
    --data-root "$SPEECHRL_DATA_DIR" --lock /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
# the same with --check: IDENTICAL apart from generated_at
python -B -m pytest -q -p no:cacheprovider tests/unit/test_slurp_s2a1_recall_ceiling.py   # 15 passed
```

**Outputs.** They are under `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-S2A-RANKER-STUDY-V1/`: `report.json`, `tables.md`
and `content-sha256.json`. Per-item outcomes are recorded as ids, types, outcome codes and ranks only.

**Content hashes, with `generated_at` removed.**

- `report.json`: `a7684e7442c0c9d162a3fa63714f5e99f693c2030bfd82cc596260bcd6dc72d3`
- `tables.md`: `b249140679f7d54225673c1b053a971988ced81cad72f952b3988a8b567fe1c3`

A `--check` re-run (29 min) reported IDENTICAL apart from `generated_at`. A `--check` of the default
`--ranker trigram-lexicon` read against the S2a.1 outputs is also IDENTICAL, so the default outputs are unchanged.
