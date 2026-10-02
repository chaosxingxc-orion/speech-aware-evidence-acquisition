"""Link verified construction trajectories to saved native numeric feedback.

This module never calls a model or scorer, copies reference text, or admits memory.
ExperienceSource.response_sha256 follows AgentLoopResult's final-text convention.
Transport response identity remains separately available in provenance.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from ..contracts import TraceRecord
from ..core.bundle.verify import verify_bundle
from ..core.roster import CONSTRUCTION_ROSTER_ROLE, read_roster
from ..core.scoring_receipt import SavedScoreReceiptRef, verify_complete_score_receipt
from .experience_memory import ExperienceSource
from .hashing import content_hash

REWARD_LINK_SCHEMA = "saea-reward-link-v1"
REWARD_PROJECTION_SCHEMA = "saea-reward-projection-v1"
_SHA256 = re.compile(r"[0-9a-f]{64}")
_RESEARCH_AXES = frozenset({"OBS", "ORG", "SUPPLY", "USE"})
_ACTION_AXES = _RESEARCH_AXES | {"REVIEW", "REPLAY", "TOOL"}
_ASR_ROWS = frozenset({"wer", "hits", "substitutions", "deletions", "insertions"})
SLURP_NATIVE_FIELDS = (
    "scenario_action_exact", "scenario_exact", "action_exact",
    "slot_f1_exact_tp", "slot_f1_exact_fp", "slot_f1_exact_fn",
    "slu_f1_word_tp", "slu_f1_word_fp", "slu_f1_word_fn",
    "slu_f1_char_tp", "slu_f1_char_fp", "slu_f1_char_fn",
)
A2T_NATIVE_FIELDS = (
    "tool_correct", "exact_match", "param_exact_match",
    "param_precision", "param_recall", "param_f1",
    "param_correct_keys", "param_predicted_keys", "param_gold_keys", "parsed",
    "is_multi_tool", "num_expected_tools", "multi_tool_all_match",
    "multi_tool_recall", "multi_tool_precision", "multi_tool_f1",
)
_A2T_FLAGS = frozenset({"tool_correct", "exact_match", "param_exact_match", "parsed",
                        "is_multi_tool", "multi_tool_all_match"})
_A2T_COUNTS = frozenset({"param_correct_keys", "param_predicted_keys", "param_gold_keys",
                         "num_expected_tools"})
_A2T_RATES = frozenset(A2T_NATIVE_FIELDS) - _A2T_FLAGS - _A2T_COUNTS
_A2T_AGGREGATES = frozenset({
    "samples", "tool_accuracy", "exact_match", "param_exact_match", "param_precision",
    "param_recall", "param_f1", "param_precision_micro", "param_recall_micro",
    "param_f1_micro", "param_correct_keys", "param_predicted_keys", "param_gold_keys",
    "parse_rate", "parse_failures", "multi_tool_samples",
})
_SLURP_AGGREGATES = frozenset(
    "port_micro." + field for field in (
        "samples", "slu_f1", "slu_f1_precision", "slu_f1_recall",
        "span_f1", "span_f1_precision", "span_f1_recall",
        "scenario_accuracy", "action_accuracy", "intent_accuracy",
    )
)
_NATIVE_PROJECTIONS = {
    "a2t-toolcall-official": (_A2T_AGGREGATES, frozenset(A2T_NATIVE_FIELDS),
                              frozenset(A2T_NATIVE_FIELDS)),
    "asr-wer": (frozenset({"mean_wer", "samples"}), _ASR_ROWS, _ASR_ROWS),
    "asr-wer-whisper": (
        frozenset({"corpus_wer", "substitutions", "deletions", "insertions",
                   "reference_words", "samples"}), _ASR_ROWS, _ASR_ROWS,
    ),
    **{name: (_SLURP_AGGREGATES, frozenset(SLURP_NATIVE_FIELDS),
              frozenset(SLURP_NATIVE_FIELDS))
       for name in ("slurp-slu-official", "slurp-slu-official-train", "slurp-slu-train")},
}
_MANIFEST_KEYS = frozenset({
    "tool_id", "tool_manifest_sha256", "manifest_sha256", "tool_manifest_id",
})


class RewardLinkError(ValueError):
    """A source, native projection, or immutable reward link is invalid."""


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise RewardLinkError(f"{field} must be nonempty text")
    return value


def _sha(value, field):
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise RewardLinkError(f"{field} must be a lowercase SHA-256")
    return value


def _mapping(value, field):
    if not isinstance(value, Mapping):
        raise RewardLinkError(f"{field} must be an object")
    return value


def _fields(value, field):
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence) or not value:
        raise RewardLinkError(f"{field} must be a nonempty field sequence")
    result = tuple(_text(item, field) for item in value)
    if len(set(result)) != len(result):
        raise RewardLinkError(f"{field} contains duplicate paths")
    return result


def _numeric_path(value, field, *, allow_boolean=False):
    current = value
    for part in field.split("."):
        if not isinstance(current, Mapping) or part not in current:
            raise RewardLinkError(f"native score field {field!r} is missing")
        current = current[part]
    if isinstance(current, bool) and allow_boolean:
        current = int(current)  # Only named official boolean metrics permit this conversion.
    if isinstance(current, bool) or not isinstance(current, (int, float)):
        raise RewardLinkError(f"native score field {field!r} must be numeric")
    if not math.isfinite(current) or current < 0:
        raise RewardLinkError(f"native score field {field!r} must be finite and nonnegative")
    if field in SLURP_NATIVE_FIELDS[:3] and current not in (0, 1):
        raise RewardLinkError(f"intent correctness field {field!r} must be zero or one")
    return current


def audio2tool_native_counts(counts):
    """Validate the official saved numeric view without loading targets or rescoring."""
    if not isinstance(counts, Mapping) or set(counts) != set(A2T_NATIVE_FIELDS):
        raise RewardLinkError("Audio2Tool feedback requires all official native fields")
    values = {field: _numeric_path(counts, field, allow_boolean=field in _A2T_FLAGS)
              for field in A2T_NATIVE_FIELDS}
    if any(values[k] not in (0, 1) for k in _A2T_FLAGS):
        raise RewardLinkError("official correctness and applicability flags must be binary")
    if any(values[k] > 1 for k in _A2T_RATES):
        raise RewardLinkError("official quality rates must be on the zero-to-one scale")
    if any(not float(values[k]).is_integer() for k in _A2T_COUNTS):
        raise RewardLinkError("official parameter and tool counts must be integers")
    if (values["num_expected_tools"] < 1
            or values["is_multi_tool"] != int(values["num_expected_tools"] > 1)
            or values["param_correct_keys"] > min(values["param_predicted_keys"], values["param_gold_keys"])
            or values["exact_match"] != values["tool_correct"] * values["param_exact_match"]):
        raise RewardLinkError("official native counts have inconsistent identities")
    return values


@dataclass(frozen=True)
class RewardProjection:
    """Select task-native numbers while retaining all per-row sufficient counts."""

    reward_rule_id: str
    scorer: str
    aggregate_fields: tuple[str, ...]
    per_sample_fields: tuple[str, ...]
    schema: str = REWARD_PROJECTION_SCHEMA

    def __post_init__(self):
        _text(self.reward_rule_id, "reward rule ID")
        _text(self.scorer, "scorer")
        specification = _NATIVE_PROJECTIONS.get(self.scorer)
        if specification is None:
            raise RewardLinkError("scorer has no registered native quality projection")
        aggregate = _fields(self.aggregate_fields, "aggregate fields")
        rows = _fields(self.per_sample_fields, "per-sample fields")
        allowed_aggregate, allowed_rows, required_rows = specification
        if not set(aggregate) <= allowed_aggregate or not set(rows) <= allowed_rows:
            raise RewardLinkError("projection contains non-native or answer-bearing fields")
        if not required_rows <= set(rows):
            raise RewardLinkError("projection omits required native sufficient statistics")
        if self.schema != REWARD_PROJECTION_SCHEMA:
            raise RewardLinkError("unsupported reward projection schema")
        object.__setattr__(self, "aggregate_fields", aggregate)
        object.__setattr__(self, "per_sample_fields", rows)

    def as_json(self):
        return {
            "schema": self.schema, "reward_rule_id": self.reward_rule_id,
            "scorer": self.scorer, "aggregate_fields": list(self.aggregate_fields),
            "per_sample_fields": list(self.per_sample_fields),
        }

    @classmethod
    def from_json(cls, value):
        row = _mapping(value, "reward projection")
        if set(row) != {"schema", "reward_rule_id", "scorer", "aggregate_fields", "per_sample_fields"}:
            raise RewardLinkError("reward projection has missing or unknown fields")
        return cls(**row)


@dataclass(frozen=True)
class RewardLink:
    """One source-bound feedback artifact; validate again before conversion."""

    source: ExperienceSource
    carrier_lock_key: str
    construction_roster_sha256: str
    projection: RewardProjection
    native_score_vector: Mapping[str, object]
    provenance: Mapping[str, object]
    link_sha256: str
    schema: str = REWARD_LINK_SCHEMA

    def unsigned_json(self):
        return {
            "schema": self.schema, "source": self.source.as_json(),
            "carrier_lock_key": self.carrier_lock_key,
            "construction_roster_sha256": self.construction_roster_sha256,
            "projection": self.projection.as_json(),
            "native_score_vector": dict(self.native_score_vector),
            "provenance": dict(self.provenance),
        }

    def validate(self):
        """Validate stored integrity; verify_reward_links rechecks source authority."""
        if self.schema != REWARD_LINK_SCHEMA:
            raise RewardLinkError("unsupported reward link schema")
        self.source.validate()
        if self.source.partition_role != "train":
            raise RewardLinkError("reward links require the TRAIN construction partition")
        _text(self.carrier_lock_key, "carrier")
        _sha(self.construction_roster_sha256, "construction roster hash")
        _sha(self.link_sha256, "reward link hash")
        self.projection.__post_init__()
        if content_hash(self.unsigned_json()) != self.link_sha256:
            raise RewardLinkError("reward link contents no longer match its hash")

    def as_json(self):
        self.validate()
        # Do not hand mutable internal containers to a serialization consumer.
        return json.loads(json.dumps({**self.unsigned_json(), "link_sha256": self.link_sha256}))

def _artifact_pin(manifest, key):
    entry = _mapping(manifest.get(key), f"manifest {key}")
    path = Path(_text(entry.get("path"), f"{key} path")).resolve()
    digest = _sha(entry.get("sha256"), f"{key} hash")
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise RewardLinkError(f"{key} changed after bundle verification")
    return {"path": str(path), "sha256": digest}


def _manifest_identities(payload):
    """Keep each tool/manifest identity at its own path, without evidence text."""
    found = {}

    def visit(value, path):
        if isinstance(value, Mapping):
            for key, child in value.items():
                location = f"{path}.{key}" if path else str(key)
                if isinstance(key, str) and (key in _MANIFEST_KEYS or key.endswith("_manifest_sha256")):
                    if isinstance(child, str):
                        found[location] = child
                visit(child, location)
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            for index, child in enumerate(value):
                visit(child, f"{path}[{index}]")

    visit(payload, "")
    return dict(sorted(found.items()))


def _model_index(documents, sample_ids):
    """Bind normalized responses and control contacts to exact transport requests."""
    requests, responses, contacts = {}, {}, {}
    for row in documents:
        if row["channel"] != "MODEL_REQUEST":
            continue
        record_id = row["record_id"]
        payload = _mapping(row["payload"].get("payload"), "model request payload")
        if not record_id.endswith("/request"):
            raise RewardLinkError("model request has a noncanonical record identity")
        request_id = record_id.removesuffix("/request")
        sample = payload.get("sample_id")
        if sample not in sample_ids or payload.get("request_id") != request_id:
            raise RewardLinkError("model request has a conflicting sample or request identity")
        if content_hash(payload) != row["payload"].get("payload_sha256"):
            raise RewardLinkError("model request payload hash differs from its content")
        requests[request_id] = {"sample": sample, "payload": payload}
    for row in documents:
        if row["channel"] != "MODEL_RESPONSE":
            continue
        record_id = row["record_id"]
        if not record_id.endswith("/response"):
            raise RewardLinkError("model response has a noncanonical record identity")
        request_id = record_id.removesuffix("/response")
        if request_id not in requests:
            raise RewardLinkError("model response lacks its exact request")
        payload = row["payload"]
        text = payload.get("text")
        if not isinstance(text, str):
            raise RewardLinkError("normalized model response text is missing")
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if digest != payload.get("response_text_sha256"):
            raise RewardLinkError("normalized model response text hash differs")
        responses[request_id] = digest
        request = requests[request_id]
        history = request["payload"].get("history", [])
        controls = [turn for turn in history if isinstance(turn, Mapping)
                    and turn.get("role") == "control" and "contact_id" in turn]
        if controls:
            cid = _text(controls[-1]["contact_id"], "control contact ID")
            contacts.setdefault((request["sample"], cid, digest), set()).add(request_id)
    # An attempted request without a normalized response is retained, but cannot
    # satisfy a successful USE contact or a credited final response.
    return requests, responses, contacts



def _native_contact_roles(assigned, contacts):
    """Read explicit native roles; never infer a role from an invocation index."""
    records = {(sample, row["record_id"]): row["payload"] for sample, row in assigned}
    roles, requests = {}, {}
    for sample, row in assigned:
        rid, payload = row["record_id"], row["payload"]
        if row["channel"] != "USE" or not rid.endswith("/native-role-contact"):
            continue
        request_id = rid.removesuffix("/native-role-contact")
        role = _text(payload.get("use_role_id"), "native role ID")
        cid = _text(payload.get("use_agent_contact_id"), "native contact ID")
        digest = _sha(payload.get("use_response_text_sha256"), "native response text")
        key = (sample, cid, digest)
        request = records.get((sample, request_id + "/request"))
        response = records.get((sample, request_id + "/response"))
        if (request_id not in contacts.get(key, ()) or request is None or response is None
                or payload.get("use_request_sha256") != request.get("payload_sha256")
                or payload.get("use_response_sha256") != response.get("response_sha256")
                or digest != response.get("response_text_sha256")):
            raise RewardLinkError("native role differs from its exact model contact")
        suffix = ":" + sample
        prefix, separator, index = cid.removesuffix(suffix).rpartition(":")
        if (not cid.endswith(suffix) or not separator or not index.isdecimal()
                or str(int(index)) != index or not prefix.endswith(":" + role)):
            raise RewardLinkError("native role differs from its registered contact identity")
        if key in roles or request_id in requests:
            raise RewardLinkError("native contact has duplicate role attribution")
        roles[key] = role
        requests[request_id] = (sample, role, digest)
    return roles, requests


def _validate_actions(assigned, contacts, outputs, delivery_contacts=None, abstentions=None):
    """Cross-check typed phase identities before crediting any action."""
    phases, native_phases, runtime, latest = {}, {}, {}, {}
    native_roles, native_requests = _native_contact_roles(assigned, contacts)
    successful_responses = {(sample, digest) for sample, _, digest in contacts}
    delivery_contacts = delivery_contacts or {}
    abstentions = abstentions or {}

    def phase_responses(sample, phase):
        key = (sample, phase)
        if key in native_phases:
            return native_phases[key]
        return {phases[key]} if key in phases else set()

    def contact_requests(sample, contact):
        contact = _mapping(contact, "USE contact")
        plan = _mapping(contact.get("plan"), "USE contact plan")
        cid = _text(plan.get("contact_id"), "USE contact ID")
        digest = _sha(contact.get("response_sha256"), "USE response hash")
        matches = contacts.get((sample, cid, digest))
        if not matches:
            raise RewardLinkError("USE contact has a stale or cross-sample response")
        return matches, digest

    for sample, row in assigned:
        record_id, payload = row["record_id"], row["payload"]
        if row["channel"] != "USE" or "use_contacts" not in payload:
            continue
        suffix = "/agent-loop/runtime-use"
        if not record_id.endswith(suffix):
            raise RewardLinkError("USE contacts lack a canonical runtime namespace")
        head = record_id.removesuffix(suffix)
        rows = payload["use_contacts"]
        if not isinstance(rows, list) or not rows:
            raise RewardLinkError("runtime USE requires successful contacts")
        final_hash = _sha(payload.get("use_final_response_sha256"), "phase final response")
        delivery_contact = delivery_contacts.get((sample, final_hash))
        contact_final_hash = delivery_contact[0] if delivery_contact else final_hash
        native_runtime = any(
            (sample, contact.get("plan", {}).get("contact_id"), contact.get("response_sha256"))
            in native_roles for contact in rows if isinstance(contact, Mapping)
        )
        eligible = set()
        runtime_requests = set()
        for contact in rows:
            matches, digest = contact_requests(sample, contact)
            runtime_requests.update(matches)
            if digest == contact_final_hash:
                eligible.update(matches)
            # Shared phase materials name contacts as program:phase:sample.
            # Continuous programs have one runtime-use record for all phases.
            cid = contact["plan"]["contact_id"]
            native_role = native_roles.get((sample, cid, digest))
            if native_role is not None:
                native_phases.setdefault((sample, native_role), set()).add(digest)
                continue
            if native_runtime:
                raise RewardLinkError("native runtime contact lacks explicit role custody")
            suffix = ":" + sample
            if cid.endswith(suffix):
                _, separator, contact_phase = cid.removesuffix(suffix).rpartition(":")
                if separator:
                    key = (sample, contact_phase)
                    if key in phases and phases[key] != digest:
                        raise RewardLinkError("phase has conflicting successful contacts")
                    phases[key] = digest
        if delivery_contact:
            eligible &= {delivery_contact[1]}
        abstained = sample in abstentions and final_hash == hashlib.sha256(b"").hexdigest()
        if abstained:
            if (runtime_requests != abstentions[sample] or any(
                    wave.get("selected_final_contact_id") is not None
                    for wave in payload.get("use_waves", []))):
                raise RewardLinkError("abstention runtime differs from its complete unselected contacts")
            # Empty delivery is a deterministic terminal disposition, not a
            # successful model response or credit for the rejected completion.
            eligible.clear()
        elif not eligible:
            raise RewardLinkError("phase final response is absent from its successful contacts")
        for wave in payload.get("use_waves", []):
            plans, hashes = wave.get("contact_plans", []), wave.get("response_sha256s", [])
            if len(plans) != len(hashes):
                raise RewardLinkError("USE wave contact and response counts differ")
            for plan, digest in zip(plans, hashes):
                contact_requests(sample, {"plan": plan, "response_sha256": digest})
        waves = payload.get("use_waves", [])
        selected = waves[-1].get("selected_final_contact_id") if waves else None
        if selected is not None:
            eligible &= contacts.get((sample, selected, contact_final_hash), set())
            if not eligible:
                raise RewardLinkError("selected final contact differs from the runtime answer")
        if "use_runtime_trace_sha256" in payload:
            keys = ("controller_policy_id", "agent_executor_id", "agent_executor_version",
                    "knowledge_snapshot_sha256", "initial_query_state_sha256",
                    "final_query_state_sha256", "speech_packet_sha256", "contacts",
                    "waves", "transitions", "final_response_sha256")
            if any("use_" + key not in payload for key in keys):
                raise RewardLinkError("runtime USE digest has an incomplete document")
            document = {key: payload["use_" + key] for key in keys}
            if content_hash(document) != payload["use_runtime_trace_sha256"]:
                raise RewardLinkError("runtime USE document hash differs")
        runtime[head] = payload
        latest[sample] = (contact_final_hash, eligible)

    for sample, row in assigned:
        if row["channel"] != "ORG":
            continue
        for state in row["payload"].get("org_agent_states", []):
            kind = state.get("state_kind", "")
            if not isinstance(kind, str) or not kind.startswith("phase:"):
                continue
            phase = kind.removeprefix("phase:")
            digest = _sha(state.get("source_response_sha256"), "phase state source")
            if (sample, digest) not in successful_responses:
                raise RewardLinkError("phase state lacks a traced sample response")
            key = (sample, phase)
            if key in native_phases:
                if digest not in native_phases[key]:
                    raise RewardLinkError("native phase state conflicts with its role contacts")
            else:
                if key in phases and phases[key] != digest:
                    raise RewardLinkError("phase state conflicts with its contact response")
                phases[key] = digest

    for sample, row in assigned:
        record_id, payload = row["record_id"], row["payload"]
        for key in ("sample_id", "query_sample_id", "review_sample_id", "use_sample_id",
                    "obs_sample_id", "org_sample_id", "supply_sample_id"):
            if key in payload and payload[key] != sample:
                raise RewardLinkError("typed action sample differs from its trace namespace")
        for key in ("org_initial_query_state", "org_final_query_state"):
            if key in payload and _mapping(payload[key], key).get("query_sample_id") != sample:
                raise RewardLinkError("organization query state belongs to another sample")
        for axis in ("obs", "use"):
            result = payload.get(axis + "_result")
            if isinstance(result, Mapping) and "sample_id" in result and result["sample_id"] != sample:
                raise RewardLinkError("tool result belongs to another sample")
        for prefix in ("review", "use_review"):
            key = prefix + "_response_sha256"
            if key in payload:
                phase = payload.get("review_phase" if prefix == "review" else "use_phase")
                expected = phase_responses(sample, phase)
                if payload[key] not in expected:
                    raise RewardLinkError("review references a stale or cross-phase answer")
        parts = record_id.rsplit("/", 3)
        if parts[-1].startswith("tool-"):
            phase = parts[-2]
            for key in ("obs_source_response_sha256", "use_source_response_sha256"):
                if key in payload and payload[key] not in phase_responses(sample, phase):
                    raise RewardLinkError("phase tool references a stale source response")
        elif len(parts) == 4 and parts[-2].startswith("tool-"):
            phase = parts[-3]
            axes = [axis for axis in ("obs", "use") if axis + "_core_request_id" in payload]
            if len(axes) != 1:
                raise RewardLinkError("native phase tool lacks a unique source contact")
            for axis in axes:
                request_key = axis + "_core_request_id"
                request_id = payload[request_key]
                digest = payload.get(axis + "_source_response_sha256")
                call_id = _text(payload.get(axis + "_tool_call_id"), "native tool call ID")
                if (native_requests.get(request_id) != (sample, phase, digest)
                        or payload.get(axis + "_phase") != phase
                        or parts[-1] != content_hash({"request_id": request_id,
                                                      "tool_call_id": call_id})):
                    raise RewardLinkError("native phase tool differs from its source contact")
        if record_id.endswith("/agent-loop/posthoc-use"):
            head = record_id.removesuffix("/agent-loop/posthoc-use")
            prior = runtime.get(head)
            if prior is None or any(payload.get(key) != prior.get(key) for key in (
                "use_runtime_trace_sha256", "use_final_response_sha256",
            )):
                raise RewardLinkError("posthoc USE differs from its runtime response")
    for output in outputs:
        sample = output["sample_id"]
        if sample in latest:
            final_hash, eligible = latest[sample]
            if output["response_text_sha256"] != final_hash or output["request_id"] not in eligible:
                raise RewardLinkError("credited final output differs from the terminal phase")


def _native_abstention(output, documents, requests, response_payloads, contacts):
    """Verify empty delivery against the shared derivation and exact model custody."""
    from ..core.delivery import native_abstention_records, native_seal_refusal_abstention_records
    from .native_episode_receipt import validate_native_episode_delivery_receipt

    receipt = _mapping(output.get("native_episode_receipt"), "native abstention receipt")
    delivery = validate_native_episode_delivery_receipt(receipt, error_type=RewardLinkError)
    if delivery.kind != "abstention":
        raise RewardLinkError("derived final output is not a native abstention")
    disposition = delivery.terminal_disposition
    if disposition["reason"] == "finite_completion":
        derived_id, derived_request, derived_response = native_abstention_records(
            sample_id=output["sample_id"], source_contact=delivery.final_contact,
            finish_reason=disposition["finish_reason"])
    else:
        derived_id, derived_request, derived_response = native_seal_refusal_abstention_records(
            sample_id=output["sample_id"], source_contact=delivery.final_contact,
            seal_refusal=disposition["seal_refusal"])
    expected = {derived_id + "/request": derived_request, derived_id + "/response": derived_response}
    records = [row for row in documents if row["record_id"] in expected]
    if (output["request_id"] != derived_id or output.get("text") != ""
            or len(records) != 2 or {r["record_id"] for r in records} != set(expected)
            or any(r["channel"] != "TOOL" or r["payload"] != expected[r["record_id"]] for r in records)
            or any(output.get(k) != derived_response[k] for k in (
                "request_sha256", "response_sha256", "response_text_sha256"))):
        raise RewardLinkError("native abstention differs from its exact empty derivation")
    bound = set()
    role_records = {row["record_id"]: row["payload"] for row in documents if row["channel"] == "USE"}
    visits = [*receipt["role_visits"], receipt["interrupted_role"]]
    for visit in visits:
        for contact in visit["execution_receipt"]["contacts"]:
            rid = contact["request_id"]
            request = requests.get(rid)
            response = response_payloads.get(rid, {})
            key = (output["sample_id"], contact["agent_contact_id"], contact["response_text_sha256"])
            role = role_records.get(rid + "/native-role-contact", {})
            if (request is None or request["sample"] != output["sample_id"]
                    or content_hash(request["payload"]) != contact["request_sha256"]
                    or any(response.get(k) != contact[k] for k in ("response_sha256", "response_text_sha256"))
                    or rid not in contacts.get(key, ())
                    or role.get("use_role_id") != visit["role_id"]):
                raise RewardLinkError("native abstention receipt differs from its exact model contacts")
            bound.add(rid)
    if bound != {rid for rid, value in requests.items() if value["sample"] == output["sample_id"]}:
        raise RewardLinkError("native abstention receipt omits model contacts")
    return bound


def _trace(bundle, sample_ids, raw):
    """Associate opaque requests and existing phase namespaces by exact identity."""
    from ..core.bundle import BundleError
    from ..core.bundle.outputs import _delivery_normalisation_receipt, _verify_delivery_normalisation

    documents = [json.loads(line) for line in raw.decode("utf-8").split("\n") if line]
    requests, responses, contacts = _model_index(documents, sample_ids)
    response_payloads = {r["record_id"].removesuffix("/response"): r["payload"]
                         for r in documents if r["channel"] == "MODEL_RESPONSE"}
    contact_outputs = []
    delivery_contacts = {}
    abstentions = {}
    for output in bundle.outputs_rows:
        request = requests.get(output["request_id"])
        if request is None or output.get("native_episode_receipt", {}).get("abstention_receipt"):
            abstentions[output["sample_id"]] = _native_abstention(
                output, documents, requests, response_payloads, contacts)
            continue
        if request is None or request["sample"] != output["sample_id"]:
            raise RewardLinkError("final output does not name its sample's exact request")
        contact_output = output
        try:
            normalisation = _delivery_normalisation_receipt(output)
            if normalisation is not None:
                payload = response_payloads.get(output["request_id"], {})
                if payload.get("response_sha256") != output["response_sha256"]:
                    raise RewardLinkError("delivery normalisation differs from its wire response")
                _verify_delivery_normalisation(output, normalisation, payload)
                # Attribute the model contact using its original response; keep
                # the actual delivered answer and official reward unchanged.
                contact_output = {**output, "response_text_sha256": normalisation["input_sha256"]}
                delivery_contacts[(output["sample_id"], output["response_text_sha256"])] = (
                    normalisation["input_sha256"], output["request_id"])
        except BundleError as error:
            raise RewardLinkError(str(error)) from error
        if responses.get(output["request_id"]) != contact_output["response_text_sha256"]:
            raise RewardLinkError("final output does not name its exact normalized response")
        contact_outputs.append(contact_output)
    events = {sample: [] for sample in sample_ids}
    assigned = []
    for row in documents:
        axis, record_id, payload = row["channel"], row["record_id"], row["payload"]
        if bundle.trace_records.get(record_id) != payload:
            raise RewardLinkError("trace changed after bundle verification")
        sample, prefix = None, record_id
        while "/" in prefix:
            prefix = prefix.rsplit("/", 1)[0]
            if prefix in requests:
                sample = requests[prefix]["sample"]
                break
        if axis in _ACTION_AXES:
            prefix = record_id
            while "/" in prefix:
                prefix = prefix.rsplit("/", 1)[0]
                if prefix in sample_ids:
                    if sample is not None and sample != prefix:
                        raise RewardLinkError("phase trace conflicts with model sample")
                    sample = prefix
                    break
        if sample is None:
            # Global bookkeeping remains covered by the whole trace hash.
            continue
        assigned.append((sample, row))
        events[sample].append({
            "axis": axis, "record_id": record_id,
            "event_sha256": TraceRecord(axis, record_id, payload).content_hash(),
            "tool_manifest_identity": _manifest_identities(payload),
        })
    _validate_actions(assigned, contacts, contact_outputs, delivery_contacts, abstentions)
    actions = {sample: [row for row in rows if row["axis"] in _ACTION_AXES]
               for sample, rows in events.items()}
    return events, actions


def _score_vector(receipt, projection, sample_ids):
    meta = _mapping(receipt.get("score_result"), "score result")
    raw = Path(_text(meta.get("path"), "score path")).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != meta.get("sha256"):
        raise RewardLinkError("score result changed after receipt verification")
    score = json.loads(raw)["scores"][projection.scorer]
    aggregate = _mapping(score.get("aggregate"), "score aggregate")
    rows = score.get("per_sample")
    if not isinstance(rows, list):
        raise RewardLinkError("score per_sample must be a list")
    by_id = {}
    for row in rows:
        row = _mapping(row, "score row")
        sample = _text(row.get("sample_id"), "score sample")
        if sample in by_id:
            raise RewardLinkError("duplicate native score row")
        by_id[sample] = row
    if set(by_id) != sample_ids:
        raise RewardLinkError("native scores do not exactly cover construction membership")
    per_sample = {
        sample: {field: _numeric_path(row, field, allow_boolean=(
            projection.scorer == "a2t-toolcall-official" and field in _A2T_FLAGS))
            for field in projection.per_sample_fields}
        for sample, row in by_id.items()
    }
    if projection.scorer == "a2t-toolcall-official":
        per_sample = {sample: audio2tool_native_counts(row) for sample, row in per_sample.items()}
    return {
        "aggregate": {field: _numeric_path(aggregate, field) for field in projection.aggregate_fields},
        "per_sample": per_sample,
    }, digest


def build_reward_links(manifest_path, score_receipt: SavedScoreReceiptRef,
                       construction_roster_path, projection: RewardProjection):
    """Build only from complete verified construction runs and their saved scores."""
    if not isinstance(projection, RewardProjection):
        raise RewardLinkError("projection must be a RewardProjection")
    projection.__post_init__()
    bundle = verify_bundle(Path(manifest_path))
    if bundle.manifest["status"] != "COMPLETED" or bundle.attempt_state != "FINALIZED":
        raise RewardLinkError("reward links require a COMPLETED, FINALIZED bundle")
    roster_path = Path(construction_roster_path)
    roster = read_roster(roster_path)
    if roster["roster_role"] != CONSTRUCTION_ROSTER_ROLE:
        raise RewardLinkError("reward links require a construction roster")
    carrier = roster["carrier_lock_key"]
    if carrier != bundle.manifest["split"]["carrier_lock_key"]:
        raise RewardLinkError("bundle and construction carrier differ")
    ids = tuple(item["sample_id"] for item in roster["items"])
    if len(set(ids)) != len(ids) or set(ids) != bundle.split_ids:
        raise RewardLinkError("bundle does not exactly match the construction roster")
    if carrier == "slurp":
        if any(not sample.startswith("slurp:train:") for sample in ids):
            raise RewardLinkError("SLURP construction requires TRAIN sample identities")
        if projection.scorer not in {"slurp-slu-official-train", "slurp-slu-train"}:
            raise RewardLinkError("SLURP construction requires its TRAIN scorer")
    elif carrier == "audio2tool":
        if (projection.scorer != "a2t-toolcall-official"
                or bundle.manifest["plan"]["split_role"] != "discovery"
                or roster["split_role"] != "discovery"):
            raise RewardLinkError("Audio2Tool feedback requires its official scorer and discovery construction")
    elif carrier not in {"earnings21-original", "earnings22-original"} or projection.scorer not in {
        "asr-wer", "asr-wer-whisper",
    }:
        raise RewardLinkError("carrier and native quality projection do not match")
    if projection.scorer not in bundle.manifest["scorers"]:
        raise RewardLinkError("native scorer is not declared by the bundle")
    receipt = verify_complete_score_receipt(score_receipt, bundle)
    vector, result_sha = _score_vector(receipt, projection, set(ids))
    # Shared source files are hashed once, not once for every sample.
    common = {
        "manifest": {"path": str(Path(manifest_path).resolve()),
                     "sha256": hashlib.sha256(Path(manifest_path).read_bytes()).hexdigest()},
        **{key: _artifact_pin(bundle.manifest, key) for key in ("outputs", "raw_trace", "trace_manifest")},
    }
    raw = Path(common["raw_trace"]["path"]).read_bytes()
    if hashlib.sha256(raw).hexdigest() != common["raw_trace"]["sha256"]:
        raise RewardLinkError("raw trace changed after verification")
    events, actions = _trace(bundle, set(ids), raw)
    roster_sha = hashlib.sha256(roster_path.read_bytes()).hexdigest()
    outputs = {row["sample_id"]: row for row in bundle.outputs_rows}
    links = []
    for sample in ids:
        output = outputs[sample]
        row_vector = {"aggregate": vector["aggregate"],
                      "per_sample": {sample: vector["per_sample"][sample]}}
        outcome = content_hash({
            "partition_role": "train", "sample_id": sample, "carrier_lock_key": carrier,
            "construction_roster_sha256": roster_sha,
            "projection": projection.as_json(), "native_score_vector": row_vector,
            "score_result_sha256": result_sha,
        })
        source = ExperienceSource(
            "train", sample, content_hash({"events": events[sample]}),
            content_hash({"actions": actions[sample]}),
            _sha(output["response_text_sha256"], "final-text hash"), outcome,
        )
        provenance = {
            **common, "score_result_sha256": result_sha,
            "score_receipt_identity": receipt["identity"],
            "ordered_events": events[sample], "ordered_actions": actions[sample],
            "wire_response_sha256": _sha(output["response_sha256"], "wire response hash"),
        }
        unsigned = {
            "schema": REWARD_LINK_SCHEMA, "source": source.as_json(),
            "carrier_lock_key": carrier, "construction_roster_sha256": roster_sha,
            "projection": projection.as_json(), "native_score_vector": row_vector,
            "provenance": provenance,
        }
        links.append(RewardLink(source, carrier, roster_sha, projection,
                                row_vector, provenance, content_hash(unsigned)))
    return tuple(links)


def verify_reward_links(links, manifest_path, score_receipt,
                        construction_roster_path, projection):
    """Reverify source artifacts, full roster order and every link's contents."""
    expected = build_reward_links(manifest_path, score_receipt, construction_roster_path, projection)
    given = tuple(links)
    if [link.as_json() for link in given] != [link.as_json() for link in expected]:
        raise RewardLinkError("reward links differ from verified source artifacts")
    return expected


def build_experience_sources(manifest_path, score_receipt, construction_roster_path, projection):
    """Convert a freshly verified source bundle once for the complete roster."""
    return tuple(link.source for link in build_reward_links(
        manifest_path, score_receipt, construction_roster_path, projection,
    ))


def verify_experience_sources(links, manifest_path, score_receipt,
                              construction_roster_path, projection):
    """Convert stored links only after one full source-bound verification."""
    return tuple(link.source for link in verify_reward_links(
        links, manifest_path, score_receipt, construction_roster_path, projection,
    ))


build_reward_link = build_reward_links
build_reward_link_sources = build_experience_sources
__all__ = [
    "REWARD_LINK_SCHEMA", "REWARD_PROJECTION_SCHEMA", "SLURP_NATIVE_FIELDS",
    "RewardLink", "RewardLinkError", "RewardProjection", "build_experience_sources",
    "build_reward_link", "build_reward_link_sources", "build_reward_links", "verify_reward_links",
    "verify_experience_sources",
]
