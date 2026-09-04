# G5 fixed16 postflight result analysis

## Scope and result

This is a postflight, zero-contact decomposition of the completed
`SAEA-A2T-G5-EXHAUSTIVE-FAMILY-FIXED16-V1` run. It reads only the recorded G5
PLAN states, execute requests and outputs, the frozen family corpus, the frozen
Audio2Tool scorer-side gold, and the already-recorded G1 M0 outputs for the same
16 identities. It reads no audio and makes no model, tool-service, tokenizer, or
network contact.

The end-to-end G5 result is negative on this fixed16 screen:

| System | Tool correct | Exact | Slot P / R / F1 | Parsed JSON |
|---|---:|---:|---:|---:|
| G5 PLAN -> family compile -> EXECUTE | 4/16 | 3/16 | 0.1143 / 0.3333 / 0.1702 | 16/16 |
| Frozen G1 M0, same 16 IDs | 12/16 | 6/16 | 0.3000 / 0.7500 / 0.4286 | 16/16 |

Relative to M0 on these same identities, G5 loses eight tool-correct rows and
three exact rows. Tool accuracy improves on zero rows, is unchanged on eight,
and regresses on eight. Exact match improves on one row, regresses on four, and
is unchanged on eleven. This comparison is descriptive: the systems have
different request structures, and fixed16 is a small discovery screen rather
than an independent confirmatory population.

The primary failure is family routing and PLAN validation, not selection inside
a correct exhaustive bundle:

- The actual execute request contains every gold tool's family on only 4/16
  rows. Those four rows achieve 4/4 tool accuracy and 3/4 exact match.
- The actual execute request lacks at least one gold family on the other 12
  rows. Those rows achieve 0/12 tool accuracy and 0/12 exact match.
- Therefore there is no observed within-supplied-family tool-selection failure
  in this sample. The only covered-family non-exact row selects the right tool
  but realizes arguments differently from frozen gold.
- Seven PLAN responses are replaced by `INVALID_FALLBACK`. All seven are valid
  JSON with the required object shapes and plausible families, but each invents
  semantic operation verbs such as `set-volume`, `check`, or `set-mode` instead
  of copying the taxonomy's sole allowed operation tag, `execute`.
- The fallback always supplies the same three unrelated families:
  `smart-car-charging-energy`, `smart-home-maintenance`, and
  `wearables-device-state`. It covers the complete gold family set on none of
  the seven fallback rows. Four of those seven raw PLAN responses had already
  named every gold family before strict validation discarded them.

This is strong mechanism evidence within fixed16: family supply is a necessary
gate for G5 tool identity here, while the strict operation-tag interface and its
fixed fallback destroy useful PLAN information.

## Tier breakdown

Each tier has two rows. `T` is tool-correct count, `E` is exact count, and F1 is
the scorer's tier-local micro slot F1.

| Tier | Gold-family-covered rows | G5 T / E / F1 | G1 M0 T / E / F1 |
|---|---:|---:|---:|
| tier1 direct | 0/2 | 0 / 0 / 0.0000 | 2 / 0 / 0.0000 |
| tier2 parametric | 1/2 | 1 / 1 / 0.4000 | 1 / 1 / 0.5000 |
| tier3 multi-intent | 0/2 | 0 / 0 / 0.0000 | 2 / 0 / 0.0000 |
| tier4 implicit | 1/2 | 1 / 1 / 1.0000 | 1 / 0 / 0.0000 |
| tier5 needle | 1/2 | 1 / 0 / 0.0000 | 2 / 1 / 0.5000 |
| tier6 correction | 0/2 | 0 / 0 / 0.0000 | 2 / 2 / 1.0000 |
| tier7 multiturn | 1/2 | 1 / 1 / 0.4000 | 2 / 2 / 1.0000 |
| tier8 intent blending | 0/2 | 0 / 0 / 0.2000 | 0 / 0 / 0.4444 |

Tier1 and tier3 have zero expected argument slots under frozen gold. Their zero
slot F1 is the scorer's defined zero-denominator result and is not evidence that
their argument values are all wrong. Tool accuracy and exact match remain
well-defined.

## Per-row reconstruction

Call notation is `tool(key=value, ...)`; `{}` means the frozen scorer expects no
arguments. `fallback` means the recorded canonical state is
`{"operations":[],"status":"INVALID_FALLBACK"}` and the execute request gets
the fixed three-family fallback above. Family coverage below is measured from
the actual execute request, not inferred from the raw PLAN.

