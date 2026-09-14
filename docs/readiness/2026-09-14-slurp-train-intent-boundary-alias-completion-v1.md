# SLURP TRAIN intent-boundary segment-alias completion

Status: **MODEL-FREE PREPARATION COMPLETE; NO EXPERIMENT ADMITTED**. This note supersedes the contract gap recorded in `2026-09-14-slurp-train-intent-boundary-alias-contract-gap-v1.md`. Root authorized the reusable format extension after confirming that the shared runtime already consumes `sealed-segment-vectors` query sources.

## Shared contract

`core.preparation_vectors` now accepts the explicit schema `saea-sealed-segment-vector-dimension-alias-v1` only when `source.kind` is exactly `sealed-segment-vectors`. It validates both source and export with the existing strict segment loader and uses the existing preparation lock and immutable receipt path. It preserves each outer ID, audio SHA-256, source frame count, sample rate, segment ID, frame range, row order, segment order, and numeric component. Only the per-segment vector key changes from `content` to `intent-boundary`. The existing flat `saea-sealed-vector-dimension-alias-v1` schema retains its prior config and export shape; the code does not infer either schema.

The final implementation SHA-256 is `c05303189d5139fb8f7fcf0b5d6dd5f28dd69191081e7dcc3b5bd37164c633cb`. Sixteen focused tests passed, covering flat cold/warm behavior, one and multiple segments, complete metadata preservation, unknown and mixed dimensions, wrong pins, duplicate row and segment IDs, changed warm exports, and the explicit segmented schema and source kind.

## TRAIN artifacts

| Fold | Config SHA-256 | Source SHA-256 | Export SHA-256 | Receipt SHA-256 | Rows / segments |
| --- | --- | --- | --- | --- | --- |
| TRAIN-A | `81f9140b54a055b2193f1a8fcda5d542078199173b68d484dcfbc0cec1a13a37` | `cff97de32d373c318b9c73f703d6ddf173f5150697fc1e25851e8d13cb6ec1f6` | `e7a5b2264dc61fcab3c63d50fb645d4629d3f0a99f83ad5fbe323c73884e5f0b` | `c1aaf37a678240633078a8fcca455f949a5c4b2b18d37356129976006c9dc138` | 1,080 / 1,080 |
| TRAIN-B | `01e541cd3d6ca46b487b55d958f2aea801838bb50bcf9850145ea6aece60e894` | `9f095cee1ee9a138092d4549d9afa648a2dc158e33c24b858859c62d5a5a9a89` | `83c5da6190fb2a65edf98a8f9ef35ff2cb310eb4e4b94eba9e04f9eedce9f299` | `78de8aa2d30afab442d286b1a14919e1dfc031f79b007f62b3eebd747a9d0ea0` | 1,080 / 1,080 |

The exports are respectively `vectors/slurp-intent-boundaries-train-fold-a-1080-v1/query-vectors-speech-segments.jsonl` and the fold-B sibling under `SPEECHRL_DATA_DIR`. Their immutable receipts are under `prepared/SAEA-SLURP-INTENT-BOUNDARY-TRAIN-FOLD-{A,B}-ALIAS-V1/query-dimension-alias.json`.

Cold preparation and immediate warm reuse both passed for each fold. A separate structural comparison confirmed identical outer metadata, segment metadata, numeric vectors, IDs, and order except for the declared dimension key. The A/B ID sets are disjoint. Each receipt records zero encoder, tokenizer, and model contacts, `values_unchanged=true`, and `max_absolute_delta=0.0`.

The configs pin the existing SEALED source preparation receipt, the corresponding committed TRAIN dataset config, and the shared A/B-excluded knowledge build receipt. No audio, transcript, label, gold, knowledge value, scorer, model, tokenizer, encoder, backend, GPU, network, or task-quality source was read or contacted during this derivative preparation. These aliases create no capability or experiment admission; root retains the decision to bind them to any later registered optimization.
