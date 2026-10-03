"""Prepare nested fixed400 inputs and held shared-runtime slots without dispatch."""

import copy
import json
from pathlib import Path

from ..data.runtime_subset import build_runtime_subset
from .hashing import content_hash
from .system_text_policy import require

MEMBERS = tuple(
    f"{branch}-{role}"
    for branch in ("L", "B")
    for role in ("parent", "parent-aa", "candidate-1", "candidate-2")
)
ITEM_KEYS = {
    "sample_id",
    "audio_seconds",
    "audio_sha256",
    "media_relpath",
    "packet_id",
    "sample_rate_hz",
}


def build_stage(parent, template, baseline, *, size, expected_pool_hash):
    """Return metadata-only scaffolding; policy freeze and real admission remain owed.

    The compiled seed is a preparation basis, never an invented proposal. Every
    member remains held and lacks worker/campaign stages, even where seed text is
    already known. The exact final candidate must be recompiled and prepared.
    """
    require(type(size) is int and size in (50, 100, 200), "unrequested scale")
    ids = [i["sample_id"] for i in parent["items"]]
    require(
        parent["count"] == len(ids) == len(set(ids)) == 400
        and parent["split_role"] == "discovery"
        and parent["carrier_lock_key"] == "slurp"
        and all(i.startswith("slurp:train:") for i in ids)
        and content_hash(ids) == expected_pool_hash,
        "source must be the exact fixed400 TRAIN pool",
    )
    require(
        all(set(item) == ITEM_KEYS for item in parent["items"]),
        "runtime item contains undeclared or target fields",
    )
    prefix = f"slurp-native-stage3-system-text-fixed400-scale{size}"
    dataset = f"slurp-speech-native-system-text-fixed400-prefix{size}-owner225-v1"
    roster = f"docs/receipts/rosters/slurp-system-text-fixed400-prefix{size}-owner225-v1.json"
    view, receipt = build_runtime_subset(
        parent,
        seed=20261001,
        count=size,
        name=f"SLURP-SYSTEM-TEXT-FIXED400-PREFIX{size}-OWNER225-V1",
    )
    require(
        receipt["sample_ids"] == ids[:size],
        "source order is not the registered stable prefix",
    )
    members = []
    for member in MEMBERS:
        slug = f"{prefix}-{member.lower()}-v1"
        run = f"SAEA-SLURP-SYSTEM-TEXT-FIXED400-SCALE{size}-{member.upper()}-V1"
        attempt = f"attempt-{prefix}-{member.lower()}-generation-v1"
        e, b = copy.deepcopy(template), copy.deepcopy(baseline)
        c = e["cells"][0]
        c.update(
            cell_id=slug,
            run_id=run,
            attempt_id=attempt,
            baseline_fragment=slug,
            dataset_fragment=dataset,
            allowed_execution_stages=["check", "prepare-supply"],
            readiness={
                "state": "held",
                "requirements": [],
                "reason": "Offline owner225 scale preparation only. Review previous stage, freeze exact policies, prepare each binding, register FIT/engineering/family and obtain root admission before worker stages.",
            },
            system_text_scaling_slot={
                "member": member,
                "policy_status": "pending-freeze",
                "basis": "Corrected CONTROL2 seed; not a new proposal or selected candidate",
                "input_namespace": "learning" if member.startswith("L-") else "blind",
            },
        )
        e.update(
            experiment_id=run,
            date="2026-10-03",
            split_id=view["split_name"],
            population={
                "count": size,
                "roster_receipt": roster,
                "split_identity_hash": view["split_identity_hash"],
            },
            populations=[{"dataset_fragment": dataset, "ids": ids[:size]}],
        )
        e["execution_plan"]["planned_model_calls"] = 13 * size
        e["family_budget"] = {
            "complete_system_trajectories": size,
            "generation_calls_cap": 13 * size,
            "knowledge_tool_calls_cap": size,
            "official_complete_scoring_jobs": 1,
        }
        e["stage3_measurement"] = {
            "claims_benefit": False,
            "measurement_design": "form-proof",
            "expected_effect_pp": 0,
            "rows": size,
            "primary_metric": "Exploratory system diagnosis; formal claim not admitted",
            "primary_metric_key": "slu",
            "read_roster": view["split_name"],
            "tuning_roster": "none",
            "note": "Reused optimization prefix; retain cumulative exposure. Full family and in-chain A/A required before read. Final analysis registration remains pending.",
        }
        b.pop("prepared_phase_supply", None)
        b["native_contact_fit"].update(
            run_id=run.replace("-V1", "-FIT-V1"),
            attempt_id=attempt.replace("-generation-v1", "-fit-v1"),
            contact_cap=52 * size,
        )
        members.append(
            {"member": member, "experiment_name": slug, "experiment": e, "baseline": b}
        )
    return {
        "view": view,
        "roster": receipt,
        "dataset_name": dataset,
        "roster_path": roster,
        "members": members,
        "trajectory_ceiling": 8 * size,
        "contacts_authorized": 0,
    }


