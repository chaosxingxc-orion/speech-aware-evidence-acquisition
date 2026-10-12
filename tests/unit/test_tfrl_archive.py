"""E-T4: archive, parent choice, ruled selection, curve, proposer-side meta summary."""

from __future__ import annotations

import copy
import hashlib
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis.sealed_credit import archive as ar
from speech_aware_evidence_acquisition.analysis.sealed_credit import meta_summary as ms
from speech_aware_evidence_acquisition.analysis.sealed_credit import parent_choice as pc
from speech_aware_evidence_acquisition.analysis.sealed_credit import selection as sel

def H(tag):
    return hashlib.sha256(tag.encode("ascii")).hexdigest()


def ci(point, lo=None, hi=None):
    return {"point": point, "lo": point - 1.0 if lo is None else lo, "hi": point + 1.0 if hi is None else hi}


def credit(slu=2.0, slu_lo=0.5, intent=0.5, intent_lo=-0.2, vs_twin=None, vs_parent=None):
    return {
        "slu_f1": 66.0, "intent": 83.0,
        "vs_lock": {"slu": ci(slu, slu_lo, slu + 1.0), "intent": ci(intent, intent_lo, intent + 1.0)},
        "vs_twin": vs_twin, "vs_parent": vs_parent,
        "per_scenario": {"alarm": {"slu": 1.0, "intent": 0.0}},
        "false_fill": {"n": 10, "delta_pp": -0.5}, "non_empty_exact": {"n": 90, "delta_pp": 1.0},
        "contacts_per_row": 5.0,
    }


def state(tag, parent=None, iteration=1, cls="knowledge", verdict="accepted", cr=None, arm="typed", pred=None):
    kwargs = dict(
        artefact_hashes={"exemplar_index_release": H(tag)}, parent_id=parent, iteration=iteration,
        operator_class=None if iteration == 0 else cls, candidate_id=None if iteration == 0 else f"cand-{tag}",
        verdict=verdict, arm=arm, predicted_slu_pp=pred,
    )
    if verdict != "unflown":
        kwargs.update(credit=cr or credit(), run_id=f"run-{tag}", attempt=1)
    return ar.build_state(**kwargs)


def root():
    return ar.build_state(
        artefact_hashes={"exemplar_index_release": H("0")}, parent_id=None, iteration=0,
        operator_class=None, candidate_id=None, verdict="accepted", credit=credit(0.0, 0.0, 0.0, 0.0),
        run_id="lock", attempt=1,
    )


# ---- archive -------------------------------------------------------------------------------

def test_state_id_is_deterministic_and_order_free():
    a = ar.compute_state_id({"key_view": H("a"), "slot_store_release": H("b")})
    b = ar.compute_state_id({"slot_store_release": H("b"), "key_view": H("a")})
    assert a == b and len(a) == 64
    assert a != ar.compute_state_id({"key_view": H("b"), "slot_store_release": H("a")})


def test_state_id_rejects_unknown_artefact_and_bad_hash():
    with pytest.raises(ar.ArchiveError):
        ar.compute_state_id({"prompt_template": H("a")})
    with pytest.raises(ar.ArchiveError):
        ar.compute_state_id({"key_view": "xyz"})


def test_archive_is_write_once(tmp_path):
    arch = ar.Archive(tmp_path / "arch")
    r = root()
    path = arch.put(r)
    assert path.exists()
    with pytest.raises(ar.ArchiveError, match="already archived"):
        arch.put(r)
    assert arch.get(r["state_id"]) == r


def test_archive_stores_refused_and_requires_parent(tmp_path):
    arch = ar.Archive(tmp_path)
    r = root()
    arch.put(r)
    child = state("1", parent=r["state_id"], verdict="refused")
    arch.put(child)
    assert [c["state_id"] for c in arch.children(r["state_id"])] == [child["state_id"]]
    orphan = state("2", parent=H("f"))
    with pytest.raises(ar.ArchiveError, match="not in the archive"):
        arch.put(orphan)


def test_archive_refuses_text_bearing_content():
    bad = copy.deepcopy(credit())
    bad["utterance_text"] = "x"
    with pytest.raises(ar.ArchiveError):
        ar.validate_credit(bad)
    with pytest.raises(ar.ArchiveError):
        ar.assert_no_text_fields({"a": {"transcript": 1}})
    with pytest.raises(ar.ArchiveError):
        ar.assert_no_text_fields({"candidate": "turn the lights on please"})


