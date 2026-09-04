"""Unit tests for reproduction.slurp_official_eval.

No real data, no subprocess on the real evaluator here (that lives in the
one opt-in integration test at the bottom, gated on
``SAEA_SLURP_OFFICIAL_EVAL=1`` plus a real ``SPEECHRL_DATA_DIR``): every test
above it uses synthetic ``SlurpRecord``/``PredictedSlurpSample`` objects,
monkeypatched subprocess stand-ins, or a fabricated (non-pinned) evaluator
checkout.
"""

from __future__ import annotations

import io
import json
import os
import subprocess
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.data.slurp import SlurpRecord
from speech_aware_evidence_acquisition.reproduction import slurp_official_eval as soe
from speech_aware_evidence_acquisition.reproduction.slurp_official_eval import (
    SLURP_OFFICIAL_COMMIT,
    SLURP_OFFICIAL_SCORER_VERSION,
    OfficialSluResult,
    PredictedSlurpSample,
    SlurpOfficialEvalError,
    _parse_official_stdout,
    official_evaluator_root,
    run_official_evaluate,
    score_slurp_outputs_official,
    write_official_inputs,
)
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import SlotEntity


def _gold(
    sample_id: str,
    scenario: str,
    action: str,
    entities: tuple[SlotEntity, ...],
    *,
    split: str = "devel",
) -> SlurpRecord:
    return SlurpRecord(
        sample_id=sample_id,
        utterance_id=sample_id.split(":")[2],
        split=split,
        media_relpath=f"slurp_real/{sample_id}.flac",
        audio_seconds=1.5,
        scenario=scenario,
        action=action,
        intent=f"{scenario}_{action}",
        entities=entities,
    )


# ---------------------------------------------------------------------------
# write_official_inputs: format assertions (derived from util.py, module
# docstring) + round-trip fidelity of the synthetic tokens/span
# reconstruction.
# ---------------------------------------------------------------------------


def _official_release2prediction(document: dict) -> dict:
    """A faithful, minimal reimplementation of the official
    ``util.release2prediction`` (gold side, ``load_gold=False``) -- used
    ONLY to independently verify :func:`write_official_inputs`'s gold-file
    format round-trips exactly, without importing the real evaluator."""

    return {
        "text": " ".join(token["surface"] for token in document["tokens"]),
        "scenario": document["scenario"],
        "action": document["action"],
        "entities": [
            {
                "type": entity["type"],
                "filler": " ".join(
                    document["tokens"][i]["surface"].lower() for i in entity["span"]
                ),
            }
            for entity in document["entities"]
        ],
    }


def test_write_official_inputs_gold_round_trips_through_official_reconstruction(tmp_path):
    records = [
        _gold(
            "slurp:devel:000001:rec-a",
            "alarm",
            "set",
            (SlotEntity("time", "seven am"), SlotEntity("date", "tomorrow")),
        ),
        _gold("slurp:devel:000002:rec-b", "email", "send", (SlotEntity("person", "john"),)),
        # Zero-entity record: a legal SLURP utterance with no slots at all.
        _gold("slurp:devel:000003:rec-c", "music", "play", ()),
    ]
    predictions = [
        PredictedSlurpSample("slurp:devel:000001:rec-a", "alarm", "set", (SlotEntity("time", "seven am"),)),
        PredictedSlurpSample("slurp:devel:000002:rec-b", None, None, ()),
        PredictedSlurpSample("slurp:devel:000003:rec-c", "music", "play", ()),
    ]

    gold_path, pred_path = write_official_inputs(records, predictions, tmp_path)
    assert gold_path == tmp_path / "gold.jsonl"
    assert pred_path == tmp_path / "predictions.jsonl"

    gold_lines = [json.loads(line) for line in gold_path.read_text(encoding="utf-8").splitlines()]
    assert len(gold_lines) == 3
    for line, record in zip(gold_lines, records):
        assert set(line) == {"tokens", "scenario", "action", "entities", "recordings"}
        assert line["recordings"] == [{"file": record.sample_id}]
        reconstructed = _official_release2prediction(line)
        assert reconstructed["scenario"] == record.scenario
        assert reconstructed["action"] == record.action
        assert reconstructed["entities"] == [
            {"type": entity.type, "filler": entity.filler} for entity in record.entities
        ]

    pred_lines = [json.loads(line) for line in pred_path.read_text(encoding="utf-8").splitlines()]
    assert len(pred_lines) == 3
    for line, prediction in zip(pred_lines, predictions):
        assert set(line) == {"file", "scenario", "action", "entities"}
        assert line["file"] == prediction.sample_id
        assert line["scenario"] == prediction.scenario
        assert line["action"] == prediction.action
        assert line["entities"] == [
            {"type": entity.type, "filler": entity.filler} for entity in prediction.entities
        ]


