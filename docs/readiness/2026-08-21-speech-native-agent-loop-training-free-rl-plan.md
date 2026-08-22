# Speech-native AgentLoop training-free policy optimization plan

Date: 2026-08-21

Status: bounded discovery only; FINAL60 is blocked

## Decision

The speech-to-text-key route remains live, while the current AgentLoop candidate does not qualify for FINAL60. On unread GATE18, direct K0-M0 scores 15/18, the K1-M1 decision embedded inside M5 scores 16/18, and the observed M5-v2 controller scores 15/18. The controller therefore removes the one-point gain produced by maintainable text keys.

This is not an AgentLoop success result. It is evidence that the external controller has a non-degenerate optimization surface:

- OPT-B18 contains one helpful and one harmful escalation.
- GATE18 contains zero helpful, one harmful, two neutral, and three action-sensitive escalations.
- GATE18 also contains one wrong M1/M3 agreement that stops before alternate actions are observed.
- A model-free counterfactual policy requiring unanimous M3-order support scores 16/18 on the exposed GATE trajectories, versus 15/18 for the observed majority policy. This is post-read discovery and requires new validation.

Do not contact FINAL60. Do not claim that AgentLoop improves task accuracy. Do not discard the speech-native text-key hypothesis.

## Research boundary

Treat the frozen Omni decoder and text-key matcher as the environment. Optimize only the external controller over versioned discrete actions. Never update Omni, mmproj, embedding, retriever, verifier, or prompt-model parameters. Do not add a second answering model. Every model action must carry the original speech packet again.

Run every preprocessing, model-contact, resource-monitoring, and model-free read command inside WSL2. Use the native WSL workspace and ext4 feature/run roots; never launch an experiment from the Windows checkout or through a `/mnt/*` working directory. The Windows checkout may carry reviewed source changes, but it is not an execution environment.

This boundary borrows the environment/controller separation from SPARKLE, but rejects its learned proxy model because this repository forbids a task-trained second model. Adaptive-RAG also demonstrates why retrieval depth should depend on query state, but its trained complexity classifier is out of scope. PromptAgent supports search over discrete prompt states and actions with MCTS; here the search object is the controller policy rather than Omni parameters. AgentFly motivates non-gradient policy adaptation through memory, but only its non-parametric memory variant is admissible here.

Primary references:

