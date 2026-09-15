# E21 raw execution-unit bridge

Status: model-free integration evidence; not a GPU admission or a scientific result.

## Shared execution boundary

Keep the 44 discovery calls as the dataset and official-scoring roster. The pinned existing
raw-window inventory supplies 1,593 ordered execution units. A unit retains its parent
sample ID and exact SliceRecord; its separate request key namespaces contact IDs, query
states, controller states, native role histories, fit budgets, traces and result coverage.
Neither a window nor its metadata becomes a new labelled dataset sample.

The raw inventory loader validates the source artifact, full ordered parent roster,
window order, parent custody and all slice bytes. It consumes no legacy model answers,
feature packets or encoder outputs. The same registered slices are admitted into the
FrozenCoreClient's media index before the shared runner dispatches them.

The existing EvidenceAgentController, FlightRuntime and OpenJiuwen executor run both
direct-only and native-role programs. Native role visits retain Solver answer authority;
per-window output is never scored against the entire parent transcript. Terminal results
are first checked against actual contact timing and the existing native delivery validator,
then passed to the shared ordered stitching function. Only parent outputs reach scoring.

Empty direct window responses are recorded as explicit empty-response state metadata while
the actual answer stays empty. Raw model responses and their hashes remain unchanged.
Whitespace trimming and output-cap quarantine happen in the shared delivery function.
Derived request/response/use trace records bind the stitch to its ordered sources and do
not add metered model calls. Existing parent-only timing serialization is unchanged.

The static fit entry point now captures requests from the same single-phase runtime path.
Captured requests are aligned by their scoped unit identity, then checked against the exact
ordered source roster; thread completion order cannot change the fit roster. The native
per-contact fit gate separately binds each observation and counts contacts per unit. Root
verified that a third contact for one two-contact unit is refused while the second unit
retains its own budget, and that cross-window audio is rejected before tokenizer contact.

## Exact inherited source

The configured prepared_execution_units declaration is:

~~~json
{
  "relpath": "analysis/SAEA-E21-DR-SHARED-EXACT-WINDOW-INVENTORY-V1/window-inventory.json",
  "sha256": "7b12a5c32654855701c48b57152ab1643e0c776b9a7a3853fda009a6ac78face",
  "batch": "SAEA-E21-DR-SHARED-EXACT-WINDOW-INVENTORY-V1",
  "registry_run_id": "SAEA-E21-DR-SHARED-EXACT-WINDOW-INVENTORY-V1",
  "unit_count": 1593,
  "split_identity_hash": "fcc1b0bc55432d02347dcdf730c6bcef561a9b0ad9605c45b367e1ed3da5d69e"
}
~~~

The declaration is source binding, not permission to launch an experiment. The full loader
proof is under SPEECHRL_DATA_DIR/coordination/e21-native-window-bridge-v1/
raw-loader-full1593-proof-v1.json. All 44 parents and 1,593 windows passed; no decoding,
encoding, model generation or tokenizer endpoint was used. The resulting ordered roster
hash is 761da3457eb9a28032ec8c47a945a89d6367161dae6be59ee491a6bbec8a2d8c.

## Root verification

Root ran the real local FrozenCoreClient and shared FlightRuntime dispatch against an
in-memory transport using the installed OpenJiuwen runtime. Two concurrent raw windows
of one parent completed eight independent native role contacts, selected the two Solver
responses, stitched one parent output and passed output-to-trace identity verification.
The two-contact direct program passed the same path, including whitespace, empty output,
finish_reason=length, and completion-token cap cases. Original responses were preserved.
A changed unit binding was rejected. Derived stitching did not change contact counts.

The related root regression ran 507 tests successfully, including inherited controller,
native finite-delivery, request staging and delivery identity tests. Ruff and the existing
engineering-base check passed. These are model-free engineering proofs, not capacity,
quality, throughput, or full-campaign results.

## Remaining before an E21 flight

1. Prove the integrated single-phase request materializer through complete synthetic runtime
   construction, then obtain capacity receipts only under a registered GPU contact plan.
   Conditional native roles retain per-contact checks; do not fabricate future histories.
2. Verify the complete runtime construction, preparation, dispatch and bundle lifecycle with
   a registered synthetic source before freezing a real flight.
3. Bind the E21 direct/system configurations, exact source declarations, execution plans,
   exposure entries, serving geometry and full-parent scoring protocol.
4. Queue after the independent A2T and prepared SLURP work. Do not interrupt their frozen
   runtime or change drivers during generation.

No E21 flight was admitted, launched, rescored or scientifically judged by this bridge work.
