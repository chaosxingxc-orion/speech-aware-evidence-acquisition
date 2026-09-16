# SLURP two-track system optimization

Date: 2026-09-16
Decision owner: root
Scope: SLURP development only; keep E21 and Audio2Tool held.

## Research decomposition

Treat candidate inclusion and evidence-conditioned decision as separate bottlenecks. A candidate is useful when the gold intent is present; its rank need not be correct at Perception. Solver jointly chooses a candidate and its supported slots. Measure candidate coverage, decision accuracy on common-covered rows, slot quality given correct intent, and final official task quality. Do not multiply marginal rates with different denominators or treat candidate coverage alone as system benefit.

The retained TRAIN Fold A anchor covers 937/1080 gold intents (86.7593%). Final intent is correct for 842 rows. Of the covered rows, 95 finish with the wrong intent; 525 rows have correct intent but a nonexact entity set. Full intent-plus-entity exactness is 317/1080. These released counts motivate both tracks. The 95 percent coverage priority requires at least 1026 covered rows, but does not delay work on downstream errors.

## Track A: candidate inclusion

Run one maximum-five arm against the retained maximum-three anchor on the exact full1080 roster. Keep all 60 legal intents visible, minimum one distinct candidate, the original K8 knowledge selection, fixed Solver value budget, roles, tools and decoding. The prepared first-phase selections and values equal the anchor exactly. Preserve actual candidate width, duplicates, invalid entries and delivered knowledge volume. Do not pad missing candidates or infer confidence from narrow lists.

Register coverage transitions, conditional final-intent accuracy on the same common-covered rows, own-covered denominators, full-task gains/harms and all scenario strata. Enlarging N can dilute per-candidate values and increase confusions; report these consequences.

Knowledge coverage is the next diagnosis-driven choice, not an automatic K sweep. The completed broad/factored experiment improved coverage only slightly and reduced the final-task point estimate. Distinguish failure to retrieve a relevant intent, loss of a useful distinction during value construction, and failure to use a visible distinction before proposing a successor. Prefer compact, complete coverage of confusable intent boundaries to undifferentiated extra text. Use stable activation conditions, exclusion conditions, competing intents and evidence that distinguishes them. Construction must exclude the evaluation folds.

## Track B: intent decision, slots and evidence review

Keep separate intent-boundary and slot-contract stores. Intent values explain why one candidate fits and nearby alternatives fail. Slot values explain semantic role, admissible values/types, scope, extraction evidence and normalization. Avoid reference-derived answer hints. Candidate-conditioned knowledge must resolve semantic ambiguity rather than merely repeat labels. The released September 14 entity-loss audit already verified that omission and evidence-preservation rules exist in Solver/context prompts and authored slot contracts, and that the completed replica exposes slot contracts in every Reviewer request. Repeating these rules or supplying the same visible cards is not a named information-gain mechanism. The next value revision must address a source-grounded annotation boundary, concrete semantic contrast, or otherwise demonstrated missing distinction; an acoustic tool needs a demonstrated hearing uncertainty.

Reviewer checks the draft against the speech and explicit task evidence. It identifies a concrete suspected error or unresolved distinction before requesting information. Planner decides whether to acquire evidence, revise or accept. Solver alone writes the task answer. The existing target-knowledge tool may retrieve a requested candidate's intent distinctions or slot explanation; tool calls remain on demand. Local ASR or re-listening are future evidence tools when the suspected gap is acoustic, not mandatory preprocessing.

Use role separation without claiming statistical independence. The current shared history exposes earlier reasoning, so this is not a draft-blind independent judge. A later separately registered evidence-first review may reduce anchoring, but is not silently bundled into the maximum-five arm.

Measure initial-draft versus final saves and harms, issue detection versus actual draft errors, proposed versus executed revisions, and tool attempted/returned/exposed counts. Visibility is not semantic consumption or causal benefit. The shared source verification and analysis APIs already provide most joins. Before Track B admission, bind only the missing stage-score table, structured issue/action output and traceable evidence-use linkage needed by its claims. The September 16 preparation now supplies shared source-bound Solver stage scores and bounded Reviewer declarations; the current held report configuration is slurp-native-evidence-review-train-a-held-v2. These engineering proofs do not establish model benefit or capacity.

The current held Track B configuration is a preparation artifact, not a launched experiment. It changes Reviewer evidence access and reserves a final report slot, so its effect would be a package contrast unless those factors are separately controlled. Root will finalize the smallest useful contrast after the maximum-five verdict; do not interpret it as an isolated tool effect.

## Execution and advancement

