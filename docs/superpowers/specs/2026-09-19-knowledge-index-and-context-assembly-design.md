# The knowledge INDEX and index-based context assembly — design draft v1 (owner decision 48)

Author: Claude Fable 5.1, root coordinator. Date: 2026-09-19. Tree: `fable/index` from `4aa47a42`.
Status: **DRAFT for owner review. Nothing here is decided, registered, admitted or authorised.**

Authority: **owner decision 48 of 2026-09-19**
(`docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`, section "Owner decision 48").
Owner, translated: *"What matters more is not fetching one particular piece of information but
fetching the information already in the context together with its related INDEX. What is important
is how the index is designed and ordered, and what the strategy for assembling context on the basis
of the index is."*

Design frame: `docs/superpowers/specs/2026-09-19-agent-base-lock-v2-draft.md` (the task abstraction
`T = (U, C, K, A, S)`, six nodes, 22 edges, the knowledge-plane primitives KN-1…KN-6, the three
supply channels); `docs/superpowers/specs/2026-09-17-node-context-policy-design.md` sections 3-5, 9,
16-19; `docs/superpowers/specs/2026-09-19-e18-acquisition-node-design.md`;
`docs/superpowers/specs/2026-09-19-e17-constant-tool-rendering-design.md`;
`docs/results/2026-09-19-slurp-throughput-root-cause-v1.md` (the measured cost model).

Machine-readable companion: `docs/receipts/knowledge-index-design-v1.json`.

**Model-free.** Zero model, tokenizer, encoder, scorer, tool, server and network contacts were made
while this document was written. Everything measured below was read from sealed run directories and
released knowledge snapshots under `SPEECHRL_DATA_DIR` (read-only) and from committed configuration.
No utterance text, no reference transcript and no gold of any row appears here or in the receipt.
Token counts are derived from the runs' own sealed `usage.prompt_tokens` and from character counts;
nothing was re-tokenised.

---

## 1. Principle and scope

### 1.1 What "index" means here

An **index** is a stable, addressable, ordered catalogue of the task's knowledge space `K`, rendered
into the **constant prefix** of every request, at a declared granularity, with **short ids the model
can cite**. It is not a retrieval result and it is not evidence. It is the map that makes a retrieval
result readable: the row's own context then carries **pointers** into the index (which entries this
row's speech selected, and how strongly) plus a **bounded expansion** (the full text of a few
entries), instead of the full text of everything retrieved.

Three properties define it and separate it from what the repository does today.

1. **Addressable.** Every entry has a short id the contract already legalises, so a node can name an
   entry without the entry's text being present, and a receipt can record which entries a node was
   pointed at and which it expanded.
2. **Constant.** The index does not depend on the row. It is therefore part of the prefix the
   llama.cpp per-slot KV cache keeps, which is what makes it nearly free (section 2.5).
3. **Ordered.** The order is declared — taxonomy first, then a within-group rule, then per-row
   pointers by score — and the order *is* the degradation order: what a context-budget COMPACT
   decision drops first is the tail of the expansions, never the index.

### 1.2 What changes against today's "render what was retrieved"

Today the pipeline is: rank a frozen store against the row's sealed speech vector, take the top `k`,
and render **the full content of every selected value** into `supplied_evidence` as
`[evidence <id>] <content>`. Selection is the only control; rendering is total. Measured on the
sealed B1 arm, one Solver contact carries 39 evidence items and 32,588 characters of store text
(section 2.3), and 24,057 of those characters are the slot-contract cards of at most three candidate
intents.

The index-centred design separates three things the current pipeline fuses:

| | today | under the index |
| --- | --- | --- |
| **what exists** | implicit; only the 60 intent ids and 55 entity types appear, inside the contract | explicit, at L0 (id + name) and L1 (one-line contract) for every entry of every store the episode may draw on |
| **what this row selected** | the full text of the selected values | a **pointer block**: ids, ranks, and the neighbour vote as `id x count` |
| **what the node reads in full** | everything selected | a **bounded expansion**, declared per node as a budget, ordered most-relevant-first |

The ORG axis of `wiki/Research-Objective.md` is "knowledge organisation and provenance"; the SUPPLY
axis is "evidence selection, amount, **order** and **timing**". Decision 48 is the statement that ORG
has so far been exercised as *store construction* only, and that the organisation the model actually
sees — the index and its order — is a separate, unexercised control.

### 1.3 Scope, and what this draft does not do

In scope: the index schema at three granularities, its ids and ordering, its measured sizes on the
released SLURP stores, the per-node assembly table, the staged expansion, the degradation order, the
receipts, the one config key, the cells that would test it, and the cross-carrier instances. Out of
scope, and stated once here and once in section 10: no cell, no preregistration, no exposure row, no
`ExecutionPlan`, no armed config, no code, and no claim about task quality. Every SLURP number quoted
from a verdict is a **development** number on TRAIN Fold A, which owner decision 28 forbids comparing
with a published test baseline; this document does not.

---

## 2. Today's prompt anatomy, measured

### 2.1 What was measured, and how

Source: the sealed B1 arm `SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TRAIN-FOLD-A-RECOVERY-V2`,
attempt `attempt-slurp-native-exemplars-k20-anchor-train-fold-a-generation-recovery-v2`, its
`<RUN_ID>.trace.jsonl` (507 MB, 34,693 records: 5,425 `MODEL_REQUEST`, 5,425 `COST`, 10,833 `USE`).
The first **20 distinct rows** were taken in flight order — 100 contacts, exactly 5.00 per row.

The sealed `MODEL_REQUEST` payload is the **canonical logical request**, not the wire body: its 19
keys are `task_instruction`, `supplied_evidence`, `evidence_provenance`, `history`,
`speech_feature_parts`, `tool_schemas`, `decoding_params` and the row's identity fields. The wire
body is rendered at call time by `reproduction/ojw/native_request.py` into exactly two messages,
`[system(str), user]`; under this arm's `prompt_order = "speech-query-prefix-v2"` the user content is
`[query speech part][stable text parts][key packets][mutable evidence + agent state]`, with the
node's own role query as the last user text part. Each part below was measured on the payload field
that renders into it, with the rendering overhead of `[evidence <id>] ` and
`[agent state <id> kind=<kind>] ` added explicitly.

Two **chars-per-token anchors** are used, both measured, neither re-tokenised:

* **3.67 chars/token** for contract- and inventory-shaped text — the throughput report measures the
  tools toggle at "about 2,220 tokens in" and the cached count on toggled contacts at 2,219 tokens
  against 2,224 when no toggle occurred, i.e. the 8,118-character system message is about 2,215
  tokens;
