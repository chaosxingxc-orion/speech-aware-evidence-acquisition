"""E11 (2026-09-18, owner directive 26): the delivery-time normaliser node.

Model-free and offline: no model, tokenizer, encoder, tool, server or network
contact, and no run directory is read or written. Every fixture here is
synthetic and the real TRAIN-mined legal intent inventory is replaced by a
three-scenario one, so nothing in this module needs ``SPEECHRL_DATA_DIR``.

Four layers, kept apart on purpose:

1. WHY IT IS NOT A JUDGE -- owner Decision 11-C makes every
   ``core.base.JUDGES`` entry criticism-only, which a node that rewrites the
   delivered answer can never be; the node is the same seam
   ``COMMIT_POLICIES`` is, and its registry checks that at the door;
2. the RULE -- one implementation shared with the v3 scorer
   (``rails.slurp_projection_v3``), idempotent, a byte-identical no-op on an
   already-normal answer, and a pass-through on an answer the parser refuses;
3. the SWITCH -- one ``episode``-class key whose OFF arm is its absence, and
   whose loader refuses an unregistered rule, the wrong carrier, the second
   spelling of the same rule, and the grouped-Solver combination whose
   custody nobody has designed;
4. the OFFLINE REPLAY -- the same rule re-applied to sealed bytes, so an
   arm's projected numbers can be re-derived without contact.
"""

from __future__ import annotations

import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.analysis.deliver_normaliser_replay import (
    DeliverNormaliserReplayError,
    replay,
    replay_row,
)
from speech_aware_evidence_acquisition.core.base import (
    DELIVERY_NORMALISERS,
    JUDGES,
    DeliveryNormalisation,
    DeliveryNormaliserError,
    JudgeError,
    assert_delivery_normaliser,
)

# Importing rails.delivery_normalisers is what POPULATES
# core.base.DELIVERY_NORMALISERS.
from speech_aware_evidence_acquisition.rails import (  # noqa: F401
    delivery_normalisers as _delivery_normalisers,
)
from speech_aware_evidence_acquisition.rails import slurp_projection_v3 as v3
from speech_aware_evidence_acquisition.rails.config_tables import (
    EPISODE_LEVEL_SWITCH_KEYS,
    ConfigTableError,
    is_episode_null_arm,
    resolve_episode_switch_key,
)
from speech_aware_evidence_acquisition.rails.delivery_normalisers import (
    DELIVER_NORMALISE_V3,
    DELIVER_NORMALISER_RECEIPT_SCHEMA,
)
from speech_aware_evidence_acquisition.rails.native_episode_config import (
    load_native_episode_config,
)
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (
    SlotEntity,
    legal_intent_inventory,
    parse_slu_response,
)

from test_native_episode_config import config as _episode_values, program as _program

SWITCH_KEY = "native_episode.deliver_normaliser"
ARM = {"normaliser": DELIVER_NORMALISE_V3}

#: A three-scenario stand-in for the real 60-id TRAIN inventory. ``music``
#: has no ``play_music`` action, but ``play_music`` IS the legal composed id
#: of ``(play, music)`` -- the A1 audit's own ``R_action`` headroom class.
INVENTORY = legal_intent_inventory(
    {
        "music": ("likeness", "dislikeness", "play", "query", "settings"),
        "play": ("audiobook", "game", "music", "podcasts", "radio"),
        "alarm": ("set", "remove", "query"),
    }
)


@pytest.fixture(autouse=True)
def _synthetic_inventory(monkeypatch):
    """Every call in this module uses the synthetic inventory, so no test
    here reads the data root."""

    monkeypatch.setattr(
        v3, "_default_legal_intent_inventory", lambda: INVENTORY
    )