Parallelize model-free preparation and measurement binding; serialize model contact under one root-owned resident service and lease. Use WSL, precomputed SLURP speech packets and a decoder-only four-slot service without GPU mmproj. Fit every realized immutable request immediately before dispatch, including live role history. There is no static guarantee for unexecuted branches.

Use official pooled SLU micro-F1 on the complete roster as primary, paired speaker-cluster bootstrap with 10000 draws and seed 20260915, CI95 for advancement and CI90 for diagnostics. Report natural-mixture, equal-scenario and all18-stratum results. A positive point gain with CI95 lower bound above zero advances to a separately registered same-roster replication. Only replicated benefit supports a stable-base claim. Preserve historical process differences and prior failures.

Do not treat manual architecture/prompt work as training-free RL. Once the base is stable, expose explicit candidate, knowledge, observation, review and stopping decisions as the optimization workspace, then separately define trajectory sampling, rewards and an algorithmic update. No training-free RL result is claimed here.


## Keep the system question explicit

An improvement over the retained agent anchor diagnoses an optimization direction; it does
not by itself prove superiority over direct model invocation. A promising locked system must
also be evaluated against the shared-harness direct baseline on a matched, appropriately
registered roster. Use existing complete comparators where their configuration and population
actually match. This plan does not create new confirmatory exposure.

Judge review policy by evidence-supported correction precision, missed-error rate, harmful
revision rate, and final official task quality. More tool calls or more REVISE decisions are
not a success criterion. Keep acoustic uncertainty, intent-boundary uncertainty, and slot
meaning/span uncertainty separate so each can request the tool that adds the missing
information. The current package admits target knowledge only in its held configuration;
future ASR or selective replay remain separately registered on-demand actions.


## Source-grounded context correction under preparation

The completed follow-up in
docs/results/2026-09-16-slurp-review-context-provenance.md locates an unsupported
illustrative filler in the legacy global task contract, not either semantic knowledge
snapshot. It also observes candidate label/description mismatch and a later role treating
alternative hypotheses as simultaneous evidence. These are distinct failure paths; five
revision cases do not establish their corpus prevalence or isolated causes.

Prepare one shared opt-in contract projection that retains the full legal inventory but
omits global example fillers. The same projection must reach the initial instruction,
task-contract tool and actual capacity request. Preserve historical default bytes and
leave the active maximum-five experiment unchanged. No held Reviewer configuration or
flight is automatically updated. Root chooses the later contrast after A1's paired verdict.

Do not substitute stricter prose for information that is missing. A decision value should
supply the activation condition, nearest alternative and the observation that separates
them; a slot value should supply meaning, extraction scope and representation boundaries.
Existing no-invention rules are already visible. On-demand tools should add the missing
distinction or observation, while the final report distinguishes supporting evidence from
candidate explanations and previous model opinions. Future evaluation must count actual
candidate-boundary escapes as well as coverage and covered-set decision accuracy.


## Next-decision table

| Complete A1 finding | Next decision |
| --- | --- |
| Coverage and the registered full-task gain rule both improve | Register the required same-roster replication before introducing another mechanism. Treat a single positive result as a lead. |
| Coverage improves but common-covered decision or full-task quality worsens | Attribute the downstream loss and keep the incumbent. Use the larger candidate set as a diagnostic result, not an adopted system. |
| Coverage does not improve enough | Separate missing relevant intent information from failure to use visible information before selecting a broader or differently organized value supply. Do not launch a blind K sweep. |
| Full-task gain remains unresolved | Preserve that uncertainty and the fixed verdict; root may choose a separately registered, source-grounded successor without labeling the original successful. |

In the released anchor, 143 gold intents are absent from candidates. Of those, 33 have
their own intent card visible and 110 do not. Visibility does not establish usefulness,
and absence does not prove that retrieval caused the miss: 23 covered cases also lack
their own card. These strata identify different questions for coverage work. Larger N
may rescue a visible alternative; broader knowledge may rescue a missing distinction.
Measure new inclusions and lost inclusions separately.

The retained 95 covered-but-finally-wrong cases are the cleanest starting point for
candidate-conditioned decision analysis. The 525 correct-intent cases with nonexact
entities expose a separate extraction gap. These two failure slices are disjoint at the final-intent boundary;
neither is a new evaluation roster or a causal component estimate. Keep all 1080 rows in final
quality metrics and compare common-covered rows before comparing changing own-covered
denominators. No fresh roster or small accuracy screen is admitted by this table.

## Temporal follow-up narrows Track B

Read docs/results/2026-09-16-slurp-temporal-slot-diagnosis.md. All 84 date-omission rows already expose the exact released date card to initial Solver and Reviewer. In 25, the missing expression also appears in a candidate distinction. All initial roles receive speech packets. This names an evidence-to-delivery completeness gap while preserving the distinction between exposure, textual mention, grounding and causal use.

