"""E0 D2: per-arm runtime-visible fields + executed leakage negative controls.

The artifact freezes, per engineering arm, exactly which fields may cross into the
frozen core's request path — and then *executes* the negative controls: every
forbidden runtime field (gold/reference/test-annotation/future-turn family) is
injected at three payload depths and must be rejected by
``contracts.assert_information_boundary``; cross-axis smuggling into OBS/ORG/
SUPPLY/USE trace channels must be rejected by ``contracts.TraceRecord``. A single
unexpected acceptance fails the generator closed.

General-audio exclusion is also executed here, with the excluded lock keys read
from ``configs/experiment/e0-model-free-closure.yaml`` (never hard-coded in
package code): no study config may configure them as a ``lock_key`` input, no
package source may mention them, and in the umbrella lock they must not belong to
any speech-aware profile.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Mapping

from ..contracts import (
    FORBIDDEN_RUNTIME_FIELDS,
    BoundaryViolation,
    TraceContractError,
    TraceRecord,
    assert_information_boundary,
)
from ..data.lock import load_lock, lock_entry
from .artifacts import REPO_ROOT, ArtifactError, today


E0_CONFIG_RELPATH = "configs/experiment/e0-model-free-closure.yaml"

ARM_VISIBLE_FIELDS: dict[str, tuple[str, ...]] = {
    "bare-core": (
        "request_id",
        "carrier_lock_key",
        "sample_id",
        "speech_ref",
        "media_relpath",
        "audio_seconds",
        "sample_rate_hz",
        "task_instruction",
        "history",
        "decoding_params",
    ),
    "fixed-legal-context": (
        "request_id",
        "carrier_lock_key",
        "sample_id",
        "speech_ref",
        "media_relpath",
        "audio_seconds",
        "sample_rate_hz",
        "task_instruction",
        "history",
        "decoding_params",
        "supplied_evidence",
        "evidence_provenance",
    ),
    "fixed-retrieval": (
        "request_id",
        "carrier_lock_key",
        "sample_id",
        "speech_ref",
        "media_relpath",
        "audio_seconds",
        "sample_rate_hz",
        "task_instruction",
        "history",
        "decoding_params",
        "retrieval_query",
        "retrieved_evidence",
        "evidence_provenance",
    ),
    # New arms (2026-08-13), introduced rather than mutating a frozen entry
    # above (core.policies module docstring: "the arm payload vocabulary
    # never grows without a new D2 receipt" -- growing it means a NEW key
    # here, never appending a field to an existing tuple, which would
    # retroactively break every already-issued payload for that arm).
    #
    # "exemplar-context": fixed-legal-context's own field set plus
    # "exemplar_bank" -- the M-C-prime static acoustic-supply arm
    # (core.exemplars module docstring; docs/exposure-ledger.md's
    # SAEA-SMOKE-mm2 row). Consumed by core.policies.FixedPolicy (which
    # threads SampleContext.exemplar_bank into build_arm_payload for this
    # arm the same way it already threads evidence) and, unchanged, by the
    # obs-agent-loop/obs-replay-loop slice payload builders (reproduction.
    # obs_loop already threads ctx.exemplar_bank into every slice
    # unconditionally).
    "exemplar-context": (
        "request_id",
        "carrier_lock_key",
        "sample_id",
        "speech_ref",
        "media_relpath",
        "audio_seconds",
        "sample_rate_hz",
        "task_instruction",
        "history",
        "decoding_params",
        "supplied_evidence",
        "evidence_provenance",
        "exemplar_bank",
    ),
    # "fixed-legal-context-replay": fixed-legal-context's own field set plus
    # "exemplar_bank" AND "delta_candidates" -- the REPLAY-scoped arm
    # reproduction.replay_loop.ObsReplayLoopPolicy needs so its pass-2
    # (REPLAY) requests can attach genuine retrieved/exemplar content
    # (module docstring of that file). Evidence-bearing (unlike bare-core)
    # so RETRIEVE has real per-sample text to draw candidates from -- see
    # that module's own RETRIEVE section. Because core.driver.run_experiment
    # constructs exactly ONE core.model.FrozenCoreAdapter per run, bound to
    # this ONE arm's field set for every request the run sends, PASS 1's own
    # slice requests (reused verbatim from reproduction.obs_loop) must
    # ALSO satisfy this arm's frozen fields -- reproduction.obs_loop now
    # attaches an always-empty "delta_candidates" placeholder exactly when
    # the run's arm declares the field (its own module comment), so PASS 1
    # is never broken by a REPLAY-only arm requirement.
    "fixed-legal-context-replay": (
        "request_id",
        "carrier_lock_key",
        "sample_id",
        "speech_ref",
        "media_relpath",
        "audio_seconds",
        "sample_rate_hz",
        "task_instruction",
        "history",
        "decoding_params",
        "supplied_evidence",
        "evidence_provenance",
        "exemplar_bank",
        "delta_candidates",
    ),
}


def _clean_payload(arm: str) -> dict[str, object]:
    payload: dict[str, object] = {field: "x" for field in ARM_VISIBLE_FIELDS[arm]}
    payload["history"] = [{"turn": 1, "role": "user", "content": "past turn only"}]
    payload["decoding_params"] = {"temperature": 0, "seed": 20260803}
    for evidence_field in ("supplied_evidence", "retrieved_evidence"):
        if evidence_field in payload:
            payload[evidence_field] = [
                {"evidence_id": "ev-1", "source_uri": "conec://placeholder", "content": "text"}
            ]
    return payload


def excluded_lock_keys(repo_root: Path = REPO_ROOT) -> list[str]:
    """Parse ``excluded_lock_keys`` from the E0 experiment config (single source)."""

    config = repo_root / E0_CONFIG_RELPATH
    try:
        lines = config.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise ArtifactError(f"cannot read {config}: {error}") from error
    keys: list[str] = []
    collecting = False
    for line in lines:
        stripped = line.split("#", 1)[0].rstrip()
        if stripped.strip() == "excluded_lock_keys:":
            collecting = True
            continue
        if collecting:
            match = re.fullmatch(r"\s+-\s+(\S+)", stripped)
            if match:
                keys.append(match.group(1))
                continue
            if stripped.strip():
                break
    if not keys:
        raise ArtifactError(f"no excluded_lock_keys parsed from {config}")
    return keys


def _run_boundary_negative_controls() -> list[dict[str, object]]:
    results = []
    for field in sorted(FORBIDDEN_RUNTIME_FIELDS):
        for shape, payload in (
            ("top_level", {**_clean_payload("bare-core"), field: "leak"}),
            ("nested", {**_clean_payload("bare-core"), "wrapper": {field: "leak"}}),
            (
                "list_nested",
                {**_clean_payload("bare-core"), "items": [{"inner": {field: "leak"}}]},
            ),
        ):
            try:
                assert_information_boundary(payload)
            except BoundaryViolation:
                results.append({"field": field, "shape": shape, "rejected": True})
            else:
                raise ArtifactError(
                    f"leakage negative control FAILED: field {field!r} at {shape} was accepted"
                )
    return results


def _run_trace_axis_negative_controls() -> list[dict[str, object]]:
    smuggles = [
        ("OBS", {"obs_ref": "x", "supply_evidence": "smuggled"}),
        ("ORG", {"org_source": "x", "use_admission": "smuggled"}),
        ("SUPPLY", {"supply_items": "x", "obs_ref": "smuggled"}),
        ("USE", {"use_stop": "x", "org_index": "smuggled"}),
    ]
    results = []
    for channel, payload in smuggles:
        try:
            TraceRecord(channel=channel, record_id="d2-neg", payload=payload).validate()
        except TraceContractError:
            results.append({"channel": channel, "rejected": True})
        else:
            raise ArtifactError(
                f"trace axis negative control FAILED: {channel} accepted a foreign axis key"
            )
    return results


def _general_audio_exclusion(lock_path: Path, repo_root: Path) -> dict[str, object]:
    excluded = excluded_lock_keys(repo_root)

    configured: set[str] = set()
    for config in sorted((repo_root / "configs").rglob("*.yaml")):
        configured.update(
            re.findall(
                r"^\s*lock_key:\s*(\S+)", config.read_text(encoding="utf-8"), re.MULTILINE
            )
        )
    offending = sorted(set(excluded) & configured)
    if offending:
        raise ArtifactError(f"excluded assets configured as lock_key inputs: {offending}")

    source_hits: list[str] = []
    for source in sorted((repo_root / "src").rglob("*.py")):
        text = source.read_text(encoding="utf-8").lower()
        for key in excluded:
            if key.lower() in text:
                source_hits.append(f"{source.name}:{key}")
    if source_hits:
        raise ArtifactError(f"excluded asset names appear in package source: {source_hits}")

    lock = load_lock(lock_path)
    lock_profiles: dict[str, object] = {}
    for key in excluded:
        entry = lock_entry(lock, key)
        profiles = entry.get("profiles")
        profile_list = [str(p) for p in profiles] if isinstance(profiles, list) else []
        speechy = [p for p in profile_list if p.startswith("speech-aware")]
        if speechy:
            raise ArtifactError(f"excluded asset {key!r} sits in speech-aware profiles {speechy}")
        lock_profiles[key] = profile_list

    return {
        "excluded_lock_keys_source": E0_CONFIG_RELPATH,
        "excluded_lock_keys": excluded,
        "configured_lock_keys": sorted(configured),
        "package_source_mentions": [],
        "umbrella_lock_profiles": lock_profiles,
        "note": (
            "Excluded general-audio assets are named only by the experiment config "
            "and this receipt; package code never references them."
        ),
    }


def _dependency_surface(repo_root: Path) -> dict[str, object]:
    import tomllib

    pyproject = tomllib.loads((repo_root / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = pyproject.get("project", {}).get("dependencies", None)
    if dependencies != []:
        raise ArtifactError(
            f"E0 executable surface must be stdlib-only; found dependencies={dependencies!r}"
        )
    return {
        "project_dependencies": [],
        "note": "No dataset/audio library can pull excluded assets into the E0 dependency graph.",
    }


def build_d2(lock_path: Path, repo_root: Path = REPO_ROOT) -> dict[str, object]:
    boundary_results = _run_boundary_negative_controls()
    trace_results = _run_trace_axis_negative_controls()

    clean_arms: dict[str, object] = {}
    for arm, fields in ARM_VISIBLE_FIELDS.items():
        assert_information_boundary(_clean_payload(arm))
        clean_arms[arm] = {"visible_fields": list(fields), "clean_payload_accepted": True}

    return {
        "artifact_kind": "saea-e0-d2-leakage-v1",
        "generated": today(),
        "runtime_visible_fields_by_arm": clean_arms,
        "forbidden_runtime_fields": sorted(FORBIDDEN_RUNTIME_FIELDS),
        "negative_controls": {
            "boundary_injections": {
                "executed": len(boundary_results),
                "all_rejected": True,
                "shapes_per_field": ["top_level", "nested", "list_nested"],
                "results": boundary_results,
            },
            "trace_axis_smuggling": {
                "executed": len(trace_results),
                "all_rejected": True,
                "results": trace_results,
            },
        },
        "general_audio_exclusion": _general_audio_exclusion(lock_path, repo_root),
        "dependency_surface": _dependency_surface(repo_root),
        "enforcement_points": [
            "contracts.assert_information_boundary (runtime payload choke point)",
            "contracts.TraceRecord.validate (axis namespace separation)",
            "data.loader.SampleRef.runtime_view (loader-side boundary check)",
            "tests/contract (CI-enforced, fails closed)",
        ],
    }
