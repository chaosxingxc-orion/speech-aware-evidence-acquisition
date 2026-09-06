# Earnings-21 agentic-metric baseline v1 — the comparator every Earnings mechanism cell pairs against

Owner ruling, 2026-09-06: **"WER is not a reasonable speech-agentic task."** Corpus WER stays the
alignment anchor against the published Earnings-21 rows; the paper-facing line for Earnings
**mechanism** cells becomes entity-level metrics with published numbers plus a semantic high-impact
error rate. This note registers those metrics' values on the bare frozen core.

Zero model, GPU, tool, embedding, network and audio contact; no Earnings-22 read. Exposure row
`SAEA-E21-MF-AGENTIC-METRIC-BASELINE-V1`, registered and committed before the first scorer touched a
reference. Receipts:
`docs/checks/speech-aware-evidence-acquisition/2026-09-06-e21-agentic-metric-baseline/`
(`MANIFEST.sha256`). Literature and the metric definitions read out of primary sources:
`docs/readiness/2026-09-06-earnings-agentic-metric-literature.md`.

| | |
|---|---|
| source | `SAEA-E21-FULL44-DIRECT-BASELINE-V2`, attempt `attempt-20260904T233816Z-bcd338`, study commit `44db2e9d` |
| population | all 44 `earnings21-original` discovery calls, 39.263 h, 1,593 fixed 90-second windows, split identity `fcc1b0bc…d69e` |
| arm | `bare-core` — no evidence, no ConEC context, no roster, no bias list; greedy; Q4_K_M on build `04ccc72a` |
| scoring path | `core.scoring_batch`, three complete verified manifests, one process each, never sharded (3 of 3 succeeded; 647.4 s / 528.6 s / 5.8 s) |
| metrics | `asr-wer-whisper` (anchor), `conec-entity-wer-official`, `numeric-value-accuracy-v1`; `semantic-high-impact-error-rate-v1` registered and **awaiting its taxonomy** |

---

## 1. The identity anchor holds to the digit

The re-scoring bundles are byte-identical copies of the sealed artifacts whose manifests differ from
the sealed one **only** in artifact paths and the `scorers` list, so this is a claim about the same
run, not a re-measurement of it. Two independent checks agree:

| check | sealed 2026-09-04 | this re-score |
|---|---:|---:|
| `asr-wer-whisper` corpus WER, all 44 | 8.200 % | **8.200 %** |
| substitutions / deletions / insertions | 13,098 / 5,701 / 10,700 | **13,098 / 5,701 / 10,700** |
| reference words | 359,765 | **359,765** |
| per-call rows differing on WER, S, D or I | — | **0 of 44** |
| `conec-entity-wer-official`'s own `__ALL__` bucket | — | **8.200 %** |

The last row is the ConEC mirror's built-in anchor: a different function, over the same
whole-string-normalized sequences, lands on the same corpus figure. If a future edit to the mirror's
alignment or normalization drifts, that bucket moves and the drift is visible without anyone
remembering to check.

## 2. The three metrics, all 44 and on the E5 split

The **E5 split** separates the ten calls of the frozen `r4-e21-sub10` evaluation roster (the
2026-08-14/15 N10 arms and every read since are on them) from the 34 kb-construction calls
(`SAEA-BENCH-kb34-floor`, 2026-08-14). Reported apart so a mechanism cell can never quote a
construction-contaminated number as an evaluation one.

| roster | calls | corpus WER % | ConEC overall WER % | ConEC non-entity WER % | numeric accuracy % | numeric values |
|---|---:|---:|---:|---:|---:|---:|
| **all 44** | 44 | **8.200** | 8.200 | 4.730 | **90.73** | 9,734 |
| construction 34 | 34 | 8.470 | 8.470 | 4.946 | 90.22 | 7,488 |
| evaluation 10 | 10 | 7.185 | 7.185 | 3.917 | 92.43 | 2,246 |

The evaluation ten are the easier half on every metric, by the same margin the sealed verdict already
recorded for corpus WER (7.185 against 8.470). **A mechanism cell on the ten must be compared against
the 7.185 / 92.43 column, never against the corpus column.**

## 3. ConEC's per-entity WER, with the published numbers beside it