Time has a different pattern: 55 same-type matches but only eight exact filler pairs; representation and span differences are prominent in the offline root audit. The contracts already state generic omission and preservation rules but lack complete per-intent boundaries and serialization. Treat source-derived contract refinement as a distinct hypothesis from acoustic observation.

Prioritize Reviewer checks of supported mentions omitted from the answer and answer fields unsupported by speech. Route missing semantic distinctions to targeted knowledge and unresolved speech to optional acoustic tools. Do not fetch an already visible card and label it new information. Build any new value from admitted construction data excluding A/B; never convert the offline reference cases into runtime exemplars.

Keep the current A1 request program frozen. The next admitted experiment remains conditional on its complete verdict and is one bounded contrast, not a simultaneous rewrite of every role, store and tool.

## Prepared Reviewer history factor

The shared runtime now supports an optional Reviewer-only latest-Solver-and-local-tools
history scope. Read docs/readiness/2026-09-16-slurp-reviewer-history-scope.md.
It retains original speech, current knowledge and the latest complete Solver state, plus
the current review visit's exact tool call/result chain. It removes Perception candidate
IDs and explanations, older drafts and previous Reviewer/Planner/tool history from this
role's request only. Full episode custody and other roles are unchanged.

This factor is prepared and tested without real model contact. It can reduce exposure to
earlier opinions but can also remove useful candidate information. Current knowledge still
reflects prior candidate selection. Do not call it blind or statistically independent review.

The prepared baseline differs only in history scope and descriptive text from the existing
unrun structured-review v2 baseline. That is its controlled comparison; a comparison to
the historical anchor is a package contrast. Neither arm is admitted here. Keep the optional
no-example task-contract projection separate. After the complete A1 verdict, root selects
one bounded, decision-relevant next experiment or the required replication.

## Owner refinement: compile typed role context

The owner identified role-specific analysis, cleaning and normalization of context as the
central mechanism. Follow
docs/readiness/2026-09-16-role-context-compilation-contract.md.
Do not promote the prepared history-only restriction automatically. It removes all Perception
hypotheses, including potentially useful alternatives. The next shared design should preserve
useful candidates as explicitly labeled hypotheses and distinguish them from speech, tool
observations, task knowledge, the current draft and current review declarations.

Reuse the existing projections, parsers, phase-material and native role-binding seam.
Structural validation and citation availability do not prove semantic correctness; the frozen
roles retain semantic judgments. The full typed compiler is implemented and passed163
focused synthetic tests; its real-model configuration remains held. Read
docs/readiness/2026-09-16-role-context-implementation.md.
Keep A1 frozen and select one next contrast only after its complete verdict.

## Matched direct comparison preparation

The metadata audit identifies no released TRAIN A comparator matching current max512 and
shared direct-only execution. A held full1080 direct configuration and saved-score recipe
now reuse the common base. Read
docs/readiness/2026-09-16-slurp-direct-train-a-comparator-preparation.md.
The old TRAIN A direct contract is full SLU, but its fixed path, max64, seed and geometry
differ. No old output quality was read. Do not substitute DEV1000 scores for TRAIN A.
This preparation does not admit a new contact or change A1's advancement rule.

## Complete A1 decision and next selected package

A1 is complete and NOT_ADVANCED; read docs/results/2026-09-16-slurp-candidate-five-train-a.md.
Candidate coverage gains14 net rows, while the primary pooled SLU interval includes zero.
Initial-to-final review corrects only two intents across seven revisions. The sealed supply
audit finds no binding total/per-candidate cap exclusions. Keep maximum-three as incumbent;
do not automatically increase N or value limits.

Root selects the existing typed role-context plus structured evidence-review package for
one complete comparison with the prepared max512 direct-only baseline on TRAIN A1080.
Both use the same service geometry, speech and shared executor. This package includes
source-bound context compilation, structured review, on-demand existing target-knowledge
access and a reserved final report. It is not an isolated compiler ablation. Preserve the
historical task contract and knowledge; keep no-example, history-only, acoustic tools,
new knowledge values and candidate refresh out of this registration.

The existing DEV1000/NEW500 base has useful exploratory repeatability, recorded in
docs/results/2026-09-14-slurp-dual-store-base-replication-verdict-v1.md.
What remains unverified is the new package and its matching TRAIN A direct comparison.
First positive quality leads require a fresh same-roster matched replication. Root owns
attribution and admission; mechanical configuration work may proceed in an isolated WSL
worktree while root closes the completed flight.