* **4.60 chars/token** as the median over the four roles of (this arm's rendered characters) /
  (its own sealed `usage.prompt_tokens`): 4.29 perception, 4.63 solver, 4.57 reviewer, 4.80 planner.

Every token figure below is given at both anchors or at the one that fits the text kind, and is
marked as derived.

### 2.2 The ordered parts, per role (medians over 20 rows)

Parts are listed in rendered order. "distinct" is the number of distinct SHA-256 values of that part
over the role's contacts in the 20-row window.

| # | part | perception | solver | reviewer (x2) | planner | distinct |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | system: `task_instruction` | **8,118** | **8,118** | **8,118** | **8,118** | **1 over all 100 contacts** |
| 2 | system: `tools` array | 0 | 0 | **221** | 0 | 1 value, reviewer only |
| 3 | user: speech packet reference | 149 | 149 | 149 | 149 | 20/20 (row) |
| 4 | user: evidence `intent-boundaries` (8 items) | 6,057 | 6,057 | 6,057 | 6,057 | 20/20 (row) |
| 5 | user: evidence `slot-contracts` (11.5 items) | — | **24,057** | **24,057** | **24,057** | 18/20 (row) |
| 6 | user: evidence `train-exemplars` (20 items) | — | 2,474 | 2,474 | 2,474 | 20/20 (row) |
| 7 | user: agent state `phase:perception` | — | 626 | 626 | 626 | row |
| 8 | user: agent state `phase:solver` | — | — | 229 | 229 | row |
| 9 | user: agent state `phase:reviewer` | — | — | 106 | 684 | row |
| 10 | user: agent state `tool-result` (contract replay) | — | — | 5,256 | **10,512** | row |
| 11 | user: role query (instruction + limits JSON) | 1,135 | 1,304 | 609 | 367 | **1 per role, over all rows** |
| | **total rendered characters** | **15,460** | **43,545** | **46,082** | **54,026** | |
| | sealed `prompt_tokens` (median) | 3,600 | 9,396 | 10,082 | 11,251 | |
| | chars per prompt token | 4.29 | 4.63 | 4.57 | 4.80 | |
| | completion tokens (median) | 118 | 19 | 34 | **2** | |

One row of five contacts: **205,194 rendered characters, 44,412 prompt tokens** (median sums,
Reviewer counted twice). The run's own manifest reports 49,388,949 prompt tokens over 5,425 contacts
on 1,080 rows, i.e. 45,730 per row — the 20-row window is representative to within 3 %.

### 2.3 Where the characters are

Of the **43,545** characters of the first Solver contact:

* **32,588 (74.8 %) is store text** — the three supply channels' selected values;
* 8,118 (18.6 %) is the contract;
* 1,304 (3.0 %) is the role query;
* 626 (1.4 %) is the only upstream model text in the request (the Perception candidate state);
* 149 (0.3 %) is the speech.

And of the 32,588 characters of store text:

| store | items | chars | share of the block | share of the Solver prompt |
| --- | ---: | ---: | ---: | ---: |
| `slot-contracts` (candidate slot cards) | 11.5 | **24,057** | **73.8 %** | **55.2 %** |
| `intent-boundaries` (Perception's k = 8) | 8 | 6,057 | 18.6 % | 13.9 % |
| `train-exemplars` (module M1, k = 20) | 20 | **2,474** | **7.6 %** | **5.7 %** |

**Finding F-1.** Owner decision 46 was answered on the premise that the k = 20 exemplar supply is
"the largest prompt-token contributor". The bytes say otherwise: the exemplar block is **2,474
characters, 7.6 % of the evidence block and 5.7 % of the Solver's prompt** — 123.7 characters per
exemplar, because an exemplar value is one construction utterance (median 69 characters) plus a
12.9-character `task_target`. The throughput report's lever L3 figure ("about 48 % of a row's
prefill") is the **whole** supplied-evidence block, three quarters of which is the candidate
slot-contract cards. Compressing k from 20 to 10 removes about 1,237 characters per contact, roughly
270 tokens; pointerising the slot-contract expansion removes about 24,057 characters, roughly 5,230
tokens. They differ by a factor of 19.

### 2.4 What is constant and what is row-specific

| class | parts | bytes per row | position |
| --- | --- | ---: | --- |
| **constant over the whole run** | `task_instruction` (1 distinct SHA-256 over all 5,425 requests of the run), the `tools` array (1 value) | 8,118 + 221 | **first** — the system message |
| **constant per role, over every row** | the role query (perception 1,135 / solver 1,304 / reviewer 609 / planner 367) | 3,415 per row | **last** — after every row-specific part |
| **constant within a row, across its contacts** | the whole supplied-evidence block (1 distinct value inside a row) | 32,588 | middle |
| **row-specific** | the speech packet reference, the evidence selection, every agent state | — | middle and late |

**Finding F-2.** The role query is **byte-identical across rows** for each role and is rendered
**last**, behind every row-specific part. 3,415 characters per row of perfectly constant text sit in
the one position where the prefix cache can never reach them. Nothing in this design depends on
moving it, but any prompt-order work should know it.

**Finding F-3.** Every supplied evidence item carries `knowledge_role: "value"` — 182,233 of 182,233
items in this run — so the transport's cache-explicit key/value split puts **nothing** in the stable
prefix: `stable_text_parts` is empty and the entire knowledge block lands in the mutable suffix. The
machinery for a constant knowledge prefix already exists in the transport and is unused. The index is
exactly what belongs on its key side.

**Finding F-4.** The supplied-evidence block is byte-identical across the Solver, both Reviewer and
the Planner contacts of one row. Its whole cost is therefore the **Solver's first render**, which is
one place to intervene rather than four.

### 2.5 The cache economics, measured

From `docs/results/2026-09-19-slurp-throughput-root-cause-v1.md`, joined per slot with 100.00 %
agreement between the server's `n_tokens - generated + 1` and the client's `usage.prompt_tokens` on
all 5,425 contacts of this run:

| position | role | tools | prompt (med) | prefilled (med) | cached | packet re-decoded | prefilled/row | share |
| ---: | --- | :--: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | perception | 0 | 3,597 | 1,373 | **61.8 %** | 100 % | 1,374 | 5.2 % |
| 1 | solver | 0 | 9,960 | 6,591 | 36.1 % | 0 % | 6,258 | 23.9 % |
| 2 | reviewer #1 | **1** | 10,062 | 7,843 | 23.6 % | 100 % | 7,505 | 28.7 % |
| 3 | reviewer #2 | 1 | 11,813 | 1,757 | 83.5 % | 1.4 % | 1,859 | 7.1 % |
| 4 | planner | **0** | 11,805 | 9,586 | 19.8 % | 100 % | 9,109 | 34.8 % |

Two facts from this table are the whole economic basis of the design.

**The constant prefix is paid once per SLOT, not once per row.** Perception is the first contact of a
row and still caches **61.8 %** — 2,224 tokens, exactly the system message — because
`decoding_params.id_slot` is `per-sample`, the slot's KV prefix survives between rows, and the
previous row on that slot left the identical system message behind. A 1,080-row flight at `-np 4`
therefore prefills the system message **4 times**, not 1,080 times. Adding N tokens to the constant
prefix costs `4N` tokens per flight — at N = 3,526 that is 14,104 tokens over 1,080 rows, or
**13 tokens per row**. Against a row that prefills 25,933 tokens today, the index is free.

**The toggle, not the size, is the cost.** The `tools` array is **221 characters** — 0.4 % of the
Planner's prompt — and its appearance at contact 3 and disappearance at contact 5 costs **63.5 % of
the row's prefill**, because the Qwen3-Omni template renders `tools` inside the system message and
each toggle invalidates everything behind it, the speech packet included. Item **E17**
(`native_episode.tool_schema_rendering: "constant"`) removes the toggle; the efficiency cell EFF-1
is its admission and its four-row smoke closed structurally on 2026-09-19 (commit `ce1c5a36`).

**Consequence for ordering.** The index is only free while the prefix is stable. **This design is
conditional on E17**: without constant tool rendering, the prefix breaks twice per row and a longer
prefix is a longer thing to re-prefill. The index cell must fly **after** EFF-1 seals and reads
NEUTRAL.

### 2.6 Two more costs the index design has to respect

**The contract replay.** The Planner's prompt carries a 10,512-character `tool-result` agent state —
the task-contract tool's observation, replayed verbatim — while the same Planner's system message
already carries the contract. That is **19.5 %** of the Planner's prompt spent restating the one part
of the prompt that never changes. Cell **B7c** (lever L4) is registered to render it by reference and
is held. If the index lands in the system message, the replay grows with it unless B7c lands first.

**The fit gate and the geometries it opens or forecloses.** Item E17 repaired `_assess_prompt_budget`
to budget against the live serving slot, with the reserve `min(8192, slot // 8)` below 32,768: at
np4 x 24,576 that is a 3,072-token reserve and **21,504 usable tokens**. The companion analysis of
owner decision 45 (`docs/results/2026-09-19-slurp-serving-geometry-and-degradation-v1.md`,
branch `fable/geometry`, section 2.4) measures the post-L1 prompt tail at p99 12,816, p99.9 13,930,
**max 14,524**, and reads the constraint table as: np4 fits with a 7,000-token margin, np5 (17,024
usable) fits, **np6 (14,336 usable) is refused by 188 tokens**, np8 (10,752) is refused outright —
while modelling np6 at **+7.5 %** and np8 at **+11.8 %** throughput once the flight became co-bound.

An **index-only** arm adds about 3,526 tokens to every contact. It still fits np4 (18,050 + the
512-token completion ceiling against 21,504), but it **forecloses np5 and np6** — the two geometries
the decision-45 analysis identifies as the next lever. The index **with** its pointer block moves the
maximum the other way: 14,524 − about 5,230 + 3,526 = about **12,820 tokens**, which fits np6's
14,336 with 1,516 to spare and turns "refused by 188 tokens" into admissible. The two halves of the
mechanism therefore do not merely belong together for tidiness; they decide whether the next serving
lever exists (sections 5.2 and 6.3).
---

## 3. The INDEX schema, cross-carrier

### 3.1 Entry kinds

An index entry is one addressable unit of the knowledge space `K`. The kinds are carrier-specific;
the **schema** is not.

| carrier | entry kind | what one entry is | count | source of truth |
| --- | --- | --- | ---: | --- |
| SLURP | `intent` | one of the closed 60 legal intents | **60** | the contract's own inventory; `intent-boundaries-v1/v2` cards |
| SLURP | `slot` | one entity type | **55** legal / **54** carded | the contract's type line; `slot-contracts-v2` cards |
| SLURP | `edge` | one construction confusion pair `(intent, neighbour)` | **81** over 44 intents | `scenario-hints-v1` (E14) |
| SLURP | `exemplar` | one annotated construction utterance | **9,354** | `size-pool-annotated-exemplars` (M1) |
| contextual ASR | `entity` | one governed name / lexicon term | per release | `participant-roster-v1`, `document-lexicon-v1`, ConEC name and bias lists |
| contextual ASR | `unit` | one registered 90-second window of a call | **1,593** over 44 calls | the registered slice identity |
| Audio2Tool | `tool` | one row of the 152-tool registry | **152** | `render_tool_schemas` / `audio2tool-registry-compact` |
| Audio2Tool | `domain` | one domain group over the registry | per compilation | the ORG-1 grouping (`audio2tool-registry-grouped`) |
| Audio2Tool | `parameter` | one action's parameter semantics | per compilation | `parameter-meaning-v1` |

The **exemplar** kind is the one kind that is deliberately **not** rendered into the constant index:
9,354 entries at 123.7 characters each is 1.16 MB. Exemplars are pointer-and-expansion only. This is
the schema's own rule: **an entry kind enters the constant index only when its whole L1 rendering
fits the prefix budget; otherwise it is reachable by pointer and by expansion alone.**

### 3.2 Ids: a grammar the model can cite

The repository already has two id conventions and they do not agree. The evidence ids the model sees
today are `intent-boundaries::intent-boundary:play_music` (48 characters) and
`train-exemplars::value:10005` — a store name, a value namespace and a key. The contract, meanwhile,
legalises the bare `play_music`.

Proposed grammar, one line, carrier-neutral:

```
<kind-sigil><name>            intents:  I/play_music        slots:  S/artist_name
<kind-sigil><name>~<name>     edges:    E/play_music~play_radio
<kind-sigil><n>               exemplars: X/10005            tools:  T/setColorTemperature
```

Rules, and why each is a rule rather than a preference:

1. **The name is the one the contract already legalises**, verbatim. `play_music`, not a synonym, not
   a number. A citation the model emits is then checkable against the same closed inventory
   `saea-deliver-normalise-v3` and the official scorer use, and a hallucinated id is detectable by
   membership rather than by parsing.
2. **One sigil per kind, one character.** `I` `S` `E` `X` `T` `D` `P` `U`. The cost of the whole id
   space is then the names, which are already in the prompt: the 60 intent names are 826 characters,
   the 54 slot names 615.
3. **No store name in the id.** Which store an entry came from is provenance; it belongs in the
   receipt and in the supply record, not in the token stream the model reads 5 times per row. Today's
   `intent-boundaries::intent-boundary:` prefix is 34 characters repeated on every one of the 8
   Perception items — 272 characters per contact, 1,360 per row, for information the model cannot
   act on.
4. **Ids are stable across releases of the store.** `I/play_music` survives a re-pin from
   `intent-boundaries-v1` to `v2`; only the L1/L2 text behind it moves. This is what lets a store
   re-pin cell (B4b's form) and an index cell be separate factors.

### 3.3 Granularity: L0, L1, L2

| level | what an entry renders as | where it lives | who may read it |
| --- | --- | --- | --- |
| **L0** | id + display name | the constant prefix | every node, always |
| **L1** | id + **one line**: the entry's operative contract | the constant prefix | every node, always |
| **L2** | the entry's full released card | the **row's expansion block**, budgeted | the node whose expansion budget admits it |

The released stores already have the L1 line inside them. Both authored SLURP stores are written as
labelled sections, and the sections are separable:

| store | sections per card | rows | distinct values | total chars | mean |
| --- | --- | ---: | ---: | ---: | ---: |
| `intent-boundaries-v1` | `Activation boundary` | 60 | **60** | 4,244 | 70.7 |
| | `Confusable exclusions` | 60 | **60** | 7,301 | 121.7 |
| | `Uncertainty behavior` | 60 | **1** | 11,940 | 199.0 |
| | `Limitations` | 60 | **15** | 12,362 | 206.0 |
| `slot-contracts-v2` | `Admissible formats` | 54 | **54** | 5,352 | 99.1 |
| | `Extraction cues` | 54 | **54** | 12,928 | 239.4 |
| | `Intent bindings and semantic roles` | 54 | **54** | 24,877 | 460.7 |
| | `Ambiguity behavior` | 54 | **54** | 6,997 | 129.6 |
| | `Missing behavior` | 54 | **8** | 8,513 | 157.6 |
| | `Limitations` | 54 | **54** | 16,725 | 309.7 |

**Finding F-5.** The `Uncertainty behavior` section of the intent store is **one identical 199-character
string repeated on all 60 cards** — 11,940 characters, **28.3 % of the whole store** — and
`Limitations` has only **15 distinct values over 60 cards**. On the slot store, `Missing behavior`
has **8 distinct values over 54 cards**. Shared guidance is being paid for per card, at the moment of
retrieval, in the uncacheable part of the prompt. The repository has already built the repair:
`intent-boundaries-factored-v1` (61 values, `build_factored_intent_boundary_snapshot`) collapses the
per-intent card from **702.2 to 297.2 characters mean, 42,133 to 18,127 total, −57.0 %**, by lifting
the shared guidance into one value. The base-lock table records it as "superseded / unused". An index
is exactly the place that shared value belongs: once, in the prefix, as the section header of the
whole intent index.

### 3.4 Ordering

The ordering rule has three levels and is declared, not emergent.

**(a) Taxonomy first.** SLURP intent ids *are* the taxonomy: every legal id is `<scenario>_<action>`
over **18 scenarios** and **60 pairs**, and the contract's `slurp-label-inventory` fill already
renders them grouped — 18 lines, one per scenario, 1,029 characters, plus a 805-character entity-type
line, 1,834 characters in total. **The L0 index already exists and is already paid for.** What is
missing above it is L1 and below it the pointer discipline.

**(b) Within a group, by construction frequency.** The construction pool (9,354 utterances, split
identity `67e53fb5…`) gives each intent a row count; `scenario-hints-v1` carries it as `rows`. Within
a scenario, most-frequent first. This is a construction statistic, not a gold-derived one, and it is
the same pool E12, E14 and M1 all pin.

**(c) Confusion edges beside their intent.** `scenario-hints-v1` holds 81 `(intent, neighbour)` pairs
over 44 intents (16 intents have no neighbour, 18 have one, 15 two, 11 three) and 231 cue rows over
130 distinct cue words. An edge is rendered **on the line after its intent**, not in a separate
table, because the thing the model needs at the moment it reads `I/play_music` is that
`I/play_radio` is the neighbour it is confused with.

**(d) Per-row pointers by score or vote, so the tail is the degradation order.** Within the row's
pointer block the order is the retrieval rank (or the neighbour-vote count), highest first, so that a
COMPACT disposition truncating the tail removes the least-supported pointer, deterministically, and
the receipt can say exactly which pointers were dropped.

**The ordering warning, stated before the schema is proposed rather than after.** The one time this
program changed only the **order** of an unchanged registry — Audio2Tool ORG-1, the same 152 rows
re-rendered under `## DOMAIN` headers — the official tool accuracy fell **61.40 % → 58.17 %, −3.23 pp,
CI90 [−4.15, −2.33]**, `p < 0.0001`, with **every** domain losing including `wearables` (13 tools,
fewest confusable neighbours, −3.38). The mechanism fired as designed (cross-domain twin misses
−38 %) and the errors simply moved one step closer (same-domain twin misses +24 %). Re-rendering an
unchanged store moved **no store byte** and still cost 3.23 points. Ordering is a mechanism with its
own sign, and the only control that separates shape from content is a **token-matched form twin**
(owner ruling of 2026-09-06: lock the score against a token-matched control, not against a token
count). Section 7 makes that twin a precondition, not an option.

### 3.5 Measured index sizes, SLURP

Computed directly from the released snapshots; the token columns are derived at the two measured
anchors of section 2.1 and no tokenizer was run.

| index variant | chars | tok @4.60 | tok @3.67 | status |
| --- | ---: | ---: | ---: | --- |
| **L0 intent** (18 scenario lines + header) | 1,029 | 224 | 281 | **already rendered** inside the contract |
| **L0 slot** (55 entity types, one line) | 805 | 175 | 220 | **already rendered** |
| **L0 total** = the `slurp-label-inventory` fill | **1,834** | **399** | **500** | **already paid** |
| L1 intent: id + `Activation boundary` | 5,249 | 1,141 | 1,432 | proposed |
| L1 intent: id + `Confusable exclusions` | 8,306 | 1,806 | 2,266 | alternative |
| L1 intent: both lines | 13,615 | 2,960 | 3,715 | alternative |
| L1 slot: id + `Admissible formats` | 6,128 | 1,332 | 1,672 | proposed |
| L1 slot: id + `Extraction cues` | 13,704 | 2,979 | 3,739 | alternative |
| L1 slot: id + `Intent bindings and semantic roles` | 25,653 | 5,577 | 6,999 | too large |
| L0 edges: 81 pairs, ids only | 2,610 | 567 | 712 | proposed |
| L1 edges: 81 pairs + 231 cue words | 4,366 | 949 | 1,191 | alternative |
| L2 intent cards, all 60 | 42,133 | 9,159 | 11,496 | never in the prefix |
| L2 slot cards, all 54 | 83,351 | 18,120 | 22,742 | never in the prefix |
| L2 exemplars, all 9,354 | 1,157,000 (approx.) | — | — | never in the prefix |

**The proposed composite index** = the existing 1,834-character inventory, re-rendered as L0, plus
L1 intent (`Activation boundary`), plus L1 slot (`Admissible formats`), plus L0 edges, plus about
400 characters of section headers:

| quantity | value |
| --- | ---: |
| composite index | **16,221 chars** |
| — as tokens | **3,526 (@4.60) … 4,426 (@3.67)** |
| delta over today's 1,834-character inventory | **+14,387 chars, +3,128 … +3,925 tokens** |
| new system message | 8,118 → **22,505 chars**, about 5,300 … 6,100 tokens |

### 3.6 The cache economics of L1, stated as an equation

With `native_episode.tool_schema_rendering: "constant"` armed (E17), the system message is
byte-identical across every contact of a row **and** across rows on the same pinned slot. The index
is part of it. Therefore, for a flight of `R` rows at `-np S` slots, the index's total prefill cost is

```
index prefill  =  S x index_tokens          (once per slot, for the whole flight)
per-row cost   =  S x index_tokens / R
```

At `S = 4`, `R = 1,080`, `index_tokens = 3,526`: **14,104 tokens per flight, 13.1 tokens per row**,
against a row that prefills 25,933 tokens today and 13,065 after E17. That is **0.1 %** of the
post-E17 row. Under the flight's own measured rate (2,048 prefilled tokens/s) the whole index costs
**6.9 seconds of GPU time per flight**.

The same equation is why the index must never be row-conditioned. An index rendered per row — for
example only the candidate intents' L1 lines — would cost `R x index_tokens` instead of
`S x index_tokens`, a factor of 270 on this roster, and would additionally break the prefix at the
system message on every row. **A per-row index is not an index; it is a pointer block.**

### 3.7 Where the index physically lives

The index is a **pure suffix** to the already-rendered `slurp-label-inventory` fill, inside the
`{tool_schemas}` placeholder of the frozen contract template `probes/slurp_native_role_context_v3.txt`
(872 characters). This is the form the repository already uses and documents:
`render_slurp_closed_label_inventory`'s own docstring records that its output is the unchanged task
contract "followed by the compact closed inventory", so that "an arm using this fill differs from
that sealed comparator by a pure SUFFIX and by nothing else — which is what makes the paired contrast
a measurement of the closed inventory rather than of a rewritten prompt." The index is the third
member of that suffix chain. **The template is not edited**, which keeps owner decision 40's Stage-2
template freeze intact; the *fill* is extended, exactly as the inventory itself once extended the
ontology.
---

## 4. Index-based context ASSEMBLY

### 4.1 The prompt layout rule

One rule, three positions, checkable by construction:

```
[ system ]  contract  ->  L0 index  ->  L1 index          CONSTANT   (paid once per slot)
[ user   ]  speech packet                                 row
            POINTER BLOCK   ids + rank/vote, ordered      row, small
            EXPANSION BLOCK L2 cards, budgeted, ordered    row, bounded
            agent states (upstream model text)            row
            role query                                    constant per role
```

* **Constant index first.** Anything that can be constant must be earlier than anything that cannot.
* **Row pointers second.** They are short and they change every row, so they mark the exact byte
  where the cacheable prefix ends.
* **Expansions last, before the states.** They are the part a budget decision truncates, so they must
  be at the end of the knowledge region; truncating them must not move anything before them.

This is a strictly weaker requirement than the current `speech-query-prefix-v2` order, which already
puts stable text before mutable evidence — it is the same order with the *stable* bucket finally
non-empty (finding F-3).

### 4.2 The per-node assembly table

Node names are the base lock's (`agent-base-lock-v2-draft` section 3). "Expansion budget" is the
number of L2 cards that node's context may carry; it is a config value, not a constant.

| node | reads from the index | pointers it receives | expansion budget | may cite | writes back (typed) | receipt fields |
| --- | --- | --- | --- | --- | --- | --- |
| **N1 Perception** (OBS) | L0 intents (all 60, grouped by scenario), L0 slots | none — it is the node that *produces* the first pointers | **0** | `I/<name>` from the closed inventory | a bounded candidate list of `I/<name>` with a distinction string (today: `slurp-intent-hypotheses-v1`, 1,080/1,080 parsed) | `phase_supply` receipt; the projection's selection audit; `index_ids_available` (the L0 set's hash) |
| **N2 Solver** (USE) | L0 + L1 intents, L0 + L1 slots, L0 edges | the Perception candidates (<= 3, ranked); the **neighbour vote** `I/<name> x <count>` over the k = 20 exemplars; the ids of the slot types bound to each candidate | **r** L2 exemplars (default `r = 5`) and **e** L2 slot cards (default `e = 0`) | every id in the pointer block and every id in the index | the draft, with its intent cited as `I/<name>` | `expanded_ids`, `pointer_ids`, `expansion_budget`, `pointer_budget`, the rendered block's sha256 and chars |
| **N3 Reviewer** (USE + SUPPLY) | L1 of **the ids the draft cited**, and only those; the slot-audit block (E12) | the draft's cited ids; the audit flags `TYPE-UNSEEN` / `EMPTY-DRAFT` / `MISSING-COMMON` / `REPRESENTATION` | **1** L2 card, of a cited id it flags | the cited ids | findings, criticism-only, referencing ids | `reviewer_audit` block (already `saea-reviewer-slot-audit-v1`) plus `cited_ids_verified` |
| **N4 Planner** (USE) | **L0 only** | the draft's cited ids, the findings' ids, the remaining budget | **0** | nothing — it emits one action token | one action token, byte-matched | `planner_routes[i]` unchanged; `index_granularity: "L0"` |
| **N5 Acquisition** (SUPPLY + OBS) | L0 + L1 | key = **speech + the drafted id** (E18 kind (a), `knowledge-requery`) | the kind's own item cap | the ids it brought | one typed `acquired-evidence` block naming the new ids | `acquisition_receipt` (`saea-native-acquisition-v1`): kind, policy, `provenance_ids`, `inputs_sha256`, `evidence_sha256` |
| **N6 Delivery** (USE) | L0 only (the closed inventory it normalises against) | none | 0 | n/a — zero contacts | the delivered text | `deliver_normaliser` block unchanged |

Three things this table asserts that today's system does not do.

1. **The Planner reads L0 and nothing else.** It emits a median of **2 tokens** for 25.0 % of the run's
   prompt budget and 34.8 % of its prefill. A routing decision needs the id space and the states, not
   the store. This is finding F-6 of the base lock, answered with a budget instead of a node removal.
2. **The Reviewer reads only what the draft cited.** Criticism against a contract requires the
   contract of the thing criticised, not of everything retrieved. E12's slot-audit block is already
   exactly this shape (687-787 characters, counts and shares only) and is held.
3. **The Solver's expansion is a budget, not a consequence of `k`.** Today `k` decides both how many
   items are *selected* and how much text is *rendered*. Under the index those are two knobs:
   `pointer_budget` (how many ids the row names) and `expansion_budget` (how many of them it reads in
   full).

### 4.3 The staged expansion

The stage sequence for one SLURP row, with the information that crosses each stage:

```
 speech --> N1 Perception       reads L0 (60 ids)
                               emits <= 3 candidate ids            [pointer, 0 expansions]
        --> knowledge plane     ranks the exemplar store by the sealed SPEECH vector, k = 20
                               aggregates to a vote: id x count     [pointer]
        --> N2 Solver           reads L1 of the candidates + the vote + r exemplars
                               emits the draft, citing one id       [<= r + e expansions]
        --> N3 Reviewer         reads L1 of the CITED id + the audit block
                               emits findings                       [<= 1 expansion]
        --> N4 Planner          reads L0 + the states
                               emits ACCEPT | REVISE | ACQUIRE
        --> N5 Acquisition      (only on ACQUIRE) key = speech + drafted id
                               emits one typed acquired-evidence block
        --> N2 Solver (revision) reads the acquired block
        --> N6 Delivery         normalises against L0
```

**The vote is the aggregation decision 47 asked for, and it is measured.** Over 60 sealed B1 rows the
k = 20 retrieved exemplars carry a **median of 3 distinct construction intents** (mean 3.7, min 1,
max 12); the top-1 intent holds a **median 15 of 20** votes; the top-3 cover a **median 20 of 20**.
So at the median the block's *label* content is losslessly expressible as three lines of
`I/<name> x <count>` — about 60 characters against 2,474. What the 20 raw exemplars carry beyond the
vote is their *surface form* — the way the request is actually phrased — and that is precisely what
the `r` expansions are for. The design therefore renders **both**: the vote as a pointer (always) and
`r` exemplars as an expansion (budgeted), instead of 20 exemplars as undifferentiated evidence.

**The acquisition stage is where SUPPLY's *timing* finally varies.** E18 kind (a) is built, armed end
to end on SLURP, costs **zero contacts**, and its key is the row's own sealed speech vector restricted
by state filters derived from the latest Reviewer finding and the Planner's action token
(`derive_state_filters`, bounded at 8 tokens). Under the index the state restriction becomes
*addressable*: the drafted id is a legal index id, so "fetch more about `I/play_radio`" is a
well-formed request rather than a bag of words. The drafted id is **model state**, not gold — this is
the same legality argument E18 already carries, and the owner ruling of 2026-09-06 (retrieval queries
are speech or speech+state, never text alone) is satisfied because the speech vector remains the key
and the id only restricts the ranking.

### 4.4 The degradation order (owner decision 45)

`rails.context_budget` produces a per-request decision, but the decision-45 analysis found that the
runtime seam its own docstring reserves — "receipt-bound exact counts for an already rendered payload
immediately before each model contact" — **has never been wired**: preflight raises
`FlightRuntimeError` on anything but `ALLOW`, and at dispatch there is no budget check at all, so a
server-side `exceed_context_size_error` propagates and kills the flight. That analysis designs the
repair as `native_episode.context_fit_policy` (`"raise"` / `"compact-or-abstain"`) on the
finite-completion contract, with a declared drop order whose first item is "`value:` exemplars beyond
the first k/2" and whose items 3 and 4 are the scenario-hints and Reviewer-audit blocks.

Under the index that drop order simplifies, because the hints and the audit are no longer per-row
blocks to drop — they are in the prefix, which is never droppable. What remains is a clean ladder:

```
1. expansions, from the tail            (lowest rank / lowest vote first)
2. pointers, from the tail              (below the top-1)
3. the L1 index                         (fall back to L0)
4. NEVER the L0 index, the contract, the speech packet or the states
```

Rule 4 is the safety property: dropping L0 would let the model emit an id the closed inventory does
not contain, which the delivery normaliser would then have to repair and the official scorer would
count as a miss. Every degradation step is **recorded as a row disposition**, never silently applied
— the same honesty requirement decision 45 states for the serving side ("a degraded request is
recorded as such, never silently truncated").

Because the expansion block is last in the knowledge region and ordered by score, truncating it moves
no byte before it, so a COMPACT row's prefix is still a prefix of the uncompacted one and the KV cache
is undisturbed. That property is a consequence of the layout rule in 4.1 and is worth a test.

### 4.5 The information boundary

Unchanged from the base lock section 3.9 and restated because an index is a new surface:

* **The index is construction-only.** Every entry, every L1 line and every ordering statistic comes
  from the 9,354-utterance construction pool (governed TRAIN minus every utterance with a recording in
  TRAIN Fold A, Fold B or DEV-1000; split identity `67e53fb5…`; 2,160 excluded) or from the closed
  legal inventory the contract already renders. `KN-5 decontaminate` is re-checked at build time and
  the exclusion is **not** an optimisable knob.
* **No gold of an evaluated row enters the index**, at any granularity. A3's own confusion pairs were
  computed on evaluated rows' gold and are therefore a diagnostic ceiling; E14 already re-derives its
  neighbours from the construction pool alone and the index uses E14's table, not A3's.
* **The drafted id is model state.** A pointer derived from the Solver's own draft is the model's
  output, not a label. A pointer derived from the *gold* intent would be an oracle and is refused.
* **No transcript, no ASR state, no future turn** as a retrieval key: the key stays the sealed speech
  vector, exactly as `rails/phase_supply.py` enforces (it names `embedding-server` as a kind and
  refuses it, so an in-flight encoder contact is a named refusal).
* **The index carries no utterance text of any evaluated row.** The exemplar kind, which does carry
  construction utterance text, is not in the constant index at all (section 3.1).

---

## 5. The per-row budget, design versus today

### 5.1 Client prompt tokens

Per row, medians, derived from section 2.2 at 4.60 chars/token:

| step | perception | solver | reviewer x2 | planner | **row** |
| --- | ---: | ---: | ---: | ---: | ---: |
| today (B1, measured) | 3,600 | 9,396 | 20,164 | 11,251 | **44,412** |
| + index prefix (+3,526 on every contact) | 7,126 | 12,922 | 27,216 | 14,777 | **62,042** |
| − slot-contract expansion (−5,230 on 4 contacts) | 7,126 | 7,692 | 16,756 | 9,547 | **41,122** |
| − exemplars 20 → r = 5 (−403 on 4 contacts) | 7,126 | 7,289 | 15,950 | 9,144 | **39,510** |

Prompt tokens fall about **11 %**. That is not where the money is; the prefill is.

### 5.2 Prefilled tokens — the number that buys GPU hours

Until 2026-09-19 the flight was prefill-bound at 488-536 seconds per million prefilled tokens, so GPU
hours tracked prefilled tokens alone. That changed while this document was being written. The
decision-45 analysis measured the EFF-1 post-L1 window on the resident session's own `server.log` and
found the row now presents **9,906 prefilled tokens** (1,972 per request, cached share 40-44 % →
**75.3 %**, packet re-decode 60 % → **20.4 %**), at **50.20 contacts per minute** — but with the
aggregate prefill rate off its ceiling (1,650 against 2,100 tok/s) and aggregate decode up to
36.6 tok/s, **62 %** of the measured np4 decode ceiling of 59.4. The flight is now **co-bound**.
Post-L1 is therefore *better* than E17 predicted (9,906 against a predicted 13,065) and further
prefill cuts convert into time at less than one for one.

| step | prefilled tok/row | rows/min | GPU-h / 1,080 | 13,078-row read | source |
| --- | ---: | ---: | ---: | ---: | --- |
| 0 — B1 as flown | **25,933** | 4.66 | 3.860 | 46.5 h | measured |
| 1 — + E17 constant tool rendering | **9,906** | **9.97** | **1.79** | **21.7 h** | **measured** (decision-45 analysis, sections 2.1-2.2) |
| 2 — + index, `expansion_budget = 0` | ~**4,676** | 10.1 … 16.2 | **1.11 … 1.78** | **13.4 … 21.5 h** | derived, bounded |
| 2' — + index, `expansion_budget = 4` | ~6,010 | 10.1 … 16.2 | 1.11 … 1.78 | 13.4 … 21.5 h | derived, bounded |
| 3 — + step 2 makes np6 admissible | ~4,676 | up to 24.0 | ~0.75 … 1.78 | ~9 … 21.5 h | derived from the np6 row of the decision-45 table |

The derivation of step 2, stated so it can be falsified. The Solver's own contribution is the **first
render of the evidence block plus the Perception state plus the role query**: 24,057 + 2,474 + 626 +
1,304 = 28,461 characters, which at this arm's own 4.63 chars/token is 6,147 tokens. Replacing the
24,057-character slot-contract expansion with a pointer block (about 420 characters: three candidates
x six slot-type ids plus headers) and the exemplar block with a vote plus `r = 5` expansions (about
680 characters) removes about 24,900 characters, about **5,230 tokens**, from that first render, and
the row falls from 9,906 to about **4,676**. At `expansion_budget = 4` the four L2 slot cards add
about 6,172 characters, about 1,333 tokens, and the row is about 6,010.

**Why the time column is a range, not a number.** With prefilled/row at 4,676 the prefill-only
ceiling rises to 2,100/4,676 x 60 = **26.9 rows/min**, while the decode-only ceiling stays at
59.4/219 x 60 = **16.24 rows/min**: the row becomes **decode-bound**. The decision-45 analysis brackets
a co-bound flight between fully serialised — `1/(1/26.9 + 1/16.24)` = **10.1 rows/min**, i.e. *no gain
at all* — and perfectly overlapped, **16.2 rows/min**. Today's measured overlap sits between its own
two brackets (9.97 against 7.13 and 12.72), so the honest statement is the range. Anyone quoting a
single number here is quoting the overlap model, not a measurement.

**Step 3 is the interesting one, and it is the index's second-order effect.** Once the row is
decode-bound, slot count is the correct lever, and the decision-45 analysis says np6 would buy +7.5 %
and np8 +11.8 % — except that **np6 is refused today by 188 tokens** (14,336 usable against a post-L1
maximum of 14,524). The index's pointer block takes that maximum to about **12,820**, so np6 becomes
admissible with 1,516 tokens to spare, and its decode ceiling of 87.7 tok/s raises the decode-only
term to **24.0 rows/min**. The prompt shrink is what unlocks the geometry, and the geometry is what
converts the prompt shrink into hours.

The index's own cost does not appear anywhere in the table because it is 13.1 tokens per row
(section 3.6).

Three honest caveats. (i) Every step-2 and step-3 figure is **derived**, exactly as lever L3 is
derived in the throughput report; only a live cell measures them, and EFF-1 itself is the proof that
a derived prefill number can be wrong by 24 % in the favourable direction. (ii) The Reviewer and
Planner deltas are assumed unchanged, which holds only while the evidence block precedes the states in
the render order — the layout rule of 4.1 is what makes the assumption true, and the model-free render
proof of section 7.0 must confirm it. (iii) The test split's own prompt tail **has never been
measured**; the decision-45 analysis makes bounding it a prerequisite of any geometry choice for the
read, and that applies to this design too.

### 5.3 Contacts per row

Unchanged at **5.00** for the index cell: the index changes what a contact carries, never how many
there are, and the one-factor rule requires that.

The staged-acquisition cell is different. E18 kind (a) costs **zero contacts of its own**, but an
`ACQUIRE` route spends a revision, so an acquiring row costs `solver + reviewer + planner` = 3 more
contacts and the loader's checked ceiling becomes **7** (`1 + 2 x 3 + 0`). On the sealed anchor the
Planner emitted a non-`ACCEPT` token on **6 of 1,085** routes, so at today's routing rate the expected
cost is about 5.02 contacts per row; a cell that *intends* acquisition to fire will move that rate and
must budget for it explicitly rather than assume it.

---

## 6. Config surface

### 6.1 What already exists and already carries part of this

Nothing in this design needs a new *supply* mechanism. Seven existing key families already express
pieces of it:

| key | what it already controls | its role under the index |
| --- | --- | --- |
| `knowledge_stores.<id>.phase_supply.<phase>.{k, tau, rank_policy, rank_weights, fuse_policy, fuse_coverage, dimensions, query_source, facet_source, expose_facets}` | selection: how many entries the row's speech key selects, and how they are ranked and fused | becomes the **pointer** budget's source: `k` selects pointers, not text |
| `knowledge_stores.<id>.candidate_supply.<phase>.{max_candidates, max_values_per_candidate, max_total_values, projection_policy, rank_policy, fuse_policy, candidate_state_phase, compact_source_phase}` | the candidate slot-card expansion: **3 candidates x 16 values, capped at 28 total** | already an **expansion budget** in everything but name; the index gives it a granularity |
| `native_episode.solver_hints` (E14, key 7) | the confusion-edge block at `solver:candidate-hypothesis`, bounded `max_neighbours` x `max_cues` | becomes the **edge** entry kind's per-row rendering |
| `native_episode.reviewer_audit` (E12, key 5) | the slot-audit block at `reviewer:current-draft` | becomes the Reviewer's L1-of-cited-ids view |
| `native_episode.deliver_normaliser` (E11, key 4) | `saea-deliver-normalise-v3` against the closed inventory | unchanged; it is the L0 index's write-side twin |
| `native_episode.acquisition` (E18, key 9) | the fifth role, its kinds, its budget | the staged expansion's timing control |
| `native_episode.tool_schema_rendering` (E17, key 8) | constant vs per-role `tools` | **the precondition**: without it the prefix is not constant |
| `task_instruction_template` + `task_instruction_fill` | the contract shell and `slurp-label-inventory` | where the index physically renders (section 3.7) |

### 6.2 The one new switch

```jsonc
"native_episode": {
  "knowledge_index": {
    "view": "slurp-knowledge-index-v1",       // a released, hash-pinned construction view
    "granularity": {"intent": "L1", "slot": "L1", "edge": "L0"},
    "ordering": "taxonomy-frequency-v1",      // scenario -> intent, then construction frequency
    "pointer_budget": {"intent": 3, "slot": 8, "exemplar_vote": 3},
    "expansion_budget": {"exemplar": 5, "slot_card": 0, "intent_card": 0}
  }
}
```

`native_episode.knowledge_index` is proposed for the closed allowlist
`rails.config_tables.EPISODE_LEVEL_SWITCH_KEYS` (today nine members: `roles.solver`, `review_loop`,
`context_policy`, `deliver_normaliser`, `reviewer_audit`, `finite_completion_policy`, `solver_hints`,
`tool_schema_rendering`, `acquisition`). It would be the **tenth or eleventh**, depending on whether
`native_episode.context_fit_policy` — proposed by the decision-45 analysis for the same allowlist —
lands first. Its **null arm is the key's absence**, and an absent key must compose byte-identical
requests and an identical receipt: the same falsifier E11/E12/E14/E17/E18 all carry.

Note also that the allowlist's own docstring is stale in three places (base-lock finding F-18: it
says "All three are dotted paths" over seven, then nine, members). Admitting a tenth is a code change
with a test; it should repair the docstring on the way past.

### 6.3 Why it is ONE key and not two

The obvious alternative is two keys: one for the prefix rendering and one for the pointer/expansion
budgets. It is rejected on two measured grounds, not a stylistic one.

**Serving.** An index-only arm adds about 3,526 tokens to every contact, taking the post-L1 maximum
prompt from 14,524 to about 18,050. That still fits np4 (21,504 usable) but **forecloses np5 (17,024)
and np6 (14,336)** — and np6 is the geometry the decision-45 analysis models at +7.5 %, currently
refused by 188 tokens. The pointer block is what pays for the index in slot width: index + pointers
takes the maximum to about 12,820 and makes np6 admissible for the first time. Armed apart, the first
half spends a serving option the second half would have bought.

**Semantics.** A pointer-only arm removes the card text while the model has no index to resolve the
pointers against — a strictly worse system, and a cell measuring nothing anyone wants.

The prefix and the pointers are **two halves of one mechanism**: the index is the referent and the
pointer is the reference. One key that arms both keeps the cell one-factor and keeps the halves from
drifting apart across cells. The *budgets inside the key* are then the sweep surface of a later cell,
exactly as `k` is for `phase_supply`.

### 6.4 The refusals the loader must carry

Fail-closed, before any contact, in the shape `load_native_episode_config` already uses:

1. an unreleased or hash-mismatched `view`;
2. a `granularity` naming an entry kind the view does not carry;
3. `expansion_budget.exemplar > 0` with no exemplar store armed on any phase;
4. `pointer_budget.intent > candidate_supply.max_candidates` — the pointer block may never name more
   candidates than the projection produced;
5. `expansion_budget.slot_card > candidate_supply.max_total_values`;
6. an `ordering` id not registered in `core.base`;
7. the key armed with `tool_schema_rendering` absent or `"per-role"` — the economic premise of the
   design is the constant prefix, and an arm that does not have it is measuring something else;
8. the key armed on a carrier whose descriptor declares no `knowledge_layer` (today: both Earnings
   descriptors, base-lock finding F-1).

Refusal 7 is the one that will be argued about. It is deliberate: it makes the ordering of the cells
(EFF-1 before the index cell) a machine fact rather than a plan.
---

## 7. The cells that would test it

None of the following is registered. Each is described so the owner can approve, reorder or refuse it.

### 7.0 Precondition: the model-free render proof (zero contacts)

Before any cell, the same proof form E17's Probe A and cell B7c both use: re-render the 100 contacts
of **20 sealed B1 rows** through the production transport with the key armed, and emit a receipt
carrying, per contact, the rendered system-message SHA-256 (must be **one** value over all five
contacts of a row and over all 20 rows), the rendered prompt SHA-256, the pointer and expansion ids,
and the predicted prefilled-token count under llama.cpp's common-prefix rule given the pinned per-row
slot. Predicted outcome, from section 5.2: the Solver falls from about 6,260 to about 654 predicted
prefilled tokens, the row from 13,065 to about 7,855, and **no byte before the expansion block moves
when the expansion budget is reduced**. Cost: zero GPU, zero contacts, minutes of CPU. A render proof
that does not reproduce these three properties stops the cell.

### 7.1 Cell "index prefix + pointer block" (the first instance)

| field | value |
| --- | --- |
| **factor** | `native_episode.knowledge_index`, absent → armed. Nothing else moves. |
| **base** | the B1 exemplar arm, plus the admitted modules in the default plan (M4b slot store v2, M3 deliver normaliser), plus E17 `tool_schema_rendering: "constant"` once EFF-1 seals |
| **comparator** | the **sealed B1 arm bytes**, `SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TRAIN-FOLD-A-RECOVERY-V2`, n = 1,080 TRAIN Fold A, paired per row |
| **margins** | **B1's own null**, from the registered but unflown request-identical replicate `SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-REPLICATE-V1` (owner decision 38, decision 37's B1r). Until B1r flies there is no correct margin for this comparator: the anchor's own null (intent half-width 0.92, SLU-F1 micro 1.18, 2026-09-09) belongs to a different configuration, and the imported 0.60 bar was already shown too narrow. **The cell does not read before B1r supplies its margins.** |
| **scoring** | SLURP official `evaluate.py` from the pinned local clone, once per complete manifest through `core.scoring_batch`, plus the `slurp-slu-f1-normalized-v1-train` symmetric sibling and `cost` |
| **effectiveness read** | **NEUTRAL is a pass.** The claim of this cell is efficiency: if official pooled SLU micro F1 and intent accuracy are both non-inferior under B1's own margins, the saving is free and the module enters the default plan by the same design rule cell B7c carries (a NEUTRAL cell that lowers cost is admitted). ADMITTED if it also gains. |
| **efficiency read** | **measured, not modelled**: prefilled tokens per row, wall seconds per row, aggregate prefill tok/s, per-position cache shares, speech-packet re-decode share, GPU-hours per 1,080 — read from the serving session's `server.log` and the flight receipt, joined per slot exactly as the throughput report joins them |
| **structural read** | per row: `distinct system-message sha256 == 1`; the pointer ids; the expanded ids; the count of Solver citations that resolve in the index; the count that do not |
| **preceded by** | the 7.0 render proof; a four-row smoke; a prompt-fit receipt (the widest realised request against the live slot budget) |
| **twin** | required — section 7.2 |
| **power** | n = 1,080, above the n >= 400 paired-effectiveness floor; TRAIN Fold A, the roster every comparator in this family used |

**Ordering against the other queued cells.** EFF-1 must seal first (refusal 7 of section 6.4 makes
that mechanical). B1r must fly, because it is this cell's only legitimate margin source and it is
already required by decision 37. B7c should be considered before or with this cell, because the
Planner's 10,512-character contract replay grows with the index.

### 7.2 The twin, and why it is not optional

`native_episode.knowledge_index` changes **two** things at once in the eyes of a critic: the prompt
now *contains* 60 intent contracts and 54 slot contracts that were previously only present when
retrieved, and the prompt now *omits* the retrieved cards' full text. A NEUTRAL or positive read has
at least three explanations — the index's content helps, the index's mere presence and shape help, or
the omission of 24,000 characters of card text helps by removing distraction.

The control that separates them is the one this program already built for module M1: a **derangement
twin**. The index's L1 lines are permuted across ids by a Sattolo derangement (seed recorded, zero
fixed points, `gold_read: false`), so every id carries another entry's contract line. Token count,
token positions, ordering, pointer block, expansion budget and every other byte are matched; only the
*correspondence* between id and contract is destroyed.