def test_write_official_inputs_refuses_duplicate_gold_sample_id(tmp_path):
    records = [
        _gold("slurp:devel:000001:rec-a", "alarm", "set", ()),
        _gold("slurp:devel:000001:rec-a", "alarm", "set", ()),
    ]
    with pytest.raises(SlurpOfficialEvalError, match="duplicate gold sample_id"):
        write_official_inputs(records, [], tmp_path)


def test_write_official_inputs_refuses_duplicate_prediction_sample_id(tmp_path):
    predictions = [
        PredictedSlurpSample("slurp:devel:000001:rec-a", "alarm", "set", ()),
        PredictedSlurpSample("slurp:devel:000001:rec-a", "alarm", "set", ()),
    ]
    with pytest.raises(SlurpOfficialEvalError, match="duplicate prediction sample_id"):
        write_official_inputs([], predictions, tmp_path)


# ---------------------------------------------------------------------------
# official_evaluator_root: commit/content identity verification.
# ---------------------------------------------------------------------------


def test_official_evaluator_root_fails_closed_on_missing_checkout(tmp_path):
    with pytest.raises(SlurpOfficialEvalError, match="checkout missing"):
        official_evaluator_root(tmp_path)


def test_official_evaluator_root_fails_closed_on_missing_evaluation_dir(tmp_path):
    (tmp_path / "repos" / "slurp").mkdir(parents=True)
    with pytest.raises(SlurpOfficialEvalError, match="evaluator directory missing"):
        official_evaluator_root(tmp_path)


def _write_evaluator_files(evaluation_dir: Path, content: bytes = b"placeholder\n") -> None:
    evaluation_dir.mkdir(parents=True)
    (evaluation_dir / "metrics").mkdir()
    for relpath in ("evaluate.py", "util.py", "metrics/metrics.py", "metrics/distance.py"):
        (evaluation_dir / relpath).write_bytes(content)


def test_official_evaluator_root_git_head_mismatch_fails_closed(tmp_path):
    checkout = tmp_path / "repos" / "slurp"
    evaluation_dir = checkout / "scripts" / "evaluation"
    _write_evaluator_files(evaluation_dir)
    subprocess.run(["git", "init", "-q"], cwd=checkout, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=checkout, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=checkout, check=True)
    subprocess.run(["git", "add", "-A"], cwd=checkout, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=checkout, check=True)

    with pytest.raises(SlurpOfficialEvalError, match="expected the pinned commit"):
        official_evaluator_root(tmp_path)


def test_official_evaluator_root_content_hash_fallback_rejects_drifted_bytes(tmp_path):
    checkout = tmp_path / "repos" / "slurp"
    evaluation_dir = checkout / "scripts" / "evaluation"
    _write_evaluator_files(evaluation_dir, content=b"not the pinned bytes\n")
    # No .git metadata at all -> git rev-parse fails -> content-hash fallback.
    with pytest.raises(SlurpOfficialEvalError, match="content hash mismatch"):
        official_evaluator_root(tmp_path)


