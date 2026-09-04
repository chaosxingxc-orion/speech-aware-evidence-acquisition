# Audio2Tool tiers-2/5/8 official population, v1 — preregistration

One run, profile `baseline-reproduction`, one cell. Written before any model contact.

| Run id | Cell | Population | Experiment fragment |
|---|---|---|---|
| `SAEA-A2T-TIER258-OFFICIAL-POPULATION-V1` | `T258-official-pop-1500` | A2T-TIER258-OFFICIAL-POP-1500 (1,500) | `configs/experiment/a2t-tier258-official-population-v1.json` |

Predecessor: `docs/readiness/2026-09-04-a2t-tier1-official-population-v1-verdict.md`
(run `SAEA-A2T-TIER1-OFFICIAL-POPULATION-V1`, cell `T1-official-pop-500`, attempt
`attempt-20260904T172609Z-t1officialpop500`, manifest SHA-256
`17acd0f4c1de9b5f4c658390fb67e8a6065f1628ff09b19bcd77afa47e7f99cf`, study commit `e61b424a`).

**One run id, unlike the tier-1 flight.** All three tiers fly in one roster with tier as the
stratum, so there is one population, one split identity hash and one exposure row.
`contracts.gate_exposure` requires exactly one pre-registered row per run id whose split identity
hash equals the plan's; the tier-1 flight needed two run ids because its two cells flew two
different populations, and that does not recur here.

## 1. Why this flight exists

The owner's standing requirement is that our per-tier number be within 3 points of
arXiv:2604.22821 Table 3 (Qwen-3-Omni-30B) or better, and never below a degraded model's published
number. On the frozen 400 — 50 rows per tier, Wilson CI90 about ±11 pp — the official scorer left
three tiers "not aligned" but undecidable:

| tier | frozen 400 (n = 50) | CI90 | paper | delta |
|---|---:|---|---:|---:|
| tier2_parametric | 74.0 | [62.8, 82.8] | 84.6 | −10.6 |
| tier5_needle | 78.0 | [67.1, 86.0] | 90.6 | −12.6 |
| tier8_intent_blending | 34.0 | [24.1, 45.6] | 41.7 | −7.7 |

(Tier 5's 78.0 is the sealed `R-official-raw` figure; the whitespace cell's own tier-5 row was
76.0. Neither changes the point: at n = 50 an 11-point interval cannot separate a 3-point rule.)

This flight buys resolution on exactly those three tiers with the paper code's own population rule
and n = 500 each. Tier 1 is done (`docs/readiness/2026-09-04-a2t-tier1-official-population-v1-verdict.md`).
Tiers 3, 4, 6 and 7 are not flown: on the frozen 400 they already sit inside the 3-point band
(tier 3 −0.7, tier 4 +0.6, tier 6 +0.5, tier 7 +5.4).

Nothing about the protocol is re-litigated. The request is the released code mirrored string for
string (`docs/receipts/environments/audio2tool-official-code.json`, commit
`b9d5383ca30945fbafb965a04bea40117e1e8a82`), byte-identical to `R-official-raw` and
`T1-official-pop-500`.

### The published rows this flight is judged against

| tier | Qwen-3-Omni-30B TA | EM | Slot F1 | Qwen-2.5-Omni-7B TA | weakest published SpeechLM TA |
|---|---:|---:|---:|---:|---:|
| tier2_parametric | 84.6 | 15.6 | 21.7 | 80.6 | 75.3 (Audio-Flamingo-8B) |
| tier5_needle | 90.6 | 36.0 | 41.6 | 74.1 | 58.9 |
| tier8_intent_blending | 41.7 | 12.4 | 19.9 | 36.5 | 30.4 |

## 2. Each tier's own population, derived from the pinned code

`BenchmarkEvaluator` with `max_speakers_per_query 1` evaluates `audio_paths[0]` for every query
directory a tier loader yields, walking `sorted(data_dir.glob("query_*"))`. The three tiers spell
`_get_audio_paths` differently, and the differences are recorded per tier rather than smoothed
over. Every claim below is verified in the roster receipt, directory by directory, not assumed.