The precedent is not hypothetical. Audio2Tool ORG-1 re-rendered 152 unchanged registry rows under
domain headers, moved **no store byte**, and cost **−3.23 pp [−4.15, −2.33]** with every domain
losing including one with 13 tools and no confusable neighbours — the verdict's own words: *"Something
about the prompt's FORM, not its content, is doing part of this."* A cell that changes prompt form on
this scale without a form-matched control cannot distinguish its mechanism from its shape.

### 7.3 Cell "staged acquisition" (B9a's first instance)

| field | value |
| --- | --- |
| **factor** | `native_episode.acquisition` armed with `saea-acquire-knowledge-requery-v1`, kind (a), `max_acquisitions_per_row: 1`, `contact_budget: 0`; OFF arm is the key's absence |
| **key** | the row's own sealed **speech** vector, restricted by the **drafted index id** plus the state filters E18 already derives — never text alone, never gold |
| **base** | the index cell's arm if it is not HARMFUL; otherwise the best not-HARMFUL base |
| **what it tests** | SUPPLY's **timing**, the one thing pre-contact supply cannot vary (base lock OQ-3): does fetching the drafted intent's exemplars *after* a draft exists beat fetching 20 exemplars *before* one does? |
| **cost** | 0 contacts for the acquisition itself; an `ACQUIRE` route spends a revision, so the contact ceiling is 7 and the expected rate must be budgeted explicitly, not assumed from the anchor's 6-of-1,085 non-`ACCEPT` rate |
| **read** | official SLU micro F1 and intent, under the base's own margins; plus the acquisition receipt's `provenance_ids` and the share of rows that acquired |

