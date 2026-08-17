"""P-SLU flight orchestration -- REGISTERED probe (Stage-2, bounded-discovery-
probe): ``docs/readiness/2026-08-17-pslu-preregistration-REGISTERED.md``.

Six arms over the SAME n=60 devel sample set (A0/A1/A1'/A2/A3/A4), NOT run
through ``rails.runner.run_rails_experiment`` -- that runner's ``arms=``
vocabulary is frozen to exactly ``("zero-supply", "supplied")``
(``rails.runner.RAILS_ARMS``); six independently-named, differently-rostered
arms need their own orchestration loop, built from the SAME primitives
that runner composes on top of (``SlurpAdapter.assemble_prompt`` /
``CoreClient.complete`` / ``SlurpAdapter.score`` /
``SlurpAdapter.extract_consumption``), never a reimplementation of them.

Two-phase plan (bridge mission instruction): PHASE 1 sends one zero-supply
(A0) request per sample and parses its predicted scenario
(``reproduction.slurp_scoring.parse_slu_response``) -- this IS the A0 arm's
own scored response, spent once, never a second throwaway call (the
preregistration's own cost line, "6 arms x 60 + headroom", counts phase 1 as
arm A0, not as an extra pass). PHASE 2 sends the remaining five arms (A1,
A1', A2, A3, A4) per sample, where A1' selects its roster by EACH sample's
own phase-1 PREDICTED scenario (self-supplied, deployment-legal) rather than
A1's gold scenario (ceiling-tier, gold-scoped selection -- the
preregistration's own "ceiling companion" label). If phase 1 failed to parse
a scenario, or predicted one outside the 18-scenario roster table, A1' falls
back to the scenario-agnostic A2 roster -- NEVER to the gold scenario: a
gold fallback would silently promote the "self-supplied" arm to ceiling
tier on exactly the samples where the core's own first pass was weakest,
which is precisely backwards.

Rosters come ONLY from ``configs/probes/g0-binding/pslu-rosters-train-only
.json`` (:func:`load_pslu_rosters` checks that file's own
``legality_tier``/``train_synthetic_refused`` fields at load time) --
``data.slurp.load_slurp_ontology`` (the shipped ontology miner, ceiling-tier
for a devel-split probe: 64.8% verbatim ``train_synthetic`` overlap with
``devel``, that function's own docstring) is asserted NOT referenced
anywhere in this module's own source, both at import time and again at the
top of :func:`run_pslu_flight` (:func:`assert_never_calls_ontology_miner`).

Silence-swap (module docstring continued): the 3 seeded A1' samples'
silent-audio variant is NOT generated or registered here -- that is
``rails.silence_swap``'s job (a ``core.model.SliceRecord``, registered via
``FrozenCoreClient.register_slice`` before any flight request runs, since
only a REAL ``FrozenCoreClient`` has a slice registry at all; ``MockCoreClient``
does not). This module's own job is narrower and generic over ANY
``CoreClient``: given a caller-supplied ``sample_id -> already-registered
media_relpath`` mapping, issue one EXTRA A1' request per silence-swap sample
with the audio content part's ``media_relpath`` swapped for the silent one,
same roster text, same instruction.
"""

from __future__ import annotations

import ast
import json
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping, Sequence

from ...reproduction.slurp_scoring import parse_slu_response
from ..adapters.slurp import SlurpAdapter, SlurpSample
from ..consumption import ConsumptionTrace
from ..supply import SupplyDose, SupplyForm, SupplyItem, SupplyPacket

PSLU_PHASE1_ARM = "A0"
PSLU_PHASE2_ARMS: tuple[str, ...] = ("A1", "A1p", "A2", "A3", "A4")
PSLU_ARMS: tuple[str, ...] = (PSLU_PHASE1_ARM, *PSLU_PHASE2_ARMS)

_PROBE_ID = "P-SLU"
_LEGAL_TIER = "legal"
_FORBIDDEN_ONTOLOGY_SYMBOL = "load_slurp_ontology"


class PsluFlightError(RuntimeError):
    """A P-SLU flight input is malformed, a roster table fails its own
    load-time legality checks, or the ontology-miner import guard tripped."""


# ---------------------------------------------------------------------------
# The ontology-miner call guard (module docstring).
# ---------------------------------------------------------------------------


