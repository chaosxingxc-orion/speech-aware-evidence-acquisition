"""``core.scoring_strata`` -- the official-scoring path's ``--strata-inside-scorer`` mode
(coordinator ruling 2026-09-30), on fakes only.

Post-stratification by gold intent happens INSIDE the scoring step and leaves as aggregates only.
These tests prove, on a synthetic floored two-stratum roster (3 'small' rows the right arm wins,
9 'big' rows nobody wins; population 90:10): the raw / post-stratified / equal-stratum intent
deltas are +25 / +90 / +50 pp; the receipt carries per-stratum n and per-arm intent-correct / TP /
FP / FN totals and no sample id; every refusal fires BEFORE the gold binding is called and writes
nothing; the CLI demands the mode switch and refuses any per-row output; and the official gold
binding refuses a non-test row under the test scorer before the data root is touched. Zero model,
scorer-subprocess, network and data-root contacts.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis import stratified_paired as SP
from speech_aware_evidence_acquisition.core import scoring_batch
from speech_aware_evidence_acquisition.core import scoring_strata as scs
from speech_aware_evidence_acquisition.reproduction import slurp_official_eval as soe

SCORER = "slurp-slu-official-train"


def _ids() -> list[str]:
    return [f"slurp:train:{i:06d}:audio-{i}" for i in range(12)]


def _stratum(i: int) -> str:
    return "small_query" if i < 3 else "big_query"


def _row(sample_id: str, correct: bool) -> dict:
    v = 1.0 if correct else 0.0
    tp, bad = (1.0, 0.0) if correct else (0.0, 1.0)
    return {
        "sample_id": sample_id, "parsed": True, "scenario_action_exact": v, "scenario_exact": v,
        "action_exact": v, "slot_f1_exact_f1": v, "slot_f1_exact_tp": tp, "slot_f1_exact_fp": bad,
        "slot_f1_exact_fn": bad, "slu_f1_f1": v, "slu_f1_word_tp": tp, "slu_f1_word_fp": bad,
        "slu_f1_word_fn": bad, "slu_f1_char_tp": tp, "slu_f1_char_fp": bad, "slu_f1_char_fn": bad,
    }


def _write(path: Path, payload) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


class Fake:
    def __init__(self, tmp: Path, *, stratification: dict | None = None) -> None:
        self.ids = _ids()
        roster = {"roster_id": "SLURP-FAKE-FLOORED-V1", "stratum_withheld_per_item": True,
                  "items": [{"sample_id": s, "utterance_id": s.rsplit(":", 1)[0]} for s in self.ids]}
        if stratification is not None:
            roster["stratification"] = stratification
        self.roster = _write(tmp / "roster.json", roster)
        self.counts = _write(tmp / "population-counts.json",
                             {"population_counts": {"small_query": 90, "big_query": 10}})
        self.left = self._scores(tmp / "left.scores.json", set())
        self.right = self._scores(tmp / "right.scores.json", {0, 1, 2})
        self.out_dir = tmp / "out"
        self.out_dir.mkdir()
        self.gold_calls = 0

    def _scores(self, path: Path, correct: set) -> Path:
        rows = [_row(s, i in correct) for i, s in enumerate(self.ids)]
        return _write(path, {SCORER: {"per_sample": rows, "aggregate": {"identity_check": {"passed": True}}}})

    def gold(self, scorer_id: str, sample_ids):
        self.gold_calls += 1
        index = {s: i for i, s in enumerate(self.ids)}
        return {s: _stratum(index[s]) for s in sample_ids}

    def run(self, **overrides):
        kwargs = dict(scorer_id=SCORER, left_scores=self.left, right_scores=self.right,
                      roster=self.roster, population_counts=self.counts,
                      output=self.out_dir / "scorer-strata-aggregate.json", cluster_key="sample_id",
                      seed=7, draws=300, gold_intents=self.gold)
        kwargs.update(overrides)
        return scs.score_paired_strata(**kwargs)


FLOORED = {"floor_driven_utterances": 3, "sample_floor_utterances": 3}


def test_the_scoring_batch_path_exports_the_mode() -> None:
    assert scoring_batch.score_paired_strata is scs.score_paired_strata
    assert "score_paired_strata" in scoring_batch.__all__


def test_floored_two_stratum_fake_gives_raw_25_post_stratified_90_equal_50(tmp_path: Path) -> None:
    fake = Fake(tmp_path, stratification=FLOORED)
    receipt = fake.run()
    w = receipt["weightings"]
    assert w["raw"]["intent"]["delta_pp"] == pytest.approx(25.0)
    assert w["post_stratified"]["intent"]["delta_pp"] == pytest.approx(90.0)
    assert w["equal_stratum"]["intent"]["delta_pp"] == pytest.approx(50.0)
    for block in (w["raw"], w["post_stratified"], w["equal_stratum"]):
        low, high = block["intent"]["ci95_pp"]
        assert low <= block["intent"]["delta_pp"] <= high
    assert w["post_stratified"]["population_weights"] == {"big_query": 0.1, "small_query": 0.9}
    small, big = receipt["per_stratum"]["small_query"], receipt["per_stratum"]["big_query"]
    assert small["n"] == 3 and big["n"] == 9
    assert small["counts"]["left"] == {"n": 3, "intent_correct": 0.0, "tp": 0.0, "fp": 6.0, "fn": 6.0}
    assert small["counts"]["right"] == {"n": 3, "intent_correct": 3.0, "tp": 6.0, "fp": 0.0, "fn": 0.0}
    assert big["counts"]["right"]["intent_correct"] == 0.0
    assert small["intent"]["delta_pp"] == pytest.approx(100.0)
    assert receipt["receipt_sha256"] == SP.canonical_digest(receipt, exclude=("receipt_sha256",))
    written = json.loads((fake.out_dir / "scorer-strata-aggregate.json").read_text())
    assert written == receipt
    assert fake.gold_calls == 1


def test_the_output_directory_holds_one_aggregate_file_and_no_sample_id(tmp_path: Path) -> None:
    fake = Fake(tmp_path, stratification=FLOORED)
    fake.run()
    files = sorted(p for p in fake.out_dir.rglob("*") if p.is_file())
    assert [p.name for p in files] == ["scorer-strata-aggregate.json"]
    text = files[0].read_text(encoding="utf-8")
    assert not any(sample_id in text for sample_id in fake.ids)
    assert not any(sample_id.rsplit(":", 1)[0] in text for sample_id in fake.ids)


def test_same_inputs_give_the_same_floats_as_the_shared_estimators_called_directly(tmp_path: Path) -> None:
    """The draw-identity argument: the receipt's numbers are exactly the shared module's on the same
    sorted ids / strata / clusters / seed / draws -- what the read driver's gold-bank path calls."""

    fake = Fake(tmp_path, stratification=FLOORED)
    receipt = fake.run()
    left = {r["sample_id"]: {k: float(v) for k, v in r.items() if k != "sample_id"}
            for r in json.loads(fake.left.read_text())[SCORER]["per_sample"]}
    right = {r["sample_id"]: {k: float(v) for k, v in r.items() if k != "sample_id"}
             for r in json.loads(fake.right.read_text())[SCORER]["per_sample"]}
    ids = sorted(fake.ids)
    stratum_of = {s: _stratum(i) for i, s in enumerate(fake.ids)}.__getitem__
    direct = SP.stratified_paired_read(
        left, right, ids, stratum_of=stratum_of, cluster_of=lambda s: s,
        weights={"small_query": 0.9, "big_query": 0.1}, seed=7, draws=300,
    )
    for kind in ("intent", "slu_f1"):
        assert receipt["weightings"]["post_stratified"][kind] == direct["post_stratified"][kind]
        assert receipt["weightings"]["raw"][kind] == direct["raw"][kind]
        for key, value in direct["equal_stratum"][kind].items():
            assert receipt["weightings"]["equal_stratum"][kind][key] == value


