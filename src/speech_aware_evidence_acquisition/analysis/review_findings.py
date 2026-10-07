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

def _strict_slurp_reply(text):
    """Inspect raw task shape without repairing, scoring or changing runtime parsing."""
    import json

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate task key")
            result[key] = value
        return result

    def nonfinite(_value):
        raise ValueError("nonfinite task value")

    try:
        value = json.loads(text, object_pairs_hook=unique, parse_constant=nonfinite)
    except (ValueError, TypeError):
        return False
    return (
        isinstance(value, dict)
        and set(value) == {"scenario", "action", "entities"}
        and all(
            isinstance(value[k], str) and value[k].strip()
            for k in ("scenario", "action")
        )
        and isinstance(value["entities"], list)
        and all(
            isinstance(entity, dict)
            and set(entity) == {"type", "filler"}
            and isinstance(entity["type"], str)
            and bool(entity["type"].strip())
            and isinstance(entity["filler"], str)
            for entity in value["entities"]
        )
    )


def _context_contains(payload, text):
    """Inspect only serialized task instruction/history; visibility is not use."""

    def leaves(value):
        if isinstance(value, str):
            yield value
        elif isinstance(value, dict):
            for child in value.values():
                yield from leaves(child)
        elif isinstance(value, list):
            for child in value:
                yield from leaves(child)

    return any(
        text in leaf
        for field in ("task_instruction", "history")
        for leaf in leaves(payload.get(field))
    )


def validate_review_applicability(source, binding):
    """Bind prospective review applicability to a verified config and its traces.

    Pass exactly schema/config_sha256/review_loop in the registered diagnostic
    recipe. This opt-in does not authorize READ. An omitted binding preserves the
    historical missing-review interpretation. The off profile permits at most one
    Perception and one Solver attempt, including interruptions; missing execution
    remains measurable. Multiple contacts inside one attempt are permitted.
    """
    from collections.abc import Mapping
    from .native_episode_source import VerifiedNativeEpisodeSource

    if (not isinstance(source, VerifiedNativeEpisodeSource)
            or not isinstance(binding, dict)
            or set(binding) != {"schema", "config_sha256", "review_loop"}
            or binding["schema"] != "saea-review-applicability-v1"
            or binding["config_sha256"] != source.composed.config_hash
            or binding["review_loop"] not in ("on", "off")):
        raise ReviewFindingsError("review applicability needs the exact verified configuration")
    episode_config = source.composed.values.get("native_episode", {})
    roles = episode_config.get("roles", {})
    counts = [roles.get(role, {}).get("max_iterations") for role in ("reviewer", "planner")]
    revisions = episode_config.get("max_revisions")
    if any(type(n) is not int or n < 0 for n in [*counts, revisions]):
        raise ReviewFindingsError("review applicability requires explicit iteration and revision limits")
    enabled = all(n > 0 for n in counts)
    expected = "on" if enabled else "off"
    if ((not enabled and (counts != [0, 0] or revisions != 0))
            or binding["review_loop"] != expected
            or episode_config.get("review_loop", expected) != expected):
        raise ReviewFindingsError("review applicability conflicts with configured review execution")
    if not enabled:
        for sid in source.sample_ids:
            episode = source.phase_results[sid]["native_episode_receipt"]
            visits = list(episode["role_visits"])
            interrupted = episode.get("interrupted_role")
            if interrupted is not None:
                if not isinstance(interrupted, Mapping):
                    raise ReviewFindingsError("invalid interrupted role in review-off trace")
                visits.append(interrupted)
            allowed = {"perception", "solver"}
            if (episode.get("planner_routes") or episode.get("reviewer_verdicts")
                    or any(v.get("role_id") not in allowed
                           or v.get("stage", v.get("role_id")) not in allowed for v in visits)
                    or any(sum(v.get("role_id") == role or v.get("stage") == role
                               for v in visits) > 1 for role in allowed)):
                raise ReviewFindingsError("review-off trace exceeds its Perception/Solver-only profile")
        if any(isinstance(record, Mapping) and "use_role_id" in record
               and record["use_role_id"] not in {"perception", "solver"}
               for record in source.bundle.trace_records.values()):
            raise ReviewFindingsError("review-off trace contains a contact outside Perception/Solver")
    return dict(binding)


