"""Evidence sources (the evidence seam): conec contexts, none, oracle refusal,
and the deterministic mismatch decorator applied by the driver on a config flag.

R0 repair refactor stage 2 (part B): ``_conec_contexts`` used to hardcode the
ConEC evidence path as ``earnings21/contexts/<id>.txt`` regardless of which
carrier the run's split actually named -- exactly what made a config naming
``earnings22-original`` with ``evidence_source=conec-contexts`` non-runnable
(and, worse, silently wrong for any carrier whose ids happened to collide
with earnings21-original's own). Every evidence source now takes the sample's
``carrier_lock_key`` explicitly and ``_conec_contexts`` resolves its path via
that carrier's own ``data.carriers.CarrierDescriptor.evidence`` layout; a
carrier with no ConEC evidence layer (``descriptor.evidence is None``, e.g.
earnings22-original) fails closed with a clear message instead of reading the
wrong carrier's contexts.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from ..data.carriers import CarrierDescriptorError, get_carrier_descriptor
from ..data.lock import asset_dir, lock_entry
from ..e0.artifacts import sha256_file
from .base import EVIDENCE_SOURCES, EvidenceError, EvidenceItem


class OracleEvidenceError(RuntimeError):
    """Oracle evidence was requested on the runtime path."""


def evidence_file_relpath(
    lock: Mapping[str, object], carrier_lock_key: str, sample_id: str
) -> str:
    """IMPORTANT 1 (external-threat-model review round 4): the evidence
    file's path, relative to the controlled data root -- the SAME
    construction :func:`_conec_contexts` resolves internally, exposed here
    so a run's D1 evidence-identity rail
    (``contracts.FrozenCoreGate.verify_evidence_identity``) can ask the gate
    to re-hash EXACTLY the file this run's evidence source is about to read,
    from one shared path convention rather than a second, independently
    drifting construction -- the same discipline ``data.references.
    reference_file_relpath`` already applies for the reference layer.

    Unlike ``reference_file_relpath`` (relative to the CARRIER's own asset
    root), an evidence file lives under its OWN lock key's asset root
    (``EvidenceLayout.lock_key`` -- module docstring: ConEC evidence for
    Earnings21 lives under the separate ``conec`` lock key), so the
    ``local_subdir`` prefix here comes from the evidence layout's own lock
    key, not from ``carrier_lock_key`` itself. A carrier with no evidence
    layer registered fails closed exactly as :func:`_conec_contexts` itself
    does.
    """

    try:
        descriptor = get_carrier_descriptor(carrier_lock_key)
    except CarrierDescriptorError:
        descriptor = None
    if descriptor is None or descriptor.evidence is None:
        raise EvidenceError(
            f"carrier {carrier_lock_key!r} has no ConEC evidence layer registered "
            "(data.carriers.CarrierDescriptor.evidence is None); cannot resolve an "
            "evidence file path for it"
        )
    layout = descriptor.evidence
    entry = lock_entry(lock, layout.lock_key)
    local_subdir = entry.get("local_subdir")
    if not isinstance(local_subdir, str) or not local_subdir:
        raise EvidenceError(
            f"asset {layout.lock_key!r} lacks a usable local_subdir in the lock"
        )
    return f"{local_subdir.rstrip('/')}/{layout.subdir}/{sample_id}{layout.extension}"


def _none_source(
    lock: Mapping[str, object], root: Path, sample_id: str, carrier_lock_key: str
) -> list[EvidenceItem]:
    return []


def _conec_contexts(
    lock: Mapping[str, object], root: Path, sample_id: str, carrier_lock_key: str
) -> list[EvidenceItem]:
    try:
        descriptor = get_carrier_descriptor(carrier_lock_key)
    except CarrierDescriptorError:
        descriptor = None
    if descriptor is None or descriptor.evidence is None:
        raise EvidenceError(
            f"carrier {carrier_lock_key!r} has no ConEC evidence layer registered "
            "(data.carriers.CarrierDescriptor.evidence is None); refusing to guess "
            "another carrier's context path"
        )
    layout = descriptor.evidence
    relpath = f"{layout.subdir}/{sample_id}{layout.extension}"
    path = asset_dir(lock, layout.lock_key, root) / layout.subdir / f"{sample_id}{layout.extension}"
    if not path.is_file():
        raise EvidenceError(f"conec context missing for {sample_id}: {path}")
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise EvidenceError(f"cannot read conec context {path}: {error}") from error
    item = EvidenceItem(
        evidence_id=f"{layout.lock_key}/{sample_id}",
        source_uri=f"{layout.lock_key}://{relpath}",
        content=content,
        provenance={"lock_key": layout.lock_key, "relpath": relpath, "sha256": sha256_file(path)},
    )
    return [item.validate()]


def _oracle_refusal(
    lock: Mapping[str, object], root: Path, sample_id: str, carrier_lock_key: str
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
