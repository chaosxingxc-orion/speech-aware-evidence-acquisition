"""Parse declared Reviewer findings without inventing judgments or actions.

This offline contract measures what the Reviewer reports. It does not prove an
issue is correct, an evidence citation was visible, or a tool caused a gain.
Planner retains routing authority and Solver retains task-answer authority.
"""
from __future__ import annotations

from typing import Any

from ..rails.review_findings import (
    REVIEW_FINDINGS_SCHEMA,
    ReviewFindingsError,
    parse_review_findings,
)


def analyze_native_review_findings(source) -> dict[str, Any]:
    """Bind declared findings to each actual Reviewer visit after source release.

    Parse failures remain distinct from a no-issue declaration. No reference,
    answer text or reasoning text is exported. Citations are declared IDs only;
    this table never upgrades them to verified exposure or semantic consumption.
    """
    from collections import Counter
    from collections.abc import Mapping

    from .native_episode_source import VerifiedNativeEpisodeSource
    from .native_role_responses import select_verified_native_role_response

    if not isinstance(source, VerifiedNativeEpisodeSource):
        raise ReviewFindingsError("review analysis requires a verified native source")
    ids = source.sample_ids
    if (not ids or len(ids) != len(set(ids))
            or set(source.phase_results) != set(ids)
            or set(source.output_rows) != set(ids)):
        raise ReviewFindingsError("review analysis requires the exact complete roster")
    rows = []
    for sample_id in ids:
        episode = source.phase_results[sample_id]["native_episode_receipt"]
        visits = episode["role_visits"]
        indices = [i for i, visit in enumerate(visits) if visit["role_id"] == "reviewer"]
        interrupted = episode.get("interrupted_role")
        if isinstance(interrupted, Mapping) and interrupted.get("role_id") == "reviewer":
            indices.append(None)
        if not indices:
            indices = [None]
        for index in indices:
            review = select_verified_native_role_response(
                source, sample_id=sample_id, role_id="reviewer", visit_index=index,
            )
            before = len(visits) if index is None else index
            solver_indices = [
                i for i, visit in enumerate(visits[:before]) if visit["role_id"] == "solver"
            ]
            draft = (
                select_verified_native_role_response(
                    source, sample_id=sample_id, role_id="solver", visit_index=solver_indices[-1],
                ).source_json()
                if solver_indices else None
            )
            planner_index = next(
                (i for i in range(before + 1, len(visits))
                 if visits[i]["role_id"] == "planner"),
                None,
            ) if index is not None else None
            routes = [
                route for route in episode.get("planner_routes", [])
                if planner_index is not None and route["role_visit_index"] == planner_index
            ]
            if len(routes) > 1:
                raise ReviewFindingsError("review visit has ambiguous Planner routing")
            action = routes[0]["action"] if routes else None
            revision_completed = False
            revision_attempted = False
            if planner_index is not None:
                for visit in visits[planner_index + 1:]:
                    if visit["role_id"] in {"reviewer", "planner"}:
                        break
                    if visit["role_id"] == "solver":
                        revision_completed = True
                        revision_attempted = True
                else:
                    if (isinstance(interrupted, Mapping)
                            and interrupted.get("role_id") == "solver"
                            and interrupted.get("execution_receipt", {}).get("contacts")):
                        revision_attempted = True
            parsed = None
            status = review.status
            if status == "completed":
                try:
                    parsed = parse_review_findings(review.response_text)
                except ReviewFindingsError:
                    status = "malformed"
                else:
                    status = "parsed"
            rows.append({
                "sample_id": sample_id,
                "reviewer_source": review.source_json(),
                "reviewed_solver_source": draft,
                "report_status": status,
                "verdict": None if parsed is None else parsed["verdict"],
                "recommendation": None if parsed is None else parsed["recommendation"],
                "finding_dimensions": [] if parsed is None else [
                    finding["dimension"] for finding in parsed["findings"]
                ],
                "declared_evidence_ids": [] if parsed is None else list(dict.fromkeys(
                    evidence_id for finding in parsed["findings"]
                    for evidence_id in finding["evidence_ids"]
                )),
                "has_remaining_uncertainty": None if parsed is None else bool(
                    parsed["remaining_uncertainty"].strip()
                ),
                "planner_visit_index": planner_index,
                "planner_action": action,
                "solver_revision_attempted": revision_attempted,
                "solver_revision_completed": revision_completed,
            })
    return {
        "schema": "saea-native-review-findings-analysis-v1",
        "report_schema": REVIEW_FINDINGS_SCHEMA,
        "source": {
            "run_id": source.plan.run_id,
            "attempt_id": source.plan.attempt_id,
            "config_sha256": source.composed.config_hash,
            "phase_artifact_sha256": source.phase_artifact_sha256,
        },
        "sample_count": len(ids),
        "report_row_count": len(rows),
        "report_status_counts": dict(Counter(row["report_status"] for row in rows)),
        "verdict_counts": dict(Counter(row["verdict"] for row in rows if row["verdict"] is not None)),
        "rows": rows,
        "semantics": (
            "These are source-bound Reviewer declarations, actual Planner routes "
            "and executed revisions. Issue accuracy requires offline draft scoring. "
            "Evidence IDs declare citations; they do not establish visibility, "
            "semantic consumption, independence, or causal benefit."
        ),
    }
