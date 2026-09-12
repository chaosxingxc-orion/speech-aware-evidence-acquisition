# Speech tools as an external evidence-acquisition policy

Status: owner-requested design and local acquisition; no new dataset inference is admitted by this document.

## Owner decisions and unchanged active comparison

Prioritize overall WER and PERSON quality in future newly registered E21 experiments. Analyze small insertion increases separately instead of applying the historical automatic veto. Preserve the historical verdict and set any numerical guard prospectively.

Trigger review when the Reviewer has high confidence that a problem or a missing piece of evidence exists. Do not interpret this as high confidence that the current answer is correct. The owner confirmed this meaning on 2026-09-12. Treat self-reported confidence as an uncalibrated signal until evaluated on legally available development trajectories.

Download tools and weights locally in WSL, pin their identities and validate offline loading. The interrupted Audio2Tool comparison remains immutable at cbc53ac0c36bed94fdb50c3b069a74569d935720. The active experiment is the sole full matched Audio2Tool recovery frozen at 22b56d706e2f5601dc79f58a8fad2bb6a9629f51; read task quality only after all three recovery manifests seal. Local tool acquisition and load validation permit no new ASR inference, dataset audio processing, labels, task-result reads, auxiliary neural forward passes, GPU allocation, or paid inference. They do not authorize another experiment generation.

## System contract

Use the shared TaskAdapter, EvidenceAgentController, FlightRuntime and OpenJiuwen execution path. A tool supplies scoped evidence; only the frozen core supplies the final task answer.

The Solver creates a draft. The Reviewer emits a problem category, affected answer field, suspected audio span, observable reason, and confidence in the problem. The Planner selects stop, inspect, relisten, transcribe, align, retrieve context, or revise within a configured transition budget. A tool request identifies the missing distinction it is intended to resolve. A bounded Solver revision consumes the original evidence and the returned evidence together. Preserve the draft and all rejected evidence.

Keep three separate decisions: whether to investigate, which observation to acquire, and whether its result warrants a change. Agreement between systems is not proof, and disagreement alone is not a command to overwrite the draft. A tool timeout, empty result or unsupported alignment retains an explicit fallback.

Define the external action space as (tool, span, representation, legal context source, supply policy, stop-or-continue). This supplies meaningful optimization variables for a later training-free policy.

## Candidate tool inventory

| Capability | Candidate local implementation | Distinguishing evidence supplied | First task | Priority and interpretation |
|---|---|---|---|---|
| Independent ASR evidence | Official OpenAI Whisper large-v3 | A second transcription of an exact suspect span, optional word times and decoder diagnostics | SLURP, then Audio2Tool | First neural tool candidate; ASR only, never a second task-answering model |
| Speech activity and boundary inspection | Silero VAD with frozen thresholds | Speech spans, possible clipped boundaries, silence regions | All three carriers | Prepare metadata first; do not silently remove speech or change the frozen window protocol |
| Targeted replay and context extension | Existing audio slice APIs plus local FFmpeg | Exact source segment with explicit margins; optional separately registered tempo transform | SLURP and Audio2Tool | Reuse existing observation path; record original-to-derived time mapping and fresh feature costs |
| Word-to-audio alignment | Existing pinned MMS_FA wrapper first; WhisperX code as an alternative integration | Where a proposed word maps to audio and which tokens cannot be aligned | Slots, PERSON, numbers | Alignment locates a hypothesis; it does not establish that the hypothesis is true |
| Disagreement localization | Shared deterministic comparison of primary draft and ASR evidence | Conflicting tokens, negation, correction order, entity/number spans | SLURP and Audio2Tool | New transcript supply and conflict highlighting are separable interventions |
| Speaker turns and overlap | Existing sealed Sortformer path first; pyannote community-1 as an additional candidate subject to authorized access | Anonymous speaker labels, turn ranges and overlap information | E21, later E22 development | Test task WER/PERSON benefit; do not infer real identity or introduce a summary benchmark |
| Speech signal/channel inspection | Local ffprobe/FFmpeg and deterministic numeric checks | Duration, sample rate, channels, clipping, silence, boundary risk | All carriers | Diagnose evidence quality; do not infer semantic labels or environmental audio classes |
| Phonetic/domain candidate lookup | Existing knowledge provider with source-supported pronunciation and contrast cards | Candidate spellings, units, argument roles and explicit differences | Slots, PERSON, Audio2Tool arguments | Knowledge narrows legal alternatives; it must not manufacture acoustic evidence or reveal test entities |
| Speaker/time-scoped context retrieval | Existing provider over legal prior observations and current-recording state | Relevant prior mentions and unresolved references, with time/source links | E21/E22 development | Working state is distinct from long-term correction memory; no future turns under current protocols |
| Task contract and normalization checks | Shared adapter validators and registered deterministic transforms | Missing/invalid slots, tool schemas, unit/number ambiguity, supported correction ordering | SLURP and Audio2Tool | Report problems to Reviewer; retain final answer authority and do not repair missing facts automatically |

