"""The SIGNED test-sample allowance v2 (owner decision 207, signed 2026-09-30).

``docs/receipts/owner/2026-09-30-slurp-test-sample-allowance-v2.json`` succeeds the
decision-151 allowance v1 by adding exactly the two native contact-fit run ids the
milestone cells need. It was committed as a draft and signed by the owner's
confirmation in conversation (verbatim in ``signature.owner_words_verbatim``; English:
"Decision 207: agreed"). These tests prove:

1. the committed signed bytes are ACCEPTED by ``require_owner_split_allowance`` for all
   eleven permitted ids (the nine v1 ids and the two FIT ids) and REFUSE a twelfth;
2. an otherwise identical copy still reading the draft status is refused (check 6);
3. every v1 term is carried unchanged, and ``supersedes`` pins v1's exact bytes.

The file name keeps ``_draft`` for history; the content is the signed state.
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
#: Keys v2 adds; every other v1 key must be equal in value except V2_CHANGED.
V2_ONLY = {"supersedes", "amendment", "signature", "owner_confirmation_instructions"}
V2_CHANGED = {"permitted_run_ids", "preparation_run_ids", "run_ids"}


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


def test_committed_signed_bytes_accept_all_eleven_ids_and_refuse_a_twelfth() -> None:
    raw, v2 = _load(V2)
    assert v2["status"] == "authorised"
    assert len(v2["permitted_run_ids"]) == 11
    pin = {"path": V2, "sha256": hashlib.sha256(raw).hexdigest()}

    def call(run_id: str):
        return require_owner_split_allowance(
            run_id=run_id,
            execution_profile="bounded-discovery-probe",
            carrier_lock_key=v2["split"]["carrier_lock_key"],
            split_identity_hash=v2["split"]["split_identity_hash"],
            owner_allowance=pin,
        )

    for run_id in v2["permitted_run_ids"]:
        assert run_id in call(run_id)["permitted_run_ids"]
    with pytest.raises(ExecutionScopeError, match="is not in the owner allowance"):
        call("SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-06-V1")


def test_a_draft_status_copy_is_refused(tmp_path: Path) -> None:
    _, v2 = _load(V2)
    draft = dict(v2, status="draft-awaiting-owner-signature")
    draft_raw = (json.dumps(draft, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    for run_id in FIT_IDS:
        with pytest.raises(ExecutionScopeError, match="status is 'draft-awaiting-owner-signature'"):
            _call(draft_raw, run_id, tmp_path)


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


def test_every_other_term_is_identical_to_v1_and_the_signature_is_filled() -> None:
    v1_raw, v1 = _load(V1)
    _, v2 = _load(V2)
    assert set(v2) == set(v1) | V2_ONLY
    for key in set(v1) - V2_CHANGED:
        assert v2[key] == v1[key], key
    for run_id, entry in v1["run_ids"].items():
        assert v2["run_ids"][run_id] == entry
    assert set(v2["run_ids"]) == set(v1["run_ids"]) | set(FIT_IDS)
    assert v2["supersedes"]["path"] == V1
    assert v2["supersedes"]["sha256"] == hashlib.sha256(v1_raw).hexdigest()
    assert v2["amendment"]["date"] == "2026-09-30"
    assert v2["amendment"]["adds_run_ids"] == FIT_IDS
    signature = v2["signature"]
    assert signature["decision"] == 207
    assert signature["signed_by"] == "owner"
    assert signature["signed_at"].startswith("2026-09-30T")
    assert signature["owner_words_verbatim"] == "\u51b3\u7b56207\uff1a\u540c\u610f"
    assert signature["owner_words_english"] == "Decision 207: agreed"
