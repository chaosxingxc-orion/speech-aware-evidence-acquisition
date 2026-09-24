# Release registration: `train-exemplars-with-empty-v1`

Date: 2026-09-24. Execution profile `model-free-check`. Zero model, tool, embedding, encoder,
tokenizer, scorer, ASR, server, network, GPU and paid-API contacts. Exposure ledger row
`SAEA-SLURP-TRAIN-EXEMPLARS-WITH-EMPTY-BUILD-V1` (DRAFT, root countersignature pending).

A RELEASE, never a cell. It registers no cell, reserves no contact, constructs no
`contracts.ExecutionPlan`, admits no mechanism and states no effectiveness, superiority or
generalisation claim. Nothing consumes it yet; `consumers` in the pins file is empty on purpose.

No utterance text, transcript, gold filler, predicted filler or knowledge content appears in this
document or in any receipt this release writes. Every cell below is a label, an identifier, a
count, a share or a hash.

## 0. Read this first: the number that motivated the request is wrong, the headroom is not

The request came from `docs/results/2026-09-24-slurp-plan-bad-case-bank.md` section 1e, which
reports that the released `train-exemplars` pool holds **0 entity-free values out of 9,354** while
38.3 % (TRAIN Fold A) / 31.4 % (DEV-2000-ADDED) of roster rows carry no gold entity.

Measured directly on the released parent snapshot `4c498dc0...`:

| Released parent store | Values | Entity-free | Entity-bearing | Entity-free share |
| --- | ---: | ---: | ---: | ---: |
| `size-pool-annotated-exemplars` (the locked v2.0 plan's pin) | 9354 | 2949 | 6405 | 31.5 % |
| `size-pool-annotated-exemplars-minus-r01` (the ROLL-1 pin) | 8554 | 2741 | 5813 | 32.0 % |

The pool has never been entity-bearing by construction. The bank's own parser
(`scripts/analysis/slurp_plan_bad_case_bank.py::load_exemplar_labels`) splits the raw line's third
field on `;` and keeps the text before `=`; an entity-free line renders
`<utterance> | <scenario>_<action> | none`, so the literal token `none` is counted as an entity
type named "none" and the value lands in the 1-entity bucket. That is why the published spread
starts at 1 and the 0-bucket is empty -- by construction of the parser, not by measurement of the
store. The bad-case bank is a countersigned immutable record and is **not** rewritten; this
document is its English successor on that one number.

**Everything else in section 1e survives.** ENTITY-FP-ONLY is 131 rows (12.1 %) on TRAIN Fold A
and 108 (10.8 %) on DEV-2000-ADDED, carrying +4.76 / +3.47 pp of pooled official SLU headroom, and
41.5 % / 48.4 % of empty-gold rows still emit an entity. So the supply is **not** missing the
empty *case*. What it never shows is the correct empty **answer**.

## 1. What this release changes, and only this

The Solver's output contract (`configs/probes/slurp_native_role_solver_v2.txt`, sha256
`18bff5c557cac7ac`) is:

```
{"scenario":"...","action":"...","entities":[{"type":"...","filler":"..."}]}
```

with the sentence "If no entity is expressed, return an empty entities array". The exact bytes a
correct empty answer carries are therefore `"entities":[]`. The word `none` occurs nowhere in that
contract and in no legal Solver response.

Module M1's admitted gain was convention transfer from the annotated raw line. This release
extends that one mechanism to the empty case. KB view `annotated-exemplars-empty-contract`
(`rails.knowledge_build.VIEW_ANNOTATED_EXEMPLARS_EMPTY_CONTRACT`) renders the trailing field of an
entity-free line as `rails.knowledge_build.SOLVER_EMPTY_ENTITY_LIST_FORM` instead of `none`:

| Line shape | Parent view `annotated-exemplars` | This view |
| --- | --- | --- |
| entity-bearing | `<utterance> \| <scenario>_<action> \| type=filler; type=filler` | identical, byte for byte |
| entity-free | `<utterance> \| <scenario>_<action> \| none` | `<utterance> \| <scenario>_<action> \| "entities":[]` |

Nothing else moves. The builder asserts all of it before it writes a byte, and refuses on any
drift:

| Property | Relation to the released parent |
| --- | --- |
| Construction exclusion | the same three roster receipts, in the same order, asserted equal to `scripts/build_slurp_exemplar_pool_assets.py`'s own tuple by a test |
| Pool size | 9,354 utterances (11,514 governed TRAIN minus 2,160 named by Fold A / Fold B / DEV-1000) |
| `source_split_identity_hash` | `22f6092dfdb4a160...` -- **equal** to the parent's, so the selection provably did not move |
| Facets | 9,354, **all byte-identical**: id, dimension, representation kind, representation text, source sample ids, parent facet ids |
| Facet ids | `facet:content:<slurp_id>`, unchanged -- the sealed speech-keyed retrieval binds unchanged |
| Value ids, prior scores, task targets, associations, provenance refs | identical on all 9,354 |
| Value contents | 6,405 byte-identical; 2,949 differ in the trailing field alone |

