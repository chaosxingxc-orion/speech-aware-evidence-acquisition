# Earnings native tasks and owner scope alignment

Status: model-free task-definition review, 2026-09-11 UTC. No data sample,
reference transcript, current generation output or quality statistic was read
for this review. No scorer, model service or encoder was invoked.

The owner confirms in OWNER-DATASET-TASKS-010 that summary design is feasibility
only. Existing dataset tasks determine success. This corrects the earlier root
plan's expansion of meeting-minutes evaluation into a required acceptance item.

## Primary-source findings

- [Earnings21 release](https://github.com/revdotcom/speech-datasets/tree/main/earnings21):
  ASR on earnings-call speech with entity annotations and entity-class WER
  reporting. Its released task description does not define summary generation
  or reference summaries.
- [Earnings22 release](https://github.com/revdotcom/speech-datasets/tree/main/earnings22)
  and [original paper](https://arxiv.org/abs/2203.15591):
  accented-speech ASR, with WER and analyses by accent/origin. Neither reviewed
  definition establishes a meeting-minutes task or evaluator.
- [ConEC release](https://github.com/huangruizhe/ConEC):
  contextual ASR using accompanying participant information and public company
  documents, with corrected transcription and contextual vocabulary. These
  materials are recognition context, not target meeting summaries.
- The upstream speech-datasets root README also records Earnings21 RTTM
  additions for diarization evaluation. Availability of speaker annotations
  does not establish a summary task or make DER a current study endpoint.
  A later diarization metric would require the pinned version, protocol and
  scoring-only access; reference speakers must not become runtime evidence.

These are release-document findings, not a claim to have inspected every future
third-party derivative. Do not import a similarly named newer benchmark or
change dataset versions. Resolve dataset identity only from the umbrella lock.

## Local implementation qualification

The umbrella docs/datasets.lock.json entries earnings21-original and
earnings22-original retain ASR/reference-layer scope; the latter explicitly
does not supply the Earnings21-equivalent token entity annotation layer. The
shared .nlp schema shown in a public README does not prove that every dataset
has populated, equivalent entity labels.

src/speech_aware_evidence_acquisition/core/scorers.py registers the current
Whisper-normalized WER implementation. Its conec-entity-wer-official scorer
mirrors a pinned upstream accounting definition and emits official_tool_run:
false. It does not execute upstream fstalign. Preserve that provenance in
reports. It is currently scoped to Earnings21, not Earnings22.

numeric-value-accuracy-v1 is a repository-defined preservation measure.
semantic-high-impact-error-rate-v1 is a repository taxonomy-dependent measure.
Neither is a dataset-native summary metric. E22 ESB configurations still
evaluate ASR, with their own segmentation/normalization contract. Do not
conflate full-call original and utterance-level ESB populations.

## Execution consequence

Keep the registered E21 direct-to-KC-E1f pair's frozen PERSON primary and its
WER/nonentity/insertion/numeric guards, complete-call pairing, strata and costs.
Do not add summary labels, subjective summary quality, ROUGE or a new minutes
evaluation to the current comparison. Keep native metrics and study auxiliary
measures visibly distinguished.

Dialogue history and speaker-topic memory can be considered as input
organization mechanisms for the existing transcription/repair task. Their
admission would depend on downstream task results and their full costs, not
on a convincing-looking summary. The current proposal is feasibility only.

Future-turn exclusion and source provenance still apply to the admitted task.
No episode-end summary contract is required to complete this round because
summary generation is not an admitted dataset target. Live E21
Reviewer-to-Planner-to-observation remains a separate unproven accepted-runtime
behavior; this scope clarification does not pretend the fixed repair pair
establishes it.
