"""Prepare bounded knowledge edits from complete, verified construction systems.

Reuse native source, official feedback, grouping and immutable preparation rails.
This path projects recorded semantic requests; it does not replay speech or
claim that its projection is the literal wire prompt. No scorer is invoked.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from pathlib import Path

from ..analysis.native_episode_source import verify_native_episode_source
from ..analysis.system_feedback import load_system_feedback
from ..analysis.system_rollout_groups import (
    load_group_source,
    group_complete_system_sources,
)
from ..analysis.system_semantic_trajectory import materialize_semantic_trajectories
from ..analysis.system_semantic_feedback import prepare_semantic_feedback_groups
from ..analysis.shared_json import share_json, restore_json
from ..analysis.system_event_view import VIEW_ID, project_system_events
from ..core.preparation import hash_stable_file, prepare_artifact, load_artifact
from .hashing import content_hash
from .prepared_feedback import (
    PreparedFeedbackError,
    _read_pinned_json,
    _resolve_data_path,
    _canonical_context,
    load_verified_prepared_contexts,
)
from .semantic_knowledge_edits import (
    slot_value_edit_contract,
    slot_value_edit_response_format,
)
from .system_group_update_context import _roster
from .system_summary_context import _source_path

SOURCE_SCHEMA = "saea-knowledge-edit-source-v1"
GROUP_SOURCE_SCHEMA = "saea-knowledge-edit-source-v2"
PREPARED_SCHEMA = "saea-prepared-knowledge-edit-v1"
DOCUMENT_SCHEMA = "saea-knowledge-edit-contexts-v1"
KIND = "knowledge-edit-contexts"
REQUEST_FIELDS = (
    "task_instruction",
    "history",
    "supplied_evidence",
    "tool_schemas",
    "decoding_params",
)


def _require(condition, message):
    if not condition:
        raise PreparedFeedbackError(message)


def project_episode(episode):
    """Preserve all role responses/tools, actual supply and semantic request history."""
    _require(
        content_hash({k: v for k, v in episode.items() if k != "content_sha256"})
        == episode["content_sha256"],
        "knowledge episode fingerprint differs",
    )
    pool = episode["content_pool"]
    contacts = []
    for c in episode["contacts"]:
        payload = {k: pool[v] for k, v in c["request_field_refs"].items()}
        wire = c["wire_response"]
        contacts.append(
            {
                **{
                    k: copy.deepcopy(c[k])
                    for k in (
                        "visit_index",
                        "role_id",
                        "stage",
                        "interrupted",
                        "request_record_id",
                        "response_record_id",
                    )
                },
                "recorded_request": {
                    k: copy.deepcopy(payload[k]) for k in REQUEST_FIELDS if k in payload
                },
                "omitted_request_fields": sorted(set(payload) - set(REQUEST_FIELDS)),
                "response_record": copy.deepcopy(pool[c["response_record_ref"]]),
                "wire_response_utf8": None
                if wire is None
                else pool[wire["body_utf8_ref"]],
            }
        )
    return {
        "source_episode_sha256": episode["content_sha256"],
        "contacts": contacts,
        "actual_tool_records": [
            {
                "record_id": t["record_id"],
                "record": copy.deepcopy(pool[t["record_ref"]]),
            }
            for t in episode["tool_records"]
        ],
        **{
            k: copy.deepcopy(episode[k])
            for k in (
                "input_group_sha256",
                "timeline_record_ids",
                "control_receipt",
                "delivered_text",
            )
        },
        "delivery": copy.deepcopy(episode["trajectory"]["delivery"]),
    }


def build_knowledge_edit_contexts(source_pin, *, data_root):
    """Reopen complete actors/scores before any cached context may be consumed."""
    try:
        return _build(source_pin, Path(data_root))
    except (ValueError, KeyError, TypeError, OSError, RuntimeError) as error:
        if isinstance(error, PreparedFeedbackError):
            raise
        raise PreparedFeedbackError(
            f"cannot prepare knowledge edit input: {error}"
        ) from error


def _build(source_pin, data):
    binding, source_sha = _read_pinned_json(
        source_pin, data_root=data, field="knowledge edit source"
    )
    per_input = (
        isinstance(binding, Mapping) and binding.get("schema") == GROUP_SOURCE_SCHEMA
    )
    _require(
        isinstance(binding, Mapping)
        and set(binding)
        == (
            {
                "schema",
                "round_id",
                "frozen_f0",
                "members",
                "construction_roster",
                "proposal_roster",
                "base_authored",
                "edit_contract",
            }
            | ({"context_view", "max_context_bytes"} if per_input else set())
        )
        and binding["schema"] in {SOURCE_SCHEMA, GROUP_SOURCE_SCHEMA},
        "knowledge edit source fields differ",
    )
    if per_input:
        _require(
            binding["context_view"] == VIEW_ID
            and type(binding["max_context_bytes"]) is int
            and binding["max_context_bytes"] > 0,
            "group context view or byte bound differs",
        )
    ancestry, ancestry_sha = _roster(
        binding["construction_roster"], data, "cumulative construction"
    )
    active_ids, active_sha = _roster(
        binding["proposal_roster"], data, "proposal anchor"
    )
    _require(
        (per_input or len(active_ids) == 1) and set(active_ids) <= set(ancestry),
        "construction anchors differ from the declared partition",
    )
    members = binding["members"]
    _require(
        isinstance(members, list) and len(members) >= 2,
        "complete repeated system sources required",
    )
    reports, sources = [], []
    for member in members:
        _require(
            isinstance(member, Mapping)
            and set(member) == {"label", "source_repo_root", "feedback_export"},
            "knowledge member fields differ",
        )
        repo = member["source_repo_root"]
        _require(
            isinstance(repo, str) and Path(repo).is_absolute(),
            "frozen checkout must be absolute",
        )
        feedback, _ = _read_pinned_json(
            member["feedback_export"], data_root=data, field="official feedback"
        )
        actor = feedback["source_bindings"]
        rebuilt = load_system_feedback(
            data_root=data, repo_root=Path(repo), binding=actor
        )
        _require(feedback == rebuilt, "feedback differs from complete official source")
        manifest, manifest_sha = _source_path(actor["manifest"], data, "actor manifest")
        phases, phases_sha = _source_path(actor["phases"], data, "actor phases")
        source = verify_native_episode_source(
            manifest_path=manifest,
            expected_manifest_sha256=manifest_sha,
            phase_artifact_path=phases,
            expected_phase_sha256=phases_sha,
            repo_root=Path(repo),
            data_root=data,
        )
        _require(
            set(source.sample_ids) <= set(ancestry),
            "actor exceeds registered construction ancestry",
        )
        reports.append(
            materialize_semantic_trajectories(source, round_id=binding["round_id"])
        )
        sources.append(
            load_group_source(
                data_root=data,
                feedback_pin=member["feedback_export"],
                label=member["label"],
            )
        )
    grouped = group_complete_system_sources(sources, f0=binding["frozen_f0"])
    joined = prepare_semantic_feedback_groups(grouped, reports)
    base, _ = _read_pinned_json(
        binding["base_authored"], data_root=data, field="base authored rows"
    )
    from ..core.semantic_knowledge_preparation import SOURCE_SCHEMA as AUTHORED_SCHEMA

    _require(
        isinstance(base, Mapping)
        and set(base)
        == {"schema", "builder_policy_id", "source_split_identity_hash", "rows"}
        and base["schema"] == AUTHORED_SCHEMA
        and base["builder_policy_id"] == "saea-authored-slot-contracts-v1",
        "base must be authored slot contracts",
    )
    contract, _ = _read_pinned_json(
        binding["edit_contract"], data_root=data, field="edit contract"
    )
    slots = sorted({row["slot_id"] for row in contract["editable"]})
    fields = sorted({row["field"] for row in contract["editable"]})
    expected = slot_value_edit_contract(
        base["rows"],
        slot_ids=slots,
        fields=fields,
        evidence_groups={f"g{i + 1}": ancestry for i in range(len(joined["groups"]))},
        max_edits=contract["max_edits"],
        max_field_chars=contract["max_field_chars"],
    )
    _require(
        expected == contract,
        "edit contract differs from full groups, base or cumulative ancestry",
    )
    episodes = {e["content_sha256"]: e for r in reports for e in r["episodes"]}
    groups, group_samples = [], {}
    for i, group in enumerate(joined["groups"]):
        group_id = f"g{i + 1}"
        sample_ids = {
            episodes[m["episode_sha256"]]["trajectory"]["sample_id"]
            for m in group["comparison_feedback"]["members"]
        }
        _require(len(sample_ids) == 1, "input group spans different samples")
        group_samples[group_id] = next(iter(sample_ids))
        attempts = [
            {
                "terminal_feedback": copy.deepcopy(m),
                "episode": project_episode(episodes[m["episode_sha256"]]),
            }
            for m in group["comparison_feedback"]["members"]
        ]
        groups.append(
            {
                "group_id": group_id,
                "input_group_sha256": group["input_group_sha256"],
                "outcome_variation": group["comparison_feedback"]["eligibility"],
                "attempts": attempts,
            }
        )
    evidence = {
        "groups": groups,
        "base_slot_rows": [
            copy.deepcopy(r) for r in base["rows"] if r["slot_id"] in slots
        ],
    }
    shared = share_json(evidence)
    _require(
        restore_json(shared) == evidence, "shared evidence does not reconstruct exactly"
    )
    context = {
        "stage": "complete-system-knowledge-edit",
        "edit_contract": contract,
        "evidence": shared,
        "reading_contract": (
            "Resolve $ref in evidence through its shared pool; $object encodes literal pairs. "
            "Read every group, including ties, every recorded response, actual tool event and terminal delivery. "
            "Semantic request histories and supplied knowledge are exact recorded fields; this is not a literal wire prompt. "
            "Omitted request custody/media fields remain addressable in the source. Speech is not replayed. "
            "Role text is a claim, not evidence that a tool ran. Scores describe final system outputs only; "
            "trajectory differences are not isolated causal credit. No reference transcript or gold answer is supplied. "
            "Propose general slot interpretations, never sample-specific answers. Empty edits retain the incumbent."
        ),
        "feedback_definition": {
            "frozen_f0": binding["frozen_f0"],
            "utility": "2*TP - frozen_f0*(2*TP+FP+FN)",
            "counts": "official combined word/character entity counts",
            "intent_exact": "separate terminal intent correctness",
            "format_ok": "separate terminal format validity",
        },
    }
    _canonical_context(context)
    contexts = [
        {
            "source_sample_id": active_ids[0],
            "source_feedback_sha256": joined["content_sha256"],
            "model_context": context,
            "model_context_sha256": content_hash(context),
        }
    ]
    if per_input:
        contract = slot_value_edit_contract(
            base["rows"],
            slot_ids=slots,
            fields=fields,
            evidence_groups={"observed-group": ancestry},
            max_edits=contract["max_edits"],
            max_field_chars=contract["max_field_chars"],
        )
        contexts = _group_contexts(
            groups,
            group_samples,
            active_ids,
            evidence["base_slot_rows"],
            contract,
            context["feedback_definition"],
            joined["content_sha256"],
            binding["max_context_bytes"],
        )
    return {
        "schema": DOCUMENT_SCHEMA,
        "source_bindings_sha256": source_sha,
        "construction_roster_sha256": active_sha,
        "full_construction_roster_sha256": ancestry_sha,
        "full_construction_sample_ids": ancestry,
        "source_materialization_sha256": [r["content_sha256"] for r in reports],
        "source_group_sha256": grouped["content_sha256"],
        "edit_contract": contract,
        "feedback_summary": joined["summary"],
        "contexts": contexts,
        "model_contacts_added": 0,
        "scorer_contacts_added": 0,
    }


def _group_contexts(
    groups, samples, active_ids, rows, contract, feedback, feedback_sha, maximum
):
    """Partition only by recorded input identity; include ties and every attempt."""
    _require(
        set(samples.values()) == set(active_ids) and len(samples) == len(active_ids),
        "group proposal roster must cover every input group exactly once",
    )
    cards = []
    for row in rows:
        card = copy.deepcopy(row)
        support = card.pop("source_support")
        card["source_support_binding"] = {
            "source_sha256": content_hash(support),
            "entries": len(support),
            "field": f"base_authored.rows[{row['slot_id']}].source_support",
            "disposition": "custody-list-omitted; canonical source and full ancestry retained",
        }
        cards.append(card)
    by_sample = {}
    for group in groups:
        observed = copy.deepcopy(group)
        observed["source_group_id"] = group["group_id"]
        observed["group_id"] = "observed-group"
        for attempt in observed["attempts"]:
            attempt["episode"] = project_system_events(attempt["episode"])
        evidence = {"groups": [observed], "base_slot_rows": cards}
        shared = share_json(evidence)
        _require(restore_json(shared) == evidence, "group evidence sharing differs")
        context = {
            "stage": "complete-system-knowledge-edit",
            "context_view": VIEW_ID,
            "edit_contract": contract,
            "evidence": shared,
            "feedback_definition": feedback,
            "reading_contract": (
                "This is one recorded input group from a complete batch, not an outcome-selected subset. "
                "Resolve shared JSON references and read every full-system attempt, including ties. "
                "Every role response, supplied knowledge body, actual tool result, route and delivery is retained. "
                "Control/tool-history JSON and wire responses have explicit decoded views, not literal wire copies. "
                "Only listed custody, timing and source-support lists are omitted; source hashes address originals. "
                "Unknown fields and malformed JSON remain literal. Speech and gold answers are not supplied. "
                "Cite only observed-group; its source_group_id and input hash bind this local alias. "
                "Do not attribute terminal differences causally to a single component. "
                "Generate a provisional general knowledge candidate or no edit; update no policy within this batch."
            ),
        }
        _require(
            len(_canonical_context(context).encode("utf-8")) <= maximum,
            "group proposal exceeds its context byte bound; no truncation permitted",
        )
        sample_id = samples[group["group_id"]]
        by_sample[sample_id] = {
            "source_sample_id": sample_id,
            "source_feedback_sha256": feedback_sha,
            "model_context": context,
            "model_context_sha256": content_hash(context),
        }
    return [by_sample[sample_id] for sample_id in active_ids]


def preparation_inputs(document):
    from ..analysis import (
        native_episode_source,
        system_feedback,
        system_rollout_groups,
        system_semantic_feedback,
        system_semantic_trajectory,
        shared_json,
        system_event_view,
    )
    from . import prepared_feedback, semantic_knowledge_edits, semantic_knowledge_build

    modules = (
        native_episode_source,
        system_feedback,
        system_rollout_groups,
        system_semantic_feedback,
        system_semantic_trajectory,
        shared_json,
        system_event_view,
        prepared_feedback,
        semantic_knowledge_edits,
        semantic_knowledge_build,
    )
    paths = [Path(__file__), *(Path(m.__file__) for m in modules)]
    return {
        "document_sha256": content_hash(document),
        "implementation_sha256": content_hash(
            {
                str(p.name): hash_stable_file(p, "knowledge edit implementation")[1]
                for p in paths
            }
        ),
    }


def prepare_knowledge_edit_contexts(source_pin, output_path, *, data_root):
    document = build_knowledge_edit_contexts(source_pin, data_root=data_root)
    return prepare_artifact(
        Path(output_path),
        kind=KIND,
        inputs=preparation_inputs(document),
        producer=lambda: document,
        contact_class="model-free",
    )


def load_knowledge_edit_feedback(
    spec, *, data_root, sample_ids, construction_roster_sha256
):
    states, receipt, document = load_verified_prepared_contexts(
        spec,
        data_root=data_root,
        sample_ids=sample_ids,
        construction_roster_sha256=construction_roster_sha256,
        schema=PREPARED_SCHEMA,
        build_contexts=build_knowledge_edit_contexts,
        preparation_inputs=preparation_inputs,
        artifact_kind=KIND,
        input_stage="complete-system-knowledge-edit",
    )
    receipt.update(
        full_construction_roster_sha256=document["full_construction_roster_sha256"],
        source_feedback_semantics="whole-system-terminal-official-counts-not-intermediate-credit",
    )
    return states, receipt


def knowledge_edit_response_format(_lock, root, *, prepared_contexts):
    wrapper, sha = _read_pinned_json(
        prepared_contexts, data_root=Path(root), field="knowledge contexts"
    )
    path = _resolve_data_path(
        prepared_contexts["relpath"], data_root=Path(root), field="knowledge contexts"
    )
    _require(
        isinstance(wrapper, Mapping) and wrapper.get("contact_class") == "model-free",
        "prepared context required",
    )
    document = load_artifact(
        path, expected_sha256=sha, kind=KIND, inputs=wrapper["inputs"]
    )
    _require(document["schema"] == DOCUMENT_SCHEMA, "knowledge context schema differs")
    return slot_value_edit_response_format(document["edit_contract"])
