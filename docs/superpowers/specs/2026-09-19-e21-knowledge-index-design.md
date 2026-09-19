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
