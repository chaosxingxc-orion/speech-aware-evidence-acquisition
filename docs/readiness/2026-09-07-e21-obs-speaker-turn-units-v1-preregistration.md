# OBS-E1 — the Earnings-21 transport unit becomes the speaker turn

**Status (2026-09-08): PREREGISTERED, COMPOSABLE, AND STILL NOT AUTHORIZED TO FLY.** The obs seam
of §8 has landed and the cell now composes; the two things it still lacks are **its own exposure row
and the owner's GO**. Nothing in this document is an authorization, and the fragments of §9 are a
launch record, not a permission. The superseded status line read: *"PREREGISTERED, NOT AUTHORIZED TO
FLY, AND NOT YET COMPOSABLE — the cell needs three things it does not have: the obs seam of §8
implemented (it cannot be, until `wt/ts2y`'s tail knob merges — §8.0), its own exposure row, and the
owner's GO."* See the dated update below; **no rule, margin, stratum, budget or decision criterion in
this document is changed by it.**

Owner thesis, 2026-09-07: **cut the speech by SPEAKER first, then understand per speaker.** The
measurement behind it is already sealed — a fixed 90-second cut has no reason to land in a pause and
does not.

| | |
|---|---|
| model-free predecessor | `SAEA-E21-MF-SPEAKER-TURN-UNITS-V1`, receipt `docs/checks/speech-aware-evidence-acquisition/2026-09-07-e21-speaker-turn-units/` |
| unit plan | `docs/receipts/obs/e21-speaker-turn-units-v1.json`, schema `saea-e21-speaker-turn-units-v1`, **5,288 units over 44 calls** |
| comparator | `SAEA-E21-FULL44-DIRECT-BASELINE-V2`, attempt `attempt-20260904T233816Z-bcd338` |
| comparator identity | config `e4b133d1…`, protocol `06f7f308…`, split `fcc1b0bc…d69e` |
| execution profile | `bounded-discovery-probe` |
| split role | `discovery` |
| program context | `docs/readiness/2026-09-05-three-dimension-experiment-program.md` (the OBS dimension) |

---

## Update — 2026-09-08: the seam landed, and what is left

**This section records facts and closes preconditions. It changes no rule and no budget:** §5's
equal-contact statement, §6's decision rule and −0.30-point margin, §7's 5,800 calls / 165,000 speech
seconds / 3.5 GPU-hours against their 6,000 / 170,000 / 4.0 ceilings, §8's spec and §10's claim
surface all stand exactly as written.

**The seam is implemented.** `wt/ts2y`'s tail knob and its one encoder merged, so §8.0's sequencing
condition is met and §8 was built to. `reproduction.obs_loop.ObsLoopConfig` knows `obs_unit_plan` and
`obs_unit_plan_sha256`, both defaulting to `null`; both cut sites of the registered `obs-agent-loop`
policy consume the plan's units in `unit_index` order through the SAME
`reproduction.obs_audio.encode_slice` and the SAME `obs_slice_tail_silence_seconds` knob; the OBS
record carries `obs_unit_id`, `obs_unit_speaker` and `obs_unit_end_cut` beside the unit bounds; and
`saea-obs-derivation-v1` names the plan it was cut by and records `boundary_mode` `"unit-plan"`. Two
things §8 did not spell out are recorded here rather than left to a reader. First, §8.2's items 3 and
4 — a roster call the plan does not cover, and a plan block whose `decoded_duration_seconds`
disagrees with the runtime decode — cannot be decided by `from_values`, which sees neither the roster
nor the audio; they are enforced by `UnitPlan.units_for`, called once per sample **before that
sample's first window is cut**, which is the fail-closed property §8.2 asks for. Second, the
openJiuwen executor's `window_frames` is clock-derived by construction, so it **refuses** a unit plan
by name rather than silently cutting fixed windows for a config that asked for units; the cell's own
`obs_batch_samples 1` puts it on the plain policy, where `obs_batch_slices 8` stays legal exactly as
§8.2 argues.

**§9's fragments compose, and the receipt says so with numbers.** Model-free row
`SAEA-E21-MF-OBS-E1-SEAM-V1`, receipt
`docs/checks/speech-aware-evidence-acquisition/2026-09-08-e21-obs-e1-seam/`, **result PASS with zero
failures, zero model contacts and zero sockets**, study commit `aaf926eb`.

| | |
|---|---|
| composed config hash | `06e1eb28a5b3fcce31deb9191db5114cb859dae5f584380ee2c5b7c20659fdfc` |
| composed protocol hash | `cb5e964fb82a00a7b7d15506d03ebed619b8f72318b4cfea02b5fe36f9bdc331` |
| split identity | `fcc1b0bc…d69e`, unchanged |
| plan pin | `fed5188b…`, matching the baseline fragment's `obs_unit_plan_sha256` |
| units loaded and re-tiled | **5,288 over 44 calls**, against the comparator's 1,593 windows |
| unit seconds | min **0.001**, median **16.06**, mean **26.73**, max **90.00** |
| cut / delivered seconds | **141,345.852687** / **151,921.852687**, the §2 figures to the digit |
| coverage | 44/44 calls carry units; 44/44 plan durations equal that call's own sealed 90-second window total |
| payload-binding stage | BOUND, rows `4320211` and `4397829` of 44 |

**§8.6's falsifier holds, on real bytes, 4 of 4.** The contact-free dry run cut **172 units over four
calls** — 4386541 (34), 4387332 (51), 4392809 (49) and the no-pause call 4366522 (38) — from PCM
reconstructed out of the comparator's own sealed 90-second slices, through the real policy, the real
`SliceRegistry` chain and the real `TraceSink`. Every unit reproduced its planned span with
`audio_seconds` still equal to it, `iteration = unit_index - 1`, exactly one `tail-silence-2s`
transform, `pre_sha256` chaining to the untailed cut, and the `bare-core` D2-frozen ten as the whole
payload key set; and concatenating each call's delivered slices with the 2.0-second tails removed
reproduced that call's **committed `saea-diarization-v1` `audio_sha256`** exactly. Byte-identity in
the other direction is proved too: with the keys `null`, replaying call 4386541's own 13 sealed
windows through the seam-carrying cutter reproduces every one of that call's committed
`source_audio_sha256` values, and the key-absent and explicitly-`null` runs agree byte for byte on
media, records, trace and outcome on both executor paths (`tests/unit/test_obs_unit_plan.py`).

**One property named before any score is read, not after.** The plan's shortest unit is **0.001 s**,
17 units are under 0.1 s and 166 under 1.0 s, all flagged `short-kept`. A flight therefore sends some
16-sample cuts under a 2.0-second tail. This is a property of the model-free plan — §4's `<1 s`
stratum already counts 166 of them, and §10 fixed the 1.0-second minimum before any score existed —
not a decision this seam makes, and §4's unit-length stratum is where the verdict reports it.

**Preconditions, restated (§9's list, as it now stands).**

| §9 precondition | state |
|---|---|
| the obs seam of §8, with its byte-level falsifier passing | **CLOSED 2026-09-08** — seam landed; falsifier 4/4 on real bytes |
| a 4-row dry run of the composed cell | **CLOSED 2026-09-08** — four calls, 172 units, contact-free, PASS |
| this cell's own exposure row, registered with `consumed = no` before the first contact | **OPEN** — `SAEA-E21-MF-OBS-E1-SEAM-V1` covers the model-free check only and authorizes nothing |
| the owner's GO | **OPEN** |

**The flight command, once those two close.** The cell is `E21-obs-e1-speaker-turn-units` of
`configs/experiment/e21-obs-e1-speaker-turn-units-v1.json`, and it attaches to the coordinator's
resident session rather than starting one (owner's 2026-09-07 always-on serving ruling), which is how
`SAEA-E21-FULL44-TAIL2S-V1` flew on this same geometry:

```
saea-driver run \
  --model q4km-e21-buf90-mmproj-gpu-04ccc72a-np6 \
  --dataset earnings21-discovery \
  --baseline e21-units-obse1-scored7 \
  --experiment e21-obs-e1-speaker-turn-units-v1 \
  --plan <the ExecutionPlan file: bounded-discovery-probe, discovery, 5,800 calls,
          165,000 speech audio seconds, 3.5 GPU-hours -- section 7, unchanged> \
  --run-dir $SPEECHRL_DATA_DIR/runs/SAEA-E21-OBS-E1-SPEAKER-TURN-UNITS-V1 \
  --runtime-root /home/chao \
  --session-receipt <the resident -c 36864 -np 6 session's receipt>
```

Environment as every Earnings-21 flight on this geometry: WSL2 `Ubuntu-24.04`,
`source ~/.venvs/speechrl/bin/activate`, `PYTHONDONTWRITEBYTECODE=1`, `PYTHONPATH=<checkout>/src`,
`SPEECHRL_DATA_DIR` as pinned, no `LLAMA_MTMD_FEAT_CACHE_DIR`. `scripts/run_arm_sequence.sh` is
deliberately **not** used: it starts a server, and this flight attaches. §7's stop rules are
unchanged — the smoke's measured rate is projected to the full pass and the flight stops and reports
if it projects past 4.0 GPU-hours.

---

## Update — 2026-09-08 (v2): the coordinator's minimum-duration rule, re-pinned and re-verified

**This section records facts and re-pins one input. It changes no RULE**: §5's equal-contact
statement, §6's decision rule and −0.30-point margin, and §8's spec and §10's claim surface all stand
exactly as written, applied now to a different plan. What moves is which plan the fragments name and
the NUMBERS that follow from it — every count in §§1–4 and §7 that names `5,288`, `26.73`, `16.06`,
`151,921.853`, `166` or the flight command's `5,800 / 165,000 / 3.5` is v1's own, superseded here, not
edited there.

**The coordinator's decision (2026-09-08, under the owner's OBS-E1 GO):** *"a 16-sample unit wrapped
in a 2-second tail is a diarizer artifact, not a transport unit."* Plan v2
(`analysis.e21_speaker_turn_units.plan_units_v2`, schema `saea-e21-speaker-turn-units-v2`) keeps v1's
rules 1–3 and 5 byte for byte and replaces v1's rule 4 — a short span kept unless a SAME-speaker
neighbour is reachable across a non-turn-change boundary — with one explicit exception to rule 1: **a
span under 1.0 s merges into whichever ADJACENT unit is LONGER, of EITHER speaker, ties going to the
PRECEDING neighbour**; the 90 s cap still holds (a merge that would break it tries the other
neighbour, and a sliver with no admissible neighbour on either side keeps its sliver and is flagged
`short-kept`, same as v1). Built model-free from the identical two sealed inputs v1 used (exposure row
`SAEA-E21-MF-SPEAKER-TURN-UNITS-V2`, receipt
`docs/checks/speech-aware-evidence-acquisition/2026-09-08-e21-speaker-turn-units-v2/`); a v1 rebuild
against those same inputs reproduced the committed v1 plan byte for byte (`fed5188b86d6...`) before
v2 was cut.

**The new counts.** 5,122 units over the 44 calls (v1: 5,288, −166). Unit seconds min **1.001**
(v1: 0.001), median **17.775** (16.060), mean **27.596** (26.730), max **90.000** unchanged.
**Units under 1.0 s remaining: 0 of 5,122** — v1's own 166, all `short-kept`, are now zero. 166
pre-merge slivers absorbed into 166 surviving units — 153 flagged `cross-speaker-merge`, 13
`same-speaker-merge` — with 174 total absorbed-sliver records (159 units absorbed one, 6 absorbed
two, 1 absorbed three: a cascade). Cut audio is exactly conserved, **141,345.852687 s**, identical to
v1 and to the sealed 1,593-window total; delivered audio is **151,589.852688 s** (v1:
151,921.852688), a delta of exactly `−166 × 2.0 s = −332.000 s`. Purity mean rises slightly, 0.9431 →
0.9506. §4's strata are recomputed at the v2 grain in the same receipt (dominance 4,916/147/+59
silent; speakers 0/1/2/≥3 = 59/3,898/1,126/39; length `<1s/1–10s/10–60s/≥60s` = 0/2,006/2,284/832; cut
kind pause/turn-boundary/forced-cap-split/call-end = 4,387/676/15/44, the latter two identical to v1
by construction since rules 1–3 are shared). The no-pause call `4366522` carries 36 units, not 38: a
0.966 s same-speaker sliver and a 0.646 s sliver that crossed a speaker change both merged into their
respective longer neighbours; all 36 still end on an active frame.

**Re-pinned and re-verified.** `configs/baseline/e21-units-obse1-scored7.json`'s `obs_unit_plan` /
`obs_unit_plan_sha256` now name the v2 plan (`0f5f013959b89fa0acc3bb366324e701cbe3a022f7b29ef3e364d621d98eb03b`,
was `fed5188b86d672b2d2a9c8f1b55dc51fe5712776fc06cc938dc759854d52026a`).
`reproduction.obs_loop.OBS_UNIT_PLAN_SCHEMAS` now accepts **both**
`saea-e21-speaker-turn-units-v1` and `-v2`, so v1's own receipts, fragments and tests are unaffected
by this re-pin. §8.2's refusals, the falsifier and the payload-binding stage were all re-run against
the re-pinned fragments and PASS again:

| | v1 (2026-09-08) | v2 (2026-09-08) |
|---|---|---|
| composed config hash | `06e1eb28a5b3fcce31deb9191db5114cb859dae5f584380ee2c5b7c20659fdfc` | `4e5549ee9eed1187251439cfaf4dc2b3a4da6d54ef842e6b7993cb4c4907b027` |
| composed protocol hash | `cb5e964fb82a00a7b7d15506d03ebed619b8f72318b4cfea02b5fe36f9bdc331` | `39b7cc2c4b071467bd876ca686ffd119ba2168563a568e32100a238b1b60d314` |
| units loaded and re-tiled | 5,288 / 44 calls | **5,122 / 44 calls** |
| coverage | 44/44 calls, 44/44 durations | 44/44 calls, 44/44 durations |
| dry-run units (4386541/4387332/4392809/4366522) | 34/51/49/38 = 172 | **33/50/48/36 = 167** |
| §6 falsifier | PASS 4/4 | **PASS 4/4** |
| payload-binding stage | BOUND, rows `4320211`/`4397829` | **BOUND, rows `4320211`/`4397829`** |
| study commit | `aaf926eb` | `b537a594` |

Receipt: `docs/checks/speech-aware-evidence-acquisition/2026-09-08-e21-obs-e1-seam-v2/` (`wire-check.json`,
`MANIFEST.sha256`), same schema `saea-e21-obs-e1-seam-wire-check-v1`, result **PASS**, zero failures,
zero contacts. This does **not** open a second exposure row: it is a dated **ATTEMPT 2** entry folded
into the SAME row `SAEA-E21-MF-OBS-E1-SEAM-V1` v1's wire check closed under, in
`docs/exposure-ledger.md`.

**The contact budget, recomputed by the same formula v1 used.** `planned_model_calls` = the v2 unit
count plus 10 % retry headroom = `ceil(5,122 × 1.10) = 5,635` (against the unchanged registered
ceiling of 6,000). `planned_speech_audio_seconds` = v2's own delivered audio times the same 10 %
headroom = `151,589.852688 × 1.10 = 166,748.838`, rounded up to **167,000** (unchanged ceiling
170,000). `planned_gpu_hours`: BRACKETED from the comparator's realized **0.9734 GPU-h** for 1,593
contacts over 141,345.85 s at this exact geometry, scaled by v2's OWN delivered audio and contact
count — audio-proportional `0.9734 × 151,589.853 / 141,345.853 = 1.044` GPU-h (the floor), contact-
proportional `0.9734 × 5,122 / 1,593 = 3.130` GPU-h (the ceiling), both strictly below v1's own
1.05 / 3.23 brackets because v2 has fewer, though individually slightly longer, units than v1 over the
same 44 calls. Applying the same margin v1 applied to its own contact-proportional ceiling
(`3.5 / 3.23 = 1.083×`) gives `3.130 × 1.083 = 3.4` GPU-h planned, against the **unchanged 4.0-hour
ceiling** — v2 needs strictly less of all three registered quantities than v1 did, so v1's ceilings
already bound v2 with more margin than they bounded v1, and none of the three registered ceilings
moves. `configs/experiment/e21-obs-e1-speaker-turn-units-v1.json`'s `execution_plan` /
`execution_plan_basis` carry these three recomputed figures and the formula that produced them; the
flight command block above is v1's own historical record and is superseded by this paragraph's
numbers, not rewritten in place.

**Preconditions, restated again.** The two items §9 already recorded CLOSED (the obs seam, the 4-row
dry run) are re-closed against the v2 plan by the table above; the two still OPEN are unchanged by
this update: this cell's own exposure row (still none, `SAEA-E21-MF-OBS-E1-SEAM-V1` covers the
model-free checks only and authorizes nothing) and the owner's GO.

