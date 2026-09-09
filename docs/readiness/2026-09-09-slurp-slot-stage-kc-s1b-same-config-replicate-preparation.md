# KC-S1b same-config replication preparation

Status: **HELD; preparation only.** This note prepares the full frozen DEV-1000 same-config
replication of KC-S1b under `SAEA-SLURP-KC-S1B-SAME-CONFIG-REPLICATE-V1` and its separate
tokenizer-only full-roster fit under `SAEA-SLURP-KC-S1B-SAME-CONFIG-REPLICATE-FIT-V1`.

The model, dataset and baseline fragments, plus the model-visible request semantics, are expected
to remain unchanged. The experiment fragment changes its identity and preparation metadata, so root
must complete the whole-roster request comparison before treating the replica as same-config:

| component | binding |
|---|---|
| model | `q4km-mmproj-free-speech-native-np4-base-speech-query-prefix-max64` |
| dataset | `slurp-speech-native-dev1000`, frozen DEV-1000 roster |
| baseline | `slurp-phase-slots-given-intent-schema-v1`, including the original example-bearing schema |
| experiment semantics | original example-bearing schema, closed-list-direct runtime predecessor state, one slot contact per row, same prompt order, geometry and decoding |

The replication comparator is pinned to `runs/SAEA-SLURP-KC-S1B-SLOTS-SCHEMA-DEV1000-V1/attempt-20260906T025102Z-af6b04/SAEA-SLURP-KC-S1B-SLOTS-SCHEMA-DEV1000-V1.run-manifest.json`, whose full SHA-256 is `088c9307a39f38db124a5204793806e9a8589d942259b15e7826ad2685fe8d08`. It is not runtime predecessor state. Runtime state remains bound by the unchanged baseline `phase_material.slots.predecessor_source` to `SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1`, manifest SHA-256 `f908ff4c7b0267322b34c7bf2ca9ad29d6db97ee8bb3cf18bf8824a057ebc94c`.

The fit proposal is 3,001 tokenizer contacts: one `/props` call, 1,000 `/apply-template`
calls, and two `/tokenize` calls for each of the 1,000 actual requests. It is not derived from
the generation proposal of 1,050 calls. The shared fitter must cover every unique DEV-1000 row,
persist only the hashable fit artifact and counts, and generate no model output.

The following prerequisites remain unresolved and are owned by root:

1. Register the fit exposure and structured plan before service access. Register generation
   after binding the successful fit, so its protocol hash describes the final configuration.
   Keep paid API spend at zero; each run remains unconsumed until its own registered contact.
2. Bind the owner-approved runtime-version bridge, including the pinned llama.cpp build,
   runtime receipt and per-file model identities. This preparation records no invented hashes.
3. Run the shared full-roster fit with the 3,001 contact cap and bind its artifact to the same
   composed configuration, split identity, request boundary and runtime identity.
4. Pass the contact-free wire proof, review fit margin and complete the source/request identity
   comparison before any generation contact. No new real-model smoke is authorized here; use the
   inherited failure and one-recovery procedure if generation is later released.
5. Record the final exposure/readiness state. This note does not mark either cell ready.

The same experiment fragment now carries two held cells. The fit cell allows only `check`,
`wire-check` and `prompt-fit`; the generation cell allows `check`, `wire-check`, `prepare-supply`,
`worker` and `campaign`. The generation campaign must hold automatically until the fit artifact is
verified. Both cells use identical model, dataset and baseline fragment names; their run IDs and
attempt registrations remain separate.

No model, tokenizer, encoder, network or scorer contact was made while preparing this note.

Update: complete-roster wire and payload parity passed; see the successor registration in
2026-09-09-kc-s1b-replica-registration/. Real capacity and generation remain unexecuted.
