"""``rails.probes.pslu_flight``: the P-SLU six-arm, two-phase flight
orchestration (docs/readiness/2026-08-17-pslu-preregistration-REGISTERED.md).
Engineering-only, zero live model contact -- every test drives a
``MockCoreClient``.
"""

from __future__ import annotations

import json
import hashlib
import threading
import time
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.model import SliceRegistry
from speech_aware_evidence_acquisition.core.driver.speech_native import (
    build_profile_tasks,
    profile_timing_metrics,
    read_speech_native_predictions,
)
from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT
from speech_aware_evidence_acquisition.core.tracing import DispatchingSink, TraceSink
from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.data.slurp import (
    SlurpTrainMaterial,
    SlurpTrainRecording,
)
from speech_aware_evidence_acquisition.rails import MockCoreClient
from speech_aware_evidence_acquisition.rails.adapters.slurp import SlurpAdapter
from speech_aware_evidence_acquisition.rails.probes.pslu_flight import (
    KeyCardV1,
    PSLU_ARMS,
    PsluFlightError,
    PsluRosters,
    PsluSampleManifest,
    _source_references_ontology_miner,
    assert_never_calls_ontology_miner,
    build_speech_native_binding,
    load_pslu_rosters,
    load_pslu_sample_manifest,
    load_speech_native_engineering_gate,
    pslu_supply_packet,
    render_roster_entries,
    render_speech_native_keys,
    render_type_vocabulary,
    run_pslu_flight,
    select_pslu_samples,
    run_speech_native_matcher,
    SpeechNativeMatchTask,
    run_speech_native_match_tasks,
)
from speech_aware_evidence_acquisition.rails.silence_swap import build_silence_swap_slice

_ROSTERS = PsluRosters(
    scenario_rosters={
        "iot": (("house_place", "kitchen"), ("device_type", "light")),
        "email": (("email_folder", "inbox"),),
    },
    global_types=("house_place", "device_type", "email_folder", "time"),
    full_roster=(("house_place", "kitchen"), ("time", "six")),
    derangement={"iot": "email", "email": "iot"},
)

_KEY_CARDS = (
    KeyCardV1(
        key_id="K001",
        definition="Commands that create, change, inspect, or remove alarms.",
        positive_examples=("wake me at six", "cancel my morning alarm"),
        contrastive_boundary="Do not use for calendar appointments.",
        value_label="alarm",
    ).validate(),
    KeyCardV1(
        key_id="K002",
        definition="Commands about email messages and mailboxes.",
        positive_examples=("read my new email", "send an email to Alex"),
        contrastive_boundary="Do not use for social messages.",
        value_label="email",
    ).validate(),
)


class _SpeechFeatureClient:
    def __init__(self, responses):
        self._responses = iter(responses)
        self.calls = []

    def complete(self, messages, **kwargs):
        self.calls.append((messages, kwargs))
        return next(self._responses)


class _SpeechSample:
    sample_id = "slurp:train:000001:audio-1"


_QUERY_DESCRIPTOR = {"packet_id": "slurp/train/query", "sha256": "a" * 64, "role": "query"}


def _assert_every_call_carries_query(client):
    for messages, kwargs in client.calls:
        parts = messages[1]["content"]
        queries = [
            part["speech_features"]
            for part in parts
            if part.get("type") == "input_speech_features"
            and part["speech_features"]["role"] == "query"
        ]
        assert queries == [_QUERY_DESCRIPTOR]
        assert kwargs["speech_feature_sample_id"] == _SpeechSample.sample_id


def test_key_card_rendering_never_exposes_value_label_for_text_cards():
    rendered = render_speech_native_keys(_KEY_CARDS, "K2")
    assert "K001" in rendered and "wake me at six" in rendered
    assert "calendar appointments" in rendered
    assert "value_label" not in rendered
    assert '"alarm"' not in rendered


def test_m1_selects_an_opaque_key_id_and_maps_label_deterministically():
    client = _SpeechFeatureClient(['{"key_id":"K002"}'])
    result = run_speech_native_matcher(
        core_client=client,
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=_KEY_CARDS,
        key_representation_id="K2",
        matcher_policy_id="M1",
    )
    assert result.key_id == "K002"
    assert result.value_label == "email"
    assert result.calls == 1
    _assert_every_call_carries_query(client)


def test_m1_canonicalizes_safe_zero_padding_without_exposing_a_fake_key_example():
    client = _SpeechFeatureClient(['{"key_id":"K2"}'])
    result = run_speech_native_matcher(
        core_client=client,
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=_KEY_CARDS,
        key_representation_id="K2",
        matcher_policy_id="M1",
    )
    assert result.key_id == "K002"
    assert result.value_label == "email"
    system_text = client.calls[0][0][0]["content"]
    assert "K000" not in system_text
    assert "copied verbatim from a supplied key heading" in system_text


def test_m2_reintroduces_the_same_speech_query_for_factor_and_selection_steps():
    client = _SpeechFeatureClient(
        [
            '{"factors":["message medium"],"summary":"mail command"}',
            '{"key_id":"K002"}',
        ]
    )
    result = run_speech_native_matcher(
        core_client=client,
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=_KEY_CARDS,
        key_representation_id="K2",
        matcher_policy_id="M2",
    )
    assert result.value_label == "email"
    assert result.calls == 2
    _assert_every_call_carries_query(client)


