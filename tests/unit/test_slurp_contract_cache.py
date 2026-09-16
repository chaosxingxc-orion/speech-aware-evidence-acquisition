from __future__ import annotations
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pytest
from speech_aware_evidence_acquisition.data import slurp
from speech_aware_evidence_acquisition.data import slurp_contract_cache as cache


def _record(scenario: str, action: str = "play") -> dict[str, object]:
    return {
        "slurp_id": 1,
        "scenario": scenario,
        "action": action,
        "tokens": [{"id": 0, "surface": "jazz"}],
        "entities": [{"type": "genre", "span": [0]}],
    }


@pytest.fixture
def source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    metadata = tmp_path / "metadata"
    audio = tmp_path / "audio"
    metadata.mkdir()
    audio.mkdir()
    train = metadata / "train.jsonl"
    synthetic = metadata / "train_synthetic.jsonl"
    train.write_text(json.dumps(_record("music")) + "\n", encoding="utf-8")
    synthetic.write_text(json.dumps(_record("alarm", "set")) + "\n", encoding="utf-8")
    def roots(lock, root):
        return ("audio", audio, metadata)
    monkeypatch.setattr(slurp, "_governed_roots", roots)
    monkeypatch.setattr(cache, "_governed_roots", roots)
    lock = {"assets": [{"name": "slurp", "annotations": {"governed_copy": "metadata"}}]}
    cache.clear_slurp_contract_cache()
    return tmp_path, lock, train, synthetic


def test_cold_warm_contract_is_byte_identical_and_parses_once(source, monkeypatch):
    _, lock, _, _ = source
    calls = 0
    original = cache.load_slurp_ontology

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(cache, "load_slurp_ontology", counted)
    first = cache.load_cached_slurp_contract(lock, source[0])
    second = cache.load_cached_slurp_contract(lock, source[0])
    assert first == second
    assert calls == 1


def test_source_bytes_invalidate_even_when_size_and_mtime_are_preserved(source):
    root, lock, train, _ = source
    first = cache.load_cached_slurp_contract(lock, root)
    stat = train.stat()
    replacement = json.dumps(_record("alarm")) + "\n"
    assert len(replacement) == train.stat().st_size
    train.write_text(replacement, encoding="utf-8")
    os.utime(train, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    second = cache.load_cached_slurp_contract(lock, root)
    assert first != second
    assert "alarm" in second


def test_train_default_never_reads_query_or_synthetic_metadata(source):
    root, lock, _, synthetic = source
    synthetic.write_text("not valid JSON", encoding="utf-8")
    (synthetic.parent / "devel.jsonl").write_text("not valid JSON", encoding="utf-8")
    (synthetic.parent / "test.jsonl").write_text("not valid JSON", encoding="utf-8")
    expected = slurp.render_slurp_ontology(slurp.load_slurp_ontology(lock, root))
    from speech_aware_evidence_acquisition.rails.adapters.slurp import SlurpAdapter

    class ForbiddenSample:
        def __getattribute__(self, name):
            raise AssertionError("task contract must not read query fields")

    adapter = SlurpAdapter(lock, root)
    assert adapter.build_task_contract(ForbiddenSample(), None) == expected
    assert adapter.build_task_contract(ForbiddenSample(), None) == expected


def test_cache_is_bounded_and_implementation_identity_is_bound(source, monkeypatch):
    root, lock, _, _ = source
    monkeypatch.setattr(cache, "_MAX_ENTRIES", 2)
    first = cache.load_cached_slurp_contract(lock, root)
    for revision in ("next", "third"):
        monkeypatch.setattr(cache, "_IMPLEMENTATION_SHA256", revision)
        assert cache.load_cached_slurp_contract(lock, root) == first
    assert len(cache._CACHE) == 2
    assert {key[1] for key in cache._CACHE} == {"next", "third"}


def test_concurrent_cold_calls_parse_once(source, monkeypatch):
    _, lock, _, _ = source
    calls = 0
    guard = threading.Lock()
    original = cache.load_slurp_ontology

    def counted(*args, **kwargs):
        nonlocal calls
        with guard:
            calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(cache, "load_slurp_ontology", counted)
    with ThreadPoolExecutor(max_workers=8) as pool:
        values = list(
            pool.map(
                lambda _: cache.load_cached_slurp_contract(lock, source[0]), range(8)
            )
        )
    assert len(set(values)) == 1
    assert calls == 1


def test_source_drift_during_parse_is_refused(source, monkeypatch):
    root, lock, train, _ = source
    original = cache.load_slurp_ontology

    def drifting(*args, **kwargs):
        result = original(*args, **kwargs)
        train.write_text(train.read_text(encoding="utf-8") + " ", encoding="utf-8")
        return result

    monkeypatch.setattr(cache, "load_slurp_ontology", drifting)
    with pytest.raises(cache.SlurpContractCacheError, match="changed while loading"):
        cache.load_cached_slurp_contract(lock, root)


def test_governed_lock_identity_invalidates_entry(source):
    root, lock, _, _ = source
    first = cache.load_cached_slurp_contract(lock, root)
    changed = {
        "assets": [
            {
                "name": "slurp",
                "annotations": {"governed_copy": "metadata"},
                "revision": "changed",
            }
        ]
    }
    second = cache.load_cached_slurp_contract(changed, root)
    assert first == second
    assert len(cache._CACHE) == 2


def test_contract_views_preserve_legacy_bytes_and_do_not_alias(source, monkeypatch):
    root, lock, _, _ = source
    calls = 0
    original = cache.load_slurp_ontology

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(cache, "load_slurp_ontology", counted)
    ontology = original(lock, root)
    legacy = cache.load_cached_slurp_contract(lock, root)
    projected = cache.load_cached_slurp_contract(
        lock, root, view=cache.SLURP_TASK_CONTRACT_VIEW_LABEL_INVENTORY
    )

    assert legacy == slurp.render_slurp_ontology(ontology)
    assert projected == slurp.render_slurp_label_inventory(ontology)
    assert legacy != projected
    assert calls == 2
    assert len(cache._CACHE) == 2

    assert cache.load_cached_slurp_contract(lock, root) == legacy
    assert cache.load_cached_slurp_contract(
        lock, root, view=cache.SLURP_TASK_CONTRACT_VIEW_LABEL_INVENTORY
    ) == projected
    assert calls == 2


def test_unknown_contract_view_refuses_before_source_resolution(source, monkeypatch):
    root, lock, _, _ = source

    def forbidden(*_args, **_kwargs):
        raise AssertionError("unknown views must fail before runtime data loading")

    monkeypatch.setattr(cache, "_governed_roots", forbidden)
    with pytest.raises(cache.SlurpContractCacheError, match="unsupported.*view"):
        cache.load_cached_slurp_contract(lock, root, view="invented-view")
