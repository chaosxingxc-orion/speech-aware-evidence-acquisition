"""Qualify complete configured capacity evidence for root structural review.

Reuse the shared runtime's capacity records. Do not dispatch, read task quality,
change a source, or grant runtime admission. The caller must verify file pins,
registered read scope, terminal process identities and fresh live gates.
"""
from __future__ import annotations

import math
import hashlib
import json
import re
from collections import Counter
from copy import deepcopy
from .experiment_population import validate_population_config
from .hashing import content_hash
from .system_text_policy import _pin, sha


def _require(condition, reason):
    if not condition:
        raise ValueError(reason)


def qualify_capacity_family(population, population_pin, registration, finished,
                            windows_exit, receipts, **limits):
    """Qualify one complete successful epoch without altering terminal evidence."""
    try:
        _require(type(finished["exit_code"]) is int and finished["exit_code"] == 0
                 and type(windows_exit["exit_code"]) is int and windows_exit["exit_code"] == 0,
                 "Capacity or Windows entry did not finish successfully")
        _require(all(type(finished[k]) is int and finished[k] == 0 for k in ("generation_contacts", "scorer_contacts")),
                 "Capacity family added generation or scoring")
        return _qualify_members(population, population_pin, registration,
                                finished["members"], receipts, **limits)
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError("Malformed capacity family evidence") from error


def qualify_matched_capacity_family(populations, population_pins, registration,
                                    finished, windows_exit, receipts, *,
                                    original_registration, member_terminals, output_reserve,
                                    structural_reserve, slot_tokens,
                                    graph_config_hashes):
    """Qualify the original complete two-arm capacity, including control/A/A.

    Supply verified config dictionaries keyed by arm, ordered ``arm``/``pin``
    entries, the independently pinned original dispatch registration, the actual
    outer Windows finished/exit records, and each child's original finished
    record keyed by label in ``member_terminals``. Do not manufacture a combined
    terminal receipt. Derive expected reserves, slot geometry and graph config
    hashes from the pinned configs. Read only saved operational evidence.
    The caller must verify their raw file pins,
    read authorization, terminal process identities, and fresh live gates. This
    review neither joins epochs nor grants structural or scientific admission.
    Counts come from the configurations and original member registrations.
    Returned evidence hashes are canonical content hashes, not raw-file pins.
    """
    try:
        _require(isinstance(population_pins, list) and len(population_pins) == 2,
                 "Matched capacity requires two ordered population pins")
        arms = [p["arm"] for p in population_pins]
        _require(all(isinstance(a, str) and a and a.isascii() for a in arms)
                 and len(set(arms)) == 2 and set(populations) == set(arms),
                 "Matched population arms differ")
        _require(all(set(p) == {"arm", "pin"} and set(p["pin"]) == {"relpath", "sha256"}
                     and all(isinstance(v, str) and v for v in p["pin"].values())
                     for p in population_pins)
                 and population_pins[0]["pin"] != population_pins[1]["pin"],
                 "Matched population pins are malformed or repeated")
        _require(content_hash(registration) == content_hash(original_registration),
                 "Capacity differs from the original complete registration")
        _require(registration["schema"] == "saea-configured-partitioned-capacity-entry-v1"
                 and registration["status"] == "ROOT-ADMITTED",
                 "Original matched capacity was not admitted")
        _require(registration["experiment_populations"] == population_pins,
                 "Ordered matched population pins differ")
        _require(all(type(value) is int and value > 0
                     for value in (output_reserve, structural_reserve, slot_tokens)),
                 "Invalid capacity reserves or slot geometry")
        configured = {}
        geometry = populations[arms[0]]["execution"]
        for entry in population_pins:
            arm, pin = entry["arm"], entry["pin"]
            config = validate_population_config(populations[arm])
            _require(config["sampling"] == registration["sampling"], "Sampling differs")
            _require(config["execution"] == geometry, "Matched execution geometry differs")
            for cohort in config["cohorts"]:
                for role, field in (("control", "control_ids"), ("candidate", "candidate_ids")):
                    for member_id in cohort[field]:
                        label = arm + "-" + member_id
                        _require(label not in configured, "Configured matched member repeats")
                        configured[label] = (arm, pin, cohort, role, member_id)
        labels = list(configured)
        members = registration["members"]
        _require([m["label"] for m in members] == labels, "Ordered matched capacity members differ")
        _require(set(receipts) == set(labels) and set(graph_config_hashes) == set(labels),
                 "Matched receipts or graph hashes do not cover exactly the family")
        _require(set(member_terminals) == set(labels), "Child terminals do not cover exactly the family")
        _require([m["label"] for m in finished["members"]] == labels, "Terminal members differ")
        _require(all(type(e["exit_code"]) is int and e["exit_code"] == 0
                     for e in (finished, windows_exit)), "Capacity or Windows entry did not finish successfully")
        _require(all(type(finished[k]) is int and finished[k] == 0
                     for k in ("generation_contacts", "scorer_contacts")),
                 "Capacity family added generation or scoring")
        _require(finished["failure"] is None, "Capacity finished with a recorded failure")
        _require(all(type(m["contact_cap"]) is int and m["contact_cap"] > 0 for m in members),
                 "Invalid capacity endpoint cap")
        budget = {"generation_contacts": 0, "scorer_contacts": 0,
                  "tokenizer_endpoint_caps": {m["label"]: m["contact_cap"] for m in members},
                  "tokenizer_endpoints_total": sum(m["contact_cap"] for m in members)}
        _require(content_hash(registration["budget"]) == content_hash(budget), "Capacity budget differs")
        _require(all(isinstance(m[k], str) and m[k] for m in members
                     for k in ("run_id", "attempt_id", "composed_config_hash"))
                 and all(len({m[k] for m in members}) == len(members)
                         for k in ("run_id", "attempt_id")), "Capacity identities are empty or repeated")
        summary = []
        for member, exit_record in zip(members, finished["members"], strict=True):
            label = member["label"]
            arm, pin, cohort, role, member_id = configured[label]
            roster = cohort["sample_ids"]
            _require(member["experiment_population"] == pin, "Member population pin differs")
            _require(all(exit_record[k] == member[k] for k in ("label", "run_id", "attempt_id"))
                     and all(type(exit_record[k]) is int and exit_record[k] == 0
                             for k in ("exit_code", "observer_exit_code")),
                     "Outer member identity or observer exit differs")
            terminal = member_terminals[label]
            _require(all(type(terminal[k]) is int and terminal[k] == 0
                         for k in ("exit_code", "generation_contacts", "scorer_contacts"))
                     and isinstance(terminal["members"], list) and len(terminal["members"]) == 1,
                     "Child capacity terminal is incomplete or unsuccessful")
            _require(type(member["expected_rows"]) is int and member["expected_rows"] == len(roster)
                     and type(member["graph_rows"]) is int and 0 < member["graph_rows"] <= len(roster),
                     "Registered roster or graph count differs")
            record = receipts[label]
            _require(record["inputs"]["roster"] == roster, "Ordered matched roster differs")
            result = _qualify_member(member, terminal["members"][0], registration, record, roster,
                                     output_reserve=output_reserve, structural_reserve=structural_reserve,
                                     slot_tokens=slot_tokens, graph_config_hash=graph_config_hashes[label])
            output = record["output"]
            _require(type(output["generation_contacts"]) is int and output["generation_contacts"] == 0
                     and ("scorer_contacts" not in output or
                          type(output["scorer_contacts"]) is int and output["scorer_contacts"] == 0),
                     "Capacity output added generation or scoring")
            _require(all(type(record["inputs"][k]) is int for k in ("output_reserve", "structural_reserve"))
                     and all(type(row[k]) is int for row in output["rows"] for k in
                             ("maximum_completion_tokens", "additional_structural_reserve_tokens", "slot_tokens")),
                     "Malformed measured reserves or geometry")
            _qualify_graph_counts(output, roster, member["graph_rows"])
            result.update(arm=arm, member_id=member_id, member_role=role,
                          population_cohort=cohort["cohort_id"], experiment_population=deepcopy(pin))
            summary.append(result)
        return {"schema": "saea-matched-capacity-family-review-v1",
                "experiment_populations": deepcopy(population_pins), "members": summary,
                "tokenizer_endpoints": sum(m["contacts"] for m in summary),
                "generation_contacts": 0, "scorer_contacts": 0,
                "registration_sha256": content_hash(registration),
                "finished_sha256": content_hash(finished), "windows_exit_sha256": content_hash(windows_exit),
                "capacity_receipts_sha256": content_hash(receipts),
                "member_terminals_sha256": content_hash(member_terminals),
                "root_review_required": True, "runtime_admission": False}
    except (KeyError, TypeError, AttributeError, IndexError, StopIteration) as error:
        raise ValueError("Malformed matched capacity family evidence") from error


