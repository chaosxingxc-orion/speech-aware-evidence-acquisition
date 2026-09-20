# Item E24 (2026-09-20): the DERANGEMENT TWIN of the knowledge index

**Naming.** "E21" is also this program's shorthand for the Earnings-21 carrier
(`scripts/e21_*.py`, `wiki/experiments/.../e21-*`). Everywhere below, **item E21
is the knowledge index** and **item E24 is its derangement twin**; neither is the
Earnings-21 carrier.

Engineering item E24. Author: Claude Fable 5.1. Branch `fable/e24` from `4c5a04ef`.
Model-free: zero model, tool, tokenizer, encoder, ASR, scorer, server and network contacts.
Nothing was written under `SPEECHRL_DATA_DIR`; the built twin lives in this session's scratch.

Authority: **owner decisions 48, 50 and 53 of 2026-09-19**, and design section 7.2 of
`docs/superpowers/specs/2026-09-19-knowledge-index-and-context-assembly-design.md`
("The twin, and why it is not optional"). The item it twins is
`docs/superpowers/specs/2026-09-19-e21-knowledge-index-design.md` (the view schema, the two
pin conventions, the renderer, the receipt) and its section 7.1 (E21w, the live seam).
The mechanism this item copies is module M1's own derangement twin, which this program has
already flown.

This item ships the twin and its proofs. It registers **no cell**, releases **no view** and
opens **no exposure row**: section 8 below says so again.

---

## 1. Why a twin, in one paragraph

`native_episode.knowledge_index` changes **two** things at once in the eyes of a critic: the
prefix now *contains* 60 intent and 54 slot contracts that used to appear only when
retrieved, and it now *omits* the retrieved cards' full text. A NEUTRAL or positive read then
has at least three explanations — the index's **content** helps, its mere **presence and
shape** help, or dropping about 24,000 characters of card text helps by removing distraction.
The twin separates them by holding every byte of form and destroying only the
**correspondence** between an id and its contract line. The precedent is measured, not
hypothetical: Audio2Tool ORG-1 re-rendered 152 unchanged registry rows under domain headers,
moved no store byte, and read **−3.23 pp [−4.15, −2.33]** with every domain losing. A cell
that changes prompt form on this scale without a form-matched control cannot distinguish its
mechanism from its shape.

---

## 2. What was built

| file | what changed |
|---|---|
| `src/speech_aware_evidence_acquisition/rails/knowledge_index.py` | `KNOWLEDGE_INDEX_TWIN_VIEW_ID` and the admitted-view tuple; the derangement (`_draw_below`, `sattolo_derangement`, `derange_snapshot`, `twin_line_multisets`); the twin half of refusal 1 (`validate_twin_release`); `KnowledgeIndexTable.twin_of` / `render_label` / `header_view_id` / `is_twin`; `IndexAssembly.view_id`; `default_index_plan`; the receipt's `twin_of` |
| `scripts/build_slurp_knowledge_index_view.py` | `--twin-seed <int>`, the twin's own namespace and release/completion documents, and `build_twin` — which proves T1, T2 and T3 **before it writes a byte** |
| `tests/unit/test_e24_knowledge_index_twin.py` | 60 proofs (section 6) |

No new module, no `rails/probes/` entry, no `TaskAdapter` or controller subclass, no
`launcher/` directory: the twin is a second **released view** of the view schema E21 already
built, loaded through the same loader, rendered by the same renderer and armed by the same
config key with one field changed. That is the whole engineering claim.

**The builder, not a sibling script.** A sibling would have to re-read the three released
source stores, re-mine the closed inventory and re-hoist the 114 cards, and would then be a
second implementation of the build whose drift nobody would notice until the two views
disagreed. `--twin-seed` derives the twin from the **in-memory source snapshot this build just
produced**, so a twin can never be a derangement of bytes nobody verified, and the source path
is untouched when the flag is absent.

---

## 3. The twin, `slurp-knowledge-index-twin-v1`

