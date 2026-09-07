# Preregistration — should the study standardize Audio2Tool's input rate to 16 kHz itself?

**NOT AUTHORIZED. NOT FLOWN.** Two single-factor cells on the Audio2Tool frozen 400, each paired
against the same sealed official-protocol comparator on the same rows. Written before either exists
and before any number from either is read. Each cell needs its own owner GO and its own exposure
row; both are blocked by one shared precondition that this preparation deliberately did not build,
and §7 names it with the exact line it stops at.

The media is built and committed. Row `SAEA-SN-MF-A2T-CAL400-16K-MEDIA-V1`; builder
`scripts/build_a2t_input_rate_16k_media.py`; receipts under
`docs/checks/speech-aware-evidence-acquisition/2026-09-07-a2t-calibration-400-16k{,-tail2s}-media/`.
The resampler read this rests on is `docs/readiness/2026-09-07-a2t-input-rate-audit-v1.md`
(row `SAEA-A2T-MF-INPUT-RATE-AUDIT-V1`).

---

## 0. What is being asked, and why it is worth asking

The owner rule of 2026-09-07 is to **standardize every input clip to a rate the model can handle,
such as 16 kHz, with `librosa`**. The audit of the same day establishes what that would replace.

Every Audio2Tool release wav is **24 kHz mono**; the Qwen3-Omni front end hard-codes **16 kHz**
(`clip.cpp:1552`); and **nothing in this study converts between them**. `core/model/transport.py:295`
base64s the sealed bytes verbatim, llama.cpp forwards them untouched, and the conversion happens
inside miniaudio 0.11.25's `ma_resample_algorithm_linear` — **the algorithm miniaudio itself labels
"Fastest, lowest quality"** (`vendor/miniaudio/miniaudio.h:5403`): two-tap linear interpolation
preceded by a 4th-order Butterworth at 8 kHz.

**Audio2Tool is the only carrier in this study where that happens.** Earnings-21, Earnings-22 and
SLURP media are already 16 kHz, because this study converts them itself with the very
`librosa`/`soxr_hq` path the owner rule names.

Measured on synthetic tones against a −9.031 dBFS reference (audit §3):

| | llama.cpp miniaudio linear | study librosa `soxr_hq` |
|---|---:|---:|
| 6 kHz | −1.30 dB | −0.000 dB |
| 7 kHz | **−2.07 dB**, only 0.9442 of the output still at 7 kHz | −0.000 dB, 1.0000 |
| 7.5 kHz | −3.02 dB, 0.9245 | −0.43 dB, 1.0000 |
| 8.1 kHz in → 7.9 kHz out | **−5.65 dB below input** (alias) | −95.5 dB (alias) |
| 9 kHz in → 7 kHz out | −14.25 dB (alias) | annihilated |
| output length | `floor(2n/3)`, drops up to 41.7 µs | `ceil(2n/3)`, drops nothing |

**So the change is real and single-factor.** The question this preregistration fixes, before any
number exists, is: **does replacing miniaudio's resampler with `soxr_hq` change Audio2Tool tool
accuracy at all?**

**The media build already found the reason it might not.** The differences live at 6–8 kHz and
above, and the frozen 400 has almost nothing there. Share of each sealed clip's spectral energy
above the 8 kHz output Nyquist, measured on all 400 (`build-receipt.json` →
`source_band_energy`):

| band | median | mean | p90 | max | clips > 0.1 % | clips > 1 % |
|---|---:|---:|---:|---:|---:|---:|
| above 4 kHz | 0.005112 | 0.013410 | 0.034363 | 0.213346 | 291 | 139 |
| above 6 kHz | 0.000790 | 0.004430 | 0.010684 | 0.140788 | 192 | 42 |
| **above 7 kHz** | **0.000165** | 0.002269 | 0.005467 | 0.105255 | 122 | 22 |
| **above 8 kHz** | **0.0000022** | 0.000291 | 0.000379 | 0.044207 | **15** | **1** |

The alias mechanism has a median of **two millionths** of the clip's energy to fold. The droop
mechanism has more to work with — a median 1.65 × 10⁻⁴ above 7 kHz and 22 clips carrying over 1 %
there — but it is still small. §5 signs the prediction accordingly.

---

## 1. The two cells

Every cell is **one factor, the media**. Same rows, same prompt byte for byte, same build, same
decoding, same geometry, same official scorer as the sealed comparator. Signed as
**cell − sealed comparator**, so a POSITIVE delta on tool accuracy is an improvement.

