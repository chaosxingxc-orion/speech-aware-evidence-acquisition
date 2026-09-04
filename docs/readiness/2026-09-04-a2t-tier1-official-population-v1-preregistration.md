# Audio2Tool tier-1 official population, v1 — preregistration

Two runs, both profile `baseline-reproduction`, one cell each. Written before any model contact of
either.

| Run id | Cell | Population | Experiment fragment |
|---|---|---|---|
| `SAEA-A2T-TIER1-OFFICIAL-POPULATION-V1` | `T1-official-pop-500` | A2T-TIER1-OFFICIAL-POP-500 (500) | `configs/experiment/a2t-tier1-official-population-v1.json` |
| `SAEA-A2T-TIER1-OFFICIAL-POPULATION-WHITESPACE-V1` | `W-official-raw-yaml` | A2T-CALIBRATION-400 (400) | `configs/experiment/a2t-tier1-official-population-whitespace-v1.json` |

**Why two run ids for one experiment.** `contracts.gate_exposure._require_exposure_preregistration`
requires exactly one pre-registered exposure row per run id and refuses a plan whose split identity
hash differs from that row's. A run id therefore cannot span two populations, and these two cells
fly different ones. The gate refused the first attempt at a single-run-id design on 2026-09-04 and
the design was corrected, not the gate. Everything else is shared: one preregistration, one
harness, one entry point, one verdict, one pair of scorers.

Predecessor: `docs/readiness/2026-09-04-a2t-official-protocol-replication-v1-verdict.md`
(run `SAEA-A2T-OFFICIAL-PROTOCOL-REPLICATION-V1`, cell `R-official-raw`, attempt
`attempt-20260904T135250Z-rofficialraw`, manifest SHA-256
`64d0759d6cb117574e4bfdb23c3b6832b5bde7434990b74b859f56aa145a2401`, study commit `7eb4aa00`).

## 1. Why this flight exists

The 2026-09-04 replication flew the released Audio2Tool protocol mirrored string for string and
still missed the published Tier-1 row by 32.4 pp — 60.0 % against 92.4 % — while seven of the
eight tiers landed between −12.6 and +3.4 pp. That verdict named three remaining suspects and
ranked them:

1. **the roster** — the frozen 400 is 50 stratified rows per tier over 374 distinct `query_idx`
   with mixed speakers; the release evaluates the **first successful speaker of every query of
   every tier**;
2. **quantization** — Q4_K_M against the release's bf16 (a separate preregistered probe, not this
   flight);
3. **the system-prompt whitespace variant** — the released code carries the same four sentences
   twice, once space-separated in the adapter's own default and once as a newline-separated YAML
   block scalar that `run_benchmark.py` passes whenever a config file is used.

This flight closes 1 and 3 on the same harness, the same request and the same scorers. Nothing
about the protocol is re-litigated: it is the released code mirrored string for string
(`docs/receipts/environments/audio2tool-official-code.json`, commit
`b9d5383ca30945fbafb965a04bea40117e1e8a82`).

### The published row (arXiv:2604.22821 Table 3, Qwen3-Omni-30B)

| tier | tool accuracy | exact match | R-official-raw (n=50) |
|---|---:|---:|---:|
| tier1_direct | 92.4 | 92.4 | **60.0** |
| tier2_parametric | 84.6 | 15.6 | 74.0 |
| tier3_multi_intent | 74.7 | 28.6 | 72.0 |
| tier4_implicit | 33.4 | 11.3 | 28.0 |
| tier5_needle | 90.6 | 36.0 | 78.0 |
| tier6_correction | 81.5 | 24.8 | 84.0 |
| tier7_multiturn | 54.6 | 16.3 | 58.0 |
| tier8_intent_blending | 41.7 | 12.4 | 34.0 |

## 2. The release's own tier-1 population, derived from the pinned code

`audio_benchmark/datasets/tier1_dataset.py` walks `sorted(data_dir.glob("query_*"))` and, per
query directory, keeps the rows of `generation_results.csv` **in file order** whose `success` is
true, resolving each row's `audio_path` and falling back to `query_dir / Path(audio_path).name`
when the CSV's absolute path is stale. `BenchmarkEvaluator` with `max_speakers_per_query 1` then
evaluates `audio_paths[0]`.

