"""Admit ``slurp:test`` runtime rows only under a signed final-report owner allowance.

The SLURP runtime adapter (``rails.adapters.slurp_runtime``) refuses every
``slurp:test`` sample unless :func:`evaluate_test_sample_admission` admits the
view; this module holds that decision so the adapter stays within its line
budget. Labels are not handled here: the adapter still strips them and refuses
a label-carrying sample, and ``gold()`` still raises.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Mapping

from ..contracts import (
    ExecutionScopeError, FINAL_REPORT_SPLIT_ROLE, require_owner_split_allowance,
)
from .adapters.runtime_view import RuntimeViewError


# --- The signed test SAMPLE (owner decisions 151 and 202) -------------------
#
# A ``slurp:test:*`` row is refused by default. It is admitted ONLY for the
# roster an authorised owner split allowance names, and only when ALL of the
# following hold (each failure is refused and names its condition):
#
#   (a) the runtime view (dataset fragment) AND the execution plan both carry
#       split role ``final-report``;
#   (b) the composed config pins a committed owner allowance by sha256
#       (``owner_allowance`` = {path, sha256}) whose ``split`` names the view's
#       carrier and split identity, and the view's items recompute to exactly
#       that identity (data.splits convention);
#   (c) the roster receipt the allowance names hashes to the allowance's pin,
#       recomputes to the same identity from its committed item ids, and every
#       selected sample id is one of its members;
#   (d) the flight's run id is one of the allowance's ``permitted_run_ids``.
#
# (b) and (d) are the checks ``contracts.plan.require_owner_split_allowance``
# already makes for a ``final-report`` ExecutionPlan; they are reused, not
# re-implemented, so a successor allowance (for example one adding FIT ids)
# works without a code change once the config pins its bytes. Labels stay
# stripped and a label-carrying sample is still refused by the adapter.

_TEST_NAMESPACE = "test"


@dataclass(frozen=True)
class FinalReportSampleAdmission:
    """The outcome of the final-report test-sample check for one runtime view.

    ``sample_ids`` is the signed roster's membership when every condition
    held; otherwise ``refusal`` names the first condition that failed.
    """

    sample_ids: frozenset[str] | None
    refusal: str | None = None


def _view_namespaces(values: Mapping[str, object]) -> set[str]:
    items = values.get("items")
    if not isinstance(items, list):
        return set()
    namespaces = set()
    for item in items:
        sample_id = item.get("sample_id") if isinstance(item, Mapping) else None
        parts = sample_id.split(":") if isinstance(sample_id, str) else []
        if len(parts) >= 2:
            namespaces.add(parts[1])
    return namespaces


def _identity_of(sample_ids, carrier_lock_key: str) -> str:
    # data.splits.split_identity_hash over data.splits.prefixed ids: sha256
    # over the LF-joined sorted ``<lock_key>/<sample_id>`` strings.
    prefixed = sorted(f"{carrier_lock_key}/{sample_id}" for sample_id in sample_ids)
    return hashlib.sha256("\n".join(prefixed).encode("utf-8")).hexdigest()


def _repo_file(repo_root, relpath: object, what: str) -> Path:
    if not isinstance(relpath, str) or not relpath or "\\" in relpath:
        raise RuntimeViewError(f"{what} path must be a repo-relative POSIX path")
    pure = PurePosixPath(relpath)
    if pure.is_absolute() or ".." in pure.parts:
        raise RuntimeViewError(f"{what} path must be a repo-relative POSIX path")
    return Path(repo_root).joinpath(*pure.parts)


def _require_final_report_test_admission(
    values: Mapping[str, object], repo_root, run_id: str | None,
) -> frozenset[str]:
    plan = values.get("execution_plan") or {}
    if not isinstance(plan, Mapping):
        plan = {}
    # (a) split role on both the view and the plan.
    if values.get("split_role") != FINAL_REPORT_SPLIT_ROLE:
        raise RuntimeViewError(
            f"condition (a): the runtime view's split_role is {values.get('split_role')!r}, "
            f"not {FINAL_REPORT_SPLIT_ROLE!r}"
        )
    if plan.get("split_role") != FINAL_REPORT_SPLIT_ROLE:
        raise RuntimeViewError(
            f"condition (a): the execution plan's split_role is {plan.get('split_role')!r}, "
            f"not {FINAL_REPORT_SPLIT_ROLE!r}"
        )
    # (d) needs the flight's own run id.
    if not isinstance(run_id, str) or not run_id:
        raise RuntimeViewError(
            "condition (d): no flight run id reached the SLURP adapter, so the "
            "allowance's permitted_run_ids cannot be checked"
        )
    carrier = values.get("carrier_lock_key")
    declared_identity = values.get("split_identity_hash")
    population = values.get("population")
    if isinstance(population, Mapping) and "split_identity_hash" in population:
        if population["split_identity_hash"] != declared_identity:
            raise RuntimeViewError(
                "condition (b): the experiment population's split identity differs "
                "from the runtime view's"
            )
    # (b) + (d): the committed allowance, pinned by bytes, authorised, naming
    # this carrier, this split identity and this run id.
    if values.get("owner_allowance") is None:
        raise RuntimeViewError(
            "condition (b): the composed config pins no owner_allowance={path, sha256}"
        )
    try:
        allowance = require_owner_split_allowance(
            run_id=run_id,
            execution_profile=str(plan.get("execution_profile", "")),
            carrier_lock_key=str(carrier),
            split_identity_hash=str(declared_identity),
            owner_allowance=values.get("owner_allowance"),
            source_root=repo_root,
        )
    except ExecutionScopeError as error:
        condition = "(d)" if "permitted_run_ids" in str(error) and "is not in" in str(error) else "(b)"
        raise RuntimeViewError(f"condition {condition}: {error}") from error
    split = allowance["split"]
    signed_identity = split.get("split_identity_hash")
    items = values.get("items") or []
    view_ids = [item.get("sample_id") for item in items if isinstance(item, Mapping)]
    if _identity_of(view_ids, str(carrier)) != signed_identity:
        raise RuntimeViewError(
            "condition (b): the runtime view's items do not recompute to the "
            "allowance's split identity"
        )
    # (c) the signed roster, pinned by the allowance, is the membership.
    roster_path = _repo_file(repo_root, split.get("roster_receipt_relpath"), "roster receipt")
    if isinstance(population, Mapping) and "roster_receipt" in population:
        if population["roster_receipt"] != split.get("roster_receipt_relpath"):
            raise RuntimeViewError(
                "condition (c): the experiment population names a different roster "
                "receipt from the allowance"
            )
    try:
        raw = roster_path.read_bytes()
    except OSError as error:
        raise RuntimeViewError(
            f"condition (c): the allowance's roster receipt is unreadable: {error}"
        ) from error
    if hashlib.sha256(raw).hexdigest() != split.get("roster_receipt_sha256"):
        raise RuntimeViewError(
            "condition (c): the roster receipt does not hash to the allowance's "
            "roster_receipt_sha256"
        )
    try:
        roster = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeViewError(f"condition (c): the roster receipt is not JSON: {error}") from error
    members = [
        item.get("sample_id") for item in roster.get("items", ())
        if isinstance(item, Mapping)
    ] if isinstance(roster, Mapping) else []
    if (
        not isinstance(roster, Mapping)
        or roster.get("split_role") != FINAL_REPORT_SPLIT_ROLE
        or roster.get("split_identity_hash") != signed_identity
        or roster.get("roster_id") != split.get("roster_id")
        or not members
        or any(not isinstance(member, str) or not member for member in members)
        or len(set(members)) != len(members)
        or _identity_of(members, str(carrier)) != signed_identity
    ):
        raise RuntimeViewError(
            "condition (c): the roster receipt is not the signed final-report roster "
            "(role, roster id, identity or recomputed member identity differs)"
        )
    return frozenset(members)


def evaluate_test_sample_admission(
    values: Mapping[str, object], repo_root, run_id: str | None,
) -> FinalReportSampleAdmission | None:
    """``None`` when the view carries no ``slurp:test`` row (train/devel paths
    are untouched); otherwise the admitted roster or the named refusal."""

    if _TEST_NAMESPACE not in _view_namespaces(values):
        return None
    try:
        return FinalReportSampleAdmission(
            _require_final_report_test_admission(values, repo_root, run_id)
        )
    except RuntimeViewError as error:
        return FinalReportSampleAdmission(None, str(error))


def assert_test_samples(samples, *, split_role: str, admission, label: str) -> None:
    if admission is None:
        raise RuntimeViewError(
            f"runtime SLURP view contains a {label} (no final-report test-sample "
            "admission was evaluated)"
        )
    if admission.refusal is not None or admission.sample_ids is None:
        raise RuntimeViewError(
            f"runtime SLURP view contains a {label}; final-report test-sample "
            f"admission refused: {admission.refusal}"
        )
    if split_role != FINAL_REPORT_SPLIT_ROLE:
        raise RuntimeViewError(
            f"runtime SLURP view contains a {label}; final-report test-sample "
            f"admission refused: condition (a): split role {split_role!r}"
        )
    outside = [s.sample_id for s in samples if s.sample_id not in admission.sample_ids]
    if outside:
        raise RuntimeViewError(
            f"runtime SLURP view contains a {label}; final-report test-sample "
            f"admission refused: condition (c): {len(outside)} sample(s) outside "
            "the signed roster"
        )
