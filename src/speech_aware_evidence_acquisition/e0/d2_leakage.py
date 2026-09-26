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
    CONSTRUCTION_VISIBLE_ARMS,
    CONSTRUCTION_VISIBLE_FIELD,
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
    # Text-only TRAIN artifact analysis. No construction gold, fresh speech,
    # evidence or tools; verified prepared ORG context and phase control only.
    "prepared-context-text": (
        "request_id", "carrier_lock_key", "sample_id", "speech_ref",
        "media_relpath", "audio_seconds", "sample_rate_hz", "task_instruction",
        "history", "decoding_params", "prepared_text",
    ),
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
    # "bare-core-native-tools" (D1a, 2026-09-03): bare-core's own field set
    # plus "tool_schemas" -- the native chat-template tool-calling arm for
    # the Audio2Tool direct baseline. A NEW arm, not a mutation of the frozen
    # "bare-core" entry above: the direct-prompt baseline still pastes the
    # tool registry as raw text into task_instruction (bare-core, unchanged);
    # this arm instead sends the registry as an OpenAI-format `tools` list
    # (core.model.transport.LlamaServerTransport.__call__ forwards it
    # verbatim as the request's `tools` key) so the pinned GGUF chat
    # template renders <tools>...</tools> itself and the model answers with
    # structured tool_calls instead of free text. No evidence, no
    # exemplar_bank, no delta_candidates, no speech-feature fields --
    # otherwise identical to bare-core.
    "bare-core-native-tools": (
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
        "tool_schemas",
    ),
    # Raw speech remains raw while native role history preserves tool custody.
    "raw-speech-agent-native-tools": (
        "request_id", "carrier_lock_key", "sample_id", "speech_ref",
        "media_relpath", "audio_seconds", "sample_rate_hz", "task_instruction",
        "history", "decoding_params", "supplied_evidence", "evidence_provenance",
        "tool_schemas", "raw_speech_query",
    ),
    # "construction-proposer-text" (E2.4, 2026-09-05): bare-core's own ten
    # fields plus "construction_targets" -- the ONE arm on which the frozen
    # core may see gold, and only CONSTRUCTION gold. A NEW arm, never a
    # mutation of the frozen "bare-core" entry above (core.policies module
    # docstring: "the arm payload vocabulary never grows without a new D2
    # receipt").
    #
    # THE BOUNDARY ARGUMENT, stated where the field is declared.
    # (1) WHOSE gold. Only rows of a committed `roster_role = "construction"`
    #     roster, which the Audio2Tool exposure union excludes by design and
    #     which is block-disjoint, by construction and by an explicit
    #     recomputed proof, from every committed evaluation identity of the
    #     same carrier (docs/receipts/rosters/a2t-construction-800-v1.json).
    #     The legality class is exactly TRAIN gold entering a knowledge-base
    #     build, which this study has always allowed.
    # (2) HOW it is enforced, not merely intended. `contracts.gate_exposure
    #     ._require_construction_role_for_visible_targets` refuses the touch
    #     unless the plan's own `split_identity_hash` equals a committed
    #     construction roster of the plan's carrier and the plan's split role
    #     is "discovery"; every other arm is unaffected by that check.
    # (3) WHAT comes back. The contact is TEXT-ONLY (no audio part at all)
    #     and its output is an ARTIFACT -- proposed prompt text, a tool
    #     description, a cue -- never an answer to a scored row. Artifacts
    #     reach an evaluation contact only through the audited instruction
    #     fields of a later arm, hash-pinned in a committed config fragment,
    #     so nothing produced here can reach a scored row unlogged.
    # (4) WHAT is still forbidden. Every entry of FORBIDDEN_RUNTIME_FIELDS is
    #     rejected inside this payload exactly as in every other arm
    #     (build_d2 runs assert_information_boundary on it), and no
    #     evaluation identity can ever appear in it, because the gate binds
    #     the whole request set to a construction roster.
    "construction-proposer-text": (
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
        "construction_targets",
    ),
    # "construction-advantage-text" (Stage-3 S3-4, 2026-09-22): bare-core's
    # own ten fields plus "construction_targets", byte-identical in SHAPE to
    # "construction-proposer-text" above and admitted for the same reason
    # (owner decision 82: the frozen core may see CONSTRUCTION gold, never
    # evaluation gold). This is a SECOND, independent arm rather than a
    # second use of the proposer arm's name because its material and its
    # output contract both differ: the proposer arm asks for a rewritten
    # artifact over a target's tool description; this arm asks the core to
    # STATE, in a fixed three-line form (DELTA-KIND / TARGET / STATEMENT),
    # what distinguished a Stage-3 rollout's best sample from its worst on
    # one disagreeing construction row (Training-Free GRPO's group-relative
    # semantic advantage). "construction_targets" here carries this row's
    # own construction-gold target (the same field name and field-set
    # discipline `_construction_visibility` enforces below: every arm this
    # dict declares as construction-visible must be bare-core's ten fields
    # plus exactly this one), never the best/worst SAMPLE ANSWERS -- those
    # are rendered ONLY into the instruction text at flight time
    # (`rails.stage3_advantage`), the same "artifact never receipted"
    # discipline `construction_draws` documents at
    # core/flight/runtime.py's wire-check receipt.
    "construction-advantage-text": (
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
        "construction_targets",
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
    # Formal decoder-only speech-feature requests. This is a new arm rather
    # than a mutation of any historical allowlist: raw media metadata remains
    # bound for split identity and metering, while the transport consumes only
    # the packet references and refuses raw input_audio in this mode.
    "speech-feature-query": (
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
        "speech_feature_parts",
        "speech_packet_sha256",
        "query_source",
        "key_representation_id",
        "matcher_policy_id",
        "mmproj_loaded",
    ),
    # "speech-feature-query-native-tools" (D1b, 2026-09-03): speech-feature-
    # query's own field set plus "tool_schemas" -- the native chat-template
    # tool-calling arm for the Audio2Tool packet (formal decoder-only
    # speech-feature) path, the second half of D1a's "bare-core-native-tools"
    # naming convention. A NEW arm, not a mutation of the frozen
    # "speech-feature-query" entry above (module docstring: "the arm payload
    # vocabulary never grows without a new D2 receipt"): the packet-path
    # decision call still answers as free text by default (speech-feature-
    # query, unchanged); this arm instead sends the tool registry as an
    # OpenAI-format `tools` list (core.model.transport.LlamaServerTransport.
    # __call__ forwards it verbatim as the request's `tools` key) so the
    # pinned GGUF chat template renders <tools>...</tools> itself and the
    # model answers with structured tool_calls instead of free text. Exactly
    # speech-feature-query's own fields plus "tool_schemas" -- no other field
    # added or removed.
    "speech-feature-query-native-tools": (
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
        "speech_feature_parts",
        "speech_packet_sha256",
        "query_source",
        "key_representation_id",
        "matcher_policy_id",
        "mmproj_loaded",
        "tool_schemas",
    ),
}


