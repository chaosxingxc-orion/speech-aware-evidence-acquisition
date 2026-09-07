# The paired verdict of the three Earnings-22 short-clip encoding probe cells

Row `SAEA-E22-MF-ENCODING-PROBES-VERDICT-V1` (`model-free-check`), registered before the first
sealed score file was read. **Zero contacts of every kind** — model, tokenizer, embedder,
retriever, network, GPU, audio decode — with `analysis.dev100_reviewer_audit.arm_offline_guard()`
armed before the first input is opened and its recorded outbound-attempt count written into
`summary.json`. No media byte is opened and the coordinator's resident serving session is neither
started, stopped nor attached.

Section 4 of `docs/readiness/2026-09-07-e22-dev-encoding-probes-v1-preregistration.md` fixed a
three-clause decision rule before any of the three cells was flown, and each flight receipt says in
writing that "the paired contrast against the sealed comparator, its CI90 and the three-clause
decision rule of section 4 are a later document's". These are that document's receipts; the
document is `docs/readiness/2026-09-07-e22-dev-encoding-probes-v1-verdict.md`.

| path | what it pins |
|---|---|
| `summary.json` | the section 4.1 falsifier of each cell, the identity gate, all three pooled contrasts per cell with both intervals, the preregistered decision per cell, the two pairwise cost contrasts, the per-call and duration tables, the category masses before and after with the boundary block and its containment buckets, the head/tail asymmetry, the entity-inventory basis reconciliation, and cell 1's re-cut clips under 0.15 s by name |
| `per-call-table.csv` | the ten-call table as a rectangle — identifiers and numbers only, no dev sentence text |
| `MANIFEST.sha256` | the byte hashes of this directory |

**Inputs, all sealed or committed.** The four finalize `<run_id>.scores.json` per-sample blocks
(arm A restricted to the 1,500 roster ids, and the three cells); the three cells' verified
`score-batch` score files, cross-checked row for row against those blocks (1,500 rows each, zero
disagreements); the four sealed `<run_id>.outputs.jsonl`; the hash-pinned dev10 reference layer and
dev10 segment table, both re-hashed on load; `docs/receipts/rosters/e22-dev-esb-1500-v1.json`; the
three committed variant roster receipts under `2026-09-07-e22-dev1500-encoding-variants/`
(identifiers, durations, sample counts and token counts only); the three committed flight
`falsifier.json` receipts; and the committed `2026-09-07-e22-short-clip-encoding-audit/summary.json`
for the comparator's own audio-token cost.

**The section 4.1 falsifier runs before any score is opened.** Section 6.2 item 7 puts it there, so
each cell's committed falsifier receipt is re-read and re-hashed first and the verdict refuses
unless all three report `HOLDS` on 1,500 of 1,500 rows with matching `prompt_tokens` totals
(210,663 / 251,782 / 678,026).

**The identity gate runs before any contrast.** Four hard-coded raw triples — corpus WER, agentic
error rate and boundary block in WER points — 17.4012 / 1.9161 / 8.2778 for arm A on these 1,500
rows, 14.3537 / 1.8971 / 5.4969 for cell 1, 9.4054 / 1.7599 / 1.1085 for cell 2, 9.3254 / 1.7752 /
0.9295 for cell 3, must reproduce from the sealed per-sample rows and from
`analysis.e22_error_taxonomy` at its committed version, or `build_receipts` raises and writes
nothing.

**The three flight receipts do not share one entity-inventory basis, and the receipt says so.** The
per-call entity inventory feeds `classify_span`, so it moves the agentic rate and, through
`runaway-head`, the boundary block. Arm A and cell 1 reproduce to the digit on the `dev10` basis;
cells 2 and 3 reproduce to the digit on `subset1500` and on nothing else. Every arm is therefore
scanned on both, the gate checks each receipt against the basis it used, and **every contrast is
computed on the comparator's `dev10` basis for all four arms** — the `entity_inventory_basis` block
carries both numbers for every arm. Corpus WER is unaffected: it comes from the scorer.

**Byte-deterministic**: two back-to-back writes reproduce the same `MANIFEST.sha256`.

**The six calibration-exposed ESB test calls were not opened** (`test_split_read: false`): the
reference loader is pinned to the dev10 receipt alone and the segment-table loader to the dev10
extracted table, so no test reference, segment table, derived clip or sealed test output is
reachable from the runner. The 109 confirmatory Earnings-22 calls are not named, loaded or read.

Module `src/speech_aware_evidence_acquisition/analysis/e22_encoding_probes.py` (a thin derivation
over the base `analysis/e22_usage_cells.py`); runner `scripts/e22_encoding_probes_read.py`; tests
`tests/unit/test_e22_encoding_probes.py` and `tests/unit/test_e22_usage_cells.py`.