def test_build_state_clause_checks():
    with pytest.raises(ar.ArchiveError):
        ar.build_state(artefact_hashes={"key_view": H("a")}, parent_id=None, iteration=1,
                       operator_class="k", candidate_id="c", verdict="refused")  # no credit
    with pytest.raises(ar.ArchiveError):
        ar.build_state(artefact_hashes={"key_view": H("a")}, parent_id=None, iteration=1,
                       operator_class="k", candidate_id="c", verdict="unflown", credit=credit(),
                       run_id="r", attempt=1)


# ---- parent choice -------------------------------------------------------------------------

def test_edit_budget_schedule():
    assert [pc.edit_budget(t) for t in (1, 2, 3)] == [2, 1, 1]
    with pytest.raises(ValueError):
        pc.edit_budget(0)


def test_parent_prefers_best_lower_bound():
    r = root()
    a = state("a", r["state_id"], cr=credit(2.0, 0.6))
    b = state("b", r["state_id"], cr=credit(3.0, 1.2))
    out = pc.choose_parent([r, a, b])
    # root: 0 - 0.25*2 = -0.5 ; a: 0.6 ; b: 1.2
    assert out["parent_id"] == b["state_id"]


def test_parent_child_penalty_flips_choice():
    r = root()
    a = state("a", r["state_id"], cr=credit(2.0, 1.0))
    b = state("b", r["state_id"], cr=credit(2.0, 0.9))
    kids = [state(f"k{i}", a["state_id"], iteration=2, verdict="refused") for i in range(3)]
    out = pc.choose_parent([r, a, b, *kids])
    # a: 1.0 - 0.75 = 0.25 ; b: 0.9
    assert out["parent_id"] == b["state_id"]
    assert pc.choose_parent([r, a, b])["parent_id"] == a["state_id"]


def test_unflown_children_carry_no_penalty():
    r = root()
    a = state("a", r["state_id"], cr=credit(2.0, 1.0))
    u = state("u", a["state_id"], iteration=2, verdict="unflown")
    out = pc.choose_parent([r, a, u])
    assert out["parent_id"] == a["state_id"]
    assert out["ranking"][0]["n_children"] == 0


def test_class_masking_after_two_refused_same_class():
    r = root()
    s = [state("x1", r["state_id"], cls="delivery", verdict="refused"),
         state("x2", r["state_id"], cls="delivery", verdict="refused"),
         state("x3", r["state_id"], cls="scope", verdict="refused")]
    out = pc.choose_parent([r, *s])
    assert out["parent_id"] == r["state_id"]
    assert out["masked_classes"] == ["delivery"]
    # one refusal per class under another parent does not mask
    assert pc.masked_classes(s[:1], r["state_id"]) == []


def test_ties_break_by_state_id_and_arm_is_isolated():
    r = root()
    a = state("a", r["state_id"], cr=credit(2.0, 1.0))
    b = state("b", r["state_id"], cr=credit(2.0, 1.0))
    ace = state("c", r["state_id"], cr=credit(9.0, 8.0), arm="ace")
    out = pc.choose_parent([r, ace, a, b])
    assert out["parent_id"] == min(a["state_id"], b["state_id"])
    with pytest.raises(ValueError):
        pc.choose_parent([a], arm="ace")


# ---- selection -----------------------------------------------------------------------------

LOCK = {"role": "lock", "n_rows": 1080}
TWIN = credit(0.4, -0.8)


def verdict(child, twin=TWIN, parent=None, rules=None):
    return sel.select(child, LOCK, twin, parent, rules)


def test_select_accepts_clean_child():
    v = verdict(credit(2.0, 0.5, 0.7, 0.1))
    assert v.accepted and v.status == "accepted" and v.failed == []


def test_select_clause_a_ci_lower_bound():
    v = verdict(credit(2.0, 0.0))
    assert not v.accepted and v.failed == ["a_ci_lb"]


def test_select_clause_b_point_floor():
    v = verdict(credit(1.48, 0.1))
    assert v.failed == ["b_point_floor"]
    assert verdict(credit(1.49, 0.1)).accepted


def test_select_clause_c_twin():
    v = verdict(credit(2.0, 0.5), twin=credit(2.0, 0.5))
    assert v.failed == ["c_beats_twin"]
    v = verdict(credit(2.0, 0.5), twin=credit(2.5, 0.5))
    assert v.failed == ["c_beats_twin"]


