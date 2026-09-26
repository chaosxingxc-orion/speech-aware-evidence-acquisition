# Knowledge construction and consumption: the corrected split

Owner decision 126 (2026-09-26) withdrew the registration of the four per-group knowledge proposals as
designed and asked first for a measurement, not a redesign. This note carries that measurement and states the
corrected shape. Decision 127, taken immediately after, sets the admission criterion used in section 9. No
cell is registered, no exposure row is countersigned and `launch_authority` stays false.

Measured object: `coordination/slurp-system-knowledge-value001-group-v1/prepared-contexts-v1.json` under
`SPEECHRL_DATA_DIR`, prepared artifact `output_sha256`
`eb8b7aead811bc7fc6fd8886b4de2b6be03cc74117800a23631fba289348c96b`. Driver:
`scripts/analysis/knowledge_edit_context_composition.py`. Contacts added: model 0, tokenizer service 0,
encoder 0, scorer 0.

## 1. Method

Re-serialise each `model_context` with the same canonical rule the preparation rail uses
(`rails.prepared_feedback._canonical_context`: `ensure_ascii=True`, `sort_keys=True`, `separators=(",",":")`).
Walk the shared-JSON form structurally, label every container node, then re-emit the canonical bytes through
an instrumented emitter so that every byte is charged to exactly one label and the labels sum to the total by
construction. A pool entry is charged to the label of the site that references it; each `{"$ref":"pN"}`
wrapper is charged to `reference_resolution`. Count tokens with the local `llama-tokenize` binary at
`/home/chao/llama.cpp/build/bin/llama-tokenize`, loading the pinned `Qwen3-Omni-30B-A3B-Instruct-Q4_K_M.gguf`
vocab only: one short local process, no server, no port, no GPU, 63 invocations for the whole measurement.

Treat that tokenizer as validated against the served one. Against
`docs/checks/speech-aware-evidence-acquisition/2026-09-05-e22-dev-esb-shape-c-v1/prompt-fit/prompt-fit-render.json`
(build `04ccc72a`, chat template `45777d2e...`) the three recorded prompts read 47 / 21 / 16 served tokens and
79 / 53 / 48 locally -- a constant +32 on all three, which is the 41-character media marker the server
substitutes and the local binary tokenises literally. Modulo that marker the two agree exactly, and parsing
special tokens or not changes no number below. Byte attribution is exact; per-label token counts are measured
on each label's own bytes and over-count the whole by 1,538 to 1,613 tokens (about 3.0 per cent) because each
boundary restarts tokenisation, so read label shares to about a third of a point.

## 2. Composition of the four group contexts

Totals, as flown (`total_bytes` matches the four `context_bytes` in
`docs/receipts/continuation/2026-09-26-knowledge-group-context-readiness-v1.json`):

| group | sample | bytes | tokens | bytes/token |
| --- | --- | ---: | ---: | ---: |
| g1 | `slurp:train:000282:audio-1502114155` | 156,560 | 52,178 | 3.000 |
| g2 | `slurp:train:000308:audio-1488905475` | 152,555 | 51,538 | 2.960 |
| g3 | `slurp:train:000309:audio-1490018206` | 157,401 | 51,886 | 3.034 |
| g4 | `slurp:train:000351:audio-1499689684` | 150,600 | 50,659 | 2.973 |
| batch | four contexts | 617,116 | 206,261 | -- |

Decomposition, bytes / tokens per group, with g1's share of its own context:

