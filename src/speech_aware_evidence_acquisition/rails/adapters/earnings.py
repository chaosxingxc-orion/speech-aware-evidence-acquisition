"""Earnings21/22 ASR ``TaskAdapter`` (C2 rails, third concrete adapter).

Plain automatic speech recognition over the core Earnings21/22 carrier pair
this study's frozen scoring stack already backs (``data.loader``,
``core.scorers``, ``scoring.wer``, ``scoring.normalize``) -- unlike
Audio2Tool/SLURP, this adapter needs no bespoke response parser: the model's
whole response text IS the hypothesis transcript, scored word-for-word
against the carrier's own ``.nlp`` reference tokens.

Reference-import isolation (``tests/contract/
test_reference_import_isolation.py``, AST-enforced, ``core/scorers.py``'s own
module docstring: "This is the ONLY module allowed to import
data.references... It runs strictly after the runtime phase, on recorded
outputs -- never inside a request loop"): this module therefore NEVER
imports ``data.references`` -- not even lazily inside a function, since the
contract check walks the whole file's AST regardless of nesting. Instead,
:meth:`Earnings21Adapter.score_response` reaches the frozen reference layer
exclusively through ``core.scorers.score_asr_outputs``, the one sanctioned
post-hoc entry point, by handing it a one-row outputs file for the single
response being scored. This is genuinely post-hoc, not "inside a request
loop": the base ``TaskAdapter.score`` docstring already documents ``score``
itself as running strictly after ``core_client.complete()`` has returned
(``rails.runner._run_one_arm`` calls ``score`` only once a response text
already exists) -- the SAME discipline ``score_asr_outputs`` requires of its
own caller, just exercised one response at a time instead of one whole
outputs file at a time. :meth:`Earnings21Adapter.gold` therefore returns the
sample's OWN identity (``carrier_lock_key``/``sample_id``), never reference
token content -- the actual reference bytes are read only inside
``core.scorers``, at the moment scoring happens, exactly as that module's
own docstring requires.

Split scope: ``load_split`` accepts the two roles ``data.splits`` names for
this carrier pair -- ``"discovery"`` (``data.splits.discovery_split``, the
Earnings21 carrier in full) and ``"dev"`` (``data.splits.dev_split``, the
Earnings22 subset10 carrier). The two roles resolve to DIFFERENT physical
carriers (``earnings21-original`` vs ``earnings22-original``) with the same
media/reference layout shape (``data.carriers.CarrierDescriptor``) --
``EarningsSample.carrier_lock_key`` records which one a given sample came
from, so ``core.scorers.score_asr_outputs`` always reads the right carrier's
reference layer. ``"discovery"`` resolves through the frozen
``data.loader.load_earnings21`` wrapper directly; ``"dev"`` resolves its
carrier's descriptor dynamically via ``data.carriers.get_carrier_descriptor``
and loads through the shared ``data.loader.load_carrier`` (the exact
function ``load_earnings21``/``load_earnings22`` are themselves thin
wrappers over) -- deliberately NOT a hardcoded import of the Earnings22
descriptor constant, so this module stays agnostic to how ``data.carriers``
names or shapes that second descriptor.

Evidence/ConEC supply is explicitly NOT this adapter's job: it arrives, if
at all, as a ``SupplyPacket`` the rails runner's own ``supply_builder``
constructs and passes into the base ``TaskAdapter.assemble_prompt``
default -- this module never reads ``core.evidence`` or ConEC context text.

Gold discipline (D2, unchanged, ``rails.task_adapter`` module docstring):
gold identity is read ONLY inside :meth:`Earnings21Adapter.gold`/
:meth:`Earnings21Adapter.score_response`, never inside
:meth:`Earnings21Adapter.instruction`/``build_task_contract``.
"""

from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from ...core.scorers import score_asr_outputs
from ...data.carriers import get_carrier_descriptor
from ...data.loader import load_carrier, load_earnings21
from ...data.lock import REPO_ROOT
from ...data.splits import dev_split, discovery_split
from ..obs import AudioRef, ObsPacket
from ..task_adapter import TaskAdapter

_DISCOVERY_SPLIT_ID = "discovery"
_DEV_SPLIT_ID = "dev"
_ASR_INSTRUCTION_TEMPLATE_RELPATH = ("configs", "probes", "r4_transcribe_nocontext.txt")

_TASK_CONTRACT = (
    "Automatic speech recognition (ASR) over one Earnings21/22 call segment: "
    "transcribe the spoken English exactly, word for word. There is no tool "
    "registry, ontology, or evidence text in this task's fixed schema -- "
    "ConEC evidence, when supplied at all, arrives ONLY as prompt-level "
    "SupplyPacket text the rails runner builds separately, never through "
    "this contract and never through gold."
)


@dataclass(frozen=True)
class EarningsSample:
    """One Earnings21/22 ASR sample -- ``sample_id``/``audio_ref``/
    ``audio_seconds`` satisfy ``rails.task_adapter.TaskSample``;
    ``media_relpath`` is what the base ``TaskAdapter.assemble_prompt``
    default needs to point the message at the actual audio file.
    ``carrier_lock_key`` (``"earnings21-original"`` for the discovery split,
    ``"earnings22-original"`` for the dev split, module docstring) names
    which physical carrier's reference layer
    :meth:`Earnings21Adapter.score_response` must read for this sample --
    the actual reference transcript is looked up scorer-side, keyed on this
    field, never carried on the sample itself."""

    sample_id: str
    audio_ref: AudioRef
    audio_seconds: float
    media_relpath: str
    carrier_lock_key: str


