# R4 (SAEA-E-002) analysis plan — pre-registered before any arm result is read

Status: DRAFT written 2026-08-09 while SAEA-E-001 was still running and before
any R4 arm had executed. Commits to the repo after E-001 finalizes (avoiding
HEAD churn mid-run). Purpose: fix the judgement rule in advance so no
statistic is chosen after seeing the numbers.

## The claim under test

Siskos-direction monotonicity on a frozen speech carrier, under our boundary:
supplying a call's OWN contextual materials improves transcription; supplying
ANOTHER call's materials does not.

Pre-registered success criterion (already in the exposure rows):

    WER(matched) < WER(no-context)  AND  WER(matched) < WER(mismatched)

## Design

- Carrier/sample: `r4-e21-sub10` — seeded 10-of-44 subset of the frozen
  earnings21 discovery split (sample-once receipt, manifest-bound).
- Arms (same samples, same protocol, same model; ONLY the SUPPLY channel
  differs): `no-context` (bare-core-ojw) / `matched` (fixed-legal-context-ojw,
  each call's own ConEC contexts layer) / `mismatched`
  (mismatched-evidence-ojw, deterministic rotation derangement).
- Instruction text is IDENTICAL between matched and mismatched (equalized
  2026-08-08 after the design-leak fix), so the arms differ only in evidence
  content.
- Unit of analysis: the CALL (10 per arm), not the slice — slices are an OBS
  implementation detail; the hypothesis is about call-level transcription.

## Statistics (fixed now)

1. **Primary**: per-call WER from the frozen scoring stack, paired across arms
   (same 10 calls in every arm). Report per-arm mean and median WER.
2. **Paired comparison**: Wilcoxon signed-rank on the 10 paired differences,
   two-sided, for each of the two contrasts (matched vs no-context; matched vs
   mismatched). With n=10 the minimum attainable two-sided p is 0.002, so the
   test can in principle reject at 0.05; it is nonetheless underpowered for
   small effects — see "What this design can and cannot show".
3. **Effect size**: median of the paired WER differences, with a
   bootstrap 95% CI (10,000 resamples over calls, fixed seed 20260807).
4. **No subgroup slicing, no per-slice tests, no alternative metrics** are
   admitted post hoc. Per-entity-class WER stays DEFERRED (no owner-pinned
   `wer_tags` adapter exists); if that adapter later lands, it becomes a new
   pre-registered analysis, not a re-cut of this one.

## What this design can and cannot show

- **Can**: whether the direction holds on this carrier under our boundary, at
  a sample size adequate for a large effect (Siskos reports ~4.8 WER points
  between no-context and retrieved-context; a paired effect of that size is
  detectable at n=10). Whether mismatched evidence HARMS relative to matched
  (the negative-control direction) — this is the part no published work on
  our carriers has ever measured under a frozen-core boundary.
- **Cannot**: (i) an absolute WER comparable to published Siskos/ConEC numbers
  — different model, INT4 quantization, different segmentation protocol;
  (ii) any claim about the 44-call discovery split as a whole, let alone the
  corpus — this is a 10-call probe; (iii) any confirmatory claim whatsoever
  (Stage-2 discovery/dev only).

## Failure modes to report honestly (not to explain away)

- If `matched ≈ no-context`: report as a null on this carrier at this n, with
  the observed CI, and treat the *mechanism* (evidence injection) as
  unsupported here rather than reaching for a different metric.
- If `mismatched < matched` (wrong direction): that is evidence the gain, if
  any, is not content-relevance but prompt-length/format — an important
  negative result the rotation control exists precisely to expose.
- If arms differ in slice counts (boundary decisions differ under different
  prompts): report the counts; the WER unit is the call, so differing slice
  counts do not invalidate the comparison but must be disclosed.
- Quantization noise (measured Q4-vs-Q8 agreement 1.50% WER) is common-mode
  across arms and cancels in the paired differences, but the absolute WERs
  carry it; state this in every reported number.
