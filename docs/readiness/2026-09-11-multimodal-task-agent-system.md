# Multimodal task agent: tools, TRAIN memory and evidence use

Date: September 11, 2026. Authority: OWNER-MULTIMODAL-SYSTEM-FIRST-016, with OWNER015's SLURP-first sequence and OWNER014's quality-first selection objective. Status: root system specification and source-backed implementation map. Supersede the binary supply-policy seam as the next stage's main implementation. No new system flight or completed optimizer is claimed.

## The system being selected

Select a complete task-solving control plane around the one frozen speech-capable Solver:

task speech + legal task contract -> current working state -> Planner -> source-bound tool execution and memory views -> Solver -> Reviewer -> bounded re-plan or final delivery.

Offline TRAIN memory construction and post-seal quality feedback are distinct processes around that runtime. The testable system includes all three, not only the choice of a retriever. Training-free optimization later changes external strategy, memory organization/utility and action selection while the core remains frozen.

SLURP is the first carrier because the speech/features, TRAIN knowledge and score paths already exist. It need not mimic a meeting. E21/E22 subsequently test longer observation, context and credit chains through the same interfaces. Neither a large immediate gain nor an exhaustive SLURP component search is required before transfer.

## Evidence that changes the implementation choice

Current source: 7ed5f3021f6955c864c1bf7be74895aeaeeb68f2.

- rails/knowledge_build.py:1-71,185-286 is already a TRAIN-only, distribution-aware, decontaminated builder. It links TRAIN text, scenario/action/intent, slot fillers, speaker grouping and recording identity. These are admitted BUILD inputs, not forbidden evaluation gold.
- rails/knowledge.py:344-445 binds an immutable KnowledgeSnapshot to TRAIN or governed external sources and refuses DEV/TEST-built runtime knowledge.
- Current SLURP speech retrieval uses Omni-Embed-Nemotron-3B speech queries against TRAIN text keys. The baseline pins 11,514 text-key utterances, top-5 rank/fusion and prepared recall. This is cross-modal query-to-text retrieval; it does not establish an audio-plus-text episode memory.
- rails/tools.py:13-30,330-374 implements a typed, pinned SYSTEM-invoked tool catalog. It explicitly does not offer those manifests to the core or execute choices from model output. The configured command toolkit is an allowlist, not proof of a live model tool loop.
- Native tool schemas and tool-call envelopes exist in the transport, but the Audio2Tool task's scored tool-call output is not evidence of an internal tool-result-return loop. SLURP can validate real internal schema/memory/observation tool execution without becoming an external tool-call prediction benchmark.
- AgentStateArtifact, QueryState, PhaseSupply and KnowledgeProvider already provide the state/evidence rails. The OpenJiuwen executor and generic bounded review Planner already run. The missing work is their complete system connection, source-bound multimodal memory views and a qualified action dispatcher.

Preserve the shared base. Do not build a new controller hierarchy, memory service, vector database or experiment runner merely to name this architecture.

## Three different stores

### 1. TRAIN knowledge and episodic memory

Build offline from the admitted TRAIN partition, freeze before evaluation, and retain original source identities. Each episode associates:
- source utterance and recording IDs plus original media hash;
- legal TRAIN transcript/semantic description;
- scenario/action and slot schema/filler structure;
- separately pinned text and speech retrieval-key references;
- decoder-ready speech feature packet reference when an audio view is prepared;
- links to declarative schema/vocabulary/prior knowledge;
- builder/encoder versions, source split and preparation lineage.

Reuse the existing Q-K-V design: speech is the primary query, current agent state is auxiliary; keys expose independently rankable facets; values provide task-helpful content. A retrieval embedding and a Qwen decoder feature packet are different artifacts with different consumers. Never substitute one for the other.

Keep semantic, speech and optional speaker-related facets separate. Match in a qualified common embedding space, or combine separately ranked lists through the existing rank/fusion seam; do not assume arbitrary audio and text vectors are comparable. Treat speaker similarity as a possible covariate, not evidence of semantic relevance or an unseen-speaker claim.

The first memory build reuses all qualified existing TRAIN text/schema/source records and the existing speech-query-to-text-key retrieval. A paired speech/text VALUE needs a source-bound decoder packet; it does not require an audio retrieval KEY. Prepare only the missing decoder packets for the frozen eligible evidence union first. Treat TRAIN audio-key retrieval as a separate later ORG/SUPPLY factor, with its own encoder and roster. Do not promise full audio-memory coverage until exact source joins and existing/missing packet counts are verified.

