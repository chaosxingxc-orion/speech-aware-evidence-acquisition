# `SAEA-E21-FULL44-DISPATCH-ADMISSION-V1` — the cross-call dispatcher's admission test

**STATUS: NEUTRAL.** The cell of
`docs/readiness/2026-09-08-e21-dispatcher-admission-v1-preregistration.md`: the sealed full-44
direct baseline flown a third time under its exact configuration **except one key**,
`obs_prefetch_depth: 1`, so the harness module of
`docs/readiness/2026-09-08-e21-obs-pipeline-v1.md` earns the per-carrier receipt the owner rule of
2026-09-08 requires — *every harness module shows gain or no harm before large-scale use.*

The full reasoning is `docs/readiness/2026-09-08-e21-dispatcher-admission-v1-verdict.md`; the
decided row is in `docs/receipts/harness-admission.json`.

| | |
|---|---|
| study commit | `a58a27e8` (registration) — the flight binds it, `study_repo_dirt` empty |
| flight | attempt `attempt-20260908T191537Z-ba0a08`, 1,593 windows over 44 calls, one attempt, no recovery |
| comparator | `SAEA-E21-FULL44-DIRECT-BASELINE-V2`, attempt `attempt-20260904T233816Z-bcd338` |
| second arm | `SAEA-E21-FULL44-NULL-REPLICATE-V1`, attempt `attempt-20260908T113102Z-bdde07` (depth 0, same resident session) |
| identity | config `94af86c3…`, protocol `5ebcb722…`, split `fcc1b0bc…` — the comparator's split; **the two composed configs differ on exactly one key** |
| falsifier | **1,593 of 1,593** slices byte-identical to the comparator's; prompt tokens 1,935,965 on all three arms |
| corpus WER | 8.19952 % → **8.20730 %**, paired **+0.00778** [−0.02329, +0.03856] call-clustered — **0.13 null half-widths** |
| status | **NEUTRAL** on both pairings; no gating metric harmed, none improved |
| **throughput** | **17.244 → 20.168 windows/min (+16.96 %)**, zero-slot share **17.55 % → 3.75 %**, idle runs **43 → 10** |
| saturation | **0** windows, as both depth-0 arms |
| serving | attached to the resident session `e21-np6-c36864-20260908`; no server started, none stopped |
| cost | 1,593 calls of 1,750; 141,345.8527 metered speech seconds of 150,000; **1.0165 GPU-h of 1.2**; paid API spend 0 |

## The gate this receipt answers

Section 8 of `docs/readiness/2026-09-08-agent-system-episode-and-core-pressure-v1.md`: the contrast
is module ON versus module OFF in the same harness on the same roster (**one config key, never a
second code path**), paired with the carrier's cluster structure, n ≥ 400, cluster bootstrap, CI90;
the guard is non-inferiority at the margin taken from the carrier's own null. The default plan
contains only ADMITTED or NEUTRAL modules.

| metric | delta vs comparator | CI90 | margin | inside? |
|---|---:|---|---:|---|
| corpus WER / ConEC overall | +0.00778 | [−0.02329, +0.03856] | 0.05793 | yes |
| ConEC non-entity | −0.00263 | [−0.01994, +0.01574] | 0.06475 | yes |
| ConEC PERSON | +0.20569 | [−0.07995, +0.51951] | 0.25009 | yes |
| ConEC ORG | −0.32088 | [−0.88314, +0.19584] | 0.35609 | yes |
| numeric-value accuracy | −0.05137 | [−0.19511, +0.09794] | 0.15651 | yes |
| semantic high-impact *(advisory, never gating)* | +0.00222 | [+0.00110, +0.00343] | 0.00148 | **no** |

The margins are `SAEA-E21-FULL44-NULL-REPLICATE-V1`'s own measured call-clustered CI90
half-widths. The semantic rate was removed from the gate **before any number existed**, because its
own same-request null excludes zero; this cell then reproduced that null's high-impact mass exactly
(108 words on both arms, against the comparator's 100), so its pairing-B delta is +0.00000. If it
were gating, the status would be HARMFUL, and `verdict/result-summary.json` says so in
`admission.status_if_advisory_were_gating`.

## Contents

| path | what |
|---|---|
| `flight/falsifier.json` | section 2, run before any score file was opened: 1,593 slices vs the comparator's own, plus the wire totals |
| `flight/flight-receipt.json` | identity anchor, budgets, cost, throughput, the attached session and its monitor summary |
| `flight/occupancy-depth1-cell.json` | this attempt's own slot occupancy from the session `server.log` |
| `flight/occupancy-depth0-null-replicate.json` | the depth-0 arm's, same instrument, same session |
| `flight/rescore-bundles.json`, `flight/jobs.jsonl`, `flight/batch-summary.json` | the four post-hoc scoring bundles and their batch result |
| `flight/verified-score-read.json` | the four verified score reads, per-sample `ref_hit_mask` arrays dropped (`reduction` names the unreduced files and their sha256) |
| `verdict/result-summary.json` | the identity gate, both pairings, the admission decision, per-call, per-stratum, window-level, text identity, throughput and the prediction check |
| `verdict/per-call-table.md` | all 44 calls against both depth-0 arms, with both identity rates |

## The scripts that produced it

| script | role |
|---|---|
| `scripts/e21_dispatch_admission_falsifier.py` | section 2, against the sealed comparator's own `SliceRecord` dumps |
| `scripts/e21_null_replicate_rescore.py` | the four post-hoc scoring bundles — **reused byte for byte** from the null replicate; the mechanism is arm-parameterised and needed no copy |
| `scripts/build_e21_dispatch_admission_verdict.py` | the identity gate, both pairings, section 4's admission rule, the window level and the prediction check |
| `scripts/e21_attempt_slot_occupancy.py` | one attempt's slot occupancy carved out of a shared session `server.log`, reusing `scripts/obs_pipeline_dry_run.py`'s own parsing and occupancy arithmetic |
| `scripts/e21_dispatch_admission_flight_receipt.py` | the flight receipt and the monitor summary |

`MANIFEST.sha256` covers every file here; `sha256sum -c MANIFEST.sha256` verifies from committed
bytes.

## What this receipt does not say

Nothing about quality in either direction — NEUTRAL means the score did not leave this carrier's
own replicate band, and the module is a scheduler whose request bytes are provably unchanged.
Nothing about SLURP or Audio2Tool, which have no measured null. Nothing about
`obs_prefetch_depth` ≥ 2. Nothing about the Earnings-21 test split, and nothing published.
