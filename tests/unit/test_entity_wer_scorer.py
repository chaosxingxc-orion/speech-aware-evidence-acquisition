"""``entity-wer`` scorer: registry resolution + computation on synthetic
fixtures with hand-computed expected entity-WER, fail-closed cases (owner
decision D-3, entity-class WER scorer admission)."""

import json

import pytest

from speech_aware_evidence_acquisition.core import scorers  # noqa: F401 (registration)
from speech_aware_evidence_acquisition.core.base import SCORERS
from speech_aware_evidence_acquisition.core.bundle import VerifiedBundle
from speech_aware_evidence_acquisition.core.scorers import (
    ENTITY_WER_ADAPTER_VERSION,
    ScoringPhaseError,
    _mention_fully_hit,
    _normalized_span_offsets,
    score_bundle,
    score_entity_wer_outputs,
)
from speech_aware_evidence_acquisition.data.lock import load_lock


def _write_nlp(path, rows):
    lines = ["token|speaker|tags|wer_tags"]
    for token, wer_tags in rows:
        lines.append(f"{token}|0||{wer_tags}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_sidecar(path, mapping):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(mapping), encoding="utf-8")


def _write_outputs(tmp_path, rows, name="y.outputs.jsonl"):
    path = tmp_path / name
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8"
    )
    return path


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def test_entity_wer_is_registered():
    assert "entity-wer" in SCORERS.names()


def test_entity_wer_resolves_to_the_same_function_the_offline_cli_calls():
    assert SCORERS.resolve("entity-wer") is score_entity_wer_outputs


# ---------------------------------------------------------------------------
# _normalized_span_offsets / _mention_fully_hit (white-box: position mapping
# between raw .nlp tokens and the normalized sequence align() aligns over).
# ---------------------------------------------------------------------------


def test_normalized_span_offsets_is_one_to_one_when_no_token_splits():
    assert _normalized_span_offsets(["Acme", "Corporation"]) == [(0, 1), (1, 2)]


def test_normalized_span_offsets_handles_a_raw_token_that_splits_into_two():
    # "AT&T" -> normalize_text_v1 turns "&" into a space -> "at t" -> two
    # normalized tokens; "reported" stays one.
    assert _normalized_span_offsets(["AT&T", "reported"]) == [(0, 2), (2, 3)]


def test_normalized_span_offsets_handles_a_raw_token_that_vanishes():
    # A punctuation-only cell normalizes to zero tokens.
    assert _normalized_span_offsets(["...", "hi"]) == [(0, 0), (0, 1)]


def test_mention_fully_hit_true_when_every_position_hits():
    assert _mention_fully_hit((0, 1), [(0, 1), (1, 2)], (True, True)) is True


def test_mention_fully_hit_false_when_any_position_misses():
    assert _mention_fully_hit((0, 1), [(0, 1), (1, 2)], (True, False)) is False


def test_mention_not_counted_correct_when_it_normalizes_to_zero_positions():
    assert _mention_fully_hit((0,), [(0, 0)], (True,)) is False


# ---------------------------------------------------------------------------
# Hand-computed entity-WER over a synthetic fixture with a known entity error.
# ---------------------------------------------------------------------------

_ONE_ENTITY_WRONG_ROWS = [
    ("The", "[]"),
    ("Acme", "['0']"),
    ("Corporation", "['0']"),
    ("reported", "[]"),
    ("strong", "[]"),
    ("results", "[]"),
    ("in", "[]"),
    ("March", "['1']"),
    ("2020", "['1']"),
]


def _setup_one_entity_wrong(synthetic_world):
    nlp = synthetic_world.e21 / "transcripts" / "nlp_references" / "4000001.nlp"
    _write_nlp(nlp, _ONE_ENTITY_WRONG_ROWS)
    sidecar = synthetic_world.e21 / "transcripts" / "wer_tags" / "4000001.wer_tag.json"
    _write_sidecar(sidecar, {"0": {"entity_type": "ORG"}, "1": {"entity_type": "DATE"}})


