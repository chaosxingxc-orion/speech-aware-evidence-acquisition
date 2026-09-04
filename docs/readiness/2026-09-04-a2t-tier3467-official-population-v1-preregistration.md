# Audio2Tool tiers-3/4/6/7 official population, v1 — preregistration

One run, profile `baseline-reproduction`, one cell. Written before any model contact.

| Run id | Cell | Population | Experiment fragment |
|---|---|---|---|
| `SAEA-A2T-TIER3467-OFFICIAL-POPULATION-V1` | `T3467-official-pop-2000` | A2T-TIER3467-OFFICIAL-POP-2000 (2,000) | `configs/experiment/a2t-tier3467-official-population-v1.json` |

Predecessor: `docs/readiness/2026-09-04-a2t-tier258-official-population-v1-verdict.md`
(run `SAEA-A2T-TIER258-OFFICIAL-POPULATION-V1`, cell `T258-official-pop-1500`, attempt
`attempt-20260904T193726Z-t258officialpop1500`, manifest SHA-256
`7de7429110e978784fc8303e632c54360d9cdbb70aa61e9d084b957f68db847f`, study commit `b52c22b0`).

**One run id.** All four tiers fly in one roster with tier as the stratum, so there is one
population, one split identity hash and one exposure row. `contracts.gate_exposure` requires
exactly one pre-registered row per run id whose split identity hash equals the plan's; the
tiers-2/5/8 flight established this shape and it is unchanged here.

## 1. Why this flight exists

Four tiers of the published table have been decided at n = 500 (tier 1, and tiers 2, 5 and 8). The
four that remain are the ones the frozen 400 happened to place **inside** the owner's 3-point band —
which at n = 50 says nothing at all, because the Wilson CI90 there is about ±11 pp:

| tier | frozen 400 (n = 50) | CI90 | paper | delta |
|---|---:|---|---:|---:|
| tier3_multi_intent | 72.0 | [60.6, 81.1] | 74.7 | −2.7 |
| tier4_implicit | 28.0 | [18.7, 39.6] | 33.4 | −5.4 |
| tier6_correction | 84.0 | [73.9, 90.7] | 81.5 | +2.5 |
| tier7_multiturn | 58.0 | [46.4, 68.7] | 54.6 | +3.4 |

An interval that wide contains both "aligned" and "off by ten points" on every one of them. This
flight buys the same resolution the other four tiers already have, under the paper code's own
population rule and n = 500 each, and completes the eight-tier table at one resolution.

Nothing about the protocol is re-litigated. The request is the released code mirrored string for
string (`docs/receipts/environments/audio2tool-official-code.json`, commit
`b9d5383ca30945fbafb965a04bea40117e1e8a82`), byte-identical to `R-official-raw`,
`T1-official-pop-500` and `T258-official-pop-1500`.

### The published rows this flight is judged against

| tier | Qwen-3-Omni-30B TA | EM | Slot F1 | Qwen-2.5-Omni-7B TA | weakest published SpeechLM TA |
|---|---:|---:|---:|---:|---:|
| tier3_multi_intent | 74.7 | 28.6 | 35.0 | 50.2 | 40.6 |
| tier4_implicit | 33.4 | 11.3 | 23.4 | 22.4 | 7.9 |
| tier6_correction | 81.5 | 24.8 | 32.4 | 68.3 | 44.6 |
| tier7_multiturn | 54.6 | 16.3 | 26.8 | 48.2 | 34.5 |

## 2. Each tier's own population, derived from the pinned code

`BenchmarkEvaluator` with `max_speakers_per_query 1` evaluates `audio_paths[0]` for every query
directory a tier loader yields, walking `sorted(data_dir.glob("query_*"))`. Every claim below is
verified in the roster receipt, directory by directory, not assumed. Builder:
`scripts/build_a2t_tier258_official_population_roster.py --group tier3467` — the tiers-2/5/8 builder
with its tier list extended, not a new script.

