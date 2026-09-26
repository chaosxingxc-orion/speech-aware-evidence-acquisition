
"""Prevent a registered family read before every complete official score exists."""
import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[2] / "scripts/analysis/system_memory_batch_read.py"


def reader():
    spec = importlib.util.spec_from_file_location("memory_batch_reader_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def family(tmp_path):
    reg = {"arms": {}}
    for index in range(8):
        label, run, attempt = f"arm{index}", f"run{index}", f"attempt{index}"
        reg["arms"][label] = {"run_id": run, "attempt_id": attempt,
                             "expected_rows": 4, "expected_official_scores": 1}
        ap = tmp_path / "attempts" / run / (attempt + ".json")
        ap.parent.mkdir(parents=True)
        ap.write_text(json.dumps({"state": "FINALIZED"}))
        fp = tmp_path / "runs" / run / attempt / "flight-receipts.json"
        fp.parent.mkdir(parents=True)
        fp.write_text(json.dumps({"stages": {
            "seal": {"outputs_row_count": 4},
            "score": {"job_count": 1, "result": {"succeeded": 1, "failed": 0}}
        }}))
    return reg


def test_complete_family_read_gate(tmp_path):
    reg = family(tmp_path)
    reader().require_complete_family(tmp_path, reg)


@pytest.mark.parametrize("defect", ["open", "absent", "no-score", "failed", "twice", "partial"])
def test_last_incomplete_member_blocks_whole_family(tmp_path, defect):
    reg = family(tmp_path)
    ap = tmp_path / "attempts/run7/attempt7.json"
    fp = tmp_path / "runs/run7/attempt7/flight-receipts.json"
    if defect == "open":
        ap.write_text(json.dumps({"state": "OPENED"}))
    elif defect == "absent":
        ap.unlink()
    else:
        doc = json.loads(fp.read_text())
        if defect == "no-score":
            del doc["stages"]["score"]
        elif defect == "failed":
            doc["stages"]["score"]["result"]["failed"] = 1
        elif defect == "twice":
            doc["stages"]["score"]["job_count"] = 2
        elif defect == "partial":
            doc["stages"]["seal"]["outputs_row_count"] = 3
        fp.write_text(json.dumps(doc))
    with pytest.raises(ValueError):
        reader().require_complete_family(tmp_path, reg)
