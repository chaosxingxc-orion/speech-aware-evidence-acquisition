# Live system evidence gaps after reproducing the original results

Date: 2026-09-10 UTC. Base inspected: 7c2f34f3. Continue the accepted Stage-2 plan; preserve OWNER-REPRODUCTION-FIRST-008 and the original-result audit. This document records the root's implementation review and the resulting engineering sequence. It grants no new generation, scoring or feature-encoding contact and changes no historical configuration.

## Supported starting point

The reproduced evidence supports schema-conditioned SLURP slots and constrained E21 entity repair as components. It does not establish an end-to-end live system. Independent inference repeats already exist for the original components. The useful next engineering work must therefore establish live state provenance, answer assembly, actual request capacity and total cost, rather than spend another generation merely to recover the same published number.

## Current capability and concrete missing behavior

| Requirement | Current evidence | Missing behavior |
|---|---|---|
| SLURP live state transfer | EvidenceAgentController seals current responses; phase_runner.run_program threads prior-phase state; append-sealed-state and the original schema fill already exist. | Every current KC/KV/KU-S3 slot baseline uses a sealed-manifest predecessor. No registered baseline combines a current direct response with the schema slot stage. |
| SLURP final answer | reproduction.slurp_delivery.join_slurp_rosters already gives predecessor scenario/action and slot-arm entities separate authority. | FlightRuntime seals the last phase's response only. The shared join is currently read-side; a live system needs an explicitly declared deterministic delivery with source-bound first and last responses. |
| Raw response preservation | The trace binds requests and raw model responses. Runtime also retains phase summaries. | phases.json is outside the ordinary verified bundle contract. Do not use an unbound sidecar as sole authority for a joined answer, or replace a raw response hash with a derived-text hash. |
| SLURP actual fit | Shared real-request fitting handles one phase and sealed predecessor material. | materialize_phase_requests refuses multi-phase programs. Future-phase requests depend on current responses and require a bounded preflight plus an exact check at the stage boundary. |
| E21 controller bridge | Shared OBS/OJW execution and ControllerWindowHook are integrated. Exact-four synthetic request/delivery parity already exists. | ControllerWindowHook admits only direct-only and creates an empty per-window state context. The repair predecessor is still a pinned historical snapshot. |
| E21 review and planning | Registered critics emit scores and flags without replacement answers. Historical LOOP plans are prepared from sealed drafts. | The bridge does not execute live review. The generic review setting records criticism; on_flag=loop is explicitly refused. No current live reviewer-to-planner-to-new-observation path exists. |
| E21 model-free full-path proof | FlightRuntime has wire_check and a separate shared OBS dispatch. | wire_check incorrectly treats every non-fixed policy as a phase program, so obs-repair-loop-ojw cannot reach its existing dispatch through this proof entry. Fix this shared routing defect before relying on the method for admission evidence. |
| Cost | Whole-roster phase summaries and the OBS driver meter all actual contacts and expose aggregate cost. | A complete system must include current draft generation, later stages, preparation, retries, capacity checks and service boundaries. Four successful selected windows are not a worst-case retry budget. |

Source anchors: rails/controllers.py (EvidenceAgentController.advance); rails/phase_runner.py (run_program); rails/phase_material.py (build_material_for_phase); core/flight/runtime.py (_rows_from_phase_summaries, materialize_phase_requests, _dispatch_obs_policy, wire_check, seal); reproduction/window_controller.py; reproduction/repair_loop.py; reproduction/slurp_delivery.py. The root inspected these functions on the base commit, not just their descriptions.

## Preserve the common execution and delivery contracts

Implement the OBS fake-transport proof through the same _dispatch_obs_policy and core.driver.run_experiment that generation uses. Inject only the existing fake gate/transport. Derive expected successful contacts from the actual window plan, not call count, and preserve the distinction between simulated requests and zero actual neural contacts. Keep the registered run's attempt store untouched. Close or abort synthetic work on failures and leave no substituted transport/plan in the runtime. Do not create another window controller or experiment launcher to make the test pass.