**`tier3_multi_intent`, `tier4_implicit`, `tier6_correction` — the tier-1/tier-2 spelling exactly**
(`tier3_dataset.py`, `tier4_dataset.py`, `tier6_dataset.py`): the rows of `generation_results.csv`
in file order whose `success` is true, resolving each row's `audio_path` and falling back to
`query_dir / Path(audio_path).name` when the CSV's absolute path is stale. The released CSVs carry
the authors' internal `/data2/Audio2ToolData/...` paths, so on any public copy the documented
fallback is the branch that fires. **2,146 / 2,132 / 2,146 query directories, all agreements with
the manifest-first pick, 0 disagreements, 0 unresolved.** No counterpart of tier 1's one
`query_01982` exception exists on any of them.

**Tier 4 ships an irregular number of recordings, and it changes nothing.** 2,125 of its 2,132
directories ship the usual two; **seven ship three or four** (`query_00185`, `query_00192`,
`query_00232`, `query_00483`, `query_00763`, `query_00860`, `query_00995`), and **two of those carry
a duplicated manifest row** — `query_00232` ids 468/469 and `query_00763` ids 1534/1535, each pair
naming the same `speaker_idx` and the same wav. On all seven the released loader's first resolvable
CSV row is still the manifest's lowest-id row, so the population pick is unaffected; the duplicate
is never the lowest id. The builder records the shipped-count distribution and both duplicate pairs
rather than asserting a count the release does not honour.

**`tier7_multiturn` — the one tier whose audio is not in the tier manifest at all.** Its rows carry
no top-level `path` and no `duration`; audio lives per turn inside `chat_history`. And
`Tier7Dataset._get_audio_paths` never opens `generation_results.csv`: it returns
`sorted(query_dir.glob("turn_*_user_*.wav"))`, with `include_agent_turns` defaulting to `False`. So
`audio_paths[0]` is the **first user turn's wav**, and the request carries no chat history, no agent
turn and no later user turn — only that one recording, against a gold call the whole conversation
resolves to.

This flight applies exactly that rule, and it is cross-checked against the release's own metadata:
the tier manifest's `chat_history[0]` names the identical file, with a matching duration, on
**all 2,146 directories**, and the glob's first element is `turn_00_user_*.wav` on **all 2,146**.

**Which turn it resolves to, per query.** Every released tier-7 query has at least two user turns:
1,449 have two, 691 have three, 6 have four. **Zero queries have `turn_00` as their only user turn;
all 2,146 have later user turns.** Within the drawn 500 the split is 345 / 153 / 2. The last user
turn is `turn_02` on 1,445 queries, `turn_04` on 677, `turn_03` on 18 and `turn_06` on 6.

**How the frozen 400's tier-7 rows were bound, for comparison.** They were **not** bound this way.
`data.audio2tool._entry_media` binds a tier-7 sample to `chat_history[-1]` — the **final** user
turn, the one that actually states the request ("Yes, please turn it on!"). So the frozen 400's
tier-7 58.0 was measured on a recording the released evaluator never sends, and this flight's
tier-7 number is measured on a recording the frozen 400 never sent. The two tier-7 estimates are
therefore **not** two samples of the same measurement, and section 7 treats the tier-7 row of the
population-effect table accordingly.

### The two tier-7 exclusions, applied before the draw

Both are constraints of **this repository**, not of the release, and both are named id by id in the
roster receipt.

1. **Media identity (50 ids).** `docs/receipts/artifacts/d1-identity.json` already records 50 tier-7
   sample ids — the frozen 400's tier-7 rows — bound to the **final** user turn.
   `contracts.gate_media_identity` refuses a D1 supplement that duplicates a base D1 sample, and for
   a base-D1 sample it re-hashes the flown file against the base record, so a first-user-turn
   binding of those same ids can never reach the frozen core. Under the unrestricted population the
   seeded draw would have taken 12 of them.
2. **Scorer-side resolvability (4 ids).** Ids **373, 1258, 1744, 2023** end their `chat_history` on
   an **agent** turn. `_entry_media` fails closed on those, so admitting one into a probe-sample
   receipt would break `load_official_gold` for every Audio2Tool scoring job, not just this one. The
   unrestricted draw would have taken 2 of them.

