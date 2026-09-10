# Exact-window feature preparation provenance

Status: shared model-free validation implemented; no encoder run or serving
qualification is claimed.

The historical Audio2Tool preprocessing report records only aggregate contact
and failure counts. It does not enumerate each audio SHA-256, legacy FNV cache
key, and request identity, so it cannot prove exact-window encoding completion.

The shared encoding handoff schema is
saea-window-feature-encoding-record-v1. It binds the encoding run, attempt,
preprocess session, runtime receipt in both file and canonical-document forms,
session receipt, exact inventory, encoder identity, sealed client trace and
cost, and one outcome for every unique audio input. Fresh successful inputs
carry their current contact ID. Failed inputs may retain an attempted request
ID for diagnostics without calling it a charged contact. Warm reuse has zero
current contact ID and must cite the inherited contact ID plus a prior final
provenance receipt under the same encoder identity.

The final source-bound builder verifies the preprocess runtime and session,
the normal root-owned stop receipt, an independent current observation that
the stopped PID is gone, the prepared feature-cache audit, the exact inventory
digest, and complete unique-audio SHA/FNV coverage. Forced stops, defunct or
reused live PIDs, failed inputs, duplicate or incomplete coverage, and
unverified warm reuse are refused. Inventory batch names may belong to
generation runs and need not match the encoder run.

The former driver stop-chain helper remains as a thin compatibility wrapper
over the public shared authority. Legacy and current stop-receipt key sets are
accepted for chain validation; final provenance does not trust a declared
process-state field.

This code reads and validates existing local artifacts only. The standard
adapter still must produce the encoding record, root must stop the shared
service after worker detachment, the cache audit must be built from the
completed cache, and the resulting provenance must pass owner review before
any generation use. This work starts no service, performs no encoding, and
contacts no model, tokenizer, scorer, or endpoint.