def _qualify_graph_counts(output, roster, graph_rows):
    """Bind both operational stress modes to their registered graph roster size."""
    modes = ("new-acquisition", "wide-automatic-supply")
    proofs = output["proofs"]
    _require(isinstance(proofs, list) and [p["mode"] for p in proofs] == list(modes),
             "Capacity graph proofs differ")
    _require(all(type(p["terminal_rows"]) is int and p["terminal_rows"] == graph_rows
                 for p in proofs), "Capacity graph terminal count differs")
    rows = output["rows"]
    _require(set(r["mode"] for r in rows) == set(modes), "Measured graph modes differ")
    graph_rosters = []
    for mode in modes:
        measured = [r for r in rows if r["mode"] == mode]
        samples = {r["sample_id"] for r in measured}
        _require(len(samples) == graph_rows and samples <= set(roster), "Measured graph roster differs")
        _require(all(type(r["captured_request_index"]) is int for r in measured)
                 and [r["captured_request_index"] for r in measured] == list(range(len(measured))),
                 "Measured graph requests are missing, repeated or reordered")
        graph_rosters.append(samples)
    _require(graph_rosters[0] == graph_rosters[1], "Graph stress rosters differ")


def qualify_architecture_capacity_family(population, population_pin, registration,
                                         finished, windows_exit, receipts, *,
                                         original_registration, member_terminals,
                                         policy_config_bytes, source_check,
                                         output_reserve, structural_reserve,
                                         slot_tokens, graph_config_hashes):
    """Review one complete manual V4 family; never authorize runtime contacts.

    This explicit interface does not relax either historical qualifier. Supply
    original outer Windows finished/exit and child terminal/lease records, the
    independently pinned registration, verified graph config hashes, and each
    member's raw policy bytes. The caller verifies raw population/receipt pins,
    process identities, read scope and fresh live gates. No evidence is repaired.

    Register schema ``saea-architecture-capacity-entry-v1`` with the population
    pin, sampling, execution, worker/worker_commit, budget, and ordered members.
    Each member adds member_id, population_cohort, execution_config,
    execution_identity_sha256 (canonical V4 member hash), model_per_trajectory,
    rehearsal_profile, and ordered graph_sample_ids to the existing
    run/attempt/config/cap/row fields. Verify graph_sample_ids against the same
    pinned graph configuration as graph_config_hashes before calling. Branches
    follow that registered roster, never the order of parallel completions.
    ``source_check_sha256`` pins the separate completed model-free source check
    canonically: source_commit, experiment_population, exit_code, and integer
    zero generation_contacts/tokenizer_contacts/scorer_contacts are required.
    This is evidence of that prerequisite, never a replacement capacity run.
    Returned evidence hashes are canonical hashes, not raw-file pins.
    """
    try:
        _pin(population_pin)
        config = validate_population_config(population, allow_architecture=True)
        _require(config["schema"] == "saea-experiment-population-config-v4",
                 "Architecture capacity requires the explicit manual V4 population")
        _require(content_hash(registration) == content_hash(original_registration),
                 "Architecture capacity differs from its original registration")
        _require(registration["schema"] == "saea-architecture-capacity-entry-v1"
                 and registration["status"] == "ROOT-ADMITTED", "Architecture capacity was not admitted")
        _require(registration["experiment_population"] == population_pin
                 and registration["sampling"] == config["sampling"]
                 and registration["execution"] == config["execution"], "Architecture population binding differs")
        _require(isinstance(registration["worker"], str) and bool(registration["worker"])
                 and isinstance(registration["worker_commit"], str)
                 and re.fullmatch(r"[a-f0-9]{40}", registration["worker_commit"]),
                 "Capacity worker source must be an immutable commit")
        _require(content_hash(source_check) == registration["source_check_sha256"]
                 and source_check["source_commit"] == registration["worker_commit"]
                 and source_check["experiment_population"] == population_pin
                 and all(type(source_check[k]) is int and source_check[k] == 0 for k in
                         ("exit_code", "generation_contacts", "tokenizer_contacts", "scorer_contacts")),
                 "Model-free source check is missing, unsuccessful or cross-bound")
        _require((output_reserve, structural_reserve, slot_tokens) == (512, 2048, 24576)
                 and all(type(v) is int for v in (output_reserve, structural_reserve, slot_tokens)),
                 "Unsupported architecture capacity geometry")
        identities = config["architecture"]["members"]
        labels = [m["member_id"] for m in identities]
        _require(len(set(labels)) == len(labels), "Architecture capacity member labels repeat")
        members = registration["members"]
        _require([m["label"] for m in members] == labels
                 and [m["label"] for m in finished["members"]] == labels,
                 "Ordered architecture capacity members differ")
        runtime_fields = ("runtime_sample_ids", "runtime_graph_sample_ids")
        if (any(k in m for m in members for k in runtime_fields)
                or any(k in m for m in source_check.get("members", []) for k in runtime_fields)):
            checked_members = source_check["members"]
            _require(isinstance(checked_members, list)
                     and [m["label"] for m in checked_members] == labels,
                     "Frozen runtime order check does not cover the complete ordered family")
            for member, checked in zip(members, checked_members, strict=True):
                _require(checked["graph_config_hash"] == graph_config_hashes[member["label"]]
                         and ("graph_config_hash" not in member
                              or member["graph_config_hash"] == checked["graph_config_hash"]),
                         "Frozen runtime graph configuration differs")
                _require(all(k in member and k in checked and member[k] == checked[k]
                             for k in (*runtime_fields, "run_id", "attempt_id", "composed_config_hash",
                                       "graph_sample_ids")),
                         "Registered runtime order differs from the frozen production source check")
        _require(all(set(mapping) == set(labels) for mapping in
                     (receipts, member_terminals, graph_config_hashes, policy_config_bytes)),
                 "Architecture evidence does not cover exactly the complete family")
        _require(all(type(e["exit_code"]) is int and e["exit_code"] == 0
                     for e in (finished, windows_exit)) and finished["failure"] is None
                 and all(type(finished[k]) is int and finished[k] == 0
                         for k in ("generation_contacts", "scorer_contacts")),
                 "Architecture capacity outer process is incomplete or unsuccessful")
        _require(all(isinstance(m[k], str) and m[k] for m in members for k in ("run_id", "attempt_id"))
                 and all(len({m[k] for m in members}) == len(members) for k in ("run_id", "attempt_id")),
                 "Capacity run or attempt identities are empty or repeated")
        _require(all(type(m["contact_cap"]) is int and m["contact_cap"] > 0 for m in members),
                 "Invalid architecture capacity endpoint cap")
        budget = {"generation_contacts": 0, "scorer_contacts": 0,
                  "tokenizer_endpoint_caps": {m["label"]: m["contact_cap"] for m in members},
                  "tokenizer_endpoints_total": sum(m["contact_cap"] for m in members)}
        _require(content_hash(registration["budget"]) == content_hash(budget), "Capacity budget differs")
        cohorts = {c["cohort_id"]: c for c in config["cohorts"]}
        summary = []
        for identity, member, outer in zip(identities, members, finished["members"], strict=True):
            label = member["label"]
            summary.append(_qualify_architecture_member(
                identity, member, outer, member_terminals[label], receipts[label], registration,
                cohorts[identity["cohort_id"]], policy_config_bytes[label], graph_config_hashes[label],
                output_reserve=output_reserve, structural_reserve=structural_reserve, slot_tokens=slot_tokens))
        return {"schema": "saea-architecture-capacity-family-review-v1",
                "experiment_population": deepcopy(population_pin), "members": summary,
                "tokenizer_endpoints": sum(m["contacts"] for m in summary),
                "generation_contacts": 0, "scorer_contacts": 0,
                "registration_sha256": content_hash(registration), "source_check_sha256": content_hash(source_check),
                "finished_sha256": content_hash(finished), "windows_exit_sha256": content_hash(windows_exit),
                "capacity_receipts_sha256": content_hash(receipts),
                "member_terminals_sha256": content_hash(member_terminals),
                "root_review_required": True, "runtime_admission": False}
    except (KeyError, TypeError, AttributeError, IndexError, UnicodeError) as error:
        raise ValueError("Malformed architecture capacity family evidence") from error


