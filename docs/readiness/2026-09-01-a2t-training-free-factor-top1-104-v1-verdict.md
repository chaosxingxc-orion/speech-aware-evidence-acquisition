# Audio2Tool training-free semantic-factor top-1 v1 — liveness failed before scoring

Date: 2026-09-01. Status: **MECHANISM FAILED; DO NOT SCORE OR SCALE**.
Experiment: `SAEA-A2T-TFRL-FACTOR-TOP1-104-V1`. Committed structural result:
`docs/checks/speech-aware-evidence-acquisition/2026-09-01-a2t-factor-top1-104-v1/mechanism-result.json`.
Its SHA-256 is `1cca5291452022d1897144ad41073b37c0cf29445e5359bcd189197d4cae85b8`.

## Verdict

The strict semantic-factor channel failed before it could acquire any evidence. All 103 recovery
samples returned factor-contact responses, but none passed the frozen exact parser. Eighty-two
responses were not exact JSON and 21 were JSON objects with the wrong field set. Consequently,
deterministic BM25 produced zero available top-1 registry rows across all eight tiers. The
registered factor-parse and retrieval-liveness gates failed at 0% against their 95% and 90%
minimums.

This is a terminal negative result for the registered strict-factor-to-BM25-top-1 mechanism. The
result does not establish agent-over-single-call benefit, information gain, or a training-free RL
contribution. It cannot be followed on these returns by schema relaxation, JSON extraction,
larger `k`, a supplied menu, BM25 tuning, state-bin search, or a lower promotion threshold.

## Evaluation and scorer efficiency

The user-proposed efficiency rule remains adopted: preserve the official scorer as an unchanged
single-process program over one complete manifest, and run independent complete-manifest jobs
concurrently through `scripts/evaluate_parallel.sh --workers 2`. The earlier self-consistency
flight measured a 1.9065-times effective speedup for two such whole-manifest jobs.

This flight correctly did not invoke either scorer. No available top-1 rows meant that the frozen
two-per-tier resend control could not be formed, neither complete manifest sealed, and the
pre-scoring liveness gate stopped the run. There was no shard, shard-level score, score averaging,
gold read, or scorer modification.

The run also exposed a broader evaluation-efficiency issue. The current generic trajectory runner
required a diagnostic final contact even after a factor was invalid, so all 103 recovery samples
spent a second contact with zero supplied evidence. Future two-stage probes must first complete the
whole ORG batch, apply its label-free liveness gate, and only then launch the USE batch. That phase
boundary would have saved 103 model contacts here and will make failures cheaper without changing
the scientific criterion.

## Attempts and accounting

The first preflight refused a developer-binary mismatch with zero contact. A receipt-pinned canary
then consumed five contacts and 7.986 metered audio seconds; three factor requests received HTTP
500 because the server could not combine its peg-native output contract with OpenAI
`response_format`. The registered recovery removed only that server-side constraint and retained
the exact external parser. It completed 206 request/response/cost triples over 103 samples and
1,169.760 metered audio seconds, then stopped at the frozen resend-availability gate.

Cumulative use was 211 of 228 registered contacts and 1,177.746 of 1,340 registered audio seconds,
with zero paid API spend. The resend attempt never started. Only coarse response shape and parser,
retrieval, request, and accounting structure were inspected; no response meaning, task answer,
label, official score, test annotation, or future turn was read.

The receipt-pinned experiment binary is preserved at
`/home/chao/llama.cpp-featcache/build/bin-receipt-04ccc72a-after-factor-top1`. The developer runtime
for commit `9a41ce51850898973a41c39f9224818ff1a7fbe2` is restored at the active build path, and no server
remains running.

## Next design constraint

The next admissible branch must change the information interface rather than post-hoc repair these
factor outputs. It should use a batch-level acquisition gate, prove that its control state and
evidence channel are live without gold, and reserve official scoring for complete candidates that
pass that gate. It must begin at approximately 100 discovery samples under a new preregistration.
Only a stable fresh-split gain that separately establishes information gain, agent-over-single-call
benefit, and a training-free control contribution can justify expansion toward approximately 1,000
samples.

This result opens no remaining exposed-296, G2, unexposed Audio2Tool population, FINAL60, test,
Stage-3, or paper-scale work.