def test_m3_verifies_each_retrieved_candidate_and_arbitrates_only_a_tie():
    client = _SpeechFeatureClient(
        [
            '{"key_ids":["K001","K002"]}',
            '{"compatible":true,"confidence":80}',
            '{"compatible":true,"confidence":80}',
            '{"key_id":"K002"}',
        ]
    )
    result = run_speech_native_matcher(
        core_client=client,
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=_KEY_CARDS,
        key_representation_id="K2",
        matcher_policy_id="M3",
        top_k=2,
    )
    assert result.key_id == "K002"
    assert result.calls == 4
    assert result.top_key_ids == ("K001", "K002")
    _assert_every_call_carries_query(client)


def test_m4_trace_policy_preserves_ensemble_and_order_identity():
    client = _SpeechFeatureClient(
        ['{"key_id":"K001"}', '{"key_id":"K002"}', '{"key_id":"K001"}']
    )
    result = run_speech_native_matcher(
        core_client=client,
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=_KEY_CARDS,
        key_representation_id="K2",
        matcher_policy_id="M4",
        ensemble_base_policy_id="M1",
    )

    assert result.key_id == "K001"
    assert [kwargs["matcher_policy_id"] for _, kwargs in client.calls] == [
        "M4:M1:order-0:listwise",
        "M4:M1:order-1:listwise",
        "M4:M1:order-2:listwise",
    ]
    _assert_every_call_carries_query(client)


def test_audio_key_mode_carries_ordered_key_packets_without_key_body_text():
    client = _SpeechFeatureClient(['{"key_id":"K001"}'])
    audio_keys = {
        "K001": {"packet_id": "slurp/train/key-1", "sha256": "b" * 64},
        "K002": {"packet_id": "slurp/train/key-2", "sha256": "c" * 64},
    }
    run_speech_native_matcher(
        core_client=client,
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=_KEY_CARDS,
        key_representation_id="K3",
        matcher_policy_id="M1",
        audio_key_bindings=audio_keys,
    )
    parts = client.calls[0][0][1]["content"]
    key_parts = [part["speech_features"] for part in parts if part.get("type") == "input_speech_features"][1:]
    assert [part["packet_id"] for part in key_parts] == [
        "slurp/train/key-1",
        "slurp/train/key-2",
    ]
    assert all(part["role"] == "key" for part in key_parts)
    text = "\n".join(part["text"] for part in parts if part.get("type") == "text")
    assert "wake me at six" not in text


