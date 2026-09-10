# E21 LOOP exact-slice inventory preparation

This model-free preparation materializes the sealed judge and matched-random LOOP plans through the shared `FlightRuntime.prepare_window_inventory` path. Each arm must yield 600 selected slices across all 44 frozen discovery calls and total 15,340.460005376464 seconds. The plan loader re-proves each selected span and predecessor word range before the shared cutter writes and hashes the actual WAV slice.

The two artifacts remain separate because each plan owns different request identities. After both succeed, the closure receipt compares their source audio SHA-256 and encoder keys to report union deduplication across arms. No count declared in this file can substitute for the actual source-bound artifact rows.

This preparation reads the sealed historical predecessor needed to construct each request tail. It opens no reference layer and makes no model, server, encoder, tokenizer or scorer contact. It does not choose a serving geometry, qualify packet transport, authorize fitting or generation, or modify the held LOOP successor.


## Completed preparation and root review

Both source-run-specific inventories completed with 600 requests over 44 calls.
The combined inventory contains 1,200 requests and 1,198 unique audio hashes.
Root independently matched each complete combined batch to its per-arm
request key, payload hash, encoding key and full source-provenance rows.

External directory:
/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/analysis/SAEA-E21-LOOP-EXACT-SLICE-INVENTORY-V1.

- Judge inventory file SHA256:
  0e08d8a9f3d6852b7f707c04a2ee952c38541c9492b45e648b0597bae52cecd7.
- Twin inventory file SHA256:
  0e63b413a536510b1509e2de709cb2ee29616951ba4996b4ae8ddc1b1ab25be1.
- Combined inventory file SHA256:
  e9ebf598700f575a542bb8fa65783d9ac9a0776fa7d96963b9a9254d6d0e4ed9.
- Combined canonical output SHA256:
  62f999740ecf6f9ffe1aa76219a8186c96b354f7ca73c1abf62e05695d57f269.
- inventory-closure.json SHA256:
  8a2c63cc2c7d834cb3cbac30ebee0e1fed01bb14e3c85e53f68b7fe07394ce20.

Actual PCM durations are 15,340.460125 seconds for judge and 15,340.4590625
for twin; each plan requested 15,340.46000537646 seconds. Every cut passed
the existing time/source checks, with boundary quantization below half a
16 kHz sample. Preserve four mpg123 warning lines as decode observations.
The final wrapper print raised KeyError after atomic artifact publication;
independent correspondence verification passed, and no rematerialization
or source-audio repair followed. The external README preserves the public
API/config reproduction sequence and logs.

## Exact reuse and next encoder window

The two cross-arm duplicates are both among the current-build DR overlaps.
Judge and twin each have 11 DR hits, totaling 20 unique reused inputs.
Root verified identical encoder identity and copied the corresponding 240
cache chunks, 193,826,560 bytes, into
/home/chao/feat-cache/e21-cddb000c-loop-gpu-v1. Every copied chunk matches
the completed DR encoding descriptor's size and SHA256; originals remain
unchanged. No neural contact occurred.

The copy receipt is external at
analysis/SAEA-E21-LOOP-WARM-REUSE-PREPARATION-V1/warm-cache-copy.json,
SHA256 5f6260ccc6c80afc58f6b3abf0d6c20520a21d91f0514405b22f223cb3af2d58.
The reuse chain must bind both the completed DR encoding artifact and its
complete preparation provenance. A source encoding hash alone is not the
final provenance identity consumed by preparation closure.

Prepare the two source-run-specific encoding operations on one dedicated
future resident encoder service. Each has 600 total inputs, 11 verified
warm inputs and exactly 589 fresh contacts. Combined new encoding is 1,178
contacts. Keep the existing single-source SliceRegistry boundary and use
the combined artifact to prove union deduplication. No multi-source runtime
exception or duplicate encoding is needed.

Held configurations are e21-loop-judge-slice-gpu-encoding-v1 and
e21-loop-twin-slice-gpu-encoding-v1, using the shared LOOP preprocessing
model fragment. Their per-operation upper bounds are 589 contacts, 0.5
utilization-weighted GPU hours and 15,000 speech seconds. These preprocessing
costs are separate from the unchanged LOOP family 1.0 GPU-hour generation
ceiling. Root must finish the shared warm-reuse review, register exposure
and open the dedicated service window before any encoding contact.
The current DR decoder service and frozen source are unaffected.


## Shared warm-reuse implementation closure

Root reviewed the optional config binding and verified the actual inventories
through the implemented source and cache loader: 600 total inputs, 11 verified
warm entries and 589 fresh inputs for each arm. Both source encoding and
complete provenance wrappers are hash-bound; the warm record carries the
complete provenance SHA required by downstream preparation closure.

The shared runtime tests include one warm plus one fresh input, authorization
cap one, exactly one client contact and two successful output entries. A
valid-shaped feature mutation is rejected before client authorization.
Thirty-five related preparation tests passed, as did the engineering base
check. Legacy no-warm artifact inputs remain unchanged; optional warm inputs
add a source-map digest. No model or encoder contact occurred in validation.

The prerequisite is closed. The held configuration reason now concerns only
exposure registration and the next dedicated root-owned service window.
Do not rematerialize these inventories or re-encode verified warm inputs.


## Registered future encoder window

The exact judge and twin preprocessing ExecutionPlans and exposure rows are
now registered before any contact. Both cells are READY for preparation only;
root lease and full service identity checks remain mandatory. Their shared
encoder service starts after both current DR parents have sealed, with no
overlap in GPU ownership. Source-run-specific operations reuse one resident
encoder configuration and the verified isolated cache. No extra model
qualification request or throughput probe is admitted.

Plan protocols: judge
c4cd977b99c9673ef9e8f065c22b063678dd1e89af3f4b78c94f92f4254081e9,
twin
c06a92a8884f1f3f78bc4c021dc11d9e29e68eef3203e66e38cfc3bd42d5fcf3.
The dedicated service ID is serving-e21-loop-slice-gpu-encoding-v1.
