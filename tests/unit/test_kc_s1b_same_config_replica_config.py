import os
import hashlib
import json
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
CONFIG = REPO / "configs/experiment/slurp-slot-stage-kc-s1b-same-config-replicate-v1.json"


def test_replica_keeps_four_fragments_and_held_readiness():
    document = json.loads(CONFIG.read_text(encoding="utf-8"))
    fit, generation = document["cells"]
    assert document["experiment_id"] == "SAEA-SLURP-KC-S1B-SAME-CONFIG-REPLICATE-V1"
    assert fit["run_id"] == "SAEA-SLURP-KC-S1B-SAME-CONFIG-REPLICATE-FIT-V1"
    assert generation["run_id"] == document["experiment_id"]
    assert fit["readiness"]["state"] == "held"
    # The generation cell was held as registered (a1042b0c) and flipped to ready by 0805094f ("register fitted KC
    # replication"), whose only requirement is the fit cell's own complete request fit.
    assert generation["readiness"]["state"] in ("held", "ready")
    if generation["readiness"]["state"] == "ready":
        requirements = generation["readiness"]["requirements"]
        assert [req["kind"] for req in requirements] == ["preparation"]
        assert requirements[0]["relpath"] == f"prepared/{fit['run_id']}/request-fit.json"
        assert requirements[0] == {**requirements[0], **{k: document["prepared_request_fit"][k] for k in ("relpath", "sha256")}}
    assert fit["allowed_execution_stages"] == ["check", "wire-check", "prompt-fit"]
    assert generation["allowed_execution_stages"] == ["check", "wire-check", "prepare-supply", "worker", "campaign"]
    assert fit["baseline_fragment"] == generation["baseline_fragment"] == "slurp-phase-slots-given-intent-schema-v1"
    assert fit["model_fragment"] == generation["model_fragment"] == "q4km-mmproj-free-speech-native-np4-base-speech-query-prefix-max64"
    assert fit["dataset_fragment"] == generation["dataset_fragment"] == "slurp-speech-native-dev1000"


def test_predecessor_manifest_hash_and_fit_endpoint_budget_are_exact():
    document = json.loads(CONFIG.read_text(encoding="utf-8"))
    predecessor = document["replication_source"]
    data_root = Path((os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET"))
    manifest = data_root / predecessor["manifest_relpath"]
    assert hashlib.sha256(manifest.read_bytes()).hexdigest() == predecessor["manifest_sha256"]
    runtime = document["runtime_predecessor"]
    runtime_manifest = data_root / runtime["manifest_relpath"]
    assert hashlib.sha256(runtime_manifest.read_bytes()).hexdigest() == runtime["manifest_sha256"]
    basis = document["prompt_fit"]["endpoint_count_basis"]
    assert basis["total"] == basis["props"] + basis["apply_template_total"] + basis["tokenize_total"]
    assert basis["apply_template_total"] == basis["roster_rows"]
    assert basis["tokenize_total"] == 2 * basis["roster_rows"]
    assert document["prompt_fit"]["contact_cap_proposal"] == 3001
