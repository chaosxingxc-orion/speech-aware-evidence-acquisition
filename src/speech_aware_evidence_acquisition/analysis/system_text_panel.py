"""Read complete registered eight-arm prefixes of the retained optimization pool.

Reuse official scoring custody and whole-system statistics. A panel registration
never grants generation, scoring, scaling or formal adoption authority.
"""

import json
import hashlib
from pathlib import Path
from dataclasses import dataclass

from ..rails.hashing import content_hash
from ..rails.system_optimization import (
    LEARNING_MEMBERS as LEARNING_MEMBERS,
    PANEL_SIZES,
    require_panel_scope,
    panel_identities as identities,
    panel_member_run_id as member_run_id,
)
from ..rails.system_text_policy import _read_pin, canonical, require, sha
from .system_text_pilot import (
    MEMBERS,
    _attach_answer_changes,
    _learning_projection,
    _read_complete_evidence,
)
from .system_text_update import _describe_complete_cohort

SCHEMA = "saea-complete-system-panel-evidence-v1"
REGISTRATION_SCHEMA = "saea-fixed400-system-panel-registration-v1"


def scope_record(registration, owner, growth):
    """Keep only source commitments in the scope shared with the L proposer."""
    return {
        "family_id": registration["family_id"],
        "proposal_round": registration["proposal_round"],
        "rows": registration["rows_per_member"],
        "read_id": registration["read_id"],
        "registration_sha256": registration["registration_sha256"],
        "pool_sample_ids_sha256": registration["pool_sample_ids_sha256"],
        "prefix_sample_ids_sha256": registration["prefix_sample_ids_sha256"],
        "proposal_protocol_sha256": registration["proposal_protocol_sha256"],
        "pool_owner_sha256": content_hash(owner),
        "growth_owner_sha256": content_hash(growth),
    }


def validate_definition(recipe, registration, owner, *, growth, protocol, pool_ids):
    """Validate prospective scope without granting or fabricating READ authority."""
    profile = protocol.get("measurement_profile")
    require(recipe.get("measurement_profile") == registration.get("measurement_profile") == profile,
            "panel measurement profile differs from protocol or READ recipe")
    if profile is not None:
        from ..rails.system_search_measurement import validate_profile
        validate_profile(profile)
    require(
        owner.get("decision_id") == 224
        and owner.get("status") == "approved"
        and owner.get("progressive_sizes") == list(PANEL_SIZES),
        "approved owner224 fixed-pool scope is required",
    )
    require(
        growth.get("decision_id") == 223
        and growth.get("status") == "approved"
        and growth.get("stage_ladder") == list(PANEL_SIZES),
        "approved owner223 reviewed scaling scope is required",
    )
    r, rows = registration.get("proposal_round"), registration.get("rows_per_member")
    family, read_id = identities(r, rows)
    require(
        registration.get("schema") == REGISTRATION_SCHEMA
        and registration.get("family_id") == recipe.get("family_id") == family,
        "exact prospective fixed-pool panel family is required",
    )
    require(
        registration.get("registration_sha256")
        == content_hash(
            {k: v for k, v in registration.items() if k != "registration_sha256"}
        ),
        "panel registration hash differs",
    )
    require(
        protocol.get("updates") == r
        and registration.get("proposal_protocol_sha256") == content_hash(protocol),
        "panel proposal protocol differs",
    )
    ids = recipe.get("sample_ids", [])
    require(
        isinstance(pool_ids, list)
        and len(pool_ids) == len(set(pool_ids)) == 400
        and all(isinstance(s, str) and s.startswith("slurp:train:") for s in pool_ids)
        and content_hash(pool_ids)
        == owner.get("sample_ids_sha256")
        == registration.get("pool_sample_ids_sha256")
        and ids == pool_ids[:rows]
        and content_hash(ids) == registration.get("prefix_sample_ids_sha256"),
        "panel must retain the exact ordered prefix of the original TRAIN pool",
    )
    require(
        recipe.get("required_rows_per_member") == rows
        and registration.get("trajectory_cap") == rows * 8
        and registration.get("official_score_jobs_cap") == 8
        and registration.get("new_proposal_opportunities") == 0
        and {223, 224} <= set(registration.get("owner_decisions", []))
        and registration.get("root_stage_review") == "completed"
        and registration.get("scientific_role") == "optimization-only"
        and registration.get("independent_validation") is False
        and registration.get("automatic_expansion") is False,
        "panel budget, review or retained-exposure purpose differs",
    )
    bindings, members = (
        registration.get("member_bindings", {}),
        registration.get("expected_members", {}),
    )
    require(
        set(bindings) == set(members) == MEMBERS
        and members == recipe.get("expected_members"),
        "all eight panel members are required",
    )
    require(
        all(
            b.get("run_id") == members[c] == member_run_id(r, rows, c)
            and all(
                isinstance(b.get(k), str) and b[k]
                for k in ("attempt_id", "config_hash", "bundle_id")
            )
            for c, b in bindings.items()
        )
        and len({b["attempt_id"] for b in bindings.values()}) == 8,
        "panel member run, attempt or policy identity differs",
    )
    for branch in ("L", "B"):
        require(
            bindings[branch + "-parent"]["bundle_id"]
            == bindings[branch + "-parent-aa"]["bundle_id"],
            "panel parent and A/A policy must agree",
        )
    require(
        bindings["B-parent"]["bundle_id"]
        == protocol.get("seed_bundle", {}).get("bundle_id"),
        "blind parent must remain the original frozen seed",
    )
    require(
        recipe.get("run_ids", {}).get("read")
        == registration.get("read_id")
        == read_id,
        "exact prospective panel READ identity is required",
    )