**`tier2_parametric` — the tier-1 spelling exactly** (`tier2_dataset.py`): the rows of
`generation_results.csv` in file order whose `success` is true, resolving each row's `audio_path`
and falling back to `query_dir / Path(audio_path).name` when the CSV's absolute path is stale. The
released CSVs carry the authors' internal `/data2/Audio2ToolData/...` paths, so on any public copy
the documented fallback is the branch that fires. **3,160 query directories, 3,160 agreements with
the manifest-first pick, 0 disagreements, 0 unresolved.** No counterpart of tier 1's one
`query_01982` exception exists.

**`tier5_needle` — the same walk with the fallback missing** (`tier5_dataset.py`): it appends only
when `Path(audio_path).exists()`. Because `generation_results.csv` exists in every tier-5 query
directory the `else`-branch glob never runs either, so **a literal replay of the released tier-5
loader against the public release resolves ZERO audio paths**, `_load_query` returns `None` for all
2,146 directories, and the released tier-5 loader loads an empty dataset. This flight therefore
applies the tier-1/tier-2 spelling of the same walk — identical except for the documented fallback
— and the roster receipt records **both** replays: the literal one (0 rows resolved) and the
fallback one (**2,146 agreements, 0 disagreements, 0 unresolved**). This is deviation 3 of
section 4, not a silent repair.

**`tier8_intent_blending` — no speaker choice to make** (`tier8_dataset.py`): each query directory
ships exactly one `mixed.wav` (foreground and background intents mixed into one recording), there
is no `generation_results.csv` beside it, and every manifest row carries `speaker_idx` **`null`**.
The loader names `query_dir / "mixed.wav"` directly. **How the file-order rule resolved: trivially.**
All 821 directories ship that one file, the manifest carries exactly one row per directory, so
"first successful speaker" selects it everywhere and the released manifest and the released loader
cannot disagree. The receipt records the existence check over all 821.

For tiers 2 and 5 the public v1.0 release ships exactly **two** of the up-to-25 generated speakers
per query directory, and the tier manifest carries one item per shipped (query, speaker) recording
ordered by query directory then `speaker_idx`. The loader rule therefore selects the shipped
speaker with the lowest `speaker_idx` — the manifest row with the lowest `id` — and the builder
verifies that equivalence on every directory rather than assuming it.

Note also that `audio_benchmark/datasets/release_dataset.py`, the loader the release documents for
public users, expects a `metadata.jsonl` layout the v1.0 dataset release does not ship. It cannot
read the published dataset as distributed, so the tier loaders above are the only released code
that resolves these bytes at all.

### The draw

500 per tier, uniform without replacement, `random.Random(20260803).sample(population, 500)` over
each tier's population in ascending manifest-`id` (= sorted query-directory) order — the same call,
with the same seed, the tier-1 flight used. Each tier draws from its own freshly seeded generator
so a tier's draw does not depend on the tiers built before it. Roster receipt:
`docs/checks/speech-aware-evidence-acquisition/2026-09-04-a2t-tier258-official-population-roster/flight-roster-receipt.json`
(SHA-256 `9e17b44e0a6889f0dc710a2ec6293fc5c9ae0f5d38f6f10ca01f1c32e528a83a`), split identity hash
`9bd2e1c9…`, flight split identity hash `adb1cee2…`.

**`max_samples` is deliberately not used.** The release orders every subset
`smart_home → wearables → smart_car` (its own README says so), so `max_samples 500` over sorted
query directories would be a near-pure `smart_home` sample on tiers 2 and 5.

| tier | population | drawn | draw domain mix | population domain mix | draw audio (s) | longest row (s) |
|---|---:|---:|---|---|---:|---:|
| tier2_parametric | 3,160 | 500 | 370 / 108 / 22 | 2500 / 550 / 110 | 1,527.7175 | 10.376875 |
| tier5_needle | 2,146 | 500 | 368 / 91 / 41 | 1590 / 390 / 166 | 5,224.414375 | 32.43375 |
| tier8_intent_blending | 821 | 500 | 195 / 211 / 94 | 333 / 333 / 155 | 3,032.206 | 15.577 |
| **all three** | **6,127** | **1,500** | — | — | **9,784.337875** | **32.43375** |

