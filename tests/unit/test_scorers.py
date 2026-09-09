"""Scorer adapters over the frozen stack; transition accounting from hit masks."""

import contextlib
import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.contracts import GateClosed
from speech_aware_evidence_acquisition.core import scorers  # noqa: F401 (registration)
from speech_aware_evidence_acquisition.core.base import SCORERS
from speech_aware_evidence_acquisition.core.bundle import BundleError, VerifiedBundle
from speech_aware_evidence_acquisition.core.bundle.git_commit import (
    require_clean_load_bearing_surface,
)
from speech_aware_evidence_acquisition.core.scorers import (
    ScoringPhaseError,
    score_bundle,
    transition_report,
)
from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT


def _write_outputs(tmp_path, rows):
    path = tmp_path / "x.outputs.jsonl"
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8"
    )
    return path


def _git(repo_root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo_root, check=True, capture_output=True, text=True)


@pytest.fixture()
def clean_repo_root(tmp_path):
    """An isolated, ACTUAL git repo distinct from this checkout's own
    REPO_ROOT -- used only for score_bundle's load-bearing-surface check
    (core.bundle.git_commit.require_clean_load_bearing_surface), never for
    the D3/scope check
    (which is always the real REPO_ROOT -- see
    core.scorers._assert_scoring_entry_gate's docstring for why). Isolating
    this check keeps these tests deterministic regardless of this checkout's
    own ambient git status during concurrent development."""

    repo_root = tmp_path / "clean-repo"
    repo_root.mkdir()
    _git(repo_root, "init", "-q")
    _git(repo_root, "config", "user.email", "test@example.com")
    _git(repo_root, "config", "user.name", "Test")
    (repo_root / ".keep").write_text("", encoding="utf-8")
    _git(repo_root, "add", "-A")
    _git(repo_root, "commit", "-q", "-m", "init")
    return repo_root


@contextlib.contextmanager
def _tamper_real_scoring_source():
    """CRITICAL-fix probes (round-2 external-threat-model review) need to
    prove score_bundle refuses when a REAL frozen scoring source is edited --
    the D3 freeze is bound to THIS checkout's actual scoring/ package, not
    any synthetic stand-in (see _assert_scoring_entry_gate's docstring).
    Mirrors the established, self-cleaning pattern already used against the
    real gate in tests/contract/test_real_receipts.py: the file is restored
    to its EXACT original bytes in `finally`, so this never leaves the
    checkout modified even if the assertion inside the `with` block fails."""

    path = REPO_ROOT / "src" / "speech_aware_evidence_acquisition" / "scoring" / "wer.py"
    original = path.read_bytes()
    try:
        path.write_bytes(original + b"\n# tampered-by-round2-review-test\n")
        yield path
    finally:
        path.write_bytes(original)


def test_asr_wer_scores_against_references(synthetic_world, tmp_path):
    nlp = synthetic_world.e21 / "transcripts" / "nlp_references" / "4000001.nlp"
    nlp.write_text("token|tags\nhello|\nworld|\n", encoding="utf-8")
    outputs = _write_outputs(
        tmp_path,
        [{"sample_id": "4000001", "carrier_lock_key": "earnings21-original",
          "arm": "bare-core", "request_id": "req-0001", "text": "hello world",
          "request_sha256": "0" * 64, "response_sha256": "0" * 64}],
    )
    lock = load_lock(synthetic_world.lock_path)
    scores = SCORERS.resolve("asr-wer")(outputs, lock, synthetic_world.data_root)
    assert scores["aggregate"] == {"mean_wer": 0.0, "samples": 1}
    assert scores["per_sample"][0]["ref_hit_mask"] == [True, True]


