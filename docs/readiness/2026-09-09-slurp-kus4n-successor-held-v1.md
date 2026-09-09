# KU-S4N successor configurations held

This note covers two independent experiment fragments:

- KU-S4N: `configs/experiment/slurp-kus4n-candidates-successor-v1.json`
- KU-S4N-t: `configs/experiment/slurp-kus4n-candidates-twin-successor-v1.json`

Each fragment contains its own fixed fit and generation cells, separate run and attempt identities, and separate preparation receipts. The generation run IDs preserve the inherited identities `SAEA-SLURP-KUS4N-CANDIDATES-DEV1000-V1` and `SAEA-SLURP-KUS4N-CANDIDATES-TWIN-DEV1000-V1`. Attempt IDs were generated through the repository's `fresh_attempt_id` helper and validated by `core.attempts.validate_id`.

Both arms retain the existing SLURP DEV-1000 roster, candidate bank, candidate snapshot, sealed closed-list predecessor, decoder-only model fragment, 65,536-token context, eight server slots, and 64-token output ceiling. The complete 60-label inventory remains active, with at most eight additional typed candidate blocks.

Both fit and generation cells remain HELD. Preparation is documentary only until root registers and verifies each arm's full-roster prompt-fit receipt and persistent phase-supply receipt. No placeholder runtime pin, model contact, tokenizer contact, encoder contact, scorer contact or outcome read is authorized.

The exact null calibration artifact is `docs/checks/speech-aware-evidence-acquisition/2026-09-09-null-new500-calibration/calibration.json`, SHA-256 `2bd7e76ea2ea3c03369cd92d2c117c331fd28394a35da3568bf9f3e023cbdcb3`. Its paired speaker-cluster bootstrap uses seed `20260903` and 10,000 draws. Metric-specific operational NI margins are copied from the artifact. NI is reported separately as one-sided 95% lower bound greater than negative delta. Efficacy is separate: intent CI90 lower bound must exceed the maximum of the historical 1.4341 percentage-point floor and the aligned null upper bound, the twin contrast lower bound must exceed zero, and protection metrics must pass their non-inferiority gates.

Two-sided equivalence is reported distinctly: its CI90 must lie inside the metric-specific interval `(-delta, +delta)`. NI does not imply equivalence. A neutral NI result permits exemplar work without an efficacy conclusion; an NI failure remains held with no automatic rerun.

Live or adaptive cases outside the registered fixed shared-controller configuration remain unsupported and held for root review.

Efficacy intent requires the CI90 lower bound to exceed `max(1.4341, 1.9048627925746557)` percentage points, a positive twin contrast, and passing non-inferiority guard gates for scenario exact, action exact, and corpus micro SLU-F1. The normalized secondary must agree in sign on both contrasts. Per-sample F1 and corpus micro F1 remain distinct.

The synthetic factory test constructs a direct fixture under the successor identity. It
proves common carrier construction, not complete candidate-arm request materialization.
Full candidate bank binding and real request coverage remain preparation/fit gates before
generation. The shared slurp_runtime_material binder is used; no private launcher is added.
