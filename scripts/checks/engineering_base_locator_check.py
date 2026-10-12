#!/usr/bin/env python3
"""Engineering-base locator gate (owner directive 2026-10-12, decision 274; ruling 284).

The ONE declared base -- which model, which features, from which disk -- lives in
``configs/base/engineering-base-v1.json``; the data-root default lives in ONE line of
``scripts/lib/data_root.sh``. This gate keeps the two honest and keeps hot paths off 9p.

Repository rules (always; model-free, no data-root read, run anywhere):

* ``manifest``   the manifest parses and carries every required section.
* ``authority``  ``scripts/lib/data_root.sh`` assigns ``SAEA_DATA_ROOT_DEFAULT``,
                 ``SAEA_HOT_DATA_ROOT`` and ``SAEA_LEGACY_DATA_ROOT`` exactly once each, and they
                 equal ``roots.data_root.current`` / ``roots.hot.path`` / ``roots.legacy.path``;
                 ``status`` is ``pre-cut-over`` exactly when the current root is the legacy one.
* ``live``       every declared live script exists, carries no hard-coded legacy root, and
                 sources the authority (entries also call ``saea_data_root_init``).
* ``ratchet``    no file under ``scripts/ src/ configs/ tests/`` contains a hard-coded data-root path
                 (FAIL): the manifest's legacy root, ``/mnt/e/chao_workspace`` or any
                 ``/mnt/e/.../speechrl-data``. The sweep is complete (owner rulings 289 B / 290 B,
                 2026-10-12), so the frozen baseline (``engineering_base_locator_baseline.json``) must
                 stay EMPTY (FAIL otherwise). Configs spell the root ``${SAEA_DATA_ROOT}``
                 (``core/data_root_placeholder.py``), scripts source ``scripts/lib/data_root.sh``.
* ``models``     each model's runtime receipt pins the declared GGUF sha256 and build commit;
                 the umbrella lock entry (when readable) names both declared sha256 values.
* ``geometry``   each serving geometry's model fragment exists and agrees with the manifest
                 (lock key, -c, -np, max_tokens, packet root, decoder sha); the serving_lib
                 geometry table names the same session and fragment per target.

Host rules (``--host``; WSL only; light reads: mountinfo, stat, a few small-file hashes):

* ``hot-fs``     every declared hot path resolves to a mounted ext4 (9p, drvfs, tmpfs, fuse
                 refused); the legacy data root is accepted with a WARN while
                 ``status == pre-cut-over``.
* ``hot-mount``  the hot root exists on a mounted ext4 other than the root filesystem (the mount
                 point itself or a directory inside it, decision 296) (FAIL after cut-over or with
                 ``--require-hot-mounted``; WARN before).
* ``e-free``     the E: drive (``/mnt/e``) has at least 500 GB free (decision 291: disk 1 grows to 3.6 TB
                 inside E:, so the VHDX can only grow while E: keeps headroom); FAIL below the cap,
                 WARN when E: is not readable on this host.
* ``assets``     each model file exists with the declared size (no GGUF re-hash); each packet
                 root exists; each named promotion receipt hashes to its pin.

Exit 0 on PASS (warnings allowed), 1 on any FAIL, 2 on a usage or manifest error.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Mapping, Sequence

MANIFEST_RELPATH = "configs/base/engineering-base-v1.json"
AUTHORITY_RELPATH = "scripts/lib/data_root.sh"
BASELINE_RELPATH = "scripts/checks/engineering_base_locator_baseline.json"
SERVING_LIB_RELPATH = "scripts/flights/batch/serving_lib.sh"
SCHEMA = "saea-engineering-base-v1"
RATCHET_DIRS = ("scripts", "src", "configs", "tests")
RATCHET_SUFFIXES = (".sh", ".py", ".json", ".ps1", ".md", ".txt", ".yaml", ".yml", ".toml")
E_DRIVE_PATH = "/mnt/e"
E_FREE_MIN_BYTES = 500 * 1000**3  # decision 291: refuse when E: free space drops under 500 GB
GENERIC_DATA_ROOT_PATTERNS = (r"/mnt/e/chao_workspace", r"/mnt/e/[^\s\"']*speechrl-data")
REFUSED_FSTYPES = frozenset({"9p", "v9fs", "drvfs", "tmpfs", "fuse", "fuseblk", "overlay", "cifs", "nfs"})
REQUIRED_SECTIONS = ("roots", "hot_paths", "migration", "models", "packet_roots", "serving_geometries", "live_scripts", "timing_budget")
AUTHORITY_VARIABLES = {
    "SAEA_DATA_ROOT_DEFAULT": ("data_root", "current"),
    "SAEA_HOT_DATA_ROOT": ("hot", "path"),
    "SAEA_LEGACY_DATA_ROOT": ("legacy", "path"),
}


class ManifestError(RuntimeError):
    pass


@dataclass
class Report:
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    passes: list[str] = field(default_factory=list)

    def fail(self, rule: str, message: str) -> None:
        self.failures.append(f"[{rule}] {message}")

    def warn(self, rule: str, message: str) -> None:
        self.warnings.append(f"[{rule}] {message}")

    def ok(self, rule: str, message: str) -> None:
        self.passes.append(f"[{rule}] {message}")


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------


def load_manifest(path: Path) -> dict:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ManifestError(f"cannot read manifest {path}: {error}") from error
    if not isinstance(document, dict) or document.get("schema") != SCHEMA:
        raise ManifestError(f"manifest {path} is not a {SCHEMA} document")
    missing = [key for key in REQUIRED_SECTIONS if key not in document]
    if missing:
        raise ManifestError(f"manifest {path} lacks section(s): {', '.join(missing)}")
    roots = document["roots"]
    for key in ("data_root", "legacy", "hot"):
        if not isinstance(roots.get(key), Mapping):
            raise ManifestError(f"manifest roots.{key} is missing")
    if not isinstance(roots["data_root"].get("current"), str) or roots["data_root"].get("status") not in ("pre-cut-over", "cut-over"):
        raise ManifestError("manifest roots.data_root needs a string current and status pre-cut-over|cut-over")
    for key in document["hot_paths"]:
        if key not in roots:
            raise ManifestError(f"manifest hot_paths names unknown root {key!r}")
    return document


def root_path(manifest: Mapping, key: str) -> str:
    entry = manifest["roots"][key]
    return entry["current"] if key == "data_root" else entry["path"]


def legacy_literal(manifest: Mapping) -> str:
    return manifest["roots"]["legacy"]["path"]


# ---------------------------------------------------------------------------
# Repository rules
# ---------------------------------------------------------------------------


def check_authority(repo: Path, manifest: Mapping, report: Report) -> None:
    path = repo / AUTHORITY_RELPATH
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        report.fail("authority", f"cannot read {AUTHORITY_RELPATH}: {error}")
        return
    for variable, (root, key) in AUTHORITY_VARIABLES.items():
        values = re.findall(rf"^{variable}=(\S+)\s*$", text, re.M)
        if len(values) != 1:
            report.fail("authority", f"{AUTHORITY_RELPATH} must assign {variable} exactly once (found {len(values)})")
            continue
        expected = manifest["roots"][root][key]
        if values[0] != expected:
            report.fail("authority", f"{variable}={values[0]} but the manifest roots.{root}.{key} is {expected}")
    current = manifest["roots"]["data_root"]["current"]
    status = manifest["roots"]["data_root"]["status"]
    legacy = manifest["roots"]["legacy"]["path"]
    hot = manifest["roots"]["hot"]["path"]
    if status == "pre-cut-over" and current != legacy:
        report.fail("authority", f"status pre-cut-over but the current data root {current} is not the legacy root")
    if status == "cut-over" and current != hot:
        report.fail("authority", f"status cut-over but the current data root {current} is not the hot root {hot}")
    if not report.failures:
        report.ok("authority", f"data root {current} ({status}); hot root {hot}")


def check_live_scripts(repo: Path, manifest: Mapping, report: Report) -> None:
    literal = legacy_literal(manifest)
    bad = 0
    for entry in manifest["live_scripts"]:
        rel, role = entry.get("path"), entry.get("role")
        path = repo / str(rel)
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            report.fail("live", f"{rel}: declared live script is missing")
            bad += 1
            continue
        if literal in text and role not in ("tool",):
            report.fail("live", f"{rel}: hard-codes the legacy data root (use $SAEA_DATA_ROOT from {AUTHORITY_RELPATH})")
            bad += 1
        if role in ("entry", "library") and "lib/data_root.sh" not in text:
            report.fail("live", f"{rel}: does not source {AUTHORITY_RELPATH}")
            bad += 1
        if role == "entry" and "saea_data_root_init" not in text:
            report.fail("live", f"{rel}: entry script never calls saea_data_root_init (the mount and split-brain guard)")
            bad += 1
        if role == "python" and "data_root.sh" not in text:
            report.fail("live", f"{rel}: python tool does not derive its default from {AUTHORITY_RELPATH}")
            bad += 1
    if not bad:
        report.ok("live", f"{len(manifest['live_scripts'])} live script(s) read the one authority")


def forbidden_pattern(literal: str) -> "re.Pattern[bytes]":
    parts = [re.escape(literal)] + list(GENERIC_DATA_ROOT_PATTERNS)
    return re.compile("|".join(parts).encode("utf-8"))


def literal_offenders(repo: Path, literal: str, skip: Iterable[str] = ()) -> list[str]:
    skipped = set(skip)
    offenders: list[str] = []
    pattern = forbidden_pattern(literal)
    for top in RATCHET_DIRS:
        base = repo / top
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix not in RATCHET_SUFFIXES or "__pycache__" in path.parts:
                continue
            rel = path.relative_to(repo).as_posix()
            if rel in skipped:
                continue
            try:
                if pattern.search(path.read_bytes()):
                    offenders.append(rel)
            except OSError:
                continue
    return sorted(offenders)


def ratchet_exempt(manifest: Mapping) -> set[str]:
    # The authority, the manifest, this gate's own baseline and the migration tool must name the
    # legacy root; the live-script rule polices the tool separately.
    exempt = {AUTHORITY_RELPATH, MANIFEST_RELPATH, BASELINE_RELPATH, "scripts/checks/engineering_base_locator_check.py"}
    exempt.update(str(e["path"]) for e in manifest["live_scripts"] if e.get("role") == "tool")
    return exempt


def load_baseline(path: Path) -> set[str]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ManifestError(f"cannot read ratchet baseline {path}: {error}") from error
    files = document.get("legacy_literal_files")
    if not isinstance(files, list) or not all(isinstance(f, str) for f in files):
        raise ManifestError(f"ratchet baseline {path} lacks a legacy_literal_files list")
    return set(files)


def check_ratchet(repo: Path, manifest: Mapping, baseline: set[str], report: Report) -> list[str]:
    offenders = literal_offenders(repo, legacy_literal(manifest), ratchet_exempt(manifest))
    for rel in offenders:
        report.fail("ratchet", f"{rel}: hard-coded data-root path (config: ${{SAEA_DATA_ROOT}}; script: source {AUTHORITY_RELPATH}; python: SAEA_DATA_ROOT)")
    if baseline:
        report.fail("ratchet", f"the frozen baseline must be empty (sweep complete); it still lists {len(baseline)} file(s), first: {sorted(baseline)[0]}")
    if not offenders and not baseline:
        report.ok("ratchet", "no hard-coded data-root path under scripts/ src/ configs/ tests/; baseline empty")
    return offenders


def _read_json(path: Path) -> Mapping | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, Mapping) else None


def check_models(repo: Path, manifest: Mapping, report: Report, *, umbrella_lock: Path | None) -> None:
    lock_entries: dict[str, str] = {}
    if umbrella_lock is not None:
        lock = _read_json(umbrella_lock)
        if lock is None:
            report.warn("models", f"umbrella lock {umbrella_lock} is not readable; lock cross-check skipped")
        else:
            for entry in lock.get("models", []) or []:
                if isinstance(entry, Mapping) and isinstance(entry.get("name"), str):
                    lock_entries[entry["name"]] = json.dumps(entry, sort_keys=True)
    bad = 0
    for model in manifest["models"]:
        core = model.get("core")
        receipt = _read_json(repo / str(model.get("runtime_receipt")))
        if receipt is None:
            report.fail("models", f"{core}: runtime receipt {model.get('runtime_receipt')} is missing or not JSON")
            bad += 1
            continue
        pinned = {str(f.get("sha256")) for f in receipt.get("gguf_files", []) if isinstance(f, Mapping)}
        if model["gguf"]["sha256"] not in pinned:
            report.fail("models", f"{core}: runtime receipt does not pin the declared GGUF sha256 {model['gguf']['sha256'][:12]}")
            bad += 1
        commit = (receipt.get("llama_cpp") or {}).get("build_commit")
        if commit != model.get("llama_cpp_build_commit"):
            report.fail("models", f"{core}: runtime receipt build commit {commit} != declared {model.get('llama_cpp_build_commit')}")
            bad += 1
        if receipt.get("model_lock_key") not in (None, model.get("lock_key")):
            report.fail("models", f"{core}: runtime receipt lock key {receipt.get('model_lock_key')} != {model.get('lock_key')}")
            bad += 1
        if lock_entries:
            text = lock_entries.get(str(model.get("lock_key")))
            if text is None:
                report.fail("models", f"{core}: umbrella lock has no model entry {model.get('lock_key')}")
                bad += 1
            else:
                for part in ("gguf", "mmproj"):
                    if model[part]["sha256"] not in text:
                        report.fail("models", f"{core}: umbrella lock entry {model.get('lock_key')} does not name the {part} sha256")
                        bad += 1
    if not bad:
        report.ok("models", f"{len(manifest['models'])} core(s) agree with their runtime receipts{' and the umbrella lock' if lock_entries else ''}")


def _arg_after(args: Sequence[str], flag: str) -> str | None:
    for i, value in enumerate(args[:-1]):
        if value == flag:
            return args[i + 1]
    return None


def serving_lib_table(text: str) -> dict[str, tuple[str, str]]:
    table: dict[str, tuple[str, str]] = {}
    for match in re.finditer(r"^\s{4}([a-z0-9-]+)\)\n(.*?);;", text, re.M | re.S):
        body = match.group(2)
        sid = re.search(r"G_SID=(\S+)", body)
        fragment = re.search(r"G_FRAGMENT=(\S+)", body)
        if sid and fragment:
            table[match.group(1)] = (sid.group(1), fragment.group(1))
    return table


def check_geometry(repo: Path, manifest: Mapping, report: Report) -> None:
    models = {m["core"]: m for m in manifest["models"]}
    packets = {p["id"]: p for p in manifest["packet_roots"]}
    try:
        table = serving_lib_table((repo / SERVING_LIB_RELPATH).read_text(encoding="utf-8"))
    except OSError:
        table = {}
        report.fail("geometry", f"cannot read {SERVING_LIB_RELPATH}")
    bad = 0
    for geometry in manifest["serving_geometries"]:
        target = geometry["target"]
        fragment = _read_json(repo / "configs" / "model" / f"{geometry['model_fragment']}.json")
        if fragment is None:
            report.fail("geometry", f"{target}: model fragment {geometry['model_fragment']} is missing")
            bad += 1
            continue
        model = models.get(geometry["core"])
        packet = packets.get(geometry["packet_root"])
        problems: list[str] = []
        if model is None:
            problems.append(f"unknown core {geometry['core']}")
        elif fragment.get("model_lock_key") != model["lock_key"]:
            problems.append(f"lock key {fragment.get('model_lock_key')} != {model['lock_key']}")
        args = [str(a) for a in fragment.get("server_args", [])]
        if _arg_after(args, "-c") != str(geometry["ctx"]):
            problems.append(f"-c {_arg_after(args, '-c')} != {geometry['ctx']}")
        if _arg_after(args, "-np") != str(geometry["slots"]):
            problems.append(f"-np {_arg_after(args, '-np')} != {geometry['slots']}")
        if (fragment.get("decoding_params") or {}).get("max_tokens") != geometry["max_tokens"]:
            problems.append(f"max_tokens {(fragment.get('decoding_params') or {}).get('max_tokens')} != {geometry['max_tokens']}")
        if packet is None:
            problems.append(f"unknown packet root {geometry['packet_root']}")
        elif fragment.get("speech_feature_root") != packet["path"]:
            problems.append(f"speech_feature_root {fragment.get('speech_feature_root')} != {packet['path']}")
        env = fragment.get("server_env") or {}
        if model is not None and env.get("LLAMA_SPEECH_DECODER_SHA256") not in (None, model["gguf"]["sha256"]):
            problems.append("LLAMA_SPEECH_DECODER_SHA256 is not the declared GGUF sha256")
        row = table.get(target)
        if table and row is None:
            problems.append(f"{SERVING_LIB_RELPATH} has no geometry row {target}")
        elif row is not None and row != (geometry["session_id"], geometry["model_fragment"]):
            problems.append(f"{SERVING_LIB_RELPATH} row {target} = {row}, manifest = {(geometry['session_id'], geometry['model_fragment'])}")
        for problem in problems:
            report.fail("geometry", f"{target}: {problem}")
        bad += bool(problems)
    if not bad:
        report.ok("geometry", f"{len(manifest['serving_geometries'])} serving geometr(ies) agree with fragments and serving_lib")


# ---------------------------------------------------------------------------
# Host rules
# ---------------------------------------------------------------------------


def _unescape_mount(path: str) -> str:
    return re.sub(r"\\([0-7]{3})", lambda m: chr(int(m.group(1), 8)), path)


def parse_mountinfo(text: str) -> list[tuple[str, str]]:
    """``[(mount point, fstype)]`` from /proc/self/mountinfo text."""

    mounts: list[tuple[str, str]] = []
    for line in text.splitlines():
        left, sep, right = line.partition(" - ")
        if not sep:
            continue
        fields = left.split()
        tail = right.split()
        if len(fields) >= 5 and tail:
            mounts.append((_unescape_mount(fields[4]), tail[0]))
    return mounts


def mount_of(path: str, mounts: Sequence[tuple[str, str]]) -> tuple[str, str] | None:
    """``(mount point, fstype)`` of the longest mount point that prefixes ``path`` (already resolved)."""

    best: tuple[str, str] | None = None
    for point, fstype in mounts:
        prefix = point.rstrip("/") + "/"
        if path == point or path.startswith(prefix) or point == "/":
            if best is None or len(point) > len(best[0]):
                best = (point, fstype)
    return best


def fstype_of(path: str, mounts: Sequence[tuple[str, str]]) -> str | None:
    """The fstype of the longest mount point that prefixes ``path`` (already resolved)."""

    found = mount_of(path, mounts)
    return None if found is None else found[1]


def check_hot_filesystems(manifest: Mapping, mounts: Sequence[tuple[str, str]], report: Report, *, require_hot_mounted: bool) -> None:
    status = manifest["roots"]["data_root"]["status"]
    legacy = manifest["roots"]["legacy"]["path"]
    bad = 0
    for key in manifest["hot_paths"]:
        declared = root_path(manifest, key)
        if key == "data_root" and declared == legacy and status == "pre-cut-over":
            report.warn("hot-fs", f"data root {declared} is the 9p E: original (pre-cut-over; decision 284 moves it to {manifest['roots']['hot']['path']})")
            continue
        resolved = os.path.realpath(declared)
        if not os.path.isdir(resolved):
            report.fail("hot-fs", f"{key}: {declared} does not exist on this host")
            bad += 1
            continue
        fstype = fstype_of(resolved, mounts)
        if fstype != "ext4":
            report.fail("hot-fs", f"{key}: {declared} resolves to {resolved} on '{fstype}', not ext4")
            bad += 1
    hot = manifest["roots"]["hot"]["path"]
    resolved_hot = os.path.realpath(hot)
    found = mount_of(resolved_hot, mounts) if os.path.isdir(resolved_hot) else None
    hot_fs = None if found is None else found[1]
    # Decision 296: the hot root is a directory INSIDE the disk-1 mount (/mnt/wsl/saea-data-1/speechrl-data), so the rule is
    # "on a mounted ext4 other than the root filesystem" -- an unmounted VHDX leaves the path absent or on the /mnt/wsl tmpfs.
    mount_point = None if found is None else found[0]
    on_data_mount = hot_fs == "ext4" and mount_point not in (None, "/")
    if on_data_mount:
        report.ok("hot-mount", f"hot root {hot} -> {resolved_hot} is on the mounted ext4 {mount_point}")
    else:
        message = (f"hot root {hot} -> {resolved_hot} is not on a mounted ext4 data disk "
                   f"(exists={os.path.isdir(resolved_hot)}, fstype={hot_fs}, mount point={mount_point})")
        if status == "cut-over" or require_hot_mounted:
            report.fail("hot-mount", message)
            bad += 1
        else:
            report.warn("hot-mount", message)
    if not bad:
        report.ok("hot-fs", f"{len(manifest['hot_paths'])} hot path(s) on ext4 (legacy data root excepted pre-cut-over)")


def check_e_free_space(report: Report, *, path: str = E_DRIVE_PATH, minimum: int = E_FREE_MIN_BYTES, disk_usage=shutil.disk_usage) -> None:
    """Decision 291: E: keeps at least ``minimum`` bytes (500 GB) free; the 3.6 TB VHDX grows inside it."""

    try:
        free = int(disk_usage(path).free)
    except (OSError, ValueError):
        report.warn("e-free", f"{path} is not readable on this host; the E: free-space cap (>= {minimum // 10**9} GB) was not measured")
        return
    if free < minimum:
        report.fail("e-free", f"{path} has {free / 10**9:.0f} GB free, under the {minimum // 10**9} GB cap (decision 291): free E: before growing the VHDX or writing there")
    else:
        report.ok("e-free", f"{path} has {free / 10**9:.0f} GB free (cap >= {minimum // 10**9} GB)")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def check_assets(manifest: Mapping, report: Report) -> None:
    bad = 0
    for model in manifest["models"]:
        for part in ("gguf", "mmproj"):
            path = Path(model[part]["path"])
            try:
                size = path.stat().st_size
            except OSError:
                report.fail("assets", f"{model['core']} {part}: {path} is missing")
                bad += 1
                continue
            if size != model[part]["size_bytes"]:
                report.fail("assets", f"{model['core']} {part}: {path} is {size} bytes, declared {model[part]['size_bytes']}")
                bad += 1
    for packet in manifest["packet_roots"]:
        root = Path(packet["path"])
        if not root.is_dir():
            report.fail("assets", f"packet root {packet['id']}: {root} is missing")
            bad += 1
            continue
        for receipt in packet.get("promotion_receipts", []):
            path = root / receipt["name"]
            try:
                measured = _sha256(path)
            except OSError:
                report.fail("assets", f"packet root {packet['id']}: promotion receipt {receipt['name']} is missing")
                bad += 1
                continue
            if measured != receipt["sha256"]:
                report.fail("assets", f"packet root {packet['id']}: {receipt['name']} hashes to {measured[:12]}, pinned {receipt['sha256'][:12]}")
                bad += 1
    if not bad:
        report.ok("assets", "model files present at their declared sizes; packet roots and promotion receipts verified")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def run(
    repo: Path,
    *,
    manifest_path: Path | None = None,
    baseline_path: Path | None = None,
    umbrella_lock: Path | None = None,
    host: bool = False,
    mountinfo_text: str | None = None,
    require_hot_mounted: bool = False,
    e_path: str = E_DRIVE_PATH,
    e_free_min_gb: float = E_FREE_MIN_BYTES / 10**9,
) -> Report:
    report = Report()
    manifest = load_manifest(manifest_path or repo / MANIFEST_RELPATH)
    baseline = load_baseline(baseline_path or repo / BASELINE_RELPATH)
    check_authority(repo, manifest, report)
    check_live_scripts(repo, manifest, report)
    check_ratchet(repo, manifest, baseline, report)
    check_models(repo, manifest, report, umbrella_lock=umbrella_lock)
    check_geometry(repo, manifest, report)
    if host:
        if mountinfo_text is None:
            mountinfo_text = Path("/proc/self/mountinfo").read_text(encoding="utf-8")
        mounts = parse_mountinfo(mountinfo_text)
        check_hot_filesystems(manifest, mounts, report, require_hot_mounted=require_hot_mounted)
        check_e_free_space(report, path=e_path, minimum=int(e_free_min_gb * 10**9))
        check_assets(manifest, report)
    return report


def write_baseline(repo: Path, manifest_path: Path | None, baseline_path: Path | None) -> int:
    """The baseline is retired: this only (re)writes the EMPTY list, and refuses while any file carries a literal."""

    manifest = load_manifest(manifest_path or repo / MANIFEST_RELPATH)
    offenders = literal_offenders(repo, legacy_literal(manifest), ratchet_exempt(manifest))
    if offenders:
        print(f"engineering base locator check: refusing to baseline {len(offenders)} file(s) with a hard-coded data-root path "
              f"(first: {offenders[0]}); the baseline stays empty, fix the files", file=sys.stderr)
        return 1
    target = baseline_path or repo / BASELINE_RELPATH
    target.write_text(json.dumps({
        "schema": "saea-engineering-base-locator-baseline-v1",
        "literal": legacy_literal(manifest),
        "note": "RETIRED and empty (owner rulings 289 B / 290 B, 2026-10-12): no file may name the data root by absolute path. "
                "The ratchet refuses every hard-coded data-root path and refuses a non-empty list here.",
        "legacy_literal_files": [],
    }, indent=1) + "\n", encoding="utf-8")
    print(f"engineering base locator check: wrote the empty baseline to {target}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--umbrella-lock", type=Path, help="default: <repo>/../../docs/datasets.lock.json when present")
    parser.add_argument("--host", action="store_true", help="also check this host's filesystems and assets (WSL)")
    parser.add_argument("--require-hot-mounted", action="store_true", help="FAIL (not WARN) when the hot root is not a mounted ext4")
    parser.add_argument("--e-path", default=E_DRIVE_PATH, help="mount point of the E: drive (host mode)")
    parser.add_argument("--e-free-min-gb", type=float, default=E_FREE_MIN_BYTES / 10**9, help="E: free-space cap in GB (host mode)")
    parser.add_argument("--write-baseline", action="store_true", help="rewrite the (empty) retired baseline; refused while a literal remains")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    repo = args.repo_root.resolve()
    try:
        if args.write_baseline:
            return write_baseline(repo, args.manifest, args.baseline)
        lock = args.umbrella_lock
        if lock is None:
            candidate = repo.parent.parent / "docs" / "datasets.lock.json"
            lock = candidate if candidate.is_file() else None
        report = run(repo, manifest_path=args.manifest, baseline_path=args.baseline, umbrella_lock=lock,
                     host=args.host, require_hot_mounted=args.require_hot_mounted,
                     e_path=args.e_path, e_free_min_gb=args.e_free_min_gb)
    except ManifestError as error:
        print(f"engineering base locator check: FAIL: {error}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps({"failures": report.failures, "warnings": report.warnings, "passes": report.passes}, indent=2))
    else:
        for line in report.passes:
            print(f"PASS {line}")
        for line in report.warnings:
            print(f"WARN {line}")
        for line in report.failures:
            print(f"FAIL {line}")
    verdict = "FAIL" if report.failures else "PASS"
    print(f"engineering base locator check: {verdict} ({len(report.failures)} failure(s), {len(report.warnings)} warning(s), "
          f"{'host' if args.host else 'repository'} mode)")
    return 1 if report.failures else 0


if __name__ == "__main__":
    sys.exit(main())
