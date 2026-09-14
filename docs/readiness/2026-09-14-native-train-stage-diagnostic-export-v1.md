# Native TRAIN candidate-stage diagnostic export

Status: shared offline implementation with synthetic verification only. This
document registers no analysis read, model contact, scorer invocation, GPU use,
proposal input, memory record, optimizer update, or experiment decision.

## Purpose and source boundary

Run this sidecar only after one complete native SLURP TRAIN task-answer bundle,
its native phase artifact, first complete official score, and reward-link
artifact are sealed and separately registered for reading. The implementation
first calls `analysis.native_episode_source.verify_native_episode_source`, then
uses the existing verified native Perception join and authoritative SLURP
reference/candidate loaders from `analysis.slurp_topn_diagnostics_cli`. It reads
final intent correctness through `rails.reward_link_io`, which re-verifies the
complete score receipt and reward source.

The configuration schema is
`saea-native-train-stage-diagnostic-config-v1`. It pins:

- `native_source.manifest` and `native_source.phase_artifact` by absolute path
  and SHA-256;
- `reward_source.config` and `reward_source.artifact` by absolute path and
  SHA-256; and
- the existing `reference_source` binding accepted by the SLURP Top-N reader.

Invoke the module with the pinned configuration hash, the clean checkout at the
source bundle's recorded commit, and a new output path:

```bash
python -m speech_aware_evidence_acquisition.analysis.native_train_stage_diagnostics \
  --config PATH --config-sha256 SHA256 \
  --source-repo-root SOURCE_CHECKOUT --output OUTPUT
```

The output uses shared `prepare_artifact` storage with contact class
`model-free`. It binds the manifest, phase artifact, reward configuration,
reward artifact, complete score receipt, composed configuration, run, attempt,
protocol, split, candidate projection, legal inventory, ordered cohort, and
construction roster identities. It also binds the hash of the fully derived
document, so an unchanged document can reuse a warm artifact while a changed
derivation refuses stale bytes.

## Exported diagnostic

Each sample contains only its source sample ID, initial distinct candidate
width, `gold_covered`, `final_correct`, `covered_and_correct`,
`covered_and_wrong`, and `uncovered`. `final_correct` is the official
per-sample `scenario_action_exact` native count. Gold intent strings are used
only for an in-memory membership comparison and are never included in the
returned or prepared document.

Aggregate ratios always carry numerator and denominator. Conditional accuracy
uses covered samples as its denominator. If no sample is covered, its value is
null with denominator zero. Uncovered samples are reported separately and are
never assigned a conditional-selection failure reward.

## Limits

This artifact is a post-seal diagnostic sidecar. It does not change the
existing group-relative task reward vector or enter proposal model context. It
does not attribute credit to Reviewer, Solver, a tool call, evidence, or a
transition. It does not estimate a counterfactual, construct procedural memory,
select a compact pack, update a policy, or admit a record. Candidate coverage
and conditional correctness remain descriptive properties of one realized
trajectory.

The initial candidate set is the first Perception state after the configured
first-occurrence distinct projection. A later refreshed candidate set would
need a separately named stage and export. Final correctness is intent
correctness; slot and entity quality remain in the unchanged task-native reward
and score artifacts.

Synthetic tests cover successful exact joins, zero candidate coverage,
malformed or duplicate candidate rows, wrong cohort order, wrong reward sample,
mixed construction rosters, wrong split identity, a reward configuration bound
to another manifest, explicit conditional denominators, and absence of gold
strings from serialized output. Preparation tests cover valid warm reuse and
refusal when a derived document changes under unchanged source identities.
Existing native-source and SLURP Top-N tests remain in the regression selection.

## Root integration review

Root reviewed the shared reuse and found a concrete warm-cache issue: changed
helper behavior could produce a new verified document under unchanged source
pins. The correction includes the derived document hash in preparation inputs.
The synthetic test now checks unchanged warm reuse and refusal of changed
derived output. The integrated65-test selection passed in8.76seconds.
Log: DATA/coordination/slurp-native-dual-store-train-fold-a-anchor-recovery-v1/
integrated-stage-diagnostic-tests-v1.log.
SHA256: d9b2a1d8a862d3d2016272bcb9b9bb50e6a98aead8b870eaf7311fd5fd4cec14.

The assembly test substitutes separately tested source, reward and candidate
verifiers. This is synthetic composition evidence, not a completed real TRAIN
source analysis. The live recovery source remains on its frozen826a77c7 checkout;
these offline code changes do not enter its requests.
