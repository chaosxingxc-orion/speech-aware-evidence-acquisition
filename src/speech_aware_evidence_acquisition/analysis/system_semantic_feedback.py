"""Prepare separate complete-episode and terminal-feedback semantic inputs.

Consume the existing verified-source exports. This pure join rechecks integrity
and correspondence; it does not authenticate arbitrary caller-created reports,
admit learning, contact a model, or replace the upstream semantic update stages.
"""
from __future__ import annotations

import copy
import hashlib
import math
from collections.abc import Mapping

from ..rails.finite_action_policy import official_utility
from ..rails.hashing import content_hash
from .system_rollout_groups import normalized_answer_hash
from .system_semantic_trajectory import tfgrpo_summary_fields

OUTCOME_FIELDS = ("tp", "fp", "fn", "intent_exact", "format_ok")
ELIGIBILITY_RULE = "terminal-outcome-vector-disagreement-v1"


class SemanticFeedbackError(ValueError):
    """Actor episodes and complete official feedback cannot be joined."""


def _require(condition, message):
    if not condition:
        raise SemanticFeedbackError(message)


def _fingerprint(document, field, label):
    _require(isinstance(document, Mapping), f"{label} must be an object")
    unsigned = dict(document)
    claimed = unsigned.pop(field, None)
    _require(claimed == content_hash(unsigned), f"{label} fingerprint differs")


def _identity(source):
    return source["run_id"], source["attempt_id"]


def prepare_semantic_feedback_groups(group_report, semantic_reports):
    """Join every construction group without binary filtering or reference text.

    Obtain group_report through load_group_source/group_complete_system_sources
    and semantic_reports through materialize_semantic_trajectories on the same
    verified native sources. Register real reads before calling this function.
    Fingerprints are integrity bindings, not substitutes for those verifiers.

    Summary fields remain score-free. The separate comparison_feedback channel
    exposes only terminal numeric counts, signed utility, intent and format.
    All groups and all complete episodes remain present. Eligibility marks a
    possible semantic comparison; it is not permission for an updater contact.
    """
    try:
        return _prepare(group_report, tuple(semantic_reports))
    except (KeyError, TypeError, IndexError) as error:
        raise SemanticFeedbackError(f"incomplete semantic-feedback input: {error}") from error


