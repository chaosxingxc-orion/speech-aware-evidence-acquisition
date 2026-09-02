#!/usr/bin/env python3
"""Contact-free preflight and injectable runtime for the G7 fixed16 screen.

This module never discovers or reads construction rows. A separately authorized
caller must build and pass the frozen ``ConstructionExampleGround`` artifact.
The command-line entry point performs identity/config checks only and cannot
start a model service or contact a model, scorer, tokenizer, or network.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Callable, Mapping, Sequence


REPO = Path(__file__).resolve().parents[5]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from speech_aware_evidence_acquisition.rails.probes.a2t_g7_example_ground import (  # noqa: E402
    G7ExampleGround,
    execute_g7_workflows,
    parse_family_assessment,
)
from speech_aware_evidence_acquisition.contracts import ExecutionPlan  # noqa: E402
from speech_aware_evidence_acquisition.core.config import compose, protocol_hash  # noqa: E402
from speech_aware_evidence_acquisition.data.audio2tool import AUDIO2TOOL_LOCK_KEY  # noqa: E402


RUN_ID = "SAEA-A2T-G7-EXHAUSTIVE-EXAMPLE-GROUND-FIXED16-V1"
SPLIT_ID = "A2T-G7-EXAMPLE-FIXED16"
SPLIT_IDENTITY_HASH = "94a10c359dfe9e6a96cd63940c4dcb52fc7206e4c0e7d855733b21b69b987212"
ROSTER_SHA256 = "8be941c6e82527f9b63cd1f9ea09449f6cabbf175e7b2401642de455edc975c3"
BUILDER_COMMIT = "7046ce6e7fbbba67ddbae5f122748e2158761e23"
GROUND_SHA256 = "a5bb788a64db320b8d09de3712ede38f46c5395d8e7dd1932d8acbbf8cedc855"
GROUND_RECEIPT_SHA256 = "65d7a94296bc893de877c020370815833e697bb8f6ff26c210f9a73111299dc7"
CONTACTS_PER_SAMPLE = 30
SAMPLE_COUNT = 16
MODEL_CONTACTS = CONTACTS_PER_SAMPLE * SAMPLE_COUNT
SLOTS = 2
MAX_CONCURRENT_MODEL_REQUESTS = 2
QUEUE_DEPTH = 4
OBS_COMPLETION_TOKENS = 512
EVIDENCE_COMPLETION_TOKENS = 512
RESOLVE_COMPLETION_TOKENS = 1024
COMPOSED_CONFIG_SHA256 = "d9eea74417d95cdf32e7fd44e23ec4012f8172f3828dd2f7fd10efdf5597c20d"
PROTOCOL_SHA256 = "e2a7a37dd14a237f3fe89b63e79e76cea334676354ed689242c3f5778f010e02"

ROSTER = REPO / "docs/receipts/a2t/A2T-G7-EXAMPLE-FIXED16.json"
BASELINE = REPO / "configs/baseline/a2t-g7-exhaustive-example-ground-agentloop.json"
EXPERIMENT = REPO / "configs/experiment/a2t-g7-exhaustive-example-ground-fixed16-v1.json"
GROUND_CORPUS = REPO / "knowledge/audio2tool/g7-construction-example-ground-v1/corpus.txt"
GROUND_RECEIPT = REPO / (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-02-a2t-g7-exhaustive-example-ground-fixed16-v1/ground-receipt.json"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def execution_plan(attempt_id: str) -> ExecutionPlan:
    """Return the exact structured G7 flight plan without opening a service."""
    return ExecutionPlan(
        run_id=RUN_ID,
        execution_profile="bounded-discovery-probe",
        carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
        split_role="discovery",
        split_identity_hash=SPLIT_IDENTITY_HASH,
        planned_model_calls=MODEL_CONTACTS,
        planned_gpu_hours=1.0,
        planned_speech_audio_seconds=185,
        protocol_hash=PROTOCOL_SHA256,
        attempt_id=attempt_id,
    ).validate()


def _byte_upper_bound(text: str) -> int:
    """Return a conservative tokenizer-free construction bound for ASCII prompts."""
    return len(text.encode("utf-8"))


def _render_obs() -> str:
    return (
        "Listen to the original complete dialogue. Describe the spoken request in bounded "
        "plain English. Do not name tools, propose a final answer, or add metadata."
    )


def _render_evidence(context: object) -> str:
    return (
        f"OBSERVATION\n{context.observation}\n\nFAMILY CONSTRUCTION EXAMPLES\n"
        f"{context.family_bundle_text}\n\nINSTRUCTION\n{context.instruction}"
    )


def _render_resolve(context: object) -> str:
    return (
        f"OBSERVATION\n{context.observation}\n\n"
        "ALL-TOOL EXECUTION SHEET WITH 152 NORMALIZED ASSESSMENTS\n"
        f"{context.execution_sheet}\n\n"
        f"INSTRUCTION\n{context.instruction}"
    )


def _fit_dict(fit: object) -> dict[str, int | str]:
    return {
        "contact_id": fit.contact_id,
        "prompt_tokens": fit.prompt_tokens,
        "completion_tokens": fit.completion_tokens,
        "total_tokens": fit.total_tokens,
        "remaining_tokens": fit.remaining_tokens,
    }


def preflight_ground(
    ground: object, *, speech_feature_tokens_max: int
) -> dict[str, object]:
    """Validate the in-memory artifact and measure every static exact prompt."""
    if getattr(ground, "receipt", {}).get("schema") != (
        "saea-a2t-construction-example-ground-receipt-v1"
    ):
        raise ValueError("construction-example ground receipt schema is not frozen")
    if ground.sha256 != GROUND_SHA256:
        raise ValueError("construction-example ground SHA-256 drift")
    core = G7ExampleGround(ground.bundles)
    observation = type("Obs", (), {"text": "No reliable observation was available."})()
    obs = core.measure_prompt(
        contact_id="g7-obs",
        text=_render_obs(),
        token_counter=_byte_upper_bound,
        completion_tokens=OBS_COMPLETION_TOKENS,
        speech_feature_tokens=speech_feature_tokens_max,
    )
    evidence = tuple(
        core.measure_prompt(
            contact_id=context.contact_id,
            text=_render_evidence(context),
            token_counter=_byte_upper_bound,
            completion_tokens=EVIDENCE_COMPLETION_TOKENS,
        )
        for context in core.build_evidence_contexts(observation)
    )
    empty = tuple(
        parse_family_assessment(
            "{}", family_tag=context.family_tag, family_tool_names=context.tool_names
        )
        for context in core.build_evidence_contexts(observation)
    )
    worst = tuple(
        parse_family_assessment(
            json.dumps(
                {
                    "assessments": [
                        {
                            "tool_name": tool_name,
                            "status": "support",
                            "evidence": ["abcdefghijklmnop", "qrstuvwxyzabcdef"],
                        }
                        for tool_name in context.tool_names
                    ]
                },
                separators=(",", ":"),
            ),
            family_tag=context.family_tag,
            family_tool_names=context.tool_names,
        )
        for context in core.build_evidence_contexts(observation)
    )
    resolve_base = core.measure_prompt(
        contact_id="g7-resolve",
        text=_render_resolve(core.build_resolve_context(observation, empty)),
        token_counter=_byte_upper_bound,
        completion_tokens=RESOLVE_COMPLETION_TOKENS,
        speech_feature_tokens=speech_feature_tokens_max,
    )
    resolve_worst = core.measure_prompt(
        contact_id="g7-resolve",
        text=_render_resolve(core.build_resolve_context(observation, worst)),
        token_counter=_byte_upper_bound,
        completion_tokens=RESOLVE_COMPLETION_TOKENS,
        speech_feature_tokens=speech_feature_tokens_max,
    )
    return {
        "schema": "saea-a2t-g7-precontact-report-v1",
        "run_id": RUN_ID,
        "split_id": SPLIT_ID,
        "split_identity_hash": SPLIT_IDENTITY_HASH,
        "roster_sha256": ROSTER_SHA256,
        "builder_commit": BUILDER_COMMIT,
        "ground_sha256": ground.sha256,
        "contacts": MODEL_CONTACTS,
        "contacts_per_sample": CONTACTS_PER_SAMPLE,
        "audio_contacts_per_sample": 2,
        "family_count": len(ground.bundles),
        "tool_count": len(ground.tool_names),
        "slots": SLOTS,
        "max_concurrent_model_requests": MAX_CONCURRENT_MODEL_REQUESTS,
        "queue_depth": QUEUE_DEPTH,
        "token_counter": "utf8-byte-construction-upper-bound",
        "obs_prompt": _fit_dict(obs),
        "evidence_prompts": [_fit_dict(row) for row in evidence],
        "resolve_empty_assessment_base_prompt": _fit_dict(resolve_base),
        "resolve_worst_normalized_assessment_prompt": _fit_dict(resolve_worst),
        "resolve_measurement": "dynamic-after-152-assessments-seal",
    }


def execute_preflighted(
    *,
    sample_ids: Sequence[str],
    ground: object,
    speech_feature_tokens_by_sample: Mapping[str, int],
    invoke_contact: Callable[[str, str, object], str],
) -> tuple[object, ...]:
    """Execute through an injected contact function with fail-closed prompt fits."""
    if len(sample_ids) != SAMPLE_COUNT or set(sample_ids) != set(speech_feature_tokens_by_sample):
        raise ValueError("execution requires the exact sixteen receipt-bound samples")
    preflight_ground(
        ground, speech_feature_tokens_max=max(speech_feature_tokens_by_sample.values())
    )
    core = G7ExampleGround(ground.bundles)

    def measured(sample_id: str, stage: str, context: object) -> str:
        if stage == "OBS":
            rendered, completion, speech = (
                _render_obs(),
                OBS_COMPLETION_TOKENS,
                speech_feature_tokens_by_sample[sample_id],
            )
        elif stage == "EVIDENCE":
            rendered, completion, speech = _render_evidence(context), EVIDENCE_COMPLETION_TOKENS, 0
        else:
            rendered, completion, speech = (
                _render_resolve(context),
                RESOLVE_COMPLETION_TOKENS,
                speech_feature_tokens_by_sample[sample_id],
            )
        core.measure_prompt(
            contact_id=getattr(context, "contact_id", "g7-obs"),
            text=rendered,
            token_counter=_byte_upper_bound,
            completion_tokens=completion,
            speech_feature_tokens=speech,
        )
        return invoke_contact(sample_id, stage, context)

    return execute_g7_workflows(
        sample_ids=sample_ids, bundles=ground.bundles, invoke_contact=measured
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify committed precontact bindings")
    args = parser.parse_args()
    if not args.check:
        parser.error("only --check is available before a separately authorized ground is supplied")
    if _sha256(ROSTER) != ROSTER_SHA256:
        raise SystemExit("G7 roster hash mismatch")
    if _sha256(GROUND_CORPUS) != GROUND_SHA256:
        raise SystemExit("G7 construction ground hash mismatch")
    if _sha256(GROUND_RECEIPT) != GROUND_RECEIPT_SHA256:
        raise SystemExit("G7 construction ground receipt hash mismatch")
    for path in (BASELINE, EXPERIMENT, GROUND_RECEIPT):
        json.loads(path.read_text(encoding="utf-8"))
    composed = compose(
        REPO,
        "q4km-mmproj-free-speech-native-np2-a2t-max1024",
        "audio2tool-g1-104",
        "a2t-g7-exhaustive-example-ground-agentloop",
        "a2t-g7-exhaustive-example-ground-fixed16-v1",
    )
    if composed.config_hash != COMPOSED_CONFIG_SHA256:
        raise SystemExit("G7 composed config identity mismatch")
    measured_protocol = protocol_hash(
        composed.config_hash, str(composed.values["arm"]), SPLIT_IDENTITY_HASH
    )
    if measured_protocol != PROTOCOL_SHA256:
        raise SystemExit("G7 protocol identity mismatch")
    execution_plan("precontact-check")
    print(json.dumps({"status": "PRECONTACT_ONLY", "contacts_sent": 0}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
