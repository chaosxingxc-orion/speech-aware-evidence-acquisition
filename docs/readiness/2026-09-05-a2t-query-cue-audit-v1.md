# MF-1: the Audio2Tool query-cue audit, v1 — completed

Model-free, zero contacts. Ledger row `SAEA-A2T-MF-QUERY-CUE-AUDIT-V1`, registered before the
first read of construction query text. Preregistration:
`docs/readiness/2026-09-05-a2t-query-cue-audit-v1-preregistration.md`. Receipts:
`docs/checks/speech-aware-evidence-acquisition/2026-09-05-a2t-query-cue-audit/`
(`summary.json` SHA-256 `81ea9b79e7ca713cb5c0b788190c57ecd147cbee02456565ec02e39cd2afe732`,
`per-pair-table.json` `a8b24736a48057d9c71abedf2adb5ff5c2c9e5122a87abd3fa036e78196f533b`,
`decontamination.json` `68e5b9524813d7ee9b7e8ecd5414f0613eaf13008bab24bc74c400fa244bd7f1`,
`MANIFEST.sha256`). Code: `analysis/a2t_query_cue_audit.py`, runner
`scripts/run_a2t_query_cue_audit.py`, tests `tests/unit/test_a2t_query_cue_audit.py`.
Outbound connection attempts: **0** against 0 targets, guard armed before the first input opened.

## Verdict

**The KC-A1 gate PASSES: 235 of the sealed 4,000-row misses sit inside disjoint TARGET tool sets,
against a threshold of 100** (230 if the two pairs whose accuracy does not beat their own
majority-class rate are struck out; 278 if every intra-target confusion is counted, not only the
audited directions). Twenty-two of 53 audited pairs are TARGET, two are LABEL NOISE, eighteen are
UNCERTAIN and eleven are INSUFFICIENT-DATA. **No pair is DOMAIN-ONLY**: every cross-domain pair
that cleared the 0.80 separability bar also cleared the 20-point description bar, and ORG-1's
domain grouping — the mechanism DOMAIN-ONLY was defined to defer to — was dropped as HARMFUL.

The gate passes, and the number should be read with the finding beside it: **147 of those 235 rows
are the lighting cluster, and the lighting cluster is exactly the error mass A2T-ORG-1 already
proved it can move without gaining a point.** Under the grouped registry the same directions fall
from 147 to 76, and the flight still lost 3.23 pp because the misses became same-domain ones. What
MF-1 adds is that the cue is *there* — the queries separate at 0.86 to 1.00 on every lighting pair
— so the failure of ORG-1 was one of prompt form and of where the model falls after the domain is
fixed, not of missing information. KC-A1 is therefore admissible and is a genuine test, but its
expected value is not "recover 235 rows".

## 1. Population and legality

| quantity | primary | strict |
|---|---:|---:|
| definition | every `(tier, query_idx)` unit whose whole BLOCK is untouched by the exposure union | `propose_partition(...).construction`, which additionally removes the legacy 400-block PROPOSED evaluation tier |
| construction units | **3,207** | 1,667 |
| distinct `query_idx` blocks | **1,689** | 1,289 |
| manifest items behind them | 5,953 | 3,129 |
| sample-id overlap with the exposure union | **0** | **0** |
| block overlap with exposed blocks | **0** | — |

The exposure union is the committed one: **5,279 identities from 14 evaluation sources** (the
frozen 400, the three official-population rosters, the two 104-row AgentLoop cohorts, the seven
`d1-a2t-*` media supplements, and the reserved `A2T-FRESH-800-V1` roster), reserving 2,956 of the
carrier's 4,645 blocks. Decontamination is fail-closed: the run refuses to write a number if either
population touches the union.

**Declared deviation.** The preregistration wrote the population as
`propose_partition(...).construction`. That expression additionally removes the 400-block *proposed*
evaluation tier, which is a proposal and has never been a registered split. Under the union that
now also reserves A2T-FRESH-800 it costs a further 48 % of the remaining units and leaves
single-digit row counts on most twins: on the strict population **41 of 53 pairs are
INSUFFICIENT-DATA** and the gate is unmeasurable there (its measurable TARGET mass is 62). The
primary population is therefore the exposure-free construction pool, the strict population is
measured and reported beside it pair for pair in the same receipt, and both are proven disjoint
from every evaluation identity. The deviation is recorded in the ledger row, not discovered later.

