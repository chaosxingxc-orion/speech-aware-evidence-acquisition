# V4 — whole-population regression arm — REGISTERED

Date: 2026-08-19. Status: **REGISTERED — flyable once the machinery lands**. Profile:
`bounded-discovery-probe`. Owner GO: 2026-08-19 blanket exploration release ("该跑的探索都
可以跑"); design per the adversarial panel's Finding 3 (refuter-corrected scoping).

## 1. Question

C1's conversion evidence lives on the gold-identified 120-sample headroom set, where EM
cannot regress. Does the clean supply form COST anything on the samples the core already
gets fully right — the missing regression term of the signed law?

## 2. Design (one session)

Population: the **97 EM-correct ids** of the frozen A2T 400 (tool_accuracy=1 ∧ EM=1 — the
only EM-regression-eligible ids; the 183 tool-selection-failure ids are excluded because EM
cannot regress there either AND no gold-free supply-row rule exists for them — recorded
limitation, carried on every citation).

| Arm | Supply | n |
|---|---|---|
| R0 | zero-supply re-fly (in-session comparator; doubles as this population's first EM-stability measurement) | 97 |
| R1 | B1-form values-stripped row of the core's own A0-selected tool (self-supplied, deployment-legal — on these ids the A0 selection is the correct tool) | 97 |

194 requests. Seed 20260807; decode config identical to the consumed A2T flights.

## 3. Metrics and verdicts (panel CI discipline applies)

Primary: EM regressions (EM 1→0) per arm; Δreg = reg(R1) − reg(R0); paired per-sample
bootstrap (shared `analysis/bootstrap.py`, N=10,000, seed 20260807) publishes σ̂(Δreg) and
a 90% CI. Guardrails: induced substitutions (full-registry default-value yardstick),
tool-selection retention, empty/parse rates, per-tier tables.
- **REGRESSION-SAFE**: Δreg ≤ 2 AND CI upper bound ≤ 5 — the clean form does not
  meaningfully damage already-correct behavior; the whole-population account becomes
  citable: net = conversions [8,10]/120 (cited) − Δreg, over 400, with the 183-exclusion
  disclosure.
- **REGRESSION-COSTLY**: Δreg ≥ 6 (≥5% of 97 with margin) — the signed law's negative term
  is real at whole-population scale; C1/C5 must carry it.
- Otherwise **INCONCLUSIVE-POP** (report Δreg, CI, ingredients).
Pre-read reachability statement mandatory (trivially reachable here — EM can fall on all 97
— but the statement documents R0's own re-fly stability, this population's first).

## 4. Cost (registered ceilings)

194 requests; ≤220 core calls; ≤2,000 metered audio-seconds; ≤0.5 GPU-h.

## 5. Discipline

One-shot read; pinned suite (`analysis/a2t_pop_read.py`, reusing the consumed A2T scoring
primitives verbatim + the shared bootstrap) built and coordinator-reviewed BEFORE the read;
exposure row `SAEA-PROBE-a2t-pop-194` at registration (consumed=no); supply content from
the shipped registry only (legal tier); NC carried.
