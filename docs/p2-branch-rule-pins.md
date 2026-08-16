# P2 branch-rule operationalization pins (pre-comparator-read)

Dated 2026-08-16, authored by the research lead BEFORE any comparator arm of the P2 R-ladder
resume block (SAEA-P2-r1verify / r2draft / r0wrong / r1wrong) has been read. Exposure inherited
at pin time: the D4 shape screens (consumed 2026-08-15) and the SAEA-P2-r0bias one-shot salvage
read (spent 2026-08-16 06:48–07:18). Discipline and disclosure follow the HER/RIR definition
record mirrored at `docs/p2-metric-definitions-mirror.md`: raw values are always printed so any
reader can re-derive every clause under alternative pins.

The registered branch rules (`docs/arms/p2-rladder-resume.arms`, quoted verbatim there) name
three AFFIRM limbs, a COLLAPSE test, and a voiding condition, using words this note pins.

## Pin 1 — data sources per arm

R0-bias numbers come EXCLUSIVELY from the preserved salvage outputs
(`docs/checks/speech-aware-evidence-acquisition/2026-08-16-p2-r0bias-salvage/r0bias.asr-wer.json`,
`r0bias.entity-wer.json`, `r0bias.copycount.json`); the sealed trace is never re-read (one-shot
semantics). Comparator arms are read from their COMPLETED attempts via the pinned suite
(`scripts/p2_reads.py`, commit `3b3e34c`). Any cross-arm contrast must state both sources; if a
metric's extraction method differs between the salvage scripts and the suite in a way that could
change a verdict, that contrast is reported method-flagged and the affected clause is UNRESOLVED
rather than silently compared.

## Pin 2 — "(R2-R1>0)" (AFFIRM limb 1)

Fires iff BOTH co-primary ledgers agree: paired entity-correct total (entity-wer-v1 8284-token
ledger) strictly higher under R2-draft than R1-verify, AND paired macro WER strictly lower under
R2-draft than R1-verify, over the six effective calls. A mixed result does not fire the limb and
is reported as mixed.

## Pin 3 — "R1 beats R0-bias at matched entity gain with lower HER" (AFFIRM limb 2)

"Matched entity gain": R1-verify's entity-correct total is not lower than R0-bias's by more than
25 tokens (the tie margin of Pin 5). "Lower HER": strictly fewer harmful accepted splices by raw
counts, with both arms' denominators subject to the mirrored <10 guard — if either denominator is
below 10, the comparison falls to raw harmful counts (descriptive); if raw counts are degenerate
(0 vs 0, or denominators too small to distinguish), the limb is UNRESOLVED. Note: the salvage read
already fixed R0-bias's denominator at 3 accepted splices, so this limb is expected to resolve at
raw-count level or UNRESOLVED; it cannot silently pass.

## Pin 4 — "wrongref copy rate materially lower under verify than bias framing" (AFFIRM limb 3)

Measured on PRE-LOCALIZE replay text (the D7E guard-2 aperture), raw verbatim copy counts:
C_bias from SAEA-P2-r0wrong, C_verify from SAEA-P2-r1wrong. The limb fires iff C_verify <=
0.5 * C_bias AND C_bias >= 4. If C_bias < 4 the copy-opportunity base is too thin and the limb
is UNRESOLVED (insufficient opportunities), never passed or failed.

## Pin 5 — "~" (the COLLAPSE test's equivalence)

Two arms are "~" (equivalent) iff |paired macro WER difference| <= 0.10 percentage points AND
|paired entity-correct difference| <= 25 tokens. Scale rationale from the N10 block: 0.01 pp was
treated as a tie and 0.29 pp as directional; 117 entity tokens was directional. The registered
COLLAPSE requires R1~R0-bias on both ledgers AND on HER (HER equivalence is raw-count-based and
guard-aware per Pin 3) AND R2~R1; all conjuncts must hold.

## Pin 6 — the voiding condition and its precedence

Evaluated FIRST, before any AFFIRM/COLLAPSE clause: "wrong-reference copying in R1/R2" means
pre-localize verbatim copies of a supplied wrong reference in the verify-framing wrongref control
(SAEA-P2-r1wrong) or own-draft arm. The audio-verification claim is VOID iff that copy count >= 2.
A count of exactly 1 does not void but is reported as a material weakening in the verdict. The
registered rule's "regardless of WER deltas" is honored: voiding is checked and reported before
and independent of every other read.

## Pin 7 — statistical reads

Paired Wilcoxon (exact, as implemented in the reused `analysis.context_dose` machinery) at
effective n=6 is reported with exact p-values as DESCRIPTIVE evidence; no clause of the branch
rule turns on a significance threshold, because n=6 cannot support one. Clause decisions use the
pinned point-value margins above; the Wilcoxon values are printed alongside for the record.

## Disclosure

These pins were chosen without sight of any comparator-arm result. The "materially lower" 50%
factor, the >=4 / >=2 count floors, and the 0.10 pp / 25-token margins are implementer-level
choices made pre-read; a clean confirmation under independently pre-registered thresholds remains
required before any paper-level operator claim, exactly as the HER/RIR record already states.
