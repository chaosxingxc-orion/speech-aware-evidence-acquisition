"""``FrozenCoreGate`` mixin: D1-anchored evidence byte-identity verification
(IMPORTANT 1, external-threat-model review round 4).

The third identity rail, alongside ``gate_media_identity._MediaIdentityMixin``
(I-4) and ``gate_reference_identity._ReferenceIdentityMixin`` (IMPORTANT 2,
round 3). Before this rail existed, ``core.evidence._conec_contexts`` read a
ConEC context file and computed ``sha256_file(path)`` from whatever was on
disk, storing that self-computed hash as the evidence item's own
provenance -- a tampered context byte returned normally with a fresh,
self-consistent hash and no refusal. Nothing ever compared it to D1's own
frozen per-file identity (``docs/receipts/artifacts/d1-identity.json``,
``conec.layers.e21_contexts``) the way :meth:`verify_media_identity` and
:meth:`verify_reference_identity` already do for media and references.

IMPROVEMENT (fifth external-threat-model review): :meth:`verify_evidence_identity`
re-hashes the evidence FILE on disk, at gate/adapter-construction time -- but the
content a run actually puts in the prompt was already read into memory earlier
(``core.driver.run_experiment``, well before this gate ever opens). A file that is
tampered, read, then RESTORED to its pristine bytes before the gate runs would pass
``verify_evidence_identity`` while the tampered content already read is still what
reaches the model -- the mirror image of the accepted check<->send race
(``contracts.LlamaServerTransport.__call__``'s own documented residual gap; see
``task-5-report.md``): there, the check happens first and the send might not match it
later; here, the read already happened and the check might not reflect it.
:meth:`verify_evidence_content_identity` closes this for evidence, at zero extra I/O
cost -- no file is touched here at all, only the sha256 of bytes the caller already
holds in memory.

Relpath layer routing (2026-08-13, ``conec-names`` gate-closure incident): before
this existed, EVERY evidence relpath a carrier's evidence source supplied was
checked against the SAME single D1 layer named by
``EvidenceLayout.d1_layer_key`` (``e21_contexts`` for conec), regardless of which
PHYSICAL file it actually names. ``core.evidence._conec_names`` reads a
participant-names roster one directory level below ``layout.subdir``
(``<layout.subdir>/participant_names/<id>.names.txt``) -- a file D1's
``e21_contexts`` layer has never recorded (that layer's own
``excluded_non_layer_files`` lists ``participant_names`` as OUTSIDE it, module
docstring of ``core.evidence``). Looking that file's bytes up under
``e21_contexts``'s per-sample facts compared a names-roster file's bytes against a
DIFFERENT file's D1-recorded size/hash, sharing only the ``sample_id`` key -- the
"evidence identity drift" a real run hit despite the file never being tampered.
:meth:`verify_evidence_identity` now routes each relpath EXPLICITLY, per item
(:func:`_route_evidence_layer_key`): a relpath directly under ``layout.subdir``
still resolves to ``layout.d1_layer_key`` (``e21_contexts``, byte-identical to
before this rail existed), a relpath one level deeper under
``layout.subdir``'s own ``participant_names/`` resolves to the new
``e21_participant_names`` layer, and anything else matches no routing rule and
refuses -- fail-closed, the same discipline a missing D1 layer already gets.
:meth:`verify_evidence_content_identity` is unchanged by this: it carries no
relpath to route by (its caller, ``core.model.lifecycle``, passes only
``sample_id -> content bytes``), so it keeps checking the carrier's single
default evidence layer via :meth:`_evidence_manifest`, exactly as before.
"""

from __future__ import annotations

import hashlib
from typing import Mapping

import speech_aware_evidence_acquisition.contracts as _contracts_pkg

from ..data.carriers import CarrierDescriptorError, EvidenceLayout, get_carrier_descriptor
from .errors import GateClosed
from .gate_d1_lookup import _D1IdentityLookupMixin
from .identifiers import _SHA256
from .receipts import _resolve_under, _safe_relative_path

