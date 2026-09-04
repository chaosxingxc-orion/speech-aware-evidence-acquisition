# G7 V2 fixed16 post-score paired result analysis

## Decision

Retain G7 V2 as a complete engineering and trajectory-generation baseline, not as an
end-task improvement over direct M0. The sealed run completed all 480 contacts, produced valid
OBS records on 16/16 rows, and produced parseable final JSON on 16/16 rows. It therefore exposes
live OBS, ORG, SUPPLY, and USE state suitable for designing a later control policy. It does not
show positive paired end-task information gain: against the correct same-row G1 M0 comparator,
G7 has no tool or exact saves and regresses every aggregate end-task metric.

The `>0.90` target is a target for a later training-free reward-guided controller after policy
fitting and disjoint validation. It is not an admission requirement for this engineering
baseline. This analysis opens no disjoint40, fresh88, test, future-turn, or previously closed
surface, launches no model or scorer, and changes no sealed run artifact.

## Comparator correction

The previously cited M0 result of 6/16 tool correct, 3/16 exact, and 0.285714 slot-F1 belongs to
the **G6 roster**, as recorded in the immutable G6 result analysis. G6 and G7 have different
fixed16 identities, so that number is not a paired G7 comparator.

The authoritative G7 comparison filters the frozen G1 M0 output, SHA-256
`dea60ff1e63fd2ef11c93edf8808217062fea3f0565ed5b60f136264bc6a9467`, to the exact 16 identities
in the G7 run manifest. Under the unchanged `a2t-scorer-v1` and `a2t-gold-v1` semantics, this
same-row M0 slice is 11/16 tool correct, 4/16 exact, 18 slot true positives over 30 expected and
42 predicted slots, and 16/16 parsed.

## Authoritative paired result

| System | Tool correct | Exact | Slot precision | Slot recall | Slot F1 | Parsed |
|---|---:|---:|---:|---:|---:|---:|
| Frozen G1 M0, exact G7 IDs | 11/16 | 4/16 | 0.428571 | 0.600000 | 0.500000 | 16/16 |
| G7 V2 | 7/16 | 3/16 | 0.358974 | 0.466667 | 0.405797 | 16/16 |

Paired outcomes are:

- Tool accuracy: 0 saves, 4 harms, 7 both correct, and 5 both wrong.
- Exact match: 0 saves, 1 harm, 3 both correct, and 12 both wrong.
- Row-level slot-F1: 1 win, 4 losses, and 11 ties.

The G7 exact rows are a strict subset of the M0 exact rows. The sole exact harm is
`tier2_parametric:005678`. Tool harms are `tier1_direct:001432`,
`tier2_parametric:000240`, `tier3_multi_intent:002560`, and `tier5_needle:000060`.
The sole row-level slot-F1 win is `tier5_needle:002753`, where G7 reduces predicted slots while
retaining one true positive; it does not become exact.

