from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.analysis import (
    e21_selective_loop_windows as subject,
)
from speech_aware_evidence_acquisition.core.bundle.artifacts import VerifiedBundle
from speech_aware_evidence_acquisition.core.bundle.delivery_replay import canonical
from speech_aware_evidence_acquisition.core.delivery import normalize_terminal_response
from speech_aware_evidence_acquisition.core.predecessor_snapshot import (
    PredecessorWindow,
)
from speech_aware_evidence_acquisition.core.repair_alignment import accept_entity_repair
from speech_aware_evidence_acquisition.reproduction.obs_loop import (
    OBS_RELISTEN_PLAN_SCHEMA,
    PlannedUnit,
)
from speech_aware_evidence_acquisition.reproduction.repair_loop import RepairWindowHook

PASS1 = (
    "Thank you and good morning everyone welcome to the fourth quarter earnings "
    "call I would like to turn the call over to our President and Chief Executive "
    "Officer Brett Ponton who will walk you through the results for the quarter"
)
RETURNED = PASS1.replace("Ponton", "Pontone")
PARENT = f"prefix {PASS1} suffix"
DELIVERED_PARENT = f"prefix {RETURNED} suffix"
FINAL = f"a {DELIVERED_PARENT} e"


def _window(index, text):
    return PredecessorWindow(
        f"s#w{index:04d}",
        "s",
        index,
        f"old-{index}",
        (index - 1) * 10,
        index * 10,
        10,
        False,
        text,
        sha256(text.encode()).hexdigest(),
        None,
        None,
    )


def _unit():
    return PlannedUnit("s#u0001", 1, 11.0, 19.0, None, "recut", 2, 1, 41)


def _predecessors():
    return (_window(1, "a"), _window(2, PARENT), _window(3, "e"))


def _obs(*, transcript=RETURNED, saturated=False, skipped=False, **overrides):
    unit = _unit()
    hook = RepairWindowHook(
        sample_id="s",
        predecessors=_predecessors(),
        frame="x",
        rule=lambda old, new: accept_entity_repair(
            old, new, max_substituted_fraction=1.0
        ),
        units=(unit,),
    )
    delivered, fields = hook.accept(
        iteration=0,
        record=SimpleNamespace(
            start_seconds=round(unit.cut_start_seconds * 16000) / 16000,
            end_seconds=round(unit.cut_end_seconds * 16000) / 16000,
        ),
        transcript=normalize_terminal_response(
            transcript if not skipped else None,
            saturated=saturated,
            skipped=skipped,
        ),
        saturated=saturated,
        skipped=skipped,
    )
    value = {
        **fields,
        "obs_iteration": 0,
        "obs_retry_of": None,
        "obs_boundary_mode": "fixed",
        "obs_unit_id": unit.unit_id,
        "obs_relisten_parent_window_index": unit.parent_window_index,
        "obs_window_start_seconds": round(unit.cut_start_seconds * 16000) / 16000,
        "obs_window_end_seconds": round(unit.cut_end_seconds * 16000) / 16000,
        "obs_skipped": skipped,
        "obs_saturated": saturated,
        "obs_delivered_text": delivered,
    }
    value.update(overrides)
    return value


def _bundle(obs, response=RETURNED, request_id="root-i0000"):
    payload = {
        "request_id": request_id,
        "sample_id": "s",
        "audio_seconds": obs["obs_window_end_seconds"] - obs["obs_window_start_seconds"],
        "sample_rate_hz": 16000,
        "decoding_params": {"max_tokens": 8},
    }
    records = {
        f"{request_id}/request": {
            "payload": payload,
            "payload_sha256": sha256(canonical(payload)).hexdigest(),
        },
        f"{request_id}/obs": obs,
        "root/request": {
            "stitch": True,
            "stitched_request_ids": [] if obs["obs_skipped"] else [request_id],
        },
    }
    if response is not None:
        records[f"{request_id}/response"] = {
            "text": response,
            "response_text_sha256": sha256(response.encode()).hexdigest(),
            "usage": {"completion_tokens": 8 if obs["obs_saturated"] else 1},
        }
    return VerifiedBundle(
        manifest_path=Path("/synthetic/manifest.json"),
        manifest={"schema": "saea-run-manifest-v1"},
        outputs_path=None,
        outputs_rows=(
            {"sample_id": "s", "request_id": "root", "text": obs["obs_delivered_text"]},
        ),
        trace_records=records,
        split_ids=frozenset({"s"}),
        attempt_state="SEALED",
    )