Three facts about the released bytes make that rule concrete, and all three are verified in the
roster receipt rather than assumed:

1. **The CSVs are stale on every public copy.** Their `audio_path` cells carry the authors'
   internal `/data2/Audio2ToolData/...` paths, so the loader's documented fallback is the branch
   that actually fires.
2. **The release ships two of the up-to-25 generated speakers per tier-1 query.** The CSVs list
   25 rows; the directory holds two wavs. `audio_paths[0]` is therefore the shipped speaker with
   the lowest `speaker_idx`, which is the tier manifest's lowest-`id` row for that directory.
   `scripts/build_a2t_tier1_official_population_roster.py` replays the loader on all 2,146
   directories and compares: **2,145 agreements, 0 disagreements.**
3. **One directory is an exception.** `query_01982`'s `generation_results.csv` names 25 speaker
   filenames, none of which is either wav the release ships beside it: its CSV belongs to a
   different synthesis batch. The internal loader would resolve no audio and skip that query; the
   released manifest is unambiguous. This flight treats the **manifest** as authoritative, so the
   population is the full 2,146, and the exception is recorded in the receipt so a reader can
   subtract it.

Note also that `audio_benchmark/datasets/release_dataset.py` — the loader the release documents
for public users — expects a `metadata.jsonl` layout the v1.0 dataset release does not ship
(`<subset>_data/` + `<subset>_audios/`). It cannot read the published dataset as distributed, so
the tier loaders above are the only released code that resolves these bytes at all.

### The draw

500 of the 2,146, uniformly without replacement, `random.Random(20260803).sample(population, 500)`
over the population in ascending manifest-`id` (= sorted query-directory) order. Roster receipt:
`docs/checks/speech-aware-evidence-acquisition/2026-09-04-a2t-tier1-official-population-roster/flight-roster-receipt.json`
(SHA-256 `07a6931614709394a697f00fb676f545225a63a254c9cd620bc63f7a9f76f8cd`), split identity hash
`23d32ac8…`, flight split identity hash `4d22744c…`.

**`max_samples` is deliberately not used.** The release orders every subset
`smart_home → wearables → smart_car` (its own README says so), so `max_samples 500` over sorted
query directories would be a pure `smart_home` sample. The draw's domain mix is
`smart_home 368 / wearables 91 / smart_car 41` against a population of `1590 / 390 / 166` — 73.6 /
18.2 / 8.2 % against 74.1 / 18.2 / 7.7 %.

**Overlap with the frozen 400.** Twelve of the 500 drawn *queries* are also among the 50 tier-1
queries of the frozen 400, and eleven of the 500 *sample ids* are already inside a committed
probe-sample receipt (five in `r1-audio2tool-sample.json`, three in each of the two 104-row
post-seal AgentLoop scoring receipts). Nothing is re-drawn for them; they are exposed rows being
used again.

**One row is a release defect and is kept anyway.** `tier1_direct:003943` (query_idx 4551,
`query_01972`) ships a 654.6325 s wav for a four-word query — 18× longer than anything this
repository has served and 39 % of the roster's whole audio budget. The released population
contains it and the paper's Tier-1 row was computed over a population that contains it, so it is
flown. Section 6 item 5 carries the contingency for a runtime that cannot serve it.

### Identity closure

- **Scoring identity.** 489 of the 500 sample ids are new to `data.audio2tool`'s frozen-receipt
  universe and enter it through `docs/receipts/probe-samples/a2t-tier1-official-population-500.json`
  (SHA-256 `66ddb74326c1089f40d26649d43c258459e7fb9e0d348f70ec26f32ea509972f`). The other 11 already
  resolve through existing receipts, and `data.audio2tool._resolve_items` refuses a sample id that
  appears in two receipts, so repeating them would be a defect. Without this receipt
  `a2t-toolcall-official` refuses to score the roster at all.
