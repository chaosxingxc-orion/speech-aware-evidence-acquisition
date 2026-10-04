"""Scoped repeated TRAIN optimization within the existing text-policy pipeline.

No function dispatches, opens task results, admits a runtime or relaxes a held-out
reader. Owner224 permits feedback reuse on one pinned pool, not knowledge leakage.
"""

import json

from .hashing import content_hash
from .system_text_policy import (
    _read_pin,
    _pin,
    assert_roster_disjoint,
    cumulative_sources,
    require,
    sha,
    validate_sources,
)

OWNER224 = "docs/receipts/owner/2026-10-02-decision224-fixed400-context-postcall.json"
CONTEXT_AUTHORITY = "docs/receipts/owner/2026-10-03-context-space-and-node-timing-amendment.json"
CONTEXT_SCOPE_SCHEMA = "saea-context-layout-search-scope-v2"
NODE_SCOPE_SCHEMA = "saea-node-context-search-scope-v3"
NODE_AUTHORITY = "docs/receipts/owner/2026-10-04-node-optimization-space.json"
CONTEXT_SCOPES = (CONTEXT_SCOPE_SCHEMA, NODE_SCOPE_SCHEMA)
PILOT = "pilot20-owner220"
LEARNING_MEMBERS = {"L-parent", "L-parent-aa", "L-candidate-1", "L-candidate-2"}
SUCCESSOR_MEMBERS = {f"{b}-{m}" for b in ("L", "B") for m in ("parent", "parent-aa", "candidate-2")}
SUCCESSOR_EXCLUDED = {"L-candidate-1", "B-candidate-1"}
SUCCESSOR_REGISTRATION = "saea-successor-system-panel-registration-v1"
SUCCESSOR_SIZES = (20, 50, 100, 200)
SELECTION_SCHEMA = "saea-exploratory-learning-selection-v1"
BOOTSTRAP_SELECTION_SCHEMA = "saea-historical-seed-selection-v1"


def editable_for_scope(schema):
    return (["role_text", "context_layout", "node_context"] if schema == NODE_SCOPE_SCHEMA else
            ["role_text", "context_layout"] if schema == CONTEXT_SCOPE_SCHEMA else ["role_text"])


def validate_context_authority(pin, *, repo_root, node_version=False):
    expected = NODE_AUTHORITY if node_version else CONTEXT_AUTHORITY
    require(pin.get("relpath") == expected, "exact context-space owner receipt required")
    authority = json.loads(_read_pin(pin, repo_root))
    schema = "saea-owner-node-optimization-space-v1" if node_version else "saea-owner-context-space-amendment-v1"
    require(authority.get("schema") == schema
            and authority.get("gpu_dispatch_authorized_by_this_record") is False
            and authority.get("new_human_permission_required_within_owner227") is False,
            "context-space owner authority differs")
    return authority


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
        from .system_search_successor import SCHEMAS as SUCCESSORS
        decision_id = 227 if extension["schema"] in SUCCESSORS else 223
        require(owner.get("decision_id") == decision_id and owner.get("status") == "approved",
                "extended context scope requires its exact registered owner")
        allowed_stages.add(f"update-{extension['round']}")
    context_version = isinstance(block, dict) and block.get("schema") in CONTEXT_SCOPES
    fields = {"plan", "stages", "editable"}
    if context_version:
        fields |= {"schema", "context_authority"}
    require(
        isinstance(block, dict)
        and set(block) == fields
        and isinstance(block["stages"], list)
        and block["stages"]
        and len(set(block["stages"])) == len(block["stages"])
        and set(block["stages"]) <= allowed_stages
        and block["editable"] == editable_for_scope(block.get("schema")),
        "invalid context optimization scope",
    )
    if context_version:
        validate_context_authority(block["context_authority"], repo_root=repo_root,
                                   node_version=block.get("schema") == NODE_SCOPE_SCHEMA)
    if extension is not None:
        require(block["editable"] == extension["editable"]
                and block.get("context_authority") == extension.get("context_authority"),
                "context scope differs from its registered allocation")
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
            isinstance(changes, dict) and set(changes) <= set(protocol["optimization_panel"]["editable"]),
            "this context optimization cycle freezes construction, knowledge and supply",
        )


