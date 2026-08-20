"""P-EMB-3L flight delta -- REGISTERED probe SAEA-PROBE-pemb3l-234
(``bounded-discovery-probe``): ``docs/readiness/
2026-08-20-pemb3l-preregistration-REGISTERED.md``. MACHINERY ONLY: this
module contains zero live model contact and is never itself pointed at a
real server -- every test drives ``rails.embedding_client.
MockEmbeddingClient``, exactly like the parent ``rails.probes.pemb_flight``
suite.

Extends the consumed P-EMB-1 read (``SAEA-PROBE-pemb1-78``, EMB-WEAK,
``docs/readiness/2026-08-19-pemb1-verdict.md``) with a three-arm sweep over
the SAME frozen surface -- the 60 SLURP devel audio samples +
the 18 canonical scenario labels, the SAME ``split_identity_hash`` pinned in
``rails.probes.pemb_flight`` (:data:`~.pemb_flight.
EXPECTED_RUN_A_SPLIT_IDENTITY_HASH`, reused verbatim, never re-derived) --
under three training-free constructions the pinned llama.cpp already
supports, before any external embedder is adopted:

======  ============  =========================================================
arm     pooling mode  instruction prefix (BOTH sides, common-mode)
======  ============  =========================================================
L1      last          none (bare, mirrors P-EMB-1's own text/audio shape)
L2      last          GritLM-style instruct prefixes (:data:`AUDIO_INSTRUCT_PREFIX`
                       / :data:`TEXT_INSTRUCT_PREFIX`)
L3      mean          the SAME instruct prefixes as L2
======  ============  =========================================================

Each arm is its own 60+18=78-contact flight (:func:`run_pemb3l_arm_flight`,
:data:`ARM_TOTAL_N`); the full sweep is 3*78=234 contacts
(:data:`EXPECTED_TOTAL_CONTACTS`), zero generation. The registration's own
cited comparator -- mean pooling, no instruction, EMB-WEAK's own 3/60 =
0.0500 -- is NOT re-flown here; it is the CITED constant
:data:`CITED_MEAN_BARE_ACCURACY` (provenance: ``docs/readiness/
2026-08-19-pemb1-verdict.md`` section 1, "argmax-cosine accuracy vs gold ...
3 / 60 = 0.0500", the SAME already-consumed P-EMB-1 read this probe's own
registration cites verbatim). ``analysis.pemb3l_read`` computes the
L3-vs-cited-mean-bare common-mode delta from this constant, never by
re-embedding the mean-bare construction a second time.

Two server sessions, tagged not managed (module docstring continued): L1 and
L2 share pooling mode ``last`` and therefore ONE ``--pooling last`` llama-
server session's client; L3 alone needs a SEPARATE ``--pooling mean``
session's client (a resident llama-server's pooling mode is a startup flag,
never a per-request parameter -- this module performs no server
spawning/selection of its own, mirroring every sibling probe module's own
"caller loads/derives, this module only resolves" split). Each
:class:`Pemb3lArm` carries its own required ``pooling_mode`` so the flight
agent that DOES own servers can route each arm to the correct session
without this module ever touching a socket; :func:`run_pemb3l_sweep_flight`
accordingly takes one client PER arm_id, never a single shared client.

Binding config + sha256 (module docstring continued, prereg: "EXACT strings
... frozen in the binding config with sha256"): :func:`binding_config_sha256`
recomputes a canonical JSON digest of every arm's own
(pooling_mode, audio_prefix, text_prefix) tuple and :func:`assert_
binding_config_sha256` fails LOUD, before any flight, the moment a future
edit drifts the arm table away from the pinned :data:`BINDING_CONFIG_SHA256`
-- the two EXACT instruct-prefix strings therefore can never silently change
underneath a flight already in progress.

Vector persistence reuses ``rails.probes.pemb_flight.write_embedding_manifest``
/ ``load_embedding_manifest`` UNMODIFIED (never a second manifest writer):
each arm's own :class:`~.pemb_flight.PembRunSummary` carries
``run_id = arm_run_id(arm_id)`` (``"SAEA-PROBE-pemb3l-234/<arm>"``), so the
existing writer's own ``derived/embeddings/<run_id>/...`` path convention
places each arm's vectors + manifest under
``derived/embeddings/SAEA-PROBE-pemb3l-234/<arm>/`` exactly as registered,
with zero new I/O code.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping, Sequence

from ..adapters.slurp import SlurpSample
from ..embedding_client import EmbeddingClientProtocol
from .pemb_flight import (
    EXPECTED_RUN_A_SPLIT_IDENTITY_HASH,
    RUN_A_AUDIO_N,
    RUN_A_LABEL_N,
    LoadedEmbeddingManifest,
    PembFlightError,
    PembRunSummary,
    _read_audio_bytes,
    _validate_run_summary,
    assert_run_a_split_identity_hash,
    load_embedding_manifest,
    write_embedding_manifest,
)
from .pslu_flight import _source_references_ontology_miner, assert_never_calls_ontology_miner

PROBE_ID = "SAEA-PROBE-pemb3l-234"

POOLING_LAST = "last"
POOLING_MEAN = "mean"

ARM_L1_ID = "l1-last-bare"
ARM_L2_ID = "l2-last-instruct"
ARM_L3_ID = "l3-mean-instruct"

# EXACT strings, pinned verbatim from the registration (module docstring
# table). Trailing spaces are load-bearing -- the client concatenates
# prefix + payload with NO separator of its own
# (``rails.embedding_client.EmbeddingClient.embed_text``/``embed_audio``).
AUDIO_INSTRUCT_PREFIX = "Represent this utterance for intent retrieval: "
TEXT_INSTRUCT_PREFIX = "Represent this intent label for retrieval: "

# The P-EMB-1 surface reused verbatim (module docstring): 60 audio + 18
# canonical labels per arm.
ARM_AUDIO_N = RUN_A_AUDIO_N  # 60
ARM_LABEL_N = RUN_A_LABEL_N  # 18
ARM_TOTAL_N = ARM_AUDIO_N + ARM_LABEL_N  # 78, matches the registered per-arm count

# CITED from the consumed P-EMB-1 read -- docs/readiness/
# 2026-08-19-pemb1-verdict.md section 1: "argmax-cosine accuracy vs gold ...
# 3 / 60 = 0.0500" (mean pooling, no instruction, EMB-WEAK). Never re-flown
# by this probe; carried as a constant so the L3-vs-cited-mean-bare delta in
# analysis.pemb3l_read never requires a second embedding contact.
CITED_MEAN_BARE_ACCURACY = 0.0500


class Pemb3lFlightError(PembFlightError):
    """A P-EMB-3L arm input is malformed, a hard count/identity/legality
    invariant is violated, the ontology-miner import guard tripped, or the
    binding config's own sha256 drifted from its pinned value. A subclass of
    :class:`~.pemb_flight.PembFlightError` -- every sibling module's
    ``except PembFlightError`` clause (e.g. ``analysis.pemb_read.main``)
    catches this without modification."""


# ---------------------------------------------------------------------------
# Arm table.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Pemb3lArm:
    """One sweep arm's own binding facts. ``pooling_mode`` is a TAG for the
    flight agent that owns servers (module docstring: "tagged not
    managed") -- this dataclass performs no server I/O and asserts nothing
    about which session is actually live."""

    arm_id: str
    pooling_mode: str
    audio_prefix: str
    text_prefix: str


ARM_L1 = Pemb3lArm(arm_id=ARM_L1_ID, pooling_mode=POOLING_LAST, audio_prefix="", text_prefix="")
ARM_L2 = Pemb3lArm(
    arm_id=ARM_L2_ID, pooling_mode=POOLING_LAST, audio_prefix=AUDIO_INSTRUCT_PREFIX, text_prefix=TEXT_INSTRUCT_PREFIX
)
ARM_L3 = Pemb3lArm(
    arm_id=ARM_L3_ID, pooling_mode=POOLING_MEAN, audio_prefix=AUDIO_INSTRUCT_PREFIX, text_prefix=TEXT_INSTRUCT_PREFIX
)
ARMS: tuple[Pemb3lArm, ...] = (ARM_L1, ARM_L2, ARM_L3)
ARM_IDS: tuple[str, ...] = tuple(arm.arm_id for arm in ARMS)
ARMS_BY_ID: Mapping[str, Pemb3lArm] = MappingProxyType({arm.arm_id: arm for arm in ARMS})

EXPECTED_TOTAL_CONTACTS = ARM_TOTAL_N * len(ARMS)  # 234, matches the registered exposure row

BINDING_CONFIG_SCHEMA = "saea-pemb3l-binding-config-v1"

# Pinned verbatim (module docstring: "frozen in the binding config with
# sha256"). Recomputed by :func:`binding_config_sha256` and checked by
# :func:`assert_binding_config_sha256`; a future edit to ARMS, the two
# instruct-prefix constants above, or POOLING_LAST/POOLING_MEAN that changes
# this digest is refused fail-closed rather than silently flown.
BINDING_CONFIG_SHA256 = "fa698d31699314ecc94a046b8de4c664f7ea35ccab858f248d93b235d3ef8b15"


def arm_run_id(arm_id: str) -> str:
    """The ``run_id`` an arm's :class:`~.pemb_flight.PembRunSummary` and
    on-disk manifest carry -- ``"SAEA-PROBE-pemb3l-234/<arm>"`` (module
    docstring: places vectors under ``derived/embeddings/
    SAEA-PROBE-pemb3l-234/<arm>/`` via the UNMODIFIED parent writer)."""

    if arm_id not in ARMS_BY_ID:
        raise Pemb3lFlightError(f"arm_run_id: unknown arm_id {arm_id!r}, expected one of {ARM_IDS}")
    return f"{PROBE_ID}/{arm_id}"


def _binding_config_document() -> dict[str, object]:
    return {
        "schema": BINDING_CONFIG_SCHEMA,
        "arms": [
            {
                "arm_id": arm.arm_id,
                "pooling_mode": arm.pooling_mode,
                "audio_prefix": arm.audio_prefix,
                "text_prefix": arm.text_prefix,
            }
            for arm in ARMS
        ],
    }


def binding_config_sha256() -> str:
    """sha256 over the canonical (sorted-key, no-whitespace) JSON encoding
    of every arm's own ``(pooling_mode, audio_prefix, text_prefix)`` --
    recomputed fresh every call, never cached, so it always reflects the
    LIVE ``ARMS`` table rather than whatever was true when this module was
    first written."""

    canonical = json.dumps(_binding_config_document(), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def assert_binding_config_sha256() -> None:
    """Fail-closed drift guard (module docstring): raises
    :class:`Pemb3lFlightError` the moment the LIVE arm table's own digest
    disagrees with the pinned :data:`BINDING_CONFIG_SHA256` -- the two exact
    instruct-prefix strings, or either arm's pooling mode, can never
    silently change underneath a flight."""

    actual = binding_config_sha256()
    if actual != BINDING_CONFIG_SHA256:
        raise Pemb3lFlightError(
            f"P-EMB-3L binding config sha256 {actual!r} does not match the pinned "
            f"{BINDING_CONFIG_SHA256!r} -- the arm table (pooling modes / instruct prefixes) has "
            "drifted from the registered EXACT strings; refusing (fail-closed)"
        )


# ---------------------------------------------------------------------------
# The ontology-miner call guard (mirrors rails.probes.pemb_flight's own
# double-guard pattern exactly).
# ---------------------------------------------------------------------------


def _assert_this_module_never_calls_ontology_miner(source: str | None = None) -> None:
    text = source if source is not None else Path(__file__).read_text(encoding="utf-8")
    if _source_references_ontology_miner(text):
        raise Pemb3lFlightError(
            "rails.probes.pemb3l_flight source references load_slurp_ontology; the canonical "
            "scenario labels come ONLY from configs/probes/g0-binding/pslu-rosters-train-only.json "
            "(rails.probes.pslu_flight.load_pslu_rosters), reused verbatim from rails.probes.pemb_flight"
        )


# ---------------------------------------------------------------------------
# One arm's own flight.
# ---------------------------------------------------------------------------


def run_pemb3l_arm_flight(
    *,
    client: EmbeddingClientProtocol,
    arm: Pemb3lArm,
    samples: Sequence[SlurpSample],
    canonical_labels: Sequence[str],
    split_identity_hash: str,
    data_root: Path,
    expected_audio_n: int = ARM_AUDIO_N,
    expected_label_n: int = ARM_LABEL_N,
) -> PembRunSummary:
    """One sweep arm: the SAME P-EMB-1 surface (``expected_audio_n`` audio +
    ``expected_label_n`` canonical labels) embedded under ``arm``'s own
    pooling mode + instruct prefixes (module docstring). Zero generation,
    ``expected_audio_n + expected_label_n`` contacts (78 at the registered
    defaults). Reuses ``rails.probes.pemb_flight``'s own count/duplicate/
    split-identity/legality checks verbatim rather than re-deriving them."""

    assert_never_calls_ontology_miner()
    _assert_this_module_never_calls_ontology_miner()
    assert_binding_config_sha256()
    assert_run_a_split_identity_hash(split_identity_hash)

    if arm.arm_id not in ARMS_BY_ID or ARMS_BY_ID[arm.arm_id] != arm:
        raise Pemb3lFlightError(
            f"run_pemb3l_arm_flight: {arm!r} is not one of the pinned ARMS ({ARM_IDS}) -- refusing "
            "an arm that does not match this module's own frozen table"
        )

    if len(samples) != expected_audio_n:
        raise Pemb3lFlightError(
            f"{arm.arm_id}: requires exactly {expected_audio_n} audio sample(s), got {len(samples)}"
        )
    sample_ids = [sample.sample_id for sample in samples]
    if len(set(sample_ids)) != len(sample_ids):
        raise Pemb3lFlightError(f"{arm.arm_id}: duplicate sample_id in samples")

    labels = list(canonical_labels)
    if len(labels) != expected_label_n:
        raise Pemb3lFlightError(
            f"{arm.arm_id}: requires exactly {expected_label_n} canonical label(s), got {len(labels)}"
        )
    if len(set(labels)) != len(labels):
        raise Pemb3lFlightError(f"{arm.arm_id}: duplicate canonical label")
    for label in labels:
        if not isinstance(label, str) or not label or label != label.strip():
            raise Pemb3lFlightError(f"{arm.arm_id}: canonical label must be a bare, non-empty string, got {label!r}")

    client.verify_media_marker()

    audio_vectors = tuple(
        client.embed_audio(
            contact_id=sample.sample_id,
            audio_bytes=_read_audio_bytes(data_root, sample.media_relpath),
            prompt_prefix=arm.audio_prefix,
        )
        for sample in samples
    )
    text_vectors = tuple(
        client.embed_text(contact_id=label, text=label, prefix=arm.text_prefix) for label in labels
    )

    summary = PembRunSummary(run_id=arm_run_id(arm.arm_id), audio_vectors=audio_vectors, text_vectors=text_vectors)
    _validate_run_summary(summary, expected_audio_n=expected_audio_n, expected_text_n=expected_label_n)
    return summary


def run_pemb3l_sweep_flight(
    *,
    clients: Mapping[str, EmbeddingClientProtocol],
    samples: Sequence[SlurpSample],
    canonical_labels: Sequence[str],
    split_identity_hash: str,
    data_root: Path,
    expected_audio_n: int = ARM_AUDIO_N,
    expected_label_n: int = ARM_LABEL_N,
) -> tuple[PembRunSummary, ...]:
    """All three arms, one client PER ``arm_id`` (module docstring: L1/L2
    share one ``--pooling last`` session's client, L3 uses a separate
    ``--pooling mean`` session's client -- this function never opens a
    server itself and never assumes ``clients`` values are distinct
    objects). Returns the three summaries in :data:`ARMS` order and fails
    closed unless the sweep's combined contact count is exactly
    ``3 * (expected_audio_n + expected_label_n)`` (234 at the registered
    defaults, :data:`EXPECTED_TOTAL_CONTACTS`)."""

    assert_binding_config_sha256()
    missing = [arm_id for arm_id in ARM_IDS if arm_id not in clients]
    if missing:
        raise Pemb3lFlightError(f"run_pemb3l_sweep_flight: missing client(s) for arm(s) {missing}")

    summaries = tuple(
        run_pemb3l_arm_flight(
            client=clients[arm.arm_id],
            arm=arm,
            samples=samples,
            canonical_labels=canonical_labels,
            split_identity_hash=split_identity_hash,
            data_root=data_root,
            expected_audio_n=expected_audio_n,
            expected_label_n=expected_label_n,
        )
        for arm in ARMS
    )
    expected_total = 3 * (expected_audio_n + expected_label_n)
    total_contacts = sum(len(summary.audio_vectors) + len(summary.text_vectors) for summary in summaries)
    if total_contacts != expected_total:
        raise Pemb3lFlightError(
            f"run_pemb3l_sweep_flight: sweep produced {total_contacts} total contacts, expected "
            f"exactly {expected_total} (3 arms x {expected_audio_n + expected_label_n})"
        )
    return summaries


# ---------------------------------------------------------------------------
# Manifest persistence -- thin, arm-aware wrappers over rails.probes.
# pemb_flight's own writer/loader, reused UNMODIFIED (module docstring).
# ---------------------------------------------------------------------------


def write_pemb3l_arm_manifest(root: Path, summary: PembRunSummary) -> Path:
    """``write_embedding_manifest`` reused verbatim -- ``summary.run_id``
    (``arm_run_id(...)``) already places the manifest under
    ``derived/embeddings/SAEA-PROBE-pemb3l-234/<arm>/manifest.json``."""

    return write_embedding_manifest(root, summary)


def write_pemb3l_sweep_manifests(root: Path, summaries: Sequence[PembRunSummary]) -> tuple[Path, ...]:
    return tuple(write_pemb3l_arm_manifest(root, summary) for summary in summaries)


def load_pemb3l_arm_manifest(root: Path, arm_id: str) -> LoadedEmbeddingManifest:
    """``load_embedding_manifest`` reused verbatim, keyed by
    ``arm_run_id(arm_id)`` -- the sha256-verified re-load every sibling
    manifest reader gets for free."""

    return load_embedding_manifest(root, arm_run_id(arm_id))


__all__ = [
    "ARM_AUDIO_N",
    "ARM_IDS",
    "ARM_L1",
    "ARM_L1_ID",
    "ARM_L2",
    "ARM_L2_ID",
    "ARM_L3",
    "ARM_L3_ID",
    "ARM_LABEL_N",
    "ARM_TOTAL_N",
    "ARMS",
    "ARMS_BY_ID",
    "AUDIO_INSTRUCT_PREFIX",
    "BINDING_CONFIG_SCHEMA",
    "BINDING_CONFIG_SHA256",
    "CITED_MEAN_BARE_ACCURACY",
    "EXPECTED_RUN_A_SPLIT_IDENTITY_HASH",
    "EXPECTED_TOTAL_CONTACTS",
    "POOLING_LAST",
    "POOLING_MEAN",
    "PROBE_ID",
    "TEXT_INSTRUCT_PREFIX",
    "Pemb3lArm",
    "Pemb3lFlightError",
    "arm_run_id",
    "assert_binding_config_sha256",
    "binding_config_sha256",
    "load_pemb3l_arm_manifest",
    "run_pemb3l_arm_flight",
    "run_pemb3l_sweep_flight",
    "write_pemb3l_arm_manifest",
    "write_pemb3l_sweep_manifests",
]


# Executed at import time (mirrors rails.probes.pemb_flight's own
# module-bottom self-check): fails LOUD the moment this module is next
# imported if a future edit adds a live reference to the forbidden ontology
# miner, or drifts the binding config away from its pinned sha256.
assert_never_calls_ontology_miner()
_assert_this_module_never_calls_ontology_miner()
assert_binding_config_sha256()