def test_official_evaluator_root_content_hash_fallback_accepts_matching_bytes(tmp_path, monkeypatch):
    checkout = tmp_path / "repos" / "slurp"
    evaluation_dir = checkout / "scripts" / "evaluation"
    content = b"fabricated-but-self-consistent evaluator bytes\n"
    _write_evaluator_files(evaluation_dir, content=content)
    fabricated_hash = soe._hash_file(evaluation_dir / "evaluate.py")
    monkeypatch.setattr(
        soe,
        "_PINNED_FILE_SHA256",
        {
            "evaluate.py": fabricated_hash,
            "util.py": fabricated_hash,
            "metrics/metrics.py": fabricated_hash,
            "metrics/distance.py": fabricated_hash,
        },
    )
    resolved = official_evaluator_root(tmp_path)
    assert resolved == evaluation_dir


def test_official_evaluator_root_matches_the_real_pinned_checkout():
    """When SPEECHRL_DATA_DIR is a real, unmutated checkout, verification
    must succeed through the git-HEAD branch (no data reads, no subprocess
    on evaluate.py itself -- just ``git rev-parse``)."""

    raw = os.environ.get("SPEECHRL_DATA_DIR")
    if not raw or not Path(raw).is_dir():
        pytest.skip("SPEECHRL_DATA_DIR not set to a real data root")
    root = Path(raw)
    if not (root / "repos" / "slurp" / ".git").exists():
        pytest.skip("repos/slurp has no git metadata in this environment")
    resolved = official_evaluator_root(root)
    assert resolved == root / "repos" / "slurp" / "scripts" / "evaluation"


# ---------------------------------------------------------------------------
# _parse_official_stdout / run_official_evaluate: a fake evaluate.py stdout
# fixture, built with the SAME print(text, "\n") call the real script uses.
# ---------------------------------------------------------------------------


def _fake_stdout(rows: dict[str, tuple[float, float, float, float, float, float]]) -> str:
    """``rows`` maps official ``format_results`` label -> (p, r, f, tp, fp, fn).
    Reproduces the exact ``print(formatted, "\\n")`` call evaluate.py makes
    for each block, in the SAME fixed order this module's parser expects."""

    buffer = io.StringIO()
    for label in (
        "scenario",
        "action",
        "intent (scen_act)",
        "entities",
        "entities (distance word)",
        "entities (distance char)",
        "SLU F1",
    ):
        p, r, f, tp, fp, fn = rows[label]
        header = f"{label.capitalize()},Precision,Recall,F-Measure,TP,FP,FN"
        row = f"OVERALL,{p},{r},{f},{tp},{fp},{fn}"
        print(header + "\n" + row, "\n", file=buffer)
    return buffer.getvalue()


_FIXTURE_ROWS = {
    "scenario": (0.9, 0.9, 0.9, 90.0, 10.0, 10.0),
    "action": (0.85, 0.85, 0.85, 85.0, 15.0, 15.0),
    "intent (scen_act)": (0.8, 0.8, 0.8, 80.0, 20.0, 20.0),
    "entities": (0.7, 0.6, 0.6470588235294118, 70.0, 30.0, 46.66666666666667),
    "entities (distance word)": (0.75, 0.65, 0.6962025316455696, 75.0, 25.5, 35.0),
    "entities (distance char)": (0.72, 0.62, 0.6666666666666666, 72.0, 28.0, 44.0),
    "SLU F1": (0.735, 0.635, 0.6813725490196079, 147.0, 53.5, 79.0),
}


def test_parse_official_stdout_recovers_exact_values():
    stdout = _fake_stdout(_FIXTURE_ROWS)
    raw = _parse_official_stdout(stdout)
    assert set(raw) == {
        "scenario",
        "action",
        "intent",
        "entities",
        "entities_distance_word",
        "entities_distance_char",
        "slu_f1",
    }
    assert raw["scenario"]["official_label"] == "Scenario"
    assert raw["intent"]["official_label"] == "Intent (scen_act)"
    assert raw["slu_f1"]["official_label"] == "Slu f1"
    for key, label in zip(
        (
            "scenario",
            "action",
            "intent",
            "entities",
            "entities_distance_word",
            "entities_distance_char",
            "slu_f1",
        ),
        (
            "scenario",
            "action",
            "intent (scen_act)",
            "entities",
            "entities (distance word)",
            "entities (distance char)",
            "SLU F1",
        ),
    ):
        p, r, f, tp, fp, fn = _FIXTURE_ROWS[label]
        entry = raw[key]
        assert entry["precision"] == pytest.approx(p)
        assert entry["recall"] == pytest.approx(r)
        assert entry["f_measure"] == pytest.approx(f)
        assert entry["tp"] == pytest.approx(tp)
        assert entry["fp"] == pytest.approx(fp)
        assert entry["fn"] == pytest.approx(fn)