The tier-7 draw is therefore uniform over **2,092 of the released 2,146 (97.5 %)**. This is
deviation 4 of section 4. Tiers 3, 4 and 6 keep their populations whole: an overlapping query there
resolves to a different manifest id whenever the speaker differs, and where the id is the same the
media is the same file, so no re-binding arises.

### The draw

500 per tier, uniform without replacement, `random.Random(20260803).sample(population, 500)` over
each tier's population in ascending manifest-`id` (= sorted query-directory) order — the same call,
with the same seed, every official-population flight used. Each tier draws from its own freshly
seeded generator. Roster receipt:
`docs/checks/speech-aware-evidence-acquisition/2026-09-04-a2t-tier3467-official-population-roster/flight-roster-receipt.json`
(SHA-256 `6cf30c18bb9df209f87662b804ed117be7f31b1b2b9e486553ba7019915fc760`), split identity hash
`00f60263…`, flight split identity hash `bdd28d42…`.

**`max_samples` is deliberately not used.** The release orders every subset
`smart_home → wearables → smart_car` (its own README says so), so `max_samples 500` over sorted
query directories would be a near-pure `smart_home` sample on all four tiers.

| tier | population | drawn | coverage | draw domain mix | population domain mix | draw audio (s) | longest row (s) |
|---|---:|---:|---:|---|---|---:|---:|
| tier3_multi_intent | 2,146 | 500 | 23.3 % | 368 / 91 / 41 | 1590 / 390 / 166 | 3,211.2795 | 654.6325 |
| tier4_implicit | 2,132 | 500 | 23.5 % | 375 / 90 / 35 | 1576 / 390 / 166 | 1,464.958 | 5.976875 |
| tier6_correction | 2,146 | 500 | 23.3 % | 368 / 91 / 41 | 1590 / 390 / 166 | 3,382.069583 | 654.635667 |
| tier7_multiturn | 2,092 | 500 | 23.9 % | 380 / 84 / 36 | 1557 / 373 / 162 | 3,906.524083 | 654.635667 |
| **all four** | **8,516** | **2,000** | — | — | — | **11,964.831167** | **654.635667** |

Domain mixes are `smart_home / wearables / smart_car`. Population audio totals are 12,983.911 s,
6,926.113 s, 18,183.708 s and 17,035.034 s. Every population is 73.9–74.4 % `smart_home`, the same
concentration that decided both tiers-2/5/8 failures.

**Overlap with the frozen 400.** By *query*: 10 of the 50 tier-3 queries, 13 of the 50 tier-4, 12 of
the 50 tier-6 and **0** of the 50 tier-7 (all 50 were excluded above). By *sample id*: 6 / 7 / 5 / 0
— tiers 3, 4 and 6 of the frozen 400 carry mixed speakers, so a shared query often means a different
recording. In total 46 of the 2,000 sample ids are already inside a committed probe-sample receipt
(18 in `r1-audio2tool-sample.json`, 15 and 13 in the two 104-row post-seal AgentLoop scoring
receipts). Nothing is re-drawn for them; they are exposed rows being used again.

### Identity closure

- **Scoring identity.** 1,954 of the 2,000 sample ids are new to `data.audio2tool`'s
  frozen-receipt universe and enter it through
  `docs/receipts/probe-samples/a2t-tier3467-official-population-2000.json` (SHA-256
  `e8c49d388ab01383d38443212a2f8a6adbccff27d25fefcc544d298ca87dea8e`, split identity hash
  `4da261f6…`, per tier 486 / 480 / 491 / 497). The other 46 already resolve through existing
  receipts, and `data.audio2tool._resolve_items` refuses a sample id that appears in two receipts,
  so repeating them would be a defect. Without this receipt `a2t-toolcall-official` refuses to score
  the roster at all.
- **Media identity.** 1,982 of the 2,000 are new to the immutable D1 identity closure and are
  carried by `docs/receipts/artifacts/d1-a2t-tier3467-official-population-2000.json` (SHA-256
  `8ec384ef6c7a715cf51da9c6857491cccca2aeee0089003e0f71ca0bb544c6d7`, schema
  `saea-d1-media-supplement-v1`, 1,982 entries, 570,747,430 bytes). The 18 already inside
  `d1-identity.json` (6 tier-3, 7 tier-4, 5 tier-6, 0 tier-7) are verified against it byte for byte
  and skipped, because `contracts.gate_media_identity` refuses a supplement that duplicates a base
  D1 sample. Tier 7 contributes none of those 18 by construction.