This is where decision 47's "load all intents into the prefix and process the retrieved top-20 in
stages" becomes a measurement rather than a design: the prefix half is cell 7.1 and the staging half
is this cell.

### 7.4 What is NOT claimed

* **No claim that ordering helps.** The only ordering experiment this program has run read HARMFUL.
  The index cell's ordering is a declared rule with a twin, not a hypothesis with a prediction.
* **No claim that an L1 line suffices.** Whether one 70.7-character activation line carries what a
  1,543-character slot card carries is exactly what the expansion budget sweep would answer, and it is
  not answered here.
* **No efficiency claim without a live measurement.** Every prefill number in section 5.2 is modelled
  from the measured post-E17 profile, in the same way lever L3 is modelled, and is labelled as such.
* **No claim about the test split.** Every number is a development number on TRAIN Fold A (decision 28).
* **No cross-carrier claim.** Section 8 states what exists on the other two carriers; it admits nothing.
* **No claim that this reaches the bar.** The SLURP dev bar is official SLU-F1 >= 64 and intent >= 78,
  replicated (decision 23). B1 reads 62.67 / 81.76 with the normaliser and B5e 63.78 / 81.85. An
  efficiency-NEUTRAL cell moves neither.

---

## 8. Cross-carrier instances

The schema of section 3 is carrier-neutral; its instances are not. What follows is what exists today
and what a carrier would have to build.

