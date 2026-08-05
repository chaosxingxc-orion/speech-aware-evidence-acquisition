"""Atomic run bundle: manifest build + verify + finalize (R0 repair T6, invariant I7).

Reproduced defect (task-6 brief): scoring reads only ``carrier_lock_key``/
``sample_id``/``text`` from each outputs row -- a row whose ``text`` was
mutated while keeping its old ``response_sha256`` scores normally. Nothing
checks that the outputs sample set equals the frozen split, that request ids
appear in the trace, or that the trace manifest matches the raw trace.
``core.tracking.log_run`` uploads only outputs + trace manifest (never the raw
trace, never a score artifact), and ``core.base.RunResult`` carries no
outputs/scores hash. There is no single verifiable transaction binding
run -> artifacts -> scores -> ledger row.

This module is that transaction. One attempt produces exactly one
``run-manifest.json`` (schema ``saea-run-manifest-v1``) binding: the study
commit (read from git, fail-closed if the tree is dirty or the commit cannot
be read -- see :func:`_study_commit`), the four config fragment names +
config_hash, the protocol hash, the FULL :class:`~..contracts.ExecutionPlan`
(including ``attempt_id``), the exposure run id, the split name/role/
identity_hash/ids, the session receipt path+sha256 (when the profile touches
the model), the outputs/raw-trace/trace-manifest/scores path+sha256, the
actual cost, and a terminal status (``COMPLETED``/``ABORTED``) with a failure
reason when aborted.

:func:`verify_bundle` re-derives every hash from bytes on disk -- never trusts
the manifest's own numbers -- and cross-checks: every outputs row's
``response_text_sha256`` against a fresh ``sha256(text)`` (the adapter-side
fix in ``core.model.CoreResponse``, see its docstring for why the raw
``response_sha256`` alone is not strictly re-derivable from ``text`` after the
fact); the outputs sample-id set against the frozen split's ids (no missing,
extra, or duplicate); every outputs ``request_id`` against the raw trace's
record ids; and the trace manifest's per-record hashes against records
re-hashed straight from the raw trace file. The attempt's OWN durable state
file (``core.attempts.AttemptHandle``) is re-read fresh, never trusted from
the manifest's self-reported ``status`` -- this is what makes "finalize an
ABORTED attempt as COMPLETED" fail even if the manifest's ``status`` field is
hand-edited afterward.

:func:`finalize_bundle` is the only path that transitions an attempt to
FINALIZED: verify -> run the manifest's configured scorers (via
``core.scorers.score_bundle``, which refuses anything but a genuine
:class:`VerifiedBundle`) -> write a scores artifact -> attach it to the
manifest -> re-verify -> (stubbable) MLflow upload -> a machine-derived
ledger row (``core.tracking.ledger_row_for_bundle``, which refuses any
hand-supplied cell that contradicts the verified manifest) -> mark the
attempt FINALIZED.

ACCEPTED SCOPE BOUNDARY (state this bluntly; do not let a reader over-trust
this module): everything above is a CONSISTENCY check over files on disk, not
an AUTHENTICITY check that those files were ever genuinely produced by the
frozen model. An attacker (or a bug) with plain filesystem write access to a
run's ``run_dir`` -- the same access level a legitimate run already needs to
create outputs/trace files in the first place -- can synthesize a FULLY
SELF-CONSISTENT bundle from scratch: real split ids, self-matching
``response_sha256``/``response_text_sha256`` pairs, a raw trace whose records
hash-agree with a hand-built trace manifest, all outer artifact hashes
correct. ``finalize_bundle`` accepts such a bundle end to end, because
``response_sha256`` hashes the raw transport bytes, and those bytes are never
independently persisted anywhere outside files the same writer controls --
there is no external, write-once anchor proving a response actually crossed
the ``LlamaServerTransport``/``SessionReceipt`` boundary (I5) rather than
being typed into ``outputs.jsonl`` by hand. The external anchors this module
DOES provide -- a real clean git commit (proves what CODE would have run, not
that it did), the frozen split's identity hash (proves the CLAIMED sample set
is legitimate, not that responses were genuinely produced), and the
``core.attempts`` state-machine transition (a genuine one-time gate only if
the attacker lacks write access to ``SPEECHRL_DATA_DIR/attempts/`` too, which
an attacker with run_dir access under the same controlled data root very
plausibly also has) -- do not close this gap. Closing it would require a
genuinely separate, append-only/immutable transport log written independently
of anything the same writer later controls, or a remote/signed attestation
anchor outside the local filesystem; both are out of scope for R0's local,
single-machine, single-operator trust model and are not attempted here. I7
should be read as "the recorded artifacts stayed internally coherent from
when they were written to when they were finalized," not "these are proven
genuine model outputs."
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping

from ..contracts import (
    STUDY_SLUG,
    BoundaryViolation,
    ExecutionPlan,
    TraceContractError,
    TraceRecord,
)
from ..e0.artifacts import REPO_ROOT, sha256_file, write_json_artifact
from .attempts import AttemptError, AttemptHandle, AttemptStore
from .attempts import STATE_FINALIZED, STATE_OPENED
from .base import RunResult
from .config import ComposedConfig
from .scorers import score_bundle
from .split_receipt import VerifiedSplit
from .tracking import ledger_row_for_bundle, log_bundle

RUN_MANIFEST_SCHEMA = "saea-run-manifest-v1"
STATUS_COMPLETED = "COMPLETED"
STATUS_ABORTED = "ABORTED"
_VALID_STATUSES = (STATUS_COMPLETED, STATUS_ABORTED)

# VerifiedBundle.attempt_state sentinel for "no attempt file exists at all"
# (a failure before FrozenCoreAdapter ever opened one) -- distinct from every
# real core.attempts state (RESERVED/OPENED/FINALIZED/ABORTED), but like all
# of those except OPENED, never eligible for finalize_bundle to proceed.
ATTEMPT_STATE_NEVER_OPENED = "NEVER_OPENED"


class BundleError(RuntimeError):
    """A run manifest cannot be built, or a bundle fails verification/finalization."""


# ---------------------------------------------------------------------------
# Study commit (build time only -- never re-verified at verify_bundle time,
# since the study repo legitimately moves commits after a run was recorded).
# ---------------------------------------------------------------------------


def _git(repo_root: Path, *args: str) -> tuple[int, str, str]:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.returncode, completed.stdout.strip(), completed.stderr.strip()


def _study_commit(repo_root: Path) -> str:
    """Read the study repo's commit, fail-closed.

    Design choice (task-6 brief asks this be stated explicitly): a run
    manifest binds the EXACT commit the run executed against. If the tree is
    dirty, "the commit" is a lie -- uncommitted changes could be anything --
    so we refuse rather than record a commit that does not describe what
    actually ran. If ``git`` itself is unavailable or the directory is not a
    repository, we likewise refuse rather than silently omit study_commit
    (an optional/None field here would make every later manifest field's
    trustworthiness ambiguous: "was there no repo, or did we just not check?").
    This mirrors ``e0.runtime_receipt.build_runtime_receipt``'s existing
    dirty-tree refusal for the llama.cpp build tree -- same discipline,
    applied to the study tree itself.
    """

    code, dirty, stderr = _git(repo_root, "status", "--porcelain")
    if code != 0:
        raise BundleError(f"cannot read git status for {repo_root}: {stderr}")
    if dirty:
        raise BundleError(
            f"study repo {repo_root} has uncommitted changes; a run manifest must bind "
            f"the exact commit that produced the run, never a dirty tree:\n{dirty}"
        )
    code, commit, stderr = _git(repo_root, "rev-parse", "HEAD")
    if code != 0 or not commit:
        raise BundleError(f"cannot read the study repo's HEAD commit at {repo_root}: {stderr}")
    return commit


def require_clean_study_repo(repo_root: Path) -> str:
    """Public wrapper over :func:`_study_commit` (CRITICAL fix, T6 fix round):
    ``core.driver.run_experiment_bundled`` calls this BEFORE ``run_experiment``
    ever spends attempt budget, not only once a manifest is finally built at
    the end. Without this, a dirty/unreadable study repo let a run execute to
    completion (outputs written, calls/audio-seconds durably spent) and only
    THEN discover it could never produce a manifest -- leaving a
    budget-consuming run with no manifest and its attempt stuck OPENED
    forever, since the raising `build_manifest` call sat outside the
    try/except that would otherwise have aborted it. Returns the commit for
    convenience (unused by the caller today); raises :class:`BundleError`
    exactly as ``_study_commit`` does."""

    return _study_commit(Path(repo_root))


# ---------------------------------------------------------------------------
# Repo confinement (IMPORTANT fix, T6 fix round): no bundle artifact --
# manifest, scores, or ledger row -- may ever be written INSIDE the study
# repository. ``core.tracing.TraceSink`` already refuses an in-repo run_dir
# for outputs/trace files; the ORIGINAL build_manifest/finalize_bundle never
# re-checked this independently, so an aborted-run manifest (which does not
# go through TraceSink at all -- it is written directly by write_json_artifact)
# could land inside the checkout. Fixed here as an independent rail, mirroring
# the two-rail discipline T3 established for I3/I4 (adapter AND transport each
# check media confinement on their own authority, never trusting the other).
# ---------------------------------------------------------------------------


def _refuse_if_inside_repo(path: Path, label: str) -> Path:
    resolved = Path(path).resolve()
    if resolved == REPO_ROOT or REPO_ROOT in resolved.parents:
        raise BundleError(
            f"{label} {resolved} is inside the study repository ({REPO_ROOT}); run bundle "
            "artifacts (manifest, scores, ledger rows) are NEVER written into the repository "
            "(study contract) -- use a run_dir under SPEECHRL_DATA_DIR or another location "
            "outside the repository checkout"
        )
    return resolved


# ---------------------------------------------------------------------------
# Manifest construction.
# ---------------------------------------------------------------------------


def _artifact_meta(path: Path) -> dict[str, str]:
    return {"path": str(Path(path).resolve()), "sha256": sha256_file(path)}


def _manifest_document(
    *,
    repo_root: Path,
    data_root: Path,
    composed: ComposedConfig,
    plan: ExecutionPlan,
    verified_split: VerifiedSplit,
    session_receipt_path: Path | None,
    run_dir: Path,
    status: str,
    failure_reason: str | None,
    result: RunResult | None,
    now: Callable[[], datetime],
) -> dict[str, object]:
    if status not in _VALID_STATUSES:
        raise BundleError(f"manifest status must be one of {_VALID_STATUSES}, got {status!r}")
    if status == STATUS_COMPLETED:
        if failure_reason is not None:
            raise BundleError("a COMPLETED manifest must not carry a failure_reason")
        if result is None:
            raise BundleError("a COMPLETED manifest requires the run's RunResult")
    if status == STATUS_ABORTED and not (isinstance(failure_reason, str) and failure_reason.strip()):
        raise BundleError("an ABORTED manifest requires a non-empty failure_reason")

    attempt_id = plan.attempt_id
    if not isinstance(attempt_id, str) or not attempt_id.strip():
        raise BundleError(
            "a run manifest requires a plan with a non-empty attempt_id (R0 repair T4/T6)"
        )
    run_id = plan.run_id
    run_dir = Path(run_dir).resolve()

    outputs_meta = None
    raw_trace_meta = None
    trace_manifest_meta = None
    cost = None
    if result is not None:
        outputs_path = Path(result.outputs_path).resolve()
        if not outputs_path.is_file():
            raise BundleError(f"RunResult.outputs_path does not exist: {outputs_path}")
        outputs_meta = _artifact_meta(outputs_path)
        raw_trace_path = run_dir / f"{run_id}.trace.jsonl"
        trace_manifest_path = run_dir / f"{run_id}.trace-manifest.json"
        if raw_trace_path.is_file():
            raw_trace_meta = _artifact_meta(raw_trace_path)
        if trace_manifest_path.is_file():
            trace_manifest_meta = _artifact_meta(trace_manifest_path)
        cost = dict(result.cost)
    else:
        # Best-effort: an aborted attempt may still have left a partial trace
        # (never outputs -- run_experiment only writes outputs after every
        # sample succeeds) on disk; bind whatever genuinely exists so the
        # aborted bundle is still auditable, never pretend it is complete.
        raw_trace_path = run_dir / f"{run_id}.trace.jsonl"
        if raw_trace_path.is_file():
            raw_trace_meta = _artifact_meta(raw_trace_path)

    session_meta = None
    if session_receipt_path is not None:
        session_path = Path(session_receipt_path).resolve()
        if session_path.is_file():
            session_meta = _artifact_meta(session_path)

    attempts_root = Path(data_root) / "attempts"
    attempt_state_path = attempts_root / run_id / f"{attempt_id}.json"

    return {
        "schema": RUN_MANIFEST_SCHEMA,
        "study": STUDY_SLUG,
        "run_id": run_id,
        "created_at": now().astimezone(timezone.utc).isoformat(),
        "status": status,
        "failure_reason": failure_reason,
        "study_commit": _study_commit(Path(repo_root)),
        "config": {"fragments": dict(composed.fragments), "config_hash": composed.config_hash},
        "protocol_hash": plan.protocol_hash,
        "plan": {
            "schema": plan.schema,
            "study": plan.study,
            "run_id": plan.run_id,
            "execution_profile": plan.execution_profile,
            "carrier_lock_key": plan.carrier_lock_key,
            "split_role": plan.split_role,
            "split_identity_hash": plan.split_identity_hash,
            "planned_model_calls": plan.planned_model_calls,
            "planned_gpu_hours": plan.planned_gpu_hours,
            "planned_speech_audio_seconds": plan.planned_speech_audio_seconds,
            "protocol_hash": plan.protocol_hash,
            "attempt_id": plan.attempt_id,
        },
        "exposure_run_id": plan.run_id,
        "split": {
            "name": str(composed.values.get("split_name", "")),
            "role": verified_split.split_role,
            "carrier_lock_key": verified_split.carrier_lock_key,
            "identity_hash": verified_split.identity_hash,
            "ids": sorted(verified_split.ids),
        },
        "session_receipt": session_meta,
        "outputs": outputs_meta,
        "raw_trace": raw_trace_meta,
        "trace_manifest": trace_manifest_meta,
        "scores": None,
        "scorers": list(composed.values.get("scorers", [])),
        "cost": cost,
        "attempt": {
            "run_id": run_id,
            "attempt_id": attempt_id,
            "state_path": str(attempt_state_path),
        },
    }


def build_manifest(
    *,
    repo_root: Path,
    data_root: Path,
    composed: ComposedConfig,
    plan: ExecutionPlan,
    verified_split: VerifiedSplit,
    session_receipt_path: Path | None,
    run_dir: Path,
    status: str,
    failure_reason: str | None = None,
    result: RunResult | None = None,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> Path:
    """Build and durably write one attempt's run manifest; return its path."""

    # Repo confinement FIRST (IMPORTANT fix, T6 fix round): the cheapest,
    # dependency-free check, before touching git or the filesystem for
    # anything else -- a manifest destined for inside the repository is
    # refused before any other work happens, on COMPLETED and ABORTED calls
    # alike (they share this one function).
    _refuse_if_inside_repo(run_dir, "run manifest run_dir")

    document = _manifest_document(
        repo_root=repo_root,
        data_root=data_root,
        composed=composed,
        plan=plan,
        verified_split=verified_split,
        session_receipt_path=session_receipt_path,
        run_dir=run_dir,
        status=status,
        failure_reason=failure_reason,
        result=result,
        now=now,
    )
    manifest_path = Path(run_dir).resolve() / f"{plan.run_id}.run-manifest.json"
    write_json_artifact(manifest_path, document)
    return manifest_path


