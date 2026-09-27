"""The ``final-report`` split role: every refusal branch, and the one way past.

Owner decision 99 of 2026-09-22 and owner decision 107 of 2026-09-23
(``docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md``): exactly
ONE complete official SLURP test-split read at the end of Stage 3, with its
preparations registered now and built ahead of time. Section 6.3 of the one-shot
read protocol draft
(``docs/readiness/2026-09-19-slurp-test-split-one-read-protocol-v1-draft.md``)
requires the paired code change these tests cover: a machine role "named for
what it is", never a reuse of ``dev``, admitted only behind a dated owner
allowance.

Two surfaces are covered.

1. ``contracts.plan.require_owner_split_allowance`` / ``ExecutionPlan.validate``
   -- the plan-level authorisation. Every one of its refusals is exercised, plus
   the single acceptance path, plus the two roles that must NOT move
   (``confirmatory`` stays refused verbatim; ``discovery``/``dev`` may not carry
   an allowance).
2. ``contracts.gate_exposure._ExposureAndCarrierMixin
   ._require_final_report_isolation`` -- the gate-level isolation: no
   construction-visible arm, a gate-time disjointness RE-PROOF from live bytes,
   and one sealed attempt per permitted read run id.

The committed receipt ``docs/receipts/owner/2026-09-23-slurp-test-split-
allowance-v1.json`` carries ``status: "pending-owner"``, so the last test in the
first group asserts what matters most today: in this repository, as it stands, a
``final-report`` plan is refused.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, fields, replace
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.contracts import (
    FINAL_REPORT_EXECUTION_PROFILE,
    FINAL_REPORT_SPLIT_ROLE,
    OWNER_SPLIT_ALLOWANCE_RELDIR,
    OWNER_SPLIT_ALLOWANCE_SCHEMA,
    STAGE2_SPLIT_ROLES,
    ExecutionPlan,
    ExecutionScopeError,
    FrozenCoreGate,
    GateClosed,
    OwnerSplitAllowance,
    require_owner_split_allowance,
)

CARRIER = "slurp"
READ_RUN_ID = "SAEA-SLURP-TEST-FULL-LOCKED-SYSTEM-V1"
PREP_RUN_ID = "SAEA-SN-TEST-FULL-PREPROCESS"
ALLOWANCE_RELPATH = (
    f"{OWNER_SPLIT_ALLOWANCE_RELDIR}/2026-09-23-slurp-test-split-allowance-v1.json"
)
SAMPLE_IDS = (
    "slurp:test:000000:audio--1504197928",
    "slurp:test:000000:audio--1504197928-headset",
    "slurp:test:000001:audio--1502210266",
)
OTHER_IDS = ("slurp:train:000001:audio--1504192678",)


def identity_hash(sample_ids) -> str:
    return hashlib.sha256(
        "\n".join(sorted(f"{CARRIER}/{value}" for value in sample_ids)).encode("utf-8")
    ).hexdigest()


TEST_IDENTITY = identity_hash(SAMPLE_IDS)
OTHER_IDENTITY = identity_hash(OTHER_IDS)


def allowance_document(**overrides) -> dict:
    document = {
        "schema": OWNER_SPLIT_ALLOWANCE_SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "status": "authorised",
        "dated_owner_decision": "owner decision 108 of 2026-09-24",
        "venue": "Remedy B: the read stays in the study carrier because ...",
        "split": {
            "carrier_lock_key": CARRIER,
            "split_name": "TEST-FULL",
            "split_identity_hash": TEST_IDENTITY,
        },
        "permitted_run_ids": [READ_RUN_ID, PREP_RUN_ID],
        "read_run_ids": [READ_RUN_ID],
        "preparation_run_ids": [PREP_RUN_ID],
    }
    document.update(overrides)
    return document


def write_allowance(root: Path, document: object, *, relpath: str = ALLOWANCE_RELPATH) -> str:
    path = Path(root) / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def plan(**overrides) -> ExecutionPlan:
    fields = {
        "run_id": READ_RUN_ID,
        "execution_profile": FINAL_REPORT_EXECUTION_PROFILE,
        "carrier_lock_key": CARRIER,
        "split_role": FINAL_REPORT_SPLIT_ROLE,
        "split_identity_hash": TEST_IDENTITY,
        "planned_model_calls": 13078,
        "planned_gpu_hours": 42.0,
        "planned_speech_audio_seconds": 36912,
        "protocol_hash": "b" * 64,
        "attempt_id": "attempt-test-full-v1",
    }
    fields.update(overrides)
    return ExecutionPlan(**fields)


# --------------------------------------------------------------------------- #
# 1. the plan-level authorisation
# --------------------------------------------------------------------------- #


def test_final_report_is_not_a_stage2_role():
    """The role is admitted, but never by widening the Stage-2 set."""

    assert FINAL_REPORT_SPLIT_ROLE == "final-report"
    assert FINAL_REPORT_SPLIT_ROLE not in STAGE2_SPLIT_ROLES
    assert set(STAGE2_SPLIT_ROLES) == {"discovery", "dev"}


def test_the_allowance_never_moves_a_plan_s_serialized_identity(tmp_path):
    """``owner_allowance`` is an InitVar, so ``asdict`` is byte-identical.

    Three frozen launchers under ``docs/checks/`` compare ``asdict(plan)``
    against committed execution-plan documents whose SHA-256 they also assert,
    and ``core.driver.speech_native`` re-checks a resumed run's plan copy
    against it. A thirteenth field would have moved all of them at once.
    """

    digest = write_allowance(tmp_path, allowance_document())
    bare = plan(split_role="dev", owner_allowance=None)
    carried = plan(owner_allowance={"path": ALLOWANCE_RELPATH, "sha256": digest})

    assert "owner_allowance" not in asdict(bare)
    assert "owner_allowance" not in asdict(carried)
    assert {field.name for field in fields(ExecutionPlan)} == set(asdict(bare))
    assert bare.owner_allowance is None
    assert carried.owner_allowance == OwnerSplitAllowance(
        path=ALLOWANCE_RELPATH, sha256=digest
    )


def test_replace_carries_the_allowance_forward(tmp_path):
    """``core.flight.runtime`` re-caps a plan with ``dataclasses.replace``.

    An InitVar WITH a default is read back off the instance by ``replace``, so
    the re-capped plan keeps its authorisation instead of silently losing it and
    being refused for declaring none.
    """

    digest = write_allowance(tmp_path, allowance_document())
    original = plan(owner_allowance={"path": ALLOWANCE_RELPATH, "sha256": digest})
    recapped = replace(original, planned_speech_audio_seconds=36913)

    assert recapped.owner_allowance == original.owner_allowance
    assert recapped.validate(source_root=tmp_path) is recapped


def test_confirmatory_is_still_refused_verbatim():
    """Section 6.1 of the protocol quotes this refusal; it must not move."""

    with pytest.raises(ExecutionScopeError) as error:
        plan(split_role="confirmatory").validate()
    assert "requires OWNER_GO_AND_PAPER_EXECUTION_CONTRACT" in str(error.value)


def test_unknown_role_names_both_the_stage2_roles_and_the_final_report_role():
    with pytest.raises(ExecutionScopeError) as error:
        plan(split_role="held-out").validate()
    message = str(error.value)
    assert "unknown split role 'held-out'" in message
    assert "['dev', 'discovery']" in message
    assert FINAL_REPORT_SPLIT_ROLE in message


def test_a_stage2_plan_may_not_carry_an_allowance(tmp_path):
    """The field is the final-report authorisation, not a decoration."""

    digest = write_allowance(tmp_path, allowance_document())
    with pytest.raises(ExecutionScopeError) as error:
        plan(
            split_role="dev",
            owner_allowance={"path": ALLOWANCE_RELPATH, "sha256": digest},
        ).validate(source_root=tmp_path)
    assert "only meaningful for split role 'final-report'" in str(error.value)


def test_missing_allowance_is_refused(tmp_path):
    with pytest.raises(ExecutionScopeError) as error:
        plan().validate(source_root=tmp_path)
    message = str(error.value)
    assert "no owner_allowance was declared" in message
    assert OWNER_SPLIT_ALLOWANCE_SCHEMA in message


@pytest.mark.parametrize(
    "value",
    [
        "docs/receipts/owner/x.json",
        {"path": "docs/receipts/owner/x.json"},
        {"path": "docs/receipts/owner/x.json", "sha256": 7},
        {"path": "docs/receipts/owner/x.json", "sha256": "a" * 64, "extra": 1},
    ],
)
def test_malformed_allowance_is_refused(tmp_path, value):
    with pytest.raises(ExecutionScopeError) as error:
        plan(owner_allowance=value).validate(source_root=tmp_path)
    assert "must be an OwnerSplitAllowance or a mapping" in str(error.value)


@pytest.mark.parametrize(
    "relpath",
    [
        "docs/receipts/rosters/x.json",  # outside the owner directory
        "docs/receipts/owner/../../../etc/passwd",
        "docs/receipts/owner\\x.json",
        "/docs/receipts/owner/x.json",
        "C:/docs/receipts/owner/x.json",
        "",
    ],
)
def test_unsafe_allowance_path_is_refused(tmp_path, relpath):
    with pytest.raises(ExecutionScopeError) as error:
        plan(owner_allowance={"path": relpath, "sha256": "a" * 64}).validate(
            source_root=tmp_path
        )
    assert "must be a repo-relative POSIX path under" in str(error.value)


def test_malformed_allowance_digest_is_refused(tmp_path):
    with pytest.raises(ExecutionScopeError) as error:
        plan(owner_allowance={"path": ALLOWANCE_RELPATH, "sha256": "not-a-hash"}).validate(
            source_root=tmp_path
        )
    assert "owner allowance sha256 must be a 64-hex SHA-256" in str(error.value)


def test_wrong_execution_profile_is_refused(tmp_path):
    digest = write_allowance(tmp_path, allowance_document())
    with pytest.raises(ExecutionScopeError) as error:
        plan(
            execution_profile="baseline-reproduction",
            owner_allowance={"path": ALLOWANCE_RELPATH, "sha256": digest},
        ).validate(source_root=tmp_path)
    assert "runs only under execution profile 'bounded-discovery-probe'" in str(error.value)


def test_missing_receipt_file_is_refused(tmp_path):
    with pytest.raises(ExecutionScopeError) as error:
        plan(owner_allowance={"path": ALLOWANCE_RELPATH, "sha256": "a" * 64}).validate(
            source_root=tmp_path
        )
    assert "owner allowance receipt is missing or unreadable" in str(error.value)


def test_byte_drift_is_refused(tmp_path):
    write_allowance(tmp_path, allowance_document())
    with pytest.raises(ExecutionScopeError) as error:
        plan(owner_allowance={"path": ALLOWANCE_RELPATH, "sha256": "0" * 64}).validate(
            source_root=tmp_path
        )
    message = str(error.value)
    assert "not the pinned" in message
    assert "flipping the receipt's status is exactly such a drift" in message


def test_non_json_receipt_is_refused(tmp_path):
    path = tmp_path / ALLOWANCE_RELPATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"not json")
    digest = hashlib.sha256(b"not json").hexdigest()
    with pytest.raises(ExecutionScopeError) as error:
        plan(owner_allowance={"path": ALLOWANCE_RELPATH, "sha256": digest}).validate(
            source_root=tmp_path
        )
    assert "is not readable JSON" in str(error.value)


def test_non_object_receipt_is_refused(tmp_path):
    digest = write_allowance(tmp_path, ["not", "an", "object"])
    with pytest.raises(ExecutionScopeError) as error:
        plan(owner_allowance={"path": ALLOWANCE_RELPATH, "sha256": digest}).validate(
            source_root=tmp_path
        )
    assert "must be a JSON object" in str(error.value)


@pytest.mark.parametrize(
    ("overrides", "fragment"),
    [
        ({"schema": "saea-something-else-v1"}, "schema must be"),
        ({"study": "another-study"}, "study identity must be"),
        ({"status": "pending-owner"}, "status is 'pending-owner', not 'authorised'"),
        ({"split": "not-an-object"}, "carries no 'split' object"),
        (
            {"split": {"carrier_lock_key": "earnings21-original", "split_identity_hash": TEST_IDENTITY}},
            "authorises carrier 'earnings21-original'",
        ),
        (
            {"split": {"carrier_lock_key": CARRIER, "split_identity_hash": "c" * 64}},
            "authorises split identity",
        ),
        ({"permitted_run_ids": []}, "permitted_run_ids must be a"),
        ({"permitted_run_ids": [READ_RUN_ID, READ_RUN_ID]}, "permitted_run_ids must be a"),
        ({"permitted_run_ids": [READ_RUN_ID, 7]}, "permitted_run_ids must be a"),
        ({"read_run_ids": [READ_RUN_ID, PREP_RUN_ID]}, "must partition permitted_run_ids"),
        ({"preparation_run_ids": []}, "must partition permitted_run_ids"),
        ({"read_run_ids": "not-a-list"}, "must partition permitted_run_ids"),
        ({"dated_owner_decision": "   "}, "must name the dated owner decision"),
        ({"venue": ""}, "must state in 'venue' why this read"),
    ],
)
def test_receipt_field_refusals(tmp_path, overrides, fragment):
    digest = write_allowance(tmp_path, allowance_document(**overrides))
    with pytest.raises(ExecutionScopeError) as error:
        plan(owner_allowance={"path": ALLOWANCE_RELPATH, "sha256": digest}).validate(
            source_root=tmp_path
        )
    assert fragment in str(error.value)


def test_a_run_id_the_owner_did_not_name_is_refused(tmp_path):
    digest = write_allowance(tmp_path, allowance_document())
    with pytest.raises(ExecutionScopeError) as error:
        plan(
            run_id="SAEA-SLURP-TEST-FULL-SECOND-READ-V1",
            owner_allowance={"path": ALLOWANCE_RELPATH, "sha256": digest},
        ).validate(source_root=tmp_path)
    assert "is not in the owner allowance's permitted_run_ids" in str(error.value)


def test_the_one_acceptance_path(tmp_path):
    """Everything right: the plan validates and the receipt comes back."""

    digest = write_allowance(tmp_path, allowance_document())
    allowance = {"path": ALLOWANCE_RELPATH, "sha256": digest}
    validated = plan(owner_allowance=allowance).validate(source_root=tmp_path)

    assert validated.split_role == FINAL_REPORT_SPLIT_ROLE
    assert validated.owner_allowance == OwnerSplitAllowance(
        path=ALLOWANCE_RELPATH, sha256=digest
    )
    # A mapping was coerced to the frozen dataclass, so the plan stays hashable
    # exactly as every other ExecutionPlan is.
    assert isinstance(hash(validated), int)

    document = require_owner_split_allowance(
        run_id=PREP_RUN_ID,
        execution_profile=FINAL_REPORT_EXECUTION_PROFILE,
        carrier_lock_key=CARRIER,
        split_identity_hash=TEST_IDENTITY,
        owner_allowance=OwnerSplitAllowance(path=ALLOWANCE_RELPATH, sha256=digest),
        source_root=tmp_path,
    )
    assert document["read_run_ids"] == [READ_RUN_ID]
    assert document["preparation_run_ids"] == [PREP_RUN_ID]


def test_the_committed_receipt_refuses_every_final_report_plan_today():
    """The state of THIS repository: decision 108 has not been taken.

    Resolved against the module's own checkout root, exactly as a production
    caller that passes no ``source_root`` resolves it.
    """

    repo_root = Path(__file__).resolve().parents[2]
    raw = (repo_root / ALLOWANCE_RELPATH).read_bytes()
    document = json.loads(raw.decode("utf-8"))
    assert document["status"] == "pending-owner"

    with pytest.raises(ExecutionScopeError) as error:
        plan(
            run_id=PREP_RUN_ID,
            split_identity_hash=document["split"]["split_identity_hash"],
            owner_allowance={
                "path": ALLOWANCE_RELPATH,
                "sha256": hashlib.sha256(raw).hexdigest(),
            },
        ).validate()
    assert "status is 'pending-owner', not 'authorised'" in str(error.value)


def test_every_permitted_run_id_of_the_committed_receipt_is_named_once():
    repo_root = Path(__file__).resolve().parents[2]
    document = json.loads((repo_root / ALLOWANCE_RELPATH).read_text(encoding="utf-8"))
    permitted = document["permitted_run_ids"]
    assert set(document["read_run_ids"]) | set(document["preparation_run_ids"]) == set(
        permitted
    )
    assert not set(document["read_run_ids"]) & set(document["preparation_run_ids"])
    assert set(permitted) == {
        "SAEA-SN-TEST-FULL-PREPROCESS",
        "SAEA-SLURP-TEST-FULL-SPEECH-QUERY-ENCODING-V1",
        "SAEA-SLURP-TEST-FULL-QUERY-VECTOR-EXPORT-V1",
        "SAEA-SLURP-TEST-FULL-LOCKED-SYSTEM-V1",
        "SAEA-SLURP-TEST-FULL-DIRECT-V1",
    }


def test_the_committed_receipt_binds_the_committed_roster():
    repo_root = Path(__file__).resolve().parents[2]
    document = json.loads((repo_root / ALLOWANCE_RELPATH).read_text(encoding="utf-8"))
    split = document["split"]
    roster_path = repo_root / split["roster_receipt_relpath"]
    roster = json.loads(roster_path.read_text(encoding="utf-8"))

    assert roster["roster_id"] == split["roster_id"]
    assert roster["split_role"] == FINAL_REPORT_SPLIT_ROLE
    assert roster["split_identity_hash"] == split["split_identity_hash"]
    assert len(roster["items"]) == split["recordings"] == 13078
    assert (
        hashlib.sha256(roster_path.read_bytes()).hexdigest()
        == split["roster_receipt_sha256"]
    )


# --------------------------------------------------------------------------- #
# 2. the gate-level isolation
# --------------------------------------------------------------------------- #


def roster_receipt(sample_ids, *, roster_id: str, split_role: str, roster_role: str) -> dict:
    return {
        "schema": "saea-roster-receipt-v1",
        "roster_id": roster_id,
        "carrier_lock_key": CARRIER,
        "split_role": split_role,
        "roster_role": roster_role,
        "seed": 20260923,
        "per_stratum": {"all": len(sample_ids)},
        "strata_counts": {"all": len(sample_ids)},
        "items": [
            {"sample_id": value, "stratum": "all"} for value in sorted(sample_ids)
        ],
        "excluded_count": 0,
        "split_identity_hash": identity_hash(sample_ids),
    }


def build_gate(tmp_path: Path, *, allowance_overrides: dict | None = None) -> tuple[FrozenCoreGate, dict]:
    digest = write_allowance(tmp_path, allowance_document(**(allowance_overrides or {})))
    rosters = tmp_path / "docs/receipts/rosters"
    rosters.mkdir(parents=True, exist_ok=True)
    (rosters / "slurp-test-full.json").write_text(
        json.dumps(
            roster_receipt(
                SAMPLE_IDS,
                roster_id="SLURP-TEST-FULL-13078-V1",
                split_role=FINAL_REPORT_SPLIT_ROLE,
                roster_role="evaluation",
            ),
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    data_root = tmp_path / "data"
    data_root.mkdir(parents=True, exist_ok=True)
    gate = FrozenCoreGate(
        e0_receipt=tmp_path / "docs/receipts/e0-closure.json",
        runtime_receipt=tmp_path / "docs/receipts/runtime.json",
        data_root=data_root,
        lock_path=tmp_path / "datasets.lock.json",
        runtime_root=tmp_path / "runtime",
        exposure_ledger=tmp_path / "docs/exposure-ledger.md",
        source_root=tmp_path,
    )
    return gate, {"path": ALLOWANCE_RELPATH, "sha256": digest}


def write_snapshot(data_root: Path, name: str, sample_ids) -> None:
    path = data_root / "knowledge" / CARRIER / name / "snapshot.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "snapshot_version": "knowledge-snapshot-v1",
                "snapshot_id": name,
                "source_partition_role": "train",
                "source_sample_ids": sorted(sample_ids),
                "values": [{"content": "a TRAIN gold string this pass never reads"}],
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def write_attempt(data_root: Path, run_id: str, attempt_id: str, state: str) -> None:
    path = data_root / "attempts" / run_id / f"{attempt_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema": "saea-attempt-v1",
                "run_id": run_id,
                "attempt_id": attempt_id,
                "carrier_lock_key": CARRIER,
                "state": state,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def test_gate_isolation_is_a_no_op_for_every_other_split_role(tmp_path):
    gate, _allowance = build_gate(tmp_path)
    gate._require_final_report_isolation(plan(split_role="discovery"), None)
    gate._require_final_report_isolation(plan(split_role="dev"), "bare-core")


def test_gate_accepts_a_clean_final_report_touch(tmp_path):
    gate, allowance = build_gate(tmp_path)
    write_snapshot(gate.data_root, "train-exemplars", OTHER_IDS)
    gate._require_final_report_isolation(plan(owner_allowance=allowance), "bare-core")


def test_gate_refuses_a_construction_visible_arm(tmp_path):
    gate, allowance = build_gate(tmp_path)
    with pytest.raises(GateClosed) as error:
        gate._require_final_report_isolation(
            plan(owner_allowance=allowance), "construction-proposer-text"
        )
    assert "can never carry it" in str(error.value)


def test_gate_refuses_an_unrostered_split_identity(tmp_path):
    gate, allowance = build_gate(tmp_path)
    document = json.loads(
        (tmp_path / ALLOWANCE_RELPATH).read_text(encoding="utf-8")
    )
    document["split"]["split_identity_hash"] = OTHER_IDENTITY
    digest = write_allowance(tmp_path, document)
    with pytest.raises(GateClosed) as error:
        gate._require_final_report_isolation(
            plan(
                split_identity_hash=OTHER_IDENTITY,
                owner_allowance={"path": allowance["path"], "sha256": digest},
            ),
            None,
        )
    assert "exactly ONE committed roster receipt" in str(error.value)


def test_gate_refuses_an_overlapping_construction_roster(tmp_path):
    gate, allowance = build_gate(tmp_path)
    (tmp_path / "docs/receipts/rosters/slurp-construction.json").write_text(
        json.dumps(
            roster_receipt(
                (SAMPLE_IDS[0],) + OTHER_IDS,
                roster_id="SLURP-CONSTRUCTION-OVERLAP",
                split_role="discovery",
                roster_role="construction",
            ),
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    with pytest.raises(GateClosed) as error:
        gate._require_final_report_isolation(plan(owner_allowance=allowance), None)
    message = str(error.value)
    assert "shares 1 sample id(s) with the committed roster" in message
    assert "slurp-construction.json" in message


def test_gate_refuses_an_overlapping_knowledge_store(tmp_path):
    gate, allowance = build_gate(tmp_path)
    write_snapshot(gate.data_root, "clean-pool", OTHER_IDS)
    write_snapshot(gate.data_root, "leaky-pool", OTHER_IDS + (SAMPLE_IDS[1],))
    with pytest.raises(GateClosed) as error:
        gate._require_final_report_isolation(plan(owner_allowance=allowance), None)
    message = str(error.value)
    assert "knowledge store / exemplar pool" in message
    assert "leaky-pool" in message


def test_gate_skips_a_snapshot_whose_bytes_cannot_hold_a_roster_id(tmp_path):
    """The byte scan is a superset test, so a clean store is never parsed."""

    gate, _allowance = build_gate(tmp_path)
    write_snapshot(gate.data_root, "clean-pool", OTHER_IDS)
    path = gate.data_root / "knowledge" / CARRIER / "clean-pool" / "snapshot.json"
    assert not gate._bytes_contain_any(path, (b"slurp:test:",))
    assert gate._bytes_contain_any(path, (b"slurp:train:",))


def test_gate_allows_at_most_one_attempt_of_a_read_run_id(tmp_path):
    gate, allowance = build_gate(tmp_path)
    write_attempt(gate.data_root, READ_RUN_ID, "attempt-test-full-v1", "OPENED")
    # The in-flight attempt re-opening the gate is fine ...
    gate._require_final_report_isolation(plan(owner_allowance=allowance), None)
    # ... a SECOND attempt id under the same read run id is not, recovery or not.
    with pytest.raises(GateClosed) as error:
        gate._require_final_report_isolation(
            plan(owner_allowance=allowance, attempt_id="attempt-test-full-recovery-v1"),
            None,
        )
    message = str(error.value)
    assert "allows at most 1 attempt(s)" in message
    assert "no repeat, no second configuration, no best-of" in message


def test_gate_refuses_to_re_fly_a_sealed_read(tmp_path):
    gate, allowance = build_gate(tmp_path)
    write_attempt(gate.data_root, READ_RUN_ID, "attempt-test-full-v1", "FINALIZED")
    with pytest.raises(GateClosed) as error:
        gate._require_final_report_isolation(plan(owner_allowance=allowance), None)
    assert "is already FINALIZED" in str(error.value)


def test_a_preparation_run_id_keeps_one_recovery(tmp_path):
    gate, allowance = build_gate(tmp_path)
    write_attempt(gate.data_root, PREP_RUN_ID, "attempt-packets-v1", "ABORTED")
    prepared = plan(
        run_id=PREP_RUN_ID,
        owner_allowance=allowance,
        attempt_id="attempt-packets-recovery-v1",
    )
    gate._require_final_report_isolation(prepared, None)

    write_attempt(gate.data_root, PREP_RUN_ID, "attempt-packets-recovery-v1", "ABORTED")
    with pytest.raises(GateClosed) as error:
        gate._require_final_report_isolation(
            plan(
                run_id=PREP_RUN_ID,
                owner_allowance=allowance,
                attempt_id="attempt-packets-third-v1",
            ),
            None,
        )
    assert "allows at most 2 attempt(s)" in str(error.value)


# --------------------------------------------------------------------------- #
# 3. declared partitions of a final-report roster (owner decision 147)
# --------------------------------------------------------------------------- #
#
# Decision 141 permitted a coverage-guaranteed test SAMPLE with its COMPLEMENT
# sealed at the same moment; decision 146 adopted SLURP-TEST-SAMPLE-3010-V1 and
# SLURP-TEST-CLOSURE-10068-V1, both ``derived_from`` the frozen parent
# SLURP-TEST-FULL-13078-V1. A partition member shares every one of its ids with
# its parent by construction, so the gate as built refused all three. Decision
# 147: adjust WITH PROOF, never by relaxing -- the parent and the sibling(s) are
# skipped only after the gate re-proves the partition from committed item
# lists; every other intersection is unchanged.

CLOSURE_IDS = (
    "slurp:test:000002:audio--1000000002",
    "slurp:test:000002:audio--1000000002-headset",
    "slurp:test:000003:audio--1000000003",
)
PARENT_IDS = SAMPLE_IDS + CLOSURE_IDS
PARENT_IDENTITY = identity_hash(PARENT_IDS)
CLOSURE_IDENTITY = identity_hash(CLOSURE_IDS)
PARENT_NAME = "slurp-test-full.json"
SAMPLE_NAME = "slurp-test-sample.json"
CLOSURE_NAME = "slurp-test-closure.json"
PARENT_ROSTER_ID = "SLURP-TEST-FULL-13078-V1"
SAMPLE_ROSTER_ID = "SLURP-TEST-SAMPLE-3010-V1"
CLOSURE_ROSTER_ID = "SLURP-TEST-CLOSURE-10068-V1"


def write_roster(root: Path, name: str, document: dict) -> str:
    path = Path(root) / "docs/receipts/rosters" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(document, indent=2, sort_keys=True).encode("utf-8")
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def declaration(document: dict, name: str, sha256: str | None = None) -> dict:
    value = {
        "roster_id": document["roster_id"],
        "repo_relpath": f"docs/receipts/rosters/{name}",
        "split_identity_hash": document["split_identity_hash"],
        "recordings": len(document["items"]),
    }
    if sha256 is not None:
        value["sha256"] = sha256
    return value


def build_partition_gate(
    tmp_path: Path,
    *,
    fly: str,
    sample_ids=SAMPLE_IDS,
    closure_ids=CLOSURE_IDS,
    parent_ids=PARENT_IDS,
    parent_split_role: str = FINAL_REPORT_SPLIT_ROLE,
    closure_split_role: str = FINAL_REPORT_SPLIT_ROLE,
    write_closure: bool = True,
    mutate=None,
) -> tuple[FrozenCoreGate, dict]:
    """Three committed receipts -- parent, sample, closure -- declared as a
    partition exactly as ``scripts/build_slurp_test_sample_roster.py`` writes
    them, plus an allowance binding the roster named by ``fly``. ``mutate``
    receives ``{"sample": doc, "closure": doc}`` after the declarations are
    built and before the children are written."""

    parent = roster_receipt(
        parent_ids, roster_id=PARENT_ROSTER_ID, split_role=parent_split_role,
        roster_role="evaluation",
    )
    parent_sha = write_roster(tmp_path, PARENT_NAME, parent)
    sample = roster_receipt(
        sample_ids, roster_id=SAMPLE_ROSTER_ID, split_role=FINAL_REPORT_SPLIT_ROLE,
        roster_role="evaluation",
    )
    closure = roster_receipt(
        closure_ids, roster_id=CLOSURE_ROSTER_ID, split_role=closure_split_role,
        roster_role="evaluation",
    )
    sample["derived_from"] = {
        "source_roster": declaration(parent, PARENT_NAME, parent_sha),
        "sibling_roster": declaration(closure, CLOSURE_NAME),
        "selection": "one seeded prompt draw; the sibling is the set difference",
    }
    closure["derived_from"] = {
        "source_roster": declaration(parent, PARENT_NAME, parent_sha),
        "sibling_roster": declaration(sample, SAMPLE_NAME),
        "selection": "one seeded prompt draw; the sibling is the set difference",
    }
    if mutate is not None:
        mutate({"sample": sample, "closure": closure})
    write_roster(tmp_path, SAMPLE_NAME, sample)
    if write_closure:
        write_roster(tmp_path, CLOSURE_NAME, closure)

    chosen = {"parent": parent, "sample": sample, "closure": closure}[fly]
    digest = write_allowance(
        tmp_path,
        allowance_document(
            split={
                "carrier_lock_key": CARRIER,
                "split_name": chosen["roster_id"],
                "split_identity_hash": chosen["split_identity_hash"],
            }
        ),
    )
    data_root = tmp_path / "data"
    data_root.mkdir(parents=True, exist_ok=True)
    gate = FrozenCoreGate(
        e0_receipt=tmp_path / "docs/receipts/e0-closure.json",
        runtime_receipt=tmp_path / "docs/receipts/runtime.json",
        data_root=data_root,
        lock_path=tmp_path / "datasets.lock.json",
        runtime_root=tmp_path / "runtime",
        exposure_ledger=tmp_path / "docs/exposure-ledger.md",
        source_root=tmp_path,
    )
    return gate, {
        "split_identity_hash": chosen["split_identity_hash"],
        "owner_allowance": {"path": ALLOWANCE_RELPATH, "sha256": digest},
    }


def exemptions(gate: FrozenCoreGate, flown: ExecutionPlan) -> dict[str, str]:
    receipts = gate._carrier_roster_receipts(CARRIER)
    relpath, document, ids = gate._final_report_roster(flown, receipts)
    return gate._final_report_partition_exemptions(flown, relpath, document, ids, receipts)


@pytest.mark.parametrize("fly", ["sample", "closure"])
def test_a_proven_partition_member_is_admitted_against_its_parent_and_sibling(tmp_path, fly):
    gate, fields = build_partition_gate(tmp_path, fly=fly)
    write_snapshot(gate.data_root, "train-exemplars", OTHER_IDS)
    flown = plan(**fields)
    gate._require_final_report_isolation(flown, "bare-core")
    sibling = CLOSURE_IDENTITY if fly == "sample" else TEST_IDENTITY
    assert exemptions(gate, flown) == {
        PARENT_IDENTITY: f"docs/receipts/rosters/{PARENT_NAME}",
        sibling: f"docs/receipts/rosters/{CLOSURE_NAME if fly == 'sample' else SAMPLE_NAME}",
    }


def test_the_full_parent_is_admitted_against_its_own_children(tmp_path):
    gate, fields = build_partition_gate(tmp_path, fly="parent")
    flown = plan(**fields)
    gate._require_final_report_isolation(flown, None)
    assert exemptions(gate, flown) == {
        TEST_IDENTITY: f"docs/receipts/rosters/{SAMPLE_NAME}",
        CLOSURE_IDENTITY: f"docs/receipts/rosters/{CLOSURE_NAME}",
    }


@pytest.mark.parametrize("fly", ["sample", "closure", "parent"])
def test_a_partition_member_is_still_refused_against_a_foreign_roster(tmp_path, fly):
    """The exemption names the proven parent/sibling/children and nothing
    else: a construction roster sharing one id refuses every member of the
    partition with the message the gate has always given."""

    gate, fields = build_partition_gate(tmp_path, fly=fly)
    leaked = SAMPLE_IDS[0] if fly != "closure" else CLOSURE_IDS[0]
    write_roster(
        tmp_path,
        "slurp-construction.json",
        roster_receipt(
            (leaked,) + OTHER_IDS, roster_id="SLURP-CONSTRUCTION-OVERLAP",
            split_role="discovery", roster_role="construction",
        ),
    )
    with pytest.raises(GateClosed) as error:
        gate._require_final_report_isolation(plan(**fields), None)
    message = str(error.value)
    assert "shares 1 sample id(s) with the committed roster" in message
    assert "slurp-construction.json" in message
    assert "partition proof" not in message


def test_a_partition_member_is_still_refused_against_a_leaky_knowledge_store(tmp_path):
    gate, fields = build_partition_gate(tmp_path, fly="sample")
    write_snapshot(gate.data_root, "leaky-pool", OTHER_IDS + (SAMPLE_IDS[1],))
    with pytest.raises(GateClosed) as error:
        gate._require_final_report_isolation(plan(**fields), None)
    assert "knowledge store / exemplar pool" in str(error.value)


def test_a_non_partition_final_report_roster_is_intersected_exactly_as_before(tmp_path):
    """No ``derived_from`` on either side: the exemption is empty and a second
    final-report roster sharing an id is refused with the original message."""

    gate, allowance = build_gate(tmp_path)
    assert exemptions(gate, plan(owner_allowance=allowance)) == {}
    write_roster(
        tmp_path,
        "slurp-test-other.json",
        roster_receipt(
            (SAMPLE_IDS[2],) + OTHER_IDS, roster_id="SLURP-TEST-OTHER",
            split_role=FINAL_REPORT_SPLIT_ROLE, roster_role="evaluation",
        ),
    )
    with pytest.raises(GateClosed) as error:
        gate._require_final_report_isolation(plan(owner_allowance=allowance), None)
    message = str(error.value)
    assert message.startswith(
        f"the {FINAL_REPORT_SPLIT_ROLE!r} roster docs/receipts/rosters/slurp-test-full.json "
        "shares 1 sample id(s) with the committed roster "
        "docs/receipts/rosters/slurp-test-other.json"
    )


@pytest.mark.parametrize("fly", ["sample", "parent"])
def test_a_short_union_is_refused(tmp_path, fly):
    gate, fields = build_partition_gate(tmp_path, fly=fly, closure_ids=CLOSURE_IDS[:-1])
    with pytest.raises(GateClosed) as error:
        gate._require_final_report_isolation(plan(**fields), None)
    message = str(error.value)
    assert "partition proof failed" in message
    assert "is short of the declared parent" in message
    assert PARENT_ROSTER_ID in message
    assert "by 1 sample id(s)" in message


@pytest.mark.parametrize("fly", ["sample", "parent"])
def test_an_overlapping_sibling_is_refused(tmp_path, fly):
    gate, fields = build_partition_gate(
        tmp_path, fly=fly, closure_ids=CLOSURE_IDS + (SAMPLE_IDS[0],)
    )
    with pytest.raises(GateClosed) as error:
        gate._require_final_report_isolation(plan(**fields), None)
    message = str(error.value)
    assert "partition proof failed" in message
    assert "share 1 sample id(s)" in message
    assert SAMPLE_ROSTER_ID in message and CLOSURE_ROSTER_ID in message


def test_a_surplus_id_is_refused(tmp_path):
    gate, fields = build_partition_gate(
        tmp_path, fly="sample", closure_ids=CLOSURE_IDS + ("slurp:test:000009:audio--9",)
    )
    with pytest.raises(GateClosed) as error:
        gate._require_final_report_isolation(plan(**fields), None)
    message = str(error.value)
    assert "are not in the declared parent" in message
    assert PARENT_ROSTER_ID in message


def test_a_roster_that_declares_a_parent_it_does_not_partition_is_refused(tmp_path):
    """The declared parent is committed and final-report, but the roster's
    ids are not inside it."""

    other = roster_receipt(
        OTHER_IDS + ("slurp:train:000002:audio--2",), roster_id="SLURP-OTHER-FULL",
        split_role=FINAL_REPORT_SPLIT_ROLE, roster_role="evaluation",
    )
    other_sha = write_roster(tmp_path, "slurp-other-full.json", other)

    def repoint(documents):
        for document in documents.values():
            document["derived_from"]["source_roster"] = declaration(
                other, "slurp-other-full.json", other_sha
            )

    gate, fields = build_partition_gate(tmp_path, fly="sample", mutate=repoint)
    with pytest.raises(GateClosed) as error:
        gate._require_final_report_isolation(plan(**fields), None)
    message = str(error.value)
    assert "partition proof failed" in message
    assert "SLURP-OTHER-FULL" in message


def test_a_parent_that_is_not_final_report_is_refused(tmp_path):
    gate, fields = build_partition_gate(tmp_path, fly="sample", parent_split_role="dev")
    with pytest.raises(GateClosed) as error:
        gate._require_final_report_isolation(plan(**fields), None)
    message = str(error.value)
    assert f"declared parent {PARENT_ROSTER_ID}" in message
    assert "has split_role 'dev', not 'final-report'" in message


def test_a_child_that_is_not_final_report_refuses_the_parent(tmp_path):
    gate, fields = build_partition_gate(tmp_path, fly="parent", closure_split_role="dev")
    with pytest.raises(GateClosed) as error:
        gate._require_final_report_isolation(plan(**fields), None)
    message = str(error.value)
    assert CLOSURE_ROSTER_ID in message
    assert "has split_role 'dev', not 'final-report'" in message


def _sibling_not_committed(documents):
    documents["sample"]["derived_from"]["sibling_roster"]["split_identity_hash"] = "d" * 64


def _sibling_declares_another_parent(documents):
    documents["closure"]["derived_from"]["source_roster"]["split_identity_hash"] = "e" * 64


def _sibling_does_not_name_this_roster(documents):
    documents["closure"]["derived_from"]["sibling_roster"]["split_identity_hash"] = "f" * 64


def _sibling_declares_no_partition(documents):
    del documents["closure"]["derived_from"]


def _sibling_items_tampered(documents):
    documents["closure"]["items"].append({"sample_id": "slurp:test:000009:audio--9", "stratum": "all"})


def _sibling_forges_the_parent_pin(documents):
    documents["sample"]["derived_from"]["source_roster"]["sha256"] = "0" * 64


def _sibling_forges_the_parent_id(documents):
    documents["sample"]["derived_from"]["source_roster"]["roster_id"] = "SLURP-TEST-FULL-FORGED"


def _sibling_forges_the_sibling_relpath(documents):
    documents["sample"]["derived_from"]["sibling_roster"]["repo_relpath"] = "docs/receipts/rosters/elsewhere.json"


def _half_a_declaration(documents):
    del documents["sample"]["derived_from"]["sibling_roster"]


@pytest.mark.parametrize(
    ("mutate", "fragment"),
    [
        (_sibling_not_committed, "declared sibling (dddddddddddd...) is not a committed roster receipt"),
        (_sibling_declares_another_parent, "declares parent (eeeeeeeeeeee...), not this roster's parent"),
        (_sibling_does_not_name_this_roster, "the declaration is not mutual"),
        (_sibling_declares_no_partition, "declares no partition of its own, so it cannot be this roster's sibling"),
        (_sibling_items_tampered, "refusing a tampered receipt"),
        (_sibling_forges_the_parent_pin, "declared parent file sha256"),
        (_sibling_forges_the_parent_id, "declared parent roster_id 'SLURP-TEST-FULL-FORGED'"),
        (_sibling_forges_the_sibling_relpath, "declared sibling repo_relpath"),
        (_half_a_declaration, "declares half a partition"),
    ],
)
def test_a_forged_sibling_or_parent_declaration_is_refused(tmp_path, mutate, fragment):
    gate, fields = build_partition_gate(tmp_path, fly="sample", mutate=mutate)
    with pytest.raises(GateClosed) as error:
        gate._require_final_report_isolation(plan(**fields), None)
    assert fragment in str(error.value)


def test_the_parent_is_refused_while_a_declared_child_is_missing(tmp_path):
    """Only the sample is committed: the parent's declared children do not
    cover it and the sample names a sibling that is not there."""

    gate, fields = build_partition_gate(tmp_path, fly="parent", write_closure=False)
    with pytest.raises(GateClosed) as error:
        gate._require_final_report_isolation(plan(**fields), None)
    message = str(error.value)
    assert "partition proof failed" in message
    assert "not exactly the other committed receipts that declare this roster as their parent" in message


def test_a_child_whose_sibling_set_is_not_the_other_children_refuses_the_parent(tmp_path):
    gate, fields = build_partition_gate(
        tmp_path, fly="parent", mutate=_sibling_does_not_name_this_roster
    )
    with pytest.raises(GateClosed) as error:
        gate._require_final_report_isolation(plan(**fields), None)
    assert "not exactly the other committed receipts" in str(error.value)


def test_the_committed_test_rosters_prove_their_partition_and_nothing_else_is_skipped():
    """THIS repository's receipts: the sample, the closure and the FULL parent
    each pass the roster intersection under the exemption they earn, and the
    exemption names exactly the partition. Model-free: committed receipts only;
    an empty data root, so no snapshot is opened."""

    repo_root = Path(__file__).resolve().parents[2]
    gate = FrozenCoreGate(
        e0_receipt=repo_root / "docs/receipts/e0-closure.json",
        runtime_receipt=repo_root / "docs/receipts/runtime.json",
        data_root=repo_root / "docs/checks/does-not-exist",
        lock_path=repo_root / "docs/datasets.lock.json",
        runtime_root=repo_root,
        exposure_ledger=repo_root / "docs/exposure-ledger.md",
        source_root=repo_root,
    )
    names = {
        "full": "slurp-test-full-13078-v1.json",
        "sample": "slurp-test-sample-3010-v1.json",
        "closure": "slurp-test-closure-10068-v1.json",
    }
    hashes = {
        key: json.loads(
            (repo_root / "docs/receipts/rosters" / name).read_text(encoding="utf-8")
        )["split_identity_hash"]
        for key, name in names.items()
    }
    assert hashes["sample"] == "0164dabf7b30f8e06f830ba28af849cef7459e8c8821cfbea7a56cabb32470f9"
    assert hashes["closure"] == "377b937df3c29e52e3596426741b03129fa526bf677d92b5c03b78dd8dc2457b"
    assert hashes["full"] == "7247647b8c8b37becd564b7031691565d4e6b09d8e124823054906d36372c95d"
    receipts = gate._carrier_roster_receipts(CARRIER)
    for key, split_identity in hashes.items():
        flown = plan(run_id=f"PROBE-{key.upper()}", split_identity_hash=split_identity)
        relpath, document, ids = gate._final_report_roster(flown, receipts)
        gate._require_final_report_disjointness(
            flown, relpath, ids, document=document, receipts=receipts
        )
        skipped = gate._final_report_partition_exemptions(flown, relpath, document, ids, receipts)
        others = {other for other in hashes if other != key}
        assert skipped == {
            hashes[other]: f"docs/receipts/rosters/{names[other]}" for other in others
        }


# --------------------------------------------------------------------------- #
# 4. the SAMPLE allowance signed under owner decision 151 (2026-09-27)
# --------------------------------------------------------------------------- #
#
# ``docs/receipts/owner/2026-09-27-slurp-test-sample-allowance-v1.json`` is the
# first receipt in this repository whose status is ``authorised``. These tests
# load the COMMITTED bytes and prove what the gate accepts and what it still
# refuses: a sample-identity ``bounded-discovery-probe`` plan for every run id
# the owner named is accepted (plan level and gate level); the closure identity
# is refused naming both hashes; ``paper-scale-confirmatory`` is refused; and
# the FULL receipt of 2026-09-23 still refuses everything (``pending-owner``).
# Model-free: committed receipts only, an empty data root, no media opened.

SAMPLE_ALLOWANCE_RELPATH = (
    f"{OWNER_SPLIT_ALLOWANCE_RELDIR}/2026-09-27-slurp-test-sample-allowance-v1.json"
)
COMMITTED_SAMPLE_IDENTITY = "0164dabf7b30f8e06f830ba28af849cef7459e8c8821cfbea7a56cabb32470f9"
COMMITTED_CLOSURE_IDENTITY = "377b937df3c29e52e3596426741b03129fa526bf677d92b5c03b78dd8dc2457b"
COMMITTED_FULL_IDENTITY = "7247647b8c8b37becd564b7031691565d4e6b09d8e124823054906d36372c95d"
SAMPLE_PREPARATION_RUN_IDS = (
    "SAEA-SN-TEST-SAMPLE-3010-PREPROCESS",
    "SAEA-SLURP-TEST-SAMPLE-3010-SPEECH-QUERY-ENCODING-V1",
    "SAEA-SLURP-TEST-SAMPLE-3010-QUERY-VECTOR-EXPORT-V1",
)
SAMPLE_READ_RUN_IDS = (
    "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-00-PLAN-V1",
    "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-01-V1",
    "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-02-V1",
    "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-03-V1",
    "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-04-V1",
    "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-05-V1",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _committed(relpath: str) -> tuple[bytes, dict, str]:
    raw = (_repo_root() / relpath).read_bytes()
    return raw, json.loads(raw.decode("utf-8")), hashlib.sha256(raw).hexdigest()


def sample_plan(**overrides) -> ExecutionPlan:
    _raw, _document, digest = _committed(SAMPLE_ALLOWANCE_RELPATH)
    fields = {
        "run_id": SAMPLE_READ_RUN_IDS[0],
        "split_identity_hash": COMMITTED_SAMPLE_IDENTITY,
        "planned_model_calls": 3010,
        "planned_gpu_hours": 10.0,
        "planned_speech_audio_seconds": 8207,
        "attempt_id": "attempt-test-sample-v1",
        "owner_allowance": {"path": SAMPLE_ALLOWANCE_RELPATH, "sha256": digest},
    }
    fields.update(overrides)
    return plan(**fields)


def _committed_gate() -> FrozenCoreGate:
    repo_root = _repo_root()
    return FrozenCoreGate(
        e0_receipt=repo_root / "docs/receipts/e0-closure.json",
        runtime_receipt=repo_root / "docs/receipts/runtime.json",
        data_root=repo_root / "docs/checks/does-not-exist",
        lock_path=repo_root / "docs/datasets.lock.json",
        runtime_root=repo_root,
        exposure_ledger=repo_root / "docs/exposure-ledger.md",
        source_root=repo_root,
    )


def test_the_sample_allowance_is_signed_under_decision_151():
    _raw, document, _digest = _committed(SAMPLE_ALLOWANCE_RELPATH)
    assert document["schema"] == OWNER_SPLIT_ALLOWANCE_SCHEMA
    assert document["study"] == "speech-aware-evidence-acquisition"
    assert document["status"] == "authorised"
    decision = document["dated_owner_decision"]
    assert "decision 151" in decision and "2026-09-27" in decision
    # The owner's words, verbatim, and their translation.
    assert "决策3：现在签" in decision
    assert "Decision 3: sign now." in decision
    assert document["venue"].strip()
    assert document["split"]["carrier_lock_key"] == CARRIER
    assert document["split"]["split_identity_hash"] == COMMITTED_SAMPLE_IDENTITY
    gate = document["first_contact_gate"]
    assert gate["verbatim_from_decision_151"] == (
        "the FIRST CONTACT with the sample is nevertheless gated on the coordinator reporting a "
        "dev-admitted composed arm to the owner in conversation"
    )
    assert "pending-owner" in document["closure_status"]
    assert COMMITTED_CLOSURE_IDENTITY in document["closure_status"]


def test_the_sample_allowance_names_exactly_the_owner_s_run_ids_and_no_direct_read():
    _raw, document, _digest = _committed(SAMPLE_ALLOWANCE_RELPATH)
    permitted = document["permitted_run_ids"]
    assert len(set(permitted)) == len(permitted)
    assert set(document["read_run_ids"]) == set(SAMPLE_READ_RUN_IDS)
    assert set(document["preparation_run_ids"]) == set(SAMPLE_PREPARATION_RUN_IDS)
    assert set(document["read_run_ids"]) | set(document["preparation_run_ids"]) == set(permitted)
    assert not set(document["read_run_ids"]) & set(document["preparation_run_ids"])
    assert not any("DIRECT" in run_id for run_id in permitted)
    assert set(document["run_ids"]) == set(permitted)
    for run_id in SAMPLE_READ_RUN_IDS:
        assert document["run_ids"][run_id]["kind"] == "read"
        assert "one attempt" in document["run_ids"][run_id]["what"]
    for run_id in SAMPLE_PREPARATION_RUN_IDS:
        assert document["run_ids"][run_id]["kind"] == "preparation"
        assert document["run_ids"][run_id]["reads_labels"] is False
    assert document["attempt_budget"]["read_run_ids"] == 1
    assert document["attempt_budget"]["preparation_run_ids"] == 2


def test_the_sample_allowance_binds_the_committed_sample_roster_and_its_partition():
    """Every hash and count in the receipt's ``split`` and ``derived_from``
    blocks is recomputed here from the committed roster receipts."""

    repo_root = _repo_root()
    _raw, document, _digest = _committed(SAMPLE_ALLOWANCE_RELPATH)
    split = document["split"]
    roster_raw, roster, roster_digest = _committed(split["roster_receipt_relpath"])
    assert roster["roster_id"] == split["roster_id"] == "SLURP-TEST-SAMPLE-3010-V1"
    assert roster["split_role"] == FINAL_REPORT_SPLIT_ROLE
    assert roster_digest == split["roster_receipt_sha256"]

    ids = [item["sample_id"] for item in roster["items"]]
    assert len(ids) == len(set(ids)) == split["recordings"] == 3010
    assert identity_hash(ids) == split["split_identity_hash"] == COMMITTED_SAMPLE_IDENTITY
    bare = hashlib.sha256("\n".join(sorted(ids)).encode("utf-8")).hexdigest()
    assert bare == split["carrier_split_identity_hash"] == roster["carrier_split_identity_hash"]
    assert len({item["utterance_id"] for item in roster["items"]}) == split["utterances"] == 682
    assert sum(1 for item in roster["items"] if item["headset"]) == split["headset_recordings"]
    assert sum(1 for item in roster["items"] if not item["headset"]) == split["far_field_recordings"]
    assert abs(sum(item["audio_seconds"] for item in roster["items"]) - split["audio_seconds_total"]) < 1e-9

    derived = document["derived_from"]
    _closure_raw, closure, closure_digest = _committed(derived["sibling_roster"]["repo_relpath"])
    _full_raw, full, full_digest = _committed(derived["source_roster"]["repo_relpath"])
    assert closure_digest == derived["sibling_roster"]["sha256"]
    assert full_digest == derived["source_roster"]["sha256"]
    closure_ids = [item["sample_id"] for item in closure["items"]]
    full_ids = [item["sample_id"] for item in full["items"]]
    assert identity_hash(closure_ids) == derived["sibling_roster"]["split_identity_hash"] == COMMITTED_CLOSURE_IDENTITY
    assert identity_hash(full_ids) == derived["source_roster"]["split_identity_hash"] == COMMITTED_FULL_IDENTITY
    assert not set(ids) & set(closure_ids)
    assert set(ids) | set(closure_ids) == set(full_ids)
    arithmetic = derived["partition_proof_receipt"]["arithmetic"]
    assert arithmetic["union_split_identity_hash"] == identity_hash(set(ids) | set(closure_ids))
    assert arithmetic["intersection_recordings"] == 0 and arithmetic["union_equals_parent"] is True
    proof_digest = hashlib.sha256(
        (repo_root / derived["partition_proof_receipt"]["repo_relpath"]).read_bytes()
    ).hexdigest()
    assert proof_digest == derived["partition_proof_receipt"]["sha256"] == split["disjointness_receipt_sha256"]

    # The receipt's media bytes are the committed D1 supplement's per-row bytes
    # summed over exactly the sample's ids; no audio is opened here either.
    _d1_raw, d1, _d1_digest = _committed("docs/receipts/artifacts/d1-slurp-test-full.json")
    by_id = {row["id"]: row["bytes"] for row in d1["manifest"]}
    assert sum(by_id[value] for value in ids) == split["media_bytes_total"]


@pytest.mark.parametrize("run_id", SAMPLE_PREPARATION_RUN_IDS + SAMPLE_READ_RUN_IDS)
def test_the_sample_allowance_accepts_a_sample_plan_for_every_permitted_run_id(run_id):
    """The one acceptance path, on the committed bytes, resolved against the
    module's own checkout root exactly as a production caller resolves it."""

    validated = sample_plan(run_id=run_id).validate()
    assert validated.split_role == FINAL_REPORT_SPLIT_ROLE
    assert validated.split_identity_hash == COMMITTED_SAMPLE_IDENTITY
    document = require_owner_split_allowance(
        run_id=run_id,
        execution_profile=FINAL_REPORT_EXECUTION_PROFILE,
        carrier_lock_key=CARRIER,
        split_identity_hash=COMMITTED_SAMPLE_IDENTITY,
        owner_allowance=validated.owner_allowance,
    )
    assert document["status"] == "authorised"
    assert run_id in document["permitted_run_ids"]