def _source_references_ontology_miner(source: str) -> bool:
    """AST-based (never a plain substring search: this module's OWN
    docstrings legitimately name ``load_slurp_ontology`` in prose, which a
    substring search could not tell apart from a live import/call). True iff
    ``source`` contains an ``import ... load_slurp_ontology``, a bare
    ``load_slurp_ontology`` name reference (covers both a direct call and
    passing the function as a value), or a ``<module>.load_slurp_ontology``
    attribute access."""

    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and any(
            alias.name == _FORBIDDEN_ONTOLOGY_SYMBOL for alias in node.names
        ):
            return True
        if isinstance(node, ast.Name) and node.id == _FORBIDDEN_ONTOLOGY_SYMBOL:
            return True
        if isinstance(node, ast.Attribute) and node.attr == _FORBIDDEN_ONTOLOGY_SYMBOL:
            return True
    return False


def assert_never_calls_ontology_miner(source: str | None = None) -> None:
    """Static, executed guard (bridge mission instruction: "assert at load
    time that load_slurp_ontology is NOT called on this path"). ``source``
    is this module's OWN source text by default (``Path(__file__)``); a
    caller (a test) may pass a synthetic snippet instead. Runs
    automatically at IMPORT time (module-level call at the bottom of this
    file) and again, explicitly, at the top of :func:`run_pslu_flight` --
    so a future edit that adds the forbidden import/call fails LOUD the
    moment this module is next imported, not silently at flight time."""

    text = source if source is not None else Path(__file__).read_text(encoding="utf-8")
    if _source_references_ontology_miner(text):
        raise PsluFlightError(
            f"rails.probes.pslu_flight source references "
            f"{_FORBIDDEN_ONTOLOGY_SYMBOL!r}; this flight is REGISTERED to consume "
            "rosters ONLY from configs/probes/g0-binding/pslu-rosters-train-only.json "
            "(load_pslu_rosters) -- the shipped ontology miner is ceiling-tier for a "
            "devel-split probe (data.slurp.load_slurp_ontology's own docstring: 64.8% "
            "verbatim train_synthetic overlap with devel)"
        )


# ---------------------------------------------------------------------------
# Roster table (configs/probes/g0-binding/pslu-rosters-train-only.json)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PsluRosters:
    """The four roster shapes the binding table's ``arms`` block carries --
    one per non-A0 arm family. ``scenario_rosters`` backs BOTH A1 (gold
    scenario key) and A1' (predicted scenario key); A4 also reads it, keyed
    by its own derangement partner."""

    scenario_rosters: Mapping[str, tuple[tuple[str, str], ...]]
    global_types: tuple[str, ...]
    full_roster: tuple[tuple[str, str], ...]
    derangement: Mapping[str, str]


def load_pslu_rosters(path: Path) -> PsluRosters:
    """Load and validate ``pslu-rosters-train-only.json`` -- checks, at load
    time, that the table declares ``probe == "P-SLU"``,
    ``legality_tier == "legal"``, and
    ``train_synthetic_refused.train_jsonl_overlap_with_devel == 0`` (the
    table's own recorded proof that its rosters are train-split-only and
    zero-overlap with the devel evaluation surface) before trusting any
    roster it carries."""

    document = json.loads(Path(path).read_text(encoding="utf-8"))
    if document.get("probe") != _PROBE_ID:
        raise PsluFlightError(f"{path}: probe must be {_PROBE_ID!r}, got {document.get('probe')!r}")
    if document.get("legality_tier") != _LEGAL_TIER:
        raise PsluFlightError(
            f"{path}: legality_tier must be {_LEGAL_TIER!r}, got {document.get('legality_tier')!r}"
        )
    refused = document.get("train_synthetic_refused")
    if not isinstance(refused, Mapping) or refused.get("train_jsonl_overlap_with_devel") != 0:
        raise PsluFlightError(
            f"{path}: train_synthetic_refused.train_jsonl_overlap_with_devel must be 0"
        )
    try:
        arms = document["arms"]
        scenario_rosters = {
            scenario: tuple((str(t), str(v)) for t, v in entries)
            for scenario, entries in arms["A1_scenario_roster"]["rosters"].items()
        }
        global_types = tuple(str(t) for t in arms["A2_global_type_vocabulary"]["types"])
        full_roster = tuple(
            (str(t), str(v)) for t, v in arms["A3_full_ontology_dose_capped"]["roster"]
        )
        derangement = {str(k): str(v) for k, v in arms["A4_deranged"]["mapping"].items()}
    except (KeyError, TypeError, ValueError) as error:
        raise PsluFlightError(f"{path}: malformed roster table: {error}") from error
    if not scenario_rosters or not global_types or not full_roster or not derangement:
        raise PsluFlightError(f"{path}: one or more roster sections resolved empty")
    return PsluRosters(
        scenario_rosters=scenario_rosters,
        global_types=global_types,
        full_roster=full_roster,
        derangement=derangement,
    )


