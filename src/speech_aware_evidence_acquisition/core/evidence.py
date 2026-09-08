"""Evidence sources (the evidence seam): conec contexts, conec names,
derived candidates, none, oracle refusal, the three B-2a bias-list sources,
and the deterministic mismatch decorator applied by the driver on a config
flag.

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

``conec-names`` (2026-08-12, ``docs/readiness/2026-08-12-clean-floor-
context-verdict.md`` "the decisive pilot"): a second verbatim ConEC source,
``_conec_names``, built by literally mirroring ``_conec_contexts`` -- same
carrier-availability gate (``descriptor.evidence is None`` fails closed
identically), same ``identity`` transform, same ``DerivedEvidenceRecord``/
``EvidenceItem`` shape, registered into the SAME ``EVIDENCE_SOURCES`` and
``core.evidence_derivation.TRANSFORMS`` registries -- differing only in
WHICH per-sample file it reads: ConEC ships one participant-name roster per
sample (``earnings21/contexts/participant_names/<id>.names.txt``, "Name -
Role/Affiliation" one per line -- the shape ``core.bias_lists``' own
``roster`` sub-pattern already documents) alongside its context file
(``earnings21/contexts/<id>.txt``), under the SAME ``conec`` lock key asset
root, one directory level deeper. Because this is a different SOURCE FILE
and not a new registered evidence LAYER, ``conec_names_file_relpath`` builds
its own participant-names path rather than reusing ``evidence_file_relpath``
(which is pinned to ``descriptor.evidence``'s own contexts subdir/
extension) -- see that function's docstring for the one place the two
diverge. D1's own identity artifact (``docs/receipts/artifacts/d1-identity.
json``, ``conec.layers.e21_contexts.excluded_non_layer_files``) already
lists ``participant_names`` as OUTSIDE the ``e21_contexts`` layer it
manifests today, i.e. this file's per-sample identity has never been
D1-recorded -- ``carrier_bound`` stays ``True`` (this is structurally a
per-sample carrier file, exactly like ``conec-contexts``), so a real gated
run correctly keeps failing closed at the unchanged
``contracts.gate_evidence_identity`` rail until a future D0/D1 update adds
this layer; nothing here weakens that gate or bypasses it early.

``conec-class-lists`` / ``conec-class-lists-placebo`` (2026-09-06, E5 /
KC-E1 / KU-E1c, ``docs/readiness/2026-09-06-e21-kc-e1-pre-meeting-brief-v1-
preregistration.md``): the PRE-MEETING BRIEF and its form twin. Unlike every
source above, one call of these returns TWO items -- the participant roster
rendered as labelled participant/organization/division lines, then the
context document rendered as company-ticker, product-segment and residual
term candidates, each entry carrying its Whisper-normalized form where
casing or punctuation moves it. Two items rather than one because
``contracts.gate_evidence_identity._route_evidence_layer_key`` routes ONE
relpath to ONE D1 layer and the brief's two halves live under two
(``e21_contexts`` and ``e21_participant_names``), so a fused item could
carry a verifiable derivation chain for neither half. Both halves reuse
``_conec_names``/``_conec_contexts`` verbatim for the read -- so the roster
half inherits, unchanged, the D1 gap the ``conec-names`` paragraph above
already records, and a gated run still fails closed there until a D0/D1
update adds that layer. The rendering itself lives in ``core.class_lists``
(module docstring: what ConEC's two files actually contain, why the
document-derived classes are CANDIDATES rather than an inventory, and why
the twin is a function of shape alone), whose four pure transforms are
registered in ``core.evidence_derivation.TRANSFORMS`` and resolved in
:func:`resolve_declared_transform_params` exactly like the bias-list ones.

``conec-class-lists-placebo-token-matched`` (2026-09-07,
``SAEA-E21-KU-E1C-TOKEN-MATCH-V1``) is the twin the flight actually needs.
The KC-E1 prompt fit measured the whitespace twin on the flight tokenizer and
found it 42 to 256 tokens light per window at cap 12, median 161, so a verdict
drawn against it would price content and volume together. This source renders
the same twin and then replays a per-line pad plan measured once against the
resident serving geometry, through the two ``-placebo-tm`` transforms; the
plan is pinned by path and sha256 in the composed config
(``evidence_pad_plan``), so its exact per-line repeat counts land in
``params_hash`` and ``DerivedEvidenceRegistry`` re-derives the padded twin from
the same ConEC bytes on every gated run. No tokenizer is reached at flight
time. The unpadded twin stays registered unchanged, because it is what the
prompt-fit receipt measured.

``e22-metadata-brief`` / ``-deranged`` / ``-deranged-token-matched``
(2026-09-07, KC-E2 / KU-E2c, ``docs/readiness/2026-09-07-e22-kc-e2-pre-meeting-
brief-v1-preregistration.md``): the Earnings-22 counterpart of the brief above,
for a carrier with no ConEC evidence layer at all. Its source is the carrier's
OWN metadata table (``data.carriers.CarrierDescriptor.metadata_filename``, the
same file ``data.loader.load_carrier`` resolves), pinned by path and sha256 in
the composed config and re-hashed on every read; the transform is invoked on the
call's two-line SOURCE SLICE (header line plus that call's data line, both
verbatim), because a transform signature carries no sample id and a params
resolver carries no sample either. ``carrier_bound`` is ``False`` and the
docstring says why: D1 records the table's 125 ids through a ``_csv_layer`` and
no per-file manifest, so there is no per-sample evidence identity for the D1 rail
to check and this source does not pretend otherwise -- the same honesty
``distractor-only-bias-list`` already states. The form twin is another call's
brief under a pinned, fixed-point-free call derangement rather than a neutral
placeholder (``core.metadata_brief`` module docstring for why), and its
token-matched form replays a per-line pad plan through
``core.class_lists.pad_placebo`` -- the SAME padder KU-E1c uses.

``derived-candidates`` (2026-08-12, offline retrieval-gated candidate
evidence -- the E-003R mechanism and the KC-Q3 two-pass machinery's shared
evidence layer; see ``scripts/materialize_candidates.py``'s own module
docstring for how these files are produced): a THIRD verbatim-passthrough
source, ``_derived_candidates``, reading a per-sample file an OFFLINE
materializer already wrote --
``derived/evidence-candidates/<materialization_id>/<sample_id>.candidates.
txt`` directly under the controlled data root (never a lock-registered asset
subdir) -- one already retrieval-gated, score-thresholded candidate per
line. Same ``identity`` transform / ``DerivedEvidenceRecord``/``EvidenceItem``
shape as ``conec-contexts``/``conec-names`` above, but this source names no
carrier at all: ``materialization_id`` comes from a NEW baseline-config key,
``evidence_materialization_id`` -- required by, and legal ONLY WITH,
``evidence_source == "derived-candidates"``. :func:`resolve_evidence_
materialization_id` fails closed on a missing/empty value (called inside
``_derived_candidates`` itself, so a direct call to that source function --
e.g. a unit test bypassing ``run_experiment`` entirely, exactly the pattern
every other source's own test suite already uses -- gets the identical
fail-closed behaviour); :func:`assert_evidence_materialization_id_legal`
fails closed if the key is supplied alongside any OTHER ``evidence_source``,
called once, early, in ``core.driver.run_experiment`` -- the same "resolved
and validated HERE, before any other per-run work" placement ``core.
evidence_budget.resolve_evidence_budget_bytes`` already established.
Because this source never resolves a ``data.carriers.CarrierDescriptor`` at
all, its ``DerivedEvidenceRecord.carrier_bound`` is honestly ``False``
(``core.base.DerivedEvidenceRecord``'s own docstring): the file was never,
and can never be, D1-recorded under any carrier's identity layer -- it is a
materializer's own derived output, not a shipped carrier asset -- so
identity rests solely on this record's own re-derived chain plus the
materializer's own ``manifest.json`` sha256 receipt, exactly the honesty
``distractor-only-bias-list`` already established for the identical reason.

SAEA-P2 abort fix (2026-08-15 P2 abort -- both R-ladder arms aborted at
``run_experiment``'s eager per-sample evidence resolution with ``failure_
reason: 'evidence content must be a non-empty string'`` on a legitimately
0-byte p1-oracle-v2/-shuffled candidates file): a candidates file that
EXISTS and reads cleanly but has zero non-blank lines (a call with zero
benchmark errors) now returns ``_none_source``'s own "no evidence" shape --
an empty list, no ``EvidenceItem`` -- instead of building one whose empty
``content`` :meth:`~.base.EvidenceItem.validate` refuses. A MISSING or
unreadable file is unchanged (still raises). See :func:`_derived_candidates`
for the exact check and why this loses no provenance in practice.
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
from ..data.variant_ids import published_sample_key
from .class_lists import (
    CLASS_LIST_TOKEN_MATCHED_TRANSFORMS,
    CLASS_LIST_TRANSFORMS,
    resolve_max_entries_per_class,
    resolve_placebo_pad_params,
)
from .evidence_derivation import TRANSFORMS, canonical_params_hash
from .metadata_brief import (
    METADATA_BRIEF_ARM_TOKEN_MATCHED_TRANSFORMS,
    METADATA_BRIEF_DERANGED_TRANSFORMS,
    METADATA_BRIEF_TOKEN_MATCHED_TRANSFORMS,
    METADATA_BRIEF_TRANSFORMS,
    call_source_slice,
    resolve_arm_token_matched_params,
    resolve_brief_source_pin,
    resolve_derangement_params,
    resolve_token_matched_params,
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


# conec-names (module docstring): the participant-names roster subdir/
# extension, one directory level below conec-contexts' own
# ``descriptor.evidence.subdir`` -- not part of any ``data.carriers.
# EvidenceLayout`` (that dataclass names conec-contexts' own layer, D1
# layer key included; participant_names has no D1 layer key at all yet, see
# module docstring), so these two constants are this source's own, in
# exactly the same spirit as ``core.bias_lists._BIAS_LISTS_SUBDIR``.
_CONEC_NAMES_SUBDIR_SUFFIX = "participant_names"
_CONEC_NAMES_EXTENSION = ".names.txt"


def conec_names_file_relpath(
    lock: Mapping[str, object], carrier_lock_key: str, sample_id: str
) -> str:
    """The ``conec-names`` counterpart to :func:`evidence_file_relpath`: same
    carrier-availability gate (a carrier with no ConEC evidence layer at all
    still refuses, identically worded), same ``conec`` lock key asset root
    resolution -- but the participant-names subdir/extension in place of
    conec-contexts' own ``layout.subdir``/``layout.extension``, since a
    names roster is a DIFFERENT source file under the SAME evidence layer's
    asset root, not a second registered ``EvidenceLayout`` (module
    docstring). Exposed the same way ``evidence_file_relpath`` is, in case a
    future D1 update wants to re-hash exactly this file too."""

    try:
        descriptor = get_carrier_descriptor(carrier_lock_key)
    except CarrierDescriptorError:
        descriptor = None
    if descriptor is None or descriptor.evidence is None:
        raise EvidenceError(
            f"carrier {carrier_lock_key!r} has no ConEC evidence layer registered "
            "(data.carriers.CarrierDescriptor.evidence is None); cannot resolve a "
            "conec-names file path for it"
        )
    layout = descriptor.evidence
    entry = lock_entry(lock, layout.lock_key)
    local_subdir = entry.get("local_subdir")
    if not isinstance(local_subdir, str) or not local_subdir:
        raise EvidenceError(
            f"asset {layout.lock_key!r} lacks a usable local_subdir in the lock"
        )
    return (
        f"{local_subdir.rstrip('/')}/{layout.subdir}/{_CONEC_NAMES_SUBDIR_SUFFIX}/"
        f"{sample_id}{_CONEC_NAMES_EXTENSION}"
    )


def _conec_names(
    lock: Mapping[str, object],
    root: Path,
    sample_id: str,
    carrier_lock_key: str,
    values: Mapping[str, object] | None = None,
) -> list[EvidenceItem]:
    """Verbatim passthrough of one sample's ConEC participant-names roster
    (module docstring) -- literally ``_conec_contexts`` with the names
    subdir/extension in place of the carrier's own contexts layout; every
    other line (carrier gate, identity transform, ``EvidenceItem``/
    ``DerivedEvidenceRecord`` shape) is unchanged."""

    try:
        descriptor = get_carrier_descriptor(carrier_lock_key)
    except CarrierDescriptorError:
        descriptor = None
    if descriptor is None or descriptor.evidence is None:
        raise EvidenceError(
            f"carrier {carrier_lock_key!r} has no ConEC evidence layer registered "
            "(data.carriers.CarrierDescriptor.evidence is None); refusing to guess "
            "another carrier's participant-names path"
        )
    layout = descriptor.evidence
    relpath = f"{layout.subdir}/{_CONEC_NAMES_SUBDIR_SUFFIX}/{sample_id}{_CONEC_NAMES_EXTENSION}"
    path = (
        asset_dir(lock, layout.lock_key, root)
        / layout.subdir
        / _CONEC_NAMES_SUBDIR_SUFFIX
        / f"{sample_id}{_CONEC_NAMES_EXTENSION}"
    )
    if not path.is_file():
        raise EvidenceError(f"conec participant names missing for {sample_id}: {path}")
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise EvidenceError(f"cannot read conec participant names {path}: {error}") from error
    # Same identity-transform derivation chain as _conec_contexts (module
    # docstring): derived_sha256 == source_sha256 by construction, re-proved
    # by core.evidence_derivation.DerivedEvidenceRegistry re-invoking the
    # SAME registered "identity" transform -- no second transform to
    # register, no change to resolve_declared_transform_params below.
    source_bytes = content.encode("utf-8")
    source_sha256 = hashlib.sha256(source_bytes).hexdigest()
    derivation = DerivedEvidenceRecord(
        sample_id=sample_id,
        source_relpath=conec_names_file_relpath(lock, carrier_lock_key, sample_id),
        source_sha256=source_sha256,
        transform_name="identity",
        transform_version="v1",
        params_hash=canonical_params_hash({}),
        derived_sha256=source_sha256,
        carrier_bound=True,
    )
    item = EvidenceItem(
        evidence_id=f"{layout.lock_key}/participant-names/{sample_id}",
        source_uri=f"{layout.lock_key}://{relpath}",
        content=content,
        provenance={"lock_key": layout.lock_key, "relpath": relpath, "sha256": sha256_file(path)},
        derivation=derivation,
        derivation_source_bytes=source_bytes,
    )
    return [item.validate()]


def resolve_evidence_materialization_id(values: Mapping[str, object] | None) -> str:
    """The ``evidence_materialization_id`` baseline-config key
    ``_derived_candidates`` needs to find its offline-materialized per-sample
    candidate file (``scripts/materialize_candidates.py``'s own ``--out-id``)
    -- a non-empty string, no default (there is no sane fallback id here, the
    same "no default" discipline ``core.config.model_lock_key`` already
    applies to a model fragment's own required key).

    Deliberately does NOT look at ``evidence_source``: this resolver is
    shared, unconditional, and never re-derives which source called it --
    the same discipline ``resolve_bias_list_max_entries`` already applies for
    its own (differently-scoped) knob. See :func:`assert_evidence_
    materialization_id_legal` for the source-exclusivity half of this key's
    contract, checked once, early, at the composed-config level."""

    value = values.get("evidence_materialization_id") if values is not None else None
    if not isinstance(value, str) or not value:
        raise EvidenceError(
            "baseline config evidence_materialization_id must be a non-empty "
            f"string (required by the derived-candidates evidence source), got {value!r}"
        )
    return value


def assert_evidence_materialization_id_legal(values: Mapping[str, object]) -> None:
    """Key-legality matrix for ``evidence_materialization_id`` (module
    docstring): required by, and legal ONLY WITH, ``evidence_source ==
    "derived-candidates"``. Called once, early, in ``core.driver.
    run_experiment`` -- the same "resolved and validated HERE, before any
    other per-run work" placement ``core.evidence_budget.resolve_evidence_
    budget_bytes`` already established -- so a baseline fragment that sets
    this key under any OTHER evidence_source refuses before any per-run work
    happens, rather than the source dispatch simply never reading (and
    therefore never catching) a stray key left over from a copy-pasted
    fragment."""

    evidence_source = str(values.get("evidence_source", "none"))
    if evidence_source == "derived-candidates":
        resolve_evidence_materialization_id(values)
        return
    if "evidence_materialization_id" in values:
        raise EvidenceError(
            "baseline config evidence_materialization_id is only legal with "
            f"evidence_source='derived-candidates', got evidence_source={evidence_source!r}"
        )


def derived_candidates_file_relpath(materialization_id: str, sample_id: str) -> str:
    """The on-disk relpath (relative to the controlled data root) of one
    sample's offline-materialized ``derived-candidates`` file (module
    docstring) -- exposed the same way ``evidence_file_relpath``/
    ``conec_names_file_relpath`` are, so a SECOND caller
    (``reproduction.replay_loop._pack_terms``, RETRIEVE's own/roster-band's
    own candidate-pool builder, D7/D7B chain-defect fix) can resolve the
    EXACT SAME file :func:`_derived_candidates` already reads for this
    evidence source, from one shared path convention rather than a second,
    independently drifting construction."""

    return f"derived/evidence-candidates/{materialization_id}/{sample_id}.candidates.txt"


def _derived_candidates(
    lock: Mapping[str, object],
    root: Path,
    sample_id: str,
    carrier_lock_key: str,
    values: Mapping[str, object] | None = None,
) -> list[EvidenceItem]:
    """Verbatim passthrough of one sample's OFFLINE-materialized candidate
    file (module docstring) -- carrier-independent (``carrier_lock_key`` is
    accepted only for signature parity with every other evidence source,
    exactly like ``_none_source``, and is never read), so no ``data.carriers.
    CarrierDescriptor`` lookup happens here at all."""

    materialization_id = resolve_evidence_materialization_id(values)
    relpath = derived_candidates_file_relpath(materialization_id, sample_id)
    path = Path(root) / relpath
    if not path.is_file():
        raise EvidenceError(f"derived candidates missing for {sample_id}: {path}")
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise EvidenceError(f"cannot read derived candidates {path}: {error}") from error
    # SAEA-P2 abort fix (2026-08-15 P2 abort, both r0bias/r1verify arms: the
    # p1-oracle-v2/-shuffled materializations legitimately ship a 0-byte
    # candidates file for a call with zero benchmark errors -- the exact
    # "legitimate empty pool" reproduction.replay_loop._pack_terms already
    # tolerates downstream, module docstring's D7/D7B chain-defect fix
    # paragraph). ``core.driver.run_experiment`` resolves EVERY sample's
    # evidence eagerly, before any policy (and therefore _pack_terms) ever
    # runs, so this source itself must never hand such a file to
    # ``EvidenceItem(content=...).validate()`` -- that call refuses an empty
    # ``content`` string unconditionally (``core.base.EvidenceItem.
    # validate``), which is correct for every OTHER reason content could be
    # empty but wrong for THIS one: a materializer's honest "nothing to
    # supply here" is not a malformed evidence item. A file that exists and
    # reads cleanly but carries zero non-blank lines therefore mirrors
    # ``_none_source``'s own "no evidence for this sample" shape -- an empty
    # list, no ``EvidenceItem`` -- exactly like a bare-core sample's;
    # ``core.driver.run_experiment``'s derivation-chain loop already skips
    # an empty per-sample list (``if not items: continue``), and
    # ``core.evidence_derivation.DerivedEvidenceRegistry.register`` refuses
    # empty source/derived bytes outright, so this content could never have
    # produced a verifiable ``DerivedEvidenceRecord`` here either way. A
    # MISSING or unreadable file is UNCHANGED above -- still raises. This
    # does not lose the file's provenance: ``derived_candidates_file_relpath``
    # (public, module docstring) resolves the SAME relpath a caller can
    # re-hash on demand, and ``reproduction.replay_loop._pack_terms``
    # independently re-reads this exact file (by design, so PASS-1 evidence
    # suppression can never affect it -- that function's own docstring) and
    # records its own "empty-candidates-file" note on the replay-derivation
    # artifact, which is the audit trail this emptiness actually needs.
    if not any(line.strip() for line in content.splitlines()):
        return []
    # Same identity-transform derivation chain as _conec_contexts/_conec_names
    # (module docstring), but carrier_bound=False (core.base.
    # DerivedEvidenceRecord's own docstring): this file lives outside any
    # carrier's asset root entirely, so it can never be D1-recorded -- the
    # HONEST record here rests solely on this chain's own re-derivation,
    # never a fabricated D1 anchor, exactly like distractor-only-bias-list.
    source_bytes = content.encode("utf-8")
    source_sha256 = hashlib.sha256(source_bytes).hexdigest()
    derivation = DerivedEvidenceRecord(
        sample_id=sample_id,
        source_relpath=relpath,
        source_sha256=source_sha256,
        transform_name="identity",
        transform_version="v1",
        params_hash=canonical_params_hash({}),
        derived_sha256=source_sha256,
        carrier_bound=False,
    )
    item = EvidenceItem(
        evidence_id=f"derived-candidates/{sample_id}",
        source_uri=f"derived-candidates://{relpath}",
        content=content,
        provenance={
            "lock_key": "derived-candidates",
            "relpath": relpath,
            "sha256": sha256_file(path),
            "materialization_id": materialization_id,
        },
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


def _class_list_item(
    raw_item: EvidenceItem,
    sample_id: str,
    transform_name: str,
    content: str,
    max_entries: int,
    part: str,
    params: Mapping[str, object],
) -> EvidenceItem:
    """One half of the pre-meeting brief, wrapped exactly the way
    ``_conec_bias_list`` wraps its own transform output: the RAW item's source
    relpath and source sha256 carried through, so the derivation chain pins the
    ConEC file this half was actually built from, and
    ``core.evidence_derivation.DerivedEvidenceRegistry`` can re-invoke the SAME
    registered transform on the SAME bytes and get this content back."""

    derived_sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()
    source_record = raw_item.derivation
    derivation = DerivedEvidenceRecord(
        sample_id=sample_id,
        source_relpath=source_record.source_relpath,
        source_sha256=source_record.source_sha256,
        transform_name=transform_name,
        transform_version="v1",
        params_hash=canonical_params_hash(params),
        derived_sha256=derived_sha256,
        carrier_bound=True,
    )
    item = EvidenceItem(
        evidence_id=f"{transform_name}/{sample_id}",
        source_uri=f"{transform_name}://{raw_item.provenance['relpath']}",
        content=content,
        provenance={
            **raw_item.provenance,
            "extraction": f"{transform_name}-v1",
            "brief_part": part,
            "max_entries_per_class": max_entries,
        },
        derivation=derivation,
        derivation_source_bytes=raw_item.derivation_source_bytes,
    )
    return item.validate()


def _class_list_items(
    lock: Mapping[str, object],
    root: Path,
    sample_id: str,
    carrier_lock_key: str,
    values: Mapping[str, object] | None,
    *,
    placebo: bool,
    token_matched: bool = False,
) -> list[EvidenceItem]:
    """E5's pre-meeting brief, or either of its two form twins, as TWO
    evidence items.

    Roster first, then document, because that is the order a human reads a
    briefing in and the order ``core.model.transport`` renders the two
    ``[evidence ...]`` blocks. Two items rather than one fused item because
    ``contracts.gate_evidence_identity._route_evidence_layer_key`` routes one
    relpath to one D1 layer, and the brief's two halves live under two
    (``e21_contexts`` and ``e21_participant_names``); a fused item could carry a
    verifiable derivation chain for neither. Both halves reuse
    ``_conec_names``/``_conec_contexts`` verbatim for the read, so a carrier
    with no ConEC evidence layer (earnings22-original) fails closed with their
    wording, unchanged."""

    if token_matched and not placebo:
        raise EvidenceError(
            "the token-matched variant is a form twin; there is no token-matched "
            "rendering of the arm itself"
        )
    max_entries = resolve_max_entries_per_class(values)
    suffix = ("-placebo-tm" if token_matched else "-placebo") if placebo else ""
    roster_raw = _conec_names(lock, root, sample_id, carrier_lock_key)[0]
    document_raw = _conec_contexts(lock, root, sample_id, carrier_lock_key)[0]
    # The params BOTH halves are rendered with and hashed under. Resolved
    # through the same :func:`resolve_declared_transform_params` the driver
    # re-verifies with, never rebuilt inline, so an applied pad plan and a
    # verified pad plan can never be two different mappings.
    params: dict[str, object] = resolve_declared_transform_params(
        f"conec-class-lists-roster{suffix}", values
    )
    # The SAME registered transforms (core.evidence_derivation.TRANSFORMS) the
    # registry will independently re-invoke to verify these items -- one
    # implementation of "what does this brief say", never a second copy built
    # inline here (core.bias_lists module docstring, "CLOSED GAP").
    roster_transform = f"conec-class-lists-roster{suffix}"
    document_transform = f"conec-class-lists-document{suffix}"
    roster_content = TRANSFORMS.resolve(roster_transform, "v1").apply(roster_raw.content, params)
    document_content = TRANSFORMS.resolve(document_transform, "v1").apply(
        document_raw.content, params
    )
    return [
        _class_list_item(
            roster_raw,
            sample_id,
            roster_transform,
            roster_content,
            max_entries,
            "roster",
            params,
        ),
        _class_list_item(
            document_raw,
            sample_id,
            document_transform,
            document_content,
            max_entries,
            "document",
            params,
        ),
    ]


def _conec_class_lists(
    lock: Mapping[str, object],
    root: Path,
    sample_id: str,
    carrier_lock_key: str,
    values: Mapping[str, object] | None = None,
) -> list[EvidenceItem]:
    """E5 / KC-E1 (``docs/readiness/2026-09-06-e21-kc-e1-pre-meeting-brief-v1-
    preregistration.md``): the PRE-MEETING BRIEF -- this call's ConEC
    participant roster and context documents rendered as labelled entity-class
    lines with the Whisper-normalized form beside each surface form. Built from
    the call's OWN two ConEC context files and nothing else; never a reference
    transcript, a timestamp file, a wer_tags sidecar or another call's material
    (``core.class_lists`` module docstring for what those two files contain and
    for the class-by-class provenance)."""

    return _class_list_items(lock, root, sample_id, carrier_lock_key, values, placebo=False)


def _conec_class_lists_placebo(
    lock: Mapping[str, object],
    root: Path,
    sample_id: str,
    carrier_lock_key: str,
    values: Mapping[str, object] | None = None,
) -> list[EvidenceItem]:
    """KU-E1c's form twin of ``conec-class-lists``: the same class labels, the
    same entry count and the same whitespace-token count per line, with every
    entry token replaced by a position-chosen neutral placeholder. Built from
    the SAME source bytes as the arm it controls, so the two can never drift in
    shape (``core.class_lists.placebo_of``)."""

    return _class_list_items(lock, root, sample_id, carrier_lock_key, values, placebo=True)


def _conec_class_lists_placebo_token_matched(
    lock: Mapping[str, object],
    root: Path,
    sample_id: str,
    carrier_lock_key: str,
    values: Mapping[str, object] | None = None,
) -> list[EvidenceItem]:
    """KU-E1c's TOKEN-matched form twin (owner ruling 2026-09-06,
    ``SAEA-E21-KU-E1C-TOKEN-MATCH-V1``): ``conec-class-lists-placebo`` with the
    pinned per-line pad plan replayed onto it, so each twin line measures its
    own brief line on the FLIGHT tokenizer instead of merely carrying the same
    whitespace-token count.

    Why a third source rather than a knob on the second: an unpadded twin and
    a padded twin are different derivations, and the pinned transform name is
    what a ``DerivedEvidenceRecord`` uses to say which one ran. Sharing a name
    would leave the two indistinguishable in a sealed trace, which is exactly
    what ``core.evidence_derivation``'s versioned registry exists to prevent.
    The cost is honest and small: the twin's evidence-block header is a few
    tokens longer than the arm's, because the two must name different
    transforms; the measurement receipt reports that residual rather than
    hiding it, and the brief CONTENT itself is token-equal line by line.

    Everything else is ``conec-class-lists-placebo``'s: the same two source
    files, the same two D1 layers, the same roster-then-document order, the
    same cap. The pad plan is read from the artifact the composed config pins
    by path and sha256 (``core.class_lists.resolve_placebo_pad_params``), so
    the flight needs no tokenizer of its own.
    """

    return _class_list_items(
        lock,
        root,
        sample_id,
        carrier_lock_key,
        values,
        placebo=True,
        token_matched=True,
    )


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


# ---------------------------------------------------------------------------
# The Earnings-22 pre-meeting brief (2026-09-07, KC-E2 / KU-E2c)
# ---------------------------------------------------------------------------


def e22_metadata_file_relpath(lock: Mapping[str, object], carrier_lock_key: str) -> str:
    """The carrier's own metadata table, relative to the controlled data root.

    The ``conec-contexts`` counterpart of this module resolves a PER-SAMPLE
    evidence file from ``descriptor.evidence``; Earnings-22 has no such layer
    (``data.carriers.EARNINGS22_ORIGINAL.evidence is None``, and the ConEC
    Earnings-22 side is per-call PDF packets nothing here reads). The
    Earnings-22 brief's source is instead the carrier's OWN metadata table --
    the same file ``data.loader.load_carrier`` already resolves through
    ``descriptor.metadata_filename`` -- so this function derives its path from
    the descriptor exactly the way the loader does, never from a literal.
    """

    try:
        descriptor = get_carrier_descriptor(carrier_lock_key)
    except CarrierDescriptorError as error:
        raise EvidenceError(
            f"carrier {carrier_lock_key!r} has no registered carrier descriptor; "
            f"cannot resolve a metadata-brief source for it: {error}"
        ) from error
    if descriptor.metadata_filename is None:
        raise EvidenceError(
            f"carrier {carrier_lock_key!r} declares no metadata table "
            "(data.carriers.CarrierDescriptor.metadata_filename is None); the "
            "metadata brief is refused rather than pointed at another carrier's table"
        )
    entry = lock_entry(lock, carrier_lock_key)
    local_subdir = entry.get("local_subdir")
    if not isinstance(local_subdir, str) or not local_subdir:
        raise EvidenceError(
            f"asset {carrier_lock_key!r} lacks a usable local_subdir in the lock"
        )
    return f"{local_subdir.rstrip('/')}/{descriptor.metadata_filename}"


def brief_call_id(sample_id: str) -> str:
    """The CALL a dev clip belongs to: the published key (``@`` variant suffix
    stripped, ``data.variant_ids.published_sample_key``) up to its first ``-``.

    Earnings-22 File IDs are digit strings with no internal ``-``, and the ESB
    clip convention is ``<call>-<segment>[@<variant>]``, so this recovers the
    call for a clip and returns a bare call id unchanged. Fail-closed on
    anything that is not a plain call id, rather than guessing.
    """

    if not isinstance(sample_id, str) or not sample_id:
        raise EvidenceError("a sample id must be non-empty text")
    call_id = published_sample_key(sample_id).split("-", 1)[0]
    if not call_id or not call_id.isalnum():
        raise EvidenceError(
            f"cannot recover an Earnings-22 call id from sample {sample_id!r}; the "
            "metadata brief is never rendered for a sample whose call is a guess"
        )
    return call_id


def _metadata_brief_items(
    lock: Mapping[str, object],
    root: Path,
    sample_id: str,
    carrier_lock_key: str,
    values: Mapping[str, object] | None,
    *,
    deranged: bool,
    token_matched: bool,
) -> list[EvidenceItem]:
    """KC-E2's brief, or either form of its twin, as ONE evidence item.

    One item rather than the brief's two (``conec-class-lists`` returns two
    because the E21 brief spans two ConEC files under two D1 layers): the
    Earnings-22 brief has exactly one source file and therefore exactly one
    derivation chain.

    ``carrier_bound`` is ``False`` (``core.metadata_brief`` module docstring):
    D1 records this table's 125 sample ids and no per-file manifest for it, so
    there is no D1-recorded per-sample evidence identity to check against, and
    the record says so rather than fabricating one. The table's bytes are pinned
    instead by the composed config and re-hashed here on every read.

    ``token_matched`` applies to BOTH sides, unlike the Earnings-21 brief's
    one-sided twin: ``core.metadata_brief.pair_pad_repeats`` grows whichever side
    is short, because a real-call twin can be longer than the brief it twins and
    on the Oceania calls every fact-distinct partner is. The padded arm gains
    neutral filler and no fact.
    """

    relpath = e22_metadata_file_relpath(lock, carrier_lock_key)
    pinned_relpath, pinned_sha256 = resolve_brief_source_pin(values)
    if pinned_relpath != relpath:
        raise EvidenceError(
            f"the composed config pins the metadata brief's source at {pinned_relpath!r} "
            f"but carrier {carrier_lock_key!r} resolves it at {relpath!r}; a brief is "
            "never rendered from a table the fragment did not pin"
        )
    path = Path(root) / relpath
    if not path.is_file():
        raise EvidenceError(f"Earnings-22 metadata table missing: {path}")
    try:
        blob = path.read_bytes()
    except OSError as error:
        raise EvidenceError(f"cannot read Earnings-22 metadata table {path}: {error}") from error
    measured = hashlib.sha256(blob).hexdigest()
    if measured != pinned_sha256:
        raise EvidenceError(
            f"Earnings-22 metadata table {path} hashes to {measured}, not the "
            f"configured {pinned_sha256}; a corpus table edited after the fragment was "
            "written is refused rather than silently flown"
        )
    try:
        text = blob.decode("utf-8")
    except UnicodeError as error:
        raise EvidenceError(
            f"Earnings-22 metadata table {path} is not UTF-8: {error}"
        ) from error

    call_id = brief_call_id(sample_id)
    if token_matched and deranged:
        transform = "e22-metadata-brief-deranged-tm"
        params = resolve_token_matched_params(values)
    elif token_matched:
        transform = "e22-metadata-brief-tm"
        params = resolve_arm_token_matched_params(values)
    elif deranged:
        transform = "e22-metadata-brief-deranged"
        params = resolve_derangement_params(values)
    else:
        transform = "e22-metadata-brief"
        params = {"metadata_relpath": pinned_relpath, "metadata_sha256": pinned_sha256}
    source_call = call_id
    if deranged:
        derangement = params["derangement"]
        partner = derangement.get(call_id)
        if partner is None:
            raise EvidenceError(
                f"the pinned derangement has no partner for call {call_id!r} (sample "
                f"{sample_id!r}); a form twin is never improvised at flight time"
            )
        source_call = str(partner)
    slice_text = call_source_slice(text, source_call)
    source_bytes = slice_text.encode("utf-8")
    content = TRANSFORMS.resolve(transform, "v1").apply(slice_text, params)
    derivation = DerivedEvidenceRecord(
        sample_id=sample_id,
        source_relpath=relpath,
        source_sha256=hashlib.sha256(source_bytes).hexdigest(),
        transform_name=transform,
        transform_version="v1",
        params_hash=canonical_params_hash(params),
        derived_sha256=hashlib.sha256(content.encode("utf-8")).hexdigest(),
        carrier_bound=False,
    )
    item = EvidenceItem(
        evidence_id=f"{transform}/{sample_id}",
        source_uri=f"{transform}://{relpath}",
        content=content,
        provenance={
            "lock_key": carrier_lock_key,
            "relpath": relpath,
            "sha256": pinned_sha256,
            "extraction": f"{transform}-v1",
            "call_id": call_id,
            "source_call_id": source_call,
            "brief_part": "metadata",
        },
        derivation=derivation,
        derivation_source_bytes=source_bytes,
    )
    return [item.validate()]


def _e22_metadata_brief(
    lock: Mapping[str, object],
    root: Path,
    sample_id: str,
    carrier_lock_key: str,
    values: Mapping[str, object] | None = None,
) -> list[EvidenceItem]:
    """KC-E2: the Earnings-22 pre-meeting brief -- this call's own row of the
    corpus metadata table, rendered as labelled fact lines with the
    Whisper-normalized form beside each value. Built from the benchmark's own
    published table and from nothing else: no transcript, no ESB reference, no
    speaker list, no annotation overlay and no external lookup (owner ruling
    2026-09-07: Earnings-22 collects no external information, or the result stops
    being comparable with the academic references)."""

    return _metadata_brief_items(
        lock, root, sample_id, carrier_lock_key, values, deranged=False, token_matched=False
    )


def _e22_metadata_brief_token_matched(
    lock: Mapping[str, object],
    root: Path,
    sample_id: str,
    carrier_lock_key: str,
    values: Mapping[str, object] | None = None,
) -> list[EvidenceItem]:
    """KC-E2's own arm, PADDED to its twin (owner ruling 2026-09-06, the control
    is locked to the treatment on the flight tokenizer).

    A padded ARM is what the Earnings-21 brief never needed and this one does:
    ``core.metadata_brief.pair_pad_repeats`` is symmetric because a real
    Earnings-22 brief can be longer than the one it twins, so the two sides meet
    in the middle instead of the twin always growing. The arm gains ``" item"``
    repeats and nothing else -- no fact, no name, no sector -- and the ONE factor
    between the two cells stays the words in the five fact fields."""

    return _metadata_brief_items(
        lock, root, sample_id, carrier_lock_key, values, deranged=False, token_matched=True
    )


def _e22_metadata_brief_deranged(
    lock: Mapping[str, object],
    root: Path,
    sample_id: str,
    carrier_lock_key: str,
    values: Mapping[str, object] | None = None,
) -> list[EvidenceItem]:
    """KU-E2c's UNPADDED form twin: the SAME renderer on ANOTHER call's row,
    chosen by the pinned call derangement. Same heading, same five labels, same
    kind of value in every field, and zero information about the call being
    decoded (``core.metadata_brief`` module docstring for why a neutral-token
    placeholder is the wrong control for a five-line fact table)."""

    return _metadata_brief_items(
        lock, root, sample_id, carrier_lock_key, values, deranged=True, token_matched=False
    )


def _e22_metadata_brief_deranged_token_matched(
    lock: Mapping[str, object],
    root: Path,
    sample_id: str,
    carrier_lock_key: str,
    values: Mapping[str, object] | None = None,
) -> list[EvidenceItem]:
    """KU-E2c's TOKEN-matched form twin (owner ruling 2026-09-06): the deranged
    twin with a per-line pad plan replayed onto it, so each twin line measures
    its own brief line on the FLIGHT tokenizer. A third registered source rather
    than a knob, for the reason ``conec-class-lists-placebo-token-matched``
    already gives: a padded and an unpadded twin are different derivations, and
    the pinned transform name is what a sealed trace uses to say which ran."""

    return _metadata_brief_items(
        lock, root, sample_id, carrier_lock_key, values, deranged=True, token_matched=True
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
    if transform_name in CLASS_LIST_TRANSFORMS:
        return {"max_entries_per_class": resolve_max_entries_per_class(values)}
    if transform_name in CLASS_LIST_TOKEN_MATCHED_TRANSFORMS:
        return resolve_placebo_pad_params(values)
    if transform_name in METADATA_BRIEF_TRANSFORMS:
        relpath, sha256_hex = resolve_brief_source_pin(values)
        return {"metadata_relpath": relpath, "metadata_sha256": sha256_hex}
    if transform_name in METADATA_BRIEF_ARM_TOKEN_MATCHED_TRANSFORMS:
        return resolve_arm_token_matched_params(values)
    if transform_name in METADATA_BRIEF_DERANGED_TRANSFORMS:
        return resolve_derangement_params(values)
    if transform_name in METADATA_BRIEF_TOKEN_MATCHED_TRANSFORMS:
        return resolve_token_matched_params(values)
    raise EvidenceError(
        f"no declared-params resolver registered for transform {transform_name!r}"
    )


EVIDENCE_SOURCES.register("none", _none_source)
EVIDENCE_SOURCES.register("conec-contexts", _conec_contexts)
EVIDENCE_SOURCES.register("conec-names", _conec_names)
EVIDENCE_SOURCES.register("derived-candidates", _derived_candidates)
EVIDENCE_SOURCES.register("oracle", _oracle_refusal)
EVIDENCE_SOURCES.register("conec-bias-list", _conec_bias_list)
EVIDENCE_SOURCES.register("conec-bias-phrases", _conec_bias_phrases)
EVIDENCE_SOURCES.register("distractor-only-bias-list", _distractor_only_bias_list)
EVIDENCE_SOURCES.register("conec-class-lists", _conec_class_lists)
EVIDENCE_SOURCES.register("conec-class-lists-placebo", _conec_class_lists_placebo)
EVIDENCE_SOURCES.register(
    "conec-class-lists-placebo-token-matched", _conec_class_lists_placebo_token_matched
)
EVIDENCE_SOURCES.register("e22-metadata-brief", _e22_metadata_brief)
EVIDENCE_SOURCES.register(
    "e22-metadata-brief-token-matched", _e22_metadata_brief_token_matched
)
EVIDENCE_SOURCES.register("e22-metadata-brief-deranged", _e22_metadata_brief_deranged)
EVIDENCE_SOURCES.register(
    "e22-metadata-brief-deranged-token-matched",
    _e22_metadata_brief_deranged_token_matched,
)

# --- WAVE R7: the frozen-historical A2T AgentLoop evidence-source ids -------
#
# Group C of the reuse map (assessment §6.3), the evidence half: fourteen
# ``evidence_source`` values declared by the Audio2Tool AgentLoop baseline
# fragments and resolving in NO core.base registry.
#
# They are deliberately NOT pointed at a live renderer. An EVIDENCE_SOURCES
# entry above is ``(sample, carrier_lock_key, values) -> EvidenceItem`` reading
# ConEC/E22 material off disk; the Audio2Tool "evidence sources" are handbook
# renderers of an entirely different shape that a probe launcher assembled, so
# binding one of these names to a renderer would claim a protocol the sealed
# flight never used. What each id gets instead is a
# ``core.base.FrozenHistoricalComponent``: it RESOLVES, so the fragment's value
# is a name this base accounts for and the engineering-base gate reads it out
# of this canonical registration site; it carries the fragment and the sealed
# receipt that consumed it; and it REFUSES every call. See
# core/frozen_historical.py for the full scan and the disposition rule.
from .frozen_historical import frozen_evidence_source  # noqa: E402

EVIDENCE_SOURCES.register(
    "query-independent-construction-semantic-handbook",
    frozen_evidence_source("query-independent-construction-semantic-handbook"),
)
EVIDENCE_SOURCES.register(
    "same-core-self-transcript-content-bm25-top5",
    frozen_evidence_source("same-core-self-transcript-content-bm25-top5"),
)
EVIDENCE_SOURCES.register(
    "query-independent-full-executable-handbook",
    frozen_evidence_source("query-independent-full-executable-handbook"),
)
EVIDENCE_SOURCES.register(
    "semantic-factor-registry-top1-stripped",
    frozen_evidence_source("semantic-factor-registry-top1-stripped"),
)
EVIDENCE_SOURCES.register(
    "task-blind-English-OBS-to-construction-BM25-k32",
    frozen_evidence_source("task-blind-English-OBS-to-construction-BM25-k32"),
)
EVIDENCE_SOURCES.register(
    "sealed-English-state-to-deterministic-semantic-microground",
    frozen_evidence_source("sealed-English-state-to-deterministic-semantic-microground"),
)
EVIDENCE_SOURCES.register(
    "closed-English-family-taxonomy-to-deterministic-full-unranked-family-contract-bundle",
    frozen_evidence_source(
        "closed-English-family-taxonomy-to-deterministic-full-unranked-family-contract-bundle"
    ),
)
EVIDENCE_SOURCES.register(
    "exhaustive-family-local-reference-scan-then-evidence-bound-resolution",
    frozen_evidence_source(
        "exhaustive-family-local-reference-scan-then-evidence-bound-resolution"
    ),
)
EVIDENCE_SOURCES.register(
    "exhaustive-construction-example-family-assessment",
    frozen_evidence_source("exhaustive-construction-example-family-assessment"),
)
EVIDENCE_SOURCES.register(
    "shared-g7-normalized-assessments-with-complete-macro-actions",
    frozen_evidence_source(
        "shared-g7-normalized-assessments-with-complete-macro-actions"
    ),
)
EVIDENCE_SOURCES.register(
    "paired-complete-registry-or-values-stripped-executable-handbook",
    frozen_evidence_source(
        "paired-complete-registry-or-values-stripped-executable-handbook"
    ),
)
EVIDENCE_SOURCES.register(
    "registry-resolved-union-stripped",
    frozen_evidence_source("registry-resolved-union-stripped"),
)
EVIDENCE_SOURCES.register(
    "local-qwen3-embedding-transcript-to-build-only-tool-tier-centroids",
    frozen_evidence_source(
        "local-qwen3-embedding-transcript-to-build-only-tool-tier-centroids"
    ),
)
EVIDENCE_SOURCES.register(
    "local-qwen3-embedding-tool-tier-centroids-and-same-core-retrieval-query",
    frozen_evidence_source(
        "local-qwen3-embedding-tool-tier-centroids-and-same-core-retrieval-query"
    ),
)
# --- end WAVE R7 -----------------------------------------------------------
