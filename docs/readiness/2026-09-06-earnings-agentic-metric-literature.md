# Earnings agentic metrics: what ConEC actually publishes, and what its scorer actually computes

Read-first note for B4 of plan revision 2. Owner ruling 2026-09-06: *"WER is not a reasonable
speech-agentic task"* — corpus WER stays the alignment anchor against the published Earnings-21
rows, and the paper-facing line for Earnings **mechanism** cells becomes entity-level metrics with
published numbers plus a semantic high-impact error rate. This note establishes the published side
of that line from primary sources. Zero model, GPU, tool, embedding and network contact beyond the
literature fetches listed below.

Every number here is quoted from the source named beside it. Where this repository has produced a
number of its own it is marked **(ours)** and never mixed into a published column.

---

## 0. Sources, and what was read first-hand

| # | source | how read | when |
|---|---|---|---|
| S1 | Huang, Yarmohammadi, Trmal, Liu, Raj, García, Ivanov, Ehlen, Yu, Rastrow, Povey, Khudanpur. **"ConEC: Earnings Call Dataset with Real-world Contexts for Benchmarking Contextual Speech Recognition"**, LREC-COLING 2024, pages 3700–3706, ELRA and ICCL, May 2024. <https://aclanthology.org/2024.lrec-main.328/> (BibTeX key `huang-etal-2024-conec`; CC BY-NC 4.0 per the paper's own footer, CC BY 4.0 per the anthology page's 2024 blanket statement) | full PDF read locally via `pdftotext -layout`; PDF sha256 `0f363d79bb1a99194cc49e9ab27740810383721b57d914bf1fda45c06b5d7482` at `$SPEECHRL_DATA_DIR/survey-fulltext/2024.lrec-main.328/2024.lrec-main.328.pdf` | 2026-09-06 |
| S2 | **ConEC data release**, <https://github.com/huangruizhe/ConEC> | the local clone under `$SPEECHRL_DATA_DIR/datasets/conec` (umbrella lock key `conec`), inspected directly: `git log`, `git ls-files`, file shapes | 2026-09-06 |
| S3 | **fstalign**, <https://github.com/revdotcom/fstalign>, Apache-2.0, branch `develop` at commit `69df0b2b357f994101d630cb3f56e22b57ebcf04` | source read first-hand: `src/wer.cpp`, `src/Walker.cpp`, `src/Nlp.cpp`, `src/AlignmentTraversor.cpp`, `docs/{Usage,NLP-Format}.md`, `docs/json_log_schema.json`, `test/data/short.sbs.txt` | 2026-09-06 |
| S4 | **Earnings-21** entity-type definitions and `.nlp` format, <https://github.com/revdotcom/speech-datasets/tree/main/earnings21> (ConEC's own footnote 6) | the local release under `$SPEECHRL_DATA_DIR/datasets/earnings21-22/earnings21` | 2026-09-06 |
| S5 | Durmus, Cen, Pacheco, Okan, Orhon. "Contextual Earnings-22: A Speech Recognition Benchmark with Custom Vocabulary in the Wild", arXiv:2604.07354, submitted 2026-03-28 | abstract page only | 2026-09-06 |
| S6 | ProfASR-Bench, arXiv:2512.23686 | prior program deep read, `wiki/survey/workbench/2026-08-16-deep-reading-adversarial-check/cluster-c-biasing.md` §C-4 | 2026-08-16 |

**Two things the ConEC release does NOT ship**, checked directly rather than assumed (S2): the
repository holds **514 tracked files, of which exactly one is not data** — `README.md`. There is
**no scorer code, no metric script and no LICENSE file** in it. The metric implementation the paper
used is therefore third-party (fstalign, S3) and the ASR baselines live in `k2-fsa/icefall`. This is
the fact that decides how the metric can be reproduced here at all (§4).

---

## 1. What ConEC is, in one paragraph

