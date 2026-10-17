# Launch automation: machine sign-off (M6), one-command launch (M7), pre-registration in flight (M8)

Date: 2026-10-15. Engineering note for the efficiency measures of the registry section "Experimental efficiency: root causes and measures"
(2026-10-14 16:20Z) and owner ruling 314 A. Model-free: nothing here contacts a model, encoder, scorer, server or the GPU.

## M6 Machine sign-off

Files: `scripts/flights/batch/smoke_signoff.py`, `scripts/flights/batch/chain_lib.sh`, worked example
`docs/readiness/2026-10-13-slurp-nxt-r1-thinking-policy-fold-b-v1-signoff-conditions-v1.json`.

* The conditions file (`saea-smoke-signoff-conditions-v1`) is registered data: the no-think nodes per arm, the reasoning and marker limits for
  those nodes (all 0), the per-node limits on cap hits, empty answers, malformed JSON and `finish_reason_length` (all 0), the arm-mix ratio (1.3),
  and optional extra comparisons. The table's own `mode` label must agree with the registered no-think list (a disagreement fails).
* `smoke_signoff.py` PASS writes the marker (line 1: `machine sign-off under owner ruling 314 A: PASS <UTC> package=... conditions=<sha12> table=<sha12>`;
  then the evidence JSON). FAIL writes `<marker>.refused` (the failing checks) and never the marker. An existing marker is never overwritten.
* `chain_lib.sh: wait_or_machine_signoff <reader-cmd> <conditions-json> <marker> <veto-minutes>`: an existing coordinator marker returns at once;
  otherwise the reader runs, the machine decides, PASS starts the VETO window (`SIGNOFF_VETO_MINUTES`, default 20; 0 = none). Deleting the marker
  returns 10, creating `/home/chao/batch-STOP` returns 8; both are logged. FAIL (or a failed reader) falls back to the coordinator wait of the
  existing chains (5 on timeout, 8 on STOP).
* `close_rows_after_seal <run-id>...` runs `ledger_mark_consumed.py --apply` for the flown run ids and commits `docs/exposure-ledger.md` alone
  (idempotent: an unchanged ledger commits nothing; refuses to commit during a merge).
* The NX-T R1 conditions file sits BESIDE the package directory. No registered document pins its hash. A new package's writer should emit its
  own copy inside the package so the hash is pinned before the flight.

Adoption (the coordinator applies it for the next package; `batch_chain_nxt_r1.sh` is not modified here). In the chain, source the library after
`LOG=`/`DATA=` are set and replace the call `wait_signoff || exit $?` (lines 150 and 152 of `batch_chain_nxt_r1.sh`) with:

    wait_or_machine_signoff "bash scripts/flights/nx/nxt_r1_read.sh smoke" "$MAIN/docs/readiness/<package>-signoff-conditions-v1.json" "$SIGNOFF_MARKER" "${SIGNOFF_VETO_MINUTES:-20}" || exit $?

with one added line `. "$SP/chain_lib.sh"` after the `SP=` assignment, and `PY=/home/chao/.venvs/speechrl/bin/python`. The chain's
`NXT1_SIGNOFF_WAIT_SECONDS` is honoured as the fallback wait. After the final seal, call `close_rows_after_seal <run ids>`.

## M7 One-command launch

Files: `scripts/flights/batch/package_launch.sh` (wrapper), `package_launch.py`, worked example `scripts/flights/nx/nxt_r1_launch_spec.json`.

    bash scripts/flights/batch/package_launch.sh <spec.json> [--from STEP] [--until STEP] [--dry-run] [--root-countersign] [--redo STEP]

Steps: derive, write, countersign, mint, commit, flip, chain (default end), read (post-seal, only with `--until read`). Each step is idempotent: a step
with an ok receipt of the spec's `launch_id` is skipped (`--redo` forces it); countersign, mint and commit are also idempotent without receipts
(rows already `REGISTERED BEFORE` are left; `mint.done_if` names a receipt file and strings it must contain; an empty staged diff commits nothing).
Log `/home/chao/<short>-launch.out`, receipts `/home/chao/<short>-launch/launch-steps.jsonl`; the first non-zero step stops the run (exit 1; 2 a rule
refused; 3 countersign without the flag).

Rules enforced before acting: master clean (`git status --porcelain` empty) before derive, flip, chain; no merge/rebase/cherry-pick in progress; no
driver, flight, lease, re-pin or flip process and no `flight.lock` before flip and chain (the pattern of `flip_in_ext4.sh:34`); the flip's gate block
is parsed (one `check: PASS` per cell, no FAIL/REFUSED/DID NOT CONVERGE, `FLIP_CHAIN_DONE`, `master verified at flight commit` equal to HEAD), not the
wrapper's exit code alone; the flight-commit file equals master HEAD before the chain starts (the chain is started with
`saea_task.ps1 -Name <task> -Script <wrapper> -Start` through WSL interop, a task already running is a failure); the countersign step replaces the
`DRAFT -- REGISTERED. ` scope prefix and the leading `DRAFT` note token with the package's `countersign-row-texts-v1.json` text stamped with the UTC,
and only with `--root-countersign`. READ rows (`-READ-`) are not countersigned at launch.