Domain mixes are `smart_home / wearables / smart_car`. Population audio totals are 9,625.046 s,
22,436.219 s and 5,022.675 s. Tier 8's population is 821, so the draw covers 60.9 % of it; tiers 2
and 5 cover 15.8 % and 23.3 %.

**Overlap with the frozen 400.** By *query*: 12 of the 50 tier-2 queries, 13 of the 50 tier-5
queries and 32 of the 50 tier-8 queries are also drawn here. By *sample id*: 6, 7 and 32 — tiers 2
and 5 of the frozen 400 carry mixed speakers, so a shared query often means a different recording,
while tier 8 has only one recording per query and the two counts coincide. In total 77 of the 1,500
sample ids are already inside a committed probe-sample receipt (45 in `r1-audio2tool-sample.json`,
20 and 12 in the two 104-row post-seal AgentLoop scoring receipts). Nothing is re-drawn for them;
they are exposed rows being used again.

### Identity closure

- **Scoring identity.** 1,423 of the 1,500 sample ids are new to `data.audio2tool`'s
  frozen-receipt universe and enter it through
  `docs/receipts/probe-samples/a2t-tier258-official-population-1500.json` (SHA-256
  `818cec5890f96f1e59d34c095a694967ad9b9983488eb39e6e09b861fc2c4bfe`, split identity hash
  `3a03e75e…`, per tier 488 / 485 / 450). The other 77 already resolve through existing receipts,
  and `data.audio2tool._resolve_items` refuses a sample id that appears in two receipts, so
  repeating them would be a defect. Without this receipt `a2t-toolcall-official` refuses to score
  the roster at all.
- **Media identity.** 1,455 of the 1,500 are new to the immutable D1 identity closure and are
  carried by `docs/receipts/artifacts/d1-a2t-tier258-official-population-1500.json` (SHA-256
  `753eec5382b96a7d4993b2b9b3922aa9dd12192695b663b3e973db8084474391`, schema
  `saea-d1-media-supplement-v1`, 1,455 entries, 455,801,724 bytes). The 45 already inside
  `d1-identity.json` (6 tier-2, 7 tier-5, 32 tier-8) are verified against it byte for byte and
  skipped, because `contracts.gate_media_identity` refuses a supplement that duplicates a base D1
  sample.

Both receipts are model-free: identifiers, media paths, WAV byte hashes and container headers only.

## 3. The cell

| Cell | Roster | System message | Model fragment | Serving geometry |
|---|---|---|---|---|
| `T258-official-pop-1500` | A2T-TIER258-OFFICIAL-POP-1500 (1,500 rows) | the release's in-code default, unchanged from `R-official-raw` and `T1-official-pop-500` | `q4km-featcache-a2t-official-04ccc72a` | `-c 49152 -np 3`, 16,384 tokens/slot |

Shared and unchanged: `bare-core` arm, the `direct-only` phase program of
`rails.controllers.EvidenceAgentController` through `core.flight.FlightRuntime` and the OpenJiuwen
executor, entered through `scripts/flights/run_calibration_cell.py`; raw audio through the bf16
mmproj on build `04ccc72a`; the compact 152-row registry rendered by `format_tools_compact`; the
user turn's audio first and then `Convert this voice command to a tool call.`; temperature 0, seed
20260803, `max_tokens` 256, one contact per item, no evidence, no OBS.

**The longest wav was checked first, and it does not force `-np 2`.** The roster's longest row is
`tier5_needle:003555` at 32.43375 s, against the tier-1 official-population roster's 654.6325 s
release defect. Speech cost follows the mmproj encoder's exact one-second window rule
`n_tokens = 13 × ceil(audio_seconds)`, which reproduces all 400 per-packet `n_tokens` of the
A2T-CALIBRATION-400 promotion receipt without a single exception, so that row costs 429 speech
tokens and its request needs `3,581 text + 429 speech + 256 completion + 2 special = 4,268` tokens.
At the 49,152 total context this GPU is proven to serve on the raw path, `-np 3` leaves 12,116
tokens of margin against the preregistered 8,192-token reserve; `-np 4` would leave 8,020 and is
refused. So this cell serves the **same geometry `R-official-raw` and `W-official-raw-yaml` flew**,
and no new model fragment is created. The prompt-fit route re-proves the window rule and re-measures
this before any generation.

