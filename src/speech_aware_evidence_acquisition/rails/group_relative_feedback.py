"""Build offline native-quality vector feedback from verified TRAIN trajectories.

This is feedback preparation, not a policy update or a causal-effect estimator.
It never loads task references, emits answers, invokes a scorer, or changes weights.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from pathlib import Path

from ..core.preparation import hash_stable_file, prepare_artifact
from .hashing import content_hash
from .reward_link_io import read_verified_reward_link_artifact
from .reward_links import SLURP_NATIVE_FIELDS, RewardLinkError, audio2tool_native_counts

GROUP_FEEDBACK_SCHEMA = "saea-group-relative-quality-feedback-v1"


class GroupFeedbackError(ValueError):
    """A complete paired source or native numeric feedback binding is invalid."""


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise GroupFeedbackError("quality values must be finite numbers")
    return float(value)


def _advantages(vectors):
    """Center each quality dimension separately; never scalarize competing goals."""
    if not isinstance(vectors, Sequence) or len(vectors) < 2:
        raise GroupFeedbackError("a group needs at least two actual trajectories")
    if not isinstance(vectors[0], Mapping) or not vectors[0]:
        raise GroupFeedbackError("nonempty quality vectors are required")
    keys = tuple(vectors[0])
    if any(not isinstance(v, Mapping) or set(v) != set(keys) for v in vectors):
        raise GroupFeedbackError("group quality dimensions differ")
    result = [{} for _ in vectors]
    for key in keys:
        values = [_number(v[key]) for v in vectors]
        mean = math.fsum(values) / len(values)
        std = math.sqrt(math.fsum((v - mean) ** 2 for v in values) / len(values))
        for row, value in zip(result, values, strict=True):
            centered = value - mean
            row[key] = {"value": value, "mean": mean, "std": std,
                        "centered": centered, "advantage": centered / std if std else 0.0}
    return result


def _native_quality(carrier, counts):
    """Use sample-native statistics; cohort pooled micro F1 remains an evaluator."""
    if carrier == "audio2tool":
        try:
            values = audio2tool_native_counts(counts)
        except RewardLinkError as error:
            raise GroupFeedbackError(str(error)) from error
        quality = {key: values[key] for key in (
            "tool_correct", "exact_match", "param_exact_match", "param_precision",
            "param_recall", "param_f1", "parsed",
        )}
        # The official scorer stores zeroes for inapplicable multi-tool fields.
        # Keep applicability/counts in native_counts, not as a false quality loss.
        if values["is_multi_tool"]:
            quality.update({key: values[key] for key in (
                "multi_tool_all_match", "multi_tool_recall", "multi_tool_precision", "multi_tool_f1",
            )})
        return quality
    if carrier == "slurp":
        if set(counts) != set(SLURP_NATIVE_FIELDS):
            raise GroupFeedbackError("SLURP feedback requires all native sufficient counts")
        values = {key: _number(value) for key, value in counts.items()}
        if any(v < 0 for v in values.values()):
            raise GroupFeedbackError("native counts must be nonnegative")
        if any(values[key] not in (0, 1) for key in SLURP_NATIVE_FIELDS[:3]):
            raise GroupFeedbackError("intent, scenario and action must be binary")
        tp = values["slu_f1_word_tp"] + values["slu_f1_char_tp"]
        fp = values["slu_f1_word_fp"] + values["slu_f1_char_fp"]
        fn = values["slu_f1_word_fn"] + values["slu_f1_char_fn"]
        denominator = 2 * tp + fp + fn
        quality = {key: values[key] for key in SLURP_NATIVE_FIELDS[:3]}
        for prefix in ("slot_f1_exact", "slu_f1_word", "slu_f1_char"):
            part_tp = values[prefix + "_tp"]
            part_denominator = 2 * part_tp + values[prefix + "_fp"] + values[prefix + "_fn"]
            quality["sample_" + prefix] = 2 * part_tp / part_denominator if part_denominator else 0.0
        # This is the official pooled-count formula applied to one sample, not
        # an intent/entity scalar reward or the final cohort-level estimand.
        quality["sample_word_char_f1"] = 2 * tp / denominator if denominator else 0.0
        return quality
    if carrier in {"earnings21-original", "earnings22-original"}:
        if set(counts) != {"wer", "hits", "substitutions", "deletions", "insertions"}:
            raise GroupFeedbackError("ASR feedback requires all native counts")
        values = {key: _number(value) for key, value in counts.items()}
        if any(v < 0 for v in values.values()):
            raise GroupFeedbackError("native counts must be nonnegative")
        return {"negative_wer": -values["wer"]}
    raise GroupFeedbackError("carrier has no registered native group feedback")


def _read_source(binding):
    if not isinstance(binding, Mapping) or set(binding) != {"candidate_id", "config", "artifact"}:
        raise GroupFeedbackError("source binding has missing or unknown fields")
    cid, config, artifact = binding["candidate_id"], binding["config"], binding["artifact"]
    if not isinstance(cid, str) or not cid.strip():
        raise GroupFeedbackError("candidate ID must be nonempty text")
    if not isinstance(artifact, Mapping) or set(artifact) != {"path", "sha256"}:
        raise GroupFeedbackError("reward artifact pin has wrong fields")
    if not isinstance(artifact["path"], str) or not Path(artifact["path"]).is_absolute():
        raise GroupFeedbackError("reward artifact path must be absolute")
    try:
        path = Path(artifact["path"])
        _, digest, fingerprint = hash_stable_file(path, "group reward artifact")
        if digest != artifact["sha256"]:
            raise GroupFeedbackError("reward artifact hash mismatch")
        links = read_verified_reward_link_artifact(config, path)
        _, after, after_fingerprint = hash_stable_file(path, "group reward artifact after verification")
        if digest != after or fingerprint != after_fingerprint:
            raise GroupFeedbackError("reward artifact changed during verification")
        manifest_path = Path(config["manifest"]["path"])
        _, manifest_sha, _ = hash_stable_file(manifest_path, "group source manifest")
        if manifest_sha != config["manifest"]["sha256"]:
            raise GroupFeedbackError("source manifest changed during verification")
        raw = manifest_path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != manifest_sha:
            raise GroupFeedbackError("source manifest changed before metadata read")
        manifest = json.loads(raw)
        state_path = Path(manifest["attempt"]["state_path"])
        _, state_sha, _ = hash_stable_file(state_path, "group finalized attempt")
        state_raw = state_path.read_bytes()
        if hashlib.sha256(state_raw).hexdigest() != state_sha:
            raise GroupFeedbackError("attempt state changed before metadata read")
        state = json.loads(state_raw)
        if (
            state["state"] != "FINALIZED" or state["run_id"] != manifest["run_id"]
            or state["attempt_id"] != manifest["attempt"]["attempt_id"]
        ):
            raise GroupFeedbackError("actual attempt identity is not finalized")
    except (ValueError, RuntimeError, OSError, KeyError, TypeError) as error:
        raise GroupFeedbackError(f"cannot verify complete reward source: {error}") from error
    if not links:
        raise GroupFeedbackError("reward source has no complete construction cohort")
    metadata = {
        "candidate_id": cid, "reward_artifact": dict(artifact),
        "reward_config_sha256": content_hash(config),
        "manifest": dict(config["manifest"]),
        "complete_score_receipt": dict(config["complete_score_receipt"]),
        "run_id": manifest["run_id"], "attempt_id": manifest["attempt"]["attempt_id"],
        "attempt_state": {"path": str(state_path), "sha256": state_sha, "state": "FINALIZED"},
        "config_hash": manifest["config"]["config_hash"],
        "session_receipt": manifest["session_receipt"],
    }
    return metadata, links


def build_group_relative_feedback(source_bindings):
    """Reverify complete native TRAIN artifacts, then pair every sample exactly.

    The caller must preregister the source reads and scientific comparison.
    Different actual policies may have different configurations or predecessors;
    this artifact records realized outcomes and grants no causal/admission claim.
    """
    if (
        not isinstance(source_bindings, Sequence)
        or isinstance(source_bindings, (str, bytes))
        or len(source_bindings) < 2
    ):
        raise GroupFeedbackError("at least two complete candidate sources are required")
    sources, cohorts = [], []
    candidate_ids, runs, artifacts = set(), set(), set()
    expected = None
    for binding in source_bindings:
        metadata, links = _read_source(binding)
        identity = (metadata["run_id"], metadata["attempt_id"])
        if (
            metadata["candidate_id"] in candidate_ids or identity in runs
            or metadata["reward_artifact"]["sha256"] in artifacts
        ):
            raise GroupFeedbackError("duplicate candidate, actual attempt or reward source")
        candidate_ids.add(metadata["candidate_id"])
        runs.add(identity)
        artifacts.add(metadata["reward_artifact"]["sha256"])
        first = links[0]
        sample_ids = tuple(link.source.source_sample_id for link in links)
        signature = (first.carrier_lock_key, first.construction_roster_sha256,
                     content_hash(first.projection.as_json()), sample_ids)
        if expected is None:
            expected = signature
        if signature != expected or len(set(sample_ids)) != len(sample_ids):
            raise GroupFeedbackError("candidate construction, projection or ordered cohort differs")
        for link in links:
            link.validate()
            if (
                link.source.partition_role != "train"
                or link.carrier_lock_key != signature[0]
                or link.construction_roster_sha256 != signature[1]
                or content_hash(link.projection.as_json()) != signature[2]
                or set(link.native_score_vector["per_sample"]) != {link.source.source_sample_id}
            ):
                raise GroupFeedbackError("source contains a mixed or invalid TRAIN member")
        sources.append(metadata)
        cohorts.append(links)
    groups = []
    for index, sample_id in enumerate(expected[3]):
        counts = [dict(cohort[index].native_score_vector["per_sample"][sample_id])
                  for cohort in cohorts]
        quality = _advantages([_native_quality(expected[0], row) for row in counts])
        members = []
        for position, (source, cohort) in enumerate(zip(sources, cohorts, strict=True)):
            link = cohort[index]
            members.append({
                "candidate_id": source["candidate_id"],
                "reward_link_sha256": link.link_sha256, "source": link.source.as_json(),
                "native_counts": counts[position], "quality": quality[position],
            })
        groups.append({"sample_id": sample_id, "members": members})
    return {
        "schema": GROUP_FEEDBACK_SCHEMA, "status": "source-verified",
        "carrier_lock_key": expected[0], "construction_roster_sha256": expected[1],
        "projection_sha256": expected[2], "candidate_ids": [s["candidate_id"] for s in sources],
        "normalization": "per-sample per-metric population-standard-deviation; zero variance gives zero",
        "scalar_reward": None, "cost_penalty": None,
        "interpretation": "paired realized TRAIN trajectories; not causal effects or policy admission",
        "sources": sources, "groups": groups,
    }


def prepare_group_relative_feedback(source_bindings, output_path):
    """Persist through shared preparation; warm reads still reverify authority."""
    feedback = build_group_relative_feedback(source_bindings)
    try:
        _, implementation_sha, _ = hash_stable_file(Path(__file__), "group feedback implementation")
        return prepare_artifact(
            Path(output_path), kind="group-relative-quality-feedback",
            inputs={"feedback_sha256": content_hash(feedback),
                    "implementation_sha256": implementation_sha},
            producer=lambda: feedback, contact_class="model-free",
        )
    except (ValueError, RuntimeError, OSError) as error:
        raise GroupFeedbackError(str(error)) from error