def test_select_clause_d_parent_column():
    parent = credit(1.8, 0.4)
    ok = verdict(credit(2.0, 0.5, vs_parent={"slu": ci(0.2), "intent": ci(0.0)}), parent=parent)
    assert ok.accepted
    tie = verdict(credit(2.0, 0.5, vs_parent={"slu": ci(0.0), "intent": ci(0.0)}), parent=parent)
    assert tie.failed == ["d_beats_parent"]
    derived = verdict(credit(2.0, 0.5), parent=credit(2.1, 0.5))
    assert derived.failed == ["d_beats_parent"]
    assert "d_beats_parent" not in verdict(credit(2.0, 0.5)).clauses


def test_select_clause_e_intent_guard():
    assert verdict(credit(2.0, 0.5, intent=0.3, intent_lo=-0.66)).failed == ["e_intent_guard"]
    assert verdict(credit(2.0, 0.5, intent=0.3, intent_lo=-0.65)).accepted
    assert verdict(credit(2.0, 0.5, intent=-0.1, intent_lo=-0.3)).failed == ["e_intent_guard"]


def test_select_lists_every_failure_and_row_mismatch():
    v = verdict(credit(0.5, -0.5, intent=-1.0, intent_lo=-2.0))
    assert set(v.failed) == {"a_ci_lb", "b_point_floor", "e_intent_guard"}
    child = credit(2.0, 0.5)
    child["n_rows"] = 1000
    with pytest.raises(sel.SelectionError):
        sel.select(child, LOCK, TWIN, None)


def test_rules_from_floor_table_reads_decision_190():
    repo = Path(__file__).resolve().parents[2]
    rules = sel.rules_from_floor_table(1080, repo)
    assert rules["slu_floor_pp"] == pytest.approx(1.49, abs=0.01)
    assert rules["intent_guard_pp"] == pytest.approx(0.65, abs=0.01)


def test_stop_rule_is_three_iterations():
    assert [sel.loop_complete(n) for n in (0, 1, 2, 3, 4)] == [False, False, False, True, True]
    assert [sel.next_iteration(n) for n in (0, 2, 3)] == [1, 3, None]


def test_curve_repeats_level_on_refused_iteration():
    r = root()
    a1 = state("a1", r["state_id"], iteration=1, cr=credit(2.0, 0.6))
    ref = state("r2", a1["state_id"], iteration=2, verdict="refused", cr=credit(1.0, -0.3))
    unf = state("u3", a1["state_id"], iteration=3, verdict="unflown")
    pts = sel.curve([r, a1, ref, unf])
    assert [p["iteration"] for p in pts] == [1, 2, 3]
    assert pts[0]["level"]["point"] == 2.0 and pts[0]["marked"] is None
    assert pts[1]["level"] == pts[0]["level"] and pts[1]["marked"] == "refused"
    assert pts[1]["state_id"] == a1["state_id"]
    assert pts[1]["flown_children"][0]["verdict"] == "refused"
    assert pts[2]["level"] == pts[0]["level"] and pts[2]["marked"] == "unflown"


def test_curve_first_iteration_refused_starts_at_zero_and_arm_filter():
    r = root()
    ref = state("r1", r["state_id"], iteration=1, verdict="refused", cr=credit(0.5, -1.0))
    ace = state("c1", r["state_id"], iteration=1, arm="ace", cr=credit(3.0, 1.0))
    pts = sel.curve([r, ref, ace])
    assert pts[0]["level"] == {"point": 0.0, "lo": 0.0, "hi": 0.0} and pts[0]["marked"] == "refused"
    assert sel.curve([r, ref, ace], arm="ace")[0]["level"]["point"] == 3.0


# ---- meta summary --------------------------------------------------------------------------

def test_meta_summary_aggregates_and_is_never_shipped():
    r = root()
    a = state("a", r["state_id"], iteration=1, cls="knowledge", cr=credit(2.0, 0.5), pred=1.6)
    b = state("b", r["state_id"], iteration=1, cls="knowledge", verdict="refused", cr=credit(0.4, -0.5), pred=1.5)
    c = state("c", r["state_id"], iteration=1, cls="delivery", verdict="unflown")
    doc = ms.build_meta_summary([r, a, b, c])
    assert doc["never_shipped"] is True
    rows = {(x["iteration"], x["operator_class"]): x for x in doc["rows"]}
    k = rows[(1, "knowledge")]
    assert (k["n_accepted"], k["n_refused"], k["n_unflown"]) == (1, 1, 0)
    assert k["mean_predicted_slu_pp"] == pytest.approx(1.55)
    assert k["mean_measured_slu_pp"] == pytest.approx(1.2)
    assert k["mean_realised_minus_predicted_pp"] == pytest.approx(-0.35)
    assert rows[(1, "delivery")]["n_unflown"] == 1
    assert "knowledge" in ms.render_for_proposer(doc)


