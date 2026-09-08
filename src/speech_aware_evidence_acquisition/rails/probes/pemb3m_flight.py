"""P-EMB-3M flight orchestration -- REGISTERED probe SAEA-PROBE-pemb3m-388
(``bounded-discovery-probe``): ``docs/readiness/
2026-08-20-pemb3m-preregistration-REGISTERED.md``. MACHINERY ONLY: this
module contains zero live model contact and is never itself pointed at a
real server/model -- every test drives ``rails.embedding_client.
MockEmbeddingClient`` and ``rails.local_encoder_client.MockLocalEncoderClient``.

Four arms over the SAME frozen P-EMB-1 surface (60 SLURP devel audio, split
identity :data:`EXPECTED_SPLIT_IDENTITY_HASH`, 18 canonical scenario labels;
argmax cosine; scoring-side gold -- registration section 2), each pointed at
a DIFFERENT dedicated embedder, bare content on both sides (no instruction
prefix -- "prompt/prefix strings (bare, per P-EMB-1 precedent)", the
prereg's own opening paragraph, in explicit contrast to P-EMB-3L's own
short-lived, refuted instruct-prefix experiment):

======  ==============================  ============  ====  ================================
arm     model (lock key)                query side    dim   client / kind
======  ==============================  ============  ====  ================================
M1      lco-embedding-omni-3b-gguf      60 audio       2048  ``rails.embedding_client.
        (PRIMARY)                                            EmbeddingClient``, ``--pooling
                                                               last``, mmproj, marker-pinned
M2      glap (CONTROL, audio-TYPE)      60 audio       1024  ``rails.local_encoder_client.
                                                               LocalTransformersEncoderClient``,
                                                               in-process
M3      clsp (CONTROL, speaking-STYLE)  60 audio        512  same client family as M2
M4      qwen3-embedding-0.6b-gguf       60 T0           1024  ``rails.embedding_client.
        (CASCADE)                       self-transcript        EmbeddingClient`` pointed at a
                                         (TEXT, not audio)     text-only server (``expected_dim
                                                                =1024, require_marker_
                                                                verification=False`` -- the
                                                                EXTENSION seam ``rails.
                                                                embedding_client`` added for
                                                                exactly this caller)
======  ==============================  ============  ====  ================================

Every arm also embeds the SAME 18 canonical scenario-label strings as its
own label side (bare text, ``embed_text``). Each arm is its own
:data:`ARM_TOTAL_N` = 78-contact flight; the full sweep is
:data:`PLANNED_TOTAL_EMBEDDING_CONTACTS` = 312, plus up to
:data:`CASCADE_T0_SUPPLEMENT_MAX_CONTACTS` = 66 contingency generation
contacts (pre-flight gate (c) fallback, never spent when the frozen 60's T0
self-transcripts are already found among the CONSUMED ``SAEA-PROBE-pkey2-338``
artifacts -- see :func:`run_cascade_source_check`) plus up to
:data:`GATE_CONTACTS_MAX` = 10 gate contacts (pooling-differ + control
sanity + M4 repeat-call determinism) -- 388 in the worst case, the exposure
row's own name.

Four pre-flight gates (registration section 3), each fail-closed and
receipt-logged, run BEFORE any scored contact:

(a) :func:`run_pooling_differ_gate` -- the pemb3l-verdict-mandated
    POOLING-DIFFER check: embed one identical audio file under two SEPARATE
    ``--pooling last`` / ``--pooling mean`` server sessions and byte-compare.
(b) :func:`run_control_import_feasibility_gates` -- GLAP/CLSP must import
    and produce one sanity embed with the shared venv AS-IS
    (``rails.local_encoder_client.run_import_feasibility_gate``, reused
    verbatim); a missing dependency reports DROPPED-DEPS and never blocks
    M1/M4; this module NEVER pip-installs anything.
(c) :func:`run_cascade_source_check` -- locate the frozen 60's T0
    self-transcripts among the CONSUMED ``SAEA-PROBE-pkey2-338`` artifacts
    (ledger row verified ``consumed = yes`` FIRST,
    :func:`assert_ledger_row_consumed`, before anything under the data root
    is opened); :func:`run_cascade_t0_supplement_flight` is the registered
    ``CASCADE-T0`` fallback, wired but never invoked when the source check
    reports ``COMPLETE``.
(d) :func:`run_encode_only_preflight_gate` -- the charter-mandated
    structural encode-only machine check (``rails.encode_only_check.
    run_encode_only_machine_check``), fail-closed; the flight refuses to
    take off on a red check.

Ceilings (registration section 5, fail-closed):
:func:`assert_within_registered_ceilings` refuses any plan/receipt claiming
more than :data:`CEILING_CALLS` = 440 calls, :data:`CEILING_AUDIO_SECONDS`
= 900 metered audio-seconds, or :data:`CEILING_GPU_HOURS` = 0.5 GPU-hours.
:func:`build_execution_plan` constructs and ``.validate()``s a
``contracts.ExecutionPlan`` for this probe (``execution_profile =
"bounded-discovery-probe"``, ``contracts.assert_execution_scope`` fires
transitively through ``.validate()``) -- ``rails.probes.pemb3l_flight``
itself carries NO in-module ``ExecutionPlan`` construction (that lives only
in its own archived launcher,
``docs/checks/speech-aware-evidence-acquisition/2026-08-20-pemb3l-flight/
launcher/launch_pemb3l_flight.py``); this module adds an explicit, directly
testable builder here instead, since no equivalent launcher exists yet for
this probe and the mission explicitly calls out this integration as part of
the machinery itself (a judgment call, recorded here for audit).

Arm-level idempotence (the pemb3l abort lesson --
``docs/readiness/2026-08-20-pemb3l-verdict.md`` never states this directly,
but the SAME abort-then-orphan-session failure mode ``ae85db1``'s own
sweep hit is what this guards against): :func:`run_pemb3m_sweep_flight`
checks :func:`is_arm_complete` (an already-written, sha256-verified
manifest under the data root) BEFORE invoking an arm's own runner callable
-- an already-complete arm's session is loaded from disk and its runner is
NEVER called a second time.

Binding config + sha256 (:func:`build_binding_config_document` /
:func:`binding_config_sha256` / :func:`assert_binding_config_sha256`):
covers the frozen split identity, the 18 labels' own count, the (empty,
bare) prefix strings, the pinned T0-transcript-registry artifact sha256,
and -- for every arm -- its model's own identity fields RESOLVED FROM THE
UMBRELLA LOCK AT CALL TIME (``resolve_model_binding``, never a hardcoded
hash in this module's own source: the umbrella lock's own ``glap``/``clsp``/
``lco-embedding-omni-3b-gguf`` entries are ``LOCAL_CANDIDATE``/
``UNRESOLVED_LOCAL_SOURCE`` and carry only an aggregate ``size_bytes``/
``files`` count, never a per-file sha256 -- this function passes through
WHATEVER the lock actually provides, never synthesizing a hash that is not
there; only ``qwen3-embedding-0.6b-gguf``'s own resolved HF source carries a
real per-file sha256). The resulting digest is still PINNED
(:data:`BINDING_CONFIG_SHA256`) and drift-checked fail-closed
(:func:`assert_binding_config_sha256`) exactly like ``rails.probes.
pemb3l_flight``'s own pattern -- the difference is that THIS digest also
commits to the umbrella lock's current content for these four model keys,
so a future lock edit that changes any of them is refused, not silently
absorbed.

Manifest persistence (:func:`write_pemb3m_arm_manifest` /
:func:`load_pemb3m_arm_manifest`, schema :data:`PEMB3M_MANIFEST_SCHEMA`):
a NEW, dim-generic writer/loader -- NOT a reuse of ``rails.probes.
pemb_flight.write_embedding_manifest``/``load_embedding_manifest``, because
those hardcode ``dims == rails.embedding_client.EMBEDDING_DIM`` (2048) at
both the per-entry AND the document level, which M2 (1024)/M3 (512)/M4
(1024) all violate. Entries are keyed by ``side`` (``query``/``label``/
``jitter``), never ``kind`` (``audio``/``text``) -- M4's OWN query side is
``kind="text"`` (T0 transcripts, never audio), so ``kind`` alone cannot
discriminate query-vs-label the way it could for the pemb1/pemb2/pemb3l
audio-vs-text runs; ``side`` is the uniform discriminator across all four
arms. This is a considered design delta from the "reuse
``pemb_flight``'s writer" precedent set by ``pemb3l_flight`` (recorded here
for audit -- pemb3l could reuse it unmodified because LCO's own dim matches
the shared 2048 constant exactly; three of pemb3m's four arms cannot).

The M4-only ``jitter`` side (0 or 2 entries, :func:`run_m4_repeat_call_gate`)
carries the registered "repeat-call determinism sample per server session"
(registration section 6, E-1 Mission C: qwen3-emb is NOT bit-exact across
identical GPU calls) -- persisted alongside M4's own query/label vectors so
``analysis.pemb3m_read`` can compute the declared cosine >= 0.9999 tolerance
and an argmax-stability check without a fifth manifest file.

Zero live model contact, engineering only: every test in this module's own
suite drives ``MockEmbeddingClient``/``MockLocalEncoderClient``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Callable, Mapping, Sequence

from ...contracts import ExecutionPlan, assert_execution_scope
from ..adapters.slurp import SlurpSample
from ..embedding_client import EMBEDDING_DIM as LCO_EMBEDDING_DIM
from ..embedding_client import EmbeddingClientProtocol, EmbeddingVector
from ..local_encoder_client import (
    CLSP_EMBEDDING_DIM,
    GLAP_EMBEDDING_DIM,
    ImportFeasibilityResult,
    LocalEncoderClientProtocol,
)
from .pemb_flight import (
    EXPECTED_RUN_A_SPLIT_IDENTITY_HASH as EXPECTED_SPLIT_IDENTITY_HASH,
)
from .pemb_flight import (
    PembFlightError,
    _npy_bytes,
    _npy_to_array,
    _read_audio_bytes,
    _safe_filename,
    assert_run_a_split_identity_hash as assert_split_identity_hash,
)
from .pkey_flight import T0_INSTRUCTION  # noqa: F401 -- re-exported for callers building CASCADE-T0 receipts
from .pkey_flight import TranscriptRecord, assemble_t0_messages, build_transcript_record
from .pslu_flight import _source_references_ontology_miner, assert_never_calls_ontology_miner

PROBE_ID = "SAEA-PROBE-pemb3m-388"

ARM_M1_ID = "m1-lco-primary"
ARM_M2_ID = "m2-glap-control"
ARM_M3_ID = "m3-clsp-control"
ARM_M4_ID = "m4-cascade"

ARM_QUERY_N = 60  # the frozen 60 SLURP devel samples (audio for M1-M3, T0 transcript for M4)
ARM_LABEL_N = 18  # the 18 canonical scenario labels, every arm
ARM_TOTAL_N = ARM_QUERY_N + ARM_LABEL_N  # 78, matches the registered per-arm count

QWEN3_EMB_EMBEDDING_DIM = 1024

PLANNED_TOTAL_EMBEDDING_CONTACTS = 4 * ARM_TOTAL_N  # 312
CASCADE_T0_SUPPLEMENT_MAX_CONTACTS = 66
GATE_CONTACTS_MAX = 10

CEILING_CALLS = 440
CEILING_AUDIO_SECONDS = 900
CEILING_GPU_HOURS = 0.5

DEFAULT_PLANNED_MODEL_CALLS = PLANNED_TOTAL_EMBEDDING_CONTACTS + CASCADE_T0_SUPPLEMENT_MAX_CONTACTS + GATE_CONTACTS_MAX  # 388
DEFAULT_PLANNED_GPU_HOURS = CEILING_GPU_HOURS
DEFAULT_PLANNED_SPEECH_AUDIO_SECONDS = CEILING_AUDIO_SECONDS

PEMB3M_MANIFEST_SCHEMA = "saea-pemb3m-embeddings-manifest-v1"

POOLING_DIFFER_GATE_CONTACT_ID = "pooling-differ-gate"


class Pemb3mFlightError(PembFlightError):
    """A P-EMB-3M arm input is malformed, a hard count/identity/legality
    invariant is violated, the ontology-miner import guard tripped, a
    registered ceiling was exceeded, or the binding config's own sha256
    drifted from its pinned value. A subclass of :class:`~.pemb_flight.
    PembFlightError` -- every sibling module's ``except PembFlightError``
    clause catches this without modification."""


# ---------------------------------------------------------------------------
# The ontology-miner call guard (mirrors rails.probes.pemb3l_flight's own
# double-guard pattern exactly).
# ---------------------------------------------------------------------------


def _assert_this_module_never_calls_ontology_miner(source: str | None = None) -> None:
    text = source if source is not None else Path(__file__).read_text(encoding="utf-8")
    if _source_references_ontology_miner(text):
        raise Pemb3mFlightError(
            "rails.probes.pemb3m_flight source references load_slurp_ontology; the canonical "
            "scenario labels come ONLY from configs/probes/g0-binding/pslu-rosters-train-only.json "
            "(rails.probes.pslu_flight.load_pslu_rosters), reused verbatim from rails.probes.pemb_flight"
        )


# ---------------------------------------------------------------------------
# Arm table.
# ---------------------------------------------------------------------------

KIND_LLAMACPP_SERVER = "llamacpp-server"
KIND_LLAMACPP_SERVER_TEXT_ONLY = "llamacpp-server-text-only"
KIND_IN_PROCESS_TRANSFORMERS = "in-process-transformers"


@dataclass(frozen=True)
class Pemb3mArm:
    arm_id: str
    model_lock_key: str
    embedding_dim: int
    uses_audio: bool
    kind: str


ARM_M1 = Pemb3mArm(
    arm_id=ARM_M1_ID,
    model_lock_key="lco-embedding-omni-3b-gguf",
    embedding_dim=LCO_EMBEDDING_DIM,
    uses_audio=True,
    kind=KIND_LLAMACPP_SERVER,
)
ARM_M2 = Pemb3mArm(
    arm_id=ARM_M2_ID,
    model_lock_key="glap",
    embedding_dim=GLAP_EMBEDDING_DIM,
    uses_audio=True,
    kind=KIND_IN_PROCESS_TRANSFORMERS,
)
ARM_M3 = Pemb3mArm(
    arm_id=ARM_M3_ID,
    model_lock_key="clsp",
    embedding_dim=CLSP_EMBEDDING_DIM,
    uses_audio=True,
    kind=KIND_IN_PROCESS_TRANSFORMERS,
)
ARM_M4 = Pemb3mArm(
    arm_id=ARM_M4_ID,
    model_lock_key="qwen3-embedding-0.6b-gguf",
    embedding_dim=QWEN3_EMB_EMBEDDING_DIM,
    uses_audio=False,
    kind=KIND_LLAMACPP_SERVER_TEXT_ONLY,
)
ARMS: tuple[Pemb3mArm, ...] = (ARM_M1, ARM_M2, ARM_M3, ARM_M4)
ARM_IDS: tuple[str, ...] = tuple(arm.arm_id for arm in ARMS)
ARMS_BY_ID: Mapping[str, Pemb3mArm] = MappingProxyType({arm.arm_id: arm for arm in ARMS})
CONTROL_ARM_IDS: tuple[str, ...] = (ARM_M2_ID, ARM_M3_ID)


def arm_run_id(arm_id: str) -> str:
    if arm_id not in ARMS_BY_ID:
        raise Pemb3mFlightError(f"arm_run_id: unknown arm_id {arm_id!r}, expected one of {ARM_IDS}")
    return f"{PROBE_ID}/{arm_id}"


# ---------------------------------------------------------------------------
# Binding config -- model identity resolved from the umbrella lock at call
# time (module docstring: "never a hardcoded hash in this module's own
# source"), never copied into code.
# ---------------------------------------------------------------------------

BINDING_CONFIG_SCHEMA = "saea-pemb3m-binding-config-v1"


def resolve_model_binding(lock: Mapping[str, object], name: str) -> dict[str, object]:
    """Every identity field the umbrella lock's own entry for ``name``
    carries, passed through VERBATIM -- never synthesized, never a
    hardcoded fallback. A ``LOCAL_CANDIDATE``/``UNRESOLVED_LOCAL_SOURCE``
    entry (glap/clsp/lco-embedding-omni-3b-gguf, per ``docs/readiness/
    2026-08-20-e1-local-embedder-identity.md`` Mission A) carries only an
    aggregate ``size_bytes``/``files`` count and NO per-file sha256;
    ``qwen3-embedding-0.6b-gguf``'s own resolved HF source carries a real
    per-file sha256 list. Both shapes are returned as-is."""

    from ...data.lock import AssetResolutionError, lock_entry

    try:
        entry = lock_entry(lock, name)
    except AssetResolutionError as error:
        raise Pemb3mFlightError(str(error)) from error
    source = entry.get("source") if isinstance(entry.get("source"), Mapping) else {}
    verification = entry.get("verification") if isinstance(entry.get("verification"), Mapping) else {}
    raw_files = source.get("files") if isinstance(source, Mapping) else None
    file_hashes = tuple(
        {"filename": item.get("filename"), "sha256": item.get("sha256")}
        for item in raw_files
        if isinstance(item, Mapping) and item.get("sha256")
    ) if isinstance(raw_files, list) else ()
    return {
        "name": entry.get("name"),
        "local_subdir": entry.get("local_subdir"),
        "source_kind": source.get("kind") if isinstance(source, Mapping) else None,
        "source_id": source.get("id") if isinstance(source, Mapping) else None,
        "revision": entry.get("revision"),
        "lifecycle": entry.get("lifecycle"),
        "size_bytes": entry.get("size_bytes", verification.get("size_bytes") if isinstance(verification, Mapping) else None),
        "files_count": entry.get("files", verification.get("files") if isinstance(verification, Mapping) else None),
        "file_hashes": file_hashes,
    }


def build_binding_config_document(lock: Mapping[str, object]) -> dict[str, object]:
    return {
        "schema": BINDING_CONFIG_SCHEMA,
        "split_identity_hash": EXPECTED_SPLIT_IDENTITY_HASH,
        "query_count": ARM_QUERY_N,
        "label_count": ARM_LABEL_N,
        "prefixes": {"audio_prefix": "", "text_prefix": ""},
        "t0_transcript_registry_sha256": PKEY2_338_TRANSCRIPT_REGISTRY_SHA256,
        "arms": [
            {
                "arm_id": arm.arm_id,
                "model_lock_key": arm.model_lock_key,
                "embedding_dim": arm.embedding_dim,
                "uses_audio": arm.uses_audio,
                "kind": arm.kind,
                "model_binding": resolve_model_binding(lock, arm.model_lock_key),
            }
            for arm in ARMS
        ],
    }


def binding_config_sha256(lock: Mapping[str, object]) -> str:
    canonical = json.dumps(build_binding_config_document(lock), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


# HISTORICAL. Pinned against the umbrella lock's own content for these four
# keys as it stood when this module was written and when the 2026-08-20
# P-EMB-3M flight sealed (docs/checks/speech-aware-evidence-acquisition/
# 2026-08-20-pemb3m-flight/{flight-receipt,config-values}.json both carry
# this exact value under "binding_config_sha256"). Kept ONLY so those
# sealed receipts stay readable against a named constant -- no live code
# checks against this value any more; see BINDING_CONFIG_SHA256 below for
# the constant assert_binding_config_sha256 actually enforces.
BINDING_CONFIG_SHA256_AT_FLIGHT = "307e6828b0a61ef445a5db20bb0ecf35c10e8b008b625b0fa66a9b5e125a6d3a"

# Re-pinned 2026-09-08 against umbrella commit faebc8f (owner Decision 11-D:
# "commit the pending umbrella changes AND re-pin the study's P-EMB
# hashes", chosen over reverting the lock). The umbrella lock's own entry
# for one of these four keys -- lco-embedding-omni-3b-gguf -- changed in
# that commit: from an unresolved local candidate (source.kind
# "observed-local", id UNRESOLVED_LOCAL_SOURCE, revision
# UNRESOLVED_LOCAL_REVISION, lifecycle LOCAL_CANDIDATE, aggregate-only
# verification) to a resolved HF source (marksverdhei/LCO-Embedding-Omni-
# 3B-GGUF, revision af8a36fbb6e7629c9dbcb218478c6b1477b36e09, lifecycle
# AUXILIARY, profile speech-aware-tools, 3 verified files with real
# per-file sha256). glap, clsp and qwen3-embedding-0.6b-gguf are
# byte-identical across the two lock commits -- this is NOT incidental
# lock growth riding along; it is the bound model's own identity becoming
# resolved, so the digest change is deliberate reviewed content, never
# silently absorbed drift.
#
# The lock's PRE-faebc8f entry for lco-embedding-omni-3b-gguf carried no
# per-file sha256 at all (only an aggregate size_bytes/files count), so
# the lock's own metadata cannot prove the model bytes are identical
# across the two commits -- only that the aggregate size moved by 1,462
# bytes (6238572624 -> 6238571162) as the file count dropped 5 -> 3. (For
# context, not a substitute for that proof: the sealed 2026-08-20
# P-EMB-3M/P-EMB-4R flight receipts independently hashed the local
# LCO-Embedding-Omni-3B-Q8_0.gguf and its mmproj file at flight time --
# before the lock carried any per-file hash for this model -- and both
# measured hashes equal the two GGUF hashes the resolved lock entry now
# pins; the entry's third file, README.md, was never independently hashed
# by either flight.) Any future reuse of this embedder must re-verify
# against the resolved lock entry rather than lean on this note.
BINDING_CONFIG_SHA256 = "f41aae5d356b2c43d4e602cca168ab60a61142e9423949d242dee3b61e0bdfa4"


def assert_binding_config_sha256(lock: Mapping[str, object]) -> None:
    actual = binding_config_sha256(lock)
    if actual != BINDING_CONFIG_SHA256:
        raise Pemb3mFlightError(
            f"P-EMB-3M binding config sha256 {actual!r} does not match the pinned "
            f"{BINDING_CONFIG_SHA256!r} -- the arm table, prefix strings, T0 registry pin, or the "
            "umbrella lock's own content for one of the four model keys has drifted; refusing "
            "(fail-closed)"
        )


# ---------------------------------------------------------------------------
# Ceilings (registration section 5).
# ---------------------------------------------------------------------------


def assert_within_registered_ceilings(*, calls: int, audio_seconds: float, gpu_hours: float) -> None:
    if calls > CEILING_CALLS:
        raise Pemb3mFlightError(f"{calls} calls exceeds the registered ceiling of {CEILING_CALLS}")
    if audio_seconds > CEILING_AUDIO_SECONDS:
        raise Pemb3mFlightError(
            f"{audio_seconds} metered audio-second(s) exceeds the registered ceiling of {CEILING_AUDIO_SECONDS}"
        )
    if gpu_hours > CEILING_GPU_HOURS:
        raise Pemb3mFlightError(f"{gpu_hours} GPU-hour(s) exceeds the registered ceiling of {CEILING_GPU_HOURS}")


# ---------------------------------------------------------------------------
# contracts.ExecutionPlan integration.
# ---------------------------------------------------------------------------


def build_execution_plan(
    *,
    lock: Mapping[str, object],
    attempt_id: str | None = None,
    planned_model_calls: int = DEFAULT_PLANNED_MODEL_CALLS,
    planned_gpu_hours: float = DEFAULT_PLANNED_GPU_HOURS,
    planned_speech_audio_seconds: int = DEFAULT_PLANNED_SPEECH_AUDIO_SECONDS,
    carrier_lock_key: str = "slurp",
) -> ExecutionPlan:
    """Constructs and ``.validate()``s the ``contracts.ExecutionPlan`` for
    this probe. ``contracts.assert_execution_scope`` is called BOTH
    directly here (fail-fast, matching the mission's explicit naming of
    both symbols) AND again transitively through ``ExecutionPlan.
    validate()`` -- the same belt-and-suspenders double-check this client's
    own :meth:`~rails.embedding_client.EmbeddingClient.verify_media_marker`
    uses for the media marker. ``protocol_hash`` is
    :func:`binding_config_sha256` (an existing 64-hex sha256, never a
    second, independently-computed digest)."""

    execution_profile = assert_execution_scope("bounded-discovery-probe")
    assert_within_registered_ceilings(
        calls=planned_model_calls, audio_seconds=planned_speech_audio_seconds, gpu_hours=planned_gpu_hours
    )
    plan = ExecutionPlan(
        run_id=PROBE_ID,
        execution_profile=execution_profile,
        carrier_lock_key=carrier_lock_key,
        split_role="discovery",
        split_identity_hash=EXPECTED_SPLIT_IDENTITY_HASH,
        planned_model_calls=planned_model_calls,
        planned_gpu_hours=planned_gpu_hours,
        planned_speech_audio_seconds=planned_speech_audio_seconds,
        protocol_hash=binding_config_sha256(lock),
        attempt_id=attempt_id,
    )
    return plan.validate()


# ---------------------------------------------------------------------------
# Pre-flight gate (a) -- POOLING-DIFFER (the pemb3l-verdict carry-forward).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PoolingDifferGateResult:
    pooling_override_present: bool
    last_vector: EmbeddingVector
    mean_vector: EmbeddingVector


def run_pooling_differ_gate(
    *,
    last_client: EmbeddingClientProtocol,
    mean_client: EmbeddingClientProtocol,
    audio_bytes: bytes,
    contact_id: str = POOLING_DIFFER_GATE_CONTACT_ID,
) -> PoolingDifferGateResult:
    """``docs/readiness/2026-08-20-pemb3l-verdict.md`` section 6 item 1: embed
    the SAME audio under two SEPARATE server sessions (``--pooling last`` /
    ``--pooling mean``) and byte-compare. 2 contacts, never counted against
    :data:`PLANNED_TOTAL_EMBEDDING_CONTACTS` (they are gate contacts, module
    docstring)."""

    last_client.verify_media_marker()
    mean_client.verify_media_marker()
    last_vector = last_client.embed_audio(contact_id=contact_id, audio_bytes=audio_bytes)
    mean_vector = mean_client.embed_audio(contact_id=contact_id, audio_bytes=audio_bytes)
    if last_vector.dims != mean_vector.dims:
        raise Pemb3mFlightError(
            f"pooling-differ gate: last-pooled dim {last_vector.dims} != mean-pooled dim "
            f"{mean_vector.dims} -- cannot compare vectors of different dimensionality"
        )
    pooling_override_present = last_vector.values == mean_vector.values
    return PoolingDifferGateResult(
        pooling_override_present=pooling_override_present, last_vector=last_vector, mean_vector=mean_vector
    )


# ---------------------------------------------------------------------------
# Pre-flight gate (b) -- GLAP/CLSP import feasibility.
# ---------------------------------------------------------------------------


def run_control_import_feasibility_gates(
    *, loaders: Mapping[str, tuple[str, Callable[[], LocalEncoderClientProtocol]]]
) -> dict[str, ImportFeasibilityResult]:
    """``loaders``: ``arm_id -> (model_id, loader_callable)`` for
    :data:`CONTROL_ARM_IDS`. Delegates to ``rails.local_encoder_client.
    run_import_feasibility_gate`` verbatim -- a DROPPED-DEPS result never
    raises here (registration: "a dropped control never blocks M1/M4") and
    this function never pip-installs anything."""

    from ..local_encoder_client import run_import_feasibility_gate

    unknown = set(loaders) - set(CONTROL_ARM_IDS)
    if unknown:
        raise Pemb3mFlightError(f"run_control_import_feasibility_gates: unknown arm id(s) {sorted(unknown)}")
    return {
        arm_id: run_import_feasibility_gate(arm_id=arm_id, model_id=model_id, loader=loader)
        for arm_id, (model_id, loader) in loaders.items()
    }


# ---------------------------------------------------------------------------
# Pre-flight gate (c) -- CASCADE source check + CASCADE-T0 supplement.
# ---------------------------------------------------------------------------

PKEY2_338_RUN_EXPERIMENT_ID = "SAEA-PROBE-pkey2-338"
PKEY2_338_ATTEMPT_ID = "attempt-20260819T111032Z-3109e8"
PKEY2_338_TRANSCRIPT_REGISTRY_RELPATH = (
    f"runs/{PKEY2_338_RUN_EXPERIMENT_ID}/{PKEY2_338_ATTEMPT_ID}/transcript-registry.json"
)
# Verified live against the CONSUMED artifact under $SPEECHRL_DATA_DIR
# during this module's own build mission (read-only; never touched): 60/60
# entries, exact match against the frozen 60's own sample_id set
# (configs/probes/g0-binding/pslu-sample-devel-n60.json,
# split_identity_hash fc9de436...5ee5).
PKEY2_338_TRANSCRIPT_REGISTRY_SHA256 = "f8f6426aeb0eb84c33ad58b603cb36b8f420c3063149b6cd11a0b210d8774959"

# The ledger's own column order (docs/exposure-ledger.md header row): date /
# run-experiment-id / execution profile / scope / model-tool / carrier+split
# / split role / split identity hash / consumed / calls / audio-seconds /
# gpu-hours / inherited exposure / artifacts / notes -- "consumed" is column
# index 8 (0-based) after splitting a row on "|" and dropping the empty
# leading/trailing cells the outer pipes produce.
LEDGER_CONSUMED_COLUMN_INDEX = 8


def assert_ledger_row_consumed(ledger_text: str, *, run_experiment_id: str = PKEY2_338_RUN_EXPERIMENT_ID) -> None:
    """Fail-closed: locate the UNIQUE ledger row naming
    ``run_experiment_id`` and check its own ``consumed`` column reads
    exactly ``"yes"`` -- refuses if the row is missing, ambiguous
    (more than one match), too short to carry a consumed column, or
    ``consumed != "yes"``. Text-parsed against the markdown table (this
    repository's own ledger format has no literal ``|`` inside a cell, by
    convention -- every existing row already relies on that)."""

    anchor = f"| {run_experiment_id} |"
    matches = [line for line in ledger_text.splitlines() if anchor in line]
    if not matches:
        raise Pemb3mFlightError(f"exposure ledger carries no row for {run_experiment_id!r}")
    if len(matches) > 1:
        raise Pemb3mFlightError(
            f"exposure ledger carries {len(matches)} row(s) matching anchor {anchor!r}, expected exactly one"
        )
    cells = [cell.strip() for cell in matches[0].strip().strip("|").split("|")]
    if len(cells) <= LEDGER_CONSUMED_COLUMN_INDEX:
        raise Pemb3mFlightError(
            f"exposure ledger row for {run_experiment_id!r} has {len(cells)} column(s), fewer than "
            f"the {LEDGER_CONSUMED_COLUMN_INDEX + 1} required to read its consumed column"
        )
    consumed_cell = cells[LEDGER_CONSUMED_COLUMN_INDEX]
    if consumed_cell != "yes":
        raise Pemb3mFlightError(
            f"exposure ledger row for {run_experiment_id!r} carries consumed={consumed_cell!r}, expected "
            "'yes' -- the cascade source check refuses to read from an unconsumed artifact"
        )


CASCADE_SOURCE_STATUS_COMPLETE = "COMPLETE"
CASCADE_SOURCE_STATUS_PARTIAL = "PARTIAL"
CASCADE_SOURCE_STATUS_ABSENT = "ABSENT"


@dataclass(frozen=True)
class CascadeSourceCheckResult:
    status: str  # COMPLETE | PARTIAL | ABSENT
    registry_path: Path | None
    registry_sha256: str | None
    transcripts: Mapping[str, TranscriptRecord]
    supplement_required: bool


def run_cascade_source_check(
    *,
    data_root: Path,
    ledger_text: str,
    expected_sample_ids: frozenset[str],
    expected_registry_sha256: str | None = PKEY2_338_TRANSCRIPT_REGISTRY_SHA256,
) -> CascadeSourceCheckResult:
    """Pre-flight gate (c): verify the ledger row is ``consumed = yes``
    BEFORE opening anything (module docstring/mission instruction), then
    locate and hash-pin the frozen 60's T0 self-transcripts among the
    CONSUMED ``SAEA-PROBE-pkey2-338`` artifacts. ZERO model contact --
    this function only reads local files. ``expected_registry_sha256``
    defaults to the module's own pinned :data:`PKEY2_338_TRANSCRIPT_
    REGISTRY_SHA256` (real-flight fail-closed drift check, unchanged for
    every real caller); pass ``None`` to skip the pin check entirely -- the
    seam this module's own test suite uses to exercise the COMPLETE/PARTIAL
    branches against a synthetic fixture registry, which can never share
    the real consumed artifact's exact bytes."""

    assert_ledger_row_consumed(ledger_text)
    path = Path(data_root) / PKEY2_338_TRANSCRIPT_REGISTRY_RELPATH
    if not path.is_file():
        return CascadeSourceCheckResult(
            status=CASCADE_SOURCE_STATUS_ABSENT,
            registry_path=None,
            registry_sha256=None,
            transcripts=MappingProxyType({}),
            supplement_required=True,
        )
    data_bytes = path.read_bytes()
    actual_sha256 = hashlib.sha256(data_bytes).hexdigest()
    if expected_registry_sha256 is not None and actual_sha256 != expected_registry_sha256:
        raise Pemb3mFlightError(
            f"T0 transcript registry at {path} has sha256 {actual_sha256}, expected the pinned "
            f"{expected_registry_sha256} -- refusing a drifted consumed artifact"
        )
    try:
        raw = json.loads(data_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Pemb3mFlightError(f"{path}: cannot parse T0 transcript registry: {error}") from error
    if not isinstance(raw, Mapping):
        raise Pemb3mFlightError(f"{path}: T0 transcript registry must be a JSON object")

    transcripts: dict[str, TranscriptRecord] = {}
    for sample_id, entry in raw.items():
        if not isinstance(entry, Mapping):
            raise Pemb3mFlightError(f"{path}: malformed T0 transcript entry for {sample_id!r}")
        text = entry.get("text")
        expected_entry_sha256 = entry.get("sha256")
        if not isinstance(text, str) or not isinstance(expected_entry_sha256, str):
            raise Pemb3mFlightError(f"{path}: T0 transcript entry for {sample_id!r} missing text/sha256")
        record = build_transcript_record(str(sample_id), text)
        if record.sha256 != expected_entry_sha256:
            raise Pemb3mFlightError(f"{path}: T0 transcript sha256 mismatch for {sample_id!r}")
        transcripts[str(sample_id)] = record

    present_ids = frozenset(transcripts.keys())
    if present_ids == expected_sample_ids:
        status = CASCADE_SOURCE_STATUS_COMPLETE
    elif present_ids & expected_sample_ids:
        status = CASCADE_SOURCE_STATUS_PARTIAL
    else:
        status = CASCADE_SOURCE_STATUS_ABSENT
    return CascadeSourceCheckResult(
        status=status,
        registry_path=path,
        registry_sha256=actual_sha256,
        transcripts=MappingProxyType(transcripts),
        supplement_required=(status != CASCADE_SOURCE_STATUS_COMPLETE),
    )


def run_cascade_t0_supplement_flight(
    *,
    core_client,
    samples: Sequence[SlurpSample],
    decoding_params: Mapping[str, object] | None = None,
    max_contacts: int = CASCADE_T0_SUPPLEMENT_MAX_CONTACTS,
) -> dict[str, TranscriptRecord]:
    """The registered ``CASCADE-T0`` supplement (registration section 3
    item 3): ``<=66`` generation contacts on the frozen core, reusing
    ``rails.probes.pkey_flight``'s own T0 construction VERBATIM
    (:func:`~.pkey_flight.assemble_t0_messages` / :data:`~.pkey_flight.
    T0_INSTRUCTION` / :func:`~.pkey_flight.build_transcript_record`, never
    re-derived here). Wired but NEVER invoked by this module's own build
    mission (zero real model/server contacts) -- exercised only via a
    duck-typed ``core_client`` double in this module's own test suite.
    ``core_client`` is duck-typed against ``rails.core_client.CoreClient``
    (module docstring: never imported/annotated directly, mirroring ``rails.
    probes.pslu_flight.run_pslu_flight``'s own ``core_client`` parameter --
    the SAME reason: this keeps this module's own source free of importing
    the generation-capable client, which ``rails.encode_only_check``'s
    import guard is scoped to actually forbid)."""

    if len(samples) > max_contacts:
        raise Pemb3mFlightError(
            f"CASCADE-T0 supplement: {len(samples)} sample(s) exceeds the registered ceiling of "
            f"{max_contacts} generation contacts"
        )
    if not samples:
        raise Pemb3mFlightError("CASCADE-T0 supplement requires at least one sample")
    sample_ids = [sample.sample_id for sample in samples]
    if len(set(sample_ids)) != len(sample_ids):
        raise Pemb3mFlightError("CASCADE-T0 supplement: duplicate sample_id in samples")

    registry: dict[str, TranscriptRecord] = {}
    for sample in samples:
        messages = assemble_t0_messages(sample)
        response_text = core_client.complete(messages, decoding_params=decoding_params)
        registry[sample.sample_id] = build_transcript_record(sample.sample_id, response_text)
    return registry


# ---------------------------------------------------------------------------
# Pre-flight gate (d) -- encode-only structural machine check.
# ---------------------------------------------------------------------------


def run_encode_only_preflight_gate():
    """Delegates to ``rails.encode_only_check.run_encode_only_machine_check``
    verbatim (module docstring: "the flight refuses to take off on a red
    check"). Fail-closed: raises ``rails.encode_only_check.
    EncodeOnlyCheckError`` on any violation, never a soft flag."""

    from ..encode_only_check import run_encode_only_machine_check

    return run_encode_only_machine_check()


# ---------------------------------------------------------------------------
# M4 repeat-call determinism gate (E-1 Mission C jitter tolerance).
# ---------------------------------------------------------------------------


def run_m4_repeat_call_gate(
    *,
    client: EmbeddingClientProtocol,
    text: str,
    contact_id_a: str = "m4-jitter-a",
    contact_id_b: str = "m4-jitter-b",
) -> tuple[EmbeddingVector, EmbeddingVector]:
    """Embeds the SAME ``text`` twice against the SAME M4 (qwen3-emb)
    session -- "a repeat-call determinism sample per server session is
    recorded in the flight receipt" (registration section 6). 2 contacts.
    Cosine/argmax-stability evaluation against the declared >= 0.9999
    tolerance is ``analysis.pemb3m_read``'s own job, not this gate's --
    this function only PRODUCES the pair."""

    client.verify_media_marker()
    vector_a = client.embed_text(contact_id=contact_id_a, text=text)
    vector_b = client.embed_text(contact_id=contact_id_b, text=text)
    return vector_a, vector_b


# ---------------------------------------------------------------------------
# Query/label validation shared by every arm flight.
# ---------------------------------------------------------------------------


def _validate_query_samples(samples: Sequence[SlurpSample], *, expected_n: int = ARM_QUERY_N) -> None:
    if len(samples) != expected_n:
        raise Pemb3mFlightError(f"requires exactly {expected_n} query sample(s), got {len(samples)}")
    sample_ids = [sample.sample_id for sample in samples]
    if len(set(sample_ids)) != len(sample_ids):
        raise Pemb3mFlightError("duplicate sample_id in samples")


def _validate_canonical_labels(labels: Sequence[str], *, expected_n: int = ARM_LABEL_N) -> tuple[str, ...]:
    resolved = list(labels)
    if len(resolved) != expected_n:
        raise Pemb3mFlightError(f"requires exactly {expected_n} canonical label(s), got {len(resolved)}")
    if len(set(resolved)) != len(resolved):
        raise Pemb3mFlightError("duplicate canonical label")
    for label in resolved:
        if not isinstance(label, str) or not label or label != label.strip():
            raise Pemb3mFlightError(f"canonical label must be a bare, non-empty string, got {label!r}")
    return tuple(resolved)


# ---------------------------------------------------------------------------
# Arm summary + generic result validation.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Pemb3mArmSummary:
    run_id: str
    arm_id: str
    embedding_dim: int
    query_vectors: tuple[EmbeddingVector, ...]
    label_vectors: tuple[EmbeddingVector, ...]
    jitter_vectors: tuple[EmbeddingVector, ...] = ()


def _validate_arm_summary(
    summary: Pemb3mArmSummary, *, expected_query_n: int = ARM_QUERY_N, expected_label_n: int = ARM_LABEL_N
) -> None:
    if len(summary.query_vectors) != expected_query_n:
        raise Pemb3mFlightError(
            f"{summary.run_id}: {len(summary.query_vectors)} query vector(s), expected exactly {expected_query_n}"
        )
    if len(summary.label_vectors) != expected_label_n:
        raise Pemb3mFlightError(
            f"{summary.run_id}: {len(summary.label_vectors)} label vector(s), expected exactly {expected_label_n}"
        )
    if summary.jitter_vectors and len(summary.jitter_vectors) != 2:
        raise Pemb3mFlightError(
            f"{summary.run_id}: {len(summary.jitter_vectors)} jitter vector(s), expected exactly 0 or 2"
        )
    for side, vectors in (
        ("query", summary.query_vectors),
        ("label", summary.label_vectors),
        ("jitter", summary.jitter_vectors),
    ):
        ids = [vector.contact_id for vector in vectors]
        if len(set(ids)) != len(ids):
            raise Pemb3mFlightError(f"{summary.run_id}: duplicate {side} contact_id in results")
        for vector in vectors:
            if vector.dims != summary.embedding_dim:
                raise Pemb3mFlightError(
                    f"{summary.run_id}: {side} vector for {vector.contact_id!r} has dim {vector.dims} "
                    f"!= arm dim {summary.embedding_dim}"
                )


# ---------------------------------------------------------------------------
# M1 -- LCO primary (llama.cpp server, EmbeddingClientProtocol).
# ---------------------------------------------------------------------------


def run_m1_arm_flight(
    *,
    client: EmbeddingClientProtocol,
    samples: Sequence[SlurpSample],
    canonical_labels: Sequence[str],
    split_identity_hash: str,
    data_root: Path,
    expected_query_n: int = ARM_QUERY_N,
    expected_label_n: int = ARM_LABEL_N,
) -> Pemb3mArmSummary:
    assert_never_calls_ontology_miner()
    _assert_this_module_never_calls_ontology_miner()
    assert_split_identity_hash(split_identity_hash)
    _validate_query_samples(samples, expected_n=expected_query_n)
    labels = _validate_canonical_labels(canonical_labels, expected_n=expected_label_n)

    client.verify_media_marker()
    query_vectors = tuple(
        client.embed_audio(contact_id=sample.sample_id, audio_bytes=_read_audio_bytes(data_root, sample.media_relpath))
        for sample in samples
    )
    label_vectors = tuple(client.embed_text(contact_id=label, text=label) for label in labels)

    summary = Pemb3mArmSummary(
        run_id=arm_run_id(ARM_M1_ID),
        arm_id=ARM_M1_ID,
        embedding_dim=ARM_M1.embedding_dim,
        query_vectors=query_vectors,
        label_vectors=label_vectors,
    )
    _validate_arm_summary(summary, expected_query_n=expected_query_n, expected_label_n=expected_label_n)
    return summary


# ---------------------------------------------------------------------------
# M2/M3 -- GLAP/CLSP controls (in-process, LocalEncoderClientProtocol).
# ---------------------------------------------------------------------------


def run_local_encoder_arm_flight(
    *,
    arm_id: str,
    client: LocalEncoderClientProtocol,
    samples: Sequence[SlurpSample],
    canonical_labels: Sequence[str],
    split_identity_hash: str,
    data_root: Path,
    expected_query_n: int = ARM_QUERY_N,
    expected_label_n: int = ARM_LABEL_N,
) -> Pemb3mArmSummary:
    if arm_id not in CONTROL_ARM_IDS:
        raise Pemb3mFlightError(f"run_local_encoder_arm_flight: arm_id must be one of {CONTROL_ARM_IDS}, got {arm_id!r}")
    assert_never_calls_ontology_miner()
    _assert_this_module_never_calls_ontology_miner()
    assert_split_identity_hash(split_identity_hash)
    _validate_query_samples(samples, expected_n=expected_query_n)
    labels = _validate_canonical_labels(canonical_labels, expected_n=expected_label_n)

    arm = ARMS_BY_ID[arm_id]
    query_vectors = tuple(
        client.embed_audio(contact_id=sample.sample_id, audio_bytes=_read_audio_bytes(data_root, sample.media_relpath))
        for sample in samples
    )
    label_vectors = tuple(client.embed_text(contact_id=label, text=label) for label in labels)

    summary = Pemb3mArmSummary(
        run_id=arm_run_id(arm_id),
        arm_id=arm_id,
        embedding_dim=arm.embedding_dim,
        query_vectors=query_vectors,
        label_vectors=label_vectors,
    )
    _validate_arm_summary(summary, expected_query_n=expected_query_n, expected_label_n=expected_label_n)
    return summary


# ---------------------------------------------------------------------------
# M4 -- CASCADE (text-text, EmbeddingClientProtocol pointed at qwen3-emb).
# ---------------------------------------------------------------------------


def run_m4_arm_flight(
    *,
    client: EmbeddingClientProtocol,
    transcript_registry: Mapping[str, TranscriptRecord],
    canonical_labels: Sequence[str],
    split_identity_hash: str,
    jitter_vectors: tuple[EmbeddingVector, EmbeddingVector] | tuple[()] = (),
    expected_query_n: int = ARM_QUERY_N,
    expected_label_n: int = ARM_LABEL_N,
) -> Pemb3mArmSummary:
    assert_never_calls_ontology_miner()
    _assert_this_module_never_calls_ontology_miner()
    assert_split_identity_hash(split_identity_hash)
    if len(transcript_registry) != expected_query_n:
        raise Pemb3mFlightError(
            f"M4 requires exactly {expected_query_n} T0 transcript(s), got {len(transcript_registry)}"
        )
    labels = _validate_canonical_labels(canonical_labels, expected_n=expected_label_n)

    client.verify_media_marker()
    query_vectors = tuple(
        client.embed_text(contact_id=sample_id, text=transcript_registry[sample_id].text)
        for sample_id in sorted(transcript_registry)
    )
    label_vectors = tuple(client.embed_text(contact_id=label, text=label) for label in labels)

    summary = Pemb3mArmSummary(
        run_id=arm_run_id(ARM_M4_ID),
        arm_id=ARM_M4_ID,
        embedding_dim=ARM_M4.embedding_dim,
        query_vectors=query_vectors,
        label_vectors=label_vectors,
        jitter_vectors=tuple(jitter_vectors),
    )
    _validate_arm_summary(summary, expected_query_n=expected_query_n, expected_label_n=expected_label_n)
    return summary


# ---------------------------------------------------------------------------
# Manifest persistence -- dim-generic, side-keyed (module docstring: NOT a
# reuse of rails.probes.pemb_flight's own writer/loader).
# ---------------------------------------------------------------------------


def _arm_manifest_dir(root: Path, arm_id: str) -> Path:
    return Path(root) / "derived" / "embeddings" / arm_run_id(arm_id)


def is_arm_complete(root: Path, arm_id: str) -> bool:
    """True iff a manifest ALREADY EXISTS for ``arm_id`` under ``root`` --
    the arm-level idempotence check (module docstring: "a completed arm is
    carried, its session never respawned"). Presence-only (cheap, no
    sha256 verification here -- :func:`load_pemb3m_arm_manifest` performs
    the full verified reload whenever an arm's vectors are actually
    needed)."""

    return (_arm_manifest_dir(root, arm_id) / "manifest.json").is_file()


def write_pemb3m_arm_manifest(root: Path, summary: Pemb3mArmSummary) -> Path:
    from ...e0.artifacts import write_json_artifact

    out_dir = _arm_manifest_dir(root, summary.arm_id)
    entries: list[dict[str, object]] = []
    seen_safe: dict[tuple[str, str], str] = {}
    for side, vectors in (
        ("query", summary.query_vectors),
        ("label", summary.label_vectors),
        ("jitter", summary.jitter_vectors),
    ):
        for vector in vectors:
            safe_id = _safe_filename(vector.contact_id)
            key = (side, safe_id)
            if key in seen_safe and seen_safe[key] != vector.contact_id:
                raise Pemb3mFlightError(
                    f"{summary.run_id}: {side} contact ids {seen_safe[key]!r} and {vector.contact_id!r} "
                    f"both sanitize to the on-disk filename {safe_id!r} -- refusing a filename collision"
                )
            seen_safe[key] = vector.contact_id
            relpath = f"derived/embeddings/{summary.run_id}/{side}/{safe_id}.npy"
            path = Path(root) / relpath
            path.parent.mkdir(parents=True, exist_ok=True)
            data = _npy_bytes(vector.values)
            path.write_bytes(data)
            entries.append(
                {
                    "contact_id": vector.contact_id,
                    "side": side,
                    "relpath": relpath,
                    "dims": len(vector.values),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            )
    entries.sort(key=lambda entry: (entry["side"], entry["contact_id"]))
    document = {
        "schema": PEMB3M_MANIFEST_SCHEMA,
        "run_id": summary.run_id,
        "arm_id": summary.arm_id,
        "dims": summary.embedding_dim,
        "query_count": len(summary.query_vectors),
        "label_count": len(summary.label_vectors),
        "jitter_count": len(summary.jitter_vectors),
        "entries": entries,
    }
    manifest_path = out_dir / "manifest.json"
    write_json_artifact(manifest_path, document)
    return manifest_path


@dataclass(frozen=True)
class LoadedPemb3mManifest:
    run_id: str
    arm_id: str
    dims: int
    query: Mapping[str, object]
    label: Mapping[str, object]
    jitter: Mapping[str, object]


def load_pemb3m_arm_manifest(root: Path, arm_id: str) -> LoadedPemb3mManifest:
    import numpy as np

    run_id = arm_run_id(arm_id)
    manifest_path = _arm_manifest_dir(root, arm_id) / "manifest.json"
    if not manifest_path.is_file():
        raise Pemb3mFlightError(f"embedding manifest missing for arm {arm_id!r}: {manifest_path}")
    try:
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise Pemb3mFlightError(f"cannot read embedding manifest {manifest_path}: {error}") from error
    if not isinstance(document, Mapping):
        raise Pemb3mFlightError(f"{manifest_path}: must be a JSON object")
    if document.get("schema") != PEMB3M_MANIFEST_SCHEMA:
        raise Pemb3mFlightError(
            f"{manifest_path}: schema must be {PEMB3M_MANIFEST_SCHEMA!r}, got {document.get('schema')!r}"
        )
    if document.get("run_id") != run_id:
        raise Pemb3mFlightError(f"{manifest_path}: run_id {document.get('run_id')!r} != expected {run_id!r}")
    if document.get("arm_id") != arm_id:
        raise Pemb3mFlightError(f"{manifest_path}: arm_id {document.get('arm_id')!r} != expected {arm_id!r}")
    dims = document.get("dims")
    if not isinstance(dims, int) or isinstance(dims, bool) or dims <= 0:
        raise Pemb3mFlightError(f"{manifest_path}: dims must be a positive integer, got {dims!r}")
    entries = document.get("entries")
    if not isinstance(entries, list) or not entries:
        raise Pemb3mFlightError(f"{manifest_path}: no entries")

    buckets: dict[str, dict[str, object]] = {"query": {}, "label": {}, "jitter": {}}
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise Pemb3mFlightError(f"{manifest_path}: entry is not an object: {entry!r}")
        contact_id = entry.get("contact_id")
        side = entry.get("side")
        relpath = entry.get("relpath")
        expected_sha256 = entry.get("sha256")
        if not isinstance(contact_id, str) or not contact_id:
            raise Pemb3mFlightError(f"{manifest_path}: entry missing non-empty contact_id: {entry!r}")
        if side not in buckets:
            raise Pemb3mFlightError(f"{manifest_path}: entry {contact_id!r} has unknown side {side!r}")
        if not isinstance(relpath, str) or not relpath:
            raise Pemb3mFlightError(f"{manifest_path}: entry {contact_id!r} missing non-empty relpath")
        if not isinstance(expected_sha256, str) or not expected_sha256:
            raise Pemb3mFlightError(f"{manifest_path}: entry {contact_id!r} missing non-empty sha256")
        bucket = buckets[side]
        if contact_id in bucket:
            raise Pemb3mFlightError(f"{manifest_path}: duplicate {side} contact_id {contact_id!r}")
        vector_path = Path(root) / relpath
        if not vector_path.is_file():
            raise Pemb3mFlightError(f"{manifest_path}: vector file missing for {contact_id!r}: {vector_path}")
        data = vector_path.read_bytes()
        actual_sha256 = hashlib.sha256(data).hexdigest()
        if actual_sha256 != expected_sha256:
            raise Pemb3mFlightError(
                f"{manifest_path}: sha256 mismatch for {contact_id!r}: manifest says {expected_sha256}, "
                f"file is {actual_sha256}"
            )
        array = _npy_to_array(data)
        if array.shape != (dims,):
            raise Pemb3mFlightError(
                f"{manifest_path}: vector for {contact_id!r} has shape {array.shape}, expected ({dims},)"
            )
        if not np.isfinite(array).all():
            raise Pemb3mFlightError(f"{manifest_path}: vector for {contact_id!r} contains a non-finite value")
        bucket[contact_id] = array

    for side, count_key in (("query", "query_count"), ("label", "label_count"), ("jitter", "jitter_count")):
        expected_count = document.get(count_key)
        if expected_count != len(buckets[side]):
            raise Pemb3mFlightError(
                f"{manifest_path}: {count_key} {expected_count!r} does not match {len(buckets[side])} "
                f"loaded {side} entries"
            )

    return LoadedPemb3mManifest(
        run_id=run_id,
        arm_id=arm_id,
        dims=dims,
        query=MappingProxyType(buckets["query"]),
        label=MappingProxyType(buckets["label"]),
        jitter=MappingProxyType(buckets["jitter"]),
    )


# ---------------------------------------------------------------------------
# Sweep orchestration -- arm-level idempotence (module docstring).
# ---------------------------------------------------------------------------


def run_pemb3m_sweep_flight(
    *, root: Path, arm_runners: Mapping[str, Callable[[], Pemb3mArmSummary]]
) -> dict[str, LoadedPemb3mManifest]:
    """``arm_runners``: ``arm_id -> a zero-arg callable`` that performs that
    arm's OWN flight IF invoked. An arm whose manifest already exists under
    ``root`` is loaded WITHOUT invoking its runner -- its session is never
    respawned (module docstring: the pemb3l abort lesson). Every arm's
    result -- freshly flown or already-complete -- is returned as the SAME
    sha256-verified :class:`LoadedPemb3mManifest` shape, via a mandatory
    write-then-reload for a freshly flown arm (this study's own "write
    once, always verify-reload" discipline, mirrored from ``rails.probes.
    pemb_flight``)."""

    unknown = set(arm_runners) - set(ARM_IDS)
    if unknown:
        raise Pemb3mFlightError(f"run_pemb3m_sweep_flight: unknown arm id(s) {sorted(unknown)}")
    results: dict[str, LoadedPemb3mManifest] = {}
    for arm_id, runner in arm_runners.items():
        if not is_arm_complete(root, arm_id):
            summary = runner()
            if summary.arm_id != arm_id:
                raise Pemb3mFlightError(
                    f"run_pemb3m_sweep_flight: runner for {arm_id!r} returned a summary for "
                    f"{summary.arm_id!r}"
                )
            write_pemb3m_arm_manifest(root, summary)
        results[arm_id] = load_pemb3m_arm_manifest(root, arm_id)
    return results


__all__ = [
    "ARM_IDS",
    "ARM_LABEL_N",
    "ARM_M1",
    "ARM_M1_ID",
    "ARM_M2",
    "ARM_M2_ID",
    "ARM_M3",
    "ARM_M3_ID",
    "ARM_M4",
    "ARM_M4_ID",
    "ARM_QUERY_N",
    "ARM_TOTAL_N",
    "ARMS",
    "ARMS_BY_ID",
    "BINDING_CONFIG_SCHEMA",
    "BINDING_CONFIG_SHA256",
    "BINDING_CONFIG_SHA256_AT_FLIGHT",
    "CASCADE_SOURCE_STATUS_ABSENT",
    "CASCADE_SOURCE_STATUS_COMPLETE",
    "CASCADE_SOURCE_STATUS_PARTIAL",
    "CASCADE_T0_SUPPLEMENT_MAX_CONTACTS",
    "CEILING_AUDIO_SECONDS",
    "CEILING_CALLS",
    "CEILING_GPU_HOURS",
    "CONTROL_ARM_IDS",
    "DEFAULT_PLANNED_GPU_HOURS",
    "DEFAULT_PLANNED_MODEL_CALLS",
    "DEFAULT_PLANNED_SPEECH_AUDIO_SECONDS",
    "EXPECTED_SPLIT_IDENTITY_HASH",
    "GATE_CONTACTS_MAX",
    "LEDGER_CONSUMED_COLUMN_INDEX",
    "PEMB3M_MANIFEST_SCHEMA",
    "PKEY2_338_ATTEMPT_ID",
    "PKEY2_338_RUN_EXPERIMENT_ID",
    "PKEY2_338_TRANSCRIPT_REGISTRY_RELPATH",
    "PKEY2_338_TRANSCRIPT_REGISTRY_SHA256",
    "PLANNED_TOTAL_EMBEDDING_CONTACTS",
    "POOLING_DIFFER_GATE_CONTACT_ID",
    "PROBE_ID",
    "QWEN3_EMB_EMBEDDING_DIM",
    "CascadeSourceCheckResult",
    "LoadedPemb3mManifest",
    "Pemb3mArm",
    "Pemb3mArmSummary",
    "Pemb3mFlightError",
    "PoolingDifferGateResult",
    "arm_run_id",
    "assert_binding_config_sha256",
    "assert_ledger_row_consumed",
    "assert_within_registered_ceilings",
    "binding_config_sha256",
    "build_binding_config_document",
    "build_execution_plan",
    "is_arm_complete",
    "load_pemb3m_arm_manifest",
    "resolve_model_binding",
    "run_cascade_source_check",
    "run_cascade_t0_supplement_flight",
    "run_control_import_feasibility_gates",
    "run_encode_only_preflight_gate",
    "run_local_encoder_arm_flight",
    "run_m1_arm_flight",
    "run_m4_arm_flight",
    "run_m4_repeat_call_gate",
    "run_pemb3m_sweep_flight",
    "run_pooling_differ_gate",
    "write_pemb3m_arm_manifest",
]


# Executed at import time (mirrors rails.probes.pemb3l_flight's own
# module-bottom self-check): fails LOUD the moment this module is next
# imported if a future edit adds a live reference to the forbidden ontology
# miner. Binding-config sha256 is NOT self-checked at import time (unlike
# pemb3l_flight) because it now depends on the umbrella lock's own live
# content, which this module never loads implicitly -- every caller passes
# its own already-loaded ``lock`` explicitly to
# :func:`assert_binding_config_sha256`.
assert_never_calls_ontology_miner()
_assert_this_module_never_calls_ontology_miner()
