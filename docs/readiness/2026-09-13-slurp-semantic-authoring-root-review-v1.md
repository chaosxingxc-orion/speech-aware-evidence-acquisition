# Root review of SLURP semantic authoring support

Status: registered support preparation complete; first root-authored intent source complete; runtime releases pending.

Root verified support.json SHA-256 1be15d89797e55bfb492df87cc994844bb8db69aab5ce8a70e0880f13e8dcdee and receipt.json SHA-256 7bc136f2ff956b1eb5dcb43add3674010a935d4d2b0d325820f2290338c38253. The governed A/B-excluded TRAIN pool remains exactly 9,354 utterances, 37,407 recordings, 60 intents and 54 entity types, with existing KB source identity 22f6092dfdb4a160376e529d8e59e9215bc7701e274620d35feb1c4d82f309e9. Intent support contains 474 utterances and 2,037 recordings. Slot support contains 803 deduplicated utterances and 3,162 recordings over 402 observed intent/type pairs. No neural, tokenizer, encoder, scorer or tool-backend contact was added.

Root read all 474 registered intent-support rows and authored 60 candidate-guidance values. Each value contains its activation boundary, a named neighboring intent and distinguishing evidence, uncertainty handling, limitations and exact support provenance. Paired distinctions cite support for both labels. The values guide candidate selection; they do not eliminate labels or turn frequent fields into mandatory slots.

The reviewed source demonstrates why semantic rules must preserve uncertainty. Cooking query and recipe support overlap; cooking_query has only three selected support rows. Coffee support crosses a device/ordering distinction. Lighting color support includes a brightness request. Several contact, takeaway and broad conversational examples overlap neighboring labels. One takeaway example has an unrelated entity annotation. These anomalies are limitations, not rules to memorize. Do not derive universal exclusions or copy inconsistent entity values.

Stable distinctions are mainly about the requested operation and its object: inspect versus create versus remove; a personal calendar versus public event discovery; selecting music versus changing playback mode; directions/timetable information versus ticket acquisition. Slot knowledge still requires a separate root review of semantic roles, mention boundaries, repeated values and missing evidence. An intent/type frequency catalog cannot substitute for that work.

Authored source (create-only):
/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/prepared/SAEA-SLURP-SEMANTIC-AUTHORING-PREPARE-V1/authored-intent-boundaries-v1.json

Source SHA-256: 040b8143072ccd660cd1659f5a0ddf71dec5a3f8f8ec6e98bda726a6b7db1a13.
A model-free builder compilation produced 60 values with semantic content SHA-256 2803be170657d6d1daf3c0f672e1e6fc2cd0c2e65af2548d559715da6072e41d. This compilation is not a runtime store release. The later shared preparation entry must validate all forbidden rosters and release bindings before consumption.

The construction roster identity f244b9760e9c9c21e04dcf335becb30cea95e66b7f66a8f60147bb94e5d83549 differs from the historical KB pool identity because the existing roster and KB builders use different identity conventions. Keep both named; never substitute one for the other.

Preparation code is fa9ba618; its root integration is a9d75eaa. The selected support bytes and historical experiment artifacts remain unchanged. No DEV/test content, results or error-derived rule was used to author these values.
