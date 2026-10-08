# Local node panel preparation

Use scripts/preparation/prepare_manual_audio_recovery.py with the explicit
saea-local-node-panel-preparation-input-v1 schema. Default recovery and historical
admission remain unchanged. This prepares held configs and immutable supply
envelopes. It does not compile proposals, register exposure, qualify proofs,
dispatch execution, or authorize reading outcomes.

Choose target_role as solver or reviewer. Solver uses the exact original review-off
N100 preparation receipt; Reviewer uses the exact original seed N100 receipt.
The shared rails/local_node_panel.py anchors both receipts and original population
by raw hash. Only selected role instruction bytes may change. Controls and A/A
retain original request text. Other policy fields, role text, response schemas,
tools, knowledge bindings, sampling, geometry and ordered roster remain fixed.
Content-addressed paths may move when corresponding role bytes remain equal.

Compile original proposals through the existing compiler and original seed.
Then bind compiled role template paths into the exact current prepared policy:
update phase_material role instruction_template and matching role template
parameters of knowledge-consumption-opportunity. Preserve prepared retrieval,
query, vote, packet and preparation metadata. Verify the existing archive binding
before preparation. Record this deterministic source-preserving binding overlay.

## Input contract

Supply a clean integrated source commit and pinned V4 execution population.
Candidate count, IDs and order come from that population. It allocates zero new
semantic proposals. Separately preserve original actor allocation and root
validation. The complete input shape is:

    {
      "schema": "saea-local-node-panel-preparation-input-v1",
      "target_role": "solver",
      "source_preparation_commit": "<clean integrated commit>",
      "experiment_population": {"relpath": "<repo population>", "sha256": "<raw hash>"},
      "population_cohort": "<configured cohort>",
      "package_relpath": "docs/readiness/<fresh package>",
      "runtime_root": "/home/chao",
      "datasets_lock_path": "<umbrella datasets.lock.json>",
      "graph_dataset_fragment": "slurp-speech-native-simple-consumption-n100-graph4-v1",
      "local_node_basis": {
        "schema": "saea-local-node-panel-basis-v1",
        "target_role": "solver",
        "source_preparation_receipt": {"relpath": "<exact role source>", "sha256": "<raw hash>"},
        "source_population": {"relpath": "<original N100 population>", "sha256": "<raw hash>"},
        "proposal_custody": {
          "registration": {"relpath": "<DATA actor plan copy>", "sha256": "<raw hash>"},
          "validation": {"relpath": "<DATA root validation>", "sha256": "<raw hash>"}
        }
      },
      "member_specs": {
        "<each configured member>": {
          "identity": {
            "experiment": "<fresh lower-case fragment>",
            "cell_id": "<same fragment>",
            "run_id": "<fresh generation run>",
            "attempt_id": "<fresh generation attempt>",
            "fit_run_id": "<fresh actual-request FIT run>",
            "fit_attempt_id": "<fresh actual-request FIT attempt>"
          },
          "policy_binding": "<existing archive binding object>",
          "companions": {
            "capacity": {
              "experiment": "<fresh fragment>", "cell_id": "<same fragment>",
              "run_id": "<fresh run ending -FIT-V1>", "attempt_id": "<fresh attempt>"
            },
            "graph": {
              "experiment": "<fresh fragment>", "cell_id": "<same fragment>",
              "run_id": "<fresh run>", "attempt_id": "<fresh attempt>"
            },
            "natural": {
              "experiment": "<fresh fragment>", "cell_id": "<same fragment>",
              "run_id": "<fresh run>", "attempt_id": "<fresh attempt>",
              "fit_run_id": "<fresh actual-request FIT run>",
              "fit_attempt_id": "<fresh actual-request FIT attempt>"
            }
          }
        }
      }
    }

Root validation schema is saea-local-node-original-proposal-validation-v1,
status ROOT_VALIDATED_ORIGINAL_PROPOSALS. Require matching target_role,
proposal_registration equal to registration pin, ordered candidate_ids equal
to the configured cohort, and runtime_admission false. Its members object contains
exactly candidate IDs. Each member binds execution_config and base_bundle_id.
The top-level original_design_slot object maps exactly candidate IDs to slots.
In configured candidate order those slots must equal the pinned actor plan's
ordered design_slots. The actor schema must match the target role and its status
must be ROOT_COUNTERSIGNED_AND_POSITIONS_RESERVED_BEFORE_CONTACT with runtime
admission false. Preserve supplementary root provenance,
including original output pin and overlay description. Controls have no proposal
allocation. Preserve the original actor output; these are model-authored templates.

Invoke the existing CLI with --input, --input-sha256, --repo-root and --data-root.
Keep input outside the checkout or commit it first: preparation refuses an unclean
source checkout.

## Outputs and qualification

Preparation derives K, N, member order, complete-path generation contacts,
actual-request FIT endpoints and audio allowances from config and parsed topology.
It emits held baseline/experiment pairs, generation receipts, configured capacity,
graph4 and natural4 companions, execution identity map and summary. Duplicate
identities, source spend reuse, existing destinations, policy drift, roster drift
and custody mismatches fail closed.

Supply production copies only pinned original output into a fresh envelope bound
to current config and implementation bytes. Check original output equality and
canonical output digest. Preserve knowledge-store configuration. Do not rebuild
source data or knowledge.

Use existing manual authoring, capacity qualification, natural-family structural
qualification, runtime FIT, root decision, scoring and READ routes. Opt in with
local-solver-panel-v1 or local-reviewer-panel-v1 consistently across plans,
decision and READ recipe. Carry identical local_node_basis throughout.
Historical natural compatibility and architecture extents are refused. Fresh
capacity supply must equal preserved N100 generation output. Local development
has claims_benefit false and adds no full-system adoption gate for each iteration.

Source tests exercise exact config composition, both role topologies, unchanged
knowledge, configured counts and audio budgets, proposal custody,
request-identical controls and refusal cases. Actual fresh preparation and proof
qualification must still run against root-supplied pins. Source tests do not admit
model execution.