ConEC augments the existing Earnings-21/22 corpora with real, pre-existing context materials.
**Earnings-21 (44 calls, mean 54 min, 17 min to 1 h 34) is the evaluation set; Earnings-22 (about
119 h, 125 files, accented English from 7 regions) is offered as train/dev** (S1 §3). The added
layers are: presentation slides and earnings releases downloaded from the companies' investor
relations pages; participant names and affiliations scraped from Seeking Alpha; corrected `.nlp`
transcripts (the release's `<unk>` / `<inaudible>` tokens and misspelled entity names replaced from
the S&P Capital IQ transcription by Levenshtein alignment); word-level timestamps; and sentence-level
segmentation. The context material is used as **"a bag of uncased, unigram words"**, about **100 to
2000 words per call**, active globally for every utterance of that call — no per-utterance selection,
no speech conditioning, no filtering. The baseline system is a **71.5 M-parameter zipformer
transducer trained on normalized SPGISpeech**, biased by **shallow fusion**
`W* = argmax log P(W|X) + λ log P_C(W)` in icefall.

---

## 2. The metric definitions, exactly as published

### 2.1 What the paper says, verbatim

S1 §4.1 states the entire metric protocol in three sentences:

> "We use the fstalign⁸ tool to evaluate overall WER, WER for common/rare words, and WER for each
> entity types. An ideal system should reduce rare words and entities WER without hurting common
> words WER. Hypothesis and reference texts are normalized with Whisper normalizer⁹ before being fed
> into fstalign."

with footnote 8 = `https://github.com/revdotcom/fstalign`, footnote 9 =
`https://github.com/kurianbenoy/whisper_normalizer` (a repackaging of OpenAI Whisper's
`EnglishTextNormalizer`), and footnote 6 pointing the entity taxonomy at the Earnings-21 release's
own definitions.

Three definitional consequences, each load-bearing:

1. **There is no entity F1, precision or recall in ConEC.** Table 2's only per-entity quantity is a
   WER. Any "ConEC entity F1" would be an invention. Accordingly this study registers no
   `conec-entity-...-f1` scorer.
2. **Rare words are defined against the ASR model's own training text**: *"We define rare words to
   be the words with frequency below top-3k in the SPGISpeech training text, which accounts for 10 %
   of total tokens. Around 70 % of named entities are rare words."* (S1 §4.2). That definition is
   **not portable** to a frozen general-purpose omni core, which has no SPGISpeech training text; the
   common/rare split is therefore reported here as a published column only and is never computed for
   our own outputs.
3. **Numeric entities are excluded.** *"Similar to SPGISpeech, we omit all numeric entities for the
   time being, and leave number normalization as a future work."* (S1 §3.2). ConEC's per-entity
   columns are exactly the **eight non-numeric types** of Table 1.

### 2.2 What the metric therefore is, from fstalign's own source (S3)

The paper delegates the definition to a tool, so the definition lives in that tool's source. Read at
commit `69df0b2b357f994101d630cb3f56e22b57ebcf04`:

* **Error counting.** `src/wer.h::WerResult` — `NumErrors() = insertions + substitutions +
  deletions`; `WER() = NumErrors() / numWordsInReference`. Corpus aggregation is a **count ratio**,
  never a mean of per-file rates.
* **Entity accounting, `src/wer.cpp::RecordTagWer`.** For every aligned stitch that carries a
  non-empty `wer_tags` list, each tag id accumulates `insertions`, `deletions`, `substitutions`, and
  `numWordsInReference += 1` **unless the stitch is an insertion**. An insertion stitch has no NLP
  row, so its `wer_tags` list is empty and the loop body never runs for it: **fstalign attributes no
  insertion to any entity**. Its own committed fixture confirms this — in `test/data/short.sbs.txt`
  every `<ins>` row has an empty `Wer_Tag_Entities` column. So the per-entity number is
  `(S + D) / (tagged reference words)`.
* **Entity class.** `src/Nlp.cpp::NlpFstLoader` fills each tag's `entity_type` from the
  `wer_tag.json` sidecar, keyed by tag id. A reference token may carry several tag ids and is then
  counted once per id.
* **A second, different per-class block exists.** `src/wer.cpp::RecordWer` builds a `classWER` report
  from the `.nlp` **`tags`** column instead (class-label spans `___<id>_<CLASS>___`, insertions
  inside a span *are* attributed there). ConEC's per-entity table can only have come from the
  `wer_tags` path on our reference layer — see §4.2 for the measurement that settles it.
* **Alignment.** `src/Walker.cpp` walks an OpenFST composition for a minimum-cost path with
  unit-cost insert/delete/substitute arcs, i.e. a shortest-path formulation of the same edit distance
  a Levenshtein aligner minimizes.

### 2.3 Normalization