def _qualify_architecture_member(identity, member, outer, terminal, record, registration,
                                 cohort, policy_bytes, graph_config_hash, *, output_reserve,
                                 structural_reserve, slot_tokens):
    """Apply identical member proof checks to original and explicitly recovered sources."""
    label = member["label"]
    sha(member["composed_config_hash"])
    sha(graph_config_hash)
    roster = cohort["sample_ids"]
    _require(member["member_id"] == identity["member_id"]
             and member["population_cohort"] == identity["cohort_id"]
             and member["execution_config"] == identity["execution_config"]
             and member["execution_identity_sha256"] == content_hash(identity)
             and type(member["model_per_trajectory"]) is int
             and member["model_per_trajectory"] == identity["model_per_trajectory"]
             and member["experiment_population"] == registration["experiment_population"],
             "Registered architecture member differs from its policy or ceiling")
    _require(type(member["expected_rows"]) is int and member["expected_rows"] == len(roster)
             and type(member["graph_rows"]) is int and member["graph_rows"] == 4,
             "Architecture capacity requires its complete roster and four graph rows")
    graph_roster = member["graph_sample_ids"]
    _require(isinstance(graph_roster, list) and len(graph_roster) == 4
             and len(set(graph_roster)) == 4 and set(graph_roster) <= set(roster),
             "Registered graph branch roster is missing, repeated or outside the population")
    runtime_fields = ("runtime_sample_ids", "runtime_graph_sample_ids")
    explicit_runtime_order = any(k in member for k in runtime_fields)
    runtime_roster, runtime_graph_roster = roster, graph_roster
    if explicit_runtime_order:
        _require(all(k in member for k in runtime_fields), "Runtime roster bindings must be supplied together")
        runtime_roster, runtime_graph_roster = (member[k] for k in runtime_fields)
        for actual, configured in ((runtime_roster, roster), (runtime_graph_roster, graph_roster)):
            _require(isinstance(actual, list) and all(isinstance(s, str) for s in actual)
                     and len(actual) == len(configured) and len(set(actual)) == len(actual)
                     and set(actual) == set(configured),
                     "Runtime roster binding is missing, repeated or outside the registered membership")
    raw = policy_bytes
    _require(isinstance(raw, bytes) and hashlib.sha256(raw).hexdigest() == identity["execution_config"]["sha256"],
             "Architecture policy bytes differ from their population pin")
    episode = json.loads(raw)["native_episode"]
    off = identity["active_roles"] == ["perception", "solver"]
    tool = episode.get("solver_tool_access", "none") == "bounded-slot-lookup-v1"
    profile = "review-off-v1" if off else "legacy-four-path-v1"
    _require(member["rehearsal_profile"] == profile
             and (episode.get("review_loop") == "off") == off,
             "Capacity profile differs from the pinned architecture")
    if off:
        roles = episode["roles"]
        _require(episode["max_revisions"] == 0
                 and episode.get("solver_tool_access", "none") in ("none", "bounded-slot-lookup-v1")
                 and {r: roles[r]["max_iterations"] for r in ("perception", "solver", "reviewer", "planner")}
                 == {"perception": 1, "solver": 2 if tool else 1, "reviewer": 0, "planner": 0}
                 and identity["model_per_trajectory"] == (3 if tool else 2),
                 "Unsupported review-off role or contact limits")
    _require(all(outer[k] == member[k] for k in ("label", "run_id", "attempt_id"))
             and all(type(outer[k]) is int and outer[k] == 0 for k in ("exit_code", "observer_exit_code")),
             "Capacity outer member identity or observer exit differs")
    _require(all(type(terminal[k]) is int and terminal[k] == 0 for k in
                 ("exit_code", "generation_contacts", "scorer_contacts"))
             and isinstance(terminal["members"], list) and len(terminal["members"]) == 1,
             "Child capacity terminal is incomplete or unsuccessful")
    _require(record["inputs"]["roster"] == runtime_roster, "Ordered architecture roster differs")
    for value in (record["inputs"], record["output"]):
        _require(value.get("rehearsal_profile", "legacy-four-path-v1") == profile,
                 "Capacity receipt profile differs from its registration")
    if off:
        endpoint_budget = record["inputs"]["endpoint_budget"]
        ranking = endpoint_budget["ranking_tokenizer_endpoints"]
        _require(type(ranking) is int and ranking > 0, "Invalid ranking endpoint count")
        expected_budget = {"profile": profile, "graph_rows": 4,
            "supply_modes": 2 if tool else 1, "captured_requests": 22 if tool else 8,
            "ranking_tokenizer_endpoints": ranking, "padding_tokenizer_endpoints": 60 if tool else 18,
            "request_measurement_endpoints": 66 if tool else 24, "contact_cap": ranking + (127 if tool else 43)}
        _require(content_hash(endpoint_budget) == content_hash(expected_budget)
                 and content_hash(record["output"]["endpoint_budget"]) == content_hash(expected_budget)
                 and type(record["inputs"]["registered_contact_cap"]) is int
                 and record["inputs"]["registered_contact_cap"] == member["contact_cap"]
                 and member["contact_cap"] >= expected_budget["contact_cap"]
                 and type(record["output"]["contacts"]) is int
                 and 0 < record["output"]["contacts"] <= expected_budget["contact_cap"],
                 "Review-off measured endpoint budget differs or exceeds registration")
    result = _qualify_member(member, terminal["members"][0], registration, record, roster,
                             output_reserve=output_reserve, structural_reserve=structural_reserve,
                             slot_tokens=slot_tokens, graph_config_hash=graph_config_hash)
    _qualify_architecture_proofs(record, runtime_graph_roster, off=off, tool=tool)
    result.update(member_id=identity["member_id"], population_cohort=identity["cohort_id"],
                  member_role="control" if label in cohort["control_ids"] else "candidate",
                  execution_config=deepcopy(identity["execution_config"]),
                  execution_identity_sha256=content_hash(identity),
                  graph_sample_ids=deepcopy(graph_roster),
                  model_per_trajectory=identity["model_per_trajectory"], rehearsal_profile=profile)
    if explicit_runtime_order:
        result.update(runtime_sample_ids=deepcopy(runtime_roster),
                      runtime_graph_sample_ids=deepcopy(runtime_graph_roster))
    return result


def _qualify_architecture_proofs(record, graph_roster, *, off, tool):
    """Refuse partial captures, wrong stress profiles and absent final custody."""
    output = record["output"]
    _require(record["inputs"]["schema"] == "saea-native-graph-capacity-input-v1"
             and output["schema"] == "saea-native-graph-capacity-v1",
             "Unsupported architecture capacity receipt schema")
    _require(type(output["generation_contacts"]) is int and output["generation_contacts"] == 0
             and ("scorer_contacts" not in output or
                  type(output["scorer_contacts"]) is int and output["scorer_contacts"] == 0),
             "Capacity output added generation or scoring")
    _require(all(type(record["inputs"][k]) is int for k in ("output_reserve", "structural_reserve"))
             and all(type(row[k]) is int for row in output["rows"] for k in
                     ("maximum_completion_tokens", "additional_structural_reserve_tokens", "slot_tokens")),
             "Malformed measured capacity reserves or geometry")
    speech = output["maximum_speech_tokens_over_roster"]
    selected = output["selected_slots"]
    _require(type(speech) is int and speech > 0, "Maximum roster speech measurement is missing")
    _require(isinstance(selected, list) and len(selected) == 2
             and all(isinstance(s, (list, tuple)) and len(s) == 3
                     and type(s[0]) is int and s[0] > 0
                     and all(isinstance(v, str) and v for v in s[1:]) for s in selected)
             and selected[0][0] >= selected[1][0]
             and len({s[1] for s in selected}) == len({s[2] for s in selected}) == 2,
             "Two longest distinct slot value measurements are required")
    for row in output["rows"]:
        _require(isinstance(row["request_body_sha256"], str)
                 and re.fullmatch(r"[a-f0-9]{64}", row["request_body_sha256"])
                 and all(type(row[k]) is int and row[k] >= 0 for k in
                         ("text_tokens", "speech_tokens", "media_count", "special_tokens",
                          "required_tokens", "margin_tokens", "margin_after_structural_reserve"))
                 and row["speech_tokens"] == speech and row["media_count"] == 1
                 and row["special_tokens"] == 2
                 and type(row["fit_multiple"]) in (int, float) and row["fit_multiple"] == 1
                 and row["required_tokens"] == row["text_tokens"] + speech + 512 + 2
                 and row["margin_tokens"] == 24576 - row["required_tokens"]
                 and row["margin_after_structural_reserve"] == row["margin_tokens"] - 2048,
                 "Capacity request measurement is missing or internally inconsistent")
    modes = ["new-acquisition", "wide-automatic-supply"] if not off or tool else ["wide-automatic-supply"]
    counts = [4, 5, 5, 8] if not off else ([2, 3, 3, 3] if tool else [2, 2, 2, 2])
    proofs, rows = output["proofs"], output["rows"]
    _require(isinstance(proofs, list) and [p["mode"] for p in proofs] == modes
             and [r["mode"] for r in rows] == [m for m in modes for _ in range(sum(counts))],
             "Capacity stress modes or captured request counts differ")
    for proof in proofs:
        _require(type(proof["terminal_rows"]) is int and proof["terminal_rows"] == 4
                 and type(proof["synthetic_completions"]) is int and proof["synthetic_completions"] == sum(counts),
                 "Capacity terminal or completion counts differ")
        _require(isinstance(proof["requests_sha256"], str)
                 and re.fullmatch(r"[a-f0-9]{64}", proof["requests_sha256"]), "Malformed capture hash")
        intents = proof["candidate_intents"]
        _require(isinstance(intents, list) and len(intents) == 3
                 and all(isinstance(i, str) and i for i in intents) and len(set(intents)) == 3,
                 "Three distinct capacity candidate intents are required")
        tokens = proof["synthetic_response_tokens"]
        expected_tokens = ({"perception", "solver", "solver_tool_call"} if tool else {"perception", "solver"}) if off else {"perception", "solver", "reviewer"}
        _require(set(tokens) == expected_tokens
                 and all(type(v) is int and 0 < v <= 512 for v in tokens.values()),
                 "Bounded synthetic role response measurements differ")
        measured = [r for r in rows if r["mode"] == proof["mode"]]
        # Parallel trajectories can interleave and their first contacts can
        # complete in any order. Only each registered branch's count and the
        # global capture indexes are invariant; do not regroup the source rows.
        observed_counts = Counter(r["sample_id"] for r in measured)
        _require(observed_counts == dict(zip(graph_roster, counts, strict=True))
                 and all(type(r["captured_request_index"]) is int for r in measured)
                 and [r["captured_request_index"] for r in measured] == list(range(sum(counts))),
                 "Capacity graph requests are missing, repeated or reordered")
        if off:
            _require(type(proof["synthetic_tool_calls"]) is int and proof["synthetic_tool_calls"] == (2 if tool else 0)
                     and type(proof["post_tool_final_requests"]) is int
                     and proof["post_tool_final_requests"] == (3 if tool else 0),
                     "Review-off capacity tool and final-contact counts differ")
            finals = proof["accepted_final_request_sha256"]
            _require(set(finals) == set(graph_roster)
                     and all(isinstance(v, str) and re.fullmatch(r"[a-f0-9]{64}", v) for v in finals.values())
                     and len(set(finals.values())) == 4, "Review-off accepted final request custody is incomplete")


