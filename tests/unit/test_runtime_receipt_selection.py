"""Second-pinned-model plumbing: the receipt PATH a session/gate pair binds
to is selectable via the model config fragment's optional ``runtime_receipt``
key (``core.config.runtime_receipt_relpath``/``resolve_runtime_receipt_path``),
defaulting to today's committed ``docs/receipts/runtime.json`` when the key
is absent. Covers the three call sites named by the plumbing change: the
``contracts.FrozenCoreGate.for_study_repo`` default, ``saea-driver smoke``,
and ``saea-driver run`` (``core.session.attach_session``'s own receipt load).

Loading a DIFFERENT model's receipt file does not, by itself, authorize a
gate open against it: ``contracts.FrozenCoreGate._validate_runtime`` asserts
the receipt's ``model_lock_key`` equals the gate's own ``expected_model_
lock_key`` (default: the frozen ``contracts.MODEL_LOCK_KEY``; a caller may
now widen it explicitly -- see ``tests/contract/
test_model_lock_key_binding.py`` for that identity check, both directions,
and ``test_cli_run_passes_the_models_declared_model_lock_key_to_the_gate``
below for proof that ``saea-driver run`` derives it from the SAME composed
config that chose the receipt path, never independently). This module only
proves WHICH FILE gets read/refused.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.contracts import FrozenCoreGate
from speech_aware_evidence_acquisition.core.session import SessionError, load_runtime_receipt


def test_for_study_repo_default_runtime_receipt_path_unchanged(tmp_path):
    gate = FrozenCoreGate.for_study_repo(tmp_path, tmp_path, tmp_path)
    assert gate.runtime_receipt == tmp_path / "docs" / "receipts" / "runtime.json"


def test_for_study_repo_accepts_an_explicit_runtime_receipt_relpath(tmp_path):
    gate = FrozenCoreGate.for_study_repo(
        tmp_path, tmp_path, tmp_path, runtime_receipt_relpath="receipts/runtime-q4km.json"
    )
    assert gate.runtime_receipt == tmp_path / "docs" / "receipts" / "runtime-q4km.json"
    # Every other field is untouched by the new keyword-only parameter.
    default_gate = FrozenCoreGate.for_study_repo(tmp_path, tmp_path, tmp_path)
    assert gate.e0_receipt == default_gate.e0_receipt
    assert gate.data_root == default_gate.data_root
    assert gate.runtime_root == default_gate.runtime_root
    assert gate.exposure_ledger == default_gate.exposure_ledger
    assert gate.source_root == default_gate.source_root


def test_for_study_repo_accepts_an_optional_d1_media_supplement(tmp_path):
    supplement = (
        tmp_path
        / "docs"
        / "receipts"
        / "artifacts"
        / "d1-speech-native-train90.json"
    )
    gate = FrozenCoreGate.for_study_repo(
        tmp_path,
        tmp_path,
        tmp_path,
        d1_media_supplement_relpath=(
            "receipts/artifacts/d1-speech-native-train90.json"
        ),
        d1_media_supplement_sha256="a" * 64,
    )
    assert gate.d1_media_supplement == supplement
    assert gate.d1_media_supplement_sha256 == "a" * 64
    assert FrozenCoreGate.for_study_repo(
        tmp_path, tmp_path, tmp_path
    ).d1_media_supplement is None


def test_missing_default_runtime_receipt_fails_closed(tmp_path):
    path = tmp_path / "docs" / "receipts" / "runtime.json"
    with pytest.raises(SessionError, match="runtime.json"):
        load_runtime_receipt(path)


def test_missing_custom_runtime_receipt_fails_closed_naming_the_custom_file(tmp_path):
    path = tmp_path / "docs" / "receipts" / "runtime-q4km.json"
    with pytest.raises(SessionError, match="runtime-q4km.json"):
        load_runtime_receipt(path)


def test_unreadable_json_runtime_receipt_fails_closed(tmp_path):
    path = tmp_path / "docs" / "receipts" / "runtime-q4km.json"
    path.parent.mkdir(parents=True)
    path.write_text("not valid json {", encoding="utf-8")
    with pytest.raises(SessionError, match="runtime-q4km.json"):
        load_runtime_receipt(path)


# ---------------------------------------------------------------------------
# End-to-end: ``saea-driver run`` (core/driver/cli.py::_cli_run) reads the
# composed model fragment's own runtime_receipt key -- exercised the same
# way ``tests/unit/test_driver_smoke.py`` exercises the ``smoke`` subcommand
# non-dry-run path, but for ``run`` (the "session start" call site).
# ---------------------------------------------------------------------------


def _write_model_fragment(configs: Path, name: str, extra: dict | None = None) -> None:
    body = {
        "model_lock_key": "qwen3-omni-30b-a3b-instruct-gguf",
        "transport": "llama-server",
        "base_url": "http://127.0.0.1:8080",
        "timeout_seconds": 300.0,
        "decoding_params": {"temperature": 0, "seed": 20260803},
    }
    body.update(extra or {})
    (configs / "model" / f"{name}.json").write_text(json.dumps(body), encoding="utf-8")


def _write_minimal_fragments(repo_root: Path) -> None:
    configs = repo_root / "configs"
    for kind in ("model", "dataset", "baseline", "experiment"):
        (configs / kind).mkdir(parents=True)
    _write_model_fragment(
        configs, "custom-receipt", {"runtime_receipt": "receipts/runtime-cli-run.json"}
    )
    _write_model_fragment(configs, "default-receipt")
    # A DIFFERENT declared model_lock_key than every other fragment in this
    # module (which all share "qwen3-omni-30b-a3b-instruct-gguf") -- the one
    # value that can distinguish "the gate learned this run's declared key
    # from the composed config" from "the gate silently kept using its own
    # default", since the two coincide for every other fragment here.
    _write_model_fragment(
        configs,
        "alt-model-key",
        {
            "model_lock_key": "qwen3-omni-30b-a3b-instruct-gguf-q4km",
            "runtime_receipt": "receipts/runtime-alt-key.json",
            "d1_media_supplement": "receipts/artifacts/d1-alt.json",
            "d1_media_supplement_sha256": "c" * 64,
        },
    )
    (configs / "dataset" / "d.json").write_text(
        json.dumps({"carrier_lock_key": "earnings21-original", "split_name": "discovery"}),
        encoding="utf-8",
    )
    (configs / "baseline" / "b.json").write_text(
        json.dumps({"arm": "bare-core"}), encoding="utf-8"
    )
    (configs / "experiment" / "e.json").write_text(
        json.dumps({"experiment_id": "SAEA-E-000-cli-run-test"}), encoding="utf-8"
    )


def _write_plan(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "run_id": "SAEA-E-000-cli-run-test",
                "execution_profile": "baseline-reproduction",
                "carrier_lock_key": "earnings21-original",
                "split_role": "dev",
                "split_identity_hash": "a" * 64,
                "planned_model_calls": 1,
                "planned_gpu_hours": 0.1,
                "planned_speech_audio_seconds": 60,
                "protocol_hash": "b" * 64,
            }
        ),
        encoding="utf-8",
    )


def _run_cli_run(monkeypatch, tmp_path, synthetic_world, *, model: str):
    import speech_aware_evidence_acquisition.core.driver.cli as cli_module
    from speech_aware_evidence_acquisition.core.driver import main as driver_main

    repo_root = tmp_path / "repo"
    _write_minimal_fragments(repo_root)
    monkeypatch.setattr(cli_module, "REPO_ROOT", repo_root)
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.data.lock.umbrella_lock_path",
        lambda *a, **k: synthetic_world.lock_path,
    )
    monkeypatch.setenv("SPEECHRL_DATA_DIR", str(synthetic_world.data_root))

    plan_path = tmp_path / "plan.json"
    _write_plan(plan_path)

    return driver_main(
        [
            "run",
            "--model", model,
            "--dataset", "d",
            "--baseline", "b",
            "--experiment", "e",
            "--plan", str(plan_path),
            "--run-dir", str(tmp_path / "run"),
            "--runtime-root", str(tmp_path / "runtime-root"),
            "--session-receipt", str(tmp_path / "session-receipt.json"),
        ]
    )


def test_cli_run_uses_the_models_custom_runtime_receipt_path(monkeypatch, tmp_path, synthetic_world):
    with pytest.raises(SessionError, match="runtime-cli-run.json"):
        _run_cli_run(monkeypatch, tmp_path, synthetic_world, model="custom-receipt")


def test_cli_run_falls_back_to_the_default_runtime_receipt_path(monkeypatch, tmp_path, synthetic_world):
    with pytest.raises(SessionError, match="runtime.json"):
        _run_cli_run(monkeypatch, tmp_path, synthetic_world, model="default-receipt")


# ---------------------------------------------------------------------------
# Identity-binding wiring: the SAME composed config that selects the receipt
# PATH must also select the gate's identity EXPECTATION -- proving
# ``_cli_run`` cannot silently keep asserting the frozen Q8_0 constant while
# resolving a genuinely different model's receipt file. See
# ``tests/contract/test_model_lock_key_binding.py`` for the gate's own
# refusal semantics once it has the wrong expectation; this proves only that
# ``_cli_run`` never lets the two drift apart in the first place.
# ---------------------------------------------------------------------------


def test_cli_run_passes_the_models_declared_model_lock_key_to_the_gate(
    monkeypatch, tmp_path, synthetic_world
):
    import speech_aware_evidence_acquisition.contracts as contracts_mod

    captured: dict = {}
    original = contracts_mod.FrozenCoreGate.for_study_repo.__func__

    def _spy(cls, *args, **kwargs):
        captured.update(kwargs)
        return original(cls, *args, **kwargs)

    monkeypatch.setattr(contracts_mod.FrozenCoreGate, "for_study_repo", classmethod(_spy))

    with pytest.raises(SessionError, match="runtime-alt-key.json"):
        _run_cli_run(monkeypatch, tmp_path, synthetic_world, model="alt-model-key")

    assert captured["expected_model_lock_key"] == "qwen3-omni-30b-a3b-instruct-gguf-q4km"
    assert captured["runtime_receipt_relpath"] == "receipts/runtime-alt-key.json"
    assert captured["d1_media_supplement_relpath"] == "receipts/artifacts/d1-alt.json"
    assert captured["d1_media_supplement_sha256"] == "c" * 64
