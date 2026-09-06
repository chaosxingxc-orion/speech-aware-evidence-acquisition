# SAEA-E21-MF-AGENTIC-METRIC-BASELINE-V1 — receipts

The Earnings-21 comparator every mechanism cell pairs against from now on, re-scored from the sealed
full-44 direct baseline's own bytes under the 2026-09-06 agentic metrics. Note:
`docs/readiness/2026-09-06-earnings-agentic-metric-baseline-v1.md`. Literature (what ConEC publishes
and what its scorer actually computes): `docs/readiness/2026-09-06-earnings-agentic-metric-literature.md`.

**Zero model, GPU, tool, embedding, network and audio contact**, and no Earnings-22 read. The ledger
row was registered and committed before the first scorer touched a reference. Source:
`SAEA-E21-FULL44-DIRECT-BASELINE-V2`, attempt `attempt-20260904T233816Z-bcd338`, study commit
`44db2e9d` — all 44 `earnings21-original` discovery calls, 39.263 h, split identity `fcc1b0bc…d69e`.

**The identity anchor holds to the digit.** The re-scored `asr-wer-whisper` job reproduces the sealed
2026-09-04 read exactly: corpus **8.200 %** (S 13,098 / D 5,701 / I 10,700 over 359,765 reference
words) and **all 44 per-call rows with zero mismatches**. Independently, the ConEC mirror's own
`__ALL__` bucket — built by a different function over the same normalized sequences — lands on the
same 8.200 %.

| file | what it holds |
|---|---|
| `scoring/rescore-bundles.json` | the three re-scoring bundles: per metric, each sealed artifact's path, its copy's path, and the sha256 they share. The copies are byte-identical and each manifest differs from the sealed one **only** in artifact paths and the `scorers` list, so `core.bundle.verify_bundle` re-derives every hash and cross-check (split identity, protocol hash, outputs↔split↔trace binding) and gets the sealed values. The sealed attempt directory was never written to. |
| `scoring/jobs.jsonl`, `scoring/batch-summary.json` | the `core.scoring_batch` job table and summary: 3 of 3 succeeded, one complete verified manifest per process, `max_workers` 1, never sharded. 647.4 s / 528.6 s / 5.8 s. |
| `scoring/verified-score-read.json` | the three `verified: true` reads. Per-sample `ref_hit_mask` arrays dropped for size (the same reduction the 2026-09-04 receipt made); every count verbatim; the unreduced files' sha256s are in `verdict/result-summary.json`'s `jobs` block. |
| `verdict/result-summary.json` | the identity anchor with its per-call mismatch list, the three metrics on all 44 and on the E5 split (34 kb-construction vs the r4 ten evaluation calls), ConEC Table 2's published columns beside the eight classes it publishes, all 30 observed classes, the numeric `by_kind` block, and the ConEC scorer's provenance block (`official_tool_run: false`). |
| `verdict/per-call-table.md` | all 44 calls with their roster label, corpus WER, ConEC entity WER over the eight published classes, numeric-value accuracy, and the label-transfer residue. |

`semantic-high-impact-error-rate-v1` is registered and tested but produces **no Earnings-21 value
here**: its taxonomy is the Earnings-22 semantic scan's deliverable and has not landed. The scorer
fails closed by name until `docs/taxonomies/semantic-high-impact/ACTIVE.json` exists.
