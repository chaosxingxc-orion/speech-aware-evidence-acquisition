# Engineering base cleanup v1 (2026-10-09)

Owner instruction of 2026-10-09: "clean up the engineering base". Engineering agent (Sonnet) in worktree
`fable/base-cleanup`, cut from `master` at `d389ee178`. Model-free throughout: zero model, tokenizer,
encoder, scorer, server, GPU and network contacts; no utterance text or gold was read or printed; no
scientific number changed; no hash-pinned registered artifact (flown-cell fragment, receipt, sealed
plan) was edited. Master was clean at the start (`git status --porcelain` empty).

## 1. Unit suite

Starting state on master (owner session): `22 failed, 24423 passed, 10 skipped, 2 errors`, one failure already
fixed. The first full run in this worktree (`-q --tb=line -p no:logging --show-capture=no`, 31 minutes) listed
`21 failed, 24542 passed, 10 skipped, 2 errors`, which includes the diagnostics-normalisation test the owner
session listed separately. Every one was root-caused; none was deleted or loosened.

| test | root cause | fix |
| --- | --- | --- |
| `test_batch_process_guard` (2) | stale fixture: a plan-routed step inspects through `$REPO/scripts/flights/batch/batch_inspect.py`, the fixture only stubbed `$SP/batch_inspect.py` | fixture writes the recording stub into the fixture repo too |
| `test_build_a2t_construction_roster` (2) | code wrong: the Audio2Tool exposure union failed closed on the nine SLURP `saea-runtime-subset-receipt-v1/-v2` files filed in `docs/receipts/rosters/` | `knowledge_build_a2t._roster_receipt_source` skips them only when every id is a `slurp:` id (non-empty); any other shape still fails closed |
| `test_comp1b_testsample_milestone` (2) | stale: both cells were flipped to `ready` on 2026-09-30 (`297397cd3`); the shared sample-preparation artifact is now named once per cell | test expects `ready`; the missing-artifact test asserts the refusal kind and path for every cell that pins it |
| `test_configured_context_lifecycle` (8) | stale: `_check_registered_supply_binding` gained a required `ledger` argument | test passes `{}` (the plans carry no `carrier_lock_key`) |
| `test_flight_queue_readiness` (1) | stale: `FlightQueue.next_ready()` now raises `FlightQueueError` ("Campaign admission refused after ...") once a completed flight's scoring failed | test asserts the stricter refusal; the invariant (a failed score never satisfies a dependency) is kept |
| `test_native_episode_diagnostics_normalisation` (1) | stale: I7n requires the output row to name the normaliser's carrier | fixture row carries `carrier_lock_key` taken from the receipt; the rehashed-false-delivery test still guards the custody invariant |
| `test_rails_controllers::test_registered_program_ids_match_the_shipped_configs` (1) | stale oracle: `phase-native-slot-review-contract-v1` shipped 2026-10-02 without a row | row added, shape read from the shipped config (4 roles, ceiling 13) |
| `test_system_text_context_read` / `_recovery` (2) | stale: the reward-link stub validates the projection strictly; the supplements carried `{"scorer": ...}` only | supplements carry a full `RewardProjection` |
| `test_obs_loop_policy`, `test_serving_resource_guard` (2 errors) | environment: the prescribed flag `-p no:logging` removes the `caplog` fixture those two tests use | none needed; they pass without `-p no:logging` (the final run omits the flag) |

Also exposed and fixed (see section 2): `test_flight_registration_check::test_the_real_tree_terminates_with_a_documented_exit_code`
failed on the real tree because the gate itself crashed (uncaught `BundleError`).

### Residue (left failing on purpose, scientific invariants)

1. `test_natural_source_compatibility::test_actual_reviewed_full_runtime_ast`. It proves
   `core/flight/runtime.py` differs from the historical natural runtime (`d4ba0ec70`) only by the reviewed
   audio-guard insertion. `f5617bcd9` (2026-10-09, NX node-template wiring) legitimately changed
   `runtime.py`, so the delta is no longer the reviewed one. Honest repair needs a new root review of that
   delta and re-pinned compatibility records; the assertion is not loosened.
2. `test_filler_family::test_disjointness_proof_is_complete_and_zero`. The registered Fold B filler family
   (1,080 rows, disjointness proof hash-pinned) now overlaps two later roster receipts:
   `slurp-system-text-selection-400-analysis-v1.json` and `slurp-system-text-update-3-400-analysis-v1.json`
   (400 of 400 ids each lie inside the filler family; both bound by `84c22d759`, 2026-10-02). The filler
   family is therefore no longer unexposed; this needs an owner/coordinator ruling, not a test edit.