@dataclass(frozen=True)
class PsluSampleManifest:
    """The frozen n=60 sample set (``configs/probes/g0-binding/pslu-sample-
    devel-n60.json``) -- the ORDERED ``sample_id`` list a real flight must
    run, not "whatever ``SlurpAdapter.load_split('devel')`` happens to
    return" (that call resolves the FULL ~2000-item devel split; the
    preregistered probe scope is exactly this frozen 60)."""

    sample_ids: tuple[str, ...]
    split_identity_hash: str
    seed: int


def load_pslu_sample_manifest(path: Path) -> PsluSampleManifest:
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    if document.get("probe") != _PROBE_ID:
        raise PsluFlightError(f"{path}: probe must be {_PROBE_ID!r}, got {document.get('probe')!r}")
    items = document.get("items")
    if not isinstance(items, list) or not items:
        raise PsluFlightError(f"{path}: no items")
    try:
        sample_ids = tuple(str(item["sample_id"]) for item in items)
    except (KeyError, TypeError) as error:
        raise PsluFlightError(f"{path}: malformed items: {error}") from error
    split_identity_hash = document.get("split_identity_hash")
    if not isinstance(split_identity_hash, str) or len(split_identity_hash) != 64:
        raise PsluFlightError(f"{path}: split_identity_hash must be a 64-hex sha256")
    seed = document.get("seed")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise PsluFlightError(f"{path}: seed must be an integer")
    if len(set(sample_ids)) != len(sample_ids):
        raise PsluFlightError(f"{path}: duplicate sample_id in items")
    return PsluSampleManifest(sample_ids=sample_ids, split_identity_hash=split_identity_hash, seed=seed)


def select_pslu_samples(
    all_samples: Sequence[SlurpSample], manifest: PsluSampleManifest
) -> tuple[SlurpSample, ...]:
    """Filter+order ``all_samples`` (e.g. every ``SlurpAdapter.
    load_split("devel")`` result) down to EXACTLY ``manifest.sample_ids``,
    in that frozen order -- fail-closed if any id is missing: the probe's
    n=60 sample set is frozen pre-registration, so a run must never
    silently resolve to fewer samples than registered."""

    by_id = {sample.sample_id: sample for sample in all_samples}
    missing = [sample_id for sample_id in manifest.sample_ids if sample_id not in by_id]
    if missing:
        raise PsluFlightError(
            f"sample manifest names {len(missing)} sample id(s) not present in the loaded "
            f"split: {missing[:5]}{'...' if len(missing) > 5 else ''}"
        )
    return tuple(by_id[sample_id] for sample_id in manifest.sample_ids)


def render_roster_entries(entries: Sequence[tuple[str, str]]) -> str:
    return "; ".join(f"{entry_type}={value}" for entry_type, value in entries)


def render_type_vocabulary(types: Sequence[str]) -> str:
    return ", ".join(types)


def _roster_packet(arm: str, entries: Sequence[tuple[str, str]]) -> SupplyPacket:
    prompt_block = render_roster_entries(entries)
    items = tuple(
        SupplyItem(item_id=f"{arm}-{index:03d}", text=f"{entry_type}={value}")
        for index, (entry_type, value) in enumerate(entries)
    )
    return SupplyPacket(
        form=SupplyForm.ROSTER,
        dose=SupplyDose(n_items=len(entries), token_count=len(prompt_block.split())),
        prompt_block=prompt_block,
        assembly_template_id=f"pslu-{arm}-roster-v1",
        items=items,
    ).validate()


def _type_vocabulary_packet(arm: str, types: Sequence[str]) -> SupplyPacket:
    prompt_block = render_type_vocabulary(types)
    items = tuple(SupplyItem(item_id=f"{arm}-{index:03d}", text=t) for index, t in enumerate(types))
    return SupplyPacket(
        form=SupplyForm.ROSTER,
        dose=SupplyDose(n_items=len(types), token_count=len(prompt_block.split())),
        prompt_block=prompt_block,
        assembly_template_id=f"pslu-{arm}-roster-v1",
        items=items,
    ).validate()


