# The 90-second window now has a speaker stratum, and the tool's 4-speaker bound is the headline caveat

Exposure row `SAEA-E21-TOOL-DIARIZATION-V1` (`bounded-discovery-probe`), registered with
`consumed = no` before the first contact and closed by this receipt. **Zero frozen-core contacts** —
the Qwen3-Omni core was not started, not queried and not involved. No transcript, no word and no text
of any kind was produced; no embedder, tokenizer, second answering model, network or paid API was
touched. The pass executed the preregistration
`docs/readiness/2026-09-06-e21-diarization-obs-v1-preregistration.md` step for step, on Route B (the
`q8_0` GGUF through the pinned `nemo-speech` CUDA build), and nothing in that document was
renegotiated while it ran.

| | |
|---|---|
| attempt | `attempt-20260907T045837Z-5b3f93` |
| population | all 44 `earnings21-original` discovery calls, **1,593** fixed 90-second windows, split identity `fcc1b0bc…d69e` |
| input | the sealed 90-second obs-slices of `SAEA-E21-FULL44-DIRECT-BASELINE-V2`, attempt `attempt-20260904T233816Z-bcd338`, concatenated per call |
| tool | `diar-sortformer-4spk-v2` (NVIDIA streaming Sortformer v2, 117 M params, 16 kHz mono, **max 4 speakers**, CC-BY-4.0) through `nemo-speech` 1.0.0, `--device cuda:0` |
| artifact | `$SPEECHRL_DATA_DIR/runs/SAEA-E21-TOOL-DIARIZATION-V1/attempt-20260907T045837Z-5b3f93/diarization.json`, sha256 `a61c4d559debe3814e024bb1edd9c1b65f063e22aa6a37b1df4a3eea22691ce7`, 2,224,669 B |
| runner | `scripts/e21_diarization_pass.py` (`inputs` → `diarize` → `artifact` → `agreement` → `table`) |
| reader | `src/speech_aware_evidence_acquisition/reproduction/diarization.py`, schema `saea-diarization-v1` |
| realized cost | **45** call-level tool contacts of 50, **142,442.95** audio seconds of 145,000, **0.3825** GPU-h of 2.0, **0** frozen-core contacts, **0** paid API |

The artifact is a large derivative of sealed model-adjacent audio, so it lives under the controlled
data root and never enters Git; its SHA-256 and its whole summary are committed here instead.

## 1. The input is the flight's own audio, proven byte for byte

Every call was rebuilt as one 16 kHz mono WAV by concatenating **its own sealed obs-slices in
iteration order**, and each slice's SHA-256 was re-verified against the sealed
`*.obs-derivation.<sample_id>.json` receipt *before* its frames were appended. **1,593 of 1,593
slices verified**, 44 of 44 calls, 141,345.853 s, 4,523,069,222 B, 77.0 s wall.

No MP3 was decoded, no sample was resampled and `ffmpeg` was not invoked — its absence stays pinned.
`inputs.json` carries, per call, the slice count, a single digest over the ordered slice hashes (so
the input chain is recomputable from the sealed receipts without copying 1,593 hashes into Git), the
concatenation's own SHA-256, and its duration against both the roster's `audio_seconds` and the
sealed `decoded_duration_seconds`.

The concatenation tiles into **exactly the 1,593 windows the sealed roster records**, call for call —
the runner refuses to continue on the first call where `ceil(D / 90)` disagrees. So a diarization
window and an `analysis.e21_window_pairing` window are the same object under the same
`<sample_id>#w<index>` id, not two grids that happen to look alike.

## 2. The stop rule ran first, and did not fire

The preflight is the shortest of the 44, `4386541` (1,097.1 s, 13 windows) — a **construction** call,
so the rate probe never lands on the evaluation ten.

| | preflight | corpus pass |
|---|---:|---:|
| audio | 1,097.1 s | 141,345.853 s |
| wall (incl. model load) | 18.518 s | 1,358.453 s |
| realtime factor | **59.2×** | **104.0×** |
| peak VRAM | 510 MiB | 708 MiB |
| mean GPU utilisation | 60.2 % | 92.1 % |
| peak power | 95.07 W | 104.78 W (100 W enforced limit) |

The preflight's 59.2× projects the full pass at **0.66 GPU-h** against the 2.0 GPU-h ceiling, so the
pass proceeded; the directory pass then beat its own projection at 104.0× because four workers share
one model load and one batching queue. Realized GPU time is **1,376.97 s = 0.3825 GPU-h**, 19 % of
the ceiling. The CPU fallback was never needed.

**Two invocations were refused by the tool's own argument validation before the preflight** (`rc 2`,
`--output-dir is only valid for a directory input`, 0.07 s, **0 MiB GPU**): the runner was passing a
directory-only flag for a single-file contact. Neither loaded the model, read one audio sample or
touched the GPU, so neither consumed audio seconds or GPU hours; they are recorded here as
invocations, not as call contacts, and the fix (`--output` plus `--recording-id` for a file,
`--output-dir` for a directory) was proven on the very next one-call run. That is the one permitted
recovery, and it was spent on the preflight, which is exactly what the preflight is for.

## 3. What the tool found

12,104 speaker segments over 44 calls; 126,462.86 s of attributed speech, **89.5 %** of the corpus
wall clock.

**Per call, the speaker count is min 2 / median 4 / max 4.** Forty-two of the 44 calls saturate the
tool at four speakers; only `4374910` and `4394084` come back with two.