def test_text_containing_unicode_line_separator_round_trips(tmp_path, synthetic_world):
    """json.dumps(ensure_ascii=False) (the driver's own write style) leaves
    U+2028/U+2029 raw inside string values; the reader must split records on
    "\\n" only, not str.splitlines(), or a hit response text containing one of
    these characters cuts a single valid JSONL row in two."""

    nlp = synthetic_world.e21 / "transcripts" / "nlp_references" / "4000001.nlp"
    nlp.write_text("token|tags\nhello|\nworld|\n", encoding="utf-8")
    row = {
        "sample_id": "4000001", "carrier_lock_key": "earnings21-original",
        "arm": "bare-core", "request_id": "req-0001",
        "text": "hello world",
        "request_sha256": "0" * 64, "response_sha256": "0" * 64,
    }
    path = tmp_path / "u2028.outputs.jsonl"
    path.write_text(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8"
    )
    lock = load_lock(synthetic_world.lock_path)
    scores = SCORERS.resolve("asr-wer")(path, lock, synthetic_world.data_root)
    assert scores["aggregate"] == {"mean_wer": 0.0, "samples": 1}


def test_empty_outputs_fail_closed(tmp_path, synthetic_world):
    path = tmp_path / "empty.outputs.jsonl"
    path.write_text("", encoding="utf-8")
    lock = load_lock(synthetic_world.lock_path)
    with pytest.raises(ScoringPhaseError, match="empty"):
        SCORERS.resolve("asr-wer")(path, lock, synthetic_world.data_root)


def test_transition_report_counts_mask_flips():
    baseline = {"per_sample": [{"sample_id": "a", "ref_hit_mask": [True, False, True]}]}
    treatment = {"per_sample": [{"sample_id": "a", "ref_hit_mask": [True, True, False]}]}
    report = transition_report(baseline, treatment)
    assert report == {
        "correct_to_correct": 1,
        "correct_to_wrong": 1,
        "wrong_to_correct": 1,
        "wrong_to_wrong": 0,
    }


def test_transition_report_fails_closed_on_mismatch():
    with pytest.raises(ScoringPhaseError, match="differ"):
        transition_report(
            {"per_sample": [{"sample_id": "a", "ref_hit_mask": [True]}]},
            {"per_sample": [{"sample_id": "b", "ref_hit_mask": [True]}]},
        )


# ---------------------------------------------------------------------------
# score_bundle: R0 repair T6 (I7) manifest-entry scoring seam. "Refuse to
# score an unverified bundle" is enforced structurally -- only a genuine
# core.bundle.VerifiedBundle is accepted, never a bare path or dict.
# ---------------------------------------------------------------------------


def _outputs_path(tmp_path, synthetic_world):
    nlp = synthetic_world.e21 / "transcripts" / "nlp_references" / "4000001.nlp"
    nlp.write_text("token|tags\nhello|\nworld|\n", encoding="utf-8")
    return _write_outputs(
        tmp_path,
        [{"sample_id": "4000001", "carrier_lock_key": "earnings21-original",
          "arm": "bare-core", "request_id": "req-0001", "text": "hello world",
          "request_sha256": "0" * 64, "response_sha256": "0" * 64,
          "response_text_sha256": "0" * 64}],
    )


