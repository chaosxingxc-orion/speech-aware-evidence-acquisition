# E21 current-executor four-row engineering proof

Experiment configuration: configs/experiment/e21-current-executor-four-row-proof-v1.json.

## Scope

This is a held, model-free engineering proof for the current shared path:
core.flight.FlightRuntime, obs-repair-loop-ojw, phase-direct-only-v1, and the
raw-window request materializer. It does not register exposure, start a
service, contact a model or tokenizer, decode a score, or read an outcome. It
is not an effectiveness screen.

The proof preserves the sealed KC-E1f predecessor binding from
SAEA-E21-FULL44-DIRECT-BASELINE-V2, the existing cap-12 ConEC brief, and the
registered substitution-only delivery rule with parameters 4, 0.60, and 0.10.
It also pins the existing model-free judge plan and its two registered judge
identities. Those pins make the intended routing auditable; they do not make
the present bridge execute a live review phase.

## Deterministic rows

The source population is the already authorized 44-call Earnings-21 discovery
roster. The configuration sorts the sealed judge plan by sample_id,
parent_window_index, and unit_index, then takes its first four distinct units.
The result is one call and four fixed parent-window identities:

| row | window | unit | re-cut seconds |
| --- | --- | --- | --- |
| 1 | 4320211#w0005 | 4320211#u0001 | 388.4177215189873 to 398.7974683544304 |
| 2 | 4320211#w0006 | 4320211#u0002 | 487.8755364806867 to 498.2618025751073 |
| 3 | 4320211#w0009 | 4320211#u0003 | 799.6370967741935 to 810.0 |
| 4 | 4320211#w0011 | 4320211#u0004 | 946.9367588932806 to 957.6482213438735 |

The canonical JSON encoding of the four selected routing records hashes to
046fc42decae75f12445215362178b0e4b78e781db3d44709a3b4f7765294d0f.
Selection reads plan routing metadata only. It does not use transcript text,
reference labels, scores, or other outcome information.

## Current-executor limit

ControllerWindowHook supports only phase-direct-only-v1. It seals the single
direct contact and delegates delivery to the existing repair hook. It rejects
phase_review, phase_supply, top-level judges, and other multi-phase controls.
The baseline window_review remains documentary metadata for the already sealed
re-listen plan; it is not a live Reviewer, Planner, or relisten propagation
path. That live chain is an unresolved G6 shared-controller gap.

The verified probe-sample receipt narrows the runtime roster to call 4320211 with its own split identity. The new E21 runtime subset seam verifies that receipt, verifies frozen discovery, requires construction role and containment in discovery, then selects the verified call from the full discovery loader. The four-unit plan covers the complete one-call roster. The shared fitter and OJW fake-transport integration test now passes: each constructs exactly four matching requests and no fifth request, using the real repair hook, shared controller, and deterministic synthetic audio. Root independently ran the integration and adapter tests (11 passed); the receipt is `docs/checks/speech-aware-evidence-acquisition/2026-09-10-e21-exact-four-root-review/review.json`. This proves model-free request and delivery integration only.

This does not enable a live Reviewer, Planner, or multi-phase relisten chain. The pinned judges remain source lineage for the model-free plan; ControllerWindowHook supports phase-direct-only-v1 only.

## Admission boundary

The cell remains held for no-GPU-mmproj serving qualification, exact-window feature preparation, and root registration and admission. Its historical GPU-mmproj model fragment describes the model-free prototype only and cannot authorize live use under OWNER-FEATURE-SERVING-007. Any later execution must select and pin the qualified replacement identity and use a newly registered attempt and exposure row before the first model-facing contact. This document grants neither. The live G6 Reviewer, Planner, and relisten chain remains unresolved.