def bind_scaling_policy(
    compiled,
    policy_binding,
    *,
    source_protocol,
    cohort_binding,
    size,
    repo_root,
    data_root,
):
    """Prepare an unchanged policy on a larger prefix; never alter its proposal.

    The transient cohort projection is explicitly recorded and is used only by
    the shared input binder. It is not a successor proposal protocol, selection,
    registration or runtime admission. Return values remain preparation inputs.
    """
    from .system_optimization import assert_policy_roster, load_optimization_panel
    from .system_search_archive import SystemSearchArchive
    from .system_search_protocol import stage_for
    from .system_text_cohort import bind_system_text_cohort
    from .system_text_policy import _read_pin, verify_system_text_binding

    require(
        type(size) is int and size in (50, 100, 200), "unrequested preparation scale"
    )
    round_index = source_protocol.get("allocation_extension", {}).get("round")
    require(
        type(round_index) is int
        and round_index >= 4
        and source_protocol.get("updates") == round_index,
        "pin the extended source proposal round",
    )
    stage = f"update-{round_index}"
    require(cohort_binding.get("stage") == stage, "scaling source stage differs")
    resolved = load_optimization_panel(source_protocol, stage, repo_root=repo_root)
    require(resolved is not None, "scaling requires the owner's exact fixed pool")
    plan, pool = resolved
    source_stage = stage_for(source_protocol, stage)
    assert_policy_roster(
        [],
        source_stage["sample_ids"],
        protocol=source_protocol,
        stage=stage,
        repo_root=repo_root,
    )
    view = json.loads(_read_pin(cohort_binding["runtime_view"], repo_root))
    full = json.loads(_read_pin(plan["source_runtime_view"], repo_root))
    require(
        view.get("count") == size
        and view.get("items") == full["items"][:size]
        and all(set(item) == ITEM_KEYS for item in view["items"])
        and [i["sample_id"] for i in view["items"]] == pool[:size],
        "scaling must reuse exact immutable media/packet rows without target fields",
    )
    proof = verify_system_text_binding(
        compiled, policy_binding, repo_root=repo_root, data_root=data_root
    )
    policy_path = Path(data_root) / policy_binding["bundle"]["relpath"]
    bundle = SystemSearchArchive(policy_path.parent.parent).load_policy(
        policy_binding["bundle_id"]
    )
    # The source object and its file stay byte-identical. Only the read-only
    # cohort projection can differ, and only in the declared evaluation roster.
    evaluation_protocol = copy.deepcopy(source_protocol)
    evaluation_stage = stage_for(evaluation_protocol, stage)
    evaluation_stage.update(
        sample_ids=pool[:size], roster_sha256=content_hash(pool[:size])
    )
    if "rows" in evaluation_stage:
        evaluation_stage["rows"] = size
    if "trajectory_cap" in evaluation_stage:
        evaluation_stage["trajectory_cap"] = 8 * size
    exposure = assert_policy_roster(
        bundle.as_json()["cumulative_sources"],
        pool[:size],
        protocol=evaluation_protocol,
        stage=stage,
        repo_root=repo_root,
    )
    result = bind_system_text_cohort(
        compiled,
        cohort_binding,
        protocol=evaluation_protocol,
        stage=stage,
        repo_root=repo_root,
        data_root=data_root,
    )
    require(
        verify_system_text_binding(
            result, policy_binding, repo_root=repo_root, data_root=data_root
        )
        == proof,
        "scaling changed effective policy role bytes",
    )
    require(
        all(
            result.get(k) == compiled.get(k)
            for k in (
                "policy",
                "scorers",
                "phase_material",
                "phase_tools",
                "serving_slots",
                "serving_slot_tokens",
            )
        ),
        "scaling changed policy, scorer, tool or serving semantics",
    )
    receipt = {
        "schema": "saea-system-text-scaling-policy-preparation-v1",
        "source_proposal_protocol_sha256": content_hash(source_protocol),
        "source_proposal_round": round_index,
        "evaluation_protocol_sha256": content_hash(evaluation_protocol),
        "evaluation_stage": evaluation_stage,
        "cohort_binding_sha256": content_hash(cohort_binding),
        "pool_sample_ids_sha256": content_hash(pool),
        "prefix_sample_ids_sha256": content_hash(pool[:size]),
        "rows": size,
        "bundle_id": bundle.bundle_id,
        "policy_binding": copy.deepcopy(policy_binding),
        "source_configuration_sha256": content_hash(compiled),
        "prepared_configuration_sha256": content_hash(result),
        "role_sha256": proof["role_sha256"],
        "cumulative_sources_sha256": content_hash(
            bundle.as_json()["cumulative_sources"]
        ),
        "retained_exposure": exposure,
        "runtime_admission": "separate-required",
        "contacts_added": 0,
    }
    return {"baseline": result, "preparation": receipt}
