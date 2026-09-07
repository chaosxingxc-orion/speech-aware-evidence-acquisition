# SAEA-E21-TOOL-DIARIZATION-V1 — speaker diarization as a frozen tool-level OBSERVATION

**Status: EXECUTED 2026-09-07** — receipt
`docs/checks/speech-aware-evidence-acquisition/2026-09-06-e21-diarization-obs/`, section 11 below.
Sections 1–10 are the pre-registration as it stood before any diarization output existed and are
left unedited; they state what the pass would produce, what it would cost, and what it is and is not
allowed to say. The reader (`reproduction/diarization.py`, schema `saea-diarization-v1`) and the
feasibility receipt
(`docs/checks/speech-aware-evidence-acquisition/2026-09-06-e21-diarization-feasibility/`) were
committed first; the pass was a separate act.

Exposure row `SAEA-E21-TOOL-DIARIZATION-V1`, `bounded-discovery-probe`, registered with
`consumed = no` before the first contact. **Zero frozen-core contacts.** The frozen Qwen3-Omni core
is not started, not queried, and not involved.

---

## 1. What diarization is for here, and what it is not

Two jobs, both at the OBS layer:

1. **Per-window speaker strata.** The owner's 2026-09-06 ruling makes the 90-second window the
   Earnings pairing unit (`analysis/e21_window_pairing.py`,
   `docs/checks/…/2026-09-06-e21-window-pairing/`). A window's *speaker count* and *dominant-speaker
   class* are the natural strata at that unit, and they do not exist at any coarser one. Every
   Earnings verdict from KC-E1 onward carries a per-stratum table; this pass is what fills it.
2. **Tying the pre-meeting brief's roster to speaker turns.** ConEC's participant roster names who
   is on the call; diarization says when each of them holds the floor. Whether that pairing helps is
   a later question — this row only produces the observation.

**What it is not.** It never enters a prompt, never changes a hypothesis, and carries no answer
authority: the frozen core keeps that, exactly as the study charter's frozen-tool clause requires.
It is not an ASR tool and produces no transcript, no words and no text of any kind — only
`(start, end, anonymous speaker id)`. The owner's 2026-09-06 "no transcript tokens" ruling is
untouched.

## 2. The tool, and the route that exists

Umbrella lock entry **`diar-sortformer-4spk-v2`** (`meeting-minutes-tools` profile, lifecycle
AUXILIARY, CC-BY-4.0, ungated, `research_role`: *frozen tool-level speaker diarization … TOOL_DIAR
tier*). NVIDIA streaming Sortformer v2, 117 M parameters, 16 kHz mono, **max 4 speakers**. Identity
is resolved through `data.lock` at run time; no hash or revision is copied into this repository.

The feasibility probe re-hashed both payloads against the lock and found **both routes live**:

| route | what it is | live |
|---|---|---|
| **A** — NeMo reference | the fp32 `.nemo` checkpoint under the ISOLATED `~/.venvs/diar` (torch 2.9.1+cu128, `nemo_toolkit` 3.0.0) | yes |
| **B** — NeMo-Speech.cpp | the first-party `q8_0` GGUF through the CUDA build of `nemo-speech`, binary SHA-256 matching the lock's pin, at pinned commit `4c749a70…` | yes |

`nemo` is **absent from the shared `~/.venvs/speechrl`**, which is correct and stays that way: nothing
in this study installs it there, or anywhere.

**Route B is selected.** It is the deployment path the lock itself designates, its binary identity is
pinned and verified, it emits RTTM directly, it batches a whole directory in one process with one
model load, and it needs no Python environment switch mid-campaign. Route A stays as the named
fallback if Route B's output disagrees with itself on a preflight call.

`nemo-speech doctor --json` with `CUDA_VISIBLE_DEVICES` empty reports
`accelerator_available: false` and falls back to CPU — which is exactly the evidence that the
feasibility probe touched no GPU. The pass itself runs `--device cuda:0`.

## 3. The input: the flight's own audio, not a new decode