def test_entity_wer_hand_computed_one_of_two_entities_wrong(synthetic_world, tmp_path):
    """Reference: "Acme Corporation" (ORG) and "March 2020" (DATE). The
    hypothesis gets the ORG mention exactly right and mangles the DATE
    mention's second token (2020 -> 2021, one substitution). Hand-computed:
    expected_total=2, correct=1, recall=0.5, entity_wer=0.5; ORG's own
    entity_wer=0.0, DATE's own entity_wer=1.0."""

    _setup_one_entity_wrong(synthetic_world)
    outputs = _write_outputs(
        tmp_path,
        [
            {
                "sample_id": "4000001",
                "carrier_lock_key": "earnings21-original",
                "text": "the acme corporation reported strong results in march 2021",
            }
        ],
    )
    lock = load_lock(synthetic_world.lock_path)
    scores = score_entity_wer_outputs(outputs, lock, synthetic_world.data_root)

    assert len(scores["per_sample"]) == 1
    sample = scores["per_sample"][0]
    assert sample["sample_id"] == "4000001"
    assert sample["expected_total"] == 2
    assert sample["correct"] == 1
    assert sample["precision"] == pytest.approx(1.0)
    assert sample["recall"] == pytest.approx(0.5)
    assert sample["entity_wer"] == pytest.approx(0.5)
    assert sample["by_entity_type"]["ORG"]["entity_wer"] == pytest.approx(0.0)
    assert sample["by_entity_type"]["ORG"]["correct"] == 1
    assert sample["by_entity_type"]["DATE"]["entity_wer"] == pytest.approx(1.0)
    assert sample["by_entity_type"]["DATE"]["correct"] == 0

    aggregate = scores["aggregate"]
    assert aggregate["adapter_version"] == ENTITY_WER_ADAPTER_VERSION
    assert aggregate["samples"] == 1
    assert aggregate["samples_with_entities"] == 1
    assert aggregate["expected_total"] == 2
    assert aggregate["correct"] == 1
    assert aggregate["entity_wer"] == pytest.approx(0.5)
    assert aggregate["macro_entity_wer"] == pytest.approx(0.5)
    assert aggregate["by_entity_type"]["ORG"]["entity_wer"] == pytest.approx(0.0)
    assert aggregate["by_entity_type"]["DATE"]["entity_wer"] == pytest.approx(1.0)


def test_entity_wer_hand_computed_all_entities_correct(synthetic_world, tmp_path):
    _setup_one_entity_wrong(synthetic_world)
    outputs = _write_outputs(
        tmp_path,
        [
            {
                "sample_id": "4000001",
                "carrier_lock_key": "earnings21-original",
                "text": "the acme corporation reported strong results in march 2020",
            }
        ],
    )
    lock = load_lock(synthetic_world.lock_path)
    scores = score_entity_wer_outputs(outputs, lock, synthetic_world.data_root)
    sample = scores["per_sample"][0]
    assert sample["entity_wer"] == 0.0
    assert sample["correct"] == 2
    assert sample["expected_total"] == 2


def test_entity_wer_hand_computed_all_entities_wrong(synthetic_world, tmp_path):
    _setup_one_entity_wrong(synthetic_world)
    outputs = _write_outputs(
        tmp_path,
        [
            {
                "sample_id": "4000001",
                "carrier_lock_key": "earnings21-original",
                # Both entity mentions garbled; every non-entity word intact.
                "text": "the xxxx yyyy reported strong results in zzzz wwww",
            }
        ],
    )
    lock = load_lock(synthetic_world.lock_path)
    scores = score_entity_wer_outputs(outputs, lock, synthetic_world.data_root)
    sample = scores["per_sample"][0]
    assert sample["correct"] == 0
    assert sample["entity_wer"] == pytest.approx(1.0)


