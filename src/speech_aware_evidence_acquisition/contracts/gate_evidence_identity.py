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

Follow-up (2026-08-13, same incident, second check point): the relpath-routing
fix above landed alone first and was declared "unchanged" for
:meth:`verify_evidence_content_identity` -- but that method sees the SAME
``conec-names`` evidence in a real gated run (``core.model.lifecycle`` calls
both checks back to back on the SAME ``binding``), and it ALSO used to resolve
every sample's expected facts from the carrier's single default layer
(``e21_contexts``) by ``sample_id`` alone, with no relpath at all to route by.
A real run hit this exact "evidence content identity drift" for the same
reason, one check point later: the file rail passed (routed correctly), the
content rail still checked the names bytes against the contexts layer's
facts. :meth:`verify_evidence_content_identity` now takes a SECOND required
mapping, ``evidence_relpaths`` -- the SAME per-sample relpaths
:meth:`verify_evidence_identity` itself routes by -- and routes each sample's
content the identical way (:func:`_route_evidence_layer_key`, shared, not
reimplemented). ``core.model.lifecycle`` threads it through from the SAME
``binding.evidence_relpaths`` the file check already consulted (that field
already existed on ``core.base.PayloadBindingContext`` for the first check;
nothing new needed there). A sample present in ``evidence_contents`` with no
matching entry in ``evidence_relpaths`` refuses -- fail-closed, never assumed
to belong to the default layer.

D1 evidence supplement (2026-09-06, KC-E1 precondition 1)
---------------------------------------------------------
The relpath routing above has always been able to NAME ``e21_participant_names``
and has never been able to RESOLVE it: the immutable E0 D1 artifact records four
ConEC layers and not that one (``e21_contexts``'s own
``excluded_non_layer_files`` lists ``participant_names`` as outside it), so every
run whose evidence source reads a participant-names roster failed closed here.
The E0 D1 artifact is never rewritten in place, so the layer arrives the same way
a bounded media slice already does (``gate_media_identity._d1_media_supplement_records``):
as an ADDITIVE, hash-pinned successor document, ``saea-d1-evidence-supplement-v1``,
carrying exactly ONE declared D1 layer key and that layer's own
``data.identity.Layer`` digests -- ``ids_sha256`` over the LF-joined sorted sample
ids and ``manifest_sha256`` over the LF-joined ``id,bytes,sha256`` lines, the SAME
two recipes ``data.identity`` computes for every layer already inside D1, so the
supplement's facts are recomputable by the functions that produced its siblings
rather than by a second, supplement-only convention.

Four refusals make it additive rather than a rewrite: the supplement's
``parent_d1_sha256`` must equal the live D1 artifact's own digest; its
``carrier_lock_key`` must equal the evidence layout's carrier; it may NOT declare
a layer key the base D1 already carries (no shadowing -- a supplement can only
ADD a layer, never replace one); and its ``source_binding_sha256`` must equal BOTH
its own ``ids_sha256`` AND the base D1 carrier's own default evidence layer's
``ids_sha256``, i.e. the supplement covers exactly the carrier's already-frozen
sample universe and can never quietly widen it.

ONE supplement per gate (``gate.FrozenCoreGate.__post_init__``): a gate carries
the base D1 identity plus at most one supplement, media or evidence, never both.

