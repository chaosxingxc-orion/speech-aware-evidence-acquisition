"""TaskAdapter: the unified interface every carrier-specific task plugs into
the shared rails runner through -- exactly the five methods the B0 mission
freezes: ``load_split``, ``build_task_contract``, ``assemble_prompt``,
``score``, ``extract_consumption``. Existing callers (``rails.runner``,
probes, tests) still see exactly this five-method public shape; ``ObsPacket``
construction remains a plain, reusable function
(``rails.obs.default_obs_packet``), not a sixth interface method.

C2 consolidation ("one task base, thin adapters"): before this change,
``rails.adapters.audio2tool.Audio2ToolAdapter`` and
``rails.adapters.slurp.SlurpAdapter`` each hand-wrote their own identical
sha256 ``AudioRef`` helper, their own identical ``assemble_prompt`` message
shape, and their own identical ``rails.consumption.build_consumption_trace``
call inside ``extract_consumption``. This base class now owns every one of
those as a concrete default; a carrier adapter overrides only what is
genuinely task-specific. ``load_split``/``build_task_contract`` stay
abstract (a carrier's split membership and task-schema text have no
cross-carrier default); ``instruction``/``gold``/``score_response`` are new,
narrower extension points a concrete adapter fills in instead of
reimplementing ``assemble_prompt``/``score`` wholesale -- deliberately NOT
declared via ``@abc.abstractmethod`` (several ``rails.probes.*`` adapters
predate this refactor and fully override ``assemble_prompt``/``score``
themselves without ever touching these hooks; making them ABC-abstract
would make those adapters uninstantiable). A concrete adapter that relies on
the base ``assemble_prompt``/``score`` defaults WITHOUT implementing
``instruction``/``gold``/``score_response`` fails loudly the first time that
hook is actually called, via the ``NotImplementedError`` below -- not at
class-definition time.

Gold discipline (D2, unchanged): gold text or gold-derived structure must
never enter ``assemble_prompt``/``build_task_contract``; it is read only
inside ``gold``/``score_response``, both reached exclusively from ``score``
-- strictly post-hoc, after a response already exists (mirrors
``core.scorers``' own "scoring runs strictly after the runtime phase, never
inside a request loop" discipline).
"""

from __future__ import annotations

import abc
import hashlib
from dataclasses import dataclass
from typing import Mapping, Protocol, Sequence, runtime_checkable

from .candidate_contract_lookup import CandidateContractProvider
from .consumption import ConsumptionTrace, build_consumption_trace
from .obs import AudioRef, ObsPacket
from .supply import SupplyPacket


@runtime_checkable
class TaskSample(Protocol):
    """The minimal shape ``rails.obs.default_obs_packet`` needs -- a stable
    id plus enough audio identity to build a whole-file ``ObsPacket``.
    Concrete adapters attach whatever additional task-specific fields they
    need on their own sample dataclass (e.g. ``rails.adapters.audio2tool.
    Audio2ToolSample.media_relpath``); this Protocol names only the common
    subset the rails layer itself relies on. The base ``TaskAdapter.
    assemble_prompt`` default additionally reads ``sample.media_relpath``
    (not part of this Protocol, by the same convention) -- every concrete
    sample dataclass in this study carries it."""

    sample_id: str
    audio_ref: AudioRef
    audio_seconds: float


@dataclass(frozen=True)
class CandidateInventory:
    """A carrier's complete ordered candidate names and source identity."""

    candidate_ids: tuple[str, ...]
    source_sha256: str
    source_authority: str

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> "CandidateInventory":
        if not isinstance(self.candidate_ids, tuple):
            raise ValueError("candidate_ids must be a tuple")
        if not self.candidate_ids:
            raise ValueError("candidate_ids must be non-empty")
        for candidate_id in self.candidate_ids:
            if (
                not isinstance(candidate_id, str)
                or not candidate_id
                or candidate_id.strip() != candidate_id
                or not candidate_id.isascii()
            ):
                raise ValueError(
                    "candidate_ids must contain non-empty trimmed ASCII names"
                )
        if len(self.candidate_ids) != len(set(self.candidate_ids)):
            raise ValueError("candidate_ids contains a duplicate")
        if (
            not isinstance(self.source_sha256, str)
            or len(self.source_sha256) != 64
            or any(char not in "0123456789abcdef" for char in self.source_sha256)
        ):
            raise ValueError("source_sha256 must be 64 lowercase hex characters")
        if (
            not isinstance(self.source_authority, str)
            or not self.source_authority
            or self.source_authority.strip() != self.source_authority
            or not self.source_authority.isascii()
        ):
            raise ValueError("source_authority must be non-empty trimmed ASCII text")
        return self


