# D-1 probe: do behavioural quality signals predict error? (2026-08-09)

**Exploratory, n=10 calls, offline on existing traces — zero model touches, no
exposure row required.** Not powered for a precise estimate; the purpose is to
decide whether a direction is worth building.

## Question

Behind a chat endpoint there are no logits, so any self-monitoring the agent
does must be behavioural. Do cheap per-call signals predict the call's WER?

## Signals tested (E-001 outputs + traces, frozen scorer for WER)

| signal | Spearman ρ vs per-call WER |
|---|---|
| s1 words per speech-second | **+0.21** |
| s4 type–token ratio | **−0.30** |
| s5 digit-token share | **−0.31** |
| s2 slices per call / s3 words per slice | invalid this round — the trace
payload is a Python-repr string and the parser mis-counted (every call read as
1 slice). Fixed for the next pass; conclusions below do not depend on them. |

**No signal reaches |ρ| ≥ 0.6, and at n=10 none is distinguishable from
noise.** Within a healthy run, these signals do NOT rank calls by quality.

## The result that matters: regime detection, not quality ranking

The same signal computed across the two protocol regimes:

| regime | example | words / speech-second |
|---|---|---|
| collapsed (retired whole-call protocol) | 16 words over 4,307 s | **0.004** |
| healthy (obs-agent-loop) | 10,335 words over 4,307 s | **2.40** |

≈ **600× separation.** So s1 is a **regime detector**, not a quality ranker: it
identifies a catastrophically failed observation with three orders of magnitude
of margin, and says nothing useful about how good a working transcript is.

## Consequence for W-D (design corrected before anything was built)

- **D-2 (selective re-observation) must trigger on catastrophic signals**
  (e.g. words/speech-second below ~0.5, i.e. two orders of magnitude inside the
  gap), not on "the worst 15 % of slices" as originally sketched — that
  fine-grained trigger has no empirical support and would fire on noise.
- **D-3/D-4 (routing, cost-aware evidence) cannot use these signals as-is** to
  choose per-input policy; they need either a different signal class or an
  ordinal target coarser than WER. Building them on this signal set is not
  justified by evidence.
- A fine-grained quality signal remains an open problem worth one more cheap
  probe (candidates: per-slice boundary-fallback rate, retry incidence,
  cross-slice entity inconsistency count) — but on slice-level rather than
  call-level granularity, where the variance is larger and n is ~600 instead
  of 10.

## Honest limits

One healthy run, 10 calls, one carrier (earnings22 dev). The regime-separation
claim rests on comparing two protocols rather than on within-regime variation.
The corrected slice-level parser should be re-run against the R4 traces (3
arms × 610 slices) when they land, which gives ~1,800 slice-level observations
and a real chance to test the fine-grained question properly.