def test_parse_official_stdout_fails_closed_on_too_few_blocks():
    stdout = _fake_stdout(_FIXTURE_ROWS)
    truncated = "\n".join(stdout.splitlines()[:4])  # keep only part of the first block
    with pytest.raises(SlurpOfficialEvalError, match="expected 7"):
        _parse_official_stdout(truncated)


def test_run_official_evaluate_builds_command_and_parses_stdout(tmp_path, monkeypatch):
    evaluator_root = tmp_path / "evaluation"
    evaluator_root.mkdir()
    (evaluator_root / "evaluate.py").write_text("# stand-in\n", encoding="utf-8")
    gold_path = tmp_path / "gold.jsonl"
    pred_path = tmp_path / "predictions.jsonl"
    gold_path.write_text("", encoding="utf-8")
    pred_path.write_text("", encoding="utf-8")

    captured: dict[str, object] = {}

    class _FakeCompleted:
        def __init__(self, stdout: str) -> None:
            self.returncode = 0
            self.stdout = stdout
            self.stderr = ""

    def _fake_run(command, *, cwd, capture_output, text, encoding, check):
        captured["command"] = command
        captured["cwd"] = cwd
        return _FakeCompleted(_fake_stdout(_FIXTURE_ROWS))

    monkeypatch.setattr(soe.subprocess, "run", _fake_run)

    result = run_official_evaluate(gold_path, pred_path, evaluator_root=evaluator_root)
    assert isinstance(result, OfficialSluResult)
    assert captured["cwd"] == str(evaluator_root)
    assert captured["command"][:2] == [soe.official_evaluator_python(), str(evaluator_root / "evaluate.py")]
    assert "--table-layout" in captured["command"]
    assert "csv" in captured["command"]
    assert result.scenario_accuracy == pytest.approx(0.9)
    assert result.action_accuracy == pytest.approx(0.85)
    assert result.intent_accuracy == pytest.approx(0.8)
    assert result.slu_f1 == pytest.approx(0.6813725490196079)
    assert result.span_f1 == pytest.approx(0.6470588235294118)
    as_dict = result.as_dict()
    assert as_dict["command"] == captured["command"]
    assert as_dict["raw"]["slu_f1"]["official_label"] == "Slu f1"


def test_run_official_evaluate_fails_closed_on_nonzero_exit(tmp_path, monkeypatch):
    evaluator_root = tmp_path / "evaluation"
    evaluator_root.mkdir()
    (evaluator_root / "evaluate.py").write_text("# stand-in\n", encoding="utf-8")

    class _FakeCompleted:
        returncode = 1
        stdout = ""
        stderr = "boom"

    monkeypatch.setattr(soe.subprocess, "run", lambda *a, **k: _FakeCompleted())
    with pytest.raises(SlurpOfficialEvalError, match="exited 1"):
        run_official_evaluate(tmp_path / "g.jsonl", tmp_path / "p.jsonl", evaluator_root=evaluator_root)


def test_run_official_evaluate_fails_closed_on_missing_script(tmp_path):
    evaluator_root = tmp_path / "evaluation"
    evaluator_root.mkdir()
    with pytest.raises(SlurpOfficialEvalError, match="evaluate.py missing"):
        run_official_evaluate(tmp_path / "g.jsonl", tmp_path / "p.jsonl", evaluator_root=evaluator_root)


# ---------------------------------------------------------------------------
# score_slurp_outputs_official: identity_check logic + heldout refusal --
# both official_evaluator_root and run_official_evaluate are monkeypatched
# out so this never touches the real data root or a subprocess.
# ---------------------------------------------------------------------------


