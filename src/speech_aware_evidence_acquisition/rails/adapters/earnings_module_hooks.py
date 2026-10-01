"""Earnings-21's carrier hooks for the evidence-consumption module.

Design ``docs/superpowers/specs/2026-09-29-slurp-consumption-module-design.md``
sections 2b.1-2b.3 and 2d (owner decision 196): the module names no carrier
and reaches Earnings-21 + ConEC only through this file, beside the Earnings
runtime adapter. Resolved by profile name
(``rails.consumption_module.resolve_carrier_hooks("earnings")``); the config
lock key ``earnings21-original`` maps to it through
``core.base.CONSUMPTION_MODULE_PROFILES``. Earnings-22 uses its own thin
``earnings22_module_hooks`` profile. Neither this carrier's ConEC sources
nor its component admissions transfer to that profile.

The mapping (design 2b.2): transcription has no closed decision label, so
there is no Perception decision, contrast or forced-candidate analogue.

* ``lock_layer`` -- Earnings has NO locked system: the six-node form flew
  once (item E35) and is NOT admitted (base lock v3 section 4; E39 / E41 are
  four-row form proofs). The records name the DIRECT arm as the comparator
  (E35 read, ``docs/results/2026-09-22-e21-native-window-flightruntime-e35-
  read.md``), so the all-off arm is the DIRECT layer on the full discovery
  roster: ``configs/baseline/e21-native-window-direct-full44-v1.json``'s
  policy blocks (the direct-only program and its one ``phase_material``
  entry, byte-identical to the E35 sub10 and four-row direct arms). No
  ``lock_versions`` / ``current_lock``.
* ``delivered_units`` -- :func:`earnings_delivered_units`: the numeric values
  of the delivered transcript (the ``numeric-value-accuracy-v1`` unit: a
  Whisper-normalised word carrying a digit) and, when the caller passes the
  call's ConEC context terms (runtime evidence, never gold), the entity
  mentions of those terms -- the ConEC entity mirror's unit.
* ``tool_offer_units`` (design 2d; E-C3) -- the numeric values only.
* ``default_deliver_normaliser`` -- ``saea-deliver-earnings-text-v1``, the
  registered Earnings FORM normaliser (text hygiene only). The Whisper
  normaliser is NOT a registered delivery normaliser: it lives inside the
  scorer (``asr-wer-whisper``) and never touches delivered text. A direct
  layer has no deliver node, so the module checks this only against a
  system layer.
* ``carrier_components`` -- ``kc-e1f-repair-supply``, the Solver-repair
  analogue (E-C1): ADMITTED on E21 and REPLICATED (PERSON +3.634), listed as
  a SUPPLY component; never armable until an Earnings system layer is locked
  (decision 187 keeps the GPU on SLURP).

``None`` members (the module refuses the component here):
``decision_supply_path``, ``decision_candidates``,
``max_decision_candidates``, ``perception_branch_frame``,
``flown_branch_programs``, ``delivered_path_admissions`` (no decision label,
no Perception contrast), ``deliver_stages`` (the E-C4 numeric format
convention is unregistered), ``lock_versions`` / ``current_lock``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence

from ..consumption_module import DIRECT_LAYER_KEYS, CarrierHooks, DeliveredUnit

PROFILE = "earnings"

#: The all-off arm's layer: the direct arm the E35 / E41 records compare with,
#: on the full 44-call discovery roster.
LOCK_BASELINE_FRAGMENT = "e21-native-window-direct-full44-v1"
DIRECT_PROGRAM = "phase-direct-only-v1"
FLOWN_PROGRAMS: Mapping[tuple[int, str | None], str] = {(1, None): DIRECT_PROGRAM}
#: The registered Earnings delivery normaliser (``rails.delivery_normalisers``).
DEFAULT_DELIVER_NORMALISER = "saea-deliver-earnings-text-v1"

CARRIER_COMPONENTS: Mapping[str, Mapping[str, object]] = {
    "kc-e1f-repair-supply": {
        "analogue_of": "Solver consumption / USE repair (E-C1)",
        "plane": "SUPPLY -> Solver repair (roster-grounded entity substitution, the ConEC brief)",
        "status": "admitted on E21 (replicated PERSON +3.634)",
        "record": "docs/readiness/2026-09-08-e21-kc-e1f-replication-v1-verdict.md",
        "harness_row": "SAEA-E21-KC-E1F-VERDICT-V2",
        "armable": False,
    },
    "e-c3-numeric-relisten": {
        "analogue_of": "relisten (post-delivery re-listen)",
        "plane": "OBS post-delivery verification",
        "status": "not flown (re-plan v2 row C3)",
        "record": "docs/results/2026-09-27-a2t-earnings-gap-diagnosis.md",
        "armable": False,
    },
}

_REPO_ROOT = Path(__file__).resolve().parents[4]


def _numeric_units(words: Sequence[str]) -> list[DeliveredUnit]:
    from ...reproduction.numeric_value_accuracy import is_numeric_value, numeric_kind  # noqa: PLC0415

    return [
        DeliveredUnit(type="numeric", filler=word, index=0, kind=numeric_kind(word))
        for word in words if is_numeric_value(word)
    ]


def earnings_delivered_units(
    delivered_text: str, *, entity_terms: Sequence[str] = (),
) -> tuple[str | None, tuple[DeliveredUnit, ...], bool]:
    """The ``delivered_units`` hook: ``(None, units, parsed)`` -- there is no
    decision label. Units, in transcript order: every numeric value of the
    Whisper-normalised transcript (``kind`` = its ``numeric_kind``) and every
    occurrence of an ``entity_terms`` term (``type`` ``entity``, ``kind``
    ``entity``), both on the same normalised words. ``parsed`` is ``False``
    only for a non-string or blank delivery."""

    from ...reproduction.numeric_value_accuracy import whisper_words  # noqa: PLC0415

    if not isinstance(delivered_text, str) or not delivered_text.strip():
        return None, (), False
    words = whisper_words(delivered_text)
    positioned: list[tuple[int, DeliveredUnit]] = []
    for position, word in enumerate(words):
        for unit in _numeric_units([word]):
            positioned.append((position, unit))
    for term in dict.fromkeys(t for t in entity_terms if isinstance(t, str) and t.strip()):
        needle = whisper_words(term)
        if not needle:
            continue
        for start in range(len(words) - len(needle) + 1):
            if words[start:start + len(needle)] == needle:
                positioned.append((start, DeliveredUnit(
                    type="entity", filler=" ".join(needle), index=0, kind="entity",
                )))
    positioned.sort(key=lambda item: (item[0], item[1].type))
    return None, tuple(
        DeliveredUnit(type=unit.type, filler=unit.filler, index=index, kind=unit.kind)
        for index, (_position, unit) in enumerate(positioned)
    ), True


def earnings_tool_offer_units(delivered_text: str) -> tuple[str | None, tuple[DeliveredUnit, ...], bool]:
    """The ``tool_offer_units`` hook (design 2d, E-C3's targets): the numeric
    values of the delivered transcript, indexed from 0."""

    return earnings_delivered_units(delivered_text)


def carrier_module_hooks(*, repo_root: Path | None = None) -> CarrierHooks:
    """Earnings-21's :class:`CarrierHooks`; ``repo_root`` locates the layer."""

    root = _REPO_ROOT if repo_root is None else Path(repo_root)

    def lock_layer() -> Mapping[str, object]:
        from ...core.config import read_fragment  # noqa: PLC0415

        fragment = read_fragment(root, "baseline", LOCK_BASELINE_FRAGMENT)
        return {key: fragment[key] for key in DIRECT_LAYER_KEYS}

    return CarrierHooks(
        profile=PROFILE,
        lock_layer=lock_layer,
        flown_programs=FLOWN_PROGRAMS,
        delivered_units=earnings_delivered_units,
        default_deliver_normaliser=lambda: DEFAULT_DELIVER_NORMALISER,
        roster_pin_paths=(),
        tool_offer_units=earnings_tool_offer_units,
        carrier_components=CARRIER_COMPONENTS,
    )