| ID | Raw PLAN family / operation -> actual supply | Frozen gold | G5 prediction | Classification | Frozen G1 M0 |
|---|---|---|---|---|---|
| `tier1_direct:002609` | `smart-car-maintenance / execute` -> same; gold is `smart-home-maintenance` | `resetFilterStatus({})` | `resetTPMSSensors({})` | Family/domain routing | `resetFilterStatus(deviceId=purifier_1)`; tool correct, not exact |
| `tier1_direct:002728` | `smart-home-lighting / execute` -> same; gold is `smart-home-core-control` | `setLighting({})` | `setLightState(deviceId=light_1, state=On)` | Family/category routing | `setLighting(deviceId=light_1, state=On, level=null, color=null)`; tool correct, not exact |
| `tier2_parametric:003923` | `smart-home-core-control / execute` -> same; gold is `smart-home-maintenance` | `rebootDevice(deviceId=smart_hub_central)` | unregistered `execute(label=restart, span=RESTART)` | Family routing plus PLAN-state leakage into call syntax | `restartDevice(deviceId=gateway_1)` |
| `tier2_parametric:006317` | `smart-car-driving-dynamics / execute` -> same, covered | `setFollowDistance(level=6)` | exact gold | Exact | exact gold |
| `tier3_multi_intent:002995` | `smart-home-lighting / dim`; `smart-home-status / list` -> fallback; gold needs `smart-home-core-control` plus `smart-home-lighting` | `getDeviceList({})`; `setBrightness({})` | 17 calls: `getBatteryStatus`, `runNetworkSpeedTest`, `findPairedPhone`, `setChargingAmperage(amps=32)`, `setChargeLimit(percentage=80)`, `setScheduledDeparture(time=08:00, precondition=true)`, `startCharging`, `stopCharging`, `triggerBatteryPreconditioning`, `unlockChargeCable`, `calibrateThermostat(deviceId=thermostat_1, offset=0)`, `rebootDevice(deviceId=camera_1)`, `resetFilterStatus(deviceId=purifier_1)`, `updateFirmware(deviceId=camera_1)`, `setAlarm(time=07:00)`, `setAlwaysOnDisplay(enabled=true)`, `setDoNotDisturb(enabled=true, mode=Sleep)` | Invalid operation tags; fallback bundle enumeration | Both gold tool names; `setBrightness` adds `deviceId=light_kitchen, level=30`; tool correct, not exact |
| `tier3_multi_intent:003153` | `smart-home-climate / set-schedule`; same / `set-mode`; `smart-home-lighting / enable-adaptive` -> fallback. The raw families fully cover gold. | `setThermostatSchedule({})`; `setThermostatMode({})`; `setAdaptiveLighting({})` | `setThermostatSchedule(schedule={nights:{mode:heat, temperature:20}})`; `setAdaptiveLighting(enabled=true, location=bedroom)` | Correct raw families discarded; one call omitted and all contracts absent | All three gold tool names with added default/content arguments; tool correct, not exact |
| `tier4_implicit:001074` | `smart-car-media-cabin / execute` -> same, covered | `controlPlayback(action=Previous)` | exact gold | Exact; the only exact improvement over M0 | `controlPlayback(action=PlayPause)` |
| `tier4_implicit:001148` | `smart-car-status / execute` -> same; gold is `smart-home-media` | `castContent({})` | `getChargeState({})` | Family/domain routing | `[]` |
| `tier5_needle:000241` | `smart-home-lighting / execute` -> same, covered | `setAdaptiveLighting({})` | `setAdaptiveLighting(deviceId=light_1, enabled=true)` | Argument realization / contract-gold mismatch | Same as G5 |
| `tier5_needle:002215` | `smart-home-climate / smart-home-core-control` -> fallback; gold is `smart-home-status` | `getThermostatState(deviceId=thermostat_1)` | `getBatteryStatus({})` | Invalid operation tag and wrong family | exact gold |
| `tier6_correction:002179` | `smart-home-climate / check` -> fallback; gold is `smart-home-status` | `getThermostatState(deviceId=thermostat_1)` | `calibrateThermostat(deviceId=main_thermostat, offset=0)` | Invalid operation tag, wrong family, correction not represented | exact gold |
| `tier6_correction:003197` | `wearables-health-activity / get-heart-rate` -> fallback. The raw family covers gold. | `getBiometricData(type=Heart_Rate)` | `getBatteryStatus({})` | Correct raw family discarded; correction not represented | exact gold |
| `tier7_multiturn:000545` | `smart-home-media / set-volume` -> fallback. The raw family covers gold. | `setVolume(deviceId=speaker_1, level=25)` | `setChargeLimit(percentage=80)` | Correct raw family discarded | exact gold |
| `tier7_multiturn:002120` | `smart-car-climate-environment / execute` -> same, covered | `setRecirculation(enabled=true)` | exact gold | Exact | exact gold |
| `tier8_intent_blending:000581` | Three `wearables-health-activity / execute` operations -> one deduplicated health-family supply; gold also needs `wearables-system-connectivity` | `getHRV(period=Last_Week)`; `installApp({})`; `setHapticStrength({})` | `startWorkout(activity=Walking)`; `getActivitySummary(period=Last_Week)`; `getHRV(period=Last_Week)` | Partial family routing; two intents forced into the health family | Same three tool names as G5, with `activity=Hiking, goal=null` on `startWorkout` |
| `tier8_intent_blending:000720` | `smart-car-navigation / stop`; `smart-car-driving-dynamics / start`; `smart-car-climate-environment / turn-off` -> fallback. The raw family set contains the one gold family but also two extraneous families. | `setCampingMode(enabled=false)`; `setSteeringWheelHeat(enabled=false)` | `setScheduledDeparture(time=08:00, precondition=false)`; `setDoNotDisturb(enabled=true, mode=Driving)` | Invalid operation tags; useful climate family discarded | `cancelNavigation({})`; `setCampingMode(enabled=true)`; `setSteeringWheelHeat(enabled=false)` |