Each call is diarized as ONE whole-call 16 kHz mono WAV built by **concatenating the sealed
90-second slices the full-44 flight itself observed**
(`$SPEECHRL_DATA_DIR/derived/obs-slices/SAEA-E21-FULL44-DIRECT-BASELINE-V2/<sample_id>/i####.wav`,
16 kHz mono 16-bit, tiling the call with a short tail — verified: 37 slices totalling 3,285.816 s for
call `4320211`).

Three reasons, and they matter:

* **No new decode, and no ffmpeg.** ffmpeg's absence is pinned for this program; every buf90 slice
  was cut through the librosa fallback, and re-decoding the MP3 would change bytes.
* **The diarizer hears exactly what the core heard.** A speaker stratum computed on different audio
  than the window it labels is a different measurement.
* **Byte-provable.** Every slice's SHA-256 is already in the sealed
  `*.obs-derivation.<sample_id>.json` receipt, so the concatenation's inputs are pinned and the
  concatenation itself is deterministic.

The concatenated WAVs are written under `$SPEECHRL_DATA_DIR/derived/meeting-minutes/e21-diar-input/`
and never enter Git. Their per-call SHA-256 goes in the artifact's `audio_sha256`.

## 4. The output: `saea-diarization-v1`

One artifact for all 44 calls, written to
`$SPEECHRL_DATA_DIR/runs/SAEA-E21-TOOL-DIARIZATION-V1/<attempt_id>/diarization.json`, with its
SHA-256 and summary committed as a receipt. Schema and reader:
`src/speech_aware_evidence_acquisition/reproduction/diarization.py`.

Per call: `sample_id`, `audio_seconds`, `audio_sha256`, and the RTTM segment list as
`{start_seconds, end_seconds, speaker}` in start order — anonymous ids only.

Per 90-second window, on the SAME fixed `ceil(D / 90)` grid the OBS loop cuts and under the SAME
window ids `analysis.e21_window_pairing.window_id` mints (`<sample_id>#w<index>`), so a diarization
window and a paired-analysis window are the same object:

| field | meaning |
|---|---|
| `speaker_seconds` | each speaker's attributed time inside the window |
| `dominant_speaker` / `dominant_share` | the top speaker and its share of the window's *attributed* time (silence is not a competitor) |
| `speaker_count` | how many distinct speakers the window carries |
| `overlap_share` | the fraction of the window's wall clock with two or more speakers simultaneously attributed — the crosstalk estimate, and the reason a 4-speaker bound matters on an earnings call |

**The artifact is self-checking.** Every per-window field is a derivation of the call's own segment
list, and `load_diarization` re-derives all of them and refuses any disagreement: a hand-edited
stratum, a truncated segment list, a shifted boundary or a grid that does not tile the call is a
load-time error, never a silently wrong row in a verdict table. Twenty-four unit tests
(`tests/unit/test_diarization_artifact.py`) pin that on a synthetic artifact.

**Strata.** `DiarizationArtifact.window_strata(grain)` returns `window_id -> label` ready for
`analysis.paired`'s `strata_of`: `speakers=0/1/2/>=3` (count), `dominated`/`shared` at a stated
0.60 threshold (dominance), or both.

## 5. Speaker ids are anonymous, and naming them is a separate, gated act

The diarizer emits `speaker_0 … speaker_3`. The ids carry no identity and are not comparable across
calls. **Everything KC-E1 needs — count, dominance class, overlap share — works on anonymous ids
alone**, so the naming question does not block anything.

When a mapping is wanted, the rule is hard:

* a mapping may be built **only** from the call's own pre-meeting brief (ConEC context, classified
  `runtime-legal-input`) or from the frozen core's own outputs;
* it may **never** be built from a reference transcript, a `wer_tags` sidecar, a timestamp file, or
  any other gold artifact. In particular a "first turn is the operator, second is the CEO" heuristic
  is allowed only if it reads the brief; it is forbidden if it reads the reference;
* `reproduction.diarization.speaker_roster_mapping` therefore takes candidate names the caller
  supplies and checks them; it has no reference-reading path and cannot acquire one. An id with no
  candidate stays anonymous rather than being guessed;
