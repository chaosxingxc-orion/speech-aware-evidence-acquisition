"""Synthetic tests for the ASRBIAS Fold B biasing-variant instrument (no model, no data, no GPU)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load(rel: str, name: str):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / rel)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


AB = _load("scripts/analysis/asr339/foldb_bias_transcription.py", "asrbias_instrument_under_test")


# ------------------------------------------------------------------------------------------ registry


def test_every_registry_variant_resolves_and_files_match_registry():
    files = sorted(p.name for p in AB.CONFIG_DIR.glob("variant-*.json"))
    assert files == sorted(f"variant-{v}.json" for v in AB.VARIANT_IDS)
    for vid in AB.VARIANT_IDS:
        doc = AB.load_variant(vid)
        assert doc["variant_id"] == vid and doc["context"] in AB.CONTEXT_KINDS
        assert len(doc["_sha256"]) == 64


def test_variant_semantics_match_the_design():
    v = {i: AB.load_variant(i) for i in AB.VARIANT_IDS}
    assert v["v0"]["context"] == "none" and v["v0"]["decode"]["samples"] == 1
    assert v["v1"]["context"] == "type-vocabulary"
    assert (v["v2-n30"]["lexicon_n"], v["v2-n100"]["lexicon_n"]) == (30, 100)
    assert v["v3-n100"]["first_token_bias"] > 0 and v["v2-n100"]["first_token_bias"] == 0
    for vid in ("v4-none", "v4-n100"):
        assert v[vid]["decode"]["samples"] == 5 and v[vid]["decode"]["temperature"] == 0.6
        assert len(set(v[vid]["decode"]["seeds"])) == 5


def test_unknown_variant_and_bad_fragments_fail_closed(tmp_path):
    with pytest.raises(AB.InstrumentError):
        AB.load_variant("v9")
    bad = {"schema": AB.SCHEMA_VARIANT, "variant_id": "v1", "context": "gold-values", "lexicon_n": None,
           "first_token_bias": 0.0, "decode": {"temperature": 0, "samples": 1, "seeds": []}}
    (tmp_path / "variant-v1.json").write_text(json.dumps(bad))
    with pytest.raises(AB.InstrumentError):
        AB.load_variant("v1", tmp_path)
    bias_without_lexicon = {**bad, "context": "type-vocabulary", "first_token_bias": 2.0}
    (tmp_path / "variant-v1.json").write_text(json.dumps(bias_without_lexicon))
    with pytest.raises(AB.InstrumentError):
        AB.load_variant("v1", tmp_path)


def test_type_descriptions_are_type_level_one_liners():
    descriptions = AB.type_descriptions()
    assert len(descriptions) >= 50
    for slot_type, line in descriptions.items():
        assert "\n" not in line and 1 <= len(line.split()) <= 12, slot_type
        assert not any(ch.isdigit() for ch in line), slot_type


# ------------------------------------------------------------------------------------------ lexicon scoping


def _records():
    return [
        ("u-train-1", "play_music", [("artist_name", "Beyonce"), ("song_name", "halo")]),
        ("u-train-2", "play_music", [("artist_name", "beyonce")]),
        ("u-train-2", "play_music", [("artist_name", "beyonce")]),  # a second recording of the same utterance
        ("u-train-3", "play_music", [("song_name", "yesterday")]),
        ("u-foldA", "play_music", [("artist_name", "only-in-fold-a")]),
        ("u-foldB", "play_music", [("artist_name", "only-in-fold-b"), ("song_name", "only-in-fold-b-song")]),
        ("u-train-4", "alarm_set", [("time", "seven am")]),
    ]


def test_fold_a_and_fold_b_utterances_never_feed_the_lexicon():
    lex = AB.build_lexicon(_records(), {"u-foldA", "u-foldB"})
    flat = {v for vals in lex["type_values"].values() for v in vals}
    assert "only-in-fold-a" not in flat and "only-in-fold-b" not in flat and "only-in-fold-b-song" not in flat
    assert lex["n_utterances"] == 4  # u-train-1..4, each counted once
    assert lex["type_values"]["artist_name"][0] == "beyonce"  # case-folded, counted over two utterances
    assert lex["intent_type_prior"]["play_music"]["artist_name"] == round(2 / 3, 6)


def test_row_own_gold_values_are_excluded_by_construction():
    """The row's own utterance is in the excluded set, so a value that occurs only there cannot reach any composed
    context, whatever the committed intent is."""
    lex = AB.build_lexicon(_records(), {"u-foldA", "u-foldB"})
    own_gold = {"only-in-fold-b", "only-in-fold-b-song"}
    for intent in list(lex["intent_type_prior"]) + [None, "unknown_intent"]:
        for n in (30, 100):
            assert own_gold.isdisjoint(AB.compose_values(intent, lex, n))
    # without the exclusion the same values DO appear, so the test would fail if scoping broke
    leaky = AB.build_lexicon(_records(), set())
    assert own_gold & set(AB.compose_values("play_music", leaky, 100))


def test_compose_is_intent_scoped_capped_deterministic_and_deduplicated():
    lex = {"type_values": {"a": ["x", "y", "z"], "b": ["y", "w"], "c": ["only-c"]},
           "intent_type_prior": {"i1": {"a": 0.9, "b": 0.5}, "i2": {"c": 1.0}, "i3": {"a": 0.001}}}
    assert AB.compose_values("i1", lex, 100) == ["x", "y", "z", "w"]
    assert AB.compose_values("i1", lex, 2) == ["x", "y"]
    assert AB.compose_values("i2", lex, 100) == ["only-c"]
    assert AB.compose_values("i3", lex, 100) == []  # prior under the floor
    assert AB.compose_values(None, lex, 100) == []
    assert AB.compose_values("i1", lex, 100) == AB.compose_values("i1", lex, 100)


# ------------------------------------------------------------------------------------------ budget


def test_v1_context_fits_the_budget_under_the_conservative_estimator():
    text = AB.render_context(AB.load_variant("v1"), [], AB.type_descriptions())
    assert text and AB.approx_tokens(text) <= AB.CONTEXT_TOKEN_BUDGET


def test_fit_budget_trims_lexicon_values_and_refuses_oversize_vocabulary():
    v2 = AB.load_variant("v2-n100")
    values = [f"word{i}" for i in range(100)]
    text, tokens, kept, trimmed = AB.fit_budget(v2, values, {}, lambda t: len(t.split()), budget=40)
    assert tokens <= 40 and trimmed == 100 - len(kept) and 0 < len(kept) < 100
    assert text.endswith(kept[-1] + ".")
    full = AB.fit_budget(v2, values, {}, AB.approx_tokens)
    assert full[3] == 0 and full[1] <= AB.CONTEXT_TOKEN_BUDGET  # 100 short values fit untrimmed
    with pytest.raises(AB.InstrumentError):
        AB.fit_budget(AB.load_variant("v1"), [], AB.type_descriptions(), lambda t: 10_000)
    assert AB.fit_budget(v2, [], {}, AB.approx_tokens)[0] is None  # unknown intent: no context at all


def test_bias_tokens_skip_stop_words_and_short_words_and_are_capped():
    toks = {"london": [11], " london": [12], "the beatles": [3], " the beatles": [4], "ab": [5], "alanis morissette": [21, 22],
            " alanis morissette": [31, 32]}
    out = AB.bias_first_tokens(["london", "the beatles", "ab", "alanis morissette"], lambda t: toks[t], 2.0)
    assert out == [[11, 2.0], [12, 2.0], [21, 2.0], [31, 2.0]]
    many = AB.bias_first_tokens([f"value{i}" for i in range(1000)], lambda t: [abs(hash(t)) % 10**6 + 1], 2.0)
    assert len(many) <= AB.MAX_BIAS_TOKENS


# ------------------------------------------------------------------------------------------ requests and schemas


def test_context_is_rendered_as_system_message_and_audio_only_in_user_turn():
    decode = AB.load_variant("v4-n100")["decode"]
    body = AB.request_body(b"abc", "CTX", decode, [[7, 2.0]], 12)
    assert [m["role"] for m in body["messages"]] == ["system", "user"]
    assert body["messages"][0]["content"] == "CTX"
    parts = body["messages"][1]["content"]
    assert [p["type"] for p in parts] == ["input_audio"]
    assert body["logit_bias"] == [[7, 2.0]] and body["seed"] == 12 and body["temperature"] == 0.6
    plain = AB.request_body(b"abc", None, AB.load_variant("v0")["decode"], [], None)
    assert [m["role"] for m in plain["messages"]] == ["user"] and "logit_bias" not in plain and "seed" not in plain
    assert plain["temperature"] == 0


def test_row_and_catalog_schema_extend_the_asr339_schema():
    item = {"sample_id": "slurp:train:1", "audio_sha256": "a" * 64, "audio_seconds": 2.5}
    v = AB.load_variant("v4-n100")
    ctx = {"chars": 10, "tokens": 4, "values": 3, "trimmed": 0, "bias_tokens": 0, "intent_known": True}
    row = AB.row_record(item, v, "ok", "a <SEP> b", 1.0, {"prompt_tokens": 9, "completion_tokens": 3}, ctx, ["a", "b"])
    base_fields = {"schema", "sample_id", "status", "transcript", "audio_sha256", "audio_seconds", "asr_seconds",
                   "completion_tokens", "prompt_tokens"}
    assert base_fields <= set(row)
    assert {"variant", "variant_config_sha256", "context_tokens", "context_chars", "lexicon_values"} <= set(row)
    assert row["nbest_count"] == 2 and row["variant_config_sha256"] == v["_sha256"]
    single = AB.row_record(item, AB.load_variant("v0"), "ok", "a", 1.0, {}, ctx, None)
    assert "nbest" not in single


def test_full_guard_looks_for_the_asrbias_ledger_row(tmp_path):
    (tmp_path / "docs").mkdir()
    ledger = tmp_path / "docs" / "exposure-ledger.md"
    ledger.write_text("| SAEA-SLURP-ASR339-FOLD-B-V1 | consumed = no | countersigned |\n", encoding="utf-8")
    assert AB.LEDGER_ROW_ID == "SAEA-SLURP-ASRBIAS-FOLD-B-V1"
    with pytest.raises(AB.InstrumentError):
        AB.check_ledger(tmp_path)  # the ASR339 row does not authorise this pass
    ledger.write_text("| SAEA-SLURP-ASRBIAS-FOLD-B-V1 | consumed = no | root countersignature: pending |\n",
                      encoding="utf-8")
    with pytest.raises(AB.InstrumentError):
        AB.check_ledger(tmp_path)  # a pending countersignature is not a countersignature
    ledger.write_text("| SAEA-SLURP-ASRBIAS-FOLD-B-V1 | consumed = no | countersigned 2026-10-20T00:00:00Z |\n",
                      encoding="utf-8")
    AB.check_ledger(tmp_path)
    ledger.write_text("| SAEA-SLURP-ASRBIAS-FOLD-B-V1 | consumed = no | pending |\n", encoding="utf-8")
    with pytest.raises(AB.InstrumentError):
        AB.check_ledger(tmp_path)
    ledger.write_text("| SAEA-SLURP-ASRBIAS-FOLD-B-V1 | consumed = yes | countersigned |\n", encoding="utf-8")
    with pytest.raises(AB.InstrumentError):
        AB.check_ledger(tmp_path)


def test_score_subcommand_delegates_unchanged(monkeypatch):
    seen = {}
    monkeypatch.setattr(AB.BASE, "main", lambda argv: seen.setdefault("argv", argv) and 0)
    assert AB.main(["score", "--transcripts", "d", "--containment"]) == 0
    assert seen["argv"] == ["score", "--transcripts", "d", "--containment"]


def test_smoke_refuses_outside_the_smoke_root(tmp_path, monkeypatch):
    monkeypatch.setenv("SPEECHRL_DATA_DIR", str(tmp_path))
    args = AB.argparse.Namespace(model_id="qwen3-asr-1.7b", variant="v0", out_root=str(tmp_path / "prepared"),
                                 lexicon=None, rows=2, smoke=True, full=False, port=None, session_root=str(tmp_path))
    with pytest.raises(AB.InstrumentError, match="ASRBIAS-SMOKE"):
        AB.cmd_transcribe(args)
    args.rows = 5
    args.out_root = str(tmp_path / "diagnostics" / "ASRBIAS-SMOKE" / "t")
    with pytest.raises(AB.InstrumentError, match="--rows"):
        AB.cmd_transcribe(args)
