# Root review of SLURP slot semantic support

Status: semantic source authoring is complete; registered shared preparation is next. No runtime benefit is claimed.

Root read all 803 selected utterances in the governed, A/B-excluded TRAIN support, including their intents, text, fillers and token-span references. There are 1,388 entity mentions, 54 types, 402 selected intent/type pairs and 3,162 recording IDs. The model-free review material preserves the rows; its SHA-256 is 858764363353b46d2ac24608d5697c00be27129cc9eb4ea681008e1a1576691d.

The authored source is prepared/SAEA-SLURP-SEMANTIC-AUTHORING-PREPARE-V1/authored-slot-contracts-v1.json under SPEECHRL_DATA_DIR, SHA-256 34f6c3dc192eca4a30ef7208d10c1e2b797a0ae2ffe5122f16b376e10a30e4c5. Its selected construction identity is 1253ec6ce2bd34a715a4838a8edf17d472aaa1a1c969217df5ebf44dc667ac27. One value per entity type describes observed intent bindings, extraction cues, admissible surface forms, missing-evidence behavior, ambiguity handling, limitations and exact permitted support. The support union equals all 3,162 permitted recording IDs. Bindings index guidance, never required fields or an exhaustive legal-type whitelist.

## Semantic decisions

Distinguish role from lexical identity: merchant from business category, application from content/equipment, artist/author from title, and contact-field name from its value. Do not infer missing names, addresses, domains, units, dates or preferences.

Preserve relations and mention scope. A target level introduced by to differs from a relative change introduced by by. Routes and time ranges can contain separate endpoints. Do not collapse named people, currencies or other distinct mentions solely because their types match. Respect negation and explicit corrections.

Interpret temporal expressions and titles contextually. A month or year inside a title need not be a date. A duration differs from a calendar anchor, and a part of day can be separately stated from a clock reading. Preserve supported spoken expressions rather than inventing normalized calendar values.

The cards explain extraction and competing interpretations without placing a TRAIN corpus into runtime memory. Candidate-specific consumption and a deterministic cardinality limit must be registered before the knowledge-effectiveness comparison.

## Source limitations

Annotations are not a flawless specification. Selected examples include an unrelated business filler in a takeaway utterance, a non-temporal word labeled time, music titles labeled movie_name, inconsistent person/artist assignments, and omitted or differently typed temporal modifiers. Root recorded these as limitations and did not author exception lookups reproducing them.

The formatted review's zero filler/token-span mismatch result checks annotation self-consistency, not agreement between the text field and all annotation tokens. It does not disprove the semantic/text anomalies above.

There are 168 selected support pairs with fewer than three rows. Rare types such as game_type, ingredient and audiobook_author provide little evidence for broad rules. Do not infer absent types are forbidden, frequent types are mandatory, or confidence follows candidate count.

## Intent identity correction

Keep the original 60 intent rows unchanged. authored-intent-boundaries-v2.json corrects only their selected construction identity to f76a7d00172a29452e791b0ec292c08492b9ae48e5eb28f72f58afd7f34cb1df; its file SHA-256 is 1950c4a3a8bed73d0cf810c10a9f32d42b683b3d317cdc24634366faa0808fb1. Preserve the original source and review receipt. This lets the existing shared identity contract remain intact.

No DEV/test content or evaluation feedback was used to write these cards. Shared preparation independently verifies all registered exclusions before release. All new model, tokenizer, encoder, backend, scorer and GPU experiment contacts are zero.
