"""Deterministic, source-addressed views of already authorized complete feedback.

This is an offline capsule projection, not a scorer, evaluator or runtime store.
The caller must first pass the existing complete-family export gate. Every case
is indexed; previews explicitly omit text and retain exact raw character ranges.
"""
from __future__ import annotations

import hashlib
import json
import math

from .reward_links import SLURP_NATIVE_FIELDS
from .system_text_policy import canonical, require


CATEGORIES = ("correct_answer_repaired", "correct_answer_damaged", "native_counts_unchanged",
              "changed_not_resolved", "unreliable_execution")


def reference(artifact):
    return {k: artifact[k] for k in ("artifact_id", "kind", "characters")}


def _rows(artifact, read_page):
    """Stream JSONL in character coordinates, including original CRLF delimiters."""
    pending, offset = "", 0
    for start in range(0, artifact["characters"], 256 * 1024):
        pending += read_page(artifact, start, 256 * 1024)
        while "\n" in pending:
            line, pending = pending.split("\n", 1)
            line += "\n"
            if line.strip():
                yield json.loads(line), {"artifact_id": artifact["artifact_id"],
                                       "offset": offset, "characters": len(line)}
            offset += len(line)
    if pending.strip():
        yield json.loads(pending), {"artifact_id": artifact["artifact_id"],
                                   "offset": offset, "characters": len(pending)}


def _preview(text, source, size):
    require(isinstance(text, str), "feedback response text is missing")
    return {"text_prefix": text[:size], "text_characters": len(text),
            "omitted_characters": max(0, len(text) - size), "source": source}


def _correct(member):
    counts = member["native_counts"]
    return (counts["scenario_action_exact"] == 1 and counts["slot_f1_exact_fp"] == 0
            and counts["slot_f1_exact_fn"] == 0)


def _category(parent, child):
    if not all(m["execution"]["reliable_completion"] for m in (parent, child)):
        return "unreliable_execution"
    if _correct(parent) and not _correct(child):
        return "correct_answer_damaged"
    if not _correct(parent) and _correct(child):
        return "correct_answer_repaired"
    if parent["native_counts"] == child["native_counts"]:
        return "native_counts_unchanged"
    return "changed_not_resolved"


