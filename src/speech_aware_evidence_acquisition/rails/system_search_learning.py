"""Record configured aggregate search proposals through the shared policy compiler.

This storage boundary does not qualify scientific feedback or admit actor/model
contacts. Its caller must first prepare a source-qualified aggregate input, pin
its isolated actor capsule and register the exact contact allowance. A private
registration binds those identities here; hashes alone do not establish READ
permission. No execution API calls this prospective interface yet.
"""
from __future__ import annotations

from copy import deepcopy
import json
import re

from .experiment_population import load_population_config, population_accounting
from .hashing import content_hash
from .system_search_archive import SystemSearchArchive
from .system_text_policy import (
    SEARCH_ALGORITHMS, TextPolicyUpdateProposal, _read_pin, apply_text_proposal,
    require, require_search_parent_compatibility, sha, validate_sources, cumulative_sources, _text,
)


def _registration(archive, registration_pin, repo_root):
    d = json.loads(_read_pin(registration_pin, repo_root))
    return _validate_registration(archive, d, repo_root)


def _validate_registration(archive, d, repo_root):
    require(isinstance(archive, SystemSearchArchive), "shared archive required")
    fields = {"schema", "status", "batch_id", "algorithm", "iteration", "experiment_population",
              "qualified_input_sha256", "actor_input_sha256", "slots", "evidence_record_ids", "cumulative_sources"}
    require(isinstance(d, dict) and set(d) == fields
            and d["schema"] == "saea-search-update-registration-v1" and d["status"] == "ROOT_REGISTERED",
            "exact root search registration required")
    require(isinstance(d["batch_id"], str) and re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", d["batch_id"])
            and d["algorithm"] in SEARCH_ALGORITHMS
            and type(d["iteration"]) is int and d["iteration"] > 0,
            "search identity differs")
    for key in ("qualified_input_sha256", "actor_input_sha256"):
        sha(d[key])
    require(isinstance(d["evidence_record_ids"], list), "aggregate evidence identities required")
    for item in d["evidence_record_ids"]:
        sha(item)
    require(len(set(d["evidence_record_ids"])) == len(d["evidence_record_ids"]), "duplicate aggregate evidence")
    validate_sources(d["cumulative_sources"])
    population = load_population_config(d["experiment_population"], repo_root=repo_root)
    positions = [(c["cohort_id"], cid) for c in population["cohorts"] for cid in c["candidate_ids"]]
    require(isinstance(d["slots"], list) and len(d["slots"]) == len(positions), "configured search slots differ")
    for slot, (cohort, candidate) in zip(d["slots"], positions, strict=True):
        require(isinstance(slot, dict) and set(slot) == {"candidate_id", "cohort_id", "mode", "parent_bundle_ids"}
                and slot["candidate_id"] == candidate and slot["cohort_id"] == cohort,
                "search slot order differs from population")
        # Use the same validator for planned identities and actual proposals.
        TextPolicyUpdateProposal.from_search_json({"schema": "saea-search-policy-update-proposal-v1",
            "algorithm": d["algorithm"], "iteration": d["iteration"], "candidate_id": candidate,
            "mode": slot["mode"], "parent_ids": slot["parent_bundle_ids"], "changes": {},
            "rationale": "Validate the registered search position.", "hypotheses": [], "evidence": []})
        require_search_parent_compatibility([archive.load_policy(p) for p in slot["parent_bundle_ids"]])
    require_search_parent_compatibility([archive.load_policy(p) for slot in d["slots"]
                                         for p in slot["parent_bundle_ids"]])
    return d, population


def _reservation(d, population, registration_pin):
    return {"schema": "saea-search-update-reservation-v1", "registration": registration_pin,
            "registration_sha256": content_hash(d), "experiment_population": d["experiment_population"],
            "qualified_input_sha256": d["qualified_input_sha256"], "actor_input_sha256": d["actor_input_sha256"],
            "algorithm": d["algorithm"], "iteration": d["iteration"], "slots": d["slots"],
            "proposal_slots": len(d["slots"]), "proposer": population["proposer"],
            "population_budget": population_accounting(population), "runtime_admission": False,
            "scope": "Spent proposal positions only; source qualification and contact admission remain external."}


def reserve_search_update(archive, *, registration_pin, repo_root):
    """Spend all configured slots before contact; never allocate a replacement."""
    d, population = _registration(archive, registration_pin, repo_root)
    record = _reservation(d, population, registration_pin)
    archive._write(f"context-learning/search-updates/{d['batch_id']}/reservation.json", record)
    return record


