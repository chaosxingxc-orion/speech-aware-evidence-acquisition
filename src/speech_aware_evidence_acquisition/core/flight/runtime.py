"""``FlightRuntime``: the one harness every arm and carrier flies through
(C4c consolidation).

Six stages, always run in this order, each producing exactly one hash-bound
receipt (``core.flight.receipts.FlightReceipts``) and refusing to run out of
order or twice:

``preflight -> preprocess -> serve -> run_phases -> seal -> score``

Every stage that could otherwise reach a model, a GPU, llama-server, an
embedding tool, or the network is reached ONLY through an injectable seam
(``session_starter``, ``transport_factory``, ``gate_factory``,
``rails_runner``, ``phase_runner``, ``score_batch``, ``packet_promoter``,
``client_factory``, ...); every seam defaults to the real production
primitive it wraps, but this module itself never imports anything that
performs I/O against a live server. Unit tests inject fakes for every seam
and never touch a server (module docstring's own hard rule) -- a real flight
is a later, separately preregistered step (see the residual list in the C4c
report).

This module composes primitives that already exist and are owned elsewhere
in this study; it invents no new model-facing behaviour. See each stage
method's own docstring for exactly which existing function it calls.
"""

from __future__ import annotations

import hashlib
import json
import math
import threading
import time
from pathlib import Path
from typing import Callable, Mapping, Sequence

from ...contracts import (
    CONSTRUCTION_VISIBLE_FIELD,
    STUDY_SLUG,
    ExecutionPlan,
    FrozenCoreGate,
    _EXPOSURE_RUN_COLUMN,
    _parse_ledger_tables,
    assert_execution_scope,
)
from ...data.lock import asset_dir, load_lock, umbrella_lock_path
from ...data.splits import prefixed, split_identity_hash
from ...e0.d2_leakage import ARM_VISIBLE_FIELDS
from ...rails.context_budget import (
    ContextBudgetBreakdown,
    ContextBudgetInput,
    REGISTERED_SPECIAL_TOKEN_RESERVE,
    assess_context_budget,
)
from ...rails.controllers import default_phase_program
from ...rails.core_client import FrozenCoreClient, build_payload_binding
from ...rails.evolution import ProposerMaterial, build_proposer_material
from ...rails.phase_runner import run_continuous_program, run_program
from ...rails.runner import RAILS_ARMS, run_rails_experiment
from ...rails.task_adapter import TaskAdapter
from ..attempts.store import AttemptStore
from ..base import (
    CoreError,
    PayloadBindingContext,
    MAX_TOKENS_POLICIES,
    RunResult,
    declared_derived_media_roots,
)
from ..bundle.finalize import abort_attempt_if_opened, finalize_bundle
from ..bundle.git_commit import require_clean_study_repo
from ..bundle.manifest import build_manifest
from ..bundle.verify import verify_bundle
from ..config import (
    compose,
    d1_evidence_supplement_relpath,
    d1_evidence_supplement_sha256,
    d1_media_supplement_relpath,
    d1_media_supplement_sha256,
    effective_request_decoding_params,
    effective_request_values,
    model_lock_key,
    model_materialization_root,
    protocol_hash as compute_protocol_hash,
    resolve_runtime_receipt_path,
    runtime_receipt_relpath,
)
from ..configured_transport import build_configured_transport
from ..model.speech_features import materialize_legacy_cached_speech_feature_packets
from ..preparation_runtime import (
    assert_stable_file_fingerprint as _assert_file_fingerprint,
    verify_feature_encoder_runtime,
    verify_pinned_file as _verify_pinned_file,
)
from ..scoring_batch import load_score_jobs, run_score_batch
from ..tracing import set_current_trace_buffer
from ..tracking import ledger_row_for_bundle
from ..session import attach_session, load_runtime_receipt, start_session, stop_session
from ..session.serving import (
    MONITOR_JSONL_NAME,
    SESSION_RECEIPT_NAME,
    ServingSessionError,
    assert_identity_matches,
    find_resident_session,
    serving_identity,
    summarize_monitor_file,
)
from ..session.serving import merge_server_args as _merge_server_args
from ..split_receipt import VerifiedSplit
from .lease import WorkerExecutionPolicy
from .receipts import FLIGHT_STAGES, FlightReceipts, require_mandatory_throughput_fields

# ``core.driver.speech_native`` is imported lazily (function-local, inside
# the one method that needs it) rather than at module scope: ``core.driver``
# is itself lazily resolved from ``core/__init__.py`` (PEP 562) specifically
# to break the cycle ``rails/__init__ -> rails.consumption -> core.retrieval
# -> core/__init__ -> core.driver -> core.driver.speech_native -> rails``
# (partially initialized) -- see that module's own comment. This module
# already imports ``rails.*`` at module scope for the seams above, so an
# eager ``core.driver.speech_native`` import here would reopen exactly that
# cycle the moment anything imports ``core.flight.runtime`` before ``rails``
# has finished initializing.


class FlightRuntimeError(RuntimeError):
    """A :class:`FlightRuntime` input is invalid, or a stage cannot run."""


class FlightStageOrderError(FlightRuntimeError):
    """A stage ran before its required predecessor(s), or a second time."""


class FlightServeGeometryMismatchError(FlightRuntimeError):
    """``serve(reuse=...)`` was asked to reuse a server of a different
    serving geometry -- the queue must start a fresh server instead."""


#: Schema of the attempt-local record a flight writes when it ATTACHES to an
#: always-on serving session instead of spawning its own server (E7). It is
#: the attach counterpart of ``core.session``'s spawn-time session receipt:
#: same run/attempt identity, the serving session it bound to, the identity
#: fields that were compared, and -- once ``seal`` has run -- the monitor
#: summary for this attempt's own contact window.
SESSION_ATTACH_RECEIPT_SCHEMA = "saea-session-attach-receipt-v1"


class FlightServingSessionMismatchError(FlightRuntimeError):
    """An always-on serving session is resident, but it does not serve what
    this flight requires.

    Raised INSTEAD of quietly spawning a second server: two 18.5 GB
    llama-servers do not fit in this host's VRAM, so the correct action is
    always an operator decision (stop the session and start the other
    geometry), never a silent second spawn. The message names every
    differing identity field (``core.session.serving.identity_mismatches``);
    ``mismatches`` carries them structured.
    """

    def __init__(self, message: str, mismatches: Sequence[Mapping[str, object]] = ()) -> None:
        super().__init__(message)
        self.mismatches = tuple(dict(entry) for entry in mismatches)


#: Fields the experiment fragment's ``execution_plan`` object must declare;
#: everything else the real ``contracts.ExecutionPlan`` needs
#: (``run_id``/``attempt_id`` from the CLI/constructor, ``carrier_lock_key``
#: from the dataset fragment, ``split_identity_hash``/``protocol_hash``
#: computed from the live split and composed config) is filled in by
#: :meth:`FlightRuntime.preflight`, never read from config -- mirroring how
#: the September launcher's own ``parse_execution_plans``/the A0 launcher's
#: ``flight_plan`` module keep identity/budget fields separate from
#: computed-at-flight-time ones.
REQUIRED_EXECUTION_PLAN_FIELDS = (
    "execution_profile",
    "split_role",
    "planned_model_calls",
    "planned_gpu_hours",
    "planned_speech_audio_seconds",
)

#: The one ``ARM_VISIBLE_FIELDS`` entry that distinguishes the
#: speech-feature-packet audio path (``speech-feature-query`` and
#: ``speech-feature-query-native-tools``) from the raw-audio one
#: (``bare-core``, ``bare-core-native-tools``, ``fixed-legal-context``, ...).
#: Every branch below that asks "packets or raw audio?" asks it HERE, off
#: the arm's own D2-frozen field set, never off a hardcoded arm-name list --
#: the same discipline ``core.policies.FixedPolicy.run_sample`` already
#: documents at length for its own evidence branch.
SPEECH_FEATURE_ARM_FIELD = "speech_feature_parts"

#: A promotion receipt's packet ids are the flight's sample ids with ``:``
#: replaced by ``/`` (``tier1_direct:000045`` -> ``tier1_direct/000045``) --
#: the convention every Audio2Tool packet root and every SLURP runtime view
#: already uses, and the one ``scripts/a2t_g1_preprocess.py`` writes.
PACKET_ID_SEPARATOR = "/"
SAMPLE_ID_SEPARATOR = ":"

#: ``core.model.speech_features`` packets for this study's frozen core are
#: 2048-dimensional; the promoter re-asserts it rather than trusting bytes.
SPEECH_PACKET_N_EMBD = 2048

#: A model fragment may declare ``decoding_params.id_slot = "per-sample"``.
#: That is a SENTINEL, not a value: the batch executor that owns slot
#: allocation resolves it to an allocated llama-server slot integer so every
#: request of one sample lands on one slot and keeps that sample's stable
#: prefix in the slot's KV cache (canonical constant:
#: ``reproduction.ojw.runner.SLOT_AFFINITY_SENTINEL``, re-declared here as a
#: literal because that module imports openjiuwen at import time and lives
#: behind a lazy seam). ``core.model.adapter.FrozenCoreAdapter.request``
#: refuses the unresolved sentinel, so a runner that does not resolve it
#: cannot make a single contact.
SLOT_AFFINITY_SENTINEL = "per-sample"

#: This harness dispatches exactly one contact at a time (``rails.runner.
#: run_rails_experiment`` loops serially, and so does the packet direct
#: arm), so there is never more than one in-flight request to allocate a
#: slot for and the sentinel resolves to a single stable slot. That is also
#: the best case for what slot affinity exists to buy: every request of a
#: direct baseline shares the same multi-thousand-token instruction prefix,
#: and pinning one slot keeps it in that slot's KV cache. A future
#: concurrent dispatcher must resolve the sentinel per in-flight worker from
#: a free-slot queue instead, exactly as ``core.policies``' fixed-batch
#: policy and ``reproduction.ojw.runner`` already do.
SEQUENTIAL_DISPATCH_SLOT = 0

#: The bundle contract's own outputs field set (``core.bundle.outputs.
#: _REQUIRED_OUTPUTS_FIELDS``), named here so the Earnings dispatch can prove
#: the obs driver's sealed rows already satisfy it rather than rebuild them.
_OBS_OUTPUTS_FIELDS = frozenset(
    {
        "request_id",
        "sample_id",
        "carrier_lock_key",
        "arm",
        "text",
        "admitted",
        "request_sha256",
        "response_sha256",
        "response_text_sha256",
    }
)

#: A model (or baseline) fragment normally declares
#: ``decoding_params.max_tokens`` as a plain integer and every request of the
#: cell carries that same one. It may instead declare an OBJECT -- ``{"policy":
#: <a core.base.MAX_TOKENS_POLICIES id>, ...that policy's parameters}`` -- and
#: this runtime resolves it to an integer PER SAMPLE, from the sample's own
#: ``audio_seconds``, in exactly the three places it already resolves
#: :data:`SLOT_AFFINITY_SENTINEL` into a per-request slot.
#:
#: The seam is deliberately fragment-agnostic: ``core.config.compose`` merges
#: the four fragments into one flat mapping with disjoint top-level keys, so
#: whichever fragment carries ``decoding_params`` carries this too (the model
#: fragment, by this repository's convention -- 67 model fragments declare
#: ``decoding_params`` and no baseline fragment does).
#:
#: Fail-closed in both directions and byte-identical when absent:
#:
#: * an object without a registered ``policy`` id is refused;
#: * a ``max_tokens`` that is neither an integer nor such an object is refused;
#: * ``core.model.adapter.FrozenCoreAdapter.request`` refuses a non-integer
#:   ``max_tokens`` reaching the transport, exactly as it refuses an unresolved
#:   ``id_slot``, so a resolver that did not run cannot make a single contact;
#: * a fragment declaring a plain integer renders byte-identical requests (the
#:   base mapping is passed through unchanged, not rebuilt).
MAX_TOKENS_POLICY_KEY = "policy"


