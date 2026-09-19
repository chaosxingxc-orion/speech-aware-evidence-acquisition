# Item E21 (2026-09-19): the knowledge INDEX and index-based context assembly

**Naming.** "E21" is also this program's shorthand for the Earnings-21 carrier
(`scripts/e21_*.py`, `wiki/experiments/.../e21-*`). Everywhere below, **item E21
is the knowledge index, not the Earnings-21 carrier**; the two share nothing but
the two characters.

Engineering item E21. Author: Claude Fable 5.1. Branch `fable/e21` from `7d696378`.
Model-free: zero model, tool, tokenizer, encoder, scorer, server and network contacts.
Nothing was written under `SPEECHRL_DATA_DIR`; the built view lives in this session's scratch.

Authority: **owner decisions 48 and 50 of 2026-09-19**. Source of every design statement below:
`docs/superpowers/specs/2026-09-19-knowledge-index-and-context-assembly-design.md` (sections 3, 4,
6 and 7.0). Precedents whose code pattern this item copies: E17
(`2026-09-19-e17-constant-tool-rendering-design.md` — an episode-level switch, its receipt block,
its render proof, its absent-key falsifier), E18 (`2026-09-19-e18-acquisition-node-design.md` — a
module split across the key and the role rows), E14 `rails/scenario_hints.py` (a released,
hash-pinned construction view and its bounded selection), E20 `rails/context_fit.py` (the COMPACT
disposition this item's degradation ladder hooks into, unchanged).

This item ships the mechanism and its proofs. It registers **no cell**: the index cell, its
derangement twin and its exposure row are the coordinator's, and section 8 below says so again.

---

## 1. What was built

| file | what it is |
|---|---|
| `src/speech_aware_evidence_acquisition/rails/knowledge_index.py` | the rail: the id grammar, the released view and its loader, the registered ordering, the constant-index renderer with the section hoist, the config parser, the per-row assembly, the degradation ladder and the receipt |
| `src/speech_aware_evidence_acquisition/core/base.py` | three registries — `KNOWLEDGE_INDEX_ORDERINGS`, `KNOWLEDGE_INDEX_VIEWS`, `KNOWLEDGE_INDEX_RECEIPTS` — so every new id (ordering, view, receipt) resolves where every other config-declared component id resolves |
| `src/speech_aware_evidence_acquisition/rails/config_tables.py` | the eleventh `episode`-class switch key, its null arm, and the repair of base-lock finding **F-18** (the allowlist docstring said "All three are dotted paths" over what had become nine members) |
| `src/speech_aware_evidence_acquisition/rails/native_episode_config.py` | the key's parse, the eight fail-closed refusals, the paired `roles.<role>.knowledge_index_budget` override, `NativeEpisodeConfig.knowledge_index_json`, `NativeEpisodeRunBinding.knowledge_index` |
| `src/speech_aware_evidence_acquisition/rails/runner.py` | one fail-closed guard: an armed key with no binding stops the flight (section 7) |
| `scripts/build_slurp_knowledge_index_view.py` | the view builder, `--out-root` required, `--check` reproduction |
| `scripts/slurp_knowledge_index_render_proof.py` | the model-free render proof over the 100 sealed B1 contacts |
| `tests/unit/test_e21_knowledge_index.py` | 35 proofs (section 6) |
| `tests/unit/test_config_table_module_switches.py` | the closed-allowlist ratchet, extended by one |
| `configs/policy/native-episode-knowledge-index-v1.json` | a SAMPLE fragment for the future cell; no baseline references it |

### 1.1 The view, `slurp-knowledge-index-v1`

Built from the **released stores only**, each read through its own declared pin, and from the closed
contract inventory mined from `train.jsonl` alone:

| source | pin convention | what it contributes |
|---|---|---|
| `intent-boundaries-v1` (**not** v2 — v2 read HARMFUL in cell B4a) | `release.json` by file bytes, `snapshot.json` by `KnowledgeSnapshot.content_hash()` | the 60 intent cards, their `Activation boundary` and `Confusable exclusions` lines |
| `slot-contracts-v2` (admitted, module M4b) | the same two conventions | the 54 slot cards, their `Admissible formats` and `Extraction cues` lines |
| `scenario-hints-v1` (E14) | file bytes on both files | the 81 construction confusion pairs and every intent's **construction row count**, which is the ordering statistic |
| the closed inventory (`data.slurp.load_slurp_ontology`, `include_synthetic=False`) | the umbrella lock | the 60 legal intents, their scenario pairing, and the 55 legal entity types |

The two pin conventions are declared per pin rather than guessed: the repository has both, and reading
one as the other is how a build "verifies" nothing. The build refused on the first run for exactly
this reason and was repaired, not worked around.

Built counts, reproduced by `--check`:

```
entries = {intent: 60, slot: 54, edge: 81}   shared_sections = 9
legal_intents = 60   legal_slot_types = 55   construction pool = 9,354 utterances
source_split_identity_hash = 67e53fb5f712c40b21b8b54b74e867e6da209f057c68cd40dd987aaa99b19875
snapshot.json   sha256 = f6d61056165a41d91e604a55d80a0aef08491a8052dc713e95eae66cfeb2cd4c
release.json    sha256 = bcfc220b11672169f81e9a9f941e6c1bee05e9a5e3ac7aa3bd6dc448017235d2
completion.json sha256 = 50efd295f99784168edd0aad72782ea62d8c0af4f9232524b9021d97089f6ac2
```

The snapshot's file sha256 **equals** `KnowledgeIndexTable.content_hash()`: the loader re-types
nothing, so a receipt's `content_hash` and the released bytes are one number.

The `exemplar` kind is not built at all (9,354 entries at about 124 characters is 1.16 MB); it is
pointer-and-expansion only, which is the schema's own rule.

### 1.2 The hoist (design question Q6, answered inside the renderer)

Finding F-5 of the design measures the waste: `intent-boundaries-v1`'s `Uncertainty behavior` is
**one identical 199-character string on all 60 cards** (28.3 % of that store), and
`slot-contracts-v2`'s `Missing behavior` has **8 distinct values over 54 cards**. The renderer lifts
them into the index's own section headers (`IU-1`; `SM-1` … `SM-8`) and each entry keeps the exact
byte offset the section was removed from. **No released store is touched and nothing is re-pinned** —
`intent-boundaries-factored-v1` stays unused, and the factoring is a property of the view, not of a
store re-pin cell. `restore_card(residue, hoisted, shared)` splices every card back **byte for
byte**; the builder checks it on all 114 hoisted cards before writing anything, and a unit test
checks it again.

### 1.3 The rendered index

At the recommended defaults, over the released stores:

| variant | chars | tokens @4.60 (derived) |
|---|---:|---:|
| `intent L1 / slot L1 / edge L0` — **the default** | **17,265** | **3,753** |
| `intent L0 / slot L0 / edge L0` — the pure addressable catalogue | 7,626 | 1,658 |
| `intent L1 / slot L1 / edge L1` | 27,413 | 5,959 |

sha256 of the default rendering: `b279dcc016d8fea5bc22f942a404dbcd87c36294780e9b977a4b2da6238d4438`.

The design draft estimated 16,221 characters / 3,526 tokens for the composite index; the built one is
**+6.4 %**, and the difference is exactly the 9 shared-guidance lines and the per-kind section headers
the draft did not budget for.

**Two rendering decisions that deviate from the draft's section 3.3 table, and why.** The draft
writes L0 as "id + display name" and puts the section label on the line. Both are dropped:

* an L0 line is the **id alone**. Grammar rule 1 says the name inside an id is the one the closed
  inventory already legalises, *verbatim*, so `I/play_music` already carries the display name, and
  printing `play music` beside it is precisely the second spelling of a closed label that rule 1
  exists to prevent. It also costs about 2,500 characters of constant prefix across the 195 entries
  for no information;
* the section label (`Activation boundary:`, `Admissible formats:`) is stated **once**, in the kind's
  section header, not once per line — paying for a per-kind constant on every line is the same
  mistake finding F-5 measures inside the cards themselves.

Together these are what keep the built index inside the draft's own budget.

---

## 2. The one key and its defaults

```jsonc
"native_episode": {
  "tool_schema_rendering": "constant",          // E17, a precondition (refusal 7)
  "knowledge_index": {
    "view": "slurp-knowledge-index-v1",
    "release":  {"relpath": "...", "root": "data", "sha256": "..."},
    "snapshot": {"relpath": "...", "root": "data", "sha256": "..."},
    "granularity": {
      "intent": {"level": "L1", "section": "Activation boundary"},
      "slot":   {"level": "L1", "section": "Admissible formats"},
      "edge":   {"level": "L0", "section": "Confusable exclusions"}
    },
    "ordering": "taxonomy-frequency-v1",
    "pointer_budget":   {"intent": 3, "slot": 8, "exemplar_vote": 3},
    "expansion_budget": {"exemplar": 5, "slot_card": 4, "intent_card": 0},
    "solver_citation": "permitted"
  }
}
```

`native_episode.knowledge_index` is the **eleventh** member of the closed allowlist
`rails.config_tables.EPISODE_LEVEL_SWITCH_KEYS`. Its OFF arm is the key's **absence**; there is no
third shape, and a `granularity` may be written as a bare level string or as the `{level, section}`
object above — the two compose the **same canonical text**, so two spellings of one arm are one cell
identity.

**Every design question that touches code is a config value with the recommended default**, never a
constant:

| question | decision | how it is expressed |
|---|---|---|
| **Q1** one key or two | ONE | `native_episode.knowledge_index` arms the prefix *and* the budgets; `apply_to_payload` refuses one half without the other by name |
| **Q3** the intent L1 line | `Activation boundary`, with `Confusable exclusions` folded into the **edge** entries | `granularity.intent.section`, choices `Activation boundary` / `Confusable exclusions` |
| **Q4** the slot L1 line | `Admissible formats` | `granularity.slot.section`, choices `Admissible formats` / `Extraction cues` |
| **Q6** factoring | inside the **renderer**; no store is re-pinned | `HOISTED_SECTIONS` + the view's `shared_sections` |
| **Q7** citation | `permitted` (default). `required` is a `response_format_id` change and a second factor, so it is **refused by name** until its own cell exists | `solver_citation` |
| **Q8** `expansion_budget.slot_card` | **4**, with **0** a legal value | `expansion_budget.slot_card` |
| **Q12** per-role budgets | **OFF by default**: with no override every role receives the same block the Solver receives (today's byte-identical-evidence shape, finding F-4). The Planner-L0-only and Reviewer-cited-only reads are expressible as overrides | `native_episode.roles.<role>.knowledge_index_budget` |

The per-role override is declared **on the role row**, beside the role it budgets, exactly as E18's
acquisition seat is; declaring it inside the module block instead is refused as two spellings of one
override, and declaring it without the module is refused as a half-armed module.

Questions the owner still owns and that this item does **not** decide: **Q2** (is a pure suffix of the
fill a contract change under decision 40), **Q5** (is the derangement twin required on the first
cell), **Q9** (cell order), **Q10** (cross-carrier), **Q11** (does already-legal content newly
rendered need its own exposure row), **Q13** (is the np6 geometry flip part of the cell's claim).

---

## 3. The eight refusals

Fail-closed, in `load_native_episode_config`, before any contact:

1. **an unreleased or hash-mismatched view** — the id at config time (only the released view id is
   admitted, and each pin must be a `{relpath, root: "data", sha256}` under
   `knowledge/slurp/semantic/`), the **bytes** at `load_knowledge_index_table`, which refuses a file
   whose digest moved and a release that does not pin its own snapshot;
2. **a granularity naming an entry kind the view does not carry** — `exemplar` is the one that will
   be tried and it is refused by name; so is an `L2` level, which never lives in the prefix;
3. **`expansion_budget.exemplar > 0` with no exemplar store armed** on any phase (`store_role`
   `train-exemplars` with a `phase_supply` block);
4. **`pointer_budget.intent > candidate_supply.max_candidates`** — the pointer block may never name
   more candidates than the projection produced;
5. **`expansion_budget.slot_card > candidate_supply.max_total_values`**;
6. **an `ordering` id not registered** in `core.base.KNOWLEDGE_INDEX_ORDERINGS`;
7. **the key armed with `tool_schema_rendering` absent or `"per-role"`** — the economic premise of
   the design is the constant prefix. This is the one that will be argued about; it is deliberate,
   and it makes the cell ordering (EFF-1 before the index cell) a machine fact rather than a plan;
8. **a carrier whose descriptor declares no `knowledge_layer`** — today both Earnings descriptors
   (base-lock finding F-1), plus a config that declares no `carrier_lock_key` at all.

Refusals 4 and 5 are checked against **every** declared `candidate_supply` phase block and against
**every** per-role override, not only the module default.

---

## 4. The assembly, and the degradation ladder

Layout rule 4.1, enforced by construction in `IndexAssembly.content_parts()`:

```
[ system ]  contract fill  ->  the index (a pure SUFFIX)        CONSTANT, once per slot
[ user   ]  speech packet                                       row
            POINTER BLOCK    ids + rank/vote, ordered           row, small
            EXPANSION BLOCK  L2 cards, budgeted, ordered        row, bounded, LAST
            agent states                                        row
            role query                                          constant per role
```

* the pointer block is one content part, `evidence_id` `index-pointers`; the transport renders it as
  `[evidence index-pointers] …`;
* each expansion is its **own** content part whose `evidence_id` **is the index id** — the store alias
  `X/10005` replaces `train-exemplars::value:10005`, which removes the 34-character
  store-and-namespace prefix finding F-13 measures at about 1,360 characters per row;
* an expanded card renders as its **residue** plus `Shared guidance: <labels>` — a reference to the
  header, never a second copy of the shared section;
* the expansion order is exemplars (retrieval rank) → the top candidate's slot cards → intent cards,
  so truncating from the **tail** spends the intent cards before the slot cards before the exemplars.

**The ladder** (`index_droppable_items`, producing `rails.context_fit.DroppableItem` values so one
caller can drive both ladders through E20's own `apply_drops`; **E20's behaviour is unchanged**):

```
1. expansions, from the tail            tranche 1
2. the pointer block, below the top-1   tranche 2
3. the L1 index -> L0                   tranche 2
4. NEVER the L0 index, the contract, the speech packet or the states
```

Rule 4 is the safety property: dropping L0 would let the model emit an id the closed inventory does
not contain. Every step is a recorded row disposition (`degradation_step`, carried in the receipt's
`degradation` list and counted as `degradation_steps`), never silent — the honesty requirement owner
decision 45 states for the serving side.

---

## 5. The receipt

One block per row, `saea-native-knowledge-index-v1`, sealed exactly where E17's
`tool_schema_rendering` block is sealed. It carries the view id and its three digests, the
granularity, the ordering, the two budgets and any per-role overrides, the rendered index's sha256
and character count, and per contact:

```
contact_id, role_id, pointer_ids, expanded_ids,
pointer_block_sha256, pointer_block_chars, expansion_block_sha256, expansion_block_chars,
index_sha256, index_chars, system_message_sha256,
cited_ids, citations_resolved, citations_unresolved, unresolved_ids,
degradation[]
```

plus the row-level `distinct_system_message_sha256` — **1 is the constancy claim**, exactly as E17's
`distinct_tool_schemas_sha256 == 1` is. A citation resolves by **membership** in the index (or in this
contact's own pointer/expansion ids), never by parsing, so a hallucinated id is detectable.
Digests and counts only: no rendered text, no card, no exemplar, no draft. The OFF arm seals **no
block**, as E11/E12/E14/E17/E18's OFF arms seal none.

---

## 6. The proofs

### 6.1 The render proof (design section 7.0, the E17 Probe A form)

`scripts/slurp_knowledge_index_render_proof.py`, over the **100 contacts of the first 20 sealed rows**
of `SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TRAIN-FOLD-A-RECOVERY-V2` (read-only), with the key armed
at the recommended defaults and E17 constant tool rendering.

**The estimator is E17's own and no tokenizer was contacted.** E17 derives its prefill numbers from
"character-level longest-common-prefix proxies over sealed requests plus llama.cpp's common-prefix
rule" and says in as many words that "re-tokenising here would have been a tokenizer contact". This
proof uses exactly that: the rendered stream is the system message (the `tools` array included,
because the Qwen3-Omni template renders it inside the system message) followed by every user content
part in wire order; prompt tokens are `chars / 4.60`; cached tokens are the longest common prefix
with the previous request **on the same pinned `id_slot`**, in characters, over 4.60. **Every number
in the table is DERIVED**, exactly as E17's own 50.1 % is.

| position | predicted prompt | predicted prefilled | E17 measured prompt | E17 measured prefilled |
|---|---:|---:|---:|---:|
| perception | 7,827 | **2,387** | 3,597 | 1,373 |
| solver | 8,002 | **423** | 9,960 | 6,591 |
| reviewer #1 | 7,903 | **184** | 10,062 | 7,843 |
| reviewer #2 | 9,261 | **1,357** | 11,813 | 1,757 |
| planner | 9,321 | **1,541** | 11,805 | 9,586 |
| **row** | | **5,892** | | **25,933** as flown / **9,906** measured post-E17 |

At `expansion_budget.slot_card = 0` the predicted row falls further, to **4,018**.

The three properties, all reproduced:

| property | result |
|---|---|
| **P1** one rendered system message over all five contacts of a row and over all 20 rows | **1 distinct sha256** over 100 contacts, on both arms |
| **P2** the Solver's prefill collapses | **6,591 → 423** predicted (the design predicted about 654) |
| **P3** reducing `expansion_budget.slot_card` to 0 moves **no byte before the expansion block** | **true over 100 contacts**, checked positionally *and* textually |

The Solver's own blocks at the defaults: pointer block **511 characters / 12 pointer ids**, expansion
block **8,983 characters / 9 expansions**; at `slot_card = 0`, **395 characters / 5 expansions**.

**The key's own falsifier**, against the sealed B1 request bytes, hashes only: with the key absent
each sealed payload is re-composed and re-hashed, and the digest equals the sealed `payload_sha256` on
**100 of 100** contacts. The same falsifier runs in the unit suite over 25 sealed contacts and skips
when the controlled data root is not mounted.

Proof receipt (this session's scratch, not a repository or data-root path):
`…/scratchpad/e21/out/render-proof.json`; the built view is beside it under
`…/scratchpad/e21/out/knowledge/slurp/semantic/slurp-knowledge-index-v1/`.

**Which production code the proof runs, and which rails it does not.** The rendering path is the
transport's own — `_speech_history_texts`, `_ordered_speech_feature_content`,
`_assert_agent_history_suffix`, the `[evidence <id>] <content>` item format, the two-message
`[system, user]` composition and `project_native_framework_history` / `project_native_history`. The
rails not run are the live-session validity check, the speech-packet loader and the media-confinement
check; none of them moves a byte of the rendered body, and all three need a resident server or the
packet store. The same offline reuse of these functions is already the repository's form in
`rails.phase_material` and `rails.a2t_executable_ground_prompt_fit`.

One consequence worth recording, because it is a custody rail the design did not mention:
`validate_native_framework_contact` refuses a request whose framework `messages[0]` differs from its
own `task_instruction`. A live armed episode composes both from one binding; `apply_to_payload`
therefore rewrites the framework contact envelope's system message too, and re-hashes it, rather than
leaving a stale digest behind.

### 6.2 The unit suite

`tests/unit/test_e21_knowledge_index.py` — 35 tests, all offline, all against a **synthetic** view
built in the module:

* the key resolves in the episode class and its OFF arm is its absence;
* the id grammar, and membership against the closed inventory (a well-formed id the view does not
  carry does **not** resolve);
* citation extraction from free text, with sentence punctuation trimmed only from the tail;
* the hoist is lossless on every card, and a missing shared section is refused;
* the view round-trips and its content hash is its own bytes;
* the ordering is registered, declared and **total** — the same input in any permutation orders the
  same way, edges land on the line after their intent, slots are their own last group;
* an unregistered ordering is refused;
* the index is pure, L0 is strictly shorter than L1, the L1 section is a config value, and the shared
  guidance appears exactly once;
* the exemplar kind can never be an index entry;
* the pointer block carries ids and ranks and **no card text**, and empty selections use the closed
  empty phrases;
* the expansion block is last, ordered by class, and an expanded card references the shared guidance
  rather than copying it;
* **truncating the expansion tail moves no byte before it**;
* the ladder spends the tail first and never L0;
* per-role overrides are OFF by default and expressible;
* **the eight refusals, one test each**, plus `solver_citation: "required"`, plus the module/role
  pairing in both directions;
* the absent key composes the pre-E21 episode and moves no payload byte, and reproduces the sealed
  B1 request hashes;
* the receipt's schema, its counts, and that it contains no rendered text;
* a degradation step is recorded, never silent;
* the render proof's three properties, end to end, on the synthetic store.

### 6.3 Gates

`engineering_base_check.py`, `harness_admission_check.py`, `results_ledger_check.py`,
`tool_catalog_check.py` and `finite_completion_policy_check.py` all **PASS** on this branch. Every
`policy` / `evidence_source` / `scorers` value in the one config fragment added resolves — the
fragment declares none of them; it is a documentation fragment carrying the episode block alone.

---

## 7. What is built but NOT yet wired

The rail, the key, the refusals, the receipt builder and the render proof are complete. The **live
runner wiring** — building a `knowledge_index` binding on `NativeEpisodeRunBinding` from the released
view, deriving each row's `RowSelection` inside the flight, appending the index to the rendered system
message and swapping the value-rendering seam for the pointer/expansion parts — is the index cell's
own step and is **not** in this item.

Until it lands, an armed key cannot fly: `rails/runner.py` refuses a native episode whose
`config.knowledge_index_json` is set while `binding.knowledge_index` is `None`, by name. A config hash
that claims an index the request bytes do not carry is the one failure this item is unwilling to make
possible.

Three things the cell's wiring must close, named here so they are not discovered late:

* **evidence provenance.** `apply_to_payload` rewrites `supplied_evidence` and leaves
  `evidence_provenance` alone; the render proof is unaffected (provenance renders no byte) but a live
  flight composes provenance from its own supply and must emit it for the pointer and expansion
  blocks, whose `source_uri` scheme this item writes as `knowledge-index://<view>/<id>`.
* **the row selector.** `RowSelection` is the typed input the assembly takes; deriving it in flight
  from the Perception state, the retrieved exemplars' own construction intents and the candidate
  projection's bound types is the binding's job. The render proof derives it from the sealed request
  and the sealed Perception state, which is the same information a live row has.
* **the exemplar retrieval RANK.** Today's rendering is in lexicographic evidence-id order and
  carries no rank at all (M1 analysis section 4.2); under the key the order is the retrieval rank.
  The sealed arm does not record that rank, so the proof uses the sealed render order and says so.

---

### 7.1 What item E21w wired (2026-09-19), and what it measured

Item **E21w**, branch `fable/e21w` from `f7acb0aa`. Model-free: zero model, tool,
tokenizer, encoder, scorer, server and network contacts. Nothing was written under
`SPEECHRL_DATA_DIR`; the view was rebuilt into this session's scratch and reproduced the
same three digests (`release.json` `bcfc220b…`, `snapshot.json` `f6d61056…`,
`completion.json` `50efd295…`).

The three gaps section 7 named are closed, and the rest of the live seam with them:

| gap / seam | where it now lives |
|---|---|
| the **binding** | `rails.knowledge_index.build_knowledge_index_binding` + `KnowledgeIndexBinding`, built by `core.flight.FlightRuntime._knowledge_index_binding` at run start and carried on `NativeEpisodeRunBinding.knowledge_index`. It loads the released view under its two declared pins — the release by FILE BYTES, the snapshot by CONTENT HASH — and refuses by name when the snapshot's file digest is not `KnowledgeIndexTable.content_hash()` |
| the **row selector** | `rails.knowledge_index.derive_row_selection`, from the Perception state's own ranked candidates, the retrieved exemplars' own construction intents and the candidate projection's bound slot types; it returns a PROVENANCE record naming where each half came from |
| the **retrieval rank** | `rails.knowledge_index.value_retrieval_ranks` / `retrieval_similarity`, recorded in `rails.phase_supply.build_supply_for_phase` beside the decision that makes it |
| the **seam swap** | `rails.runner._agent_messages` + its `_index_content`: the index is a pure suffix of the contract fill and the row's `value:` blocks become the pointer block plus the bounded expansion |
| **provenance** | the pointer/expansion parts carry `source_uri` `knowledge-index://<view>/<id>`, and `rails.core_client._supply_provenance` turns each into a `knowledge-index` provenance row instead of a `rails-supply` one |
| **per-role budgets** | resolved at request composition from the role's own kind, OFF by default |
| the **ladder** | `rails.context_fit.index_ladder` binds `index_droppable_items` to the request's own content indices, so ONE caller drives both ladders through E20's own `apply_drops` |
| the **receipt** | `compact_receipt["knowledge_index"]`, sealed exactly where E17's `tool_schema_rendering` block is, plus four run-level counters beside E20's `native_episode_dispositions` |

**The wire check** — `scripts/knowledge_index_wire_check.py`, the E17 Probe A form one level
deeper than section 6.1: it drives the PRODUCTION runner seam (not the rail) over the same 20
sealed B1 rows, read-only and hashes only, ON and OFF, and then over the four engineering smoke
rows of `SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-SMOKE-4-V2`. Receipt (this session's scratch,
not a repository or data-root path): `…/scratchpad/e21w/out/wire-check.json`.

| property | 20 sealed B1 rows (100 contacts) | 4 smoke rows (20 contacts) |
|---|---|---|
| **W1** OFF: the seam re-composes the sealed messages byte for byte | **100 / 100** | **20 / 20** |
| **W1** OFF: the rail re-composes the sealed `payload_sha256` | **100 / 100** | **20 / 20** |
| **W2** ON: distinct rendered system-message sha256 | **1** | **1** |
| **W3** ON-vs-OFF differing payload keys | `task_instruction`, `history`, `supplied_evidence` | same |
| **W5** provenance rows / of them naming the view | 820 / **820** | 164 / **164** |
| **W6** truncation violations at `slot_card = 0` | **0** | **0** |
| **W7** `validate_native_framework_contact` after the envelope rewrite | **100 / 100** | **20 / 20** |
| **W7** receipt rows populated | **100 / 100** | **20 / 20** |
| findings | **0** | **0** |

`evidence_provenance` is NOT in the W3 key set, and that is not an omission: `apply_to_payload`
composes no provenance (section 7's first gap), so the payload-level diff cannot show it. W5
proves it instead, through the production composer over the seam's own parts — one row per
pointer/expansion part, `lock_key` `knowledge-index`, `relpath` `<view>/<id>`. This arm carries
no `key:` parts at all, which is why all 820 provenance rows are index rows.

**The per-position table, DERIVED with E17's own estimator and no tokenizer** (medians over the
100 contacts, beside section 6.1's render-proof numbers):

| position | E21w predicted prompt | E21w predicted prefilled | render-proof predicted prefilled |
|---|---:|---:|---:|
| perception | 5,955 | **378** | 2,387 |
| solver | 8,002 | **2,343** | 423 |
| reviewer #1 | 7,903 | **184** | 184 |
| reviewer #2 | 9,261 | **1,357** | 1,357 |
| planner | 9,321 | **1,541** | 1,541 |
| **row** | | **5,803** | **5,892** |

The row total moves by **−1.5 %**; what moved is the split between the Perception and Solver
positions, and it moved for a reason worth recording. The render proof derived ONE selection per
row (from the Solver contact's sealed payload) and applied it to all five contacts. A LIVE row
cannot: at the Perception contact there is no Perception state and, on this arm, no candidate
projection either, so that contact's pointer/expansion block is smaller and the Solver shares less
prefix with it. The live numbers are the causal ones; section 6.1's P2 figure of 423 assumed a
Perception request that had already read the Solver's own selection.

The smoke arm reads 5,956 / 7,749 / 7,656 / 9,013 / 9,058 predicted prompt and 5,956 / 2,100 /
188 / 1,358 / 1,535 predicted prefilled, row **11,137** — the Perception figure is the whole
prompt because with four rows over four slots every row's first contact is the first request on
its slot and has no predecessor to share a prefix with.

**The ladder (W8).** On a Solver contact the armed request has 11 content parts and
`rails.context_fit.droppable_items` returns **10** index items: the 9 expansions from the TAIL in
tranche 1, then the pointer block in tranche 2 — never before it — and `apply_drops` removes
exactly one part per item. E20's own ladder is unchanged with the key absent (its 19 tests pass
untouched).

**Design decisions this item had to make, and why.**

1. **The selection is per CONTACT, not per row.** A live Perception contact cannot read its own
   future answer. When no Perception state exists the retrieval order stands in, and the receipt's
   `selection.candidate_source` says `retrieval-order` rather than `perception-state`.
2. **The L1 → L0 granularity step is NOT executed at the dispatch seam**, and is refused there by
   name. It re-renders the CONSTANT PREFIX, which lives in the system message;
   `CompactableRequest` deliberately excludes the system message, and re-rendering it on one
   contact would break the very prefix constancy the key exists for. A row that still does not fit
   after the two content tranches takes E20's terminal `context_compaction` disposition, exactly
   as an unarmed one does.
3. **A candidate the closed inventory does not carry is dropped and COUNTED**, not raised on. A
   candidate is the Perception node's own output; refusing the row would kill a flight on model
   noise and rendering the spelling would put a second label into a closed list. The receipt's
   `selection.refused_candidates` is the honest third option.
4. **The rank is re-derived, not re-plumbed.** `rails.kb_policy._fuse_supply_filter` computes each
   value's best-admitted-supporting-facet score and then returns `tuple(sorted(set(...)))`;
   `value_retrieval_ranks` re-derives exactly that number from the `RankResult` and the snapshot's
   own value-to-facet association, so it is reproducible from the sealed vectors and the store.
   It is recorded ONLY into a dict a caller hands over, which is only when the key is armed.
   `saea-phase-supply-v2` is deliberately NOT extended: that receipt is hashed by cells that do not
   arm this key, and the similarity is named on the index receipt's own `retrieval_rank` block
   instead (`{"recorded": false}` when the supply recorded none — never implied).
5. **The four run-level counters are ADDED only when a row sealed the block**, so an unarmed
   dispatch still reports exactly E20's four counters and its manifest is byte-identical.
6. **The binding and the key are refused in BOTH directions**: an armed key with no binding, and a
   binding with no armed key. The second is new here and is the same defect seen from the other
   side — an index no config hash claims.

**What section 7.1 does not authorise.** No view RELEASE (nothing was written under
`SPEECHRL_DATA_DIR` and no release-pins registration file exists). No cell, no preregistration, no
exposure-ledger row, no `contracts.ExecutionPlan`, no readiness package, no armed baseline. **No
contact of any kind was made**, and no number above is a task measurement: every prefill figure is
DERIVED with E17's estimator, and nothing here claims anything about SLU F1, intent accuracy or
ordering quality.


## 8. What this does not authorise

No owner decision is recorded. **No view release** (the builder writes nothing under
`SPEECHRL_DATA_DIR` — `--out-root` is required and this session passed a scratch directory, and no
release-pins registration file was written; registering the release is a separate zero-contact job).
**No cell**, no preregistration, no exposure-ledger row, no `contracts.ExecutionPlan`, no readiness
package, no armed baseline (the sample fragment is referenced by nothing). **No contact** of any kind
was made. No claim is made about SLU F1, intent accuracy, ordering, or any quality metric: the only
ordering experiment this program has run (Audio2Tool ORG-1) read **−3.23 pp [−4.15, −2.33]** with
every domain losing, so the index's ordering is a declared rule with a twin ahead of it, not a
hypothesis with a prediction. Every prefill number in section 6.1 is **derived**, in the same way
lever L3 is derived, and every SLURP figure quoted from a verdict is a **development** number on
TRAIN Fold A, which owner decision 28 forbids comparing with a published test baseline.