Both receipts are model-free: identifiers, media paths, WAV byte hashes and container headers only.

## 3. The cell

| Cell | Roster | System message | Model fragment | Serving geometry |
|---|---|---|---|---|
| `T3467-official-pop-2000` | A2T-TIER3467-OFFICIAL-POP-2000 (2,000 rows) | the release's in-code default, unchanged from `R-official-raw`, `T1-official-pop-500` and `T258-official-pop-1500` | `q4km-featcache-a2t-official-np2-04ccc72a` | `-c 49152 -np 2`, 24,576 tokens/slot |

Shared and unchanged: `bare-core` arm, the `direct-only` phase program of
`rails.controllers.EvidenceAgentController` through `core.flight.FlightRuntime` and the OpenJiuwen
executor, entered through `scripts/flights/run_calibration_cell.py`; raw audio through the bf16
mmproj on build `04ccc72a`; the compact 152-row registry rendered by `format_tools_compact`; the
user turn's audio first and then `Convert this voice command to a tool call.`; temperature 0, seed
20260803, `max_tokens` 256, one contact per item, no evidence, no OBS.

**The longest wav was checked first, and it forces `-np 2`.** This roster carries **three** of the
release's 654-second synthesis defects — `tier3_multi_intent:003555` (654.6325 s),
`tier6_correction:003151` (654.635667 s) and `tier7_multiturn:001033` (654.635667 s) — against the
tier-1 official population's one (`tier1_direct:003943`) and the tiers-2/5/8 roster's longest of
32.43375 s. No other row of this roster exceeds 60 s. Speech cost follows the mmproj encoder's exact
one-second window rule `n_tokens = 13 × ceil(audio_seconds)`, which reproduces all 400 per-packet
`n_tokens` of the A2T-CALIBRATION-400 promotion receipt without a single exception, so the worst row
costs 8,515 speech tokens and its request needs `3,581 text + 8,515 speech + 256 completion + 2
special = 12,354` tokens. At the 49,152 total context this GPU is proven to serve on the raw path,
`-np 2` leaves 12,222 tokens of margin against the preregistered 8,192-token reserve; `-np 3` would
leave 4,030 and is refused. So this cell serves the **same geometry `T1-official-pop-500` flew**,
through the model fragment that already exists for it (whose 900 s timeout exists for exactly these
rows), and no new model fragment is created. The prompt-fit route re-proves the window rule and
re-measures this before any generation.

## 4. Deviations, recorded rather than fixed

The deviations of the replication and the earlier official-population preregistrations still stand
where they apply. In force here:

1. **Quantization and runtime.** Q4_K_M GGUF on llama.cpp build `04ccc72a` instead of the release's
   bf16 HuggingFace checkpoint. Unchanged, not flown here, and the subject of its own preregistered
   probe. It is the last of the three ranked Tier-1 suspects still open.
2. **Chat template.** The GGUF chat template under `--jinja`, not the HF `Qwen3OmniMoeProcessor`
   template. The prompt-fit route proves what it renders.
3. **Population reconstruction generally.** The rule is derived from the pinned loaders and verified
   on 2,146 + 2,132 + 2,146 + 2,146 directories. If the authors evaluated their **internal** corpus
   (up to 25 speakers per query on tiers 3, 4 and 6) rather than the public release (two per query,
   or three/four on seven tier-4 directories), "first successful speaker" resolves to a different
   wav for most queries. That is unknowable from the release.
4. **Tier 7's population is narrowed by 54 of 2,146 (2.5 %)** for the two identity reasons in
   section 2. The excluded 50 are the frozen 400's own tier-7 queries — themselves a fixed set, not
   a property of the tier — and the excluded 4 are a release defect this repository's loader refuses.
   The estimand for tier 7 is therefore the released tier-7 population *minus those 54*, stated
   plainly rather than silently.