---

## 1. The one factor

OBS-E1 is the sealed full-44 direct baseline with **the transport unit replaced and nothing else**.

| held byte-identical to the comparator | value |
|---|---|
| task instruction | `Transcribe the speech verbatim exactly as spoken. Never insert, repeat, or add any word you do not clearly hear in the audio. Output only the transcript text.` |
| arm / policy / evidence | `bare-core` / `obs-agent-loop` / `none` |
| D1 identity | dataset fragment `earnings21-discovery`, carrier `earnings21-original`, split `discovery`, split identity `fcc1b0bc55432d02347dcdf730c6bcef561a9b0ad9605c45b367e1ed3da5d69e`, all 44 calls |
| model fragment | `q4km-e21-buf90-mmproj-gpu-04ccc72a-np6` |
| serving geometry | `-c 36864 -np 6`, slot 6,144, `GGML_CUDA_DISABLE_GRAPHS=1`, bf16 mmproj resident on the GPU |
| decoding | greedy, `temperature 0`, `seed 20260803`, `max_tokens 1024`, `id_slot per-sample` |
| build | `04ccc72a2207347ca76161b93fd9d846dd0a8675`, Q4_K_M, no `LLAMA_MTMD_FEAT_CACHE_DIR` |
| audio path | raw audio through the GPU-resident bf16 mmproj; no MP3 re-decode, no resample, `ffmpeg` absent |
| stitch | `" ".join(span for span in accepted_spans if span)`, unchanged |

