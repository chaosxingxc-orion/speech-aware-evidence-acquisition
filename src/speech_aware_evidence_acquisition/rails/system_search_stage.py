"""Freeze update membership before contact; never dispatch or relax a scored family."""

import json
import os
import re
from pathlib import Path

from .hashing import content_hash
from .system_search_protocol import stage_for
from .system_text_policy import (
    TextPolicyUpdateProposal,
    assert_roster_disjoint,
    require,
    sha,
)

SCHEMA = "saea-system-search-stage-registration-v1"
SLOTS = [
    f"{b}-{m}"
    for b in ("L", "B")
    for m in ("parent", "parent-aa", "candidate-1", "candidate-2")
]
PARENTS = {f"{b}-{m}" for b in ("L", "B") for m in ("parent", "parent-aa")}


def recipe_family_identity(recipe):
    """Resolve frozen recipe spellings without rewriting or weakening their pins.

    The admitted update recipe uses stage/members with an embedded immutable
    registration; earlier readers used family_id/expected_members. Accept the
    former only when all redundant identities and the evaluation binding agree.
    """
    if recipe.get("schema") == "saea-node-panel-schedule-analysis-v1":
        family = "node-panel-schedule-n20"
        layouts = [f"{layout}-{schedule}-pair{pair}" for schedule in ("trajectory", "panel")
                   for layout in ("legacy", "before-speech") for pair in (1, 2)]
        members = {f"{layout}-{repeat}": f"SAEA-SLURP-NODE-PANEL-SCHEDULE-N20-{layout.upper()}-{repeat.upper()}-V1"
                   for layout in layouts for repeat in ("primary", "aa")}
        expected = [{"layout": layout, **{repeat: members[f"{layout}-{repeat}"]
                                         for repeat in ("primary", "aa")}} for layout in layouts]
        require(recipe.get("comparisons") == expected
                and recipe.get("complete_family") == list(members.values())
                and recipe.get("run_ids", {}).get("read") == "SAEA-SLURP-NODE-PANEL-SCHEDULE-N20-READ-V1"
                and recipe.get("rows_per_member") == 20 and recipe.get("trajectory_cap") == 320
                and recipe.get("optimizer_export") is False
                and not {"stage", "members", "initial_members", "system_search_stage", "system_search_evaluation"}.intersection(recipe),
                "exact sixteen-member scheduling family differs or has ambiguous learning aliases")
    elif recipe.get("schema") == "saea-context-matrix-analysis-v1":
        family = "context-matrix-n20"
        layouts = ("legacy-trajectory", "before-speech-trajectory", "legacy-role", "before-speech-role")
        members = {f"{layout}-{repeat}": f"SAEA-SLURP-CONTEXT-MATRIX-N20-{layout.upper()}-{repeat.upper()}-V1"
                   for layout in layouts for repeat in ("primary", "aa")}
        expected = [{"layout": layout, **{repeat: members[f"{layout}-{repeat}"]
                                         for repeat in ("primary", "aa")}} for layout in layouts]
        require(recipe.get("comparisons") == expected
                and len(recipe.get("complete_family", [])) == 8
                and set(recipe["complete_family"]) == set(members.values())
                and recipe.get("run_ids", {}).get("read") == "SAEA-SLURP-CONTEXT-MATRIX-N20-READ-V1"
                and recipe.get("optimizer_export") is False
                and not {"stage", "members", "initial_members", "system_search_stage", "system_search_evaluation"}.intersection(recipe),
                "exact context engineering family differs or has ambiguous learning aliases")
    elif "stage" in recipe or "members" in recipe:
        require(
            recipe.get("schema") == "saea-system-text-analysis-recipe-v1"
            and {"stage", "members", "system_search_stage", "system_search_evaluation"}
            <= set(recipe)
            and "initial_members" not in recipe,
            "nested analysis recipe identity is incomplete or ambiguous",
        )
        registration = validate_stage_registration(recipe["system_search_stage"])
        family, members = registration["stage"], registration["expected_members"]
        require(
            recipe["stage"] == family and recipe["members"] == members
            and recipe["system_search_evaluation"] == registration["evaluation"],
            "nested analysis recipe differs from its frozen registration",
        )
    else:
        members = recipe.get("expected_members", recipe.get("initial_members"))
        family = "initial" if "initial_members" in recipe else recipe.get("family_id")
    require(
        ("family_id" not in recipe or recipe["family_id"] == family)
        and ("expected_members" not in recipe or recipe["expected_members"] == members)
        and ("initial_members" not in recipe or recipe["initial_members"] == members),
        "analysis recipe identity aliases disagree",
    )
    return family, members


