# SLURP autonomous typed loop with the ACE comparator (decision 263-A): loop package

Status: **DRAFT / HELD.** This directory is not a live registration package: it holds no `registered-facts`, no plan, no exposure-ledger
row and no countersignature, and nothing here authorises a flight, a readiness flip or an admission entry. The coordinator countersigns
later (design section 7: the countersign attests conformance only).

Design: `docs/superpowers/specs/2026-10-11-slurp-autonomous-typed-loop-with-ace-comparator-design.md` (sections 5-9). Rulings:
`docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`, "Decisions 263-265 ruled" and "265 coverage pre-read ... decision 266
PROPOSED". Iteration 1 will most likely fly the stall default (lock / twin / ACE i1, the typed arm empty by measurement); the driver treats
an empty typed arm as a legal state.

## Files

| file | what it is |
| --- | --- |
| `tfrl-loop-protocol-v1.json` | the pinned rules: selection arithmetic (clauses a-e, quoted from `analysis/sealed_credit/selection.py`), parent choice, edit budget `L_t`, `T_cap` formula and the ACE curator constants hash, the stop rule (three iterations), the curve, the fold roles, the arm set per iteration and the algorithm labels; `protocol_sha256` is the hash of the canonical document without that key. Rebuild or verify with `python -B scripts/flights/tfrl/build_tfrl_loop_protocol.py [--check]`. |
| `archive/` , `archive-specs/`, `iterations/i<t>/` | written by the driver: write-once archive states (identifiers, hashes and numbers only), the accepted states' column specs, and every step's receipt JSON. Absent until the first `open`. |
| `loop-state.json` | written by the first `open`: the protocol hash the loop is pinned to. The driver refuses to run when the file's hash differs. |

## Driver (scripts/flights/tfrl/)

    python -B scripts/flights/tfrl/tfrl_loop_driver.py open  --iter t [--stage propose|cell] ...
    python -B scripts/flights/tfrl/tfrl_loop_driver.py close --iter t [--row-scores F]
    python -B scripts/flights/tfrl/tfrl_loop_driver.py status

Each subcommand is idempotent, refuses while a batch driver, a flight or a flip loop runs, and runs the external model-free analysis
scripts only with `--execute` (otherwise it prints the commands and stops before any archive write). See the module docstring for the flow.

## Human steps the driver cannot take

1. Countersign the DRAFT exposure rows (twice per iteration: the proposer and reflector cells, then the column cell).
2. Mint the decision receipts (`tfrl_mint_receipt.py --kind column|proposers`).
3. Run the loop-form flip (`tfrl_i1_flip.sh`), refresh the registered plan pins, flip again, run the gates.
4. Start `SAEA-Batch-Driver` from PowerShell (the PowerShell task registration; decision 77: a session never launches a flight).
5. Prepare the iteration's `ace-playbook` store release (`prepare_semantic_knowledge_store` over the registration the driver stages) and
   hand the release and snapshot pins back with `--ace-release-pins`. The EMPTY release i0 is already prepared and declared by lock v2.3
   (see "Lock v2.3 and the empty release i0" below); only releases i1 and later are prepared per iteration.
6. After the three iterations: the Fold A confirmation, the DEV composed read and the owner's lock-admission ruling (design R4).

## Lock v2.3 and the empty release i0 (decisions 263 A / 266-A)

* `scripts/build_ace_playbook_i0_release.py` built the EMPTY iteration-0 playbook as the delta-store authored form (one inert anchor row
  addressed to the `planner` node, so the Solver slice is empty) and prepared it write-once under the data root. The committed
  `ace-playbook-i0-release-registration.json` reuses the `stage3-deltas-v1r` construction scope, permitted roster and forbidden rosters;
  `ace-playbook-i0-release-receipt-v1.json` pins `release.json` and `snapshot.json`. `--verify` re-checks the pinned bytes.
* Lock v2.3 (`rails/adapters/slurp_module_lock_v2_3.py`) is a DECLARATION-ONLY successor of v2.2: the v2.2 layer plus
  `knowledge_stores.ace-playbook` at release i0, routed `context_supply` to the Solver. Rendered requests are byte-identical to v2.2's
  (proof P-ACE-0, `tests/unit/test_lock_v2_3_ace_store.py`). The iteration cells compose on `lock: v2.3` (`tf.LOCK`; `tf.PARENT_LOCK` is
  the committed R6-P1 parent's v2.2 and the typed root state's hash). The hooks wrapper the first driver version used is gone: the
  compile and the loader's `verify_declared_module` both run under the real carrier hooks.
* Iteration 1 tables source: `open --iter 1` reads the R6-P1 delivering lock column (run `SAEA-SLURP-STAGE3-NX-R6-PERCEPTION-FOLD-B-V1`,
  attempt `attempt-slurp-native-stage3-nx-r6-perception-fold-b-generation-v1`, arm `lock`), which has per-row official scores on disk; the
  VER-1a S0 pool does not. `--source-run-id` / `--source-attempt` still override. The pinned protocol's `playbook_flow` sentence still
  names the VER-1a column for t = 1; the protocol bytes are hash-pinned and are not rewritten here.

## Known blockers recorded in every iteration package

* The ace release and snapshot pins of the iteration (`i1` and later) are zeros until those releases are prepared.
