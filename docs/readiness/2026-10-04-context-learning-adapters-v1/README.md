# Offline context-learning baseline adapters

This change adds a usable optimizer-input and supplied-update boundary on the existing shared base. It executes no learner, reflection callback, model request, flight, tokenizer, scorer or automatic scaling. Synthetic tests establish engineering behavior only. They are not learning results, efficacy evidence or runtime admission.

The authoring channel is the human-requested GPT-6.1 Sol engineering subagent. The four Sol systems remain root-known initialization. They are not blind proposals, learned updates, old Astra replacements or compute-matched historical allocations. Old proposal archives and allocations remain unchanged.

## Contract and qualification

`N` counts distinct inputs, `K` counts distinct complete prompt-and-assembly systems, and `M` is Perception/Solver/Reviewer/Planner. This entry admits only the initial `N=20`, `K=4`, `M=4` contract. Candidate exposure is 80 complete trajectories, with 320 initial node visits if all complete. Tools and revisions add visits; failures may end before completion. A separately declared unchanged seed and same-chain A/A add 40 control trajectories, making the complete family 120 trajectories. There is no additional candidate-count multiplier. Algorithms, iterations and separately declared controls have their own accounting.

Every system uses temperature zero and seed `20260913`. Context variation supplies diversity. All candidate bundles preserve the same seed configuration, knowledge, construction instruction, construction receipt and supply. Only full role texts and implemented `context_layout`/`node_context` settings are editable. Unsupported compression, progressive loading, parser/tool/dataset/answer-authority changes and knowledge edits are rejected.

`prepare_context_optimizer_input` accepts no cached feedback or caller qualification flag. It:

1. Reads hash-pinned recipe, registration, prospective protocol, deterministic owner receipt and ordered same400 TRAIN roster. It requires the exact first20 prefix, four distinct candidate bundle IDs, all declared members and independent run IDs. Optional controls have the exact names `seed` and `seed-aa`, with identical bundle IDs.
2. Reuses `scripts/system_text_search.py::require_read_registration`. Both the current recipe and the declared original reference source require the existing unique, zero-call, discovery, unambiguously root-countersigned READ ledger row and exact recipe pin. This adapter never countersigns or writes exposure records.
3. Reuses the sole successful complete-score metadata checker and `_read_complete_evidence`. Every declared candidate and control must pass operational identity, FINALIZED state, cohort, verified seal and complete official-count checks. All members' measured timing reports and common serving session are validated before candidate projection. Both mean-all and non-first means remain available. Failures, abstentions, missing usage and ineligible efficiency measurements remain recorded.
4. Requalifies the pinned original initial TRAIN seed/seed-AA reference through the shared `read_family` gate. It accepts only an initial source spec with exactly `seed`/`seed-aa`, an explicitly selected seed reference and no recursive substitute. It requires the resulting original reference to contain at least400 unique TRAIN IDs, its source commitment and valid zero-to-one frozen F1. Blind, milestone, test or caller-entered references are refused.
5. Rechecks READ/job metadata and source pins, then creates exact ordered N-by-K candidate groups. Controls stay in complete-family commitments and budget accounting. Each rollout ID commits sample, candidate, bundle, run, attempt and config identity. A packet never grants runtime or read authority to a later dispatch.

The shared legacy `CompleteSystemFeedback.from_family` minimum400 gate and legacy proposal parser are unchanged. This is a separate opt-in schema. The new entry returns the same `CompleteSystemFeedback` type inside shared custody processing; it does not weaken older pilot, L/B isolation or successor-panel rules.

## Prospective source materials

Root must prepare and review these immutable source documents before calling the input boundary. No real protocol or READ row is created by this engineering patch.

The prospective protocol schema is `saea-context-learning-protocol-v1`, with fields:

| Field | Required value or source |
|---|---|
| `family_id`, `iteration` | Separate new family and positive iteration, never an old L/B slot |
| `N`, `K`, `M` | `20`, `4`, ordered lowercase four-role list |
| `candidate_members` | Ordered four distinct candidate labels |
| `control_members` | `[]` or `["seed", "seed-aa"]` |
| `sampling` | `{"temperature": 0, "seed": 20260913}` |
| `owner` | Relative SHA-256 pin to the deterministic owner receipt |
| `fixed_roster` | Relative SHA-256 pin to the existing UPDATE2 ordered400 roster |
| `frozen_reference` | Relative SHA-256 pin to the original fully registered initial TRAIN family spec |
| `algorithms` | `["tf-grpo-context-diversity", "gepa"]`, explicitly permitting shared initialization feedback |
| `measurement_profile` | Existing `saea-system-search-measurement-v2`, sequential trajectory, four slots/queue4 |
| `automatic_expansion`, `independent_validation` | Both `false` |

