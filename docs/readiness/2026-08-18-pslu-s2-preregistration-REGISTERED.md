# P-SLU Stage-2 follow-up — format-matched control + self-scoping re-fly — REGISTERED

Date: 2026-08-18. Status: **REGISTERED — flyable once the two-arm machinery lands** (flight
queued behind the P-PROMPT GPU slot). Profile: `bounded-discovery-probe`. Owner GO:
2026-08-18 ("2) Go" on the coordinator's S3 recommendation). Parent: the consumed P-SLU read
(`d8b71a5`, verdict UNRESOLVED), whose own §8.6 and §9 prescribe exactly these two arms.
Samples: the SAME 60 seeded SLURP devel samples (seed 20260807, frozen stratified sample);
decode config identical to the consumed flight.

## 1. The two questions (independent verdicts, no exclusive lattice — the P-SLU rule-gap
lesson; thresholds calibrated against the measured ±0.013 noise floor / 0.03 separability
bar, per the verdict's §9 calibration mandate)

**Q-A — is the control gain format, and does knowledge survive a schema-primed floor?**
Arm **F1 (format-matched filler control)**: a 100-entry roster rendered byte-compatibly with
A3's `"{type}={value}"` item shape and prompt framing, but carrying SYNTHETIC NON-ONTOLOGY
filler — type names and values drawn from a seeded generator over a non-SLURP wordlist,
machine-checked at binding for ZERO overlap with (a) the 55 ontology type names, (b) every
ontology value, (c) the 89 gold slot values of the 60 samples. ×60, phase-2 form identical
to A3. Verdicts (independent, may co-fire):
- **FORMAT-FLOOR-CONFIRMED**: F1 gain vs A0 ≥ +0.1046 (= A4's +0.1346 − 0.03) — filler
  with the right SHAPE reproduces the deranged arm's gain; the control-arm anomaly that
  sank the original branch lattice is format, and F1 becomes the schema-primed floor.
- **KNOWLEDGE-BEYOND-FORMAT**: A3(consumed 0.5961) − F1 SLU-F1 ≥ 0.10 — value knowledge
  survives against the schema-primed floor at ≥3× the separability bar. (A3 is cited from
  the consumed read, not re-flown: identical samples, identical decode config, and the §4
  duplicate-condition floor bounds re-fly drift at ~±0.013.)
- **FORMAT-IS-EVERYTHING**: A3 − F1 ≤ 0.03 — the L3 anchor's knowledge component does not
  survive; the supply-benefit curve's middle anchor is restated as format-only.
- Otherwise **INCONCLUSIVE-QA** (report the F1 number and both gaps).

**Q-B — does legal self-scoping work once the label-space defect is fixed?**
Arm **A1'r (self-scoping re-fly)**: phase 1 forces a CLOSED-SET scenario choice — the 18
canonical SLURP scenario labels (task-native schema, train-split-derived, legal) are
supplied and the core must pick one; phase 2 supplies the scenario-scoped value roster via
the SAME frozen `pslu_supply_packet` keyed on the chosen canonical label. ×60 (120 calls,
two-phase). The A2-fallback path stays in place but every call records fallback vs
non-fallback (primary integrity metric — the original A1' fell back 60/60). Verdicts:
- **SELF-SCOPING-WORKS**: non-fallback ≥ 50/60 AND A1'r gain ≥ A2's consumed +0.2946 − 0.03
  — scoped self-supply is at least vocabulary-parity and the scoping machinery actually ran.
- **SELF-SCOPING-FAILS**: non-fallback < 30/60 (the closed set did not fix the label-space
  boundary), OR A1'r gain < A2 − 0.10 (scoping actively hurts).
- Otherwise **INCONCLUSIVE-QB** (report non-fallback rate, phase-1 accuracy vs gold
  scenario — scoring-side only — and the gain).

## 2. Metrics

The consumed read's instrument set unchanged: official SLU-F1 (distance-weighted) with Δ vs
the consumed A0 (0.1741), slot_f1_exact, entity TP/FP/FN, induced-substitution count (the
metric §9 endorses), intent accuracy (reported; known degenerate), per-arm supplied-item
count audit. Copy-rate is REPORTED but carries no clause (§8.3: shape-variant definition,
uninformative on value-bearing arms). Silence-swap: 3 seeded A1'r samples re-fly with
silenced audio (same unanimity VOID bar as the parent, note 7).

## 3. Cost (registered ceilings)

180 audio requests + 3 silence-swap = 183 (F1 60; A1'r 120 two-phase; swaps 3); ≤220 core
calls; ≤2,000 metered audio-seconds; ≤0.5 GPU-h (parent flew 363 requests in 0.12 GPU-h).

## 4. Discipline

One-shot read; pinned read suite (extending `analysis/pslu_read.py` with the four-verdict
evaluator and the filler-overlap integrity check) built and coordinator-reviewed BEFORE the
read; exposure row `SAEA-PROBE-pslu-s2-183` appended at registration (consumed=no); filler
content synthetic-only (no gold-derived field anywhere; binding-time zero-overlap check is
fail-closed); scenario label set is task-native train-split schema (legal tier); SLURP audio
CC BY-NC 4.0 carried on all audio-derived numbers.
