# System selection and training-free relative optimization

**Superseded execution order:** OWNER-SLURP-FIRST-2026-RL-015 replaces the E21-first proposal below. Read [the current SLURP-first plan](2026-09-11-slurp-first-system-and-training-free-rl-plan.md) and [2026 source audit](2026-09-11-training-free-rl-2026-source-audit.md). Earlier results and gaps remain valid; historical paragraphs do not authorize reopening a closed flight.

Authority: OWNER-SYSTEM-OPTIMIZATION-014. Status: root design direction; current evidence and proposed next implementation are distinguished. This document supersedes large-gain and cost-efficiency criteria in the previous next-stage plan. It does not rewrite the two closed system verdicts.

## Research questions in order

1. Does a shared multimodal agent base improve any task-relevant capability relative to direct frozen-model calls?
2. Which OBS, ORG, SUPPLY and USE decisions explain improvements or regressions, and which can be optimized?
3. Once the system and action surface are fixed, can a frozen model with an externally updated policy/experience artifact improve relative to its unoptimized system baseline?

A small aggregate gain with an interpretable component effect is useful at this stage. Failure to establish broad superiority is not failure to establish a promising system. Record all quality dimensions, rather than reduce the current research decision to the old binary gates.

## Primary candidate and supporting carrier

Use E21 full-call transcription and entity repair as the primary candidate. The fresh two-stage pipeline reduced PERSON errors675 to576 (23.1402% to19.7463%, paired gain3.3939pp) and whole-call word errors29216 to29051. Its five extra insertions remain a real recorded regression under the old rule. This is evidence of a useful controlled-revision capability, not proof that the full agent is already optimal.

Use SLURP as a supporting, faster-to-interpret component carrier. Fixed-predecessor S3 retrieval improved slot filling and replicated. The final independently regenerated system pair did not pass NEW500 primary/intent guards; direct intents differ despite equal structured requests. Preserve the separation between component evidence and end-to-end effects. Do not repeat that closed pair.

## System to make explicit

The experimental system is a stateful control plane around one frozen multimodal Solver:
speech input and legal context -> current draft -> Reviewer flags/scores -> Planner action -> selected speech/context acquisition -> Solver revision -> traced delivery -> sealed task score.

The Reviewer never writes the final answer. The Planner acts on deployment-visible state and registered actions. Post-hoc official scores stay outside runtime. Each action must expose the original speech provenance, what new evidence it supplies, and how it can affect the answer.

| Component | Current useful evidence | Optimization surface |
|---|---|---|
| OBS | Fixed long windows protect some entity quality; shorter turn segmentation improves WER but harms PERSON; targeted re-listening beats its random twin yet loses to the incumbent system | Whether to re-listen, target segment, context extent and stopping. Do not assume diarization or shortest cuts are better. |
| ORG | Public call briefs and draft-conditioned entity repair are useful; destructive removal of SLURP original examples was harmful | Local dialogue context, relevant speaker/document scope, conflict and provenance records. Speaker/topic summaries remain optional task-tested representations. |
| SUPPLY | Speech-keyed SLURP filler retrieval has replicated component benefit | Evidence eligibility, ranking, diversity, candidate count, abstention and text/speech representation. Candidate narrowing is not automatically helpful. |
| USE | E21 constrained revision repairs names; free/short-draft variants have regressions | Preserve/revise/stop, allowed edit form, conflict handling and final assembly. Analyze legitimate name-token changes separately from insertions in the scorer. |
| Control | Generic bounded phase Planner and shared state transitions exist | Which component action to choose from current state; feedback-directed policy/experience updates are not yet live. |

## Next engineering increment

Complete only the missing current E21 path: current-run draft -> reviewer flags -> bounded selected plan -> source-bound observation/preparation -> actual Solver revision -> full-call delivery. Extend the existing window/controller/FlightRuntime seams and configuration registries; do not build another agent framework.

