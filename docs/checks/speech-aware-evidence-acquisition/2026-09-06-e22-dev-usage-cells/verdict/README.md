# The paired verdict of the Earnings-22 model-usage cells (a) and (b)

Row `SAEA-E22-MF-USAGE-CELLS-VERDICT-V1` (`model-free-check`), registered before the first sealed
score file was read. **Zero contacts of every kind** — model, tokenizer, embedder, retriever,
network, GPU, audio decode — with `analysis.dev100_reviewer_audit.arm_offline_guard()` armed before
the first input is opened and its recorded outbound-attempt count written into `summary.json`.

Section 4 of `docs/readiness/2026-09-06-e22-dev-usage-cells-v1-preregistration.md` fixed a decision
rule before either cell existed, and section 7.5 assigns its application to a later document. Both
flight rows published raw numbers only and said in writing that "the paired contrast, its
call-stratified CI90 and the preregistered decision rule are a LATER document's". These are that
document's receipts; the document is
`docs/readiness/2026-09-06-e22-dev-usage-cells-v1-verdict.md`.

| path | what it pins |
|---|---|
| `summary.json` | the identity gate, both pooled contrasts with both intervals, the preregistered decision per cell, the per-call and duration tables, the category masses before and after with the boundary block, and the cell (b) prediction check |
| `per-call-table.csv` | the ten-call table as a rectangle — identifiers and numbers only, no dev sentence text |
| `MANIFEST.sha256` | the byte hashes of this directory |

**Inputs, all sealed or committed.** The three finalize `<run_id>.scores.json` per-sample blocks
(arm A restricted to the 1,500 roster ids, cell (a), cell (b)); the two verified
`score-batch-per-sample` score files, cross-checked row for row against those blocks; the three
sealed `<run_id>.outputs.jsonl`; the hash-pinned dev10 reference layer and dev10 segment table, both
re-hashed on load; `docs/receipts/rosters/e22-dev-esb-1500-v1.json`; and the committed
`caps-1500.json` of the cell (b) flight receipt.

**The identity gate runs before any contrast.** Six hard-coded raw pairs — 17.4012 / 1.9161 for arm
A on these 1,500 rows, 16.9708 / 1.8552 for cell (a), 17.2603 / 1.9009 for cell (b) — must
reproduce from the sealed per-sample rows and from `analysis.e22_error_taxonomy` at its committed
version, or `build_receipts` raises and writes nothing.

**Byte-deterministic**: two back-to-back writes reproduce the same `MANIFEST.sha256`.

**The six calibration-exposed ESB test calls were not opened** (`test_split_read: false`): the
reference loader is pinned to the dev10 receipt alone and the segment-table loader to the dev10
extracted table, so no test reference, segment table or sealed test output is reachable from the
runner. The 109 confirmatory Earnings-22 calls are not named, loaded or read.

Module `src/speech_aware_evidence_acquisition/analysis/e22_usage_cells.py`; runner
`scripts/e22_usage_cells_read.py`; tests `tests/unit/test_e22_usage_cells.py`.
