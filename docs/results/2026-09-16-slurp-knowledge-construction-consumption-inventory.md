# SLURP knowledge construction and consumption inventory

This is a bounded factual inventory at repository snapshot eb1a33df2402d743221bb3d291d6e50ad8db59fb. It describes the released intent-boundary and slot-contract stores, their registered selection paths, and the current frozen maximum-three typed-context configuration. It does not read evaluation references, recompute coverage, inspect the active flight, or propose a successor.

## Construction population and exclusions

The registered construction read used governed TRAIN only. It excluded an entire utterance when any recording belonged to TRAIN Fold A, TRAIN Fold B, or DEV-1000, and prohibited DEV/test content and results from authoring (docs/readiness/2026-09-13-slurp-semantic-authoring-registration-v1.json:2-7,28-40). The source pool contained 9,354 utterances, 37,407 recordings, all 60 intents, and all 54 entity types observed in that governed construction pool (:21-26). The count of 54 is construction-local and is not the authoritative global legal entity inventory. Intent support retained at most eight utterances per intent; slot support retained at most three utterances per observed intent/type pair and deduplicated utterances across pairs (:75-80).

The resulting reviewed supports contain:

- 60/60 intent labels, represented by 60 intent values supported by 474 utterances and 2,037 recordings (docs/readiness/2026-09-13-slurp-semantic-authoring-root-review-v1.md:5-7). This is complete label inventory coverage in the authored store; it is not a runtime retrieval-coverage claim.
- 54/54 entity types observed in the construction pool, represented by 54 slot values supported by 803 deduplicated utterances, 1,388 mentions, 3,162 recordings, and 402 observed intent/type bindings (docs/readiness/2026-09-13-slurp-slot-semantic-authoring-root-review-v1.md:5-7). The authoritative legacy task contract separately contains 55 legal entity types and 60 intents (DATA/coordination/slurp-review-measurement-v1/root-contract-projection-verification-v1.json:5-17). Root's catalog union check records 52 catalog types, with music_album catalog-only and game_type, sport_type, and transport_name slot-only. This inventory does not infer a global set from construction coverage. Of the 402 support pairs, 168 have fewer than three selected rows (:19-25). Absence of an intent/type binding is not registered as a prohibition.

The released intent source uses corrected construction split identity f76a7d00172a29452e791b0ec292c08492b9ae48e5eb28f72f58afd7f34cb1df and source SHA-256 1950c4a3a8bed73d0cf810c10a9f32d42b683b3d317cdc24634366faa0808fb1 (docs/readiness/2026-09-13-slurp-slot-semantic-authoring-root-review-v1.md:27-31). The slot source uses construction split identity 1253ec6ce2bd34a715a4838a8edf17d472aaa1a1c969217df5ebf44dc667ac27 and source SHA-256 34f6c3dc192eca4a30ef7208d10c1e2b797a0ae2ffe5122f16b376e10a30e4c5 (:5-7). The frozen configuration binds intent semantic snapshot hash 5520b8449b627530227563d1f8db71f8a391f20f7d0ff7d7bd439e28ec6e48fe and slot semantic snapshot hash 11c246e4b815a4f966e8cf8785f06b70515755eca71658862c6f98e9914044e6 (configs/baseline/slurp-native-typed-role-context-train-fold-a-v1.json:44-50,68-74).

## Registered key and value fields

The intent authored row has intent_id, one or more activation_boundary texts, structured confusable_exclusions containing a neighboring intent ID and distinction, uncertainty_behavior, limitations, and exact source support. The builder renders all of these fields into the model-facing value (src/speech_aware_evidence_acquisition/rails/semantic_knowledge_build.py:105-138). Its retrieval key is narrower: intent_id plus the activation-boundary texts only (:194-219). Therefore the sealed intent key measures similarity to the label and its activation description. Confusable distinctions, uncertainty, and limitations are value content and do not enter that key.

