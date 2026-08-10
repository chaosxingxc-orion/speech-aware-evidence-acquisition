"""Evidence sources (the evidence seam): conec contexts, none, oracle refusal,
the three B-2a bias-list sources, and the deterministic mismatch decorator
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
config plumbing only, no new registry, no new call site. ``conec-bias-
phrases`` (2026-08-10, below) reads a DIFFERENT knob the same way
(``bias_phrase_max_tokens`` via ``core.bias_lists.resolve_bias_phrase_max_
tokens``) -- config plumbing only, same discipline, no new mechanism.

See ``core.bias_lists``' own module docstring for: why only the entity-
extraction rule (not a raw-text passthrough) satisfies B-2a's leakage
constraint and the real yield measured against the materialized ConEC
corpus; and for ``conec-bias-phrases``, why the real ConEC corpus's unigram
shape fragments multi-word entities and how phrase reconstruction undoes
that at matched content volume, never entry count.

Derivation-chain rail (2026-08-09, ``docs/readiness/2026-08-09-conec-
evidence-shape.md`` "Blocking gap", now CLOSED): ``conec-contexts``,
``conec-bias-list``, ``conec-bias-phrases`` and ``distractor-only-bias-list``
each build a ``core.base.DerivedEvidenceRecord`` alongside their
``EvidenceItem`` -- ``core.driver.run_experiment`` hands every one of them to
``core.evidence_derivation.DerivedEvidenceRegistry`` before a run proceeds,
so identity stays provable for TRANSFORMED evidence exactly the way
``core.model.slices.SliceRegistry`` already proves it for runtime-derived
AUDIO. ``conec-contexts``'s record uses the ``identity`` transform (its
content is unchanged, byte-identical to before this rail existed);
``conec-bias-list``'s, ``conec-bias-phrases``'s and ``distractor-only-bias-
list``'s content is built by calling the SAME pinned, registered transform
functions (``core.bias_lists.conec_bias_list_content``/
``conec_bias_phrase_content``/``distractor_only_content``) the registry
independently re-invokes to verify them.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Mapping

from ..data.carriers import CarrierDescriptorError, get_carrier_descriptor
from ..data.lock import asset_dir, lock_entry
from ..e0.artifacts import sha256_file
from .base import EVIDENCE_SOURCES, DerivedEvidenceRecord, EvidenceError, EvidenceItem
from .bias_lists import (
    conec_bias_list_content,
    conec_bias_phrase_content,
    distractor_only_content,
    distractor_only_source_document,
    distractor_only_source_texts,
    distractor_only_terms,
    extract_bias_candidates,
    format_bias_list_content,
    reconstruct_bias_phrases,
    resolve_bias_list_max_entries,
    resolve_bias_phrase_max_tokens,
)
from .evidence_derivation import canonical_params_hash


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
    # Derivation-chain rail (module docstring): a verbatim passthrough is
    # still a transform -- the "identity" one -- so it carries a genuine
    # DerivedEvidenceRecord too, rather than being a case the registry has to
    # special-case. derived_sha256 == source_sha256 by construction (identity
    # never changes a byte), which is exactly what
    # core.evidence_derivation.DerivedEvidenceRegistry re-proves when it
    # re-invokes the "identity" transform.
    source_bytes = content.encode("utf-8")
    source_sha256 = hashlib.sha256(source_bytes).hexdigest()
    derivation = DerivedEvidenceRecord(
        sample_id=sample_id,
        source_relpath=evidence_file_relpath(lock, carrier_lock_key, sample_id),
        source_sha256=source_sha256,
        transform_name="identity",
        transform_version="v1",
        params_hash=canonical_params_hash({}),
        derived_sha256=source_sha256,
        carrier_bound=True,
    )
    item = EvidenceItem(
        evidence_id=f"{layout.lock_key}/{sample_id}",
        source_uri=f"{layout.lock_key}://{relpath}",
        content=content,
        provenance={"lock_key": layout.lock_key, "relpath": relpath, "sha256": sha256_file(path)},
        derivation=derivation,
        derivation_source_bytes=source_bytes,
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
    params: dict[str, object] = {"max_entries": max_entries}
    # The SAME registered transform (core.evidence_derivation.TRANSFORMS)
    # core.evidence_derivation.DerivedEvidenceRegistry will independently
    # re-invoke to verify this item's derivation chain -- one implementation,
    # never a second copy built inline here.
    content = conec_bias_list_content(raw_item.content, params)
    derived_sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()
    source_record = raw_item.derivation
    derivation = DerivedEvidenceRecord(
        sample_id=sample_id,
        source_relpath=source_record.source_relpath,
        source_sha256=source_record.source_sha256,
        transform_name="conec-bias-list",
        transform_version="v1",
        params_hash=canonical_params_hash(params),
        derived_sha256=derived_sha256,
        carrier_bound=True,
    )
    item = EvidenceItem(
        evidence_id=f"conec-bias-list/{sample_id}",
        source_uri=f"conec-bias-list://{raw_item.provenance['relpath']}",
        content=content,
        provenance={
            **raw_item.provenance,
            "extraction": "conec-bias-list-v1",
            "candidate_count": len(candidates),
            "max_entries": max_entries,
        },
        derivation=derivation,
        derivation_source_bytes=raw_item.derivation_source_bytes,
    )
    return [item.validate()]


def _conec_bias_phrases(
    lock: Mapping[str, object],
    root: Path,
    sample_id: str,
    carrier_lock_key: str,
    values: Mapping[str, object] | None = None,
) -> list[EvidenceItem]:
    """B-2a arm 2b (2026-08-10, reconstructed multi-word phrase candidates,
    ``docs/readiness/2026-08-09-conec-evidence-shape.md`` "B-2a redesigned
    again"): the SAME ConEC context file ``_conec_bias_list`` reads (reused
    here for the identical fail-closed behaviour on a carrier with no ConEC
    evidence layer), reassembled by ``core.bias_lists.reconstruct_bias_
    phrases`` into ADJACENT-LINE bigram phrase candidates instead of single
    tokens -- the FORM contrast against ``conec-bias-list`` at matched
    content VOLUME (``core.bias_lists.DEFAULT_BIAS_PHRASE_MAX_TOKENS``'s own
    docstring has the budget-matching arithmetic). Never reads
    ``bias_lists/oracle_list.txt`` -- structurally identical provenance to
    ``conec-bias-list``, whose raw source read this function reuses
    verbatim."""

    raw_item = _conec_contexts(lock, root, sample_id, carrier_lock_key)[0]
    max_tokens = resolve_bias_phrase_max_tokens(values)
    candidates = reconstruct_bias_phrases(raw_item.content, max_tokens=max_tokens)
    if not candidates:
        raise EvidenceError(
            f"no phrase candidates could be reconstructed from the conec "
            f"context for sample {sample_id!r}; refusing to emit an empty "
            "phrase list"
        )
    params: dict[str, object] = {"max_tokens": max_tokens}
    # The SAME registered transform (core.evidence_derivation.TRANSFORMS)
    # core.evidence_derivation.DerivedEvidenceRegistry will independently
    # re-invoke to verify this item's derivation chain -- one implementation,
    # never a second copy built inline here.
    content = conec_bias_phrase_content(raw_item.content, params)
    derived_sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()
    source_record = raw_item.derivation
    derivation = DerivedEvidenceRecord(
        sample_id=sample_id,
        source_relpath=source_record.source_relpath,
        source_sha256=source_record.source_sha256,
        transform_name="conec-bias-phrases",
        transform_version="v1",
        params_hash=canonical_params_hash(params),
        derived_sha256=derived_sha256,
        carrier_bound=True,
    )
    item = EvidenceItem(
        evidence_id=f"conec-bias-phrases/{sample_id}",
        source_uri=f"conec-bias-phrases://{raw_item.provenance['relpath']}",
        content=content,
        provenance={
            **raw_item.provenance,
            "extraction": "conec-bias-phrases-v1",
            "candidate_count": len(candidates),
            "max_tokens": max_tokens,
        },
        derivation=derivation,
        derivation_source_bytes=raw_item.derivation_source_bytes,
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
    content = format_bias_list_content(candidates, header)
    # Carrier-independent derivation chain (core.base.DerivedEvidenceRecord
    # docstring): this arm never reads a per-sample carrier file, so its
    # SOURCE is the COMBINED text of the two shipped bias_lists/ files
    # (never a fabricated single-file per-sample path). Re-read here purely
    # to build that combined document; `content` above is unchanged from
    # before this rail existed.
    oracle_text, distractor_text, oracle_relpath, distractor_relpath = (
        distractor_only_source_texts(lock, root)
    )
    params: dict[str, object] = {"max_entries": max_entries}
    source_document = distractor_only_source_document(
        oracle_text, distractor_text, oracle_relpath, distractor_relpath
    )
    source_bytes = source_document.encode("utf-8")
    # Internal consistency guard: the registered transform (the SAME one
    # core.evidence_derivation.DerivedEvidenceRegistry will independently
    # re-invoke) must reproduce `content` exactly -- catches a future
    # refactor that lets the two computations drift apart, before a run ever
    # gets as far as the registry's own refusal.
    transform_content = distractor_only_content(source_document, params)
    if transform_content != content:
        raise EvidenceError(
            "distractor-only-bias-list internal consistency check failed: the "
            "registered transform disagrees with the direct computation"
        )
    derivation = DerivedEvidenceRecord(
        sample_id=sample_id,
        source_relpath=f"{oracle_relpath}+{distractor_relpath}",
        source_sha256=hashlib.sha256(source_bytes).hexdigest(),
        transform_name="distractor-only",
        transform_version="v1",
        params_hash=canonical_params_hash(params),
        derived_sha256=hashlib.sha256(content.encode("utf-8")).hexdigest(),
        carrier_bound=False,
    )
    item = EvidenceItem(
        evidence_id=f"distractor-only-bias-list/{sample_id}",
        source_uri=f"distractor-only-bias-list://{facts['distractor_relpath']}",
        content=content,
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
        derivation=derivation,
        derivation_source_bytes=source_bytes,
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


def resolve_declared_transform_params(
    transform_name: str, values: Mapping[str, object] | None
) -> dict[str, object]:
    """``core.driver.run_experiment``'s independent source of "what params
    did THIS run's config actually declare for this transform" --
    deliberately never read off a ``DerivedEvidenceRecord`` itself
    (``core.evidence_derivation.DerivedEvidenceRegistry``'s condition 3: an
    evidence source that lied about the params it used must be caught, not
    trusted). One entry per transform this module actually wires
    (deliverable 4); an unrecognised ``transform_name`` refuses rather than
    silently resolving to an empty/wrong params mapping -- a derivation
    record can never be verified against a transform this resolver does not
    know."""

    if transform_name == "identity":
        return {}
    if transform_name in ("conec-bias-list", "distractor-only"):
        return {"max_entries": resolve_bias_list_max_entries(values)}
    if transform_name == "conec-bias-phrases":
        return {"max_tokens": resolve_bias_phrase_max_tokens(values)}
    raise EvidenceError(
        f"no declared-params resolver registered for transform {transform_name!r}"
    )


EVIDENCE_SOURCES.register("none", _none_source)
EVIDENCE_SOURCES.register("conec-contexts", _conec_contexts)
EVIDENCE_SOURCES.register("oracle", _oracle_refusal)
EVIDENCE_SOURCES.register("conec-bias-list", _conec_bias_list)
EVIDENCE_SOURCES.register("conec-bias-phrases", _conec_bias_phrases)
EVIDENCE_SOURCES.register("distractor-only-bias-list", _distractor_only_bias_list)
