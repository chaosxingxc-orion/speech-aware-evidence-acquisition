"""Deterministic full-window delivery over an already verified parent trace.

Terminal OBS records define coverage, including exhausted windows omitted from
stitched_request_ids. No alternate retry or response is selected by quality.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Mapping

from ..base import RESPONSE_POSTPROCESSORS, CoreError
from ..delivery import (
    deliver_terminal_response,
    normalize_terminal_response,
    terminal_response_saturated,
)
from ..predecessor_snapshot import PredecessorSnapshot
from . import BundleError
from .artifacts import VerifiedBundle

PHASE_RESPONSE_PAIR_SCHEMA = "saea-phase-response-pair-v1"
SEALED_STATE_RESPONSE_PAIR_SCHEMA = "saea-sealed-state-response-pair-v1"
_PHASE_SELECTOR_KEYS = {
    "schema",
    "program_id",
    "program_sha256",
    "predecessor_phase",
    "response_phase",
}
_SEALED_STATE_SELECTOR_KEYS = {
    "schema",
    "program_id",
    "program_sha256",
    "response_phase",
}


def canonical(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _request(parent, request_id, sample_id):
    request = parent.trace_records.get(f"{request_id}/request")
    if not isinstance(request, Mapping) or not isinstance(
        request.get("payload"), Mapping
    ):
        raise BundleError("terminal OBS lacks its actual model request")
    payload = request["payload"]
    if payload.get("request_id") != request_id or payload.get("sample_id") != sample_id:
        raise BundleError("terminal request identity disagrees with window sample")
    if sha256(canonical(payload)) != request.get("payload_sha256"):
        raise BundleError("terminal request payload hash mismatch")
    return request


def _phase_program(selector: Mapping, values: Mapping, *, program=None):
    from ...rails.controllers import RailsControllersError, default_phase_program

    if set(selector) != _PHASE_SELECTOR_KEYS:
        raise BundleError("phase response source_selector has missing or unknown fields")
    if selector.get("schema") != PHASE_RESPONSE_PAIR_SCHEMA:
        raise BundleError("phase response source_selector schema mismatch")
    for field in ("program_id", "predecessor_phase", "response_phase"):
        if not isinstance(selector.get(field), str) or not selector[field]:
            raise BundleError(f"phase response source_selector {field} must be non-empty")
    if selector["predecessor_phase"] == selector["response_phase"]:
        raise BundleError("phase response source phases must be distinct")
    if values.get("policy") != selector["program_id"]:
        raise BundleError("phase response source program differs from parent policy")
    try:
        registered_program = default_phase_program(selector["program_id"])
        program = registered_program if program is None else program
        program.validate()
    except RailsControllersError as error:
        raise BundleError(f"phase response source program is not registered: {error}") from error
    if program.as_json() != registered_program.as_json():
        raise BundleError("phase response source differs from the executing program")
    program_sha256 = selector.get("program_sha256")
    if (
        not isinstance(program_sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", program_sha256) is None
        or program_sha256 != sha256(canonical(program.as_json()))
    ):
        raise BundleError("phase response source program hash mismatch")
    names = program.phase_names()
    try:
        predecessor_index = names.index(selector["predecessor_phase"])
        response_index = names.index(selector["response_phase"])
    except ValueError:
        raise BundleError("phase response source names a phase outside its program") from None
    if predecessor_index >= response_index:
        raise BundleError("phase response predecessor must precede the response phase")
    if response_index != len(names) - 1:
        raise BundleError("phase response source must be the program's terminal phase")
    return program


def _sealed_state_program(selector: Mapping, values: Mapping, *, program=None):
    from ...rails.controllers import RailsControllersError, default_phase_program

    if set(selector) != _SEALED_STATE_SELECTOR_KEYS:
        raise BundleError("sealed-state source_selector has missing or unknown fields")
    if selector.get("schema") != SEALED_STATE_RESPONSE_PAIR_SCHEMA:
        raise BundleError("sealed-state source_selector schema mismatch")
    for field in ("program_id", "response_phase"):
        if not isinstance(selector.get(field), str) or not selector[field]:
            raise BundleError(f"sealed-state source_selector {field} must be non-empty")
    if values.get("policy") != selector["program_id"]:
        raise BundleError("sealed-state source program differs from parent policy")
    try:
        registered = default_phase_program(selector["program_id"])
        program = registered if program is None else program
        program.validate()
    except RailsControllersError as error:
        raise BundleError(f"sealed-state source program is not registered: {error}") from error
    if program.as_json() != registered.as_json():
        raise BundleError("sealed-state source differs from the registered program")
    if selector.get("program_sha256") != sha256(canonical(program.as_json())):
        raise BundleError("sealed-state source program hash mismatch")
    names = program.phase_names()
    if selector["response_phase"] not in names:
        raise BundleError("sealed-state response phase is outside its program")
    if selector["response_phase"] != names[-1]:
        raise BundleError("sealed-state response phase must be terminal")
    return program


def _source_selector_program(selector: Mapping, values: Mapping, *, program=None):
    schema = selector.get("schema")
    if schema == PHASE_RESPONSE_PAIR_SCHEMA:
        return _phase_program(selector, values, program=program)
    if schema == SEALED_STATE_RESPONSE_PAIR_SCHEMA:
        return _sealed_state_program(selector, values, program=program)
    raise BundleError("delivery source_selector schema is not registered")


def _sealed_state_phase_spec(selector: Mapping, values: Mapping, program):
    from ...rails.phase_material import PhaseMaterialError, load_phase_material_specs

    try:
        spec = load_phase_material_specs(values, program)[selector["response_phase"]]
    except (KeyError, PhaseMaterialError) as error:
        raise BundleError(f"sealed-state phase material is invalid: {error}") from error
    if spec.predecessor_binding != "sealed-manifest":
        raise BundleError("sealed-state response phase must bind a sealed manifest")
    source = spec.predecessor_source
    if not isinstance(source, Mapping) or set(source) != {
        "manifest_relpath",
        "manifest_sha256",
        "producer_policy_id",
    }:
        raise BundleError("sealed-state predecessor source binding is incomplete")
    return spec


def delivery_declarations(values: Mapping) -> tuple[Mapping, ...]:
    """Validate the shared declaration shape before generation and replay."""
    declarations = values.get("delivery_derivatives")
    if declarations is None:
        return ()
    if not isinstance(declarations, list):
        raise BundleError("delivery_derivatives must be a list")
    required = {
        "cell_id", "parent_cell_id", "response_postprocessor",
        "response_postprocessor_params",
    }
    identities = set()
    for item in declarations:
        if not isinstance(item, Mapping) or set(item) not in (
            required, required | {"source_selector"},
        ):
            raise BundleError("delivery declaration has missing or unknown fields")
        for key in ("cell_id", "parent_cell_id"):
            if not isinstance(item[key], str) or re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9._-]*", item[key]
            ) is None:
                raise BundleError("delivery cell identity must be a safe config name")
        if item["cell_id"] in identities or not isinstance(
            item["response_postprocessor_params"], Mapping
        ):
            raise BundleError("delivery declaration repeats a cell or has invalid rule parameters")
        if "source_selector" in item and not isinstance(item["source_selector"], Mapping):
            raise BundleError("delivery source_selector must be a mapping")
        identities.add(item["cell_id"])
    return tuple(declarations)


def selected_phase_delivery_declarations(
    values: Mapping, parent_fragments: Mapping | None = None,
) -> tuple[Mapping, ...]:
    """Select phase derivatives by the exact parent cell, independent of scoring."""
    selected = []
    for declaration in delivery_declarations(values):
        if "source_selector" not in declaration:
            continue
        if parent_fragments is not None:
            cells = values.get("cells")
            if not isinstance(cells, list):
                raise BundleError("phase delivery requires declared parent cells")
            parents = [
                cell for cell in cells
                if isinstance(cell, Mapping)
                and cell.get("cell_id") == declaration.get("parent_cell_id")
            ]
            if len(parents) != 1:
                raise BundleError("phase delivery requires exactly one declared parent cell")
            if any(parents[0].get(key) != value for key, value in parent_fragments.items()):
                continue
        selected.append(declaration)
    return tuple(selected)


def validate_phase_delivery_sources(
    values: Mapping, *, program=None, parent_fragments: Mapping | None = None
) -> tuple[Mapping, ...]:
    """Return applicable, validated phase declarations before requests or replay.

    An absent selector preserves the historical OBS delivery contract. An
    opted-in selector binds the exact executed program structure through the
    composed configuration hash, including its phases and contact ceiling.
    """
    selected = selected_phase_delivery_declarations(values, parent_fragments)
    for declaration in selected:
        selector = declaration["source_selector"]
        if not isinstance(selector, Mapping):
            raise BundleError("phase response source_selector must be a mapping")
        resolved_program = _source_selector_program(selector, values, program=program)
        if selector.get("schema") == SEALED_STATE_RESPONSE_PAIR_SCHEMA:
            _sealed_state_phase_spec(selector, values, resolved_program)
        try:
            params = declaration["response_postprocessor_params"]
            if not isinstance(params, Mapping):
                raise BundleError("phase delivery rule parameters must be a mapping")
            rule = RESPONSE_POSTPROCESSORS.resolve(
                declaration["response_postprocessor"]
            )(**params)
            if not callable(rule):
                raise BundleError("phase delivery rule factory must return a callable")
        except (CoreError, KeyError, TypeError, ValueError) as error:
            raise BundleError(f"phase delivery rule is invalid: {error}") from error
    return selected


def require_experiment_phase_declarations(
    repo_root, experiment: str, declarations, parent_fragments: Mapping,
) -> None:
    """Keep required delivery recoverable from the experiment's Git source."""
    if not declarations:
        return
    from ..config import read_fragment

    document = read_fragment(repo_root, "experiment", experiment)
    recorded = selected_phase_delivery_declarations(document, parent_fragments)
    if canonical(recorded) != canonical(declarations):
        raise BundleError("phase delivery must be declared in the actual experiment fragment")


