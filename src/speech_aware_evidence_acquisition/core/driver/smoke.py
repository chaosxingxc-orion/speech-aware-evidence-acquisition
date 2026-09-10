"""``saea-driver smoke``: one command, fresh attempt, plan -> session -> run
-> finalize (R0 operator-path repair).

Independent rereview (``wiki/audit/speech-aware-evidence-acquisition-r0-review/
independent-rereview-2026-08-07/``) finding B2: even after B1's CLI-entry
repair, the R0 smoke runbook required an operator to hand-assemble a plan
(computing ``protocol_hash`` and reading ``split_identity_hash`` off
``docs/receipts/splits.json`` by hand), separately call an undocumented
Python API to start a session and persist its receipt, run, then finalize
without ever passing ``--tracking-uri`` -- five manual, error-prone steps
spread across the runbook. This module collapses that into one command.

``run_smoke`` is deliberately a THIN sequencer: it calls exactly the two
sanctioned functions ``saea-driver run``/``saea-driver finalize`` already
call (``core.driver.run_experiment_bundled`` then ``core.bundle.finalize_bundle``)
in the same order, with no gate/trust-boundary logic of its own -- it cannot
"bypass" I1-I9 because it never reimplements any check those functions
already make. ``_cli_smoke`` is the argument-parsing/wiring layer: it derives
a FRESH ``attempt_id`` every invocation (so a failed attempt never needs a
manual fresh-attempt-id/fresh-run-dir dance -- the next invocation simply
gets a new one automatically), looks up ``split_identity_hash``/``split_role``
itself via the same verified ``load_split`` invariant-I1 path rather than
asking the operator to copy a hash out of a receipt file by hand, and
computes ``protocol_hash`` via ``core.config.protocol_hash`` (the exact
convention ``run_experiment`` itself re-checks) instead of asking the
operator to reconstruct that formula.

``--dry-run`` (TEST-ONLY, never for a real smoke) substitutes exactly two
things, both documented at their construction site below: a fake, in-memory
``transport`` callable that never opens a socket (mirroring the ``_transport``
test double used throughout ``tests/unit/test_driver.py``/``test_bundle.py``),
and a no-op ``_NoOpGate`` (mirroring those same tests' ``_OpenGate``) instead
of a real ``contracts.FrozenCoreGate`` and a real spawned llama-server session.
Everything else -- ``run_experiment_bundled``, ``finalize_bundle``, the
attempt store, the manifest/bundle verification chain -- runs for real even
under ``--dry-run``; those are exactly the trust-boundary components I1-I9's
own extensive test suite already covers, so this module does not re-prove
them, only that the ORCHESTRATION around them (fresh attempt id, plan
derivation, run -> finalize sequencing, artifact-location printing) actually
works end to end. A real (non-``--dry-run``) invocation never touches
``_NoOpGate``/the fake transport at all -- it constructs the real gate and
calls ``core.session.start_session`` to spawn the receipt-pinned binary,
exactly as the runbook's own preconditions require.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import secrets
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping

from ...contracts import ExecutionPlan
from ...e0.artifacts import REPO_ROOT
from ..bundle import FinalizeResult, finalize_bundle
from ..config import (
    ComposedConfig,
    compose,
    d1_evidence_supplement_relpath,
    d1_evidence_supplement_sha256,
    d1_media_supplement_relpath,
    d1_media_supplement_sha256,
    model_materialization_root,
    model_lock_key,
    protocol_hash as compute_protocol_hash,
    resolve_runtime_receipt_path,
    runtime_receipt_relpath,
)
from ..resources import NullSampler, ResourceSampler
from ..session import (
    STUDY_SLUG,
    ModelFileRef,
    SessionReceipt,
    SESSION_RECEIPT_SCHEMA,
    write_session_receipt,
)
from .bundled import run_experiment_bundled
from .run import load_split


class _NoOpGate:
    """TEST-ONLY stand-in for ``contracts.FrozenCoreGate``, reachable only via
    ``smoke --dry-run``. Mirrors the ``_OpenGate`` test double already used
    throughout ``tests/unit/test_driver.py``/``tests/unit/test_bundle.py`` --
    accepts any plan unconditionally, never touched by a real (non-dry-run)
    smoke invocation."""

    def assert_model_touch_allowed(self, plan: ExecutionPlan) -> None:
        return None


def _dry_run_transport(request_bytes: bytes) -> bytes:
    """TEST-ONLY fake transport, reachable only via ``smoke --dry-run``: never
    opens a socket, never spawns a process, never touches a model. Mirrors the
    ``_transport``/``_dry_run`` fixtures already used throughout
    ``tests/unit/test_driver.py``/``tests/unit/test_bundle.py``."""

    return json.dumps(
        {"text": "dry-run smoke: no real model was touched", "usage": {"prompt_tokens": 0}}
    ).encode("utf-8")


def _write_dry_run_session_receipt(path: Path, *, session_id: str) -> SessionReceipt:
    """TEST-ONLY synthetic session receipt, reachable only via
    ``smoke --dry-run``: every field is a clearly-labelled placeholder, never
    re-verified against a runtime receipt (the fake transport above never
    calls ``assert_session_alive``) -- persisted through the REAL,
    already-tested ``core.session.write_session_receipt`` so the "persist a
    session receipt" step is genuinely exercised, not skipped. A real smoke
    invocation calls ``core.session.start_session`` instead, which spawns the
    receipt-pinned binary and records what it actually observed."""

    placeholder_binary = hashlib.sha256(b"dry-run-smoke-no-real-binary").hexdigest()
    placeholder_model = hashlib.sha256(b"dry-run-smoke-no-real-model").hexdigest()
    receipt = SessionReceipt(
        schema=SESSION_RECEIPT_SCHEMA,
        study=STUDY_SLUG,
        session_id=session_id,
        binary_path="dry-run/no-real-binary",
        binary_sha256=placeholder_binary,
        argv=("dry-run-smoke-no-real-process",),
        pid=1,
        host="127.0.0.1",
        port=1,
        model_files=(ModelFileRef(path="dry-run/no-real-model.gguf", sha256=placeholder_model),),
        started_at=datetime.now(timezone.utc).isoformat(),
        startup_stdout_sha256=hashlib.sha256(b"").hexdigest(),
    ).validate()
    write_session_receipt(path, receipt)
    return receipt


def fresh_attempt_id(*, now: Callable[[], float] = time.time) -> str:
    """A fresh, ``RUN_ID_PATTERN``-safe attempt id: wall-clock timestamp plus
    a random suffix, so two invocations in the same second still never
    collide. This is the ONE place ``smoke`` generates an attempt id -- an
    operator never types one by hand, and a failed attempt is automatically
    followed by a fresh one on the next invocation, never a silent reuse."""

    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime(now()))
    return f"attempt-{stamp}-{secrets.token_hex(3)}"


@dataclass(frozen=True)
class SmokeResult:
    run_id: str
    attempt_id: str
    plan_path: Path
    session_receipt_path: Path
    manifest_path: Path
    finalize: FinalizeResult


def run_smoke(
    composed: ComposedConfig,
    plan: ExecutionPlan,
    gate: object,
    lock: Mapping[str, object],
    root: Path,
    run_dir: Path,
    transport: Callable[[bytes], bytes],
    *,
    repo_root: Path = REPO_ROOT,
    session_receipt_path: Path,
    plan_path: Path,
    tracking_uri: str,
    ledger_cells: Mapping[str, str] | None = None,
    resource_sampler: ResourceSampler | None = None,
) -> SmokeResult:
    """Thin sequencer: exactly ``run_experiment_bundled`` then
    ``finalize_bundle`` -- the same two sanctioned functions
    ``saea-driver run``/``saea-driver finalize`` already call, in the same
    order, with no additional gate/trust-boundary logic. Fails closed exactly
    as those two functions do: nothing here is caught or retried."""

    manifest_path = run_experiment_bundled(
        composed, plan, gate, lock, root, run_dir, transport,
        repo_root=repo_root, session_receipt_path=session_receipt_path,
        resource_sampler=resource_sampler,
    )
    finalize_result = finalize_bundle(
        manifest_path, lock, root, repo_root=repo_root,
        ledger_cells=ledger_cells, tracking_uri=tracking_uri,
    )
    return SmokeResult(
        run_id=plan.run_id,
        attempt_id=str(plan.attempt_id),
        plan_path=plan_path,
        session_receipt_path=session_receipt_path,
        manifest_path=manifest_path,
        finalize=finalize_result,
    )


def _server_args(values: Mapping[str, object]) -> list[str]:
    """Extra llama-server argv from the MODEL config's ``server_args`` key.

    2026-08-08: the first real smoke failed with ``56032 tokens > n_ctx 4096``
    — context/offload flags are part of the run's identity, so they live in
    the config (config-hash → protocol-hash bound), never in an ad-hoc
    operator flag. Absent key = no extra argv; a non-list fails closed.
    """

    raw = values.get("server_args", [])
    if not isinstance(raw, (list, tuple)):
        raise ValueError(
            f"model config server_args must be a list of argv tokens, got {type(raw).__name__}"
        )
    return [str(token) for token in raw]


def _server_env(values: Mapping[str, object]) -> dict[str, str]:
    """Extra llama-server environment from the MODEL config's ``server_env``
    key (W3, 2026-08-11: GGML_CUDA_DISABLE_GRAPHS changes decode rate by
    +34% at batch>1, so a runtime env var is serving identity — it lives in
    the config, inside the config hash, never in an operator shell). Absent
    key = no extra env; a non-mapping or non-string content fails closed
    (``start_session`` re-checks the str->str contract at spawn time)."""

    raw = values.get("server_env", {})
    if not isinstance(raw, Mapping):
        raise ValueError(
            f"model config server_env must be a mapping of str->str, got {type(raw).__name__}"
        )
    resolved = {str(key): str(value) for key, value in raw.items()}
    transport_root = values.get("speech_feature_root")
    if transport_root is not None and (
        not isinstance(transport_root, str)
        or not transport_root
        or resolved.get("LLAMA_SPEECH_FEATURE_ROOT") != transport_root
    ):
        raise ValueError(
            "model config speech feature root must be identical for the transport "
            "and LLAMA_SPEECH_FEATURE_ROOT server environment"
        )
    return resolved


def _write_inference_process_audit(session: object, output: Path) -> Path | None:
    """Persist the live zero-mmproj proof before the first inference request."""

    if getattr(session, "role", None) != "inference":
        return None
    from ..session import audit_mmproj_free_inference

    audit = audit_mmproj_free_inference(session)
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return target


def _cli_smoke(args: argparse.Namespace) -> int:
    from ...contracts import FrozenCoreGate
    from ...data.lock import data_root, load_lock, umbrella_lock_path
    from ..configured_transport import build_configured_transport
    from ..resources import resolve_resource_sampler
    from ..session import load_runtime_receipt, start_session, stop_session

    repo_root = Path(args.repo_root) if args.repo_root else REPO_ROOT
    if not args.dry_run and not args.runtime_root:
        raise SystemExit("smoke: --runtime-root is required unless --dry-run is given")

    lock = load_lock(umbrella_lock_path())
    root = data_root()
    composed = compose(repo_root, args.model, args.dataset, args.baseline, args.experiment)
    ids, split_hash, split_role = load_split(
        repo_root, str(composed.values["split_name"]), lock, root
    )

    expected_plan_values = {
        "run_id": args.run_id,
        "execution_profile": args.execution_profile,
        "carrier_lock_key": str(composed.values["carrier_lock_key"]),
        "split_role": split_role,
        "split_identity_hash": split_hash,
        "planned_model_calls": args.planned_model_calls,
        "planned_gpu_hours": args.planned_gpu_hours,
        "planned_speech_audio_seconds": args.planned_speech_audio_seconds,
        "protocol_hash": compute_protocol_hash(
            composed.config_hash, str(composed.values["arm"]), split_hash
        ),
    }
    if args.plan is None:
        attempt_id = fresh_attempt_id()
        plan = ExecutionPlan(
            **expected_plan_values,
            attempt_id=attempt_id,
        ).validate()
    else:
        try:
            plan_document = json.loads(Path(args.plan).read_text(encoding="utf-8"))
            plan = ExecutionPlan(**plan_document).validate()
        except (OSError, UnicodeError, json.JSONDecodeError, TypeError) as error:
            raise SystemExit(
                f"smoke: cannot read preregistered plan {args.plan!r}: {error}"
            ) from error
        mismatches = {
            field_name: {
                "expected": expected_value,
                "actual": getattr(plan, field_name),
            }
            for field_name, expected_value in expected_plan_values.items()
            if getattr(plan, field_name) != expected_value
        }
        if mismatches:
            raise SystemExit(
                "smoke: preregistered plan disagrees with the composed runtime "
                f"contract: {json.dumps(mismatches, sort_keys=True)}"
            )
        if plan.attempt_id is None:
            raise SystemExit(
                "smoke: preregistered plan must carry one explicit attempt_id"
            )
        attempt_id = plan.attempt_id

    # A fresh attempt_id (above) always names a brand-new attempt directory
    # here too -- no operator ever needs to invent a fresh --run-dir by hand
    # after a failed attempt (independent rereview §7.1); --run-dir is the
    # STABLE parent an operator points at once, this attempt's own
    # subdirectory is always new.
    attempt_run_dir = Path(args.run_dir) / attempt_id
    if args.plan is not None and attempt_run_dir.exists():
        raise SystemExit(
            "smoke: preregistered attempt directory already exists; refusing plan reuse: "
            f"{attempt_run_dir}"
        )
    attempt_run_dir.mkdir(parents=True, exist_ok=args.plan is None)
    plan_path = attempt_run_dir / f"{plan.run_id}.plan.json"
    plan_path.write_text(
        json.dumps(asdict(plan), indent=2, sort_keys=True), encoding="utf-8", newline="\n"
    )
    session_receipt_path = attempt_run_dir / f"{plan.run_id}.session-receipt.json"
    session_stop_receipt_path = (
        attempt_run_dir / f"{plan.run_id}.session-stop-receipt.json"
    )
    process_audit_output_path = attempt_run_dir / f"{plan.run_id}.mmproj-audit.json"
    process_audit_path: Path | None = None
    # Task 1 (2026-08-09 finding): llama-server's own stdout/stderr used to
    # be captured for the startup window only, then thrown away -- hours of
    # server output were unrecoverable after exactly the kind of mid-run
    # stall that killed two arms. A real (non-dry-run) attempt now gets a
    # persisted log automatically, next to this attempt's other artifacts --
    # no operator flag, so it can never be forgotten the way the smoke
    # launcher itself once was (scripts/run_arm_sequence.sh's own history).
    server_log_path = attempt_run_dir / f"{plan.run_id}.server.log"

    if args.dry_run:
        gate: object = _NoOpGate()
        transport: Callable[[bytes], bytes] = _dry_run_transport
        _write_dry_run_session_receipt(
            session_receipt_path, session_id=f"dry-run-{plan.run_id}-{attempt_id}"
        )
        sampler: ResourceSampler = NullSampler(
            "smoke --dry-run: TEST-ONLY, never touches a real GPU or model"
        )
    else:
        # R0.2 second-model plumbing: the model fragment's own optional
        # "runtime_receipt" key (default: today's "receipts/runtime.json")
        # picks which committed receipt this session/gate pair is bound to
        # -- see core.config.runtime_receipt_relpath's own docstring. The
        # gate's expected_model_lock_key is derived from the SAME composed
        # config that chose the receipt path, so a run can never pair one
        # model's config with a different model's receipt (core.config.
        # model_lock_key's own docstring; contracts.FrozenCoreGate.
        # expected_model_lock_key).
        runtime_receipt = load_runtime_receipt(resolve_runtime_receipt_path(repo_root, composed.values))
        configured_model_root = model_materialization_root(composed.values)
        model_root = Path(configured_model_root) if configured_model_root is not None else None
        gate = FrozenCoreGate.for_study_repo(
            repo_root,
            root,
            Path(args.runtime_root),
            runtime_receipt_relpath=runtime_receipt_relpath(composed.values),
            expected_model_lock_key=model_lock_key(composed.values),
            model_root=model_root,
            d1_media_supplement_relpath=d1_media_supplement_relpath(composed.values),
            d1_media_supplement_sha256=d1_media_supplement_sha256(composed.values),
            d1_evidence_supplement_relpath=d1_evidence_supplement_relpath(composed.values),
            d1_evidence_supplement_sha256=d1_evidence_supplement_sha256(composed.values),
        )
        session = start_session(
            runtime_root=Path(args.runtime_root),
            data_root=root,
            runtime_receipt=runtime_receipt,
            host=args.host,
            port=args.port,
            session_id=f"{plan.run_id}-{attempt_id}",
            extra_argv=_server_args(composed.values),
            extra_env=_server_env(composed.values),
            receipt_path=session_receipt_path,
            server_log_path=server_log_path,
            role=runtime_receipt.get("role", "legacy"),
            model_root=model_root,
        )
        try:
            process_audit_path = _write_inference_process_audit(
                session, process_audit_output_path
            )
            transport = build_configured_transport(
                composed.values, root, repo_root=repo_root, session=session,
                runtime_receipt=runtime_receipt, runtime_root=Path(args.runtime_root),
            )
            sampler = resolve_resource_sampler()
        except BaseException:
            stop_session(
                session,
                runtime_receipt=runtime_receipt,
                runtime_root=Path(args.runtime_root),
                force_after_timeout=True,
                receipt_path=session_stop_receipt_path,
            )
            raise

    ledger_cells = (
        json.loads(Path(args.ledger_cells).read_text(encoding="utf-8")) if args.ledger_cells else {}
    )

    try:
        result = run_smoke(
            composed, plan, gate, lock, root, attempt_run_dir, transport,
            repo_root=repo_root, session_receipt_path=session_receipt_path,
            plan_path=plan_path, tracking_uri=args.tracking_uri,
            ledger_cells=ledger_cells, resource_sampler=sampler,
        )
    finally:
        # A smoke invocation owns the server process it starts. Always stop
        # that exact receipt-bound PID, including after a failed run, so a
        # preprocess session cannot keep mmproj resident when the later
        # inference role starts. Dry-run has no process and remains a no-op.
        if not args.dry_run:
            stop_session(
                session,
                runtime_receipt=runtime_receipt,
                runtime_root=Path(args.runtime_root),
                force_after_timeout=True,
                receipt_path=session_stop_receipt_path,
            )
    print(
        json.dumps(
            {
                "run_id": result.run_id,
                "attempt_id": result.attempt_id,
                "dry_run": bool(args.dry_run),
                "plan": str(result.plan_path),
                "session_receipt": str(result.session_receipt_path),
                "session_stop_receipt": (
                    None if args.dry_run else str(session_stop_receipt_path)
                ),
                "mmproj_audit": (
                    str(process_audit_path) if process_audit_path is not None else None
                ),
                # None under --dry-run: no real server was ever spawned, so
                # no server log exists (Task 1, 2026-08-09).
                "server_log": None if args.dry_run else str(server_log_path),
                "manifest": str(result.manifest_path),
                "scores": str(result.finalize.scores_path),
                "ledger_markdown": str(result.finalize.ledger_markdown_path),
                "ledger_json": str(result.finalize.ledger_json_path),
                "mlflow_run": result.finalize.mlflow_run_id,
                "attempt_state": result.finalize.attempt_state,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0
