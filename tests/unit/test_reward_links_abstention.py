"""Keep canonical native abstention in complete-system reward and cost lineage."""
import copy
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest
import test_reward_links as reward_fixtures

from speech_aware_evidence_acquisition.core.bundle import verify_bundle
from speech_aware_evidence_acquisition.core.delivery import (
    native_abstention_records, native_seal_refusal_abstention_records,
)
from speech_aware_evidence_acquisition.rails.reward_links import (
    RewardLinkError, _trace, build_reward_links,
)

bundled_repo = reward_fixtures.bundled_repo
completed_source = reward_fixtures.completed_source


def abstain_first(rows, outputs, *, reason="finite_completion"):
    """End the first synthetic episode at its first interrupted Solver."""
    sid = outputs[0]["sample_id"]
    requests = [row for row in rows if row["channel"] == "MODEL_REQUEST"
                and row["payload"]["payload"]["sample_id"] == sid]
    kept = {row["record_id"].removesuffix("/request") for row in requests[:2]}
    all_requests = {row["record_id"].removesuffix("/request") for row in requests}
    contacts = []
    for row in requests[:2]:
        rid = row["record_id"].removesuffix("/request")
        response = next(r["payload"] for r in rows if r["record_id"] == rid + "/response")
        control = next(x for x in reversed(row["payload"]["payload"]["history"])
                       if x["role"] == "control")
        contacts.append({"request_id": rid, "agent_contact_id": control["contact_id"],
                         "request_sha256": row["payload"]["payload_sha256"],
                         **{k: response[k] for k in ("response_sha256", "response_text_sha256")}})
    visits = [{"role_id": "perception", "stage": "perception", "execution_receipt": {
        "contacts": contacts[:1], "final_contact": contacts[0]}}]
    disposition = {"reason": reason, "role_id": "solver", "stage": "solver",
                   "revision_count": 0, "planner_accepted": False,
                   "rejected_contact": contacts[-1]}
    if reason == "finite_completion":
        disposition["finish_reason"] = "length"
        rid, request, response = native_abstention_records(
            sample_id=sid, source_contact=contacts[-1], finish_reason="length")
    else:
        disposition["seal_refusal"] = {"error_class": "RailsError", "message": "Synthetic refusal."}
        rid, request, response = native_seal_refusal_abstention_records(
            sample_id=sid, source_contact=contacts[-1], seal_refusal=disposition["seal_refusal"])
    receipt = {"role_visits": visits, "planner_routes": [], "terminal_disposition": disposition,
               "interrupted_role": {"role_id": "solver", "stage": "solver", "execution_receipt": {
                   "contacts": contacts[1:], "final_contact": contacts[-1]}},
               "abstention_receipt": {"source_contact": contacts[-1]}}
    rows = [row for row in rows if not row["record_id"].startswith(sid + "/")
            and not any(row["record_id"].startswith(r + "/") for r in all_requests - kept)]
    rows.extend([
        {"channel": "TOOL", "record_id": rid + "/request", "payload": request},
        {"channel": "TOOL", "record_id": rid + "/response", "payload": response},
        {"channel": "USE", "record_id": sid + "/synthetic-program/agent-loop/runtime-use",
         "payload": {"use_contacts": [{"plan": {"contact_id": c["agent_contact_id"]},
                                       "response_sha256": c["response_text_sha256"]} for c in contacts],
                     "use_final_response_sha256": response["response_text_sha256"],
                     "use_waves": [{"contact_plans": [{"contact_id": c["agent_contact_id"]}],
                                    "response_sha256s": [c["response_text_sha256"]],
                                    "selected_final_contact_id": None} for c in contacts]}}])
    outputs[0] = {**outputs[0], "request_id": rid, "text": "", "native_episode_receipt": receipt,
                  **{k: response[k] for k in ("request_sha256", "response_sha256", "response_text_sha256")}}
    return rows, outputs


