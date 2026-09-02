# A2T executable-ground qualification 104 v1 preprocessing verdict

Date: 2026-09-02. Experiment: `SAEA-SN-A2T-GROUND-QUAL-104-PREPROCESS`.
Verdict: **PACKET PREPROCESSING PASSES; PROMPT-FIT INHERITANCE STOPS ON THE MEASURED MAXIMUM**.

## Execution result

The registered one-shot attempt `attempt-20260902T130411Z-a2tgroundqualpre` completed all 104
receipt-pinned contacts with zero failures and 543.107 speech-audio seconds, within ceilings of 120
contacts and 650 seconds. It produced 10,933 prompt tokens and 104 completion tokens; response
meaning was never read. The receipt-pinned CPU-only sidecar stopped normally after `SIGTERM` without
a forced stop. The GPU decoder received no request and was unreachable before and after.

The promotion produced exactly 104 audited packets under
`/home/chao/feat-cache/a2t-q4km-packets-04ccc72a`, using llama.cpp build
`04ccc72a2207347ca76161b93fd9d846dd0a8675`. Every packet audio hash matched the frozen cohort
receipt, and every packet carried the receipt-bound decoder, mmproj, and encoder provenance. The
promotion receipt SHA-256 is
`b350567a6dd8b5d9021725756424f2b6ae99803c8c0327901c724fe3ebe8a47f`; the trace-manifest SHA-256 is
`c71477e2a7f31bf46cbb7bc97e079058ae0a6099246e4bbfa6de18aaf040361f`; and the repository report
SHA-256 is `c2120c9500ac943dc485d1953087965312e13f491ee850775df23347c4dccb0a`.

## Packet-size result

Complete-packet speech tokens are: count 104, minimum 13, median 65, mean 75.125, p90 143, p95
169, maximum 468, and sum 7,813. The maximum is `tier7_multiturn/001590` at 468 tokens. It exceeds
the inherited 455-token reserve by 13 tokens. No packet was truncated, split, resampled, removed, or
selected by size.

The preprocessing result is valid, but the old full-handbook prompt-fit receipt cannot be inherited
literally. Ground qualification remains closed until a separately preregistered model-free successor
recomputes the exact direct and one-state AgentLoop envelopes with a 468-token speech reserve.

## Boundary and next permission

No query text, handbook, registry, label, reference transcript, expected call, prior task response,
score, reward, test annotation, scorer, retriever, embedding tool, tokenizer endpoint, external
network, or paid API was opened. Network jitter, packet loss, injected latency, and retry stress were
not measured. The protected unexposed 400 remains unopened.

This verdict authorizes only the 468-token model-free prompt-fit successor. It does not authorize
ground task inference, candidate pruning, training-free control, approximately-1,000 scale, baseline
change, test access, Stage-3, or paper-scale work.
