# P-A2T selection-loss decomposition verdict — DRIFT-CONFIRMED (registered model-free re-read, 2026-08-18)

Mechanical outcome computed by the pinned offline read suite (`1a2daf6` — `scripts/a2t_loss_decomp.py`
-> `speech_aware_evidence_acquisition.analysis.a2t_loss_decomp`; 38/38 unit tests green immediately
before the read, clean tree at `1a2daf6`) over the three ALREADY-CONSUMED attempts of record:
Stage-2 `attempt-20260818T124955Z-84b944`, Stage-2b `attempt-20260818T153859Z-8da515`, Stage-2c
`attempt-20260818T175018Z-0d3363`. Read archive:
`docs/checks/speech-aware-evidence-acquisition/2026-08-18-a2t-loss-decomp/` (`verdict.json`,
`report.txt`, `README.md`, `MANIFEST.sha256`). The suite ran **exactly once** (exit 0; it is
idempotence-guarded — a pre-existing `verdict.json` refuses a second run before any work happens);
the exposure row `SAEA-CHECK-a2t-loss-decomp` flips to consumed in the same commit. This is a
RE-READ: the three parent rows stay consumed and their own verdicts untouched; every input archive
was MANIFEST-verified before reading (headroom 4 files; flight archives 28/25/29 files with
`flight-receipt.json` cross-checked in place; read archives 3/3/3 with `verdict.json` verified in
place), the three-way reconciliation matched on all eight arms (computed = parent-recomputed =
archived-published), and the exact gates fired where registered: **B2 = 21, N0r = 5, C3 = 7**.

## 1. B2 verdict — the verdict carrier

**DRIFT-CONFIRMED** — **3/21** of B2's losses are DRAGGED-TO-SUPPLIED (rate 0.1429).

| branch | clause | verdict | detail |
|---|---|---|---|
| DRAG-CONFIRMED | B2 DRAGGED-TO-SUPPLIED >= 11/21 (0.5238) of B2's own losses | **not met** | dragged **3/21** (0.1429) vs floor 0.5238 — short by **8 raw drags** |
| **DRIFT-CONFIRMED** | B2 DRAGGED-TO-SUPPLIED <= 5/21 (0.2381) of B2's own losses, N0r reference shape reported side-by-side | **MET** | dragged **3/21** (0.1429) vs ceiling 0.2381 — margin **2 raw drags** (at 6 dragged the verdict would have been MIXED) |

The highlighted wrong row does **not** act by pulling selection onto itself. B2's 21 losses are
dominated by format collapse — **12/21** (6 EMPTY + 6 PARSE-FAIL) — plus **5/21** drifted to some
other wrong tool in the 152-row registry and **1/21** MULTIPLICITY (correct tool set, wrong call
count); only **3/21** went exactly to the supplied wrong tool (2.5 percent of the 120 arm samples,
inside the 12.5 percent selection-noise band Stage-2's byte-identical N0r re-fly already recorded
for this axis). Drag is nonzero but weak: N0r structurally cannot express DRAGGED-TO-SUPPLIED, so
the 3 observed drags are a class the reference arm cannot produce — reported as such, not tested.

## 2. N0r reference shape side-by-side (reporting obligation, not a statistical test)

| class | B2 (21 losses of n=120) | N0r (5 losses of n=40) |
|---|---|---|
| DRAGGED-TO-SUPPLIED | 3 | 0 (structurally undefined at zero supply) |
| DRIFTED-OTHER | 5 | 0 |
| MULTIPLICITY | 1 | 0 |
| EMPTY | 6 | 0 |
| PARSE-FAIL | 6 | 5 |

