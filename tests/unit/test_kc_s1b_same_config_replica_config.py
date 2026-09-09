import hashlib
import json
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
CONFIG = REPO / "configs/experiment/slurp-slot-stage-kc-s1b-same-config-replicate-v1.json"


def test_replica_keeps_four_fragments_and_held_readiness():
    document = json.loads(CONFIG.read_text(encoding="utf-8"))
    cell = document["cells"][0]
    assert document["experiment_id"] == "SAEA-SLURP-KC-S1B-SAME-CONFIG-REPLICATE-V1"
    assert cell["run_id"] == document["experiment_id"]
    assert cell["readiness"]["state"] == "held"
    assert cell["baseline_fragment"] == "slurp-phase-slots-given-intent-schema-v1"
    assert cell["model_fragment"] == "q4km-mmproj-free-speech-native-np4-base-speech-query-prefix-max64"
    assert cell["dataset_fragment"] == "slurp-speech-native-dev1000"


def test_predecessor_manifest_hash_and_fit_endpoint_budget_are_exact():
    document = json.loads(CONFIG.read_text(encoding="utf-8"))
    predecessor = document["predecessor"]
    data_root = Path("/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data")
    manifest = data_root / predecessor["manifest_relpath"]
    assert hashlib.sha256(manifest.read_bytes()).hexdigest() == predecessor["manifest_sha256"]
    basis = document["prompt_fit"]["endpoint_count_basis"]
    assert basis["total"] == basis["props"] + basis["apply_template_total"] + basis["tokenize_total"]
    assert basis["apply_template_total"] == basis["roster_rows"]
    assert basis["tokenize_total"] == 2 * basis["roster_rows"]
    assert document["prompt_fit"]["contact_cap_proposal"] == 3001