`conec-entity-wer-official` is a **definition mirror**, not an executed official metric: ConEC's
metric tool is fstalign, a C++/OpenFST binary this repository does not install and has never run, and
the ConEC release ships no scorer code at all. The definition is transcribed from fstalign's own
source at commit `69df0b2b` — `(S + D) / tagged reference words`, per `wer_tags` entity id, pooled by
the sidecar's `entity_type`, **insertions unattributed** — and every aggregate carries
`official_tool_run: false` with the pinned `definition_source`.

**Condition.** Our arm is `bare-core` with no evidence of any kind, so it is the **no-context**
condition. The two published rows it belongs beside are ConEC Table 2 **row 1** (their in-domain
71.5 M zipformer, no biasing — the biasing floor) and **row 8** (Whisper large, no biasing — the only
published row comparable in kind to a frozen general model). Row 5 (the post-hoc oracle over row 1's
output, entity words replaced where the context contains them) is the **ceiling any ConEC-context
supply arm could reach**, not a system.

| class | **ours, no context** | ref words | ConEC row 8 Whisper-large | ConEC row 1 no biasing | ConEC row 5 oracle |
|---|---:|---:|---:|---:|---:|
| PERSON | **22.5** | 2,917 | 28.9 | 45.9 | 13.0 |
| ORG | **17.2** | 4,363 | 19.6 | 29.5 | 17.7 |
| GPE | **18.7** | 1,537 | 17.0 | 18.8 | 12.9 |
| LOC | **2.5** | 485 | 5.85 | 5.85 | 5.46 |
| PRODUCT | **19.2** | 390 | 18.7 | 24.2 | 19.2 |
| EVENT | **2.4** | 494 | 2.78 | 43.1 | 35.6 |
| NORP | **9.7** | 236 | 8.54 | 9.55 | 5.53 |
| FAC | **21.3** | 122 | 21.6 | 28.7 | 16.6 |
| overall WER | **8.200** | 359,765 | 7.98 | 10.41 | 9.69 |
| non-entity | **4.730** | 304,331 | 7.50 | 9.40 | 9.25 |

Read carefully, and with §5's four caveats attached to every cell:

* **Every one of the eight classes is within 3 points of Whisper large**, and five are better:
  PERSON −6.4, LOC −3.35, ORG −2.4, EVENT −0.4, FAC −0.3. The three that are worse are worse by 1.7
  (GPE), 1.2 (NORP) and 0.5 (PRODUCT).
* **Seven of the eight beat ConEC row 1**, the in-domain biasing floor, by 0.1 (GPE) to 40.7 (EVENT)
  points. The exception is NORP, worse by 0.15 on 236 reference words — level, not a gap.
* **The two aggregate rows are not like-for-like and must not be quoted as if they were.** Our
  `__ALL__` bucket includes insertions (it is the corpus WER) while our `__NON_ENTITY__` bucket, like
  every entity bucket here, excludes them, because fstalign's `RecordTagWer` cannot attribute an
  insertion to a tag. Our 4.730 non-entity figure is therefore an `(S + D)` rate and ConEC's 9.40 is
  not; the honest same-family comparison for it is our own `(S + D) / reference words` over the whole
  corpus, 5.225 %. The insertion-heavy profile the sealed verdict already recorded (10,700 insertions
  against 5,701 deletions) is what separates the two.
* **ORG at 17.2 is below ConEC's own oracle ceiling of 17.7** — the frozen core with no context
  already reaches, on that class, what row 1 could reach only by having its entity words replaced from
  the context. That bounds how much a ConEC-supply arm can be expected to win on ORG, and it is the
  single most useful number in this table for planning the Earnings mechanism ladder.
* **PERSON is the open class**: 22.5 sits between row 8 (28.9) and the oracle (13.0), and ConEC's own
  Table 1 says the participant roster is what carries PERSON coverage (30 % → 82 %). If any Earnings
  supply mechanism has room, it is here.
