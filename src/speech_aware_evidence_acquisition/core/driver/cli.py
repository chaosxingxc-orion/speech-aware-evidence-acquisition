"""``saea-driver`` CLI: ``score`` / ``run`` / ``finalize`` / ``smoke`` subcommands.

Split out of the former monolithic ``core/driver.py`` (R0 repair refactor
stage 1, pure move, no behaviour change). The function-local
``from ...contracts import FrozenCoreGate`` / ``from .. import session``
imports inside ``_cli_run`` are preserved exactly as they were (not
promoted to module level) -- see that function's own history for why.

``smoke`` (R0 operator-path repair, independent rereview
``2026-08-07-saea-r0-script-engineering-review-assessment.md`` §10 item 3) is
implemented in ``smoke.py``, not here, purely for file size -- its own module
docstring explains what it does and why ``--dry-run`` is TEST-ONLY.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ...contracts import ExecutionPlan
from ...e0.artifacts import REPO_ROOT
from ..base import SCORERS, TRANSPORTS
from ..bundle import finalize_bundle, verify_bundle
from ..config import compose, resolve_runtime_receipt_path, runtime_receipt_relpath
from ..resources import resolve_resource_sampler
from ..scorers import score_bundle
from .bundled import run_experiment_bundled
from .smoke import _cli_smoke


def _cli_score(args: argparse.Namespace) -> int:
    """IMPORTANT fix (T6 fix round, I7): the manifest path is now the
    AUTHORITATIVE one. ``--manifest`` verifies the bundle
    (``core.bundle.verify_bundle``) and scores it through
    ``core.scorers.score_bundle`` -- I7's whole point, that scoring enters
    only through a verified bundle. ``--outputs`` is KEPT (removing it would
    break ad-hoc/exploratory scoring of a file that has no manifest yet, a
    genuinely useful capability) but is now explicit about what it is: no
    split/trace/hash verification happens at all, so its result is NEVER an
    audit record -- a loud warning is printed to stderr and the result is
    tagged ``"verified": false`` on stdout, so nothing downstream can mistake
    it for an authoritative score by accident."""

    from ...data.lock import data_root, load_lock, umbrella_lock_path

    lock = load_lock(umbrella_lock_path())
    root = data_root()
    if args.manifest:
        bundle = verify_bundle(Path(args.manifest))
        results = score_bundle(bundle, lock, root)
        print(
            json.dumps(
                {
                    "manifest": str(Path(args.manifest)),
                    "verified": True,
                    "scores": {name: result["aggregate"] for name, result in results.items()},
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    print(
        "WARNING: unverified raw-outputs scoring (--outputs, no --manifest). This "
        "result bypasses split/trace/hash verification (invariant I7) entirely and "
        "is NOT an audit record -- it must never be cited as a formal R0/R1/2B "
        "result. Pass --manifest for an authoritative, verified score.",
        file=sys.stderr,
    )
    for name in args.scorers.split(","):
        scores = SCORERS.resolve(name.strip())(Path(args.outputs), lock, root)
        print(
            json.dumps(
                {"verified": False, "scorer": name.strip(), "aggregate": scores["aggregate"]},
                indent=2,
                sort_keys=True,
            )
        )
    return 0


def _cli_run(args: argparse.Namespace) -> int:
    from ...contracts import FrozenCoreGate
    from ...data.lock import data_root, load_lock, umbrella_lock_path
    from ..session import attach_session, load_runtime_receipt

    lock = load_lock(umbrella_lock_path())
    root = data_root()
    composed = compose(REPO_ROOT, args.model, args.dataset, args.baseline, args.experiment)
    plan = ExecutionPlan(**json.loads(Path(args.plan).read_text(encoding="utf-8")))
    runtime_root = Path(args.runtime_root)
    # R0.2 second-model plumbing: the model fragment's own optional
    # "runtime_receipt" key (default: today's "receipts/runtime.json") picks
    # which committed receipt this gate/session pair is bound to -- see
    # core.config.runtime_receipt_relpath's own docstring.
    receipt_relpath = runtime_receipt_relpath(composed.values)
    gate = FrozenCoreGate.for_study_repo(
        REPO_ROOT, root, runtime_root, runtime_receipt_relpath=receipt_relpath
    )
    # R0 repair T5 (I5): the runtime receipt is the SAME committed file the
    # gate itself re-hashes. attach_session binds this run to a session
    # receipt whose binary/model identity, live pid, PROCESS IMAGE identity
    # (T5 fix-1 -- pid liveness alone proves nothing) and loopback host it
    # independently re-verifies against that file -- a resident server
    # started out of band is only usable if it can PROVE it is the
    # receipt-pinned process, never merely because its base_url matches the
    # config.
    runtime_receipt = load_runtime_receipt(resolve_runtime_receipt_path(REPO_ROOT, composed.values))
    session = attach_session(
        Path(args.session_receipt), runtime_receipt=runtime_receipt, runtime_root=runtime_root
    )
    transport_factory = TRANSPORTS.resolve(str(composed.values["transport"]))
    transport = transport_factory(
        composed.values,
        root,
        session=session,
        runtime_receipt=runtime_receipt,
        runtime_root=runtime_root,
    )
    # R0 repair T6 (I7): every real run always produces a run manifest, win
    # or lose -- run_experiment_bundled marks the attempt ABORTED and still
    # writes it on failure, then re-raises (a CLI traceback on a genuine
    # run failure is expected; the manifest survives it either way).
    # R0 repair T7 (I8): this is the ONE call site that resolves a real
    # resource sampler -- every other caller of run_experiment/
    # run_experiment_bundled (library code, every test) gets that function's
    # own NullSampler default instead, so a real nvidia-smi is only ever
    # touched by an actual live run through this CLI.
    manifest_path = run_experiment_bundled(
        composed, plan, gate, lock, root, Path(args.run_dir), transport,
        session_receipt_path=Path(args.session_receipt),
        resource_sampler=resolve_resource_sampler(),
    )
    print(json.dumps({"run_id": plan.run_id, "manifest": str(manifest_path)}, indent=2))
    return 0


def _cli_finalize(args: argparse.Namespace) -> int:
    from ...data.lock import data_root, load_lock, umbrella_lock_path

    lock = load_lock(umbrella_lock_path())
    root = data_root()
    ledger_cells = (
        json.loads(Path(args.ledger_cells).read_text(encoding="utf-8"))
        if args.ledger_cells
        else {}
    )
    result = finalize_bundle(
        Path(args.manifest),
        lock,
        root,
        ledger_cells=ledger_cells,
        tracking_uri=args.tracking_uri,
    )
    print(
        json.dumps(
            {
                "scores": str(result.scores_path),
                "ledger_markdown": str(result.ledger_markdown_path),
                "ledger_json": str(result.ledger_json_path),
                "mlflow_run": result.mlflow_run_id,
                "attempt_state": result.attempt_state,
            },
            indent=2,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="saea-driver")
    sub = parser.add_subparsers(dest="command", required=True)
    score = sub.add_parser(
        "score",
        help=(
            "model-free scoring: --manifest is the AUTHORITATIVE, I7-verified path; "
            "--outputs is UNVERIFIED ad-hoc scoring, never an audit record"
        ),
    )
    score_target = score.add_mutually_exclusive_group(required=True)
    score_target.add_argument(
        "--manifest",
        default=None,
        help="path to a run-manifest.json; verified and scored via core.bundle/core.scorers (I7)",
    )
    score_target.add_argument(
        "--outputs",
        default=None,
        help=(
            "path to a raw outputs.jsonl; scored with NO split/trace/hash verification "
            "-- not an audit record"
        ),
    )
    score.add_argument(
        "--scorers", default="asr-wer", help="comma-separated scorer names (--outputs mode only)"
    )
    score.set_defaults(func=_cli_score)
    run = sub.add_parser("run", help="gate-enforced live run (requires a plan file)")
    run.add_argument("--model", required=True)
    run.add_argument("--dataset", required=True)
    run.add_argument("--baseline", required=True)
    run.add_argument("--experiment", required=True)
    run.add_argument("--plan", required=True)
    run.add_argument("--run-dir", required=True)
    run.add_argument("--runtime-root", required=True)
    run.add_argument(
        "--session-receipt",
        required=True,
        help=(
            "path to a SessionReceipt (core.session.attach_session) for an "
            "already-resident, receipt-pinned llama-server; R0 repair T5, "
            "invariant I5 -- there is no run without one"
        ),
    )
    run.set_defaults(func=_cli_run)
    finalize = sub.add_parser(
        "finalize",
        help=(
            "verify a run-manifest bundle, score it, upload it, and mark the "
            "attempt FINALIZED (R0 repair T6, invariant I7)"
        ),
    )
    finalize.add_argument("--manifest", required=True, help="path to a run-manifest.json")
    finalize.add_argument(
        "--ledger-cells",
        default=None,
        help=(
            "path to a JSON object of human-supplied ledger cells (experiment_id, "
            "date, etc.); refused if any cell contradicts the verified manifest"
        ),
    )
    finalize.add_argument(
        "--tracking-uri",
        default=None,
        help="MLflow tracking URI; omit to skip the (stubbable) MLflow upload entirely",
    )
    finalize.set_defaults(func=_cli_finalize)

    smoke = sub.add_parser(
        "smoke",
        help=(
            "thin orchestrator (R0 operator-path repair): fresh attempt_id -> plan -> "
            "session -> run -> finalize, one command, printing every artifact location; "
            "see smoke.py's module docstring for exactly what --dry-run substitutes"
        ),
    )
    smoke.add_argument("--model", required=True)
    smoke.add_argument("--dataset", required=True)
    smoke.add_argument("--baseline", required=True)
    smoke.add_argument("--experiment", required=True)
    smoke.add_argument("--run-id", required=True)
    smoke.add_argument(
        "--execution-profile",
        default="bounded-discovery-probe",
        help="Stage-2 execution profile (default: bounded-discovery-probe)",
    )
    smoke.add_argument(
        "--planned-model-calls", type=int, required=True,
        help="finite positive integer; no numeric ceiling since the 2026-08-06 owner amendment",
    )
    smoke.add_argument("--planned-gpu-hours", type=float, required=True)
    smoke.add_argument("--planned-speech-audio-seconds", type=int, required=True)
    smoke.add_argument(
        "--run-dir", required=True,
        help="STABLE parent directory; a fresh attempt_id subdirectory is created every run",
    )
    smoke.add_argument(
        "--runtime-root", default=None,
        help="required unless --dry-run; see docs/runbooks/2026-08-05-r0-smoke.md preconditions",
    )
    smoke.add_argument("--host", default="127.0.0.1")
    smoke.add_argument("--port", type=int, default=8090)
    smoke.add_argument(
        "--tracking-uri", required=True,
        help="explicit local MLflow tracking URI; smoke never silently skips the upload",
    )
    smoke.add_argument("--ledger-cells", default=None)
    smoke.add_argument(
        "--repo-root", default=None,
        help="TEST-ONLY override of the study repo root; real operator usage should never pass this",
    )
    smoke.add_argument(
        "--dry-run", action="store_true",
        help=(
            "TEST-ONLY: fake transport + no-op gate + a synthetic session receipt, never a "
            "real model touch; never pass this for a real smoke"
        ),
    )
    smoke.set_defaults(func=_cli_smoke)

    args = parser.parse_args(argv)
    return args.func(args)