def test_meta_summary_forbidden_keys_and_shipping_refusal():
    r = root()
    doc = ms.build_meta_summary([r, state("a", r["state_id"])])
    for key in ("summary", "transcript", "hypothesis_text", "gold_label", "prompt"):
        bad = copy.deepcopy(doc)
        bad["rows"][0][key] = 1
        with pytest.raises(ms.MetaSummaryError):
            ms.assert_meta_clean(bad)
    bad = copy.deepcopy(doc)
    bad["never_shipped"] = False
    with pytest.raises(ms.MetaSummaryError):
        ms.assert_meta_clean(bad)
    bad = copy.deepcopy(doc)
    bad["rows"][0]["operator_class"] = "free text with spaces"
    with pytest.raises(ms.MetaSummaryError):
        ms.assert_meta_clean(bad)
    with pytest.raises(ms.MetaSummaryError):
        ms.assert_shippable(doc)
    ms.assert_shippable({"table": [1, 2]})


# ---- corrections and unmeasured refusals (2026-10-11) -------------------------------------------


def _ace_state(tag, parent=None, iteration=1):
    return ar.build_state(artefact_hashes={"playbook_release": H(tag)}, parent_id=parent, iteration=iteration,
                          operator_class="playbook", candidate_id=f"ace-i{iteration}", verdict="refused", arm="ace",
                          credit=credit(), run_id="run", attempt=1)


def _correction(state_id, wrong, right):
    return {"schema": ar.CORRECTION_SCHEMA, "state_id": state_id, "artefact": "playbook_release", "slug": "playbook-hash",
            "wrong": wrong, "right": right, "cause": "stale-playbook-file-written-by-superseded-open-cell-run",
            "derives_from": {"receipt": "docs/x/open-cell-receipt.json", "field": "ace.playbook_content_hash",
                             "receipt_sha256": H("receipt")}}


def test_a_correction_is_applied_by_the_readers_and_the_state_file_is_never_edited(tmp_path):
    archive = ar.Archive(tmp_path / "archive")
    s = _ace_state("wrong")
    archive.put(s)
    path = tmp_path / "archive" / f"state-{s['state_id']}.json"
    raw = path.read_bytes()
    record_path = archive.put_correction(_correction(s["state_id"], H("wrong"), H("right")))
    assert record_path.parent.name == "corrections" and path.read_bytes() == raw
    for view in (archive.get(s["state_id"]), archive.states()[0]):
        assert view["state_id"] == s["state_id"] and view["artefact_hashes"] == {"playbook_release": H("right")}
        assert view["corrections"] == [{"artefact": "playbook_release", "wrong": H("wrong"), "right": H("right"), "slug": "playbook-hash"}]
    # a child archived under the uncorrected id still finds its parent
    child = _ace_state("child", parent=s["state_id"], iteration=2)
    archive.put(child)
    assert [x["iteration"] for x in archive.states()] == [1, 2]
    with pytest.raises(ar.ArchiveError, match="write-once"):
        archive.put_correction(_correction(s["state_id"], H("wrong"), H("right")))


def test_a_correction_must_name_the_wrong_value_and_carry_identifiers_only(tmp_path):
    archive = ar.Archive(tmp_path / "archive")
    s = _ace_state("wrong")
    archive.put(s)
    with pytest.raises(ar.ArchiveError, match="does not record the wrong"):
        archive.put_correction(_correction(s["state_id"], H("other"), H("right")))
    bad = _correction(s["state_id"], H("wrong"), H("right"))
    bad["cause"] = "free text with spaces"
    with pytest.raises(ar.ArchiveError, match="free-text"):
        ar.validate_correction(bad)
    same = _correction(s["state_id"], H("wrong"), H("wrong"))
    with pytest.raises(ar.ArchiveError, match="must change"):
        ar.validate_correction(same)
    extra = _correction(s["state_id"], H("wrong"), H("right"))
    extra["note"] = "x"
    with pytest.raises(ar.ArchiveError):
        ar.validate_correction(extra)