def _response_invalid(packet, response, proposal_records, *, allocation_extension=None):
    """Recheck objective input/response faults; do not exclude a valid losing proposal."""
    try:
        require(
            set(response)
            == {
                "raw_response",
                "session_id",
                "model_version",
                "input_sha256",
                "input_tokens",
                "output_tokens",
            },
            "response fields differ",
        )
        for key in ("session_id", "model_version", "input_sha256"):
            require(response[key] == packet[key], "response identity differs")
        for record in proposal_records:
            if (record["branch"], record["round"], record["slot"]) == (
                packet["branch"],
                packet["round"],
                packet["slot"],
            ):
                continue
            require(
                record["receipt"]["session_id"] != response["session_id"]
                and record["receipt"]["model_version"] == response["model_version"],
                "proposal context/model reused",
            )
        proposal = TextPolicyUpdateProposal.from_json(
            json.loads(response["raw_response"]), allocation_extension=allocation_extension
        ).as_json()
        require(
            (proposal["branch"], proposal["round"], proposal["slot"])
            == (packet["branch"], packet["round"], packet["slot"]),
            "response allocation differs",
        )
        allowed = {packet["parent_bundle_id"]} | {
            content_hash(p) for p in packet.get("complementary_policies", [])
        }
        require(
            proposal["parent_ids"][0] == packet["parent_bundle_id"]
            and set(proposal["parent_ids"]) <= allowed,
            "response parent differs",
        )
        for field, cap in (
            ("input_tokens", "input_token_cap"),
            ("output_tokens", "output_token_cap"),
        ):
            value = response[field]
            require(
                value is None or type(value) is int and 0 <= value <= packet[cap],
                "response exceeds cap",
            )
    except (ValueError, TypeError, KeyError):
        return True
    return False


