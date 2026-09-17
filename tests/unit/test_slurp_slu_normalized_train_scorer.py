"""``slurp-slu-f1-normalized-v1-train``: the TRAIN-gold sibling of the
symmetric-normalised SLU scorer (owner decision 14 of 2026-09-17,
``docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md``).

Three properties, and nothing else:

(a) on one synthetic TRAIN-shaped fixture the TRAIN sibling reproduces the DEV
    scorer's arithmetic EXACTLY on identical rows -- same predictions, same
    gold content, only the split label (and therefore the gold each resolves)
    differing;
(b) it refuses a ``devel`` sample id the same way the DEV binding refuses a
    TRAIN one, naming its own split;
(c) the registry entry resolves in ``core.base`` and is a binding of the same
    implementation, never a second one.

Model-free. The official ``evaluate.py`` subprocess is stubbed exactly as
``tests/unit/test_scorers_slurp_official.py`` stubs it; the identity check the
normalized column depends on is satisfied by echoing the port's OWN micro
numbers back, which is what the real subprocess returns whenever the port is
faithful to it. No corpus byte and no model is touched.
"""

from __future__ import annotations

import json

import pytest

from speech_aware_evidence_acquisition.core import scorers  # noqa: F401 (registration)
from speech_aware_evidence_acquisition.core.base import SCORERS
from speech_aware_evidence_acquisition.data.slurp import SlurpRecord
from speech_aware_evidence_acquisition.reproduction import slurp_official_eval as soe
from speech_aware_evidence_acquisition.reproduction import slurp_slot_normalizer as ssn
from speech_aware_evidence_acquisition.reproduction.slurp_official_eval import (
    OfficialSluResult,
    SlurpOfficialEvalError,
    score_slurp_outputs_slu_normalized,
    score_slurp_outputs_slu_normalized_train,
)
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import SlotEntity

# Gold fillers are stored ALREADY lower-cased by ``data.slurp._entity_filler``
# (the official ``release2prediction``'s own load-time behaviour), while a
# predicted filler is never lower-cased. Row 1 is therefore the case and
# punctuation asymmetry the A1 audit measured: the official column scores it as
# a partial match, the symmetric normalizer scores it as an exact one. Row 2 is
# a control that both columns call exact.
_UTTERANCES = (
    ("000001", "rec-a", "alarm", "set", "time", "seven a.m.", "Seven A.M."),
    ("000002", "rec-b", "calendar", "query", "date", "tomorrow", "tomorrow"),
)


def _gold(split: str) -> list[SlurpRecord]:
    records = []
    for utterance, recording, scenario, action, slot_type, gold_filler, _pred in _UTTERANCES:
        sample_id = f"slurp:{split}:{utterance}:{recording}"
        records.append(
            SlurpRecord(
                sample_id=sample_id,
                utterance_id=utterance,
                split=split,
                media_relpath=f"slurp_real/{sample_id}.flac",
                audio_seconds=1.5,
                scenario=scenario,
                action=action,
                intent=f"{scenario}_{action}",
                entities=(SlotEntity(slot_type, gold_filler),),
            )
        )
    return records