The registration schema is `saea-context-learning-registration-v1`. It contains `family_id`, the exact `protocol` pin, `member_bindings`, `expected_members`, `read_id`, `measurement_profile`, and `registration_sha256`. Bind each declared member to its original `run_id`, `attempt_id`, `config_hash` and `bundle_id`. `expected_members` is the complete member-to-run mapping. Compute `registration_sha256` with the existing `content_hash` over the registration excluding that field.

The recipe schema is `saea-context-learning-analysis-v1`. It contains `family_id`, identical `expected_members`, ordered first20 `sample_ids`, `required_rows_per_member:20`, `run_ids.read`, identical `measurement_profile`, and the exact `context_learning_registration` pin. Root must prospectively countersign the corresponding shared READ ledger row against this exact recipe. Each binding passed to the API has the existing `candidate_id` and reward-link `config` structure, with pinned manifest/construction-roster/complete-score sources and official TRAIN projection. The ordinary shared READ preparation remains responsible for constructing those sources; the adapter does not score or manufacture them.

All source pins use existing `{relpath, sha256}` validation confined to `repo_root`. Large policy ancestry and feedback remain in the data root. Initialize a fresh optimizer archive with the complete approved policy ancestry using existing archive imports before preparing inputs. Candidate bundles can be loaded from that archive; the boundary revalidates each bundle against its archived parents. An isolated optimizer archive is preparation, not runtime registration.

## Integration API

```python
from speech_aware_evidence_acquisition.rails.system_context_learning import (
    prepare_context_optimizer_input,
    record_context_update,
    apply_experience_operations,
)

tf_packet = prepare_context_optimizer_input(
    archive,
    bindings=complete_declared_family_bindings,
    recipe_pin=exact_countersigned_recipe_pin,
    repo_root=repo_root,
    algorithm="tf-grpo-context-diversity",
    iteration=registered_iteration,
    policies=ordered_four_candidate_bundles,
    experiences=current_english_experience,
)
gepa_packet = prepare_context_optimizer_input(
    archive,
    bindings=complete_declared_family_bindings,
    recipe_pin=exact_countersigned_recipe_pin,
    repo_root=repo_root,
    algorithm="gepa",
    iteration=registered_iteration,
    policies=ordered_four_candidate_bundles,
    candidate_id=selected_per_example_front_parent,
    component="role_text.reviewer",
)
# A separately authorized reflector or reviewed human supplies the response.
record = record_context_update(
    archive,
    input_sha256=tf_packet["input_sha256"],
    update_id="reviewed-update-1",
    proposal_document=english_context_proposal,
    experience_operations=reviewed_semantic_operations,
)
```

No CLI dispatch command is added. The API writes create-only records under `context-learning/inputs/{algorithm}-{iteration}.json` and `context-learning/updates/{algorithm}-{iteration}-{update_id}.json`, using `SystemSearchArchive` alongside its ordinary policy store. Inputs include full four-role policies, candidate groups, verified frozen reference, separate measured business rows, source/read commitments and budget accounting. Two algorithms have separate packet identities. Inputs can be prepared only once per algorithm/iteration in an archive.

`TextPolicyUpdateProposal.from_context_json` opts into `saea-context-policy-update-proposal-v1`. The exact payload fields are `schema`, `algorithm`, `iteration`, `candidate_id`, `component`, `parent_ids`, `changes`, `rationale`, `hypotheses`, and `evidence`. It has no `branch`, `round` or `slot`. `evidence` must be exactly `[input_sha256]` at import. `parent_ids` must contain the selected evaluated full-system bundle. TF uses `component:"joint-system"`; GEPA uses one of `role_text.perception`, `role_text.solver`, `role_text.reviewer`, `role_text.planner`, `context_layout`, or `node_context` and can edit only that selected component. Role values remain complete English instruction texts.