The slot authored row has slot_id; one or more intent bindings, each with intent_id and semantic_role; extraction_cues; admissible_formats; missing_behavior; ambiguity_behavior; limitations; and exact source support. The full rendered value includes each field (src/speech_aware_evidence_acquisition/rails/semantic_knowledge_build.py:141-172). The slot facet key contains the slot ID and all rendered intent/semantic-role bindings (:194-219), but the current candidate-conditioned route does not vector-retrieve those facets.

The slot values consequently include semantic meaning through intent-specific semantic roles, extraction guidance, surface/representation guidance, missing-evidence behavior, ambiguity guidance, and limitations. They do not contain a separate structured examples field, an enumerated exhaustive allowed-value set, or a structured neighboring-slot contrast list. admissible_formats is registered as guidance rather than a whitelist, and bindings are guidance rather than required fields (docs/readiness/2026-09-13-slurp-slot-semantic-authoring-root-review-v1.md:7,11-17). Intent values do contain explicit named neighboring-intent contrasts (docs/readiness/2026-09-13-slurp-semantic-authoring-root-review-v1.md:7-11). Neither builder derives mandatory fields or task targets (src/speech_aware_evidence_acquisition/rails/semantic_knowledge_build.py:257-274,393-410).

## Intent retrieval and what its key measures

The frozen route compares sealed full-utterance speech-segment query vectors, SHA-256 e7a5b2264dc61fcab3c63d50fb645d4629d3f0a99f83ad5fbe323c73884e5f0b, with sealed text vectors for the 60 compact intent keys, SHA-256 76e8d16a067ebfc5d67a4ecef2966636310815b950a7d9790ec7c0136f01ecd2 (configs/baseline/slurp-native-typed-role-context-train-fold-a-v1.json:13-18,28-33). Ranking uses cosine only: w_cos=1, w_prior=0, and w_agree=0 (:35-41). The route ranks k=8, then selects at most one associated value for each of the first eight facets and at most eight values total (:20-27). expose_facets=false means the compact keys themselves are not rendered to the model (:8-13); the selected full intent values are rendered.

The key representation therefore measures sealed speech-query proximity to compact authored label-plus-activation text. It does not directly measure proximity to the full intent card, confusable exclusions, slot contracts, transcript text, task output, or evaluation result. Segment rows are source-bound to their speech packet before selection, and the runtime loads the pinned query and facet vectors rather than contacting an encoder (src/speech_aware_evidence_acquisition/rails/phase_supply.py:253-292,900-929).

The completed, pre-existing breadth audit is reused rather than recomputed. It binds report SHA-256 caff838a3898e74006d2e5c6643b87b84dd89aa6868f42b6b332f5e1e68bc944 and a 1,080-row cohort (docs/readiness/2026-09-15-root-slurp-supply-breadth-analysis-v1.md:69-74). Its reported own-intent-card availability is 947/1,080 at breadth 8 and 1,040/1,080 at breadth 32; the breadth-32 knowledge bytes are 3.97 times breadth 8 (:13-26). These are supplied-card counts, not generated-candidate counts.

## Candidate-to-slot selection

The candidate-to-slot index is rebuilt from the released authored slot source. The implementation requires the source builder and split identity to match the snapshot, rebuilds the entire slot snapshot byte-for-byte, rejects candidate IDs outside the authoritative 60-label inventory, and maps every authored intent_bindings[].intent_id to slot-contract:<slot_id> (src/speech_aware_evidence_acquisition/rails/candidate_semantic_supply.py:328-403). It does not infer a relation from a slot title, value ID, frequency, or free text. After a slot value is selected, the renderer supplies the entire immutable authored slot card, including all of that slot's intent/semantic-role bindings. It does not project the card down to only the candidate binding that selected it (src/speech_aware_evidence_acquisition/rails/semantic_knowledge_build.py:141-172,212-219; src/speech_aware_evidence_acquisition/rails/knowledge_provider.py:1322-1405).