Both sides pass through Whisper's `EnglishTextNormalizer` before alignment. That normalizer expands
spelled numbers to digits, unifies currency and percentages, strips thousands separators, expands
contractions and honorifics, removes bracketed spans and the filler set `hmm|mm|mhm|mmm|uh|um`, and
unifies British/American spellings. This repository already vendors it byte-for-byte at upstream tag
`v20240930` under `src/speech_aware_evidence_acquisition/reproduction/whisper_normalizer/` (per-file
SHA-256s in that package's `PROVENANCE.md`), which is the same normalizer family ConEC's footnote 9
points at.

---

## 3. The published numbers

### 3.1 Table 1 — entity counts and context coverage (S1 §3.2)

"Coverage" is the percentage of **spoken entity tokens** (not types) present in the ConEC context for
that call. Total spoken tokens in Earnings-21 are given as 364 k.

| entity type | coverage | tokens | entity type | coverage | tokens |
|---|---:|---:|---|---:|---:|
| PERSON | 82 % | 3,340 | PRODUCT | 39 % | 671 |
| ORG | 66 % | 6,362 | EVENT | 39 % | 575 |
| GPE | 61 % | 1,605 | NORP | 39 % | 201 |
| LOC | 48 % | 532 | FAC | 29 % | 181 |

*"From Table 1, PERSON and ORG have the highest coverage after including names and affiliation
information. Otherwise, the coverage is only 30 % and 56 % for PERSON and ORG from the slides and
earnings releases."* — the participant roster is what carries PERSON coverage.

### 3.2 Table 2 — Earnings-21 WER (%) by system and context condition (S1)

All rows are the authors' own measurements. `*` = the improvement over row 1 is statistically
significant at p < 0.05 (their Appendix A). "None" is the non-entity column. Rows 1–5 are the same
71.5 M zipformer under different biasing contexts; rows 6–8 are Whisper without any biasing.

| row | context | WER (common / rare) | None | PERSON | ORG | GPE | LOC | PROD. | EVENT | NORP | FAC |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | **no biasing** | 10.41 (8.71 / 26.02) | 9.40 | 45.9 | 29.5 | 18.8 | 5.85 | 24.2 | 43.1 | 9.55 | 28.7 |
| 2 | Le et al. (2021) synthetic — per-utterance gold rare words + 500 distractors | 10.08 (8.62 / 23.43) | 9.18 | 40.7* | 25.6* | 17.8* | 5.26 | 20.2* | 42.3 | 8.04 | 25.4* |
| 3 | Fox & Delworth (2022) synthetic — gold PERSON+ORG for all calls + Fortune-500/CEO distractors, one shared 3,066-word list | 10.22 (8.62 / 24.80) | 9.35 | 38.9* | 25.3* | 19.2* | 5.65 | 23.5 | 41.9 | 10.1 | 29.8* |
| 4 | **ConEC real — slides + earnings release + participant roster** | 10.29 (8.70 / 24.84) | 9.39 | 39.8* | 26.1* | 18.4 | 5.65 | 21.9* | 43.1 | 9.55 | 28.7 |
| 5 | **ConEC oracle** — row-1 output with entity words replaced by the correct ones *if present in the context* | 9.69 (8.71 / 18.72) | 9.25 | 13.0* | 17.7* | 12.9* | 5.46 | 19.2* | 35.6* | 5.53* | 16.6* |
| 6 | Whisper tiny (39 M), no biasing | 19.16 (16.79 / 40.62) | 18.4 | 61.1 | 47.8 | 31.1 | 18.9 | 46.1 | 8.00* | 25.1 | 54.1 |
| 7 | Whisper base (74 M), no biasing | 14.67 (12.72 / 32.37) | 13.9 | 51.5 | 40.1 | 25.9 | 14.8 | 35.5 | 7.30* | 18.1 | 48.1 |
| 8 | **Whisper large (1550 M), no biasing** | 7.98 (6.94 / 17.43) | 7.50 | 28.9* | 19.6* | 17.0* | 5.85 | 18.7* | 2.78* | 8.54* | 21.6 |

Readings the authors themselves draw, and the one that matters for evidence-supply work: **row 3 is
the harmful-supply datapoint** — a shared, distractor-heavy list improves PERSON and ORG but pushes
GPE (19.2), NORP (10.1) and FAC (29.8) *above* the no-context row. Row 4, the real context, is
provenance-clean and beats row 3 on the non-target types but is weaker than row 2 overall, and it
raises the common-word and non-entity WER — *"which indicates such real-world contexts are
noisier"*. Row 5 is an **upper bound on what any consumer of these contexts can reach**, not a
system: it is a post-hoc oracle substitution over row 1's output.

**There is no "participant names only" WER row in ConEC.** The roster's contribution is published
only as the coverage delta in §3.1 (PERSON 30 % → 82 %, ORG 56 % → 66 %). Any comparison of a
names-only arm against a published ConEC row is therefore a comparison against row 4 (roster
included) or nothing.

### 3.3 Table 3 — LibriSpeech sanity check for the shallow-fusion baseline (S1)

Reported so the biasing implementation is not confounded with the corpus. Not an Earnings number.

| system | test-clean all / com / rare | test-other all / com / rare |
|---|---|---|
| no biasing | 2.17 / 1.25 / 9.65 | 5.22 / 3.32 / 21.83 |
| shallow fusion | 1.59 / 1.26 / 4.22 | 4.11 / 3.32 / 11.05 |
| Yang et al. (2023) | 2.00 / – / – | 4.45 / – / – |

### 3.4 Corpus-WER numbers reported beside, and what ConEC does *not* report

ConEC's own corpus-WER column is the "WER" column of Table 2: **10.41** for the unbiased zipformer
and **7.98** for Whisper large, both on all 44 Earnings-21 files, **sentence-segmented**, under the
Whisper normalizer, through fstalign.

**ConEC reports no ESB numbers and no Earnings-22 WER at all** — Earnings-22 is offered as a
train/dev resource, not scored. The Earnings-21/22 corpus-WER rows this study aligns against come
from elsewhere and are tracked in umbrella
`wiki/experiments/speech-aware-evidence-acquisition/published-baselines.md`: whisper-large-v3 **9.71**
(Open ASR Leaderboard long-form, all 44), Whisper large-v2 **9.7** (Whisper paper App. D.4), TRADE
**9.75** and FastConformer FT+LCA+GT **13.84** (arXiv:2606.08486 Table 2), the Whisper degraded
floors medium.en **10.2** / small.en **10.8** / base.en **12.5** / tiny.en **17.0**, and
Qwen2-Audio-7B **26.06** (FinAudio, normalizer unnamed — a floor only). None of those is
fstalign-scored, and **none is comparable to ConEC's 7.98/10.41**, which are sentence-segmented: on
ConEC's own numbers, Whisper large sits at 7.98 segmented against roughly 10.3 whole-file, so about
**2.3 points of any overall-WER gap is segmentation, not system**.

### 3.5 Third-party work that reports on or beside ConEC

Distinguished from the authors' own numbers, and thin: ConEC is a 2024 resource whose entity table
has not, as far as this sweep found, been reproduced by anyone else.

| source | relation | what it reports |
|---|---|---|
| Siskos et al., EMNLP-F 2025, arXiv:2509.19567 | same corpus, different context pipeline; **not** ConEC's metric | Earnings-21 WER: no-context 35.9, CB-RAG 31.1, CB-LLM 31.8, oracle 29.7 — a black-box ASR + context pipeline, corpus WER only, no per-entity table |
| ProfASR-Bench, arXiv:2512.23686 (preprint) | adjacent benchmark; defines **NE-WER and Entity-F1** | synthetic TTS speech, Whisper tiny/base/small + Qwen2.5-Omni-3B; Whisper-small 9.98 no-prompt / 9.95 profile / 9.92 oracle — an oracle gain of ~0.06 pp, its "context-utilization gap" claim |
| Contextual Earnings-22, arXiv:2604.07354 (2026-03-28, S5) | adjacent Earnings-22 custom-vocabulary benchmark | abstract read only; reports no ConEC row and no per-entity table on the abstract page |
| RECOVER, arXiv:2603.16411 (preprint, no code) | LLM correction pipeline over 5 sets incl. Earnings-21 | relative entity-WER reduction 8–46 %, recall up to +22 pp; not a ConEC row |

---

## 4. What can and cannot be reproduced here, and why

### 4.1 The official metric code cannot be run

fstalign is a C++/OpenFST program. This repository's standing rule, carried in every Earnings verdict
since 2026-09-04, is that **fstalign is not installed and was not run**; installing and building it
(plus OpenFST) is outside this study's dependency envelope, and the 2026-09-04 alignment audit and
the full-44 verdict both state explicitly that *"nothing here is comparable to ConEC's fstalign-based
Table 2"*. There is also nothing to vendor from the ConEC release itself (§0: one non-data file).

So the metric registered by this task is a **definition mirror**, not an executed official metric:
`reproduction/conec_entity_scoring.py` transcribes `RecordTagWer`'s accounting from the pinned
fstalign source, and every aggregate it emits carries `official_tool_run: false` plus the pinned
`definition_source`, so no downstream table can quote it as an official run by accident. Its two
named differences from fstalign — a Levenshtein aligner instead of an FST shortest path, and
whole-string rather than cell-wise Whisper normalization — are stated in that module's own docstring
and in §4.3 below.

### 4.2 The entity layer: `wer_tags`, not `tags` — measured, not assumed

fstalign offers two per-class paths (§2.2). On the reference layer this study actually scores against
(`earnings21-original`, the Rev release, D1-hash-pinned — **not** ConEC's corrected `.nlp` files), the
`tags` column carries **no named-entity classes at all**. Measured on call `4330115` (S4):

| layer | tokens carrying a label | classes observed |
|---|---:|---|
| `tags` column, Rev original | 285 of 6,602 | CONTRACTION 155, CARDINAL 49, FALLBACK 24, PERCENT 19, YEAR 13, ABBREVIATION 10, MONEY 6, ALPHANUMERIC 6, ORDINAL 2, WEBSITE 1 |
| `wer_tags` column + sidecar, Rev original | 886 of 6,602 | includes PERSON, ORG, GPE, LOC, PRODUCT, EVENT, NORP, FAC — ConEC Table 2's eight columns |
| `tags` column, ConEC corrected | 955 of 6,612 | DATE 408, CONTRACTION 145, MONEY 87, GPE 81, ORG 77, PERSON 55, … (ConEC re-populated it) |

ConEC's own corrected release populates `tags` densely; the Rev original does not. On our pinned
layer only the `wer_tags` path can express the published table, and it is the same annotation
(`wer_tag.json` sidecar) `entity-wer` already consumes.

### 4.3 The four differences a ConEC comparison must carry

Any Earnings cell that quotes a ConEC row beside one of ours must state all four:

1. **Segmentation.** ConEC scores sentence-segmented audio; we score whole calls in fixed 90-second
   windows. ConEC's own Whisper-large row moves about 2.3 points between the two regimes.
2. **Reference text.** ConEC scores against its **corrected** `.nlp` files (S&P-repaired entity
   names); we score against the **original Rev** `.nlp` files, which is what D1 pins and what the
   sealed 8.200 was computed on. ConEC's whole §3.1 is an argument that the original contains wrong
   entity names — so on the entity columns specifically, our reference is the harder, noisier one.
3. **System class.** ConEC rows 1–5 are a 71.5 M zipformer trained **in-domain** on SPGISpeech, plus
   beam-search score access for shallow fusion. Only row 8 (Whisper large, no biasing) is comparable
   in kind to a frozen general model reached across an API boundary; rows 6–8 are the honest
   comparison set for us, and row 1 is the biasing floor.
4. **Aligner and normalizer granularity.** §4.1.

### 4.4 Support, and which published cells are directional only

ConEC's own per-class supports are the Table 1 token counts: FAC 181, NORP 201, LOC 532, EVENT 575,
PRODUCT 671. Any per-class comparison on those five is directional at best; PERSON (3,340), ORG
(6,362) and GPE (1,605) carry real weight. The same caveat applies from our side with our own gold
mention counts.

---

## 5. What this note fixes for the metric definitions that follow

* The ConEC entity metric is **`(S + D) / tagged reference words`, per `wer_tags` entity id, pooled by
  the sidecar's `entity_type`, insertions unattributed** — from fstalign's source, not from a guess.
* **Comparable published cells** for a bare frozen core with no biasing are **Table 2 row 8** (Whisper
  large, no biasing) as the target and **Table 2 row 1** as the biasing floor; row 5 is the
  context-supply ceiling; rows 2 and 3 are the synthetic-supply comparators, one of which is the
  published harmful-supply datapoint.
* **No entity F1 exists to mirror**, and **no names-only WER row exists to compare against**.
* **Numeric entities are outside ConEC's table by the authors' own choice**, which is exactly the gap
  `numeric-value-accuracy-v1` fills — it is a complement to ConEC's eight columns, never a
  reproduction of them.
* The **common/rare split is not portable** to a frozen general core and is not computed here.