**The factor that moves:** the OBS loop stops cutting `ceil(D / 90)` fixed windows and cuts the
call into the plan's **speaker-turn units** instead — a unit that never crosses a diarized speaker
change, never ends inside active speech where a pause of ≥ 300 ms sits within 2.0 s of the turn
change, is capped at 90 s, has a 1.0-second minimum, and carries a 2.0-second digital silence tail on
the delivered media only.

**The 90-second slot fit is unchanged and needs no re-certification.** No unit exceeds 90 s
(`assert_tiles` refuses a plan that contains one), so the worst request is still the 2,258-token
90-second window the slot receipt certified at 2.72× against the 6,144-token slot.

**Two things ride along with the factor and are named rather than hidden.** The units are *more
numerous* (5,288 against 1,593) and *shorter* (mean 26.73 s against 88.73 s). Those are properties of
"the transport unit is the speaker turn", not separable knobs, and §5 says exactly what that costs
the claim.

## 2. What the model-free row already established

From the committed receipt, measured on the cut and not on the model:

| | fixed 90-s windows (sealed) | speaker-turn units |
|---|---:|---:|
| contacts | 1,593 | **5,288** |
| mean / median unit seconds | 88.73 / 90.00 | **26.73 / 16.06** |
| **ends on an ACTIVE frame** | **1,043 (65.5 %)** | **617 (11.7 %)** |
| exactly one speaker | 645 (40.5 %) | **4,024 (76.1 %)** |
| `dominated` at 0.60 | 1,351 (84.8 %) | **5,034 (95.2 %)** |
| mean dominant-speaker share | — | **0.9431** (median 1.0000) |
| cut audio | 141,345.853 s | 141,345.853 s |
| delivered audio | 141,345.853 s | **151,921.853 s** (+7.48 %, all tail) |
| attributed reference words | 359,765 | 359,765 |