### 1.1 The media, and the rules

| | cell (a) `@16k` | cell (b) `@16k+ts2` |
|---|---|---|
| rule | every sealed 24 kHz mono int16 wav → 16 kHz mono int16 through `reproduction.obs_loop.decode_parent_pcm` (`librosa.load(sr=16000, mono=True)`, `res_type` `soxr_hq`, then `clip(rint(f32 × 32767), −32768, 32767)`) | the `@16k` samples, then exactly 2.0 s of digital silence through the **pinned** Earnings-22 `transform('tail-silence-2s', …)` |
| clips | 400 | 400 |
| sealed s | 2,159.647 | 2,159.647 |
| variant s | **2,159.647312** | **2,959.647312** |
| bytes | 69,126,314 | 94,726,314 |
| split identity | `292b7220…f12b0` | `655b5ed6…79db67` |
| media root | `derived/a2t-calibration-400-16k-v1` | `derived/a2t-calibration-400-16k-tail2s-v1` |
| roster | `docs/receipts/rosters/a2t-calibration-400-16k-v1.json` | `…-16k-ts2-v1.json` |
| D1 supplement | `docs/receipts/artifacts/d1-a2t-calibration-400-16k.json` (`4894d54d…`) | `…-16k-tail2s.json` (`172ea2a9…`) |

**Nothing was truncated and nothing was invented.** Durations equal the source within one 16 kHz
sample on **400 of 400**; the worst deviation is **+0.000041667 s** and **every deviation is
positive**, because `librosa` returns `ceil(2n/3)` frames. 2 of 400 clips carry a clipped sample
after the resample (4 samples in total).

**The decoder is pinned three ways** and the build refuses on any drift: the SHA-256 of
`decode_parent_pcm`'s own source text (`32450dec…`), the `librosa` 0.11.0 / `soxr` 1.1.0 versions
plus `librosa.load`'s default `res_type`, and the **absence of `ffmpeg`** — which
`decode_parent_pcm` prefers when present and which would change every produced byte without
changing a line of code.

Ids are `<sealed id>@16k` and `<sealed id>@16k+ts2`; the sealed key is recovered by splitting on the
**first** `@` (`reproduction.esb_reference.published_segment_key`), so each population carries its
own split identity, distinct from the comparator's and from each other's.

### 1.2 The token budget does not move, which is what keeps the contrast single-factor

Speech tokens are `13 × (n_samples // 16000 + 1)` (2026-09-07 short-clip encoding audit §2.4). Cell
(a) changes `n_samples` by **at most one sample** per clip, so a clip's block count can only change
if it sits exactly on a multiple of 100 mel frames. The measured worst request under the official
protocol — 3,581 registry text + 468 speech + 256 completion + 2 special = **4,307 tokens** against
a 16,384-token slot (`configs/model/q4km-featcache-a2t-official-04ccc72a.json`) — is therefore
unchanged, and `-c 49152 -np 3` is the comparator's own geometry, kept. Cell (b) adds 2.0 s = 2
blocks = **+26 speech tokens**, worst request 4,333, still 12,051 under the slot.

### 1.3 The comparator

| | |
|---|---|
| comparator | `SAEA-A2T-OFFICIAL-PROTOCOL-REPLICATION-V1`, cell `R-official-raw`, attempt `attempt-20260904T135250Z-rofficialraw` |
| comparator identity | config `0e56ce8f…`, protocol `6da614b2…`, split `e1d751e6…` |
| paper-facing scorer | `a2t-toolcall-official` (vendored release `metrics.py`, upstream `b9d5383c`) |
| sealed tool accuracy, n = 400 | T1 60.0, T2 74.0, T3 72.0, T4 28.0, T5 78.0, T6 84.0, T7 58.0, T8 34.0; **overall 61.0**, exact match 20.25, parse rate 99.75 |
| serving path | raw audio through the bf16 mmproj, `-c 49152 -np 3`, `max_tokens` 256, greedy |

**What the comparator sends is the whole point.** It sends the 24 kHz bytes, so **its** arm is the
one miniaudio resamples. Neither arm is re-flown to produce the other: the sealed bytes are the
comparator, because greedy decoding on this runtime is not bitwise reproducible across batch
compositions.

### 1.4 `A2T-BOUNDARY`, carried over unchanged for cell (b)