## 2. What was measured, and how

* **Separability ceiling.** Bag-of-words multinomial naive Bayes (a linear model in bag-of-words
  features), add-one smoothed, **uniform class priors** so the statistic answers "does the query
  carry a cue" rather than "can the prior be exploited"; 5 folds **grouped by `query_idx`**, seeded
  at 20260903, so no block's re-renderings straddle a fold. Reported as accuracy (the preregistered
  statistic) with balanced accuracy and the majority-class rate beside it, plus the top-15 per-token
  log-odds each side (tokens seen at least 3 times).
* **Description-cue coverage.** For each side, the share of its queries carrying at least one
  content token of its own registry description/signature against the share carrying one of the
  twin's; the pair's gap is the mean of the two sides' differences in points. Exclusive-token
  variants and the shared-token list are in the receipt.
* **Domain-cue coverage** (cross-domain pairs only), from fixed word lists that are **mutually
  disjoint by construction** — the code refuses a word claimed by two domains, which is why
  "garage", "camera", "fan", "lock", "door", "window", "alarm", "battery" and "volume" appear in no
  list: each names a real device in more than one domain of this registry.
* **Sealed-error cross-check.** Misses in each direction over the sealed 4,000 official-population
  rows (1,544 misses: 172 + 464 + 908), through the registered `a2t-toolcall-official` scorer over
  already-sealed outputs. A2T-ORG-1's own 4,000 rows (1,673 misses) are read as a fourth manifest,
  cross-check only.

**Pair set.** The 14 named pairs of the three official-population verdicts, the A2T-ORG-1 verdict
and the loop's lighting cluster, plus every additional unordered pair the sealed miss table shows at
least 5 times in one direction — 39 more, 53 in all. Every tool name is verified against
`tools_registry.csv`; a pair naming an unregistered tool raises.

**One refusal added to the preregistered rule.** A pair whose either side holds fewer than 5
construction units or fewer than 5 distinct blocks is INSUFFICIENT-DATA: a 5-fold grouped
classifier on three queries measures nothing. Those pairs keep their error mass in the report and
can never be a TARGET.

**One inconsistency in the preregistration, named rather than silently resolved.** Section 4 glosses
the 20-point description clause as "the current description does not carry it", but the arithmetic
it fixes (own-description share minus twin-description share ≥ 20 points) is satisfied when the
queries align with their own description *more* than with the twin's — that is, when a
description-level contrast is expressible in the vocabulary speakers actually use. The arithmetic is
applied exactly as written; the gloss is wrong about its own metric and is corrected here.

## 3. The per-pair table

`sep` is accuracy, `bal` balanced accuracy, `gap` the description-cue gap in points, `dom` the
domain-cue coverage (cross-domain only). `*` marks a pair whose accuracy does not beat its own
majority-class rate — the ceiling is then an artefact of side sizes, and it is flagged rather than
overridden. `A→B / B→A` are sealed baseline misses in each direction; `ORG-1` is the same mass
after the grouped registry; `strict` is the strict population's row counts.

