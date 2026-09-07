"""The ``@<variant>`` gold-id rail for Audio2Tool and SLURP (2026-09-07).

Section 6.2 of ``docs/readiness/2026-09-07-cross-carrier-silence-tail-v1-
preregistration.md`` names this as a precondition of two of the three cells:
a derived-media population carries ``<published id>@<variant>`` ids, and both
carriers' gold lookups resolved by EXACT ``sample_id``, so an ``@ts2`` row
failed closed at scoring. Earnings-22 had already solved the same problem
with ``reproduction.esb_reference.published_segment_key``; the rule now lives
once, in ``data.variant_ids.published_sample_key``, and every gold lookup on
both carriers goes through it.

Three properties, and the file is organised around them:

1. **Unsuffixed ids are unchanged.** Proved on REAL sealed manifests, not on
   fixtures: the sealed Audio2Tool official-protocol 400 and the sealed SLURP
   DEV-1000 closed-list run are scored as they sit and must still reproduce
   their own published anchors to the digit.
2. **Suffixed ids resolve, to exactly the same gold.** The same sealed rows
   with ``@ts2`` appended to every id must produce per-sample entries and
   aggregates identical to the unsuffixed ones.
3. **A foreign id still refuses.** The rail strips a suffix; it never widens
   a gold closure. An id whose PUBLISHED key is outside the frozen receipt
   refuses exactly as before, and the refusal names the RAW id that was
   flown.

The sealed-manifest tests SKIP (never soften an assertion) when the umbrella
lock, ``$SPEECHRL_DATA_DIR`` or a sealed artifact is absent -- the same
convention ``test_audio2tool_official_scorer.py`` already uses for the pinned
Audio2Tool clone. Everything else runs everywhere on synthetic fixtures.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

import pytest

import speech_aware_evidence_acquisition.core  # noqa: F401 (populate registries)
from speech_aware_evidence_acquisition.core.base import SCORERS
from speech_aware_evidence_acquisition.data.lock import (
    AssetResolutionError,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.data.slurp import SlurpRecord
from speech_aware_evidence_acquisition.data.variant_ids import (
    VARIANT_ID_SEPARATOR,
    published_sample_key,
    variant_suffix,
)
from speech_aware_evidence_acquisition.rails.adapters.audio2tool import (
    Audio2ToolAdapter,
    Audio2ToolSample,
)
from speech_aware_evidence_acquisition.rails.obs import AudioRef
from speech_aware_evidence_acquisition.reproduction import slurp_official_eval as soe
from speech_aware_evidence_acquisition.reproduction.a2t_scorer import (
    ToolCallScoringError,
    score_audio2tool_outputs,
    score_audio2tool_outputs_official,
    score_audio2tool_outputs_v2,
)
from speech_aware_evidence_acquisition.reproduction.esb_reference import (
    published_segment_key,
)
from speech_aware_evidence_acquisition.reproduction.slurp_official_eval import (
    OfficialSluResult,
    PredictedSlurpSample,
    SlurpOfficialEvalError,
    write_official_inputs,
)
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import SlotEntity

A2T_SEALED_OUTPUTS = (
    "runs/SAEA-A2T-OFFICIAL-PROTOCOL-REPLICATION-V1/"
    "attempt-20260904T135250Z-rofficialraw/"
    "SAEA-A2T-OFFICIAL-PROTOCOL-REPLICATION-V1.outputs.jsonl"
)
SLURP_SEALED_OUTPUTS = (
    "runs/SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1/"
    "attempt-20260905T060424Z-2c5596/"
    "SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1.outputs.jsonl"
)

#: docs/readiness/2026-09-07-cross-carrier-silence-tail-v1-preregistration.md
#: section 1.3, the sealed Audio2Tool comparator's own published anchors.
A2T_SEALED_TIER_ACCURACY = {
    "tier1_direct": 60.0,
    "tier2_parametric": 74.0,
    "tier3_multi_intent": 72.0,
    "tier4_implicit": 28.0,
    "tier5_needle": 78.0,
    "tier6_correction": 84.0,
    "tier7_multiturn": 58.0,
    "tier8_intent_blending": 34.0,
}

#: The same preregistration, section 1.2, for SLURP.
SLURP_SEALED = {
    "scenario_accuracy": 0.8260,
    "action_accuracy": 0.7460,
    "intent_accuracy": 0.7310,
}


# ---------------------------------------------------------------------------
# 0. The rule itself, and that it is ONE rule
# ---------------------------------------------------------------------------


def test_the_rule_strips_a_variant_suffix_and_is_inert_otherwise() -> None:
    assert VARIANT_ID_SEPARATOR == "@"
    assert published_sample_key("tier1_direct:000045") == "tier1_direct:000045"
    assert published_sample_key("tier1_direct:000045@ts2") == "tier1_direct:000045"
    assert published_sample_key("slurp:devel:000011:audio-1") == "slurp:devel:000011:audio-1"
    assert published_sample_key("slurp:devel:000011:audio-1@ts2") == (
        "slurp:devel:000011:audio-1"
    )
    assert published_sample_key("4320211#w0001@ts2") == "4320211#w0001"
    # Only the FIRST separator splits, so a second one cannot smuggle an id back.
    assert published_sample_key("a@b@c") == "a"
    assert published_sample_key("a@") == "a"


def test_variant_suffix_is_a_diagnostic_and_never_a_lookup_key() -> None:
    assert variant_suffix("tier1_direct:000045") is None
    assert variant_suffix("tier1_direct:000045@ts2") == "ts2"
    assert variant_suffix("tier1_direct:000045@") == ""


def test_the_earnings22_name_and_the_shared_rail_are_the_same_rule() -> None:
    """``published_segment_key`` is the Earnings-22 SPELLING of this rule and
    now delegates to it, so the three carriers cannot drift apart."""

    for sample_id in (
        "4453225-103",
        "4453225-103@ts2",
        "4453225-103@p30",
        "4453225-103@bx1",
        "4453225-103@a@b",
        "tier1_direct:000045@ts2",
        "slurp:devel:000011:audio-1497266596@ts2",
    ):
        assert published_segment_key(sample_id) == published_sample_key(sample_id)


def test_the_rule_refuses_a_non_string_id() -> None:
    with pytest.raises(TypeError):
        published_sample_key(None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 1. Audio2Tool -- the adapter's flight-time gold lookup
# ---------------------------------------------------------------------------


def _sample(sample_id: str) -> Audio2ToolSample:
    return Audio2ToolSample(
        sample_id=sample_id,
        audio_ref=AudioRef(path="datasets/audio2tool/x.wav", sha256="00" * 32),
        audio_seconds=1.0,
        media_relpath="datasets/audio2tool/x.wav",
    )


def _adapter(world) -> Audio2ToolAdapter:
    return Audio2ToolAdapter(
        load_lock(world.lock_path), world.data_root, repo_root=world.repo_root
    )


def test_adapter_gold_is_unchanged_for_an_unsuffixed_id(audio2tool_world) -> None:
    gold = _adapter(audio2tool_world).gold(_sample("tier1_direct:000001"))
    assert gold and gold[0].name


def test_adapter_gold_resolves_a_variant_id_to_the_published_sample(
    audio2tool_world,
) -> None:
    adapter = _adapter(audio2tool_world)
    assert adapter.gold(_sample("tier1_direct:000001@ts2")) == adapter.gold(
        _sample("tier1_direct:000001")
    )


def test_adapter_gold_still_refuses_a_foreign_id_carrying_a_variant_suffix(
    audio2tool_world,
) -> None:
    """The suffix is not a skeleton key: stripping it must not invent gold for
    a published id the frozen receipt never named."""

    with pytest.raises(ValueError) as error:
        _adapter(audio2tool_world).gold(_sample("tier1_direct:999999@ts2"))
    # The RAW id is what the trace and the receipt must show.
    assert "tier1_direct:999999@ts2" in str(error.value)


# ---------------------------------------------------------------------------
# 2. Audio2Tool -- the three registered scorers
# ---------------------------------------------------------------------------

A2T_SCORERS = (
    ("a2t-toolcall", score_audio2tool_outputs),
    ("a2t-toolcall-v2", score_audio2tool_outputs_v2),
    ("a2t-toolcall-official", score_audio2tool_outputs_official),
)


def _write_outputs(path: Path, rows) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
        newline="\n",
    )
    return path


def _drop_suffix(entry):
    return {**entry, "sample_id": published_sample_key(str(entry["sample_id"]))}


@pytest.mark.parametrize("name,scorer", A2T_SCORERS, ids=[name for name, _ in A2T_SCORERS])
def test_a2t_scorers_score_a_variant_id_exactly_as_its_published_sample(
    audio2tool_world, tmp_path, name, scorer
) -> None:
    assert name in SCORERS.names()
    lock = load_lock(audio2tool_world.lock_path)
    # One row, and deliberately the one whose gold tool the synthetic
    # world's two-row registry actually carries: a2t-scorer-v2 refuses a
    # drifted registry, which is its own (correct) behaviour and not what is
    # under test here. The eight-tier, 400-row breadth is covered on the
    # SEALED manifest below.
    rows = [{"sample_id": "tier1_direct:000001", "text": "setLighting()"}]
    plain = scorer(
        _write_outputs(tmp_path / "plain.outputs.jsonl", rows),
        lock,
        audio2tool_world.data_root,
        repo_root=audio2tool_world.repo_root,
    )
    variant = scorer(
        _write_outputs(
            tmp_path / "ts2.outputs.jsonl",
            [{**row, "sample_id": row["sample_id"] + "@ts2"} for row in rows],
        ),
        lock,
        audio2tool_world.data_root,
        repo_root=audio2tool_world.repo_root,
    )
    assert plain["aggregate"] == variant["aggregate"]
    assert plain["per_sample"] == [_drop_suffix(entry) for entry in variant["per_sample"]]
    # The RAW id is what the score file records, so a receipt still says which
    # media was flown.
    assert [entry["sample_id"] for entry in variant["per_sample"]] == [
        "tier1_direct:000001@ts2"
    ]


@pytest.mark.parametrize("name,scorer", A2T_SCORERS, ids=[name for name, _ in A2T_SCORERS])
def test_a2t_scorers_still_refuse_a_foreign_published_key(
    audio2tool_world, tmp_path, name, scorer
) -> None:
    del name
    with pytest.raises(ToolCallScoringError) as error:
        scorer(
            _write_outputs(
                tmp_path / "foreign.outputs.jsonl",
                [{"sample_id": "tier1_direct:999999@ts2", "text": "setLighting()"}],
            ),
            load_lock(audio2tool_world.lock_path),
            audio2tool_world.data_root,
            repo_root=audio2tool_world.repo_root,
        )
    assert "tier1_direct:999999@ts2" in str(error.value)


# ---------------------------------------------------------------------------
# 3. SLURP -- the official evaluator's gold lookup and its "file" pairing
# ---------------------------------------------------------------------------


def _slurp_gold(sample_id: str) -> SlurpRecord:
    return SlurpRecord(
        sample_id=sample_id,
        utterance_id=sample_id.split(":")[2],
        split="devel",
        media_relpath=f"slurp_real/{sample_id}.flac",
        audio_seconds=1.5,
        scenario="alarm",
        action="set",
        intent="alarm_set",
        entities=(SlotEntity("time", "seven am"),),
    )


def _official_result() -> OfficialSluResult:
    raw = {
        key: {
            "official_label": key,
            "precision": 1.0,
            "recall": 1.0,
            "f_measure": 1.0,
            "tp": 1.0,
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
        scenario_accuracy=1.0,
        action_accuracy=1.0,
        intent_accuracy=1.0,
        slu_f1=1.0,
        span_f1=1.0,
        raw=raw,
        stdout="fake",
        command=("python", "evaluate.py"),
    )


def _bind_synthetic_slurp(monkeypatch, record: SlurpRecord, seen: list) -> None:
    monkeypatch.setattr(
        soe,
        "load_slurp_split",
        lambda lock, root, split_id, *, allow_heldout=False, allow_synthetic=False: [record],
    )
    monkeypatch.setattr(soe, "official_evaluator_root", lambda root: Path("unused"))

    def fake_run(gold_path, pred_path, *, evaluator_root, python_executable=None, average="micro"):
        seen.append(
            (
                [json.loads(line) for line in gold_path.read_text(encoding="utf-8").splitlines()],
                [json.loads(line) for line in pred_path.read_text(encoding="utf-8").splitlines()],
            )
        )
        return _official_result()

    monkeypatch.setattr(soe, "run_official_evaluate", fake_run)


def _slurp_row(sample_id: str, record: SlurpRecord) -> dict:
    return {
        "sample_id": sample_id,
        "text": json.dumps(
            {
                "scenario": record.scenario,
                "action": record.action,
                "entities": [
                    {"type": entity.type, "filler": entity.filler}
                    for entity in record.entities
                ],
            }
        ),
    }


def test_slurp_official_scorer_pairs_a_variant_row_against_the_published_gold(
    tmp_path, monkeypatch
) -> None:
    record = _slurp_gold("slurp:devel:000001:rec-a")
    seen: list = []
    _bind_synthetic_slurp(monkeypatch, record, seen)

    outputs = _write_outputs(
        tmp_path / "ts2.outputs.jsonl", [_slurp_row(record.sample_id + "@ts2", record)]
    )
    result = SCORERS.resolve("slurp-slu-official")(outputs, {}, tmp_path)

    assert result["aggregate"]["identity_check"]["passed"] is True
    # The per-sample row keeps the RAW id it was flown under ...
    assert [entry["sample_id"] for entry in result["per_sample"]] == [
        "slurp:devel:000001:rec-a@ts2"
    ]
    # ... while both sides of the official evaluator's own "file" key carry the
    # PUBLISHED id, which is the key evaluate.py pairs on.
    gold_docs, pred_docs = seen[-1]
    assert [doc["recordings"][0]["file"] for doc in gold_docs] == [record.sample_id]
    assert [doc["file"] for doc in pred_docs] == [record.sample_id]


def test_slurp_official_scorer_is_unchanged_for_an_unsuffixed_row(
    tmp_path, monkeypatch
) -> None:
    record = _slurp_gold("slurp:devel:000001:rec-a")
    seen: list = []
    _bind_synthetic_slurp(monkeypatch, record, seen)
    outputs = _write_outputs(
        tmp_path / "plain.outputs.jsonl", [_slurp_row(record.sample_id, record)]
    )
    result = SCORERS.resolve("slurp-slu-official")(outputs, {}, tmp_path)
    assert [entry["sample_id"] for entry in result["per_sample"]] == [record.sample_id]
    gold_docs, pred_docs = seen[-1]
    assert [doc["recordings"][0]["file"] for doc in gold_docs] == [record.sample_id]
    assert [doc["file"] for doc in pred_docs] == [record.sample_id]


def test_slurp_official_scorer_still_refuses_a_foreign_published_key(
    tmp_path, monkeypatch
) -> None:
    record = _slurp_gold("slurp:devel:000001:rec-a")
    _bind_synthetic_slurp(monkeypatch, record, [])
    outputs = _write_outputs(
        tmp_path / "foreign.outputs.jsonl",
        [_slurp_row("slurp:devel:999999:rec-z@ts2", record)],
    )
    with pytest.raises(SlurpOfficialEvalError) as error:
        SCORERS.resolve("slurp-slu-official")(outputs, {}, tmp_path)
    assert "slurp:devel:999999:rec-z@ts2" in str(error.value)


def test_two_variants_of_one_published_row_cannot_be_scored_together(tmp_path) -> None:
    """A manifest that mixed a sealed row with its own ``@ts2`` twin would put
    two hypotheses against ONE gold row in the official evaluator. That fails
    closed at the prediction writer rather than silently scoring one of them."""

    record = _slurp_gold("slurp:devel:000001:rec-a")
    predictions = [
        PredictedSlurpSample(
            sample_id=record.sample_id,
            scenario=record.scenario,
            action=record.action,
            entities=record.entities,
        ),
        PredictedSlurpSample(
            sample_id=record.sample_id,
            scenario=record.scenario,
            action=record.action,
            entities=record.entities,
        ),
    ]
    with pytest.raises(SlurpOfficialEvalError):
        write_official_inputs([record], predictions, tmp_path)


# ---------------------------------------------------------------------------
# 4. The sealed manifests: unsuffixed unchanged, suffixed identical
# ---------------------------------------------------------------------------


def _real_lock():
    try:
        return load_lock(umbrella_lock_path())
    except AssetResolutionError as error:
        pytest.skip(f"the umbrella datasets lock is not reachable from here: {error}")


def _sealed(relpath: str) -> tuple[Path, Path]:
    from speech_aware_evidence_acquisition.data.lock import data_root

    try:
        root = data_root()
    except Exception as error:  # noqa: BLE001 -- environment, not behaviour
        pytest.skip(f"$SPEECHRL_DATA_DIR is not resolvable here: {error}")
    outputs = root / relpath
    if not outputs.is_file():
        pytest.skip(f"the sealed outputs artifact is absent on this machine: {outputs}")
    return root, outputs


def _assert_close(left, right, path: str = "aggregate") -> None:
    """Structural equality, with floats compared to 1e-9."""

    if isinstance(left, Mapping) and isinstance(right, Mapping):
        assert set(left) == set(right), path
        for key in sorted(left):
            _assert_close(left[key], right[key], f"{path}/{key}")
    elif isinstance(left, (list, tuple)) and isinstance(right, (list, tuple)):
        assert len(left) == len(right), path
        for index, (one, other) in enumerate(zip(left, right)):
            _assert_close(one, other, f"{path}[{index}]")
    elif isinstance(left, float) or isinstance(right, float):
        assert left == pytest.approx(right, abs=1e-9, rel=1e-9), path
    else:
        assert left == right, path


def _sealed_rows(outputs: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in outputs.read_text(encoding="utf-8").split("\n")
        if line.strip()
    ]


def test_the_sealed_audio2tool_400_is_byte_for_byte_unchanged_and_its_variant_matches(
    tmp_path,
) -> None:
    root, outputs = _sealed(A2T_SEALED_OUTPUTS)
    lock = _real_lock()
    rows = _sealed_rows(outputs)
    assert len(rows) == 400

    repo_root = Path(__file__).resolve().parents[2]
    plain_path = _write_outputs(tmp_path / "sealed.outputs.jsonl", rows)
    variant_path = _write_outputs(
        tmp_path / "sealed-ts2.outputs.jsonl",
        [{**row, "sample_id": row["sample_id"] + "@ts2"} for row in rows],
    )
    for _name, scorer in A2T_SCORERS:
        plain = scorer(plain_path, lock, root, repo_root=repo_root)
        variant = scorer(variant_path, lock, root, repo_root=repo_root)
        assert plain["aggregate"] == variant["aggregate"]
        assert plain["per_sample"] == [
            _drop_suffix(entry) for entry in variant["per_sample"]
        ]

    # The published anchors of the sealed comparator, to the digit -- which is
    # what "unsuffixed ids are unchanged" actually has to mean.
    aggregate = score_audio2tool_outputs_official(
        plain_path, lock, root, repo_root=repo_root
    )["aggregate"]
    assert round(aggregate["tool_accuracy"] * 100, 4) == 61.0
    assert round(aggregate["exact_match"] * 100, 4) == 20.25
    assert round(aggregate["parse_rate"] * 100, 4) == 99.75
    assert aggregate["rows_with_multiple_call_matches"] == 52
    assert {
        tier: round(view["tool_accuracy"] * 100, 4)
        for tier, view in aggregate["per_tier"].items()
    } == A2T_SEALED_TIER_ACCURACY


def test_the_sealed_slurp_dev1000_is_byte_for_byte_unchanged_and_its_variant_matches(
    tmp_path,
) -> None:
    root, outputs = _sealed(SLURP_SEALED_OUTPUTS)
    lock = _real_lock()
    rows = _sealed_rows(outputs)
    assert len(rows) == 1000

    scorer = SCORERS.resolve("slurp-slu-official-projected-v2")
    plain = scorer(_write_outputs(tmp_path / "sealed.outputs.jsonl", rows), lock, root)
    variant = scorer(
        _write_outputs(
            tmp_path / "sealed-ts2.outputs.jsonl",
            [{**row, "sample_id": row["sample_id"] + "@ts2"} for row in rows],
        ),
        lock,
        root,
    )
    assert plain["per_sample"] == [_drop_suffix(entry) for entry in variant["per_sample"]]

    # ``official.command`` names the per-invocation temp directory the two
    # evaluator subprocesses were handed, so it differs between ANY two runs of
    # the same scorer and is excluded here rather than asserted equal. Every
    # number is compared.
    def without_command(aggregate):
        # ``command`` names the per-invocation temp directory the evaluator
        # subprocess was handed, and ``stdout`` is that subprocess's own
        # printed table -- both are provenance, not measurement. Every number
        # the scorer parsed OUT of that stdout stays in ``official["raw"]``
        # and IS compared below.
        official = {
            key: value
            for key, value in aggregate["official"].items()
            if key not in ("command", "stdout")
        }
        return {**aggregate, "official": official}

    # The official evaluator is a SUBPROCESS whose own summation order is not
    # bit-stable across invocations (its interpreter runs with hash
    # randomization), so two runs of the SAME file already differ in the last
    # ulp of slu_f1. Every value is compared, floats within 1e-9 -- which is
    # three orders of magnitude tighter than the scorer's own 1e-6 identity
    # tolerance and far tighter than any effect this cell could claim.
    _assert_close(without_command(plain["aggregate"]), without_command(variant["aggregate"]))

    official = plain["aggregate"]["official"]
    assert round(official["scenario_accuracy"], 4) == SLURP_SEALED["scenario_accuracy"]
    assert round(official["action_accuracy"], 4) == SLURP_SEALED["action_accuracy"]
    assert round(official["intent_accuracy"], 4) == SLURP_SEALED["intent_accuracy"]
    assert round(official["slu_f1"] * 100, 2) == 35.80
