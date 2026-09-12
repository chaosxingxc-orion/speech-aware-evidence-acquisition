# SLURP training-cycle knowledge preparation v1

## Scope

Build one model-free successor of the frozen compact SLURP K5 knowledge snapshot for the disjoint TRAIN selection cohorts. Exclude every TRAIN utterance represented by either cohort before knowledge construction. Preserve every existing snapshot and vector artifact.

This preparation authorizes no Qwen, Whisper, retrieval encoder, tokenizer, scorer, network, GPU, or task-result contact. It does not authorize A/B answering, reward reading, proposal, selection, update, or evaluation.

## Frozen inputs

- Builder: `scripts/build_knowledge_snapshot.py`, SHA-256 `6b4685df51c51123eaed3d121a6d7a409c9adace9d285c55dd2eab85372d4423`.
- Shared builder implementation: `src/speech_aware_evidence_acquisition/rails/knowledge_build.py`, SHA-256 `672f4b9312d94dcb487b1712cb2eb8bcf9d342920a6db6ec8f217af06d6ba66b`.
- Fold A roster: `docs/receipts/rosters/slurp-evo-fold-a-v2.json`, roster `SLURP-EVO-FOLD-A-V2`, split identity `61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6`, file SHA-256 `1fe7908c31396774d7535fdf37bd791762215c324999d66ed7beb9e7b2f9033d`, 1,080 rows.
- Fold B roster: `docs/receipts/rosters/slurp-evo-fold-b-v2.json`, roster `SLURP-EVO-FOLD-B-V2`, split identity `4407794c4a5d2e8883d93fdf242deb33c0987405d62e05a7d8416f5251a3484a`, file SHA-256 `47b89b9e33b1aed553ad94a1819acba6ac8837130ca546c33219d91a1ab944a8`, 1,080 rows.
- Original compact K5 snapshot: `knowledge/slurp/saea-kb-distmodel-v1/size-full-content-slot-fillers-intent-slot-frame/snapshot.json`, SHA-256 `609854e4211891614b621e6431ccf23706c2aa3a3bc9133dae9d9765628c88b8`. It remains immutable.
- Full TRAIN source identity before exclusions: `6a6677e97a64063b8672b2d175bd6378bcf9b644346fa2d249cc2d80343b252c`.

## Frozen construction settings

Use builder policy `saea-kb-distmodel-v1`, seed `20260823`, datastore size `full`, dimensions `content`, view `slot-fillers`, value format `intent-slot-frame`, and tier suffix `tfrl-folds-v1`. Pass both roster receipt paths through the existing `--exclude-rosters` interface. That interface removes an entire governed TRAIN utterance row when any of its recording IDs occurs in an excluded roster.

Expected create-only successor paths:

- `$SPEECHRL_DATA_DIR/knowledge/slurp/saea-kb-distmodel-v1/size-full-content-slot-fillers-intent-slot-frame-tfrl-folds-v1/snapshot.json`
- `docs/receipts/knowledge/slurp-kb-size-full-content-slot-fillers-intent-slot-frame-tfrl-folds-v1.json`

## Mechanical acceptance

Before any later recall preparation:

1. Recompute both roster file hashes and counts.
2. Verify the successor snapshot and receipt hashes agree.
3. Verify the receipt pins both roster identities, hashes, and counts.
4. Verify no fold-A or fold-B sample ID occurs in the successor snapshot, any facet source binding, or any value source binding.
5. Verify the successor retains the declared builder policy, seed, full size, content dimension, slot-fillers view, and intent-slot-frame value format.
6. Record aggregate source, facet, value, and byte counts without printing knowledge text or value payloads.

The existing full facet-vector artifact is a safe runtime superset because recall asks it only for facet IDs present in the pinned successor snapshot. No shared API currently creates a cohort-filtered vector derivative. This preparation therefore creates no private vector pipeline and makes no encoder contact. A/B speech-query embeddings are absent and remain a separately registered future preparation. The A/B identities are historical and must inherit their existing ledger rows, including V2 packet preparation, intent flights, fold-A and fold-B flights, prompt fit, and smoke.

## Completed result

The registered model-free build completed with zero contacts.

- Successor snapshot content SHA-256: `9c64e8ec48a0fce4f172bd190932f99c98c7efa18bbfb14526d54c62fdf7032b`.
- Successor snapshot file SHA-256: `f2785aa3521b08e874d4075154e65cc639284497afc789a3654c2c70a65405ef`.
- Snapshot size: 15,364,578 bytes.
- Build receipt file SHA-256: `5db718d38426e5e6d2311efbed0c4faf36bf30473c8d00b14e06618257889766`.
- Build receipt size: 3,980 bytes.
- Source roster: 37,407 unique recording IDs with identity `22f6092dfdb4a160376e529d8e59e9215bc7701e274620d35feb1c4d82f309e9`.
- Compact snapshot: 9,354 facets and 9,354 values.
- Fold-A overlap: zero in snapshot, facet sources, and value sources.
- Fold-B overlap: zero in snapshot, facet sources, and value sources.
- Coverage reported by the unchanged builder: intent 1.0, entity type 1.0, long-tail intent 1.0, and intent-distribution KL 0.0.

Mechanical verification streamed only identifiers and structural metadata from the snapshot. It did not print knowledge values, transcripts, gold labels, or task results.

Root reverified the final receipt, builder source hashes, both roster bindings and all three source-membership layers before integration. The earlier draft receipt hash in this mutable note was corrected to the final receipt. Coverage is relative to the remaining construction pool, not a task-quality result. These historical A/B cohorts remain discovery/construction data; prospective update-versus-selection roles must be explicitly bound before any neural run.