def test_the_sample_allowance_passes_the_gate_on_the_committed_receipts():
    """Gate level: allowance, no construction-visible arm, the partition-aware
    disjointness re-proof against every committed ``slurp`` roster receipt,
    and the one-attempt budget (no attempt exists) -- all on committed bytes."""

    gate = _committed_gate()
    for run_id in (SAMPLE_READ_RUN_IDS[0], SAMPLE_READ_RUN_IDS[1], SAMPLE_PREPARATION_RUN_IDS[0]):
        gate._require_final_report_isolation(sample_plan(run_id=run_id), None)


def test_the_sample_allowance_refuses_the_closure_identity_naming_both_hashes():
    with pytest.raises(ExecutionScopeError) as error:
        sample_plan(split_identity_hash=COMMITTED_CLOSURE_IDENTITY).validate()
    message = str(error.value)
    assert "authorises split identity" in message
    assert COMMITTED_SAMPLE_IDENTITY in message
    assert COMMITTED_CLOSURE_IDENTITY in message

    gate = _committed_gate()
    with pytest.raises(ExecutionScopeError) as gate_error:
        gate._require_final_report_isolation(
            sample_plan(split_identity_hash=COMMITTED_CLOSURE_IDENTITY), None
        )
    assert COMMITTED_CLOSURE_IDENTITY in str(gate_error.value)


