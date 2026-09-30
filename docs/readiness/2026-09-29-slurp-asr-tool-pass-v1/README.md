# E5-0 / E5-1 registration: the pinned Whisper transcript pass and the offline oracle read

Status: **prepared, not run.** Nothing here has contacted a model, a tool, an encoder or the GPU. The three
exposure-ledger rows are DRAFT and wait for the root countersignature. Design:
`docs/superpowers/specs/2026-09-29-e5-asr-tool-slot-value-verification-design.md` and its addendum of
2026-09-29 (the owner supplement to decision 201).

## What E5 is now: an instrument, not a delivery step

Owner decision 201 (option A, 2026-09-29) changed the direction: the study builds the system and optimises it
at system level, and a pinned ASR is a legitimate system component. The owner supplement of the same day
fixes how a tool may act: **a tool is invoked by the model on its own initiative, never applied by the system
by default.** A system that runs ASR and then edits the answer is ASR + LLM, not an omni agent system, and
measuring it would prove only itself.

So:

- **E5-0** (the transcript pass) and **E5-1** (the offline read) are INSTRUMENTS / ORACLES. They bound what a
  perfect tool call could yield and measure the decision the model would have to learn.
- The three deterministic rules of E5-1 (R-FLAG, R-DROP, R-SWAP) are **oracle bounds of a system-applied
  check**. None of them, including the former "E5-2a", is a runtime candidate.
- The runtime form is **E5-2: the frozen core is OFFERED a pinned ASR tool and DECIDES whether to call it**
  (addendum, section A3). No code for E5-2 exists yet.

The boundary is unchanged: the frozen core keeps final answer authority; the tool is pinned (umbrella lock
`whisper-large-v3-openai-pt`) and logged (rows before contact); gold never enters runtime; transcripts never
reach the intent decision, the Perception or Solver prompts, or a retrieval key.

## Files

| file | what |
| --- | --- |
| `fold-a-gpu/`, `fold-a-cpu/`, `fold-b-gpu/`, `fold-b-cpu/` | `preparation-protocol.json` + `preparation-plan.json` (envelope) of each roster x device, written by `e5_asr_tool_pass.py register` and re-derived byte-identically by every `check` / `run` |
| `e5-1-read-recipe-v1.json` | the E5-1 recipe: inputs, canonicaliser, rules, tuning grid, statistics and the pre-declared bars |

| roster | row | split | rows | speech s (planned) | source inventory (sha256) |
| --- | --- | --- | ---: | ---: | --- |
| TRAIN Fold A | `SAEA-SLURP-ASR-TOOL-PASS-V1` (also the umbrella row) | `61b0f062…` | 1,080 | 3,084.53 (3,085) | `prepared/SAEA-SLURP-TRAIN-A-LIVE-SPEECH-SOURCES-PREPARE-V1/sources.json` (`e756e7f7…`, landed 2026-09-14; re-derived byte-identically) |
| TRAIN Fold B | `SAEA-SLURP-ASR-TOOL-PASS-FOLD-B-V1` | `4407794c…` | 1,080 | 3,154.80 (3,155) | `prepared/SAEA-SLURP-TRAIN-B-ASR-TOOL-PASS-SOURCES-V1/sources.json` (`1a8117a3…`, model-free, written by the pass if absent) |

The Fold B source inventory is built from `configs/dataset/slurp-speech-native-evo-fold-b-1080.json` and the
EVO-FOLDS-V2 promotion receipt (`/home/chao/feat-cache/slurp-q4km-packets-04ccc72a/EVO-FOLDS-V2-promotion.json`,
`4f048f47…`): packet and original-audio metadata only, no audio decode. The same builder reproduces the landed
Fold A inventory byte for byte, which is the proof that it matches the flight runtime's own export.

## Decode settings (quoted from the DEV-1000 recovery run)

GPU, byte for byte the `decoding` block of
`docs/readiness/2026-09-12-slurp-whisper-recovery-v1/preparation-protocol.json`: `batch_size` 8, `beam_size` 5,
`cpu_workers` 8, `device` `cuda`, `fp16` true, `language` `en`, `logprob_threshold` -1.0,
`no_speech_threshold` 0.6, `sample_len` 224, `task` `transcribe`, `temperature` 0, `without_timestamps` true.
CPU fallback: the same decode fields with `device` `cpu`, `fp16` false, `batch_size` 1, `cpu_workers` 1,
`cpu_thread_limits` 4 inference + 1 interop (the 2026-09-14 Fold A CPU envelope). Neither carries a prompt or
`initial_prompt`, so Whisper is conditioned on no text. Checkpoint and patched source: the recovery runtime
inventory (`79c79469…`), checkpoint `large-v3.pt` sha256 `e5b1a55b…1dadb`.

## E5-0 CLI

```bash
# model-free
python -B scripts/analysis/e5_asr_tool_pass.py sources  --roster fold-b            # would-be sha256, no write
python -B scripts/analysis/e5_asr_tool_pass.py register --roster fold-a --device gpu --check
python -B scripts/analysis/e5_asr_tool_pass.py check    --roster fold-a [--cpu]    # exit 0 admissible, 3 refused
bash scripts/flights/e5/e5_tool_pass.sh both --check
# the contact (queue only, in the restart gap)
bash scripts/flights/e5/e5_tool_pass.sh both [--cpu]   # -> e5_asr_tool_pass.py run --roster fold-a, then fold-b
```

`e5_tool_pass.sh` runs the driver with `~/.venvs/saea-whisper-gpu/bin/python` (override `SAEA_E5_PY`), with
`PYTHONPATH` set to this checkout's `src`, `CUDA_VISIBLE_DEVICES` empty under `--cpu`, and stops at the first
failing roster.