def _commit_reference_d1_receipt(repo_root: Path, carrier_lock_key: str, nlp_path: Path) -> None:
    """IMPORTANT 2 (fix-wave3, external-threat-model review round 3):
    ``core.scorers._assert_scoring_entry_gate`` now re-verifies the
    reference (``.nlp``) bytes ``score_asr_outputs`` is about to read
    against a D1 identity artifact bound to ``repo_root`` (the SAME
    test-overridable parameter ``require_clean_study_repo`` already uses --
    see ``_assert_scoring_entry_gate``'s own docstring for why this is sound
    for a DATA-identity receipt, unlike the D3 SOURCE-CODE freeze). Writes
    and commits a minimal, genuinely matching one -- computed from
    ``nlp_path``'s CURRENT bytes, so it can never be out of sync with them --
    into ``repo_root``'s own ``docs/receipts/``, mirroring
    ``tests/contract/test_media_identity.py``'s synthetic-D1-artifact
    pattern for ``verify_media_identity``."""

    raw = nlp_path.read_bytes()
    sample_id = nlp_path.stem
    d1_document = {
        "carriers": {
            carrier_lock_key: {
                "layers": {
                    "nlp_references": {
                        "manifest": [
                            {
                                "id": sample_id,
                                "bytes": len(raw),
                                "sha256": hashlib.sha256(raw).hexdigest(),
                            }
                        ]
                    }
                }
            }
        }
    }
    receipts_dir = repo_root / "docs" / "receipts"
    artifacts_dir = receipts_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    (artifacts_dir / "d1-identity.json").write_text(json.dumps(d1_document), encoding="utf-8")
    e0_document = {"deliverables": {"d1_identity": {"artifact": "artifacts/d1-identity.json"}}}
    (receipts_dir / "e0-closure.json").write_text(json.dumps(e0_document), encoding="utf-8")
    _git(repo_root, "add", "-A")
    _git(repo_root, "commit", "-q", "-m", "add reference-identity D1 receipt")


@pytest.mark.parametrize("not_a_bundle", ["some/path.jsonl", {"outputs_path": "x"}, None, 7])
def test_score_bundle_refuses_anything_but_a_verified_bundle(tmp_path, synthetic_world, not_a_bundle):
    lock = load_lock(synthetic_world.lock_path)
    with pytest.raises(ScoringPhaseError, match="VerifiedBundle"):
        score_bundle(not_a_bundle, lock, synthetic_world.data_root)


_VALID_PLAN_META = {"carrier_lock_key": "earnings21-original"}


def test_score_bundle_runs_configured_scorers_over_a_genuine_bundle(
    tmp_path, synthetic_world, clean_repo_root
):
    outputs = _outputs_path(tmp_path, synthetic_world)
    _commit_reference_d1_receipt(
        clean_repo_root,
        "earnings21-original",
        synthetic_world.e21 / "transcripts" / "nlp_references" / "4000001.nlp",
    )
    lock = load_lock(synthetic_world.lock_path)
    bundle = VerifiedBundle(
        manifest_path=tmp_path / "fake.run-manifest.json",
        manifest={"scorers": ["asr-wer"], "plan": _VALID_PLAN_META},
        outputs_path=outputs,
        outputs_rows=(),
        trace_records={},
        split_ids=frozenset({"4000001"}),
        attempt_state="OPENED",
    )
    results = score_bundle(bundle, lock, synthetic_world.data_root, repo_root=clean_repo_root)
    assert results == {"asr-wer": SCORERS.resolve("asr-wer")(outputs, lock, synthetic_world.data_root)}


def test_score_bundle_refuses_when_no_scorers_are_configured(
    tmp_path, synthetic_world, clean_repo_root
):
    outputs = _outputs_path(tmp_path, synthetic_world)
    lock = load_lock(synthetic_world.lock_path)
    bundle = VerifiedBundle(
        manifest_path=tmp_path / "fake.run-manifest.json",
        manifest={"scorers": [], "plan": _VALID_PLAN_META},
        outputs_path=outputs,
        outputs_rows=(),
        trace_records={},
        split_ids=frozenset({"4000001"}),
        attempt_state="OPENED",
    )
    with pytest.raises(ScoringPhaseError, match="no configured scorers"):
        score_bundle(bundle, lock, synthetic_world.data_root, repo_root=clean_repo_root)


# ---------------------------------------------------------------------------
# CRITICAL fix (round-2 external-threat-model review): score_bundle now
# re-verifies the D3 scoring-source freeze, this study's speech-only carrier
# scope, and a clean study tree BEFORE any scorer runs -- see
# core.scorers._assert_scoring_entry_gate's docstring. Required probes: edit
# a frozen scoring source -> refuse; a general-audio carrier -> refuse; a
# dirty tree -> refuse; an unmodified tree + legitimate bundle (the tests
# just above) -> still scores.
# ---------------------------------------------------------------------------


