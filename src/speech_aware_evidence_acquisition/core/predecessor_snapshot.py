"""The sealed-predecessor binding for Earnings-21 windows.

What it is for
--------------
KC-E1f is a second pass over windows a sealed run already decoded. Its pass 1
is NOT re-flown: the comparator ``SAEA-E21-FULL44-DIRECT-BASELINE-V2`` supplies
each window's pass-1 hypothesis, so the cell costs ONE contact per window and
the deletion profile it is measured against is the comparator's own bytes
rather than a fresh decode that would have to be paired all over again.

The same problem the SLURP slot stage solved, in the Earnings shape
------------------------------------------------------------------
``rails.phase_material.sealed_states_from_manifest`` reads a sealed bundle and
rebuilds one ``AgentStateArtifact`` per SAMPLE, bound to that row's own
``request_sha256``/``response_text_sha256``. Earnings-21 needs the same thing
one level finer: a sample is a 40-75 minute call whose sealed outputs row is a
single stitched hypothesis, and the unit a KC-E1f contact happens at is the
90-second WINDOW. The per-window hypotheses are recoverable -- and are
recovered, never re-derived -- by ``analysis.e21_window_pairing.
stitched_windows_from_trace``, which the window-pairing receipt proves rebuilds
every sealed hypothesis byte for byte.

Those recovered hypotheses are per-request derivatives of sealed model outputs,
so they live under ``SPEECHRL_DATA_DIR`` where those live and never in Git.
What a config fragment pins instead is a CONTENT-FREE receipt: the artifact's
path and SHA-256, the source manifest/outputs/trace hashes, the window and call
counts, and a chain hash over ``(window_id, text_sha256)`` pairs. No hypothesis
text, no reference transcript, no gold: a reader of the repository learns that
a specific 1,593-row artifact was bound and can verify it, and learns nothing
about what any window said. Exactly the discipline KC-S1b's ``sealed-manifest``
binding follows, with the receipt playing the role its ``manifest_sha256`` did.

Fail-closed, in this order
--------------------------
:func:`load_predecessor_binding` refuses on a receipt whose bytes do not hash to
the configured digest, a receipt of the wrong schema, a missing artifact, an
artifact whose bytes or size disagree with the receipt, an artifact naming a
different run or attempt, a row count or call count that disagrees, a row whose
text does not hash to its own recorded digest, and a chain hash that does not
re-derive. Only then does any window text become readable. A caller that wants
one sample's windows asks for them by sample id and gets them in stitch order
or an error -- never a partial list.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from .base import CoreError

#: The artifact written under ``SPEECHRL_DATA_DIR`` (carries the text).
SNAPSHOT_SCHEMA = "saea-e21-predecessor-snapshot-v1"
#: The receipt committed under ``docs/receipts/`` (carries no text).
BINDING_SCHEMA = "saea-e21-predecessor-binding-v1"

#: Config key a baseline fragment declares the binding under.
CONFIG_KEY = "predecessor_snapshot"
#: Its two required members: a path relative to ``<repo_root>/docs`` and the
#: receipt's own SHA-256, so selecting different bytes changes the composed
#: protocol identity exactly as ``d1_evidence_supplement`` does.
CONFIG_MEMBERS = ("receipt_relpath", "receipt_sha256")


class PredecessorSnapshotError(CoreError):
    """A sealed-predecessor binding refuses -- fail closed, never guess."""


@dataclass(frozen=True)
class PredecessorWindow:
    """One sealed pass-1 window, as the comparator actually emitted it."""

    window_id: str
    sample_id: str
    window_index: int
    request_id: str
    start_seconds: float
    end_seconds: float
    audio_seconds: float
    saturated: bool
    text: str
    text_sha256: str
    completion_tokens: int | None = None
    prompt_tokens: int | None = None


@dataclass(frozen=True)
class PredecessorSnapshot:
    """A verified binding: the receipt's identity plus the verified rows."""

    run_id: str
    attempt_id: str
    receipt_relpath: str
    receipt_sha256: str
    artifact_relpath: str
    artifact_sha256: str
    source: Mapping[str, str]
    windows: Mapping[str, PredecessorWindow]
    order: Mapping[str, tuple[str, ...]]

    def for_sample(self, sample_id: str) -> tuple[PredecessorWindow, ...]:
        """This call's windows, in stitch order. Refuses an unknown sample."""

        try:
            ids = self.order[sample_id]
        except KeyError:
            raise PredecessorSnapshotError(
                f"sealed predecessor {self.run_id} carries no window for sample "
                f"{sample_id!r}"
            ) from None
        return tuple(self.windows[window_id] for window_id in ids)

    @property
    def call_count(self) -> int:
        return len(self.order)

    @property
    def window_count(self) -> int:
        return len(self.windows)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def window_text_chain_sha256(rows: Sequence[Mapping[str, object]]) -> str:
    """The receipt's content-free fingerprint of the whole artifact.

    A canonical JSON list of ``[window_id, text_sha256]`` pairs in the
    artifact's own row order, hashed once. It pins WHICH hypothesis each window
    carries without carrying any of them, and it changes if a single row is
    reordered, retitled or re-decoded.
    """

    payload = [[str(row["window_id"]), str(row["text_sha256"])] for row in rows]
    blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def binding_from_values(values: Mapping[str, object]) -> tuple[str, str]:
    """``(receipt_relpath, receipt_sha256)`` out of a composed config.

    Applies the same path refusals every other path-shaped config value in this
    study gets -- no absolute path, no backslash, no empty or traversal segment
    -- before the string is joined onto a filesystem path.
    """

    raw = values.get(CONFIG_KEY)
    if not isinstance(raw, Mapping):
        raise PredecessorSnapshotError(
            f"config {CONFIG_KEY} must be an object with {list(CONFIG_MEMBERS)}, "
            f"got {raw!r}"
        )
    missing = [key for key in CONFIG_MEMBERS if key not in raw]
    if missing:
        raise PredecessorSnapshotError(f"config {CONFIG_KEY} lacks {missing}")
    unknown = sorted(set(raw) - set(CONFIG_MEMBERS))
    if unknown:
        raise PredecessorSnapshotError(
            f"config {CONFIG_KEY} carries unknown members {unknown}"
        )
    relpath = raw["receipt_relpath"]
    digest = raw["receipt_sha256"]
    if not isinstance(relpath, str) or not relpath:
        raise PredecessorSnapshotError(
            f"config {CONFIG_KEY}.receipt_relpath must be a non-empty string, got {relpath!r}"
        )
    if "\\" in relpath or relpath.startswith("/"):
        raise PredecessorSnapshotError(
            f"config {CONFIG_KEY}.receipt_relpath must be a relative POSIX path, got {relpath!r}"
        )
    if any(part in ("", ".", "..") for part in relpath.split("/")):
        raise PredecessorSnapshotError(
            f"config {CONFIG_KEY}.receipt_relpath has an empty or traversal segment: {relpath!r}"
        )
    if not isinstance(digest, str) or len(digest) != 64 or not all(
        character in "0123456789abcdef" for character in digest
    ):
        raise PredecessorSnapshotError(
            f"config {CONFIG_KEY}.receipt_sha256 must be a lowercase hex sha256, got {digest!r}"
        )
    return relpath, digest


