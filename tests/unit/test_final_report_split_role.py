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