def test_speech_native_match_tasks_keep_multistep_slot_affinity_and_flush_in_task_order(
    tmp_path,
):
    run_id = "SAEA-E-TEST-speech-native-batch"
    sink = TraceSink(tmp_path / "trace", run_id)
    dispatcher = DispatchingSink(sink)

    class ConcurrentClient:
        def __init__(self):
            self.lock = threading.Lock()
            self.active = 0
            self.max_active = 0
            self.calls_by_sample = {}
            self.sequence = 0

        def complete(self, messages, **kwargs):
            sample_id = kwargs["speech_feature_sample_id"]
            slot = kwargs["decoding_params"]["id_slot"]
            with self.lock:
                self.active += 1
                self.max_active = max(self.max_active, self.active)
                self.calls_by_sample.setdefault(sample_id, []).append(slot)
                self.sequence += 1
                sequence = self.sequence
            dispatcher.emit(
                "OBS",
                f"batch-{sequence:04d}/obs",
                {"obs_sample_id": sample_id},
            )
            time.sleep(0.02 if sample_id.endswith("0") else 0.005)
            with self.lock:
                self.active -= 1
            if kwargs["matcher_policy_id"].endswith(":intent-factors"):
                return '{"factors":["domain"],"summary":"command"}'
            return '{"key_id":"K001"}'

    class Sample:
        def __init__(self, sample_id):
            self.sample_id = sample_id

    tasks = tuple(
        SpeechNativeMatchTask(
            task_id=f"task-{index}",
            sample=Sample(f"sample-{index}"),
            query_descriptor={
                "packet_id": f"slurp/train/query-{index}",
                "sha256": f"{index + 1:x}" * 64,
                "role": "query",
            },
            key_cards=_KEY_CARDS,
            key_representation_id="K2",
            matcher_policy_id="M2",
            decoding_params={"temperature": 0, "id_slot": "per-sample"},
        )
        for index in range(4)
    )
    client = ConcurrentClient()
    outcomes = run_speech_native_match_tasks(
        core_client=client,
        tasks=tasks,
        slot_count=2,
        queue_depth=2,
        trace_run_id=run_id,
        trace_flusher=lambda buffer: buffer.flush_into(sink),
    )
    sink.close()

    assert [outcome.task_id for outcome in outcomes] == [task.task_id for task in tasks]
    assert all(outcome.decision.value_label == "alarm" for outcome in outcomes)
    assert client.max_active == 2
    assert all(len(set(slots)) == 1 for slots in client.calls_by_sample.values())
    trace_rows = [
        json.loads(line)
        for line in (tmp_path / "trace" / f"{run_id}.trace.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert [row["payload"]["obs_sample_id"] for row in trace_rows] == [
        sample_id
        for sample_id in (f"sample-{index}" for index in range(4))
        for _ in range(2)
    ]


def test_speech_native_match_tasks_reject_queue_smaller_than_slot_pool():
    with pytest.raises(PsluFlightError, match="queue_depth must be at least slot_count"):
        run_speech_native_match_tasks(
            core_client=object(),
            tasks=(),
            slot_count=2,
            queue_depth=1,
        )


def test_speech_native_match_tasks_never_retry_a_failed_task():
    class FailingClient:
        def __init__(self):
            self.calls = []

        def complete(self, messages, **kwargs):
            sample_id = kwargs["speech_feature_sample_id"]
            self.calls.append(sample_id)
            if sample_id == "sample-fail":
                raise RuntimeError("registered one-shot failure")
            return '{"key_id":"K001"}'

    class Sample:
        def __init__(self, sample_id):
            self.sample_id = sample_id

    tasks = tuple(
        SpeechNativeMatchTask(
            task_id=sample_id,
            sample=Sample(sample_id),
            query_descriptor={
                "packet_id": f"slurp/train/{sample_id}",
                "sha256": digest,
                "role": "query",
            },
            key_cards=_KEY_CARDS,
            key_representation_id="K2",
            matcher_policy_id="M1",
            decoding_params={"id_slot": "per-sample"},
        )
        for sample_id, digest in (("sample-ok", "a" * 64), ("sample-fail", "b" * 64))
    )
    client = FailingClient()
    with pytest.raises(RuntimeError, match="registered one-shot failure"):
        run_speech_native_match_tasks(
            core_client=client,
            tasks=tasks,
            slot_count=2,
            queue_depth=2,
        )
    assert sorted(client.calls) == ["sample-fail", "sample-ok"]


def test_profile_task_expansion_and_slot_metrics_are_deterministic():
    class Sample:
        def __init__(self, sample_id):
            self.sample_id = sample_id

    samples = (Sample("s1"), Sample("s2"))
    bindings = {
        "s1": {"packet_id": "slurp/train/s1", "sha256": "a" * 64},
        "s2": {"packet_id": "slurp/train/s2", "sha256": "b" * 64},
    }
    tasks = build_profile_tasks(
        samples=samples,
        packet_bindings=bindings,
        key_cards=_KEY_CARDS,
        order_ids=("canonical", "reverse"),
        decoding_params={"temperature": 0, "id_slot": "per-sample"},
        key_representation_id="K2",
        matcher_policy_id="M1",
    )
    assert [task.task_id for task in tasks] == [
        "canonical:s1",
        "canonical:s2",
        "reverse:s1",
        "reverse:s2",
    ]
    assert [card.key_id for card in tasks[2].key_cards] == ["K002", "K001"]
    metrics = profile_timing_metrics(
        (
            {
                "started_at": "2026-08-21T12:00:00+00:00",
                "latency_seconds": 2.0,
            },
            {
                "started_at": "2026-08-21T12:00:00+00:00",
                "latency_seconds": 2.0,
            },
        ),
        slot_count=2,
        prompt_tokens=180,
        completion_tokens=20,
    )
    assert metrics == {
        "request_window_seconds": 2.0,
        "slot_occupancy_pct": 100.0,
        "aggregate_tokens_per_second": 100.0,
    }


def test_model_free_prediction_read_verifies_and_selects_the_better_cell(tmp_path):
    binding_path = REPO_ROOT / "configs/probes/g0-binding/speech-native-train-binding.json"
    binding_sha256 = hashlib.sha256(binding_path.read_bytes()).hexdigest()
    binding = json.loads(binding_path.read_text(encoding="utf-8"))
    items = binding["splits"]["OPT-A36"]["items"]
    key_by_label = {card["value_label"]: card["key_id"] for card in binding["key_cards"]}

    def write_cell(cell_id, *, make_first_wrong):
        key_representation_id, matcher_policy_id = cell_id.split("-")
        attempt_dir = tmp_path / cell_id
        attempt_dir.mkdir()
        rows = []
        for index, item in enumerate(items):
            key_id = key_by_label[item["value_label"]]
            if index == 0 and make_first_wrong:
                key_id = next(candidate for candidate in key_by_label.values() if candidate != key_id)
            predicted = next(
                card["value_label"] for card in binding["key_cards"] if card["key_id"] == key_id
            )
            rows.append(
                {
                    "schema": "saea-speech-native-decision-v1",
                    "sample_id": item["sample_id"],
                    "key_id": key_id,
                    "predicted_value_label": predicted,
                    "parse_failure": False,
                }
            )
        decisions = attempt_dir / "decisions.jsonl"
        decisions.write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
            encoding="utf-8",
        )
        digest = hashlib.sha256(decisions.read_bytes()).hexdigest()
        receipt = {
            "status": "COMPLETED",
            "request_failures": [],
            "split_identity_hash": "a" * 64,
            "run_id": f"run-{cell_id}",
            "profile": {
                "key_representation_id": key_representation_id,
                "matcher_policy_id": matcher_policy_id,
                "actual_contact_count": len(rows),
            },
            "decisions": {
                "path": decisions.name,
                "sha256": digest,
                "count": len(rows),
            },
            "timing": {"aggregate_tokens_per_second": 100.0},
        }
        (attempt_dir / "flight-receipt.json").write_text(
            json.dumps(receipt), encoding="utf-8"
        )
        return attempt_dir

    baseline_dir = write_cell("K0-M1", make_first_wrong=True)
    candidate_dir = write_cell("K2-M1", make_first_wrong=False)
    report = read_speech_native_predictions(
        attempt_dirs=(baseline_dir, candidate_dir),
        binding_path=binding_path,
        binding_sha256=binding_sha256,
        split_name="OPT-A36",
    )
    assert report["selected_cell_id"] == "K2-M1"
    candidate = next(item for item in report["aggregates"] if item["cell_id"] == "K2-M1")
    assert candidate["correct"] == 36
    assert candidate["wrong_to_correct_vs_baseline"] == 1
    assert candidate["correct_to_wrong_vs_baseline"] == 0