### 8.1 Contextual ASR (Earnings-21/22 + ConEC)

| schema element | instance | status |
| --- | --- | --- |
| `entity` entries | `participant-roster-v1` (names, scoped to the 44 governed discovery calls, pinning the D1 evidence supplement `313da4c4…`), `document-lexicon-v1` (`lexical_limit 128`), the ConEC contexts / names / bias lists / class lists and their placebo and distractor-only twins, the `e22-metadata-brief` and its deranged twin | stores **registered, never flown**; `evidence_source: "none"` in both named fragments |
| `unit` entries | the **1,593 registered 90-second windows over 44 governed parent calls**; unit identity is the registered slice, never a synthetic id | flown; OBS-E1 speaker-turn units read HARM (WER 8.200 → 7.151, PERSON 22.49 → 24.58) |
| L0 | **does not exist and cannot be copied from SLURP.** The 2026-09-14 transfer readiness records the owner position that no intent taxonomy is introduced for ASR; there is no closed inventory the contract already renders | the entity index would be this carrier's **first** closed list |
| L1 | a one-line entity card: the name, its spoken-form convention, and the call it is attested in | not built |
| ordering | by call, then by attested frequency in that call's governed sources | not built |
| pointers | the window's own retrieved entity ids; the deterministic judges' flags (`e21-substitution-alignment-flag-v1`, `earnings-numeric-format-v1`, `e21-brief-name-near-miss-v1`) are already id-shaped pointers into the roster | the judge path is the one ADMITTED, REPLICATED mechanism on this carrier (KC-E1f, PERSON +3.634 [+2.590, +4.690]) |