def _attach_scores(manifest_path: Path, scores_path: Path) -> None:
    try:
        document = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise BundleError(f"cannot read run manifest {manifest_path}: {error}") from error
    document["scores"] = _artifact_meta(scores_path)
    write_json_artifact(manifest_path, document)


# ---------------------------------------------------------------------------
# Verification: recompute every hash from bytes on disk; trust nothing else.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VerifiedBundle:
    """The result of a bundle that passed every I7 cross-check. Only this
    type -- never a bare manifest path or dict -- is accepted by
    ``core.scorers.score_bundle``: scoring is structurally impossible without
    first surviving :func:`verify_bundle`."""

    manifest_path: Path
    manifest: Mapping[str, object]
    outputs_path: Path | None
    outputs_rows: tuple[Mapping[str, object], ...]
    trace_records: Mapping[str, Mapping[str, object]]
    split_ids: frozenset
    attempt_state: str


def _read_bytes(path: Path, label: str) -> bytes:
    try:
        return Path(path).read_bytes()
    except OSError as error:
        raise BundleError(f"cannot read {label} at {path}: {error}") from error


def _verify_artifact(meta: object, label: str) -> bytes | None:
    if meta is None:
        return None
    if not isinstance(meta, Mapping) or not isinstance(meta.get("path"), str) or not isinstance(
        meta.get("sha256"), str
    ):
        raise BundleError(f"manifest {label} entry must be a {{path, sha256}} object")
    raw = _read_bytes(Path(meta["path"]), label)
    actual = hashlib.sha256(raw).hexdigest()
    if actual != meta["sha256"]:
        raise BundleError(
            f"{label} hash mismatch: manifest records {meta['sha256'][:12]}..., actual "
            f"on-disk bytes hash to {actual[:12]}... ({meta['path']})"
        )
    return raw


