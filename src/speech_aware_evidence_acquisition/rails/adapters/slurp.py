"""SLURP slot-filling ``TaskAdapter`` (B0 rails).

Carrier admission: the bounded discovery-probe carrier admitted by the
2026-08-15 owner amendment (Amendment 2, umbrella
``wiki/experiments/speech-aware-evidence-acquisition/
2026-08-15-owner-go-dual-track-agentic.md``): "SLURP slot filling enters as
a task carrier under the existing boundary's entity clause (slot values are
entity extraction from human speech). Probe scope: user-ontology matching ->
slot repair -> command-level success, deployment-legal knowledge only ...
after the R4 acquisition verification."

License split (governed metadata's own annotation-receipt.json, umbrella
``docs/datasets.lock.json``'s ``slurp`` entry): the textual annotation layer
this adapter reads (scenario/action/entities/tokens) is Creative Commons
Attribution 4.0 International (CC BY 4.0); the audio this adapter points
prompts at is Creative Commons Attribution-NonCommercial 4.0 International
(CC BY-NC 4.0) -- the NC term binds every use of the ``.flac`` bytes this
module resolves paths to, even though it never reads their content itself.

Supersedes the former interface-complete stub now that ``data.slurp`` and
``reproduction.slurp_scoring`` exist to back it (every method used to raise
``NotImplementedError`` with a TODO; ``git log`` this file for that
history) -- governed SLURP metadata landed 2026-08-17 (``data.slurp``
module docstring has the full layout/split-discipline account).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from ...data.lock import REPO_ROOT
from ...data.slurp import SLURP_LOCK_KEY, load_slurp_ontology, load_slurp_split, render_slurp_ontology
from ...reproduction.slurp_scoring import SlotEntity, parse_slu_response, score_slu
from ..consumption import ConsumptionTrace, build_consumption_trace
from ..obs import AudioRef, ObsPacket
from ..supply import SupplyPacket
from ..task_adapter import TaskAdapter

_INSTRUCTION = (
    "You are given spoken audio expressing one command to a voice assistant. "
    "Identify the scenario, the action, and every entity slot (type and "
    "value) expressed in the speech.\n\n"
    'Respond with ONLY a JSON object of the form '
    '{"scenario": "...", "action": "...", "entities": '
    '[{"type": "...", "filler": "..."}, ...]}.'
)


@dataclass(frozen=True)
class SlurpSample:
    """``TaskSample`` shape for SLURP (module docstring) -- ``sample_id``/
    ``audio_ref``/``audio_seconds`` satisfy ``rails.task_adapter.
    TaskSample``; ``utterance_id``/``scenario``/``action``/``intent``/
    ``entities`` carry SLURP's own SLU gold layer directly on the sample
    (unlike ``rails.adapters.audio2tool.Audio2ToolSample``, which keeps gold
    off the sample entirely and re-derives it scorer-side) -- deliberately
    WITHOUT the raw sentence text (``data.slurp.SlurpRecord`` docstring).
    Carrying these fields here is loader-legal; the boundary this study's
    own gold-leak test enforces is that ``SlurpAdapter.assemble_prompt``
    below never renders them into prompt text."""

    sample_id: str
    audio_ref: AudioRef
    audio_seconds: float
    utterance_id: str
    media_relpath: str
    scenario: str
    action: str
    intent: str
    entities: tuple[SlotEntity, ...]


class SlurpAdapter(TaskAdapter):
    """``TaskAdapter`` over the governed-metadata-scoped SLURP carrier
    (module docstring)."""

    def __init__(
        self, lock: Mapping[str, object], root: Path, *, repo_root: Path | None = None
    ) -> None:
        self._lock = lock
        self._root = Path(root)
        self._repo_root = Path(REPO_ROOT if repo_root is None else repo_root)

    def load_split(
        self, split_id: str, *, allow_heldout: bool = False, allow_synthetic: bool = False
    ) -> Sequence[SlurpSample]:
        """``split_id`` is one of ``data.slurp``'s four governed splits.
        ``allow_heldout``/``allow_synthetic`` default closed (``data.slurp.
        load_slurp_split``'s own split-discipline account) -- additive,
        defaulted keyword-only refusals; the base ``TaskAdapter.
        load_split(split_id)`` call shape a caller that only ever wants
        ``devel`` needs stays intact."""

        records = load_slurp_split(
            self._lock,
            self._root,
            split_id,
            allow_heldout=allow_heldout,
            allow_synthetic=allow_synthetic,
        )
        samples = [
            SlurpSample(
                sample_id=record.sample_id,
                audio_ref=self._audio_ref(record.media_relpath),
                audio_seconds=record.audio_seconds,
                utterance_id=record.utterance_id,
                media_relpath=record.media_relpath,
                scenario=record.scenario,
                action=record.action,
                intent=record.intent,
                entities=record.entities,
            )
            for record in records
        ]
        return tuple(sorted(samples, key=lambda sample: sample.sample_id))

    def _audio_ref(self, media_relpath: str) -> AudioRef:
        media_path = self._root / media_relpath
        digest = hashlib.sha256(media_path.read_bytes()).hexdigest()
        return AudioRef(path=media_relpath, sha256=digest).validate()

    def build_task_contract(self, sample: SlurpSample, obs: ObsPacket) -> str:
        """Return the TRAIN-only ontology roster as stable task schema.

        The spoken command remains the query. The entity types, example
        fillers, scenarios, and actions define what its slots may match
        (module docstring, entity clause's own
        "user-ontology matching" probe scope) -- mined from ``train``/
        ``train_synthetic`` only (``data.slurp.load_slurp_ontology``), never
        from ``sample``'s own gold fields."""

        ontology = load_slurp_ontology(self._lock, self._root)
        return render_slurp_ontology(ontology)

    def assemble_prompt(
        self, sample: SlurpSample, supply: SupplyPacket | None
    ) -> Sequence[Mapping[str, object]]:
        """Fixed task instruction plus the sample's own audio -- gold-leak
        boundary (module docstring): NOTHING from ``sample.scenario``/
        ``action``/``intent``/``entities`` is ever read here; the only text
        besides the fixed instruction is ``supply.prompt_block`` when a
        caller's ``supply_builder`` chose to inject a roster."""

        content: list[Mapping[str, object]] = []
        if supply is not None:
            content.append({"type": "text", "text": supply.prompt_block})
        content.append({"type": "input_audio", "media_relpath": sample.media_relpath})
        return (
            {"role": "system", "content": _INSTRUCTION},
            {"role": "user", "content": content},
        )

    def score(self, sample: SlurpSample, response: str) -> Mapping[str, object]:
        """Post-hoc only (module docstring): gold (``sample.scenario``/
        ``action``/``entities``) is read HERE, never in
        ``assemble_prompt``/``build_task_contract`` above. See
        ``reproduction.slurp_scoring`` module docstring for the
        ``slot_f1_exact`` vs official ``slu_f1`` distinction -- never
        mislabeled, per this mission's own instruction."""

        predicted_scenario, predicted_action, predicted_entities, parsed = parse_slu_response(response)
        result = score_slu(
            gold_scenario=sample.scenario,
            gold_action=sample.action,
            gold_entities=sample.entities,
            predicted_scenario=predicted_scenario,
            predicted_action=predicted_action,
            predicted_entities=tuple(predicted_entities),
        )
        metrics = dict(result.as_metrics_dict())
        metrics["parsed"] = parsed
        return metrics

    def extract_consumption(
        self, sample: SlurpSample, supply: SupplyPacket | None, response: str
    ) -> ConsumptionTrace:
        return build_consumption_trace(span_id="full", supply=supply, response_text=response)


__all__ = ["SLURP_LOCK_KEY", "SlurpAdapter", "SlurpSample"]
