# P-A2T Stage-2c form-robustness probe — REGISTERED

Date: 2026-08-18. Status: **REGISTERED — flyable once the render delta lands** (engineering
ticket dispatched same day). Profile: `bounded-discovery-probe`. Owner GO: 2026-08-18
approval of the coordinator's recommendation — robustness before Stage-2B qualification.
Parent: the consumed Stage-2b read (`c9ee811`, Q-A CONFIRMED-CUT) whose own caveat list
motivates this probe: **B1's conversion of 8/120 cleared its floor with zero margin**.
Samples: the SAME 120 headroom ids; seed 20260807 throughout; decode config identical to
Stage-2/2b (deterministic decode — a byte-identical re-fly reproduces, so robustness must be
probed on the *presentation axis*, not by re-flying B1).

## 1. Question

Is B1's CONFIRMED-CUT (values-stripped supply keeps ~half the conversion and cuts 94% of the
injection) robust to the surface form of the stripped row, or a knife-edge artifact of the
exact B1 rendering? Secondary (descriptive): does the clean form survive the
deployment-realistic *augmenting* position, where the full registry — including the correct
tool's default values — remains in context?

## 2. Design

| Arm | Supply (per sample, correct tool's row with `argument_defaults` STRIPPED) | Form | n |
|---|---|---|---|
| C1 | stripped row, seeded permutation of field order and constraint order | replacing (like B1) | 120 |
| C2 | stripped row, constraints verbalized as English prose sentences (same content) | replacing (like B1) | 120 |
| C3 | stripped row appended to the FULL 152-row registry under the same "particularly relevant" header as Stage-2b's B2 | augmenting | 120 |

360 requests total. C1/C2 perturb only presentation relative to B1 (content identical); C3
is the direct right-row contrast to B2's wrong-row augment (identical form, opposite
content) and the deployment reading — a retriever *adds* a row, it does not replace the
registry. Note C3's context still contains the correct tool's defaults inside the registry
block, so C3 also tests whether highlighting re-opens the value-copy channel.

## 3. Verdicts (mechanical; C1/C2 decide, C3 is an independent overlay)

- **ROBUST**: C1 AND C2 each have conversion ≥ 6/120 (= 2× the cited 0.0250 noise floor)
  AND induced-substitutions ≤ 5 — the clean-form result stands; Stage-2B qualification may
  cite the envelope [min, max] across B1/C1/C2.
- **FORM-FRAGILE**: C1 or C2 has conversion ≤ 3/120 (≤ noise) OR induced ≥ 20 — the 8/120
  was form-specific; any qualification must carry the fragility bound.
- Otherwise **INCONCLUSIVE-C** (report the envelope and ingredients).
- **DEPLOY-AUGMENT overlay** (independent, descriptive): C3 conversion ≥ 6/120 AND C3
  induced ≤ 5 ⇒ flag DEPLOYABLE (the clean form survives in-context registry defaults);
  C3 induced ≥ 20 ⇒ flag CHANNEL-REOPENED (highlighting re-activates the registry's own
  values as a copy source). C3 fires no primary branch.

## 4. Metrics

Same instrument set as Stage-2/2b: EM conversion on the 120 vs the consumed A0 comparator;
tool-selection retention; slot micro P/R/F1 (approved direct primitives); induced-substitution
with the approved bare-key alignment, counted against the FULL registry's default-value set
(the unchanged yardstick — apples-to-apples with 34/2); empty-call and parse-failure rates;
per-tier tables mandatory with small-n flags. Noise floors cited from Stage-2's N0r (EM 0/40;
12.5% selection band) — no new noise arm. Retention carries NO verdict clause in this probe
(the 12.5% selection-noise band cannot bear one at this n; lesson of Stage-2/2b).

## 5. Cost (registered ceilings)

360 requests (3×120); ≤400 core calls; ≤3,000 metered audio-seconds; ≤0.75 GPU-h (featcache
fully warm; C1/C2 prompts tiny, C3 registry-sized with prefix-cache reuse).

## 6. Discipline

One-shot read; pinned read suite (`analysis/a2t_s2c_read.py`, an extension of the Stage-2b
suite evaluating §3) built and coordinator-reviewed BEFORE the read; exposure row
`SAEA-PROBE-a2t-s2c-120` appended at registration (consumed=no); all supply content from the
shipped tool registry (legal tier; C3's header is instruction text, not evidence); NC
license carried on audio-derived results.
