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


INLINE_BYTES = 8192


def inline_feedback_examples(overview, artifacts, read_page):
    """Expose balanced source examples before optional reads, never select by gain.

    Only already-exported own-branch views are consumed. Original full records
    remain indexed. This presentation is neither causal attribution nor adoption.
    """
    def read(identity):
        a = artifacts[identity]
        return json.loads(read_page(a, 0, a["characters"]))

    index = read(overview["case_index"]["artifact_id"])
    choices = {}
    parent = overview["parent_id"]
    for case in index["cases"]:
        view = read(case["artifact_id"])
        members = {m["candidate_id"]: m for m in view["members"]}
        require(parent in members, "inline parent is missing")
        for cid in sorted(set(members) - {parent}):
            categories = [_category(members[parent], members[cid]),
                          "parent_correct" if _correct(members[parent]) else "parent_incorrect"]
            order = hashlib.sha256(f"20261001:{view['sample_id']}:{cid}".encode()).hexdigest()
            for category in categories:
                if category not in choices or order < choices[category][0]:
                    choices[category] = order, case["artifact_id"], view, cid
    require(choices, "inline examples need a complete comparison")
    selected = {}
    for category, (_, identity, view, cid) in sorted(choices.items()):
        key = view["sample_id"], cid
        if key not in selected:
            selected[key] = identity, view, cid, []
        selected[key][3].append(category)
    sources, response_text = [], {}

    def exact_response(response):
        address = response["source"]
        key = address["artifact_id"], address["offset"], address["characters"]
        if key not in response_text:
            raw = read_page(artifacts[key[0]], key[1], key[2])
            text = json.loads(raw)["payload"]["text"]
            require(isinstance(text, str) and len(text) == response["text_characters"]
                    and text.startswith(response["text_prefix"]), "inline response differs from indexed source")
            response_text[key] = text
        return response_text[key]

    def location(address):
        identity = address["artifact_id"]
        require(identity in artifacts, "inline source is not registered")
        if identity not in sources:
            sources.append(identity)
        return [sources.index(identity), address["offset"], address["characters"]]

    for limit in (256, 128, 64, 32, 16):
        examples = []
        for identity, view, cid, categories in selected.values():
            result = {"sample_id": view["sample_id"], "comparison": cid,
                      "categories": categories, "details_artifact_id": identity, "members": []}
            for m in view["members"]:
                if m["candidate_id"] not in {parent, cid}:
                    continue
                terminal = m["terminal"]
                responses = []
                for r in m["role_responses"]:
                    if r.get("missing_response"):
                        continue
                    prefix = exact_response(r)[:limit]
                    responses.append([r["role"], prefix, r["text_characters"],
                                      r["text_characters"] - len(prefix), location(r["source"])])
                prefix = terminal["text_prefix"][:limit]
                result["members"].append({"candidate_id": m["candidate_id"],
                    "counts": [m["native_counts"][k] for k in SLURP_NATIVE_FIELDS],
                    "utility": m["utility"], "relative_return": m["relative_return"],
                    "reliable": m["execution"]["reliable_completion"],
                    "terminal": [prefix, terminal["text_characters"],
                                 terminal["text_characters"] - len(prefix), location(terminal["source"])],
                    "responses": responses,
                    "missing_responses": sum(bool(r.get("missing_response")) for r in m["role_responses"])})
            examples.append(result)
        result = {"schema": "saea-proposer-inline-feedback-examples-v1",
            "sample_count": index["sample_count"], "covered_categories": sorted(choices),
            "count_fields": list(SLURP_NATIVE_FIELDS), "sources": sources, "examples": examples,
            "response_fields": ["role", "text_prefix", "text_characters", "omitted_characters", "source_range"],
            "terminal_fields": ["text_prefix", "text_characters", "omitted_characters", "source_range"],
            "source_range_fields": ["sources_index", "offset", "characters"],
            "selection": "One smallest seed20261001 sample/comparison hash per observed outcome category and parent correctness. Deduplicate pairs. Never choose by reward magnitude.",
            "omissions": ["Only representative pairs and response prefixes are inline; they are not full trajectories. Every original case/member, request, response, tool record and omitted character remains indexed.",
                          "Read source ranges before making claims about omitted text. A/A differences and terminal outcomes do not identify causal node contributions."]}
        if len(canonical(result).encode()) <= INLINE_BYTES:
            return result
    require(False, "inline source examples exceed the registered presentation bound")


COHERENT_BYTES = 6144


def coherent_feedback_chain(overview, artifacts, read_page):
    """Expose one whole decision chain, with every other case still indexed.

    Select by a frozen sample/member hash among structurally complete chains,
    never by reward or error magnitude. Do not truncate a selected response to
    make admission fit. This is a source presentation, not a causal explanation.
    """
    def read(identity):
        artifact = artifacts[identity]
        return json.loads(read_page(artifact, 0, artifact["characters"]))

    index = read(overview["case_index"]["artifact_id"])
    choices = []
    for case in index["cases"]:
        view = read(case["artifact_id"])
        for member in view["members"]:
            responses = member["role_responses"]
            for start in range(len(responses) - 2):
                chain = responses[start:start + 3]
                if [r["role"] for r in chain] != ["solver", "reviewer", "planner"]:
                    continue
                if start + 3 < len(responses) and responses[start + 3]["role"] == "solver":
                    chain = [*chain, responses[start + 3]]
                if any(r.get("missing_response") for r in chain):
                    continue
                order = hashlib.sha256(
                    f"20261001:{view['sample_id']}:{member['candidate_id']}".encode()
                ).hexdigest()
                choices.append((order, view["sample_id"], member["candidate_id"],
                                case["artifact_id"], member, chain))
                break
    omissions = [
        "Only one Solver-Reviewer-Planner decision and its immediate Solver revision, when present, are inline. This is not a complete trajectory.",
        "All cases, outcomes, remaining role visits, requests, tool records, terminals and source custody remain in the complete case index and original artifacts.",
        "Selection uses structural availability and a frozen hash, not reward magnitude. The balanced category index includes failures and damage; one chain is not representative evidence of efficacy or node causality.",
    ]
    result = {"schema": "saea-proposer-coherent-feedback-chain-v1",
              "status": "no-complete-decision-chain", "responses": [],
              "case_index": reference(artifacts[overview["case_index"]["artifact_id"]]),
              "omissions": omissions}
    if not choices:
        return result
    _, sid, cid, details, member, chain = min(choices, key=lambda c: c[:3])
    responses = []
    for response in chain:
        address = response["source"]
        raw = read_page(artifacts[address["artifact_id"]], address["offset"], address["characters"])
        original = json.loads(raw)
        text = original["payload"]["text"]
        require(original["channel"] == "MODEL_RESPONSE"
                and original["record_id"] == response["request_id"] + "/response"
                and isinstance(text, str) and len(text) == response["text_characters"]
                and text.startswith(response["text_prefix"]),
                "coherent response differs from indexed source")
        responses.append({"role": response["role"], "request_id": response["request_id"],
                          "text": text, "source": address})
    result.update(status="complete-decision-chain", sample_id=sid, candidate_id=cid,
        details_artifact_id=details, responses=responses, native_counts=member["native_counts"],
        utility=member["utility"], relative_return=member["relative_return"],
        reliable_completion=member["execution"]["reliable_completion"],
        omitted_role_responses=len(member["role_responses"]) - len(chain))
    require(len(canonical(result).encode()) <= COHERENT_BYTES,
            "coherent feedback exceeds the registered presentation bound; do not truncate or silently select another case")
    return result
