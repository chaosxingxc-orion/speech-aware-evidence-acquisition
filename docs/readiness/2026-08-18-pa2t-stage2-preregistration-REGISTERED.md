# P-A2T Stage-2 supply probe — REGISTERED

Date: 2026-08-18. Status: **REGISTERED — flyable once the supply-arm flight machinery lands**
(engineering ticket dispatched the same day). Profile: `bounded-discovery-probe`. Owner ruling
2026-08-18: fly **ALL 120** headroom samples, no subsampling. Binding sources: the consumed A0
read (`ec25706`; headroom list `docs/checks/speech-aware-evidence-acquisition/2026-08-18-pa2t-a0-read/headroom.json`,
schema `saea-a2t-a0-headroom-v1`), the frozen split receipt (hash `e1d751e6…332c`), the
152-row tool registry.

## 1. Question

On the 120 samples where the frozen core already selects the correct tool but fails the full
call, does prompt-level supply of tool-schema knowledge convert failures into exact matches —
and is the effect knowledge or format? (The P-SLU verdict's schema-vs-knowledge confound is
promoted here to a first-class branch.)

## 2. Design

Samples: the 120 headroom ids exactly (tier distribution 23/17/29/3/12/12/8/16). Baseline
comparator: their A0 outcomes (EM=0 by construction; tool selection correct) from the consumed
read — no A0 re-fly on the 120.

| Arm | Supply (prompt-level, per sample) | n |
|---|---|---|
| S1' | **self-supplied single row**: the registry row (schema + argument constraints) of the tool the core ITSELF selected in A0 — deployment-legal, self-supplied tier | 120 |
| S2 | diluted: the correct row + 8 seeded distractor rows (K=9), seed 20260807 | 120 |
| S4 | deranged: ONE wrong tool's row (fixed-point-free seeded mapping among the 120), length-matched | 120 |
| N0r | **noise-floor arm**: zero-supply re-fly of 40 seeded samples of the 120 (institutionalizing the P-SLU accidental noise-floor lesson — no carrier noise floor exists yet) | 40 |

Total 400 requests. The full-registry arm is deliberately absent: A0's system prompt already
carries all 152 rows, so full-registry supply ≡ A0 (measured; the attempt-2 finding).

## 3. Metrics (per-tier reporting MANDATORY; pooled numbers are never the headline)

Primary: **EM conversion rate** per arm (EM 0→1 on the 120). Guardrails: tool-selection
retention (supply must not break the already-correct selection), slot precision/recall/F1,
empty-call rate, induced-substitution count (supplied argument VALUES appearing where the
aligned gold argument differs), parse-failure rate. Noise floor := max(EM-flip rate on N0r,
1/40).

## 4. Branch rules (mechanical, in order)

1. **VOID**: harness defect (completeness/duplicate/arm checks fail-closed), receipt mismatch,
   or N0r shows the A0 comparator is unstable (N0r EM-flip rate > 25%).
2. **COPY-TRAP**: any arm's induced-substitutions ≥ its EM-flip count, OR S4 tool-selection
   retention < 90% (a wrong row DRAGS selection away).
3. **SCHEMA-ONLY**: S1' and S4 conversion rates within 2× noise of each other while both ≥
   max(2× noise, 5%) — the wrong row converts as well as the right one ⇒ the effect is
   format/schema, not knowledge (the P-SLU gap, now a named outcome).
4. **SUPPLY-CONVERTS**: S1' conversion ≥ 15% of 120 AND S4 conversion ≤ max(2× noise, 5%) AND
   S1' tool-selection retention ≥ 95%.
5. **INERT**: every supply arm < max(2× noise, 5%).
6. **DOSE point** (secondary, descriptive): S2 vs S1' — does dilution to K=9 cost conversion?

## 5. Legality

All supply content is drawn from the task's own shipped tool registry (task-native, legal
tier); S1''s row selection is keyed on the core's OWN A0 choice (self-supplied tier — the
deployment-realistic reading). No gold-derived field enters any prompt (E1' checked). NC
license constraint carried on audio-derived results.

## 6. Cost (registered ceilings)

≤450 core calls; ≤3,500 audio-seconds; ≤1.0 GPU-h (basis: A0 measured ~10.5 req/min with
registry prefix-cache reuse; 400 requests ≈ 40 min + margin).

## 7. Discipline

One-shot read: all arms flown before any result is read; pinned read suite (extending
`analysis/a2t_read.py` with the arm comparisons and branch evaluator) built and reviewed BEFORE
the read; consumed flips at the read. Exposure row `SAEA-PROBE-a2t-s2-120` appended at
registration (consumed=no). Per-tier tables in the verdict; the four tiers with ≥16 headroom
samples (tier1/2/3/8) carry the interpretive weight, the four thin tiers (tier4/5/6/7) are
reported with explicit small-n caveats.