### Is it a superset?

**Stated exactly, as the parent agent's brief requires rather than claimed.** It is a superset in
every dimension except the one it is built to change:

* superset (in fact equality) of the parent's **selection**, **facets**, **value ids**, **prior
  scores**, **task targets**, **associations** and **provenance refs**;
* **not** a byte superset of the parent's **value contents**: 6,405 of 9,354 value contents are
  present byte-identically; the remaining 2,949 -- exactly the entity-free ones, identified from
  the governed rows and never from parsing a rendered line -- carry the same line with `none`
  replaced by `"entities":[]` in the trailing field.

A view that were a strict byte superset of the parent's contents would have to keep `none` and add
something beside it; that is a second mechanism (more supply) rather than the one-factor rendering
change this release is, and it was deliberately not built (section 5).

## 2. Pool composition, per scenario

Counts and shares of the 9,354-utterance construction pool. Labels and integers only.

| scenario | entity-bearing | entity-free | total | entity-free share |
| --- | ---: | ---: | ---: | ---: |
| `alarm` | 181 | 89 | 270 | 33.0 % |
| `audio` | 30 | 140 | 170 | 82.4 % |
| `calendar` | 1185 | 383 | 1568 | 24.4 % |
| `cooking` | 78 | 13 | 91 | 14.3 % |
| `datetime` | 231 | 51 | 282 | 18.1 % |
| `email` | 563 | 270 | 833 | 32.4 % |
| `general` | 160 | 372 | 532 | 69.9 % |
| `iot` | 400 | 249 | 649 | 38.4 % |
| `lists` | 170 | 249 | 419 | 59.4 % |
| `music` | 62 | 150 | 212 | 70.8 % |
| `news` | 311 | 72 | 383 | 18.8 % |
| `play` | 942 | 315 | 1257 | 25.1 % |
| `qa` | 738 | 325 | 1063 | 30.6 % |
| `recommendation` | 229 | 84 | 313 | 26.8 % |
| `social` | 229 | 42 | 271 | 15.5 % |
| `takeaway` | 120 | 17 | 137 | 12.4 % |
| `transport` | 374 | 77 | 451 | 17.1 % |
| `weather` | 402 | 51 | 453 | 11.3 % |
| **all** | **6405** | **2949** | **9354** | **31.5 %** |

The spread is wide and it matters for a rollout: `audio` (82.4 %), `music` (70.8 %),
`general` (69.9 %) and `lists` (59.4 %) are majority-empty, while `weather` (11.3 %),
`takeaway` (12.4 %) and `cooking` (14.3 %) are almost entirely entity-bearing. A speech-keyed
top-20 recall therefore already delivers a different empty/non-empty mixture per row; this
release changes what an empty neighbour *says*, never how many arrive.

## 3. Pins

Store id and role stay `train-exemplars`; only the namespace moves. See section 4 for why.