| pair | class | units L / R | sep | bal | gap | dom | A→B / B→A | mass | ORG-1 | strict | decision |
|---|---|---|---|---|---|---|---|---:|---:|---|---|
| `setColor+setColorTemperature+setLighting` / `setAmbientLighting` | cross | 169 / 9 | 0.949* | 0.605 | 28.9 | 0.23 | 88 / 0 | 88 | 25 | 48/4 | **TARGET** |
| `setSecurityMode` / `armSecuritySystem` | same | 59 / 3 | n/a | n/a | 11.6 | — | 64 / 0 | 64 | 72 | 1/3 | **INSUFFICIENT-DATA** |
| `rebootDevice` / `restartDevice` | same | 50 / 35 | 0.776 | 0.780 | −7.7 | — | 41 / 1 | 42 | 74 | 10/35 | **UNCERTAIN** |
| `setAmbientLighting` / `setColorTemperature` | cross | 9 / 30 | 0.923 | 0.911 | 50.6 | 0.31 | 0 / 35 | 35 | 9 | 4/6 | **TARGET** |
| `setLighting` / `setLightState` | same | 90 / 5 | 0.926* | 0.489 | −5.0 | — | 33 / 0 | 33 | 25 | 40/5 | **UNCERTAIN** |
| `setAmbientLighting` / `setLighting` | cross | 9 / 90 | 0.950 | 0.822 | 34.4 | 0.20 | 0 / 28 | 28 | 11 | 4/40 | **TARGET** |
| `getApplianceState` / `getApplianceStatus` | same | 44 / 49 | 0.581 | 0.584 | 15.8 | — | 25 / 2 | 27 | 28 | 41/19 | **LABEL-NOISE** |
| `findMyDevice` / `findPairedPhone` | cross | 26 / 10 | 0.694* | 0.542 | 11.2 | 0.32 | 25 / 0 | 25 | 21 | 7/3 | **UNCERTAIN** |
| `setAmbientLighting` / `setColor` | cross | 9 / 49 | 0.862 | 0.782 | 22.8 | 0.25 | 0 / 25 | 25 | 5 | 4/2 | **TARGET** |
| `getAirQuality` / `getAirQuality_diag` | same | 26 / 48 | 0.865 | 0.825 | 13.4 | — | 11 / 11 | 22 | 37 | 19/30 | **UNCERTAIN** |
| `setGarageDoor` / `setGarageOpener` | cross | 5 / 2 | n/a | n/a | 0.0 | 0.35 | 22 / 0 | 22 | 33 | 5/2 | **INSUFFICIENT-DATA** |
| `setFanMode` / `setFanSpeed` | cross | 39 / 7 | 0.826* | 0.546 | −4.6 | 0.06 | 21 / 0 | 21 | 18 | 13/7 | **UNCERTAIN** |
| `setGroupLightState` / `setLighting` | same | 55 / 90 | 0.855 | 0.855 | 20.5 | — | 15 / 3 | 18 | 27 | 38/40 | **TARGET** |
| `setVolume` / `adjustVolume` | cross | 28 / 2 | n/a | n/a | 1.8 | 0.23 | 18 / 0 | 18 | 9 | 2/2 | **INSUFFICIENT-DATA** |
| `streamCamera` / `viewRemoteCamera` | cross | 44 / 5 | 0.816* | 0.632 | −10.0 | 0.54 | 17 / 1 | 18 | 7 | 44/5 | **UNCERTAIN** |
| `getCameraStream` / `streamCamera` | same | 46 / 44 | 0.656 | 0.658 | −1.1 | — | 15 / 2 | 17 | 20 | 2/44 | **UNCERTAIN** |
| `controlPlayback_home` / `controlPlayback` | cross | 8 / 42 | 0.800* | 0.729 | 7.4 | 0.38 | 0 / 16 | 16 | 9 | 1/7 | **UNCERTAIN** |
| `getNetworkHealth` / `runNetworkSpeedTest` | same | 71 / 14 | n/a | n/a | 19.2 | — | 16 / 0 | 16 | 18 | 33/7 | **INSUFFICIENT-DATA** |
| `activateScene` / `activateRoutine` | same | 46 / 65 | 0.820 | 0.824 | 20.3 | — | 12 / 3 | 15 | 26 | 37/44 | **TARGET** |
| `setColor` / `setLighting` | same | 49 / 90 | 0.734 | 0.702 | −1.5 | — | 15 / 0 | 15 | 32 | 2/40 | **UNCERTAIN** |
| `controlPlayback` / `playMedia` | cross | 42 / 22 | 0.672 | 0.620 | 11.6 | 0.14 | 8 / 5 | 13 | 18 | 7/1 | **UNCERTAIN** |
| `getBiometricData` / `getHRV` | same | 56 / 51 | 0.869 | 0.872 | 27.7 | — | 8 / 5 | 13 | 13 | 41/36 | **TARGET** |
| `setAmbientLighting` / `setBrightness` | cross | 9 / 18 | 0.926 | 0.917 | 27.8 | 0.17 | 0 / 13 | 13 | 5 | 4/1 | **TARGET** |
| `getLockState` / `getLockStatus` | cross | 58 / 0 | n/a | n/a | 0.9 | 0.15 | 12 / 0 | 12 | 17 | 21/0 | **INSUFFICIENT-DATA** |
| `setAdaptiveLighting` / `setAmbientLighting` | cross | 8 / 9 | n/a | n/a | 23.6 | 0.24 | 12 / 0 | 12 | 4 | 6/4 | **INSUFFICIENT-DATA** |
| `setAmbientLighting` / `setGroupLightState` | cross | 9 / 55 | 0.953 | 0.833 | 31.0 | 0.47 | 0 / 12 | 12 | 8 | 4/38 | **TARGET** |
| `setApplianceMode` / `startCleaning` | same | 20 / 32 | 0.885 | 0.869 | 28.8 | — | 12 / 0 | 12 | 6 | 6/6 | **TARGET** |
| `setBrightness` / `setLighting` | same | 18 / 90 | 0.843 | 0.617 | 1.1 | — | 4 / 8 | 12 | 17 | 1/40 | **UNCERTAIN** |
| `setAudioVolume` / `setVolume` | cross | 0 / 28 | n/a | n/a | −3.6 | 0.23 | 0 / 11 | 11 | 21 | 0/2 | **INSUFFICIENT-DATA** |
| `getBatteryLevel` / `getBatteryStatus` | cross | 46 / 2 | n/a | n/a | 1.1 | 0.39 | 10 / 0 | 10 | 8 | 23/2 | **INSUFFICIENT-DATA** |
| `setLockState` / `setLockState_home` | cross | 64 / 9 | 0.863* | 0.492 | −4.8 | 0.34 | 9 / 1 | 10 | 11 | 9/1 | **UNCERTAIN** |
| `getAirQuality_diag` / `setAirQualityMode` | cross | 48 / 3 | n/a | n/a | 41.7 | 0.27 | 9 / 0 | 9 | 7 | 30/3 | **INSUFFICIENT-DATA** |
| `rampBrightness` / `setAmbientLighting` | cross | 17 / 9 | 0.731 | 0.768 | 42.5 | 0.23 | 7 / 0 | 7 | 4 | 6/4 | **UNCERTAIN** |
| `rebootDevice` / `runNetworkSpeedTest` | same | 50 / 14 | n/a | n/a | 46.3 | — | 6 / 1 | 7 | 8 | 10/7 | **INSUFFICIENT-DATA** |
| `setAlarm` / `setSecurityMode` | cross | 58 / 59 | 0.966 | 0.966 | 18.0 | 0.31 | 0 / 7 | 7 | 3 | 41/1 | **UNCERTAIN** |
| `setGroupLightState` / `setLightState` | same | 55 / 5 | 0.917* | 0.591 | 1.8 | — | 7 / 0 | 7 | 1 | 38/5 | **UNCERTAIN** |
| `setTargetTemperature` / `setThermostatMode` | same | 25 / 48 | 0.699 | 0.618 | −0.8 | — | 7 / 0 | 7 | 4 | 2/7 | **UNCERTAIN** |
| `activateRoutine` / `setSecurityMode` | same | 65 / 59 | 0.911 | 0.913 | 55.2 | — | 0 / 6 | 6 | 8 | 44/1 | **TARGET** |
| `activateScene` / `setSecurityMode` | same | 46 / 59 | 0.895 | 0.892 | 35.8 | — | 0 / 6 | 6 | 2 | 37/1 | **TARGET** |
| `calibrateCameras` / `updateFirmware` | cross | 7 / 55 | 0.935 | 0.714 | 90.1 | 0.43 | 0 / 6 | 6 | 8 | 7/42 | **TARGET** |
| `getLightState` / `setAmbientLighting` | cross | 29 / 9 | 0.895 | 0.893 | 42.5 | 0.37 | 6 / 0 | 6 | 3 | 8/4 | **TARGET** |
| `setColorTemperature` / `setLighting` | same | 30 / 90 | 0.850 | 0.789 | 6.1 | — | 6 / 0 | 6 | 32 | 6/40 | **UNCERTAIN** |
| `activateRoutine` / `setApplianceMode` | same | 65 / 20 | 0.965 | 0.925 | 43.9 | — | 0 / 5 | 5 | 2 | 44/6 | **TARGET** |
| `calibrateCameras` / `rebootDevice` | cross | 7 / 50 | 0.877* | 0.623 | 57.9 | 0.51 | 0 / 5 | 5 | 6 | 7/10 | **TARGET** |
| `castContent` / `playMedia` | same | 40 / 22 | 0.871 | 0.839 | 47.2 | — | 5 / 0 | 5 | 4 | 6/1 | **TARGET** |
| `getBiometricData` / `setHapticStrength` | same | 56 / 39 | 0.990 | 0.987 | 65.1 | — | 0 / 5 | 5 | 5 | 41/37 | **TARGET** |
| `getHRV` / `setRomanceMode` | cross | 51 / 10 | 0.967 | 0.940 | 83.1 | 0.41 | 5 / 0 | 5 | 4 | 36/4 | **TARGET** |
| `rebootDevice` / `streamCamera` | same | 50 / 44 | 0.925 | 0.927 | 35.5 | — | 5 / 0 | 5 | 7 | 10/44 | **TARGET** |
| `resetFilterStatus` / `setAmbientLighting` | cross | 61 / 9 | 1.000 | 1.000 | 90.3 | 0.43 | 5 / 0 | 5 | 0 | 47/4 | **TARGET** |
| `setBrightness` / `setGroupLightState` | same | 18 / 55 | 0.877 | 0.769 | 36.6 | — | 0 / 5 | 5 | 8 | 1/38 | **TARGET** |
| `setClimate` / `setTargetTemperature` | cross | 10 / 25 | 0.514* | 0.420 | 14.0 | 0.53 | 0 / 5 | 5 | 10 | 4/2 | **LABEL-NOISE** |
| `setDoNotDisturb` / `setDrivingMode` | cross | 70 / 2 | n/a | n/a | 11.4 | 0.11 | 5 / 0 | 5 | 4 | 45/2 | **INSUFFICIENT-DATA** |
| `setHvacMode` / `setThermostatMode` | cross | 8 / 48 | 0.857* | 0.604 | 8.3 | 0.55 | 0 / 5 | 5 | 4 | 4/7 | **UNCERTAIN** |