The root's metadata inspection of the current pinned prepared recall found 1,000 query rows, exactly five candidate content facets per row, and 2,621 unique TRAIN content facets in their union. This offers a bounded preparation candidate when that exact selection remains the comparison; it is not a new roster registration or a count of missing recordings. Multiple recordings can realize one text episode. Fix the recording choice from TRAIN identity/quality metadata before outcomes, use the same choice in every applicable arm, and verify cache overlap through the media join. A richer state-dependent retrieval policy must prepare its entire admitted candidate universe or explicitly limit available actions; it cannot silently encode a surprise example during decoder generation.

### 2. Current episode working state

This contains only the current query speech, current drafts/hypotheses, tool results, selected memory references, review flags and executed actions. It evolves during this task and is not silently persisted as knowledge for other evaluation samples.

Do not hard-freeze an initial intent as irrevocable in the full system. If legal evidence reveals a conflict, the Planner may request another schema view and the same Solver may revise the hypothesis. Keep the full legal label space; a retrieved candidate list is evidence, not deletion of other labels. Whether that flexibility helps is a prospective USE/system comparison, not an already established result.

### 3. Procedural experience / external policy

Store general action guidance, applicability conditions, evidence-use rules and reward/trajectory provenance. This is the object TF-GRPO-style updates or a 2026 optimizer may change later. It is not the TRAIN example store and not a table mapping evaluation sample IDs to answers.

Freeze policy and memory versions before evaluation. Scoring-derived feedback crosses an offline update boundary; raw evaluation references never enter runtime prompts or deployed memories. Existing data-role and Stage-2 rules remain in force.

## Tool capability interface

Expose a small task-level capability surface; execute it through existing registered primitives.

| Capability | Input | Result the system consumes | Existing base / missing bridge |
|---|---|---|---|
| Read task knowledge | Current task/hypothesis, knowledge snapshot ID | Legal label/schema/vocabulary view with provenance | TRAIN schema and state-fill loaders exist; expose as a bounded action |
| Search episode memory | Current speech key, optional legal state filters, declared facet/rank mode | Ranked episode IDs with per-facet scores and source bindings | KnowledgeProvider candidates/fuse and prepared recall exist; add episode/source bindings; audio-key facets are an independent later option |
| Open memory evidence | Selected episode IDs and view: text, speech, paired | Typed knowledge values and validated optional TRAIN speech packets | Text materialization exists; shared multimodal view assembly needs qualification |
| Observe current speech | Current packet or a legal segment/context request | The same source speech or registered derived packet, with derivation | ObserveStep/SliceRegistry/preparation exist; connect action/result to current state |
| Check current answer | Current Solver output plus admitted schema/evidence | Flags/scores/conflict locations, no replacement answer | Judge registry and bounded review exist; use their results in the action contract |
| Solve or revise | Current speech, state and selected evidence | Solver-authored task answer | Existing frozen core and phase material path |
| Deliver | Selected terminal Solver response and declared delivery rule | Final task result, preserving raw response | Existing pure delivery/replay and complete scoring |

These are semantic action contracts, not permission to render native Python byte/array APIs to the model. Tool descriptions, JSON-safe inputs and result references must match the actual executable adapters. Reject unknown actions, invalid evidence IDs and illegal media substitutions before a side effect.

Separate invocation modes explicitly:
- The fixed agent baseline uses a declared reproducible Planner policy that invokes real tools and conditions continuation on the current state/flags.
- A frozen-core Planner variant can select from the same bounded action schema and consume returned result references; the same frozen model performs that role, with Solver retaining final answer authority.
- The current catalog's system-only default does not prove or automatically authorize the latter semantic. Implement an explicit opt-in action bridge and retain the old default. Qualify the complete selection -> dispatch -> result -> subsequent model request path before claiming model-decided tool use.
- Later external policy artifacts implement the same action interface. Do not define a different optimizer-owned runner.

The target system is reusable across both invocation modes. Do not confuse the fixed-policy baseline required for attribution with an already demonstrated adaptive tool agent.

## First SLURP system behavior

