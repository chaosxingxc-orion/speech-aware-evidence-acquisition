# SLURP task-agent model-free preparation

This registration admits only deterministic preparation and synthetic full-path verification for the three held SLURP task-agent arms at study commit `dc864f0bfc3a8adeba653dc77674f5fc5e6b119c`.

The preparation uses `FlightRuntime.prepare_phase_recall` for phase `solve` in the knowledge and intent-slot-frame arms. It writes one source-bound prepared recall artifact per arm under `SPEECHRL_DATA_DIR/prepared/`. The direct arm has no phase supply and needs no recall artifact. After the prepared artifacts are hash-bound into successor config bytes, `FlightRuntime.wire_check(seal_and_score=False)` drives every DEV-1000 request through the shared controller, OpenJiuwen executor, frozen-core client, and fake transport. Request observers may compare content-free request structure, selected value identifiers and ordering, and the fixed phase-tool result contract.

No model service, tokenizer, encoder, scorer, reference, or outcome is contacted. The synthetic response is not a scientific result. Generation, live fitting, scientific admission, and result reading remain held for root review. Existing knowledge snapshots, sealed vector files, promoted speech packets, and experiment identities remain immutable.
