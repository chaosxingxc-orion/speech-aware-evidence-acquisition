# Preregistration — does two seconds of silence transfer off Earnings-22?

**NOT AUTHORIZED. NOT FLOWN.** Three single-factor cells, one per carrier, each paired against that
carrier's own sealed comparator on the same rows. Written before any of them exists, and before any
number from any of them is read. Each cell needs its own owner GO and its own exposure row; two of
the three additionally need a precondition that this preparation deliberately did not build, and
§6 names both, with the exact line they stop at measured rather than guessed.

The media is built and committed. Rows `SAEA-SN-MF-SLURP-DEV1000-TS2-MEDIA-V1`,
`SAEA-SN-MF-A2T-CAL400-TS2-MEDIA-V1` and `SAEA-SN-MF-E21-BUF90-TS2-MEDIA-V1`; builder
`scripts/build_cross_carrier_tail2s_media.py`; receipts under
`docs/checks/speech-aware-evidence-acquisition/2026-09-07-{slurp-dev1000,a2t-calibration-400,e21-buf90}-tail2s-media/`.

---

## 0. What is being asked, and why it is worth asking

On Earnings-22 short-form, appending 2.0 s of digital silence after the published span moved corpus
Whisper-normalized WER from **15.9365 to 9.2377** on the sealed 2,735-utterance test population
(`docs/readiness/2026-09-07-e22-esb-shortform-tail2s-test-v1-verdict.md`), a paired
**−6.6988** [−7.0373, −6.3753]. The whole gain was an insertion collapse: 4,612 → 1,248 insertions,
the `runaway-tail` error mass down 97 % while `runaway-head` barely moved. The mechanism the
2026-09-07 encoding audit priced is the discontinuity at the clip end — our path glues a block of
constant, non-silent `0.0` mel features to the last speech frame, and the model continues past the
boundary rather than stopping.

**That mechanism is not about Earnings-22.** It is about how a clip ends. So the question this
preregistration fixes, before any number exists, is: **does the same 2.0 s of silence help on
carriers whose task is not transcription at all, and whose clips end differently?**

The answer is not obviously yes, and the media build already found the reason it might be no. §1.4
records, per carrier, how much silence each sealed clip ALREADY carries after its last active
frame. The three carriers are not alike, and the prediction in §5 is signed accordingly.

---

## 1. The three cells

Every cell is **one factor, the media**. Same rows, same prompt byte for byte, same build, same
decoding, same geometry, same official scorer as its sealed comparator. Signed as **cell − sealed
comparator** throughout, so on a metric where higher is better a POSITIVE delta is an improvement,
and on WER a NEGATIVE delta is.

### 1.1 The media, and the rule

Exactly **2.0 seconds** of digital silence appended to every sealed clip. Strictly additive: nothing
removed, no sealed sample altered, no sample rate changed, no parent container re-decoded that the
comparator did not itself decode. `librosa` never ran and `ffmpeg` stayed absent.

The rule is the Earnings-22 rule, not a new one:
`scripts/build_e22_dev1500_media_variants.py` is imported and pinned by SHA-256
`49e5d91095c061d167688bd4dea35fc7503d3a09caa3066db68fde9807d196e6`, and the build **proves** its own
seconds-based `append_tail` byte-identical to that file's `transform('tail-silence-2s', ...)` at
16 kHz before it touches a clip. That proof is load-bearing rather than decorative: the pinned
transform hard-codes `2 * 16000` samples, and **every Audio2Tool release wav is 24 kHz mono**, where
that integer would have appended 1.333 s and silently changed the factor under test.

| carrier | container | rate | tail | clips | sealed s | variant s |
|---|---|---:|---:|---:|---:|---:|
| SLURP DEV-1000 | FLAC, lossless round trip proved per file | 16 kHz | 32,000 samples | 1,000 | 2,884.794 | 4,884.794 |
| Audio2Tool frozen 400 | WAV | **24 kHz** | 48,000 samples | 400 | 2,159.647 | 2,959.647 |
| Earnings-21 buf90 windows | WAV | 16 kHz | 32,000 samples | 1,593 | 141,345.853 | 144,531.853 |

Ids are `<sealed id>@ts2`, the identity convention §1.4 of the 2026-09-06 boundary-exact
preregistration fixed. Each population therefore carries its own split identity, distinct from its
comparator's, and the sealed key is recovered by splitting on `@`.

### 1.2 SLURP — DEV-1000 closed-list direct

| | |
|---|---|
| comparator | `SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1`, attempt `attempt-20260905T060424Z-2c5596` |
| comparator identity | config `6be064ba…`, protocol `7e83a705…`, split `8580d199…` |
| paper-facing scorer | `slurp-slu-official-projected-v2` (SLURP official `evaluate.py`, pinned clone) |
| sealed numbers, n = 1,000 | scenario **82.60**, action **74.60**, intent **73.10**, entities-strict 21.91, word-F1 33.69, char-F1 38.20, **SLU-F1 35.80**, unparsed 3 |
| serving path | mmproj-free decode over `SpeechFeaturePacketV1` packets, `-c 65536 -np 8` |
| cell | `SAEA-SLURP-DEV1000-CLOSED-LIST-TAIL2S-V1`, split identity `9f78d0ff…` |
| variant identity | `configs/dataset/slurp-speech-native-dev1000-tail2s.json`, composed config hash `6643cfb2f988851a1df030cb0877275bb42affbcd85d0ee103ca99b24fcc9ddb` |

**The packet-path answer, which is the question this carrier was prepared to settle.** DEV-1000 does
not fly raw audio. It flies encoder features, materialized once and decoded mmproj-free. The legacy
feature-cache key is **FNV-1a over the ORIGINAL media bytes**
(`core.model.speech_features.legacy_audio_feature_cache_key`), so a `@ts2` file is a cache miss by
construction and can never reuse the comparator's packets.

