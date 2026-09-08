# `SAEA-E21-FULL44-NULL-REPLICATE-V1` — Earnings-21's own greedy replicate null

The cell of `docs/readiness/2026-09-08-e21-own-null-replicate-v1-preregistration.md`: the sealed
full-44 direct baseline flown a second time under its **exact** configuration, so this carrier
finally measures its own replicate noise instead of importing Earnings-22's half-width.
Owner Decision 8 of 2026-09-08; named in advance by section 3 of the cross-carrier silence-tail
preregistration and again by section 10 item 1 of the tail-cell verdict.

**There is no ADMITTED / NOT-ADMITTED verdict.** The cell has no factor: it is the same request,
twice. Its output is a table of intervals. The full reasoning is
`docs/readiness/2026-09-08-e21-own-null-replicate-v1-verdict.md`.

| | |
|---|---|
| study commit | `839a73e5` (registration) — the flight binds it, `study_repo_dirt` empty |
| flight | attempt `attempt-20260908T113102Z-bdde07`, 1,593 windows over 44 calls, one attempt, no recovery |
| comparator | `SAEA-E21-FULL44-DIRECT-BASELINE-V2`, attempt `attempt-20260904T233816Z-bcd338` |
| identity | config `e4b133d1…`, protocol `06f7f308…`, split `fcc1b0bc…` — **the comparator's own three** |
| falsifier | **1,593 of 1,593** slices byte-identical to the comparator's; prompt tokens 1,935,965 on both arms |
| corpus WER | 8.19952 % -> **8.17951 %**, paired **−0.02001** [−0.08502, +0.03085] call-clustered |
| text identity | **33.90 %** of windows byte-identical; 0 of 44 calls fully identical |
| saturation | **0** windows, as the comparator |
| serving | attached to the coordinator's resident session `e21-np6-c36864-20260908`; no server started, none stopped |
| cost | 1,593 calls of 1,750; 141,345.8527 metered speech seconds of 150,000; **1.0085 GPU-h of 1.2**; paid API spend 0 |

## The margins this cell puts in force

Section 4 of the preregistration fixed the rule before any number existed: the Earnings-21
non-inferiority margin per metric becomes the half-width of this null's own call-clustered CI90,
and a future cell demonstrates an effect only if its CI90 is **disjoint from this null's measured
interval**. These replace the imported Earnings-22 half-width of ±0.1524 for **Earnings-21 only**.

| metric | margin | null interval |
|---|---:|---|
| corpus WER / ConEC overall | **0.05793** | [−0.08502, +0.03085] |
| ConEC non-entity | **0.06475** | [−0.11375, +0.01575] |
| ConEC PERSON | **0.25009** | [−0.24338, +0.25680] |
| ConEC ORG | **0.35609** | [−0.44313, +0.26904] |
| numeric-value accuracy | **0.15651** | [−0.18758, +0.12543] |
| semantic high-impact rate | **0.00148** | [+0.00080, +0.00377] |

**The imported margin was wrong in both directions**: 2.6x too wide for corpus WER, 1.6x too narrow
for PERSON. And the semantic metric's null **excludes zero**, so it can never have carried a "does
not rise" clause on this carrier.

## Layout

| path | what |
|---|---|
| `flight/falsifier.json` | section 2: every emitted `SliceRecord` against the sealed comparator's own, field by field, plus the wire-level token and audio identity and the saturation covariate |
| `flight/flight-receipt.json` | the flight: identity anchor re-read from the sealed manifest, per-call window counts, token distribution, cost, throughput, the attached session and its monitor summary |
| `flight/rescore-bundles.json`, `flight/jobs.jsonl`, `flight/batch-summary.json` | the four post-hoc agentic-metric bundles and the `core.scoring_batch` job table: 4 of 4 succeeded, one complete verified manifest per process, `max_workers` 1, never sharded |
| `flight/verified-score-read.json` | the four `verified: true` reads, collapsed into one document. Per-sample `ref_hit_mask` arrays dropped for size (the same reduction the 2026-09-04 and 2026-09-06 Earnings receipts made); every count verbatim, and the unreduced files' sha256s are in its own `reduction` block |
| `verdict/result-summary.json` | the machine form: identity gate, the null table with every interval and half-width, the margin rule, per-call and per-stratum tables, the error structure, the window-level intervals, the text-identity section and the section-5 prediction check |
| `verdict/per-call-table.md` | all 44 calls with sector, sample rate, window count, reference words, both corpus-WER figures, both S/D/I triples and the per-call text-identity rate |