* **This flatly contradicts the 2026-09-04 audit's per-class reading**, and the difference is the
  metric, not the system. That audit used `entity-wer` — mention-level `1 − recall` under
  `normalize_text_v1`, where a mention counts correct only if *every* one of its tokens survives — and
  concluded PRODUCT, NORP and FAC failed ConEC's own floor. Under ConEC's actual token-level
  definition and the Whisper normalizer, none of them does. The audit's numbers were never wrong about
  what they measured; they were not the published metric family. `entity-wer` stays registered and
  unchanged, and stays this repository's own recall-flavoured view.

The full 30-class table (including the numeric, temporal and orthographic classes ConEC omits) is in
`verdict/result-summary.json`. The largest of them: CONTRACTION 4.83 % over 17,667 words, DATE 3.47 %
over 16,166, CARDINAL 11.00 % over 4,463, ABBREVIATION 25.68 % over 2,566, YEAR 19.49 % over 1,180.

**Support.** FAC (122 reference words), NORP (236), PRODUCT (390), LOC (485) and EVENT (494) are thin
on our side, exactly as they are thin on ConEC's (their Table 1 counts 181, 201, 671, 532, 575 spoken
tokens). Those five rows are directional; PERSON, ORG and GPE carry real weight.

## 4. Numeric-value accuracy — the gap ConEC leaves open

ConEC omits numeric entities by the authors' own choice. `numeric-value-accuracy-v1` is the
complement, not a reproduction: the share of the reference's digit-bearing words (after the Whisper
normalizer, which is what turns spelled numbers, currency, percentages and dates into digit-bearing
tokens at all) that the hypothesis reproduces exactly, bag-matched per call and pooled.

**90.73 % over 9,734 numeric values on all 44 calls**, against 4.73 % non-entity WER on the same
transcripts — i.e. the numbers are roughly **twice as likely to be wrong as the surrounding words**
(9.27 % missed against 4.73 % non-entity error), which is the concrete form of "earnings calls are
number-dense and the numbers are the payload".

| kind | accuracy % | expected | matched | in hypothesis |
|---|---:|---:|---:|---:|
| ordinal | 98.96 | 2,111 | 2,089 | 2,134 |
| year | 92.91 | 1,002 | 931 | 1,058 |
| other | 90.52 | 116 | 105 | 124 |
| percent | 88.60 | 1,395 | 1,236 | 1,380 |
| integer | 88.34 | 4,030 | 3,560 | 4,057 |
| currency | 85.18 | 992 | 845 | 904 |
| decimal | 75.00 | 88 | 66 | 86 |

**Currency and decimals are the weak kinds** — 85.2 % and 75.0 % — and they are the two that carry
financial magnitude. 911 numeric values appear in the hypotheses that are not in the references
(`spurious_numeric_words`), consistent with the insertion-heavy profile the sealed verdict already
recorded (10,700 insertions against 5,701 deletions).

## 5. Caveats that travel with every ConEC comparison

Four differences, all named in the literature note's section 4.3, and none of them removable from
here:

1. **Segmentation.** ConEC scores sentence-segmented audio; we score whole calls in fixed 90-second
   windows. On ConEC's own numbers Whisper large moves about 2.3 points between the two regimes
   (7.98 segmented against roughly 10.3 whole-file), so the *overall* WER row is the one most affected
   and the per-entity rows the least.
2. **Reference text.** ConEC scores against its **corrected** `.nlp` files, with `<unk>`,
   `<inaudible>` and misspelled entity names repaired from the S&P transcription. We score against the
   **original Rev** files, which D1 pins and which the sealed 8.200 was computed on. ConEC's own §3.1
   is an argument that those originals contain wrong entity names — so on the entity columns
   specifically our reference is the harder one, and this cuts against us, not for us.
3. **System class.** ConEC rows 1–5 are a 71.5 M zipformer trained in-domain on SPGISpeech with
   beam-search score access. Only row 8 is comparable in kind to a frozen general model behind an API
   boundary.
4. **Aligner and normalizer granularity.** fstalign walks an OpenFST composition; we use the frozen
   unit-cost Levenshtein re-expressed as an operation trace, asserted equal to `scoring.wer.align` on
   fixed and randomized inputs. Both minimize the same edit distance so the totals agree, but where
   several minimal alignments exist a given error can land on a different token, which can move a thin
   class by a word or two. And ConEC necessarily normalized cell-wise (fstalign consumes per-token
   rows); we normalize whole strings so the anchor holds, and carry entity labels across from a
   run-chunked normalization. **1,479 reference words of 359,765 (0.41 %) could not be labelled by
   that transfer** and are reported as `__UNLABELLED__` rather than silently called non-entity; their
   own WER is 12.85 %, higher than the corpus average, exactly as expected for the positions where the
   two normalizations disagree (multi-word number merges).

