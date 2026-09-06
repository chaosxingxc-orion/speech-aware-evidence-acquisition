"""The evolution loop's I/O edge: committed receipts and carrier text in,
``rails.evolution`` value objects out.

``rails.evolution`` holds the decisions and is deliberately pure -- every
function there is a function of already-loaded documents, which is what lets
the offline dry run drive a whole round with no carrier, no lock and no wav.
This module is the other half: it reads the committed rosters, resolves the
construction rows the loop needs from the carrier, and assembles the one
:class:`~rails.evolution.CarrierMaterial` value the steps consume. It makes
no decision of its own and contacts nothing.

Legality, stated where the reading happens. The only rows this module ever
resolves are those a committed ``roster_role == "construction"`` receipt
names -- the loop's exemplar pool and its two folds, all three of which the
Audio2Tool exposure union excludes by design (owner decision 2026-09-05). It
never opens an evaluation roster's query text; the one step of the cell that
does is the decontamination gate inside
``rails.proposer.validate_candidate_artifact``, which is not reached from
here.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping, Sequence

from ..data.audio2tool import AUDIO2TOOL_LOCK_KEY, load_query_rows, load_tool_registry
from ..data.lock import load_lock, umbrella_lock_path
from .evolution import CarrierMaterial, EvolutionError, EvolutionState, LoopConfig, RoundOutcome

#: Which steps need which carrier material. Loading the whole lot for every
#: step would hash every exemplar wav before a selection that reads only
#: score files, so each step declares what it actually reads.
_STEP_NEEDS = {
    "propose": ("registry", "exemplars", "media"),
    "candidates": ("registry",),
    "select": ("fold_a",),
    "confirm": ("fold_b",),
}

#: SLURP's ``"registry"`` is the pair of TRAIN slot schemas -- ``A_0`` as
#: KC-S1b flew it, and the same mining unfloored, which is the only authority
#: for a type's count, its share and its intent's line cap.
_SLURP_LOCK_KEY = "slurp"

__all__ = [
    "load_carrier_material",
    "load_state",
    "read_roster_document",
    "rows_of_target_from_roster",
    "sentinel_rows_from_roster",
    "slurp_candidate_validator",
]


def read_roster_document(repo_root: Path, relpath: str) -> Mapping[str, object]:
    """One committed roster receipt, verified fail-closed."""

    from ..core.roster import RosterError, verify_roster  # noqa: PLC0415

    path = Path(repo_root) / relpath
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise EvolutionError(f"roster receipt unreadable ({path}): {error}") from error
    if not isinstance(document, Mapping):
        raise EvolutionError(f"roster receipt {path} is not a JSON object")
    try:
        verify_roster(document)
    except RosterError as error:
        raise EvolutionError(f"roster receipt {path} is not verifiable: {error}") from error
    return document


def _rows_by_tool(document: Mapping[str, object]) -> dict[str, list[str]]:
    by_tool: dict[str, list[str]] = {}
    for item in document.get("items", ()):
        if not isinstance(item, Mapping):
            raise EvolutionError("fold roster item must be an object")
        by_tool.setdefault(str(item.get("stratum")), []).append(str(item["sample_id"]))
    return by_tool


def rows_of_target_from_roster(
    document: Mapping[str, object],
    targets: Mapping[str, Sequence[str]],
    sentinel_tools: Mapping[str, Sequence[str]] | None = None,
) -> dict[str, tuple[str, ...]]:
    """Each target's REWARD rows of a fold roster.

    A fold roster's targeted rows are stratified by the row's GOLD TOOL
    (the fold receipts' own ``strata`` statement), so a target's rows are
    every item whose stratum is one of that target's tools. Background rows
    are stratified by tier and therefore belong to no target, which is what
    makes them the background.

    ``sentinel_tools`` (owner decision 2026-09-06) names, per target, the
    tools whose rows are HARM SENTINELS: they are flown and reported but they
    are not reward rows, so they are removed here rather than inside the
    selection, which keeps stage one exactly the preregistered count rule on
    exactly the rows a save could ever come from.
    """

    by_tool = _rows_by_tool(document)
    excluded = sentinel_tools or {}
    out: dict[str, tuple[str, ...]] = {}
    for target_id in sorted(targets):
        skip = set(excluded.get(target_id, ()))
        rows: list[str] = []
        for tool in sorted(targets[target_id]):
            if tool in skip:
                continue
            rows.extend(by_tool.get(tool, ()))
        if not rows:
            raise EvolutionError(
                f"target {target_id!r} has no reward row in this fold roster; a target "
                "the fold cannot reward must be dropped before the round, not silently"
            )
        out[target_id] = tuple(sorted(set(rows)))
    return out


def sentinel_rows_from_roster(
    document: Mapping[str, object],
    targets: Mapping[str, Sequence[str]],
    sentinel_tools: Mapping[str, Sequence[str]],
) -> dict[str, dict[str, tuple[str, ...]]]:
    """``target_id -> sentinel tool -> that tool's rows`` of a fold roster.

    A declared sentinel with no row in the fold is an error rather than an
    empty entry: it means the roster and the loop config disagree about which
    tools the draw actually carried, and the sentinel-harms line would then
    quietly report nothing about a tool the proposer is still rewriting.
    """

    by_tool = _rows_by_tool(document)
    out: dict[str, dict[str, tuple[str, ...]]] = {}
    for target_id in sorted(sentinel_tools):
        if target_id not in targets:
            raise EvolutionError(f"sentinel_tools names unknown target {target_id!r}")
        rows = {
            tool: tuple(sorted(set(by_tool.get(tool, ()))))
            for tool in sorted(sentinel_tools[target_id])
        }
        empty = sorted(tool for tool, ids in rows.items() if not ids)
        if empty:
            raise EvolutionError(
                f"target {target_id!r} declares sentinel tool(s) {empty} the fold roster "
                "carries no row for; the roster and the loop config disagree"
            )
        out[target_id] = rows
    return out


def _split_fold_rows(
    document: Mapping[str, object],
    targets: Mapping[str, Sequence[str]],
    sentinel_tools: Mapping[str, Sequence[str]] | None = None,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """``(targeted rows, background rows)``.

    A sentinel row falls to the BACKGROUND, which is the owner's rule: it is
    counted in the confirmation's background bound, never in the targeted
    interval a candidate is accepted on.
    """

    targeted: set[str] = set()
    for rows in rows_of_target_from_roster(document, targets, sentinel_tools).values():
        targeted |= set(rows)
    every = {str(item["sample_id"]) for item in document.get("items", ())}
    return tuple(sorted(targeted)), tuple(sorted(every - targeted))


def load_state(repo_root: Path, config: LoopConfig, round_index: int) -> EvolutionState:
    """``A_{r-1}`` and its history, read from the previous round's receipt.

    Round 1 starts from ``A_0`` -- the empty override mapping, i.e. the
    released compact registry byte for byte -- and every later round reads
    the receipt :func:`rails.evolution.write_round_receipt` sealed, so the
    state a round advances is always the state a receipt records rather than
    something a command line asserted.
    """

    if round_index == 1:
        return EvolutionState(round=0, incumbent_overrides={}).validate()
    path = (
        Path(repo_root)
        / config.receipts_reldir
        / f"evolution-round-{round_index - 1:02d}.json"
    )
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise EvolutionError(
            f"round {round_index} needs round {round_index - 1}'s sealed receipt "
            f"({path}): {error}"
        ) from error
    state = document.get("state")
    if not isinstance(state, Mapping):
        raise EvolutionError(f"{path} carries no state block")
    return EvolutionState(
        round=int(state["round"]),
        incumbent_overrides=dict(state["incumbent_overrides"]),
        history=tuple(
            RoundOutcome(
                round=int(entry["round"]),
                accepted=bool(entry["accepted"]),
                gain_pp=float(entry["gain_pp"]),
                reason=str(entry["reason"]),
                portfolio_sha256=entry.get("portfolio_sha256"),
            )
            for entry in state.get("history", ())
        ),
    ).validate()


def load_carrier_material(
    repo_root: Path,
    config: LoopConfig,
    *,
    step: str,
    lock: Mapping[str, object] | None = None,
    data_root: Path | None = None,
    exemplar_roster_relpath: str | None = None,
    fold_a_roster_relpath: str | None = None,
    fold_b_roster_relpath: str | None = None,
) -> CarrierMaterial:
    """The carrier material one step needs, and nothing more.

    ``step`` selects what is actually read (``_STEP_NEEDS``): the PROPOSE
    step hashes every exemplar recording because the roster it freezes records
    measured media facts, while SELECT and CONFIRM read only committed
    receipts and never touch the carrier at all.

    Two carriers, one loader, dispatched on the loop config's own
    ``carrier_lock_key``: Audio2Tool's material is the tool registry plus
    query/gold-call rows, SLURP's is the pair of TRAIN slot schemas plus
    sentence/gold-entity rows. Everything else -- which rosters, which steps
    read what, how a fold's rows are grouped by stratum -- is shared, which is
    what "the same loop code on a second carrier" has to mean.

    The three roster relpaths default to the ones ``config`` names, so a
    re-freeze (V1 -> V2) is a committed-config change; an explicit argument
    still wins, which is what lets a test drive this against a fixture.
    """

    exemplar_roster_relpath = exemplar_roster_relpath or config.exemplar_roster_relpath
    fold_a_roster_relpath = fold_a_roster_relpath or config.fold_a_roster_relpath
    fold_b_roster_relpath = fold_b_roster_relpath or config.fold_b_roster_relpath

    if step not in _STEP_NEEDS:
        raise EvolutionError(f"unknown step {step!r}")
    needs = _STEP_NEEDS[step]
    resolved_lock = lock if lock is not None else load_lock(umbrella_lock_path(repo_root))
    root = Path(data_root) if data_root is not None else _data_root()
    if config.carrier_lock_key == _SLURP_LOCK_KEY:
        return _slurp_carrier_material(
            repo_root,
            config,
            needs=needs,
            lock=resolved_lock,
            root=root,
            exemplar_roster_relpath=exemplar_roster_relpath,
            fold_a_roster_relpath=fold_a_roster_relpath,
            fold_b_roster_relpath=fold_b_roster_relpath,
        )
    if config.carrier_lock_key != AUDIO2TOOL_LOCK_KEY:
        raise EvolutionError(
            f"this loader serves the {AUDIO2TOOL_LOCK_KEY!r} and {_SLURP_LOCK_KEY!r} "
            f"carriers; the config names {config.carrier_lock_key!r}"
        )

    registry_rows: tuple[Mapping[str, str], ...] = ()
    if "registry" in needs:
        registry_rows = tuple(load_tool_registry(resolved_lock, root))

    exemplar_pool: dict[str, tuple[str, ...]] = {}
    exemplar_rows: Mapping[str, Mapping[str, str]] = {}
    media_facts: Mapping[str, Mapping[str, object]] = {}
    if "exemplars" in needs:
        document = read_roster_document(repo_root, exemplar_roster_relpath)
        wanted = {tool for tools in config.targets.values() for tool in tools}
        pool: dict[str, list[str]] = {tool: [] for tool in sorted(wanted)}
        for item in document.get("items", ()):
            stratum = str(item.get("stratum"))
            if stratum in pool:
                pool[stratum].append(str(item["sample_id"]))
        empty = sorted(tool for tool, rows in pool.items() if not rows)
        if empty:
            raise EvolutionError(
                f"the exemplar roster has no construction row for {empty}; a target "
                "whose tool cannot be exemplified must be dropped before the draw"
            )
        exemplar_pool = {tool: tuple(sorted(rows)) for tool, rows in pool.items()}
        every_id = sorted({sid for rows in exemplar_pool.values() for sid in rows})
        exemplar_rows = load_query_rows(resolved_lock, root, every_id)
        if "media" in needs:
            # MEASURED facts, not ``data.audio2tool.load_media_rows``'s, and the
            # difference is the one the I-4 gate refuses on. That reader returns
            # the manifest's three-decimal ``duration`` cell as ``audio_seconds``
            # and binds a tier-7 row to its LAST chat turn; a D1 media supplement
            # is built from wav HEADERS and refuses a disagreement above 1e-6, so
            # a proposer roster carrying manifest durations can never have a
            # supplement built for it, and its anchors could never pass
            # ``gate.verify_media_identity`` at model-touch time. This is the same
            # function and the same tier-7 rule (the FIRST user turn, which is what
            # the official protocol serves) that the two folds' flight-roster
            # receipts and their supplements were built from, so every EVO-A1
            # media artifact now agrees by construction.
            from ..analysis.a2t_evo_capacity import measured_media_facts  # noqa: PLC0415

            media_facts = measured_media_facts(resolved_lock, root, every_id)

    fold_a_rows_of_target: Mapping[str, tuple[str, ...]] = {}
    fold_a_sentinel_rows: Mapping[str, Mapping[str, tuple[str, ...]]] = {}
    if "fold_a" in needs:
        fold_a = read_roster_document(repo_root, fold_a_roster_relpath)
        fold_a_rows_of_target = rows_of_target_from_roster(
            fold_a, config.targets, config.sentinel_tools
        )
        fold_a_sentinel_rows = sentinel_rows_from_roster(
            fold_a, config.targets, config.sentinel_tools
        )

    fold_b_targeted: tuple[str, ...] = ()
    fold_b_background: tuple[str, ...] = ()
    if "fold_b" in needs:
        fold_b_targeted, fold_b_background = _split_fold_rows(
            read_roster_document(repo_root, fold_b_roster_relpath),
            config.targets,
            config.sentinel_tools,
        )

    return CarrierMaterial(
        registry_rows=registry_rows,
        exemplar_pool=exemplar_pool,
        media_facts=media_facts,
        exemplar_rows=exemplar_rows,
        fold_a_rows_of_target=fold_a_rows_of_target,
        fold_b_targeted_rows=fold_b_targeted,
        fold_b_background_rows=fold_b_background,
        fold_a_sentinel_rows=fold_a_sentinel_rows,
    )


def _slurp_carrier_material(
    repo_root: Path,
    config: LoopConfig,
    *,
    needs: Sequence[str],
    lock: Mapping[str, object],
    root: Path,
    exemplar_roster_relpath: str,
    fold_a_roster_relpath: str,
    fold_b_roster_relpath: str,
) -> CarrierMaterial:
    """EVO-S1's half of :func:`load_carrier_material`.

    Legality, stated where the reading happens. The only rows this branch ever
    resolves are those a committed ``roster_role == "construction"`` receipt
    names, and the one reader that carries SENTENCE TEXT beside gold
    (``data.slurp.load_slurp_train_construction_rows``) can reach no split but
    TRAIN. The evaluation side of the decontamination gate -- the DEV
    sentences -- is opened inside ``rails.proposer
    .validate_slurp_candidate_artifact`` alone and is not reached from here.
    """

    from ..data.slurp import (  # noqa: PLC0415 (heavy carrier import, lazily paid)
        load_slurp_intent_slot_schema,
        load_slurp_train_construction_rows,
    )

    slot_schema = None
    unfloored_schema = None
    entity_type_names: tuple[str, ...] = ()
    if "registry" in needs:
        slot_schema = load_slurp_intent_slot_schema(lock, root)
        unfloored_schema = load_slurp_intent_slot_schema(lock, root, min_share=0.0)
        # A_0's closure, executed rather than transcribed (preregistration
        # section 16 open point 1). The pins live in the committed loop config
        # and are checked against this mining before a candidate is built from
        # it; the receipt file's own sha256 is checked here too, because the
        # document a reviewer opens and the table the loop mines have to be
        # the same artifact.
        pins = config.a_0 or {}
        receipt_relpath = pins.get("receipt_relpath")
        receipt_sha256 = None
        if isinstance(receipt_relpath, str) and receipt_relpath:
            receipt_path = Path(repo_root) / receipt_relpath
            try:
                receipt_sha256 = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
            except OSError as error:
                raise EvolutionError(
                    f"the pinned A_0 receipt is unreadable ({receipt_path}): {error}"
                ) from error
        config.assert_a_0(
            floored=slot_schema,
            unfloored=unfloored_schema,
            receipt_sha256=receipt_sha256,
        )
        entity_type_names = tuple(
            sorted(
                {
                    entity_type
                    for profile in unfloored_schema.intents.values()
                    for entity_type, _count, _share in profile.types
                }
            )
        )

    exemplar_pool: dict[str, tuple[str, ...]] = {}
    exemplar_rows: Mapping[str, Mapping[str, object]] = {}
    media_facts: Mapping[str, Mapping[str, object]] = {}
    if "exemplars" in needs:
        document = read_roster_document(repo_root, exemplar_roster_relpath)
        wanted = {member for members in config.targets.values() for member in members}
        pool: dict[str, list[str]] = {member: [] for member in sorted(wanted)}
        for item in document.get("items", ()):
            stratum = str(item.get("stratum"))
            if stratum in pool:
                pool[stratum].append(str(item["sample_id"]))
        empty = sorted(name for name, rows in pool.items() if not rows)
        if empty:
            raise EvolutionError(
                f"the exemplar roster has no construction row for {empty}; a target "
                "whose stratum cannot be exemplified must be dropped before the draw"
            )
        exemplar_pool = {name: tuple(sorted(rows)) for name, rows in pool.items()}
        every_id = sorted({sid for rows in exemplar_pool.values() for sid in rows})
        exemplar_rows = load_slurp_train_construction_rows(lock, root, every_id)
        if "media" in needs:
            media_facts = {
                sample_id: {
                    "media_relpath": row["media_relpath"],
                    "audio_seconds": row["audio_seconds"],
                    "audio_sha256": row["audio_sha256"],
                }
                for sample_id, row in exemplar_rows.items()
            }

    fold_a_rows_of_target: Mapping[str, tuple[str, ...]] = {}
    if "fold_a" in needs:
        fold_a_rows_of_target = rows_of_target_from_roster(
            read_roster_document(repo_root, fold_a_roster_relpath), config.targets
        )

    fold_b_targeted: tuple[str, ...] = ()
    fold_b_background: tuple[str, ...] = ()
    fold_b_rows_of_target: Mapping[str, tuple[str, ...]] = {}
    if "fold_b" in needs:
        fold_b = read_roster_document(repo_root, fold_b_roster_relpath)
        fold_b_rows_of_target = rows_of_target_from_roster(fold_b, config.targets)
        fold_b_targeted, fold_b_background = _split_fold_rows(fold_b, config.targets)

    return CarrierMaterial(
        registry_rows=(),
        exemplar_pool=exemplar_pool,
        media_facts=media_facts,
        exemplar_rows=exemplar_rows,
        fold_a_rows_of_target=fold_a_rows_of_target,
        fold_b_targeted_rows=fold_b_targeted,
        fold_b_background_rows=fold_b_background,
        slot_schema=slot_schema,
        unfloored_schema=unfloored_schema,
        entity_type_names=entity_type_names,
        fold_b_rows_of_target=fold_b_rows_of_target,
    )


def slurp_candidate_validator(
    repo_root: Path,
    config: LoopConfig,
    carrier: CarrierMaterial,
    state: EvolutionState,
    *,
    token_counter,
    exemplar_texts: Sequence[str] = (),
):
    """EVO-S1's form + decontamination gate, bound to committed artifacts.

    The gate itself lives in ``rails.proposer.validate_slurp_candidate_artifact``
    and this function only resolves its inputs, which is why it belongs here
    rather than in ``rails.evolution``: the incumbent block texts (``A_r``
    rendered through the ONE renderer), ``A_0``'s own 1,008 TRAIN fillers as the
    exempt baseline, and the committed decontamination artifact read through
    ``load_evaluation_ngram_digests``.

    **No devel text is opened.** The evaluation side arrives as the hash-pinned
    6-gram DIGESTS ``SAEA-SLURP-MF-EVO-DECONTAMINATION-V1`` already built and
    committed; that row is the one licensed to read SLURP devel sentences and it
    has spent its licence. ``token_counter`` is the flight's own
    ``/tokenize`` -- ``allow_estimator`` is never passed, so a candidate priced
    any other way is refused.
    """

    from .evolution import _checked_slurp_incumbent, slot_schema_for  # noqa: PLC0415
    from .proposer import (  # noqa: PLC0415
        SERVING_TOKENIZER_ID,
        _slurp_fillers_of,
        load_evaluation_ngram_digests,
        slurp_block_texts,
        validate_slurp_candidate_artifact,
    )

    if config.artifact_family != "slurp-slot-schema":
        raise EvolutionError(
            f"slurp_candidate_validator serves the SLURP artifact family, not "
            f"{config.artifact_family!r}"
        )
    if carrier.slot_schema is None or carrier.unfloored_schema is None:
        raise EvolutionError("the validator needs A_0 and the unfloored TRAIN table")
    declared = dict(config.decontamination or {})
    relpath = declared.get("artifact_relpath")
    if not isinstance(relpath, str) or not relpath:
        raise EvolutionError(
            "the loop config must name its committed decontamination artifact"
        )
    path = Path(repo_root) / relpath
    measured = hashlib.sha256(path.read_bytes()).hexdigest()
    expected = declared.get("artifact_sha256")
    if isinstance(expected, str) and expected and measured != expected:
        raise EvolutionError(
            f"decontamination artifact {relpath} hashes to {measured}, not the "
            f"configured {expected}"
        )
    digests = sorted(load_evaluation_ngram_digests(json.loads(path.read_text(encoding="utf-8"))))

    incumbent = _checked_slurp_incumbent(state.incumbent_overrides, carrier.slot_schema)
    incumbent_blocks = slurp_block_texts(
        slot_schema_for(incumbent, carrier.slot_schema, carrier.unfloored_schema),
        intents=tuple(sorted(incumbent)),
    )
    baseline_fillers = tuple(
        _slurp_fillers_of(dict(_checked_slurp_incumbent({}, carrier.slot_schema)))
    )

    def validate(candidate):
        return validate_slurp_candidate_artifact(
            candidate,
            unfloored=carrier.unfloored_schema,
            base=carrier.slot_schema,
            incumbent_blocks=incumbent_blocks,
            token_counter=token_counter,
            token_counter_id=SERVING_TOKENIZER_ID,
            evaluation_ngram_digests=digests,
            baseline_filler_texts=baseline_fillers,
            exemplar_texts=tuple(str(text) for text in exemplar_texts),
        ).as_json()

    return validate


def _data_root() -> Path:
    from ..data.lock import data_root  # noqa: PLC0415

    return data_root()
