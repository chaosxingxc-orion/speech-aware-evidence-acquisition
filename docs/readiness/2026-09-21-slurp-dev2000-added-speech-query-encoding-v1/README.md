# SLURP DEV-2000-ADDED speech-query embedding preparation, v1

Registration only (owner decisions 34, 35, 76a, 78, 79). Modelled on the TRAIN fold A/B precedent
`docs/readiness/2026-09-12-slurp-training-query-embedding-preparation-v1.md` /
`docs/readiness/2026-09-12-slurp-training-query-embedding-registration-v1.json`. This package is
not an exposure registration by itself acting alone -- the corresponding ledger row still must be
appended and committed before any contact; see below. No model, tokenizer, encoder, network or GPU
contact was made while drafting it.

## What is bound

- Roster `SLURP-DEV-2000-ADDED-V1`, split identity
  `ee6c43cd4dd8fc2a583d2dd053e799c2d002efa3755fcd092ba7c7565431bf67`, 1,000 recordings,
  2,983.527 source seconds. Roster receipt `docs/receipts/rosters/slurp-dev-2000-added-v1.json`.
- Sources: unlike Fold A/B (which built a bespoke external `coordination/*-source-inventory-v3.json`
  because those TRAIN folds had no committed runtime view), this protocol points directly at the
  already-committed, already-hashed `configs/dataset/slurp-speech-native-dev2000-added.json`
  (`runtime_view_sha256` `6968a0564699968f1615bb98b45d2f0ccf179dd0a04351b2871bc096a9052477`).
- Encoder: the same frozen local `omni-embed-nemotron-3b` inventory Fold A/B pinned,
  `/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/coordination/a2t-speech-query-encoder-inventory-v2.json`,
  sha256 `1548387ba91209921fd747e9eff981027be618c618b732efe20ca7d43680bb31`, reverified without
  loading the model.
- Protocol: `configs/preparation/slurp-dev2000-added-speech-query-encoding-protocol-v1.json`, sha256
  `cb2d3b1e3ff1201577790d495724ea8a2a9a91d6931e059382349d72b759b402`. Preserves the shipped literal
  `query: ` prompt, complete audio, 2,048 dimensions, masked mean pooling, L2 normalization, batch
  size one, 120-second windows, 8-second overlap, an 8,192-token bound, a 1,920,000-sample bound,
  four CPU prefetch workers, ten-second monitoring, and the `fixed-stride-complete-final-tail-v1`
  boundary policy -- all unchanged from the Fold A/B protocol.
- Expected unique spans: **1,000** (one per recording). Mean duration 2,983.527s / 1,000 =
  2.984s, far below the 120s window, so every recording resolves to exactly one complete-tail
  window; this mirrors the Fold A/B precedent, whose `expected_unique_spans` (1,080) also equalled
  its source-utterance count for the identical reason.
- Own cache namespace `prepared/slurp-dev2000-added-speech-query-span-cache-v1`, separate from the
  TRAIN folds' shared `prepared/slurp-tfrl-speech-query-span-cache-v1` (devel, not TRAIN, data;
  never share a cache root across splits).

## Command

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<frozen-checkout>/src OMP_NUM_THREADS=1 \
python -m speech_aware_evidence_acquisition.core.speech_preparation_runtime \
  --config <external-runtime-config.json> \
  --config-sha256 <runtime-config-sha256> \
  --data-root /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data \
  --source-root <frozen-checkout>
```

`<external-runtime-config.json>` is built from `registration-v1.json`'s `plans[0].
runtime_config_shape` exactly as the Fold A/B precedent describes, with `study_head` replaced by
the final clean registration commit (the commit that carries this package's protocol and ledger
row). `run_preparation` supplies the `ExecutionPlan`, tool-plan gate, encoder-inventory
verification, `GenerationLease`, `AttemptStore`, before-forward accounting, immutable per-span
start markers, create-only index publication, query-row export, monitoring, and one-shot abort
semantics -- unchanged from the precedent. The encoder is an in-process local retrieval tool with
no endpoint; it must hold exclusive GPU custody without a resident answering server, so run it
after `SAEA-SN-DEV2000-ADDED-PREPROCESS` (packets) closes and the sidecar is stopped, and outside
any window a phase-program flight holds the GenerationLease.

## Outputs

`prepared/SAEA-SLURP-DEV2000-ADDED-SPEECH-QUERY-ENCODING-V1/index.json` and
`.../queries.jsonl`, matching the Fold A/B `output_relpath` / `query_rows_relpath` naming exactly.

## What cell B6 actually binds

Not this raw output directly. Following the Fold A/B dual-store precedent
(`docs/readiness/2026-09-14-slurp-native-dual-store-train-source-folds-held-v1.md`), a SEPARATE
zero-contact alias step must repackage the sealed `queries.jsonl` into
`vectors/slurp-dev2000-added-v1/query-vectors-speech-segments.jsonl`, with an alias receipt
recording row/segment counts, zero max delta, and zero model/tokenizer/encoder contacts. That alias
step is NOT registered by this package (it is zero-contact and only meaningful after the vectors
above are sealed); it is named as the third open item in
`docs/readiness/2026-09-21-slurp-b6-dev2000-added-preparation-plan-v1.md`.

## Ledger row

`SAEA-SLURP-DEV2000-ADDED-SPEECH-QUERY-ENCODING-V1`, tool-level encoder contacts only, 0 frozen-core
contacts, `consumed = no`, planned 1,000 calls / 2,984 speech-seconds / 2.0 GPU-hours. See
`registration-v1.json` `plans[0].ledger_row_cells` for the exact 15-cell row appended to
`docs/exposure-ledger.md`.