Use a bounded Plan -> Observe/Knowledge -> Solve -> Review loop with the original query speech kept addressable:
1. Establish task state from source speech and the legal contract. Preserve the original direct baseline as its own matched shared-executor configuration.
2. Planner chooses task knowledge and memory operations needed for that state.
3. Observer/knowledge tools retrieve and open a compact, source-bound evidence view. Keep retrieved relevance separate from the choice to expose text, speech or both.
4. Solver produces the structured SLURP result with the selected material.
5. Reviewer flags schema/label/evidence conflicts. Planner either delivers or requests one bounded, specifically motivated acquisition/revision cycle. Additional steps need new information; repetition alone is not a useful agent capability.

Exact phase/contact ceilings are fixed in the prospective cohort, not inferred from historical two-call or 600-relisten budgets. The fixed policy, allowed actions and memory view settings are configuration, not a private experiment script.

Engineering-lock criteria cover a complete trajectory: actual tool call/result hashes, memory lineage, actual changed request, review/decision, Solver answer, shared delivery and complete official score. A registry row or four-row proof is insufficient for full task-quality claims. A bounded four-row test can qualify connectivity once before the full discovery comparison.

## Minimal comparisons with a named purpose

First compare system objects, then optimize them:
- Direct frozen-model configuration: the no-agent anchor through the shared executor.
- Fixed tool-capable agent without episodic memory: tests whether task organization, tool execution and review offer useful behavior.
- The same fixed agent with TRAIN text memory.
- The same fixed agent with paired TRAIN speech-plus-text memory.

The fixed policy is an attribution anchor, not the endpoint of the architecture. After the complete fixed path is qualified, compare a frozen-core Planner against that exact system with the same memory universe and available tools. The Planner must actually choose executable actions and consume their results; an output naming a tool is insufficient. Complete this adaptive invocation proof before locking a system for training-free optimization. Exact graph bounds and contact counts belong to the prospective configuration, including every Planner and Solver call.

The primary modality contrast holds episode IDs, selection, ordering and text/task metadata fixed and adds the audio view. If selection itself also changes through speech keys, declare a separate retrieval-key question; do not attribute its gain solely to audio consumption. All query inputs remain speech. A text-memory control is not a transcript-only task baseline.

Use common sealed current states for component attribution where appropriate, then independently exercise a fresh complete system to assess upstream decisions and end-to-end quality. Component replay cannot substitute for whole-system evidence. Reuse prior controls only if their actual estimand, program/input and data identities match; do not reopen old attempts.

Later compare optimized external policy against this exact fixed system, with the same available tools and memory universe. Report optimized-minus-fixed and optimized-minus-direct separately. Keep official slot micro metrics and row-F1 distinct, alongside intent/scenario/action, natural/equal-stratum results and failure/revision evidence. Do not reward tool activity or proxy validity instead of task quality.

Not every component needs a large positive effect. A memory view may be harmful, a tool may prove unnecessary, and a simpler retained system may still expose meaningful optimization choices. Record those findings and narrow the deployed capability set based on evidence.

## Why these components should work together

State four falsifiable system hypotheses:
1. TRAIN schema/episodic memories connect speech patterns to legal semantic structures, reducing ambiguity where a direct answer lacks task-specific evidence.
2. Paired values can preserve pronunciation or acoustic cues lost in a transcript-only memory. They can also add irrelevant speaker/noise similarity and overload the request; the same-ID modality comparison tests the net effect.
3. Tool results can repair an initial hypothesis only if the state retains uncertainty and the Solver can reconsider it. More evidence behind an irreversible wrong intent may amplify the error instead.
4. Adaptive control helps only if runtime-visible state and review signals select useful evidence or revision actions. A review score is an observation to evaluate, not the reward itself or proof that a flagged answer is wrong.

Inspect the complete causal path in saved traces: available capability -> chosen action -> returned evidence -> evidence actually supplied -> Solver revision -> official quality change. Report selection correctness only where a lawful post-hoc definition exists; never infer evidence use solely from a retrieval hit. Use matched action/view contrasts where outcomes cannot identify the responsible component. More tool calls are not a success criterion.

## Feedback and training-free optimization targets

After the complete system is concrete, optimize a versioned subset of:
- ORG: memory granularity, facet organization, coverage, summarization/experience consolidation;
- SUPPLY: retrieval query/state use, per-facet fusion, diversity, evidence view and conflict-aware selection;
- OBS: source extent or bounded re-listen when the task has a real observation decision;
- USE/control: evidence consumption instructions, revision form, action sequence and stopping.

