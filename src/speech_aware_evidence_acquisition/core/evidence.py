"""Evidence sources (the evidence seam): conec contexts, none, oracle refusal,
and the deterministic mismatch decorator applied by the driver on a config flag."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from ..data.lock import asset_dir
from ..e0.artifacts import sha256_file
from .base import EVIDENCE_SOURCES, EvidenceError, EvidenceItem


class OracleEvidenceError(RuntimeError):
    """Oracle evidence was requested on the runtime path."""


def _none_source(
    lock: Mapping[str, object], root: Path, sample_id: str
) -> list[EvidenceItem]:
    return []


def _conec_contexts(
    lock: Mapping[str, object], root: Path, sample_id: str
) -> list[EvidenceItem]:
    relpath = f"earnings21/contexts/{sample_id}.txt"
    path = asset_dir(lock, "conec", root) / "earnings21" / "contexts" / f"{sample_id}.txt"
    if not path.is_file():
        raise EvidenceError(f"conec context missing for {sample_id}: {path}")
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise EvidenceError(f"cannot read conec context {path}: {error}") from error
    item = EvidenceItem(
        evidence_id=f"conec/{sample_id}",
        source_uri=f"conec://{relpath}",
        content=content,
        provenance={"lock_key": "conec", "relpath": relpath, "sha256": sha256_file(path)},
    )
    return [item.validate()]


def _oracle_refusal(
    lock: Mapping[str, object], root: Path, sample_id: str
) -> list[EvidenceItem]:
    raise OracleEvidenceError(
        "oracle evidence is a scoring-side upper-bound analysis interface; it "
        "never enters a runtime arm (entry contract R0; design spec §2). Its "
        "computation is specified with the probe that first uses it."
    )


def rotated_mismatch(
    evidence_by_sample: Mapping[str, list[EvidenceItem]],
) -> dict[str, list[EvidenceItem]]:
    """Each sample receives the next sorted sample's evidence — a deterministic
    derangement (mismatched-evidence negative control), no randomness involved."""

    ordered = sorted(evidence_by_sample)
    if len(ordered) < 2:
        raise EvidenceError("rotated mismatch needs at least 2 samples")
    return {
        sample_id: list(evidence_by_sample[ordered[(index + 1) % len(ordered)]])
        for index, sample_id in enumerate(ordered)
    }


EVIDENCE_SOURCES.register("none", _none_source)
EVIDENCE_SOURCES.register("conec-contexts", _conec_contexts)
EVIDENCE_SOURCES.register("oracle", _oracle_refusal)
