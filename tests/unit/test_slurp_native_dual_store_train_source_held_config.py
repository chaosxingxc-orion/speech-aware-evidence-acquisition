import os
import hashlib
import json

import pytest
from pathlib import Path

from speech_aware_evidence_acquisition.core.config import compose
from speech_aware_evidence_acquisition.rails.phase_supply import load_sealed_segment_vectors

REPO = Path(__file__).resolve().parents[2]
DATA = Path((os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET"))
PROMOTION = Path("/home/chao/feat-cache/slurp-q4km-packets-04ccc72a/EVO-FOLDS-V2-promotion.json")
EXPERIMENT = REPO / "configs/experiment/slurp-native-dual-store-train-source-folds-held-v1.json"
MODEL = "q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1"
FOLDS = {
    "a": {"dataset": "slurp-speech-native-evo-fold-a-1080", "baseline": "slurp-native-dual-store-train-fold-a-held-v1", "split_hash": "61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6", "query_sha": "e7a5b2264dc61fcab3c63d50fb645d4629d3f0a99f83ad5fbe323c73884e5f0b"},
    "b": {"dataset": "slurp-speech-native-evo-fold-b-1080", "baseline": "slurp-native-dual-store-train-fold-b-held-v1", "split_hash": "4407794c4a5d2e8883d93fdf242deb33c0987405d62e05a7d8416f5251a3484a", "query_sha": "83c5da6190fb2a65edf98a8f9ef35ff2cb310eb4e4b94eba9e04f9eedce9f299"},
}

def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def test_cells_are_held_check_only_and_compose_without_contact_authority():
    experiment = _read(EXPERIMENT)
    assert experiment["execution_profile"] == "model-free-check"
    assert [cell["prospective_partition_role"] for cell in experiment["cells"]] == ["corrective-guidance-source", "disjoint-train-evaluation"]
    recovery = _read(REPO / "configs/baseline/slurp-native-dual-store-dev1000-reboot-recovery-v1.json")
    for cell in experiment["cells"]:
        assert cell["allowed_execution_stages"] == ["check"]
        assert cell["readiness"]["state"] == "held"
        assert cell["run_id"].startswith("HELD-NO-CONTACT-")
    for fold, expected in FOLDS.items():
        values = compose(REPO, model=MODEL, dataset=expected["dataset"], baseline=expected["baseline"], experiment="slurp-native-dual-store-train-source-folds-held-v1").values
        assert values["split_identity_hash"] == expected["split_hash"]
        assert values["policy"] == recovery["policy"]
        assert values["native_episode"] == recovery["native_episode"]
        assert values["phase_material"] == recovery["phase_material"]
        assert values["phase_tools"] == recovery["phase_tools"]
        assert values["scorers"] == []
        assert not {"execution_plan", "native_contact_fit", "prepared_phase_supply", "prepared_phase_recall", "live_phase_fit"} & set(values)
        query = values["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]["query_source"]
        assert query["kind"] == "sealed-segment-vectors"
        assert query["sha256"] == expected["query_sha"]
        assert f"slurp-intent-boundaries-train-fold-{fold}" in query["relpath"]

@pytest.mark.skipif(
    not DATA.is_dir() or not PROMOTION.is_file(),
    reason="Requires the local sealed TRAIN vectors and promoted packet metadata",
)
def test_fold_segments_join_datasets_and_promoted_packets_exactly():
    assert hashlib.sha256(PROMOTION.read_bytes()).hexdigest() == "4f048f47830a22d41d0bc81ccb453efd41bf8c6726a462bd1dc11eab36f30247"
    packets = {row["packet_id"]: row for row in _read(PROMOTION)["packets"]}
    rosters = {}
    for fold, expected in FOLDS.items():
        dataset = _read(REPO / f"configs/dataset/{expected['dataset']}.json")
        baseline = _read(REPO / f"configs/baseline/{expected['baseline']}.json")
        pin = baseline["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]["query_source"]
        queries = load_sealed_segment_vectors(DATA / pin["relpath"], expected_sha256=pin["sha256"], dimensions=("intent-boundary",))
        items = {row["sample_id"]: row for row in dataset["items"]}
        assert len(items) == len(queries) == 1080
        assert set(items) == set(queries)
        for sample_id, item in items.items():
            assert queries[sample_id].audio_sha256 == item["audio_sha256"]
            assert packets[item["packet_id"]]["audio_sha256"] == item["audio_sha256"]
        rosters[fold] = set(items)
    assert rosters["a"].isdisjoint(rosters["b"])

def test_released_store_registrations_forbid_both_fold_rosters():
    expected = {"docs/receipts/rosters/slurp-evo-fold-a-v2.json", "docs/receipts/rosters/slurp-evo-fold-b-v2.json"}
    registrations = ["docs/readiness/2026-09-13-slurp-intent-boundaries-preparation-registration-v2.json", "docs/readiness/2026-09-13-slurp-slot-contracts-preparation-registration-v1.json"]
    for relpath in registrations:
        document = _read(REPO / relpath)
        entries = {entry["relpath"]: entry for entry in document["forbidden_rosters"]}
        assert expected <= set(entries)
        for path in expected:
            assert hashlib.sha256((REPO / path).read_bytes()).hexdigest() == entries[path]["sha256"]
