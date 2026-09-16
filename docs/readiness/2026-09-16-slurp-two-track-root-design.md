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
