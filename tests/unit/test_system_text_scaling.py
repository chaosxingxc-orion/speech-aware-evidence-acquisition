"""Exercise fixed-pool staging without granting any execution authority."""

import copy
import pytest
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_text_scaling import build_stage


def fixture():
    import hashlib

    ids = sorted(
        [f"slurp:train:{i:06d}:audio-{i}" for i in range(400)],
        key=lambda s: hashlib.sha256(f"20261001:{s}".encode()).hexdigest(),
    )
    items = [
        dict(
            sample_id=s,
            audio_seconds=2.0,
            audio_sha256="a" * 64,
            media_relpath=f"data/{i}.flac",
            packet_id=s,
            sample_rate_hz=16000,
        )
        for i, s in enumerate(ids)
    ]
    view = dict(
        carrier_lock_key="slurp",
        count=400,
        split_role="discovery",
        split_name="CURRENT400",
        seed=20261001,
        items=items,
    )
    view["runtime_view_sha256"] = content_hash(view)
    exp = dict(
        cells=[
            dict(
                cell_id="old",
                run_id="OLD",
                attempt_id="old",
                model_fragment="model",
                dataset_fragment="old",
                baseline_fragment="old",
                readiness=dict(state="ready"),
                system_text_policy_binding=dict(bundle_id="seed"),
            )
        ],
        execution_plan=dict(
            planned_model_calls=260,
            planned_gpu_hours=1,
            planned_speech_audio_seconds=1500,
            execution_profile="bounded-discovery-probe",
            split_role="discovery",
        ),
        family_budget={},
        population={},
        populations=[],
        stage3_measurement={},
    )
    base = dict(
        policy="shared",
        native_episode=dict(roles={}),
        native_contact_fit=dict(
            run_id="OLD-FIT",
            attempt_id="old-fit",
            contact_cap=1040,
            max_speech_packets=1,
        ),
        prepared_phase_supply=dict(relpath="old", sha256="x"),
        knowledge_stores=dict(unchanged=True),
    )
    return view, exp, base, content_hash(ids)


@pytest.mark.parametrize("size", [50, 100, 200])
def test_nested_immutable_inputs_and_all_eight_held(size):
    v, e, b, h = fixture()
    before = copy.deepcopy((v, e, b))
    stage = build_stage(v, e, b, size=size, expected_pool_hash=h)
    assert (v, e, b) == before
    assert stage["view"]["items"] == v["items"][:size]
    assert len(stage["members"]) == 8
    assert len({m["experiment"]["cells"][0]["run_id"] for m in stage["members"]}) == 8
    for m in stage["members"]:
        c = m["experiment"]["cells"][0]
        assert c["attempt_id"].startswith("attempt-slurp-native-")
        assert c["readiness"]["state"] == "held"
        assert c["allowed_execution_stages"] == ["check", "prepare-supply"]
        assert c["system_text_scaling_slot"]["policy_status"] == "pending-freeze"
        assert m["baseline"]["knowledge_stores"] == b["knowledge_stores"]
        assert "prepared_phase_supply" not in m["baseline"]
        assert m["baseline"]["native_contact_fit"]["contact_cap"] == 52 * size
        assert m["experiment"]["execution_plan"]["planned_model_calls"] == 13 * size
        assert m["experiment"]["stage3_measurement"]["claims_benefit"] is False
    assert stage["trajectory_ceiling"] == 8 * size
    assert stage["contacts_authorized"] == 0


@pytest.mark.parametrize("size", [True, 0, 20, 400, 51])
def test_refuse_unrequested_scale(size):
    v, e, b, h = fixture()
    with pytest.raises(ValueError):
        build_stage(v, e, b, size=size, expected_pool_hash=h)


@pytest.mark.parametrize("defect", ["hash", "partition", "reordered", "label"])
def test_refuse_wrong_pool_or_runtime_gold(defect):
    v, e, b, h = fixture()
    if defect == "hash":
        h = "0" * 64
    if defect == "partition":
        v["split_role"] = "final-report"
    if defect == "reordered":
        v["items"] = list(reversed(v["items"]))
    if defect == "label":
        v["items"][0]["gold"] = "forbidden"
    v["runtime_view_sha256"] = content_hash(
        {k: x for k, x in v.items() if k != "runtime_view_sha256"}
    )
    with pytest.raises(ValueError):
        build_stage(v, e, b, size=50, expected_pool_hash=h)
