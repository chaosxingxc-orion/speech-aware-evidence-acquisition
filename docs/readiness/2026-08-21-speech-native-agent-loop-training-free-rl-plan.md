# Speech-native AgentLoop training-free policy optimization plan

Date: 2026-08-21

Status: bounded discovery only; schema-v2 action topology is frozen for GATE-C36 construction; no controller is validated and FINAL60 remains blocked

## Decision

The speech-to-text-key route remains live, while the current AgentLoop candidate does not qualify for FINAL60. On unread GATE18, direct K0-M0 scores 15/18, the K1-M1 decision embedded inside M5 scores 16/18, and the observed M5-v2 controller scores 15/18. The controller therefore removes the one-point gain produced by maintainable text keys.

This is not an AgentLoop success result. It is evidence that the external controller has a non-degenerate optimization surface:

- OPT-B18 contains one helpful and one harmful escalation.
- GATE18 contains zero helpful, one harmful, two neutral, and three action-sensitive escalations.
- GATE18 also contains one wrong M1/M3 agreement that stops before alternate actions are observed.
- A model-free counterfactual policy requiring unanimous M3-order support scores 16/18 on the exposed GATE trajectories, versus 15/18 for the observed majority policy. This is post-read discovery and requires new validation.

Do not contact FINAL60. Do not claim that AgentLoop improves task accuracy. Do not discard the speech-native text-key hypothesis.

### DISCOVERY-X108 outcome

The preregistered expansion is complete. On 108 speaker-grouped discovery queries, K1-M1 scores 89/108 and the unanimous-fallback AgentLoop scores 90/108, with two wrong-to-correct and one correct-to-wrong changes. The one-case gain occurs in only one of three speaker-grouped folds; the other folds are unchanged. The preregistered out-of-fold contextual policy scores 87/108, with zero wrong-to-correct and two correct-to-wrong changes, and is rejected.

The action space is nevertheless non-degenerate: 31 queries are action-sensitive, seven observable states have reward spread, seven primary errors are recoverable by a recorded action, canonical top-3 reachability is 99/108, and the diagnostic action oracle is 96/108. These are optimization-headroom measurements, not a deployable policy. Freeze no controller, do not construct GATE-C36, and do not contact FINAL60.

### Knowledge-grounded semantic refinement interpretation

The owner premise is that decision-relevant information must be represented in the knowledge base. Treat a failure of that premise as a key-construction defect, not as a retrieval defect. Each maintainable text key must therefore expose the discriminative domain, operation, target, constraints, positive evidence, and contrastive exclusions needed to separate it from its nearest competing keys. Add an offline discovery-only oracle-pair coverage check before blaming the controller: present the frozen speech query with the gold key and a preregistered hard negative, and measure whether the frozen core can select the gold key. Gold remains outside runtime and the result only diagnoses whether key material is adequate.

The existing M2 already tests ungrounded semantic augmentation. It first creates free-form intent factors from speech and then carries both the factors and the original speech packet into key selection. On OPT-A36 it scores 28/36, equal to M1; relative to direct M0 it repairs four errors and regresses one, while M1 repairs three and regresses none. Semantic text is therefore action-sensitive but not yet net-beneficial. The next semantic action must ground the generated state in retrieved knowledge rather than asking the core to invent an unconstrained summary before seeing the key space.

Define the next loop as follows:

1. `RETRIEVE_SPEECH`: carry the original speech packet and retrieve a broad top-k from all text keys.
2. `BUILD_GROUNDED_QUERY_STATE`: carry the same speech packet plus only the retrieved key cards; return a strict `GroundedQueryStateV1` with candidate key ids, domain, operation, target, constraints, exclusions, unresolved ambiguity, and cited source fields. Do not request or retain a transcript.
3. `REFINE_WITH_SPEECH_AND_STATE`: carry the same speech packet, the structured state, and the complete text-key collection; retrieve again rather than selecting only from the first candidates.
4. `VERIFY_OR_BACKTRACK`: compare the refined candidates against the speech. Keep the first speech-only decision when the semantic state is malformed, unsupported by cited key fields, unstable under key order, or in conflict with direct speech evidence.

