"""SLURP slot-filling ``TaskAdapter`` (B0 rails): interface-complete STUB.

SLURP entered this study's scope via the entity clause (2026-08-15 owner
amendment, Amendment 2, umbrella
``wiki/experiments/speech-aware-evidence-acquisition/
2026-08-15-owner-go-dual-track-agentic.md``): "SLURP slot filling enters as
a task carrier under the existing boundary's entity clause (slot values are
entity extraction from human speech). Probe scope: user-ontology matching ->
slot repair -> command-level success, deployment-legal knowledge only ...
after the R4 acquisition verification."

No SLURP lock entry, on-disk layout, or loader exists in this repository
yet -- a separate agent is inventorying local bytes/layout concurrently with
this B0 rails-freeze mission, and this adapter deliberately does not block
on that inventory landing first (mission instruction: "write
interface-complete stubs with TODOs if local bytes/layout are unclear").

Every method below is STRUCTURALLY complete against the same ``TaskAdapter``
shape ``rails.adapters.audio2tool.Audio2ToolAdapter`` implements, but raises
``NotImplementedError`` with a TODO pointing at the missing piece -- there is
no SLURP loader to call yet, so any real implementation here would be a
guess this module refuses to make. Replace each TODO once a SLURP loader
(``data.slurp`` or wherever it lands) exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from ..consumption import ConsumptionTrace
from ..obs import AudioRef, ObsPacket
from ..supply import SupplyPacket
from ..task_adapter import TaskAdapter


@dataclass(frozen=True)
class SlurpSample:
    """``TaskSample`` shape for SLURP -- ``sample_id``/``audio_ref``/
    ``audio_seconds`` satisfy ``rails.task_adapter.TaskSample``;
    ``utterance_id``/``scenario`` mirror the two identity fields the public
    SLURP release itself carries per record (its ``recordings.jsonl``'s own
    ``slurp_id``/``scenario`` columns), named here ahead of the loader
    landing so a real loader has an obvious target shape to fill rather than
    inventing one from scratch."""

    sample_id: str
    audio_ref: AudioRef
    audio_seconds: float
    utterance_id: str
    scenario: str


class SlurpAdapter(TaskAdapter):
    """STUB (module docstring): every method raises ``NotImplementedError``
    until a SLURP loader lands. Constructible today so rails-layer plumbing
    (the runner, TaskAdapter-shape tests) can exercise "an adapter that is
    not Audio2Tool" without waiting on the SLURP inventory."""

    def __init__(
        self, lock: Mapping[str, object], root: Path, *, repo_root: Path | None = None
    ) -> None:
        self._lock = lock
        self._root = Path(root)
        self._repo_root = repo_root

    def load_split(self, split_id: str) -> Sequence[SlurpSample]:
        # TODO(slurp-loader): no data.slurp loader/lock entry exists yet
        # (module docstring); wire this to whatever load_slurp(lock, root)
        # the concurrent inventory task lands, filtered to split_id the
        # same way Audio2ToolAdapter.load_split filters by split_role.
        raise NotImplementedError(
            "SlurpAdapter.load_split: no SLURP loader exists in this repository yet "
            "(2026-08-15 owner amendment Amendment 2 admits the carrier; the on-disk "
            "layout/lock entry are still being inventoried) -- TODO wire a data.slurp "
            "loader once it lands"
        )

    def build_query(self, sample: SlurpSample, obs: ObsPacket) -> str:
        # TODO(slurp-loader): SLURP's task-native query is presumably the
        # user-ontology (scenario/action/slot-type roster) the slot values
        # must be matched against (mirroring Audio2ToolAdapter.build_query's
        # tool-schema roster) -- the entity clause's own "user-ontology
        # matching" probe scope names this explicitly. Confirm the exact
        # ontology source once the loader lands; do not guess its shape here.
        raise NotImplementedError(
            "SlurpAdapter.build_query: SLURP ontology source is not yet wired -- see "
            "this method's own TODO"
        )

    def assemble_prompt(
        self, sample: SlurpSample, supply: SupplyPacket | None
    ) -> Sequence[Mapping[str, object]]:
        # TODO(slurp-loader): same {system-instruction, user-audio(+supply)}
        # shape Audio2ToolAdapter.assemble_prompt already uses; blocked only
        # on having a real sample.media_relpath (or equivalent) to point at.
        raise NotImplementedError(
            "SlurpAdapter.assemble_prompt: no SLURP media path resolution yet -- see "
            "this method's own TODO"
        )

    def score(self, sample: SlurpSample, response: str) -> Mapping[str, object]:
        # TODO(slurp-loader): slot-filling scoring (slot-F1 at minimum,
        # mirroring reproduction.toolcall_scoring's slot-triple machinery)
        # needs SLURP's own gold slot annotations, scorer-side only (D2) --
        # no such gold layer is wired into data/identity.py yet.
        raise NotImplementedError(
            "SlurpAdapter.score: no SLURP gold/scoring layer wired yet -- see this "
            "method's own TODO"
        )

    def extract_consumption(
        self, sample: SlurpSample, supply: SupplyPacket | None, response: str
    ) -> ConsumptionTrace:
        # Not actually blocked on the loader -- rails.consumption.build_consumption_trace
        # is already generic and works for any SupplyPacket once one exists.
        # Kept raising here anyway rather than silently returning a trace no
        # real assemble_prompt call could ever have produced yet.
        raise NotImplementedError(
            "SlurpAdapter.extract_consumption: no SLURP response is ever produced yet "
            "(assemble_prompt is unimplemented) -- see this class's other TODOs"
        )


__all__ = ["SlurpAdapter", "SlurpSample"]
