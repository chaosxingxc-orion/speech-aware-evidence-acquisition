"""Contract 8: the committed E0 receipts stay true on every checkout, in CI.

Without this, receipt drift (an edited scoring source, a tampered artifact, a
regenerated-but-not-reclosed deliverable) would only surface when someone manually
ran the gate dry-run. These checks are cheap (KBs of hashing, no data root, no
model bytes) and run everywhere; the GGUF/runtime-library re-hash remains the
model-touch gate's job on the machine that owns those bytes.
"""

import json
import re
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.contracts import (
    E0_RECEIPT_SCHEMA,
    MODEL_LOCK_KEY,
    RUNTIME_RECEIPT_SCHEMA,
    SCORING_PACKAGE_RELPATH,
    STUDY_SLUG,
    FrozenCoreGate,
)
from speech_aware_evidence_acquisition.e0.artifacts import sha256_file

REPO_ROOT = Path(__file__).resolve().parents[2]
RECEIPTS = REPO_ROOT / "docs" / "receipts"

pytestmark = pytest.mark.skipif(
    not (RECEIPTS / "e0-closure.json").is_file(),
    reason="E0 closure receipts not landed in this checkout",
)


def test_e0_closure_chain_verifies_via_the_real_gate():
    gate = FrozenCoreGate(
        e0_receipt=RECEIPTS / "e0-closure.json",
        runtime_receipt=RECEIPTS / "runtime.json",
        data_root=REPO_ROOT,
        lock_path=REPO_ROOT / "does-not-matter-for-e0.json",
        runtime_root=REPO_ROOT,
        exposure_ledger=REPO_ROOT / "docs" / "exposure-ledger.md",
        source_root=REPO_ROOT,
    )
    gate._validate_e0()


def test_d3_freeze_matches_the_working_tree():
    d3 = json.loads(
        (RECEIPTS / "artifacts" / "d3-scoring.json").read_text(encoding="utf-8")
    )
    frozen = d3["frozen_sources_sha256"]
    scoring_dir = REPO_ROOT / SCORING_PACKAGE_RELPATH
    actual = {
        f"{SCORING_PACKAGE_RELPATH}/{path.name}"
        for path in scoring_dir.iterdir()
        if path.is_file() and path.name.endswith(".py")
    }
    assert set(frozen) == actual, "the freeze must name exactly the scoring package"
    for relpath, digest in frozen.items():
        assert sha256_file(REPO_ROOT / relpath) == digest, f"{relpath} drifted"


def test_runtime_receipt_is_internally_coherent():
    runtime = json.loads((RECEIPTS / "runtime.json").read_text(encoding="utf-8"))
    assert runtime["schema"] == RUNTIME_RECEIPT_SCHEMA
    assert runtime["study"] == STUDY_SLUG
    assert runtime["model_lock_key"] == MODEL_LOCK_KEY

    build = runtime["llama_cpp"]
    reported = re.search(r"\(([0-9a-f]{7,40})\)", build["reported_build"])
    assert reported is not None
    assert build["build_commit"].startswith(reported.group(1))

    gguf_paths = [entry["path"] for entry in runtime["gguf_files"]]
    assert len(gguf_paths) == len(set(gguf_paths)) == 2
    assert all(entry["bytes"] > 0 for entry in runtime["gguf_files"])

    bin_dir = build["binary_path"].rsplit("/", 1)[0]
    library_paths = [entry["path"] for entry in runtime["runtime_libraries"]]
    assert library_paths, "a lone launcher stub cannot be the runtime"
    assert len(library_paths) == len(set(library_paths))
    assert all(path.rsplit("/", 1)[0] == bin_dir for path in library_paths)
    assert build["binary_path"] not in library_paths