# Relpath routing (module docstring): the participant-names roster's own
# subdir/D1-layer-key -- mirrors ``core.evidence._CONEC_NAMES_SUBDIR_SUFFIX``
# (``contracts.*`` stays independent of ``core.*`` at import time, same
# discipline ``data.carriers``' own module docstring documents for why THAT
# module carries no filesystem/``core.*`` dependency either -- so this is its
# own explicit fact here, not an import, exactly like ``core.evidence`` mirrors
# ``data.carriers.EvidenceLayout`` facts instead of importing ``contracts.*``).
_PARTICIPANT_NAMES_SUBDIR = "participant_names"
_PARTICIPANT_NAMES_D1_LAYER_KEY = "e21_participant_names"


def _route_evidence_layer_key(layout: EvidenceLayout, relpath: str) -> str:
    """Explicit, fail-closed relpath -> D1 layer key routing (module
    docstring's "Relpath layer routing" section for the incident this
    closes). Exactly two relpath shapes are recognised, both relative to
    ``layout.subdir``:

    - ``<layout.subdir>/<anything with no further "/">`` -- a context file
      directly under the layer's own subdir -- routes to
      ``layout.d1_layer_key`` (``e21_contexts`` for conec, unchanged).
    - ``<layout.subdir>/participant_names/<anything with no further "/">``
      -- a names-roster file one directory level deeper -- routes to
      :data:`_PARTICIPANT_NAMES_D1_LAYER_KEY` (``e21_participant_names``).

    Any other shape (an unrecognised sub-directory, e.g. ConEC's own
    ``pdfs/`` -- D1-excluded exactly like ``participant_names`` was before
    this rail existed -- or a relpath that never names a file under
    ``layout.subdir`` at all) matches no routing rule and refuses: a relpath
    this function cannot place is never assumed to be a context file by
    default (IMPORTANT 1 fail-closed, the same discipline a missing D1 layer
    already gets)."""

    subdir_prefix = f"{layout.subdir}/"
    marker = f"/{subdir_prefix}"
    if relpath.startswith(subdir_prefix):
        remainder = relpath[len(subdir_prefix):]
    else:
        index = relpath.find(marker)
        if index == -1:
            raise GateClosed(
                f"evidence relpath {relpath!r} does not name a file under carrier "
                f"evidence layer {layout.lock_key!r}'s own {layout.subdir!r} subdir; "
                "model touch refused (no evidence-layer routing rule matched, "
                "IMPORTANT 1 fail-closed)"
            )
        remainder = relpath[index + len(marker):]
    if not remainder:
        raise GateClosed(
            f"evidence relpath {relpath!r} names no file under carrier evidence "
            f"layer {layout.lock_key!r}'s own {layout.subdir!r} subdir; model touch "
            "refused (no evidence-layer routing rule matched, IMPORTANT 1 "
            "fail-closed)"
        )
    if "/" not in remainder:
        return layout.d1_layer_key
    head, _, tail = remainder.partition("/")
    if head == _PARTICIPANT_NAMES_SUBDIR and tail and "/" not in tail:
        return _PARTICIPANT_NAMES_D1_LAYER_KEY
    raise GateClosed(
        f"evidence relpath {relpath!r} matches no known routing rule under carrier "
        f"evidence layer {layout.lock_key!r}'s own {layout.subdir!r} subdir; model "
        "touch refused (IMPORTANT 1 fail-closed)"
    )