def _binding_material():
    material = []
    for scenario_index, scenario in enumerate(("alarm", "email")):
        for item_index in range(12):
            speaker = f"speaker-{scenario_index}-{item_index}"
            sample_id = f"slurp:train:{scenario_index:02d}{item_index:04d}:audio-{scenario_index}-{item_index}"
            material.append(
                SlurpTrainMaterial(
                    utterance_id=f"{scenario_index:02d}{item_index:04d}",
                    scenario=scenario,
                    action="act",
                    sentence=f"unique {scenario} example {item_index}",
                    recordings=(
                        SlurpTrainRecording(
                            sample_id=sample_id,
                            media_relpath=f"datasets/slurp/slurp_real/audio-{scenario_index}-{item_index}.flac",
                            speaker_id=speaker,
                        ),
                    ),
                )
            )
    return tuple(material)


def test_speech_native_binding_is_stratified_and_query_key_isolated():
    binding = build_speech_native_binding(
        _binding_material(),
        seed=20260821,
        expected_scenarios=("alarm", "email"),
        opt_a_per_scenario=2,
        opt_b_per_scenario=1,
        gate_per_scenario=1,
        key_examples_per_scenario=5,
    )
    assert len(binding["splits"]["OPT-A36"]["items"]) == 4
    assert len(binding["splits"]["OPT-B18"]["items"]) == 2
    assert len(binding["splits"]["GATE18"]["items"]) == 2
    engineering_gate = binding["engineering_gate"]
    assert engineering_gate["name"] == "ENG-GATE8"
    assert len(engineering_gate["items"]) == 4
    assert all(
        set(item) == {"sample_id", "media_relpath"}
        for item in engineering_gate["items"]
    )
    assert engineering_gate["sample_ids"] == [
        item["sample_id"] for item in binding["splits"]["OPT-A36"]["items"]
    ]
    assert engineering_gate["split_identity_hash"] == _binding_document_sha256(
        {
            key: engineering_gate[key]
            for key in ("schema", "name", "seed", "sample_ids")
        }
    )
    assert len(binding["key_cards"]) == 2
    query_items = [
        item for split in binding["splits"].values() for item in split["items"]
    ]
    key_sources = [
        source for key in binding["key_material"] for source in key["sources"]
    ]
    assert {item["speaker_id"] for item in query_items}.isdisjoint(
        source["speaker_id"] for source in key_sources
    )
    assert {item["sample_id"] for item in query_items}.isdisjoint(
        source["sample_id"] for source in key_sources
    )
    assert {item["normalized_sentence"] for item in query_items}.isdisjoint(
        source["normalized_sentence"] for source in key_sources
    )


def _binding_document_sha256(document):
    import hashlib

    raw = json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def test_speech_native_binding_is_byte_deterministic_for_the_same_seed():
    first = build_speech_native_binding(
        _binding_material(), seed=7, expected_scenarios=("alarm", "email")
    )
    second = build_speech_native_binding(
        reversed(_binding_material()), seed=7, expected_scenarios=("alarm", "email")
    )
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_speech_native_binding_refuses_insufficient_isolated_material():
    with pytest.raises(PsluFlightError, match="insufficient"):
        build_speech_native_binding(
            _binding_material()[:8],
            seed=1,
            expected_scenarios=("alarm", "email"),
        )


