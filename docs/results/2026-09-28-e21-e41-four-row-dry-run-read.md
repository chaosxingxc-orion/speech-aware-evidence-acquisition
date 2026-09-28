# 2026-09-28: item E41 four-row dry run, receipts-only read (form proof, PASS)

Item E41 (owner decisions 103 and 158) bounds the Perception note on the Earnings21 + ConEC system form with one
pin (`probes/e21_native_window_system_perception_v1.txt` -> `probes/e21_native_window_system_perception_v2.txt`);
package [`docs/readiness/2026-09-27-e21-native-window-e41-v1/`](../readiness/2026-09-27-e21-native-window-e41-v1/README.md).
This note records the dry run's read. It is a **form proof on 4 windows of one call: no effect, score, comparison or
benefit is claimed** (`stage3_measurement`: form-proof, rows 1, claims_benefit false).

## Gates

| gate | meaning | result | counts |
| --- | --- | --- | --- |
| R1 | recipe assertion R1 (no violations) | PASS | violations 0 |
| R2 | every window delivers non-empty (SHA-256 compare against the empty-string digest) | PASS | 4 / 4 windows delivered non-empty |
| R3 | Perception truncation rate, target zero (Reviewer count reported beside it) | PASS | Perception truncated 0 / 4; Reviewer truncated 0 / 8 |

Verdict: **PASS**. The Perception length-truncation mode is absent on this dry run, against 2 / 4 on the sealed E39b
dry run at the same 640 cap.

## Tables written by the driver (numbers only)

Per-role contacts (finish reason stop / length):

| role | this arm | E39b |
| --- | --- | --- |
| Perception | 4 (4 / 0) | 4 (2 / 2) |
| Planner | 8 (8 / 0) | 7 (7 / 0) |
| Reviewer | 8 (8 / 0) | 7 (7 / 0) |
| Solver | 8 (8 / 0) | 7 (7 / 0) |
| total | 28 | 25 |

- Terminal disposition: none / none on 4 of 4 episodes, this arm and E39b alike.
- Delivery: windows `4320211#w0001`..`#w0004` all delivered non-empty, each with a normaliser receipt present.
- Budget: 28 generation calls (ceiling 44), 2,520.0 repeated speech seconds (ceiling 3,960); within ceilings.
- Perception completion tokens: min 74, p50 85.5, max 137 (cap 640; E41 worst-case bound 574); all 4 notes within
  the E41 bound (at most 5 lines, 20 words per line, 2 readings per line, 4 quoted words per reading).
- Planner routes: ACCEPT 4, REVISE 4; REVISE second pass byte-identical Solver response hash on 1 of 4.
- Solver completion tokens (n 8): min 269, p50 270.0, max 283.
- Abort and recovery history: empty.

## Identity

- Run `SAEA-E21-NATIVE-WINDOW-SYSTEM-FOUR-ROW-E41-V1`, attempt `attempt-e21-native-window-system-four-row-e41-v1`;
  manifest status COMPLETED, study commit `cb628f592934921a48102a5451ce1dd2f5c0fc98`, study-repo dirt empty;
  profile `bounded-discovery-probe`, split role discovery, split identity
  `4d9ea907c05b67c43b5829e3e6c379ee37d39df012028a864aa0cdb7ae0c1992`, protocol
  `b1e88eaa78bf7719be5964f8859f8a37515e69c723e21379f00f5112d0744651`, config
  `92d9644817e1c9d9640b015f0a9d999c502c91f2fbe08c4c72a4980eebf87c0a`.
- Sealed files (SHA-256), under `$SPEECHRL_DATA_DIR/runs/SAEA-E21-NATIVE-WINDOW-SYSTEM-FOUR-ROW-E41-V1/attempt-e21-native-window-system-four-row-e41-v1/`:
  - run manifest `f59abbdeb5b429f38e359b740c84443cef2736547f73433c31c492595b0d36c6`
  - generation manifest `79f6fd3a4bc1b3aeb7e652ea663da519bdeab3629814bfc982072ba9cc4d7e0e`
  - trace manifest `cf5626e5aaeb1e5d2e8e8e54942ec7f27936632cde7a34db9499c6489141e692`
  - raw trace `32c75f0cb17efca25699086b8897eadb9f2b3e97f0e5b9f04226de4214bdbbba`
  - outputs `7725cc7470b0bf30a6396e93f2413ea4ff89d8f1b049af3b8fdd3fd0bd9994d8`
  - flight receipts `d9726d6587802d07d5a52497e255a69cfb5b235e3ab38caeef68c1d3b1a716b7`
