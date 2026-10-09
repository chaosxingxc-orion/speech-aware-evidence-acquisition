"""Read a configured manual architecture family through existing complete custody.

This thin selector creates no learner, scorer, policy or execution authority.
"""

import json
from dataclasses import dataclass

from ..core.config import compose
from ..core.flight.campaign import load_campaign_cells
from ..rails.experiment_population import population_stage_spec
from ..rails.hashing import content_hash
from ..rails.system_text_policy import _read_pin, require
from .system_text_pilot import _attach_answer_changes, _read_complete_evidence
from .system_text_update import (
    _describe_complete_cohort, require_additional_contrast_binding,
    validate_additional_paired_contrasts,
)

SELECTOR = "manual-architecture-n20-v1"
FIXED_ROSTER_SELECTOR = "manual-architecture-fixed-roster-v1"
from ..rails.local_node_panel import SELECTORS as LOCAL_NODE_SELECTORS
SELECTORS = (SELECTOR, FIXED_ROSTER_SELECTOR, *LOCAL_NODE_SELECTORS)
REGISTRATION = "saea-manual-architecture-analysis-registration-v1"
SCHEMA = "saea-complete-manual-architecture-evidence-v1"


@dataclass(frozen=True)
class CompleteArchitectureEvidence:
    """Complete root evidence with no optimizer projection method."""

    document_json: str

    def as_json(self):
        return json.loads(self.document_json)


def validate_registration(
    recipe, registration, owner, authority, *, repo_root, data_root
):
    """Retain the exact whole-family READ gate before source validation."""
    require(
        authority.get("read_run_id")
        == recipe.get("run_ids", {}).get("read")
        == registration.get("read_id")
        and authority.get("ledger_row_sha256"),
        "exact root manual READ required",
    )
    return validate_source_registration(
        recipe, registration, owner, repo_root=repo_root, data_root=data_root
    )


