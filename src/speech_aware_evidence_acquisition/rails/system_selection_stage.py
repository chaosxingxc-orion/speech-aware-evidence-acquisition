"""Freeze historical nominees for one common cohort, without ranking old cohorts."""

import os
import re
from pathlib import Path

from .hashing import content_hash
from .system_search_protocol import require_stage_feedback, stage_for
from .system_text_feedback import CompleteSystemFeedback
from .system_text_policy import assert_roster_disjoint, cumulative_sources, require, sha

SCHEMA = "saea-system-search-selection-registration-v1"
UPDATES = ("update-1", "update-2", "update-3")
SLOTS = ("seed", "seed-aa", "L-1", "L-2", "B-1", "B-2")
REQUIRED = {"seed", "seed-aa", "L-1", "B-1"}


def validate_selection_registration(d, *, protocol=None):
    """Validate the prospective recipe binding, not its scientific nomination merit."""
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
            "exclusions",
            "survivors",
            "retentions",
            "history_feedback_sha256",
            "cumulative_sources",
            "evaluation",
            "trajectory_cap",
            "official_score_jobs_cap",
            "runtime_admission",
            "registration_sha256",
        },
        "selection registration fields differ",
    )
    require(
        d["schema"] == SCHEMA
        and d["stage"] == "selection"
        and d["runtime_admission"] == "separate-required",
        "invalid selection registration",
    )
    require(
        d["registration_sha256"]
        == content_hash({k: v for k, v in d.items() if k != "registration_sha256"}),
        "selection registration changed",
    )
    sha(d["protocol_sha256"])
    sha(d["roster_sha256"])
    runs, members, excluded = d["planned_runs"], d["expected_members"], d["exclusions"]
    require(
        set(runs) == set(SLOTS)
        and len(set(runs.values())) == len(SLOTS)
        and all(
            isinstance(r, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,240}", r)
            for r in runs.values()
        ),
        "declare six distinct confined prospective run identities",
    )
    require(
        REQUIRED <= set(members)
        and set(members).isdisjoint(excluded)
        and set(members) | set(excluded) == set(SLOTS),
        "seed/A/A or a required branch nominee is missing",
    )
    require(
        members == {cid: runs[cid] for cid in members}, "selection run identity differs"
    )
    for cid, value in excluded.items():
        require(
            cid in {"L-2", "B-2"}
            and value == {"status": "not-nominated", "run_id": runs[cid]},
            "only an unused second nomination may be excluded before contact",
        )
    require(
        type(d["rows"]) is int
        and d["rows"] == 400
        and d["trajectory_cap"] == 400 * len(members)
        and d["official_score_jobs_cap"] == len(members),
        "selection budget differs",
    )
    require(
        set(d["survivors"])
        == set(d["retentions"])
        == set(d["cumulative_sources"])
        == {"L", "B"}
        and set(d["history_feedback_sha256"]) == set(UPDATES),
        "complete branch history is required",
    )
    for digest in d["history_feedback_sha256"].values():
        sha(digest)
    for branch in ("L", "B"):
        retained = d["survivors"][branch]
        require(
            isinstance(retained, list)
            and 1 <= len(retained) <= 2
            and len(set(retained)) == len(retained),
            "nominate one or two distinct historical survivors per branch",
        )
        for identity in retained:
            sha(identity)
        require(
            set(d["retentions"][branch]) == set(UPDATES),
            "all three retention receipts are required",
        )
        for digest in d["retentions"][branch].values():
            sha(digest)
        require(
            d["cumulative_sources"][branch]
            == cumulative_sources([], d["cumulative_sources"][branch]),
            "selection exposure must retain normalized source identities",
        )
        require(
            {cid for cid in members if cid.startswith(branch + "-")}
            == {f"{branch}-{slot}" for slot in range(1, len(retained) + 1)},
            "nomination slots differ",
        )
    evaluation = d["evaluation"]
    require(
        set(evaluation) == {"schema", "stage", "protocol_sha256", "member_bindings"}
        and evaluation["schema"] == "saea-system-search-evaluation-binding-v1"
        and evaluation["stage"] == "selection"
        and evaluation["protocol_sha256"] == d["protocol_sha256"],
        "selection evaluation identity differs",
    )
    bindings = evaluation["member_bindings"]
    require(
        set(bindings) == set(members), "selection evaluation omits admitted members"
    )
    for cid, b in bindings.items():
        require(
            set(b) == {"bundle_id", "run_id", "config_hash"}
            and b["run_id"] == members[cid],
            "selection evaluation binding differs",
        )
        sha(b["bundle_id"])
        sha(b["config_hash"])
    require(
        bindings["seed"]["bundle_id"] == bindings["seed-aa"]["bundle_id"],
        "selection A/A differs from seed",
    )
    for branch in ("L", "B"):
        require(
            [
                bindings[f"{branch}-{slot}"]["bundle_id"]
                for slot in range(1, len(d["survivors"][branch]) + 1)
            ]
            == d["survivors"][branch],
            "selection policy differs from its frozen nomination",
        )
    if protocol is not None:
        stage = stage_for(protocol, "selection")
        require(
            d["protocol_sha256"] == content_hash(protocol)
            and set(stage["member_slots"]) == set(SLOTS)
            and d["roster_sha256"] == content_hash(stage["sample_ids"])
            and len(stage["sample_ids"]) == d["rows"]
            and d["trajectory_cap"] <= stage["trajectory_cap"],
            "selection differs from the frozen protocol or cohort",
        )
        require(
            bindings["seed"]["bundle_id"] == protocol["seed_bundle"]["bundle_id"],
            "selection seed differs",
        )
        required_exposure = {
            sid
            for name in ("initial", *UPDATES)
            for sid in stage_for(protocol, name)["sample_ids"]
        }
        for sources in d["cumulative_sources"].values():
            assert_roster_disjoint(sources, stage["sample_ids"])
            require(
                required_exposure
                <= {sid for source in sources for sid in source["sample_ids"]},
                "selection lost historical feedback exposure",
            )
    return d


