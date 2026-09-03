#!/usr/bin/env python3
"""Thin G8C fixed12 successor over the corrected frozen G8B protocol.

Only identity, cardinality, run/config paths, cost geometry, and audit namespaces
change here. Prompts, parsers, macro-actions, OpenJiuwen execution, context
policy, and batching are inherited from the prospective corrected G8B launcher.
The default command is a contact-free preflight; this file itself authorizes no
model, scorer, audio-byte, gold, or network contact.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Mapping, Sequence


REPO = Path(__file__).resolve().parents[5]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

G8B_LAUNCHER = REPO / (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-03-a2t-g8b-action-support-reachability-fixed16-v1/launcher/"
    "launch_a2t_g8b_fixed16.py"
)
_SPEC = importlib.util.spec_from_file_location("_saea_g8b_corrected_parent", G8B_LAUNCHER)
if _SPEC is None or _SPEC.loader is None:  # pragma: no cover
    raise RuntimeError("cannot load the corrected G8B protocol surface")
_parent = importlib.util.module_from_spec(_SPEC)
sys.modules.setdefault(_SPEC.name, _parent)
_SPEC.loader.exec_module(_parent)

G8B_RUN_ID = _parent.RUN_ID
G8C_ROSTER = REPO / "docs/receipts/a2t/A2T-G8C-ACTION-SUPPORT-FIXED12.json"
G8B_ROSTER = REPO / "docs/receipts/a2t/A2T-G8B-ACTION-SUPPORT-FIXED16.json"

RUN_ID = "SAEA-A2T-G8C-ACTION-SUPPORT-REACHABILITY-FIXED12-V1"
SPLIT_ID = "A2T-G8C-ACTION-SUPPORT-FIXED12"
SPLIT_IDENTITY_HASH = "acf2d1e7664987bf7154e2e45ed366b712c11e710910cf94af067e90ba4e1acb"
ROSTER_SHA256 = "f00ab9486d978c334e14c96231ac45968f24c3bf8792181427703b738260dac0"
G8B_ROSTER_SHA256 = "9a7b60394f53578d5ab948d1e5de4737cff73d1803a86883182c90fd0cc48705"
G8B_LAUNCHER_SHA256 = "65047c7a96dac5601368739944e01921510d302d844e3b28ada2e358b7379229"
BASELINE_FRAGMENT = "a2t-g8c-action-support-reachability-agentloop"
EXPERIMENT_FRAGMENT = "a2t-g8c-action-support-reachability-fixed12-v1"
COMPOSED_CONFIG_SHA256 = "137f3caab46a5a8818c90bd526d0d7868d2ee386f4c0d5308a12763c0146fc76"
PROTOCOL_SHA256 = "b68f29ac9afffd9bdc4064ce4d2959c8b7b9f54f99fd80842a0496d090672465"
SAMPLE_COUNT = 12
SHARED_CONTACTS_PER_SAMPLE = 29
BASE_DYNAMIC_CONTACTS = 396
MAX_MODEL_CONTACTS = 408
MIN_MODEL_CONTACTS = 384
MODEL_CONTACTS = MAX_MODEL_CONTACTS
REPEATED_SPEECH_AUDIO_SECONDS = 76.694
PLANNED_SPEECH_AUDIO_SECONDS = 2608

PROTOCOL_DESCRIPTOR = {
    "schema": "saea-a2t-g8c-action-support-reachability-protocol-v1",
    "scientific_protocol_parent_run_id": G8B_RUN_ID,
    "run_id": RUN_ID,
    "empty_selection": "EMPTY_BIND_PASSTHROUGH_THEN_FINAL_RESOLVE",
    "invalid_select": "TERMINAL_RAW_RESPONSE_FOR_SAMPLE",
    "invalid_nonempty_bind": "TERMINAL_RAW_RESPONSE_FOR_SAMPLE",
    "retry_repair_strip_substitution": False,
    "planned_contact_ceiling": MAX_MODEL_CONTACTS,
    "realized_contact_formula": (
        "396 + nonempty_valid_selections - invalid_selects - invalid_binds"
    ),
}
PROTOCOL_DESCRIPTOR_SHA256 = hashlib.sha256(
    json.dumps(
        PROTOCOL_DESCRIPTOR,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
).hexdigest()


def _configure_parent() -> None:
    """Install immutable G8C identity parameters into one private parent module."""
    if hashlib.sha256(G8B_LAUNCHER.read_bytes()).hexdigest() != G8B_LAUNCHER_SHA256:
        raise RuntimeError("corrected G8B parent launcher hash drift")
    values = {
        "BASELINE_FRAGMENT": BASELINE_FRAGMENT,
        "EXPERIMENT_FRAGMENT": EXPERIMENT_FRAGMENT,
        "SPLIT_ID": SPLIT_ID,
        "SPLIT_IDENTITY_HASH": SPLIT_IDENTITY_HASH,
        "ROSTER_SHA256": ROSTER_SHA256,
        "G8B_ROSTER": G8C_ROSTER,
        "G8_ROSTER": G8B_ROSTER,
        "G8_ROSTER_SHA256": G8B_ROSTER_SHA256,
        "COMPOSED_CONFIG_SHA256": COMPOSED_CONFIG_SHA256,
        "SAMPLE_COUNT": SAMPLE_COUNT,
        "SHARED_CONTACTS_PER_SAMPLE": SHARED_CONTACTS_PER_SAMPLE,
        "BASE_DYNAMIC_CONTACTS": BASE_DYNAMIC_CONTACTS,
        "MAX_MODEL_CONTACTS": MAX_MODEL_CONTACTS,
        "MIN_MODEL_CONTACTS": MIN_MODEL_CONTACTS,
        "MODEL_CONTACTS": MODEL_CONTACTS,
        "REPEATED_SPEECH_AUDIO_SECONDS": REPEATED_SPEECH_AUDIO_SECONDS,
        "PLANNED_SPEECH_AUDIO_SECONDS": PLANNED_SPEECH_AUDIO_SECONDS,
        "RUN_ID": RUN_ID,
        "TRACE_RECORD_PREFIX": "g8c",
        "DERIVATIVE_SOURCE_KIND": "sealed-g8c",
        "RAW_INVALID_SOURCE_KIND": "sealed-g8c-raw-invalid-stage-response",
        "FINAL_SOURCE_KIND": "sealed-g8c-frozen-core-final",
        "MISSION_SUBDIR": "g8c",
        "REQUEST_ID_PREFIX": "g8cfixed12",
        "PREFLIGHT_SCHEMA": "saea-a2t-g8c-action-support-precontact-report-v1",
        "FLIGHT_RECEIPT_SCHEMA": "saea-a2t-g8c-action-support-fixed12-flight-v1",
        "PROTOCOL_DESCRIPTOR": PROTOCOL_DESCRIPTOR,
        "PROTOCOL_DESCRIPTOR_SHA256": PROTOCOL_DESCRIPTOR_SHA256,
        "PROTOCOL_SHA256": PROTOCOL_SHA256,
    }
    for name, value in values.items():
        setattr(_parent, name, value)


_configure_parent()

# Re-export the private configured parent as a deliberately small successor API.
Audio2ToolSample = _parent.Audio2ToolSample
ContactRecord = _parent.ContactRecord
ExecutionPlan = _parent.ExecutionPlan
FlightSummary = _parent.FlightSummary
FrozenCoreClient = _parent.FrozenCoreClient
FrozenCoreGate = _parent.FrozenCoreGate
G8ActionSupportCore = _parent.G8ActionSupportCore
ToolBindings = _parent.ToolBindings
ToolSelection = _parent.ToolSelection
TraceSink = _parent.TraceSink
BRANCH_ORDER = _parent.BRANCH_ORDER
_emit_state_audits = _parent._emit_state_audits
_selected_roster_ids = _parent._selected_roster_ids
_state_geometry = _parent._state_geometry
_verify_repeated_speech_reservation = _parent._verify_repeated_speech_reservation
build_branch_derivatives = _parent.build_branch_derivatives
classify_binding_response = _parent.classify_binding_response
classify_selection_response = _parent.classify_selection_response
empty_bind_passthrough = _parent.empty_bind_passthrough
execution_plan = _parent.execution_plan
load_runtime_surface = _parent.load_runtime_surface
physical_and_logical_costs = _parent.physical_and_logical_costs
run_openjiuwen_phase = _parent.run_openjiuwen_phase
static_preflight = _parent.static_preflight

_parent_parallel_score_plan = _parent.parallel_score_plan


def parallel_score_plan(branch_manifests: Mapping[str, Path]) -> dict[str, object]:
    """Keep the inherited outer scorer plan but bind every job to fixed12."""
    document = _parent_parallel_score_plan(branch_manifests)
    for job in document["jobs"]:
        job["row_count"] = SAMPLE_COUNT
    return document


# Parent sealing resolves this name dynamically, so install the cardinality-only wrapper.
_parent.parallel_score_plan = parallel_score_plan


def launch(root: Path, attempt_id: str, *, execute: bool = False) -> Mapping[str, object]:
    """Delegate to the configured frozen parent state machine."""
    return _parent.launch(root, attempt_id, execute=execute)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight-only", action="store_true")
    mode.add_argument("--run", action="store_true")
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--attempt-id", required=True)
    args = parser.parse_args(argv)
    root = args.data_root or _parent._v1.data_root()
    print(json.dumps(launch(root, args.attempt_id, execute=args.run), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