## 4. Deviations, recorded rather than fixed

The deviations of the replication and tier-1 preregistrations still stand where they apply. In
force here:

1. **Quantization and runtime.** Q4_K_M GGUF on llama.cpp build `04ccc72a` instead of the release's
   bf16 HuggingFace checkpoint. Unchanged, not flown here, and the subject of its own preregistered
   probe. It is the last of the three ranked Tier-1 suspects still open.
2. **Chat template.** The GGUF chat template under `--jinja`, not the HF `Qwen3OmniMoeProcessor`
   template. The prompt-fit route proves what it renders.
3. **The tier-5 loader cannot read the released tier-5 bytes.** Section 2. This flight applies the
   tier-1/tier-2 spelling of the same walk. If the authors ran tier 5 on their internal corpus, the
   fallback question never arose for them; from the release it is unanswerable, and it is the single
   largest residual uncertainty about the tier-5 cell.
4. **Population reconstruction generally.** The rule is derived from the pinned loaders and verified
   on 3,160 + 2,146 + 821 directories. If the authors evaluated their **internal** corpus (up to 25
   speakers per query on tiers 2 and 5) rather than the public release (two per query), "first
   successful speaker" resolves to a different wav for most queries. That is unknowable from the
   release.
5. **Tier 8's gold is the foreground call.** The released tier-8 loader reads the foreground
   fields of `query_metadata.json` and this repository's `load_official_gold` reads the manifest's
   top-level `tool_name` / `extracted_params` / `additional_tool_calls`, which are the same
   foreground fields; the `background_*` columns are never read. Unchanged from the frozen 400,
   where tier 8 already scored under this scorer.
6. **Sample rate.** Every Audio2Tool wav is 24 kHz mono 16-bit, not the 16 kHz its README claims.
   The release's own pipeline resamples with `librosa.load(..., sr=16000)`; llama.cpp's mmproj does
   its own resampling. The frozen 400 is the same material, so the comparison sits on identical
   footing.
7. **Serving geometry.** `-np`/`-c` have no counterpart in the release, which runs one request at a
   time on HF. Section 3 records the check that fixed it.
8. **Seed and temperature.** 20260803 and 0, both inert under greedy decoding, as before.
9. **Builder reuse.** The roster builder is new because the tier-1 one is hard-wired to one tier;
   the D1 media-supplement builder, the prompt-fit script, the flight entry point, the wire check
   and the scorers are the tier-1 flight's own, reused unchanged. No new script family.

## 5. Budget (ExecutionPlan)

| Run id | Calls (planned / ceiling) | Speech seconds (planned / ceiling) | GPU hours (planned / ceiling) |
|---|---|---|---|
| `SAEA-A2T-TIER258-OFFICIAL-POPULATION-V1` | 1,508 / 1,560 | 9,785 / 9,900 | 1.0 / 1.5 |
| `SAEA-A2T-TIER258-OFFICIAL-POPULATION-SMOKE-V1` | 12 / 20 | 200 / 250 | 0.2 / 0.2 |
| `SAEA-A2T-TIER258-OFFICIAL-POPULATION-PROMPT-FIT-V1` | 1 / 2 | 1 / 2 | 0.3 / 0.3 |
| **Flight total** | **1,521 / 1,582** | **9,986 / 10,152** | **1.5 / 2.0** |

Paid API spend 0 throughout. 1,508 = 1,500 rows + 8 canaries. The measured roster sum is
9,784.337875 s, rounded up to the integer `contracts.ExecutionPlan` requires and then to 9,785. The
smoke plan registers 12 rather than 4 calls because attempt budget is enforced run-cumulatively
(`core.model.adapter.FrozenCoreAdapter` re-reads every prior attempt's durable actuals for the run
id on every request), so a plan must cover prior spend plus its own worst case; 12 covers a clean
pass plus up to two recoveries. One-shot attempt semantics; at most one recovery re-registration
per flight; a second failure stops the flight and the fix is proven on a 4-row dry run.

