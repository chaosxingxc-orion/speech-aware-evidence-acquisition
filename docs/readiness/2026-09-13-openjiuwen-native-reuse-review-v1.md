# Native OpenJiuwen reuse review

Status: source audit and six synthetic behavior checks complete; independently
reproduced by the root agent. Production role integration remains outstanding.
This receipt records engineering evidence, not task-quality results.

## Owner correction and implementation decision

The owner asked whether the agent framework already implements the routing,
role separation, and analytical tool behaviors discussed in this task.

The answer is yes for the general orchestration mechanisms. The previously
reported limitations describe this repository's current integration, not a
missing capability of OpenJiuwen. Pause the unpromoted custom phase-actor
implementation. Compose native Workflow and ReAct mechanisms before adding
research-specific extensions. Do not create another agent controller, scheduler,
conversation-history loop, or general tool dispatcher.

This is an implementation correction to
[the candidate coverage and node authority amendment](2026-09-13-candidate-coverage-and-node-authority-owner-amendment-v1.md).
It preserves candidate-coverage evaluation, downstream joint intent/slot
selection, Reviewer/Planner analytical tool authority, and Solver answer
authority. It does not change the registered candidate recovery cohort,
projection rule, comparison, or budget.

## Evidence scope

Inspect the installed WSL distribution, openjiuwen 0.1.16.post2, rather than
assuming the latest web API is present. Eight relevant installed source files
match their distribution RECORD digests. Retain the file-level hashes in
[the source audit receipt](2026-09-13-openjiuwen-native-capability-source-audit-v1.json).