def pslu_supply_packet(
    arm: str, *, scenario: str | None, rosters: PsluRosters
) -> SupplyPacket | None:
    """One arm's ``SupplyPacket`` (or ``None`` for A0's zero-supply). Module
    docstring covers the roster-selection rule per arm; ``scenario`` is the
    GOLD scenario for A1/A4 (documented, gold-scoped-by-design arms) and the
    PHASE-1 PREDICTED scenario (``None`` if unparsed/unknown) for A1'."""

    if arm == PSLU_PHASE1_ARM:
        return None
    if arm == "A1":
        if scenario is None:
            raise PsluFlightError("A1 requires the sample's own gold scenario")
        entries = rosters.scenario_rosters.get(scenario)
        if entries is None:
            raise PsluFlightError(f"no A1 roster for scenario {scenario!r}")
        return _roster_packet(arm, entries)
    if arm == "A1p":
        entries = rosters.scenario_rosters.get(scenario) if scenario is not None else None
        if entries is None:
            # Module docstring: an unparsed/unknown phase-1 prediction falls
            # back to the scenario-agnostic A2 roster -- NEVER to gold.
            return _type_vocabulary_packet("A1p-fallback-A2", rosters.global_types)
        return _roster_packet(arm, entries)
    if arm == "A2":
        return _type_vocabulary_packet(arm, rosters.global_types)
    if arm == "A3":
        return _roster_packet(arm, rosters.full_roster)
    if arm == "A4":
        if scenario is None:
            raise PsluFlightError("A4 requires the sample's own gold scenario for its derangement key")
        deranged_scenario = rosters.derangement.get(scenario)
        if deranged_scenario is None:
            raise PsluFlightError(f"no A4 derangement mapping for scenario {scenario!r}")
        entries = rosters.scenario_rosters.get(deranged_scenario)
        if entries is None:
            raise PsluFlightError(f"no A1 roster for deranged scenario {deranged_scenario!r}")
        return _roster_packet(arm, entries)
    raise PsluFlightError(f"unknown P-SLU arm {arm!r}; known arms are {PSLU_ARMS}")


# ---------------------------------------------------------------------------
# Flight orchestration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PsluArmResult:
    arm: str
    sample_id: str
    messages: tuple[Mapping[str, object], ...]
    response_text: str
    metrics: Mapping[str, object]
    consumption: ConsumptionTrace
    silence_swapped: bool = False
    # Only meaningful on an "A0" row: whether parse_slu_response actually
    # parsed a scenario out of that row's own response (phase 1's own
    # signal for A1''s roster selection). None for every other arm.
    phase1_scenario_parsed: bool | None = None


@dataclass(frozen=True)
class PsluFlightSummary:
    results: tuple[PsluArmResult, ...]
    # sample_id -> the phase-1 predicted scenario, or None when phase 1
    # failed to parse one (module docstring's A1' fallback trigger) -- kept
    # on the summary for audit even though A1p's own supply packet already
    # encodes the consequence.
    predicted_scenario_by_sample_id: Mapping[str, str | None]


def _swap_audio_media_relpath(
    messages: Sequence[Mapping[str, object]], media_relpath: str
) -> tuple[Mapping[str, object], ...]:
    """A silence-swap variant of ``messages``: same system+text content,
    audio content part's ``media_relpath`` replaced. Never mutates the
    input."""

    system_message, user_message = messages
    new_content = []
    for part in user_message["content"]:  # type: ignore[union-attr]
        if isinstance(part, Mapping) and part.get("type") == "input_audio":
            new_content.append({**part, "media_relpath": media_relpath})
        else:
            new_content.append(dict(part))
    return (dict(system_message), {"role": "user", "content": new_content})


