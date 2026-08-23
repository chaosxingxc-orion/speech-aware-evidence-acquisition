# Unified speech-native knowledge agent abstraction across carriers

Date: 2026-08-08

Updated: 2026-08-23

Status: the task-independent TRAIN-build/DEV-use contracts are implemented in
`rails.knowledge`; historical carrier adapters and the SLURP M11 controller have not yet
been fully migrated onto one task-independent AgentLoop runner. No cross-task effectiveness
claim is currently supported.

## Research verdict

The reusable object of study is not a better SLU prompt or a larger intent graph. It is an
external, reward-guided control plane around one frozen speech-capable Omni core. The control
plane separately governs:

1. `OBS`: preserve and address the original speech observation;
2. `ORG`: construct a compact, auditable state describing what is understood and what remains
   unresolved;
3. `SUPPLY`: acquire train-built evidence that adds a previously absent decision variable;
4. `USE`: ask the same frozen core to solve the task from the original speech plus the selected
   evidence; and
5. `CONTROL`: stop, acquire, contrast, expand, verify, or backtrack under an external policy.

The immutable query anchor is the original speech-feature packet. Agent-produced text may enter
only as bounded ORG state. Every decision contact carries the same speech packet again. A
transcript, generated intent summary, or state object alone is never a replacement query.

This separation is required by both the local evidence and recent primary work. Speech-Hands
finds that blindly combining original audio with noisy external candidates can degrade performance
and makes source arbitration an explicit action. PlanRAG-Audio separates modality planning,
retrieval, deterministic fusion, and final generation. SPARKLE separates retrieval decision, query
formulation, and knowledge integration. ToolScope separates global planning, local perception, and
answer synthesis. These systems train components that this repository forbids, but their control
topology is directly testable outside a frozen core.

## Knowledge lifecycle

Knowledge construction, knowledge use, and knowledge optimization are three different processes.
They must never be collapsed into one evaluation loop.

### BUILD — TRAIN only

Construct a content-addressed `KnowledgeSnapshot` from a broad, representative TRAIN partition.
Sampling is coverage-driven rather than a fixed number of examples per label. A build must model:

- the support of every task target, including long-tail targets when the label vocabulary exceeds
  100 entries;
- decision boundaries between confusable targets;
- operation, entity, domain, constraint, speaker/channel, and task-defined factors when the source
  data supports them;
- train-derived priors, prototypes, counterexamples, and provenance; and
- missing-factor coverage, so knowledge inadequacy is diagnosed before retrieval is blamed.

The builder may use more TRAIN samples than a later optimization cohort. Build scale is determined
by relation/factor coverage, not the 100/500/1,000 optimization ladder.

### USE — disjoint DEV queries

Freeze the snapshot before opening a DEV query cohort. Each `QueryState` binds one DEV speech
packet, the snapshot identity, previous value ids, and bounded Agent state ids. Ranking and fusion
produce separately hashed `RankResult` and `FusionDecision` records. DEV samples cannot contribute
facets, values, examples, priors, or retrieval memory to their own decision.

### OPTIMIZE — discovery trajectories, then unread DEV holdout

Optimize only the external discrete controller from completed discovery trajectories. Learn action
utility from speaker-isolated, out-of-fold `(state, action, return)` memory. Freeze the policy before
reading an unread DEV holdout. Test remains untouched in Stage-2; a test report requires Stage-3
promotion and a separate execution contract.

## Query, key, and value

### Query

Use:

`query_t = (speech_packet, task_contract, agent_state_refs_t, retrieved_value_refs_t)`

The speech packet is mandatory and immutable across the trajectory. `agent_state_refs_t` may name
factor hypotheses, unresolved gaps, prior candidates, or evidence sufficiency judgments, but these
objects are auxiliary. They cannot contain gold, a reference transcript, a DEV label, future action
outcomes, or an unbound free-form replacement query.

### Key

A key is a set of independently rankable `KeyFacet` objects rather than one task-specific card.
The default representation is maintainable English text. Candidate dimensions include:

- content and semantic intent;
- operation or requested action;
- entity and argument constraints;
- domain and task schema;
- speaker, channel, or acoustic condition when it has demonstrated task utility;
- positive prototypes and contrastive boundaries; and
- procedural/tool affordances.

No dimension is admitted merely because it is available. It must resolve a named task uncertainty,
improve candidate discrimination, or support a mechanism control. Ranking policy and cross-facet
fusion policy remain separate, versioned decisions. This addresses the cross-modal failure observed
in VisRet: shared embeddings can behave like bags of concepts and lose structured relations. It also
adopts GranuRAG's lesson that fine-grained elements must be first-class retrieval units if failures
are to be attributable rather than hidden inside a coarse record.

### Value

A `ValueBundle` is sample-associated task evidence, not just a label string. It may carry:

- a task target or deterministic result mapping;
- train-derived priors and prototype support;
- contrastive evidence and exclusions;
- entity/tool schema details;
- a procedural action or verification rule; and
- complete source-sample and provenance references.

