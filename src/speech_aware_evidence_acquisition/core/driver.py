"""The ONE experiment driver: config + plan -> gate -> run -> outputs (R0).

Every Stage-2 run (R0 smoke, R1 reproduction, X probes, 2B deep digs) goes
through run_experiment(); an experiment differs from another only by its four
config fragments and, rarely, a newly registered component. RUNTIME PHASE:
this module never imports data.references.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Callable, Mapping

from ..contracts import ExecutionPlan
from ..data.lock import asset_dir
from ..e0.artifacts import REPO_ROOT
from .base import (
    CARRIERS,
    EVIDENCE_SOURCES,
    POLICIES,
    SCORERS,
    TRANSPORTS,
    CoreError,
    PayloadBindingContext,
    RunResult,
    SampleContext,
)
from .bundle import (
    STATUS_ABORTED,
    STATUS_COMPLETED,
    abort_attempt_if_opened,
    build_manifest,
    finalize_bundle,
)
from .config import ComposedConfig, compose, protocol_hash
from .evidence import rotated_mismatch
from .model import FrozenCoreAdapter
from .split_receipt import load_verified_split
from .tracing import TraceSink


def load_split(
    repo_root: Path, split_name: str, lock: Mapping[str, object], root: Path
) -> tuple[set[str], str, str]:
    """Thin wrapper: strictly parsed AND live-recomputed split (delegates to
    :func:`core.split_receipt.load_verified_split`; see that module for the
    trust boundary this closes)."""

    verified = load_verified_split(repo_root, split_name, lock, root)
    return set(verified.ids), verified.identity_hash, verified.split_role


def run_experiment(
    composed: ComposedConfig,
    plan: ExecutionPlan,
    gate: object,
    lock: Mapping[str, object],
    root: Path,
    run_dir: Path,
    transport: Callable[[bytes], bytes],
    repo_root: Path = REPO_ROOT,
) -> RunResult:
    values = composed.values
    arm = str(values["arm"])
    verified_split = load_verified_split(repo_root, str(values["split_name"]), lock, root)
    sample_ids = set(verified_split.ids)
    split_hash = verified_split.identity_hash
    receipt_split_role = verified_split.split_role
    if plan.split_identity_hash != split_hash:
        raise CoreError(
            "plan split identity hash does not match the frozen splits receipt "
            f"for split {values['split_name']!r}"
        )
    if plan.split_role != receipt_split_role:
        raise CoreError(
            f"plan split role {plan.split_role!r} does not match the frozen splits "
            f"receipt split role {receipt_split_role!r} for split {values['split_name']!r}"
        )
    if str(values["carrier_lock_key"]) != plan.carrier_lock_key:
        raise CoreError(
            f"plan carrier_lock_key {plan.carrier_lock_key!r} does not match the "
            f"composed config carrier {values['carrier_lock_key']!r}"
        )
    expected_protocol = protocol_hash(composed.config_hash, arm, split_hash)
    if plan.protocol_hash != expected_protocol:
        raise CoreError(
            f"plan protocol hash {plan.protocol_hash!r} does not match the composed "
            f"config/arm/split protocol hash {expected_protocol!r}"
        )
    loader = CARRIERS.resolve(str(values["carrier_lock_key"]))
    samples = [s for s in loader(lock, root) if s.sample_id in sample_ids]
    if {s.sample_id for s in samples} != sample_ids:
        raise CoreError("split ids missing from the carrier's loaded samples")
    source = EVIDENCE_SOURCES.resolve(str(values.get("evidence_source", "none")))
    evidence_by_sample = {
        s.sample_id: source(lock, root, s.sample_id) for s in samples
    }
    if values.get("evidence_mismatch", False):
        evidence_by_sample = rotated_mismatch(evidence_by_sample)
    policy = POLICIES.resolve(str(values["policy"]))
    sink = TraceSink(run_dir, plan.run_id)
    # Payload<->plan<->split binding context (R0 repair T3, I3/I4): built here,
    # from exactly the verified split ids and the same loader's SampleRef
    # facts already used above to validate the carrier's loaded samples --
    # never from anything a payload later claims about itself.
    carrier_root = asset_dir(lock, str(values["carrier_lock_key"]), root)
    binding = PayloadBindingContext(
        carrier_lock_key=str(values["carrier_lock_key"]),
        allowed_sample_ids=frozenset(sample_ids),
        sample_facts={s.sample_id: (s.audio_seconds, s.sample_rate_hz) for s in samples},
        data_root=Path(root),
        carrier_root=carrier_root,
    )
    adapter = FrozenCoreAdapter(
        gate=gate, plan=plan, arm=arm, transport=transport, sink=sink, binding=binding
    )
    outputs_path = Path(run_dir) / f"{plan.run_id}.outputs.jsonl"
    try:
        outputs_handle = outputs_path.open("x", encoding="utf-8", newline="\n")
    except FileExistsError as error:
        raise CoreError(
            f"outputs file already exists: {outputs_path}; a re-run must use a "
            "fresh attempt directory, not overwrite a prior attempt's outputs"
        ) from error
    with outputs_handle as outputs:
        for index, sample in enumerate(sorted(samples, key=lambda s: s.sample_id), start=1):
            request_id_base = f"req-{index:04d}"
            view = sample.runtime_view()
            sink.emit(
                "OBS",
                f"{request_id_base}/obs",
                {
                    "obs_speech_ref": view["speech_ref"],
                    "obs_audio_seconds": view["audio_seconds"],
                },
            )
            evidence = evidence_by_sample.get(sample.sample_id, [])
            if evidence:
                sink.emit(
                    "ORG",
                    f"{request_id_base}/org",
                    {
                        "org_evidence_count": len(evidence),
                        "org_source_lock_keys": sorted(
                            {item.provenance["lock_key"] for item in evidence}
                        ),
                    },
                )
                sink.emit(
                    "SUPPLY",
                    f"{request_id_base}/supply",
                    {
                        "supply_evidence_ids": [item.evidence_id for item in evidence],
                        "supply_content_bytes": sum(
                            len(item.content.encode("utf-8")) for item in evidence
                        ),
                    },
                )
            ctx = SampleContext(
                sample=sample,
                evidence=evidence,
                adapter=adapter,
                sink=sink,
                arm=arm,
                task_instruction=str(values["task_instruction"]),
                decoding_params=dict(values.get("decoding_params", {})),
                request_id_base=request_id_base,
                retrieval_query=values.get("retrieval_query"),
            )
            outcome = policy.run_sample(ctx)
            outputs.write(
                json.dumps(
                    {
                        "request_id": request_id_base,
                        "sample_id": outcome.sample_id,
                        "carrier_lock_key": sample.carrier_lock_key,
                        "arm": arm,
                        "text": outcome.text,
                        "admitted": outcome.admitted,
                        "request_sha256": outcome.request_sha256,
                        "response_sha256": outcome.response_sha256,
                        "response_text_sha256": outcome.response_text_sha256,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
                + "\n"
            )
    manifest_hash = sink.close()
    return RunResult(
        run_id=plan.run_id,
        arm=arm,
        outputs_path=outputs_path,
        trace_manifest_hash=manifest_hash,
        cost=adapter.cost_summary(),
    )


def run_experiment_bundled(
    composed: ComposedConfig,
    plan: ExecutionPlan,
    gate: object,
    lock: Mapping[str, object],
    root: Path,
    run_dir: Path,
    transport: Callable[[bytes], bytes],
    *,
    repo_root: Path = REPO_ROOT,
    session_receipt_path: Path | None = None,
) -> Path:
    """R0 repair T6 (I7): run one attempt and ALWAYS produce a run manifest --
    the audit trail, not a raised exception alone, is the record of what
    happened.

    On success: ``run_experiment`` runs to completion and this returns the
    path to a manifest with status COMPLETED, binding every artifact it
    produced.

    On any failure: the attempt is marked ABORTED on disk (if it was ever
    opened at all -- ``core.bundle.abort_attempt_if_opened`` is a no-op
    otherwise) with the failure's own message as the reason, a manifest is
    still durably written to the SAME deterministic path
    (``run_dir / f"{plan.run_id}.run-manifest.json"``) with status ABORTED
    binding whatever partial artifacts genuinely exist, and then the
    original exception is RE-RAISED (this function does not swallow errors
    -- callers that need the manifest path after a failure can reconstruct
    it from ``run_dir``/``plan.run_id``, or use ``core.bundle.verify_bundle``
    against that path directly). Either way, an ABORTED manifest can never
    later be finalized as COMPLETED (I7; see ``core.bundle.finalize_bundle``).
    """

    verified_split = load_verified_split(repo_root, str(composed.values["split_name"]), lock, root)
    try:
        result = run_experiment(
            composed, plan, gate, lock, root, run_dir, transport, repo_root=repo_root
        )
    except Exception as error:
        abort_attempt_if_opened(root, plan.run_id, plan.attempt_id, reason=str(error))
        build_manifest(
            repo_root=repo_root,
            data_root=root,
            composed=composed,
            plan=plan,
            verified_split=verified_split,
            session_receipt_path=session_receipt_path,
            run_dir=run_dir,
            status=STATUS_ABORTED,
            failure_reason=str(error),
            result=None,
        )
        raise
    return build_manifest(
        repo_root=repo_root,
        data_root=root,
        composed=composed,
        plan=plan,
        verified_split=verified_split,
        session_receipt_path=session_receipt_path,
        run_dir=run_dir,
        status=STATUS_COMPLETED,
        failure_reason=None,
        result=result,
    )


def _cli_score(args: argparse.Namespace) -> int:
    from ..data.lock import data_root, load_lock, umbrella_lock_path

    lock = load_lock(umbrella_lock_path())
    root = data_root()
    for name in args.scorers.split(","):
        scores = SCORERS.resolve(name.strip())(Path(args.outputs), lock, root)
        print(json.dumps({name.strip(): scores["aggregate"]}, indent=2, sort_keys=True))
    return 0


def _cli_run(args: argparse.Namespace) -> int:
    from ..contracts import FrozenCoreGate
    from ..data.lock import data_root, load_lock, umbrella_lock_path
    from .session import attach_session, load_runtime_receipt

    lock = load_lock(umbrella_lock_path())
    root = data_root()
    composed = compose(REPO_ROOT, args.model, args.dataset, args.baseline, args.experiment)
    plan = ExecutionPlan(**json.loads(Path(args.plan).read_text(encoding="utf-8")))
    runtime_root = Path(args.runtime_root)
    gate = FrozenCoreGate.for_study_repo(REPO_ROOT, root, runtime_root)
    # R0 repair T5 (I5): the runtime receipt is the SAME committed file the
    # gate itself re-hashes. attach_session binds this run to a session
    # receipt whose binary/model identity, live pid, PROCESS IMAGE identity
    # (T5 fix-1 -- pid liveness alone proves nothing) and loopback host it
    # independently re-verifies against that file -- a resident server
    # started out of band is only usable if it can PROVE it is the
    # receipt-pinned process, never merely because its base_url matches the
    # config.
    runtime_receipt = load_runtime_receipt(REPO_ROOT / "docs" / "receipts" / "runtime.json")
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
    manifest_path = run_experiment_bundled(
        composed, plan, gate, lock, root, Path(args.run_dir), transport,
        session_receipt_path=Path(args.session_receipt),
    )
    print(json.dumps({"run_id": plan.run_id, "manifest": str(manifest_path)}, indent=2))
    return 0


def _cli_finalize(args: argparse.Namespace) -> int:
    from ..data.lock import data_root, load_lock, umbrella_lock_path

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
    score = sub.add_parser("score", help="model-free scoring of recorded outputs")
    score.add_argument("--outputs", required=True)
    score.add_argument("--scorers", default="asr-wer")
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
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