def build_feedback_views(packet, artifacts, read_page, append):
    """Index the entire own-branch cohort, with equal visibility for every outcome."""
    if packet["branch"] == "B":
        require("feedback" not in packet, "blind views cannot read feedback")
        return
    feedback = packet["feedback"]
    groups = feedback["feedback"]["groups"]
    ids = [g["sample_id"] for g in groups]
    members = set(feedback["summaries"])
    parent_id = "seed" if "seed" in members else "L-parent"
    require(groups and len(set(ids)) == len(ids) and parent_id in members,
            "feedback view cohort or parent is missing/duplicated")
    for group in groups:
        names = [m["candidate_id"] for m in group["members"]]
        require(set(names) == members and len(names) == len(members), "incomplete feedback view family")
        for m in group["members"]:
            require(set(m["native_counts"]) == set(SLURP_NATIVE_FIELDS), "native counts fields differ")
            require(all(type(v) in (int, float) and math.isfinite(v) and v >= 0
                        for v in m["native_counts"].values()), "invalid native counts")
            require(all(m["native_counts"][k] in (0, 1) for k in SLURP_NATIVE_FIELDS[:3]),
                    "invalid native correctness count")
            require(type(m["execution"]["reliable_completion"]) is bool, "completion flag is missing")

    def source(pin, kind):
        matches = [a for a in artifacts.values() if a["kind"] == kind and a["source"] == pin]
        require(len(matches) == 1, "feedback view source is not uniquely registered")
        return matches[0]

    terminals, responses = {}, {}
    for cid in sorted(members):
        executions = [next(m["execution"] for m in g["members"] if m["candidate_id"] == cid) for g in groups]
        require(all(all(e[k] == executions[0][k] for k in ("terminal_output", "trace")) for e in executions),
                "feedback view member mixes source files")
        terminal = source(executions[0]["terminal_output"], "feedback-terminal_output")
        trace = source(executions[0]["trace"], "feedback-trace")
        rows, wanted, found = {}, {}, {}
        for row, address in _rows(terminal, read_page):
            sid = row["sample_id"]
            require(sid in ids and sid not in rows, "terminal view cohort differs or is duplicated")
            roles = []
            for visit in row["native_episode_receipt"]["role_visits"]:
                for contact in visit.get("execution_receipt", {}).get("contacts", []):
                    request = contact["request_id"]
                    require(request not in wanted, "duplicate terminal contact identity")
                    wanted[request] = sid
                    roles.append((visit["role_id"], request))
            rows[sid] = {"terminal": _preview(row["text"], address, 256), "roles": roles,
                         "planner_routes": row["native_episode_receipt"].get("planner_routes", [])}
        require(set(rows) == set(ids), "terminal view cohort is incomplete")
        for row, address in _rows(trace, read_page):
            if row["channel"] != "MODEL_RESPONSE":
                continue
            rid = row["record_id"]
            require(rid.endswith("/response"), "response view identity differs")
            request = rid.removesuffix("/response")
            if request not in wanted:
                continue  # Unattributed records remain in the complete source.
            require(request not in found, "duplicate response view identity")
            found[request] = _preview(row["payload"].get("text"), address, 128)
        terminals[cid], responses[cid] = rows, found

    comparisons = {cid: {"counts": dict.fromkeys(CATEGORIES, 0), "representatives": {},
                        "interpretation": "A/A variation, not a treatment effect" if cid.endswith("-aa")
                        else "Descriptive whole-system outcomes, not causal node effects"}
                   for cid in sorted(members - {parent_id})}
    cases, representative_order = [], {}
    for group in groups:
        sid = group["sample_id"]
        by_id = {m["candidate_id"]: m for m in group["members"]}
        view = {"schema": "saea-proposer-feedback-case-view-v1", "sample_id": sid, "members": [],
                "omissions": ["Response text tails, complete request bodies, tool payloads and custody metadata remain in the source artifacts.",
                              "Character ranges locate the complete original JSONL records; prefixes are not complete trajectories."]}
        for member in group["members"]:
            cid = member["candidate_id"]
            row = terminals[cid][sid]
            execution = member["execution"]
            view["members"].append({"candidate_id": cid, "native_counts": member["native_counts"],
                "utility": member["utility"], "relative_return": member["relative_return"],
                "execution": {k: v for k, v in execution.items() if k not in {"trace", "terminal_output"}},
                "terminal": row["terminal"], "planner_routes": row["planner_routes"],
                "complete_trace": reference(source(execution["trace"], "feedback-trace")),
                "role_responses": [{"role": role, "request_id": rid,
                                    **responses[cid].get(rid, {"missing_response": True})}
                                   for role, rid in row["roles"]]})
        artifact_id = append(canonical(view).encode(), "feedback-case-view",
                             {"input_sha256": packet["input_sha256"], "sample_id": sid})
        brief = {"schema": "saea-proposer-feedback-case-brief-v1", "sample_id": sid,
                 "details_artifact_id": artifact_id, "count_fields": list(SLURP_NATIVE_FIELDS),
                 "members": [{"candidate_id": m["candidate_id"],
                     "counts": [m["native_counts"][k] for k in SLURP_NATIVE_FIELDS],
                     "utility": m["utility"], "reliable": m["execution"]["reliable_completion"],
                     "calls": [m["execution"]["model_calls"], m["execution"]["tool_calls"]],
                     "terminal_prefix": m["terminal"]["text_prefix"][:96],
                     "role_prefixes": [[r["role"], r.get("text_prefix", "")[:32], r.get("missing_response", False)]
                                       for r in m["role_responses"]]} for m in view["members"]],
                 "omissions": ["Terminal prefixes are at most96 characters; role prefixes at most32. Full text, costs, relative returns, other family members and source ranges are in details. Prefixes are not full trajectories."]}
        brief_ids = {}
        for cid in comparisons:
            pair = {**brief, "comparison": cid,
                    "members": [m for m in brief["members"] if m["candidate_id"] in {parent_id, cid}]}
            brief_ids[cid] = append(canonical(pair).encode(), "feedback-case-brief",
                {"input_sha256": packet["input_sha256"], "sample_id": sid, "comparison": cid})
        cases.append({"sample_id": sid, "artifact_id": artifact_id, "brief_artifact_ids": brief_ids})
        # Pick one deterministic representative per category, never the largest gain.
        order = hashlib.sha256(f"20261001:{sid}".encode()).hexdigest(), sid
        for cid, comparison in comparisons.items():
            category = _category(by_id[parent_id], by_id[cid])
            comparison["counts"][category] += 1
            key = cid, category
            if key not in representative_order or order < representative_order[key]:
                representative_order[key] = order
                comparison["representatives"][category] = {"sample_id": sid, "artifact_id": brief_ids[cid],
                                                          "characters": artifacts[brief_ids[cid]]["characters"]}
    index = append(canonical({"schema": "saea-proposer-feedback-case-index-v1", "cases": cases,
        "sample_count": len(cases), "omissions": []}).encode(), "feedback-case-index",
        {"input_sha256": packet["input_sha256"]})
    overview = {"schema": "saea-proposer-feedback-overview-v1", "family_id": feedback["family_id"],
        "sample_count": len(groups), "parent_id": parent_id, "comparisons": comparisons,
        "case_index": reference(artifacts[index]),
        "definitions": "Correct means intent correct and zero exact-slot FP/FN. Unchanged means all native counts equal, not necessarily identical text. These are descriptive categories, not a new reward or an adoption test.",
        "representative_rule": "One smallest seed-20261001 sample hash per nonempty category/comparison; every case remains in the index.",
        "omissions": ["This overview omits individual counts and trajectory text; use indexed case views and their original-source ranges."]}
    append(canonical(overview).encode(), "feedback-overview", {"input_sha256": packet["input_sha256"]})
