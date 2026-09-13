# Multimodal task agent: knowledge, corrective memory and control

Current execution overlay, September13: [OWNER-SYSTEM-VERSIONS-025](../superpowers/plans/experiment-handoff/OWNER-SYSTEM-VERSIONS-025.md) makes direct frozen-model calling versus the complete agentic system the primary task comparison. Expand system capability step by step from results. [STATUS-078](../superpowers/plans/experiment-handoff/STATUS-078.md) and [the active direct-versus-native plan](2026-09-13-slurp-direct-vs-native-system-plan-v1.md) supersede older supplied/withheld knowledge comparisons and bulk-encoding priority in this document. Both arms completed and received first official scores from frozen runtime 7ec4cf34. The [released verdict](2026-09-13-slurp-direct-vs-native-system-v1-verdict.md) reports an exploratory candidate: NEW500 pooled micro +14.4297 points and intent +6.2 points. Same-roster replication is dispatched; new results remain held. Preserve task-specific discriminative knowledge, distinct corrective memory and Audio2Tool alongside SLURP and E21/E22 design/readiness.

Date: September 11, 2026. Authority: OWNER-KNOWLEDGE-EXPERIENCE-SEPARATION-017, continuing OWNER016's complete-system design, OWNER015's SLURP-first sequence and OWNER014's quality-first objective. This mutable specification replaces its earlier classification of the raw TRAIN store as episodic memory. Historical source receipts and owner/status records remain unchanged.

## System objective and boundaries

Build a complete control plane around the single frozen speech-capable Solver:

task speech + legal contract -> working state -> Planner -> registered tools -> knowledge and/or applicable experience -> Solver -> Reviewer -> bounded continuation or delivery.

Construct knowledge and learn from execution offline. At runtime, consume their frozen versions through distinct interfaces. The optimization target includes knowledge organization, tool choice, evidence consumption, experience applicability, revision and stopping. The architecture is not determined by whichever optimizer is easiest to port.

SLURP establishes the reusable base first. E21/E22 later exercise longer speech, context and credit chains with dataset-native metrics. Large immediate gains and online latency are not selection requirements. Preserve Stage-2 roles, the frozen answerer, WSL-only execution, complete standard scoring and registered contact lineage.

## Separate five objects

| Object | Content and purpose | Admission and runtime use |
|---|---|---|
| Knowledge | TRAIN speech/text examples, semantic annotations, schemas, vocabulary, domain facts and factual summaries | Build from admitted sources; retrieve evidence relevant to the current task |
| Trajectory archive | Raw inputs/references, requests, actions, tool returns, drafts, reviews, outputs and offline scores, each in its permitted access domain | Preserve audit bytes; do not mount the whole archive into runtime |
| Experience memory | Analyzed failure/correction experiences and generalized procedural rules, including conditions, counterexamples and validation | Admit through an offline decision; retrieve guidance relevant to current state and failure symptoms |
| Working state | This task's speech, hypotheses, tool results, selected knowledge/experience references and review flags | Evolve within the current trajectory; do not silently share evaluation state across samples |
| Policy | Rules or externally updated action-selection behavior | Choose executable actions using legal state, retrieved evidence and applicable experience; freeze the evaluated version |

Classify by function and evidence, not by database technology or whether a record came from TRAIN. A vector store can hold either knowledge or experience; that does not make the concepts interchangeable. A factual summary of SLURP label meanings remains knowledge. A supported lesson about when similar examples mislead the Solver can become experience. A successful trajectory can also support memory when it explains a reproducible strategy; failures are not the only possible source. When a validated rule becomes universally applicable and deterministic, implement it as a shared policy/configuration check while retaining its experience provenance. Keep conditional guidance retrievable rather than adding every rule to every prompt.

## Knowledge construction and consumption

Reuse KnowledgeSnapshot, KeyFacet, ValueBundle, KnowledgeProvider and the admitted TRAIN builder. Maintain source split, recording identity, media hashes, builder/encoder identity and all typed query/rank/fusion bindings.