5. **Tier 7 hears one turn.** The released evaluator sends only the first user turn, with no history
   and no agent audio, while the gold call is what the whole conversation resolves to. That is the
   release's own protocol and it is flown unchanged; it is recorded here because it is the single
   largest interpretive fact about the tier-7 number, and because the frozen 400 bound the tier
   differently (section 2).
6. **Tier 4's irregular shipping and duplicated manifest rows.** Section 2. Recorded; the pick is
   unaffected.
7. **Sample rate.** Every Audio2Tool wav is 24 kHz mono 16-bit, not the 16 kHz its README claims.
   The release's own pipeline resamples with `librosa.load(..., sr=16000)`; llama.cpp's mmproj does
   its own resampling. The frozen 400 is the same material, so the comparison sits on identical
   footing.
8. **Serving geometry.** `-np`/`-c` have no counterpart in the release, which runs one request at a
   time on HF. Section 3 records the check that fixed it.
9. **Seed and temperature.** 20260803 and 0, both inert under greedy decoding, as before.
10. **Builder reuse.** The roster builder is the tiers-2/5/8 one with a second tier group
    (`--group tier3467`); the tiers-2/5/8 receipt still rebuilds byte for byte from it. The D1
    media-supplement builder, the prompt-fit script, the flight entry point, the wire check and the
    scorers are reused unchanged. No new script family.

## 5. Budget (ExecutionPlan)

| Run id | Calls (planned / ceiling) | Speech seconds (planned / ceiling) | GPU hours (planned / ceiling) |
|---|---|---|---|
| `SAEA-A2T-TIER3467-OFFICIAL-POPULATION-V1` | 2,008 / 2,080 | 11,965 / 12,100 | 1.5 / 2.0 |
| `SAEA-A2T-TIER3467-OFFICIAL-POPULATION-SMOKE-V1` | 12 / 20 | 5,950 / 6,000 | 0.2 / 0.2 |
| `SAEA-A2T-TIER3467-OFFICIAL-POPULATION-PROMPT-FIT-V1` | 1 / 2 | 1 / 2 | 0.3 / 0.3 |
| **Flight total** | **2,021 / 2,102** | **17,916 / 18,102** | **2.0 / 2.5** |

