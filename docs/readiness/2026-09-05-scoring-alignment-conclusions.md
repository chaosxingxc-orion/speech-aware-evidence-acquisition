# Scoring alignment conclusions, three carriers (2026-09-05)

Owner goal (2026-09-04): per carrier, our number must sit within 3 points of the published number under both our
scorer and the official scorer, or better; align what can be aligned first; never below a degraded model's
published number. The axes that matter are the prompt, the way the model is used, and the scoring script. This
note consolidates the verdicts landed between 2026-09-04 and 2026-09-05; every number below is read from a
sealed manifest scored once through `core.scoring_batch`, and every published number from the literature reports
in the session record. The frozen core throughout is Qwen3-Omni-30B-A3B-Instruct, Q4_K_M GGUF, llama.cpp featcache
build 04ccc72a, greedy decoding.

## 1. Status under the 3-point rule

| carrier | our number (official metric) | published target | floor | status |
|---|---|---|---|---|
| Earnings-21, all 44 discovery calls, Whisper-normalized corpus WER | **8.200** | whisper-large-v3 9.71 (ASR Leaderboard long-form), large-v2 9.7, TRADE 9.75 | medium.en 10.2 (strict), base.en 12.5 | **ALIGNED**, every floor cleared |
| Audio2Tool, eight tiers, official code protocol and scorer, n = 500 per tier | equal-domain: 7 of 8 tiers inside the band, 5 above the paper; natural mixture: 1 of 8 (tier 8) | Table 3, Qwen-3-Omni-30B | Qwen-2.5-Omni-7B, cleared on every tier (tier 2 by -1.0 inside CI) | **ALIGNED on equal-domain weighting except tier 1**; NOT ALIGNED on the natural mixture |
| SLURP, DEV-1000, official `evaluate.py` micro | closed-list direct baseline intent 71.40 / SLU-F1 35.80 | weak commercial pipeline 72.06 / 64.02; strong pipeline 78.33 / 70.84; prompt-only ChatGPT over transcripts 79.25 intent | no prompt-only published SLU-F1 exists | **intent ALIGNED** with the weak pipeline and the prompt-only cascade; **SLU-F1 NOT ALIGNED** (28 points under the weakest trained system, no like-for-like target) |
| Earnings-22, ESB short-form test (6 confirmatory calls, read once) | 15.937 | the same frozen model's published 9.79 (NeMo) / 12.3 (Nemotron) | whisper-large-v3 11.59, base.en 15.09 | **NOT ALIGNED** |

## 2. What was aligned on each axis, and what was excluded by measurement

Audio2Tool. Prompt and scoring: the released code (github.com/audio2tool/Audio2Tool @ b9d5383c) is mirrored
string for string (full 152-tool registry as compact text, `tool_name(k=v)` output, first-call parse,
primary-tool accuracy) with its `metrics.py` vendored as `a2t-toolcall-official`; our `a2t-toolcall-v2` now
parses the same format and agrees with the official scorer exactly on every single-call tier. Model usage: raw
audio through the bf16 mmproj; the Q8_0 probe (expert offload, paired on the frozen 400) is identical to Q4_K_M
on tier 1 (50 of 50 rows) and on wearables (95 of 95); quantization is excluded and Q4_K_M stays the operating
core. Population: the release's own first-successful-speaker rule at n = 500 per tier. Excluded by measurement:
the old reconstruction (-5.5 pp), the whitespace prompt variant (+1.0, null), the roster (+5.6), quantization
(0.0 on tier 1). Open: the published tier-1 row (92.4 / 92.4) is not reproduced by five sealed cells, and the
gap on every tier is one stratum, smart_home, where 889 of 908 misses name another real registry tool, mostly
its cross-domain twin. The llama.cpp audio front-end versus the HF processor is the one unmeasured model-usage
difference; the paper's population composition and internal tool taxonomy are unknowable without the authors.

Earnings-21. Scoring: the Whisper English normalizer, corpus-level, is the paper-facing metric beside the frozen
`saea-scoring-v1`; the two families are never mixed, and the August ConEC-names gain inverts under the standard
normalizer (names trades substitutions for deletions). Model usage: the sealed protocol (90-s windows, no VAD,
verbatim instruction) with the GPU-resident encoder, all 44 calls including 4346923 (18.94 alone).

SLURP. Scoring: the pinned official `evaluate.py` with the identity check against the per-sample port, N-predicted
reported (the script silently skips unanswered rows). Prompt: the sealed M0 listed scenarios, actions and entity
types but not the scenario_action pairing; adding the 60 TRAIN-observed pairs lifts intent 53.60 to 71.40 (+17.8,
CI90 +15.7 to +19.9) with SLU-F1 unchanged. Consequence for the locked knowledge cell: BLEND's intent margin over
the direct baseline is +4.3 pooled and +2.6 (CI90 -0.2 to +5.6) on the unexposed 500; slot filling is the open
target and is not a prompt problem.

Earnings-22 short-form. The one-time read is spent. On the dev split (6,038 ESB-train utterances) the prompt text
(verbatim vs the model card's default: -0.83, verbatim better) and the model card's request shape (no system
message, text after audio: corpus +0.32 worse, per-utterance mean better, length ratio 1.086 to 1.040) are both
excluded as causes; over-generation was a symptom (insertions traded for deletions, substitutions flat). Remaining
suspects in order: the cleaned ESB reference layer's conventions (model-free), a self-run whisper-large-v3 anchor
on our exact rows (needs an asset admission), context-free clipping, quantization.

## 3. Standing decisions and next step

- Operating core: Qwen3-Omni Q4_K_M on build 04ccc72a; Q8_0 is 7.85x slower per call for +2.25 pp overall.
- Direct baselines from now on: Audio2Tool = the official-protocol cell (report natural-mixture and
  equal-domain weightings, per domain); Earnings-21 = the 44-call bare-core cell under the Whisper normalizer;
  SLURP = the closed-list direct baseline under the official script. Every mechanism claim is paired against these
  sealed manifests, never against a re-flown control (greedy decoding is not bitwise reproducible across batch
  shapes on this runtime).
- Alignment is as clear as the published material allows on Audio2Tool, Earnings-21 and SLURP intent; the
  Earnings-22 short-form gap and SLURP slot F1 are recorded as open with their next suspects named. Mechanism
  design (knowledge and the agent system) starts from three measured targets: Audio2Tool smart_home twin-tool
  confusion, SLURP slot filling, and Earnings entity classes PRODUCT / NORP / FAC under the ConEC no-bias floor.

Verdicts: `2026-09-04-a2t-official-protocol-replication-v1-verdict.md`,
`2026-09-04-a2t-tier1-official-population-v1-verdict.md`, `2026-09-04-a2t-tier258-official-population-v1-verdict.md`,
`2026-09-04-a2t-tier3467-official-population-v1-verdict.md`, `2026-09-04-a2t-q8-quantization-probe-v1-verdict.md`,
`2026-09-04-scoring-alignment-audit-slurp-earnings.md`, `2026-09-04-e21-full44-direct-baseline-v1-verdict.md`,
`2026-09-04-e22-esb-shortform-alignment-v1-verdict.md`, `2026-09-05-e22-dev-esb-prompt-ab-v1-verdict.md`,
`2026-09-05-e22-dev-esb-shape-c-v1-verdict.md`, `2026-09-05-slurp-closed-list-direct-baseline-v1-verdict.md`.