- [SPARKLE: A Structured and Plug-and-play Agentic Retrieval Policy for Adaptive RAG Models](https://aclanthology.org/2026.acl-long.1793/)
- [Adaptive-RAG: Learning to Adapt Retrieval-Augmented Large Language Models through Question Complexity](https://aclanthology.org/2024.naacl-long.389/)
- [PromptAgent: Strategic Planning with Language Models Enables Expert-level Prompt Optimization](https://arxiv.org/abs/2310.16427)
- [AgentFly: Fine-tuning LLM Agents without Fine-tuning LLMs](https://arxiv.org/abs/2508.16153)
- [Language Agent Tree Search Unifies Reasoning, Acting, and Planning in Language Models](https://openreview.net/forum?id=njwv9BsGHF)

## Controller model

Use a finite-horizon, fully external control process.

### Runtime-legal state

- M1 selected key or parse failure.
- Canonical M3 selected key, ordered top-3 keys, verifier compatibility bits, verifier confidences, tie-arbitration use, and contact cost.
- Agreement relation between M1 and canonical M3.
- After expansion, reverse and rotate-7 M3 keys, order disagreement pattern, and cumulative budget.
- No gold label, reference transcript, future action outcome, or devel/test annotation.

### Actions

- `STOP_PRIMARY`: return M1.
- `EXPAND_ORDERS`: run reverse and rotate-7 M3 with the original speech packet.
- `OVERRIDE_MAJORITY`: return a two-order M3 majority.
- `OVERRIDE_UNANIMOUS`: return M3 only when all three orders agree.
- `RETAIN_PRIMARY`: keep M1 when support is insufficient.
- A later bounded probe may add `CONTRAST_PRIMARY_VS_M3`, but only after its prompt and contact ceiling are preregistered.

### Offline reward

Gold is available only after a completed discovery rollout and never enters runtime state. Prefer lexicographic constrained selection over a fragile single scalar:

1. maximize final correct count;
2. require correct-to-wrong relative to M1 to be zero when tied alternatives exist;
3. minimize parse failures;
4. minimize contacts, tokens, wall time, and GPU time;
5. prefer policies with stable action choice across speaker-isolated folds.

For algorithms that require a scalar, preregister all coefficients and report the unscalarized components:

`reward = correct - lambda_regression * primary_regression - lambda_parse * parse_failure - lambda_call * normalized_contacts`.

Never tune coefficients on the validation gate.

## Next bounded experiments

### A0 — action-support rollout on exposed discovery data

Use only already-exposed OPT-A36 and, if required, OPT-B18. Do not use GATE18 again for policy selection. Execute a full-branch M5 explorer that records M1 plus canonical, reverse, and rotate-7 M3 for every query, including initial M1/M3 agreements. This supplies counterfactual action support that the current disagreement-only log lacks.

The rollout must reuse the existing driver and matcher. Add a versioned exploration-policy field to M5; do not add an executable script. Full expansion is a data-acquisition policy, not the final serving policy.

### A1 — training-free policy search

Search a small, preregistered controller family:

- disagreement trigger versus verifier-margin trigger;
- majority versus unanimous override;
- primary versus canonical fallback;
- contact budget 6, 10, and 16;
- optional contrast action only if A0 shows unresolved recoverable errors.

Use exhaustive enumeration for the initial finite family. Use contextual bandits, MCTS, or non-parametric episodic retrieval only if the family expands beyond direct enumeration. The optimizer consumes logged discovery trajectories and produces a versioned policy table; it never changes model weights.

Use speaker-isolated cross-validation across the exposed discovery queries. Report mean accuracy, worst-fold accuracy, correct-to-wrong, helpful/harmful/neutral action counts, action coverage, and cost. A policy with no action variation or no reward spread is not optimization-ready.

Before any `DISCOVERY-X108` result is read, freeze the following model-free evaluator. Assign intact speaker groups to three folds by descending group size, SHA-256 speaker rank, and greedy lowest-fold load. Evaluate the finite trigger/aggregator family in every fold. In parallel, cross-fit `speaker-grouped-oof-observable-state-action-v1`: derive state only from primary/canonical agreement, M3 consensus, primary/majority agreement, and valid-vote count; compare primary, unanimous fallback, majority fallback, and the three order-specific predictions. For each held-out fold, learn the state action from the other two folds only. Require at least three training trajectories in a state and a strict correct-count gain over primary before selecting a non-primary action; otherwise use primary. Report out-of-fold accuracy and regressions, per-fold deltas, action counts, state reward spread, prediction variation, and a diagnostic per-query action oracle. The oracle is headroom evidence only and can never be frozen as a controller.

### A1x — conditional 100+ sample expansion

Do not expand by default. Expand only if the completed A0/A1 read cannot support a relative controller conclusion because the best admissible policy differs from M1 by fewer than three cases, the direction is not reproduced across at least two speaker-isolated folds, or fewer than five queries expose a helpful-or-harmful branch outcome.

If any trigger holds, freeze `DISCOVERY-X108`: six unused SLURP train queries per scenario, at least 108 queries total, isolated from all key material, OPT-A36, OPT-B18, consumed GATE18, and the future validation gate by utterance, audio, and speaker. Speaker isolation is across these sets; repeated utterances from one speaker inside `DISCOVERY-X108` are allowed and must stay in the same policy-analysis fold. Materialize its speech packets offline into the WSL ext4 feature root before starting the mmproj-free server. Run the same full-action policy-support rollout; do not introduce a new prompt, key representation, model, or action after reading it. `DISCOVERY-X108` remains discovery data and cannot serve as validation evidence.

The A0 read activated A1x: the best enumerated policy changed M1 by zero cases and only two queries carried a helpful or harmful full-branch outcome. `DISCOVERY-X108` is therefore the single authorized expansion. Its 108 packets must be promoted and validated in parallel before the inference server starts; sample count must not expand again during this stage.

### A2 — new unread train gate

After A1 freezes one policy, draw one new small GATE-C18 from unused SLURP train material with query/key/speaker isolation. Preprocess its packets offline before inference, then run direct M0 and the frozen policy once. Do not reuse GATE18 as validation.

If A1x is activated, increase this unread gate to GATE-C36 so the larger discovery search is not followed by a weaker 18-query validation. Keep the gate train-only, speaker-isolated, one-shot, and unread until every controller rule is frozen.

The frozen policy qualifies only if all conditions hold:

- final accuracy is at least M1 and strictly above same-run M0;
- correct-to-wrong relative to M1 is zero;
- no parse failure;
- at least one non-stop action occurs, unless every M1 decision is correct;
- the policy saves contacts relative to full expansion;
- the mmproj audit remains zero.

Only after A2 qualifies may the owner decide whether FINAL60 is still an appropriate bounded discovery read.

## GPU execution requirement

The current adaptive run fails the full-load gate because rare escalation creates a thin tail. Do not increase the sample set to manufacture utilization.

- Queue M1 and canonical M3 independently.
- Queue verifier candidates concurrently.
- Queue reverse and rotate-7 branches concurrently.
- For A0, fully expand all registered actions, which naturally provides enough same-sample branch work to fill 16 llama.cpp slots.
- Keep `-np 16 -c 65536 -b 2048 -ub 512`, queue depth 64, zero OOM, zero host spill, and zero request failure.
- Require request-active median utilization at least 95 percent, P10 at least 90 percent, and slot occupancy at least 90 percent before accepting the execution profile.

If the adaptive serving policy still has an unavoidable short tail after A0, report steady-state and tail utilization separately; do not redefine the registered whole-window gate after reading results.

If all three registered np geometries fail mechanically while their stable waves reach high utilization, permit one label-blind scheduler rescue after semantic read: keep np16 and every scientific byte fixed, raise the task queue to `8×np` so all 108 exposed X108 tasks can contribute ready contacts across stage boundaries, and inspect only mechanical serving fields. This cell cannot change or corroborate the scientific result. If it also fails the original whole-window thresholds, stop live profiling and refactor the existing dispatcher into an explicit global stage-ready state machine before any validation-gate contact.

## Claim boundary

The strongest current claim is:

> On one unread 18-query train gate, frozen speech-feature queries matched against maintainable text keys through the frozen Omni decoder outperform direct speech classification by one case at the embedded M1 decision level. The tested AgentLoop does not preserve that gain, but its logged actions produce distinct positive, negative, and neutral outcomes that support bounded training-free controller optimization.

Do not claim final superiority, generalization, or a validated AgentLoop improvement.