**What moves** (`TWIN_MOVED_FIELDS`): an entry's `l1` table and its L2 card — the `residue`
and the `hoisted` splice table that restores it. They move **together**, as one value, which
is what makes "the same permutation on L1 and L2" true by construction rather than by a second
draw: an expansion of id `X` shows the same donor's card that `X`'s prefix line came from.

**What is held** (`TWIN_HELD_FIELDS`): `id`, `kind`, `group` and `rank` — so the ids, the
taxonomy grouping and the **construction ordering statistics** are byte-identical, and
`taxonomy_frequency_order` produces the same order over the same ids on both arms. The
`shared_sections` header, the `legal_intents` and `legal_slot_types` inventories, the
`store_pins`, the `source_split_identity_hash` and the construction utterance count are held
too.

**The permutation.** Within each kind, independently — an intent line among intents, a slot
line among slots, an edge line among edges. Deranging **across** kinds would move a slot's
`Admissible formats` line onto an intent id and change the rendered length of every line.
`sattolo_derangement` is Sattolo's algorithm: the draw is strictly **below** the position
(that one line is what separates it from Fisher–Yates), so the result is a single cycle of
length *n* and therefore has **zero fixed points as a property of the algorithm, not of the
seed**. `count < 2` has no derangement and is refused rather than silently returning the
identity.

**The draw is a sha256 counter stream, not `random`.** A released control has to reproduce
from its recorded seed for as long as the cell it controls is cited, and that must not depend
on a standard-library generator's internals. `_draw_below` rejection-samples the top
`(bound-1).bit_length()` bits of `sha256(f"{stream}:{counter}:{attempt}")`; the stream key is
`saea-knowledge-index-twin:<seed>:<kind>`.

**The release.** The twin's `release.json` carries the source's shape plus exactly three
fields (`TWIN_RELEASE_KEYS`):

```jsonc
"twin_of":     {"view_id": "slurp-knowledge-index-v1", "snapshot_content_hash": "f6d61056…"},
"derangement": {"algorithm": "sattolo-cycle-sha256-stream-v1", "seed": 20260920,
                "kinds": {"edge": 81, "intent": 60, "slot": 54},
                "permutation_sha256": "908044…", "fixed_points": 0,
                "moved_fields": [...], "held_fields": [...]},
"gold_read":   false
```

`gold_read: false` is not decoration: the twin reads no gold because it reads **nothing new at
all** — every byte in it is a byte of the released source view, re-assigned.

### 3.1 The rendered header states the SOURCE view's id, on both arms

`render_constant_index` prints the view id in the index's first line. The twin's id is five
characters longer than the source's, and that one difference would shift every byte after it —
so the twin would not be form-matched, and the 17,265-character prefix would not be the same
prefix. Worse, a header that reads `slurp-knowledge-index-twin-v1` **tells the model which arm
it is on**: a control the subject can read is not a control.

`KnowledgeIndexTable.render_label` therefore carries the id the header states, and
`load_knowledge_index_table` sets it from the twin's own `twin_of.view_id`. Three properties
keep this honest rather than sly:

* the **snapshot** is untouched by it — `render_label` is not in `as_json()`, so the snapshot's
  file sha256 and `KnowledgeIndexTable.content_hash()` remain one number, for the twin exactly
  as for the source;
* the **receipt** names the twin (`view.view_id` is the twin id and `view.twin_of` is stated),
  so no reader of a flight has to infer the arm;
* the **provenance** names the twin: `IndexAssembly.view_id` puts the twin's real id in
  `knowledge-index://<view>/<id>`, and provenance renders no byte of the prompt.

Which arm flew is a fact of the release, the pins, the config hash and the receipt. It is never
a fact of the token stream.

---

## 4. The three proofs, and what they measured

The builder refuses on any of them **before writing a byte** — the precedent is the source
build's own `restore_card` check over all 114 hoisted cards.