def _phase_request_index(parent: VerifiedBundle) -> dict:
    """Index the verified trace once for complete-roster delivery."""
    index: dict[tuple[str, str], list] = {}
    for record_id, request in parent.trace_records.items():
        if not isinstance(request, Mapping):
            continue
        payload = request.get("payload")
        if not isinstance(payload, Mapping):
            continue
        sample_id = payload.get("sample_id")
        history = payload.get("history")
        if not isinstance(sample_id, str) or not isinstance(history, list) or not history:
            continue
        controls = [
            turn
            for turn in history
            if isinstance(turn, Mapping) and turn.get("role") == "control"
        ]
        if not controls or not isinstance(controls[-1].get("contact_id"), str):
            continue
        key = (sample_id, controls[-1]["contact_id"])
        index.setdefault(key, []).append((record_id, request, payload, history, controls))
    return index


def _phase_contact(
    parent: VerifiedBundle, request_index: Mapping, *, sample_id: str, contact_id: str
):
    matches = request_index.get((sample_id, contact_id), ())
    if len(matches) != 1:
        raise BundleError(
            f"phase contact {contact_id!r} has {len(matches)} request records, expected one"
        )
    record_id, request, payload, history, controls = matches[0]
    if len(controls) != 1 or history[-1] is not controls[0]:
        raise BundleError("phase request must carry exactly one terminal control turn")
    request_id = payload.get("request_id")
    if not isinstance(request_id, str) or record_id != f"{request_id}/request":
        raise BundleError("phase request record identity disagrees with its payload")
    if sha256(canonical(payload)) != request.get("payload_sha256"):
        raise BundleError("phase request payload hash mismatch")
    control = controls[0]
    content = control.get("content")
    if not isinstance(content, str) or sha256(content.encode("utf-8")) != control.get(
        "content_sha256"
    ):
        raise BundleError("phase control text hash mismatch")
    response = parent.trace_records.get(f"{request_id}/response")
    if not isinstance(response, Mapping) or not isinstance(response.get("text"), str):
        raise BundleError("phase request lacks exactly one usable response")
    response_sha256 = response.get("response_sha256")
    if not isinstance(response_sha256, str) or re.fullmatch(
        r"[0-9a-f]{64}", response_sha256
    ) is None:
        raise BundleError("phase response wire hash is malformed")
    text = response["text"]
    if sha256(text.encode("utf-8")) != response.get("response_text_sha256"):
        raise BundleError("phase response text hash mismatch")
    return request_id, request, response, text