def _outputs(tmp_path, split: str):
    path = tmp_path / f"{split}.outputs.jsonl"
    lines = []
    for utterance, recording, scenario, action, slot_type, _gold_filler, pred in _UTTERANCES:
        lines.append(
            json.dumps(
                {
                    "sample_id": f"slurp:{split}:{utterance}:{recording}",
                    "carrier_lock_key": "slurp",
                    "text": json.dumps(
                        {
                            "scenario": scenario,
                            "action": action,
                            "entities": [{"type": slot_type, "filler": pred}],
                        }
                    ),
                }
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _empty_inventory() -> ssn.SlotNormalizerInventory:
    """A TRAIN-mined inventory with nothing learned: rung ``R3`` is inert, so
    the fixture exercises ``R0``-``R2`` only and needs no corpus read."""

    return ssn.SlotNormalizerInventory(
        source_split="train",
        utterance_count=0,
        min_witnesses=1,
        fillers={},
        leading_tokens=(),
        rejected_tokens=(),
        witnesses={},
        witness_examples={},
        source_identity_hash="0" * 64,
    )


def _official_result(port_micro) -> OfficialSluResult:
    raw = {
        key: {
            "official_label": key,
            "precision": 0.0,
            "recall": 0.0,
            "f_measure": 0.0,
            "tp": 0.0,
            "fp": 0.0,
            "fn": 0.0,
        }
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
        scenario_accuracy=port_micro["scenario_accuracy"],
        action_accuracy=port_micro["action_accuracy"],
        intent_accuracy=port_micro["intent_accuracy"],
        slu_f1=port_micro["slu_f1"],
        span_f1=port_micro["span_f1"],
        raw=raw,
        stdout="stubbed official evaluate.py",
        command=("python", "evaluate.py"),
    )


_ZERO_MICRO = {
    "slu_f1": 0.0,
    "span_f1": 0.0,
    "scenario_accuracy": 0.0,
    "action_accuracy": 0.0,
    "intent_accuracy": 0.0,
}


@pytest.fixture()
def slurp_stubs(monkeypatch, tmp_path):
    """Split-aware synthetic gold, an inert TRAIN normalizer inventory, and an
    official subprocess that echoes the port once the probe pass has read it."""

    monkeypatch.setattr(
        soe,
        "load_slurp_split",
        lambda lock, root, split_id, *, allow_heldout=False, allow_synthetic=False: _gold(
            split_id
        ),
    )
    monkeypatch.setattr(soe, "official_evaluator_root", lambda root: tmp_path / "unused")
    monkeypatch.setattr(
        ssn, "load_slot_normalizer_inventory", lambda lock, root, **kwargs: _empty_inventory()
    )

    echo = {"micro": None}

    def run(gold_path, pred_path, *, evaluator_root, python_executable=None, average="micro"):
        # The probe pass returns zeros: ``score_slurp_outputs_official``
        # REPORTS an identity mismatch, it never raises on one, so the probe
        # can read the port's own micro numbers out of its aggregate.
        return _official_result(echo["micro"] or _ZERO_MICRO)

    monkeypatch.setattr(soe, "run_official_evaluate", run)
    return echo


def test_train_sibling_reproduces_the_dev_scorer_arithmetic_on_identical_rows(
    tmp_path, slurp_stubs
):
    train_outputs = _outputs(tmp_path, "train")
    devel_outputs = _outputs(tmp_path, "devel")

    probe = soe.score_slurp_outputs_official(train_outputs, {}, tmp_path, split_id="train")
    slurp_stubs["micro"] = probe["aggregate"]["port_micro"]

    train = score_slurp_outputs_slu_normalized_train(train_outputs, {}, tmp_path)
    devel = score_slurp_outputs_slu_normalized(devel_outputs, {}, tmp_path)

    # The document each sibling returns names the gold it resolved.
    assert train["aggregate"]["split_id"] == "train"
    assert devel["aggregate"]["split_id"] == "devel"

    # Both computed their symmetric column on a passing identity check.
    assert train["aggregate"]["identity_check"]["passed"] is True
    assert devel["aggregate"]["identity_check"]["passed"] is True

    # Same schema: the TRAIN sibling adds and removes no key anywhere.
    assert set(train) == set(devel)
    assert set(train["aggregate"]) == set(devel["aggregate"])
    assert set(train["aggregate"]["normalized"]) == set(devel["aggregate"]["normalized"])

    # Same arithmetic: every symmetric aggregate number and every rung.
    assert train["aggregate"]["normalized"] == devel["aggregate"]["normalized"]
    assert train["aggregate"]["normalized_per_rule"] == devel["aggregate"]["normalized_per_rule"]

    # Same arithmetic per row, in row order (only the split label differs).
    assert [row["normalized"] for row in train["per_sample"]] == [
        row["normalized"] for row in devel["per_sample"]
    ]
    assert [row["sample_id"].split(":")[1] for row in train["per_sample"]] == ["train", "train"]
    assert [row["sample_id"].split(":")[1] for row in devel["per_sample"]] == ["devel", "devel"]

    # And the official half agrees too, so nothing about the TRAIN binding
    # moved the primary column either.
    assert train["aggregate"]["port_micro"] == devel["aggregate"]["port_micro"]

    # The fixture is not trivial: the symmetric column scores the case and
    # punctuation alignment of row 1 at zero, so it sits strictly above the
    # official one. That gap is the representation-alignment share decision 7
    # of 2026-09-17 asks every report to state.
    symmetric = train["aggregate"]["normalized"]["micro"]
    assert symmetric["span_f1"] == pytest.approx(1.0)
    assert train["aggregate"]["port_micro"]["span_f1"] < symmetric["span_f1"]
    assert train["aggregate"]["port_micro"]["slu_f1"] < symmetric["slu_f1"]


def test_train_sibling_refuses_devel_ids_the_way_the_dev_sibling_refuses_train_ids(
    tmp_path, slurp_stubs
):
    train_outputs = _outputs(tmp_path, "train")
    devel_outputs = _outputs(tmp_path, "devel")

    with pytest.raises(SlurpOfficialEvalError) as train_refusal:
        score_slurp_outputs_slu_normalized_train(devel_outputs, {}, tmp_path)
    assert "is not part of SLURP split 'train'" in str(train_refusal.value)
    assert "slurp:devel:000001:rec-a" in str(train_refusal.value)

    with pytest.raises(SlurpOfficialEvalError) as devel_refusal:
        score_slurp_outputs_slu_normalized(train_outputs, {}, tmp_path)
    assert "is not part of SLURP split 'devel'" in str(devel_refusal.value)
    assert "slurp:train:000001:rec-a" in str(devel_refusal.value)


def test_train_sibling_is_registered_and_resolves_in_core_base():
    names = SCORERS.names()
    assert "slurp-slu-f1-normalized-v1-train" in names
    assert "slurp-slu-f1-normalized-v1" in names

    resolved = SCORERS.resolve("slurp-slu-f1-normalized-v1-train")
    assert resolved is score_slurp_outputs_slu_normalized_train
    # A sibling, never an alias: the DEV id must keep resolving to the DEV gold.
    assert resolved is not SCORERS.resolve("slurp-slu-f1-normalized-v1")


def test_train_sibling_runs_through_the_uniform_three_positional_signature(
    tmp_path, slurp_stubs
):
    """The registry entry is callable exactly like every other scorer --
    ``SCORERS.resolve(name)(outputs_path, lock, root)`` -- which is the call
    convention ``core.scorers.score_bundle`` makes."""

    train_outputs = _outputs(tmp_path, "train")
    probe = soe.score_slurp_outputs_official(train_outputs, {}, tmp_path, split_id="train")
    slurp_stubs["micro"] = probe["aggregate"]["port_micro"]

    result = SCORERS.resolve("slurp-slu-f1-normalized-v1-train")(train_outputs, {}, tmp_path)

    assert result["aggregate"]["split_id"] == "train"
    assert result["aggregate"]["normalized"]["scorer_id"] == ssn.SLURP_SLU_NORMALIZED_SCORER_ID
    assert result["aggregate"]["normalized"]["applies_to"] == (
        "gold and prediction alike, before the official distance blocks"
    )
    assert result["aggregate"]["normalized"]["replaces_official"] is False
    assert len(result["per_sample"]) == 2