def test_an_unmeasured_refusal_has_no_credit_and_is_not_a_flown_child():
    r = root()
    refused = ar.build_state(artefact_hashes={"delivery_rule_table": H("rule")}, parent_id=r["state_id"], iteration=1,
                             operator_class="delivery", candidate_id="cand-rule", verdict="refused", arm="typed",
                             refusal_code="offline-family-unsupported")
    assert refused["credit"] is None and refused["read"] is None and refused["refusal_code"] == "offline-family-unsupported"
    with pytest.raises(ar.ArchiveError):
        ar.build_state(artefact_hashes={"delivery_rule_table": H("r2")}, parent_id=r["state_id"], iteration=1, operator_class="delivery",
                       candidate_id="c", verdict="accepted", arm="typed", refusal_code="offline-family-unsupported")
    with pytest.raises(ar.ArchiveError):
        ar.build_state(artefact_hashes={"delivery_rule_table": H("r3")}, parent_id=r["state_id"], iteration=1, operator_class="delivery",
                       candidate_id="c", verdict="refused", arm="typed", refusal_code="made-up")
    states = [r, refused, refused | {"state_id": H("second"), "candidate_id": "cand-rule-2"}]
    chosen = pc.choose_parent(states)
    assert chosen["ranking"][0]["n_children"] == 0 and chosen["masked_classes"] == []      # two unmeasured refusals mask nothing
    curve = sel.curve(states, "typed")
    assert curve[0]["marked"] == "unflown" and curve[0]["flown_children"] == []
    meta = ms.build_meta_summary(states, "typed")
    assert meta["rows"][0]["n_refused"] == 2 and meta["rows"][0]["mean_measured_slu_pp"] is None


# ---- rereads ---------------------------------------------------------------------------------

def reread_record(state_id, iteration=2, verdict="refused"):
    return {"schema": ar.REREAD_SCHEMA, "state_id": state_id, "archived_verdict": "refused", "iteration": iteration,
            "candidate_id": H(f"cand-{iteration}"), "column": {"run_id": f"run-i{iteration}", "attempt": 1}, "reread_verdict": verdict,
            "clauses": {"ci_lb_gt_0": {"pass": False, "value": 0.0, "threshold": 0.0}}, "credit": credit(0.0, 0.0, 0.0, 0.0)}


def test_a_reread_is_a_write_once_sibling_that_never_touches_the_state_or_the_parent_choice(tmp_path):
    arch = ar.Archive(tmp_path / "arch")
    r = root()
    arch.put(r)
    child = state("a", parent=r["state_id"], verdict="refused")
    arch.put(child)
    raw = (tmp_path / "arch" / f"state-{child['state_id']}.json").read_bytes()
    states_before = arch.states()
    path, created = arch.put_reread(reread_record(child["state_id"]))
    assert created and path == tmp_path / "arch" / "rereads" / f"{child['state_id']}-i2.json"
    assert arch.put_reread(reread_record(child["state_id"]))[1] is False                 # identical re-run accepted
    changed = reread_record(child["state_id"])
    changed["reread_verdict"] = "accepted"
    with pytest.raises(ar.ArchiveError, match="different content"):
        arch.put_reread(changed)
    assert (tmp_path / "arch" / f"state-{child['state_id']}.json").read_bytes() == raw
    assert arch.states() == states_before and [x["state_id"] for x in arch.rereads()] == [child["state_id"]]
    assert pc.choose_parent(arch.states())["parent_id"] == r["state_id"]
    arch.put_reread(reread_record(child["state_id"], iteration=3))                      # a later iteration is its own file
    assert len(arch.rereads()) == 2


def test_a_reread_needs_an_archived_state_and_carries_identifiers_only(tmp_path):
    arch = ar.Archive(tmp_path / "arch")
    r = root()
    arch.put(r)
    with pytest.raises(ar.ArchiveError):
        arch.put_reread(reread_record(H("missing")))
    bad = reread_record(r["state_id"])
    bad["clauses"] = {"note": "free text"}
    with pytest.raises(ar.ArchiveError):
        arch.put_reread(bad)
    bad = reread_record(r["state_id"])
    bad["extra"] = 1
    with pytest.raises(ar.ArchiveError):
        arch.put_reread(bad)


def test_the_meta_summary_counts_rereads_only_when_some_exist():
    r = root()
    child = state("a", parent=r["state_id"], verdict="refused")
    plain = ms.build_meta_summary([r, child], "typed")
    assert all("n_rereads" not in row for row in plain["rows"])
    counted = ms.build_meta_summary([r, child], "typed", rereads=[reread_record(child["state_id"]), reread_record(child["state_id"], 3)])
    assert [row["n_rereads"] for row in counted["rows"]] == [2]
    ms.assert_meta_clean(counted)
