"""Complete, source-bound semantic material for the existing context learners.

This offline projection adds no policy, scorer or model contact. The public
export freshly qualifies the whole family before opening semantic sources.
It never discovers arbitrary paths from a proposer or copies root chat/logs.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..analysis.native_episode_source import verify_native_episode_source
from ..analysis.system_trajectory import export_system_trajectories
from .hashing import content_hash
from .prepared_feedback import reject_non_latin_scripts
from .system_context_learning import _qualified_feedback
from .system_text_policy import canonical, require


def materialize_context_trajectory(source, sample_id):
    """Preserve one verified full episode, including interrupted/failed visits.

    The caller owns READ authority; use export_context_source_material for a
    learner entry. No truncation, success selection, gold or reward is added.
    Original record hashes remain in the shared trajectory index.
    """
    return _materialize_indexed_trajectory(
        source, sample_id, export_system_trajectories(source)
    )


def _materialize_indexed_trajectory(source, sample_id, index):
    """Reuse the exact verified index across a bulk export without changing bytes."""
    require(sample_id in index["sample_ids"], "sample is outside the verified source")
    trajectory = next(r for r in index["trajectories"] if r["sample_id"] == sample_id)
    result = {
        "schema": "saea-context-trajectory-material-v1",
        "sample_id": sample_id,
        "source": index["source"],
        "trajectory": trajectory,
        "phase_result": source.phase_results[sample_id],
        "terminal_output": source.output_rows[sample_id],
        "trace_records": {
            r["record_id"]: source.bundle.trace_records[r["record_id"]]
            for r in trajectory["trace_records"]
        },
        "omissions": [],
        "scope": "Complete recorded episode; optimizer only, never runtime knowledge.",
    }
    # Refuse rather than silently remove or translate an immutable source.
    # A separately pinned complete English translation is required if this fails.
    reject_non_latin_scripts(result)
    result["material_sha256"] = content_hash(result)
    return json.loads(canonical(result))


def export_context_source_material(
    archive, *, bindings, recipe_pin, repo_root, data_root, source_specs
):
    """Qualify all members, then publish complete candidate-only episode files.

    source_specs only pins each candidate's phase file and recorded clean source
    checkout. Manifest identity comes from the already-qualified family bindings.
    Controls still qualify the family but are not copied to the learner material.
    The final index is published last; incomplete output never becomes an input.
    """
    qualified = _qualified_feedback(
        bindings, recipe_pin=recipe_pin, repo_root=repo_root
    )
    evidence, recipe, registration, _, candidates, _, _ = qualified
    require(
        set(source_specs) == set(candidates),
        "exact candidate source specifications required",
    )
    indexed = {b["candidate_id"]: b for b in bindings}
    groups = {
        g["sample_id"]: {m["candidate_id"]: m for m in g["members"]}
        for g in evidence["feedback"]["groups"]
    }
    directory = "context-learning/material/" + recipe_pin["sha256"]
    pending, members = [], {}
    for candidate in candidates:
        spec = source_specs[candidate]
        require(set(spec) == {"repo_root", "phase"}, "unexpected source specification")
        manifest = indexed[candidate]["config"]["manifest"]
        phase = spec["phase"]
        source = verify_native_episode_source(
            manifest_path=Path(manifest["path"]),
            expected_manifest_sha256=manifest["sha256"],
            phase_artifact_path=Path(phase["path"]),
            expected_phase_sha256=phase["sha256"],
            repo_root=Path(spec["repo_root"]),
            data_root=Path(data_root),
        )
        expected = registration["member_bindings"][candidate]
        require(
            source.plan.run_id == expected["run_id"]
            and source.plan.attempt_id == expected["attempt_id"]
            and source.composed.config_hash == expected["config_hash"],
            "semantic source identity differs",
        )
        require(
            len(source.sample_ids) == len(recipe["sample_ids"])
            and set(source.sample_ids) == set(recipe["sample_ids"]),
            "semantic source cohort differs",
        )
        members[candidate] = []
        trajectory_index = export_system_trajectories(source)
        for sid in recipe["sample_ids"]:
            execution = groups[sid][candidate]["execution"]
            require(
                source.bundle.manifest["raw_trace"] == execution["trace"]
                and source.bundle.manifest["outputs"] == execution["terminal_output"],
                "semantic source differs from qualified feedback",
            )
            document = _materialize_indexed_trajectory(source, sid, trajectory_index)
            path = (
                directory
                + "/"
                + content_hash({"candidate": candidate, "sample": sid})
                + ".json"
            )
            pending.append((path, document))
            members[candidate].append(
                {
                    "sample_id": sid,
                    "archive_path": path,
                    "material_sha256": document["material_sha256"],
                    "characters": len(canonical(document)),
                    "omissions": [],
                }
            )
    # Recheck authority, score jobs and custody before publishing any material.
    fresh = _qualified_feedback(bindings, recipe_pin=recipe_pin, repo_root=repo_root)
    require(
        content_hash(fresh[0]) == content_hash(evidence)
        and fresh[1:3] == qualified[1:3],
        "complete family changed during semantic export",
    )
    index = {
        "schema": "saea-context-material-index-v1",
        "recipe": recipe_pin,
        "family_id": recipe["family_id"],
        "family_sha256": content_hash(evidence),
        "read_authority": evidence["read_authority"],
        "source_specs": source_specs,
        "sample_ids": recipe["sample_ids"],
        "members": members,
        "contacts_added": {"model": 0, "scorer": 0},
        "runtime_admission": False,
    }
    index["index_sha256"] = content_hash(index)
    for path, document in pending:
        archive._write(path, document)
    archive._write(directory + "/index.json", index)
    return index
