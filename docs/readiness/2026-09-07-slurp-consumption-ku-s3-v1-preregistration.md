# SLURP consumption cell KU-S3 — design note and preregistration v1 (2026-09-07)

Cell **KU-S3**: KC-S1b's admitted slot contact, unchanged, **plus the slot fillers of the top-5
TRAIN utterances retrieved by the row's own SPEECH vector**, supplied as traced typed content.
One contact per row — exactly the contacts KC-S1b spends — so the only thing that moves is what
the model can see.

Predecessors this note is built on and does not restate:
`docs/readiness/2026-09-05-slurp-slot-stage-kc-s1-v1-verdict.md` (KC-S1b, ADMITTED, SLU-F1 44.35),
`docs/readiness/2026-09-06-slurp-retrieval-key-audit-v2.md` (MF-7b: neighbour retrieval on SLURP
**intent** is CLOSED and the **filler** side is handed to this cell),
`docs/readiness/2026-09-06-slurp-legal-label-projection-v2-verdict.md` (the projected comparator),
`docs/readiness/2026-09-06-slurp-consumption-ku-s1-v2-preregistration.md` (the E6 supply seam and
the owner's query-signal rule), and
`docs/readiness/2026-09-05-three-dimension-experiment-program.md` (the cell's slot in the program).

**Status: REGISTERED, FLYABLE, NOT FLOWN.** Zero model contacts were spent preparing it. Every
number below is model-free and re-derivable from committed bytes.

**Re-scoping, stated up front.** The three-dimension program's KU-S3 was
"intent-then-slots as one phase program (`phase-intent-then-slots-v1`)", a two-contact live cell
whose admission rule was "SLU-F1 LB > 0 and intent CI90 includes 0". That cell is superseded here.
Two things happened after it was written: KC-S1b **admitted** a one-contact slot stage conditioned
on a sealed intent, which makes re-deciding the intent live an expense with a measured null
attached to it (KC-S1a, +0.09 pp); and MF-7b **closed** neighbour retrieval on intent while handing
on the filler side. KU-S3 keeps its name, its carrier, its roster and its budget line, and becomes
the consumption cell on the slot side. Nothing about the claim surface changes.

---

## 1. The cell

| item | value |
|---|---|
| run ids | `SAEA-SLURP-KU-S3-FILLERS-SPEECH-DEV1000-V1` (key **a**), `SAEA-SLURP-KU-S3-FILLERS-TWIN-DEV1000-V1` (the form twin), `SAEA-SLURP-KU-S3-FILLERS-SPEECH-STATE-DEV1000-V1` (key **b**) |
| profile | `bounded-discovery-probe` |
| policy | `phase-slots-given-intent-supplied-v1` — one phase `slots`, `knowledge: "supplied"` |
| baselines | `configs/baseline/slurp-phase-slots-supplied-fillers-speech-v1.json`, `-twin-v1.json`, `-speech-state-v1.json` |
| model / dataset | `q4km-mmproj-free-speech-native-np4-base-speech-query-prefix-max64`, `slurp-speech-native-dev1000` |
| decision population | the unexposed **NEW500** |
| comparator **and** equal-contact control | the SEALED KC-S1b rows (`SAEA-SLURP-KC-S1B-SLOTS-SCHEMA-DEV1000-V1`, manifest sha256 `088c9307a39f38db124a5204793806e9a8589d942259b15e7826ad2685fe8d08`) |

### 1.1 What is identical to KC-S1b, by construction

The system message, the instruction template (`probes/slurp_phase_slots.txt`), the state fill
(`slurp-intent-slot-schema-for-state`), the sealed predecessor manifest, the packet promotion
receipt, the decoding parameters, the serving geometry and the contact count. Proved, not asserted:
the wire check (section 7) resolves the system message to sha256
`4073f79ef25c4796b0a46cb2ac7f5d4982c83084982b87ddd8a70504090d37db`, which is the sealed closed-list
baseline's own instruction hash that KC-S1a and KC-S1b both carried.

**Nothing this cell adds can reach a control turn.** `rails.phase_supply` returns a hash-bound
`RankResult`/`FusionDecision` pair, never prompt text; `rails.runner._agent_messages` renders the
selected values as typed content blocks carrying `evidence_id`, `source_uri` and
`knowledge_role: "value"`. A supplied phase's instruction bytes are the same bytes the unsupplied
phase would send.

### 1.2 The two keys, and their order

The query vectors are the sealed 2026-09-06 MF-7b Omni-Embed-Nemotron-3B sets. Both are legal under
the owner's 2026-09-06 rule (`QUERY_SIGNAL_MODALITIES`), both are preregistered, and they are
**ordered**:

**(a) `speech`** — `q-speech-nemotron`: the DEV-1000 recording alone, prompt `query: ` through the
encoder's own `sentence_transformers.jinja` wrapper. **This is the primary arm and it flies first.**

**(b) `speech+state`** — `q-speech-nemotron-fused`: the same recording fused *inside the encoder*
with that row's own sealed KU-S1c phase-1 draft text.

Why (a) first, on two grounds that agree.

1. **The quantity this cell consumes does not separate them.** MF-7b measured filler recall@5 at
   **43.46** for speech alone and **42.85** for the fused key, against the draft key's 31.47. The
   fused key's advantage — recall@5 87.40 against 83.20, vote 75.80 against 71.80 — was measured on
   **intent**, which this cell does not consume and which MF-7b closed.
2. **(b) reaches further outside the cell.** Its state half is another program's sealed output
   (KU-S1c's draft phase), so an arm built on it is one step further from KC-S1b and carries KU-S1c's
   provenance as well as its own. (a) needs nothing but the recording.

Key (b) is registered now, at the same k, knobs, snapshot and twin, so that flying it later is a
pinned hash and a declared modality rather than a new design. **It flies only if (a) is not HARMFUL**,
and it is read as a second, separate cell — never pooled with (a), never selected after the fact.

### 1.3 The predecessor binding does **not** project

`predecessor_binding: "sealed-manifest"` with **no** `fill_params.projection`, exactly as KC-S1b
flew. The headline comparator is KC-S1b's SEALED rows, which chose their per-intent schema blocks
from **unprojected** bytes; the v2 verdict measured that projecting turns 39 of KC-S1b's 42
full-schema fallback rows legal and lands 17 of them on the gold intent. An arm that projected while
its comparator did not would beat that comparator partly by **better block selection** rather than by
the supplied fillers, and the one factor would no longer be one factor. This is the same ruling
`configs/baseline/slurp-phase-slots-given-intent-schema-projected-v2.json` already states for the
EVO-S1 DEV-1000 final read, applied here for the same reason. Measured on the sealed bytes this cell
will actually send: **59 distinct schema blocks over 1,000 rows, 42 of them the 26,720-character
full-schema fallback**, 494 / 898 / 26,720 characters at min / median / max.

### 1.4 The form twin

`SAEA-SLURP-KU-S3-FILLERS-TWIN-DEV1000-V1` runs the **identical mechanism** — same provider, same
knobs, same k, same snapshot, same rendering, same contact, same instruction bytes — keyed by
**another DEV row's speech vector**. The permutation is
`saea-kus3-within-predicted-scenario-derangement-v1`: rows are bucketed by the scenario their
**sealed closed-list response names** (the prediction, never gold — the same information the phase's
own state fill already conditions on), and inside each bucket the sorted sample ids are rotated by
one. Measured: 24 buckets, **0 rows receive their own vector**, 3 of 1,000 cross a bucket (the three
singleton buckets `movies`, `sport`, `sports`, pooled and rotated among themselves).

The twin delivers the preregistered "same number of typed blocks with fillers drawn from random
TRAIN rows of the same scenario" **through the mechanism itself**: the neighbours are real TRAIN
utterances retrieved for a real recording of the row's own predicted scenario, so they carry
scenario-typical types at scenario-typical rates, and the retrieval stack is held fixed. It is a
strictly stronger control than a uniform draw from the scenario's TRAIN rows — which would break the
neighbourhood structure as well as the alignment — and it needs no new code path.

**Token-matched by construction, not by a cap — and measured.** Running the cell's own pre-flight
decision path over the first 30 DEV-1000 rows for all three query files:

| arm | blocks per row (min–max) | blocks total | supplied chars per row (min / p50 / max) | blocks carrying no filler |
|---|---|---|---|---|
| key (a) `speech` | **5 – 5** | 150 | 354 / 422 / 570 | 35 of 150 (23.3 %) |
| the **twin** | **5 – 5** | **150** | **354 / 422 / 570** | 40 of 150 (26.7 %) |
| key (b) `speech+state` | 5 – 5 | 150 | 351 / 435 / 555 | 42 of 150 (28.0 %) |

Five blocks on every row of every arm, and a character volume whose min, median and max agree to the
character between the arm and its twin. Per the owner's 2026-09-06 ruling, token counts are advisory:
the twin is the lock, and the supplied character volume is reported as a covariate beside every
contrast.

The one worked example says what the factor is. For `slurp:devel:000011` — the row whose sealed
prediction is `iot / hue_lightoff` — key (a) supplies `house_place=bathroom`, `house_place=bed room`,
`house_place=kids bedroom|room`, `house_place=room` and `color_type=red`, while the twin supplies
five TRAIN utterances that carry **no filler at all**. Same five blocks, same shape, same cost.

---

## 2. The provider seam check (model-free)

**Question.** Does an existing registered provider render neighbour fillers as typed values from the
sealed vectors, or is a thin `neighbour-fillers-v1` needed?

**Answer: `kb-facet-v1` is exactly right and no new provider is admitted. What a provider cannot do
is author the block — so the work that *was* needed is a knowledge-BUILD derivation, not a fourth
provider class.** Three findings, in the order they were measured.

### 2.1 `kb-facet-v1` already selects what this cell wants

`rails.knowledge_provider.KbFacetProvider` recalls through `rails.kb_policy.multidim_recall`, which
scores a facet by cosine between `query_vectors[dimension]` and `facet_vectors(facet_id)[dimension]`.
The MF-7b TRAIN key vectors are keyed **`facet:content:<slurp_id>`** — already, exactly, the content
facet ids `rails.knowledge_build` mints. Nothing needs to be re-keyed, re-embedded or adapted.
`dense-centroid-v1` is the Audio2Tool tool-tier index and has no SLURP artifact to build from;
`conec-context-v1` is an Earnings evidence source. A `neighbour-fillers-v1` would have had the same
inputs, the same cosine and the same output as `kb-facet-v1`, and would have been a second copy of a
base the owner's engineering rules name as *the* base.

### 2.2 The provider does not author the typed block — the SNAPSHOT does

`rails.runner._agent_messages` renders `ValueBundle.content` **verbatim** for every value visible in
the `QueryState`. `KnowledgeProvider.materialize` is not on the phase-supply path at all (the
KU-S1 v2 preregistration removed the fold with no fallback). So a provider chooses *which* values;
the snapshot decides *what they say*. A `neighbour-fillers-v1` could not have changed one character
of what reaches the model.

### 2.3 Two measured facts forced a slot-filler view of the snapshot

**(i) The exemplar view refuses this cell's prompt on every row.**
`rails.runner._assert_agent_control_excludes_knowledge_payloads` protects every facet
representation and every value content of the BOUND snapshot by raw substring at an eight-character
floor. A supplied cell must bind the `content` dimension it recalls on, and that dimension's facet
representations are 11,514 raw TRAIN utterances. Measured 2026-09-07 against KU-S3's own per-row
instruction (directive + sealed state + schema fill), over the content-dimension snapshot:

| protected material | instructions refused |
|---|---|
| content-dimension **facet representations** (11,404 payloads ≥ 8 chars) | **1,000 of 1,000** |
| content-dimension **value contents** (11,514 payloads) | **0 of 1,000** |
| facet representations vs the 1,000 sealed closed-list states alone | 78 (58 of them `calendar`) |
| facet representations vs the 59 distinct schema blocks alone | **59 of 59** (`how much` hits every one) |

The 78 reproduces KC-S1b's own deviation-1 number exactly, from the same bytes. The top collisions
are ordinary English — `how much`, `donald trump`, `shopping`, `train wreck`, `calendar`,
`learning games` — not knowledge payloads: they are false positives of a substring rule applied to
one- and two-word utterances. KC-S1a/b escaped by **dropping** the content dimension. A cell that
recalls on content facets cannot, which is precisely the ruling KC-S1b's deviation 1 asked the owner
for.

**(ii) The exemplar VALUE supplies a closed mechanism and duplicates an admitted one.** It reads
`Exemplar sentence: "…" -> intent alarm_set (scenario=alarm, action=set). Slot type=filler pairs: …
<surface-form variants> <entity-type prior for that intent>`. Naming the neighbour's intent is the
mechanism MF-7b closed; restating the entity-type prior duplicates the block KC-S1b already sends
and would confound the contrast against it.

**The derivation, and it is thin.** `scripts/build_knowledge_snapshot.py --view slot-fillers` (a new
`KnowledgeBuildSpec.view` field on the existing registered builder `saea-kb-distmodel-v1` — no new
module, no new class, no new registry id) changes exactly two rendered strings:

* a content facet's representation **quotes** its utterance inside a descriptor —
  `TRAIN utterance 1 (slot-filler retrieval key): "wake me up at nine am on friday"` — exactly as the
  `label` / `speaker` / `prior` dimensions already describe rather than *are* their payload;
* a value becomes that utterance's fillers alone —
  `Slot type=filler pairs observed in TRAIN utterance 1: date=friday; time=nine am.`

Same selection, same facet ids (so the sealed key vectors bind unchanged), same value ids, same
`prior_score`s, same source samples, same provenance. Snapshot
`knowledge/slurp/saea-kb-distmodel-v1/size-full-content-slot-fillers/snapshot.json`, sha256
`2c43147780b60fe64a3f46de5e9f6ab28b053f3a28a6900b2a92c04591541cf6`, 11,514 facets and 11,514 values,
intent and entity-type coverage 1.0000, KL 0.000000, decontamination clean. Receipt
`docs/receipts/knowledge/slurp-kb-size-full-content-slot-fillers.json`.

**The leakage rule stays at full strength** over everything a control turn could actually paste —
all 11,514 values, and the utterance itself the moment anyone sends it with its own key text — and
measures **0 of 1,000** collisions against this snapshot's 23,028 protected payloads. **Every
committed snapshot keeps its bytes**: `size-full`, `size-1000`, `size-5000` and
`size-full-label-prior-speaker` were rebuilt to their committed sha256s, because the build
descriptor gains a `view` key only for a non-default view.

### 2.4 Two seam repairs the preparation found, both in `core/flight/runtime.py`

1. **A supplied FIRST phase was refused even for `kb-facet-v1`.** `_resolve_phase_supply` raised
   unless `bind_phase_supply_providers` had been called, on the stated ground that the seed decision
   "has to be computable before the flight". For `kb-facet-v1` it already is: `build_supply_for_phase`
   constructs it from the frozen snapshot and publishes the factory on
   `supply_for_phase.provider_factories`, which is what `_phase_supply_seeds` reads. The guard was
   over-broad, and it forced exactly the launcher script the owner's engineering base rules forbid.
   It now names the provider and refuses only the ones this seam cannot construct.
2. **`_phase_supply_seeds` read `self._plan`, which `wire_check` never sets.** The one cell shape
   that seeds a first phase could not be wire-checked at all (`AttributeError: 'NoneType' object has
   no attribute 'split_identity_hash'`). It now takes the plan **driving this dispatch**, which is
   the same object in a real flight and the wire-check plan in a wire check. Found by wire-checking
   the cell, which is the case the method exists for.

Both are inside the base, both are a few lines, and `python scripts/checks/engineering_base_check.py`
returns PASS.

---

## 3. Knobs: the BLEND lock's do not transfer, and that was measured first

The DEV-1000 BLEND lock's `tau 0.65` is a percept-admission threshold calibrated on a **text** query
against **text** keys, where Nemotron's own text-space neighbour cosine is about 0.87. This cell's
query is a **speech** vector. Measured model-free over 20 DEV-1000 rows against all 11,514 keys:

| quantity | min | mean | max |
|---|---|---|---|
| top-1 cosine, key (a) `speech` | 0.2232 | **0.3975** | 0.5522 |
| top-5 cosine pooled, key (a) | 0.2123 | 0.3861 | 0.5522 |
| top-1 cosine, the twin | 0.2232 | 0.3816 | 0.5323 |
| top-1 cosine, key (b) `speech+state` | 0.3043 | 0.4267 | 0.4952 |

| tau | top-5 candidates admitted | rows keeping any value |
|---|---|---|
| **0.65 (the lock's)** | **0 of 100** | **0 of 20** |
| 0.50 | 11 of 100 | 3 of 20 |
| 0.40 | 46 of 100 | 10 of 20 |
| 0.30 | 81 of 100 | 18 of 20 |
| **0.00 (registered)** | 100 of 100 | 20 of 20 |

At the lock's tau this cell supplies **nothing, on every row** — and it fails silently, because a
sample whose recall admits nothing simply runs unsupplied, which is lawful. The wire check caught it
as "this cell declares `phase_supply` but not one request carried a typed knowledge block".

Registered knobs, and why each is what it is:

* **`tau: 0.0`.** `multidim_recall` has *already* truncated to the top `k = 5` by cosine. A further
  admission threshold can only subtract from the mechanism this note preregisters, which is "the
  top-5 neighbours". Setting it to a re-tuned cross-modal value would be choosing a knob on a
  distribution measured from the decision carrier, which this study does not do.
* **`fuse_coverage: {m: 5, c: 5, top_l: 5}`.** The lock's `c 2 / top_l 3` is a coverage reshaper that
  groups candidates by intent and keeps two per intent for the top three intents — which would make
  the block **count** depend on how many intents the neighbourhood spans, and would let the twin and
  the arm differ in volume for a reason unrelated to the factor. Five in, five out, on both arms.
* **`rank_weights: {w_cos: 1.0, w_prior: 0.0, w_agree: 0.0}`.** An identity on the ordering — with a
  content-only snapshot no `PRIOR_MASS` dimension is recalled, so the prior term is structurally 0.0
  and the agreement term structurally 1.0 — and it makes the ranked score **equal the cosine** in the
  trace. It also says out loud that this cell ranks on speech-to-text similarity alone, never on how
  common a neighbour's intent is.
* **no `alpha`.** A one-phase program has no prior answer to blend against; `retain_prior` never
  fires and the program always runs its single contact.

**A property of the corpus this cell cannot hide.** 3,755 of the 11,514 TRAIN utterances (**32.61 %**)
carry no entity at all, and they are legitimate keys. Their value renders
`… none recorded.`, so roughly a third of supplied blocks carry no filler — measured at 23.3 % on the
arm and 26.7 % on the twin over the first 30 rows, both under the corpus rate, which is the retrieval
doing a little work. That is exactly why MF-7b's filler recall@5 is 42.85 rather than higher, and it
is reported as a covariate, not designed away: restricting the key space to filler-bearing utterances
would change the key space MF-7b measured and is registered here only as a named, unflown variant.

---

## 4. Vectors as sealed sources

No new embedding pass. `scripts/build_slurp_kus3_vectors.py` re-encodes the sealed MF-7b files into
the `sealed-vectors` schema `rails.phase_supply.load_sealed_vectors` reads
(`{"id": …, "vectors": {"content": […]}}` rather than MF-7b's dimension-free `{"id": …, "vector": …}`),
verifying each source against the MF-7b receipt's own sha256 first and reading each written file back
through the flight's own loader afterwards. Exposure row `SAEA-SLURP-KU-S3-VECTORS-V1`
(`model-free-check`): **0 frozen-core contacts, 0 tool contacts, 0 embedding contacts, 0 GPU hours,
0 paid spend**, 72.5 s wall. Receipt
`docs/checks/speech-aware-evidence-acquisition/2026-09-07-slurp-kus3-vectors/vectors.json`.

| file (`$SPEECHRL_DATA_DIR/vectors/slurp-kus3/`) | role | rows × dims | sha256 | produced by |
|---|---|---|---|---|
| `facet-vectors.jsonl` | key | 11,514 × 2048 | `5dfe75231c12f2624913988e4643c51b74856465bdbd108358b4f371dacffc1e` | MF-7b `nemotron-train-text` |
| `query-vectors-speech.jsonl` | query (a) | 1,000 × 2048 | `99b2e1700a058640a12c86fb261e3fc1898cd99004b0157366682b2a048b2e7c` | MF-7b `q-speech-nemotron` |
| `query-vectors-speech-state.jsonl` | query (b) | 1,000 × 2048 | `a17382eb57149a49a69cda2ee5afbefe024ed5ad8d38e9b15b774d9038ed92b2` | MF-7b `q-speech-nemotron-fused` |
| `query-vectors-speech-twin.jsonl` | query (twin) | 1,000 × 2048 | `64e99d51f145e88ad1d8172c465968a2c61166605cbb45fb9162329f92508a12` | MF-7b `q-speech-nemotron`, deranged |

All four read back through `load_sealed_vectors` at **max abs delta 0.0**; every L2 norm is 1.0 to
seven decimals. The two contact rows that produced the floats are
`SAEA-SLURP-MF7B-NEMOTRON-EMBEDDING-V1` (13,575 embedding tool contacts, 0.1101 GPU-h, jitter pair
bit-exact) and, for the state half of key (b), the sealed
`SAEA-SLURP-KU-S1C-DRAFT-REVISE-DEV1000-V1` draft text.

**Declared signals**, which ride the config hash and are therefore part of what each cell IS: key (a)
`speech: …`, key (b) `speech+state: …`, the twin `speech: … of ANOTHER row …`. The twin's modality
token is `speech` because its vectors *are* speech vectors — of another recording; the free-English
half says whose. The facet side declares `text:` and is unconstrained, as
`rails.phase_supply` intends: a key is knowledge text by construction.

**Nothing is missing.** Every vector file this cell and its twin need exists, is hash-pinned and is
loadable by the flight's own reader.

---

## 5. Budget, and the cost the seeding actually carries

Run-cumulative across every attempt of a run id, enforced by `core.model.adapter` against a fresh
sibling read of durable attempt actuals. At most **one** recovery re-registration per run id; a
second failure stops the flight and the fix is proven on a 4-row dry run.

| run id | calls (ceiling) | speech seconds (ceiling) | GPU-h (ceiling) | tool | embedding | paid |
|---|---|---|---|---|---|---|
| `SAEA-SLURP-KU-S3-FILLERS-SPEECH-DEV1000-V1` | 1,000 + 8 canaries (**1,050**) | 2,884.7937 (**3,000**) | ~0.85 (**2.0**) | 0 | 0 | 0 |
| `SAEA-SLURP-KU-S3-FILLERS-TWIN-DEV1000-V1` | 1,000 + 8 (1,050) | 2,884.7937 (3,000) | ~0.85 (2.0) | 0 | 0 | 0 |
| `SAEA-SLURP-KU-S3-FILLERS-SPEECH-STATE-DEV1000-V1` | 1,000 + 8 (1,050) | 2,884.7937 (3,000) | ~0.85 (2.0) | 0 | 0 | 0 |

**The GPU-h ceiling is set by the PRE-FLIGHT SEED, not by the contacts, and this is the operational
finding of the preparation.** `rails.kb_policy._cosine` is pure Python and
`multidim_recall` scores **all 11,514** content facets per sample. Measured on this machine at
dim 2048: **198.1 µs per pair → 2.28 s per sample** in isolation, and **2.43 to 2.56 s per sample end
to end** through the real decision path over 30 DEV-1000 rows on all three query files — about
**0.68 to 0.71 h of single-threaded CPU for a 1,000-row roster**, against roughly 0.20 h of contacts
at `-np 4`. (Loading and re-hashing the 528.6 MB key file is not the cost: 8.6 to 10.1 s.)
`_phase_supply_seeds` runs inside `FlightRuntime._dispatch_phase_program`, so a resident serving
session idles through it.

Three things follow, and only the coordinator picks among them.

* **As registered**: run the seed while the model loads and let the always-on session serve other
  geometries meanwhile (the 2026-08-24 front-load rule and the 2026-09-07 always-on serving note).
  Budgeted at 2.0 GPU-h so the wall clock cannot trip the ceiling.
* **A bit-exact 3× is available and is NOT taken here.** `_cosine` recomputes both L2 norms for
  every pair; a norm computed once per vector is the *same float* (same summation order), so caching
  them would cut the seed to about 0.21 h per arm with byte-identical selections. It touches a base
  file under concurrent edit and it is not needed to fly, so it is named, priced and left to the
  coordinator.
* Not an option: sharding, approximating, or reducing k.

**`-np 4`, not `-np 16`.** Geometry-matching to KC-S1b is the point — its sealed rows are the
comparator, and greedy decoding is not bitwise reproducible across batch shapes. It is also the only
geometry that fits: the 42 fallback rows carry the full 60-intent schema at about 7,500 tokens on top
of a 7,583-character system message, so KC-S1b's worst envelope was 10,006 tokens. At `-np 16` the
65,536-token server context divides into 4,096-token slots and those rows do not fit at all.

**Prompt fit.** The supplied blocks add exactly five values per row, measured at **354 to 570
characters in total** over 30 rows (analytic worst case, five of the corpus maximum 254, is 1,270) —
roughly 100 to 160 tokens, on top of KC-S1b's measured worst envelope of 10,006 against the
16,384-token slot. The margin stays above +6,000 tokens. The
flight still measures the real envelopes through the resident server's `/apply-template` +
`/tokenize` before takeoff and pins a `prompt_fit_receipt` + `prompt_fit_receipt_sha256` pair into
the fragment, exactly as KC-S1b did: `FlightRuntime`'s own pre-flight estimator is not evidence for a
cell like this (KC-S1 deviation 3).

---

## 6. Analysis and decision rule (frozen before the read)

`analysis.paired.paired_contrast`, delta = arm minus comparator on per-sample official scores,
stratified bootstrap **N = 10,000**, strata = the gold scenario, **seed 20260903**, **CI90**, exact
sign test. Metrics: per-sample slot F1 (exact type+filler), per-sample SLU-F1, slot precision, slot
recall, entities strict, Word-F1, Char-F1, and intent (scen_act, asserted identical). Both
weightings reported: natural mixture and equal-stratum. Per-stratum table with the published column
beside the repo column.

Scoring is the dataset's standard scorer: the real, unmodified official `evaluate.py` at pinned
commit `8eb16545762be97ace75334109d73824217311f1` in `~/.venvs/slurp-official-eval`,
`--average micro`, run **once over the complete manifest** through `core.scoring_batch`, never
sharded, with the official-vs-port identity check.

**Decision rule.**

* **ADMITTED** iff, on the unexposed **NEW500**, the per-sample SLU-F1 **CI90 lower bound is above 0
  against the sealed KC-S1b rows** AND the **(KU-S3 minus the form twin) CI90 lower bound is above 0**.
  The second condition is the whole point: five extra typed blocks must not be worth anything unless
  they are *this row's* neighbours' fillers.
* **NULL** if either interval includes 0. Supplied neighbour fillers then join neighbour intent as a
  closed branch on this carrier, and KC-S1b stays the SLURP slot mechanism.
* **HARMFUL** if an upper bound is below 0; the consumption branch on SLURP ends with its
  form/content attribution recorded, and key (b) does not fly.

**Intent is identical by construction** on every arm — the sealed closed-list prediction is the
input, and the projection overwrites scenario and action row by row — and is asserted row by row, as
in KC-S1a/b. A non-zero intent delta is a defect, not a result.

**The greedy-noise reference, stated before the read.** EVO-S1 round 1 measured, on this carrier and
this build, that **286 of 1,019 byte-identically prompted rows (28.1 %) returned different text
anyway**, and that 31 rows moved their reward on an unchanged prompt against 4 on a changed one. Any
claim read off a handful of moved rows is below that floor. KC-S1b's own admitted margin was 60 saves
against 2 harms on NEW500 with a CI90 of [+8.11, +12.19] — far above it — and this cell is held to
the same standard: the CI90 lower bound, on 500 unexposed rows, against two comparators.

---

## 7. Wire check, containment and the checks the preflight applies

**Wire check: PASS on all three arms**, 4 DEV-1000 rows each, on a clean tree, against
`WireCheckGate` and `WireCheckTransport` — **zero sockets, zero model contacts, zero GPU**, about
24 s wall each. It drove the real path: composition, the label-free roster with every media file
re-hashed, the snapshot load and hash verification, the `phase_supply` spec resolution, the sealed
vector load and re-hash, the `kb-facet-v1` construction, the pre-flight bootstrap selection, the
request build and the transport seam.

| assertion | result |
|---|---|
| model contacts | **0** on every arm |
| dispatch | `phase-program`, `program_id` `phase-slots-given-intent-supplied-v1`, `contacts_per_sample` 1, `supplied_phases` `["slots"]`, `seeded_supply_phases` `["slots"]` |
| barrier | whole-roster per phase (`rails.phase_runner.run_program`) — the only supplied phase is the seeded first one, so no continuous dispatch is needed |
| sealed vectors loaded and re-hashed | 1,000 query rows and 11,514 facet rows per arm |
| declared modality in the receipt | `speech` (arm, twin) / `speech+state` (key b) |
| payload keys equal the arm's visible fields | true, and they include `supplied_evidence` |
| typed knowledge blocks on the request | **present on every row** (the harness refuses the check otherwise, and did, before the knobs were corrected — that refusal is what caught the `tau 0.65` transfer error) |
| resolved system message | sha256 `4073f79e…37db` on every arm — **byte-identical to KC-S1b's** |
| config hashes | distinct per arm (the twin's is `ec55b6af…cc49`), because the query source rides the hash |
| four distinct request bodies | yes (one per sample, each with its own speech packet re-verified) |
| seal half | SKIPPED — `scripts/flights/run_slurp_closed_list_cell.py` pins `REPO` to the main checkout by design, so the worktree ran the request half only; the seal half runs on master before takeoff |

**The containment fold, on the real snapshot: 0 of 1,000.** The instruction the cell will actually
send, row by row (directive + sealed closed-list state + per-intent schema fill), against all 23,028
protected payloads of the bound slot-filler snapshot. Zero collisions — because the supplied values
travel as typed content and never as instruction text, and because the key descriptors are
descriptors.

**What the preflight applies to the typed blocks, in order.**

1. `assert_phase_supply_queries_carry_speech` on the raw fragment, before the program resolves: every
   `query_source.embedded_signal` must declare `speech` or `speech+state`. A text-only key is refused
   before a file is opened.
2. `load_sealed_vectors` re-hashes every vector file against the fragment's pin and refuses a
   malformed line, a duplicate id, an undeclared dimension, or two vectors of different width.
3. `load_phase_supply_specs` refuses a supplied phase the program does not declare
   `knowledge: "supplied"` for, and refuses any `provider` / `rank_policy` / `fuse_policy` that does
   not resolve in a `core.base` registry.
4. `_assert_agent_control_excludes_knowledge_payloads` on every contact instruction, against every
   facet representation and value content of the bound snapshot — the fold above, measured at 0.
5. `assert_knowledge_use_binding` on every acquire transition: query/snapshot sample disjointness,
   every hash edge, ranked-facet membership and the facet-to-value association. **The seeded
   first-phase route does not get this call** — there is no advance to carry an acquire transition —
   and the compensating evidence is that its decision is pre-flight and hash-pinned: a pure function
   of the config hash, the snapshot sha256 and two vector sha256s. That trade is stated in
   `rails.phase_supply.build_bootstrap_selection`'s own docstring and is restated here so the verdict
   carries it.
6. `rails.runner.run_speech_native_agent_loop` refuses any run whose query samples overlap the
   snapshot's `source_sample_ids`. This cell's queries are DEVEL and the snapshot is TRAIN, so the
   rule passes with nothing to do — but it is why the snapshot must never be rebuilt over devel rows.

**Echo, and how it is reported.** MF-7b's methodological result was to report the echo rate beside
any retrieval number. The analogue here is post-hoc and belongs to the verdict, not the preflight:
the fraction of answered entity mentions whose filler string appears **verbatim in a supplied block**,
reported for the arm and for the twin. A high echo on the arm with a low one on the twin is the
mechanism working; a high echo on both is the model copying whatever it is given, and would make the
twin contrast the only readable number.

---

## 8. Roster, populations and exposure

The whole frozen DEV-1000 runtime view, id for id, split identity hash
`8580d199bffc95a51ad6d8c5b2a2e9e39faa2c551dd095f8afcd78174a1e3c84`, receipt
`docs/receipts/probe-samples/DEV-1000.json`. **No new draw and no new exposure**: this is the roster
the sealed 2026-08-25 lock campaign, the 2026-09-05 closed-list direct baseline, KC-S1a/b, KU-S1c and
the two MF-7b embedding passes already read.

| population | n | receipt | role |
|---|---|---|---|
| DEV-1000-NEW500 | 500 | `docs/receipts/probe-samples/DEV-1000-NEW500.json` | **the decision population**; reported first |
| DEV-1000 pooled | 1000 | `docs/receipts/probe-samples/DEV-1000.json` | reported |
| DEV-500 (prior-exposed) | 500 | `docs/receipts/probe-samples/DEV-500.json` | reported separately, never pooled into a decision |

Gold never enters the flight process: samples are built label-free from the runtime view and the
adapter's `gold()` refuses outright; gold opens once, scoring-side, at the single registered read.
The held-out test split is never named, loaded or scored. Model-free preparation rows:
`SAEA-SLURP-KU-S3-VECTORS-V1` and `SAEA-SLURP-KU-S3-SNAPSHOT-V1`, both `model-free-check`, both
0/0/0.

---

## 9. What the flight agent must do, on master, in order

0. **Merge this branch and re-run the gates.** `python scripts/checks/engineering_base_check.py`
   and `pytest`; the two `core/flight/runtime.py` repairs of section 2.4 are load-bearing and a
   merge that drops either makes the cell unflyable (the first) or unwire-checkable (the second).
1. **Exposure rows written** for the prompt-fit, smoke and flight run ids, before any contact.
2. **Dry run** (`--dry-run`): preflight only, no server, no contact — where a stale vector hash or a
   text-only `embedded_signal` fails loudly and cheaply.
3. **Wire check** (`--wire-check`) on a clean committed tree, **with the seal half**, asserting that
   the per-request typed content-block count is non-zero on every row and that seal-and-score is not
   REFUSED.
4. **Prompt fit**, zero generated tokens, both arms, all 1,000 rows, with the real supplied blocks,
   through the resident server's `/apply-template` + `/tokenize`. Report the worst envelope against
   the 16,384-token slot; a negative margin STOPS the mission. Pin `prompt_fit_receipt` +
   `prompt_fit_receipt_sha256` into both fragments.
5. **4-row smoke** on four DEV-1000 rows fixed in a smoke fragment before they are read, proving on
   real rows: the seeded selection, the typed content blocks with `evidence_id` / `source_uri` /
   `knowledge_role`, the `-np 4` geometry, and exactly one sealed outputs row per sample. Its
   responses are a wiring proof and enter no verdict.
6. **Fly key (a), then the twin**, one attempt each, one seal each, on a clean tree for the whole run
   (a COMPLETED manifest reads `study_commit` at finalize and refuses a dirty tree). Two run ids, two
   plans, two exposure rows, one recovery allowance each — a shared run id would meter both arms
   against one budget.
7. **`core.scoring_batch`**, one job per complete manifest, never sharded, with the
   official-vs-port identity check.
8. **One registered read**, then the verdict
   `docs/readiness/2026-09-07-slurp-consumption-ku-s3-v1-verdict.md` and its `result-summary.json`.

**Reporting obligations, without exception.** The per-stratum table in both weightings; the realized
seed wall time and the realized contacts; the supplied-block count and character volume per row as a
covariate, for the arm **and** the twin, with the fraction of blocks that carried no filler; the
declared query-signal modality and the pinned vector sha256s, because both are part of the config
hash; the echo rate of section 7; the statement that the seeded route carries no
`assert_knowledge_use_binding` call and why; and the statement that the pre-flight query vector
cannot see this flight's own answer.

---

## 10. What this authorizes, and what it forbids

**Authorizes**: the three arms above, on DEV-1000, at the budgets of section 5, under the decision
rule of section 6, in the order of section 9 — and nothing else today. It fixes the roster, the
knobs, the comparator, the analysis and the reporting obligations so that flying is execution rather
than design.

**Forbids**, as always: any test-split contact; any superiority or generalization claim; any Stage-3
or paper-scale activity; any knob change or re-fly on the strength of a number; flying key (b) if key
(a) is HARMFUL; pooling key (a) and key (b); treating the sealed BLEND figures as this cell's
comparator; and any claim about what supplied evidence adds on SLURP drawn from a cell that has not
flown.