For the current Solver route, the provider parses the source-bound Perception state under the declared maximum-three projection and preserves model candidate order (src/speech_aware_evidence_acquisition/rails/knowledge_provider.py:1670-1707). Value IDs are sorted inside each candidate, then selected round-robin in candidate order, with each shared slot card selected once. The independent bounds are 16 values per candidate and 28 total (:1322-1405; configs/baseline/slurp-native-typed-role-context-train-fold-a-v1.json:54-66). Selection is completed before already-visible cards are removed, so visibility does not page into additional values (src/speech_aware_evidence_acquisition/rails/candidate_semantic_supply.py:642-720).

Reviewer on-demand lookup uses the same explicit released relations. At store binding time, the runtime rebuilds an intent index mapping each legal intent ID to its same-ID intent card and a slot index from the authored slot intent bindings (src/speech_aware_evidence_acquisition/rails/released_target_index.py:41-108). The current Reviewer tool is authorized for both stores, up to three candidate IDs, 16 values per candidate, and 28 values total (configs/baseline/slurp-native-typed-role-context-train-fold-a-v1.json:204-222). This released index is the mapping authority; the null task_target fields in the historical snapshots are not guessed or rewritten.

## Content visible to each current role

Every role contact receives the task adapter's system and user messages. The system includes the task contract; the user content includes the original speech packet and every value currently visible in QueryState (src/speech_aware_evidence_acquisition/rails/runner.py:1212-1278,1688-1694). Named-store values are prefixed with store ID and store role (src/speech_aware_evidence_acquisition/rails/knowledge_stores.py:207-220). The typed role-context compiler filters only role-history states. It does not filter accumulated QueryState knowledge: every later role receives all intent and slot values already present in QueryState through the same base-message renderer (src/speech_aware_evidence_acquisition/rails/runner.py:1212-1278,1888-1914).

- **First Perception:** original speech, the task contract with its authoritative 60-intent and 55-entity-type legal inventory, plus up to eight full intent-boundary values selected by the sealed speech/text retrieval. It sees no old candidate or draft state. The compact retrieval facets are hidden.
- **Solver:** the same accumulated base evidence plus slot-contract values mapped from the ordered maximum-three Perception candidates. Its role-history view includes the latest candidate hypotheses labeled unverified-model-hypotheses and, on a revision, the latest draft and current structured review (src/speech_aware_evidence_acquisition/rails/role_context.py:537-586).
- **Reviewer:** the accumulated intent and slot values, the latest unverified candidate hypotheses, and the current Solver draft. It does not inherit earlier Reviewer opinion (src/speech_aware_evidence_acquisition/rails/role_context.py:537-568,641-645). It may call the task-contract tool or source-bound target lookup. A returned native source/result pair and any newly acquired values remain explicitly bound and visible through the normal query-state/tool custody path.
- **Planner:** the accumulated base evidence, compact current-draft identity/status, and the current structured review plus relevant Reviewer tool source/result pairs after the latest Solver. It does not receive candidate prose (src/speech_aware_evidence_acquisition/rails/role_context.py:489-515,556-586,631-640). It selects the registered ACCEPT or REVISE route; it does not author the delivered task answer.

The compiler labels candidate interpretations and review declarations as unverified. Citation availability records only evidence IDs visible at the destination; it does not certify entailment or semantic truth (src/speech_aware_evidence_acquisition/rails/role_context.py:511-554,660-673).

## Existing broad/factored assets and closed status

The existing broad/factored package is a completed, closed flight, not unused preparation. Its source-bound configuration and protocol already register the factored intent store, the same sealed 60 facet vectors and speech query vectors, k=60, m=60, c=2, top_l=61, and the unchanged maximum-three candidate-conditioned slot route (configs/baseline/slurp-native-broad-factored-train-fold-a-v1.json:5-76). The factored preparation is pinned to authored source SHA-256 4f0906e2f6237e525ce4e79c6ab07348842091edde9ea21200a335030ac1a020, the same corrected intent construction split, and the same forbidden rosters (docs/readiness/2026-09-15-slurp-factored-intent-preparation-v1.json:1-42). These artifacts preserve the complete source/config path.

