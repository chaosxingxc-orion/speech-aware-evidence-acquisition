"""Validate one prospective multi-branch authoring response through shared proposals.

Allocation, source READ, materialization and runtime admission remain separate.
Never repair, replace or select away an invalid original branch here.
"""
from .hashing import content_hash
from .system_text_policy import TextPolicyUpdateProposal, require, _text

def validate_population_response(response, request, *, input_hashes):
    """Bind all16 whole-system proposals to the exact four-by-four design."""
    require(isinstance(response, dict) and set(response) == {
        "schema", "strategies", "branches", "provenance", "usage"}
        and response["schema"] == "saea-template-population-response-v1", "population response schema differs")
    provenance = response["provenance"]
    require(provenance == {"input_hashes": input_hashes, "model": "gpt-6.1-sol", "reasoning_effort": "high"},
            "exact isolated actor input provenance required")
    usage = response["usage"]
    require(isinstance(usage, dict) and set(usage) == {"provider_contacts", "input_tokens", "output_tokens"}
            and all(v is None or type(v) is int and v >= 0 for v in usage.values()), "provider usage differs")
    strategies = response["strategies"]
    require(isinstance(strategies, list) and len(strategies) == 4, "four strategy descriptions required")
    for i, strategy in enumerate(strategies):
        require(isinstance(strategy, dict) and set(strategy) == {"strategy_id", "mechanism", "tradeoff"}
                and strategy["strategy_id"] == f"strategy-{i+1}", "strategy order or identity differs")
        _text(strategy["mechanism"])
        _text(strategy["tradeoff"])
    expected = [{"candidate_id": f"branch-{i*4+j+1:02d}", "strategy_id": f"strategy-{i+1}",
                 "assembly_profile": key} for i in range(4) for j, key in enumerate("ABCD")]
    require(request["slots"] == expected, "registered population must contain all16 exact slots")
    rows = response["branches"]
    require(isinstance(rows, list) and len(rows) == 16, "all16 original branches required")
    perception = request["qualified_own_history"]["policies"][request["common_parent_candidate"]]["policy"]["role_text"]["perception"]
    result, hashes, strategy_hashes = [], set(), []
    for slot, row in zip(expected, rows, strict=True):
        require(isinstance(row, dict) and set(row) == {"strategy_id", "assembly_profile", "proposal"}
                and all(row[k] == slot[k] for k in ("strategy_id", "assembly_profile")), "branch order or design differs")
        proposal = TextPolicyUpdateProposal.from_context_json(row["proposal"])
        p = proposal.as_json()
        require(p["candidate_id"] == slot["candidate_id"] and p["algorithm"] == "tf-grpo-context-diversity"
                and p["iteration"] == 1 and p["component"] == "joint-system"
                and p["parent_ids"] == [request["common_parent_bundle_id"]]
                and p["evidence"] == [request["input_sha256"]], "proposal identity, parent or evidence differs")
        changes = p["changes"]
        require(set(changes) == {"role_text", "context_layout", "node_context"}
                and set(changes["role_text"]) == {"perception", "solver", "reviewer", "planner"}
                and changes["role_text"]["perception"] == perception, "complete consumption scope or fixed Perception differs")
        profile = request["assembly_profiles"][slot["assembly_profile"]]
        require(all(changes[k] == profile[k] for k in ("context_layout", "node_context")), "registered assembly profile differs")
        identity = content_hash(changes)
        require(identity not in hashes, "duplicate effective context system")
        hashes.add(identity)
        if slot["assembly_profile"] == "A":
            strategy_hashes.append(content_hash({r: changes["role_text"][r] for r in ("solver", "reviewer")}))
        result.append(proposal)
    require(len(set(strategy_hashes)) == 4, "strategy rows need distinct Solver/Reviewer designs")
    return result