## 2. `flight_registration_check.py` (tree mode)

Before: `FAIL (984 cell(s) in scope (tree mode), 560 clean, 42 blocking, 382 advisory; blocking from 2026-09-26 in tree mode)`.

The 42 blocking cells and their finding kinds fell into five groups.

| group | cells | finding kinds | class | disposition |
| --- | --- | --- | --- | --- |
| Fable-era held cells whose registered plan predates the flip: `comp1-fold-a-rec-v1`, `comp1-fold-a-rec-smoke-4-v1`, `comp1b-testsample-v1` | 3 | `registered-supply-binding` | (b) check wrong | plan declares the artifact path with a placeholder hash (zeros) and annotation members; comparison now ignores annotations and compares a placeholder on `relpath` only |
| flown tokenizer-only capacity spends (`summary-s1..s4-capacity-v2`, `s1..s4-np1-capacity-v1`, `s1..s4-wire-capacity-v1`, `batch-synthesis001-np1-capacity-v1`, `-format-np1-capacity-v1`, `comparison001`, `event-credit001`, `group-update001` and its format cell) | 18 | `missing-row`, `no-analysis-recipe`, `no-decision-receipt`, `row-not-countersigned` | (b) flown, check blind | these spends leave no `attempts/` or `runs/` record; their evidence is the ledger row (`consumed = yes`, `Completed`/`Verdict:` disposition). Whole-tree mode now treats such a row as historical while the cell is the sole attempt registered for its run id; named (launch) cells and a second attempt are still gated in full |
| never-flown superseded drafts: `summary-s1..s4-capacity-v1`, `summary-s1..s4-np1-run-v1`, `memory-batch002-empty-s4-run-v1` | 9 | `missing-row`, `no-analysis-recipe`, `no-decision-receipt`, `row-not-countersigned`, `run-not-eligible` | (a) retired | per the 2026-09-19 ledger-hygiene convention: `readiness.state` -> `superseded` with one appended sentence, each unconsumed ledger row closed (`consumed` no -> yes, one appended sentence). Evidence per cell: zero contacts (`2026-09-26-system-summary-fit-precontact-refusal.json`, `2026-09-26-system-summary001-precontact-refusal.json`, `2026-09-26-system-memory-batch002-resource-read-failure.json` with `empty-s4` `not_started`) and a flown successor (capacity-v2, np1-run-v2, empty-s4 recovery1) |
| K4 recovery1 remaining-b2: `branch-13..16`, `seed`, `seed-aa` | 6 | `row-not-countersigned`, `no-decision-receipt` | (a') live prepared line | see residue |
| PSV4: `psv4-fold-b-v1`, `psv4-fold-b-smoke-4-v1` | 2 | `registered-supply-binding` | (c) real drift | see residue |
| simple-consumption N100: `review-off-n100-v1`, `seed-aa-n100-v1`, `solver-lookup-n100-v1`, `seed-n100-audio-recovery1-v1` | 4 | `population-config-binding` (3), `missing-row` + `no-package` (1) | (a') live prepared line | see residue |

Also fixed: an uncaught `BundleError` (source custody of a recorded original worktree,
`/home/chao/saea-worktrees/codex-simple-consumption-natural4-instrumented-v4`, which does not exist on this
machine) crashed the whole gate on the four flown `audio-recovery1-entry2` cells. It is now a
`population-config-binding` finding on those (historical, reported-only) cells.

Unit tests for each rule were added to `tests/unit/test_flight_registration_check.py`.

### Residue (12 blocking cells, all ready and unflown, none a gate defect)

* **K4 recovery1 remaining-b2 (6)**: the ChatGPT prepared line is registered `ready` with DRAFT exposure
  rows ("DRAFT exposure rows block dispatch pending root admission and structural proof"). The gate is
  doing its job: they cannot launch. Closing them needs root admission (countersign + decision receipt) or a
  flip back to `held` through `repin_cell.py`, which rewrites hashes in a live line; not done here.
* **simple-consumption N100 (4)**: `review-off-n100-v1` and `solver-lookup-n100-v1` report "N20 prepared
  implementation source differs"; `seed-aa-n100-v1` reports "Registered cumulative speech-audio budget 1500
  is below the complete legal bound 3820"; `seed-n100-audio-recovery1-v1` has no ledger row and no readiness
  package. These are open registration defects of the live ChatGPT line, for its owner to re-register.
* **PSV4 (2)**: `psv4-fold-b-v1` and `-smoke-4-v1` registered plans (hash-pinned) name
  `prepared/.../phase-supply-v2.json` ("MINTED_AT_THE_FLIP"), but the flip (`1ffad1a0e`) minted and pinned
  `phase-supply-v1.json` in the baseline. A genuine path disagreement on a cell decision 208 intends to fly;
  needs a coordinator re-registration or an explicit amendment, not a gate change.

## 3. `results_ledger_check.py`

The harness-admission entry `SAEA-SLURP-STAGE3-SLOTFILL-FOLD-A-V1` is `PENDING`: the dispatcher slot-fill cell
(`docs/readiness/2026-09-27-slurp-stage3-slotfill-fold-a-v1/`) was registered and held on 2026-09-27 and has
never flown (no run, attempt or sealed output on the data root; the `WIRECHECK-SLOTFILL-*` directories are
model-free wire checks). A descriptive `PENDING`, `flown: false` row `SLURP-SLOTFILL` was added to the JSON
ledger (carrier_summary SLURP rows 55 -> 56, pending 13 -> 14) and its markdown mirror, exactly like the
held `SLURP-MODULE-COMP1B-DEV2000` row. The check still passes; the SLOTFILL finding is gone. Twelve older
cross-check C findings (flown, decided Stage-2 entries whose results rows are filed under other run ids)
remain by design: that check reports and never fixes them.

## 4. Hygiene sweep

* `__pycache__` / `*.pyc` under `src/` or `reproduction/`: none, in the worktree or on master (D3 gate clean).
  Tracked bytecode: none.
* `.gitattributes` LF (`git ls-files --eol`): no tracked file has a non-LF index or working-tree form; no CR in
  any tracked `*.sh` or `*.py`.
* Byte-identical duplicate scripts under `scripts/`: none.
* Control characters: none introduced (one `\b` escape slip during the work was caught by a test and fixed
  before commit).
* Report-only: a name-token scan finds configs whose stem appears in no other tracked file (fragments that a
  glob or a prefix may still reach): `configs/` analysis 17, baseline 75, campaign 17, dataset 9, experiment
  170, experiments 18, knowledge 1, model 23, policy 3, preparation 37, toolkit 4. These are candidates for a
  reviewed prune, not deletions: the scan cannot see prefix or glob references and most are historical flown
  cells whose bytes are evidence.
* The ignored `logs/` directory in the worktree is test output, untracked, not committed.

## 5. Verification (end of work, from the worktree)

* Full unit suite (`pytest tests/unit -q --tb=line --show-capture=no`): `2 failed, 24576 passed, 10 skipped, 320 warnings, 75 subtests passed in 1917.85s`; the two failures are the two residue items of section 1.
* `flight_registration_check.py`: `FAIL (975 cell(s) in scope (tree mode), 579 clean, 12 blocking, 384 advisory; blocking from 2026-09-26 in tree mode)` (before: 984 / 560 clean / 42 blocking / 382 advisory); the 12 are the residue of section 2.
* `results_ledger_check.py`: `PASS (93 row(s), 150 run id(s) registered and closed, 306 cited path(s) present, 35 status word(s) re-parsed from the verdict's first line, 0 row(s) compared against the umbrella, 291 finding(s) reported)`; the SLOTFILL finding is gone.
* `engineering_base_check.py`: `PASS`. `tool_catalog_check.py`: `PASS (34 tools, 1 extra pin(s), 17 module(s) clean of framework clients)`.
* `finite_completion_policy_check.py`: `PASS (... 570 in-scope plan(s), 449 baseline(s) read; out of scope: 2 with no ledger row, 440 consumed, 0 naming no run id, 2 not-live cell(s) [superseded 2])`.
* `stage3_effect_floor_check.py`: `PASS (... 0 blocking, 10 advisory finding(s) ...)`. `stage3_algorithm_label_check.py`: `PASS (1135 Stage-3 cell(s) of 1583 experiment fragment(s); 4 allowlisted ...)`.
* `handoff_freshness_check.py`: `FAIL [stale-vs-results]` on the stamp only (the stamp predates the results-ledger commit of this branch); the handoff refresh belongs to the coordinator at merge.

## 6. Commits (branch `fable/base-cleanup`, not merged)

Five logical commits precede this note: stale-test repairs, the Audio2Tool exposure-union fix, the gate repairs with their tests, the retirement of nine superseded cells, and the SLOTFILL results-ledger row. Each commit message states its scope.
