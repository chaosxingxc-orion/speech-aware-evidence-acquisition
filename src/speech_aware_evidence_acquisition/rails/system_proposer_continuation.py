"""Prospective serialized continuation bounds; preserve oversize evidence and stop.

These are client acceptance bounds after a metered completion. They do not cap
provider generation or promise that arbitrary artifact reads finish in four calls.
Legacy admissions without this explicitly registered factor keep their semantics.
"""
from .system_text_policy import canonical, require

LIMITS = {"provider_output_items_bytes": 4096, "tool_result_bytes": 4096}


def require_limits(limits):
    if limits is not None:
        require(isinstance(limits, dict) and limits == LIMITS
            and all(type(v) is int for v in limits.values()), "invalid continuation envelope")


def checked_output(output, limits):
    require_limits(limits)
    if limits is not None:
        require(len(canonical(output).encode("utf-8")) <= limits["provider_output_items_bytes"],
            "provider continuation exceeds registered serialized envelope")


def checked_tool(supplied, call_id, limits):
    require_limits(limits)
    item = {"type": "function_call_output", "call_id": call_id, "output": canonical(supplied)}
    if limits is not None:
        require(len(canonical(item).encode("utf-8")) <= limits["tool_result_bytes"],
            "artifact continuation exceeds registered serialized envelope")
    return item


def audit_envelope(capsule_document):
    """Rehearse three maximal accepted serialized turns and a final request.

    Placeholder history is a byte envelope, not a claim about an artifact's value
    or a future provider output. Charge every preceding input its entire bound.
    Output usage1000 per tool turn is explicit; output exhaustion still stops.
    """
    import copy
    from .hashing import content_hash
    from .system_proposer_capsule import ProposerCapsule
    from .system_proposer_capacity import request_bound
    capsule = ProposerCapsule.from_json(copy.deepcopy(capsule_document))
    packet = capsule_document["packet"]
    history = copy.deepcopy(capsule.request()["input"])
    rows, charged, previous, sizes = [], 0, 0, []
    for index in range(4):
        remaining = packet["input_token_cap"] - charged
        if remaining <= 0:
            break
        request = capsule.request(history=history, remaining_input=remaining,
            remaining_output=packet["output_token_cap"] - 1000 * index,
            previous_input_tokens=previous, remaining_contacts=4 - index)
        bound = request_bound(request)
        rows.append({"contact": index + 1, "request_sha256": content_hash(request),
            "input_token_bound": bound, "remaining_input_tokens": remaining, "fits": bound <= remaining})
        if bound > remaining or index == 3:
            break
        output = [{"type": "reasoning", "encrypted_content": ""},
            {"type": "function_call", "call_id": f"envelope-{index}", "name": "read_artifact",
             "arguments": canonical({"artifact_id": "0" * 64, "offset": 0, "limit": 2048})}]
        output[0]["encrypted_content"] = "x" * (4096 - len(canonical(output).encode("utf-8")))
        checked_output(output, LIMITS)
        supplied = {"text": ""}
        item = checked_tool(supplied, f"envelope-{index}", LIMITS)
        supplied["text"] = "x" * (4096 - len(canonical(item).encode("utf-8")))
        item = checked_tool(supplied, f"envelope-{index}", LIMITS)
        sizes = [len(canonical(output).encode("utf-8")), len(canonical(item).encode("utf-8"))]
        require(sizes == [4096, 4096], "synthetic envelope size differs")
        history.extend(output)
        history.append(item)
        charged += bound
        previous = bound
    return {"schema": "saea-proposer-continuation-envelope-audit-v1", "actual_contacts": 0,
        "status": "covered_envelope_fits" if len(rows) == 4 and all(r["fits"] for r in rows) else "input_budget_exceeded",
        "capsule_sha256": content_hash(capsule_document), "requests": rows,
        "cumulative_request_bounds": sum(r["input_token_bound"] for r in rows),
        "input_cap": packet["input_token_cap"], "continuation_item_sizes": sizes,
        "assumed_output_per_tool_turn": 1000, "final_output_reserve": packet["output_token_cap"] - 3000,
        "scope": "Four requests with three maximal accepted serialized continuations. Placeholder history is not task evidence.",
        "limitations": "No arbitrary tool completion or matched-compute claim. Actual usage and outputs remain independently gated."}
