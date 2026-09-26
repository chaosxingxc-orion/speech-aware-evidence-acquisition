# Complete-system group update inputs and operation proposals

## Algorithm purpose and fidelity

Continue the locked TF-GRPO sequence: whole-trajectory summaries, semantic
within-input comparison, group update against frozen existing memory, then
batch reconciliation and frozen full-system reexecution. The reference is
the already pinned youtu-agent experience_updater.py at
c2caa539f4c95ae1c39ed24dc8a99cb3651e1d5d; its local copy and prompts were read
again for this connection. No upstream code was executed and no reference
revision was changed.

The new stage consumes actual sealed comparison output, extracts its
Experiences block and presents it with the frozen memory and observed
complete-system comparisons to the same frozen core. It requests ADD, UPDATE,
DELETE or NONE proposals. It does not let root rewrite the learned content
or treat a component score as system return.

This is an input/runtime/operation-reading connection, not a completed
algorithm run. No research summary, comparison, update or reexecution occurred.
GPU diagnosis and fresh scientific registration remain separate prerequisites;
the execution-closed candidate flight stays closed and its isolated control
quality remains unread.

## Shared source and execution path

analysis.prepared_text_source now owns the reader shared by summaries,
comparisons and group updates. It verifies the finalized scoreless bundle,
exact retained clean checkout, composed configuration, registered prepared
inputs, full request population, actual request histories and response lineage.
system_summary_source remains a thin compatibility wrapper preserving its
previous public result shape. No second execution framework was introduced.

Use rails.system_group_update_context and baseline system-group-update-text-v1.
The prepared spec is saea-prepared-system-group-update-v1. It feeds the common
prepared-state loader, FlightRuntime, direct-only controller, OpenJiuwen,
whole-wave fitting and raw artifact output. It refuses a fresh-speech arm.

The DATA-local source document has exactly:

- schema: saea-system-group-update-source-v1.
- comparison_manifest: relpath/sha256 pin to the completed comparison bundle.
- comparison_repo_root: the absolute retained clean source checkout.
- source_construction_roster: the complete original TRAIN roster pin.
- update_roster: the exact ordered ready-update roster pin, or null for
  diagnostic preparation without execution authority.
- memory_id: stable identity of the existing experience pool.
- base_memory: null for an explicitly empty initial pool, or an exact
  materialization_config pin, candidate_artifact pin and snapshot_sha256.

For nonempty memory, replay the existing provisional candidate materializer
from its registered config. Require the replayed artifact and frozen snapshot
to match the supplied pins and complete source construction roster. Preserve
issued IDs and parent history when the source is a consolidated snapshot.
Show record IDs, kind, diagnosis, guidance, limitations and applicability to
the model; keep source hashes and validation metadata outside its prompt.
Every group sees the same snapshot; no group mutates another group's input.

Prepare through the shared module entry point in WSL:

    PYTHONPATH=src /home/chao/.venvs/speechrl/bin/python -m \
      speech_aware_evidence_acquisition.rails.system_group_update_context \
      --data-root "$SPEECHRL_DATA_DIR" \
      --source-relpath REGISTERED_SOURCE_RELPATH \
      --source-sha256 REGISTERED_SOURCE_SHA256 \
      --output-relpath REGISTERED_OUTPUT_RELPATH

## Full construction population versus model-contact roster

Preserve both identities. construction_roster_sha256 in the generic prepared
runtime receipt identifies this stage's active model-contact cohort.
source_construction_roster_sha256 and full_construction_sample_ids identify
the entire original construction population. The base memory is bound to the
latter. A small ready subset must not make other construction samples appear
unexposed or become an evaluation permission.

The comparison preparation now retains its actors' common full construction
roster hash, separately from its comparison-contact roster. Reprepare new
artifacts with their own hashes; never rewrite an older pinned artifact.

Retain every original group and its disposition. Missing or empty Experiences
blocks produce no update proposal. Ambiguous blocks or unusable completions
remain blocked and retain their raw output. Use the upstream case-insensitive
Experiences tag extraction for a single valid block, but explicitly retain
missing/ambiguous cases instead of silently dropping them. The update roster
must equal the resulting ordered ready groups before any registered contact.

## Raw operations and batch boundary

analysis.system_group_operations reads sealed group outputs through the same
source verifier. Its parser preserves exact response text and accepts only
JSON-array operations with operation, id and content fields. ADD and NONE
cannot assign an ID. UPDATE and DELETE must target a record in the original
frozen pool. ADD/UPDATE require nonempty English guidance; DELETE/NONE use
empty content in this declared adapter. Duplicate keys, extra admission fields,
unknown targets and malformed outputs remain explicit invalid records.

Conflicting proposals may survive as input to batch reconciliation. They are
not applied as a sequential edit plan. Empty operation arrays are legitimate
no-change proposals. Capped output is held even if its visible JSON parses.
The derived report preserves the full construction population, frozen base,
raw response and source hash; runtime_authorized remains false.

The old atomic candidate consolidator selects/revises already materialized
proposal records. It cannot yet reproduce upstream batch synthesis of newly
worded experience content. Keep that limited adapter labeled as such.
The next implementation must let the model synthesize typed guidance in the
batch stage, bind its support/contradiction to actual complete-system sources,
and apply the resulting plan atomically with stable IDs. Do not substitute
selection of existing candidates for this missing semantic capability.

## Validation and remaining work

Read docs/receipts/continuation/2026-09-26-system-group-update-validation.json.
306 targeted tests, Ruff and nine offline gates passed. Historical ledger
findings and handoff warnings remain recorded; the checks grant no launch authority.
The focused tests exercise frozen synthetic comparison configurations and
actual recorded request reconstruction, complete-population retention,
empty/capped/ambiguous responses, replay-bound initial and consolidated memory,
the shared runtime fit/send/output path, and operation parsing without mutation.

Source bundle/scorer readers, the base materializer and model transport are
substituted at documented synthetic test boundaries. Existing real-source
materialization and memory tests run as regression coverage; no real new
updater model call or complete source-finalization claim follows.

The updater memory binding does not by itself prove that source actors were
sampled under that same memory. Bind the actually executed actor policy and
memory version when registering a complete round; do not infer on-policy
sampling from a frozen updater input.

Still required: model-facing batch consolidation with source-bound typed
content, the full-population versus active-cohort materialization join,
multi-round TRAIN memory-use scheduling, real capacity registration, complete
sampling/update/reexecution and matched full-system evaluation. The next
scientific conclusion must come from official delivered-task outcomes and
replication against the locked default and strongest eligible fixed system.
