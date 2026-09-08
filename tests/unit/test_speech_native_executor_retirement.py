"""The legacy speech-native executor's retirement (owner Decision 12-F, 2026-09-08).

Assessment ``docs/readiness/2026-09-08-openjiuwen-implementation-assessment-v1.md``
section 5.4 item 3: *name the executor explicitly, in one spelling.* Today
``openjiuwen-workflow-v1`` was reached by four different config keys and, for
the SLURP phase-program cells, by no key at all -- and 32 speech-native
baselines reached ``legacy-contact-dag-v1`` by declaring nothing whatsoever.
A cell that does not name its executor cannot state which harness produced
its number.

What retires the legacy executor is therefore not a rewrite. It is that the
silent default is gone: ``build_speech_native_profile`` (and
``finalize_from_disk``) refuse a fragment that does not name an executor, so
the legacy contact DAG can only be reached by a fragment that SAYS SO, and
its remaining users are exactly the list this suite enumerates. Shrinking
that list is per-carrier phase-program work
(``configs/baseline/slurp-phase-direct-only-v1.json`` demonstrates it for the
simplest of them), not something a config edit can do: the openJiuwen
speech-native executor is an M1/M2 one-or-two-contact vertical slice, and
none of the 32 composes into it.

Model-free: this suite reads committed JSON and calls one validator. Zero
model, GPU, network and dataset contacts.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE_DIR = REPO_ROOT / "configs" / "baseline"
EXECUTOR_KEY = "speech_native_agent_executor_id"
LEGAL_EXECUTORS = frozenset({"legacy-contact-dag-v1", "openjiuwen-workflow-v1"})

#: Every baseline fragment that reaches the speech-native profile driver.
SPEECH_NATIVE_BASELINES = tuple(sorted(BASELINE_DIR.glob("speech-native-*.json")))


def _document(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_the_speech_native_baseline_set_is_the_thirty_two_the_assessment_counted():
    assert len(SPEECH_NATIVE_BASELINES) == 32, [
        path.name for path in SPEECH_NATIVE_BASELINES
    ]


@pytest.mark.parametrize(
    "path", SPEECH_NATIVE_BASELINES, ids=lambda path: path.name
)
def test_every_speech_native_baseline_names_its_executor(path):
    """No fragment may reach an executor by saying nothing. This is the whole
    of the retirement: the list of legacy users is now a grep, not a
    default."""

    document = _document(path)
    executor = document.get(EXECUTOR_KEY)
    assert executor in LEGAL_EXECUTORS, f"{path.name} declares {executor!r}"


def test_the_remaining_legacy_users_are_enumerable_and_are_all_thirty_two():
    """The retirement's own ledger. When a carrier's cells become phase
    programs this number drops; it can never rise by accident, because a new
    fragment that names nothing is refused before any packet is promoted."""

    legacy = [
        path.name
        for path in SPEECH_NATIVE_BASELINES
        if _document(path).get(EXECUTOR_KEY) == "legacy-contact-dag-v1"
    ]
    assert len(legacy) == 32
    assert all(name.startswith("speech-native-") for name in legacy)


def test_no_speech_native_baseline_composes_into_the_openjiuwen_executor_today():
    """Why every one of the 32 still names the legacy id, measured rather
    than asserted: the openJiuwen speech-native path requires the predictions
    result mode, matcher policy M1 or M2, and that policy's own one/two
    contact ceiling. Not one fragment satisfies all three, so re-pointing
    them would refuse them rather than port them."""

    eligible = []
    for path in SPEECH_NATIVE_BASELINES:
        document = _document(path)
        ceiling = {"M1": 1, "M2": 2}.get(document.get("matcher_policy_id"))
        if (
            document.get("speech_native_result_mode") == "predictions"
            and ceiling is not None
            and document.get("speech_native_contact_ceiling_per_task", 1) == ceiling
        ):
            eligible.append(path.name)
    assert eligible == []


def test_the_profile_builder_refuses_a_fragment_that_names_no_executor():
    """The default itself, gone. The refusal names the retirement, both legal
    spellings and the date, so a fragment written before today is repaired
    rather than guessed at."""

    from speech_aware_evidence_acquisition.core.driver.speech_native import (
        SpeechNativeProfileError,
        resolve_speech_native_agent_executor_id,
    )

    with pytest.raises(SpeechNativeProfileError, match="retired on 2026-09-08"):
        resolve_speech_native_agent_executor_id({})
    with pytest.raises(SpeechNativeProfileError, match="must be"):
        resolve_speech_native_agent_executor_id({EXECUTOR_KEY: "some-third-harness"})
    # One resolver for both call sites -- the profile flight and
    # finalize-from-disk -- so the two can never disagree about what a cell
    # declared.
    for executor in sorted(LEGAL_EXECUTORS):
        assert (
            resolve_speech_native_agent_executor_id({EXECUTOR_KEY: executor})
            == executor
        )