The authoritative verdict is NOT_ADVANCED_FULL_TASK_GAIN_GATE_FAILED; the completed 1,080-row run reported generated candidate coverage 947/1,080, official pooled SLU 47.6347%, and 841 correct final intents (docs/results/2026-09-16-slurp-broad-factored-train-a.md:1-23,64-77). It changed intent organization and supply together, so its protocol does not isolate breadth from factoring (:58-62). This closed status is recorded here only to prevent the registered broad/factored package from being described as untested.

## Observable metadata gaps

The released metadata does not expose a calibrated score or confidence for authored rules, an exhaustive allowed-value domain for slots, a structured examples collection in runtime cards, a structured neighboring-slot contrast graph, or a mandatory-slot schema. The construction store's 54 types also do not by themselves explain the authoritative contract's 55th legal type. It also does not establish that an absent intent/type binding is invalid.

The retrieval audit records supplied-card availability. It does not by itself show which specific card text a model used, whether a distinction resolved an ambiguity, or whether a citation entailed the final answer. The current receipts can show selected values, role-visible evidence IDs, tool calls, and revisions; semantic use remains unobserved unless a separate released trace-level analysis defines it.

The construction metadata reports 402 observed intent/type bindings but does not publish, in the repository documents inspected here, a complete aggregate matrix of binding counts by each of the 60 intents and 54 slot types. The exact relation exists in the pinned authored source and released index; only the aggregate count is visible in Git metadata.

## Source pins

| Source | SHA-256 |
| --- | --- |
| Current typed-context baseline config | d30323c5a8ac9b7ef913ac52786ac5b04ea7c956c23879deaed3ded42e684e35 |
| Existing broad/factored baseline config | 95722e69f49ab517d4e8119b9fabb9f3cd463ae1dce87c9cc085d68c7f3f5c7c |
| Semantic authoring registration | cf52fe8267473d57f119978c59c846f823a4f771fe459832279f653cdc6e32cc |
| Intent authoring root review | ac419db667d6a3b655050f24cff8dcfe2b1b58491cda4c06783b53ba95b024ef |
| Slot authoring root review | 055e11876ec54fb89fcd98133ad423e3bd88ee9d1fd19f20680bf763e1855808 |
| Released store pins document | ad38deb34c4a198f0b3f4e23f29069688fcdbbffec38460bc3658d6c8b6d0ed2 |
| Root legacy contract projection verification under SPEECHRL_DATA_DIR | d1dbe4915d1cfcdb7035089487bc60263014fd4d5d544f576d1f610442a6f899 |
| Completed breadth analysis document | 151ffe54954c93ffbd4cbb64f8b3265a9881158665aae8ca80ba8b667df11f7d |
| Breadth audit final-v2 report under SPEECHRL_DATA_DIR | caff838a3898e74006d2e5c6643b87b84dd89aa6868f42b6b332f5e1e68bc944 |
| Closed broad/factored verdict | 4db21819b80562e702404b64327e80c5d7135499b7a0e7b4484d4389e7dbfe44 |
| Semantic builder implementation | f76f185c7f5a35497fae90dd59d401c233cd4bcd0c6c486e2bae5bcb9833e668 |
| Candidate supply implementation | 2c84f6b1fc1e242071aefdedafa267553f39fb4aa6412d83cb6ff5a3905e9433 |
| Candidate provider implementation | 365d74ffdcb55613a6501c8f6eeed749a29e75692ffdf557f079f08079a05614 |
| Released target-index implementation | 9765c9c5497455d6d24188ca2199ae211fbeb600667c342e05f4d77034d55639 |
| Typed role-context implementation | a45634e50c3f52ed3fdfb305ef0b2de34c8775e4784a59c4ad5d101b9a2f0cc5 |
| Shared runner implementation | 7fd5a0e392ea24135411508d933dbee15df3acd02197a4680104d59a31188570 |
