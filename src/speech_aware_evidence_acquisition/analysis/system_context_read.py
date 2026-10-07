"""Describe a qualified deterministic context family using the shared statistics.

This module does not authorize reads, run a scorer or choose a learned policy.
The CLI and optimizer entry independently enforce complete source custody.
"""

from ..rails.system_context_learning import FEEDBACK_SCHEMA, population_candidates
from ..rails.system_search_measurement import measured_rows, measured_frontier
from ..rails.system_text_feedback import CompleteSystemFeedback
from ..rails.system_text_policy import require
from .system_text_pilot import _attach_answer_changes
from .system_text_update import _describe_complete_cohort


def analyze(evidence, *, recipe, registration, protocol, roster, supplement):
    require(
        isinstance(evidence, CompleteSystemFeedback),
        "qualified context evidence required",
    )
    d = evidence.as_json()
    bindings = registration["member_bindings"]
    candidates, controls = protocol["candidate_members"], protocol["control_members"]
    # The caller qualifies the hash-pinned owner amendment before reading sources.
    # This pure reporter still rejects silent resizing and incomplete populations.
    population = protocol.get("population_authorization")
    expected_k = 4
    require(protocol.get("population_partition") is None or population is not None,
            "partition requires original population authorization")
    if "experiment_population" in protocol:
        pin = protocol["experiment_population"]
        require(all(x.get("experiment_population") == pin
                    and x.get("population_cohort") == protocol.get("population_cohort")
                    and x.get("population_budget") == protocol.get("population_budget")
                    for x in (recipe, registration)), "configured report bindings differ")
        expected_k = protocol["population_budget"]["K"]
        require(len(recipe["sample_ids"]) == protocol["population_budget"]["N"],
                "configured report roster size differs")
    elif population is not None:
        require(
            isinstance(population, dict)
            and isinstance(population.get("relpath"), str)
            and bool(population["relpath"])
            and isinstance(population.get("sha256"), str)
            and len(population["sha256"]) == 64
            and all(c in "0123456789abcdef" for c in population["sha256"])
            and protocol.get("N") == 20
            and protocol.get("algorithms") == ["tf-grpo-context-diversity"]
            and candidates == population_candidates(protocol),
            "exact prospective population report scope required",
        )
        expected_k = len(population_candidates(protocol))
    require(
        type(protocol.get("K", 4)) is int
        and protocol.get("K", 4) == expected_k
        and len(controls) == len(set(controls)) == 2
        and len(candidates) == len(set(candidates)) == expected_k
        and set(candidates + controls) == set(bindings),
        "complete context and control scope required",
    )
    require(
        d.get("schema") == FEEDBACK_SCHEMA
        and d.get("family_id") == recipe["family_id"] == registration["family_id"]
        and d.get("read_authority", {}).get("read_run_id") == recipe["run_ids"]["read"]
        and d.get("registration_sha256") == registration["registration_sha256"]
        and set(d["summaries"]) == set(bindings),
        "context evidence identity differs",
    )
    sources = d["feedback"]["sources"]
    require(
        len(sources) == len(bindings)
        and {s["candidate_id"] for s in sources} == set(bindings),
        "complete context sources required",
    )
    require(
        all(
            all(
                s[k] == bindings[s["candidate_id"]][k]
                for k in ("run_id", "attempt_id", "config_hash")
            )
            for s in sources
        ),
        "context source identity differs",
    )
    rows = measured_rows(
        d, list(bindings), bindings, profile=recipe["measurement_profile"]
    )
    report = _describe_complete_cohort(
        d,
        ids=recipe["sample_ids"],
        bindings=bindings,
        recipe={**recipe, "resampling": supplement["resampling"]},
        roster=roster,
        comparison_groups={"context": (*controls, candidates)},
    )
    _attach_answer_changes(report, d, recipe["sample_ids"], set(bindings))
    # A/A is a separate null observation, never a second selectable copy of seed.
    report.update(
        schema="saea-context-learning-root-read-v1",
        status="EXPLORATORY-CONTEXT-INITIALIZATION-NO-ADOPTION",
        optimizer_feedback_allowed=False,
        automatic_expansion=False,
        measured_rows=rows,
        measured_frontier=measured_frontier(
            [r for r in rows if r["candidate_id"] != controls[1]],
            profile=recipe["measurement_profile"],
        ),
        interpretation="Complete registered-input deterministic context initialization. "
        "Report whole-system quality, reliability and actual all/non-first sample latency. "
        "No stable benefit, learned improvement, node causal credit or independent validation. "
        "Real learner input requires a separately pinned fresh qualification.",
    )
    report.update({k: protocol[k] for k in ("experiment_population", "population_cohort", "population_budget")
                   if k in protocol})
    if "search_evaluation" in protocol:
        require(all(d.get("search_evaluation") == protocol["search_evaluation"]
                    for d in (recipe, registration)), "search report provenance differs")
        report.update(status="EXPLORATORY-SEARCH-EVALUATION-NO-ADOPTION",
            search_evaluation=protocol["search_evaluation"], search_algorithms=protocol["algorithms"],
            interpretation="Complete registered-input deterministic search evaluation. "
            "Retain all original candidate outcomes, quality, reliability, process diagnostics and cost. "
            "No stable benefit, automatic adoption, exact GRPO/GEPA reproduction or independent validation. "
            "Any later optimizer export requires separate fresh complete-source qualification.")
    return report