The current SLURP snapshot contains 11,514 content facets/values covering 50,628 TRAIN source recording identities. Existing retrieval uses speech queries against TRAIN text keys. A decoder-ready speech packet is a value representation, not a retrieval embedding. Paired speech/text values do not require a new audio-key index.

The first modality contrast keeps candidate IDs, recording selection, ordering and text metadata fixed, then adds source-bound speech. It tests knowledge representation. An audio-key retrieval study changes a different factor and requires its own registered preparation. Keep the complete legal label space; retrieved candidates must not erase alternatives.

Prepare the entire admitted candidate union before decoder inference. A runtime policy cannot silently encode an unprepared example. For state-dependent retrieval, either prepare its declared universe or constrain available candidates explicitly.

## What qualifies for experience memory

Use two related record kinds, neither of which is a raw TRAIN row.

1. Corrective experience: describe the runtime-visible situation, observed failure symptom, evidence for a proposed cause, corrective action, before/after outcome and limits of that inference. Retain references to the underlying trajectory and knowledge items, rather than copying all media and annotations into the memory.
2. Generalized rule: state a conditional procedure derived from one or more experiences, its applicable task/model/tool/schema versions, supporting and contradicting cases, validation result and current status.

Keep these minimum fields in the design:
- identity, revision, record kind and construction role;
- source trajectory, action, response and offline score/decision hashes;
- runtime-observable applicability conditions and failure/component tags;
- proposed diagnosis with its confidence or unresolved alternatives;
- concrete action/evidence-use guidance, its prerequisites and limits;
- supporting and harmful cases, validation roster/protocol and result references;
- status, superseded-by lineage and the frozen memory-version binding.

Do not claim a single successful retry identifies the cause of a failure. Changed randomness, prompt form, evidence and observation can be competing explanations. Keep a narrowly scoped episode provisional where appropriate; only stronger validation justifies a generalized rule.

Illustrative SLURP candidate, not a measured result: if the current hypothesis is acoustically or structurally inconsistent with a retrieved example, preserve the full legal intent space, inspect the relevant source speech and ask the same Solver to reconsider. The knowledge store supplies the example and schema. Memory would supply a validated condition and procedure explaining when this reconsideration helps, including cases where it harms.

Illustrative negative experience: a highly similar example led the Solver to copy a slot value unsupported by the query. Keep the source trace, distinguish selection from consumption failure, and test a targeted evidence-use correction. Do not encode the evaluation example's correct answer as the rule.

## Memory lifecycle and feedback isolation

Use a bounded offline lifecycle:

archive -> candidate experience -> validation -> admitted frozen memory -> usage/outcome record -> retained, revised, rejected or superseded.

Construct the first experiences from admitted TRAIN executions or another explicitly designated optimization role. Existing historically exposed discovery results may motivate labeled hypotheses; they are not fresh validation and do not authorize copying their references into runtime. Do not adopt the proposed DEV split merely because a metadata audit exists.

Validate applicability and quality on data separate from the cases used to induce the rule. Report both repairs and newly introduced errors. A larger number of stored memories, confident reflection, or better retrieval similarity is not evidence of task improvement. Judge flags describe observations; dataset-native offline quality remains the outcome.

Freeze knowledge, memory and policy before each evaluation cohort. Evaluation outputs may be archived/scored, but cannot update later samples within that cohort. A subsequent optimization round uses its declared update role and produces a new version. Preserve rejected rules and negative evidence in the archive; runtime sees only the admitted compact view.

## How the agent uses memory

Retrieve knowledge using task content and current lawful state. Retrieve experience using the current phase, uncertainty/conflict signals, available tools, recent action/result pattern and relevant component conditions. A semantically similar sentence alone is insufficient evidence that a procedural lesson applies.

The Planner receives a compact applicable experience view and decides whether to act. The Solver may receive evidence-use guidance when relevant; the Reviewer may check the stated risk. Guidance never becomes a substitute answer. All roles use the one frozen core or admitted pinned tool, and the Solver retains answer authority.

Record available candidates, selected experience IDs/version, applicability match, adopted or ignored advice, executed action and terminal outcome. Evidence that a memory was supplied does not establish that it caused the improvement. Use matched comparisons where attribution matters.