**The cache equation changes shape here, and in the carrier's favour.** On SLURP the index is constant
over the whole run. On contextual ASR the entity index is constant over a **call** — 44 of them, about
36 windows each — so it is prefilled once per call per slot rather than once per run. At 44 calls,
4 slots and an index of a few thousand tokens that is still a rounding error against a carrier whose
admitted mechanism already spends 1.11 GPU-h at np4.

**Two blockers.** (i) Both Earnings descriptors declare `task=None`, so the carrier registry cannot
state a `knowledge_layer` and refusal 8 of section 6.4 would refuse the key today (base-lock finding
F-1). (ii) The entire scored contextual-ASR history was produced **outside** the node graph, by
`obs-agent-loop` / `obs-repair-loop` programs with no Perception, Reviewer, Planner or Delivery node
(finding F-10), so there is no assembly table to attach an index to until a node-graph cell flies on
that carrier.

### 8.2 Audio2Tool

Audio2Tool is the carrier where **the index already exists and the pointer block does not** — the
exact mirror of SLURP.

| schema element | instance | status |
| --- | --- | --- |
| `tool` entries | the **152-row registry**, rendered as prompt text by `render_tool_schemas` through the `audio2tool-registry-compact` fill, inside `probes/r1_audio2tool_official.txt` | flown; this **is** an L0 + L1 index in the constant prefix, and it is the protocol the published paper specifies |
| `domain` entries | the same 152 rows re-rendered under `## DOMAIN` headers (`audio2tool-registry-grouped`) | **HARMFUL, −3.23 pp [−4.15, −2.33]**, `p < 0.0001`, 194 saves / 323 harms / 3,483 ties |
| `parameter` entries | `parameter-meaning-v1`, one action's parameter semantics, supplied as `candidate_supply` to the Solver with `max_actions: 8` | flown, not admitted |
| pointers | `tool-activation-v1` at `phase_supply.perception`, k = 8, speech-keyed, `saea-fuse-supplyfilter-v1` — but it renders **cards**, not pointers | flown in the 4,000-row read, not admitted |
| scope-restricted expansion | `tool-activation-scope-v1`, reachable **only** through `saea-tool-knowledge-target-lookup-v1`, `candidate_limit 4`, `knowledge_value_limit 4` | held; this is an expansion budget under another name |

