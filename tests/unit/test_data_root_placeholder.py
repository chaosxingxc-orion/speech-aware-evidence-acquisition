"""The data-root placeholder (owner rulings 289 B / 290 B, 2026-10-12).

A repository config never names where the data root lives: it spells ``${SAEA_DATA_ROOT}``. ``compose`` hashes the
UNEXPANDED text and hands consumers the expanded values, the preparation / promotion / pinned-document loaders expand
what they read, and every test below runs against a temporary root, so the sweep works with either default root.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core import config as cfg
from speech_aware_evidence_acquisition.core.data_root_placeholder import (
    DATA_ROOT_PLACEHOLDER,
    collapse_data_root,
    expand_data_root,
    resolve_data_root_text,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("SAEA_DATA_ROOT", raising=False)
    monkeypatch.delenv("SPEECHRL_DATA_DIR", raising=False)


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    for kind, body in {
        "model": {"model_lock_key": "k", "server_env": {"TRIGGER": "${SAEA_DATA_ROOT}/coordination/t.trigger"}},
        "dataset": {"dataset": "d"},
        "baseline": {"artifacts": [{"path": "${SAEA_DATA_ROOT}/runs/R/a.json", "sha256": "0" * 64}], "plain": "/home/chao/feat-cache"},
        "experiment": {"experiment": "e"},
    }.items():
        target = repo / "configs" / kind / f"{kind[0]}1.json"
        target.parent.mkdir(parents=True)
        target.write_text(json.dumps(body), encoding="utf-8")
    return repo


def test_resolution_order_is_explicit_then_saea_then_speechrl(monkeypatch, tmp_path):
    assert resolve_data_root_text() is None
    monkeypatch.setenv("SPEECHRL_DATA_DIR", "/b/")
    assert resolve_data_root_text() == "/b"
    monkeypatch.setenv("SAEA_DATA_ROOT", "/a")
    assert resolve_data_root_text() == "/a"
    assert resolve_data_root_text(tmp_path) == str(tmp_path)


def test_expand_is_recursive_leaves_keys_and_other_strings_and_is_a_noop_without_a_root():
    document = {"k${SAEA_DATA_ROOT}": ["${SAEA_DATA_ROOT}/x", {"n": "a ${SAEA_DATA_ROOT}/y b"}], "z": 3, "p": "/home/chao"}
    assert expand_data_root(document) == document  # no root known: verbatim
    expanded = expand_data_root(document, "/root")
    assert expanded == {"k${SAEA_DATA_ROOT}": ["/root/x", {"n": "a /root/y b"}], "z": 3, "p": "/home/chao"}


def test_collapse_inverts_expand_on_path_boundaries_only():
    document = {"a": "${SAEA_DATA_ROOT}/x", "b": ["${SAEA_DATA_ROOT}"], "c": "${SAEA_DATA_ROOT}-twin/y"}
    assert collapse_data_root(expand_data_root(document, "/root"), "/root")["a"] == "${SAEA_DATA_ROOT}/x"
    assert collapse_data_root("/rootless/x", "/root") == "/rootless/x"
    assert collapse_data_root("/root", "/") == "/root"


def test_compose_hash_is_the_placeholder_hash_whatever_the_root(monkeypatch, tmp_path):
    repo = _repo(tmp_path)
    bare = cfg.compose(repo, "m1", "d1", "b1", "e1")
    assert bare.values["artifacts"][0]["path"] == "${SAEA_DATA_ROOT}/runs/R/a.json"  # no root: verbatim, fail-closed at use
    first = tmp_path / "root-one"
    second = tmp_path / "root-two"
    one = cfg.compose(repo, "m1", "d1", "b1", "e1", data_root=first)
    two = cfg.compose(repo, "m1", "d1", "b1", "e1", data_root=second)
    assert one.values["artifacts"][0]["path"] == f"{first}/runs/R/a.json"
    assert one.values["server_env"]["TRIGGER"] == f"{first}/coordination/t.trigger"
    assert two.values["artifacts"][0]["path"] == f"{second}/runs/R/a.json"
    assert one.config_hash == two.config_hash == bare.config_hash
    assert one.values["plain"] == "/home/chao/feat-cache"
    monkeypatch.setenv("SAEA_DATA_ROOT", str(first))
    from_env = cfg.compose(repo, "m1", "d1", "b1", "e1")
    assert from_env.values["artifacts"][0]["path"] == f"{first}/runs/R/a.json"
    # a recomputation over the expanded values (registration checks) lands on the same identity
    assert cfg._canonical_hash(cfg.drop_null_arms(from_env.values)) == from_env.config_hash


def test_read_fragment_stays_unexpanded_so_fragment_hashes_do_not_move(tmp_path):
    repo = _repo(tmp_path)
    fragment = cfg.read_fragment(repo, "model", "m1")
    assert fragment["server_env"]["TRIGGER"].startswith(DATA_ROOT_PLACEHOLDER)


def test_pinned_json_expands_both_the_binding_and_the_document(tmp_path):
    from speech_aware_evidence_acquisition.core import speech_preparation_runtime as spr

    root = tmp_path / "data"
    (root / "coordination").mkdir(parents=True)
    document = {"encoder": {"path": "${SAEA_DATA_ROOT}/coordination/enc.json"}}
    target = root / "coordination" / "proto.json"
    raw = json.dumps(document).encode()
    target.write_bytes(raw)
    import hashlib

    import os

    os.environ["SAEA_DATA_ROOT"] = str(root)
    try:
        value = spr.pinned_json({"path": "${SAEA_DATA_ROOT}/coordination/proto.json", "sha256": hashlib.sha256(raw).hexdigest()})
    finally:
        del os.environ["SAEA_DATA_ROOT"]
    assert value["encoder"]["path"] == f"{root}/coordination/enc.json"


def test_promotion_plan_validation_expands_the_placeholder(tmp_path):
    from speech_aware_evidence_acquisition.core import packet_promotion as pp

    root = tmp_path / "data"
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    root.mkdir()
    plan = {
        "schema": pp.PLAN_SCHEMA, "source_root": "${SAEA_DATA_ROOT}",
        "source_roster_path": "${SAEA_DATA_ROOT}/a.json", "source_roster_sha256": "a" * 64,
        "cache_provenance_path": "${SAEA_DATA_ROOT}/b.json", "cache_provenance_sha256": "b" * 64,
        "cache_audit_path": "${SAEA_DATA_ROOT}/c.json", "cache_audit_sha256": "c" * 64,
        "legacy_cache_dir": str(legacy), "feature_root": str(tmp_path / "feat"),
        "receipt_output": "${SAEA_DATA_ROOT}/receipt.json",
        "decoder_gguf_sha256": "d" * 64, "mmproj_sha256": "e" * 64,
        "expected_n_embd": 4, "causal_attention": True, "workers": 2,
    }
    import os

    os.environ["SAEA_DATA_ROOT"] = str(root)
    try:
        checked = pp._validate_plan(plan)
    finally:
        del os.environ["SAEA_DATA_ROOT"]
    assert checked["receipt_output"] == root / "receipt.json"
    assert checked["source_roster_path"] == root / "a.json"


def test_every_swept_shell_script_that_reads_the_root_sources_the_authority():
    offenders = []
    for path in sorted((REPO_ROOT / "scripts").rglob("*.sh")):
        text = path.read_text(encoding="utf-8")
        if "$SAEA_DATA_ROOT" in text or "${SAEA_DATA_ROOT" in text:
            if "data_root.sh" not in text and path.relative_to(REPO_ROOT).as_posix() != "scripts/lib/data_root.sh":
                offenders.append(path.relative_to(REPO_ROOT).as_posix())
    assert offenders == [], offenders


def test_swept_shell_scripts_parse():
    paths = [p for p in (REPO_ROOT / "scripts").rglob("*.sh") if "SAEA_DATA_ROOT" in p.read_text(encoding="utf-8")]
    assert paths
    for path in paths:
        result = subprocess.run(["bash", "-n", str(path)], capture_output=True, text=True)
        assert result.returncode == 0, (path, result.stderr)


def test_no_committed_config_names_an_absolute_data_root():
    pattern = re.compile(r"/mnt/e/|/home/chao/saea-data|/mnt/wsl/saea-data")
    bad = [p.relative_to(REPO_ROOT).as_posix() for p in (REPO_ROOT / "configs").rglob("*")
           if p.is_file() and p.suffix in {".json", ".yaml", ".yml"} and p.relative_to(REPO_ROOT).as_posix() != "configs/base/engineering-base-v1.json"
           and pattern.search(p.read_text(encoding="utf-8"))]
    assert bad == [], bad
