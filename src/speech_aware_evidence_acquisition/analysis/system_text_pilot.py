"""Exact owner220 exploratory read with owner222 isolated learning projection.

Reuse the official source verifier, attributed cost reader and paired statistics.
Small-batch learning is separate from the formal registered-stage minimum.
"""

import json
import math
from dataclasses import dataclass
from pathlib import Path

from ..core.bundle.verify import verify_bundle
from ..rails.group_relative_feedback import build_group_relative_feedback
from ..rails.hashing import content_hash
from ..rails.system_text_feedback import (
    CompleteSystemFeedback,
    _absolute_json,
    _official_family_rows,
    feedback_utility,
    paired_relative_returns,
    preflight_family,
)
from ..rails.system_text_policy import canonical, require
from .system_text_update import _describe_complete_cohort

FAMILY = "pilot20-owner220"
READ_ID = "SAEA-SLURP-SYSTEM-TEXT-PILOT20-OWNER220-READ-V1"
SCHEMA = "saea-complete-system-pilot-evidence-v1"
MEMBERS = {
    f"{b}-{m}"
    for b in ("L", "B")
    for m in ("parent", "parent-aa", "candidate-1", "candidate-2")
}


@dataclass(frozen=True)
class CompleteSystemPilotEvidence:
    """Full root evidence; owner222 permits a separate learning-only projection."""

    document_json: str

    def as_json(self):
        return json.loads(self.document_json)

    def learning_projection(self, *, amendment, reference):
        """Keep every L case; never send blind outcomes or claim promotion."""
        d = self.as_json()
        require(
            amendment.get("decision_id") == 222
            and amendment.get("status") == "approved"
            and amendment.get("family_id") == FAMILY
            and amendment.get("allow_learning_feedback") is True
            and amendment.get("recipient_branch") == "L"
            and amendment.get("complete_family_required") is True
            and amendment.get("formal_adoption") is False,
            "exact owner222 learning allowance is required",
        )
        require(
            d.get("schema") == SCHEMA
            and d.get("family_id") == FAMILY
            and d.get("read_authority", {}).get("read_run_id") == READ_ID
            and set(d["summaries"]) == MEMBERS
            and len(d["feedback"]["groups"]) == 20,
            "complete root pilot evidence is required before learning",
        )
        return _learning_projection(
            d, amendment=amendment, reference=reference,
            interpretation="Exploratory twenty-input full-system learning feedback. Use successes, failures, "
            "unchanged cases and damaged answers to propose testable text/knowledge revisions. "
            "No reliable-benefit claim, node causal credit, policy gradient or guaranteed improvement. "
            "Evaluate the next version on a prospectively fixed disjoint small panel.",
        )


def _learning_projection(d, *, amendment, reference, interpretation, members=None):
    """Project a separately qualified full family; callers enforce exact allowance."""
    require(
        isinstance(reference, CompleteSystemFeedback),
        "verified frozen reference is required",
    )
    frozen = reference.as_json()["reference"]
    require(
        len(frozen["sample_ids"]) >= 400
        and all(s.startswith("slurp:train:") for s in frozen["sample_ids"]),
        "preserve the original TRAIN reference F1",
    )
    family_hash = content_hash(d)
    from ..rails.system_optimization import SUCCESSOR_MEMBERS, SUCCESSOR_REGISTRATION
    members = MEMBERS if members is None else members
    require(members == MEMBERS or (members == SUCCESSOR_MEMBERS
        and d.get("panel_scope", {}).get("evaluation_schema") == SUCCESSOR_REGISTRATION),
        "learning projection cannot select an arbitrary member subset")
    own = sorted(c for c in members if c.startswith("L-"))
    d["schema"] = "saea-exploratory-system-feedback-v1"
    d["reference"] = frozen
    for group in d["feedback"]["groups"]:
        require(
            len(group["members"]) == len(members)
            and {m["candidate_id"] for m in group["members"]} == members,
            "all original trajectories must remain in the root pilot evidence",
        )
        group["members"] = [m for m in group["members"] if m["candidate_id"] in own]
        utilities = [
            feedback_utility(m["native_counts"], frozen["f1"])
            for m in group["members"]
        ]
        for member, utility, relative in zip(
            group["members"],
            utilities,
            paired_relative_returns(utilities),
            strict=True,
        ):
            member.update(utility=utility, relative_return=relative)
            member.pop("quality", None)
    d["summaries"] = {c: d["summaries"][c] for c in own}
    d["feedback"]["candidate_ids"] = own
    d["feedback"]["sources"] = [
        s for s in d["feedback"]["sources"] if s["candidate_id"] in own
    ]
    require(
        len(d["feedback"]["sources"]) == len(own)
        and {s["candidate_id"] for s in d["feedback"]["sources"]} == set(own),
        "all four learning source indexes are required",
    )
    d.update(
        read_gate_family_sha256=family_hash,
        learning_allowance_sha256=content_hash(amendment),
        optimizer_feedback_allowed=True,
        formal_adoption=False,
        interpretation=interpretation,
    )
    if members == SUCCESSOR_MEMBERS:
        d["successor_custody"] = {k: {cid: value for cid, value in values.items() if cid.startswith("L-")}
            for k, values in d["successor_custody"].items()}
        d["panel_scope"]["custody_sha256"] = content_hash(d["successor_custody"])
        d["successor_bindings"] = {cid: b for cid, b in d["successor_bindings"].items() if cid in own}
        d["panel_scope"]["bindings_sha256"] = content_hash(d["successor_bindings"])
    return CompleteSystemFeedback(canonical(d))