def _clean_payload(arm: str) -> dict[str, object]:
    payload: dict[str, object] = {field: "x" for field in ARM_VISIBLE_FIELDS[arm]}
    payload["history"] = [{"turn": 1, "role": "user", "content": "past turn only"}]
    payload["decoding_params"] = {"temperature": 0, "seed": 20260803}
    if CONSTRUCTION_VISIBLE_FIELD in payload:
        payload[CONSTRUCTION_VISIBLE_FIELD] = [
            {"sample_id": "tier1_direct:000001", "target": "setLighting(state='on')"}
        ]
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


def _construction_visibility() -> dict[str, object]:
    """The construction-gold visibility statement, EXECUTED, not asserted in
    prose: exactly the arms named by ``contracts.CONSTRUCTION_VISIBLE_ARMS``
    declare ``construction_targets``, and no other arm does. A drift in
    either direction fails the generator closed, so the D2 artifact can never
    record a gold-visible arm the contract layer does not know about, nor a
    contract-declared arm the freeze does not carry."""

    declaring = {
        arm
        for arm, fields in ARM_VISIBLE_FIELDS.items()
        if CONSTRUCTION_VISIBLE_FIELD in fields
    }
    if declaring != set(CONSTRUCTION_VISIBLE_ARMS):
        raise ArtifactError(
            "construction-visibility drift: arms declaring "
            f"{CONSTRUCTION_VISIBLE_FIELD!r} are {sorted(declaring)}, but "
            f"contracts.CONSTRUCTION_VISIBLE_ARMS is {sorted(CONSTRUCTION_VISIBLE_ARMS)}"
        )
    for arm in sorted(declaring):
        missing = set(ARM_VISIBLE_FIELDS["bare-core"]) - set(ARM_VISIBLE_FIELDS[arm])
        if missing:
            raise ArtifactError(
                f"construction-visible arm {arm!r} drops bare-core fields {sorted(missing)}; "
                "it must be bare-core's field set plus the one declared field"
            )
        if set(ARM_VISIBLE_FIELDS[arm]) != set(ARM_VISIBLE_FIELDS["bare-core"]) | {
            CONSTRUCTION_VISIBLE_FIELD
        }:
            raise ArtifactError(
                f"construction-visible arm {arm!r} carries fields beyond bare-core plus "
                f"{CONSTRUCTION_VISIBLE_FIELD!r}"
            )
    return {
        "field": CONSTRUCTION_VISIBLE_FIELD,
        "arms": sorted(CONSTRUCTION_VISIBLE_ARMS),
        "arms_declaring_the_field": sorted(declaring),
        "no_other_arm_declares_it": True,
        "boundary_argument": (
            "Owner decision 2026-09-05. The frozen core may act as a PROPOSER over "
            "CONSTRUCTION rows with their gold labels, on this text-only arm alone. "
            "(1) Construction identities only: the gate "
            "(contracts.gate_exposure._require_construction_role_for_visible_targets) "
            "refuses the touch unless the plan's split identity hash equals a committed "
            "roster receipt whose carrier is the plan's own and whose roster_role is "
            "'construction', and whose split role is 'discovery'. (2) Block-disjoint "
            "from every evaluation identity by construction: a construction roster is "
            "drawn from the exposure-free block partition and its zero overlap with the "
            "exposure union is recomputed and refused fail-closed before the receipt is "
            "written. The exposure union excludes construction-role rosters by design, "
            "so the two sets can never converge. (3) Outputs are ARTIFACTS -- proposed "
            "prompt text -- never answers to a scored row; they reach an evaluation "
            "contact only through the audited instruction fields, hash-pinned in a "
            "committed config fragment. (4) The contact is text-only and every "
            "FORBIDDEN_RUNTIME_FIELDS name is still rejected inside this payload, "
            "exactly as in every other arm. The legality class is the same as TRAIN "
            "gold entering a knowledge-base build."
        ),
    }


def build_d2(lock_path: Path, repo_root: Path = REPO_ROOT) -> dict[str, object]:
    boundary_results = _run_boundary_negative_controls()
    trace_results = _run_trace_axis_negative_controls()
    construction_visibility = _construction_visibility()

    clean_arms: dict[str, object] = {}
    for arm, fields in ARM_VISIBLE_FIELDS.items():
        assert_information_boundary(_clean_payload(arm))
        clean_arms[arm] = {"visible_fields": list(fields), "clean_payload_accepted": True}

    return {
        "artifact_kind": "saea-e0-d2-leakage-v1",
        "generated": today(),
        "runtime_visible_fields_by_arm": clean_arms,
        "construction_gold_visibility": construction_visibility,
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
