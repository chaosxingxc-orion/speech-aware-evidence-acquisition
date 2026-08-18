# P-A2T Stage-2c form-robustness registered one-shot read — archive (2026-08-18)

The single sanctioned read of the flown P-A2T Stage-2c form-robustness probe. The pinned offline
read suite ran **exactly once**; the exposure row `SAEA-PROBE-a2t-s2c-120` flipped to consumed in
the same commit, and the suite is idempotence-guarded against a second run into this directory (a
pre-existing `verdict.json` refuses the read before any work happens).

## What was read

| | |
|---|---|
| Attempt | `$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-a2t-s2c-120/attempt-20260818T175018Z-0d3363` |
| Attempt status | `COMPLETED` (`error: null`, `request_failures: []`, `arms: ["C1","C2","C3"]`) |
| Rows scored | 360 = C1 120 + C2 120 + C3 120 |
| Sample set | the frozen 120-sample Stage-2 headroom list (`saea-a2t-a0-headroom-v1`) — the SAME ids Stage-2/2b flew |
| Split identity | `e1d751e6c76e49d087620842ba17c34e432a4602169dc2b93ee7e0a529ca332c` |
| Reused Stage-2 arm plan | `runs/SAEA-PROBE-a2t-s2-120/attempt-20260818T124955Z-84b944/SAEA-PROBE-a2t-s2-120.arm-plan.json` (verbatim; per-row `supplied_tool` cross-check proved it, identically for all three arms) |
| Suite | `scripts/a2t_s2c_read.py` -> `speech_aware_evidence_acquisition.analysis.a2t_s2c_read` (`59c6fa5`) |
| Pre-read gate | `pytest tests/unit/test_a2t_s2c_read.py` 20 passed, clean tree at `878e1ee`; flight-archive MANIFEST `sha256sum -c` all OK |
| Registration | `docs/readiness/2026-08-18-pa2t-stage2c-preregistration-REGISTERED.md` |
| Flight archive | `878e1ee` (flight machinery `cabe07c`, registration `a6652da`) |

Model-free and read-only: the suite never opens a model session and never mutates the attempt
directory. No GPU, no model contact, no installs.

## Contents

- `verdict.json` — machine-readable report (`saea-a2t-s2c-read-v1`): per-arm and per-tier
  EM-conversion / tool-selection-retention / slot P-R-F1 / empty-call / parse-failure /
  induced-substitution aggregates, plus every FORM-ROBUSTNESS clause with its own verdict and
  detail text, and the independently-evaluated DEPLOY-AUGMENT overlay.
- `report.txt` — the suite's rendered human-readable report, verbatim as printed.
- `MANIFEST.sha256` — SHA-256 over every other file in this directory.

## Outcome

The primary verdict is decided by C1+C2 jointly; the DEPLOY-AUGMENT overlay is evaluated
independently over C3 alone and fires no primary branch:

- **FORM-ROBUSTNESS: ROBUST.** C1 (permuted stripped row) converted **0.0833 (10/120)** with **4**
  induced substitutions; C2 (verbalized stripped row) converted **0.0750 (9/120)** with **3** — all
  four clauses met (conversion floor 6/120, induced ceiling 5), no FORM-FRAGILE clause close.
  Stage-2b B1's zero-margin 8/120 is the envelope **minimum** across B1/C1/C2: conversion
  [8/120, 10/120], induced [2, 4].
- **DEPLOY-AUGMENT: CHANNEL-REOPENED.** C3 (stripped row appended to the full 152-row registry)
  converted **0.0583 (7/120)** — above the DEPLOYABLE floor — but injected **22** default values
  (ceiling 5, reopen floor 20): with the registry's own defaults still in context, highlighting the
  right tool re-activates them as a copy source. Near-threshold fire (22 vs 20), flagged as such.

0 harness defects, 0 registry `argument_defaults` parse warnings. Floors are **cited** from
Stage-2's own N0r arm (EM 0/40) — this probe flew no noise arm. Retention was computed and
reported but carries no verdict clause in this probe, by registration.

The full reading — per-arm and per-tier tables, the robustness envelope, the C3-vs-B2 right-vs-wrong
row contrast, the format-hygiene comparison against B1's degradation finding, the joint
Stage-2/2b/2c L5 supply-law synthesis, and the limitations — is in
**`docs/readiness/2026-08-18-a2t-s2c-verdict.md`**; that document, not this README, is the verdict
of record.
