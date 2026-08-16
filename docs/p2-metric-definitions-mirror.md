<!--
ADDED AT MIRROR TIME (this header block only; the document below the "---
end of mirror-time header ---" marker is a VERBATIM copy and must not be
edited in place).

- Source repo: umbrella `exploring-l4-intelligence` (the program umbrella,
  outside this study repo).
- Source commit: `34fb703`.
- Original path at that commit:
  `wiki/experiments/speech-aware-evidence-acquisition/2026-08-16-p2-metric-definition-amendment.md`.
- Rename note: the umbrella file was renamed 2026-08-16 to
  `2026-08-16-p2-metric-definitions.md`. This mirror is saved content-addressed
  against the pre-rename commit `34fb703` precisely so the rename cannot break
  this reference; the byte content mirrored below is unaffected by the rename.
- Retrieval command used:
  `git -C <umbrella repo root> show 34fb703:wiki/experiments/speech-aware-evidence-acquisition/2026-08-16-p2-metric-definition-amendment.md`.
- Obligation discharged: this mirror satisfies the source record's own
  section 6 ("Mirror obligation") — "mirror this record into the study repo's
  docs/ during the next GPU gap, alongside docs/arms/p2-rladder.arms, so the
  definitions travel with the pre-registration they qualify." That obligation
  is DISCHARGED by this file landing in `docs/`.
- Nothing below this comment has been altered from the source blob at
  `34fb703`, including its own YAML frontmatter.
-->
<!-- end of mirror-time header; verbatim content begins immediately below -->
---
record_id: "SAEA-P2-METRIC-DEFINITION-2026-08-16"
title: "P2 R-ladder metric definitions: HER and the recoverable-information ratio"
date: "2026-08-16"
issued_by: "implementer (Stage-2 study execution); NOT an owner record and NOT an audit-campaign record"
amends: "studies/speech-aware-evidence-acquisition/docs/arms/p2-rladder.arms - PRE-REGISTERED READS and BRANCH RULES, definitions only"
status: "IN_FORCE__DEFINITIONS_PINNED_BEFORE_COMPARATOR_ARMS_READ"
model_touch_performed: false
scope: "study speech-aware-evidence-acquisition, Stage-2A, Phase 2 R-ladder ceiling block (wf_c21a2756 Phase 2)"
mirror_pending: "studies/speech-aware-evidence-acquisition/docs/ - to be mirrored during the next GPU gap; the study tree is frozen while the block flies"
---

# P2 metric definitions - HER and the recoverable-information ratio (2026-08-16)

## 1. Why this amendment exists

The Phase 2 R-ladder ceiling block pre-registers its reads and its branch rules in the study repo
file `docs/arms/p2-rladder.arms` (committed at `a001a22`). Two of the registered reads - **HER**
and the **recoverable-information ratio** - were named there but never given a computable formula:
an offline salvage of the first arm established that neither metric has a pinned definition
anywhere in the repository, in code or in prose.

One of the registered branch rules turns on HER directly:

> BRANCH RULES (registered before launch): operator AFFIRMED iff at
> least one of (R2-R1>0) / (R1 beats R0-bias at matched entity gain
> with lower HER) / (wrongref copy rate materially lower under verify
> than bias framing).

A branch rule whose deciding quantity has no formula is not falsifiable: any post-hoc arithmetic
could be made to satisfy or violate it. This record fixes the two formulas in writing so that the
rule can be applied mechanically, and it does so **before** the comparator arms are read.

## 2. Disclosure - the definitions were pinned late, and this is stated rather than concealed

The first arm of the block, `SAEA-P2-r0bias` (attempt `attempt-20260816T002109Z-4e1f59`), **has
already been read** offline, before the formulas below were pinned. The sequence of events is:

1. `SAEA-P2-r0bias` ran its inference to completion, was sealed by an `ABORTED` manifest bind, and
   was then scored exactly once via offline salvage.
2. The definitions in section 3 and section 4 of this record were fixed **after** that scoring.
3. The four comparator arms - `SAEA-P2-r1verify`, `SAEA-P2-r2draft`, `SAEA-P2-r0wrong`,
   `SAEA-P2-r1wrong` - are in flight and **none of their results have been read** at the time this
   record is written.

`r0bias`'s own numbers were **not** used to choose between candidate definitions. The definitions
were selected on the source meaning of the terms and on what the existing scorer and ledger already
support, not on which variant produced a more favourable r0bias figure.

This is nonetheless a **weaker position than pinning the formulas at registration time**. A reader
who wants to discount the branch-rule conclusion on that ground has everything needed to do so: the
first arm's numbers existed before the metric that partly decides the rule was defined. The
disclosure is made here so the discount can be applied by the reader rather than assumed away by
the implementer.

## 3. HER - Harmful Edit Rate

The term is taken from the Voice Memory line of work and means **harmful** edit rate. It is **not**
hallucinated-entity rate; any reading of the P2 branch rule that substitutes a hallucination
measure is a misreading of the registration.

- **Unit of analysis**: an **accepted replay splice** - a replay window whose edit was admitted and
  spliced into the final hypothesis. Rejected edits and untouched windows are not units.