The update record preserves the supplied raw proposal and semantic operations even when invalid. A valid changed bundle is `provisional`, an identical runtime policy is `no-change`, and invalid payloads are `invalid`; none is adopted or runtime-admitted. The shared `apply_text_proposal` materializer retains parent, complete feedback exposure and proposal ancestry. An ancestry-only new bundle is classified as no runtime change. Invalid updates never obtain a child policy. A repeated update ID is refused rather than overwritten. Supplied offline payloads are not proof that a model produced or learned them; real reflection calls still need their own original contact/provenance receipts.

## Distinct algorithm behavior and remaining work

Both learners use the existing registered trajectory utility
`u = 2TP - F_ref * (2TP + FP + FN)`, with word/char counts combined and `F_ref` frozen from the qualified original official seed source. Empty-entity false positives yield negative utility. The official pooled SLU/intent numbers remain separate; per-input F1 does not replace this reward. There is no z-score or PPO update rule.

TF-GRPO packets retain every input group. Exactly equal utility produces `skip-zero-variation`, with no summary/advantage task. Nonconstant groups request an individual summary per rollout followed by a supported semantic comparison of winners and losers. The contract calls for add/delete/modify/keep experience operations. Supplied operations are validated and saved with before/after state, including invalid attempts. A wholly constant family cannot invent an advantage-based edit. Current experience storage is optimizer-only: no experience renderer exists. To affect runtime, a reviewed experience insight must become explicit role-text/assembly changes and a newly compiled bundle.

This is explicitly the owner's deterministic context-diversity TF-GRPO adaptation. The original paper/code samples multiple trajectories from the same policy/experience; these groups instead contain K distinct frozen context systems at temperature0. The pinned upstream binary mean-between-zero-and-one filter is not copied into continuous SLU feedback. There is no claim of exact original-paper reproduction.

GEPA packets expose the best/tied candidates separately for each example and require a chosen parent from the union of that front. This is separate from the pooled-quality/latency business measurements. A reflective task contains one selected component, the complete parent and retained feedback. The original GEPA selector/engine can supply parent/component decisions through this seam; this patch does not reproduce its sampling probabilities, acceptance engine, evaluation cache, held-out front or full search loop. Current initial inputs are TRAIN optimization exposure, never held-out validation.

Before actual learning, root still needs a reviewed prospective common-feedback protocol/registration/READ package, admitted exact runtime configs and own supplies, capacity/structural proofs, whole-family executions and one official complete score per member. After qualification, separately authorize and meter English trajectory summarization/reflection calls, preserve their raw responses and failures outside Git, validate supplied semantic operations/component proposals, compile each provisional bundle through the existing compiler, and prospectively evaluate/retain/reject it through the same shared runtime. Learner iteration policy, reflection-call budgets, GEPA selector/acceptance scheduling, runtime experience rendering, new reviewed N/K stages and final adoption are not implemented here. There is no fabricated learned prompt or efficacy claim.

SkillOpt remains an organization/edit-history reference only. No third learner or hidden hybrid is introduced. All later sizing remains reviewed; N400 and human review before8x400 are not bypassed.

## Source and verification evidence

The deterministic owner receipt and source manifest are already registered at `docs/receipts/owner/2026-10-04-deterministic-context-rollouts.json` and `docs/readiness/2026-10-04-deterministic-context-baselines-v1/reference-sources-v1.json`. Inspected source bytes under the manifest's data-root reference directory match the pinned hashes: TF-GRPO `math/experience.py` (`7c859225…`, commit `7612f860a2314c015573adc742f82157b0d66a6f`); GEPA `candidate_selector.py` (`c2565e25…`), `core/state.py` (`6872c464…`) and `reflective_mutation.py` (`2fcc6681…`, commit `fb1ed589fd83372caef499cffc2c73173d3b096b`). They establish the individual-summary/semantic-experience seam and separate per-example/component-reflection behavior.

The TDD skill used is `C:/Users/35686/.agents/skills/tdd-workflow/SKILL.md`. Tests preceded implementation: the initial missing-adapter import failed; later required semantic-history, control/session timing, blind-reference and source-recheck tests failed before their fixes. The suite uses synthetic counts and files only. Actual shared READ ledger refusal, complete-family operational checks, seal-before-count ordering, successful-score completeness, invalid/no-change records, full four-role materialization, deterministic settings, source pins, all-member latency and legacy rejection paths are covered. Focused results and precise changed-versus-aggregate coverage are recorded in `validation-v1.json` alongside this document. No actual task answer, quality file or scientific result was opened for this patch.
