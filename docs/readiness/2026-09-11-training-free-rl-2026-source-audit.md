# 2026 training-free RL: implementation audit for the speech control plane

Date: September 11, 2026. Authority: OWNER-SLURP-FIRST-2026-RL-015. Scope: primary-source literature and static author-linked code inspection, not benchmark reproduction. Root reviewed the decisive update and acceptance paths. No upstream package was installed, imported or executed, and this review made no experimental model contacts.

## Decision

Keep 2025 Training-Free GRPO as the engineering baseline. OWNER-MULTIMODAL-SYSTEM-FIRST-016 supersedes the earlier premature EvoTool-first selection: choose the complete tool/memory/control system before choosing its optimizer. EvoTool remains a targeted module-evolution candidate; classify it as reward-guided gradient-free evolution, not Q-learning or literal GRPO.

Keep MemRL as the narrow RL comparator for experience/evidence selection after a useful experience store exists. MemQ is a later structural-credit extension, particularly relevant if E21 has a genuine provenance graph. JitRL remains a candidate for action-value reranking after its API and numerical semantics are qualified. Use SkillOpt's bounded-edit/validation pattern as an engineering reference, not a second framework. Do not implement all methods before launching the first shared feedback loop.

The [complete multimodal system specification](2026-09-11-multimodal-task-agent-system.md) governs execution order. No cited method establishes speech transfer by its published non-speech scores.

## What is actually training-free?

Frozen core weights do not mean nothing changes. These methods update external memory values, action statistics, textual policies or inference sampling. Distinguish those objects and feedback paths. Ordinary retrieval with no reward update is not demonstrated RL; prompt evolution with a fitness score is not automatically a temporal RL algorithm. A frozen-policy evaluation must not keep updating from its own ground truth.

| Method | First public paper / venue | Mutable object and actual mechanism | Place in our work |
|---|---|---|---|
| Training-Free GRPO | October 2025 | Grouped rollouts, contrastive feedback, external experience edits | Engineering baseline, explicitly adapted |
| MemRL | January 6, 2026 | Episodic-memory Q/utility metadata and value-aware retrieval | Narrow ORG/SUPPLY RL comparator |
| JitRL | January 26, 2026 | Retrieved action advantages and external candidate reranking | Later Planner candidate; numerical/API qualification needed |
| ETS | January 29, 2026 | Energy-guided sampling with Monte Carlo estimates | Not selected for the API-only control-plane base |
| EvoTool | 2026; ACL July 2026 | Blame-directed single-module text mutation, reward acceptance and population selection | Modular system optimizer candidate after system selection |
| MemQ | May 8, 2026 | Memory Q updates with provenance-path credit and value-guided retrieval | Later memory-credit extension |
| SkillOpt | May 22, 2026 | Bounded text-skill edits, validation selection and slow updates | Update-lifecycle reference; gate caveat below |

Dates identify first submissions where stated, rather than mistaking a 2026 revision or conference for a new 2026 method. Each row is supported by its primary paper and pinned implementation below.

## MemRL: a real external value update, with a short-horizon default

