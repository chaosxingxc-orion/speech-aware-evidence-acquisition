# Audio2Tool and Earnings21 + ConEC gap diagnosis from sealed rows (owner decision 163, analysis track): DESCRIPTIVE

Written 2026-09-27 by the analysis agent (Claude Opus 5.5, worktree `/home/chao/saea-worktrees/fable-xcarrier`, branch
`fable/xcarrier`) for the analysis track of owner decision 163: for the two carriers other than SLURP, where do the
current gains and harms come from, where does the raw knowledge fall short, and which capability must be added.
Model-free: exposure row `SAEA-XC-MF-A2T-EARNINGS-GAP-DIAGNOSIS-V1` was registered before any new number was computed
(in the commit 'research: register the owner-decision-163 A2T and Earnings gap diagnosis row before reading', which precedes this note on branch fable/xcarrier; first written as a32c34a2 before the rebase onto master); zero model, tokenizer, encoder, scorer, server, GPU and network contacts. Reference annotations
and transcripts were read offline through sealed first-score alignments and the 2026-09-15 attribution artifacts only;
this note carries ids, tier / domain / category / tool / key / entity-type NAMES, counts and rates, never a transcript,
reference text, argument value or model output. Development rows only (owner decisions 28 and 86): every table below is
descriptive, no row is a verdict, and every "ceiling" is an arithmetic upper bound on sealed rows, never a prediction.

| artifact | sha256 |
| --- | --- |
| `scripts/analysis/a2t_gap_diagnosis.py` | `b70d48d22a4b648a369b0b41ce3315ba94131f75b134013813dc99fa193950d5` |
| `scripts/analysis/e21_gap_diagnosis.py` | `175dcad223c77bf3f209e22b43b5e5ef668f0743f012cfeeb091a880d05d732d` |
| `analysis/SAEA-XC-MF-A2T-EARNINGS-GAP-DIAGNOSIS-V1/a2t-gap-diagnosis.json` | `2fb01bbbf0e5321623bc6a489427f98b08c355288f4fef0b275d703922e8e5f0` |
| `analysis/SAEA-XC-MF-A2T-EARNINGS-GAP-DIAGNOSIS-V1/e21-gap-diagnosis.json` | `026a8105cd8da329b87d94ea43d7e1f4a753ca17afbfb36ca8323a2a22a9d464` |
| A2T-AA null used for the paired-400 re-read (`analysis/SAEA-A2T-STAGE3-AA-PAIRED-400-READ-V1/null.json`) | `2c7fce43875a30c4a58bb9ad9a27ff898b8cca330492c9d214c7646d4e8a547a` |

---

## Part A. Audio2Tool: the dual-store system against the direct baseline

**Rows.** Direct `SAEA-A2T-NATIVE-ROLE-DIRECT-UNION4000-V1` and the dual-store system
`SAEA-A2T-NATIVE-ROLE-DUAL-STORE-UNION4000-RECOVERY-V1` on the sealed union-4000 (500 per tier), joined per row to the
2026-09-15 ordered-action and primary-parameter attribution rows and to the public tool registry (152 tools, 28
`domain/category` families). The joins reproduce the sealed totals: direct 62.025 % tool / 18.500 % exact, system
58.425 % / 22.550 %, candidate union coverage of the official primary tool 2,882 of 4,000 (72.05 %). Earlier cells read
beside, not re-derived: ORG-1 domain-grouped registry HARMFUL (-3.23 pp tool accuracy; cross-domain twin misses
621 -> 521 but same-domain twin misses 898 -> 1,118), KC-A1 inline contrast notes NULL (+0.42 pp [-0.12, +0.97]; the
content leg +0.17), EVO-A1's capacity wall (the construction pool cannot reward the dominant lighting confusion).

### A1. Where the system gains and where it loses, by tier

Official protocol (primary call). Paper columns: arXiv:2604.22821 Table 3, Qwen3-Omni-30B, and the Qwen-2.5-Omni-7B
floor (tool accuracy), published references rather than matched comparators.

| tier | direct tool | system tool | delta | tool saves / harms | direct exact | system exact | delta | exact saves / harms | candidate coverage | paper tool / exact | Qwen2.5 floor |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- | ---: | --- | ---: |
| tier1_direct | 67.2 | 61.4 | -5.8 | 27 / 56 | 16.0 | 9.8 | -6.2 | 4 / 35 | 79.8 | 92.4 / 92.4 | 79.5 |
| tier2_parametric | 78.4 | 75.8 | -2.6 | 31 / 44 | 28.2 | 35.2 | +7.0 | 68 / 33 | 85.6 | 84.6 / 15.6 | 80.6 |
| tier3_multi_intent | 67.6 | 64.8 | -2.8 | 33 / 47 | 20.4 | 27.4 | +7.0 | 45 / 10 | 79.8 | 74.7 / 28.6 | 50.2 |
| tier4_implicit | 29.0 | 24.4 | -4.6 | 34 / 57 | 6.4 | 9.8 | +3.4 | 23 / 6 | 34.2 | 33.4 / 11.3 | 22.4 |
| tier5_needle | 80.4 | 74.4 | -6.0 | 15 / 45 | 21.8 | 27.8 | +6.0 | 48 / 18 | 84.0 | 90.6 / 36.0 | 74.1 |
| tier6_correction | 76.0 | 72.8 | -3.2 | 37 / 53 | 24.0 | 29.0 | +5.0 | 54 / 29 | 84.6 | 81.5 / 24.8 | 68.3 |
| tier7_multiturn | 49.0 | 45.4 | -3.6 | 36 / 54 | 10.6 | 12.4 | +1.8 | 17 / 8 | 65.0 | 54.6 / 16.3 | 48.2 |
| tier8_intent_blending | 48.6 | 48.4 | -0.2 | 35 / 36 | 20.6 | 29.0 | +8.4 | 54 / 12 | 63.4 | 41.7 / 12.4 | 36.5 |
| all (equal-tier = natural) | 62.025 | 58.425 | -3.600 | 248 / 392 | 18.500 | 22.550 | +4.050 | 313 / 151 | 72.05 | 69.19 / 29.68 (means) | 57.48 (mean) |

