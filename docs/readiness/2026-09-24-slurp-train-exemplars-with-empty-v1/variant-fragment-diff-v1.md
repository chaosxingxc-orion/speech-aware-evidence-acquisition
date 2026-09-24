# Config fragment diff for an empty-contract construction-variant cell

Date: 2026-09-24. A DOCUMENT, not a config: nothing below is committed as a fragment, no cell is
registered, no run id is reserved and no flight is queued. It states exactly what a variant cell
would have to change, and what it must not.

Base fragment: `configs/baseline/slurp-native-default-plan-lock-baseline-v1.json` (the locked
SLURP v2.0 plan, arm `speech-feature-query-native-tools`, policy
`phase-native-candidates-review-revise-v1`). Release registered in `README.md` beside this file.

## 1. The decision: re-pin the existing block, do not add a second store

`rails.knowledge_stores.load_knowledge_store_binding` refuses a store whose `release.store_id`
differs from its `knowledge_stores` key, or whose `release.store_role` differs from the block's
`store_role`. `rails.knowledge_index.EXEMPLAR_EVIDENCE_PREFIX` is the literal
`train-exemplars::value:`, and `rails.knowledge_index.EXEMPLAR_STORE_ROLE` is `train-exemplars`;
every exemplar evidence id, every index alias and every downstream receipt carries that prefix.

The released store therefore keeps `store_id` and `store_role` = `train-exemplars`, and the
variant cell **re-points the existing `knowledge_stores["train-exemplars"]` block at the new
namespace**. A second block under a distinct id would rewrite every evidence id and make the cell
a wiring change rather than a one-factor construction read -- and `_compose_supplies` would then
deliver twenty exemplars from each store instead of twenty in total.

## 2. The diff -- four scalar leaves

```diff
   "knowledge_stores": {
     "train-exemplars": {
       "release": {
-        "relpath": "knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars/release.json",
-        "sha256": "171aa4a82c2b15fff2c72e907ea80298be8d72309cca0d7367eb50debb042129"
+        "relpath": "knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars-empty-contract-v1/release.json",
+        "sha256": "4aa2c6dce28395efae5662aea2d4f755a01fdc9ab81ab0c6ad9844f4eeb71c2d"
       },
       "snapshot": {
-        "relpath": "knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars/snapshot.json",
-        "sha256": "4c498dc0282055b9fe036ed7e950af519bd48b5f26e76876d0250727196a72e9"
+        "relpath": "knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars-empty-contract-v1/snapshot.json",
+        "sha256": "e39985250bbd32ae0ac80ef234b8d0357943c4a68ac4e73b680ee4be4f48dbc6"
       },
       "store_role": "train-exemplars",
       "phase_supply": { "solver": { ... unchanged ... } }
     }
   }
```

and the matching receipt row:

```diff
   "preparation_source_receipts": [
     ...
-    { "relpath": "docs/receipts/knowledge/slurp-kb-size-pool-annotated-exemplars.json",
-      "root": "repository",
-      "sha256": "48d0f34cf536ebf9806d55b5dcced1b607080bec3c68ca7dea27cdb01478cc72" }
+    { "relpath": "docs/receipts/knowledge/slurp-kb-size-pool-annotated-exemplars-empty-contract-v1.json",
+      "root": "repository",
+      "sha256": "df28a3cea60cee6ca3b57d12aa0f58f16e6592bb639f444344b6ea54ff8194bf" }
   ]
```

`snapshot.sha256` is the snapshot's **content hash** (`KnowledgeSnapshot.content_hash()`), which is
what the loader compares and what `release.json` repeats in its own `snapshot_sha256` field -- not
the file-byte hash. The file-byte hash `53135ef430c1ba56...` is recorded in the pins file for
integrity only and must not be pasted into a fragment.

## 3. What must NOT move

| Leaf | Value | Why it is frozen |
| --- | --- | --- |
| `knowledge_stores["train-exemplars"].store_role` | `train-exemplars` | release identity and every `train-exemplars::value:` evidence id |
| `phase_supply.solver.facet_source` | `vectors/slurp-kus3/facet-vectors.jsonl`, sha256 `5dfe75231c12f262...` | the sealed KEY side; this store's facet ids and representations are the parent's, so it binds unchanged and no encoder is contacted |
| `phase_supply.solver.query_source` | `vectors/slurp-exemplars-pool/query-vectors-speech-content-v1.jsonl` (or the roster's own sealed speech query file) | the query side is sealed speech; the release touches neither |
| `phase_supply.solver.k`, `fuse_coverage`, `fuse_policy`, `rank_policy`, `rank_weights`, `tau`, `dimensions`, `expose_facets`, `provider` | unchanged | twenty in, twenty out; a changed retrieval geometry would confound the rendering read |
| `policy`, `native_episode`, `phase_material`, `phase_tools`, every instruction template | unchanged | the Solver's instruction bytes must stay byte-identical to the anchor's |
| `knowledge_stores["slot-contracts"]` | unchanged | M4b is a separate admitted module |
| serving geometry, roster, split, scorers | unchanged | one factor at a time |

## 4. What the cell still owes beside the diff

These are cell-registration duties, listed so the diff is not mistaken for a complete cell. None
of them was performed here.

1. **Its own `native_contact_fit` run and attempt identity**, at the ceiling the roster resizes.
2. **Its own `prepared_phase_supply` pin.** The base pins
   `prepared/SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1/phase-supply-v1.json` (sha256
   `50da0c7bdaa756fb...`). A prepared supply's artifact identity binds the store snapshot it was
   prepared from, so it **must be regenerated** against the new snapshot; re-using the base pin
   will be refused at payload binding.
3. **Its own speech-feature identity ids** (provenance only; absent from every rendered byte).
4. **A `what_the_train_exemplars_store_is` note** rewritten to say `annotated-exemplars-empty-
   contract` and to state the empty form, so the fragment's own prose does not describe the parent
   view.
5. **A twin.** The IDX reading of 2026-09-21 separated form loss from content: a rendering change
   deserves a form twin, not only an arm.
6. **A preregistration with margins.** The SLURP own null is `h_SLU` 1.2485 / `h_intent` 1.0 on
   the locked plan; a rendering variant is a candidate for a NEUTRAL-by-width read and the bar
   must be set before the flight, not after.
7. **A roster decision.** On TRAIN Fold A the store is legal as released (Fold A is excluded from
   the pool). On a **construction** roster such as R01/R01C the BUILD/USE disjointness rule in
   `rails.runner.run_speech_native_agent_loop` applies, and this release does **not** clear it --
   an `-empty-contract` sibling of `size-pool-annotated-exemplars-minus-r01` would have to be
   built first (same builder, one extra roster in `EXCLUDE_ROSTER_RELPATHS`).

## 5. What the cell would be testing

Whether showing the Solver the **correct empty answer** in its own contract bytes moves the
ENTITY-FP-ONLY mass (131 rows / +4.76 pp pooled official SLU on TRAIN Fold A; 108 rows / +3.47 pp
on DEV-2000-ADDED), without harming the entity-bearing rows whose 6,405 exemplar lines are byte
unchanged. The guard that matters is the other direction: an exemplar supply that makes empty
answers cheaper can suppress genuine entities, so the read must carry ENTITY-FN-ONLY beside
ENTITY-FP-ONLY and the per-stratum table the owner's reporting rule requires.
