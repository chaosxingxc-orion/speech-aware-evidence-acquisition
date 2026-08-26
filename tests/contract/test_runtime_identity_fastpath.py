"""GGUF cheap-identity fast path (owner decision 2026-08-06,
docs/owner-decisions-pending.md item 7): the gate must not re-hash the pinned
multi-GB GGUF set on every open when nothing about the files has changed,
while runtime libraries stay fully hashed always and any genuine drift still
refuses the touch. The residual, owner-accepted weakness (an in-place edit
that preserves size/mtime/file-id) is pinned here as a test, not left as
prose alone."""

import hashlib
import json
import os
import time
from pathlib import Path

import pytest

import speech_aware_evidence_acquisition.contracts as contracts
from speech_aware_evidence_acquisition.contracts import GateClosed

from gate_fixture import GateFixture


@pytest.fixture(autouse=True)
def _isolated_session_floor(monkeypatch):
    """Every test in this module starts with a clean process-level "has this
    session already done one full GGUF hash for this receipt" floor (see
    contracts._SESSION_FULL_HASH_DONE's own docstring) AND a clean
    RUNTIME_FULL_HASH_ENV. Without this, execution order across the whole
    suite -- other files share GateFixture's identical, hard-coded receipt
    content/sha256 -- could make "the very first call this session" or an
    inherited env var from another test nondeterministic."""

    monkeypatch.setattr(contracts, "_SESSION_FULL_HASH_DONE", set())
    monkeypatch.delenv(contracts.RUNTIME_FULL_HASH_ENV, raising=False)


@pytest.fixture()
def world(tmp_path):
    return GateFixture(tmp_path)


def _cache_path(world) -> Path:
    return world.data_root / contracts.RUNTIME_IDENTITY_CACHE_FILENAME


def _gguf_target(world) -> Path:
    return world.data_root / world.SUBDIR / "model-q8_0.gguf"


@pytest.mark.requires_wsl2_execution_authority
def test_unchanged_files_second_open_uses_the_fast_path_and_skips_rehash(world, monkeypatch):
    """The core perf claim, proved by an actual re-hash CALL COUNT, not merely
    by elapsed time (which is noisy for tiny fixture files)."""

    gate = world.gate()
    plan = world.plan()

    first: dict[str, object] = {}
    gate.assert_model_touch_allowed(plan, full_hash=False, diagnostics=first)
    assert first["gguf_fast_path_used"] is False  # nothing cached yet: full hash
    assert first["gguf_files_full_hashed"] == first["gguf_files_total"] == 2
    assert _cache_path(world).is_file()

    rehashed: list[str] = []
    real_measure = contracts._measure_file

    def spy(path, label):
        rehashed.append(label)
        return real_measure(path, label)

    monkeypatch.setattr(contracts, "_measure_file", spy)

    second: dict[str, object] = {}
    gate.assert_model_touch_allowed(plan, full_hash=False, diagnostics=second)
    assert second["gguf_fast_path_used"] is True
    assert second["gguf_files_full_hashed"] == 0
    # Only the GGUF set is asserted here -- E0 artifacts, the scoring freeze,
    # the llama.cpp build binary and runtime libraries are UNCHANGED (item 3)
    # and legitimately still go through _measure_file every call.
    gguf_rehashed = [label for label in rehashed if "gguf_files" in label]
    assert not gguf_rehashed, f"fast path must not re-hash GGUF bytes, but re-hashed: {gguf_rehashed}"


@pytest.mark.requires_wsl2_execution_authority
def test_explicit_full_hash_true_always_rehashes_even_with_a_warm_cache(world):
    gate = world.gate()
    plan = world.plan()
    gate.assert_model_touch_allowed(plan, full_hash=False)  # warm the cache

    diagnostics: dict[str, object] = {}
    gate.assert_model_touch_allowed(plan, full_hash=True, diagnostics=diagnostics)
    assert diagnostics["gguf_fast_path_used"] is False
    assert diagnostics["gguf_files_full_hashed"] == diagnostics["gguf_files_total"]


@pytest.mark.requires_wsl2_execution_authority
def test_a_process_never_trusts_a_preexisting_cache_on_its_first_gate_open(world):
    """The 'at least once per session' floor (owner decision item 5): even
    with a fully valid, matching on-disk cache already present (as if written
    by an earlier process), the very first call in a FRESH session must still
    do a genuine full hash before ever taking the fast path."""

    gate = world.gate()
    plan = world.plan()
    gate.assert_model_touch_allowed(plan)  # default (None): warms a real, valid cache

    # Simulate a brand-new process/session that inherits the same on-disk
    # cache but starts with an empty in-memory session floor.
    contracts._SESSION_FULL_HASH_DONE.clear()
    diagnostics: dict[str, object] = {}
    gate.assert_model_touch_allowed(plan, diagnostics=diagnostics)
    assert diagnostics["gguf_fast_path_used"] is False


