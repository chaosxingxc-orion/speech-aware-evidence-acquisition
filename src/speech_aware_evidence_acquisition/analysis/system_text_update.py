"""Describe a qualified TRAIN update using the shared paired resampler.

This module calculates evidence for root review. It neither selects a policy,
infers node credit, changes an archive nor grants scientific-read authority.
"""

import json
import math
from collections import Counter
from copy import deepcopy

from .null_calibration import pooled_f1
from .paired import resampled_statistic
from ..rails.hashing import content_hash
from ..rails.system_search_archive import OBJECTIVES, pareto_frontier
from ..rails.system_search_protocol import require_stage_feedback, stage_for
from ..rails.system_search_stage import recipe_family_identity
from ..rails.system_text_feedback import CompleteSystemFeedback
from ..rails.system_text_policy import require

FIELDS = tuple(
    tuple(f"slu_f1_{axis}_{kind}" for axis in ("word", "char"))
    for kind in ("tp", "fp", "fn")
)


def load_additional_contrast_document(raw):
    """Observe every raw object property before duplicate keys can erase an opt-in."""
    has_optional, has_duplicates = False, False

    def observe(pairs):
        nonlocal has_optional, has_duplicates
        result = {}
        for name, value in pairs:
            has_optional = has_optional or name == "additional_paired_contrasts"
            has_duplicates = has_duplicates or name in result
            result[name] = value
        return result

    document = json.loads(raw, object_pairs_hook=observe)
    require(not has_optional or not has_duplicates,
            "duplicate JSON field in additional contrast document")
    return document


def validate_additional_paired_contrasts(recipe, comparison_groups):
    """Validate the optional signed combination of existing architecture F1 metrics."""
    if "additional_paired_contrasts" not in recipe:
        return None
    block = recipe["additional_paired_contrasts"]
    require(
        isinstance(block, dict)
        and set(block) == {"schema", "comparison_group", "metric", "contrasts"}
        and block["schema"] == "saea-additional-pooled-contrasts-v1"
        and block["comparison_group"] == "architecture"
        and "architecture" in comparison_groups
        and block["metric"] == "slu_f1"
        and isinstance(block["contrasts"], list) and block["contrasts"],
        "additional paired contrasts require the exact architecture pooled-F1 schema",
    )
    parent, aa, candidates = comparison_groups["architecture"]
    members = {parent, aa, *candidates}
    reserved = {"same-request-null"}
    for group, (_, _, group_candidates) in comparison_groups.items():
        for cid in group_candidates:
            suffix = cid.removeprefix(group + "-")
            reserved.update({suffix + "-minus-parent", suffix + "-minus-aa"})
    names, definitions = set(), set()
    for contrast in block["contrasts"]:
        require(isinstance(contrast, dict) and set(contrast) == {"id", "coefficients"},
                "additional contrast requires exact id and coefficients keys")
        name, coefficients = contrast["id"], contrast["coefficients"]
        require(isinstance(name, str) and name.strip() and name not in names | reserved,
                "additional contrast id is empty, duplicated or reserved")
        require(isinstance(coefficients, dict) and len(coefficients) in {2, 4}
                and all(isinstance(member, str) and member in members
                        and type(weight) is int and weight in {-1, 1}
                        for member, weight in coefficients.items())
                and sum(coefficients.values()) == 0,
                "additional contrast needs two opposite or four balanced integer member weights")
        definition = tuple(sorted(coefficients.items()))
        require(definition not in definitions, "duplicate additional contrast definition")
        names.add(name)
        definitions.add(definition)
    return block


def require_additional_contrast_binding(recipe, registration):
    """Retain exact optional presence and definition through immutable registration."""
    key = "additional_paired_contrasts"
    require((key in recipe) == (key in registration)
            and (key not in recipe or content_hash(recipe[key]) == content_hash(registration[key])),
            "additional paired contrast recipe/registration definition differs")


