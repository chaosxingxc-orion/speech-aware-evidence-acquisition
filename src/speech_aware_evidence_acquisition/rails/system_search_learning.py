"""Record configured aggregate search proposals through the shared policy compiler.

This storage boundary does not qualify scientific feedback or admit actor/model
contacts. Its caller must first prepare a source-qualified aggregate input, pin
its isolated actor capsule and register the exact contact allowance. A private
registration binds those identities here; hashes alone do not establish READ
permission. No execution API calls this prospective interface yet.
"""
from __future__ import annotations

import json
import re

from .experiment_population import load_population_config, population_accounting
from .hashing import content_hash
from .system_search_archive import SystemSearchArchive
from .system_text_policy import (
    SEARCH_ALGORITHMS, TextPolicyUpdateProposal, _read_pin, apply_text_proposal,
    require, require_search_parent_compatibility, sha, validate_sources,
)


def _registration(archive, registration_pin, repo_root):
    require(isinstance(archive, SystemSearchArchive), "shared archive required")
    d = json.loads(_read_pin(registration_pin, repo_root))
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
