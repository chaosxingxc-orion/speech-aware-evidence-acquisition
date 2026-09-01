"""Registry-semantic successor to Audio2Tool signed-supply memory v1.

V2 appends only deployment-visible registry ``domain``/``category`` pairs
to v1's structural state.  Actions, rewards, grouped folds, exact-cell
memory thresholds, promotion gates, and default action are reused from v1.
The module is model-free and cannot launch a prospective run.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Mapping, Sequence

from ..reproduction.toolcall_scoring import parse_tool_calls_text
from . import training_free_a2t_supply_memory as v1

POLICY_SCHEMA = "saea-a2t-training-free-registry-semantic-memory-policy-v2"
EXPERIMENT_ID = "SAEA-A2T-MF-TFRL-REGISTRY-SEMANTIC-MEMORY-V2"
CANDIDATE_IDS: tuple[str, ...] = (
    "domain-category-coarse-v2",
    "domain-category-detailed-v2",
)
EXPECTED_V1_MEMORY_SHA256 = (
    "a17cef81f1746c2b15f6cf6de235e4a182e4eb57bf749d1198e67767bdf81fd6"
)


def extract_semantic_pairs(
    response_text: str, registry_rows: Sequence[Mapping[str, str]]
) -> tuple[tuple[str, str], ...]:
    """Return sorted unique selected ``(domain, category)`` pairs.

    Tool names are used only to resolve the deployment row and never leave
    this function.  Missing parsing, tools, or metadata share one explicit
    unresolved class; an empty valid call list has its own no-call class.
    """

    registry: dict[str, tuple[str, str] | None] = {}
    for row in registry_rows:
        name = row.get("tool_name")
        if not isinstance(name, str) or not name:
            raise v1.SupplyMemoryError("registry row lacks a non-empty tool_name")
        if name in registry:
            raise v1.SupplyMemoryError(f"registry has duplicate tool_name {name!r}")
        domain = row.get("domain")
        category = row.get("category")
        registry[name] = (
            (domain, category)
            if isinstance(domain, str)
            and domain
            and isinstance(category, str)
            and category
            else None
        )

    calls, parsed = parse_tool_calls_text(response_text)
    if not parsed:
        return (("unresolved", "unresolved"),)
    if not calls:
        return (("no-call", "no-call"),)
    pairs: set[tuple[str, str]] = set()
    for call in calls:
        pair = registry.get(call.name)
        if pair is None:
            pairs.add(("unresolved", "unresolved"))
        else:
            pairs.add(pair)
    return tuple(sorted(pairs))


@dataclass(frozen=True)
class SemanticRuntimeState:
    base: v1.RuntimeState
    semantic_pairs: tuple[tuple[str, str], ...]

    def key(self, candidate_id: str) -> tuple[str, ...]:
        semantic = tuple(f"{domain}/{category}" for domain, category in self.semantic_pairs)
        if candidate_id == "domain-category-coarse-v2":
            return self.base.key("coarse-v1") + semantic
        if candidate_id == "domain-category-detailed-v2":
            return self.base.key("detailed-v1") + semantic
        raise v1.SupplyMemoryError(f"unknown candidate id {candidate_id!r}")


@dataclass(frozen=True)
class SemanticSignedSupplyOutcome:
    sample_id: str
    group_id: str
    state: SemanticRuntimeState
    stop_exact: int
    supply_exact: int
    stop_tool_accuracy: float
    supply_tool_accuracy: float
    stop_slot_f1: float
    supply_slot_f1: float

    @property
    def delta(self) -> int:
        return self.supply_exact - self.stop_exact


def augment_outcomes(
    outcomes: Sequence[v1.SignedSupplyOutcome],
    direct_response_by_id: Mapping[str, str],
    registry_rows: Sequence[Mapping[str, str]],
) -> tuple[SemanticSignedSupplyOutcome, ...]:
    """Append semantic state while preserving every v1 identity/reward."""

    augmented: list[SemanticSignedSupplyOutcome] = []
    for item in sorted(outcomes, key=lambda value: value.sample_id):
        response = direct_response_by_id.get(item.sample_id)
        if response is None:
            raise v1.SupplyMemoryError(
                f"v2 lacks the original A0 response for {item.sample_id!r}"
            )
        augmented.append(
            SemanticSignedSupplyOutcome(
                sample_id=item.sample_id,
                group_id=item.group_id,
                state=SemanticRuntimeState(
                    base=item.state,
                    semantic_pairs=extract_semantic_pairs(response, registry_rows),
                ),
                stop_exact=item.stop_exact,
                supply_exact=item.supply_exact,
                stop_tool_accuracy=item.stop_tool_accuracy,
                supply_tool_accuracy=item.supply_tool_accuracy,
                stop_slot_f1=item.stop_slot_f1,
                supply_slot_f1=item.supply_slot_f1,
            )
        )
    return tuple(augmented)


def screen_candidates(
    outcomes: Sequence[SemanticSignedSupplyOutcome],
    *,
    seed: int = 20260901,
    n_folds: int = 5,
    n_replicates: int = 10_000,
) -> v1.ScreenResult:
    """Apply v1's evaluator and unchanged gates to both semantic states."""

    ordered = tuple(sorted(outcomes, key=lambda item: item.sample_id))
    if not ordered:
        raise v1.SupplyMemoryError("semantic candidate screen requires outcomes")
    reports = {
        candidate_id: v1._evaluate_candidate(  # noqa: SLF001 - v2 reuses the frozen evaluator
            ordered,
            candidate_id=candidate_id,
            seed=seed,
            n_folds=n_folds,
            n_replicates=n_replicates,
        )
        for candidate_id in CANDIDATE_IDS
    }
    eligible = [report for report in reports.values() if report.promotion_passed]
    if not eligible:
        return v1.ScreenResult(reports, None, False)
    selected = sorted(
        eligible,
        key=lambda report: (
            -report.metrics.net_gain,
            -report.metrics.saved,
            report.metrics.supplied,
            report.candidate_id,
        ),
    )[0]
    return v1.ScreenResult(reports, selected.candidate_id, True)


