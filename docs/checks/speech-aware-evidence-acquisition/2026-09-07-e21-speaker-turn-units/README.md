# The OBS-E1 transport unit: 44 calls, 5,288 speaker-turn units, and the cut that lands in a pause

Exposure row `SAEA-E21-MF-SPEAKER-TURN-UNITS-V1` (`model-free-check`), registered and committed
before the first slice was read. **Zero frozen-core, diarizer, GPU, embedder, tokenizer, network and
paid-API contacts.** No MP3 was decoded and nothing was resampled, so `ffmpeg` stayed absent; the only
audio touch is a local PCM read of the already-sealed 90-second obs-slices, whose samples become
20 ms frame energies and are then discarded. **No reference text was opened** — per-unit
reference-word counts are interpolated from the per-window reference-word COUNTS of the sealed
window-pairing rows, never from a transcript, a `wer_tags` sidecar or a timestamp file.

| | |
|---|---|
| owner thesis | cut the speech by SPEAKER first, then understand per speaker |
| sources | `SAEA-E21-TOOL-DIARIZATION-V1` (`attempt-20260907T045837Z-5b3f93`, anonymous segments) and the sealed slices of `SAEA-E21-FULL44-DIRECT-BASELINE-V2` (`attempt-20260904T233816Z-bcd338`) |
| reference-word source | `SAEA-E21-MF-WINDOW-PAIRING-V1` per-window rows, sha256 `e2e7da6f…7f800` |
| population | all 44 `earnings21-original` discovery calls, split identity `fcc1b0bc…d69e`, 141,345.853 s |
| module / runner | `analysis/e21_speaker_turn_units.py` · `scripts/e21_speaker_turn_units_build.py` (136 lines) |
| tests | `tests/unit/test_e21_speaker_turn_units.py`, 41 on synthetic diarization and synthetic PCM |
| plan | `docs/receipts/obs/e21-speaker-turn-units-v1.json`, sha256 in `unit-plan-summary.json` |
| wall clock | 67.7 s, single process, CPU only, `CUDA_VISIBLE_DEVICES` empty |

---

## 1. The five rules, and where each of them bit

A unit **never crosses a diarized speaker change**; **never ends inside active speech** where a pause
of at least 300 ms sits within 2.0 s of the turn change; is **capped at 90 s** (a long monologue
splits at its longest internal pause, recursively); has a **1.0-second minimum** (merged into a
same-speaker neighbour across a non-speaker-change boundary when the result still fits the cap, else
kept and flagged); and carries a **2.0-second digital silence tail on the delivered media only** —
the admitted Earnings-22 convention, which moves no cut and no span.

| rule | how often it fired |
|---|---:|
| 1. speaker change opens a unit | 5,288 units over 5,244 interior boundaries; every unit's dominant speaker holds it |
| 2. boundary snapped onto a pause | **4,471 of 5,244 interior cuts (85.3 %)**; 758 (14.5 %) stayed where the turn change put them |
| 3. cap split at the longest internal pause | 15 forced splits on **2 calls**, 23 units carry `forced-cap-split` |
| 4. minimum | 8 merges; **166 units (3.1 %) kept under 1.0 s and flagged `short-kept`** |
| 5. tail | 5,288 × 2.0 s = 10,576.0 s of delivered silence, and 0 s of moved cut |

The activity gate is `analysis.e22_clip_boundary.frame_rms_dbfs` at its committed settings — 20 ms
frames, active = RMS within 30 dB of the window's own peak and above −55 dBFS — thresholded **per
90-second window**, which is exactly the gate the 65.5 % window-end figure was measured with. 38,166
pauses of at least 300 ms were found over the 44 calls.

## 2. The headline: the cut now lands in silence

| | fixed 90-s windows (sealed) | speaker-turn units |
|---|---:|---:|
| units per corpus | 1,593 | **5,288** (3.32×) |
| mean unit seconds | 88.73 | **26.73** |
| median unit seconds | 90.00 | **16.06** |
| **ends on an ACTIVE frame** | **1,043 (65.5 %)** | **617 (11.7 %)** |
| interior cuts ending within 20 ms of speech | 1,088 of 1,549 (70.2 %) | — |
| single-speaker units | 645 (40.5 %) | **4,024 (76.1 %)** |
| two speakers | 498 (31.3 %) | 1,128 (21.3 %) |
| three or more | 445 (27.9 %) | 35 (0.7 %) |
| no attributed speech | 5 (0.3 %) | 101 (1.9 %) |
| `dominated` at the 0.60 threshold | 1,351 (84.8 %) | **5,034 (95.2 %)** |
| `shared` | 237 (14.9 %) | 153 (2.9 %) |

