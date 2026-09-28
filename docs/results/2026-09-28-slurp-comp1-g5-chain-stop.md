# The COMP-1 + G5 chain STOP of 2026-09-28T03:28:18Z: the COMP-1 arm aborted on a cited-answer contract refusal after 1,913 calls; the smoke and the shared A/A sealed COMPLETED; G5 never started (OPERATIONAL RECORD)

Recorded 2026-09-28 by Claude Opus 5.5 (the merge and records agent, on master) from the batch driver's status
records only: `/home/chao/batch-status.jsonl.20260928T035054Z.bak` (the chain's status stream, moved aside when
the next chain started), `/home/chao/batch-STOP.20260928T035054Z.bak`, `/home/chao/batch-chain-comp1g5.out`,
`/home/chao/queue-e41-comp1.out`, `/home/chao/queue-comp1-wave.out` and `/home/chao/queue-wave-revtfrl.out`, the
exception line of the arm's campaign log `/home/chao/batch-campaign-1-comp1-20260928T004655Z.log`, and the run
manifests under `$SPEECHRL_DATA_DIR/runs/`. No trace, output or score content was read; no utterance text,
transcript, gold label or model output is quoted. This is an operational record: no score, no read, no verdict.

## 1. The chain

The COMP-1 + G5 chain (`batch-chain-comp1g5.out`) started 2026-09-28T00:45:20Z at flight commit
`cb628f592934921a48102a5451ce1dd2f5c0fc98` on session `serving-slurp-native-candidate-five-train-a-np4-v1`,
after the E41 four-row dry run returned 0 at 00:44:30Z and the serving swap back to the SLURP np4 geometry
exited 0 at 00:45:20Z. Its queue: step 1 `comp1` (the smoke, then the shared A/A and the COMP-1 arm), step 2
`g5` (the smoke, then the G5 arm).

## 2. Status lines (driver status stream)

| at (UTC) | event | detail |
| --- | --- | --- |
| 00:45:20 | driver-start | flight commit cb628f59 |
| 00:45:21 | step-start | step 1 `comp1`, cell `slurp-native-stage3-comp1-fold-a-v1` |
| 00:45:25 | registration-gate-ok, prelaunch-ok | step 1 |
| 00:46:45 | smoke-worker-exit rc 0; smoke-inspect pass | `SAEA-SLURP-STAGE3-COMP1-FOLD-A-SMOKE-4-V1`: manifest COMPLETED, 16 calls, 42.382 speech-audio seconds |
| 00:46:55 | arm-start | campaign log `batch-campaign-1-comp1-20260928T004655Z.log` |
| 03:28:18 | arm-exit rc 1 | step 1 |
| 03:28:18 | arm-inspect FAIL | no run manifest for `SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1` (attempt `attempt-slurp-native-stage3-comp1-fold-a-generation-v1`); attempt state ABORTED; 1,913 calls, 5,171.378 speech-audio seconds |
| 03:28:18 | STOP | "arm failed on step 1 (campaign rc 1, inspect rc 3)"; the chain's driver exited 9 |

The exception that ended the arm (campaign log; the Solver role's cited-answer contract, raised in
`rails/solver_citation.py` `parse_cited_answer` and surfaced through the native episode as a node failure):
`SolverCitationError: intent citations must be unique non-blank ids`, re-raised as
`RailsRunnerError: cited-answer contract refused: intent citations must be unique non-blank ids`, and as
`NativeEpisodeError: native episode node failed: ... component 'solver_0_role' ...`.

## 3. What sealed and what did not

| run id | state |
| --- | --- |
| `SAEA-SLURP-STAGE3-COMP1-FOLD-A-SMOKE-4-V1` | **COMPLETED** at cb628f59: 4 rows, 16 calls, 42.382 speech-audio seconds (form proof, unscored) |
| `SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1` (the shared in-chain A/A) | **COMPLETED** at cb628f59: 1,080 rows, 4,435 calls, 12,614.317 speech-audio seconds |
| `SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1` (the COMP-1 arm) | **ABORTED**: 1,913 calls, 5,171.378 speech-audio seconds, no run manifest, no score |
| G5 smoke and G5 arm | not started (step 2 never began) |

The shared A/A is sealed but is read only together with its arm; no score of it has been read.

## 4. Recovery route and what flew after

- Diagnosis and the single permitted recovery re-registration (one per flight) are in progress on branch
  `fable/comp1rec`; nothing of it is merged into master at this writing, and the COMP-1 arm stays unread.
- The queue that was to follow the chain (`queue_comp1_wave.sh`) halted at 03:42:08Z with exit 4 -- "never
  chained onto a STOP".
- The knowledge wave (W1, W3a, W4, sharing the in-chain A/A `SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1`) was then
  launched FRESH after the STOP, not chained onto it: `queue_wave_revtfrl.sh` recorded the STOP as already
  terminal at 03:50:52Z, moved the marker aside, and started `batch_chain_wave.sh` at flight commit
  `5f8b4c9d53862e0243ff4c9610e90189423057d4` (driver start 03:50:54Z; the W1 smoke passed at 03:52:17Z and the
  W1 step's arm started at 03:52:27Z). REV-TFRL-1 follows the wave in the same queue.

## 5. Recovery staged (amendment, 2026-09-28)

- The coordinator chose recovery variant 2, the `-REC` recovery re-registration
  (`SAEA-SLURP-STAGE3-COMP1-FOLD-A-REC-V1`, a full 1,080-row re-fly under a fresh run id). The owner's ruling
  on variant 1, the resume under owner decision 22, is still open; the resume variant stays HELD and is not
  queued.
- The `-REC` smoke and arm were flipped to ready on master; flight commit
  `472474bfc` (arm flip, after the smoke flip `fba40286c`). Decision receipt:
  `coordination/slurp-stage3-comp1-fold-a-v1/root-admission-rec-v1.json` under `SPEECHRL_DATA_DIR`
  (decision id `slurp-stage3-comp1-fold-a-rec-admission-v1`).
- Queue: the scheduled task `SAEA-Queue-AFTER-REVTFRL` waits on the knowledge wave and REV-TFRL-1, then flies
  `-REC` + G5, then the E41 sub10 re-read, then the filler (behind its hold switch).
- Two tool gaps found while staging:
  1. `scripts/flights/repin_cell.py`'s "old hash residue" check scans all of `docs/` and `configs/` and trips
     on a parent package's sealed pins when a derived cell inherits them; the `-REC` flip needed three flip
     runs to converge.
  2. The flip scripts `scripts/flights/e41/e41_flip_sub10.sh` and `scripts/flights/revtfrl/revtfrl_flip.sh`
     still hard-code the old commit trailer.