def test_score_bundle_refuses_when_a_frozen_scoring_source_is_edited(
    tmp_path, synthetic_world, clean_repo_root
):
    outputs = _outputs_path(tmp_path, synthetic_world)
    lock = load_lock(synthetic_world.lock_path)
    bundle = VerifiedBundle(
        manifest_path=tmp_path / "fake.run-manifest.json",
        manifest={"scorers": ["asr-wer"], "plan": _VALID_PLAN_META},
        outputs_path=outputs,
        outputs_rows=(),
        trace_records={},
        split_ids=frozenset({"4000001"}),
        attempt_state="OPENED",
    )
    with _tamper_real_scoring_source():
        with pytest.raises(GateClosed, match="freeze drift"):
            score_bundle(bundle, lock, synthetic_world.data_root, repo_root=clean_repo_root)


def test_score_bundle_refuses_a_general_audio_carrier(tmp_path, synthetic_world, clean_repo_root):
    outputs = _outputs_path(tmp_path, synthetic_world)
    lock = json.loads(Path(synthetic_world.lock_path).read_text(encoding="utf-8"))
    lock["datasets"].append(
        {"name": "fsd50k", "kind": "dataset", "profiles": ["retained-cross-domain"]}
    )
    bundle = VerifiedBundle(
        manifest_path=tmp_path / "fake.run-manifest.json",
        manifest={"scorers": ["asr-wer"], "plan": {"carrier_lock_key": "fsd50k"}},
        outputs_path=outputs,
        outputs_rows=(),
        trace_records={},
        split_ids=frozenset({"4000001"}),
        attempt_state="OPENED",
    )
    with pytest.raises(GateClosed, match="general-audio"):
        score_bundle(bundle, lock, synthetic_world.data_root, repo_root=clean_repo_root)


def _asr_bundle(tmp_path, outputs):
    return VerifiedBundle(
        manifest_path=tmp_path / "fake.run-manifest.json",
        manifest={"scorers": ["asr-wer"], "plan": _VALID_PLAN_META},
        outputs_path=outputs,
        outputs_rows=(),
        trace_records={},
        split_ids=frozenset({"4000001"}),
        attempt_state="OPENED",
    )


@pytest.mark.parametrize(
    "relpath",
    [
        "src/tampered.py",
        "configs/tampered.json",
        "docs/arms/tampered.arms",
        "scripts/tampered.sh",
    ],
)
def test_score_bundle_refuses_dirt_inside_the_load_bearing_surface(
    tmp_path, synthetic_world, clean_repo_root, relpath
):
    """Every file whose bytes can change a score is inside the load-bearing
    surface -- the driver's own ``src/`` (``data.references``, which the D3
    freeze over ``scoring/*.py`` does NOT cover, lives there), the composed
    ``configs/``, the committed arm files and the launch ``scripts/`` -- and
    an uncommitted edit to any of them still refuses before a scorer runs."""

    outputs = _outputs_path(tmp_path, synthetic_world)
    _commit_reference_d1_receipt(
        clean_repo_root,
        "earnings21-original",
        synthetic_world.e21 / "transcripts" / "nlp_references" / "4000001.nlp",
    )
    lock = load_lock(synthetic_world.lock_path)
    target = clean_repo_root / relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("tampered before scoring", encoding="utf-8")
    with pytest.raises(BundleError, match="load-bearing"):
        score_bundle(
            _asr_bundle(tmp_path, outputs),
            lock,
            synthetic_world.data_root,
            repo_root=clean_repo_root,
        )


