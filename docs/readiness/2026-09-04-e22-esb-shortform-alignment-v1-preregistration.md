# Earnings-22 short-form alignment against the only same-model published number, v1 preregistration (DRAFT, not registered, not authorized to fly)

Status: drafted 2026-09-04. Blocked on ONE owner decision (section 2): the six calls that define the published
"Earnings22" test subset all sit inside this study's Earnings-22 confirmatory split.

## 1. Why this cell exists

The owner's alignment goal (within 3 points of the published number, or better) has exactly one same-model,
same-task published target across the three carriers: **Qwen3-Omni-30B-A3B-Instruct, zero-shot, Earnings-22
"short-form" test subset, WER 9.79** (NVIDIA NeMo AutoModel, "Fine-Tune Qwen3-Omni for ASR"; Whisper
`EnglishTextNormalizer` on both sides; greedy decoding; N = 2,741 utterances), cross-read by **12.3** for the same
model on the Open ASR Leaderboard English subset (Nemotron 3 Nano Omni, arXiv:2604.24954v2 Table 8). The two
vendor numbers disagree by 2.5 points, so the band the study can claim is "consistent with both" at best.

The subset is not the 125-file corpus: "Earnings22" on the leaderboard is the ESB partition by source file,
**test = calls 4432298, 4450488, 4470290, 4479741, 4483338, 4485244** (validation = 4420696, 4448760, 4461799,
4469836, 4473238, 4482110; train = the remaining 113), cut at punctuation boundaries into utterances of at most
20 s by wav2vec2 forced alignment (2,741 rows in `hf-audio/open-asr-leaderboard` config `earnings22`; 2,735 rows
with `source_id`, `start_ts`, `end_ts`, `sentence` in `sanchit-gandhi/earnings22_split`; the 6-row gap is
unexplained and is recorded as such). Degraded-model floors on the same column (leaderboard revision of
2026-09-04): whisper-large-v3 11.59, whisper-large-v3-turbo 11.07, distil-large-v3.5 10.83, Qwen3-ASR-0.6B
10.78, Qwen3-ASR-1.7B 9.73; older vintage (2026-06-13, before the normalizer/hardware change): whisper
medium.en 12.63, small.en 12.97, base.en 15.09, tiny.en 19.12.

Decision rule under the owner's goal: ALIGNED if corpus-level Whisper-normalized WER is at most 12.79 (9.79 + 3)
and the floor rule holds (not above whisper-large-v3's 11.59 is the strict reading; not above whisper-base.en's
15.09 is the loose reading; both are reported); ALIGNED-BETTER if below 9.79 by more than 3; otherwise NOT
ALIGNED, with the per-call table and the gap decomposition (segmentation, quantization, serving) reported.

## 2. The owner decision this draft is blocked on

`docs/receipts/splits.json` places all twelve ESB test and validation calls in the study's **confirmatory** split
(115 calls); the dev subset10 (4453225, 4469088, 4470684, 4474506, 4479944, 4481952, 4482383, 4482613, 4483937,
4485192) contains none of them and carries no published number. Any Earnings-22 alignment therefore reads
confirmatory audio and references. Proposed handling, for the owner to accept or refuse:

- read ONLY the six ESB test calls, once, as a direct-baseline calibration (no mechanism arm, no knob tuned);
- re-designate those six ids as `calibration-exposed` in `docs/receipts/splits.json` (successor record, the
  original hash retained), leaving 109 confirmatory calls for final reporting;
- record the read in the exposure ledger as a confirmatory-split exposure with this justification.

## 3. Population and materials

- Audio: the six calls from the locked `earnings22-original` asset already on disk; utterances cut locally from
  those MP3s at the published `start_ts` / `end_ts` (the segment table is a small external reference pinned by
  SHA-256 in a receipt; no new audio asset is downloaded). Local cutting reproduces the utterance boundaries, not
  the byte-exact HF chunks; the WER effect is negligible and is stated.
- References: the `sentence` field of the segment table (the leaderboard's `text`), normalized with the vendored
  Whisper English normalizer at scoring time; references are never in the request path.
- Requests: one utterance per contact, the speech-native direct arm through `core.flight.FlightRuntime`, the
  Earnings adapter's ASR task contract, greedy (temperature 0), `max_tokens` sized to the longest reference plus
  margin; raw audio through the bf16 mmproj; build 04ccc72a, Q4_K_M.
- Scoring: `asr-wer-whisper` (Whisper normalizer both sides) reported corpus-level (total edits over total
  reference words) as the paper-facing number, beside the mean of per-utterance WER and the frozen
  `saea-scoring-v1` `asr-wer`; per-call table for the six calls.

## 4. Budget (ExecutionPlan, to be filled at registration)

About 2,741 calls plus canaries, about 5 h of speech audio, planned 1.5 GPU-h (ceiling 2.0); paid API spend 0.
A 4-row smoke precedes the flight. Prerequisites: segment-table receipt, D1 identity supplement for the utterance
ids, prompt-fit receipt, wire check on a clean tree, ledger row before any contact.

## 5. What this preregistration does not authorize

No mechanism arm; no read of the other 109 confirmatory calls; no fine-tuning comparison (NeMo's 8.89 is a
fine-tuned number and is reported only as context); no Q8_0 cell; no superiority or Stage-3 claim.

## 6. Owner decision and execution log

Pending.
