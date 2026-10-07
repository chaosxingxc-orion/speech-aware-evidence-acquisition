"""Capacity and rehearsal must refuse real stale seeds before any contact."""

import hashlib
import json
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.analysis import native_graph_capacity as capacity
from speech_aware_evidence_acquisition.analysis import (
    native_graph_rehearsal as rehearsal,
)
from speech_aware_evidence_acquisition.core.preparation import (
    PreparationError,
    canonical_bytes,
)
from speech_aware_evidence_acquisition.rails import phase_supply
from test_prepared_phase_supply import setup_runtime


def prepared_graph(tmp_path, monkeypatch, fault):
    runtime, binding, _program = setup_runtime(tmp_path)
    runtime._composed.values["phase_tools"] = {
        "slots": {"allowed_tools": ["saea-tool-knowledge-target-lookup-v1"]}
    }
    packets = binding["speech_packet_bindings"]
    packets.update({sid: dict(packets["s1"]) for sid in ("s2", "s3", "s4")})
    monkeypatch.setattr(
        phase_supply,
        "build_bootstrap_selection",
        lambda *a, **kw: ({}, {sid: ("v1",) for sid in packets}),
    )
    path = tmp_path / "seed.json"
    runtime.prepare_phase_supply(path)
    if fault in {"runtime", "selection"}:
        document = json.loads(path.read_bytes())
        if fault == "runtime":
            document["inputs"]["sources"]["implementation"]["runtime"] = "0" * 64
        else:
            document["output"]["values"]["slots"]["s1"] = ["not-released"]
            from speech_aware_evidence_acquisition.core.preparation import digest

            document["output_sha256"] = digest(document["output"])
        path.write_bytes(canonical_bytes(document))
    pin = {
        "relpath": "seed.json",
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }
    runtime._composed.values["prepared_phase_supply"] = pin
    if fault == "hash":
        pin["sha256"] = "0" * 64
    if fault == "missing":
        path.unlink()
    runtime._client = runtime._plan = None
    context = {
        "values": runtime._composed.values,
        "sample_ids": list(packets),
        "execution_plan": SimpleNamespace(split_role="discovery"),
    }
    runtime.preparation_context = lambda: context
    return runtime, path


@pytest.mark.parametrize("entry", ["capacity", "rehearsal"])
@pytest.mark.parametrize("fault", ["runtime", "selection", "hash", "missing"])
def test_real_pinned_graph_refused_before_dry_run_or_session(
    tmp_path, monkeypatch, entry, fault
):
    runtime, path = prepared_graph(tmp_path, monkeypatch, fault)
    before = path.read_bytes() if path.exists() else None
    import speech_aware_evidence_acquisition.analysis.native_episode_dry_run as dry
    import speech_aware_evidence_acquisition.core.session as session

    monkeypatch.setattr(
        dry, "compose_dry_run", lambda *a, **kw: pytest.fail("dry-run fallback reached")
    )
    monkeypatch.setattr(
        session, "attach_session", lambda *a, **kw: pytest.fail("session opened")
    )
    runtime.authorize_preparation_contacts = lambda **kw: pytest.fail(
        "contacts authorized"
    )
    with pytest.raises(PreparationError, match="prepared_phase_supply") as error:
        if entry == "capacity":
            capacity.fit_native_graph(
                runtime,
                tmp_path / "fit.json",
                policy=None,
                graph_factory=lambda: runtime,
            )
        else:
            rehearsal.rehearse_native_graph(
                runtime,
                session_path=tmp_path / "session.json",
                respond=lambda _: pytest.fail("response requested"),
                output=tmp_path / "wire-check" / "proof",
            )
    if fault == "runtime":
        assert "sources.implementation.runtime" in str(error.value)
    assert (path.read_bytes() if path.exists() else None) == before
    assert not (tmp_path / "fit.json").exists()
    assert not (tmp_path / "wire-check").exists()


@pytest.mark.parametrize("entry", ["capacity", "rehearsal"])
def test_real_current_pin_passes_before_the_next_stage(tmp_path, monkeypatch, entry):
    runtime, _path = prepared_graph(tmp_path, monkeypatch, None)
    import speech_aware_evidence_acquisition.analysis.native_episode_dry_run as dry
    import speech_aware_evidence_acquisition.core.session as session

    class NextStage(Exception):
        pass

    def reached(*args, **kwargs):
        assert runtime.verify_prepared_artifacts()[0]["seed_ok"] is True
        raise NextStage

    monkeypatch.setattr(dry, "compose_dry_run", reached)
    monkeypatch.setattr(session, "attach_session", reached)
    runtime._runtime_root = tmp_path
    context = runtime.preparation_context()
    context["runtime_receipt"] = {}
    with pytest.raises(NextStage):
        if entry == "capacity":
            capacity.fit_native_graph(
                runtime,
                tmp_path / "fit.json",
                policy=None,
                graph_factory=lambda: runtime,
            )
        else:
            rehearsal.rehearse_native_graph(
                runtime,
                session_path=tmp_path / "session.json",
                respond=lambda _: pytest.fail("response requested"),
                output=tmp_path / "wire-check" / "proof",
            )


@pytest.mark.parametrize("pinned", [False, True])
def test_current_artifact_or_historical_unpinned_graph_remains_admitted(
    tmp_path, monkeypatch, pinned
):
    runtime, _path = prepared_graph(tmp_path, monkeypatch, None)
    if not pinned:
        del runtime._composed.values["prepared_phase_supply"]
    rehearsal.require_prepared_graph_artifacts(runtime)
    reports = runtime.verify_prepared_artifacts()
    assert reports == () if not pinned else reports[0]["seed_ok"] is True
