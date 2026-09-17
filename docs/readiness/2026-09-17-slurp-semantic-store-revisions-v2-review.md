# Root review of the SLURP semantic store revisions v2 (E5b)

Date: 2026-09-17. Item: `docs/superpowers/specs/2026-09-16-slurp-v2-base-program-design.md`
section 3 rows M4a / M4b and section 4 item E5. Branch `fable/e5b-contract-revisions`.
Zero model, tokenizer, encoder, scorer, GPU and tool contacts; the authoring is a root read of the
governed construction pool, exactly as the 2026-09-13 v1 authoring was root-authored.
No utterance text is reproduced in this note.

Two revised stores are released and pinned; nothing is admitted and nothing is scheduled. The two
baseline fragments are held.

## 1. What this revision is allowed to use

Targeting comes from `docs/results/2026-09-17-slurp-a3-coverage-confusion-audit-v1.md`: FIX-2
(the one-directional qa/general contrast, 11 rows), FIX-4 (the `date` emit-when-spoken rule plus the
five omission-dominated types of T5) and FIX-5 (the `time` spoken-form representation rule, 46 rows).
The audit chooses **which** cards are revised. Every rule sentence and every surface form written
into a card is derived from the governed TRAIN construction pool only —
`prepared/SAEA-SLURP-SEMANTIC-AUTHORING-PREPARE-V1/support.json`
(SHA-256 `1be15d89…`, 474 intent-support utterances / 2,037 recordings) and its model-free slot
review material (SHA-256 `858764…`, 803 utterances / 1,388 mentions / 3,162 recordings) — under the
2026-09-13 exclusion: every TRAIN utterance with a recording in Fold A, Fold B or DEV-1000 is
outside the pool. No DEV or test content, no anchor output, no scorer feedback and no error list was
read to author a value. The 2026-09-13 authoring rules still hold: observed intent/type
co-occurrence is evidence, never a required-slot schema, and the source limitations recorded in v1
are retained verbatim.

## 2. Intent store: five of sixty cards (M4a, FIX-2)

The boundary is stated **one-directionally**. Each revised card says when the request is *not* its
own label and belongs to `general_quirky`; no card receives a new push *out of* `general_quirky`.
The v1 sentence "avoid treating all questions as quirky" — the reverse-direction push — is replaced
by the positive criterion it was built on.

| Card | Change |
| --- | --- |
| `general_quirky` | The single `qa_factoid` exclusion becomes four named exclusions (`general_greet`, `general_joke`, `qa_definition`, `qa_factoid`), each stating the neighbour's positive criterion and returning the targetless case to `general_quirky`; uncertainty behaviour gains the open-domain clause. |
| `qa_factoid` | Gains a `general_quirky` exclusion: factoid support always asks a determinate fact about a named entity, property or relation; a request naming no such fact target is `general_quirky`. Uncertainty clause added. |
| `qa_definition` | Gains a `general_quirky` exclusion keyed on the term whose meaning is asked (the support marks it as the definition word). Uncertainty clause added. |
| `general_greet` | Gains a `general_quirky` exclusion: greet support is a greeting or a question about the assistant's own state; anything asked beyond that is `general_quirky`. Uncertainty clause added. |
| `general_joke` | Its existing `general_quirky` exclusion is restated on the evidence (joke support asks for or sets up a joke) and keeps the "an unusual request does not become a joke" clause. Uncertainty clause added. |

The added uncertainty sentence is identical on all five cards: *an open-domain, conversational or
unanswerable request with no device, media, information-lookup or scheduling target is
general_quirky, not qa_\**.

Evidence counted (construction pool, counts only): 8 selected support utterances per intent. Of the
8 `general_quirky` rows, the same 7 name no device, media, information-lookup or scheduling target
and carry no entity annotation at all; the eighth is the heterogeneous row already recorded as a v1
limitation, which is kept unchanged. Of the 8 `qa_factoid` rows, 6 carry a named person or place
entity and all 8 ask for a determinate fact. Of the 8 `qa_definition` rows, 7 carry a
`definition_word` entity. All 8 `general_greet` rows are greetings or state-of-being exchanges. All
8 `general_joke` rows request or reference a joke; 3 carry a `joke_type`. The generic target test is
grounded in the `general_quirky` group itself, so the provenance of each revised card is exactly its
own support group plus the groups of the neighbours it names (5 / 2 / 2 / 2 / 1 groups).

