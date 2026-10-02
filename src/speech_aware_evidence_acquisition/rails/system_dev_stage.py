"""Bind the four frozen endpoint systems to the registered DEV regression cohort."""
import json
import os
import re
from pathlib import Path

from .hashing import content_hash
from .system_search_protocol import stage_for
from .system_text_policy import assert_roster_disjoint, cumulative_sources, require, sha

SCHEMA = "saea-system-search-dev-registration-v1"
SLOTS = {"seed", "seed-aa", "L-frozen", "B-frozen"}


def validate_dev_registration(d, *, protocol=None):
    """Validate fixed endpoint membership; this is neither a READ nor runtime admission."""
    require(isinstance(d, dict) and set(d) == {"schema", "stage", "protocol_sha256", "roster_sha256",
        "rows", "expected_members", "finalists", "evaluation", "trajectory_cap", "official_score_jobs_cap",
        "runtime_admission", "registration_sha256"}, "DEV registration fields differ")
    require(d["schema"] == SCHEMA and d["stage"] == "dev" and d["runtime_admission"] == "separate-required",
            "invalid DEV registration")
    require(d["registration_sha256"] == content_hash({k: v for k, v in d.items() if k != "registration_sha256"}),
            "DEV registration changed")
    for key in ("protocol_sha256", "roster_sha256"):
        sha(d[key])
    members = d["expected_members"]
    require(set(members) == SLOTS and len(set(members.values())) == 4 and all(
        isinstance(r, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,240}", r) for r in members.values()),
        "DEV requires four distinct confined run identities including seed A/A")
    require(type(d["rows"]) is int and d["rows"] == 1000 and d["trajectory_cap"] == 4000
            and d["official_score_jobs_cap"] == 4, "DEV budget differs")
    f = d["finalists"]
    require(set(f) == {"schema", "protocol_sha256", "feedback_sha256", "selections", "members",
        "dev_roster_sha256", "cumulative_sources", "status", "runtime_admission", "freeze_sha256"}
        and f["schema"] == "saea-system-search-finalists-v1"
        and f["status"] == "frozen-for-dev-not-adopted" and f["runtime_admission"] == "separate-required",
        "finalists fields or status differ")
    require(f["freeze_sha256"] == content_hash({k: v for k, v in f.items() if k != "freeze_sha256"})
        and f["protocol_sha256"] == d["protocol_sha256"] and f["dev_roster_sha256"] == d["roster_sha256"],
        "finalists protocol, roster or identity differs")
    require(set(f["members"]) == SLOTS and set(f["selections"]) == {"L", "B"}, "finalists membership differs")
    for identity in [f["feedback_sha256"], *f["members"].values(), *f["selections"].values()]:
        sha(identity)
    require(f["members"]["seed"] == f["members"]["seed-aa"], "DEV seed A/A differs")
    require(f["cumulative_sources"] == cumulative_sources([], f["cumulative_sources"]),
            "finalists cumulative exposure differs")
    e = d["evaluation"]
    require(set(e) == {"schema", "stage", "protocol_sha256", "member_bindings"}
        and e["schema"] == "saea-system-search-evaluation-binding-v1" and e["stage"] == "dev"
        and e["protocol_sha256"] == d["protocol_sha256"] and set(e["member_bindings"]) == SLOTS,
        "DEV evaluation binding differs")
    for cid, b in e["member_bindings"].items():
        require(set(b) == {"bundle_id", "run_id", "config_hash"}
            and b["run_id"] == members[cid] and b["bundle_id"] == f["members"][cid],
            "DEV policy differs from its frozen finalist")
        sha(b["config_hash"])
    if protocol is not None:
        stage = stage_for(protocol, "dev")
        ids = stage["sample_ids"]
        require(d["protocol_sha256"] == content_hash(protocol) and set(stage["member_slots"]) == SLOTS
            and content_hash(ids) == stage["roster_sha256"] == d["roster_sha256"]
            and len(ids) == len(set(ids)) == 1000 and all(s.startswith("slurp:devel:") for s in ids)
            and d["trajectory_cap"] == stage["trajectory_cap"]
            and d["official_score_jobs_cap"] == stage["official_score_jobs_cap"]
            and f["members"]["seed"] == protocol["seed_bundle"]["bundle_id"],
            "DEV differs from the frozen protocol or seed")
        required = {sid for name in ("initial", "update-1", "update-2", "update-3", "selection")
                    for sid in stage_for(protocol, name)["sample_ids"]}
        require(required <= {sid for s in f["cumulative_sources"] for sid in s["sample_ids"]},
                "finalists lost historical evaluation exposure")
        assert_roster_disjoint(f["cumulative_sources"], ids)
    return d


def verified_finalists(archive, *, protocol, selection_feedback):
    """Recheck saved choices against freshly gated common-cohort evidence."""
    saved = json.loads((archive.root / "finalists.json").read_text())
    require(saved == archive.finalists_document(protocol=protocol, feedback=selection_feedback),
            "frozen finalists differ from reverified common selection")
    return saved


def compile_dev_member(archive, *, protocol, selection_feedback, member, baseline,
                       cohort_binding, repo_root, staging_root, data_root):
    """Compile an already frozen system, rebinding inputs through the shared path."""
    from .system_text_policy import compile_system_text_policy
    from .system_text_cohort import bind_system_text_cohort
    require(member in SLOTS, "unknown frozen DEV member")
    f = verified_finalists(archive, protocol=protocol, selection_feedback=selection_feedback)
    bundle = archive.load_policy(f["members"][member])
    assert_roster_disjoint(bundle.as_json()["cumulative_sources"], stage_for(protocol, "dev")["sample_ids"])
    compiled = compile_system_text_policy(baseline, bundle, repo_root=repo_root,
        output_root=staging_root, data_root=data_root)
    return bind_system_text_cohort(compiled, cohort_binding, protocol=protocol, stage="dev",
                                  repo_root=repo_root, data_root=data_root)


def freeze_dev_stage(archive, *, protocol, selection_feedback, member_bindings, data_root):
    """Publish the original four-member regression recipe before contact; never dispatch."""
    require(not (archive.root / "stages/dev.json").exists(), "DEV registration already exists")
    f = verified_finalists(archive, protocol=protocol, selection_feedback=selection_feedback)
    require(set(member_bindings) == SLOTS, "DEV requires every frozen member")
    d = {"schema": SCHEMA, "stage": "dev", "protocol_sha256": content_hash(protocol),
        "roster_sha256": content_hash(stage_for(protocol, "dev")["sample_ids"]), "rows": 1000,
        "expected_members": {cid: b["run_id"] for cid, b in member_bindings.items()}, "finalists": f,
        "evaluation": {"schema": "saea-system-search-evaluation-binding-v1", "stage": "dev",
            "protocol_sha256": content_hash(protocol), "member_bindings": member_bindings},
        "trajectory_cap": 4000, "official_score_jobs_cap": 4, "runtime_admission": "separate-required"}
    d["registration_sha256"] = content_hash(d)
    validate_dev_registration(d, protocol=protocol)
    require(all(not os.path.lexists(Path(data_root) / directory / run)
                for run in d["expected_members"].values() for directory in ("runs", "attempts")),
            "cannot freeze DEV after a prospective run has artifacts or an attempt")
    for identity in f["members"].values():
        assert_roster_disjoint(archive.load_policy(identity).as_json()["cumulative_sources"],
                              stage_for(protocol, "dev")["sample_ids"])
    archive._write("stages/dev.json", d)
    return d