**A silence tail CAN enter the packet path, and the raw-audio fallback is not needed.** What it
costs is its own promotion, which is a separate registered row and not part of the cell:

* **encode**: 1,000 contacts through the CPU-only sidecar
  (`q4km-preprocess-featcache-cpu-sidecar`, port 8081, `-ngl 0 --no-mmproj-offload`,
  `max_tokens: 1`, response never read semantically) into a fresh legacy cache
  `/home/chao/feat-cache/slurp-ts2-q4km`. **0 GPU-hours**; projected **≈ 37 min** of CPU wall, scaled
  from `SAEA-SN-DEV1000-PREPROCESS`'s measured 11.0 min for 1,462.712 audio seconds through this same
  sidecar. Profile `bounded-discovery-probe`, its own exposure row, registered before the first
  contact.
* **promote**: `materialize_legacy_cached_speech_feature_packets` into
  `/home/chao/feat-cache/slurp-dev1000-ts2-packets-04ccc72a`. **Zero contacts.**
* **gate first**: a 4-row dry run of the encode, proving the libsndfile-written FLAC decodes in
  llama.cpp's miniaudio front end and that the promoted packet's token count equals the sealed
  packet's plus the tail's blocks. Four contacts, not a thousand, if it is wrong.

Because the promotion exists, the cell flies on **the comparator's own serving path** — the model
fragment `q4km-mmproj-free-speech-native-np8-ts2-packets-max64` is the comparator's fragment byte for
byte except `speech_feature_root`. The contrast is therefore single-factor in the media and in
nothing else, and no dual plain/tail raw-audio design is needed on this carrier.

What the promotion does **not** prove is that the CPU sidecar and a GPU mmproj emit identical
features. It does not need to: the comparator's own packets were produced by this same sidecar, so
both arms are encoded by the same instrument.

### 1.3 Audio2Tool — the official protocol on the frozen 400

| | |
|---|---|
| comparator | `SAEA-A2T-OFFICIAL-PROTOCOL-REPLICATION-V1`, cell `R-official-raw`, attempt `attempt-20260904T135250Z-rofficialraw` |
| comparator identity | config `0e56ce8f…`, protocol `6da614b2…`, split `e1d751e6…` |
| paper-facing scorer | `a2t-toolcall-official` (vendored release `metrics.py`, upstream `b9d5383c`) |
| sealed tool accuracy, n = 400 | T1 60.0, T2 74.0, T3 72.0, T4 28.0, T5 78.0, T6 84.0, T7 58.0, T8 34.0; **overall 61.0**, exact match 20.25, parse rate 99.75 |
| serving path | raw audio through the bf16 mmproj, `-c 49152 -np 3`, `max_tokens` 256, greedy |
| cell | `SAEA-A2T-OFFICIAL-PROTOCOL-TAIL2S-V1`, split identity `6aa3aa43…` |

**The boundary-like failure class, defined here from the sealed columns and BEFORE any cell number is
read.** Audio2Tool outputs are call strings, so continuation past the clip end cannot show up as
"extra words". It shows up in exactly three places, all of which the sealed per-row score entries
already carry:

1. **A second call.** `official_call_matches` counts call-shaped regex spans in the raw completion;
   the official scorer parses only the first. The sealed run has **52 of 400 rows with more than one
   match**, and they are not spread evenly: **27 in tier 3 (multi-intent), 25 in tier 8 (intent
   blending), and ZERO in the other six tiers.** That concentration is itself the caution — those two
   tiers are the ones where a second call may be the task rather than an artifact.
2. **Extra arguments.** `param_predicted_keys` − `param_correct_keys` per row against
   `param_gold_keys`; the exact extra-key set is re-derived from the row's own verbatim
   `predicted_tool_call` through `audio2tool_official.parse.parse_tool_call`, the same parser the
   scorer uses. `analysis.a2t_scorer_v2_study.classify_row` already returns `keys_extra` /
   `keys_missing` and the `EXTRA_KEYS_DEFAULT_ONLY` / `EXTRA_KEYS_NONDEFAULT` categories; it has
   never been run against the official-protocol outputs and this is where it gets run.
3. **Output length.** `completion_tokens` from the trace's own `COST` / `MODEL_RESPONSE` records.
   The decoding ceiling is 256, so a continuation artifact hitting the cap shows as rows piled at
   256.

**`A2T-BOUNDARY` is defined as: `official_call_matches > 1` OR a non-empty non-default extra-key
set.** It is reported per tier, on both arms, with the `completion_tokens` distribution beside it.
The frozen 400 is used, not the tier-1 official 500: the 400 is the roster the official-protocol
comparator itself flew, and pairing against it is what makes the contrast single-factor.

**Amendment, 2026-09-07 — this cell may be superseded before it flies.** The same-day input-rate
audit (`docs/readiness/2026-09-07-a2t-input-rate-audit-v1.md`) established that **Audio2Tool is the
only carrier in this study whose audio llama.cpp resamples**: its release wavs are 24 kHz and
miniaudio converts them to 16 kHz with its linear resampler. The `@ts2` media above appends 2.0 s to
those **24 kHz** bytes, so it inherits that conversion. `docs/readiness/2026-09-07-a2t-input-rate-standardization-v1-preregistration.md`
registers a `@16k+ts2` population — the same 2.0 s tail on librosa-standardized 16 kHz bytes,
appended by this same pinned transform — as cell (b). **If that preregistration's cell (a) admits
the standardization, cell (b) REPLACES `R-official-tail2s` and this Audio2Tool cell does not fly**;
if cell (a) is not admitted, this cell stands exactly as written. **The SLURP and Earnings-21 cells
of this preregistration are untouched either way**: their media is already 16 kHz and no resampler
runs on it.

### 1.4 Earnings-21 — the full-44 buf90 windows