def test_zero_entity_sample_reports_entity_wer_zero_not_via_recall(synthetic_world, tmp_path):
    """A sample with no gold entities at all must read entity_wer=0.0
    ("nothing to get wrong"), never 1.0 -- EntityScore.recall's own
    0.0-when-empty convention run through `1 - recall` would misleadingly
    read as a 100% error rate here."""

    nlp = synthetic_world.e21 / "transcripts" / "nlp_references" / "4000001.nlp"
    _write_nlp(nlp, [("hello", "[]"), ("world", "[]")])
    sidecar = synthetic_world.e21 / "transcripts" / "wer_tags" / "4000001.wer_tag.json"
    _write_sidecar(sidecar, {})
    outputs = _write_outputs(
        tmp_path,
        [{"sample_id": "4000001", "carrier_lock_key": "earnings21-original", "text": "hello world"}],
    )
    lock = load_lock(synthetic_world.lock_path)
    scores = score_entity_wer_outputs(outputs, lock, synthetic_world.data_root)
    sample = scores["per_sample"][0]
    assert sample["expected_total"] == 0
    assert sample["entity_wer"] == 0.0
    aggregate = scores["aggregate"]
    assert aggregate["samples"] == 1
    assert aggregate["samples_with_entities"] == 0
    assert aggregate["macro_entity_wer"] == 0.0
    assert aggregate["entity_wer"] == 0.0


def test_macro_entity_wer_excludes_zero_entity_samples(synthetic_world, tmp_path):
    """A second, zero-entity sample must not dilute the macro average -- it
    is excluded from ``macro_entity_wer`` (documented deviation from a naive
    all-samples mean; corpus-level ``entity_wer`` below is unaffected either
    way since it micro-averages over entity occurrences, not samples)."""

    _setup_one_entity_wrong(synthetic_world)
    nlp2 = synthetic_world.e21 / "transcripts" / "nlp_references" / "4000002.nlp"
    _write_nlp(nlp2, [("hello", "[]"), ("world", "[]")])
    sidecar2 = synthetic_world.e21 / "transcripts" / "wer_tags" / "4000002.wer_tag.json"
    _write_sidecar(sidecar2, {})
    outputs = _write_outputs(
        tmp_path,
        [
            {
                "sample_id": "4000001",
                "carrier_lock_key": "earnings21-original",
                "text": "the acme corporation reported strong results in march 2021",
            },
            {
                "sample_id": "4000002",
                "carrier_lock_key": "earnings21-original",
                "text": "hello world",
            },
        ],
    )
    lock = load_lock(synthetic_world.lock_path)
    scores = score_entity_wer_outputs(outputs, lock, synthetic_world.data_root)
    aggregate = scores["aggregate"]
    assert aggregate["samples"] == 2
    assert aggregate["samples_with_entities"] == 1
    assert aggregate["macro_entity_wer"] == pytest.approx(0.5)
    assert aggregate["entity_wer"] == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Fail-closed cases
# ---------------------------------------------------------------------------


def test_unsupported_carrier_fails_closed(synthetic_world, tmp_path):
    outputs = _write_outputs(
        tmp_path,
        [{"sample_id": "5000000", "carrier_lock_key": "earnings22-original", "text": "hello world"}],
    )
    lock = load_lock(synthetic_world.lock_path)
    with pytest.raises(ScoringPhaseError, match="entity layer"):
        score_entity_wer_outputs(outputs, lock, synthetic_world.data_root)


def test_missing_sidecar_fails_closed_through_scoring_phase_error(synthetic_world, tmp_path):
    nlp = synthetic_world.e21 / "transcripts" / "nlp_references" / "4000001.nlp"
    _write_nlp(nlp, [("Acme", "['0']")])
    sidecar = synthetic_world.e21 / "transcripts" / "wer_tags" / "4000001.wer_tag.json"
    sidecar.unlink()
    outputs = _write_outputs(
        tmp_path,
        [{"sample_id": "4000001", "carrier_lock_key": "earnings21-original", "text": "acme"}],
    )
    lock = load_lock(synthetic_world.lock_path)
    with pytest.raises(ScoringPhaseError, match="cannot resolve entity references"):
        score_entity_wer_outputs(outputs, lock, synthetic_world.data_root)


def test_empty_outputs_fail_closed(synthetic_world, tmp_path):
    path = tmp_path / "empty.outputs.jsonl"
    path.write_text("", encoding="utf-8")
    lock = load_lock(synthetic_world.lock_path)
    with pytest.raises(ScoringPhaseError, match="empty"):
        score_entity_wer_outputs(path, lock, synthetic_world.data_root)