def validate_registration(recipe, registration, owner, authority, *, growth, protocol, pool_ids):
    """Require real countersigned READ metadata in addition to prospective scope."""
    validate_definition(recipe, registration, owner, growth=growth, protocol=protocol, pool_ids=pool_ids)
    require(isinstance(authority, dict) and authority.get("read_run_id") == registration["read_id"],
            "exact panel root READ authority is required")
    sha(authority.get("ledger_row_sha256"))


def _require_complete(d):
    scope = require_panel_scope(d)
    require(d.get("schema") == SCHEMA, "complete panel evidence schema differs")
    feedback = d.get("feedback", {})
    groups, sources = feedback.get("groups", []), feedback.get("sources", [])
    require(
        set(d.get("summaries", {})) == MEMBERS
        and len(sources) == 8
        and {s["candidate_id"] for s in sources} == MEMBERS,
        "all eight complete panel summaries and sources are required",
    )
    require(
        all(
            s.get("run_id")
            == member_run_id(scope["proposal_round"], scope["rows"], s["candidate_id"])
            and s.get("attempt_id")
            and s.get("config_hash")
            for s in sources
        )
        and len({s["attempt_id"] for s in sources}) == 8,
        "complete panel source identity differs",
    )
    ids = [g["sample_id"] for g in groups]
    require(
        len(ids) == len(set(ids)) == scope["rows"]
        and all(isinstance(s, str) and s.startswith("slurp:train:") for s in ids)
        and content_hash(ids) == scope["prefix_sample_ids_sha256"]
        and all(
            len(g["members"]) == 8
            and {m["candidate_id"] for m in g["members"]} == MEMBERS
            for g in groups
        ),
        "panel feedback is incomplete or mixes cohorts",
    )
    return scope


@dataclass(frozen=True)
class CompletePanelEvidence:
    """Full root evidence with a separately qualified own-learning projection."""

    document_json: str

    def as_json(self):
        return json.loads(self.document_json)

    def learning_projection(self, *, amendment, reference):
        d = self.as_json()
        scope = _require_complete(d)
        require(
            amendment.get("decision_id") == 223
            and amendment.get("status") == "approved"
            and amendment.get("stage_ladder") == list(PANEL_SIZES)
            and content_hash(amendment) == scope["growth_owner_sha256"],
            "exact approved reviewed-scaling learning scope is required",
        )
        return _learning_projection(
            d,
            amendment=amendment,
            reference=reference,
            interpretation=f"Exploratory {scope['rows']}-input complete-system learning feedback. "
            "Preserve all own successes, failures, unchanged and damaged answers. "
            "Owner224 reuses the same ordered TRAIN pool with cumulative exposure. "
            "No independent validation, formal adoption, guaranteed improvement, node causal credit "
            "or policy gradient. Root reviews every stage before any further scaling.",
        )


def read_evidence(
    bindings, *, recipe, registration, owner, authority, growth, protocol, pool_ids
):
    validate_registration(
        recipe,
        registration,
        owner,
        authority,
        growth=growth,
        protocol=protocol,
        pool_ids=pool_ids,
    )
    job_pins = _job_metadata(bindings)
    result = _read_complete_evidence(
        bindings,
        recipe=recipe,
        registration=registration,
        authority=authority,
        family=recipe["family_id"],
        schema=SCHEMA,
        evidence_type=CompletePanelEvidence,
    )
    require(
        _job_metadata(bindings) == job_pins,
        "panel official job metadata changed during read",
    )
    return CompletePanelEvidence(
        canonical(
            {
                **result.as_json(),
                "panel_scope": scope_record(registration, owner, growth),
            }
        )
    )


