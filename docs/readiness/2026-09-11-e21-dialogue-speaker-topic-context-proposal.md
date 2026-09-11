# E21 dialogue, speaker and topic context proposal

Status: feasibility-only design, qualified by OWNER-DATASET-TASKS-010 on 2026-09-11. Judge any later method on the existing dataset task; no final-summary task, evaluator or generation campaign is required by this proposal. No new mechanism, diarizer run, summary generation or GPU budget is admitted. The registered offline direct-to-KC-E1f baseline continues.

## Root recommendation

Use diarization as an uncertain observation and retrieval index. Preserve local dialogue order and complete question-answer context; add speaker-specific memory indexed jointly by topic. A speaker is not a topic: an analyst asks and an executive answers the same question, while one executive discusses many subjects. Maintain both relationships.

Do not immediately replace the fixed audio windows with isolated speaker turns. The existing OBS-E1 run improved corpus WER from8.19952 to7.15078, but worsened PERSON from22.48886 to24.58005 and was rejected. Its transport change also changed boundary placement, speaker purity, contact count and length. This is evidence of a quality tradeoff, not causal proof that missing context alone caused the name errors. Source: docs/readiness/2026-09-08-e21-obs-speaker-turn-units-v1-verdict.md.

The full44 diarization pass already exists. Reuse and verify it for analysis before considering any rerun. It was computed from complete calls and is not an authorized prefix-causal prompt input: an early-window memory cannot consume its future-derived speaker assignments unchanged. A runtime speaker view requires its own temporal-source qualification. Its frozen Sortformer tool has a four-speaker design bound and anonymous call-local IDs; the sealed receipt records38 of44 participant rosters above that bound (maximum19), and42 of44 diarized calls reach four detected IDs. Existing output qualifies coarse observation strata and turn hypotheses, not a trustworthy global person identity store. Source: docs/readiness/2026-09-06-e21-diarization-obs-v1-preregistration.md. This is not evidence of a measured diarization error rate, but it makes conflated global speaker memories a concrete concern. A stable multi-speaker identity route and its budget would need separate qualification before identity-dependent claims.

The inherited OBS-E1b proposal adds local left/right audio context around unchanged speaker-turn ownership and an overlap stitch; it remains unexecuted. It does not implement semantic dialogue history or dynamic speaker summaries. Those are separate hypotheses.

## Proposed context views

| View | Store | Retrieve | Purpose |
|---|---|---|---|
| Local dialogue | Recent grounded utterances in time order, speaker hypotheses, unresolved questions and correction links | The active exchange and its antecedents, truncated only at an explicit budget boundary | Resolve pronouns, ellipsis, negation, references and question-answer dependence |
| Speaker-topic memory | Atomic claims, entities, numbers with units/periods, commitments, questions, and changes of position, with evidence references | Active speaker plus relevant interlocutors, restricted to the current topic | Recover an earlier explanation without mixing unrelated statements by the same person |
| Topic state | Cross-speaker question-answer links, contested claims, agreements and unresolved items | Current or explicitly resumed topic | Preserve meaning across speaker changes and detect revisited topics |
| Evidence store | Versioned source audio ranges and frozen-core transcript outputs | Source spans supporting each retrieved claim, with targeted relisten only if separately admitted | Check summary distortion and speaker attribution |

A memory record should bind call ID, anonymous speaker hypothesis, topic ID, claim type, content, source window/turn IDs, time bounds, observed-through time, evidence hashes, uncertainty and supersession links. A topic or speaker summary is a derived index, never a replacement for the source evidence. Keep exact numeric value, unit, comparison basis and time period as structured fields.

Do not infer a real identity from voice. Name mappings may use only runtime-legal participant material and observed self-introductions from the frozen core. Leave unresolved mappings anonymous. Do not treat a dominance share as a calibrated identity probability. Ambiguous, overlapping or potentially merged speakers must not update a definitive per-person claim.

## Read and write discipline

Construct each request from the current audio or delivered transcript span, the local exchange, selected speaker-topic records, the active topic state and the legal participant brief. Reserve actual audio, instructions and output capacity first; allocate memory from the measured remaining budget. Do not invent a universal token allocation before the complete actual-request fit.

Retrieve before answering. Let the frozen core produce the answer and any structured memory update through registered bounded stages. The Reviewer produces scores and flags; the Planner chooses whether to retrieve, relisten or stop; neither takes final answer authority. All semantic summary generation remains on the same frozen answering core and contributes to contact, token and GPU cost.

