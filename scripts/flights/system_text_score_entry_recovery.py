"""Execute the owner-authorized single scoring-entry recovery via the shared scorer."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_once(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("registration", type=Path)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    r = json.loads(args.registration.read_text())
    assert r["schema"] == "saea-score-entry-recovery-registration-v1"
    assert r["owner_decision"] == 216 and r["max_official_score_jobs"] == 1
    owner = r["owner_receipt"]
    assert digest(owner["path"]) == owner["sha256"]
    assert json.loads(Path(owner["path"]).read_text())["decisions"]["216"]["status"] == "approved"
    repo = Path(r["source_root"])
    assert subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip() == r["source_commit"]
    assert not subprocess.check_output(["git", "-C", str(repo), "status", "--porcelain"], text=True).strip()
    assert sys.dont_write_bytecode and os.environ.get("PYTHONDONTWRITEBYTECODE") == "1"
    assert all(digest(p) == h for p, h in r["preserved_pins"].items())
    assert digest(r["manifest"]) == r["unscored_manifest_sha256"]
    assert not Path(r["output_dir"]).exists()
    sys.path.insert(0, str(repo / "src"))
    from speech_aware_evidence_acquisition.core.flight.scoring import load_sealed_score_jobs
    from speech_aware_evidence_acquisition.core.bundle.verify import verify_bundle
    from speech_aware_evidence_acquisition.core.scorers import _assert_scoring_entry_gate
    from speech_aware_evidence_acquisition.core.scoring_batch import ScoringContext, run_score_batch
    from speech_aware_evidence_acquisition.data.lock import load_lock
    jobs = load_sealed_score_jobs(json.loads(Path(r["flight_receipts"]).read_text())["stages"]["seal"])
    assert len(jobs) == 1 and jobs[0].job_id == r["attempt_id"]
    bundle = verify_bundle(jobs[0].manifest)
    assert bundle.attempt_state == "OPENED" and len(bundle.split_ids) == 400
    _assert_scoring_entry_gate(bundle, load_lock(Path(r["lock_path"])), Path(r["data_root"]), repo)
    if args.check_only:
        print(json.dumps({"preflight": "PASS", "rows": 400, "scorer_contacts": 0}))
        return 0
    directory = args.registration.parent
    write_once(directory / "started.json", {"started_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "pid": os.getpid(), "registration_sha256": digest(args.registration)})
    summary = run_score_batch(jobs, output_dir=Path(r["output_dir"]), max_workers=1,
        operation="finalize", include_per_sample=True,
        context=ScoringContext(repo, Path(r["data_root"]), Path(r["lock_path"])))
    preserved = all(digest(p) == h for p, h in r["preserved_pins"].items())
    result = {"finished_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "job_count": summary["job_count"], "succeeded": summary["succeeded"], "failed": summary["failed"],
        "preserved_evidence_unchanged": preserved, "new_generation_contacts": 0,
        "batch_summary": str(Path(r["output_dir"]) / "batch-summary.json"), "retry_permitted": False}
    write_once(directory / "finished.json", result)
    print(json.dumps(result))
    return 0 if preserved and summary["failed"] == 0 and summary["succeeded"] == 1 else 1


if __name__ == "__main__":
    raise SystemExit(main())
