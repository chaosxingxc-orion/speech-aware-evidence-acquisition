# Native role flight bridge

## Owner direction

Use the installed OpenJiuwen framework for agent control. Do not maintain a second
actor loop or a second scheduler. Keep the frozen core as the only answering model.
Expose analytical tools only to Reviewer and Planner; keep Perception and Solver
tool-free. Supply task-specific knowledge through the existing shared interfaces.

## Responsibility boundary

OpenJiuwen 0.1.16.post2 owns Workflow and BranchRouter routing, ReActAgent iteration
and conversation history, and AbilityManager/AgentRail tool invocation and role
permissions. The repository binds actual requests to speech packets, the frozen
client, source authority, experiment admission, fit checks, and sealed output.

The executable path is configuration -> FlightRuntime phase dispatch ->
run_continuous_program -> run_speech_native_agent_loop -> the existing OpenJiuwen
scheduler -> native Workflow/role nodes. The scheduler now accepts an episode
invoker while retaining its admission queue, stable sample slot, timeout session,
contact shielding/draining, and failure ordering. The historical wave callback
path remains the default when no native episode binding is configured.

## Configuration

The registered phase-native-review-revise-v1 program declares four phase
descriptors and an 11-contact ceiling. Its role graph executes Perception, Solver,
Reviewer, and Planner; the phase descriptor list is not a second routing loop.

A matching native_episode configuration declares:
- schema saea-native-episode-config-v1;
- an episode identity;
- max_revisions;
- distinct exact action strings for accept, revise, and acquire;
- a phase identity and max_iterations for each of the four roles.

Require a computed graph ceiling equal to the registered program ceiling. For
one allowed revision, Perception 1, Solver 1, Reviewer 3, and Planner 1 reserve
1 + 2 * (1 + 3 + 1) = 11 model contacts per sample. Actual use can be lower.
Expose current revision, remaining contact allowance, role iteration bound, and
available Planner actions in the shared role query.

This binding acquires analytical evidence inside Reviewer/Planner ReAct calls.
It binds no separate acquisition node: advertise only accept/revise while a
revision remains, and only accept after the revision bound. The unused acquire
action is rejected by the native graph rather than silently treated as revise.

Use existing phase material, phase tools, knowledge stores, and review tables.
Set native tool entries only for authorized analytical roles, with
source_authority_role equal to the role's phase identity. A tool name must have
one schema across the registered union; each role selects its own subset.
Ordinary tool-free arms keep their original D2 request field set. An empty role
scope on a native-tool arm is explicit and does not select the global registry.

## Actual request and response custody

Every ReAct iteration prepares a real shared FrozenCoreClient request, runs its
actual-contact fit gate, and sends that same prepared request in the assigned
sample slot. Do not count an entire role or episode as one model request.

Bind each tool action to the current pre-contact QueryState, exact raw response,
CoreCompletion request and response hashes, role, sample, selected schemas,
function arguments, and tool-call identity. Use the existing PhaseToolDispatcher
and its counted custodian exactly once. Give repeated actions unique source-bound
attempt, state, and trace identities.

Pass the canonical tool message content string to LocalFunction. Preserve that
message in ReAct history and in the next role's source-bound state projection.
Keep raw model responses intact. Record each role visit and each Planner route,
and accept only the latest eligible Solver receipt.

Canonical output sealing resolves the accepted Solver's existing RequestTiming
by request identity and checks all response hashes and text. It does not use the
last Planner timing and does not synthesize a new response. Retain per-contact
judge criticism even when a phase is revisited.

Keep native role instances alive across revisions. Close their own framework
abilities and rails after the complete episode, including failed episodes, through
public lifecycle APIs. Never clear process-global framework resources belonging
to another sample.

## Dynamic capacity receipt

Use a separately registered native_contact_fit identity:
run_id, attempt_id, contact_cap, and optional max_speech_packets (default 1).

Reserve:

    roster_size * program.max_contacts * (max_speech_packets + 3)

tokenizer endpoints. A realized request with n speech packets spends n + 3
endpoints: properties, template application, and n + 1 text-segment tokenizations.
Validate packet order and identity before endpoint contact. Serialize fitting
under the same experiment lease while other slots of that experiment can generate.
Preserve failed fit journals and never reuse a contacted identity.

This certifies realized variable-trajectory requests before dispatch. It is not
a capacity claim for unexecuted branches. No fit gate may start a replacement
service. Model-free identity checks explicitly report capacity_verified: false.

## Verification scope

Synthetic responses have exercised the actual public Workflow, ReAct nodes,
shared runner, FrozenCoreClient, and LlamaServerTransport renderer:
- ordinary and native-tool arms with empty role tool scopes;
- two samples overlapping while preserving each sample's service slot;
- fit-before-dispatch equality for the actual rendered request;
- accepted Solver output and ordered role/source receipts;
- bounded revision and contact-cap refusal with retained completed contacts;
- one Reviewer task-contract tool call, its exact canonical result in the next
  Reviewer request and revised Solver request, and one counted tool invocation.

A separate test exercises FlightRuntime's actual configuration dispatch through
the continuous runner and canonical Solver output selection. Its fit stub records
request identity only; the shared dynamic fit implementation has separate
synthetic tokenizer tests. These are engineering proofs, not GPU runs, Whisper
quality tests, or evidence of an end-to-end task improvement.

## Remaining experiment work

Finish root review and release of the distinct intent and slot knowledge stores.
Finish the concrete SLURP baseline/arm configuration, exposure registration,
dataset roster binding, and actual service/packet readiness. Then restore a newly
identified root-owned decoder-only service and execute the registered bounded GPU
proof before the discovery comparison. Do not broaden the campaign or change
historical verdicts through this engineering integration.
