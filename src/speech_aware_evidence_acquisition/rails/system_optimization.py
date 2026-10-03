"""Scoped repeated TRAIN optimization within the existing text-policy pipeline.

No function dispatches, opens task results, admits a runtime or relaxes a held-out
reader. Owner224 permits feedback reuse on one pinned pool, not knowledge leakage.
"""

import json

from .hashing import content_hash
from .system_text_policy import (
    _read_pin,
    assert_roster_disjoint,
    cumulative_sources,
    require,
    sha,
    validate_sources,
)

OWNER224 = "docs/receipts/owner/2026-10-02-decision224-fixed400-context-postcall.json"
PILOT = "pilot20-owner220"
LEARNING_MEMBERS = {"L-parent", "L-parent-aa", "L-candidate-1", "L-candidate-2"}
SELECTION_SCHEMA = "saea-exploratory-learning-selection-v1"


def load_optimization_panel(protocol, stage, *, repo_root):
    """Resolve the exact owner-approved metadata before any candidate is staged."""
    block = protocol.get("optimization_panel")
    if block is None:
        return None
    allowed_stages = {"update-1", "update-2", "update-3"}
    extension = protocol.get("allocation_extension")
    if extension is not None:
        from .system_search_allocations import require_round
        require_round(extension.get("round"), extension)
        owner = json.loads(_read_pin(extension["owner"], repo_root))
        from .system_search_successor import SCHEMA as SUCCESSOR
        decision_id = 227 if extension["schema"] == SUCCESSOR else 223
        require(owner.get("decision_id") == decision_id and owner.get("status") == "approved",
                "extended context scope requires its exact registered owner")
        allowed_stages.add(f"update-{extension['round']}")
    require(
        isinstance(block, dict)
        and set(block) == {"plan", "stages", "editable"}
        and isinstance(block["stages"], list)
        and block["stages"]
        and len(set(block["stages"])) == len(block["stages"])
        and set(block["stages"]) <= allowed_stages
        and block["editable"] == ["role_text"],
        "invalid context optimization scope",
    )
    if stage not in block["stages"]:
        return None
    plan = json.loads(_read_pin(block["plan"], repo_root))
    require(
        plan.get("schema") == "saea-fixed-optimization-panel-plan-v1"
        and plan.get("scientific_role") == "optimization-only"
        and plan.get("no_runtime_authority") is True
        and plan.get("source_rows") == 400,
        "fixed panel must be an optimization-only plan",
    )
    require(plan["owner"]["relpath"] == OWNER224, "exact owner224 receipt required")
    owner = json.loads(_read_pin(plan["owner"], repo_root))
    require(
        owner.get("decision_id") == 224
        and owner.get("status") == "approved"
        and owner.get("fixed_roster") == plan["source_roster"]
        and owner.get("fixed_runtime_view") == plan["source_runtime_view"]
        and owner.get("sample_ids_sha256") == plan["sample_ids_sha256"]
        and owner.get("progressive_sizes") == [20, 50, 100, 200, 400],
        "owner224 panel identity differs",
    )
    roster = json.loads(_read_pin(plan["source_roster"], repo_root))
    view = json.loads(_read_pin(plan["source_runtime_view"], repo_root))
    ids = roster["sample_ids"]
    require(
        isinstance(ids, list)
        and len(ids) == len(set(ids)) == 400
        and all(isinstance(s, str) and s.startswith("slurp:train:") for s in ids)
        and content_hash(ids) == plan["sample_ids_sha256"]
        and [r["sample_id"] for r in view["items"]] == ids
        and view["count"] == roster["count"] == 400,
        "fixed pool identity or partition differs",
    )
    require(
        [s["rows"] for s in plan["stages"]] == [20, 50, 100, 200, 400],
        "fixed panel ladder differs",
    )
    for s in plan["stages"]:
        require(
            s["selection"] == "existing-ordered-roster-prefix"
            and s["start"] == 0
            and s["stop_exclusive"] == s["rows"]
            and s["sample_ids_sha256"] == content_hash(ids[: s["rows"]])
            and s["purpose"] == "reused-optimization-panel"
            and s["independent_validation"] is False,
            "fixed panel prefix differs",
        )
    return plan, ids


def assert_policy_roster(sources, sample_ids, *, protocol, stage, repo_root):
    """Permit retained learning exposure only for an explicit optimization stage."""
    resolved = load_optimization_panel(protocol, stage, repo_root=repo_root)
    if resolved is None:
        assert_roster_disjoint(sources, sample_ids)
        return None
    from .system_search_protocol import stage_for

    plan, pool = resolved
    require(
        len(sample_ids) in (20, 50, 100, 200, 400)
        and list(sample_ids) == pool[: len(sample_ids)]
        and list(sample_ids) == stage_for(protocol, stage)["sample_ids"],
        "candidate must use the exact registered fixed-pool prefix",
    )
    validate_sources(list(sources))
    immutable = [s for s in sources if s["kind"] in {"knowledge", "construction"}]
    assert_roster_disjoint(immutable, sample_ids)

    def utterance(sid):
        return ":".join(sid.split(":")[:3])

    evaluated = {utterance(s) for s in sample_ids}
    overlap = sorted(
        evaluated.intersection(
            utterance(sid) for s in sources for sid in s["sample_ids"]
        )
    )
    return {
        "purpose": "reused-optimization-panel",
        "independent_validation": False,
        "pool_sha256": plan["sample_ids_sha256"],
        "rows": len(sample_ids),
        "overlap_utterances": overlap,
    }


