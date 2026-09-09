"""Scorer aliases share one invocation; independently configured callables do not."""
from functools import partial
from types import SimpleNamespace

from speech_aware_evidence_acquisition.core import bundle, scorers
from speech_aware_evidence_acquisition.core.base import Registry


def _score(monkeypatch, tmp_path, entries):
    registry = Registry("synthetic scorer")
    for name, function in entries:
        registry.register(name, function)
    monkeypatch.setattr(scorers, "SCORERS", registry)
    monkeypatch.setattr(bundle, "VerifiedBundle", SimpleNamespace)
    monkeypatch.setattr(scorers, "_assert_scoring_entry_gate", lambda *args: None)
    verified = SimpleNamespace(
        outputs_path=tmp_path / "synthetic.outputs.jsonl",
        manifest={"scorers": [name for name, _ in entries]},
    )
    return scorers.score_bundle(verified, {}, tmp_path)


def test_aliases_keep_result_keys_but_run_official_callable_once(monkeypatch, tmp_path):
    calls = []
    def scorer(*args):
        calls.append(args)
        return {"aggregate": {"count": 1}, "per_sample": [{"sample_id": "synthetic"}]}
    result = _score(monkeypatch, tmp_path, [("official", scorer), ("alias", scorer)])
    assert len(calls) == 1
    assert list(result) == ["official", "alias"]
    assert result["official"] == result["alias"]


def test_distinct_parameter_bindings_are_not_deduplicated(monkeypatch, tmp_path):
    calls = []
    def scorer(*args, normalized):
        calls.append(normalized)
        return {"aggregate": {"normalized": normalized}}
    result = _score(monkeypatch, tmp_path, [
        ("raw", partial(scorer, normalized=False)),
        ("normalized", partial(scorer, normalized=True)),
    ])
    assert calls == [False, True]
    assert result["raw"] != result["normalized"]
