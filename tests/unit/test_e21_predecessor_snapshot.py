"""The sealed-predecessor binding (``core.predecessor_snapshot``).

The binding is what lets KC-E1f cost ONE contact per window: pass 1 is the
sealed comparator's own bytes rather than a fresh decode. Everything below is
a refusal test, because the only interesting property of a binding is what it
declines to read.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.predecessor_snapshot import (
    BINDING_SCHEMA,
    SNAPSHOT_SCHEMA,
    PredecessorSnapshotError,
    binding_from_values,
    load_predecessor_binding,
    window_text_chain_sha256,
)

RUN_ID = "SAEA-E21-TEST-PREDECESSOR"
ATTEMPT_ID = "attempt-20260907T000000Z-test01"
ARTIFACT_RELPATH = f"derived/e21-predecessor/{RUN_ID}/{ATTEMPT_ID}/window-hypotheses.json"


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _rows() -> list[dict[str, object]]:
    texts = {
        ("4000001", 1): "Good morning and welcome to the call",
        ("4000001", 2): "I will hand over to Brett Ponton now",
        ("4000002", 1): "Revenue grew eleven percent in the quarter",
    }
    rows: list[dict[str, object]] = []
    for (sample_id, index), text in texts.items():
        rows.append(
            {
                "window_id": f"{sample_id}#w{index:04d}",
                "sample_id": sample_id,
                "window_index": index,
                "request_id": f"req-{sample_id}-i{index:04d}",
                "start_seconds": 90.0 * (index - 1),
                "end_seconds": 90.0 * index,
                "audio_seconds": 90.0,
                "saturated": False,
                "text": text,
                "text_sha256": _sha256_text(text),
                "text_chars": len(text),
                "text_whitespace_tokens": len(text.split()),
                "prompt_tokens": 1232,
                "completion_tokens": 270,
            }
        )
    return rows


def _write_world(tmp_path: Path, *, rows=None, receipt_overrides=None, artifact_overrides=None):
    rows = _rows() if rows is None else rows
    data_root = tmp_path / "data"
    docs = tmp_path / "docs" / "receipts"
    docs.mkdir(parents=True, exist_ok=True)
    artifact_path = data_root / ARTIFACT_RELPATH
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot = {
        "schema": SNAPSHOT_SCHEMA,
        "run_id": RUN_ID,
        "attempt_id": ATTEMPT_ID,
        "windows": len(rows),
        "calls": len({row["sample_id"] for row in rows}),
        "rows": rows,
    }
    snapshot.update(artifact_overrides or {})
    artifact_path.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    blob = artifact_path.read_bytes()
    receipt = {
        "schema": BINDING_SCHEMA,
        "run_id": RUN_ID,
        "attempt_id": ATTEMPT_ID,
        "artifact": {
            "relpath": ARTIFACT_RELPATH,
            "sha256": hashlib.sha256(blob).hexdigest(),
            "bytes": len(blob),
        },
        "windows": len(rows),
        "calls": len({row["sample_id"] for row in rows}),
        "window_text_sha256_chain": window_text_chain_sha256(rows),
        "source": {"manifest_sha256": "0" * 64},
    }
    receipt.update(receipt_overrides or {})
    receipt_path = docs / "binding.json"
    receipt_path.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return receipt_path, data_root, artifact_path


class TestHappyPath:
    def test_a_verified_binding_reads_back_in_stitch_order(self, tmp_path):
        receipt_path, data_root, _artifact = _write_world(tmp_path)
        snapshot = load_predecessor_binding(receipt_path, data_root)
        assert snapshot.run_id == RUN_ID
        assert snapshot.window_count == 3
        assert snapshot.call_count == 2
        windows = snapshot.for_sample("4000001")
        assert [window.window_index for window in windows] == [1, 2]
        assert windows[1].text.endswith("Brett Ponton now")
        assert windows[0].completion_tokens == 270

    def test_the_configured_receipt_digest_is_enforced_when_given(self, tmp_path):
        receipt_path, data_root, _artifact = _write_world(tmp_path)
        digest = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
        snapshot = load_predecessor_binding(
            receipt_path, data_root, expected_receipt_sha256=digest
        )
        assert snapshot.receipt_sha256 == digest

    def test_an_unknown_sample_is_refused_rather_than_returned_empty(self, tmp_path):
        receipt_path, data_root, _artifact = _write_world(tmp_path)
        snapshot = load_predecessor_binding(receipt_path, data_root)
        with pytest.raises(PredecessorSnapshotError, match="no window for sample"):
            snapshot.for_sample("4009999")


class TestRefusals:
    def test_a_receipt_whose_bytes_moved_is_refused(self, tmp_path):
        receipt_path, data_root, _artifact = _write_world(tmp_path)
        with pytest.raises(PredecessorSnapshotError, match="hashes to"):
            load_predecessor_binding(
                receipt_path, data_root, expected_receipt_sha256="f" * 64
            )

    def test_a_foreign_schema_is_refused(self, tmp_path):
        receipt_path, data_root, _artifact = _write_world(
            tmp_path, receipt_overrides={"schema": "something-else-v1"}
        )
        with pytest.raises(PredecessorSnapshotError, match="not a saea-e21-predecessor-binding"):
            load_predecessor_binding(receipt_path, data_root)

    def test_a_missing_artifact_is_refused_and_says_where_it_lives(self, tmp_path):
        receipt_path, data_root, artifact = _write_world(tmp_path)
        artifact.unlink()
        with pytest.raises(PredecessorSnapshotError, match="SPEECHRL_DATA_DIR"):
            load_predecessor_binding(receipt_path, data_root)

    def test_a_tampered_artifact_byte_is_refused(self, tmp_path):
        receipt_path, data_root, artifact = _write_world(tmp_path)
        blob = artifact.read_text(encoding="utf-8")
        # A SAME-LENGTH tamper, so the size check cannot catch it and the
        # content hash has to.
        artifact.write_text(blob.replace("Ponton", "Pontan"), encoding="utf-8")
        with pytest.raises(PredecessorSnapshotError, match="hashes to"):
            load_predecessor_binding(receipt_path, data_root)

    def test_a_size_disagreement_is_refused_before_the_content_hash(self, tmp_path):
        receipt_path, data_root, _artifact = _write_world(tmp_path)
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["artifact"]["bytes"] = 1
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        with pytest.raises(PredecessorSnapshotError, match="bytes, the receipt says"):
            load_predecessor_binding(receipt_path, data_root)

    def test_an_artifact_naming_another_attempt_is_refused(self, tmp_path):
        receipt_path, data_root, _artifact = _write_world(
            tmp_path, artifact_overrides={"attempt_id": "attempt-somewhere-else"}
        )
        with pytest.raises(PredecessorSnapshotError, match="attempt_id"):
            load_predecessor_binding(receipt_path, data_root)

    def test_a_row_count_disagreement_is_refused(self, tmp_path):
        receipt_path, data_root, _artifact = _write_world(
            tmp_path, receipt_overrides={"windows": 99}
        )
        with pytest.raises(PredecessorSnapshotError, match="rows, the receipt says"):
            load_predecessor_binding(receipt_path, data_root)

    def test_a_call_count_disagreement_is_refused(self, tmp_path):
        receipt_path, data_root, _artifact = _write_world(
            tmp_path, receipt_overrides={"calls": 7}
        )
        with pytest.raises(PredecessorSnapshotError, match="calls, the receipt says"):
            load_predecessor_binding(receipt_path, data_root)

    def test_a_row_whose_text_does_not_hash_to_its_own_digest_is_refused(self, tmp_path):
        rows = _rows()
        rows[0]["text_sha256"] = "a" * 64
        receipt_path, data_root, _artifact = _write_world(tmp_path, rows=rows)
        with pytest.raises(PredecessorSnapshotError, match="recorded text_sha256"):
            load_predecessor_binding(receipt_path, data_root)

    def test_a_duplicate_window_is_refused(self, tmp_path):
        rows = _rows()
        rows.append(dict(rows[0]))
        receipt_path, data_root, _artifact = _write_world(tmp_path, rows=rows)
        with pytest.raises(PredecessorSnapshotError, match="duplicate window"):
            load_predecessor_binding(receipt_path, data_root)

    def test_a_reordered_artifact_breaks_the_chain_hash(self, tmp_path):
        rows = _rows()
        receipt_path, data_root, _artifact = _write_world(tmp_path, rows=rows)
        # Re-write the artifact with the rows reversed, and repair the artifact
        # digest in the receipt: only the chain hash can catch this.
        artifact = data_root / ARTIFACT_RELPATH
        snapshot = json.loads(artifact.read_text(encoding="utf-8"))
        snapshot["rows"] = list(reversed(snapshot["rows"]))
        artifact.write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        blob = artifact.read_bytes()
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["artifact"]["sha256"] = hashlib.sha256(blob).hexdigest()
        receipt["artifact"]["bytes"] = len(blob)
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        with pytest.raises(PredecessorSnapshotError, match="window/text chain"):
            load_predecessor_binding(receipt_path, data_root)


class TestConfigBinding:
    def test_a_well_formed_binding_resolves(self):
        relpath, digest = binding_from_values(
            {
                "predecessor_snapshot": {
                    "receipt_relpath": "receipts/e21-predecessor.json",
                    "receipt_sha256": "b" * 64,
                }
            }
        )
        assert relpath == "receipts/e21-predecessor.json"
        assert digest == "b" * 64

    @pytest.mark.parametrize(
        "block",
        [
            None,
            {},
            {"receipt_relpath": "receipts/x.json"},
            {"receipt_relpath": "/abs/x.json", "receipt_sha256": "b" * 64},
            {"receipt_relpath": "receipts\\x.json", "receipt_sha256": "b" * 64},
            {"receipt_relpath": "receipts/../x.json", "receipt_sha256": "b" * 64},
            {"receipt_relpath": "receipts/x.json", "receipt_sha256": "NOTAHASH"},
            {
                "receipt_relpath": "receipts/x.json",
                "receipt_sha256": "b" * 64,
                "extra": 1,
            },
        ],
    )
    def test_malformed_bindings_refuse_rather_than_guess(self, block):
        with pytest.raises(PredecessorSnapshotError):
            binding_from_values({"predecessor_snapshot": block})


class TestCommittedReceipt:
    """The real receipt this repository committed, read as a document only.

    No artifact is opened here: the artifact lives under ``SPEECHRL_DATA_DIR``
    and this assertion has to hold on a machine that has never materialized the
    corpus.
    """

    def test_the_committed_binding_is_shaped_and_content_free(self):
        path = (
            Path(__file__).resolve().parents[2]
            / "docs/receipts/e21-predecessor-full44-direct-baseline-v2.json"
        )
        receipt = json.loads(path.read_text(encoding="utf-8"))
        assert receipt["schema"] == BINDING_SCHEMA
        assert receipt["run_id"] == "SAEA-E21-FULL44-DIRECT-BASELINE-V2"
        assert receipt["windows"] == 1593
        assert receipt["calls"] == 44
        assert receipt["saturated_windows"] == 0
        assert len(receipt["per_call"]) == 44
        assert all(
            entry["check"] == "PASS"
            for entry in receipt["identity_anchors"].values()
            if isinstance(entry, dict)
        )
        # Content-free: the only long strings are hashes and prose. No row
        # carries text, and no key named "text" survives anywhere.
        blob = json.dumps(receipt)
        assert '"text"' not in blob
        assert '"rows"' not in blob