For the future SLURP live path, use a shared two-phase program and the existing append-sealed-state/schema machinery. The first stage must be explicitly defined: the historical predecessor was a full closed-list SLU response, not a newly invented intent-only prompt. Compare the live system against a matching shared-executor direct arm and retain any actual request differences from the original historical baseline. Do not claim identity merely because both use the same prompt template.

Keep ordinary generation output bound to the raw terminal response. A deterministic intent/entities join must be a predeclared delivery product, verified from its source generation trace and the registered shared join. Prefer extending the existing derived-delivery and scoring entry over weakening the ordinary bundle's raw-response invariant. The verified parent trace already contains the first phase MODEL_RESPONSE record and its text/hash binding; phases.json is therefore convenience metadata, not the necessary authority. Existing core.bundle.delivery verifies the parent before replay, and verify_delivery_bundle replays separate saea-derived-delivery-v1 outputs. Extend its source-selection/declaration seam to select both phase responses by explicit phase/contact identity; a postprocessor registration alone cannot make the current OBS-only replay select them. Reuse core.scoring_batch for the complete derived manifest. Include every parser/join dependency in the delivery implementation binding. Preserve both raw sources, their sample/phase/request identities, rule parameters and output hash. Reviewer and Planner never gain answer authority through this assembly.

For future multi-phase capacity, check a conservative bound before opening a live run, then check the actual next-stage payloads once current predecessor responses exist. The second check must use the same request builder as execution, be registered as a tool contact, and hold the exclusive service lease. Never silently shorten output, truncate a predecessor, drop rows or alter a schema when the actual payload fails. Preserve the current response and spent-contact record before a named refusal. Stage-specific caps and their total budget require an explicit configuration; the 64-token historical component and later 256-token retrieval component cannot be conflated.

## E21 timing and feature preparation dependency

Current fixed 90-second input windows can be prepared before first-stage generation. Actual live judge-selected re-listen bounds depend on that generation, so their exact feature inventory does not exist at the start. The historical sealed-plan case avoided this dependency; it cannot establish that a live implementation can prepare all future cuts in advance.

The owner has been asked to clarify whether live means current-run predecessor generation and automatic stage chaining with a preparation barrier, or low-latency completion of each individual sample. This is a product/experimental timing distinction, not a request to reconfirm already authorized engineering work. No dependent runtime or protocol change is made while that clarification remains pending.

A stage barrier can preserve exact selected cuts and feature-first inference, but its preparation and any root-managed service transitions must count in end-to-end cost. A low-latency requirement needs a separately justified observation/encoding schedule. Do not claim one meets the other, silently replace selected cuts with a fixed catalog, allow cache misses to encode during strict inference, or keep the GPU busy by adding ineligible experiments.

## Integration and scientific sequence

1. Correct and prove shared OBS wire-check routing using synthetic data and the existing OpenJiuwen executor. Verify fixed and phase-program compatibility and failure cleanup. This does not qualify the neural cache runtime.
2. Preserve the completed exact-four CPU feature preparation. Resume its registered successor qualification only after the original-evidence review boundary is closed; establish actual strict-cache hit/miss/failure behavior and exact request capacity before a scientific flight.
3. Complete the accepted G5 component comparisons and their official one-pass scoring/decisions. DR retains two generation sources and four predeclared correlated deliveries; LOOP selection and twin remain distinct from live full-system evidence.
4. Implement and verify the missing live state/delivery/planner seams in the common base with config-controlled behavior. Independent model-free engineering can proceed before G5 completes; scientific full-system selection waits for its component decisions.
5. Register complete-system settings, actual phase budgets, matching controls and end-to-end measurements. Preserve G2's failed non-inferiority and G3/G4 holds. No new mechanism is admitted just because this engineering proof passes.

## Worktree archaeology correction

The prior non-ancestor branch list was insufficient to establish missing code. Patch-equivalence and exact file comparisons against 7c2f34f3 show that e21-current-executor-proof (44d8529b), e21-ojw-integration-proof (75f536c7) and shared-preparation (through a8f12368) are already represented on master despite different commit ids. Do not merge them again. The remaining shared-delivery branch commits concern held KU-S4N configuration/readiness only; they do not repair an E21 shared-runtime gap. Preserve the worktrees and the scientific hold.