Maintain immutable source responses and versioned state updates. A correction adds a superseding record; it does not silently overwrite an old claim. A repeatedly compressed paraphrase must periodically resolve back to source evidence. Mark an analyst's assumption as a question or hypothesis rather than recording it as the company's assertion.

For window-level transcription or repair, admit only state whose observed-through time precedes the allowed boundary. Offline latency tolerance does not waive the inherited future-turn prohibition. A later final-minutes stage can use a fully observed episode only under its own explicit episode-end input contract; do not inject its retrospective memory into an earlier-window comparison.

## Minimal scientific sequence, not an execution registration

1. Close the currently registered direct-to-KC-E1f baseline. Preserve its new draft, repair outputs and complete costs.
2. Prepare dialogue and memory views without changing the audio roster or window geometry. Verify legal sources and speaker-ID limitations before identity-dependent use.
3. Register a minimal local-context arm against a matched no-context arm, with the same windows, core, service geometry and delivery rule. Keep a complete paired roster; do not turn a four-row engineering proof into an effectiveness claim.
4. If useful, compare local context plus speaker-topic memory against local context plus an equally budgeted topic-only or unpartitioned memory built from the same source claims. Match input/contact budgets or explicitly separate total-system benefit from allocation effects.
5. Compare selective retrieval with an equal-volume irrelevant or alternative selection control only when a concrete decision requires it. Do not add a large Cartesian sweep.
6. Consider audio resegmentation or a different diarizer in a later separate comparison. Changing diarizer, segmentation, summaries and prompts together would prevent useful attribution.

Speaker records with a qualified temporal visibility contract may be prepared once and reused across the comparison. The existing full-call diarization artifact alone does not satisfy that contract for earlier-window prompts. If a memory builder adds model calls, charge them to all relevant systems rather than hiding them as preprocessing. Saved-derived arms are correlated results and do not become independent replications.

## Quality and execution

Follow the existing E21 ASR/entity task and the frozen comparison endpoints: WER, PERSON, non-entity, numeric and insertion measures with full-call paired clustering and complete-score discipline. Distinguish dataset-supported measures from repository-defined auxiliaries and the ConEC definition mirror; do not call all of them executed official metrics. The reviewed E21/E22 releases define no native summary/minutes target or evaluator. Do not add a new human evaluation, summary reference set or summary-quality gate. Candidate memory views are useful only if the existing downstream task improves under its registered comparisons and costs. See 2026-09-11-earnings-native-task-alignment.md.

Before a new comparison, freeze primary endpoints, guard tolerances, full roster, state visibility, all contact budgets and the role of memory. Do not carry an old numerical noise tolerance across a changed metric or protocol without calibration.

Reuse TaskAdapter, KnowledgeProvider, EvidenceAgentController, FlightRuntime and OpenJiuwen. Existing diarization artifacts, planned windows, predecessor snapshots and prepared packet/fit/score paths are available. Current unit-plan and sealed-repair paths explicitly reject rolling context tails, and the current window-controller bridge admits only direct-only behavior. A per-call dialogue state store, speaker-topic views and bounded memory-update transitions therefore require an explicit shared extension; a judge or tail configuration alone does not implement them.

Parallelize independent preparation and independent calls. Stateful turns within a call retain order, while different calls fill the resident service slots. A diarizer or feature encoder that needs the GPU receives a separate root-owned preparation window; it must not coexist with another generating flight. Do not start a second answering model. Reuse the current validated full-window packets for initial context-only arms.

## Research context

The external literature motivates hypotheses, not a guaranteed result on this frozen core. QMSum studies locating and summarizing meeting spans for a query, supporting topic/query-focused evidence selection: https://aclanthology.org/2021.naacl-main.472/. Dialogue discourse-aware summarization models relations between utterances rather than only a linear sequence: https://arxiv.org/abs/2012.03502. Topic-aware dialogue summarization explicitly addresses information scattered across different speakers: https://arxiv.org/abs/2109.04994. These trained systems are not imported into this zero-parameter study.

## Contract clarification after root review

The umbrella owner execution contract (2026-08-04, lines 102-107 and 117-123) explicitly excludes future-turn material from runtime; the Stage-2A entry (2026-08-02, lines 34-44) repeats that rule. Neither text grants a blanket offline exception. The existing full-parent barrier only makes sealed outputs available for their declared same-window repair. It does not authorize later-window information in an earlier-window request.

A distinct future final-minutes task would need its own target and input contract, but OWNER-DATASET-TASKS-010 excludes creating that task as a requirement of this round. The existing dataset task remains the evaluation target. The local-context hypothesis remains chronological, and full-call speaker observations remain analysis inputs until separately qualified.