Do not install several ASR backends and call them independent scientific mechanisms when they implement the same weights. WhisperX is initially an optional alignment integration candidate, not a second Whisper evidence source. Reuse the existing pinned MMS_FA alignment and sealed Sortformer infrastructure before adding duplicate dependencies.

The code audit found concrete reuse points: rails/tools.py supplies tool schemas and registry; rails/phase_tools.py seals post-phase tool state; rails/phase_review.py and rails/phase_planner.py already separate critique from continuation; rails/controllers.py composes bounded phases; core/span_surgery.py and core/model/slices.py bind audio derivations. The shared phase-tool action set now includes a source-bound prepared-speech-observation action alongside task-contract, prepared-knowledge and corrective-memory actions. Its typed OBS evidence is separate from knowledge and retains original tool-contact provenance. See 2026-09-12-prepared-speech-observation-integration-v1.md. A registered real ASR producer remains pending.

The existing ToolResult does not enforce a live decoder's complete source/span/checkpoint/config/output/attempt accounting. Add that governed contract in the shared base before live auxiliary decoding. Reviewer word indices are not audio timestamps. Therefore the first ASR integration should decode an already-bound full short utterance on the configured trigger; targeted audio seconds require the separately validated alignment operation. Recut and decode remain explicit operations because current relisten transitions cannot also invent agent state.

The repository's vendored Whisper code is only a text normalizer, not an installed ASR decoder. The local acquisition is therefore a real new tool preparation, not a claim that the existing scorer dependency already supplies ASR.

Keep neural enhancement and blind source separation outside the first tool comparison. Their changed speech evidence requires its own source-preservation and task-quality experiment. Do not revive previously deferred enhancement work merely because a model is downloadable.

## Experiment order and attribution

1. Finish and analyze the active full matched Audio2Tool recovery at `22b56d706e2f5601dc79f58a8fad2bb6a9629f51`. Preserve the original finalized direct/stage-control and aborted knowledge attempts; read task quality only after all three recovery manifests seal. Retain the current SLURP compact-frame system as the exploratory working baseline; its gain does not establish an isolated knowledge-value effect.
2. Prepare a SLURP tool-observation registration on the same full DEV1000 roster. Use the existing quality metrics and NEW500 analysis identity, retaining historical exposure. Freeze model, prompts, stage count, output budget and source knowledge.
3. Compare the same staged system with a no-new-evidence review/revision path against fixed-policy Whisper evidence supply. Preserve original speech, and start with one additional evidence acquisition and at most one revision. This isolates availability of new evidence from merely adding another reflection turn.
4. If the tool supplies useful evidence, test Reviewer-targeted selection against a matched random selection. Match count and relevant audio-duration strata; use legal state only. Register threshold selection before evaluation. This separates the value of the tool from the value of choosing where to use it.
5. Add word alignment or conflict localization only to resolve a named limitation. Keep their ablation targeted: full transcript versus localized conflict evidence, or fixed span versus aligned span, with matched generation controls.
6. Replicate a promising system on the same roster before admitting another mechanism. A four-row dry run proves wiring only; it cannot establish task benefit.
7. Transfer the retained evidence interfaces to native Audio2Tool and E21 tasks. Give Audio2Tool negation, self-correction, numbers and tool-argument distinctions separate diagnostics. Give E21 PERSON, numbers, non-entity words and insertion changes separate diagnostics.
8. Defer speaker-conditioned context experiments until the shared state/provenance path exists and the first short-task tool experiment is closed. E22 test is closed; any future work must use an explicitly admitted development scope.

