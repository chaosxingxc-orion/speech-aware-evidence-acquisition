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
from ..rails.system_text_policy import require

FAMILY = "fixed400-context20-v1"
READ_ID = "SAEA-SLURP-SYSTEM-TEXT-FIXED400-CONTEXT20-READ-V1"
SCHEMA = "saea-complete-context-comparison-evidence-v1"
REGISTRATION_SCHEMA = "saea-fixed400-context-comparison-registration-v1"
MEMBERS = {"B-parent", "B-parent-aa", "B-candidate-1", "B-candidate-2"}


@dataclass(frozen=True)
class CompleteContextEvidence:
    """Source-bound root evidence with no proposer export or adoption authority."""

    document_json: str

    def as_json(self):
        return json.loads(self.document_json)


def validate_registration(recipe, registration, owner, authority):
    require(
        owner.get("decision_id") == 224
        and owner.get("status") == "approved"
        and owner.get("progressive_sizes") == [20, 50, 100, 200, 400],
        "exact approved owner224 scope is required",
    )
    require(
        registration.get("schema") == REGISTRATION_SCHEMA
        and recipe.get("family_id") == registration.get("family_id") == FAMILY,
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
        == READ_ID
        and len(authority.get("ledger_row_sha256", "")) == 64,
        "exact context root READ is required",
    )


def read_evidence(bindings, *, recipe, registration, owner, authority):
    validate_registration(recipe, registration, owner, authority)
    return _read_complete_evidence(
        bindings,
        recipe=recipe,
        registration=registration,
        authority=authority,
        family=FAMILY,
        schema=SCHEMA,
        evidence_type=CompleteContextEvidence,
    )


def analyze(evidence, *, recipe, registration, roster, supplement):
    require(
        isinstance(evidence, CompleteContextEvidence),
        "qualified context evidence required",
    )
    d = evidence.as_json()
    require(
        d.get("schema") == SCHEMA
        and d.get("family_id") == FAMILY
        and d.get("read_authority", {}).get("read_run_id") == READ_ID,
        "context evidence scope differs",
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
    _attach_answer_changes(report, d, recipe["sample_ids"], MEMBERS)
    return report