def _canonical_hash(document: object) -> str:
    blob = json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _default_token_counter(payload_bytes: bytes) -> int:
    """Placeholder-only ~4-bytes/token heuristic.

    ``rails.context_budget``'s own module docstring requires "receipt-bound
    exact counts for an already rendered payload immediately before each
    model contact" for a REAL contact; this default exists only so
    :meth:`FlightRuntime.preflight` is runnable (e.g. for a ``--dry-run``
    flight that never reaches :meth:`FlightRuntime.serve`) without a caller
    having wired the resident server's own tokenizer yet. A real flight must
    inject ``token_counter`` bound to the live server's exact tokenizer.
    """

    return max(1, len(payload_bytes) // 4)


def arm_uses_speech_feature_packets(arm: str) -> bool:
    """Whether ``arm``'s own D2-frozen field set carries speech-feature
    packet fields -- the single place this runtime decides "packets or raw
    audio", for every stage that has to branch on it.

    An arm this module has never heard of answers ``False`` rather than
    raising, exactly as :meth:`FlightRuntime.frozen_core_client_kwargs`'s
    own ``ARM_VISIBLE_FIELDS.get(arm, ())`` already does: refusing an
    unknown arm name is ``rails.core_client.FrozenCoreClient``'s job (it
    raises "unknown D2 arm" at construction, before any request), and
    duplicating that refusal here would only move the error earlier for
    fakes while changing nothing for a real flight.
    """

    return SPEECH_FEATURE_ARM_FIELD in ARM_VISIBLE_FIELDS.get(arm, ())


def arm_shows_construction_targets(arm: str) -> bool:
    """Whether ``arm``'s D2-frozen field set carries ``construction_targets``
    -- read off the freeze itself, never a hardcoded arm-name literal, the
    same discipline ``core.policies.build_arm_payload`` documents for its own
    branches. Today exactly ``"construction-proposer-text"`` answers yes."""

    return CONSTRUCTION_VISIBLE_FIELD in set(ARM_VISIBLE_FIELDS.get(arm, ()))


def _default_construction_material(
    values: Mapping[str, object],
    *,
    lock: Mapping[str, object],
    data_root: Path,
    repo_root: Path,
    samples: Sequence[object],
) -> ProposerMaterial:
    """The config-driven default for the ``construction_material_resolver``
    seam: render every proposer contact this flight will make.

    Everything it reads is committed and hash-pinned by the composed config:

    * ``construction_proposer_roster_receipt`` (+ ``_sha256``) -- the
      round's proposer roster, whose ``roster_role`` must be
      ``"construction"`` (``rails.evolution.read_proposer_roster`` refuses
      anything else) and whose items ARE the draws;
    * ``construction_target_tools`` -- the round's target sets, the same
      disjoint tool sets ``rails.evolution.Target`` carries;
    * ``evolution_incumbent_artifact_relpath`` (+ ``_sha256``), optional --
      ``A_r``'s override mapping; absent means ``A_0``, the released
      registry byte for byte.

    The construction rows' query text and gold calls are read HERE, at flight
    time, from the carrier (``data.audio2tool.load_query_rows``) and are
    rendered into the instruction and nowhere else: no construction text is
    ever written to a receipt or committed to this repository.
    """

    from ...data.audio2tool import load_query_rows, load_tool_registry  # noqa: PLC0415

    relpath = values.get("construction_proposer_roster_receipt")
    if not isinstance(relpath, str) or not relpath:
        raise FlightRuntimeError(
            "a construction-proposer flight's baseline fragment must declare "
            "'construction_proposer_roster_receipt' (the committed roster whose items "
            "are this round's draws)"
        )
    receipt_path = Path(repo_root) / relpath
    try:
        document = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise FlightRuntimeError(
            f"proposer roster receipt unreadable ({receipt_path}): {error}"
        ) from error
    declared_sha256 = values.get("construction_proposer_roster_receipt_sha256")
    if isinstance(declared_sha256, str) and declared_sha256:
        measured = _sha256_file(receipt_path)
        if measured != declared_sha256:
            raise FlightRuntimeError(
                f"proposer roster receipt {relpath} hashes to {measured}, not the "
                f"configured {declared_sha256}"
            )

    target_tools = values.get("construction_target_tools")
    if not isinstance(target_tools, Mapping) or not target_tools:
        raise FlightRuntimeError(
            "a construction-proposer flight's baseline fragment must declare "
            "'construction_target_tools' (target id -> its disjoint tool set)"
        )

    incumbent_overrides: Mapping[str, str] = {}
    incumbent_relpath = values.get("evolution_incumbent_artifact_relpath")
    if isinstance(incumbent_relpath, str) and incumbent_relpath:
        artifact_path = Path(repo_root) / incumbent_relpath
        declared = values.get("evolution_incumbent_artifact_sha256")
        if isinstance(declared, str) and declared:
            measured = _sha256_file(artifact_path)
            if measured != declared:
                raise FlightRuntimeError(
                    f"incumbent artifact {incumbent_relpath} hashes to {measured}, not "
                    f"the configured {declared}"
                )
        try:
            incumbent_overrides = json.loads(artifact_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise FlightRuntimeError(
                f"incumbent artifact unreadable ({artifact_path}): {error}"
            ) from error
        if not isinstance(incumbent_overrides, Mapping):
            raise FlightRuntimeError(
                f"incumbent artifact {incumbent_relpath} must be a JSON object of "
                "tool name to replacement description"
            )

    wanted: set[str] = set()
    for item in document.get("items", ()):
        if isinstance(item, Mapping):
            wanted.add(str(item.get("sample_id")))
            for exemplar_id in item.get("exemplar_ids", ()) or ():
                wanted.add(str(exemplar_id))
    exemplar_rows = load_query_rows(lock, Path(data_root), sorted(wanted))

    material = build_proposer_material(
        document,
        registry_rows=load_tool_registry(lock, Path(data_root)),
        target_tools={str(key): tuple(value) for key, value in target_tools.items()},
        incumbent_overrides={str(k): str(v) for k, v in incumbent_overrides.items()},
        exemplar_rows=exemplar_rows,
        carrier_lock_key=str(values.get("carrier_lock_key") or "") or None,
    )
    roster_ids = {contact.sample_id for contact in material.contacts}
    split_ids = {getattr(sample, "sample_id", None) for sample in samples}
    if roster_ids != split_ids:
        raise FlightRuntimeError(
            "the proposer roster's draws and this flight's split disagree about which "
            f"samples are contacted; symmetric difference "
            f"{sorted(roster_ids ^ split_ids)[:5]}"
        )
    return material


def merge_server_args(
    server_args: Sequence[object], *, slots: int, context_tokens: int
) -> list[str]:
    """The model fragment's own ``server_args``, with ONLY ``-np``/``-c``
    replaced (or appended when absent) from the adapter's serving geometry.

    Before this, :meth:`FlightRuntime.serve` passed ``["-np", ..., "-c", ...]``
    and NOTHING else to ``session_starter``, silently dropping every other
    flag the fragment declares -- including ``-ngl 999``, which is the
    difference between serving on the GPU and serving the whole flight on
    the CPU. The geometry still wins over the fragment for those two values
    (the adapter is what ``serve``/``FlightQueue`` compare when deciding
    whether a resident server can be reused), but nothing else is invented
    or discarded here.

    The merge itself now lives in ``core.session.serving`` so an
    operator-started always-on server (``scripts/serving_session.sh``) and a
    flight-started one are built by exactly ONE function -- otherwise the
    cross-process attach predicate would be comparing two dialects of the
    same command line. This wrapper exists only to keep the failure type a
    :class:`FlightRuntimeError` for every existing caller.
    """

    try:
        return _merge_server_args(server_args, slots=slots, context_tokens=context_tokens)
    except ServingSessionError as error:
        raise FlightRuntimeError(str(error)) from error


def _default_tool_schema_resolver(
    lock: Mapping[str, object], data_root: Path, fill_name: str
) -> Sequence[Mapping[str, object]]:
    """Resolve a baseline fragment's ``tool_schema_fill`` name through
    ``core.policies.TOOL_SCHEMA_FILLS`` -- the SAME registry
    ``core.policies.FixedPolicy.run_sample`` resolves it through on the
    non-flight path, so a native tool-calling arm sends byte-identical
    ``tools`` whichever path it flies. Imported function-locally: this
    module's own import surface stays light and free of the
    ``core.policies -> rails`` direction."""

    from ..policies import TOOL_SCHEMA_FILLS  # noqa: PLC0415 (light-import discipline)

    return TOOL_SCHEMA_FILLS.resolve(fill_name)(lock, Path(data_root))


def load_promotion_receipt(path: Path) -> Mapping[str, object]:
    """Read and shape-check a ``saea-a2t-speech-packet-promotion-receipt-v1``
    document (``scripts/a2t_g1_preprocess.py``'s own output): the hash-bound
    record of which packets exist, under which feature root, promoted from
    which legacy cache, under which encoder/decoder/mmproj identity."""

    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise FlightRuntimeError(
            f"speech packet promotion receipt is unreadable ({path}): {error}"
        ) from error
    if not isinstance(document, Mapping):
        raise FlightRuntimeError("speech packet promotion receipt must be a JSON object")
    required = ("feature_root", "legacy_cache_dir", "runtime_receipt_sha256", "packets")
    missing = [field for field in required if field not in document]
    if missing:
        raise FlightRuntimeError(
            f"speech packet promotion receipt is missing field(s) {missing}: {path}"
        )
    packets = document["packets"]
    if not isinstance(packets, list) or not packets:
        raise FlightRuntimeError(
            f"speech packet promotion receipt carries no packets: {path}"
        )
    return document


def packet_id_for_sample(sample_id: str) -> str:
    return sample_id.replace(SAMPLE_ID_SEPARATOR, PACKET_ID_SEPARATOR)


def sample_id_for_packet(packet_id: str) -> str:
    return packet_id.replace(PACKET_ID_SEPARATOR, SAMPLE_ID_SEPARATOR)


#: Schema of the receipt ``scripts/a2t_calibration_prompt_fit.py
#: --phase-program`` writes and :meth:`FlightRuntime._verify_phase_prompt_fit`
#: verifies before any contact.
PHASE_PROMPT_FIT_SCHEMA = "saea-phase-prompt-fit-v1"

#: The literal appended to a phase instruction that binds a predecessor
#: response which does not exist yet (``append-sealed-state`` at pre-flight
#: time). The pad's LENGTH is the completion-token ceiling's worth of ASCII,
#: which is the exact bound on what that predecessor can be;
#: :meth:`FlightRuntime._phase_prompt_payloads` has always used this shape
#: and the measurement/verification path reuses it so the two agree.
PHASE_PREDECESSOR_PAD_PREFIX = "Prior phase response (pad)"

#: Bytes of ASCII pad per completion token (``_phase_prompt_payloads``' own
#: ``"x" * (4 * max_tokens)``).
PHASE_PREDECESSOR_PAD_BYTES_PER_TOKEN = 4


def phase_envelope_sha256(envelope: Sequence[Mapping[str, object]]) -> str:
    """The identity of ONE phase contact's rendered transport envelope.

    Canonical JSON over the ``(system, user)`` message pair
    ``rails.phase_material.render_phase_envelope`` returns -- the same
    ``sort_keys``/compact-separator rule ``_canonical_hash`` applies
    everywhere else in this module. Defined HERE rather than in the
    measurement script so the number the script records and the number
    :meth:`FlightRuntime._verify_phase_prompt_fit` recomputes have exactly
    one authority and cannot drift.
    """

    return _canonical_hash(list(envelope))


def phase_program_system_text(adapter: object, sample: object) -> str:
    """The system message a phase contact for ``sample`` carries.

    ``rails.runner._agent_messages``' own rule, reproduced here so the
    prompt-fit measurement and this runtime's verification build the same
    bytes: the adapter's assembled system content, plus the adapter's task
    contract appended when the instruction does not already contain it.
    """

    from ...rails.obs import default_obs_packet  # noqa: PLC0415 (cycle guard)

    messages = adapter.assemble_prompt(sample, None)
    system_text = str(messages[0]["content"])
    contract = adapter.build_task_contract(sample, default_obs_packet(sample))
    if contract not in system_text:
        system_text = f"{system_text}\n\nTask contract:\n{contract}"
    return system_text


def render_phase_prompt_envelopes(
    *,
    program_id: str,
    phase_names: Sequence[str],
    specs: Mapping[str, object],
    static_text_by_phase: Mapping[str, str],
    system_text: str,
    prompt_order: str,
    packet_descriptor: Mapping[str, object],
    sample_id: str,
    sealed_states_by_phase: Mapping[str, Mapping[str, object]] | None = None,
    state_fill_by_phase: Mapping[str, object] | None = None,
    supply_blocks_by_phase: Mapping[str, Sequence[tuple[str, str]]] | None = None,
    completion_token_ceiling: int,
) -> dict[str, tuple[Mapping[str, object], ...]]:
    """``{phase: envelope}`` for ONE sample of a phase program.

    The one authority for what a phase contact looks like before it is sent.
    Two callers must agree byte-for-byte or the pinned receipt is worthless:
    ``scripts/a2t_calibration_prompt_fit.py --phase-program`` (which measures
    the envelope through the resident server) and
    :meth:`FlightRuntime._verify_phase_prompt_fit` (which re-renders it at
    pre-flight time and refuses on any difference).

    Per phase the instruction is the rendered static text, plus the
    predecessor binding's own suffix:

    * ``none`` -- nothing appended; the envelope is EXACT.
    * ``sealed-manifest`` -- the state this sample's row was sealed with,
      from ``sealed_states_by_phase[phase][sample_id]``; also EXACT, and
      genuinely per-sample.
    * ``append-sealed-state`` -- the predecessor is this run's own preceding
      response and does not exist yet, so the instruction is padded with
      ``completion_token_ceiling`` tokens' worth of ASCII: an upper bound,
      never an under-count.

    A ``sealed-manifest`` phase with no state supplied falls back to the same
    pad, so a caller that deliberately measures the bound (this runtime's own
    ``_phase_prompt_payloads`` estimate) and a caller that measures the exact
    text share one code path.

    ``supply_blocks_by_phase`` (E6) is the traced knowledge a SUPPLIED phase
    carries, in the exact ``"[evidence <id>] <content>"`` wire form. It never
    touches the instruction -- that is the whole point of the traced channel
    -- but it IS part of the request, so a prompt estimate that omitted it
    would under-count exactly the cell the estimate exists for. ``None`` by
    default and byte-identical to the pre-E6 rendering.

    ``state_fill_by_phase`` is the LAST thing appended, after the state block
    -- the same position and the same blank-line join
    ``rails.phase_material.build_material_for_phase`` uses, which is the real
    runtime path. It is ``None`` by default and the rendering is then
    byte-identical to what it always was, so a pinned
    :data:`PHASE_PROMPT_FIT_SCHEMA` receipt measured before this parameter
    existed still verifies. A caller that renders a phase declaring
    ``state_fill`` and does NOT pass its fill is counting a prompt shorter
    than the one that goes on the wire (for KC-S1b, by roughly 7,500 tokens),
    which is why :meth:`FlightRuntime._phase_prompt_payloads` resolves and
    passes them.
    """

    from ...rails.phase_material import (  # noqa: PLC0415 (cycle guard)
        render_phase_envelope,
    )

    if not isinstance(completion_token_ceiling, int) or completion_token_ceiling <= 0:
        raise FlightRuntimeError(
            "render_phase_prompt_envelopes needs a positive completion_token_ceiling"
        )
    pad = "x" * (PHASE_PREDECESSOR_PAD_BYTES_PER_TOKEN * int(completion_token_ceiling))
    states = dict(sealed_states_by_phase or {})
    fills = dict(state_fill_by_phase or {})
    supply_blocks = dict(supply_blocks_by_phase or {})
    envelopes: dict[str, tuple[Mapping[str, object], ...]] = {}
    for phase in phase_names:
        spec = specs[phase]
        instruction = static_text_by_phase[phase]
        binding = getattr(spec, "predecessor_binding", "none")
        if binding != "none":
            state = states.get(phase, {}).get(sample_id)
            if state is None:
                state_content = pad
                instruction = (
                    f"{instruction}\n\n{PHASE_PREDECESSOR_PAD_PREFIX}:\n{pad}"
                )
            else:
                state_content = str(state.content)
                instruction = (
                    f"{instruction}\n\nPrior phase response "
                    f"({state.state_kind}):\n{state.content}"
                )
            fill = fills.get(phase)
            if fill is not None:
                rendered = fill(state_content)
                if not isinstance(rendered, str) or not rendered.strip():
                    raise FlightRuntimeError(
                        f"phase {phase!r} state fill rendered no text for sample "
                        f"{sample_id!r}; a declared fill that renders nothing would "
                        "silently under-count the prompt it is part of"
                    )
                instruction = f"{instruction}\n\n{rendered}"
        envelopes[phase] = render_phase_envelope(
            system_text,
            instruction,
            prompt_order=prompt_order,
            packet_descriptor=packet_descriptor,
            contact_id=f"{program_id}:{phase}:{sample_id}",
            supply_blocks=tuple(supply_blocks.get(phase, ())),
        )
    return envelopes


#: Every wire-check artifact is written under a run id carrying this
#: prefix, so its durable attempt accounting can never be mistaken for --
#: or summed into -- a registered run's own budget. No exposure row exists
#: for such a run id, and none should: a wire check contacts nothing.
WIRE_CHECK_RUN_ID_PREFIX = "WIRECHECK-"

#: What the fake transport answers. Deliberately a well-formed tool-call
#: array so the real scorers have something legal to parse: a wire check
#: proves the SCORING LINK runs, never that any number it produces means
#: anything.
WIRE_CHECK_RESPONSE_TEXT = '[{"name": "wire-check", "arguments": {}}]'


class WireCheckGate:
    """A gate double for :meth:`FlightRuntime.wire_check`.

    It authorizes nothing real: no GGUF is hashed, no exposure row is read,
    no model is reachable, because the transport beside it never opens a
    socket. It exists only so the REAL ``FrozenCoreAdapter`` -- which
    demands a gate object -- can be constructed and its payload allowlist,
    media binding and attempt accounting exercised.
    """

    def __init__(self) -> None:
        self.checked_plans: list[object] = []
        self.checked_arms: list[str | None] = []

    def assert_model_touch_allowed(
        self, plan: object, *, arm: str | None = None, **_kwargs: object
    ) -> str:
        # ``arm`` is NAMED rather than swallowed by ``**_kwargs`` on purpose.
        # ``core.model.lifecycle`` detects the capability BY SIGNATURE and
        # refuses a construction-gold-visible arm outright when the gate
        # cannot receive it -- so a wire check of the ``construction-proposer
        # -text`` arm would die at its first (fake) contact against a gate
        # double that only had ``**kwargs``. It authorizes nothing either
        # way; it records what it was told, which is what the check asserts.
        self.checked_plans.append(plan)
        self.checked_arms.append(arm)
        return "0" * 64


class WireCheckTransport:
    """A transport double that records every request payload and answers
    :data:`WIRE_CHECK_RESPONSE_TEXT`. Never opens a socket."""

    def __init__(
        self,
        response_text: str = WIRE_CHECK_RESPONSE_TEXT,
        native_tool_calls_on_first: bool = False,
    ) -> None:
        self.payloads: list[Mapping[str, object]] = []
        self.request_bodies: list[bytes] = []
        self._response_text = response_text
        # When set, the FIRST response imitates a native tool-calling
        # envelope: the raw ``message.tool_calls`` list beside the canonical
        # text the transport would have derived from it. That is the only
        # way a contact-free check can prove the native-versus-text
        # accounting actually distinguishes the two, since the canonical
        # text is byte-identical either way.
        self._native_tool_calls_on_first = bool(native_tool_calls_on_first)

    def __call__(self, request_bytes: bytes) -> bytes:
        if not isinstance(request_bytes, bytes):
            raise FlightRuntimeError("transport must be handed bytes")
        first = not self.request_bodies
        self.request_bodies.append(request_bytes)
        self.payloads.append(json.loads(request_bytes.decode("utf-8")))
        envelope: dict[str, object] = {
            "text": self._response_text,
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }
        if first and self._native_tool_calls_on_first:
            envelope["tool_calls"] = [
                {
                    "id": "wire-check-0",
                    "type": "function",
                    "function": {"name": "wire-check", "arguments": "{}"},
                }
            ]
        return json.dumps(envelope).encode("utf-8")


def _default_packet_promoter(
    *, adapter: TaskAdapter, data_root: Path, samples: Sequence[object], workers: int
) -> tuple[Sequence[object], Mapping[str, object]]:
    """Sentinel-only fallback.

    This used to be the real default, and it fails closed because the
    bindings a promotion needs (a legacy featcache directory, the
    ``role: "preprocess"`` runtime receipt's hash, and the decoder/mmproj
    SHA-256 pair) are not derivable from thin air. They ARE, however,
    derivable from the artifact a preprocessing pass already wrote -- its
    ``saea-a2t-speech-packet-promotion-receipt-v1`` -- so
    :meth:`FlightRuntime._builtin_packet_promoter` now does exactly that.
    This function survives ONLY as the identity sentinel the constructor
    matches on to select that builtin (naming it explicitly and leaving it
    unset are therefore the same request), plus this defensive body for the
    one path that could still reach it: a caller that bypasses the
    constructor and installs it directly.
    """

    raise FlightRuntimeError(
        "the fail-closed sentinel packet_promoter was installed directly; construct "
        "FlightRuntime normally (its config-driven default resolves the baseline "
        "fragment's speech_packet_promotion_receipt) or inject a promoter that wraps "
        "core.model.speech_features.materialize_legacy_cached_speech_feature_packets"
    )


class FlightRuntime:
    """One flight's hash-bound harness: compose config, load the split,
    build and validate an :class:`~contracts.ExecutionPlan`, open the gate,
    (optionally) promote speech packets, serve the resident core, run the
    baseline's declared policy, seal the bundle, and score it.

    Every external effect is reached through a constructor-injected seam;
    every seam not given defaults to the real primitive named in its
    parameter's own comment below. A stage's own docstring names the
    existing function(s) it calls.
    """

    def __init__(
        self,
        repo_root: Path,
        data_root: Path,
        *,
        model: str,
        dataset: str,
        baseline: str,
        experiment: str,
        run_id: str,
        attempt_id: str,
        adapter_factory: Callable[[Mapping[str, object], Path], TaskAdapter],
        runtime_root: Path,
        session_starter: Callable[..., object] = start_session,
        session_stopper: Callable[..., Mapping[str, object]] = stop_session,
        # E7 always-on serving (owner rule 2026-09-07). The finder returns
        # the ONE resident serving session under the data root, or None; the
        # attacher binds to its on-disk session receipt. Defaults are the
        # real primitives, so a data root with no `serving/` directory (every
        # existing test, and any host that never starts a session) behaves
        # exactly as before: spawn, own, stop.
        serving_session_finder: Callable[[Path], object | None] = find_resident_session,
        session_attacher: Callable[..., object] = attach_session,
        transport_factory: Callable[..., object] | None = None,
        gate_factory: Callable[..., object] = FrozenCoreGate.for_study_repo,
        rails_runner: Callable[..., object] = run_rails_experiment,
        # The Earnings carrier's runner (owner Decision 12-F item #9,
        # 2026-09-08). ``None`` -- the default -- resolves lazily to
        # ``core.driver.run.run_experiment``, the ONE obs harness; the seam
        # exists so a wiring proof can drive :meth:`run_phases` over a fake
        # transport without importing librosa, exactly as ``rails_runner``
        # and ``phase_runner`` do for their own dispatches.
        obs_runner: Callable[..., object] | None = None,
        phase_runner: Callable[..., object] = run_program,
        continuous_phase_runner: Callable[..., object] = run_continuous_program,
        live_phase_fit_factory: Callable[..., object] | None = None,
        score_batch: Callable[..., Mapping[str, object]] = run_score_batch,
        clock: Callable[[], float] = time.time,
        # -- additional seams the C4c brief calls for "through seams" but
        # does not enumerate in its own constructor list (each defaults to
        # the real primitive it wraps; see the module docstring) --------
        manifest_builder: Callable[..., Path] = build_manifest,
        bundle_verifier: Callable[..., object] = verify_bundle,
        bundle_finalizer: Callable[..., object] = finalize_bundle,
        flight_receipt_builder: Callable[..., Mapping[str, object]] | None = None,
        packet_promoter: Callable[..., tuple[Sequence[object], Mapping[str, object]]] = (
            _default_packet_promoter
        ),
        client_factory: Callable[..., object] = FrozenCoreClient,
        payload_binding_factory: Callable[..., object] = build_payload_binding,
        carrier_root_resolver: Callable[[Mapping[str, object], str, Path], Path] = asset_dir,
        runtime_receipt_loader: Callable[[Path], Mapping[str, object]] = load_runtime_receipt,
        attempt_store_factory: Callable[[Path], object] = (
            lambda data_root: AttemptStore(Path(data_root) / "attempts")
        ),
        abort_attempt: Callable[..., bool] = abort_attempt_if_opened,
        ledger_validator: Callable[..., object] = ledger_row_for_bundle,
        token_counter: Callable[[bytes], int] = _default_token_counter,
        tool_schema_resolver: Callable[[Mapping[str, object], Path, str], Sequence[Mapping[str, object]]]
        | None = _default_tool_schema_resolver,
        construction_material_resolver: Callable[..., ProposerMaterial] = (
            _default_construction_material
        ),
        lock: Mapping[str, object] | None = None,
        run_dir: Path | None = None,
        host: str = "127.0.0.1",
        port: int = 8080,
        request_id_prefix: str = "flight",
        campaign_active: bool = False,
        speech_tokens_per_second: float = 14.4,
        execution_policy: WorkerExecutionPolicy | None = None,
    ) -> None:
        if not isinstance(run_id, str) or not run_id:
            raise FlightRuntimeError("run_id must be a non-empty string")
        if not isinstance(attempt_id, str) or not attempt_id:
            raise FlightRuntimeError("attempt_id must be a non-empty string")
        if not callable(adapter_factory):
            raise FlightRuntimeError("adapter_factory must be callable")
        self._execution_policy = execution_policy
        self._serve_fingerprint: str | None = None
        self._repo_root = Path(repo_root)
        self._data_root = Path(data_root)
        self._runtime_root = Path(runtime_root)
        self._model = model
        self._dataset = dataset
        self._baseline = baseline
        self._experiment = experiment
        self._run_id = run_id
        self._attempt_id = attempt_id
        self._adapter_factory = adapter_factory
        self._session_starter = session_starter
        self._session_stopper = session_stopper
        self._serving_session_finder = serving_session_finder
        self._session_attacher = session_attacher
        self._transport_factory = transport_factory
        self._gate_factory = gate_factory
        self._rails_runner = rails_runner
        self._obs_runner = obs_runner
        self._phase_runner = phase_runner
        self._continuous_phase_runner = continuous_phase_runner
        self._live_phase_fit_factory = live_phase_fit_factory
        self._score_batch = score_batch
        self._clock = clock
        self._manifest_builder = manifest_builder
        self._bundle_verifier = bundle_verifier
        self._bundle_finalizer = bundle_finalizer
        self._flight_receipt_builder = flight_receipt_builder
        # Leaving ``packet_promoter`` unset -- or naming the module-level
        # sentinel explicitly, which is the same request -- selects the
        # config-driven builtin below; any other callable is used verbatim.
        self._packet_promoter = (
            self._builtin_packet_promoter
            if packet_promoter is _default_packet_promoter
            else packet_promoter
        )
        self._client_factory = client_factory
        self._payload_binding_factory = payload_binding_factory
        self._carrier_root_resolver = carrier_root_resolver
        self._runtime_receipt_loader = runtime_receipt_loader
        self._attempt_store_factory = attempt_store_factory
        self._abort_attempt = abort_attempt
        self._ledger_validator = ledger_validator
        self._token_counter = token_counter
        self._tool_schema_resolver = tool_schema_resolver
        self._construction_material_resolver = construction_material_resolver
        self._lock = lock
        self._explicit_run_dir = Path(run_dir) if run_dir is not None else None
        self._host = host
        self._port = int(port)
        self._request_id_prefix = request_id_prefix
        self._campaign_active = bool(campaign_active)
        self._speech_tokens_per_second = float(speech_tokens_per_second)

        self.receipts = FlightReceipts(run_id=run_id, attempt_id=attempt_id)
        self._composed = None
        self._adapter: TaskAdapter | None = None
        self._plan: ExecutionPlan | None = None
        self._split_id: str | None = None
        self._samples: tuple[object, ...] = ()
        self._gate = None
        self._attempt_store = None
        self._attempt_handle = None
        self._session = None
        self._transport = None
        self._runtime_receipt: Mapping[str, object] | None = None
        self._session_receipt_path: Path | None = None
        self._client = None
        self._binding = None
        self._validated_packet_set = None
        self._output_rows: list[Mapping[str, object]] = []
        # Every phase summary ``run_phases`` got back, in program order.
        # ``_output_rows`` above carries only the LAST phase's rows (one row
        # per sample is what the bundle contract accepts); the earlier
        # phases are not thrown away -- ``seal`` writes all of them to
        # ``<run_id>.phases.json`` so a two-contact cell's first-phase
        # responses stay auditable beside the answer that was sealed.
        self._phase_summaries: tuple[object, ...] = ()
        # Set only by the Earnings/obs dispatch: the ``core.base.RunResult``
        # the obs driver returned, carrying that run's own arm, trace
        # manifest hash and measured cost. ``seal`` reads it instead of
        # closing a client the obs path never built.
        self._obs_result: RunResult | None = None
        self._phase_program_material: Mapping[str, object] | None = None
        self._phase_material_receipt: Mapping[str, object] | None = None
        # E6: what the baseline fragment's ``phase_supply`` resolved to --
        # the identity record (never the vectors), and the injection seam
        # for a provider this harness cannot construct from the frozen
        # KnowledgeSnapshot alone.
        self._phase_supply_receipt: Mapping[str, object] | None = None
        self._phase_supply_providers: Mapping[str, object] | None = None
        # W1 (owner Decision 11-B change #1, 2026-09-08): what the baseline
        # fragment's ``phase_review`` resolved to -- the spec plus the flag
        # counts the judges raised -- and the injection seam for the carrier
        # material a judge needs and no config fragment can hold (a legal
        # label inventory, a per-intent slot block, a candidate roster). Same
        # shape and same reason as the two phase_supply fields above.
        self._phase_review_receipt: Mapping[str, object] | None = None
        self._phase_review_material: Mapping[str, object] | None = None
        self._promotion_receipt: Mapping[str, object] | None = None
        self._window_feature_packets = None
        self._window_feature_packet_config = None
        self._construction_material: ProposerMaterial | None = None
        self._owns_session = False
        # E7: set only when this flight ATTACHED to an always-on serving
        # session -- the session's directory, its monitor JSONL, and the
        # attempt-local attach receipt that records both plus (at seal) the
        # monitor summary for this attempt's own contact window.
        self._serving_session_dir: Path | None = None
        self._serving_monitor_path: Path | None = None
        self._session_attach_receipt_path: Path | None = None
        self._session_attach_receipt: dict[str, object] | None = None
        # (first contact epoch, last contact epoch) of ``run_phases``.
        self._contact_window: tuple[float, float] | None = None

    # -- small read-only accessors ---------------------------------------

    @property
    def adapter(self) -> TaskAdapter:
        if self._adapter is None:
            raise FlightStageOrderError("adapter is unavailable before preflight()")
        return self._adapter

    @property
    def attempt_id(self) -> str:
        return self._attempt_id

    @property
    def run_id(self) -> str:
        return self._run_id

    @property
    def plan(self) -> ExecutionPlan:
        if self._plan is None:
            raise FlightStageOrderError("plan is unavailable before preflight()")
        return self._plan

    def _run_dir(self) -> Path:
        if self._explicit_run_dir is not None:
            return self._explicit_run_dir
        return self._data_root / "runs" / self._run_id / self._attempt_id

    def _require_prior_stages(self, stage: str) -> None:
        index = FLIGHT_STAGES.index(stage)
        for prior in FLIGHT_STAGES[:index]:
            if not self.receipts.has(prior):
                raise FlightStageOrderError(
                    f"flight stage {stage!r} requires {prior!r} to have run first; "
                    f"completed so far: {self.receipts.completed_stages()}"
                )
        if self.receipts.has(stage):
            raise FlightStageOrderError(
                f"flight stage {stage!r} has already run for run {self._run_id!r} "
                f"attempt {self._attempt_id!r}; refusing to run it twice"
            )

    # -- stage 1: preflight -----------------------------------------------

    def _gate_touch(self, gate: object, plan: ExecutionPlan) -> object:
        """``gate.assert_model_touch_allowed(plan, arm=...)``, with the arm
        forwarded whenever the gate can receive it.

        The arm exists for exactly one check,
        ``contracts.gate_exposure._require_construction_role_for_visible_targets``,
        which refuses a construction-gold-visible arm whose plan is not bound
        to a committed ``roster_role == "construction"`` roster of the plan's
        own carrier. ``core.model.lifecycle`` already forwards it at the
        FIRST CONTACT; forwarding it here as well moves the refusal to
        preflight and to serve, i.e. before a server has been started and
        before an attempt id has been spent -- and a stage that cannot
        forward it must never fly a construction-visible arm at all.

        Capability is detected BY SIGNATURE, never by catching ``TypeError``:
        catching it would swallow a genuine ``TypeError`` raised INSIDE the
        gate and silently retry the touch without the arm. A gate that cannot
        take the arm (every pre-existing test double) keeps its old behaviour
        for every ordinary arm.
        """

        import inspect  # noqa: PLC0415 -- function-local, cheap, mirrors core.model.lifecycle

        call = gate.assert_model_touch_allowed
        try:
            accepts_arm = "arm" in inspect.signature(call).parameters
        except (TypeError, ValueError):
            accepts_arm = False
        arm = self._arm()
        if not accepts_arm:
            if arm_shows_construction_targets(arm):
                raise FlightRuntimeError(
                    f"arm {arm!r} makes construction gold visible to the frozen core, "
                    "but this gate cannot receive the arm and so cannot check the "
                    "construction-roster binding; flight refused"
                )
            return call(plan)
        return call(plan, arm=arm)

    def _require_exposure_row_unconsumed(self, run_id: str) -> None:
        """Reuse ``contracts.gate_exposure``'s own ledger parser
        (re-exported from ``contracts`` -- see that package's module
        docstring) to independently confirm a pre-registered, unconsumed
        exposure row exists for ``run_id``, ahead of and separate from
        whatever ``gate_factory``'s own ``assert_model_touch_allowed`` does
        (which may be a fake in a test)."""

        ledger_path = self._repo_root / "docs" / "exposure-ledger.md"
        try:
            text = ledger_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise FlightRuntimeError(
                f"exposure ledger unreadable ({ledger_path}): {error}"
            ) from error
        rows = _parse_ledger_tables(text)
        matched = [row for row in rows if row.get(_EXPOSURE_RUN_COLUMN) == run_id]
        if not matched:
            raise FlightRuntimeError(
                f"no pre-registered exposure row for run {run_id!r} in {ledger_path}"
            )
        if len(matched) > 1:
            raise FlightRuntimeError(f"run {run_id!r} is pre-registered more than once")
        if matched[0].get("consumed", "").strip().lower() != "no":
            raise FlightRuntimeError(
                f"exposure row for run {run_id!r} is not consumed=no; refusing to fly"
            )

    def _build_execution_plan(self, values: Mapping[str, object], carrier_lock_key: str, identity_hash: str) -> ExecutionPlan:
        declaration = values.get("execution_plan")
        if not isinstance(declaration, Mapping):
            raise FlightRuntimeError(
                "experiment fragment must declare an 'execution_plan' object with "
                f"fields {REQUIRED_EXECUTION_PLAN_FIELDS}"
            )
        missing = [name for name in REQUIRED_EXECUTION_PLAN_FIELDS if name not in declaration]
        if missing:
            raise FlightRuntimeError(
                f"experiment fragment execution_plan is missing required field(s): {missing}"
            )
        arm = values.get("arm")
        if not isinstance(arm, str) or not arm:
            raise FlightRuntimeError("baseline fragment must declare a non-empty 'arm'")
        phash = compute_protocol_hash(self._composed.config_hash, arm, identity_hash)
        plan = ExecutionPlan(
            run_id=self._run_id,
            execution_profile=declaration["execution_profile"],
            carrier_lock_key=carrier_lock_key,
            split_role=declaration["split_role"],
            split_identity_hash=identity_hash,
            planned_model_calls=declaration["planned_model_calls"],
            planned_gpu_hours=declaration["planned_gpu_hours"],
            planned_speech_audio_seconds=declaration["planned_speech_audio_seconds"],
            protocol_hash=phash,
            attempt_id=self._attempt_id,
        )
        plan.validate()
        assert_execution_scope(plan.execution_profile)
        return plan

    def _phase_prompt_payloads(
        self, samples: Sequence[object], program: object
    ) -> Mapping[str, bytes]:
        """The LARGEST rendered request PER PHASE over the WHOLE roster.

        A phase's own instruction rides the payload's ORG/CONTROL history
        turn, so the adapter's bare ``assemble_prompt`` -- what the direct
        path estimates over -- is not the request a phase program sends. For
        a cell whose select phase carries a tool registry that is thousands
        of tokens of difference, i.e. exactly the kind of miss a prompt-fit
        estimate exists to catch. This renders each phase through
        :func:`render_phase_prompt_envelopes`, the same one authority the
        pinned prompt-fit measurement and its verification use.

        WHY EVERY SAMPLE, NOT ONE (KC-S1's defect 3, 2026-09-05). This used
        to render ONE representative row and apply no ``state_fill`` at all.
        Both under-count, and a prompt budget that under-counts is worse than
        none: for KC-S1b the estimate was about 7,500 tokens short of the
        widest real request, so its ALLOW said nothing about the phase cell
        that actually flies. What is rendered now, per sample:

        * the sample's OWN system text (``phase_program_system_text``, which
          is ``rails.runner._agent_messages``' rule -- the adapter's
          assembled system content plus its task contract when the
          instruction does not already carry it) and its OWN packet
          descriptor;
        * for a ``sealed-manifest`` phase, that sample's REAL sealed
          predecessor state, rebuilt from the pinned manifest exactly as
          :meth:`_verify_phase_prompt_fit` rebuilds it;
        * for a phase declaring a ``state_fill``, the fill's per-sample text,
          appended last, as ``rails.phase_material.build_material_for_phase``
          appends it on the wire.

        The one remaining approximation stays, and stays in the SAFE
        direction: an ``append-sealed-state`` phase's predecessor is this
        run's own preceding response and does not exist yet, so it is padded
        with the completion-token ceiling's worth of ASCII, which is exactly
        what bounds it. A state fill over that pad renders the fill's own
        fallback, which is its widest output.

        The maximum is taken on SERIALIZED BYTES, not on tokens: this method
        is the fail-early estimate and must not pay a real tokenizer 3 x
        1,000 times at pre-flight; :meth:`_assess_prompt_budget` counts
        tokens once per phase on the payload chosen here. The exact
        per-request measurement remains the pinned prompt-fit receipt.
        """

        from ...rails.phase_material import (  # noqa: PLC0415 (cycle guard)
            PHASE_STATE_FILLS,
            load_phase_material_specs,
            render_static_instruction,
            sealed_states_from_manifest,
        )

        samples = tuple(samples)
        if not samples:
            raise FlightRuntimeError(
                "_phase_prompt_payloads needs at least one sample to render"
            )
        baseline_values = self._composed.values
        specs = load_phase_material_specs(baseline_values, program)
        static_text = {
            phase: render_static_instruction(
                spec, self._repo_root, self._lock, self._data_root
            )
            for phase, spec in specs.items()
        }
        bindings = self.speech_packet_bindings()
        prompt_order = str(
            baseline_values.get("prompt_order") or "speech-query-prefix-v2"
        )
        ceiling = self._completion_token_ceiling()
        sample_ids = tuple(str(sample.sample_id) for sample in samples)

        # A sealed-manifest phase's predecessor is REAL and per-sample: load
        # the whole roster's states once, from the manifest the fragment
        # pins, rather than padding over something already on disk.
        sealed_states: dict[str, Mapping[str, object]] = {}
        for phase, spec in specs.items():
            if getattr(spec, "predecessor_binding", "none") != "sealed-manifest":
                continue
            source = spec.predecessor_source or {}
            sealed_states[phase] = sealed_states_from_manifest(
                self._data_root / str(source["manifest_relpath"]),
                expected_sha256=str(source["manifest_sha256"]),
                phase_name=phase,
                producer_policy_id=str(source["producer_policy_id"]),
                sample_ids=sample_ids,
            )

        # Registered per-sample fills, resolved ONCE (a fill that reads
        # pinned carrier data pays for it here, not per sample) through the
        # same public registry ``build_material_for_phase`` resolves.
        fills: dict[str, object] = {}
        for phase, spec in specs.items():
            name = getattr(spec, "state_fill", None)
            if name is None:
                continue
            factory = PHASE_STATE_FILLS.resolve(str(name))
            if not callable(factory):
                raise FlightRuntimeError(
                    f"registered phase state fill {name!r} is not callable"
                )
            # ``fill_params`` reach the FACTORY, exactly as
            # ``rails.phase_material._resolved_state_fills`` passes them on the
            # flight path itself. Calling ``factory()`` bare here was a real
            # divergence rather than a shortcut: EVO-S1's evolved fill opens a
            # committed artifact named by ``artifact_relpath``/``artifact_sha256``
            # and cannot be built without them, so the PROMPT BUDGET -- the one
            # pre-flight stage whose whole job is to render the widest real
            # request -- died before a candidate arm could fly at all, while the
            # arm it was budgeting for was fine.
            fill = factory(**dict(getattr(spec, "fill_params", {}) or {}))
            if not callable(fill):
                raise FlightRuntimeError(
                    f"phase {phase!r} state fill {name!r} did not resolve to a "
                    "callable (state_content) -> str"
                )
            fills[phase] = fill

        supply_blocks = self._phase_supply_prompt_bound(program)

        payloads: dict[str, bytes] = {}
        for sample in samples:
            sample_id = str(sample.sample_id)
            envelopes = render_phase_prompt_envelopes(
                program_id=program.program_id,
                phase_names=program.phase_names(),
                specs=specs,
                static_text_by_phase=static_text,
                system_text=phase_program_system_text(self._adapter, sample),
                prompt_order=prompt_order,
                packet_descriptor=bindings[sample_id],
                sample_id=sample_id,
                sealed_states_by_phase=sealed_states,
                state_fill_by_phase=fills,
                supply_blocks_by_phase=supply_blocks,
                completion_token_ceiling=ceiling,
            )
            for phase, envelope in envelopes.items():
                blob = json.dumps(
                    list(envelope), ensure_ascii=False, sort_keys=True
                ).encode("utf-8")
                if len(blob) > len(payloads.get(phase, b"")):
                    payloads[phase] = blob
        return payloads

    def _phase_supply_prompt_bound(
        self, program: object
    ) -> dict[str, tuple[tuple[str, str], ...]]:
        """An UPPER BOUND on the traced blocks each supplied phase adds (E6).

        The exact per-sample selection is a function of that sample's sealed
        query vector, and rendering it here would mean loading the vector
        file and running recall/rank/fuse 1,000 times inside a fail-early
        estimate. The bound instead takes the ``k`` LONGEST values in the
        frozen snapshot (and, for a facet-exposing phase, the ``m`` longest
        facet representations): no per-sample decision can select more than
        ``k`` values, and none can select a longer one, so this is a true
        ceiling and it errs in the SAFE direction -- the same discipline
        :func:`render_phase_prompt_envelopes` already applies to an
        ``append-sealed-state`` predecessor it cannot know yet.

        The exact per-request measurement remains the pinned prompt-fit
        receipt.
        """

        from ...rails.phase_supply import (  # noqa: PLC0415 (cycle guard)
            load_phase_supply_specs,
        )

        specs = load_phase_supply_specs(self._composed.values, program)
        if not specs:
            return {}
        snapshot = self._load_knowledge_snapshot()
        by_length = sorted(
            snapshot.values, key=lambda value: (-len(value.content), value.value_id)
        )
        facets_by_length = sorted(
            snapshot.facets,
            key=lambda facet: (-len(facet.representation), facet.facet_id),
        )
        bound: dict[str, tuple[tuple[str, str], ...]] = {}
        for phase, spec in specs.items():
            blocks: list[tuple[str, str]] = []
            if spec.expose_facets:
                width = int((spec.fuse_coverage or {}).get("m", spec.k))
                blocks.extend(
                    (f"[evidence key:{facet.facet_id}] {facet.representation}", "key")
                    for facet in facets_by_length[:width]
                )
            blocks.extend(
                (f"[evidence {value.value_id}] {value.content}", "value")
                for value in by_length[: spec.k]
            )
            bound[phase] = tuple(blocks)
        return bound

    def _verify_phase_prompt_fit(self) -> Mapping[str, object] | None:
        """Verify a PINNED phase prompt-fit receipt against what this flight
        would actually render, before any contact.

        A fragment opts in by declaring BOTH ``prompt_fit_receipt`` (a plain
        relative path under this study repository) and
        ``prompt_fit_receipt_sha256``. Neither key present is the pre-existing
        behaviour: nothing is verified and ``None`` is returned. One key
        without the other is refused -- a receipt path with no hash pins
        nothing.

        What is checked, in order, each fail-closed:

        1. the receipt file's own sha256 equals the configured one;
        2. it carries schema :data:`PHASE_PROMPT_FIT_SCHEMA`;
        3. this flight's ``policy`` is a phase program (a receipt of this
           schema describes per-phase envelopes and means nothing otherwise);
        4. the receipt carries exactly ONE cell naming this flight's four
           config fragments -- the receipt says which measurement belongs to
           which cell and this runtime never guesses. The cell's recorded
           ``config_hash`` is provenance, never the match key: a receipt is
           measured from a fragment that does not yet pin it, and pinning it
           changes that very hash;
        5. that cell's phases are exactly the program's phases;
        6. for EVERY phase, re-rendering the envelope for the sample the
           receipt records as its maximum -- through
           :func:`render_phase_prompt_envelopes`, the same function the
           measurement used -- reproduces the recorded ``envelope_sha256``.

        Step 6 is the point of the whole mechanism: a receipt measured
        against an instruction, a registry, a template, a task contract, a
        prompt order or a packet binding that has since changed no longer
        describes what would go on the wire, and a flight that trusted it
        would be certifying a fit for a prompt it is not sending.

        This does NOT replace :meth:`_assess_prompt_budget`; that estimate
        runs unchanged beside it.
        """

        from ...rails.phase_material import (  # noqa: PLC0415 (cycle guard)
            load_phase_material_specs,
            render_static_instruction,
            sealed_states_from_manifest,
        )

        values = self._composed.values
        if values.get("prepared_request_fit") is not None:
            return self._verify_prepared_request_fit(values["prepared_request_fit"])
        relpath = values.get("prompt_fit_receipt")
        expected_sha256 = values.get("prompt_fit_receipt_sha256")
        if relpath is None and expected_sha256 is None:
            return None
        if not isinstance(relpath, str) or not relpath.strip():
            raise FlightRuntimeError(
                "prompt_fit_receipt_sha256 is declared but prompt_fit_receipt is not a "
                "non-empty relative path; a pinned hash with no file pins nothing"
            )
        if not isinstance(expected_sha256, str) or len(expected_sha256) != 64:
            raise FlightRuntimeError(
                f"prompt_fit_receipt {relpath!r} requires a 64-character "
                "prompt_fit_receipt_sha256; an unpinned receipt is not evidence"
            )
        if relpath.startswith("/") or "\\" in relpath or ".." in Path(relpath).parts:
            raise FlightRuntimeError(
                f"prompt_fit_receipt {relpath!r} is not a plain relative path inside "
                "the study repository"
            )
        receipt_path = self._repo_root / relpath
        if not receipt_path.is_file():
            raise FlightRuntimeError(f"prompt_fit_receipt missing: {receipt_path}")
        measured = _sha256_file(receipt_path)
        if measured != expected_sha256:
            raise FlightRuntimeError(
                f"prompt_fit_receipt {receipt_path} hashes to {measured}, not the "
                f"configured {expected_sha256}"
            )
        try:
            document = json.loads(receipt_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise FlightRuntimeError(
                f"prompt_fit_receipt {receipt_path} is unreadable: {error}"
            ) from error
        if not isinstance(document, Mapping) or document.get("schema") != (
            PHASE_PROMPT_FIT_SCHEMA
        ):
            raise FlightRuntimeError(
                f"prompt_fit_receipt {receipt_path} is not a "
                f"{PHASE_PROMPT_FIT_SCHEMA} document"
            )

        policy = values.get("policy")
        if not isinstance(policy, str) or policy == "fixed":
            raise FlightRuntimeError(
                f"prompt_fit_receipt {receipt_path} pins per-phase envelopes but this "
                f"flight's policy is {policy!r}, which is not a phase program"
            )
        program = default_phase_program(policy)
        if not self.uses_speech_feature_packets():
            raise FlightRuntimeError(
                f"prompt_fit_receipt {receipt_path} pins speech-feature packet "
                f"envelopes but arm {self._arm()!r} does not travel the packet path"
            )

        cells = document.get("cells")
        if not isinstance(cells, list) or not cells:
            raise FlightRuntimeError(
                f"prompt_fit_receipt {receipt_path} carries no cells"
            )
        wanted = {
            "model_fragment": self._model,
            "dataset_fragment": self._dataset,
            "baseline_fragment": self._baseline,
            "experiment_fragment": self._experiment,
        }
        matches = [
            cell
            for cell in cells
            if isinstance(cell, Mapping)
            and all(cell.get(key) == value for key, value in wanted.items())
        ]
        if len(matches) != 1:
            raise FlightRuntimeError(
                f"prompt_fit_receipt {receipt_path} carries {len(matches)} cell(s) for "
                f"fragments {wanted}; it measured "
                f"{[cell.get('cell_id') for cell in cells if isinstance(cell, Mapping)]}"
            )
        cell = matches[0]
        phase_entries = cell.get("phases")
        if not isinstance(phase_entries, list) or not phase_entries:
            raise FlightRuntimeError(
                f"prompt_fit_receipt {receipt_path} cell {cell.get('cell_id')!r} carries "
                "no phases"
            )
        recorded = tuple(
            str(entry.get("phase")) for entry in phase_entries if isinstance(entry, Mapping)
        )
        if recorded != tuple(program.phase_names()):
            raise FlightRuntimeError(
                f"prompt_fit_receipt {receipt_path} measured phases {list(recorded)} but "
                f"program {program.program_id!r} declares {list(program.phase_names())}"
            )

        specs = load_phase_material_specs(values, program)
        static_text = {
            phase: render_static_instruction(
                spec, self._repo_root, self._lock, self._data_root
            )
            for phase, spec in specs.items()
        }
        bindings = self.speech_packet_bindings()
        prompt_order = str(values.get("prompt_order") or "speech-query-prefix-v2")
        ceiling = self._completion_token_ceiling()
        samples_by_id = {sample.sample_id: sample for sample in self._samples}

        verified: list[Mapping[str, object]] = []
        for entry in phase_entries:
            phase = str(entry["phase"])
            sample_id = entry.get("max_sample_id")
            recorded_sha256 = entry.get("envelope_sha256")
            if not isinstance(sample_id, str) or not isinstance(recorded_sha256, str):
                raise FlightRuntimeError(
                    f"prompt_fit_receipt {receipt_path} phase {phase!r} lacks a "
                    "max_sample_id / envelope_sha256 pair"
                )
            sample = samples_by_id.get(sample_id)
            if sample is None:
                raise FlightRuntimeError(
                    f"prompt_fit_receipt {receipt_path} phase {phase!r} was measured on "
                    f"sample {sample_id!r}, which this flight's split does not carry"
                )
            sealed_states: dict[str, Mapping[str, object]] = {}
            spec = specs[phase]
            if spec.predecessor_binding == "sealed-manifest":
                source = spec.predecessor_source
                sealed_states[phase] = sealed_states_from_manifest(
                    self._data_root / str(source["manifest_relpath"]),
                    expected_sha256=str(source["manifest_sha256"]),
                    phase_name=phase,
                    producer_policy_id=str(source["producer_policy_id"]),
                    sample_ids=(sample_id,),
                )
            envelopes = render_phase_prompt_envelopes(
                program_id=program.program_id,
                phase_names=(phase,),
                specs=specs,
                static_text_by_phase=static_text,
                system_text=phase_program_system_text(self._adapter, sample),
                prompt_order=prompt_order,
                packet_descriptor=bindings[sample_id],
                sample_id=sample_id,
                sealed_states_by_phase=sealed_states,
                completion_token_ceiling=ceiling,
            )
            rebuilt = phase_envelope_sha256(envelopes[phase])
            if rebuilt != recorded_sha256:
                raise FlightRuntimeError(
                    f"prompt_fit_receipt {receipt_path} phase {phase!r} recorded envelope "
                    f"{recorded_sha256} for sample {sample_id!r} but this flight renders "
                    f"{rebuilt}; the measured envelope is not the one this flight would "
                    "send, so the pinned fit does not describe this contact"
                )
            verified.append(
                {
                    "phase": phase,
                    "max_sample_id": sample_id,
                    "envelope_sha256": rebuilt,
                    "max_text_prompt_tokens": entry.get("max_text_prompt_tokens"),
                    "every_request_fits": entry.get("every_request_fits"),
                }
            )
        return {
            "prompt_fit_receipt": str(receipt_path),
            "prompt_fit_receipt_sha256": measured,
            "schema": PHASE_PROMPT_FIT_SCHEMA,
            "cell_id": cell.get("cell_id"),
            "config_hash": self._composed.config_hash,
            "measured_config_hash": cell.get("config_hash"),
            "program_id": program.program_id,
            "phases": verified,
        }

    def _assess_prompt_budget(self, samples: Sequence[object]) -> tuple[Mapping[str, object], ...]:
        """Serialize a request per phase through the adapter and run it
        through ``rails.context_budget.assess_context_budget`` -- a PRE-FLIGHT
        estimate (module docstring: exact counts are required "immediately
        before each model contact", which is what a real flight's
        ``token_counter`` seam must supply at request time; this stage runs
        once, ahead of any contact).

        For a PHASE PROGRAM the request is the WIDEST one the roster
        produces for that phase, rendered by :meth:`_phase_prompt_payloads`
        over every sample, because a phase's own instruction -- and its
        per-sample predecessor state and state fill -- are part of what it
        sends. For ``policy == "fixed"`` nothing changed: one direct
        ``assemble_prompt`` over the representative row, exactly as before.

        An OBS policy has one phase and one instruction per window, and its
        speech term is a WINDOW rather than a whole call: an Earnings call is
        40-75 minutes but never reaches the core as one request. Estimating
        the whole call here would refuse every legal Earnings flight on a
        context ceiling no request of it ever approaches, so the speech term
        is the configured buffer -- which is exactly what one window carries,
        and is capped by the same knob a unit plan is cut under.
        """

        representative = samples[0]
        baseline_values = self._composed.values
        policy = baseline_values.get("policy")
        obs_policy = policy in self._obs_policy_names()
        phase_names: tuple[str, ...]
        phase_payloads: Mapping[str, bytes] = {}
        if policy == "fixed" or obs_policy:
            phase_names = ("obs-window",) if obs_policy else ("direct",)
        else:
            program = default_phase_program(str(policy))
            phase_names = program.phase_names()
            if self.uses_speech_feature_packets():
                phase_payloads = self._phase_prompt_payloads(samples, program)
        max_tokens = self._completion_token_ceiling()
        if self.shows_construction_targets():
            # The proposer arm sends no audio part at all, and its prompt is
            # NOT the adapter's instruction: it is the rendered proposer or
            # placebo instruction for one draw. Estimating the adapter's
            # registry prompt here would fit the wrong request entirely, so
            # the representative is the WIDEST instruction this flight will
            # actually send, and the speech term is one token rather than a
            # duration (``ContextBudgetBreakdown`` measures a packet list;
            # zero speech is what this arm sends).
            material = self.construction_material()
            widest = max(material.contacts, key=lambda contact: len(contact.instruction))
            messages = (
                {"role": "system", "content": widest.instruction},
                {"role": "user", "content": []},
            )
            speech_tokens = 1
        else:
            messages = self._adapter.assemble_prompt(representative, None)
            # An obs window, not the whole call (docstring above): the
            # configured buffer plus whatever silence tail the fragment
            # appends, which is precisely what one slice delivers.
            audio_seconds = (
                float(baseline_values.get("obs_buffer_seconds", 60.0))
                + float(baseline_values.get("obs_slice_tail_silence_seconds", 0.0))
                if obs_policy
                else float(getattr(representative, "audio_seconds", 1.0))
            )
            speech_tokens = max(
                1, round(audio_seconds * self._speech_tokens_per_second)
            )
        payload_bytes = json.dumps(
            list(messages), ensure_ascii=False, sort_keys=True
        ).encode("utf-8")
        receipts: list[Mapping[str, object]] = []
        for phase_name in phase_names:
            phase_bytes = phase_payloads.get(phase_name, payload_bytes)
            rendered_tokens = self._token_counter(phase_bytes)
            breakdown = ContextBudgetBreakdown(
                rendered_text_tokens=rendered_tokens,
                speech_feature_packet_tokens=((representative.sample_id, speech_tokens),),
                speech_feature_tokens=speech_tokens,
                special_token_reserve=REGISTERED_SPECIAL_TOKEN_RESERVE,
                completion_token_ceiling=max_tokens,
                required_window_tokens=(
                    rendered_tokens + speech_tokens + REGISTERED_SPECIAL_TOKEN_RESERVE + max_tokens
                ),
            )
            candidate = ContextBudgetInput.from_payload(phase_bytes, breakdown=breakdown)
            decision = assess_context_budget(candidate)
            if decision.decision.value != "ALLOW":
                # A pre-flight estimate has no live compaction mechanism to
                # apply, so COMPACT_REQUIRED is just as fail-closed here as
                # REFUSE: anything short of a clean ALLOW at compaction_pass
                # 0 means the estimate does not clear operational headroom.
                raise FlightRuntimeError(
                    f"prompt budget {decision.decision.value} (not ALLOW) for phase "
                    f"{phase_name!r}, representative sample "
                    f"{representative.sample_id!r}: {decision.to_dict()}"
                )
            receipts.append({"phase": phase_name, **decision.to_dict()})
        return tuple(receipts)

    def _prepare(self) -> tuple[Mapping[str, object], str, str, str]:
        """Compose the four fragments, build the adapter, load and
        identity-hash the split.

        Factored out of :meth:`preflight` so :meth:`wire_check` can reuse
        EXACTLY this resolution -- same fragments, same adapter, same
        samples, same identity hash -- without also opening the gate,
        asserting a clean tree or touching attempt accounting, none of which
        a contact-free wiring proof needs (and the clean-tree assertion in
        particular would make the check unusable precisely when it is most
        useful: on a working tree carrying the fix under test).
        """

        composed = compose(
            self._repo_root, self._model, self._dataset, self._baseline, self._experiment
        )
        self._composed = composed
        values = composed.values
        from ..bundle.delivery_replay import (
            require_experiment_phase_declarations, validate_phase_delivery_sources,
        )

        delivery_fragments = {
            "model_fragment": self._model,
            "dataset_fragment": self._dataset,
            "baseline_fragment": self._baseline,
        }
        deliveries = validate_phase_delivery_sources(values, parent_fragments=delivery_fragments)
        require_experiment_phase_declarations(
            self._repo_root, self._experiment, deliveries, delivery_fragments,
        )

        lock = self._lock if self._lock is not None else load_lock(umbrella_lock_path(self._repo_root))
        self._lock = lock

        adapter = self._adapter_factory(lock, self._data_root)
        if not isinstance(adapter, TaskAdapter):
            raise FlightRuntimeError("adapter_factory must return a TaskAdapter instance")
        self._adapter = adapter

        carrier_lock_key = values.get("carrier_lock_key")
        if not isinstance(carrier_lock_key, str) or not carrier_lock_key:
            raise FlightRuntimeError("dataset fragment must declare a non-empty carrier_lock_key")

        split_id = values.get("split_id")
        if not isinstance(split_id, str) or not split_id:
            raise FlightRuntimeError("dataset fragment must declare a non-empty split_id")
        self._split_id = split_id

        samples = tuple(adapter.load_split(split_id))
        if not samples:
            raise FlightRuntimeError(f"split {split_id!r} resolved to zero samples")
        self._samples = samples
        sample_ids = tuple(sample.sample_id for sample in samples)
        if len(set(sample_ids)) != len(sample_ids):
            raise FlightRuntimeError(f"split {split_id!r} contains duplicate sample ids")
        identity_hash = split_identity_hash(prefixed(carrier_lock_key, sample_ids))
        return values, carrier_lock_key, split_id, identity_hash

    def preflight(self) -> Mapping[str, object]:
        """Compose the four config fragments, load and identity-hash the
        split, build and validate the :class:`~contracts.ExecutionPlan`,
        open the gate (``gate_factory(...)`` then
        ``assert_model_touch_allowed``), independently re-check the
        exposure ledger row, assert a clean study tree
        (``core.bundle.git_commit.require_clean_study_repo``), reserve this
        attempt in the durable :class:`~core.attempts.store.AttemptStore`,
        verify a pinned phase prompt-fit receipt when the fragment declares
        one (:meth:`_verify_phase_prompt_fit`), and pre-assess the prompt
        budget -- for a phase program, over the WIDEST request each phase
        renders across the whole roster; for ``policy == "fixed"``, over one
        representative request. Fails closed and records nothing on any
        failure.
        """

        self._require_prior_stages("preflight")
        values, carrier_lock_key, split_id, identity_hash = self._prepare()
        if "whole_roster_wave_barrier" in values or "live_phase_fit" in values:
            from ..preparation_fit import validate_live_phase_fit_config
            policy = values.get("policy")
            if policy == "fixed" or policy in self._obs_policy_names():
                raise FlightRuntimeError("live phase fitting requires a registered phase program")
            validate_live_phase_fit_config(values, default_phase_program(policy))
        composed = self._composed
        adapter = self._adapter
        samples = self._samples

        plan = self._build_execution_plan(values, carrier_lock_key, identity_hash)
        self._plan = plan

        configured_model_root = model_materialization_root(values)
        gate = self._gate_factory(
            self._repo_root,
            self._data_root,
            self._runtime_root,
            runtime_receipt_relpath=runtime_receipt_relpath(values),
            expected_model_lock_key=model_lock_key(values),
            model_root=(Path(configured_model_root) if configured_model_root is not None else None),
            d1_media_supplement_relpath=d1_media_supplement_relpath(values),
            d1_media_supplement_sha256=d1_media_supplement_sha256(values),
            d1_evidence_supplement_relpath=d1_evidence_supplement_relpath(values),
            d1_evidence_supplement_sha256=d1_evidence_supplement_sha256(values),
        )
        self._gate = gate
        self._gate_touch(gate, plan)

        self._require_exposure_row_unconsumed(plan.run_id)

        study_commit = require_clean_study_repo(self._repo_root)

        # Attempt accounting: CHECK availability here, RESERVE in
        # core.model.adapter.FrozenCoreAdapter.
        #
        # This stage used to call open_attempt() itself. That double-opened
        # the one-time (run_id, attempt_id) key, because FrozenCoreAdapter --
        # "the ONLY model request path", by its own module docstring, and the
        # place core.attempts.AttemptStore.abort_if_opened itself names as
        # the thing that opens an attempt -- opens the SAME pair again when
        # run_phases builds the client. Every flight through this harness
        # therefore died at client construction with "already reserved or
        # opened ... a retry must mint a fresh attempt_id", after preflight
        # had already reported success. The handle this stage kept was never
        # read by anything.
        #
        # The early-failure intent survives without consuming the key: an
        # attempt file that already exists means this attempt_id was used
        # before, which is refused HERE rather than after a server has been
        # started and a geometry served.
        attempt_store = self._attempt_store_factory(self._data_root)
        self._attempt_store = attempt_store
        attempt_path = attempt_store.handle(plan.run_id, plan.attempt_id).path
        if attempt_path.is_file():
            raise FlightRuntimeError(
                f"attempt {plan.run_id}/{plan.attempt_id} already exists at "
                f"{attempt_path}; a (run_id, attempt_id) pair is a one-time key and "
                "a retry must mint a fresh attempt_id"
            )

        phase_prompt_fit = self._verify_phase_prompt_fit()
        prompt_budget = self._assess_prompt_budget(samples)

        payload = {
            "run_id": plan.run_id,
            "attempt_id": plan.attempt_id,
            "config_hash": composed.config_hash,
            "protocol_hash": plan.protocol_hash,
            "split_identity_hash": identity_hash,
            "split_id": split_id,
            "sample_count": len(samples),
            "carrier_lock_key": carrier_lock_key,
            "serving_geometry": dict(adapter.serving_geometry()),
            "study_commit": study_commit,
            "attempt_reservation": "deferred to core.model.adapter.FrozenCoreAdapter",
            "prompt_budget": prompt_budget,
            "phase_prompt_fit": phase_prompt_fit,
        }
        return self.receipts.record("preflight", payload)

    # -- stage 2: preprocess ----------------------------------------------

    def _arm(self) -> str:
        arm = self._composed.values.get("arm")
        if not isinstance(arm, str) or not arm:
            raise FlightRuntimeError("baseline fragment must declare a non-empty 'arm'")
        return arm

    def uses_speech_feature_packets(self) -> bool:
        """Whether THIS flight's arm travels the speech-feature packet audio
        path. Requires :meth:`preflight` (the arm comes from the composed
        baseline fragment)."""

        if self._composed is None:
            raise FlightStageOrderError("the arm is unavailable before preflight()")
        return arm_uses_speech_feature_packets(self._arm())

    def shows_construction_targets(self) -> bool:
        """Whether THIS flight's arm is the text-only construction-proposer
        arm -- the ONE arm whose payload carries gold (E2.4). Requires
        :meth:`_prepare` (the arm comes from the composed baseline
        fragment)."""

        if self._composed is None:
            raise FlightStageOrderError("the arm is unavailable before preflight()")
        return arm_shows_construction_targets(self._arm())

    def construction_material(self) -> ProposerMaterial:
        """This flight's rendered proposer contacts, resolved once.

        Resolution is a SEAM (``construction_material_resolver``) exactly
        like ``tool_schema_resolver`` and ``packet_promoter``: the default
        reads the committed roster, the target sets, the incumbent artifact
        and the carrier's own construction rows; a test injects a synthetic
        one and never touches the carrier.
        """

        if self._construction_material is None:
            if self._composed is None:
                raise FlightStageOrderError(
                    "construction material is unavailable before preflight()"
                )
            if not callable(self._construction_material_resolver):
                raise FlightRuntimeError("construction_material_resolver must be callable")
            material = self._construction_material_resolver(
                self._composed.values,
                lock=self._lock,
                data_root=self._data_root,
                repo_root=self._repo_root,
                samples=self._samples,
            )
            if not isinstance(material, ProposerMaterial):
                raise FlightRuntimeError(
                    "construction_material_resolver must return a "
                    "rails.evolution.ProposerMaterial"
                )
            if not material.contacts:
                raise FlightRuntimeError(
                    "the construction-proposer flight resolved zero contacts; there is "
                    "nothing to fly"
                )
            self._construction_material = material
        return self._construction_material

    def window_feature_packet_binding(self):
        """Load one immutable window map per composed source binding."""
        from ..driver.run import load_window_packet_binding

        declaration = self._composed.values.get("prepared_window_feature_packets")
        if declaration is None:
            return None
        identity = _canonical_hash({
            "values": self._composed.values,
            "samples": [sample.sample_id for sample in self._samples],
        })
        if getattr(self, "_window_feature_packet_config", None) != identity:
            self._window_feature_packets = load_window_packet_binding(
                self._composed.values, self._samples, self._data_root, self._repo_root,
            )
            self._window_feature_packet_config = identity
        return self._window_feature_packets

    def _promotion_receipt_path(self) -> Path:
        value = self._composed.values.get("speech_packet_promotion_receipt")
        if not isinstance(value, str) or not value:
            raise FlightRuntimeError(
                f"arm {self._arm()!r} travels the speech-feature packet path; its "
                "baseline fragment must declare 'speech_packet_promotion_receipt' "
                "(the promotion receipt a registered SAEA-SN-*-PREPROCESS pass wrote)"
            )
        return Path(value)

    def _load_promotion_receipt(self) -> Mapping[str, object]:
        if self._promotion_receipt is None:
            self._promotion_receipt = load_promotion_receipt(self._promotion_receipt_path())
        return self._promotion_receipt

    def speech_packet_bindings(self) -> Mapping[str, Mapping[str, str]]:
        """``{sample_id: {"packet_id": ..., "sha256": ...}}`` for exactly
        this flight's samples, read from the registered promotion receipt.

        This is the binding ``rails.core_client.FrozenCoreClient`` refuses to
        be constructed without for a speech-feature arm, and which nothing
        previously supplied on this path. Fails closed on any sample the
        receipt does not cover -- promotion is a prerequisite, never
        something a flight silently completes for itself.
        """

        promotion = self._load_promotion_receipt()
        registered: dict[str, str] = {}
        for entry in promotion["packets"]:
            if not isinstance(entry, Mapping):
                raise FlightRuntimeError("promotion receipt packet entry must be an object")
            packet_id = entry.get("packet_id")
            packet_sha256 = entry.get("packet_sha256")
            if not isinstance(packet_id, str) or not isinstance(packet_sha256, str):
                raise FlightRuntimeError(
                    "promotion receipt packet entry must carry packet_id and packet_sha256"
                )
            registered[packet_id] = packet_sha256
        bindings: dict[str, Mapping[str, str]] = {}
        missing: list[str] = []
        for sample in self._samples:
            packet_id = packet_id_for_sample(sample.sample_id)
            sha256 = registered.get(packet_id)
            if sha256 is None:
                missing.append(sample.sample_id)
                continue
            bindings[sample.sample_id] = {"packet_id": packet_id, "sha256": sha256}
        if missing:
            raise FlightRuntimeError(
                f"{len(missing)} sample(s) have no promoted packet in "
                f"{self._promotion_receipt_path()}, e.g. {sorted(missing)[:5]}"
            )
        return bindings

    def _speech_feature_root(self) -> Path:
        value = self._composed.values.get("speech_feature_root")
        if not isinstance(value, str) or not value:
            raise FlightRuntimeError(
                f"arm {self._arm()!r} travels the speech-feature packet path; its "
                "model fragment must declare 'speech_feature_root'"
            )
        root = Path(value)
        window_packets = self.window_feature_packet_binding()
        promotion_root = (
            Path(window_packets.feature_root) if window_packets is not None
            else Path(str(self._load_promotion_receipt()["feature_root"]))
        )
        if root != promotion_root:
            raise FlightRuntimeError(
                f"model fragment speech_feature_root {root} disagrees with the "
                f"promotion receipt's feature_root {promotion_root}; refusing to "
                "serve packets from a root this flight's identity does not pin"
            )
        return root

    def _builtin_packet_promoter(
        self, *, adapter: TaskAdapter, data_root: Path, samples: Sequence[object], workers: int
    ) -> tuple[Sequence[object], Mapping[str, object]]:
        """The config-driven default promoter (replaces the fail-closed
        :func:`_default_packet_promoter` whenever the constructor was not
        given an explicit one).

        Raw-audio arms promote nothing and say so: their audio travels
        through the mmproj at request time, so a packet plane would be a
        fiction. Speech-feature arms re-materialize exactly the packets the
        registered promotion receipt already pins, through the same
        carrier-neutral primitive ``scripts/a2t_g1_preprocess.py`` used to
        write it (``core.model.speech_features.
        materialize_legacy_cached_speech_feature_packets``), and every
        promoted packet's SHA-256 is checked against that receipt -- so this
        stage can only ever reproduce a registered promotion, never invent
        an unregistered one.
        """

        if not self.uses_speech_feature_packets():
            return (), {
                "audio_path": "raw-audio-mmproj",
                "packets_required": False,
                "reason": (
                    "this arm's D2 field set carries no speech_feature_parts; its audio "
                    "travels through the mmproj at request time and no packet is promoted"
                ),
            }
        window_packets = self.window_feature_packet_binding()
        if window_packets is not None:
            return tuple(sorted({entry.packet_id for entry in window_packets.bindings})), {
                "audio_path": "mmproj-free-window-speech-feature-packets",
                "packets_required": True,
                "feature_root": window_packets.feature_root,
                "prepared_window_feature_packets": dict(
                    self._composed.values["prepared_window_feature_packets"]
                ),
                "request_count": window_packets.request_count,
                "new_encoder_contacts": 0,
            }
        promotion = self._load_promotion_receipt()
        feature_root = self._speech_feature_root()
        legacy_cache_dir = Path(str(promotion["legacy_cache_dir"]))
        registered = {
            str(entry["packet_id"]): entry for entry in promotion["packets"]
        }
        first = promotion["packets"][0]
        bindings = tuple(
            {
                "packet_id": packet_id_for_sample(sample.sample_id),
                "audio_path": str(Path(data_root) / sample.media_relpath),
            }
            for sample in samples
        )
        packets = materialize_legacy_cached_speech_feature_packets(
            feature_root=feature_root,
            bindings=bindings,
            legacy_cache_dir=legacy_cache_dir,
            encoder_receipt_sha256=str(promotion["runtime_receipt_sha256"]),
            decoder_gguf_sha256=str(first["decoder_gguf_sha256"]),
            mmproj_sha256=str(first["mmproj_sha256"]),
            expected_n_embd=SPEECH_PACKET_N_EMBD,
            causal_attention=True,
            workers=workers,
        )
        for packet in packets:
            entry = registered.get(packet.packet_id)
            if entry is None or entry.get("packet_sha256") != packet.packet_sha256:
                raise FlightRuntimeError(
                    f"promoted packet {packet.packet_id} does not match the registered "
                    f"promotion receipt {self._promotion_receipt_path()}"
                )
        return tuple(packet.packet_id for packet in packets), {
            "audio_path": "mmproj-free-speech-feature-packets",
            "packets_required": True,
            "feature_root": str(feature_root),
            "legacy_cache_dir": str(legacy_cache_dir),
            "promotion_receipt": str(self._promotion_receipt_path()),
            "promotion_receipt_sha256": _sha256_file(self._promotion_receipt_path()),
        }

    def preprocess(self, *, workers: int | None = None) -> Mapping[str, object]:
        """Run the adapter's ``preprocess_plan()`` through the packet
        promotion seam (defaults to a fail-closed placeholder; a real flight
        injects one wrapping ``core.model.speech_features.
        materialize_legacy_cached_speech_feature_packets`` -- see
        :func:`_default_packet_promoter`). ``workers`` overrides the plan's
        own declared worker count when given; either way, workers are
        capped to 8 whenever this runtime was constructed with
        ``campaign_active=True`` (owner rule: cap CPU preprocessing
        parallelism to 8 while a GPU campaign flies)."""

        self._require_prior_stages("preprocess")
        plan_declaration = self._adapter.preprocess_plan()
        if not isinstance(plan_declaration, Mapping) or "workers" not in plan_declaration:
            raise FlightRuntimeError("adapter.preprocess_plan() must declare a 'workers' field")
        declared_workers = plan_declaration["workers"]
        resolved_workers = declared_workers if workers is None else workers
        if isinstance(resolved_workers, bool) or not isinstance(resolved_workers, int) or resolved_workers <= 0:
            raise FlightRuntimeError("preprocess workers must be a positive integer")
        if self._campaign_active:
            resolved_workers = min(resolved_workers, 8)

        started = self._clock()
        packets, promoter_meta = self._packet_promoter(
            adapter=self._adapter,
            data_root=self._data_root,
            samples=self._samples,
            workers=resolved_workers,
        )
        duration = max(self._clock() - started, 1e-9)
        packet_validation_seconds = 0.0
        if self.uses_speech_feature_packets() and self.window_feature_packet_binding() is None:
            from ...rails.core_client import validate_speech_packet_set

            values = self._composed.values
            carrier_root = self._carrier_root_resolver(
                self._lock, self._plan.carrier_lock_key, self._data_root
            )
            binding = self._payload_binding_factory(
                carrier_lock_key=self._plan.carrier_lock_key,
                samples=self._samples,
                data_root=self._data_root,
                carrier_root=carrier_root,
                derived_media_roots=declared_derived_media_roots(values, self._data_root),
            )
            if isinstance(binding, PayloadBindingContext):
                validation_started = self._clock()
                self._validated_packet_set = validate_speech_packet_set(
                    self._speech_feature_root(), self.speech_packet_bindings(), binding,
                    workers=resolved_workers,
                )
                packet_validation_seconds = max(
                    self._clock() - validation_started, 1e-9
                )
        packet_count = len(packets)
        packets_per_second = packet_count / duration
        manifest_hash = _canonical_hash({"packets": sorted(str(packet) for packet in packets)})

        payload = {
            "kind": plan_declaration.get("kind"),
            "workers_declared": declared_workers,
            "workers_used": resolved_workers,
            "campaign_active": self._campaign_active,
            "packet_count": packet_count,
            "packet_manifest_hash": manifest_hash,
            "duration_seconds": duration,
            "packet_validation_seconds": packet_validation_seconds,
            "packets_per_second": packets_per_second,
            "promoter_meta": dict(promoter_meta) if isinstance(promoter_meta, Mapping) else {},
        }
        require_mandatory_throughput_fields("preprocess", payload, ("packets_per_second",))
        return self.receipts.record("preprocess", payload)

    # -- stage 3: serve -----------------------------------------------------

    def serve(self, *, reuse: "FlightRuntime | None" = None) -> Mapping[str, object]:
        """Start (or reuse) the resident server for ``adapter.
        serving_geometry()`` -- ``slots`` becomes ``-np``, ``slot_tokens *
        slots`` becomes ``-c``. When ``reuse`` names another
        :class:`FlightRuntime` that has already served, its session and
        transport are reused ONLY when the two flights' serving geometries
        agree (:class:`FlightServeGeometryMismatchError` otherwise -- a
        :class:`~.queue.FlightQueue` uses this to restart the server only on
        a genuine geometry change, never merely because a different flight
        is also ready). A fresh spawn re-checks ``gate.
        assert_model_touch_allowed`` immediately beforehand (the gate's own
        documented invariant: the process that opens the gate must be the
        process that starts llama-server, immediately afterward) -- calling
        it a second time (after :meth:`preflight` already called it once) is
        cheap: ``contracts.FrozenCoreGate`` caches the expensive GGUF
        full-hash check per process."""

        self._require_prior_stages("serve")
        self.assert_generation_lease()
        geometry = dict(self._adapter.serving_geometry())

        # Workers reattach through pinned session verification even for in-process reuse.
        if self._execution_policy is not None:
            reuse = None
        if reuse is not None:
            if not isinstance(reuse, FlightRuntime):
                raise FlightRuntimeError("serve(reuse=...) must be another FlightRuntime")
            reuse_geometry = dict(reuse.adapter.serving_geometry())
            server_geometry = {
                key: geometry[key] for key in ("slots", "slot_tokens")
            }
            reuse_server_geometry = {
                key: reuse_geometry[key] for key in ("slots", "slot_tokens")
            }
            if reuse_server_geometry != server_geometry:
                raise FlightServeGeometryMismatchError(
                    f"cannot reuse a server serving geometry {reuse_geometry} for a "
                    f"flight whose adapter declares geometry {geometry}"
                )
            if reuse._session is None or reuse._transport is None:
                raise FlightRuntimeError("serve(reuse=...) target has not itself served yet")
            fingerprint = self.serving_profile_fingerprint()
            if fingerprint != reuse._serve_fingerprint:
                raise FlightRuntimeError("cannot reuse a server with a different full identity")
            self._gate_touch(self._gate, self._plan)
            self._serve_fingerprint = fingerprint
            self._session = reuse._session
            self._transport = reuse._transport
            self._runtime_receipt = reuse._runtime_receipt
            self._session_receipt_path = reuse._session_receipt_path
            # A reused server belongs to the flight that started it; this
            # flight must never stop it out from under that owner.
            self._owns_session = False
            self._serving_session_dir = reuse._serving_session_dir
            self._serving_monitor_path = reuse._serving_monitor_path
            payload = {
                "reused_from_attempt_id": reuse.attempt_id,
                "session_id": self._session.session_id,
                "host": self._session.host,
                "port": self._session.port,
                "serving_geometry": geometry,
                "reused": True,
                "session_reused": True,
                "session_source": "in-process-reuse",
                "startup_seconds": 0.0,
            }
            return self.receipts.record("serve", payload)

        values = self._composed.values
        runtime_receipt = self._runtime_receipt_loader(
            resolve_runtime_receipt_path(self._repo_root, values)
        )
        self._runtime_receipt = runtime_receipt
        self._serve_fingerprint = self.serving_profile_fingerprint()
        self._gate_touch(self._gate, self._plan)

        # The fragment's own server_args, with ONLY -np/-c overridden from
        # the adapter geometry (:func:`merge_server_args`). Passing the two
        # derived flags alone -- what this stage used to do -- silently
        # dropped -ngl/-fa/-ctk/-ctv and every batch and cache flag the
        # fragment declares, i.e. served the flight on the CPU.
        extra_argv = merge_server_args(
            values.get("server_args", ()),
            slots=int(geometry["slots"]),
            context_tokens=int(geometry["slot_tokens"]) * int(geometry["slots"]),
        )
        extra_env_value = values.get("server_env", {})
        if not isinstance(extra_env_value, Mapping):
            raise FlightRuntimeError("model config server_env must be a mapping")
        session_id = f"{self._plan.run_id}-{self._plan.attempt_id}"
        run_dir = self._run_dir()
        run_dir.mkdir(parents=True, exist_ok=True)
        session_receipt_path = run_dir / f"{session_id}.session-receipt.json"
        server_log_path = run_dir / f"{session_id}.server.log"

        # ``role`` and ``model_root`` are read from the SAME two places the
        # rest of this study reads them: the runtime receipt's own ``role``
        # (an mmproj-free inference receipt declares ``"inference"``, which
        # is what makes ``start_session`` inject ``--no-mmproj``) and the
        # model fragment's ``model_materialization_root`` (where the GGUF
        # bytes actually live, e.g. /home/chao rather than the data root).
        # Both were previously ignored here, so a packet flight would have
        # been served WITH the mmproj and from the wrong model root.
        configured_model_root = model_materialization_root(values)

        # E7 (owner rule 2026-09-07): before spawning anything, look for the
        # coordinator's always-on serving session. Attaching is the normal
        # path on this host; spawning is the fallback for a host that has
        # none. A resident session that serves something ELSE is a refusal,
        # never a second spawn -- see FlightServingSessionMismatchError.
        attached = self._attach_resident_serving_session(
            geometry=geometry,
            values=values,
            runtime_receipt=runtime_receipt,
            extra_argv=extra_argv,
            extra_env=dict(extra_env_value),
            configured_model_root=configured_model_root,
            session_id=session_id,
            run_dir=run_dir,
        )
        if attached is not None:
            return attached

        started = self._clock()
        session = self._session_starter(
            runtime_root=self._runtime_root,
            data_root=self._data_root,
            runtime_receipt=runtime_receipt,
            host=self._host,
            port=self._port,
            session_id=session_id,
            extra_argv=extra_argv,
            extra_env=dict(extra_env_value),
            receipt_path=session_receipt_path,
            server_log_path=server_log_path,
            role=str(runtime_receipt.get("role", "legacy")),
            model_root=(
                Path(configured_model_root) if configured_model_root is not None else None
            ),
        )
        startup_seconds = max(self._clock() - started, 0.0)
        self._session = session
        self._session_receipt_path = session_receipt_path
        self._owns_session = True

        transport = build_configured_transport(
            values,
            self._data_root,
            repo_root=self._repo_root,
            session=session,
            runtime_receipt=runtime_receipt,
            runtime_root=self._runtime_root,
            transport_factory=self._transport_factory,
        )
        self._transport = transport

        payload = {
            "session_id": session.session_id,
            "host": session.host,
            "port": session.port,
            "pid": session.pid,
            "serving_geometry": geometry,
            "extra_argv": extra_argv,
            "session_role": str(runtime_receipt.get("role", "legacy")),
            "model_root": (
                str(configured_model_root) if configured_model_root is not None else None
            ),
            "startup_seconds": startup_seconds,
            "reused": False,
            "session_reused": False,
            "session_source": "spawned",
        }
        return self.receipts.record("serve", payload)

    # -- stage 3a: the always-on serving session (E7) -----------------------

    @property
    def execution_policy(self) -> WorkerExecutionPolicy | None:
        return self._execution_policy

    def bind_execution_policy(self, policy: WorkerExecutionPolicy) -> None:
        """Bind one coordinator capability before serving; never replace an active one."""
        if self._session is not None or self._execution_policy is not None:
            raise FlightRuntimeError("worker execution policy is already bound or serving")
        if not isinstance(policy, WorkerExecutionPolicy):
            raise FlightRuntimeError("worker execution policy must be a WorkerExecutionPolicy")
        self._execution_policy = policy

    def assert_generation_lease(self) -> None:
        """Revalidate root custody immediately before attachment or generation."""
        if self._execution_policy is not None:
            self._execution_policy.assert_lease(
                self._data_root, run_id=self.run_id, attempt_id=self.attempt_id,
            )

    def serving_profile_fingerprint(self) -> str:
        """Hash every declared input that builds the pinned serving identity.

        This is model-free and also usable for queue grouping. The attach path
        additionally verifies the resulting binary/model/process identity.
        """
        from ..config import fragment_hash, read_fragment

        if self._composed is None:
            raise FlightRuntimeError("preflight must precede serving profile inspection")
        values = self._composed.values
        geometry = dict(self.adapter.serving_geometry())
        receipt = self._runtime_receipt_loader(
            resolve_runtime_receipt_path(self._repo_root, values)
        )
        identity_inputs = {
            "model_fragment": self._model,
            "model_fragment_sha256": fragment_hash(read_fragment(self._repo_root, "model", self._model)),
            "runtime_receipt_relpath": runtime_receipt_relpath(values),
            "runtime_receipt": receipt,
            "runtime_root": str(self._runtime_root.resolve()),
            "data_root": str(self._data_root.resolve()),
            "model_root": model_materialization_root(values),
            "server_argv": merge_server_args(
                values.get("server_args", ()), slots=int(geometry["slots"]),
                context_tokens=int(geometry["slots"]) * int(geometry["slot_tokens"]),
            ),
            "server_env": values.get("server_env", {}),
            "host": self._host, "port": self._port,
        }
        return hashlib.sha256(json.dumps(
            identity_inputs, sort_keys=True, separators=(",", ":"), default=str,
        ).encode()).hexdigest()

    def session_required_identity(self) -> Mapping[str, object]:
        """Build the full pinned identity for root startup and attach-only fitting."""
        if self._composed is None:
            self._prepare()
        values = self._composed.values
        geometry = dict(self.adapter.serving_geometry())
        receipt = self._runtime_receipt_loader(
            resolve_runtime_receipt_path(self._repo_root, values)
        )
        return self._required_serving_identity(
            values=values, runtime_receipt=receipt, geometry=geometry,
            extra_argv=merge_server_args(
                values.get("server_args", ()), slots=int(geometry["slots"]),
                context_tokens=int(geometry["slots"]) * int(geometry["slot_tokens"]),
            ), extra_env=values.get("server_env", {}),
            configured_model_root=model_materialization_root(values),
        )

    def _required_serving_identity(
        self,
        *,
        values: Mapping[str, object],
        runtime_receipt: Mapping[str, object],
        geometry: Mapping[str, object],
        extra_argv: Sequence[str],
        extra_env: Mapping[str, str],
        configured_model_root: str | None,
    ) -> Mapping[str, object]:
        """What a resident serving session must BE for this flight to attach.

        Built from exactly the values ``serve`` would otherwise spawn with --
        the same ``core.session.build_server_command`` argv (so ``-c``,
        ``-np``, ``-ngl``, ``--mmproj`` and the model paths are compared as
        the command line they actually are), the same runtime receipt bytes,
        the same role/model root, the same ``server_env``, the same
        host/port -- plus the two ``GET /props`` facts a flight CAN derive
        (``total_slots`` and the per-slot ``n_ctx``), which is the live
        server's own account of the geometry it is serving.
        """

        from ..config import fragment_hash, read_fragment  # noqa: PLC0415 (light-import discipline)
        from ..session import build_server_command  # noqa: PLC0415 (light-import discipline)
        from ..session.paths import _sha256_file as _hash_file  # noqa: PLC0415

        fragment = read_fragment(self._repo_root, "model", self._model)
        receipt_path = resolve_runtime_receipt_path(self._repo_root, values)
        command = build_server_command(
            runtime_root=self._runtime_root,
            data_root=self._data_root,
            runtime_receipt=runtime_receipt,
            host=self._host,
            port=self._port,
            extra_argv=tuple(extra_argv),
            extra_env=extra_env,
            role=str(runtime_receipt.get("role", "legacy")),
            model_root=(
                Path(configured_model_root) if configured_model_root is not None else None
            ),
        )
        model_argv = list(command.argv)
        model_path = model_argv[model_argv.index("-m") + 1] if "-m" in model_argv else None
        return serving_identity(
            model_fragment=self._model,
            model_fragment_sha256=fragment_hash(fragment),
            runtime_receipt_relpath=runtime_receipt_relpath(values),
            runtime_receipt_sha256=_hash_file(receipt_path),
            binary_path=command.binary_path,
            binary_sha256=command.binary_sha256,
            model_files=[
                {"path": entry.path, "sha256": entry.sha256} for entry in command.model_files
            ],
            session_role=str(runtime_receipt.get("role", "legacy")),
            model_root=configured_model_root,
            server_argv=command.argv,
            server_env=extra_env,
            host=self._host,
            port=self._port,
            props={
                "total_slots": int(geometry["slots"]),
                "default_generation_settings": {"n_ctx": int(geometry["slot_tokens"])},
                "model_path": model_path,
            },
        )

    def _attach_resident_serving_session(
        self,
        *,
        geometry: Mapping[str, object],
        values: Mapping[str, object],
        runtime_receipt: Mapping[str, object],
        extra_argv: Sequence[str],
        extra_env: Mapping[str, str],
        configured_model_root: str | None,
        session_id: str,
        run_dir: Path,
    ) -> Mapping[str, object] | None:
        """Bind this flight to the coordinator's always-on server, or return
        ``None`` when there is none to bind to.

        Never stops what it attaches to (``_owns_session`` stays false, so
        :meth:`stop_serving` is a no-op for this flight): the session belongs
        to the coordinator's foreground wrapper, and an agent that stopped it
        would take the GPU away from every other queued flight -- the exact
        waste this enabler exists to remove.
        """

        resident = self._serving_session_finder(self._data_root)
        if resident is None:
            if self._execution_policy is not None:
                from .lease import GenerationLeaseError
                raise GenerationLeaseError("required resident session is absent; worker cannot start it")
            return None
        session_dir, document = resident
        session_dir = Path(session_dir)
        required = self._required_serving_identity(
            values=values,
            runtime_receipt=runtime_receipt,
            geometry=geometry,
            extra_argv=extra_argv,
            extra_env=extra_env,
            configured_model_root=configured_model_root,
        )
        try:
            assert_identity_matches(document, required)
        except ServingSessionError as error:
            raise FlightServingSessionMismatchError(
                str(error), getattr(error, "mismatches", ())
            ) from error

        if self._execution_policy is not None:
            from ..session.worker import attach_worker_session
            session_dir, document, session = attach_worker_session(
                policy=self._execution_policy, data_root=self._data_root,
                run_id=self.run_id, attempt_id=self.attempt_id,
                required_identity=required, runtime_receipt=runtime_receipt,
                runtime_root=self._runtime_root, finder=self._serving_session_finder,
                attacher=self._session_attacher,
            )
        else:
            session = self._session_attacher(
                session_dir / SESSION_RECEIPT_NAME,
                runtime_receipt=runtime_receipt,
                runtime_root=self._runtime_root,
            )
        self._session = session
        self._owns_session = False
        self._session_receipt_path = session_dir / SESSION_RECEIPT_NAME
        self._serving_session_dir = session_dir
        self._serving_monitor_path = session_dir / MONITOR_JSONL_NAME

        self._transport = build_configured_transport(
            values,
            self._data_root,
            repo_root=self._repo_root,
            session=session,
            runtime_receipt=runtime_receipt,
            runtime_root=self._runtime_root,
            transport_factory=self._transport_factory,
        )

        if self._execution_policy is not None:
            from ..session.worker import LeaseCheckedTransport
            self._transport = LeaseCheckedTransport(self._transport, self.assert_generation_lease)

        serving_session_id = str(document.get("session_id"))
        self._session_attach_receipt_path = (
            run_dir / f"{session_id}.session-attach-receipt.json"
        )
        self._session_attach_receipt = {
            "schema": SESSION_ATTACH_RECEIPT_SCHEMA,
            "study": STUDY_SLUG,
            "run_id": self._plan.run_id,
            "attempt_id": self._plan.attempt_id,
            "session_reused": True,
            "session_source": "attached-serving-session",
            "session_id": serving_session_id,
            "serving_session_dir": str(session_dir),
            "serving_session_pid": document.get("pid"),
            "serving_session_started_at": document.get("started_at"),
            "session_receipt_path": str(self._session_receipt_path),
            "monitor_path": str(self._serving_monitor_path),
            "serving_geometry": dict(geometry),
            "identity": dict(required),
            "attached_at": self._clock(),
            # Filled by seal(): the monitor summary between this attempt's
            # first and last contact.
            "monitor_summary": None,
        }
        self._write_session_attach_receipt()

        payload = {
            "session_id": serving_session_id,
            "host": session.host,
            "port": session.port,
            "pid": session.pid,
            "serving_geometry": dict(geometry),
            "extra_argv": list(extra_argv),
            "session_role": str(runtime_receipt.get("role", "legacy")),
            "model_root": (
                str(configured_model_root) if configured_model_root is not None else None
            ),
            "startup_seconds": 0.0,
            "reused": True,
            "session_reused": True,
            "session_source": "attached-serving-session",
            "serving_session_dir": str(session_dir),
            "monitor_path": str(self._serving_monitor_path),
            "session_attach_receipt_path": str(self._session_attach_receipt_path),
        }
        return self.receipts.record("serve", payload)

    def _write_session_attach_receipt(self) -> None:
        if self._session_attach_receipt_path is None or self._session_attach_receipt is None:
            return
        path = self._session_attach_receipt_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                self._session_attach_receipt,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
                default=str,
            )
            + "\n",
            encoding="utf-8",
            newline="\n",
        )

    def serving_monitor_summary(self) -> Mapping[str, object] | None:
        """The always-on session's monitor summary between this attempt's
        first and last contact, or ``None`` when this flight did not attach
        to a serving session (or made no contact at all).

        ``core.session.serving.summarize_monitor_file`` in-process, over the
        JSONL ``scripts/serving_monitor.py`` is appending to -- no second
        implementation of the parked/active accounting, and no subprocess.
        """

        if self._serving_monitor_path is None or self._contact_window is None:
            return None
        first, last = self._contact_window
        return summarize_monitor_file(
            self._serving_monitor_path, from_epoch=first, to_epoch=last
        )

    def stop_serving(self) -> Mapping[str, object] | None:
        """Stop the resident server THIS flight started, with its own stop
        receipt (``core.session.stop_session``, which re-verifies process
        identity and socket ownership before SIGTERM -- never a broad
        ``pkill``).

        Returns ``None``, and stops nothing, when this flight never served
        or merely reused another flight's server: a reused server belongs to
        the flight that started it.

        This exists because :meth:`serve` had no counterpart. A flight left
        an 18.5 GB llama-server resident for the life of the process (and
        orphaned it afterwards), so a second serving geometry could not get
        the VRAM to start -- exactly the situation a two-geometry factorial
        walks into. ``FlightQueue`` calls this on a genuine geometry change
        and from ``shutdown()``.

        TWO independent guards, not one (E7b defect 3, 2026-09-07): a flight
        that ATTACHED must never stop the coordinator's server, and the cost
        of getting that wrong is every other queued flight's GPU time, so
        ``_serving_session_dir`` is checked beside ``_owns_session`` rather
        than trusting a single boolean that some future ``serve`` path could
        set. The two can only disagree through a bug, which is the point.
        """

        if self._session is None or not self._owns_session:
            return None
        if self._serving_session_dir is not None:  # pragma: no cover -- guard
            raise FlightRuntimeError(
                "refusing to stop the always-on serving session at "
                f"{self._serving_session_dir}: this flight attached to it and does not "
                "own it (a flight that stops the coordinator's server takes the GPU "
                "away from every other queued flight)"
            )
        receipt_path = (
            self._session_receipt_path.with_name(
                self._session_receipt_path.name.replace(
                    ".session-receipt.json", ".session-stop-receipt.json"
                )
            )
            if self._session_receipt_path is not None
            else None
        )
        stop_receipt = self._session_stopper(
            self._session,
            runtime_receipt=self._runtime_receipt,
            runtime_root=self._runtime_root,
            receipt_path=receipt_path,
            force_after_timeout=True,
        )
        self._owns_session = False
        self._session = None
        self._transport = None
        return stop_receipt

    # -- stage 4: run_phases ------------------------------------------------

    def frozen_core_client_kwargs(
        self,
        *,
        plan: ExecutionPlan | None = None,
        gate: object | None = None,
        transport: object | None = None,
        run_dir: Path | None = None,
    ) -> Mapping[str, object]:
        """Build the exact kwargs :meth:`run_phases` passes to
        ``client_factory`` (default: ``rails.core_client.FrozenCoreClient``)
        -- factored out so a test can inspect them without also driving a
        real (or fake) ``rails_runner``/``phase_runner`` call. Requires
        :meth:`preflight` and :meth:`serve` to have already run."""

        # Overrides exist for :meth:`wire_check`, which builds the SAME
        # kwargs against a fake gate/transport and a scratch plan; every
        # caller that passes none behaves exactly as before.
        plan = plan if plan is not None else self._plan
        gate = gate if gate is not None else self._gate
        transport = transport if transport is not None else self._transport
        if plan is None or gate is None or transport is None:
            raise FlightStageOrderError(
                "frozen_core_client_kwargs() requires preflight() and serve() to have run"
            )
        baseline_values = self._composed.values
        arm = baseline_values.get("arm")
        if not isinstance(arm, str) or not arm:
            raise FlightRuntimeError("baseline fragment must declare a non-empty 'arm'")
        carrier_root = self._carrier_root_resolver(self._lock, plan.carrier_lock_key, self._data_root)
        binding = self._payload_binding_factory(
            carrier_lock_key=plan.carrier_lock_key,
            samples=self._samples,
            data_root=self._data_root,
            carrier_root=carrier_root,
            # DERIVED-MEDIA CONFINEMENT: whatever derived media roots the
            # composed fragment declares (and pins to a D1 media supplement)
            # become legal alongside the carrier root, so a media-variant
            # population binds without moving its files or rewriting its
            # roster. Empty -- hence inert -- for every fragment without such
            # a key.
            derived_media_roots=declared_derived_media_roots(
                baseline_values, self._data_root
            ),
        )
        self._binding = binding
        kwargs: dict[str, object] = {
            "plan": plan,
            "gate": gate,
            "transport": transport,
            "run_dir": run_dir if run_dir is not None else self._run_dir(),
            "binding": binding,
            "arm": arm,
            "request_id_prefix": self._request_id_prefix,
        }
        arm_fields = ARM_VISIBLE_FIELDS.get(arm, ())
        if "tool_schemas" in arm_fields:
            fill_name = baseline_values.get("tool_schema_fill")
            if self._tool_schema_resolver is None or not isinstance(fill_name, str):
                raise FlightRuntimeError(
                    f"arm {arm!r} declares tool_schemas; a tool_schema_resolver seam and "
                    "a baseline 'tool_schema_fill' name are both required"
                )
            kwargs["tool_schemas"] = self._tool_schema_resolver(self._lock, self._data_root, fill_name)
        if SPEECH_FEATURE_ARM_FIELD in arm_fields:
            # rails.core_client.FrozenCoreClient REFUSES to be constructed
            # for a speech-feature arm without these two -- and nothing on
            # this path supplied them, so every packet cell used to die at
            # client construction. Both are config/receipt derived: the root
            # from the model fragment (cross-checked against the promotion
            # receipt), the per-sample descriptors from that same receipt.
            kwargs["speech_feature_root"] = self._speech_feature_root()
            kwargs["speech_packet_bindings"] = self.speech_packet_bindings()
            if self._validated_packet_set is not None:
                kwargs["validated_packet_set"] = self._validated_packet_set
        if CONSTRUCTION_VISIBLE_FIELD in arm_fields:
            # rails.core_client.FrozenCoreClient REFUSES to be constructed for
            # a construction-proposer arm without its targets, and binds them
            # ONCE for the client's whole life. The UNION of every draw's own
            # declared targets is bound here; each request then names the
            # ordered SUBSET its own draw showed, which can only ever narrow
            # what the core sees (FrozenCoreClient._selected_construction_
            # targets). This is what closes the gap the EVO-A1 preregistration
            # section 12 item 9 named a blocker: before it, no config could
            # reach this arm at all.
            kwargs["construction_targets"] = [
                dict(entry) for entry in self.construction_material().bound_targets
            ]
        return kwargs

    def _decoding_params(self) -> Mapping[str, object] | None:
        """The composed ``decoding_params``, with the slot-affinity sentinel
        resolved (see :data:`SLOT_AFFINITY_SENTINEL`).

        Passing the sentinel through unresolved is not a cosmetic slip: the
        frozen-core adapter refuses it ("id_slot must be a non-negative
        integer"), so every cell of a flight whose model fragment declares
        it dies at its first contact.
        """

        value = effective_request_decoding_params(self._composed.values)
        if value is None:
            return None
        if not isinstance(value, Mapping):
            raise FlightRuntimeError("decoding_params must be a mapping when declared")
        resolved = dict(value)
        id_slot = resolved.get("id_slot")
        if id_slot == SLOT_AFFINITY_SENTINEL:
            resolved["id_slot"] = SEQUENTIAL_DISPATCH_SLOT
        elif id_slot is not None and (
            isinstance(id_slot, bool) or not isinstance(id_slot, int) or id_slot < 0
        ):
            raise FlightRuntimeError(
                "decoding_params.id_slot must be a non-negative integer or the "
                f"{SLOT_AFFINITY_SENTINEL!r} sentinel, got {id_slot!r}"
            )
        # Validate a declared per-sample max_tokens rule HERE, once, before any
        # sample is dispatched -- a malformed rule must not become 1,500
        # requests under a cap nobody intended. The rule OBJECT itself stays in
        # place; :meth:`_sample_decoding_params` is what turns it into an
        # integer, per request.
        self._max_tokens_rule(resolved)
        return resolved

    def _completion_token_ceiling(self) -> int:
        """Return the configured request cap used by preflight and fitting."""
        if self._composed.values.get("request_decoding_overrides") is None:
            return int(self._adapter.serving_geometry()["max_tokens"])
        decoding = self._decoding_params() or {}
        maximum = decoding.get("max_tokens")
        if isinstance(maximum, int) and not isinstance(maximum, bool) and maximum > 0:
            return maximum
        return int(self._adapter.serving_geometry()["max_tokens"])

    def _max_tokens_rule(
        self, decoding_params: Mapping[str, object] | None
    ) -> tuple[object, Mapping[str, object]] | None:
        """``(policy, rule)`` when ``decoding_params.max_tokens`` declares a
        per-sample rule object, ``None`` when it is a plain integer or absent
        (see :data:`MAX_TOKENS_POLICY_KEY`).

        Refuses anything else, and refuses an unregistered policy id: those are
        the two ways a cell could otherwise reach the wire with a cap that was
        silently ignored.
        """

        if decoding_params is None or "max_tokens" not in decoding_params:
            return None
        declared = decoding_params["max_tokens"]
        if isinstance(declared, bool):
            raise FlightRuntimeError(
                f"decoding_params.max_tokens must be an integer or a per-sample rule "
                f"object, got {declared!r}"
            )
        if isinstance(declared, int):
            return None
        if not isinstance(declared, Mapping):
            raise FlightRuntimeError(
                f"decoding_params.max_tokens must be an integer or a per-sample rule "
                f"object, got {declared!r}"
            )
        policy_id = declared.get(MAX_TOKENS_POLICY_KEY)
        if not isinstance(policy_id, str) or not policy_id:
            raise FlightRuntimeError(
                "a per-sample decoding_params.max_tokens rule must name a "
                f"{MAX_TOKENS_POLICY_KEY!r} registered in core.base.MAX_TOKENS_POLICIES"
            )
        # Function-local: importing core.policies is what POPULATES
        # core.base.MAX_TOKENS_POLICIES (the registration lives beside the
        # implementation, in the one canonical policy-registration site), and
        # this module deliberately does not import core.policies at module
        # scope.
        from .. import policies as _policies  # noqa: PLC0415, F401 (registration)

        try:
            policy = MAX_TOKENS_POLICIES.resolve(policy_id)
            policy.parameters(declared)
        except CoreError as error:
            raise FlightRuntimeError(str(error)) from None
        return policy, declared

    def _sample_decoding_params(
        self, sample: object, decoding_params: Mapping[str, object] | None
    ) -> Mapping[str, object] | None:
        """``decoding_params`` with a per-sample ``max_tokens`` rule resolved to
        this sample's integer.

        Returns the argument UNCHANGED -- the same object, not a copy -- when no
        rule is declared, which is what makes every fragment that predates this
        seam render byte-identical requests.
        """

        binding = self._max_tokens_rule(decoding_params)
        if binding is None:
            return decoding_params
        policy, rule = binding
        audio_seconds = getattr(sample, "audio_seconds", None)
        try:
            cap = policy.resolve(rule, audio_seconds)
        except CoreError as error:
            raise FlightRuntimeError(
                f"sample {getattr(sample, 'sample_id', sample)!r}: {error}"
            ) from None
        resolved = dict(decoding_params or {})
        resolved["max_tokens"] = cap
        return resolved

    @staticmethod
    def _rows_from_direct_summary(summary: object) -> list[Mapping[str, object]]:
        rows: list[Mapping[str, object]] = []
        for result in summary.results:
            consumption = getattr(result, "consumption", None)
            rows.append(
                {
                    "arm": getattr(result, "arm", None),
                    "sample_id": result.sample_id,
                    "messages": list(getattr(result, "messages", ()) or ()),
                    "response_text": getattr(result, "response_text", None),
                    "metrics": dict(getattr(result, "metrics", {}) or {}),
                    "consumption": consumption.as_json() if consumption is not None else None,
                }
            )
        return rows

    def _speech_feature_trace_ids(self) -> tuple[str, str]:
        values = self._composed.values
        pair = (
            values.get("speech_feature_key_representation_id"),
            values.get("speech_feature_matcher_policy_id"),
        )
        for name, value in zip(
            ("speech_feature_key_representation_id", "speech_feature_matcher_policy_id"),
            pair,
            strict=True,
        ):
            if not isinstance(value, str) or not value:
                raise FlightRuntimeError(
                    f"arm {self._arm()!r} travels the speech-feature packet path; its "
                    f"baseline fragment must declare a non-empty {name!r} "
                    "(both ride the audited payload as ORG/CONTROL identity)"
                )
        return str(pair[0]), str(pair[1])

    def _speech_feature_contact(
        self, client: object, sample: object, decoding_params: Mapping[str, object] | None
    ) -> Mapping[str, object]:
        """One packet-path contact for one sample -- the unit both the
        serial and the concurrent dispatcher run, so the two can never
        disagree about what a contact is."""

        descriptor = self.speech_packet_bindings()[sample.sample_id]
        key_representation_id, matcher_policy_id = self._speech_feature_trace_ids()
        messages = (
            {"role": "system", "content": self._adapter.instruction(sample)},
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_speech_features",
                        "speech_features": {
                            "packet_id": descriptor["packet_id"],
                            "sha256": descriptor["sha256"],
                            "role": "query",
                        },
                    }
                ],
            },
        )
        response_text = client.complete(
            messages,
            decoding_params=decoding_params,
            speech_feature_sample_id=sample.sample_id,
            key_representation_id=key_representation_id,
            matcher_policy_id=matcher_policy_id,
        )
        return self._row_for(sample, messages, response_text)

    def _raw_audio_contact(
        self, client: object, sample: object, decoding_params: Mapping[str, object] | None
    ) -> Mapping[str, object]:
        """One raw-audio contact for one sample, assembled exactly as
        ``rails.runner._run_one_arm`` assembles it (same
        ``adapter.assemble_prompt(sample, None)`` zero-supply shape, same
        ``complete``, same post-hoc scoring). The serial path still goes
        through ``rails_runner`` itself so a ``workers=1`` flight is
        byte-identical to the sealed smoke; this exists for the concurrent
        path, which the serial runner cannot express."""

        messages = self._adapter.assemble_prompt(sample, None)
        response_text = client.complete(messages, decoding_params=decoding_params)
        return self._row_for(sample, messages, response_text)

    def _row_for(
        self, sample: object, messages: object, response_text: str
    ) -> Mapping[str, object]:
        consumption = self._adapter.extract_consumption(sample, None, response_text)
        return {
            "arm": self._arm(),
            "sample_id": sample.sample_id,
            "messages": list(messages),
            "response_text": response_text,
            "metrics": dict(self._adapter.score(sample, response_text)),
            "consumption": consumption.as_json() if consumption is not None else None,
        }

    def _dispatch_concurrent(
        self, client: object, *, workers: int
    ) -> tuple[list[Mapping[str, object]], dict[str, object]]:
        """Run one contact per sample across ``workers`` threads, each
        pinned to its own ``id_slot``.

        Invariants, and why each is what it is:

        * **Exactly one contact per sample.** No batching of several samples
          into one prompt -- the arm under test is a one-contact direct
          baseline and merging prompts would change what is measured.
        * **A worker owns one slot for its whole life** (``0..workers-1``,
          taken once from a free-slot queue and never returned), so no two
          in-flight requests ever share a llama-server slot and the
          per-sample slot-affinity semantics the sentinel encodes are
          preserved by construction. For a one-contact policy that is the
          whole of affinity: a sample makes exactly one request, so
          "the sample's requests share a slot" is trivially true.
        * **At most ``workers`` requests in flight**, because the pool has
          exactly that many threads. Queue depth is therefore irrelevant
          here and is deliberately not a knob: with one contact per sample
          there is no second request behind a sample to pipeline, so the
          only thing a deeper queue could add is more in-flight requests
          than slots, which is exactly what the slot pinning forbids.
        * **Deterministic order.** Samples are handed out in
          ``self._samples`` order and results are collected back into that
          order, so the sealed outputs rows do not depend on completion
          timing.
        * **Trace safety, verified rather than assumed.**
          ``core.tracing.TraceSink.emit`` holds NO lock: it check-then-sets
          a dict and reopens the trace file per record, so concurrent
          workers must not write it directly. Each task therefore emits into
          its own ``core.tracing.TraceBuffer`` (bound through the contextvar
          ``set_current_trace_buffer``, which is per-thread), and the parent
          flushes those buffers one at a time, in sample order, through
          ``FrozenCoreClient.flush_trace_buffer`` -- which serializes on the
          client's own ``_state_lock``. The client's request counter and
          timings, and the adapter's budget and metering counters, ARE
          already lock-guarded (``_state_lock``/``_metering_lock``), which
          is why nothing else needs one here.
        * **A failure aborts cleanly.** Remaining work is cancelled and the
          first exception is re-raised, but every buffer that did complete
          is still flushed first, so the durable trace keeps what actually
          happened rather than losing it to the abort.
        """

        from concurrent.futures import ThreadPoolExecutor  # noqa: PLC0415
        from queue import Queue  # noqa: PLC0415

        if isinstance(workers, bool) or not isinstance(workers, int) or workers < 1:
            raise FlightRuntimeError("workers must be a positive integer")
        packets = self.uses_speech_feature_packets()
        contact = self._speech_feature_contact if packets else self._raw_audio_contact
        base_decoding = dict(self._decoding_params() or {})
        samples = tuple(self._samples)

        free_slots: "Queue[int]" = Queue()
        for slot in range(workers):
            free_slots.put(slot)
        thread_state = threading.local()
        in_flight = 0
        max_in_flight = 0
        slots_used: set[int] = set()
        meter = threading.Lock()
        buffers: dict[int, object] = {}
        make_buffer = getattr(client, "new_trace_buffer", None)

        def one(index: int, sample: object) -> Mapping[str, object]:
            nonlocal in_flight, max_in_flight
            slot = getattr(thread_state, "slot", None)
            if slot is None:
                slot = free_slots.get_nowait()
                thread_state.slot = slot
            with meter:
                in_flight += 1
                max_in_flight = max(max_in_flight, in_flight)
                slots_used.add(slot)
            buffer = None
            if callable(make_buffer):
                buffer = make_buffer()
                set_current_trace_buffer(buffer)
                buffers[index] = buffer
            try:
                decoding_params = dict(
                    self._sample_decoding_params(sample, base_decoding) or {}
                )
                decoding_params["id_slot"] = slot
                return contact(client, sample, decoding_params)
            finally:
                if buffer is not None:
                    set_current_trace_buffer(None)
                with meter:
                    in_flight -= 1

        rows: list[Mapping[str, object] | None] = [None] * len(samples)
        error: BaseException | None = None
        with ThreadPoolExecutor(
            max_workers=workers, thread_name_prefix="saea-flight-contact"
        ) as pool:
            futures = {
                pool.submit(one, index, sample): index
                for index, sample in enumerate(samples)
            }
            for future, index in futures.items():
                try:
                    rows[index] = future.result()
                except BaseException as failure:  # noqa: BLE001 -- re-raised below
                    if error is None:
                        error = failure
                    for pending in futures:
                        pending.cancel()

        # Flush in SAMPLE order, whatever the completion order was, and do it
        # even when a task failed so the durable trace keeps the contacts
        # that really happened.
        flush = getattr(client, "flush_trace_buffer", None)
        if callable(flush):
            for index in sorted(buffers):
                flush(buffers[index])
        if error is not None:
            raise error
        return list(rows), {
            "workers": workers,
            "max_in_flight": max_in_flight,
            "slot_ids_used": sorted(slots_used),
            "dispatch": "concurrent",
            "contacts_per_sample": 1,
            "queue_depth": (
                "not a knob: one contact per sample means nothing queues behind a "
                "sample, and more in-flight requests than slots is what the slot "
                "pinning exists to forbid"
            ),
        }

    def _run_speech_feature_direct(self, client: object) -> list[Mapping[str, object]]:
        """The fixed-policy direct arm for the speech-feature packet audio
        path: ONE contact per sample, carrying exactly one
        ``input_speech_features`` query descriptor.

        ``rails.runner.run_rails_experiment`` cannot carry this arm: it
        always calls ``core_client.complete(messages)`` under the AUDIO
        invariant, and ``FrozenCoreClient`` refuses a speech-feature arm
        without ``speech_feature_sample_id`` and a query packet ("speech-
        feature-query requires speech_feature_sample_id and a query packet
        on every decision call"). This is the SAME single contact, the same
        instruction from the same adapter, the same post-hoc scoring -- only
        the audio content part differs, which is precisely what Factor D of
        a raw-audio-versus-packets comparison is about. It adds no phase, no
        second contact and no evidence.
        """

        bindings = self.speech_packet_bindings()
        key_representation_id, matcher_policy_id = self._speech_feature_trace_ids()
        decoding_params = self._decoding_params()
        arm = self._arm()
        rows: list[Mapping[str, object]] = []
        for sample in self._samples:
            descriptor = bindings[sample.sample_id]
            messages = (
                {"role": "system", "content": self._adapter.instruction(sample)},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_speech_features",
                            "speech_features": {
                                "packet_id": descriptor["packet_id"],
                                "sha256": descriptor["sha256"],
                                "role": "query",
                            },
                        }
                    ],
                },
            )
            response_text = client.complete(
                messages,
                decoding_params=self._sample_decoding_params(sample, decoding_params),
                speech_feature_sample_id=sample.sample_id,
                key_representation_id=key_representation_id,
                matcher_policy_id=matcher_policy_id,
            )
            consumption = self._adapter.extract_consumption(sample, None, response_text)
            rows.append(
                {
                    "arm": arm,
                    "sample_id": sample.sample_id,
                    "messages": list(messages),
                    "response_text": response_text,
                    "metrics": dict(self._adapter.score(sample, response_text)),
                    "consumption": consumption.as_json() if consumption is not None else None,
                }
            )
        return rows

    @staticmethod
    def _phase_summary_contacts(summary: object) -> int:
        """How many model contacts one phase summary accounts for.

        ``rails.phase_runner.run_agent_phase`` already validates that every
        result of a phase carries exactly one contact, so this is normally
        ``len(summary.results)``; summing the contact tuples instead keeps
        the receipt honest if a future program ever runs a phase with a
        richer per-sample trajectory.
        """

        return sum(
            len(getattr(result, "contacts", ()) or ()) for result in summary.results
        )

    @staticmethod
    def _rows_from_phase_summaries(
        summaries: Sequence[object], *, policy: str
    ) -> list[Mapping[str, object]]:
        """ONE row per sample, carrying the LAST phase's response.

        A ``PhaseProgram`` answers a sample once: the program's final phase
        produces the text that stands (``rails.phase_runner.run_program``
        threads each phase's sealed state into the next, and
        ``rails.controllers.EvidenceAgentController`` keeps only the last
        phase's response as the trajectory's answer). Emitting one row per
        (phase, sample) -- what this used to do -- gave a two-phase program
        two rows per sample id, which ``core.bundle.outputs.seal`` then
        refused as duplicate sample ids AFTER every contact had been spent.

        Fails closed when the phases disagree about WHICH samples they ran:
        a program whose second phase silently dropped or added a row would
        otherwise seal the last phase's roster while the receipt counted
        contacts for another one, and the paired analysis downstream would
        be comparing manifests over different sample sets.
        """

        if not summaries:
            raise FlightRuntimeError(
                f"phase program {policy!r} returned no phase summaries; there is "
                "nothing to seal"
            )
        last = summaries[-1]
        last_ids = tuple(result.sample_id for result in last.results)
        if len(set(last_ids)) != len(last_ids):
            raise FlightRuntimeError(
                f"phase program {policy!r} final phase returned duplicate sample ids"
            )
        expected = set(last_ids)
        for index, summary in enumerate(summaries[:-1]):
            ids = {result.sample_id for result in summary.results}
            if ids != expected:
                phase_id = getattr(summary, "controller_policy_id", f"phase[{index}]")
                raise FlightRuntimeError(
                    f"phase program {policy!r} phase {phase_id!r} ran "
                    f"{len(ids)} sample(s) but its final phase ran {len(expected)}; "
                    f"symmetric difference {sorted(ids ^ expected)[:5]}. Every phase "
                    "of a program must run the same whole roster, or the sealed row "
                    "for a sample would carry a response the earlier phases never "
                    "conditioned on"
                )
        phase_id = getattr(last, "controller_policy_id", None)
        return [
            {
                "phase": phase_id,
                "sample_id": result.sample_id,
                "final_response_text": getattr(result, "final_response_text", None),
                "contact_count": len(getattr(result, "contacts", ()) or ()),
            }
            for result in last.results
        ]

    def _run_construction_proposer(
        self, client: object, decoding_params: Mapping[str, object] | None
    ) -> list[Mapping[str, object]]:
        """The fixed-policy direct arm for the TEXT-ONLY construction-proposer
        arm: ONE contact per DRAW, carrying that draw's rendered instruction
        and its own ordered exemplar ids, and no audio part at all.

        A thin sibling of :meth:`_run_speech_feature_direct`, and for the same
        reason: ``rails.runner.run_rails_experiment`` cannot carry this arm
        (it always calls ``core_client.complete(messages)`` under the AUDIO
        invariant, and ``FrozenCoreClient`` refuses a construction-proposer
        request that names no ``text_only_sample_id``). It adds no phase, no
        second contact and no evidence: the instruction is the system message,
        the user content list is EMPTY (a zero-supply arm has nowhere to
        record a free-floating user text part), and the audited payload
        carries the draw's own construction targets.

        Rows carry no metrics on purpose. A proposer answer is an ARTIFACT --
        a JSON object of tool descriptions -- not an answer to a scored row,
        so running the carrier's scorer over it would be scoring the wrong
        thing (and would need gold this sample has no business resolving).
        The candidates are produced afterwards, model-free, by
        ``rails.evolution.harvest_proposer_responses`` over the SEALED
        manifest.
        """

        material = self.construction_material()
        by_sample = material.by_sample()
        arm = self._arm()
        rows: list[Mapping[str, object]] = []
        for sample in self._samples:
            contact = by_sample.get(sample.sample_id)
            if contact is None:
                raise FlightRuntimeError(
                    f"sample {sample.sample_id!r} is in this flight's split but names no "
                    "draw in the proposer roster"
                )
            messages = (
                {"role": "system", "content": contact.instruction},
                {"role": "user", "content": []},
            )
            response_text = client.complete(
                messages,
                decoding_params=decoding_params,
                text_only_sample_id=sample.sample_id,
                construction_target_ids=contact.construction_target_ids,
            )
            rows.append(
                {
                    "arm": arm,
                    "sample_id": sample.sample_id,
                    "messages": list(messages),
                    "response_text": response_text,
                    "metrics": {},
                    "consumption": None,
                    "proposer_draw": contact.as_json(),
                }
            )
        return rows

    def _dispatch_fixed_policy(
        self, client: object, plan: ExecutionPlan, *, workers: int | None = None
    ) -> tuple[list[Mapping[str, object]], int, str, dict[str, object]]:
        """The ``policy == "fixed"`` dispatch, factored out so
        :meth:`wire_check` drives the SAME code path a real flight does --
        a wiring proof that ran its own copy of this would prove nothing
        about the flight."""

        baseline_values = self._composed.values
        if self.shows_construction_targets():
            # One contact per draw, serial: a proposer round makes at most
            # four contacts per target (twelve in round 1), so there is
            # nothing for a worker pool to overlap, and a serial dispatch
            # keeps the per-draw request order identical to the roster's.
            rows = self._run_construction_proposer(client, self._decoding_params())
            return (
                rows,
                len(rows),
                "direct-construction-proposer",
                {
                    "workers": 1,
                    "max_in_flight": 1,
                    "slot_ids_used": [SEQUENTIAL_DISPATCH_SLOT],
                    "dispatch": "serial",
                    "contacts_per_sample": 1,
                    "queue_depth": "not a knob for a one-contact text-only policy",
                },
            )
        packets = self.uses_speech_feature_packets()
        resolved = (
            int(self._adapter.serving_geometry()["slots"]) if workers is None else int(workers)
        )
        if resolved > 1:
            rows, dispatch = self._dispatch_concurrent(client, workers=resolved)
            kind = "direct-speech-feature-packets" if packets else "direct"
            return rows, len(rows), kind, dispatch
        serial = {
            "workers": 1,
            "max_in_flight": 1,
            "slot_ids_used": [SEQUENTIAL_DISPATCH_SLOT],
            "dispatch": "serial",
            "contacts_per_sample": 1,
            "queue_depth": "not a knob for a one-contact policy",
        }
        if packets:
            # Same fixed policy, same one contact per sample -- but through
            # the packet content part rails.runner cannot express (see
            # :meth:`_run_speech_feature_direct`).
            rows = self._run_speech_feature_direct(client)
            return rows, len(rows), "direct-speech-feature-packets", serial
        arms = tuple(baseline_values.get("rails_arms", RAILS_ARMS))
        base_decoding = self._decoding_params()
        summary = self._rails_runner(
            data_root=self._data_root,
            plan=plan,
            adapter=self._adapter,
            core_client=client,
            split_id=self._split_id,
            arms=arms,
            # A per-sample max_tokens rule reaches the SERIAL path as a
            # resolver, which ``rails.runner.run_rails_experiment`` calls once
            # per sample; with no rule declared this is the same mapping the
            # runner has always been handed, by identity, so a fragment that
            # predates the seam dispatches byte-identically.
            decoding_params=(
                base_decoding
                if self._max_tokens_rule(base_decoding) is None
                else (lambda sample: self._sample_decoding_params(sample, base_decoding))
            ),
        )
        return (
            self._rows_from_direct_summary(summary),
            len(summary.results),
            "direct",
            serial,
        )

    def _obs_policy_names(self) -> tuple[str, ...]:
        """The obs policies this harness dispatches through the obs driver.

        Function-local import: this module must not pull
        ``reproduction.obs_loop`` (librosa, the VAD engines) into every
        flight's import graph, and ``reproduction.ojw`` must stay behind the
        D2 lazy seam. Names only -- nothing openjiuwen-dependent is touched.
        """

        from ...reproduction.obs_loop import (  # noqa: PLC0415
            OBS_LOOP_POLICY_NAME,
        )
        from ...reproduction.ojw import OJW_OBS_POLICY_NAMES  # noqa: PLC0415
        from ...reproduction.repair_loop import (  # noqa: PLC0415
            OBS_REPAIR_LOOP_POLICY_NAME,
        )

        return (
            OBS_LOOP_POLICY_NAME,
            OBS_REPAIR_LOOP_POLICY_NAME,
            *OJW_OBS_POLICY_NAMES,
        )

    def _dispatch_obs_policy(
        self, plan: ExecutionPlan
    ) -> tuple[list[Mapping[str, object]], int, str, dict[str, object], RunResult]:
        """The Earnings carrier's dispatch: one whole-call sample -> N
        buffer-slice contacts -> one stitched hypothesis, run by the obs
        driver (owner Decision 12-F item #9, 2026-09-08).

        **This stage delegates; it does not reimplement.** ``core.driver.
        run_experiment`` is the ONE obs harness -- it resolves the run's
        evidence through ``core.evidence`` and proves its D1 identity and
        derivation chain, builds the per-run ``core.model.SliceRegistry`` the
        adapter enforces slice binding against, constructs the single
        ``core.model.FrozenCoreAdapter`` that reserves this attempt, emits the
        per-sample OBS/ORG/SUPPLY preamble, runs the prefetch pipeline when
        the fragment declares one, writes ``<run_id>.outputs.jsonl`` in the
        bundle contract's own field set, and closes its trace sink. A second
        copy of any of that inside this class would be exactly the parallel
        harness the owner's 2026-09-03 rule forbids, and would make an
        Earnings number produced here incomparable with the sealed Earnings
        numbers produced there.

        What FlightRuntime contributes is the envelope the obs driver never
        had: preflight (composition, split identity, the ExecutionPlan, the
        gate, the exposure-row re-check, the clean-tree assertion, the
        prompt-budget assessment), preprocess, serve/attach to the resident
        always-on session (E7), then seal and score once through
        ``core.scoring_batch``.

        Two deliberate differences from the phase-program dispatch:

        * **No ``FrozenCoreClient``.** The obs policy's single door is the
          adapter's ``request``; the client is the rails ``messages`` shim
          over that same adapter, and building one here would open the
          attempt twice.
        * **The ``id_slot`` sentinel is NOT pre-resolved.** ``_decoding_params``
          collapses it to slot 0 because the phase harness dispatches one
          contact at a time; the obs executors resolve it themselves, per
          sample, from the run's dispatch pool -- which is the whole point of
          per-sample slot affinity. The composed value therefore reaches the
          driver exactly as the fragment wrote it.
        """

        from ..driver.run import run_experiment  # noqa: PLC0415 (cycle guard)

        if self._transport is None:
            raise FlightStageOrderError(
                "an obs-policy dispatch requires serve() to have bound a transport"
            )
        run_dir = self._run_dir()
        run_dir.mkdir(parents=True, exist_ok=True)
        obs_runner = self._obs_runner if self._obs_runner is not None else run_experiment
        effective_values = effective_request_values(self._composed.values)
        obs_composed = self._composed
        if effective_values is not self._composed.values:
            obs_composed = type(self._composed)(
                values=effective_values,
                config_hash=self._composed.config_hash,
                fragments=self._composed.fragments,
            )
        result = obs_runner(
            obs_composed,
            plan,
            self._gate,
            self._lock,
            self._data_root,
            run_dir,
            self._transport,
            repo_root=self._repo_root,
        )
        rows = self._rows_from_obs_outputs(result)
        cost = dict(result.cost)
        calls_used = cost.get("calls_used")
        contact_count = int(calls_used) if isinstance(calls_used, (int, float)) else len(rows)
        dispatch = {
            # The obs driver's own shape, read back from the composed config
            # rather than guessed: how many samples of lookahead it kept, how
            # wide the run's dispatch pool was, and which executor cut.
            "dispatch": "obs-loop",
            "workers": int(self._composed.values.get("obs_batch_slices", 1) or 1),
            "obs_prefetch_depth": int(self._composed.values.get("obs_prefetch_depth", 0) or 0),
            "obs_batch_samples": int(self._composed.values.get("obs_batch_samples", 1) or 1),
            "contacts_per_sample": (
                contact_count / len(rows) if rows else 0.0
            ),
            "queue_depth": (
                "the obs driver's own: obs_prefetch_depth samples of lookahead "
                "over a run-wide ObsDispatcher"
            ),
        }
        return rows, contact_count, "obs-loop", dispatch, result

    def _rows_from_obs_outputs(self, result: RunResult) -> list[Mapping[str, object]]:
        """Read the obs driver's own sealed outputs rows back.

        ``core.driver.run.run_experiment`` writes exactly the field set
        ``core.bundle.outputs`` requires -- request_id, sample_id,
        carrier_lock_key, arm, text, admitted and the three identity hashes,
        the last three being the STITCH descriptors the obs policy computed
        over that sample's own per-window requests and responses. They are
        read back rather than rebuilt, because rebuilding them here would
        mean a second opinion about what a stitched hypothesis' identity is.
        """

        rows: list[Mapping[str, object]] = []
        text = Path(result.outputs_path).read_text(encoding="utf-8")
        for number, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except ValueError as error:
                raise FlightRuntimeError(
                    f"obs outputs line {number} is not JSON: {error}"
                ) from error
            missing = sorted(_OBS_OUTPUTS_FIELDS - set(row))
            if missing:
                raise FlightRuntimeError(
                    f"obs outputs line {number} lacks {missing}; the obs driver is "
                    "the authority for a stitched hypothesis' identity and this "
                    "stage refuses to invent it"
                )
            rows.append(row)
        return rows

    def _dispatch_phase_program(
        self, client: object, plan: ExecutionPlan, policy: str, *, model_free_check: bool = False
    ) -> tuple[
        list[Mapping[str, object]],
        int,
        str,
        dict[str, object],
        list[Mapping[str, object]],
    ]:
        """The ``policy != "fixed"`` dispatch, factored out for exactly the
        reason :meth:`_dispatch_fixed_policy` is: :meth:`wire_check` drives
        THIS code path, so a wiring proof of a phase program proves something
        about the flight rather than about a second copy of it."""

        from ..tracing import TraceBuffer  # noqa: PLC0415 (function-local, cheap)

        program = default_phase_program(policy)
        from ..preparation_fit import build_live_phase_fit_gate, validate_live_phase_fit_config
        live_fit_spec = validate_live_phase_fit_config(self._composed.values, program)
        whole_roster = live_fit_spec is not None
        live_fit_gate = None
        if whole_roster:
            if model_free_check:
                # Wire-check transport is synthetic. Record request identities
                # without claiming that any tokenizer capacity was measured.
                def live_fit_gate(phase, batch):
                    from ..preparation_fit import boundary_identity
                    live_fit_gate.receipts.append({
                        "phase": phase, "model_free_request_identity_only": True,
                        "boundary_sha256": boundary_identity(tuple(r.as_payload() for r in batch)),
                        "capacity_verified": False,
                    })
                live_fit_gate.receipts = []
            else:
                live_fit_gate = (self._live_phase_fit_factory or build_live_phase_fit_gate)(
                    self, program, plan
                )
        from ..bundle.delivery_replay import validate_phase_delivery_sources

        validate_phase_delivery_sources(
            self._composed.values, program=program, parent_fragments={
                "model_fragment": self._model,
                "dataset_fragment": self._dataset,
                "baseline_fragment": self._baseline,
            },
        )
        binding = self._phase_program_material
        if binding is None:
            # E1: a phase program whose material IS expressible in the
            # baseline fragment binds itself here, so a two-contact cell is a
            # config edit rather than a launcher script.
            # bind_phase_program_material(...) remains the explicit override
            # and, when it was called, wins outright.
            binding = self._default_phase_program_binding(program, client)
        # rails.runner.run_speech_native_agent_loop requires an append-only
        # AgentTraceSink BOUND TO plan.run_id. FrozenCoreClient is not one --
        # it owns a private TraceSink and exposes only flush_trace_buffer --
        # so the loop gets a TraceBuffer, exactly as every sealed AgentLoop
        # launcher in this study did, and it is flushed into the client's own
        # sink once the whole program has settled.
        sink = binding.get("trace_sink")
        if sink is None or sink is client:
            sink = TraceBuffer(plan.run_id)
        supply_for_phase = binding.get("supply_for_phase")
        supply_specs = binding.get("supply_specs") or {}
        review_for_phase = binding.get("review_for_phase")
        review_specs = binding.get("review_specs") or {}
        facet_seed, value_seed = self._phase_supply_seeds(
            program, binding, supply_specs, plan
        )
        # E6: a program with a supplied NON-FIRST phase must run as ONE
        # continuous trajectory. run_program executes each phase as its own
        # whole-roster max_contacts=1 wave, so a phase's controller never
        # reaches its own advance -- and advance is the only place a traced
        # acquire transition can be emitted (rails.controllers, "Traced
        # supply"). A program with no supply, or whose only supply is the
        # pre-flight-seeded FIRST phase, keeps the per-phase barrier form.
        continuous = whole_roster or bool(
            set(supply_specs) - {program.phase_names()[0]}
        )
        live_options = (
            {"whole_roster_wave_barrier": True, "request_batch_gate": live_fit_gate}
            if whole_roster else {}
        )
        try:
            if continuous:
                summaries = (
                    self._continuous_phase_runner(
                        program=program,
                        adapter=self._adapter,
                        plan=plan,
                        data_root=self._data_root,
                        core_client=client,
                        split_id=self._split_id,
                        knowledge_snapshot=binding["knowledge_snapshot"],
                        speech_packet_bindings=binding["speech_packet_bindings"],
                        trace_sink=sink,
                        decoding_params=self._phase_decoding_params(),
                        material_for_phase=binding["material_for_phase"],
                        supply_for_phase=supply_for_phase,
                        review_for_phase=review_for_phase,
                        bootstrap_facet_ids=facet_seed.get(program.phase_names()[0], ()),
                        bootstrap_value_ids=value_seed.get(program.phase_names()[0], ()),
                        **live_options,
                    ),
                )
            else:
                summaries = self._phase_runner(
                    program=program,
                    adapter=self._adapter,
                    plan=plan,
                    data_root=self._data_root,
                    core_client=client,
                    split_id=self._split_id,
                    knowledge_snapshot=binding["knowledge_snapshot"],
                    speech_packet_bindings=binding["speech_packet_bindings"],
                    trace_sink=sink,
                    decoding_params=self._phase_decoding_params(),
                    material_for_phase=binding["material_for_phase"],
                    supply_for_phase=supply_for_phase,
                    review_for_phase=review_for_phase,
                    bootstrap_facet_ids_by_phase=facet_seed,
                    bootstrap_value_ids_by_phase=value_seed,
                )
            if review_specs:
                from ...rails.phase_review import (  # noqa: PLC0415 (cycle guard)
                    phase_review_receipt,
                )

                self._phase_review_receipt = phase_review_receipt(
                    review_specs, review_for_phase
                )
        finally:
            flush = getattr(client, "flush_trace_buffer", None)
            if isinstance(sink, TraceBuffer) and callable(flush):
                flush(sink)
        self._phase_summaries = tuple(summaries)
        rows = self._rows_from_phase_summaries(self._phase_summaries, policy=policy)
        contact_count = sum(
            self._phase_summary_contacts(summary) for summary in self._phase_summaries
        )
        phase_receipt = [
            {
                "phase": getattr(summary, "controller_policy_id", None),
                "rows": len(summary.results),
                "contacts": self._phase_summary_contacts(summary),
            }
            for summary in self._phase_summaries
        ]
        dispatch: dict[str, object] = {
            "dispatch": "phase-program-continuous" if continuous else "phase-program",
            "program_id": program.program_id,
            "phase_names": list(program.phase_names()),
            "contacts_per_sample": len(program.phases),
            "barrier": (
                "whole-roster waves with retained controller state"
                if whole_roster else
                "none: one continuous trajectory per sample "
                "(rails.phase_runner.run_continuous_program) -- required so a "
                "supplied phase's acquire transition can be emitted"
                if continuous
                else "whole-roster per phase (rails.phase_runner.run_program)"
            ),
            "material_source": (
                "bind_phase_program_material override"
                if self._phase_program_material is not None
                else "baseline fragment phase_material (rails.phase_material)"
            ),
            "supplied_phases": sorted(supply_specs),
            "seeded_supply_phases": sorted(set(facet_seed) | set(value_seed)),
            # W1: which phases this flight REVIEWED. Criticism only -- a
            # reviewed phase sends the same bytes as an unreviewed one
            # (owner Decision 11-C), so this is provenance, not a mode.
            "reviewed_phases": sorted(review_specs),
        }
        if whole_roster:
            dispatch["whole_roster_wave_barrier"] = True
            dispatch["live_phase_fit_receipts"] = list(live_fit_gate.receipts)
        return rows, contact_count, "phase-program", dispatch, phase_receipt

    def preparation_context(self):
        """Resolve a fit context without preflight's circular fit-pin check."""
        values, carrier, _split, identity = self._prepare()
        receipt = self._runtime_receipt_loader(
            resolve_runtime_receipt_path(self._repo_root, values))
        preparation_plan = self._build_execution_plan(values, carrier, identity)
        return {
            "values": values, "split_identity_hash": identity,
            "repo_root": self._repo_root,
            "data_root": self._data_root, "runtime_root": self._runtime_root,
            "run_id": self._run_id, "attempt_id": self.attempt_id,
            "geometry": dict(self._adapter.serving_geometry()),
            "execution_plan": preparation_plan,
            "sample_ids": [sample.sample_id for sample in self._samples],
            "runtime_receipt": receipt,
            "required_identity": self.session_required_identity(),
        }

    def authorize_preparation_contacts(self, *, contact_cap: int):
        """Apply the normal committed plan/exposure gate before tokenizer access."""
        plan, _gate = self.authorize_preparation_client(contact_cap=contact_cap)
        return plan

    def authorize_preparation_client(self, *, contact_cap: int):
        """Return the shared checked plan and gate for a preparation client."""
        from dataclasses import replace
        from ..preparation import PreparationError

        values, carrier, _split, identity = self._prepare()
        if (isinstance(contact_cap, bool) or not isinstance(contact_cap, int) or contact_cap < 1):
            raise PreparationError("fit contact cap must be a positive integer")
        # Tokenizer and generation are separately registered runs. Keep the
        # actual config/protocol/split but require the explicitly requested
        # tokenizer cap to match its own exposure row at the normal gate.
        plan = replace(self._build_execution_plan(values, carrier, identity),
                       planned_model_calls=contact_cap).validate()
        configured_root = model_materialization_root(values)
        gate = self._gate_factory(
            self._repo_root, self._data_root, self._runtime_root,
            runtime_receipt_relpath=runtime_receipt_relpath(values),
            expected_model_lock_key=model_lock_key(values),
            model_root=Path(configured_root) if configured_root is not None else None,
            d1_media_supplement_relpath=d1_media_supplement_relpath(values),
            d1_media_supplement_sha256=d1_media_supplement_sha256(values),
            d1_evidence_supplement_relpath=d1_evidence_supplement_relpath(values),
            d1_evidence_supplement_sha256=d1_evidence_supplement_sha256(values),
        )
        self._gate_touch(gate, plan)
        self._require_exposure_row_unconsumed(plan.run_id)
        require_clean_study_repo(self._repo_root)
        return plan, gate

    def prepare_window_inventory(self, output: Path, *, max_workers: int = 1):
        """Persist verified exact-window inputs without any model contact."""

        from ..model import FrozenCoreError
        from ..model.paths import _normalized_relative_path, _resolve_confined
        from ..preparation import PreparationError, hash_stable_file
        from ..preparation_windows import (
            WindowFeatureEncoderIdentity,
            prepare_window_feature_inventory,
        )

        values, carrier, _split, split_identity = self._prepare()
        execution_plan = self._build_execution_plan(
            values, carrier, split_identity
        )

        receipt_path = resolve_runtime_receipt_path(self._repo_root, values)
        receipt_size, receipt_sha256, receipt_fingerprint = hash_stable_file(
            receipt_path, "runtime receipt"
        )
        if receipt_size == 0:
            raise PreparationError("runtime receipt is empty")
        receipt = self._runtime_receipt_loader(receipt_path)
        _assert_file_fingerprint(
            receipt_path, receipt_fingerprint, "runtime receipt"
        )

        llama_cpp = receipt.get("llama_cpp")
        if not isinstance(llama_cpp, Mapping):
            raise PreparationError("runtime receipt lacks a llama_cpp mapping")
        build_commit = llama_cpp.get("build_commit")
        if (
            not isinstance(build_commit, str)
            or len(build_commit) != 40
            or any(char not in "0123456789abcdef" for char in build_commit)
        ):
            raise PreparationError(
                "runtime receipt build_commit must be a lowercase 40-hex commit"
            )

        try:
            binary_relpath = _normalized_relative_path(
                llama_cpp.get("binary_path"), "runtime binary path"
            )
            binary_path = _resolve_confined(
                self._runtime_root,
                binary_relpath,
                self._runtime_root,
                "runtime binary path",
                strict=True,
            )
        except FrozenCoreError as error:
            raise PreparationError(str(error)) from error
        _verify_pinned_file(
            binary_path,
            expected_size=llama_cpp.get("binary_bytes"),
            expected_sha256=llama_cpp.get("binary_sha256"),
            label="runtime binary",
        )

        gguf_files = receipt.get("gguf_files")
        if not isinstance(gguf_files, list) or not gguf_files:
            raise PreparationError("runtime receipt lacks a non-empty gguf_files list")
        decoder_entries = []
        mmproj_entries = []
        for entry in gguf_files:
            if not isinstance(entry, Mapping):
                raise PreparationError(
                    "runtime receipt gguf_files entries must be mappings"
                )
            raw_path = entry.get("path")
            try:
                relative = _normalized_relative_path(
                    raw_path, "runtime receipt GGUF path"
                )
            except FrozenCoreError as error:
                raise PreparationError(str(error)) from error
            target = mmproj_entries if "mmproj" in Path(relative).name.lower() else decoder_entries
            target.append((entry, relative))
        if len(decoder_entries) != 1 or len(mmproj_entries) != 1:
            raise PreparationError(
                "window inventory requires exactly one decoder and one mmproj GGUF"
            )

        configured_root = model_materialization_root(values)
        materialization_root = (
            Path(configured_root) if configured_root is not None else self._data_root
        )
        verified_hashes = {}
        for role, entries in (
            ("decoder", decoder_entries),
            ("mmproj", mmproj_entries),
        ):
            entry, relative = entries[0]
            try:
                actual_path = _resolve_confined(
                    materialization_root,
                    relative,
                    materialization_root,
                    f"{role} GGUF path",
                    strict=True,
                )
            except FrozenCoreError as error:
                raise PreparationError(str(error)) from error
            verified_hashes[role] = _verify_pinned_file(
                actual_path,
                expected_size=entry.get("bytes"),
                expected_sha256=entry.get("sha256"),
                label=f"{role} GGUF",
            )

        encoder_override = verify_feature_encoder_runtime(
            repo_root=self._repo_root,
            data_root=materialization_root,
            runtime_root=self._runtime_root,
            values=values,
            generation_receipt=receipt,
            receipt_loader=self._runtime_receipt_loader,
        )
        encoder_identity = (
            encoder_override.encoder_identity
            if encoder_override is not None
            else WindowFeatureEncoderIdentity(
                runtime_receipt_sha256=receipt_sha256,
                build_commit=build_commit,
                decoder_gguf_sha256=verified_hashes["decoder"],
                mmproj_sha256=verified_hashes["mmproj"],
            )
        )
        batch = self.materialize_window_batch(
            execution_plan=execution_plan,
            **({"max_workers": max_workers} if max_workers != 1 else {}),
        )
        return prepare_window_feature_inventory(
            Path(output),
            batches={self._run_id: batch},
            data_root=self._data_root,
            encoder_identity=encoder_identity,
        )

    def materialize_request_fit_batch(self, *, execution_plan=None):
        """Return raw E21 fit requests, or ``None`` for phase-program fits.

        The shared preparation fitter calls this before it decides how to
        render a request. Keeping the dispatch here makes root-coordinated
        and attach-only fits bind the same request builder and source facts.
        """
        if self._adapter.preprocess_plan().get("kind") != "raw-speech-windows":
            return None
        return self.materialize_window_batch(execution_plan=execution_plan)

    def materialize_window_batch(self, *, execution_plan=None, max_workers: int | None = None):
        """Build the configured E21 raw-window requests without model contact."""
        from ..base import SampleContext
        from ..model.slices import SliceRegistry
        from ..preparation import PreparationError
        from ..preparation_windows import materialize_window_requests
        from ...reproduction.window_controller import (
            PROGRAM_KEY,
            build_controller_window_hook,
        )
        from ...reproduction.repair_loop import build_repair_window_hook

        values, _carrier, _split, _identity = self._prepare()
        if max_workers is None:
            max_workers = values.get("window_preparation_workers", 1)
        if isinstance(max_workers, bool) or not isinstance(max_workers, int) or not 1 <= max_workers <= 20:
            raise PreparationError("window preparation max_workers must be between 1 and 20")
        from ..flight_lock import read_flight_lock
        # Root allocates a global CPU budget. A live/stale lease conservatively
        # enforces the lower campaign cap even if a caller says it is idle.
        if read_flight_lock(self._data_root) is not None:
            max_workers = min(max_workers, 8)
        if self._adapter.preprocess_plan().get("kind") != "raw-speech-windows":
            raise PreparationError(
                "window fit requires the E21 raw-speech-windows adapter"
            )
        if not isinstance(self._adapter, TaskAdapter):
            raise PreparationError("window fit requires the prepared runtime adapter")
        if values.get("policy") not in (
            "obs-agent-loop-ojw",
            "obs-repair-loop-ojw",
        ):
            raise PreparationError(
                "window fit refuses unsupported live or adaptive policies"
            )
        if values.get("evidence_mismatch", False):
            raise PreparationError("window fit refuses rotated evidence mismatch")
        from ..driver.run import materialize_evidence_binding
        evidence_binding = materialize_evidence_binding(
            self._lock, self._data_root, self._samples, values,
            evidence_budget_bytes=int(values.get("evidence_budget_bytes", 0)),
        )
        plan = execution_plan or self._plan
        if values.get(PROGRAM_KEY) and plan is None:
            raise PreparationError("window fit requires the authorized execution plan")
        registry = SliceRegistry(
            data_root=self._data_root,
            run_id=self._run_id,
            parent_facts={
                sample.sample_id: (sample.media_relpath, sample.audio_seconds)
                for sample in self._samples
            },
        )
        window_packets = self.window_feature_packet_binding()
        contexts = []
        for sample in self._samples:
            contexts.append(
                SampleContext(
                    sample=sample,
                    evidence=evidence_binding.evidence_by_sample.get(sample.sample_id, ()),
                    adapter=self._adapter,
                    sink=object(),
                    arm=str(values["arm"]),
                    task_instruction=self._adapter.instruction(sample),
                    decoding_params=dict(values.get("decoding_params", {})),
                    request_id_base=f"{self._run_id}-{sample.sample_id}",
                    extras={
                        "slice_registry": registry,
                        "data_root": self._data_root,
                        "run_dir": self._run_dir(),
                        "repo_root": self._repo_root,
                        "config_values": values,
                        "execution_plan": plan,
                        "obs_dispatcher": None,
                        **({"window_feature_packets": window_packets}
                           if window_packets is not None else {}),
                    },
                )
            )

        def hook_factory(ctx, cfg, root, sample):
            delegate = None
            if values["policy"] == "obs-repair-loop-ojw":
                delegate = build_repair_window_hook(ctx, cfg, root, sample)
            if values.get(PROGRAM_KEY):
                return build_controller_window_hook(ctx, cfg, delegate)
            return delegate

        return materialize_window_requests(
            contexts,
            expected_sample_ids=[sample.sample_id for sample in self._samples],
            hook_factory=hook_factory,
            evidence_binding=evidence_binding,
            **({"max_workers": max_workers} if max_workers != 1 else {}),
        )


    def request_fit_inputs(self, payloads, *, window_batch=None):
        from .. import preparation, preparation_fit
        from .. import config as config_module
        from ..model import transport
        from ..model import speech_features
        from ..preparation import artifact_inputs
        from ...rails.adapters import runtime_view
        from ...rails import core_client

        context = self.preparation_context()
        sources = {
            "boundary_sha256": preparation_fit.boundary_identity(
                payloads, window_routes=window_batch is not None
            ),
            "runtime_receipt": context["runtime_receipt"],
            "required_identity": context["required_identity"],
            "implementation": {
                "runtime": _sha256_file(Path(__file__)),
                "transport": _sha256_file(Path(transport.__file__)),
                "preparation_fit": _sha256_file(Path(preparation_fit.__file__)),
                "preparation": _sha256_file(Path(preparation.__file__)),
                "config": _sha256_file(Path(config_module.__file__)),
                "runtime_view": _sha256_file(Path(runtime_view.__file__)),
                "core_client": _sha256_file(Path(core_client.__file__)),
                "speech_features": _sha256_file(Path(speech_features.__file__)),

            },
        }
        if window_batch is not None:
            from ...reproduction import obs_loop, repair_loop, window_controller
            from ...reproduction.ojw import components as ojw_components
            from ...reproduction.ojw import policy as ojw_policy, state as ojw_state
            from .. import class_lists, evidence, evidence_derivation, preparation_windows
            from ..driver import run as driver_run
            from ..driver.run import (
                evidence_binding_identity,
                materialize_evidence_binding,
            )

            if context["values"].get("prepared_window_feature_packets") is not None:
                from .. import preparation_window_packets
                sources["prepared_window_feature_packets"] = dict(
                    context["values"]["prepared_window_feature_packets"]
                )
                sources["implementation"]["preparation_window_packets"] = _sha256_file(
                    Path(preparation_window_packets.__file__)
                )
            sources["window_implementation"] = {
                module.__name__: _sha256_file(Path(module.__file__))
                for module in (
                    obs_loop, repair_loop, preparation_windows, window_controller,
                    driver_run, ojw_components, ojw_policy, ojw_state,
                )
            }
            prepared_binding = getattr(window_batch, "evidence_binding", None)
            if prepared_binding is None:
                if context["values"].get("evidence_source", "none") not in (None, "none"):
                    from ..preparation import PreparationError

                    raise PreparationError(
                        "evidence-bearing window batch lacks its materialized evidence binding"
                    )
            else:
                current_binding = materialize_evidence_binding(
                    self._lock,
                    self._data_root,
                    self._samples,
                    context["values"],
                    evidence_budget_bytes=int(context["values"].get("evidence_budget_bytes", 0)),
                )
                evidence_sources = evidence_binding_identity(prepared_binding)
                if evidence_binding_identity(current_binding) != evidence_sources:
                    from ..preparation import PreparationError

                    raise PreparationError(
                        "window evidence sources changed after payload materialization"
                    )
                if any(evidence_sources.values()):
                    sources["window_evidence"] = evidence_sources
                    sources["window_implementation"].update(
                        {
                            module.__name__: _sha256_file(Path(module.__file__))
                            for module in (
                                window_controller,
                                driver_run,
                                evidence,
                                class_lists,
                                evidence_derivation,
                            )
                        }
                    )
            sources.update(
                window_sources=list(
                    preparation_fit.canonical_window_sources(window_batch.source_bindings)
                ),
                window_measurement=(
                    "resident-template-tokenizer-and-bound-packet-counts"
                    if context["values"].get("prepared_window_feature_packets") is not None
                    else "resident-multimodal-input-tokens"
                ),
            )
        return artifact_inputs(
            config=context["values"],
            split_identity_hash=context["split_identity_hash"],
            sources=sources,
        )


    def _verify_prepared_request_fit(self, pin):
        from ..preparation import PreparationError, load_artifact
        from ..model.paths import _normalized_relative_path, _resolve_confined

        if not isinstance(pin, Mapping) or set(pin) != {"relpath", "sha256"}:
            raise PreparationError("prepared_request_fit requires relpath and sha256")
        path = _resolve_confined(
            self._data_root, _normalized_relative_path(pin["relpath"], "prepared fit"),
            self._data_root, "prepared fit", strict=True,
        )
        self._prepare()
        window_batch = None
        if self._adapter.preprocess_plan().get("kind") == "raw-speech-windows":
            window_batch = self.materialize_window_batch()
        if window_batch is not None:
            payloads = window_batch.payloads
        else:
            payloads = self.materialize_phase_requests()
        result = load_artifact(
            path,
            expected_sha256=pin["sha256"],
            kind="request-fit",
            inputs=self.request_fit_inputs(payloads, window_batch=window_batch),
        )
        if not isinstance(result, dict) or result.get("every_request_fits") is not True:
            raise PreparationError("prepared request fit did not pass every row")
        rows = result.get("rows")
        expected = (
            set(window_batch.request_keys)
            if window_batch is not None
            else {payload["sample_id"] for payload in payloads}
        )
        row_key = "request_key" if window_batch is not None else "sample_id"
        if (
            not isinstance(rows, list)
            or len(rows) != len(expected)
            or any(not isinstance(row, dict) or row.get("fits") is not True for row in rows)
            or {row.get(row_key) for row in rows} != expected
            or result.get("sample_count") != len(expected)
        ):
            raise PreparationError("prepared request fit does not certify the full roster")
        return {
            "schema": "saea-prepared-request-fit-check-v1",
            "sample_count": len(expected),
            "every_request_fits": True,
            "sha256": pin["sha256"],
            "relpath": pin["relpath"],
        }

    def materialize_phase_requests(self, *, max_workers: int = 1):
        """Return every real boundary payload for a single-phase fit.

        The normal controller, adapter, supplied seeds, and payload binding
        execute against a contact-free transport. Multi-phase programs are
        refused because a later prompt could depend on a fake predecessor.
        Payloads remain in memory and the wire-check attempt is aborted.
        """
        from ..preparation import PreparationError

        values, _carrier, _split, _identity = self._prepare()
        program = default_phase_program(str(values["policy"]))
        if len(program.phase_names()) != 1:
            raise PreparationError("actual fit requires one phase with sealed predecessors")
        payloads = []
        prior_client = getattr(self, "_client", None)
        prior_outputs = getattr(self, "_output_rows", None)
        try:
            self.wire_check(
                seal_and_score=False, max_workers=max_workers,
                request_payload_observer=payloads.append,
            )
        finally:
            self._client = prior_client
            self._output_rows = prior_outputs
        expected = [sample.sample_id for sample in self._samples]
        actual = [payload.get("sample_id") for payload in payloads]
        if len(set(actual)) != len(actual) or set(actual) != set(expected):
            raise PreparationError("actual request materialization must cover the full roster")
        return tuple(payloads)

    def _phase_seed_inputs(self, binding, spec, split_identity_hash):
        """Bind prepared selections to the same frozen inputs used by dispatch."""
        from ..preparation import artifact_inputs, verify_source_receipts
        from ...rails import kb_policy, knowledge_provider, phase_supply

        return artifact_inputs(
            config=self._composed.values, split_identity_hash=split_identity_hash,
            sources={
                "frozen_source_receipts": verify_source_receipts(
                    self._composed.values.get("preparation_source_receipts"),
                    repo_root=self._repo_root, data_root=self._data_root,
                ),
                "snapshot": binding["knowledge_snapshot"].content_hash(),
                "supply_spec": spec.as_json(),
                "packets": dict(binding["speech_packet_bindings"]),
                "implementation": {
                    **{module.__name__: _sha256_file(Path(module.__file__))
                       for module in (kb_policy, knowledge_provider, phase_supply)},
                    "runtime": _sha256_file(Path(__file__)),
                },
            },
        )

    def prepare_phase_supply(self, path: Path, *, max_workers: int = 1) -> Mapping[str, object]:
        """Persist the real first-phase selection offline for reuse at dispatch.

        No server, tokenizer, gate, attempt, or inference contact is opened.
        Existing vector/snapshot bindings are verified by the normal resolver.
        """
        from types import SimpleNamespace
        from ..preparation import PreparationError, prepare_artifact

        values, _carrier, _split, identity = self._prepare()
        program = default_phase_program(str(values["policy"]))
        binding = self._phase_program_material
        if binding is None:
            binding = self._default_phase_program_binding(program, None)
        specs = binding.get("supply_specs") or {}
        first = program.phase_names()[0]
        if first not in specs:
            raise PreparationError("program has no supplied first phase to prepare")
        inputs = self._phase_seed_inputs(binding, specs[first], identity)

        def produce():
            facets, selected = self._phase_supply_seeds(
                program, binding, specs, SimpleNamespace(split_identity_hash=identity),
                max_workers=max_workers,
            )
            return {"facets": facets, "values": selected}

        return prepare_artifact(path, kind="phase-supply", inputs=inputs, producer=produce)

    def prepare_phase_recall(self, path: Path, *, phase: str, max_workers: int = 1) -> Mapping[str, object]:
        """Persist model-free multidimensional recall for one configured phase.

        The artifact stores only the deterministic recall scores. Runtime still
        executes the registered ranker and fuser against the actual QueryState.
        """
        from ..preparation import PreparationError, prepare_artifact
        from ...rails.phase_supply import load_phase_supply_specs, load_sealed_vectors
        from ...rails.phase_supply import prepare_recall_rows, _validate_bootstrap_workers

        max_workers = _validate_bootstrap_workers(max_workers)
        if getattr(self, "_campaign_active", False):
            max_workers = min(max_workers, 8)
        values, _carrier, _split, identity = self._prepare()
        program = default_phase_program(str(values["policy"]))
        binding = self._phase_program_material
        if binding is None:
            binding = self._default_phase_program_binding(program, None)
        specs = load_phase_supply_specs(values, program)
        spec = specs.get(phase)
        if spec is None:
            raise PreparationError(f"phase {phase!r} has no configured phase supply")
        if spec.provider != "kb-facet-v1" or spec.query_source.get("kind") != "sealed-vectors":
            raise PreparationError("prepared recall requires kb-facet-v1 and sealed query vectors")
        if spec.facet_source is not None and spec.facet_source.get("kind") != "sealed-vectors":
            raise PreparationError("prepared recall requires sealed facet vectors")
        snapshot = binding["knowledge_snapshot"]
        query = load_sealed_vectors(
            self._data_root / str(spec.query_source["relpath"]),
            expected_sha256=str(spec.query_source["sha256"]),
            dimensions=spec.dimensions,
        )
        facets = (
            {}
            if spec.facet_source is None
            else load_sealed_vectors(
                self._data_root / str(spec.facet_source["relpath"]),
                expected_sha256=str(spec.facet_source["sha256"]),
                dimensions=spec.dimensions,
            )
        )
        if set(query) != set(binding["speech_packet_bindings"]):
            raise PreparationError("prepared recall query roster differs from the runtime packets")
        inputs = self._phase_seed_inputs(binding, spec, identity)
        inputs.update({"recall_schema": "saea-phase-recall-v1", "phase": phase,
                       "roster_ids": sorted(query)})
        def produce():
            rows = prepare_recall_rows(snapshot, query, facets, spec.k, workers=max_workers)
            return {"phase": phase, "rows": rows}
        return prepare_artifact(path, kind="phase-recall", inputs=inputs, producer=produce)

    def _load_phase_supply_seed(self, pin, binding, spec, split_identity_hash):
        from ..preparation import PreparationError, load_artifact
        from ..model.paths import _normalized_relative_path, _resolve_confined

        if not isinstance(pin, Mapping) or set(pin) != {"relpath", "sha256"}:
            raise PreparationError("prepared_phase_supply requires relpath and sha256")
        relative = _normalized_relative_path(pin["relpath"], "prepared phase supply")
        path = _resolve_confined(self._data_root, relative, self._data_root,
                                 "prepared phase supply", strict=True)
        output = load_artifact(
            path, expected_sha256=pin["sha256"], kind="phase-supply",
            inputs=self._phase_seed_inputs(binding, spec, split_identity_hash),
        )
        if not isinstance(output, dict) or set(output) != {"facets", "values"}:
            raise PreparationError("prepared phase selection shape mismatch")
        allowed_rows = set(binding["speech_packet_bindings"])
        snapshot = binding["knowledge_snapshot"]
        results = []
        for name, allowed in (
            ("facets", {f.facet_id for f in snapshot.facets}),
            ("values", {v.value_id for v in snapshot.values}),
        ):
            phases = output[name]
            if not isinstance(phases, dict) or set(phases) - {spec.phase}:
                raise PreparationError("prepared phase selection contains another phase")
            decoded = {}
            for phase, rows in phases.items():
                if not isinstance(rows, dict) or set(rows) - allowed_rows:
                    raise PreparationError("prepared phase selection contains another row")
                decoded[phase] = {}
                for sid, ids in rows.items():
                    if (not isinstance(ids, list) or any(not isinstance(i, str) for i in ids)
                            or len(ids) != len(set(ids)) or set(ids) - allowed):
                        raise PreparationError("prepared phase selection contains unknown IDs")
                    decoded[phase][sid] = tuple(ids)
            results.append(decoded)
        return tuple(results)

    def _load_phase_recall(self, pin, binding, spec, split_identity_hash):
        from ..preparation import PreparationError, load_artifact
        from ..model.paths import _normalized_relative_path, _resolve_confined

        if not isinstance(pin, Mapping) or set(pin) != {"relpath", "sha256"}:
            raise PreparationError("prepared_phase_recall requires relpath and sha256")
        relative = _normalized_relative_path(pin["relpath"], "prepared phase recall")
        path = _resolve_confined(self._data_root, relative, self._data_root,
                                 "prepared phase recall", strict=True)
        inputs = self._phase_seed_inputs(binding, spec, split_identity_hash)
        inputs.update({"recall_schema": "saea-phase-recall-v1", "phase": spec.phase})
        # The roster is independently checked against the current sealed query table.
        from ...rails.phase_supply import load_sealed_vectors
        query = load_sealed_vectors(
            self._data_root / str(spec.query_source["relpath"]),
            expected_sha256=str(spec.query_source["sha256"]),
            dimensions=spec.dimensions,
        )
        if set(query) != set(binding["speech_packet_bindings"]):
            raise PreparationError("prepared recall query roster differs from the runtime packets")
        inputs["roster_ids"] = sorted(query)
        output = load_artifact(path, expected_sha256=pin["sha256"],
                               kind="phase-recall", inputs=inputs)
        if not isinstance(output, Mapping) or set(output) != {"phase", "rows"}:
            raise PreparationError("prepared phase recall shape mismatch")
        if output["phase"] != spec.phase or not isinstance(output["rows"], Mapping):
            raise PreparationError("prepared phase recall phase mismatch")
        rows = output["rows"]
        if set(rows) != set(query):
            raise PreparationError("prepared phase recall roster mismatch")
        facet_dimensions = {
            facet.facet_id: facet.dimension
            for facet in binding["knowledge_snapshot"].facets
        }
        # Recall also includes snapshot label/prior dimensions without vectors.
        # spec.dimensions only governs the sealed vector-file dimensions.
        for sample_id, recalled in rows.items():
            if not isinstance(sample_id, str) or not isinstance(recalled, Mapping):
                raise PreparationError("prepared phase recall row is malformed")
            for facet_id, dimensions in recalled.items():
                if facet_id not in facet_dimensions or not isinstance(dimensions, Mapping):
                    raise PreparationError("prepared phase recall contains an unknown facet")
                if set(dimensions) != {facet_dimensions[facet_id]}:
                    raise PreparationError("prepared phase recall contains an unknown dimension")
                for score in dimensions.values():
                    if isinstance(score, bool) or not isinstance(score, (int, float)):
                        raise PreparationError("prepared phase recall score is not numeric")
                    if not math.isfinite(float(score)) or float(score) <= 0.0:
                        raise PreparationError("prepared phase recall score is invalid")
        return {str(sample_id): rows[sample_id] for sample_id in query}

    def _phase_supply_seeds(
        self,
        program: object,
        binding: Mapping[str, object],
        supply_specs: Mapping[str, object],
        plan: ExecutionPlan,
        max_workers: int = 1,
    ) -> tuple[dict[str, object], dict[str, object]]:
        """``({phase: facet seed}, {phase: value seed})`` for a supplied
        FIRST phase (E6).

        Only the first phase can be seeded, and only the first phase needs
        to be: every later phase carries its supply on the preceding wave's
        ``acquire`` transition. Empty for every other program.

        ``plan`` is the plan DRIVING this dispatch, not ``self._plan``. They
        are the same object in a real flight, but :meth:`wire_check` builds
        its own plan under its own run id and never sets ``self._plan`` -- so
        reading the attribute raised ``AttributeError: 'NoneType'`` and made
        the one cell shape that seeds a first phase (KU-S3) unable to be
        wire-checked at all. Found by wire-checking it, 2026-09-07, which is
        the case the method exists for.
        """

        from ...rails.phase_supply import (  # noqa: PLC0415 (cycle guard)
            build_bootstrap_selection,
        )

        if not supply_specs:
            return {}, {}
        first_phase = program.phase_names()[0]
        spec = supply_specs.get(first_phase)
        if spec is None:
            return {}, {}
        prepared = self._composed.values.get("prepared_phase_supply")
        if prepared is not None:
            return self._load_phase_supply_seed(
                prepared, binding, spec, plan.split_identity_hash
            )
        supply_for_phase = binding.get("supply_for_phase")
        factories = getattr(supply_for_phase, "provider_factories", {}) or {}
        query_tables = getattr(supply_for_phase, "query_tables", {}) or {}
        factory = factories.get(first_phase)
        provider = None if factory is None else factory()
        if provider is None:
            raise FlightRuntimeError(
                f"phase_supply seeds the first phase {first_phase!r} but no provider "
                "was resolved for it"
            )
        facets, values = build_bootstrap_selection(
            spec,
            provider=provider,
            query_vectors_by_sample=query_tables.get(first_phase, {}),
            speech_packet_bindings=binding["speech_packet_bindings"],
            split_identity_hash=plan.split_identity_hash,
            workers=max_workers,
            lease_metadata_present=(self._data_root / "locks" / "flight.lock").exists(),
        )
        return ({first_phase: facets} if facets else {}), (
            {first_phase: values} if values else {}
        )

    def run_phases(self, *, workers: int | None = None) -> Mapping[str, object]:
        """Build a ``client_factory`` (default ``FrozenCoreClient``) from
        :meth:`frozen_core_client_kwargs`, then dispatch on the baseline
        fragment's ``policy``: ``"fixed"`` runs ``rails_runner`` (default
        ``rails.runner.run_rails_experiment``); any other value is resolved
        as a phase-program id through ``rails.controllers.
        default_phase_program`` and run via ``phase_runner`` (default
        ``rails.phase_runner.run_program``), which requires this runtime to
        have been given a ``knowledge_snapshot``/``speech_packet_bindings``/
        ``material_for_phase`` (see :meth:`bind_phase_program_material`) --
        a phase-program flight without that binding fails closed here.
        Records wall time, contact count, an estimated tokens/s (see the
        module note on why it is an estimate: ``CoreClient``'s public
        surface exposes per-request latency via ``timings`` but not
        per-request token counts before ``close()``), and slot occupancy.
        """

        self._require_prior_stages("run_phases")
        self.assert_generation_lease()
        baseline_values = self._composed.values
        policy = baseline_values.get("policy")
        if not isinstance(policy, str) or not policy:
            raise FlightRuntimeError("baseline fragment must declare a non-empty 'policy'")
        self._assert_phase_supply_is_legal_for(policy)
        self._assert_phase_review_is_legal_for(policy)

        # The Earnings carrier (owner Decision 12-F item #9, 2026-09-08). An
        # obs policy is dispatched through the obs driver and builds NO
        # FrozenCoreClient: that client is the rails ``messages`` shim over
        # the same FrozenCoreAdapter the obs driver constructs, and building
        # one here would open this attempt twice
        # (:meth:`_dispatch_obs_policy`).
        if policy in self._obs_policy_names():
            return self._run_obs_phases(policy)

        client_kwargs = self.frozen_core_client_kwargs()
        client_initialization_started = self._clock()
        client = self._client_factory(**client_kwargs)
        client_initialization_seconds = max(
            self._clock() - client_initialization_started, 1e-9
        )
        self._client = client

        started = self._clock()
        dispatch: dict[str, object] = {"dispatch": "phase-program"}
        phase_receipt: list[Mapping[str, object]] = []
        if policy == "fixed":
            (
                self._output_rows,
                contact_count,
                policy_kind,
                dispatch,
            ) = self._dispatch_fixed_policy(client, self._plan, workers=workers)
        else:
            (
                self._output_rows,
                contact_count,
                policy_kind,
                dispatch,
                phase_receipt,
            ) = self._dispatch_phase_program(client, self._plan, policy)
        ended = self._clock()
        wall_seconds = max(ended - started, 1e-9)
        # E7: the window the always-on session's monitor summary is taken
        # over. Dispatch start/end, not per-request stamps: RequestTiming
        # carries latency, not a wall clock, and the GPU accounting this
        # window feeds is about the interval the flight occupied the card.
        self._contact_window = (started, ended)

        timings = client.timings
        latencies = tuple(timing.latency_seconds for timing in timings)
        average_latency = sum(latencies) / len(latencies) if latencies else 0.0
        slots = int(self._adapter.serving_geometry()["slots"])
        contacts_per_second = contact_count / wall_seconds
        # Occupancy is measured against the slots this dispatch actually
        # used, not against the server's slot count: a serial dispatch on a
        # 3-slot server occupies one slot, and reporting it as a third of
        # three would understate exactly the thing the number is for.
        occupancy_slots = int(dispatch.get("workers") or slots)
        slot_occupancy = (
            (contact_count * average_latency) / (wall_seconds * occupancy_slots)
            if occupancy_slots > 0
            else 0.0
        )
        # Estimate only: an UPPER BOUND (measured contact rate times this
        # task's declared completion-token ceiling), not an exact figure --
        # RequestTiming carries latency, not token counts, and CoreClient's
        # public surface has no other pre-close() accessor for them (see the
        # C4c report's residual list).
        max_tokens = int(self._adapter.serving_geometry()["max_tokens"])
        tokens_per_second_estimate = contacts_per_second * max_tokens

        decoding = self._decoding_params() or {}
        payload = {
            "policy": policy,
            "policy_kind": policy_kind,
            "arm": client.arm,
            "id_slot": decoding.get("id_slot"),
            "id_slot_resolution": (
                f"{SLOT_AFFINITY_SENTINEL!r} sentinel resolved to slot "
                f"{SEQUENTIAL_DISPATCH_SLOT} (this harness dispatches one contact at "
                "a time)"
                if self._composed.values.get("decoding_params", {}).get("id_slot")
                == SLOT_AFFINITY_SENTINEL
                else "declared by the model fragment; no sentinel to resolve"
            ),
            # The generation cap this cell sent. A plain integer here means one
            # cap for every request; a mapping means the fragment declared a
            # per-sample rule (see MAX_TOKENS_POLICY_KEY) and every row's own
            # resolved integer is in that row's MODEL_REQUEST trace record.
            "max_tokens": decoding.get("max_tokens"),
            "max_tokens_resolution": (
                f"per-sample rule {decoding.get('max_tokens', {}).get(MAX_TOKENS_POLICY_KEY)!r} "
                "resolved from each sample's own audio_seconds; every request's integer "
                "is in its MODEL_REQUEST trace record"
                if self._max_tokens_rule(decoding) is not None
                else "one integer declared by the fragment; no rule to resolve"
            ),
            "wall_seconds": wall_seconds,
            "contact_window": {"from": started, "to": ended},
            "contact_count": contact_count,
            # One entry per phase of a phase program, in program order:
            # which controller policy ran it, how many rows it answered and
            # how many contacts it spent. Empty for a fixed-policy direct
            # arm, which has no phases at all. ``contact_count`` above is
            # the sum of the ``contacts`` column.
            "phases": phase_receipt,
            # What each phase's instruction and response format actually
            # were, by sha256 and length -- never the text itself, which can
            # be the whole 152-tool registry. None for a direct arm, and for
            # a caller-supplied bind_phase_program_material override (whose
            # material this harness never rendered and cannot describe).
            "phase_material": self._phase_material_receipt,
            # E6: which phases this flight supplied, with what provider,
            # policy ids, knobs and pinned vector files -- never the vectors
            # and never any snapshot content. None for a cell that supplies
            # nothing.
            "phase_supply": self._phase_supply_receipt,
            # W1 (owner Decision 11-B change #1): which phases this flight
            # REVIEWED, with which judge ids and versions, how many rows each
            # judge read, how many it flagged and at what severity -- never a
            # draft and never a flag's reason in bulk (the per-row detail is
            # in the REVIEW trace records). None for a cell that reviews
            # nothing, which is every cell written before this wave.
            "phase_review": self._phase_review_receipt,
            "contacts_per_second": contacts_per_second,
            "average_latency_seconds": average_latency,
            "slot_occupancy": slot_occupancy,
            "tokens_per_second": tokens_per_second_estimate,
            "tokens_per_second_basis": "contacts_per_second_times_completion_token_ceiling_upper_bound_estimate",
            "response_arrival": self.response_arrival_counts(client),
            "dispatch": dispatch,
            "serving_slots": slots,
            "occupancy_slots": occupancy_slots,
            "client_initialization_seconds": client_initialization_seconds,
        }
        require_mandatory_throughput_fields(
            "run_phases", payload, ("contacts_per_second", "tokens_per_second")
        )
        return self.receipts.record("run_phases", payload)

    def _run_obs_phases(self, policy: str) -> Mapping[str, object]:
        """``run_phases`` for the Earnings carrier: the obs driver's run,
        recorded in this harness's own receipt shape.

        The throughput line is MEASURED here rather than estimated: the obs
        driver's cost block carries this run's real ``calls_used``,
        ``completion_tokens_total`` and ``latency_seconds_total``, so
        ``tokens_per_second`` is the flight's actual completion rate and not
        the contact-rate-times-ceiling upper bound the phase path has to
        settle for.
        """

        started = self._clock()
        (
            self._output_rows,
            contact_count,
            policy_kind,
            dispatch,
            result,
        ) = self._dispatch_obs_policy(self._plan)
        ended = self._clock()
        self._obs_result = result
        self._contact_window = (started, ended)
        wall_seconds = max(ended - started, 1e-9)

        cost = dict(result.cost)

        def _number(name: str) -> float:
            value = cost.get(name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return 0.0
            return float(value)

        completion_tokens = _number("completion_tokens_total")
        latency_total = _number("latency_seconds_total")
        contacts_per_second = contact_count / wall_seconds
        average_latency = latency_total / contact_count if contact_count else 0.0
        slots = int(self._adapter.serving_geometry()["slots"])
        occupancy_slots = int(dispatch.get("workers") or slots)
        slot_occupancy = (
            latency_total / (wall_seconds * occupancy_slots) if occupancy_slots > 0 else 0.0
        )
        decoding = self._composed.values.get("decoding_params") or {}
        payload = {
            "policy": policy,
            "policy_kind": policy_kind,
            "arm": result.arm,
            "id_slot": decoding.get("id_slot"),
            "id_slot_resolution": (
                f"{SLOT_AFFINITY_SENTINEL!r} sentinel passed through UNRESOLVED: the "
                "obs executors resolve it per sample from the run's own dispatch "
                "pool, which is what per-sample slot affinity means"
                if decoding.get("id_slot") == SLOT_AFFINITY_SENTINEL
                else "declared by the model fragment; no sentinel to resolve"
            ),
            "max_tokens": decoding.get("max_tokens"),
            "max_tokens_resolution": (
                "one integer declared by the fragment; the obs loop reads it per "
                "slice for its own decode-cap saturation check"
            ),
            "wall_seconds": wall_seconds,
            "contact_window": {"from": started, "to": ended},
            "contact_count": contact_count,
            "phases": [],
            "phase_material": None,
            "phase_supply": None,
            "phase_review": None,
            "contacts_per_second": contacts_per_second,
            "average_latency_seconds": average_latency,
            "slot_occupancy": slot_occupancy,
            # MEASURED, not an upper bound: the obs driver's adapter counted
            # every completion token this run actually spent.
            "tokens_per_second": completion_tokens / wall_seconds,
            "tokens_per_second_basis": "measured_completion_tokens_over_dispatch_wall",
            "response_arrival": None,
            "dispatch": dispatch,
            "serving_slots": slots,
            "occupancy_slots": occupancy_slots,
            # The obs driver's own aggregates, carried into the receipt so a
            # closure reports holes beside quality (module comment above
            # reproduction.obs_loop.SLICE_RETRYABLE_EXCEPTIONS).
            "obs_saturated_slice_count": cost.get("saturated_slice_count"),
            "obs_skipped_slice_count": cost.get("skipped_slice_count"),
            "obs_trace_manifest_hash": result.trace_manifest_hash,
        }
        require_mandatory_throughput_fields(
            "run_phases", payload, ("contacts_per_second", "tokens_per_second")
        )
        return self.receipts.record("run_phases", payload)

    def _assert_phase_supply_is_legal_for(self, policy: str) -> None:
        """A ``policy == "fixed"`` direct arm has no phases at all, so a
        ``phase_supply`` block on it is dead config that would silently
        supply nothing (E6). Refused, loudly, before any contact.

        Owner rule 2026-09-06, enforced in the same place: the retrieval
        QUERY must contain the speech signal (speech, or speech plus an
        agent intermediate state -- never text-only). Every sealed-vector
        ``query_source`` must DECLARE its modality as the first token of
        ``embedded_signal``; ``rails.phase_supply`` owns the vocabulary and
        the refusal message. Applied here to the RAW fragment so a text-only
        query is refused before the phase program is even resolved, and
        again inside ``PhaseSupplySpec.validate`` for every other caller.
        """

        declared = self._composed.values.get("phase_supply")
        if policy == "fixed" and declared:
            raise FlightRuntimeError(
                "baseline fragment declares 'phase_supply' but policy is 'fixed'; a "
                "direct arm runs no phase program and would supply nothing. Declare a "
                "phase-program policy, or drop the phase_supply block"
            )
        from ...rails.phase_supply import (  # noqa: PLC0415 (cycle guard)
            PhaseSupplyError,
            assert_phase_supply_queries_carry_speech,
        )

        try:
            assert_phase_supply_queries_carry_speech(self._composed.values)
        except PhaseSupplyError as error:
            raise FlightRuntimeError(str(error)) from None

    def _assert_phase_review_is_legal_for(self, policy: str) -> None:
        """A ``policy == "fixed"`` direct arm runs no phase program, so a
        ``phase_review`` block on it is dead config that would review
        nothing while reading as if it reviewed. Refused, loudly, before any
        contact -- the same rule and the same reason as
        :meth:`_assert_phase_supply_is_legal_for`.
        """

        declared = self._composed.values.get("phase_review")
        if policy == "fixed" and declared:
            raise FlightRuntimeError(
                "baseline fragment declares 'phase_review' but policy is 'fixed'; a "
                "direct arm runs no phase program and would review nothing. Declare a "
                "phase-program policy, or drop the phase_review block"
            )

    def _phase_decoding_params(self) -> Mapping[str, object]:
        """The run-level decoding params a PHASE program may carry.

        Two keys the direct path legitimately sends are refused by the agent
        loop and must be dropped here rather than at the call site:

        * ``id_slot`` -- ``rails.runner.run_speech_native_agent_loop``
          refuses it outright ("the runner owns it"): it hands each
          trajectory a slot from its own pool. Every mmproj-free model
          fragment in this repository declares ``id_slot: "per-sample"``, so
          without this every phase-program flight would have died at its
          first contact.
        * ``response_format`` -- ``rails.phase_runner.run_agent_phase``
          refuses it, because each phase's own format comes from its
          ``PhaseMaterial`` (which is exactly what the ``RESPONSE_FORMATS``
          registry now supplies).
        """

        base = self._decoding_params()
        if self._max_tokens_rule(base) is not None:
            # The per-sample max_tokens seam resolves at the ONE place a fixed
            # direct arm builds a request (:meth:`_sample_decoding_params`).
            # A phase program's contacts are built by rails.phase_runner, which
            # this method hands ONE run-level mapping, so a rule arriving here
            # would travel unresolved to the adapter and die at the first
            # contact -- after a server start. Refused here instead, before one.
            raise FlightRuntimeError(
                "a per-sample decoding_params.max_tokens rule is a fixed-policy "
                "direct-arm seam; this cell declares a phase program, whose contacts "
                "are not resolved per sample here. Declare an integer max_tokens"
            )
        params = dict(base or {})
        params.pop("id_slot", None)
        params.pop("response_format", None)
        return params

    def _load_knowledge_snapshot(self) -> object:
        """The frozen TRAIN snapshot named by the baseline fragment's
        ``knowledge_snapshot_relpath``/``knowledge_snapshot_sha256``, loaded
        from under the data root and hash-verified against the pin.

        ``rails.runner.run_speech_native_agent_loop`` requires a validated,
        non-empty ``KnowledgeSnapshot`` for EVERY agent-loop contact, even
        one whose phases all declare ``knowledge: "none"``. Such a phase
        binds the snapshot INVISIBLY: ``bootstrap_facet_ids``/
        ``bootstrap_value_ids`` stay empty, so the initial ``QueryState``
        makes no facet or value visible and ``rails.runner._agent_messages``
        renders none of it into the prompt. The snapshot is still what the
        runner's own leakage rules are enforced against -- which is the
        point: a phase instruction that quoted snapshot material would be
        refused rather than silently smuggled past traced supply.
        """

        from ...rails.knowledge import KnowledgeSnapshot  # noqa: PLC0415 (cycle guard)

        values = self._composed.values
        relpath = values.get("knowledge_snapshot_relpath")
        expected = values.get("knowledge_snapshot_sha256")
        if not isinstance(relpath, str) or not relpath:
            raise FlightRuntimeError(
                "a phase-program baseline fragment must declare "
                "'knowledge_snapshot_relpath' (under the data root) -- the frozen "
                "TRAIN snapshot rails.runner.run_speech_native_agent_loop requires"
            )
        if not isinstance(expected, str) or len(expected) != 64:
            raise FlightRuntimeError(
                "'knowledge_snapshot_sha256' must be the pinned 64-hex content hash of "
                f"{relpath!r}"
            )
        path = self._data_root / relpath
        if not path.is_file():
            raise FlightRuntimeError(f"knowledge snapshot missing: {path}")
        snapshot = KnowledgeSnapshot.from_frozen_json(
            json.loads(path.read_text(encoding="utf-8"))
        )
        measured = snapshot.content_hash()
        if measured != expected:
            raise FlightRuntimeError(
                f"knowledge snapshot {path} hashes to {measured}, not the configured "
                f"{expected}"
            )
        return snapshot

    def _default_phase_program_binding(
        self, program: object, client: object
    ) -> Mapping[str, object]:
        """Build the phase-program binding from CONFIG alone (E1).

        ``bind_phase_program_material`` stays the explicit override for a
        caller that genuinely has material no fragment can express; this is
        what a cell whose material IS expressible gets for free, so a new
        two-contact cell is a config edit rather than a launcher script
        (owner rule of 2026-09-03, "one base, thin derivations").

        Three refusals, all BEFORE any contact:

        1. the arm must travel the speech-feature packet path -- the agent
           loop is speech-feature only (``rails.core_client.FrozenCoreClient``
           refuses ``history`` without ``speech_feature_sample_id``);
        2. every rendered static instruction, and every per-sample sealed
           state that will be appended to one, must pass the SAME
           protected-material containment rule ``rails.runner`` applies at
           contact time -- otherwise the flight dies mid-roster, after part
           of the budget is gone, on a defect that was fully decidable here;
        3. everything :mod:`rails.phase_material` itself refuses: a phase
           without material, material for a phase the program does not
           declare, a response-format presence or id mismatch, an unfilled
           template, a missing sealed predecessor row.
        """

        from ...rails.phase_material import (  # noqa: PLC0415 (cycle guard)
            build_material_for_phase,
            load_phase_material_specs,
            phase_material_receipt,
            render_static_instruction,
            resolve_response_formats,
            sealed_states_from_manifest,
        )
        from ...rails.runner import (  # noqa: PLC0415 (cycle guard)
            _protected_knowledge_material,
        )

        if not self.uses_speech_feature_packets():
            raise FlightRuntimeError(
                f"arm {self._arm()!r} does not travel the speech-feature packet path, but "
                f"policy {getattr(program, 'program_id', program)!r} is a phase program: "
                "rails.runner's agent loop binds one input_speech_features query packet "
                "per contact and rails.core_client refuses Agent history without it"
            )
        snapshot = self._load_knowledge_snapshot()
        specs = load_phase_material_specs(self._composed.values, program)
        static_text = {
            phase: render_static_instruction(
                spec, self._repo_root, self._lock, self._data_root
            )
            for phase, spec in specs.items()
        }
        formats = resolve_response_formats(specs, self._lock, self._data_root)

        sample_ids = tuple(sample.sample_id for sample in self._samples)
        per_sample_states: dict[str, Mapping[str, object]] = {}
        for phase, spec in specs.items():
            if spec.predecessor_binding != "sealed-manifest":
                continue
            source = spec.predecessor_source
            per_sample_states[phase] = sealed_states_from_manifest(
                self._data_root / str(source["manifest_relpath"]),
                expected_sha256=str(source["manifest_sha256"]),
                phase_name=phase,
                producer_policy_id=str(source["producer_policy_id"]),
                sample_ids=sample_ids,
            )

        protected = _protected_knowledge_material(snapshot)
        offenders: list[str] = []
        for phase, text in sorted(static_text.items()):
            lowered = text.casefold()
            if any(material in lowered for material in protected):
                offenders.append(f"instruction[{phase}]")
        for phase, states in sorted(per_sample_states.items()):
            for sample_id, state in sorted(states.items()):
                lowered = state.content.casefold()
                if any(material in lowered for material in protected):
                    offenders.append(f"sealed-state[{phase}][{sample_id}]")
        if offenders:
            raise FlightRuntimeError(
                f"{len(offenders)} phase material item(s) embed frozen knowledge "
                f"key/value payloads, e.g. {offenders[:5]}; rails.runner refuses such a "
                "contact instruction at request time "
                "(_assert_agent_control_excludes_knowledge_payloads), so this would have "
                "died mid-roster. Acquire that material through traced knowledge supply "
                "instead"
            )

        self._phase_material_receipt = phase_material_receipt(
            specs, static_text, formats
        )
        supply_for_phase, supply_specs = self._resolve_phase_supply(program, snapshot)
        review_for_phase, review_specs = self._resolve_phase_review(program)
        return {
            "knowledge_snapshot": snapshot,
            "speech_packet_bindings": self.speech_packet_bindings(),
            "material_for_phase": build_material_for_phase(
                specs,
                program_id=program.program_id,
                static_text_by_phase=static_text,
                response_format_by_phase=formats,
                per_sample_states=per_sample_states,
            ),
            "supply_for_phase": supply_for_phase,
            "supply_specs": supply_specs,
            "review_for_phase": review_for_phase,
            "review_specs": review_specs,
            "trace_sink": client,
        }

    def _resolve_phase_review(
        self, program: object
    ) -> tuple[object | None, Mapping[str, object]]:
        """Resolve the baseline fragment's ``phase_review`` into the
        ``review_for_phase`` callable ``rails.controllers`` consults (owner
        Decision 11-B change #1, 2026-09-08).

        Config only, and fail-closed before any contact: every judge id must
        resolve in ``core.base.JUDGES``, every reviewed phase must be one the
        program declares, and ``on_flag: "loop"`` is refused by name until
        ``rails.runner``'s state-id/contact-id rails admit a re-ask
        (``rails.phase_review.LOOP_REFUSAL_REASON``).

        Returns ``(None, {})`` for a fragment that reviews nothing -- which
        is byte-identical to every cell written before this wave.
        """

        from ...rails.phase_review import (  # noqa: PLC0415 (cycle guard)
            PhaseReviewError,
            build_review_for_phase,
            load_phase_review_specs,
            phase_review_receipt,
        )

        try:
            specs = load_phase_review_specs(self._composed.values, program)
        except PhaseReviewError as error:
            raise FlightRuntimeError(str(error)) from None
        if not specs:
            self._phase_review_receipt = None
            return None, {}
        review_for_phase = build_review_for_phase(
            specs, extra_material=self._phase_review_material
        )
        # The pre-flight receipt: the spec, with zero rows reviewed. It is
        # replaced after dispatch by the same call over the reviewer that
        # actually ran, so a receipt exists even if the flight dies mid-roster.
        self._phase_review_receipt = phase_review_receipt(specs)
        return review_for_phase, specs

    def bind_phase_review_material(
        self, material: Mapping[str, Mapping[str, Mapping[str, object]]]
    ) -> None:
        """Inject ``{phase: {judge_id: material}}`` for the judges of a
        reviewed phase.

        A judge's own knobs ride the config fragment's
        ``phase_review.<phase>.params`` and therefore the config hash; the
        CARRIER material a judge reads -- a legal ``(scenario, action)``
        inventory, a per-intent slot-type block, a candidate roster -- is far
        too large for a fragment, exactly as a knowledge provider's artifact
        is (:meth:`bind_phase_supply_providers`). This seam supplies that
        material, never the judge's identity: the id still has to resolve in
        ``core.base.JUDGES``, and a config param wins any key collision.
        """

        if not isinstance(material, Mapping) or not material:
            raise FlightRuntimeError(
                "bind_phase_review_material needs a non-empty "
                "{phase: {judge_id: material}} mapping"
            )
        self._phase_review_material = {
            str(phase): dict(entry or {}) for phase, entry in material.items()
        }

    def _resolve_phase_supply(
        self, program: object, snapshot: object
    ) -> tuple[object | None, Mapping[str, object]]:
        """Resolve the baseline fragment's ``phase_supply`` into the
        ``supply_for_phase`` callable ``rails.controllers`` consults (E6).

        Config only: every id resolves in a ``core.base`` registry, every
        vector file is pinned by sha256 and re-hashed here, and NOTHING this
        returns can put text on a control turn -- a supplied phase's
        instruction is byte-identical to the same phase's unsupplied one
        (``rails.controllers``, "Traced supply").

        Refusals, all before any contact:

        * a ``phase_supply`` entry for a phase the program does not declare,
          or for a phase whose ``PhaseSpec.knowledge`` is not ``"supplied"``
          (``rails.phase_supply.load_phase_supply_specs``);
        * a supplied FIRST phase, which cannot carry an ``acquire``
          transition because no ``advance`` precedes it. Its selection is
          per-sample seeded into the initial ``QueryState`` instead, through
          ``rails.runner``'s ``bootstrap_value_ids`` mapping form -- but the
          decision has to be computable before the flight, so it is refused
          here unless the phase's provider is ``kb-facet-v1`` (which this
          seam constructs from the frozen snapshot) or an instance was
          injected through :meth:`bind_phase_supply_providers`;
        * an ``embedding-server`` query source (declared, never resolvable).
        """

        from ..preparation import PreparationError
        from ...rails.phase_supply import (  # noqa: PLC0415 (cycle guard)
            build_supply_for_phase,
            load_phase_supply_specs,
            phase_supply_receipt,
        )

        specs = load_phase_supply_specs(self._composed.values, program)
        if not specs:
            self._phase_supply_receipt = None
            return None, {}
        first_phase = program.phase_names()[0]
        if (
            first_phase in specs
            and self._phase_supply_providers is None
            # ``build_supply_for_phase`` CONSTRUCTS 'kb-facet-v1' itself -- its
            # whole state is the frozen snapshot this runtime already loaded and
            # hash-verified -- and publishes the factory on
            # ``supply_for_phase.provider_factories``, which is exactly what
            # ``_phase_supply_seeds`` reads to compute the pre-flight bootstrap
            # selection. So the requirement the message below states ("the
            # decision has to be computable before the flight") is already met
            # for that provider, and refusing it forced a launcher script the
            # owner's engineering base rules forbid (cell KU-S3, 2026-09-07).
            # Every other registered provider still needs its instance injected.
            and specs[first_phase].provider != "kb-facet-v1"
        ):
            raise FlightRuntimeError(
                f"phase_supply declares the FIRST phase {first_phase!r} of program "
                f"{getattr(program, 'program_id', program)!r} with provider "
                f"{specs[first_phase].provider!r}. A first phase has no "
                "preceding advance, so it cannot carry an acquire transition; its "
                "selection has to be computed before the flight and seeded into each "
                "sample's initial QueryState, and this seam can only construct "
                "'kb-facet-v1' on its own. Bind the built provider through "
                "bind_phase_supply_providers so this runtime can compute it, or move "
                "the supply to a later phase"
            )
        providers = self._phase_supply_providers
        prepared_recall = None
        prepared_pin = self._composed.values.get("prepared_phase_recall")
        if prepared_pin is not None:
            if not isinstance(prepared_pin, Mapping) or set(prepared_pin) != set(specs):
                raise PreparationError("prepared_phase_recall must name exactly the supplied phases")
            if providers is not None or any(spec.provider != "kb-facet-v1" for spec in specs.values()):
                raise PreparationError("prepared recall cannot be ignored by an injected provider")
            prepared_recall = {
                phase: self._load_phase_recall(
                    prepared_pin[phase], {"knowledge_snapshot": snapshot, "speech_packet_bindings": self.speech_packet_bindings()}, specs[phase], self._prepare()[3]
                )
                for phase in specs
                if phase in prepared_pin
            }
            if set(prepared_recall) != set(specs):
                raise PreparationError("prepared_phase_recall must cover every supplied phase")
        supply_for_phase = build_supply_for_phase(
            specs,
            snapshot=snapshot,
            snapshot_sha256=snapshot.content_hash(),
            data_root=self._data_root,
            provider_for_phase=(
                None if providers is None else lambda phase: providers.get(phase)
            ),
            prepared_recall_by_phase=prepared_recall,
            seed_phases=(first_phase,) if first_phase in specs else (),
        )
        self._phase_supply_receipt = phase_supply_receipt(
            specs,
            getattr(supply_for_phase, "query_vector_rows", {}),
            getattr(supply_for_phase, "facet_vector_rows", {}),
        )
        return supply_for_phase, specs

    def bind_phase_supply_providers(
        self, providers: Mapping[str, object]
    ) -> None:
        """Inject a built ``rails.knowledge_provider.KnowledgeProvider`` per
        supplied phase (E6).

        ``rails.phase_supply`` can construct ``kb-facet-v1`` on its own --
        its whole state IS the frozen ``KnowledgeSnapshot`` this runtime
        already loaded and hash-verified. Every other registered provider
        needs an artifact this harness has no way to build from a snapshot
        (the Audio2Tool ``dense-centroid-v1`` semantic index), so it comes
        in here rather than through a launcher script. The provider id in
        the fragment still has to resolve in
        ``core.base.KNOWLEDGE_PROVIDERS``; this seam supplies the INSTANCE,
        never the identity.
        """

        if not isinstance(providers, Mapping) or not providers:
            raise FlightRuntimeError(
                "bind_phase_supply_providers needs a non-empty {phase: provider} mapping"
            )
        self._phase_supply_providers = dict(providers)

    def bind_phase_program_material(
        self,
        *,
        knowledge_snapshot: object,
        speech_packet_bindings: Mapping[str, Mapping[str, object]],
        material_for_phase: Callable[..., object],
        supply_for_phase: Callable[..., object] | None = None,
        review_for_phase: Callable[..., object] | None = None,
        trace_sink: object | None = None,
    ) -> None:
        """Bind the caller-supplied, genuinely task-specific material a
        phase-program baseline's :meth:`run_phases` needs
        (``rails.phase_runner.run_program`` requires ``knowledge_snapshot``/
        ``speech_packet_bindings``/``material_for_phase`` and this generic
        harness builds none of them on its own -- they encode which
        knowledge BUILD a flight consumes and what each phase's instruction
        text is). A no-op for a ``policy == "fixed"`` direct-arm baseline."""

        self._phase_program_material = {
            "knowledge_snapshot": knowledge_snapshot,
            "speech_packet_bindings": speech_packet_bindings,
            "material_for_phase": material_for_phase,
            "supply_for_phase": supply_for_phase,
            "supply_specs": {},
            "review_for_phase": review_for_phase,
            "review_specs": {},
            "trace_sink": trace_sink,
        }

    # -- stage 5: seal --------------------------------------------------

    #: The twelve ledger columns ``core.tracking.bundle_ledger_cells``
    #: deliberately does NOT derive -- "human judgment or external-index
    #: facts this module has no basis to invent", its own words.
    #: ``core.bundle.finalize_bundle`` validates the COMPLETE 21-column
    #: surface before scoring, so a caller that supplies none of these makes
    #: finalize refuse with "ledger row must have exactly the columns ...".
    #: seal() supplied none, so every flight died at the finalizer AFTER its
    #: contacts were spent.
    CALLER_LEDGER_COLUMNS = (
        "experiment_id",
        "speech task/carrier",
        "changed axes",
        "shared code revision",
        "model rev",
        "dataset rev",
        "MLflow run",
        "effectiveness",
        "reasonableness",
        "efficiency",
        "deviations",
        "decision",
    )

    #: What the four judgment columns say before anyone has judged anything.
    #: A run seals before its verdict is written, so inventing a verdict here
    #: would be worse than saying so.
    PENDING_JUDGMENT = "pending post-run analysis"

    def _default_ledger_cells(self, plan: ExecutionPlan) -> dict[str, str]:
        """The twelve caller-owned ledger cells, derived from this flight's
        own composed identity where that is honest and marked pending where
        it is a judgment nobody has made yet. A caller passing
        ``seal(ledger_cells=...)`` overrides any of them."""

        values = self._composed.values
        fragments = dict(self._composed.fragments)
        return {
            "experiment_id": str(values.get("experiment_id", self._run_id)),
            "speech task/carrier": (
                f"{plan.carrier_lock_key}; split {self._split_id}; "
                f"{len(self._samples)} samples"
            ),
            "changed axes": (
                "model={model}; dataset={dataset}; baseline={baseline}; "
                "experiment={experiment}".format(**fragments)
            ),
            "shared code revision": (
                "none; this study declares no speechrl_common dependency"
            ),
            "model rev": str(values.get("model_lock_key", "")),
            "dataset rev": str(plan.split_identity_hash),
            "MLflow run": "not used",
            "effectiveness": self.PENDING_JUDGMENT,
            "reasonableness": self.PENDING_JUDGMENT,
            "efficiency": self.PENDING_JUDGMENT,
            "deviations": self.PENDING_JUDGMENT,
            "decision": self.PENDING_JUDGMENT,
        }

    @staticmethod
    def response_arrival_counts(client: object) -> dict[str, object]:
        """How this cell's responses ARRIVED: native tool calls versus text.

        The transport canonicalizes native ``message.tool_calls`` into the
        same ``[{"name": ..., "arguments": {...}}]`` text a free-text arm
        produces -- which is what lets one scorer serve both arms, and is
        exactly why a sealed outputs row cannot be read back to tell them
        apart. The calibration smoke hit that ambiguity: three of four
        native-arm rows were canonical JSON arrays with nothing recording
        which mechanism produced them. This counts it at the one place that
        still knows (``rails.core_client.RequestTiming.native_tool_calls``,
        set from the adapter's own ``CoreResponse.tool_calls``) and puts the
        answer in the run receipt, changing no audited artifact.
        """

        timings = tuple(getattr(client, "timings", ()) or ())
        native_rows = [t for t in timings if getattr(t, "native_tool_calls", None) is not None]
        return {
            "rows_total": len(timings),
            "rows_with_native_tool_calls": len(native_rows),
            "rows_answered_as_text": len(timings) - len(native_rows),
            "native_tool_calls_total": sum(
                int(t.native_tool_calls) for t in native_rows
            ),
            "basis": (
                "rails.core_client.RequestTiming.native_tool_calls, set from "
                "core.model.CoreResponse.tool_calls; None means the response envelope "
                "carried no tool_calls key at all, i.e. the model answered as text"
            ),
        }

    def _canonical_output_rows(self, client: object) -> list[Mapping[str, object]]:
        """The outputs rows ``core.bundle.verify_bundle`` actually requires.

        ``core.bundle.outputs._REQUIRED_OUTPUTS_FIELDS`` is a hash-bound
        audit contract -- ``request_id``, ``sample_id``, ``carrier_lock_key``,
        ``arm``, ``text``, ``admitted`` and the three identity hashes -- and
        it binds each row's ``carrier_lock_key``/``arm`` to the manifest and
        re-derives ``response_text_sha256`` from ``text``. This stage used to
        write its own loose diagnostic dict instead (``messages``/
        ``metrics``/``consumption``), so a sealed rails flight could never
        verify: the bundle refused with "outputs line 1 lacks required
        fields" AFTER every contact had been spent.

        The hashes come from the client's own per-request records
        (``rails.core_client.RequestTiming``), which is where the adapter's
        ``CoreResponse`` identity now lands. One row per sample, as the
        contract requires (it refuses duplicate sample ids); when a policy
        made several contacts for one sample, the LAST one is the response
        that stands.
        """

        timing_by_sample: dict[str, object] = {}
        for timing in getattr(client, "timings", ()) or ():
            timing_by_sample[timing.sample_id] = timing
        arm = self._arm()
        # Defence in depth for the multi-phase path: the bundle refuses
        # duplicate sample ids only inside ``core.bundle.outputs.seal``,
        # i.e. after every contact has already been spent.
        # ``_rows_from_phase_summaries`` now reduces a program to one row
        # per sample, and this says so HERE, where the failure is still
        # free, rather than trusting that it always will.
        seen: list[str] = [str(row.get("sample_id")) for row in self._output_rows]
        duplicates = sorted({sid for sid in seen if seen.count(sid) > 1})
        if duplicates:
            raise FlightRuntimeError(
                f"{len(duplicates)} sample id(s) appear more than once in the rows to "
                f"seal, e.g. {duplicates[:5]}; the bundle contract accepts exactly one "
                "outputs row per sample (a policy that made several contacts for one "
                "sample seals the LAST response, never one row per contact)"
            )
        rows: list[Mapping[str, object]] = []
        for row in self._output_rows:
            sample_id = str(row.get("sample_id"))
            # The Earnings/obs dispatch reads its rows back from the obs
            # driver's own sealed outputs, which ARE this contract's field
            # set: the three hashes there are the STITCH descriptors the obs
            # policy computed over that sample's per-window requests and
            # responses, and no client timing exists (or could) for a
            # multi-window stitch. Passed through unchanged, because a second
            # opinion about a stitched hypothesis' identity is exactly what
            # this stage must not have.
            if not (_OBS_OUTPUTS_FIELDS - set(row)):
                rows.append(dict(row))
                continue
            timing = timing_by_sample.get(sample_id)
            if timing is None:
                raise FlightRuntimeError(
                    f"no per-request record for sample {sample_id!r}; an outputs row "
                    "cannot be sealed without the response identity hashes the bundle "
                    "contract requires"
                )
            text = row.get("response_text")
            if text is None:
                text = row.get("final_response_text")
            if not isinstance(text, str):
                raise FlightRuntimeError(
                    f"sample {sample_id!r} produced no response text to seal"
                )
            missing = [
                name
                for name in ("request_sha256", "response_sha256", "response_text_sha256")
                if not getattr(timing, name, None)
            ]
            if missing:
                raise FlightRuntimeError(
                    f"per-request record for sample {sample_id!r} lacks {missing}; the "
                    "bundle contract binds an outputs row to its response bytes"
                )
            rows.append(
                {
                    "request_id": timing.request_id,
                    "sample_id": sample_id,
                    "carrier_lock_key": self._plan.carrier_lock_key
                    if self._plan is not None
                    else self._composed.values["carrier_lock_key"],
                    "arm": arm,
                    "text": text,
                    "admitted": True,
                    "request_sha256": timing.request_sha256,
                    "response_sha256": timing.response_sha256,
                    "response_text_sha256": timing.response_text_sha256,
                }
            )
        return rows


    def seal(
        self,
        *,
        flight_receipt_kwargs: Mapping[str, object] | None = None,
        ledger_cells: Mapping[str, str] | None = None,
        defer_scoring: bool = False,
    ) -> Mapping[str, object]:
        """Write ``<run_id>.outputs.jsonl`` from the samples ``run_phases``
        produced,
        close the client (which closes its owned ``TraceSink`` -- "write
        outputs JSONL + trace via the client's sink"), then
        ``manifest_builder`` (default ``core.bundle.manifest.
        build_manifest``), ``bundle_verifier`` (default ``core.bundle.
        verify.verify_bundle``) and ``bundle_finalizer`` (default
        ``core.bundle.finalize.finalize_bundle``) in that order. When
        ``flight_receipt_kwargs`` is given, additionally mints a
        disk-derived flight receipt via ``flight_receipt_builder`` (default
        ``core.driver.speech_native.build_flight_receipt_from_disk``,
        resolved lazily -- see the module-level import note); the exact
        extra keys that function needs (``profile_identity``,
        ``contact_ceiling_per_task``, ...) are genuinely flight-specific and
        are therefore supplied by the caller, not derived generically here
        (see the C4c report's residual list)."""

        self._require_prior_stages("seal")
        from ..bundle.delivery_replay import validate_phase_delivery_sources

        deliveries = validate_phase_delivery_sources(
            self._composed.values, parent_fragments={
                "model_fragment": self._model,
                "dataset_fragment": self._dataset,
                "baseline_fragment": self._baseline,
            },
        )
        run_dir = self._run_dir()
        run_dir.mkdir(parents=True, exist_ok=True)
        # `<run_id>.outputs.jsonl`, not `outputs.jsonl`: the cost scorer
        # locates a run's manifest by the shared run_id stem
        # (core.scorers._manifest_path_for_outputs, the same convention
        # core.bundle.build_manifest uses for `<run_id>.run-manifest.json`)
        # and refuses any other name. Writing the bare name made official
        # scoring fail AFTER every contact had been spent.
        outputs_path = run_dir / f"{self._plan.run_id}.outputs.jsonl"
        canonical_rows = self._canonical_output_rows(self._client)
        with outputs_path.open("w", encoding="utf-8") as handle:
            for row in canonical_rows:
                handle.write(
                    json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
                )

        # `<run_id>.phases.json`: every phase summary, in program order,
        # beside the sealed outputs. The bundle contract accepts one outputs
        # row per sample, so a two-contact cell's FIRST phase responses have
        # nowhere to live inside the manifest -- and they are exactly what a
        # per-phase parse rate, a select-then-fill error attribution or a
        # "which phase changed the answer" read needs. Written next to the
        # outputs rather than inside them, and recorded here with its own
        # sha256, so it is auditable without being part of the hash-bound
        # audit contract ``core.bundle.verify`` enforces (that contract, and
        # ``core.bundle.manifest``, are deliberately untouched).
        phases_path: Path | None = None
        if self._phase_summaries:
            phases_path = run_dir / f"{self._plan.run_id}.phases.json"
            phases_path.write_text(
                json.dumps(
                    {
                        "schema": "saea-flight-phase-summaries-v1",
                        "run_id": self._plan.run_id,
                        "attempt_id": self._plan.attempt_id,
                        "policy": self._composed.values.get("policy"),
                        "phases": [
                            summary.as_json() for summary in self._phase_summaries
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                    default=str,
                )
                + "\n",
                encoding="utf-8",
                newline="\n",
            )

        if self._obs_result is not None:
            # The Earnings/obs dispatch: the obs driver already closed its own
            # sink and returned this run's arm, trace manifest hash and
            # MEASURED cost. There is no client to close -- building one would
            # have opened this attempt twice -- so the close receipt is that
            # RunResult, read rather than recomputed.
            close_receipt = {
                "arm": self._obs_result.arm,
                "trace_manifest_hash": self._obs_result.trace_manifest_hash,
                "cost": self._obs_result.cost,
            }
        else:
            close_receipt = self._client.close()
        result = RunResult(
            run_id=self._plan.run_id,
            arm=close_receipt["arm"],
            outputs_path=outputs_path,
            trace_manifest_hash=close_receipt["trace_manifest_hash"],
            cost=close_receipt["cost"],
        )

        sample_ids = tuple(sample.sample_id for sample in self._samples)
        verified_split = VerifiedSplit(
            name=self._split_id,
            carrier_lock_key=self._plan.carrier_lock_key,
            split_role=self._plan.split_role,
            ids=tuple(sorted(sample_ids)),
            prefixed_ids=tuple(prefixed(self._plan.carrier_lock_key, sample_ids)),
            identity_hash=self._plan.split_identity_hash,
        )

        manifest_path = self._manifest_builder(
            repo_root=self._repo_root,
            data_root=self._data_root,
            composed=self._composed,
            plan=self._plan,
            verified_split=verified_split,
            session_receipt_path=self._session_receipt_path,
            run_dir=run_dir,
            status="COMPLETED",
            result=result,
        )
        verified = self._bundle_verifier(manifest_path)
        merged_ledger_cells = self._default_ledger_cells(self._plan)
        merged_ledger_cells.update(dict(ledger_cells or {}))
        missing = [
            column
            for column in self.CALLER_LEDGER_COLUMNS
            if column not in merged_ledger_cells
        ]
        if missing:
            raise FlightRuntimeError(
                f"ledger cells are missing the caller-owned column(s) {missing}; "
                "core.bundle.finalize_bundle validates the complete ledger surface "
                "before it will score"
            )
        deferred_scoring = None
        if deliveries or defer_scoring or self._execution_policy is not None:
            from .scoring import seal_scoring_inputs
            # Validate caller cells now; the official finalizer validates them
            # again after root releases generation custody.
            self._ledger_validator(verified, merged_ledger_cells)
            deferred_scoring = seal_scoring_inputs(
                manifest_path, run_id=self.run_id, attempt_id=self.attempt_id,
                ledger_cells=merged_ledger_cells,
                delivery_cells=[item["cell_id"] for item in deliveries],
            )
            finalize_payload = deferred_scoring["finalize"]
        else:
            finalize_result = self._bundle_finalizer(
                manifest_path,
                self._lock,
                self._data_root,
                repo_root=self._repo_root,
                ledger_cells=merged_ledger_cells,
            )
            finalize_payload = {
                "scores_path": str(finalize_result.scores_path),
                "ledger_markdown_path": str(finalize_result.ledger_markdown_path),
                "attempt_state": finalize_result.attempt_state,
            }

        flight_receipt: Mapping[str, object] | None = None
        if flight_receipt_kwargs is not None:
            builder = self._flight_receipt_builder
            if builder is None:
                from ..driver.speech_native import (  # noqa: PLC0415 (cycle guard, module note)
                    build_flight_receipt_from_disk,
                )

                builder = build_flight_receipt_from_disk
            merged = dict(flight_receipt_kwargs)
            merged.setdefault("attempt_dir", run_dir)
            merged.setdefault("plan", self._plan)
            merged.setdefault("config_hash", self._composed.config_hash)
            flight_receipt = builder(**merged)

        # E7: what the card did while this attempt held it. Recorded only
        # for a flight that ATTACHED to an always-on serving session (a
        # flight that spawned its own server has no monitor beside it), and
        # folded back into the attach receipt so the attempt's own directory
        # carries the GPU accounting beside its outputs.
        serving_monitor_summary = self.serving_monitor_summary()
        if serving_monitor_summary is not None and self._session_attach_receipt is not None:
            self._session_attach_receipt["monitor_summary"] = dict(serving_monitor_summary)
            self._session_attach_receipt["contact_window"] = {
                "from": self._contact_window[0],
                "to": self._contact_window[1],
            }
            self._write_session_attach_receipt()

        payload = {
            "manifest_path": str(manifest_path),
            "manifest_sha256": _sha256_file(manifest_path),
            "session_reused": self._serving_session_dir is not None,
            "session_attach_receipt_path": (
                str(self._session_attach_receipt_path)
                if self._session_attach_receipt_path is not None
                else None
            ),
            "serving_monitor_summary": serving_monitor_summary,
            "verified_attempt_state": getattr(verified, "attempt_state", None),
            "outputs_path": str(outputs_path),
            "outputs_row_count": len(self._output_rows),
            "phases_path": str(phases_path) if phases_path is not None else None,
            "phases_sha256": (
                _sha256_file(phases_path) if phases_path is not None else None
            ),
            "phase_count": len(self._phase_summaries),
            "trace_manifest_hash": close_receipt["trace_manifest_hash"],
            "cost": close_receipt["cost"],
            "ledger_cells": merged_ledger_cells,
            "finalize": finalize_payload,
            "flight_receipt": flight_receipt,
        }
        if deferred_scoring is not None:
            payload.update(deferred_scoring)
        return self.receipts.record("seal", payload)

    # -- stage 6: score ---------------------------------------------------

    def score(
        self,
        *,
        max_workers: int = 1,
        output_dir: Path | None = None,
        include_per_sample: bool = False,
    ) -> Mapping[str, object]:
        """``load_score_jobs`` + ``score_batch`` (default
        ``core.scoring_batch.run_score_batch``) over the exactly-one manifest
        :meth:`seal` sealed -- one job per complete manifest, never sharded
        (``core.scoring_batch``'s own module docstring).

        ``include_per_sample`` is forwarded to ``run_score_batch`` and
        recorded in this stage's receipt. It is what the evolution loop reads:
        a round's selection rule counts SAVES and HARMS per row against the
        incumbent (``rails.evolution``), which needs the per-sample scores the
        batch otherwise summarizes away. Default ``False``, so every existing
        caller's receipt and result shape are unchanged.
        """

        self._require_prior_stages("score")
        seal_payload = self.receipts.require("seal")
        if seal_payload.get("delivery_required"):
            raise FlightRuntimeError(
                "raw phase parent requires declared delivery: use build-delivery, "
                "then score the derived manifest through score-batch"
            )
        manifest_path = Path(seal_payload["manifest_path"])
        run_dir = self._run_dir()
        jobs_path = run_dir / "score-jobs.jsonl"
        score_kwargs = {}
        if seal_payload.get("finalize", {}).get("status") == "deferred-to-score-worker":
            from .scoring import load_sealed_score_jobs
            jobs = load_sealed_score_jobs(seal_payload)
            score_kwargs["operation"] = "finalize"
            include_per_sample = True
        else:
            with jobs_path.open("w", encoding="utf-8") as handle:
                handle.write(
                    json.dumps({"job_id": self._plan.attempt_id, "manifest": str(manifest_path)}) + "\n"
                )
            jobs = load_score_jobs(jobs_path)
        resolved_output_dir = Path(output_dir) if output_dir is not None else run_dir / "score-batch"

        started = self._clock()
        result = self._score_batch(
            jobs,
            output_dir=resolved_output_dir,
            max_workers=max_workers,
            include_per_sample=include_per_sample,
            **score_kwargs,
        )
        duration = max(self._clock() - started, 1e-9)

        payload = {
            "jobs_path": str(jobs_path),
            "output_dir": str(resolved_output_dir),
            "job_count": len(jobs),
            "include_per_sample": bool(include_per_sample),
            "duration_seconds": duration,
            "jobs_per_second": len(jobs) / duration,
            "result": result,
        }
        if seal_payload.get("finalize", {}).get("status") == "deferred-to-score-worker":
            payload["source_generation_manifest_sha256"] = seal_payload["generation_manifest_sha256"]
            payload["finalized_manifest_sha256"] = (
                _sha256_file(manifest_path) if not result.get("failed", 0) else None
            )
            payload["operation"] = "finalize"
        require_mandatory_throughput_fields("score", payload, ("jobs_per_second",))
        return self.receipts.record("score", payload)

    # -- contact-free wiring proof -----------------------------------------

    def _wire_check_obs_policy(
        self,
        *,
        carrier_lock_key: str,
        split_id: str,
        identity_hash: str,
        arm: str,
        policy: str,
        declared: Mapping[str, object],
        wire_run_id: str,
        wire_attempt_id: str,
        run_dir: Path,
        response_text: str,
        request_payload_observer: Callable[[Mapping[str, object]], None] | None,
    ) -> Mapping[str, object]:
        """Exercise the shared OJW OBS driver against contact-free doubles.

        The supported OJW fixed-window policies choose a variable number of
        exact windows before dispatch. Materialize through the production
        window seam first, then give the production OBS driver an attempt
        sized to those requests.
        """

        def _plan(planned_model_calls: int) -> ExecutionPlan:
            return ExecutionPlan(
                run_id=wire_run_id,
                execution_profile=declared["execution_profile"],
                carrier_lock_key=carrier_lock_key,
                split_role=declared["split_role"],
                split_identity_hash=identity_hash,
                planned_model_calls=planned_model_calls,
                planned_gpu_hours=declared["planned_gpu_hours"],
                planned_speech_audio_seconds=declared[
                    "planned_speech_audio_seconds"
                ],
                protocol_hash=compute_protocol_hash(
                    self._composed.config_hash, arm, identity_hash
                ),
                attempt_id=wire_attempt_id,
            ).validate()

        gate = WireCheckGate()
        transport = WireCheckTransport(response_text=response_text)
        saved = {
            name: getattr(self, name)
            for name in (
                "_run_id",
                "_attempt_id",
                "_plan",
                "_gate",
                "_transport",
                "_explicit_run_dir",
                "_client",
                "_obs_result",
                "_output_rows",
                "_composed",
                "_adapter",
                "_split_id",
                "_samples",
                "_lock",
            )
        }
        dispatch_started = False
        aborted = False
        receipt: Mapping[str, object] | None = None
        observed_payloads: list[Mapping[str, object]] = []
        try:
            # Window derivation and driver artifacts both belong to the fresh
            # synthetic identity. Never cut media under the registered run's
            # route namespace or write into its attempt directory.
            self._run_id = wire_run_id
            self._attempt_id = wire_attempt_id
            self._explicit_run_dir = run_dir
            self._gate = gate
            self._transport = transport
            self._client = None

            provisional = _plan(max(len(self._samples), 1))
            window_batch = self.materialize_window_batch(execution_plan=provisional)
            selected_window_count = len(window_batch.request_keys)
            if selected_window_count < 1:
                raise FlightRuntimeError(
                    "OBS wire check materialized no selected window requests"
                )
            plan = _plan(selected_window_count)
            self._plan = plan
            started = self._clock()
            dispatch_started = True
            rows, contact_count, policy_kind, dispatch, result = (
                self._dispatch_obs_policy(plan)
            )
            wall_seconds = max(self._clock() - started, 1e-9)

            expected_fields = set(ARM_VISIBLE_FIELDS.get(arm, ()))
            from ..preparation_fit import boundary_identity  # noqa: PLC0415

            expected_request_ids = sorted(
                str(payload.get("request_id")) for payload in window_batch.payloads
            )
            actual_request_ids = sorted(
                str(payload.get("request_id")) for payload in transport.payloads
            )
            problems: list[str] = []
            if contact_count != selected_window_count:
                problems.append(
                    f"driver reported {contact_count} synthetic contact(s) for "
                    f"{selected_window_count} selected window(s)"
                )
            if len(transport.payloads) != selected_window_count:
                problems.append(
                    f"fake transport received {len(transport.payloads)} request(s) for "
                    f"{selected_window_count} selected window(s)"
                )
            if len(set(expected_request_ids)) != len(expected_request_ids):
                problems.append(
                    "actual window materialization produced duplicate request identities"
                )
            if len(set(actual_request_ids)) != len(actual_request_ids):
                problems.append(
                    "fake transport received duplicate request identities"
                )
            try:
                expected_boundary = boundary_identity(
                    window_batch.payloads, window_routes=True
                )
                actual_boundary = boundary_identity(
                    transport.payloads, window_routes=True
                )
            except Exception as error:
                problems.append(f"window payload normalization refused: {error}")
            else:
                if actual_boundary != expected_boundary:
                    problems.append(
                        "fake transport payloads differ from the complete normalized "
                        "materialized-window boundary"
                    )
            stitched_ids = [row.get("sample_id") for row in rows]
            expected_samples = {sample.sample_id for sample in self._samples}
            if (
                len(rows) != len(self._samples)
                or any(not isinstance(sample_id, str) for sample_id in stitched_ids)
                or len(set(stitched_ids)) != len(stitched_ids)
                or set(stitched_ids) != expected_samples
            ):
                problems.append(
                    "OBS driver stitched output roster differs from the complete "
                    "unique runtime sample roster"
                )
            if len(gate.checked_plans) != 1 or gate.checked_plans[0] != plan:
                problems.append(
                    "fake gate did not observe exactly the final exact-window plan"
                )
            for index, payload in enumerate(transport.payloads):
                if set(payload) != expected_fields:
                    problems.append(
                        f"request {index} payload keys differ from "
                        f"ARM_VISIBLE_FIELDS[{arm!r}]: "
                        f"{sorted(set(payload) ^ expected_fields)}"
                    )
            if problems:
                raise FlightRuntimeError("OBS wire check failed: " + "; ".join(problems))

            observed_payloads = [
                json.loads(json.dumps(payload)) for payload in transport.payloads
            ]
            first = transport.payloads[0]
            receipt = {
                "schema": "saea-flight-wire-check-v1",
                "flight_run_id": saved["_run_id"],
                "wire_check_run_id": wire_run_id,
                "attempt_id": wire_attempt_id,
                "attempt_aborted": True,
                "config_hash": self._composed.config_hash,
                "protocol_hash": plan.protocol_hash,
                "split_id": split_id,
                "split_identity_hash": identity_hash,
                "arm": arm,
                "native_tools_arm": "tool_schemas" in expected_fields,
                "construction_proposer_arm": False,
                "construction_draws": [],
                "sample_count": len(self._samples),
                "selected_window_count": selected_window_count,
                "contact_count": contact_count,
                "contacts_per_sample": dispatch["contacts_per_sample"],
                "fake_gate_attempts": len(gate.checked_plans),
                "fake_transport_requests": len(transport.payloads),
                "policy": policy,
                "policy_kind": policy_kind,
                "phases": [],
                "dispatch": dispatch,
                "wall_seconds": wall_seconds,
                "payload_keys": sorted(first),
                "payload_keys_equal_arm_visible_fields": True,
                "request_ids": actual_request_ids,
                "request_body_sha256": [
                    hashlib.sha256(body).hexdigest()
                    for body in transport.request_bodies
                ],
                "trace_manifest_hash": result.trace_manifest_hash,
                "cost": dict(result.cost),
                "seal_and_score": {
                    "status": "SKIPPED",
                    "reason": "OBS synthetic wire checks do not seal or score",
                },
                "transport": (
                    "core.flight.runtime.WireCheckTransport (never opens a socket)"
                ),
                "gate": "core.flight.runtime.WireCheckGate (authorizes nothing real)",
                "model_contacts": 0,
            }
        finally:
            try:
                if dispatch_started:
                    aborted = self._abort_attempt(
                        self._data_root,
                        wire_run_id,
                        wire_attempt_id,
                        reason=(
                            "OBS wire check: contact-free wiring proof, no model was ever reached"
                        ),
                    )
            finally:
                for name, prior in saved.items():
                    setattr(self, name, prior)
        if dispatch_started and not aborted:
            raise FlightRuntimeError(
                "OBS wire check did not abort its synthetic spent attempt"
            )
        if receipt is None:
            raise FlightRuntimeError("OBS wire check produced no receipt")
        if request_payload_observer is not None:
            for payload in observed_payloads:
                request_payload_observer(payload)
        return receipt

    def wire_check(
        self,
        *,
        seal_and_score: bool = True,
        max_workers: int = 1,
        workers: int | None = None,
        response_text: str = WIRE_CHECK_RESPONSE_TEXT,
        request_payload_observer: Callable[[Mapping[str, object]], None] | None = None,
    ) -> Mapping[str, object]:
        """Drive this flight's ENTIRE request path against a fake transport,
        with zero model contacts, and return a receipt.

        What is real here: the composed fragments, the adapter and its
        samples, the payload binding, the tool-schema resolution, the
        promoted speech-feature packets (loaded and hash-verified), the
        arm's own dispatch (:meth:`_dispatch_fixed_policy`), the whole
        ``FrozenCoreClient``/``FrozenCoreAdapter`` stack including its
        payload allowlist and attempt accounting, and -- when
        ``seal_and_score`` -- the manifest builder, bundle verifier and the
        registered scorers. What is fake: exactly two things, the gate and
        the transport (:class:`WireCheckGate`, :class:`WireCheckTransport`),
        so nothing can reach a server.

        This exists because three separate defects in this harness were each
        discovered only by burning a server start on a registered smoke: the
        client refused the arm, the attempt was double-opened, and the
        slot-affinity sentinel was never resolved. None was visible to
        :meth:`preflight`; all three would have been caught here.

        Everything is written under a :data:`WIRE_CHECK_RUN_ID_PREFIX` run
        id and the attempt it opens is aborted before returning, so no
        registered run's durable accounting is touched.
        """

        values, carrier_lock_key, split_id, identity_hash = self._prepare()
        arm = self._arm()
        # A FRESH run id per invocation. Attempt budget is run-CUMULATIVE
        # across every attempt of a run id (core.model.adapter re-reads the
        # store's prior actuals on every request), so a fixed wire-check run
        # id would let the first cell's contacts exhaust the second cell's
        # budget -- which is exactly what happened the first time this ran.
        policy = values.get("policy")
        if not isinstance(policy, str) or not policy:
            raise FlightRuntimeError("baseline fragment must declare a non-empty 'policy'")
        obs_policy = policy in self._obs_policy_names()
        if obs_policy and seal_and_score:
            raise FlightRuntimeError(
                "OBS wire checks do not support seal_and_score=True: the shared OBS "
                "driver deliberately has no FlightRuntime FrozenCoreClient, and this "
                "synthetic path does not prove bundle scoring"
            )
        if obs_policy and workers is not None:
            raise FlightRuntimeError(
                "OBS wire checks do not accept workers=: OBS request concurrency "
                "is bound by the composed obs_batch_slices configuration"
            )
        # A phase program makes ONE contact per phase per sample. The
        # attempt budget is run-cumulative (core.model.adapter re-reads the
        # store's prior actuals on every request), so a wire-check plan sized
        # for one contact per sample is exhausted the moment the SECOND phase
        # asks for its first contact -- the same defect the fresh run id
        # below already fixed once, in the other dimension.
        contacts_per_sample = None if obs_policy else (
            1 if policy == "fixed" else len(default_phase_program(policy).phases)
        )
        stamp = int(self._clock() * 1000)
        wire_run_id = f"{WIRE_CHECK_RUN_ID_PREFIX}{self._run_id}-{stamp:d}"
        wire_attempt_id = f"attempt-wire-check-{stamp:d}"
        declared = self._composed.values.get("execution_plan")
        if not isinstance(declared, Mapping):
            raise FlightRuntimeError("experiment fragment must declare an execution_plan")
        run_dir = self._data_root / "wire-check" / wire_run_id / wire_attempt_id
        if obs_policy:
            if policy not in ("obs-agent-loop-ojw", "obs-repair-loop-ojw"):
                raise FlightRuntimeError(
                    f"OBS wire check refuses policy {policy!r}: exact-window "
                    "materialization currently supports only the shared OJW policies"
                )
            return self._wire_check_obs_policy(
                carrier_lock_key=carrier_lock_key,
                split_id=split_id,
                identity_hash=identity_hash,
                arm=arm,
                policy=policy,
                declared=declared,
                wire_run_id=wire_run_id,
                wire_attempt_id=wire_attempt_id,
                run_dir=run_dir,
                response_text=response_text,
                request_payload_observer=request_payload_observer,
            )
        assert contacts_per_sample is not None
        plan = ExecutionPlan(
            run_id=wire_run_id,
            execution_profile=declared["execution_profile"],
            carrier_lock_key=carrier_lock_key,
            split_role=declared["split_role"],
            split_identity_hash=identity_hash,
            planned_model_calls=max(len(self._samples) * contacts_per_sample, 1),
            planned_gpu_hours=declared["planned_gpu_hours"],
            planned_speech_audio_seconds=declared["planned_speech_audio_seconds"],
            protocol_hash=compute_protocol_hash(
                self._composed.config_hash, arm, identity_hash
            ),
            attempt_id=wire_attempt_id,
        ).validate()
        run_dir.mkdir(parents=True, exist_ok=True)

        gate = WireCheckGate()
        native = "tool_schemas" in set(ARM_VISIBLE_FIELDS.get(arm, ()))
        proposer = arm_shows_construction_targets(arm)
        transport = WireCheckTransport(
            response_text=response_text, native_tool_calls_on_first=native
        )
        client_kwargs = self.frozen_core_client_kwargs(
            plan=plan, gate=gate, transport=transport, run_dir=run_dir
        )
        packet_bindings = dict(client_kwargs.get("speech_packet_bindings") or {})
        client = self._client_factory(**client_kwargs)
        self._client = client

        started = self._clock()
        phase_receipt: list[Mapping[str, object]] = []
        if policy == "fixed":
            rows, contact_count, policy_kind, dispatch = self._dispatch_fixed_policy(
                client, plan, workers=workers
            )
        else:
            (
                rows,
                contact_count,
                policy_kind,
                dispatch,
                phase_receipt,
            ) = self._dispatch_phase_program(client, plan, policy, model_free_check=True)
        wall_seconds = max(self._clock() - started, 1e-9)
        self._output_rows = rows

        # -- the assertions each landed defect would have failed -----------
        expected_fields = set(ARM_VISIBLE_FIELDS.get(arm, ()))
        expected_payloads = len(self._samples) * contacts_per_sample
        problems: list[str] = []
        max_tokens_binding = self._max_tokens_rule(self._decoding_params())
        max_tokens_per_sample: dict[str, int] = {}
        if len(transport.payloads) != expected_payloads:
            problems.append(
                f"{len(transport.payloads)} request(s) reached the transport for "
                f"{len(self._samples)} sample(s) x {contacts_per_sample} phase(s)"
            )
        for index, payload in enumerate(transport.payloads):
            if set(payload) != expected_fields:
                problems.append(
                    f"request {index} payload keys differ from "
                    f"ARM_VISIBLE_FIELDS[{arm!r}]: "
                    f"{sorted(set(payload) ^ expected_fields)}"
                )
            schemas = payload.get("tool_schemas")
            if native and (not isinstance(schemas, list) or not schemas):
                problems.append(
                    f"request {index} carries no tool_schemas for a native arm"
                )
            if not native and schemas is not None:
                problems.append(
                    f"request {index} carries tool_schemas for a non-native arm"
                )
            request_decoding = dict(payload.get("decoding_params") or {})
            id_slot = request_decoding.get("id_slot")
            if isinstance(id_slot, bool) or not isinstance(id_slot, int):
                problems.append(f"request {index} id_slot is {id_slot!r}, not an integer")
            if max_tokens_binding is not None:
                # The per-sample cap must have become an INTEGER by the time it
                # crossed the transport seam, and it must be exactly the integer
                # the declared policy resolves for THIS request's own audio
                # duration -- the proof that the resolver ran on the sample it
                # was supposed to and not on some cell-wide stand-in.
                cap_policy, cap_rule = max_tokens_binding
                sent = request_decoding.get("max_tokens")
                if isinstance(sent, bool) or not isinstance(sent, int):
                    problems.append(
                        f"request {index} max_tokens is {sent!r}, not an integer; the "
                        "per-sample rule reached the wire unresolved"
                    )
                else:
                    expected = cap_policy.resolve(cap_rule, payload.get("audio_seconds"))
                    if sent != expected:
                        problems.append(
                            f"request {index} max_tokens is {sent}, not the {expected} "
                            f"the rule resolves for {payload.get('audio_seconds')!r} s"
                        )
                    max_tokens_per_sample[str(payload.get("sample_id"))] = sent
        if proposer:
            problems.extend(
                self._wire_check_construction_problems(transport, contacts_per_sample)
            )
        arrival = self.response_arrival_counts(client)
        # The transport imitated exactly one native envelope for a native
        # arm and none for a text arm, so the accounting must report
        # precisely that -- a count that cannot tell the two apart is the
        # ambiguity this whole field exists to remove.
        expected_native_rows = 1 if native else 0
        if arrival["rows_with_native_tool_calls"] != expected_native_rows:
            problems.append(
                f"response-arrival accounting reports "
                f"{arrival['rows_with_native_tool_calls']} native tool-call row(s); the "
                f"fake transport emitted {expected_native_rows}"
            )
        if arrival["rows_answered_as_text"] != expected_payloads - expected_native_rows:
            problems.append(
                f"response-arrival accounting reports "
                f"{arrival['rows_answered_as_text']} text row(s) for "
                f"{expected_payloads} request(s)"
            )
        if policy != "fixed":
            # A phase's instruction rides the payload's ORG/CONTROL history,
            # not the system message (rails.core_client._agent_history). If
            # the last history turn is not the control turn, the phase's own
            # instruction never reached the wire and the cell would have run
            # every phase on the bare system prompt.
            for index, payload in enumerate(transport.payloads):
                history = payload.get("history")
                if not isinstance(history, list) or not history:
                    problems.append(
                        f"request {index} carries no Agent history; a phase program's "
                        "instruction travels on the CONTROL history turn"
                    )
                    continue
                last = history[-1]
                if not isinstance(last, Mapping) or last.get("role") != "control":
                    problems.append(
                        f"request {index} last history turn has role "
                        f"{(last or {}).get('role') if isinstance(last, Mapping) else last!r}, "
                        "not 'control'"
                    )
                elif not str(last.get("content") or "").strip():
                    problems.append(
                        f"request {index} control turn carries an empty instruction"
                    )
        # E6: a supplied phase's knowledge rides TYPED CONTENT BLOCKS, not
        # the control turn. Count them at the transport seam and prove they
        # are typed: an untyped block is knowledge the containment rule
        # cannot distinguish from smuggled instruction text, and a supplied
        # cell with zero blocks is a cell that supplied nothing.
        typed_blocks: list[int] = []
        for index, payload in enumerate(transport.payloads):
            items = payload.get("supplied_evidence") or []
            typed_blocks.append(len(items))
            for position, item in enumerate(items):
                if not isinstance(item, Mapping):
                    problems.append(
                        f"request {index} supplied_evidence[{position}] is not an object"
                    )
                    continue
                missing = [
                    field
                    for field in ("evidence_id", "source_uri", "content")
                    if not str(item.get(field) or "").strip()
                ]
                if missing:
                    problems.append(
                        f"request {index} supplied_evidence[{position}] lacks "
                        f"{missing}; a traced block carries its own provenance"
                    )
                if item.get("knowledge_role") not in {"key", "value"}:
                    problems.append(
                        f"request {index} supplied_evidence[{position}] carries "
                        f"knowledge_role {item.get('knowledge_role')!r}, not "
                        "'key'/'value'"
                    )
        if self._phase_supply_receipt is not None and not any(typed_blocks):
            problems.append(
                "this cell declares phase_supply but not one request carried a typed "
                "knowledge block; the supply never reached the wire"
            )
        if problems:
            raise FlightRuntimeError("wire check failed: " + "; ".join(problems))

        close_receipt = client.close()
        seal_and_score_result: Mapping[str, object] = {
            "status": "SKIPPED",
            "reason": "seal_and_score=False",
        }
        if seal_and_score:
            seal_and_score_result = self._wire_check_seal_and_score(
                plan=plan,
                run_dir=run_dir,
                close_receipt=close_receipt,
                max_workers=max_workers,
            )
        aborted = self._abort_attempt(
            self._data_root,
            wire_run_id,
            wire_attempt_id,
            reason="wire check: contact-free wiring proof, no model was ever reached",
        )
        if request_payload_observer is not None:
            for payload in transport.payloads:
                request_payload_observer(json.loads(json.dumps(payload)))
        first = transport.payloads[0] if transport.payloads else {}
        return {
            "schema": "saea-flight-wire-check-v1",
            "flight_run_id": self._run_id,
            "wire_check_run_id": wire_run_id,
            "attempt_id": wire_attempt_id,
            "attempt_aborted": bool(aborted),
            "config_hash": self._composed.config_hash,
            "protocol_hash": plan.protocol_hash,
            "split_id": split_id,
            "split_identity_hash": identity_hash,
            "arm": arm,
            "native_tools_arm": native,
            "construction_proposer_arm": proposer,
            # Identity and counts only, never the rendered instruction: a
            # proposer prompt carries construction query text and gold calls,
            # which no receipt in this repository may hold.
            "construction_draws": (
                [contact.as_json() for contact in self.construction_material().contacts]
                if proposer
                else []
            ),
            "sample_count": len(self._samples),
            "contact_count": contact_count,
            "contacts_per_sample": contacts_per_sample,
            "policy": policy,
            "policy_kind": policy_kind,
            "phases": phase_receipt,
            "phase_material": self._phase_material_receipt,
            "phase_supply": self._phase_supply_receipt,
            "phase_review": self._phase_review_receipt,
            # E6: how many TYPED knowledge blocks each request carried, in
            # request order -- the observable proof that a supplied phase's
            # knowledge travelled the traced channel and not the control
            # turn (whose role is asserted separately above).
            "typed_knowledge_blocks": typed_blocks,
            "typed_knowledge_blocks_total": sum(typed_blocks),
            "dispatch": dispatch,
            "wall_seconds": wall_seconds,
            "payload_keys": sorted(first),
            "payload_keys_equal_arm_visible_fields": True,
            "tool_schemas_count": (
                len(first.get("tool_schemas") or []) if native else 0
            ),
            "id_slot": dict(first.get("decoding_params") or {}).get("id_slot"),
            # The generation cap that actually crossed the transport seam. For
            # a plain-integer fragment this is that integer and
            # ``max_tokens_per_sample`` is None; for a fragment declaring a
            # per-sample rule it is the FIRST request's resolved integer and
            # the mapping carries every request's, keyed by sample id -- the
            # observable proof that the cap was resolved per sample and not
            # once for the cell.
            "max_tokens": dict(first.get("decoding_params") or {}).get("max_tokens"),
            "max_tokens_policy": (
                max_tokens_binding[1].get(MAX_TOKENS_POLICY_KEY)
                if max_tokens_binding is not None
                else None
            ),
            "max_tokens_rule": (
                dict(max_tokens_binding[1]) if max_tokens_binding is not None else None
            ),
            "max_tokens_per_sample": (
                dict(sorted(max_tokens_per_sample.items()))
                if max_tokens_binding is not None
                else None
            ),
            "request_body_sha256": [
                hashlib.sha256(body).hexdigest() for body in transport.request_bodies
            ],
            "speech_packets_verified": {
                sample_id: descriptor["sha256"]
                for sample_id, descriptor in sorted(packet_bindings.items())
            },
            "trace_manifest_hash": close_receipt["trace_manifest_hash"],
            "cost": close_receipt["cost"],
            "response_arrival": arrival,
            "seal_and_score": seal_and_score_result,
            "transport": (
                "core.flight.runtime.WireCheckTransport (never opens a socket)"
            ),
            "gate": "core.flight.runtime.WireCheckGate (authorizes nothing real)",
            "payload_to_wire_tools_mapping": (
                "payload tool_schemas -> request body 'tools' is core.model.transport."
                "LlamaServerTransport's own step, covered by "
                "tests/unit/test_native_tools_arm.py's transport section; this check "
                "asserts at the transport seam, where the payload is what crosses"
            ),
            "model_contacts": 0,
        }

    def _wire_check_construction_problems(
        self, transport: "WireCheckTransport", contacts_per_sample: int
    ) -> list[str]:
        """The contact-free proof for the construction-proposer arm.

        Four things, each of which a real flight would otherwise only learn
        by spending contacts on a registered run: exactly ONE payload per
        draw; each payload's ``construction_targets`` are EXACTLY the M
        exemplars that draw declared, in that order; no audio field of any
        kind reaches the wire; and the system message is the draw's own
        rendered instruction, by sha256.
        """

        material = self.construction_material()
        by_sample = material.by_sample()
        problems: list[str] = []
        if contacts_per_sample != 1:
            problems.append(
                f"the proposer arm is a one-contact policy but the check expects "
                f"{contacts_per_sample} contacts per sample"
            )
        if len(transport.payloads) != len(material.contacts):
            problems.append(
                f"{len(transport.payloads)} request(s) reached the transport for "
                f"{len(material.contacts)} draw(s); the proposer makes exactly one "
                "contact per draw"
            )
        seen: set[str] = set()
        for index, payload in enumerate(transport.payloads):
            sample_id = str(payload.get("sample_id"))
            if sample_id in seen:
                problems.append(f"request {index} repeats draw sample {sample_id!r}")
            seen.add(sample_id)
            contact = by_sample.get(sample_id)
            if contact is None:
                problems.append(
                    f"request {index} names sample {sample_id!r}, which is no draw"
                )
                continue
            declared = payload.get(CONSTRUCTION_VISIBLE_FIELD)
            if not isinstance(declared, list) or not declared:
                problems.append(
                    f"request {index} carries no {CONSTRUCTION_VISIBLE_FIELD} for the "
                    "one arm whose whole purpose is to carry them"
                )
                continue
            got = tuple(str(entry.get("sample_id")) for entry in declared)
            if got != contact.construction_target_ids:
                problems.append(
                    f"request {index} declares construction targets {list(got)}, not "
                    f"draw {contact.draw.draw_id}'s own "
                    f"{list(contact.construction_target_ids)}"
                )
            if any(set(entry) != {"sample_id", "target"} for entry in declared):
                problems.append(
                    f"request {index} has a construction target entry with keys beyond "
                    "sample_id/target"
                )
            instruction = str(payload.get("task_instruction") or "")
            digest = hashlib.sha256(instruction.encode("utf-8")).hexdigest()
            if digest != contact.prompt_sha256:
                problems.append(
                    f"request {index} task_instruction hashes to {digest[:16]}, not draw "
                    f"{contact.draw.draw_id}'s pinned prompt {contact.prompt_sha256[:16]}"
                )
        for index, body in enumerate(transport.request_bodies):
            text = body.decode("utf-8", errors="replace")
            for marker in ("input_audio", "input_speech_features", "audio_url"):
                if marker in text:
                    problems.append(
                        f"request body {index} carries {marker!r}; the proposer arm is "
                        "text-only and sends no audio part at all"
                    )
        return problems

    def _wire_check_seal_and_score(
        self,
        *,
        plan: ExecutionPlan,
        run_dir: Path,
        close_receipt: Mapping[str, object],
        max_workers: int,
    ) -> Mapping[str, object]:
        """Seal a wire-check bundle from the fake responses and run the
        registered scorers over it, so the manifest/verify/score links are
        exercised too. A dirty study tree refuses a COMPLETED manifest by
        design (``core.bundle.git_commit``); that is RECORDED rather than
        raised, because the wire check's whole point is to run on the tree
        that carries the fix under test."""

        outputs_path = run_dir / f"{plan.run_id}.outputs.jsonl"
        canonical_rows = self._canonical_output_rows(self._client)
        with outputs_path.open("w", encoding="utf-8") as handle:
            for row in canonical_rows:
                handle.write(
                    json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
                )
        result = RunResult(
            run_id=plan.run_id,
            arm=close_receipt["arm"],
            outputs_path=outputs_path,
            trace_manifest_hash=close_receipt["trace_manifest_hash"],
            cost=close_receipt["cost"],
        )
        sample_ids = tuple(sample.sample_id for sample in self._samples)
        verified_split = VerifiedSplit(
            name=self._split_id,
            carrier_lock_key=plan.carrier_lock_key,
            split_role=plan.split_role,
            ids=tuple(sorted(sample_ids)),
            prefixed_ids=tuple(prefixed(plan.carrier_lock_key, sample_ids)),
            identity_hash=plan.split_identity_hash,
        )
        try:
            manifest_path = self._manifest_builder(
                repo_root=self._repo_root,
                data_root=self._data_root,
                composed=self._composed,
                plan=plan,
                verified_split=verified_split,
                session_receipt_path=None,
                run_dir=run_dir,
                status="COMPLETED",
                result=result,
            )
            verified = self._bundle_verifier(manifest_path)
            # The FINALIZER too, not merely the manifest builder and the
            # verifier. seal() calls it, and it validates the complete
            # 21-column ledger surface before it will score; a wire check
            # that skipped it let a flight die at finalize AFTER its
            # contacts were spent (defect 9). It is called in validate-only
            # mode here -- ledger cells built exactly as seal() builds them,
            # through core.tracking.ledger_row_for_bundle -- rather than run
            # for real, because finalize_bundle also settles the attempt
            # this check is about to abort.
            ledger_cells = self._default_ledger_cells(plan)
            missing = [
                column
                for column in self.CALLER_LEDGER_COLUMNS
                if column not in ledger_cells
            ]
            if missing:
                raise FlightRuntimeError(
                    f"ledger cells are missing the caller-owned column(s) {missing}"
                )
            self._ledger_validator(verified, ledger_cells)
            jobs_path = run_dir / "score-jobs.jsonl"
            with jobs_path.open("w", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        {"job_id": plan.attempt_id, "manifest": str(manifest_path)}
                    )
                    + "\n"
                )
            jobs = load_score_jobs(jobs_path)
            score_result = self._score_batch(
                jobs, output_dir=run_dir / "score-batch", max_workers=max_workers
            )
        except Exception as error:  # noqa: BLE001 -- record, never mask
            return {
                "status": "REFUSED",
                "reason": f"{type(error).__name__}: {error}",
                "note": (
                    "a dirty study tree refuses a COMPLETED manifest by design, which "
                    "is the common cause here; any other reason above is a real defect "
                    "in the sealing or ledger path and must be fixed, not re-run"
                ),
            }
        # A score BATCH reports a failed job in its result dict; it does not
        # raise. Reporting OK on "no exception" was a false green: the first
        # clean-tree wire check said OK for all four cells while every
        # scoring job had in fact failed (the cost scorer refused the
        # outputs artifact's name). A green here now REQUIRES every job to
        # have succeeded.
        failed = score_result.get("failed") if isinstance(score_result, Mapping) else None
        succeeded = score_result.get("succeeded") if isinstance(score_result, Mapping) else None
        job_failures = [
            {
                "job_id": job.get("job_id"),
                "error": job.get("error"),
                "returncode": job.get("returncode"),
                "stderr_log": job.get("stderr_log"),
            }
            for job in (score_result.get("jobs") or ())
            if isinstance(score_result, Mapping) and job.get("status") != "succeeded"
        ]
        if failed or succeeded != len(jobs) or job_failures:
            return {
                "status": "SCORING_FAILED",
                "reason": (
                    f"{failed} of {len(jobs)} scoring job(s) failed; a wire check is "
                    "green only when every registered scorer ran to completion"
                ),
                "manifest_path": str(manifest_path),
                "manifest_sha256": _sha256_file(manifest_path),
                "verified_attempt_state": getattr(verified, "attempt_state", None),
                "outputs_row_count": len(canonical_rows),
                "scorers": list(self._composed.values.get("scorers", ())),
                "job_failures": job_failures,
                "score_result": score_result,
            }
        return {
            "status": "OK",
            "manifest_path": str(manifest_path),
            "manifest_sha256": _sha256_file(manifest_path),
            "verified_attempt_state": getattr(verified, "attempt_state", None),
            "outputs_row_count": len(canonical_rows),
            "score_result": score_result,
            "scorers": list(self._composed.values.get("scorers", ())),
            "ledger_surface_validated": True,
            "numbers_are_meaningless": (
                "these scores are computed over WireCheckTransport's canned response, "
                "not over any model output; they prove the scoring link runs and "
                "nothing else"
            ),
        }

    # -- convenience --------------------------------------------------------

    def run_all(self) -> FlightReceipts:
        """Run every stage in order and return the accumulated
        :class:`~.receipts.FlightReceipts`."""

        self.preflight()
        self.preprocess()
        self.serve()
        self.run_phases()
        self.seal()
        self.score()
        return self.receipts

    def abort(self, reason: str) -> bool:
        """Mark this attempt ABORTED if it was ever opened (``core.bundle.
        finalize.abort_attempt_if_opened``); a no-op (``False``) if it was
        never opened, or if it already reached a terminal state
        (FINALIZED/ABORTED)."""

        if not isinstance(reason, str) or not reason.strip():
            raise FlightRuntimeError("abort reason must be a non-empty string")
        attempt_id = self._plan.attempt_id if self._plan is not None else self._attempt_id
        return self._abort_attempt(self._data_root, self._run_id, attempt_id, reason=reason)


__all__ = [
    "FlightRuntime",
    "FlightRuntimeError",
    "FlightServeGeometryMismatchError",
    "FlightStageOrderError",
    "PACKET_ID_SEPARATOR",
    "REQUIRED_EXECUTION_PLAN_FIELDS",
    "SAMPLE_ID_SEPARATOR",
    "SEQUENTIAL_DISPATCH_SLOT",
    "SLOT_AFFINITY_SENTINEL",
    "SPEECH_FEATURE_ARM_FIELD",
    "SPEECH_PACKET_N_EMBD",
    "WIRE_CHECK_RESPONSE_TEXT",
    "WIRE_CHECK_RUN_ID_PREFIX",
    "WireCheckGate",
    "WireCheckTransport",
    "arm_uses_speech_feature_packets",
    "load_promotion_receipt",
    "merge_server_args",
    "packet_id_for_sample",
    "sample_id_for_packet",
]
