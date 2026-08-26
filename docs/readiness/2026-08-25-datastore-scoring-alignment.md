# DATASTORE SCORING ALIGNMENT — the field's four metrics, and every one of them shown able to fail

Date: 2026-08-25. Status: **ALIGNMENT AND REPORTING CHANGE — computed, ZERO CONTACTS, 0 outbound
connection attempts against zero targets.** Row `SAEA-SN-MF-DATASTORE-SCORING-ALIGNMENT`
(registered `776358d6`, **BEFORE any computation**). Module
`src/speech_aware_evidence_acquisition/analysis/datastore_scoring_alignment.py`; receipts
`docs/checks/speech-aware-evidence-acquisition/2026-08-25-datastore-scoring-alignment/datastore-scoring-alignment.json`
(sha256 `2b409750c63b069c538e4d13975a29feae56425a75b2b3146c73922a694fb261`) and
`.../source-mutation-battery.json` (sha256
`585193a1a43732d76f2be0d3c1f9c7abb7084e29dcdedbe5a1abeec60e308d8a`).

**Spend: 0 frozen-core contacts, 0 embedding-tool contacts, 0 tokenizer contacts, 0 HTTP or socket
requests, 0 audio seconds, 0.0 GPU hours, 0 new dependencies.**
`analysis.dev100_reviewer_audit.arm_offline_guard()` was armed before the first input was opened and
recorded **0 outbound connection attempts against zero targets**. The llama-server at pid 38623 /
port 8090 had its VRAM released and was treated as cold: not contacted, not probed, not
reconfigured, not stopped.

**No knob moved.** `configs/policy/kb-policy-v1-dev100.json` is byte-identical at
`d68afd2cfb6e12d9cbd9d3fbcf0daf3f81f6ed8be9b2a75c4f8ffb234011a919`, asserted by the module before
it read anything. No snapshot was rebuilt on disk, nothing under `configs/`, `rails/` or `core/`
was written, and **no landed receipt or readiness document was rewritten in place.**

> **SECONDARY READING.** The SLURP unexposed 500 inside DEV-1000 is the LOCKED baseline's own
> population. Every number computed on it here is a secondary, descriptive **retrieval-side**
> reading over already-sealed records and must NOT be used to revise, re-tune or restate the
> 2026-08-25 baseline lock. It revises nothing; §5.3 reports it beside the exposed half only so the
> two halves can be seen to agree.

---

## 1. The one-line answer

**We did create the difficulty, the field's fix is four metrics rather than one, and all four move
— which is how we know they are worth landing.** The replaced family read 1.0 (or 0.0, or `"clean"`)
in every cell of every sweep. The replacement reports, on the datastore that actually flew:

* a SLURP scaling curve whose recall@5 spans **0.090** and is **NOT monotone** — it rises to a peak
  at 500 exemplars and then *falls* as the datastore grows;
* an A2T support distribution in which **`getLockStatus` reads support 0 at every size**, against a
  denominator that is the frozen 152-tool registry rather than the 151-tool pool it was drawn from;
* gold recall@5 of **0.736** (SLURP DEV-500) and **0.654** (A2T-G1-104) — not 1.0;
* a decontamination intersection that is **not zero**: 3 of 1,000 SLURP eval items and **11 of 400**
  A2T eval items carry text that is verbatim inside the datastore, and 15 / 36 respectively share an
  8-gram, while the landed id-only gate reads 0 and publishes `"clean"`.

Two things the new metrics settle that the old ones could not even ask. First, **coverage was never
the binding constraint**: `recall_at_full_datastore` is **1.0 on both carriers at every swept size**
— every eval query's gold target has at least one positively-scoring exemplar even at the smallest
tier. What binds is **rank**, not presence. Second, **bigger is not better at fixed k**: on SLURP,
recall@64 falls monotonically from 0.988 (100 exemplars) to 0.888 (11,514) while recall@1 rises from
0.462 to 0.620. Growing the datastore sharpens the nearest neighbour and simultaneously crowds the
window — a trade a coverage ratio of 1.0 at every size is structurally incapable of showing.

---

## 2. What the field does, and the source for each of the four

