# P-SLU preregistration DRAFT — slot-roster supply probe on SLURP (L3 anchor)

Date: 2026-08-17 (late night). Status: **DRAFT — not registered, not flyable.** Numeric bindings
marked `[TBD]` are pinned at registration; flight requires the registered successor plus an
exposure row. Profile: `bounded-discovery-probe`. Sibling design: the P-A2T draft (L5).

## 1. Question

At L3 (SLU), does legal-tier compact knowledge supply — entity-type vocabularies and slot-value
rosters — convert slot-extraction errors on a frozen omni core? This is the L3 sampling point of
the supply-benefit-versus-task-level curve. SLURP is legality-clean by construction: rosters are
mined from the TRAIN split ontology, fully disjoint from the devel evaluation surface — no
gold-derived field ever enters supply (machine-checked by E1').

## 2. Design

Single flight, `devel` split only (`test` held out; loader refuses it without an explicit flag).
n = [TBD, target 50–100 utterances], stratified across scenarios, seeded; REAL audio only.
Mechanism/shape probe: no macro claims.

Arms (same audio per sample):

| Arm | Supply | Purpose |
|---|---|---|
| A0 | none | zero anchor |
| A1 | scenario-scoped roster: entity types + top-[TBD] slot values for the sample's scenario, mined from train | precision ladder top (legal) |
| A2 | global type vocabulary: all entity types, no values | compact/dose midpoint |
| A3 | full-ontology roster (types + values, dose-capped at [TBD] entries) | dose-law point — expected degradation per the 50–100-entry law |
| A4 | deranged roster: another scenario's A1 roster, length-matched | copy-trap control |

Controls: copy-rate per arm (supplied roster tokens parroted into slot fillers); silence-swap on
≥[TBD ≥3] A1 samples. Scenario labels used for A1 scoping come from the sample's gold scenario —
that makes A1 **ceiling-tier at the scoping step**; register A1' (scenario predicted by the core
in a first pass, self-supplied tier) as the deployment-legal companion. [Binding decision: fly
A1 + A1' both, or A1' only — pick at registration.]

## 3. Metrics

Primary: official SLU-F1 delta on entity slots (per-sample TP/FP/FN summed then micro-averaged,
matching the adapter's `slu_f1` family). Guardrails: intent accuracy drift vs A0; `slot_f1_exact`
reported alongside; copy-rate per arm. Descriptive at this n.

## 4. Branch rules (pre-registered, mechanical)

- **SUPPLY-CONVERTS**: A1' slot-F1 gain ≥ [TBD] with A4 ≈ 0 gain and copy-rate < [TBD]%.
- **COPY-TRAP**: A4 gain comparable to A1' OR copy-rate ≥ [TBD]%.
- **DOSE-CONFIRM** (secondary): A3 underperforms A2 — the dose law reproduces at L3.
- **INERT**: no arm moves slot-F1 materially.
- **VOID**: silence-control persistence, harness defect, or scoring mismatch vs the official
  ingredients.

## 5. Legality and license

Rosters: train-split ontology only (legal); scenario scoping per §2. SLURP license is split —
text CC BY 4.0, **audio CC BY-NC 4.0**: audio-derived results carry the non-commercial
constraint (recorded in the adapter docstring and the lock entry).

## 6. Exposure discipline

One-shot read; register the exposure row before flight; all arms flown before any result read;
consumed flips after the single read session. ExecutionPlan carries split role (devel =
discovery), split identity hash, protocol hash, and this document's registered successor.

## 7. Engineering preconditions

SlurpAdapter green (landed 2026-08-17 night, suite 2058/9); E0' flight lock; featcache warms on
flight (no prebuild needed — per-utterance audio is seconds-scale); exposure row. GPU estimate:
[TBD after a 3-sample timing smoke; expected well under 1 GPU-h].
