"""Verify the shared seal/scoring cleanliness gate with real temporary Git repos."""

from __future__ import annotations

import subprocess

import pytest

from speech_aware_evidence_acquisition.core.bundle import BundleError
from speech_aware_evidence_acquisition.core.bundle.git_commit import (
    _dirty_relpaths,
    require_clean_load_bearing_surface,
    require_clean_study_repo,
)


def _git(root, *args):
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


@pytest.fixture
def status_repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "Synthetic Review")
    _git(root, "config", "user.email", "synthetic@example.invalid")
    (root / "README.md").write_text("Synthetic repository.\n", encoding="utf-8")
    _git(root, "add", "README.md")
    _git(root, "commit", "-qm", "Synthetic initial state")
    return root


@pytest.mark.parametrize("relative", ["src/scorer.py", "scripts/score.py", "configs/cell.json", "docs/arms/cell.json"])
def test_first_unstaged_load_bearing_change_refuses(status_repo, relative):
    target = status_repo / relative
    target.parent.mkdir(parents=True)
    target.write_text("original\n", encoding="utf-8")
    _git(status_repo, "add", relative)
    _git(status_repo, "commit", "-qm", "Synthetic load-bearing file")
    target.write_text("changed\n", encoding="utf-8")
    assert _git(status_repo, "status", "--porcelain").startswith(" M ")
    with pytest.raises(BundleError, match="load-bearing"):
        require_clean_load_bearing_surface(status_repo)


def test_rename_out_of_load_bearing_tree_refuses(status_repo):
    source = status_repo / "src/scorer.py"
    source.parent.mkdir()
    source.write_text("original\n", encoding="utf-8")
    _git(status_repo, "add", "src/scorer.py")
    _git(status_repo, "commit", "-qm", "Synthetic source")
    (status_repo / "docs/readiness").mkdir(parents=True)
    _git(status_repo, "mv", "src/scorer.py", "docs/readiness/scorer.py")
    with pytest.raises(BundleError, match="load-bearing"):
        require_clean_load_bearing_surface(status_repo)


def test_wholly_untracked_docs_tree_cannot_hide_an_arm(status_repo):
    target = status_repo / "docs/arms/new.json"
    target.parent.mkdir(parents=True)
    target.write_text("{}\n", encoding="utf-8")
    assert _git(status_repo, "status", "--porcelain") == "?? docs/\n"
    with pytest.raises(BundleError, match="load-bearing"):
        require_clean_load_bearing_surface(status_repo)


def test_governance_filenames_survive_spaces_quotes_arrows_and_newlines(status_repo):
    relative = 'docs/readiness/ note "quoted" -> next\nline.md'
    target = status_repo / relative
    target.parent.mkdir(parents=True)
    target.write_text("Synthetic note.\n", encoding="utf-8")
    commit, tolerated = require_clean_load_bearing_surface(status_repo)
    assert commit == _git(status_repo, "rev-parse", "HEAD").strip()
    assert tolerated == [relative]
    with pytest.raises(BundleError, match="uncommitted"):
        require_clean_study_repo(status_repo)


@pytest.mark.parametrize("status", ["R ", "C "])
def test_nul_porcelain_preserves_both_rename_or_copy_paths(status):
    assert _dirty_relpaths(
        f'{status} docs/readiness/after -> move.md\0src/before "quoted".py\0'
    ) == ["docs/readiness/after -> move.md", 'src/before "quoted".py']


@pytest.mark.parametrize("malformed", [" M src/a.py", "M src/a.py\0", "?? \0", "R  docs/note.md\0", "?? docs/note.md\0\0"])
def test_malformed_status_fails_closed(malformed):
    with pytest.raises(BundleError, match="porcelain"):
        _dirty_relpaths(malformed)


def test_clean_repository_returns_exact_head(status_repo):
    assert require_clean_load_bearing_surface(status_repo) == (
        _git(status_repo, "rev-parse", "HEAD").strip(), []
    )