**This row took ZERO NETWORK CONTACTS, so nothing was fetched and no citation is quoted from
outside.** Every source below is an already-landed, addressable entry in this repository's own
commissioned survey `docs/readiness/2026-08-23-cross-modal-retrieval-survey.md` (git blob sha256
`0172d38c818f472844fd94c02198f3ef4c191de7481c950ce9a3c8dd771c2ce5`), which is itself the record of
the coordinator-directed web survey of 2026-08-23. The survey's own mapping lines — written before
any of this — already prescribed all four.

| # | What the field does | Source (survey item) | The survey's own mapping line | Implemented as |
|---|---|---|---|---|
| 1 | **Datastore size is a swept AXIS with a scaling curve**, not a coverage ratio | MassiveDS (Shao et al., NeurIPS 2024) — trillion-token datastore scaling, "size is a reported axis" | lane 1 item 5: *"the template for the KB scaling curve and decontamination discipline"* | `scaling_curve` |
| 2 | **Per-target support distribution** with the long-tail shape | Long-tail crisis in NN LMs (2025, arXiv 2503.22426); Tip-Adapter (Zhang et al., ECCV 2022) — a training-free K-shot key-value cache read per class and per shot count | lane 1 item 3: *"report per-class and per-bucket deltas on dev, never aggregate only"* | `support_distribution` |
| 3 | **Gold recall@k against the EVAL population's gold** | retrieve-then-rerank evaluation — ColBERTv2 (NAACL 2022), RankGPT (Sun et al., EMNLP 2023), listwise rerankers | lane 1 item 12: recall depth is the reported axis, and it is reported over the query set | `gold_recall_curve` |
| 4 | **Decontamination as a MEASURED intersection count** | MassiveDS — "explicit decontamination vs eval sets"; RETRO (Borgeaud et al., ICML 2022) — quantifies train/test leakage via n-gram overlap | lane 1 item 6: *"report accuracy stratified by train↔eval near-duplicate overlap"*, which requires a MEASURED overlap, not a verdict string | `decontamination_intersection` |

**We had already called for three of the four and not run them.** The survey's own closing line
reads *"MassiveDS hygiene: KB scaling curve with decontamination and dev-only knob tuning"*; the
size-1000 and size-5000 SLURP snapshots were **built** (receipts
`docs/receipts/knowledge/slurp-kb-size-1000.json`, `...-5000.json`) and never read as a curve. Gold
recall@k has been doing the real work all along — the A2T gold-absence diagnosis's k = 5…1024
reachability curve, the K-WIDEN round, the K1 hybrid-ranking gate — but it was **re-derived by each
analysis** instead of being a reported metric. This row does not invent a fourth thing; it runs what
was already prescribed.

---

## 3. What we had, and why it could not fail

Four families, all landed, all classified by an audit before this row existed.

| Metric | Carrier | Last landed value | Landed receipt | Classified by | Why it cannot fail |
|---|---|---|---|---|---|
| `intent_coverage` | slurp | **1.0** | `docs/receipts/knowledge/slurp-kb-size-full.json` | `2026-08-25-slurp-intent-coverage-check.md` §Q4 | **CANNOT FAIL.** 1.0 with probability one at the landed configuration (`datastore_size=None` makes `selected == rows` identically), and the denominator is TRAIN-derived while the contract clause it serves is about TASK targets |
| `scenario_ / action_ / entity_type_ / long_tail_ / cluster_coverage_proxy`; `kl_…_over_intent` | slurp | **1.0 / 1.0 / 1.0 / 1.0 / 1.0**; **0.0** | same | `2026-08-25-gate-audit-can-it-fail.md` row 5 | **CANNOT FAIL.** 1.0 (KL 0.0) in all ten swept cells; at `datastore_size=1` the sampler still returns 90 utterances covering all 60 intents — the size argument is a floor, not a cap |
| `tool_ / tier_ / category_ / argument_key_ / argument_pattern_family_ / long_tail_coverage` | audio2tool | **1.0** | `docs/receipts/knowledge/a2t-kb-size-full.json` | `2026-08-25-gate-audit-can-it-fail.md` rows 6, 7 | **CANNOT FAIL** (1.0 in every swept cell) and **NARROWER THAN ITS CLAIM**: `tool_coverage`'s denominator is the 151-tool construction pool it was drawn from, not the 152-tool registry the core may call, so `getLockStatus` is modelled by nothing while the metric reads 1.0 |
| `decontamination.verdict` | both | **`"clean"`** | both receipts | `2026-08-25-gate-audit-can-it-fail.md` rows 1, 2, 4 | **CANNOT FAIL.** The string is a Python literal with no other reachable value, and the id intersection it reports is structurally empty (SLURP ids are split-namespaced; the A2T construction pool is literally *pool − eval − exposed*) |

### 3.1 What was done with the old metrics, and why

**KEPT BESIDE, not removed.** `rails.knowledge_build.coverage_report` and
`rails.knowledge_build_a2t.coverage_report_a2t` are **untouched** — this row wrote nothing under
`rails/` — and the landed receipts that carry their last values are untouched (git blob sha256
`09e3b5bbe3ea57580d5ffc371dcd6e71297c0f6895efe385cf604a224c33a710` for `slurp-kb-size-full.json`,
`75f52a23ee86ff00abc2d33bb865fd3a0864dcb77fe7035eece13fbb2e77e081` for `a2t-kb-size-full.json`).

Three reasons for keeping rather than deleting. (1) Those receipts are the record of what was
BUILT and what FLEW; rewriting them would destroy that record and they are hash-cited by the
DEV-1000 lock verdict and the A2T generality plan. (2) Deleting a metric silently is the same
failure mode as publishing one that cannot fail — the reader loses the ability to check. (3) The
old values are still *true*, just uninformative; the honest repair is to say so where the reader
will look.

So `SUPERSEDED_METRICS` in the new module carries, for each family, its **last landed value**, the
**receipt that holds it**, the **audit that classified it**, **why it cannot fail**, and **which new
metric replaces it** — and the new receipt embeds that block. The full-size cell of each carrier
additionally re-runs the old `coverage_report` and carries its output verbatim under
`superseded_coverage_report`, so the old and the new sit side by side in one artifact and the
reader can see 1.0 next to 0.736.

---

## 4. The zero-contact route to the scaling curve, and its proof

A scaling curve normally costs a rebuild and a re-embed per size. It does not have to.

**The argument.** Both builders emit content facets keyed `facet:content:<row id>` whose
`representation` is the row's own text and nothing else
(`rails.knowledge_build._build_facets_and_values`, `rails.knowledge_build_a2t._build_facets_and_values`).
A smaller datastore is a subset of the pool, so its content facets are a subset of the full tier's,
**with identical ids and identical representations** — and therefore identical vectors, which are
already in the landed full NPZ. Restricting the candidate set is exactly equivalent to rebuilding
and re-embedding, for the content dimension.

**The proof, run at every swept size.** The module does not rely on the argument. At each size it
**builds that size's snapshot in memory** (`build_knowledge_snapshot` / `build_a2t_knowledge_snapshot`
are pure model-free functions of the pool rows; nothing is written to disk) and asserts, via
`prove_restriction_is_exact`, that the reduced content-facet id set is a subset of the pinned full
snapshot's **and** that every representation is byte-equal. It raises otherwise. Measured:

| carrier | size | reduced content facets | subset | representations identical |
|---|---|---|---|---|
| slurp | 100 / 500 / 1000 / 5000 / full | 100 / 500 / 1000 / 5000 / **11,514** | ✔ at all five | ✔ at all five |
| audio2tool | 100 / 500 / 1000 / 5000 / full | **354** / 500 / 1000 / 5000 / **12,601** | ✔ at all five | ✔ at all five |

At the full tier the check is tightened to **equality** (`require_equality=True`): the rebuild must
cover the pinned snapshot's content plane exactly, not merely be contained in it. It does, on both
carriers — `pinned_content_facets_not_in_this_tier = 0`.

**One honest divergence, reported rather than papered over.** The *whole-snapshot* content hash is a
different question from the content plane.

* **SLURP reproduces byte-for-byte**: the in-memory full build hashes to
  `e27b274516604ffc0e21319758aea99dc027f459d480a32a74a715b023a51b57`, exactly the pinned snapshot.
* **A2T does not**: the rebuild hashes to
  `ad4e0bbff31e46a66a9281fbc1deb893546c53d68debfe4b479c4658435c8e76` against the pinned
  `ec2f9ec454d3f16957ac08e4d7686a6f3941f22c600ff2b1b2b97ff43baf9fb2`.

That divergence is **expected and already on record**: the 2026-08-25 prior-score semantics repair
(`docs/readiness/2026-08-25-prior-score-semantics-repair.md`) changed both builders' `prior_score`
expression after these snapshots were pinned; §3 of that document measures the SLURP repair to be an
**exact identity** and §4.2 measures **12,237 of 12,601** A2T values to have moved. This row's
independent measurement reproduces exactly that split. It touches nothing here: the divergence is on
the **prior plane**, the restriction is on the **content plane**, and no number in this sweep reads
the prior plane.

**What the restriction does NOT buy, stated so it is not misread.** Label / prior / speaker facets
carry per-snapshot counts in their representation text and their prior mass is renormalised by the
selection, so a full four-dimension **policy replay** at a reduced size is NOT reproducible by
restriction and was not attempted. Everything reported per size is a retrieval-side quantity over
the content dimension — which is exactly what the field's recall@k is.

**Fidelity, not assumed.** Before any recall number is read, 8 samples per carrier are cross-checked
against a real `kb.multidim_recall` call: it must admit the same facet set with the same scores as
this module's vectorised cosine row. It did, 8/8 on both carriers. The ranking is therefore the
registered ranker's own ordering (cosine descending, `facet_id` ascending tie-break, strictly
positive scores only), not a lookalike.

---

## 5. The four metrics as landed, with their values on both carriers

### 5.1 METRIC 1 — the scaling curve (datastore size as a swept axis)

**SLURP.** Primary population **DEV-500 (prior-exposed)** — the exposed half is what drives the
curve, deliberately, so no curve reads off the locked cell's population.

| requested size | actual | candidate facets | median support | recall@1 | recall@5 | recall@64 | recall@full |
|---|---|---|---|---|---|---|---|
| 100 | 100 | 100 | 1 | 0.462 | 0.700 | 0.988 | 1.000 |
| 500 | 500 | 500 | 6 | 0.600 | **0.790** | 0.972 | 1.000 |
| 1,000 | 1,000 | 1,000 | 12 | 0.566 | 0.754 | 0.954 | 1.000 |
| 5,000 | 5,000 | 5,000 | 56 | 0.582 | 0.758 | 0.930 | 1.000 |
| full | **11,514** | 11,514 | 127 | **0.620** | 0.736 | **0.888** | 1.000 |

`curve_is_informative` **True**; 5 distinct recall@5 values; span **0.090**;
`monotone_non_decreasing_in_size` **False**.

**Audio2Tool.** Population A2T-G1-104 (exposed; its seal was broken by the landed G1 read).

| requested size | actual | candidate facets | median support | recall@1 | recall@5 | recall@64 | recall@full |
|---|---|---|---|---|---|---|---|
| 100 | **354** | 354 | 2 | 0.346 | 0.606 | 0.885 | 1.000 |
| 500 | 500 | 500 | 3 | 0.394 | 0.663 | 0.894 | 1.000 |
| 1,000 | 1,000 | 1,000 | 4 | 0.433 | **0.683** | **0.904** | 1.000 |
| 5,000 | 5,000 | 5,000 | 11 | 0.490 | 0.654 | 0.875 | 1.000 |
| full | **12,601** | 12,601 | 16 | **0.529** | 0.654 | 0.875 | 1.000 |

`curve_is_informative` **True**; 4 distinct recall@5 values; span **0.077**;
`monotone_non_decreasing_in_size` **False**. The requested 100 returns **354** because the builder's
per-target and per-stratum floors are HARD and the size argument is a best-effort target — the
actual is what every cell reports.

