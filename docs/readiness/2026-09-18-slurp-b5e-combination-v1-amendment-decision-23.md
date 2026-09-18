# Cell B5e: amendment of the bar clause under owner decision 23 (recorded before any number was read)

Status: **AMENDMENT, PRE-READ.** Author: Fable 5.1, root coordinator, 2026-09-18. Authority: owner
decision 23 of 2026-09-18 (`docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`).
This note grants no model contact and edits no sealed byte: the preregistration
`docs/readiness/2026-09-18-slurp-b5e-combination-v1-preregistration.md` keeps the hash the readiness
package and the decision receipt pinned; this note supersedes ONE clause of it for the verdict.

## What changes

Clause 1 of section 7 (the bar clause) read the v3-projected numbers. Under owner decision 23 the
program bar and every final evaluation read the **official, unprojected SLURP `evaluate.py` number**
(`slurp-slu-official-train`), the community-standard protocol. The amended clause:

> **Clause 1 (amended) -- the bar clause (owner decisions 1 and 23).** Cell B5e MEETS THE BAR on
> this pass if and only if the **official unprojected pooled SLU-F1 is >= 64.00 AND the official
> intent (scenario+action) is >= 78.00**, read once from the single official score of the complete
> manifest. The v3-projected and the TRAIN symmetric numbers are reported beside them as
> diagnostics, and the verdict states whether the v3 number would have cleared 64.00. Meeting the bar
> registers B5er immediately; missing it does not lower the bar (owner decision 20).

Clauses 2 and 3 (the combination clause and the HARMFUL trigger against the sealed B1 arm), the
metrics, the resampling, the cost and prompt-fit sections, the failure rule and the analysis recipe
are unchanged. Additivity stays a reported diagnostic and never a gate (owner decision 23: gains are
never assumed additive).

## Why now

The amendment is recorded at 2026-09-18T14:5xZ, before any B5e number exists: the first arm attempt
aborted at 25 contacts on an infrastructure failure (see the exposure ledger) and its recovery
re-registration has not flown. Nothing about the amended clause was chosen after seeing data.

## Arithmetic stated to the owner

If the two single-module official deltas were additive, B5e would read about 61.14 + 2.55 = 63.69
official pooled SLU-F1, below 64.00; the v3 arithmetic (64.73) is not the bar. A miss routes the
program through owner decision 20 (keep admitting B2 v3, B7a, B4a; read B5b against the unchanged
bar) rather than through any lowering of the bar.
