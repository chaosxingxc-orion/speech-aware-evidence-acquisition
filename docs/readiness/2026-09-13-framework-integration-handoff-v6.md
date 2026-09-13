# Framework integration handoff v6

Status: the shared full-episode integration is complete with synthetic execution evidence. Actual GPU role validation and task-quality evaluation remain pending. This supersedes the current-status statements in handoff v5 without rewriting that historical observation.

## Implemented framework use

Use installed OpenJiuwen 0.1.16.post2 public Workflow/BranchRouter for role transitions, ReActAgent for bounded model/tool iteration and local history, and AbilityManager/AgentRail for tool registration and execution authority. Keep the existing admission/slot scheduler. Do not resume the paused custom actor loop.

The configured execution path now reaches actual native roles through FlightRuntime, run_continuous_program, the shared speech runner and the existing OpenJiuwen scheduler. The new registered phase-native-review-revise-v1 policy is opt-in. Historical configurations retain their default behavior.

Perception and Solver have no analytical tools. Reviewer and Planner can use their independently scoped registered tools during their own native ReAct turns. The graph routes Perception -> Solver -> Reviewer -> Planner and a bounded revision back to Solver. Only the accepted Solver response can become the task output. This binding collects analytical evidence within those eligible role turns; no separate acquisition node is bound. Advertise only the supported accept/revise actions and refuse unsupported acquisition routing.

Reuse shared phase material, knowledge supply, tool custody, split/roster handling and scoring. Every internal model contact uses one actual FrozenCoreClient prepared request, the assigned sample slot, a separately registered exact-request capacity gate and the existing serving lease. Never count a role containing several iterations as one model contact. Preserve all original response bytes and source-bound tool history.

## Root review and validation

Root implementation 2b9d9994 fixes canonical output provenance: the accepted Solver request can precede the last Planner request, so sealing resolves the actual accepted Solver timing by request identity and verifies its response hashes and text. Tampering with the episode receipt is refused against the runtime result. Keep per-contact judge criticism when a role is revisited, instead of relying only on a latest-per-phase summary.

Role resources remain alive through revisions and are released after the complete episode, including failures, using the public lifecycle APIs. Release only that instance's owned rails and abilities. Preserve the original exception if cleanup also fails.

The integration was reconciled with canonical master da8186a1950a75ccaba5123bb7071fface0edb38 at f9cd4bee. The only merge conflict concerned retaining the new shared pure state-transition helper; the resolved tree preserves both that helper and the existing shared phase-sealing function. Historical analysis, source artifacts, verdicts and prior handoffs remain unchanged.

Final WSL verification on the reconciled tree: 209 passed, three warnings, no failures. The selected suite covers:
- actual native Workflow and ReAct role execution through the shared runner;
- ordinary/native arms, stable per-sample slots and overlapping samples;
- bounded revisions and per-contact ceiling refusal;
- an actual registered local task-contract tool and canonical observation consumption;
- exact prepared/rendered request fitting before dispatch;
- role permission, tool ownership and lifecycle behavior;
- FlightRuntime configuration dispatch and accepted Solver canonical sealing;
- historical controller/phase execution and canonical output invariants.

Ruff passed on every changed Python file. The engineering base and diff checks passed. Synthetic request responses and tokenizer fixtures were used: no real model, tokenizer endpoint, Whisper/backend, encoder, scorer or GPU experiment contact was added. This evidence establishes integration, not task-quality gains.

See [the execution and configuration contract](2026-09-13-native-role-flight-bridge-v1.md) for exact responsibilities, ceilings and capacity accounting.

## Scientific and knowledge state

The completed distinct-candidate matched comparison is unchanged. NEW500 intent improved from 76.6% to 79.4%, while pooled SLU micro changed by only +0.01237 percentage points with an interval crossing zero. The overall verdict remains inconclusive. The closed-joint error partition is 50 missing-gold candidates, 53 covered but unselected gold intents, 236 correct intents with inexact entities, and 161 jointly exact rows. These findings motivate slot evidence and system investigation; they do not establish a full-system gain.

Root reviewed all 474 selected TRAIN intent-support rows and authored 60 intent boundary values. Both runtime store releases are still pending. The separate slot-support review material preserves all 803 selected utterances, 54 types and 402 observed intent/type pairs; it adds indexes, not semantic rules. Root must finish contextual slot contracts from those lawful sources. Keep TEST/DEV content and evaluation feedback outside this knowledge authoring path.

## Serving state

Read-only process inspection at 2026-09-13T13:43:55.390426+00:00 found no llama-server executable running in WSL. Boot identity is bdb3587a-52c6-452a-b7ff-162bbc0b588a. The old service and monitor referenced in v5 are no longer live. The earlier sealed comparison had completed before this restart; preserve its process identity and all contact records.

No replacement service was started and no old attempt was replayed in this integration. At the next ready GPU boundary, establish a new root-owned registered service/session and bind monitoring. Use the prepared-feature decoder configuration without GPU mmproj for the SLURP proof. Do not infer current utilization from historical monitor samples.

## Next bounded work

1. Finish root slot semantics and release the separately bound intent/slot stores through the shared preparation entry.
2. Freeze concrete SLURP baseline and native-role configurations, lawful rosters, delivery rules, tool scopes, actual-contact fit identities and prospective exposure plans.
3. Start the newly identified root-owned service and run the registered bounded real-model engineering proof. Check actual speech/tool consumption and Solver delivery; do not use a small proof for effectiveness claims.
4. After that proof, run the admitted matched discovery comparison through the same shared entry and serving geometry. Continue CPU preparation and complete official scoring in parallel where scientifically eligible.
5. Assess candidate inclusion, conditional selection, entity quality, final task metrics, correction gains and harms, and tool use. Keep training-free policy optimization downstream of a verified system baseline.

Keep the research goal active. No new user decision is needed for routine integration or the already requested preparation. Keep frozen experiment checkouts and untracked wsl$/ scratch content untouched; do not push or publish this work.
