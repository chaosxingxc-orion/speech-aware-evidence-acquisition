# Agent system, knowledge and the optimization workspace

Status: factual implementation map plus explicitly labeled root interpretation.
This page does not admit a new experiment.

## Shared execution architecture

Keep the existing TaskAdapter, KnowledgeProvider, EvidenceAgentController and FlightRuntime.
Execute direct and system arms through the same OpenJiuwen path. Extend registered shared
components only when the existing interface cannot express the experiment. Thin configs select
behavior; do not add a private experiment runner, controller or independent model service.

The native workflow already supports role transitions, bounded tool visits, revision,
optional acquisition and optional candidate refresh. Framework capability is not the same as
an enabled action in a particular frozen experiment.

The current system has Perception -> Solver -> Reviewer -> Planner, with at most one Solver
revision. All answering and role generation use the same frozen core. Planner routes; Solver
owns the delivered answer. Reviewer is a separate responsibility, not an independent model
or a statistically independent measurement.

The current frozen package enables Reviewer task-contract and target-knowledge lookup.
Planner exposes ACCEPT and REVISE. It does not enable acoustic acquisition or candidate refresh.
Do not describe it as a completed on-demand Whisper/refresh policy.

## What each role actually receives

| Role | Required information and current behavior | Important limit |
| --- | --- | --- |
| Perception | Original speech, full legal task inventory, up to eight retrieved intent-boundary cards; produces at most three distinct ordered candidates | Candidate explanation is a hypothesis, not a verified transcript. Empty unresolved/evidence fields are not confidence. |
| Solver | Speech, typed candidate hypotheses and candidate-linked slot cards; latest draft and current review on revision | A card's example or a suggested filler is not evidence that it was spoken. Solver must own the answer. |
| Reviewer | Speech, current draft, candidate hypotheses, accumulated knowledge, own source-bound tool pairs; structured findings | Seeing a draft can anchor the review. A valid finding or available citation does not establish semantic correctness. |
| Planner | Compact draft identity/structural status, current structured review and relevant current Reviewer tool pairs | Chooses legal continuation; does not author a substitute answer. Current actions cannot resolve every acoustic gap. |

Every role also inherits the task adapter's base messages. The current role-context compiler
filters role-history states, but it does **not** project away all accumulated QueryState
knowledge. Once acquired, intent and slot cards remain in the base knowledge renderer for
later roles. This is an actual remaining interface gap, not a completed role-isolation feature.

## Context compilation: what is implemented

The registered compiler runs after supply resolution and before the shared request is frozen.
FIT and dispatch use the same prepared request. The compiler itself makes no retrieval, ASR,
encoding, tokenization, model or official-scoring contacts.

It preserves raw canonical history while making separately identified typed views:

- Preserve first-occurrence candidate order, actual distinct width, normalization mapping and
  source identity. Do not invent missing alternatives or treat duplicates as confidence.
- Parse the current Solver draft under a closed schema, including an explicit entity array.
  Preserve exact field strings and repeated entities. Keep malformed drafts visibly malformed;
  do not convert a parse failure into a valid empty answer.
- Parse structured review declarations. Distinguish supported issue, insufficient evidence,
  unavailable/malformed report and no declared issue. These remain model declarations.
- Separate evidence, task knowledge, hypotheses, drafts and reviewer recommendations.
  Keep exact required native tool call/result pairs with their sources.
- Give Planner and revision the relevant current review. Avoid carrying an earlier Reviewer's
  opinion into a later independent-role review as if it were new evidence.
- Record selected/excluded source versions, derivation hashes, destination-visible evidence
  IDs and ORG traces. Citation availability is not entailment.
- Preserve historical behavior when the option is absent.

This is a deterministic custody/representation layer. It cannot determine missing acoustic
facts, certify the meaning of a model explanation, or become a second answering model.
The owner requested analysis and filtering of handoffs; the current package implements
structural normalization and role-history selection. Semantic benefit remains under test.

Sources:
[contract](../../readiness/2026-09-16-role-context-compilation-contract.md),
[implementation](../../readiness/2026-09-16-role-context-implementation.md),
[construction/consumption inventory](../../results/2026-09-16-slurp-knowledge-construction-consumption-inventory.md).

## Knowledge construction and consumption must be designed together

The stable knowledge store and corrective memory have different purposes.