Defined in §1.3 of the cross-carrier preregistration and **not redefined here**:
`official_call_matches > 1` **OR** a non-empty non-default extra-key set, re-derived from each row's
own verbatim `predicted_tool_call` through `audio2tool_official.parse.parse_tool_call` and
`analysis.a2t_scorer_v2_study.classify_row`. On the sealed run it fires on **52 of 400 rows — 27 in
tier 3 (multi-intent), 25 in tier 8 (intent blending), and zero in the other six tiers.** Reported
per tier, on both arms, with the `completion_tokens` distribution beside it.

---

## 2. The comparator, the pairing and the statistics

Identical to the cross-carrier cells this transfers from:

* Paired **per row** on the key recovered by splitting the `@` suffix, against the sealed
  comparator's own sealed outputs.
* `analysis.paired.resampled_statistic` for pooled ratios, `analysis.paired.paired_contrast` for
  per-row saves/harms/ties and the exact sign test. **10,000 replicates, stratified bootstrap,
  seed 20260903, CI90.** Strata = tier.
* **Identity gate first**: no contrast is computed until the sealed comparator reproduces §1.3's
  eight tier accuracies plus the overall, to the digit, from its own sealed score file.
* Scoring runs **once over the complete sealed manifest** through `core.scoring_batch`, never
  sharded, with the official `a2t-toolcall-official` scorer and no other.

---

## 3. The null, and where it is imported

The Earnings-22 rule states admission as **disjointness from a measured same-request null**, because
this runtime produces a non-zero delta when nothing changed. **No such null has been measured on
Audio2Tool.** Two consequences, both binding, and both inherited verbatim from §3 of the
cross-carrier preregistration:

1. Per tier, the null is the **Wilson CI90 of the sealed tier proportion** at n = 50 — an arithmetic
   fact, not an import. Computed with `scripts/a2t_official_protocol_analysis.py::wilson` at
   `Z_90 = 1.6449`:

   | tier | sealed | Wilson CI90 | **harm floor** |
   |---|---:|---|---:|
   | `tier1_direct` | 60.0 | [48.4, 70.6] | **48.4** |
   | `tier2_parallel` | 74.0 | [62.8, 82.8] | **62.8** |
   | `tier3_multi_intent` | 72.0 | [60.6, 81.1] | **60.6** |
   | `tier4_ambiguous` | 28.0 | [18.9, 39.4] | **18.9** |
   | `tier5_conditional` | 78.0 | [67.1, 86.1] | **67.1** |
   | `tier6_correction` | 84.0 | [73.8, 90.7] | **73.8** |
   | `tier7_multiturn` | 58.0 | [46.4, 68.8] | **46.4** |
   | `tier8_intent_blending` | 34.0 | [24.1, 45.6] | **24.1** |

   **A correction to the cross-carrier preregistration, recorded rather than propagated.** Its §3
   describes this interval as "4–7 pp across the accuracy range". That figure is the binomial
   **standard error** at n = 50 (6.9 pp at p = 0.60, 5.8 pp at p = 0.78); the CI90 **half-width** it
   actually names as the harm bound is **9.3 to 11.1 pp**. The table above is the arithmetic; the
   sentence was loose. Nothing flown was affected — the cross-carrier cells have not been flown.

2. For the **overall** delta, which is a paired ratio and not a fresh binomial, there is no measured
   null, so the admission clause uses **zero** as the null and adds a margin equal to the
   Earnings-22 null's own half-width on the same scale. **The verdict must say that the margin is
   imported, not measured.** A result that lands inside it is **NOT ADMITTED and NOT REFUTED**; it
   is reported as *"inside the imported null margin, and the null this carrier actually has was
   never measured"*, and measuring it becomes the named next cell rather than a footnote.

---

## 4. The decision rules, fixed now, before any number exists

### 4.1 Cell (a) — `@16k` vs the sealed 24 kHz comparator

The rule is **§4.2 of the cross-carrier preregistration, quoted and then adapted in exactly one
place**. Quoted verbatim:

> **ADMITTED iff all three hold**:
>
> 1. **Overall official tool accuracy rises**, and the CI90 lower bound on the paired delta is
>    **> 0**, computed by the stratified bootstrap over tiers rather than from a pooled binomial.
> 2. **No tier falls outside its own sealed Wilson CI90.** A tier that drops below the lower bound
>    of its sealed proportion's interval is a harm, and one harmed tier blocks admission.
> 3. **The boundary class moves in the predicted direction.**

Clauses 1 and 2 apply **unchanged**, with §3's table as the clause-2 floors. **Clause 3 is
replaced**, because `A2T-BOUNDARY` is a clip-end mechanism and this cell does not touch the clip
end:

> 3′. **The mechanism is where the audit says it is.** The per-row delta must be larger on the
>     **122 clips carrying more than 0.1 % of their energy above 7 kHz** than on the 278 that do
>     not, and larger still on the 22 above 1 %. This is the clause that can falsify the mechanism
>     even when the pooled number moves, and it is the reason the band energy was measured before
>     the cell rather than after. **A cell that clears 1 and 2 but not 3′ is reported as an accuracy
>     effect without a mechanism**, exactly as the Earnings-22 rule already does for its own
>     clause 3.

Reported beside the verdict whether it fires or not: the per-tier table, exact match, parse rate
(sealed 99.75), the `completion_tokens` distribution, and the `A2T-BOUNDARY` count per tier — the
last as a **descriptive control**, since a media change that alters nothing at the clip end should
leave it flat, and a large move in it would be evidence that something other than the resampler
changed.

### 4.2 Cell (b) — `@16k+ts2`, the tail on standardized media

Cell (b) is **the cross-carrier `@ts2` Audio2Tool cell, rebuilt on standardized media**, and its
rule is §4.2 of that preregistration **in full and unmodified**, `A2T-BOUNDARY` clause included —
because cell (b) *does* change the clip end. Its comparator is the same sealed 24 kHz run, so cell
(b) measures **the tail and the standardization together**; the tail's own effect is the difference
between cell (b) and cell (a), and that difference is reported but is **not** an admission criterion
here, because it was not preregistered as a paired contrast with its own null.

**Cell (b) does not fly unless cell (a) has flown and been read.** Otherwise its two factors cannot
be separated at all.

### 4.3 The falsifier both cells must check before any score is read

**The media accounting must close on every flown row.** Each row's delivered audio seconds must
equal its sealed row's (cell a) or its sealed row's plus exactly 2.0 (cell b), to within one 16 kHz
sample, and each row's media SHA-256 must equal the committed D1 supplement's entry for that id.
**Zero disagreeing rows, or the cell is void and no score is read.**

---

## 5. The prediction, signed and recorded before the cells exist

**Cell (a): near zero, and a null here is a real result.** The two resamplers differ at 6–8 kHz and
above; the corpus's median energy above 8 kHz is **0.0000022** and above 7 kHz **0.000165**. One
clip of 400 carries more than 1 % above 8 kHz. Predicted overall tool-accuracy delta **−1.0 to
+1.5 pp**, and *inside the imported null margin* is the single most likely outcome. **That would be
the useful finding**: it would say the input-rate standardization is hygiene rather than a
performance lever, and it would justify applying it once, globally, on correctness grounds without
spending further cells on it.

**A large positive result would be suspicious, not exciting.** Nothing in the audit predicts more
than a fraction of a decibel of change to a median clip, so a multi-point gain would more plausibly
indicate a harness difference — a changed request, a cache miss changing batch composition, a
different slot assignment — than a resampler effect, and the verdict must say so and check the
prompt bytes before claiming otherwise.

**Cell (b): the cross-carrier prediction, unchanged.** Only 5.0 % of these clips end on an active
frame and the median already carries 80 ms of trailing silence, so the tail's precondition is
largely absent. Predicted overall delta **−1.0 to +1.5 pp** against the sealed run, dominated by
whatever cell (a) showed.

---

## 6. The re-lock consequence, and the price of the union rebuild

**This is the part that makes cell (a) expensive even though its own flight is cheap.**

If cell (a) is ADMITTED, the study cannot keep one Audio2Tool population on standardized media and
another on raw 24 kHz bytes: a later cell that mixes them is no longer single-factor in whatever it
claims to test. Admission therefore carries two obligations, and they are stated **before** the cell
so that admitting is a decision and not a drift.

### 6.1 The frozen-400 comparator is re-locked

The sealed `R-official-raw` outputs were produced from 24 kHz bytes. Once `@16k` is the standard,
those bytes stop being a like-for-like baseline for anything new, and **the comparator every future
Audio2Tool cell pairs against must be the `@16k` arm** — which is cell (a)'s own output. Cell (a)
therefore does double duty: it is the test *and*, if admitted, the new baseline. Its manifest must
be sealed and scored to the same standard as a comparator, not as a probe, and its per-row outputs
must be retained under `SPEECHRL_DATA_DIR/runs/…` for future pairing.

### 6.2 The ORG-1 union 4,000 must be re-standardized before any further Audio2Tool cell