The plan tiles every call, so the cut audio is conserved to the digit and the whole delivered-audio
delta is `5,288 × 2.0 s`. **The sealed baseline's windows do not overlap** — `obs_boundary_mode:
fixed` with advance = buffer tiles each call once — so there is no overlap credit to net out.

## 3. The comparator, by name and by number

`SAEA-E21-MF-AGENTIC-METRIC-BASELINE-V1` and `SAEA-E21-MF-SEMANTIC-IMPACT-BASELINE-V1` on the sealed
`SAEA-E21-FULL44-DIRECT-BASELINE-V2` outputs. All 44 calls, which is this cell's population:

| metric | sealed value |
|---|---:|
| `asr-wer-whisper` corpus WER | **8.1995 %** (S 13,098 / D 5,701 / I 10,700 over 359,765 reference words) |
| `conec-entity-wer-official` **PERSON** | **22.5 %** over 2,917 reference words |
| ORG / GPE / LOC / PRODUCT / EVENT / NORP / FAC | 17.2 / 18.7 / 2.5 / 19.2 / 2.4 / 9.7 / 21.3 |
| non-entity | 4.730 % |
| `numeric-value-accuracy-v1` | **90.7335 %** over 9,734 values |
| `semantic-high-impact-error-rate-v1` (negation-critical) | **0.02780 %**, taxonomy `e22-semantic-scan-2026-09-06-content-impact-word-pair-v1` |

Pairing rules from the agentic-metric note §7 hold unchanged: same roster (all 44, so the all-44
column and never the evaluation-ten column), same scorers through `core.scoring_batch` over one
complete verified manifest, never sharded; and **the headline for a mechanism is the entity and
numeric line, not corpus WER**, with corpus WER kept as the anchor and as the harm check.

**PERSON is the metric this cell is aimed at**, and the reason is in the comparator note: PERSON at
22.5 sits between ConEC row 8 (Whisper large, 28.9) and ConEC's own post-hoc oracle (13.0), so it is
the one published class with room. ORG is already below ConEC's oracle at 17.2 vs 17.7 and is
reported without an expectation.

## 4. Pairing and statistics

**The paired unit is the CALL, and the reason is structural, not a preference.** The comparator's
1,593 windows and this cell's 5,288 units do not align one to one, and no construction makes them:
a unit boundary is placed by speaker changes and pauses, a window boundary by a clock. So the two
arms share exactly one level at which both produce a complete, comparable quantity — the call's own
pooled metrics over its own reference words.

* **44 clusters, one per call**, ids = the 44 `earnings21-original` discovery sample ids.
* `analysis.paired.resampled_statistic` with the pooled ratio as the statistic (`sum(numerator) /
  sum(denominator)` over the resampled ids — corpus WER, ConEC entity WER and numeric accuracy are
  all of that shape), **seed 20260903, 10,000 replicates, CI90**, matching
  `analysis.e21_window_pairing.E21_WINDOW_*` so two reads of the same rows cannot silently differ.
* The estimand is the **pooled delta**, comparator − cell, in points, positive = improvement.

**n = 44 is below the program's `n >= 400` rule for a paired effectiveness claim, and this cell does
not clear it.** That is the exact situation the owner's 2026-09-06 ruling addressed by pairing
Earnings at the window; replacing the window with a unit that does not align breaks that answer.
**So OBS-E1 reports an interval and a direction, never a paper-facing effectiveness claim.** A claim
of that tier needs the confirmatory route, which is Stage-3 and is not available here.

**One secondary read is preregistered, labelled, and reported beside the primary.** Both arms'
alignments can be charged to the sealed 90-second window grid by REFERENCE index rather than by
hypothesis index: the reference is the same string in both arms, the sealed window rows partition it
into 1,593 consecutive index ranges, and every substitution, deletion and hit carries a reference
index that falls in exactly one of them (an insertion carries none and goes to the window its
reference cursor stands in, the symmetric convention `charge_operations_to_windows` already uses for
the hypothesis cursor). That yields **1,593 paired rows on a common refinement**, and it buys exactly
what the window-pairing module says a window unit buys: a saves / harms / ties count and the
per-window strata — **not extra power.** Clustering by call, the interval it produces is
arithmetically the same as §4's; a verdict that quotes the 1,593-row interval as if it were the
honest one is misreading this section, and the honest one is the 44-cluster interval above.

**Strata, reported and never used as a knob.** From the sealed `saea-diarization-v1` artifact at the
UNIT grain via `reproduction.diarization.window_speakers` on each unit's own bounds:

| stratum | grain | cell's own distribution |
|---|---|---|
| dominance | `dominated` / `shared` at the 0.60 threshold — **the primary stratum**, because the tool's `speaker_count` saturates at four | 5,034 / 153 (+101 silent) |
| speaker count | `speakers=0/1/2/>=3` | 101 / 4,024 / 1,128 / 35 |
| unit length | `<1 s` / `1–10 s` / `10–60 s` / `>=60 s` | 166 / 2,010 / 2,281 / 831 |
| cut kind | `pause` / `turn-boundary` / `forced-cap-split` / `call-end` | 4,471 / 758 / 15 / 44 |
| the no-pause call | `4366522` alone — zero pauses of ≥ 300 ms over 1,817.7 s, all 38 of its units end on an active frame | reported apart, never pooled away |
| sector and sample rate | the two strata the Earnings-21 release itself reports | as the comparator |

Every verdict table carries the per-stratum breakdown, natural-mixture and equal-stratum weighted,
per the 2026-09-03 reporting rule.

## 5. The equal-contact question, stated before the flight

**A contact-matched control is impossible by construction, and this section exists so that fact is
on the record before any number is read.** The cell sends 5,288 contacts against the comparator's
1,593 because a call cut at its speaker turns yields 5,288 pieces; there is no way to cut the same
call into speaker-turn units *and* into 1,593 of them. So the contrast is not "speaker-aligned
boundaries, all else equal" — it is **the transport unit as a whole**, and it confounds three things
that move together:

1. **boundary placement** (11.7 % of cuts land mid-speech against 65.5 %),
2. **speaker purity** (76.1 % single-speaker units against 40.5 %),
3. **contact count and length** (5,288 × 26.73 s against 1,593 × 88.73 s).

**Both arms report contacts and delivered audio seconds in the verdict's first table**, and the
verdict states this confound in the same paragraph as the headline number, every time.

**The control that DOES exist is named here and is not this cell.** A fixed-window arm at
`obs_buffer_seconds = 26.73` would deliver 5,288 windows on the same calls — matched in contact count
and mean length, unmatched in boundary placement and speaker purity. That arm (call it **OBS-E1b**)
is the clean decomposition of factor 3 away from factors 1 and 2, it costs one more full pass, and it
is admitted only after OBS-E1 shows a direction worth decomposing. Registering it now would be a
second experiment in flight, which the 2026-09-03 iteration rule forbids.

## 6. The decision rule, fixed before the flight

Let `ΔPERSON` = comparator PERSON entity WER − cell PERSON entity WER, and `ΔWER` = comparator corpus
WER − cell corpus WER, both in points, both pooled over the 44 calls under §4's cluster bootstrap,
both **positive when the cell is better**.

* **WIN** — `CI90 LB(ΔPERSON) > 0` **AND** `CI90 LB(ΔWER) > 0`.
* **WIN (entity-only)** — `CI90 LB(ΔPERSON) > 0` **AND** corpus WER **non-inferior**, i.e.
  `CI90 LB(ΔWER) > −0.30` points.
* **NO EFFECT** — neither, and `CI90` on both deltas contains 0.
* **HARM** — `CI90 UB(ΔPERSON) < 0` or `CI90 UB(ΔWER) < −0.30`, with the failing half named and
  the gap decomposed per stratum and per call.

**The −0.30-point non-inferiority margin, justified rather than chosen at read time.** It is six
times the 0.05-point build-and-audio-path noise the sealed verdict measured, so it cannot be tripped
by the noise it is meant to absorb; and it is one tenth of the owner's 3.0-point alignment band
around the published 9.71, so a cell that passes it has spent at most a tenth of the alignment budget
and the Earnings-21 alignment verdict (ALIGNED at 8.200) survives it intact. A cell that lands
outside the margin says so and does not claim non-inferiority.

**Harm guards reported beside the rule, never folded into it**: `numeric-value-accuracy-v1` against
90.7335 %, `semantic-high-impact-error-rate-v1` against 0.02780 % under the same taxonomy id, the
remaining seven ConEC classes, and the non-entity rate. The negation-critical rate is a weak guard by
its own note's admission (100 HIGH reference words on all 44) and is reported as a direction only.

**The falsifier, run before any score is read.** The seam is a media change, so it has a byte-level
oracle: concatenating the unit slices of a call in unit order must reproduce that call's sealed
concatenated audio SHA-256 (`saea-diarization-v1`'s per-call `audio_sha256`) once the 2.0-second
tails are removed, because the units tile and the tails are appended. If any call disagrees, the cut
moved and the cell is stopped before it is scored.

## 7. Budget, and what stops the flight

| | planned | ledger ceiling | basis |
|---|---:|---:|---|
| model calls | **5,800** | 6,000 | 5,288 units, plus 512 of headroom for `obs_slice_retry_max = 1` retries |
| speech audio seconds | **165,000** | 170,000 | 151,921.853 s delivered (141,345.853 cut + 10,576.0 tail), rounded up with retry headroom |
| GPU hours | **3.5** | 4.0 | see below |
| frozen-core contacts | 5,288 | — | one per unit; no second answering model, no retriever, no embedder |
| paid API spend | **0** | 0 | unchanged and still in force |

**The GPU projection is bracketed, not guessed.** The comparator realized **3,504.4 GPU-seconds
(0.973 GPU-h)** for 1,593 contacts over 141,345.85 s of audio at this exact geometry, i.e. 40.3×
realtime and about 17.5 contacts/minute.

* audio-proportional: `0.973 × 151,921.853 / 141,345.853` = **1.05 GPU-h** — the floor, if cost
  tracks encoded seconds;
* contact-proportional: `0.973 × 5,288 / 1,593` = **3.23 GPU-h** — the ceiling, if cost tracks
  requests.

The truth is between: prompt tokens rise about 23 % (1.94 M to roughly 2.38 M, audio tokens tracking
delivered seconds plus a per-request instruction), completion tokens are roughly conserved (the
transcript is the same corpus), and per-request scheduling overhead is what the contact-proportional
bound is measuring. **3.5 planned against a 4.0 ceiling** covers the pessimistic bracket with margin.

**Stop rules, in order.**

1. The smoke's measured rate is projected to the full pass; **the flight stops and reports** if it
   projects past 4.0 GPU-h.
2. One experiment in flight; **at most one recovery re-registration**, and a second failure stops the
   flight with the fix proven on a 4-row dry run (2026-09-03 iteration rule).
3. `planned_model_calls` and `planned_speech_audio_seconds` are enforced **cumulatively across every
   attempt of a run id** (`core/model/adapter.py`), so a partially spent attempt cannot be re-run
   under the same id and the one permitted recovery takes a fresh run id and a fresh exposure row.

## 8. The obs seam — the SPEC the implementer builds to

### 8.0 Sequencing, and why this is a spec rather than a patch

`reproduction/obs_loop.py` is being edited on branch `wt/ts2y`, which adds
`obs_slice_tail_silence_seconds` and factors the three duplicated cut sites onto one encoder,
`reproduction.obs_audio.encode_slice`. **This seam calls that encoder**, so it lands *after* that
merge and is not written here. Nothing in this section is implemented, and the fragments of §9 will
not compose until it is.

### 8.1 Two new keys, both defaulting to today's behaviour

Added to `_KNOWN_OBS_KEYS` and to `ObsLoopConfig`, exactly the shape the tail knob already set:

| key | type | default | meaning |
|---|---|---|---|
| `obs_unit_plan` | string or `null` | `null` | repo-relative path to a `saea-e21-speaker-turn-units-v1` plan |
| `obs_unit_plan_sha256` | string or `null` | `null` | the plan file's SHA-256; the byte pin |

`null` reproduces the fixed-window cutter byte for byte, so **every sealed Earnings run stays
reproducible** and no existing config's `protocol_hash` moves. Setting one key without the other is a
`from_values` error.

### 8.2 What `from_values` must refuse, fail-closed, before a window is cut

1. a plan whose `schema` is not `saea-e21-speaker-turn-units-v1`;
2. a plan whose SHA-256 is not `obs_unit_plan_sha256`;
3. a plan with no block for a `sample_id` the run's roster contains;
4. a plan block whose `decoded_duration_seconds` differs from the runtime decode by more than 1e-6 s
   — the decode is the authority, and a plan cut against different audio is a different measurement;
5. a plan block whose units do not tile `[0, duration)` (re-derived through
   `analysis.e21_speaker_turn_units.assert_tiles`, so the loader re-proves the property rather than
   trusting the file);
6. `obs_boundary_mode != "fixed"`, `obs_condition_tail_chars != 0`, or
   `obs_vad_trim_min_seconds != 0` while a plan is set. The plan fixes every unit position before the
   first contact, which is precisely the independence condition `from_values` already requires for
   `obs_batch_slices > 1`; a rolling tail or a runtime VAD trim would make unit *k+1* depend on unit
   *k* and destroy it.

`obs_batch_slices > 1` therefore stays **legal** under a unit plan, for the same reason and by the
same argument the fixed-window path already records.

### 8.3 What the cutter does

Both cut sites — `ObsAgentLoopPolicy._slice_parallel_pass` and `ObsAgentLoopPolicy.run_sample` —
replace the `while cursor < duration - _EPSILON_SECONDS` fixed-window loop with an iteration over
`plan[sample_id]["units"]` in `unit_index` order. Everything downstream is untouched:

* `start_frame = round(unit.start_seconds * rate)`, `end_frame = round(unit.end_seconds * rate)`,
  clamped to `len(pcm)`;
* the bytes come from `obs_audio.encode_slice(...)` with `tail_silence_seconds` from the **existing**
  `obs_slice_tail_silence_seconds` knob — **no second tail implementation, and none is admitted**;
* `SliceRecord.start_seconds` / `end_seconds` / `audio_seconds` carry the unit's own span, so
  `core.model.SliceRegistry.register`'s `audio_seconds == end - start` assertion is what refuses a
  seam that silently moved a cut;
* `iteration` is `unit_index - 1`, so slice relpaths stay `i%04d.wav` and request ids stay
  `<base>-i%04d`;
* the OBS record's `obs_window_start_seconds` / `obs_window_end_seconds` carry the unit bounds and
  gain `obs_unit_id` (`<sample_id>#u<NNNN>`, minted by
  `analysis.e21_speaker_turn_units.unit_id`), `obs_unit_speaker`, `obs_unit_end_cut`;