| | property | how it is checked | result on the released view, seed 20260920 |
|---|---|---|---|
| **T1** | zero fixed points | inside `derange_snapshot`, by **CONTENT** and not only by position: two entries whose released lines happened to be identical would leave an id carrying its own contract even under a position-derangement, and that is a broken control rather than an unlucky draw | **0** fixed points over 195 entries (60 intent, 54 slot, 81 edge) |
| **T2** | the per-kind multiset of L1 lines and L2 cards is unchanged | `twin_line_multisets`, plus a byte-equality check on the held fields and the shared sections | **equal** on all three kinds; ids, groups, ranks and the 9 shared sections held byte for byte |
| **T3** | the rendered index has the same length | both snapshots rendered through the production renderer at the recommended defaults | **17,265 = 17,265** characters, **227 = 227** lines |

Rendered sha256: source `b279dcc016d8fea5bc22f942a404dbcd87c36294780e9b977a4b2da6238d4438` —
the number item E21 recorded, so **the source's rendering did not move** — and twin
`cf754db2da7e38e12bf11ae30b95e911cd0d80bea5ba593387317d003b72701f`.

**Two honest readings of T3.**

* "Same length" is the **total**, not the line. A line is `id + "  " + statement`; the ids are
  held and the statements are re-assigned within a kind, so an individual line's length moves
  while the multiset of statements per kind — and therefore the sum — does not. What is matched
  is the prefix's character count, its line count, its ids, its grouping and its order.
* At the recommended defaults the **edge** kind renders **L0** (the id alone), so **114 of the
  227 rendered lines** are re-assigned: the 60 intent and 54 slot L1 lines. The edge derangement
  is real but invisible at `edge: "L0"`. At `edge: "L1"` both arms render **27,413 = 27,413**
  characters with **195 of 227** lines re-assigned — the same figure item E21 recorded for the
  all-L1 variant.

### 4.1 The one residual, named rather than discovered late

The constant prefix is matched exactly. The **row's expansion block is not**, and cannot be
under this design: at the defaults a row expands up to 4 slot cards, and a slot card's length
varies (mean 1,389 characters, mean |Δ| between the arms **641**, max 2,564, **Σ Δ = 0** over
all 54 — the multiset is preserved, the per-row draw is not). The same holds for intent cards
(mean 502, mean |Δ| 68, max 214, Σ Δ = 0) whose default budget is 0. Exemplar expansions are
the row's own retrieval and are byte-identical on both arms.

Three consequences the cell must decide, not this item:

1. the **pointer block** is ids and ranks only and is byte-identical on the two arms, always;
2. a cell that wants a strictly byte-matched request sets `expansion_budget.slot_card: 0` and
   `intent_card: 0`, at which point the whole expansion block is exemplars and the two arms
   differ by **no byte** outside the prefix's re-assignment;
3. a cell that keeps the default budgets accepts a row-level length difference in the **last,
   uncacheable** region of the prompt, whose expectation over a roster is zero. It must say so
   in its own verdict rather than claim a byte-exact twin.

---

## 5. The loader, the refusals and the receipt

The twin is loaded **exactly like the source** — it is a released, hash-pinned view, not a test
fixture. `parse_knowledge_index_config` admits both ids (`KNOWLEDGE_INDEX_VIEW_IDS`), the pins
are the same `{relpath, root: "data", sha256}` under `knowledge/slurp/semantic/`,
`load_knowledge_index_table` checks the same byte digests and the same release↔snapshot
agreement, and `build_knowledge_index_binding` still refuses a view whose file digest is not
its `content_hash()`.

`validate_twin_release` adds refusal 1's twin half, **in both directions**:

* a **twin view id whose release declares no `twin_of`, no `derangement` or no
  `gold_read: false`** — an unproven control, which is worse than no control because it will be
  cited as one;
* a **source view id whose release declares any of the three** — a twin wearing the source's
  name, which would put a deranged prefix behind a config hash that claims the real index;
* a `derangement` whose `fixed_points` is not `0`, whose `seed` is not an integer, whose
  `permutation_sha256` is not a 64-character digest, or whose `kinds` table is empty;
* a `twin_of` naming any view other than `slurp-knowledge-index-v1`.

The receipt's `view` block gains `twin_of` **only on a twin arm**, so a source arm's receipt
keeps exactly the bytes item E21 sealed and a reader never infers the arm from an absent field:
on a twin it is stated.

---

## 6. The proofs in the suite, and the gates

