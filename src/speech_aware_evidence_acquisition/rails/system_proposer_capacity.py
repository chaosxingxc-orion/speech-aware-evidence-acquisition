"""Audit explicit continuation scenarios without provider or dispatch authority.

Usage is an assumption, not a tokenizer measurement or a provider observation.
Each scenario covers only its enumerated tool turns and the following request.
Actual provider usage, final-output size and different model choices remain unknown.
"""
from __future__ import annotations

import copy

from .hashing import content_hash
from .system_proposer_capsule import ProposerCapsule, SUBSCRIPTION_BUDGET
from .system_proposer_responses import _output, strict_json
from .system_text_policy import canonical, require
from .system_proposer_continuation import checked_output, checked_tool, require_limits


def request_bound(request):
    """Use the registered full-request UTF-8 byte bound plus its fixed reserve."""
    return len(canonical(request).encode("utf-8")) + 4096


def audit_scenario(capsule_document, scenario):
    """Reproduce retained history on a private capsule; never reserve a contact."""
    require(isinstance(scenario, dict) and (set(scenario) == {"schema", "contact_cap", "turns"}
                 or set(scenario) == {"schema", "contact_cap", "turns", "continuation_limits"})
            and scenario["schema"] == "saea-proposer-capacity-scenario-v1", "invalid capacity scenario")
    limits = scenario.get("continuation_limits")
    require_limits(limits)
    cap, turns = scenario["contact_cap"], scenario["turns"]
    require(type(cap) is int and 1 <= cap <= 4, "invalid scenario contact cap")
    require(isinstance(turns, list) and len(turns) < cap, "scenario requires a following request slot")
    capsule = ProposerCapsule.from_json(copy.deepcopy(capsule_document))
    packet = capsule.as_json()["packet"]
    seen, validated = set(), []
    for turn in turns:
        require(isinstance(turn, dict) and set(turn) == {"output", "assumed_input_tokens", "assumed_output_tokens"},
                "invalid scenario turn")
        require(all(type(turn[key]) is int and turn[key] >= 0
                    for key in ("assumed_input_tokens", "assumed_output_tokens")), "invalid assumed usage")
        calls, _ = _output(turn, seen, subscription=packet.get("budget_profile") == SUBSCRIPTION_BUDGET)
        require(len(calls) == 1, "scenario turn must request one registered artifact")
        validated.append((calls[0], strict_json(calls[0]["arguments"])))

    report = {"schema": "saea-proposer-capacity-audit-v1", "status": "covered_requests_fit",
              "capsule_sha256": content_hash(capsule_document), "scenario_sha256": content_hash(scenario),
              "proposal_input_sha256": packet["input_sha256"], "branch": packet["branch"],
              "round": packet["round"], "slot": packet["slot"], "model_version": packet["model_version"],
              "view_profile": capsule_document.get("view_profile", "full-index-v1"),
              "contact_cap": cap, "input_token_cap": packet["input_token_cap"],
              "output_token_cap": packet["output_token_cap"], "usage_kind": "assumed_not_measured",
              "actual_contacts": 0, "dispatch_authority": False, "requests": [], "artifact_reads": [],
              "first_failed_contact": None,
              "limitations": ["Only the enumerated continuation and its assumed usage are covered.",
                  "Future model output, different tool choices and actual provider usage are unknown.",
                  "A fitting request does not prove completion or provide runtime admission."]}
    history = copy.deepcopy(capsule.request()["input"])
    total_input = total_output = previous_input = assessed = 0
    for index in range(len(turns) + 1):
        input_left = packet["input_token_cap"] - total_input
        output_left = packet["output_token_cap"] - total_output
        if input_left <= 0 or output_left <= 0:
            report["status"] = "input_budget_exceeded" if input_left <= 0 else "output_budget_exhausted"
            report["first_failed_contact"] = index + 1
            break
        request = capsule.request(remaining_output=output_left, remaining_input=input_left,
            history=history, remaining_contacts=cap - index, previous_input_tokens=previous_input)
        bound = request_bound(request)
        fits = bound <= input_left
        report["requests"].append({"contact": index + 1, "request_sha256": content_hash(request),
            "input_token_bound": bound, "remaining_input_tokens": input_left,
            "remaining_output_tokens": output_left, "remaining_contacts": cap - index,
            "margin_tokens": input_left - bound, "fits": fits})
        if not fits:
            report["status"], report["first_failed_contact"] = "input_budget_exceeded", index + 1
            break
        if index == len(turns):
            break
        turn = turns[index]
        require(turn["assumed_input_tokens"] <= bound, "assumed input exceeds the request bound")
        total_input += turn["assumed_input_tokens"]
        total_output += turn["assumed_output_tokens"]
        previous_input = turn["assumed_input_tokens"]
        assessed += 1
        if turn["assumed_output_tokens"] > output_left:
            report["status"], report["first_failed_contact"] = "assumed_output_exceeds_allowance", index + 1
            break
        checked_output(turn["output"], limits)
        tool, arguments = validated[index]
        supplied = capsule.read_artifact(arguments)
        report["artifact_reads"].append({"after_contact": index + 1, "arguments": copy.deepcopy(arguments),
            "artifact_sha256": supplied["sha256"], "response_sha256": content_hash(supplied),
            "characters": len(supplied["text"]), "next_offset": supplied["next_offset"], "eof": supplied["eof"]})
        # Match ResponsesProposer's exact whole-item custody, including reasoning.
        history.extend(copy.deepcopy(turn["output"]))
        history.append(checked_tool(supplied, tool["call_id"], limits))
    report["assumed_usage"] = {"input_tokens": total_input, "output_tokens": total_output}
    report["covered_requests"] = len(report["requests"])
    report["unassessed_turns"] = len(turns) - assessed
    return report
