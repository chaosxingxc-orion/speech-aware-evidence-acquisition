# SLURP: candidate coverage and evidence-grounded resolution

Date: 2026-09-16. Owner-directed research plan. Keep SLURP as the single active optimization dataset. Investigate two tracks in parallel and evaluate them through one shared agent system. This document defines research priorities; it does not register a new model contact or reopen a closed attempt.

## Decision and current evidence

Root owns scientific interpretation, intervention selection, admission and final review. Two reading agents gather bounded repository evidence; neither chooses the scientific verdict. Keep the existing E21 static fit within its already registered scope, then hold. Hold Audio2Tool proof and full-flight preparation. Preserve the shared code already completed for those carriers.

Use the retained complete TRAIN Fold A incumbent as the development anchor: 1,080 recordings, 125 speakers, 18 scenarios. Its candidate coverage is 937/1,080 (86.7593%), final intent correctness is 842/1,080, and 525 of the 842 correct-intent predictions have nonexact entity sets. Reaching 95% coverage on this roster requires at least 1,026 covered recordings: a net increase of 89 over the incumbent. Keep 95% as a priority target alongside complete-task quality, not as a prerequisite for Track B.

The rejected broad/factored package increases coverage to 947/1,080 but decreases official SLU micro F1 from 48.5336% to 47.6347%. The primary CI95 for the difference includes zero. Among the same 917 recordings covered by both arms, final correct intents decrease from 834 to 824. This establishes the need to separate inclusion from use; it does not identify breadth or factoring as an isolated causal cause.

The incumbent initially supplies the gold intent's own card on 947 recordings: 914 are covered by candidates and 33 are missed. Another 23 are covered without that own card; 110 have neither. These are descriptive associations. An own-card match is not a measure of whether every useful distinction is available or consumed.

Read the existing complete reports:
- [TRAIN anchor](../results/2026-09-14-slurp-native-train-a-anchor.md).
- [Entity-loss attribution](../results/2026-09-14-slurp-train-a-entity-loss-attribution-v1.md).
- [Broad/factored result](../results/2026-09-16-slurp-broad-factored-train-a.md).

## Track A: keep the correct intent in a useful candidate set

Research question: how much candidate omission can be recovered through candidate width and through better coverage of discriminative knowledge, while retaining a tractable downstream decision?

Distinguish three quantities:
- K: retrieved knowledge breadth. The retained initial supply uses eight retrieved intent-boundary values.
- N: the maximum number of distinct generated intent hypotheses. The retained program allows one to three.
- C: the set of generated legal candidates actually available downstream. Measure gold membership in C only during offline evaluation.

The full 60-label legal inventory already exists. A list containing every legal label trivially covers the gold label and is not a useful achievement of the candidate module.

### A1: candidate-width policy first

Prepare one prospective comparison of maximum N=3 versus N=5, keeping the retained initial knowledge version and its retrieval policy. Keep the minimum at one in this first contrast; a forced exactly-five policy is a separate experiment. Record actual distinct widths, duplicates, invalid labels, ordering and empty outputs. Do not infer confidence from a short output or pad missing candidates after generation.

Propagate the declared width through the response schema, parser, state projection, candidate-to-slot provider, Solver, review tools, fit requests and diagnostics. Preserve the source response. Do not let an old three-candidate projection silently discard the fourth and fifth labels.

Keep the incumbent total Solver value cap of 28 and per-candidate cap of 16 in A1, while widening the permitted candidate IDs consistently. Increasing N can spread that fixed total supply more thinly: report actual supplied values and missing relevant contracts by candidate. This is part of the N=5 policy under the retained supply budget. It cannot separate the benefits of extra candidates from losses due to diluted descriptions. Track B may investigate improved representation or separately registered additional value supply; do not silently scale the cap in A1.

Reserve N=8 for a subsequent explicitly selected question. Do not launch a large width sweep or keep retrying until 95% is reached. Existing at-most-three outputs cannot estimate recall at five or eight. Prefix coverage from a future wider list is useful correlated diagnostics, not the result of independently running narrower generators.

### A2: knowledge coverage with a fixed candidate policy

After fixing the candidate policy for this comparison, investigate coverage of the distinctions needed to propose plausible alternatives:
- action, object, requested outcome and surrounding situation;
- paraphrases and indirect requests from authorized construction sources;
- neighboring intents with explicit positive cues and exclusion conditions;
- distinctions obscured by lexical overlap or ambiguous spoken wording.

Keep a concise complete overview and supply targeted detailed contrasts. Measure own-card availability separately from coverage of relevant neighboring distinctions. Reuse the current store/provider abstractions. Do not repeat the failed package by increasing retrieval breadth and changing value structure simultaneously without identifying the intended comparison.

