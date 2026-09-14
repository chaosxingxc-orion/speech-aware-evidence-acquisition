# SLURP TRAIN intent-boundary alias contract gap

Status: **BLOCKED BY THE SHARED INPUT CONTRACT**. This was a bounded CPU-only source and interface check at canonical base `b8a328ea1ac21b4d02eab0bdb06782c57fe2e6a7`. No task quality, gold, transcript, knowledge value, audio, model, encoder, tokenizer, GPU, scorer, network, or experiment contact was read or made. No preparation config, DATA alias, DATA receipt, or experiment admission was created.

## Verified source pins

The two existing speech-query preparations are complete and usable through the registered segment-vector consumer:

| Fold | Dataset config SHA-256 | Sealed preparation receipt SHA-256 | Query rows SHA-256 | Index SHA-256 | Verified shape |
| --- | --- | --- | --- | --- | --- |
| TRAIN-A | `4ba55688e80d8d768ec6cfc3ff4bacc9802fb34e4dab54913934015184497215` | `81fa1d2d12ef1aa2c29099ce0710d8f9f07edc47999b17244574dd940b10fd3f` | `cff97de32d373c318b9c73f703d6ddf173f5150697fc1e25851e8d13cb6ec1f6` | `266206b9f4f83ca79818e5defab8ffc60f6d438a518e9624f14ccac2b7c12287` | 1,080 roster-ordered rows; one 2,048-wide `content` segment per row |
| TRAIN-B | `1d30c501612686004936b5dd295885d9452175e6449b4a66187c08227a322cea` | `583d37669b3a8275be6a244454e21ebd7b5fbe1fd90af2b73f251d86bf7d00eb` | `9f095cee1ee9a138092d4549d9afa648a2dc158e33c24b858859c62d5a5a9a89` | `668029fd0d56839374975d56ec7aa300bc880cdb3784e27e0bbe58b42d0f5560` | 1,080 roster-ordered rows; one 2,048-wide `content` segment per row |

The receipts at `preparation-runs/SAEA-SLURP-TFRL-FOLD-{A,B}-SPEECH-QUERY-ENCODING-V1/encode-v1/receipt.json` report schema `saea-speech-query-preparation-receipt-v1`, status `SEALED`, the exact run/attempt identity, and the query-row hashes above. The shared `load_sealed_segment_vectors` reader accepted both files with dimension `content`; their ordered IDs equal the corresponding committed dataset roster order, and the A/B ID sets are disjoint.

The independently prepared knowledge source remains the existing A/B-excluded compact snapshot at `knowledge/slurp/saea-kb-distmodel-v1/size-full-content-slot-fillers-intent-slot-frame-tfrl-folds-v1/snapshot.json`, file SHA-256 `f2785aa3521b08e874d4075154e65cc639284497afc789a3654c2c70a65405ef`, runtime content SHA-256 `9c64e8ec48a0fce4f172bd190932f99c98c7efa18bbfb14526d54c62fdf7032b`, and repository build-receipt SHA-256 `5db718d38426e5e6d2311efbed0c4faf36bf30473c8d00b14e06618257889766`. This check did not open its values.

## Why the registered alias entry cannot run

`core.preparation_vectors.prepare_vector_dimension_alias` is the exact shared entry used for DEV1000. Its source contract calls `load_sealed_vectors` and requires every JSONL row to contain exactly `id` and `vectors`, with the declared source dimension directly under `vectors`. DEV1000 satisfies that flat schema.

The TRAIN outputs use the different registered `saea-speech-query-segment-vectors-v1` schema. Every row contains `id`, `audio_sha256`, `source_frames`, `source_sample_rate_hz`, and `segments`; the `content` vector is nested in each segment. Both TRAIN files therefore fail the flat loader with its required row-shape error. The alias entry has no source-kind switch and no segment-vector branch. `expected_rows`, `vector_width`, and `target_dimension` cannot change that schema mismatch.

Although these short-utterance folds currently have one segment per row, flattening them would create a new derivative and custody rule that the generic entry does not define. Writing an ad hoc flat export, private converter, or misleading config would bypass the requested shared contract. For the same reason, cold creation and warm reuse of TRAIN intent-boundary aliases cannot be verified in this task.

## Required shared resolution

Before these aliases can be prepared, the shared dimension-alias contract must explicitly support sealed segment-query rows while preserving the complete outer source fields, segment IDs and frame ranges, row/segment order, numeric components, source and output hashes, and zero-contact accounting. That capability needs a shared implementation and tests, then two minimal configs pinned to the sealed receipts above and separate DATA output/receipt paths. This task does not authorize that source change, so it stops here without creating partial artifacts.
