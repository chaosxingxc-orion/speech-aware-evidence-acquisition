"""Owned filler hold in scripts/flights/batch/queue_lib.sh (coordinator fix after the 2026-09-30 hold race).

queue_a2.sh took the filler hold, and its predecessor queue_next.sh's release step removed it 28 s later with
``rm -f``. The hold is now owned: ``ql_hold_take`` / ``ql_hold_release`` / ``ql_hold_owner``, and a predecessor's
release never removes a successor's hold. ``ql_seg_line`` replaces the bare grep that matched a queue's own
preamble line.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
BATCH = REPO / "scripts" / "flights" / "batch"
QUEUE_LIB = BATCH / "queue_lib.sh"
FILLER = REPO / "scripts" / "flights" / "filler" / "filler_queue.sh"

pytestmark = pytest.mark.skipif(shutil.which("bash") is None or shutil.which("awk") is None, reason="needs bash + awk")


def _env(tmp_path: Path) -> dict[str, str]:
    env = dict(os.environ)
    env.update(
        QL_HOLD=str(tmp_path / "filler.hold"),
        QL_LOG=str(tmp_path / "queue.out"),
        SAEA_RUNTIME_ROOT=str(tmp_path),
    )
    return env


def _ql(tmp_path: Path, body: str) -> subprocess.CompletedProcess[str]:
    script = f'source "{QUEUE_LIB}"\n{body}\n'
    return subprocess.run(["bash", "-c", script], env=_env(tmp_path), capture_output=True, text=True, check=False)


def _last_rc(proc: subprocess.CompletedProcess[str]) -> str:
    lines = [line for line in proc.stdout.splitlines() if line.startswith("RC=")]
    assert lines, (proc.stdout, proc.stderr)
    return lines[-1][3:]


def _call(tmp_path: Path, call: str) -> int:
    return int(_last_rc(_ql(tmp_path, f"{call}; echo \"RC=$?\"")))


def _owner(tmp_path: Path) -> str | None:
    proc = _ql(tmp_path, 'o=$(ql_hold_owner) && echo "OWNER=$o" || echo "NOHOLD"')
    out = proc.stdout.strip().splitlines()[-1]
    return None if out == "NOHOLD" else out.removeprefix("OWNER=")


def _log(tmp_path: Path) -> str:
    path = tmp_path / "queue.out"
    return path.read_text(encoding="utf-8") if path.exists() else ""


def test_take_writes_owner_token_and_utc_time(tmp_path: Path) -> None:
    assert _call(tmp_path, "ql_hold_take queue_a2") == 0
    words = (tmp_path / "filler.hold").read_text(encoding="utf-8").split()
    assert words[0] == "queue_a2"
    assert words[1].endswith("Z") and "T" in words[1]
    assert _owner(tmp_path) == "queue_a2"
    assert "filler hold taken by queue_a2" in _log(tmp_path)
    assert _call(tmp_path, "ql_hold_take queue_a2") == 0  # idempotent for its own owner
    assert "filler hold already ours (queue_a2)" in _log(tmp_path)


def test_take_refuses_another_owners_hold_without_overwriting(tmp_path: Path) -> None:
    assert _call(tmp_path, "ql_hold_take coordinator") == 0
    before = (tmp_path / "filler.hold").read_text(encoding="utf-8")
    assert _call(tmp_path, "ql_hold_take queue_e5") == 1
    assert (tmp_path / "filler.hold").read_text(encoding="utf-8") == before
    assert "hold already held by coordinator" in _log(tmp_path)
    # naming the wrong predecessor does not hand it over either
    assert _call(tmp_path, "ql_hold_take queue_e5 queue_a2") == 1
    assert _owner(tmp_path) == "coordinator"


def test_release_only_by_owner(tmp_path: Path) -> None:
    assert _call(tmp_path, "ql_hold_take queue_a2") == 0
    assert _call(tmp_path, "ql_hold_release queue_next") == 3
    assert (tmp_path / "filler.hold").exists()
    assert "hold owned by queue_a2; not released" in _log(tmp_path)
    assert _call(tmp_path, "ql_hold_release queue_a2") == 0
    assert not (tmp_path / "filler.hold").exists()
    assert "filler hold removed (owner queue_a2)" in _log(tmp_path)
    assert _owner(tmp_path) is None
    assert _call(tmp_path, "ql_hold_release queue_a2") == 0  # nothing to release
    assert "no filler hold to release (queue_a2)" in _log(tmp_path)


def test_successor_takes_over_before_predecessor_release(tmp_path: Path) -> None:
    """The 2026-09-30 sequence, owned: the predecessor's release must leave the successor's hold in place."""
    assert _call(tmp_path, "ql_hold_take queue_next") == 0
    assert _call(tmp_path, "ql_hold_take queue_a2 queue_next") == 0
    assert _owner(tmp_path) == "queue_a2"
    assert "filler hold handed over from queue_next to queue_a2" in _log(tmp_path)
    assert _call(tmp_path, "ql_hold_release queue_next") == 3
    assert _owner(tmp_path) == "queue_a2"
    assert _call(tmp_path, "ql_hold_release queue_a2") == 0
    assert _owner(tmp_path) is None


def test_legacy_touch_hold_is_adopted_only_when_named(tmp_path: Path) -> None:
    (tmp_path / "filler.hold").write_text("", encoding="utf-8")
    assert _owner(tmp_path) == "legacy"
    assert _call(tmp_path, "ql_hold_take queue_e5") == 1
    assert _call(tmp_path, "ql_hold_take queue_e5 legacy") == 0
    assert _owner(tmp_path) == "queue_e5"


@pytest.mark.parametrize("call", ["ql_hold_take ''", "ql_hold_take 'a b'", "ql_hold_take legacy", "ql_hold_release 'x/y'"])
def test_bad_tokens_are_refused(tmp_path: Path, call: str) -> None:
    assert _call(tmp_path, call) == 2
    assert not (tmp_path / "filler.hold").exists()


def test_seg_line_ignores_quoted_phrases_and_earlier_runs(tmp_path: Path) -> None:
    log = tmp_path / "queue-next.out"
    log.write_text(
        "2026-09-29T10:00:00Z queue start (queue_next.sh)\n"
        "2026-09-29T10:00:01Z filler hold removed\n"
        "2026-09-29T18:47:31Z queue start (queue_next.sh)\n"
        "2026-09-29T18:47:31Z flight commits ...; requiring 'SEALONLY-E4 DONE' and 'filler hold removed' in x\n"
        "2026-09-30T01:59:15Z NEXT DONE 2026-09-30T01:59:15Z\n",
        encoding="utf-8",
    )
    seg = f'ql_seg_line "{log}" queue_next.sh'
    assert _call(tmp_path, f'{seg} "NEXT DONE"') == 0
    assert _call(tmp_path, f'{seg} "filler hold removed"') == 1  # preamble quote and the earlier run do not count
    with log.open("a", encoding="utf-8") as fh:
        fh.write("2026-09-30T02:00:16Z filler hold removed\n")
    assert _call(tmp_path, f'{seg} "filler hold removed"') == 0
    assert _call(tmp_path, f'ql_seg_line "{tmp_path / "missing.out"}" queue_next.sh "NEXT DONE"') != 0


def test_filler_held_line_names_the_owner(tmp_path: Path) -> None:
    hold = tmp_path / "filler.hold"
    hold.write_text("queue_e5 2026-09-30T05:00:00Z\n", encoding="utf-8")
    env = dict(os.environ, FILLER_HOLD=str(hold), FILLER_HOME=str(tmp_path), FILLER_QUEUE_LOG=str(tmp_path / "f.out"),
               FILLER_STATE=str(tmp_path / "state.jsonl"))
    proc = subprocess.run(["bash", str(FILLER), "--dry-run", "--once"], env=env, capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "filler held"
    assert "owner queue_e5 since 2026-09-30T05:00:00Z" in (tmp_path / "f.out").read_text(encoding="utf-8")
    hold.write_text("", encoding="utf-8")
    subprocess.run(["bash", str(FILLER), "--dry-run", "--once"], env=env, capture_output=True, text=True, check=False)
    assert "owner legacy" in (tmp_path / "f.out").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "relpath",
    [
        "scripts/flights/batch/queue_lib.sh",
        "scripts/flights/batch/queue_successor_template.sh",
        "scripts/flights/rankvis/queue_rankvis.sh",
        "scripts/flights/filler/filler_queue.sh",
    ],
)
def test_touched_scripts_parse(relpath: str) -> None:
    proc = subprocess.run(["bash", "-n", str(REPO / relpath)], capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr
