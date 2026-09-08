"""``core.base``'s JUDGES registry, the ``Judge`` protocol and the structural
proof of owner Decision 11-C (2026-09-08): the Reviewer is CRITICISM ONLY --
it scores and flags, it never proposes a revision.

Model-free, no GPU, no network: every test drives the types directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import pytest

from speech_aware_evidence_acquisition.core.base import (
    JUDGE_FLAG_SEVERITIES,
    JUDGES,
    MAX_JUDGE_TEXT_CHARS,
    Judge,
    JudgeError,
    JudgeFlag,
    JudgeRegistry,
    JudgeVerdict,
    assert_criticism_only,
    assert_judge,
)


class _Judge:
    """A minimal conforming judge, used only as a registration fixture."""

    def __init__(self, judge_id: str, *, criticism_only: bool = True) -> None:
        self.id = judge_id
        self.version = "test-v1"
        self.criticism_only = criticism_only

    def __call__(
        self,
        draft: str,
        material: Mapping[str, object],
        state: Mapping[str, object],
    ) -> JudgeVerdict:
        return JudgeVerdict(judge_id=self.id, version=self.version, score=1.0)


# ---------------------------------------------------------------------------
# 1. The registry is the same one-Registry mechanism as every other seam.
# ---------------------------------------------------------------------------


def test_judges_is_a_registry_living_beside_the_other_core_base_registries():
    from speech_aware_evidence_acquisition.core import base

    assert isinstance(JUDGES, JudgeRegistry)
    assert JUDGES.names() == sorted(JUDGES.names())
    # Same module, same mechanism as the registries the owner rule names.
    for name in ("POLICIES", "EVIDENCE_SOURCES", "SCORERS", "AGENT_CONTROLLERS"):
        assert hasattr(base, name)


def test_registry_refuses_a_duplicate_and_a_blank_name():
    registry = JudgeRegistry("judge")
    registry.register("a-judge", _Judge("a-judge"))
    with pytest.raises(Exception):
        registry.register("a-judge", _Judge("a-judge"))
    with pytest.raises(Exception):
        registry.register("   ", _Judge("   "))


def test_registry_resolves_what_it_registered_and_refuses_what_it_did_not():
    registry = JudgeRegistry("judge")
    judge = _Judge("a-judge")
    registry.register("a-judge", judge)
    assert registry.resolve("a-judge") is judge
    with pytest.raises(Exception):
        registry.resolve("no-such-judge")


# ---------------------------------------------------------------------------
# 2. The door checks Decision 11-C: criticism_only=True, and one identity.
# ---------------------------------------------------------------------------


def test_registration_refuses_a_judge_that_does_not_declare_criticism_only():
    registry = JudgeRegistry("judge")
    with pytest.raises(JudgeError, match="criticism_only=True"):
        registry.register("loud", _Judge("loud", criticism_only=False))


def test_registration_refuses_a_judge_whose_own_id_differs_from_its_registry_name():
    registry = JudgeRegistry("judge")
    with pytest.raises(JudgeError, match="one identity"):
        registry.register("declared-name", _Judge("other-name"))


def test_registration_refuses_a_non_callable_and_an_unidentified_entry():
    registry = JudgeRegistry("judge")
    with pytest.raises(JudgeError, match="must be callable"):
        registry.register("plain", object())

    class _NoVersion:
        id = "no-version"
        criticism_only = True

        def __call__(self, draft, material, state):  # pragma: no cover - never called
            raise AssertionError

    with pytest.raises(JudgeError, match="version"):
        registry.register("no-version", _NoVersion())


def test_assert_judge_accepts_a_conforming_judge():
    judge = _Judge("ok-judge")
    assert assert_judge(judge, name="ok-judge") is judge
    assert isinstance(judge, Judge)


# ---------------------------------------------------------------------------
# 3. The verdict type structurally cannot carry a proposed revision.
# ---------------------------------------------------------------------------


def test_the_shipped_verdict_types_are_proven_criticism_only():
    assert assert_criticism_only(JudgeFlag) is JudgeFlag
    assert assert_criticism_only(JudgeVerdict, proven=(JudgeFlag,)) is JudgeVerdict


def test_a_verdict_type_with_a_mapping_field_is_refused():
    @dataclass(frozen=True)
    class _Leaky:
        BOUNDED_TEXT_FIELDS = ("judge_id",)

        judge_id: str
        replacement: Mapping[str, object]

    with pytest.raises(JudgeError, match="proposed revision"):
        assert_criticism_only(_Leaky)


def test_a_verdict_type_with_an_undeclared_text_field_is_refused():
    @dataclass(frozen=True)
    class _Leaky:
        BOUNDED_TEXT_FIELDS = ("judge_id",)

        judge_id: str
        rewritten_answer: str

    with pytest.raises(JudgeError, match="BOUNDED_TEXT_FIELDS"):
        assert_criticism_only(_Leaky)


def test_a_verdict_type_with_a_tuple_of_undeclared_text_is_refused():
    @dataclass(frozen=True)
    class _Leaky:
        BOUNDED_TEXT_FIELDS = ("judge_id",)

        judge_id: str
        rewritten_lines: tuple[str, ...]

    with pytest.raises(JudgeError, match="BOUNDED_TEXT_FIELDS"):
        assert_criticism_only(_Leaky)


def test_a_verdict_type_of_scalars_and_proven_nested_types_is_accepted():
    @dataclass(frozen=True)
    class _Fine:
        BOUNDED_TEXT_FIELDS = ("judge_id",)

        judge_id: str
        score: float | None
        flags: tuple[JudgeFlag, ...]
        count: int

    assert assert_criticism_only(_Fine, proven=(JudgeFlag,)) is _Fine


# ---------------------------------------------------------------------------
# 4. Verdict validation: every text field capped at one reason's length.
# ---------------------------------------------------------------------------


def test_verdict_round_trips_to_json_with_span_and_field_references():
    verdict = JudgeVerdict(
        judge_id="j",
        version="v1",
        score=0.25,
        flags=(
            JudgeFlag(
                code="illegal_label",
                severity="block",
                reason="scenario/action pair is outside the legal inventory",
                field_ref="intent.action",
                span=(3, 5),
            ),
        ),
        reasons=("one row, one remark",),
    ).validate()
    assert verdict.flagged is True
    assert verdict.as_json() == {
        "judge_id": "j",
        "version": "v1",
        "score": 0.25,
        "flags": [
            {
                "code": "illegal_label",
                "severity": "block",
                "reason": "scenario/action pair is outside the legal inventory",
                "field_ref": "intent.action",
                "span": [3, 5],
            }
        ],
        "reasons": ["one row, one remark"],
    }


@pytest.mark.parametrize(
    "verdict",
    [
        JudgeVerdict(judge_id="x" * (MAX_JUDGE_TEXT_CHARS + 1), version="v1"),
        JudgeVerdict(judge_id="j", version="v" * (MAX_JUDGE_TEXT_CHARS + 1)),
        JudgeVerdict(judge_id="j", version="v1", reasons=("r" * (MAX_JUDGE_TEXT_CHARS + 1),)),
        JudgeVerdict(
            judge_id="j",
            version="v1",
            flags=(
                JudgeFlag(
                    code="c",
                    severity="warn",
                    reason="r" * (MAX_JUDGE_TEXT_CHARS + 1),
                ),
            ),
        ),
    ],
)
def test_no_verdict_field_may_carry_text_longer_than_a_reason(verdict):
    with pytest.raises(JudgeError, match="cap"):
        verdict.validate()


def test_verdict_refuses_an_unknown_severity_and_an_out_of_range_score():
    with pytest.raises(JudgeError, match="severity"):
        JudgeFlag(code="c", severity="fatal", reason="r").validate()
    assert set(JUDGE_FLAG_SEVERITIES) == {"info", "warn", "block"}
    with pytest.raises(JudgeError, match=r"\[0, 1\]"):
        JudgeVerdict(judge_id="j", version="v1", score=1.5).validate()


def test_verdict_refuses_a_malformed_span():
    for span in ((5, 5), (-1, 2), (1,), (1, 2, 3)):
        with pytest.raises(JudgeError, match="span"):
            JudgeFlag(code="c", severity="warn", reason="r", span=span).validate()


def test_a_judge_returning_a_verdict_says_nothing_that_could_replace_the_draft():
    verdict = _Judge("j")("the draft", {}, {})
    payload = verdict.as_json()
    assert "the draft" not in repr(payload)
    assert set(payload) == {"judge_id", "version", "score", "flags", "reasons"}
