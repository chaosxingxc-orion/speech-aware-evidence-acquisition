# Evaluation definition — executable-ground prompt fit at 468 speech tokens

## Unit

One frozen prompt envelope. There are exactly two: `ground-direct` and `ground-agent-observed`.

## Transformation

Verify the two frozen source files and replace only the speech reserve, 455 to the complete-packet
maximum 468. Recompute prompt requirement and one-slot margin using integer arithmetic.

## Primary gate

The maximum across both envelopes plus the frozen 1,024-token completion allowance must not exceed
the frozen 32,768-token per-slot context. The margin must be positive.

## Forbidden

Do not contact a model, tokenizer, scorer, retriever, embedding tool, network service, audio decoder,
or GPU. Do not read gold, labels, query text, task responses, scores, rewards, protected unexposed
data, or test annotations. Do not change, prune, summarize, reorder, or truncate the handbook,
observation, audio packet, or message bytes. Do not measure network jitter or retry behavior.
