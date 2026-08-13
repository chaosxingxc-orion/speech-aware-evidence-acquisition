"""``core.candidate_materializer`` (Part 2, offline retrieval-gated candidate
materializer): tmpdir fixtures only, never real run outputs or real ConEC
data -- this module is a WRITER over a fake draft run + fake pack files."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.candidate_materializer import (
    MANIFEST_SCHEMA,
    DraftSample,
    MaterializeError,
    _cli_parser,
    find_newest_attempt_dir,
    find_outputs_file,
    load_draft_samples,
    materialize,
    materialize_sample,
    pack_candidates,
)
from speech_aware_evidence_acquisition.data.lock import load_lock

# ---------------------------------------------------------------------------
# Shared fixture: a fake controlled data root with just enough of a "conec"
# lock asset to exercise conec-contexts/conec-names, plus a fake draft run.
# ---------------------------------------------------------------------------

SAMPLE_ID = "4000001"
CONTEXT_CONTENT = "danaher corporation revenue growth unrelated tokenzzz filler padding words extra\n"
NAMES_CONTENT = "danaher - CEO\ncorporation - Something\nunrelated person - Nobody\n"
# Correction semantics (materialize_sample, 2026-08-13): a pack candidate
# verbatim-present in the draft is dropped before scoring, so a fixture
# using the SAME spellings in both would filter its own signal down to
# nothing. This hypothesis instead uses plausible ASR-typo variants of
# CONTEXT_CONTENT/NAMES_CONTENT's terms (danahr/corperation/revenuw/groath
# for danaher/corporation/revenue/growth) -- none of them equal a pack
# candidate verbatim, so all four survive the filter and are ranked by
# fuzzy/phonetic score, exactly the shape a real garbled ASR draft produces
# (verified: corporation=0.955, danaher=0.929, revenue=0.804, growth=0.792
# against this draft -- see the four MIN_SCORE-gated tests below).
DRAFT_HYPOTHESIS = "quarterly revenuw exceeded expectations danahr corperation groath"
MIN_SCORE = 0.75


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _build_world(tmp_path: Path) -> SimpleNamespace:
    data_root = tmp_path / "speechrl-data"
    lock_path = tmp_path / "datasets.lock.json"
    lock_path.write_text(
        json.dumps(
            {
                "datasets": [
                    {"name": "earnings21-original", "local_subdir": "datasets/earnings21-22/earnings21"},
                    {"name": "conec", "local_subdir": "datasets/conec"},
                ]
            }
        ),
        encoding="utf-8",
    )
    conec = data_root / "datasets" / "conec"
    _write(conec / "earnings21" / "contexts" / f"{SAMPLE_ID}.txt", CONTEXT_CONTENT)
    _write(
        conec / "earnings21" / "contexts" / "participant_names" / f"{SAMPLE_ID}.names.txt",
        NAMES_CONTENT,
    )
    return SimpleNamespace(data_root=data_root, lock_path=lock_path)


def _write_outputs_row(handle, *, sample_id, carrier_lock_key, text, request_id="req-0001"):
    handle.write(
        json.dumps(
            {
                "request_id": request_id,
                "sample_id": sample_id,
                "carrier_lock_key": carrier_lock_key,
                "arm": "B0",
                "text": text,
                "admitted": True,
            },
            ensure_ascii=False,
        )
        + "\n"
    )


def _write_draft_run(data_root: Path, run_id: str, *, attempt_id: str, hypothesis: str) -> Path:
    attempt_dir = data_root / "runs" / run_id / attempt_id
    attempt_dir.mkdir(parents=True, exist_ok=True)
    outputs_path = attempt_dir / f"{run_id}.outputs.jsonl"
    with outputs_path.open("w", encoding="utf-8") as handle:
        _write_outputs_row(
            handle, sample_id=SAMPLE_ID, carrier_lock_key="earnings21-original", text=hypothesis
        )
    return attempt_dir


# ---------------------------------------------------------------------------
# find_newest_attempt_dir / find_outputs_file
# ---------------------------------------------------------------------------


def test_find_newest_attempt_dir_picks_the_latest_mtime(tmp_path):
    run_dir = tmp_path / "runs" / "X"
    older = run_dir / "attempt-20260812T090000Z-aaaaaa"
    newer = run_dir / "attempt-20260812T100000Z-bbbbbb"
    older.mkdir(parents=True)
    newer.mkdir(parents=True)
    now = datetime.now().timestamp()
    os.utime(older, (now - 100, now - 100))
    os.utime(newer, (now, now))

    assert find_newest_attempt_dir(run_dir) == newer


def test_find_newest_attempt_dir_refuses_when_run_dir_missing(tmp_path):
    with pytest.raises(MaterializeError, match="does not exist"):
        find_newest_attempt_dir(tmp_path / "runs" / "nope")


def test_find_newest_attempt_dir_refuses_when_no_attempt_dirs(tmp_path):
    run_dir = tmp_path / "runs" / "X"
    run_dir.mkdir(parents=True)
    with pytest.raises(MaterializeError, match="no attempt-\\* subdirectories"):
        find_newest_attempt_dir(run_dir)


def test_find_outputs_file_refuses_when_none(tmp_path):
    attempt_dir = tmp_path / "attempt-a"
    attempt_dir.mkdir()
    with pytest.raises(MaterializeError, match="no \\*.outputs.jsonl"):
        find_outputs_file(attempt_dir)


def test_find_outputs_file_refuses_when_ambiguous(tmp_path):
    attempt_dir = tmp_path / "attempt-a"
    attempt_dir.mkdir()
    (attempt_dir / "X.outputs.jsonl").write_text("{}\n", encoding="utf-8")
    (attempt_dir / "Y.outputs.jsonl").write_text("{}\n", encoding="utf-8")
    with pytest.raises(MaterializeError, match="multiple"):
        find_outputs_file(attempt_dir)


def test_find_outputs_file_picks_the_one_match(tmp_path):
    attempt_dir = tmp_path / "attempt-a"
    attempt_dir.mkdir()
    expected = attempt_dir / "X.outputs.jsonl"
    expected.write_text("{}\n", encoding="utf-8")
    assert find_outputs_file(attempt_dir) == expected


# ---------------------------------------------------------------------------
# load_draft_samples: sample_id + the longest OTHER string field, stitched.
# ---------------------------------------------------------------------------


def test_load_draft_samples_picks_the_longest_string_field(tmp_path):
    outputs_path = tmp_path / "run.outputs.jsonl"
    with outputs_path.open("w", encoding="utf-8") as handle:
        # "text" is the longest string field besides sample_id -- the row's
        # other fields (request_id, carrier_lock_key, arm) are all shorter.
        _write_outputs_row(
            handle, sample_id="s1", carrier_lock_key="earnings21-original", text="the quick brown fox"
        )
    drafts = load_draft_samples(outputs_path)
    assert set(drafts) == {"s1"}
    assert drafts["s1"].hypothesis == "the quick brown fox"
    assert drafts["s1"].carrier_lock_key == "earnings21-original"


def test_load_draft_samples_stitches_multiple_rows_for_the_same_sample(tmp_path):
    outputs_path = tmp_path / "run.outputs.jsonl"
    with outputs_path.open("w", encoding="utf-8") as handle:
        _write_outputs_row(handle, sample_id="s1", carrier_lock_key="earnings21-original", text="first part")
        _write_outputs_row(
            handle, sample_id="s1", carrier_lock_key="earnings21-original", text="second part", request_id="req-0002"
        )
    drafts = load_draft_samples(outputs_path)
    assert drafts["s1"].hypothesis == "first part second part"


def test_load_draft_samples_refuses_on_missing_sample_id(tmp_path):
    outputs_path = tmp_path / "run.outputs.jsonl"
    outputs_path.write_text(json.dumps({"carrier_lock_key": "x", "text": "hi"}) + "\n", encoding="utf-8")
    with pytest.raises(MaterializeError, match="sample_id"):
        load_draft_samples(outputs_path)


def test_load_draft_samples_refuses_on_missing_carrier_lock_key(tmp_path):
    outputs_path = tmp_path / "run.outputs.jsonl"
    outputs_path.write_text(json.dumps({"sample_id": "s1", "text": "hi"}) + "\n", encoding="utf-8")
    with pytest.raises(MaterializeError, match="carrier_lock_key"):
        load_draft_samples(outputs_path)


def test_load_draft_samples_refuses_on_conflicting_carrier_lock_key(tmp_path):
    outputs_path = tmp_path / "run.outputs.jsonl"
    with outputs_path.open("w", encoding="utf-8") as handle:
        _write_outputs_row(handle, sample_id="s1", carrier_lock_key="earnings21-original", text="a")
        _write_outputs_row(handle, sample_id="s1", carrier_lock_key="earnings22-original", text="b", request_id="req-0002")
    with pytest.raises(MaterializeError, match="two different"):
        load_draft_samples(outputs_path)


def test_load_draft_samples_refuses_on_invalid_json(tmp_path):
    outputs_path = tmp_path / "run.outputs.jsonl"
    outputs_path.write_text("not json\n", encoding="utf-8")
    with pytest.raises(MaterializeError, match="invalid JSON"):
        load_draft_samples(outputs_path)


def test_load_draft_samples_refuses_when_no_usable_rows(tmp_path):
    outputs_path = tmp_path / "run.outputs.jsonl"
    outputs_path.write_text("\n\n", encoding="utf-8")
    with pytest.raises(MaterializeError, match="no usable rows"):
        load_draft_samples(outputs_path)


def test_load_draft_samples_refuses_when_row_has_no_other_string_field(tmp_path):
    outputs_path = tmp_path / "run.outputs.jsonl"
    outputs_path.write_text(
        json.dumps({"sample_id": "s1", "carrier_lock_key": "x", "admitted": True}) + "\n", encoding="utf-8"
    )
    with pytest.raises(MaterializeError, match="no non-empty string field"):
        load_draft_samples(outputs_path)


# ---------------------------------------------------------------------------
# pack_candidates: conec-contexts (unique >3-char tokens) vs conec-names
# (name part before " - ").
# ---------------------------------------------------------------------------


def test_pack_candidates_conec_contexts_splits_unique_terms_over_three_chars():
    candidates = pack_candidates("conec-contexts", "abc abcd abcd wxyz ab cdef")
    # "abc"/"ab" are <=3 chars and dropped; "abcd" appears twice but is
    # deduplicated; order is first-seen.
    assert candidates == ["abcd", "wxyz", "cdef"]


def test_pack_candidates_conec_names_takes_the_name_before_the_dash():
    candidates = pack_candidates("conec-names", "Jane Doe - CEO\n\nJohn Roe - CFO\n")
    assert candidates == ["Jane Doe", "John Roe"]


def test_pack_candidates_refuses_an_unsupported_source():
    with pytest.raises(MaterializeError, match="unsupported --pack-source"):
        pack_candidates("conec-bias-list", "irrelevant")


# ---------------------------------------------------------------------------
# materialize_sample: the retrieval gate itself.
# ---------------------------------------------------------------------------


def test_materialize_sample_ranks_fuzzy_matches_by_score_descending():
    """Correction semantics (materialize_sample): CONTEXT_CONTENT's four
    correctly-spelled terms are never verbatim-present in DRAFT_HYPOTHESIS's
    typo'd forms, so none are dropped by the new filter -- they rank by
    fuzzy/phonetic score, not tied at 1.0 and not alphabetically."""

    draft = DraftSample(sample_id=SAMPLE_ID, carrier_lock_key="earnings21-original", hypothesis=DRAFT_HYPOTHESIS)
    retrieved = materialize_sample(draft, CONTEXT_CONTENT, "conec-contexts", k=10, min_score=MIN_SCORE)
    assert [candidate for candidate, _score in retrieved] == ["corporation", "danaher", "revenue", "growth"]
    scores = [score for _candidate, score in retrieved]
    assert scores == sorted(scores, reverse=True)
    assert all(MIN_SCORE <= score < 1.0 for score in scores)


def test_materialize_sample_respects_k():
    draft = DraftSample(sample_id=SAMPLE_ID, carrier_lock_key="earnings21-original", hypothesis=DRAFT_HYPOTHESIS)
    retrieved = materialize_sample(draft, CONTEXT_CONTENT, "conec-contexts", k=2, min_score=MIN_SCORE)
    assert [candidate for candidate, _score in retrieved] == ["corporation", "danaher"]


def test_materialize_sample_refuses_when_hypothesis_has_no_query_terms():
    draft = DraftSample(sample_id=SAMPLE_ID, carrier_lock_key="earnings21-original", hypothesis="a to be an")
    with pytest.raises(MaterializeError, match="no query terms"):
        materialize_sample(draft, CONTEXT_CONTENT, "conec-contexts", k=10, min_score=0.5)


def test_materialize_sample_refuses_when_pack_has_no_candidates():
    draft = DraftSample(sample_id=SAMPLE_ID, carrier_lock_key="earnings21-original", hypothesis=DRAFT_HYPOTHESIS)
    with pytest.raises(MaterializeError, match="no candidates"):
        materialize_sample(draft, "ab cd ef", "conec-contexts", k=10, min_score=0.5)


# ---------------------------------------------------------------------------
# Correction semantics itself (materialize_sample, 2026-08-13 fix): a pack
# candidate verbatim-present in the draft (post normalize_term) is dropped
# before scoring -- even though an exact match would otherwise score 1.0 and
# flood the top-k -- and the all-filtered case fails closed with its own
# named message rather than falling through to core.retrieval.retrieve's
# unrelated "no candidates" refusal.
# ---------------------------------------------------------------------------


def test_materialize_sample_never_returns_a_candidate_verbatim_present_in_the_draft():
    draft = DraftSample(sample_id=SAMPLE_ID, carrier_lock_key="earnings21-original", hypothesis=DRAFT_HYPOTHESIS)
    # "danahr" is verbatim one of DRAFT_HYPOTHESIS's own query terms (a
    # pre-existing pack candidate could coincide with the draft's own
    # -- garbled -- wording); it would score 1.0 against itself, exactly the
    # inversion the fix (commit 4a78dfa) exists to prevent.
    pack_content = CONTEXT_CONTENT.strip() + " danahr\n"
    retrieved = materialize_sample(draft, pack_content, "conec-contexts", k=10, min_score=MIN_SCORE)
    returned = [candidate for candidate, _score in retrieved]
    assert "danahr" not in returned
    assert "danaher" in returned  # the non-verbatim fuzzy variant still survives


def test_materialize_sample_refuses_when_every_candidate_is_verbatim_present():
    draft = DraftSample(sample_id=SAMPLE_ID, carrier_lock_key="earnings21-original", hypothesis=DRAFT_HYPOTHESIS)
    # Every token here is verbatim one of DRAFT_HYPOTHESIS's own query terms,
    # so the correction-semantics filter empties the pool completely.
    pack_content = "danahr corperation groath"
    with pytest.raises(MaterializeError, match="nothing to supply"):
        materialize_sample(draft, pack_content, "conec-contexts", k=10, min_score=0.5)


# ---------------------------------------------------------------------------
# materialize(): the full offline pipeline.
# ---------------------------------------------------------------------------


def test_materialize_writes_candidate_files_and_a_manifest(tmp_path):
    world = _build_world(tmp_path)
    lock = load_lock(world.lock_path)
    _write_draft_run(world.data_root, "draft-run-1", attempt_id="attempt-20260812T090000Z-aaaaaa", hypothesis=DRAFT_HYPOTHESIS)

    result = materialize(
        lock=lock, root=world.data_root, draft_run="draft-run-1", pack_source="conec-contexts",
        k=10, min_score=MIN_SCORE, out_id="mat-test-1",
        now=lambda: datetime(2026, 8, 12, tzinfo=timezone.utc),
    )

    candidate_path = result.out_dir / f"{SAMPLE_ID}.candidates.txt"
    assert candidate_path.read_text(encoding="utf-8") == "corporation\ndanaher\nrevenue\ngrowth\n"
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema"] == MANIFEST_SCHEMA
    assert manifest["materialization_id"] == "mat-test-1"
    assert manifest["inputs"]["draft_run"] == "draft-run-1"
    assert manifest["inputs"]["pack_source"] == "conec-contexts"
    assert manifest["params"] == {"k": 10, "min_score": MIN_SCORE}
    assert manifest["samples"][SAMPLE_ID]["candidate_count"] == 4
    assert len(manifest["samples"][SAMPLE_ID]["sha256"]) == 64
    assert manifest["generated_at"] == "2026-08-12T00:00:00+00:00"


def test_materialize_conec_names_pack_source(tmp_path):
    world = _build_world(tmp_path)
    lock = load_lock(world.lock_path)
    _write_draft_run(world.data_root, "draft-run-2", attempt_id="attempt-20260812T090000Z-aaaaaa", hypothesis=DRAFT_HYPOTHESIS)

    result = materialize(
        lock=lock, root=world.data_root, draft_run="draft-run-2", pack_source="conec-names",
        k=10, min_score=MIN_SCORE, out_id="mat-test-2",
    )
    candidate_path = result.out_dir / f"{SAMPLE_ID}.candidates.txt"
    assert candidate_path.read_text(encoding="utf-8") == "corporation\ndanaher\n"


def test_materialize_dry_run_writes_nothing(tmp_path):
    world = _build_world(tmp_path)
    lock = load_lock(world.lock_path)
    _write_draft_run(world.data_root, "draft-run-3", attempt_id="attempt-20260812T090000Z-aaaaaa", hypothesis=DRAFT_HYPOTHESIS)

    result = materialize(
        lock=lock, root=world.data_root, draft_run="draft-run-3", pack_source="conec-contexts",
        k=10, min_score=MIN_SCORE, out_id="mat-test-3", dry_run=True,
    )
    assert result.manifest_path is None
    assert not result.out_dir.exists()
    assert result.per_sample[SAMPLE_ID]["candidate_count"] == 4


def test_materialize_is_deterministic_across_two_runs(tmp_path):
    world = _build_world(tmp_path)
    lock = load_lock(world.lock_path)
    _write_draft_run(world.data_root, "draft-run-4", attempt_id="attempt-20260812T090000Z-aaaaaa", hypothesis=DRAFT_HYPOTHESIS)

    first = materialize(
        lock=lock, root=world.data_root, draft_run="draft-run-4", pack_source="conec-contexts",
        k=10, min_score=MIN_SCORE, out_id="mat-test-4a",
    )
    second = materialize(
        lock=lock, root=world.data_root, draft_run="draft-run-4", pack_source="conec-contexts",
        k=10, min_score=MIN_SCORE, out_id="mat-test-4b",
    )
    first_bytes = (first.out_dir / f"{SAMPLE_ID}.candidates.txt").read_bytes()
    second_bytes = (second.out_dir / f"{SAMPLE_ID}.candidates.txt").read_bytes()
    assert first_bytes == second_bytes
    assert (
        first.per_sample[SAMPLE_ID]["sha256"] == second.per_sample[SAMPLE_ID]["sha256"]
    )


def test_materialize_uses_the_newest_attempt(tmp_path):
    world = _build_world(tmp_path)
    lock = load_lock(world.lock_path)
    older = _write_draft_run(
        world.data_root, "draft-run-5", attempt_id="attempt-20260812T090000Z-aaaaaa",
        hypothesis="a to be an",  # no usable query terms -- would refuse if selected
    )
    newer = _write_draft_run(
        world.data_root, "draft-run-5", attempt_id="attempt-20260812T100000Z-bbbbbb",
        hypothesis=DRAFT_HYPOTHESIS,
    )
    now = datetime.now().timestamp()
    os.utime(older, (now - 100, now - 100))
    os.utime(newer, (now, now))

    result = materialize(
        lock=lock, root=world.data_root, draft_run="draft-run-5", pack_source="conec-contexts",
        k=10, min_score=MIN_SCORE, out_id="mat-test-5",
    )
    assert result.per_sample[SAMPLE_ID]["candidate_count"] == 4


def test_materialize_refuses_on_zero_admitted_candidates(tmp_path):
    world = _build_world(tmp_path)
    lock = load_lock(world.lock_path)
    # A hypothesis sharing no similar words at all with CONTEXT_CONTENT's
    # candidates (verified: every candidate scores well under 0.9 against
    # this query) -- retrieve() legitimately returns an empty list, which
    # materialize() must refuse rather than write an empty candidates file.
    _write_draft_run(
        world.data_root, "draft-run-6", attempt_id="attempt-20260812T090000Z-aaaaaa",
        hypothesis="zzzznope wwwwmiss qqqqgone",
    )

    with pytest.raises(MaterializeError, match="zero candidates"):
        materialize(
            lock=lock, root=world.data_root, draft_run="draft-run-6", pack_source="conec-contexts",
            k=10, min_score=0.9, out_id="mat-test-6",
        )


def test_materialize_refuses_an_unsupported_pack_source(tmp_path):
    world = _build_world(tmp_path)
    lock = load_lock(world.lock_path)
    _write_draft_run(world.data_root, "draft-run-7", attempt_id="attempt-20260812T090000Z-aaaaaa", hypothesis=DRAFT_HYPOTHESIS)

    with pytest.raises(MaterializeError, match="--pack-source must be one of"):
        materialize(
            lock=lock, root=world.data_root, draft_run="draft-run-7", pack_source="oracle",
            k=10, min_score=0.9, out_id="mat-test-7",
        )


def test_materialize_refuses_an_empty_out_id(tmp_path):
    world = _build_world(tmp_path)
    lock = load_lock(world.lock_path)
    _write_draft_run(world.data_root, "draft-run-8", attempt_id="attempt-20260812T090000Z-aaaaaa", hypothesis=DRAFT_HYPOTHESIS)

    with pytest.raises(MaterializeError, match="--out-id must be a non-empty string"):
        materialize(
            lock=lock, root=world.data_root, draft_run="draft-run-8", pack_source="conec-contexts",
            k=10, min_score=0.9, out_id="",
        )


def test_materialize_refuses_when_draft_run_directory_is_missing(tmp_path):
    world = _build_world(tmp_path)
    lock = load_lock(world.lock_path)
    with pytest.raises(MaterializeError, match="does not exist"):
        materialize(
            lock=lock, root=world.data_root, draft_run="no-such-run", pack_source="conec-contexts",
            k=10, min_score=0.9, out_id="mat-test-9",
        )


# ---------------------------------------------------------------------------
# CLI parser shape (argparse wiring only -- main() itself needs a real
# SPEECHRL_DATA_DIR/umbrella lock, exercised at the operator layer, not here).
# ---------------------------------------------------------------------------


def test_cli_parser_requires_every_flag():
    parser = _cli_parser()
    args = parser.parse_args(
        [
            "--draft-run", "R",
            "--pack-source", "conec-contexts",
            "--k", "5",
            "--min-score", "0.5",
            "--out-id", "mat-1",
        ]
    )
    assert args.draft_run == "R"
    assert args.pack_source == "conec-contexts"
    assert args.k == 5
    assert args.min_score == 0.5
    assert args.out_id == "mat-1"
    assert args.dry_run is False


def test_cli_parser_rejects_an_unsupported_pack_source():
    parser = _cli_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "--draft-run", "R", "--pack-source", "oracle", "--k", "5",
                "--min-score", "0.5", "--out-id", "mat-1",
            ]
        )