| | |
|---|---|
| comparator | `SAEA-E21-FULL44-DIRECT-BASELINE-V2`, attempt `attempt-20260904T233816Z-bcd338` |
| comparator identity | config `e4b133d1…`, protocol `06f7f308…`, split `fcc1b0bc…` |
| paper-facing scorer | `asr-wer-whisper`, corpus WER, Whisper `EnglishTextNormalizer` both sides |
| sealed corpus WER | **8.1995 %** (S 13,098 / D 5,701 / I 10,700 over 359,765 reference words) |
| the four agentic metrics, sealed | `asr-wer-whisper` **8.1995**; `conec-entity-wer-official` **8.200** overall / 4.730 non-entity; `numeric-value-accuracy-v1` **90.7335**; `semantic-high-impact-error-rate-v1` **0.02780** |
| serving path | raw audio through the bf16 mmproj, `-c 36864 -np 6`, `GGML_CUDA_DISABLE_GRAPHS=1` |
| pairing | per window `<call>#w<NNNN>`, clustered by call (`analysis.e21_window_pairing.call_of`); owner ruling 2026-09-06 |

**The window-end measurement, which is the reason this carrier is in the probe at all.** The
question the brief asked was whether a buf90 window already ends in silence or in mid-speech.
Measured with `analysis.e22_clip_boundary.energy_margins` at its committed version on the SEALED
slices — 20 ms frames, active = frame RMS within 35 dB of the clip's own peak and above the absolute
floor:

| | Earnings-21 buf90 | SLURP DEV-1000 | Audio2Tool 400 |
|---|---:|---:|---:|
| n | 1,593 | 1,000 | 400 |
| **ends on an ACTIVE frame** | **1,043 (65.5 %)** | 549 (54.9 %) | **20 (5.0 %)** |
| trailing silence ≤ 0.02 s | 1,103 (69.2 %) | 644 (64.4 %) | 51 (12.8 %) |
| median trailing silence | **0.000 s** | 0.000 s | **0.080 s** |
| mean | 0.253 s | 0.075 s | 0.121 s |
| p90 | 0.460 s | 0.200 s | 0.280 s |
| max | 37.240 s | 1.400 s | 0.620 s |
| already ≥ 2.0 s | 39 | 0 | 0 |

**A fixed 90-second cut has no reason to land in a pause, and it does not.** Splitting the last
window of each call out from the rest: the 44 final windows carry a median 0.560 s of trailing
silence (they end where the call ends), while **1,088 of the 1,549 INTERIOR windows (70.2 %) end
within 20 ms of active speech**. That is the largest mid-speech-boundary exposure of the three
carriers, and it is the population where the Earnings-22 mechanism has the most to bite on.

---

## 2. The comparator, the pairing and the statistics

Identical on all three carriers, and identical to the Earnings-22 cells this transfers from:

* Paired **per row** on the key recovered by splitting the `@ts2` suffix, against the sealed
  comparator's own sealed outputs. No arm is re-flown to produce its comparator.
* `analysis.paired.resampled_statistic` for pooled ratios, `analysis.paired.paired_contrast` for
  per-row saves/harms/ties and the exact sign test. **10,000 replicates, stratified bootstrap,
  seed 20260903, CI90.**
* Strata: SLURP = gold scenario (read only inside the scorer, never in the request path);
  Audio2Tool = tier; Earnings-21 = source call.
* Earnings-21 additionally reports the **call-clustered** interval beside the stratified one and
  the verdict reads the clustered one as the honest interval, per the window-pairing module's own
  note that pairing at n = 1,593 buys per-window strata and an optimistic bound, not extra power.
* **Identity gate first**: no contrast is computed until the sealed comparator reproduces its own
  published numbers from its own sealed score file, to the digit. The anchors are §1.2's seven SLURP
  figures, §1.3's eight tier accuracies plus the overall, and §1.4's four agentic metrics plus
  S/D/I.

---

## 3. The measured greedy null, per carrier

The Earnings-22 rule is stated as **disjointness from a measured same-request null**, not as
"excludes zero", because this runtime produces a non-zero delta when nothing changed. That rule is
kept, and the null is per carrier:

* **Earnings-22's own null**, measured on 1,432 rows whose request differed only by an inert
  integer: −0.0844 corpus-WER points, CI90 **[−0.2356, +0.0692]**, 302 of 1,432 rows emitting
  different bytes.
* **No such null has been measured on SLURP, Audio2Tool or Earnings-21.** This is stated plainly
  rather than papered over. Two consequences, both binding:
  1. Where a carrier has no measured null, the admission clause uses **zero** as the null and adds a
     margin equal to the Earnings-22 null's own half-width on the same scale — and the verdict must
     say that the margin is imported, not measured.
  2. A carrier whose result lands inside that imported margin is **NOT ADMITTED and NOT REFUTED**;
     it is reported as *"inside the imported null margin, and the null this carrier actually has was
     never measured"*, and measuring it becomes the named next cell rather than a footnote.

The one carrier where an imported margin is clearly wrong is Audio2Tool, whose metric is a
proportion over n = 50 per tier. There the null is the **Wilson CI90 of the sealed tier proportion**,
which is 4–7 pp across the accuracy range the sealed run spans — an arithmetic fact, not an import.

---

## 4. The decision rule, fixed now, before any number exists

Each carrier is judged on its own admission, and **there is no cross-carrier verdict**: three cells,
three answers, reported side by side.

### 4.1 SLURP

**ADMITTED** as a model-usage local optimization **iff all three hold**:

1. **Intent accuracy (scenario+action), the paper-facing headline.** The CI90 lower bound on the
   delta is **> +0.60 pp** — above zero and above the imported null margin. Point estimate positive.
2. **SLU-F1 does not worsen.** Its CI90 lower bound is above **−0.60 pp** (non-inferiority at the
   same imported margin), and scenario and action accuracy are both non-inferior on the same rule.
3. **No stratum is harmed beyond the carrier's own rule.** SLURP's per-scenario harm bound, as
   EVO-S1 already uses it: no scenario loses more than **3.0 pp** of intent accuracy, and at most
   **2 of the 18** scenarios lose anything at all.