def _actual_max_tokens(request: Mapping) -> int | None:
    payload = request.get("payload")
    decoding = payload.get("decoding_params") if isinstance(payload, Mapping) else None
    if not isinstance(decoding, Mapping):
        raise BundleError("phase request lacks actual decoding_params")
    max_tokens = decoding.get("max_tokens")
    if max_tokens is None:
        return None
    if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or max_tokens < 1:
        raise BundleError("phase request actual max_tokens must be a positive integer")
    return max_tokens


def replay_phase_pair_delivery(
    parent: VerifiedBundle,
    declaration: Mapping,
    values: Mapping,
) -> tuple[list[dict], list[dict]]:
    """Deliver one registered phase response against an earlier phase response."""
    selector = declaration.get("source_selector")
    if not isinstance(selector, Mapping):
        raise BundleError("phase-pair delivery requires a source_selector mapping")
    program = _phase_program(selector, values)
    rule = RESPONSE_POSTPROCESSORS.resolve(declaration["response_postprocessor"])(
        **declaration["response_postprocessor_params"]
    )
    rows, sources = [], []
    seen_samples = set()
    request_index = _phase_request_index(parent)
    for source_row in parent.outputs_rows:
        sample_id = source_row.get("sample_id")
        if not isinstance(sample_id, str) or sample_id in seen_samples:
            raise BundleError("phase-pair parent outputs have invalid sample identities")
        seen_samples.add(sample_id)
        predecessor_contact = (
            f"{program.program_id}:{selector['predecessor_phase']}:{sample_id}"
        )
        response_contact = f"{program.program_id}:{selector['response_phase']}:{sample_id}"
        predecessor_id, predecessor_request, predecessor_response, predecessor_text = (
            _phase_contact(
                parent, request_index, sample_id=sample_id, contact_id=predecessor_contact
            )
        )
        response_id, response_request, response_response, response_text = _phase_contact(
            parent, request_index, sample_id=sample_id, contact_id=response_contact
        )
        if (
            source_row.get("request_id") != response_id
            or source_row.get("text") != response_text
            or source_row.get("request_sha256") != response_request.get("payload_sha256")
            or source_row.get("response_sha256")
            != response_response.get("response_sha256")
            or source_row.get("response_text_sha256")
            != response_response.get("response_text_sha256")
        ):
            raise BundleError(
                "terminal response phase does not match the parent's raw output row"
            )
        predecessor_max_tokens = _actual_max_tokens(predecessor_request)
        response_max_tokens = _actual_max_tokens(response_request)
        predecessor_saturated = terminal_response_saturated(
            predecessor_response.get("usage"), predecessor_max_tokens
        )
        response_saturated = terminal_response_saturated(
            response_response.get("usage"), response_max_tokens
        )
        normalized_predecessor = normalize_terminal_response(
            predecessor_text, saturated=predecessor_saturated
        )
        normalized_response = normalize_terminal_response(
            response_text, saturated=response_saturated
        )
        outcome = deliver_terminal_response(
            normalized_predecessor,
            response_text,
            rule=rule,
            saturated=response_saturated,
        )
        rows.append(
            {
                "request_id": f"{response_id}/delivery/{declaration['cell_id']}",
                "sample_id": sample_id,
                "carrier_lock_key": source_row["carrier_lock_key"],
                "arm": source_row["arm"],
                "text": outcome.text,
                "admitted": source_row["admitted"],
                "delivery_text_sha256": sha256(outcome.text.encode("utf-8")),
                "source_request_id": response_id,
                "source_output_sha256": sha256(canonical(source_row)),
            }
        )
        sources.append(
            {
                "sample_id": sample_id,
                "selector": dict(selector),
                "predecessor_contact_id": predecessor_contact,
                "predecessor_request_id": predecessor_id,
                "predecessor_request_record_sha256": sha256(
                    canonical(predecessor_request)
                ),
                "predecessor_response_record_sha256": sha256(
                    canonical(predecessor_response)
                ),
                "predecessor_text_sha256": sha256(predecessor_text.encode("utf-8")),
                "normalized_predecessor_sha256": sha256(
                    normalized_predecessor.encode("utf-8")
                ),
                "predecessor_max_tokens": predecessor_max_tokens,
                "predecessor_saturated": predecessor_saturated,
                "response_contact_id": response_contact,
                "response_request_id": response_id,
                "response_request_record_sha256": sha256(canonical(response_request)),
                "response_response_record_sha256": sha256(canonical(response_response)),
                "response_text_sha256": sha256(response_text.encode("utf-8")),
                "normalized_response_sha256": sha256(normalized_response.encode("utf-8")),
                "response_max_tokens": response_max_tokens,
                "response_saturated": response_saturated,
                "delivered_text_sha256": sha256(outcome.text.encode("utf-8")),
                "refusal_reason": outcome.refusal_reason,
            }
        )
        diagnostics = getattr(outcome, "diagnostics", None)
        if diagnostics is not None:
            if not isinstance(diagnostics, Mapping):
                raise BundleError("phase delivery diagnostics must be a mapping")
            sources[-1]["delivery_diagnostics"] = dict(diagnostics)
    if seen_samples != set(parent.split_ids):
        raise BundleError("phase-pair delivery does not cover the verified parent roster")
    return rows, sources