def _write_outputs(tmp_path: Path, rows: list[dict]) -> Path:
    path = tmp_path / "x.outputs.jsonl"
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return path


_SYNTHETIC_GOLD = [
    _gold("slurp:devel:000001:rec-a", "alarm", "set", (SlotEntity("time", "seven am"),)),
    _gold("slurp:devel:000002:rec-b", "email", "send", (SlotEntity("person", "john"),)),
    _gold("slurp:devel:000003:rec-c", "music", "play", ()),
]


def _install_fake_split(monkeypatch, records=_SYNTHETIC_GOLD):
    calls: list[tuple] = []

    def _fake_load_slurp_split(lock, root, split_id, *, allow_heldout=False, allow_synthetic=False):
        calls.append((split_id, allow_heldout))
        return list(records)

    monkeypatch.setattr(soe, "load_slurp_split", _fake_load_slurp_split)
    return calls


def _install_fake_official(monkeypatch, official_result: OfficialSluResult):
    monkeypatch.setattr(soe, "official_evaluator_root", lambda root: Path("unused"))
    monkeypatch.setattr(
        soe,
        "run_official_evaluate",
        lambda gold_path, pred_path, *, evaluator_root, python_executable=None, average="micro": official_result,
    )


def _official_result(slu_f1: float, span_f1: float) -> OfficialSluResult:
    raw = {
        key: {"official_label": key, "precision": 0.0, "recall": 0.0, "f_measure": 0.0, "tp": 0.0, "fp": 0.0, "fn": 0.0}
        for key in (
            "scenario",
            "action",
            "intent",
            "entities",
            "entities_distance_word",
            "entities_distance_char",
            "slu_f1",
        )
    }
    return OfficialSluResult(
        scenario_accuracy=1.0,
        action_accuracy=1.0,
        intent_accuracy=1.0,
        slu_f1=slu_f1,
        span_f1=span_f1,
        raw=raw,
        stdout="fake",
        command=("python", "evaluate.py"),
    )


def test_score_slurp_outputs_official_identity_check_passes_on_perfect_predictions(tmp_path, monkeypatch):
    _install_fake_split(monkeypatch)
    outputs = _write_outputs(
        tmp_path,
        [
            {"sample_id": r.sample_id, "text": json.dumps({
                "scenario": r.scenario, "action": r.action,
                "entities": [{"type": e.type, "filler": e.filler} for e in r.entities],
            })}
            for r in _SYNTHETIC_GOLD
        ],
    )
    # A perfect prediction against these 3 gold records: slot_f1_exact and
    # slu_f1 are both exactly 1.0 (2 correct entities, 0 FP, 0 FN across word
    # and char distance too).
    _install_fake_official(monkeypatch, _official_result(slu_f1=1.0, span_f1=1.0))

    result = score_slurp_outputs_official(outputs, {}, tmp_path)
    assert result["aggregate"]["port_micro"]["slu_f1"] == pytest.approx(1.0)
    assert result["aggregate"]["port_micro"]["span_f1"] == pytest.approx(1.0)
    assert result["aggregate"]["port_micro"]["scenario_accuracy"] == pytest.approx(1.0)
    assert result["aggregate"]["port_micro"]["intent_accuracy"] == pytest.approx(1.0)
    assert result["aggregate"]["identity_check"]["passed"] is True
    assert result["aggregate"]["identity_check"]["slu_f1_abs_diff"] == pytest.approx(0.0)
    assert result["aggregate"]["identity_check"]["span_f1_abs_diff"] == pytest.approx(0.0)
    assert result["aggregate"]["scorer_version"] == SLURP_OFFICIAL_SCORER_VERSION
    assert result["aggregate"]["evaluator_commit"] == SLURP_OFFICIAL_COMMIT
    assert len(result["per_sample"]) == 3


