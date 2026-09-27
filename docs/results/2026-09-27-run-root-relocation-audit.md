# Run-root relocation audit (owner decision 148(b)): CONFLICT -- the run root does not move

Date: 2026-09-27. Author: Fable 5.1 (root coordinator), from the audit agent's inventory at master
`1df49946`. Model-free: zero model, server, encoder and scorer contacts; no file under `src/` changed.

## Verdict

**The run root cannot move from `$SPEECHRL_DATA_DIR/runs` to ext4 without weakening an enforcement
point or breaking cited hashes.** Decision 148(b) says "if none conflicts, adjust"; three conflict, so the
move waits. The standing rule that only `mlruns` lives on ext4 stands unamended.

## The three conflicts

1. **Sealed manifests bind absolute artifact paths and `verify_bundle` confines to the manifest's own
   directory.** `core/bundle/manifest.py:41` records `str(Path(path).resolve())`;
   `core/bundle/verify.py:69-77` passes `confine_to=run_dir_resolved` (the manifest's own
   directory) into `_verify_artifact` (`core/bundle/artifacts.py:42`), which refuses any
   outputs / raw_trace / trace_manifest / scores path not strictly under it. Confirmed on the sealed ROLL-2
   manifest (lines 38, 57, 67, 1168 all absolute under `/mnt/e/.../runs/`). A bundle sealed on ext4 and
   synced byte-identically to E: fails `verify_bundle` on the archive; rewriting the paths makes it pass
   but changes `manifest_sha256`, which is cited in 371 docs files, 101 configs, 72 scripts and 65 tests.
   The seal profile had to verify "the path-rewritten generation manifest"
   (`scripts/analysis/slurp_seal_path_profile.py:483,676`) for exactly this reason.
2. **`persist_flight_receipts` positively confines `flight-receipts.json` to `$SPEECHRL_DATA_DIR/runs`**
   (`core/flight/receipts.py:203-209`, "flight receipt path escapes the governed runs directory").
3. **The bundle is not immutable at the seal.** Deferred scoring (`core/flight/scoring.py:54` -> score
   worker -> `finalize_bundle`) rewrites the manifest afterwards through `_attach_scores`
   (`core/bundle/manifest.py:336-342`, absolute `scores.path`) and writes `scores.json` / `ledger-row.*`
   beside it, so a post-seal archive diverges from the run root. The batch driver's inspect step
   (`scripts/flights/batch/batch_inspect.py:57`, `continuation_status.py:113`) reads `$DATA/runs/...` and
   follows the manifest's absolute paths verbatim.

## Inventory (place / resolves through the data root? / conflict if runs move alone?)

| place | resolution | conflict |
| --- | --- | --- |
| `core/flight/runtime.py:1558,1573` `_run_dir`, predecessor dir (E10) | `data_root/runs/<run>/<attempt>` | switchable |
| `core/flight/resume.py:258` predecessor trace (E10/I7r) | sibling of `_run_dir` | switchable |
| `core/bundle/manifest.py:41,281,341` artifact and `attempt.state_path` | absolute paths baked in | **yes (1)** |
| `core/bundle/artifacts.py:42` `verify_bundle` confinement | manifest's own directory | **yes -- would be weakened** |
| `core/bundle/finalize.py:164-200` scores, ledger rows, `_attach_scores` | manifest's directory, post-seal rewrite | **yes (3)** |
| `core/flight/receipts.py:203` `persist_flight_receipts` | `data_root/runs` positive guard | **yes (2)** |
| `core/flight/scoring.py:180`, `core/scoring_batch.py:197` score jobs | absolute manifest path in `score-jobs.jsonl` | archive copy would point at ext4 |
| `core/flight_lock.py`, `scripts/lib/flight_lock.sh`, `core/flight/lease.py:28` | `data_root/locks` | no |
| `core/flight/campaign.py:139-152` readiness receipts | `prepared/` under the data root | no |
| `core/flight/coordinator.py:180,259` subprocess env | forwards `SPEECHRL_DATA_DIR` only | a new variable would need forwarding |
| `core/session/serving.py:224`, `core/session/receipt.py:246` | data root | no |
| `runtime.py:3504,10178` live-speech `prepared/`; `runtime.py:11001` wire-check | data root | no |
| `scripts/checks/derived_media_confinement_check.py`, `core/base.py:891` | `derived/` under the data root | no (runs are not derived media) |
| `scripts/checks/results_ledger_check.py` | reads no data root | no |
| `scripts/flights/batch/batch_inspect.py:57`, `continuation_status.py:113` | `$DATA/runs` + absolute manifest paths | **yes**, and frozen while a flight runs |
| `scripts/run_arm_sequence.sh:264` `--run-dir` | `$SPEECHRL_DATA_DIR/runs/$run_id` literal | legacy launcher |
| ~90 analysis and read recipes | `data_root/runs/...` or `"relpath": "runs/..."` | resolve only through a complete archive |
| string-pinned receipts | 429 docs files and 11 configs pin `speechrl-data/runs/` literally; 123 `"relpath": "runs/"` pins | resolve only on E: |
| umbrella `wiki/Data-and-Assets.md:14`, `docs/data.md:17`, `docs/setup.md:38` | "ext4 holds only the MLflow store" | policy text; owner amendment only |

## What recovers the tax instead

The profile (`docs/results/2026-09-26-slurp-seal-path-profile.md`) attributes 355.6 s per flight to the
per-record open/append/close in `TraceSink.emit` and 14.6 s per seal to the 8 KiB-buffer line scan in
`read_attempt_trace_facts`; both are recovered on the mount by the two code fixes on `fable/tracefix`
(decision 148(a)), leaving about 6.7 s per seal attributable to the mount itself. If relocation is ever
wanted, its precondition is a manifest schema change -- run-dir-relative artifact paths (or a recorded
`run_root` plus relative paths) with `verify_bundle` confining by relative path -- a new manifest schema
version with a migration for the cited hashes, not a switch.

## Gates

`bash scripts/flights/batch/main_gates_generic.sh` at master `1df49946`: all seven exit 0.
