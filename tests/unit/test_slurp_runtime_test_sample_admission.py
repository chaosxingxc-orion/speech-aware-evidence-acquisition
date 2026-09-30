"""The SLURP runtime adapter admits ``slurp:test`` rows ONLY under a signed
final-report owner allowance (owner decisions 151 and 202).

Every fixture here is synthetic: fake sample ids, fake media bytes, a fake
allowance and a fake roster receipt inside a temporary repository. The real
test split is never opened.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.flight.factory import build_flight_runtime
from speech_aware_evidence_acquisition.rails.adapters.runtime_view import RuntimeViewError
from speech_aware_evidence_acquisition.rails.adapters.slurp_runtime import (
    FinalReportSampleAdmission, RuntimeSlurpAdapter, evaluate_test_sample_admission,
)
from test_flight_runtime import _make_repo, _HAPPY_PATH_KWARGS, _FakeGate, _git

RUN_ID = "SAEA-FAKE-TEST-SAMPLE-MILESTONE-00-PLAN-V1"
FIT_ID = "SAEA-FAKE-TEST-SAMPLE-FIT-V1"
ROSTER_IDS = [
    "slurp:test:000001:audio-a", "slurp:test:000001:audio-b", "slurp:test:000002:audio-a",
]
ALLOWANCE_REL = "docs/receipts/owner/2026-09-30-fake-test-sample-allowance-v1.json"
ROSTER_REL = "docs/receipts/rosters/fake-test-sample-v1.json"


def _identity(ids):
    return hashlib.sha256(
        "\n".join(sorted(f"slurp/{sample_id}" for sample_id in ids)).encode()
    ).hexdigest()


def _roster(ids=ROSTER_IDS, **overrides):
    document = {
        "schema": "saea-roster-receipt-v1", "roster_id": "FAKE-TEST-SAMPLE-V1",
        "split_role": "final-report", "split_identity_hash": _identity(ids),
        "items": [{"sample_id": sample_id, "audio_seconds": 1.0} for sample_id in ids],
    }
    document.update(overrides)
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode()


def _allowance(roster_bytes, *, identity=None, permitted=(RUN_ID,), status="authorised"):
    permitted = list(permitted)
    return (json.dumps({
        "schema": "saea-owner-split-allowance-v1",
        "study": "speech-aware-evidence-acquisition",
        "status": status,
        "dated_owner_decision": "synthetic decision for a unit test",
        "venue": "synthetic venue statement for a unit test",
        "split": {
            "carrier_lock_key": "slurp", "roster_id": "FAKE-TEST-SAMPLE-V1",
            "roster_receipt_relpath": ROSTER_REL,
            "roster_receipt_sha256": hashlib.sha256(roster_bytes).hexdigest(),
            "split_identity_hash": identity or _identity(ROSTER_IDS),
        },
        "permitted_run_ids": permitted,
        "read_run_ids": [permitted[0]],
        "preparation_run_ids": permitted[1:],
    }, indent=2, sort_keys=True) + "\n").encode()


def _repo(
    tmp_path, *, view_ids=ROSTER_IDS, split_role="final-report", view_role="final-report",
    allowance=True, allowance_identity=None, permitted=(RUN_ID,), roster_ids=ROSTER_IDS,
    view_label=None, allowance_sha=None,
):
    roster_bytes = _roster(roster_ids)
    allowance_bytes = _allowance(
        roster_bytes, identity=allowance_identity, permitted=permitted,
    )
    experiment_extra = {
        "population": {
            "roster_receipt": ROSTER_REL, "split_identity_hash": _identity(view_ids),
        },
    }
    if allowance:
        experiment_extra["owner_allowance"] = {
            "path": ALLOWANCE_REL,
            "sha256": allowance_sha or hashlib.sha256(allowance_bytes).hexdigest(),
        }
    repo = _make_repo(
        tmp_path, RUN_ID, carrier_lock_key="slurp",
        model_extra={"server_args": ["-np", "2", "-c", "8192"]},
        baseline_extra={"task_instruction": "Return the spoken command.",
                        "serving_slots": 2, "serving_slot_tokens": 4096},
        execution_plan_overrides={
            "split_role": split_role, "execution_profile": "bounded-discovery-probe",
        },
        experiment_extra=experiment_extra,
    )
    (repo / ALLOWANCE_REL).parent.mkdir(parents=True, exist_ok=True)
    (repo / ALLOWANCE_REL).write_bytes(allowance_bytes)
    (repo / ROSTER_REL).parent.mkdir(parents=True, exist_ok=True)
    (repo / ROSTER_REL).write_bytes(roster_bytes)
    data = tmp_path / "data"
    items = []
    for number, sample_id in enumerate(view_ids):
        path = data / "media" / f"row-{number}.wav"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"synthetic media {number}".encode())
        item = {
            "sample_id": sample_id, "media_relpath": f"media/row-{number}.wav",
            "audio_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "audio_seconds": 1.0, "sample_rate_hz": 16000, "packet_id": f"packet-{number}",
        }
        if view_label is not None and number == 0:
            item["intent"] = view_label
        items.append(item)
    view = {
        "schema": "saea-speech-native-runtime-view-v1", "count": len(items),
        "items": items, "carrier_lock_key": "slurp", "split_id": "TEST-SAMPLE",
        "split_name": "TEST-SAMPLE", "split_role": view_role,
        "split_identity_hash": _identity(view_ids),
    }
    (repo / "configs/dataset/d.json").write_text(json.dumps(view))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "bind synthetic test-sample view")
    return repo, data


def _adapter(runtime):
    # The factory builds the adapter eagerly (every refusal above is raised by
    # build_flight_runtime itself); read it back without a preflight, which
    # would also validate the fake ExecutionPlan against the real repository.
    return runtime._adapter_factory({}, None)  # noqa: SLF001


def _build(repo, data, tmp_path, run_id=RUN_ID):
    return build_flight_runtime(
        repo, data, model="m", dataset="d", baseline="b", experiment="e",
        run_id=run_id, attempt_id="a", runtime_root=tmp_path / "runtime",
        lock={}, lock_path=None, gate_factory=lambda *a, **kw: _FakeGate(),
        **_HAPPY_PATH_KWARGS,
    )


def test_test_sample_is_admitted_when_all_four_conditions_hold(tmp_path):
    repo, data = _repo(tmp_path)
    runtime = _build(repo, data, tmp_path)
    samples = _adapter(runtime).load_split("TEST-SAMPLE")
    assert sorted(sample.sample_id for sample in samples) == sorted(ROSTER_IDS)
    assert all(
        not (s.scenario or s.action or s.intent or s.entities) for s in samples
    )
    with pytest.raises(RuntimeViewError, match="gold"):
        _adapter(runtime).gold(samples[0])
    with pytest.raises(RuntimeViewError, match="registered split"):
        _adapter(runtime).load_split("TEST-SAMPLE", allow_heldout=True)


def test_successor_allowance_admits_a_fit_run_id_without_code_change(tmp_path):
    repo, data = _repo(tmp_path, permitted=(RUN_ID, FIT_ID))
    runtime = _build(repo, data, tmp_path, run_id=FIT_ID)
    assert len(_adapter(runtime).load_split("TEST-SAMPLE")) == len(ROSTER_IDS)


def test_refused_without_the_allowance(tmp_path):
    repo, data = _repo(tmp_path, allowance=False)
    with pytest.raises(RuntimeViewError, match=r"non-devel sample.*condition \(b\).*owner_allowance"):
        _build(repo, data, tmp_path)


def test_refused_when_the_allowance_bytes_drift_from_the_pin(tmp_path):
    repo, data = _repo(tmp_path, allowance_sha="0" * 64)
    with pytest.raises(RuntimeViewError, match=r"condition \(b\).*hashes to"):
        _build(repo, data, tmp_path)


def test_refused_with_a_wrong_split_identity(tmp_path):
    repo, data = _repo(tmp_path, allowance_identity="f" * 64)
    with pytest.raises(RuntimeViewError, match=r"condition \(b\).*split identity"):
        _build(repo, data, tmp_path)


def test_refused_for_a_run_id_the_allowance_does_not_name(tmp_path):
    repo, data = _repo(tmp_path)
    with pytest.raises(RuntimeViewError, match=r"condition \(d\).*permitted_run_ids"):
        _build(repo, data, tmp_path, run_id="SAEA-FAKE-UNNAMED-RUN-V1")


def test_refused_when_a_sample_is_outside_the_signed_roster(tmp_path):
    view_ids = ROSTER_IDS + ["slurp:test:000009:audio-z"]
    repo, data = _repo(
        tmp_path, view_ids=view_ids, allowance_identity=_identity(view_ids),
    )
    with pytest.raises(RuntimeViewError, match=r"condition \(c\)"):
        _build(repo, data, tmp_path)


def test_refused_when_the_view_is_not_the_signed_identity(tmp_path):
    # The view drops a roster member: its own identity no longer equals the
    # allowance's, even though every row it carries is a roster member.
    repo, data = _repo(tmp_path, view_ids=ROSTER_IDS[:2])
    with pytest.raises(RuntimeViewError, match=r"condition \(b\)"):
        _build(repo, data, tmp_path)


@pytest.mark.parametrize("split_role,view_role", [
    ("dev", "final-report"), ("final-report", "dev"), ("discovery", "discovery"),
])
def test_refused_unless_view_and_plan_are_both_final_report(tmp_path, split_role, view_role):
    repo, data = _repo(tmp_path, split_role=split_role, view_role=view_role)
    with pytest.raises(RuntimeViewError, match=r"condition \(a\)"):
        _build(repo, data, tmp_path)


def test_label_carrying_view_row_is_refused_even_under_the_allowance(tmp_path):
    repo, data = _repo(tmp_path, view_label="alarm_set")
    with pytest.raises(RuntimeViewError, match="label"):
        _build(repo, data, tmp_path)


def test_label_carrying_test_sample_is_refused_by_the_adapter_under_the_allowance(tmp_path):
    from speech_aware_evidence_acquisition.rails.adapters.slurp import SlurpSample
    from speech_aware_evidence_acquisition.rails.obs import AudioRef

    sample = SlurpSample(
        sample_id=ROSTER_IDS[0],
        audio_ref=AudioRef(path="media/row-0.wav", sha256="a" * 64).validate(),
        audio_seconds=1.0, utterance_id="000001", media_relpath="media/row-0.wav",
        scenario="alarm", action="set", intent="alarm_set", entities=(),
    )
    admission = FinalReportSampleAdmission(frozenset(ROSTER_IDS))
    with pytest.raises(RuntimeViewError, match="gold labels"):
        RuntimeSlurpAdapter(
            {}, tmp_path, repo_root=tmp_path, split_id="TEST-SAMPLE", samples=[sample],
            instruction_text="Return the spoken command.", split_role="final-report",
            test_admission=admission,
        )
    # Without an admission the same row is refused at the namespace guard.
    with pytest.raises(RuntimeViewError, match="non-devel sample"):
        RuntimeSlurpAdapter(
            {}, tmp_path, repo_root=tmp_path, split_id="TEST-SAMPLE", samples=[sample],
            instruction_text="Return the spoken command.", split_role="final-report",
        )


def test_train_and_devel_views_never_evaluate_the_admission(tmp_path):
    for namespace in ("train", "devel"):
        values = {"items": [{"sample_id": f"slurp:{namespace}:1:a"}]}
        assert evaluate_test_sample_admission(values, tmp_path, RUN_ID) is None


def test_the_agreement_producer_passes_the_adapter_under_the_allowance(tmp_path, monkeypatch):
    """The model-free producer's first step is build_flight_runtime; under the
    allowance it now returns a runtime over the signed sample and the producer
    proceeds to the runtime's own phase identity (which this fake cell lacks)."""

    repo, data = _repo(tmp_path)
    script = Path(__file__).resolve().parents[2] / "scripts" / "build_slurp_intent_exemplar_agreement.py"
    spec = importlib.util.spec_from_file_location("agreement_producer_under_test", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    cell = SimpleNamespace(
        run_id=RUN_ID, attempt_id="a",
        document={"cell_id": "fake-cell", "model_fragment": "m",
                  "dataset_fragment": "d", "baseline_fragment": "b"},
    )
    monkeypatch.setattr(module, "load_campaign_cells", lambda _repo, _exp: [cell])
    built = []

    def factory(*args, **kwargs):
        kwargs.update(lock={}, lock_path=None, gate_factory=lambda *a, **kw: _FakeGate(),
                      **_HAPPY_PATH_KWARGS)
        runtime = build_flight_runtime(*args, **kwargs)
        built.append(runtime)
        return runtime

    monkeypatch.setattr(module, "build_flight_runtime", factory)
    args = SimpleNamespace(
        repo_root=str(repo), data_root=str(data), experiment="e", cell="fake-cell",
        runtime_root=str(tmp_path / "runtime"), lock_path=str(tmp_path / "lock.json"),
    )
    with pytest.raises(Exception) as caught:
        module.build(args)
    assert not isinstance(caught.value, RuntimeViewError), caught.value
    assert len(built) == 1
    samples = _adapter(built[0]).load_split("TEST-SAMPLE")
    assert sorted(sample.sample_id for sample in samples) == sorted(ROSTER_IDS)
