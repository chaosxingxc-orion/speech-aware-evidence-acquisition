"""Measure exact tokenizer fit for G2 in the model's full 65,536-token slot."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Mapping


REPO = Path(__file__).resolve().parents[4]
SOURCE = REPO / (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-02-a2t-executable-ground-prompt-fit-v1/run_prompt_fit.py"
)
SPEC = importlib.util.spec_from_file_location("saea_ground_prompt_fit_v1", SOURCE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load the frozen prompt-fit runner")
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


def _single_slot_bounds(text_prompt_tokens: Mapping[str, int]) -> dict[str, object]:
    direct = "ground-direct"
    observed = "ground-agent-observed"
    expected = {direct, observed}
    if set(text_prompt_tokens) != expected:
        raise RuntimeError("prompt-fit envelopes drifted")
    rows: list[dict[str, object]] = []
    for envelope_id in (direct, observed):
        text_tokens = text_prompt_tokens[envelope_id]
        observation = (
            RUNNER.OBSERVATION_TOKEN_ALLOWANCE
            if envelope_id == observed
            else 0
        )
        prompt = (
            text_tokens
            + RUNNER.SPEECH_FEATURE_TOKEN_RESERVE
            + 2
            + observation
        )
        rows.append(
            {
                "envelope_id": envelope_id,
                "text_prompt_tokens": text_tokens,
                "speech_feature_token_reserve": RUNNER.SPEECH_FEATURE_TOKEN_RESERVE,
                "special_token_reserve": 2,
                "observation_token_allowance": observation,
                "prompt_tokens_with_all_reserves": prompt,
            }
        )
    worst = max(rows, key=lambda row: int(row["prompt_tokens_with_all_reserves"]))
    maximum_prompt = int(worst["prompt_tokens_with_all_reserves"])
    required = maximum_prompt + RUNNER.COMPLETION_TOKEN_ALLOWANCE
    context = 65_536
    margin = context - required
    if margin < 4_096:
        raise RuntimeError("G2 lacks the registered 4,096-token single-slot margin")
    return {
        "envelopes": rows,
        "worst_envelope_id": worst["envelope_id"],
        "maximum_text_prompt_tokens": max(text_prompt_tokens.values()),
        "maximum_prompt_tokens_with_all_reserves": maximum_prompt,
        "completion_token_allowance": RUNNER.COMPLETION_TOKEN_ALLOWANCE,
        "required_context_per_slot": required,
        "context_tokens": context,
        "slot_count": 1,
        "context_tokens_per_slot": context,
        "context_margin_tokens": margin,
        "minimum_registered_margin_tokens": 4_096,
        "maximum_prompt_fits_one_slot": True,
    }


RUNNER.EXPERIMENT_ID = (
    "SAEA-A2T-MF-CONSTRUCTION-SEMANTIC-GROUND-PROMPT-FIT-V2-NP1"
)
RUNNER.CHECK_DIR = Path(__file__).resolve().parent
RUNNER.OUTPUT = RUNNER.CHECK_DIR / "prompt-fit-result.json"
RUNNER.HANDBOOK_RELPATH = Path(
    "knowledge/audio2tool/construction-semantic-ground-v2/handbook.txt"
)
RUNNER.HANDBOOK_SHA256 = (
    "04c9c78d03b002faf6c828a5b35f1786aadc7f5da3fee2bf675374e7ea2ea697"
)
RUNNER.BUILD_RECEIPT_RELPATH = Path(
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-02-a2t-construction-semantic-ground-build-v2/build-receipt.json"
)
RUNNER.BUILD_RECEIPT_SHA256 = (
    "ad7a96c11fbd633e0d1643d385e44726f5a456c522619720e8dcc3f54da56b0d"
)
RUNNER.MODEL_FRAGMENT_RELPATH = Path(
    "configs/model/q4km-mmproj-free-speech-native-np1-a2t-max1024.json"
)
RUNNER.MODEL_FRAGMENT_SHA256 = (
    "0a76f4d257b43544caab01cef033cdd70964b2b5bd404353f9a09d696227a507"
)
RUNNER.SLOT_COUNT = 1
RUNNER.CONTEXT_TOKENS_PER_SLOT = 65_536
RUNNER.compute_prompt_fit_bounds = _single_slot_bounds


if __name__ == "__main__":
    raise SystemExit(RUNNER.main())