- **Scoring procedure**: for each accepted splice, take the affected span and score it against the
  aligned gold span twice - once with the **pass-1** text, once with the **post-splice** text.
  Score with the study's own scorer, on both ledgers separately: **macro word error** and **entity
  error**.
- **Harm criterion**: an accepted splice is **harmful on a ledger** iff its post-splice span error
  is **strictly greater** than its pass-1 span error **on that ledger**. Equality is not harm.
- **Rate**:

  **HER = (harmful accepted splices) / (accepted splices)**

  reported **per ledger**, with the raw numerator and denominator **always printed next to the
  rate**. A bare rate without its counts is not a reportable HER value.

### 3.1 Mandatory degenerate-denominator guard

When the denominator (accepted splices) is **below 10**, the rate is **descriptive only** and
**must not decide the branch rule**. In that case:

1. the branch rule falls back to the **raw harmful-splice counts**;
2. if those counts are also degenerate, the HER clause of the branch rule is recorded as
   **UNRESOLVED** - never silently passed, and never silently failed.

This guard is not hypothetical. `SAEA-P2-r0bias` accepted only **3 splices across 79,285 words**,
which is far below the threshold; on that arm the HER clause is guard-bound from the outset.

## 4. RIR - recoverable-information ratio

Plain statement of the question the metric answers: *of the evidence we supplied that could have
fixed something, how much actually got used.*

- **Denominator**: entity tokens **wrong in the pass-1 hypothesis** whose **correct form appears in
  the candidate set delivered to that call**.
- **Numerator**: that same set, **restricted to tokens that are correct in the final hypothesis**.
- **Ratio**:

  **RIR = numerator / denominator**

  reported with **both raw counts**, **per arm**.
- **Token matching**: uses the study's existing `core.retrieval.normalize_term` normalization.
  Entity tokens come from the same `entity-wer-v1` adapter and **8284-token ledger** that the
  pre-registration already names. **No new normalizer and no new ledger may be introduced** for
  this metric.

### 4.1 Degenerate-denominator guard

**Identical to HER's** (section 3.1): below a denominator of 10 the ratio is descriptive only, the
read falls back to raw counts, and a degenerate fallback is recorded as **UNRESOLVED** rather than
resolved in either direction.

## 5. Nothing else in the P2 pre-registration changes

This record adds **formulas for two already-registered reads and nothing more**. Explicitly, and
for the avoidance of any doubt:

- the **co-primary paired call-level Wilcoxon reads** on macro WER and entity-WER (8284-token
  ledger) stand exactly as registered;
- the **AFFIRM and COLLAPSE branch rules** stand exactly as registered, including the
  wrong-reference clauses and the voiding condition;
- the **arm set** stands exactly as registered - `SAEA-P2-r0bias`, `SAEA-P2-r1verify`,
  `SAEA-P2-r2draft`, `SAEA-P2-r0wrong`, `SAEA-P2-r1wrong`;
- the effective paired n, the tier fields, the split identity hash, the oracle lineage and the
  registered budget cells are untouched.

For self-containment, the governing registration text as committed in
`studies/speech-aware-evidence-acquisition/docs/arms/p2-rladder.arms`:

> PRE-REGISTERED READS: co-primary paired call-level Wilcoxon on macro
> WER and entity-WER (8284-token ledger); HER; recoverable-information
> ratio; wrong-reference COPY COUNT measured on PRE-LOCALIZE replay
> text (the D7E guard-2 aperture note); format-normalized secondary;
> per-term flip lists.
>
> BRANCH RULES (registered before launch): operator AFFIRMED iff at
> least one of (R2-R1>0) / (R1 beats R0-bias at matched entity gain
> with lower HER) / (wrongref copy rate materially lower under verify
> than bias framing). Taxonomy COLLAPSE iff R1~R0-bias on both ledgers
> and HER AND R2~R1 - then the 2026-08-14/15 scope amendments are
> re-amended, the candidate keeps targeting/small-N wording, no
> "different operator" language. Wrong-reference copying in R1/R2
> voids the audio-verification claim regardless of WER deltas.

and the registered arm set:

> ```
> # run_id:baseline_fragment
> SAEA-P2-r0bias:p2-r0bias8-buf90
> SAEA-P2-r1verify:p2-r1verify8-buf90
> SAEA-P2-r2draft:p2-r2draft8-buf90
> SAEA-P2-r0wrong:p2-r0wrong8-buf90
> SAEA-P2-r1wrong:p2-r1wrong8-buf90
> ```

The four-arm resume runs from `docs/arms/p2-rladder-resume.arms`, whose header is copied verbatim
from the file above; that resume created no new registration, and this record creates none either.

## 6. Mirror obligation

The study working tree is **frozen while the P2 block flies** - a single modified file under
`studies/speech-aware-evidence-acquisition/` breaks the run manifest's `study_commit` bind and
destroys the arm at finalize. This record was therefore written in the umbrella repository only.

**Action required**: mirror this record into the study repo's `docs/` during the **next GPU gap**,
alongside `docs/arms/p2-rladder.arms`, so the definitions travel with the pre-registration they
qualify. Until that mirror lands, this umbrella file is the authoritative text of the two
definitions, and the study repo carries no copy.
