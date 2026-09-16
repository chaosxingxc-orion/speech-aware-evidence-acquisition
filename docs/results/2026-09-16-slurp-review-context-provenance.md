# SLURP review context provenance

Date: 2026-09-16. Root interpretation of the already released complete TRAIN Fold A
anchor. This model-free follow-up examines every executed-revision episode, not a
new cohort. It adds no model, analytical-tool, tokenization, encoding or scoring contact.

## Finding and its limits

An illustrative entity value that appeared in a harmful revision was already present
in the global task instruction and the task-contract tool response. It is absent from
both released semantic knowledge snapshots. The legacy task contract therefore supplies
a separate source of examples, even when the new intent and slot stores are controlled.

The source code explains the path. load_slurp_ontology reads all real TRAIN rows and
retains up to five sorted distinct fillers per entity type. render_slurp_ontology
includes those examples. The registered slurp-label-inventory instruction fill includes
that legacy rendering, and SlurpAdapter.build_task_contract returns the same ontology
through its cache. The task-contract tool returns that contract unchanged.

The example appears later in a Reviewer suggestion and a Solver revision, and also in
another episode's initial Solver output. This identifies exposure and chronology; it
does not establish a causal copying effect, its prevalence, or an isolated remedy.
The audit does not newly decode speech or read gold transcripts/fillers. Repeated trace
metadata fields must not be counted as repeated on-wire token consumption.

The legacy full-TRAIN ontology and the released semantic stores have different
construction boundaries. The latter retain their evaluation-fold exclusions. A generic
ontology example is not itself evidence of target-specific gold leakage; preserve the
difference rather than describing every source as fold-excluded.

## Candidate meaning and role behavior

The five audited trajectories also expose two distinct problems:

- One Perception candidate describes a message-notification request but attaches the
  general_joke label. A fluent candidate explanation can disagree with the legal intent
  it names. Coverage of the gold label alone does not measure this semantic alignment.
- In another episode, Reviewer treats descriptions of alternative candidates as several
  simultaneous requests. The existing single-command contract and prohibition on treating
  knowledge as speech evidence are already present. Adding the same instruction again
  is not a demonstrated new information source.

In the harmful revision, intent selection and entity grounding fail together. In a
different revision, the proposed replacement intent also leaves the original candidate
set despite the Solver prompt requiring selection within it. The current instruction
is not a proof that this boundary is enforced. Measure actual candidate membership
alongside gold coverage and final choice correctness; do not repair historical outputs.

All roles receive the same source speech packet and prior role history. Reviewer is a
separate role with a separate output responsibility, but is neither draft-blind nor a
statistically independent judge. Setting predecessor_binding to none changes instruction
suffixes, not shared state visibility.

## Bounded preparation decision

Prepare one opt-in legal-inventory-only task-contract view using the existing compact
renderer. Preserve all legal scenario/action pairs and entity-type names. Omit unrelated
example fillers from this global contract. Keep intent distinctions and slot explanations
in their separately constructed knowledge stores, selected for the current ambiguity.

The instruction fill and adapter task contract must select the same view. Otherwise the
runtime appends the legacy contract again or the task-contract tool restores the examples.
Use the same adapter contract for native requests, tool responses and capacity checks.
Keep the historical default strings unchanged and bind cache entries to the view identity.
No new controller, role graph or review-history processor is needed for this preparation.

The legacy instruction fill already includes the compact inventory after its example-bearing
ontology. Mere containment of the compact text is therefore insufficient to establish a
consistent no-example view. Refuse mismatched fill/view selections before loading runtime
samples, as well as unknown views. An unchanged default must retain its original behavior.

This is an engineering option, not an adopted scientific improvement. Global examples
may also supply useful semantic cues. The compact inventory preserves label legality,
not a semantic definition of every intent or slot. Removing examples could hurt
performance and needs a complete, separately registered comparison. Do not bundle a causal example-removal claim
into a broader structured-review/tool package. Root selects the smallest useful contrast
after the running maximum-five experiment is fully sealed, scored and compared.

Preserve that active experiment's frozen configuration. E21 and Audio2Tool remain held.
The closed twice-failed dynamic-tools flight stays closed. No new launch is admitted here.

## Prepared configuration and verification

The shared option is implemented without changing any existing experiment fragment:

    {
      "task_instruction_fill": "slurp-label-inventory-only-v1",
      "slurp_task_contract_view": "label-inventory-v1",
      "task_instruction_template": "probes/slurp_native_role_context_v3.txt",
      "task_instruction_template_active": true
    }

These keys select an instruction and contract view; they are not a complete experiment
configuration or a model-contact admission. Keep the normal shared model, dataset,
baseline, experiment and ExecutionPlan composition for any later registered flight.

The implementation passed 112 related tests with 92 percent combined changed-source
coverage, Ruff and engineering-base checks. Root separately verified the actual governed
source: all 60 intent pairs across 18 scenarios and all 55 entity types remain. The old
contract exactly matches its historical exposed SHA256. The new contract has 1834
characters versus 5424 in the legacy contract; no tokenizer endpoint was called, so no
token savings or runtime capacity claim follows. The known illustrative value is absent.

Verification artifact:
coordination/slurp-review-measurement-v1/root-contract-projection-verification-v1.json,
SHA256 d1dbe4915d1cfcdb7035089487bc60263014fd4d5d544f576d1f610442a6f899.
The opt-in still derives its legal inventory from the existing global ontology source;
it does not retroactively make that source fold-excluded.

## Reproduction and custody

The earlier complete-cohort stage report remains authoritative:
2026-09-16-slurp-train-a-review-stage-attribution.md. It includes all 18 scenarios and
distinguishes partial slot gains from complete-task correctness.

All follow-up artifacts are under
SPEECHRL_DATA_DIR/coordination/slurp-review-measurement-v1:

- anchor-context-provenance-audit-preregistration-v1.json:
  ddd076cb0c55946041023a42753247a3d61b09039573b837423a93661bf77a14.
- anchor-context-provenance-locations-v1.json:
  87612228184cc7b333a9d8369cd81f13f262bfccca894f6d738c9783daaf6672.
- root-context-provenance-interpretation-v1.json:
  d10635e3f5e07710d8c4b6fe1ffe4fd27ae9a2403a8468e001f1e6f65f067794.

The locations artifact retains field locations and string hashes without copying raw
responses into Git. Source raw trace:
912e9853e2e32afec9a009afd0aecdae696f6299343f22d3613f4edcde2c6e67.
Source phase trace:
883ce8711ef5e54efdb157d9572afb72f9e03d2e6877bbb990b9365b0b09ceb7.
The narrow case scope cannot estimate how often these patterns occur outside revisions.