Reported beside the verdict whether it fires or not: the unparsed count (sealed 3), entities-strict,
word-F1 and char-F1, and the per-scenario table.

### 4.2 Audio2Tool

**ADMITTED iff all three hold**:

1. **Overall official tool accuracy rises**, and the CI90 lower bound on the paired delta is
   **> 0**, computed by the stratified bootstrap over tiers rather than from a pooled binomial.
2. **No tier falls outside its own sealed Wilson CI90.** A tier that drops below the lower bound of
   its sealed proportion's interval is a harm, and one harmed tier blocks admission.
3. **The boundary class moves in the predicted direction.** `A2T-BOUNDARY` (§1.3) falls, and the
   fall is concentrated outside tiers 3 and 8 — because in those two tiers a second call may be the
   task. A cell that clears 1 and 2 but not 3 is reported as **an accuracy effect without a
   mechanism**, exactly as the Earnings-22 rule already does for its own clause 3.

### 4.3 Earnings-21

**ADMITTED iff all three hold**:

1. **Corpus WER, and it must beat the null.** The CI90 upper bound on the delta is **< −0.2356** —
   below zero and disjoint from the Earnings-22 same-request null's interval, which is the closest
   measured null this carrier has and is labelled as imported.
2. **No agentic metric worsens.** `numeric-value-accuracy-v1` and `conec-entity-wer-official`
   (overall and non-entity) are non-inferior at their own CI90, and
   `semantic-high-impact-error-rate-v1` does not rise. Its sealed 0.02780 % is a strict lower bound
   on the true content-impact rate and the verdict must repeat that when it uses it.
3. **The effect concentrates where the audit predicts.** The per-window contrast is larger on the
   **1,088 interior windows that end within 20 ms of active speech** than on the 39 windows that
   already carry 2.0 s or more of trailing silence. This is the clause that can falsify the
   mechanism even when the pooled number moves, and it is the reason §1.4's measurement was made
   before the cell rather than after.

### 4.4 A falsifier every cell must check before any score is read

Same shape as the Earnings-22 cells': **the media accounting must close on every flown row.** Each
row's delivered audio seconds must equal its sealed row's plus exactly 2.0, and each row's media
SHA-256 must equal the committed D1 supplement's entry for that `@ts2` id. Zero disagreeing rows, or
the cell is void and no score is read.

---

## 5. The prediction, signed and recorded before the cells exist

**Earnings-21: largest effect, same direction, smaller in size than Earnings-22's.** The population
is 65.5 % mid-speech-ended and the task is transcription, so the insertion-collapse mechanism
applies almost unchanged. But the unit is a 90-second window, not a 3-second utterance: the
Earnings-22 effect was 21.4 WER points on sub-second clips and 3.4 on the 16 s+ bucket, and every
buf90 window is 90 s. Predicted corpus-WER delta **−0.2 to −1.5 points** from the sealed 8.1995.

**SLURP: small, positive, quite possibly inside the null.** 54.9 % of clips end on an active frame,
which is the mechanism's precondition, but the task is a short structured label rather than an open
transcription, the decoding cap is 64 tokens, and there is far less room to run on. Predicted intent
delta **0 to +2.0 pp**, and *inside the imported null margin* is an entirely plausible outcome that
would be reported as such.

**Audio2Tool: near zero, and this is the carrier most likely to refute a naive transfer story.**
Only 5.0 % of its clips end on an active frame; the median clip already carries 80 ms of trailing
silence. The mechanism's precondition is largely absent. Predicted overall tool-accuracy delta
**−1.0 to +1.5 pp**. **A null result here is a real result** — it would say the tail is not a
general prompt-side improvement but a repair for a specific media defect, which is the more useful
finding of the two.

If all three land positive and large, the honest reading is *not* "the tail is universally good"; it
is that the study should immediately measure the per-carrier same-request null, because a uniform
gain across three unrelated metrics is also what a systematic harness difference looks like.

---

## 6. What is NOT built, measured rather than guessed

`scripts/cross_carrier_tail2s_wire_check.py` composed all four flyable cells and drove them twice —
`FlightRuntime.preflight` behind the real gate, and `FlightRuntime.wire_check` against a fake gate
and a socket-less transport. Receipt:
`docs/checks/speech-aware-evidence-acquisition/2026-09-07-cross-carrier-tail2s-wire-check/`.
**Zero model contacts, zero servers, zero sockets, zero GPU.** On the first pass every stop was one
of three named classes and none was a surprise; the re-measurements after the rail landed added a
fourth, `seal-and-score-not-ok`, which is an environment refusal rather than a cell's, and it is
named below rather than tidied away.

| cell | rows | preflight | before the rail | after the rail, no other flight | after the rail, under a live flight |
|---|---:|---|---|---|---|
| `R-official-tail2s-smoke-4` | 4 | gate refuses: not authorized | A2T rail missing | **`seal_and_score: OK`** | seal `REFUSED` |
| `R-official-tail2s` | 400 | gate refuses: not authorized | A2T rail missing | seal `REFUSED` | seal `REFUSED` |
| `closed-list-tail2s-smoke-4` | 4 | gate refuses: not authorized | SLURP packet root missing | SLURP packet root missing | SLURP packet root missing |
| `closed-list-tail2s` | 1,000 | gate refuses: not authorized | SLURP packet root missing | SLURP packet root missing | SLURP packet root missing |

**Three measurements, and the committed receipt is the third**, because that is the one taken by the
current driver. Column 4 was measured at commit `99fbc88a`; columns 5 and 6 are the same cells run
again at commit `1308486f`, the second time while another agent's live GPU flight
(`SAEA-E21-KC-E1-BRIEF-44-V1`, `$SPEECHRL_DATA_DIR/locks/flight.lock`, `study_head` `d5e26004…`) was
in the air.