Deliberately unchanged: every `activation_boundary` line (section 5), the two v1 limitations of
`general_quirky` — including "do not use this label as an automatic catch-all", which records a
support anomaly rather than a routing preference — and all 55 other cards, byte for byte.

## 3. Slot store: eight of fifty-four cards (M4b, FIX-4 / FIX-5)

Each revised card gains one extraction cue (semantic role, the intents the construction pool
actually pairs the type with, and the observed span convention). The seven omission-dominated types
additionally gain an explicit emit-when-spoken sentence **in front of** the unchanged
omit-and-never-invent rule, which in v1 spoke only about omission. `time`, whose failure is
representation rather than omission, keeps its missing behaviour and gains the spoken-form rule
instead.

| Card | Change | Construction evidence (mentions) |
| --- | --- | --- |
| `date` | Emit-when-spoken; the cue names `weather_query`, `datetime_query`, `calendar_query`, `news_query`, `recommendation_events`, `calendar_set`, `calendar_remove`, `alarm_set`, `alarm_remove`, `transport_ticket`, and states that relative and absolute calendar expressions are both annotated as `date` whenever spoken | 171 mentions over 40 intents; 5 / 4 / 13 / 6 / 6 for the five named FIX-4 intents; 112 one-word and 50 two-word spans |
| `time` | Spoken-form representation rule with five attested surface forms | 131 mentions, 0 with a digit, 0 with a colon, 67 carrying a spoken `am`/`pm` token |
| `media_type` | Emit-when-spoken; medium/channel/service role, never the content title | 46 mentions over 11 intents; 42 one-word spans |
| `transport_type` | Emit-when-spoken; mode, not provider, class or destination | 37 mentions over 4 intents; 37 one-word spans |
| `business_type` | Emit-when-spoken; category noun with its spoken modifiers | 33 mentions over 11 intents; 26 one-word, 6 two-word |
| `order_type` | Emit-when-spoken; fulfillment mode itself | 15 mentions over 3 intents; 13 one-word |
| `relation` | Emit-when-spoken; role word with its possessive ending, separate from an adjacent name | 48 mentions over 17 intents; 37 one-word, 11 two-word |
| `event_name` | Emit-when-spoken; occasion or activity, named most often under `calendar_set` / `calendar_query` | 88 mentions over 21 intents; 17 and 14 for those two intents; spans of one to five words |

`event_name` is inside the revision because item E5's own emit-when-spoken clause names its two
intents (`calendar_query`, `calendar_set`); it is also the sixth omission-dominated type of audit
table T5 (22 of 41 gold rows omitted). This is the one scope decision in the set — see section 9.

Deliberately unchanged: **all 402 intent bindings**, every semantic role string, every
`ambiguity_behavior`, every `limitations` entry, every `admissible_formats` entry except the one
appended to `time`, and all 46 other cards, byte for byte. No binding was added, so no
candidate-keyed supply decision changes.

Every identifier a revised card names was checked against the 60 intent ids and 54 entity types; a
card that invents a label would teach the Solver an id the official scorer cannot accept, which is
the out-of-inventory failure mode of audit table T3.

## 4. Released stores

| Store | Values | Facets | Source recordings | Snapshot content SHA-256 |
| --- | ---: | ---: | ---: | --- |
| `intent-boundaries-v2` | 60 | 60 | 2,037 | `8a27424a84d5b419e033391b9bba00f30952de520c993237ea0219a9978c07c5` |
| `slot-contracts-v2` | 54 | 54 | 3,162 | `d5992bd12687cbd0204c14fc4e29f987697b8751321d524d7707229032f5bdec` |

Both were built by `saea-driver prepare-semantic-knowledge` from the two registrations, with the
same builder policies (`saea-authored-intent-boundaries-v1`, `saea-authored-slot-contracts-v1`), the
same construction scope (37,407 recordings), the same permitted support rosters and split identities
(`f76a7d00…`, `1253ec6c…`) and the same three exclusion rosters as v1. Completion receipts record
model / tool / scorer contacts = 0. Every pin is in
`docs/readiness/2026-09-17-slurp-semantic-store-release-pins-v2.json`.

As an independent check the same builders were run in memory over the **v1** sources and reproduced
the released v1 snapshot content hashes `5520b844…` and `11c246e4…` exactly, so the v2 hashes above
come from the same compilation path, not from a re-implementation.

## 5. Retrieval-key status: no facet needs re-encoding

