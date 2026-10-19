# slurp-asr339-foldb-transcription-v1: Qwen3-ASR qualification pass over TRAIN Fold B (CPU sidecar)

Date: 2026-10-19. Owner rulings 339 (triggered ASR tool) and 342 A (candidates are only the open Qwen3-ASR 0.6B and 1.7B;
VRAM-bounded tool). Spec: `docs/superpowers/specs/2026-10-19-slurp-triggered-asr-tool-design.md`. This package is an
INSTRUMENT: it measures tool quality so the root can compare Qwen3-ASR with the sealed Whisper large-v3 Fold B catalog.
It is never a delivery step, makes zero core contacts, and answers nothing. The tool contract (Solver offer,
cite-and-protect, receipt) is a later build step and is not in this package.

**Status: prepared, NOT run.** Only the 4-row smoke below was executed (diagnostics, not a ledger-bearing pass).

## 1. Parts

| part | path |
| --- | --- |
| CPU sidecar | `scripts/flights/direct/asr_sidecar.sh` (+ `asr_sidecar.py`) |
| transcribe / score driver | `scripts/analysis/asr339/foldb_transcription.py` |
| launch spec | `docs/readiness/2026-10-19-slurp-asr339-foldb-transcription-v1/launch-spec.json` |
| tests | `tests/unit/test_asr339_sidecar_instrument.py` |

Asset identity comes from the umbrella lock entries `qwen3-asr-0.6b-gguf` and `qwen3-asr-1.7b-gguf` (umbrella commit
`70b4bb5`, branch `sonnet/asr339-lock`; it must be on umbrella master before the full pass). Nothing is copied out of
the lock. The lock path is `--lock` / `SAEA_ASR_LOCK`, default the master umbrella lock.

## 2. Sidecar facts

- Runtime: the pinned build `04ccc72a2` binary `/home/chao/llama.cpp-featcache/build/bin/llama-server` (mtmd Qwen3 audio
  support). Each model loads with its bf16 mmproj on CPU: `-ngl 0 --no-mmproj-offload -t 8 -c 4096 -np 1`, and the
  process is started with `CUDA_VISIBLE_DEVICES=` so it cannot touch the GPU held by a flight.
- Port: **8190** (never 8080). One sidecar at a time on that port; pass `--port` to run both.
- Reaper safety: the argv is `llama-server --port 8190 --host 127.0.0.1 ...`. The core serving entry reaps with
  `pgrep -f 'llama-server --host'`, which does not match because `--port` precedes `--host`. Verified live with `pgrep`:
  only the core server (port 8080) matched while the sidecar ran. The E5 port-8080 detector regex does not match either.
- Session receipt: `$SPEECHRL_DATA_DIR/serving/asr-sidecar-<model-id>/session.json` (schema
  `saea-asr-sidecar-session-v1`: model and mmproj paths with the lock SHA-256, lock revision, build commit, argv, port, pid,
  started_at) plus `session-stop.json` and `server.log`. `start` stays in the foreground and verifies both files'
  size and SHA-256 against the lock before launching.
- Audio is sent as an OpenAI-compatible `input_audio` content part (base64 FLAC, no text part) to
  `/v1/chat/completions`, temperature 0, max_tokens 256. Output form `language <L><asr_text><text>`; the driver strips it.

## 3. Procedure for the full pass (root only)

```bash
export SPEECHRL_DATA_DIR=/home/chao/saea-data/speechrl-data
bash scripts/flights/direct/asr_sidecar.sh start qwen3-asr-0.6b &          # live background wrapper
python3 -B scripts/analysis/asr339/foldb_transcription.py transcribe --model-id qwen3-asr-0.6b --full \
    --out $SPEECHRL_DATA_DIR/prepared/SAEA-SLURP-ASR339-TRANSCRIPTS-V1/qwen3-asr-0.6b
bash scripts/flights/direct/asr_sidecar.sh stop qwen3-asr-0.6b
~/.venvs/speechrl/bin/python -B scripts/analysis/asr339/foldb_transcription.py score --containment \
    --transcripts $SPEECHRL_DATA_DIR/prepared/SAEA-SLURP-ASR339-TRANSCRIPTS-V1/qwen3-asr-0.6b --out <dir>/score.json
# repeat for qwen3-asr-1.7b
```