`tests/unit/test_e24_knowledge_index_twin.py` — **60 tests**, all offline, all against synthetic
views built in the module (one reused from the E21 suite, one equal-width view built here):

* Sattolo has zero fixed points and is one cycle, over 7 sizes × 4 seeds, and refuses `n < 2`;
* the draw is deterministic, seed-sensitive and kind-sensitive;
* no entry keeps its own content, for three seeds, in every kind; no line moves across kinds;
* the per-kind multiset of L1 lines and L2 cards is unchanged; ids, groups, ranks, shared
  sections, inventories and ordering are held; the twin's cards still restore byte for byte;
* one permutation moves the L1 line and its L2 card together;
* the rendered index has the same length, the same line count and a different sha256; the header
  does not name the arm; a twin loaded **without** its release states its own id, which is why
  the loader — never the snapshot — is what sets the label;
* the build reproduces from its seed and the record states what a reader needs;
* the config admits the twin id, `core.base.KNOWLEDGE_INDEX_VIEWS` resolves it, the loader and
  the binding accept it, the receipt names it and carries `twin_of`, and the eight refusal cases
  above each fail closed;
* the assembly produces a byte-identical pointer block and byte-equal expansion sizes with
  different contents on the equal-width view, and the twin names itself in provenance only.

Module set, on this branch: `test_e21_knowledge_index.py`, `test_config_table_module_switches.py`,
`test_native_episode_config.py` and the new file — **249 passed**.

Gates, on this branch: `engineering_base_check.py`, `harness_admission_check.py`,
`results_ledger_check.py`, `tool_catalog_check.py` and `finite_completion_policy_check.py` all
**PASS**.

---

## 7. What was built, and where

Built with `--twin-seed 20260920` into this session's scratch (**not** the data root, which
still carries only `slurp-knowledge-index-v1`):

```
knowledge/slurp/semantic/slurp-knowledge-index-twin-v1/
  snapshot.json   sha256 = 9620a595b11e760fd0aeca78641fd8e4230c002d7e51fb9ebc3811827c53ba1b
  release.json    sha256 = c77021cb642940b6b65612c8e35561b6a107768be6d556c9a16db5496329eb27
  completion.json sha256 = 0c56cf9e7af3c6d11e25eed2385988262600a03ef265a58691f42532097c87c9

twin_of            = slurp-knowledge-index-v1 @ f6d61056165a41d91e604a55d80a0aef08491a8052dc713e95eae66cfeb2cd4c
permutation_sha256 = 908044534f734676aca1a60aa61475691124d55880e18268f3b96664849dff97
entries            = {intent: 60, slot: 54, edge: 81}   shared_sections = 9
rendered           = 17,265 chars / 227 lines at the defaults (the source's 17,265 / 227)
```

The snapshot's file sha256 **equals** `KnowledgeIndexTable.content_hash()`, for the twin exactly
as for the source. `--twin-seed 20260920 --check` reproduces all three files; the source's own
`--check` against the released data root still reads `OK` with `snapshot_sha256=f6d61056…`, which
is the proof that no source byte moved.

Releasing the twin into the data root and writing its release pins beside
`docs/readiness/2026-09-19-slurp-knowledge-index-release-pins-v1.json` is the coordinator's
separate, zero-contact job. This item wrote no pins file.

---

## 8. What this does not authorise

No owner decision is recorded. **No view release** — the builder requires `--out-root`, this
session passed a scratch directory, nothing was written under `SPEECHRL_DATA_DIR` and no
release-pins registration file was written or edited. **No cell**, no preregistration, no
exposure-ledger row, no `contracts.ExecutionPlan`, no readiness package, no armed baseline: no
config fragment in this repository names the twin view id. **No contact** of any kind was made —
zero model, tool, tokenizer, encoder, ASR, scorer, server and network contacts, and no byte of
utterance text or gold label was printed or persisted. No claim is made about SLU F1, intent
accuracy, ordering or any quality metric: the twin is a control, and a control predicts nothing.
Every character count above is a measured property of a rendered string, never a token
measurement — nothing here was tokenized.
