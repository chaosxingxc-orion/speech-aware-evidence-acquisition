# E108 attempt finalization — pre-read incident record and owner decision request

Date: 2026-08-23. Status: **PRE-READ — no semantic content of the attempt has been read.**
Scope: the single flown attempt under exposure row
`SAEA-SN-EVIDENCE-E108-K1M11-INFORMATION-COMPLETE-ACTION-SUPPORT-ZCOPY` (composed config
`928facf7…12f5`, protocol `fd27d74f…a0f2`, resident session `33639d3d…8698`).

## 1. Facts (from the flight agent's gold-free report; no result value consulted)

- Prompt-fit passed session-bound: 5,118 envelopes, minimum margin 1,623 tokens; the audit's
  own model-free exposure row was committed before the audit ran.
- The flight completed **338/338 contacts** over **108/108 final decisions** with the frozen
  runtime invariants all holding: exact original-speech carriage on every contact
  (`query_source=speech_features`, packet sha bound), zero request/parse/OOM/spill/runaway
  markers, mmproj never loaded (argv + open files + process maps), balanced native slot
  lifecycle events (338 launches = 338 releases; 884 = 884 service-wide), resident PID 607
  never stopped or reloaded. Spend: 338 ≤ 600 calls; 939.881 ≤ 1800 metered audio-seconds;
  wall clock 1,198 s bounds GPU-active ≤ 0.333 h ≤ 0.8 ceiling.
- **Finalization refused**: `profile_server_slot_event_gpu_metrics` raised "request GPU sample
  timeline is unavailable". Root cause: `GpuSampler.start()` performs one synchronous
  `nvidia-smi` poll and, on failure, returns WITHOUT starting its sampling thread; the
  post-run metrics stage then fails closed. No `flight-receipt.json` exists; the attempt is
  not finalized. The slot-event lifecycle check in the same function had already PASSED.
- The one-shot row is spent (no silent retry, correctly honoured). The durable run records
  (request/response/cost triples, decisions file line-counted only, server-log window) are
  complete and hash-stable on disk. No prediction, label, correctness, reward, or response
  meaning was read; the `MODEL_RESPONSE` trace channel was never opened.

## 2. The defect being enforced is a demoted requirement

The refused stage assembles the GPU-utilization telemetry that the same-day owner ruling
(`2026-08-23-knowledge-plane-baseline-rulings.md` §2.1) demoted from admission criterion to
DESCRIPTIVE reporting for scientific cells. The scientific invariants the reader contract
depends on (decision completeness, speech carriage, zero mechanism failures, service
identity) are all independently evidenced.

## 3. Sampler repair (authorized as shared-infrastructure hygiene, proceeding now)

`GpuSampler` start-failure semantics change: a failed initial poll degrades to
`gpu_timeline: NOT_AVAILABLE` plus an explicit defect flag in the receipt and a completed
finalization — never a run-destroying refusal — with unit tests covering both paths. This
repair applies to every future flight regardless of §4's outcome and does not touch the flown
attempt's bytes.

## 4. Owner decision requested — disposition of the flown attempt

- **Option A — successor re-fly**: register a fresh `-R2` row and re-fly the identical cell
  (~338 contacts, ~0.33 GPU-h) after the §3 repair. Cleanest one-shot discipline (matches the
  schema-v2 precedent of never retro-finalizing). Cost: duplicate GPU spend on byte-identical
  inputs; the resend-divergence finding (6/20 at temp 0) means the re-fly is NOT guaranteed
  byte-identical, and the first attempt's outputs must then stay permanently unread.
- **Option B — registered model-free finalization (coordinator recommendation)**: under a new
  `model-free-check` row, rebuild the flight receipt deterministically from the durable
  on-disk records with GPU fields recorded `NOT_AVAILABLE` (wall-clock bound retained), zero
  model contacts, label-blind; then the frozen in-fragment reader runs as originally
  registered. Precedent shape: the pcorrf §8 pre-read accounting adjudication (the ceiling
  metric was interpreted, not the results); distinction from the schema-v2 non-finalization
  precedent: there the failed gate touched the speech-carriage evidence chain, here that chain
  is complete and the missing piece is telemetry the owner already demoted.

Until the owner chooses, the attempt directory is quarantined (read nothing further), and no
successor E108 registration is authored.