Class totals, each sealed direction counted once (a cluster pair and the individual pairs inside it
cover the same directions and must not both be added):

| class | pairs | sealed miss mass |
|---|---:|---:|
| TARGET | 22 | **235** |
| UNCERTAIN | 18 | 283 |
| INSUFFICIENT-DATA | 11 | 186 |
| LABEL-NOISE | 2 | **32** |
| DOMAIN-ONLY | 0 | 0 |

## 4. The TARGET list — five disjoint targets, 23 tools

A tool belongs to at most one target: TARGET pairs are merged as an undirected graph and the
derived lighting family (12 registry tools, membership recomputable from a lighting head word in
the description, name or signature) is pre-merged into one node. `strict` counts only the audited
directions, once each; `component` counts every sealed miss whose gold and predicted tool both sit
inside the target.

| target | tools | strict | component | ORG-1 residual |
|---|---|---:|---:|---:|
| **lighting** | `getLightState`, `resetFilterStatus`, `setAmbientLighting`, `setBrightness`, `setColor`, `setColorTemperature`, `setGroupLightState`, `setLighting` | **147** | 186 | 76 |
| **activateRoutine** | `activateRoutine`, `activateScene`, `setApplianceMode`, `setSecurityMode`, `startCleaning` | **44** | 48 | 44 |
| **getBiometricData** | `getBiometricData`, `getHRV`, `setHapticStrength`, `setRomanceMode` | **23** | 23 | 22 |
| **calibrateCameras** | `calibrateCameras`, `rebootDevice`, `streamCamera`, `updateFirmware` | **16** | 16 | 21 |
| **castContent** | `castContent`, `playMedia` | **5** | 5 | 4 |
| **total** | 23 tools | **235** | **278** | 167 |

