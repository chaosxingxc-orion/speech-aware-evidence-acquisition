"""Contract 5: exposure-claim schema validates; the model entry gate refuses without receipts."""

import json
from pathlib import Path

import pytest

import hashlib

from speech_aware_evidence_acquisition.contracts import (
    E0_RECEIPT_SCHEMA,
    MODEL_LOCK_KEY,
    ExecutionPlan,
    ExecutionScopeError,
    ExposureSchemaError,
    FrozenCoreGate,
    GateClosed,
    validate_exposure_claim,
)

from gate_fixture import GateFixture


REPO_ROOT = Path(__file__).resolve().parents[2]

VALID_CLAIM = {
    "scope": "earnings21-original dev slice, D0 acquisition only",
    "date": "2026-08-03",
    "counts": {"model_calls": 0, "speech_audio_seconds": 0},
    "inherited": "W1 probe campaigns on other carriers; zero model exposure on the three carriers",
}


def test_valid_exposure_claim_passes():
    validate_exposure_claim(VALID_CLAIM)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda claim: claim.pop("scope"),
        lambda claim: claim.pop("inherited"),
        lambda claim: claim.update(date="03/08/2026"),
        lambda claim: claim.update(counts={}),
        lambda claim: claim.update(counts={"model_calls": -1}),
        lambda claim: claim.update(extra_field=1),
    ],
)
def test_malformed_exposure_claims_fail(mutation):
    claim = {key: (dict(value) if isinstance(value, dict) else value) for key, value in VALID_CLAIM.items()}
    mutation(claim)
    with pytest.raises(ExposureSchemaError):
        validate_exposure_claim(claim)


def test_exposure_ledger_header_carries_contract_columns():
    """Parse the real table header — prose mentions of a column name do not count."""

    ledger = (REPO_ROOT / "docs" / "exposure-ledger.md").read_text(encoding="utf-8")
    header = None
    for line in ledger.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and "run/experiment id" in stripped.lower():
            header = [cell.strip().lower() for cell in stripped.strip("|").split("|")]
            break
    assert header is not None, "exposure ledger must have a markdown table header row"
    for column in (
        "date",
        "run/experiment id",
        "execution profile",
        "scope",
        "model/tool",
        "speech carrier + split",
        "split role",
        "split identity hash",
        "consumed",
        "calls",
        "speech audio seconds",
        "gpu hours",
        "inherited exposure",
    ):
        assert column in header, f"exposure ledger header lacks column {column!r}"


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


@pytest.fixture()
def world(tmp_path):
    return GateFixture(tmp_path)


def test_fully_valid_receipts_open_the_gate(world):
    world.gate().assert_model_touch_allowed(world.plan())


# ---------------------------------------------------------------------------
# M-3 (external-threat-model review): the umbrella lock is read exactly once
# per gate call, and its SHA-256 is returned so a downstream reader (the run
# manifest / ledger "dataset rev" cell) can bind to WHICH revision a run used.
# ---------------------------------------------------------------------------


def test_gate_returns_the_umbrella_lock_sha256(world):
    gate = world.gate()
    expected = _sha(world.lock_path.read_bytes())
    result = gate.assert_model_touch_allowed(world.plan())
    assert result == expected


def test_gate_reads_the_umbrella_lock_exactly_once_per_call(world, monkeypatch):
    """Before M-3, one call independently re-read/re-parsed the lock file up to
    three times (exposure pre-registration, carrier scope resolution, the
    runtime model-entry lookup). Proved via an actual read-count, not merely
    by reading source order."""

    import speech_aware_evidence_acquisition.contracts as contracts_mod

    calls: list[int] = []
    original = contracts_mod.FrozenCoreGate._load_lock_with_hash

    def _counting(self):
        calls.append(1)
        return original(self)

    monkeypatch.setattr(contracts_mod.FrozenCoreGate, "_load_lock_with_hash", _counting)
    gate = world.gate()
    gate.assert_model_touch_allowed(world.plan())
    assert calls == [1], "the lock must be read exactly once per assert_model_touch_allowed call"