The generated state is advisory evidence, never a replacement query. Every model contact must carry the original speech packet. Use the same frozen Omni core for all steps, and keep the deterministic `key_id -> value_label` mapping outside the model.

Training-free RL operates over the external decisions `STOP_SPEECH_ONLY`, `BUILD_GROUNDED_STATE`, `REFINE_TOP_3`, `REFINE_TOP_5`, `CONTRAST_TOP_2`, and `BACKTRACK_TO_SPEECH`. Runtime state may include first-round key ids, verifier compatibility and margins, cross-order disagreement, structured-field presence, cited-field validity, first/second-round overlap, and cumulative contact cost. Logged discovery reward may use correctness, regressions, malformed-state penalties, and contact cost; gold never enters runtime. Required controls are semantic-state shuffle, drop-semantic replay, matched-state plus speech derangement, ordinary speech derangement, and key-text shuffle. No control or decision call may omit the original query feature required by its registered arm. A gain that survives only when the semantic state is matched but speech is deranged is a text-cascade result and is inadmissible.

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
- [JitRL: Training-Free Test-Time Reinforcement Learning](https://arxiv.org/abs/2601.18510)
- [Budget-Aware Evaluation of Active Retrieval-Augmented Generation](https://arxiv.org/abs/2607.24010)
- [AudioToolAgent: Agentic Audio Understanding](https://arxiv.org/abs/2510.02995)
- [DuplexSLA: A Duplex Speech-Language-Action Model](https://arxiv.org/abs/2605.20755)
- [llama.cpp continuous batching and slot behavior](https://github.com/ggml-org/llama.cpp/discussions/8567)

JitRL motivates a non-parametric memory of state, discrete action, and observed return, but this study does not alter logits or use a second model evaluator. Budget-aware active RAG motivates reporting marginal correctness relative to the no-refinement speech baseline together with realized action rate, harm rate, and cost. AudioToolAgent and DuplexSLA provide architectural evidence for iterative and concurrent tool/action scheduling, but their extra models, transcript-centered orchestration, training, or test-mini tuning are outside this repository's boundary. Only their control-loop and scheduling abstractions are reused.

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

### A1b — frozen post-read episodic action evaluator

The first X108 read exposed seven recoverable errors but rejected the preregistered coarse contextual policy. Before a second model-free read of the same sealed decisions, freeze `speaker-grouped-oof-episodic-action-advantage-v2`. It uses only runtime-legal telemetry already present in the decision file: M1 and canonical M3 key ids, their relation, the M1 rank in canonical top-k, compatible-candidate count, selected-candidate compatibility, verifier-margin bucket, and contact costs. It retrieves at most nine training-fold states at weighted Hamming distance at most three. A non-primary action requires at least five neighbors, estimated net gain at least two, and zero observed harmful transitions. Speaker groups remain intact in deterministic three-fold out-of-fold evaluation. The available actions are M1, unanimous/majority fallback, and canonical/reverse/rotate fallback. Report action counts, fold deltas, wrong-to-correct, correct-to-wrong, mean contacts, and the complete neighbor/action audit.

This evaluator is post-read method development. Its registered model-free read is `SAEA-SN-DISCOVERY-X108-EPISODIC-READ/attempt-20260822T073000Z-12a001`. It can reject the action family or justify a future validation candidate, but it cannot independently validate a controller, reopen GATE-C36, or contact FINAL60. It performs zero model calls and never reads a new split.

The registered read is complete and rejects this policy. It selects `primary` on 108/108 held-out queries and scores 89/108, exactly equal to M1, with zero wrong-to-correct and zero correct-to-wrong transitions. All three speaker folds have zero delta. Only 25/108 held-out states have the required five-neighbor support, and no non-primary action reaches the frozen net-gain threshold of two; the best estimated net gain is one on 14/108 states. Do not relax a threshold after reading. The result establishes that the current agreement/rank/verifier telemetry is too sparse or weakly discriminative for safe action selection. It does not reject training-free RL over a richer, knowledge-grounded semantic state. D500 remains blocked.

### A1c — knowledge-grounded semantic action support

Do not treat the old free-form M2 as the final semantic-refinement test. Refactor the existing matcher and stage-DAG dispatcher to support the four-stage grounded loop specified above; do not add a standalone experiment script. First exercise it on already-exposed OPT-A36 with full action logging and the required semantic controls. Freeze the state schema, prompts, top-k values, backtrack rule, and contact ceiling before contact. If it does not produce at least three action-sensitive cases or does not improve the discovery action oracle, revise key construction or the state schema locally rather than expanding samples.

The first matched action-support cell is frozen as `M6 / knowledge-grounded-semantic-refinement-full-action-v1`. It keeps K1 for both full-library retrieval passes, expands only the first top-3 candidates through the already-frozen K2 contrastive fields while building `GroundedQueryStateV1`, and then returns to the complete K1 collection. Every evidence quote must be an exact substring of a visible definition, positive example, or contrastive boundary, with at least one citation per first-round candidate; otherwise the loop deterministically returns the embedded M1 primary. The state contact alone has a 512-token output ceiling; all other contacts retain the selected 64-token profile ceiling. Top-k is three, verifier policy is contrastive-v2, the worst-case ceiling is eight contacts per query, dispatch is contact-level with np16 and queue depth 64, and no retry is allowed.

Run this cell once on the already-exposed OPT-A36. Before interpreting correctness, require 36/36 completed decisions, zero request/mmproj/model-binding failures, exact speech-packet carriage on every contact, and at least 30/36 mechanically valid grounded states. If state validity is below 30, the result is a prompt/schema engineering failure: inspect only parse and citation failure categories, preregister a bounded prompt successor, and do not conclude that semantic refinement fails. If validity passes, read the embedded M1 and refined actions together. Continue to semantic mechanism controls only if at least three decisions are action-sensitive or the recorded refined action increases the OPT-A action oracle. This matched cell is action-support discovery, not an effectiveness gate, and cannot promote D500 by itself.

The first matched contact completed through the resident np16 decoder service but failed this mechanical state gate. It completed 36/36 decisions and 108 contacts with zero request, initial-retrieval parse, OOM, host-spill, runaway, or mmproj failures. All 36 speech-only top-3 retrievals parsed, all 36 state contacts ran, and all 36 returned `backtrack:invalid-grounding`; zero state passed the strict citation parser, so no speech-plus-state retrieval or verification occurred and no correctness field was read. Request-active GPU median/P10 was 88/50 percent and slot occupancy was 82.26 percent because every task terminated at the same state barrier. The resident decoder remained healthy under the same PID after finalization.

The parse-only diagnosis authorizes exactly one local successor, `knowledge-grounded-semantic-refinement-schema-v2`. The first prompt omitted machine types and field enums: 34/36 responses were JSON objects with the exact top-level fields, but every citation used rendered title case while the parser required lowercase field ids, and 29/34 used a boolean ambiguity value while the parser required a string. Without reading correctness, schema-only normalization would make 17 responses citation-valid; the remaining nonexclusive defects are nine multi-example quotes, six incomplete candidate-coverage sets, two candidate-order changes, two excessive evidence arrays, and two invalid or truncated JSON objects. The v2 prompt therefore keeps the parser and all scientific inputs fixed while requiring the exact dynamic candidate-id array, four non-empty string scalars, exactly one citation per candidate in order, lowercase `definition` / `positive_examples` / `contrastive_boundary`, and one-source quotes that never contain the positive-example `|` separator. The same 30/36 mechanical gate remains in force; a second failure does not authorize correctness reading, threshold relaxation, sample expansion, or a semantic-method conclusion.

The schema-v2 contact demonstrates that the local prompt repair solved the state-construction defect: all 36 states pass the unchanged strict parser. It completed 269 model contacts with complete request/response/cost traces and no runtime failure, but its durable attempt remains ABORTED because the original completion gate incorrectly required one server-side feature-decode log message per contact. Exact trace audit proves original sample-bound speech-query carriage on 269/269 requests. The 256/269 log count is an expected resident prompt-cache effect, not missing speech: a full-prompt cache hit skips feature decoding and its associated log message. The attempt is not retroactively finalized and is not retried; no action or correctness result has been read. Future completion uses exact trace-carriage identity as primary evidence and retains feature-decode log counts only as auxiliary diagnostics. Before any effectiveness claim or A2 promotion, register a model-free admissibility/action-support decision for these ABORTED outputs or run the already-frozen policy on a fresh unread train-only gate; do not silently treat this attempt as finalized evidence.

### Recent primary evidence and local translation

The August 2026 design review uses recent primary sources as architecture evidence, not as imported claims of local effectiveness. [VoxMind](https://aclanthology.org/2026.acl-long.459/) formalizes an end-to-end spoken agent around observations, history, a dynamic local tool set, an explicit think-before-act state, and environment feedback; its training and auxiliary-LLM components violate this repository's frozen-core boundary, so only the control topology is adopted. [ToolOmni](https://aclanthology.org/2026.acl-long.1736/) similarly separates proactive tool retrieval from grounded execution, supporting a local text-key subset followed by full-library recovery, while its SFT/GRPO stages remain out of scope. [Stream RAG](https://arxiv.org/abs/2510.02044) shows that intermediate speech-conditioned tool queries can be revised and that recovery from an erroneous intermediate query matters; locally, every revision must retain the original speech packet and cite visible key fields instead of becoming a transcript cascade. [Audio2Tool](https://arxiv.org/abs/2604.22821) motivates a later complexity ladder from direct commands to compositional and multi-intent tool use, but its public evaluation set is not used for tuning here. [Tool Preferences in Agentic LLMs are Unreliable](https://aclanthology.org/2025.emnlp-main.1060/) makes key-description, order, and shuffle controls mandatory rather than cosmetic. Finally, [JitRL](https://arxiv.org/abs/2601.18510) provides the closest training-free optimization template: store compact `(state, action, return)` trajectories, retrieve local neighbors, estimate action advantages, and adjust the frozen prior without parameter updates. This repository initially applies that idea at the system action selector rather than decoder logits because llama.cpp does not yet expose a registered, auditable logit-bias contract for this multimodal path.

The resulting local state is `SpeechAgentStateV2 = {speech_packet_sha256, initial_top_key_ids, grounded_query_state, refined_top_key_ids, verifier_scores, ambiguity, calls_so_far}`. The action set remains finite and externally controlled: `accept_primary`, `retrieve_with_grounded_state`, `verify_candidate`, `expand_key_set`, and later `request_clarification` only on datasets with real dialogue feedback. Rewards remain offline and task-verifiable: final label/tool success, correct-to-wrong harm, contact cost, and invalid-state penalties. Generated text is advisory state, never a replacement query; every decision contact must carry the original speech packet.

Before reading any schema-v2 action vote, run the preregistered gold-free structural audit. It requires the exact four source hashes in the exposure ledger, the exact legacy completion-gate abort reason, 269/269 trace-carriage validity, zero mmproj/process failures, four structurally valid M6 steps per decision, and no split binding. At least three primary-versus-refined changes permits one fresh unread train-only effectiveness gate; fewer than three rejects the topology without reading correctness.

The structural audit passes exactly at the frozen threshold. It verifies 269/269 sample-bound speech-query contacts, 36/36 valid grounded states, zero label or gold access, and three primary-versus-refined action changes. Grounded refinement changes the initial candidate ranking on 10/36 queries, the candidate set on 2/36, and top-1 on 4/36. Nineteen trajectories use seven contacts and 17 use the registered optional eighth tie-arbitration contact. This is action-support evidence only: the source attempt remains `ABORTED`, `effectiveness_eligible=false`, and no prediction has been compared with gold. Freeze schema v2 and proceed only through a fresh unread train-only effectiveness gate.

### A2 — new unread train gate

Freeze `GATE-C36` before opening any new train item. Extend the committed X108 successor binding with seed `20260823`, split name `GATE-C36`, and exactly two unused queries per scenario. The extension must preserve every key byte and exclude all parent query and key-example audio identities, utterances, and normalized sentences, plus every key-example speaker. Materialize or promote all 36 packets offline before contact; prefer the existing WSL feature store and keep the resident decoder loaded. A missing packet fails closed and never authorizes online mmproj loading.

The first model-free binding attempt wrote no output because strict parent-query speaker isolation is infeasible after X108: the `cooking` scenario has zero remaining candidates under that constraint. Do not use test, synthetic speech, or another task to hide this dataset fact. Reuse of a parent discovery-query speaker is therefore explicitly admitted and audited for GATE-C36 while query/key speaker isolation and all exact query identity exclusions remain strict. This is safe for the frozen schema-v2 policy because it has no trained parameters and reads no X108 trajectory memory, but it narrows the claim: GATE-C36 can establish same-domain relative task effect, not unseen-speaker generalization. The binding must record the exact parent-query speaker overlap count.

The frozen binding contains 36 new query identities, preserves zero query/key overlap, and records 28 parent-discovery speaker identities in common. None of its 36 audio hashes is present in the existing SLURP legacy featcache or packet roots, so packet promotion correctly refuses online fallback and writes no packet. Keep the decoder-only inference service resident on GPU PID 600. Populate only the missing legacy cache entries through one receipt-pinned CPU sidecar on port 8081 with `-ngl 0 --no-mmproj-offload`; the sidecar may load the same frozen decoder file and fixed mmproj into host memory, must stop after exactly 36 label-free preprocessing contacts, and must never replace, stop, or mutate the GPU service. Then promote all 36 packets in parallel into the GPU service's existing feature root. This is the only admitted extra model load: it is required by genuinely missing offline features and is not repeated between scientific cells.

Run four preregistered cells through the same receipt-pinned always-on np16 decoder without reading any prediction between cells: direct matched M0, matched schema-v2 M6, schema-v2 M6 with the deterministic speech derangement, and schema-v2 M6 with deterministic key-text shuffle. The matched M6 trajectory contains the same-run K1-M1 primary, so do not run a redundant standalone M1 cell. Every M6 contact, including state construction, retrieval, verification, and tie arbitration, carries the selected speech packet. Use the existing stage-DAG dispatcher, queue depth 64, the unchanged K1/K2 cards, top-k three, strict citation parser, seven-contact nominal and eight-contact worst-case policy, and zero retries. The control mappings, plan hashes, packet identities, and all four attempt ids must be frozen before the first contact.

Read all four cells once and together only after each cell records 36/36 completed decisions, exact speech-query trace carriage on every contact, 36/36 valid grounded states for each M6 cell, zero request/parse/OOM/spill/runaway/mmproj failure, and a healthy unchanged resident-service PID. The matched topology supplies positive AgentLoop evidence only if all conditions hold:

- matched M6 is at least two correct decisions above its embedded M1 primary;
- wrong-to-correct relative to M1 is at least two and correct-to-wrong is zero;
- matched M6 is strictly above same-run M0;
- at least two decisions are action-sensitive;
- matched M6 exceeds speech-swap M6 by at least 8/36 and key-text-shuffle M6 by at least 6/36;
- mean matched M6 contacts remain below the existing full-branch M5 expansion.

Reject this frozen AgentLoop topology if matched M6 is at least two decisions below M1 or makes at least two correct-to-wrong changes. If the paired M6-minus-M1 delta is in `{-1, 0, +1}` with at most one correct-to-wrong change, record `RELATIVE-EVIDENCE-UNDERPOWERED` rather than success or failure and activate exactly one already-frozen expansion: `EFFECT-C108`, seed `20260824`, six additional unused train queries per scenario, drawn as an isolated successor of the GATE-C36 binding. EFFECT-C108 must keep the same model, service profile, keys, prompts, parser, action topology, controls, and reader; it may not be redesigned after GATE-C36 is read. Require net gain at least 3/108 over embedded M1, positive delta in at least two of three speaker-grouped folds, worst-fold delta at least zero, at most one correct-to-wrong change, zero parse failures, matched-minus-speech-swap at least 24/108, and matched-minus-key-shuffle at least 18/108 before promotion. This conditional 100-plus stage is the owner's authorized response to insufficient relative evidence; it is not a reason to touch test or FINAL60. D500 remains separately blocked.

GATE-C36 is mechanically closed without a correctness read. All four cells completed 36/36 decisions through the unchanged resident PID 600 with exact speech carriage on 845/845 contacts, zero request, final-decision parse, OOM, spill, runaway, or mmproj failure. Matched M6 and key-shuffle each produced 36/36 strict grounded states, but speech-swap produced 35/36: sample `slurp:train:013389:audio-1490109881` took the preregistered `backtrack:invalid-grounding` primary fallback after its state-construction response failed the strict parser. The old gate explicitly required 36/36 valid states in every M6 cell, so no prediction, action correctness, label comparison, or accuracy may be read and no cell may be rerun. Request-active GPU median/P10 remained below the unchanged full-load target: M0 84/80, matched M6 91/61, speech-swap 89/62, and key-shuffle 92/60 percent. This reinforces the existing conclusion that dependency tails, not sample count, remain the serving defect.

Activate the already reserved `EFFECT-C108` because the owner explicitly authorized a 100-plus train-only expansion when the current experiment cannot produce relative evidence. This activation is based only on the gold-free mechanical failure above, not on a result effect. Keep seed `20260824`, the same prompts, parser, keys, M6 policy, controls, resident decoder profile, and no-retry semantics. Freeze one clarification before any C108 contact: matched M6 must have 108/108 strict grounded states; control cells may take the already-frozen primary fallback after an invalid grounded state, and every such event is counted as a mechanism-degradation outcome rather than retried or silently discarded. Every cell must still have 108/108 final decisions, zero final-decision parse failure, exact speech carriage, zero request/mmproj failure, and a healthy unchanged resident PID. Read all four C108 cells only once and together. Retain the existing effectiveness thresholds: M6 minus embedded M1 at least +3/108, positive in at least two speaker folds, worst fold nonnegative, correct-to-wrong at most one, matched-minus-speech-swap at least 24/108, and matched-minus-key-shuffle at least 18/108. Any matched invalid grounded state, any final-decision parse failure, or any threshold failure rejects promotion. GATE-C36 stays prediction-unread permanently; FINAL60, D500, devel, and test remain blocked.

The first EFFECT-C108 M0 cell completed 108/108 decisions and stays correctness-unread. The schema-v2 matched cell then completed 108/108 final decisions and 815 contacts with zero request, final-decision parse, OOM, spill, runaway, mmproj, packet-binding, or speech-carriage failure; the original speech packet was present on 815/815 contacts and resident PID 600 remained healthy. Its grounded-state contract nevertheless passed on only 107/108 queries: one trajectory took the preregistered `backtrack:invalid-grounding` action after state construction. The frozen matched 108/108 requirement therefore fails before any correctness read. Do not inspect predictions, labels, action rewards, or a 107-item subset. Do not run the schema-v2 speech-swap or key-shuffle cells: once the matched cell is mechanically ineligible, those approximately 1,700 contacts cannot contribute to an admissible read. Record both controls as canceled before contact. The completed M0 and schema-v2 matched outputs remain permanently prediction-unread; neither cell is rerun.

Authorize one local control-plane successor, `knowledge-grounded-semantic-refinement-schema-v3`, based only on that mechanical failure. Keep the same EFFECT-C108 identities, K1/K2 card bytes, M6 topology, prompts, strict parser, top-k, verifier, aggregator, control mappings, resident service, and thresholds. Change only the state-construction request: use llama.cpp's OpenAI-compatible `response_format=json_schema` to constrain the exact candidate-id sequence, non-empty bounded scalar/list types, one evidence object per candidate, allowed field names, and quotes drawn verbatim from that candidate's visible key fields. The generated domain/operation/target/constraint text remains model-produced semantic state. Every state, re-retrieval, verification, and arbitration request still carries the original speech packet; no transcript query, parameter update, second model, retry, or parser relaxation is admitted.

Reuse the already-completed unread M0 cell as the direct baseline and register three fresh schema-v3 cells: matched, speech-swap, and key-text-shuffle. Run matched first. It must produce 108/108 strict grounded states, 108/108 final decisions, exact speech carriage, and zero request/final-parse/mmproj failure before either control starts. If it fails, stop without a result read. Controls retain the frozen primary fallback for an invalid grounded state and count every fallback as mechanism degradation. If all three cells are mechanically eligible, read M0 plus the schema-v3 cells exactly once under the unchanged thresholds: M6 minus embedded M1 at least +3/108, positive in at least two speaker folds, worst fold nonnegative, correct-to-wrong at most one, matched-minus-speech-swap at least 24/108, and matched-minus-key-shuffle at least 18/108. This successor is bounded prompt/control optimization on already-exposed train discovery data, not a validation claim; FINAL60, D500, devel, and test remain blocked.

The schema-v3 matched and both mechanism-control cells are mechanically eligible, but the original M0 cell is not: it completed 108/108 decisions and exact speech carriage with zero request/mmproj failure, yet two final label responses failed the frozen parser. No correctness was read. Permanently exclude that M0 attempt rather than scoring the two null decisions or dropping samples. Authorize one 108-call direct-baseline successor, `speech-native-json-copy-v4`, on the same already-exposed queries. Keep K0 labels, speech packets, instruction text, decoder, service, sampling values, and one-contact topology fixed; constrain only the `label` field to the frozen 18-label enum through llama.cpp JSON Schema. Require 108/108 parse-valid decisions and all existing runtime rails. The schema-v3 cells remain unread and are not rerun. Only after the M0 successor passes may the four eligible cells be read together once.

The first joint EFFECT-C108 read attempt failed closed before writing any report. The reader validated grounded-state citations against the original key cards even for the preregistered key-text-shuffle control, whereas that control had cited the deterministically rotated text that was actually visible at runtime. No output artifact, aggregate metric, threshold verdict, or sample prediction was surfaced. Repair only this model-free reconstruction rule: rebuild the same rotated visible cards before citation validation for `key-text-shuffle-v1`; retain the original key-id-to-label mapping for scoring. Commit `17acbb3` implements the WSL repair, and the speech-native unit suite passes 108/108 including a matched-plus-control regression. Register one replacement read attempt with the same four source hashes, binding, folds, comparisons, and frozen thresholds. This repair does not authorize a model contact, source rerun, threshold change, additional split, or sample-level inspection.

The replacement read completed once and wrote SHA-256 `6f7017fbe584c0cadccac0c48d091b0d2ec52b4fdbb83441c13abaddf923f40a`. Direct K0-M0 scores 77/108. The matched M6 trajectory's embedded speech-only K1-M1 primary scores 90/108, while the final grounded refinement scores 89/108. Relative to M0, final M6 changes 16 wrong decisions to correct and four correct decisions to wrong for a net gain of 12; the stronger embedded M1 primary is 13 decisions above M0. The grounded loop changes 12 primary decisions, recovering four primary errors but damaging five primary successes, so its final-minus-primary effect is -1. A per-query action oracle that accepts only the four helpful refinements reaches 94/108, four above primary; this is diagnostic headroom, not a runtime-legal controller. Speaker-fold deltas are 0, -1, and 0; positive-fold count is zero and worst-fold delta is -1. Harmful refinement is five, above the frozen maximum of one. Matched M6 exceeds speech-swap by 14/108, below the frozen 24 threshold, and exceeds key-text-shuffle by 89/108, above the frozen 18 threshold. Top-3 reachability is 100/108 for matched M6; all four cells have zero parse failures.

Therefore reject the current always-refine M6 controller and do not promote it to FINAL60, D500, devel, or test. Do not reject speech-native text-key matching: its same-trajectory M1 primary materially exceeds direct label classification on this bounded discovery split, and key-text shuffle collapses both primary and final accuracy to 0/108. The speech-swap control drops final accuracy from 89 to 75, establishing speech sensitivity but not the stronger preregistered mechanism threshold. The four helpful and five harmful refinement transitions constitute offline action-reward support for a conservative training-free controller; they do not themselves validate such a controller. Any successor must choose among stop-at-primary, build-state, re-retrieve, verify, accept-refinement, and backtrack using speaker-grouped out-of-fold discovery, with the frozen core, original speech packet, and text keys unchanged.

## Progressive scale ladder

The current 108-query rollout already satisfies the owner's permission to expand beyond 100 when smaller evidence is underpowered. Do not expand again merely to increase GPU utilization or narrow a confidence interval around a non-improving policy.

1. `D108 — action qualification`: a single preregistered out-of-fold external policy may request promotion only with net correct gain at least 3/108 over M1, positive delta in at least two of three speaker folds, worst-fold delta at least zero, at most one correct-to-wrong transition, zero parse failures, non-primary action rate between 5 and 50 percent, and fewer mean contacts than full expansion. Existing unanimous and coarse contextual policies do not pass.
2. `D500 — bounded train-only development`: this requires an explicit owner-approved successor contract. Use 360 speaker-isolated train queries for policy memory/calibration and keep 140 train queries as an unread internal holdout. Freeze keys, prompts, action set, thresholds, cost coefficients, and packet identities before reading the 140. Promote only if the holdout is net positive, correct-to-wrong is at most one percent, direction is nonnegative across preregistered speaker/scenario strata, all mechanism controls pass, and cost remains below full expansion.
3. `V1000+ — baseline lock`: this is Stage-3 paper-scale work and is prohibited in this repository. It requires `OWNER_GO_AND_PAPER_EXECUTION_CONTRACT` and a standalone `papers/<slug>` carrier. Test remains untouched during optimization. Only a stable gain on a 1,000-plus preregistered validation cohort may lock a large-scale engineering baseline; it still does not by itself establish final superiority or generalization.

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

The q128 rescue and the first global-branch refactor are complete and both fail the unchanged whole-window gate. The global-branch run completes 108/108 decisions and 1,599 contacts with zero request, parse, OOM, host-spill, runaway, or mmproj failure. Slot occupancy reaches 90.57 percent, but request-active GPU median/P10 is 89/60 percent and aggregate throughput is 1,209.47 tokens/s. The process audit records zero mmproj hits. Stop live profiling. The next engineering change must be model-free: replace blocking branch jobs with a persistent dependency-aware stage DAG whose ready queue applies bounded backpressure while preserving retrieval-before-verification causality and deterministic trace order. Revalidate it with tests and replay before preregistering any further model contact.

The explicit stage DAG is now implemented in the existing dispatcher. It uses one persistent contact executor, admits ready nodes only up to queue depth, creates verifier nodes only after retrieval completion, carries the original speech packet in every node, propagates a failed contact without retry, and merges traces deterministically by task, branch, and stage. A model-free latency replay completes 12 tasks and 120 contacts, reaches all four simulated slots across stage transitions, and loses no outcome. The complete WSL regression passes. This closes the code/replay prerequisite but does not authorize another live GPU profile; any such contact still needs a new exposure row and must keep semantic bytes isolated.

## Claim boundary

The strongest current claim is:

> Frozen speech-feature queries can be matched directly against maintainable text keys through the frozen Omni decoder without loading mmproj at inference. One unread 18-query train gate shows a one-case K1-M1 gain over direct speech classification, while the larger 108-query discovery rollout shows only a one-case AgentLoop gain that is not reproduced across speaker-grouped folds. Logged actions expose seven recoverable primary errors and a seven-case diagnostic oracle gap, so training-free controller optimization remains technically motivated, but no controller is validated or ready for a new gate.

The stronger current EFFECT-C108 observation supersedes the operational part of that statement: embedded K1-M1 reaches 90/108 versus 77/108 for K0-M0, but the grounded always-refine M6 policy falls to 89/108. Its fold deltas versus M1 are 0/-1/0, and it makes four helpful versus five harmful refinements. Key-text shuffle collapses to 0/108, while speech swap reaches 75/108. This supports speech-native matching against maintainable text knowledge as a bounded discovery result, rejects the current AgentLoop controller, and leaves training-free action selection as an unvalidated optimization direction.

Do not claim final superiority, generalization, or a validated AgentLoop improvement.
