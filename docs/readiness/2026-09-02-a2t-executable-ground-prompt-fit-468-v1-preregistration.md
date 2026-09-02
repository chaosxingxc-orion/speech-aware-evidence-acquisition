# A2T executable-ground prompt-fit 468 v1 preregistration

Date: 2026-09-02. Status: **EXECUTED; PASS**.
Experiment id: `SAEA-A2T-MF-EXECUTABLE-GROUND-PROMPT-FIT-468-V1`.
Execution profile: `model-free-check`.

## Question

Does the exact full executable handbook still fit one 32,768-token serving slot when the fresh
`A2T-GROUND-QUAL-104` packet maximum replaces the old 455-token speech reserve with the measured
468-token reserve?

## Frozen sources and permitted computation

The only sources are:

- the landed prompt-fit result
  `docs/checks/speech-aware-evidence-acquisition/2026-09-02-a2t-executable-ground-prompt-fit-v1/prompt-fit-result.json`,
  SHA-256 `627e0efb01595eb45751a448fcc2b9029ce35f38f73810107506226f86a55c63`;
- the ground preprocessing report
  `docs/checks/speech-aware-evidence-acquisition/2026-09-02-a2t-ground-qual-104-preprocess/preprocess-report.json`,
  SHA-256 `c2120c9500ac943dc485d1953087965312e13f491ee850775df23347c4dccb0a`;
- the external promotion receipt, SHA-256
  `b350567a6dd8b5d9021725756424f2b6ae99803c8c0327901c724fe3ebe8a47f`.

The computation must verify both repository hashes, the promotion-receipt binding recorded by the
preprocess report, all 104 packet counts, and the measured maximum of 468. It may then replace only
`speech_feature_token_reserve`: 455 becomes 468 in both frozen envelopes. Text prompt counts,
special-token reserve, observation allowance, completion allowance, slot count, context size,
handbook bytes, messages, chat template, model, and runtime remain unchanged. Every derived value is
recomputed by integer arithmetic; no prior pass/fail field is copied.

## Pass conditions

For each envelope:

`prompt = text_prompt_tokens + speech_reserve + special_reserve + observation_allowance`.

The worst envelope then requires `prompt + 1,024` completion tokens. Pass requires this quantity to
be at most 32,768, a strictly positive margin, unchanged source/message/runtime identities, and no
source drift. The result must report both old and new reserves and the exact 13-token delta.

## Contact and scope boundary

Allowed contacts are exactly zero: no frozen-core endpoint, tokenizer endpoint, audio decode, local
or external network, retriever, embedding tool, scorer, paid API, or GPU. Gold, labels, query text,
task responses, scores, rewards, protected unexposed data, and test annotations remain unopened.
Network jitter, packet loss, injected latency, and retry stress are out of scope.

Failure leaves ground qualification closed. Passing authorizes only separately preregistered
qualification implementation and zero-contact preflight over the already frozen 104 roster and 104
packets. It authorizes no task contact by itself, no pruning, no training-free control, no
approximately-1,000 scale, no baseline change, no test access, no Stage-3, and no paper-scale work.

## Execution closure

The source-bound integer computation passed. The worst `ground-agent-observed` envelope is 14,066
prompt tokens and requires 15,090 tokens with the frozen 1,024-token completion allowance, leaving
17,678 of the 32,768-token slot. Result SHA-256:
`277f5147b8ce1ac9acca538e4b8a83a2c5b282c62f278afd56e27c9fd61a2fd5`.

The run recorded zero contacts and zero outbound attempts. Two earlier invocations wrote no result:
the runner incorrectly treated its mutable guard counter object as a boolean, although its recorded
count was zero. The corrected runner reads `.count` and `.targets`; it changes no input, arithmetic,
or gate. Five unit tests pass, and the repricing module has 85% statement coverage.
