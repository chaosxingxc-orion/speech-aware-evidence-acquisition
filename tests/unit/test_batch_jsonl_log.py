"""The unattended batch logger must write one valid JSONL event per call."""

import json
from pathlib import Path
import subprocess
import sys


SCRIPT = Path(__file__).parents[2] / "scripts" / "flights" / "batch" / "batch_jsonl_log.py"
DRIVER = SCRIPT.with_name("batch_driver.sh")


def emit(event, detail, *extra):
    result = subprocess.run([sys.executable, str(SCRIPT), event, detail, *extra],
                            text=True, capture_output=True, check=True)
    assert result.stdout.count("\n") == 1
    return json.loads(result.stdout)


def test_multiline_inspector_failure_and_quotes_are_one_string_detail():
    raw = 'FAIL: no manifest\n{"status": "missing", "quote": "a\\"b"}\n'
    event = emit("arm-inspect", raw)
    assert event["event"] == "arm-inspect"
    assert event["detail"] == raw


def test_valid_json_detail_remains_an_object():
    event = emit("arm-exit", '{"step":6,"rc":9}')
    assert event["detail"] == {"step": 6, "rc": 9}


def test_stop_text_is_preserved_even_if_json_shaped():
    event = emit("STOP", '{"incident": "failure"}', "--text")
    assert event["detail"] == '{"incident": "failure"}'


def test_driver_routes_log_through_serializer():
    source = DRIVER.read_text(encoding="utf-8")
    assert 'batch_jsonl_log.py' in source
    assert 'log "STOP" "$1" --text' in source