def _prepare(group_report, semantic_reports):
    _fingerprint(group_report, "content_sha256", "complete rollout groups")
    _require(group_report.get("schema") == "saea-complete-system-rollout-groups-v1"
             and group_report.get("scope") == "construction-diagnostic-only"
             and group_report.get("learning_authorized") is False,
             "only verified construction diagnostic groups are supported")
    sources = group_report["sources"]
    _require(len(sources) >= 2 and len(sources) == group_report["group_size"],
             "complete group size differs")
    identities = [_identity(source) for source in sources]
    labels = [source["label"] for source in sources]
    _require(len(set(identities)) == len(sources) and len(set(labels)) == len(sources),
             "source identity or label is duplicated")
    _require(all(source["feedback_role"] == "construction" for source in sources),
             "evaluation feedback cannot enter semantic inputs")
    reference = sources[0]
    for source in sources:
        for field in ("split_identity_hash", "model_fragment", "session_receipt_sha256"):
            _require(source[field] == reference[field], f"group {field} differs")

    groups = group_report["groups"]
    roster = [group["sample_id"] for group in groups]
    _require(roster and len(roster) == len(set(roster)), "group roster is empty or duplicated")
    _require(len(semantic_reports) == len(sources), "semantic source population differs")
    materializations, episode_indexes, rounds = {}, {}, set()
    for report in semantic_reports:
        _fingerprint(report, "content_sha256", "semantic materialization")
        _require(report.get("schema") == "saea-system-semantic-trajectory-materialization-v1"
                 and report.get("learning_authorized") is False,
                 "only score-free complete semantic materializations are supported")
        identity = _identity(report["source"])
        _require(identity in identities and identity not in materializations,
                 "semantic source identity is missing, unknown or duplicated")
        source = sources[identities.index(identity)]
        _require(report["source"]["config_hash"] == source["config_hash"],
                 "semantic source configuration differs")
        episodes = report["episodes"]
        _require(report["sample_ids"] == roster
                 and [e["trajectory"]["sample_id"] for e in episodes] == roster,
                 "semantic episodes do not cover the complete ordered roster")
        index = {}
        for episode in episodes:
            _fingerprint(episode, "content_sha256", "semantic episode")
            trajectory = episode["trajectory"]
            _fingerprint(trajectory, "trajectory_sha256", "complete trajectory")
            _require(_identity(trajectory["source"]) == identity
                     and trajectory["source"]["config_hash"] == source["config_hash"]
                     and episode["split_identity_hash"] == source["split_identity_hash"],
                     "episode source or split differs")
            _require(episode["input_group_sha256"] == content_hash({
                "round_id": episode["round_id"],
                "split_identity_hash": episode["split_identity_hash"],
                "input_sha256": episode["input_sha256"],
            }), "semantic speech grouping identity differs")
            rounds.add(episode["round_id"])
            index[trajectory["sample_id"]] = episode
        materializations[identity] = report
        episode_indexes[identity] = index
    _require(len(rounds) == 1, "semantic inputs mix different construction rounds")
    f0 = group_report["frozen_f0"]
    official_utility(tp=0, fp=0, fn=0, f0=f0)

    prepared, eligible_count = [], 0
    for group in groups:
        sid = group["sample_id"]
        members = group["members"]
        _require([m["source_label"] for m in members] == labels,
                 "group members differ from ordered complete sources")
        summary_inputs, feedback_members, group_hashes = [], [], set()
        source_members = []
        for source, member in zip(sources, members):
            episode = episode_indexes[_identity(source)][sid]
            trajectory = episode["trajectory"]
            _require(member["sample_id"] == sid
                     and member["trajectory_sha256"] == trajectory["trajectory_sha256"]
                     and member["input_sha256"] == episode["input_sha256"] == group["input_sha256"],
                     "feedback belongs to another complete episode or speech input")
            _require(hashlib.sha256(episode["delivered_text"].encode("utf-8")).hexdigest()
                     == trajectory["final_output"]["delivered_text_sha256"],
                     "materialized delivered bytes differ from the bound terminal output")
            _require(member["normalized_answer_sha256"] == normalized_answer_hash(episode["delivered_text"]),
                     "feedback answer differs from the materialized delivery")
            _require(member["action_probability"] is None
                     and member["decision_status"] == "historical-allocation-not-an-optimized-action-decision",
                     "optimized decisions require their registered policy-credit join")
            _require(type(member["intent_exact"]) in (int, float) and member["intent_exact"] in (0, 1),
                     "intent feedback must be numeric zero or one")
            _require(type(member["format_ok"]) is bool, "format feedback must be boolean")
            utility = official_utility(
                tp=member["tp"], fp=member["fp"], fn=member["fn"], f0=f0)
            _require(type(member["utility"]) in (int, float)
                     and math.isfinite(member["utility"]) and member["utility"] == utility,
                     "recorded utility differs from frozen official-count feedback")
            group_hashes.add(episode["input_group_sha256"])
            source_members.append({
                "run_id": source["run_id"], "attempt_id": source["attempt_id"],
                "official_feedback_sha256": source["feedback_sha256"],
                "episode_sha256": episode["content_sha256"],
                "trajectory_sha256": trajectory["trajectory_sha256"],
                "action_sha256": content_hash({
                    "role_visits": trajectory["role_visits"], "tool_events": trajectory["tool_events"],
                    "delivery": trajectory["delivery"]}),
                "response_sha256": trajectory["final_output"]["delivered_text_sha256"],
                "outcome": {field: copy.deepcopy(member[field]) for field in OUTCOME_FIELDS},
            })
            binding = {
                "source_label": source["label"], "run_id": source["run_id"],
                "attempt_id": source["attempt_id"],
                "episode_sha256": episode["content_sha256"],
                "trajectory_sha256": trajectory["trajectory_sha256"],
            }
            summary_inputs.append({
                **binding, "fields": tfgrpo_summary_fields(episode),
            })
            feedback_members.append({
                **binding, **{field: copy.deepcopy(member[field]) for field in OUTCOME_FIELDS},
                "utility": utility,
            })
        _require(len(group_hashes) == 1, "group episodes have different speech/split/round identity")
        differences = [
            field for field in OUTCOME_FIELDS
            if len({member[field] for member in feedback_members}) > 1
        ]
        eligible = bool(differences)
        eligible_count += eligible
        group_hash = next(iter(group_hashes))
        prepared.append({
            "sample_id": sid, "input_group_sha256": group_hash,
            "summary_inputs": summary_inputs,
            "experience_source": {
                "schema": "saea-complete-system-feedback-group-source-v1",
                "sample_id": sid, "input_group_sha256": group_hash,
                "members": source_members, "frozen_f0": f0,
            },
            "comparison_feedback": {
                "input_group_sha256": group_hash,
                "scope": "offline construction; complete delivered system",
                "frozen_f0": f0,
                "utility_definition": "2*TP - frozen_f0*(2*TP + FP + FN)",
                "count_definition": "official combined word/character counts",
                "members": feedback_members,
                "eligibility": {
                    "rule_id": ELIGIBILITY_RULE, "eligible": eligible,
                    "reason": ("terminal-outcome-vector-differs" if eligible
                               else "identical-terminal-outcome-vector"),
                    "differing_fields": differences,
                },
                "interpretation": (
                    "Compare whole-system terminal outcomes; do not manufacture component credit. "
                    "Intent and format remain separate outcomes. Signed utility is neither success "
                    "probability nor pooled-F1 ranking. No reference answer is supplied. Eligibility "
                    "does not authorize a model call, update or runtime feedback exposure."
                ),
            },
        })

    report = {
        "schema": "saea-system-semantic-feedback-inputs-v1",
        "scope": "construction-input-preparation-only", "learning_authorized": False,
        "round_id": next(iter(rounds)),
        "source_group_sha256": group_report["content_sha256"],
        "source_materialization_sha256": [
            materializations[identity]["content_sha256"] for identity in identities],
        "eligibility_rule": ELIGIBILITY_RULE,
        "groups": prepared,
        "summary": {
            "groups": len(groups), "episodes": len(groups) * len(sources),
            "eligible_groups": eligible_count, "ineligible_groups": len(groups) - eligible_count,
        },
        "update_disposition": ("requires-separately-registered-semantic-update" if eligible_count
                               else "no-informative-terminal-groups"),
        "model_contacts_added": 0, "scorer_contacts_added": 0,
        "claim_boundary": (
            "No semantic summary inference, group comparison, experience update, policy sampling "
            "or TF-GRPO reproduction has occurred. Raw feedback is for an offline updater, never "
            "an actor context. All groups are retained; eligibility is prospective and versioned."
        ),
    }
    report["content_sha256"] = content_hash(report)
    return report