**The two things the unit was supposed to buy, it buys.** Mid-speech cuts fall from 65.5 % to
11.7 % of units, and the share of units carrying exactly one speaker rises from 40.5 % to 76.1 %.
Mean dominant-speaker share is **0.9431** and the median is **1.0000**; 4,156 units (78.6 %) are at
or above 0.99.

**Nothing here says the core transcribes them better.** This is a property of the cut, measured
model-free. Whether it moves PERSON entity WER or corpus WER is the OBS-E1 cell's question, and that
cell has not flown.

## 3. Duration distribution

| min | p05 | p25 | median | p75 | p90 | p99 | max | mean |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.001 s | 1.320 s | 4.474 s | **16.060 s** | 44.753 s | 70.243 s | 88.019 s | 90.000 s | 26.730 s |

Cumulative: 11 units under 0.05 s, 17 under 0.1 s, 32 under 0.3 s, **166 under 1.0 s**, 520 under
2 s, 1,446 under 5 s, 2,176 under 10 s, 3,369 under 30 s, 4,457 under 60 s, 5,273 under 90 s.
Per call: 34 to 238 units (median 121) against 13 to 64 windows, a unit-to-window ratio of 1.81 to
4.79 (median 3.26).

**The 166 short units are a real cost, not a rounding artefact.** They are backchannels between two
other speakers, so rule 1 forbids merging them anywhere: their median length is 0.649 s and the
shortest is **1 ms**. Each is still a model contact under this plan. The OBS-E1 preregistration
counts them in the budget rather than quietly dropping them, and reports them as their own stratum.

## 4. Audio: the cut is conserved, the delivery is not

| | seconds |
|---|---:|
| sealed decoded call audio | 141,345.853 |
| **total unit CUT audio** | **141,345.853** |
| total window cut audio | 141,345.853 |
| total unit DELIVERED audio (with the 2.0 s tail) | **151,921.853** |
| total window delivered audio | 141,345.853 |
| **delivered delta** | **+10,576.000 (+7.48 %)** |

**The brief's expectation that the buffered windows overlap does not hold on this arm, and the plan
reports the measurement rather than the assumption.** The sealed full-44 baseline runs
`obs_boundary_mode: fixed` with advance = buffer, so its 1,593 windows tile each call exactly once
with no overlap; window delivered audio equals call audio to the digit. The whole delivered-audio
delta of this plan is therefore the tail, `5,288 × 2.0 s`, and nothing else. A tail-bearing window
arm would carry `1,593 × 2.0 = 3,186 s` of the same kind, so against **that** comparator the delta
is +7,390.0 s.

## 5. Reference words, attributed without opening a transcript

The sealed window rows give each 90-second window the number of whole-string-normalized reference
words the scorer's own alignment charged to it. Cumulating those counts is a monotone map from
window boundary TIME to reference-word INDEX; the plan interpolates it linearly inside a window and
rounds, so consecutive units get consecutive half-open index ranges.

* **359,765 reference words attributed, against the sealed 359,765 — exact.**
* Median 40 reference words per unit, mean 68.0, max 313.
* **21 units (0.4 %) are attributed no reference word at all**; their median length is 0.045 s, i.e.
  they are the sub-100-millisecond backchannels of §3.

**It is an attribution, never a timestamped alignment.** It is exact at every window boundary and an
interpolation inside one, and a unit that coincides with window boundaries receives exactly that
window's words. ConEC ships timestamps this repository may not read at runtime, and no gold timing
was used to build this map.

## 6. Three limitations, named

1. **One call has no detectable pause at all.** `4366522` (1,817.7 s, 21 windows) returns **zero**
   pauses of ≥ 300 ms under the peak-relative gate: its noise floor never drops 30 dB below its own
   peak. Every one of its 38 units therefore ends at a turn boundary or a forced cap split, all 38
   end on an active frame, and 13 of the 15 corpus-wide forced splits are its. On that call the plan
   delivers the speaker axis and none of the boundary axis, and the OBS-E1 verdict must report it
   apart rather than pooling it away. The other 43 calls carry 252 to 1,926 pauses each.
2. **The diarizer's 4-speaker bound travels with the unit.** The diarization row already recorded it:
   38 of the 44 calls name more than four participants on their own ConEC roster, and 42 of 44
   saturate the tool at four speakers. A "unit that never crosses a speaker change" is therefore a
   unit that never crosses a change the tool could SEE. The dominance stratum stays the primary one
   for the same reason it was primary there.