## M8 Which launch steps are safe while a batch driver runs

Verdict, by reading the code:

| Step | In flight | Reason (file:line) |
| --- | --- | --- |
| derive, write, mint, commit | SAFE | They touch the master worktree (git objects, configs, readiness dir, ledger) and `coordination/` receipts only. The flight runs from the separate `fable-batch-flight` worktree at its pinned commit (`batch_driver.sh:35-48`, `batch_chain_nxt_r1.sh:90-92`), so master moving does not touch it. The flight reads its own ledger copy (`runtime.py:_require_exposure_row_unconsumed`). |
| countersign | SAFE (coordinator act) | Edits the master ledger text only. |
| flip | NOT SAFE | See below: three independent blockers. |
| chain start | NOT SAFE | Refuses on any live driver (`batch_chain_nxt_r1.sh:79`); one serial GPU. |

What `core.flight.cli check` (the flip's last gate, `repin.py:497` `default_run_check`; `repin_cell_generic.sh:38`) touches:

* **No flight lock, no attempt record.** `preflight` reserves nothing: the attempt is only checked for existence (`runtime.py:5100-5107`) and opened later by
  `FrozenCoreAdapter`. The flight lock is read as a path only in `serve`/`score` paths (`runtime.py:3889`, `9736`), never acquired by `check`
  (`cli.py` check branch, no `GenerationLease`; the lease is taken in `campaign.py:282`).
* **One data-root write:** `_write_resume_declaration` (`runtime.py:1792-1830`, called at `runtime.py:4984`) writes
  `runs/<run>/<attempt>/resume-declaration.json` and creates that directory, for a resume cell only. NEW: `core.flight.cli check --read-only`
  (`cli.py:176-183`, `cli.py:295-298`) suppresses it; `repin.default_run_check` passes the flag when `SAEA_REPIN_CHECK_READONLY=1` (`repin.py:530`). AMENDED 2026-10-17: the flag is passed by DEFAULT (`SAEA_REPIN_CHECK_READONLY=0` restores the writing check) after the NX-T R1 rec2 flip, run without the env, wrote the declaration and the chain's attempt-not-opened precondition refused the launch.
  Tests: `tests/unit/test_flight_cli_check_read_only.py`.
* **One benign write:** the GGUF identity cache, an atomic write-then-replace in the model materialization root (`identity_cache.py:204-226`), best effort.
* **I/O:** unless `SAEA_RUNTIME_FULL_HASH` is set to a false value (`identity_cache.py:106-129`), the gate full-hashes the GGUF set once per process
  (`gate_runtime.py:_validate_runtime`); with a resident Thinking session that is a full read of the multi-GB GGUF beside the flight. In flight set
  `SAEA_RUNTIME_FULL_HASH=false`.

The blockers that remain, and why the flip still waits for the seal:

1. **Process-name collision at step boundaries.** `batch_driver.sh:113` runs `pgrep -af 'core.flight.cli|lease_cli'` before EVERY queue step and calls
   `stop` (writing `batch-STOP`) when it matches; a `check` process alive at that moment would stop the queue. A single-step queue is exposed only at
   its start, a multi-step queue at every boundary. A read-only flag cannot change the process name.
2. **The refusal guards** `flip_in_ext4.sh:34` (exit 3), `nxt_r1_flip.sh:31` (exit 7) and the other flip scripts' equivalents refuse while a driver or
   `core.flight.cli` is alive. Removing them for a flip in flight would also remove their protection against two flips.
3. **Shared mutable files in `/home/chao`:** `repin_loop_generic.sh` picks the newest `/home/chao/*-repin-*.err`, and `flip_in_ext4.sh:79` and
   `flip_package_ext4.sh` rewrite every `*flight-commit.txt` newer than their marker (a chain writing `batch-flight-commit.txt`, `batch_chain_nxt_r1.sh:92`,
   during a flip would be overwritten). The re-pin's prepare-supply step also runs CPU embedding beside the flight (host-memory and jitter hazards).

Conclusion: everything up to the flip (derive, write, countersign, mint, commit; `package_launch.sh --until commit`) is done in flight. The flip waits for
the seal. The seal-to-launch gap is therefore one flip (about 80 s: `[flip_in_ext4] total 81 s` in the 2026-10-14 log) plus the chain start, with the
sign-off wait now machine-decided. Re-pin outputs that depend on the flown package's HEAD (draft rows carry plan hashes re-pinned at the flipped bytes)
are rewritten by the flip itself, so pre-registering early does not make the flip longer.

## Gates and tests

`tests/unit/test_smoke_signoff.py`, `tests/unit/test_package_launch.py`, `tests/unit/test_flight_cli_check_read_only.py` (fixtures only);
`engineering_base_check.py`, `harness_admission_check.py`, `finite_completion_policy_check.py`.