One sample, several evidence files (2026-09-06, same task)
-----------------------------------------------------------
Routing per relpath is only useful if every relpath a sample draws on actually
REACHES the rail. Both methods used to take one relpath and one content blob per
sample, and ``core.driver.run_experiment``'s per-item loop assigned rather than
accumulated -- so a source returning several carrier-bound items per sample had
all but the LAST silently dropped. E5's ``conec-class-lists`` is exactly that: two
items per call, the participant roster and the context document, routing to two
different layers. The roster half -- the whole point of the supplement above --
was therefore never checked. Both methods now accept, per sample, either a bare
value (unchanged for every existing caller) or an ordered tuple
(:func:`_as_tuple`); ``evidence_contents`` and ``evidence_relpaths`` are
positionally paired and a length mismatch refuses, because an unpaired content
has no relpath to route by.
"""

from __future__ import annotations

import hashlib
from typing import Mapping

import speech_aware_evidence_acquisition.contracts as _contracts_pkg

from ..data.carriers import CarrierDescriptorError, EvidenceLayout, get_carrier_descriptor
from .errors import GateClosed
from .gate_d1_lookup import _D1IdentityLookupMixin
from .identifiers import _SHA256, STUDY_SLUG
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

#: The additive D1 evidence-layer successor document's schema (module
#: docstring's "D1 evidence supplement" section). Its media counterpart is
#: ``gate_media_identity``'s own ``saea-d1-media-supplement-v1``; the two are
#: mutually exclusive on one gate (``gate.FrozenCoreGate.__post_init__``).
EVIDENCE_SUPPLEMENT_SCHEMA = "saea-d1-evidence-supplement-v1"

#: Exact key set of that document -- an extra or missing key refuses, the same
#: discipline the media supplement applies to its own envelope.
_EVIDENCE_SUPPLEMENT_KEYS = frozenset(
    {
        "schema",
        "study",
        "carrier_lock_key",
        "d1_layer_key",
        "parent_d1_sha256",
        "source_binding_sha256",
        "count",
        "ids_sha256",
        "manifest",
        "manifest_sha256",
        "total_bytes",
        "excluded_non_layer_files",
    }
)


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


def _as_tuple(value: object, label: str, kinds: tuple[type, ...]) -> tuple:
    """One value or an ordered tuple of them (2026-09-06, KC-E1).

    A sample may draw on MORE THAN ONE evidence file: E5's ``conec-class-lists``
    reads the call's participant roster AND its context document, which route to
    two different D1 layers. Both rails therefore accept either a bare value
    (one file -- byte-identical to every caller that predates this) or a
    non-empty tuple of them, checked in order and each routed on its own.
    Fail-closed on anything else, including an empty tuple."""

    values = value if isinstance(value, tuple) else (value,)
    if not values or not all(isinstance(item, kinds) for item in values):
        raise GateClosed(
            f"{label} must be a {'/'.join(kind.__name__ for kind in kinds)} or a "
            "non-empty tuple of them"
        )
    return values


def _parse_evidence_manifest(
    manifest_entries: object, label: str
) -> dict[str, tuple[int, str]]:
    """One per-sample ``(bytes, sha256)`` manifest, parsed with the same
    fail-closed shape rules whether it came from the base D1 artifact or from
    an additive evidence supplement -- one parser, never two that could drift."""

    if not isinstance(manifest_entries, list) or not manifest_entries:
        raise GateClosed(f"{label} must be a non-empty list")
    recorded: dict[str, tuple[int, str]] = {}
    for entry in manifest_entries:
        if not isinstance(entry, Mapping):
            raise GateClosed(f"{label} entry is not an object")
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
            raise GateClosed(f"{label} entry is malformed: {entry!r}")
        if sample_id in recorded:
            raise GateClosed(f"{label} repeats sample id {sample_id!r}")
        recorded[sample_id] = (rec_bytes, rec_sha)
    return recorded


def _layer_ids_sha256(recorded: Mapping[str, tuple[int, str]]) -> str:
    """``data.identity.Layer.ids_sha256``'s recipe, recomputed here so the
    supplement's claimed digest is checked rather than trusted (``contracts.*``
    stays independent of ``data.identity`` at import time, the same discipline
    :func:`_route_evidence_layer_key` follows for ``core.evidence``'s own
    constants)."""

    return hashlib.sha256("\n".join(sorted(recorded)).encode("utf-8")).hexdigest()


def _layer_manifest_sha256(recorded: Mapping[str, tuple[int, str]]) -> str:
    """``data.identity.Layer.manifest_sha256``'s recipe, recomputed the same way
    and for the same reason as :func:`_layer_ids_sha256`."""

    lines = "\n".join(
        f"{sample_id},{facts[0]},{facts[1]}" for sample_id, facts in sorted(recorded.items())
    )
    return hashlib.sha256(lines.encode("utf-8")).hexdigest()


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
        the routing-aware building block both :meth:`verify_evidence_identity`
        and :meth:`verify_evidence_content_identity` call once per distinct
        layer key their relpaths route to (follow-up, module docstring: both
        checks now share this exact per-layer loader, neither has its own
        single-default-layer path any more). Raises :class:`GateClosed` for
        every refusal both callers already documented (missing carrier
        identity, missing/malformed manifest)."""

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
        base_present = isinstance(manifest_entries, list) and bool(manifest_entries)
        supplement = self._d1_evidence_supplement_manifest(
            layout, d1_layer_key, carrier_doc, base_present=base_present
        )
        if supplement is not None:
            return supplement
        if not base_present:
            raise GateClosed(
                f"D1 identity artifact carrier {layout.lock_key!r} lacks a "
                f"{d1_layer_key!r} manifest, and no D1 evidence supplement declares that "
                "layer; model touch refused"
            )
        return _parse_evidence_manifest(manifest_entries, "D1 evidence manifest")

    def _d1_evidence_supplement_manifest(
        self,
        layout: EvidenceLayout,
        d1_layer_key: str,
        carrier_doc: Mapping[str, object],
        *,
        base_present: bool,
    ) -> dict[str, tuple[int, str]] | None:
        """The additive D1 evidence-layer successor, or ``None`` (module
        docstring's "D1 evidence supplement" section).

        Returns ``None`` when no supplement is configured on this gate, and when
        the configured supplement declares a DIFFERENT layer key than the one
        being resolved -- one supplement carries exactly one layer, and a relpath
        routed to any other layer is answered from the base D1 alone. Every other
        outcome is either a validated manifest or a refusal."""

        path = getattr(self, "d1_evidence_supplement", None)
        expected_digest = getattr(self, "d1_evidence_supplement_sha256", None)
        if path is None and expected_digest is None:
            return None
        if path is None or expected_digest is None or _SHA256.fullmatch(expected_digest) is None:
            raise GateClosed(
                "D1 evidence supplement path and lowercase 64-hex SHA-256 must be paired"
            )
        supplement_bytes, actual_digest = _contracts_pkg._measure_file(
            path, "D1 evidence supplement"
        )
        if actual_digest != expected_digest:
            raise GateClosed(
                "D1 evidence supplement hash drift: configured "
                f"{expected_digest[:12]}..., actual {actual_digest[:12]}..."
            )
        document = self._load(path, "D1 evidence supplement")
        if set(document) != set(_EVIDENCE_SUPPLEMENT_KEYS):
            raise GateClosed(
                "D1 evidence supplement must carry exact keys "
                f"{sorted(_EVIDENCE_SUPPLEMENT_KEYS)}"
            )
        if document["schema"] != EVIDENCE_SUPPLEMENT_SCHEMA:
            raise GateClosed("D1 evidence supplement schema mismatch")
        if document["study"] != STUDY_SLUG:
            raise GateClosed("D1 evidence supplement study identity mismatch")
        declared_layer = document["d1_layer_key"]
        if not isinstance(declared_layer, str) or not declared_layer:
            raise GateClosed("D1 evidence supplement d1_layer_key must be non-empty text")
        if document["carrier_lock_key"] != layout.lock_key:
            raise GateClosed(
                "D1 evidence supplement carrier does not match the evidence layer's own "
                f"carrier {layout.lock_key!r}"
            )
        if declared_layer != d1_layer_key:
            return None
        if base_present:
            raise GateClosed(
                f"D1 evidence supplement declares layer {declared_layer!r}, which the base "
                "D1 identity artifact already records; a supplement may only ADD a layer, "
                "never shadow one"
            )
        _base_bytes, base_digest = _contracts_pkg._measure_file(
            self._d1_identity_artifact_path(), "parent D1 identity artifact"
        )
        if document["parent_d1_sha256"] != base_digest:
            raise GateClosed("D1 evidence supplement parent D1 hash mismatch")
        binding = document["source_binding_sha256"]
        if not isinstance(binding, str) or _SHA256.fullmatch(binding) is None:
            raise GateClosed("D1 evidence supplement source binding hash is malformed")
        # The carrier's OWN default evidence layer is the frozen sample universe
        # this supplement must cover exactly -- never a wider one.
        layers = carrier_doc.get("layers")
        default_layer = layers.get(layout.d1_layer_key) if isinstance(layers, Mapping) else None
        universe = default_layer.get("ids_sha256") if isinstance(default_layer, Mapping) else None
        if not isinstance(universe, str) or _SHA256.fullmatch(universe) is None:
            raise GateClosed(
                f"D1 identity artifact carrier {layout.lock_key!r} has no usable "
                f"{layout.d1_layer_key!r} ids_sha256 to bind an evidence supplement to"
            )
        if binding != universe:
            raise GateClosed(
                "D1 evidence supplement source binding does not name the carrier's own "
                f"{layout.d1_layer_key!r} sample universe"
            )
        excluded = document["excluded_non_layer_files"]
        if not isinstance(excluded, list) or not all(
            isinstance(name, str) and name for name in excluded
        ):
            raise GateClosed(
                "D1 evidence supplement excluded_non_layer_files must be a list of "
                "non-empty file names"
            )
        recorded = _parse_evidence_manifest(document["manifest"], "D1 evidence supplement")
        ids_digest = _layer_ids_sha256(recorded)
        if document["count"] != len(recorded) or document["ids_sha256"] != ids_digest:
            raise GateClosed("D1 evidence supplement count or ids SHA-256 mismatch")
        if ids_digest != universe:
            raise GateClosed(
                "D1 evidence supplement covers a different sample set than the carrier's own "
                f"{layout.d1_layer_key!r} layer"
            )
        if document["manifest_sha256"] != _layer_manifest_sha256(recorded):
            raise GateClosed("D1 evidence supplement manifest SHA-256 mismatch")
        total_bytes = sum(facts[0] for facts in recorded.values())
        if document["total_bytes"] != total_bytes or supplement_bytes <= 0:
            raise GateClosed("D1 evidence supplement total_bytes mismatch")
        return recorded

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
            if not isinstance(sample_id, str) or not sample_id:
                raise GateClosed("evidence_facts keys must be non-empty sample ids")
            for one_relpath in _as_tuple(
                relpath, f"evidence_facts[{sample_id!r}]", (str,)
            ):
                d1_layer_key = _route_evidence_layer_key(layout, one_relpath)
                recorded = manifests_by_layer_key.get(d1_layer_key)
                if recorded is None:
                    recorded = self._evidence_layer_manifest(
                        carrier_lock_key, layout, d1_layer_key
                    )
                    manifests_by_layer_key[d1_layer_key] = recorded
                d1_fact = recorded.get(sample_id)
                if d1_fact is None:
                    raise GateClosed(
                        f"sample {sample_id!r} (carrier {carrier_lock_key!r}) has no "
                        "D1-recorded evidence identity; evidence outside D1's identity "
                        "closure can never enter a run"
                    )
                rec_bytes, rec_sha = d1_fact
                relative = _safe_relative_path(
                    one_relpath, f"evidence_facts[{sample_id!r}] relpath"
                )
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
        self,
        carrier_lock_key: str,
        evidence_contents: Mapping[str, bytes],
        evidence_relpaths: Mapping[str, str],
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
        builds both from the one ``evidence_by_sample`` it already read).
        No filesystem access happens in this method at all: the caller
        already paid the one read cost when it built ``evidence_contents``,
        so this check is a pure in-memory hash comparison, zero additional
        I/O.

        ``evidence_relpaths`` (follow-up, 2026-08-13, module docstring's
        second "Relpath layer routing" section) maps the SAME sample ids to
        the SAME evidence relpath :meth:`verify_evidence_identity` itself
        routes by -- the caller (``core.model.lifecycle``) threads it
        through from the SAME ``binding.evidence_relpaths`` the file check
        already consulted. Each sample's content is routed to its own D1
        layer key via :func:`_route_evidence_layer_key`, exactly like the
        file rail; per-layer manifests are loaded at most once per distinct
        layer key actually routed to in this call, not once per sample. A
        sample present in ``evidence_contents`` with no matching entry in
        ``evidence_relpaths`` refuses -- fail-closed, never assumed to
        belong to the carrier's default layer.
        """

        if not isinstance(evidence_contents, Mapping) or not evidence_contents:
            raise GateClosed(
                "verify_evidence_content_identity requires a non-empty sample_id -> "
                "content-bytes mapping"
            )
        if not isinstance(evidence_relpaths, Mapping) or not evidence_relpaths:
            raise GateClosed(
                "verify_evidence_content_identity requires a non-empty sample_id -> "
                "evidence_relpath mapping to route each sample's content against its "
                "own D1 layer (IMPORTANT 1 fail-closed)"
            )
        layout = self._evidence_layout(carrier_lock_key)
        manifests_by_layer_key: dict[str, dict[str, tuple[int, str]]] = {}

        for sample_id, content_bytes in evidence_contents.items():
            if not isinstance(sample_id, str) or not sample_id:
                raise GateClosed("evidence_contents keys must be non-empty sample ids")
            blobs = _as_tuple(
                content_bytes, f"evidence_contents[{sample_id!r}]", (bytes, bytearray)
            )
            relpath = evidence_relpaths.get(sample_id)
            if relpath is None:
                raise GateClosed(
                    f"evidence_contents[{sample_id!r}] has no matching "
                    "evidence_relpaths entry to route its D1 layer by; model touch "
                    "refused (IMPORTANT 1 fail-closed)"
                )
            relpaths = _as_tuple(
                relpath, f"evidence_relpaths[{sample_id!r}]", (str,)
            )
            if len(relpaths) != len(blobs):
                raise GateClosed(
                    f"evidence_contents[{sample_id!r}] carries {len(blobs)} contents "
                    f"but evidence_relpaths carries {len(relpaths)} relpaths; the two "
                    "are positionally paired and an unpaired content can never be "
                    "routed (IMPORTANT 1 fail-closed)"
                )
            for one_relpath, one_content in zip(relpaths, blobs):
                d1_layer_key = _route_evidence_layer_key(layout, one_relpath)
                recorded = manifests_by_layer_key.get(d1_layer_key)
                if recorded is None:
                    recorded = self._evidence_layer_manifest(
                        carrier_lock_key, layout, d1_layer_key
                    )
                    manifests_by_layer_key[d1_layer_key] = recorded
                d1_fact = recorded.get(sample_id)
                if d1_fact is None:
                    raise GateClosed(
                        f"sample {sample_id!r} (carrier {carrier_lock_key!r}) has no "
                        "D1-recorded evidence identity; evidence outside D1's identity "
                        "closure can never enter a run"
                    )
                rec_bytes, rec_sha = d1_fact
                actual_bytes = len(one_content)
                actual_sha = hashlib.sha256(one_content).hexdigest()
                if actual_bytes != rec_bytes or actual_sha != rec_sha:
                    raise GateClosed(
                        f"evidence content identity drift for sample {sample_id!r}: D1 "
                        f"recorded {rec_bytes} bytes / {rec_sha[:12]}..., the in-memory "
                        f"content this run already read is {actual_bytes} bytes / "
                        f"{actual_sha[:12]}...; model touch refused (fifth review, "
                        "evidence-bytes-consumed check)"
                    )
