# P-TRAP — self-percept trap probe — REGISTERED

Date: 2026-08-19. Status: **REGISTERED — flyable once the machinery lands** (GPU slot after
P-KEY). Profile: `bounded-discovery-probe`. Owner GO: 2026-08-18 approval of the speech-term
program (probe ③). Samples: the SAME frozen 60 SLURP devel samples (seed 20260807); decode
config identical to the consumed P-SLU flights.

## 1. Question

Is supply-use matching **acoustically mediated**? If the core matches roster entries against
its acoustic percept, then an entry equal to its OWN earlier mishearing of THIS audio should
capture its output at a higher rate than an equally wrong entry with no acoustic relation to
this audio.

## 2. Legality-critical design (registered)

Trap content is NEVER gold-derived (hard rule preserved). Traps are the core's OWN
model-generated values from the consumed A0 zero-supply attempt:
- **V1 (self-percept traps)** ×60: the A3-form 100-entry legal roster + K≤5 appended entries
  per sample, each being one of THIS sample's own A0 wrong emitted values (model text,
  consumed attempt, deployment-legal), rendered in the roster's own item shape. Samples with
  zero usable A0 wrong values fly with K=0 and are excluded from the capture denominator
  (count disclosed).
- **V2 (cross-percept control)** ×60: identical construction, but the K appended entries are
  seeded-drawn from OTHER samples' A0 wrong values (fixed-point-free at sample level,
  length-matched) — same source distribution, no acoustic relation to this audio.
Binding-time fail-closed check: no appended entry equals (post-normalization) any gold slot
value of its target sample — a trap that IS the gold value tests nothing and would breach
the gold-free rule in effect.

## 3. Metrics and verdicts

Per sample: CAPTURE := the response emits an appended trap entry (post-normalization exact
match) in any slot. Primary contrast: capture rate V1 vs V2 on the common denominator.
- **ACOUSTIC-MEDIATED**: capture(V1) − capture(V2) ≥ +0.10 AND raw difference ≥ 6 — the
  core preferentially re-commits to its own percept when supplied ⇒ matching consults the
  audio; the speech channel participates in supply use (and self-percept contamination is a
  measured USE-side risk).
- **KEY-ONLY-MATCHING**: |capture(V1) − capture(V2)| ≤ 0.03 — traps capture (or not)
  independently of acoustic relation ⇒ matching is text-side.
- Otherwise **INCONCLUSIVE-TRAP** (report both rates and the per-sample table).
Guardrails reported: SLU-F1 per arm vs the consumed A3 (does trapping cost task quality),
induced substitutions, empty/parse rates, per-sample K distribution.

## 4. Cost (registered ceilings)

120 requests (2×60); ≤140 core calls; ≤1,000 metered audio-seconds; ≤0.3 GPU-h.

## 5. Discipline

One-shot read; pinned read suite (`analysis/ptrap_read.py`, capture detector + verdict
evaluator + binding checks) built and coordinator-reviewed BEFORE the read; exposure row
`SAEA-PROBE-ptrap-120` appended at registration (consumed=no); all appended content is
model-generated text from a consumed attempt or the train-mined legal roster (no gold-derived
field anywhere; fail-closed binding check above); SLURP audio CC BY-NC 4.0 carried.

## 6. Amendment 2026-08-19 (registration-time calibration discipline; panel Finding-2 class)

The capture-rate axis has no measured reproducibility. Before any verdict fires: the read
suite computes a per-sample paired bootstrap over the common-denominator samples and
publishes σ̂ of the V1−V2 capture difference with a 90% CI. KEY-ONLY-MATCHING (an
equivalence verdict) fires only if the ENTIRE CI lies inside [−0.03, +0.03];
ACOUSTIC-MEDIATED requires the CI lower bound > 0 in addition to the registered point
thresholds; anything else is INCONCLUSIVE-TRAP. A pre-read reachability statement is
mandatory (given the per-sample K distribution and usable-trap counts, publish the maximum
attainable capture difference; unreachable branches may not be reported as affirmative
outcomes).