def test_score_slurp_outputs_official_identity_check_fails_on_disagreement(tmp_path, monkeypatch):
    _install_fake_split(monkeypatch)
    outputs = _write_outputs(
        tmp_path,
        [
            {"sample_id": r.sample_id, "text": json.dumps({
                "scenario": r.scenario, "action": r.action,
                "entities": [{"type": e.type, "filler": e.filler} for e in r.entities],
            })}
            for r in _SYNTHETIC_GOLD
        ],
    )
    # Deliberately wrong "official" numbers -> the identity check must fail.
    _install_fake_official(monkeypatch, _official_result(slu_f1=0.5, span_f1=0.5))

    result = score_slurp_outputs_official(outputs, {}, tmp_path)
    assert result["aggregate"]["identity_check"]["passed"] is False
    assert result["aggregate"]["identity_check"]["slu_f1_abs_diff"] == pytest.approx(0.5)
    assert result["aggregate"]["identity_check"]["span_f1_abs_diff"] == pytest.approx(0.5)


def test_score_slurp_outputs_official_refuses_split_id_test_without_allow_heldout(tmp_path):
    outputs = _write_outputs(tmp_path, [{"sample_id": "slurp:devel:000001:rec-a", "text": "{}"}])
    with pytest.raises(Exception, match="HELD OUT"):
        score_slurp_outputs_official(outputs, {}, tmp_path, split_id="test")


def test_score_slurp_outputs_official_refuses_a_test_named_row_regardless_of_split_id(tmp_path):
    outputs = _write_outputs(tmp_path, [{"sample_id": "slurp:test:000001:rec-a", "text": "{}"}])
    with pytest.raises(SlurpOfficialEvalError, match="HELD OUT"):
        score_slurp_outputs_official(outputs, {}, tmp_path, split_id="devel")


def test_score_slurp_outputs_official_refuses_empty_outputs(tmp_path):
    outputs = tmp_path / "x.outputs.jsonl"
    outputs.write_text("", encoding="utf-8")
    with pytest.raises(SlurpOfficialEvalError, match="empty"):
        score_slurp_outputs_official(outputs, {}, tmp_path)


def test_score_slurp_outputs_official_refuses_unknown_sample_id(tmp_path, monkeypatch):
    _install_fake_split(monkeypatch)
    outputs = _write_outputs(tmp_path, [{"sample_id": "slurp:devel:999999:rec-z", "text": "{}"}])
    with pytest.raises(SlurpOfficialEvalError, match="not part of SLURP split"):
        score_slurp_outputs_official(outputs, {}, tmp_path)


# ---------------------------------------------------------------------------
# Opt-in integration test: builds a 5-record synthetic gold/pred pair and
# runs the REAL, unmodified official evaluate.py subprocess against them --
# the one test in this file that touches the real data root / a subprocess.
# ---------------------------------------------------------------------------


def _data_root_from_env() -> Path | None:
    raw = os.environ.get("SPEECHRL_DATA_DIR")
    if not raw:
        return None
    path = Path(raw)
    return path if path.is_dir() else None


