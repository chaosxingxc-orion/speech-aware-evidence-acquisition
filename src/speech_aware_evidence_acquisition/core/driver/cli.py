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
import os
import sys
from pathlib import Path
from typing import Mapping

from ...contracts import ExecutionPlan
from ...data.lock import data_root, load_lock, umbrella_lock_path
from ...data.slurp import load_slurp_train_material
from ...e0.artifacts import REPO_ROOT, write_json_artifact

# rails.probes.pslu_flight must stay function-local in this module: a module-level
# import closes the cycle rails/__init__ -> rails.consumption -> core.retrieval ->
# core/__init__ -> core.driver -> this module -> rails.probes.pslu_flight ->
# rails.adapters.slurp -> rails.consumption (partially initialized).
from ..base import SCORERS
from ..bundle import finalize_bundle, verify_bundle
from ..config import (
    compose,
    d1_evidence_supplement_relpath,
    d1_evidence_supplement_sha256,
    d1_media_supplement_relpath,
    d1_media_supplement_sha256,
    model_lock_key,
    model_materialization_root,
    resolve_runtime_receipt_path,
    runtime_receipt_relpath,
)
from ..resources import resolve_resource_sampler
from ..configured_transport import build_configured_transport
from ..scorers import score_bundle
from .bundled import run_experiment_bundled
from .smoke import _cli_smoke
from .speech_native import (
    _cli_speech_native_action_audit,
    _cli_speech_native_engine_audit,
    _cli_speech_native_finalize_from_disk,
    _cli_speech_native_prompt_audit,
    _cli_speech_native_profile,
    _cli_speech_native_read,
)


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
    """Compatibility wrapper for the shared preprocess stop-chain authority."""

    from ..preparation_feature_provenance import load_preprocess_stop_chain

    return load_preprocess_stop_chain(
        session_receipt_path=session_receipt_path,
        stop_receipt_path=stop_receipt_path,
        runtime_receipt=runtime_receipt,
    )


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
        raise ValueError(
            f"speech packet promotion receipt already exists: {receipt_output}"
        )
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
        or any(
            character
            not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
            for character in args.dataset
        )
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
        raise ValueError(
            "speech packet promotion requires a preprocess runtime receipt"
        )
    session, stop = _load_preprocess_stop_chain(
        session_receipt_path=Path(args.session_receipt),
        stop_receipt_path=Path(args.stop_receipt),
        runtime_receipt=runtime_receipt,
    )
    gguf_files = runtime_receipt.get("gguf_files")
    if not isinstance(gguf_files, list):
        raise ValueError("preprocess runtime receipt gguf_files must be a list")
    decoder = [
        entry
        for entry in gguf_files
        if "mmproj" not in Path(str(entry.get("path"))).name.lower()
    ]
    mmproj = [
        entry
        for entry in gguf_files
        if "mmproj" in Path(str(entry.get("path"))).name.lower()
    ]
    if len(decoder) != 1 or len(mmproj) != 1:
        raise ValueError(
            "preprocess runtime receipt must bind exactly one decoder and one mmproj"
        )
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
        raise ValueError(
            f"speech packet promotion receipt already exists: {output}"
        ) from error
    print(json.dumps({"receipt": str(output), "count": len(packets)}, indent=2))
    return 0


def _cli_promote_pinned_roster_speech_packets(args: argparse.Namespace) -> int:
    """Promote one pinned carrier roster without a carrier-specific loader."""

    from ..packet_promotion import promote_pinned_roster_legacy_cache

    receipt = promote_pinned_roster_legacy_cache(
        promotion_plan=Path(args.promotion_plan),
        promotion_plan_sha256=args.promotion_plan_sha256,
    )
    print(
        json.dumps(
            {
                "promotion_plan": str(args.promotion_plan),
                "count": receipt["count"],
                "schema": receipt["schema"],
            },
            sort_keys=True,
        )
    )
    return 0


