#!/usr/bin/env python3
"""Mint the step-2b runtime config of the Stage-3 construction roster R01.

Step 2b of the preparation plan
(``docs/readiness/2026-09-22-slurp-stage3-construction-r01-preparations-v1.md``
sections 3 and 8) is launched with::

    python -m speech_aware_evidence_acquisition.core.speech_preparation_runtime \
        --config  <data root>/coordination/slurp-stage3-construction-r01-query-encoding-v1/runtime-config-v1.json \
        --config-sha256 <that file's raw sha256> \
        --data-root "$SPEECHRL_DATA_DIR" --source-root "$PWD"

That runtime config cannot be a committed file, and its digest cannot be
written into any committed document, because ``core.speech_preparation_runtime.
main`` refuses to run unless the config's ``study_head`` equals the HEAD of the
clean checkout the launch runs from -- a commit that only exists once the
registration itself is committed. This generator closes that loop: it reads
HEAD, re-hashes the committed protocol and the umbrella lock, writes the config
deterministically (the same bytes for the same inputs) and prints its sha256
together with the exact launch line.

MODEL-FREE. Zero model, encoder, tokenizer, scorer, GPU and network contacts:
it hashes three files, reads ``git rev-parse``/``git status`` and writes one
small JSON document under the data root. It authorises nothing -- the launch it
prints still needs the countersigned exposure row
``SAEA-SLURP-STAGE3-CONSTRUCTION-R01-SPEECH-QUERY-ENCODING-V1``.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import subprocess
import sys
from pathlib import Path

RUN = "SAEA-SLURP-STAGE3-CONSTRUCTION-R01-SPEECH-QUERY-ENCODING-V1"
ATTEMPT = "encode-v1"
PROTOCOL_RELPATH = (
    "configs/preparation/slurp-stage3-construction-r01-speech-query-encoding-protocol-v1.json"
)
CONFIG_RELPATH = (
    "coordination/slurp-stage3-construction-r01-query-encoding-v1/runtime-config-v1.json"
)
SESSION_ID = "local-nemotron-slurp-stage3-construction-r01-query-v1"
SPLIT_IDENTITY = "2ece5e51ff781fdec89bef8e7448d8ba88249030d3c8a6478dba5e7c1e621dac"
PLANNED_MODEL_CALLS = 800
PLANNED_SPEECH_AUDIO_SECONDS = 3492
PLANNED_GPU_HOURS = 2.0
DEFAULT_UMBRELLA_LOCK = "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"


def sha256_of(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git(repo_root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo_root), *arguments],
        check=True, capture_output=True, text=True,
    ).stdout.strip()


def build_runtime_config(*, study_head: str, protocol_sha256: str, umbrella_lock: str,
                         umbrella_lock_sha256: str) -> dict:
    """The exact document ``core.speech_preparation_runtime`` consumes."""

    return {
        "plan": {
            "attempt_id": ATTEMPT,
            "carrier_lock_key": "slurp",
            "execution_profile": "bounded-discovery-probe",
            "planned_gpu_hours": PLANNED_GPU_HOURS,
            "planned_model_calls": PLANNED_MODEL_CALLS,
            "planned_speech_audio_seconds": PLANNED_SPEECH_AUDIO_SECONDS,
            "protocol_hash": protocol_sha256,
            "run_id": RUN,
            "schema": "saea-execution-plan-v1",
            "split_identity_hash": SPLIT_IDENTITY,
            "split_role": "discovery",
            "study": "speech-aware-evidence-acquisition",
        },
        "protocol": {"path": PROTOCOL_RELPATH, "sha256": protocol_sha256},
        "session_id": SESSION_ID,
        "study_head": study_head,
        "umbrella_lock": {"path": umbrella_lock, "sha256": umbrella_lock_sha256},
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--umbrella-lock", default=DEFAULT_UMBRELLA_LOCK)
    parser.add_argument(
        "--allow-dirty", action="store_true",
        help="write anyway on a dirty tree; the launch itself will still refuse",
    )
    args = parser.parse_args(argv)

    repo_root, data_root = Path(args.repo_root).resolve(), Path(args.data_root).resolve()
    dirt = [
        line for line in git(repo_root, "status", "--porcelain").splitlines()
        if not line.startswith("??")
    ]
    if dirt and not args.allow_dirty:
        print("REFUSED: %d tracked change(s) in %s; the launch binds a clean study_head"
              % (len(dirt), repo_root))
        return 1
    study_head = git(repo_root, "rev-parse", "HEAD")
    protocol_sha256 = sha256_of(repo_root / PROTOCOL_RELPATH)
    umbrella_lock = Path(args.umbrella_lock)
    document = build_runtime_config(
        study_head=study_head,
        protocol_sha256=protocol_sha256,
        umbrella_lock=str(umbrella_lock),
        umbrella_lock_sha256=sha256_of(umbrella_lock),
    )
    raw = json.dumps(document, indent=2, sort_keys=True) + "\n"
    out = data_root / CONFIG_RELPATH
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists() and out.read_text(encoding="utf-8") != raw:
        print("REFUSED: %s already exists with different bytes; delete it deliberately "
              "if a fresh registration is truly intended" % out)
        return 1
    with io.open(out, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(raw)
    config_sha256 = hashlib.sha256(raw.encode("utf-8")).hexdigest()

    print("runtime config %s" % out)
    print("sha256         %s" % config_sha256)
    print("study_head     %s" % study_head)
    print("protocol_hash  %s" % protocol_sha256)
    print("plan           %d calls / %d speech seconds / %.1f GPU hours / split_role discovery"
          % (PLANNED_MODEL_CALLS, PLANNED_SPEECH_AUDIO_SECONDS, PLANNED_GPU_HOURS))
    print()
    print("step 2b (run from %s at a clean tree, after the ledger row is countersigned):" % repo_root)
    print("  python -B -m speech_aware_evidence_acquisition.core.speech_preparation_runtime \\")
    print("      --config %s \\" % out)
    print("      --config-sha256 %s \\" % config_sha256)
    print("      --data-root %s --source-root %s" % (data_root, repo_root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
