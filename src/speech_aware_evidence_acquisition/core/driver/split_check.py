"""``run_experiment``'s split<->plan<->config cross-checks (M-2, I-1).

Split out of ``run.py`` (R0 repair refactor stage 2, part C, pure move, no
behaviour change) purely for file size. Loads and independently re-verifies
the frozen split the plan claims to run against -- see each check's own
comment (carried verbatim) for exactly what it closes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from ...contracts import ExecutionPlan
from ..base import CoreError
from ..config import ComposedConfig, protocol_hash
from ..split_receipt import VerifiedSplit, load_verified_split


def _verify_split_for_run(
    composed: ComposedConfig,
    plan: ExecutionPlan,
    lock: Mapping[str, object],
    root: Path,
    repo_root: Path,
) -> VerifiedSplit:
    """Load the frozen split the plan's ``split_identity_hash``/``split_role``
    claim, and cross-check every field ``run_experiment`` must agree on
    before spending any budget. Raises :class:`CoreError` on any mismatch."""

    values = composed.values
    arm = str(values["arm"])
    verified_split = load_verified_split(repo_root, str(values["split_name"]), lock, root)
    split_hash = verified_split.identity_hash
    receipt_split_role = verified_split.split_role
    if plan.split_identity_hash != split_hash:
        raise CoreError(
            "plan split identity hash does not match the frozen splits receipt "
            f"for split {values['split_name']!r}"
        )
    if plan.split_role != receipt_split_role:
        raise CoreError(
            f"plan split role {plan.split_role!r} does not match the frozen splits "
            f"receipt split role {receipt_split_role!r} for split {values['split_name']!r}"
        )
    # M-2 (external-threat-model review): the split RECEIPT's own carrier
    # must agree with the plan's carrier too, not just its hash/role. Today
    # this is masked by the two registered carriers (earnings21-original,
    # earnings22-original) having disjoint id namespaces -- a wrong-carrier
    # split/plan pairing is indirectly caught a few lines below ("split ids
    # missing from the carrier's loaded samples") only because the ids
    # never happen to overlap. That is an accident of today's two loaders,
    # not a guarantee: `conec` is a `speech-aware-core` lock key keyed on
    # Earnings21 ids, so a future conec-aware loader sharing that id space
    # would make the indirect check silently pass on a split verified for
    # a DIFFERENT carrier than the one the plan/config actually name. This
    # check is direct and carrier-name-based, so it holds regardless of
    # whether any two carriers' id spaces happen to overlap.
    if verified_split.carrier_lock_key != plan.carrier_lock_key:
        raise CoreError(
            f"plan carrier_lock_key {plan.carrier_lock_key!r} does not match the "
            f"frozen splits receipt carrier_lock_key {verified_split.carrier_lock_key!r} "
            f"for split {values['split_name']!r} (M-2: a split verified for one carrier "
            "can never authorize a run against another)"
        )
    if str(values["carrier_lock_key"]) != plan.carrier_lock_key:
        raise CoreError(
            f"plan carrier_lock_key {plan.carrier_lock_key!r} does not match the "
            f"composed config carrier {values['carrier_lock_key']!r}"
        )
    expected_protocol = protocol_hash(composed.config_hash, arm, split_hash)
    if plan.protocol_hash != expected_protocol:
        raise CoreError(
            f"plan protocol hash {plan.protocol_hash!r} does not match the composed "
            f"config/arm/split protocol hash {expected_protocol!r}"
        )
    return verified_split