The cap of 12 targets is not reached, so nothing is dropped. `resetFilterStatus` is in the lighting
target because its only TARGET pair is with `setAmbientLighting`; it is a maintenance tool and a
contrast note for it will be about filters, not lights.

## 5. Where the error mass is NOT addressable, and what that says

* **The single largest confusion in the corpus cannot be audited.** `setSecurityMode →
  armSecuritySystem` is 64 of 1,544 baseline misses and rises to 72 under ORG-1, and
  `armSecuritySystem` has **3 construction units in 3 blocks** — the twin barely exists as a gold
  label. Six more INSUFFICIENT-DATA pairs have the same shape (`setGarageOpener` 2 units,
  `adjustVolume` 2, `getLockStatus` **0**, `setAudioVolume` **0**, `getBatteryStatus` 2,
  `setDrivingMode` 2). **186 rows of error mass, 12 % of all misses, sit on pairs whose second tool
  the corpus almost never uses as gold.** That is a property of the release, not of the model, and
  no description rewrite can be validated against it from construction data alone.
* **Two pairs are label noise: 32 rows, the floor of any Audio2Tool mechanism.**
  `getApplianceState` / `getApplianceStatus` (27 rows, separability 0.581 on 44 against 49
  well-populated queries — the two tools' construction queries are genuinely not separable) and
  `setClimate` / `setTargetTemperature` (5 rows, 0.514). Their top log-odds tokens are appliance
  names on both sides: `washer`, `laundry`, `maker` against `oven`, `dishwasher`, `cycle`. The
  distinction is arbitrary from the query's point of view.
* **`rebootDevice` / `restartDevice`, 42 rows and the biggest single miss under ORG-1 (74), is
  UNCERTAIN and nearly noise**: separability 0.776, and a **negative** description gap (−7.7) —
  each tool's queries touch the twin's description vocabulary slightly more than their own. The
  descriptions ("Performs a soft reboot of a device" / "Reboots a specific smart device") are
  near-synonymous, so the pair is a candidate for the loop only if a rewrite invents a distinction
  the corpus itself does not carry. It should not be a round-1 target.
* **Three high-mass UNCERTAIN pairs fail on the description clause with high separability**:
  `setLighting` / `setLightState` (33, sep 0.926 but imbalance-flagged and gap −5.0),
  `setFanMode` / `setFanSpeed` (21, 0.826, gap −4.6), `streamCamera` / `viewRemoteCamera` (18,
  0.816, gap −10.0). The cue is in the speech; the registry's own words are not the cue. These are
  the natural second-round candidates if KC-A1 is admitted, and the preregistration already reserves
  UNCERTAIN pairs for "if capacity allows".

## 6. Consequences for KC-A1 and the evolution loop

1. **KC-A1 is gated ON** (235 ≥ 100, 230 excluding imbalance-flagged pairs). Its preregistration
   must cite this TARGET list and its 235-row addressable mass, and must state the lighting caveat
   above: 147 of the 235 rows are directions ORG-1 already halved without gaining a point, so a
   KC-A1 gain has to come from the contrast content surviving at ORG-1's own prompt cost.
2. **Form is the confound to control.** ORG-1 changed shape (465 lines against 155, +87 tokens) as
   well as content and lost 3.23 pp with `wearables` −3.38 on 13 barely-confusable tools. KC-A1's
   inline append and its equal-token control KC-A1c are the right design, and the +40-token cap of
   the loop's section 5 should be enforced from round 0.
3. **The loop's targets are named.** Five disjoint targets, 23 tools, well under the cap of 12
   targets; the lighting cluster is one target as the program requires.
4. **The floor is 32 rows of label noise plus 186 rows of pairs the corpus cannot support.** Any
   Audio2Tool mechanism that claims more than roughly 1,326 of the 1,544 misses are recoverable is
   claiming something this audit contradicts.

## 7. Deviations and limits

1. **Population**, as declared in section 1: the primary population is the exposure-free
   construction pool, not `propose_partition(...).construction`. Both are in the receipt.
2. **INSUFFICIENT-DATA** is an addition to the preregistered label set — a refusal, never a verdict,
   and never counted as TARGET.
3. **The imbalance flag** is a diagnostic, not an override: accuracy stays the decision statistic
   exactly as preregistered, and the two flagged TARGET pairs are named in `summary.json`.
4. **`propose_partition` was repaired to make the strict column computable at all.** Under the
   union that now reserves A2T-FRESH-800, the 400-block draw starved nine smart_home tools
   (`broadcastMessage`, `castContent`, `controlPlayback_home`, `getCameraStream`, `rampBrightness`,
   `setAdaptiveLighting`, `setApplianceMode`, `setBrightness`, `setHumidifierState`) and the
   fail-closed floor check refused the whole partition. Every tool the free pool can supply now
   keeps one deterministic block out of eval candidacy, so the starvation branch is unreachable
   rather than luck-dependent; 46 blocks are protected this way beside the 223 already protected for
   rare tools.
5. **Lexical only.** The classifier reads words, not prosody or acoustics. A cue the speech carries
   and the transcript does not is invisible here, so every separability number is a lower bound on
   what the frozen core could in principle use, and an upper bound only on lexical discriminators.
6. **The ceiling is not a promise.** A separability of 0.95 says a discriminator exists in the query
   surface; it says nothing about whether a 200-character description can transfer it to a frozen
   core across 152 tools. That is what KC-A1 measures.