**What A2T uniquely offers.** Because the index half is already flown and scored, A2T is the only
carrier where the **pointer half can be tested alone**: keep the registry rendering byte-identical and
replace the k = 8 activation-card supply with an activation *pointer* block naming the same eight
`T/<name>` ids with their scores. One factor, no prefix change, and the comparator is the sealed
official-protocol arm. That is a cheaper and cleaner first test of "pointers instead of text" than
SLURP can offer, and it inherits ORG-1's warning about form.

**Two blockers.** (i) Audio2Tool has **zero** harness-admission entries and **no default plan**
(finding F-2), so there is no "comparator plus decided modules" to be one factor against. (ii)
`rails.reward_links._NATIVE_PROJECTIONS` registers no Audio2Tool projection at all (finding F-16), so
nothing downstream can consume an A2T outcome.

### 8.3 What the three instances have in common, and what they do not

Common: a closed or governed entry set; construction-only authorship under KN-5; a speech-keyed
ranking that produces the pointers; a rendering step that is currently total and could be budgeted.

Not common: SLURP has an L0 in the contract and no L1; A2T has L0 + L1 in the contract and no pointer
discipline; contextual ASR has neither and cannot have an L0 without the owner reopening the "no
taxonomy for ASR" position. The schema therefore generalises; the *first* instance of it does not
transfer as a verdict — base-lock OQ-7's recommendation applies (carry the form, never the verdict,
and require the receiving carrier's own one-factor cell).

---

## 9. Owner questions, and findings

### 9.1 Questions

**Q1 (blocking).** Accept `native_episode.knowledge_index` as **one** key arming both the constant
prefix and the pointer/expansion budgets — on the measured ground that an index-only arm is refused by
the live-slot fit gate (18,987 vs 16,384 tokens) and a pointer-only arm has no referent — or split it
into two keys and accept that neither half can be flown alone?

**Q2.** Is extending the `slurp-label-inventory` fill by a **pure suffix** a contract change under
decision 40's Stage-2 template freeze? The template file is not touched, and the repository's own
docstring records this exact form as what makes a paired contrast legitimate. If the owner reads it as
a contract change, the index needs its own instruction fill id and a `contract`-class switch instead.

**Q3.** Which line is the intent L1? `Activation boundary` alone (5,249 chars, 1,141-1,432 tokens),
`Confusable exclusions` alone (8,306), or both (13,615)? Recommendation: `Activation boundary` for the
first cell, with `Confusable exclusions` folded into the **edge** entries instead, so that
"what distinguishes A from B" is attached to the pair rather than to A.

**Q4.** Which line is the slot L1? `Admissible formats` (6,128 chars) or `Extraction cues` (13,704)?
Recommendation: `Admissible formats`, because it is what the delivery normaliser and the E12
`REPRESENTATION` flag both key on, so the index, the audit and the normaliser would finally quote one
sentence.

**Q5.** The ordering control. Is the **derangement twin** of section 7.2 required on the **first**
cell, or only if the first cell reads HARMFUL? A2T ORG-1 argues for the first; a twin doubles the
flight cost (about 1.15 GPU-h at the projected rate, so roughly 2.3 GPU-h for the pair).

**Q6.** `intent-boundaries-factored-v1` already exists (61 values, per-card content 702.2 → 297.2
chars, −57.0 %) and the base lock records it as "superseded / unused". Should it become the L2 store
behind the index — a `stores`-class re-pin cell of its own, in B4b's form — or should the factoring be
done inside the index renderer and the store left alone?

**Q7.** Should the Solver be **required** to cite an index id (a `response_format_id` change, a second
factor) or merely permitted? A required citation makes the Reviewer's "L1 of the cited ids" view and
the acquisition key well-defined; it also changes the answer surface, which is where the official
scorer reads.

**Q8.** Default `expansion_budget.slot_card`: **0** (pure L1, row 7,855 prefilled tokens) or **4**
(row 9,195)? The difference is about 2.4 hours on the 13,078-row test read.