Knowledge coverage means supplying missing decision information. It does not mean reproducing all training utterances in context. Preserve the intent-boundary store separately from the slot-interpretation store and preserve construction/evaluation isolation.

### Track A outputs

Report candidate coverage, actual width distribution, rank of the gold label when present, gained/lost coverage, all scenario strata, and downstream intent and full SLU outcomes. Keep natural-mixture and equal-scenario views. Attribute losses between supplied-but-omitted and not-supplied cases without treating their observed association as a causal effect.

### Implementation and source-review findings

The hypothesis validator, bounded candidate projection, candidate semantic provider, candidate-contract view and downstream diagnostic readers contain independent caps at three. The canonical parser already accepts a configured bound up to the legal inventory. Generalize the existing shared seams together, preserving historical defaults and identities; do not create a separate Top-N controller. Changing only prompt wording or one JSON maximum is insufficient.

An earlier model-free retrieval audit replayed K=12 through K=60 under the incumbent knowledge source. Those outputs are useful prospective supply diagnostics, not observations of the later factored store. Root rejected an attempted join that treated that replay as the broad/factored run's actual own-card supply. The existing complete report explicitly leaves that newer own-card metric unavailable. Retain this limitation; no replacement metric or new scorer is needed to design A1.

## Track B: choose the right intent and extract supported slots

Research question: with the candidate source held fixed, what information and review process help the frozen core select the correct interpretation and extract the entities the task actually asks for?

Track B can proceed while Track A is below 95%. Use a complete, sealed, source-bound candidate set for the component comparison. Never insert the gold intent or a reference transcript into the runtime. If a later integrated system refreshes candidates, record initial and post-refresh coverage separately; that refresh belongs to the candidate acquisition route.

### Information to supply

| Consumer | Information value | What it must resolve |
| --- | --- | --- |
| Solver choosing an intent | Candidate-specific inclusion/exclusion cues and direct contrasts with plausible alternatives | Why one intent matches the request more closely than another |
| Solver extracting a slot | Semantic role, allowed type, mention boundary, surface-form convention, omission conditions and relevant task examples | What the field means and which spoken words support its value |
| Reviewer | Current speech, delivered draft, candidate alternatives, relevant contracts, source-bound tool evidence | Unsupported, missing, conflicting or incorrectly interpreted claims |

Use the task's documented annotation conventions. Examples in knowledge are illustrations, not evidence that a value was spoken. A slot's association with an intent is not a requirement to fill it.

The released entity audit partitions official FP+FN loss mass into 31.49% unmatched references, 28.82% unmatched predictions, 35.04% same-type filler distance and 4.65% heuristic type swaps. The categories overlap at sample level and do not establish an ASR cause. Hearing, span boundaries, normalization and task semantics can produce similar score symptoms.

### Independent review as an explicit experimental factor

The repository has one frozen answering core. Reviewer independence therefore means a separate role invocation and controlled context, not an independent model or statistically independent errors.

The current Reviewer instruction mandates a task-contract call on every review and then requests general findings. Its existing tools and role history should be audited before adding code. The next review proposal should make the check concrete:
- compare the chosen intent with the strongest plausible alternative using a distinguishing cue;
- check support for every emitted entity and plausible omissions;
- distinguish unsupported values, wrong roles/types, boundaries, negation and correction;
- identify what evidence would resolve an unresolved issue;
- report a concise source-bound finding, while leaving final answer authority with Solver.

Investigate a fresh Reviewer context that excludes the Solver's rationale and prior evaluative claims, while preserving original speech and the exact draft to be checked. This reduces one route to anchoring but does not prove independence. A genuinely draft-blind evidence pass requires a separate invocation before exposing the draft; placing evidence earlier in one prompt is not equivalent. Treat that stronger two-pass route as a separately measured option, not an implemented capability.

Permit ACCEPT when the evidence supports the draft. Do not prompt Reviewer as if every answer must be wrong. Planner decides whether to acquire evidence, revise or stop; Solver can retain a supported original answer. Measure the policy actually executed, including suggested revisions that never reach Solver.

### On-demand tools

Choose the tool from the specific information gap:
- semantic ambiguity: request the relevant intent contrast or slot interpretation;
- structural inconsistency: inspect the task/schema contract;
- uncertain spoken words, names or numbers: request a bounded local Whisper observation of the current speech.

Keep tool selection inside Reviewer/Planner execution. Whisper output is fallible evidence for the frozen Solver, not a substitute answering model or mandatory preprocessing. Reuse the existing local speech provider and shared tool dispatcher. Do not add an independent carrier-specific agent framework.

The earlier SLURP dynamic-tools recovery closed after its second failure, with no released partial quality result. This plan does not create a third attempt. A future successor must specify a named change, source-bound protocol, necessary engineering proof and separate contact registration; copying old settings to a new ID is insufficient.