@pytest.mark.requires_wsl2_execution_authority
def test_env_var_true_forces_full_hash_when_full_hash_argument_is_none(world, monkeypatch):
    gate = world.gate()
    plan = world.plan()
    gate.assert_model_touch_allowed(plan, full_hash=False)  # warm the cache

    monkeypatch.setenv(contracts.RUNTIME_FULL_HASH_ENV, "1")
    diagnostics: dict[str, object] = {}
    gate.assert_model_touch_allowed(plan, diagnostics=diagnostics)  # full_hash=None (default)
    assert diagnostics["gguf_fast_path_used"] is False


@pytest.mark.requires_wsl2_execution_authority
def test_env_var_false_permits_the_fast_path_when_full_hash_argument_is_none(world, monkeypatch):
    gate = world.gate()
    plan = world.plan()
    gate.assert_model_touch_allowed(plan, full_hash=False)  # warm the cache

    monkeypatch.setenv(contracts.RUNTIME_FULL_HASH_ENV, "0")
    diagnostics: dict[str, object] = {}
    gate.assert_model_touch_allowed(plan, diagnostics=diagnostics)  # full_hash=None (default)
    assert diagnostics["gguf_fast_path_used"] is True


@pytest.mark.requires_wsl2_execution_authority
def test_explicit_full_hash_argument_wins_over_the_env_var(world, monkeypatch):
    gate = world.gate()
    plan = world.plan()
    gate.assert_model_touch_allowed(plan, full_hash=False)  # warm the cache

    monkeypatch.setenv(contracts.RUNTIME_FULL_HASH_ENV, "0")
    diagnostics: dict[str, object] = {}
    gate.assert_model_touch_allowed(plan, full_hash=True, diagnostics=diagnostics)
    assert diagnostics["gguf_fast_path_used"] is False


@pytest.mark.requires_wsl2_execution_authority
def test_malformed_env_var_falls_through_to_the_safe_auto_default(world, monkeypatch):
    """A garbage env value must never be silently treated as an explicit
    fast-path request -- it falls through to the auto/session floor, which is
    the SAFE side."""

    gate = world.gate()
    plan = world.plan()
    gate.assert_model_touch_allowed(plan, full_hash=False)  # warm the cache

    monkeypatch.setenv(contracts.RUNTIME_FULL_HASH_ENV, "not-a-recognized-value")
    contracts._SESSION_FULL_HASH_DONE.clear()  # fresh-session simulation
    diagnostics: dict[str, object] = {}
    gate.assert_model_touch_allowed(plan, diagnostics=diagnostics)
    assert diagnostics["gguf_fast_path_used"] is False