**Q9.** Cell order. Proposed: EFF-1 seals → B1r (margins) → index cell + twin → B7c → staged
acquisition. The already-queued order in `wiki/Research-Objective.md` is B4a → EFF-1 → B1 replicate →
B8b → B8c → B9a → B5b → B6 → lock. Where does the index cell enter it, and does it displace B8b/B8c —
whose blocks (the slot audit and the scenario hints) are **the same objects the index would render
once, in the prefix, instead of per row**?

**Q10.** Cross-carrier: adopt the schema for Audio2Tool now — where the pointer half can be tested
alone against a sealed official-protocol comparator and the prefix does not move — or hold every
carrier until the SLURP cell reads?

**Q11.** The exposure ledger. The index is construction-only and closed-list, and every byte of it is
already legal in the prompt today. Confirm that it nevertheless requires its own exposure
pre-registration row and one-shot attempt semantics, i.e. that "already legal content, newly
rendered" is a new exposure.

**Q12.** Does the Planner's **L0-only** budget (section 4.2) require its own cell, or may it ride on
the index cell? It is arguably a second factor: today the Planner receives the whole episode
unfiltered (25.0 % of the run's prompt budget, 34.8 % of its prefill, for a median 2-token verdict),
and cutting it to L0 is a change to what a node reads, not only to how the store is rendered.

**Q13.** The decision-45 analysis shows the post-index row would be **decode-bound**, and that the
index's own prompt shrink is what makes **np6** admissible (+7.5 %, refused today by 188 tokens). Is
the geometry flip part of the index cell's claim, a separate serving probe (that analysis's Probe G2,
explicitly gated on `context_fit_policy` landing), or held until the test split's prompt tail has
been bounded?

### 9.2 Companion analyses

Two sibling analyses were running in parallel with this one and were checked before this draft was
sealed.

* **Owner decision 45 — serving geometry and degradation.** Delivered:
  `docs/results/2026-09-19-slurp-serving-geometry-and-degradation-v1.md` on branch `fable/geometry`
  (commit `1eb753ff`), companion receipt `docs/receipts/slurp-serving-geometry-analysis-v1.json`. Its
  numbers are cited throughout sections 2.6, 4.4, 5.2, 6.2, 6.3 and findings F-11, F-15, F-16 — in
  particular the measured post-L1 row (**9,906 prefilled tokens, 50.20 contacts/min, 1.79 GPU-h per
  1,080 rows, 21.7 h test read**), the co-bound regime (prefill 1,650 of 2,100 tok/s, decode 36.6 of
  59.4), the constraint table (np4 21,504 usable / np5 17,024 / np6 14,336 / np8 10,752 against a
  post-L1 maximum prompt of **14,524**, np6 refused by **188 tokens**), the measured VRAM calibration
  (53.30 KiB/token at q8_0, 17,857 MiB intercept, 23,119 MiB usable envelope), the measured enforced
  power limit (**100.00 W against a 175.00 W maximum**), and the finding that WSL 2 forbids GPU
  memory oversubscription so degradation must be harness-side.
* **Owner decisions 46-47 — M1 exemplar compression, the neighbour vote and staged acquisition.**
  **Not yet available.** Branch `fable/m1compress` was at `1b607e7a` (the decision record only) when
  this draft was sealed, and
  `docs/results/2026-09-19-slurp-m1-exemplar-compression-analysis-v1.md` did not exist on it. The
  exemplar figures used here — the block's 2,474 characters (finding F-1) and the neighbour vote's
  concentration (finding F-7, median 3 distinct intents, top-1 15 of 20 over 60 sealed rows) — were
  therefore measured independently for this document from the same sealed arm. **They must be
  reconciled with that analysis when it lands**, and where the two disagree, its own measurement is
  the more careful one: it reads the full roster, this one reads a 20- and 60-row window.

### 9.3 Findings

All reproduce at `4aa47a42` against the sealed B1 arm and the released snapshots; none is repaired here.

| id | finding | evidence |
| --- | --- | --- |
| **F-1** | The k = 20 exemplar block is **2,474 characters — 7.6 % of the Solver's evidence block and 5.7 % of its prompt**. The candidate slot-contract cards are **24,057 characters, 73.8 %**. Decision 46's premise that the exemplar supply is the largest prompt-token contributor does not survive measurement; lever L3's 48 % is the whole block | section 2.3, 20 sealed B1 rows |
| **F-2** | The role query is **byte-identical across rows** per role (1,135 / 1,304 / 609 / 367 chars) and is rendered **last**, behind every row-specific part: 3,415 constant characters per row in the one position the prefix cache cannot reach | section 2.4 |
| **F-3** | All **182,233 of 182,233** supplied evidence items are `knowledge_role: "value"`, so `stable_text_parts` is empty and the transport's cache-explicit key/value split holds nothing. The machinery for a constant knowledge prefix exists and is unused | trace payloads; throughput report section 5.1 |
| **F-4** | The supplied-evidence block is byte-identical across the Solver, both Reviewer and the Planner contacts of one row, so its entire cost is the **Solver's first render** | section 2.4 |
| **F-5** | The `Uncertainty behavior` section of `intent-boundaries-v1` is **one identical 199-character string on all 60 cards** (11,940 chars, 28.3 % of the store); `Limitations` has 15 distinct values over 60 cards; `slot-contracts-v2`'s `Missing behavior` has 8 over 54. `intent-boundaries-factored-v1` already collapses this (−57.0 % per card) and is unused | section 3.3 |
| **F-6** | The 60 legal intent ids **are** the taxonomy (`<scenario>_<action>`, 18 scenarios) and the contract already renders them grouped: the L0 index exists and costs 1,834 characters that are already paid. What is missing is L1 above it and the pointer discipline below it | section 3.4, 3.5 |
| **F-7** | Over 60 sealed B1 rows the k = 20 retrieved exemplars carry a **median of 3 distinct construction intents** (mean 3.7, min 1, max 12); the top-1 intent holds a **median 15 of 20** votes and the top-3 cover **20 of 20**. The block's label content is a three-line aggregate at the median | section 4.3 |
| **F-8** | The constant prefix is prefilled **once per slot, not once per row**: Perception, the first contact of a row, caches 61.8 % = 2,224 tokens = exactly the system message, carried across rows on the pinned slot. A 3,526-token index therefore costs **13.1 tokens per row** at `-np 4` over 1,080 rows | section 2.5 |
| **F-9** | The `tools` array is **221 characters** and its toggle costs **63.5 % of the row's prefill**. The smallest part of the prompt carries the largest cost, and E17 removes it | section 2.5; E17 design |
| **F-10** | The Planner carries a **10,512-character replay of the contract its own system message already holds verbatim** — 19.5 % of its prompt — to emit a median of 2 tokens. Cell B7c is registered for it and held | section 2.6 |
| **F-11** | An **index-only** arm fits np4 (about 18,050 tokens against 21,504 usable) but **forecloses np5 and np6**. np6 is refused today by **188 tokens** (14,336 usable against a post-L1 maximum of 14,524) and is modelled at +7.5 %. Index **plus** pointers takes the maximum to about **12,820**, making np6 admissible with 1,516 to spare. The prompt shrink is what unlocks the geometry | section 2.6, 5.2, 6.3; decision-45 analysis section 2.4 |
| **F-15** | The post-L1 row is **measured at 9,906 prefilled tokens**, 24 % better than E17's derived 13,065, and the flight is now **co-bound** (prefill 1,650 of 2,100 tok/s, decode 36.6 of 59.4). Further prefill cuts therefore convert into time at less than one for one, and the honest form of any post-index saving is a **range** bracketed by the serialised and perfectly-overlapped limits | decision-45 analysis sections 2.1-2.2; section 5.2 |
| **F-16** | `rails.context_budget`'s own runtime seam — a budget check on the rendered payload immediately before each contact — **has never been wired**: preflight raises on anything but `ALLOW` and dispatch has no check at all, so an over-long request kills the flight. The degradation order of section 4.4 has nothing to execute it until `context_fit_policy` lands | decision-45 analysis sections 3.2-3.3 |
| **F-12** | No carrier has an index today. The closest existing objects are E12's Reviewer slot-audit block (687-787 chars) and E14's Solver scenario hints (578 / 788 / 1,608 chars) — both **per-row** additions at a boundary, both built, both unregistered. Rendering the same material once in the prefix instead of per row is the design's direct competitor to cells B8b and B8c | NCP design sections 16.1, 16.2 |
| **F-13** | Evidence ids carry a 34-character store-and-namespace prefix the model cannot act on (`intent-boundaries::intent-boundary:`), repeated on 8 items per Perception contact = 272 characters per contact, about 1,360 per row | trace payloads |
| **F-14** | Re-rendering an unchanged 152-row registry under domain headers cost Audio2Tool **−3.23 pp [−4.15, −2.33]** with every domain losing, including one with 13 tools and no confusable neighbours. Ordering is a mechanism with its own sign and needs a form-matched control | A2T ORG-1 verdict, 2026-09-05 |

---

## 10. What this draft does not authorise

No owner decision is recorded, no cell is registered, no preregistration is written, no exposure row
is opened, no `contracts.ExecutionPlan` is composed, no readiness package is created, no config
fragment is armed, no code is written, no knowledge store or view is built or re-pinned, no ledger
row moves, and no model, tool, scorer, tokenizer, encoder, server or network contact was made. The
only files added are this document and its machine-readable companion. Every FREEZE, DEFAULT and
RECOMMENDATION above is a proposal; every finding is reported, not repaired; every question is open.
