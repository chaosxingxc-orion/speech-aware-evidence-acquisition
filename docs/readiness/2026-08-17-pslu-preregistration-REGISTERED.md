# P-SLU preregistration — REGISTERED (supersedes the same-day draft)

Date: 2026-08-17 (night). Status: **REGISTERED — flyable once the rails CoreClient bridge lands
and the ExecutionPlan binds this document.** Profile: `bounded-discovery-probe`. Binding source:
`docs/readiness/2026-08-17-g0-binding-tables.md` + `configs/probes/g0-binding/` (commit
`928a048`); 24-assertion sanity gate PASS.

## 1. Question

At L3 (SLU), does legal-tier compact knowledge supply — entity-type vocabularies and slot-value
rosters mined from the train split only — convert slot-extraction errors on the frozen core?
First quantified prompt-only roster-supply point at L3 on this model family.

## 2. Bound design

`devel` split = discovery surface (loader refuses `test` without an explicit flag). Sample:
**n = 60**, seed **20260807**, scenario-stratified across all 18 devel scenarios,
entity-bearing, REAL audio only, 60/60 flac resolved, 182.26 s total audio (mean 3.04 s),
**89 gold slots**, split identity hash `fc9de436…` (full hash in the binding JSON).

Rosters: **train.jsonl ONLY** (55 entity types, 4,157 distinct values; legal-tier value
coverage of the sample's gold slots = 76.4%). The shipped `load_slurp_ontology` is
**prohibited for this flight**: it mines `train_synthetic.jsonl`, which overlaps devel 64.8%
verbatim (1,317/2,033 slurp_ids with identical sentence and entity set) — ceiling-tier by the
either-field doctrine. Engineering fix queued; the flight consumes
`configs/probes/g0-binding/pslu-rosters-train-only.json` (0 overlap) directly.

Arms (same audio per sample; six arms):

| Arm | Supply | Tier |
|---|---|---|
| A0 | none | — |
| A1 | scenario-scoped roster, scenario = GOLD label (mean 35.6 entries, ~188 tokens) | **ceiling companion** (gold-scoped selection) |
| A1' | scenario-scoped roster, scenario = the core's own first-pass prediction | self-supplied (deployment-legal) |
| A2 | global type vocabulary, 55 types (~184 tokens) | legal |
| A3 | full-ontology roster, **dose cap 100 entries** (uncapped 4,157 ≈ 25k tokens) | legal; dose-law point |
| A4 | deranged roster: fixed-point-free scenario permutation, mean length delta 1.67 | control |

Controls: copy-rate on every arm (supplied roster tokens appearing as slot fillers where the
aligned reference is a non-roster word counts as induced substitution); silence-swap on 3
seeded A1' samples.

## 3. Metrics

Primary: official SLU-F1 delta on entity slots vs A0 (per-sample TP/FP/FN, summed,
micro-averaged — the adapter's `slu_f1` family). Alongside: `slot_f1_exact`, intent accuracy
(guardrail: any-arm drift beyond −5 pp flags attention tax), copy-rate, induced-substitution
count. Descriptive at n=60; no p-values.

## 4. Branch rules (mechanical)

- **SUPPLY-CONVERTS**: A1' SLU-F1 gain ≥ **+0.05** absolute over A0 AND A4 gain ≤ +0.01 AND
  A1' copy-rate < 50%.
- **COPY-TRAP**: A4 gain ≥ half of A1' gain, OR any glossary-arm induced-substitution count ≥
  its entity true-positive gain, OR copy-rate ≥ 50%.
- **DOSE-CONFIRM** (secondary, descriptive): A3 underperforms A2.
- **INERT**: no arm gains ≥ +0.02 SLU-F1 over A0.
- **VOID**: silence-swap answers persist unchanged, harness defect, or per-sample TP/FP/FN
  fail to reproduce the adapter's committed scorer on recheck.

Branch evaluation is mechanical from the per-sample ingredients; one-shot read (all six arms
flown before any result is read; consumed flips after the single read session).

## 5. Legality and license

All rosters train-split-mined (disjoint from devel; zero gold-derived fields — E1' checked).
A1 is explicitly registered ceiling-tier at the scoping step; A1' is the deployment-legal
companion. SLURP audio is CC BY-NC 4.0 (non-commercial constraint carried on audio-derived
results).

## 6. Cost

Registered: ≤450 core calls (6 arms × 60 + headroom), ≤1,500 audio-seconds metered, ≤0.5
GPU-h (binding estimate 0.15–0.40 GPU-h incl. both A1 and A1').

## 7. Preconditions

Rails CoreClient → FrozenCoreAdapter bridge (engineering ticket dispatched 2026-08-17 night);
E0' flight lock; exposure row `SAEA-PROBE-pslu-n60` appended at registration (consumed=no);
ExecutionPlan carries split role (devel=discovery), split identity hash `fc9de436…`, protocol
hash, and this document as the pre-registration binding.