def join_recorded_summaries(feedback, summaries):
    """Join actual summaries; keep every group, unusable output and all ties."""
    from .system_summary_source import VerifiedSystemSummaries

    _fingerprint(feedback, "content_sha256", "semantic feedback")
    _require(feedback.get("schema") == "saea-system-semantic-feedback-inputs-v1",
             "semantic feedback schema differs")
    # Display schemas may change; the verified original episode digest still
    # binds its full actor identity and is shared with official terminal feedback.
    episode_identities = {}
    for group in feedback["groups"]:
        for member in group["comparison_feedback"]["members"]:
            digest = member["episode_sha256"]
            key = (*_identity(member), group["sample_id"])
            _require(digest not in episode_identities, "feedback episode identity duplicated")
            episode_identities[digest] = key
    index = {}
    for source in summaries:
        _require(isinstance(source, VerifiedSystemSummaries), "summaries must be source-verified")
        contexts = source.prepared_document["contexts"]
        for context in contexts:
            episode = context["model_context"]["trajectory"]
            sid = context["source_sample_id"]
            if episode.get("schema") == "saea-complete-episode-wire-view-v1":
                episode_sha = episode.get("source_episode_sha256")
                _require(isinstance(episode_sha, str) and episode_sha in episode_identities,
                         "compact summary has an unknown complete episode")
                key = episode_identities[episode_sha]
                _require(key[-1] == sid and context.get("source_feedback_sha256") == episode_sha,
                         "compact summary sample or episode custody differs")
            else:
                episode_sha = episode["content_sha256"]
                key = (*_identity(episode["trajectory"]["source"]), sid)
            _require(key not in index and sid in source.rows, "summary identity duplicated or missing")
            row = source.rows[sid]
            _require(row["episode_sha256"] == episode_sha
                     and row["summary_response_sha256"] == hashlib.sha256(row["summary"].encode()).hexdigest(),
                     "recorded summary episode or content differs")
            index[key] = row
    groups, wanted = [], set()
    for group in feedback["groups"]:
        sid = group["sample_id"]
        comparisons, custody, unusable = [], [], []
        for number, member in enumerate(group["comparison_feedback"]["members"], 1):
            key = (*_identity(member), sid)
            _require(key in index and key not in wanted, "summary member population differs")
            wanted.add(key)
            row = index[key]
            _require(row["episode_sha256"] == member["episode_sha256"],
                     "summary is bound to another complete episode")
            label = f"option-{number}"
            comparisons.append({
                "label": label, "summary": row["summary"], "summary_status": row["status"],
                "terminal_feedback": {field: member[field] for field in (*OUTCOME_FIELDS, "utility")},
            })
            custody.append({"label": label, **member,
                            **{k: v for k, v in row.items() if k not in ("summary", "status")}})
            if row["status"] != "usable":
                unusable.append({"label": label, "status": row["status"]})
        eligible = group["comparison_feedback"]["eligibility"]["eligible"]
        disposition = ("blocked-unusable-summary" if unusable else
                       "ready" if eligible else "no-update-terminal-tie")
        context = {
            "stage": "complete-system-semantic-comparison",
            "question": group["summary_inputs"][0]["fields"]["raw_question"],
            "attempts": comparisons,
            "feedback_definition": {key: group["comparison_feedback"][key] for key in
                                    ("frozen_f0", "utility_definition", "count_definition", "interpretation")},
        }
        groups.append({
            "sample_id": sid, "input_group_sha256": group["input_group_sha256"],
            "eligibility": copy.deepcopy(group["comparison_feedback"]["eligibility"]),
            "disposition": disposition, "unusable_summaries": unusable,
            "model_context": context, "model_context_sha256": content_hash(context),
            "candidate_bindings": custody,
            "experience_source": copy.deepcopy(group["experience_source"]),
        })
    _require(wanted == set(index), "unknown or extra summary episodes")
    report = {
        "schema": "saea-system-semantic-comparison-inputs-v1",
        "source_feedback_sha256": feedback["content_sha256"],
        "round_id": feedback["round_id"], "groups": groups,
        "ready_sample_ids": [g["sample_id"] for g in groups if g["disposition"] == "ready"],
        "model_contacts_added": 0, "scorer_contacts_added": 0,
        "claim_boundary": "Prepared semantic comparison, not an executed update or task gain.",
    }
    report["content_sha256"] = content_hash(report)
    return report
