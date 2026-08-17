# P-SLU flight attempt 2026-08-17 — NOT FLOWN (blocked at pre-flight)

**Zero frozen-core contact occurred.** No `llama-server` was spawned, no attempt directory was
created under `$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pslu-n60/`, and the exposure row
`SAEA-PROBE-pslu-n60` remains `consumed = no`. This directory is the receipt for the pre-flight
pass and for the blocker it found.

Probe: `docs/readiness/2026-08-17-pslu-preregistration-REGISTERED.md`.
Flight config: `configs/probes/g0-binding/pslu-flight.json`. Profile `bounded-discovery-probe`.

## Blocker: SLURP has no D1 media-identity closure

`core.model.lifecycle` (the `FrozenCoreAdapter` construction path every `rails.core_client.
FrozenCoreClient` request goes through) calls `gate.verify_media_identity(binding.carrier_lock_key,
...)` whenever `binding.media_relpaths` is non-empty — and `rails.core_client.build_payload_binding`
always populates `media_relpaths` (deliberately: its own docstring notes the production caller
"always supplies it, so a real run is never silently exempted from this check").

`contracts.gate_media_identity.verify_media_identity` resolves D1's artifact **through** the E0
closure receipt (`contracts.gate_d1_lookup._d1_identity_artifact_path` → `deliverables.d1_identity.
artifact` → `docs/receipts/artifacts/d1-identity.json`). That artifact closes over exactly three
carriers — `conec`, `earnings21-original`, `earnings22-original` — and
`data.carriers.resolve_media_identity_carrier("slurp")` returns `"slurp"` unchanged (no alias).

Measured, not inferred (`d1-media-identity-refusal.log`):

```
resolve_media_identity_carrier('slurp') -> slurp
verify_media_identity('slurp'): REFUSED -> GateClosed: D1 identity artifact has no per-sample
media identity for carrier 'slurp' (plan carrier 'slurp'); model touch refused
```

Every one of the flight's 363 requests would be refused before reaching the core. The two ways
around it are both outside flight-operations authority and neither was taken:

1. constructing the binding without `media_relpaths` — deliberately disabling the I-4 media
   identity rail *and* the payload↔loader `media_relpath` binding in `core.model.binding`;
2. extending `docs/receipts/artifacts/d1-identity.json` — an E0 re-closure, since `_validate_e0`
   re-verifies that artifact's hash against `docs/receipts/e0-closure.json`.

`data.identity` has `earnings21_layers` / `earnings22_layers` / `conec_layers` and no
`slurp_layers`, so SLURP D1 admission is unwritten work, not merely an unrun generator. The same
gap blocks the P-A2T A0 flight (`audio2tool` is likewise absent from D1).

## What the pre-flight DID verify (all model-free)

`preflight-before-ledger-repair.log` — every substantive registered fact reproduced:

- frozen sample manifest resolves against the governed `devel` split (8,690 samples loaded,
  60 selected in the frozen order), **60/60 flac present**;
- **182.26 s** total audio, mean 3.04 s; **89 gold slots**; **18** distinct gold scenarios — each
  matching the preregistration exactly;
- roster table loads under its own legality checks: 18 scenario rosters, 55 global types,
  100 dose-capped full-roster entries, 18 derangement keys; every gold scenario has both an A1
  roster and an A4 derangement partner;
- all 3 seeded silence-swap sample ids lie inside the frozen 60;
- exposure row `SAEA-PROBE-pslu-n60` present exactly once, `consumed = no`, budgets 450 calls /
  1500 audio-seconds / 0.5 GPU-h;
- `ExecutionPlan` validates (`bounded-discovery-probe`, `discovery`).

## Pre-flight registration repair (committed separately, before this receipt)

The registered row's `split identity hash` **cell** carried the 8-hex prose prefix `fc9de436`,
while `contracts.gate_exposure._require_exposure_preregistration` compares that cell verbatim
against `ExecutionPlan.split_identity_hash`, which `contracts.plan` requires to be a full 64-hex
SHA-256 — an independent gate refusal, found first. The cell now carries the full hash read from
`configs/probes/g0-binding/pslu-sample-devel-n60.json`. Re-checked with the gate's own methods
(`gate-recheck-after-ledger-repair.log`): exposure pre-registration PASS, carrier scope PASS,
E0 receipt PASS. No other cell changed.

## `launcher/`

The full flight launcher, written to the bridge's documented operator sequence
(`FrozenCoreGate.for_study_repo` → `start_session` → `TRANSPORTS.resolve("llama-server")` →
`FrozenCoreClient` → 3 × `build_silence_swap_slice` + `register_slice` → `run_pslu_flight` →
`client.close()`). It is **import-verified only** (`launcher-import-check.log`); it has never been
run against a server, because the D1 blocker above sits in front of the first request. It is
archived so the next attempt starts from proven machinery rather than rebuilding it.

Notable properties, all documented in the files themselves:

- it never reads a result — scored rows are written to `outputs.jsonl` for the separately
  registered one-shot read mission, and only request index / sample id / latency / ok-fail /
  response *length* are logged;
- `--attempt-id` resumes an aborted attempt by replaying `responses.jsonl` instead of
  re-contacting the core, failing closed if a replayed request's message hash diverges — so a
  server wedge costs only the un-flown remainder of the registered call budget;
- `flight_identity.py` builds the run's `values`/`config_hash` from the **committed** model
  fragment `configs/model/q4km-featcache.json` with three documented deltas (campaign-own feature
  cache; the batch-executor-only `id_slot` sentinel dropped, which `core.model.adapter` would
  otherwise refuse; a probe-identity block), because no SLURP dataset/baseline/experiment fragment
  exists for `core.config.compose` and the flight config itself assigns `protocol_hash` to the
  launcher.

Feature cache: `/home/chao/feat-cache/slurp-q4km`, created empty and unused, per the
`<dataset>-<encoder>` rule in `docs/featcache-directories.md`. The legacy 26 GB
`/home/chao/feat-cache/q4km` was never opened.
