"""Model-free E22 consumption plumbing; no source read, own null or adoption."""

from pathlib import Path
import json
import copy

import pytest

from speech_aware_evidence_acquisition.core.base import DELIVERY_NORMALISERS, DeliveryNormaliserError
from speech_aware_evidence_acquisition.rails import consumption_module as cm
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
from speech_aware_evidence_acquisition.rails.native_episode_config import (
    load_native_episode_config,
)
from test_e35_earnings_native_episode_wire import NORMALISERS, _values

ROOT = Path(__file__).resolve().parents[2]


def test_e22_layer_contains_only_generic_direct_policy_not_e21_sources():
    hooks = cm.resolve_carrier_hooks("earnings22", repo_root=ROOT)
    layer = hooks.lock_layer()
    raw = json.loads((ROOT / "configs/baseline/e22-native-window-direct-base-v1.json").read_text())
    assert set(raw) == set(cm.DIRECT_LAYER_KEYS)
    assert layer == cm.resolve_carrier_hooks("earnings").lock_layer()
    assert hooks.carrier_components == {}
    assert hooks.current_lock is None and hooks.lock_versions is None
    assert hooks.roster_pin_paths == ()


def test_e22_numeric_units_accept_no_conec_entity_terms():
    hooks = cm.resolve_carrier_hooks("earnings22")
    label, units, parsed = hooks.delivered_units("Acme reported 23 sales")
    assert label is None and parsed
    assert [(unit.type, unit.filler) for unit in units] == [("numeric", "23")]
    assert hooks.tool_offer_units("Acme reported 23 sales") == (label, units, parsed)
    assert hooks.delivered_units("") == (None, (), False)
    with pytest.raises(TypeError):
        hooks.delivered_units("Acme reported 23 sales", entity_terms=("Acme",))


@pytest.mark.parametrize("carrier", NORMALISERS)
@pytest.mark.parametrize("text, expected", [
    ("Transcript:  Revenue\n was 23", "Revenue was 23"),
    ("<answer>Revenue was 23</answer>", "Revenue was 23"),
    ("```text\nRevenue was 23\n```", "Revenue was 23"),
    ("Revenue was twenty three", "Revenue was twenty three"),
    ("We said Answer: revenue fell", "We said Answer: revenue fell"),
])
def test_earnings_hygiene_preserves_words_and_separates_carrier_receipts(carrier, text, expected):
    rule = DELIVERY_NORMALISERS.resolve(NORMALISERS[carrier])
    result = rule(text)
    assert result.text == expected
    assert result.changed == (text != expected)
    assert result.receipt["carrier_lock_key"] == carrier
    assert result.receipt["normaliser_id"] == NORMALISERS[carrier]
    assert result.receipt["rule_id"] == "earnings-text-hygiene-v1"


@pytest.mark.parametrize("carrier", NORMALISERS)
@pytest.mark.parametrize("text", ["", "Transcript:   ", "<answer> </answer>"])
def test_empty_delivery_is_not_invented(carrier, text):
    with pytest.raises(DeliveryNormaliserError, match="abstain"):
        DELIVERY_NORMALISERS.resolve(NORMALISERS[carrier])(text)


@pytest.mark.parametrize("carrier", NORMALISERS)
def test_carriers_cannot_arm_each_others_normaliser(carrier):
    values = _values(armed=True, carrier=carrier)
    other = next(key for key in NORMALISERS if key != carrier)
    values["native_episode"]["deliver_normaliser"]["normaliser"] = NORMALISERS[other]
    with pytest.raises(ValueError, match="carrier"):
        load_native_episode_config(values, default_phase_program("phase-native-review-revise-acquire-v1"))


def test_e22_default_names_only_its_own_rule():
    hooks = cm.resolve_carrier_hooks("earnings22")
    assert hooks.default_deliver_normaliser() == NORMALISERS["earnings22-original"]


@pytest.mark.parametrize("spec", cm.COMPONENT_CATALOGUE, ids=lambda spec: spec.component_id)
def test_e22_direct_layer_refuses_every_armed_component(spec):
    block = {"module_id": cm.CONSUMPTION_MODULE_ID, "profile": "earnings22",
             "components": [{"component_id": spec.component_id, "state": "on",
                             "admitted_by": "synthetic negative test", "record": "README.md",
                             "params": {key: None for key in spec.params}}], "columns": []}
    reason = "direct layer" if "on" in spec.states else "cannot be 'on'"
    with pytest.raises(cm.ConsumptionModuleConfigError, match=reason):
        cm.compile_module(block, cm.resolve_carrier_hooks("earnings22"))