def _qualify_members(population, population_pin, registration, member_exits,
                     receipts, *, output_reserve,
                            structural_reserve, slot_tokens, graph_config_hashes):
    """Preserve every configured member and reject partial or changed proofs."""
    try:
        labels = [label for cohort in population["cohorts"] for label in cohort["candidate_ids"]]
        _require(labels and len(set(labels)) == len(labels), "Configured candidates are empty or repeated")
        members = registration["members"]
        _require(registration["status"] == "ROOT-ADMITTED", "Capacity was not admitted")
        _require(registration["experiment_population"] == population_pin, "Population pin differs")
        _require(registration["sampling"] == population["sampling"], "Sampling differs")
        _require([m["label"] for m in members] == labels, "Ordered capacity members differ")
        _require(set(receipts) == set(labels), "Capacity receipts do not cover exactly the family")
        _require(set(graph_config_hashes) == set(labels), "Expected graph hashes do not cover the family")
        _require([m["label"] for m in member_exits] == labels, "Terminal members differ")
        _require(all(type(m["contact_cap"]) is int and m["contact_cap"] > 0 for m in members),
                 "Invalid capacity endpoint cap")
        budget = {"generation_contacts": 0, "scorer_contacts": 0,
                  "tokenizer_endpoint_caps": {m["label"]: m["contact_cap"] for m in members},
                  "tokenizer_endpoints_total": sum(m["contact_cap"] for m in members)}
        _require(registration["budget"] == budget, "Capacity budget differs")
        summary = []
        for member, exit_record in zip(members, member_exits, strict=True):
            label = member["label"]
            _require(member["experiment_population"] == population_pin, "Member population pin differs")
            roster = next(c["sample_ids"] for c in population["cohorts"] if label in c["candidate_ids"])
            result = _qualify_member(member, exit_record, registration, receipts[label], roster,
                                     output_reserve=output_reserve, structural_reserve=structural_reserve,
                                     slot_tokens=slot_tokens, graph_config_hash=graph_config_hashes[label])
            result["candidate_id"] = result.pop("label")
            summary.append(result)
        return {"schema": "saea-configured-capacity-family-review-v1",
                "experiment_population": dict(population_pin), "members": summary,
                "tokenizer_endpoints": sum(m["contacts"] for m in summary),
                "generation_contacts": 0, "scorer_contacts": 0,
                "root_review_required": True, "runtime_admission": False}
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError("Malformed capacity family evidence") from error


def _qualify_member(member, exit_record, registration, record, roster, *,
                    output_reserve, structural_reserve, slot_tokens, graph_config_hash):
    """Validate the same saved operational capacity evidence for every member."""
    _require(all(exit_record[k] == member[k] for k in ("label", "run_id", "attempt_id")),
             "Terminal run or attempt identity differs")
    _require(all(type(exit_record[k]) is int and exit_record[k] == 0 for k in ("exit_code", "lease_exit_code")),
             "Member or lease did not finish successfully")
    inputs, output = record["inputs"], record["output"]
    _require(record["contact_class"] == "tokenizer", "Capacity contact class differs")
    _require(content_hash(output) == record["output_sha256"], "Capacity output hash differs")
    _require(inputs["source_commit"] == registration["worker_commit"]
             and inputs["config_hash"] == member["composed_config_hash"]
             and inputs["graph_config_hash"] == graph_config_hash, "Capacity source differs")
    _require(sorted(inputs["roster"]) == sorted(roster), "Capacity source roster differs")
    _require(inputs["output_reserve"] == output_reserve
             and inputs["structural_reserve"] == structural_reserve, "Capacity reserves differ")
    _require(output["every_request_fits"] is True and output["generation_contacts"] == 0
             and output["scientific_results_read"] is False, "Invalid capacity-only result")
    _require(type(output["contacts"]) is int and 0 < output["contacts"] <= member["contact_cap"],
             "Capacity endpoint use exceeds registration")
    rows = output["rows"]
    _require(isinstance(rows, list) and rows, "No measured requests")
    for row in rows:
        margin = row["margin_after_structural_reserve"]
        _require(row["fits"] is True and row["maximum_completion_tokens"] == output_reserve
                 and row["additional_structural_reserve_tokens"] == structural_reserve
                 and row["slot_tokens"] == slot_tokens, "Measured request reserve or geometry differs")
        _require(type(margin) in (int, float) and math.isfinite(margin) and margin >= 0,
                 "Invalid remaining context margin")
    return {"label": member["label"], "run_id": member["run_id"],
            "attempt_id": member["attempt_id"], "contacts": output["contacts"],
            "measured_requests": len(rows),
            "minimum_margin_after_structural_reserve": min(r["margin_after_structural_reserve"] for r in rows),
            "capacity_output_sha256": record["output_sha256"]}