def validate_stage_registration(d, *, protocol=None):
    """Validate the exact recipe-bound membership; its publisher still needs admission."""
    if isinstance(d, dict) and d.get("schema") == "saea-system-search-dev-registration-v1":
        from .system_dev_stage import validate_dev_registration
        return validate_dev_registration(d, protocol=protocol)
    if isinstance(d, dict) and d.get("schema") == "saea-system-search-selection-registration-v1":
        from .system_selection_stage import validate_selection_registration
        return validate_selection_registration(d, protocol=protocol)
    require(
        isinstance(d, dict)
        and set(d)
        == {
            "schema",
            "stage",
            "protocol_sha256",
            "roster_sha256",
            "rows",
            "planned_runs",
            "expected_members",
            "allocations",
            "exclusions",
            "evaluation",
            "trajectory_cap",
            "official_score_jobs_cap",
            "proposal_opportunities_consumed",
            "runtime_admission",
            "registration_sha256",
        },
        "stage registration fields differ",
    )
    require(
        d["schema"] == SCHEMA
        and d["stage"] in {"update-1", "update-2", "update-3"}
        and d["runtime_admission"] == "separate-required",
        "invalid update registration",
    )
    require(
        d["registration_sha256"]
        == content_hash({k: v for k, v in d.items() if k != "registration_sha256"}),
        "stage registration changed",
    )
    for key in ("protocol_sha256", "roster_sha256"):
        sha(d[key])
    planned, members, excluded = (
        d["planned_runs"],
        d["expected_members"],
        d["exclusions"],
    )
    require(
        set(planned) == set(SLOTS)
        and len(set(planned.values())) == 8
        and all(
            isinstance(v, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,240}", v)
            for v in planned.values()
        ),
        "declare eight distinct confined prospective run identities",
    )
    require(
        PARENTS <= set(members)
        and set(members).isdisjoint(excluded)
        and set(members) | set(excluded) == set(SLOTS),
        "parent/A/A or proposal allocation is missing",
    )
    require(
        members == {cid: planned[cid] for cid in members},
        "admitted run identity differs",
    )
    require(
        type(d["rows"]) is int
        and d["rows"] == 400
        and d["trajectory_cap"] == 400 * len(members)
        and d["official_score_jobs_cap"] == len(members)
        and d["proposal_opportunities_consumed"] == 4,
        "stage budget differs",
    )
    allocations = d["allocations"]
    require(
        set(allocations) == set(SLOTS) - PARENTS,
        "all four spent proposal opportunities are required",
    )
    for cid, a in allocations.items():
        require(
            set(a)
            == {
                "input_sha256",
                "receipt_sha256",
                "import_sha256",
                "compilation_sha256",
                "status",
            },
            "proposal custody fields differ",
        )
        for key in ("input_sha256", "receipt_sha256", "import_sha256"):
            sha(a[key])
        if cid in excluded:
            require(
                a["status"] == "invalid"
                and a["compilation_sha256"] is None
                and excluded[cid]
                == {
                    "status": "invalid",
                    "run_id": planned[cid],
                    "import_sha256": a["import_sha256"],
                },
                "only a recorded pre-contact invalid proposal may be excluded",
            )
        else:
            require(
                a["status"] in {"provisional", "no-change", "duplicate"},
                "valid candidates must remain admitted",
            )
            sha(a["compilation_sha256"])
    evaluation = d["evaluation"]
    require(
        set(evaluation) == {"schema", "stage", "protocol_sha256", "member_bindings"}
        and evaluation["schema"] == "saea-system-search-evaluation-binding-v1"
        and evaluation["stage"] == d["stage"]
        and evaluation["protocol_sha256"] == d["protocol_sha256"],
        "evaluation stage binding differs",
    )
    bindings = evaluation["member_bindings"]
    require(set(bindings) == set(members), "evaluation omits admitted members")
    for cid, b in bindings.items():
        require(
            set(b) == {"bundle_id", "run_id", "config_hash"}
            and b["run_id"] == members[cid],
            "evaluation run/config binding differs",
        )
        sha(b["bundle_id"])
        sha(b["config_hash"])
    for branch in ("L", "B"):
        require(
            bindings[branch + "-parent"]["bundle_id"]
            == bindings[branch + "-parent-aa"]["bundle_id"],
            "same-chain A/A policy differs",
        )
    if protocol is not None:
        stage = stage_for(protocol, d["stage"])
        require(
            d["protocol_sha256"] == content_hash(protocol)
            and set(stage["member_slots"]) == set(SLOTS)
            and d["roster_sha256"] == content_hash(stage["sample_ids"])
            and d["rows"] == len(stage["sample_ids"])
            and d["trajectory_cap"] <= stage["trajectory_cap"],
            "stage differs from frozen protocol or cohort",
        )
        require(
            bindings["B-parent"]["bundle_id"] == protocol["seed_bundle"]["bundle_id"],
            "blind parent differs",
        )
    return d