def _confined_data_path(data_root, relpath: object) -> Path:
    if (
        not isinstance(relpath, str)
        or not relpath
        or relpath.startswith("/")
        or "\\" in relpath
        or ":" in relpath
        or any(part in ("", ".", "..") for part in relpath.split("/"))
    ):
        raise BundleError("sealed-state predecessor path must be canonical POSIX relative")
    root = Path(data_root).resolve()
    path = (root / relpath).resolve()
    if not path.is_relative_to(root):
        raise BundleError("sealed-state predecessor path escapes data_root")
    return path


def _history_carries_state(history: object, state, *, contact_id: str) -> bool:
    if not isinstance(history, list):
        return False
    expected = state.as_json()
    expected.pop("state_artifact_version")
    expected["content_sha256"] = sha256(state.content.encode("utf-8"))
    matches = [
        entry
        for entry in history
        if isinstance(entry, Mapping)
        and entry.get("role") == "agent_state"
        and all(entry.get(key) == value for key, value in expected.items())
    ]
    if any(isinstance(entry, Mapping) and entry.get("role") == "agent_state" for entry in history):
        return len(matches) == 1

    from ...rails.phase_material import PREDECESSOR_PREFIX, render_phase_predecessor_block

    controls = [
        entry for entry in history
        if isinstance(entry, Mapping)
        and entry.get("role") == "control"
        and entry.get("contact_id") == contact_id
    ]
    if len(controls) != 1:
        return False
    control = controls[0]
    content = control.get("content")
    if (
        not isinstance(content, str)
        or control.get("content_sha256") != sha256(content.encode("utf-8"))
    ):
        return False
    prefix = f"\n\n{PREDECESSOR_PREFIX} ("
    block = "\n\n" + render_phase_predecessor_block(state)
    if content.count(prefix) != 1 or content.count(block) != 1:
        return False
    suffix = content.split(block, 1)[1]
    return not suffix or suffix.startswith("\n\n")