## PLAN and structure findings

### Valid PLANs still expose unintuitive family boundaries

Nine canonical PLANs are valid. Only four fully cover gold. The other five
show that the construction taxonomy's category names are not reliably aligned
with an intuitive speech-level ontology:

- “filter indicator” goes to car maintenance instead of home maintenance;
- “light on” goes to home lighting, while the gold `setLighting` tool is filed
  under home core control;
- “restart” goes to home core control, while `rebootDevice` is filed under home
  maintenance;
- “game replay” goes to car status instead of home media;
- the three blended wearable intents are all assigned to health/activity even
  though two gold calls are filed under system/connectivity.

These are routing failures induced by family semantics, not evidence that the
correct family bundle cannot select a tool.

### The operation vocabulary is a brittle, redundant gate

The taxonomy advertises every family as `[execute]`, yet all seven invalid
responses use more descriptive verbs. Their JSON, required keys, values,
families, roles, turn references, and Boolean fields are otherwise structurally
usable. Strict fail-closed parsing converts the entire PLAN to fallback rather
than preserving its valid family information. In four rows—`003153`, `003197`,
`000545`, and `000720`—the raw family set covers every gold tool family before
that conversion. No counterfactual execute score is claimed, but the lost
coverage is directly observable.

The fallback then replaces a speech-conditioned family decision with a fixed
three-family union. It produces 0/7 tool accuracy. On `002995`, EXECUTE emits 17
calls drawn across that union, consistent with treating an exhaustive bundle as
an action list rather than selecting from it.

### Correction and history fields are not used

Both tier6 raw PLANs set `correction=false`, use no `supersedes` index, and are
invalid for their invented operation tags. Both tier7 PLANs reference only
`current`; neither uses `prior:N`. One tier7 row still succeeds because its final
turn contains enough information, but fixed16 provides no evidence that the
correction/supersession or prior-turn control fields work.

Multi-operation enumeration itself is not absent: both tier3 raw responses and
both tier8 raw responses enumerate multiple operations. The structural problem
is faithful family/operation typing and preservation through validation.

### Parse success is only a syntax check

All 16 G5 outputs parse as JSON tool-call arrays, but `tier2_parametric:003923`
uses the unregistered tool name `execute`. The frozen parser also counts an
empty JSON array as parsed, which is why G1 M0 has 16/16 parse success even
though `tier4_implicit:001148` predicts no calls. “parse16” therefore does not
establish registry validity, nonempty execution, or semantic correctness.

## SUPPLY and USE mechanism findings

The observed conditional result—4/4 tool identity with full family coverage and
0/12 without it—makes SUPPLY coverage the dominant bottleneck in this screen.
Once the correct family is present, the exhaustive unranked family bundle is
sufficient for tool identity on every observed row. It does not improve tool
identity over M0 on any row, however: M0 already has the correct tool on all four
covered rows. G5's only exact improvement is the implicit playback argument on
`tier4_implicit:001074`.

SUPPLY is also not a hard output constraint. On `tier3_multi_intent:003153`, the
fallback request supplies none of the gold climate or lighting contracts, yet
EXECUTE emits two gold tool names from those absent families and omits the third.
Conversely, `002995` emits nearly a fallback-bundle inventory. USE therefore
varies between ignoring supplied contract boundaries and over-consuming them.

