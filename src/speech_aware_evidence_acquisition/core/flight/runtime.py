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
import time
from pathlib import Path
from typing import Callable, Mapping, Sequence

from ...contracts import (
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
from ...rails.phase_runner import run_program
from ...rails.runner import RAILS_ARMS, run_rails_experiment
from ...rails.task_adapter import TaskAdapter
from ..attempts.store import AttemptStore
from ..base import RunResult, TRANSPORTS
from ..bundle.finalize import abort_attempt_if_opened, finalize_bundle
from ..bundle.git_commit import require_clean_study_repo
from ..bundle.manifest import build_manifest
from ..bundle.verify import verify_bundle
from ..config import (
    compose,
    d1_media_supplement_relpath,
    d1_media_supplement_sha256,
    model_lock_key,
    model_materialization_root,
    protocol_hash as compute_protocol_hash,
    resolve_runtime_receipt_path,
    runtime_receipt_relpath,
)
from ..model.speech_features import materialize_legacy_cached_speech_feature_packets
from ..scoring_batch import load_score_jobs, run_score_batch
from ..session import load_runtime_receipt, start_session, stop_session
from ..split_receipt import VerifiedSplit
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
    """

    if isinstance(server_args, (str, bytes)) or not isinstance(server_args, Sequence):
        raise FlightRuntimeError("model config server_args must be a list of strings")
    merged = [str(value) for value in server_args]
    for flag, value in (("-np", slots), ("-c", context_tokens)):
        if flag in merged:
            index = merged.index(flag)
            if index + 1 >= len(merged):
                raise FlightRuntimeError(
                    f"model config server_args declares {flag} with no value"
                )
            merged[index + 1] = str(value)
        else:
            merged.extend([flag, str(value)])
    return merged


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

    def assert_model_touch_allowed(self, plan: object, **_kwargs: object) -> str:
        self.checked_plans.append(plan)
        return "0" * 64


class WireCheckTransport:
    """A transport double that records every request payload and answers
    :data:`WIRE_CHECK_RESPONSE_TEXT`. Never opens a socket."""

    def __init__(self, response_text: str = WIRE_CHECK_RESPONSE_TEXT) -> None:
        self.payloads: list[Mapping[str, object]] = []
        self.request_bodies: list[bytes] = []
        self._response_text = response_text

    def __call__(self, request_bytes: bytes) -> bytes:
        if not isinstance(request_bytes, bytes):
            raise FlightRuntimeError("transport must be handed bytes")
        self.request_bodies.append(request_bytes)
        self.payloads.append(json.loads(request_bytes.decode("utf-8")))
        return json.dumps(
            {
                "text": self._response_text,
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            }
        ).encode("utf-8")


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
        transport_factory: Callable[..., object] | None = None,
        gate_factory: Callable[..., object] = FrozenCoreGate.for_study_repo,
        rails_runner: Callable[..., object] = run_rails_experiment,
        phase_runner: Callable[..., object] = run_program,
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
        token_counter: Callable[[bytes], int] = _default_token_counter,
        tool_schema_resolver: Callable[[Mapping[str, object], Path, str], Sequence[Mapping[str, object]]]
        | None = _default_tool_schema_resolver,
        lock: Mapping[str, object] | None = None,
        run_dir: Path | None = None,
        host: str = "127.0.0.1",
        port: int = 8080,
        request_id_prefix: str = "flight",
        campaign_active: bool = False,
        speech_tokens_per_second: float = 14.4,
    ) -> None:
        if not isinstance(run_id, str) or not run_id:
            raise FlightRuntimeError("run_id must be a non-empty string")
        if not isinstance(attempt_id, str) or not attempt_id:
            raise FlightRuntimeError("attempt_id must be a non-empty string")
        if not callable(adapter_factory):
            raise FlightRuntimeError("adapter_factory must be callable")
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
        self._transport_factory = transport_factory
        self._gate_factory = gate_factory
        self._rails_runner = rails_runner
        self._phase_runner = phase_runner
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
        self._token_counter = token_counter
        self._tool_schema_resolver = tool_schema_resolver
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
        self._output_rows: list[Mapping[str, object]] = []
        self._promotion_receipt: Mapping[str, object] | None = None
        self._owns_session = False

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

    def _assess_prompt_budget(self, samples: Sequence[object]) -> tuple[Mapping[str, object], ...]:
        """Serialize one representative request per phase through the
        adapter and run it through ``rails.context_budget.
        assess_context_budget`` -- a PRE-FLIGHT estimate (module docstring:
        exact counts are required "immediately before each model contact",
        which is what a real flight's ``token_counter`` seam must supply at
        request time; this stage runs once, ahead of any contact)."""

        representative = samples[0]
        baseline_values = self._composed.values
        policy = baseline_values.get("policy")
        phase_names: tuple[str, ...]
        if policy == "fixed":
            phase_names = ("direct",)
        else:
            phase_names = tuple(phase.name for phase in default_phase_program(str(policy)).phases)
        max_tokens = int(self._adapter.serving_geometry()["max_tokens"])
        messages = self._adapter.assemble_prompt(representative, None)
        payload_bytes = json.dumps(
            list(messages), ensure_ascii=False, sort_keys=True
        ).encode("utf-8")
        rendered_tokens = self._token_counter(payload_bytes)
        speech_tokens = max(
            1, round(float(getattr(representative, "audio_seconds", 1.0)) * self._speech_tokens_per_second)
        )
        receipts: list[Mapping[str, object]] = []
        for phase_name in phase_names:
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
            candidate = ContextBudgetInput.from_payload(payload_bytes, breakdown=breakdown)
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
        and pre-assess the prompt budget for a representative request per
        phase. Fails closed and records nothing on any failure.
        """

        self._require_prior_stages("preflight")
        values, carrier_lock_key, split_id, identity_hash = self._prepare()
        composed = self._composed
        adapter = self._adapter
        samples = self._samples
        lock = self._lock

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
        )
        self._gate = gate
        gate.assert_model_touch_allowed(plan)

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
        promotion_root = Path(str(self._load_promotion_receipt()["feature_root"]))
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
        geometry = dict(self._adapter.serving_geometry())

        if reuse is not None:
            if not isinstance(reuse, FlightRuntime):
                raise FlightRuntimeError("serve(reuse=...) must be another FlightRuntime")
            reuse_geometry = dict(reuse.adapter.serving_geometry())
            if reuse_geometry != geometry:
                raise FlightServeGeometryMismatchError(
                    f"cannot reuse a server serving geometry {reuse_geometry} for a "
                    f"flight whose adapter declares geometry {geometry}"
                )
            if reuse._session is None or reuse._transport is None:
                raise FlightRuntimeError("serve(reuse=...) target has not itself served yet")
            self._session = reuse._session
            self._transport = reuse._transport
            self._runtime_receipt = reuse._runtime_receipt
            self._session_receipt_path = reuse._session_receipt_path
            # A reused server belongs to the flight that started it; this
            # flight must never stop it out from under that owner.
            self._owns_session = False
            payload = {
                "reused_from_attempt_id": reuse.attempt_id,
                "session_id": self._session.session_id,
                "host": self._session.host,
                "port": self._session.port,
                "serving_geometry": geometry,
                "reused": True,
                "startup_seconds": 0.0,
            }
            return self.receipts.record("serve", payload)

        values = self._composed.values
        runtime_receipt = self._runtime_receipt_loader(
            resolve_runtime_receipt_path(self._repo_root, values)
        )
        self._runtime_receipt = runtime_receipt
        self._gate.assert_model_touch_allowed(self._plan)

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

        transport_factory = self._transport_factory or TRANSPORTS.resolve(str(values["transport"]))
        transport = transport_factory(
            values,
            self._data_root,
            session=session,
            runtime_receipt=runtime_receipt,
            runtime_root=self._runtime_root,
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
        }
        return self.receipts.record("serve", payload)

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
        """

        if self._session is None or not self._owns_session:
            return None
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
        return kwargs

    def _decoding_params(self) -> Mapping[str, object] | None:
        """The composed ``decoding_params``, with the slot-affinity sentinel
        resolved (see :data:`SLOT_AFFINITY_SENTINEL`).

        Passing the sentinel through unresolved is not a cosmetic slip: the
        frozen-core adapter refuses it ("id_slot must be a non-negative
        integer"), so every cell of a flight whose model fragment declares
        it dies at its first contact.
        """

        value = self._composed.values.get("decoding_params")
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
                decoding_params=decoding_params,
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
    def _rows_from_phase_summaries(summaries: Sequence[object]) -> list[Mapping[str, object]]:
        rows: list[Mapping[str, object]] = []
        for summary in summaries:
            phase_id = getattr(summary, "controller_policy_id", None)
            for result in summary.results:
                rows.append(
                    {
                        "phase": phase_id,
                        "sample_id": result.sample_id,
                        "final_response_text": getattr(result, "final_response_text", None),
                        "contact_count": len(getattr(result, "contacts", ()) or ()),
                    }
                )
        return rows

    def _dispatch_fixed_policy(
        self, client: object, plan: ExecutionPlan
    ) -> tuple[list[Mapping[str, object]], int, str]:
        """The ``policy == "fixed"`` dispatch, factored out so
        :meth:`wire_check` drives the SAME code path a real flight does --
        a wiring proof that ran its own copy of this would prove nothing
        about the flight."""

        baseline_values = self._composed.values
        if self.uses_speech_feature_packets():
            # Same fixed policy, same one contact per sample -- but through
            # the packet content part rails.runner cannot express (see
            # :meth:`_run_speech_feature_direct`).
            rows = self._run_speech_feature_direct(client)
            return rows, len(rows), "direct-speech-feature-packets"
        arms = tuple(baseline_values.get("rails_arms", RAILS_ARMS))
        summary = self._rails_runner(
            data_root=self._data_root,
            plan=plan,
            adapter=self._adapter,
            core_client=client,
            split_id=self._split_id,
            arms=arms,
            decoding_params=self._decoding_params(),
        )
        return self._rows_from_direct_summary(summary), len(summary.results), "direct"

    def run_phases(self) -> Mapping[str, object]:
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
        baseline_values = self._composed.values
        policy = baseline_values.get("policy")
        if not isinstance(policy, str) or not policy:
            raise FlightRuntimeError("baseline fragment must declare a non-empty 'policy'")

        client_kwargs = self.frozen_core_client_kwargs()
        client = self._client_factory(**client_kwargs)
        self._client = client

        started = self._clock()
        if policy == "fixed":
            self._output_rows, contact_count, policy_kind = self._dispatch_fixed_policy(
                client, self._plan
            )
        else:
            program = default_phase_program(policy)
            binding = getattr(self, "_phase_program_material", None)
            if binding is None:
                raise FlightRuntimeError(
                    f"policy {policy!r} is a phase program; call "
                    "bind_phase_program_material(...) before run_phases()"
                )
            summaries = self._phase_runner(
                program=program,
                adapter=self._adapter,
                plan=self._plan,
                data_root=self._data_root,
                core_client=client,
                split_id=self._split_id,
                knowledge_snapshot=binding["knowledge_snapshot"],
                speech_packet_bindings=binding["speech_packet_bindings"],
                trace_sink=binding.get("trace_sink", client),
                decoding_params=self._decoding_params(),
                material_for_phase=binding["material_for_phase"],
                supply_for_phase=binding.get("supply_for_phase"),
            )
            self._output_rows = self._rows_from_phase_summaries(summaries)
            contact_count = sum(len(summary.results) for summary in summaries)
            policy_kind = "phase-program"
        wall_seconds = max(self._clock() - started, 1e-9)

        timings = client.timings
        latencies = tuple(timing.latency_seconds for timing in timings)
        average_latency = sum(latencies) / len(latencies) if latencies else 0.0
        slots = int(self._adapter.serving_geometry()["slots"])
        contacts_per_second = contact_count / wall_seconds
        slot_occupancy = (
            (contact_count * average_latency) / (wall_seconds * slots) if slots > 0 else 0.0
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
            "wall_seconds": wall_seconds,
            "contact_count": contact_count,
            "contacts_per_second": contacts_per_second,
            "average_latency_seconds": average_latency,
            "slot_occupancy": slot_occupancy,
            "tokens_per_second": tokens_per_second_estimate,
            "tokens_per_second_basis": "contacts_per_second_times_completion_token_ceiling_upper_bound_estimate",
        }
        require_mandatory_throughput_fields(
            "run_phases", payload, ("contacts_per_second", "tokens_per_second")
        )
        return self.receipts.record("run_phases", payload)

    def bind_phase_program_material(
        self,
        *,
        knowledge_snapshot: object,
        speech_packet_bindings: Mapping[str, Mapping[str, object]],
        material_for_phase: Callable[..., object],
        supply_for_phase: Callable[..., object] | None = None,
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
            "trace_sink": trace_sink,
        }

    # -- stage 5: seal --------------------------------------------------

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
        rows: list[Mapping[str, object]] = []
        for row in self._output_rows:
            sample_id = str(row.get("sample_id"))
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


    def seal(self, *, flight_receipt_kwargs: Mapping[str, object] | None = None) -> Mapping[str, object]:
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
        finalize_result = self._bundle_finalizer(
            manifest_path, self._lock, self._data_root, repo_root=self._repo_root
        )

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

        payload = {
            "manifest_path": str(manifest_path),
            "manifest_sha256": _sha256_file(manifest_path),
            "verified_attempt_state": getattr(verified, "attempt_state", None),
            "outputs_path": str(outputs_path),
            "outputs_row_count": len(self._output_rows),
            "trace_manifest_hash": close_receipt["trace_manifest_hash"],
            "cost": close_receipt["cost"],
            "finalize": {
                "scores_path": str(finalize_result.scores_path),
                "ledger_markdown_path": str(finalize_result.ledger_markdown_path),
                "attempt_state": finalize_result.attempt_state,
            },
            "flight_receipt": flight_receipt,
        }
        return self.receipts.record("seal", payload)

    # -- stage 6: score ---------------------------------------------------

    def score(self, *, max_workers: int = 1, output_dir: Path | None = None) -> Mapping[str, object]:
        """``load_score_jobs`` + ``score_batch`` (default
        ``core.scoring_batch.run_score_batch``) over the exactly-one manifest
        :meth:`seal` sealed -- one job per complete manifest, never sharded
        (``core.scoring_batch``'s own module docstring)."""

        self._require_prior_stages("score")
        seal_payload = self.receipts.require("seal")
        manifest_path = Path(seal_payload["manifest_path"])
        run_dir = self._run_dir()
        jobs_path = run_dir / "score-jobs.jsonl"
        with jobs_path.open("w", encoding="utf-8") as handle:
            handle.write(
                json.dumps({"job_id": self._plan.attempt_id, "manifest": str(manifest_path)}) + "\n"
            )
        jobs = load_score_jobs(jobs_path)
        resolved_output_dir = Path(output_dir) if output_dir is not None else run_dir / "score-batch"

        started = self._clock()
        result = self._score_batch(jobs, output_dir=resolved_output_dir, max_workers=max_workers)
        duration = max(self._clock() - started, 1e-9)

        payload = {
            "jobs_path": str(jobs_path),
            "output_dir": str(resolved_output_dir),
            "job_count": len(jobs),
            "duration_seconds": duration,
            "jobs_per_second": len(jobs) / duration,
            "result": result,
        }
        require_mandatory_throughput_fields("score", payload, ("jobs_per_second",))
        return self.receipts.record("score", payload)

    # -- contact-free wiring proof -----------------------------------------

    def wire_check(
        self,
        *,
        seal_and_score: bool = True,
        max_workers: int = 1,
        response_text: str = WIRE_CHECK_RESPONSE_TEXT,
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
        stamp = int(self._clock() * 1000)
        wire_run_id = f"{WIRE_CHECK_RUN_ID_PREFIX}{self._run_id}-{stamp:d}"
        wire_attempt_id = f"attempt-wire-check-{stamp:d}"
        declared = self._composed.values.get("execution_plan")
        if not isinstance(declared, Mapping):
            raise FlightRuntimeError("experiment fragment must declare an execution_plan")
        plan = ExecutionPlan(
            run_id=wire_run_id,
            execution_profile=declared["execution_profile"],
            carrier_lock_key=carrier_lock_key,
            split_role=declared["split_role"],
            split_identity_hash=identity_hash,
            planned_model_calls=max(len(self._samples), 1),
            planned_gpu_hours=declared["planned_gpu_hours"],
            planned_speech_audio_seconds=declared["planned_speech_audio_seconds"],
            protocol_hash=compute_protocol_hash(
                self._composed.config_hash, arm, identity_hash
            ),
            attempt_id=wire_attempt_id,
        ).validate()
        run_dir = self._data_root / "wire-check" / wire_run_id / wire_attempt_id
        run_dir.mkdir(parents=True, exist_ok=True)

        gate = WireCheckGate()
        transport = WireCheckTransport(response_text=response_text)
        client_kwargs = self.frozen_core_client_kwargs(
            plan=plan, gate=gate, transport=transport, run_dir=run_dir
        )
        packet_bindings = dict(client_kwargs.get("speech_packet_bindings") or {})
        client = self._client_factory(**client_kwargs)
        self._client = client

        started = self._clock()
        rows, contact_count, policy_kind = self._dispatch_fixed_policy(client, plan)
        wall_seconds = max(self._clock() - started, 1e-9)
        self._output_rows = rows

        # -- the assertions each landed defect would have failed -----------
        expected_fields = set(ARM_VISIBLE_FIELDS.get(arm, ()))
        native = "tool_schemas" in expected_fields
        problems: list[str] = []
        if len(transport.payloads) != len(self._samples):
            problems.append(
                f"{len(transport.payloads)} request(s) reached the transport for "
                f"{len(self._samples)} sample(s)"
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
            id_slot = dict(payload.get("decoding_params") or {}).get("id_slot")
            if isinstance(id_slot, bool) or not isinstance(id_slot, int):
                problems.append(f"request {index} id_slot is {id_slot!r}, not an integer")
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
            "sample_count": len(self._samples),
            "contact_count": contact_count,
            "policy_kind": policy_kind,
            "wall_seconds": wall_seconds,
            "payload_keys": sorted(first),
            "payload_keys_equal_arm_visible_fields": True,
            "tool_schemas_count": (
                len(first.get("tool_schemas") or []) if native else 0
            ),
            "id_slot": dict(first.get("decoding_params") or {}).get("id_slot"),
            "request_body_sha256": [
                hashlib.sha256(body).hexdigest() for body in transport.request_bodies
            ],
            "speech_packets_verified": {
                sample_id: descriptor["sha256"]
                for sample_id, descriptor in sorted(packet_bindings.items())
            },
            "trace_manifest_hash": close_receipt["trace_manifest_hash"],
            "cost": close_receipt["cost"],
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
                    "the sealing and scoring links refuse a dirty study tree by "
                    "design; re-run this wire check on a clean tree to exercise them"
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
