# Finite policy runtime integration

Status: model-free engineering integration completed on 2026-09-25. No formal
policy cell has been registered or flown. The active F10 checkout is unchanged.

## Behavior and framework reuse

The ordinary FlightRuntime supply callback now accepts an optional
finite_supply_policy configuration. Without it, the original callback is returned
unchanged. No controller, answering model, or execution framework was added.

After the initial Perception state is sealed, the callback parses candidates with
the existing SLURP candidate reader and its existing projection rule. It previews
the default 20-example local route, using released training labels from structured
ValueBundle.task_target fields. The preview is explicitly not model exposure.
Its query, ranking, fusion and knowledge identities are checked. The first
candidate's agreement with those labels determines one of the five fixed states.

The frozen schedule chooses one action before the first Solver request. The
complete system then uses the ordinary Solver, Reviewer, Planner and revision
path. Every revision retains the same episode action. The callback neither calls
a model nor updates policy values. The default action uses the existing router;
other actions reuse a factored selection-only router factory and must retain the
same composite knowledge snapshot.

The implementation rejects future role state in the initial decision, mismatched
query/response/sample identities, changed initial state on revision, resumed
partial rounds, unsupported grouped Solver paths, unknown configuration fields,
and overrides outside the admitted exemplar supply route.

## Frozen artifacts and concurrency

The snapshot and schedule are confined local files pinned by raw SHA-256.
Duplicate JSON keys, source changes during reading, unknown fields, mismatched
rosters, split identities, policy contents and invalid probabilities are rejected.

Balanced round-one allocations are determined in frozen roster order, independent
of concurrent worker arrival. Receipts store the actual conditional probability
vector, registered draw, roster sequence, snapshot and schedule hashes.
Round-two epsilon-greedy and zero-exploration evaluation reuse the same interface.
The decision is recorded on the SUPPLY rail before selected evidence is acquired.
The runtime receipt keeps control-plane preview and actual supply visits separate.

## Configuration contract

The optional top-level finite_supply_policy object has these exact fields:

- schema: saea-finite-supply-policy-config-v1.
- algorithm_id: finite-action-bandit-v1.
- phase_id and perception_phase: the existing native Solver and Perception phases.
- preview_store: the existing train-exemplars store; preview_k: 20.
- snapshot and schedule: objects with confined relpath and raw sha256.
- actions: two to four ordered action_id/overrides objects. The unchanged default
  is first. Each later override must address an existing Solver exemplar route
  field accepted by the shared supply knob parser.

This documents a configuration interface, not an executable admission. A complete
formal cell still needs the bound snapshot, schedule, plans, capacity receipts,
root decision, finite completion policies and exposure registration.

## Validation

118 focused and legacy tests passed in WSL Python 3.12, with three preexisting
third-party deprecation warnings. The tests cover the numeric policy, strict
artifact loading, schedule assignment, runtime configuration, and ordinary native
runner and historical supply-variant compatibility.

Two tests run the actual OpenJiuwen execution graph with fake model transport:
one seven-contact revision trajectory and two concurrent four-role episodes.
They verify decision timing, episode-held actions, request evidence and absence
of grouped side-branch artifacts. These are offline framework proofs, not
inference quality, real capacity or GPU-contact evidence.

Root reviewed the implementation and fixed an initially invalid trace payload
prefix. A separate bounded read-only review found no additional concrete defect.
Engineering-base, Stage-3 algorithm-label and finite-completion checks passed.
Historical ledger findings from the prior receipt remain unresolved; these checks
do not establish a clean historical ledger or authorize a flight.

## Remaining boundary

The pure update function validates arithmetic and roster completeness, but does
not by itself prove that inputs came from sealed experiment artifacts. Before a
formal round, implement the offline join of source-pinned complete manifest,
terminal trajectories, policy decision receipts and complete official counts.
That join must reject incomplete or inconsistent sources and construct immutable
next-round snapshots without rereading evaluation labels into policy memory.

Then register real all-action request capacity, including the whole revision
horizon, and the first complete-system policy family. F10 determines whether a
new representation merits subsequent matched confirmation; no F10 outcome has
been read. The first policy is a MemRL-inspired contextual bandit adaptation,
not a faithful MemRL reproduction or an already demonstrated RL gain.