def freeze_update_stage(archive, *, protocol, round_index, member_bindings, data_root):
    """Create an immutable registration input after proposals/compilation, before runs.

    Runtime config hashes are the coordinator's prospective composed identities;
    own supplies, FIT, exposure rows and launch admission remain separate gates.
    """
    require(
        type(round_index) is int and round_index in (1, 2, 3), "invalid update index"
    )
    name = f"update-{round_index}"
    stage = stage_for(protocol, name)
    require(
        protocol.get("proposer_exact_version") and set(member_bindings) == set(SLOTS),
        "pin proposer and account for every prospective slot",
    )
    require(
        not (archive.root / f"stages/{name}.json").exists(),
        "stage registration already exists",
    )
    run_ids = [b["run_id"] for b in member_bindings.values()]
    require(
        len(set(run_ids)) == 8
        and all(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,240}", r) for r in run_ids),
        "run identities must be distinct and confined",
    )
    require(
        all(not os.path.lexists(Path(data_root) / "runs" / r) for r in run_ids),
        "cannot freeze membership after any prospective run has artifacts",
    )

    def read(relative):
        return json.loads((archive.root / relative).read_text())

    allocations, excluded, bindings, parents = {}, {}, {}, {}
    proposal_records = archive.history()
    for branch in ("L", "B"):
        for slot in (1, 2):
            key = f"{branch}-{round_index}-{slot}"
            cid = f"{branch}-candidate-{slot}"
            packet = read(f"inputs/{key}.json")
            imported = read(f"imports/{key}.json")
            response = read(f"responses/{key}.json")
            require(
                packet["input_sha256"]
                == content_hash(
                    {k: v for k, v in packet.items() if k != "input_sha256"}
                )
                and packet["protocol_sha256"] == content_hash(protocol)
                and (packet["branch"], packet["round"], packet["slot"])
                == (branch, round_index, slot)
                and packet["model_version"] == protocol["proposer_exact_version"]
                and packet["seed_bundle_id"] == protocol["seed_bundle"]["bundle_id"]
                and packet["input_token_cap"] == protocol["proposal_input_token_cap"]
                and packet["output_token_cap"] == protocol["proposal_output_token_cap"],
                "frozen proposal input changed",
            )
            require(
                imported["proposal_allocation"] == [branch, round_index, slot]
                and imported.get("input_sha256") == packet["input_sha256"]
                and imported.get("receipt_sha256") == content_hash(response),
                "proposal response/disposition changed",
            )
            parent = packet["parent_bundle_id"]
            require(
                branch not in parents or parents[branch] == parent,
                "branch proposal parents disagree",
            )
            parents[branch] = parent
            if branch == "B" or round_index == 1:
                require(
                    parent == protocol["seed_bundle"]["bundle_id"],
                    "initial/blind parent must be seed",
                )
            else:
                selection = read(f"retentions/update-{round_index - 1}/L.json")
                require(
                    packet.get("selection") == selection
                    and selection["active_ids"][0] == parent
                    and selection["protocol_sha256"] == content_hash(protocol),
                    "learning parent differs from retention",
                )
            b = member_bindings[cid]
            a = {
                "input_sha256": packet["input_sha256"],
                "receipt_sha256": content_hash(response),
                "import_sha256": content_hash(imported),
                "status": imported["status"],
                "compilation_sha256": None,
            }
            if imported["status"] == "invalid":
                require(
                    _response_invalid(packet, response, proposal_records),
                    "invalid disposition is not supported by the response",
                )
                require(
                    b["bundle_id"] is None
                    and b["config_hash"] is None
                    and not (archive.root / f"compilations/{key}.json").exists(),
                    "invalid proposal cannot activate",
                )
                excluded[cid] = {
                    "status": "invalid",
                    "run_id": b["run_id"],
                    "import_sha256": a["import_sha256"],
                }
            else:
                require(
                    not _response_invalid(packet, response, proposal_records),
                    "invalid response cannot activate",
                )
                proposal = read(f"proposals/{key}.json")
                require(
                    proposal["receipt"] == response
                    and proposal["status"] == imported["status"],
                    "proposal record differs from exact response",
                )
                compiled = read(f"compilations/{key}.json")
                require(
                    compiled["allocation"] == [branch, round_index, slot]
                    and compiled["input_sha256"] == packet["input_sha256"]
                    and compiled["import_sha256"] == a["import_sha256"]
                    and compiled["bundle_id"] == b["bundle_id"],
                    "compiled candidate binding differs",
                )
                a["compilation_sha256"] = content_hash(compiled)
                bindings[cid] = dict(b)
            allocations[cid] = a
    for branch, parent in parents.items():
        for suffix in ("parent", "parent-aa"):
            cid = f"{branch}-{suffix}"
            require(
                member_bindings[cid]["bundle_id"] == parent,
                "branch comparator/A/A parent differs",
            )
            bindings[cid] = dict(member_bindings[cid])
    for b in bindings.values():
        assert_roster_disjoint(
            archive.load_policy(b["bundle_id"]).as_json()["cumulative_sources"],
            stage["sample_ids"],
        )
    d = {
        "schema": SCHEMA,
        "stage": name,
        "protocol_sha256": content_hash(protocol),
        "roster_sha256": content_hash(stage["sample_ids"]),
        "rows": len(stage["sample_ids"]),
        "planned_runs": {cid: member_bindings[cid]["run_id"] for cid in SLOTS},
        "expected_members": {
            cid: bindings[cid]["run_id"] for cid in SLOTS if cid in bindings
        },
        "allocations": allocations,
        "exclusions": excluded,
        "evaluation": {
            "schema": "saea-system-search-evaluation-binding-v1",
            "stage": name,
            "protocol_sha256": content_hash(protocol),
            "member_bindings": bindings,
        },
        "trajectory_cap": len(stage["sample_ids"]) * len(bindings),
        "official_score_jobs_cap": len(bindings),
        "proposal_opportunities_consumed": 4,
        "runtime_admission": "separate-required",
    }
    d["registration_sha256"] = content_hash(d)
    validate_stage_registration(d, protocol=protocol)
    archive._write(f"stages/{name}.json", d)
    return d



