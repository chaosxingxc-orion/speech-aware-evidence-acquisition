# SLURP DEV-2000-ADDED packet preprocessing (ENCODE + PROMOTE), v1

Registration only (owner decisions 34, 35, 76a, 78, 79; docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md).
This package authorizes cell B6's two preparations, not the B6 arms themselves. Precedent:
`SAEA-SN-DEV1000-PREPROCESS` (2026-08-24, `configs/experiment/slurp-dev1000-preprocess.json`,
script `scripts/slurp_evo_fold_preprocess.py` describes the same two-phase shape for the EVO
folds). No model, tokenizer, encoder, network or GPU contact was made while drafting this package.

## What is bound

- Roster: `SLURP-DEV-2000-ADDED-V1`, `docs/receipts/rosters/slurp-dev-2000-added-v1.json`, split
  identity `ee6c43cd4dd8fc2a583d2dd053e799c2d002efa3755fcd092ba7c7565431bf67`.
- Runtime view: `configs/dataset/slurp-speech-native-dev2000-added.json`, sha256
  `6968a0564699968f1615bb98b45d2f0ccf179dd0a04351b2871bc096a9052477`.
- Composed config: model `q4km-preprocess-featcache-cpu-sidecar` (unchanged from the DEV-1000
  precedent) + dataset `slurp-speech-native-dev2000-added` + baseline `speech-native-preprocess`
  (unchanged) + experiment `slurp-dev2000-added-preprocess` (new fragment in this package).
  `config_hash` `0be0d987139895bd4bcb0f72914718b8c624cf35c02ea52b5ba4d840050121eb`; `protocol_hash`
  `a4498f5c21d5bf6adf99287167508e269c3ad002e7a1ba7a83b8e457777dd135` (arm `bare-core`, split
  identity as above). Both computed with `core.config.compose` / `core.config.protocol_hash` on
  this worktree at commit `51c7ec4dcabbc592ac86476c430f9279cb5a8bd9`.
- Full plan: `docs/readiness/2026-09-21-slurp-dev2000-added-preprocess-v1/plan.json`.

## Step 1 -- ENCODE (1,000 contacts, CPU sidecar, GPU-free)

Spawn the CPU-only sidecar exactly as the DEV-1000 precedent's model fragment specifies
(`configs/model/q4km-preprocess-featcache-cpu-sidecar.json`, unchanged):

```text
llama-server -m <Qwen3-Omni-30B-A3B-Instruct Q4_K_M gguf> --mmproj <bf16 mmproj> \
  -c 16384 -np 4 -b 512 -ub 128 -fa on -ngl 0 --no-mmproj-offload \
  --port 8081 \
  --host 127.0.0.1
# LLAMA_MTMD_FEAT_CACHE_DIR=/home/chao/feat-cache/slurp-q4km
```

pinned by the runtime receipt `docs/receipts/runtime-q4km-preprocess.json` (build commit
`04ccc72a`, per-file GGUF SHA-256 already on file from the DEV-1000/EVO-fold precedents; this
package pins no new binary). Drive one contact per row at `max_tokens: 1` with the fixed
instruction "Observe the complete speech signal for deterministic feature preprocessing. Respond
with OK." over the 1,000 `SLURP-DEV-2000-ADDED-V1` rows, workers <= 8 (per the packet-preparation
plan's CPU-campaign cap). Stop the sidecar with a targeted, non-forced stop and write its stop
receipt before step 2. The resident decoder-only service on port 8080 is never touched; its log is
snapshotted before/after the sidecar window per the DEV-1000 precedent's disclosure convention.

## Step 2 -- PROMOTE (0 contacts)

```text
python -c "
from speech_aware_evidence_acquisition.core.model.speech_features import (
    materialize_legacy_cached_speech_feature_packets)
materialize_legacy_cached_speech_feature_packets(
    runtime_view='configs/dataset/slurp-speech-native-dev2000-added.json',
    packet_root='/home/chao/feat-cache/slurp-q4km-packets-04ccc72a',
    workers=8,
)"
```

ADDITIVE ONLY: new `slurp/devel/<id>/` packet directories plus a new
`/home/chao/feat-cache/slurp-q4km-packets-04ccc72a/DEV-2000-ADDED-promotion.json`. No file the
resident session already serves is read-modified-written; no existing promotion receipt (for
example `DEV-1000-promotion.json`) is touched. Refuse-on-conflict is the safety property: any byte
mismatch against an already-served packet aborts before writing.

## The `DEV-2000-ADDED-promotion.json` receipt must carry

See `plan.json` `promotion_receipt_required_fields`: promoted count 1000/1000, the bound
`runtime_view_sha256`, per-row `packet_id -> audio_sha256`, the sidecar stop receipt reference
(`forced=false`), a zero-conflict assertion against every packet the resident root already serves,
and the legacy feature-cache warm-row count before/after the sidecar window (0 -> 1000 expected,
per `media-inventory.json`'s measured 0/1000 warm baseline).

## Exposure ledger

One row, `SAEA-SN-DEV2000-ADDED-PREPROCESS`, appended before any contact, `consumed = no`. It
covers BOTH steps in one row -- the precedent `SAEA-SN-DEV1000-PREPROCESS` folded its zero-contact
promotion into the same row as its 500 encode contacts rather than registering a second row, and
this package follows the same convention. Planned: 1,000 calls, 2,984 speech-seconds (rounded from
the packet-preparation plan's exact 2,983.527), 1.0 GPU-hours (nominal; own GPU offload is zero,
matching the DEV-1000 row's own characterization of a CPU-only sidecar pass).

## Reproduce this package

`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD/src`, then compute the composed config and protocol
hash with `core.config.compose` / `core.config.protocol_hash` exactly as in `plan.json`'s
`composed_config.computed_via` note; both are pure, offline, and read only committed config
fragments and the pinned split identity hash already on file in
`docs/readiness/2026-09-19-slurp-dev-2000-roster-v1.md`.
