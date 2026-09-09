# Existing output-budget metadata audit

Owner question: determine whether a 64-token SLURP completion cap can constrain structured output and whether reasoning should be evaluated separately.

Read existing sealed KC-S1b and the seven recovered KV manifests and hash-bound traces only to extract completion lengths, request output ceilings, stop/saturation metadata, retries and schema/delivery statuses where retained. Do not read gold/reference transcripts into runtime, rerun scoring, tokenize outputs through a service, or issue any model/encoder request. Do not print answer bodies into review output. Missing stop reasons remain unknown; reaching a cap is not proof that a valid answer was truncated.

Compare per-run rates and existing length distributions. This is a retrospective engineering audit, not a treatment effectiveness test. A prospective 64-versus-256 comparison or bounded-reasoning treatment needs separate config, fit and exposure registration; neither is admitted by this audit.