def replay_sealed_state_response_delivery(
    parent: VerifiedBundle,
    declaration: Mapping,
    values: Mapping,
    *,
    data_root,
) -> tuple[list[dict], list[dict]]:
    """Deliver a terminal response against its exact external sealed state."""
    from ...rails.phase_material import (
        PhaseMaterialError,
        sealed_states_from_manifest,
    )
    from .verify import verify_bundle

    selector = declaration.get("source_selector")
    if not isinstance(selector, Mapping):
        raise BundleError("sealed-state delivery requires a source_selector")
    program = _sealed_state_program(selector, values)
    response_phase = selector["response_phase"]
    spec = _sealed_state_phase_spec(selector, values, program)
    source = spec.predecessor_source
    source_path = _confined_data_path(data_root, source["manifest_relpath"])
    try:
        source_manifest_sha256 = sha256(source_path.read_bytes())
    except OSError as error:
        raise BundleError(f"cannot read sealed-state predecessor manifest: {error}") from error
    if source_manifest_sha256 != source["manifest_sha256"]:
        raise BundleError("sealed-state predecessor manifest hash differs from source")
    predecessor = verify_bundle(source_path)
    from .hypothesis_source import is_derived_hypothesis_bundle

    if not (
        (
            predecessor.attempt_state == "FINALIZED"
            and predecessor.manifest.get("status") == "COMPLETED"
        )
        or is_derived_hypothesis_bundle(predecessor)
    ):
        raise BundleError(
            "sealed-state predecessor must be FINALIZED and COMPLETED "
            "or an explicitly verified hypothesis derivation"
        )
    if predecessor.split_ids != parent.split_ids:
        raise BundleError("sealed-state predecessor roster differs from response parent")
    runtime_producers = [
        (record_id.split("/", 1)[0], payload.get("use_controller_policy_id"))
        for record_id, payload in predecessor.trace_records.items()
        if "use_controller_policy_id" in payload
    ]
    if (
        len(runtime_producers) != len(predecessor.split_ids)
        or {sample_id for sample_id, _policy in runtime_producers}
        != set(predecessor.split_ids)
        or {policy for _sample_id, policy in runtime_producers}
        != {source["producer_policy_id"]}
    ):
        raise BundleError("sealed-state predecessor producer identity differs from source")
    try:
        states = sealed_states_from_manifest(
            source_path,
            expected_sha256=source["manifest_sha256"],
            phase_name=response_phase,
            producer_policy_id=source["producer_policy_id"],
            sample_ids=tuple(row["sample_id"] for row in parent.outputs_rows),
            bundle_verifier=lambda _path: predecessor,
        )
    except (KeyError, PhaseMaterialError) as error:
        raise BundleError(f"sealed-state predecessor loading failed: {error}") from error
    rule = RESPONSE_POSTPROCESSORS.resolve(declaration["response_postprocessor"])(
        **declaration["response_postprocessor_params"]
    )
    request_index = _phase_request_index(parent)
    rows, sources = [], []
    seen = set()
    for source_row in parent.outputs_rows:
        sample_id = source_row.get("sample_id")
        if not isinstance(sample_id, str) or sample_id in seen:
            raise BundleError("sealed-state response parent has invalid sample identities")
        seen.add(sample_id)
        state = states[sample_id]
        contact_id = f"{program.program_id}:{response_phase}:{sample_id}"
        request_id, request, response, response_text = _phase_contact(
            parent, request_index, sample_id=sample_id, contact_id=contact_id
        )
        if not _history_carries_state(
            request["payload"].get("history"), state, contact_id=contact_id,
        ):
            raise BundleError("response request did not carry the exact sealed predecessor state")
        if (
            source_row.get("request_id") != request_id
            or source_row.get("text") != response_text
            or source_row.get("request_sha256") != request.get("payload_sha256")
            or source_row.get("response_sha256") != response.get("response_sha256")
            or source_row.get("response_text_sha256")
            != response.get("response_text_sha256")
        ):
            raise BundleError("sealed-state response differs from parent output")
        max_tokens = _actual_max_tokens(request)
        saturated = terminal_response_saturated(response.get("usage"), max_tokens)
        normalized = normalize_terminal_response(response_text, saturated=saturated)
        outcome = deliver_terminal_response(
            state.content,
            response_text,
            rule=rule,
            saturated=saturated,
        )
        rows.append(
            {
                "request_id": f"{request_id}/delivery/{declaration['cell_id']}",
                "sample_id": sample_id,
                "carrier_lock_key": source_row["carrier_lock_key"],
                "arm": source_row["arm"],
                "text": outcome.text,
                "admitted": source_row["admitted"],
                "delivery_text_sha256": sha256(outcome.text.encode("utf-8")),
                "source_request_id": request_id,
                "source_output_sha256": sha256(canonical(source_row)),
            }
        )
        sources.append(
            {
                "sample_id": sample_id,
                "selector": dict(selector),
                "predecessor_manifest": {
                    "path": str(source_path),
                    "sha256": source["manifest_sha256"],
                },
                "sealed_state_sha256": state.content_hash(),
                "sealed_state_source_query_sha256": state.source_query_state_sha256,
                "sealed_state_source_response_sha256": state.source_response_sha256,
                "response_contact_id": contact_id,
                "response_request_id": request_id,
                "response_request_record_sha256": sha256(canonical(request)),
                "response_response_record_sha256": sha256(canonical(response)),
                "response_text_sha256": sha256(response_text.encode("utf-8")),
                "normalized_response_sha256": sha256(normalized.encode("utf-8")),
                "response_max_tokens": max_tokens,
                "response_saturated": saturated,
                "delivered_text_sha256": sha256(outcome.text.encode("utf-8")),
                "refusal_reason": outcome.refusal_reason,
            }
        )
        diagnostics = getattr(outcome, "diagnostics", None)
        if diagnostics is not None:
            if not isinstance(diagnostics, Mapping):
                raise BundleError("sealed-state delivery diagnostics must be a mapping")
            sources[-1]["delivery_diagnostics"] = dict(diagnostics)
    if seen != set(parent.split_ids):
        raise BundleError("sealed-state delivery does not cover the response parent roster")
    return rows, sources