* **the mapping's accuracy against ConEC's roster is an AUDIT read under its own exposure row**, is
  reported as a diagnostic only, and never enters a runtime decision or a cell's decision rule.

## 6. The 4-speaker bound is a real limitation, stated up front

The lock's own `claim_limit` records it: *"4-speaker design bound … ICSI (3-10 speakers) is outside
this tool's bound"*. **Earnings calls routinely carry more than four speakers** — ConEC's rosters list
operator, several executives and a queue of sell-side analysts. So on this carrier the diarizer is
being used **outside** the population it was designed for, and the pass must report that rather than
absorb it:

* the number of calls whose roster names more than four participants, and the number of windows in
  them, is reported beside the strata;
* `speakers>=3` is a saturating stratum: a window the tool calls 3-or-4-speaker may hold more;
* the `dominant_speaker` of a window is more trustworthy than its `speaker_count`, and a stratum
  built on dominance is therefore the primary one, with the count stratum reported beside it;
* **no diarization error rate is claimed.** ConEC ships no speaker-turn gold this repository is
  allowed to read at runtime, and AMI/ICSI appear in NVIDIA's own training-data list, so a DER
  measured with this tool on those corpora would be an in-domain number. This row measures no DER
  and makes no accuracy claim of any kind about the diarizer.

## 7. Budget and stop rules

| | value | basis |
|---|---:|---|
| tool contacts (`calls` column) | **50** | 44 calls, plus one preflight call re-run and retry headroom |
| speech audio seconds | **145,000** | 141,348.532 s over the 44 calls, plus the preflight call twice |
| GPU hours | **2.0** | Sortformer is 117 M parameters against the core's 30 B; the acquisition receipt's only timing is an 11-second bundled sample in 19.48 s wall INCLUDING model load, which is not a rate. The number is a CEILING, not a prediction |
| frozen-core contacts | **0** | the core is not started |
| paid API spend | **0** | unchanged and still in force |

**The rate is measured, not assumed.** The flight runs ONE call first — `4386541`, the shortest of
the 44 at 1,097.1 s / 13 windows by the roster receipt, and a CONSTRUCTION call, so the preflight
never lands on the evaluation ten — records wall clock and realtime factor, and projects the full
pass. If the
projection exceeds 2.0 GPU-h the pass **stops and reports** rather than continuing; the fallback is
`--device cpu` overnight, which costs no GPU at all and is explicitly acceptable because nothing is
waiting on this artifact except a stratum column.

One experiment in flight; at most one recovery re-registration; a second failure stops the pass and
the fix is proven on a 1-call dry run.

## 8. The flight agent's checklist, in order

1. **Register and commit** the exposure row before the first contact (already written, `consumed = no`).
2. **Build the inputs.** Concatenate the sealed slices per call; verify each slice's SHA-256 against
   the sealed `*.obs-derivation.<sample_id>.json`; record each concatenation's own SHA-256 and its
   duration against the roster receipt's `audio_seconds`.
3. **Preflight one call** on `--device cuda:0`; record wall clock, realtime factor and peak VRAM;
   project the full pass; stop if it exceeds the ceiling.
4. **Run the 44** in one process (`diarize <dir> --recursive --format rttm --output-dir …`), one model
   load, one device.
5. **Build the artifact** through `reproduction.diarization.build_call_block`, so the per-window
   derivation is written by the same code the reader re-derives with; then **load it back** with
   `load_diarization` and refuse to seal it if it does not validate.
6. **Report** the strata distribution over the 1,593 windows, the >4-participant caveat of §6, and
   the pass's realized cost. Land the receipt under
   `docs/checks/speech-aware-evidence-acquisition/2026-09-06-e21-diarization-obs/`.
7. **Do not** name a speaker, compute a DER, or let any output reach a prompt.

## 9. Relationship to KC-E1