The one covered-family argument failure, `tier5_needle:000241`, reveals a frozen
contract/gold tension. Gold expects `setAdaptiveLighting({})`, while both G5 and
M0 emit the contract defaults `deviceId=light_1, enabled=true`. The scorer
correctly marks this non-exact under its frozen semantics, but the miss should
not be interpreted as wrong tool selection. Similar empty-gold/default-argument
effects explain several M0 tool-correct but non-exact rows.

## Disposition

G5 does not qualify as an end-to-end improvement over frozen G1 M0 on fixed16.
The screen does isolate a potentially useful inner mechanism: exhaustive family
contracts select the correct tool whenever actual family supply is complete in
this sample. That signal is currently dominated by three controller defects:

1. family labels do not consistently match intuitive spoken intent;
2. the literal `execute` operation tag rejects otherwise useful PLANs; and
3. the fixed fallback is unrelated to the rejected PLAN and encourages
   irrelevant or enumerative execution.

The result licenses controller diagnosis only. It does not license a superiority
claim, a generalization claim, a production-scale implementation, or a new
flight. In particular, the raw-PLAN observations are not counterfactual scores.

## Audit inputs and reproduction

The analysis script is [`analyze.py`](./analyze.py). It writes nothing and emits
one JSON document to standard output. Its recorded input identities are:

| Input | SHA-256 |
|---|---|
| G5 outputs JSONL | `fe483c0b97bbdb33f4324a5634ecafab901539fcbad7f113e4cf07542888908a` |
| G5 PLAN-state JSONL | `e1703a20c69c23c756a771fe4b958aca00f8ef389b9c81b28130fadd5c7ec191` |
| G5 agent trace JSONL | `eba6e4ba6f91460dd58327a8e73ac1f69e96b5bde0bc8f4bf0c814ed98ac4a91` |
| G1 M0 outputs JSONL | `dea60ff1e63fd2ef11c93edf8808217062fea3f0565ed5b60f136264bc6a9467` |
| G5 family corpus | `92684a16e39985d3c4c6e7e6d62ac54feaa357eaa7c24c744df21950e51f95e5` |
| Frozen scorer semantics (`a2t-scorer-v1`) | `a2b1380f408a29af0a31cb3a0d8d0730fa8ec07e64ec45d14a7e258595ac70a0` |
| Frozen gold parser (`a2t-gold-v1`) | `29e0f2d56a28ce975508ed2e0cfbf2eade7c64907c60d0027909ebcb74da1209` |

The scorer-side manifest entries are resolved locally from the frozen
Audio2Tool asset for exactly the 16 output identities. The script deliberately
does not read the speech files or task transcript fields.

## Correction under a2t-scorer-v2 (2026-09-03)

Zero-contact offline re-score of the same sealed `g5` outputs.jsonl (16/16 rows) and the shared
`A2T-G1-104` M0 baseline (filtered to these same 16 sample ids), v1 identity confirmed to 4 decimals
overall, under the registered `a2t-scorer-v2` (`analysis.a2t_v2_rescore`,
`docs/checks/speech-aware-evidence-acquisition/2026-09-03-a2t-scorer-v2-rescore/`).

| System | v1 exact | v1 tool | v2 exact | v2 tool (ordered) | v2 tool (multiset) | v2 slot F1 | v1 slot F1 | parse rate |
|---|---|---|---|---|---|---|---|---|
| g5 | 0.1875 | 0.2500 | 0.2500 | 0.2500 | 0.2500 | 0.3200 | 0.1702 | 1.0000 |
| m0 (same 16 ids) | 0.3750 | 0.7500 | 0.5625 | 0.7500 | 0.7500 | -- | -- | -- |

Paired contrast, g5 vs. m0 (same 16 ids; v1 and v2, CI90, 10,000 replicates, tier-stratified):

| metric | delta | saves | harms | ties | CI90 |
|---|---|---|---|---|---|
| v1 exact | -0.1875 | 1 | 4 | 11 | [-0.3125, -0.0625] |
| v2 exact | -0.3125 | 1 | 6 | 9 | [-0.4375, -0.1875] |
| v1 tool | -0.5000 | 0 | 8 | 8 | [-0.6250, -0.3750] |
| v2 tool (multiset) | -0.5000 | 0 | 8 | 8 | [-0.6250, -0.3750] |

g5's own EM moves under v2 (0.1875 -> 0.2500) but its deficit versus m0 is unchanged in direction and
grows more negative in the exact-match interval ([-0.3125, -0.0625] v1 -> [-0.4375, -0.1875] v2), and
tool accuracy is unmoved (v2's ordered and multiset tool accuracy are identical for both systems
here, so the -0.5000 gap is scorer-version-invariant). This is a mechanism diagnostic, not a
promotion decision; the reading that g5's exhaustive-family approach underperforms m0 on this same-16
comparison holds under v2 as well.
