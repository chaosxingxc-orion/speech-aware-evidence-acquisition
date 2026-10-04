# Bounded baseline learning iterations

This change runs a complete learning iteration through the shared `system_context_learning` seam. It adds algorithm scheduling, summary/semantic-experience flow, proposal import, qualified trial evaluation, optimization retention/rejection, continuation state and immutable failure history. The tests execute the actual code with synthetic callbacks and sources. No real learned prompt, learning result or efficacy claim is produced by this engineering change.

The worktree starts at `4c1f020b4` on `codex/context-learning-iterations`. Its authoring channel is the explicitly requested GPT-6.1 Sol subagent. Frozen capacity/structural workers, root preparation, old archives/allocations, exposure ledger, services, queue and STOP are untouched. Paid spend and actual model/tokenizer/proposer/scorer contacts are zero. The only external requests fetch two official GEPA source files at the already pinned commit; the supplemental manifest preserves the previous source manifest.

## API and external seams

```python
from speech_aware_evidence_acquisition.rails.system_context_learning import (
    ContextLearningCallbacks, run_context_learning_iteration, select_gepa_task,
)

decision = run_context_learning_iteration(
    archive,
    bindings=all_declared_initial_family_bindings,
    recipe_pin=exact_root_countersigned_recipe_pin,
    repo_root=repo_root,
    algorithm="tf-grpo-context-diversity",  # Or "gepa".
    iteration=registered_iteration,
    policies=ordered_four_complete_bundles,
    callbacks=ContextLearningCallbacks(
        summarize=authorized_individual_summary,
        compare=authorized_semantic_group_comparison,
        update_experience=authorized_semantic_experience_update,
        propose=authorized_policy_reflector,
        evaluate=root_owned_complete_family_evaluator,
    ),
    previous_decision_sha256=None,  # Exact prior archived decision for continuation.
)
```

The runner invokes only these injected functions. Each real function must separately enforce its admitted exposure, model/tool budgets, English input, exact model-request FIT, original response storage and runtime/scoring contracts. This runner supplies neither a provider client nor a second answering model, executor, flight launcher, retry, queue operation, server control or automatic next iteration. The callback tasks are structured source-addressed optimizer data, not a ready model-request body; use the existing request/context/compiler tools and retain provenance when assembling the actual request.

Every callback returns exactly `{value, provenance, usage}`. `provenance` is a nonempty English metadata object retaining the original request/response source identity. `usage` has exactly `provider_contacts`, `input_tokens`, and `output_tokens`, each a measured nonnegative integer or `null` when unavailable. A callable invocation can represent multiple underlying contacts. Invocation counts are never used as substitute provider-contact counts. If any stage's usage is unknown, the corresponding total remains unknown. Callback elapsed seconds are measured and retained separately from complete-system sample latency.

TF callback values are: one English rollout summary; one English semantic comparison; a validated list of add/delete/modify/keep experience operations; and one full-system context proposal per named system. GEPA invokes its single selected-component policy reflector. The evaluator receives the exact four trial bundle IDs, changed member labels, declared controls, cohort, fixed sampling and measurement envelope. It returns only `{bindings, recipe_pin}` for a prospectively registered, separately executed complete trial. It cannot return rewards, an acceptance boolean or a caller qualification flag. The runner reuses the shared complete-family reader to requalify that trial before deciding.

## Prospective plan and accounting

The existing root-countersigned context-learning protocol must pin an iteration plan. A common initialization protocol can use `iteration_plans` with exactly the two algorithm keys, so both learners reuse one qualified initialization family. A single-algorithm protocol can use `iteration_plan`. Both spellings together are refused. The plan is acyclic: it names the family and ordered sample commitment, not a reciprocal recipe hash.

The `saea-context-learning-iteration-plan-v1` fields are:

| Field | Value |
|---|---|
| `algorithm`, `iteration`, `input_family_id` | Exact registered algorithm, positive iteration and source family |
| `sample_ids_sha256` | Existing `content_hash` of the ordered first20 IDs |
| `selection_seed` | Explicit upstream selection RNG seed; default `0`, separate from decoding |
| `callback_caps` | Exactly `summarize`, `compare`, `update_experience`, `propose`, `evaluate`; nonnegative integer caps |
| `evaluation_candidate_trajectories_cap` | `80` |
| `evaluation_control_trajectories_cap` | `40` with declared seed/A/A, otherwise `0` |
| `acceptance` | `strict-registered-utility-sum` |
| `automatic_next_iteration` | `false` |

TF requires four proposal opportunities and one evaluation request; typical other stage caps are80/20/1. GEPA requires one proposal and one evaluation; unused summary/semantic caps may be zero. Caps bound callback opportunities, not hidden provider work. Their external contacts still need their separate original execution/proposer plans. Exhaustion or failure stops the iteration; no retry or quota replacement occurs.

`N20`, `K4`, full four-role policies, temperature0 and decoding seed`20260913` remain enforced by the existing qualified boundary. The initial80 candidate trajectories and optional40 controls are already acquired qualified evidence. Decisions label that reused family and its commitment explicitly; shared initialization must not be charged as a fresh runtime population once per algorithm. Each fresh trial reserves80 candidate trajectories plus separately counted controls before its evaluator callback. It retains the proposed child systems and exact unchanged others, with fresh run/attempt identities, the same ordered cohort, frozen reference and measured schedule. No-change proposals preserve the original active bundle IDs; no fabricated duplicate system fills K. A trial that collapses four prompt/assembly systems into identical runtime content is refused before evaluation.