The intent retrieval key is `intent_id` plus the `activation_boundary` lines; the slot facet key is
`slot_id` plus the `intent_id: semantic_role` bindings. Neither was touched, so every facet
representation is byte-identical to v1 for both stores. Proved two ways: facet-by-facet string
equality against the v1 snapshots, and — for the intent store — facet-by-facet equality of
`sha256(representation)` against all 60 `text_sha256` values in the sealed key-encoding index
`prepared/SAEA-SLURP-INTENT-BOUNDARY-KEY-ENCODING-V1/index.json`. **Zero stale facets; the sealed
`facets.jsonl` (`76e8d16a…`) still binds and no re-encoding contact is required.**

The sealed encoding receipt names the v1 snapshot content hash `4579079c…` in its inputs, because
that is the snapshot it was run against. Nothing in the runtime path compares that receipt to the
loaded snapshot — the vectors are keyed by facet id — and the key text is identical, so the binding
is semantically exact. Re-encoding would produce the same vectors at the cost of a new tool contact.

What does change is the prepared phase-supply artifact identity: it binds both the knowledge
snapshot content hash and the composed config values, so each cell must prepare its own phase supply
before contact. Both fragments say so and stay held.

## 6. Containment

`rails.runner._assert_agent_control_excludes_knowledge_payloads` refuses a control turn that
contains, casefolded, any facet representation or value content of the bound snapshot whose stripped
length is at least 8 characters. Checked with the same rule
(`analysis.slurp_slot_vocabulary.containment_collisions`) over the protected material of both v2
snapshots against all four anchor control turns (`slurp_native_role_perception_v3.txt`,
`…planner_v1.txt`, `…reviewer_v1.txt`, `…solver_v2.txt`), the task-contract template
(`slurp_native_role_context_v3.txt`) and the rendered task contract
(`slurp-label-inventory` fill, rendered text SHA-256 `485f8f20…`):
**0 collisions, in every combination.** A regression test carries the same check.

## 7. Rendered value sizes

| Store | v1 total | v2 total | Delta | v1 words | v2 words |
| --- | ---: | ---: | ---: | ---: | ---: |
| intent (60 cards) | 42,133 B | 44,109 B | +1,976 B | 5,740 | 6,016 |
| slot (54 cards) | 80,049 B | 83,351 B | +3,302 B | 11,647 | 12,137 |

Per changed card, v1 → v2 bytes (words): `general_quirky` 849 → 1,594 (+107 w); `general_greet`
823 → 1,157 (+46 w); `qa_factoid` 664 → 1,038 (+49 w); `qa_definition` 689 → 1,008 (+43 w);
`general_joke` 685 → 889 (+31 w); `date` 3,201 → 3,828 (+90 w); `event_name` 2,566 → 2,987 (+62 w);
`relation` 2,104 → 2,580 (+70 w); `business_type` 1,620 → 2,095 (+64 w); `media_type` 2,008 → 2,448
(+63 w); `transport_type` 1,246 → 1,578 (+49 w); `order_type` 1,144 → 1,438 (+48 w); `time`
3,370 → 3,607 (+44 w).

Exposure per contact: Perception fuses `k = 8` intent cards, so its worst case is all five revised
cards in one packet, +1,976 B; the common case is `general_quirky` alone, +745 B. The Solver's
candidate-bound slot supply is capped at 28 values (16 per candidate), so its worst case is all
eight revised cards in one packet, +3,302 B. Token counts are deliberately not estimated here: the
owner rule is to measure on the flight tokenizer, which belongs to each cell's prompt-fit receipt
before contact, and this item carries zero tokenizer contacts.

## 8. Artifacts

Under `SPEECHRL_DATA_DIR`, namespace `prepared/SAEA-SLURP-SEMANTIC-AUTHORING-PREPARE-V2/`
(create-only):

| File | SHA-256 |
| --- | --- |
| `authored-intent-boundaries-v3.json` | `80c6eab120f620188cbae911017cfd74b210c5ca917a17752928a886baf1d22d` |
| `authored-slot-contracts-v2.json` | `fc34b243f2e48e4e0bc3fe10d328d25601b1f1fa7c190c049d696c3ca0db4dd2` |
| `CHANGES.json` | `48b3ab71706a820856117bcd5e01452ea248829c57f4aa75ca4d22b75c1aa63f` |
| `rendered-values-v1-vs-v2.diff` | `ed8fc19f9320240b2eafcac6a3c41bb63757cb6be666a87f04fae42e442570a4` |
| `author-semantic-store-revisions-v2.py` | `612c405b5bc76ebb84e98b3e02d4351d0dc292941e152a8e5c802732bcf769cc` |