def _envelope(response, d, population):
    r = response
    require(isinstance(r, dict) and set(r) == {"schema", "registration_sha256", "actor_input_sha256",
            "model", "reasoning_effort", "usage", "proposals"}
            and r["schema"] == "saea-search-update-response-v1"
            and r["registration_sha256"] == content_hash(d)
            and r["actor_input_sha256"] == d["actor_input_sha256"]
            and all(r[k] == population["proposer"][k] for k in ("model", "reasoning_effort")),
            "original search response envelope differs")
    require(isinstance(r["usage"], dict) and set(r["usage"]) == {"provider_contacts", "input_tokens", "output_tokens"}
            and all(v is None or type(v) is int and v >= 0 for v in r["usage"].values()),
            "provider usage must retain measured values or explicit unknowns")
    require(isinstance(r["proposals"], list) and len(r["proposals"]) == len(d["slots"])
            and all(isinstance(p, dict) and p.get("candidate_id") == s["candidate_id"]
                    for p, s in zip(r["proposals"], d["slots"], strict=True)),
            "original response positions differ; no reorder or replacement")


def record_search_update(archive, *, registration_pin, repo_root, response_document):
    """Archive the one original response, materialize valid positions, never activate.

    Preserve no-change children with new exposure and ancestry. Envelope failures
    consume the entire batch; individual illegal edits consume their own slots.
    Storage failures propagate after original-response preservation and require
    incident disposition rather than a silent replay.
    """
    d, population = _registration(archive, registration_pin, repo_root)
    base = f"context-learning/search-updates/{d['batch_id']}"
    path = archive.root / base / "reservation.json"
    require(path.is_file(), "search positions must be reserved before contact")
    require(json.loads(path.read_text()) == _reservation(d, population, registration_pin),
            "immutable search reservation differs")
    raw = {"schema": "saea-search-update-original-response-v1", "registration": registration_pin,
           "response_sha256": content_hash(response_document), "response_document": response_document}
    archive._write(base + "/response.json", raw)
    result = {"schema": "saea-search-update-result-v1", "registration": registration_pin,
              "response_sha256": raw["response_sha256"], "status": "recorded", "records": [],
              "usage": None, "runtime_admission": False,
              "experiment_population": d["experiment_population"], "algorithm": d["algorithm"],
              "iteration": d["iteration"], "population_budget": population_accounting(population)}
    try:
        _envelope(response_document, d, population)
    except ValueError as error:
        result.update(status="invalid-envelope", error=str(error),
                      records=[{"candidate_id": s["candidate_id"], "status": "invalid"} for s in d["slots"]])
    else:
        result["usage"] = dict(response_document["usage"])
        for slot, payload in zip(d["slots"], response_document["proposals"], strict=True):
            entry = {"candidate_id": slot["candidate_id"], "proposal_sha256": content_hash(payload)}
            try:
                proposal = TextPolicyUpdateProposal.from_search_json(payload)
                require(payload["algorithm"] == d["algorithm"] and payload["iteration"] == d["iteration"]
                        and payload["mode"] == slot["mode"] and payload["parent_ids"] == slot["parent_bundle_ids"],
                        "proposal differs from its registered search position")
                require(set(payload["evidence"]) <= set(d["evidence_record_ids"]), "unregistered aggregate evidence")
                parents = [archive.load_policy(p) for p in slot["parent_bundle_ids"]]
                sources = [*d["cumulative_sources"], {"kind": "proposal", "sha256": content_hash(payload),
                    "sample_ids": sorted({sid for s in d["cumulative_sources"] for sid in s["sample_ids"]})}]
                child = apply_text_proposal(proposal, parents=parents, added_sources=sources)
                keys = ("role_text", "node_context", "context_layout")
                unchanged = all(child.as_json()[k] == parents[0].as_json()[k] for k in keys)
            except ValueError as error:
                entry.update(status="invalid", error=str(error))
            else:
                # Keep storage exceptions outside validation handling: do not call
                # a partial write an invalid proposal or automatically repair it.
                archive.store_policy(child)
                entry.update(status="no-change" if unchanged else "materialized-policy", bundle_id=child.bundle_id,
                             parent_bundle_ids=slot["parent_bundle_ids"])
            result["records"].append(entry)
    archive._write(base + "/result.json", result)
    return result


