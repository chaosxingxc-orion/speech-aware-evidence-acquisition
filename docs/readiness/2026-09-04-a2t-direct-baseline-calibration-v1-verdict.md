# Audio2Tool direct-baseline calibration, v1 — verdict

Run `SAEA-A2T-DIRECT-CALIBRATION-V1`, flown 2026-09-04 on the frozen 400-item Audio2Tool discovery
split (`A2T-CALIBRATION-400`, split identity hash
`11091b38ae9d53530952af632636d7e79a614350213e10c6c26583c37f85846b`). Preregistration:
`docs/readiness/2026-09-03-a2t-direct-baseline-calibration-v1-preregistration.md`. Full numbers:
`docs/checks/speech-aware-evidence-acquisition/2026-09-04-a2t-direct-calibration-400-v1/result-summary.json`.

## Verdict: NO CELL PASSES. The miss is the finding.

Preregistration section 6 asked for at least one cell reaching per-tier tool-accuracy
|delta| <= 5 pp against the paper row on tiers 1, 2, 5 and 6, with the tier rank order preserved.
**No cell meets it on any of the four tiers, and no cell preserves the tier rank order.** Section 6's
own contingency therefore applies: report which factor moved tool accuracy and by how much, and stop
mechanism work until the owner decides.

The two protocol facts this flight was built to vary do not explain the gap. Neither closes it, and
one of them makes it worse.

## What was flown

Four cells, 400 rows each, 1,600 contacts, one contact per row, all on build `04ccc72a`, Q4_K_M,
temperature 0, seed 20260803, `max_tokens` 1024, no evidence, no OBS.

| cell | Factor A (output contract) | Factor D (audio path) | arm |
|---|---|---|---|
| A0'-legacy-raw | legacy registry text | raw audio through the bf16 mmproj | `bare-core` |
| A1-native-raw | native OpenAI-format `tools` | raw audio through the bf16 mmproj | `bare-core-native-tools` |
| P0-legacy-packets | legacy registry text | mmproj-free speech-feature packets | `speech-feature-query` |
| P1-native-packets | native OpenAI-format `tools` | mmproj-free speech-feature packets | `speech-feature-query-native-tools` |

## Overall, n = 400 per cell

| cell | tool accuracy | exact match v1 | exact match v2 | slot F1 | parse rate |
|---|---:|---:|---:|---:|---:|
| A0'-legacy-raw | 51.75 | 24.00 | 31.50 | 28.99 | 89.00 |
| A1-native-raw | 46.00 | 24.25 | 29.00 | 35.40 | 87.00 |
| P0-legacy-packets | 52.75 | 23.50 | 30.75 | 29.42 | 89.25 |
| P1-native-packets | 44.00 | 22.75 | 28.00 | 34.50 | 86.75 |

Tool accuracy is the registered `a2t-toolcall` scorer's own figure, which compares expected and
predicted tool-name **multisets**. The registered scorer provides no ordered variant, so the ordered
column preregistration section 6 also asks for is **not computed** rather than invented: adding a
scoring rule after the flight would make the paper-facing number something other than the dataset's
standard scorer.

## Per-tier tool accuracy against the paper row (pp delta)

| tier | paper | A0'-legacy-raw | A1-native-raw | P0-legacy-packets | P1-native-packets |
|---|---:|---:|---:|---:|---:|
| tier1_direct | 92.4 | 64.0 (−28.4) | 50.0 (−42.4) | 60.0 (−32.4) | 50.0 (−42.4) |
| tier2_parametric | 84.6 | 68.0 (−16.6) | 70.0 (−14.6) | 66.0 (−18.6) | 70.0 (−14.6) |
| tier3_multi_intent | 74.7 | 50.0 (−24.7) | 12.0 (−62.7) | 58.0 (−16.7) | 12.0 (−62.7) |
| tier4_implicit | 33.4 | 30.0 (−3.4) | 26.0 (−7.4) | 30.0 (−3.4) | 22.0 (−11.4) |
| tier5_needle | 90.6 | 60.0 (−30.6) | 80.0 (−10.6) | 54.0 (−36.6) | 76.0 (−14.6) |
| tier6_correction | 81.5 | 60.0 (−21.5) | 70.0 (−11.5) | 60.0 (−21.5) | 62.0 (−19.5) |
| tier7_multiturn | 54.6 | 56.0 (+1.4) | 48.0 (−6.6) | 62.0 (+7.4) | 48.0 (−6.6) |
| tier8_intent_blending | 41.7 | 26.0 (−15.7) | 12.0 (−29.7) | 32.0 (−9.7) | 12.0 (−29.7) |