**What column 5 proves, and it is the point of §6.2.** The smoke cell ran the whole request path and
then sealed and scored: 4 canned contacts, `payload_keys=10`, zero sockets, a `COMPLETED` manifest,
the 21-column ledger surface validated, and **all four registered scorers --
`a2t-toolcall-official`, `a2t-toolcall-v2`, `a2t-toolcall` and `cost` -- run to completion over
`@ts2` sample ids**. That is exactly the link §8 item 4 exists to prove, and on this carrier it now
holds. The 400-row cell ran the identical path to the same point -- 400 contacts, same payload keys,
zero sockets -- and was refused at the SEAL for an environment reason that names itself: *"HEAD moved
during the flight: the flight lock recorded study_head ... refusing to bind a COMPLETED manifest to a
commit the flight never ran under"*.

**What column 6 proves is that the refusal is about the environment and not the cell.** Under a live
flight BOTH Audio2Tool cells are refused at the seal, the smoke included, for the same lock reason --
and `REFUSED` means the harness declined to BUILD a `COMPLETED` manifest at all, which is different
in kind from `SCORING_FAILED`, where a manifest sealed and the scorers then failed. The driver now
distinguishes them (`seal-and-score-not-ok`, commit `1308486f`), because before it did not: a cell
that exited 0 with a refused seal was recorded as `stop_class: none` and `reached_the_end: true`, a
green over the one link this check exists to prove.

The lock is **never** removed or edited to get a green. **§8 item 4 therefore stays a live refusal
point for both Audio2Tool cells**: re-run the check when no other flight holds the lock, immediately
before the flight, and require `seal_and_score: OK`. What the wire check is not needed for is the
SCORING itself: all three Audio2Tool scorers were run over the sealed 400 with `@ts2` appended to
every id and reproduce the unsuffixed per-sample entries and aggregates exactly
(`tests/unit/test_variant_id_gold_rail.py::test_the_sealed_audio2tool_400_is_byte_for_byte_unchanged_and_its_variant_matches`).

A second finding, and it was in the CHECK rather than in a cell: the Audio2Tool runner writes its own
per-cell receipt under `docs/checks/` by default, so on the first pass the smoke cell's receipt
landed in the working tree and the 400-row cell's scoring correctly refused a `COMPLETED` manifest on
a dirty tree. The by-product now goes under `$SPEECHRL_DATA_DIR` (commit `99fbc88a`) and this
section's receipt stays the single committed record. It is recorded because it is exactly the failure
mode §8 item 2 warns about, met in a contactless rehearsal instead of after the GPU time was spent.

`preflight` reaching the gate is the CORRECT state and is what it proves: config composition, roster
hydration with a per-file SHA-256 re-hash of all 1,000 / 400 media, media-path confinement to the
variant's own derived root, the count check and `ExecutionPlan` construction all pass, and only then
does `contracts.FrozenCoreGate` refuse with *"has no pre-registered exposure row"*. The SLURP full
cell composes 1,000 samples at config hash `6643cfb2…`; its smoke composes 4 at `e1837235…`.

### 6.1 Precondition A — SLURP packets (blocks 1.2)

`FlightRuntime._speech_feature_root` refuses:
`model fragment speech_feature_root /home/chao/feat-cache/slurp-dev1000-ts2-packets-04ccc72a
disagrees with the promotion receipt's feature_root /home/chao/feat-cache/slurp-q4km-packets-04ccc72a`.
That is the harness working: the packets do not exist because the encode pass of §1.2 has not been
registered or run. **Cost to clear: one `bounded-discovery-probe` row, 1,000 CPU-only contacts,
0 GPU-h, ≈ 37 min wall, gated by a 4-row dry run.**

### 6.2 Precondition B — the `@ts2` gold-id rail (blocks 1.2 and 1.3)

`rails/adapters/audio2tool.py` refuses:
`sample 'tier1_direct:000045@ts2' is not in the frozen audio2tool probe receipt`. The SLURP scorer
resolves gold the same way, by exact `sample_id`, and will refuse identically once its packets exist.

**Earnings-22 already solved this exact problem.**
`reproduction.esb_reference.published_segment_key` splits a derived-media id on `@` to recover the
sealed key, and its docstring records the property that makes it safe: *"An id without a suffix is
returned unchanged, so every population that existed before the convention is byte-for-byte
unaffected."* The equivalent one-line rail is needed at the SLURP and Audio2Tool gold lookups.

**This preparation did not apply it, on purpose.** A gold lookup decides what a sample's ground
truth IS; changing one is a reviewed edit to a paper-facing path, not something a model-free media
build does on its own initiative mid-campaign. It is named here as a precondition with its
precedent, its exact call sites and its inertness property, so whoever does apply it does so
deliberately and with a test that the unsuffixed populations are unchanged.

**CLOSED 2026-09-07** (commit `e6c29449`). The rule now lives ONCE, in
`data.variant_ids.published_sample_key`; `reproduction.esb_reference.published_segment_key` -- the
Earnings-22 spelling -- delegates to it, so the three carriers cannot drift into three spellings.
Four gold lookups resolve through it: `rails/adapters/audio2tool.py::Audio2ToolAdapter.gold` (the
flight-time lookup this wire check stopped at, and the one `CalibrationAdapter` inherits), all three
registered Audio2Tool scorers in `reproduction/a2t_scorer.py` (`a2t-toolcall`, `a2t-toolcall-v2`,
`a2t-toolcall-official`), and `reproduction/slurp_official_eval.py::score_slurp_outputs_official`,
where the published key is ALSO what goes into the official evaluator's own `file` field on BOTH
sides, because that is the key `evaluate.py` pairs on. The RAW id stays in every per-sample row and
every refusal message, so a score file still records which media was flown.

