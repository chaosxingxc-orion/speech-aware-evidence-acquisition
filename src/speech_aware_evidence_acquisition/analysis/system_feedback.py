"""Read complete system trajectories and separate terminal construction feedback.

All execution roles remain in the shared trajectory representation. Official
labels/counts stay in the offline terminal-feedback section, never role context.
This first feedback adapter is SLURP-specific; trajectory custody is shared.
"""
from __future__ import annotations

import copy
import math
from collections.abc import Mapping
from pathlib import Path

from ..core.flight.receipts import _validate_document
from ..rails.finite_policy_artifacts import _confined_file, _pinned_json
from ..rails.hashing import content_hash
from ..reproduction.slurp_scoring import parse_slu_response
from .native_episode_source import verify_native_episode_source
from .official_metric_feedback import extract_official_feedback, pooled_f1


class SystemFeedbackError(ValueError):
    """A terminal score cannot be credited to a complete verified system."""


def _mapping(value, label):
    if not isinstance(value, Mapping):
        raise SystemFeedbackError(f"{label} must be an object")
    return value


def _same_path(value, expected, label):
    if not isinstance(value, str) or Path(value).resolve() != expected.resolve():
        raise SystemFeedbackError(f"{label} path disagrees")


def _score_rows(scores, scorer, sample_ids):
    entry = _mapping(scores.get(scorer), "official scorer")
    rows = entry.get("per_sample")
    if not isinstance(rows, list) or len(rows) != len(sample_ids):
        raise SystemFeedbackError("official scores must cover every system trajectory once")
    feedback = {}
    for row in rows:
        row = _mapping(row, "official row")
        sid = row.get("sample_id")
        if not isinstance(sid, str) or sid not in sample_ids or sid in feedback:
            raise SystemFeedbackError("official score IDs differ from the full roster")
        # The registered official scorer's own counts are the authority.
        # A separately reported normalized view must not replace these silently.
        item = extract_official_feedback(row)
        feedback[sid] = item
    official = _mapping(_mapping(entry.get("aggregate"), "aggregate").get("official"), "official aggregate")
    recorded = official.get("slu_f1")
    if (isinstance(recorded, bool) or not isinstance(recorded, (int, float))
            or not math.isfinite(recorded)
            or not math.isclose(pooled_f1(list(feedback.values())), recorded, rel_tol=0, abs_tol=1e-6)):
        raise SystemFeedbackError("complete official counts do not reproduce aggregate SLU-F1")
    return feedback



def _score_custody(stages, paths, hashes, job, attempt_id):
    """Bind the supplied score job to the completed flight, including finalization."""
    seal = stages["seal"]
    score = _mapping(stages.get("score"), "complete score stage")
    _same_path(score.get("jobs_path"), paths["score_jobs"], "score-stage jobs")
    result = _mapping(score.get("result"), "official score batch result")
    if (score.get("include_per_sample") is not True or score.get("job_count") != 1
            or type(result.get("failed")) is not int or result["failed"] != 0
            or result.get("succeeded") != 1 or result.get("job_count") != 1):
        raise SystemFeedbackError("flight must contain one successful complete official score")
    rows = result.get("jobs")
    if not isinstance(rows, list) or len(rows) != 1:
        raise SystemFeedbackError("score result job population differs")
    row = _mapping(rows[0], "score result job")
    if (row.get("job_id") != attempt_id or row.get("status") != "succeeded"
            or type(row.get("returncode")) is not int or row["returncode"] != 0):
        raise SystemFeedbackError("official score result does not finalize this attempt")
    _same_path(row.get("manifest"), paths["manifest"], "score result manifest")
    deferred = (seal.get("finalize") or {}).get("status") == "deferred-to-score-worker"
    operation = "finalize" if deferred else "score"
    if row.get("operation") != operation or result.get("operation") != operation:
        raise SystemFeedbackError("official score operation differs from sealed execution")
    expected_fields = {"job_id", "manifest", "ledger_cells"} if deferred else {"job_id", "manifest"}
    if set(job) != expected_fields:
        raise SystemFeedbackError("score job fields differ from the ordinary flight contract")
    if deferred:
        _same_path(seal.get("score_jobs_path"), paths["score_jobs"], "sealed score jobs")
        if seal.get("score_jobs_sha256") != hashes["score_jobs"]:
            raise SystemFeedbackError("official score job hash differs from its generation seal")
        if (score.get("operation") != "finalize"
                or score.get("source_generation_manifest_sha256") != seal.get("generation_manifest_sha256")
                or score.get("finalized_manifest_sha256") != hashes["manifest"]):
            raise SystemFeedbackError("official score finalization source/output hashes disagree")
        ledger_path = Path(str(seal.get("score_ledger_cells_path"))).resolve()
        _same_path(job.get("ledger_cells"), ledger_path, "sealed job ledger")
        _same_path(row.get("ledger_cells"), ledger_path, "score result ledger")