def test_the_sample_allowance_refuses_the_full_parent_identity():
    with pytest.raises(ExecutionScopeError) as error:
        sample_plan(split_identity_hash=COMMITTED_FULL_IDENTITY).validate()
    assert COMMITTED_FULL_IDENTITY in str(error.value)


def test_the_sample_allowance_refuses_a_paper_scale_confirmatory_profile():
    with pytest.raises(ExecutionScopeError):
        sample_plan(execution_profile="paper-scale-confirmatory").validate()
    _raw, _document, digest = _committed(SAMPLE_ALLOWANCE_RELPATH)
    with pytest.raises(ExecutionScopeError) as error:
        require_owner_split_allowance(
            run_id=SAMPLE_READ_RUN_IDS[0],
            execution_profile="paper-scale-confirmatory",
            carrier_lock_key=CARRIER,
            split_identity_hash=COMMITTED_SAMPLE_IDENTITY,
            owner_allowance={"path": SAMPLE_ALLOWANCE_RELPATH, "sha256": digest},
        )
    assert "runs only under execution profile 'bounded-discovery-probe'" in str(error.value)


def test_the_sample_allowance_refuses_a_run_id_the_owner_did_not_name():
    with pytest.raises(ExecutionScopeError) as error:
        sample_plan(run_id="SAEA-SLURP-TEST-SAMPLE-3010-DIRECT-V1").validate()
    assert "is not in the owner allowance's permitted_run_ids" in str(error.value)