def qualify_precontact_capacity_epochs(population, population_pin, epochs,
                                      receipts, **limits):
    """Join completed prefixes after explicit precontact dispositions.

    Each failed epoch retains its actual nonzero terminal status and a startup
    receipt proving its next worker was not started. The caller verifies raw
    source pins, disposition authority, preserved lease identities, and absence
    of worker/contact evidence for each unstarted member. This function never creates a synthetic successful batch receipt. A recorded
    capacity-only amendment may change startup headroom, never the running floor
    or scientific inputs; every epoch retains its own resource policy.
    """
    try:
        _require(isinstance(epochs, list) and len(epochs) >= 2,
                 "Use the ordinary qualifier for a single epoch")
        original = epochs[0]["registration"]
        full = original["members"]
        labels = [m["label"] for m in full]
        exits, sources, summaries, seen = [], {}, [], set()
        for index, epoch in enumerate(epochs):
            identity = epoch["epoch_id"]
            _require(isinstance(identity, str) and identity and identity not in seen,
                     "Epoch identity is empty or repeated")
            seen.add(identity)
            reg, terminal, outer = (epoch[k] for k in
                                   ("registration", "finished", "windows_exit"))
            offset = len(exits)
            remaining = full[offset:]
            _require(remaining and reg["members"] == remaining,
                     "Epoch does not contain the exact unused suffix")
            _require(reg["status"] == "ROOT-ADMITTED", "Epoch was not admitted")
            _require(all(reg[k] == original[k] for k in
                         ("worker", "worker_commit", "experiment_population", "sampling")),
                     "Continuation source or policy differs")
            budget = {"generation_contacts": 0, "scorer_contacts": 0,
                      "tokenizer_endpoint_caps": {m["label"]: m["contact_cap"] for m in remaining},
                      "tokenizer_endpoints_total": sum(m["contact_cap"] for m in remaining)}
            _require(reg["budget"] == budget, "Continuation budget differs")
            if index:
                disposition = epoch["root_disposition"]
                _require(disposition["status"] == "decided"
                         and disposition["completed_candidate_ids"] == labels[:offset]
                         and disposition["eligible_candidate_ids"] == labels[offset:]
                         and disposition["eligible_run_ids"] == [m["run_id"] for m in remaining],
                         "Exact root continuation disposition is absent")
            if index:
                previous_policy = epochs[index-1]["registration"]["resource_policy"]
                next_policy = reg["resource_policy"]
                if next_policy != previous_policy:
                    amendment = disposition["resource_policy_amendment"]
                    _require(amendment["scope"] == "nongenerative-capacity-only"
                             and amendment["previous"] == previous_policy
                             and amendment["next"] == next_policy
                             and isinstance(amendment["reason"], str)
                             and bool(amendment["reason"].strip()),
                             "Capacity resource amendment is not explicitly bound")
                    _require({k: v for k, v in next_policy.items() if k != "start_gib"}
                             == {k: v for k, v in previous_policy.items() if k != "start_gib"},
                             "Only the capacity startup threshold may be amended")
                    _require(all(type(next_policy[k]) in (int, float)
                                 and math.isfinite(next_policy[k]) and next_policy[k] > 0
                                 for k in ("start_gib", "floor_gib"))
                             and next_policy["start_gib"] >= next_policy["floor_gib"],
                             "Invalid capacity startup threshold or running floor")
            completed = terminal["members"]
            _require(isinstance(completed, list) and len(completed) <= len(remaining),
                     "Epoch completed member list is invalid")
            for member, record in zip(remaining, completed):
                _require(all(record[k] == member[k] for k in ("label", "run_id", "attempt_id"))
                         and all(type(record[k]) is int and record[k] == 0
                                 for k in ("exit_code", "lease_exit_code")),
                         "Completed member identity or lease exit differs")
                sources[member["label"]] = identity
            code = terminal["exit_code"]
            _require(type(code) is int and type(outer["exit_code"]) is int
                     and outer["exit_code"] == code,
                     "Epoch and Windows exits differ")
            _require(all(type(terminal[k]) is int and terminal[k] == 0
                         for k in ("generation_contacts", "scorer_contacts")),
                     "Epoch added generation or scoring")
            if index == len(epochs)-1:
                _require(code == 0 and len(completed) == len(remaining),
                         "Final epoch has not completed the unused suffix")
            else:
                _require(code != 0 and len(completed) < len(remaining),
                         "A prior epoch is not a failed partial prefix")
                failure = epoch["precontact_failure"]
                _require(failure["candidate_id"] == remaining[len(completed)]["label"]
                         and failure["worker_started"] is False
                         and type(failure["exit_code"]) is int and failure["exit_code"] == 125
                         and failure["status"] in ("observation-failed", "wait-expired"),
                         "Prior failure was not a registered precontact wait failure")
            exits.extend(completed)
            summaries.append({"epoch_id": identity, "exit_code": code,
                              "completed_candidate_ids": [m["label"] for m in completed],
                              "resource_policy": dict(reg["resource_policy"]),
                              "evidence_sha256": content_hash(epoch)})
        review = _qualify_members(population, population_pin, original,
                                  exits, receipts, **limits)
        review.update(schema="saea-precontact-capacity-epochs-review-v1",
                      epochs=summaries, member_source_epochs=sources)
        return review
    except (KeyError, TypeError, AttributeError, IndexError) as error:
        raise ValueError("Malformed capacity epoch evidence") from error

_RECOVERY_LABELS = ("seed", "seed-aa", "review-off", "solver-lookup")
_RECOVERY_MEMBER_FIELDS = (
    "label", "member_id", "population_cohort", "execution_config", "execution_identity_sha256",
    "model_per_trajectory", "rehearsal_profile", "run_id", "attempt_id", "composed_config_hash",
    "capacity", "graph", "graph_config_hash", "graph_sample_ids", "contact_cap", "expected_rows", "graph_rows",
)
_RECOVERY_REGISTRATION_FIELDS = (
    "schema", "experiment_population", "sampling", "execution", "worker", "worker_commit", "budget", "new_receipt_root",
)


def architecture_capacity_recovery_binding(registration):
    """Return the prospective identity without circular authority/source-check pins.

    Bind the launched capacity cell as well as each source/config/run/attempt.
    Root disposition and compatibility pins can then be added to the registration
    without changing the identity they prospectively approve. This grants no contact.
    """
    try:
        return {**{k: deepcopy(registration[k]) for k in _RECOVERY_REGISTRATION_FIELDS},
                "members": [{k: deepcopy(m[k]) for k in _RECOVERY_MEMBER_FIELDS}
                            for m in registration["members"]]}
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError("Malformed architecture recovery registration binding") from error


def _recovery_raw(raw, pin):
    """Verify caller-supplied immutable bytes without opening any path."""
    _require(isinstance(pin, dict) and set(pin) == {"path", "sha256"}
             and isinstance(pin["path"], str) and bool(pin["path"]), "Malformed recovery evidence pin")
    sha(pin["sha256"])
    _require(isinstance(raw, bytes) and hashlib.sha256(raw).hexdigest() == pin["sha256"],
             "Recovery evidence raw bytes differ from their pin")
    return raw


def _recovery_source(entry, schema, labels, receipt_labels, config, pin, graphs):
    """Check one real source envelope; preserve its outer disposition verbatim."""
    reg = entry["registration"]
    _require(content_hash(reg) == content_hash(entry["original_registration"]),
             "Recovery source differs from its independently pinned registration")
    _require(reg["schema"] == schema and reg["status"] == "ROOT-ADMITTED",
             "Recovery source schema or admission differs")
    _require(reg["experiment_population"] == pin and reg["sampling"] == config["sampling"]
             and reg["execution"] == config["execution"], "Recovery population or execution differs")
    _require(isinstance(reg["worker"], str) and reg["worker"]
             and isinstance(reg["worker_commit"], str) and re.fullmatch(r"[a-f0-9]{40}", reg["worker_commit"]),
             "Recovery requires an immutable worker source")
    source = entry["source_check"]
    _require(content_hash(source) == reg["source_check_sha256"]
             and source["source_commit"] == reg["worker_commit"] and source["experiment_population"] == pin
             and all(type(source[k]) is int and source[k] == 0 for k in
                     ("exit_code", "generation_contacts", "tokenizer_contacts", "scorer_contacts")),
             "Recovery source check is unsuccessful or cross-bound")
    members = reg["members"]
    _require([m["label"] for m in members] == labels
             and [m["label"] for m in entry["finished"]["members"]] == labels
             and set(entry["member_terminals"]) == set(graphs) == set(labels)
             and set(entry["receipts"]) == set(receipt_labels), "Recovery source coverage differs")
    _require(all(isinstance(m[k], str) and m[k] for m in members for k in ("run_id", "attempt_id", "capacity", "graph"))
             and all(len({m[k] for m in members}) == len(members) for k in ("run_id", "attempt_id")),
             "Recovery source identities are empty or repeated")
    _require(all(type(m["contact_cap"]) is int and m["contact_cap"] > 0 for m in members),
             "Recovery endpoint cap is invalid")
    budget = {"generation_contacts": 0, "scorer_contacts": 0,
              "tokenizer_endpoint_caps": {m["label"]: m["contact_cap"] for m in members},
              "tokenizer_endpoints_total": sum(m["contact_cap"] for m in members)}
    _require(content_hash(reg["budget"]) == content_hash(budget), "Recovery source budget differs")
    _require(all(graphs[m["label"]] == m["graph_config_hash"] for m in members),
             "Recovery graph differs from independently verified source")
    _require(all(type(entry["finished"][k]) is int and entry["finished"][k] == 0
                 for k in ("generation_contacts", "scorer_contacts")), "Recovery source added generation or scoring")
    return reg