`A2T-ORG1-UNION-4000` (`configs/dataset/audio2tool-org1-union-4000.json`) is the 4,000-row union of
the three sealed official-population rosters — 500 per tier over all eight tiers, 23,418.083083
audio seconds — and **every one of those rows already carries a sealed official-protocol output**
produced on 24 kHz media. It is the population A2T-ORG-1 and every domain-grouped-registry cell
pairs against.

**Priced, model-free, from this build's own measured throughput** (`build-receipt.json` →
`union_rebuild_price`):

| item | @16k | @16k+ts2 |
|---|---:|---:|
| rows | 4,000 | 4,000 |
| source audio seconds | 23,418.083083 | 23,418.083083 |
| scale from the measured 400 | ×10.843477 | ×10.843477 |
| projected output bytes | 749,569,612 (**0.6981 GiB**) | 1,027,162,630 (**0.9566 GiB**) |
| CPU wall | **≈ 1.4 min** at 8 workers (measured: 7.4 s for 2,159.647 s of source audio) | ≈ 1.4 min |
| GPU-hours | **0.0** | 0.0 |
| frozen-core contacts | **0** | 0 |

**The CPU minutes are not the cost.** Three things are:

1. **A new D1 supplement.** The union's existing supplement covers 3,932 ids parented directly to
   `d1-identity.json`; a standardized twin is required, because `contracts.gate_media_identity`
   accepts exactly one supplement path per run and refuses an entry that duplicates a base D1
   sample. Model-free, but a real artifact with its own row.
2. **A new roster and two new identity hashes** per variant, and every fragment naming the union has
   to be re-emitted against them.
3. **The sealed baseline stops being a baseline.** The 4,000 official-protocol outputs the union is
   paired against were produced from 24 kHz bytes. To stay like-for-like they would have to be
   **re-flown on standardized media: 4,000 contacts and ~23,418 audio seconds of GPU work** —
   about **0.85 GPU-hours** at the sealed 400-row run's own measured ~280 s of wall, and **2.0
   GPU-hours** if it is registered against the same per-row ceiling §8 uses for cell (a). **That is
   the real price of admitting cell (a)**, and it is registered here as a consequence rather than
   discovered later.

**If cell (a) is NOT admitted** — including the "inside the imported null margin" outcome — none of
§6 fires, the sealed 24 kHz comparator stands, and the `@16k` media stays a committed, unused
artifact. That asymmetry is deliberate: it is much cheaper to leave the input rate alone than to
change it, so the change has to earn itself.

### 6.3 What this replaces in the cross-carrier preregistration

If cell (a) is admitted, **cell (b) replaces the `R-official-tail2s` cell of
`docs/readiness/2026-09-07-cross-carrier-silence-tail-v1-preregistration.md`**, whose media appends
2.0 s to the 24 kHz bytes. A dated paragraph saying so has been added to §1.3 of that document. The
SLURP and Earnings-21 cells of that preregistration are **untouched**: their media is already
16 kHz and no resampler runs on it.

---

## 7. What is NOT built, measured rather than guessed

### 7.1 Precondition — the `@16k` gold-id rail (blocks both cells)

`rails/adapters/audio2tool.py:161-171` looks up gold by exact `sample_id`:

```python
        expected = expected_by_id.get(sample.sample_id)
        if expected is None:
            raise ValueError(
                f"sample {sample.sample_id!r} is not in the frozen audio2tool probe receipt"
            )
```