The value must be associated with one or more ranked facets. A label may be returned by a final
deterministic mapping, but it must not leak into key text merely to make matching trivial.

## Information-gain contract

Semantic similarity is a candidate-generation signal, not the scientific objective. The objective
is downstream evidence utility. Utility-Oriented Visual Evidence Selection formalizes this as the
change induced in the answer distribution and shows why visually similar evidence may be useless or
misleading. Its implementation depends on token logits and a second surrogate model, so this
repository cannot reproduce that scorer. The transferable contract is:

- every acquired item has a stable `evidence_id` and names the unresolved decision variable it can
  resolve;
- an action that only repeats visible speech, state, or key text contributes zero new SUPPLY;
- a SUPPLY-producing continuation is legal only if it can introduce an evidence id absent from
  the trajectory;
- post-hoc discovery reward measures the actual task transition caused by the evidence, including
  wrong-to-correct, correct-to-wrong, unchanged-wrong, and unchanged-correct outcomes; and
- novelty, attribution, mechanism validity, contact cost, and latency are reported separately from
  correctness rather than hidden inside one score.

Generated semantic state is ORG, not knowledge SUPPLY. The model may use it to specify a missing
factor or reformulate which facet to retrieve, but the information gain must come from a train-built
value that was not already visible. This preserves the owner's premise: useful information must
exist in the knowledge base; otherwise BUILD is incomplete.

## Task-independent AgentLoop

Use one finite action vocabulary across tasks:

- `STOP`: return the current speech-conditioned result;
- `ORGANIZE(state_schema)`: create bounded auxiliary state while retaining the speech anchor;
- `ACQUIRE(facet_dimension)`: retrieve a new value for a named missing factor;
- `EXPAND(k)`: widen candidate support without changing the query anchor;
- `CONTRAST(candidate_a, candidate_b)`: retrieve a boundary that distinguishes two candidates;
- `VERIFY(value_ids)`: re-evaluate compatibility with the original speech;
- `BACKTRACK`: discard harmful or unsupported state and return to the last speech-grounded decision.

One loop step is:

1. observe the original speech packet and current task contract;
2. organize a strict state with candidates, resolved factors, unresolved gaps, and cited evidence;
3. choose one external action;
4. acquire and fuse only the value ids authorized by that action;
5. call the same frozen Omni core with speech plus the updated evidence;
6. record the transition and either stop or continue within the frozen horizon.

The runtime controller cannot inspect gold or post-action reward. The offline optimizer can inspect
reward only after states, available actions, model predictions, and cost are sealed.

## Per-family fit

| family / task shape | query anchor | knowledge facets and values | task result |
|---|---|---|---|
| long-form contextual ASR (`earnings21/22`, `conec`) | speech span or stream packet | entity, terminology, speaker/channel, local context, correction boundary | transcript or corrected span |
| SLU (`slurp`) | utterance packet | domain, operation, target, entity constraints, intent boundaries | scenario/intent/slots |
| spoken QA (`slue-sqa-5`) | role-typed question and document speech packets | entity, span, relation, answerability, provenance | answer span or free text |
| tool calling (`audio2tool`) | utterance or session-turn packet | tool affordance, operation, argument schema, state preconditions, conflict boundary | deterministic tool call |
| meeting understanding (`ami`) | stream packet plus span address | speaker, topic, entity, temporal relation, decision/action item | structured answer or summary |

Task-specific adapters own parsing, scoring, and deterministic result mapping. They do not own the
AgentLoop action semantics, knowledge lifecycle, ranking/fusion trace, reward schema, or speech-query
invariant.

## Training-free policy optimization

JitRL supports the usefulness of non-parametric state-action-return memory and local action
advantage, but its direct logit intervention and model-based evaluator are unavailable here. Adopt
only the external part:

- store compact, functionally equivalent states with discrete actions and observed returns;
- estimate each legal action relative to the local state baseline from TRAIN/discovery memory;
- require minimum support, explicit exploration coverage, and zero or tightly bounded observed harm
  before selecting a non-primary action;
- choose the action deterministically outside the model; and
- keep model parameters, logits, prompts, retriever parameters, and decoder internals unchanged.

Use lexicographic reward: task correctness first, then harmful transition, mechanistic validity,
evidence novelty, parse validity, calls, tokens, wall time, and GPU time. If a scalar is needed for a
search algorithm, preregister its coefficients and still report every component.

## Engineering fit and remaining gaps

Implemented and reusable:

- `KnowledgeSnapshot`, multi-dimensional `KeyFacet`, sample-associated `ValueBundle`, speech-bound
  `QueryState`, `RankResult`, `FusionDecision`, response-bound `AgentStateArtifact`, speech-bound
  `AgentStepTransition`, and their hash/disjointness/information-delta checks;
- the unified `TaskAdapter`, `EvidenceSet`, `SupplyPacket`, and consumption tracing seams;
- the shared batched AgentLoop runner: TRAIN snapshot/DEV query separation, trajectory-affine slot
  reuse, mandatory packet carriage on every contact, exact ORG/SUPPLY deltas, and scoring only after
  the complete runtime window is sealed;
