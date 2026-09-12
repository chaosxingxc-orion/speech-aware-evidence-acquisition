# SLURP cached Whisper treatment configuration template

These templates freeze the matched treatment configuration before the registered Whisper catalog exists. They are deliberately stored outside the configs directory because the catalog SHA-256 is the only unresolved field and the shared configuration loader must reject placeholders.

Root must replace UNRESOLVED_AFTER_REGISTERED_WHISPER_CATALOG_SEALS with the actual lowercase SHA-256 of the sealed catalog at prepared/SAEA-SLURP-WHISPER-OBSERVATIONS-V1/attempt-slurp-whisper-observations-v1/catalog.json. Root then writes the final baseline to configs/baseline/slurp-speech-observation-whisper-v1.json and the final experiment to configs/experiment/slurp-speech-observation-whisper-v1.json.

Do not prepare recall before that replacement. After the catalog is bound, prepare the treatment's distinct solve recall through the shared FlightRuntime.prepare_phase_recall entry point. Verify all 1,000 selected value IDs and their serialized order against the control receipt. Only the returned prepared_phase_recall.solve pin and readiness or other excluded receipt fields may change afterward.

Scientific admission, immutable generation and fit registrations, service admission, actual live-phase fitting, generation and scoring remain root-owned and pending. These files authorize no model, speech tool, tokenizer, GPU or scorer contact.