| Sample | M0 tool / exact / slot-F1 | G7 tool / exact / slot-F1 | Earliest visible issue |
|---|---:|---:|---|
| `tier1_direct:001432` | 1 / 0 / 0.000000 | 0 / 0 / 0.000000 | RESOLVE ignores supported `setApplianceMode`, selects uncertain `startCleaning`, emits illegal key `action`, and copies placeholder `evidence g7`. |
| `tier1_direct:001631` | 1 / 0 / 0.000000 | 1 / 0 / 0.000000 | Correct tool, but RESOLVE invents `irrigation_controller` and arguments where scorer gold is empty. |
| `tier2_parametric:000240` | 1 / 0 / 0.500000 | 0 / 0 / 0.000000 | RESOLVE ignores supported `setLightState` for uncertain sibling `setLighting`. |
| `tier2_parametric:005678` | 1 / 1 / 1.000000 | 1 / 0 / 0.666667 | USE loses the observed one-time repeat value and emits `repeat=[]`. |
| `tier3_multi_intent:002560` | 1 / 0 / 0.400000 | 0 / 0 / 0.400000 | All gold tools are supported, but RESOLVE substitutes `setLightState` for `setLighting` and adds unsupported device IDs. |
| `tier3_multi_intent:003982` | 0 / 0 / 0.800000 | 0 / 0 / 0.800000 | Gold `setAirQualityMode` stays uncertain while supported semantic sibling `setRecirculation` is selected. |
| `tier4_implicit:001409` | 0 / 0 / 0.000000 | 0 / 0 / 0.000000 | Gold `setApplianceMode` stays uncertain while non-gold `getApplianceStatus` is supported and selected. |
| `tier4_implicit:003979` | 1 / 0 / 0.500000 | 1 / 0 / 0.500000 | Correct tool, but `maxTemp=80` is neither speech-bound nor within the registered range. |
| `tier5_needle:000060` | 1 / 0 / 0.500000 | 0 / 0 / 0.000000 | Gold `setLighting` and non-gold `setAmbientLighting` are both supported; RESOLVE selects the wrong sibling. |
| `tier5_needle:002753` | 1 / 0 / 0.250000 | 1 / 0 / 0.333333 | Sole slot win; the device ID remains wrong and expected null-valued slots are absent. |
| `tier6_correction:003450` | 1 / 1 / 1.000000 | 1 / 1 / 1.000000 | Both exact. |
| `tier6_correction:003900` | 0 / 0 / 0.444444 | 0 / 0 / 0.444444 | OBS preserves both the superseded 1:35 alarm and corrected 1:40 alarm, causing duplicate calls. |
| `tier7_multiturn:000274` | 0 / 0 / 0.000000 | 0 / 0 / 0.000000 | Final-turn-only speech loses the earlier air-quality intent; `getSensorState` replaces `getAirQuality`. |
| `tier7_multiturn:002099` | 1 / 1 / 0.000000 | 1 / 1 / 0.000000 | Both exact; the scorer defines zero-slot call F1 as zero. |
| `tier8_intent_blending:000441` | 1 / 1 / 1.000000 | 1 / 1 / 1.000000 | Both exact. |
| `tier8_intent_blending:000673` | 0 / 0 / 0.600000 | 0 / 0 / 0.500000 | OBS hallucinates dog mode and regenerative braking and omits toll permission, producing extra calls and incomplete route arguments. |

Tool accuracy regresses by one row in each of tiers 1, 2, 3, and 5 and ties in the other tiers.
Exact match regresses only in tier 2. Slot micro-F1 regresses in tiers 2, 4, 5, and 8 and does
not improve in any tier.

## Macro-router ceiling

A post-hoc gold oracle choosing between the already-recorded M0 and G7 terminal response on each
row reaches only:

- 11/16 tool correct;
- 4/16 exact;
- slot precision 0.450000, recall 0.600000, and F1 0.514286, from 18 true positives over
  30 expected and 40 predicted slots.

For exact-first reward, the oracle always retains M0 because G7 has no exact save. A VW-style
macro-action policy whose complete action set is `STOP_M0` versus `USE_G7` therefore cannot
approach 0.90, regardless of routing quality. The one slot benefit does not alter the exact or
tool ceiling.

## Intermediate signal versus end-task information gain

G7 does create intermediate signal that G6's strict free-form SCAN path failed to preserve:

- 382/448 family responses are strict-valid and 403/448 are tolerant-valid;
- 1,656/2,432 tool assessments are explicit and the controller normalizes all 2,432 tool states;
- explicit statuses contain 96 support, 68 contradict, and 1,492 uncertain decisions;
- post-hoc, 16/21 gold tool instances are supported, 5 are uncertain, and none is contradicted;
- 11/16 rows support every gold tool, and all final responses remain nonempty and parseable.

This is useful state and action-support instrumentation. It is not end-task information gain.
Eighty of the 96 support labels name non-gold tools, only 6 of the 11 rows with complete gold
support finish tool-correct, and G7 has no tool or exact save over same-row M0.

The descriptive G6-to-G7 progression is not causal: the rosters differ, and construction
examples, OBS, repeated speech access, tolerant parsing, normalization, and all-tool RESOLVE
supply changed together. The same-row M0-to-G7 comparison estimates only the effect of the whole
G7 package on these rows. Post-hoc associations between OBS or evidence states and errors do not
identify component effects.