`CHANGES.json` names the changed card ids, their per-card byte and word sizes, the v1 and v2
rendered-value hashes, the key-text hash and its unchanged flag, and the unified diff of every
changed rendered value; the diff file carries the same diff as text. The authoring script is stored
beside its outputs rather than in Git, as the A3 audit scripts were, and refuses to overwrite a
published byte.

In Git: the two registrations, this note, the release-pins document, the two held fragments
(`configs/baseline/slurp-native-dual-store-train-fold-a-intent-v2-v1.json`,
`…-slot-v2-v1.json`) and `tests/unit/test_slurp_semantic_store_revisions_v2.py`.

## 9. Decisions, deviations and open questions

1. **Key text left alone by choice.** Item E5b prefers value-field language so the sealed facet
   vectors stay valid. All new boundary language therefore lives in `confusable_exclusions` and
   `uncertainty_behavior`; no `activation_boundary` line was touched. Consequence: the Perception
   retrieval that selects the eight cards is unchanged, and the cell measures the effect of the card
   *content* only. If a later cell wants the boundary in the key, that is a separate registration
   plus a re-encoding contact for the facets it changes.
2. **`event_name` is in the revision set.** Item E5b lists date, time and the five widened types,
   but its emit-when-spoken clause names `event_name`'s two intents explicitly, and T5 shows it is
   omission-dominated (22 of 41). It is revised on the same pattern. If the coordinator wants the
   B4b surface to be exactly seven cards, drop it and rebuild; the change is one entry in the
   generator.
3. **Surface forms are the attested ones.** The illustrative strings "next friday" and "the third of
   may" are not attested in the construction pool, so the `date` cue uses attested forms of the same
   two classes instead (relative and absolute). Examples must come from the pool, never from an
   illustration.
4. **The registration schema cannot record the authoring method.** `core.semantic_knowledge_
   preparation` validates the registration against an exact key set, so "root-authored, zero
   contacts" is recorded in `CHANGES.json` (`derivation`, `contacts`) and in this note rather than
   inside the registration file. Both registrations are otherwise byte-equivalent to their v1
   predecessors except the source pin, the registration id and the output namespace.
5. **Uncertainty text is no longer shared by all 60 intent cards**, so the intent v3 source cannot
   be compiled by `saea-authored-intent-boundaries-factored-v1`, which requires one shared
   `uncertainty_behavior`. The factored store `intent-boundaries-factored-v1` is untouched and stays
   pinned to the v2 source; a factored twin of this revision would need the clause on all 60 rows,
   which would break the "every other card byte-identical" requirement. Open for the coordinator if
   a factored arm is wanted.
6. **The fragments are the anchor's held form.** They derive from the committed
   `slurp-native-dual-store-train-fold-a-held-v1.json` (the anchor minus the contact bindings) and
   differ from it only in `knowledge_stores`, `preparation_source_receipts`,
   `prospective_phase_supply`, the two speech-feature identity strings and `what_this_is`. They
   therefore carry no `native_contact_fit`, no `prepared_phase_supply` and an empty `scorers` list,
   exactly as the held precedent does.
7. **Speech-feature ids are now fragment-unique.** All 65 SLURP fragments share
   `saea-slurp-task-agent-v1:query-speech` / `saea-slurp-task-agent-v1`; these two fragments use
   `…:query-speech:intent-store-v2` / `…:intent-store-v2` and the slot twin. The pair rides the
   audited payload as ORG/CONTROL identity, resolves in no registry and is bound to no packet
   receipt, so the change is trace identity only.
8. **Not measured here.** Whether either revision helps is a question for cells B4a and B4b under
   their own preregistration, null margins and paired analysis. This item claims only that the
   stores are built, pinned, contained and byte-accounted.

## 10. Verification run

- `python scripts/checks/engineering_base_check.py` — PASS.
- `python -m pytest tests/unit/test_slurp_semantic_store_revisions_v2.py` — 16 passed.
- `python -m pytest tests/unit/test_semantic_knowledge_build.py tests/unit/test_semantic_knowledge_preparation.py tests/unit/test_slot_binding_view.py tests/unit/test_candidate_semantic_supply.py tests/unit/test_factored_intent_boundary_build.py` — passed.
- `ruff check` on the new test file — clean.
- Contacts this item: model 0, tokenizer 0, encoder 0, scorer 0, GPU 0, tool 0.