The official [SDK overview](https://github.com/openJiuwen-ai/agent-core) and
[English single-agent API](https://github.com/openJiuwen-ai/agent-core/blob/develop/docs/en/2.Development%20Guide/API%20Docs/openjiuwen.core/single_agent/single_agent.md)
corroborate workflow, ReAct, ability management, and context support. These
moving documentation pages are explanatory references; the installed bytes and
synthetic checks are the local compatibility evidence. Context7 was unavailable,
so the audit used installed source and official upstream documentation.

Read repository code at 867c12e00e57ae100bd768c0c11e2b52ad678d77 for the
integration findings below. Do not mutate the frozen serving or active source
worktrees during this audit.

## Capability mapping

| Requirement | Installed framework mechanism | Present integration and action |
| --- | --- | --- |
| Route to a different node after review or planning | Workflow.add_conditional_connection; BranchComponent | The current speech graph uses generic prepare/contact/aggregate nodes. Express actor transitions in the native graph. |
| Bound a local reasoning/tool loop | ReActAgent; ReActAgentConfig.max_iterations | The current controller interprets tool requests and advances a flat phase sequence. Compose the native ReAct loop for eligible actors. |
| Register tools and return observations to the model | AbilityManager; Tool/LocalFunction; framework ToolMessage creation | Reuse the framework dispatch/message lifecycle; adapt only the study's pinned tool contracts, evidence bindings, and contact records. |
| Give roles different visible tools | An independent agent AbilityManager per role | Remove the assumption that all nonfinal phases must advertise one identical tool set. Enforce authority as well as visibility. |
| Continue after a Reviewer returns text | Workflow node outputs and explicit downstream edges | Treat completion of the Reviewer node as a review result; do not deliver it as the task answer. |
| Carry scoped history and evidence | Session input mappings; ModelContext; ContextEngine | Select the lawful evidence for each actor using the shared knowledge provider, then let framework contexts carry it. |
| Intercept model and tool calls | AgentRail and public lifecycle callbacks | Attach study budget, source, permission, and provenance checks at these boundaries. |
| Keep one frozen answering model | ReActAgent.set_llm public injection point; WorkflowComponent composition | Inject the existing metered frozen-core request path. Do not instantiate an alternate answering model or an unmetered provider client. |

The current graph does use OpenJiuwen meaningfully for loop scheduling,
parallel graph execution, fan-in, and session dataflow. Calling it entirely
unused would be inaccurate. Its integration is incomplete at the actor and
tool-decision level.

## Concrete integration limitations

1. In rails/phase_tools.py:139-158, native-answer-or-tool requires native tools
   on every nonfinal phase, with identical tool/schema/store signatures.
   This is a repository validation rule, not an OpenJiuwen requirement.
2. In rails/controllers.py:735-739, tool choice is derived from whether the
   phase is last, rather than its actor authority.
3. In rails/controllers.py:856-857, any non-tool native completion stops the
   current program. This does not distinguish a Reviewer finishing a review
   from a Solver completing a task answer.
4. In reproduction/ojw/runner.py:341-398, the native graph is a
   prepare_agent_wave -> agent_contact_* -> aggregate_agent_wave loop.
   Role-specific reasoning currently lives behind the callbacks.

The role meanings are application policy. The framework provides composition
and enforcement hooks; it does not infer the research contract from node names.

## Specific boundaries that still require study code

- Keep TaskAdapter, KnowledgeProvider, EvidenceAgentController, and FlightRuntime
  as the shared study bases. Move general orchestration responsibility into the
  existing OpenJiuwen integration. Let the controller retain study policy and
  configuration interpretation rather than grow another execution framework.
- Keep the actual multimodal request builder, packet/slice binding, service
  identity/lease, and exact fit check. The installed generic ReAct input helper
  converts ordinary query input to text; a generic chat example is not proof
  that prepared audio packets or selective re-listening stay byte-equivalent.
- Keep dataset-specific candidate validation, intent/slot knowledge value
  construction, evaluation, and no-reference runtime boundaries. Framework
  context or memory storage does not decide what constitutes useful
  discriminative knowledge, a lawful memory, or the correct task label.
- Keep delivery provenance: only a validated Solver artifact can be delivered.
  A Planner can accept that artifact or request a revision; it cannot substitute
  its own answer. A Reviewer can assess or collect permitted evidence.
- Retain model/tool cost accounting and OBS/ORG/SUPPLY/USE traces at native
  lifecycle boundaries. Framework telemetry alone is not an exposure ledger.
- Pin automatic argument repair, history processing, retries, and stop behavior
  explicitly before production adoption. Do not silently change a historical
  arm by adopting framework defaults.

## Permission and failure details

The installed AbilityManager contains a global-resource fallback
(ability_manager.py:1287-1305). A tool omitted from an agent's advertised tools
can still be looked up by name if globally registered. Therefore an empty
Solver tool list is not, by itself, a hard analytical-tool prohibition.

Use a public BEFORE_TOOL_CALL hook with the explicit role/tool allowlist before
any backend action. The callback framework distinguishes AbortError from
ordinary callback exceptions; an ordinary raised exception may be logged rather
than stop dispatch. Verify actual backend non-execution, including a globally
registered but unadvertised fake tool. A denied action and termination of the
entire agent are different outcomes.

The packaged ReActAgentComp exposes ability_manager but not a public model
injection setter, and converts invocation exceptions to result_type=error.
Prefer a thin WorkflowComponent that composes the public ReActAgent and
set_llm method when the single frozen-core door is required. Do not patch
private fields or subclass the framework loop. Handle returned error outcomes
explicitly before downstream delivery.

## Intended episode composition

Use this role graph as a configurable composition, not a mandatory extra model
call at every edge:

1. Perception consumes intent knowledge and produces an explicit candidate set.
2. Solver consumes candidate-specific slot knowledge and original evidence,
   selects an intent, and produces a draft with slots.
3. Reviewer consumes the draft and evidence; it may invoke scoped analytical
   tools in its native ReAct node and returns structured findings.
4. Planner consumes the findings and controls accept, acquire more evidence,
   or revise. It may invoke only its own registered analytical tools.
5. Revision routes to Solver. Acceptance delivers the latest validated Solver
   artifact. Bound both local ReAct iterations and whole-episode contacts.

Candidate source quality is measured offline by gold inclusion in the set.
The runtime never sees gold labels. Downstream selection quality is measured
separately. Independent intent and slot knowledge stores remain appropriate
because they supply different decision evidence; a framework memory facility
does not eliminate that distinction.

## Execution order

The bounded native-framework proof is closed. Root reviewed its source and
independently reproduced all six outcomes with the same result digest. The
proof required no real model, tokenizer, analytical backend, dataset, or GPU
contact. No serving process was changed.

Next, wire the minimal native composition through the existing frozen-core and
tool boundaries, verify actual request/fit equivalence and role authority, and
register the bounded real-model validation. Keep the already registered
candidate commitment comparison separate from this new mechanism.

The current candidate source was generated previously; its deterministic
recovery and matched successors do not require the new role/tool mechanism.
Continue their independent preparation without expanding this comparison.


## Closed synthetic validation

The root reproduction exactly matches
[the six-check result](2026-09-13-openjiuwen-native-reuse-proof-v1.json),
SHA-256 635d25008a5d87610958b46e50e7df9e9636b5faa7e2d1f6161d5d539b9ef464.

The public checker is scripts/checks/openjiuwen_native_reuse_check.py. It accepts
only a new output path and refuses to overwrite a previous result. Run it as a
separate process because its synthetic tools use the framework's process-local
registry. It is an engineering check, not an experiment or production executor.

From a checkout in WSL, run the following with a fresh output path:

    PYTHONPATH="$PWD/src" /home/chao/.venvs/speechrl/bin/python -B scripts/checks/openjiuwen_native_reuse_check.py --output /tmp/saea-ojw-reuse-proof-new.json

The six passing checks demonstrate:

1. An advertised analytical LocalFunction is invoked and its observation returns
   through framework-managed assistant/tool history with the call ID preserved.
2. Different agents receive different advertised tool sets.
3. A globally registered unadvertised tool can execute without an authority
   rail, confirming that visibility and execution authority are separate.
4. AgentRail.before_tool_call with public AbortError prevents the denied
   callback from executing; the framework returns a tool-error observation
   and continues the bounded agent. It does not automatically fail the flight.
5. A one-iteration limit permits one model/tool iteration and then returns
   result_type=error. An episode must handle this outcome explicitly.
6. A Workflow passes a Reviewer's textual output to Solver and executes Solver.

The source inspection also confirms conditional-routing APIs. This synthetic
check exercises a linear Reviewer-to-Solver edge, not every branch, a complete
multimodal episode, real speech tools, service affinity, or dataset quality.
Those remain implementation or experiment checks at their appropriate boundary.

Separately, 144 focused tests passed after integrating shared aborted-source
verification and the deterministic hypothesis projection. Those changes do not
supply evidence for a native-role performance claim.