def freeze_selection_stage(
    archive, *, protocol, update_feedback, member_bindings, data_root
):
    """Bind root's explicit nominees to reverified history, before any common run.

    Nominees may come from any of the three recorded branch retentions. This
    command never compares their different-cohort scores or selects a winner.
    The CLI must supply freshly gated families, not cached feedback files.
    """
    require(
        protocol.get("proposer_exact_version") and set(update_feedback) == set(UPDATES),
        "pin proposer and supply all three complete update families",
    )
    require(
        not (archive.root / "stages/selection.json").exists(),
        "selection registration already exists",
    )
    require(
        set(member_bindings) == set(SLOTS),
        "account for all six prospective selection slots",
    )
    runs = [b["run_id"] for b in member_bindings.values()]
    require(
        len(set(runs)) == len(SLOTS)
        and all(
            isinstance(r, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,240}", r)
            for r in runs
        ),
        "selection run identities must be distinct and confined",
    )
    require(
        all(not os.path.lexists(Path(data_root) / "runs" / r) for r in runs),
        "cannot freeze selection after any prospective run has artifacts",
    )
    history = {branch: {} for branch in ("L", "B")}
    for name in UPDATES:
        feedback = update_feedback[name]
        require(
            isinstance(feedback, CompleteSystemFeedback)
            and feedback.as_json()["family_id"] == name
            and bool(feedback.as_json().get("read_authority")),
            "selection requires bound complete history",
        )
        require_stage_feedback(protocol, name, feedback)
        for branch in history:
            history[branch][name] = archive._selection(
                protocol=protocol, stage_name=name, feedback=feedback, branch=branch
            )
    stage = stage_for(protocol, "selection")
    sources = {
        branch: cumulative_sources(
            [],
            [
                source
                for record in records.values()
                for source in record["cumulative_sources"]
            ],
        )
        for branch, records in history.items()
    }
    for source in sources.values():
        assert_roster_disjoint(source, stage["sample_ids"])
    bindings, excluded, survivors = {}, {}, {}
    seed = protocol["seed_bundle"]["bundle_id"]
    for cid in ("seed", "seed-aa"):
        require(
            member_bindings[cid]["bundle_id"] == seed,
            "common comparator must remain the seed",
        )
        bindings[cid] = dict(member_bindings[cid])
    for branch in history:
        allowed = {
            identity
            for record in history[branch].values()
            for identity in record["active_ids"]
        }
        survivors[branch] = []
        for slot in (1, 2):
            cid = f"{branch}-{slot}"
            b = member_bindings[cid]
            if b["bundle_id"] is None:
                require(
                    slot == 2 and b["config_hash"] is None,
                    "only the second nomination may be unused",
                )
                excluded[cid] = {"status": "not-nominated", "run_id": b["run_id"]}
                continue
            require(
                b["bundle_id"] in allowed and b["bundle_id"] not in survivors[branch],
                "nominee was not distinctly retained on this branch",
            )
            survivors[branch].append(b["bundle_id"])
            bindings[cid] = dict(b)
    for b in bindings.values():
        assert_roster_disjoint(
            archive.load_policy(b["bundle_id"]).as_json()["cumulative_sources"],
            stage["sample_ids"],
        )
    d = {
        "schema": SCHEMA,
        "stage": "selection",
        "protocol_sha256": content_hash(protocol),
        "roster_sha256": content_hash(stage["sample_ids"]),
        "rows": len(stage["sample_ids"]),
        "planned_runs": {cid: member_bindings[cid]["run_id"] for cid in SLOTS},
        "expected_members": {
            cid: bindings[cid]["run_id"] for cid in SLOTS if cid in bindings
        },
        "exclusions": excluded,
        "survivors": survivors,
        "retentions": {
            b: {n: r["selection_sha256"] for n, r in records.items()}
            for b, records in history.items()
        },
        "history_feedback_sha256": {
            n: content_hash(f.as_json()) for n, f in update_feedback.items()
        },
        "cumulative_sources": sources,
        "evaluation": {
            "schema": "saea-system-search-evaluation-binding-v1",
            "stage": "selection",
            "protocol_sha256": content_hash(protocol),
            "member_bindings": bindings,
        },
        "trajectory_cap": len(stage["sample_ids"]) * len(bindings),
        "official_score_jobs_cap": len(bindings),
        "runtime_admission": "separate-required",
    }
    d["registration_sha256"] = content_hash(d)
    validate_selection_registration(d, protocol=protocol)
    archive._write("stages/selection.json", d)
    return d