The inertness claim is proved on the SEALED manifests rather than on fixtures
(`tests/unit/test_variant_id_gold_rail.py`). The sealed Audio2Tool official-protocol 400 still
reproduces its own published anchors to the digit -- overall 61.0, exact match 20.25, parse rate
99.75, 52 rows with more than one call match, and all eight tier accuracies of section 1.3 -- and
the same 400 rows with `@ts2` appended to every id give byte-identical per-sample entries and
aggregates through all three scorers. The sealed SLURP DEV-1000 still gives scenario 82.60, action
74.60, intent 73.10 and SLU-F1 35.80, and its `@ts2` twin matches it row for row. A foreign
published key still refuses, suffix or no suffix: the rail strips a suffix, it never widens a gold
closure.

### 6.3 Precondition C — Earnings-21 has no cell to compose at all

**Earnings-21 gets no config fragments, and that is a finding rather than an omission.** Its
90-second windows are cut at RUNTIME by `reproduction.obs_loop` from each whole call
(`obs_boundary_mode: fixed`, `obs_buffer_seconds: 90`, advance = buffer); **nothing in the harness
consumes pre-cut slices** — `scripts/precut_manifest.py` writes a `saea-precut-manifest-v1` document
that no code reads — and the full-44 baseline flies through `core.driver.run_experiment_bundled`
rather than `FlightRuntime`, so it has no `wire_check` to run. A dataset fragment naming the `@ts2`
window media would compose and could not fly.

What the cell needs is **one named, thin obs knob**: a baseline-fragment parameter
(`obs_slice_tail_silence_seconds`, default 0.0) that appends the tail to each emitted slice's PCM
before the slice WAV is written, in `reproduction/obs_loop.py`'s sequential path and its
`_slice_parallel_pass` twin, with the OpenJiuwen executor mirroring it. That is a thin derivation of
the existing registered `obs-agent-loop` policy, not a new base.

**And the committed `@ts2` media is that knob's byte-exact oracle**, which is the reason it was built
for a carrier that cannot yet use it: the cell's falsifier is that **each of the 1,593 slices the
flight emits must hash to the SHA-256 the committed D1 supplement
`docs/receipts/artifacts/d1-e21-buf90-1593-tail2s.json` already records for that window**. A runtime
change that would otherwise be unverifiable becomes a 1,593-of-1,593 identity check.

**CLOSED 2026-09-07** (commit `8b69e2eb`), and the falsifier holds at **1,593 of 1,593**. The knob is
`obs_slice_tail_silence_seconds`, default `0.0`, on the already-registered `obs-agent-loop` policy --
a thin derivation, not a new base. The three cut sites (the sequential path, `_slice_parallel_pass`
and the openJiuwen `FeedBuffer`) now call ONE encoder, `reproduction.obs_audio.encode_slice`, which
with no preprocess and no tail is `write_wav_bytes` and nothing else, so every sealed Earnings run's
bytes are untouched; the ojw equivalence harness gained a `tail-silence` scenario, so the two
executors are PROVED to emit identical slices under the knob rather than asserted to.

The tail changes the DELIVERED bytes only. `SliceRecord.start_seconds`/`end_seconds`/`audio_seconds`
stay the CUT span -- `core.model.SliceRegistry.register` requires `audio_seconds` to equal the span,
and a tail that moved the span would move the next window and destroy the per-window pairing against
the sealed comparator -- while `sha256`/`bytes` describe the file that was actually sent and
`preprocess` declares `tail-silence-2s` with `pre_sha256` chaining back to the sealed cut. Delivered
seconds per window are `audio_seconds + 2.0`, i.e. 144,534.532 s over 1,593 windows against the
harness's own metered 141,348.532 s; the registered ceiling of 150,000 covers the larger figure.

**The cell now composes.** Baseline `e21-buf90-tail2s-scored7` (the sealed fragment with ONE key
added and none changed, plus the three remaining agentic scorer ids so section 4.3's four metrics
come out of `core.scoring_batch`'s verified path -- all four measured to SUCCEED on the comparator's
own sealed outputs first, at roughly 10 s per call for the three text-alignment ones); experiment
`e21-full44-tail2s-v1`; arms file `docs/arms/e21-full44-tail2s-v1.arms`; composed config hash
`3d28fb5abfe2ff6d05cbefac1384e9088504794d9859071a4e5fcc9f16047d22`.

Earnings-21 still has **no `wire_check`**, because it still does not fly through `FlightRuntime`.
What it has instead is `run_experiment_bundled`'s own model-free preflight, and both halves of it
were driven on 2026-09-07 with zero contacts: `compose` (OK), `ObsLoopConfig.from_values` (OK: buffer
90.0, mode fixed, batch_slices 8, tail 2.0), `load_verified_split` (OK: 44 samples, identity
`fcc1b0bc...d69e`), `ExecutionPlan(...).validate()` (OK) and `require_clean_study_repo` (OK on the
committed tree). The half that does NOT run model-free is `run_experiment` itself, which needs a live
llama-server session and the cell's own owner GO and exposure row -- the gate refuses without them,
which is the correct state.

---

## 7. Budgets, geometries and the order to fly them

Paid API spend is 0 and stays 0. Every figure below is a registered ceiling, not an estimate to be
exceeded.

| cell | contacts | audio s | GPU-h | geometry |
|---|---:|---:|---:|---|
| SLURP packet encode (precondition) | 1,000 | 4,885 | **0.0** | CPU sidecar, port 8081, `-ngl 0` |
| SLURP smoke | 8 | 60 | 0.05 | `q4km-…-np8-ts2-packets-max64`, `-c 65536 -np 8` |
| SLURP cell | 1,050 | 5,000 | **0.30** | same |
| Audio2Tool smoke | 8 | 120 | 0.05 | `q4km-featcache-a2t-official-04ccc72a`, `-c 49152 -np 3` |
| Audio2Tool cell | 408 | 3,100 | **0.20** | same |
| Earnings-21 smoke (4 windows) | 8 | 400 | 0.05 | `q4km-e21-buf90-mmproj-gpu-04ccc72a-np6`, `-c 36864 -np 6` |
| Earnings-21 cell | 1,750 | 150,000 | **1.20** | same |