def analyze_update(feedback, *, protocol, recipe, roster):
    """Analyze already-qualified feedback; the CLI must freshly reverify its family."""
    require(
        isinstance(feedback, CompleteSystemFeedback), "complete feedback is required"
    )
    d = feedback.as_json()
    stage_name = d["family_id"]
    require(
        stage_name in {"update-1", "update-2", "update-3"}
        and bool(d.get("read_authority")),
        "analysis needs an authorized TRAIN update",
    )
    require_stage_feedback(protocol, stage_name, feedback)
    family, members = recipe_family_identity(recipe)
    evaluation = recipe["system_search_evaluation"]
    bindings = evaluation["member_bindings"]
    require(
        family == stage_name
        and evaluation["stage"] == stage_name
        and evaluation["schema"] == "saea-system-search-evaluation-binding-v1"
        and evaluation["protocol_sha256"] == content_hash(protocol),
        "registered analysis protocol differs",
    )
    require(
        set(bindings) == set(d["summaries"])
        and members
        == {cid: b["run_id"] for cid, b in bindings.items()},
        "analysis member identity differs",
    )
    sources = d["feedback"]["sources"]
    require(
        len(sources) == len(bindings)
        and {s["candidate_id"] for s in sources} == set(bindings),
        "complete source identity differs",
    )
    for source in sources:
        require(
            all(
                source[k] == bindings[source["candidate_id"]][k]
                for k in ("run_id", "config_hash")
            ),
            "measured source differs from the frozen evaluation",
        )
    for branch in ("L", "B"):
        parent, aa = branch + "-parent", branch + "-parent-aa"
        require(
            parent in bindings
            and aa in bindings
            and bindings[parent]["bundle_id"] == bindings[aa]["bundle_id"],
            "both same-chain parent/A/A identities are required",
        )
    require(
        bindings["B-parent"]["bundle_id"] == protocol["seed_bundle"]["bundle_id"],
        "blind parent differs from seed",
    )
    ids = stage_for(protocol, stage_name)["sample_ids"]
    require(len(ids) >= 400, "system search analysis requires at least 400 rows")
    report = _describe_complete_cohort(d, ids=ids, bindings=bindings, recipe=recipe, roster=roster)
    report["protocol_sha256"] = content_hash(protocol)
    return report


