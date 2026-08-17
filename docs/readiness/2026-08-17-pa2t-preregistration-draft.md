# P-A2T preregistration DRAFT — roster-precision supply probe on Audio2Tool (L5 anchor)

Date: 2026-08-17. Status: **DRAFT — not registered, not flyable.** Every `[TBD]` must be bound
from the 2026-08-17 carrier inventory and the B0 rails state before registration; flight requires
the registered successor of this document plus an exposure row. Profile:
`bounded-discovery-probe`.

## 1. Question

At the agentic end of the capability ladder (L5), does legal-tier compact knowledge supply
convert tool-selection competence into exact-match execution? Measured headroom from the consumed
T2 discovery read: tool-acc 84.6% vs EM 15.6%. The probe measures the frozen core's
USE / COPY / IGNORE response to argument-relevant evidence as a function of roster precision —
the L5 sampling point of the supply-benefit-versus-task-level curve (standard scheme v1, umbrella
spec 2026-08-17).

## 2. Design

Single flight, discovery split only, n = [TBD, target 25–40 samples, prioritizing samples where
tool selection was correct but EM failed]. This is a mechanism/shape probe: n is below any MDE by
construction; no macro or superiority claims can issue from it.

Arms (same audio per sample):

| Arm | Supply | Purpose |
|---|---|---|
| A0 | none | zero anchor. May reuse consumed T2 results ONLY if protocol hash + split identity match exactly [verify at binding]; otherwise re-fly in-block |
| A1 | exact roster: argument-relevant entities for this sample, task-native legal provenance | precision ladder top |
| A2 | diluted roster: exact + K = [TBD] distractors from the task-global entity pool | ladder midpoint |
| A3 | global roster: full task entity pool, no per-sample targeting | does L5 need routing at all (kb34 mirror) |
| A4 | deranged roster: length-matched rosters from other samples | copy-trap control; gains here void supply attribution |

Inherited controls: copy-rate (byte-identical parroting of supplied tokens) computed on every
arm; silence-swap spot control on ≥[TBD ≥3] A1 samples (audio replaced by silence — if EM
persists, the core answered from the roster, not the speech).

## 3. Metrics

Primary: EM conversion on initially-wrong samples (wrong→right flips), per arm. Guardrails:
right→wrong flips, copy-rate per arm, tool-acc drift vs A0. All descriptive at this n.

## 4. Branch rules (pre-registered; mechanical evaluation)

- **SUPPLY-CONVERTS**: A1 flips ≥ [TBD]% of headroom samples AND A4 flips ≈ 0 AND A1 copy-rate
  < [TBD]% → L5 anchor = measured conversion; proceed to precision-ladder analysis (A1 vs A2 vs
  A3 gradient).
- **COPY-TRAP**: A4 flips comparable to A1 OR copy-rate ≥ [TBD]% → the copy law extends to L5;
  record as the agentic extension of the P2 finding.
- **INERT**: no arm flips materially → compact-roster supply has no L5 leverage; anchor = 0
  pending form variations.
- **VOID**: silence-control EM persistence, harness defect, or identity mismatch at A0 reuse.

Threshold values are bound at registration, before any flight, and evaluated mechanically.

## 5. Legality

A1/A2/A3 rosters carry legal tier only (task-shipped context; E1' fields stamped at build). Any
gold-derived roster is ceiling-tier and is NOT flown in this probe (a ceiling companion may be
registered separately). The rails runner's legality gate is the enforcement point.

## 6. Exposure discipline

One-shot read: register the probe exposure row before flight; fly all arms before reading any
result; single read session; consumed flips immediately after. ExecutionPlan carries split role,
split identity hash, protocol hash, and this document's registered successor as the
pre-registration binding.

## 7. Engineering preconditions

B0 rails + Audio2Tool adapter green (in flight today); E0' flight lock active; Audio2Tool
featcache warm (campaign running); stale lock-blocked docstrings fixed. GPU estimate
0.1–0.25 GPU-h.

## 8. 2026-08-17 night RESTRUCTURE (binding-prep findings `928a048` — supersedes §2)

1. **The 84.6%/15.6% headroom premise is RETIRED**: unsourced (prose-only in five files) and
   contradicted by both recoverable archival reads (dev 67.5%/65.0%, test 86.7%/85.0% —
   tool-acc ≈ EM). The L5 headroom is unknown until measured. Corrected in the standard-scheme
   spec the same night.
2. **A0 reuse is impossible**: the consumed T2 read left zero artifacts anywhere on this
   machine; the frozen 400-item split was never bound to an execution here. The headroom sample
   list is unbindable pre-flight.
3. **Two design defects**: the per-item `functions` field IS the gold tool (so A3 ≡ A0
   byte-identically), and A1/A2 have no legal-tier per-sample source.
4. **New shape**: Stage 1 = **A0 zero-supply baseline re-fly** on the frozen 400-item split
   (`baseline-reproduction` profile; ~0.5–1.3 GPU-h — every request carries a ~12.7k-token
   registry prefill; warms the featcache; measures the REAL tool-acc/EM gap and yields the
   headroom list {tool_acc==1 ∧ EM==0}). Stage 2 (registered separately, only if Stage 1 shows
   measurable headroom): compacted supply probe — A0/A3 collapsed; A1' self-supplied single-row
   roster keyed on the core's own first-pass tool selection; A2 diluted K=9; deranged arm. The
   2026-08-15 amendment's 2×2 {roster, not} × {clean, noisy} factorization mismatch is noted
   for the owner if Stage 2 diverges from it.
