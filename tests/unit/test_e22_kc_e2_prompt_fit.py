"""The KC-E2 prompt-fit script's measurement halves, driven with a FAKE
tokenizer client and a synthetic corpus.

The script itself touches the resident server, which is the flight agent's step.
What is tested here is everything that decides a number: the token counter's
envelope subtraction, the symmetric pad plan it builds, the verify-then-reselect
rule for the committed pairing, and the fit arithmetic.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "e22_kc_e2_prompt_fit.py"

HEADER = (
    "File ID,Ticker Symbol,Country by Ticker,UN Defined,Major Dialect Family,"
    "Language Family + Area Based,File Length (seconds),Sampling Rate (Hz)"
)
ROWS = (
    "4453225,APNHF,South Africa,Sub-Saharan Africa,Other,English,4307,16000",
    "4474506,COST,United States,Europe and Northern America,North American,English,3975,24000",
    "4479944,HDB,India,Central and Southern Asia,Other,Asian,3892,44100",
    "4481952,CAHPF,Australia,Oceania,Oceanic,English,3710,24000",
)
TABLE = HEADER + "\n" + "\n".join(ROWS) + "\n"


def _load():
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    if str(ROOT / "src") not in os.environ.get("PYTHONPATH", "").split(":"):
        pytest.skip("PYTHONPATH must contain the checkout's src for this script's guard")
    spec = importlib.util.spec_from_file_location("e22_kc_e2_prompt_fit", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _FakeClient:
    """``/apply-template`` wraps the system text in a fixed template envelope and
    ``/tokenize`` counts whitespace words, so a brief's measured cost is its own
    word count plus a constant -- exactly the shape the real routes have, and the
    shape the counter's envelope subtraction has to cancel."""

    ENVELOPE = "<|im_start|>system X Y Z <|im_end|>"

    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def request_json(self, method, path, body):
        self.calls.append((path, body))
        if path == "/apply-template":
            messages = body["messages"]
            text = " ".join(str(message["content"]) for message in messages)
            return {"prompt": f"{self.ENVELOPE} {text}"}
        if path == "/tokenize":
            return {"tokens": list(range(len(str(body["content"]).split())))}
        raise AssertionError(path)


def _inputs(module, calls):
    _, rows = module.metadata_header_and_rows(TABLE)
    slices = {call: module.call_source_slice(TABLE, call) for call in rows}
    return {
        "calls": list(calls),
        "clip_call": {f"{calls[0]}-1": calls[0]},
        "metadata_relpath": module.METADATA_RELPATH,
        "metadata_sha256": "0" * 64,
        "slices": slices,
        "briefs": {call: module.render_brief(text) for call, text in slices.items()},
        "terms": {call: module.brief_terms(text) for call, text in slices.items()},
        "table_rows": sorted(rows),
    }


def test_the_counter_cancels_the_templates_own_envelope():
    module = _load()
    counts = {"POST /apply-template": 0, "POST /tokenize": 0}
    counter = module.TemplateTokenCounter(_FakeClient(), counts)
    assert counter.envelope_tokens == len(_FakeClient.ENVELOPE.split())
    assert counter("one two three") == 3
    # Cached: a repeated text costs no further route calls.
    before = counts["POST /tokenize"]
    assert counter("one two three") == 3
    assert counts["POST /tokenize"] == before


def test_the_pad_plan_matches_every_pair_and_carries_both_roles():
    module = _load()
    counter = module.TemplateTokenCounter(_FakeClient(), {"POST /apply-template": 0, "POST /tokenize": 0})
    inputs = _inputs(module, ("4453225", "4481952"))
    plan, partners, reselected = module.build_pad_plan(
        inputs, counter, committed_derangement=None, measured_on={"route": "fake"}
    )
    assert reselected is True
    assert plan["schema"] == module.PAD_PLAN_SCHEMA
    assert {entry["role"] for entry in plan["entries"]} == {"arm", "twin"}
    assert len(plan["entries"]) == 2 * len(inputs["calls"])
    # Every pair measures equal after padding, and no twin is its own arm.
    for row in plan["per_call"]:
        assert row["matched_tokens"] >= row["arm_tokens_unpadded"]
        assert row["matched_tokens"] >= row["twin_tokens_unpadded"]
        assert row["fields_distinct"] is True
        assert row["twin_call"] != row["roster_call"]
    assert set(partners.values()).isdisjoint(set(inputs["calls"]))


def test_a_committed_pairing_that_still_holds_is_kept_rather_than_re_selected():
    module = _load()
    counter = module.TemplateTokenCounter(_FakeClient(), {"POST /apply-template": 0, "POST /tokenize": 0})
    inputs = _inputs(module, ("4453225",))
    _, partners, first = module.build_pad_plan(
        inputs, counter, committed_derangement=None, measured_on={}
    )
    assert first is True
    _, kept, second = module.build_pad_plan(
        inputs, counter, committed_derangement=partners, measured_on={}
    )
    assert second is False
    assert kept == partners


def test_a_committed_pairing_that_fails_is_re_selected_and_says_so():
    module = _load()
    counter = module.TemplateTokenCounter(_FakeClient(), {"POST /apply-template": 0, "POST /tokenize": 0})
    inputs = _inputs(module, ("4453225",))
    # A pairing naming a call with a different line count can never be padded.
    inputs["briefs"]["bogus"] = "one line"
    inputs["slices"]["bogus"] = TABLE
    inputs["terms"]["bogus"] = dict(inputs["terms"]["4474506"])
    _, partners, reselected = module.build_pad_plan(
        inputs, counter, committed_derangement={"4453225": "bogus"}, measured_on={}
    )
    assert reselected is True
    assert partners["4453225"] != "bogus"


def test_the_fit_rule_is_the_repositorys_own():
    module = _load()
    geometry = {"slots": 8, "slot_tokens": 5120, "max_tokens": 1024}
    block = module.fit_block(geometry=geometry, worst_text_tokens=200, longest_seconds=34.88)
    # 13 * ceil(34.88) = 455 speech tokens.
    assert block["worst_speech_tokens"] == 455
    assert block["worst_required_tokens"] == 455 + 200 + 1024 + 2
    assert block["fits_strictly"] is True
    assert block["satisfies_margin_rule"] is True
    tight = module.fit_block(geometry=geometry, worst_text_tokens=2000, longest_seconds=34.88)
    assert tight["fits_strictly"] is True
    assert tight["satisfies_margin_rule"] is False


def test_speech_tokens_round_up_to_whole_seconds():
    module = _load()
    assert module.speech_tokens(1.0) == 13
    assert module.speech_tokens(1.0001) == 26
    assert module.speech_tokens(34.88) == 455