## Algorithm behavior and fidelity

TF skips exactly constant utility groups. For each nonconstant input it invokes K individual summaries, then a semantic winner/loser comparison. It aggregates the comparisons into explicit experience operations and asks for four system-bound full-context proposals using the revised experience. Invalid/no-change proposals consume their opportunity, remain archived and preserve that member's original runtime system. A changed trial is evaluated as a complete N-by-K family. Experience and child systems become the next optimization state only when total registered utility strictly increases; rejected semantic drafts remain historical. There is no numeric z-score, PPO or gradient update.

This TF algorithm is explicitly the owner's deterministic distinct-context adaptation. The original paper samples the same policy/experience; this implementation varies complete contexts at fixed decoding. The pinned upstream math implementation's binary mixed-correctness filter is not used for continuous SLU utility. The quality-gated experience/context retention rule, sequential external callbacks, bounded no-retry failure handling and explicit role-text materialization are study adaptations. There is still no automatic runtime experience renderer. These differences are not labeled exact original TF-GRPO reproduction.

GEPA implements the pinned default instance-front selector: retain tied per-example best programs, remove lower-aggregate programs whose front coverage is already covered by remaining programs, then draw proportional to surviving front frequency. Its RNG state is persisted. The separate fixed decoding seed never changes. Component selection cycles per program through the four role texts and two supported assembly components; an accepted child inherits its parent's advanced cursor. The `StrictImprovementAcceptance` rule compares the sum of the proposed program's registered per-example utilities with its parent. Other systems remain present in trial custody and accounting. Pooled official SLU/intent, reliable completion, failures and all/non-first latency remain available in separate business rows without hidden weighted rewards.

The selector control flow is implemented against `gepa_utils.py` at commit`fb1ed589fd83372caef499cffc2c73173d3b096b`; synthetic tests compare selections directly with that hash-verified standard-library helper. The accepted program pool grows while K remains the number of runtime systems in a registered family. Prior pool/source families are freshly requalified, including controls, before they influence another iteration. Accepted and rejected proposals and earlier decisions remain immutable; rejected children never silently enter the parent pool. A historical selected parent absent from the current registered K family causes a pre-callback refusal. Root can use the pure `select_gepa_task` recommendation to prepare a prospective family containing that parent; the runner never substitutes another parent or dispatches it automatically.

GEPA parent selection, per-program cursor inheritance and strict-sum acceptance follow the pinned sources. Mapping assembly settings to two reflective components is the study's supported-component adaptation. Evaluating one whole registered N20 TRAIN replacement family substitutes for upstream minibatch acceptance followed by separate validation-set evaluation. The pool uses the latest source-qualified same-cohort utility observation for a program when root re-evaluates it. This is optimization exposure, not held-out validation. Merge search, upstream dataset/minibatch sampling, batched proposal selection strategies, caching, perfect-score skipping and full validation-set machinery are not claimed as reproduced.

Retention means **retained for optimization**, never scientific/formal adoption, stable benefit, guaranteed improvement or automatic scaling. TF uses total K-system utility for its explicitly declared study gate; GEPA uses its selected program's utility. Both use the original frozen official-seed utility `2TP - F_ref*(2TP+FP+FN)` and preserve false-positive penalties. No per-input F1 or latency-weighted substitute is introduced. Root still reviews the separate business measurements and any next runtime admission.

## Immutable history and remaining integration

The archive stores an iteration reservation, each consumed stage/task before invocation, each completed/failed JSON response with provenance and usage, original context-update records and a terminal decision under `context-learning/iterations/{algorithm}-{iteration}`. Non-JSON callback values retain their type and failed opportunity; the external callback must retain their original raw source. Duplicate iteration/update IDs refuse additional callbacks. Invalid outputs, no-change, regressions, partial failures and budget exhaustion are retained. Decisions commit continuation state; tampering is rejected before further callbacks. No operator is allowed to repair history by editing it or replaying spent calls.

Root still must connect admitted real English summary/reflection callbacks and actual whole-family runtime preparation/execution/scoring/READ callbacks, with their original plans/receipts and source-bound request FIT. Root owns GPU and structural admission, one complete standard score per member, policy compilation, serving/memory/lease checks and review between stages. The engineering code now executes the algorithm iteration, but no real learning iteration has been flown by this patch. Later N/K sizes, experience rendering, independent validation and scientific adoption remain separately reviewed. Human-before8x400, other-carrier holds and zero paid spend remain intact.

## Verification

TDD skill: `C:/Users/35686/.agents/skills/tdd-workflow/SKILL.md`. The first17 iteration tests failed on missing orchestration APIs; later history, duplicate-runtime-system and common-plan tests failed before their corresponding fixes. Tests exercise complete synthetic TF and GEPA iterations, invalid/no-change/regression consumption, usage/provenance, exact child/unchanged/control custody, reference/scheduling identity, state source requalification, RNG/cursor continuation, rejected-parent isolation and immutable replay refusal. Pinned source hashes and focused gate/coverage evidence are recorded beside this README. No real task answer or scientific quality was opened for this work.