def validate_pilot_registration(recipe, registration, owner, authority):
    require(
        owner.get("decision_id") == 220 and owner.get("status") == "approved",
        "exact approved owner220 allowance is required",
    )
    require(
        all(
            owner.get("budget", {}).get(k) == v
            for k, v in {
                "members": 8,
                "rows_per_member": 20,
                "system_trajectories": 160,
                "new_proposals": 0,
            }.items()
        ),
        "owner pilot budget differs",
    )
    require(
        registration.get("schema") == "saea-small-system-pilot-registration-v1"
        and registration.get("family_id") == recipe.get("family_id") == FAMILY,
        "this reader admits only the exact owner220 pilot family",
    )
    require(
        registration.get("registration_sha256")
        == content_hash(
            {k: v for k, v in registration.items() if k != "registration_sha256"}
        ),
        "pilot registration hash differs",
    )
    require(
        recipe.get("required_rows_per_member")
        == registration.get("rows_per_member")
        == 20
        and registration.get("trajectory_cap") == 160
        and registration.get("official_score_jobs_cap") == 8
        and registration.get("new_proposal_opportunities") == 0
        and 220 in registration.get("owner_decisions", []),
        "pilot bounds differ",
    )
    ids = recipe.get("sample_ids", [])
    require(
        len(ids) == len(set(ids)) == 20
        and all(s.startswith("slurp:train:") for s in ids),
        "pilot requires the exact twenty TRAIN inputs",
    )
    members, bindings = (
        registration.get("expected_members", {}),
        registration.get("member_bindings", {}),
    )
    require(
        set(members) == set(bindings) == MEMBERS
        and members == recipe.get("expected_members"),
        "all eight pilot members are required",
    )
    require(
        all(
            b.get("run_id") == members[cid]
            and all(b.get(k) for k in ("attempt_id", "config_hash", "bundle_id"))
            for cid, b in bindings.items()
        ),
        "pilot member identity differs",
    )
    for branch in ("L", "B"):
        require(
            bindings[branch + "-parent"]["bundle_id"]
            == bindings[branch + "-parent-aa"]["bundle_id"],
            "pilot parent/A/A policy differs",
        )
    require(
        recipe.get("run_ids", {}).get("read")
        == registration.get("read_id")
        == authority.get("read_run_id")
        == READ_ID
        and len(authority.get("ledger_row_sha256", "")) == 64,
        "exact pilot root READ authority is required",
    )


def read_pilot_evidence(bindings, *, recipe, registration, owner, authority):
    """Call only after the shared ledger gate has freshly verified root authority."""
    validate_pilot_registration(recipe, registration, owner, authority)
    return _read_complete_evidence(bindings, recipe=recipe, registration=registration,
                                  authority=authority, family=FAMILY, schema=SCHEMA,
                                  evidence_type=CompleteSystemPilotEvidence)