**Intent store:** 60 compact cards, supported by 474 governed TRAIN utterances / 2,037 recordings.
Its key is intent label plus activation-boundary text. Its value includes activation conditions,
named confusable-intent distinctions/exclusions, uncertainty behavior, limitations and provenance.
The key does not contain all discriminative value text.

**Slot store:** 54 construction-observed types, supported by 803 deduplicated utterances,
1,388 mentions, 3,162 recordings and 402 observed intent/type bindings. The legal task contract
separately contains 55 entity types. Construction coverage is not the authoritative legal set.
Each value contains intent-specific semantic roles, extraction cues, admissible-format guidance,
missing/ambiguity behavior, limitations and provenance. These are not exhaustive allowed-value
lists, mandatory fields or proof that absent bindings are prohibited.

Construction excludes entire utterances if any recording is in TRAIN A, TRAIN B or DEV1000.
Do not use evaluation errors to insert their correct answer strings into these stores.

**Current consumption:** sealed speech-query vectors rank 60 text-key vectors by cosine;
K8 supplies at most eight intent cards. Perception produces maximum-three distinct candidates.
An explicit released relation maps those candidates to slot cards, preserving candidate order
and round-robin selection with per-candidate 16 / total 28 caps. The renderer includes the
entire selected slot card, including all of its intent bindings; it does not yet project it
down to the particular candidate binding that caused selection. Reviewer target lookup
uses the same pinned explicit indexes.

**Legacy task contract caveat:** the global ontology contains filler examples gathered from
full real TRAIN, unlike the newer fold-excluded semantic stores. Root traced an illustrative
filler in a harmful revision to this visible legacy contract, not the new stores. This
establishes exposure and chronology, not causal copying or target-specific gold leakage.
Preserve this provenance distinction in reports.

**Memory:** keep generalized, source-grounded error/correction lessons, conditions,
exceptions and measured outcomes. Raw TRAIN recordings, evaluation answers and transcripts
do not become a runtime memory database. Some typed preparation/materialization infrastructure
exists; it is not evidence of an executed successful RL cycle or a released corrective memory
for the current flight.

## Root's interpretation of the information gap

1. More retrieved cards and more allowed candidates are different interventions.
   A supplied gold-intent card does not imply a generated correct candidate.
2. More candidates do not guarantee a superset of previous candidates. Preserve loss rows;
   blindly increasing N can worsen downstream ambiguity.
3. For selection, discriminative value must explain what rules a neighboring intent in or out.
   For entities, explanatory value must identify semantic role, span, representation and
   annotation-relevant boundaries. Generic labels alone are weak value.
4. A necessary card already being visible rules out simple non-delivery for that case.
   It does not prove the model understood or used it. Additional identical lookup may add no
   useful information.
5. Review is useful only when it identifies a resolvable issue, obtains or points to the
   needed evidence, and changes the delivered result beneficially. More critiques/revisions
   are not objectives.
6. Introduce a speech tool for a named acoustic uncertainty; introduce contract information
   for an extraction/annotation ambiguity. Do not assume every slot error is an ASR error.
7. The current package bundles context normalization, structured review and target lookup.
   Its system-versus-direct result cannot isolate the contribution of each part.

## Implementation routing

Read only the modules required by the next action:

| Component | Existing location under src/speech_aware_evidence_acquisition/ |
| --- | --- |
| Typed role views and request binding | rails/role_context.py; rails/role_context_binding.py |
| Shared supply and role requests | rails/knowledge_provider.py; rails/phase_supply.py; rails/runner.py |
| Governed semantic store construction | rails/semantic_knowledge_build.py |
| Candidate-to-slot relation and limits | rails/candidate_semantic_supply.py |
| Source-bound named target lookup | rails/released_target_index.py |
| Native framework state machine | reproduction/ojw/native_episode.py |
| Tool authority and rejected-batch validation | rails/native_tool_authority.py; analysis/native_tool_exposure.py |
| Complete source verification | analysis/native_episode_source.py |
| Stage attribution and structured review diagnostics | analysis/slurp_solver_stage_attribution.py; analysis/review_findings.py |
| Saved-score bridge and paired comparison | rails/reward_link_io.py; analysis/score_compare_cli.py |

The shared batch-rejection repair has already been integrated. It rejects the full invalid
batch without dispatch, preserves every original call, supplies ordered source-bound rejection
results and lets the framework continue inside existing bounds. Do not reimplement it locally.