## Bottleneck precedence

Final JSON parsing is not the primary bottleneck. All 16 final responses parse, although all 16
violate the no-fence instruction, and one contains a prohibited placeholder.

The earliest visible error classes are approximately:

1. OBS/history/correction defects decisively damage about three rows: the duplicate corrected
   alarm, the missing earlier multiturn intent, and the hallucinated blended intents.
2. EVIDENCE and ORG retain broad but weakly discriminative sibling support: only 16/96 support
   labels correspond to gold tool instances.
3. RESOLVE and USE lose multiple rows even when the correct tool is explicitly supported; four
   named tool harms are visible in this condition.
4. Argument binding remains downstream-limiting: only 3 of the 7 tool-correct G7 rows are exact.

These counts are diagnostic precedence estimates, not causal decompositions.

## What the existing traces identify

For a macro-action contextual bandit, the same-row artifacts expose both terminal outcomes for
the two observed actions, M0 and G7. They therefore identify their paired rewards and the exact
two-action oracle ceiling above. They do not expose a useful positive exact-reward region for the
G7 action.

For a sequential action-dependent-feature controller, the G7 trace contains only one
deterministic behavior trajectory per row:

`OBS -> all 28 EVIDENCE families -> all-tool RESOLVE`

The trace establishes state liveness and records observation, family validity, assessment
coverage, support conflicts, candidate width, argument skeletons, and budget. It does not contain
counterfactual outcomes or propensities for skipping, reordering, deepening OBS, narrowing
SUPPLY, verifying values, backtracking, or stopping early. Consequently it cannot identify
sequential `Q(state, action)` values, stage credit, or an unbiased off-policy estimate for a
sequential ADF policy. A later training-free controller experiment must prospectively log
one-shot randomized or exhaustive action branches before using post-hoc discovery rewards.

## Audit inputs

| Input | Absolute path | SHA-256 |
|---|---|---|
| G7 run manifest | `/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-A2T-G7-MULTIMODAL-EXHAUSTIVE-EXAMPLE-GROUND-FIXED16-V2/flight-20260903T000610Z/g7/SAEA-A2T-G7-MULTIMODAL-EXHAUSTIVE-EXAMPLE-GROUND-FIXED16-V2.run-manifest.json` | `e6a86bfe402e49aa7954e0524946e3b527087e0028bc46c98c7b19c873816739` |
| G7 final outputs | `/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-A2T-G7-MULTIMODAL-EXHAUSTIVE-EXAMPLE-GROUND-FIXED16-V2/flight-20260903T000610Z/g7/SAEA-A2T-G7-MULTIMODAL-EXHAUSTIVE-EXAMPLE-GROUND-FIXED16-V2.outputs.jsonl` | `9c2c618c42fb601bce4a22b90f41a6ca3893378fd737fcb6c021b14b62652ec0` |
| G7 assessment states | `/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-A2T-G7-MULTIMODAL-EXHAUSTIVE-EXAMPLE-GROUND-FIXED16-V2/flight-20260903T000610Z/g7/g7-assessment-states.jsonl` | `8a310d0bdc1c67dd4cb7d314854667c319d4991835714c3b9fb78663e841f6f6` |
| G7 agent trace | `/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-A2T-G7-MULTIMODAL-EXHAUSTIVE-EXAMPLE-GROUND-FIXED16-V2/flight-20260903T000610Z/g7/agent-trace/SAEA-A2T-G7-MULTIMODAL-EXHAUSTIVE-EXAMPLE-GROUND-FIXED16-V2.trace.jsonl` | `f66a253b6f2ebbefdffb479e5f114f35f4d797a3826f94b43d0d463b9ede9000` |
| G7 agent trace manifest | `/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-A2T-G7-MULTIMODAL-EXHAUSTIVE-EXAMPLE-GROUND-FIXED16-V2/flight-20260903T000610Z/g7/agent-trace/SAEA-A2T-G7-MULTIMODAL-EXHAUSTIVE-EXAMPLE-GROUND-FIXED16-V2.trace-manifest.json` | `654505a2a2876067e7135e242129f44f986f55d4a172abfbaf58488ad4b212e8` |
| Frozen G1 M0 outputs | `/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-A2T-G1/attempt-20260825T100735Z-a2tg1m0/arm1-m0-outputs.jsonl` | `dea60ff1e63fd2ef11c93edf8808217062fea3f0565ed5b60f136264bc6a9467` |
| G7 identity receipt | `/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/docs/receipts/a2t/A2T-G7-EXAMPLE-FIXED16.json` | `8be941c6e82527f9b63cd1f9ea09449f6cabbf175e7b2401642de455edc975c3` |
| G7 structured ground | `/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/knowledge/audio2tool/g7-construction-example-ground-v1/ground.json` | `f890e2a0975c4517e1909ecb2dee04d38eeaa05c4f0d9830b41ac634dbc9d830` |
| Scorer semantics | `/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/src/speech_aware_evidence_acquisition/reproduction/toolcall_scoring.py` | `a2b1380f408a29af0a31cb3a0d8d0730fa8ec07e64ec45d14a7e258595ac70a0` |
| Gold parser | `/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/src/speech_aware_evidence_acquisition/reproduction/toolcall_gold.py` | `29e0f2d56a28ce975508ed2e0cfbf2eade7c64907c60d0027909ebcb74da1209` |
| Prior G6 result analysis | `/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/docs/checks/speech-aware-evidence-acquisition/2026-09-02-a2t-g6-result-analysis/README.md` | `72aabf618e555af8d91d9eccf21400f79e6a9aa397d6cb028850d5dee248f601` |