Read honestly, the two shapes are not identical: N0r's zero-supply losses are **5/5 PARSE-FAIL**,
while B2 spreads across all five classes. The registered DRIFT-CONFIRMED clause is the numeric
drag ceiling with the side-by-side as a reporting obligation (suite note 2, quoting the
preregistration's own "no statistical test at n=21 vs n=5 — stated as a shape comparison, not
inference"); the side-by-side is presented above and no compatibility statistic is computed or
implied at these n.

## 3. Per-arm five-class table (all eight arms)

| arm | n | losses | DRAGGED-TO-SUPPLIED | DRIFTED-OTHER | MULTIPLICITY | EMPTY | PARSE-FAIL |
|---|---|---|---|---|---|---|---|
| N0r | 40 | 5 | 0 | 0 | 0 | 0 | 5 |
| S1p | 120 | 8 | 0 | 0 | 1 | 0 | 7 |
| S2 | 120 | 9 | 0 | 2 | 0 | 0 | 7 |
| B1 | 120 | 16 | 0 | 0 | 1 | 2 | 13 |
| **B2** | 120 | **21** | **3** | **5** | **1** | **6** | **6** |
| C1 | 120 | 31 | 0 | 0 | 1 | 0 | 30 |
| C2 | 120 | 13 | 0 | 0 | 1 | 1 | 11 |
| C3 | 120 | 7 | 0 | 0 | 0 | 0 | 7 |

Notes on the descriptive arms. (a) DRAGGED-TO-SUPPLIED is zero everywhere outside B2 by structural
assertion, machine-checked at two levels before and during classification (the supplied tool IS the
correct tool for S1'/S2/B1/C1/C2/C3; the defense-in-depth guard never fired). (b) **MULTIPLICITY
totals 5 across the eight arms**: S1p 1, B1 1, C1 1, C2 1 — all four the SAME sample
`tier6_correction:002740` (a0 `setLighting`, predicted the correct tool set at the wrong call
count) — plus B2's 1 (`tier6_correction:000305`, `rampBrightness`); N0r, S2 and C3 carry 0. (c)
Outside B2, losses are overwhelmingly format collapse: PARSE-FAIL is 5/5 (N0r), 7/8 (S1p), 7/9
(S2), 13/16 (B1), 30/31 (C1), 11/13 (C2), 7/7 (C3); the only non-B2 drift anywhere is S2's 2. (d)
**C3's 7 losses are all PARSE-FAIL**, concentrated in tier5_needle (4) and tier6_correction (3) —
zero drift, zero empty.

## 4. Per-sample detail — B2's 21 losses

| sample_id | A0 (correct) selection | B2 arm output | class |
|---|---|---|---|
| tier1_direct:001631 | setWaterValve | (empty) | EMPTY |
| tier1_direct:002581 | resetFilterStatus | (empty) | EMPTY |
| tier2_parametric:000240 | setLightState | setLighting | DRIFTED-OTHER |
| tier2_parametric:000247 | setLightState | setLighting | DRIFTED-OTHER |
| tier2_parametric:001869 | castContent | castContent, setInputSource | DRIFTED-OTHER |
| tier2_parametric:006210 | setValetMode | (empty) | EMPTY |
| tier3_multi_intent:000924 | setGarageDoor, setTargetTemperature | (parse-fail) | PARSE-FAIL |
| tier3_multi_intent:003058 | activateRoutine, setTargetTemperature | activateRoutine, setTargetTemperature, setThermostatMode | DRIFTED-OTHER |
| tier4_implicit:001541 | setPowerState | (empty) | EMPTY |
| tier4_implicit:003312 | startWorkout | (empty) | EMPTY |
| tier4_implicit:003979 | setCabinOverheatProtection | (parse-fail) | PARSE-FAIL |
| tier5_needle:000537 | setFanMode | getApplianceStatus | **DRAGGED-TO-SUPPLIED** |
| tier5_needle:002753 | setLighting | (parse-fail) | PARSE-FAIL |
| tier6_correction:000305 | rampBrightness | rampBrightness | MULTIPLICITY |
| tier7_multiturn:000043 | setBrightness | (parse-fail) | PARSE-FAIL |
| tier7_multiturn:000348 | setLockState | setLockState_home | DRIFTED-OTHER |
| tier7_multiturn:000599 | castContent | playMedia | **DRAGGED-TO-SUPPLIED** |
| tier7_multiturn:001590 | setThermostatSchedule | getThermostatState | **DRAGGED-TO-SUPPLIED** |
| tier7_multiturn:002115 | setMirrorAngle | (empty) | EMPTY |
| tier8_intent_blending:000284 | setAdaptiveLighting, setBrightness | (parse-fail) | PARSE-FAIL |
| tier8_intent_blending:000696 | setFanSpeed, setSeatComfort, wiperServiceMode | (parse-fail) | PARSE-FAIL |

The three drags cluster where context is longest or most indirect (tier5_needle 1, tier7_multiturn
2); none of the four interpretive-weight tiers (1/2/3/8) contributed a single drag. Two of the five
drifts are the near-synonym `setLightState -> setLighting`, one is an over-generation superset
(the correct pair plus one extra tool), and one is the non-registry name `setLockState_home` — the
drift class is mostly near-miss naming, not wholesale re-selection.

## 5. Amendment history

The first execution attempt of this registered check REFUSED fail-closed at the suite's own
three-way reconciliation gate before writing any output row: the pre-amendment suite declared
losses on deduplicated distinct-tool IDENTITY while the parents' `tool_accuracy` is a name-MULTISET
comparison (the divergence surfaced by the duplicated gold tool name on headroom sample
`tier3_multi_intent:003994`), so its counts could not reconcile against the parents' published
retention. No output row was read, no verdict was produced, the idempotence guard never tripped,
and the ledger row stayed consumed=no. The repair was registered as preregistration §5 BEFORE any
read (commit `1a2daf6`, coordinator-reviewed): the loss definition was aligned to the parents' own
multiset comparator verbatim (`reproduction.toolcall_scoring.score_item` against fresh gold, never
reimplemented) and a fifth class MULTIPLICITY (correct tool SET, wrong call COUNT — structurally
neither dragged nor drifted, legal for every arm) joined the taxonomy, with the B2 verdict clauses
unchanged (a MULTIPLICITY loss weighs against DRAG-CONFIRMED exactly as EMPTY and PARSE-FAIL do).
The reconciliation gate itself — the instrument that caught the defect — was not changed, and on
this execution it passed at exactly B2=21 / N0r=5 / C3=7. One further integrity note: the executor
session was interrupted by a transient connection error immediately AFTER the read's output bundle
was written; this verdict document and the ledger flip were completed from the already-written,
MANIFEST-covered bundle with no second execution.

## 6. What this settles

**For the consumed Stage-2b MISLEAD caveat** (that row's caveat 3: retention was raw mean
`tool_accuracy` and "cannot say where B2's 21 lost selections went"): the question is now answered
mechanically, and the answer supports the MISLEAD overlay's non-fire rather than undermining it.
The highlighted wrong row's mechanism is NOT drag — only 3/21 losses landed on the supplied wrong
tool (8 short of the DRAG-CONFIRMED floor), while 12/21 collapsed to empty/parse-fail and 5/21
drifted to other, mostly near-synonym tools. The Stage-2b reading that B2's whole profile sits on
the zero-supply N0r noise band therefore survives this decomposition with one refinement: a weak
residual pull exists (3 drags, a class N0r cannot structurally express) but is bounded well inside
the selection-noise band, so "misleading by highlighted wrong supply" remains unconfirmed at this
n on both the pooled threshold (Stage-2b) and now the mechanism (this read). **For the Stage-2c
CHANNEL-REOPENED reading**: C3's 7 selection losses are 7/7 PARSE-FAIL — zero drag (undefined for
the augment form), zero drift, zero empty — so the augmenting right row does not corrupt tool
SELECTION at all; CHANNEL-REOPENED's harm (22 induced default-value substitutions) lives entirely
in the ARGUMENT channel of retained or converted calls. The two Stage-2c readings are thus cleanly
separated by axis: the reopened copy channel is a value-injection phenomenon, and the selection
axis under augmentation is as clean as any correct-tool arm flown.

SCOPE: this is a shape comparison over already-consumed discovery-split attempts (21/5/7 losses
from single, never re-flown flights); no statistical inference is performed or implied at these n,
and no confirmatory, superiority or generalization claim is licensed. The three parent rows stay
consumed with their verdicts untouched. Audio2Tool license CC BY-NC 4.0 carried on all
audio-derived results.