def _patch(monkeypatch):
    windows = _predecessors()
    snapshot = SimpleNamespace(for_sample=lambda sample: windows, run_id="predecessor")
    unit = _unit()
    plan = SimpleNamespace(
        schema=OBS_RELISTEN_PLAN_SCHEMA,
        units_by_sample={"s": (unit,)},
        units_for=lambda sample, duration: (unit,),
    )
    monkeypatch.setattr(
        subject,
        "_values",
        lambda bundle, root: {
            "obs_unit_plan": "p",
            "obs_unit_plan_sha256": "h",
            "obs_buffer_seconds": 90,
            "response_postprocessor": "p",
            "response_postprocessor_params": {},
            "decoding_params": {"max_tokens": 8},
        },
    )
    monkeypatch.setattr(subject, "binding_from_values", lambda values: ("x", "d"))
    monkeypatch.setattr(
        subject, "load_predecessor_binding", lambda *args, **kwargs: snapshot
    )
    monkeypatch.setattr(subject, "_load_unit_plan", lambda *args, **kwargs: plan)
    monkeypatch.setattr(subject, "REPAIR_FRAMES", {"e21-entity-repair-frame-v1": "x"})
    monkeypatch.setattr(
        subject,
        "RESPONSE_POSTPROCESSORS",
        SimpleNamespace(
            resolve=lambda name: (
                lambda **kwargs: (
                    lambda old, new: accept_entity_repair(
                        old, new, max_substituted_fraction=1.0
                    )
                )
            )
        ),
    )


def _verified(monkeypatch, tmp_path, **kwargs):
    _patch(monkeypatch)
    return subject.verified_selective_loop_windows(
        _bundle(**kwargs), repo_root=tmp_path, data_root=tmp_path
    )


def test_reconstructs_selected_substitution_and_all_unselected_windows(
    monkeypatch, tmp_path
):
    spans = _verified(
        monkeypatch,
        tmp_path,
        obs=_obs(obs_retry_of="root-i0000"),
        request_id="root-i0000-r1",
    )

    assert [span.text for span in spans["s"]] == ["a", DELIVERED_PARENT, "e"]
    assert spans["s"][1].request_id == "root-i0000-r1"
    assert spans["s"][1].saturated is False
    assert spans["s"][0].request_id == "predecessor/old-1"
    assert spans["s"][2].request_id == "predecessor/old-3"


@pytest.mark.parametrize(
    "field,value,match",
    [
        ("obs_repair_predecessor_text_sha256", "0" * 64, "predecessor"),
        ("obs_delivered_text", "tampered", "shared repair hook"),
        ("obs_relisten_window_text", "tampered", "shared repair hook"),
        ("obs_unit_id", "wrong-unit", "binding"),
        ("obs_relisten_parent_window_index", 1, "binding"),
        ("obs_relisten_predecessor_word_start", 2, "binding"),
        ("obs_relisten_predecessor_word_end", 42, "binding"),
        ("obs_window_start_seconds", 10.0, "start"),
    ],
)
def test_refuses_trace_or_plan_binding_drift(
    monkeypatch, tmp_path, field, value, match
):
    with pytest.raises(subject.SelectiveLoopWindowsError, match=match):
        _verified(monkeypatch, tmp_path, obs=_obs(**{field: value}))


@pytest.mark.parametrize("skipped,saturated", [(False, True), (True, False)])
def test_saturation_or_skip_falls_back_to_predecessor(
    monkeypatch, tmp_path, skipped, saturated
):
    obs = _obs(saturated=saturated, skipped=skipped)
    spans = _verified(monkeypatch, tmp_path, obs=obs, response=None if skipped else "")

    assert [span.text for span in spans["s"]] == ["a", PARENT, "e"]
    assert spans["s"][1].request_id == "root-i0000"
    assert spans["s"][1].saturated is saturated


def test_refuses_terminal_response_usage_inconsistent_with_saturation(
    monkeypatch, tmp_path
):
    _patch(monkeypatch)
    bundle = _bundle(_obs(saturated=True), response="")
    bundle.trace_records["root-i0000/response"]["usage"]["completion_tokens"] = 1

    with pytest.raises(subject.SelectiveLoopWindowsError, match="saturation"):
        subject.verified_selective_loop_windows(
            bundle, repo_root=tmp_path, data_root=tmp_path
        )