Summed absolute gap across all eight tiers: A0' 142.3 pp, P0 146.3 pp, A1 185.5 pp, P1 201.5 pp.
Across the four acceptance tiers alone the order differs: A1 79.1 pp, P1 91.1 pp, A0' 97.1 pp,
P0 109.1 pp. Both orderings are recorded because they disagree, and neither cell passes either way.

## The four paired contrasts, n = 400, tier-stratified, CI90, 10,000 replicates, seed 20260903

delta = right − left.

| contrast | metric | left | right | delta | saves | harms | ties | sign test p | CI90 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| A within raw (A0' → A1) | tool accuracy | 0.5175 | 0.4600 | **−0.0575** | 46 | 69 | 285 | 0.0398 | [−0.1000, −0.0150] |
| A within packets (P0 → P1) | tool accuracy | 0.5275 | 0.4400 | **−0.0875** | 44 | 79 | 277 | 0.0020 | [−0.1300, −0.0475] |
| D within legacy (A0' → P0) | tool accuracy | 0.5175 | 0.5275 | +0.0100 | 24 | 20 | 356 | 0.6516 | [−0.0175, +0.0375] |
| D within native (A1 → P1) | tool accuracy | 0.4600 | 0.4400 | −0.0200 | 11 | 19 | 370 | 0.2005 | [−0.0425, +0.0025] |
| A within raw | exact match v1 | 0.2400 | 0.2425 | +0.0025 | 26 | 25 | 349 | 1.0000 | [−0.0250, +0.0300] |
| A within packets | exact match v1 | 0.2350 | 0.2275 | −0.0075 | 26 | 29 | 345 | 0.7877 | [−0.0375, +0.0225] |
| D within legacy | exact match v1 | 0.2400 | 0.2350 | −0.0050 | 9 | 11 | 380 | 0.8238 | [−0.0225, +0.0125] |
| D within native | exact match v1 | 0.2425 | 0.2275 | −0.0150 | 5 | 11 | 384 | 0.2101 | [−0.0325, +0.0000] |
| A within raw | exact match v2 | 0.3150 | 0.2900 | −0.0250 | 28 | 38 | 334 | 0.2678 | [−0.0575, +0.0075] |
| A within packets | exact match v2 | 0.3075 | 0.2800 | −0.0275 | 30 | 41 | 329 | 0.2351 | [−0.0625, +0.0050] |
| D within legacy | exact match v2 | 0.3150 | 0.3075 | −0.0075 | 11 | 14 | 375 | 0.6900 | [−0.0275, +0.0125] |
| D within native | exact match v2 | 0.2900 | 0.2800 | −0.0100 | 8 | 12 | 380 | 0.5034 | [−0.0275, +0.0075] |

Interaction (A within packets − A within raw): tool accuracy **−0.0300**, exact match v1 −0.0100,
exact match v2 −0.0025. The interaction is a difference of two deltas on the same paired 400; no
bootstrap interval is quoted for it, because `analysis.paired` contrasts two score maps rather than
two contrasts, and computing one here would mean writing a second statistic outside the registered
one.

## Reading

- **Factor A is real, significant and NEGATIVE.** The native tool-calling contract costs 5.75 pp of
  tool accuracy on raw audio (p = 0.040, CI90 excludes zero) and 8.75 pp on packets (p = 0.0020,
  CI90 excludes zero). Section 1 framed native `tools` as the promising half of Factor A. It is the
  worse half.
- **The native contract is not uniformly worse — it trades tiers.** It gains on the tiers the paper
  scores highest (tier5 +20.0 pp raw, tier6 +10.0 pp raw) and collapses on compositional ones
  (tier3 −38.0 pp, tier8 −14.0 pp). Slot F1 rises (28.99 → 35.40 raw), so when it does call the
  right tools it fills arguments better. That is a specific, testable mechanism claim for later
  work, not a calibration result.
- **Factor D is null.** Packets versus raw audio moves tool accuracy by +1.0 pp under the legacy
  contract (p = 0.65) and −2.0 pp under the native one (p = 0.20); both CI90s straddle zero, and
  exact match is null under both scorers. **The mmproj-free packet path is behaviourally equivalent
  to raw audio for this baseline** — which is a load-bearing engineering result: every September
  mechanism experiment ran on packets, and this is the first paired evidence at n = 400 that the
  audio path is not what separates those runs from A0.
- **The gap to the paper is not the request protocol.** Both factors together move tool accuracy by
  at most 8.75 pp, while tier1 alone is 28.4–42.4 pp short. Whatever explains the paper's Table 3 is
  somewhere this flight did not look.
- **Tier1 is the anomaly.** The paper reports 92.4 tool accuracy and 92.4 exact match on tier1 —
  identical figures — while every cell here scores 50–64 tool accuracy on it. That the paper's two
  metrics coincide exactly on this one tier, and nowhere else, is worth a protocol clarification
  before any further reproduction attempt.

## Native tool calls versus text — the smoke was unrepresentative

| cell | rows | arrived as native `tool_calls` | arrived as text | native calls total |
|---|---:|---:|---:|---:|
| A0'-legacy-raw | 400 | 0 | 400 | 0 |
| A1-native-raw | 400 | **347** | 53 | 371 |
| P0-legacy-packets | 400 | 0 | 400 | 0 |
| P1-native-packets | 400 | **346** | 54 | 368 |

The four-row smoke saw zero native tool calls and suggested the model was declining the tools
interface. At 400 rows it uses it on 87 % of requests. **The smoke's reading was an artefact of four
rows** and is corrected here. The instrumentation that makes this readable was added specifically
because a canonical JSON array in a sealed row cannot otherwise be told from model-authored text.

## Throughput

| cell | wall | contacts/s | mean latency | slot occupancy | workers | prompt tok/call | completion tok/s |
|---|---:|---:|---:|---:|---:|---:|---:|
| A0'-legacy-raw | 429.4 s | 0.932 | 1.401 s | 0.653 | 2 | 13,315 | 26.88 |
| A1-native-raw | 467.0 s | 0.857 | 1.625 s | 0.696 | 2 | 13,837 | 27.13 |
| P0-legacy-packets | 274.9 s | 1.455 | 1.317 s | 0.639 | 3 | 13,313 | 29.04 |
| P1-native-packets | 341.3 s | 1.172 | 1.654 s | 0.646 | 3 | 13,835 | 28.27 |

The packet path is 56 % faster per contact than raw audio at the legacy contract (1.455 versus
0.932 contacts/s), from three slots rather than two and a lower per-request latency. The native
contract costs about 520 more prompt tokens per call, matching the prompt-fit measurement
(13,914 versus 13,236 text tokens).

## Budget

1,600 contacts of 1,608 planned and 1,700 registered; 8,638.752 speech-audio seconds of 9,000
registered; four attempts, all FINALIZED, none aborted. GPU `enforced.power.limit` held at 100.00 W
throughout with maximum SM clock 3,090 MHz; no throttling event.

## What this does and does not authorize

No cell becomes the direct baseline for mechanism work, and the umbrella `published-baselines.md`
row is filled from the closest cell explicitly marked as not accepted. Nothing here is a superiority,
generality or Stage-3 claim; the population is exposed discovery data and no knob was tuned on it.
Mechanism work stays stopped pending the owner's decision among the section 6 options: Factor C
(Q8_0), prompt-template variants, or a protocol clarification request to the paper's authors — for
which tier1's coincident metrics are the concrete question to ask.

## Addendum — three questions the verdict left open

Zero model contacts. Every figure below is read from the four sealed
`SAEA-A2T-DIRECT-CALIBRATION-V1.scores.json` / `.outputs.jsonl` artifacts of the same four
FINALIZED attempts, plus scorer-side gold (`data.audio2tool.load_expected_calls`, reduced to
call counts and tool names) and the frozen `tools_registry.csv`. Nothing was re-scored and no
scoring rule was added. Builder: `scripts/a2t_calibration_addendum.py`; machine-readable form:
the `addendum` key of `result-summary.json`.

### A1 — Correction: ordered tool accuracy *was* computed, and was sealed by this flight

The section above ("Overall, n = 400 per cell") states that the registered scorer provides no
ordered variant and that the ordered column is therefore **not computed**. That is wrong, and
is corrected here rather than rewritten above. The registered `a2t-toolcall-v2` scorer seals
**both** rules for every sample and every tier: its `tool_accuracy` field is
`AggregateScoreV2.tool_accuracy_ordered`, the expected-versus-predicted tool-name **sequence**
match, and its `tool_accuracy_multiset` field is v1's multiset rule. The flight's own scoring
job computed them; they were in the artifacts all along. The identification is asserted, not
assumed: for every cell and every tier, v2's `tool_accuracy_multiset` equals v1's
`a2t-toolcall` `tool_accuracy` exactly, which is what distinguishes v2's `tool_accuracy` as a
genuinely different, ordered rule rather than a relabelled multiset.

### A2 — Ordered versus multiset tool accuracy (ordered / multiset)

| tier | A0'-legacy-raw | A1-native-raw | P0-legacy-packets | P1-native-packets |
|---|---:|---:|---:|---:|
| tier1_direct | 64.0 / 64.0 | 50.0 / 50.0 | 60.0 / 60.0 | 50.0 / 50.0 |
| tier2_parametric | 68.0 / 68.0 | 70.0 / 70.0 | 66.0 / 66.0 | 70.0 / 70.0 |
| tier3_multi_intent | 46.0 / 50.0 | 12.0 / 12.0 | 54.0 / 58.0 | 12.0 / 12.0 |
| tier4_implicit | 30.0 / 30.0 | 26.0 / 26.0 | 30.0 / 30.0 | 22.0 / 22.0 |
| tier5_needle | 60.0 / 60.0 | 80.0 / 80.0 | 54.0 / 54.0 | 76.0 / 76.0 |
| tier6_correction | 60.0 / 60.0 | 70.0 / 70.0 | 60.0 / 60.0 | 62.0 / 62.0 |
| tier7_multiturn | 56.0 / 56.0 | 48.0 / 48.0 | 62.0 / 62.0 | 48.0 / 48.0 |
| tier8_intent_blending | 20.0 / 26.0 | 10.0 / 12.0 | 26.0 / 32.0 | 8.0 / 12.0 |
| **overall, n = 400** | 50.50 / 51.75 | 45.75 / 46.00 | 51.50 / 52.75 | 43.50 / 44.00 |

Ordering costs 1.25 pp overall on A0', 0.25 pp on A1, 1.25 pp on P0 and 0.50 pp on P1.
The penalty is **exactly zero on all six single-call tiers in all four cells** and appears only
on tier3 and tier8, the two multi-call tiers — 4.0 and 6.0 pp on both legacy cells, 0.0/2.0 pp
on A1 and 0.0/4.0 pp on P1. Ordering is therefore not a second, independent failure mode: it is
a small correction confined to the tiers that emit more than one call, and it does not change
the verdict or any cell's acceptance. Note that the native cells' apparently *smaller* order
penalty is an artefact of A3 below — a cell that emits one call cannot get the order wrong.

### A3 — Why the native cells collapse on tier3 and tier8: they emit one call instead of many

Predicted call count is the length of the call array recovered from each sealed response by
`reproduction.toolcall_scoring.parse_tool_calls_text`, the same parse both registered scorers
run; every row's parse outcome was asserted equal to the `parsed` flag the scorer sealed for
that row, and an unparsed row counts as 0 calls exactly as the scorer treats it. Gold enters
only as a length. Tier3 and tier8 are the only tiers where gold ever asks for two or more
calls, and there it always does: 50 of 50 rows in each.

Share of the 50 gold-multi-call rows on which the cell emitted **exactly one** call:

| tier | gold-multi rows | A0'-legacy-raw | A1-native-raw | P0-legacy-packets | P1-native-packets |
|---|---:|---:|---:|---:|---:|
| tier3_multi_intent | 50 | 0 % | 86 % | 2 % | 84 % |
| tier8_intent_blending | 50 | 2 % | 76 % | 0 % | 84 % |
| **both tiers** | 100 | 1 % | 81 % | 1 % | 84 % |

**This is the mechanism.** The legacy contract emits one call on 1 of 100 multi-call rows; the
native contract does it on 81 (A1) and 84 (P1) of 100. Mean calls emitted against a mean gold
of 2.40 on tier3: A0' 1.82, P0 2.02, but A1 1.14 and P1 1.16. Against a mean gold of 2.74 on
tier8: A0' 2.18, P0 2.34, but A1 1.32 and P1 1.22. The native cells are not choosing the wrong
tools on these tiers — they are **stopping after the first one**. On tier3 A1 emitted a single
call on 43 of 50 rows and never more than two; the legacy A0' emitted two on 29 and three on 11.

The proxy is sound. Per-row native counts are not sealed, only the per-cell totals in the
"Native tool calls versus text" table above, so the canonicalized array length stands in for
them — and it reconciles exactly. Reconstructed parsed calls total 372 for A1 against 371
native calls recorded, and 369 for P1 against 368, the difference in each case being exactly
one text-arriving row whose free text still parsed; reconstructed unparsed rows are 52 of 53
text-arriving rows for A1 and 53 of 54 for P1. Every natively-arriving row parsed, and its
array length is its `tool_call` count.

A second, separate native cost shows up on the single-call tiers: A1 and P1 fail to parse 11–12
of 50 tier1 rows and 16 of 50 tier7 rows, where both legacy cells fail 0–1 and 1. Those are the
rows that declined the tools interface and answered as prose. The native contract thus loses
rows two ways — under-emission where gold wants many calls, and prose fallback where it wants
one — which together account for its 5.75–8.75 pp deficit without any change in tool choice.

### A4 — Tier 1: how wrong is the wrong tool?

A tier1 row counts as wrong when its sealed v1 `tool_accuracy` is below 1.0. Rows that emitted
exactly one call against exactly one gold call are placed by where the predicted `tool_name`
sits relative to gold's in the registry taxonomy (3 domains, 28 `(domain, category)` families,
152 tools). Four buckets are reported rather than the two the question names, because the
question's own exemplar — `setLighting` versus `setLightState` — is itself same-domain but
**cross-category** (`smart_home/core_control` versus `smart_home/lighting`); scoring "same
family" as "same domain *and* category" alone would classify that exemplar as a different
family and report **zero** near-neighbour substitutions for both legacy cells. Names only.

| | A0'-legacy-raw | A1-native-raw | P0-legacy-packets | P1-native-packets |
|---|---:|---:|---:|---:|
| rows with wrong tool set (of 50) | 18 | 25 | 20 | 25 |
| — unparsed (no tool set emitted) | 0 | 11 | 0 | 12 |
| — call-count mismatch | 2 | 0 | 3 | 0 |
| — single-call substitutions | 16 | 14 | 17 | 13 |
| · same domain, same category | 0 | 3 | 0 | 2 |
| · same domain, other category | 5 | 3 | 7 | 4 |
| · other domain, same category label | 2 | 3 | 2 | 2 |
| · other domain, other category label | 9 | 5 | 8 | 5 |
| **same-domain share of substitutions** | 31 % | 43 % | 41 % | 46 % |

Read the same-domain rows together: 5 of 16 substitutions on A0', 6 of 14 on A1, 7 of 17 on P0
and 6 of 13 on P1 stay inside the correct device domain — 31–46 %. Under the strict
`(domain, category)` reading only the native cells register any at all (3 on A1, 2 on P1) and
both legacy cells register none, which is precisely why the wider split is reported.

The majority of tier1 substitutions are therefore **not** naming near-misses: they cross the
device domain, and they do so onto a functionally analogous name in the wrong one. Three
substitutions recur in **all four** cells — `getBatteryLevel` → `getBatteryStatus`
(`smart_home/diagnostics` → `smart_car/charging_energy`), `getLockState` → `getLockStatus`
(`smart_home/status` → `smart_car/status`) and `setVolume` → `adjustVolume`
(`smart_home/media` → `smart_car/media_cabin`) — and `viewRemoteCamera` → `getCameraStream`
(`smart_car/security` → `smart_home/security`) in three. The climate group behaves the same way
with a contract-dependent target: `setThermostatMode` / `setTargetTemperature` /
`setThermostatSchedule` → `setClimate` on both legacy cells, `setThermostatMode` →
`setZoneTemperature` on both native ones. These are stable properties of the
registry-plus-prompt, not sampling noise. The failure is **device-domain disambiguation** across
a 152-tool registry carrying three near-duplicate capability sets, not tool naming.

Inside `smart_home` the residual confusion is the `core_control` versus `lighting` boundary, and
it too is contract-dependent in the same direction: the legacy cells collapse `setBrightness` /
`setColor` / `setColorTemperature` / `setGroupLightState` onto the generic `setLighting`, while
the native cells collapse them — and `setLighting` itself — onto `setLightState`. The
question's exemplar is thus real and directional, but it sits inside the same-domain bucket,
which is 5 of 16 and 7 of 17 substitutions on the legacy cells and 6 of 14 and 6 of 13 on the
native ones — a minority of tier1's misses either way.

None of this changes the verdict. It does sharpen the tier1 clarification question the section
above recommends: the paper's 92.4 requires resolving both the device domain and the
`core_control`/`lighting` boundary from speech alone, and it is worth asking whether the
published protocol scopes the candidate tool set per utterance rather than offering all 152.

## Correction (2026-09-04, appended after the official-protocol replication; zero contacts)

The official-protocol replication flight (`docs/readiness/2026-09-04-a2t-official-protocol-replication-v1-verdict.md`)
found that the flight path ignored a baseline fragment's `task_instruction_template` field: the adapter's built-in
`_INSTRUCTION_TEMPLATE` ("You control tools. Available tools:" + the rendered registry + "Respond with ONLY a JSON
array of tool calls, e.g. [{"name": "x", "arguments": {}}].") was rendered regardless of the fragment. For this
calibration that changes no number and no conclusion: preregistration section 3 already names
`rails/adapters/audio2tool.py::_INSTRUCTION_TEMPLATE` as the instruction of both legacy cells, byte-identical to what
A0 sent, and the prompt-fit receipt measured the rendered request itself (13,236 registry tokens). Two statements
are corrected:

- Preregistration section 3 says `configs/probes/r1_audio2tool_direct.txt` "is its source text". It is not: that
  probe file carries a longer instruction ("You are a voice assistant that controls devices by calling tools ...")
  that no sealed cell ever sent. The flown text is `_INSTRUCTION_TEMPLATE` alone.
- Baseline fragments `a2t-direct-calibration.json` and `a2t-direct-packets.json` declare
  `task_instruction_template: probes/r1_audio2tool_direct.txt`; that field was inert. Since commit 46ce43b5 the
  field is honoured only when a fragment also sets `task_instruction_template_active: true`, so every sealed
  calibration manifest remains reproducible byte for byte.

The four sealed manifests, their hashes, the per-tier tables and the Factor A / Factor D contrasts above stand as
written.