def require_historical_bootstrap(value, *, feedback, parent, own, round_index, protocol=None):
    """Keep qualified old evidence separate from a new measured policy sequence."""
    from .system_search_measurement import validate_profile
    from .system_text_policy import NODE_BUNDLE_SCHEMA
    require(isinstance(value, dict) and set(value) == {
        "schema", "round", "seed_transition", "previous_parent_id", "seed_bundle_id",
        "source_projection_sha256", "prospective_measurement_profile"}
        and value["schema"] == "saea-historical-seed-bootstrap-v1",
        "exact historical bootstrap descriptor required")
    _pin(value["seed_transition"])
    for key in ("previous_parent_id", "seed_bundle_id", "source_projection_sha256"):
        sha(value[key])
    validate_profile(value["prospective_measurement_profile"])
    require(type(value["round"]) is int and value["round"] == round_index and round_index > 3
            and content_hash(feedback) == value["source_projection_sha256"]
            and "measurement_profile" not in feedback,
            "historical bootstrap is restricted to its unchanged unmeasured source and round")
    require(set(own) == LEARNING_MEMBERS
            and own["L-parent"]["bundle_id"] == value["previous_parent_id"]
            and own["L-parent-aa"]["bundle_id"] == value["previous_parent_id"]
            and parent.get("schema") == NODE_BUNDLE_SCHEMA
            and content_hash(parent) == value["seed_bundle_id"]
            and parent.get("parent_ids") == [value["previous_parent_id"]]
            and not parent.get("optimizer_experience")
            and all(s["kind"] == "knowledge" for s in parent.get("cumulative_sources", [])),
            "historical observations cannot be relabeled as the new seed")
    if protocol is not None:
        from .system_search_successor import SEED_SCHEMA
        extension = protocol.get("allocation_extension", {})
        require(protocol.get("historical_bootstrap") == value
                and protocol.get("measurement_profile") == value["prospective_measurement_profile"]
                and extension.get("schema") == SEED_SCHEMA
                and extension.get("round") == round_index
                and extension.get("seed_bundle_id") == value["seed_bundle_id"]
                and extension.get("seed_transition", {}).get("parent_bundle_id") == value["previous_parent_id"]
                and extension.get("seed_transition", {}).get("receipt") == value["seed_transition"],
                "historical bootstrap lacks the exact seed-transition protocol authority")
    return value