def test_score_bundle_scores_through_dirt_outside_the_load_bearing_surface(
    tmp_path, synthetic_world, clean_repo_root
):
    """REGRESSION (2026-09-09): what SEALS must SCORE.

    ``core.bundle.git_commit._study_commit_for_completed_manifest`` binds a
    COMPLETED manifest over dirt confined outside the load-bearing surface
    (the 2026-08-16 flight-protection fix) and records it. This gate used to
    call ``require_clean_study_repo``, which refuses ANY dirt, so the same
    tree that sealed a manifest could never score or finalize it -- the
    2026-08-16 incident moved one step later. Measured on 2026-09-09 as the
    four Audio2Tool wire-check cells' ``seal_and_score = SCORING_FAILED`` /
    "official scorer exited with status 1" over ONE untracked readiness note
    (``docs/checks/speech-aware-evidence-acquisition/
    2026-09-09-a2t-official-scorer-seal-and-score-diagnosis/``).

    The dirt is placed directly under ``docs/`` -- already tracked here, via
    the D1 receipt committed just above -- because an entirely new, wholly
    untracked directory collapses in ``git status --porcelain`` to its own
    directory entry, which is not the shape a governance-doc edit takes in
    the real study repo."""

    outputs = _outputs_path(tmp_path, synthetic_world)
    _commit_reference_d1_receipt(
        clean_repo_root,
        "earnings21-original",
        synthetic_world.e21 / "transcripts" / "nlp_references" / "4000001.nlp",
    )
    lock = load_lock(synthetic_world.lock_path)
    governance_doc = clean_repo_root / "docs" / "2026-09-09-mid-flight-note.md"
    governance_doc.write_text("a readiness note landed mid-flight", encoding="utf-8")
    # The seal half tolerates exactly this and records it; the score half
    # must agree, or a sealed COMPLETED manifest is unfinalizable.
    commit, tolerated = require_clean_load_bearing_surface(clean_repo_root)
    assert len(commit) == 40
    assert tolerated == ["docs/2026-09-09-mid-flight-note.md"]
    results = score_bundle(
        _asr_bundle(tmp_path, outputs),
        lock,
        synthetic_world.data_root,
        repo_root=clean_repo_root,
    )
    assert set(results) == {"asr-wer"}


# ---------------------------------------------------------------------------
# `cost` scorer (R0 repair T8, scorer seam): reads the SIBLING run manifest's
# `cost` block (same run_dir, same run_id stem as outputs_path -- the naming
# convention `core.bundle.build_manifest` already uses), never a parallel
# accounting path.
# ---------------------------------------------------------------------------


def _write_manifest(tmp_path, run_id, cost, schema=None):
    from speech_aware_evidence_acquisition.core.bundle import RUN_MANIFEST_SCHEMA

    manifest_path = tmp_path / f"{run_id}.run-manifest.json"
    document = {"schema": schema or RUN_MANIFEST_SCHEMA, "cost": cost}
    manifest_path.write_text(json.dumps(document), encoding="utf-8")
    return manifest_path


def test_cost_scorer_is_registered():
    assert "cost" in SCORERS.names()


def test_cost_scorer_reads_the_sibling_run_manifest(tmp_path):
    run_id = "SAEA-E-000-cost"
    outputs_path = tmp_path / f"{run_id}.outputs.jsonl"
    outputs_path.write_text("", encoding="utf-8")
    cost = {
        "calls_used": 3,
        "audio_seconds_used": 12.5,
        "latency_seconds_total": 1.2,
        "prompt_tokens_total": 30,
        "completion_tokens_total": 9,
    }
    _write_manifest(tmp_path, run_id, cost)
    result = SCORERS.resolve("cost")(outputs_path, {}, tmp_path)
    assert result == {"per_sample": [], "aggregate": cost}


def test_cost_scorer_refuses_outputs_path_with_wrong_suffix(tmp_path):
    bad_path = tmp_path / "not-an-outputs-file.jsonl"
    with pytest.raises(ScoringPhaseError, match="outputs artifact named"):
        SCORERS.resolve("cost")(bad_path, {}, tmp_path)


