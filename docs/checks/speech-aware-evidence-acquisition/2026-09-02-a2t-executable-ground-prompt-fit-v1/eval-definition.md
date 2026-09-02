# Eval Definition: A2T Executable Ground Prompt Fit V1

## Capability evals

| id | criterion |
|---|---|
| E01 | The external handbook and in-repository build receipt match their preregistered SHA-256 values. |
| E02 | The exact direct and one-state AgentLoop envelopes render through the pinned live chat template with one media marker each. |
| E03 | The capacity bound includes 455 measured speech tokens, two special tokens, a 1,024-token completion allowance, and a separate 1,024-token observation-body allowance for the AgentLoop envelope. |
| E04 | The worst envelope has a strictly positive margin in one 32,768-token serving slot. |
| E05 | Contact accounting is exactly one props request, two template requests, and no more than four tokenizer requests, with zero decoder evaluations and generated tokens. |

## Regression evals

| id | criterion |
|---|---|
| R01 | Existing executable-ground builder and audit tests remain green. |
| R02 | The check refuses handbook, build-receipt, serving-fragment, runtime-receipt, context, chat-template, or media-marker drift. |
| R03 | No model completion, audio decode, gold, test, retriever, embedding tool, or external-network surface is reachable from the check. |
| R04 | The handbook bytes are never rewritten or selected in response to measured token counts. |

## Success rule

All capability and regression evals must pass at the first registered attempt. A failure closes V1
and permits only a separately preregistered model-free successor; it never permits an in-place
prompt edit after token counts are read.
