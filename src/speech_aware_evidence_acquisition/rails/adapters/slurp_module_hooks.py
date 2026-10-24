"""SLURP's carrier hooks for the evidence-consumption module.

Design ``docs/superpowers/specs/2026-09-29-slurp-consumption-module-design.md``
section 2b.1: the module (``rails.consumption_module``) names no carrier and
reaches every carrier fact through ``CarrierHooks``. This file is SLURP's one
hooks file, beside the SLURP runtime adapter (``rails/adapters/
slurp_runtime.py`` is near its line budget, so the hooks get their own file,
the ``slurp_runtime_material.py`` precedent). Resolved by profile name:
``rails.consumption_module.resolve_carrier_hooks("slurp")``.

Migration step 2: the lock layer, the decision node's supply-seed path and
the flown program ids the compiler needs. Migration step 5 (design 2b.4): the
SLURP hard-codings the carrier-agnostic rails used to spell themselves now
live HERE, behind the design's four hooks, and the rails reach them through
``CarrierHooks`` (``rails.consumption_module.carrier_hooks_for_lock_key``):

* ``decision_candidates`` -- :func:`slurp_decision_candidates`, the intent-boundary value-id shape
  ``<store>::intent-boundary:<intent_id>`` (formerly ``perception_presentations.branch_supplied_intent_ids``);
* ``max_decision_candidates`` -- SLURP's candidate-list ceiling (the loader's ``min_candidates`` bound);
* ``delivered_units`` -- :func:`slurp_delivered_units`, the delivered answer's (intent label, entities) through
  ``parse_slu_response`` (re-listen's targeting, live and replayed);
* ``default_deliver_normaliser`` -- the projection v3 deliver node.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence

from ..consumption_module import POLICY_OWNED_KEYS, CarrierHooks
from . import slurp_module_construction, slurp_module_lock_v2_2 as lock_v2_2, slurp_module_lock_v2_3 as lock_v2_3

PROFILE = "slurp"

#: The intent-boundary store's own value id shape (``rails.
#: semantic_knowledge_build.build_intent_boundary_snapshot``, dimension
#: ``"intent-boundary"``): a value id qualified for a composed supply is
#: ``qualify_id(store_id, local_id)`` (``rails.knowledge_stores.qualify_id``)
#: where ``local_id`` is ``"intent-boundary:<intent_id>"``, i.e. the whole
#: qualified id is ``<store_id>::intent-boundary:<intent_id>``.
INTENT_BOUNDARY_LOCAL_PREFIX = "intent-boundary:"

def slurp_decision_candidates(supplied_value_ids: Sequence[str]) -> tuple[str, ...]:
    """The first two DISTINCT candidate intents a supply names, in rendered
    order (the ``decision_candidates`` hook; formerly
    ``perception_presentations.branch_supplied_intent_ids``, byte for byte).

    Pure and zero-contact: it inspects only the qualified value ids the
    caller already resolved, never a snapshot, a store binding or the
    network. A value id that does not carry the intent-boundary store's own
    local-id shape contributes nothing; the shared preamble sentinel
    (``rails.semantic_knowledge_build.SHARED_INTENT_GUIDANCE_VALUE_ID``) names
    no intent and is skipped. Returns at most two ids.
    """

    from ..semantic_knowledge_build import SHARED_INTENT_GUIDANCE_VALUE_ID  # noqa: PLC0415

    seen: list[str] = []
    for value_id in supplied_value_ids:
        if not isinstance(value_id, str):
            continue
        _store_id, separator, local_id = value_id.partition("::")
        if not separator or not local_id.startswith(INTENT_BOUNDARY_LOCAL_PREFIX):
            continue
        if local_id == SHARED_INTENT_GUIDANCE_VALUE_ID:
            continue
        intent_id = local_id[len(INTENT_BOUNDARY_LOCAL_PREFIX):]
        if not intent_id or intent_id in seen:
            continue
        seen.append(intent_id)
        if len(seen) == 2:
            break
    return tuple(seen)

def slurp_max_decision_candidates() -> int:
    """SLURP's candidate-list ceiling (the ``max_decision_candidates`` hook):
    ``rails.candidate_semantic_supply.DEFAULT_MAX_SLURP_CANDIDATES`` (3), the
    value every registered cell's ``phase_material.perception.fill_params.
    max_candidates`` carries. The constant itself stays where it is: that
    file is bound into prepared-supply identity."""

    from ..candidate_semantic_supply import DEFAULT_MAX_SLURP_CANDIDATES  # noqa: PLC0415

    return DEFAULT_MAX_SLURP_CANDIDATES


def slurp_delivered_units(delivered_text: str) -> tuple[str | None, tuple, bool]:
    """The ``delivered_units`` hook: ``(context label, units, parsed)`` of a
    delivered SLURP answer -- the intent label ``<scenario>_<action>`` and the
    entities (``.type``, ``.filler``) that re-listen targets, through the SAME
    parser the official scorer's adapter uses. An unparsed answer is
    ``(None, (), False)``."""

    from ...reproduction.slurp_scoring import parse_slu_response  # noqa: PLC0415

    scenario, action, entities, parsed = parse_slu_response(delivered_text)
    if not parsed:
        return None, (), False
    return f"{scenario}_{action}", tuple(entities), True

#: The v2.0 lock (decision 169): the null arm of every composed read and the
#: layer the module compiles its components onto (ruling R2).
LOCK_BASELINE_FRAGMENT = "slurp-native-default-plan-lock-baseline-v1"

#: Lock versions a block may name in its ``lock`` key (step 6). v2.1 (decision
#: 204, docs/results/2026-09-30-slurp-v2-1-lock-v1.md) = v2.0 with ONE pin moved,
#: the Reviewer template cell G5 flew. No ``lock`` key = v2.0, as before.
LOCK_V2_0, LOCK_V2_1 = "v2.0", "v2.1"
#: The CURRENT lock: v2.2 since owner decision 249 (2026-10-10; v4g delivered gain locked); v2.3 since decisions 263 A / 266-A
#: (2026-10-11; declaration-only: v2.2 + the ace-playbook store at i0, P-ACE-0 byte-identical). The null arm of new cells and the OFF arm.
CURRENT_LOCK = lock_v2_3.LOCK_V2_3
#: ``(relpath under configs/, sha256)``: v2.0 / v2.1 Reviewer templates.
LOCK_V2_0_REVIEWER_TEMPLATE = (
    "probes/slurp_native_role_reviewer_v1.txt",
    "dce206a20d361b221ea146dc4ff274ba5e08ce4ab1bfbfece662dc7da5012417",
)
LOCK_V2_1_REVIEWER_TEMPLATE = (
    "probes/slurp_native_role_reviewer_v1_g5_v1.txt",
    "724a437de1eeb1167d11395ad78605d595e324e682cff552c27cb84caa8cef35",
)
#: ROSTER pins inside the policy blocks (step 6): the sealed per-roster
#: speech-query vectors -- cell identity, never policy.
ROSTER_PIN_PATHS: tuple[tuple[str, ...], ...] = (
    ("knowledge_stores", "intent-boundaries", "phase_supply", "perception", "query_source"),
    ("knowledge_stores", "train-exemplars", "phase_supply", "solver", "query_source"),
)

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

#: ``(branch level, contact ceiling, Solver response_format_id) -> program
#: id`` for the branched programs SLURP cells already flew (the P-SV cells:
#: three Perception branches, level 2 -> ceiling 15; level 1 -> 13).
FLOWN_BRANCH_PROGRAMS: Mapping[tuple[int, int, str | None], str] = {
    (1, 13, None): "phase-native-candidates-review-revise-pbranch3-l1-v1",
    (2, 15, None): "phase-native-candidates-review-revise-pbranch3-l2-v1",
}

#: Where and how Perception columns compile (migration step 4): the frame
#: every flown P-SV branch block shares -- the delivering branch A and its
#: twin T at the lock's 10 supplied items, and the registered fit estimate.
PERCEPTION_BRANCH_FRAME: Mapping[str, object] = {
    "block_path": ("native_episode", "roles", "perception", "branches"),
    "delivering_branch_id": "a-agree",
    "twin_branch_id": "t-twin",
    "max_supplied_items": 10,
    "fit_estimate": {
        "base_prompt_tokens": 2577, "completion_ceiling": 512,
        "slot_tokens": 24576, "tokens_per_supplied_item": 149,
    },
}

#: Where template columns compile (NX E1): the Solver's and the Perception's (level-2) block; arm ``lock`` delivers, ``aa`` is the twin.
TEMPLATE_VARIANT_FRAME: Mapping[str, object] = {"block_path": ("native_episode", "roles", "solver", "template_variants"), "node": "solver", "delivering_arm_id": "lock", "twin_arm_id": "aa"}
PERCEPTION_TEMPLATE_VARIANT_FRAME: Mapping[str, object] = {**TEMPLATE_VARIANT_FRAME, "node": "perception", "block_path": ("native_episode", "roles", "perception", "template_variants")}

#: Ruling R3: ``{component id: admitting record}`` of the Perception components admitted to the delivered path. EMPTY: no column read
#: has nominated one yet, so ``top2-contrast`` / ``forced-candidate-list`` may be ``column`` but never ``on``.
DELIVERED_PATH_ADMISSIONS: Mapping[str, str] = {}

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

    def lock_layer_v2_1() -> Mapping[str, object]:
        """The v2.0 layer with the Reviewer template moved to the G5 bytes --
        fail-closed on either template's bytes."""

        import copy  # noqa: PLC0415
        import hashlib  # noqa: PLC0415

        from ..consumption_module import ConsumptionModuleConfigError  # noqa: PLC0415

        layer = copy.deepcopy(dict(lock_layer()))
        for relpath, sha256 in (LOCK_V2_0_REVIEWER_TEMPLATE, LOCK_V2_1_REVIEWER_TEMPLATE):
            path = root / "configs" / relpath
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != sha256:
                raise ConsumptionModuleConfigError(
                    f"lock {LOCK_V2_1}: configs/{relpath} is missing or does not hash to {sha256}"
                )
        reviewer = layer["phase_material"]["reviewer"]
        if reviewer.get("instruction_template") != LOCK_V2_0_REVIEWER_TEMPLATE[0]:
            raise ConsumptionModuleConfigError(
                f"lock {LOCK_V2_1}: the v2.0 layer's Reviewer template is not "
                f"{LOCK_V2_0_REVIEWER_TEMPLATE[0]!r}"
            )
        reviewer["instruction_template"] = LOCK_V2_1_REVIEWER_TEMPLATE[0]
        return layer

    def lock_layer_v2_2() -> Mapping[str, object]:  # module step 7: v2.1 + the v4g normaliser
        return lock_v2_2.layer_from_v2_1(lock_layer_v2_1())

    def lock_layer_v2_3() -> Mapping[str, object]:  # decision 263 A / 266-A: v2.2 + the ace-playbook store at i0
        return lock_v2_3.layer_from_v2_2(lock_layer_v2_2())

    def deliver_stages() -> Mapping[str, Mapping[str, object]]:
        from .. import delivery_normalisers as dn  # noqa: PLC0415

        return {
            "scope-rule": {
                "compositions": dict(dn.SCOPE_RULE_COMPOSITIONS),
                "params": {
                    "min_pool_occurrences": dn.SCOPE_RULE_MIN_POOL_OCCURRENCES,
                    "untagged_share": dn.SCOPE_RULE_UNTAGGED_SHARE,
                    "table": {"relpath": dn.SCOPE_RULE_TABLE_RELPATH, "sha256": dn.SCOPE_RULE_TABLE_SHA256},
                },
            },
        }

    return CarrierHooks(
        profile=PROFILE,
        lock_layer=lock_layer,
        decision_supply_path=DECISION_SUPPLY_PATH,
        flown_programs=FLOWN_PROGRAMS,
        decision_candidates=slurp_decision_candidates,
        max_decision_candidates=slurp_max_decision_candidates,
        delivered_units=slurp_delivered_units,
        default_deliver_normaliser=lambda: DEFAULT_DELIVER_NORMALISER,
        deliver_stages=deliver_stages(),
        perception_branch_frame=PERCEPTION_BRANCH_FRAME,
        flown_branch_programs=FLOWN_BRANCH_PROGRAMS,
        delivered_path_admissions=DELIVERED_PATH_ADMISSIONS,
        lock_versions={LOCK_V2_0: lock_layer, LOCK_V2_1: lock_layer_v2_1, lock_v2_2.LOCK_V2_2: lock_layer_v2_2,
                       lock_v2_3.LOCK_V2_3: lock_layer_v2_3},
        lock_deliver_normalisers=lock_v2_3.lock_deliver_normalisers(),
        current_lock=CURRENT_LOCK,
        roster_pin_paths=ROSTER_PIN_PATHS, template_variant_frame=TEMPLATE_VARIANT_FRAME,
        perception_template_variant_frame=PERCEPTION_TEMPLATE_VARIANT_FRAME,
        thinking_variant_frame={**PERCEPTION_TEMPLATE_VARIANT_FRAME, "block_path": ("native_episode", "roles", "perception", "thinking_variants"), "delivering_arm_id": "both-on", "twin_arm_id": "both-on-twin"},  # NX-T R1
        supply_variant_frame={**TEMPLATE_VARIANT_FRAME, "block_path": ("native_episode", "roles", "solver", "supply_variants")},  # E-S1
        decoding_variant_frame={**TEMPLATE_VARIANT_FRAME, "block_path": ("native_episode", "roles", "solver", "decoding_variants")},  # NX-T R4
        sampling_variant_frame={**PERCEPTION_TEMPLATE_VARIANT_FRAME, "block_path": ("native_episode", "roles", "perception", "sampling_variants"), "delivering_arm_id": "lock", "twin_arm_id": "aa"},  # decision 338
        construction=slurp_module_construction.construction_hooks(ROSTER_PIN_PATHS),  # the r01c variant (2026-10-12)
    )
