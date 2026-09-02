# Evaluation definition — A2T-GROUND-QUAL-104 packet preprocessing

## Unit

The unit is one receipt-pinned WAV recording in `A2T-GROUND-QUAL-104`. The operation is label-free
speech-feature materialization, not task answering.

## Frozen inputs

- Cohort receipt SHA-256:
  `eeb90abbe8695e449c676f18339db6618cb6d606d6c1e7c656626e4e9b6b6c16`.
- Run identity:
  `fbd4addd541ff29214cbff7c35564b15f27e2fb7f438202b79d694b1c5961d4b`.
- Count and duration: 104 recordings and 543.107 speech-audio seconds.
- Preprocessing runtime: `docs/receipts/runtime-q4km-preprocess.json`.
- Legacy cache: `/home/chao/feat-cache/audio2tool-q4km-04ccc72a`.
- Packet root: `/home/chao/feat-cache/a2t-q4km-packets-04ccc72a`.
- Fixed instruction: `Observe the complete speech signal for deterministic feature preprocessing.
  Respond with OK.`
- Completion cap: one token.

## Pass conditions

1. The exact 104 receipt identities and audio SHA-256 values resolve without drift.
2. Exactly 104 contacts complete with zero failures, within 120 calls and 650 audio seconds.
3. The CPU-only receipt-pinned sidecar stops before promotion; the GPU decoder receives zero request.
4. Exactly 104 packets are promoted; every audio, decoder, mmproj, encoder-receipt, and packet hash
   verifies; the exclusive promotion receipt is complete.
5. The report records every packet's `n_tokens`, plus minimum, maximum, mean, median, p90, and p95.
6. Gold, task annotations, task-response meaning, scorer, test data, retriever, embedding tool,
   tokenizer endpoint, paid API, and external network remain unopened.

## Prompt-fit inheritance

Qualification may inherit `SAEA-A2T-MF-EXECUTABLE-GROUND-PROMPT-FIT-V1` only if the measured packet
maximum is at most 455 tokens. A larger maximum is not a preprocessing failure and must not cause
truncation; it closes qualification pending a separately registered exact envelope successor.

## Non-metrics

Network jitter, packet loss, injected latency, retry behavior, and fault-stressed throughput are not
measured. This row makes no task-accuracy, model-comprehension, agent-gain, information-gain, or
training-free-control claim.
