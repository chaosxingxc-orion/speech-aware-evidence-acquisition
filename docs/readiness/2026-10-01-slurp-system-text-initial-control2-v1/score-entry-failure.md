# Initial A/A scoring-entry failure and proposed bounded disposition

Status: STOPPED; proposed owner decision216 is pending. No recovery is authorized
by this document. The initial family READ remains unsigned and all feedback remains
unread. Preserve the queue, STOP, generation artifacts, failed score batch and frozen
worker exactly as observed.

At 2026-10-01T20:48:14Z the campaign exited with code1; the driver wrote STOP at
20:48:19Z. Seed is FINALIZED with400 rows and one successful complete official score.
A/A generated400 rows in2,792 model contacts but its scoring worker exited at the
E0/D3 entry gate. Its attempt remains OPENED and its COMPLETED generation manifest
is not a finalized scored result. Do not treat the manifest flag as completion.

The named failure is a `__pycache__` directory beside the frozen scoring sources.
The guard correctly refused before the official evaluation function could execute.
Six cache files have timestamps at19:56:29Z, after the seed scoring entry gate had
passed. The producing process is not established. The registered score worker already
uses both `-B` and `PYTHONDONTWRITEBYTECODE=1`; do not blame that worker or weaken
the freeze without evidence. There is no successful A/A score result to inspect.

Preparation completed, without any model or scorer invocation:

- Created an isolated clean checkout of the exact generation commit
  `953f9b598adba1df7c424c755993713087428823` at
  `/home/chao/saea-worktrees/codex-system-text-score-entry-recovery1`.
- Its original E0/D3 gate passes and its frozen scoring package has zero caches.
- The original worker, cache files and failed batch are untouched. No source,
  output, roster, policy, scorer or scoring parameter is changed.

Proposed owner decision216: allow exactly one separately receipted scoring-entry
recovery for the existing complete A/A generation from that clean checkout. Retain
both existing400-row generations and the seed's successful score. Keep the failed
job and all original bytes as evidence. A Windows-owned WSL scoring job would use
the unchanged whole-manifest finalization path, with one complete official evaluation
and an exclusive successor output directory. No new generation, new roster, relabeling,
row selection or policy update is authorized. A further failure stops the family.

Admission must explicitly acknowledge the failed pre-evaluation worker, preserve its
receipt and distinguish it from a successful official evaluation. Revalidate the full
generation seal before any scoring contact. Only after both members are independently
finalized with verified seals and one successful official score each may root
countersign the existing family READ and export feedback. The owner can instead close
this initial family without a quality read.

This is a narrow exception to the registered initial-family stop-on-failure policy,
so the general request to start GPU work promptly does not supply this approval.
No other held experiment gains authority from either disposition.
