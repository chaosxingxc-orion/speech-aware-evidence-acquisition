# Framework integration handoff v5

Status: progress. Native role speech/request components are integrated into canonical master at 1d458f17eb33813cff71cf654fb5bd2d52377f18. The actual registered full-episode experiment entry remains unfinished. Keep the research goal active.

## Framework decision

Use installed OpenJiuwen 0.1.16.post2 public Workflow/BranchRouter, ReActAgent, AbilityManager and AgentRail. The earlier limitations were repository integration constraints. Do not resume the unpromoted custom phase-actor controller. Retain the shared TaskAdapter, KnowledgeProvider, EvidenceAgentController and FlightRuntime; extract pure policy/materialization functions when the native graph needs them.

## Completed model-free integration

The native integration tree is /home/chao/saea-worktrees/native-agentic-system-integration-v1, HEAD 311f88ce. Its completed components are merged into master.

MeteredNativeSpeechRequest now builds and dispatches the same one-use FrozenCoreClient prepared request, with full source-bound framework history, original query speech and scoped tools. Prepared contacts belong to one adapter and snapshot caller metadata. Only known OpenJiuwen context_message_id routing metadata and the exact frozen callback model sentinel are removed from model-visible serialization; unregistered changes are refused.

Root and independent tests exercise actual NativeRoleNode, shared FrozenCoreClient/LlamaServerTransport, PhaseToolDispatcher, FlightRuntime tool custodian and phase sealing with a synthetic provider and POST callback. The Reviewer emits a null-content native tool call, consumes its canonical observation on the next actual transmitted request, and a tool-free Solver retains the evidence. Prepare/render/send bodies agree, speech and tool observations appear once, and synthetic accounting is three model calls and one backend call. This is engineering evidence, not real generation or task improvement.

Combined testing exposed a real instance collision: OpenJiuwen stateless tool registration uses a process-global bare tool ID and retains the first callback. NativeRoleNode now has a unique internal agent identity and owns a private stateful Tool proxy with a cloned card. Public role IDs, visible schemas, prompts and caller cards are preserved. Same-named sequential Reviewer instances now invoke their own providers. Root combined verification: 179 passed, one platform skip; Ruff passed. The merged canonical engineering base check passes. Do not clear framework globals to conceal this defect.

## Closed scientific diagnostics

Raw delivery diagnostic v2 is complete and merged. Output SHA-256 a9fdac614352a767719694d893b65f8431914daff4874d3ecb696636d296a17b. All scientific aggregates and stratum/width tables match v1. DEV1000 adds source-verified counts: 15 joint refusals, 18 hard-first refusals, 56 hard-first attempted intent switches and zero outside-shortlist proposals. See the delivery-supplement-v1 report.

The main SLU verdict remains inconclusive. NEW500 intent improves from 76.6% to 79.4%; pooled SLU micro changes by only +0.01237 percentage points with an interval crossing zero. The joint partition remains 50 gold missing, 53 gold covered but not selected, 236 correct intent with inexact entities, and 161 jointly exact. Do not describe candidate coverage or intent gain as a full-system gain.

## Actual knowledge authoring

Registered support preparation at fa9ba618 is complete. The governed A/B-excluded pool has 9,354 utterances and 37,407 recordings. Intent support has 474 utterances / 2,037 recordings; slot support has 803 utterances / 3,162 recordings over 402 observed intent/type pairs.

Root read all intent support and authored 60 semantic intent values in:
prepared/SAEA-SLURP-SEMANTIC-AUTHORING-PREPARE-V1/authored-intent-boundaries-v1.json
under SPEECHRL_DATA_DIR.
Source SHA-256: 040b8143072ccd660cd1659f5a0ddf71dec5a3f8f8ec6e98bda726a6b7db1a13.

The create-only intent-authoring-review-receipt-v1.json has SHA-256 5a6b1dcffcb03a80e7658d7a5a93b0176d5fc7141e799c5c62947a9dc86422d4. Root used the existing governed readers to verify A1080, B1080 and DEV1000 identities, exact permitted support equality and zero forbidden overlap. Model-free compilation yields 60 values, semantic SHA-256 2803be170657d6d1daf3c0f672e1e6fc2cd0c2e65af2548d559715da6072e41d. No runtime knowledge store has been released.

Do not memorize support anomalies. Cooking-query/recipe, coffee/ordering, some contact intents and takeaway boundaries overlap. The authored values state uncertainty and limitations. Slot source review, contextual extraction contracts and registered release bindings remain outstanding. Keep the outer construction roster identity distinct from the historical KB pool identity. See semantic-authoring-root-review-v1.

## Next root-owned work

Add one explicit opt-in native episode binding through FlightRuntime._dispatch_phase_program -> run_continuous_program -> run_speech_native_agent_loop -> _run_agent_openjiuwen. Preserve the shared outer roster, task adapter, packet, split, trace and scoring path. The None/default path must retain historical behavior.

The native path must execute the existing public NativeEpisodeWorkflow. Every internal ReAct contact must independently use the shared prepared request, capacity gate, lease, ledger and source authority; never hide an entire episode inside one counted controller contact. Keep the current OpenJiuwen slot/admission scheduler and extend its callback seam rather than adding another executor.

Separate reusable role material from bounded unique contact allocation. Let the graph own routing and ReAct own history/tool execution. Reuse pure controller state sealing and QueryState transition construction. The ordered execution receipt must identify role visits, actual model contacts, tool contacts, Planner decisions and the accepted Solver source. Do not derive missing intermediate provenance from only the final episode state.

The shared pure seal_phase_response_state helper is complete at original d192228a, integrated as 311f88ce and canonical b006016324de53490b8cb9e64ef62f4fa325bccc. EvidenceAgentController and phase_runner both consume it; routing, tools and scheduling are unchanged. Root checked 147 controller/phase/supply/staged-request and actual metered-history tests. All three bounded agent subtasks are complete.

Finish root slot knowledge authoring in parallel with runtime wiring. Then register and execute a bounded real GPU proof from the shared configuration entry before admitting a paired task-quality flight. Direct and treatment arms must share the same outer executor and explicit configuration mechanism. Raw E21 remains a separate carrier proof.

## Serving and preservation

Root-owned decoder service serving-slurp-top3-commitment-np8-v1 remains resident at PID 102694, port 8080, no mmproj, eight slots. At 10:47:48 UTC on 2026-09-13 the monitor reports server healthy, eight idle slots, zero utilization and 21,264 MiB allocated. No generation or official scorer is in flight. Keep the ten-second monitor and existing process; this interval is waiting, not productive GPU time.

No new real model, tokenizer, encoder, backend or scorer contact occurred in this work. Preserve frozen campaign code c4e7bb1f and all sealed runs. Keep untracked wsl$/ scratch content untouched. Do not push or publish.
