"""Contract 1+2: registry/contract/index/origin/package identity agree; lock keys exist.

Cross-repository assertions run only when the umbrella checkout is adjacent
(the registered layout ``<umbrella>/studies/<slug>/``); a standalone clone skips them
instead of asserting blind.
"""

import json
import re
import subprocess
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SLUG = "speech-aware-evidence-acquisition"
UMBRELLA = REPO_ROOT.parent.parent
UMBRELLA_PRESENT = (UMBRELLA / "wiki" / "Experiment-Assets.md").is_file()

requires_umbrella = pytest.mark.skipif(
    not UMBRELLA_PRESENT, reason="umbrella checkout not adjacent; cross-repo checks skipped"
)


def read_pyproject() -> dict:
    return tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_package_identity_matches_repository():
    project = read_pyproject()["project"]
    assert project["name"] == SLUG
    assert not re.search(r"(?:^|-)r\d+(?:-|$)", project["name"], flags=re.IGNORECASE), (
        "candidate IDs must never become engineering identity"
    )


@requires_umbrella
def test_registry_binds_this_repository():
    registry = json.loads(
        (UMBRELLA / "studies" / "registry.json").read_text(encoding="utf-8")
    )
    entries = [entry for entry in registry["studies"] if entry["slug"] == SLUG]
    assert len(entries) == 1, "this study must be registered exactly once"
    entry = entries[0]
    assert entry["package_name"] == read_pyproject()["project"]["name"]
    assert entry["local_path"] == f"studies/{SLUG}"
    assert (UMBRELLA / entry["decision_record"]).is_file()
    assert (UMBRELLA / entry["experiment_index"]).is_file()

    completed = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "remote", "get-url", "origin"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        pytest.skip("no origin remote configured in this checkout")
    assert completed.stdout.strip() == entry["github_repo"]


@requires_umbrella
def test_effective_contract_carries_stage3_paper_gate():
    registry = json.loads(
        (UMBRELLA / "studies" / "registry.json").read_text(encoding="utf-8")
    )
    entry = next(item for item in registry["studies"] if item["slug"] == SLUG)
    contract = (UMBRELLA / entry["decision_record"]).read_text(encoding="utf-8")
    assert "OWNER_GO_AND_PAPER_EXECUTION_CONTRACT" in contract, (
        "the pinned effective contract must carry the Stage-3 paper-gate stop line"
    )
    assert "paper-scale-confirmatory" in contract, (
        "the pinned effective contract must freeze the execution-scope profile boundary"
    )


@requires_umbrella
def test_experiment_index_frontmatter_matches_this_study():
    index = (UMBRELLA / "wiki" / "experiments" / SLUG / "README.md").read_text(encoding="utf-8")
    frontmatter = re.match(r"\A---\r?\n(.*?)\r?\n---", index, flags=re.DOTALL)
    assert frontmatter is not None
    assert f'study_slug: "{SLUG}"' in frontmatter.group(1)
    assert 'experiment_id_namespace: "SAEA-E' in frontmatter.group(1)


@requires_umbrella
def test_carrier_and_model_lock_keys_exist_in_umbrella_lock():
    lock_text = (UMBRELLA / "docs" / "datasets.lock.json").read_text(encoding="utf-8")
    lock = json.loads(lock_text)
    names = set()

    def collect(node):
        if isinstance(node, dict):
            name = node.get("name")
            if isinstance(name, str):
                names.add(name)
            for value in node.values():
                collect(value)
        elif isinstance(node, list):
            for item in node:
                collect(item)

    collect(lock)
    for key in (
        "earnings21-original",
        "earnings22-original",
        "conec",
        "qwen3-omni-30b-a3b-instruct-gguf",
    ):
        assert key in names, f"lock key {key} missing from umbrella datasets.lock.json"


def test_no_data_bytes_are_tracked_by_git():
    completed = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        pytest.skip("not a git checkout")
    forbidden_suffixes = (
        ".wav", ".mp3", ".flac", ".gguf", ".pt", ".pth", ".safetensors",
        ".npy", ".npz", ".parquet", ".arrow", ".bin",
    )
    offenders = [
        line
        for line in completed.stdout.splitlines()
        if line.lower().endswith(forbidden_suffixes)
    ]
    assert offenders == [], f"data/weight bytes must never enter Git: {offenders}"


def test_dataset_and_model_configs_reference_lock_keys_only():
    config_root = REPO_ROOT / "configs"
    referenced = []
    for config in sorted(config_root.rglob("*.yaml")):
        text = config.read_text(encoding="utf-8")
        match = re.search(r"^\s*lock_key:\s*(\S+)", text, flags=re.MULTILINE)
        if "dataset" in config.parts or "model" in config.parts:
            assert re.search(r"sha256:\s*\S", text) is None, (
                f"{config}: asset hashes live in the umbrella lock, not study configs"
            )
            assert match is not None, f"{config}: carrier/model configs must name a lock_key"
            referenced.append(match.group(1))
    for key in ("earnings21-original", "earnings22-original", "conec"):
        assert key in referenced, f"carrier config for {key} is missing"
    assert "qwen3-omni-30b-a3b-instruct-gguf" in referenced


def test_general_audio_assets_cannot_enter_executable_surface():
    """No source file may name a general-audio asset directly.

    The T2 carrier-scope gate (``contracts.general_audio_deny_lock_keys``) reads the
    excluded-carrier list from ``configs/experiment/e0-model-free-closure.yaml`` at
    verification time rather than hard-coding it — the same single-source discipline
    ``e0/d2_leakage.py`` already enforces as a negative control — so package source
    never needs to mention these names at all. The only permitted occurrences of the
    three excluded names are inside that config file and inside refusal tests (this
    scan covers ``src/`` only, so config and test occurrences are outside its scope
    by construction); this test additionally proves the gate's denylist function
    resolves to exactly those three names against the real config.
    """

    forbidden = {"fsd50k", "audioset-metadata-features", "esc-50"}
    source_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((REPO_ROOT / "src").rglob("*.py"))
    ).lower()
    assert not any(name in source_text for name in forbidden)

    from speech_aware_evidence_acquisition.contracts import general_audio_deny_lock_keys

    assert general_audio_deny_lock_keys(REPO_ROOT) == frozenset(forbidden), (
        "the config-derived denylist must resolve to exactly the excluded general-audio assets"
    )

    configured_lock_keys = set()
    for path in sorted((REPO_ROOT / "configs").rglob("*.yaml")):
        configured_lock_keys.update(
            re.findall(
                r"^\s*lock_key:\s*(\S+)", path.read_text(encoding="utf-8"), re.MULTILINE
            )
        )
    assert not forbidden.intersection(configured_lock_keys), (
        "general-audio assets may be named as exclusions but must not be configured as lock_key inputs"
    )
