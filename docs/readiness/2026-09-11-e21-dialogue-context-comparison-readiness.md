# E21 dialogue-context comparison readiness

Status: model-free feasibility note, qualified by OWNER-DATASET-TASKS-010. Summary/memory design is not a new task or required summary evaluation. Test any admitted method against the existing dataset target and metrics. This note does not register an experiment, admit a model contact, or change the running direct-to-KC-E1f baseline.

## Existing evidence and boundary

The proposed dialogue work has one relevant completed observation artifact and one relevant completed transport comparison.

- docs/checks/speech-aware-evidence-acquisition/2026-09-06-e21-diarization-obs/summary.json records a completed, pinned diar-sortformer-4spk-v2 OBS pass for all 44 calls and 1,593 fixed windows. It contains anonymous, call-local time ranges and speaker IDs, not human speaker annotations, reference transcripts, or real identities. The reader is src/speech_aware_evidence_acquisition/reproduction/diarization.py.
- The diarizer has a four-speaker limit: 38 of 44 ConEC rosters exceed four participants and 42 calls reach four detected IDs. It can support uncertain local turn hypotheses and coarse speaker strata. It cannot support a trustworthy cross-call identity store without separate qualification.
- docs/checks/speech-aware-evidence-acquisition/2026-09-08-e21-obs-e1-flight-v1/verdict/result-summary.json records the completed 5,122-contact speaker-turn transport against the 1,593-window direct transport. The reported WER gain and PERSON harm establish a transport tradeoff, but the contrast also changed boundary placement, speaker purity, contact count, and contact length. It does not identify local context as the cause of the PERSON result.
- docs/readiness/2026-09-08-e21-obs-e1-person-harm-decomposition-v1.md records that 78.7 percent of the 61 excess PERSON errors occurred in units shorter than ten seconds. This motivates a bounded local-context hypothesis; it is not evidence that a summary or speaker memory will help.
- docs/receipts/obs/e21-speaker-turn-units-v3.json is the frozen, tool-derived geometry for 44 calls and 5,122 units. Its SHA-256 is b2cb3899531187329b09218d0e09e3003407d0e84918122bc8d8541d08b75976. It preserves turn ownership while adding deterministic local audio bounds. analysis/e21_speaker_turn_units.py implements the deterministic context bounds.
- The E1b local-audio successor and uniform-clock twin remain plans only: configs/experiment/e21-obs-e1b-context-units-v1.json, configs/experiment/e21-obs-e1b-uniform-twin-v1.json, configs/baseline/e21-units-obse1b-context-scored7.json, and configs/baseline/e21-uniform-obse1b-twin-scored7.json. No result should be inferred from them.

## Smallest interpretable comparison sequence

A single contrast cannot identify both chronological local dialogue context and speaker-topic partitioning. The smallest interpretable sequence is therefore two matched pairwise comparisons, with the second conditional on an explicit decision to continue after the first.

1. Hold audio roster, fixed-window geometry, packet representation, prompt template, decoder, delivery rule, output cap, contact cap, and total context allocation fixed. Compare a bounded, same-call chronological local-dialogue view with a matched no-context view. The local view may contain only prior, source-bound same-call observations and frozen-core outputs. This isolates ordered local context from the completed speaker-turn transport change.
2. If a separate comparison is admitted, retain that local-dialogue view unchanged. Compare a speaker-topic index with a topic-only index built from the same atomic source claims, observed-through boundary, memory capacity, update stages, and retrieval budget. This isolates speaker partitioning from the presence of memory itself.

Neither comparison should mix diarizer replacement, audio resegmentation, an unrelated prompt change, an extra answering model, an unbudgeted memory-building stage, or outcome-selected retrieval. A four-row engineering proof can check connectivity only and cannot establish effectiveness.

## Runtime-legal inputs

A future configuration could legally use the following only after pins, ordering rules, and an exposure plan are declared.

- The current source audio range and already observed source ranges from the same call.
- Anonymous speaker observations only after their temporal source boundary is qualified. The existing OBS artifact was derived from the complete call; it may be reused for analysis, but its assignments cannot be fed unchanged to earlier-window prompts under a prefix-causal claim. IDs remain call-local hypotheses.
- The ConEC premeeting participant brief, which is runtime-legal input, and frozen-core observations such as a self-introduction. Neither may be used to claim a calibrated voice identity.
- Earlier same-call frozen-core outputs and source-bound atomic records, provided their observed-through time is strictly before the target boundary.
- A correction record that supersedes rather than overwrites a prior model-derived claim.

The runtime must never receive reference transcripts, gold labels, WER tags, annotation timestamps, future turns, outcome-derived retrieval choices, or a cross-call speaker identity inferred from the diarizer. A later minutes-generation stage may have a distinct full-episode contract; it cannot backfill context into an earlier-window comparison.

## Present reusable seams and current gaps

The existing reusable parts are deliberately static and hash-bound.

- src/speech_aware_evidence_acquisition/reproduction/diarization.py validates the pinned anonymous speaker observation and derives per-window speaker facts.
- src/speech_aware_evidence_acquisition/reproduction/obs_loop.py validates byte-pinned obs_unit_plan inputs, fixed bounds, unit ownership, and overlap stitching.
- src/speech_aware_evidence_acquisition/core/predecessor_snapshot.py loads a hash-verified sealed predecessor snapshot. src/speech_aware_evidence_acquisition/reproduction/repair_loop.py uses that snapshot for fixed-window repair.
- The existing full-window packet and FlightRuntime/OpenJiuwen paths can preserve the current audio, request fitting, cost, trace, and delivery disciplines.

They do not implement a mutable per-call dialogue state, a source-backed speaker-topic index, observed-through enforcement for each retrieved record, or a bounded memory-update transition. obs_loop.py rejects a pinned unit plan combined with obs_condition_tail_chars; repair_loop.py also requires a zero tail; and window_controller.py accepts only the fixed direct-only program. Turning on a rolling tail, judge, or retrieval field would therefore not implement the proposed comparison safely.

Any later shared extension needs to make chronology, source ranges, anonymous-speaker uncertainty, memory records, retrieval decisions, update contact costs, and final-answer authority explicit and traceable. The frozen core must remain the only answerer.

## Readiness conclusion

The completed diarization OBS artifact is reusable for analysis; runtime use needs separate temporal qualification. Frozen unit geometry, the static predecessor-binding path, and the current full-window packet route remain available within their original contracts. The scientifically interpretable next comparison is a matched local chronology contrast before any speaker-topic-memory contrast. A new stateful shared controller and provenance contract are still required before either can be admitted. This note records readiness only; it makes no quality, meeting-minutes, or causal claim.