* `obs_final_window` is true for the last unit of the call;
* the stitch, the skip bound, the retry seam and the trace shape are unchanged.

### 8.4 The receipt

`saea-obs-derivation-v1` gains `unit_plan_path` and `unit_plan_sha256`, so a sealed run names the
plan it was cut by and a later reader can re-derive the units without guessing. `boundary_mode`
records `"unit-plan"` beside the still-`fixed` advance semantics.

### 8.5 What the seam must NOT do

No new module under `rails/probes/`, no `TaskAdapter` or controller subclass, no new
`core.base` policy: `obs-agent-loop` stays the registered policy name and the plan is a **thin
derivation** on it, exactly as the tail knob is (2026-09-03 engineering-base rules, enforced by
`scripts/checks/engineering_base_check.py`). No `launcher/` directory. The direct baseline stays the
same harness through the same executor.

### 8.6 The seam's own falsifier, before any cell flies

Feed one call's plan through the cutter with the model detached and assert:

1. the emitted `SliceRecord` spans reproduce the plan's `start_seconds` / `end_seconds` /
   `duration_seconds` for all of that call's units;
2. concatenating the emitted slices **with the 2.0-second tails removed** reproduces the call's
   sealed concatenated `audio_sha256` from `saea-diarization-v1` — which holds if and only if the
   units tile and the cut is byte-exact against the sealed slices;