- **Media identity.** 495 of the 500 are new to the immutable D1 identity closure and are carried
  by `docs/receipts/artifacts/d1-a2t-tier1-official-population-500.json` (SHA-256
  `1976d6b5192a4dff15af46a9225cd5cbd61aa09bd0ce31c0036172d9e43acd3c`, schema
  `saea-d1-media-supplement-v1`, 495 entries, 79,615,802 bytes). The 5 already inside
  `d1-identity.json` are verified against it byte for byte and skipped, because
  `contracts.gate_media_identity` refuses a supplement that duplicates a base D1 sample.

Both receipts are model-free: identifiers, media paths, WAV byte hashes and container headers only.

## 3. The two cells

| Cell | Roster | System message | Model fragment | Serving geometry |
|---|---|---|---|---|
| `T1-official-pop-500` | A2T-TIER1-OFFICIAL-POP-500 (500 rows) | the release's in-code default, unchanged from `R-official-raw` | `q4km-featcache-a2t-official-np2-04ccc72a` | `-c 49152 -np 2`, 24,576 tokens/slot |
| `W-official-raw-yaml` | A2T-CALIBRATION-400 (the frozen 400) | the release's `configs/example_config.yaml` block-scalar spelling | `q4km-featcache-a2t-official-04ccc72a` | `-c 49152 -np 3`, 16,384 tokens/slot |

Shared and unchanged from `R-official-raw`: `bare-core` arm, `direct-only` phase program of
`rails.controllers.EvidenceAgentController` through `core.flight.FlightRuntime` and the OpenJiuwen
executor, entered through `scripts/flights/run_calibration_cell.py`; raw audio through the bf16
mmproj on build `04ccc72a`; the compact 152-row registry rendered by `format_tools_compact`; the
user turn's audio first and then `Convert this voice command to a tool call.`; temperature 0, seed
20260803, `max_tokens` 256, one contact per item, no evidence, no OBS.

**Why T1 serves two slots instead of three.** Purely the 654.6325 s row. Speech cost follows the
mmproj encoder's exact one-second window rule `n_tokens = 13 × ceil(audio_seconds)`, which
reproduces **all 400** per-packet `n_tokens` of the A2T-CALIBRATION-400 promotion receipt without a
single exception, so that row costs 8,515 speech tokens and its request needs
`3,581 text + 8,515 speech + 256 completion + 2 special = 12,354` tokens. At the 49,152 total
context this GPU is proven to serve on the raw path, `-np 2` leaves 12,222 tokens of margin and
`-np 3` leaves 4,030 — short of the preregistered 8,192-token reserve, so `-np 3` is refused. The
request bytes are identical either way; only batching changes.

**Why W keeps three slots.** `W-official-raw-yaml` must be byte-identical to the sealed
`R-official-raw` cell except for the system prompt's whitespace, and that includes the serving
geometry, so the paired contrast is a contrast in whitespace alone.

## 4. Deviations, recorded rather than fixed

The ten deviations of the replication preregistration (section 4) all still stand, except that
deviation 4 (roster) is exactly what `T1-official-pop-500` removes and deviation 9 (system-prompt
whitespace) is exactly what `W-official-raw-yaml` resolves. New or newly measured:

1. **Quantization and runtime.** Q4_K_M GGUF on llama.cpp build `04ccc72a` instead of the
   release's bf16 HuggingFace checkpoint. Unchanged, not flown here, and the subject of its own
   preregistered probe.
2. **Chat template.** The GGUF chat template under `--jinja`, not the HF
   `Qwen3OmniMoeProcessor` template. The prompt-fit route proves what it renders.
3. **Sample rate.** Every Audio2Tool wav is 24 kHz mono 16-bit, not the 16 kHz its README claims.
   The release's own pipeline resamples with `librosa.load(..., sr=16000)`; llama.cpp's mmproj does
   its own resampling. The frozen 400 the replication flew is the same 24 kHz material, so the two
   rosters sit on identical footing and this changes nothing about the comparison — it is recorded
   because it is a fact about the released bytes that the README gets wrong.
4. **Tier-1 population reconstruction.** The rule is derived from `tier1_dataset.py` and verified
   against 2,146 directories, with one documented exception (section 2). If the authors' own run
   used the internal corpus (25 speakers per query) rather than the public release (2 per query),
   "first successful speaker" resolves to a different wav for most queries. That is unknowable from
   the release and is the single largest residual uncertainty about this cell.
5. **One 654.6325 s row.** Kept for fidelity; section 6 item 5 carries the contingency.
6. **Serving geometry.** `-np`/`-c` have no counterpart in the release, which runs one request at
   a time on HF; T1 and W serve different slot counts for the reason in section 3.
7. **Seed and temperature.** 20260803 and 0, both inert under greedy decoding, as before.

## 5. Budget (ExecutionPlan)

Per run id, because the budget contract and the exposure gate are both per run id.

| Run id | Calls (planned / ceiling) | Speech seconds (planned / ceiling) | GPU hours (planned / ceiling) |
|---|---|---|---|
| `SAEA-A2T-TIER1-OFFICIAL-POPULATION-V1` | 508 / 540 | 1,700 / 1,750 | 1.0 / 1.2 |
| `SAEA-A2T-TIER1-OFFICIAL-POPULATION-WHITESPACE-V1` | 408 / 410 | 2,200 / 2,250 | 0.5 / 0.8 |
| `SAEA-A2T-TIER1-OFFICIAL-POPULATION-SMOKE-V1` | 12 / 20 | 2,000 / 2,050 | 0.2 / 0.2 |
| `SAEA-A2T-TIER1-OFFICIAL-POPULATION-WHITESPACE-SMOKE-V1` | 12 / 20 | 68 / 100 | 0.2 / 0.2 |
| `SAEA-A2T-TIER1-OFFICIAL-POPULATION-PROMPT-FIT-V1` | 1 / 2 | 1 / 2 | 0.3 / 0.3 |
| `SAEA-A2T-TIER1-OFFICIAL-POPULATION-WHITESPACE-PROMPT-FIT-V1` | 1 / 2 | 1 / 2 | 0.3 / 0.3 |
| **Flight total** | **916 / 950** | **3,900 / 4,000** | **1.5 / 2.0** |

Paid API spend 0 throughout. 508 = 500 rows + 8 canaries; 408 = 400 rows + 8 canaries. The smoke
plans register 12 rather than 4 calls because attempt budget is enforced run-cumulatively
(`core.model.adapter.FrozenCoreAdapter` re-reads every prior attempt's durable actuals for the run
id on every request), so a plan must cover prior spend plus its own worst case; 12 covers a clean
pass plus up to two recoveries. The T1 smoke's 2,000 s is almost entirely the single 654.6325 s row
it exists to test. One-shot attempt semantics; at most one recovery re-registration per flight; a
second failure stops the flight and the fix is proven on a 4-row dry run.

## 6. Pre-contact prerequisites

1. **Roster and identity receipts** — the flight roster, the additive probe-sample receipt and the
   additive D1 media supplement, all three model-free and committed. DONE (commit `ee8857b4`).
2. **Fragments** — dataset, baseline (both spellings), model (both geometries), experiment and
   smoke fragments, composing cleanly and with `server_args` agreeing with `serving_geometry`.
   DONE (commit `ee8857b4`).
3. **Prompt fit** — the exact request of each cell rendered through the pinned template on the
   resident server and measured, with its own exposure row, before any generation. Certified per
   cell: every request fits its slot beside the 256-token completion ceiling with the 8,192-token
   reserve; the rendered system text equals one of the release's own two spellings, and the receipt
   records which; both spellings' hashes are recorded. Speech cost for the T1 roster comes from the
   one-second window rule, which the script PROVES against the A2T-CALIBRATION-400 promotion
   receipt before applying it.
4. **Exposure rows** — six, one per run id (two prompt fits, two smokes, two flights), each
   registered with `consumed = no` before the contact it authorizes.
5. **Wire check and smoke** — `FlightRuntime.wire_check` on a clean committed tree (zero contacts),
   then a 4-row smoke per cell. The T1 smoke deliberately includes `tier1_direct:003943`, the
   654.6325 s row, because it is the only request in this flight with no precedent.
   **Long-row contingency, registered now:** if that row cannot be served by the pinned runtime
   (encode failure, timeout, or a request that does not fit its slot), the flight is not launched
   with a silent 499. The exclusion is registered with its cause before the flight, the cell flies
   the remaining 499, and the verdict reports tier-1 on n = 499 with the exclusion named.