so `tier1_direct:000045@16k` refuses, exactly as `@ts2` already does
(`cross_carrier_tail2s_wire_check.py`'s `a2t-gold-id-rail-missing` class). **Earnings-22 already
solved this exact problem**: `reproduction.esb_reference.published_segment_key` splits a derived id
on the first `@`, and its docstring records the property that makes it safe — *"An id without a
suffix is returned unchanged, so every population that existed before the convention is
byte-for-byte unaffected."*

**This preparation did not apply it, on purpose, and for the same reason the cross-carrier
preparation did not**: a gold lookup decides what a sample's ground truth IS, and changing one is a
reviewed edit to a paper-facing path, not something a model-free media build does on its own
initiative mid-campaign. It is named here with its precedent, its exact call site and its inertness
property. **The rail is a single change that unblocks `@ts2`, `@16k` and `@16k+ts2` at once**, and
the wire check of §8 re-runs against it.

### 7.2 The feature cache is a miss by construction, and that is correct

The official-protocol fragment sets `LLAMA_MTMD_FEAT_CACHE_DIR=/home/chao/feat-cache/audio2tool-q4km-04ccc72a`.
The legacy key is FNV-1a over the **original media bytes**
(`core.model.speech_features.legacy_audio_feature_cache_key`), so a `@16k` file can never hit the
comparator's cache and the encoder runs for all 400. That is what makes the cell honest — a cache
hit would return features computed from the 24 kHz bytes, which is the arm under test — and it is
also why the GPU ceiling in §8 is not lower than the sealed run's.

---

## 8. Budgets, geometries and the order to fly them

Paid API spend is 0 and stays 0. Every figure is a registered ceiling, not an estimate to be
exceeded.

| cell | contacts | audio s | GPU-h | geometry |
|---|---:|---:|---:|---|
| (a) smoke, 4 rows | 8 | 60 | 0.05 | `q4km-featcache-a2t-official-04ccc72a`, `-c 49152 -np 3` |
| **(a) `@16k`, 400 rows** | **408** | **2,400** | **0.20** | same |
| (b) smoke, 4 rows | 8 | 60 | 0.05 | same |
| **(b) `@16k+ts2`, 400 rows** | **408** | **3,100** | **0.20** | same |

One geometry, so **one resident session** for both cells; the coordinator runs it
(`docs/readiness/2026-09-07-always-on-serving-operating-note.md`) and a flight attaches and never
stops it or touches port 8080. Order: **(a) smoke → (a) → read → (b) smoke → (b)**, and (b) does not
start until (a) has been read, per §4.2.

The ceilings are above the sealed run's ~280 s of wall because every request is a feature-cache miss
(§7.2) and cell (b) carries 37 % more audio than its sealed twin. Official scoring of each cell
overlaps the next flight, once per complete manifest through `core.scoring_batch`, never sharded.

---

## 9. The flight checklist — one agent per cell

Every item is a refusal point. An agent that cannot tick one stops and reports; it does not proceed.

1. The cell's **owner GO** is recorded, and its **exposure row is written before the first contact**,
   carrying the profile, the population, the split identity, the ceilings and the inherited exposure.
2. The tree is **clean** at a committed study commit and `PYTHONDONTWRITEBYTECODE=1` is exported — a
   dirty tree and stray bytecode each close the scoring gate at finalize, after the GPU time is
   spent.
3. The **gold-id rail of §7.1 is applied and tested**, with a test proving the unsuffixed
   populations are byte-for-byte unchanged.
4. The **zero-contact wire check reaches `seal_and_score: OK`** on this cell's own fragments
   (`scripts/a2t_input_rate_16k_wire_check.py`). A manifest that seals `COMPLETED` and then will not
   score wastes GPU time after it has been spent.
5. The **4-row smoke** flies first and the media falsifier of §4.3 holds on 4 of 4.
6. The agent **attaches** to the coordinator's resident `-c 49152 -np 3` session.
7. The full cell flies **once**. At most one recovery re-registration; a second failure stops the
   flight and the fix is proven on a 4-row dry run.
8. The **media falsifier of §4.3 is checked on every flown row BEFORE any score file is opened**, and
   row count, audio seconds and GPU-hours are reconciled against the registered ceilings.
9. Scoring runs **once over the complete sealed manifest** through `core.scoring_batch`.
10. The **identity gate of §2** passes before the first contrast is computed.
11. The verdict quotes §4's rule **verbatim before applying it**, carries the per-tier table, states
    which null it used and whether that null was measured or imported, and — for cell (a) — states
    §6's re-lock consequence and the union rebuild price **as part of the admission**, not as an
    afterthought.

---

## 10. What neither cell can conclude

* **Nothing about a test split.** The frozen 400 is discovery. No published-number comparison is
  licensed from it, and the standing rule applies unchanged: a media-changed number is never
  reported as a like-for-like reproduction of a published protocol.
* **Nothing about generalization or superiority**, and nothing that belongs to Stage-3.
* **Not that `soxr_hq` is "correct".** The audit records that the two resamplers disagree in the
  7.5–8 kHz band in *both* directions: `soxr_hq` cuts content there that miniaudio keeps attenuated.
  Standardizing is a choice with a stated cost, not a repair of an error.
* **Not that the input rate is the last difference.** The mel front end still pads the last 100-frame
  block with literal `0.0` and charges 13 tokens for it (2026-09-07 short-clip encoding audit);
  standardizing the rate does not touch that.
* **Not that a null on Audio2Tool means the rule is wrong.** The owner rule is about every carrier;
  the other three are already standardized by this same path, so a null here says the rule was
  already satisfied where it mattered, not that it should not exist.