| category | g1 | g2 | g3 | g4 | g1 B% | g1 T% |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| supplied knowledge bodies | 47,774 / 11,785 | 42,686 / 10,744 | 52,698 / 12,841 | 41,414 / 10,323 | 30.51 | 21.91 |
| role contacts | 42,171 / 13,924 | 42,982 / 14,222 | 39,836 / 13,403 | 43,480 / 14,324 | 26.94 | 25.89 |
| control and delivery events | 19,912 / 7,775 | 20,617 / 8,118 | 18,568 / 7,182 | 19,207 / 7,441 | 12.72 | 14.45 |
| edit surface (contract + cards) | 16,422 / 4,402 | 16,422 / 4,402 | 16,422 / 4,402 | 16,422 / 4,402 | 10.49 | 8.18 |
| reference resolution | 14,306 / 8,594 | 13,567 / 8,161 | 13,974 / 8,404 | 14,155 / 8,501 | 9.14 | 15.98 |
| actual tool records | 11,122 / 5,377 | 11,122 / 5,391 | 11,122 / 5,376 | 11,122 / 5,363 | 7.10 | 10.00 |
| JSON scaffolding | 2,850 / 1,003 | 3,132 / 1,099 | 2,850 / 1,007 | 2,850 / 1,021 | 1.82 | 1.86 |
| terminal feedback | 2,003 / 931 | 2,027 / 963 | 1,931 / 858 | 1,950 / 880 | 1.28 | 1.73 |

Supporting counts: 352 / 343 / 360 / 344 shared pool entries, 793 / 748 / 766 / 787 `$ref` wrappers, 229 / 230
/ 227 / 224 SHA-256 digest occurrences over 167 / 170 / 163 / 165 distinct digests. Sharing already saves a
great deal: the expanded evidence is 1,234,163 / 1,214,231 / 1,181,094 / 1,249,215 bytes, so the as-flown form
is 7.5 to 8.3 times smaller than the tree it encodes. Read the 9 per cent `reference_resolution` charge as the
price of that compression, not as waste -- but read it also as 748 to 793 pointers the reader must resolve by
hand. Auditability of the table: 84 to 89 pool entries are reached under more than one category and are
charged to the most frequent one; 31 container nodes receive two labels and keep the first.

## 3. The context does not fit, and by more than the design believed

Fit against the pinned fragment `q4km-mmproj-free-system-np1-ctx48k-resource-guard-v1` (`-c 49152 -np 1`, one
live slot), with a 1,024-token completion reserve and the registered 2-token special reserve:

| group | required window | margin vs 49,152 | minus 8,192 reserve | minus 6,144 (one eighth) | vs the undeclared 32,768 ceiling |
| --- | ---: | ---: | ---: | ---: | ---: |
| g1 | 53,204 | **-4,052** | -12,244 | -10,196 | -28,628 |
| g2 | 52,564 | **-3,412** | -11,604 | -9,556 | -27,988 |
| g3 | 52,912 | **-3,760** | -11,952 | -9,904 | -28,336 |
| g4 | 51,685 | **-2,533** | -10,725 | -8,677 | -27,109 |

Three corrections follow, and all three are load-bearing.

- Decision row 126 records "about 38-39k tokens". The measured figure is 50,659 to 52,178. The contexts exceed
  the physical slot before any reserve is applied, by 2,533 to 4,052 tokens. This is not a reserve failure; it
  is a capacity failure.
- The one-eighth reserve is not what the code grants at this slot.
  `rails.context_budget.serving_bound_reserve_tokens` (line 149) returns the registered
  `OPERATIONAL_RESERVE_TOKENS` of 8,192 whenever the live slot is at or above `PER_SLOT_LIMIT_TOKENS`; the
  one-eighth clamp binds only below 32,768. Both columns appear because both were claimed; neither admits the
  context. And an undeclared budget never sees 49,152 at all: `assess_context_budget` (line 532) takes
  `min(live_limit, PER_SLOT_LIMIT_TOKENS)`, so without an explicit `context_budget_limits` block the ceiling
  is 32,768 and the shortfall is about 28,000 tokens.
- The 200,000-byte bound of `source-v1.json` passes comfortably at 150,600 to 157,401 bytes. At the measured
  2.96 to 3.03 bytes per token it corresponds to roughly 66,000 tokens, which no slot in this study holds. The
  bound is stated in the wrong unit; the readiness note's own limitation, "byte bounds are not tokenizer
  capacity admission", was right and this is the number it lacked. The fragment's `max_tokens` is 2,048, so
  the 1,024-token completion reserve used above is generous in the design's favour.

