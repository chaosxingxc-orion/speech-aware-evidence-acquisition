#!/usr/bin/env python3
"""One-command package launch (efficiency measure M7). Model-free; contacts no model, server, scorer or GPU itself.

    package_launch.sh <spec.json> [--from STEP] [--until STEP] [--dry-run] [--root-countersign] [--redo STEP ...]

Steps, in order: derive, write, countersign, mint, commit, flip, chain (default stop), read (post-seal; only with --until read / --from read).
Every step is idempotent (a step with an ok receipt of this launch id is skipped, ``--redo`` re-runs it), logged to the spec's log
(default /home/chao/<short>-launch.out) and receipted in ``launch-steps.jsonl`` (default /home/chao/<short>-launch/launch-steps.jsonl).
The runner fails closed at the first non-zero step. Rules enforced before acting:

  * the master tree is clean (``git status --porcelain`` empty) before derive, flip, chain;
  * no merge / rebase / cherry-pick is in progress before any acting step;
  * no batch driver, flight, lease, re-pin or flip process and no flight.lock before flip and chain;
  * the flip's gate block is parsed: one ``check: PASS`` per cell, no FAIL / REFUSED, FLIP_CHAIN_DONE, master verified at HEAD;
  * the flight-commit file equals master HEAD before the chain starts;
  * the countersign step runs only with --root-countersign (it is the coordinator's act; the script performs the text
    replacement and stamps the UTC).

Exit codes: 0 done, 1 a step failed, 2 a rule refused / usage, 3 countersign without --root-countersign.
Env hooks (tests): PACKAGE_LAUNCH_ALIVE_CMD (shell command printing the alive processes), SAEA_POWERSHELL, SAEA_TASK_PS1_WIN.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SPEC_SCHEMA = "saea-package-launch-spec-v1"
RECEIPT_SCHEMA = "saea-launch-step-receipt-v1"
STEPS = ["derive", "write", "countersign", "mint", "commit", "flip", "chain", "read"]
DEFAULT_UNTIL = "chain"
CLEAN_BEFORE = {"derive", "flip", "chain"}
ALIVE_BEFORE = {"flip", "chain"}
ALIVE_PATTERN = (r"batch_driver\.sh|core\.flight\.cli|lease_cli|repin_loop_generic\.sh|repin_cell\.py|repin_package_one_pass\.py|"
                 r"scripts/flights/[a-z0-9_/]*(_flip|flip_all|flip_both)[a-z0-9_]*\.sh")
DEFAULT_PS1_WIN = (r"D:\chao_workspace\exploring-l4-intelligence\studies\speech-aware-evidence-acquisition"
                   r"\scripts\flights\batch\saea_task.ps1")
DRAFT_SCOPE_PREFIX = "DRAFT -- REGISTERED. "


class Refusal(Exception):
    """A rule refused: nothing was run."""


class StepFailed(Exception):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Launch:
    def __init__(self, spec: dict, repo: Path, *, dry: bool, root_countersign: bool, redo: set[str]):
        if spec.get("schema") != SPEC_SCHEMA:
            raise Refusal(f"spec schema must be {SPEC_SCHEMA}")
        for key in ("short", "package", "readiness_dir", "launch_id", "steps"):
            if key not in spec:
                raise Refusal(f"spec lacks {key!r}")
        self.spec, self.repo, self.dry, self.root_countersign, self.redo = spec, repo, dry, root_countersign, redo
        short = spec["short"]
        self.log_path = Path(spec.get("log") or f"/home/chao/{short}-launch.out")
        self.receipts_path = Path(spec.get("receipts") or f"/home/chao/{short}-launch/launch-steps.jsonl")
        self.data_root = Path(spec.get("data_root") or os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "/nonexistent-data-root")

    # -- plumbing ----------------------------------------------------------
    def say(self, text: str) -> None:
        line = f"{utc_now()} {text}"
        print(line)
        if not self.dry:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(line + "\n")

    def git(self, *args: str, check: bool = True) -> str:
        done = subprocess.run(["git", "-C", str(self.repo), *args], capture_output=True, text=True, encoding="utf-8")
        if check and done.returncode != 0:
            raise StepFailed(f"git {' '.join(args)} failed: {done.stderr.strip()[:300]}")
        return done.stdout

    def head(self) -> str:
        return self.git("rev-parse", "HEAD").strip()

    def render(self, text: str) -> str:
        return (text.replace("{head}", self.head()).replace("{utc}", utc_now()).replace("{package}", self.spec["package"])
                .replace("{readiness_dir}", self.spec["readiness_dir"]).replace("{repo}", str(self.repo)))

    def run_cmd(self, cmd: str, env_extra: dict | None = None) -> tuple[int, str]:
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", **(env_extra or {}))
        done = subprocess.run(["bash", "-c", cmd], cwd=str(self.repo), capture_output=True, text=True, encoding="utf-8", env=env)
        out = (done.stdout or "") + (done.stderr or "")
        if not self.dry:
            with self.log_path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(f"$ {cmd}\n{out}\n[rc={done.returncode}]\n")
        return done.returncode, out

    # -- receipts ----------------------------------------------------------
    def receipts(self) -> list[dict]:
        if not self.receipts_path.is_file():
            return []
        out = []
        for line in self.receipts_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                out.append(json.loads(line))
        return [r for r in out if r.get("launch_id") == self.spec["launch_id"]]

    def is_done(self, step: str) -> bool:
        if step in self.redo:
            return False
        last = [r for r in self.receipts() if r["step"] == step]
        return bool(last) and last[-1]["status"] in ("ok", "skipped-done")

    def receipt(self, step: str, status: str, detail: str, head_before: str, rc: int = 0) -> None:
        if self.dry:
            return
        self.receipts_path.parent.mkdir(parents=True, exist_ok=True)
        row = {"schema": RECEIPT_SCHEMA, "launch_id": self.spec["launch_id"], "package": self.spec["package"], "step": step, "status": status,
               "utc": utc_now(), "head_before": head_before, "head_after": self.head(), "rc": rc, "detail": detail[:600]}
        with self.receipts_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")

    # -- rules -------------------------------------------------------------
    def rule_clean(self) -> None:
        dirt = self.git("status", "--porcelain").strip()
        if dirt:
            raise Refusal("master tree is not clean:\n" + "\n".join(dirt.splitlines()[:6]))

    def rule_no_merge(self) -> None:
        gd = self.git("rev-parse", "--git-dir").strip()
        gdir = Path(gd) if os.path.isabs(gd) else self.repo / gd
        for marker in ("MERGE_HEAD", "rebase-merge", "rebase-apply", "CHERRY_PICK_HEAD", "REVERT_HEAD"):
            if (gdir / marker).exists():
                raise Refusal(f"a merge / rebase / cherry-pick is in progress ({marker})")

    def rule_not_alive(self) -> None:
        override = os.environ.get("PACKAGE_LAUNCH_ALIVE_CMD")
        if override is not None:
            out = subprocess.run(["bash", "-c", override], capture_output=True, text=True).stdout
        else:
            out = subprocess.run(["pgrep", "-af", ALIVE_PATTERN], capture_output=True, text=True).stdout
            out = "\n".join(l for l in out.splitlines() if "package_launch" not in l)
        if out.strip():
            raise Refusal("a batch driver, flight, lease, re-pin or flip process is alive:\n" + "\n".join(out.strip().splitlines()[:5]))
        if (self.data_root / "locks" / "flight.lock").exists():
            raise Refusal(f"flight.lock present under {self.data_root}")

    def rule_flight_commit(self, path: str) -> None:
        file = Path(path)
        if not file.is_file():
            raise Refusal(f"flight-commit file {path} is missing")
        got, want = file.read_text(encoding="utf-8").strip(), self.head()
        if got != want:
            raise Refusal(f"flight-commit file {path} reads {got[:12]} but master HEAD is {want[:12]}")

    def check_rules(self, step: str) -> None:
        self.rule_no_merge()
        if step in CLEAN_BEFORE:
            self.rule_clean()
        if step in ALIVE_BEFORE:
            self.rule_not_alive()

    # -- steps -------------------------------------------------------------
    def step_cmd(self, step: str) -> tuple[str, str]:
        cfg = self.spec["steps"].get(step)
        if not cfg or "cmd" not in cfg:
            raise Refusal(f"spec has no steps.{step}.cmd")
        rc, out = self.run_cmd(self.render(cfg["cmd"]), cfg.get("env"))
        if rc != 0:
            raise StepFailed(f"{step} command exited {rc}: {out.strip()[-300:]}")
        return "ok", f"rc=0"

    def step_countersign(self) -> tuple[str, str]:
        if not self.root_countersign:
            raise Refusal("countersign is the coordinator's act: pass --root-countersign", )
        cfg = self.spec["steps"]["countersign"]
        texts = json.loads((self.repo / self.render(cfg["texts"])).read_text(encoding="utf-8"))["rows"]
        skip = cfg.get("skip_substrings", ["-READ-"])
        wanted = cfg.get("run_ids") or [r for r in texts if not any(s in r for s in skip)]
        ledger = self.repo / cfg.get("ledger", "docs/exposure-ledger.md")
        lines = ledger.read_bytes().decode("utf-8").split("\n")
        stamp, changed, already, missing = utc_now(), [], [], []
        for run_id in wanted:
            idx = next((i for i, l in enumerate(lines) if l.startswith("|") and l.count("|") >= 16 and l.split("|")[2].strip() == run_id), None)
            if idx is None:
                missing.append(run_id)
                continue
            cells = lines[idx].split("|")
            notes = cells[15].strip()
            if notes.startswith("REGISTERED BEFORE"):
                already.append(run_id)
                continue
            m = re.match(r"DRAFT\b\.?", notes)
            if not m:
                raise StepFailed(f"row {run_id} notes start with neither DRAFT nor REGISTERED BEFORE")
            text = texts[run_id].replace("<UTC timestamp>", stamp)
            cells[15] = " " + text + notes[m.end():] + " "
            scope = cells[4].strip()
            if scope.startswith(DRAFT_SCOPE_PREFIX):
                cells[4] = " " + scope[len(DRAFT_SCOPE_PREFIX):] + " "
            lines[idx] = "|".join(cells)
            changed.append(run_id)
        if missing:
            raise StepFailed(f"ledger rows not found: {missing}")
        if changed:
            ledger.write_bytes("\n".join(lines).encode("utf-8"))
        status = "ok" if changed else "skipped-done"
        return status, f"countersigned {len(changed)} row(s) at {stamp}; already {len(already)}"

    def step_mint(self) -> tuple[str, str]:
        cfg = self.spec["steps"]["mint"]
        done = cfg.get("done_if")
        if done:
            path = self.data_root / done["file"]
            if path.is_file() and all(s in path.read_text(encoding="utf-8") for s in done.get("contains", [])):
                return "skipped-done", f"receipt {done['file']} already carries the required content"
        return self.step_cmd("mint")

    def step_commit(self) -> tuple[str, str]:
        cfg = self.spec["steps"]["commit"]
        self.git("add", "--", *[self.render(p) for p in cfg["paths"]])
        if self.git("diff", "--cached", "--name-only").strip() == "":
            return "skipped-done", "nothing to commit"
        if "message_file" in cfg:
            msg = self.render(cfg["message_file"])
        else:
            handle = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8", newline="\n")
            text = self.render(cfg["message"]).rstrip("\n")
            handle.write(text + ("" if "Co-Authored-By" in text else "\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>") + "\n")
            handle.close()
            msg = handle.name
        self.git("commit", "-q", "-F", msg)
        return "ok", f"committed {self.head()[:12]}"

    def step_flip(self) -> tuple[str, str]:
        cfg = self.spec["steps"]["flip"]
        wrapper = cfg.get("wrapper", "bash scripts/flights/batch/flip_package_ext4.sh")
        cells = ",".join(cfg["cells"])
        log = cfg.get("log") or f"/home/chao/{Path(cfg.get('package', self.spec['readiness_dir'])).name}-flip.out"
        # The pins-commit message file is the wrapper's, not the repo's: when the spec carries `pins_commit_text` and the
        # file is missing, write it (2026-10-17: the NX-T R2 flip was refused "pins commit message file ... not found"
        # because nothing had ever created it; the nxt1 worked example had a hand-written one).
        pins_path = Path(cfg["pins_commit_msg"])
        if cfg.get("pins_commit_text") and not pins_path.is_file() and not self.dry:
            pins_path.parent.mkdir(parents=True, exist_ok=True)
            pins_path.write_text(cfg["pins_commit_text"].rstrip("\n") + "\n", encoding="utf-8")
        cmd = (f'{wrapper} --flip "{cfg["script"]}" --package {cfg.get("package", self.spec["readiness_dir"])} --cells {cells} '
               f'--pins-commit-msg {cfg["pins_commit_msg"]} --log {log}')
        # Each KEY=VALUE is ONE shell word (2026-10-17: `NXT2_KINDS=smoke arm` unquoted reached the wrapper as two
        # words and the NX-T R2 flip was refused with "bad extra env 'arm'"; the nxt1 worked example never ran this step).
        for key, value in cfg.get("env", {}).items():
            word = shlex.quote(f"{key}={value}")
            cmd += f" -- {word}" if cmd.count(" -- ") == 0 else f" {word}"
        rc, out = self.run_cmd(cmd)
        if rc != 0:
            raise StepFailed(f"flip wrapper exited {rc}: {out.strip()[-300:]}")
        text = Path(log).read_text(encoding="utf-8") if Path(log).is_file() else out
        self.parse_flip_log(text, len(cfg["cells"]))
        if cfg.get("flight_commit_file"):
            try:
                self.rule_flight_commit(cfg["flight_commit_file"])
            except Refusal as error:        # the flip already ran: a stale flight-commit file is a failed flip, not a refusal
                raise StepFailed(str(error)) from None
        return "ok", f"gate PASS x{len(cfg['cells'])}; master {self.head()[:12]}"

    def parse_flip_log(self, text: str, n_cells: int) -> None:
        """The hollow-flip lesson: a zero exit is not a flip. Require the gate block, not just the wrapper's exit code."""
        if "== gate" not in text:
            raise StepFailed("flip log has no gate block")
        gate = text.rsplit("== gate", 1)[1]
        gate = gate.split("flight commit file:", 1)[0]
        bad = [l for l in text.splitlines() if re.search(r"check: FAIL|GATE FAILED|REFUSED|DID NOT CONVERGE|FLIGHT COMMIT MISMATCH|NOT A FIXED POINT", l)]
        if bad:
            raise StepFailed("flip log reports a failure: " + bad[0][:200])
        passes = len(re.findall(r"check: PASS", gate))
        if passes < n_cells:
            raise StepFailed(f"flip gate block has {passes} PASS line(s) for {n_cells} cell(s)")
        if "FLIP_CHAIN_DONE" not in text:
            raise StepFailed("flip log lacks FLIP_CHAIN_DONE")
        m = re.findall(r"master verified at flight commit ([0-9a-f]{40})", text)
        if not m or m[-1] != self.head():
            raise StepFailed("flip log does not verify master at the current HEAD")

    def step_chain(self) -> tuple[str, str]:
        cfg = self.spec["steps"]["chain"]
        if cfg.get("flight_commit_file"):
            self.rule_flight_commit(cfg["flight_commit_file"])
        ps = os.environ.get("SAEA_POWERSHELL") or shutil.which("powershell.exe") or "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
        ps1 = os.environ.get("SAEA_TASK_PS1_WIN", DEFAULT_PS1_WIN)
        done = subprocess.run([ps, "-NoProfile", "-File", ps1, "-Name", cfg["task"], "-Script", cfg["wrapper"], "-Start"],
                              capture_output=True, text=True, encoding="utf-8", errors="replace")
        out = (done.stdout + done.stderr).replace("\r", "")
        with self.log_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(f"$ saea_task.ps1 -Name {cfg['task']} -Script {cfg['wrapper']} -Start\n{out}\n[rc={done.returncode}]\n")
        low = out.lower()
        if done.returncode != 0 or "started" not in low or any(w in low for w in ("refused", "not registered", "already running")):
            raise StepFailed(f"chain task did not start: {out.strip()[-300:]}")
        return "ok", f"task {cfg['task']} started"

    def run_step(self, step: str) -> tuple[str, str]:
        if step == "countersign":
            return self.step_countersign()
        if step == "mint":
            return self.step_mint()
        if step == "commit":
            return self.step_commit()
        if step == "flip":
            return self.step_flip()
        if step == "chain":
            return self.step_chain()
        return self.step_cmd(step)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    p.add_argument("spec")
    p.add_argument("--from", dest="first", default=STEPS[0], choices=STEPS)
    p.add_argument("--until", default=DEFAULT_UNTIL, choices=STEPS)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--root-countersign", action="store_true")
    p.add_argument("--redo", action="append", default=[], choices=STEPS)
    p.add_argument("--repo-root", default=None, help="default: the repository this script lives in")
    args = p.parse_args(argv)
    if STEPS.index(args.first) > STEPS.index(args.until):
        p.error("--from comes after --until")
    repo = Path(args.repo_root) if args.repo_root else Path(__file__).resolve().parents[3]
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    try:
        launch = Launch(spec, repo, dry=args.dry_run, root_countersign=args.root_countersign, redo=set(args.redo))
    except Refusal as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 2
    todo = STEPS[STEPS.index(args.first):STEPS.index(args.until) + 1]
    launch.say(f"launch {spec['launch_id']} package {spec['package']} steps {todo}{' (DRY RUN)' if args.dry_run else ''}")
    first_acting = True
    for step in todo:
        if launch.is_done(step):
            launch.say(f"step {step}: done in this launch id (receipt), skipped")
            continue
        head_before = launch.head()
        try:
            if step == "countersign" and not args.root_countersign:
                raise Refusal("countersign is the coordinator's act: pass --root-countersign")
            if args.dry_run and not first_acting:
                launch.say(f"step {step}: would run (rules are checked when the step is reached)")
                continue
            launch.check_rules(step)
            first_acting = False
            if args.dry_run:
                launch.say(f"step {step}: would run (rules pass at HEAD {head_before[:12]})")
                continue
            launch.say(f"step {step}: start at HEAD {head_before[:12]}")
            status, detail = launch.run_step(step)
        except Refusal as error:
            launch.say(f"step {step}: REFUSED: {error}")
            launch.receipt(step, "refused", str(error), head_before, 2)
            return 3 if step == "countersign" else 2
        except StepFailed as error:
            launch.say(f"step {step}: FAILED: {error}")
            launch.receipt(step, "failed", str(error), head_before, 1)
            return 1
        launch.say(f"step {step}: {status}: {detail}")
        launch.receipt(step, status, detail, head_before)
    launch.say("launch " + ("dry run complete" if args.dry_run else "complete through " + todo[-1]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