**What the curve says.** On both carriers recall@1 rises with size (non-monotonically on SLURP,
which dips to 0.566 at 1,000) and recall@k for k ≥ 5 peaks early and then falls. Adding exemplars makes the single best neighbour better and the top-k window
worse, because the added exemplars are overwhelmingly non-gold near-neighbours competing for the
same slots. The study's frozen operating point is `top_k = 5`, which sits squarely in the falling
region: **SLURP's landed full-size datastore scores 0.054 recall@5 BELOW its own 500-exemplar
tier.** That is a scaling result, not a coverage result, and no coverage ratio could have produced
it.

### 5.2 METRIC 2 — per-target support distribution (the long-tail shape)

Denominator is the **task's** target vocabulary, never the datastore's contents.

**SLURP** — task target space **60** = union of the 60 TRAIN row intents and the 59 DEV-1000 gold
intents; `eval_gold_targets_absent_from_train` is the **empty set** (measured, not assumed).

| size | total exemplars | zero-support | support 1 | support < 5 | min | p05 | p25 | p50 | p75 | p95 | max | mean |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 100 | 100 | 0 | 33 | 59 | 1 | 1 | 1 | 1 | 2 | 3 | 5 | 1.67 |
| 500 | 500 | 0 | 2 | 16 | 1 | 2 | 4 | 6 | 10 | 22 | 31 | 8.33 |
| 1,000 | 1,000 | 0 | 1 | 5 | 1 | 2 | 7 | 12 | 19 | 47 | 66 | 16.67 |
| 5,000 | 5,000 | 0 | 0 | 1 | 2 | 8 | 33 | 56 | 91 | 244 | 349 | 83.33 |
| full | 11,514 | **0** | **0** | **1** | **4** | 18 | 76 | **127** | 207 | 566 | **810** | 191.9 |

**Audio2Tool** — task target space **152**, the **frozen tool registry**: every tool the core may
call. This is the denominator `tool_coverage` should have had.

| size | total exemplars | zero-support | support 1 | support < 5 | min | p05 | p25 | p50 | p75 | p95 | max | mean |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 354 | 354 | **1** | 44 | 142 | **0** | 1 | 1 | 2 | 3 | 5 | 12 | 2.33 |
| 500 | 500 | **1** | 33 | 116 | **0** | 1 | 2 | 3 | 4 | 8 | 17 | 3.29 |
| 1,000 | 1,000 | **1** | 19 | 78 | **0** | 1 | 2 | 4 | 11 | 17 | 26 | 6.58 |
| 5,000 | 5,000 | **1** | 2 | 6 | **0** | 5 | 7 | 11 | 63 | 82 | 141 | 32.89 |
| 12,601 | 12,601 | **1** | 0 | 4 | **0** | 8 | 13 | **16** | 171 | 202 | 324 | 82.90 |

**The zero-support target is named at every size: `getLockStatus`.** The gate audit's row-7 finding
— registry 152, pool 151, `tool_coverage` = 1.0 — is now a first-class reported number rather than a
footnote, and it stays visible however large the datastore grows, because the denominator no longer
moves with the datastore.

Two shape facts the top-10 histogram in the landed receipts could not show. SLURP's full tier is a
**200:1 spread** (min 4, max 810) with a long right tail (p95 566 against p50 127). A2T's full tier
is **bimodal**: p50 16 but p75 171 — a large group of tools with a dozen-ish exemplars and a
distinct group with hundreds. Both are exactly the "report per-class support, not a coverage flag"
discipline of survey item 3.

### 5.3 METRIC 3 — gold recall@k against the EVAL population's gold

Denominator is **the eval queries**, always. A query whose gold target has no exemplar, or whose
exemplars all sit at a non-positive cosine, is a **miss at every k** and is never removed from the
denominator. Measured on the landed full-size datastore:

| population | n | @1 | @5 | @8 | @16 | @32 | @64 | @128 | @256 | @512 | @full |
|---|---|---|---|---|---|---|---|---|---|---|---|
| SLURP DEV-500 (prior-exposed) | 500 | 0.620 | **0.736** | 0.760 | 0.794 | 0.840 | 0.888 | 0.942 | 0.968 | 0.980 | **1.000** |
| SLURP DEV-1000 (pooled, descriptive) | 1,000 | 0.628 | 0.740 | 0.769 | 0.805 | 0.853 | 0.887 | 0.941 | 0.967 | 0.985 | 1.000 |
| SLURP DEV-1000 NEW500 (**SECONDARY READING**) | 500 | 0.636 | 0.744 | 0.778 | 0.816 | 0.866 | 0.886 | 0.940 | 0.966 | 0.990 | 1.000 |
| A2T-G1-104 (exposed) | 104 | 0.529 | **0.654** | 0.740 | 0.798 | 0.846 | 0.875 | 0.904 | 0.971 | 1.000 | **1.000** |

Best-gold-rank quantiles at full size — SLURP DEV-500: min 1, p25 1, p50 1, p75 7, p95 150, max
2,572. A2T-G1-104: min 1, p25 1, p50 1, p75 10, p95 203, max 466.

`queries_whose_gold_target_has_no_exemplar` is **0** and
`queries_whose_gold_exemplars_are_all_non_positive` is **0**, on every population, at every swept
size. Read together with `recall_at_full = 1.000`: **the datastore always contains the answer.** The
entire loss is ranking. That is the substantive replacement for `intent_coverage = 1.0` — the old
metric asserted presence and could only ever say "yes"; the new one measures presence *and*
reachability and says "present, at median rank 1 and 95th-percentile rank 150."

The unexposed half is reported only to show that the two halves agree (recall@5 0.744 vs 0.736); it
revises nothing and is not used to tune anything.

### 5.4 METRIC 4 — decontamination as the measured intersection count

Denominator is the **eval population**, so a wider datastore cannot flatter the number. Three
independent granularities; every result is a count with identities and there is **no verdict
string**. `by_sample_id` is the exact check the landed builders make, reported as a number.

**SLURP** — eval population = DEV-1000 (1,000 items); datastore = the TRAIN selection at each size.

| size | datastore ids | distinct normalised texts | by_sample_id | by_normalised_text | by_ngram (n = 8) |
|---|---|---|---|---|---|
| 100 | 512 | 100 | 0 | 1 | 1 |
| 500 | 2,046 | 500 | 0 | 1 | 1 |
| 1,000 | 4,091 | 1,000 | 0 | 1 | 1 |
| 5,000 | 20,089 | 5,000 | 0 | 1 | 4 |
| full | **50,628** | **11,501** | **0** | **3** | **15** |

**Audio2Tool** — eval population = the 400-unit proposed eval tier; datastore = the construction
selection at each size.

| size | datastore ids | distinct normalised texts | by_sample_id | by_normalised_text | by_ngram (n = 8) |
|---|---|---|---|---|---|
| 354 | 665 | 354 | 0 | 0 | 3 |
| 500 | 931 | 500 | 0 | 0 | 3 |
| 1,000 | 1,844 | 998 | 0 | 1 | 4 |
| 5,000 | 9,120 | 4,992 | 0 | 7 | 21 |
| full | **22,951** | **12,419** | **0** | **11** | **36** |

**Three things this measures that `"clean"` could not.**

1. **The id check really is 0** — at every size, on both carriers. The landed verdict was true. It
   is now a number with an (empty) identity list rather than a literal.
2. **The text check is NOT 0.** Three SLURP eval utterances are verbatim (case- and
   punctuation-normalised) inside the TRAIN datastore under different ids —
   `slurp:devel:000188:audio--1504198223`, `slurp:devel:002943:audio-1502200671-headset`,
   `slurp:devel:006425:audio-1495370944-headset` — and **eleven** A2T eval units are verbatim inside
   the construction pool, concentrated in `tier8_intent_blending` and reaching into `tier1_direct`
   and `tier4_implicit`. **The id-namespacing that makes the landed gate structurally unable to fire
   is exactly what makes it blind to this.**
3. **The n-gram check is larger still**: 15 of 1,000 SLURP eval items (1.5 %) and **36 of 400** A2T
   eval units (9.0 %) share an 8-gram with the datastore. Also visible: SLURP's own TRAIN pool
   carries 13 internal duplicate texts (11,514 rows → 11,501 distinct normalised texts), and A2T's
   carries 182 (12,601 → 12,419).

