"""The unified rails runner skeleton (B0): one config's ``ExecutionPlan``,
``contracts.assert_execution_scope``, and the advisory flight lock, then
zero-supply and supplied arms through a ``TaskAdapter`` and a ``CoreClient``
(a ``MockCoreClient`` in every test this mission writes). Engineering-only:
no gate, no ``AttemptStore``, no real transport -- see ``rails.core_client``'s
module docstring for why that production machinery is deliberately NOT
wired in here yet.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence

from ..contracts import ExecutionPlan, assert_execution_scope
from ..core.flight_lock import read_flight_lock
from .consumption import ConsumptionTrace
from .core_client import CoreClient
from .errors import RailsError
from .obs import ObsPacket, default_obs_packet
from .supply import SupplyPacket
from .task_adapter import TaskAdapter, TaskSample

ZERO_SUPPLY_ARM = "zero-supply"
SUPPLIED_ARM = "supplied"
RAILS_ARMS: tuple[str, ...] = (ZERO_SUPPLY_ARM, SUPPLIED_ARM)

# (sample, obs, task-native query) -> a SupplyPacket for the supplied arm, or
# None to skip supply for that one sample even though the arm ran (an
# adapter/caller-level choice, e.g. no evidence retrieved above threshold --
# distinct from the arm itself being absent from `arms`).
SupplyBuilder = Callable[[TaskSample, ObsPacket, str], SupplyPacket | None]


class RailsRunnerError(RailsError):
    """The runner refused: a bad plan, an unknown arm, or a missing supply_builder."""


@dataclass(frozen=True)
class ArmResult:
    arm: str
    sample_id: str
    messages: tuple[Mapping[str, object], ...]
    response_text: str
    metrics: Mapping[str, object]
    consumption: ConsumptionTrace


@dataclass(frozen=True)
class RunSummary:
    run_id: str
    protocol_hash: str
    arms: tuple[str, ...]
    results: tuple[ArmResult, ...]
    # Best-effort, advisory (core.flight_lock's own module docstring): None
    # whenever no flight ever ran under scripts/run_arm_sequence.sh, or the
    # lock file is missing/unreadable/malformed -- never itself a refusal.
    flight_lock: Mapping[str, object] | None


def _run_one_arm(
    *,
    arm: str,
    adapter: TaskAdapter,
    core_client: CoreClient,
    sample: TaskSample,
    supply: SupplyPacket | None,
    decoding_params: Mapping[str, object] | None,
) -> ArmResult:
    messages = adapter.assemble_prompt(sample, supply)
    response_text = core_client.complete(messages, decoding_params=decoding_params)
    metrics = adapter.score(sample, response_text)
    consumption = adapter.extract_consumption(sample, supply, response_text)
    return ArmResult(
        arm=arm,
        sample_id=sample.sample_id,
        messages=tuple(messages),
        response_text=response_text,
        metrics=metrics,
        consumption=consumption,
    )


def run_rails_experiment(
    *,
    data_root: Path,
    plan: ExecutionPlan,
    adapter: TaskAdapter,
    core_client: CoreClient,
    split_id: str,
    supply_builder: SupplyBuilder | None = None,
    arms: Sequence[str] = RAILS_ARMS,
    decoding_params: Mapping[str, object] | None = None,
) -> RunSummary:
    """Execute ``arms`` (default: zero-supply then supplied) for every
    sample ``adapter.load_split(split_id)`` returns, through
    ``core_client`` -- enforcing, before any sample runs:

    1. ``plan.validate()`` (raises ``contracts.ExecutionScopeError`` on a
       malformed plan -- this itself calls ``assert_execution_scope``
       internally).
    2. ``contracts.assert_execution_scope(plan.execution_profile)`` again,
       explicitly, so the enforcement point is named directly in this
       function's own body rather than only transitively via step 1.
    3. The advisory flight lock (``core.flight_lock.read_flight_lock`` --
       best-effort, never fail-closed by design; see that module's own
       docstring) is read and threaded into the returned summary for
       provenance, exactly as advisory as the module that produces it.

    ``SUPPLIED_ARM`` requires ``supply_builder``; requesting it without one
    is refused before any sample runs (fail closed, not a silent skip). For
    every sample, ``ObsPacket``/query are resolved ONCE
    (``rails.obs.default_obs_packet`` + ``adapter.build_query``) and reused
    across every arm for that sample -- they do not depend on which arm is
    running, only on the sample itself.
    """

    plan.validate()
    assert_execution_scope(plan.execution_profile)
    for arm in arms:
        if arm not in RAILS_ARMS:
            raise RailsRunnerError(f"unknown rails arm {arm!r}; known arms are {RAILS_ARMS}")
    if SUPPLIED_ARM in arms and supply_builder is None:
        raise RailsRunnerError(f"arm {SUPPLIED_ARM!r} requires a supply_builder; none was given")

    flight_lock = read_flight_lock(Path(data_root))
    samples = adapter.load_split(split_id)
    if not samples:
        raise RailsRunnerError(f"split {split_id!r} resolved to zero samples")

    results: list[ArmResult] = []
    for sample in samples:
        obs = default_obs_packet(sample)
        query = adapter.build_query(sample, obs)
        for arm in arms:
            supply = supply_builder(sample, obs, query) if arm == SUPPLIED_ARM else None
            if supply is not None:
                supply.validate()
            results.append(
                _run_one_arm(
                    arm=arm,
                    adapter=adapter,
                    core_client=core_client,
                    sample=sample,
                    supply=supply,
                    decoding_params=decoding_params,
                )
            )

    return RunSummary(
        run_id=plan.run_id,
        protocol_hash=plan.protocol_hash,
        arms=tuple(arms),
        results=tuple(results),
        flight_lock=flight_lock,
    )