[Paper](https://arxiv.org/abs/2601.03192); [official repository](https://github.com/MemTensor/MemRL). Pinned commit: c1b322ca43de36ddf64c6712f89d0095bfc35ce0. MIT.

The inspected [value update](https://github.com/MemTensor/MemRL/blob/c1b322ca43de36ddf64c6712f89d0095bfc35ce0/memrl/service/value_driven.py) updates stored utility toward reward plus a discounted next value. Defaults are alpha 0.1, gamma 0.0 and success/failure rewards +1/-1. The inspected selector orders by Q and then similarity, with epsilon-greedy exploration; the mere presence of weight_sim/weight_q fields does not establish a weighted-score selector.

MemoryService.update_values receives caller-supplied success booleans; it does not supply our official reward bridge. Optional textual memory rewriting is distinct from the metadata update. The upstream constructor also expects LLM/embedding providers.

Interpretation: a good minimal memory-utility mechanism, but its gamma-zero default does not demonstrate long-horizon credit. Reuse source-bound strategy memories and post-seal numeric feedback; freeze before evaluation. Do not import benchmark runners or answer-bearing reference memories.

## EvoTool: the closest modular policy-optimization fit

[ACL paper](https://aclanthology.org/2026.acl-long.2016/); [official repository](https://github.com/SYang2000/ACL_2026_EvoTool). Pinned commit: 6a82719ea6e22cf23f963078e2527094e50b47f6. MIT.

The code represents Planner, Selector, Caller and Synthesizer as separate prompt specifications. [Policy.with_module](https://github.com/SYang2000/ACL_2026_EvoTool/blob/6a82719ea6e22cf23f963078e2527094e50b47f6/src/policy/modules.py#L31) changes only the selected module and policy ID. The [evolution loop](https://github.com/SYang2000/ACL_2026_EvoTool/blob/6a82719ea6e22cf23f963078e2527094e50b47f6/src/evolve/loop.py#L157) produces a blamed target, mutates it, and admits the child only for strictly higher mean reward.

The default admission comparison uses the training mini-batch. Held-out S_sel is used for population selection; do not call the ordinary child gate a held-out test. A selection-set gate is an explicit option. Repeated selection-set use still constitutes optimization.

Interpretation: use its targeted mutation/attribution principle on our already defined components, beginning with SUPPLY policy. Preserve fixed I/O and runtime authority. Its four modules do not map one-to-one onto OBS/ORG/SUPPLY/USE, and we should not manufacture four new model calls. Blame and mutation must use registered roles of the same frozen core and legal trace projections. This is an adaptation, not a reproduced EvoTool benchmark.

## JitRL: distinguish the paper's logit formula from released action scoring

[Paper](https://arxiv.org/abs/2601.18510); [official repository](https://github.com/liushiliushi/JitRL). Pinned commit: 143d22185d95fbf633a0befe6861d5e8b732543b.

The paper derives a log-prior plus advantage adjustment. In the inspected [Jericho implementation](https://github.com/liushiliushi/JitRL/blob/143d22185d95fbf633a0befe6861d5e8b732543b/Jericho/src/jitrl_agent.py#L375), the option token log probabilities are exponentiated, normalized advantage is added to probability (or verbalized confidence), and argmax chooses the action. WebArena implements the same broad scoring pattern. Those operations are not the literal logit-plus-advantage softmax policy in the derivation.

This released path can rerank finite actions outside a core; it does not prove we need internal weight access. It does need reliable option scoring or a separately qualified confidence variant. Preserve the distinction between confidence and probability. Do not open a new LP-2 probe implicitly.

The inspected complete tree contains MIT text at Jericho/LICENSE, but no root LICENSE; whole-repository license scope is not established by that nested file. Static findings do not reproduce the published benchmark result or inherit the theoretical guarantee for the code's alternate score.

## MemQ: structural memory credit, with additional complexity

[Paper](https://arxiv.org/abs/2605.08374); [author-linked repository](https://github.com/jwliao-ai/MemQ). Pinned commit: 9d66abf4f0252b084f088d5081c44b840842e47b. MIT.

The inspected [memory service](https://github.com/jwliao-ai/MemQ/blob/9d66abf4f0252b084f088d5081c44b840842e47b/memq/service/memory_service.py#L584) propagates credit through bounded provenance paths with gamma-times-lambda decay. The edge update uses reward plus discounted child Q minus parent Q. Candidate retrieval combines similarity and normalized Q, then applies epsilon-greedy selection. This weighted score is verified here; it must not be attributed to the different inspected MemRL selector.

Interpretation: provenance credit is relevant to later local-context/speaker-memory composition, but its memory graph is not automatically a temporal conversation model. There is little reason to add that graph to the first binary SLURP routing seam. Test simpler memory utility first.

## SkillOpt: useful validation discipline, with an ungated path

[Paper](https://arxiv.org/abs/2605.23904); [official Microsoft repository](https://github.com/microsoft/SkillOpt). Pinned commit: 79124b37e9a6371e13b753f8bcd7adb1e493ade1. MIT.

The normal candidate path evaluates valid_seen and the [gate](https://github.com/microsoft/SkillOpt/blob/79124b37e9a6371e13b753f8bcd7adb1e493ade1/skillopt/evaluation/gate.py#L200) requires strict improvement. But ordinary gating is configurable, and [slow_update_gate_with_selection defaults false](https://github.com/microsoft/SkillOpt/blob/79124b37e9a6371e13b753f8bcd7adb1e493ade1/skillopt/engine/trainer.py#L1084). At epoch slow update the default branch force-injects guidance into current_skill without validation, while preserving best_skill. Therefore the blanket description that every edit is improvement-gated is too broad for the inspected defaults.

Interpretation: useful bounded edits, rejected-edit history and frozen validation lifecycle. Do not inherit unconditional slow updates or assume repeated validation is independent evaluation. The upstream separate optimizer model is not automatically admitted by our frozen single-core setup.

## TF-GRPO baseline and ETS exclusion

[TF-GRPO paper](https://arxiv.org/abs/2510.08191); [official branch](https://github.com/TencentCloudADP/youtu-agent/tree/training_free_GRPO). Pinned commit: 7612f860a2314c015573adc742f82157b0d66a6f. MIT. The training_free_grpo/train.py loop generates grouped rollouts and passes them to ExperienceUpdater. The math updater contrasts outcomes, then adds/revises/merges textual experience. The default given_ground_truth=True can place the ground-truth answer in reflection prompts. That default is incompatible with our boundary. Use score-only feedback, legal trajectories and the same frozen core; record the changed adaptation instead of claiming byte-identical reproduction.

[ETS paper](https://arxiv.org/abs/2601.21484); [official repository](https://github.com/sheriyuo/ETS). Pinned commit: ec58be0a56c3df904904db41197a597823092c11. The inspected qwen, qwen_vllm and llada paths call local model generation/forward-logit interfaces and implement block/energy sampling. They are not a drop-in external policy over our existing llama-server task API. No LICENSE path appeared in the inspected complete tree. Keep ETS as related inference research, not the first system-policy implementation.

ACE and ReasoningBank have 2025 preprints despite later 2026 appearances. MemAPO has a 2026 paper but this review did not locate an author-linked implementation; that is a search limitation, not proof none exists. Methods that use training-free rewards while training model weights do not satisfy this task.

## Reproducibility and practical limits

The adjacent source-index JSON pins every inspection receipt, full upstream commit, primary URL and source byte hash. Downloaded source remains under DATA/research/2026-training-free-rl; it is not vendored or executed in the study repository. MemRL v2 fixes only a malformed trailing literal newline in the initial receipt; the original receipt remains preserved. JitRL v2 adds the nested license and numerical interpretation to its initial source snapshot.

Source inspection establishes what selected paths implement. It does not establish paper-result reproducibility, test coverage, complete provider compatibility, speech effectiveness or license scope beyond inspected files. These are useful algorithm candidates and concrete adaptation constraints, not already deployed components.
