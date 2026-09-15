# STATUS-139: SLURP runs; E21 direct fit registration is frozen

Date: 2026-09-15. The owner GPU resume remains active. The existing frozen
SLURP broad/factored TRAIN-A campaign remains live under worker PID 293426 and
server PID 293153 on its same np4 service. No treatment quality has been read.
Model-call counts do not establish completed rows. Shared telemetry is missing
before 17:11:58 UTC, and the current campaign alone owns its first complete
official score.

The exact metadata for the post-seal paired analysis is now bound:

- DATA/coordination/slurp-broad-factored-v1/analysis-metadata-v1.json,
  SHA-256
  `53bd634b121b7b21d5172a56ed8cacfce8fa3065643f362b02a5faf2af7bd980`;
- DATA/coordination/slurp-broad-factored-v1/analysis-metadata-binding-v1.json,
  SHA-256
  `a2426724684ba106ec1b9a0291685915d4f6626a845485e2520ac907df944740`.

The binding covers 1,080 rows, 125 speakers and 18 scenarios. The
[post-seal analysis recipe](../../../readiness/2026-09-15-slurp-broad-factored-train-a-analysis-recipe-v1.json)
remains the governing source-bound recipe after a complete seal.

The Audio2Tool direct/system scope-tools pair remains fully registered,
integrated and source-frozen at
`219e305f306f11998e39c44b5fb055b4fcfb3179`. It waits for the SLURP
generation seal and custody boundary. Its same-process direct/system campaign
and next-dispatch recipe are unchanged.

The E21 stable-source admission is recorded at
DATA/coordination/e21-native-window-registration-v1/admission-v1.json with
SHA-256
`de78bb55f4fcb46e0b04432da997dc2ff3c8e5a002d358646f7cdcd0542272e8`.
The [direct-fit registration](../../../readiness/2026-09-15-e21-native-window-direct-fit-registration-v1/README.md)
is integrated and source-frozen at
`1daad5186119b23c3414e36676afb296599dc29f`. It changes six files and no
production change. Sixty-eight focused tests and four later correction checks
passed; the counts overlap and are not additive. The registered fit covers all
1,593 windows and exactly 4,780 endpoints.

Root reviewed the shared runtime plan and exposure parser in
DATA/coordination/e21-native-window-registration-v1/root-direct-fit-registration-review-v1.json,
SHA-256
`860e6aeac19e1c09ff93d86bc083211b97d12b326b80f1e32b8a6f54609bbe9e`.
The canonical integration receipt is
DATA/coordination/e21-native-window-registration-v1/direct-fit-canonical-integration-v1.json,
SHA-256
`4f60505c2c74aac483837936430ff50d5dc3b6c1cca934792db6cd9d10da9b25`.
The source-freeze receipt is
DATA/coordination/e21-native-window-registration-v1/direct-fit-source-freeze-v1.json,
SHA-256
`8dde1eb0536a7a1386844134a610648bea219cec088b21c765792f18e2533d0e`;
its manifest SHA-256 is
`06216ba9b5aa95320da849f7666946921956b293fd335b063fc164bcd9373539`
over all 5,732 tracked files.

The selected entry is the existing attach-only `prompt-fit` CLI. Root must
first start and verify the exact service and its first shared monitor sample,
then mint the standard `GenerationLease`. Do not use `coordinate-fit`,
whose monitor ownership does not match this registered route. No model,
tokenizer, fit, tool or service contact occurred during registration, and the
actual fit receipt remains absent. Generation, realized native fit and CPU ASR
remain held and unregistered.

The active order remains SLURP, Audio2Tool, then E21. Preserve prior failed
verdicts. Stable benefit for these queued system versions and trajectory-sampling or
training-free RL remain unproven. This update performs no inference, outcome read, service operation,
scoring or statistical interpretation.