@pytest.mark.parametrize("carrier", NORMALISERS)
@pytest.mark.parametrize("tamper", [None, "carrier", "receipt_carrier", "rule", "text"])
def test_earnings_sealed_delivery_checks_carrier_and_bytes(carrier, tamper):
    from speech_aware_evidence_acquisition.core.bundle import BundleError
    from speech_aware_evidence_acquisition.core.bundle.outputs import _verify_delivery_normalisation

    raw = "Transcript: Revenue was 23"
    outcome = DELIVERY_NORMALISERS.resolve(NORMALISERS[carrier])(raw)
    block = dict(outcome.receipt)
    row = {"sample_id": "synthetic:call:1", "text": outcome.text, "carrier_lock_key": carrier}
    other = next(key for key in NORMALISERS if key != carrier)
    if tamper == "carrier":
        row["carrier_lock_key"] = other
    elif tamper == "receipt_carrier":
        block["carrier_lock_key"] = other
    elif tamper == "rule":
        block["normaliser_id"] = NORMALISERS[other]
        block["carrier_lock_key"] = other
    elif tamper == "text":
        row["text"] = "Revenue was 32"
    if tamper:
        with pytest.raises(BundleError):
            _verify_delivery_normalisation(row, block, {"text": raw})
    else:
        _verify_delivery_normalisation(row, block, {"text": raw})


@pytest.mark.parametrize("carrier", NORMALISERS)
def test_offline_replay_uses_transcript_hygiene_without_fabricating_slu_diagnostics(tmp_path, carrier):
    from speech_aware_evidence_acquisition.analysis.deliver_normaliser_replay import replay, replay_row

    rule = DELIVERY_NORMALISERS.resolve(NORMALISERS[carrier])
    row = {"sample_id": "synthetic:call:1", "text": "Transcript: Revenue was 23"}
    before = copy.deepcopy(row)
    first = replay_row(row, normaliser=rule)
    assert row == before
    assert first["text"] == "Revenue was 23"
    for key in ("labels_changed", "fillers_changed", "label_branch"):
        assert first[key] is None
    source = tmp_path / "synthetic.jsonl"
    source.write_text(json.dumps(row) + "\n")
    source_bytes = source.read_bytes()
    report = replay(outputs_path=source, normaliser_id=rule.id, output_dir=tmp_path / "first")
    assert report["rows_changed"] == 1
    for key in ("rows_label_changed", "rows_filler_changed", "entities_filler_changed", "rows_unparsed"):
        assert report[key] is None
    second = replay(outputs_path=tmp_path / "first/outputs.jsonl", normaliser_id=rule.id,
                    output_dir=tmp_path / "second")
    assert second["rows_changed"] == 0
    assert second["rows_unparsed"] is None
    assert source.read_bytes() == source_bytes


def test_e22_replay_cli_preserves_source_and_refuses_overwrite(tmp_path, capsys):
    from speech_aware_evidence_acquisition.analysis.deliver_normaliser_replay import (
        DeliverNormaliserReplayError, main,
    )

    source = tmp_path / "synthetic.jsonl"
    source.write_text(json.dumps({"sample_id": "synthetic:1", "text": "Revenue was 23"}) + "\n")
    args = ["--outputs", str(source), "--normaliser", NORMALISERS["earnings22-original"],
            "--output-dir", str(tmp_path / "replay")]
    assert main(args) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["carrier_lock_key"] == "earnings22-original"
    assert report["rows_changed"] == 0 and report["rows_unparsed"] is None
    with pytest.raises(DeliverNormaliserReplayError, match="overwrite"):
        main(args)


@pytest.mark.parametrize("text", ["not json\n", "[]\n", '{"text":"test"}\n',
                                 '{"sample_id":"duplicate"}\n{"sample_id":"duplicate"}\n'])
def test_e22_replay_refuses_invalid_rows_before_writing(tmp_path, text):
    from speech_aware_evidence_acquisition.analysis.deliver_normaliser_replay import (
        DeliverNormaliserReplayError, replay,
    )

    source = tmp_path / "synthetic.jsonl"
    source.write_text(text)
    target = tmp_path / "replay"
    with pytest.raises(DeliverNormaliserReplayError):
        replay(outputs_path=source, normaliser_id=NORMALISERS["earnings22-original"], output_dir=target)
    assert not target.exists()
    assert source.read_text() == text
