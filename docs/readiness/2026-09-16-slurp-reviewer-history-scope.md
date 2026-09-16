# SLURP Reviewer history scope: model-free preparation

Date: 2026-09-16. Root owns the design, interpretation and experimental admission.

## Purpose and status

Prepare one shared, opt-in Reviewer context control. The released anchor exposes complete
earlier role history to Reviewer. The stage and provenance analyses identify both weak
correction and cases where alternative hypotheses become answer evidence. They motivate
a controlled context experiment; they do not establish that history scope caused the errors.

The existing held structured-review v2 instruction already checks supported omissions,
unsupported values, competing intents and extraction boundaries. Repeating that instruction
is not a distinct intervention. The new option changes which prior role states the actual
Reviewer request exposes.

Status: MODEL_FREE_PREPARATION_VERIFIED. No new experiment, execution plan, fit contact,
model generation, ASR, encoder or official score is admitted or performed here.
Keep the live maximum-five experiment and its frozen checkout unchanged.

## Exact behavior

Set native_episode.roles.reviewer.history_scope to latest-solver-and-local-tools.
The default is full. Other roles reject the restricted scope.

| Input or record | Restricted Reviewer behavior |
| --- | --- |
| Original query speech | Preserve the original base message and speech packet. |
| Current bound knowledge and task contract | Preserve the existing construction and supply. |
| Latest Solver state | Expose its complete original artifact, including the draft. |
| Earlier Perception states | Omit candidate IDs and their descriptions from request history. |
| Earlier drafts, Reviewer and Planner states | Omit them from request history. |
| Current Reviewer visit tool chain | Preserve each exact native call-source artifact and adjacent result, in order. |
| Earlier visits' tool conversations | Omit them from request history. |
| Complete episode trace and other roles | Preserve the full accumulated state. |

This is draft-visible review. It is neither draft-blind nor statistically independent.
Current knowledge selection can still depend on earlier candidates. The unchanged global
task contract can still contain examples. Removing Perception history also removes useful
hints in some cases; a benefit cannot be assumed.

The selector rejects duplicate identities, missing Solver state, missing or malformed
local results, foreign or old call sources, nonadjacent pairs and reordered results.
The existing shared framework renderer continues to validate source authority and exact
call/result custody. The selector does not reconstruct or rewrite those artifacts.

FlightRuntime records the nondefault scope in its native-role dispatch receipt.
Default configurations preserve the existing receipt fields. The shared request builder
uses the selected states for both the actual request fit and dispatch. Original speech,
knowledge supply, Solver answer authority and Planner routing authority remain unchanged.

Reviewer findings are declarations for interpretation and later analysis. This change does
not add an automatic mapping from issue JSON to routing. Planner still decides whether to
revise or stop; Solver retains final answer authority.

## Prepared configuration and comparison limits

Prepared option:
configs/baseline/slurp-native-reviewer-scoped-history-train-a-held-v1.json.

Its source control is the existing, unrun
configs/baseline/slurp-native-evidence-review-train-a-held-v2.json.
Only history_scope and the descriptive what_this_is field differ. The registered phase
program, episode identity, prompts, at-most-three candidates, knowledge, tool set, three
Reviewer iterations with a reserved final report, and one Solver revision are unchanged.
The shared loader accepts the option under phase-native-candidates-review-revise-v1 with
an eleven-contact per-sample ceiling. Acceptance is not proof of real-request capacity.

A future comparison against that exact structured-review control could isolate history
scope subject to matching source, configuration and population. Comparing the new option
against the historical anchor instead changes the structured-review package as well;
report a package effect in that case. No control or treatment launch is implied by this
preparation. Root selects one useful bounded contrast after the complete A1 verdict.

Do not silently combine this option with maximum-five candidates, the separate no-example
task-contract projection, revised knowledge values or new acoustic tools.

## Verification

The focused WSL suite passed 128 tests with zero skips. It exercises configuration loading,
actual shared FlightRuntime dispatch, OpenJiuwen role execution with mocked model transport,
speech custody, request-fit ordering, one and two local tool calls, revision visits,
full-history defaults, structured review declarations and request regressions.
These are synthetic transport tests, not a four-row scientific experiment.

Line coverage for native_episode_config.py is 93 percent. All 50 added production lines
classified as executable by coverage were executed. The runtime receipt dictionary
expansion has no independently classified added executable line; dispatch tests explicitly
assert scoped presence and default absence. Do not infer branch coverage from these counts.
Ruff, the engineering-base check and git diff --check passed.

The first verification receipt miscounted added executable lines as zero because its
diff-hunk regular expression was overescaped. Preserve that receipt and use its corrected,
hash-bound successor:

- DATA/coordination/slurp-review-measurement-v1/root-reviewer-history-scope-verification-v2.json
- SHA-256: 37da455659bc5fa5a08f93808c9ef6e0858a73ddd52108c625d038a841092fb9

The successor binds implementation, tests and configuration hashes, preserves the original
test result and records the measurement-only correction. Production and tests did not
change because of this metadata correction.

## Scientific evaluation after admission

Keep every row in official full-task scoring. Report before/after review saves, harms,
omitted supported entities, unsupported output fields, candidate-boundary escapes and
actual executed revisions. Compare intent choice on common-covered rows and show each
arm's own-covered denominator separately. Retain scenario strata and speaker-cluster
uncertainty. A shorter history, more criticism or more tool calls is not a quality gain.

Evaluate context restriction against its information loss: a corrected answer must remain
grounded in speech or admitted knowledge, while removed useful candidate evidence may
create new omissions. Separately investigate source-derived slot representation boundaries;
do not turn evaluation reference cases into runtime examples or memory.

This is an engineering capability for the SLURP agentic base. It is not a training-free RL
algorithm or evidence of stable system benefit over a matched direct-model baseline.