## 6. Pre-contact prerequisites

1. **Roster and identity receipts** — the flight roster, the additive probe-sample receipt and the
   additive D1 media supplement, all three model-free and committed.
2. **Fragments** — dataset, experiment and smoke fragments composing cleanly against the existing
   `a2t-direct-official-protocol` baseline and `q4km-featcache-a2t-official-04ccc72a` model
   fragments, with `server_args` agreeing with `serving_geometry`.
3. **Prompt fit** — the exact request rendered through the pinned template on the resident server
   and measured, with its own exposure row, before any generation. Certification: every request fits
   its slot beside the 256-token completion ceiling with the 8,192-token reserve; the rendered system
   text equals the release's in-code-default spelling (16,143 chars, `be7f31a2…`) and the receipt
   records which variant matched. Speech cost comes from the one-second window rule, which the
   script PROVES against the A2T-CALIBRATION-400 promotion receipt before applying it.
4. **Exposure rows** — three, one per run id (prompt fit, smoke, flight), each registered with
   `consumed = no` before the contact it authorizes.
5. **Wire check and smoke** — `FlightRuntime.wire_check` on a clean committed tree (zero contacts),
   then a 4-row smoke. The smoke rows are fixed here, before they were read off the roster: the
   roster's lexicographically first sample plus the longest sample of each tier —
   `tier2_parametric:000005`, `tier2_parametric:004985`, `tier5_needle:003555`,
   `tier8_intent_blending:000209`. That covers all three strata, the first tier-8 `mixed.wav` and
   the first tier-5 needle wav this repository has served under the official protocol, and the
   flight's worst request.
6. **GPU power** — `nvidia-smi -q -d POWER` must report `enforced.power.limit` 100.00 W. A lower cap
   stops the flight (the Legion SmartFanMode note).

## 7. Decision rules — three outcomes per tier

The owner's alignment standard governs: **aligned means within 3 points of the official number, and
being better than the official number by more than 3 points is also acceptable.** The number is the
**official** scorer's tool accuracy (`a2t-toolcall-official`, the vendored
`metrics.compute_tool_accuracy` against the primary gold tool).

Per tier, independently:

- **ALIGNED** — official tool accuracy ≥ paper − 3.0: **tier 2 ≥ 81.6, tier 5 ≥ 87.6, tier 8 ≥ 38.7**
  (or better than the paper).
- **CONSISTENT-WITHIN-NOISE** — not ALIGNED, but the paper value lies inside the Wilson score CI90
  for a binomial proportion at n = 500.
- **FAIL** — neither.

**Floor rule, reported for every tier whatever the outcome.** Our number is tabled against
Qwen-2.5-Omni-7B (80.6 / 74.1 / 36.5) and against the weakest published SpeechLM row (75.3 / 58.9 /
30.4). A tier below a degraded model's published number is called out explicitly in the verdict.

**Power.** n = 500 gives a binomial standard error of 1.6 pp at p = 0.85, 1.3 pp at p = 0.91 and
2.2 pp at p = 0.42, so the 3 pp band is wider than the noise on all three tiers and ALIGNED is a
meaningful outcome rather than an artefact of a small sample. At n = 50 the standard error was
5–7 pp, which is exactly why these three tiers could not be decided on the frozen 400.

### Reported beside the decisions, none of them part of it

- Official exact match and parameter F1 (macro and micro) per tier, beside the paper's EM / Slot F1
  (15.6 / 21.7, 36.0 / 41.6, 12.4 / 19.9).
- **Tier 8 under both rules**: the official first-call rule and `a2t-toolcall-v2`'s ordered-sequence
  rule, with the count of rows whose response named more than one call. The tier-1 verdict showed
  these two rules diverge by 26 pp on tier 8 on the frozen 400, and the divergence is structural,
  not noise.
- The same per-tier tables under the extended `a2t-toolcall-v2`, with the official scorer beside it
  and the rule behind any gap wider than 3 points named.
