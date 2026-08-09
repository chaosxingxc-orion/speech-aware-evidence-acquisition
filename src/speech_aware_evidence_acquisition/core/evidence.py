"""Evidence sources (the evidence seam): conec contexts, none, oracle refusal,
the two B-2a bias-list sources, and the deterministic mismatch decorator
applied by the driver on a config flag.

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

B-2a (2026-08-09 leakage-note redesign, ``docs/readiness/2026-08-09-
exploration-plan.md`` section 3b): every evidence source now ALSO takes the run's
composed config ``values`` mapping (optional, default ``None`` -- every
pre-existing source and every pre-existing direct-call test site that omits
it is unaffected). ``conec-bias-list``/``distractor-only-bias-list`` are the
first sources to actually read a value out of it
(``bias_list_max_entries`` via ``core.bias_lists.resolve_bias_list_max_
entries``), mirroring the ``values``-consuming pattern
``core.instructions.resolve_task_instruction`` already established for
task-instruction knobs; ``core.driver.run_experiment`` threads the SAME
``values`` it already holds into every evidence source call, so this is
config plumbing only, no new registry, no new call site.

See ``core.bias_lists``' own module docstring for: why only the entity-
extraction rule (not a raw-text passthrough) satisfies B-2a's leakage
constraint, the real yield measured against the materialized ConEC corpus,
and a KNOWN GAP left open by this task (``conec-bias-list``'s transformed
content will trip the D1 evidence-CONTENT-identity check on an actual gated
model run; fixing that is separate, reviewed engineering, not done here).
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from ..data.carriers import CarrierDescriptorError, get_carrier_descriptor
from ..data.lock import asset_dir, lock_entry
from ..e0.artifacts import sha256_file
from .base import EVIDENCE_SOURCES, EvidenceError, EvidenceItem
from .bias_lists import (
    distractor_only_terms,
    extract_bias_candidates,
    format_bias_list_content,
    resolve_bias_list_max_entries,
)


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
    lock: Mapping[str, object],
    root: Path,
    sample_id: str,
    carrier_lock_key: str,
    values: Mapping[str, object] | None = None,
) -> list[EvidenceItem]:
    return []


def _conec_contexts(
    lock: Mapping[str, object],
    root: Path,
    sample_id: str,
    carrier_lock_key: str,
    values: Mapping[str, object] | None = None,
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
    lock: Mapping[str, object],
    root: Path,
    sample_id: str,
    carrier_lock_key: str,
    values: Mapping[str, object] | None = None,
) -> list[EvidenceItem]:
    raise OracleEvidenceError(
        "oracle evidence is a scoring-side upper-bound analysis interface; it "
        "never enters a runtime arm (entry contract R0; design spec §2). Its "
        "computation is specified with the probe that first uses it."
    )


def _conec_bias_list(
    lock: Mapping[str, object],
    root: Path,
    sample_id: str,
    carrier_lock_key: str,
    values: Mapping[str, object] | None = None,
) -> list[EvidenceItem]:
    """B-2a arm 2 (ConEC-derived bias list): candidate entity/bias terms
    extracted deterministically from the call's OWN ConEC context materials
    -- the exact same file ``_conec_contexts`` reads (reused here, so this
    fails closed identically for a carrier with no ConEC evidence layer,
    e.g. earnings22-original), transformed by
    ``core.bias_lists.extract_bias_candidates`` rather than passed through
    verbatim. Never reads ``bias_lists/oracle_list.txt`` -- this arm's
    admissibility rests entirely on its content being pre-existing,
    non-reference-derived call context, never a transcript distillation."""

    raw_item = _conec_contexts(lock, root, sample_id, carrier_lock_key)[0]
    max_entries = resolve_bias_list_max_entries(values)
    candidates = extract_bias_candidates(raw_item.content, max_entries=max_entries)
    if not candidates:
        raise EvidenceError(
            f"no bias-candidate entities could be extracted from the conec "
            f"context for sample {sample_id!r}; refusing to emit an empty "
            "bias list"
        )
    header = (
        f"ConEC-derived bias candidates for this call ({len(candidates)} of "
        f"max {max_entries}), extracted deterministically from the call's own "
        "ConEC context materials (participant/press-release vocabulary; no "
        "model, no reference transcript):"
    )
    item = EvidenceItem(
        evidence_id=f"conec-bias-list/{sample_id}",
        source_uri=f"conec-bias-list://{raw_item.provenance['relpath']}",
        content=format_bias_list_content(candidates, header),
        provenance={
            **raw_item.provenance,
            "extraction": "conec-bias-list-v1",
            "candidate_count": len(candidates),
            "max_entries": max_entries,
        },
    )
    return [item.validate()]


def _distractor_only_bias_list(
    lock: Mapping[str, object],
    root: Path,
    sample_id: str,
    carrier_lock_key: str,
    values: Mapping[str, object] | None = None,
) -> list[EvidenceItem]:
    """B-2a arm 3 (distractor-only negative control): the set difference
    ``distractor_list.txt - oracle_list.txt`` -- the ~769 Fortune-500/CEO
    names the shipped distractor list adds on top of the reference-derived
    oracle list, computed at load time (``core.bias_lists.distractor_only_
    terms``), never a hand-copied name list. Same content for every sample
    id (the bias lists are call-independent), same evidence-item shape and
    cap discipline as arm 2. ``bias_lists/{oracle,distractor}_list.txt`` ship
    only under ``earnings21-original``'s own asset root (never under
    ``conec``, and earnings22-original ships neither file at all); any other
    carrier fails closed exactly as ``_conec_contexts`` does for a missing
    evidence layer."""

    if carrier_lock_key != "earnings21-original":
        raise EvidenceError(
            f"carrier {carrier_lock_key!r} has no bias-list layer registered "
            "(bias_lists/oracle_list.txt and distractor_list.txt ship only "
            "under earnings21-original's own asset root); refusing to guess "
            "another carrier's bias lists"
        )
    max_entries = resolve_bias_list_max_entries(values)
    candidates, facts = distractor_only_terms(lock, root, max_entries=max_entries)
    header = (
        f"Distractor-only bias terms ({len(candidates)} of max {max_entries}, "
        f"{facts['distractor_only_total']} total before the cap): Fortune-500/"
        "CEO names present in the shipped Earnings-21 distractor list but "
        "ABSENT from its reference-derived oracle list (negative control; no "
        "reference-transcript content):"
    )
    item = EvidenceItem(
        evidence_id=f"distractor-only-bias-list/{sample_id}",
        source_uri=f"distractor-only-bias-list://{facts['distractor_relpath']}",
        content=format_bias_list_content(candidates, header),
        provenance={
            "lock_key": "earnings21-original",
            "relpath": facts["distractor_relpath"],
            "sha256": facts["distractor_sha256"],
            "extraction": "distractor-only-v1",
            "candidate_count": len(candidates),
            "max_entries": max_entries,
            "oracle_relpath": facts["oracle_relpath"],
            "oracle_sha256": facts["oracle_sha256"],
            "distractor_only_total": facts["distractor_only_total"],
        },
    )
    return [item.validate()]


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
EVIDENCE_SOURCES.register("conec-bias-list", _conec_bias_list)
EVIDENCE_SOURCES.register("distractor-only-bias-list", _distractor_only_bias_list)
