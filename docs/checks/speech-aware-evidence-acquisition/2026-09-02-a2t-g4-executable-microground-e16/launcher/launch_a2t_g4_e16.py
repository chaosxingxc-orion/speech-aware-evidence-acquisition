#!/usr/bin/env python3
"""Launch the zero-reuse G4 executable-microground E arm on selected16.

Preflight is deliberately contact-free.  The explicit run path is the only
path allowed to open the frozen core or the unchanged official scorer.
"""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
import hashlib
import json
from pathlib import Path

from speech_aware_evidence_acquisition.contracts import ExecutionPlan
from speech_aware_evidence_acquisition.data.lock import data_root
from speech_aware_evidence_acquisition.rails.a2t_semantic_microground import (
    route_semantic_microground,
)
from speech_aware_evidence_acquisition.rails.probes.a2t_g4_microground_flight import (
    G4_MICROGROUND_E_PHASE,
    G4_QUEUE_DEPTH,
    G4_SCREEN_SPLIT_ID,
    G4_SLOT_COUNT,
    G4MicrogroundAdapter,
)


REPO = Path(__file__).resolve().parents[5]
RUN_ID = "SAEA-A2T-G4-EXECUTABLE-MICROGROUND-E16-V1"
AUDIO2TOOL_LOCK_KEY = "audio2tool"

EXPECTED_TIERS = tuple(
    f"tier{number}_{name}"
    for number, name in enumerate(
        (
            "direct",
            "parametric",
            "multi_intent",
            "implicit",
            "needle",
            "correction",
            "multiturn",
            "intent_blending",
        ),
        start=1,
    )
)
SELECTED_IDS = tuple(
    sorted(
        (
            "tier1_direct:003713",
            "tier1_direct:000074",
            "tier2_parametric:001869",
            "tier2_parametric:000568",
            "tier3_multi_intent:001732",
            "tier3_multi_intent:002166",
            "tier4_implicit:001759",
            "tier4_implicit:001628",
            "tier5_needle:001059",
            "tier5_needle:002546",
            "tier6_correction:001056",
            "tier6_correction:003671",
            "tier7_multiturn:001590",
            "tier7_multiturn:000637",
            "tier8_intent_blending:000489",
            "tier8_intent_blending:000324",
        )
    )
)
SELECTED_SPLIT_SHA256 = (
    "7590dfef54b42601c266f2bb325faee073143a575beeccd0c33cc8baf13aed45"
)
SELECTED_RUN_SHA256 = (
    "f9e3055f7eceff49405a192806be933db9bfcab150a1778bb3ddd937a8f57269"
)
PLANNED_AUDIO_SECONDS = 179

SLOT_COUNT = G4_SLOT_COUNT
QUEUE_DEPTH = G4_QUEUE_DEPTH
MAX_TOKENS = 1024
MAX_CONTACTS = 1
REPAIR_CONTACTS = 0
RETRIES = 0
JITTER_TESTING = False
PROMPT_UTF8_BYTE_CAP = 24_000

# These bindings are intentionally fail-closed until the independent builder
# and frozen configuration receipts land.  Never replace them with guessed
# identities.
CORPUS_BUILD_RELPATH: str | None = None
CORPUS_BUILD_SHA256: str | None = None
CORPUS_FILE_RELPATH: str | None = None
CORPUS_FILE_SHA256: str | None = None
CORPUS_BOUND_SHA256: str | None = None
COMPOSED_CONFIG_SHA256: str | None = None
PROTOCOL_SHA256: str | None = None
ROUTE_SET_SHA256: str | None = None

OFFICIAL_SCORE_PLAN: Mapping[str, object] = {
    "workers": 1,
    "operation": "finalize",
    "dataset_sharding": False,
    "shard_metric_averaging": False,
    "network_jitter_testing": False,
    "jobs": [
        {
            "job_id": "g4-e16",
            "input": "complete 16-row run manifest",
            "row_count": 16,
        }
    ],
}


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _validate_selected_ids(tier_by_sample: Mapping[str, str]) -> tuple[str, ...]:
    if set(tier_by_sample) != set(SELECTED_IDS):
        raise RuntimeError("runtime identities drift from the frozen G3 selected16")
    counts = Counter(tier_by_sample.values())
    if counts != Counter({tier: 2 for tier in EXPECTED_TIERS}):
        raise RuntimeError("runtime tiers drift from the frozen G3 selected16")
    if any(
        tier_by_sample[sample_id] != sample_id.split(":", 1)[0]
        for sample_id in SELECTED_IDS
    ):
        raise RuntimeError("runtime tier labels drift from the frozen G3 selected16")
    return SELECTED_IDS


def _execution_plan(attempt_id: str, *, protocol_hash: str | None = None) -> ExecutionPlan:
    bound_protocol = protocol_hash or PROTOCOL_SHA256
    if not isinstance(bound_protocol, str) or len(bound_protocol) != 64:
        raise RuntimeError("PROTOCOL_SHA256 is not bound")
    return ExecutionPlan(
        run_id=RUN_ID,
        execution_profile="bounded-discovery-probe",
        carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
        split_role="discovery",
        split_identity_hash=SELECTED_SPLIT_SHA256,
        planned_model_calls=16,
        planned_gpu_hours=0.3,
        planned_speech_audio_seconds=PLANNED_AUDIO_SECONDS,
        protocol_hash=bound_protocol,
        attempt_id=attempt_id,
    ).validate()


