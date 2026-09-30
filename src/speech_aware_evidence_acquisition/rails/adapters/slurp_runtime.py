"""Config-driven SLURP adapter over the shared label-free frozen runtime view."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Mapping

from ...contracts import (
    ExecutionScopeError, FINAL_REPORT_SPLIT_ROLE, require_owner_split_allowance,
)
from ...core.base import TASK_ADAPTERS
from ...core.instructions import resolve_active_task_instruction, resolve_task_instruction
from ...data.slurp_contract_cache import (
    SLURP_LABEL_INVENTORY_FILL,
    SLURP_TASK_CONTRACT_VIEW_LABEL_INVENTORY,
    SLURP_TASK_CONTRACT_VIEW_LEGACY,
    SlurpContractCacheError,
    load_cached_slurp_contract,
    validate_slurp_task_contract_view,
)
from ...reproduction.slurp_scoring import parse_slu_response
from ..obs import AudioRef
from .runtime_view import (
    RuntimeViewError, configured_geometry, load_runtime_view, registered_population_ids,
)
from .slurp import SlurpAdapter, SlurpSample


_REGISTERED_DEV_SPLIT = re.compile(r"DEV-[0-9]+(?:-[A-Za-z0-9]+)*$")


def _allowed_runtime_split(split_id: str) -> bool:
    return split_id in {"devel", "discovery"} or bool(_REGISTERED_DEV_SPLIT.fullmatch(split_id))


def _sample_namespace(sample_id: str) -> str:
    parts = sample_id.split(":")
    if len(parts) < 3 or parts[0] != "slurp":
        raise RuntimeViewError("runtime SLURP view contains a non-SLURP sample")
    return parts[1]


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


def _assert_test_samples(samples, *, split_role: str, admission, label: str) -> None:
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


def _namespace_label(split_id: str) -> str:
    return "non-discovery sample" if split_id == "discovery" else "non-devel sample"


def _assert_sample_namespaces(
    samples, *, split_id: str, split_role: str,
    registered_population_bound: bool, runtime_split_name: str | None,
    test_admission: FinalReportSampleAdmission | None = None,
) -> None:
    namespaces = {_sample_namespace(sample.sample_id) for sample in samples}
    if len(namespaces) != 1:
        raise RuntimeViewError("runtime SLURP view must not mix train and devel samples")
    namespace = next(iter(namespaces))
    if namespace == "devel":
        if not _allowed_runtime_split(split_id):
            raise RuntimeViewError(
                "runtime SLURP devel samples require a discovery/devel or registered DEV split"
            )
        return
    if namespace != "train":
        label = _namespace_label(split_id)
        if namespace == _TEST_NAMESPACE:
            _assert_test_samples(
                samples, split_role=split_role, admission=test_admission, label=label,
            )
            return
        raise RuntimeViewError(f"runtime SLURP view contains a {label}")
    if split_id == "devel" or _REGISTERED_DEV_SPLIT.fullmatch(split_id):
        raise RuntimeViewError("runtime SLURP view contains a non-devel sample")
    if split_role != "discovery":
        raise RuntimeViewError("runtime SLURP TRAIN samples require discovery split role")
    if not registered_population_bound:
        raise RuntimeViewError(
            "runtime SLURP TRAIN samples require an explicit registered population"
        )
    if split_id != "discovery" and split_id != runtime_split_name:
        raise RuntimeViewError(
            "runtime SLURP TRAIN split id must match its registered runtime split"
        )


def roster_samples(
    values, data_root_path, *, limit_sample_ids=None, workers=16, test_admission=None,
):
    """Build only media-scoped samples, retaining the historical wrapper call shape.

    ``test_admission`` is the result of :func:`evaluate_test_sample_admission`;
    a refused admission is raised before any media byte is opened.
    """
    if test_admission is not None and test_admission.refusal is not None:
        _assert_test_samples(
            (), split_role="", admission=test_admission,
            label=_namespace_label(str(values.get("split_id", "devel"))),
        )
    rows = load_runtime_view(values, data_root_path, sample_ids=limit_sample_ids, workers=workers)
    samples = []
    for item in rows:
        sample_id = item["sample_id"]
        _sample_namespace(sample_id)
        parts = sample_id.split(":")
        samples.append(SlurpSample(
            sample_id=sample_id, audio_ref=AudioRef(
                path=item["media_relpath"], sha256=item["audio_sha256"],
            ).validate(), audio_seconds=float(item["audio_seconds"]),
            utterance_id=parts[2], media_relpath=item["media_relpath"],
            scenario="", action="", intent="", entities=(),
        ))
    samples = tuple(samples)
    plan = values.get("execution_plan", {})
    _assert_sample_namespaces(
        samples, split_id=str(values.get("split_id", "devel")),
        split_role=str(plan.get("split_role", "")),
        registered_population_bound=limit_sample_ids is not None,
        runtime_split_name=values.get("split_name"),
        test_admission=test_admission,
    )
    return samples


def _configured_task_contract_view(values: Mapping[str, object]) -> str:
    try:
        view = validate_slurp_task_contract_view(
            values.get("slurp_task_contract_view", SLURP_TASK_CONTRACT_VIEW_LEGACY)
        )
    except SlurpContractCacheError as error:
        raise RuntimeViewError(str(error)) from error
    projected_view = view == SLURP_TASK_CONTRACT_VIEW_LABEL_INVENTORY
    projected_fill = values.get("task_instruction_fill") == SLURP_LABEL_INVENTORY_FILL
    if projected_view != projected_fill:
        raise RuntimeViewError(
            "SLURP projected task contract view and no-example instruction fill "
            "must be selected together"
        )
    if projected_view and (
        values.get("task_instruction_template_active") is not True
        or "task_instruction" in values
    ):
        raise RuntimeViewError(
            "SLURP projected task contract requires its active registered "
            "instruction template and no literal instruction"
        )
    return view


class RuntimeSlurpAdapter(SlurpAdapter):
    """Bind roster, instruction and serving geometry as data on the existing adapter."""

    def __init__(
        self, lock, root, *, repo_root, split_id, samples, instruction_text,
        serving_slots=None, serving_slot_tokens=None, serving_max_tokens=None,
        split_role="", registered_population_bound=False, runtime_split_name=None,
        task_contract_view=SLURP_TASK_CONTRACT_VIEW_LEGACY, test_admission=None,
    ):
        super().__init__(lock, root, repo_root=repo_root)
        self._split_id = split_id
        if not isinstance(instruction_text, str) or not instruction_text:
            raise RuntimeViewError("runtime SLURP requires a config-resolved instruction")
        self._instruction_text = instruction_text
        try:
            self._task_contract_view = validate_slurp_task_contract_view(task_contract_view)
        except SlurpContractCacheError as error:
            raise RuntimeViewError(str(error)) from error
        self._projected_task_contract = None
        if self._task_contract_view == SLURP_TASK_CONTRACT_VIEW_LABEL_INVENTORY:
            self._projected_task_contract = load_cached_slurp_contract(
                lock, root, view=self._task_contract_view
            )
            if self._projected_task_contract not in instruction_text:
                raise RuntimeViewError(
                    "runtime SLURP instruction must contain its projected label inventory"
                )
        self._samples = tuple(samples)
        _assert_sample_namespaces(
            self._samples, split_id=split_id, split_role=split_role,
            registered_population_bound=registered_population_bound,
            runtime_split_name=runtime_split_name, test_admission=test_admission,
        )
        if any(
            sample.scenario or sample.action or sample.intent or sample.entities
            for sample in self._samples
        ):
            raise RuntimeViewError("runtime SLURP samples must contain no gold labels")
        for name, value in (
            ("SERVING_SLOTS", serving_slots), ("SERVING_SLOT_TOKENS", serving_slot_tokens),
            ("SERVING_MAX_TOKENS", serving_max_tokens),
        ):
            if value is not None:
                if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                    raise RuntimeViewError("runtime geometry values must be positive integers")
                setattr(self, name, value)

    def load_split(self, split_id, *, allow_heldout=False, allow_synthetic=False):
        if allow_heldout or allow_synthetic or split_id != self._split_id:
            raise RuntimeViewError("runtime adapter cannot expand its registered split")
        return self._samples

    def instruction(self, sample):
        return self._instruction_text

    def build_task_contract(self, sample, obs):
        if self._projected_task_contract is not None:
            return self._projected_task_contract
        return super().build_task_contract(sample, obs)

    def gold(self, sample):
        raise RuntimeViewError("gold never enters a runtime flight; score the sealed manifest")

    def score(self, sample, response: str) -> Mapping[str, object]:
        _, _, _, parsed = parse_slu_response(response)
        return {
            "sample_id": sample.sample_id, "parsed": parsed, "response_chars": len(response),
            "scored_post_hoc_by": "slurp-slu-official through core.scoring_batch",
        }

    def bind_runtime(self, runtime, values):
        from .slurp_runtime_material import bind_runtime_material
        bind_runtime_material(runtime, values, self._lock, self._root)


def build_runtime_adapter(
    values, lock, data_root, repo_root, *, dataset_fragment, run_id=None,
):
    # Validate the selector before resolving instructions, rosters, or media.
    task_contract_view = _configured_task_contract_view(values)
    # None for every train/devel view; for a slurp:test view, the signed
    # sample's roster or the named refusal (raised before media is opened).
    test_admission = evaluate_test_sample_admission(values, repo_root, run_id)
    instruction = (
        resolve_active_task_instruction(values, repo_root, lock, data_root)
        or resolve_task_instruction(values, repo_root, lock, data_root)
    )
    geometry = configured_geometry(values, defaults=(8, 8192, 64))
    population_ids = registered_population_ids(values, dataset_fragment)
    samples = roster_samples(
        values, data_root,
        limit_sample_ids=population_ids,
        workers=values.get("runtime_view_workers", 8),
        test_admission=test_admission,
    )
    return RuntimeSlurpAdapter(
        lock, data_root, repo_root=repo_root, split_id=str(values["split_id"]),
        samples=samples, instruction_text=instruction,
        serving_slots=geometry["slots"], serving_slot_tokens=geometry["slot_tokens"],
        serving_max_tokens=geometry["max_tokens"],
        split_role=str(values.get("execution_plan", {}).get("split_role", "")),
        registered_population_bound=population_ids is not None,
        runtime_split_name=values.get("split_name"),
        task_contract_view=task_contract_view, test_admission=test_admission,
    )


def register_runtime_adapter():
    if "slurp" not in TASK_ADAPTERS.names():
        TASK_ADAPTERS.register("slurp", build_runtime_adapter)
