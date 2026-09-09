# KC-S1b same-config replication preparation

Status: **HELD; preparation only.** This note prepares the full frozen DEV-1000 same-config
replication of KC-S1b under `SAEA-SLURP-KC-S1B-SAME-CONFIG-REPLICATE-V1` and its separate
tokenizer-only full-roster fit under `SAEA-SLURP-KC-S1B-SAME-CONFIG-REPLICATE-FIT-V1`.

The experiment fragment keeps the four source fragments and the request semantics unchanged:

| component | binding |
|---|---|
| model | `q4km-mmproj-free-speech-native-np4-base-speech-query-prefix-max64` |
| dataset | `slurp-speech-native-dev1000`, frozen DEV-1000 roster |
| baseline | `slurp-phase-slots-given-intent-schema-v1`, including the original example-bearing schema |
| experiment semantics | sealed predecessor state, one slot contact per row, same prompt order, geometry and decoding |

The predecessor source is pinned to `runs/SAEA-SLURP-KC-S1B-SLOTS-SCHEMA-DEV1000-V1/attempt-20260906T025102Z-af6b04/SAEA-SLURP-KC-S1B-SLOTS-SCHEMA-DEV1000-V1.run-manifest.json`, whose full SHA-256 is `088c9307a39f38db124a5204793806e9a8589d942259b15e7826ad2685fe8d08`. The predecessor binding and source bytes remain unchanged.

The fit proposal is 3,001 tokenizer contacts: one `/props` call, 1,000 `/apply-template`
calls, and two `/tokenize` calls for each of the 1,000 actual requests. It is not derived from
the generation proposal of 1,050 calls. The shared fitter must cover every unique DEV-1000 row,
persist only the hashable fit artifact and counts, and generate no model output.

The following prerequisites remain unresolved and are owned by root:

1. Register the generation exposure row and the fit exposure row before opening either service
   session; keep paid API spend at zero and leave both run IDs unconsumed.
2. Bind the owner-approved runtime-version bridge, including the pinned llama.cpp build,
   runtime receipt and per-file model identities. This preparation records no invented hashes.
3. Run the shared full-roster fit with the 3,001 contact cap and bind its artifact to the same
   composed configuration, split identity, request boundary and runtime identity.
4. Pass the contact-free wire check and the required four-row smoke, then review fit margin and
   source/request identity before any generation contact.
5. Obtain owner GO and record the final exposure/readiness state. This note does not mark the cell
   ready.

The current `core.flight` CLI chooses one experiment fragment globally for a mode. A mixed
campaign containing both the fit cell and the generation cell could therefore route the fit
through the generation worker. The fit must be invoked separately while reusing the immutable
four-fragment identity, or root must document an owner-approved equivalent arrangement. This
preparation adds no bypass or new harness.

No model, tokenizer, encoder, network or scorer contact was made while preparing this note.