- Per-domain breakdown per tier (`smart_home` / `wearables` / `smart_car`), natural mixture and
  equal-domain, as the tier-1 verdict did.
- Each tier against the frozen 400's own 50 rows of that tier, so the population effect is a
  difference rather than a replacement. This is not a paired contrast: the populations differ.
- Parse rate, and the count of rows naming more than one call, per tier.

## 8. Claim surface

Nothing here is a superiority, generality or Stage-3 claim. The population is discovery data and no
knob is tuned on it. Not authorized: any test contact, any mechanism arm, a Q8_0 flight (its own
preregistered probe), a training-free policy fit, any edit to the locked SLURP cell, and any
extension to tiers 1, 3, 4, 6 or 7.

## 9. Execution log

Filled in as the flight proceeds; every entry is written before the step it describes is read.

### 2026-09-04, Phase 1 — model-free preparation (zero contacts)

- Reconstructed and verified each tier's released population, drew the 1,500-row roster, and landed
  the additive probe-sample receipt and D1 media supplement.
- Landed the dataset, experiment and smoke fragments and the probe-manifest registration; no new
  model or baseline fragment was needed because the longest wav does not force `-np 2`.
- Found and recorded that the released `tier5_dataset.py` cannot read the released tier-5 dataset
  (section 2, deviation 3).
- Commit `394fe142`. `python scripts/checks/engineering_base_check.py`: PASS.
  `pytest tests/unit`: 6,021 passed, 6 failed — exactly the known pre-existing set (2 × `test_pemb3m`,
  2 × `test_pemb4r`, `test_bundle` CLI, and the full-suite-only registry-pollution failure in
  `test_engineering_base_check` that passes in isolation) — plus the known
  `test_build_a2t_g6_family_sweep` collection error from the verl `scripts` shadow.
- The three exposure rows were registered next, all `consumed = no`, before any contact
  (commit `92821da4`). GPU `enforced.power.limit` read 100.00 W before the first server was spawned.

### 2026-09-04, Phase 2 — prompt fit (zero generated tokens)

Row `SAEA-A2T-TIER258-OFFICIAL-POPULATION-PROMPT-FIT-V1`, registered before the server was touched.
One `GET /props`, one `POST /apply-template` and two `POST /tokenize`; no completion endpoint
touched, `generations` 0.

| Cell | System message | Text tokens | Worst required | Slot | Margin | Fits |
|---|---|---:|---:|---:|---:|:--:|
| `T258-official-pop-1500` | in-code-default, 16,143 chars, `be7f31a2…` | 3,581 | 4,268 (`tier5_needle:003555`) | 16,384 (`-np 3`) | 12,116 | yes |

Receipt:
`docs/checks/speech-aware-evidence-acquisition/2026-09-04-a2t-tier258-official-population-v1/prompt-fit/prompt-fit.json`
(SHA-256 `baf549f20fa6ee5a4e66c6c3c9922255bbabf6dfb2ee0280aebdeea62ce2bc42`).

Three findings carried forward:

1. **The rendered system message is the release's in-code default, verbatim.** 16,143 chars,
   `be7f31a2e8c7e6dd…` — the same bytes the sealed `R-official-raw` and `T1-official-pop-500` cells
   were certified against, and `system_text_verbatim_in_rendered_prompt` is true. 3,581 text tokens,
   identical to both.
2. **The window rule held on all 400 reference packets** (13 tokens per one-second window, zero
   disagreements) before it was applied to this unpreprocessed roster. Over the 1,500 rows it gives
   min 13, median 78, p95 169, max 429.
3. **`-np 3` is certified with room to spare.** Required window min 3,852, median 3,917, max 4,268;
   served-slot margin min 12,116 against the 8,192-token reserve; `largest_slot_count_meeting_reserve_at_this_context`
   is 3, so `-np 4` is refused by the rule and not by hand. The tier-1 cell's `-np 2` is not needed.

Commit `09418c64`.

### 2026-09-04, Phase 3 — wire check and smoke

