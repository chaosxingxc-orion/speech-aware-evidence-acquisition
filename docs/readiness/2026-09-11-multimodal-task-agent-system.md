# Multimodal task agent: knowledge, corrective memory and control

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
| Durable corrective memory | Existing trajectory/reward/policy artifacts provide inputs | Still needs an immutable experience/rule artifact and registered selector; do not disguise a KnowledgeSnapshot as experience |
| Current memory-tool output | AgentStateArtifact and the new tool-result bridge | A newly created current-query-bound state can reference old experience; never inject old episode state with stale provenance |
| External update | analysis/training_free_vw_control, proposer/evolution and audited candidate optimizers | Reuse suitable reward/policy lineage after the state/action/memory objects are concrete; no production RL integration is claimed |

The new action bridge presently implements two primitives: read the current legal task contract and retrieve shared phase knowledge. It supports explicit fixed and frozen-core choice modes and one action per configured nonfinal phase. It does not yet implement durable corrective memory, every observation action, or the full reviewed acquisition loop. Its plan/solve configuration is an engineering increment, not the locked final system.

Keep the direct baseline in the same FlightRuntime/controller/OpenJiuwen family. A toolkit registration alone never changes a historical configuration into a model-selected tool loop. Shared preparation, actual request fitting, final delivery and scoring remain the common stages.

## Minimal experiments and interpretation

Stage these as named questions, with exact rosters, contact ceilings and dependencies fixed prospectively:
- Direct versus a complete fixed agent: assess the overall system contribution. This contrast can change the number of stages; it is not a pure retrieval effect.
- Fixed agent without additional knowledge versus the same agent with knowledge: assess evidence provision.
- Text versus paired speech/text knowledge, with selection held fixed: assess multimodal value consumption.
- The same knowledge-enabled system without versus with admitted experience memory: assess memory's additional contribution. Hold the knowledge universe, tool capabilities and maximum graph bounds fixed.
- Fixed versus adaptive control over the same available system: assess action selection, then external training-free updates against that frozen baseline.

Do not launch every combination. Select the smallest comparisons needed to resolve the current system question, and preserve historical closed attempts. Check both component behavior and fresh end-to-end performance; replaying a sealed predecessor cannot replace complete system evidence.

A few traceable useful experiences can test the memory interface; they cannot establish a general quality claim on a tiny screen. Apply the repository's full-roster and pairing rules for effectiveness claims. A four-row proof is connectivity evidence only.

## Training-free optimization surface

Treat memory and policy as separate but interacting external objects:
- ORG: choose knowledge structure and experience abstraction, merge redundant records, retain exceptions and revise applicability.
- SUPPLY: choose retrieval state, selected evidence/experience, view and order.
- OBS: choose legal speech extent or re-listening when there is a real observation decision.
- USE/control: choose how evidence is consumed, when a recommendation is adopted, the next tool, revision and stopping.

Use outcome-linked updates to experience utility and conditional policy, with provenance. Terminal reward alone does not allocate credit to every earlier action; use matched alternatives or explicit uncertainty in credit. Do not call arbitrary summarization or prompt editing RL. TF-GRPO is the 2025 reference; previously audited 2026 implementations remain candidates, not the architecture's organizing principle. No cost or online-latency reward penalty is required.

## Preparation and execution schedule

Complete the current shared action/knowledge increment and its configuration path. Finish the generic registered-media connection in the public preparation runtime/CLI, then register one missing-packet encoding window. Use the root-owned encoder service and return to a decoder without the projector in GPU memory. Fit actual multi-packet/stage requests, run eligible configurations consecutively, and overlap preparation and one complete scorer.

In parallel, define corrective experience candidates and the smallest runtime memory interface from admitted execution evidence. Do not wait for a generic memory database or port every optimizer before the first system experiment. Do not confuse the current knowledge preparation with a memory-benefit experiment.

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