class _EvidenceIdentityMixin(_D1IdentityLookupMixin):
    """``verify_evidence_identity``/``verify_evidence_content_identity``: the
    evidence-layer counterpart to
    ``gate_media_identity._MediaIdentityMixin.verify_media_identity`` /
    ``gate_reference_identity._ReferenceIdentityMixin.verify_reference_identity``."""

    def _evidence_layout(self, carrier_lock_key: str) -> EvidenceLayout:
        """Resolve ``carrier_lock_key``'s own D1-recorded evidence layout --
        the descriptor-level refusals (unregistered carrier, no evidence
        layer at all) that hold regardless of which D1 layer key a specific
        relpath ultimately routes to (:func:`_route_evidence_layer_key`)."""

        try:
            descriptor = get_carrier_descriptor(carrier_lock_key)
        except CarrierDescriptorError as error:
            raise GateClosed(
                f"carrier {carrier_lock_key!r} has no registered carrier descriptor; "
                f"cannot resolve an evidence-layer identity for it: {error}"
            ) from error
        if descriptor.evidence is None:
            raise GateClosed(
                f"carrier {carrier_lock_key!r} has no D1-recorded evidence-layer "
                "identity this gate can re-verify (data.carriers.CarrierDescriptor."
                "evidence is None); an evidence source configured for it is refused "
                "rather than silently trusted (IMPORTANT 1 fail-closed)"
            )
        return descriptor.evidence

    def _evidence_layer_manifest(
        self, carrier_lock_key: str, layout: EvidenceLayout, d1_layer_key: str
    ) -> dict[str, tuple[int, str]]:
        """Load D1's recorded per-sample ``(bytes, sha256)`` manifest for
        exactly ONE of ``layout.lock_key``'s D1 layers (``d1_layer_key``) --
        the routing-aware building block :meth:`verify_evidence_identity`
        calls once per distinct layer key its relpaths route to, and
        :meth:`_evidence_manifest` calls once for the carrier's single
        default layer. Raises :class:`GateClosed` for every refusal both
        callers already documented (missing carrier identity, missing/
        malformed manifest)."""

        document = self._load(self._d1_identity_artifact_path(), "D1 identity artifact")
        carriers = document.get("carriers")
        carrier_doc = carriers.get(layout.lock_key) if isinstance(carriers, Mapping) else None
        if not isinstance(carrier_doc, Mapping):
            raise GateClosed(
                f"D1 identity artifact has no per-sample identity for evidence carrier "
                f"{layout.lock_key!r} (plan carrier {carrier_lock_key!r}); model touch "
                "refused"
            )
        layers = carrier_doc.get("layers")
        evidence_layer = layers.get(d1_layer_key) if isinstance(layers, Mapping) else None
        manifest_entries = (
            evidence_layer.get("manifest") if isinstance(evidence_layer, Mapping) else None
        )
        if not isinstance(manifest_entries, list) or not manifest_entries:
            raise GateClosed(
                f"D1 identity artifact carrier {layout.lock_key!r} lacks a "
                f"{d1_layer_key!r} manifest; model touch refused"
            )
        recorded: dict[str, tuple[int, str]] = {}
        for entry in manifest_entries:
            if not isinstance(entry, Mapping):
                raise GateClosed("D1 evidence manifest entry is not an object")
            sample_id = entry.get("id")
            rec_bytes = entry.get("bytes")
            rec_sha = entry.get("sha256")
            if (
                not isinstance(sample_id, str)
                or not sample_id
                or isinstance(rec_bytes, bool)
                or not isinstance(rec_bytes, int)
                or rec_bytes <= 0
                or not isinstance(rec_sha, str)
                or _SHA256.fullmatch(rec_sha) is None
            ):
                raise GateClosed(f"D1 evidence manifest entry is malformed: {entry!r}")
            recorded[sample_id] = (rec_bytes, rec_sha)
        return recorded

    def _evidence_manifest(self, carrier_lock_key: str) -> tuple[object, dict[str, tuple[int, str]]]:
        """Shared by :meth:`verify_evidence_content_identity` (the ONLY
        caller left -- :meth:`verify_evidence_identity` now routes per
        relpath via :meth:`_evidence_layer_manifest` directly, module
        docstring): resolve ``carrier_lock_key``'s evidence layout and load
        D1's recorded per-sample ``(bytes, sha256)`` manifest for its single
        DEFAULT layer (``layout.d1_layer_key``) -- unchanged from before the
        relpath-routing rail existed, since content identity carries no
        relpath to route by. Returns ``(layout, recorded)``; raises
        :class:`GateClosed` for every refusal both callers already
        documented (unregistered carrier, no evidence layer, missing/
        malformed manifest)."""

        layout = self._evidence_layout(carrier_lock_key)
        recorded = self._evidence_layer_manifest(carrier_lock_key, layout, layout.d1_layer_key)
        return layout, recorded

    def verify_evidence_identity(
        self, carrier_lock_key: str, evidence_facts: Mapping[str, str]
    ) -> None:
        """IMPORTANT 1 (external-threat-model review round 4): re-verify, AS
        FILES, the D1-frozen evidence bytes a run's evidence source actually
        drew from -- never merely trust a self-computed ``sha256_file()``
        claim (``core.evidence`` module docstring for what this closes).

        ``evidence_facts`` maps each sample id THIS run's evidence source
        supplied non-empty evidence for, to that evidence file's path,
        relative to ``self.data_root`` -- computed by the caller via
        ``core.evidence.evidence_file_relpath``, the SAME relative-path
        convention ``core.evidence._conec_contexts`` itself resolves,
        rather than re-derived here. Scoped to exactly the samples the
        run's evidence source actually touched (never the whole evidence
        corpus), mirroring :meth:`verify_media_identity`'s cost discipline.
        Computed BEFORE any ``evidence_mismatch``/``rotated_mismatch``
        reassignment (``core.driver.run_experiment``'s own comment): this
        checks the byte-integrity of the evidence CORPUS a sample's own
        evidence-source call drew from, independent of which sample a later
        negative-control experiment happens to route that content to.

        The evidence layer's location is derived entirely from
        ``carrier_lock_key``'s own ``data.carriers.CarrierDescriptor.
        evidence`` (an :class:`~data.carriers.EvidenceLayout`: which lock
        key/subdir/extension/D1-layer-key the layer lives under) -- never a
        hand-coded path. A carrier whose descriptor declares no evidence
        layer at all (``descriptor.evidence is None``, e.g.
        earnings22-original, whose ConEC contexts are a different-shaped,
        never-read per-call-PDF layer) fails closed here too, independent
        of ``core.evidence``'s own internal refusal -- the same "never
        merely trust the caller" discipline :meth:`verify_reference_identity`
        already applies via ``_REFERENCE_SCOPED_CARRIER_LOCK_KEYS``. See
        ``docs/owner-decisions-pending.md`` for the exact carrier coverage
        this leaves and why.

        Each ``relpath`` is routed, individually, to the D1 layer key it must
        be verified against (:func:`_route_evidence_layer_key`, module
        docstring's "Relpath layer routing" section) -- a mixed
        ``evidence_facts`` mapping (some relpaths naming context files, some
        naming participant-names rosters) checks each sample against its OWN
        layer's D1 facts, never a single carrier-wide default. Per-layer
        manifests are loaded at most once per distinct layer key actually
        routed to in this call, not once per sample.
        """

        if not isinstance(evidence_facts, Mapping) or not evidence_facts:
            raise GateClosed(
                "verify_evidence_identity requires a non-empty sample_id -> "
                "evidence_relpath mapping"
            )
        layout = self._evidence_layout(carrier_lock_key)
        manifests_by_layer_key: dict[str, dict[str, tuple[int, str]]] = {}

        for sample_id, relpath in evidence_facts.items():
            if not isinstance(sample_id, str) or not isinstance(relpath, str):
                raise GateClosed(
                    f"evidence_facts[{sample_id!r}] must be a string evidence relpath"
                )
            d1_layer_key = _route_evidence_layer_key(layout, relpath)
            recorded = manifests_by_layer_key.get(d1_layer_key)
            if recorded is None:
                recorded = self._evidence_layer_manifest(carrier_lock_key, layout, d1_layer_key)
                manifests_by_layer_key[d1_layer_key] = recorded
            d1_fact = recorded.get(sample_id)
            if d1_fact is None:
                raise GateClosed(
                    f"sample {sample_id!r} (carrier {carrier_lock_key!r}) has no "
                    "D1-recorded evidence identity; evidence outside D1's identity "
                    "closure can never enter a run"
                )
            rec_bytes, rec_sha = d1_fact
            relative = _safe_relative_path(relpath, f"evidence_facts[{sample_id!r}] relpath")
            resolved = _resolve_under(
                self.data_root, relative, f"evidence for sample {sample_id!r}"
            )
            actual_bytes, actual_sha = _contracts_pkg._measure_file(
                resolved, f"evidence for sample {sample_id!r}"
            )
            if actual_bytes != rec_bytes or actual_sha != rec_sha:
                raise GateClosed(
                    f"evidence identity drift for sample {sample_id!r}: D1 recorded "
                    f"{rec_bytes} bytes / {rec_sha[:12]}..., the live file is now "
                    f"{actual_bytes} bytes / {actual_sha[:12]}...; model touch refused "
                    "(IMPORTANT 1)"
                )

    def verify_evidence_content_identity(
        self, carrier_lock_key: str, evidence_contents: Mapping[str, bytes]
    ) -> None:
        """IMPROVEMENT (fifth external-threat-model review): bind the check to
        the bytes actually consumed -- compare D1's recorded sha256 against
        the ALREADY-READ evidence content a run will actually put in the
        prompt, never a second read of the file (module docstring for the
        check<->send race this closes; :meth:`verify_evidence_identity`
        remains the file-identity rail, unchanged, run alongside this one).

        ``evidence_contents`` maps each sample id THIS run's evidence source
        supplied non-empty evidence for to the exact UTF-8 bytes of that
        evidence's ``EvidenceItem.content`` -- the SAME population
        :meth:`verify_evidence_identity` checks (``core.driver.run_experiment``
        builds both from the one ``evidence_by_sample`` it already read),
        sharing this gate's D1 manifest lookup (:meth:`_evidence_manifest`).
        No filesystem access happens in this method at all: the caller
        already paid the one read cost when it built ``evidence_contents``,
        so this check is a pure in-memory hash comparison, zero additional
        I/O.
        """

        if not isinstance(evidence_contents, Mapping) or not evidence_contents:
            raise GateClosed(
                "verify_evidence_content_identity requires a non-empty sample_id -> "
                "content-bytes mapping"
            )
        _, recorded = self._evidence_manifest(carrier_lock_key)

        for sample_id, content_bytes in evidence_contents.items():
            if not isinstance(sample_id, str) or not isinstance(
                content_bytes, (bytes, bytearray)
            ):
                raise GateClosed(
                    f"evidence_contents[{sample_id!r}] must be bytes"
                )
            d1_fact = recorded.get(sample_id)
            if d1_fact is None:
                raise GateClosed(
                    f"sample {sample_id!r} (carrier {carrier_lock_key!r}) has no "
                    "D1-recorded evidence identity; evidence outside D1's identity "
                    "closure can never enter a run"
                )
            rec_bytes, rec_sha = d1_fact
            actual_bytes = len(content_bytes)
            actual_sha = hashlib.sha256(content_bytes).hexdigest()
            if actual_bytes != rec_bytes or actual_sha != rec_sha:
                raise GateClosed(
                    f"evidence content identity drift for sample {sample_id!r}: D1 "
                    f"recorded {rec_bytes} bytes / {rec_sha[:12]}..., the in-memory "
                    f"content this run already read is {actual_bytes} bytes / "
                    f"{actual_sha[:12]}...; model touch refused (fifth review, "
                    "evidence-bytes-consumed check)"
                )