`--full` refuses unless `docs/exposure-ledger.md` carries `SAEA-SLURP-ASR339-FOLD-B-V1` exactly once, unconsumed and
countersigned. `--smoke` is limited to 4 rows and to `diagnostics/ASR339-SMOKE/`. An existing `transcripts.jsonl` is never
overwritten (one-shot).

Outputs per model: `transcripts.jsonl` (schema `saea-asr339-transcript-row-v1`: sample_id, status, transcript,
audio_sha256, audio_seconds, asr_seconds, token counts), `catalog.json` (schema `saea-asr339-transcript-catalog-v1`:
model and mmproj SHA-256, build commit, split identity hash, transcripts SHA-256, decoding config hash, wall seconds,
server peak RSS), `score.json` (schema `saea-asr339-foldb-score-v1`).

Scoring mirrors E5 and the design note: canonical-token WER (`rails.relisten.canonical_value` tokens, edit distance,
reference sentence from the governed TRAIN loader, in memory only); all-gold span containment; missed-slot and
value-error containment on the NX-T R2b `budget-3072` Fold B delivered column (the v3.0 lock form, 1,080 rows).

Whisper comparators (Fold B): canonical WER 0.152; all-gold containment 0.7606; missed-slot containment 0.625 (70/112);
value-error containment 0.367 (61/166). The design note keeps a candidate only if its canonical WER is below 0.152 and
its `missval_disc_W` ceiling exceeds Whisper's +5.07 pp by at least +1.0 pp at perfect conversion.

## 4. Cost estimate (CPU, from the smoke)

0.6B: 0.52 s per clip (about 0.21 x real time) so about 9.4 min for 1,080 clips. 1.7B: 1.20 s per clip (about 0.48 x
real time) so about 21.5 min. Peak resident memory 2.54 GiB and 5.17 GiB. CPU only; no GPU.

## 5. Smoke (first 4 Fold B rows, both models, CPU) — numbers only

Recorded under `$SPEECHRL_DATA_DIR/diagnostics/ASR339-SMOKE/<model-id>/` (transcripts, catalog, score.json) with the
sidecar receipts under `.../ASR339-SMOKE/serving/`.

| model | loads on CPU with mmproj | canonical WER (edits / ref tokens) | s per clip | server peak RSS |
| --- | --- | --- | --- | --- |
| qwen3-asr-0.6b | yes | 0.35 (7 / 20) | 0.52 | 2,660,736 KiB |
| qwen3-asr-1.7b | yes | 0.50 (10 / 20) | 1.20 | 5,417,260 KiB |

Reading: 4 clips and 20 reference tokens, so the WER is not an estimate; the pinned build is not mis-transcribing in
form (every row status ok, hypothesis token counts 20 and 20-23 against 20 reference tokens, no stray tags, ASCII text).
The qualification verdict belongs to the full pass.

## 6. Prepared exposure-ledger row (NOT appended; the root appends and countersigns it)

```
SAEA-SLURP-ASR339-FOLD-B-V1 | 2026-10-19 | bounded-discovery-probe | TOOL CONTACT, instrument pass | split role discovery
(TRAIN Fold B, split identity hash 4407794c4a5d2e8883d93fdf242deb33c0987405d62e05a7d8416f5251a3484a, 1,080 rows) |
0 core calls; 2,160 ASR calls (1,080 clips x 2 models: qwen3-asr-0.6b and qwen3-asr-1.7b, pinned build 04ccc72a2,
CPU sidecar port 8190, bf16 GGUF + bf16 mmproj per the umbrella lock) | 3,155 speech-audio seconds per model |
purpose: qualification of the open Qwen3-ASR candidates against Whisper large-v3 (WER, gold-span, missed-slot and
value-error containment); transcripts never enter a decision, prompt or retrieval key (decision 201) | one-shot,
no automatic retry | consumed = no | root countersignature: pending
```

## 7. What the root must do before the full pass

1. Land umbrella commit `70b4bb5` on umbrella master (or point `SAEA_ASR_LOCK` at that worktree's lock) and merge study
   branch `sonnet/asr339`.
2. Append and countersign the ledger row above in `docs/exposure-ledger.md` (the driver reads it).
3. Run when no generation flight is alive and the host has about 6 GiB free for the 1.7B sidecar; the core server on
   port 8080 is not touched and the GPU is not used.
4. Close the ledger row (`scripts/flights/batch/ledger_mark_consumed.py --apply`) after both models are sealed.