@pytest.fixture(params=("finite_completion", "seal_refusal"))
def abstained_source(completed_source, tmp_path, request):
    return reward_fixtures._slurp_source(completed_source, tmp_path, "native", native_framework=True,
                         trace_transform=lambda rows, outputs: abstain_first(rows, outputs, reason=request.param))


def test_verified_abstention_keeps_every_row_native_count_and_model_contact(abstained_source):
    path, ref, roster, projection, native = abstained_source
    bundle = verify_bundle(path)
    before = {p: p.read_bytes() for p in (path, bundle.outputs_path, Path(bundle.manifest["raw_trace"]["path"]))}
    links = build_reward_links(path, ref, roster, projection)
    assert len(links) == 2
    assert links[0].source.response_sha256 == hashlib.sha256(b"").hexdigest()
    assert links[0].native_score_vector["per_sample"][native[0]["sample_id"]] == {key: native[0][key] for key in projection.per_sample_fields}
    events, _ = _trace(bundle, set(bundle.split_ids), Path(bundle.manifest["raw_trace"]["path"]).read_bytes())
    first = events[bundle.outputs_rows[0]["sample_id"]]
    assert sum(e["axis"] == "MODEL_REQUEST" for e in first) == 2
    assert sum(e["axis"] == "MODEL_RESPONSE" for e in first) == 2
    assert len([e for e in first if "/delivery/" in e["record_id"]]) == 2
    assert all(p.read_bytes() == value for p, value in before.items())


@pytest.mark.parametrize("defect", ["missing_receipt", "forged_contact", "cross_sample",
    "missing_derivative", "forged_derivative", "duplicate_derivative", "false_selection", "missing_runtime_contact", "forged_role"])
def test_abstention_refuses_broken_custody(abstained_source, defect):
    path, *_ = abstained_source
    bundle = verify_bundle(path)
    rows = [json.loads(line) for line in Path(bundle.manifest["raw_trace"]["path"]).read_text().splitlines()]
    outputs = copy.deepcopy(bundle.outputs_rows)
    output = outputs[0]
    sid, rid = output["sample_id"], output["request_id"]
    receipt = output["native_episode_receipt"]
    if defect == "missing_receipt":
        del output["native_episode_receipt"]
    elif defect == "forged_contact":
        # Forge all receipt references consistently; exact transport custody must still fail.
        for contact in [receipt["abstention_receipt"]["source_contact"], receipt["terminal_disposition"]["rejected_contact"],
                        receipt["interrupted_role"]["execution_receipt"]["final_contact"],
                        receipt["interrupted_role"]["execution_receipt"]["contacts"][0]]:
            contact["request_sha256"] = "f" * 64
    elif defect == "cross_sample":
        output["sample_id"] = outputs[1]["sample_id"]
    elif defect == "forged_role":
        receipt["role_visits"][0]["role_id"] = "reviewer"
        receipt["role_visits"][0]["stage"] = "review"
    elif defect == "missing_derivative":
        rows = [row for row in rows if row["record_id"] != rid + "/response"]
    elif defect == "forged_derivative":
        next(row for row in rows if row["record_id"] == rid + "/request")["payload"]["policy"] = "forged"
    elif defect == "duplicate_derivative":
        rows.append(next(row for row in rows if row["record_id"] == rid + "/response"))
    else:
        payload = next(row["payload"] for row in rows if row["record_id"] == sid + "/synthetic-program/agent-loop/runtime-use")
        if defect == "false_selection":
            payload["use_waves"][0]["selected_final_contact_id"] = receipt["abstention_receipt"]["source_contact"]["agent_contact_id"]
        else:
            payload["use_contacts"].pop()
    modified = replace(bundle, outputs_rows=outputs, trace_records={row["record_id"]: row["payload"] for row in rows})
    raw = ("\n".join(json.dumps(row) for row in rows) + "\n").encode()
    with pytest.raises(RewardLinkError):
        _trace(modified, set(bundle.split_ids), raw)