The SLURP and Audio2Tool ceilings are above the ~0.15 and ~0.1 GPU-h the plan sketched, and the
reason is stated rather than hidden: the sealed comparators cost 0.222 GPU-h (Earnings-22 test,
2,735 rows) and ~280 s of wall (Audio2Tool 400) respectively, and each `@ts2` request carries **more
audio than its sealed twin** — SLURP +69 %, Audio2Tool +37 %, Earnings-21 +2.3 % — because 2.0 s is a
large fraction of a 2.9-second utterance and a small one of a 90-second window. The Earnings-21
ceiling is the sealed run's own 0.9734 GPU-h plus headroom, not the plan's 0.8.

**Three different geometries, so three resident sessions, and the order minimises switches to
exactly two.** The coordinator runs one resident server per geometry
(`docs/readiness/2026-09-07-always-on-serving-operating-note.md`); a flight attaches and never stops
it.

**AMENDED 2026-09-07, after two of the three preconditions closed.** The order below supersedes the
one this section first fixed, and the reason is a change of FACT, not of preference: §6.2's gold-id
rail and §6.3's obs knob are applied and tested, so Earnings-21 -- recorded above as having *no cell
to compose at all* -- now composes and is the readiest carrier, while SLURP is the only one still
waiting, on a 1,000-contact CPU encode. Cost order and readiness order no longer agree, and readiness
wins: a ready flight occupies the GPU, and no cell reserves an idle card. The switch count is still
exactly two.

1. **`-c 36864 -np 6` — Earnings-21.** First, because it is the only cell whose every precondition is
   closed and whose falsifier has already been checked offline at 1,593 of 1,593. Smoke on four
   windows -- its media falsifier must hold on 4 of 4 -- then the 1,593. It is also the most expensive
   cell, so putting it first is what keeps the rest of the campaign off the critical path.
2. **`-c 49152 -np 3` — Audio2Tool.** Cheapest cell, smallest population; its precondition was a code
   rail and that rail is in, with the smoke cell measured at `seal_and_score: OK` once no other
   flight held the lock. Both cells still owe that tick under §8 item 4 at flight time (§6's table
   says why). Smoke, then the 400.
3. **The SLURP packet encode**, on the CPU sidecar, alone. It needs no GPU session, so it can occupy a
   GPU gap — but it must not overlap a GPU flight: the campaign CPU cap is 8 workers and this program
   has already recorded that two resident CPU embedders broke bit-exactness on a paired comparison.
   Row `SAEA-SN-DEV1000-TS2-PREPROCESS-V1` is registered `consumed = no`; the 4-row gate runs first.
4. **`-c 65536 -np 8` — SLURP.** Its packets are warm by now, its baseline fragment pins the new
   promotion receipt, and its wire check has been re-run to `seal_and_score: OK`. Smoke, then the
   1,000.

Official scoring of each cell overlaps the next flight, once per complete manifest through
`core.scoring_batch`, never sharded.

---

## 8. The flight checklist — one agent per cell

Every item is a refusal point. An agent that cannot tick one stops and reports; it does not proceed.

1. The cell's **owner GO** is recorded, and its **exposure row is written before the first contact**,
   carrying the profile, the population, the split identity, the ceilings and the inherited exposure.
2. The tree is **clean** at a committed study commit, and `PYTHONDONTWRITEBYTECODE=1` is exported —
   a dirty tree and stray bytecode each close the scoring gate at finalize, after the GPU time is
   spent.
3. The cell's **precondition is closed**. Audio2Tool's and SLURP's gold-id rail: **CLOSED**
   (§6.2). Earnings-21's obs knob and its 1,593-of-1,593 hash check against the committed `@ts2`
   media: **CLOSED** (§6.3). SLURP's packets promoted with their receipt, and the cell's baseline
   fragment then pinning that receipt and its SHA-256: **OPEN**, and it is the only one.
4. The **zero-contact wire check is re-run and reaches `seal_and_score: OK`** on this cell's own
   fragments. A manifest that seals `COMPLETED` and then will not score wastes GPU time after it has
   been spent. The Audio2Tool smoke has been measured at OK once (§6, column 5); both Audio2Tool
   cells are refused at the seal whenever another flight holds
   `$SPEECHRL_DATA_DIR/locks/flight.lock`, so this tick has to be taken with the lock free,
   immediately before the flight -- and that lock is never removed or edited to get a green. The two
   SLURP cells cannot tick it at all until item 3's promotion exists. Re-running the check is a
   refusal point, not a formality.
   Earnings-21 has no `wire_check` at all — it does not fly through `FlightRuntime` — so its
   equivalent is `run_experiment_bundled`'s own model-free preflight, driven in §6.3 and re-driven
   before the flight.
5. The **4-row smoke** flies first and its media falsifier (§4.4) holds on 4 of 4.
6. The agent **attaches** to the coordinator's resident session for its geometry; it never starts or
   stops a server and never touches port 8080.
7. The full cell flies **once**. At most one recovery re-registration; a second failure stops the
   flight and the fix is proven on a 4-row dry run.
8. The **media falsifier of §4.4 is checked on every flown row BEFORE any score file is opened**, and
   the row count, audio seconds and GPU-hours are reconciled against the registered ceilings.
9. Scoring runs **once over the complete sealed manifest** through `core.scoring_batch`, verified,
   never sharded, never shard-averaged.
10. The **identity gate of §2** passes — the sealed comparator reproduces its own published anchors
    to the digit — before the first contrast is computed.
11. The verdict quotes §4's rule **verbatim before applying it**, carries the per-stratum table, and
    states which null it used and whether that null was measured or imported.

### 8.1 The exact command per cell

Every command below runs in WSL2 `Ubuntu-24.04` under `source ~/.venvs/speechrl/bin/activate`, from
the study checkout, with `PYTHONDONTWRITEBYTECODE=1` exported (§8 item 2) and on a clean tree at a
committed study commit. **None of them is authorized by this document**: each needs its cell's own
owner GO and its own exposure row first (§8 item 1). Nothing here starts or stops a server; a flight
attaches to the coordinator's resident session for its geometry (§8 item 6).