## 4. The relevance fraction

The edit surface is small and exactly known. `edit-contract-v1.json` exposes 15 editable targets: 5 slots
(`business_name`, `date`, `news_topic`, `order_type`, `place_name`) times 3 fields (`ambiguity_behavior`,
`extraction_cues`, `missing_behavior`), with `max_edits` 2 and `max_field_chars` 600. One accepted proposal
may therefore change at most 1,200 characters.

Split the same canonical bytes four ways, exclusively and exactly. Charge the framing (`stage`,
`context_view`, `reading_contract`, `edit_contract`, `feedback_definition`) to `instruction_and_contract`, and
the current values of the 15 editable fields to `on_edit_surface`. Charge to `may_bear` everything a reader
could defensibly use to justify an edit, counted generously and in full: every role contact including its
agent-state history, task instruction, tool schemas, decoding parameters and wire response; the supplied
slot-contract bodies whose slot is editable; the four terminal outcome vectors and the group's outcome
variation; the four delivered answers; the tool-call arguments. Charge everything else to `cannot_bear`: the
ontology and intent-binding surfaces the probe forbids changing, the exemplar bodies that carry retrieval
keys, the slot bodies for non-editable slots, the non-editable card fields, the decoded control messages, and
the route, custody and tool-record custody metadata. Pointer machinery keeps its own line.

| class | g1 | g2 | g3 | g4 | g1 B% | g1 T% |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| instruction and contract | 3,970 / 1,767 | 3,970 / 1,767 | 3,970 / 1,767 | 3,970 / 1,767 | 2.54 | 3.29 |
| **on edit surface** | **1,886 / 342** | 1,886 / 342 | 1,886 / 342 | 1,886 / 342 | **1.20** | **0.64** |
| may bear (generous) | 52,325 / 16,626 | 52,783 / 16,843 | 50,658 / 16,140 | 56,012 / 17,467 | 33.42 | 30.92 |
| cannot bear | 84,073 / 26,439 | 80,349 / 25,963 | 86,913 / 26,803 | 74,577 / 24,158 | 53.70 | 49.17 |
| reference resolution | 14,306 / 8,594 | 13,567 / 8,161 | 13,974 / 8,404 | 14,155 / 8,501 | 9.14 | 15.98 |

**Cannot bear plus pointer machinery is 58.92 to 64.10 per cent of the bytes and 62.52 to 65.86 per cent of
the tokens.** The fields the proposer may actually change occupy 1,886 bytes and 342 tokens: 1.20 to 1.25 per
cent of the bytes, 0.64 to 0.66 per cent of the tokens. The as-flown 1,886 bytes are below the 3,397 bytes the
15 values occupy when expanded because `business_name`, `news_topic` and `place_name` share one identical
`missing_behavior` value, which the pool stores once.

Three further relevance facts, each stated with the number that supports it.

- **No episode is wholly irrelevant.** All 16 episodes supply at least one editable slot's contract, so 0
  bytes and 0 tokens belong to episodes that touch none of them. Do not claim otherwise.
- **The supplied knowledge is mostly about surfaces that cannot change.** Distinct supplied bodies per group:
  8 intent boundaries, 20 train exemplars, and 11 to 16 slot contracts. In bytes: editable-slot bodies 8,369 /
  7,992 / 9,109 / 10,800, against non-editable slot bodies 25,663 / 20,315 / 30,021 / 15,949, intent
  boundaries 7,613 / 7,943 / 7,658 / 8,045 and exemplars 6,002 / 6,348 / 5,821 / 6,493. Editable-slot bodies
  are 17.3 to 26.2 per cent of the supplied knowledge and 5.3 to 7.2 per cent of the context.