| Artefact | Path | sha256 |
| --- | --- | --- |
| snapshot (content hash -- the value a fragment pins) | `knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars-empty-contract-v1/snapshot.json` | `e39985250bbd32ae0ac80ef234b8d0357943c4a68ac4e73b680ee4be4f48dbc6` |
| snapshot (file bytes) | same | `53135ef430c1ba560a8a4ee67683a0ebb239c02dc97071812c33f43ff1b16f7d` |
| release | `knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars-empty-contract-v1/release.json` | `4aa2c6dce28395efae5662aea2d4f755a01fdc9ab81ab0c6ad9844f4eeb71c2d` |
| build receipt | `docs/receipts/knowledge/slurp-kb-size-pool-annotated-exemplars-empty-contract-v1.json` | `df28a3cea60cee6ca3b57d12aa0f58f16e6592bb639f444344b6ea54ff8194bf` |
| release pins | `docs/readiness/2026-09-24-slurp-train-exemplars-with-empty-store-release-pins-v1.json` | (this release's pins file) |
| builder | `scripts/build_slurp_train_exemplars_with_empty_store.py` | `e2d6657a17dc15836a29b25154209790d0211989c7f812629e5a1f74c5f2ba48` |
| parent snapshot | `knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars/snapshot.json` | `4c498dc0282055b9fe036ed7e950af519bd48b5f26e76876d0250727196a72e9` |
| parent build receipt | `docs/receipts/knowledge/slurp-kb-size-pool-annotated-exemplars.json` | `48d0f34cf536ebf9806d55b5dcced1b607080bec3c68ca7dea27cdb01478cc72` |
| sealed facet vectors (UNCHANGED) | `vectors/slurp-kus3/facet-vectors.jsonl` | `5dfe75231c12f2624913988e4643c51b74856465bdbd108358b4f371dacffc1e` |

Snapshot id `slurp-kb-distmodel-75a1c9173c3ebdc3`. Builder policy `saea-kb-distmodel-v1`,
seed 20260823, `dimensions=["content"]`, `datastore_size=null`.

The pins file is a dated successor, not an edit: the predecessor
`docs/readiness/2026-09-22-slurp-train-exemplars-store-release-pins-r01-v1.json` (sha256
`7c140759fbb0586b...`) is named inside it by hash and its own bytes are untouched, exactly as the
v2 semantic pins named the v1 pins.

## 4. Why no encoder, and why no new store id

**No encoder, tokenizer or server contact was possible, let alone made.** The retrieval key side of
this store is the parent's, character for character: the facet ids are `facet:content:<slurp_id>`
and the facet representations are the identical `TRAIN utterance <id> (annotated-exemplar
retrieval key): "..."` descriptors. The sealed KU-S3 file `vectors/slurp-kus3/facet-vectors.jsonl`
carries one vector per governed TRAIN utterance (11,514) and the builder proves by membership that
it still covers all 9,354 facet ids, then prints the sealed hash unchanged. `rails.kb_policy.
multidim_recall` looks a facet's vector up by id with `.get(...)`, so nothing needed re-keying and
no derivative was written. The query side is untouched sealed bytes as well.

**The store id stays `train-exemplars`.** `rails.knowledge_stores.load_knowledge_store_binding`
requires `release.store_id` to equal the `knowledge_stores` key and `release.store_role` to equal
the block's `store_role`, and `rails.knowledge_index.EXEMPLAR_EVIDENCE_PREFIX` is the literal
`train-exemplars::value:` that every exemplar evidence id carries. A second store block under a
distinct id would rewrite every one of those strings and turn a one-factor construction variant
into a wiring change, so the variant cell **re-pins the existing block** -- see
`variant-fragment-diff-v1.md`.

## 5. Decisions deliberately not taken

* **The bad-case bank was not edited.** It is a countersigned immutable record; section 0 above
  supersedes its one wrong number in English instead.
* **`scripts/analysis/slurp_plan_bad_case_bank.py` was not patched.** Changing that parser would
  change a published read's bytes after countersignature. The defect is recorded here; repairing
  it belongs to whoever next touches that script.
* **No second (`-minus-r01`) empty-contract store was built.** A construction-roster cell on
  R01/R01C needs the same re-rendering on top of the R01 exclusion. The same builder produces it
  by adding `docs/receipts/rosters/slurp-stage3-construction-r01.json` to
  `EXCLUDE_ROSTER_RELPATHS`, but that is a second release and the brief asked for one namespace.
* **The parent's `none` rendering was not kept alongside the new form.** Showing both would supply
  more text and stop the cell being a clean one-factor read.
* **A bare `[]` and an `entities=[]` rendering were both rejected** in favour of the contract's
  exact bytes `"entities":[]`: the brief asks for the empty form "exactly as the model would have
  to answer", and the IDX finding of 2026-09-21 (MISLEADING TERSENESS, SLU -7.37) is a standing
  warning against a terser token that the model must still interpret.
* **No entity-free TRAIN utterances were added to the pool**, because none were missing: 2,949
  were already there (section 0). The selection and its split identity hash are unchanged, which
  is asserted rather than asserted-and-hoped.
* **No cell was registered, no config fragment was committed, no flight was queued.** The fragment
  diff is a document, not a config.
* **No existing released view was rewritten.** The two parent stores are untouched on disk.

## 6. Verification

* `python scripts/build_slurp_train_exemplars_with_empty_store.py --check` re-derives the same
  `snapshot_sha256` from the same sealed bytes; the release was built and then re-checked, and the
  content hash reproduced.
* `tests/unit/test_knowledge_build_empty_contract_view.py` pins: the empty form read out of the
  committed Solver contract (not restated); the entity-free rendering; the parent view's `none`
  rendering still frozen; facet byte-identity; value-level confinement of the change; the split
  identity not moving; the exclusion tuple equal to the parent pool builder's; the store identity
  staying `train-exemplars`; the parent-relation check refusing four kinds of drift; the
  composition report carrying no text or filler; and the released shape loading through
  `rails.knowledge_stores.load_knowledge_store_binding` under the unchanged store key.
* Gates run from the release worktree: `engineering_base_check.py`, `harness_admission_check.py`,
  `results_ledger_check.py`, `tool_catalog_check.py`, `derived_media_confinement_check.py`.