6. **GPU power** — `nvidia-smi -q -d POWER` must report `enforced.power.limit` 100.00 W. A lower
   cap stops the flight (the Legion SmartFanMode note).

## 7. Decision rules — three outcomes per cell

The owner's 2026-09-04 alignment standard governs: **aligned means within 3 points of the official
number, and being better than the official number by more than 3 points is also acceptable.** The
number is the **official** scorer's tool accuracy (`a2t-toolcall-official`, the vendored
`metrics.compute_tool_accuracy` against the primary gold tool).

### `T1-official-pop-500`

- **ALIGNED** — official tier-1 tool accuracy ≥ 89.4 (within 3 pp of the paper's 92.4, or better).
- **CONSISTENT-WITHIN-NOISE** — not ALIGNED, but 92.4 lies inside the Wilson score CI90 for a
  binomial proportion at n = 500.
- **FAIL** — neither.

**Power.** n = 500 gives a binomial standard error of 1.2 pp at p = 0.92 and 2.2 pp at p = 0.5, so
the 3 pp band is wider than the noise and ALIGNED is a meaningful outcome rather than an artefact
of a small sample. At n = 500 the Wilson CI90 around an observed 0.60 is roughly [0.564, 0.636], so
CONSISTENT-WITHIN-NOISE is essentially unreachable if the point estimate stays near the
replication's 60.0 — which is the point: this cell can no longer hide behind sampling noise.

### `W-official-raw-yaml`

- **ALIGNED** — per-tier official tool accuracy within 3 pp of the paper row, or better, on tiers
  1, 2, 5 and 6.
- **CONSISTENT-WITHIN-NOISE** — not ALIGNED, but the paper value lies inside the tier's Wilson CI90
  (n = 50) on all four.
- **FAIL** — neither.

Reported regardless, and the reason this cell exists: the **paired contrast against the sealed
`R-official-raw` manifest** over the same 400 rows, the same official scorer and the same official
gold — per-tier deltas, saves/harms/ties, sign test, and a tier-stratified paired bootstrap CI90
(10,000 replicates, seed 20260903). The whitespace question is answered by that contrast whatever
label the tiers earn. Under a 400-row paired design a whitespace effect smaller than about 4 pp is
not separable from noise, and the prior expectation is that the effect is zero.

### Extension contingency, registered now

If `T1-official-pop-500` is **ALIGNED**, a second registered attempt extends the SAME cell to the
remaining 1,646 tier-1 queries (roster part `remainder`,
`flight-roster-receipt-remainder.json`, SHA-256
`828979157ecd618d03fd84ccdceadb13041baea270f476b6b95cef0ef7b3fda4`) so the reported number is the
full official population. That extension is its own re-registration with its own plan (1,646 rows
+ 8 canaries) and its own exposure ceiling. If `T1-official-pop-500` is not ALIGNED, no extension
is flown.

### Reported beside the decisions, none of them part of it

- The same per-tier tables under the extended `a2t-toolcall-v2`, with the official scorer beside it
  and the rule behind any gap wider than 3 points named.
- Official exact match and parameter F1 (macro and micro) per tier; parse rate; the count of rows
  whose response named more than one call.
- `T1-official-pop-500` by domain (`smart_home` / `wearables` / `smart_car`), natural mixture and
  equal-domain.
- `T1-official-pop-500` against the frozen 400's own 50 tier-1 rows, so the roster effect is a
  difference rather than a replacement.

## 8. Claim surface

Nothing here is a superiority, generality or Stage-3 claim. The population is discovery data and no
knob is tuned on it. Not authorized: any test contact, any mechanism arm, a Q8_0 flight (its own
preregistered probe), a training-free policy fit, or any edit to the locked SLURP cell.

## 9. Zero-contact companion, registered separately

`SAEA-A2T-MF-PARSE-EXTENSION-RESCORE-V1` extends
`reproduction.toolcall_scoring.parse_tool_calls_text` to read the released call-string contract as
well as the reconstructed JSON-array one and re-scores the sealed manifests. It has no model, GPU
or network contact and is not part of this flight's budget; its receipt is
`docs/checks/speech-aware-evidence-acquisition/2026-09-04-a2t-parse-extension-rescore/rescore.json`.

## 10. Execution log

Filled in as the flight proceeds; every entry is written before the step it describes is read.

### 2026-09-04, Phase 1 — model-free preparation (zero contacts)

- Reconstructed and verified the release's own tier-1 population, drew the 500-row roster and the
  1,646-row remainder, and landed the additive probe-sample receipt and D1 media supplement.
- Landed the whitespace template, the four config fragments and the two experiment fragments.
- Extended the shared tool-call parse to read both output contracts and re-scored every sealed
  Audio2Tool manifest under it (zero contacts).
- Commit `ee8857b4`. `python scripts/checks/engineering_base_check.py`: PASS.
  `pytest tests/unit`: 6,012 passed, 6 failed — exactly the known pre-existing set (2 × `test_pemb3m`,
  2 × `test_pemb4r`, `test_bundle` CLI, and the full-suite-only registry-pollution failure in
  `test_engineering_base_check` that passes in isolation) — plus the known
  `test_build_a2t_g6_family_sweep` collection error from the verl `scripts` shadow.

### 2026-09-04, Phase 2 — prompt fit (zero generated tokens)

Rows `SAEA-A2T-TIER1-OFFICIAL-POPULATION-PROMPT-FIT-V1` and
`SAEA-A2T-TIER1-OFFICIAL-POPULATION-WHITESPACE-PROMPT-FIT-V1`, both registered before the server
was touched.

**One correction, recorded because it changed the run structure.** The first prompt-fit invocation
for the whitespace cell was refused by `contracts.gate_exposure`: the plan carried the frozen 400's
split identity hash while the single registered row carried the tier-1 roster's, and the gate
requires exactly one pre-registered row per run id whose hash equals the plan's. The cause was the
design, not the gate — one run id cannot span two populations — so the experiment was split into
two run ids with two fragments, two plans and two ledger rows, and the T1 prompt fit was re-run
against the corrected fragment bytes. No model contact was made under the refused plan; the refusal
happened before the server was spawned.

**Both fits certified, zero generated tokens.** One `GET /props`, one `POST /apply-template` and
two `POST /tokenize` per run; no completion endpoint touched.

| Cell | System message | Text tokens | Worst required | Slot | Margin | Fits |
|---|---|---:|---:|---:|---:|:--:|
| `T1-official-pop-500` | in-code-default, 16,143 chars, `be7f31a2…` | 3,581 | 12,354 (`tier1_direct:003943`) | 24,576 (`-np 2`) | 12,222 | yes |
| `W-official-raw-yaml` | example-config-yaml, 16,144 chars, `eab51383…` | 3,581 | 4,307 (`tier7_multiturn:001590`) | 16,384 (`-np 3`) | 12,077 | yes |

Receipts: `prompt-fit/tier1-pop-500/prompt-fit.json` (SHA-256
`2b45b78b382dd6cff689124222ff0b64363dfdaab79963eea3fd96891fa63f1e`) and
`prompt-fit/whitespace-400/prompt-fit.json` (SHA-256
`9c23e0c546afa7f8e9ba9576599c73af31c06ff98f183600bf0851d209666132`), both under
`docs/checks/speech-aware-evidence-acquisition/2026-09-04-a2t-tier1-official-population-v1/`.
Commit `e766b8da`.

Three findings carried forward:

1. **Both system messages appear verbatim in the rendered prompt**, and each matches one of the
   release's own two spellings; the receipt records which, so neither cell can silently send the
   other's bytes.
2. **The whitespace change costs zero tokens.** Both spellings render to exactly 3,581 text tokens
   through the pinned template, so the two cells' envelopes are identical and any outcome
   difference in `W-official-raw-yaml` cannot be a context-length effect.
3. **The window rule held on all 400 reference packets** (13 tokens per one-second window, zero
   disagreements), so the T1 fit rests on the mmproj encoder's measured behaviour rather than on an
   estimate. Over the 500 rows it gives min 13, median 26, p95 52, max 8,515 — that maximum is the
   654.6325 s row, and it is the only reason `T1-official-pop-500` serves two slots.

### 2026-09-04, Phase 3 — wire check and smoke

- `FlightRuntime.wire_check` for both cells on clean committed trees (`767e8405` for
  `T1-official-pop-500`, `3aa45f28` for `W-official-raw-yaml`): 500 and 400 contacts through the
  real client, adapter, payload binding and sealer against the fake gate and transport, zero
  sockets opened. `payload_keys` is exactly `ARM_VISIBLE_FIELDS["bare-core"]` on both.
  `seal_and_score` OK with all four registered scorers through `core.scoring_batch` as one
  whole-manifest job. Receipts under `wire-check/`; commits `3aa45f28` and `0c4f06eb`.
  **One defect and its fix:** the whitespace cell's first wire check reported `SCORING_FAILED`
  because the T1 wire check had just written its receipt into a previously untracked directory, and
  `core.scorers._assert_scoring_entry_gate` refuses to score against a dirty tree. The gate is
  right — a run manifest must bind the exact commit that produced the run — so the T1 receipt was
  committed first and the whitespace wire check re-run on the clean tree. Nothing was changed except
  the order of operations.
- Smoke rows `SAEA-A2T-TIER1-OFFICIAL-POPULATION-SMOKE-V1` (attempt
  `attempt-20260904T172215Z-t1officialpop500`, manifest SHA-256 `dd3ef14e7a25…`) and
  `SAEA-A2T-TIER1-OFFICIAL-POPULATION-WHITESPACE-SMOKE-V1` (attempt
  `attempt-20260904T172359Z-wofficialrawyaml`, manifest SHA-256 `b5530a724d8e…`), both 4 of 4
  contacts, FINALIZED, study commit `0c4f06eb`.

**The smoke's decisive finding: the 654.6325 s row is servable.** `tier1_direct:003943` encoded
through the bf16 mmproj and returned a well-formed call string, so the long-row contingency of
section 6 item 5 does **not** fire and the flight goes with all 500 rows.

**Second finding: this repository's own scorers can finally read its own official-protocol runs.**
All eight smoke rows produced call strings and parsed under `a2t-toolcall`, `a2t-toolcall-v2` and
`a2t-toolcall-official` alike, with zero parse failures — the parse extension working end to end,
against the replication flight's 400 parse failures under v1/v2. No smoke accuracy figure enters
the verdict.

The two cells produced **different protocol hashes** (`abb9c4cd…` for the in-code default,
`9ab1df16…` for the YAML variant), which is what a genuine difference in the system-prompt bytes
should produce and is a second, independent confirmation that the whitespace cell is not silently
sending the default spelling.

### 2026-09-04, Phase 4 — the flights

Rows `SAEA-A2T-TIER1-OFFICIAL-POPULATION-V1` (500 rows, attempt
`attempt-20260904T172609Z-t1officialpop500`, manifest SHA-256 `17acd0f4c1de…`) and
`SAEA-A2T-TIER1-OFFICIAL-POPULATION-WHITESPACE-V1` (400 rows, attempt
`attempt-20260904T173219Z-wofficialrawyaml`, manifest SHA-256 `051ae145a7f9…`), both on study
commit `e61b424a`, one attempt each, FINALIZED, zero aborted, zero orphans, no recovery
re-registration used. Spend was exactly 500 of 540 and 400 of 410 registered calls, and
1,668.914042 of 1,750 and 2,159.688 of 2,250 registered speech-audio seconds. GPU
`enforced.power.limit` held 100.00 W before and after both.

**Both cells FAIL the section-7 rules**, and the extension contingency does not fire. Verdict:
`docs/readiness/2026-09-04-a2t-tier1-official-population-v1-verdict.md`; numbers in
`result-summary.json` (SHA-256
`4aa4941195866a4c568369d164ef33ff6ea0ec8d8434fd1157099f47baf67837`).

The substance is in the verdict; in one line each: the roster is worth +5.6 pp rather than +32, the
whitespace variant is worth nothing (+1.00 pp, sign test p = 0.5034, 380 of 400 rows tied), and at
n = 500 tier 1 splits by domain — `wearables` 93.41 and `smart_car` 92.68 sit on the published 92.4
while `smart_home`, 368 of the 500 rows, sits at 55.71.