Per window, on the 1,593-window grid:

| count stratum | windows | | dominance stratum | windows |
|---|---:|---|---|---:|
| `speakers=0` | 5 | | `speakers=0` | 5 |
| `speakers=1` | 645 | | `dominated` (≥ 0.60 of attributed time) | 1,351 |
| `speakers=2` | 498 | | `shared` | 237 |
| `speakers>=3` | 445 | | | |

Crossed (`window_strata("both")`): `speakers=1/dominated` 645, `speakers=2/dominated` 414,
`speakers=2/shared` 84, `speakers>=3/dominated` 292, `speakers>=3/shared` 153, `speakers=0` 5.

**Overlap is real but small**: 491 of 1,593 windows carry any simultaneous attribution at all, mean
overlap share 0.33 %, median 0, p90 1.12 %, max 7.88 %. An earnings call is mostly one voice at a
time, which is why the dominance stratum is the useful one.

Per-call rows: `per-call-speakers.md`; every number in it is rendered from `summary.json`, never
retyped.

## 4. The 4-speaker bound, reported rather than absorbed

The lock's own `claim_limit` records a **4-speaker design bound**. On this carrier it is exceeded,
and not marginally:

* **38 of the 44 calls name more than four participants on their own ConEC roster** — roster sizes
  run from 2 to 19, median 9 — and those calls hold **1,476 of the 1,593 windows (92.7 %)**. Only six
  calls are inside the tool's design population.
* So `speaker_count` is a **saturating** statistic: 42 of 44 calls hit exactly four, which is the
  ceiling, not a measurement. A window the tool calls `speakers>=3` may hold five or ten.
* The **dominance stratum is therefore the primary one** and the count stratum is reported beside it,
  exactly as the preregistration required. A `dominated` window is a claim about one voice holding
  the floor, which survives a mis-merged tail; a `speakers>=3` label is a floor, not a count.
* The roster read is a **count of non-empty lines** in each call's ConEC `participant_names` file — a
  `runtime-legal-input` layer already hashed by the committed brief-provenance receipt. **No name was
  recorded here, no speaker id was mapped to a name, and no accuracy was measured.**

**No diarization error rate is claimed anywhere in this receipt.** ConEC ships no speaker-turn gold
this repository may read at runtime, and AMI/ICSI appear in NVIDIA's own training-data list, so a DER
on those corpora would be an in-domain number. The mapping of anonymous ids to roster names, and its
accuracy, remain a separate audit under their own exposure row.

## 5. The two serving geometries agree where it matters

The preflight runs one file (one worker, dynamic batching **off**); the corpus pass runs a directory
(four workers, batching **on**). Those are not bit-identical: a batched GPU reduction moves a
frame-level activation across the onset/offset threshold, the same class of effect this program
already records for greedy `llama-server` decoding. On `4386541` the two runs differ — **123 vs 120
segments, 991.324 vs 993.840 s of attributed speech**, boundaries shifted by one or two 80 ms frames.

The question the preregistration actually asks is whether Route B disagrees with *itself*, and the
decisive test is whether the difference reaches the field a verdict reads. It does not:

> **0 count-stratum disagreements, 0 dominance-stratum disagreements and 0 dominant-speaker
> disagreements across all 13 windows**, with the same four speaker ids on both sides.

Route B stands; the Route A fallback is not triggered. `geometry-agreement.json` carries the full
comparison. The artifact is built from the **corpus pass** RTTMs only — the preflight output is a
rate probe and a consistency witness, never a source of sealed rows.

## 6. The artifact checks itself, and was checked

`build_call_block` derived every per-window field, and `load_diarization` then re-derived all of them
from each call's own segment list and compared: **PASS on 44 of 44 calls and 1,593 of 1,593
windows** — dominant speaker, dominant share, speaker count, overlap share, window ids, window
bounds and the `ceil(D / 90)` tiling. A hand-edited stratum, a truncated segment list or a shifted
boundary would be a load-time error, not a silently wrong verdict row. Twenty-four unit tests
(`tests/unit/test_diarization_artifact.py`) pin that behaviour independently.

## 7. Claim surface

Discovery data; an **observation**, not a result. The artifact never enters a prompt and carries no
answer authority — the frozen core keeps it. No superiority, generality, diarization-accuracy or
Stage-3 claim; no knob was tuned on the evaluation ten; no Earnings-22 contact; no confirmatory read;
no frozen-core contact. Speaker strata are a **reporting dimension**, never a knob, so adding them to
a cell's tables after the fact changes no arm and no decision rule (preregistration §9).

## 8. Files

| file | what it holds |
|---|---|
| `inputs.json` | the per-call concatenation receipt: slice counts, ordered-slice-hash digests, concatenation SHA-256s, durations against the sealed roster |
| `contact-preflight.json` | the stop-rule contact: argv, verified tool identity, wall clock, sampled GPU peak |
| `contact-full-pass.json` | the 44-call contact, same shape |
| `geometry-agreement.json` | the two-geometry comparison on `4386541`, window by window |
| `summary.json` | the sealed artifact's identity and hash, the strata distributions, the overlap table, the 4-speaker caveat and the per-call rows |
| `per-call-speakers.md` | the per-call table, rendered from `summary.json` |
| `MANIFEST.sha256` | this directory's own byte manifest |
