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

## Material source: the construction-source lock column (coordinator resolution of 2026-10-11)

* The proposer's tables and the ACE reflector's material come from ONE lock column flown on the CONSTRUCTION roster R01C (625 TRAIN rows outside
  Fold A and Fold B): cell `slurp-native-stage3-tfrl-construction-lock-r01c-v1`, package
  `docs/readiness/2026-10-11-slurp-tfrl-construction-source-v1/`. `open --iter t` reads it for t = 1, 2 and 3 (the lock does not change), never a Fold B
  column. Reason: the semantic-knowledge preparer forbids Fold B rows as carrier ids of a delta-store registration (the construction-roster vs
  knowledge guard of 2026-09-23), so playbook releases i1+ staged from a Fold B column are refused. Fold B is the HELD-OUT selection split; Fold A confirms.
* Iterations 2-3 read the previous iteration's Fold B read ONLY for the refused-candidate buffer and the ACE counters (credit of the Fold B `ace`
  column versus `lock`, by script). Counters are numbers, not knowledge, so they may flow from the evaluation fold.
* Releases i1+ are staged with the committed `stage3-deltas-v1r` rosters: construction scope R01C, permitted roster SLURP-STAGE3-ADVANTAGE-R01C-DISAGREEING-V1
  (a subset of R01C), forbidden Fold A / Fold B / DEV-1000; the carriers are the first 50 sorted ids of the permitted roster
  (`tfrl_loop_lib.ace_release_binding`, which also refuses a carrier outside R01C or inside a forbidden roster). The driver writes the registration beside
  the protocol as `ace-playbook-i<t>-release-registration.json`; `prepare_semantic_knowledge_store` compiles it unchanged.
* `tfrl-loop-protocol-v1.json` names lock v2.3 for the iteration cells, the construction column as `material_source` and Fold B as held-out selection.
  `--source-run-id` / `--source-attempt` still override the source (tests, recovery) and are recorded in the receipt.

## Known blockers recorded in every iteration package

* The ace release and snapshot pins of the iteration (`i1` and later) are zeros until those releases are prepared.
* The construction-source column must be flown (and its two named blockers resolved: the lock's exemplar pool contains every R01C row, and the R01C
  agreement table is owed) before `open --iter 1 --execute` can read its tables; see the construction-source package README.
* OPEN DEFECT, outside this change: `rails/tfrl_ace_material.playbook_release_rows` writes `prior_score = float(total - rank)` (18.0, 17.0, ...), but
  `KnowledgeSnapshot.frozen_json` requires a probability in [0, 1], so every NON-EMPTY playbook release (i1 and later) is refused by the preparer
  whatever the rosters (the empty release i0 passes only because its anchor row carries 0.0). The fix is to divide by `total`; the module is owned by the
  E-T2 change. `tests/unit/test_tfrl_loop_driver.py` stages the roster-guard proofs with an order-preserving rescale and records the defect in a strict
  xfail test, which fails (unexpected pass) the day the module is fixed, so the mark is removed then.

## Planned GPU hours of iterations 2 and 3 (rule, 2026-10-11)

Iteration 1 flew 4,320 contacts in 2.49 GPU-active hours against a planned 1.5 (calls and audio exactly at plan): 2.075 s per contact. From
iteration 2 the column's `planned_gpu_hours` is DERIVED, not hand-set (`tfrl_family.planned_gpu_hours_arm`):
`ceil(rows x contacts_per_row x 2.075 s x 1.3 / 3600)` rounded UP to 0.1 h (iteration 2 and 3, five contacts per row: 4.1 h). The smoke cell
keeps its fixed 1.0 h. The pinned protocol JSON does not carry GPU hours, so it is unchanged (no rebuild was needed).

## Repair of a closed iteration (one-off, idempotent)

    python -B scripts/flights/tfrl/tfrl_loop_driver.py repair --iter 1 [--skip-playbook-file] [--execute]

Makes `playbook/playbook-i<t>.json` the playbook behind the pinned release (the stale file is kept as `playbook-i<t>.superseded-<ts>.json`),
writes a correction record under `archive/corrections/` for an archived ACE state that binds another playbook hash (state files are never
edited; `Archive.states()` applies the record), and reads every offline candidate that has no archive state (an unsupported family is archived
as refused with code `offline-family-unsupported`). Archive correction records are part of `archive_sha256`.

## Successor note 2026-10-13: typed-proposer fixes (owner ruling 300 A)

Iterations 1-3 flew with two defects in the typed-proposer receipt path. The sealed packages in this directory are unchanged; this note
supersedes nothing and describes the code fixes only.

1. Offered class set dropped. `derive_tfrl_iteration_cells.derive_text_only` registers a per-carrier `allowed_classes` set (construction /
   supply / delivery+scope) in the proposer brief, but `tfrl_cell_stage_inputs.build_typed_receipts` did not carry it into the typed receipts,
   so `tp.validate_candidate(allowed_classes=...)` never ran in `open --stage cell`. At least 6 of the 9 delivery candidates came from carriers
   that were not offered delivery, and the construction and supply classes were never proposed. Fix: each entry now carries `allowed_classes`
   read (fail-closed) from `tfrl_proposer.carriers` of the registered baseline fragment; a legal candidate whose class is outside its carrier's
   set is refused with the finding `class-not-allowed` (it does not shadow an identical candidate from an offered carrier); `candidates.json`
   records `offered_class_check` and the close receipt carries `typed_class_check` (`applied`, `class_not_offered`, `entry_layouts`).
2. Mislabelled hash field. `sample_id_sha_prefix` held `response_sha256[:12]`. It now holds `sha256(sample_id)[:12]`, and the response-hash
   prefix is recorded under `response_sha256_prefix`. Readers accept both layouts: `tfrl_loop_lib.typed_entry_layout` labels an entry
   `v1-legacy-response-hash-in-sample-id-field` (old) or `v2-sample-id-sha-and-response-sha-prefixes` (new).

Receipts sealed for iterations 1-3 stay in the v1 layout without `allowed_classes`; their close summaries read `applied: false`.