- **Two fifths of the edit surface, in three groups of four, has no evidence in its own group.** g1 supplies `date`, `news_topic`,
  `place_name`; g2 `business_name`, `date`, `order_type`; g3 `business_name`, `date`, `place_name`; g4 all but
  `news_topic`. So 6 / 6 / 6 / 3 of the 15 targets are proposed against a context that contains nothing about
  their slot. `news_topic` has evidence in one group of four.

## 5. The counterfactual size

Build the same context from retrieval instead of enumeration: (a) the current values of the 15 editable
targets with their `previous_value_sha256`, (b) only the evidence units keyed to those fields, selected by the
unit's own retrieval key `slot-contracts::slot-contract:<slot>` and capped at top-k = 5 (one unit per editable
slot; 3 or 4 exist per group), and (c) every other unit carried by the existing explicit source-hashed
omission mechanism rather than deleted silently. Contract, reading contract and feedback definition unchanged.

| variant | g1 bytes / tokens | g2 | g3 | g4 | token factor |
| --- | ---: | ---: | ---: | ---: | ---: |
| CF-1 editable fields only, per-unit ledger | 28,096 / 11,527 | 27,597 / 11,294 | 28,593 / 11,735 | 27,140 / 11,137 | 4.42-4.56x |
| CF-2 plus keyed supply | 36,686 / 13,413 | 35,813 / 13,067 | 37,926 / 13,729 | 38,233 / 13,531 | 3.74-3.94x |
| CF-3 plus attempt outcomes and deliveries | 38,401 / 14,167 | 38,051 / 14,002 | 39,270 / 14,358 | 39,844 / 14,243 | 3.56-3.68x |
| **CF-4 = CF-3 with a class-level ledger** | **32,236 / 11,330** | 31,886 / 11,203 | 33,105 / 11,545 | 33,679 / 11,420 | **4.44-4.61x** |

Take CF-4 as the corrected size. Its fit, same reserves as section 3:

| group | required window | margin vs 49,152 | minus 8,192 | vs the 32,768 ceiling |
| --- | ---: | ---: | ---: | ---: |
| g1 | 12,356 | +36,796 | **+28,604** | +12,220 |
| g2 | 12,229 | +36,923 | +28,731 | +12,347 |
| g3 | 12,571 | +36,581 | +28,389 | +12,005 |
| g4 | 12,446 | +36,706 | +28,514 | +12,130 |

A refused context becomes one that fits with about 28,500 tokens of operational margin, and fits even the
undeclared 32,768 ceiling with about 12,000 to spare. The reduction is 4.4 to 4.6 times in tokens and 4.5 to
4.9 times in bytes.

Where the remaining 11,330 tokens sit (g1 component bytes): omission ledger 12,773 class-level against 20,115
per unit; retrieved units 8,571; editable field values 5,794; edit contract 2,756; attempt outcomes 1,125;
deliveries 1,119; reading contract 813; feedback definition 234. The ledger dominates, and 64-hex digests
dominate the ledger. Collapse the 20 per-attempt role, tool and control units into 12 class records -- the
CF-3 to CF-4 difference -- and keep one record per omitted supplied knowledge body, because a later
consumption stage must be able to name those units. Do not compress further by replacing the per-body records
with one aggregate digest: that buys about 4,000 tokens and loses the addressability the omission mechanism
exists to provide.

## 6. The defect, in this repository's terms

The construction output schema is not at fault and must not be re-litigated.
`configs/probes/knowledge_value_edit_group_v1.txt` already asks for a bounded candidate update to named
editable fields, retains their exact previous-value hashes, keeps the ontology, intent bindings and retrieval
keys unchanged, forbids sample ids, sample answers, transcript fragments and per-example lookup instructions,
emits `slot-value-edits-v1`, and returns an empty `edits` array when nothing general is defensible; the
baseline fragment carries `evidence_source: "none"`, `scorers: []`, `result_kind: "artifact"`. The product is
a field-level bounded edit over an already-keyed store, which is right.