def require_context_only_changes(changes, *, protocol, stage, repo_root):
    if load_optimization_panel(protocol, stage, repo_root=repo_root) is not None:
        require(
            isinstance(changes, dict) and set(changes) <= {"role_text"},
            "this context optimization cycle freezes construction, knowledge and supply",
        )


def exploratory_selection(feedback, *, registration, binding, protocol, parents):
    """Record the root's provisional parent without posing as a formal retention."""
    d = feedback.as_json()
    own = {
        cid: v
        for cid, v in registration["member_bindings"].items()
        if cid in LEARNING_MEMBERS
    }
    active = [binding["parent_id"], *binding["complementary_ids"]]
    require(
        set(own) == LEARNING_MEMBERS
        and 1 <= len(active) <= 2
        and len(set(active)) == len(active)
        and set(active) <= {v["bundle_id"] for v in own.values()},
        "exploratory parent must be an observed learning-branch policy",
    )
    ids = sorted(
        {g["sample_id"] for g in d["feedback"]["groups"]}
        | set(d["reference"]["sample_ids"])
    )
    sources = cumulative_sources(
        [],
        [s for p in parents for s in p["cumulative_sources"]]
        + [{"kind": "feedback", "sha256": content_hash(d), "sample_ids": ids}],
    )
    result = {
        "schema": SELECTION_SCHEMA,
        "stage": d["family_id"],
        "branch": "L",
        "next_round": binding["next_round"],
        "formal_adoption": False,
        "protocol_sha256": content_hash(protocol),
        "binding_sha256": protocol["exploratory_learning"]["sha256"],
        "active_ids": active,
        "feedback_sha256": d["read_gate_family_sha256"],
        "learning_feedback_sha256": content_hash(d),
        "member_bindings": own,
        "cumulative_sources": sources,
    }
    result["selection_sha256"] = content_hash(result)
    return result


def require_exploratory_packet(packet, *, protocol=None):
    """Check the small-family commitment at packaging and again before transport."""
    d, s = packet.get("feedback", {}), packet.get("selection", {})
    rows, read_id = 20, "SAEA-SLURP-SYSTEM-TEXT-PILOT20-OWNER220-READ-V1"
    family = d.get("family_id")
    if family != PILOT:
        scope = require_panel_scope(d)
        rows, read_id = scope["rows"], scope["read_id"]
        require(type(packet.get("round")) is int and packet["round"] > scope["proposal_round"],
                "a panel can inform only a later prospectively allocated round")
        require(d.get("learning_allowance_sha256") == scope["growth_owner_sha256"],
                "panel learning allowance differs")
        reference = d.get("reference", {})
        require(len(reference.get("sample_ids", [])) >= 400
                and all(sid.startswith("slurp:train:") for sid in reference["sample_ids"]),
                "panel must preserve the frozen TRAIN reference")
    require(
        packet.get("branch") == "L"
        and d.get("schema") == "saea-exploratory-system-feedback-v1"
        and d.get("optimizer_feedback_allowed") is True
        and d.get("formal_adoption") is False
        and d.get("read_authority", {}).get("read_run_id")
        == read_id,
        "exact exploratory learning authority required",
    )
    require(
        set(d.get("summaries", {})) == LEARNING_MEMBERS
        and set(d["feedback"]["candidate_ids"]) == LEARNING_MEMBERS
        and len(d["feedback"]["sources"]) == 4
        and {v["candidate_id"] for v in d["feedback"]["sources"]} == LEARNING_MEMBERS,
        "exploratory feedback must contain every L member and no blind evidence",
    )
    groups = d["feedback"]["groups"]
    require(
        len(groups) == len({g["sample_id"] for g in groups}) == rows
        and all(
            g["sample_id"].startswith("slurp:train:")
            and len(g["members"]) == 4
            and {m["candidate_id"] for m in g["members"]} == LEARNING_MEMBERS
            for g in groups
        ),
        "exploratory feedback must keep all registered complete L trajectories",
    )
    require(
        s.get("schema") == SELECTION_SCHEMA
        and s.get("stage") == family
        and s.get("branch") == "L"
        and s.get("formal_adoption") is False
        and type(packet.get("round")) is int
        and packet["round"] == s.get("next_round")
        and (packet["round"] == 3 or (packet["round"] > 3 and "allocation_extension_sha256" in packet))
        and s.get("selection_sha256")
        == content_hash({k: v for k, v in s.items() if k != "selection_sha256"})
        and s.get("protocol_sha256") == packet.get("protocol_sha256")
        and s.get("feedback_sha256") == d.get("read_gate_family_sha256")
        and s.get("learning_feedback_sha256") == content_hash(d)
        and s.get("active_ids", [None])[0] == packet.get("parent_bundle_id")
        and set(s.get("member_bindings", {})) == LEARNING_MEMBERS,
        "exploratory selection binding differs",
    )
    if family != PILOT:
        require(all(
            all(source.get(k) == s["member_bindings"][source["candidate_id"]].get(k)
                for k in ("run_id", "attempt_id", "config_hash"))
            and source["run_id"] == panel_member_run_id(scope["proposal_round"], rows, source["candidate_id"])
            for source in d["feedback"]["sources"]),
            "panel learning sources differ from the observed selection")
    require(
        set(s["active_ids"]) <= {v["bundle_id"] for v in s["member_bindings"].values()}
        and {content_hash(p) for p in packet.get("complementary_policies", [])}
        <= set(s["active_ids"][1:]),
        "exploratory parent or complementary policy differs",
    )
    validate_sources(s["cumulative_sources"])
    exposed = {
        sid for source in s["cumulative_sources"] for sid in source["sample_ids"]
    }
    require(
        {g["sample_id"] for g in groups} | set(d["reference"]["sample_ids"]) <= exposed,
        "exploratory feedback ancestry is incomplete",
    )
    if packet["round"] > 3:
        from .system_search_allocations import require_packet_round_shape, require_packet_allocation
        require_packet_round_shape(packet)
        if protocol is not None:
            require_packet_allocation(packet, protocol)
    if protocol is not None:
        require(
            packet["protocol_sha256"] == content_hash(protocol)
            and s["binding_sha256"]
            == protocol.get("exploratory_learning", {}).get("sha256"),
            "exploratory protocol binding differs",
        )