def freeze_optimization_panel(
    archive,
    *,
    protocol,
    round_index,
    rows,
    member_bindings,
    root_review,
    repo_root,
    data_root,
    evaluation_authority=None,
):
    """Freeze a reviewed extra-round eight-member definition, never launch it.

    Invalid/missing slots refuse this complete-panel path and stay spent; callers
    cannot replace or omit them. Runtime config hashes are prospective coordinator
    identities. Actual per-member policy/supply/FIT/admission remains required.
    """
    import copy
    from .system_search_allocations import validate_extension, require_packet_allocation
    from .system_search_archive import proposal_sources
    from .system_optimization import (
        load_optimization_panel,
        assert_policy_roster,
        panel_identities,
        panel_member_run_id,
        require_exploratory_packet,
        require_optimization_scope,
        require_context_only_changes,
        SUCCESSOR_MEMBERS, SUCCESSOR_EXCLUDED, SUCCESSOR_REGISTRATION,
        load_successor_panel_authority,
    )
    from .system_text_policy import _read_pin, apply_text_proposal
    from ..analysis.system_text_panel import REGISTRATION_SCHEMA, validate_definition

    profile = None
    if "measurement_profile" in protocol:
        from .system_search_measurement import validate_profile
        profile = copy.deepcopy(validate_profile(protocol["measurement_profile"]))

    successor = evaluation_authority is not None
    require(not successor or profile is not None, "successor panel requires measured profile")
    family, read_id = panel_identities(round_index, rows, successor=successor)
    relative = f"panels/{family}.json"
    require(
        not os.path.lexists(archive.root / relative),
        "panel registration already exists",
    )
    extension = archive.allocation_extension(round_index)
    require(
        extension == protocol.get("allocation_extension")
        and protocol.get("updates") == round_index,
        "exact registered extra proposal round required",
    )
    validate_extension(archive, extension, repo_root=repo_root)
    name = f"update-{round_index}"
    resolved = load_optimization_panel(protocol, name, repo_root=repo_root)
    require(
        resolved is not None and set(member_bindings) == set(SLOTS),
        "all eight members and the exact fixed pool are required",
    )
    plan, pool = resolved
    owner = json.loads(_read_pin(plan["owner"], repo_root))
    evaluation_scope = None
    if successor:
        evaluation_scope, growth = load_successor_panel_authority(evaluation_authority,
            protocol=protocol, pool_ids=pool, rows=rows, repo_root=repo_root)
    else:
        growth = json.loads(_read_pin(extension["owner"], repo_root))
    evaluation = copy.deepcopy(protocol)
    stage_for(evaluation, name)["sample_ids"] = pool[:rows]
    stage_for(evaluation, name)["roster_sha256"] = content_hash(pool[:rows])
    review = json.loads(_read_pin(root_review, repo_root))
    require(not successor or review.get("evaluation_authority") == evaluation_authority,
            "root review must pin exact successor evaluation authority")
    require(
        review.get("schema") == "saea-fixed400-panel-stage-review-v1"
        and review.get("reviewer") == "ChatGPT root"
        and review.get("status") == "completed"
        and review.get("family_id") == family
        and review.get("rows_per_member") == rows
        and review.get("proposal_protocol_sha256") == content_hash(protocol)
        and review.get("pool_sample_ids_sha256") == content_hash(pool)
        and review.get("member_bindings_sha256") == content_hash(member_bindings)
        and isinstance(review.get("rationale"), str)
        and review["rationale"].strip(),
        "exact completed root stage review is required",
    )
    previous_reads = review.get("prior_complete_read_ids")
    require(
        isinstance(previous_reads, list)
        and previous_reads
        and len(previous_reads) == len(set(previous_reads))
        and all(
            isinstance(r, str)
            and r.startswith("SAEA-SLURP-SYSTEM-TEXT-")
            and r.endswith("-READ-V1")
            and r != read_id
            for r in previous_reads
        ),
        "root review must name its already complete source reads",
    )
    for cid, b in member_bindings.items():
        require(
            set(b) == {"bundle_id", "run_id", "attempt_id", "config_hash"}
            and b["run_id"] == panel_member_run_id(round_index, rows, cid, successor=successor)
            and isinstance(b["attempt_id"], str)
            and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,240}", b["attempt_id"]),
            "exact confined prospective member identities required",
        )
        if successor and cid in SUCCESSOR_EXCLUDED:
            require(b["bundle_id"] is None and b["config_hash"] is None,
                    "excluded successor slots cannot activate a policy")
        else:
            sha(b["bundle_id"])
            sha(b["config_hash"])
    require(
        len({b["attempt_id"] for b in member_bindings.values()}) == 8,
        "panel attempts must be distinct",
    )

    def no_runtime_artifacts():
        require(
            all(
                not os.path.lexists(Path(data_root) / folder / b["run_id"])
                for b in member_bindings.values()
                for folder in ("runs", "attempts")
            ),
            "cannot freeze panel after any member has runtime artifacts",
        )

    no_runtime_artifacts()
    observed = {}

    def read(path):
        raw = (archive.root / path).read_bytes()
        observed[path] = raw
        return json.loads(raw)

    records = archive.history()
    allocations, parents, exclusions = {}, {}, {}
    for branch in ("L", "B"):
        for slot in (1, 2):
            key, cid = f"{branch}-{round_index}-{slot}", f"{branch}-candidate-{slot}"
            packet = read(f"inputs/{key}.json")
            imported = read(f"imports/{key}.json")
            response = read(f"responses/{key}.json")
            require_packet_allocation(packet, protocol)
            require(
                packet["input_sha256"]
                == content_hash(
                    {k: v for k, v in packet.items() if k != "input_sha256"}
                )
                and packet["protocol_sha256"] == content_hash(protocol)
                and (packet["branch"], packet["round"], packet["slot"])
                == (branch, round_index, slot)
                and packet["seed_bundle_id"] == protocol["seed_bundle"]["bundle_id"]
                and packet["model_version"] == protocol["proposer_exact_version"],
                "frozen panel proposal input changed",
            )
            require_optimization_scope(packet, protocol=protocol)
            if branch == "L":
                require_exploratory_packet(packet, protocol=protocol)
            else:
                require(
                    not any(
                        k in packet
                        for k in (
                            "feedback",
                            "selection",
                            "learning_history",
                            "complementary_policies",
                        )
                    )
                    and packet["parent_bundle_id"] == packet["seed_bundle_id"],
                    "blind parent or feedback isolation differs",
                )
            parent = packet["parent_bundle_id"]
            require(
                branch not in parents or parents[branch] == parent,
                "branch proposal parents differ",
            )
            parents[branch] = parent
            require(
                archive.load_policy(parent).as_json() == packet["parent_policy"],
                "proposal parent policy differs from archive",
            )
            if successor and cid in SUCCESSOR_EXCLUDED:
                require(imported["proposal_allocation"] == [branch, round_index, slot]
                    and imported["input_sha256"] == packet["input_sha256"]
                    and imported["receipt_sha256"] == content_hash(response)
                    and imported["status"] == "invalid"
                    and _response_invalid(packet, response, records, allocation_extension=extension)
                    and not os.path.lexists(archive.root / f"compilations/{key}.json"),
                    "only objectively invalid spent uncompiled slots may be excluded")
                invalid = read(f"proposals/{key}.json")
                require(invalid["receipt"] == response and invalid["status"] == "invalid"
                    and invalid["proposal"] is None, "invalid proposal custody differs")
                allocations[cid] = {"input_sha256": packet["input_sha256"],
                    "receipt_sha256": content_hash(response), "import_sha256": content_hash(imported),
                    "compilation_sha256": None, "status": "invalid"}
                exclusions[cid] = {"status": "invalid", "run_id": member_bindings[cid]["run_id"],
                    "attempt_id": member_bindings[cid]["attempt_id"], "import_sha256": content_hash(imported)}
                continue
            require(
                imported["proposal_allocation"] == [branch, round_index, slot]
                and imported["input_sha256"] == packet["input_sha256"]
                and imported["receipt_sha256"] == content_hash(response)
                and imported["status"] in {"no-change", "duplicate", "provisional"}
                and imported["metering_complete"] is True
                and all(
                    type(response[k]) is int for k in ("input_tokens", "output_tokens")
                )
                and not _response_invalid(
                    packet, response, records, allocation_extension=extension
                ),
                "missing, invalid or changed proposal cannot enter a complete panel",
            )
            proposal = read(f"proposals/{key}.json")
            require(
                proposal["receipt"] == response
                and proposal["status"] == imported["status"]
                and proposal["proposal"] == json.loads(response["raw_response"]),
                "panel proposal differs from exact response",
            )
            require_context_only_changes(
                proposal["proposal"]["changes"],
                protocol=protocol,
                stage=name,
                repo_root=repo_root,
            )
            compiled = read(f"compilations/{key}.json")
            require(
                compiled["allocation"] == [branch, round_index, slot]
                and compiled["input_sha256"] == packet["input_sha256"]
                and compiled["import_sha256"] == content_hash(imported)
                and compiled["bundle_id"] == member_bindings[cid]["bundle_id"],
                "panel policy differs from its spent compilation",
            )
            sha(compiled["configuration_sha256"])
            parsed = TextPolicyUpdateProposal.from_json(
                proposal["proposal"], allocation_extension=extension
            )
            rebuilt = apply_text_proposal(
                parsed,
                parents=[
                    archive.load_policy(b) for b in proposal["proposal"]["parent_ids"]
                ],
                added_sources=proposal_sources(packet, proposal),
            )
            require(
                rebuilt.as_json()
                == archive.load_policy(compiled["bundle_id"]).as_json(),
                "compiled policy no longer matches proposal and cumulative sources",
            )
            allocations[cid] = {
                "input_sha256": packet["input_sha256"],
                "receipt_sha256": content_hash(response),
                "import_sha256": content_hash(imported),
                "compilation_sha256": content_hash(compiled),
                "status": imported["status"],
            }
    for branch, parent in parents.items():
        require(
            all(
                member_bindings[branch + "-" + suffix]["bundle_id"] == parent
                for suffix in ("parent", "parent-aa")
            ),
            "panel comparator differs from proposal parent",
        )
    admitted = {cid: b for cid, b in member_bindings.items() if not successor or cid in SUCCESSOR_MEMBERS}
    exposure = {
        cid: assert_policy_roster(
            archive.load_policy(b["bundle_id"]).as_json()["cumulative_sources"],
            pool[:rows],
            protocol=evaluation,
            stage=name,
            repo_root=repo_root,
        )
        for cid, b in admitted.items()
    }
    d = {
        "schema": SUCCESSOR_REGISTRATION if successor else REGISTRATION_SCHEMA,
        "family_id": family,
        "proposal_round": round_index,
        "expected_members": {cid: b["run_id"] for cid, b in admitted.items()},
        "member_bindings": copy.deepcopy(admitted),
        "rows_per_member": rows,
        "trajectory_cap": len(admitted) * rows,
        "official_score_jobs_cap": len(admitted),
        "new_proposal_opportunities": 0,
        "owner_decisions": [223, 224],
        "read_id": read_id,
        "root_stage_review": "completed",
        "root_stage_review_receipt": copy.deepcopy(root_review),
        "independent_validation": False,
        "automatic_expansion": False,
        "scientific_role": "optimization-only",
        "proposal_protocol_sha256": content_hash(protocol),
        "pool_sample_ids_sha256": content_hash(pool),
        "prefix_sample_ids_sha256": content_hash(pool[:rows]),
        "allocations": allocations,
        "retained_exposure": exposure,
        "runtime_admission": "separate-required",
    }
    if profile is not None:
        d["measurement_profile"] = copy.deepcopy(profile)
    if successor:
        d.update(evaluation_authority=copy.deepcopy(evaluation_authority), exclusions=exclusions,
                 planned_runs={cid: b["run_id"] for cid, b in member_bindings.items()},
                 owner_decisions=[222, 223, 224, 227])
    d["registration_sha256"] = content_hash(d)
    recipe = {
        "family_id": family,
        "expected_members": d["expected_members"],
        "sample_ids": pool[:rows],
        "required_rows_per_member": rows,
        "run_ids": {"read": read_id},
    }
    if profile is not None:
        recipe["measurement_profile"] = copy.deepcopy(profile)
    validate_definition(
        recipe, d, owner, growth=growth, protocol=protocol, pool_ids=pool,
        **({"evaluation": evaluation_scope} if successor else {})
    )
    require(
        all((archive.root / p).read_bytes() == raw for p, raw in observed.items()),
        "proposal sources changed during freeze",
    )
    require(
        json.loads(_read_pin(root_review, repo_root)) == review,
        "root review changed during freeze",
    )
    validate_extension(archive, extension, repo_root=repo_root)
    if successor:
        require(load_successor_panel_authority(evaluation_authority, protocol=protocol,
            pool_ids=pool, rows=rows, repo_root=repo_root) == (evaluation_scope, growth),
            "successor evaluation authority changed during freeze")
    no_runtime_artifacts()
    result = {
        "registration": d,
        "recipe": recipe,
        "recipe_status": "identity-only; analysis registration still required",
    }
    archive._write(relative, result)
    return result