### Track B outputs

Report the full roster, plus the common gold-covered subset for paired interpretation. Distinguish each arm's own covered subset from the same rows covered by both. Measure final intent correctness, official SLU/entity metrics, complete intent-plus-entity exactness, and saves/harms before and after review.

Audit Reviewer issue detection, unnecessary challenges to correct drafts, successful corrections, harmful revisions, unused findings and tool-result consumption. Report semantic and acoustic acquisitions separately. A successful tool invocation, a longer critique or agreement with Solver is not itself a task gain.

Use sealed-stage replay only for component attribution. Evaluate the selected complete system with live Perception, review, tool acquisition, Planner and Solver before claiming system quality or cost.

## Parallel research and sequential experimental decisions

1. Gather Track A and Track B repository evidence in parallel. Root reconciles findings with the complete released results and a small set of primary sources.
2. Prepare the width-policy contrast first because it changes the smallest clear candidate factor. At the same time, prepare the task-specific information and review contract for Track B.
3. Register each selected experiment with exact roster, source, model/service geometry, request fit, contact budgets and analysis rule. Use the same shared controller, FlightRuntime and OpenJiuwen executor for every arm.
4. Run only one GPU experiment at a time. Overlap the next CPU preparation and the preceding complete official scoring job within SLURP. Do not resume E21 or Audio2Tool experiments.
5. Select a combined system based on complete task quality relative to a matched direct-model comparator and the retained system. Reuse compatible sealed evidence where it actually answers the comparison; add only decision-relevant matched controls.
6. Replicate a promising complete system on the same roster before calling its benefit stable. Preserve protected splits until a candidate and its evaluation protocol are frozen.

The top-level comparison remains direct model versus agentic system. The component contrasts explain how to improve the system. Do not expand a broad knowledge-on/knowledge-off ablation grid.

Apply the registered full-task advancement rule and paired speaker-cluster uncertainty, with 10,000 bootstrap draws when specified by the prospective recipe. Candidate coverage is a diagnostic priority; a coverage-only win does not advance a worse complete system. Do not select favorable strata or score incomplete manifests.

Preserve state, candidate provenance, supplied values, tool actions/results, review findings, Planner actions and final revisions. These establish a later optimizable trajectory space. Root-authored engineering and the present two-track research are not training-free RL; algorithmic sampling, rewards and external-policy updates follow the stable system.

## Primary literature and transfer limits

[Chen and Wang, EMNLP Findings 2025](https://aclanthology.org/2025.findings-emnlp.749/) separate candidate generation from description-enriched intent selection and comparative reconsideration. Their candidate-size analysis shows a task-dependent selection tradeoff. Their method trains a small predictor and studies text intent datasets; its results are not evidence that widening candidates will improve this frozen speech system. Reuse the question and evaluation separation, not its trained model.

[Sun et al., ACL Findings 2024](https://aclanthology.org/2024.findings-acl.379/) study SLURP slot filling from noisy ASR and external knowledge. The reported improvements combine interventions including fine-tuning. The study motivates distinguishing acoustic noise from semantic guidance; it does not establish the effect of our proposed frozen-core tools.

[Huang et al., ICLR 2024](https://arxiv.org/abs/2310.01798) find failures of intrinsic self-correction on their reasoning tasks. [Liu et al., 2024](https://arxiv.org/abs/2406.15673) report self-correction under particular prompt and decoding conditions. Their differing findings argue for balanced review prompts and an actual local test, not a universal claim that self-review always works or never works.

[Gou et al., CRITIC, 2024 revision](https://arxiv.org/abs/2305.11738) demonstrate tool-interactive verification and correction on other tasks. This motivates source-grounded review and explicit evidence acquisition. It does not prove that Whisper, a particular review role or any tool budget will improve SLURP.

## Preparation update: controlled Reviewer history

The optional implementation in
[Reviewer history scope](2026-09-16-slurp-reviewer-history-scope.md) is now verified
with synthetic shared-runtime tests. It keeps the latest complete Solver state and current
Reviewer tool chain; it does not strip any rationale embedded inside that Solver state.
It removes earlier Perception, draft, Reviewer and Planner history from Reviewer only,
including candidate IDs and descriptions. Current speech and bound knowledge remain.
Consequently it tests the tradeoff between earlier role influence and useful prior
information, not pure statistical independence or draft-blind evidence gathering.

The option remains held. Its direct control is the unrun structured-review v2 configuration;
a historical-anchor contrast would include the other structured-review changes.
Do not combine prepared factors or schedule extra flights merely because implementation
is available. Root admits the next contrast after the complete maximum-five verdict.