def _answer(scenario, action, entities=()):
    return json.dumps(
        {
            "scenario": scenario,
            "action": action,
            "entities": [{"type": kind, "filler": filler} for kind, filler in entities],
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def _normaliser():
    return DELIVERY_NORMALISERS.resolve(DELIVER_NORMALISE_V3)


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# 1. Why this is not a judge, and what its own registry checks.
# ---------------------------------------------------------------------------


def test_the_node_is_registered_with_its_identity_and_carrier():
    entry = _normaliser()
    assert entry.id == DELIVER_NORMALISE_V3 == "saea-deliver-normalise-v3"
    assert entry.version
    assert entry.carrier_lock_key == "slurp"
    assert DELIVER_NORMALISE_V3 in DELIVERY_NORMALISERS.names()


def test_the_judge_registry_refuses_a_rewriting_entry():
    """Owner Decision 11-C, restated as an executable fact: the Reviewer seat
    is criticism-only, so a node that REWRITES the delivered answer cannot
    live in ``core.base.JUDGES``. This is why E11 registers a sibling
    registry rather than a ``judges`` table entry."""

    class _RewritingJudge:
        id = "saea-deliver-normalise-v3-as-a-judge"
        version = "1"

        def __call__(self, draft, material, state):  # pragma: no cover - never run
            return draft

    with pytest.raises(JudgeError, match="criticism_only"):
        JUDGES.register(_RewritingJudge.id, _RewritingJudge())
    assert _RewritingJudge.id not in JUDGES.names()


@pytest.mark.parametrize(
    "entry, expected",
    (
        (object(), "callable"),
        (lambda text: text, "must be non-empty text"),
    ),
)
def test_registration_refuses_an_entry_without_identity(entry, expected):
    with pytest.raises(DeliveryNormaliserError, match=expected):
        assert_delivery_normaliser(entry, name="whatever")


def test_registration_refuses_a_name_the_entry_does_not_claim():
    with pytest.raises(DeliveryNormaliserError, match="one identity"):
        assert_delivery_normaliser(_normaliser(), name="some-other-id")


def test_a_result_must_carry_its_receipt():
    with pytest.raises(DeliveryNormaliserError, match="non-empty mapping"):
        DeliveryNormalisation(text="x", changed=False, receipt={}).validate()


# ---------------------------------------------------------------------------
# 2. The rule: one implementation, shared with the v3 scorer.
# ---------------------------------------------------------------------------


def test_the_node_calls_the_same_functions_the_v3_scorer_applies(monkeypatch):
    """Not a second implementation: the node's whole rule is
    ``rails.slurp_projection_v3.apply_slurp_projection_v3_delivery``, which is
    the pair of functions the v3 scorer applies between the parse and the
    official prediction file. Proven by intercepting that one function."""

    seen = {}
    real = v3.apply_slurp_projection_v3_delivery

    def spy(text, *, carrier_lock_key, inventory=None):
        seen["carrier"] = carrier_lock_key
        return real(text, carrier_lock_key=carrier_lock_key, inventory=inventory)

    monkeypatch.setattr(v3, "apply_slurp_projection_v3_delivery", spy)
    _normaliser()(_answer("alarm", "set"))
    assert seen == {"carrier": "slurp"}


def test_r_action_repairs_the_label_at_delivery():
    """A1's own headroom class: the delivered pair (music, play_music) is
    illegal, but ``play_music`` is itself the legal composed id of
    (play, music)."""

    outcome = _normaliser()(_answer("music", "play_music"))
    scenario, action, _entities, parsed = parse_slu_response(outcome.text)
    assert parsed is True
    assert (scenario, action) == ("play", "music")
    assert outcome.changed is True
    assert outcome.receipt["labels_changed"] == 1
    assert outcome.receipt["label_branch"] == "r-action"
    assert outcome.receipt["fillers_changed"] == 0


@pytest.mark.parametrize(
    "raw_filler, normalised",
    (
        # rung 0: case and whitespace (three quarters of P2's official gain)
        ("Six  AM", "six am"),
        # rung 1: punctuation, apostrophes and internal hyphens kept
        ("o'clock, please", "o'clock please"),
        # rung 2: meridiem forms
        ("6 a.m.", "six am"),
        # rung 3: numeric tokens to English words
        ("6:30am", "six thirty am"),
        ("25%", "twenty five percent"),
        ("3rd", "third"),
    ),
)
def test_the_filler_rungs_the_a1_audit_lists(raw_filler, normalised):
    outcome = _normaliser()(_answer("alarm", "set", (("time", raw_filler),)))
    _scenario, _action, entities, _parsed = parse_slu_response(outcome.text)
    assert list(entities) == [SlotEntity(type="time", filler=normalised)]
    assert outcome.receipt["fillers_changed"] == 1
    assert outcome.receipt["labels_changed"] == 0


def test_no_support_filter_is_applied():
    """A1 REJECTED P1a/P1b: v3 drops no entity, whatever its type."""

    raw = _answer("alarm", "set", (("time", "six am"), ("date", "monday")))
    outcome = _normaliser()(raw)
    _scenario, _action, entities, _parsed = parse_slu_response(outcome.text)
    assert len(entities) == 2


def test_an_already_normal_answer_is_a_byte_identical_no_op():
    raw = _answer("alarm", "set", (("time", "six am"),))
    outcome = _normaliser()(raw)
    assert outcome.text == raw
    assert outcome.changed is False
    assert outcome.receipt["applied"] is True
    assert outcome.receipt["labels_changed"] == 0
    assert outcome.receipt["fillers_changed"] == 0


@pytest.mark.parametrize(
    "raw",
    (
        _answer("music", "play_music", (("time", "6:30AM"), ("date", "Monday"))),
        _answer("alarm", "set", (("time", "six am"),)),
        _answer("play", "music"),
    ),
)
def test_the_node_is_idempotent(raw):
    once = _normaliser()(raw)
    twice = _normaliser()(once.text)
    assert twice.text == once.text
    assert twice.changed is False


def test_an_unparsed_answer_is_delivered_unchanged_with_a_recorded_reason():
    raw = "the model said something that is not a SLURP answer"
    outcome = _normaliser()(raw)
    assert outcome.text == raw
    assert outcome.changed is False
    assert outcome.receipt["applied"] is False
    assert outcome.receipt["reason"] == "unparsed"
    assert outcome.receipt["labels_changed"] == 0
    assert outcome.receipt["fillers_changed"] == 0


def test_the_receipt_binds_its_own_input_and_output_and_names_the_rule():
    raw = _answer("music", "play_music", (("time", "6:30AM"),))
    outcome = _normaliser()(raw)
    receipt = outcome.receipt
    assert receipt["schema"] == DELIVER_NORMALISER_RECEIPT_SCHEMA
    assert receipt["normaliser_id"] == DELIVER_NORMALISE_V3
    assert receipt["rule_id"] == "slurp-use-projection-v3"
    assert receipt["carrier_lock_key"] == "slurp"
    assert receipt["input_sha256"] == _sha(raw)
    assert receipt["output_sha256"] == _sha(outcome.text)
    # A receipt names counts and digests, never the answer text: a delivered
    # SLURP answer carries slot fillers taken from speech.
    assert not any(isinstance(value, str) and "{" in value for value in receipt.values())


def test_a_semantically_unchanged_answer_is_delivered_verbatim():
    """ONE FACTOR, DOWN TO THE BYTE. The underlying transform always
    re-renders the answer it parsed, so a row the rule does not repair would
    still come back with different bytes -- the model's own JSON spacing and
    key order replaced by the canonical rendering (1,076 of 1,080 rows on the
    sealed B1 arm, against 24 repaired labels and 82 repaired fillers). The
    NODE suppresses that: nothing repaired means the accepted answer is
    delivered verbatim, so an ON arm differs from its comparator exactly on
    the rows the rule repairs."""

    # Semantically already normal, but rendered the way a model writes it:
    # unsorted keys and non-canonical spacing.
    raw = '{"scenario":"alarm","action":"set","entities":[{"filler":"six am","type":"time"}]}'
    canonical = _answer("alarm", "set", (("time", "six am"),))
    assert raw != canonical

    outcome = _normaliser()(raw)
    assert outcome.text == raw
    assert outcome.changed is False
    assert outcome.receipt["rendering_suppressed"] is True
    assert outcome.receipt["labels_changed"] == 0
    assert outcome.receipt["fillers_changed"] == 0
    assert outcome.receipt["output_sha256"] == _sha(raw)

    # ...and the scored triple is the canonical one either way, which is why
    # suppressing the re-render costs the official number nothing.
    assert parse_slu_response(raw)[:3] == parse_slu_response(canonical)[:3]


def test_a_repaired_answer_is_re_rendered_canonically():
    raw = '{"scenario":"music","action":"play_music","entities":[]}'
    outcome = _normaliser()(raw)
    assert outcome.changed is True
    assert outcome.receipt["rendering_suppressed"] is False
    assert outcome.text == _answer("play", "music")


# ---------------------------------------------------------------------------
# 3. The switch: one episode-class key, validated fail-closed before contact.
# ---------------------------------------------------------------------------


def test_the_switch_key_is_on_the_closed_episode_allowlist():
    assert SWITCH_KEY in EPISODE_LEVEL_SWITCH_KEYS
    assert resolve_episode_switch_key(SWITCH_KEY) == SWITCH_KEY
    with pytest.raises(ConfigTableError, match="not admitted"):
        resolve_episode_switch_key("native_episode.deliver_normalizer")


def test_the_off_arm_is_the_key_absent():
    assert is_episode_null_arm(SWITCH_KEY, None) is True
    assert is_episode_null_arm(SWITCH_KEY, ARM) is False


def _values(**extra):
    values = _episode_values()
    values["carrier_lock_key"] = "slurp"
    values.update(extra)
    return values


def test_the_loader_accepts_the_armed_node_and_leaves_the_off_arm_none():
    off = load_native_episode_config(_values(), _program())
    assert off.deliver_normaliser_id is None

    values = _values()
    values["native_episode"]["deliver_normaliser"] = dict(ARM)
    on = load_native_episode_config(values, _program())
    assert on.deliver_normaliser_id == DELIVER_NORMALISE_V3
    # The node makes no contact, so the ceiling is untouched.
    assert on.max_contacts == off.max_contacts


@pytest.mark.parametrize(
    "block, expected",
    (
        ({"normaliser": "no-such-rule"}, "is invalid"),
        ({"normaliser": ""}, "non-empty string"),
        ({"normalizer": DELIVER_NORMALISE_V3}, "exactly"),
        ({"normaliser": DELIVER_NORMALISE_V3, "extra": 1}, "exactly"),
        (DELIVER_NORMALISE_V3, "exactly"),
        (None, "exactly"),
    ),
)
def test_the_loader_refuses_a_malformed_or_unregistered_declaration(block, expected):
    values = _values()
    values["native_episode"]["deliver_normaliser"] = block
    with pytest.raises(ValueError, match=expected):
        load_native_episode_config(values, _program())


def test_the_loader_refuses_the_wrong_carrier():
    values = _values(carrier_lock_key="earnings21-original")
    values["native_episode"]["deliver_normaliser"] = dict(ARM)
    with pytest.raises(ValueError, match="is defined for carrier"):
        load_native_episode_config(values, _program())


def test_the_loader_refuses_the_second_spelling_of_the_same_rule():
    """The E4 run-level key applies the SAME projection at the seal, outside
    the agent. Two spellings of one rule is how a cell ends up with two
    identities."""

    values = _values(slurp_projection_v3_delivery=1)
    values["native_episode"]["deliver_normaliser"] = dict(ARM)
    with pytest.raises(ValueError, match="declare exactly one of them"):
        load_native_episode_config(values, _program())


def test_the_loader_refuses_the_grouped_solver_combination():
    """A grouped row's delivered text is already the COMMIT policy's aggregate
    (E2d/I7g). Normalising on top of it would make the delivered bytes a
    function of two rules with only one of them in custody."""

    values = _values()
    values["native_episode"]["deliver_normaliser"] = dict(ARM)
    values["native_episode"]["roles"]["solver"].update(
        samples=2,
        decoding_overrides={"temperature": 0.7, "seed_offset": 0},
        commit={
            "policy": "saea-commit-plurality-support-v1",
            "min_support": 2,
            "similarity_threshold": 0.8,
        },
    )
    with pytest.raises(ValueError, match="grouped"):
        load_native_episode_config(values, _program(ceiling=5))


# ---------------------------------------------------------------------------
# 4. The offline replay: the same rule over sealed bytes, zero contact.
# ---------------------------------------------------------------------------


def _sealed(tmp_path, rows):
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "outputs.jsonl"
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path


def test_replay_reapplies_the_rule_to_a_sealed_arm(tmp_path):
    raw = _answer("music", "play_music", (("time", "6:30AM"),))
    already = _answer("alarm", "set", (("time", "six am"),))
    outputs = _sealed(
        tmp_path / "sealed",
        [
            {"sample_id": "slurp:train:1", "text": raw},
            {"sample_id": "slurp:train:2", "text": already},
            {"sample_id": "slurp:train:3", "text": "not an answer"},
        ],
    )
    before = outputs.read_bytes()
    provenance = replay(
        outputs_path=outputs,
        normaliser_id=DELIVER_NORMALISE_V3,
        output_dir=tmp_path / "replay",
    )
    # The sealed input is never opened for writing.
    assert outputs.read_bytes() == before
    assert provenance["model_calls"] == 0
    assert provenance["rows"] == 3
    assert provenance["rows_changed"] == 1
    assert provenance["rows_label_changed"] == 1
    assert provenance["rows_unparsed"] == 1
    assert provenance["rows_already_normalised"] == 0

    replayed = [
        json.loads(line)
        for line in (tmp_path / "replay" / "outputs.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert [row["sample_id"] for row in replayed] == [
        "slurp:train:1",
        "slurp:train:2",
        "slurp:train:3",
    ]
    assert replayed[1]["text"] == already
    assert replayed[2]["text"] == "not an answer"
    # A replayed file is directly scoreable: it carries sample_id and text.
    scenario, action, _entities, _parsed = parse_slu_response(replayed[0]["text"])
    assert (scenario, action) == ("play", "music")


def test_replay_refuses_to_overwrite_an_existing_replay(tmp_path):
    outputs = _sealed(tmp_path / "sealed", [{"sample_id": "s", "text": "x"}])
    target = tmp_path / "replay"
    replay(
        outputs_path=outputs, normaliser_id=DELIVER_NORMALISE_V3, output_dir=target
    )
    with pytest.raises(DeliverNormaliserReplayError, match="refusing to overwrite"):
        replay(
            outputs_path=outputs, normaliser_id=DELIVER_NORMALISE_V3, output_dir=target
        )


def test_replay_of_an_already_normalised_row_is_a_no_op_and_says_so():
    """The idempotence witness: replaying an ON-arm row changes nothing, and
    the row is flagged as already normalised."""

    text = _answer("play", "music", (("time", "six thirty am"),))
    row = {
        "sample_id": "slurp:train:1",
        "text": text,
        "native_episode_receipt": {
            "deliver_normaliser": {
                "normaliser_id": DELIVER_NORMALISE_V3,
                "input_sha256": _sha("whatever the raw answer was"),
                "output_sha256": _sha(text),
            }
        },
    }
    replayed = replay_row(row, normaliser=_normaliser())
    assert replayed["text"] == text
    assert replayed["changed"] is False
    assert replayed["already_normalised"] is True


def test_replay_can_be_given_the_source_text_explicitly():
    """What the bundle verifier does: re-apply the rule to the trace's own
    recorded response bytes rather than to the row's delivered text."""

    raw = _answer("music", "play_music")
    row = {"sample_id": "s", "text": _answer("play", "music")}
    replayed = replay_row(row, normaliser=_normaliser(), source_text=raw)
    assert replayed["text"] == row["text"]
    assert replayed["source_text_sha256"] == _sha(raw)
