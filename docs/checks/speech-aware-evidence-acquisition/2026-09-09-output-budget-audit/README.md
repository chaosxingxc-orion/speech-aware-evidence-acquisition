# Existing SLURP output-budget audit

Root verified the sealed manifest and trace hashes for KC-S1b and all seven recovered KV runs. Every one of the 8,000 MODEL_REQUEST records declares max_tokens=64. Every run has 1,000 recorded responses.

KC-S1b completion lengths: median20, 95th percentile38.05, 99th percentile61; four responses reach64 (0.4%). The seven KV runs each have three or four at-cap responses. These are retrospective length diagnostics, not accuracy estimates. No gold data, generated answer bodies or scoring output was used in selection. No service, tokenizer, encoder or scorer was contacted.

Historical normalized response traces do not preserve finish reasons. At-cap therefore does not establish truncation. The phase schema identifiers are available, but those identifiers do not certify JSON validity; validity remains unassessed here. A selected four-row engineering comparison will examine actual stop reasons and structural completeness.

The selected cases are two historical at-cap rows, the longest non-cap row and a median non-cap control, with deterministic sample-ID tie breaks. This purposive set is not an efficacy roster. The machine-readable report retains the selection and all source hashes. Raw trace bytes remain in the external data root.
