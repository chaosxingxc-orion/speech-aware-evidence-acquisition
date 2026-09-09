"""Exercise handoff validation only against synthetic local Git repositories."""

from __future__ import annotations

from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


CHECK_PATH = Path(__file__).resolve().parents[2] / "scripts/checks/experiment_handoff_check.py"
SPEC = importlib.util.spec_from_file_location("experiment_handoff_check", CHECK_PATH)
assert SPEC is not None and SPEC.loader is not None
handoff = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(handoff)


class HandoffCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "repo"
        self.root.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "Synthetic Test")
        self.git("config", "user.email", "synthetic@example.invalid")
        (self.root / "tracked.txt").write_text("synthetic\n", encoding="utf-8")
        self.git("add", "tracked.txt")
        self.git("commit", "-qm", "Synthetic fixture")
        self.state = {
            "schema_version": 1,
            "generation": 1,
            "phase": "awaiting_fable_reply",
            "coordinator": "Codex",
            "execution_owner": "UNCONFIRMED",
            "request_id": "SAEA-HANDOFF-20260909-01",
            "request_path": "docs/superpowers/plans/experiment-handoff/REQUEST-001.md",
            "response_path": "docs/superpowers/plans/experiment-handoff/RESPONSE-001.md",
            "response_status": "awaiting_reply",
            "snapshot_commit": self.git("rev-parse", "HEAD").strip(),
            "updated_at_utc": "2026-09-09T12:00:00Z",
            "next_action": "Review reply before any flight",
            "launch_allowed": False,
        }
        self.write_state()
        (self.root / self.state["request_path"]).write_text("Synthetic request\n", encoding="utf-8")

    def git(self, *args):
        return subprocess.run(
            ["git", "-C", str(self.root), *args], check=True, capture_output=True, text=True
        ).stdout

    def write_state(self):
        path = self.root / handoff.STATE_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.state), encoding="utf-8")

    def reply(self, status="COMPLETE", request_id=None):
        path = self.root / self.state["response_path"]
        path.write_text(
            f"# Reply status: {status}\nRequest ID: {request_id or self.state['request_id']}\n"
            "Synthetic private reply body must not appear in the report.\n",
            encoding="utf-8",
        )

    def inspect(self):
        return handoff.inspect_handoff(self.root)

    def test_missing_and_pending_reply_are_legitimate_waiting_states(self):
        self.assertEqual(self.inspect()["status"], "WAITING_FOR_REPLY")
        self.reply("PENDING")
        self.assertEqual(self.inspect()["status"], "WAITING_FOR_REPLY")

    def test_complete_reply_is_ready_for_review_and_does_not_mutate_state(self):
        self.reply()
        state_bytes = (self.root / handoff.STATE_PATH).read_bytes()
        report = self.inspect()
        self.assertEqual(report["status"], "REPLY_READY")
        self.assertEqual(report["execution_authority"], "NOT_EVALUATED")
        self.assertNotIn("private reply body", json.dumps(report))
        self.assertEqual((self.root / handoff.STATE_PATH).read_bytes(), state_bytes)

    def test_mismatched_complete_reply_is_invalid(self):
        self.reply(request_id="ANOTHER-REQUEST")
        self.assertEqual(self.inspect()["status"], "INVALID")

    def test_complete_reply_requires_exact_id_and_unique_markers(self):
        path = self.root / self.state["response_path"]
        for content in (
            "Reply status: COMPLETE\n",
            "Reply status: COMPLETE\nRequest ID: wrong suffix\n",
            f"Reply status: COMPLETE\nReply status: PENDING\nRequest ID: {self.state['request_id']}\n",
        ):
            with self.subTest(content=content):
                path.write_text(content, encoding="utf-8")
                self.assertEqual(self.inspect()["status"], "INVALID")

    def test_missing_request_is_invalid(self):
        (self.root / self.state["request_path"]).unlink()
        self.assertEqual(self.inspect()["status"], "INVALID")

    def test_paths_reject_traversal_absolute_and_symlink_escape(self):
        for value in ("../outside.md", r"..\outside.md", "/tmp/outside.md", r"C:\outside.md"):
            with self.subTest(value=value):
                self.state["response_path"] = value
                self.write_state()
                self.assertEqual(self.inspect()["status"], "INVALID")
        outside = Path(self.temp.name) / "outside.md"
        outside.write_text("Synthetic external file", encoding="utf-8")
        link = self.root / "reply-link.md"
        link.symlink_to(outside)
        self.state["response_path"] = link.name
        self.write_state()
        self.assertEqual(self.inspect()["status"], "INVALID")

    def test_schema_and_execution_permission_fail_closed(self):
        for key, value in (
            ("schema_version", True), ("generation", 0), ("launch_allowed", True),
            ("phase", "ready"), ("snapshot_commit", "not-a-commit"),
            ("updated_at_utc", "2026-09-09T12:00:00"),
        ):
            with self.subTest(key=key):
                previous = self.state[key]
                self.state[key] = value
                self.write_state()
                self.assertEqual(self.inspect()["status"], "INVALID")
                self.state[key] = previous

    def test_request_response_and_state_must_resolve_to_distinct_paths(self):
        for value in (self.state["request_path"], "./" + handoff.STATE_PATH):
            with self.subTest(value=value):
                self.state["response_path"] = value
                self.write_state()
                self.assertEqual(self.inspect()["status"], "INVALID")

    def test_dirty_counts_cover_rename_staged_unstaged_and_untracked(self):
        self.git("add", ".")
        self.git("commit", "-qm", "Synthetic handoff")
        self.git("mv", "tracked.txt", "renamed.txt")
        (self.root / "renamed.txt").write_text("modified\n", encoding="utf-8")
        (self.root / "untracked.txt").write_text("new\n", encoding="utf-8")
        report = self.inspect()
        self.assertEqual(report["dirty_file_counts"], {
            "tracked": 1, "untracked": 1, "staged": 1, "unstaged": 1, "total": 2,
        })
        self.assertEqual(report["current_head"], self.git("rev-parse", "HEAD").strip())
        self.assertTrue(any("differs" in warning for warning in report["warnings"]))

    def test_duplicate_json_and_non_repository_are_invalid(self):
        path = self.root / handoff.STATE_PATH
        path.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
        self.assertEqual(self.inspect()["status"], "INVALID")
        self.assertEqual(handoff.inspect_handoff(Path(self.temp.name))["status"], "INVALID")

    def test_cli_creates_new_report_and_refuses_overwrite(self):
        output = Path(self.temp.name) / "report.json"
        with redirect_stdout(io.StringIO()):
            result = handoff.main(["--repo-root", str(self.root), "--output", str(output)])
        self.assertEqual(result, 0)
        original = output.read_bytes()
        with redirect_stdout(io.StringIO()) as captured:
            result = handoff.main(["--repo-root", str(self.root), "--output", str(output)])
        self.assertEqual(result, 1)
        self.assertEqual(output.read_bytes(), original)
        self.assertEqual(json.loads(captured.getvalue())["status"], "INVALID")


if __name__ == "__main__":
    unittest.main()