def require_search_evaluation_binding(recipe, registration, protocol, *, root, config):
    """Bind prospective evaluation to original spent slots and recorded children.

    Pins address exact create-only reservation/result metadata copied into the
    registered repository. Raw responses and cumulative sources remain private.
    This gate grants neither source READ nor runtime admission. The shared scope,
    prelaunch policy-byte check, complete-family seals and exact READ still apply.
    """
    binding = protocol.get("search_evaluation")
    require(isinstance(binding, dict) and set(binding) == {"reservation", "result"}
            and all(d.get("search_evaluation") == binding for d in (recipe, registration)),
            "exact search evaluation pins required at every stage")
    reserved = json.loads(_read_pin(binding["reservation"], root))
    result = json.loads(_read_pin(binding["result"], root))
    require(reserved.get("schema") == "saea-search-update-reservation-v1"
            and result.get("schema") == "saea-search-update-result-v1"
            and result.get("status") == "recorded"
            and reserved.get("runtime_admission") is False and result.get("runtime_admission") is False,
            "original unactivated search records required")
    algorithm = reserved.get("algorithm")
    require(algorithm in SEARCH_ALGORITHMS and protocol.get("algorithms") == [algorithm]
            and result.get("algorithm") == algorithm
            and type(reserved.get("iteration")) is int
            and reserved["iteration"] == result.get("iteration") == protocol.get("iteration"),
            "search algorithm or iteration differs")
    expected_budget = population_accounting(config)
    require(all(d.get("experiment_population") == protocol["experiment_population"]
                and d.get("population_budget") == expected_budget for d in (reserved, result))
            and reserved.get("proposer") == config["proposer"],
            "search records differ from the pinned population")
    require(result.get("registration") == reserved.get("registration")
            and isinstance(reserved.get("registration"), dict)
            and set(reserved["registration"]) == {"relpath", "sha256"}
            and bool(reserved["registration"]["relpath"]), "search registration identity differs")
    sha(reserved["registration"]["sha256"])
    for key in ("registration_sha256", "qualified_input_sha256", "actor_input_sha256"):
        sha(reserved.get(key))
    sha(result.get("response_sha256"))
    positions = [(c["cohort_id"], cid) for c in config["cohorts"] for cid in c["candidate_ids"]]
    slots, records = reserved.get("slots"), result.get("records")
    require(isinstance(slots, list) and isinstance(records, list)
            and len(slots) == len(records) == len(positions)
            and type(reserved.get("proposal_slots")) is int
            and reserved["proposal_slots"] == len(positions), "complete original search positions required")
    for slot, record, (cohort, cid) in zip(slots, records, positions, strict=True):
        require(isinstance(slot, dict)
                and set(slot) == {"candidate_id", "cohort_id", "mode", "parent_bundle_ids"}
                and slot["candidate_id"] == cid and slot["cohort_id"] == cohort
                and isinstance(record, dict) and record.get("candidate_id") == cid,
                "original search position order differs")
        TextPolicyUpdateProposal.from_search_json({"schema": "saea-search-policy-update-proposal-v1",
            "algorithm": algorithm, "iteration": reserved["iteration"], "candidate_id": cid,
            "mode": slot["mode"], "parent_ids": slot["parent_bundle_ids"], "changes": {},
            "rationale": "Verify original reserved search identity.", "hypotheses": [], "evidence": []})
        # An invalid member is never replaced or silently dropped from its cohort.
        if cohort == protocol["population_cohort"]:
            require(record.get("status") in {"materialized-policy", "no-change"}
                    and record.get("parent_bundle_ids") == slot["parent_bundle_ids"],
                    "evaluated search positions must retain valid original children and parents")
            sha(record.get("proposal_sha256"))
            sha(record.get("bundle_id"))
            require(registration["member_bindings"][cid]["bundle_id"] == record["bundle_id"],
                    "runtime policy differs from the recorded original child")
    return algorithm