3. `pre_sha256` chains to the untailed cut, and `preprocess` declares `tail-silence-2s`.

Then a **4-row dry run** before the 5,288, per the 2026-09-03 rule.

## 9. Composition, and the interaction with KC-E1

**The fragments are drafted and do not compose yet, and that is stated in the fragments themselves.**
`configs/dataset/earnings21-discovery.json` is reused unchanged (the D1 identity does not move);
`configs/baseline/e21-units-obse1-scored7.json` is the sealed comparator's fragment with **three keys
added and none changed** (`obs_unit_plan`, `obs_unit_plan_sha256`, `obs_slice_tail_silence_seconds`)
plus the four agentic scorers; `configs/experiment/e21-obs-e1-speaker-turn-units-v1.json` carries the
population, the budget and the decision rule. Until §8 lands, `ObsLoopConfig.from_values` rejects
`obs_unit_plan` as an unknown key — **fail-closed, by design**, and the fragment says so.

**KC-E1 is a different cell and stays on fixed windows.** The pre-meeting-brief cell
(`docs/readiness/2026-09-06-e21-kc-e1-pre-meeting-brief-v2-preregistration.md`) is preregistered on
the comparator's 1,593 windows and is unaffected by this document; its window rows and this cell's
unit rows are both clustered at the call, which is the level at which they remain comparable.
**The brief supplied on speaker-turn units is a two-factor cell (OBS × KC) and is explicitly not
this one** — it is admitted only after both single-factor cells have flown, per the 2026-09-03 rule
that a new mechanism is admitted only when its predecessor is replicated or root-caused.

## 10. Claim surface

Discovery data. No superiority, generality or Stage-3 claim; **no paper-facing effectiveness claim at
all**, because n = 44 clusters does not clear the program's `n >= 400` rule (§4). No knob tuned on
the evaluation ten — the plan's five rules were fixed model-free, before any score existed, and every
constant in them is either the study's own sealed value (2.0 s snap radius, 2.0 s tail, 90 s cap) or
stated once here (300 ms pause, 1.0 s minimum). No Earnings-22 contact. No fstalign install. No
diarizer re-run and no speaker naming. `paper-scale-confirmatory` is not available to this repository
and is not requested.
