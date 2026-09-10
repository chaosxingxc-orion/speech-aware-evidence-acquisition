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
cost, one outcome for every unique audio input, and exact descriptors for every
validated feature-cache chunk. Fresh successful inputs carry their current
contact ID. Failed operations use the separate
saea-window-feature-encoding-partial-v1 diagnostic schema; attempted request
IDs in that record are not charged contacts and cannot be consumed as final
evidence. Warm reuse has zero current contact ID and must cite the inherited
contact ID plus a prior final provenance receipt under the same encoder
identity.

The final source-bound builder verifies the preprocess runtime and session,
the normal root-owned stop receipt, an independent current observation that
the stopped PID is gone, the prepared feature-cache audit, the exact inventory
digest, and complete unique-audio SHA/FNV coverage. Forced stops, defunct or
reused live PIDs, failed inputs, duplicate or incomplete coverage, and
unverified warm reuse are refused. It requires the encoding artifact's chunk
filenames, sizes, dimensions, and byte hashes to equal the cache audit exactly,
and preserves those descriptors in the final provenance. Warm reuse also must
equal the prior final provenance descriptors. A valid-shaped, same-size cache
byte change therefore refuses on its changed hash. Inventory batch names may
belong to generation runs and need not match the encoder run.

The former driver stop-chain helper remains as a thin compatibility wrapper
over the public shared authority. Legacy and current stop-receipt key sets are
accepted for chain validation; final provenance does not trust a declared
process-state field.

This code reads and validates existing local artifacts only. It consumes the
shared prepared artifact kind window-feature-encoding-v1 rather than treating
its wrapper as a raw operation record. Root must still stop the shared service
after worker detachment, build the cache audit from the completed cache, and
submit the resulting provenance for owner review before any generation use.
This work starts no service, performs no encoding, and contacts no model,
tokenizer, scorer, or endpoint.
