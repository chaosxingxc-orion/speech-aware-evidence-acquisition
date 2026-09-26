# Complete-system sampling configurations and held memory arms

This is CPU configuration preparation, not a flight registration. The closed
candidate recovery, STOP, retained worker and isolated control-quality embargo
remain unchanged. Do not use these fragments as authority for model contact.

## Executable request behavior

The existing four-fragment composer now permits explicit request-only sampling
fields in request_decoding_overrides: temperature, seed, top_p, top_k, min_p,
presence_penalty, frequency_penalty, and max_tokens. Unknown fields, booleans,
nonfinite values and out-of-range numbers fail before contact. The accepted
ranges are repository policy, not a claim about every backend's accepted range.
The llama.cpp random-seed sentinel UINT32_MAX is refused for an explicit seed.

An omitted override retains the original decoding mapping. Sampling-only
overrides retain the legacy adapter's completion reserve; only an explicit
max_tokens override changes it. Serving identity continues to bind the model
fragment, receipt, weights, binary, geometry, server arguments/environment and
roots. A replica seed changes the experiment/request identity, not the resident
service identity. Slot assignment and native tool/response schemas remain owned
by the existing runner.

The four round-one fragments are
slurp-native-stage3-system-round1-r01c-s1-v1 through s4-v1.
They share the existing q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1
model, the R01C625 dataset, and slurp-native-stage3-system-common-r01c-v1.
Each is a separate complete Perception/Solver/Reviewer/Planner execution,
including its own bounded revision and final delivery. There is no grouped
Solver-only sampling or downstream branch sharing.

Construction requests use temperature 0.7, seeds 2026092601--2026092604,
top_k=0, top_p=1, min_p=0, and zero presence/frequency penalties. Disabling
these three truncation samplers makes the proposed distribution explicit; these
are repository adaptation choices, not upstream defaults or tuned optima.
Each request retains max_tokens=512 and the phase's structural grammar.
The [backend source audit](../receipts/continuation/2026-09-26-system-sampling-backend-source-v1.json)
binds the remaining default definitions to the exact pinned llama.cpp source.
A live process/default check is still required before new GPU admission.

A seed is reproducibility metadata. Reusing a replica seed across roles/rows
does not establish statistically independent random streams, joint trajectory
probabilities, or a policy-gradient estimator. Retain all four trajectories,
including identical, failed, capped and abstaining trajectories. Never resample
after viewing feedback merely to manufacture disagreement.

## Common inputs and controls

Three common baseline fragments bind R01C, Fold A and Fold B to the same locked
graph, prompts, source-excluded intent/slot/exemplar stores and twenty-example
selection. Only the cohort's speech vectors, promoted packets and provenance
change. The original prepared-supply artifact and fit identity are removed;
each actual cell must prepare its own verified supply and fit receipts.

The held slurp-native-stage3-system-eval-default-fold-b-v1 fragment composes the
greedy default with the same common knowledge. It is a new matched comparison,
not a reuse of historical Fold A quality under different exemplar knowledge.
All these cohorts are historically exposed TRAIN; no fresh-data claim follows.

Every committed new experiment cell permits only the check stage, is HELD, and
has no execution_plan. Structural contact ceilings are explanatory metadata,
not approved budgets. Worker, campaign, wire-check and prompt-fit modes are
refused by the existing campaign/lease path. The cells are not in the background
queue and have no exposure authorization.

## Memory-dependent configurations

The [memory arm templates](2026-09-26-slurp-system-round-configs/memory-arm-templates.json)
define round-two Fold A sampling and Fold B E/M1/M2 evaluation. They are
design templates, deliberately outside the executable experiment directory.
They do not fabricate candidate hashes or silently fall back to a no-memory run.

Before instantiation, bind the existing candidate_experience_memory interface
to the real artifact/output, source attestation, cumulative construction roster,
disjoint evaluation-role roster, run-specific decision and ordered record hashes.
Use the existing source loader/materializer and shared runtime; no new memory
reader or launcher is introduced. Round two and M1 select all M1 records; M2
selects all M2 records. E binds the same M2 artifact and cumulative provenance
but selects an explicitly empty list under its own decision.

The common memory patch grants the Reviewer the existing corrective-memory
tool and supplies a matching prompt. The model must invoke the tool itself;
the host does not inject a response. The prompt asks for one invocation per
review, treats advice as fallible, and preserves Planner routing and Solver
answer authority. E, M1 and M2 share this interface and the same role budgets.
Trace requested, successful and consumed tool results separately; availability
alone is not evidence of semantic use. The runtime loads the full declared pool
and applies each record's existing applicability conditions at the tool call.
The template registers Reviewer access across OBS/ORG/SUPPLY/USE; this does not
grant other roles tool authority.

The current candidate reader caps the frozen pack at 32 records. This is a real
admission constraint, not permission to take a convenient first 32 records.
Before semantic generation, register a compatible batch consolidation contract
or an explicit algorithm adaptation. If its complete output still exceeds the
bound, retain that failure and refuse reexecution. Real full-batch and full-pool
capacity remains unproved.

The baseline patch replaces only the Reviewer phase entry and adds phase_tools.
All other phase material remains unchanged. Applying a template is an explicit
configuration derivation followed by source/fit checks, not runtime inheritance.
No runtime memory configuration exists until the source-bound bindings exist.

The distinct planned registry label tfgrpo-system-memory-disjoint-v1 describes
full-system sampling, terminal feedback, semantic summary/comparison, group
operations, model-synthesized batch updates and frozen tool-mediated use.
It preserves the historical tfgrpo-semantic-advantage-v1 record and does not
reopen the closed delta experiments. Disjoint forward cohorts, typed guidance,
stable IDs and terminal-count feedback remain explicit adaptations.

## Evidence and remaining admission work

Validation and its substituted boundaries are recorded in the
[validation receipt](../receipts/continuation/2026-09-26-system-round-config-validation-v1.json).
The native execution proof composes the actual four actor configurations, then
uses synthetic task material and a simulated answering transport. It checks
fit/send equality, all four roles and the revised Solver visit. A separate
injected-session proof checks one resident startup for four experiment hashes.
Neither substitutes for actual capacity or GPU reliability.

Before GPU work: resolve the backend/host failure, pin a clean source revision,
close every model/fit/tool/audio/GPU/scoring budget and prospective exposure
registration, generate per-cell preparations, and register source-bound actor
contracts. Memory arms additionally need real semantic-stage outputs and
evaluation decisions. Freeze the full batch/memory capacity rule and exact
statistical/joint decision gates before outcomes. Execute full rounds, one
official score per complete actor manifest, semantic updates, frozen comparison
and matched replication. No real RL cycle or stable benefit has been established.