The G7 manifest retains its grandfathered `UNVERIFIED` legality declaration because its
evidence-bearing arm does not declare the later provenance fields. This analysis does not repair
or reinterpret that declaration.

## Correction under a2t-scorer-v2 (2026-09-03)

Zero-contact offline re-score of the same sealed `g7` outputs.jsonl (16/16 rows) and the shared
`A2T-G1-104` M0 baseline (filtered to these same 16 sample ids), v1 identity confirmed to 4 decimals
overall, under the registered `a2t-scorer-v2` (`analysis.a2t_v2_rescore`,
`docs/checks/speech-aware-evidence-acquisition/2026-09-03-a2t-scorer-v2-rescore/`).

| System | v1 exact | v1 tool | v2 exact | v2 tool (ordered) | v2 tool (multiset) | v2 slot F1 | v1 slot F1 | parse rate |
|---|---|---|---|---|---|---|---|---|
| g7_v2 | 0.1875 | 0.4375 | 0.1875 | 0.3750 | 0.4375 | 0.4375 | 0.4058 | 1.0000 |
| m0_same_rows | 0.2500 | 0.6875 | 0.3750 | 0.6250 | 0.6875 | -- | -- | -- |

Paired contrast, g7 vs. m0 (same 16 ids; v1 and v2, CI90, 10,000 replicates, tier-stratified):

| metric | delta | saves | harms | ties | CI90 |
|---|---|---|---|---|---|
| v1 exact | -0.0625 | 0 | 1 | 15 | [-0.1250, 0.0000] |
| v2 exact | -0.1875 | 0 | 3 | 13 | [-0.2500, -0.1250] |
| v1 tool | -0.2500 | 0 | 4 | 12 | [-0.3750, -0.1250] |
| v2 tool (multiset) | -0.2500 | 0 | 4 | 12 | [-0.3750, -0.1250] |
| v2 tool (ordered) | -0.2500 | 0 | 4 | 12 | [-0.3750, -0.1250] |

g7's exact-match deficit versus m0 widens under v2 (v1 CI90 [-0.1250, 0.0000], touching zero -> v2 CI90
[-0.2500, -0.1250], clearly excluding zero) because v2's registry-default/coercion rules resolve more
of m0's near-misses than g7's; tool accuracy is unchanged (ordered equals multiset for both systems
on this roster, so no `TOOL_ORDER_ONLY` row is present). This is a mechanism diagnostic, not a
promotion decision; the reading that g7's exhaustive-example approach underperforms m0 on this
same-16 comparison holds under v2 as well, with a somewhat stronger (not weaker) exact-match gap.