def analyze_slot_review_episode(source, *, legal_slot_types, review_applicability=None):
    """Describe every raw role reply and actual handoff in a verified native system.

    The caller must qualify and authorize its entire family first. Keep this
    derivative root-only. Slot identifiers refer to the caller's pinned legal
    inventory; no reference answers or raw criticism are exported. Model and
    official scorer contacts are zero. Existing runtime normalizers are unchanged.
    """
    import json
    from collections import Counter
    from .native_episode_source import VerifiedNativeEpisodeSource
    from .native_role_responses import select_verified_native_role_response
    from ..rails.review_handoff import normalize_review_handoff
    from ..rails.hashing import content_hash

    if not isinstance(source, VerifiedNativeEpisodeSource):
        raise ReviewFindingsError("slot analysis requires a verified native source")
    ids = source.sample_ids
    if (
        not ids
        or len(ids) != len(set(ids))
        or set(source.phase_results) != set(ids)
        or set(source.output_rows) != set(ids)
    ):
        raise ReviewFindingsError("slot analysis requires the exact complete roster")
    if (
        not isinstance(legal_slot_types, (tuple, list))
        or not legal_slot_types
        or any(not isinstance(t, str) or not t.strip() for t in legal_slot_types)
        or len(set(legal_slot_types)) != len(legal_slot_types)
    ):
        raise ReviewFindingsError(
            "slot analysis requires an unambiguous legal inventory"
        )
    legal = set(legal_slot_types)
    applicability = (None if review_applicability is None else
                     validate_review_applicability(source, review_applicability))
    review_enabled = applicability is None or applicability["review_loop"] == "on"
    counts, actions, rows = Counter(), Counter(), []
    if applicability is not None:
        counts.update({role + suffix: 0 for role in ("perception", "solver", "reviewer", "planner")
                       for suffix in ("_visits", "_contacts")})
    for sid in ids:
        episode = source.phase_results[sid]["native_episode_receipt"]
        visits = episode["role_visits"]
        row = {"sample_id": sid, "reviews": [], "solver_visits": []}
        for index, visit in enumerate(visits):
            role = visit["role_id"]
            selected = select_verified_native_role_response(
                source, sample_id=sid, role_id=role, visit_index=index
            )
            counts[role + "_visits"] += 1
            if applicability is not None:
                counts[role + "_contacts"] += len(visit["execution_receipt"]["contacts"])
            if role == "solver":
                strict = _strict_slurp_reply(selected.response_text)
                marker = "<tool_call>" in selected.response_text
                counts[
                    "solver_strict_task_json"
                    if strict
                    else "solver_not_strict_task_json"
                ] += 1
                counts["solver_text_tool_markers"] += int(marker)
                row["solver_visits"].append(
                    {
                        "source": selected.source_json(),
                        "strict_task_json": strict,
                        "text_tool_call_marker": marker,
                    }
                )
            if role != "reviewer":
                continue
            normalized = normalize_review_handoff(selected.response_text)
            handoff = json.loads(normalized)
            valid = handoff["status"] == "valid"
            counts["reviews_valid" if valid else "reviews_invalid"] += 1
            findings = handoff["findings"]
            counts["findings"] += len(findings)
            non_slot = sorted(
                {t for f in findings for t in f["slot_types"] if t not in legal}
            )
            counts["findings_with_non_slot_identifiers"] += sum(
                any(t not in legal for t in f["slot_types"]) for f in findings
            )
            planner = next(
                (
                    i
                    for i in range(index + 1, len(visits))
                    if visits[i]["role_id"] == "planner"
                ),
                None,
            )
            routes = [
                r
                for r in episode.get("planner_routes", [])
                if planner is not None and r["role_visit_index"] == planner
            ]
            if len(routes) > 1:
                raise ReviewFindingsError("slot analysis has ambiguous Planner routing")
            visible, planner_source = None, None
            if planner is not None:
                target = select_verified_native_role_response(
                    source, sample_id=sid, role_id="planner", visit_index=planner
                )
                planner_source = target.source_json()
                payload = source.bundle.trace_records[target.request_id + "/request"][
                    "payload"
                ]
                visible = _context_contains(payload, normalized)
                counts["review_handoffs_visible_to_planner"] += int(visible)
                counts["review_handoffs_not_visible_to_planner"] += int(not visible)
            action = routes[0]["action"] if routes else None
            if action is not None:
                actions[action] += 1
            row["reviews"].append(
                {
                    "source": selected.source_json(),
                    "status": handoff["status"],
                    "finding_count": len(findings),
                    "non_slot_identifiers": non_slot,
                    "handoff_in_next_planner_context": visible,
                    "planner_source": planner_source,
                    "planner_action": action,
                }
            )
        if not row["reviews"] and review_enabled:
            missing = select_verified_native_role_response(
                source, sample_id=sid, role_id="reviewer"
            )
            counts["reviews_" + missing.status] += 1
            row["reviews"].append(
                {
                    "source": missing.source_json(),
                    "status": missing.status,
                    "finding_count": None,
                    "planner_action": None,
                }
            )
        if applicability is not None:
            row["review_applicable"] = review_enabled
            interrupted = episode.get("interrupted_role")
            if interrupted is not None:
                selected = select_verified_native_role_response(
                    source, sample_id=sid, role_id=interrupted["role_id"])
                counts[selected.role_id + "_contacts"] += len(interrupted["execution_receipt"]["contacts"])
        solver = row["solver_visits"]
        row["extra_solver_revisions"] = max(0, len(solver) - 1)
        row["first_to_last_solver_text_changed"] = (
            solver[0]["source"]["response_text_sha256"]
            != solver[-1]["source"]["response_text_sha256"]
            if solver
            else None
        )
        counts["extra_solver_revisions"] += row["extra_solver_revisions"]
        counts["first_to_last_solver_text_changed"] += int(
            row["first_to_last_solver_text_changed"] is True
        )
        rows.append(row)
    result = {
        "schema": "saea-slot-review-episode-analysis-v1",
        "sample_count": len(ids),
        "source": {
            "run_id": source.plan.run_id,
            "attempt_id": source.plan.attempt_id,
            "config_sha256": source.composed.config_hash,
            "phase_artifact_sha256": source.phase_artifact_sha256,
        },
        "inventory_sha256": content_hash(list(legal_slot_types)),
        "counts": dict(counts),
        "planner_actions": dict(actions),
        "rows": rows,
        "claims_semantic_consumption": False,
        "claims_causal_node_credit": False,
        "contacts_added": {"model": 0, "scorer": 0},
    }
    if applicability is not None:
        result.update(schema="saea-slot-review-episode-analysis-v2", review_applicability=applicability)
    return result
