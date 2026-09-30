"""The two K6p artifact builders and the artifact proof, on fakes (no pinned data, no contact):
the builders call the recall read's own ``key_construction`` / ``centre_keys`` /
``centre_queries`` (monkeypatched here to a synthetic construction), write files the production
loaders read back, refuse to overwrite, and the proof's fold counts see artifact == direct."""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[2]
for extra in (REPO / "scripts", REPO / "scripts" / "analysis"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import build_slurp_centred_centroid_key as keybuild  # noqa: E402
import build_slurp_centred_query_vectors as querybuild  # noqa: E402
import slurp_k6p_artifact_proof as proof  # noqa: E402

from speech_aware_evidence_acquisition.rails.phase_supply import (  # noqa: E402
    load_sealed_segment_vectors,
    load_sealed_vectors,
)

INTENTS = ["alarm_set", "play_music", "weather_query"]
DIM = "intent-boundary"


def _fake_kc(rng):
    raw_means = rng.normal(size=(3, 4))
    return {
        "store": {"to_intent": {f"{DIM}:{x}": x for x in INTENTS},
                  "facet_vectors": {f"{DIM}:{x}": {} for x in INTENTS}},
        "intents": list(INTENTS), "raw_means": raw_means, "mu_p": rng.normal(size=4) * 0.1,
        "mu_q": rng.normal(size=4) * 0.1, "per_intent": Counter({0: 5, 1: 7}),
        "pool_info": {"construction_members": 12}, "stats_ids": ["r1", "r2"],
        "stats_overlap": {"fold_a": 0, "fold_b": 0, "pool": 0}, "files": {"x": "y"},
        "centroid": None,
    }


@pytest.fixture
def recall(monkeypatch):
    module, _diag, _cbuild = keybuild.recall_modules(REPO)
    kc = _fake_kc(np.random.default_rng(7))
    monkeypatch.setattr(module, "key_construction", lambda root, diag, cbuild, centroid_pin=None: kc)
    monkeypatch.setattr(keybuild, "recall_modules", lambda repo: (module, None, None))
    return module, kc


def test_the_key_builder_writes_the_reads_centred_keys_and_refuses_to_overwrite(tmp_path, recall):
    module, kc = recall
    result = keybuild.build(REPO, tmp_path, tmp_path)
    path = tmp_path / "prepared" / keybuild.ARTIFACT_ID / keybuild.KEY_NAME
    loaded = load_sealed_vectors(path, expected_sha256=result["key_sha256"], dimensions=(DIM,))
    expected = module.centre_keys(kc["raw_means"], kc["mu_p"])
    for j, intent in enumerate(INTENTS):
        assert np.array_equal(np.asarray(loaded[f"{DIM}:{intent}"][DIM]), expected[j])
    receipt = json.loads((path.parent / keybuild.RECEIPT_NAME).read_text(encoding="utf-8"))
    assert receipt["artifact"]["sha256"] == result["key_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert set(receipt["contacts"].values()) == {0}
    assert receipt["measured"]["centred_from_written_fallback"] == ["weather_query"]
    assert receipt["centring_statistics"]["query_mean_sha256_f8le"] == keybuild.vector_sha(kc["mu_q"])
    with pytest.raises(keybuild.BuildError, match="refusing to overwrite"):
        keybuild.build(REPO, tmp_path, tmp_path)


def _source_file(tmp_path, ids, rng):
    lines = []
    for sid in ids:
        lines.append(json.dumps({
            "id": sid, "audio_sha256": hashlib.sha256(sid.encode()).hexdigest(), "source_frames": 16000,
            "source_sample_rate_hz": 16000,
            "segments": [{"id": f"{sid}:0", "start_frame": 0, "end_frame": 16000,
                          "vectors": {DIM: [float(x) for x in rng.normal(size=4)]}}],
        }))
    path = tmp_path / "vectors" / "q.jsonl"
    path.parent.mkdir(parents=True)
    text = "\n".join(lines) + "\n"
    path.write_text(text, encoding="utf-8")
    return {"kind": "sealed-segment-vectors", "relpath": "vectors/q.jsonl",
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
            "tool_contact_ledger_row": "SYNTHETIC", "embedded_signal": "speech: synthetic"}


def test_the_query_builder_centres_every_row_and_keeps_its_identity(tmp_path, recall, monkeypatch):
    module, kc = recall
    ids = ["slurp:train:1", "slurp:train:2", "slurp:train:3"]
    pin = _source_file(tmp_path, ids, np.random.default_rng(3))
    monkeypatch.setattr(querybuild, "source_pin", lambda repo, roster: pin)
    monkeypatch.setattr(module, "roster_ids", lambda path: list(ids))
    result = querybuild.build(REPO, tmp_path, tmp_path, "fold-b")
    out = load_sealed_segment_vectors(Path(result["file"]), expected_sha256=result["sha256"], dimensions=(DIM,))
    src = load_sealed_segment_vectors(tmp_path / pin["relpath"], expected_sha256=pin["sha256"], dimensions=(DIM,))
    raw = module.unit_rows([src[s].segments[0][DIM] for s in ids])
    expected = module.centre_queries(raw, kc["mu_q"])
    for i, sid in enumerate(ids):
        assert out[sid].audio_sha256 == src[sid].audio_sha256
        assert np.array_equal(np.asarray(out[sid].segments[0][DIM]), expected[i])
    receipt = json.loads(Path(result["receipt"]).read_text(encoding="utf-8"))
    assert receipt["artifact"]["rows"] == 3 and receipt["artifact"]["unit_norm_rows"] == 3
    assert receipt["embedded_signal_for_the_pin"].startswith("speech:")
    with pytest.raises(querybuild.BuildError, match="refusing to overwrite"):
        querybuild.build(REPO, tmp_path, tmp_path, "fold-b")


def test_the_query_builder_refuses_a_source_that_does_not_cover_the_roster(tmp_path, recall, monkeypatch):
    module, _kc = recall
    pin = _source_file(tmp_path, ["slurp:train:1"], np.random.default_rng(3))
    monkeypatch.setattr(querybuild, "source_pin", lambda repo, roster: pin)
    monkeypatch.setattr(module, "roster_ids", lambda path: ["slurp:train:1", "slurp:train:2"])
    with pytest.raises(querybuild.BuildError, match="cover exactly"):
        querybuild.build(REPO, tmp_path, tmp_path, "fold-b")


def test_the_query_builder_refuses_a_tampered_source(tmp_path, recall, monkeypatch):
    pin = _source_file(tmp_path, ["slurp:train:1"], np.random.default_rng(3))
    pin["sha256"] = "0" * 64
    monkeypatch.setattr(querybuild, "source_pin", lambda repo, roster: pin)
    with pytest.raises(querybuild.BuildError, match="does not hash"):
        querybuild.build(REPO, tmp_path, tmp_path, "fold-b")


def test_the_proof_sees_artifact_equal_to_direct_and_counts_rank1():
    module, _d, _c = keybuild.recall_modules(REPO)
    rng = np.random.default_rng(11)
    kc = _fake_kc(rng)
    kc["centroid"] = module.unit_rows(kc["raw_means"])
    q_raw = module.unit_rows(rng.normal(size=(5, 4)))
    key_art = module.centre_keys(kc["raw_means"], kc["mu_p"])
    q_art = module.centre_queries(q_raw, kc["mu_q"])
    ids = [f"s{i}" for i in range(5)]
    gold = {s: INTENTS[i % 3] for i, s in enumerate(ids)}
    share = np.zeros((5, 3))
    counts = proof.fold_counts(module, kc, key_art, ids, q_art, q_raw, share, gold)
    assert counts["rows"] == 5
    assert counts["blocks_identical_artifact_vs_direct"] == 5
    assert counts["rank1"]["artifact"] == counts["rank1"]["direct"]
    assert counts["rank1_lift_artifact_vs_cent_agree"] == counts["rank1"]["artifact"] - counts["rank1"]["cent_agree"]
