"""``saea-driver`` CLI for scoring, execution, finalization, and packet promotion.

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
import hashlib
import json
import sys
from pathlib import Path
from typing import Mapping

from ...contracts import ExecutionPlan
from ...e0.artifacts import REPO_ROOT
from ..base import SCORERS, TRANSPORTS
from ..bundle import finalize_bundle, verify_bundle
from ..config import (
    compose,
    d1_media_supplement_relpath,
    d1_media_supplement_sha256,
    model_lock_key,
    model_materialization_root,
    resolve_runtime_receipt_path,
    runtime_receipt_relpath,
)
from ..resources import resolve_resource_sampler
from ..scorers import score_bundle
from .bundled import run_experiment_bundled
from .smoke import _cli_smoke
from .speech_native import _cli_speech_native_profile, _cli_speech_native_read


def _canonical_sha256(document: object) -> str:
    encoded = json.dumps(
        document,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _load_preprocess_stop_chain(
    *,
    session_receipt_path: Path,
    stop_receipt_path: Path,
    runtime_receipt: Mapping[str, object],
):
    """Verify that the receipt-bound preprocessing process is stopped."""

    from ..session import read_session_receipt, verify_against_runtime_receipt

    session = read_session_receipt(session_receipt_path)
    verify_against_runtime_receipt(session, runtime_receipt)
    if session.role != "preprocess":
        raise ValueError("speech packet promotion requires a preprocess session receipt")
    try:
        stop = json.loads(stop_receipt_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read preprocess stop receipt {stop_receipt_path}: {error}") from error
    required = {
        "schema",
        "study",
        "session_id",
        "session_role",
        "session_receipt_sha256",
        "runtime_receipt_sha256",
        "pid",
        "termination_signal",
        "forced",
        "stopped_at",
    }
    if not isinstance(stop, dict) or set(stop) != required:
        raise ValueError(f"preprocess stop receipt must carry exact keys {sorted(required)}")
    if (
        stop["schema"] != "saea-session-stop-receipt-v1"
        or stop["study"] != "speech-aware-evidence-acquisition"
        or stop["session_role"] != "preprocess"
        or stop["session_id"] != session.session_id
        or stop["pid"] != session.pid
        or stop["session_receipt_sha256"] != _canonical_sha256(session.as_json())
        or stop["runtime_receipt_sha256"] != _canonical_sha256(runtime_receipt)
    ):
        raise ValueError("preprocess session/stop/runtime receipt chain does not match")
    return session, stop


def _cli_promote_speech_packets(args: argparse.Namespace) -> int:
    """Promote an offline legacy featcache into audited packet directories."""

    from ...data.lock import data_root
    from ...data.slurp import load_slurp_engineering_gate
    from ..model import materialize_legacy_cached_speech_feature_packets
    from ..session import load_runtime_receipt

    root = data_root()
    legacy_cache_dir = Path(args.legacy_cache_dir)
    feature_root = Path(args.feature_root)
    receipt_output = Path(args.receipt_output)
    if not legacy_cache_dir.is_absolute() or not feature_root.is_absolute():
        raise ValueError("speech packet cache roots must be absolute paths")
    if not legacy_cache_dir.is_dir():
        raise ValueError(f"legacy speech featcache is unavailable: {legacy_cache_dir}")
    legacy_cache_dir = legacy_cache_dir.resolve()
    feature_root = feature_root.resolve()
    receipt_output = receipt_output.resolve()
    if legacy_cache_dir == feature_root:
        raise ValueError("legacy featcache and speech feature root must be different")
    if receipt_output.exists():
        raise ValueError(f"speech packet promotion receipt already exists: {receipt_output}")
    repo_resolved = REPO_ROOT.resolve()
    for label, candidate in (
        ("legacy featcache", legacy_cache_dir.resolve()),
        ("speech feature root", feature_root.resolve()),
        ("promotion receipt", receipt_output.resolve()),
    ):
        if candidate == repo_resolved or candidate.is_relative_to(repo_resolved):
            raise ValueError(f"{label} must stay outside the Git repository")
    if (
        not isinstance(args.dataset, str)
        or not args.dataset
        or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-" for character in args.dataset)
        or args.dataset[0] in ".-"
    ):
        raise ValueError("speech packet dataset must be a plain config fragment name")
    dataset_path = REPO_ROOT / "configs" / "dataset" / f"{args.dataset}.json"
    gate = load_slurp_engineering_gate(
        dataset_path,
        data_root=root,
        expected_count=args.expected_count,
        expected_split_name=getattr(args, "expected_split_name", "ENG-GATE8"),
        workers=args.workers,
    )
    receipt_relative = Path(args.runtime_receipt)
    if (
        receipt_relative.is_absolute()
        or "\\" in args.runtime_receipt
        or any(part in ("", ".", "..") for part in receipt_relative.parts)
    ):
        raise ValueError("speech packet runtime receipt path is unsafe")
    runtime_receipt_path = REPO_ROOT / "docs" / receipt_relative
    runtime_receipt = load_runtime_receipt(runtime_receipt_path)
    if runtime_receipt.get("role") != "preprocess":
        raise ValueError("speech packet promotion requires a preprocess runtime receipt")
    session, stop = _load_preprocess_stop_chain(
        session_receipt_path=Path(args.session_receipt),
        stop_receipt_path=Path(args.stop_receipt),
        runtime_receipt=runtime_receipt,
    )
    gguf_files = runtime_receipt.get("gguf_files")
    if not isinstance(gguf_files, list):
        raise ValueError("preprocess runtime receipt gguf_files must be a list")
    decoder = [entry for entry in gguf_files if "mmproj" not in Path(str(entry.get("path"))).name.lower()]
    mmproj = [entry for entry in gguf_files if "mmproj" in Path(str(entry.get("path"))).name.lower()]
    if len(decoder) != 1 or len(mmproj) != 1:
        raise ValueError("preprocess runtime receipt must bind exactly one decoder and one mmproj")
    packets = materialize_legacy_cached_speech_feature_packets(
        feature_root=feature_root,
        bindings=tuple(
            {
                "packet_id": sample.packet_id,
                "audio_path": str(Path(root) / sample.media_relpath),
            }
            for sample in gate.samples
        ),
        legacy_cache_dir=legacy_cache_dir,
        encoder_receipt_sha256=_canonical_sha256(runtime_receipt),
        decoder_gguf_sha256=str(decoder[0].get("sha256")),
        mmproj_sha256=str(mmproj[0].get("sha256")),
        expected_n_embd=args.expected_n_embd,
        causal_attention=True,
        workers=args.workers,
    )
    receipt = {
        "schema": "saea-speech-packet-promotion-receipt-v1",
        "study": "speech-aware-evidence-acquisition",
        "dataset_runtime_view_sha256": gate.runtime_view_sha256,
        "preprocess_session_id": session.session_id,
        "preprocess_session_receipt_sha256": _canonical_sha256(session.as_json()),
        "preprocess_stop_receipt_sha256": _canonical_sha256(stop),
        "runtime_receipt_sha256": _canonical_sha256(runtime_receipt),
        "legacy_cache_dir": str(legacy_cache_dir),
        "feature_root": str(feature_root),
        "count": len(packets),
        "packets": [
            {
                "packet_id": packet.packet_id,
                "packet_sha256": packet.packet_sha256,
                "audio_sha256": packet.audio_sha256,
                "decoder_gguf_sha256": packet.decoder_gguf_sha256,
                "mmproj_sha256": packet.mmproj_sha256,
            }
            for packet in packets
        ],
    }
    output = receipt_output
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with output.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(
                json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
            )
    except FileExistsError as error:
        raise ValueError(f"speech packet promotion receipt already exists: {output}") from error
    print(json.dumps({"receipt": str(output), "count": len(packets)}, indent=2))
    return 0


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
    # core.config.runtime_receipt_relpath's own docstring. The gate's
    # expected_model_lock_key is derived from the SAME composed config that
    # chose the receipt path, so a run can never pair one model's config
    # with a different model's receipt (core.config.model_lock_key's own
    # docstring; contracts.FrozenCoreGate.expected_model_lock_key).
    receipt_relpath = runtime_receipt_relpath(composed.values)
    configured_model_root = model_materialization_root(composed.values)
    gate = FrozenCoreGate.for_study_repo(
        REPO_ROOT,
        root,
        runtime_root,
        runtime_receipt_relpath=receipt_relpath,
        expected_model_lock_key=model_lock_key(composed.values),
        model_root=(Path(configured_model_root) if configured_model_root is not None else None),
        d1_media_supplement_relpath=d1_media_supplement_relpath(composed.values),
        d1_media_supplement_sha256=d1_media_supplement_sha256(composed.values),
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

    promote = sub.add_parser(
        "promote-speech-packets",
        help=(
            "model-free post-preprocess step: verify the targeted server stop receipt, "
            "then promote legacy featcache entries into audited speech packets"
        ),
    )
    promote.add_argument("--dataset", required=True)
    promote.add_argument(
        "--runtime-receipt",
        default="receipts/runtime-q4km-preprocess.json",
        help="path relative to the study docs directory",
    )
    promote.add_argument("--session-receipt", required=True)
    promote.add_argument("--stop-receipt", required=True)
    promote.add_argument("--legacy-cache-dir", required=True)
    promote.add_argument("--feature-root", required=True)
    promote.add_argument("--expected-count", type=int, default=8)
    promote.add_argument(
        "--expected-split-name",
        default="ENG-GATE8",
        help="exact split_name expected in the selected label-free runtime view",
    )
    promote.add_argument("--expected-n-embd", type=int, default=2048)
    promote.add_argument("--workers", type=int, default=8)
    promote.add_argument("--receipt-output", required=True)
    promote.set_defaults(func=_cli_promote_speech_packets)

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

    speech_profile = sub.add_parser(
        "speech-native-profile",
        help=(
            "engineering-only mmproj-free speech-native GPU profile through the "
            "existing session/gate/attempt/trace machinery"
        ),
    )
    speech_profile.add_argument("--model", required=True)
    speech_profile.add_argument("--dataset", required=True)
    speech_profile.add_argument("--baseline", required=True)
    speech_profile.add_argument("--experiment", required=True)
    speech_profile.add_argument("--plan", required=True)
    speech_profile.add_argument("--run-dir", required=True)
    speech_profile.add_argument("--runtime-root", required=True)
    speech_profile.add_argument("--host", default="127.0.0.1")
    speech_profile.add_argument("--port", type=int, default=8080)
    speech_profile.add_argument(
        "--session-receipt",
        default=None,
        help=(
            "attach to an already-resident receipt-pinned inference server; its "
            "binary, decoder, full launch argv, configured environment, process, "
            "socket, and mmproj-free state are reverified for this attempt, and "
            "the server remains resident after the attempt. Omit only for the "
            "legacy attempt-owned start/stop lifecycle"
        ),
    )
    speech_profile.add_argument(
        "--repo-root",
        default=None,
        help="TEST-ONLY repository-root override; real flights omit it",
    )
    speech_profile.set_defaults(func=_cli_speech_native_profile)

    speech_read = sub.add_parser(
        "speech-native-read",
        help="model-free read of hash-verified speech-native prediction flights",
    )
    speech_read.add_argument("--attempt-dir", action="append", required=True)
    speech_read.add_argument("--binding", required=True)
    speech_read.add_argument("--binding-sha256", required=True)
    speech_read.add_argument("--split-name", required=True)
    speech_read.add_argument("--output", required=True)
    speech_read.set_defaults(func=_cli_speech_native_read)

    args = parser.parse_args(argv)
    return args.func(args)