def run_pslu_flight(
    *,
    adapter: SlurpAdapter,
    core_client,
    samples: Sequence[SlurpSample],
    rosters: PsluRosters,
    decoding_params: Mapping[str, object] | None = None,
    silence_swap_media_relpaths: Mapping[str, str] = MappingProxyType({}),
) -> PsluFlightSummary:
    """Execute the full six-arm P-SLU flight over ``samples`` (module
    docstring: phase 1 = A0, phase 2 = A1/A1'/A2/A3/A4) plus one extra A1'
    request per entry in ``silence_swap_media_relpaths`` (``sample_id ->
    already-registered silent media_relpath`` -- ``rails.silence_swap`` +
    ``FrozenCoreClient.register_slice`` build that registration; this
    function only consumes the resulting mapping, staying generic over any
    ``CoreClient`` implementation, ``MockCoreClient`` included).

    ``core_client`` is duck-typed against ``rails.core_client.CoreClient``
    (not imported/annotated directly, to keep this module's own signature
    free of importing FrozenCoreClient -- the SAME "no forced import"
    discipline ``rails.obs.default_obs_packet`` uses for ``TaskSample``).
    """

    assert_never_calls_ontology_miner()
    if not samples:
        raise PsluFlightError("run_pslu_flight requires at least one sample")
    sample_ids = {sample.sample_id for sample in samples}
    unknown_silence_ids = set(silence_swap_media_relpaths) - sample_ids
    if unknown_silence_ids:
        raise PsluFlightError(
            f"silence_swap_media_relpaths names sample ids outside this flight's own "
            f"samples: {sorted(unknown_silence_ids)}"
        )

    results: list[PsluArmResult] = []
    predicted_scenario_by_sample_id: dict[str, str | None] = {}

    # Phase 1: A0 -- one zero-supply request per sample, doubling as the
    # scenario-prediction source A1' phase 2 reads (module docstring).
    for sample in samples:
        messages = adapter.assemble_prompt(sample, None)
        response_text = core_client.complete(messages, decoding_params=decoding_params)
        predicted_scenario, _predicted_action, _predicted_entities, parsed = parse_slu_response(
            response_text
        )
        predicted_scenario_by_sample_id[sample.sample_id] = predicted_scenario if parsed else None
        metrics = adapter.score(sample, response_text)
        consumption = adapter.extract_consumption(sample, None, response_text)
        results.append(
            PsluArmResult(
                arm=PSLU_PHASE1_ARM,
                sample_id=sample.sample_id,
                messages=tuple(messages),
                response_text=response_text,
                metrics=metrics,
                consumption=consumption,
                phase1_scenario_parsed=parsed,
            )
        )

    # Phase 2: A1, A1', A2, A3, A4 -- plus silence-swap A1' variants.
    for sample in samples:
        for arm in PSLU_PHASE2_ARMS:
            scenario = (
                sample.scenario
                if arm in ("A1", "A4")
                else predicted_scenario_by_sample_id[sample.sample_id]
            )
            supply = pslu_supply_packet(arm, scenario=scenario, rosters=rosters)
            messages = adapter.assemble_prompt(sample, supply)
            response_text = core_client.complete(messages, decoding_params=decoding_params)
            metrics = adapter.score(sample, response_text)
            consumption = adapter.extract_consumption(sample, supply, response_text)
            results.append(
                PsluArmResult(
                    arm=arm,
                    sample_id=sample.sample_id,
                    messages=tuple(messages),
                    response_text=response_text,
                    metrics=metrics,
                    consumption=consumption,
                )
            )
            if arm == "A1p":
                silence_media_relpath = silence_swap_media_relpaths.get(sample.sample_id)
                if silence_media_relpath is not None:
                    silence_messages = _swap_audio_media_relpath(messages, silence_media_relpath)
                    silence_response_text = core_client.complete(
                        silence_messages, decoding_params=decoding_params
                    )
                    silence_metrics = adapter.score(sample, silence_response_text)
                    silence_consumption = adapter.extract_consumption(
                        sample, supply, silence_response_text
                    )
                    results.append(
                        PsluArmResult(
                            arm=arm,
                            sample_id=sample.sample_id,
                            messages=silence_messages,
                            response_text=silence_response_text,
                            metrics=silence_metrics,
                            consumption=silence_consumption,
                            silence_swapped=True,
                        )
                    )

    return PsluFlightSummary(
        results=tuple(results), predicted_scenario_by_sample_id=predicted_scenario_by_sample_id
    )


__all__ = [
    "PSLU_ARMS",
    "PSLU_PHASE1_ARM",
    "PSLU_PHASE2_ARMS",
    "PsluArmResult",
    "PsluFlightError",
    "PsluFlightSummary",
    "PsluRosters",
    "PsluSampleManifest",
    "assert_never_calls_ontology_miner",
    "load_pslu_rosters",
    "load_pslu_sample_manifest",
    "pslu_supply_packet",
    "render_roster_entries",
    "render_type_vocabulary",
    "run_pslu_flight",
    "select_pslu_samples",
]


# Executed at import time (module docstring / assert_never_calls_ontology_miner's
# own docstring): fails LOUD the moment this module is loaded if a future
# edit adds a live reference to the forbidden ontology miner.
assert_never_calls_ontology_miner()