@pytest.mark.requires_wsl2_execution_authority
def test_bytes_replaced_same_size_and_mtime_restored_is_the_documented_residual_weakness(world):
    """Pinned by test, not merely prose (task requirement): the fast path
    defends size/mtime/file-identity, not content. An in-place edit that
    restores the exact same size and mtime is the ONE case the fast path
    cannot catch -- docs/owner-decisions-pending.md item 7 states this
    plainly as an accepted, owner-approved scope reduction."""

    gate = world.gate()
    plan = world.plan()
    gate.assert_model_touch_allowed(plan)  # warm the cache with genuine bytes

    target = _gguf_target(world)
    original_stat = target.stat()
    tampered = b"X" * len(world.GGUF_1)  # same size, different content
    target.write_bytes(tampered)
    os.utime(target, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
    assert target.stat().st_size == original_stat.st_size
    assert target.stat().st_mtime_ns == original_stat.st_mtime_ns

    diagnostics: dict[str, object] = {}
    gate.assert_model_touch_allowed(plan, diagnostics=diagnostics)  # ACCEPTS -- the weakness
    assert diagnostics["gguf_fast_path_used"] is True


@pytest.mark.requires_wsl2_execution_authority
def test_size_change_is_refused(world):
    gate = world.gate()
    plan = world.plan()
    gate.assert_model_touch_allowed(plan)  # warm the cache

    target = _gguf_target(world)
    target.write_bytes(world.GGUF_1 + b"extra-bytes")
    with pytest.raises(GateClosed, match="size drift"):
        gate.assert_model_touch_allowed(plan)


@pytest.mark.requires_wsl2_execution_authority
def test_mtime_change_alone_triggers_full_rehash_and_passes_on_identical_bytes(world):
    gate = world.gate()
    plan = world.plan()
    gate.assert_model_touch_allowed(plan)  # warm the cache

    target = _gguf_target(world)
    future = time.time() + 120
    os.utime(target, (future, future))  # same bytes, only mtime bumped

    diagnostics: dict[str, object] = {}
    gate.assert_model_touch_allowed(plan, diagnostics=diagnostics)
    assert diagnostics["gguf_fast_path_used"] is False  # cache invalidated by mtime drift
    assert diagnostics["gguf_files_full_hashed"] >= 1


@pytest.mark.requires_wsl2_execution_authority
def test_mtime_change_with_different_bytes_is_refused(world):
    gate = world.gate()
    plan = world.plan()
    gate.assert_model_touch_allowed(plan)  # warm the cache

    target = _gguf_target(world)
    target.write_bytes(b"Y" * len(world.GGUF_1))  # different bytes, same size
    future = time.time() + 240
    os.utime(target, (future, future))  # AND a fresh mtime
    with pytest.raises(GateClosed, match="SHA-256 drift"):
        gate.assert_model_touch_allowed(plan)


@pytest.mark.requires_wsl2_execution_authority
def test_different_runtime_receipt_invalidates_the_cache(world):
    gate = world.gate()
    plan = world.plan()
    gate.assert_model_touch_allowed(plan)  # warm the cache
    cache_before = json.loads(_cache_path(world).read_text(encoding="utf-8"))

    # A receipt-shape-preserving change (bump the reported build string):
    # rewriting it changes the receipt's own bytes/sha256, which the cache is
    # explicitly bound to.
    world.runtime["llama_cpp"]["reported_build"] = "version: 10000 (ddddddd)"
    (world.receipts / "runtime.json").write_text(json.dumps(world.runtime), encoding="utf-8")

    diagnostics: dict[str, object] = {}
    gate.assert_model_touch_allowed(plan, diagnostics=diagnostics)
    assert diagnostics["gguf_fast_path_used"] is False
    cache_after = json.loads(_cache_path(world).read_text(encoding="utf-8"))
    assert cache_after["runtime_receipt_sha256"] != cache_before["runtime_receipt_sha256"]


@pytest.mark.requires_wsl2_execution_authority
def test_missing_cache_file_forces_full_verification(world):
    gate = world.gate()
    plan = world.plan()
    diagnostics: dict[str, object] = {}
    gate.assert_model_touch_allowed(plan, full_hash=False, diagnostics=diagnostics)
    assert diagnostics["gguf_fast_path_used"] is False
    assert _cache_path(world).is_file()


@pytest.mark.requires_wsl2_execution_authority
def test_corrupt_cache_file_forces_full_verification_fail_safe(world):
    gate = world.gate()
    plan = world.plan()
    gate.assert_model_touch_allowed(plan, full_hash=False)
    _cache_path(world).write_text("{not valid json", encoding="utf-8")

    diagnostics: dict[str, object] = {}
    gate.assert_model_touch_allowed(plan, full_hash=False, diagnostics=diagnostics)
    assert diagnostics["gguf_fast_path_used"] is False


@pytest.mark.requires_wsl2_execution_authority
def test_runtime_library_tampering_still_refused_full_hashing_kept(world):
    """Item 3: runtime libraries are never cached and never fast-pathed."""

    gate = world.gate()
    plan = world.plan()
    gate.assert_model_touch_allowed(plan)  # warm the GGUF cache

    lib = world.runtime_root / "llama.cpp" / "build" / "bin" / "libfake-impl.so"
    lib.write_bytes(b"tampered-library-bytes")
    with pytest.raises(GateClosed, match="drift"):
        gate.assert_model_touch_allowed(plan)


@pytest.mark.requires_wsl2_execution_authority
def test_cache_file_lives_under_data_root_not_the_repo(world):
    gate = world.gate()
    plan = world.plan()
    gate.assert_model_touch_allowed(plan)
    cache = _cache_path(world)
    assert cache.is_file()
    assert cache.parent == world.data_root
    assert cache.parent != world.source_root
    document = json.loads(cache.read_text(encoding="utf-8"))
    assert document["schema"] == contracts.RUNTIME_IDENTITY_CACHE_SCHEMA
    assert document["study"] == contracts.STUDY_SLUG
    assert set(document["gguf_files"]) == {
        f"{world.SUBDIR}/model-q8_0.gguf",
        f"{world.SUBDIR}/mmproj-bf16.gguf",
    }


# ---------------------------------------------------------------------------
# MINOR 1 (external-threat-model review round 4): the fast path never
# compared the receipt's own per-file `bytes` to anything -- only the
# AGGREGATE total was checked, at the very end of the per-file loop.
# ---------------------------------------------------------------------------


def _cheap_identity(path: Path) -> dict:
    info = path.stat()
    return {
        "size": info.st_size,
        "mtime_ns": info.st_mtime_ns,
        "st_ino": info.st_ino,
        "st_dev": info.st_dev,
    }


@pytest.mark.requires_wsl2_execution_authority
def test_forged_cache_cannot_hide_a_per_file_size_swap_when_aggregate_still_matches(world):
    """Demonstrated defect: swap the two pinned GGUF files' CONTENTS on disk
    (the aggregate byte total is unchanged -- len(GGUF_1)+len(GGUF_2) either
    way), then forge a cache file whose per-file entries match the SWAPPED
    files' own live stat (an attacker fully controls this cache -- module
    docstring: never an authority, ordinary unsigned JSON). Before the fix,
    the fast path accepted this outright; only the aggregate total was ever
    checked, and it still matched."""

    gate = world.gate()
    plan = world.plan()

    model_path = world.data_root / world.SUBDIR / "model-q8_0.gguf"
    mmproj_path = world.data_root / world.SUBDIR / "mmproj-bf16.gguf"
    model_path.write_bytes(world.GGUF_2)
    mmproj_path.write_bytes(world.GGUF_1)

    receipt_sha256 = hashlib.sha256(
        (world.receipts / "runtime.json").read_bytes()
    ).hexdigest()
    forged_cache = {
        "schema": contracts.RUNTIME_IDENTITY_CACHE_SCHEMA,
        "study": contracts.STUDY_SLUG,
        "runtime_receipt_sha256": receipt_sha256,
        "gguf_files": {
            f"{world.SUBDIR}/model-q8_0.gguf": _cheap_identity(model_path),
            f"{world.SUBDIR}/mmproj-bf16.gguf": _cheap_identity(mmproj_path),
        },
    }
    _cache_path(world).write_text(json.dumps(forged_cache), encoding="utf-8")

    with pytest.raises(GateClosed, match="size drift"):
        gate.assert_model_touch_allowed(plan, full_hash=False)


# ---------------------------------------------------------------------------
# MINOR 3 (external-threat-model review round 4): _load_identity_cache,
# _cheap_file_identity, _cheap_identity_matches, _write_identity_cache and
# _resolve_full_hash_override were imported as bare names in
# gate_runtime_gguf.py -- re-exported so they LOOKED patchable, but a
# monkeypatch on the `contracts` package attribute was never observed at the
# real call site.
# ---------------------------------------------------------------------------


@pytest.mark.requires_wsl2_execution_authority
def test_patched_load_identity_cache_is_observed_by_the_fast_path(world, monkeypatch):
    gate = world.gate()
    plan = world.plan()
    gate.assert_model_touch_allowed(plan, full_hash=False)  # warm a genuine, valid cache

    calls = []
    real_load = contracts._load_identity_cache

    def spy(cache_path, receipt_sha256):
        calls.append((cache_path, receipt_sha256))
        return real_load(cache_path, receipt_sha256)

    monkeypatch.setattr(contracts, "_load_identity_cache", spy)

    diagnostics: dict[str, object] = {}
    gate.assert_model_touch_allowed(plan, full_hash=False, diagnostics=diagnostics)
    assert calls, "the patched _load_identity_cache was never observed by the fast path"
    assert diagnostics["gguf_fast_path_used"] is True  # the real cache still warm/valid


@pytest.mark.requires_wsl2_execution_authority
def test_cache_is_never_written_after_a_failed_verification(world):
    """A failed check must never leave a cache record behind that a LATER,
    unrelated call could mistakenly trust."""

    world.runtime["gguf_files"][0]["sha256"] = "0" * 64  # tamper before first open
    gate = world.gate()
    plan = world.plan()
    with pytest.raises(GateClosed, match="SHA-256 drift"):
        gate.assert_model_touch_allowed(plan)
    assert not _cache_path(world).is_file()