def v1_surface_memory_digest(surface: v1.LoggedSurface) -> str:
    lines = [
        json.dumps(
            {
                "sample_id": item.sample_id,
                "group_id": item.group_id,
                "state": asdict(item.state),
                "stop_exact": item.stop_exact,
                "supply_exact": item.supply_exact,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        for item in surface.outcomes
    ]
    return v1._identity_digest(lines)  # noqa: SLF001 - exact v1 artifact primitive


def assert_v1_surface_identity(
    surface: v1.LoggedSurface, v1_artifact: Mapping[str, object]
) -> None:
    artifact_surface = v1_artifact.get("surface")
    if not isinstance(artifact_surface, Mapping):
        raise v1.SupplyMemoryError("v1 artifact lacks surface identity")
    recorded = artifact_surface.get("memory_sha256")
    measured = v1_surface_memory_digest(surface)
    if recorded != measured or recorded != EXPECTED_V1_MEMORY_SHA256:
        raise v1.SupplyMemoryError(
            f"v1 memory identity drift: recorded={recorded!r}, measured={measured!r}"
        )


def _candidate_payload(
    report: v1.CandidateReport,
    outcomes: Sequence[SemanticSignedSupplyOutcome],
) -> dict[str, object]:
    payload = v1._candidate_payload(  # noqa: SLF001 - identical artifact fields
        report, outcomes
    )
    full_cells = payload.pop("full_surface_return_cells")
    state_counts = payload.pop("state_class_counts")
    assert isinstance(full_cells, Mapping)
    assert isinstance(state_counts, Mapping)
    non_neutral = {
        key: value
        for key, value in full_cells.items()
        if isinstance(value, Mapping)
        and (int(value.get("saves", 0)) > 0 or int(value.get("harms", 0)) > 0)
    }
    supports = [int(value["n"]) for value in full_cells.values()]
    payload["non_neutral_return_cells"] = non_neutral
    payload["state_support_summary"] = {
        "state_class_count": len(full_cells),
        "zero_return_state_count": len(full_cells) - len(non_neutral),
        "minimum_support": min(supports),
        "maximum_support": max(supports),
        "classes_at_memory_support_minimum": sum(
            support >= v1.MIN_CELL_SUPPORT for support in supports
        ),
    }
    dominant = max((int(value) for value in state_counts.values()), default=0)
    payload["state_class_summary"] = {
        "live_class_count": len(state_counts),
        "dominant_class_count": dominant,
        "dominant_class_share": dominant / len(outcomes),
        "counts_sha256": v1._identity_digest(  # noqa: SLF001
            [f"{key}\t{value}" for key, value in state_counts.items()]
        ),
    }
    return payload


def build_policy_artifact(
    outcomes: Sequence[SemanticSignedSupplyOutcome],
    screen: v1.ScreenResult,
    *,
    offline_attempts: int,
    source_hashes: Mapping[str, str] | None = None,
) -> dict[str, object]:
    reports = {
        candidate_id: _candidate_payload(report, outcomes)
        for candidate_id, report in sorted(screen.reports.items())
    }
    selected = (
        None if screen.selected_candidate is None else reports[screen.selected_candidate]
    )
    state_digest = v1._identity_digest(  # noqa: SLF001 - shared digest convention
        [
            json.dumps(
                {
                    "sample_id": item.sample_id,
                    "state": {
                        "base": asdict(item.state.base),
                        "semantic_pairs": item.state.semantic_pairs,
                    },
                    "stop_exact": item.stop_exact,
                    "supply_exact": item.supply_exact,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
            for item in outcomes
        ]
    )
    folds = v1.assign_folds(outcomes, seed=20260901, n_folds=5)
    fold_identity = [
        v1._identity_digest(  # noqa: SLF001 - shared digest convention
            [item.sample_id for item in fold]
        )
        for fold in folds
    ]
    return v1.with_self_hash(
        {
            "schema": POLICY_SCHEMA,
            "experiment_id": EXPERIMENT_ID,
            "execution_profile": "model-free-check",
            "claim_status": "fully adaptive retrospective discovery only",
            "predecessor": {
                "experiment_id": v1.EXPERIMENT_ID,
                "artifact_self_sha256": "99c19db3f1adfde2c86b6c9ebfc4c18fc3dc58fe2ccfde22a78c679a408ca7c6",
                "v1_memory_sha256": EXPECTED_V1_MEMORY_SHA256,
                "v1_decision": "STOP_DIRECT on 217 of 217",
            },
            "state_contract": "v1 structural state plus selected registry domain/category pairs",
            "policy": {
                "default_action": v1.STOP_DIRECT,
                "minimum_cell_support": v1.MIN_CELL_SUPPORT,
                "minimum_cell_saves": v1.MIN_CELL_SAVES,
                "maximum_cell_harms": v1.MAX_CELL_HARMS,
                "parameter_training": "none",
            },
            "semantic_state_sha256": state_digest,
            "fold_identity_sha256": fold_identity,
            "candidate_reports": reports,
            "selected_candidate": screen.selected_candidate,
            "selected": selected,
            "promotion_passed": screen.promotion_passed,
            "static_surface_terminal_rule": (
                "failure closes categorical and threshold search on this 217-row surface"
            ),
            "offline_guard": {
                "outbound_connection_attempts": offline_attempts,
                "targets": [],
            },
            "source_hashes": dict(sorted((source_hashes or {}).items())),
        }
    )


def assert_policy_admits_prospective(document: Mapping[str, object]) -> None:
    if document.get("schema") != POLICY_SCHEMA:
        raise v1.SupplyMemoryError("semantic policy schema mismatch")
    if document.get("promotion_passed") is not True:
        raise v1.SupplyMemoryError("semantic promotion screen did not pass")
    selected = document.get("selected")
    if not isinstance(selected, Mapping):
        raise v1.SupplyMemoryError("semantic policy lacks a selected candidate")
    metrics = selected.get("metrics")
    counts = selected.get("state_class_summary")
    if not isinstance(metrics, Mapping) or int(metrics.get("supplied", 0)) <= 0:
        raise v1.SupplyMemoryError("semantic policy does not change the v1 all-stop decision")
    if int(metrics.get("stopped", 0)) <= 0:
        raise v1.SupplyMemoryError("semantic policy does not exercise both actions")
    if not isinstance(counts, Mapping) or int(counts.get("live_class_count", 0)) < 2:
        raise v1.SupplyMemoryError("semantic policy state is not live")


__all__ = [
    "CANDIDATE_IDS",
    "EXPERIMENT_ID",
    "EXPECTED_V1_MEMORY_SHA256",
    "POLICY_SCHEMA",
    "SemanticRuntimeState",
    "SemanticSignedSupplyOutcome",
    "assert_policy_admits_prospective",
    "assert_v1_surface_identity",
    "augment_outcomes",
    "build_policy_artifact",
    "extract_semantic_pairs",
    "screen_candidates",
    "v1_surface_memory_digest",
]