def load_predecessor_binding(
    receipt_path: Path | str,
    data_root: Path | str,
    *,
    expected_receipt_sha256: str | None = None,
) -> PredecessorSnapshot:
    """Verify the binding end to end and return the readable snapshot.

    Module docstring for the refusal order. Nothing in the artifact is read as
    a hypothesis until every hash on the chain has been re-derived here.
    """

    receipt_path = Path(receipt_path)
    if not receipt_path.is_file():
        raise PredecessorSnapshotError(
            f"sealed predecessor receipt {receipt_path} does not exist"
        )
    measured_receipt = _sha256_file(receipt_path)
    if expected_receipt_sha256 is not None and measured_receipt != expected_receipt_sha256:
        raise PredecessorSnapshotError(
            f"sealed predecessor receipt {receipt_path} hashes to {measured_receipt}, "
            f"not the configured {expected_receipt_sha256}"
        )
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PredecessorSnapshotError(
            f"cannot read sealed predecessor receipt {receipt_path}: {error}"
        ) from error
    if not isinstance(receipt, Mapping) or receipt.get("schema") != BINDING_SCHEMA:
        raise PredecessorSnapshotError(
            f"{receipt_path} is not a {BINDING_SCHEMA} document"
        )

    artifact_block = receipt.get("artifact")
    if not isinstance(artifact_block, Mapping):
        raise PredecessorSnapshotError(f"{receipt_path} carries no artifact block")
    artifact_relpath = str(artifact_block["relpath"])
    artifact_path = Path(data_root) / artifact_relpath
    if not artifact_path.is_file():
        raise PredecessorSnapshotError(
            f"sealed predecessor artifact {artifact_path} does not exist; it is a "
            "per-request derivative of sealed outputs and lives under "
            "SPEECHRL_DATA_DIR, never in Git"
        )
    measured_bytes = artifact_path.stat().st_size
    if measured_bytes != int(artifact_block["bytes"]):
        raise PredecessorSnapshotError(
            f"sealed predecessor artifact {artifact_path} is {measured_bytes} bytes, "
            f"the receipt says {artifact_block['bytes']}"
        )
    measured_artifact = _sha256_file(artifact_path)
    if measured_artifact != str(artifact_block["sha256"]):
        raise PredecessorSnapshotError(
            f"sealed predecessor artifact {artifact_path} hashes to {measured_artifact}, "
            f"not the receipt's {artifact_block['sha256']}"
        )

    snapshot = json.loads(artifact_path.read_text(encoding="utf-8"))
    if not isinstance(snapshot, Mapping) or snapshot.get("schema") != SNAPSHOT_SCHEMA:
        raise PredecessorSnapshotError(
            f"{artifact_path} is not a {SNAPSHOT_SCHEMA} document"
        )
    for key in ("run_id", "attempt_id"):
        if str(snapshot.get(key)) != str(receipt.get(key)):
            raise PredecessorSnapshotError(
                f"sealed predecessor artifact {key} {snapshot.get(key)!r} does not match "
                f"the receipt's {receipt.get(key)!r}"
            )
    rows = snapshot.get("rows")
    if not isinstance(rows, list) or not rows:
        raise PredecessorSnapshotError(f"{artifact_path} carries no rows")
    if len(rows) != int(receipt["windows"]):
        raise PredecessorSnapshotError(
            f"sealed predecessor artifact carries {len(rows)} rows, the receipt says "
            f"{receipt['windows']}"
        )

    windows: dict[str, PredecessorWindow] = {}
    order: dict[str, list[str]] = {}
    for row in rows:
        window_id = str(row["window_id"])
        if window_id in windows:
            raise PredecessorSnapshotError(
                f"sealed predecessor artifact carries duplicate window {window_id!r}"
            )
        text = str(row["text"])
        recorded = str(row["text_sha256"])
        if _sha256_text(text) != recorded:
            raise PredecessorSnapshotError(
                f"sealed predecessor window {window_id!r} does not hash to its own "
                "recorded text_sha256"
            )
        sample_id = str(row["sample_id"])
        windows[window_id] = PredecessorWindow(
            window_id=window_id,
            sample_id=sample_id,
            window_index=int(row["window_index"]),
            request_id=str(row["request_id"]),
            start_seconds=float(row["start_seconds"]),
            end_seconds=float(row["end_seconds"]),
            audio_seconds=float(row["audio_seconds"]),
            saturated=bool(row["saturated"]),
            text=text,
            text_sha256=recorded,
            completion_tokens=(
                None if row.get("completion_tokens") is None else int(row["completion_tokens"])
            ),
            prompt_tokens=(
                None if row.get("prompt_tokens") is None else int(row["prompt_tokens"])
            ),
        )
        order.setdefault(sample_id, []).append(window_id)
    if len(order) != int(receipt["calls"]):
        raise PredecessorSnapshotError(
            f"sealed predecessor artifact carries {len(order)} calls, the receipt says "
            f"{receipt['calls']}"
        )
    chain = window_text_chain_sha256(rows)
    if chain != str(receipt["window_text_sha256_chain"]):
        raise PredecessorSnapshotError(
            "the sealed predecessor artifact's window/text chain hashes to "
            f"{chain}, not the receipt's {receipt['window_text_sha256_chain']}"
        )
    return PredecessorSnapshot(
        run_id=str(receipt["run_id"]),
        attempt_id=str(receipt["attempt_id"]),
        receipt_relpath=str(receipt.get("receipt_relpath", receipt_path.name)),
        receipt_sha256=measured_receipt,
        artifact_relpath=artifact_relpath,
        artifact_sha256=measured_artifact,
        source=dict(receipt.get("source", {})),
        windows=windows,
        order={sample_id: tuple(ids) for sample_id, ids in order.items()},
    )


__all__ = [
    "BINDING_SCHEMA",
    "CONFIG_KEY",
    "CONFIG_MEMBERS",
    "SNAPSHOT_SCHEMA",
    "PredecessorSnapshot",
    "PredecessorSnapshotError",
    "PredecessorWindow",
    "binding_from_values",
    "load_predecessor_binding",
    "window_text_chain_sha256",
]