def exploratory_selection(feedback, *, registration, binding, protocol, parents):
    """Record the root's provisional parent without posing as a formal retention."""
    d = feedback.as_json()
    learning_members = learning_members_for_document(d)
    if learning_members != LEARNING_MEMBERS:
        require(registration.get("schema") == SUCCESSOR_REGISTRATION
            and registration.get("registration_sha256") == d["registration_sha256"],
            "successor retention must bind its exact qualified registration")
    own = {
        cid: v
        for cid, v in registration["member_bindings"].items()
        if cid in learning_members
    }
    active = [binding["parent_id"], *binding["complementary_ids"]]
    bootstrap = protocol.get("historical_bootstrap") if learning_members == LEARNING_MEMBERS else None
    if bootstrap is not None:
        require(len(parents) == 1 and active == [content_hash(parents[0])],
                "historical bootstrap retains only the explicit transitioned seed")
        require_historical_bootstrap(bootstrap, feedback=d, parent=parents[0], own=own,
                                     round_index=binding["next_round"], protocol=protocol)
    require(
        set(own) == learning_members
        and 1 <= len(active) <= 2
        and len(set(active)) == len(active)
        and (bootstrap is not None or set(active) <= {v["bundle_id"] for v in own.values()}),
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
    profile = protocol.get("measurement_profile")
    if bootstrap is not None:
        result.update(schema=BOOTSTRAP_SELECTION_SCHEMA,
                      historical_bootstrap=json.loads(json.dumps(bootstrap)))
        profile = None
    require(d.get("measurement_profile") == profile, "exploratory measurement profile differs")
    if profile is not None:
        from .system_search_measurement import measured_rows, measured_frontier
        measured = measured_rows(d, [c for c in ("L-parent", "L-candidate-1", "L-candidate-2")
            if c in learning_members], own, profile=profile)
        unique, repeats, seen = [], [], set()
        for row in measured:
            (repeats if row["bundle_id"] in seen else unique).append(row)
            seen.add(row["bundle_id"])
        frontier = measured_frontier(unique, profile=profile)
        fallback = active == [own["L-parent"]["bundle_id"]]
        require(fallback or set(active) <= {r["bundle_id"] for r in frontier},
                "exploratory candidates must be eligible and non-dominated")
        result.update(measurement_profile=profile, measurements=unique, repeated_measurements=repeats,
                      frontier=frontier, retain_parent=fallback,
                      same_chain_aa={"candidate_id": "L-parent-aa", **d["summaries"]["L-parent-aa"]})
    result["selection_sha256"] = content_hash(result)
    return result


def require_exploratory_packet(packet, *, protocol=None):
    """Check the small-family commitment at packaging and again before transport."""
    d, s = packet.get("feedback", {}), packet.get("selection", {})
    learning_members = learning_members_for_document(d)
    if learning_members != LEARNING_MEMBERS:
        require(s.get("member_bindings") == d["successor_bindings"],
                "successor selection differs from the qualified own member bindings")
    bootstrap = s.get("schema") == BOOTSTRAP_SELECTION_SCHEMA
    if bootstrap:
        require(not packet.get("complementary_policies")
                and s.get("active_ids") == [packet.get("parent_bundle_id")]
                and not {"measurement_profile", "measurements", "frontier", "repeated_measurements"}.intersection(s),
                "historical bootstrap has no new measured frontier or complementary selection")
        require_historical_bootstrap(s.get("historical_bootstrap"), feedback=d,
            parent=packet.get("parent_policy", {}), own=s.get("member_bindings", {}),
            round_index=packet.get("round"), protocol=protocol)
    else:
        require("historical_bootstrap" not in s, "bootstrap cannot borrow a measured selection schema")
    rows, read_id = 20, "SAEA-SLURP-SYSTEM-TEXT-PILOT20-OWNER220-READ-V1"
    family = d.get("family_id")
    if family != PILOT:
        scope = require_panel_scope(d)
        rows, read_id = scope["rows"], scope["read_id"]
        require(type(packet.get("round")) is int and packet["round"] > scope["proposal_round"],
                "a panel can inform only a later prospectively allocated round")
        learning_owner_key = "learning_owner_sha256" if scope.get("evaluation_schema") == SUCCESSOR_REGISTRATION else "growth_owner_sha256"
        require(d.get("learning_allowance_sha256") == scope[learning_owner_key],
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
        set(d.get("summaries", {})) == learning_members
        and set(d["feedback"]["candidate_ids"]) == learning_members
        and len(d["feedback"]["sources"]) == len(learning_members)
        and {v["candidate_id"] for v in d["feedback"]["sources"]} == learning_members,
        "exploratory feedback must contain every L member and no blind evidence",
    )
    groups = d["feedback"]["groups"]
    require(
        len(groups) == len({g["sample_id"] for g in groups}) == rows
        and all(
            g["sample_id"].startswith("slurp:train:")
            and len(g["members"]) == len(learning_members)
            and {m["candidate_id"] for m in g["members"]} == learning_members
            for g in groups
        ),
        "exploratory feedback must keep all registered complete L trajectories",
    )
    require(
        s.get("schema") in (SELECTION_SCHEMA, BOOTSTRAP_SELECTION_SCHEMA)
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
        and set(s.get("member_bindings", {})) == learning_members,
        "exploratory selection binding differs",
    )
    if family != PILOT:
        require(all(
            all(source.get(k) == s["member_bindings"][source["candidate_id"]].get(k)
                for k in ("run_id", "attempt_id", "config_hash"))
            and source["run_id"] == panel_member_run_id(scope["proposal_round"], rows, source["candidate_id"],
                successor=scope.get("evaluation_schema") == SUCCESSOR_REGISTRATION)
            for source in d["feedback"]["sources"]),
            "panel learning sources differ from the observed selection")
    require(
        (bootstrap or set(s["active_ids"]) <= {v["bundle_id"] for v in s["member_bindings"].values()})
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
    require(s.get("measurement_profile") == d.get("measurement_profile"),
            "learning selection and feedback measurement profiles differ")
    if protocol is not None and not bootstrap:
        require(s.get("measurement_profile") == protocol.get("measurement_profile"),
                "learning measurement profile differs from frozen protocol")
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


def optimization_scope_for(protocol, round_index):
    """Project the registered scope identically into either isolated branch."""
    block = protocol.get("optimization_panel")
    if block is None or f"update-{round_index}" not in block["stages"]:
        return None
    scope = {"purpose": "reused-optimization-panel", "editable": list(block["editable"]),
             "plan_sha256": block["plan"]["sha256"]}
    if block.get("schema") in CONTEXT_SCOPES:
        scope.update(schema=block["schema"],
                     context_authority_sha256=block["context_authority"]["sha256"])
    require_optimization_scope({"optimization_scope": scope})
    return scope


def require_optimization_scope(packet, *, protocol=None):
    """Keep the same declared search scope in both isolated proposer branches."""
    scope = packet.get("optimization_scope")
    if scope is not None:
        from .system_text_policy import sha

        context_version = isinstance(scope, dict) and scope.get("schema") in CONTEXT_SCOPES
        fields = {"purpose", "editable", "plan_sha256"}
        if context_version:
            fields |= {"schema", "context_authority_sha256"}
        require(
            isinstance(scope, dict)
            and set(scope) == fields
            and scope["purpose"] == "reused-optimization-panel"
            and scope["editable"] == editable_for_scope(scope.get("schema")),
            "optimization input scope differs",
        )
        sha(scope["plan_sha256"])
        if context_version:
            sha(scope["context_authority_sha256"])
    if protocol is not None:
        expected = optimization_scope_for(protocol, packet["round"])
        require(scope == expected, "optimization scope differs from the protocol")


PANEL_SIZES = (20, 50, 100, 200, 400)


def panel_identities(round_index, rows, *, successor=False):
    """Reserve fresh comparison/read identities without granting execution."""
    require(type(round_index) is int and round_index >= 4,
            "fixed-pool panel requires an extended proposal round")
    require(type(rows) is int and rows in PANEL_SIZES,
            "fixed-pool panel size is outside the reviewed ladder")
    if successor:
        require(rows in SUCCESSOR_SIZES, "successor panel stops before400")
        return (f"fixed400-successor-round{round_index}-n{rows}-v1",
                f"SAEA-SLURP-SYSTEM-TEXT-SUCCESSOR-FIXED400-ROUND{round_index}-N{rows}-READ-V1")
    return (
        f"fixed400-text-round{round_index}-n{rows}-v1",
        f"SAEA-SLURP-SYSTEM-TEXT-FIXED400-ROUND{round_index}-N{rows}-READ-V1",
    )


def panel_member_run_id(round_index, rows, candidate_id, *, successor=False):
    """Keep every candidate, parent and A/A separately bound to its panel."""
    _, read_id = panel_identities(round_index, rows, successor=successor)
    require(candidate_id in {f"{b}-{m}" for b in ("L", "B")
            for m in ("parent", "parent-aa", "candidate-1", "candidate-2")},
            "unknown fixed-pool panel member")
    return read_id.removesuffix("READ-V1") + candidate_id.upper() + "-V1"


def load_successor_panel_authority(pin, *, protocol, pool_ids, rows, repo_root):
    """Resolve explicit owner227 evaluation scope without changing proposal custody."""
    from .system_search_successor import OWNER227, SCHEMAS
    d = json.loads(_read_pin(pin, repo_root))
    require(set(d) == {"schema", "reviewer", "status", "owner227", "growth_owner_decision",
        "learning_owner_decision", "proposal_protocol_sha256", "proposal_round", "pool_sample_ids_sha256",
        "admitted_members", "excluded_members", "progressive_sizes", "new_proposal_opportunities",
        "automatic_expansion", "independent_validation", "formal_adoption"}, "successor evaluation authority fields differ")
    root = json.loads(_read_pin(d["owner227"], repo_root))
    growth = json.loads(_read_pin(d["growth_owner_decision"], repo_root))
    learning = json.loads(_read_pin(d["learning_owner_decision"], repo_root))
    extension = protocol.get("allocation_extension", {})
    require(d["schema"] == "saea-owner227-successor-panel-evaluation-v1"
        and d["status"] == "approved" and d["reviewer"] == "ChatGPT root"
        and d["owner227"].get("relpath") == OWNER227 and d["owner227"] == extension.get("owner")
        and extension.get("schema") in SCHEMAS and root.get("decision_id") == 227 and root.get("status") == "approved"
        and set(SUCCESSOR_SIZES) <= set(root.get("authorized_rows_per_member", []))
        and d["growth_owner_decision"] != d["owner227"]
        and growth.get("decision_id") == 223 and growth.get("status") == "approved"
        and growth.get("stage_ladder") == list(PANEL_SIZES)
        and learning.get("decision_id") == 222 and learning.get("status") == "approved"
        and learning.get("family_id") == PILOT and learning.get("allow_learning_feedback") is True
        and learning.get("recipient_branch") == "L" and learning.get("complete_family_required") is True
        and learning.get("formal_adoption") is False,
        "successor requires separate pinned owner227, growth223 and learning222 authority")
    require(d["proposal_protocol_sha256"] == content_hash(protocol)
        and type(d["proposal_round"]) is int and d["proposal_round"] == protocol.get("updates") == extension.get("round")
        and d["pool_sample_ids_sha256"] == content_hash(pool_ids)
        and d["admitted_members"] == sorted(SUCCESSOR_MEMBERS)
        and d["excluded_members"] == sorted(SUCCESSOR_EXCLUDED)
        and d["progressive_sizes"] == list(SUCCESSOR_SIZES) and rows in SUCCESSOR_SIZES
        and d["new_proposal_opportunities"] == 0 and d["automatic_expansion"] is False
        and d["independent_validation"] is False and d["formal_adoption"] is False,
        "successor authority differs from exact protocol, pool, membership or bounded ladder")
    return {"authority": d, "owner227": root, "learning": learning}, growth


def require_panel_scope(document):
    """Validate shared source commitments without exporting blind identities."""
    scope = document.get("panel_scope", {})
    successor = scope.get("evaluation_schema") == SUCCESSOR_REGISTRATION
    family, read_id = panel_identities(scope.get("proposal_round"), scope.get("rows"), successor=successor)
    fields = {"family_id", "proposal_round", "rows", "read_id",
            "registration_sha256", "pool_sample_ids_sha256", "prefix_sample_ids_sha256",
            "proposal_protocol_sha256", "pool_owner_sha256", "growth_owner_sha256"}
    if successor:
        fields |= {"evaluation_schema", "evaluation_authority_sha256", "learning_owner_sha256",
                   "root_custody_sha256", "custody_sha256", "root_bindings_sha256", "bindings_sha256"}
    require(set(scope) == fields,
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


def validate_successor_custody(custody, *, round_index, rows, own=False):
    """Keep hash custody for every spent slot, with only own-L details in a projection."""
    require(isinstance(custody, dict) and set(custody) == {"allocations", "exclusions"},
            "successor custody fields differ")
    branches = ("L",) if own else ("L", "B")
    expected = {f"{b}-candidate-{s}" for b in branches for s in (1, 2)}
    excluded = {f"{b}-candidate-1" for b in branches}
    require(set(custody["allocations"]) == expected and set(custody["exclusions"]) == excluded,
            "successor must retain every spent allocation and exact invalid exclusions")
    for cid, a in custody["allocations"].items():
        require(set(a) == {"input_sha256", "receipt_sha256", "import_sha256", "compilation_sha256", "status"},
                "successor allocation custody fields differ")
        for key in ("input_sha256", "receipt_sha256", "import_sha256"):
            sha(a[key])
        if cid in excluded:
            e = custody["exclusions"][cid]
            require(a["status"] == "invalid" and a["compilation_sha256"] is None
                and set(e) == {"status", "run_id", "attempt_id", "import_sha256"}
                and e["status"] == "invalid" and e["import_sha256"] == a["import_sha256"]
                and e["run_id"] == panel_member_run_id(round_index, rows, cid, successor=True)
                and isinstance(e["attempt_id"], str) and bool(e["attempt_id"]),
                "successor invalid exclusion identity or compilation differs")
        else:
            require(a["status"] in {"provisional", "duplicate", "no-change"},
                    "valid successor candidate cannot be excluded")
            sha(a["compilation_sha256"])


def learning_members_for_document(document):
    """Recognize only the independently qualified successor projection or legacy L4."""
    scope = document.get("panel_scope", {})
    if scope.get("evaluation_schema") != SUCCESSOR_REGISTRATION:
        require("successor_custody" not in document, "successor custody requires its explicit scope")
        return LEARNING_MEMBERS
    require_panel_scope(document)
    custody = document.get("successor_custody", {})
    validate_successor_custody(custody, round_index=scope["proposal_round"], rows=scope["rows"], own=True)
    require(content_hash(custody) == scope["custody_sha256"], "own successor custody hash differs")
    own = {c for c in SUCCESSOR_MEMBERS if c.startswith("L-")}
    require(set(document.get("successor_bindings", {})) == own
        and content_hash(document["successor_bindings"]) == scope["bindings_sha256"],
        "own successor member bindings differ")
    return own
