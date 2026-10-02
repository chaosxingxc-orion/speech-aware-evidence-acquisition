"""Root-only owner224 comparison on the same fixed twenty-input optimization prefix.

Reuse shared complete-family custody, official counts and paired statistics.
This reduced comparison is neither the original eight-member learning contrast
nor a held-out read, and never exports feedback to a blind proposer.
"""

import json
from dataclasses import dataclass
from .system_text_pilot import _attach_answer_changes, _read_complete_evidence
from .system_text_update import _describe_complete_cohort
from ..rails.hashing import content_hash
from ..rails.system_text_policy import canonical, require

FAMILY = "fixed400-context20-v1"
READ_ID = "SAEA-SLURP-SYSTEM-TEXT-FIXED400-CONTEXT20-READ-V1"
SCHEMA = "saea-complete-context-comparison-evidence-v1"
REGISTRATION_SCHEMA = "saea-fixed400-context-comparison-registration-v1"
MEMBERS = {"B-parent", "B-parent-aa", "B-candidate-1", "B-candidate-2"}
RECOVERY_FAMILY = "fixed400-context20-recovery1-v1"
RECOVERY_READ_ID = "SAEA-SLURP-SYSTEM-TEXT-FIXED400-CONTEXT20-RECOVERY1-READ-V1"
READ_IDS = {FAMILY: READ_ID, RECOVERY_FAMILY: RECOVERY_READ_ID}
RECOVERY_MEMBERS = {
    "B-parent": "SAEA-SLURP-SYSTEM-TEXT-FIXED400-CONTEXT20-SEED-RECOVERY1-V1",
    "B-parent-aa": "SAEA-SLURP-SYSTEM-TEXT-FIXED400-CONTEXT20-SEED-AA-RECOVERY1-V1",
    "B-candidate-1": "SAEA-SLURP-SYSTEM-TEXT-FIXED400-CONTEXT20-PLANNER-V1",
    "B-candidate-2": "SAEA-SLURP-SYSTEM-TEXT-FIXED400-CONTEXT20-SOLVER-V1",
}


def validate_recovery_scope(recipe, registration, recovery):
    """Require the exact prospective owner225 ruling before any result read."""
    family = recipe.get("family_id")
    require(family in READ_IDS, "unknown fixed400 context family")
    if family == FAMILY:
        require(recovery is None, "recovery authority cannot authorize the old family")
        return
    require(
        isinstance(recovery, dict)
        and recovery.get("schema") == "saea-fixed400-seed-binding-recovery-authority-v1"
        and recovery.get("decision_id") == 225
        and recovery.get("status") == "approved",
        "exact approved owner225 recovery authority is required",
    )
    require(
        recovery.get("family_id") == family == registration.get("family_id")
        and recovery.get("previous_family_id") == FAMILY
        and recovery.get("read_id") == RECOVERY_READ_ID
        and 225 in registration.get("owner_decisions", [])
        and recovery.get("expected_members")
        == registration.get("expected_members")
        == recipe.get("expected_members")
        == RECOVERY_MEMBERS,
        "recovery must use new seed/A/A and the two original unstarted candidates",
    )
    require(
        recovery.get("rows_per_member") == 20
        and recovery.get("trajectory_cap") == 80
        and recovery.get("preserve_previous_family") is True
        and recovery.get("old_generation_or_score_replay_allowed") is False
        and recovery.get("automatic_failure_recovery") is False
        and all(
            recovery.get(k) == registration.get(k)
            for k in ("pool_sample_ids_sha256", "prefix_sample_ids_sha256")
        ),
        "recovery budget, fixed pool or preservation scope differs",
    )


@dataclass(frozen=True)
class CompleteContextEvidence:
    """Source-bound root evidence with no proposer export or adoption authority."""

    document_json: str

    def as_json(self):
        return json.loads(self.document_json)


def validate_registration(recipe, registration, owner, authority, *, recovery=None):
    validate_recovery_scope(recipe, registration, recovery)
    require(
        owner.get("decision_id") == 224
        and owner.get("status") == "approved"
        and owner.get("progressive_sizes") == [20, 50, 100, 200, 400],
        "exact approved owner224 scope is required",
    )
    require(
        registration.get("schema") == REGISTRATION_SCHEMA
        and recipe.get("family_id") == registration.get("family_id"),
        "exact fixed400 context family is required",
    )
    require(
        registration.get("registration_sha256")
        == content_hash(
            {k: v for k, v in registration.items() if k != "registration_sha256"}
        ),
        "context registration hash differs",
    )
    ids = recipe.get("sample_ids", [])
    require(
        len(ids) == len(set(ids)) == 20
        and all(isinstance(s, str) and s.startswith("slurp:train:") for s in ids)
        and registration.get("prefix_sample_ids_sha256") == content_hash(ids)
        and registration.get("pool_sample_ids_sha256") == owner.get("sample_ids_sha256")
        and len(owner.get("sample_ids_sha256", "")) == 64,
        "exact owner224 TRAIN pool/prefix is required",
    )
    require(
        recipe.get("required_rows_per_member")
        == registration.get("rows_per_member")
        == 20
        and registration.get("trajectory_cap") == 80
        and registration.get("official_score_jobs_cap") == 4
        and registration.get("new_proposal_opportunities") == 0
        and registration.get("independent_validation") is False
        and registration.get("optimizer_feedback_allowed") is False
        and 224 in registration.get("owner_decisions", []),
        "context comparison budget or exposure purpose differs",
    )
    members = registration.get("expected_members", {})
    bindings = registration.get("member_bindings", {})
    require(
        set(members) == set(bindings) == MEMBERS
        and recipe.get("expected_members") == members,
        "all four context members including A/A are required",
    )
    require(
        all(
            b.get("run_id") == members[c]
            and all(b.get(k) for k in ("attempt_id", "config_hash", "bundle_id"))
            for c, b in bindings.items()
        ),
        "context member identity differs",
    )
    require(
        bindings["B-parent"]["bundle_id"] == bindings["B-parent-aa"]["bundle_id"],
        "context seed/A/A policy differs",
    )
    require(
        recipe.get("run_ids", {}).get("read")
        == registration.get("read_id")
        == authority.get("read_run_id")
        == READ_IDS[recipe["family_id"]]
        and len(authority.get("ledger_row_sha256", "")) == 64,
        "exact context root READ is required",
    )


def read_evidence(bindings, *, recipe, registration, owner, authority, recovery=None):
    validate_registration(recipe, registration, owner, authority, recovery=recovery)
    evidence = _read_complete_evidence(
        bindings,
        recipe=recipe,
        registration=registration,
        authority=authority,
        family=recipe["family_id"],
        schema=SCHEMA,
        evidence_type=CompleteContextEvidence,
    )
    if recovery is not None:
        evidence = CompleteContextEvidence(
            canonical({**evidence.as_json(), "recovery_authority": recovery})
        )
    return evidence


def analyze(evidence, *, recipe, registration, roster, supplement):
    require(
        isinstance(evidence, CompleteContextEvidence),
        "qualified context evidence required",
    )
    d = evidence.as_json()
    require(
        d.get("schema") == SCHEMA
        and d.get("family_id") == recipe.get("family_id")
        and recipe.get("family_id") in READ_IDS
        and d.get("read_authority", {}).get("read_run_id")
        == READ_IDS[recipe["family_id"]],
        "context evidence scope differs",
    )
    validate_recovery_scope(recipe, registration, d.get("recovery_authority"))
    if recipe["family_id"] == RECOVERY_FAMILY:
        require(
            d.get("registration_sha256") == registration.get("registration_sha256"),
            "recovery evidence registration differs",
        )
    bindings = registration["member_bindings"]
    sources = d["feedback"]["sources"]
    require(
        set(d["summaries"]) == set(bindings) == MEMBERS
        and len(sources) == 4
        and {s["candidate_id"] for s in sources} == MEMBERS,
        "complete context source family required",
    )
    require(
        all(
            all(
                s[k] == bindings[s["candidate_id"]][k]
                for k in ("run_id", "attempt_id", "config_hash")
            )
            for s in sources
        ),
        "context measured source differs",
    )
    report = _describe_complete_cohort(
        d,
        ids=recipe["sample_ids"],
        bindings=bindings,
        recipe={**recipe, "resampling": supplement["resampling"]},
        roster=roster,
        branch_names=("B",),
    )
    report.update(
        schema="saea-fixed400-context-comparison-read-v1",
        status="EXPLORATORY-FIXED-POOL-NO-ADOPTION",
        optimizer_feedback_allowed=False,
        independent_validation=False,
        claims_feedback_learning_advantage=False,
        automatic_expansion=False,
        interpretation="Twenty-input retained-exposure optimization comparison. Describe official complete-system "
        "quality, own A/A uncertainty, failures and cost; no stable benefit, formal adoption, causal node credit "
        "or L-over-B feedback-learning claim. Never send this report to a blind proposer. Root reviews before scaling.",
    )
    if recipe["family_id"] == RECOVERY_FAMILY:
        report["recovery_authority_sha256"] = content_hash(d["recovery_authority"])
    _attach_answer_changes(report, d, recipe["sample_ids"], MEMBERS)
    return report