KC-E1 does **not** block on this pass. The cell flies with the strata it has; if this artifact exists
by then, the speaker strata are added at read time from it, and if it does not, they are added later
from the sealed artifact over the same sealed window rows — the window ids are stable and the rows
are already computed. That is stated in
`docs/readiness/2026-09-06-e21-kc-e1-pre-meeting-brief-v2-preregistration.md` §3 and is not a
loophole: the strata are a REPORTING dimension, never a knob, and adding them after the fact changes
no cell, no arm and no decision rule.

## 10. Claim surface

Discovery data. This row produces an observation, not a result. No superiority, generality,
diarization-accuracy or Stage-3 claim; no knob tuned on the evaluation ten; no Earnings-22 contact; no
confirmatory read; no frozen-core contact. `paper-scale-confirmatory` is not available to this
repository and is not requested.

## 11. What the pass actually did (2026-09-07)

Executed on Route B exactly as §2 selected, attempt `attempt-20260907T045837Z-5b3f93`; full receipt
and per-call table at
`docs/checks/speech-aware-evidence-acquisition/2026-09-06-e21-diarization-obs/`, runner
`scripts/e21_diarization_pass.py`.

| §8 checklist step | outcome |
|---|---|
| 1. register before the first contact | row was already `consumed = no`; closed COMPLETED after the pass |
| 2. build the inputs | **1,593 of 1,593** slice SHA-256s re-verified against the sealed `obs-derivation` receipts, 141,345.853 s concatenated, tiling into exactly the sealed roster's 1,593 windows; no MP3 decode, no resample, `ffmpeg` untouched |
| 3. preflight and project | `4386541`, 18.518 s wall, **59.2× realtime**, 510 MiB peak VRAM, projecting **0.66 GPU-h** against the 2.0 ceiling — the stop rule did **not** fire |
| 4. run the 44 in one process | one model load, four workers, `--device cuda:0`, 1,358.453 s wall, **104.0× realtime**, 708 MiB peak VRAM |
| 5. build through `build_call_block`, load back | reader validation **PASS** on 44 of 44 calls and 1,593 of 1,593 windows |
| 6. report strata, the §6 caveat and the cost | below |
| 7. name no speaker, compute no DER, reach no prompt | held — the artifact carries anonymous ids only and no accuracy number of any kind |

**Cost.** 45 call-level tool contacts of 50; 142,442.95 audio seconds of 145,000; **0.3825 GPU-h** of
2.0; **0** frozen-core contacts; 0 paid API. Two invocations before the preflight were refused by the
tool's own argument validation (`rc 2`, a directory-only flag on a single-file contact, 0.07 s, 0 MiB
GPU); they loaded no model and read no audio, and the fix was proven on the next one-call run — the
one permitted recovery, spent on the preflight.

**Strata.** Per call the speaker count is min 2 / median 4 / max 4. Over the 1,593 windows:
`speakers=0` 5, `speakers=1` 645, `speakers=2` 498, `speakers>=3` 445; `dominated` 1,351 and `shared`
237 at the 0.60 threshold. 491 windows carry any overlap (mean share 0.33 %, p90 1.12 %, max 7.88 %).

**The §6 caveat is the headline, not a footnote.** 38 of the 44 calls name more than four
participants on their own ConEC roster (sizes 2–19, median 9), and those calls hold 1,476 of the
1,593 windows — 92.7 %. Forty-two of 44 calls saturate the tool at four speakers, so `speaker_count`
is a floor rather than a count, and the dominance stratum is the primary one exactly as §6 required.

**One thing §2 could not have known.** The preflight geometry (one file, one worker, batching off)
and the corpus geometry (a directory, four workers, batching on) are not bit-identical: on `4386541`
they produce 123 vs 120 segments with boundaries shifted by one or two 80 ms frames. That is a
batched-GPU-reduction effect, the same class this program already records for greedy `llama-server`
decoding, and §2's Route A fallback is written for a tool that "disagrees with itself". It does not
disagree where this artifact is read: **0 count-stratum, 0 dominance-stratum and 0 dominant-speaker
disagreements over all 13 windows** (`geometry-agreement.json`). Route B stands, and the artifact is
built from the corpus-pass RTTMs only.