def load_system_feedback(*, data_root: Path, repo_root: Path, binding: Mapping) -> dict:
    """Verify an entire TRAIN round before constructing any reward record.

    repo_root is the source's retained clean checkout, not necessarily the checkout
    running this reader. No model, tokenization endpoint or scorer is called.
    """
    from .system_trajectory import export_system_trajectories

    keys = {"schema", "execution_profile", "feedback_role", "manifest", "phases",
            "flight_receipts", "score_jobs", "scorer_id"}
    if not isinstance(binding, Mapping) or set(binding) != keys:
        raise SystemFeedbackError("system feedback binding has missing or unknown fields")
    if (binding["schema"] != "saea-system-feedback-binding-v1"
            or binding["execution_profile"] != "model-free-check"
            or binding["feedback_role"] != "construction"
            or binding["scorer_id"] != "slurp-slu-official-train"):
        raise SystemFeedbackError("system feedback currently admits only official SLURP TRAIN construction")
    root = Path(data_root)
    docs, paths, hashes = {}, {}, {}
    auxiliary_pins = {}
    # Read no task scores until source pins and full flight closure are established.
    for name in ("manifest", "phases", "flight_receipts", "score_jobs"):
        doc, sha = _pinned_json(root, binding[name], name)
        docs[name], hashes[name] = _mapping(doc, name), sha
        paths[name] = _confined_file(root, binding[name]["relpath"])
    source = verify_native_episode_source(
        manifest_path=paths["manifest"], expected_manifest_sha256=hashes["manifest"],
        phase_artifact_path=paths["phases"], expected_phase_sha256=hashes["phases"],
        repo_root=Path(repo_root), data_root=root,
    )
    bundle, plan = source.bundle, source.plan
    if plan.split_role != "discovery" or binding["scorer_id"] not in bundle.manifest["scorers"]:
        raise SystemFeedbackError("construction feedback split/scorer differs from its frozen flight")
    receipts = _validate_document(dict(docs["flight_receipts"].get("receipts", docs["flight_receipts"])))
    if receipts["run_id"] != plan.run_id or receipts["attempt_id"] != plan.attempt_id:
        raise SystemFeedbackError("flight receipt belongs to another system run")
    stages = receipts["stages"]
    seal = _mapping(stages.get("seal"), "complete seal stage")
    _same_path(seal.get("phases_path"), paths["phases"], "sealed phases")
    _same_path(seal.get("manifest_path"), paths["manifest"], "sealed manifest")
    _same_path(seal.get("outputs_path"), bundle.outputs_path, "sealed outputs")
    if (seal.get("phases_sha256") != hashes["phases"]
            or seal.get("outputs_row_count") != len(source.sample_ids)
            or seal.get("phase_count") != 1 or seal.get("resume") is not None):
        raise SystemFeedbackError("seal does not cover this complete ordinary system")
    # Deferred scoring legitimately replaces the manifest's score attachment.
    # Its generation-time manifest hash is not the finalized manifest's raw hash.
    if "generation_manifest_path" in seal:
        generation_path = Path(str(seal["generation_manifest_path"])).resolve()
        if generation_path.parent != paths["manifest"].parent:
            raise SystemFeedbackError("generation manifest escapes the source run")
        auxiliary_pins["generation_manifest"] = {
            "relpath": str(generation_path.relative_to(root.resolve())),
            "sha256": seal.get("generation_manifest_sha256"),
        }
        generation, hashes["generation_manifest"] = _pinned_json(
            root, auxiliary_pins["generation_manifest"], "generation manifest")
        for key in ("run_id", "plan", "config", "split", "outputs", "raw_trace", "trace_manifest"):
            if generation.get(key) != bundle.manifest.get(key):
                raise SystemFeedbackError(f"finalization changed generation {key}")
        if seal.get("manifest_sha256") != seal.get("generation_manifest_sha256"):
            raise SystemFeedbackError("seal differs from preserved generation manifest")
    elif seal.get("manifest_sha256") != hashes["manifest"]:
        raise SystemFeedbackError("seal manifest hash lacks a preserved generation binding")
    job = docs["score_jobs"]
    if job.get("job_id") != plan.attempt_id:
        raise SystemFeedbackError("score job belongs to another attempt")
    _same_path(job.get("manifest"), paths["manifest"], "official score job")
    _score_custody(stages, paths, hashes, job, plan.attempt_id)
    if (seal.get("finalize") or {}).get("status") == "deferred-to-score-worker":
        ledger_path = Path(str(seal["score_ledger_cells_path"])).resolve()
        if ledger_path.parent != paths["manifest"].parent:
            raise SystemFeedbackError("sealed score ledger escapes the source run")
        auxiliary_pins["score_ledger_cells"] = {
            "relpath": str(ledger_path.relative_to(root.resolve())),
            "sha256": seal.get("score_ledger_cells_sha256"),
        }
        _, hashes["score_ledger_cells"] = _pinned_json(
            root, auxiliary_pins["score_ledger_cells"], "sealed score ledger")
    score_meta = _mapping(bundle.manifest.get("scores"), "attached scores")
    score_path = Path(str(score_meta.get("path"))).resolve()
    if score_path.parent != paths["manifest"].parent:
        raise SystemFeedbackError("attached scores escape the system source run")
    score_pin = {"relpath": str(score_path.relative_to(root.resolve())), "sha256": score_meta.get("sha256")}
    scores, hashes["scores"] = _pinned_json(root, score_pin, "attached official scores")
    if set(scores) != set(bundle.manifest["scorers"]):
        raise SystemFeedbackError("attached score mapping differs from configured scorers")
    counts = _score_rows(scores, binding["scorer_id"], source.sample_ids)
    trajectories = export_system_trajectories(source)
    episodes = trajectories["trajectories"]
    if tuple(row["sample_id"] for row in episodes) != source.sample_ids:
        raise SystemFeedbackError("system export changed the ordered roster")
    terminal = []
    for episode in episodes:
        sid = episode["sample_id"]
        item, output = counts[sid], source.output_rows[sid]
        native = output["native_episode_receipt"]
        flags = [name for name in ("react_exhaustion", "planner_action_illegal", "abstention_receipt")
                 if native.get(name)]
        if native.get("truncation_events"):
            flags.append("truncation_events")
        if any(route.get("legal") is False or route.get("disposition") == "planner_action_illegal"
               for route in native.get("planner_routes", [])):
            if "planner_action_illegal" not in flags:
                flags.append("planner_action_illegal")
        disposition = native.get("terminal_disposition")
        if isinstance(disposition, Mapping) and isinstance(disposition.get("reason"), str):
            flags.append("terminal:" + disposition["reason"])
        terminal.append({
            "sample_id": sid, "trajectory_sha256": episode["trajectory_sha256"],
            "delivered_output_sha256": content_hash(output),
            "tp": item.tp, "fp": item.fp, "fn": item.fn,
            "intent_exact": item.intent_exact, "format_ok": bool(parse_slu_response(output["text"])[-1]),
            "fallback_flags": flags, "episode_events": episode["episode_events"],
        })
    for name in ("manifest", "phases", "flight_receipts", "score_jobs"):
        _pinned_json(root, binding[name], name)
    _pinned_json(root, score_pin, "attached official scores")
    for name, pin in auxiliary_pins.items():
        _pinned_json(root, pin, name)
    result = {
        "schema": "saea-slurp-system-feedback-v1", "feedback_role": "construction",
        "binding_sha256": content_hash(dict(binding)),
        "source_bindings": copy.deepcopy(dict(binding)),
        "resolved_auxiliary_sources": {**auxiliary_pins, "scores": score_pin},
        "source_sha256": hashes, "run_id": plan.run_id, "attempt_id": plan.attempt_id,
        "split_identity_hash": plan.split_identity_hash,
        "system_trajectories": trajectories, "terminal_feedback": terminal,
        "policy_supply_receipt": (stages["run_phases"].get("phase_supply") or {}).get("finite_supply_policy"),
        "reward_scope": "complete delivered system; intermediate states carry no gold feedback",
        "model_contacts_added": 0, "scorer_contacts_added": 0,
    }
    choices = {
        row["sample_id"]: row["system_policy_decision"]
        for row in episodes if "system_policy_decision" in row
    }
    if choices:
        if set(choices) != set(source.sample_ids):
            raise SystemFeedbackError("complete policy choices must cover every terminal episode")
        result["policy_episode_decisions"] = choices
    result["content_sha256"] = content_hash(result)
    return result


def write_system_feedback(path: Path, report: Mapping) -> str:
    """Publish one immutable derived report; identical retries add no credit."""
    import hashlib
    import json
    import os

    unsigned = dict(report)
    claimed = unsigned.pop("content_sha256", None)
    if claimed != content_hash(unsigned):
        raise SystemFeedbackError("derived report content hash disagrees")
    raw = (json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError:
        if path.read_bytes() != raw:
            raise SystemFeedbackError("refusing to overwrite a different or partial system report")
    return hashlib.sha256(raw).hexdigest()