Use quality feedback over full trajectories, with component attribution derived from matched traces/contrasts. Establish terminal-reward lineage first; do not assume a word-error change proves which earlier tool caused it. No cost or online-latency reward penalty is required by the owner. Contact/latency/utilization measurements remain reproduction receipts.

TF-GRPO stays the 2025 engineering reference. MemRL/MemQ are relevant to external memory utility and credit; EvoTool/SkillOpt to bounded module/text-policy changes; JitRL to action reranking with its audited numerical caveat. Keep these as implementation candidates until the selected system supplies the corresponding state/action/reward objects. Do not let a paper's easiest port dictate the system.

## One implementation increment and GPU schedule

Complete a single coherent increment:
1. Source/asset inventory and memory schema: the candidate source-to-media join is now complete. Reuse KnowledgeSnapshot/KbRow, freeze one recording-selection rule, hash selected audio and audit packet overlap. This CPU work runs in parallel with action/trajectory implementation.
2. Shared memory views and tool-action bridge: implement through KnowledgeProvider, existing ToolEntry bodies, EvidenceAgentController and OpenJiuwen. Add the return-to-state/model path and bounded invocation modes, not a separate framework.
3. Configured end-to-end proof: actual no-memory/text/paired views, source isolation, returned tool results and final delivery through one executable configuration family. Write meaningful tests around the complete path, not many isolated ratchets.
4. GPU preparation: one registered decoder-packet encoding window for the frozen TRAIN evidence union, skipping only verified cache hits. Keep existing retrieval keys in the first modality contrast; a later audio-key study uses a separately bound embedding preparation. Do not load the speech projector during decoder inference.
5. GPU inference: return to one resident decoder, fit the actual multi-packet requests with their stage output bounds, run ready system configurations consecutively, overlap one complete scorer with the next eligible generation.
6. Freeze the system and its optimization surface; then run the shared feedback/update experiment and transfer to E21/E22.

Do not wait for a generic memory database, every tool, all 2026 optimizers or exhaustive fault hardening. Do not use the GPU for arbitrary traffic while the actual experiment is unregistered. The held KU-S4 campaign remains closed; a new TRAIN-memory system needs its own prospective specification and may reuse independently valid bytes, never an old failed gate or attempt ID.

The metadata-only DEV1000 partition audit found OLD500 and NEW500 share 102 speakers. A possible 383/205/412 optimization/validation/evaluation split is speaker-disjoint but remains historically exposed discovery and is not yet adopted. TRAIN memory construction and DEV policy-update roles remain separate. Dataset-native E21/E22 metrics govern later transfer; no new meeting-minutes metric is invented.

## Readiness receipts

The valid TRAIN asset inventory is DATA coordination/slurp-train-multimodal-memory-readiness-v2.json, SHA256 f5360d2d8293448e3d0cdec281e209d3235d48982c253f11b5d42188c25b9e2d. It supersedes v1 without rewriting it. Source-to-media linkage and source-joined packet coverage are still unknown; 90 known promoted packets cannot be subtracted from text-facet count to estimate missing recordings.

Root loader/count/recall verification is DATA coordination/multimodal-system-root-readiness-v1.json, SHA256 7582ff0758ea4a6da1bf3b7c36ce1515fbc05c285e8439ea91933081d01173b9. The snapshot raw file hash and canonical semantic hash differ by serialization convention and both are recorded. These are CPU metadata receipts, not generated system results or new exposure registrations.

The follow-up source-to-media join is complete for the current 2,621-facet recall union: 294 candidates have one eligible recording, 2,327 have multiple and none have zero. DATA coordination/slurp-train-recalled-candidate-media-readiness-v1.json, SHA256 6344964135820a133c6aba5cb41108ff10ba15e3600ba483801f96427018875d. Root verified its source pins, exact candidate identity set, canonical mapping hash, TRAIN source identities and all 2,621 proposed selected paths. Resolve media_relpath against SPEECHRL_DATA_DIR. The lexical source-ID choice is a deterministic proposal; audio-hash and validated packet-overlap work follows roster freeze. Do not equate 2,621 linked episodes with 2,621 missing packets.