## Reuse the shared implementation

| Capability | Existing seam | Current increment or remaining gap |
|---|---|---|
| Knowledge retrieval and views | KnowledgeProvider, PhaseSupply, KnowledgeSnapshot | New source-pinned text/speech/paired renderer; preserve historical text semantics |
| Actual task action | Native ToolEntry catalog, EvidenceAgentController, OpenJiuwen | Explicit fixed/core-choice selection, real registered invocation, source-bound returned state and subsequent Solver request |
| Current criticism/control | JudgeVerdict, phase_review, phase_planner | Reuse typed criticism and bounded Planner decisions; review declaration alone does not implement re-observation |
| Durable corrective memory | Immutable experience artifacts, registered selector, shared experience_memory_runtime and phase tool | Runtime integration and synthetic source-bound successor-state proof are complete. Construct and validate actual TRAIN memories before admission; do not disguise a KnowledgeSnapshot as experience |
| Current memory-tool output | AgentStateArtifact and the new tool-result bridge | A newly created current-query-bound state can reference old experience; never inject old episode state with stale provenance |
| External update | analysis/training_free_vw_control, proposer/evolution and audited candidate optimizers | Reuse suitable reward/policy lineage after the state/action/memory objects are concrete; no production RL integration is claimed |

The current native configuration uses OpenJiuwen Perception, joint Solver, Reviewer and Planner with at most one revision. Perception proposes up to three intents; the joint Solver consumes candidate-conditioned released slot contracts. Reviewer alone exposes the native task-contract tool and is currently instructed to call it. Planner accepts or requests the bounded revision; Solver retains final-answer authority. The first complete comparison passes the frozen exploratory quality gate; independent replication and component attribution remain unproven.

The existing live speech-observation tool has lazy local Whisper execution and source-bound returns. Its optional Reviewer configuration remains held until the current error analysis justifies it and its own runtime plans are registered. Prepared transcript lookup and current native live execution are different capabilities. Corrective-memory interfaces exist, but no real optimized memory is admitted by this current experiment.

Keep the direct baseline in the same FlightRuntime/controller/OpenJiuwen family. A toolkit registration alone never changes a historical configuration into a model-selected tool loop. Shared preparation, actual request fitting, final delivery and scoring remain the common stages.

## System versions and interpretation

Keep direct frozen-model calling as the task baseline. Evaluate each complete
system version on the registered full roster through the same shared runtime,
model and official scorer. Additional model calls are intentional; quality is
primary and cost is descriptive.

The paired analysis is complete. Replicate the current version before admitting another capability. Use
candidate coverage, candidate-internal choice, spoken-value errors and
harmful revisions to identify the next bounded capability. Examples include
discriminative intent knowledge, controlled candidate reopening, improved
joint reasoning, optional Reviewer-selected speech evidence and validated
corrective experience. Do not implement every option or queue a full component
factorial. The supplied/withheld knowledge draft is withdrawn.

Report each complete version against direct task performance; compare
successive system versions where their sources and estimands support it.
Component replay can help resolve a named cause, but cannot replace live
end-to-end system evidence. Preserve negative and inconclusive results and
follow the inherited same-roster replication or named-component root-cause
rule before admitting another mechanism. Large gains at every increment are
not a requirement for selecting useful optimization surfaces.

Once the state/action space is useful and fixed, compare an externally
optimized policy with that fixed system and with direct calling. A manually
edited prompt, extra tool or memory store alone is not a completed RL cycle.
Keep update, selection and frozen evaluation separated.

## Training-free optimization surface

Treat memory and policy as separate but interacting external objects:
- ORG: choose knowledge structure and experience abstraction, merge redundant records, retain exceptions and revise applicability.
- SUPPLY: choose retrieval state, selected evidence/experience, view and order.
- OBS: choose legal speech extent or re-listening when there is a real observation decision.
- USE/control: choose how evidence is consumed, when a recommendation is adopted, the next tool, revision and stopping.

The [native TRAIN feedback bridge](2026-09-13-native-train-feedback-bridge-result-v1.md) now has synthetic end-to-end source proof through grouped feedback and legal proposal contexts. Config-driven proposal updates, disjoint candidate selection and final memory admission remain incomplete.

