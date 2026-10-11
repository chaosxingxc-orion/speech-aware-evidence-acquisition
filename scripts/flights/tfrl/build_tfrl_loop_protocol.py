#!/usr/bin/env python3
"""Write (or --check) the DRAFT loop protocol ``tfrl-loop-protocol-v1.json`` (design section 9 step 2).

The protocol pins every rule of the autonomous loop BEFORE iteration 1: the selection arithmetic exactly as implemented in
``analysis.sealed_credit.selection``, the parent-choice constants, the edit budget L_t, the T_cap formula and the ACE curator
constants hash, the stop rule, the curve definition, the fold roles, the arm set per iteration and the algorithm labels. Its
``protocol_sha256`` is the sha256 of the canonical JSON of the document without that key. ``tfrl_loop_driver.py`` refuses to run
when the file's hash differs from the one recorded at the first ``open``, and the unit tests refuse a protocol that differs from the
implemented constants (so a code change that moves a rule also moves the protocol and is visible).

Model-free; reads the repository only. STATUS: DRAFT / HELD -- nothing here authorises a flight; no exposure-ledger row.

    python -B scripts/flights/tfrl/build_tfrl_loop_protocol.py [--check]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import tfrl_family as tf  # noqa: E402

REPO_ROOT = tf.REPO_ROOT
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

#: The selection clause list, quoted from analysis/sealed_credit/selection.py (module docstring, "Clauses").
SELECTION_CLAUSES = [
    "a. child.vs_lock.slu.lo > ci_lb_min_pp (0)",
    "b. child.vs_lock.slu.point >= slu_floor_pp (1.49)",
    "c. child.vs_lock.slu.point > twin.vs_lock.slu.point (require_beat_twin; the twin is the same-flight aa column)",
    "d. with a parent column: child.vs_parent.slu.point > 0 strictly (or, when the child carries no vs_parent, "
    "child.vs_lock.slu.point - parent.vs_lock.slu.point > 0)",
    "e. intent guard: child.vs_lock.intent.lo >= -intent_guard_pp (-0.65) AND child.vs_lock.intent.point >= "
    "intent_point_floor_pp (0, 'no loss')",
]


def build() -> dict:
    from speech_aware_evidence_acquisition.analysis.sealed_credit import parent_choice, selection  # noqa: PLC0415
    from speech_aware_evidence_acquisition.rails import tfrl_ace_material as ace  # noqa: PLC0415
    from speech_aware_evidence_acquisition.rails import tfrl_typed_proposer as tp  # noqa: PLC0415

    ace_constants = json.loads(json.dumps(ace.ACE_CONSTANTS))
    document = {
        "schema": "saea-tfrl-loop-protocol-v1",
        "status": "DRAFT-HELD",
        "status_note": ("DRAFT. Not registered as a live package: no exposure-ledger row, no countersignature, no flip. The coordinator "
                        "countersigns later. Pinned so that every loop choice is a function of sealed bytes under these rules."),
        "authority": [
            "docs/superpowers/specs/2026-10-11-slurp-autonomous-typed-loop-with-ace-comparator-design.md sections 5, 6, 7, 8, 9",
            "docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md: Decisions 263-265 ruled; 265 coverage pre-read, "
            "decision 266 PROPOSED",
            tf.CONST_PACKAGE_DIR + "/README.md: the construction-source lock column (coordinator resolution of 2026-10-11 to decision 263-A)",
        ],
        "loop": {
            "loop_id": tf.LOOP_ID,
            "stop_rule": {"iterations": selection.STOP_AFTER_ITERATIONS,
                          "text": "Exactly three iterations, whatever happens. No early stop and no extension."},
            "one_experiment_in_flight": True,
            "recovery": "At most one root-diagnosed recovery re-registration per flight; a second failure stops the flight and the fix "
                        "is proven on a four-row dry run.",
            "typed_arm_may_be_empty": ("LEGAL. When no valid candidate clears the predicted bar the iteration still flies lock / aa / "
                                       "(par) / ace, the typed point repeats on the curve, delivery candidates are still read offline "
                                       "at 0 GPU (design R1)."),
            "proposer_never_judges": "The model proposes; deterministic validation and the script objective decide (invariant I-OBJ).",
        },
        "lock": {
            "lock": tf.LOCK, "parent_lock": tf.PARENT_LOCK,
            "note": ("The iteration cells compose on lock v2.3 (v2.2 plus the empty ace-playbook-i0 declaration; requests byte-identical to v2.2's, "
                     "proof P-ACE-0). The construction-source column composes on " + tf.CONST_LOCK + ": the v2.3 ace-playbook store's source ids lie "
                     "inside the construction roster R01C and the runner refuses a query sample inside the composite knowledge source roster."),
        },
        "material_source": {
            "cell": tf.const_names("arm")["experiment"], "smoke_cell": tf.const_names("smoke")["experiment"],
            "run_id": tf.CONST_RUN_ID, "attempt_id": tf.CONST_ATTEMPT_ID, "arm": tf.CONST_ARM, "scorer": tf.CONST_SCORER,
            "roster": tf.CONST_ROSTER_ID, "roster_relpath": tf.CONST_ROSTER["arm"], "rows": tf.CONST_ROWS, "program": tf.CONST_PROGRAM,
            "contacts_per_row": tf.CONST_CONTACTS, "package": tf.CONST_PACKAGE_DIR, "measurement_design": "material-source",
            "claims_benefit": False,
            "rule": ("Every iteration's contrast tables, proposer context tables and ACE reflector materials are read from THIS column (the lock "
                     "does not change between iterations). It is flown once and re-flown only if the lock changes. Reason: the semantic-knowledge "
                     "preparer forbids Fold B rows as carrier ids of a delta-store registration (the construction-roster vs knowledge guard of "
                     "2026-09-23), so material staged from a Fold B column cannot be released."),
            "fold_b_role": ("HELD-OUT selection only. Iterations 2-3 read the previous iteration's Fold B read ONLY for the refused-candidate "
                            "buffer and the ACE counters (credit of the Fold B ace column versus lock): counters are numbers, not knowledge."),
            "ace_release_staging": {
                "construction_scope": "SLURP-STAGE3-CONSTRUCTION-R01C", "permitted_roster": "SLURP-STAGE3-ADVANTAGE-R01C-DISAGREEING-V1",
                "forbidden_rosters": ["SLURP-EVO-FOLD-A-V2", "SLURP-EVO-FOLD-B-V2", "DEV-1000"],
                "carriers": f"the first {tf.ACE_CARRIERS} sorted ids of the permitted roster (a subset of R01C), as the i0 release",
                "registration": "the committed i0 registration's roster pins (stage3-deltas-v1r)"},
        },
        "fold_roles": tf.FOLD_ROLES,
        "selection": {
            "implemented_in": "src/speech_aware_evidence_acquisition/analysis/sealed_credit/selection.py",
            "measurement_design": selection.SLU_DESIGN,
            "metrics": "official pooled micro SLU-F1 and joint intent, paired per row, whole-utterance cluster bootstrap CI95",
            "rules": dict(selection.DEFAULT_RULES),
            "floor_source": "scripts/checks/stage3_effect_floor_check.py FLOOR_TABLE, same-flight-supply-variant, decision 190: SLU 1.49 and "
                            "intent 0.65 at n = 1,080 (analysis.sealed_credit.selection.rules_from_floor_table)",
            "clauses": SELECTION_CLAUSES,
            "accepted_iff": "all clauses present hold; the verdict names every failed clause",
            "offline_candidate": {
                "text": ("An offline delivery or scope candidate is read OFFLINE over the sealed columns (0 GPU), cross-fitted "
                         "(scripts/analysis/tfrl_delivery_fit.py), and accepted iff the cross-fitted CI95 lower bound is above 0 AND "
                         "the point is at least 0.67 pp over the column of the state it edits."),
                "ci_lb_min_pp": 0.0, "point_floor_pp": tf.OFFLINE_FLOOR_PP,
            },
            "predicted_bar": {"pp": tp.PREDICTED_SLU_FLOOR_PP, "applies_to": "construction and supply candidates (decision 192)"},
            "ace_column": {
                "lockable": False,
                "accepted_means": "only that the next playbook grows from this state; a refused ACE state is still the generator of "
                                  "the next reflection (the archive marks it refused)",
                "clause_d": ("vacuous: no previous-ACE-state column flies in the same flight, so the ACE state is judged by clauses "
                             "a, b, c and e (recorded in every close receipt)"),
                "decision_245": "The ACE column puts free text into the Solver prompt by design; it is a non-delivering comparator "
                                "that can never be locked (design 4.4, R9).",
            },
            "per_scenario_and_empty_tables": "reported with every verdict, gate nothing; equal-stratum weighting beside the natural mixture",
        },
        "parent_choice": {
            "implemented_in": "src/speech_aware_evidence_acquisition/analysis/sealed_credit/parent_choice.py",
            "score": "LB_slu(state - lock) - child_penalty_pp * n_flown_children(state); the lock root counts as accepted with LB 0",
            "child_penalty_pp": parent_choice.CHILD_PENALTY_PP,
            "mask_after_refused": parent_choice.MASK_AFTER_REFUSED,
            "tie_break": "smaller state_id (lexicographic)",
            "flown_children": "accepted + refused; proposed-not-flown children do not count",
        },
        "edit_budget_L_t": {"1": parent_choice.edit_budget(1), "2": parent_choice.edit_budget(2), "3": parent_choice.edit_budget(3),
                            "text": "at most 2 operator applications in iteration 1, 1 afterwards"},
        "proposer": {
            "typed_program": tp.TFRL_TYPED_PROGRAM_ID, "ace_program": tp.TFRL_ACE_PROGRAM_ID,
            "typed_response_format": tp.TFRL_TYPED_RESPONSE_FORMAT_ID, "ace_response_format": tp.TFRL_ACE_RESPONSE_FORMAT_ID,
            "retries_per_carrier": tp.RETRIES_PER_CARRIER,
            "typed_carriers": tf.TYPED_CARRIERS, "typed_class_sets": [list(s) for s in tf.TYPED_CLASS_SETS],
            "ace_carriers": "one per scenario (18)",
            "decoding": "temperature 0, one contact per carrier, completion ceiling 1,024, no re-sampling and no best-of-N",
            "instruction_artefacts": {
                "typed": {"relpath": f"configs/{tp.TFRL_TYPED_TEMPLATE_RELPATH}",
                          "sha256": tf.sha256_file(REPO_ROOT / "configs" / tp.TFRL_TYPED_TEMPLATE_RELPATH)},
                "ace": {"relpath": ace.INSTRUCTION_RELPATH, "sha256": tf.sha256_file(REPO_ROOT / ace.INSTRUCTION_RELPATH)},
            },
            "aggregate_only": "tables of counts and rates; cells under three rows are suppressed as '<3'",
        },
        "ace": {
            "algorithm": ace.ACE_CONSTANTS["algorithm"],
            "constants": ace_constants,
            "constants_sha256": ace.constants_hash(ace.ACE_CONSTANTS),
            "constants_note": ("constants_sha256 is content_hash(ACE_CONSTANTS) WITHOUT lock_p99_supplied_tokens; the measured p99 "
                               "joins at the FIT step (with_measured_lock_p99) and is recorded in every open receipt"),
            "counters": "by script (I-OBJ): helpful / harmful / scoped_rows from per-row official SLU-F1 of the ace column vs the lock "
                        "column of the SAME iteration; cumulative across iterations",
            "playbook_flow": ("playbook i0 is empty; the reflector of iteration t reads the construction-source lock column (the same "
                              "column for t = 1, 2 and 3) and the current playbook items; curate() grows i(t-1) into i(t) with the "
                              "counters of iteration t - 1 (script-computed credit over the Fold B ace column versus lock); the ace arm of "
                              "iteration t flies i(t) on Fold B"),
        },
        "t_cap": {
            "formula": ace.ACE_CONSTANTS["t_cap_formula"],
            "allowance_items": ace.ACE_CONSTANTS["allowance_items"],
            "tokens_per_supplied_item": ace.ACE_CONSTANTS["tokens_per_supplied_item"],
            "allowance_tokens": ace.ACE_CONSTANTS["allowance_tokens"],
            "lock_p99_supplied_tokens": ("MEASURED on the construction-source lock column (table_d overall supplied_tokens p99 of the "
                                         "lock tables, or the FIT-step tokenizer measurement); never a placeholder"),
            "enforcement": "column max_supplied_items 63 = 55 + 8 and fit_estimate in the supply frame; the curator truncates by token "
                           "count at T_cap; the 4-row dry run refuses an arm over T_cap",
        },
        "curve": {
            "implemented_in": "selection.curve",
            "series": ["typed", "ace"],
            "per_series": "three points; each is the realised Fold B SLU delta vs lock of the best accepted state after iteration t "
                          "(best = highest point, ties by state_id), with its CI95",
            "refused_or_unflown_iteration": "repeats the previous accepted level, marked 'refused' (a flown child was refused) or "
                                            "'unflown' (nothing flew); plotted, never dropped",
            "children": "every flown child's own delta is listed beside the level, accepted or not",
        },
        "arm_sets": {
            "1": {"arms": list(tf.arm_ids(1)), "typed_present": False,
                  "note": "typ is added only when a valid candidate clears the 1.5 pp predicted bar; then the arms are "
                          + ", ".join(tf.arm_ids(1, typed_present=True)) + " (program c%d)" % tf.ceiling(1, typed_present=True)},
            "2": {"arms": list(tf.arm_ids(2, typed_present=True)), "typed_present": "optional",
                  "note": "par is the accumulated accepted typed parent; typ is omitted when no valid candidate exists"},
            "3": {"arms": list(tf.arm_ids(3, typed_present=True)), "typed_present": "optional"},
            "order_rule": "candidates first, then the twin aa (replicate_of lock), then the delivering arm lock LAST with no override "
                          "and no release swap (invariants I7, I7v)",
            "delivery_and_scope_rules": "not arms: read offline over every column",
        },
        "algorithm_labels": {
            "typed_proposer_cell": {"id": tf.ALGORITHM_TYPED, "operators_used": ["credit_assignment", "update"]},
            "ace_reflector_cell": {"id": tf.ALGORITHM_ACE, "operators_used": ["update", "selection"]},
            "iteration_cell": {"id": tf.ALGORITHM_TYPED,
                               "operators_used": ["rollout", "scoring", "credit_assignment", "selection", "context_application"],
                               "columns": {tf.ARM_PARENT: tf.ALGORITHM_TYPED, tf.ARM_TYPED: tf.ALGORITHM_TYPED, tf.ARM_ACE: tf.ALGORITHM_ACE}},
        },
        "measurement_block": {
            "measurement_design": selection.SLU_DESIGN, "primary_metric_key": "slu", "rows": tf.ROWS,
            "nomination_rule": "official-column", "claim_ceiling": "nominated",
            "claims_benefit": "true only when the validator's predicted effect is at least 1.5 pp; false below the floor, never true under it",
            "text_only_cells": "form-proof, claims_benefit false (fewer than 200 rows, rule 5)",
        },
        "claim_rule": ("Decision 263: the typed loop's cumulative state vs lock has CI-LB > 0 on Fold A (one attempt, rules fixed, "
                       "thresholds fitted on Fold B, not re-fitted). ACE is reported either way. Development numbers only."),
        "human_steps": [
            "coordinator countersigns the exposure rows (twice per iteration: proposer / reflector cells and the column cell)",
            "decision receipts are minted", "the loop-form flip runs, then the plan-pin refresh, then the flip again",
            "the coordinator or owner starts SAEA-Batch-Driver from PowerShell (decision 77); the session never launches a flight",
        ],
        "forbidden": [
            "any change of the protocol after the first open (the driver refuses a changed sha256)",
            "substituting a candidate by hand (only the labelled hand-author fallback, which needs an owner order)",
            "re-sampling or best-of-N over proposals", "a free-text field in the typed candidate",
            "writing under the data root outside analysis/" + tf.LOOP_ID + "/",
        ],
    }
    document["protocol_sha256"] = tf.canonical_sha256(document)
    return document


def render(document: dict) -> str:
    return json.dumps(document, indent=2, ensure_ascii=True, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail when the committed file differs from the built one")
    parser.add_argument("--out", default=str(REPO_ROOT / tf.PROTOCOL_RELPATH))
    args = parser.parse_args(argv)
    document = build()
    text = render(document)
    out = Path(args.out)
    if args.check:
        current = out.read_text(encoding="utf-8") if out.exists() else ""
        if current != text:
            print(f"FAIL: {out} differs from the implemented constants (rebuild with this script)")
            return 1
        print(f"ok: {out.name} protocol_sha256={document['protocol_sha256']}")
        return 0
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {out} protocol_sha256={document['protocol_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