Do not preregister a large combinatorial tool grid. Each next experiment must answer a named unresolved system decision. The control stage structure and minimum scientifically meaningful roster are mandatory; a tiny favorable screen is not an effectiveness result.

Report native task outcome, corrections versus newly harmed answers, tool result failures, evidence uptake, unsupported revisions, and per-stratum outcomes. Tool WER and call frequency are diagnostic, not the system objective. Use task quality as the objective; report latency and cost without penalizing them under the owner's current preference.

## Knowledge, working state and memory

Knowledge stores stable source-supported distinctions: tool applicability, similar labels and their differences, argument roles, pronunciation alternatives, unit constraints and evidence needed to distinguish alternatives. Values should answer a concrete ambiguity rather than enlarge the prompt.

Working state stores this run's observations, anonymous speaker mentions, alternative hypotheses and unresolved conflicts. It is versioned and scoped to the current legal context.

Long-term memory stores correction procedures only after independent development validation. A procedure binds the triggering pattern, helpful tool/evidence, applicability boundary, observed failure cases and validation provenance. Do not promote an exposed evaluation error or an attractive one-off reflection into memory.

## Training-free optimization interface

Record state -> action -> evidence -> revised answer -> official reward in the shared trace. An external policy can optimize span selection, tool choice, evidence presentation, knowledge value selection and stop decisions with frozen model weights.

Use legal development episodes to compare candidate actions under matched conditions, then freeze the chosen policy and memory snapshot before evaluation. Preserve independent evaluation and the same-roster replication requirement. Do not train a second answering model. Start with an interpretable fixed policy so a later training-free method has an attributable engineering baseline.

## WSL scheduling and local readiness

Store heavy assets under /home/chao/speech-tools and isolated environments under /home/chao/.venvs. Keep acquisition receipts with source URLs, package versions, revision hashes, file hashes, licenses, local paths, and load status. Never mutate the active research environment.

During current generation, use CPU/network acquisition with a global limit of eight background workers. Only one large auxiliary model may be loaded on CPU at a time. Set auxiliary CUDA visibility empty. Do not create a second GPU service.

For later GPU-intensive preprocessing, schedule an exclusive registered window, cache content-addressed evidence, then restore the frozen decoder geometry. If evidence is precomputed for the entire roster but shown selectively, count all preprocessing contacts and separately count which evidence is actually supplied. A cache hit does not erase the original inference cost.

Classify each tool separately as downloaded, importable, locally loadable, shared-interface integrated, or task-validated. None of these statuses implies the next.

The first bounded shared storage extension is implemented: core.preparation.prepare_artifact accepts the explicit speech-tool contact class. It preserves a source-bound start marker before production, refuses automatic replay after interruption, and reuses validated artifacts without another producer call. See 2026-09-12-speech-tool-preparation-validation.json for the code and test receipt. This storage extension does not authorize inference. The subsequent shared cache consumer now binds the exact query sample, packet identity, source audio/span, checkpoint, decoding configuration, finalized producer attempt and exposure ledger before conditional supply. A real ASR producer and its registered dataset contact remain pending.

## Primary implementation sources checked on 2026-09-12

- OpenAI Whisper transcribe interface: https://github.com/openai/whisper/blob/main/whisper/transcribe.py
- Silero VAD: https://github.com/snakers4/silero-vad
- WhisperX alignment and limitations: https://github.com/m-bain/whisperX
- pyannote.audio local community pipeline and access conditions: https://github.com/pyannote/pyannote-audio

These sources establish tool interfaces, not expected gains on this repository's tasks. Pin the exact acquired revisions in local receipts before research use.