def test_unreadable_outputs_path_fails_closed(synthetic_world, tmp_path):
    lock = load_lock(synthetic_world.lock_path)
    with pytest.raises(ScoringPhaseError, match="cannot read outputs"):
        score_entity_wer_outputs(tmp_path / "never-written.outputs.jsonl", lock, synthetic_world.data_root)


def test_malformed_json_line_fails_closed(synthetic_world, tmp_path):
    path = tmp_path / "bad.outputs.jsonl"
    path.write_text("{not json\n", encoding="utf-8")
    lock = load_lock(synthetic_world.lock_path)
    with pytest.raises(ScoringPhaseError, match="malformed"):
        score_entity_wer_outputs(path, lock, synthetic_world.data_root)


# ---------------------------------------------------------------------------
# score_bundle wiring: entity-wer is a legal configured scorer, and its
# reference-identity check is covered by the SAME widened gate asr-wer uses
# (IMPORTANT 2, widened by owner decision D-3).
# ---------------------------------------------------------------------------


def _commit_reference_d1_receipt(repo_root, carrier_lock_key, nlp_path):
    import hashlib
    import subprocess
    from pathlib import Path as _Path

    def _git(*args):
        subprocess.run(["git", *args], cwd=repo_root, check=True, capture_output=True, text=True)

    raw = nlp_path.read_bytes()
    sample_id = nlp_path.stem
    d1_document = {
        "carriers": {
            carrier_lock_key: {
                "layers": {
                    "nlp_references": {
                        "manifest": [
                            {"id": sample_id, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
                        ]
                    }
                }
            }
        }
    }
    receipts_dir = _Path(repo_root) / "docs" / "receipts"
    artifacts_dir = receipts_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    (artifacts_dir / "d1-identity.json").write_text(json.dumps(d1_document), encoding="utf-8")
    e0_document = {"deliverables": {"d1_identity": {"artifact": "artifacts/d1-identity.json"}}}
    (receipts_dir / "e0-closure.json").write_text(json.dumps(e0_document), encoding="utf-8")
    _git("add", "-A")
    _git("commit", "-q", "-m", "add reference-identity D1 receipt")


@pytest.fixture()
def clean_repo_root(tmp_path):
    import subprocess

    def _git(*args):
        subprocess.run(["git", *args], cwd=repo_root, check=True, capture_output=True, text=True)

    repo_root = tmp_path / "clean-repo"
    repo_root.mkdir()
    _git("init", "-q")
    _git("config", "user.email", "test@example.com")
    _git("config", "user.name", "Test")
    (repo_root / ".keep").write_text("", encoding="utf-8")
    _git("add", "-A")
    _git("commit", "-q", "-m", "init")
    return repo_root


def test_score_bundle_runs_entity_wer_over_a_genuine_bundle(
    tmp_path, synthetic_world, clean_repo_root
):
    _setup_one_entity_wrong(synthetic_world)
    _commit_reference_d1_receipt(
        clean_repo_root,
        "earnings21-original",
        synthetic_world.e21 / "transcripts" / "nlp_references" / "4000001.nlp",
    )
    outputs = _write_outputs(
        tmp_path,
        [
            {
                "sample_id": "4000001",
                "carrier_lock_key": "earnings21-original",
                "arm": "bare-core",
                "request_id": "req-0001",
                "text": "the acme corporation reported strong results in march 2020",
                "request_sha256": "0" * 64,
                "response_sha256": "0" * 64,
                "response_text_sha256": "0" * 64,
            }
        ],
        name="x.outputs.jsonl",
    )
    lock = load_lock(synthetic_world.lock_path)
    bundle = VerifiedBundle(
        manifest_path=tmp_path / "fake.run-manifest.json",
        manifest={"scorers": ["entity-wer"], "plan": {"carrier_lock_key": "earnings21-original"}},
        outputs_path=outputs,
        outputs_rows=(),
        trace_records={},
        split_ids=frozenset({"4000001"}),
        attempt_state="OPENED",
    )
    results = score_bundle(bundle, lock, synthetic_world.data_root, repo_root=clean_repo_root)
    assert results == {
        "entity-wer": score_entity_wer_outputs(outputs, lock, synthetic_world.data_root)
    }
    assert results["entity-wer"]["per_sample"][0]["entity_wer"] == 0.0
