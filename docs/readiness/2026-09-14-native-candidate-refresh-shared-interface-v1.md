# Optional candidate refresh through the shared native role graph

Date: 2026-09-14. Engineering preparation during the unchanged Fold A recovery.
This interface admits no model contact and changes no active or historical experiment fragment.

## Root design

Add a distinct optional Planner action that revisits the existing Perception node before
the next Solver visit. Reviewer and Planner retain analytical tool authority; Perception
consumes source-bound observation and knowledge, and Solver retains final answer authority.
This uses the existing OpenJiuwen Workflow and BranchRouter, the shared FlightRuntime
binding, and the metered actual-request fit gate. Do not create another experiment executor.

Configure native_episode.candidate_refresh with action and max_refreshes.
Require a nonempty action distinct from accept, revise and acquire, and a positive integer
max_refreshes no larger than max_revisions. Each refresh consumes one ordinary revision.
Its additional model-contact ceiling is max_refreshes multiplied by Perception's
max_iterations; the complete program ceiling must include these contacts before admission.

Keep REVISE as a direct return to Solver. The new action returns through Perception.
Analytical tool calls remain actual model-selected calls inside Reviewer or Planner;
the refresh edge does not implicitly invoke Whisper or fabricate an observation.
Expose remaining_candidate_refreshes and the currently allowed Planner actions in the
actual role request only when the new option is present.

At an exhausted global revision allowance, preserve the configured terminal policy.
An explicitly configured deliver-latest-solver outcome records nonacceptance and binds
the last Solver receipt. A request beyond the separate refresh allowance refuses before
another Perception contact. Never treat an unconfigured action as a refresh.

## Candidate state and knowledge

Keep every actual Perception contact in ordered role visits and source-bound phase states.
The initial candidate set comes from the first Perception; a refreshed set comes from its
later actual response before the next Solver. Never infer either set from the final answer.
Preserve both raw responses even if the candidates are identical or invalid.

A candidate-conditioned store consuming Perception must explicitly select the latest
source state when the graph enables refresh. Reject a refresh declaration with the old
single-source selection during configuration validation, before model contact.

The corresponding optional supply mode selects the bounded full card set first and then
adds only previously unseen selected values. Prior visible values remain in cumulative
episode history. Its per-selection card cap is not a cap on cumulative history: with a
single refresh, two disjoint selections can expose twice the card limit. The actual request
fit and the registered program budget must cover this cumulative history. Do not search
past the selected card cap to compensate for already-visible cards.

Default configurations preserve the existing single-source rule, strict partial-overlap
refusal, graph action vocabulary, role limits, request text and contact ceiling. Historical
sources and the running recovery remain frozen.

## Verification and boundaries

Exercise the real OpenJiuwen graph with synthetic metered responses and the shared
native runner with its fake API transport. Verify ordered refresh visits, preserved
initial and refreshed receipts, exact current action limits, fit-before-dispatch for every
actual request, only-Solver delivery, refresh exhaustion and rejection of unregistered
actions. Test configuration ceiling and candidate-supply compatibility before contact.
Run the affected source, receipt, feedback, query-state and engineering checks after integration.

This is an opt-in engineering capability, not evidence of a quality gain. No enhanced
experiment is runnable merely by flipping this option on the incumbent fragment: it
also needs a registered program with the new ceiling, compatible prompts and response
formats, the latest-state supply binding, stage-diagnostic support for all actual candidate
sets, a prospectively bound execution plan, and full actual-request fit. Select the
successor from sealed TRAIN A diagnostics. Keep Fold B untouched until selection.

The currently running source remains
/home/chao/saea-worktrees/slurp-train-anchor-cuda-recovery-v1 at
826a77c7bd9030ccbc25f2b74cd6fa4ed69db561. Use the source's automatic first official
TRAIN score after complete sealing. The reviewed post-seal recipe is
postseal-handoff-recipe-v2.md, SHA-256
f7028cd3250a6d30f30684d17fb4ae2b70adfa6043931ba8b76316080175b51a, under the
slurp-native-dual-store-train-fold-a-anchor-recovery-v1 coordination directory.
It supersedes v1 and prohibits duplicate scoring.

## Completed root review

The integrated graph, source verification, supply, existing diagnostics and reward checks
passed 190 tests. After the final legacy-preservation and route-type refinements, the
affected 65 tests passed again. Ruff and the engineering-base check passed.
Logs and hashes are retained in runtime-progress-and-refresh-preparation-v2.json in the
recovery coordination directory. Tests use synthetic responses; they establish no
candidate-coverage or final-quality gain.

The shared receipt validator now checks actual ordered Perception/Solver/Reviewer/Planner
visits, refresh-to-Perception transitions, revision indices and bounds at runtime, at
canonical delivery, and when verifying an opt-in sealed source. The dispatch receipt
records refresh action and allowance only for enhanced configurations. Default receipts
remain unchanged. The root review also corrected terminal refresh acceptance in sealing
and preserved the original single-source FusionDecision without rewriting it.

The existing TRAIN stage exporter still deliberately accepts the incumbent single
Perception source only. A successor must add explicit initial and post-refresh candidate
projections bound to actual contacts before enhanced generation is admitted. Generic
native source custody and actual-trajectory reward links already support repeated visits.