3. **The energy gate is not a VAD**, and is named as such everywhere. It is the same crude
   peak-relative gate the Earnings-22 clip-boundary audit used, chosen so this measurement and the
   65.5 % it is compared against are the same function — not because it is the best pause detector
   available.

## 7. Claim surface

Discovery data. This row produces a transport UNIT and its tiling proof, not a result: no
superiority, generality, transcription-quality or Stage-3 claim, no knob tuned on the evaluation ten,
no Earnings-22 contact, no frozen-core contact. It licenses no flight — cell OBS-E1 needs the obs
seam implemented, its own exposure row and the owner's GO
(`docs/readiness/2026-09-07-e21-obs-speaker-turn-units-v1-preregistration.md`).

## 8. Per-call table

Columns: units, sealed windows, their ratio, the unit duration median / p90 / max, how many units end
on a pause / at a turn boundary / on a forced cap split, how many end on an active frame, how many
carry exactly one speaker, the mean dominant-speaker share, and the attributed reference words.

| call | units | windows | u/w | median s | p90 s | max s | pause cuts | turn-boundary | forced | ends active | 1-speaker | purity mean | ref words |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 4320211 | 131 | 37 | 3.54 | 15.0 | 67.8 | 89.3 | 122 | 8 | 0 | 5 | 109 | 0.929 | 8673 |
| 4330115 | 73 | 28 | 2.61 | 29.9 | 72.1 | 89.6 | 67 | 5 | 0 | 5 | 65 | 0.979 | 6628 |
| 4341191 | 238 | 64 | 3.72 | 9.3 | 66.6 | 88.0 | 206 | 31 | 0 | 23 | 162 | 0.891 | 14541 |
| 4344338 | 91 | 31 | 2.94 | 23.7 | 72.1 | 83.8 | 80 | 10 | 0 | 7 | 77 | 0.985 | 6946 |
| 4344866 | 155 | 37 | 4.19 | 10.5 | 59.9 | 90.0 | 114 | 38 | 2 | 35 | 110 | 0.931 | 9130 |
| 4346818 | 121 | 45 | 2.69 | 25.8 | 77.2 | 89.9 | 113 | 7 | 0 | 6 | 113 | 0.985 | 10968 |
| 4346923 | 206 | 53 | 3.89 | 12.4 | 64.7 | 87.8 | 181 | 24 | 0 | 14 | 146 | 0.920 | 10147 |
| 4359732 | 191 | 55 | 3.47 | 13.2 | 69.4 | 86.8 | 161 | 29 | 0 | 24 | 136 | 0.934 | 11573 |
| 4359971 | 156 | 42 | 3.71 | 10.3 | 61.8 | 88.4 | 139 | 16 | 0 | 13 | 113 | 0.936 | 9554 |
| 4360366 | 154 | 44 | 3.50 | 17.1 | 64.3 | 89.6 | 130 | 23 | 0 | 13 | 126 | 0.974 | 10491 |
| 4360674 | 96 | 40 | 2.40 | 34.6 | 81.6 | 89.9 | 86 | 9 | 0 | 8 | 82 | 0.976 | 9543 |
| 4360717 | 165 | 51 | 3.24 | 18.2 | 69.8 | 89.9 | 140 | 24 | 0 | 21 | 121 | 0.937 | 11912 |
| 4361631 | 119 | 50 | 2.38 | 34.4 | 75.9 | 88.2 | 110 | 8 | 0 | 6 | 99 | 0.916 | 8917 |
| 4363614 | 181 | 63 | 2.87 | 22.6 | 70.9 | 89.5 | 170 | 10 | 0 | 8 | 155 | 0.957 | 13330 |
| 4364366 | 102 | 39 | 2.62 | 27.6 | 66.3 | 85.3 | 98 | 3 | 0 | 3 | 96 | 0.994 | 8261 |
| 4365024 | 130 | 49 | 2.65 | 27.2 | 76.6 | 88.6 | 124 | 5 | 0 | 3 | 108 | 0.964 | 11625 |
| 4365948 | 92 | 28 | 3.29 | 20.5 | 71.1 | 86.8 | 72 | 19 | 0 | 16 | 65 | 0.959 | 6704 |
| 4366302 | 157 | 40 | 3.92 | 12.3 | 62.6 | 89.1 | 139 | 17 | 0 | 12 | 116 | 0.939 | 10013 |
| 4366429 | 123 | 45 | 2.73 | 24.6 | 77.7 | 89.0 | 117 | 5 | 0 | 2 | 114 | 0.992 | 11305 |
| 4366522 | 38 | 21 | 1.81 | 38.9 | 90.0 | 90.0 | 0 | 24 | 13 | 38 | 34 | 0.989 | 4123 |
| 4366893 | 99 | 27 | 3.67 | 13.8 | 69.4 | 85.3 | 77 | 21 | 0 | 16 | 61 | 0.952 | 6390 |
| 4367318 | 62 | 20 | 3.10 | 17.0 | 70.0 | 88.3 | 52 | 9 | 0 | 6 | 44 | 0.955 | 4316 |
| 4367535 | 115 | 36 | 3.19 | 18.0 | 72.7 | 89.4 | 101 | 13 | 0 | 10 | 86 | 0.947 | 6914 |
| 4368670 | 144 | 47 | 3.06 | 19.2 | 72.7 | 90.0 | 133 | 10 | 0 | 10 | 123 | 0.971 | 11203 |
| 4374910 | 65 | 23 | 2.83 | 24.4 | 79.2 | 89.7 | 57 | 7 | 0 | 6 | 56 | 0.977 | 4921 |
| 4375653 | 121 | 39 | 3.10 | 18.3 | 68.0 | 89.6 | 92 | 28 | 0 | 22 | 96 | 0.970 | 9479 |
| 4382825 | 144 | 43 | 3.35 | 15.3 | 67.4 | 89.0 | 115 | 28 | 0 | 22 | 105 | 0.922 | 10709 |
| 4383161 | 115 | 38 | 3.03 | 21.5 | 70.1 | 85.8 | 104 | 10 | 0 | 7 | 93 | 0.949 | 8915 |
| 4384198 | 124 | 30 | 4.13 | 8.2 | 65.0 | 86.0 | 98 | 25 | 0 | 18 | 74 | 0.911 | 6568 |
| 4384683 | 62 | 17 | 3.65 | 12.3 | 60.2 | 84.3 | 47 | 14 | 0 | 12 | 44 | 0.908 | 3614 |
| 4384744 | 136 | 37 | 3.68 | 11.2 | 67.4 | 89.9 | 108 | 27 | 0 | 22 | 88 | 0.929 | 8155 |
| 4384964 | 177 | 45 | 3.93 | 8.4 | 68.0 | 89.5 | 138 | 38 | 0 | 32 | 136 | 0.947 | 9879 |
| 4385072 | 139 | 29 | 4.79 | 6.5 | 65.1 | 87.8 | 111 | 27 | 0 | 25 | 88 | 0.889 | 6480 |
| 4385388 | 149 | 49 | 3.04 | 23.0 | 73.5 | 86.2 | 123 | 25 | 0 | 23 | 112 | 0.956 | 11360 |
| 4385939 | 157 | 34 | 4.62 | 9.4 | 51.3 | 87.1 | 130 | 26 | 0 | 18 | 114 | 0.951 | 9111 |
| 4386541 | 34 | 13 | 2.62 | 28.0 | 67.9 | 86.8 | 31 | 2 | 0 | 1 | 27 | 0.956 | 2722 |
| 4387332 | 51 | 15 | 3.40 | 14.9 | 68.0 | 84.3 | 43 | 7 | 0 | 6 | 39 | 0.940 | 4030 |
| 4387383 | 110 | 24 | 4.58 | 14.0 | 40.2 | 89.3 | 72 | 37 | 0 | 32 | 79 | 0.924 | 3672 |
| 4387865 | 86 | 25 | 3.44 | 13.1 | 65.7 | 85.8 | 66 | 19 | 0 | 14 | 61 | 0.895 | 5921 |
| 4389907 | 68 | 23 | 2.96 | 20.4 | 76.3 | 88.1 | 63 | 4 | 0 | 4 | 56 | 0.946 | 3942 |
| 4392809 | 49 | 16 | 3.06 | 24.3 | 75.1 | 86.3 | 43 | 5 | 0 | 4 | 41 | 0.975 | 4079 |
| 4394084 | 52 | 20 | 2.60 | 23.9 | 72.0 | 82.4 | 47 | 4 | 0 | 3 | 43 | 0.972 | 3636 |
| 4397800 | 116 | 31 | 3.74 | 9.9 | 68.1 | 87.6 | 87 | 28 | 0 | 21 | 75 | 0.918 | 7972 |
| 4397829 | 194 | 50 | 3.88 | 13.8 | 60.3 | 89.3 | 164 | 29 | 0 | 21 | 136 | 0.931 | 11393 |
