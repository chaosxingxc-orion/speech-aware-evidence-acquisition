"""Prepare nested fixed400 inputs and held shared-runtime slots without dispatch."""

import copy

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
