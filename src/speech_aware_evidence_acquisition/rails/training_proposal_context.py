"""Project verified TRAIN trajectories and numeric feedback for offline proposals.

Model-facing content contains only prior own responses, executed control text,
supplied evidence and native numeric outcomes. Source IDs and custody paths stay
outside that content. The prepared artifact is not an admitted runtime memory.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping

from ..core.delivery import native_abstention_records
from ..core.preparation import hash_stable_file, prepare_artifact
from .group_relative_feedback import build_group_relative_feedback
from .hashing import content_hash
from .native_episode_receipt import validate_native_episode_delivery_receipt
from .native_training_context import NativeTrainingContextProjector

TRAINING_PROPOSAL_CONTEXT_SCHEMA = "saea-training-proposal-contexts-v2"


class TrainingProposalContextError(ValueError):
    """A proposal context cannot be recovered from its authorized source."""


def _read_pinned(pin, label):
    path = Path(pin["path"])
    _, actual, fingerprint = hash_stable_file(path, label)
    raw = path.read_bytes()
    _, after, after_fingerprint = hash_stable_file(path, label + " after read")
    if (
        actual != pin["sha256"] or hashlib.sha256(raw).hexdigest() != actual
        or actual != after or fingerprint != after_fingerprint
    ):
        raise TrainingProposalContextError(f"{label} changed or has a wrong hash")
    return raw


def _source_trajectories(source, sample_ids):
    manifest = json.loads(_read_pinned(source["manifest"], "proposal source manifest"))
    if manifest["arm"] == "construction-proposer-text":
        raise TrainingProposalContextError("gold-bearing construction proposers cannot supply context")
    documents = [json.loads(line) for line in
                 _read_pinned(manifest["raw_trace"], "proposal source trace").splitlines()]
    outputs = {row["sample_id"]: row for row in
               (json.loads(line) for line in
                _read_pinned(manifest["outputs"], "proposal source outputs").splitlines())}
    if set(outputs) != set(sample_ids):
        raise TrainingProposalContextError("proposal outputs do not cover the exact construction cohort")
    responses, completions, derivatives, request_ids = {}, {}, {}, set()
    requests = {sid: [] for sid in sample_ids}
    for row in documents:
        if row["channel"] == "MODEL_RESPONSE":
            rid = row["record_id"].removesuffix("/response")
            if rid in responses or row["record_id"] != rid + "/response":
                raise TrainingProposalContextError("ambiguous source response")
            responses[rid] = row["payload"]
        elif row["channel"] == "TOOL":
            if row["payload"].get("schema") == "saea-native-completion-v1":
                completion = row["payload"]
                rid = completion["request_id"]
                if rid in completions or row["record_id"] != rid + "/native-completion":
                    raise TrainingProposalContextError("ambiguous native source completion")
                completions[rid] = completion
            elif "/delivery/native-abstention-v1/" in row["record_id"]:
                if row["record_id"] in derivatives:
                    raise TrainingProposalContextError("ambiguous native abstention derivative")
                derivatives[row["record_id"]] = row["payload"]
        elif row["channel"] == "MODEL_REQUEST":
            request = row["payload"]["payload"]
            if "construction_targets" in request:
                raise TrainingProposalContextError("gold-bearing fields cannot supply proposal context")
            rid = request["request_id"]
            if rid in request_ids or row["record_id"] != rid + "/request":
                raise TrainingProposalContextError("ambiguous source request")
            if content_hash(request) != row["payload"]["payload_sha256"]:
                raise TrainingProposalContextError("source request payload hash differs")
            request_ids.add(rid)
            sid = request["sample_id"]
            if sid not in requests:
                raise TrainingProposalContextError("request lies outside the construction cohort")
            requests[sid].append(request)
    if (set(responses) | set(completions)) - request_ids:
        raise TrainingProposalContextError("source completion has no recorded request")
    result = {}
    for sid in sample_ids:
        abstention = None
        receipt = outputs[sid].get("native_episode_receipt")
        if receipt is not None:
            delivery = validate_native_episode_delivery_receipt(
                receipt, error_type=TrainingProposalContextError,
            )
            if delivery.kind == "abstention":
                disposition = delivery.terminal_disposition
                derived_id, request_document, response_document = native_abstention_records(
                    sample_id=sid,
                    source_contact=delivery.final_contact,
                    finish_reason=disposition["finish_reason"],
                )
                derivative_ids = {
                    record_id for record_id in derivatives
                    if record_id.startswith(derived_id + "/")
                }
                if (
                    outputs[sid].get("request_id") != derived_id
                    or derivative_ids != {
                        derived_id + "/request", derived_id + "/response",
                    }
                    or derivatives.get(derived_id + "/request") != request_document
                    or derivatives.get(derived_id + "/response") != response_document
                    or any(
                        outputs[sid].get(field) != response_document[field]
                        for field in (
                            "request_sha256", "response_sha256", "response_text_sha256",
                        )
                    )
                    or any(outputs[sid].get(field, "") != "" for field in ("text", "response"))
                ):
                    raise TrainingProposalContextError(
                        "native abstention derivative differs from shared delivery"
                    )
                abstention = {
                    "kind": "abstention",
                    "delivered_solver": False,
                    "derived_request_id": derived_id,
                    "response_sha256": response_document["response_sha256"],
                    "response_text_sha256": response_document["response_text_sha256"],
                }
        trajectory = []
        native = NativeTrainingContextProjector()
        evidence_pool, evidence_labels = [], {}
        for request in requests[sid]:
            rid = request["request_id"]
            response = responses.get(rid)
            controls = [h for h in request.get("history", ()) if h.get("role") == "control"]
            control = controls[-1] if controls else {}
            action = str(control.get("contact_id", "unspecified"))
            if action.endswith(":" + sid):
                action = action[:-len(sid)-1]
            selected_evidence = []
            for evidence in request.get("supplied_evidence", ()):
                text = evidence.get("content")
                if not isinstance(text, str):
                    raise TrainingProposalContextError("supplied evidence content is not text")
                value = {"content": text, "kind": evidence.get("knowledge_role", "observation")}
                key = content_hash(value)
                if key not in evidence_labels:
                    evidence_labels[key] = f"evidence-{len(evidence_labels) + 1}"
                    evidence_pool.append({"label": evidence_labels[key], **value})
                selected_evidence.append(evidence_labels[key])
            response_text = None if response is None else response.get("text")
            if response is not None and (
                not isinstance(response_text, str)
                or hashlib.sha256(response_text.encode()).hexdigest() != response["response_text_sha256"]
            ):
                raise TrainingProposalContextError("own response text no longer matches its source")
            step = {
                "action": action, "instruction": control.get("content", ""),
                "response": response_text, "response_observed": response is not None,
                "selected_final": rid == outputs[sid]["request_id"],
                "evidence_labels": selected_evidence,
            }
            native_fields = native.project(request, response, completions.get(rid))
            if native_fields is not None:
                step.update(native_fields)
            trajectory.append(step)
        selected = [step for step in trajectory if step["selected_final"]]
        if abstention is None and len(selected) != 1:
            raise TrainingProposalContextError("source has no unique selected final request")
        output_hash = outputs[sid].get("response_text_sha256")
        if abstention is None:
            final = selected[0]
            if (
                not final["response_observed"]
                or not isinstance(output_hash, str)
                or hashlib.sha256(final["response"].encode()).hexdigest() != output_hash
            ):
                raise TrainingProposalContextError(
                    "selected response does not match output response lineage"
                )
        elif selected:
            raise TrainingProposalContextError(
                "native abstention must not select a model response as final"
            )
        projected = {
            "trajectory": trajectory,
            "evidence": evidence_pool,
            "final_response_sha256": output_hash,
        }
        if abstention is not None:
            projected["delivery"] = abstention
        result[sid] = projected
    return result


def build_training_proposal_contexts(source_bindings):
    """Rebuild source authority before projecting any own trajectory content."""
    try:
        feedback = build_group_relative_feedback(source_bindings)
        ids = tuple(group["sample_id"] for group in feedback["groups"])
        trajectories = [_source_trajectories(source, ids) for source in feedback["sources"]]
        contexts = []
        for group in feedback["groups"]:
            sid = group["sample_id"]
            candidates = []
            candidate_deliveries = []
            for i, member in enumerate(group["members"]):
                projected = dict(trajectories[i][sid])
                final_response_sha256 = projected.pop("final_response_sha256")
                delivery = projected.pop("delivery", None)
                if final_response_sha256 != member["source"]["response_sha256"]:
                    raise TrainingProposalContextError(
                        "selected response differs from verified reward response lineage"
                    )
                candidates.append({
                    "label": f"option-{i + 1}",
                    **projected,
                    **({"delivery": {
                        "kind": "abstention", "delivered_solver": False,
                    }} if delivery is not None else {}),
                    "native_counts": member["native_counts"], "quality": member["quality"],
                })
                candidate_deliveries.append(delivery)
            visible = {"task_family": feedback["carrier_lock_key"], "candidates": candidates}
            serialized = json.dumps(visible, ensure_ascii=False)
            hidden = set(ids)
            for source in feedback["sources"]:
                hidden.update((
                    source["candidate_id"], source["run_id"], source["attempt_id"],
                    source["manifest"]["path"], source["reward_artifact"]["path"],
                ))
            if any(value in serialized for value in hidden):
                raise TrainingProposalContextError(
                    "source path or identity leaked into model-facing content"
                )
            contexts.append({
                "source_sample_id": sid, "source_feedback_sha256": content_hash(group),
                "candidate_bindings": [
                    {"label": f"option-{i + 1}", "candidate_id": member["candidate_id"],
                     "reward_link_sha256": member["reward_link_sha256"],
                     "source": member["source"],
                     **({"delivery": candidate_deliveries[i]}
                        if candidate_deliveries[i] is not None else {})}
                    for i, member in enumerate(group["members"])
                ],
                "model_context": visible, "model_context_sha256": content_hash(visible),
            })
        return {
            "schema": TRAINING_PROPOSAL_CONTEXT_SCHEMA, "status": "source-verified",
            "role": "training-feedback-proposal",
            "construction_roster_sha256": feedback["construction_roster_sha256"],
            "feedback_sha256": content_hash(feedback), "sources": feedback["sources"],
            "contexts": contexts,
        }
    except (ValueError, RuntimeError, OSError, KeyError, TypeError) as error:
        raise TrainingProposalContextError(str(error)) from error


def training_proposal_context_preparation_inputs(document: Mapping[str, object]) -> dict[str, str]:
    """Derive immutable prepared-artifact inputs for one verified document.

    The loader reuses this exact calculation before accepting persisted bytes,
    so a warm artifact cannot silently outlive its projection implementation.
    """

    from ..core.model import native_framework_history, native_history
    from . import core_client, hashing, native_training_context, native_tool_authority

    dependencies = [Path(__file__), *(
        Path(module.__file__) for module in (
            native_training_context, native_framework_history, native_history,
            native_tool_authority, hashing, core_client,
        )
    )]
    implementations = {
        path.name: hash_stable_file(path, "proposal projection implementation")[1]
        for path in dependencies
    }
    return {
        "document_sha256": content_hash(document),
        "implementation_sha256": content_hash(implementations),
    }


def prepare_training_proposal_contexts(source_bindings, output_path):
    """Persist compact model-facing contexts through shared preparation."""
    document = build_training_proposal_contexts(source_bindings)
    try:
        return prepare_artifact(
            Path(output_path), kind="training-proposal-contexts",
            inputs=training_proposal_context_preparation_inputs(document),
            producer=lambda: document, contact_class="model-free",
        )
    except (ValueError, RuntimeError, OSError) as error:
        raise TrainingProposalContextError(str(error)) from error