**What this does and does not license.** It is a measurement, not a verdict, and it is deliberately
not turned into one. These are near-duplicate rates, not a leakage finding: SLURP's splits are
utterance-disjoint by construction and a repeated short command ("turn off the lights") is a
property of the corpus, not a contamination event; A2T's construction pool is literally
*pool − eval − exposed*. What the number gives is the thing RETRO's mapping line asks for — an
overlap figure that results *can be stratified by* — and a gate that would actually move if a future
build were pointed at a merged corpus. **No landed result is restratified here, and none is
revised.**

---

## 6. The per-metric mutation proofs

**Every metric landed by this row was shown able to FAIL, in two independent ways.** A metric that
cannot fail is exactly what this row exists to replace, so landing another one would be worse than
doing nothing.

### 6.1 Data mutations — machine-enforced, inside the receipt

`mutation_battery` runs, for each metric, a mutation that SHOULD move it, and **RAISES if the metric
does not move**. The proof obligation is a fail-closed gate in the code, not a narration. Fourteen
mutations ran (seven per carrier); all fourteen moved.

| # | Metric | Mutation | Observed (slurp) | Observed (audio2tool) |
|---|---|---|---|---|
| 1 | `scaling_curve` | ignore the size restriction; score every swept size against the FULL candidate set | distinct recall@5 values **5 → 1**, span 0.090 → 0, `curve_is_informative` **True → False** | **4 → 1**, span 0.077 → 0, **True → False** |
| 2 | `support_distribution` | add one TASK target the datastore has no exemplar for | zero-support **0 → 1**, the new target named | **1 → 2**, named |
| 3 | `support_distribution` | delete every exemplar of the best-supported target | `calendar_set`: zero **0 → 1**, total **11,514 → 10,704** | `rebootDevice`: zero **1 → 2**, total **12,601 → 12,277** |
| 4 | `gold_recall_curve` | deterministically permute the gold assignment across the eval population (seed 20260825); every query vector and the whole datastore untouched | recall@5 **0.736 → 0.046** | **0.654 → 0.077** |
| 5 | `gold_recall_curve` | declare every eval query's gold target absent from the datastore | recall@512 **0.980 → 0.000**, denominator **500 unchanged**, gold-absent 500 | **1.000 → 0.000**, denominator **104 unchanged**, gold-absent 104 |
| 6 | `decontamination_intersection` | inject one EVAL sample id into the datastore's id set | by_sample_id **0 → 1**, `slurp:devel:000011:audio-1497266596` named | **0 → 1**, `tier1_direct:000075` named |
| 7 | `decontamination_intersection` | inject one EVAL item's verbatim text under NO shared id | by_normalised_text **3 → 4** while by_sample_id stays **0 → 0** | **11 → 12** while by_sample_id stays **0 → 0** |

Mutation 5 is the one that matters most: it proves the denominator is the eval population and not the
index — the queries stay in the denominator and recall goes to zero, rather than the queries
disappearing and recall staying high. Mutation 7 proves the text granularity catches precisely what
the id-only gate cannot.

### 6.2 Source mutations — the defect reintroduced, the test observed to fail, `git checkout --`

Each landed metric's own defect was written back into the module source, the metric's unit tests
were run, the named failure was observed, and the mutation was reverted with `git checkout --` with
the file verified byte-restored. Receipt: `.../source-mutation-battery.json`. Unmutated suite: **42
passed**.