def _split_jsonl(text: str) -> list[str]:
    """Split on the literal record separator only (matches ``core.tracing``'s
    and ``core.scorers``' own discipline): ``json.dumps(ensure_ascii=False)``
    leaves U+2028/U+2029 inside string values, which ``str.splitlines()``
    would wrongly treat as line breaks."""

    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    return lines


_REQUIRED_OUTPUTS_FIELDS = frozenset(
    {
        "request_id",
        "sample_id",
        "carrier_lock_key",
        "arm",
        "text",
        "admitted",
        "request_sha256",
        "response_sha256",
        "response_text_sha256",
    }
)


def _verify_outputs(raw: bytes | None, split_ids: frozenset) -> tuple[Mapping[str, object], ...]:
    if raw is None:
        return ()
    try:
        text = raw.decode("utf-8")
    except UnicodeError as error:
        raise BundleError(f"outputs artifact is not valid UTF-8: {error}") from error
    lines = _split_jsonl(text)
    if not lines:
        raise BundleError("outputs artifact is empty")
    rows: list[Mapping[str, object]] = []
    seen: dict[str, int] = {}
    for number, line in enumerate(lines, start=1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise BundleError(f"outputs line {number} malformed: {error}") from error
        if not isinstance(row, Mapping):
            raise BundleError(f"outputs line {number} must be a JSON object")
        missing = _REQUIRED_OUTPUTS_FIELDS - set(row)
        if missing:
            raise BundleError(f"outputs line {number} lacks required fields {sorted(missing)}")
        text_value = row["text"]
        if not isinstance(text_value, str):
            raise BundleError(f"outputs line {number} field 'text' must be a string")
        recomputed = hashlib.sha256(text_value.encode("utf-8")).hexdigest()
        if recomputed != row["response_text_sha256"]:
            raise BundleError(
                f"outputs row {row.get('sample_id')!r} (request {row.get('request_id')!r}): "
                "text does not match its recorded response_text_sha256 -- the text was "
                "mutated after the model response was recorded (I7)"
            )
        sample_id = row["sample_id"]
        if not isinstance(sample_id, str):
            raise BundleError(f"outputs line {number} field 'sample_id' must be a string")
        seen[sample_id] = seen.get(sample_id, 0) + 1
        rows.append(row)
    duplicates = sorted(sample_id for sample_id, count in seen.items() if count > 1)
    if duplicates:
        raise BundleError(f"outputs sample set contains duplicate sample ids: {duplicates}")
    row_ids = frozenset(seen)
    missing_ids = sorted(split_ids - row_ids)
    if missing_ids:
        raise BundleError(
            f"outputs sample set is missing frozen split ids: {missing_ids[:10]}"
            + (" (+more)" if len(missing_ids) > 10 else "")
        )
    extra_ids = sorted(row_ids - split_ids)
    if extra_ids:
        raise BundleError(
            f"outputs sample set contains ids outside the frozen split: {extra_ids[:10]}"
            + (" (+more)" if len(extra_ids) > 10 else "")
        )
    return tuple(rows)


def _verify_raw_trace(
    raw: bytes | None, trace_manifest_raw: bytes | None
) -> Mapping[str, Mapping[str, object]]:
    if raw is None:
        return {}
    try:
        text = raw.decode("utf-8")
    except UnicodeError as error:
        raise BundleError(f"raw trace artifact is not valid UTF-8: {error}") from error
    lines = _split_jsonl(text)
    records: dict[str, Mapping[str, object]] = {}
    hashes: dict[str, str] = {}
    for number, line in enumerate(lines, start=1):
        try:
            document = json.loads(line)
        except json.JSONDecodeError as error:
            raise BundleError(f"raw trace line {number} malformed: {error}") from error
        if not isinstance(document, Mapping) or not {"channel", "record_id", "payload"} <= set(
            document
        ):
            raise BundleError(f"raw trace line {number} must carry channel/record_id/payload")
        record_id = document["record_id"]
        if not isinstance(record_id, str):
            raise BundleError(f"raw trace line {number} record_id must be a string")
        if record_id in records:
            raise BundleError(f"raw trace contains duplicate record_id {record_id!r}")
        try:
            content_hash = TraceRecord(
                channel=document["channel"], record_id=record_id, payload=document["payload"]
            ).content_hash()
        except (TraceContractError, BoundaryViolation) as error:
            raise BundleError(f"raw trace record {record_id!r} is invalid: {error}") from error
        records[record_id] = dict(document["payload"])
        hashes[record_id] = content_hash

    if trace_manifest_raw is not None:
        try:
            trace_manifest_doc = json.loads(trace_manifest_raw.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as error:
            raise BundleError(f"trace manifest artifact is not valid JSON: {error}") from error
        manifest_records = trace_manifest_doc.get("records")
        if not isinstance(manifest_records, Mapping):
            raise BundleError("trace manifest artifact lacks a 'records' mapping")
        missing_in_manifest = sorted(set(hashes) - set(manifest_records))
        extra_in_manifest = sorted(set(manifest_records) - set(hashes))
        if missing_in_manifest or extra_in_manifest:
            raise BundleError(
                "trace manifest does not match the raw trace record set: "
                f"missing_in_manifest={missing_in_manifest[:10]} "
                f"extra_in_manifest={extra_in_manifest[:10]}"
            )
        for record_id, recorded_hash in manifest_records.items():
            if hashes[record_id] != recorded_hash:
                raise BundleError(
                    f"trace manifest hash for record {record_id!r} does not match the "
                    "raw trace record bytes (I7: trace manifest must match raw trace)"
                )
    return records


def _verify_outputs_trace_binding(
    outputs_rows: tuple[Mapping[str, object], ...], trace_records: Mapping[str, Mapping[str, object]]
) -> None:
    # CRITICAL fix (T6 fix round): the ORIGINAL code also returned early when
    # trace_records was empty -- "there are no trace records to bind against"
    # -- which meant an emptied (or never-populated) trace silently defeated
    # this ENTIRE check for a non-empty outputs file: truncate raw_trace to
    # nothing, empty trace_manifest's records, recompute those two outer
    # hashes, and any forged outputs text (with its response_text_sha256
    # recomputed to match) sailed straight through verify_bundle. There is
    # no legitimate reason for a COMPLETED, non-empty outputs bundle to have
    # zero trace records (every sample emits at least an OBS record and a
    # MODEL_RESPONSE record) -- so an empty/short trace against non-empty
    # outputs must FAIL, not silently skip. Only truly EMPTY outputs (already
    # refused earlier as "outputs artifact is empty" whenever an outputs
    # artifact exists at all) has nothing to bind.
    if not outputs_rows:
        return
    for row in outputs_rows:
        request_id = row["request_id"]
        response_record_id = f"{request_id}/response"
        if response_record_id not in trace_records:
            raise BundleError(
                f"outputs request_id {request_id!r} has no matching trace record "
                f"{response_record_id!r} (I7: every outputs request_id must appear in the trace)"
            )
        payload = trace_records[response_record_id]
        for field in ("text", "response_sha256", "response_text_sha256"):
            if payload.get(field) != row.get(field):
                raise BundleError(
                    f"outputs {field} for request {request_id!r} disagrees with the trace "
                    f"record {response_record_id!r}"
                )
        request_record_id = f"{request_id}/request"
        request_payload = trace_records.get(request_record_id)
        if request_payload is not None and request_payload.get("payload_sha256") != row.get(
            "request_sha256"
        ):
            raise BundleError(
                f"outputs request_sha256 for request {request_id!r} disagrees with the trace "
                f"record {request_record_id!r}"
            )


def verify_bundle(manifest_path: Path) -> VerifiedBundle:
    """Recompute every hash the manifest names from the bytes actually on
    disk right now, and cross-check outputs<->split<->trace. Never trusts a
    single number the manifest merely asserts about itself."""

    manifest_path = Path(manifest_path)
    manifest_bytes = _read_bytes(manifest_path, "run manifest")
    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise BundleError(f"run manifest {manifest_path} is not valid JSON: {error}") from error
    if not isinstance(manifest, Mapping):
        raise BundleError(f"run manifest {manifest_path} must be a JSON object")
    if manifest.get("schema") != RUN_MANIFEST_SCHEMA:
        raise BundleError(
            f"run manifest schema must be {RUN_MANIFEST_SCHEMA!r}, got {manifest.get('schema')!r}"
        )
    if manifest.get("study") != STUDY_SLUG:
        raise BundleError(
            f"run manifest study must be {STUDY_SLUG!r}, got {manifest.get('study')!r}"
        )
    status = manifest.get("status")
    if status not in _VALID_STATUSES:
        raise BundleError(f"run manifest status must be one of {_VALID_STATUSES}, got {status!r}")
    if status == STATUS_COMPLETED:
        for label, key in (("outputs", "outputs"), ("raw trace", "raw_trace"), ("trace manifest", "trace_manifest")):
            entry = manifest.get(key)
            if not isinstance(entry, Mapping) or not entry.get("path"):
                raise BundleError(
                    f"run manifest status is COMPLETED but lacks a usable {label} entry"
                )

    outputs_raw = _verify_artifact(manifest.get("outputs"), "outputs")
    raw_trace_raw = _verify_artifact(manifest.get("raw_trace"), "raw trace")
    trace_manifest_raw = _verify_artifact(manifest.get("trace_manifest"), "trace manifest")
    _verify_artifact(manifest.get("scores"), "scores")
    _verify_artifact(manifest.get("session_receipt"), "session receipt")

    split = manifest.get("split")
    if not isinstance(split, Mapping) or not isinstance(split.get("ids"), list):
        raise BundleError("run manifest lacks a usable split.ids list")
    split_ids = frozenset(split["ids"])

    outputs_rows = _verify_outputs(outputs_raw, split_ids)
    trace_records = _verify_raw_trace(raw_trace_raw, trace_manifest_raw)
    _verify_outputs_trace_binding(outputs_rows, trace_records)

    attempt_meta = manifest.get("attempt")
    if not isinstance(attempt_meta, Mapping) or not attempt_meta.get("state_path"):
        raise BundleError("run manifest lacks an attempt.state_path binding")
    attempt_state_path = Path(str(attempt_meta["state_path"]))
    if not attempt_state_path.is_file():
        # A failure before FrozenCoreAdapter construction ever ran (e.g. a
        # protocol-hash/carrier mismatch caught earlier in run_experiment)
        # leaves no attempt file at all -- distinct from a genuine read/parse
        # failure below. Not OPENED either way, which is all finalize_bundle
        # needs to know to refuse it; not a bundle-integrity error by itself.
        attempt_state = ATTEMPT_STATE_NEVER_OPENED
    else:
        try:
            attempt_state = AttemptHandle(
                path=attempt_state_path,
                run_id=str(attempt_meta.get("run_id", manifest.get("run_id"))),
                attempt_id=str(attempt_meta.get("attempt_id", "")),
            ).state()
        except AttemptError as error:
            raise BundleError(f"cannot read this bundle's attempt state: {error}") from error

    outputs_meta = manifest.get("outputs")
    outputs_path = (
        Path(str(outputs_meta["path"])) if isinstance(outputs_meta, Mapping) else None
    )

    return VerifiedBundle(
        manifest_path=manifest_path,
        manifest=manifest,
        outputs_path=outputs_path,
        outputs_rows=outputs_rows,
        trace_records=trace_records,
        split_ids=split_ids,
        attempt_state=attempt_state,
    )


# ---------------------------------------------------------------------------
# Finalize: verify -> score -> write scores -> re-verify -> upload -> ledger
# -> mark FINALIZED. The only path that ever transitions an attempt to
# FINALIZED.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FinalizeResult:
    manifest_path: Path
    scores_path: Path
    ledger_markdown_path: Path
    ledger_json_path: Path
    ledger_row_markdown: str
    ledger_cells: Mapping[str, str]
    mlflow_run_id: str | None
    attempt_state: str


def finalize_bundle(
    manifest_path: Path,
    lock: Mapping[str, object],
    root: Path,
    *,
    ledger_cells: Mapping[str, str] | None = None,
    tracking_uri: str | None = None,
    mlflow_metrics: Mapping[str, float] | None = None,
) -> FinalizeResult:
    """Verify, score, write scores, re-verify, (optionally) upload to
    MLflow, emit a machine-derived ledger row, and mark the attempt
    FINALIZED. Refuses (``BundleError``) unless the manifest's own status is
    COMPLETED AND the attempt's durable state file (re-read fresh, never
    trusted from the manifest) is OPENED -- the latter is the authoritative
    check: a hand-edited manifest claiming COMPLETED cannot finalize an
    attempt whose actual on-disk state is ABORTED."""

    # Repo confinement (IMPORTANT fix, T6 fix round), checked independently
    # here too -- defense in depth mirroring build_manifest's own check,
    # in case a manifest ever reaches this function by some path other than
    # build_manifest (a hand-placed file, a future caller). Scores and
    # ledger rows are written under the SAME directory as manifest_path, so
    # one check here covers all of this function's writes.
    _refuse_if_inside_repo(Path(manifest_path).parent, "run bundle directory")

    bundle = verify_bundle(manifest_path)
    if bundle.manifest.get("status") != STATUS_COMPLETED:
        raise BundleError(
            f"cannot finalize {manifest_path}: manifest status is "
            f"{bundle.manifest.get('status')!r}, not {STATUS_COMPLETED!r}"
        )
    if bundle.attempt_state != STATE_OPENED:
        raise BundleError(
            f"cannot finalize {manifest_path}: the attempt's durable state on disk is "
            f"{bundle.attempt_state!r}, not {STATE_OPENED!r} -- the attempt file, not the "
            "manifest's self-reported status, is authoritative (I7)"
        )

    scores = score_bundle(bundle, lock, root)
    run_dir = Path(manifest_path).resolve().parent
    run_id = str(bundle.manifest["run_id"])
    scores_path = run_dir / f"{run_id}.scores.json"
    write_json_artifact(scores_path, scores)
    _attach_scores(Path(manifest_path), scores_path)

    # Re-verify over the now-complete bundle: this both closes the loop the
    # brief asks for AND proves the scores artifact we just wrote binds
    # correctly (any write corruption would fail here, before upload/ledger).
    bundle = verify_bundle(manifest_path)

    mlflow_run_id = None
    if tracking_uri is not None:
        mlflow_run_id = log_bundle(bundle, tracking_uri, metrics=mlflow_metrics)

    cells = dict(ledger_cells or {})
    if mlflow_run_id is not None:
        # Overwrite (not setdefault): the caller cannot have known the real
        # mlflow_run_id before this call returned it, so any hand-supplied
        # placeholder here is necessarily stale, not an intentional override.
        cells["MLflow run"] = mlflow_run_id
    row_markdown, merged_cells = ledger_row_for_bundle(bundle, cells)
    ledger_markdown_path = run_dir / f"{run_id}.ledger-row.md"
    ledger_json_path = run_dir / f"{run_id}.ledger-row.json"
    ledger_markdown_path.write_text(row_markdown + "\n", encoding="utf-8", newline="\n")
    write_json_artifact(ledger_json_path, merged_cells)

    attempt_meta = bundle.manifest["attempt"]
    handle = AttemptHandle(
        path=Path(str(attempt_meta["state_path"])),
        run_id=str(attempt_meta["run_id"]),
        attempt_id=str(attempt_meta["attempt_id"]),
    )
    handle.mark_finalized()

    return FinalizeResult(
        manifest_path=Path(manifest_path),
        scores_path=scores_path,
        ledger_markdown_path=ledger_markdown_path,
        ledger_json_path=ledger_json_path,
        ledger_row_markdown=row_markdown,
        ledger_cells=merged_cells,
        mlflow_run_id=mlflow_run_id,
        attempt_state=STATE_FINALIZED,
    )


def abort_attempt_if_opened(data_root: Path, run_id: str, attempt_id: str | None, *, reason: str) -> bool:
    """Thin convenience wrapper so ``core.driver`` doesn't need to know the
    attempts-root layout: mark the attempt ABORTED if it was ever opened.
    A ``None``/malformed ``attempt_id`` is a no-op (False) -- there was never
    anything to abort at the store layer in that case."""

    if not isinstance(attempt_id, str) or not attempt_id.strip():
        return False
    store = AttemptStore(Path(data_root) / "attempts")
    try:
        return store.abort_if_opened(run_id, attempt_id, reason=reason)
    except AttemptError:
        return False