def test_refuses_tampered_unselected_whole_output(monkeypatch, tmp_path):
    _patch(monkeypatch)
    bundle = _bundle(_obs())
    bundle = VerifiedBundle(
        **{
            **bundle.__dict__,
            "outputs_rows": (
                {
                    "sample_id": "s",
                    "request_id": "root",
                    "text": f"X {DELIVERED_PARENT} e",
                },
            ),
        }
    )

    with pytest.raises(subject.SelectiveLoopWindowsError, match="rebuild outputs"):
        subject.verified_selective_loop_windows(
            bundle, repo_root=tmp_path, data_root=tmp_path
        )


def test_refuses_stitch_order_tamper(monkeypatch, tmp_path):
    _patch(monkeypatch)
    bundle = _bundle(_obs())
    bundle.trace_records["root/request"]["stitched_request_ids"] = []

    with pytest.raises(subject.SelectiveLoopWindowsError, match="stitch order"):
        subject.verified_selective_loop_windows(
            bundle, repo_root=tmp_path, data_root=tmp_path
        )


def test_refuses_extra_terminal_obs(monkeypatch, tmp_path):
    _patch(monkeypatch)
    bundle = _bundle(_obs())
    retry_payload = {
        "request_id": "root-i0000-r1",
        "sample_id": "s",
        "audio_seconds": 8.0,
        "decoding_params": {"max_tokens": 8},
    }
    bundle.trace_records["root-i0000-r1/obs"] = _obs(obs_retry_of="root-i0000")
    bundle.trace_records["root-i0000-r1/request"] = {
        "payload": retry_payload,
        "payload_sha256": sha256(canonical(retry_payload)).hexdigest(),
    }
    bundle.trace_records["root-i0000-r1/response"] = {
        "text": RETURNED,
        "response_text_sha256": sha256(RETURNED.encode()).hexdigest(),
        "usage": {"completion_tokens": 1},
    }

    with pytest.raises(subject.SelectiveLoopWindowsError):
        subject.verified_selective_loop_windows(
            bundle, repo_root=tmp_path, data_root=tmp_path
        )


def test_refuses_retained_checkout_commit_mismatch(monkeypatch, tmp_path):
    bundle = _bundle(_obs())
    bundle = VerifiedBundle(
        **{
            **bundle.__dict__,
            "manifest": {
                "study_commit": "a" * 40,
                "config": {
                    "fragments": {
                        "model": "m",
                        "dataset": "d",
                        "baseline": "b",
                        "experiment": "e",
                    },
                    "config_hash": "expected",
                },
            },
        }
    )
    monkeypatch.setattr(
        subject.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(stdout="b" * 40 + "\n"),
    )

    with pytest.raises(subject.SelectiveLoopWindowsError, match="study commit"):
        subject._values(bundle, tmp_path)


def test_refuses_retained_config_hash_drift(monkeypatch, tmp_path):
    bundle = _bundle(_obs())
    bundle = VerifiedBundle(
        **{
            **bundle.__dict__,
            "manifest": {
                "study_commit": "a" * 40,
                "config": {
                    "fragments": {
                        "model": "m",
                        "dataset": "d",
                        "baseline": "b",
                        "experiment": "e",
                    },
                    "config_hash": "expected",
                },
            },
        }
    )
    monkeypatch.setattr(
        subject.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(stdout="a" * 40 + "\n"),
    )
    monkeypatch.setattr(
        subject,
        "compose",
        lambda *args, **kwargs: SimpleNamespace(config_hash="changed"),
    )

    with pytest.raises(subject.SelectiveLoopWindowsError, match="retained config"):
        subject._values(bundle, tmp_path)


@pytest.mark.parametrize("sample_shift", [0, 1])
def test_pcm_frame_rounding_accepts_exact_cut_and_refuses_one_frame_drift(
    monkeypatch, tmp_path, sample_shift
):
    from dataclasses import replace
    planned = replace(_unit(), start_seconds=11.00004, end_seconds=19.00002)
    monkeypatch.setattr(__import__(__name__, fromlist=["_unit"]), "_unit", lambda: planned)
    _patch(monkeypatch)
    obs = _obs()
    obs["obs_window_start_seconds"] += sample_shift / 16000
    bundle = _bundle(obs)
    if sample_shift:
        with pytest.raises(subject.SelectiveLoopWindowsError, match="start"):
            subject.verified_selective_loop_windows(
                bundle, repo_root=tmp_path, data_root=tmp_path
            )
    else:
        spans = subject.verified_selective_loop_windows(
            bundle, repo_root=tmp_path, data_root=tmp_path
        )
        assert spans["s"][1].text == DELIVERED_PARENT