| Metric | Defect reintroduced | Mutation | Observed |
|---|---|---|---|
| `support_distribution` | denominate on the DATASTORE's own targets instead of the TASK space — the `intent_coverage` defect | `per_target = {t: supports.get(t, 0) for t in space}` → `per_target = dict(supports)` | **4 failed, 38 passed**; `test_FAILURE_MODE_a_task_target_the_datastore_lacks_reads_support_zero` failed. Reverted, byte-restored |
| `gold_recall_curve` | drop the queries the datastore cannot serve from the denominator | `"n_queries": n_queries` and `/ n_queries` → `/ max(1, len(reachable))` | **1 failed, 41 passed**; `test_FAILURE_MODE_gold_absent_from_the_datastore_is_a_miss_not_a_dropped_query` failed. Reverted, byte-restored |
| `decontamination_intersection` | compare eval ids against an EMPTY datastore id set — the structural shape that makes the landed gate read `"clean"` unconditionally | `store_ids = {…}` → `store_ids = set()` | **1 failed, 41 passed**; `test_FAILURE_MODE_an_injected_eval_id_is_counted_and_named` failed. Reverted, byte-restored |
| `scaling_curve` | declare the curve informative unconditionally, so a flat sweep passes | `len(distinct_r5) > 1 and len(distinct_sizes) > 1` → `True` | **2 failed, 40 passed**; `test_FAILURE_MODE_a_flat_curve_is_reported_as_uninformative` failed, and so did the battery's own refusal test. Reverted, byte-restored |
| `prove_restriction_is_exact` | accept a reduced tier whose content representation DRIFTED from the pinned snapshot — which would pair every reduced-tier facet with the wrong landed vector | the `drifted = sorted(...)` comprehension → `drifted = []` | **1 failed, 41 passed**; `test_FAILURE_MODE_a_drifted_representation_raises` failed. Reverted, byte-restored |

`all_mutations_caught` **true**, `all_mutations_reverted` **true**. After the battery the only tree
entries under this row's paths are its own new receipt; the twelve modified files the battery
recorded belong to a **concurrent session's** ruff repair (`ba830e45`) and were neither touched nor
reverted by this row.

---

## 7. What this row does NOT say

* **It does not revise, re-tune or restate the 2026-08-25 DEV-1000 baseline lock.** Nothing here is
  an accuracy number. The unexposed 500's recall figures are a secondary descriptive reading and are
  labelled as one in the module, the receipt and §5.3.
* **It does not recommend a datastore size.** The curve shows recall@5 peaking below full size on
  both carriers. Recall depth is not conversion — K-WIDEN measured that directly: widening the
  window changed the supply on 32 of 100 trajectories and produced **0** width-attributable flips.
  Acting on the curve is a separately registered step and this row does not take it.
* **It does not declare a leakage problem.** §5.4 reports overlap rates, not a contamination
  finding, and restratifies no landed result.
* **It does not change what is retrieved or decided.** No knob, no config, no snapshot on disk, no
  policy cell. `configs/policy/kb-policy-v1-dev100.json` is byte-identical, asserted in code before
  the first input was read.
* **It does not rewrite anything landed.** The old receipts and the two audits keep their bytes; the
  new metrics land as new artifacts alongside, and §3.1 states the relationship.

---

## 8. Not verified

* **Whether recall@k at a reduced size predicts ACCURACY at that size.** Nothing here is a policy
  replay: label / prior / speaker facets are not restriction-invariant (§4), so a reduced-size
  end-to-end arm would have to be flown, not computed. It was not.
* **The A2T eval tier beyond text.** Recall@k is measured on the 104 exposed samples that have
  landed query vectors; the other ~296 units of the proposed eval tier have none and would cost
  embedding contacts. They appear in the decontamination denominator (which needs only text) and
  nowhere else.
* **Whether the 3 SLURP and 11 A2T verbatim-text overlaps affect any landed number.** They were
  measured, named and left there. Restratifying a landed result by overlap is a separately
  registered step.
* **`test.jsonl` and FINAL60.** Not opened. `train_synthetic.jsonl` not opened. No audio file
  opened.
* **Whether other seeds move the curve.** The sweep is over SIZE at the builders' own landed seeds
  (20260823 / 20260825). A seed sweep is a different question and was not run.

---

## HARD STOP

**This row reports; it does not act.** It changes what is reported, never what is retrieved or
decided. No knob is changed, no snapshot is rebuilt on disk, no landed receipt or readiness document
is rewritten, no seal is broken, no new split is opened, no flight or re-flight is authorised, no G2
is opened, no test contact is taken, and no Stage-3 activity is licensed. Acting on any number here
— resizing the datastore, restratifying a landed result by overlap, adding an exemplar for
`getLockStatus`, or moving `top_k` off 5 — is a **separately registered step** with its own owner
authority.
