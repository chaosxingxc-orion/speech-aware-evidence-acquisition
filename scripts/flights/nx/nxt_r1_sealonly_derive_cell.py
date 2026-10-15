#!/usr/bin/env python3
"""Derive the NX-T R1 SEAL-ONLY completion of the stopped column flight (script-derived, decision 58). Model-free.

The column attempt ``attempt-slurp-native-stage3-nxt-r1-thinking-policy-fold-b-generation-rec1-v1`` (run ``SAEA-SLURP-STAGE3-NXT-R1-THINKING-POLICY-FOLD-B-V1``)
completed 1,029 of the 1,080 Fold B rows (10,298 contacts, 30,101.2 s of repeated speech) and STOPPED on row 1,030: a NON-delivering arm's (``both-off``)
no-think Solver contact ended on ``finish_reason`` ``length`` at its 1,024-token cap, the Solver fan-out left through that one exception so the twin and the
delivering arm never ran, and the final assembly raised ``RailsRunnerError: perception branch 'both-off' sealed no level-2 Solver column``. The fix
(``a harness change``: a non-delivering arm's finite completion is recorded as an ABSENT column, the delivering arm keeps its fail-closed path) is on master;
this derive registers the other half of the coordinator's proposal (owner decision 320 A, proposed): SEAL-ONLY the 1,029 complete rows, read them at n = 1,029,
report the failing row as a ``both-off`` delivery failure and the 50 never-started rows by count, and close the cell.

What it writes (CONFIG and PACKAGE files only; no contact, no ledger write, no receipt, no flip):

* ``configs/dataset/slurp-speech-native-evo-fold-b-nxt1-complete-<n>.json`` -- the Fold B runtime view restricted to the complete rows (a strict subset, its own
  split name and split identity; every item byte-identical to the parent's);
* ``configs/baseline/<parent baseline>-sealonly.json`` -- the parent's bytes except ``native_contact_fit.attempt_id`` and the note;
* ``configs/experiment/<parent cell>-sealonly.json`` -- the seal-only cell: SAME run id, a new attempt id, ``resume_from`` the stopped attempt by TRACE sha256 (mode A),
  allowed stages ``check`` / ``prepare-supply`` / ``seal-only``, the roster fixed to the complete rows;
* ``docs/readiness/<date>-<package>-sealonly-v1/`` -- README, complete-rows (a roster receipt of the complete rows), protocol, generation and FIT plans, analysis
  recipe, registered facts, draft ledger rows, countersign texts and the root-admission DRAFT; and the preregistration note beside it.

Mode A, not mode B (checkpoint): a checkpoint resume refuses unless the running ``runtime.py`` / ``rails/runner.py`` / ``core/row_checkpoint.py`` hash to the code
that wrote the checkpoint, and the absent-column harness fix changes ``rails/runner.py`` by design. A trace resume has no code-identity pin; it replays the rows'
terminal receipts under the CURRENT code and the offline replay (``scripts/analysis/replay_seal_consistency.py``, the resume prelaunch gate's checker) proves every
kept row seals clean first. The checkpoint's whole-file sha256 is recorded here as corroboration (the 1,029 rows agree with the trace's).

    PYTHONPATH=<tree>/src python -B scripts/flights/nx/nxt_r1_sealonly_derive_cell.py --data-root DIR \\
        --replay-json REPORT.json --replay-commit <code commit> --replay-at <utc>

``--data-root`` is read ONLY (the stopped attempt's trace and checkpoint, the attempt record, the pins ``compute_cell_identity`` needs).
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "lib"))

import nxt_r1_family as fam  # noqa: E402
import recovery as rcv  # noqa: E402

REPO = fam.REPO_ROOT
SPEC = fam.sealonly_spec()
ARM = fam.CELLS["arm"]
RD, PREREG = SPEC["package"], SPEC["preregistration"]
EXP = CELL = SPEC["cell"]
BASE = SPEC["baseline"]
RUN, FIT_RUN = SPEC["run"], SPEC["fit_run"]
PRED, SO, FSO = SPEC["predecessor_attempt"], SPEC["attempt"], SPEC["fit_attempt"]
DEC_ID, DEC_RELPATH, PROOF_RUN, READ_RUN = SPEC["decision_id"], SPEC["decision_relpath"], SPEC["proof_run"], SPEC["read_run"]
PARENT_RD = fam.PACKAGE
COMPLETE_ROWS = SPEC["complete_rows"]
PARENT_DATASET = "slurp-speech-native-evo-fold-b-1080"
PARENT_ROSTER = fam.ROSTER["arm"]
PARENT_SPLIT = fam.SPLIT_ID
CARRIER = "slurp"

DATE = "2026-10-15"
REGISTERED_AT = "2026-10-15T23:30:00.000000+00:00"
SOURCE_TREE = "studies/speech-aware-evidence-acquisition (single master writer; the harness fix and this registration merged from branch sonnet/nxt1-sealonly)"
STATUS = "REGISTERED_BEFORE_CONTACT_SEAL_ONLY_PENDING_OWNER_DECISION_320"
OWNER_BASIS = ("owner decision 320 A (coordinator's proposal of 2026-10-15, PENDING the owner's answer): seal-only the complete rows of the stopped NX-T R1 column, "
               "read at the complete-row n, report the failing row and the never-started rows by count, close the cell")
FLIGHT_COMMIT = "8f9d8e1ee"
STOP_AT = "2026-10-15T22:33:00Z"
STARTED_AT = "2026-10-14T17:14:43Z"
FAILURE_ERROR = "RailsRunnerError: perception branch 'both-off' sealed no level-2 Solver column"


# ---------------------------------------------------------------------------------------------------------------------------------------
# small file helpers
# ---------------------------------------------------------------------------------------------------------------------------------------


def _load(relpath: str):
    return json.loads((REPO / relpath).read_text(encoding="utf-8"))


def _dump(relpath: str, document) -> str:
    text = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    path = REPO / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write_text(relpath: str, text: str) -> str:
    path = REPO / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha(relpath: str) -> str:
    return hashlib.sha256((REPO / relpath).read_bytes()).hexdigest()


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _head() -> str:
    return subprocess.run(["git", "-C", str(REPO), "rev-parse", "--short=9", "HEAD"], capture_output=True, text=True).stdout.strip()


def _split_hash(ids) -> str:
    from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash  # noqa: PLC0415

    return split_identity_hash(prefixed(CARRIER, ids))


def _content_hash(document) -> str:
    from speech_aware_evidence_acquisition.rails.hashing import content_hash  # noqa: PLC0415

    return content_hash(document)


def _identity(experiment: str, cell_id: str):
    from speech_aware_evidence_acquisition.core.flight.campaign import load_campaign_cells  # noqa: PLC0415
    from speech_aware_evidence_acquisition.core.flight.repin import compute_cell_identity  # noqa: PLC0415

    cells = [c for c in load_campaign_cells(REPO, experiment) if c.document["cell_id"] == cell_id]
    assert len(cells) == 1, (experiment, cell_id)
    return compute_cell_identity(REPO, experiment, cells[0])


# ---------------------------------------------------------------------------------------------------------------------------------------
# 1. the stopped attempt, read from the data root (read-only)
# ---------------------------------------------------------------------------------------------------------------------------------------


def inspect_predecessor(data_root: Path, parent_ids: list[str]) -> dict:
    """What the stopped attempt left on the data root, from its own bytes (read-only): both hashes, the complete row ids (mode A, the trace), the failing row id
    (the trace's own ``sample-execution-timing`` record that says ``failed``), the rows it never started, and its attempt record's spend."""

    from speech_aware_evidence_acquisition.core.flight.resume import read_predecessor_attempt  # noqa: PLC0415
    from speech_aware_evidence_acquisition.core.row_checkpoint import read_checkpoint, sha256_file  # noqa: PLC0415

    attempt_dir = Path(data_root) / "runs" / RUN / PRED
    trace = attempt_dir / f"{RUN}.trace.jsonl"
    checkpoint = attempt_dir / f"{RUN}.rows.ckpt.jsonl"
    trace_sha = _sha_file(trace)
    checkpoint_sha = sha256_file(checkpoint)
    scan = read_predecessor_attempt(run_id=RUN, attempt_id=PRED, attempt_dir=attempt_dir, expected_trace_sha256=trace_sha, program_id=fam.PROGRAM)
    if scan.incomplete:
        raise SystemExit(f"{len(scan.incomplete)} started row(s) of the stopped attempt are INCOMPLETE; a seal-only completion needs none: {sorted(scan.incomplete)[:3]}")
    complete = set(scan.complete_sample_ids)
    ckpt_ids = [row.sample_id for row in read_checkpoint(checkpoint, expected_sha256=checkpoint_sha).rows if row.complete]
    if set(ckpt_ids) != complete or len(ckpt_ids) != len(complete):
        raise SystemExit("the checkpoint's complete rows are not the trace's complete rows")
    failed: list[str] = []
    with trace.open("rb") as handle:
        for raw in handle:
            if b"use_sample_execution_timing" not in raw:
                continue
            record = json.loads(raw)
            timing = (record.get("payload") or {}).get("use_sample_execution_timing") or {}
            if timing.get("status") == "failed":
                failed.append(str(timing["sample_id"]))
    unknown = sorted((complete | set(failed)) - set(parent_ids))
    if unknown:
        raise SystemExit(f"{len(unknown)} id(s) of the stopped attempt are outside the Fold B roster: {unknown[:3]}")
    attempt = json.loads((Path(data_root) / "attempts" / RUN / f"{PRED}.json").read_text(encoding="utf-8"))
    return {
        "trace_sha256": trace_sha, "checkpoint_sha256": checkpoint_sha, "trace_bytes": trace.stat().st_size, "checkpoint_bytes": checkpoint.stat().st_size,
        "complete_ids_in_roster_order": [sid for sid in parent_ids if sid in complete],
        "failed_ids": [sid for sid in parent_ids if sid in set(failed)],
        "never_started_ids": [sid for sid in parent_ids if sid not in complete and sid not in set(failed)],
        "attempt_record": {"state": attempt.get("state"), "failure_reason": attempt.get("failure_reason"), "calls": attempt["actual"]["calls"],
                           "audio_seconds": attempt["actual"]["audio_seconds"], "reserved": attempt.get("reserved")},
    }


def complete_rows_document(info: dict, parent_roster: dict) -> dict:
    """The complete rows as a ROSTER RECEIPT shaped document (``items[].sample_id`` / ``stratum`` / ``utterance_id``, the shape ``stage3_rollout_score.load_roster``
    and ``slurp_direct_fold_b_core_read.roster_maps`` read). It lives in the package, NOT under ``docs/receipts/rosters/`` (that directory is the exposure gate's
    roster registry); it carries no ``derived_from`` partition declaration."""

    keep = set(info["complete_ids_in_roster_order"])
    items = [copy.deepcopy(item) for item in parent_roster["items"] if item["sample_id"] in keep]
    assert [i["sample_id"] for i in items] == info["complete_ids_in_roster_order"]
    n = len(items)
    doc = {
        "schema": "saea-nxt-r1-sealonly-roster-v1",
        "roster_id": f"{PARENT_SPLIT}-NXT1-COMPLETE-{n}",
        "carrier_lock_key": CARRIER,
        "split_role": parent_roster["split_role"],
        "subset_of": {"roster_id": PARENT_SPLIT, "relpath": PARENT_ROSTER, "sha256": _sha(PARENT_ROSTER), "split_identity_hash": parent_roster["split_identity_hash"],
                      "items": len(parent_roster["items"])},
        "selection_rule": ("every row the stopped attempt COMPLETED (its trace's complete set, equal to its checkpoint's complete set), in the parent roster's order; "
                           "selected by completion alone -- no label, score, transcript or output was read"),
        "stopped_attempt": {"run_id": RUN, "attempt_id": PRED, "trace_sha256": info["trace_sha256"], "checkpoint_sha256": info["checkpoint_sha256"]},
        "items": items, "count": n,
        "audio_seconds_total": round(sum(float(i["audio_seconds"]) for i in items), 9),
        "split_identity_hash": _split_hash([i["sample_id"] for i in items]),
        "ids_sha256": hashlib.sha256("\n".join(i["sample_id"] for i in items).encode("utf-8")).hexdigest(),
        "failed_rows": {"count": len(info["failed_ids"]), "sample_ids": list(info["failed_ids"])},
        "never_started_rows": {"count": len(info["never_started_ids"]), "sample_ids": list(info["never_started_ids"])},
        "parent_rows": len(parent_roster["items"]),
    }
    assert n + doc["failed_rows"]["count"] + doc["never_started_rows"]["count"] == doc["parent_rows"]
    return doc


def subset_runtime_view(parent_view: dict, rows: dict, name: str) -> tuple[dict, dict]:
    """The Fold B runtime view restricted to the complete rows: items byte-identical and in the parent's order, a new split name, the split identity recomputed
    over the kept ids, the source binding the hash of the selection receipt, and the view hash recomputed. Mirrors ``data.runtime_subset.build_runtime_subset`` for
    an EXPLICIT id list (that tool ranks by seed; this selection is by completion)."""

    unsigned = {k: v for k, v in parent_view.items() if k != "runtime_view_sha256"}
    if parent_view.get("runtime_view_sha256") != _content_hash(unsigned):
        raise SystemExit("the parent runtime view's own hash differs")
    keep = [i["sample_id"] for i in rows["items"]]
    by_id = {i["sample_id"]: i for i in parent_view["items"]}
    if any(sid not in by_id for sid in keep):
        raise SystemExit("a complete row is not in the parent runtime view")
    items = [copy.deepcopy(item) for item in parent_view["items"] if item["sample_id"] in set(keep)]
    receipt = {
        "schema": "saea-runtime-subset-receipt-v3", "parent_runtime_view_sha256": parent_view["runtime_view_sha256"],
        "selection": "explicit-completed-rows-v1", "roster_receipt": COMPLETE_ROWS, "sample_ids": keep, "count": len(keep),
        "contacts": {"model": 0, "tool": 0, "scorer": 0, "gpu": 0},
    }
    view = copy.deepcopy(unsigned)
    view.update(items=items, count=len(items), split_name=name, split_identity_hash=_split_hash(keep), source_binding_sha256=_content_hash(receipt),
                audio_seconds_total=round(sum(float(i["audio_seconds"]) for i in items), 9))
    view["runtime_view_sha256"] = _content_hash(view)
    return view, receipt


# ---------------------------------------------------------------------------------------------------------------------------------------
# 2. the cell
# ---------------------------------------------------------------------------------------------------------------------------------------


def names(n: int) -> dict:
    return {"dataset": f"slurp-speech-native-evo-fold-b-nxt1-complete-{n}", "split": f"{PARENT_SPLIT}-NXT1-COMPLETE-{n}"}


def _note(rows: dict, info: dict) -> str:
    n = rows["count"]
    return (
        f"Cell NXT-R1 SEAL-ONLY COMPLETION ({OWNER_BASIS}). The column attempt {PRED} of run {RUN} (flight commit {FLIGHT_COMMIT}, started {STARTED_AT}) completed "
        f"{n:,} of the {rows['parent_rows']:,} Fold B rows ({info['attempt_record']['calls']:,} contacts, {info['attempt_record']['audio_seconds']:,.1f} s repeated speech) "
        f"and STOPPED at {STOP_AT} on {FAILURE_ERROR!r}. Root cause (docs/readiness/{Path(RD).name}/README.md): in one row the non-delivering both-off arm's no-think Solver "
        "contact ended on finish_reason length at its 1,024-token cap; FrozenCoreRoleFiniteCompletionError left the Solver fan-out, so the twin and the delivering arm never "
        "ran for that row, the episode took its deliver-latest-or-abstain disposition and the final assembly raised for the first branch with no Solver record. The harness fix "
        "(a finite completion on a NON-delivering branch is recorded as an ABSENT column and the fan-out continues; the delivering arm keeps its fail-closed path) is on "
        f"master. This attempt ({SO}, FIT identity {FSO}) declares resume_from the stopped attempt by its trace sha256 {info['trace_sha256']}; the roster is fixed to the "
        f"{n:,} complete rows (dataset fragment {names(n)['dataset']}, split {names(n)['split']}), so the union covers the roster and core.flight.runtime sets is_seal_only: zero new "
        "model contacts, no server, no slot, no lease; core.flight.cli seal-only seals the manifest (I7r binds every kept row to the predecessor trace) and runs the one "
        f"official finalize job. The failing row ({len(info['failed_ids'])}) and the {len(info['never_started_ids'])} rows the attempt never started are reported by count, "
        "never scored. THIS IS THE COLUMN'S ONE root-diagnosed recovery re-registration already spent by rec1 (a Windows restart); it is a completion of rec1, not a third flight: "
        "a failure of it closes the cell."
    )


def derive_dataset(rows: dict, nm: dict) -> tuple[dict, dict, str]:
    parent = _load(f"configs/dataset/{PARENT_DATASET}.json")
    view, receipt = subset_runtime_view(parent, rows, nm["split"])
    _dump(f"configs/dataset/{nm['dataset']}.json", view)
    return view, receipt, _sha(f"configs/dataset/{nm['dataset']}.json")


def derive_baseline(rows: dict, info: dict) -> None:
    doc = _load(f"configs/baseline/{SPEC['parent_baseline']}.json")
    assert doc["native_contact_fit"]["run_id"] == FIT_RUN
    doc["native_contact_fit"]["attempt_id"] = FSO
    doc["what_this_is"] = (
        f"{_note(rows, info)} This baseline is configs/baseline/{SPEC['parent_baseline']}.json byte for byte except native_contact_fit.attempt_id (a fresh seal-only FIT "
        "identity that records no contact) and this note. The parent's own note, verbatim: " + str(doc.get("what_this_is", ""))
    )
    _dump(f"configs/baseline/{BASE}.json", doc)


def _requirement(requirements, predicate, what: str) -> dict:
    found = [r for r in requirements if r.get("kind") == "preparation" and predicate(r)]
    assert len(found) == 1, what
    return found[0]


def derive_experiment(rows: dict, info: dict, nm: dict, view: dict) -> None:
    doc = _load(f"configs/experiment/{SPEC['parent_cell']}.json")
    cell = doc["cells"][0]
    assert cell["run_id"] == RUN and cell["attempt_id"] == PRED
    requirements = cell["readiness"]["requirements"]
    agreement = copy.deepcopy(_requirement(requirements, lambda r: "EXEMPLAR-AGREEMENT" in r.get("relpath", ""), "agreement"))
    supply = copy.deepcopy(_requirement(requirements, lambda r: r.get("relpath", "").startswith(f"prepared/{RUN}/phase-supply-v"), "supply"))
    supply["reason"] = (
        f"This cell's prepared first-phase Perception supply, rebuilt model-free by scripts/flights/repin_cell.py under the SAME run id for the {rows['count']:,}-row "
        f"roster (the parent's {rows['parent_rows']:,}-row supply is the previous pin, NARROWED: the rebuilt output legitimately differs, so the seal-only flip passes "
        "--allow-output-change, the roster-narrowing precedent of scripts/flights/batch/roll1_repin_arm.sh; the pin is never read by the seal-only path, which makes no "
        "contact). Zero model, tokenizer, encoder, scorer or server contact."
    )
    new_cell = {}
    for key, value in cell.items():
        if key == "allowed_execution_stages":
            new_cell[key] = ["check", "prepare-supply", "seal-only"]
        elif key == "attempt_id":
            new_cell[key] = SO
        elif key == "baseline_fragment":
            new_cell[key] = BASE
        elif key == "cell_id":
            new_cell[key] = CELL
        elif key == "dataset_fragment":
            new_cell[key] = nm["dataset"]
        elif key == "readiness":
            new_cell[key] = {
                "reason": (
                    f"{_note(rows, info)} HELD: root countersigns the seal-only clauses on the arm's generation and FIT rows and the row {PROOF_RUN}, mints {DEC_RELPATH} "
                    f"(decision id {DEC_ID}) with scripts/flights/nx/nxt_r1_sealonly_mint_receipt.py, and flips with scripts/flights/batch/flip_package_ext4.sh through "
                    "scripts/flights/nx/nxt_r1_sealonly_flip.sh. Nothing here authorises a flight, a readiness flip or an admission entry."
                ),
                "requirements": [agreement, supply],
                "state": "held",
            }
        elif key == "run_id":
            new_cell["resume_from"] = {"attempt_id": PRED, "trace_sha256": info["trace_sha256"]}
            new_cell[key] = RUN
        else:
            new_cell[key] = copy.deepcopy(value)
    doc["cells"] = [new_cell]
    doc["date"] = DATE
    doc["failure_policy"] = (
        "Stop and preserve on the first failure. No automatic restart, replay, row filtering beyond the registered complete-row roster, role-graph, prompt, knowledge, "
        "geometry or cap change. THIS registration is the SEAL-ONLY completion of the rec1 column attempt (every row it carries is complete in its trace; zero model contacts), "
        f"proposed under {OWNER_BASIS}. A failure of it CLOSES cell NXT-R1: no further registration. A partial manifest is never scored and never read."
    )
    doc["fragment_kind"] = f"saea-{EXP}"
    doc["purpose"] = f"{_note(rows, info)} THE PARENT'S PURPOSE, UNCHANGED: {doc['purpose']}"
    doc["generation_budget"]["definition"] = (
        "RUN-CUMULATIVE: the seal-only attempt and its predecessors share one run id, so core.attempts.AttemptStore.prior_actual_usage sums every attempt file under the run id "
        f"and the gate holds that sum against the plan ceiling {doc['generation_budget']['cap']:,} (invariants I3/I6). The predecessors durably spent "
        f"{info['attempt_record']['calls']:,} contacts (rec1) plus the first attempt's recorded spend; this attempt flies 0 rows (seal-only), so the run-cumulative total does "
        "not move. " + doc["generation_budget"]["definition"]
    )
    population = dict(doc["population"])
    population.update({
        "count": rows["count"], "dataset_fragment": nm["dataset"], "split_identity_hash": view["split_identity_hash"],
        "decision_population": (
            f"TRAIN Fold B ({PARENT_SPLIT}) restricted to the {rows['count']:,} rows the stopped column attempt COMPLETED ({rows['roster_id']}, {COMPLETE_ROWS}); discovery "
            "role, rollout-exposed, never a test claim (owner decisions 28 and 86). A strict subset of the 1,080-row roster of the 268-B read, selected by completion alone."
        ),
        "roster_receipt": COMPLETE_ROWS,
    })
    doc["population"] = population
    doc["populations"] = [{"dataset_fragment": nm["dataset"], "ids": [i["sample_id"] for i in rows["items"]]}]
    doc["split_id"] = nm["split"]
    _dump(f"configs/experiment/{EXP}.json", doc)


# ---------------------------------------------------------------------------------------------------------------------------------------
# 3. the package
# ---------------------------------------------------------------------------------------------------------------------------------------


def _abort(rows: dict, info: dict) -> dict:
    record = info["attempt_record"]
    return {
        "error": FAILURE_ERROR, "stopped_at_utc": STOP_AT, "started_at_utc": STARTED_AT, "flight_commit": FLIGHT_COMMIT,
        "attempt_state": record["state"], "calls": record["calls"], "audio_seconds": record["audio_seconds"],
        "complete_rows": rows["count"], "failed_rows": rows["failed_rows"]["count"], "never_started_rows": rows["never_started_rows"]["count"],
        "failed_row_sample_ids": rows["failed_rows"]["sample_ids"],
        "contacts_of_the_failing_row": record["calls"] - rows["count"] * fam.CONTACTS_PER_ROW,
        "failing_stage": "rails.runner._invoke_native_role_episode final assembly (level-2 Solver column fold) after the Solver fan-out",
        "root_cause": (
            "the first-visit Solver fan-out (rails/runner.py -> reproduction/ojw/native_supply_variants.run_perception_branch_solver_arms) invokes the five branches in "
            "declared order, the delivering arm LAST; the third contact (both-off, enable_thinking false, max_tokens 1024) ended on finish_reason 'length'; "
            "FrozenCoreRoleFiniteCompletionError propagated out of the whole fan-out (workflow log 17:59:57-04:00: graph_vertex_ability_error on node solver_0_role, "
            "'metered completion is non-authoritative because finish_reason is length'), the row had made 8 contacts (5 Perception + 3 Solver) not 10, "
            "native_episode took its deliver-latest-or-abstain disposition, and the level-2 fold found no Solver record for the first branch without one (both-off)"),
        "evidence": "campaign log lines 140542-142170 (workflow error and traceback); trace sample-execution-timing record of the failing row (status failed, error_type RailsRunnerError, "
                    "admission_index 1014 of 1080); 10,298 = 1,029 x 10 + 8 contacts; 0 of 2,058 earlier no-think Solver contacts reached the cap (max completion 66 tokens)",
        "fix": ("fix: a non-delivering level-2 branch whose Solver contact ends on a finite completion is recorded as an absent column, not fatal "
                "(branch sonnet/nxt1-sealonly: run_perception_branch_solver_arms branch_absent seam, receipt keys solver_absent / absent_reason, bundle I7v absent-column "
                "check against the recorded wire finish_reason, column renderer = canonical empty answer, readers count absent rows, sign-off condition absent_columns == 0)"),
    }


def _budget(rows: dict, info: dict) -> dict:
    cap_calls, cap_audio = fam.generation_calls("arm"), fam.cell_audio_cap("arm")
    prior = sum(p["contacts_spent"] for p in fam.RECOVERIES["arm"]["predecessors"])
    return {
        "kept_rows": rows["count"], "flown_rows": 0, "kept_from": {PRED: rows["count"]}, "seal_only": True, "flown_worst_case_calls": 0,
        "run_cumulative_actual_calls": info["attempt_record"]["calls"] + prior,
        "run_cumulative_actual_breakdown_calls": {PRED: info["attempt_record"]["calls"],
                                                  fam.RECOVERIES["arm"]["predecessor_attempt_id"]: prior},
        "run_cumulative_actual_audio_seconds_rec1": round(info["attempt_record"]["audio_seconds"], 1),
        "cap_calls": cap_calls, "cap_audio_seconds": cap_audio, "headroom_calls": cap_calls - (info["attempt_record"]["calls"] + prior),
    }


def _replay_proof(replay: dict, code_commit: str, replay_at: str, info: dict, rows: dict) -> dict:
    attempts = replay["attempts"]
    assert len(attempts) == 1 and attempts[0]["attempt_id"] == PRED and attempts[0]["trace_sha256"] == info["trace_sha256"], "the replay names another attempt or trace"
    a = attempts[0]
    return {
        "schema": "saea-resume-replay-proof-v1",
        "tool": f"scripts/analysis/replay_seal_consistency.py --experiment {SPEC['parent_cell']} --run-id {RUN} --predecessor {PRED}:{info['trace_sha256']}",
        "gate": "scripts/checks/resume_prelaunch_gate_check.py (via scripts/flights/batch/resume_prelaunch_gate.sh) on this cell, re-run by the chain and by the driver's prelaunch "
                "on the flight commit",
        "run_at_utc": replay_at,
        "predecessor_attempts": [{
            "attempt_id": PRED, "trace_sha256": info["trace_sha256"], "samples_started": a["samples_started"], "complete": a["complete"], "incomplete": a["incomplete"],
            "rows_checked": a["rows_checked"], "rows_failing": a["rows_failing"], "rows_with_perception_branches": a.get("rows_with_perception_branches"),
            "rows_with_deliver_normaliser": a.get("rows_with_deliver_normaliser"), "perception_branch_note_parse_status": a.get("perception_branch_note_parse_status"),
        }],
        "rows_checked": replay["rows_checked_total"], "rows_failing": replay["rows_failing_total"], "sealed_twice": replay["union"]["sealed_twice"],
        "union_complete_rows": replay["union"]["complete_rows"],
        "checker_sha256": _sha("scripts/analysis/replay_seal_consistency.py"), "resume_py_sha256": replay["resume_py_sha256"], "code_commit": code_commit,
        "model_contacts": replay["model_contacts"],
        "note": ("Model-free and read-only over a scratch COPY of the stopped attempt's trace (sha256 verified identical to the data root's), assets read through symlinks to the "
                 "data root: every complete row rendered through the real seal stage and re-checked against I7 / I7n / I7v (including the v5 thinking-policy wire check and "
                 "the absent-column check, which the replay tool could not see before the 2026-10-15 fix) one row at a time; no row fails and no sample is sealed twice. The "
                 "driver's prelaunch replay gate re-runs the same check at launch on the flight commit."),
    }


def _plan(parent_plan: str, ident, *, kind: str, protocol_sha: str, route: str, extra: dict, rows: dict, view: dict) -> dict:
    doc = _load(f"{PARENT_RD}/{parent_plan}")
    doc["cell"] = CELL
    doc["experiment"] = EXP
    doc["composed_config_hash"] = ident.config_hash
    ep = doc["execution_plan"]
    ep["protocol_hash"] = ident.protocol_hash
    ep["run_id"] = RUN if kind == "generation" else FIT_RUN
    ep["attempt_id"] = SO if kind == "generation" else FSO
    ep["split_identity_hash"] = view["split_identity_hash"]
    doc["protocol_document"] = {"relpath": f"{RD}/protocol-registered-v1.json", "sha256": protocol_sha}
    pin = ident.prepared_phase_supply
    doc["prepared_phase_supply"] = {
        "relpath": pin.relpath if pin else None, "sha256": pin.sha256 if pin else None,
        "note": "INHERITED pin of the 1,080-row parent; the flip rebuilds it for the narrowed roster under the same run id with --allow-output-change (roster narrowing). "
                "The seal-only path never reads it.",
    }
    doc["execution_route"] = route
    doc["preparation_base_commit"] = _head()
    doc["registered_at_utc"] = REGISTERED_AT
    doc["source_tree"] = SOURCE_TREE
    doc["status"] = STATUS
    doc["rows"] = rows["count"]
    doc["roster"] = {"roster_id": rows["roster_id"], "relpath": COMPLETE_ROWS, "rows": rows["count"], "split_identity_hash": view["split_identity_hash"],
                     "subset_of": PARENT_SPLIT, "parent_rows": rows["parent_rows"]}
    doc.update(extra)
    return doc


def _registration() -> dict:
    return {"registered_at_utc": REGISTERED_AT, "source_tree": SOURCE_TREE, "owner_basis": OWNER_BASIS, "decision_receipt": DEC_RELPATH, "decision_id": DEC_ID}


def derive_package(rows: dict, info: dict, nm: dict, view: dict, replay: dict, code_commit: str, replay_at: str) -> dict:
    ident = _identity(EXP, CELL)
    proof = _replay_proof(replay, code_commit, replay_at, info, rows)
    assert (proof["rows_checked"], proof["rows_failing"], proof["sealed_twice"], proof["union_complete_rows"]) == (rows["count"], 0, 0, rows["count"]), proof
    budget = _budget(rows, info)
    abort = _abort(rows, info)
    resume_from = {"attempt_id": PRED, "trace_sha256": info["trace_sha256"]}
    parent_protocol = f"{PARENT_RD}/protocol-registered-v1.json"
    protocol = {
        "schema": "saea-registered-protocol-v1", "protocol_id": "slurp-nxt-r1-thinking-policy-fold-b-sealonly-protocol-v1", "status": STATUS,
        "registered_at_utc": REGISTERED_AT, "source_tree": SOURCE_TREE, "study_commit_at_registration": _head(),
        "parent_protocol": {"relpath": parent_protocol, "sha256": _sha(parent_protocol),
                            "rule": "Everything the parent fixes -- the question, the five arms, the node words, the twin null, the floors, the prohibitions -- stands unchanged "
                                    "and is not re-litigated, EXCEPT the roster: n is the complete-row count, and the failing and never-started rows are reported by count."},
        "owner_basis": OWNER_BASIS, "abort": abort,
        "seal_only_completion": {
            "mechanism": ("resume_from the stopped attempt by trace sha256 (mode A); every roster row is complete in its trace, so is_seal_only; core.flight.cli seal-only "
                          "seals the manifest under I7r and runs the one official finalize job; zero model contacts, no server, no slot, no lease"),
            "why_not_mode_b": ("a checkpoint (mode B) resume pins the code identity of runtime.py / rails/runner.py / core/row_checkpoint.py; the absent-column fix changes "
                               "rails/runner.py by design, so the checkpoint would be refused. Its whole-file sha256 is recorded as corroboration only."),
            "stopped_attempt_checkpoint_sha256": info["checkpoint_sha256"], "resume_replay_proof": proof,
        },
        "roster": {"roster_id": rows["roster_id"], "relpath": COMPLETE_ROWS, "rows": rows["count"], "split_identity_hash": view["split_identity_hash"],
                   "subset_of": {"roster_id": PARENT_SPLIT, "rows": rows["parent_rows"], "split_identity_hash": rows["subset_of"]["split_identity_hash"]},
                   "failed_rows": rows["failed_rows"]["count"], "never_started_rows": rows["never_started_rows"]["count"]},
        "recovery_counter": ("The column's rec1 (a Windows restart) is its one root-diagnosed recovery re-registration, already spent. This is a SEAL-ONLY completion of the rec1 "
                             "attempt's complete rows -- no row is flown -- and a failure of it closes cell NXT-R1."),
        "cells": {"seal-only": {"cell": CELL, "experiment": EXP, "run_id": RUN, "attempt_id": SO, "fit_run_id": FIT_RUN, "fit_attempt_id": FSO,
                                "composed_config_hash": ident.config_hash, "protocol_hash": ident.protocol_hash, "resume_from": resume_from,
                                "dataset_fragment": nm["dataset"], "split_id": nm["split"]}},
        "claim_ceiling": "nominated (unchanged); claims_benefit false", "rows": {"kept": rows["count"], "flown": 0}, "budget": budget,
    }
    protocol_sha = _dump(f"{RD}/protocol-registered-v1.json", protocol)
    route = (f"core.flight.cli seal-only on the seal-only cell (--experiment {EXP} --cell {CELL}), through the batch driver as a kind=seal-only step "
             "(scripts/flights/nx/batch_chain_nxt_r1_sealonly.sh): preflight's gates (the resume prelaunch replay gate included), then zero-work preprocess / serve / run_phases "
             f"(no packet promotion, no server, no slot, no lease), the seal of the {rows['count']:,}-row manifest and the one official finalize job. No smoke, no campaign plan.")
    gen_sha = _dump(f"{RD}/generation-plan-registered-v1.json", _plan(
        "generation-plan-registered-rec1-v1.json", ident, kind="generation", protocol_sha=protocol_sha, route=route, rows=rows, view=view,
        extra={"resume_from": dict(resume_from), "resume_budget": budget, "resume_replay_proof": proof, "seal_only_registration": _registration()}))
    fit_sha = _dump(f"{RD}/fit-plan-registered-v1.json", _plan(
        "fit-plan-registered-rec1-v1.json", ident, kind="fit", protocol_sha=protocol_sha, rows=rows, view=view,
        route=("The shared core.flight.cli FIT path under this cell's own native_contact_fit ids (the rec1 FIT run id, a new attempt). SEAL-ONLY: the seal-only attempt never "
               f"builds the native contact FIT gate (run_phases is a zero-work receipt), so this FIT identity records no contact; it is fresh ({FSO}, unused on the data root "
               "at registration) because validate_native_contact_fit_config requires the block and no FIT attempt id that already holds evidence is ever reused."),
        extra={"seal_only_registration": _registration()}))

    recipe = _load(f"{PARENT_RD}/analysis-recipe-v1.json")
    recipe["recipe_id"] = "slurp-nxt-r1-thinking-policy-fold-b-sealonly-read-v1"
    recipe["registered_at_utc"] = REGISTERED_AT
    recipe["roster"] = {"relpath": COMPLETE_ROWS, "roster_id": rows["roster_id"], "rows": rows["count"], "split_identity_hash": view["split_identity_hash"]}
    recipe["run_ids"] = {**recipe["run_ids"], "arm_attempt": SO, "fit": FIT_RUN}
    recipe["parent_recipe"] = {"relpath": f"{PARENT_RD}/analysis-recipe-v1.json", "sha256": _sha(f"{PARENT_RD}/analysis-recipe-v1.json"),
                               "rule": "unchanged except the sealed attempt id, the roster (the complete rows) and the reading rule below"}
    recipe["recovery_reading_rule"] = (
        f"The five arm columns are read from the seal-only attempt {SO}'s sealed manifest: all {rows['count']:,} rows kept from {PRED} under I7r custody, 0 flown. The manifest's "
        f"predecessor_attempt block must name trace {info['trace_sha256']}; refuse otherwise. The paired contrasts run at n = {rows['count']:,} (the complete rows; utterance-"
        "cluster bootstrap, 10,000 draws, seed 20261013, unchanged). The READ reports, beside the table and by COUNT only: the failing row "
        f"({rows['failed_rows']['count']}: a both-off Solver delivery failure, never scored, not in n), the {rows['never_started_rows']['count']} never-started rows, and the absent "
        "Solver columns per arm (a column whose Solver contact ended on a finite completion is that arm's delivery failure: scored as the canonical empty answer, zero for that "
        "row's arm, counted in `absent_rows`). The delivering arm's column is never absent. Node words and floors are the parent's (floors set at n = 1,080 are quoted, not "
        "rescaled; the reader prints the CI)."
    )
    recipe["stages"] = {
        "1_columns": ("bash scripts/flights/nx/nxt_r1_read.sh sealonly-columns: stage3_rollout_score --mode perception-branches over the seal-only attempt with --roster " + COMPLETE_ROWS),
        "2_read": "bash scripts/flights/nx/nxt_r1_read.sh sealonly-read: refuses unless the READ row is root countersigned (its seal-only clause included)",
    }
    recipe_sha = _dump(f"{RD}/analysis-recipe-v1.json", recipe)

    parent_facts = _load(f"{PARENT_RD}/registered-facts-v1.json")
    measurement = copy.deepcopy(parent_facts["stage3_measurement"][RUN])
    measurement.update(rows=rows["count"], read_roster=rows["roster_id"], claims_benefit=False)
    measurement["note"] = (
        f"SEAL-ONLY n = {rows['count']:,} of the {rows['parent_rows']:,} registered rows (the rows the stopped attempt completed; {rows['failed_rows']['count']} failing and "
        f"{rows['never_started_rows']['count']} never-started rows are reported by count). A per-node attribution, not a benefit claim. " + measurement["note"]
    )
    facts = {
        "schema": "saea-registered-facts-v1", "registered_at_utc": REGISTERED_AT, "study_commit_at_registration": _head(),
        "parent_registered_facts": f"{PARENT_RD}/registered-facts-v1.json",
        "_note": ("The seal-only completion's stage3_measurement block: the parent's NX-T R1 arm block with rows = the complete-row count and read_roster = the complete-row "
                  "roster; claims_benefit stays false. Nothing else about the measurement moves."),
        "stage3_measurement": {RUN: measurement},
        "seal_only": {"cell": CELL, "attempt_id": SO, "fit_attempt_id": FSO, "resume_from": resume_from, "stopped_attempt_checkpoint_sha256": info["checkpoint_sha256"],
                      "abort": abort, "resume_replay_proof": proof, "composed_config_hash": ident.config_hash, "protocol_hash": ident.protocol_hash,
                      "roster": {"roster_id": rows["roster_id"], "relpath": COMPLETE_ROWS, "rows": rows["count"], "split_identity_hash": view["split_identity_hash"],
                                 "ids_sha256": rows["ids_sha256"], "dataset_fragment": nm["dataset"]}},
    }
    facts_sha = _dump(f"{RD}/registered-facts-v1.json", facts)

    parent_draft = _load(f"{PARENT_RD}/root-admission-draft-v1.json")
    draft = copy.deepcopy(parent_draft)
    draft["_draft_note"] = ("A DRAFT for root to mint on the data root with scripts/flights/nx/nxt_r1_sealonly_mint_receipt.py (status decided, recorded_at_utc stamped, "
                            "antecedents re-hashed, never overwrites).")
    draft["decision_id"] = DEC_ID
    draft["eligible_run_ids"] = [RUN, FIT_RUN]
    draft["eligible_attempt_ids"] = [SO]
    draft["fit_attempt_ids"] = {FIT_RUN: FSO}
    draft["resume_from"] = dict(resume_from)
    draft["resume_replay_proof"] = proof
    draft["decision"] = (f"Seal the NX-T R1 column {RUN} as the SEAL-ONLY completion of its rec1 attempt: attempt {SO} keeps the {rows['count']:,} complete rows of {PRED} "
                         f"(trace {info['trace_sha256'][:8]}...) with ZERO new model contacts through core.flight.cli seal-only, finalizes it with the one official score job, and "
                         f"reads it by the READ row {READ_RUN} at n = {rows['count']:,}.")
    draft["cell_kind"] = (f"NX-T R1 SEAL-ONLY COMPLETION: a new attempt {SO} (FIT attempt {FSO}, records no contact) under the SAME run id {RUN}, resume_from [{PRED}]; the roster is "
                          f"fixed to the {rows['count']:,} complete rows ({rows['roster_id']}); the union covers it, so nothing is flown. Claim ceiling 'nominated', "
                          "claims_benefit false.")
    draft["authorization_basis"] = (OWNER_BASIS + ". The parent authorization basis stands: " + str(parent_draft["authorization_basis"]))
    draft["retry_basis"] = (f"The rec1 column attempt flew {rows['count']:,} complete rows ({info['attempt_record']['calls']:,} calls) and stopped on a non-delivering arm's finite "
                            "completion (root cause named to a component and fixed). Its complete rows are in its trace; the seal-only completion keeps them and flies nothing.")
    budget_block = draft.setdefault("budget", {})
    budget_block.pop("smoke", None)
    budget_block["resume"] = dict(budget, note="plan budgets are run-cumulative; the seal-only completion adds none")
    draft["not_authorized"] = list(draft.get("not_authorized", [])) + [
        f"flying any row of {RUN} again (the seal-only completion makes zero model contacts)",
        "any core.flight.cli worker or campaign run of the seal-only cell (it allows check, prepare-supply and seal-only only)",
        f"writing, moving or compressing anything under the stopped attempt's directory {PRED}",
    ]
    draft.pop("supersedes_receipt", None)
    draft["population"] = {"count": rows["count"], "split_identity_hash": view["split_identity_hash"], "split_role": rows["split_role"], "roster_id": rows["roster_id"],
                           "subset_of": PARENT_SPLIT, "fold_a_contact_authorized": False, "test_contact_authorized": False,
                           "partition": f"TRAIN Fold B, the {rows['count']:,} complete rows of {rows['parent_rows']:,}; {rows['count']:,} kept from the stopped attempt, 0 flown"}
    draft["recovery"] = {"stopped_attempt": abort}
    draft.pop("recovery_budget", None)
    antecedents = {}
    antecedents["parent_registration_draft"] = {"path": f"{PARENT_RD}/root-admission-draft-v1.json", "sha256": _sha(f"{PARENT_RD}/root-admission-draft-v1.json")}
    antecedents["parent_decision_receipt"] = {"relpath": f"coordination/{fam.PKG_NAME}/root-admission-v1.json", "decision_id": fam.DECISION_ID,
                                              "status": "stands; it admitted the column attempt (rec1), which stopped"}
    antecedents["sealonly_protocol"] = {"path": f"{RD}/protocol-registered-v1.json", "sha256": protocol_sha}
    antecedents["sealonly_analysis_recipe"] = {"path": f"{RD}/analysis-recipe-v1.json", "sha256": recipe_sha}
    antecedents["sealonly_registered_facts"] = {"path": f"{RD}/registered-facts-v1.json", "sha256": facts_sha}
    antecedents["sealonly_generation_plan"] = {"path": f"{RD}/generation-plan-registered-v1.json", "sha256": gen_sha}
    antecedents["sealonly_fit_plan"] = {"path": f"{RD}/fit-plan-registered-v1.json", "sha256": fit_sha}
    antecedents["sealonly_complete_rows"] = {"path": COMPLETE_ROWS, "sha256": _sha(COMPLETE_ROWS)}
    antecedents["sealonly_preregistration"] = {"path": PREREG, "sha256": None}
    antecedents["sealonly_readme"] = {"path": f"{RD}/README.md", "sha256": None}
    antecedents["derive_script"] = {"path": "scripts/flights/nx/nxt_r1_sealonly_derive_cell.py", "sha256": _sha("scripts/flights/nx/nxt_r1_sealonly_derive_cell.py")}
    antecedents["registration_base_commit"] = _head()
    draft["antecedents"] = antecedents
    draft["registered_hashes"] = {"seal-only": {"composed_config": ident.config_hash, "protocol": ident.protocol_hash}}
    draft["status"] = "DRAFT-NOT-MINTED"
    draft["recorded_at_utc"] = None
    _dump(f"{RD}/root-admission-sealonly-draft-v1.json", draft)
    return {"ident": ident, "protocol_sha": protocol_sha, "proof": proof, "abort": abort, "budget": budget, "gen_sha": gen_sha, "fit_sha": fit_sha, "facts_sha": facts_sha}


# ---------------------------------------------------------------------------------------------------------------------------------------
# 4. the ledger drafts, the countersign texts, the README and the preregistration (text)
# ---------------------------------------------------------------------------------------------------------------------------------------


def ledger_texts(rows: dict, info: dict, nm: dict, view: dict, art: dict) -> dict:
    """The DRAFT seal-only clause texts and rows. The clauses are appended to the arm's two existing rows when root countersigns (the P-SV-1 form); the one new row is
    the model-free replay proof."""

    n = rows["count"]
    ident, proof = art["ident"], art["proof"]
    head = (f"SEAL-ONLY COMPLETION REGISTERED (DRAFT, root countersignature pending; {OWNER_BASIS}) {DATE} by the engineering agent (Claude Sonnet 5.5, branch "
            f"sonnet/nxt1-sealonly): attempt {SO} under the SAME run id, resume_from the stopped attempt {PRED} (trace {info['trace_sha256']}, {n:,} complete rows); the "
            f"roster is fixed to those rows (dataset fragment {nm['dataset']}, split {nm['split']}, split identity {view['split_identity_hash']}, a strict subset of "
            f"{PARENT_SPLIT} {rows['subset_of']['split_identity_hash']}), so it seals through core.flight.cli seal-only with no server, slot or lease and runs the one official "
            f"finalize job. The stop: {FAILURE_ERROR!r} at {STOP_AT} after {info['attempt_record']['calls']:,} calls; root cause and fix in the package README. The failing row "
            f"({rows['failed_rows']['count']}) and the {rows['never_started_rows']['count']} never-started rows are reported by count, never scored. Replay proof "
            f"({PROOF_RUN}): {proof['rows_checked']:,} rows checked, {proof['rows_failing']} failing, {proof['sealed_twice']} sealed twice. Run-cumulative spend does not move "
            f"({art['budget']['run_cumulative_actual_calls']:,} calls of {art['budget']['cap_calls']:,} planned); this completion adds 0. CONSUMED STAYS no until the seal. "
            f"Composed config {ident.config_hash}, protocol {ident.protocol_hash} (the re-pin tool rewrites both at the flip). Package {RD}.")
    gen_clause = head + (f" SPLIT IDENTITY: root, when countersigning, replaces this row's split identity hash column with {view['split_identity_hash']} (the complete-row subset) so "
                         "the plan's split identity and the row agree; the registered ceilings (calls, audio, GPU) are kept.")
    fit_clause = head.replace("SEAL-ONLY COMPLETION REGISTERED", "SEAL-ONLY COMPLETION REGISTERED (FIT identity)") + (
        f" This FIT identity ({FIT_RUN} / {FSO}) records NO contact; the FIT cap stays structural. Split identity as for the generation row.")
    proof_notes = (
        f"REGISTERED WITH ITS RESULT (DRAFT, root countersignature pending) {DATE} by the engineering agent at code commit {proof['code_commit']}, for the seal-only completion of "
        f"the NX-T R1 column: all {n:,} complete rows of {PRED} kept, zero new model contacts. Result (resume_replay_proof in the generation plan): {proof['union_complete_rows']:,} "
        f"complete of {proof['predecessor_attempts'][0]['samples_started']:,} started, {proof['rows_checked']:,} checked, {proof['rows_failing']} failing, "
        f"{proof['predecessor_attempts'][0]['rows_with_perception_branches']:,} rows with perception branches, union {proof['union_complete_rows']:,} complete, "
        f"{proof['sealed_twice']} sealed twice; resume.py sha256 {proof['resume_py_sha256'][:8]}...; model contacts {proof['model_contacts']}. It authorises nothing by itself. "
        "Ids, counts and hashes only.")
    proof_row = rcv.ledger_row(
        proof["run_at_utc"], PROOF_RUN, "model-free-check",
        ("The offline seal-consistency replay the NX-T R1 SEAL-ONLY completion rests on: every complete row of the stopped column attempt's trace rendered through the real seal "
         "stage under the current code and re-checked against I7 / I7n / I7v (v5 thinking-policy wire check and the absent-column check included) one row at a time, plus the "
         "union check (no sample sealed twice)."),
        (f"No model, tokenizer, encoder, scorer, server, GPU or network contact: scripts/analysis/replay_seal_consistency.py (sha256 {proof['checker_sha256'][:8]}...) with "
         f"--predecessor {PRED}:{info['trace_sha256'][:8]}..., read-only over a scratch copy of the recorded trace"),
        f"slurp TRAIN Fold B {n:,} (the recorded trace of the stopped column attempt, {n:,} started rows)", rows["subset_of"]["split_identity_hash"], 0, 0, 0.0,
        "Reads only an already-recorded trace; no new audio, gold, transcript or reference exposure. Prior exposure inherited in full.",
        f"{RD}/generation-plan-registered-v1.json", proof_notes)
    read_clause = (
        f"SEAL-ONLY READING CLAUSE (DRAFT, root countersignature pending) {DATE}: the NX-T R1 read runs over the seal-only attempt {SO} at n = {n:,} (roster {rows['roster_id']}, "
        f"{COMPLETE_ROWS}); the failing row ({rows['failed_rows']['count']}) and the {rows['never_started_rows']['count']} never-started rows are reported by count and never scored; an absent "
        "Solver column is that arm's delivery failure (canonical empty answer, counted). Root countersigns this clause after the seal and before any number is read.")
    table_header = "| " + " | ".join(rcv.LEDGER_COLUMN_NAMES) + " |\n| " + " | ".join("---" for _ in rcv.LEDGER_COLUMN_NAMES) + " |\n"
    return {"head": head, "generation_clause": gen_clause, "fit_clause": fit_clause, "proof_row": proof_row, "proof_notes": proof_notes, "read_clause": read_clause,
            "table_header": table_header}


def write_ledger_and_countersign(rows: dict, info: dict, nm: dict, view: dict, art: dict) -> None:
    t = ledger_texts(rows, info, nm, view, art)
    text = (
        f"# NX-T R1 seal-only completion: DRAFT exposure-ledger entries\n\nNothing here is in `docs/exposure-ledger.md` yet. Root countersigns by appending the two clauses below to the "
        f"notes of the arm's existing rows (`{RUN}`, `{FIT_RUN}`; one run id keeps exactly one row, so the clause is added to the row, not a second row) and by adding the "
        f"one new row (the replay proof) at the end of the ledger, in the P-SV-1 form (commit a842f6703). The arm rows stay `consumed = no` until the seal; "
        f"`scripts/flights/batch/ledger_mark_consumed.py --apply` closes them after it.\n\n"
        f"## Clause for `{RUN}` (generation row)\n\n{t['generation_clause']}\n\n## Clause for `{FIT_RUN}` (FIT row)\n\n{t['fit_clause']}\n\n"
        f"## New row `{PROOF_RUN}`\n\n{t['table_header']}{t['proof_row']}\n\n## Clause for `{READ_RUN}` (READ row; countersigned after the seal, before the read)\n\n{t['read_clause']}\n")
    _write_text(f"{RD}/draft-ledger-rows.md", text)
    texts = {
        "_note": ("Countersign texts for the NX-T R1 seal-only completion: the clause each ledger row gains when root countersigns it (the replacement text of a row's notes is "
                  "the existing notes plus this clause). The proof row is a new row. Replace <UTC timestamp> with the countersign time."),
        "decision_id": DEC_ID, "decision_receipt": DEC_RELPATH,
        "rows": {
            RUN: ("REGISTERED BEFORE CONTACT (root countersigned <UTC timestamp> by root flight operations; "
                  + t["generation_clause"].replace("(DRAFT, root countersignature pending; ", "(", 1) + ")"),
            FIT_RUN: ("REGISTERED BEFORE CONTACT (root countersigned <UTC timestamp> by root flight operations; "
                      + t["fit_clause"].replace("(DRAFT, root countersignature pending; ", "(", 1) + ")"),
            PROOF_RUN: ("REGISTERED WITH ITS RESULT (root countersigned <UTC timestamp> by root flight operations; "
                        + t["proof_notes"].replace("REGISTERED WITH ITS RESULT (DRAFT, root countersignature pending) ", "", 1) + ")"),
            READ_RUN: t["read_clause"],
        },
    }
    _dump(f"{RD}/countersign-row-texts-v1.json", texts)


def write_readme_and_prereg(rows: dict, info: dict, nm: dict, view: dict, art: dict) -> None:
    n = rows["count"]
    rec = info["attempt_record"]
    failed = rows["failed_rows"]["sample_ids"]
    proof = art["proof"]
    readme = f"""# NX-T R1 seal-only completion of the stopped column flight

Registered {DATE} by the engineering agent (Claude Sonnet 5.5, branch `sonnet/nxt1-sealonly`), model-free: zero model, tokenizer, encoder, scorer, server and GPU contact. Derived by
`scripts/flights/nx/nxt_r1_sealonly_derive_cell.py` (decision 58). The shape is the P-SV-1 seal-only completion (`docs/readiness/2026-09-29-slurp-stage3-psv1-fold-b-v1-resume-v1/`),
with two differences: the roster is NARROWED to the rows the stopped attempt completed, and the resume is mode A (trace) because the harness fix moves `rails/runner.py`.
**Not authorised by anything in this package.** The authority is the owner's answer to the coordinator's proposal (decision 320 A: seal-only the complete rows, read them, close the
cell), which was PENDING when this was written.

## What stopped

The column attempt `{PRED}` (run `{RUN}`, flight commit `{FLIGHT_COMMIT}`, started {STARTED_AT}) stopped at {STOP_AT}: `{FAILURE_ERROR}`. Its attempt record reads
`{rec['state']}`, {rec['calls']:,} calls, {rec['audio_seconds']:,.1f} s of repeated speech.

**Counts (corrected against the files).** {n:,} rows are complete in the trace AND in the row checkpoint (the same {n:,} ids); {rows['failed_rows']['count']} row failed; the
other {rows['never_started_rows']['count']} were never started ({n:,} + {rows['failed_rows']['count']} + {rows['never_started_rows']['count']} = {rows['parent_rows']:,}). The brief said
1,030 complete rows and 49 never flown: the 1,030th row is the FAILING one (10,298 contacts = {n:,} x 10 + 8; the checkpoint holds {n:,} row records). The failing row's emitted
trace records were never flushed (the trace buffer flushes a row after its episode settles); only its `sample-execution-timing` record (`status` failed, `error_type`
`RailsRunnerError`, `admission_index` 1,014 of 1,080, queue depth 16, 4 slots) reached the trace, so the failing row's own contact shapes cannot be read from the trace. The
root cause below rests on the campaign log (workflow events) and the contact arithmetic, and says so.

**Root cause (row class: a NON-delivering arm's no-think Solver hit its token cap).**

1. The first-visit Solver fan-out (`rails/runner.py` -> `reproduction/ojw/native_supply_variants.run_perception_branch_solver_arms`) invokes the five branches in declared
   order, `perception-off`, `solver-off`, `both-off`, `both-on-twin`, `both-on` (the delivering arm LAST).
2. In the failing row the THIRD Solver contact (`both-off`: `enable_thinking` false, `max_tokens` 1,024) ended on `finish_reason` `length`. The workflow log shows, for that
   workflow session, `graph_vertex_ability_error` on node `solver_0_role` with `metered completion is non-authoritative because finish_reason is 'length'` ({STOP_AT[:10]} 17:59:57 -04:00 = 21:59:57Z; the campaign then drained its in-flight rows and exited at {STOP_AT})
   after a 25 s request. `FrozenCoreRoleFiniteCompletionError` left the whole fan-out.
3. The row had made 8 contacts (5 Perception + 3 Solver), not 10; the twin and the delivering arm never ran, so **the delivering arm was NOT fine on that row** -- it was lost
   with the failing arm, because the fan-out is sequential and the delivering arm is last.
4. `reproduction/ojw/native_episode.py` took the row's `deliver-latest-or-abstain` disposition (the finite-completion policy), and the final assembly in `rails/runner.py` (the
   level-2 fold, `perception_branch_solver_records.pop`) found no Solver record for the first branch without one (`both-off`; `perception-off` and `solver-off` had theirs):
   `RailsRunnerError`. The campaign then drained its in-flight rows (they completed to 18:32 -04:00).
5. It was a first: across the {n:,} complete rows no no-think Solver contact came near the cap (2,058 `solver-off` / `both-off` Solver contacts, maximum completion 66 tokens, all
   `stop`); the Perception no-think contacts peaked at 116 tokens.

## The fix (merged with this package)

A finite completion on a branch that does NOT deliver is recorded as an ABSENT column and the fan-out continues, so the delivering arm still runs. The delivering arm keeps its
fail-closed path (a finite completion there still ends the row through the finite-completion policy). Receipt: two optional row keys `solver_absent` (true) and `absent_reason`
(`finite-completion:length` / `finite-completion:content_filter`), schema string unchanged, every old receipt verifies unchanged. The bundle (I7v) holds an absent mark against the
recorded wire `finish_reason`. The column renderer scores an absent column as the canonical empty answer (zero for that row's arm in every paired contrast); both NX-T readers print
`absent_rows` per arm and refuse a non-zero score for an absent row; the smoke sign-off conditions gain `absent_columns == 0`. The offline replay tool (the resume prelaunch gate's
checker) could not see the v5 thinking-policy wire check (all {n:,} rows failed it spuriously); it now carries each request's thinking decoding fields and each wire response's
finish_reason. Tests: `tests/unit/test_perception_branch_absent_solver.py`, `tests/unit/test_nxt_columns_absent_reader.py`.

## The completion

| field | value |
| --- | --- |
| experiment / cell | `{EXP}` |
| baseline | `{BASE}` (the parent's bytes except the FIT attempt id and the note) |
| dataset fragment / split | `{nm['dataset']}` / `{nm['split']}` (split identity `{view['split_identity_hash']}`; a strict subset of `{PARENT_SPLIT}` `{rows['subset_of']['split_identity_hash']}`) |
| run id | `{RUN}` (the same run id) |
| attempt | `{SO}` (new) |
| FIT identity | `{FIT_RUN}` / `{FSO}` (fresh; it records no contact) |
| resume_from | `{PRED}`, trace `{info['trace_sha256']}`, {n:,} complete rows |
| checkpoint (corroboration) | `{PRED}` `.rows.ckpt.jsonl` sha256 `{info['checkpoint_sha256']}` |
| allowed stages | `check`, `prepare-supply`, `seal-only` |
| program / arms | unchanged: `{fam.PROGRAM}`, five arms |
| claim ceiling | `nominated`, `claims_benefit` false; `stage3_measurement` rows = {n:,} |

The union of the predecessor's complete rows covers the (narrowed) roster, so `core.flight.runtime` sets `is_seal_only`: zero new model contacts, no server, no slot, no lease.
Run-cumulative spend does not move ({art['budget']['run_cumulative_actual_calls']:,} of {art['budget']['cap_calls']:,} planned calls).

**Replay proof** (`resume_replay_proof` in the generation plan; model-free, on a scratch copy of the trace whose sha256 was verified identical): `replay_seal_consistency.py
--predecessor {PRED}:{info['trace_sha256'][:8]}...` reported {proof['rows_checked']:,} rows checked, {proof['rows_failing']} failing, {proof['sealed_twice']} sealed twice,
{proof['predecessor_attempts'][0]['rows_with_perception_branches']:,} rows with perception branches, exit 0.

## Decisions this registration needs (flagged, not taken)

1. **Split identity.** The narrowed roster has its own split identity (`{view['split_identity_hash'][:12]}...`), and one run id keeps one ledger row: root, when countersigning,
   replaces the arm rows' split-identity column with the subset's hash (the clause says so). If the owner prefers to keep the parent hash, the plan's split identity cannot
   agree with the loaded roster.
2. **`--allow-output-change` at the flip.** The rebuilt phase supply covers {n:,} rows, not {rows['parent_rows']:,}; its output legitimately differs (the roster-narrowing precedent:
   `roll1_repin_arm.sh`). The seal-only path never reads the supply.
3. **Mode A, not mode B.** Mode B (checkpoint) refuses when `rails/runner.py` changed; the fix changes it. The checkpoint hash is recorded as corroboration.

## Sequence (the coordinator's; nothing below has been run)

1. Park the queue with `/home/chao/batch-STOP` while the cell is registered, countersigned and flipped (the flip refuses while a batch runs). Remove batch-STOP just before
   step 6: the seal-only chain REFUSES (exit 8) while it exists and never moves it aside.
2. Run the derive if the package is not committed yet: `python -B scripts/flights/nx/nxt_r1_sealonly_derive_cell.py --data-root $SPEECHRL_DATA_DIR --replay-json R --replay-commit C --replay-at T`.
3. Root countersigns `countersign-row-texts-v1.json` into `docs/exposure-ledger.md` (the two clauses, the proof row; the READ clause after the seal).
4. Mint: `python scripts/flights/nx/nxt_r1_sealonly_mint_receipt.py` (writes `{DEC_RELPATH}` from `root-admission-sealonly-draft-v1.json`).
5. Flip: `bash scripts/flights/batch/flip_package_ext4.sh --flip "scripts/flights/nx/nxt_r1_sealonly_flip.sh" --package {RD} --cells {CELL} --pins-commit-msg <file>`
   (loop form; writes `{fam.SEALONLY_FLIGHT_COMMIT_FILE}`).
6. Chain: `bash scripts/flights/nx/batch_chain_nxt_r1_sealonly.sh` (one `seal-only` step through the batch driver; refuses while `batch-STOP` exists; the resume prelaunch gate
   runs first).
7. Read: `bash scripts/flights/nx/nxt_r1_read.sh sealonly-columns`, then (after the READ row's seal-only clause is countersigned) `bash scripts/flights/nx/nxt_r1_read.sh sealonly-read`.

## Rehearsal (already run; reproducible)

`replay_seal_consistency.py` needs the stopped trace (668 MB) on a scratch data root plus read-only symlinks to the live root's other entries (the v4g delivery normaliser reads
`prepared/` tables): `S=/home/chao/scratch-nxt1-seal; mkdir -p $S/runs/{RUN}/{PRED}; cp --reflink=auto $SPEECHRL_DATA_DIR/runs/{RUN}/{PRED}/{RUN}.trace.jsonl $S/runs/{RUN}/{PRED}/;
for e in $(ls $SPEECHRL_DATA_DIR); do [ "$e" = runs ] || ln -s $SPEECHRL_DATA_DIR/$e $S/$e; done; SPEECHRL_DATA_DIR=$S python -B scripts/analysis/replay_seal_consistency.py --experiment
{SPEC['parent_cell']} --run-id {RUN} --predecessor {PRED}:{info['trace_sha256']} --data-root $S`. About 5 s, CPU only. The resume prelaunch gate (run by the chain) repeats it on the flight commit.

## Not verified here

`core.flight.cli` (check / seal-only), the re-pin tool with the narrowed supply, the batch driver's prelaunch and the sealed bundle's I7r verification were NOT run (no CLI, no
re-pin, no flip is allowed to this agent). What was run: unit tests, `flight_registration_check.py --cell`, `stage3_effect_floor_check.py`, the engineering gates, `compose` and
`compute_cell_identity` on the derived cell, and the offline replay on a scratch copy.
"""
    _write_text(f"{RD}/README.md", readme)
    prereg = f"""# NX-T R1: SEAL-ONLY completion of the stopped column (preregistration note)

Status: **{STATUS}** ({OWNER_BASIS}). Written with zero model, tokenizer, encoder, scorer, server and GPU contacts. No utterance text, transcript, gold label, column value or
model output is printed or persisted: ids, counts and hashes only.

This note addends the NX-T R1 registration [`{Path(PARENT_RD).name}/`]({Path(PARENT_RD).name}/) and its preregistration, which are **not edited**. Everything they fix stands unchanged:
the question (which nodes of the locked Thinking system need thinking), the five arms, the node words against the in-flight twin offset, the floors, the claim ceiling `nominated`
and the prohibitions -- except the roster: n is the number of complete rows.

1. **What stopped.** The rec1 column attempt completed {n:,} of {rows['parent_rows']:,} rows and stopped on a non-delivering arm's finite completion
   ({FAILURE_ERROR}). Root cause and fix: the package README.
2. **The completion.** A new attempt `{SO}` under the same run id, resume_from the stopped attempt by trace sha256 `{info['trace_sha256']}`; the roster is the {n:,} complete rows;
   zero new model contacts; run-cumulative spend unchanged.
3. **Reading.** The paired contrasts run at n = {n:,} (the complete rows). The READ reports by count: the failing row ({rows['failed_rows']['count']}), the
   {rows['never_started_rows']['count']} never-started rows, and the absent Solver columns per arm (an arm's delivery failure, scored as the canonical empty answer).
   Development numbers only (owner decisions 28 and 86); never a test claim; `claims_benefit` false.
4. **Closing.** The cell closes at the seal and the read; there is no further registration.
"""
    _write_text(PREREG, prereg)


# ---------------------------------------------------------------------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------------------------------------------------------------------


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-root", type=Path, required=True, help="READ ONLY: the stopped attempt's trace / checkpoint / attempt record and the cell's pins")
    parser.add_argument("--replay-json", required=True, type=Path, help="the report of scripts/analysis/replay_seal_consistency.py over the stopped attempt")
    parser.add_argument("--replay-commit", required=True, help="the code commit the replay ran at")
    parser.add_argument("--replay-at", required=True, help="the UTC time the replay ran")
    args = parser.parse_args(argv)
    replay = json.loads(args.replay_json.read_text(encoding="utf-8"))
    parent_roster = _load(PARENT_ROSTER)
    parent_ids = [i["sample_id"] for i in parent_roster["items"]]
    info = inspect_predecessor(args.data_root, parent_ids)
    rows = complete_rows_document(info, parent_roster)
    nm = names(rows["count"])
    _dump(COMPLETE_ROWS, rows)
    view, _receipt, _ = derive_dataset(rows, nm)
    assert view["split_identity_hash"] == rows["split_identity_hash"]
    derive_baseline(rows, info)
    derive_experiment(rows, info, nm, view)
    art = derive_package(rows, info, nm, view, replay, args.replay_commit, args.replay_at)
    write_ledger_and_countersign(rows, info, nm, view, art)
    write_readme_and_prereg(rows, info, nm, view, art)
    print(json.dumps({"cell": CELL, "attempt_id": SO, "fit_attempt_id": FSO, "rows": rows["count"], "failed": rows["failed_rows"]["count"],
                      "never_started": rows["never_started_rows"]["count"], "split": nm["split"], "split_identity_hash": view["split_identity_hash"],
                      "composed_config_hash": art["ident"].config_hash, "protocol_hash": art["ident"].protocol_hash, "trace_sha256": info["trace_sha256"],
                      "checkpoint_sha256": info["checkpoint_sha256"], "replay": [art["proof"]["rows_checked"], art["proof"]["rows_failing"], art["proof"]["sealed_twice"]]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