# ---------------------------------------------------------------------------
# M-1 (external-threat-model review): a __pycache__ entry inside the frozen
# scoring package is refused explicitly, not silently skipped. Demonstrated
# defect: a forged .pyc whose SOURCE hash still matched the D3 receipt made
# scoring run different code than the receipt described.
# ---------------------------------------------------------------------------


def test_gate_refuses_pycache_entry_in_scoring_package(world):
    pycache = world.scoring_dir / "__pycache__"
    pycache.mkdir()
    (pycache / "wer.cpython-312.pyc").write_bytes(b"forged bytecode, source hash still matches")
    with pytest.raises(GateClosed, match="__pycache__"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_gate_refuses_an_empty_pycache_directory_too(world):
    """Presence alone is refused, not just a non-empty cache: an empty
    __pycache__ dir is anomalous residue that could be repopulated."""

    (world.scoring_dir / "__pycache__").mkdir()
    with pytest.raises(GateClosed, match="__pycache__"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_gate_refuses_when_receipts_are_missing(tmp_path, world):
    gate = FrozenCoreGate(
        tmp_path / "absent-e0.json",
        tmp_path / "absent-runtime.json",
        world.data_root,
        world.lock_path,
        world.runtime_root,
        world.exposure_ledger,
        world.source_root,
    )
    world.lock_path.write_text(json.dumps(world.lock), encoding="utf-8")
    with pytest.raises(GateClosed, match="missing or unreadable"):
        gate.assert_model_touch_allowed(world.plan())


def test_gate_refuses_nonexistent_model_file(world):
    world.runtime["gguf_files"][1]["path"] = f"{world.SUBDIR}/definitely-does-not-exist.gguf"
    with pytest.raises(GateClosed, match="does not exist"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_gate_refuses_fabricated_hash_and_size(world):
    world.runtime["gguf_files"][0]["sha256"] = "0" * 64
    with pytest.raises(GateClosed, match="SHA-256 drift"):
        world.gate().assert_model_touch_allowed(world.plan())

    world.runtime["gguf_files"][0]["sha256"] = _sha(world.GGUF_1)
    world.runtime["gguf_files"][0]["bytes"] = 12345
    with pytest.raises(GateClosed, match="size drift"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_gate_refuses_model_byte_drift_on_disk(world):
    (world.data_root / world.SUBDIR / "model-q8_0.gguf").write_bytes(b"tampered")
    with pytest.raises(GateClosed, match="drift"):
        world.gate().assert_model_touch_allowed(world.plan())


@pytest.mark.parametrize(
    "bad_path",
    [
        "/definitely/does/not/exist/model.gguf",
        "C:/leak/model.gguf",
        "../outside.gguf",
        "models/../../escape.gguf",
    ],
)
def test_gate_refuses_absolute_and_traversal_paths(world, bad_path):
    world.runtime["gguf_files"][1]["path"] = bad_path
    with pytest.raises(GateClosed):
        world.gate().assert_model_touch_allowed(world.plan())


def test_gate_refuses_duplicate_and_extra_model_files(world):
    world.runtime["gguf_files"][1] = dict(world.runtime["gguf_files"][0])
    with pytest.raises(GateClosed, match="duplicates"):
        world.gate().assert_model_touch_allowed(world.plan())

    world.runtime["gguf_files"] = [
        world.runtime["gguf_files"][0],
        {
            "path": f"{world.SUBDIR}/mmproj-bf16.gguf",
            "bytes": len(world.GGUF_2),
            "sha256": _sha(world.GGUF_2),
        },
        {
            "path": f"{world.SUBDIR}/model-q8_0.gguf",
            "bytes": len(world.GGUF_1),
            "sha256": _sha(world.GGUF_1),
        },
    ]
    with pytest.raises(GateClosed, match="extra or missing"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_gate_refuses_lock_key_mismatch_and_missing_lock_entry(world):
    world.runtime["model_lock_key"] = "some-other-model"
    with pytest.raises(GateClosed, match="does not match"):
        world.gate().assert_model_touch_allowed(world.plan())

    world.runtime["model_lock_key"] = MODEL_LOCK_KEY
    world.lock["models"][0]["name"] = "renamed-away"
    with pytest.raises(GateClosed, match="not found in datasets lock"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_gate_refuses_path_outside_lock_subdir(world):
    stray = world.data_root / "models" / "other"
    stray.mkdir(parents=True)
    (stray / "model.gguf").write_bytes(world.GGUF_1)
    world.runtime["gguf_files"][0]["path"] = "models/other/model.gguf"
    with pytest.raises(GateClosed, match="canonical subdir"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_gate_refuses_unbacked_build_commit(world):
    world.runtime["llama_cpp"]["build_commit"] = "abc123"
    with pytest.raises(GateClosed, match="full 40-hex"):
        world.gate().assert_model_touch_allowed(world.plan())

    world.runtime["llama_cpp"]["build_commit"] = "d" * 40
    world.runtime["llama_cpp"]["binary_sha256"] = "e" * 64
    with pytest.raises(GateClosed, match="binary drift"):
        world.gate().assert_model_touch_allowed(world.plan())

    world.runtime["llama_cpp"]["binary_sha256"] = _sha(world.BINARY)
    world.runtime["llama_cpp"]["binary_path"] = "llama.cpp/missing/llama-server"
    with pytest.raises(GateClosed, match="does not exist"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_gate_refuses_e0_artifact_hash_drift(world):
    world.deliverables["d2_leakage"]["sha256"] = "f" * 64
    with pytest.raises(GateClosed, match="artifact hash drift"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_gate_refuses_open_deliverable_and_missing_artifact(world):
    world.deliverables["d3_scoring"]["status"] = "OPEN"
    with pytest.raises(GateClosed, match="d3_scoring"):
        world.gate().assert_model_touch_allowed(world.plan())

    world.deliverables["d3_scoring"]["status"] = "CLOSED"
    (world.receipts / "e0" / "d4_trace.json").unlink()
    with pytest.raises(GateClosed, match="d4_trace"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_gate_refuses_schema_or_identity_mismatch(world):
    world.e0["schema"] = "some-other-schema"
    with pytest.raises(GateClosed, match="schema mismatch"):
        world.gate().assert_model_touch_allowed(world.plan())

    world.e0["schema"] = E0_RECEIPT_SCHEMA
    world.runtime["study"] = "another-study"
    with pytest.raises(GateClosed, match="study identity mismatch"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_gate_refuses_lock_total_size_mismatch(world):
    world.lock["models"][0]["size_bytes"] += 1
    with pytest.raises(GateClosed, match="total"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_gate_refuses_confirmatory_split_even_with_allowed_profile(world):
    with pytest.raises(ExecutionScopeError, match="confirmatory"):
        world.gate().assert_model_touch_allowed(world.plan(split_role="confirmatory"))


def test_gate_refuses_over_budget_plans_regardless_of_label(world):
    for overrides in (
        {"planned_model_calls": 3001},
        {"planned_gpu_hours": 40.5},
        {"planned_speech_audio_seconds": 72001},
    ):
        with pytest.raises(ExecutionScopeError, match="cap"):
            world.gate().assert_model_touch_allowed(world.plan(**overrides))


def test_gate_refuses_missing_or_malformed_hashes(world):
    with pytest.raises(ExecutionScopeError, match="split_identity_hash"):
        world.gate().assert_model_touch_allowed(world.plan(split_identity_hash="short"))
    with pytest.raises(ExecutionScopeError, match="protocol_hash"):
        world.gate().assert_model_touch_allowed(world.plan(protocol_hash=""))


def test_gate_refuses_run_without_preregistered_exposure_row(world):
    with pytest.raises(GateClosed, match="pre-registered exposure row"):
        world.gate().assert_model_touch_allowed(
            world.plan(run_id="SAEA-E-999-unregistered")
        )


def test_gate_refuses_scoring_source_drift(world):
    (world.scoring_dir / "wer.py").write_bytes(b"def score():\n    return 1  # tampered\n")
    with pytest.raises(GateClosed, match="scoring freeze drift"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_gate_refuses_unlisted_scoring_module(world):
    (world.scoring_dir / "wer_v2.py").write_bytes(b"def score2():\n    return 2\n")
    with pytest.raises(GateClosed, match="does not name"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_gate_refuses_missing_scoring_freeze_mapping(world):
    artifact = world.receipts / "e0" / "d3_scoring.json"
    artifact.write_bytes(world.ARTIFACT)
    world.deliverables["d3_scoring"]["sha256"] = _sha(world.ARTIFACT)
    with pytest.raises(GateClosed, match="frozen_sources_sha256"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_gate_refuses_runtime_library_drift_and_unlisted_files(world):
    lib = world.runtime_root / "llama.cpp" / "build" / "bin" / "libfake-impl.so"
    lib.write_bytes(b"rebuilt-from-patched-source")
    with pytest.raises(GateClosed, match="drift"):
        world.gate().assert_model_touch_allowed(world.plan())

    lib.write_bytes(world.LIBRARY)
    stray = world.runtime_root / "llama.cpp" / "build" / "bin" / "libextra-plugin.so"
    stray.write_bytes(b"unlisted plugin")
    with pytest.raises(GateClosed, match="runtime directory drift"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_gate_refuses_reported_build_mismatch(world):
    world.runtime["llama_cpp"]["reported_build"] = "version: 9999 (abcdef1)"
    with pytest.raises(GateClosed, match="prefix-match"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_gate_refuses_ledger_row_disagreeing_with_plan(world):
    with pytest.raises(GateClosed, match="disagrees with the execution plan"):
        world.gate().assert_model_touch_allowed(world.plan(split_identity_hash="b" * 64))
    with pytest.raises(GateClosed, match="disagrees with the execution plan"):
        world.gate().assert_model_touch_allowed(world.plan(split_role="discovery"))


def test_gate_refuses_budget_exceeding_registration(world):
    with pytest.raises(GateClosed, match="pre-registered"):
        world.gate().assert_model_touch_allowed(world.plan(planned_model_calls=2999))


def test_gate_refuses_consumed_row(world):
    world.write_ledger_rows(
        f"| 2026-08-04 | {world.RUN_ID} | baseline-reproduction | s | m "
        f"| {world.CARRIER} dev | dev | {'a' * 64} | yes "
        "| 10 | 600 | 1.0 | none | none | consumed |\n"
    )
    with pytest.raises(GateClosed, match="already consumed"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_gate_refuses_duplicate_registration(world):
    row = (
        f"| 2026-08-04 | {world.RUN_ID} | baseline-reproduction | s | m "
        f"| {world.CARRIER} dev | dev | {'a' * 64} | no "
        "| 10 | 600 | 1.0 | none | none | dup |\n"
    )
    world.write_ledger_rows(row + row)
    with pytest.raises(GateClosed, match="more than once"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_gate_refuses_profile_and_seconds_disagreement(world):
    with pytest.raises(GateClosed, match="disagrees with the execution plan"):
        world.gate().assert_model_touch_allowed(
            world.plan(execution_profile="bounded-discovery-probe")
        )
    with pytest.raises(GateClosed, match="pre-registered"):
        world.gate().assert_model_touch_allowed(
            world.plan(planned_speech_audio_seconds=700)
        )
    with pytest.raises(GateClosed, match="pre-registered"):
        world.gate().assert_model_touch_allowed(world.plan(planned_gpu_hours=2.0))


def test_gate_refuses_cumulative_slice_budget_exhaustion(world):
    """N individually-bounded runs cannot sum past the frozen slice caps."""

    other = (
        "| 2026-08-04 | SAEA-E-001-prior | baseline-reproduction | s | m "
        f"| {world.CARRIER} dev | dev | {'c' * 64} | no "
        "| 2995 | 600 | 1.0 | none | none | prior run |\n"
    )
    mine = (
        f"| 2026-08-04 | {world.RUN_ID} | baseline-reproduction | s | m "
        f"| {world.CARRIER} dev | dev | {'a' * 64} | no "
        "| 10 | 600 | 1.0 | none | none | this run |\n"
    )
    world.write_ledger_rows(other + mine)
    with pytest.raises(GateClosed, match="first-slice cap"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_gate_refuses_scoring_module_hidden_in_a_subdirectory(world):
    nested = world.scoring_dir / "helpers"
    nested.mkdir()
    (nested / "extra.py").write_bytes(b"def helper():\n    return 3\n")
    with pytest.raises(GateClosed, match="does not name"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_gate_refuses_non_source_file_in_scoring_package(world):
    (world.scoring_dir / "table.json").write_bytes(b"{}")
    with pytest.raises(GateClosed, match="non-source entry"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_gate_refuses_subdirectory_in_runtime_bin(world):
    plugins = world.runtime_root / "llama.cpp" / "build" / "bin" / "plugins"
    plugins.mkdir()
    (plugins / "evil.so").write_bytes(b"plugin")
    with pytest.raises(GateClosed, match="non-file entry"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_gate_refuses_symlinked_directory_in_scoring_package(world, tmp_path):
    outside = tmp_path / "outside_pkg"
    outside.mkdir()
    (outside / "evil.py").write_bytes(b"def evil():\n    return 1\n")
    try:
        (world.scoring_dir / "vendor").symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation not permitted on this platform")
    with pytest.raises(GateClosed, match="symlinked directory"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_gate_refuses_symlinked_pycache_directory_in_scoring_package(world, tmp_path):
    """The __pycache__ name skip must not shadow the symlink refusal."""

    outside = tmp_path / "planted_bytecode"
    outside.mkdir()
    (outside / "wer.cpython-312.pyc").write_bytes(b"forged bytecode")
    try:
        (world.scoring_dir / "__pycache__").symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation not permitted on this platform")
    with pytest.raises(GateClosed, match="symlinked directory"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_gate_refuses_nan_and_negative_budget_cells(world):
    world.write_ledger_rows(
        f"| 2026-08-04 | {world.RUN_ID} | baseline-reproduction | s | m "
        f"| {world.CARRIER} dev | dev | {'a' * 64} | no "
        "| 10 | 600 | nan | none | none | nan-cell |\n"
    )
    with pytest.raises(GateClosed, match="finite non-negative"):
        world.gate().assert_model_touch_allowed(world.plan())

    decoy = (
        "| 2026-08-04 | SAEA-E-002-decoy | baseline-reproduction | s | m "
        f"| {world.CARRIER} dev | dev | {'c' * 64} | no "
        "| -1000000 | 600 | 1.0 | none | none | negative offset |\n"
    )
    mine = (
        f"| 2026-08-04 | {world.RUN_ID} | baseline-reproduction | s | m "
        f"| {world.CARRIER} dev | dev | {'a' * 64} | no "
        "| 10 | 600 | 1.0 | none | none | this run |\n"
    )
    world.write_ledger_rows(decoy + mine)
    with pytest.raises(GateClosed, match="finite non-negative"):
        world.gate().assert_model_touch_allowed(world.plan())


# ---------------------------------------------------------------------------
# I2 (whole-ledger budget totals) + M4 (row cell-count validation).
#
# The reproduced defect: the old ledger parser stopped at the first non-table
# line found after its header, so a second table -- or even a single stray
# prose line between two data rows of the SAME table -- silently dropped
# every row after it from duplicate-run-id detection, the `consumed` check,
# and the slice-total budget sum. `_LEDGER_HEADER`/`_row`/`_table` build the
# real 15-column contract shape (matching GateFixture.write_ledger_rows and
# the committed docs/exposure-ledger.md) so these probes exercise the SAME
# column set the real ledger uses, not a shorthand approximation.
# ---------------------------------------------------------------------------

_LEDGER_HEADER = (
    "| date | run/experiment id | execution profile | scope | model/tool "
    "| speech carrier + split | split role | split identity hash | consumed "
    "| calls | speech audio seconds | gpu hours | inherited exposure "
    "| artifacts | notes |\n"
)
_LEDGER_SEP = "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"


def _row(
    world,
    run_id,
    *,
    calls=10,
    audio=600,
    gpu=1.0,
    consumed="no",
    split_role="dev",
    split_hash=None,
    carrier=None,
    profile="baseline-reproduction",
    notes="row",
):
    split_hash = split_hash or "a" * 64
    carrier = carrier or f"{world.CARRIER} dev"
    return (
        f"| 2026-08-04 | {run_id} | {profile} | s | m | {carrier} | {split_role} "
        f"| {split_hash} | {consumed} | {calls} | {audio} | {gpu} | none | none | {notes} |\n"
    )


def _table(rows: str) -> str:
    return _LEDGER_HEADER + _LEDGER_SEP + rows


def test_gate_recognizes_rows_registered_in_a_second_table(world):
    """I2 fix: a run registered ONLY in a second markdown table (after prose)
    must still be found. Before the fix, the parser stopped at the first
    non-table line after the FIRST table's header, so this run would never
    pre-register and the gate would wrongly refuse it as unregistered."""

    second = "\nsome prose after the first table\n\n" + _table(
        _row(world, "SAEA-E-777-injected")
    )
    world.exposure_ledger.write_text(
        world.exposure_ledger.read_text(encoding="utf-8") + second, encoding="utf-8"
    )
    # No longer refused for "no pre-registered exposure row" -- the second
    # table's row is now recognized and the gate opens.
    world.gate().assert_model_touch_allowed(world.plan(run_id="SAEA-E-777-injected"))


def test_second_table_budget_rows_count_toward_the_slice_cap(world):
    """I2 probe: demonstrated defect -- a second table holding 2995 calls /
    71000 audio-seconds / 39 GPU-hours was invisible to the slice-total sum
    and the gate opened. It must now be counted and refuse."""

    overflow = _table(
        _row(
            world,
            "SAEA-E-778-overflow",
            calls=2995,
            audio=71000,
            gpu=39.0,
            split_hash="c" * 64,
        )
    )
    world.exposure_ledger.write_text(
        world.exposure_ledger.read_text(encoding="utf-8") + "\n" + overflow,
        encoding="utf-8",
    )
    with pytest.raises(GateClosed, match="first-slice cap"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_prose_line_between_rows_does_not_drop_rows_below_it(world):
    """I2 probe: a single prose line inserted BETWEEN two data rows of the
    SAME table must never drop the row below it from the budget sum."""

    ledger = (
        _LEDGER_HEADER
        + _LEDGER_SEP
        + _row(world, world.RUN_ID)
        + "\nSome human-readable note inserted between rows.\n\n"
        + _row(
            world,
            "SAEA-E-779-afterprose",
            calls=2995,
            audio=71000,
            gpu=39.0,
            split_hash="d" * 64,
        )
    )
    world.exposure_ledger.write_text(ledger, encoding="utf-8")
    with pytest.raises(GateClosed, match="first-slice cap"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_duplicate_run_id_across_two_tables_is_refused(world):
    """I2 probe: the SAME run id pre-registered in two different tables must
    still be caught as a duplicate registration, not treated as if the
    second table's copy never existed."""

    duplicate = _table(_row(world, world.RUN_ID, calls=5, audio=100, gpu=0.5))
    world.exposure_ledger.write_text(
        world.exposure_ledger.read_text(encoding="utf-8") + "\n" + duplicate,
        encoding="utf-8",
    )
    with pytest.raises(GateClosed, match="more than once"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_consumed_row_in_a_later_table_for_the_same_run_id_is_refused(world):
    """I2 probe: a `consumed=yes` row for the same run id, registered in a
    LATER table, must still refuse the touch -- it must not be invisible
    just because it lives in a second table."""

    consumed_elsewhere = _table(_row(world, world.RUN_ID, consumed="yes"))
    world.exposure_ledger.write_text(
        world.exposure_ledger.read_text(encoding="utf-8") + "\n" + consumed_elsewhere,
        encoding="utf-8",
    )
    # Caught by the (stricter) duplicate-registration check first, since both
    # rows share a run id -- still refused, which is exactly what the probe
    # requires.
    with pytest.raises(GateClosed, match="more than once"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_unrecognized_table_header_sharing_a_contract_column_is_refused(world):
    """I2 fail-closed: a table whose header does NOT carry the run-id column
    but DOES reuse another contract column name (here `consumed`) must be
    refused rather than silently ignored -- it could be a mis-typed or
    reordered contract table whose rows would otherwise vanish."""

    foreign = "\n| notes | consumed |\n|---|---|\n| decoy | no |\n"
    world.exposure_ledger.write_text(
        world.exposure_ledger.read_text(encoding="utf-8") + foreign, encoding="utf-8"
    )
    with pytest.raises(GateClosed, match="not the recognized contract header"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_row_with_extra_cell_from_an_unescaped_pipe_is_refused(world):
    """M4: an unescaped `|` inside a free-text cell (e.g. notes) renders as
    one cell for a human but splits into two for the parser; the row must be
    refused rather than positionally misaligned against the header."""

    world.write_ledger_rows(
        f"| 2026-08-04 | {world.RUN_ID} | baseline-reproduction | s | m "
        f"| {world.CARRIER} dev | dev | {'a' * 64} | no "
        "| 10 | 600 | 1.0 | none | none | oops | extra cell |\n"
    )
    with pytest.raises(GateClosed, match="cells"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_row_with_missing_cell_is_refused(world):
    """M4: a row with FEWER cells than its header (a dropped trailing column)
    must also be refused, not silently zipped against the wrong columns."""

    world.write_ledger_rows(
        f"| 2026-08-04 | {world.RUN_ID} | baseline-reproduction | s | m "
        f"| {world.CARRIER} dev | dev | {'a' * 64} | no "
        "| 10 | 600 | 1.0 | none |\n"
    )
    with pytest.raises(GateClosed, match="cells"):
        world.gate().assert_model_touch_allowed(world.plan())


def test_real_exposure_ledger_still_parses_correctly(world):
    """I2 regression guard: the real committed docs/exposure-ledger.md (one
    table, a data row, then trailing prose) must still parse to exactly its
    one real row through the new whole-document parser."""

    from speech_aware_evidence_acquisition.contracts import _parse_ledger_tables

    real_ledger = REPO_ROOT / "docs" / "exposure-ledger.md"
    rows = _parse_ledger_tables(real_ledger.read_text(encoding="utf-8"))
    assert len(rows) == 1
    assert rows[0]["run/experiment id"] == "SAEA-E0-CLOSURE-2026-08-04"


def test_gate_refuses_unknown_carrier_lock_key(world):
    # An unregistered carrier can never be the exposure row's unambiguous named
    # carrier (I2 binding requires the row to name a *known* dataset lock key),
    # so this now refuses at the carrier row/plan binding step rather than at
    # later carrier-scope resolution.
    world.write_ledger_rows(
        f"| 2026-08-04 | {world.RUN_ID} | baseline-reproduction | s | m "
        "| not-in-lock dev | dev | " + "a" * 64 + " | no "
        "| 10 | 600 | 1.0 | none | none | unknown carrier |\n"
    )
    with pytest.raises(GateClosed, match="known carrier lock key"):
        world.gate().assert_model_touch_allowed(world.plan(carrier_lock_key="not-in-lock"))


def test_bare_profile_strings_are_no_longer_accepted(world):
    with pytest.raises(ExecutionScopeError, match="ExecutionPlan"):
        world.gate().assert_model_touch_allowed("baseline-reproduction")