@pytest.mark.parametrize(
    "case",
    ["no-stratification", "unknown-scorer", "output-exists", "output-not-json", "rows-not-roster"],
)
def test_refusals_fire_before_gold_and_write_nothing(tmp_path: Path, case: str) -> None:
    fake = Fake(tmp_path, stratification=None if case == "no-stratification" else FLOORED)
    overrides: dict = {}
    if case == "unknown-scorer":
        overrides["scorer_id"] = "slurp-slu-official-projected-v3"
    elif case == "output-exists":
        (fake.out_dir / "scorer-strata-aggregate.json").write_text("{}", encoding="utf-8")
    elif case == "output-not-json":
        overrides["output"] = fake.out_dir / "per-row.jsonl"
    elif case == "rows-not-roster":
        rows = json.loads(fake.right.read_text())
        rows[SCORER]["per_sample"] = rows[SCORER]["per_sample"][:-1]
        _write(fake.right, rows)
    before = sorted(p.name for p in fake.out_dir.iterdir())
    with pytest.raises(scs.ScorerStrataError):
        fake.run(**overrides)
    assert fake.gold_calls == 0
    assert sorted(p.name for p in fake.out_dir.iterdir()) == before


def test_the_leak_guard_refuses_text_carrying_a_roster_id() -> None:
    with pytest.raises(scs.ScorerStrataError):
        scs._assert_aggregate_only('{"x": "slurp:train:000001:audio-1"}', ["slurp:train:000001:audio-1"])
    scs._assert_aggregate_only('{"x": 1}', ["slurp:train:000001:audio-1"])


def test_the_cli_requires_the_mode_switch_and_refuses_any_per_row_output(tmp_path: Path) -> None:
    fake = Fake(tmp_path, stratification=FLOORED)
    base = ["--scorer-id", SCORER, "--left-scores", str(fake.left), "--right-scores", str(fake.right),
            "--roster", str(fake.roster), "--population-counts", str(fake.counts),
            "--output", str(fake.out_dir / "scorer-strata-aggregate.json")]
    with pytest.raises(SystemExit) as missing_switch:
        scs.main(base)
    assert missing_switch.value.code == 2
    for flag in ("--include-per-sample", "--per-row-output"):
        assert scs.main(["--strata-inside-scorer", *base, flag]) == 2
    assert list(fake.out_dir.iterdir()) == []


def test_the_official_gold_binding_refuses_a_foreign_row_before_the_data_root(tmp_path: Path) -> None:
    missing_root = tmp_path / "no-such-data-root"
    with pytest.raises(soe.SlurpOfficialEvalError):
        soe.official_gold_intents("slurp-slu-official-test", ["slurp:devel:000001:audio-1"], {}, missing_root)
    with pytest.raises(soe.SlurpOfficialEvalError):
        soe.official_gold_intents("slurp-slu-official-projected-v3", ["slurp:devel:000001:a"], {}, missing_root)
    assert soe.OFFICIAL_GOLD_SPLIT_OF_SCORER["slurp-slu-official-test"] == ("test", True)
    assert soe.OFFICIAL_GOLD_SPLIT_OF_SCORER["slurp-slu-official-train"] == ("train", False)
