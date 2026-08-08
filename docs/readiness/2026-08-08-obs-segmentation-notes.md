# OBS segmentation v1 — the obs-agent-loop (design record + operator runbook)

Date: 2026-08-08. Authority: owner session directives of 2026-08-08 —
(1) whole-call single requests rejected, long-form audio must be windowed
("the frozen core must never be asked to process a whole 40-75-minute
earnings call in one request"); (2) architecture pivot: the OBS layer is a
model-driven agent loop inside a policy, not precomputed segments;
(3) additions: VAD boundary snap + VAD pre-trim + rms-norm preprocessing;
(4) tail conditioning (Whisper-style condition-on-previous) as Node-1
knowledge v1. This document is the design record those directives asked for.

## 1. What shipped

One policy, `obs-agent-loop` (`reproduction/obs_loop.py`, registered in
`core/policies.py`), plus the rail work that makes it legal:

- **One sample = one whole call.** Splits, the splits receipt, D1 identity,
  the exposure conventions and the outputs-row shape are all untouched. The
  earlier fixed-window segment-as-sample scaffold (segment ids, segments
  receipts, derived-media D1 layer, `asr-wer-concat`) was built, then
  dropped un-merged on the pivot directive; nothing of it is in history.
- **Per sample:** decode the parent media once (16 kHz mono PCM); optionally
  VAD-pre-trim long non-speech; loop: cut a buffer slice
  (`obs_buffer_seconds`, default 60), send ONE request carrying that slice,
  parse `TRANSCRIPT: ... BOUNDARY_SECONDS: <n>`, resolve the boundary
  through three tiers, accept transcript up to the boundary share via the
  deterministic sentence-cut rule, advance, repeat; final window accepts
  everything. Hypothesis = ordered concatenation of accepted spans; the
  outputs row carries it once per sample.
- **Boundary tiers** (`reproduction/obs_audio.resolve_advance`, all logged
  per iteration in the OBS trace record):
  1. model estimate (strict parse; last `BOUNDARY_SECONDS` line wins);
  2. snap to the nearest VAD speech/non-speech TRANSITION within
     ±`obs_silence_snap_seconds` (default 2);
  3. clamp into [`obs_min_advance_seconds`, `obs_max_advance_seconds`]
     (defaults 20/55). Unparseable/out-of-range estimate → fixed
     `obs_fallback_advance_seconds` (default 50), `obs_boundary_fallback:
     true` in the trace.
- **Sentence-cut rule (exact):** `limit = round(len(text) ×
  advance/buffer_len)`; accept through the LAST sentence-final character
  (`.!?…。！？`) inside `text[:limit]`; if none, accept the raw `text[:limit]`
  cut (dropping everything would lose real content; the next buffer
  re-covers the seam). Final window: accept all.
- **VAD v1:** deterministic pure-Python energy VAD (30 ms frame RMS;
  threshold `max(floor, min(3×p10, 0.5×p90))` — the p90 cap exists because a
  uniformly energetic recording would otherwise read as all-non-speech and
  pre-trim would skip the whole call; found by test). `obs_vad: "webrtc"` is
  runtime-detected (fail-closed if requested and absent) and never enters
  `pyproject.toml` — the dependency set stays pinned at zero. Engine +
  version land in the trace and the derivation record.
- **VAD pre-trim:** non-speech spans > `obs_vad_trim_min_seconds` (default
  5; 0 disables) are skipped before a buffer is cut. Trimmed seconds never
  enter a payload, so they are never metered (payload `audio_seconds` is the
  slice actually sent — enforced by the rail, §2). Every trim is an OBS
  trace record with from/to seconds + engine.
- **Preprocessing v1 (default OFF):** `obs_preprocess: ["rms-norm"]` —
  per-slice RMS loudness normalization to `obs_rms_target_dbfs` (default
  −20 dBFS), applied after cutting, before writing; the derivation record
  carries `preprocess`, `pre_sha256` (raw cut) and `sha256` (written bytes).
  No denoising in v1 (future ablation arm).
- **Tail conditioning (Node-1 knowledge v1):** each iteration's rendered
  `task_instruction` appends the tail of the previously ACCEPTED transcript
  (`obs_condition_tail_chars`, default 400; 0 disables and reproduces the
  unconditioned loop exactly — tested). The tail is MODEL OUTPUT — never
  gold, never a reference transcript — framed by the frozen
  `OBS_TAIL_FRAME_V1` string as prior context, not instruction. It rides
  inside `task_instruction` (not an evidence field) because the bare-core
  arm's D2-frozen 10-field payload set must not change; evidence arms keep
  their evidence fields for actual evidence.
- **Fixed-window ablation (arm A) for free:** `obs_boundary_mode: "fixed"`
  degenerates the same policy to buffer=advance windows, no boundary
  request, no snap (`configs/baseline/bare-core-obsfixed.json`: 30 s
  windows, trim off, tail off).

### Knowledge routing (owner-aligned, recorded for later phases)

Node-1 knowledge v1 = tail conditioning only. Phase-2 arms, deliberately NOT
built now: entity-glossary-aware boundaries; Node-2 confusable-set injection
(phonetic-key derivation from ConEC materials + self-detected cross-segment
inconsistencies, RECOVER-class); a correction re-ask pass. v1 stays tight.

## 2. The rail work (review this)

The one new trust-boundary mechanism is slice admission:

- `core/model/slices.py` — `SliceRecord` + `SliceRegistry`. A slice is
  admitted only when its derivation record CHAINS to the sample's registered
  media: parent path must equal the loader-bound path; `parent_sha256` must
  equal the hash of the parent bytes on disk (the same file
  `verify_media_identity` re-verified against D1 when the gate opened, so
  the chain bottoms out at D1); `[start, end)` must lie inside the parent's
  loader-fact duration (+1.0 s tolerance for CSV-vs-decoder rounding); the
  slice must live at `derived/obs-slices/<run_id>/<sample_id>/i<NNNN>.wav`
  under the data root and hash to the record. Registration re-hashes; the
  send path re-hashes AGAIN per request.
- `core/model/binding.py` — `_enforce_payload_binding` branches on the
  media path BEFORE the audio/rate fact checks: parent path → every
  pre-existing check byte-for-byte; any other path → registered slice or
  the original exact-relpath refusal. Slice payloads bind `audio_seconds` /
  `sample_rate_hz` to the SLICE record (this is what makes metering charge
  exactly the seconds sent — the sample-rate check deliberately uses the
  record, not the parent CSV fact: real e21/e22 CSVs carry 22050/24000 Hz
  rows while slices are always 16000). Confinement for slices moves to the
  run's own slice tree.
- `core/driver/run.py` — builds ONE `SliceRegistry` per run from the same
  loader facts as the binding context, hands it to both the adapter (rail)
  and the policy (`SampleContext.extras`). Whole-file policies are
  untouched (an empty registry admits nothing; full pre-existing adapter
  and driver suites green).
- **I7 stitch binding:** the outputs row is one stitched hypothesis, so the
  policy emits terminal `{req}/request` + `{req}/response` trace records
  (flagged `"stitch": true`, no COST record — no model call is implied)
  carrying exactly the descriptor hashes the row binds to; per-iteration
  MODEL_REQUEST/RESPONSE records are chained inside the descriptors by
  request id and hash. Proven against the real `verify_bundle` in
  `tests/unit/test_obs_loop_integration.py`.
- **Declared, not re-derived:** the rail verifies parent identity, offset
  bounds and written-slice bytes. It does NOT re-run the DSP (decode/cut/
  rms-norm) to prove `pre_sha256`/the cut content; that is declared
  provenance in the derivation record. Re-deriving would mean re-decoding
  the parent on every request; the honest guarantee is stated as this split.

### D1 / `verify_media_identity`: no amendment needed (verified)

`FrozenCoreGate.verify_media_identity` re-hashes exactly what
`PayloadBindingContext.media_relpaths` names — and `run.py` builds that from
the carrier loader's PARENT media paths, which are D1-recorded. Runtime
slices never reach it: they are admitted downstream by the slice rail, whose
`parent_sha256` chain terminates at the same gate-verified parent bytes. The
transport's own confinement is `data_root`-wide and slices live under
`data_root/derived/obs-slices/` — no change there either. Therefore
`e0/d1_identity.py`, `docs/receipts/artifacts/d1-identity.json` and the E0
closure are untouched; the earlier planned "derived-segments D1 layer +
amend script" is obsolete and was not landed.

### Scorer: plain `asr-wer` (verified; `asr-wer-concat` dropped)

The loop emits ONE outputs row per whole-call sample with the stitched text,
`sample_id` = the parent call id. `score_asr_outputs` resolves references by
that id and the reference-identity gate scopes to the bundle's split ids —
both unchanged. A concatenation scorer would have re-implemented what the
policy already guarantees; keeping `asr-wer` is the honest choice
(integration test scores a stitched bundle through the frozen stack).

### D2 / arm shapes: no re-freeze needed (verified)

Every iteration's request flows through `build_arm_payload` under the
existing `ARM_VISIBLE_FIELDS`; the field SETS are unchanged — the boundary
protocol and the tail ride inside the rendered `task_instruction` string,
and the slice path/seconds ride in the existing `media_relpath` /
`audio_seconds` fields. `contracts.assert_information_boundary` still runs
on every payload.

### Pinning status (honest note)

All `obs_*` knobs live in the baseline fragments → `config_hash` →
`protocol_hash`. The boundary TEMPLATE FILE's bytes and the
`OBS_TAIL_FRAME_V1` constant are not inside `protocol_hash` (it pins the
template's relative path via config); the template sha256 is recorded in
every iteration's OBS trace record and in the per-sample derivation record,
and the rendered instruction lands verbatim in every MODEL_REQUEST trace
record. If the owner wants template bytes inside the pre-registered hash,
the probe-manifest pattern (`reproduction/manifest.py`) is the seam.

## 3. Config surface

Fragments (all knobs byte-identical across the three R4 arms except the
evidence semantics they inherit from their whole-call counterparts):

| fragment | arm | policy knobs |
|---|---|---|
| `baseline/bare-core-obsloop.json` | bare-core | buffer 60, adv 20/55, snap 2, fallback 50, mode model, energy VAD, trim 5, preprocess [], tail 400 |
| `baseline/fixed-legal-context-obsloop.json` | fixed-legal-context (conec-contexts, every iteration) | same |
| `baseline/mismatched-evidence-obsloop.json` | fixed-legal-context + `evidence_mismatch` | same |
| `baseline/bare-core-obsfixed.json` | bare-core, OBS ablation arm A | buffer 30, mode fixed, snap 0, trim 0, tail 0 |

Template: `configs/probes/obs_boundary_v1.txt` (frozen; edit = new file +
new config value). Datasets: the existing `earnings22-dev-subset10` /
`earnings21-discovery` fragments — no new dataset fragments (whole-call
samples).

## 4. Budget arithmetic (real metadata, computed 2026-08-08)

Model: calls/sample ≈ `ceil((D−60)/45)+1` (mean advance 45 s of a 60 s
buffer); metered seconds ≈ 1.33×D (tail overlap 15/45). Worst case (every
boundary clamped to min advance 20 s) ≈ 3×D metered — set headroom against
the mean model, abort long before worst case.

| split | calls (audio) | obsloop est. calls | est. metered s | suggested plan (headroom ≈ +30%) |
|---|---|---|---|---|
| e22 dev subset10 | 10 (40,054 s) | 892 | 53,284 | 1,200 calls / 70,000 s |
| e21 discovery (44) | 44 (141,349 s) | 3,149 | 187,924 | 4,100 calls / 245,000 s **per arm** |
| e22 sub10, obsfixed 30 s ablation | 10 | 1,340 | 40,054 | 1,600 calls / 44,000 s |

R4 on the full discovery split × 3 arms ≈ 9,450 calls / ~156 h metered
audio. The numeric caps are retired (2026-08-06 amendment), but a **mini**
R4 wants a smaller parent set: a 10-call e21 subsample receipt
(`r4-e21-sub10-sample.json`) does NOT exist and drawing it is a sample-once
act — owner sanction + a `scripts/build_probe_samples.py`-pattern seeded
draw, not something this change fabricates. Until then the R4 obsloop
commands below run on `earnings21-discovery` (full 44) — scale plans
accordingly or authorize the subsample first.

## 5. Operator runbook (WSL, speechrl venv)

Step 0 — environment (once):
```bash
wsl -d Ubuntu-24.04
source ~/.venvs/speechrl/bin/activate
cd /mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
ffmpeg -version | head -1   # decode path; librosa in the venv is the fallback
python - <<'EOF'
import shutil; print("ffmpeg:", bool(shutil.which("ffmpeg")))
try: import librosa; print("librosa ok")
except ImportError: print("librosa MISSING (need ffmpeg then)")
EOF
```

Step 1 — pre-register the exposure row (`docs/exposure-ledger.md`) BEFORE
any command below, per the consolidated contract; use the planned numbers
from §4.

Step 2 — segmented E-001 smoke (bare core, obsloop, dev subset10):
```bash
saea-driver smoke \
  --model qwen3-omni-llamacpp --dataset earnings22-dev-subset10 \
  --baseline bare-core-obsloop --experiment r0-smoke \
  --run-id SAEA-E-001-obsloop-smoke \
  --planned-model-calls 1200 --planned-gpu-hours <owner-set> \
  --planned-speech-audio-seconds 70000 \
  --run-dir "$SPEECHRL_DATA_DIR/runs/SAEA-E-001-obsloop" \
  --runtime-root ~ --tracking-uri file:///home/<user>/mlruns
```

Step 2b — OBS ablation arm A (fixed 30 s windows, same split):
```bash
saea-driver smoke \
  --model qwen3-omni-llamacpp --dataset earnings22-dev-subset10 \
  --baseline bare-core-obsfixed --experiment r0-smoke \
  --run-id SAEA-E-001-obsfixed-smoke \
  --planned-model-calls 1600 --planned-gpu-hours <owner-set> \
  --planned-speech-audio-seconds 44000 \
  --run-dir "$SPEECHRL_DATA_DIR/runs/SAEA-E-001-obsfixed" \
  --runtime-root ~ --tracking-uri file:///home/<user>/mlruns
```

Step 3 — R4 context-dose obsloop arms (earnings21-discovery; see §4 for the
mini-subsample caveat; per arm):
```bash
for BASELINE in bare-core-obsloop fixed-legal-context-obsloop mismatched-evidence-obsloop; do
  saea-driver smoke \
    --model qwen3-omni-llamacpp --dataset earnings21-discovery \
    --baseline "$BASELINE" --experiment r4-context-dose \
    --run-id "SAEA-E-002-r4-${BASELINE}" \
    --planned-model-calls 4100 --planned-gpu-hours <owner-set> \
    --planned-speech-audio-seconds 245000 \
    --run-dir "$SPEECHRL_DATA_DIR/runs/SAEA-E-002-${BASELINE}" \
    --runtime-root ~ --tracking-uri file:///home/<user>/mlruns
  done
```
(One arm at a time in practice; each is its own pre-registered ledger row.)

Artifacts per run: outputs/trace/manifest as before, PLUS per-sample
`<run_id>.obs-derivation.<sample_id>.json` in the run dir and slice wavs
under `$SPEECHRL_DATA_DIR/derived/obs-slices/<run_id>/` (derived bytes,
never committed; safe to delete after finalize — the derivation record and
trace pin their hashes).

## 6. Verified vs assumed

Verified by tests/inspection: rail refusals (foreign file, tampered record,
out-of-parent offsets, unregistered path, swap-after-registration); metering
= slice seconds through the real adapter budget rail; verify_bundle +
score_bundle on a stitched run; tail=0 ablation identity;
`verify_media_identity` never sees slices (code path read end-to-end);
real CSV sample rates vary (22050/24000 Hz), which is why the slice branch
binds rate to the record. Assumed (not run here — no model, no WSL):
llama-server accepts 60 s WAV slices within context (the E-001 wiring memo's
context math applies per-slice now, far below the whole-call sizes that
failed); ffmpeg/librosa present in the WSL venv; real-model boundary-format
compliance rate (fallback tier absorbs non-compliance at 50 s/step).

## 7. Open items for owner/operator review

1. The stitch trace-record convention (`{req}/request`+`/response` with
   `stitch: true`, no COST record) — sanctioned shape for I7 on multi-request
   policies, or should `verify_bundle` grow a first-class notion?
2. R4 mini subsample: authorize an e21 10-call parent receipt (sample-once
   draw) or run the full 44-call discovery arms.
3. Boundary-template bytes inside a pre-registered hash (probe-manifest
   pattern) if wanted beyond trace-level pinning.
4. `obs_boundary_v1` prompt wording is v1 and untested against the real
   core; a revision is a NEW template file + config change by design.