**Nothing here is an alignment verdict.** The owner's 3-point rule was applied to Earnings-21 corpus
WER on 2026-09-04 and that verdict (ALIGNED, 8.200 against whisper-large-v3's 9.71) is unchanged and
unaffected. The per-class table above is a comparison across four stated differences, not a
reproduction, and no claim of superiority or generality is made from it.

## 6. The semantic high-impact error rate is registered and waiting

`semantic-high-impact-error-rate-v1` is implemented, tested against a synthetic taxonomy, and
registered — and it produced **no Earnings-21 value when this note was written**. Its taxonomy is the
deliverable of the Earnings-22 semantic scan (branch `wt/e22`, in progress) and had not landed; the
scorer fails closed by name until `docs/taxonomies/semantic-high-impact/ACTIVE.json` exists, and a
test asserted that path was absent from this checkout so the wait stayed visible.

**Superseded 2026-09-06 by §9.** The taxonomy landed, the metric has an Earnings-21 value, and the
absence test is replaced by one that asserts the committed file is the projection.

The file contract the scan must satisfy is in
`src/speech_aware_evidence_acquisition/reproduction/semantic_impact.py`: schema
`saea-semantic-impact-taxonomy-v1`, a `levels` list with a named `high_level`, and a `rules` list of
`{id, level, ref, hyp}` where `ref`/`hyp` are exact Whisper-normalized words, the wildcard `*`, or the
sentinel `<deleted>`. Lookup is by exact key in one fixed order of decreasing specificity, a duplicate
key is a load-time error, and an unmatched error instance is counted as unclassified rather than
assumed LOW. When it lands, this metric's Earnings-21 value is one more `core.scoring_batch` job over
the same sealed bundle — no new code.

## 7. The comparator identity

Every Earnings mechanism cell from now on pairs against **this** row, by name:

> **`SAEA-E21-MF-AGENTIC-METRIC-BASELINE-V1`** — the bare frozen Qwen3-Omni-30B-A3B-Instruct Q4_K_M
> core, no evidence, fixed 90-second windows, greedy, build `04ccc72a`, on all 44
> `earnings21-original` discovery calls (split identity `fcc1b0bc…d69e`), scored through
> `core.scoring_batch`'s verified path: **corpus WER 8.200 %**, **ConEC-mirror entity WER** PERSON
> 22.5 / ORG 17.2 / GPE 18.7 / LOC 2.5 / PRODUCT 19.2 / EVENT 2.4 / NORP 9.7 / FAC 21.3, non-entity
> 4.730, **numeric-value accuracy 90.73 %**. On the evaluation ten alone: corpus WER 7.185 %, numeric
> accuracy 92.43 %.

Pairing rules, so a later cell cannot drift:

* **Same roster.** A cell on the evaluation ten pairs against the evaluation-ten column; a cell on all
  44 pairs against the all-44 column. The construction 34 are a diagnostic surface, never an
  evaluation claim.
* **Same scorers, same path.** `asr-wer-whisper`, `conec-entity-wer-official` and
  `numeric-value-accuracy-v1` through `core.scoring_batch` off a manifest that declares them —
  never an out-of-band scorer read.
* **The headline for a mechanism is the entity and numeric line, not corpus WER.** Corpus WER stays
  reported, as the anchor against the published rows and as a harm check: a mechanism that improves
  entities while moving corpus WER by more than the 0.05-point build-and-audio-path noise the sealed
  verdict measured has to say so.
* **`entity-wer` (mention-level `1 − recall`, `normalize_text_v1`) stays registered and stays
  reportable**, but it is this repository's own view and is never quoted against a ConEC row.

## 8. Per-call table

All 44 calls, with the roster label, in
`docs/checks/speech-aware-evidence-acquisition/2026-09-06-e21-agentic-metric-baseline/verdict/per-call-table.md`.
Columns: corpus WER, ConEC entity WER pooled over the eight published classes, that pool's reference
words, numeric-value accuracy, numeric values, and the per-call `__UNLABELLED__` residue.


---

## 9. 2026-09-06 — the semantic high-impact rate, measured

The taxonomy landed and the fourth metric has a value. Row
`SAEA-E21-MF-SEMANTIC-IMPACT-BASELINE-V1` (`model-free-check`), registered and committed before the
scorer touched a reference; **zero model, GPU, tool, embedding, network and audio contact**; no
Earnings-22 read. One more `core.scoring_batch` job over the same sealed re-scoring bundle §1 used —
one complete verified manifest, one process, 568.1 s, never sharded. Receipts:
`docs/checks/speech-aware-evidence-acquisition/2026-09-06-e21-semantic-impact-baseline/`; taxonomy
receipt `.../2026-09-06-semantic-impact-taxonomy/`.

**Read the next paragraph before reading the table.** The taxonomy is a mechanical projection of the
Earnings-22 scan's committed *content-impact* model onto the exact-key `(reference word, hypothesis
word)` shape this metric looks rules up by, and two of that model's three HIGH triggers do not
survive the projection: a digit-bearing token is an open class after Whisper normalization, and the
entity trigger is a per-call inventory rebuilt from that call's own references. Both were left out
rather than approximated. **So the HIGH tier below is the scan's NEGATION trigger alone, the figure
is a negation-critical error rate, and it is a strict lower bound on the scan's own content-impact
HIGH rate — never quote it as the scan's 1.92 % agentic error rate.** On this carrier the two missing
triggers are already carried, on gold annotations rather than heuristics, by
`numeric-value-accuracy-v1` (§4) and `conec-entity-wer-official` (§3).

| roster | calls | reference words | **negation-critical %** | HIGH words | LOW % | NONE % | unclassified |
|---|---:|---:|---:|---:|---:|---:|---:|
| **all 44** | 44 | 359,765 | **0.0278** | 100 | 3.272 | 1.926 | 0 |
| construction 34 | 34 | 284,014 | 0.0303 | 86 | 3.384 | 2.027 | 0 |
| evaluation 10 | 10 | 75,751 | **0.0185** | 14 | 2.853 | 1.547 | 0 |

**The decomposition closes on a number §5 already published.** The three levels partition the
substitution-plus-deletion reference-word mass and nothing else: 100 + 11,771 + 6,928 = 18,799 = the
sealed S 13,098 + D 5,701, i.e. 5.226 % against the 5.225 % §5 computes as this arm's own
`(S + D) / reference words`. Zero reference words reached `__UNCLASSIFIED__`, so the taxonomy is
total over what this corpus contains — a partial taxonomy would have shown up here rather than
silently under-reporting.

What the level split says about this carrier, stated as a decomposition of that 5.225 points and not
as a claim: **1.926 points (36.9 %) is function-word-only churn** the scan calls impact-NONE — an
article for an article, a dropped `the` — **3.272 points (62.6 %) is ordinary wording**, and
**0.028 points (0.53 %) changes a negation**. Insertions carry no reference mass and are counted
separately: 10,700 of them, of which **56 are negation-critical**. An inserted function word is
reported LOW here where the scan says NONE, which is the one representational deviation and moves no
rate.

**As a guard it is weak, and a mechanism cell must not lean on it.** 100 HIGH reference words on all
44 calls, **14 on the evaluation ten**, and **15 of the 44 calls carry none at all**. A cell can move
this by a handful of words. The Earnings harm guards with real power stay corpus WER
non-inferiority (§7) and numeric-value accuracy (§4); the negation-critical rate is reported beside
them as a directional check and as the level decomposition above.

**The comparator identity of §7 gains one line**: `SAEA-E21-MF-SEMANTIC-IMPACT-BASELINE-V1` —
negation-critical error rate **0.0278 %** on all 44 and **0.0185 %** on the evaluation ten, under
taxonomy `e22-semantic-scan-2026-09-06-content-impact-word-pair-v1`. Same pairing rules: a cell on
the ten pairs against the ten's figure, and the taxonomy id must match or the two numbers are not
comparable.