def _read_complete_evidence(bindings, *, recipe, registration, authority,
                            family, schema, evidence_type):
    """Shared closed-family read; each public caller enforces its own scope first."""
    profile = recipe.get("measurement_profile")
    require(registration.get("measurement_profile") == profile, "registered measurement profile differs")
    if profile is not None:
        from ..rails.system_search_measurement import validate_profile
        validate_profile(profile)
    metadata = preflight_family(bindings, recipe["expected_members"])
    ids = recipe["sample_ids"]
    for binding, (manifest, _) in zip(bindings, metadata, strict=True):
        expected = registration["member_bindings"][binding["candidate_id"]]
        require(
            manifest.get("run_id") == expected["run_id"]
            and manifest.get("config", {}).get("config_hash") == expected["config_hash"]
            and manifest.get("attempt", {}).get("attempt_id") == expected["attempt_id"],
            "pilot manifest differs from registered attempt/config",
        )
        roster = _absolute_json(binding["config"]["construction_roster"])
        require(
            [r["sample_id"] for r in roster["items"]] == ids
            and manifest.get("split", {}).get("count") == len(ids) == recipe["required_rows_per_member"]
            and set(manifest.get("split", {}).get("ids", [])) == set(ids),
            "pilot roster differs",
        )
    # Verify all eight seals before any reward or terminal read.
    for binding in bindings:
        verified = verify_bundle(Path(binding["config"]["manifest"]["path"]))
        require(verified.attempt_state == "FINALIZED", "pilot seal verification failed")
    grouped = build_group_relative_feedback(bindings)
    require(
        grouped["carrier_lock_key"] == "slurp"
        and [g["sample_id"] for g in grouped["groups"]] == ids,
        "pilot score cohort differs",
    )
    rows, summaries = (_official_family_rows(bindings, metadata, grouped) if profile is None else
                       _official_family_rows(bindings, metadata, grouped, measurement_profile=profile))
    for group in grouped["groups"]:
        for member in group["members"]:
            # No relative advantage or update utility belongs in pilot evidence.
            for key in ("quality", "utility", "relative_return"):
                member.pop(key, None)
            member["execution"] = rows[member["candidate_id"]][group["sample_id"]]
    return evidence_type(
        canonical(
            {
                "schema": schema,
                **({"measurement_profile": profile} if profile is not None else {}),
                "family_id": family,
                "read_authority": authority,
                "registration_sha256": registration["registration_sha256"],
                "summaries": summaries,
                "feedback": grouped,
                "optimizer_feedback_allowed": False,
                "contacts_added": {"model": 0, "scorer": 0},
            }
        )
    )


def analyze_pilot(evidence, *, recipe, registration, roster, supplement):
    require(
        isinstance(evidence, CompleteSystemPilotEvidence),
        "root pilot evidence is required",
    )
    d = evidence.as_json()
    require(
        d.get("schema") == SCHEMA
        and d.get("family_id") == FAMILY
        and d.get("read_authority", {}).get("read_run_id") == READ_ID,
        "pilot evidence scope differs",
    )
    bindings = registration["member_bindings"]
    require(
        set(d["summaries"]) == set(bindings) == MEMBERS,
        "all eight pilot summaries are required",
    )
    sources = d["feedback"]["sources"]
    require(
        len(sources) == 8 and {s["candidate_id"] for s in sources} == MEMBERS,
        "all eight pilot sources are required",
    )
    for source in sources:
        require(
            all(
                source[k] == bindings[source["candidate_id"]][k]
                for k in ("run_id", "attempt_id", "config_hash")
            ),
            "pilot source differs from registration",
        )
    report = _describe_complete_cohort(
        d,
        ids=recipe["sample_ids"],
        bindings=bindings,
        recipe={**recipe, "resampling": supplement["resampling"]},
        roster=roster,
    )
    report.update(
        schema="saea-system-text-pilot-read-v1",
        status="EXPLORATORY-PILOT-NO-ADOPTION",
        optimizer_feedback_allowed=False,
        automatic_expansion=False,
        interpretation="Twenty-input whole-system feasibility and engineering diagnostics only. "
        "No benefit, harm, no-harm, learned-policy adoption, node causal credit or automatic expansion. "
        "Root reviews all successes, failures, unchanged cases and damaged answers; no proposer receives this report.",
    )
    _attach_answer_changes(report, d, recipe["sample_ids"], MEMBERS)
    return report


def _attach_answer_changes(report, d, ids, members):
    """Describe complete-system associations; never infer local causal repair."""
    counts = {
        cid: {
            g["sample_id"]: next(
                m["native_counts"] for m in g["members"] if m["candidate_id"] == cid
            )
            for g in d["feedback"]["groups"]
        }
        for cid in members
    }
    for branch in report["branches"].values():
        for contrast in branch["comparisons"].values():
            changes = {
                k: [] for k in ("repaired", "damaged", "both_correct", "both_incorrect")
            }
            for sid in ids:
                correct = []
                for cid in (contrast["left"], contrast["right"]):
                    c = counts[cid][sid]
                    errors = (c["slot_f1_exact_fp"], c["slot_f1_exact_fn"])
                    require(
                        all(
                            type(v) in (int, float) and math.isfinite(v) and v >= 0
                            for v in errors
                        ),
                        "exact entity error counts must be nonnegative",
                    )
                    correct.append(
                        c["scenario_action_exact"] == 1 and all(v == 0 for v in errors)
                    )
                key = {
                    (False, True): "repaired",
                    (True, False): "damaged",
                    (True, True): "both_correct",
                    (False, False): "both_incorrect",
                }[tuple(correct)]
                changes[key].append(sid)
            contrast["whole_answer_exact_changes"] = {
                "definition": "Between complete systems: intent correct and exact-entity FP=FN=0. "
                "Empty correct entities count as correct. These are associations, not within-trajectory repair attribution.",
                "counts": {k: len(v) for k, v in changes.items()},
                "sample_ids": changes,
            }
        branch["replicate_policy"] = (
            "A/A is a separate descriptive measurement; no pilot policy is selected."
        )