class TaskAdapter(abc.ABC):
    """One task carrier's plug into the shared rails runner (mission-frozen
    five-method shape), now implemented as a full base class rather than a
    bare interface (module docstring, C2 consolidation).

    Serving-geometry defaults (see :meth:`serving_geometry`) are read from
    three class attributes so a subclass overrides plain data instead of a
    method body. The values below are the base's own fallback only; every
    concrete adapter in ``rails.adapters`` sets its own carrier-specific
    numbers explicitly rather than relying on this fallback being right for
    it.
    """

    SERVING_SLOTS: int = 1
    SERVING_SLOT_TOKENS: int = 8192
    SERVING_MAX_TOKENS: int = 512

    # -- still abstract: no cross-carrier default exists ---------------

    @abc.abstractmethod
    def load_split(self, split_id: str) -> Sequence[TaskSample]:
        """Every sample belonging to ``split_id`` (e.g. a frozen probe
        receipt's ``split_role``, or a carrier-specific split name), sorted
        deterministically."""

    @abc.abstractmethod
    def build_task_contract(self, sample: TaskSample, obs: ObsPacket) -> str:
        """Stable task schema/ontology text available for ``sample``.

        This is never the query. The query is the sample's speech observation;
        a speech-native AgentLoop binds it separately as a ``QueryState``.
        Retrieval may use this contract to interpret the task vocabulary, but
        must not treat it as an audio-derived hypothesis or transcript.
        """

    # -- shared concrete helper -----------------------------------------

    def audio_ref(self, media_relpath: str) -> AudioRef:
        """Shared sha256 identity helper: re-hash the media file at
        ``self._root / media_relpath`` and validate the result. Every
        concrete adapter's ``load_split`` in this study builds each
        sample's ``AudioRef`` through this one method rather than its own
        copy of the same three lines.

        Convention: a subclass that relies on this default must set
        ``self._root`` (a ``pathlib.Path``, the carrier's materialized data
        root) in its own constructor -- the SAME convention every concrete
        adapter under ``rails.adapters`` already follows.
        """

        media_path = self._root / media_relpath
        digest = hashlib.sha256(media_path.read_bytes()).hexdigest()
        return AudioRef(path=media_relpath, sha256=digest).validate()

    def _audio_ref(self, media_relpath: str) -> AudioRef:
        """Backward-compatible private alias for :meth:`audio_ref`.

        Several frozen historical launcher scripts under
        ``docs/checks/*/launcher/`` subclass ``Audio2ToolAdapter``/
        ``SlurpAdapter`` and call ``self._audio_ref(...)`` directly (the
        method's name before this refactor); kept so this consolidation does
        not silently break those already-run receipts.
        """

        return self.audio_ref(media_relpath)

    # -- new, narrower extension points ---------------------------------

    def instruction(self, sample: TaskSample) -> str:
        """The system instruction text the default :meth:`assemble_prompt`
        renders as its system message. No cross-carrier default exists --
        every concrete adapter that relies on the default ``assemble_prompt``
        must implement this."""

        raise NotImplementedError(f"{type(self).__name__} must implement instruction()")

    def gold(self, sample: TaskSample) -> object:
        """The gold structure :meth:`score_response` scores a response
        against for ``sample`` -- read ONLY here (module docstring's gold
        discipline), never from ``assemble_prompt``/``build_task_contract``.
        No cross-carrier default exists: a tuple of expected tool calls, the
        sample's own SLU fields, reference transcript tokens, and so on are
        all carrier-specific shapes; every concrete adapter that relies on
        the default :meth:`score` must implement this."""

        raise NotImplementedError(f"{type(self).__name__} must implement gold()")

    def score_response(self, gold: object, response: str) -> Mapping[str, object]:
        """The carrier's own per-sample scoring function: ``gold`` (this
        adapter's own :meth:`gold` output) against one model ``response``.
        No cross-carrier default exists; every concrete adapter that relies
        on the default :meth:`score` must implement this."""

        raise NotImplementedError(f"{type(self).__name__} must implement score_response()")

    # -- concrete defaults built from the extension points above --------

    def assemble_prompt(
        self, sample: TaskSample, supply: SupplyPacket | None
    ) -> Sequence[Mapping[str, object]]:
        """Chat-style messages (``[{"role": ..., "content": ...}, ...]``)
        for ``sample``, with ``supply`` folded in as prompt-level text ONLY
        (owner ruling: no logit_bias anywhere in this study) when not
        ``None``; ``supply is None`` is the zero-supply arm.

        Default shape (byte-identical to what every carrier adapter in this
        study built by hand before this refactor): one system message
        (:meth:`instruction`) plus one user message whose content is
        ``[optional supply text, input_audio]``. A carrier whose prompt
        shape genuinely differs overrides this method outright.
        """

        content: list[Mapping[str, object]] = []
        if supply is not None:
            content.append({"type": "text", "text": supply.prompt_block})
        content.append({"type": "input_audio", "media_relpath": sample.media_relpath})
        return (
            {"role": "system", "content": self.instruction(sample)},
            {"role": "user", "content": content},
        )

    def score(self, sample: TaskSample, response: str) -> Mapping[str, object]:
        """Task metrics for one response -- POST-HOC only (mirrors
        ``core.scorers``' own "scoring runs strictly after the runtime
        phase, never inside a request loop" discipline); gold enters here,
        never through ``assemble_prompt`` (D2, unchanged).

        Default: :meth:`gold` looked up first, then scored against
        ``response`` via :meth:`score_response`. A carrier whose scoring
        needs more than this two-step shape overrides ``score`` outright.
        """

        return self.score_response(self.gold(sample), response)

    def extract_consumption(
        self, sample: TaskSample, supply: SupplyPacket | None, response: str
    ) -> ConsumptionTrace:
        """USE/COPY/IGNORE attribution of ``supply`` against ``response``.

        Default: built via ``rails.consumption.build_consumption_trace``
        over the whole-sample span -- every adapter in this study reuses
        this unchanged; a carrier with a different consumption unit than
        "one span, whole supply" overrides it."""

        return build_consumption_trace(span_id="full", supply=supply, response_text=response)

    # -- additional non-abstract hooks (owner design: Part B fills these
    # in further; today they carry small, honest defaults) --------------

    def candidate_contract_provider(
        self, *, excluded_construction_ids: Sequence[str] = ()
    ) -> CandidateContractProvider | None:
        """Return this carrier's canonical candidate contracts, when configured.

        The default is exactly no provider. A task adapter may prepare and cache
        an immutable provider when this hook is explicitly requested before a
        model run; ordinary historical adapter construction remains free of
        that task-specific I/O. Canonical construction exclusions name source
        units to omit, including all their recordings; unsupported adapters refuse them.
        """

        if excluded_construction_ids:
            raise ValueError("this adapter has no excluded-construction contract provider")
        return None

    def candidate_inventory(self) -> CandidateInventory | None:
        """Return the provider's complete candidate roster when one exists.

        This default deliberately delegates to the existing task-specific
        contract provider. It does not create a second source of candidate
        legality, and adapters with no provider retain an absent inventory.
        """

        provider = self.candidate_contract_provider()
        if provider is None:
            return None
        return CandidateInventory(
            candidate_ids=getattr(provider, "candidate_ids", None),
            source_sha256=provider.source_sha256,
            source_authority="task-adapter-candidate-contract-provider",
        )

    def strata_of(self, sample: TaskSample) -> str:
        """Which analysis stratum ``sample`` belongs to. Default ``"all"``
        for a carrier with no stratification of its own."""

        return "all"

    def information_spec(self) -> Mapping[str, object]:
        """Reserved extension point: a future Part B mission fills this in
        with the carrier's own information-content declaration. Empty by
        default -- no carrier populates it yet."""

        return {}

    def bind_runtime(self, runtime: object, values: Mapping[str, object]) -> None:
        """Bind carrier-specific material through shared runtime seams, if required.

        A plain adapter needs no additional material. Config-driven carrier views
        may bind frozen providers or judge material here before preflight.
        """

    def serving_geometry(self) -> Mapping[str, object]:
        """This carrier's serving geometry (slot count, tokens reserved per
        slot, and max generated tokens), read from the
        ``SERVING_SLOTS``/``SERVING_SLOT_TOKENS``/``SERVING_MAX_TOKENS``
        class attributes a concrete adapter overrides with its own
        documented numbers."""

        return {
            "slots": self.SERVING_SLOTS,
            "slot_tokens": self.SERVING_SLOT_TOKENS,
            "max_tokens": self.SERVING_MAX_TOKENS,
        }

    def preprocess_plan(self) -> Mapping[str, object]:
        """Default offline-preprocessing shape every carrier starts from;
        a carrier with different preprocessing needs overrides this."""

        return {"kind": "speech-packets", "workers": 8}
