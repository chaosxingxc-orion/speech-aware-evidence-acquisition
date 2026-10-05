"""Qualify complete configured capacity evidence for root structural review.

Reuse the shared runtime's capacity records. Do not dispatch, read task quality,
change a source, or grant runtime admission. The caller must verify file pins,
registered read scope, terminal process identities and fresh live gates.
"""
from __future__ import annotations

import math
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
            _require(all(exit_record[k] == member[k] for k in ("label", "run_id", "attempt_id")),
                     "Terminal run or attempt identity differs")
            _require(all(type(exit_record[k]) is int and exit_record[k] == 0 for k in ("exit_code", "lease_exit_code")),
                     "Member or lease did not finish successfully")
            record = receipts[label]
            inputs, output = record["inputs"], record["output"]
            _require(record["contact_class"] == "tokenizer", "Capacity contact class differs")
            _require(content_hash(output) == record["output_sha256"], "Capacity output hash differs")
            _require(inputs["source_commit"] == registration["worker_commit"]
                     and inputs["config_hash"] == member["composed_config_hash"]
                     and inputs["graph_config_hash"] == graph_config_hashes[label], "Capacity source differs")
            roster = next(c["sample_ids"] for c in population["cohorts"] if label in c["candidate_ids"])
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
            summary.append({"candidate_id": label, "run_id": member["run_id"],
                            "attempt_id": member["attempt_id"], "contacts": output["contacts"],
                            "measured_requests": len(rows),
                            "minimum_margin_after_structural_reserve": min(r["margin_after_structural_reserve"] for r in rows),
                            "capacity_output_sha256": record["output_sha256"]})
        return {"schema": "saea-configured-capacity-family-review-v1",
                "experiment_population": dict(population_pin), "members": summary,
                "tokenizer_endpoints": sum(m["contacts"] for m in summary),
                "generation_contacts": 0, "scorer_contacts": 0,
                "root_review_required": True, "runtime_admission": False}
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError("Malformed capacity family evidence") from error


def qualify_precontact_capacity_epochs(population, population_pin, epochs,
                                      receipts, **limits):
    """Join completed prefixes after explicit precontact dispositions.

    Each failed epoch retains its actual nonzero terminal status and a startup
    receipt proving its next worker was not started. The caller verifies raw
    source pins, disposition authority, and per-epoch absence of lease/contact
    evidence. This function never creates a synthetic successful batch receipt.
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
                         ("worker", "worker_commit", "experiment_population", "sampling", "resource_policy")),
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
                         and failure["status"] == "observation-failed",
                         "Prior failure was not the registered precontact observation")
            exits.extend(completed)
            summaries.append({"epoch_id": identity, "exit_code": code,
                              "completed_candidate_ids": [m["label"] for m in completed],
                              "evidence_sha256": content_hash(epoch)})
        review = _qualify_members(population, population_pin, original,
                                  exits, receipts, **limits)
        review.update(schema="saea-precontact-capacity-epochs-review-v1",
                      epochs=summaries, member_source_epochs=sources)
        return review
    except (KeyError, TypeError, AttributeError, IndexError) as error:
        raise ValueError("Malformed capacity epoch evidence") from error