def _route_selected(
    corpus: object,
    observations: Mapping[str, str],
    *,
    route_fn: Callable[..., object] = route_semantic_microground,
) -> tuple[dict[str, object], str]:
    if set(observations) != set(SELECTED_IDS):
        raise RuntimeError("OBS identities drift from the frozen G3 selected16")
    routes = {
        sample_id: route_fn(
            corpus,
            observation=observations[sample_id],
            max_utf8_bytes=16_384,
        )
        for sample_id in SELECTED_IDS
    }
    route_binding = {
        sample_id: {
            "packet_sha256": getattr(route, "packet_sha256"),
            "trace_sha256": getattr(route, "trace_sha256"),
            "candidate_names": list(getattr(route, "candidate_names")),
        }
        for sample_id, route in routes.items()
    }
    return routes, _canonical_sha256(route_binding)


def _build_adapter(
    samples: Sequence[object],
    observations: Mapping[str, str],
    routes: Mapping[str, object],
    *,
    prompt_utf8_byte_cap: int = PROMPT_UTF8_BYTE_CAP,
) -> tuple[G4MicrogroundAdapter, dict[str, object]]:
    sample_by_id = {str(getattr(sample, "sample_id")): sample for sample in samples}
    if set(sample_by_id) != set(SELECTED_IDS):
        raise RuntimeError("runtime samples drift from the frozen G3 selected16")
    if set(observations) != set(SELECTED_IDS) or set(routes) != set(SELECTED_IDS):
        raise RuntimeError("G4 adapter surfaces are incomplete")
    adapter = G4MicrogroundAdapter(
        tuple(sample_by_id[sample_id] for sample_id in SELECTED_IDS),
        phase=G4_MICROGROUND_E_PHASE,
        state_by_sample=observations,
        packet_by_sample={
            sample_id: str(getattr(routes[sample_id], "packet"))
            for sample_id in SELECTED_IDS
        },
    )
    by_sample: dict[str, int] = {}
    for sample in adapter.load_split(G4_SCREEN_SPLIT_ID):
        prompt = adapter.assemble_prompt(sample, None)
        size = len(
            json.dumps(prompt, sort_keys=True, separators=(",", ":")).encode("utf-8")
        )
        if size > prompt_utf8_byte_cap:
            raise RuntimeError(
                f"G4 prompt-size cap exceeded for {sample.sample_id}: "
                f"{size} > {prompt_utf8_byte_cap}"
            )
        by_sample[sample.sample_id] = size
    return adapter, {
        "count": len(by_sample),
        "cap_utf8_bytes": prompt_utf8_byte_cap,
        "max_utf8_bytes": max(by_sample.values()),
        "by_sample": dict(sorted(by_sample.items())),
    }


def _validate_official_score_plan(
    plan: Mapping[str, object],
) -> Mapping[str, object]:
    jobs = plan.get("jobs")
    if (
        plan.get("workers") != 1
        or plan.get("operation") != "finalize"
        or plan.get("dataset_sharding") is not False
        or plan.get("shard_metric_averaging") is not False
        or plan.get("network_jitter_testing") is not False
        or not isinstance(jobs, list)
        or len(jobs) != 1
        or jobs[0].get("input") != "complete 16-row run manifest"
        or jobs[0].get("row_count") != 16
    ):
        raise RuntimeError("G4 scoring must be one whole-manifest official job")
    return plan


def _unbound_requirements() -> tuple[str, ...]:
    names = (
        "CORPUS_BUILD_RELPATH",
        "CORPUS_BUILD_SHA256",
        "CORPUS_FILE_RELPATH",
        "CORPUS_FILE_SHA256",
        "CORPUS_BOUND_SHA256",
        "COMPOSED_CONFIG_SHA256",
        "PROTOCOL_SHA256",
        "ROUTE_SET_SHA256",
    )
    return tuple(name for name in names if globals()[name] is None)


def _static_preflight(root: Path) -> dict[str, object]:
    del root
    missing = _unbound_requirements()
    if missing:
        raise RuntimeError(
            "G4 launcher bindings are incomplete: " + ", ".join(missing)
        )
    raise RuntimeError("G4 preflight implementation is unreachable without bindings")


def _launch(root: Path) -> Mapping[str, object]:
    """Enter the explicit contact path only after the full preflight passes."""

    context = _static_preflight(root)
    # The contact implementation is activated only after every builder/config
    # identity above is bound.  Keeping this refusal here prevents a partial E
    # flight from consuming the one-shot exposure surface.
    raise RuntimeError(
        "G4 E16 contact path is sealed until all launcher bindings pass preflight; "
        f"verified {len(context['selected_ids'])} rows"
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight-only", action="store_true")
    mode.add_argument("--run", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = data_root()
    if args.preflight_only:
        context = _static_preflight(root)
        print(
            json.dumps(
                {
                    "run_id": RUN_ID,
                    "preflight": "passed",
                    "study_commit": context["commit"],
                    "samples": len(context["selected_ids"]),
                    "route_set_sha256": context["route_set_sha256"],
                    "max_prompt_utf8_bytes": context["prompt_report"][
                        "max_utf8_bytes"
                    ],
                    "official_score_manifests": 1,
                    "contacts": {
                        "gold": 0,
                        "model": 0,
                        "network": 0,
                        "retriever": 0,
                        "scorer": 0,
                        "tokenizer": 0,
                    },
                },
                sort_keys=True,
            )
        )
        return 0
    result = _launch(root)
    print(json.dumps(result, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