By domain: wearables gains most on exact (+12.4) and loses most on tool (-5.7); smart_home, 2,792 rows, gains only
+1.2 exact at -3.0 tool; smart_car +6.3 / -3.4.

**Reading.** The gain is on the ARGUMENTS of calls whose tool was already right; the loss is on TOOL SELECTION, and
the tool loss is concentrated where Perception's candidate union misses the gold tool:

| primary-tool flow | gold in candidate union | gold not in union |
| --- | ---: | ---: |
| tool harms (direct right, system wrong) | 177 | 215 |
| tool saves (direct wrong, system right) | 242 | 6 |

### A2. By error kind (exclusive, primary call, official protocol)

| error kind | direct rows | system rows | change |
| --- | ---: | ---: | ---: |
| exact | 740 | 902 | +162 |
| tool right, wrong VALUE only | 1,054 | 807 | -247 |
| tool right, EXTRA key only (argument name) | 481 | 459 | -22 |
| tool right, MISSING key only (argument name) | 85 | 61 | -24 |
| tool right, missing and extra key | 13 | 7 | -6 |
| tool right, key AND value errors | 108 | 101 | -7 |
| WRONG TOOL, same registry family | 204 | 262 | +58 |
| WRONG TOOL, other family | 1,262 | 1,383 | +121 |
| wrong tool, name not in the registry | 25 | 2 | -23 |
| FORMAT (official parse failure) | 28 | 16 | -12 |