def test_the_full_receipt_still_refuses_after_the_sample_signature():
    """Signing the sample changed nothing for the FULL split: its receipt is
    byte-for-byte the pending-owner document, and it refuses a FULL plan and a
    sample plan alike at check 6."""

    raw, document, digest = _committed(ALLOWANCE_RELPATH)
    assert document["status"] == "pending-owner"
    for run_id, split_identity in (
        (PREP_RUN_ID, COMMITTED_FULL_IDENTITY),
        (READ_RUN_ID, COMMITTED_FULL_IDENTITY),
        (PREP_RUN_ID, COMMITTED_SAMPLE_IDENTITY),
    ):
        with pytest.raises(ExecutionScopeError) as error:
            plan(
                run_id=run_id,
                split_identity_hash=split_identity,
                owner_allowance={"path": ALLOWANCE_RELPATH, "sha256": digest},
            ).validate()
        assert "status is 'pending-owner', not 'authorised'" in str(error.value)


def test_no_committed_receipt_authorises_the_closure_identity():
    """The closure stays pending-owner until the Stage-3 closure read
    (decision 151): no receipt under docs/receipts/owner/ binds its hash with
    status ``authorised``."""

    owner_dir = _repo_root() / OWNER_SPLIT_ALLOWANCE_RELDIR
    receipts = sorted(owner_dir.glob("*.json"))
    assert receipts
    for path in receipts:
        document = json.loads(path.read_text(encoding="utf-8"))
        if document.get("schema") != OWNER_SPLIT_ALLOWANCE_SCHEMA:
            continue
        bound = document["split"]["split_identity_hash"]
        if bound == COMMITTED_CLOSURE_IDENTITY:
            assert document["status"] != "authorised", path
        if document["status"] == "authorised":
            assert bound == COMMITTED_SAMPLE_IDENTITY, path