- an explicit, hash-bound bootstrap value roster for first-contact knowledge visibility and
  append-only ORG/SUPPLY/USE trajectory records. The runtime trace is emitted before scoring; a
  separate post-hoc USE record binds metrics and consumption back to that runtime hash without
  exposing reward to the controller;
- a shared bounded contact-DAG scheduler with one-shot node identities, causal front-priority,
  deterministic same-wave recovery, and explicit in-flight/queue bounds. The historical M11 path
  now reuses this scheduler instead of owning a private ready/pending loop;
- shared `Registry` instances for builders, rankers, fusers, and external controllers; task
  contracts are now named separately from the speech query;
- speech-feature packets, mmproj-free llama.cpp transport, batch/contact dispatch, stable evidence
  ids, prompt-layout auditing, and resident-session receipts;
- the existing SLURP key builders and M11 action-support/OOF readers as a task-specific reference
  implementation.

Still required before a cross-task experiment:

1. Migrate M11 policy selection and its task-specific factor parser onto the registered controller
   and shared runner; retain SLURP parsing only inside the adapter/controller component.
2. Register concrete coverage-driven builder, multidimensional ranker, and fuser implementations;
   the common registries now exist, but an empty registry is not an implemented policy.
3. Bind knowledge snapshot, Agent policy, prefix layout, and cache policy identities into every run
   receipt.
4. Lift contact batches into the shared `AgentController` protocol so registered controllers can
   declare independent branches directly. The scheduler is shared and M11 already consumes it, but
   the high-level runner still exposes only one contact at a time per controller transition.

## Inference efficiency contract

Run only in WSL2. Keep one receipt-bound llama.cpp decoder service resident on the GPU across
compatible experiments. Preprocess every speech packet before inference and never reload mmproj in
the formal service.

Use `speech -> stable text knowledge -> dynamic Agent state` as the primary prompt layout. It
preserves feature batching while allowing the speech and stable text prefix to be reused within a
trajectory. Keep active trajectory KV in HBM and preserve slot affinity. Current llama.cpp does not
provide a safe per-slot HBM-to-CPU cold-tier migration interface; cold trajectories are therefore
reconstructed from the speech packet, snapshot, and state receipt rather than serialized KV. Do not
use the global `--no-kv-offload` switch as a substitute.

Increase queue depth and parallelize independent candidate verification to saturate the existing
small cohort. Do not enlarge the scientific sample set merely to manufacture GPU utilization.

## Protocol discipline

- Published-protocol reproductions remain bare, protocol-faithful baselines. The AgentLoop is an
  additional contribution arm, never a replacement baseline.
- Knowledge BUILD uses TRAIN only; USE and controller optimization use disjoint discovery/DEV
  cohorts; test is outside Stage-2.
- Every seam identity enters `config_hash -> protocol_hash`, and every transition is traced on its
  owning OBS/ORG/SUPPLY/USE axis.
- Speech-swap, state-shuffle, value-shuffle, drop-state, and key-order controls must demonstrate that
  the result depends on matched speech and newly supplied knowledge rather than a text cascade.
- Do not use generated-token log probabilities as a speech-to-key score. Reopen log probabilities
  only if the exact receipt-bound llama.cpp API exposes a normalized conditional score for an
  arbitrary complete key under the speech-feature prefix.

## Primary sources and local boundary

- [Speech-Hands](https://aclanthology.org/2026.acl-long.1997/) supports explicit arbitration among
  original audio, external evidence, and rewrite actions; its fine-tuning and second perception
  model are excluded.
- [PlanRAG-Audio](https://aclanthology.org/2026.findings-acl.1304/) supports modality/factor planning
  and structured multi-stream retrieval; its task models and general-audio streams are not adopted.
- [ToolOmni](https://aclanthology.org/2026.acl-long.1736/) supports proactive retrieval plus grounded
  execution; its SFT/GRPO training is excluded.
- [SPARKLE](https://aclanthology.org/2026.acl-long.1793/) supports separate retrieval-decision, query
  formulation, and evidence-integration roles; its learned proxy model is excluded.
- [ToolScope](https://aclanthology.org/2026.findings-acl.11/) supports separating global planning from
  local multimodal perception; its extra tools/models are excluded.
- [Utility-Oriented Visual Evidence Selection](https://aclanthology.org/2026.acl-long.1620/) supports
  downstream utility rather than semantic similarity; its surrogate model and logit scorer are
  excluded.
- [GranuRAG](https://aclanthology.org/2026.findings-acl.509/) supports multi-granularity keys and
  attribution; its visual detectors are not part of this speech study.
- [VisRet](https://aclanthology.org/2026.acl-long.1192/) documents the structural weakness of direct
  cross-modal similarity; its text-to-image generation bridge is an analogy, not a local method.
- [WavRAG](https://aclanthology.org/2025.acl-long.613/) supports retaining native audio through
  retrieval; its trained audio-text alignment is excluded.
- [JitRL](https://arxiv.org/abs/2601.18510) supports non-parametric trajectory memory and local action
  advantage; its logit update and LLM evaluator are excluded.