Use a canonical allowlisted state projection from existing AgentStateArtifact/AgentStepTransition. Include draft/observation identity, permitted local context, prior actions, selected evidence provenance, task-visible uncertainty/conflict flags and phase status. Exclude reference text, gold entities, correctness labels and future turn content.

Register finite actions with explicit preconditions: preserve, revise with legal brief, acquire/re-listen to a selected speech extent, change a configured evidence view, and stop. Separate component actions so a trace reveals what was optimized. A configuration declaration alone is not evidence the action executed.

## Comparisons for selecting the system

Retain three distinct objects: direct model baseline, fixed unoptimized agent, and later optimized agent. First establish the unoptimized agent's runtime and component behavior. Later report both optimized-minus-unoptimized and optimized-minus-direct; an improved controller does not automatically imply an improved base model.

Use the same frozen data roles, model, scorer and matched serving settings for each prospective comparison. Preserve full natural-mixture and stratum results. Diagnose component effects with matched actions or ablations that have a named question; do not run every combination or choose favorable subsets. Existing shared component runs can supply evidence where their estimand matches.

Do not force every component to show a separate large gain before system optimization. Do require an executable action surface, useful feedback variation and enough repeated decisions for feedback to be meaningful.

## Training-free optimization design after system selection

Freeze core parameters and update a versioned external strategy/experience artifact. Treat a complete speech task trajectory as an episode. Explore predeclared alternative action sequences on the same optimization example, then compare their sealed task-quality outcomes within that group. Exploration comes from explicit action variation; temperature0 generation is not assumed perfectly repeatable.

Keep feedback as a quality vector: WER, PERSON, nonentity, numeric and insertion changes, plus action/transition outcomes. Define ranking or scalarization prospectively after choosing the system; do not insert a cost or latency penalty. Runtime proxies such as critic confidence are not substitutes for official task reward.

Add one shared boundary from sealed trajectory plus complete score receipt to a hash-bound reward record. Offline policy update may consume permitted scores and legal trajectory state. Gold text and annotations never enter a runtime prompt, retrieval store or deployed policy artifact. Keep optimization and evaluation disjoint by call/speaker where available, record historical exposure, and freeze the updated artifact before its evaluation run.

Initially use finite policy choices and structured, incremental experience updates, with add/revise/remove operations and supporting trajectory IDs. Test whether relative feedback improves future choices; a manually changed prompt or fixed rule alone is not a demonstrated RL loop.

Existing analysis/training_free_vw_control.py provides state/action/propensity/artifact conventions, but its learn_feedback fits an external contextual-bandit policy. Do not silently treat that as the selected parameter-free method. Reuse the legal interfaces; selecting a learned external predictor would need a separate boundary decision. Historical gold-bearing offline evaluators must not become runtime code.

The missing shared pieces are the allowlisted current multimodal state projection, action-to-FlightRuntime mapping, sealed reward artifact, and update/freeze/evaluation lifecycle. Implement them only around the selected system; do not start an unrelated optimizer project.

## Research references and interpretation

Training-Free GRPO proposes group-relative semantic feedback and external experience/token-prior updates with frozen model parameters. Its published math/web results do not establish transfer to speech: https://arxiv.org/html/2510.08191v1 .

ACE proposes structured incremental context/experience updates through generation, reflection and curation: https://arxiv.org/abs/2510.04618 . It informs the experience representation; context editing alone is not proof of reinforcement learning.

Our proposed speech adaptation is an inference from those approaches and our existing component evidence. Preserve the stricter repository separation of post-hoc task scoring and runtime content, and the single frozen answerer. Any reflective model contact uses a separately registered role of the same frozen core with no answer authority.

## Immediate execution

Close and merge the current evidence and source changes. Inspect and implement the shared E21 live-control seam with model-free whole-path tests while preparing the finite observation action inventory. Register the next actual capacity and GPU flight once this concrete configuration is ready. Keep the resident service available, pipeline preparation and scoring, and use the GPU for eligible trajectories. Record utilization and contacts, but do not let efficiency or present-stage effect size determine the research route.