def _write_engineering_gate_view(tmp_path):
    media_root = tmp_path / "datasets/slurp/slurp_real"
    media_root.mkdir(parents=True)
    items = []
    for index in range(4):
        raw = f"speech-{index}".encode()
        media_relpath = f"datasets/slurp/slurp_real/audio-{index}.flac"
        (tmp_path / media_relpath).write_bytes(raw)
        items.append(
            {
                "sample_id": f"slurp:train:{index:06d}:audio-{index}",
                "media_relpath": media_relpath,
                "audio_sha256": hashlib.sha256(raw).hexdigest(),
                "audio_seconds": 1.25,
                "sample_rate_hz": 16000,
                "packet_id": f"slurp/train/{index:06d}/audio-{index}",
            }
        )
    unsigned = {
        "schema": "saea-speech-native-engineering-gate-view-v1",
        "study": "speech-aware-evidence-acquisition",
        "status": "MODEL-FREE, LABEL-FREE ENGINEERING INPUT; NOT AN EXPOSURE REGISTRATION",
        "carrier_lock_key": "slurp",
        "split_name": "ENG-GATE8",
        "split_role": "discovery",
        "seed": 7,
        "split_identity_hash": "a" * 64,
        "source_binding_sha256": "b" * 64,
        "d1_media_supplement": "receipts/artifacts/d1.json",
        "d1_media_supplement_sha256": "c" * 64,
        "d1_manifest_sha256": "d" * 64,
        "count": 4,
        "audio_seconds_total": 5.0,
        "items": items,
    }
    canonical = json.dumps(
        unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    path = tmp_path / "gate.json"
    path.write_text(
        json.dumps(
            {**unsigned, "runtime_view_sha256": hashlib.sha256(canonical).hexdigest()}
        ),
        encoding="utf-8",
    )
    return path


def test_engineering_gate_loader_validates_media_in_parallel_without_gold(tmp_path):
    path = _write_engineering_gate_view(tmp_path)
    lock = threading.Lock()
    active = 0
    peak = 0

    def media_probe(media_path):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        time.sleep(0.02)
        try:
            raw = media_path.read_bytes()
            return hashlib.sha256(raw).hexdigest(), 1.25, 16000
        finally:
            with lock:
                active -= 1

    gate = load_speech_native_engineering_gate(
        path,
        data_root=tmp_path,
        expected_count=4,
        workers=3,
        media_probe=media_probe,
    )

    assert len(gate.samples) == 4
    assert 2 <= peak <= 3
    assert gate.samples[0].packet_id == "slurp/train/000000/audio-0"
    assert not hasattr(gate.samples[0], "scenario")
    assert gate.d1_media_supplement_sha256 == "c" * 64


def test_engineering_loader_accepts_generalized_runtime_view_for_named_split(tmp_path):
    path = _write_engineering_gate_view(tmp_path)
    document = json.loads(path.read_text(encoding="utf-8"))
    unsigned = {key: value for key, value in document.items() if key != "runtime_view_sha256"}
    unsigned["schema"] = "saea-speech-native-runtime-view-v1"
    unsigned["split_name"] = "OPT-A36"
    canonical = json.dumps(
        unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    path.write_text(
        json.dumps({**unsigned, "runtime_view_sha256": hashlib.sha256(canonical).hexdigest()}),
        encoding="utf-8",
    )

    gate = load_speech_native_engineering_gate(
        path,
        data_root=tmp_path,
        expected_count=4,
        expected_split_name="OPT-A36",
        media_probe=lambda media_path: (
            hashlib.sha256(media_path.read_bytes()).hexdigest(),
            1.25,
            16000,
        ),
    )

    assert len(gate.samples) == 4
    assert gate.split_identity_hash == "a" * 64


def test_engineering_gate_loader_refuses_gold_fields_and_hash_drift(tmp_path):
    path = _write_engineering_gate_view(tmp_path)
    document = json.loads(path.read_text(encoding="utf-8"))
    document["items"][0]["value_label"] = "alarm"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(PsluFlightError, match="label-free"):
        load_speech_native_engineering_gate(
            path,
            data_root=tmp_path,
            expected_count=4,
            media_probe=lambda _path: ("0" * 64, 1.25, 16000),
        )


def _adapter(slurp_world) -> SlurpAdapter:
    lock = load_lock(slurp_world.lock_path)
    return SlurpAdapter(lock, slurp_world.data_root)


# ---------------------------------------------------------------------------
# render_roster_entries / render_type_vocabulary
# ---------------------------------------------------------------------------


def test_render_roster_entries_joins_type_value_pairs():
    text = render_roster_entries([("house_place", "kitchen"), ("device_type", "light")])
    assert text == "house_place=kitchen; device_type=light"


def test_render_type_vocabulary_comma_joins_bare_types():
    assert render_type_vocabulary(["a", "b", "c"]) == "a, b, c"


# ---------------------------------------------------------------------------
# load_pslu_rosters
# ---------------------------------------------------------------------------


def _write_roster_table(path: Path, **overrides) -> None:
    document = {
        "probe": "P-SLU",
        "legality_tier": "legal",
        "train_synthetic_refused": {"train_jsonl_overlap_with_devel": 0},
        "arms": {
            "A1_scenario_roster": {
                "rosters": {
                    "iot": [["house_place", "kitchen"], ["device_type", "light"]],
                    "email": [["email_folder", "inbox"]],
                }
            },
            "A2_global_type_vocabulary": {
                "types": ["house_place", "device_type", "email_folder", "time"]
            },
            "A3_full_ontology_dose_capped": {"roster": [["house_place", "kitchen"], ["time", "six"]]},
            "A4_deranged": {"mapping": {"iot": "email", "email": "iot"}},
        },
    }
    document.update(overrides)
    path.write_text(json.dumps(document), encoding="utf-8")


def test_load_pslu_rosters_happy_path(tmp_path):
    path = tmp_path / "rosters.json"
    _write_roster_table(path)
    rosters = load_pslu_rosters(path)
    assert rosters.scenario_rosters["iot"] == (("house_place", "kitchen"), ("device_type", "light"))
    assert rosters.global_types == ("house_place", "device_type", "email_folder", "time")
    assert rosters.full_roster == (("house_place", "kitchen"), ("time", "six"))
    assert rosters.derangement == {"iot": "email", "email": "iot"}


def test_load_pslu_rosters_rejects_wrong_probe(tmp_path):
    path = tmp_path / "rosters.json"
    _write_roster_table(path, probe="P-A2T")
    with pytest.raises(PsluFlightError, match="probe must be"):
        load_pslu_rosters(path)


def test_load_pslu_rosters_rejects_non_legal_tier(tmp_path):
    path = tmp_path / "rosters.json"
    _write_roster_table(path, legality_tier="ceiling")
    with pytest.raises(PsluFlightError, match="legality_tier"):
        load_pslu_rosters(path)


def test_load_pslu_rosters_rejects_nonzero_devel_overlap(tmp_path):
    path = tmp_path / "rosters.json"
    _write_roster_table(path, train_synthetic_refused={"train_jsonl_overlap_with_devel": 5})
    with pytest.raises(PsluFlightError, match="overlap_with_devel"):
        load_pslu_rosters(path)


def test_load_pslu_rosters_against_the_real_binding_table():
    """The mission's own registered artifact -- proves this loader actually
    parses it, not merely a hand-shrunk test fixture."""

    path = (
        Path(__file__).resolve().parents[2]
        / "configs" / "probes" / "g0-binding" / "pslu-rosters-train-only.json"
    )
    rosters = load_pslu_rosters(path)
    assert "iot" in rosters.scenario_rosters
    assert len(rosters.global_types) == 55
    assert len(rosters.full_roster) == 100
    assert rosters.derangement["audio"] == "cooking"


# ---------------------------------------------------------------------------
# load_pslu_sample_manifest / select_pslu_samples
# ---------------------------------------------------------------------------


def _write_sample_manifest(path: Path, **overrides) -> None:
    document = {
        "probe": "P-SLU",
        "seed": 20260807,
        "split_identity_hash": "a" * 64,
        "items": [
            {"sample_id": "slurp:devel:000102:audio-102"},
            {"sample_id": "slurp:devel:000101:audio-101"},
        ],
    }
    document.update(overrides)
    path.write_text(json.dumps(document), encoding="utf-8")


def test_load_pslu_sample_manifest_happy_path(tmp_path):
    path = tmp_path / "manifest.json"
    _write_sample_manifest(path)
    manifest = load_pslu_sample_manifest(path)
    assert manifest.sample_ids == ("slurp:devel:000102:audio-102", "slurp:devel:000101:audio-101")
    assert manifest.seed == 20260807
    assert manifest.split_identity_hash == "a" * 64


def test_load_pslu_sample_manifest_rejects_duplicate_ids(tmp_path):
    path = tmp_path / "manifest.json"
    _write_sample_manifest(
        path,
        items=[{"sample_id": "x"}, {"sample_id": "x"}],
    )
    with pytest.raises(PsluFlightError, match="duplicate sample_id"):
        load_pslu_sample_manifest(path)


def test_load_pslu_sample_manifest_against_the_real_binding_table():
    path = (
        Path(__file__).resolve().parents[2]
        / "configs" / "probes" / "g0-binding" / "pslu-sample-devel-n60.json"
    )
    manifest = load_pslu_sample_manifest(path)
    assert len(manifest.sample_ids) == 60
    assert manifest.seed == 20260807
    assert manifest.split_identity_hash == (
        "fc9de436eba5aba120ecf07ee112765cd4ac0609150e0aaf36f4d44c9c5b5ee5"
    )


def test_select_pslu_samples_filters_and_reorders(slurp_world):
    adapter = _adapter(slurp_world)
    all_devel = adapter.load_split("devel")  # sorted by sample_id: 101, 101-headset, 102
    manifest = PsluSampleManifest(
        sample_ids=("slurp:devel:000102:audio-102", "slurp:devel:000101:audio-101"),
        split_identity_hash="a" * 64,
        seed=1,
    )
    selected = select_pslu_samples(all_devel, manifest)
    assert [s.sample_id for s in selected] == list(manifest.sample_ids)


def test_select_pslu_samples_raises_on_a_missing_id(slurp_world):
    adapter = _adapter(slurp_world)
    all_devel = adapter.load_split("devel")
    manifest = PsluSampleManifest(sample_ids=("bogus-id",), split_identity_hash="a" * 64, seed=1)
    with pytest.raises(PsluFlightError, match="not present in the loaded split"):
        select_pslu_samples(all_devel, manifest)


# ---------------------------------------------------------------------------
# pslu_supply_packet -- per-arm roster selection
# ---------------------------------------------------------------------------


def test_a0_has_no_supply():
    assert pslu_supply_packet("A0", scenario=None, rosters=_ROSTERS) is None


def test_a1_uses_the_named_scenarios_roster():
    packet = pslu_supply_packet("A1", scenario="iot", rosters=_ROSTERS)
    assert packet.prompt_block == "house_place=kitchen; device_type=light"


def test_a1_without_a_scenario_raises():
    with pytest.raises(PsluFlightError, match="A1 requires"):
        pslu_supply_packet("A1", scenario=None, rosters=_ROSTERS)


def test_a1_unknown_scenario_raises():
    with pytest.raises(PsluFlightError, match="no A1 roster"):
        pslu_supply_packet("A1", scenario="bogus", rosters=_ROSTERS)


def test_a1p_uses_the_predicted_scenarios_roster():
    packet = pslu_supply_packet("A1p", scenario="email", rosters=_ROSTERS)
    assert packet.prompt_block == "email_folder=inbox"


def test_a1p_falls_back_to_a2_when_scenario_is_none():
    packet = pslu_supply_packet("A1p", scenario=None, rosters=_ROSTERS)
    assert packet.prompt_block == render_type_vocabulary(_ROSTERS.global_types)
    assert packet.assembly_template_id == "pslu-A1p-fallback-A2-roster-v1"


def test_a1p_falls_back_to_a2_when_scenario_is_unknown():
    packet = pslu_supply_packet("A1p", scenario="not-a-real-scenario", rosters=_ROSTERS)
    assert packet.prompt_block == render_type_vocabulary(_ROSTERS.global_types)


def test_a2_is_the_global_type_vocabulary():
    packet = pslu_supply_packet("A2", scenario="iot", rosters=_ROSTERS)
    assert packet.prompt_block == "house_place, device_type, email_folder, time"


def test_a3_is_the_full_dose_capped_roster():
    packet = pslu_supply_packet("A3", scenario=None, rosters=_ROSTERS)
    assert packet.prompt_block == "house_place=kitchen; time=six"


def test_a4_uses_the_deranged_partners_roster():
    packet = pslu_supply_packet("A4", scenario="iot", rosters=_ROSTERS)
    assert packet.prompt_block == "email_folder=inbox"  # iot's deranged partner is email


def test_a4_without_a_scenario_raises():
    with pytest.raises(PsluFlightError, match="A4 requires"):
        pslu_supply_packet("A4", scenario=None, rosters=_ROSTERS)


def test_unknown_arm_raises():
    with pytest.raises(PsluFlightError, match="unknown P-SLU arm"):
        pslu_supply_packet("A99", scenario="iot", rosters=_ROSTERS)


# ---------------------------------------------------------------------------
# the ontology-miner call guard
# ---------------------------------------------------------------------------


def test_the_real_module_source_never_references_the_ontology_miner():
    assert_never_calls_ontology_miner()  # no args -- self-checks the real file


def test_guard_catches_a_live_import():
    source = "from ...data.slurp import load_slurp_ontology\n"
    assert _source_references_ontology_miner(source) is True
    with pytest.raises(PsluFlightError, match="load_slurp_ontology"):
        assert_never_calls_ontology_miner(source)


def test_guard_catches_a_bare_call():
    source = "def f(lock, root):\n    return load_slurp_ontology(lock, root)\n"
    assert _source_references_ontology_miner(source) is True


def test_guard_catches_an_attribute_access():
    source = "import speech_aware_evidence_acquisition.data.slurp as slurp\nslurp.load_slurp_ontology(1, 2)\n"
    assert _source_references_ontology_miner(source) is True


def test_guard_does_not_trip_on_a_docstring_mention():
    source = '"""This module never calls load_slurp_ontology -- see the docstring."""\nx = 1\n'
    assert _source_references_ontology_miner(source) is False
    assert_never_calls_ontology_miner(source)  # does not raise


# ---------------------------------------------------------------------------
# run_pslu_flight -- end to end
# ---------------------------------------------------------------------------


def _flight_world(slurp_world):
    adapter = _adapter(slurp_world)
    devel = adapter.load_split("devel")
    s_iot = devel[0]  # slurp:devel:000101:audio-101, gold scenario "iot"
    s_email = devel[2]  # slurp:devel:000102:audio-102, gold scenario "email"
    return adapter, s_iot, s_email


def _responder(s_iot):
    def responder(messages):
        content = messages[1]["content"]
        is_phase1 = len(content) == 1  # A0 sends audio only, every other arm prepends text
        if is_phase1:
            # Deliberately WRONG for s_iot (gold "iot") -- proves A1' reads
            # the phase-1 prediction, never the gold scenario.
            return json.dumps({"scenario": "email", "action": "query", "entities": []})
        return json.dumps({"scenario": "iot", "action": "hue_lighton", "entities": []})

    return responder


def test_run_pslu_flight_produces_a0_then_five_phase2_arms_per_sample(slurp_world):
    adapter, s_iot, s_email = _flight_world(slurp_world)
    client = MockCoreClient(responder=_responder(s_iot))

    summary = run_pslu_flight(adapter=adapter, core_client=client, samples=[s_iot, s_email], rosters=_ROSTERS)

    assert [r.arm for r in summary.results] == [
        "A0", "A0",
        "A1", "A1p", "A2", "A3", "A4",
        "A1", "A1p", "A2", "A3", "A4",
    ]
    assert len(client.calls) == 12
    assert set(PSLU_ARMS) == {"A0", "A1", "A1p", "A2", "A3", "A4"}


def test_run_pslu_flight_a1_prime_reads_the_phase1_prediction_not_gold(slurp_world):
    adapter, s_iot, s_email = _flight_world(slurp_world)
    client = MockCoreClient(responder=_responder(s_iot))

    summary = run_pslu_flight(adapter=adapter, core_client=client, samples=[s_iot, s_email], rosters=_ROSTERS)

    assert summary.predicted_scenario_by_sample_id[s_iot.sample_id] == "email"  # wrong, as scripted
    assert summary.predicted_scenario_by_sample_id[s_email.sample_id] == "email"  # right

    a1_iot = next(r for r in summary.results if r.arm == "A1" and r.sample_id == s_iot.sample_id)
    a1p_iot = next(
        r for r in summary.results if r.arm == "A1p" and r.sample_id == s_iot.sample_id and not r.silence_swapped
    )
    a1_text = a1_iot.messages[1]["content"][0]["text"]
    a1p_text = a1p_iot.messages[1]["content"][0]["text"]
    assert a1_text == "house_place=kitchen; device_type=light"  # A1: gold "iot" roster
    assert a1p_text == "email_folder=inbox"  # A1': predicted "email" roster -- differs from A1
    assert a1_text != a1p_text


def test_run_pslu_flight_phase1_row_carries_whether_it_parsed(slurp_world):
    adapter, s_iot, s_email = _flight_world(slurp_world)
    client = MockCoreClient(responder=_responder(s_iot))
    summary = run_pslu_flight(adapter=adapter, core_client=client, samples=[s_iot, s_email], rosters=_ROSTERS)
    a0_rows = [r for r in summary.results if r.arm == "A0"]
    assert all(row.phase1_scenario_parsed is True for row in a0_rows)
    phase2_rows = [r for r in summary.results if r.arm != "A0"]
    assert all(row.phase1_scenario_parsed is None for row in phase2_rows)


def test_run_pslu_flight_silence_swap_adds_one_extra_a1p_row(slurp_world):
    """``silence_swap_media_relpaths`` carries whatever media_relpath a REAL
    SliceRegistry actually produced for s_iot's raw, colon-bearing SLURP id
    (``slurp:devel:000101:audio-101``) -- not a hand-typed path the real
    registry could never build. This is the regression test for
    docs/checks/speech-aware-evidence-acquisition/2026-08-17-pslu-flight/
    2026-08-18-attempt2-flight-execution.md: the original version of this
    test hardcoded exactly the string the pre-fix registry refused to
    produce, so it hid the defect behind a green suite."""

    adapter, s_iot, s_email = _flight_world(slurp_world)
    client = MockCoreClient(responder=_responder(s_iot))
    assert ":" in s_iot.sample_id  # the defect only bites a colon-bearing raw id
    registry = SliceRegistry(
        data_root=slurp_world.data_root,
        run_id="run-x",
        parent_facts={s_iot.sample_id: (s_iot.media_relpath, s_iot.audio_seconds)},
    )
    silence_record = build_silence_swap_slice(
        registry=registry,
        data_root=slurp_world.data_root,
        sample_id=s_iot.sample_id,
        parent_media_relpath=s_iot.media_relpath,
        duration_seconds=s_iot.audio_seconds,
        sample_rate_hz=16000,
    )
    registry.register(silence_record)
    silence_relpath = silence_record.media_relpath
    assert ":" not in silence_relpath  # raw id sanitized into the filesystem token

    summary = run_pslu_flight(
        adapter=adapter,
        core_client=client,
        samples=[s_iot, s_email],
        rosters=_ROSTERS,
        silence_swap_media_relpaths={s_iot.sample_id: silence_relpath},
    )

    assert len(summary.results) == 13  # 12 base + 1 silence-swap
    swapped = [r for r in summary.results if r.silence_swapped]
    assert len(swapped) == 1
    assert swapped[0].arm == "A1p"
    assert swapped[0].sample_id == s_iot.sample_id
    assert swapped[0].messages[1]["content"][-1] == {
        "type": "input_audio", "media_relpath": silence_relpath,
    }
    # The roster text is UNCHANGED by the swap -- only the audio changes.
    normal_a1p = next(
        r for r in summary.results if r.arm == "A1p" and r.sample_id == s_iot.sample_id and not r.silence_swapped
    )
    assert swapped[0].messages[1]["content"][0] == normal_a1p.messages[1]["content"][0]


def test_run_pslu_flight_rejects_empty_samples(slurp_world):
    adapter, s_iot, _ = _flight_world(slurp_world)
    with pytest.raises(PsluFlightError, match="at least one sample"):
        run_pslu_flight(adapter=adapter, core_client=MockCoreClient(), samples=(), rosters=_ROSTERS)


def test_run_pslu_flight_rejects_unknown_silence_swap_sample_ids(slurp_world):
    adapter, s_iot, _ = _flight_world(slurp_world)
    client = MockCoreClient(responder=_responder(s_iot))
    with pytest.raises(PsluFlightError, match="outside this flight"):
        run_pslu_flight(
            adapter=adapter,
            core_client=client,
            samples=[s_iot],
            rosters=_ROSTERS,
            silence_swap_media_relpaths={"bogus-sample-id": "x.wav"},
        )