- `FlightRuntime.wire_check` on a clean committed tree (`2846b11f`): **1,500 contacts** through the
  real client, adapter, payload binding and sealer against the fake gate and transport, **zero
  sockets opened, zero servers started**. `payload_keys` is exactly `ARM_VISIBLE_FIELDS["bare-core"]`
  (ten fields). `seal_and_score` OK with all four registered scorers through `core.scoring_batch` as
  one whole-manifest job over a 1,500-row outputs file. Receipt
  `wire-check/wire-check-t258-official-pop-1500.json` (SHA-256
  `b78bc66868fa4ec66ce9f529dd5009cb0b5aca3c22803ad1398fc32232744ea5`); commit `2846b11f`.
- Smoke row `SAEA-A2T-TIER258-OFFICIAL-POPULATION-SMOKE-V1`, attempt
  `attempt-20260904T193223Z-t258officialpop1500`, manifest SHA-256
  `c2b649e12690eaa9434abd6b84d57b622fb9ea597251b0affc75f16b5c593caa`, study commit `2846b11f`,
  protocol hash `2e9e5d20…`: **4 of 4 contacts, COMPLETED and FINALIZED**, 4 of 20 registered calls
  and 61.3245 of 250 registered speech seconds, server up in 10.0 s at `-c 49152 -np 3`.

**Both new strata are servable and both parse.** All four rows returned well-formed call strings and
parsed under `a2t-toolcall-official`, `a2t-toolcall-v2` and `a2t-toolcall` alike, with zero parse
failures: the 32.43375 s tier-5 needle wav (the flight's worst request) and the tier-8 `mixed.wav`
both encoded through the bf16 mmproj and returned. No smoke accuracy figure enters the verdict.

**One shape finding worth carrying into the verdict.** The tier-8 row named **three** calls in one
response, while the two tier-2 rows and the tier-5 row named one each. That is exactly the structure
the tier-1 verdict identified as the source of the official/`v2` divergence on tiers 3 and 8 — the
official scorer reads only the first parsed call — so section 7's "tier 8 under both rules" slice is
not hypothetical.

Commit `b52c22b0`.

### 2026-09-04, Phase 4 — the flight

Row `SAEA-A2T-TIER258-OFFICIAL-POPULATION-V1`, attempt
`attempt-20260904T193726Z-t258officialpop1500`, study commit `b52c22b0`, manifest SHA-256
`7de7429110e978784fc8303e632c54360d9cdbb70aa61e9d084b957f68db847f`, protocol hash `4c7db9dc…`. One
attempt, COMPLETED and FINALIZED, zero aborted, zero orphans, no recovery re-registration used,
`study_repo_dirt` empty. Spend was exactly **1,500 of 1,560 registered calls** (1,508 planned) and
**9,784.337875 of 9,900 registered speech-audio seconds**. GPU `enforced.power.limit` held 100.00 W
before and after.

**Tier 8 is ALIGNED; tiers 2 and 5 FAIL.** Official tool accuracy at n = 500 per tier: tier 2 79.60
[76.48, 82.40] against 84.6; tier 5 80.80 [77.74, 83.53] against 90.6; tier 8 **46.80** [43.16,
50.48] against 41.7. Neither failing tier is CONSISTENT-WITHIN-NOISE — the paper value is outside
both CI90s, which is what n = 500 was bought for.

Verdict: `docs/readiness/2026-09-04-a2t-tier258-official-population-v1-verdict.md`; numbers in
`result-summary.json` (SHA-256
`42a88f0d2ae81a168115c729725b99be8749559cf28047fe3b8e76bf4065956f`).

The substance is in the verdict; in one line each: both failures are a `smart_home` effect
(equal-domain weighting gives tier 2 85.44 against 84.6 and tier 5 89.75 against 90.6), tier 2 is the
one tier below a degraded model's published floor (−1.00 pp against Qwen-2.5-Omni-7B, whose 80.6 is
inside our CI90), our exact match beats the published exact match on tiers 2 and 8 by 15.6 and 10.0
points, the official and v2 scorers agree to 0.00 pp on both single-call tiers and diverge by 31
points on tier 8 (496 of 500 gold rows carry additional calls, 215 of 500 responses name more than
one), and 460 of 464 misses name another real tool of the 152-row registry.