Use outcome-linked updates to experience utility and conditional policy, with provenance. Terminal reward alone does not allocate credit to every earlier action; use matched alternatives or explicit uncertainty in credit. Do not call arbitrary summarization or prompt editing RL. TF-GRPO is the 2025 reference; previously audited 2026 implementations remain candidates, not the architecture's organizing principle. No cost or online-latency reward penalty is required.

## Current preparation and execution schedule

Preserve the completed campaign's frozen runtime and artifacts. Prepare its same-roster replication in an isolated WSL worktree; reuse the root-owned decoder service after exact identity checks. Reuse verified query packets, match complete
serving identity and actual request capacity, keep one generating experiment,
and overlap one complete scorer with generation. Do not replace the resident
service or modify the active program to admit a later version.

In parallel, finish only source-bound analysis and the concrete preparation
needed by plausible next capabilities. The optional live-Whisper draft has
verified local source/checkpoint bytes but no new ASR execution authorization.
Its use is selected by Reviewer during execution, not eager dataset
transcription. Choose activation from current errors after the read release.

The earlier paired-example encoding and TRAIN source proposals remain held.
The following retained preparation facts establish historical byte readiness,
not an active queue or a requirement to encode before the current system
comparison. Audio2Tool remains in architecture/readiness and task-specific
knowledge work; later E21/E22 transfer follows their own task identity,
execution scope and official metrics.

The [Audio2Tool native-role reuse audit](2026-09-13-a2t-native-role-reuse-audit-v1.md) verifies the actual frozen-roster adapter path, existing complete-dialogue preparation and ordered scoring. It separates the closed two-stage task system from the new four-role graph and specifies the carrier contracts a successor must bind, without admitting a new flight.

Current preparation roster uses deterministic lexical-smallest TRAIN source ID per recalled facet. It has 2,621 distinct selected recordings. Their full bytes/hashes were verified; 4 packets qualify under the frozen target decoder/projector and 2,617 inputs are cold. This is a preparation roster, not a newly authorized generation roster.

## Artifact lineage

Preserve the historical memory-named filenames below; their contents describe knowledge readiness under OWNER017.
- TRAIN readiness v2: DATA coordination/slurp-train-multimodal-memory-readiness-v2.json; SHA256 f5360d2d8293448e3d0cdec281e209d3235d48982c253f11b5d42188c25b9e2d. V1 remains superseded.
- Root snapshot/recall verification: DATA coordination/multimodal-system-root-readiness-v1.json; SHA256 7582ff0758ea4a6da1bf3b7c36ce1515fbc05c285e8439ea91933081d01173b9.
- Source-to-media readiness: DATA coordination/slurp-train-recalled-candidate-media-readiness-v1.json; SHA256 6344964135820a133c6aba5cb41108ff10ba15e3600ba483801f96427018875d.
- Frozen preparation roster: DATA coordination/slurp-train-recalled-candidate-preparation-roster-v1.json; SHA256 094747c37870440cc4adf5dcea61a5afcd8ad0d5640444a5c68ba12f66ad4ebb.
- Target qualification: DATA prepared/SAEA-SLURP-TRAIN-RECALLED-CANDIDATE-PACKET-AUDIT-V1/target-qualification-v1.json; SHA256 d787ee8aaa42a8ab86de6955de90361fb692348fa2dcf7daff18f427e99d872a.

- Shared full-source inventory: DATA prepared/SAEA-SLURP-TRAIN-RECALLED-SOURCE-MEDIA-V1/inventory.json; SHA256 e578026f4ea30d64a4bc34091e88193f37c1eb16817d0187b719ef16bf0028b0. It pins the existing preprocess-role receipt e170f1c6360a9d0a1a7dde762bca01fb8e6e0373d73117dc212db0d75120fee5; the public execution binding and service qualification remain next work.

These receipts are CPU preparation, not model contacts or system results. The old KU-S4 gate remains failed and its encoding campaign held. The new system needs its own prospective configuration and registration.