Where the 313 exact saves come from (the direct row's kind): value-only 169, missing-key 42, extra-key 24, key and value
5, wrong tool 72 (57 other family, 12 same family, 3 unregistered), format 1. Where the 151 exact harms go (the
system row's kind): wrong tool 75 (55 other family, 19 same family, 1 unregistered), value-only 38, extra-key 36,
missing-key 2. **The system's parameter-meaning store buys value grounding (1,054 -> 807 value-only rows); its
activation store costs tool selection.**

Argument key NAMES behind the remaining system errors (tool-correct rows): wrong values concentrate on `deviceId`
(688 wrong-value keys; next `time` 41, `schedule` 23, `zones` 23, `query` 22); extra keys concentrate on `deviceId`
(316 of 660), and **389 of the 495 extra-key rows have an EMPTY reference parameter set** (the tier-1 pattern: the
paper's tier 1 is argument-free, so an otherwise correct call that names a device fails exact); 153 of the 660 extra
keys equal the tool's declared default. Missing keys: `deviceId` 54, `goal` 16, `repeat` 11.

Multi-call structure (repo parse, all calls; the official metric reads only the first call):

| arm | multi-reference rows (996): count equal / missing call / extra call | single-reference rows (3,004): equal / missing / extra |
| --- | --- | --- |
| direct | 512 / 416 / 68 | 2,959 / 27 / 18 |
| system | 653 / 246 / 97 | 2,884 / 15 / 105 |

The system enumerates more of the requested calls (missing calls 416 -> 246, carried by tier 3 191 -> 122 and tier 8
225 -> 124) but emits more surplus calls (single-reference extra calls 18 -> 105; tier 6 correction 18 -> 64 extra
calls: superseded requests are executed instead of dropped).

### A3. By function family (the gold primary tool's registry `domain/category`)

| family | rows | direct -> system tool | delta | saves / harms | direct -> system exact | delta | candidate coverage |
| --- | ---: | --- | ---: | --- | --- | ---: | ---: |
| wearables/health_activity | 418 | 78.9 -> 72.5 | -6.5 | 6 / 33 | 28.5 -> 51.7 | +23.2 | 82.8 |
| smart_home/climate | 333 | 63.1 -> 59.5 | -3.6 | 21 / 33 | 3.9 -> 3.0 | -0.9 | 74.5 |
| smart_home/core_control | 333 | 30.9 -> 25.2 | -5.7 | 21 / 40 | 15.9 -> 20.1 | +4.2 | 48.0 |
| smart_home/lighting | 332 | 43.4 -> 53.3 | +9.9 | 54 / 21 | 2.1 -> 3.3 | +1.2 | 73.2 |
| smart_home/maintenance | 320 | 65.6 -> 60.3 | -5.3 | 18 / 35 | 17.5 -> 18.8 | +1.2 | 72.5 |
| wearables/device_state | 254 | 82.3 -> 76.0 | -6.3 | 2 / 18 | 41.7 -> 44.5 | +2.8 | 86.6 |
| smart_home/media | 236 | 65.3 -> 59.3 | -5.9 | 9 / 23 | 3.0 -> 4.7 | +1.7 | 71.6 |
| smart_home/status | 226 | 58.0 -> 45.6 | -12.4 | 14 / 42 | 17.7 -> 11.1 | -6.6 | 61.5 |
| smart_home/diagnostics | 213 | 57.7 -> 58.7 | +0.9 | 18 / 16 | 11.3 -> 11.7 | +0.5 | 76.1 |
| wearables/system_connectivity | 185 | 75.7 -> 72.4 | -3.2 | 5 / 11 | 51.9 -> 53.0 | +1.1 | 82.2 |
| smart_home/security | 184 | 57.1 -> 56.0 | -1.1 | 19 / 21 | 5.4 -> 7.1 | +1.6 | 68.5 |
| smart_home/appliances | 177 | 68.4 -> 65.0 | -3.4 | 16 / 22 | 2.3 -> 1.1 | -1.1 | 70.1 |
| smart_home/energy | 164 | 72.6 -> 65.2 | -7.3 | 8 / 20 | 3.7 -> 1.2 | -2.4 | 78.0 |
| smart_home/automation | 154 | 65.6 -> 60.4 | -5.2 | 8 / 16 | 20.8 -> 36.4 | +15.6 | 67.5 |
| smart_car/media_cabin | 85 | 36.5 -> 28.2 | -8.2 | 3 / 10 | 7.1 -> 8.2 | +1.2 | 31.8 |
| smart_car/body_control | 66 | 57.6 -> 54.5 | -3.0 | 4 / 6 | 15.2 -> 34.8 | +19.7 | 69.7 |
| smart_car/climate_environment | 51 | 56.9 -> 58.8 | +2.0 | 4 / 3 | 21.6 -> 43.1 | +21.6 | 78.4 |
| smart_car/charging_energy | 47 | 72.3 -> 61.7 | -10.6 | 1 / 6 | 66.0 -> 55.3 | -10.6 | 80.9 |
| smart_home/device_finding | 40 | 25.0 -> 35.0 | +10.0 | 6 / 2 | 25.0 -> 35.0 | +10.0 | 85.0 |
| smart_car/driving_dynamics | 33 | 84.8 -> 81.8 | -3.0 | 1 / 2 | 51.5 -> 57.6 | +6.1 | 84.8 |
| smart_car/maintenance | 29 | 79.3 -> 82.8 | +3.4 | 2 / 1 | 62.1 -> 58.6 | -3.4 | 82.8 |
| smart_car/navigation | 27 | 66.7 -> 66.7 | 0.0 | 3 / 3 | 18.5 -> 29.6 | +11.1 | 70.4 |
| smart_car/status | 27 | 88.9 -> 85.2 | -3.7 | 0 / 1 | 74.1 -> 81.5 | +7.4 | 85.2 |
| smart_car/diagnostics | 23 | 82.6 -> 73.9 | -8.7 | 1 / 3 | 82.6 -> 73.9 | -8.7 | 87.0 |
| smart_car/core_control | 18 | 61.1 -> 66.7 | +5.6 | 2 / 1 | 50.0 -> 50.0 | 0.0 | 72.2 |
| smart_car/security | 14 | 57.1 -> 57.1 | 0.0 | 2 / 2 | 42.9 -> 35.7 | -7.1 | 64.3 |
| smart_car/novelty | 9 | 66.7 -> 55.6 | -11.1 | 0 / 1 | 55.6 -> 44.4 | -11.1 | 66.7 |
| smart_car/fine_grained | 2 | 100.0 -> 100.0 | 0.0 | 0 / 0 | 0.0 -> 0.0 | 0.0 | 100.0 |

Three families carry the story. **smart_home/lighting** is the only large family where the system wins tool accuracy
(+9.9, 54 saves): the dual store resolves part of the lighting confusion the construction pool could not reward.
**smart_home/status** (-12.4) and **smart_home/core_control** (-5.7, coverage 48 %) are where Perception most often
proposes the wrong object. **Exact gains** are carried by families with argument-rich calls (health_activity +23.2,
body_control +19.7, climate_environment +21.6, automation +15.6) -- the parameter-meaning store at work. Families
whose exact rate stays near zero on both arms (climate, media, appliances, energy, security, lighting: 1-7 %) are
where value grounding is still missing, which is the `deviceId` result in A2.

### A4. The 28 % Perception misses: what they are

1,117 of 3,999 available candidate states omit the official primary tool (1 state unavailable).

| cut | counts |
| --- | --- |
| by tier | tier4 329, tier8 183, tier7 174, tier1 101, tier3 101, tier5 80, tier6 77, tier2 72 |
| by domain | smart_home 900 (32.2 % of its rows), wearables 138 (16.1 %), smart_car 79 (22.5 %) |
| reference class | single-call 835, multi-call 282 |
| candidate union shape | empty 31; contains a tool of the gold's family 266; only other families 820, of which only other DOMAINS 308 |
| union width (misses / covered) | 1: 295 / 1,193; 2: 359 / 915; 3: 177 / 466; 4: 133 / 198; 5: 23 / 45; 6+: 99 / 65 |
| what happened to the answer | direct had the tool right on 239 of them; the system on 30; direct exact 44, system exact 4 |
| gold tools most often missed | setLighting 110, controlPlayback 51, rebootDevice 46, getLockState 37, setGroupLightState 37, setSecurityMode 37, setApplianceMode 30, updateFirmware 30, setFanMode 26, activateScene 25 |
| most frequent miss -> system answer | setLighting -> setLightState 42; rebootDevice -> calibrateCameras 18; setColor -> setAmbientLighting 17; updateFirmware -> calibrateCameras 16; setLighting -> setAmbientLighting 15; setApplianceMode -> startCleaning 14 |

**What the misses are.** Not a width problem (misses are not narrower than covered rows; most have 2+ candidates) and
not mostly a near-duplicate problem (only 14.4 % of the misses' wrong answers are near-name twins of the gold, against
40.7 % among covered-but-wrong rows). They are **wrong-object proposals**: 820 of 1,117 unions hold no tool of the
gold's family and 308 hold no tool of the gold's DOMAIN at all. The implicit tier (4) alone holds 329 misses (coverage
34.2 %): requests that name a goal, not a device, and a Perception note that has no knowledge mapping goals to
functions. **The damage is avoidable without new knowledge**: on 239 miss rows the bare core already answered
correctly, and the system's Solver followed the wrong shortlist (30 correct escapes only).

Near-name twins (tool NAMES that share an object token once verbs and the tags diag/home/car/state/status/mode are
removed; 104 such pairs in the 152-tool registry):

| error set | errors | near-name twin | share |
| --- | ---: | ---: | ---: |
| direct wrong-tool rows | 1,491 | 419 | 28.1 % |
| system wrong-tool rows | 1,647 | 391 | 23.7 % |
| system NEW tool errors (direct right) | 392 | 98 | 25.0 % |
| system errors with the gold IN the union (575) | 575 | 234 | 40.7 % |
| system errors with the gold NOT in the union | 1,087 | 157 | 14.4 % |

Top system confusions overall: setSecurityMode -> armSecuritySystem 59, setLighting -> setLightState 44,
rebootDevice -> restartDevice 31, setColor -> setAmbientLighting 31, getApplianceState -> getApplianceStatus 24,
findMyDevice -> findPairedPhone 22, setFanMode -> setFanSpeed 22, getLockState -> getLockStatus 21, setVolume ->
adjustVolume 21, streamCamera -> viewRemoteCamera 20. Most are cross-category in the registry (so ORG-1's domain
grouping cannot separate them) and many are near-synonyms whose registry descriptions do not say when to prefer one.

### A5. What knowledge is supplied, and what is missing

| knowledge | supplied today | missing (evidence) |
| --- | --- | --- |
| tool inventory | the full 152-tool registry in every request (official-protocol compact rows) | nothing missing in availability: the core never lacks the name |
| activation (which tool for which request) | the activation store: 8 retrieved values per Perception contact; the gold's guidance retrieved on 3,066 of 4,000 rows (76.65 %) | goal-to-function mappings for implicit requests (tier 4 coverage 34.2 %); contrastive "use X, not Y, when" distinctions for the 104 near-name twin pairs (23.7 % of system tool errors; KC-A1's inline notes on target pairs NULL, ORG-1's grouping HARMFUL) |
| exemplars | NONE: no Audio2Tool exemplar store exists (outcome of decision 155; E27/E28 are index views; the August tool-shaped base has no release and incompatible keys) | the kind of knowledge that carried SLURP (M1 exemplar supply, +12.6 SLU on the anchor) has no Audio2Tool instance; decision 157 admits it as a base item behind the SLURP line |
| parameter meaning | the parameter-meaning store (signature, type, constraints, roles, synthetic examples) | value conventions and identifiers: `deviceId` is 688 of the system's wrong-value keys; the registry publishes a default `deviceId` for 43 tools and none of those literals is in any card (2026-09-15 primary-parameter attribution); 376 of 583 reference deviceIds in the common cohort equal the public default |
| argument omission semantics | none explicit | when a call takes NO arguments (389 of 495 extra-key rows have an empty reference; the whole tier-1 exact gap to the paper's 92.4) and when a declared default should be left implicit (153 of 660 extra keys equal the default) |
| request state across turns / corrections | the Planner's revision loop | superseded requests: tier 6 extra calls 18 -> 64; tier 7 coverage 65 % |

### A6. Zero-contact re-read of the dual-store rows on the paired 400 at the A2T-AA half-widths (decision 157, option 1)

The same sealed rows restricted to the 400 ids of `A2T-PAIRED-400-V1`, system minus direct, tier-stratified paired
bootstrap (10,000 draws, seed 20260903, CI95), beside h_A2T from `docs/results/2026-09-27-a2t-aa-paired-400-read.md`
(1.625 pp tool, 1.375 pp exact; measured, not registered by the recipe's letter):

| metric | direct | system | delta (pp) | CI95 | in h units | per tier (pp, t1..t8) |
| --- | ---: | ---: | ---: | --- | ---: | --- |
| official tool accuracy | 61.75 | 59.00 | -2.75 | [-7.0, +1.5] | -1.69 | -20, -4, +4, 0, -6, +4, -4, +4 |
| official exact match | 15.00 | 20.25 | +5.25 | [+2.0, +8.5] | +3.82 | -6, +14, +14, +4, +2, +10, -2, +6 |

The paired 400 reproduces the 4,000-row pattern (exact up, tool down, tier 1 the worst) and shows why an A/A
half-width is not a contrast's width: the real contrast's CI95 on tool accuracy spans 8.5 points at n = 400.

### A7. Capability gaps, Audio2Tool

Ceilings are arithmetic on the sealed union-4000 rows (upper bounds, never predictions); the paper ladder is Table 3
(equal-tier means: Qwen3-Omni-30B 69.19 tool / 29.68 exact; Qwen-2.5-Omni-7B floor 57.48 tool). Today: direct
62.03 / 18.50, dual-store system 58.43 / 22.55.

| # | capability to add | the gap it closes (sealed rows) | knowledge it needs | ceiling if the gap closed fully | against the paper ladder |
| --- | --- | --- | --- | --- | --- |
| A-C1 | **Do-no-harm candidate formation**: a Perception shortlist that never displaces a tool the bare core would pick (e.g. always carry the direct answer's tool; or retrieval keyed on the request, not the note) | 215 tool harms and a net loss of 40 exact rows (44 -> 4) on miss rows; 239 miss rows the direct core had right | none new | tool 63.65 / exact 23.55 (misses answered as direct did) | tool above the Qwen2.5 floor, 5.5 below Qwen3-Omni's 69.19 |
| A-C1b | **Goal-to-function recall** (implicit requests, wrong-object proposals) | 1,117 misses, 329 in tier 4, 308 with no gold-domain candidate | goal/effect descriptions per tool; exemplars of implicit requests (the missing A2T exemplar store) | tool <= 80.0 if every miss converted at the covered rows' 80.05 % (optimistic) | above Qwen3-Omni's mean (69.19); the paper's own tier-4 value is 33.4 |
| A-C2 | **Twin-discriminating selection** inside a covered shortlist | 575 covered-but-wrong rows, 234 of them near-name twins | contrastive twin cards stated as decision rules (KC-A1's inline notes were not enough; ORG-1's grouping hurt); exemplars that separate the twins | tool <= 72.8 on its own | at Qwen3-Omni's mean |
| A-C3 | **Value grounding** (identifier catalog, value conventions) | 807 tool-right rows whose only defect is a value; `deviceId` 688 wrong-value keys | the published identifiers and defaults with provenance (absent from every card today), value-format conventions | exact <= 42.73 | well above the paper's 29.68 exact mean |
| A-C4 | **Argument omission / default semantics** | 527 tool-right rows whose only defect is a key (459 extra, 61 missing, 7 both); 389 extra-key rows with an empty reference | per-tool statement of when no argument is taken and when a default stays implicit | exact <= 35.73 | tier 1 exact is where the paper's 92.4 sits |
| A-C3+C4 | both | every tool-right inexact row | as above | exact <= 58.43 (= system tool accuracy) | |
| A-C5 | **Call-set state**: enumerate all requested calls, drop superseded ones | missing calls 246 (multi-reference), surplus calls 97 + 105; tier 6 surplus 64 | correction / supersession semantics in the working state | outside the official primary metric; moves repo exact and ordered-tool accuracy | tiers 3 / 6 / 8 |

Ordering the evidence supports: A-C1 first (it removes the measured harm with no new knowledge and makes the system at
least as good as direct on tool selection), then A-C3 (the largest exact mass, a concrete missing catalog), then the
knowledge items behind A-C1b / A-C2 (the Audio2Tool exemplar store of decision 157 and contrastive twin rules).

---

## Part B. Earnings21 + ConEC (and Earnings22)

**Rows.** The full-44 direct baseline `SAEA-E21-FULL44-DIRECT-BASELINE-V2` through the agentic-metric re-scoring
`SAEA-E21-MF-AGENTIC-METRIC-BASELINE-V1` (ConEC-mirror entity WER by type, numeric-value accuracy by kind), the two
sealed KC-E1f passes (`SAEA-E21-KC-E1F-REPAIR-44-V1`, `-REPLICATE-V1`), and the E35 sub10 pair
(`SAEA-E21-NATIVE-WINDOW-DIRECT-SUB10-V1` 342 windows / `SAEA-E21-NATIVE-WINDOW-SYSTEM-SUB10-V1` 1,597 contacts)
decomposed per native window over their sealed first-score ConEC alignments. Earlier reads carried beside, not
re-derived: the E21 own null (PERSON half-width 0.250, corpus WER 0.058), OBS-E1, TAIL2S, KC-E1, the E35 sub10
diagnosis, E39 / E39b, and the E22 semantic scan.

Two engineering facts surfaced while reading (recorded, not repaired here): `core.bundle.verify_bundle` now refuses
both E35 sub10 bundles because the archived copy of their pinned session receipt
(`serving-e21-native-window-flightruntime-np4-max1024-v1/session-receipt.json.archive/7d0baee1...json`) is absent
after a later restart, and `analysis.delivery_windows.verified_execution_unit_windows` refuses the system bundle on the
24 windows whose delivered text the Earnings delivery normaliser changed (their delivered text is not a trace text).
The per-window recovery was therefore redone in `e21_gap_diagnosis.py` with a hash-checked rule (24 windows cut from
the sealed stitch and re-hashed to their recorded digests; outputs, trace and scores digests equal the manifests; the
stitch rebuilds the sealed outputs byte for byte; the per-window partition reproduces the sealed S / D / I and
reference totals on both arms).

### B1. What the direct core gets wrong on the agentic metrics (full 44 calls, 359,765 reference words)

ConEC-mirror per-type WER = (S + D) / tagged reference words; insertions are unattributable (10,700, 36 % of all
errors). A word carrying two tags counts once per type.

| class | reference words | S | D | direct WER % | KC-E1f pass 1 | KC-E1f replicate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| corpus (__ALL__, incl. insertions) | 359,765 | 13,098 | 5,701 | 8.20 | 8.15 | 8.15 |
| non-entity | 304,331 | 9,697 | 4,699 | 4.73 | 4.73 | 4.73 |
| PERSON | 2,917 | 573 | 83 | **22.49** | **18.75** | **18.86** |
| ORG | 4,363 | 680 | 71 | 17.21 | 16.50 | 16.20 |
| ABBREVIATION | 2,566 | 615 | 44 | 25.68 | 25.68 | 25.41 |
| GPE | 1,537 | 258 | 29 | 18.67 | 17.96 | 17.96 |
| PRODUCT | 390 | 63 | 12 | 19.23 | 18.72 | 19.23 |
| FAC | 122 | 19 | 7 | 21.31 | 20.49 | 18.85 |
| YEAR | 1,180 | 206 | 24 | 19.49 | 19.49 | 19.49 |
| MONEY | 732 | 74 | 20 | 12.84 | 12.84 | 12.84 |
| CARDINAL | 4,463 | 366 | 125 | 11.00 | 11.02 | 11.02 |
| PERCENT | 1,868 | 169 | 21 | 10.17 | 10.17 | 10.17 |
| DATE | 16,166 | 417 | 144 | 3.47 | 3.47 | 3.47 |
| ORDINAL | 925 | 19 | 8 | 2.92 | 2.92 | 2.92 |

Named-entity words (PERSON, ORG, GPE, PRODUCT, FAC, NORP, LOC, EVENT, WEBSITE, ABBREVIATION, ALPHANUMERIC, ...) are
4.25 % of the reference words and carry 14.4 % of the substitution-plus-deletion mass (error rate 17.7 % against 4.73 %
for non-entity words); numeric-typed words are 7.3 % of the words and 8.8 % of the mass. **Entity errors are
substitutions, not omissions** (PERSON S 573 / D 83; ORG 680 / 71): the core hears a name and spells another. Numeric-
value accuracy 90.73 % over 9,734 values (currency 85.18, decimal 75.00, integer 88.34, percent 88.60, year 92.91,
ordinal 98.96; 911 spurious). Against ConEC Table 2: PERSON 22.5 sits between Whisper-large no-context 28.9 and the
oracle-list ceiling 13.0; ORG 17.2 is already below ConEC's oracle 17.7. **KC-E1f moves PERSON only** (-106 PERSON
substitutions, ORG -30, GPE -11; numerics unchanged): the one admitted Earnings knowledge module repairs names from the
roster and does not touch numbers.

Earnings22 (DEV, 2026-09-06 semantic scan): corpus WER 17.56 % but agentic (high-impact) error rate 1.92 %; 47.6 % of
the error mass is clip-boundary bleed (the model continues into the neighbouring utterance), named-entity high-impact
errors are company, plant and person names and a currency token deleted 60 times on one call. ConEC ships only PDFs
for Earnings22 (no roster, no token stream), and the owner's no-external-source rule leaves the corpus metadata table
as the only brief: its measured ceiling is 0.0229 corpus-WER points (`SAEA-E22-MF-BRIEF-SOURCE-AUDIT-V1`).

### B2. Where the system form added or removed value when it did not truncate (E35 sub10)

Reference words are partitioned per window by the DIRECT arm's alignment and the same spans are reused for the system
arm (the E35 diagnosis's convention); insertions stay with each arm's own window. Groups by the system window's
delivery. The E35 system form supplied NO ConEC knowledge: its governed participant-roster snapshot is reachable only
through the acquisition node, armed at 0 contacts (0 acquisitions on 342 of 342 windows).

| group (windows, reference words) | direct WER | system WER | S direct -> system | D direct -> system | I direct -> system | PERSON WER direct -> system | ORG | numeric matched (window level) |
| --- | ---: | ---: | --- | --- | --- | --- | --- | --- |
| Planner ACCEPT, accepted Solver draft (234, 51,202) | 7.04 | 7.17 | 1,667 -> 1,649 | 623 -> 814 | 1,313 -> 1,207 | 18.68 -> 22.99 (348 words) | 22.29 -> 22.29 | 1,358 -> 1,365 of 1,482 |
| terminal Solver draft (32, 7,219) | 6.77 | 11.28 | 211 -> 189 | 76 -> 457 | 202 -> 168 | 18.46 -> 26.15 | 21.37 -> 40.46 | 209 -> 192 of 220 |
| E13 abstention (76, 17,330) | 8.04 | 99.28 | 525 -> 51 | 408 -> 17,155 | 460 -> 0 | 13.44 -> 99.46 | 25.59 -> 99.41 | 494 -> 1 of 544 |
| all (342, 75,751) | 7.24 | 28.63 | 2,403 -> 1,889 | 1,107 -> 18,426 | 1,975 -> 1,375 | 17.03 -> 47.08 | 22.76 -> 38.84 | 2,061 -> 1,558 of 2,246 |

On the 234 completed windows (the E35 diagnosis's own partition gave 7.07 -> 7.22 on 51,193 words; the tie-break
differs by nine words): **the six-node form without knowledge is WER-neutral within 0.13 points, trades insertions
for deletions (-106 / +191, the deletions in non-entity words 531 -> 696), and moves PERSON the wrong way** (65 -> 80
errors; 13 windows worse, 2 better; S 59 -> 71). GPE (16.0 -> 13.2), CARDINAL (8.3 -> 7.9), YEAR (17.0 -> 15.9) and
window-level numeric matches (+7) move slightly the right way. Window by window: 81 windows with fewer errors, 82 with
more, 71 equal (net +67 errors). With 348 PERSON words this is a lead, not a measurement (the E21 own-null PERSON
half-width 0.25 is a full-44 figure and does not transfer to 10 calls). The revision round adds nothing measurable: 105
of its 162 revisions returned a byte-identical Solver draft (E35 diagnosis; E39b shows the same no-op pattern with a
tool-free Reviewer). The whole E35 harm is the 76 abstained windows (E13 episode scope), repaired in the harness by E39
(answering-node scope) and pending E41 (a bounded Perception note).

### B3. What knowledge is supplied versus missing (E35 sub10 direct alignment, 75,751 reference words)

For each entity-typed reference word: does its Whisper-normalised form occur among the words of the KC-E1 / KC-E1f
brief as supplied (roster participants, affiliations, divisions and document company / segment / term candidates,
12 entries per class), among the words of the full ConEC context but beyond the cap, or nowhere in the context?

| type | error words (S + D) | in the capped brief | in the context beyond the cap | absent from the context | correct words in the capped brief |
| --- | ---: | ---: | ---: | ---: | ---: |
| PERSON | 102 | 47 (46 %) | 17 (17 %) | 38 (37 %) | 341 of 497 |
| ORG | 211 | 38 (18 %) | 60 (28 %) | 113 (54 %) | 148 of 716 |
| GPE | 68 | 14 (21 %) | 40 (59 %) | 14 (21 %) | 45 of 333 |
| PRODUCT | 14 | 0 | 10 (71 %) | 4 | 8 of 53 |
| ABBREVIATION | 173 | 5 (3 %) | 69 (40 %) | 99 (57 %) | 13 of 381 |
| WEBSITE | 8 | 2 | 3 | 3 | 0 of 11 |
| CARDINAL | 96 | 4 | 24 | 68 (71 %) | 29 of 842 |
| YEAR | 59 | 0 | 4 | 55 (93 %) | 0 of 225 |
| PERCENT | 48 | 0 | 2 | 46 (96 %) | 2 of 359 |
| MONEY | 17 | 0 | 4 | 13 | 0 of 128 |
| DATE | 120 | 4 | 32 | 84 | 598 of 3,821 |
| non-entity | 2,659 | 49 (2 %) | 473 (18 %) | 2,137 (80 %) | 1,439 of 61,446 |

**Reading.** The capped brief contains fewer than half of the PERSON words the core gets wrong and under a fifth of
the ORG words; the rest of ConEC's context holds another 17 % of PERSON, 28 % of ORG, 59 % of GPE and 71 % of PRODUCT
error words that the 12-entry cap (itself forced by prompt fit: cap 16 did not fit on KC-E1) leaves out; and 37 % of
PERSON and 54 % of ORG error words are nowhere in the context the rules allow. Numbers are knowledge-free by nature:
93-96 % of the YEAR and PERCENT errors cannot be supplied by any context -- they are hearing errors.

### B4. Numeric error shapes (E35 sub10 direct, numeric-typed reference words)

| type | errors | deleted | substituted by a token with a digit | substituted by a word |
| --- | ---: | ---: | ---: | ---: |
| CARDINAL | 96 | 22 | 65 | 9 |
| DATE | 120 | 32 | 58 | 30 |
| YEAR | 59 | 2 | 54 | 3 |
| PERCENT | 48 | 4 | 38 | 6 |
| MONEY | 17 | 5 | 8 | 4 |
| ORDINAL | 6 | 1 | 0 | 5 |
| TIME | 6 | 0 | 0 | 6 |
| all | 352 | 66 (19 %) | 223 (63 %) | 63 (18 %) |

Both sides are Whisper-normalised before alignment, so an ordinary words-versus-digits difference never reaches these
counts. The substitutions by a digit-bearing token are wrong VALUES or digit splits the normaliser does not merge; the
18 % substituted by a word is the most a formatting convention could recover.

### B5. Capability gaps, Earnings

Ceilings are arithmetic upper bounds; the full-44 PERSON ceilings apply the sub10 coverage shares to the full-44
PERSON rate (22.49 %) and assume every covered error is repaired, so they are optimistic by construction.

| # | capability to add | the gap it closes (sealed rows) | knowledge it needs | ceiling | evidence so far |
| --- | --- | --- | --- | --- | --- |
| E-C0 | **Harness completion** (answering-node finite-completion scope, per-role caps, bounded Perception note) | 76 abstained windows = 95.6 % of E35's extra error mass | none | system corpus WER 28.6 -> about 7.8 on sub10 (E35 counterfactual); a prerequisite, not a gain | E39 / E39b prove the scope repair on receipts; E41 dry run registered, flies after COMP-1 |
| E-C1 | **Roster-grounded entity repair on the USE axis** (KC-E1f form, second pass, substitutions only) | PERSON substitutions (573 on full 44) | the ConEC roster + document brief at cap 12 (supplied) | PERSON 22.49 -> about 12.1 if every brief-covered PERSON error were repaired (46 %); ConEC's oracle-list row is 13.0 | ADMITTED and REPLICATED: 22.49 -> 18.75 / 18.86 (+3.6 to +3.7 pp, 10 null half-widths); not yet in a default plan (the judges-table form smoke is owed) |
| E-C2 | **Speech-keyed entity retrieval from the full context** (select the entries a window needs instead of a per-class cap) | error words beyond the cap: PERSON 17 %, ORG 28 %, GPE 59 %, PRODUCT 71 %, ABBREVIATION 40 % | the full ConEC roster and document stream (already in the D1 layers) | PERSON about 8.4, ORG about 9.2 (17.21 x 0.54) if every context-covered error were repaired | none flown; KC-E1 showed whole-prompt supply costs deletions (+2,692), so retrieval must feed the repair pass, not the transcription prompt |
| E-C3 | **Targeted numeric re-listen** (re-decode a short span around each number with the value in question) | 63 % of numeric-typed errors are wrong values; numeric accuracy 90.73 % | none (acoustic, not knowledge) | numeric accuracy <= about 96.6 % if the value errors were fixed (0.63 x 9.27 missing points) | none flown; the obs re-listen seam exists (W2) |
| E-C4 | **Numeric format convention** | 18 % of numeric-typed errors | a delivery convention | numeric accuracy <= about +1.7 pp | small by measurement; not a priority |
| E-C5 | **Transport units with context** (speaker-turn units plus a context margin) | OBS-E1: corpus WER -1.05 but PERSON +2.09 worse, 78.7 % of the harm in units under 10 s; units of 60 s or more beat the 90 s windows on PERSON | diarization (frozen tool, already run) | corpus WER about -1.0 with the PERSON harm up to 93 % addressable by a context margin | OBS-E1 REJECTED; OBS-E1b preregistered, not flown |
| E-C6 | **Entity-targeted review** (check names against the roster) instead of a generic Reviewer / revise round | the generic round is a no-op on 105 of 162 revisions and PERSON moves the wrong way on the 234 completed windows | the roster | the generic loop is 913 of the 1,597 system contacts (Reviewer 428, Planner 398, second Solver 87), 315 of them spent on byte-identical redrafts; the PERSON effect of a targeted check is unmeasured | E35 / E39b receipts |
| E-C7 | **Earnings22 clip-boundary handling** | 47.6 % of E22 DEV error mass is boundary continuation | none | about 7.6 corpus-WER points (the boundary block of the 9.98-point task-definition bin, E22 semantic scan) | tail / pad / re-cut probes flown on DEV; the published arrays overlap the same way, so this is sensitivity, not alignment |
| E-C8 | **Knowledge beyond ConEC** | 37 % of PERSON and 54 % of ORG error words are absent from every allowed context | an allowed source (none today: E21 contexts only; E22 no external sources by owner ruling) | unbounded by this study's sources | an owner question, not an engineering item |

The measurement that matters for Earnings is the entity and numeric table, not corpus WER: the core's corpus WER is
already 1.5 points better than the published Whisper-large-v3 row, while PERSON is 2.7 times the corpus rate and
insertions (36 % of all errors) never touch an entity. The order the evidence supports: finish the harness (E-C0),
put the admitted repair into the default plan (E-C1), then feed it by retrieval instead of a cap (E-C2) and add a
numeric re-listen (E-C3); the generic review loop should become entity-targeted (E-C6) or be pruned.
