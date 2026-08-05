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
from ..e0.artifacts import REPO_ROOT
from ..data.splits import SPLITS_RECEIPT_NAME
from .base import (
    CARRIERS,
    EVIDENCE_SOURCES,
    POLICIES,
    SCORERS,
    TRANSPORTS,
    CoreError,
    RunResult,
    SampleContext,
)
from .config import ComposedConfig, compose, protocol_hash
from .evidence import rotated_mismatch
from .model import FrozenCoreAdapter
from .tracing import TraceSink


def load_split(repo_root: Path, split_name: str) -> tuple[set[str], str, str]:
    receipt_path = Path(repo_root) / "docs" / "receipts" / SPLITS_RECEIPT_NAME
    if not receipt_path.is_file():
        raise CoreError(f"splits receipt missing: {receipt_path} (freeze splits first)")
    document = json.loads(receipt_path.read_text(encoding="utf-8"))
    try:
        split = document["splits"][split_name]
    except KeyError:
        raise CoreError(
            f"unknown split {split_name!r}; frozen splits: {sorted(document['splits'])}"
        ) from None
    ids = {prefixed.split("/", 1)[1] for prefixed in split["ids"]}
    return ids, split["identity_hash"], split["split_role"]


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
    sample_ids, split_hash, receipt_split_role = load_split(repo_root, str(values["split_name"]))
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
    adapter = FrozenCoreAdapter(
        gate=gate, plan=plan, arm=arm, transport=transport, sink=sink
    )
    outputs_path = Path(run_dir) / f"{plan.run_id}.outputs.jsonl"
    with outputs_path.open("w", encoding="utf-8", newline="\n") as outputs:
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

    lock = load_lock(umbrella_lock_path())
    root = data_root()
    composed = compose(REPO_ROOT, args.model, args.dataset, args.baseline, args.experiment)
    plan = ExecutionPlan(**json.loads(Path(args.plan).read_text(encoding="utf-8")))
    gate = FrozenCoreGate.for_study_repo(REPO_ROOT, root, Path(args.runtime_root))
    transport_factory = TRANSPORTS.resolve(str(composed.values["transport"]))
    transport = transport_factory(composed.values, root)
    result = run_experiment(
        composed, plan, gate, lock, root, Path(args.run_dir), transport
    )
    print(json.dumps({"run_id": result.run_id, "cost": dict(result.cost)}, indent=2))
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
    run.set_defaults(func=_cli_run)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
