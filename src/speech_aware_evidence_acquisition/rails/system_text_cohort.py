"""Bind a compiled policy to registered TRAIN inputs without changing its science."""

import copy
import json
from pathlib import Path

from .consumption_module import verify_declared_module
from .controllers import default_phase_program
from .hashing import content_hash
from .phase_supply import load_phase_supply_specs, load_sealed_agreement
from .system_text_policy import _read_pin, require


def _pin(document):
    return {key: document[key] for key in ("relpath", "sha256")}


def _vote_spec(baseline):
    return load_phase_supply_specs(
        {
            "phase_supply": baseline["knowledge_stores"]["train-exemplars"][
                "phase_supply"
            ]
        },
        default_phase_program(baseline["policy"]),
    )["solver"].as_json()


def bind_system_text_cohort(
    compiled, binding, *, protocol, stage, repo_root, data_root, module_repo_root=None
):
    """Verify exact roster and frozen vote inputs, then replace only input bindings.

    Do not prepare supplies, run FIT, admit a flight or open task outputs. The
    bootstrap fragment provides pinned query and packet identities, never policy
    text or knowledge edits. Every later run still needs its own preparation.
    """
    require(
        set(binding)
        == {
            "schema",
            "stage",
            "runtime_view",
            "bootstrap_baseline",
            "agreement_receipt",
        }
        and binding["schema"] == "saea-system-text-cohort-binding-v1"
        and binding["stage"] == stage
        and stage in {"update-1", "update-2", "update-3", "selection"},
        "cohort binding fields or stage differ",
    )
    stages = [s for s in protocol["stages"] if s["stage"] == stage]
    require(len(stages) == 1, "cohort stage is missing or duplicated")
    registered = stages[0]
    view = json.loads(_read_pin(binding["runtime_view"], repo_root))
    ids = [row["sample_id"] for row in view["items"]]
    require(
        ids == registered["sample_ids"]
        and content_hash(ids) == registered["roster_sha256"]
        and len(ids) == len(set(ids)) == view["count"]
        and bool(ids)
        and all(s.startswith("slurp:train:") for s in ids)
        and view["split_role"] == "discovery"
        and view["runtime_view_sha256"]
        == content_hash({k: v for k, v in view.items() if k != "runtime_view_sha256"}),
        "runtime view differs from the exact registered TRAIN cohort",
    )
    bootstrap = json.loads(_read_pin(binding["bootstrap_baseline"], repo_root))
    receipt = json.loads(_read_pin(binding["agreement_receipt"], data_root))
    stores = compiled["knowledge_stores"]
    source_stores = bootstrap["knowledge_stores"]
    for name, phase in (
        ("train-exemplars", "solver"),
        ("intent-boundaries", "perception"),
    ):
        require(
            all(
                stores[name][key] == source_stores[name][key]
                for key in ("snapshot", "release")
            ),
            "bootstrap changes the frozen intent or exemplar knowledge",
        )
    # Only exemplar retrieval generated the vote artifact. The bootstrap's
    # historical intent ranker is not used or copied into the compiled policy.
    vote = _vote_spec(compiled)
    bootstrap_vote = _vote_spec(bootstrap)
    require(
        {k: v for k, v in vote.items() if k != "query_source"}
        == {k: v for k, v in bootstrap_vote.items() if k != "query_source"},
        "bootstrap changes the frozen voting rules",
    )
    derived, artifact = receipt["derived_from"], receipt["artifact"]
    require(
        receipt.get("schema") == "saea-phase-agreement-receipt-v1"
        and {"model", "encoder", "gpu", "scorer"} <= set(receipt.get("contacts", {}))
        and all(type(v) is int and v == 0 for v in receipt["contacts"].values())
        and derived["split_identity_hash"] == view["split_identity_hash"]
        and derived["vote_store"] == "train-exemplars"
        and derived["vote_phase"] == "solver"
        and derived["target_store"] == "intent-boundaries"
        and derived["vote_snapshot_sha256"]
        == stores["train-exemplars"]["snapshot"]["sha256"]
        and derived["target_snapshot_sha256"]
        == stores["intent-boundaries"]["snapshot"]["sha256"]
        and derived["vote_spec"] == bootstrap_vote
        and artifact["rows"] == len(ids)
        and artifact["dimension"] == "agreement:exemplar-intent",
        "agreement receipt does not bind this cohort and frozen vote pool",
    )
    _read_pin(_pin(artifact), data_root)
    agreement = load_sealed_agreement(
        Path(data_root) / artifact["relpath"],
        expected_sha256=artifact["sha256"],
        dimension=artifact["dimension"],
    )
    require(
        set(agreement) == set(ids), "agreement rows differ from the complete cohort"
    )
    result = copy.deepcopy(compiled)
    sources = list(result.get("preparation_source_receipts", []))
    sources.extend(bootstrap.get("preparation_source_receipts", []))
    for name, phase in (
        ("train-exemplars", "solver"),
        ("intent-boundaries", "perception"),
    ):
        query = source_stores[name]["phase_supply"][phase]["query_source"]
        rows = [
            json.loads(line)
            for line in _read_pin(_pin(query), data_root).splitlines()
            if line.strip()
        ]
        query_ids = [row["id"] for row in rows]
        require(
            len(query_ids) == len(set(query_ids)) and set(ids) <= set(query_ids),
            "query source is duplicated or missing registered rows",
        )
        result["knowledge_stores"][name]["phase_supply"][phase]["query_source"] = (
            copy.deepcopy(query)
        )
        sources.append({"root": "data", **_pin(query)})
    descriptor = {
        "kind": "sealed-agreement",
        **_pin(artifact),
        "tool_contact_ledger_row": receipt["artifact_id"],
        "embedded_signal": f"Pinned {stage} speech-query votes from the frozen source-excluded exemplar pool; no evaluation labels.",
    }
    result["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"][
        "agreement_source"
    ] = descriptor
    block = result["native_episode"]["consumption_module"]
    components = [
        c for c in block["components"] if c["component_id"] == "agree-vote-seed"
    ]
    require(
        len(components) == 1 and components[0]["state"] == "on",
        "frozen agreement component is absent",
    )
    components[0]["params"]["agreement_source"] = copy.deepcopy(descriptor)
    for key in (
        "speech_packet_promotion_receipt",
        "speech_packet_promotion_receipt_sha256",
    ):
        result[key] = bootstrap[key]
    for key, root in (
        ("runtime_view", "repository"),
        ("bootstrap_baseline", "repository"),
        ("agreement_receipt", "data"),
    ):
        sources.append({"root": root, **binding[key]})
    result["preparation_source_receipts"] = list(
        {content_hash(p): p for p in sources}.values()
    )
    result.pop("prepared_phase_supply", None)
    result.pop("native_contact_fit", None)
    verify_declared_module(block, result, repo_root=Path(module_repo_root or repo_root))
    return result
