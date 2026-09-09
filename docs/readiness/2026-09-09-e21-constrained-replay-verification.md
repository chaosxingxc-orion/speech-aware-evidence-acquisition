# E21 full constrained-delivery replay verification

Register a model-free engineering read of the original sealed KC-E1f full44 repair pass. The target is the complete 1,593 fixed windows and 44 stitched call outputs, not a four-row proof or a new DR generation.

Bind the original source:
- Run: SAEA-E21-KC-E1F-REPAIR-44-V1.
- Attempt: attempt-20260908T040832Z-ecda9c.
- Manifest SHA-256: eb9f86d3ea5a8f9fedb15d98374b019dac9fdc545792b77a935cff8f2380bcfc.
- Outputs SHA-256: 8bead60e0d5fc3476861f272aba04304afe6d18399407aff19a1224817f9317f.
- Trace SHA-256: 8b3d6c1540b7a7f1f03e6c4be48c1575b87151e18153107c03833b5e4ac0fdcf.
- Predecessor receipt: docs/receipts/e21-predecessor-full44-direct-baseline-v2.json, independently verify its bound digest.

Use the shared pure core.bundle.delivery_replay.replay_delivery and the registered e21-entity-repair-substitutions-v1 rule with the original 4 / 0.60 / 0.10 parameters. Resolve the historical composed model and baseline config from the verified parent. Preserve source bytes. This retrospective compatibility check does not add derivative declarations to the old experiment or fabricate a new generation manifest.

For every terminal window compare the replayed delivered-text hash against the exact historical obs_delivered_text bytes. For every call compare replayed stitched text byte for byte with the original sealed output. Retain terminal request ancestry, skip/saturation and fallback counters. Stop on any missing source, malformed record or mismatch and name the implementation boundary; do not silently skip rows or alter the old result.

Read no gold, reference transcript or new scoring result. Invoke no scorer, model, tokenizer, encoder, network service or GPU. Report source/implementation hashes, complete coverage, exact parity and any mismatch; store raw content only in existing data-root source artifacts. Passing proves legacy constrained delivery compatibility. It does not establish DR effectiveness, four future derivative scores, or current OpenJiuwen live execution. The approved DR successor still uses two generation groups and four predeclared deliveries.