def test_cost_scorer_refuses_missing_sibling_manifest(tmp_path):
    outputs_path = tmp_path / "SAEA-E-000-missing.outputs.jsonl"
    outputs_path.write_text("", encoding="utf-8")
    with pytest.raises(ScoringPhaseError, match="sibling run manifest"):
        SCORERS.resolve("cost")(outputs_path, {}, tmp_path)


def test_cost_scorer_refuses_malformed_manifest_json(tmp_path):
    """MINOR (review): score_cost_outputs's malformed-JSON branch was
    implemented but untested -- a sibling manifest file that exists but is
    not valid JSON must fail closed with a clear message, not a bare
    json.JSONDecodeError leaking out of the scorer."""

    run_id = "SAEA-E-000-badjson"
    outputs_path = tmp_path / f"{run_id}.outputs.jsonl"
    outputs_path.write_text("", encoding="utf-8")
    manifest_path = tmp_path / f"{run_id}.run-manifest.json"
    manifest_path.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(ScoringPhaseError, match="not valid JSON"):
        SCORERS.resolve("cost")(outputs_path, {}, tmp_path)


def test_cost_scorer_refuses_wrong_manifest_schema(tmp_path):
    run_id = "SAEA-E-000-badschema"
    outputs_path = tmp_path / f"{run_id}.outputs.jsonl"
    outputs_path.write_text("", encoding="utf-8")
    _write_manifest(tmp_path, run_id, {"calls_used": 1}, schema="not-the-real-schema")
    with pytest.raises(ScoringPhaseError, match="schema"):
        SCORERS.resolve("cost")(outputs_path, {}, tmp_path)


def test_cost_scorer_refuses_manifest_with_no_cost_block(tmp_path):
    run_id = "SAEA-E-000-nocost"
    outputs_path = tmp_path / f"{run_id}.outputs.jsonl"
    outputs_path.write_text("", encoding="utf-8")
    _write_manifest(tmp_path, run_id, None)
    with pytest.raises(ScoringPhaseError, match="no cost block"):
        SCORERS.resolve("cost")(outputs_path, {}, tmp_path)


def test_score_bundle_runs_the_cost_scorer_over_a_genuine_bundle(
    tmp_path, synthetic_world, clean_repo_root
):
    outputs = _outputs_path(tmp_path, synthetic_world)  # tmp_path / "x.outputs.jsonl"
    cost = {
        "calls_used": 1,
        "audio_seconds_used": 2.0,
        "latency_seconds_total": 0.5,
        "prompt_tokens_total": 3,
        "completion_tokens_total": 4,
    }
    _write_manifest(tmp_path, "x", cost)
    lock = load_lock(synthetic_world.lock_path)
    bundle = VerifiedBundle(
        manifest_path=tmp_path / "fake.run-manifest.json",
        manifest={"scorers": ["cost"], "plan": _VALID_PLAN_META},
        outputs_path=outputs,
        outputs_rows=(),
        trace_records={},
        split_ids=frozenset({"4000001"}),
        attempt_state="OPENED",
    )
    results = score_bundle(bundle, lock, synthetic_world.data_root, repo_root=clean_repo_root)
    assert results == {"cost": {"per_sample": [], "aggregate": cost}}


def test_score_bundle_refuses_when_outputs_path_is_missing(tmp_path, synthetic_world):
    lock = load_lock(synthetic_world.lock_path)
    bundle = VerifiedBundle(
        manifest_path=tmp_path / "fake.run-manifest.json",
        manifest={"scorers": ["asr-wer"]},
        outputs_path=None,
        outputs_rows=(),
        trace_records={},
        split_ids=frozenset(),
        attempt_state="ABORTED",
    )
    with pytest.raises(ScoringPhaseError, match="no outputs artifact"):
        score_bundle(bundle, lock, synthetic_world.data_root)
