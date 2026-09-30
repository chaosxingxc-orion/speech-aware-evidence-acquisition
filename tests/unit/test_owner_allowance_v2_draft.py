"""The DRAFT test-sample allowance v2 (owner decision 207, proposed 2026-09-30).

``docs/receipts/owner/2026-09-30-slurp-test-sample-allowance-v2.json`` succeeds the
decision-151 allowance v1 by adding exactly the two native contact-fit run ids the
milestone cells need. It is committed as ``status: "draft-awaiting-owner-signature"``
so the owner can sign it with one confirmation. These tests prove:

1. the committed draft is REFUSED by ``require_owner_split_allowance`` (check 6);
2. a temp copy with only ``status`` flipped to ``authorised`` accepts both FIT ids
   and still accepts all nine v1 ids;
3. every v1 term is carried unchanged, and ``supersedes`` pins v1's exact bytes.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.contracts import ExecutionScopeError
from speech_aware_evidence_acquisition.contracts.plan import require_owner_split_allowance

REPO = Path(__file__).resolve().parents[2]
V1 = "docs/receipts/owner/2026-09-27-slurp-test-sample-allowance-v1.json"
V2 = "docs/receipts/owner/2026-09-30-slurp-test-sample-allowance-v2.json"
FIT_IDS = [
    "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-00-PLAN-FIT-V1",
    "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-01-FIT-V1",
]
#: Keys v2 adds or changes; every other v1 key must be byte-equal in value.
V2_ONLY = {
    "status_meaning_when_authorised",
    "supersedes",
    "amendment",
    "signature",
    "owner_confirmation_instructions",
}
V2_CHANGED = {"status", "status_meaning", "permitted_run_ids", "preparation_run_ids", "run_ids"}


def _load(relpath: str) -> tuple[bytes, dict]:
    raw = (REPO / relpath).read_bytes()
    return raw, json.loads(raw.decode("utf-8"))


def _call(document_raw: bytes, run_id: str, root: Path, relpath: str = V2):
    target = root / relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(document_raw)
    split = json.loads(document_raw.decode("utf-8"))["split"]
    return require_owner_split_allowance(
        run_id=run_id,
        execution_profile="bounded-discovery-probe",
        carrier_lock_key=split["carrier_lock_key"],
        split_identity_hash=split["split_identity_hash"],
        owner_allowance={"path": relpath, "sha256": hashlib.sha256(document_raw).hexdigest()},
        source_root=root,
    )


def test_committed_draft_is_refused_for_every_id() -> None:
    raw, v2 = _load(V2)
    assert v2["status"] == "draft-awaiting-owner-signature"
    for run_id in v2["permitted_run_ids"]:
        with pytest.raises(ExecutionScopeError, match="status is 'draft-awaiting-owner-signature'"):
            require_owner_split_allowance(
                run_id=run_id,
                execution_profile="bounded-discovery-probe",
                carrier_lock_key=v2["split"]["carrier_lock_key"],
                split_identity_hash=v2["split"]["split_identity_hash"],
                owner_allowance={"path": V2, "sha256": hashlib.sha256(raw).hexdigest()},
            )


def test_signed_copy_accepts_fit_ids_and_all_v1_ids(tmp_path: Path) -> None:
    _, v1 = _load(V1)
    _, v2 = _load(V2)
    signed = dict(v2, status="authorised")
    signed_raw = (json.dumps(signed, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    for run_id in FIT_IDS + list(v1["permitted_run_ids"]):
        document = _call(signed_raw, run_id, tmp_path)
        assert run_id in document["permitted_run_ids"]
    with pytest.raises(ExecutionScopeError, match="is not in the owner allowance"):
        _call(signed_raw, "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-06-FIT-V1", tmp_path)


def test_fit_ids_are_preparations_not_reads() -> None:
    _, v1 = _load(V1)
    _, v2 = _load(V2)
    assert v2["permitted_run_ids"] == v1["permitted_run_ids"] + FIT_IDS
    assert v2["preparation_run_ids"] == v1["preparation_run_ids"] + FIT_IDS
    assert v2["read_run_ids"] == v1["read_run_ids"]
    for run_id in FIT_IDS:
        entry = v2["run_ids"][run_id]
        assert entry["kind"] == "preparation"
        assert entry["annotation"] == "native_contact_fit, 0 core contacts, fit measurement only"
        assert entry["core_contacts"] == 0


def test_every_other_term_is_identical_to_v1() -> None:
    v1_raw, v1 = _load(V1)
    _, v2 = _load(V2)
    assert set(v2) == set(v1) | V2_ONLY
    for key in set(v1) - V2_CHANGED:
        assert v2[key] == v1[key], key
    assert v2["status_meaning_when_authorised"] == v1["status_meaning"]
    for run_id, entry in v1["run_ids"].items():
        assert v2["run_ids"][run_id] == entry
    assert set(v2["run_ids"]) == set(v1["run_ids"]) | set(FIT_IDS)
    assert v2["supersedes"]["path"] == V1
    assert v2["supersedes"]["sha256"] == hashlib.sha256(v1_raw).hexdigest()
    assert v2["amendment"]["date"] == "2026-09-30"
    assert v2["amendment"]["adds_run_ids"] == FIT_IDS
    assert all(v2["signature"][k] is None for k in ("signed_at", "signed_by"))
