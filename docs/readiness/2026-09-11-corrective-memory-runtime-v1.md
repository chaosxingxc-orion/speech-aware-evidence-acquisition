# Corrective-memory runtime: shared, opt-in integration

Date: September 11, 2026. Engineering status: reviewed and integrated; no real memory catalog is admitted and no memory generation flight is registered.

The shared FlightRuntime now loads a source-bound corrective-memory catalog once before contact. A configured Planner action selects applicable guidance through the registered saea-tool-corrective-memory-v1 tool. The shared phase controller and OpenJiuwen executor carry the result to the successor Solver as an AgentStateArtifact. The frozen Solver retains final-answer authority. Guidance does not enter KnowledgeSnapshot or cited_value_ids.

## Binding and selection

The optional experience_memory configuration has exactly these fields:

- manifest: a DATA-relative path and measured SHA-256 of the memory manifest.
- construction_roster: a repository-relative path and measured SHA-256 of the construction roster.
- admission: a DATA-relative path and measured SHA-256 of the admission receipt.
- task_id: the explicit task identifier used by record applicability.
- component_tags: a unique subset of obs, org, supply and use.
- max_records: a positive bounded integer, at most32.

The phase_tools table must explicitly allow the corrective-memory tool at a legal phase transition. Its action takes no arguments; the runtime determines the actual successor phase and current state. A memory binding without that action, or the action without a binding, is refused before contact. The command Planner toolkit exposes the tool only when both declarations exist.

The initial source admission supports SLURP construction rosters whose members all belong to slurp:train:. Other carriers are rejected by this initial binding implementation. This is not evidence that Audio2Tool or Earnings memory is already implemented.

The loader verifies source paths/hashes, roster role/carrier, exact TRAIN membership, catalog construction identity and the exact admitted record set. The admission schema is saea-experience-memory-admission-v1; it binds the memory manifest, construction roster and admitted record hashes. It is an explicit offline decision input, not a quality verdict produced by the loader.

Selection uses deterministic catalog order, task/phase/component applicability and only these six structural conditions: prior response present/absent, retrieved knowledge present/absent, and tool result present/absent. It does not infer semantic conflict, confidence or correctness from those flags. Unsupported conditions are refused. No match yields an empty selection; no broad fallback rule is silently substituted.

Visible output contains admitted diagnosis/guidance, limitations, applicability and provenance hashes. Full source sample IDs, offline trajectories and outcomes remain in internal lineage receipts. Runtime selection never updates memory.

## Compatibility and proof

Absent memory preserves the prior command toolkit selection and phase-tool receipt shape. Catalog membership alone enables no action. The historical default request path remains unchanged.

A synthetic positive test follows the actual FlightRuntime, continuous phase runner, OpenJiuwen executor, FrozenCoreClient and WireCheckTransport. Two samples each take two phase contacts against fake transport. The test verifies one memory load, successor Solver guidance and absence of source sample IDs from model-facing payloads; actual model contacts are zero. This is engineering wiring evidence, not memory effectiveness or a real capacity-fit receipt.

The isolated relevant suite passed252 tests. After integration, root independently ran107 focused memory/configuration/phase/attribution tests; all passed. Ruff, engineering-base and diff checks passed. Three existing dependency deprecation warnings remain. Root review also found and corrected legacy toolkit exposure and receipt-shape changes before integration.

Implementation boundary: c0494e75 on the integration branch. The runtime implementation lives in rails/experience_memory_runtime.py with a registered wrapper, shared phase_tools dispatcher and FlightRuntime construction. No experiment-specific controller, launcher or scorer was introduced.

## Scientific readiness still required

Historical EVO-S1 has sealed TRAIN construction/validation trajectories, but its round rejected confirmation and admitted no portfolio. The source audit at DATA coordination/slurp-corrective-memory-source-audit-v1.json is provenance for future construction, not admission.

Before a real memory flight, freeze the available task knowledge/tools, permitted runtime conditions, construction/update and validation partitions, candidate rule content, quality metrics, full roster, service geometry, budget, protocol and exposure plan. Validate corrections on the declared partition, then publish measured admission and manifest hashes. Use the shared preparation, actual-request fit, lease, generation, sealing and complete-scoring entries. The present code merge authorizes none of those new contacts.