def require_optimization_scope(packet, *, protocol=None):
    """Keep the same declared search scope in both isolated proposer branches."""
    scope = packet.get("optimization_scope")
    if scope is not None:
        from .system_text_policy import sha

        require(
            isinstance(scope, dict)
            and set(scope) == {"purpose", "editable", "plan_sha256"}
            and scope["purpose"] == "reused-optimization-panel"
            and scope["editable"] == ["role_text"],
            "optimization input scope differs",
        )
        sha(scope["plan_sha256"])
    if protocol is not None:
        block = protocol.get("optimization_panel")
        expected = None
        if block is not None and f"update-{packet['round']}" in block["stages"]:
            expected = {
                "purpose": "reused-optimization-panel",
                "editable": block["editable"],
                "plan_sha256": block["plan"]["sha256"],
            }
        require(scope == expected, "optimization scope differs from the protocol")


PANEL_SIZES = (20, 50, 100, 200, 400)


def panel_identities(round_index, rows):
    """Reserve fresh comparison/read identities without granting execution."""
    require(type(round_index) is int and round_index >= 4,
            "fixed-pool panel requires an extended proposal round")
    require(type(rows) is int and rows in PANEL_SIZES,
            "fixed-pool panel size is outside the reviewed ladder")
    return (
        f"fixed400-text-round{round_index}-n{rows}-v1",
        f"SAEA-SLURP-SYSTEM-TEXT-FIXED400-ROUND{round_index}-N{rows}-READ-V1",
    )


def panel_member_run_id(round_index, rows, candidate_id):
    """Keep every candidate, parent and A/A separately bound to its panel."""
    _, read_id = panel_identities(round_index, rows)
    require(candidate_id in {f"{b}-{m}" for b in ("L", "B")
            for m in ("parent", "parent-aa", "candidate-1", "candidate-2")},
            "unknown fixed-pool panel member")
    return read_id.removesuffix("READ-V1") + candidate_id.upper() + "-V1"


def require_panel_scope(document):
    """Validate shared source commitments without exporting blind identities."""
    scope = document.get("panel_scope", {})
    family, read_id = panel_identities(scope.get("proposal_round"), scope.get("rows"))
    require(set(scope) == {"family_id", "proposal_round", "rows", "read_id",
            "registration_sha256", "pool_sample_ids_sha256", "prefix_sample_ids_sha256",
            "proposal_protocol_sha256", "pool_owner_sha256", "growth_owner_sha256"},
            "panel scope commitments differ")
    for key, value in scope.items():
        if key.endswith("sha256"):
            sha(value)
    require(document.get("family_id") == scope["family_id"] == family
            and document.get("registration_sha256") == scope["registration_sha256"]
            and document.get("read_authority", {}).get("read_run_id") == scope["read_id"] == read_id,
            "panel evidence scope differs")
    sha(document.get("read_authority", {}).get("ledger_row_sha256"))
    groups = document.get("feedback", {}).get("groups", [])
    ids = [g["sample_id"] for g in groups]
    require(len(ids) == len(set(ids)) == scope["rows"]
            and all(isinstance(s, str) and s.startswith("slurp:train:") for s in ids)
            and content_hash(ids) == scope["prefix_sample_ids_sha256"],
            "panel feedback prefix differs")
    return scope