def _cli_extend_speech_native_binding(args: argparse.Namespace) -> int:
    """Build a split and/or knowledge successor with the existing selector."""

    from ...rails.probes.pslu_flight import (  # noqa: PLC0415 (import-cycle guard)
        audit_speech_native_scale_capacity,
        build_data_derived_decision_graph,
        build_speech_native_information_audit,
        extend_speech_native_binding,
        refine_speech_native_binding_knowledge,
    )

    parent_path = Path(args.parent_binding).resolve()
    output_path = Path(args.output).resolve() if args.output is not None else None
    graph_output_path = (
        Path(args.decision_graph_output).resolve()
        if args.decision_graph_output is not None
        else None
    )
    information_audit_output_path = (
        Path(args.information_audit_output).resolve()
        if args.information_audit_output is not None
        else None
    )
    scale_capacity_audit_output_path = (
        Path(args.scale_capacity_audit_output).resolve()
        if args.scale_capacity_audit_output is not None
        else None
    )
    if output_path is not None and output_path.exists():
        raise ValueError(f"speech-native binding output already exists: {output_path}")
    if graph_output_path is not None and graph_output_path.exists():
        raise ValueError(
            f"speech-native decision graph output already exists: {graph_output_path}"
        )
    if (
        information_audit_output_path is not None
        and information_audit_output_path.exists()
    ):
        raise ValueError(
            "speech-native information audit output already exists: "
            f"{information_audit_output_path}"
        )
    if (
        scale_capacity_audit_output_path is not None
        and scale_capacity_audit_output_path.exists()
    ):
        raise ValueError(
            "speech-native scale capacity audit output already exists: "
            f"{scale_capacity_audit_output_path}"
        )
    try:
        parent = json.loads(parent_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(
            f"cannot read speech-native parent binding {parent_path}: {error}"
        ) from error
    if not isinstance(parent, Mapping):
        raise ValueError("speech-native parent binding must be a JSON object")
    split_requested = args.split_name is not None or args.per_scenario is not None
    if (args.split_name is None) != (args.per_scenario is None):
        raise ValueError(
            "speech-native split extension requires both --split-name and "
            "--per-scenario"
        )
    binding_successor_requested = split_requested or args.knowledge_policy is not None
    capacity_values = (
        args.existing_memory_split,
        args.cumulative_query_count,
        args.memory_query_count,
        args.holdout_query_count,
    )
    capacity_requested = (
        scale_capacity_audit_output_path is not None
        or any(value is not None for value in capacity_values)
    )
    if capacity_requested and (
        scale_capacity_audit_output_path is None
        or any(value is None for value in capacity_values)
    ):
        raise ValueError(
            "speech-native scale capacity audit requires its output, existing "
            "memory split, cumulative count, memory count, and holdout count"
        )
    if (
        not binding_successor_requested
        and graph_output_path is None
        and information_audit_output_path is None
        and not capacity_requested
    ):
        raise ValueError(
            "speech-native binding needs a split extension or knowledge refinement"
        )
    if binding_successor_requested and output_path is None:
        raise ValueError("speech-native split or knowledge successor requires --output")
    if (
        (graph_output_path is not None or information_audit_output_path is not None)
        and args.knowledge_policy is None
        and not isinstance(parent.get("knowledge_revision"), Mapping)
    ):
        raise ValueError(
            "speech-native decision graph requires an existing or requested "
            "data-derived knowledge refinement"
        )

    material = load_slurp_train_material(
        load_lock(umbrella_lock_path()),
        data_root(),
        media_validation_workers=args.workers,
    )

    successor = dict(parent)
    if split_requested:
        successor = extend_speech_native_binding(
            successor,
            material,
            seed=args.seed,
            split_name=args.split_name,
            per_scenario=args.per_scenario,
            isolate_parent_query_speakers=(not args.allow_parent_query_speaker_overlap),
        )
    if args.knowledge_policy is not None:
        successor = refine_speech_native_binding_knowledge(
            successor,
            material,
            seed=args.seed,
            policy_id=args.knowledge_policy,
        )
    graph_artifact_sha256 = None
    information_audit_artifact_sha256 = None
    information_audit_status = None
    scale_capacity_audit_artifact_sha256 = None
    scale_capacity_status = None
    if graph_output_path is not None or information_audit_output_path is not None:
        graph = build_data_derived_decision_graph(
            successor,
            material,
            graph_id=args.decision_graph_id,
            maximum_boundaries=args.maximum_boundaries,
            boundary_policy_id=args.boundary_policy,
        )
        if graph_output_path is not None:
            graph_artifact_sha256 = write_json_artifact(
                graph_output_path, graph.as_json()
            )
        if information_audit_output_path is not None:
            information_audit = build_speech_native_information_audit(
                successor,
                material,
                graph,
            )
            information_audit_artifact_sha256 = write_json_artifact(
                information_audit_output_path,
                information_audit,
            )
            admission = information_audit.get("admission")
            if not isinstance(admission, Mapping) or not isinstance(
                admission.get("status"), str
            ):
                raise ValueError("speech-native information audit lacks admission")
            information_audit_status = admission["status"]
    if capacity_requested:
        assert scale_capacity_audit_output_path is not None
        assert args.existing_memory_split is not None
        assert args.cumulative_query_count is not None
        assert args.memory_query_count is not None
        assert args.holdout_query_count is not None
        scale_capacity_audit = audit_speech_native_scale_capacity(
            successor,
            material,
            seed=args.seed,
            existing_memory_split_name=args.existing_memory_split,
            cumulative_query_count=args.cumulative_query_count,
            memory_query_count=args.memory_query_count,
            holdout_query_count=args.holdout_query_count,
        )
        scale_capacity_audit_artifact_sha256 = write_json_artifact(
            scale_capacity_audit_output_path,
            scale_capacity_audit,
        )
        capacity_admission = scale_capacity_audit.get("admission")
        if not isinstance(capacity_admission, Mapping) or not isinstance(
            capacity_admission.get("status"), str
        ):
            raise ValueError("speech-native scale capacity audit lacks admission")
        scale_capacity_status = capacity_admission["status"]
    artifact_sha256 = (
        write_json_artifact(output_path, successor) if output_path is not None else None
    )
    extension_audit = successor.get("extension_audit")
    knowledge_revision = successor.get("knowledge_revision")
    if split_requested and not isinstance(extension_audit, Mapping):
        raise ValueError("speech-native successor lacks its extension audit")
    if args.knowledge_policy is not None and not isinstance(
        knowledge_revision, Mapping
    ):
        raise ValueError("speech-native successor lacks its knowledge revision")
    print(
        json.dumps(
            {
                "output": str(output_path) if output_path is not None else None,
                "artifact_sha256": artifact_sha256,
                "binding_sha256": successor.get("binding_sha256"),
                "query_count": (
                    extension_audit.get("query_count")
                    if isinstance(extension_audit, Mapping)
                    else None
                ),
                "parent_query_speaker_overlap_count": (
                    extension_audit.get("parent_query_speaker_overlap_count")
                    if isinstance(extension_audit, Mapping)
                    else None
                ),
                "knowledge_policy_id": (
                    knowledge_revision.get("policy_id")
                    if isinstance(knowledge_revision, Mapping)
                    else None
                ),
                "decision_graph_output": (
                    str(graph_output_path) if graph_output_path is not None else None
                ),
                "decision_graph_artifact_sha256": graph_artifact_sha256,
                "information_audit_output": (
                    str(information_audit_output_path)
                    if information_audit_output_path is not None
                    else None
                ),
                "information_audit_artifact_sha256": (
                    information_audit_artifact_sha256
                ),
                "information_audit_status": information_audit_status,
                "scale_capacity_audit_output": (
                    str(scale_capacity_audit_output_path)
                    if scale_capacity_audit_output_path is not None
                    else None
                ),
                "scale_capacity_audit_artifact_sha256": (
                    scale_capacity_audit_artifact_sha256
                ),
                "scale_capacity_status": scale_capacity_status,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _scoring_cli_context(args):
    """Resolve explicit worker paths while retaining historical CLI defaults."""
    from ...data.lock import data_root, load_lock, umbrella_lock_path

    lock_path = getattr(args, "lock_path", None)
    root_path = getattr(args, "data_root", None)
    repo_path = getattr(args, "repo_root", None)
    if repo_path and Path(repo_path).resolve() != Path(__file__).resolve().parents[4]:
        raise ValueError("scoring repo_root must match the imported source checkout")
    lock = load_lock(Path(lock_path) if lock_path else umbrella_lock_path())
    root = Path(root_path) if root_path else data_root()
    options = {"repo_root": Path(repo_path)} if repo_path else {}
    return lock, root, options


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

    lock, root, context_options = _scoring_cli_context(args)
    if args.manifest:
        bundle = verify_bundle(Path(args.manifest))
        results = score_bundle(bundle, lock, root, **context_options)
        print(
            json.dumps(
                {
                    "manifest": str(Path(args.manifest)),
                    "verified": True,
                    "scores": (
                        results
                        if args.include_per_sample
                        else {
                            name: result["aggregate"]
                            for name, result in results.items()
                        }
                    ),
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
                {
                    "verified": False,
                    "scorer": name.strip(),
                    "aggregate": scores["aggregate"],
                },
                indent=2,
                sort_keys=True,
            )
        )
    return 0


def _cli_score_batch(args: argparse.Namespace) -> int:
    """Run complete authoritative scorer jobs with bounded outer parallelism."""

    from ..scoring_batch import load_score_jobs, run_score_batch

    jobs = load_score_jobs(
        Path(args.jobs),
        require_operation=args.per_job_operation,
        require_ledger_cells=args.finalize,
    )
    summary = run_score_batch(
        jobs,
        output_dir=Path(args.output_dir),
        max_workers=args.workers,
        operation=(
            "per-job"
            if args.per_job_operation
            else ("finalize" if args.finalize else "score")
        ),
        include_per_sample=args.include_per_sample,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["failed"] == 0 else 1


def _cli_run(args: argparse.Namespace) -> int:
    from ...contracts import FrozenCoreGate
    from ...data.lock import data_root, load_lock, umbrella_lock_path
    from ..session import attach_session, load_runtime_receipt

    lock = load_lock(umbrella_lock_path())
    root = data_root()
    composed = compose(
        REPO_ROOT, args.model, args.dataset, args.baseline, args.experiment
    )
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
        model_root=(
            Path(configured_model_root) if configured_model_root is not None else None
        ),
        d1_media_supplement_relpath=d1_media_supplement_relpath(composed.values),
        d1_media_supplement_sha256=d1_media_supplement_sha256(composed.values),
        d1_evidence_supplement_relpath=d1_evidence_supplement_relpath(composed.values),
        d1_evidence_supplement_sha256=d1_evidence_supplement_sha256(composed.values),
    )
    # R0 repair T5 (I5): the runtime receipt is the SAME committed file the
    # gate itself re-hashes. attach_session binds this run to a session
    # receipt whose binary/model identity, live pid, PROCESS IMAGE identity
    # (T5 fix-1 -- pid liveness alone proves nothing) and loopback host it
    # independently re-verifies against that file -- a resident server
    # started out of band is only usable if it can PROVE it is the
    # receipt-pinned process, never merely because its base_url matches the
    # config.
    runtime_receipt = load_runtime_receipt(
        resolve_runtime_receipt_path(REPO_ROOT, composed.values)
    )
    session = attach_session(
        Path(args.session_receipt),
        runtime_receipt=runtime_receipt,
        runtime_root=runtime_root,
    )
    transport = build_configured_transport(
        composed.values,
        root,
        repo_root=REPO_ROOT,
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
        composed,
        plan,
        gate,
        lock,
        root,
        Path(args.run_dir),
        transport,
        session_receipt_path=Path(args.session_receipt),
        resource_sampler=resolve_resource_sampler(),
    )
    print(json.dumps({"run_id": plan.run_id, "manifest": str(manifest_path)}, indent=2))
    return 0


def _cli_finalize(args: argparse.Namespace) -> int:
    lock, root, context_options = _scoring_cli_context(args)
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
        **context_options,
    )
    extra = {}
    if getattr(args, "include_per_sample", False):
        # Finalization already wrote the full registered scorer result. Read that
        # artifact; never invoke a scorer again to expose its per-sample rows.
        extra["score_details"] = json.loads(Path(result.scores_path).read_text(encoding="utf-8"))
    print(
        json.dumps(
            {
                "manifest": str(Path(args.manifest)),
                "verified": True,
                "scores": str(result.scores_path),
                "ledger_markdown": str(result.ledger_markdown_path),
                "ledger_json": str(result.ledger_json_path),
                "mlflow_run": result.mlflow_run_id,
                "attempt_state": result.attempt_state,
                **extra,
            },
            indent=2,
        )
    )
    return 0


def _cli_prepare_semantic_knowledge(args: argparse.Namespace) -> int:
    """Build or release one registered source-bound semantic knowledge store."""
    from ..semantic_knowledge_preparation import prepare_semantic_knowledge_store

    receipt = prepare_semantic_knowledge_store(
        Path(args.registration),
        repo_root=Path(args.repo_root),
        data_root=Path(args.data_root),
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


def _cli_prepare_semantic_authoring_support(args: argparse.Namespace) -> int:
    """Prepare registered, model-free SLURP authoring support."""
    from ..semantic_authoring_support import (
        prepare_slurp_semantic_authoring_support,
    )

    receipt = prepare_slurp_semantic_authoring_support(
        Path(args.config),
        repo_root=Path(args.repo_root),
        data_root=Path(args.data_root),
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


def _cli_prepare_state_source(args: argparse.Namespace) -> int:
    """Prepare one registered deterministic source through the common cache."""
    from ..bundle.git_commit import require_clean_study_repo
    from ..bundle.hypothesis_source import prepare_hypothesis_source

    repo_root = Path(args.repo_root).resolve()
    if repo_root != REPO_ROOT.resolve():
        raise ValueError("prepare-state-source repo_root must match the imported checkout")
    commit = require_clean_study_repo(repo_root)
    receipt = prepare_hypothesis_source(
        registration_path=Path(args.registration),
        data_root=Path(args.data_root),
        implementation_commit=commit,
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


def _cli_revalidate_request_fit(args: argparse.Namespace) -> int:
    """Revalidate a registered full-roster fit without endpoint access."""
    from ..bundle.git_commit import require_clean_study_repo
    from ..flight.factory import build_flight_runtime
    from ..preparation import canonical_bytes, digest
    from ..preparation_fit import revalidate_phase_fit

    repo = Path(args.repo_root).resolve()
    if repo != REPO_ROOT.resolve():
        raise ValueError("fit revalidation repo_root must match the imported checkout")
    require_clean_study_repo(repo)
    path = Path(args.registration).resolve()
    if not path.is_relative_to(repo):
        raise ValueError("fit revalidation registration must be committed in repo_root")
    raw = path.read_bytes()
    registration = json.loads(raw)
    if raw != canonical_bytes(registration):
        raise ValueError("fit revalidation registration must use canonical JSON bytes")
    runtime = build_flight_runtime(
        repo, Path(args.data_root), **registration["flight"],
        runtime_root=Path(args.runtime_root), lock_path=Path(args.lock_path),
    )
    receipt = revalidate_phase_fit(
        runtime, registration=registration, registration_sha256=digest(registration),
        data_root=Path(args.data_root),
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


def _cli_build_delivery(args: argparse.Namespace) -> int:
    """Build one verified phase-delivery derivative through the shared API."""

    from ..bundle.delivery import build_delivery_bundle

    repo_root = Path(args.repo_root).resolve()
    imported_root = REPO_ROOT.resolve()
    if repo_root != imported_root:
        raise ValueError(
            "build-delivery repo_root must match the imported source checkout"
        )
    manifest = build_delivery_bundle(
        parent_manifest=Path(args.parent_manifest),
        repo_root=repo_root,
        experiment_path=Path(args.experiment_path),
        data_root=Path(args.data_root),
        derivative_cell_id=args.derivative_cell_id,
        output_dir=Path(args.output_dir),
    )
    print(
        json.dumps(
            {
                "manifest": str(manifest),
                "derivative_cell_id": args.derivative_cell_id,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _cli_flight(args: argparse.Namespace) -> int:
    """C4c: run one arm/carrier through the ``core.flight.FlightRuntime``
    harness -- ``preflight -> preprocess -> serve -> run_phases -> seal ->
    score`` (``--dry-run`` stops after ``preflight``). The adapter is
    resolved from the dataset fragment's own ``carrier_lock_key`` through
    ``data.carriers.carrier_task_layout(...).task_kind`` -- today exactly
    the two registered carriers this study's ``rails.adapters`` ship an
    adapter for (``speech-tool-use`` -> ``Audio2ToolAdapter``, ``slot-slu``
    -> ``SlurpAdapter``); a carrier with no task layer (e.g. the ``earnings*``
    transcription carriers) or an unregistered ``task_kind`` is refused here
    -- construct ``core.flight.runtime.FlightRuntime`` directly with a custom
    ``adapter_factory`` for any other carrier.
    """

    from ...data.carriers import carrier_task_layout
    from ...data.lock import data_root, load_lock, umbrella_lock_path
    from ...rails.adapters.audio2tool import Audio2ToolAdapter
    from ...rails.adapters.slurp import SlurpAdapter
    from ..flight.runtime import FlightRuntime
    from .smoke import fresh_attempt_id

    lock = load_lock(umbrella_lock_path())
    root = data_root()
    composed = compose(REPO_ROOT, args.model, args.dataset, args.baseline, args.experiment)
    from ..bundle.delivery_replay import validate_phase_delivery_sources

    phase_declarations = validate_phase_delivery_sources(
        composed.values,
        parent_fragments={
            "model_fragment": args.model,
            "dataset_fragment": args.dataset,
            "baseline_fragment": args.baseline,
        },
    )
    if phase_declarations and not args.dry_run and not args.seal_only:
        raise ValueError(
            "phase delivery declarations require --seal-only or --dry-run; "
            "raw terminal phase output must be derived before scoring"
        )
    carrier_lock_key = composed.values.get("carrier_lock_key")
    if not isinstance(carrier_lock_key, str) or not carrier_lock_key:
        raise ValueError("dataset fragment must declare a non-empty carrier_lock_key")
    task_kind = carrier_task_layout(carrier_lock_key).task_kind
    adapter_classes = {
        "speech-tool-use": Audio2ToolAdapter,
        "slot-slu": SlurpAdapter,
    }
    adapter_class = adapter_classes.get(task_kind)
    if adapter_class is None:
        raise ValueError(
            f"no flight adapter registered for task_kind {task_kind!r} (carrier "
            f"{carrier_lock_key!r}); registered task kinds: {sorted(adapter_classes)}"
        )

    attempt_id = args.attempt_id or fresh_attempt_id()
    runtime = FlightRuntime(
        REPO_ROOT,
        root,
        model=args.model,
        dataset=args.dataset,
        baseline=args.baseline,
        experiment=args.experiment,
        run_id=args.run_id,
        attempt_id=attempt_id,
        runtime_root=Path(args.runtime_root),
        adapter_factory=lambda lock_, root_: adapter_class(lock_, root_, repo_root=REPO_ROOT),
        lock=lock,
        campaign_active=bool(args.campaign_active),
    )

    if args.dry_run:
        preflight_receipt = runtime.preflight()
        print(
            json.dumps(
                {
                    "run_id": args.run_id,
                    "attempt_id": attempt_id,
                    "stage": "preflight",
                    "dry_run": True,
                    "receipt": preflight_receipt,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    runtime.preflight()
    runtime.preprocess()
    runtime.serve()
    runtime.run_phases()
    runtime.seal(defer_scoring=bool(args.seal_only or phase_declarations))
    if not args.seal_only:
        runtime.score(max_workers=args.max_workers)
    print(
        json.dumps(
            {
                "run_id": args.run_id,
                "attempt_id": attempt_id,
                "receipts": runtime.receipts.as_json(),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    from ...rails.probes.pslu_flight import (  # noqa: PLC0415 (import-cycle guard)
        SPEECH_NATIVE_BOUNDARY_POLICY_IDS,
        SPEECH_NATIVE_KNOWLEDGE_POLICY_IDS,
    )

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
        "--scorers",
        default="asr-wer",
        help="comma-separated scorer names (--outputs mode only)",
    )
    score.add_argument(
        "--include-per-sample",
        action="store_true",
        help=(
            "with --manifest, include each registered scorer's existing per-sample "
            "rows alongside its aggregate; default output remains aggregate-only"
        ),
    )
    for path_name in ("repo-root", "data-root", "lock-path"):
        score.add_argument("--" + path_name, default=None)
    score.set_defaults(func=_cli_score)
    score_batch = sub.add_parser(
        "score-batch",
        help=(
            "run independent, complete --manifest scoring jobs concurrently; "
            "official scorers remain single-process inside each job"
        ),
    )
    score_batch.add_argument(
        "--jobs",
        required=True,
        help=(
            "JSONL file with exact fields job_id and manifest; relative manifest "
            "paths resolve beside this file"
        ),
    )
    score_batch.add_argument(
        "--output-dir",
        required=True,
        help="new or empty directory for isolated score results and batch-summary.json",
    )
    score_batch.add_argument(
        "--workers",
        type=int,
        default=max(1, min(4, os.cpu_count() or 1)),
        help="maximum number of complete scorer processes to run concurrently",
    )
    score_batch.add_argument(
        "--include-per-sample",
        action="store_true",
        help=(
            "ask each complete score job for existing per-sample rows; no job is "
            "sharded or scored again"
        ),
    )
    score_operation = score_batch.add_mutually_exclusive_group()
    score_operation.add_argument(
        "--finalize",
        action="store_true",
        help=(
            "run the existing authoritative finalize command per complete manifest; "
            "this scores exactly once, writes scores, and settles each attempt"
        ),
    )
    score_operation.add_argument(
        "--per-job-operation",
        action="store_true",
        help=(
            "require an operation field on every JSONL job and run that complete "
            "manifest through score or finalize as declared; useful when a sealed "
            "recovery artifact is scoreable but no longer finalizable"
        ),
    )
    score_batch.set_defaults(func=_cli_score_batch)
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
    finalize.add_argument(
        "--manifest", required=True, help="path to a run-manifest.json"
    )
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
    finalize.add_argument(
        "--include-per-sample", action="store_true",
        help="include the saved full scorer result without a second scorer invocation",
    )
    for path_name in ("repo-root", "data-root", "lock-path"):
        finalize.add_argument("--" + path_name, default=None)
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


    promote_roster = sub.add_parser(
        "promote-pinned-roster-speech-packets",
        help=(
            "model-free promotion of a pinned carrier roster from a verified "
            "legacy feature cache"
        ),
    )
    promote_roster.add_argument("--promotion-plan", required=True)
    promote_roster.add_argument("--promotion-plan-sha256", required=True)
    promote_roster.set_defaults(func=_cli_promote_pinned_roster_speech_packets)

    extend_binding = sub.add_parser(
        "extend-speech-native-binding",
        help=(
            "model-free binding extension through the existing deterministic "
            "speech-native selector"
        ),
    )
    extend_binding.add_argument("--parent-binding", required=True)
    extend_binding.add_argument(
        "--output",
        help="binding successor output; omit only for graph-only generation",
    )
    extend_binding.add_argument("--seed", type=int, required=True)
    extend_binding.add_argument("--split-name")
    extend_binding.add_argument("--per-scenario", type=int)
    extend_binding.add_argument(
        "--knowledge-policy",
        choices=SPEECH_NATIVE_KNOWLEDGE_POLICY_IDS,
        help=(
            "replace key material with query-isolated action-complete knowledge "
            "derived model-free from SLURP train"
        ),
    )
    extend_binding.add_argument(
        "--decision-graph-output",
        help=(
            "optional paired DecisionGraphV1 output derived from the same isolated "
            "SLURP train corpus"
        ),
    )
    extend_binding.add_argument(
        "--decision-graph-id",
        default="slurp-data-derived-decision-graph-v2",
    )
    extend_binding.add_argument(
        "--information-audit-output",
        help=(
            "optional query-isolated, model-free task-information audit built "
            "through the same SLURP loader and decision-graph policy"
        ),
    )
    extend_binding.add_argument("--maximum-boundaries", type=int, default=30)
    extend_binding.add_argument(
        "--boundary-policy",
        choices=SPEECH_NATIVE_BOUNDARY_POLICY_IDS,
        default="ranked-pair-signal-v1",
        help=(
            "versioned boundary builder; shared-action entity boundaries refuse "
            "maximum-boundaries truncation"
        ),
    )
    extend_binding.add_argument("--workers", type=int, default=16)
    extend_binding.add_argument(
        "--scale-capacity-audit-output",
        help=(
            "aggregate-only 100-to-500 ladder capacity audit; does not emit or "
            "freeze new query identities"
        ),
    )
    extend_binding.add_argument("--existing-memory-split")
    extend_binding.add_argument("--cumulative-query-count", type=int)
    extend_binding.add_argument("--memory-query-count", type=int)
    extend_binding.add_argument("--holdout-query-count", type=int)
    extend_binding.add_argument(
        "--allow-parent-query-speaker-overlap",
        action="store_true",
        help=(
            "retain exact historical-query speaker overlap after a strict attempt "
            "has proved infeasible; query/key speaker isolation remains mandatory"
        ),
    )
    extend_binding.set_defaults(func=_cli_extend_speech_native_binding)

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
        "--planned-model-calls",
        type=int,
        required=True,
        help="finite positive integer; no numeric ceiling since the 2026-08-06 owner amendment",
    )
    smoke.add_argument("--planned-gpu-hours", type=float, required=True)
    smoke.add_argument("--planned-speech-audio-seconds", type=int, required=True)
    smoke.add_argument(
        "--plan",
        default=None,
        help=(
            "optional preregistered ExecutionPlan; when supplied, smoke verifies "
            "every computed identity and budget field and uses its exact attempt_id"
        ),
    )
    smoke.add_argument(
        "--run-dir",
        required=True,
        help="STABLE parent directory; a fresh attempt_id subdirectory is created every run",
    )
    smoke.add_argument(
        "--runtime-root",
        default=None,
        help="required unless --dry-run; see docs/runbooks/2026-08-05-r0-smoke.md preconditions",
    )
    smoke.add_argument("--host", default="127.0.0.1")
    smoke.add_argument("--port", type=int, default=8090)
    smoke.add_argument(
        "--tracking-uri",
        required=True,
        help="explicit local MLflow tracking URI; smoke never silently skips the upload",
    )
    smoke.add_argument("--ledger-cells", default=None)
    smoke.add_argument(
        "--repo-root",
        default=None,
        help="TEST-ONLY override of the study repo root; real operator usage should never pass this",
    )
    smoke.add_argument(
        "--dry-run",
        action="store_true",
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

    speech_finalize = sub.add_parser(
        "speech-native-finalize-from-disk",
        help=(
            "model-free finalization of an attempt whose contacts all completed "
            "but whose post-run receipt assembly was interrupted; rebuilds the "
            "flight receipt from the attempt's durable records with zero service "
            "contact of any kind"
        ),
    )
    speech_finalize.add_argument("--model", required=True)
    speech_finalize.add_argument("--dataset", required=True)
    speech_finalize.add_argument("--baseline", required=True)
    speech_finalize.add_argument("--experiment", required=True)
    speech_finalize.add_argument("--plan", required=True)
    speech_finalize.add_argument("--attempt-dir", required=True)
    speech_finalize.add_argument(
        "--session-receipt",
        required=True,
        help=(
            "path to the resident session receipt the attempt attached to; it is "
            "read as bytes only and the service is never contacted"
        ),
    )
    speech_finalize.add_argument(
        "--session-receipt-sha256",
        required=True,
        help=(
            "the receipt SHA-256 recorded for the flight; a mismatch means the "
            "service was restarted or mutated and the rebuild fails closed"
        ),
    )
    speech_finalize.add_argument(
        "--exposure-row",
        required=True,
        help="the registered model-free exposure row authorizing this rebuild",
    )
    speech_finalize.add_argument(
        "--authorization",
        required=True,
        help="the owner decision record that authorizes this finalization",
    )
    speech_finalize.add_argument(
        "--server-log-start-offset",
        type=int,
        default=None,
        help=(
            "explicit attempt window start; omit to derive the trailing window "
            "that holds exactly the traced contact count"
        ),
    )
    speech_finalize.add_argument(
        "--server-log-end-offset",
        type=int,
        default=None,
        help="explicit attempt window end; omit to use the current log size",
    )
    speech_finalize.add_argument(
        "--repo-root",
        default=None,
        help="TEST-ONLY repository-root override; real finalizations omit it",
    )
    speech_finalize.set_defaults(func=_cli_speech_native_finalize_from_disk)

    speech_action_audit = sub.add_parser(
        "speech-native-action-audit",
        help=(
            "model-free, gold-free structural action audit for finalized M7--M11 "
            "support flights and the admitted legacy M6 completion-gate abort"
        ),
    )
    speech_action_audit.add_argument("--attempt-dir", required=True)
    speech_action_audit.add_argument("--attempt-record", required=True)
    speech_action_audit.add_argument("--attempt-record-sha256", required=True)
    speech_action_audit.add_argument("--flight-receipt-sha256", required=True)
    speech_action_audit.add_argument("--decisions-sha256", required=True)
    speech_action_audit.add_argument("--trace-sha256", required=True)
    speech_action_audit.add_argument("--output", required=True)
    speech_action_audit.set_defaults(func=_cli_speech_native_action_audit)

    speech_engine_audit = sub.add_parser(
        "speech-native-engine-audit",
        help=(
            "model-free receipt-bound audit of the pinned llama.cpp MoE/CUDA-graph "
            "decode-width boundary"
        ),
    )
    speech_engine_audit.add_argument("--runtime-receipt", required=True)
    speech_engine_audit.add_argument("--session-receipt", required=True)
    speech_engine_audit.add_argument("--llama-cpp-root", required=True)
    speech_engine_audit.add_argument("--output", required=True)
    speech_engine_audit.set_defaults(func=_cli_speech_native_engine_audit)

    speech_prompt_audit = sub.add_parser(
        "speech-native-prompt-audit",
        help=(
            "model-free exact M11 prompt-fit audit through the resident "
            "llama.cpp template and tokenizer endpoints"
        ),
    )
    speech_prompt_audit.add_argument("--model", required=True)
    speech_prompt_audit.add_argument("--dataset", required=True)
    speech_prompt_audit.add_argument("--baseline", required=True)
    speech_prompt_audit.add_argument("--experiment", required=True)
    speech_prompt_audit.add_argument("--session-receipt", required=True)
    speech_prompt_audit.add_argument("--runtime-root", required=True)
    speech_prompt_audit.add_argument("--host", default="127.0.0.1")
    speech_prompt_audit.add_argument("--port", type=int, default=8080)
    speech_prompt_audit.add_argument("--workers", type=int, default=16)
    speech_prompt_audit.add_argument("--timeout-seconds", type=float, default=30.0)
    speech_prompt_audit.add_argument("--output", required=True)
    speech_prompt_audit.add_argument(
        "--repo-root",
        default=None,
        help="TEST-ONLY repository-root override; real audits omit it",
    )
    speech_prompt_audit.set_defaults(func=_cli_speech_native_prompt_audit)

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

    prepare_semantic = sub.add_parser(
        "prepare-semantic-knowledge",
        help="build or release a registered semantic knowledge store without model contact",
    )
    prepare_semantic.add_argument("--registration", required=True)
    prepare_semantic.add_argument("--repo-root", required=True)
    prepare_semantic.add_argument("--data-root", required=True)
    prepare_semantic.set_defaults(func=_cli_prepare_semantic_knowledge)
    prepare_support = sub.add_parser(
        "prepare-semantic-authoring-support",
        help="prepare registered SLURP authoring support without model contact",
    )
    prepare_support.add_argument("--config", required=True)
    prepare_support.add_argument("--repo-root", required=True)
    prepare_support.add_argument("--data-root", required=True)
    prepare_support.set_defaults(func=_cli_prepare_semantic_authoring_support)
    prepare_state = sub.add_parser(
        "prepare-state-source",
        help="prepare a registered deterministic predecessor without new inference",
    )
    prepare_state.add_argument("--registration", required=True)
    prepare_state.add_argument("--repo-root", required=True)
    prepare_state.add_argument("--data-root", required=True)
    prepare_state.set_defaults(func=_cli_prepare_state_source)

    revalidate_fit = sub.add_parser(
        "revalidate-request-fit",
        help="reuse unchanged full-roster capacity measurements after a registered repair",
    )
    for name in ("registration", "repo-root", "data-root", "runtime-root", "lock-path"):
        revalidate_fit.add_argument("--" + name, required=True)
    revalidate_fit.set_defaults(func=_cli_revalidate_request_fit)

    build_delivery = sub.add_parser(
        "build-delivery",
        help="build a verified phase-delivery derivative from an immutable parent",
    )
    build_delivery.add_argument("--parent-manifest", required=True)
    build_delivery.add_argument("--experiment-path", required=True)
    build_delivery.add_argument("--derivative-cell-id", required=True)
    build_delivery.add_argument("--output-dir", required=True)
    build_delivery.add_argument("--repo-root", required=True)
    build_delivery.add_argument("--data-root", required=True)
    build_delivery.set_defaults(func=_cli_build_delivery)

    flight = sub.add_parser(
        "flight",
        help="C4c FlightRuntime harness: preflight -> preprocess -> serve -> "
        "run_phases -> seal -> score for one arm/carrier",
    )
    flight.add_argument("--model", required=True)
    flight.add_argument("--dataset", required=True)
    flight.add_argument("--baseline", required=True)
    flight.add_argument("--experiment", required=True)
    flight.add_argument("--run-id", required=True)
    flight.add_argument(
        "--attempt-id", default=None, help="omit to mint a fresh attempt id"
    )
    flight.add_argument("--runtime-root", required=True)
    flight.add_argument(
        "--dry-run",
        action="store_true",
        help="stop after preflight() -- no server start, no model contact",
    )
    flight.add_argument(
        "--seal-only",
        action="store_true",
        help="complete raw generation and seal without final scoring",
    )
    flight.add_argument("--max-workers", type=int, default=1, help="score() worker count")
    flight.add_argument(
        "--campaign-active",
        action="store_true",
        help="cap preprocess() workers to 8 while a GPU campaign flies",
    )
    flight.set_defaults(func=_cli_flight)

    args = parser.parse_args(argv)
    return args.func(args)
