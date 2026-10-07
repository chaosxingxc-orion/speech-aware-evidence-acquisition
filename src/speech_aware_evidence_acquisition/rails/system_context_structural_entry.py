"""Qualify complete configured capacity evidence for root structural review.

Reuse the shared runtime's capacity records. Do not dispatch, read task quality,
change a source, or grant runtime admission. The caller must verify file pins,
registered read scope, terminal process identities and fresh live gates.
"""
from __future__ import annotations

import math
from copy import deepcopy
from .experiment_population import validate_population_config
from .hashing import content_hash


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