The defect is on the input side, and section 4 is its measurement: to author at most two 600-character field
edits, the proposer is handed 50,659 to 52,178 tokens of which 0.64 per cent is the fields under edit and 62.5
to 65.9 per cent cannot bear on them at all. This is the shape the owner named -- a finished construction
product delivered as though it were the output of consumption, with the retrieval, matching and filtering that
consumption performs simply absent. It is also the shape this repository has already priced: the whole-index
supply read SLU -7.37 with its derangement twin at -9.97, a pure form loss (S2, prose-as-policy), while the
only large admitted supplies were retrieved, small and typed -- speech-keyed top-5 exemplars at +12.61 and
+13.70.

Note the stronger conclusion the numbers force: the design is not merely wasteful, it is unflyable. It fails
real request fit by 2,533 to 4,052 tokens against the physical slot.

## 7. Construction: the corrected shape

Keep the output exactly as it is. Change only the input.

- Retrieve, do not enumerate. Select construction evidence by the unit's own retrieval key against the fields
  under edit, at a stated top-k, and refuse a context assembled by enumeration.
- Match to the edit surface. Admit a unit only when its key resolves to an editable `(slot_id, field)` target
  of the frozen contract. Do not carry the ontology, intent-binding or exemplar surfaces into a slot-value
  construction context; the probe forbids changing them, so they are 73.8 to 82.4 per cent of the supplied
  knowledge and none of the signal.
- Filter, then account. Cap per slot, de-duplicate identical bodies, and carry every excluded unit as an
  explicit source-hashed omission record. Never truncate silently; never drop a group, attempt or later event
  to fit.
- Price in tokens before registering. Measure the real request with the live slot's own budget, declare
  `context_budget_limits` if the 49,152 geometry is to be used as a budget, and stop the flight on a fit
  failure rather than reduce the output allowance or switch geometry.
- Keep a target with no evidence in its own group out of that group's context. Six of fifteen targets in three
  groups have nothing to read; asking for an edit there invites an invented one.

## 8. Consumption: a separate stage with its own retrieval

Consumption is not the same act and must not be measured inside construction (decision 123). Give it its own
three parts.

- Its own query, derived from speech or speech plus state, never from a transcript. The standing ruling holds:
  a retrieval query contains speech. `rails.phase_supply` already enforces this (`QUERY_SIGNAL_MODALITIES =
  ("speech", "speech+state")`) and is the only speech-keyed top-k retriever in the repository.
- Its own matching, to the row's own candidates rather than to the whole store.
- Its own filtering: legality, top-k, de-duplication, with the excluded set recorded.

State plainly what the audit of `native-candidate-slot-view-v1` found, because the v4 readiness note's framing
invites the wrong assumption. That view retrieves nothing: it has no query of any kind, its row universe is
the entire released store in fixed `slot_id` order (`rails/slot_binding_view.py` lines 270-274), and its
renderer's own docstring says "No selection, retrieval, answer generation, or tokenization occurs here"
(`core/model/native_slot_binding_view.py` lines 45-49). It does match, but only inside a row and only off
sealed agent state, partitioning `row.intent_bindings` by the Perception candidate set (`slot_binding_view.py`
lines 571-576); no row is ever dropped. It applies no top-k -- there is no `k`, `m` or `tau` in either module,
and `max_candidates` only validates the pinned Perception bound -- it de-duplicates only as a refusal guard,
and it treats legality as an assertion, falling back to the full card on violation while its own prompt text
says "Omission does not restrict legal intents or slots". It is enabled in two closed proof configs and in no
active arm. Treat it as a per-row body redaction with receipts, not as the consumption retrieval stage; that
stage has to be built on the `phase_supply` path.

## 9. Acceptance

Two admission criteria, not one (decision 127). The retrieval, matching and filtering stage specified in
sections 7 and 8 is an **engineering-base item**. It is admitted on three things -- its logic is sound, it
states the ceiling it unlocks, and it reads as doing no harm -- and **it never has to demonstrate a gain**. It
declares `claims_benefit: false`.

Preregister a harm margin equal to the measured floor of the item's own design.