Paid API spend 0 throughout. 2,008 = 2,000 rows + 8 canaries. The measured roster sum is
11,964.831167 s, rounded up to the integer `contracts.ExecutionPlan` requires and then to 11,965.
The smoke plan registers 12 rather than 4 calls, and three passes of speech rather than one, because
attempt budget is enforced run-cumulatively (`core.model.adapter.FrozenCoreAdapter` re-reads every
prior attempt's durable actuals for the run id on every request), so a plan must cover prior spend
plus its own worst case; the smoke's speech figure is large only because three of its four rows are
the 654-second defect, which is exactly why they are the rows worth proving first. One-shot attempt
semantics; at most one recovery re-registration per flight; a second failure stops the flight and
the fix is proven on a 4-row dry run.

## 6. Pre-contact prerequisites

1. **Roster and identity receipts** — the flight roster, the additive probe-sample receipt and the
   additive D1 media supplement, all three model-free and committed.
2. **Fragments** — dataset, experiment and smoke fragments composing cleanly against the existing
   `a2t-direct-official-protocol` baseline and `q4km-featcache-a2t-official-np2-04ccc72a` model
   fragments, with `server_args` agreeing with `serving_geometry`.
3. **Prompt fit** — the exact request rendered through the pinned template on the resident server
   and measured, with its own exposure row, before any generation. Certification: every request fits
   its slot beside the 256-token completion ceiling with the 8,192-token reserve; the rendered
   system text equals the release's in-code-default spelling (16,143 chars, `be7f31a2…`) and the
   receipt records which variant matched. Speech cost comes from the one-second window rule, which
   the script PROVES against the A2T-CALIBRATION-400 promotion receipt before applying it.
4. **Exposure rows** — three, one per run id (prompt fit, smoke, flight), each registered with
   `consumed = no` before the contact it authorizes.
5. **Wire check and smoke** — `FlightRuntime.wire_check` on a clean committed tree (zero contacts),
   then a 4-row smoke. The smoke rows are fixed here, before they were read off the roster: the
   longest sample of each tier — `tier3_multi_intent:003555`, `tier4_implicit:003373`,
   `tier6_correction:003151`, `tier7_multiturn:001033`. That covers all four strata, all three
   654-second rows (the flight's worst requests) and the first tier-7 `turn_00` user-turn wav this
   repository has ever served.
6. **GPU power** — `nvidia-smi -q -d POWER` must report `enforced.power.limit` 100.00 W. A lower cap
   stops the flight (the Legion SmartFanMode note).

## 7. Decision rules — three outcomes per tier

The owner's alignment standard governs: **aligned means within 3 points of the official number, and
being better than the official number by more than 3 points is also acceptable.** The number is the
**official** scorer's tool accuracy (`a2t-toolcall-official`, the vendored
`metrics.compute_tool_accuracy` against the primary gold tool).

Per tier, independently:

- **ALIGNED** — official tool accuracy ≥ paper − 3.0: **tier 3 ≥ 71.7, tier 4 ≥ 30.4, tier 6 ≥ 78.5,
  tier 7 ≥ 51.6** (or better than the paper).
- **CONSISTENT-WITHIN-NOISE** — not ALIGNED, but the paper value lies inside the Wilson score CI90
  for a binomial proportion at n = 500.
- **FAIL** — neither.

**Floor rule, reported for every tier whatever the outcome.** Our number is tabled against
Qwen-2.5-Omni-7B (50.2 / 22.4 / 68.3 / 48.2) and against the weakest published SpeechLM row
(40.6 / 7.9 / 44.6 / 34.5). A tier below a degraded model's published number is called out
explicitly in the verdict.

**Power.** n = 500 gives a binomial standard error of 1.9 pp at p = 0.75, 2.1 pp at p = 0.33,
1.7 pp at p = 0.82 and 2.2 pp at p = 0.55, so the 3 pp band is wider than the noise on all four
tiers and ALIGNED is a meaningful outcome rather than an artefact of a small sample. At n = 50 the
standard error was 6–7 pp, which is exactly why none of these four tiers was decided on the frozen
400 even though all four fell inside the band.

### Reported beside the decisions, none of them part of it

- Official exact match and parameter F1 (macro and micro) per tier, beside the paper's EM / Slot F1
  (28.6 / 35.0, 11.3 / 23.4, 24.8 / 32.4, 16.3 / 26.8).
- **Tier 3 under both rules**: the official first-call rule and `a2t-toolcall-v2`'s ordered-sequence
  rule, with the count of rows whose response named more than one call and the count of gold rows
  carrying additional expected calls. Tier 3 is the multi-intent tier — its manifest rows carry
  populated `additional_tool_calls` — so the divergence the tier-8 slice measured is expected here
  too, and is reported the same way.
- The same per-tier tables under the extended `a2t-toolcall-v2`, with the official scorer beside it
  and the rule behind any gap wider than 3 points named.
- Per-domain breakdown per tier (`smart_home` / `wearables` / `smart_car`), natural mixture and
  equal-domain, as the tier-1 and tiers-2/5/8 verdicts did.
- **Tier 7's turn resolution**: which user turn each drawn row resolved to, the user-turn count
  distribution, and how the frozen 400's tier-7 rows were bound instead.
- Each tier against the frozen 400's own 50 rows of that tier, so the population effect is a
  difference rather than a replacement. This is not a paired contrast: the populations differ, and
  on tier 7 the *binding* differs as well, which the verdict must state beside that row.
- Parse rate, and the count of rows naming more than one call, per tier.

## 8. Claim surface

Nothing here is a superiority, generality or Stage-3 claim. The population is discovery data and no
knob is tuned on it. Not authorized: any test contact, any mechanism arm, a Q8_0 flight (its own
preregistered probe), a training-free policy fit, any edit to the locked SLURP cell, and any
re-flight of tiers 1, 2, 5 or 8.

## 9. Execution log

Filled in as the flight proceeds; every entry is written before the step it describes is read.

### 2026-09-04, Phase 1 — model-free preparation (zero contacts)

- Reconstructed and verified each tier's released population, drew the 2,000-row roster, and landed
  the additive probe-sample receipt and D1 media supplement.
- Landed the dataset, experiment and smoke fragments and the probe-manifest registration; no new
  model or baseline fragment was needed because the tier-1 flight's `-np 2` fragment is exactly
  what the three 654-second rows require.
- Extended the tiers-2/5/8 roster builder with a second tier group rather than copying it, and
  re-ran the tiers-2/5/8 group to confirm its committed receipt still rebuilds **byte for byte**
  (SHA-256 `9e17b44e…`).
- Found and recorded three release facts: tier 4 ships three or four recordings on seven
  directories and duplicates a manifest row on two of them; tier 7's released loader hears only the
  first user turn while every one of its 2,146 queries has later user turns; and three rows of this
  roster are the 654-second synthesis defect.
- Commit `2a5b9392`. `python scripts/checks/engineering_base_check.py`: PASS.
  `pytest tests/unit`: 6,035 passed, 6 failed — exactly the known pre-existing set (2 × `test_pemb3m`,
  2 × `test_pemb4r`, `test_bundle` CLI, and the full-suite-only registry-pollution failure in
  `test_engineering_base_check` that passes in isolation) — plus the known
  `test_build_a2t_g6_family_sweep` collection error from the verl `scripts` shadow.
- The three exposure rows were registered next, all `consumed = no`, before any contact
  (commit `e846a694`). GPU `enforced.power.limit` read 100.00 W and no `llama-server` was resident
  before the first row was written.

### 2026-09-04, Phase 2 — prompt fit (zero generated tokens)

Row `SAEA-A2T-TIER3467-OFFICIAL-POPULATION-PROMPT-FIT-V1`, registered before the server was touched.
One `GET /props`, one `POST /apply-template` and two `POST /tokenize`; no completion endpoint
touched, `generations` 0.

| Cell | System message | Text tokens | Worst required | Slot | Margin | Fits |
|---|---|---:|---:|---:|---:|:--:|
| `T3467-official-pop-2000` | in-code-default, 16,143 chars, `be7f31a2…` | 3,581 | 12,354 (`tier3_multi_intent:003555`) | 24,576 (`-np 2`) | 12,222 | yes |

Receipt:
`docs/checks/speech-aware-evidence-acquisition/2026-09-04-a2t-tier3467-official-population-v1/prompt-fit/prompt-fit.json`
(SHA-256 `12e895df4697a9d0295e95aab2ab1072fbd748c8e2560ca035055f1297f6d5f6`).

Three findings carried forward:

1. **The rendered system message is the release's in-code default, verbatim.** 16,143 chars,
   `be7f31a2e8c7e6dd…`, 3,581 text tokens — the same bytes and the same count the sealed
   `R-official-raw`, `T1-official-pop-500` and `T258-official-pop-1500` cells were certified
   against, and `system_text_verbatim_in_rendered_prompt` is true.
2. **The window rule held on all 400 reference packets** (13 tokens per one-second window, zero
   disagreements) before it was applied to this unpreprocessed roster. Over the 2,000 rows it gives
   min 13, median 65, p95 117, max 8,515 — the p95 is *lower* than the tiers-2/5/8 roster's 169
   while the max is twenty times larger, which is the shape of a roster with three outliers and
   nothing else over 60 s.
3. **`-np 2` is certified, and it is the largest admissible slot count.** Required window min 3,852,
   median 3,904, max 12,354; served-slot margin min 12,222 against the 8,192-token reserve;
   `largest_slot_count_meeting_reserve_at_this_context` is 2, so the tiers-2/5/8 cell's `-np 3` is
   refused by the rule and not by hand.

Commit `ff1cf56a`.

### 2026-09-04, Phase 3 — wire check and smoke

- `FlightRuntime.wire_check` on a clean committed tree (`735a7ea4`): **2,000 contacts** through the
  real client, adapter, payload binding and sealer against the fake gate and transport, **zero
  sockets opened, zero servers started**. `payload_keys` is exactly `ARM_VISIBLE_FIELDS["bare-core"]`
  (ten fields). `seal_and_score` OK with all four registered scorers through `core.scoring_batch` as
  one whole-manifest job over a 2,000-row outputs file — which is also the proof that the tier-7
  exclusion of the four agent-last ids was sufficient, because `load_official_gold` resolves every
  receipt item through the `_entry_media` that fails closed on them. Receipt
  `wire-check/wire-check-t3467-official-pop-2000.json` (SHA-256
  `1c0b4e2b4ce35ebecb96fc0511cd47286e41a789021691deb1314eb5c49df6b0`); commit `735a7ea4`.
- Smoke row `SAEA-A2T-TIER3467-OFFICIAL-POPULATION-SMOKE-V1`, attempt
  `attempt-20260904T210659Z-t3467officialpop2000`, manifest SHA-256
  `ff7549374bedf6ae91479883b550672be05490b2fb98ab208222e0ae1f639da5`, study commit `735a7ea4`,
  protocol hash `db34a8f2…`: **4 of 4 contacts, COMPLETED and FINALIZED**, 4 of 20 registered calls
  and 1,969.880708 of 6,000 registered speech seconds, server up in 10.0 s at `-c 49152 -np 2`.

**All four strata are servable**, including the first tier-7 `turn_00` user-turn wav this repository
has ever put on the wire, and every one of the three 654-second rows encoded through the bf16 mmproj
and returned.

**One shape finding worth carrying into the verdict: the 654-second rows are not speech.** The
tier-6 and tier-7 ones came back as prose refusals naming *"a dog eating"* and *"a dog drinking
water"*, which the official parser cannot read at all, and the tier-3 one parsed to a plausible but
wrong tool. The release's 654-second synthesis defect is junk audio, so all three are near-certain
misses in the flight — worth at most 0.15 pp of a 2,000-row roster, and named here so the verdict's
parse-failure count is not a surprise. No smoke accuracy figure enters the verdict.

Commit `6c13fb6d`.

### 2026-09-04, Phase 4 — the flight

Row `SAEA-A2T-TIER3467-OFFICIAL-POPULATION-V1`, attempt
`attempt-20260904T211040Z-t3467officialpop2000`, study commit `6c13fb6d`, manifest SHA-256
`1f43aab3520a0e4df0aa0b11693f518fda81b52e936e510f51c00713af016d58`, protocol hash `50d18adb…`. One
attempt, COMPLETED and FINALIZED, zero aborted, zero orphans, no recovery re-registration used,
`study_repo_dirt` empty. Spend was exactly **2,000 of 2,080 registered calls** (2,008 planned) and
**11,964.831167 of 12,100 registered speech-audio seconds**. GPU `enforced.power.limit` held
100.00 W before and after.

**All four tiers FAIL, and none is CONSISTENT-WITHIN-NOISE.** Official tool accuracy at n = 500 per
tier: tier 3 65.00 [61.42, 68.42] against 74.7; tier 4 28.20 [25.01, 31.62] against 33.4; tier 6
75.80 [72.52, 78.81] against 81.5; tier 7 49.40 [45.74, 53.07] against 54.6. The paper value lies
outside every one of the four CI90s, which is what n = 500 was bought for: at n = 50 all four of
these tiers sat *inside* the 3-point band and none of them could be believed.

Verdict: `docs/readiness/2026-09-04-a2t-tier3467-official-population-v1-verdict.md`; numbers in
`result-summary.json` (SHA-256
`b2f5dd5916206823e189baacd69706444593ceb3e96eb4e8278de7bc94b9807e`).

The substance is in the verdict; in one line each: all four failures are a `smart_home` effect and
equal-domain weighting would make all four ALIGNED (73.85 / 35.24 / 83.77 / 58.52, three of them
above the paper), which completes an eight-tier picture in which seven of eight tiers are inside the
band under equal-domain weighting and only tier 1 is not; every tier clears both published floors,
tier 7 by only 1.20 pp; tier 3's official/`v2` divergence is 40.20 points because all 500 of its gold
rows carry additional expected calls while the three single-call tiers agree to 0.00–0.40 pp; tier 7
was bound to the first user turn on all 500 rows while every one of the 2,146 tier-7 queries has
later user turns and the frozen 400 bound the final one; and 889 of 908 misses name another real
registry tool, with tier 4 the one tier whose misses cross domains more often than not.