**Refusals** (every one checked by `check` and again by `run`, before any contact):

1. the roster row and the umbrella row `SAEA-SLURP-ASR-TOOL-PASS-V1` must exist once, read `consumed = no`
   and carry "root countersigned" in their notes (a "countersignature pending" note refuses);
2. no generation flight is alive: `$DATA/locks/flight.lock`, or a `core.flight.cli campaign|worker`,
   `batch_driver.sh` or `core.flight.lease_cli` process (the same patterns as `serving_lib.sh`);
3. GPU mode: no llama-server holds port 8080, so the serving session is down; otherwise pass `--cpu`;
4. the umbrella lock carries `whisper-large-v3-openai-pt` pinning checkpoint sha256 `e5b1a55b…` as COMPLETE;
5. the checkout is clean;
6. the registration files re-derive byte-identically;
7. no attempt of the run exists without a sealed catalog (a failed attempt needs its own recovery
   registration), and the other device has not already sealed this roster (one pass per roster).

The producer itself (`core.preparation_speech_observations.run_speech_observation_preparation`, unchanged)
then admits the plan against the ledger and the lock, acquires the generation lease, opens the attempt with
its reserved budget, and seals one `speech-tool` artifact per utterance plus the
`saea-prepared-speech-observation-catalog-v1` catalog. A sealed roster is the warm path: no contact.

**Outputs.** The producer catalog under `prepared/<run>/<attempt>/catalog.json` is published byte-identically
to `prepared/SAEA-SLURP-ASR-TRANSCRIPTS-V1/<roster>/catalog.json`, beside `receipt.json`
(schema `saea-slurp-asr-tool-pass-receipt-v1`) with: roster, run and attempt ids, ledger rows, split identity
hash, source-inventory pin (the roster hash), utterance count, speech seconds, device mode, the model (lock
entry, checkpoint path, bytes, sha256), the runtime-inventory pin, the Whisper source path and package pins,
the decode settings and `decoding_config_sha256`, the protocol and plan pins, the producer's own sealed
receipt, the catalog pins, the study commit, the exposure-ledger and umbrella-lock sha256 at run time, the
environment (Python, platform, torch / numpy / tiktoken / soundfile / triton versions, GPU name and driver,
`CUDA_VISIBLE_DEVICES`), start time and wall seconds, and `core_contacts` 0. No text.

The producer pins `docs/exposure-ledger.md` at its run-time sha256. That file keeps growing, so a later
consumer that reloads the catalog through `rails.speech_observation` must pin the historical bytes
(`git show <study_head>:docs/exposure-ledger.md`, the receipt records both the commit and the sha256).

## The restart-gap hook (coordinator ruling Q4)

`scripts/flights/batch/serving_restart_hook_e5.sh` runs only when `/home/chao/e5-tool-pass.request` exists
(the root creates it after countersigning both tool-pass rows; a line `mode=cpu` selects the fallback). It
takes an flock (a concurrent call logs `E5-0 BUSY`), logs `E5-0 START`, runs `e5_tool_pass.sh both`, logs
`E5-0 DONE` and removes the request, or logs `E5-0 FAILED rc=N` and renames the request to
`.failed-<stamp>` (no automatic retry). Log: `/home/chao/e5-tool-pass.log`.

`serving_swap.sh` gained `--gap-hook <script>` (valid only with `--restart`): the script runs after the clean
stop (port 8080 verified free) and before the start, under the swap lock and the pending marker, and its exit
status is recorded as step `gap-hook` and never stops the start. The live queues are not edited here; to arm
E5-0, the queue's `maybe_restart()` changes one line:

```bash
rc=0; ql_swap slurp-np4 --restart --gap-hook "$B/serving_restart_hook_e5.sh" || rc=$?
```

Expected cost: about 10 min per roster on the GPU (model load plus about 5 min of decode), about 20 min of
core downtime for both, 0 core contacts.

## E5-1 CLI and metrics

```bash
python -B scripts/analysis/e5_transcript_consistency_read.py --mode tune --roster fold-b \
    --arm psv2=SAEA-SLURP-STAGE3-PSV2-FOLD-B-V1/<attempt>
python -B scripts/analysis/e5_transcript_consistency_read.py --mode read --roster fold-a \
    --params <tune-fold-b>/params.json --params-sha256 <sha> \
    --arm agree=SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1/attempt-slurp-native-stage3-agree-w1-fold-a-generation-v1 \
    --arm wave_aa=SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1/attempt-slurp-native-stage3-wave1-aa-fold-a-generation-v1 \
    --replicate wave_aa --expect-e4-broken 63 \
    --e4 SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-V1/attempt-slurp-native-stage3-relisten-fold-a-generation-v1-seal-only
```

`tune` refuses a Fold A catalog and `read` refuses a Fold B catalog. The read reports gold-span containment
(precondition >= 0.80), exact preservation on E4-1's EXACT -> BOUNDARY items (>= 0.85), wrong-value
containment per error kind, each rule's official pooled SLU-F1 delta vs the delivered column (paired row
bootstrap, 10,000 draws, seed 20260929, CI95) with per-type tables and FORMAT / BOUNDARY transitions, and the
tool-call decision oracle with one AUC per model-visible signal. The in-process arithmetic must reproduce the
sealed official totals of every arm or the read refuses. Output:
`analysis/SAEA-SLURP-E5-TRANSCRIPT-CONSISTENCY-READ-V1/<mode>-<roster>/`.

The deterministic scope rule of the headroom note is not composed here; composing it is a follow-up once
E5-1's precondition passes.
