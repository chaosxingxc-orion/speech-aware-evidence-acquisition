"""Project verified whole-system events for semantic credit, without task labels."""
from __future__ import annotations

import copy
from collections.abc import Mapping

from ..rails.hashing import content_hash
from .shared_json import restore_json
from .system_wire_context import compact_wire_episode

EVENT_MODE = "recorded-system-events-v1"


def _require(ok, message):
    if not ok:
        raise ValueError(message)


def _index_events(reports, summaries):
    episodes = {}
    for report in reports:
        for episode in report["episodes"]:
            sha = episode["content_sha256"]
            _require(sha not in episodes, "duplicate event source episode")
            _require(content_hash({k: v for k, v in episode.items() if k != "content_sha256"}) == sha,
                     "event source episode content differs")
            episodes[sha] = episode
    indexed = {}
    for summary in summaries:
        for context in summary.prepared_document["contexts"]:
            wire = context["model_context"]["trajectory"]
            sha = wire.get("source_episode_sha256")
            sid = context["source_sample_id"]
            _require(wire.get("schema") == "saea-complete-episode-wire-view-v1",
                     "event evidence requires verified exact wire summaries")
            _require(sha in episodes and sha not in indexed,
                     "event evidence has missing, unknown or duplicate episode")
            episode = episodes[sha]
            row = summary.rows[sid]
            _require(context.get("source_feedback_sha256") == row["episode_sha256"] == sha
                     and episode["trajectory"]["sample_id"] == sid,
                     "event evidence crosses summary or sample binding")
            visible = restore_json(wire["context"])
            contacts = visible["contacts"]
            requests = {c["request_record_id"]: c["request"] for c in contacts}
            _require(len(requests) == len(contacts),
                     "event evidence repeats a model contact")
            # The outer reader independently verifies exact request bodies against
            # original fit receipts; this also binds every response/tool/control
            # byte to the independently reopened complete episode.
            rebuilt = compact_wire_episode(episode, requests)
            _require(visible == restore_json(rebuilt["context"]),
                     "event evidence differs from original complete episode")
            projected = []
            for contact in contacts:
                request = contact["request"]
                _require(isinstance(request, Mapping)
                         and isinstance(request.get("tools", []), list),
                         "advertised tool schemas must be a recorded list")
                projected.append({
                    **{k: copy.deepcopy(v) for k, v in contact.items() if k != "request"},
                    "advertised_tools": copy.deepcopy(request.get("tools", [])),
                    "tool_choice": copy.deepcopy(request.get("tool_choice")),
                })
            indexed[sha] = {
                "schema": "saea-recorded-system-event-evidence-v1",
                "source_episode_sha256": sha,
                "input_group_sha256": visible["input_group_sha256"],
                "contacts": projected,
                **{key: copy.deepcopy(visible[key]) for key in (
                    "actual_tool_records", "timeline_record_ids", "control_receipt",
                    "delivery", "delivered_text")},
            }
    _require(set(indexed) == set(episodes),
             "event evidence must retain the whole source population")
    return indexed


def add_recorded_event_evidence(comparison, reports, summaries):
    """Retain raw summaries and outcomes; add a bound event view for every option.

    Only source-verified callers may enter here. This projection excludes original
    prompt/knowledge bodies and official references. Raw model responses, actual
    tools and complete control/delivery order are retained without interpretation.
    """
    indexed = _index_events(reports, summaries)
    result = copy.deepcopy(comparison)
    wanted = set()
    for group in result["groups"]:
        context = group["model_context"]
        attempts = context["attempts"]
        bindings = group["candidate_bindings"]
        _require(len(attempts) == len(bindings), "event option population differs")
        for attempt, binding in zip(attempts, bindings):
            sha = binding["episode_sha256"]
            _require(attempt["label"] == binding["label"] and sha in indexed
                     and sha not in wanted, "event option identity differs")
            evidence = indexed[sha]
            _require(evidence["input_group_sha256"] == group["input_group_sha256"],
                     "event option speech group differs")
            wanted.add(sha)
            attempt["recorded_system_events"] = copy.deepcopy(evidence)
        context["event_evidence_contract"] = {
            "mode": EVENT_MODE,
            "reading_rule": (
                "Read ordered contacts, actual_tool_records and recorded routes as events. "
                "Advertised tools describe available capabilities, not executed actions. "
                "Role text and summaries are model claims, not proof of tool execution. "
                "An empty actual_tool_records list means no tool event was recorded. "
                "Follow the delivered answer after all revisions and delivery transformations."
            ),
            "feedback_scope": (
                "TP/FP/FN are official word/character entity counts for the final delivered "
                "answer. intent_exact and format_ok are separate terminal channels. These "
                "values do not score an intermediate response, tool or role. Associations "
                "between differing sampled trajectories do not establish isolated causal credit."
            ),
            "projection": (
                "Every recorded response, actual tool event and control/delivery record is "
                "retained. Full original request bodies remain addressable in the sealed "
                "source; only advertised tool schemas and tool_choice are projected here. "
                "No reference transcript, gold answer or intermediate gold judgment is supplied."
            ),
        }
        group["model_context_sha256"] = content_hash(context)
    _require(wanted == set(indexed), "comparison omits event source episodes")
    result["schema"] = "saea-system-semantic-comparison-inputs-v2"
    result["event_evidence"] = EVENT_MODE
    result.pop("content_sha256")
    result["content_sha256"] = content_hash(result)
    return result
