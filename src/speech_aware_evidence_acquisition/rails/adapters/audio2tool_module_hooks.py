"""Audio2Tool's carrier hooks for the evidence-consumption module.

Design ``docs/superpowers/specs/2026-09-29-slurp-consumption-module-design.md``
sections 2b.1-2b.3 and 2d (owner decision 196): the module names no carrier
and reaches Audio2Tool only through this file, beside the Audio2Tool runtime
adapter (``audio2tool_runtime.py`` is at its 260-line budget, so the hooks
get their own file -- the ``slurp_module_hooks.py`` precedent). Resolved by
profile name: ``rails.consumption_module.resolve_carrier_hooks("audio2tool")``.

The mapping (design 2b.2): tool selection is the intent analogue, parameter
values are the slot analogue.

* ``lock_layer`` -- Audio2Tool has NO locked system (base lock v3 section 4:
  "the sealed union-4000 comparators ... no new flight in Stage 2"; the
  harness receipt names no Audio2Tool default plan). The module's all-off
  arm is therefore the DIRECT layer of the shared controller:
  ``configs/baseline/a2t-native-system-direct-v1.json``'s policy blocks --
  the direct-only phase program and its one ``phase_material.direct`` entry,
  byte-identical to the sealed direct ``a2t-native-role-direct-union4000-v1``
  and to the A2T-AA passes whose half-width is h_A2T (decision 167). No
  ``lock_versions`` and no ``current_lock``: a block naming a ``lock`` is
  refused here.
* ``decision_candidates`` -- :func:`a2t_decision_candidates`: the first two
  distinct tool names of an Audio2Tool Perception state
  (``rails.a2t_perception_state``, ``candidate_tools`` in action order) or
  of a rendered supply's tool-card value ids
  (``a2t-native-card:<tool>:value``).
* ``max_decision_candidates`` -- ``max_candidates_per_action`` = 4, the value
  every registered Audio2Tool native-role config carries.
* ``delivered_units`` -- :func:`a2t_delivered_units`: the parameter values of
  each delivered action, through the repository scorer's own parser
  (``reproduction.toolcall_scoring.parse_tool_calls_text``).
* ``tool_offer_units`` (design 2d) -- the STRING parameter values only;
  enums and numerics stay with ``a2t-toolcall``'s own grading.
* ``default_deliver_normaliser`` -- ``None``: no Audio2Tool delivered-row
  normaliser is registered (``rails/delivery_normalisers.py``).

``None`` members (no analogue here, so the module refuses the component):
``decision_supply_path`` (no locked layer carries an Audio2Tool Perception
supply seed; the exemplar-vote store of decision 157 is not built),
``perception_branch_frame`` / ``flown_branch_programs`` (the direct program
has no Perception phase and no Audio2Tool Perception branch ever flew),
``delivered_path_admissions``, ``deliver_stages`` (no scope-rule analogue;
design 2b.2: "none today"), ``lock_versions`` / ``current_lock``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Mapping, Sequence

from ..consumption_module import DIRECT_LAYER_KEYS, CarrierHooks, DeliveredUnit

PROFILE = "audio2tool"

#: The all-off arm's layer (no Audio2Tool lock exists; see the module docstring).
LOCK_BASELINE_FRAGMENT = "a2t-native-system-direct-v1"
#: The direct-only phase program: one phase, one contact per row.
DIRECT_PROGRAM = "phase-direct-only-v1"
FLOWN_PROGRAMS: Mapping[tuple[int, str | None], str] = {(1, None): DIRECT_PROGRAM}

#: ``max_candidates_per_action`` of every registered Audio2Tool native-role
#: config (``rails.a2t_perception_state.parse_audio2tool_perception_state``).
MAX_CANDIDATES_PER_ACTION = 4

#: The tool-card value id shape (``rails.knowledge_compile_a2t``:
#: ``a2t-native-card:<tool name>:value``), qualified or not.
_TOOL_CARD_VALUE_ID = re.compile(r"^a2t-native-card:([A-Za-z_][A-Za-z0-9_]*):value$")

#: The design 2b.2 inventory for this carrier, as data (never armable here).
CARRIER_COMPONENTS: Mapping[str, Mapping[str, object]] = {
    "a2t-exemplar-vote-seed": {
        "analogue_of": "agree-vote-seed (decision-node supply seed)",
        "plane": "SUPPLY -> tool shortlist",
        "status": "not built: needs the Audio2Tool exemplar store (owner decision 157)",
        "record": "docs/results/2026-09-27-a2t-earnings-gap-diagnosis.md",
        "armable": False,
    },
    "a2t-org-1-domain-grouping": {
        "analogue_of": "top2-contrast (presentation)",
        "plane": "SUPPLY presentation -> tool shortlist",
        "status": "closed: HARMFUL, official tool accuracy -3.225 pp [-4.30, -2.13] at n = 4,000 (2.0x h_A2T 1.625)",
        "record": "docs/results/2026-09-27-a2t-org-1-reread-against-h-a2t.md",
        "armable": False,
    },
}

_REPO_ROOT = Path(__file__).resolve().parents[4]


def a2t_decision_candidates(supplied: object) -> tuple[str, ...]:
    """The ``decision_candidates`` hook: the first two DISTINCT tool names,
    in order, of either an ``Audio2ToolPerceptionState`` (its actions'
    ``candidate_tools``) or a sequence of supplied value ids whose local id
    has the tool-card value shape. Pure and zero-contact; anything else
    contributes nothing."""

    from ..a2t_perception_state import Audio2ToolPerceptionState  # noqa: PLC0415

    if isinstance(supplied, Audio2ToolPerceptionState):
        names: list[str] = [tool for action in supplied.actions for tool in action.candidate_tools]
    else:
        names = []
        for value_id in supplied if isinstance(supplied, Sequence) and not isinstance(supplied, str) else ():
            if not isinstance(value_id, str):
                continue
            local_id = value_id.partition("::")[2] or value_id
            match = _TOOL_CARD_VALUE_ID.fullmatch(local_id)
            if match is not None:
                names.append(match.group(1))
    seen: list[str] = []
    for name in names:
        if name not in seen:
            seen.append(name)
        if len(seen) == 2:
            break
    return tuple(seen)


def _kind(value: object) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if value is None:
        return "null"
    return "array" if isinstance(value, list) else "object"


def a2t_delivered_units(delivered_text: str) -> tuple[str | None, tuple[DeliveredUnit, ...], bool]:
    """The ``delivered_units`` hook: ``(context label, units, parsed)``.
    The label joins the delivered tool names in action order; each unit is
    one parameter value, ``type`` = ``<action index>:<tool>.<parameter>``,
    ``filler`` = the value (a string as delivered, any other JSON value in
    canonical JSON), ``kind`` = its JSON type. An unparsed answer is
    ``(None, (), False)``."""

    from ...reproduction.toolcall_scoring import parse_tool_calls_text  # noqa: PLC0415

    if not isinstance(delivered_text, str):
        return None, (), False
    calls, parsed = parse_tool_calls_text(delivered_text)
    if not parsed:
        return None, (), False
    units: list[DeliveredUnit] = []
    for action_index, call in enumerate(calls):
        for parameter, value in dict(call.arguments).items():
            filler = value if isinstance(value, str) else json.dumps(
                value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
            )
            units.append(DeliveredUnit(
                type=f"{action_index}:{call.name}.{parameter}", filler=filler,
                index=len(units), kind=_kind(value),
            ))
    return "|".join(call.name for call in calls), tuple(units), True


def a2t_tool_offer_units(delivered_text: str) -> tuple[str | None, tuple[DeliveredUnit, ...], bool]:
    """The ``tool_offer_units`` hook (design 2d): the delivered STRING
    parameter values, re-indexed from 0 -- the indices a model-initiated
    ``verify_span(index)`` offer would name."""

    label, units, parsed = a2t_delivered_units(delivered_text)
    strings = [unit for unit in units if unit.kind == "string"]
    return label, tuple(
        DeliveredUnit(type=unit.type, filler=unit.filler, index=position, kind=unit.kind)
        for position, unit in enumerate(strings)
    ), parsed


def carrier_module_hooks(*, repo_root: Path | None = None) -> CarrierHooks:
    """Audio2Tool's :class:`CarrierHooks`; ``repo_root`` locates the layer."""

    root = _REPO_ROOT if repo_root is None else Path(repo_root)

    def lock_layer() -> Mapping[str, object]:
        from ...core.config import read_fragment  # noqa: PLC0415

        fragment = read_fragment(root, "baseline", LOCK_BASELINE_FRAGMENT)
        return {key: fragment[key] for key in DIRECT_LAYER_KEYS}

    return CarrierHooks(
        profile=PROFILE,
        lock_layer=lock_layer,
        flown_programs=FLOWN_PROGRAMS,
        decision_candidates=a2t_decision_candidates,
        max_decision_candidates=lambda: MAX_CANDIDATES_PER_ACTION,
        delivered_units=a2t_delivered_units,
        roster_pin_paths=(),
        tool_offer_units=a2t_tool_offer_units,
        carrier_components=CARRIER_COMPONENTS,
    )
