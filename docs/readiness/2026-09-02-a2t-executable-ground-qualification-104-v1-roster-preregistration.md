# A2T Executable Ground Qualification 104 V1 Roster Preregistration

## Purpose

Freeze an identity-only approximately-104 discovery roster for the first executable-ground
qualification. The roster opens new model contacts later, but it opens no new carrier population:
every item is drawn from the already-registered and already-exposed Audio2Tool parent 400. This
protects the separate proposed 400-item unexposed evaluation tier for a later frozen-method read.

Experiment id: `SAEA-A2T-MF-EXECUTABLE-GROUND-QUALIFICATION-104-V1-ROSTER`.

## Pinned inputs

- parent receipt `docs/receipts/probe-samples/r1-audio2tool-sample.json`, SHA-256
  `d99570a797744f7dc3db53bdb898611836ae2682a02e726b974d05734c6cbb2d`, split identity
  `e1d751e6c76e49d087620842ba17c34e432a4602169dc2b93ee7e0a529ca332c`;
- excluded G1 receipt `docs/receipts/a2t/A2T-G1-104.json`, SHA-256
  `b42f0953a0d168955ba5ddfc77f2c300aacb54e48dce902d1b3d4a109c1996db`;
- excluded CPV2 receipt `docs/receipts/a2t/A2T-CPV2-104.json`, SHA-256
  `8f47922124c61f92fee03273c1165eb1f8f97048d910ddd4a6a7243906d78783`.

The G1 and CPV2 receipts each contain 13 items per tier and are already query-block-disjoint. The
selector excludes every complete query block named by either receipt before ranking candidates.

## Frozen selection rule

Use namespace `a2t-executable-ground-qualification-v1`. Accept only the runtime-legal candidate
fields `sample_id`, `tier`, `media_relpath`, `audio_seconds`, and `audio_sha256`. For each of the
eight canonical tiers:

1. discard every item whose tier-scoped query block appears in G1 or CPV2;
2. retain at most one item per query block;
3. rank by SHA-256 of `namespace + NUL + sample_id`, breaking ties by `sample_id`;
4. take the first 13 items.

Sort the final 104 items by `(tier, sample_id)`. The output is
`docs/receipts/a2t/A2T-GROUND-QUAL-104.json` and is exclusive-create. A reversed-parent rebuild must
produce the same selected identities and receipt bytes after the materialization commit field is
held constant.

Selection must stop unless it proves:

- exactly 13 items in each of eight tiers and 104 items total;
- 104 unique sample identities and 104 unique query blocks;
- zero sample or query-block overlap with G1 and CPV2;
- every selected item belongs to the parent 400 and its media path, duration, WAV header, and
  SHA-256 match the runtime loader;
- no query text, expected call, gold, prior output, prior score, reward, or test annotation is
  accepted by the selector or written to the receipt.

The parent A0 outputs and scores are inherited exposure, but neither may be opened by this run. The
selection namespace, allocation, exclusion set, and order are fixed independently of any result.

## Contact and scope boundary

Arm the offline connection guard before opening inputs. Frozen-core, tokenizer, retriever,
embedding, HTTP/socket, external-network, audio-decoder, GPU, scorer, gold, and test contacts are
all zero. Reading local WAV headers and hashing frozen audio bytes are identity checks, not speech
decoding or model contact.

Passing authorizes only separately preregistered label-free speech-packet preprocessing and the
ground-qualification implementation. It does not authorize a qualification model flight by itself,
candidate pruning, training-free policy fitting, the proposed unexposed 400, approximately-1,000
scale, baseline change, test access, Stage-3 work, or a superiority claim.

## Engineering scope

Later qualification scoring remains one unchanged official single-process operation per complete
manifest. Independent complete manifests may run concurrently through outer workers. Dataset
sharding and shard-score averaging are forbidden. Network-jitter testing remains out of scope.