def analyze(evidence, *, recipe, registration, roster, supplement):
    require(
        isinstance(evidence, CompletePanelEvidence), "complete panel evidence required"
    )
    d = evidence.as_json()
    scope = _require_complete(d)
    require(
        d["registration_sha256"]
        == registration.get("registration_sha256")
        == content_hash(
            {k: v for k, v in registration.items() if k != "registration_sha256"}
        )
        and d["family_id"] == recipe.get("family_id") == registration.get("family_id")
        and [g["sample_id"] for g in d["feedback"]["groups"]]
        == recipe.get("sample_ids"),
        "panel evidence registration or roster differs",
    )
    bindings = registration["member_bindings"]
    require(
        set(bindings) == MEMBERS
        and all(
            all(
                s[k] == bindings[s["candidate_id"]][k]
                for k in ("run_id", "attempt_id", "config_hash")
            )
            for s in d["feedback"]["sources"]
        ),
        "panel measured source differs from registration",
    )
    report = _describe_complete_cohort(
        d,
        ids=recipe["sample_ids"],
        bindings=bindings,
        recipe={**recipe, "resampling": supplement["resampling"]},
        roster=roster,
    )
    report.update(
        schema="saea-fixed400-system-panel-read-v1",
        status="EXPLORATORY-FIXED-POOL-NO-ADOPTION",
        optimizer_feedback_allowed=False,
        independent_validation=False,
        automatic_expansion=False,
        formal_adoption=False,
        interpretation=f"{scope['rows']}-input retained-exposure whole-system optimization comparison. "
        "Report both branches, own A/A, uncertainty, every stratum, failures and actual cost. "
        "One reused learning sequence does not establish stable recursive improvement or independent "
        "generalization. Root reviews before scaling; no proposer receives this combined report.",
    )
    _attach_answer_changes(report, d, recipe["sample_ids"], MEMBERS)
    return report


def load_scope(registration, owner, supplement, *, repo_root):
    """Resolve the already registered proposal protocol and immutable pool."""
    from ..rails.system_optimization import load_optimization_panel

    protocol = json.loads(_read_pin(supplement["proposal_protocol"], repo_root))
    growth_pin = supplement["growth_owner_decision"]
    growth = json.loads(_read_pin(growth_pin, repo_root))
    require(
        protocol.get("allocation_extension", {}).get("owner") == growth_pin,
        "panel must use the proposal allocation's exact growth authority",
    )
    resolved = load_optimization_panel(
        protocol,
        f"update-{registration['proposal_round']}",
        repo_root=repo_root,
    )
    require(resolved is not None, "panel proposal has no registered fixed-pool scope")
    plan, pool = resolved
    require(
        json.loads(_read_pin(plan["owner"], repo_root)) == owner,
        "panel analysis owner differs from the proposal's fixed pool",
    )
    return {"growth": growth, "protocol": protocol, "pool_ids": pool}


def _job_metadata(bindings):
    """Recheck sole successful official jobs before and after a feedback export."""
    pins = {}
    for binding in bindings:
        manifest = Path(binding["config"]["manifest"]["path"]).resolve()
        jobs_path = manifest.parent / "score-jobs.jsonl"
        summary_path = manifest.parent / "score-batch/batch-summary.json"
        jobs_raw, summary_raw = jobs_path.read_bytes(), summary_path.read_bytes()
        jobs = [json.loads(line) for line in jobs_raw.splitlines() if line.strip()]
        summary = json.loads(summary_raw)
        require(
            len(jobs) == 1
            and summary.get("job_count") == summary.get("succeeded") == 1
            and summary.get("failed") == 0
            and summary.get("include_per_sample") is True
            and len(summary.get("jobs", [])) == 1,
            "panel requires exactly one successful complete official job and zero failures",
        )
        job = summary["jobs"][0]
        require(
            job.get("job_id") == jobs[0].get("job_id") == manifest.parent.name
            and job.get("status") == "succeeded"
            and job.get("returncode") == 0
            and job.get("operation") == "finalize"
            and Path(job["manifest"]).resolve()
            == Path(jobs[0]["manifest"]).resolve()
            == manifest,
            "panel official job identity differs",
        )
        pins[str(jobs_path)] = hashlib.sha256(jobs_raw).hexdigest()
        pins[str(summary_path)] = hashlib.sha256(summary_raw).hexdigest()
    return pins