def replay_delivery(
    parent: VerifiedBundle,
    snapshot: PredecessorSnapshot | None,
    declaration: Mapping,
    values: Mapping,
    *,
    data_root=None,
) -> tuple[list[dict], list[dict]]:
    """Recompute whole-call outputs and a content-free, all-window receipt."""
    selector = declaration.get("source_selector")
    if isinstance(selector, Mapping) and selector.get("schema") == SEALED_STATE_RESPONSE_PAIR_SCHEMA:
        if data_root is None:
            raise BundleError("sealed-state delivery requires data_root")
        return replay_sealed_state_response_delivery(
            parent, declaration, values, data_root=data_root
        )
    if selector is not None:
        return replay_phase_pair_delivery(parent, declaration, values)
    if not isinstance(snapshot, PredecessorSnapshot):
        raise BundleError("legacy OBS delivery requires a predecessor snapshot")
    rule = RESPONSE_POSTPROCESSORS.resolve(declaration["response_postprocessor"])(
        **declaration["response_postprocessor_params"]
    )
    max_tokens = values.get("decoding_params", {}).get("max_tokens")
    rows, windows = [], []
    consumed_obs = set()
    for source_row in parent.outputs_rows:
        sample_id, root_id = source_row["sample_id"], source_row["request_id"]
        predecessors = snapshot.for_sample(sample_id)
        terminal = {}
        for record_id, obs in parent.trace_records.items():
            if not record_id.startswith(f"{root_id}-i") or not record_id.endswith(
                "/obs"
            ):
                continue
            if (
                not obs.get("obs_repair")
                or obs.get("obs_relisten")
                or obs.get("obs_boundary_mode") != "fixed"
            ):
                raise BundleError("delivery replay requires full fixed repair windows")
            iteration = obs.get("obs_iteration")
            if (
                isinstance(iteration, bool)
                or not isinstance(iteration, int)
                or iteration in terminal
            ):
                raise BundleError(
                    "terminal OBS has invalid or duplicate window iteration"
                )
            terminal[iteration] = (record_id[:-4], obs)
            consumed_obs.add(record_id)
        if set(terminal) != set(range(len(predecessors))):
            raise BundleError(
                "terminal OBS coverage does not match all predecessor windows"
            )
        delivered, contacted = [], []
        for iteration, predecessor in enumerate(predecessors):
            request_id, obs = terminal[iteration]
            base = f"{root_id}-i{iteration:04d}"
            if (
                re.fullmatch(re.escape(base) + r"(?:-r[1-9][0-9]*)?", request_id)
                is None
            ):
                raise BundleError(
                    "terminal request id disagrees with its window iteration"
                )
            retry_of = base if request_id != base else None
            if obs.get("obs_retry_of") != retry_of:
                raise BundleError("terminal retry ancestry mismatch")
            if (
                obs.get("obs_repair_predecessor_window_id") != predecessor.window_id
                or obs.get("obs_repair_predecessor_text_sha256")
                != predecessor.text_sha256
            ):
                raise BundleError("terminal OBS predecessor binding mismatch")
            if (
                abs(float(obs["obs_window_start_seconds"]) - predecessor.start_seconds)
                > 1e-6
                or abs(float(obs["obs_window_end_seconds"]) - predecessor.end_seconds)
                > 1e-6
            ):
                raise BundleError(
                    "terminal OBS window bounds differ from bound predecessor"
                )
            request = _request(parent, request_id, sample_id)
            skipped, saturated = obs.get("obs_skipped"), obs.get("obs_saturated")
            if not isinstance(skipped, bool) or not isinstance(saturated, bool):
                raise BundleError("terminal OBS lacks explicit skip/saturation state")
            response = parent.trace_records.get(f"{request_id}/response")
            if skipped:
                if response is not None or saturated:
                    raise BundleError(
                        "exhausted terminal window must not fabricate a response"
                    )
                text = None
            else:
                if not isinstance(response, Mapping) or not isinstance(
                    response.get("text"), str
                ):
                    raise BundleError("successful terminal window lacks its response")
                text = response["text"]
                if sha256(text.encode("utf-8")) != response.get("response_text_sha256"):
                    raise BundleError("terminal response text hash mismatch")
                if (
                    terminal_response_saturated(response.get("usage"), max_tokens)
                    != saturated
                ):
                    raise BundleError(
                        "terminal saturation disagrees with configured cap and usage"
                    )
                contacted.append(request_id)
            normalized = normalize_terminal_response(
                text, saturated=saturated, skipped=skipped
            )
            outcome = deliver_terminal_response(
                predecessor.text, text, rule=rule, saturated=saturated, skipped=skipped
            )
            delivered.append(outcome.text)
            windows.append(
                {
                    "sample_id": sample_id,
                    "window_id": predecessor.window_id,
                    "window_index": predecessor.window_index,
                    "terminal_request_id": request_id,
                    "retry_of": retry_of,
                    "skipped": skipped,
                    "saturated": saturated,
                    "request_record_sha256": sha256(canonical(request)),
                    "response_record_sha256": None
                    if response is None
                    else sha256(canonical(response)),
                    "obs_record_sha256": sha256(canonical(obs)),
                    "predecessor_text_sha256": predecessor.text_sha256,
                    "normalized_input_sha256": sha256(normalized.encode("utf-8")),
                    "delivered_text_sha256": sha256(outcome.text.encode("utf-8")),
                    "refusal_reason": outcome.refusal_reason,
                }
            )
        root_request = parent.trace_records[f"{root_id}/request"]
        if root_request.get("stitched_request_ids") != contacted:
            raise BundleError(
                "terminal non-skipped windows disagree with parent stitch order"
            )
        text = " ".join(span for span in delivered if span)
        rows.append(
            {
                "request_id": f"{root_id}/delivery/{declaration['cell_id']}",
                "sample_id": sample_id,
                "carrier_lock_key": source_row["carrier_lock_key"],
                "arm": source_row["arm"],
                "text": text,
                "admitted": source_row["admitted"],
                "delivery_text_sha256": sha256(text.encode("utf-8")),
                "source_request_id": root_id,
                "source_output_sha256": sha256(canonical(source_row)),
            }
        )
    all_repair_obs = {
        rid
        for rid, payload in parent.trace_records.items()
        if rid.endswith("/obs") and payload.get("obs_repair")
    }
    if consumed_obs != all_repair_obs:
        raise BundleError("parent has unaccounted terminal repair windows")
    return rows, windows