def _describe_complete_cohort(d, *, ids, bindings, recipe, roster, branch_names=("L", "B"), comparison_groups=None):
    """Shared statistics only; callers enforce their separate admission and READ gates."""
    stage_name = d["family_id"]
    resampling = recipe["resampling"]
    require(
        set(resampling) == {"bootstrap_draws", "confidence", "seed", "unit"}
        and resampling["unit"]
        == "paired utterance; keep all recording variants together"
        and resampling["confidence"] == 0.95
        and type(resampling["seed"]) is int
        and type(resampling["bootstrap_draws"]) is int
        and resampling["bootstrap_draws"] > 0,
        "registered paired resampling differs",
    )
    require(ids and len(set(ids)) == len(ids) and set(roster) == set(ids)
            and all(s.startswith("slurp:train:") for s in ids),
            "complete TRAIN metadata roster differs")
    groups = d["feedback"]["groups"]
    require([g["sample_id"] for g in groups] == ids,
            "complete ordered cohort differs or contains duplicates")
    cluster_strata = {}
    for sid in ids:
        row = roster[sid]
        require(
            row.get("sample_id") == sid
            and all(
                isinstance(row.get(k), str) and row[k]
                for k in ("utterance_id", "stratum")
            ),
            "utterance/stratum metadata is missing",
        )
        cluster = row["utterance_id"]
        require(
            cluster_strata.setdefault(cluster, row["stratum"]) == row["stratum"],
            "utterance crosses strata",
        )
    counts, execution = {cid: {} for cid in bindings}, {cid: [] for cid in bindings}
    for group in d["feedback"]["groups"]:
        members = group["members"]
        require(
            len(members) == len(bindings)
            and {m["candidate_id"] for m in members} == set(bindings),
            "each input must retain every complete system",
        )
        for member in members:
            cid, sid = member["candidate_id"], group["sample_id"]
            c = member["native_counts"]
            require(
                type(c["scenario_action_exact"]) in (int, float)
                and c["scenario_action_exact"] in (0, 1),
                "intent correctness must be binary",
            )
            counts[cid][sid] = c
            execution[cid].append(member["execution"])

    def metric(cid, selected, name):
        return (
            pooled_f1(counts[cid], selected, FIELDS)
            if name == "slu_f1"
            else math.fsum(
                counts[cid][sid]["scenario_action_exact"] for sid in selected
            )
            / len(selected)
        )

    costs = {}
    for cid, rows in execution.items():
        summary = d["summaries"][cid]
        for name in ("slu_f1", "intent"):
            require(
                math.isclose(
                    metric(cid, ids, name), summary[name], abs_tol=1e-6, rel_tol=0
                ),
                "pooled counts do not reproduce the official aggregate",
            )
        costs[cid] = {
            "rows": len(rows),
            "terminal_kinds": dict(Counter(r["delivery_kind"] for r in rows)),
        }
        for key in ("model_calls", "tool_calls", "prompt_tokens", "completion_tokens"):
            values = [r[key] for r in rows]
            require(
                all(v is None or type(v) is int and v >= 0 for v in values),
                "execution cost must be a nonnegative count",
            )
            require(
                key not in {"model_calls", "tool_calls"} or None not in values,
                "attributed contacts are required",
            )
            costs[cid][key] = None if None in values else sum(values)
        wall = [r.get("wall_time_seconds") for r in rows]
        require(
            all(
                v is None or type(v) in (int, float) and math.isfinite(v) and v >= 0
                for v in wall
            ),
            "elapsed time must be finite and nonnegative",
        )
        costs[cid]["wall_time_seconds"] = None if None in wall else math.fsum(wall)
        for field in ("role_contacts", "tool_events"):
            entries = [r.get(field) for r in rows]
            if any(entry is None for entry in entries):
                costs[cid][field] = None
            else:
                require(
                    all(
                        isinstance(entry, dict)
                        and all(type(v) is int and v >= 0 for v in entry.values())
                        for entry in entries
                    ),
                    "contact detail must contain nonnegative counts",
                )
                costs[cid][field] = {
                    key: sum(entry.get(key, 0) for entry in entries)
                    for key in sorted({key for entry in entries for key in entry})
                }
        for key in ("model_calls", "tool_calls"):
            require(
                costs[cid][key] == summary[key], "attributed cost and aggregate differ"
            )
        for key in ("reliable_completion", "abstained"):
            require(
                all(type(r[key]) is bool for r in rows),
                "terminal disposition must be explicit",
            )
            costs[cid][key + "_rate"] = sum(r[key] for r in rows) / len(rows)
        require(
            costs[cid]["reliable_completion_rate"]
            == summary["reliable_completion_rate"],
            "completion aggregate differs",
        )
    strata = []
    for label in sorted({r["stratum"] for r in roster.values()}):
        selected = [sid for sid in ids if roster[sid]["stratum"] == label]
        strata.append(
            {
                "stratum": label,
                "n": len(selected),
                "members": {
                    cid: {m: metric(cid, selected, m) for m in ("slu_f1", "intent")}
                    for cid in bindings
                },
            }
        )
    equal = {
        cid: {
            m: math.fsum(s["members"][cid][m] for s in strata) / len(strata)
            for m in ("slu_f1", "intent")
        }
        for cid in bindings
    }
    if comparison_groups is None:
        require(branch_names in (("L", "B"), ("B",)), "invalid descriptive branch scope")
        comparison_groups = {}
        for branch in branch_names:
            parent, aa = branch + "-parent", branch + "-parent-aa"
            candidates = sorted(cid for cid in bindings
                                if cid.startswith(branch + "-") and cid not in {parent, aa})
            require(all(cid in {branch + "-candidate-1", branch + "-candidate-2"}
                        for cid in candidates), "unexpected update slot")
            comparison_groups[branch] = (parent, aa, candidates)
    else:
        require(isinstance(comparison_groups, dict) and comparison_groups,
                "explicit comparison groups required")
        declared = []
        for parent, aa, candidates in comparison_groups.values():
            selected = [parent, aa, *candidates]
            require(len(selected) == len(set(selected)) and set(selected) <= set(bindings),
                    "comparison group members differ")
            declared.extend(selected)
        require(set(declared) == set(bindings), "comparisons must cover every member")
    additional = validate_additional_paired_contrasts(recipe, comparison_groups)
    branches = {}
    for branch, (parent, aa, candidates) in comparison_groups.items():
        pairs = {"same-request-null": (parent, aa)}
        for cid in candidates:
            suffix = cid.removeprefix(branch + "-")
            pairs[suffix + "-minus-parent"] = (parent, cid)
            pairs[suffix + "-minus-aa"] = (aa, cid)
        contrasts = {}
        for name, (left, right) in pairs.items():
            contrasts[name] = {"left": left, "right": right}
            for m in ("slu_f1", "intent"):
                result = resampled_statistic(
                    sample_ids=ids,
                    statistic=lambda selected, m=m, left_id=left, right_id=right: (
                        metric(right_id, selected, m) - metric(left_id, selected, m)
                    ),
                    cluster_of=lambda sid: roster[sid]["utterance_id"],
                    seed=resampling["seed"],
                    n_replicates=resampling["bootstrap_draws"],
                    ci_level=resampling["confidence"],
                )
                contrasts[name][m] = result.as_json()
        measurements = [
            {
                "candidate_id": cid,
                "bundle_id": bindings[cid]["bundle_id"],
                "cohort_id": content_hash(ids),
                **{k: d["summaries"][cid][k] for k in OBJECTIVES},
            }
            for cid in [parent, aa, *candidates]
        ]
        null = contrasts["same-request-null"]
        branches[branch] = {
            "comparisons": contrasts,
            "measurements": measurements,
            "frontier": pareto_frontier(measurements, identity_key="candidate_id"),
            "own_null_half_width": {
                m: (null[m]["ci_high"] - null[m]["ci_low"]) / 2
                for m in ("slu_f1", "intent")
            },
            "replicate_policy": "A/A remains a separate measurement, not a selectable policy; use the designated parent for retention.",
        }
    report = {
        "schema": "saea-system-text-update-read-v1",
        "status": "DESCRIPTIVE-ROOT-REVIEW-REQUIRED",
        "family_id": stage_name,
        "read_authority": d["read_authority"],
        "feedback_sha256": content_hash(d),
        "sample_count": len(ids),
        "cluster_count": len(cluster_strata),
        "resampling": resampling,
        "proposal_attrition": recipe.get("attrition"),
        "official_summaries": d["summaries"],
        "execution": costs,
        "per_stratum": strata,
        "equal_stratum_macro": equal,
        "branches": branches,
        "equal_stratum_definition": "Arithmetic mean of within-stratum pooled metrics; descriptive, not the official pooled endpoint.",
        "units": "All quality, differences, confidence endpoints and null half-widths use the zero-to-one scale.",
        "interpretation": "Root applies the preregistered own-A/A protection and tie-breaks. No automatic selection, adoption, node-level causal credit or cross-cohort frontier.",
        "contacts_added": {"model": 0, "scorer": 0},
    }
    if additional is not None:
        entries = {}
        for contrast in additional["contrasts"]:
            coefficients = contrast["coefficients"]
            result = resampled_statistic(
                sample_ids=ids,
                statistic=lambda selected, coefficients=coefficients: math.fsum(
                    weight * metric(cid, selected, "slu_f1")
                    for cid, weight in sorted(coefficients.items())
                ),
                cluster_of=lambda sid: roster[sid]["utterance_id"],
                seed=resampling["seed"],
                n_replicates=resampling["bootstrap_draws"],
                ci_level=resampling["confidence"],
            )
            entries[contrast["id"]] = {
                "coefficients": deepcopy(coefficients), "slu_f1": result.as_json(),
            }
        stratum_points = [
            {"stratum": row["stratum"], "n": row["n"], "contrasts": {
                contrast["id"]: math.fsum(
                    weight * row["members"][cid]["slu_f1"]
                    for cid, weight in sorted(contrast["coefficients"].items())
                ) for contrast in additional["contrasts"]
            }} for row in strata
        ]
        report["additional_paired_contrasts"] = {
            "definition": deepcopy(additional),
            "contrasts": entries,
            "per_stratum": stratum_points,
            "equal_stratum_macro": {
                name: math.fsum(row["contrasts"][name] for row in stratum_points) / len(stratum_points)
                for name in entries
            },
            "estimand": "Signed sum of separately pooled member SLU-F1 on each identical paired utterance-cluster draw.",
            "units": "Zero-to-one F1 scale; signed contrasts can exceed a single member's range.",
            "stratum_definition": "Within-stratum signed pooled-F1 points and their arithmetic macro mean are descriptive; no stratum intervals or official pooled substitution.",
            "interpretation": "Additional descriptive endpoints with nominal 95% paired intervals. "
            "They do not adjust for donor selection, prior search, multiplicity or unobserved run variation. "
            "Pooled F1 is nonlinear; the interaction is departure from additivity for fixed whole-system policies, "
            "not causal node credit, semantic synergy, independent validation, stable benefit or adoption. "
            "The designated control and A/A remain separate; neither is automatically selected, averaged or used as an unregistered calibration adjustment.",
        }
    return report