def validate_source_registration(recipe, registration, owner, *, repo_root, data_root):
    """Validate every source pair; grant no READ or complete-evidence authority."""
    from ..rails.architecture_natural_registration import (
        require_architecture_n20_registration,
    )

    require_additional_contrast_binding(recipe, registration)
    require(
        recipe.get("architecture_proof")
        == registration.get("architecture_proof")
        and recipe.get("architecture_proof") in SELECTORS
        and recipe.get("architecture_extent") == registration.get("architecture_extent")
        and recipe.get("natural_source_compatibility") == registration.get("natural_source_compatibility")
        and recipe.get("joint_role_basis") == registration.get("joint_role_basis")
        and registration.get("schema") == REGISTRATION
        and recipe.get("family_id") == registration.get("family_id")
        and recipe.get("learner_export") is False
        and registration.get("learner_export") is False
        and not any(
            k in recipe
            for k in (
                "pilot_registration",
                "system_panel_registration",
                "context_learning_registration",
                "system_search_evaluation",
            )
        ),
        "explicit manual architecture scope and no learner export required",
    )
    require(
        owner.get("decision_id") == 227 and owner.get("status") == "approved",
        "approved owner227 manual architecture scope required",
    )
    require(
        registration.get("registration_sha256")
        == content_hash(
            {k: v for k, v in registration.items() if k != "registration_sha256"}
        ),
        "manual registration hash differs",
    )
    stage = population_stage_spec(
        recipe["experiment_population"],
        repo_root=repo_root,
        cohort_id=recipe["population_cohort"],
        allow_architecture=True,
    )
    identities = {m["member_id"]: m for m in stage["architecture_members"]}
    labels = stage["control_members"] + stage["candidate_members"]
    require(
        len(stage["control_members"]) == 2 and list(identities) == labels,
        "manual comparison requires configured primary and A/A controls",
    )
    primary, aa = (identities[label] for label in stage["control_members"])
    require(
        all(
            primary[key] == aa[key]
            for key in ("base_bundle_id", "active_roles", "model_per_trajectory")
        )
        and primary["execution_config"]["sha256"] == aa["execution_config"]["sha256"],
        "manual A/A controls require the same pinned execution policy",
    )
    expected, bindings = (
        registration.get("expected_members", {}),
        registration.get("member_bindings", {}),
    )
    require(
        set(expected) == set(bindings) == set(labels)
        and expected == recipe.get("expected_members")
        and len(set(expected.values())) == len(labels)
        and registration.get("ordered_member_labels") == labels
        and registration.get("experiment_population") == recipe["experiment_population"]
        and registration.get("population_cohort") == recipe["population_cohort"]
        and registration.get("sample_ids")
        == recipe.get("sample_ids")
        == stage["sample_ids"]
        and registration.get("rows_per_member")
        == recipe.get("required_rows_per_member")
        == stage["N"]
        and registration.get("population_budget")
        == recipe.get("population_budget")
        == stage["population_budget"]
        and registration.get("official_score_jobs_cap")
        == recipe.get("score_jobs")
        == len(labels)
        and recipe.get("comparison_groups")
        == {"architecture": [*stage["control_members"], stage["candidate_members"]]},
        "manual complete family, roster, budget or comparators differ from configuration",
    )
    validate_additional_paired_contrasts(recipe, recipe["comparison_groups"])
    commits = set()
    runtime_orders = {}
    for label in labels:
        b = bindings[label]
        require(
            b.get("run_id") == expected[label]
            and all(
                b.get(k)
                for k in ("attempt_id", "config_hash", "bundle_id", "source_commit")
            ),
            "manual member identity is incomplete",
        )
        (cell,) = load_campaign_cells(repo_root, b["experiment"])
        c = cell.document
        configured = compose(
            repo_root,
            c["model_fragment"],
            c["dataset_fragment"],
            c["baseline_fragment"],
            b["experiment"],
        )
        pair = [
            json.loads(_read_pin(b["registered_plans"][role], repo_root))
            for role in ("generation", "fit")
        ]
        require(configured.values.get("architecture_extent") == recipe.get("architecture_extent")
                and (configured.values.get("architecture_extent") is None
                     or recipe["architecture_proof"] == FIXED_ROSTER_SELECTOR),
                "manual configured extent or selector differs")
        checked = require_architecture_n20_registration(
            configured.values, c, pair, repo_root=repo_root, data_root=data_root
        )
        require(
            checked["member_id"] == label
            and checked["sample_ids"] == stage["sample_ids"]
            and configured.config_hash == b["config_hash"]
            and c["run_id"] == b["run_id"]
            and c["attempt_id"] == b["attempt_id"]
            and b["bundle_id"] == identities[label]["base_bundle_id"]
            and checked["generation_cap"]
            == stage["member_generation_contacts_caps"][label]
            and checked["fit_cap"] == stage["member_fit_endpoints_caps"][label]
            and all(
                p["capacity_prerequisite"] == recipe["capacity_prerequisite"]
                and p.get("natural_source_compatibility") == recipe.get("natural_source_compatibility")
                and p["natural_prerequisite"] == recipe["natural_prerequisite"]
                and (recipe["architecture_proof"] != FIXED_ROSTER_SELECTOR or (
                    p.get("architecture_proof") == FIXED_ROSTER_SELECTOR
                    and p.get("architecture_extent") == recipe.get("architecture_extent")))
                for p in pair
            ),
            "manual registered pair or immutable source binding differs",
        )
        require(configured.values.get("joint_role_basis") == recipe.get("joint_role_basis")
                and all(p.get("joint_role_basis") == recipe.get("joint_role_basis") for p in pair),
                "joint source recipe/registration/configuration/plan custody differs")
        if recipe["architecture_proof"] in LOCAL_NODE_SELECTORS:
            basis = recipe.get("local_node_basis")
            require(isinstance(basis, dict) and basis.get("target_role") in {"solver", "reviewer"}
                    and recipe["architecture_proof"] == "local-" + basis["target_role"] + "-panel-v1"
                    and basis == registration.get("local_node_basis") == configured.values.get("local_node_basis")
                    and all(p.get("local_node_basis") == basis
                            and p.get("architecture_proof") == recipe["architecture_proof"] for p in pair),
                    "local node READ selector or basis differs")
        else:
            require(recipe.get("local_node_basis") is None and registration.get("local_node_basis") is None
                    and configured.values.get("local_node_basis") is None
                    and all(p.get("local_node_basis") is None and p.get("architecture_proof") not in LOCAL_NODE_SELECTORS
                            for p in pair), "local node READ requires its named opt-in selector")
        runtime = checked["runtime_sample_ids"]
        require(
            len(runtime) == len(set(runtime)) == stage["N"]
            and set(runtime) == set(stage["sample_ids"])
            and recipe["runtime_sample_ids"][label]
            == b["runtime_sample_ids"]
            == runtime,
            "manual production order differs from registered source",
        )
        commits.add(b["source_commit"])
        runtime_orders[label] = runtime
    require(
        len(commits) == 1 and registration.get("source_commit") in commits,
        "manual family requires one exact frozen source",
    )
    return {
        "labels": labels,
        "stage": stage,
        "runtime_sample_ids": runtime_orders,
        "source_commit": registration["source_commit"],
        "review_applicability": {
            label: {
                "schema": "saea-review-applicability-v1",
                "config_sha256": bindings[label]["config_hash"],
                "review_loop": "on"
                if "reviewer" in identities[label]["active_roles"]
                else "off",
            }
            for label in labels
        },
    }


def read_evidence(bindings, *, recipe, registration, owner, authority, scope):
    require(
        set(b["candidate_id"] for b in bindings) == set(scope["labels"])
        and len(bindings) == len(scope["labels"]),
        "complete unique manual source bindings required",
    )
    return _read_complete_evidence(
        bindings,
        recipe=recipe,
        registration=registration,
        authority=authority,
        family=recipe["family_id"],
        schema=SCHEMA,
        evidence_type=CompleteArchitectureEvidence,
    )


def analyze(evidence, *, recipe, registration, roster, supplement, scope):
    require(
        isinstance(evidence, CompleteArchitectureEvidence),
        "complete manual evidence required",
    )
    d = evidence.as_json()
    bindings = registration["member_bindings"]
    require(
        d.get("schema") == SCHEMA
        and d.get("family_id") == recipe["family_id"]
        and d.get("registration_sha256") == registration["registration_sha256"]
        and d.get("read_authority", {}).get("read_run_id") == recipe["run_ids"]["read"]
        and set(d["summaries"]) == set(scope["labels"]),
        "manual evidence identity differs",
    )
    sources = d["feedback"]["sources"]
    require(
        len(sources) == len(bindings)
        and {s["candidate_id"] for s in sources} == set(bindings)
        and all(
            all(
                s[k] == bindings[s["candidate_id"]][k]
                for k in ("run_id", "attempt_id", "config_hash")
            )
            for s in sources
        ),
        "manual evidence sources omit, duplicate or mismatch members",
    )
    controls, candidates = (
        scope["stage"]["control_members"],
        scope["stage"]["candidate_members"],
    )
    require_additional_contrast_binding(recipe, registration)
    validate_additional_paired_contrasts(recipe, {"architecture": (*controls, candidates)})
    if "additional_paired_contrasts" in recipe:
        require(content_hash(recipe["resampling"]) == content_hash(supplement["resampling"]),
                "additional paired contrast recipe/supplement resampling differs")
    report = _describe_complete_cohort(
        d,
        ids=recipe["sample_ids"],
        bindings=bindings,
        recipe={**recipe, "resampling": supplement["resampling"]},
        roster=roster,
        comparison_groups={"architecture": (*controls, candidates)},
    )
    _attach_answer_changes(report, d, recipe["sample_ids"], set(bindings))
    report.update(
        schema="saea-manual-architecture-read-v1",
        status="FIXED-ROSTER-VALIDATION-NO-AUTOMATIC-ADOPTION" if scope["stage"]["N"] >= 400 else "FORM-PROOF-NO-ADOPTION",
        optimizer_feedback_allowed=False,
        learner_export=False,
        automatic_expansion=False,
        claims_feedback_learning_advantage=False,
        independent_validation=False,
        review_applicability=scope["review_applicability"],
        interpretation="Manual architecture validation on the complete configured reused input roster. "
        "Retain primary/A/A and both candidate comparisons, natural-mixture and equal-stratum summaries. "
        "No stable benefit, learned policy, node causal credit, automatic adoption or expansion is established.",
    )
    return report


def combine_process(*, recipe, business, process, timing, scope, score_sources,
                    solver_stage_statistics_declaration=None):
    """Reuse qualified v2 process arithmetic and presentation; retain root custody."""
    from .slurp_process_metrics import (
        aggregate_process_metrics, validate_solver_stage_statistics,
        validate_solver_stage_statistics_declaration,
    )
    from .system_process_report import build_process_comparison

    require(
        process.get("read_authority") == business["read_authority"]
        and process.get("source_bindings") == score_sources,
        "process derivative requires exact complete root READ and saved score sources",
    )
    require(
        set(process.get("members", {})) == set(scope["labels"]),
        "complete architecture process family required",
    )
    retained = validate_solver_stage_statistics_declaration(solver_stage_statistics_declaration)
    validate_solver_stage_statistics_declaration(process.get("solver_stage_statistics_declaration"))
    require(process.get("solver_stage_statistics_declaration") == solver_stage_statistics_declaration,
            "explicit prospective stage declaration required")
    for label, source in process["members"].items():
        binding = score_sources[label]
        rows = source["rows"]
        expected = scope["review_applicability"][label]
        require(
            source.get("schema") == "saea-slurp-process-metrics-v2"
            and source.get("review_applicability") == expected
            and source.get("source", {}).get("config_hash") == expected["config_sha256"]
            and source["source"].get("run_id") == recipe["expected_members"][label]
            and source["source"].get("attempt_id") == binding["attempt_id"]
            and source["source"].get("official_score_result_sha256")
            == binding["score_result"]["sha256"]
            and [r["sample_id"] for r in rows] == scope["runtime_sample_ids"][label]
            and source["source"].get("ordered_sample_ids_sha256")
            == content_hash([r["sample_id"] for r in rows])
            and all(
                r.get("review_applicable") is (expected["review_loop"] == "on")
                for r in rows
            ),
            "process source, production order or Reviewer applicability differs",
        )
        require(retained == ("solver_stage_statistics" in source),
                "complete declared stage coverage required; unsolicited stages refused")
        if retained:
            require(source["source"] == binding.get("stage_source"),
                    "stage source differs from verified original source hashes")
            validate_solver_stage_statistics(source["solver_stage_statistics"], rows=rows,
                                             custody=source["custody"], source=binding["stage_source"])
        rebuilt = aggregate_process_metrics(rows)
        require(
            all(source.get(k) == v for k, v in rebuilt.items()),
            "process aggregates differ from complete bound observations",
        )
    return build_process_comparison(
        recipe=recipe, business=business, process=process, timing=timing
    )