def qualify_architecture_capacity_recovery(population, population_pin, original_evidence_bytes, recovery, *,
                                           original_evidence_pin, root_disposition_bytes, root_disposition_pin,
                                           source_compatibility_bytes, source_compatibility_pin,
                                           failed_contacts_bytes, failed_contacts_pin, policy_config_bytes,
                                           graph_config_hashes, output_reserve, structural_reserve, slot_tokens):
    """Qualify exactly three original successes and one fresh Solver recovery.

    This explicit opt-in never relaxes the complete-family or precontact APIs.
    The original raw-hash-pinned operational envelope contains registration,
    original_registration, source_check, finished, windows_exit, member_terminals
    for all four members, receipts for exactly the first three, and pins for the
    original registration/finished/windows_exit files. The caller verifies those
    original files against these pins, plus graph source hashes and policy bytes.
    Recovery has its own original_registration/source/terminal/receipt envelope.

    Root disposition prospectively pins the canonical original envelope and the
    acyclic new registration identity, not future recovery results. Its pinned
    compatibility evidence explicitly approves reuse under the changed source.
    The separately pinned failed contact JSONL is counted without reading task
    responses. Actual original outer exit 1 and failed spend remain in the result.
    No member is rerun here, no synthetic successful outer is created, and this
    pure validator grants neither runtime nor task-quality READ authority.
    """
    try:
        _pin(population_pin)
        config = validate_population_config(population, allow_architecture=True)
        identities = config["architecture"]["members"]
        labels = list(_RECOVERY_LABELS)
        reused, recovered = labels[:3], labels[-1]
        _require(config["schema"] == "saea-experiment-population-config-v4"
                 and [m["member_id"] for m in identities] == labels, "Unsupported recovery architecture family")
        _require((output_reserve, structural_reserve, slot_tokens) == (512, 2048, 24576)
                 and all(type(v) is int for v in (output_reserve, structural_reserve, slot_tokens)),
                 "Unsupported recovery capacity geometry")
        _require(set(policy_config_bytes) == set(labels) and set(graph_config_hashes) == {"original", "recovery"},
                 "Recovery policy or graph coverage differs")
        original = json.loads(_recovery_raw(original_evidence_bytes, original_evidence_pin))
        disposition = json.loads(_recovery_raw(root_disposition_bytes, root_disposition_pin))
        compatible = json.loads(_recovery_raw(source_compatibility_bytes, source_compatibility_pin))
        old = _recovery_source(original, "saea-architecture-capacity-entry-v1", labels, reused,
                               config, population_pin, graph_config_hashes["original"])
        new = _recovery_source(recovery, "saea-architecture-capacity-recovery-entry-v1", [recovered], [recovered],
                               config, population_pin, graph_config_hashes["recovery"])
        _require(not any(k in m for envelope in (original, recovery)
                         for m in envelope["registration"]["members"]
                         for k in ("runtime_sample_ids", "runtime_graph_sample_ids")),
                 "Explicit runtime order requires the complete-family capacity API")
        for key in ("registration", "finished", "windows_exit"):
            _require(new["original_" + key] == original["pins"][key], "Original source pin differs")
        _require(new["original_evidence"] == original_evidence_pin
                 and new["root_recovery_disposition"] == root_disposition_pin
                 and new["source_compatibility"] == source_compatibility_pin, "Recovery authority pins differ")
        _require(disposition["schema"] == "saea-architecture-capacity-root-recovery-disposition-v1"
                 and disposition["status"] == "decided"
                 and disposition["scope"] == "nongenerative-architecture-capacity-recovery-only"
                 and type(disposition["recovery_ordinal"]) is int and disposition["recovery_ordinal"] == 1
                 and disposition["experiment_population"] == population_pin
                 and disposition["reused_member_ids"] == reused and disposition["recovered_member_id"] == recovered
                 and disposition["original_evidence_sha256"] == content_hash(original)
                 and disposition["original_registration_sha256"] == content_hash(old)
                 and disposition["recovery_binding_sha256"] == content_hash(architecture_capacity_recovery_binding(new))
                 and disposition["source_compatibility"] == source_compatibility_pin
                 and disposition["failed_contacts"] == failed_contacts_pin, "Exact prospective recovery disposition is absent")
        _require(old["worker_commit"] != new["worker_commit"] and old["worker"] != new["worker"]
                 and old["new_receipt_root"] != new["new_receipt_root"], "Recovery must retain a separate frozen source and entry")
        unchanged = {m["label"]: {k: m[k] for k in
                     ("execution_identity_sha256", "graph_config_hash", "graph_sample_ids", "model_per_trajectory")}
                     for m in old["members"][:3]}
        _require(compatible["schema"] == "saea-architecture-capacity-source-compatibility-v1"
                 and compatible["status"] == "ROOT-VERIFIED" and compatible["scope"] == "solver-lookup-routing-only"
                 and compatible["experiment_population"] == population_pin
                 and compatible["source_commits"] == {"original": old["worker_commit"], "recovery": new["worker_commit"]}
                 and compatible["reused_member_ids"] == reused and compatible["changed_member_id"] == recovered
                 and content_hash(compatible["unchanged_members"]) == content_hash(unchanged)
                 and compatible["passed"] is True and all(type(compatible[k]) is int and compatible[k] == 0
                     for k in ("generation_contacts", "tokenizer_contacts", "scorer_contacts")),
                 "Exact model-free source compatibility evidence is absent")
        failed, replacement = old["members"][-1], new["members"][0]
        fixed = set(_RECOVERY_MEMBER_FIELDS) - {"run_id", "attempt_id", "capacity", "composed_config_hash"}
        _require(all(replacement[k] == failed[k] for k in fixed), "Recovered policy, graph, roster or capacity ceiling changed")
        _require(all(replacement[k] not in {m[k] for m in old["members"]}
                     for k in ("run_id", "attempt_id", "capacity", "composed_config_hash")),
                 "Recovery reuses a spent identity or capacity cell")
        for source, expected_code in ((original, 1), (recovery, 0)):
            _require(all(type(source[k]["exit_code"]) is int and source[k]["exit_code"] == expected_code
                         for k in ("finished", "windows_exit")), "Recovery source outer status differs")
        _require(bool(original["finished"]["failure"]) and recovery["finished"]["failure"] is None,
                 "Recovery must preserve the actual failed original")
        failure_outer = original["finished"]["members"][-1]
        failure_terminal = original["member_terminals"][recovered]
        _require(all(failure_outer[k] == failed[k] for k in ("label", "run_id", "attempt_id"))
                 and type(failure_outer["exit_code"]) is int and failure_outer["exit_code"] == 1
                 and type(failure_outer["observer_exit_code"]) is int and failure_outer["observer_exit_code"] == 0
                 and type(failure_terminal["exit_code"]) is int and failure_terminal["exit_code"] == 1
                 and all(type(failure_terminal[k]) is int and failure_terminal[k] == 0
                         for k in ("generation_contacts", "scorer_contacts"))
                 and len(failure_terminal["members"]) == 1, "Original Solver failure evidence differs")
        failed_child = failure_terminal["members"][0]
        _require(all(failed_child[k] == failed[k] for k in ("label", "run_id", "attempt_id"))
                 and type(failed_child["exit_code"]) is int and failed_child["exit_code"] == 1
                 and type(failed_child["lease_exit_code"]) is int and failed_child["lease_exit_code"] != 0,
                 "Original failed child identity or lease differs")
        contacts = [json.loads(line) for line in _recovery_raw(failed_contacts_bytes, failed_contacts_pin).splitlines()
                    if line.strip()]
        _require(0 < len(contacts) <= failed["contact_cap"] and all(
            c["run_id"] == failed["run_id"] and c["attempt_id"] == failed["attempt_id"]
            and type(c["contact"]) is int and c["contact"] == i
            and (c["method"], c["route"]) in (("GET", "/props"), ("POST", "/tokenize"))
            for i, c in enumerate(contacts, 1)), "Failed Solver endpoint accounting differs")
        cohorts = {c["cohort_id"]: c for c in config["cohorts"]}
        summary = []
        for index, identity in enumerate(identities):
            source_name = "original" if index < 3 else "recovery"
            source = original if index < 3 else recovery
            member = old["members"][index] if index < 3 else replacement
            outer = source["finished"]["members"][index if index < 3 else 0]
            label = member["label"]
            result = _qualify_architecture_member(
                identity, member, outer, source["member_terminals"][label], source["receipts"][label],
                source["registration"], cohorts[identity["cohort_id"]], policy_config_bytes[label],
                graph_config_hashes[source_name][label], output_reserve=output_reserve,
                structural_reserve=structural_reserve, slot_tokens=slot_tokens)
            result.update(source=source_name, source_commit=source["registration"]["worker_commit"],
                          registration_sha256=content_hash(source["registration"]))
            summary.append(result)
        endpoints = sum(m["contacts"] for m in summary)
        return {"schema": "saea-architecture-capacity-recovery-review-v1", "experiment_population": deepcopy(population_pin),
                "members": summary, "tokenizer_endpoints": endpoints, "failed_attempt_tokenizer_endpoints": len(contacts),
                "spent_tokenizer_endpoints": endpoints + len(contacts), "generation_contacts": 0, "scorer_contacts": 0,
                "sources": [{"source": label, "exit_code": source["finished"]["exit_code"],
                    "worker_commit": source["registration"]["worker_commit"],
                    "evidence_sha256": content_hash(source)} for label, source in (("original", original), ("recovery", recovery))],
                "original_evidence_sha256": content_hash(original), "recovery_evidence_sha256": content_hash(recovery),
                "root_disposition_pin": deepcopy(root_disposition_pin), "source_compatibility_pin": deepcopy(source_compatibility_pin),
                "failed_contacts_pin": deepcopy(failed_contacts_pin), "root_review_required": True,
                "runtime_admission": False, "read_authorized": False}
    except (KeyError, TypeError, AttributeError, IndexError, UnicodeError) as error:
        raise ValueError("Malformed architecture capacity recovery evidence") from error