class Earnings21Adapter(TaskAdapter):
    """``TaskAdapter`` over the Earnings21 discovery / Earnings22 dev ASR
    carrier pair (module docstring)."""

    # Owner-documented serving geometry (rails.task_adapter.TaskAdapter.
    # serving_geometry docstring) -- PROVISIONAL: no ASR flight has
    # exercised this carrier through the rails runner yet, so these three
    # numbers are a first estimate (SLURP-shaped slot/slot_tokens, a wider
    # max_tokens for full-call transcripts), not a measured budget. Revisit
    # once a real Earnings21/22 rails run exists.
    SERVING_SLOTS = 8
    SERVING_SLOT_TOKENS = 8192
    SERVING_MAX_TOKENS = 512

    def __init__(
        self, lock: Mapping[str, object], root: Path, *, repo_root: Path | None = None
    ) -> None:
        self._lock = lock
        self._root = Path(root)
        self._repo_root = Path(REPO_ROOT if repo_root is None else repo_root)

    def load_split(self, split_id: str) -> Sequence[EarningsSample]:
        """``split_id`` is ``"discovery"`` (Earnings21, in full) or
        ``"dev"`` (Earnings22 subset10) -- module docstring. Every sample
        the matching ``data.splits`` spec names, sorted by ``sample_id``."""

        if split_id == _DISCOVERY_SPLIT_ID:
            spec = discovery_split(self._lock, self._root)
            refs = load_earnings21(self._lock, self._root)
        elif split_id == _DEV_SPLIT_ID:
            spec = dev_split(self._lock, self._root)
            descriptor = get_carrier_descriptor(spec.carrier_lock_key)
            refs = load_carrier(descriptor, self._lock, self._root)
        else:
            raise ValueError(
                f"unknown Earnings split_id {split_id!r}; expected "
                f"{_DISCOVERY_SPLIT_ID!r} or {_DEV_SPLIT_ID!r}"
            )
        prefix = f"{spec.carrier_lock_key}/"
        wanted_ids = {prefixed_id[len(prefix) :] for prefixed_id in spec.ids}
        samples = [
            EarningsSample(
                sample_id=ref.sample_id,
                audio_ref=self.audio_ref(ref.media_relpath),
                audio_seconds=ref.audio_seconds,
                media_relpath=ref.media_relpath,
                carrier_lock_key=ref.carrier_lock_key,
            )
            for ref in refs
            if ref.sample_id in wanted_ids
        ]
        return tuple(sorted(samples, key=lambda sample: sample.sample_id))

    def build_task_contract(self, sample: EarningsSample, obs: ObsPacket) -> str:
        """Fixed English ASR task description -- no evidence, no gold
        (module docstring)."""

        return _TASK_CONTRACT

    def instruction(self, sample: EarningsSample) -> str:
        """The frozen R4 no-context ASR instruction template
        (``configs/probes/r4_transcribe_nocontext.txt``), read relative to
        ``self._repo_root`` the same way every other repo-relative template
        read in this study resolves (``data.lock.REPO_ROOT`` default) -- the
        same text for every sample, so ``sample`` is unused."""

        template_path = self._repo_root.joinpath(*_ASR_INSTRUCTION_TEMPLATE_RELPATH)
        try:
            return template_path.read_text(encoding="utf-8")
        except OSError as error:
            raise ValueError(
                f"cannot read ASR instruction template {template_path}: {error}"
            ) from error

    def gold(self, sample: EarningsSample) -> EarningsSample:
        """Gold IS the sample's own identity for Earnings21/22: just
        ``carrier_lock_key``/``sample_id`` (module docstring) -- the actual
        reference transcript bytes are read only inside
        :meth:`score_response`, through ``core.scorers.score_asr_outputs``,
        never here and never in ``instruction``/``build_task_contract``."""

        return sample

    def score_response(self, gold: EarningsSample, response: str) -> Mapping[str, object]:
        """Word error rate for ``response`` against ``gold``'s reference
        transcript, computed ENTIRELY through ``core.scorers.
        score_asr_outputs`` -- the sole module this study's
        ``tests/contract/test_reference_import_isolation.py`` permits to
        import ``data.references`` (module docstring). A one-row outputs
        file is the shape that function requires; this call is otherwise
        exactly the single-sample post-hoc scoring ``rails.runner.
        _run_one_arm`` already performs through ``TaskAdapter.score``."""

        row = {
            "carrier_lock_key": gold.carrier_lock_key,
            "sample_id": gold.sample_id,
            "text": response,
        }
        with tempfile.TemporaryDirectory() as scratch_dir:
            outputs_path = Path(scratch_dir) / "earnings-single-sample.outputs.jsonl"
            outputs_path.write_text(json.dumps(row) + "\n", encoding="utf-8")
            result = score_asr_outputs(outputs_path, self._lock, self._root)
        entry = result["per_sample"][0]
        return {
            "wer": entry["wer"],
            "substitutions": entry["substitutions"],
            "deletions": entry["deletions"],
            "insertions": entry["insertions"],
            "reference_words": len(entry["ref_hit_mask"]),
            "parsed": True,
        }


__all__ = ["Earnings21Adapter", "EarningsSample"]
