"""SLURP's carrier hooks for the evidence-consumption module.

Design ``docs/superpowers/specs/2026-09-29-slurp-consumption-module-design.md``
section 2b.1: the module (``rails.consumption_module``) names no carrier and
reaches every carrier fact through ``CarrierHooks``. This file is SLURP's one
hooks file, beside the SLURP runtime adapter (``rails/adapters/
slurp_runtime.py`` is near its line budget, so the hooks get their own file,
the ``slurp_runtime_material.py`` precedent). Resolved by profile name:
``rails.consumption_module.resolve_carrier_hooks("slurp")``.

Migration step 2 (this file): the lock layer, the decision node's supply-seed
path and the flown program ids the compiler needs, plus the design's four
hooks as thin references to where SLURP implements them today. Moving the
SLURP hard-codings behind these hooks (design 2b.4) is migration step 5, not
this file's job; ``delivered_units`` stays ``None`` until then.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence

from ..consumption_module import POLICY_OWNED_KEYS, CarrierHooks

PROFILE = "slurp"

#: The v2.0 lock (decision 169): the null arm of every composed read and the
#: layer the module compiles its components onto (ruling R2).
LOCK_BASELINE_FRAGMENT = "slurp-native-default-plan-lock-baseline-v1"

#: The decision node's first-phase supply seed: the intent-boundary store's
#: Perception ``phase_supply`` object (AGREE and the centroid key write here).
DECISION_SUPPLY_PATH: tuple[str, ...] = (
    "knowledge_stores", "intent-boundaries", "phase_supply", "perception",
)

#: ``(contact ceiling, Solver response_format_id) -> program id`` for the
#: programs SLURP cells already flew: the lock (11, uncited), COMP-1 (11,
#: cited) and E4-1 re-listen (17, uncited). A composition that lands on one of
#: these pairs keeps the flown program id, so its composed bytes are the
#: flown cell's own.
FLOWN_PROGRAMS: Mapping[tuple[int, str | None], str] = {
    (11, None): "phase-native-candidates-review-revise-v1",
    (11, "saea-solver-cited-answer-v1"): "phase-native-candidates-review-revise-cited-v1",
    (17, None): "phase-native-candidates-review-revise-relisten-v1",
}

#: SLURP's delivered-row normaliser (``rails/delivery_normalisers.py``).
DEFAULT_DELIVER_NORMALISER = "saea-deliver-normalise-v3"

_REPO_ROOT = Path(__file__).resolve().parents[4]


def carrier_module_hooks(*, repo_root: Path | None = None) -> CarrierHooks:
    """SLURP's :class:`CarrierHooks`; ``repo_root`` locates the lock fragment."""

    root = _REPO_ROOT if repo_root is None else Path(repo_root)

    def lock_layer() -> Mapping[str, object]:
        from ...core.config import read_fragment  # noqa: PLC0415

        fragment = read_fragment(root, "baseline", LOCK_BASELINE_FRAGMENT)
        return {key: fragment[key] for key in POLICY_OWNED_KEYS}

    def decision_candidates(supplied_value_ids: Sequence[str]) -> tuple[str, ...]:
        from ..perception_presentations import branch_supplied_intent_ids  # noqa: PLC0415

        return branch_supplied_intent_ids(supplied_value_ids)

    def max_decision_candidates() -> int:
        from ..candidate_semantic_supply import DEFAULT_MAX_SLURP_CANDIDATES  # noqa: PLC0415

        return DEFAULT_MAX_SLURP_CANDIDATES

    return CarrierHooks(
        profile=PROFILE,
        lock_layer=lock_layer,
        decision_supply_path=DECISION_SUPPLY_PATH,
        flown_programs=FLOWN_PROGRAMS,
        decision_candidates=decision_candidates,
        max_decision_candidates=max_decision_candidates,
        delivered_units=None,
        default_deliver_normaliser=lambda: DEFAULT_DELIVER_NORMALISER,
    )