- The **construction-input change** is read **offline over the sealed pool**, margin **0.67 pp**. Its effect
  on a delivered answer is a deterministic function of bytes already sealed for any candidate edit whose
  consequence is computable there, and it spends no GPU. Use this design; it is the smallest floor this
  program has.
- The **consumption stage** changes which bytes a node receives, so its effect is not computable from sealed
  bytes. Read it as a **per-row paired arm inside one campaign**, margin **0.735 pp** same-flight at n >= 200.
  Fall back to a cross-flight read only if a paired arm is impossible, and then carry **1.2485 pp** on Fold A
  at 1,080 rows or **1.2525 pp** on DEV at 1,000.

Admit the item when the primary metric's CI95 lower bound does not fall below the negative margin and intent
is non-inferior at its own null.

State the ceiling from measured headroom, not from assertion. The retrieval stage's honest ceiling argument is
about which headrooms become **reachable at all** once the right knowledge can be selected per row. Oracle
best-of-5 is +6.55 pp pooled and +12.55 pp on disagreeing rows; ENTITY-MIXED is +17.4 / +16.5;
INTENT-UNCOVERED is +5.4 / +6.8 SLU and +12.0 / +16.9 intent. None of these is presently addressable by a
supply that loads the whole store, because the form cost of carrying it is measured at -7.37 SLU and falls on
every row including the rows the store has nothing to say about. Per-row selection is the precondition for
touching any of them. That is the ceiling claim: it unlocks access and predicts no effect.

**A base item may never be reported as a gain, and two base items are never assumed to add.**

The benefit measurement does not disappear, it moves. Any gain from the candidate edits these contexts produce
belongs to the **system-level optimisation stage** under decision 115's full rule: official SLU-F1 CI95 lower
bound above zero, intent non-inferior, replicated on a fresh roster, one test read. In either mode, a
whole-system terminal read over 4 to 16 trajectories is **not** an acceptance test: the batch002 round's
-1.5636 pp over four draws is invisible to this instrument at every floor above, and comparing complete
systems after a whole batch cannot separate a bad value from a bad form of delivery -- the CELL-3 finding that
a perfect gate performs about like PLAN.

One consequence, plainly, because it inverts how this program has read its own record: we cannot see a +0.6 pp
gain at any roster size we fly, but bounding harm is the same interval read the other way round.
NEUTRAL-by-width -- filed as failure for P0, P1, B8b-anchor, the PLAN arm, R-PRIM, B1-notool and the GEPA cell
arm -- is precisely the no-harm proof a base item requires. The instrument is sufficient for base admission
even though it is insufficient for small-gain detection.

## 10. What must not change

- The ontology, the intent bindings and the retrieval keys. They are not editable, and carrying them into a
  slot-value construction context is the defect, not the remedy.
- The source-bound output schema: `slot-value-edits-v1`, named editable fields only, exact
  `previous_value_sha256` retained, no sample ids, answers or transcript fragments, empty `edits` legal and
  meaning "retain the incumbent".
- The explicit source-hashed omission mechanism. Every excluded unit keeps its field names and its source
  hash; a shorter context is never a quieter one.
- Construction and consumption row disjointness, and the closed splits: DEV6570 and test13078 stay closed,
  gold labels and reference transcripts never enter runtime.
- Immutability of what is already sealed: the v1 context, the four actors, their scores and the batch002 read
  are not rewritten; supersede them.

## 11. Smallest concrete next step

Re-prepare the four group contexts through the existing `rails.knowledge_edit_context` path with the CF-4
input shape -- 15 editable field values with their previous-value hashes, the keyed slot bodies for editable
slots at top-k 5, the four outcome vectors and deliveries, and a class-level omission ledger -- then run
`scripts/analysis/knowledge_edit_context_composition.py` against the new artifact and land the receipt. That
is one model-free preparation and one measurement; it makes the step flyable and costs no GPU. Open no further
base item to postpone the optimisation stage.