**1. Earnings-21 — `-c 36864 -np 6`.** Not a `FlightRuntime` cell: it flies through
`core.driver.run_experiment_bundled` via the committed launcher, exactly as its sealed comparator
did.

```bash
# the full cell, 1,593 windows over 44 calls -- AFTER the four-window smoke below
bash scripts/run_arm_sequence.sh \
  --arms docs/arms/e21-full44-tail2s-v1.arms \
  --dataset earnings21-discovery \
  --experiment e21-full44-tail2s-v1 \
  --model q4km-e21-buf90-mmproj-gpu-04ccc72a-np6 \
  --execution-profile baseline-reproduction \
  --planned-model-calls 1750 --planned-gpu-hours 1.2 \
  --planned-speech-audio-seconds 150000
```

The four-window smoke needs one thing this document does NOT hand it: a dataset fragment naming a
single short call. `earnings21-discovery` is the whole 44 and `run_arm_sequence.sh` has no sample-id
seam, so the smoke is a one-call sibling fragment with its own run id and its own exposure row, and
writing it is the flight agent's step. What the smoke still has to prove is the RUNTIME path -- that
the emitted slice bytes reach the server and that its four slice SHA-256s equal the committed `@ts2`
entries for those windows, checked before any score file is opened. What it no longer has to
discover is whether the knob produces the right bytes at all: that is already proved offline, with
zero contacts, on all 1,593 windows
(`tests/unit/test_obs_slice_tail_silence.py::test_the_knob_reproduces_every_committed_ts2_window_hash`).

**2. Audio2Tool — `-c 49152 -np 3`.**

```bash
python scripts/flights/run_calibration_cell.py \
  --experiment a2t-official-protocol-tail2s-400-smoke-v1 \
  --dataset audio2tool-calibration-400-tail2s-smoke4 \
  --cell R-official-tail2s-smoke-4 --run
python scripts/flights/run_calibration_cell.py \
  --experiment a2t-official-protocol-tail2s-400-v1 \
  --dataset audio2tool-calibration-400-tail2s \
  --cell R-official-tail2s --run
```

**3. The SLURP packet encode — CPU sidecar on port 8081, 0 GPU-h.** Contract
`configs/experiment/slurp-dev1000-ts2-preprocess.json` (composed config hash `67b4e7ec…`), sidecar
fragment `configs/model/q4km-preprocess-featcache-cpu-sidecar-slurp-ts2.json`, dataset fragment
`slurp-speech-native-dev1000-tail2s`, baseline fragment `speech-native-preprocess`, row
`SAEA-SN-DEV1000-TS2-PREPROCESS-V1` (registered `consumed = no`, 1,004 contacts, 4,905 audio
seconds, 0 GPU-h). The two-phase driver is the one `SAEA-SN-DEV1000-PREPROCESS` and
`SAEA-SLURP-EVO-FOLD-PACKETS-V2` used (`scripts/slurp_evo_fold_preprocess.py` is the shape: encode
under a session receipt, verified normal stop, then
`materialize_legacy_cached_speech_feature_packets`); binding it to THIS contract is the flight
agent's step, and so is the 4-row gate that precedes the 1,000.

**4. SLURP — `-c 65536 -np 8`, after the promotion.** Two things must land first: a baseline
fragment that pins the new promotion receipt and its SHA-256 (`FlightRuntime._speech_feature_root`
refuses a root the flight's identity does not pin), and a re-run of

```bash
python scripts/cross_carrier_tail2s_wire_check.py --write
```

reaching `seal_and_score: OK` on both SLURP cells. Then:

```bash
python scripts/flights/run_slurp_closed_list_cell.py \
  --experiment slurp-dev1000-closed-list-tail2s-smoke-4-v1 \
  --dataset slurp-speech-native-dev1000-tail2s-smoke4 \
  --cell closed-list-tail2s-smoke-4 --run
python scripts/flights/run_slurp_closed_list_cell.py \
  --experiment slurp-dev1000-closed-list-tail2s-v1 \
  --dataset slurp-speech-native-dev1000-tail2s \
  --cell closed-list-tail2s --run
```

**Scoring, all three carriers.** Once per complete sealed manifest through `core.scoring_batch`,
never sharded (§8 item 9), overlapping the next flight. The Earnings-21 cell declares all seven of
its scorer ids in its own manifest, so its four agentic metrics come out of that verified path; all
four were re-run against the sealed comparator's own outputs on 2026-09-07 and reproduce §1.4's
figures to the digit -- `asr-wer-whisper` corpus WER 8.19952 against §1.4's 8.1995,
`conec-entity-wer-official` 8.19952 against its 8.200, `numeric-value-accuracy-v1` 90.73351 against
its 90.7335, and `semantic-high-impact-error-rate-v1` running clean -- which is §2's identity gate
for this carrier, already passed offline and at zero contacts.

---

## 9. What none of these cells can conclude

* **Nothing about the test split of any carrier.** SLURP DEV-1000 is a dev-tier optimization
  population; Audio2Tool's 400 and Earnings-21's 44 are discovery. No published-number comparison is
  licensed from any of them, and the standing Earnings-22 rule applies unchanged: a media-changed
  number is never reported as a like-for-like reproduction of a published protocol.
* **Nothing about generalization or superiority**, and nothing that belongs to Stage-3.
* **Not that the tail is the last difference**, and not that the encoder pad was removed: appending
  whole mel blocks leaves the residue `(n_samples // 160) % 100` unchanged, so the same padded block
  is still sent, two seconds later.
* **Not that a positive result on one carrier predicts another.** That is the hypothesis under test,
  and §5 signs three different predictions precisely so that the answer cannot be read backwards
  from whichever cell happens to fly first.