@pytest.mark.skipif(
    os.environ.get("SAEA_SLURP_OFFICIAL_EVAL") != "1" or _data_root_from_env() is None,
    reason=(
        "opt-in: set SAEA_SLURP_OFFICIAL_EVAL=1 with SPEECHRL_DATA_DIR pointing at the "
        "governed data root (a repos/slurp checkout) to run the REAL official evaluate.py"
    ),
)
def test_official_evaluate_matches_port_on_a_synthetic_five_record_pair(tmp_path):
    """KNOWN ENVIRONMENT BLOCKER (recorded 2026-09-03, out of this slice's
    scope to fix -- no pip install / no venv changes): the pinned official
    evaluator's ``requirements.txt`` names ``jiwer==2.0.0``, whose
    ``wer(truth=..., hypothesis=...)`` keyword names ``metrics/distance.py``
    calls by name; the shared venv's installed ``jiwer`` is 4.0.0, which
    renamed that parameter to ``reference`` and now raises
    ``TypeError: wer() got an unexpected keyword argument 'truth'`` the
    moment ANY gold/prediction pair shares an entity type (exact match or
    not -- ``SpanDistanceFMeasure.__call__`` always calls the distance
    function for a type match, unconditionally). This is a genuine,
    pre-existing third-party version conflict in the shared venv, not a
    defect in this module: an entity-free record set runs this exact
    pipeline (``write_official_inputs``/``official_evaluator_root``/
    ``run_official_evaluate``) to completion against the REAL subprocess
    with exact scenario/action/intent-accuracy identity (verified ad hoc,
    delivery report). This test is intentionally left AS DESIGNED --
    exercising the distance-metric path is the whole point of an identity
    check against the official SLU-F1 -- so it currently fails here until
    the shared venv is deliberately re-pinned or a compat shim is reviewed
    and approved; see the delivery report for the full trace.
    """

    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import score_slu

    data_root = _data_root_from_env()
    assert data_root is not None

    gold = [
        _gold("slurp:devel:000001:rec-1", "alarm", "set", (SlotEntity("time", "seven am"),)),
        _gold("slurp:devel:000002:rec-2", "email", "send", (SlotEntity("person", "john"),)),
        _gold(
            "slurp:devel:000003:rec-3",
            "weather",
            "query",
            (SlotEntity("place", "boston"), SlotEntity("date", "tomorrow")),
        ),
        _gold("slurp:devel:000004:rec-4", "music", "play", ()),
        _gold(
            "slurp:devel:000005:rec-5",
            "iot",
            "hue_lighton",
            (SlotEntity("device_type", "kitchen light"),),
        ),
    ]
    # Deliberately mixed correctness: #1 perfect; #2 wrong action + a typo'd
    # filler (word/char-distance credit, exact mismatch); #3 one correct +
    # one wrong-filler entity (distance credit); #4 a spurious extra entity
    # (pure FP); #5 an unparseable response (pure FN across the board).
    predictions = [
        PredictedSlurpSample(
            "slurp:devel:000001:rec-1", "alarm", "set", (SlotEntity("time", "seven am"),)
        ),
        PredictedSlurpSample(
            "slurp:devel:000002:rec-2", "email", "query", (SlotEntity("person", "jon"),)
        ),
        PredictedSlurpSample(
            "slurp:devel:000003:rec-3",
            "weather",
            "query",
            (SlotEntity("place", "boston"), SlotEntity("date", "today")),
        ),
        PredictedSlurpSample(
            "slurp:devel:000004:rec-4", "music", "play", (SlotEntity("artist", "adele"),)
        ),
        PredictedSlurpSample("slurp:devel:000005:rec-5", None, None, ()),
    ]

    gold_path, pred_path = write_official_inputs(gold, predictions, tmp_path)
    evaluator_root = official_evaluator_root(data_root)
    official = run_official_evaluate(gold_path, pred_path, evaluator_root=evaluator_root)

    sample_scores = [
        score_slu(
            gold_scenario=g.scenario,
            gold_action=g.action,
            gold_entities=g.entities,
            predicted_scenario=p.scenario,
            predicted_action=p.action,
            predicted_entities=list(p.entities),
        )
        for g, p in zip(gold, predictions)
    ]
    aggregate_score = soe._aggregate_slu_score(sample_scores)
    _, _, port_slu_f1 = aggregate_score.slu_f1
    _, _, port_span_f1 = aggregate_score.slot_f1_exact

    slu_f1_diff = abs(port_slu_f1 - official.slu_f1)
    span_f1_diff = abs(port_span_f1 - official.span_f1)

    print("official raw:", json.dumps(dict(official.raw), indent=2, sort_keys=True))
    print(f"port_slu_f1={port_slu_f1!r} official.slu_f1={official.slu_f1!r} diff={slu_f1_diff!r}")
    print(
        f"port_span_f1={port_span_f1!r} official.span_f1={official.span_f1!r} "
        f"diff={span_f1_diff!r}"
    )

    assert slu_f1_diff < 1e-6, (
        f"port slu_f1={port_slu_f1} vs official slu_f1={official.slu_f1} (diff={slu_f1_diff})"
    )
    assert span_f1_diff < 1e-6, (
        f"port span_f1={port_span_f1} vs official span_f1={official.span_f1} "
        f"(diff={span_f1_diff})"
    )
