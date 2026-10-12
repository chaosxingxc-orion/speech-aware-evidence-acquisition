"""``scripts/checks/engineering_base_locator_check.py`` (decision 274 / ruling 284).

The gate must PASS on the real tree and FAIL on each defect it exists to catch: an authority line
that disagrees with the manifest, a live script that hard-codes the legacy root or skips the
authority, a NEW hard-coded legacy-root file, a model or geometry drift, a hot path on 9p or
tmpfs, an unmounted hot root after the cut-over, and a promotion receipt that no longer hashes to
its pin. Every negative control is a synthetic tree under ``tmp_path``; the real one is only read.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CHECK_PATH = REPO_ROOT / "scripts" / "checks" / "engineering_base_locator_check.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("engineering_base_locator_check", CHECK_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # the gate's dataclass resolves its own module at class creation
    spec.loader.exec_module(module)
    return module


ebl = _load_module()

LEGACY = "/srv/legacy-e/speechrl-data"
HOT = "/home/chao/saea-data/speechrl-data"
GGUF_SHA = "a" * 64
MMPROJ_SHA = "b" * 64


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _authority(current: str = LEGACY) -> str:
    return (
        "# shellcheck shell=bash\n"
        f"SAEA_LEGACY_DATA_ROOT={LEGACY}\n"
        f"SAEA_HOT_DATA_ROOT={HOT}\n"
        f"SAEA_DATA_ROOT_DEFAULT={current}\n"
        "saea_data_root_init() { :; }\n"
    )


def _manifest(tmp: Path) -> dict:
    model_dir = tmp / "models"
    packets = tmp / "packets"
    return {
        "schema": "saea-engineering-base-v1",
        "roots": {
            "data_root": {"current": LEGACY, "status": "pre-cut-over"},
            "legacy": {"path": LEGACY},
            "hot": {"path": HOT},
            "runtime_root": {"path": str(tmp / "runtime")},
        },
        "hot_paths": ["data_root", "runtime_root"],
        "migration": {},
        "models": [{
            "core": "instruct", "lock_key": "core-q4km",
            "gguf": {"path": str(model_dir / "core.gguf"), "sha256": GGUF_SHA, "size_bytes": 5},
            "mmproj": {"path": str(model_dir / "mmproj.gguf"), "sha256": MMPROJ_SHA, "size_bytes": 3},
            "runtime_receipt": "docs/receipts/runtime.json", "llama_cpp_build_commit": "c" * 40,
        }],
        "packet_roots": [{"id": "p1", "core": "instruct", "path": str(packets),
                          "promotion_receipts": [{"name": "R-promotion.json",
                                                  "sha256": hashlib.sha256(b"{}\n").hexdigest()}]}],
        "serving_geometries": [{"target": "slurp-np4", "core": "instruct", "session_id": "sid-1",
                                "model_fragment": "frag-1", "ctx": 98304, "slots": 4, "max_tokens": 512,
                                "packet_root": "p1"}],
        "live_scripts": [{"path": "scripts/flights/batch/driver.sh", "role": "entry"},
                         {"path": "scripts/flights/batch/serving_lib.sh", "role": "library"}],
        "timing_budget": {},
    }


def _tree(tmp: Path, manifest: dict | None = None) -> Path:
    repo = tmp / "repo"
    manifest = manifest if manifest is not None else _manifest(tmp)
    _write(repo / ebl.MANIFEST_RELPATH, json.dumps(manifest))
    _write(repo / ebl.AUTHORITY_RELPATH, _authority(manifest["roots"]["data_root"]["current"]))
    _write(repo / ebl.BASELINE_RELPATH, json.dumps({"legacy_literal_files": []}))
    _write(repo / "scripts/old_read.py", 'DATA = os.environ["SAEA_DATA_ROOT"]\n')
    _write(repo / "scripts/flights/batch/driver.sh",
           'source "$(dirname "$0")/../../lib/data_root.sh" || exit 70\nsaea_data_root_init || exit 70\n')
    _write(repo / "scripts/flights/batch/serving_lib.sh",
           'source "$(dirname "$0")/../../lib/data_root.sh"\n'
           "saea_geometry() {\n  case \"$1\" in\n"
           "    slurp-np4)\n      G_SID=sid-1\n      G_FRAGMENT=frag-1\n      G_LABEL=X ;;\n"
           "    *) return 1 ;;\n  esac\n}\n")
    _write(repo / "docs/receipts/runtime.json", json.dumps({
        "model_lock_key": "core-q4km", "gguf_files": [{"path": "models/core.gguf", "sha256": GGUF_SHA}],
        "llama_cpp": {"build_commit": "c" * 40}}))
    _write(repo / "configs/model/frag-1.json", json.dumps({
        "model_lock_key": "core-q4km", "server_args": ["-c", "98304", "-np", "4"],
        "decoding_params": {"max_tokens": 512}, "speech_feature_root": manifest["packet_roots"][0]["path"],
        "server_env": {"LLAMA_SPEECH_DECODER_SHA256": GGUF_SHA}}))
    return repo


def _run(repo: Path, **kwargs):
    return ebl.run(repo, **kwargs)


def test_real_tree_passes_in_repository_mode() -> None:
    report = ebl.run(REPO_ROOT)
    assert report.failures == [], report.failures


def test_synthetic_tree_passes(tmp_path: Path) -> None:
    report = _run(_tree(tmp_path))
    assert report.failures == []
    assert any("[ratchet]" in line for line in report.passes)


def test_authority_line_must_equal_the_manifest(tmp_path: Path) -> None:
    repo = _tree(tmp_path)
    _write(repo / ebl.AUTHORITY_RELPATH, _authority(HOT))
    report = _run(repo)
    assert any("SAEA_DATA_ROOT_DEFAULT" in f for f in report.failures)


def test_cut_over_status_must_match_the_current_root(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    manifest["roots"]["data_root"]["status"] = "cut-over"
    report = _run(_tree(tmp_path, manifest))
    assert any("status cut-over" in f for f in report.failures)


def test_duplicate_authority_assignment_fails(tmp_path: Path) -> None:
    repo = _tree(tmp_path)
    path = repo / ebl.AUTHORITY_RELPATH
    path.write_text(path.read_text(encoding="utf-8") + f"SAEA_DATA_ROOT_DEFAULT={LEGACY}\n", encoding="utf-8")
    assert any("exactly once" in f for f in _run(repo).failures)


def test_live_script_with_the_literal_fails(tmp_path: Path) -> None:
    repo = _tree(tmp_path)
    _write(repo / "scripts/flights/batch/driver.sh",
           f'source lib/data_root.sh\nsaea_data_root_init\nDATA={LEGACY}\n')
    report = _run(repo)
    assert any("driver.sh: hard-codes" in f for f in report.failures)


def test_entry_script_without_the_guard_fails(tmp_path: Path) -> None:
    repo = _tree(tmp_path)
    _write(repo / "scripts/flights/batch/driver.sh", 'source lib/data_root.sh\nDATA=$SAEA_DATA_ROOT\n')
    assert any("never calls saea_data_root_init" in f for f in _run(repo).failures)


def test_missing_live_script_fails(tmp_path: Path) -> None:
    repo = _tree(tmp_path)
    (repo / "scripts/flights/batch/driver.sh").unlink()
    assert any("declared live script is missing" in f for f in _run(repo).failures)


def test_any_hard_coded_data_root_path_fails(tmp_path: Path) -> None:
    repo = _tree(tmp_path)
    _write(repo / "configs/experiment/new-cell.json", json.dumps({"path": f"{LEGACY}/runs/x"}))
    report = _run(repo)
    assert any("configs/experiment/new-cell.json: hard-coded data-root path" in f for f in report.failures)


def test_generic_e_drive_data_root_paths_fail_whatever_the_manifest_legacy_root(tmp_path: Path) -> None:
    for index, literal in enumerate(("/mnt/" + "e/chao_workspace/anything", "/mnt/" + "e/some/where/speechrl-data/runs")):
        repo = _tree(tmp_path / f"t{index}")
        _write(repo / "tests/unit/test_x.py", f'DATA = "{literal}"\n')
        assert any("tests/unit/test_x.py: hard-coded" in f for f in _run(repo).failures), literal


def test_the_placeholder_and_the_environment_spelling_pass(tmp_path: Path) -> None:
    repo = _tree(tmp_path)
    _write(repo / "configs/experiment/cell.json", json.dumps({"path": "${SAEA_DATA_ROOT}/runs/x"}))
    _write(repo / "scripts/read.sh", 'DATA="$SAEA_DATA_ROOT"\n')
    assert _run(repo).failures == []


def test_a_non_empty_baseline_fails(tmp_path: Path) -> None:
    repo = _tree(tmp_path)
    _write(repo / ebl.BASELINE_RELPATH, json.dumps({"legacy_literal_files": ["scripts/old_read.py"]}))
    assert any("baseline must be empty" in f for f in _run(repo).failures)


def test_runtime_receipt_drift_fails(tmp_path: Path) -> None:
    repo = _tree(tmp_path)
    _write(repo / "docs/receipts/runtime.json", json.dumps({
        "model_lock_key": "core-q4km", "gguf_files": [{"sha256": "d" * 64}], "llama_cpp": {"build_commit": "e" * 40}}))
    failures = _run(repo).failures
    assert any("does not pin the declared GGUF" in f for f in failures)
    assert any("build commit" in f for f in failures)


def test_umbrella_lock_must_name_both_hashes(tmp_path: Path) -> None:
    repo = _tree(tmp_path)
    lock = _write(tmp_path / "lock.json", json.dumps({"models": [{"name": "core-q4km", "note": f"gguf {GGUF_SHA}"}]}))
    failures = _run(repo, umbrella_lock=lock).failures
    assert any("mmproj sha256" in f for f in failures)
    assert not any("gguf sha256" in f for f in failures)


def test_geometry_drift_fails(tmp_path: Path) -> None:
    repo = _tree(tmp_path)
    _write(repo / "configs/model/frag-1.json", json.dumps({
        "model_lock_key": "core-q4km", "server_args": ["-c", "65536", "-np", "2"],
        "decoding_params": {"max_tokens": 640}, "speech_feature_root": "/elsewhere"}))
    failures = _run(repo).failures
    for needle in ("-c 65536", "-np 2", "max_tokens 640", "speech_feature_root /elsewhere"):
        assert any(needle in f for f in failures), needle


def test_serving_lib_row_drift_fails(tmp_path: Path) -> None:
    repo = _tree(tmp_path)
    path = repo / "scripts/flights/batch/serving_lib.sh"
    path.write_text(path.read_text(encoding="utf-8").replace("G_SID=sid-1", "G_SID=sid-2"), encoding="utf-8")
    assert any("row slurp-np4" in f for f in _run(repo).failures)


MOUNTINFO = (
    "24 1 8:48 / / rw,relatime - ext4 /dev/sdd rw\n"
    "60 24 0:50 / /mnt/e rw,noatime - 9p drvfs rw\n"
    "70 24 0:60 / /mnt/wsl rw - tmpfs none rw\n"
    "71 70 8:64 / /mnt/wsl/saea-data-1 rw,relatime - ext4 /dev/sde rw\n"
    "72 24 0:61 / /mnt/with\\040space rw - ext4 /dev/sdf rw\n"
)


def test_mountinfo_parse_and_longest_prefix() -> None:
    mounts = ebl.parse_mountinfo(MOUNTINFO)
    assert ("/mnt/with space", "ext4") in mounts
    assert ebl.fstype_of("/mnt/e/x/y", mounts) == "9p"
    assert ebl.fstype_of("/mnt/wsl/saea-data-1/runs", mounts) == "ext4"
    assert ebl.fstype_of("/mnt/wsl/other", mounts) == "tmpfs"
    assert ebl.fstype_of("/home/chao", mounts) == "ext4"
    assert ebl.fstype_of("/mnt/eagle", mounts) == "ext4"


def _host_manifest(tmp: Path, *, runtime: Path, hot: Path, status: str = "pre-cut-over") -> dict:
    manifest = _manifest(tmp)
    manifest["roots"]["runtime_root"]["path"] = str(runtime)
    manifest["roots"]["hot"]["path"] = str(hot)
    if status == "cut-over":
        manifest["roots"]["data_root"] = {"current": str(hot), "status": "cut-over"}
    return manifest


def _mountinfo_for(root: Path, fstype: str, *, own_mount: bool = True) -> str:
    real = str(root.resolve())
    lines = ["24 1 8:48 / / rw - ext4 /dev/sdd rw"]
    if own_mount:
        lines.append(f"80 24 8:64 / {real} rw - {fstype} /dev/sde rw")
    return "\n".join(lines) + "\n"


def test_host_mode_refuses_a_hot_path_on_9p(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    hot = tmp_path / "hot"
    hot.mkdir()
    report = ebl.Report()
    manifest = _host_manifest(tmp_path, runtime=runtime, hot=hot)
    mounts = ebl.parse_mountinfo(_mountinfo_for(hot, "ext4") + f"81 24 0:9 / {runtime.resolve()} rw - 9p drvfs rw\n")
    ebl.check_hot_filesystems(manifest, mounts, report, require_hot_mounted=False)
    assert any("runtime_root" in f and "'9p'" in f for f in report.failures)
    assert any("9p E: original" in w for w in report.warnings)


def test_hot_root_unmounted_warns_before_and_fails_after_cut_over(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    hot = tmp_path / "hot"
    hot.mkdir()
    mounts = ebl.parse_mountinfo(_mountinfo_for(hot, "tmpfs"))
    before = ebl.Report()
    ebl.check_hot_filesystems(_host_manifest(tmp_path, runtime=runtime, hot=hot), mounts, before, require_hot_mounted=False)
    assert any("[hot-mount]" in w for w in before.warnings)
    assert not any("[hot-mount]" in f for f in before.failures)
    after = ebl.Report()
    ebl.check_hot_filesystems(_host_manifest(tmp_path, runtime=runtime, hot=hot, status="cut-over"), mounts, after,
                              require_hot_mounted=False)
    assert any("[hot-mount]" in f for f in after.failures)
    assert any("data_root" in f and "'tmpfs'" in f for f in after.failures)
    forced = ebl.Report()
    ebl.check_hot_filesystems(_host_manifest(tmp_path, runtime=runtime, hot=hot), mounts, forced, require_hot_mounted=True)
    assert any("[hot-mount]" in f for f in forced.failures)


def test_hot_root_through_a_symlink_to_its_own_ext4_mount_passes(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    mount = tmp_path / "mnt-wsl-saea-data-1"
    mount.mkdir()
    link = tmp_path / "saea-data"
    link.symlink_to(mount)
    report = ebl.Report()
    mounts = ebl.parse_mountinfo(_mountinfo_for(mount, "ext4"))
    ebl.check_hot_filesystems(_host_manifest(tmp_path, runtime=runtime, hot=link, status="cut-over"), mounts, report,
                              require_hot_mounted=True)
    assert report.failures == []


def test_hot_root_as_a_directory_inside_its_ext4_mount_passes(tmp_path: Path) -> None:
    """Decision 296: the hot root is <mount>/speechrl-data, not the mount point itself."""
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    mount = tmp_path / "mnt-wsl-saea-data-1"
    (mount / "speechrl-data").mkdir(parents=True)
    link = tmp_path / "saea-data"
    link.symlink_to(mount)
    report = ebl.Report()
    mounts = ebl.parse_mountinfo(_mountinfo_for(mount, "ext4"))
    ebl.check_hot_filesystems(_host_manifest(tmp_path, runtime=runtime, hot=link / "speechrl-data", status="cut-over"), mounts,
                              report, require_hot_mounted=True)
    assert report.failures == []
    assert any("[hot-mount]" in line and str(mount.resolve()) in line for line in report.passes)


def test_hot_root_on_the_root_filesystem_only_is_not_a_data_mount(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    hot = tmp_path / "hot"
    hot.mkdir()
    report = ebl.Report()
    mounts = ebl.parse_mountinfo("1 0 8:1 / / rw - ext4 /dev/sda rw\n")
    ebl.check_hot_filesystems(_host_manifest(tmp_path, runtime=runtime, hot=hot), mounts, report, require_hot_mounted=True)
    assert any("[hot-mount]" in f and "mount point=/" in f for f in report.failures)


def test_assets_sizes_and_promotion_receipt_hash(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    _write(Path(manifest["models"][0]["gguf"]["path"]), "12345")
    _write(Path(manifest["models"][0]["mmproj"]["path"]), "123")
    receipt = _write(Path(manifest["packet_roots"][0]["path"]) / "R-promotion.json", "{}\n")
    report = ebl.Report()
    ebl.check_assets(manifest, report)
    assert report.failures == []
    receipt.write_text('{"changed": true}\n', encoding="utf-8")
    _write(Path(manifest["models"][0]["mmproj"]["path"]), "1234")
    report = ebl.Report()
    ebl.check_assets(manifest, report)
    assert any("R-promotion.json hashes to" in f for f in report.failures)
    assert any("mmproj" in f and "4 bytes" in f for f in report.failures)


def test_manifest_errors_are_usage_errors(tmp_path: Path) -> None:
    repo = _tree(tmp_path)
    broken = copy.deepcopy(_manifest(tmp_path))
    del broken["serving_geometries"]
    _write(repo / ebl.MANIFEST_RELPATH, json.dumps(broken))
    with pytest.raises(ebl.ManifestError):
        _run(repo)
    assert ebl.main(["--repo-root", str(repo)]) == 2


def test_write_baseline_refuses_while_a_literal_remains_and_writes_the_empty_list_otherwise(tmp_path: Path) -> None:
    repo = _tree(tmp_path)
    _write(repo / "scripts/flights/batch/driver.sh", f"saea_data_root_init\nDATA={LEGACY}\n")
    assert ebl.main(["--repo-root", str(repo), "--write-baseline"]) == 1
    _write(repo / "scripts/flights/batch/driver.sh", 'source "$(dirname "$0")/../../lib/data_root.sh"\nsaea_data_root_init\n')
    assert ebl.main(["--repo-root", str(repo), "--write-baseline"]) == 0
    assert json.loads((repo / ebl.BASELINE_RELPATH).read_text(encoding="utf-8"))["legacy_literal_files"] == []


class _Usage:
    def __init__(self, free: int) -> None:
        self.free = free


def test_e_free_space_cap_refuses_under_500_gb() -> None:
    assert ebl.E_FREE_MIN_BYTES == 500 * 10**9
    low = ebl.Report()
    ebl.check_e_free_space(low, disk_usage=lambda path: _Usage(499 * 10**9))
    assert any("[e-free]" in f and "499 GB free" in f for f in low.failures)
    enough = ebl.Report()
    ebl.check_e_free_space(enough, disk_usage=lambda path: _Usage(500 * 10**9))
    assert enough.failures == [] and any("[e-free]" in line for line in enough.passes)


def test_e_free_space_warns_when_e_is_not_readable() -> None:
    def boom(path):
        raise FileNotFoundError(path)

    report = ebl.Report()
    ebl.check_e_free_space(report, disk_usage=boom)
    assert report.failures == [] and any("[e-free]" in w for w in report.warnings)
