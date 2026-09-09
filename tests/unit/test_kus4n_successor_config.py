import json
from pathlib import Path
from hashlib import sha256
from speech_aware_evidence_acquisition.rails.obs import AudioRef
from speech_aware_evidence_acquisition.rails.adapters.slurp_runtime import SlurpSample

from speech_aware_evidence_acquisition.core.attempts import validate_id
from speech_aware_evidence_acquisition.core.base import TASK_ADAPTERS
from speech_aware_evidence_acquisition.core.config import compose
from speech_aware_evidence_acquisition.core.flight.campaign import (
    load_campaign_cells,
)
from speech_aware_evidence_acquisition.core.flight.factory import (
    build_flight_runtime,
    register_builtin_task_adapters,
)


EXPERIMENTS = (
    "slurp-kus4n-candidates-successor-v1",
    "slurp-kus4n-candidates-twin-successor-v1",
)


def _cells(repo, experiment):
    path = repo / "configs/experiment" / f"{experiment}.json"
    return path, load_campaign_cells(repo, experiment)


def test_kus4n_successors_are_held_and_compose_through_shared_factory():
    repo = Path(__file__).resolve().parents[2]
    register_builtin_task_adapters()
    assert TASK_ADAPTERS.resolve("slurp")
    for experiment in EXPERIMENTS:
        path, cells = _cells(repo, experiment)
        assert len(cells) == 2
        assert "PENDING" not in path.read_text(encoding="utf-8")
        assert {cell.document["readiness"]["state"] for cell in cells} == {"held"}
        assert all(
            "PENDING" not in json.dumps(cell.document)
            for cell in cells
        )
        for cell in cells:
            values = compose(
                repo,
                cell.document["model_fragment"],
                cell.document["dataset_fragment"],
                cell.document["baseline_fragment"],
                experiment,
            ).values
            assert values["decoding_params"]["max_tokens"] == 64
            assert values["server_args"][:4] == ["-c", "65536", "-np", "8"]
            assert values["task_instruction_fill"] == "slurp-label-inventory"
            assert values["candidate_bank_sha256"] == (
                "a4458e77b648132d9d38c66d6b2ddf54fddf66924db6c6b780c59abf104c541f"
            )
            assert values["knowledge_snapshot_sha256"] == (
                "f179f5db51413fd3141f2d0b65fd49cea35f48b67429c838badf745dc3c779c5"
            )
            assert values["phase_supply"]["direct"]["provider"] == (
                "slurp-intent-candidates-v1"
            )
            assert values["phase_supply"]["direct"]["query_source"]["kind"] == (
                "sealed-vectors"
            )


def test_successor_identity_builds_shared_runtime_with_direct_fixture(tmp_path, slurp_world, monkeypatch):
    from speech_aware_evidence_acquisition.rails.adapters import slurp_runtime
    audio = slurp_world.audio_root / "slurp_real" / "audio-101.flac"
    sample = SlurpSample(
        sample_id="slurp:devel:101:audio",
        audio_ref=AudioRef(
            path="datasets/slurp/slurp_real/audio-101.flac",
            sha256=sha256(audio.read_bytes()).hexdigest(),
        ).validate(),
        audio_seconds=0.5,
        utterance_id="101",
        media_relpath="datasets/slurp/slurp_real/audio-101.flac",
        scenario="",
        action="",
        intent="",
        entities=(),
    )
    monkeypatch.setattr(slurp_runtime, "roster_samples", lambda *args, **kwargs: (sample,))
    repo = Path(__file__).resolve().parents[2]
    register_builtin_task_adapters()
    for experiment in EXPERIMENTS:
        _, cells = _cells(repo, experiment)
        cell = cells[0]
        runtime = build_flight_runtime(
            repo,
            slurp_world.data_root,
            model=cell.document["model_fragment"],
            dataset=cell.document["dataset_fragment"],
            baseline="slurp-phase-direct-only-v1",
            experiment=experiment,
            run_id=cell.run_id,
            attempt_id=cell.attempt_id,
            runtime_root=Path("/home/chao"),
            lock=json.loads(slurp_world.lock_path.read_text(encoding="utf-8")),
        )
        runtime.preparation_context()
        assert runtime.adapter.__class__.__name__ == "RuntimeSlurpAdapter"
        assert runtime.run_id == cell.run_id
        assert runtime.attempt_id == cell.attempt_id


def test_kus4n_successor_attempts_null_pin_and_report_rules():
    repo = Path(__file__).resolve().parents[2]
    expected_null_sha = (
        "2bd7e76ea2ea3c03369cd92d2c117c331fd28394a35da3568bf9f3e023cbdcb3"
    )
    attempts = []
    for experiment in EXPERIMENTS:
        path, cells = _cells(repo, experiment)
        document = json.loads(path.read_text(encoding="utf-8"))
        attempts.extend(cell.attempt_id for cell in cells)
        for cell in cells:
            validate_id(cell.attempt_id, "attempt_id")
        assert all(
            "PENDING" not in value
            for value in document["pending_preparation"].values()
            if isinstance(value, str)
        )
        assert document["null_alignment"]["artifact_relpath"] == (
            "docs/checks/speech-aware-evidence-acquisition/"
            "2026-09-09-null-new500-calibration/calibration.json"
        )
        assert document["null_alignment"]["artifact_sha256"] == expected_null_sha
        assert document["null_alignment"]["ni_rule"] == (
            "one-sided 95% lower bound > -delta for each metric"
        )
        assert document["null_alignment"]["equivalence_is_not_non_inferiority"] is True
        assert document["null_alignment"]["no_efficacy_conclusion_if_ni_only"] == (
            "allow_exemplars_noefficacy_conclusion"
        )
        assert document["null_alignment"]["ni_failure_action"] == (
            "hold; no automatic rerun"
        )
    assert len(set(attempts)) == 4


def test_kus4n_efficacy_retains_aligned_null_and_inherited_guards():
    repo = Path(__file__).resolve().parents[2]
    for experiment in EXPERIMENTS:
        document = json.loads((repo / "configs/experiment" / f"{experiment}.json").read_bytes())
        alignment = document["null_alignment"]
        metrics = alignment["metric_specific_operational_ni_margins_pp"]["slurp-slu-official-projected-v2"]
        upper = metrics["scenario_action_exact"]["ci90_pp"][1]
        assert alignment["intent_efficacy_threshold_pp"] == max(1.4341, upper)
        assert alignment["intent_efficacy_threshold_pp"] > 1.4341
        assert set(alignment["protection_metrics"]) == {"scenario_exact", "action_exact", "slu_f1_micro"}
        assert alignment["secondary_sign_guard"]