## The four things this receipt exists to pin

1. **The request side is provably unchanged.** 1,593 of 1,593 emitted slice SHA-256s, byte counts,
   spans, sample rates and parent hashes equal the sealed comparator's, `preprocess` is empty on
   both sides, and `prompt_tokens_total` is **1,935,965 on both arms**. Only the completions moved
   (439,532 -> 439,342). Checked **before any score file was opened**.
2. **The identity anchor held.** The cell introduced no config fragment; it composed the
   comparator's own four, and the sealed manifest carries the comparator's config hash, protocol
   hash and split identity to the digit. A one-character difference in any of the three was a
   preregistered STOP.
3. **The comparator reproduced its published anchors before a single contrast was computed** —
   corpus WER 8.19952, S/D/I 13,098 / 5,701 / 10,700 over 359,765 reference words, ConEC overall
   8.19952 and non-entity 4.73038, numeric accuracy 90.73351, semantic high-impact 0.02780 — and
   both arms' per-window rows re-aggregate to their own corpus totals exactly, 1,593 windows over
   44 calls, with 0 span misalignments.
4. **Scoring ran once over the complete manifest, never sharded**, on both the four declared
   scorers at finalize and the four post-hoc agentic bundles.

## Reproduction

All zero-contact; every one reads sealed artifacts only, opens no Earnings-22 surface, and touches
no model, GPU, tool, embedder or network.

```bash
# section 2's falsifier (must PASS before any score file is opened)
python scripts/e21_null_replicate_falsifier.py <attempt-dir> SAEA-E21-FULL44-NULL-REPLICATE-V1 1593 falsifier.json

# the four agentic metrics, post-hoc over complete verified manifests
python scripts/e21_null_replicate_rescore.py build <attempt-dir> SAEA-E21-FULL44-NULL-REPLICATE-V1 <work>
python scripts/e21_null_replicate_rescore.py score <work>
python scripts/e21_null_replicate_rescore.py read  <work> <work>/score-read.json

# the replicate's per-window rows (the comparator's are reused from the tail cell's own read
# and re-proved against the sealed anchors inside the paired read)
python scripts/build_e21_null_replicate_verdict.py --window-rows-only cell ...

# the paired read
python scripts/build_e21_null_replicate_verdict.py \
  --score-read <work>/score-read.json --attempt-dir <attempt-dir> \
  --comparator-window-rows <cache> --cell-window-rows <cache> \
  --falsifier falsifier.json --out result-summary.json

# the flight receipt
python scripts/e21_null_replicate_flight_receipt.py <attempt-dir> <run-id> <t0> <t1> falsifier.json out.json
```

`build_e21_null_replicate_verdict.py` imports `scripts/build_e21_tail2s_verdict.py` rather than
re-implementing it, so the null and the effects it will be compared against come out of **one**
instrument: the same identity gate, the same pooled ratios, the same
`analysis.paired.resampled_statistic` draws (10,000 replicates, seed 20260903, CI90) and the same
`analysis.e21_window_pairing` decomposition with its own byte-for-byte stitch proof.

Per-request outputs, traces, manifests, scores and the per-window row caches live under
`SPEECHRL_DATA_DIR/runs/SAEA-E21-FULL44-NULL-REPLICATE-V1/` and never enter Git.