- Recipe `e21-native-window-e41-dry-run-receipts-read-v1`
  (`docs/readiness/2026-09-27-e21-native-window-e41-v1/dry-run-analysis-recipe-v1.json`, sha256
  `519d75449f9489378b2aa0f5736071148dfdf85cf76e40025f8eb2bf4e5ca5ad`).
- Driver `scripts/analysis/e21_e41_dry_run_read.py`, sha256
  `147457b3e11c58825e9a29b0efb4052182c69bf3db40abc6e50742bf64b2fc0f`, run exactly as its README states
  (`--repo-root` the read worktree, `--data-root` `$SPEECHRL_DATA_DIR`); exit 0.
- Analysis root `$SPEECHRL_DATA_DIR/analysis/SAEA-E21-NATIVE-WINDOW-SYSTEM-FOUR-ROW-E41-V1-READ-V1/`: `read.json`
  sha256 `fda35b3ced5a9c7dbaf5ded47cbf640cd7158ab1d301a8b45887f4165d544e71`, `read.md` sha256
  `8e0df3e44075ae8ed4d3e8298522a68ac2ef1a7666a011293cfeef52895947bf`.
- Read row `SAEA-E21-NATIVE-WINDOW-SYSTEM-FOUR-ROW-E41-V1-READ-V1` in `docs/exposure-ledger.md` (model-free); its
  description of "sealed per-sample official scores" now carries a dated correction clause (receipt fields only).

## Contacts and GPU time

From the batch driver log `/home/chao/batch-campaign-1-e41dry-20260928T004134Z.log` (status lines only) and the
manifest cost block:
- 28 model responses logged between 00:41:49 and 00:44:02 UTC on 2026-09-28 (about 2 min 13 s wall).
- Final campaign status line (`saea-campaign-status-v1`): completed = [this run], state `scored`, pending none.
- Manifest cost: 28 calls, 2,520.0 speech seconds, 88.31 s total model latency, 67,328 prompt and 4,962 completion
  tokens (planned: 44 calls, 0.5 GPU-h).

## Comparators read (structurally, never re-scored or re-flown)

- Sealed E39b dry run `SAEA-E21-NATIVE-WINDOW-SYSTEM-FOUR-ROW-E39B-V1`
  (`attempt-e21-native-window-system-four-row-e39b-v1`): role and finish-reason tables above.
- Sealed E35 four-row DIRECT arm `SAEA-E21-NATIVE-WINDOW-DIRECT-FOUR-ROW-V1`
  (`attempt-e21-native-window-direct-four-row-v1`): used only for the note's window-transcript 4-gram re-emission
  feature.

## Next: E41 sub10 (E-C0)

Per the package README step 5, and only on this PASS:
1. Root fills the `dry_run_read` antecedent of
   `docs/readiness/2026-09-27-e21-native-window-e41-v1/root-admission-draft-sub10-v1.json` with this note's committed
   path and SHA-256 (the mint tool refuses while it is a placeholder).
2. Countersign the sub10 exposure rows, then mint `python scripts/flights/e41/e41_mint_receipt.py --which sub10`
   (decision `e21-native-window-e41-sub10-admission-v1`).
3. Flip with `bash scripts/flights/e41/e41_flip_sub10.sh`.
4. Fly with `bash scripts/flights/e41/batch_chain_e41_sub10.sh` on the E21 serving session only (SLURP session
   stopped): run `SAEA-E21-NATIVE-WINDOW-SYSTEM-SUB10-E41-V1`, 10 calls / 342 windows, 3,762 calls, 334,477 repeated
   speech seconds, 12.0 GPU-h. COMP-1 is still flying, so the E21 serving switch waits for its seal.
5. Read by `sub10-analysis-recipe-v1.json` (descriptive S1-S5 plus the standard scorer and agentic metrics against the
   sealed E35 sub10 direct arm bound per window; no claim), then return the SLURP geometry.