def assemble_search_actor_input(archive, *, feedback_record, configuration, repo_root):
    """Build a reviewable draft from prepared evidence; grant no source/contact rights.

    The caller must bind the original source-qualified feedback and parent plan,
    recheck their complete-family authority, and register the isolated capsule before
    contact. This pure assembler validates structure, ancestry and privacy separation;
    self-hashed objects do not establish scientific READ permission. Return a DRAFT
    recorder registration so that this helper cannot silently spend proposal slots.
    """
    c, f = deepcopy(configuration), feedback_record
    require(isinstance(c, dict) and set(c) == {"batch_id", "algorithm", "iteration",
        "experiment_population", "slots", "parent_plan_sha256", "instructions", "max_actor_input_bytes"},
        "exact configured actor draft required")
    sha(c["parent_plan_sha256"])
    _text(c["instructions"])
    require(type(c["max_actor_input_bytes"]) is int and c["max_actor_input_bytes"] > 0,
            "positive actor byte limit required")
    require(isinstance(f, dict) and f.get("schema") == "saea-qualified-aggregate-search-feedback-v1"
        and f.get("feedback_sha256") == content_hash({k:v for k,v in f.items() if k != "feedback_sha256"})
        and all(f.get(k) is False for k in ("runtime_admission", "learner_exported", "proposal_allocation_granted")),
        "immutable prepared aggregate feedback required")
    view = f["aggregate_feedback"]
    require(set(view) == {"schema", "records", "comparators", "statistic_columns", "limitations",
                         "process_encoding", "observed_populations"}
        and view["schema"] == "saea-aggregate-search-feedback-view-v1", "aggregate-only feedback required")
    record_fields = {"evaluated_iteration", "candidate_id", "cohort", "source_batch", "sample_order_sha256",
        "sample_count", "disposition", "is_active_parent", "template", "selection", "business", "comparators",
        "terminal", "node_statistics", "process", "record_id"}
    require(bool(view["records"]), "complete aggregate history required")
    for record in view["records"]:
        require(set(record) == record_fields and record["record_id"] == content_hash({
            k:v for k,v in record.items() if k != "record_id"}), "aggregate record identity or fields changed")
    population = load_population_config(c["experiment_population"], repo_root=repo_root)
    parents = {pid: archive.load_policy(pid) for slot in c["slots"] for pid in slot["parent_bundle_ids"]}
    source_identity = content_hash({"feedback_sha256": f["feedback_sha256"],
        "parent_plan_sha256": c["parent_plan_sha256"], "configuration": c})
    actor = {"schema": "saea-aggregate-search-actor-draft-v1", "source_identity_sha256": source_identity,
        "algorithm": c["algorithm"], "iteration": c["iteration"], "experiment_population": c["experiment_population"],
        "model": population["proposer"]["model"], "reasoning_effort": population["proposer"]["reasoning_effort"],
        "nodes": population["nodes"], "sampling": population["sampling"], "slots": c["slots"],
        "population_budget": population_accounting(population), "feedback": deepcopy(view),
        "parent_templates": {pid: {k: p.as_json()[k] for k in ("role_text", "context_layout", "node_context")}
                             for pid, p in parents.items()},
        "instructions": c["instructions"], "runtime_admission": False,
        "response_contract": {"schema": "saea-search-policy-update-proposal-v1",
            "ordered_candidates": [s["candidate_id"] for s in c["slots"]],
            "editable_fields": ["role_text", "context_layout", "node_context"],
            "rationale_and_hypotheses": "English template-level explanations; reference aggregate record IDs only.",
            "no_change_and_invalid": "Every original position remains spent; no replacement or extra proposal.",
            "transport": "Provider identity, usage and registration hashes are attached by the admitted receiver."}}
    sources = cumulative_sources(list(parents.values()), [{"kind": "feedback", "sha256": f["feedback_sha256"],
        "sample_ids": f["private_custody"]["feedback_sample_ids"]}])
    reg = {"schema": "saea-search-update-registration-v1", "status": "ROOT_REGISTERED",
        **{k: c[k] for k in ("batch_id", "algorithm", "iteration", "experiment_population", "slots")},
        "qualified_input_sha256": source_identity, "actor_input_sha256": content_hash(actor),
        "evidence_record_ids": [r["record_id"] for r in view["records"]], "cumulative_sources": sources}
    _validate_registration(archive, reg, repo_root)
    require(len(json.dumps(actor, ensure_ascii=True).encode()) <= c["max_actor_input_bytes"],
            "complete actor byte budget exceeded")
    reg["status"] = "DRAFT"
    result = {"schema": "saea-search-input-draft-v1", "actor_view": actor, "registration_draft": reg,
        "parent_plan_sha256": c["parent_plan_sha256"], "feedback_sha256": f["feedback_sha256"],
        "source_qualification_required": True, "runtime_admission": False, "learner_exported": False,
        "proposal_allocation_granted": False}
    result["draft_sha256"] = content_hash(result)
    return result
