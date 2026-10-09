"""NX (2026-10-09): the guarded delivery normaliser ``saea-deliver-normalise-v4g``.

v4g is v4 plus the two TRAIN-only guards of the audio attribution note
(``docs/results/2026-10-09-slurp-nx-postprocessing-v4-audio-attribution.md``): ee-wilson (ee10 fires
only when the Wilson 95 % upper bound of the intent's pool entity-carrying rate is below 0.10) and
ti-expressible (ti1 fires only on intents with >= 100 pool exemplars).

Sections 1-4 are model-free and offline (synthetic statistics; the data root is never read). Section
5 reads the data root (the pinned tables, the sealed A2 delivered column and the attribution driver's
own guarded recompute) and is skipped when it is absent. It compares bytes, digests and counts only
and never prints a text.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.base import DELIVERY_NORMALISERS
from speech_aware_evidence_acquisition.rails import delivery_normalisers as dn
from speech_aware_evidence_acquisition.rails import slurp_projection_v3 as v3
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (
    SlotEntity,
    legal_intent_inventory,
    parse_slu_response,
)

_REPO = Path(__file__).resolve().parents[2]
RECEIPT = _REPO / "docs/receipts/knowledge/slurp-v4g-registration-v1.json"

INVENTORY = legal_intent_inventory(
    {"alarm": ("set", "remove", "query"), "general": ("quirky",), "play": ("music", "radio")}
)
TABLE = dn.ScopeRuleTable({"please": (10, 0)}, sha256="0" * 64, floor=5)


@pytest.fixture(autouse=True)
def _synthetic_inventory(monkeypatch):
    monkeypatch.setattr(v3, "_default_legal_intent_inventory", lambda: INVENTORY)


def _stats(intents: dict) -> dn.SlurpV4Statistics:
    """``intents``: intent -> (exemplars, exemplars carrying entities, {slot type: exemplar count}).
    No article or o'clock strip, so only ti1 / ee10 can edit."""
    return dn.SlurpV4Statistics(
        article_strip=[], oclock_strip=False,
        intent_n={i: n for i, (n, _k, _t) in intents.items()},
        intent_with_entities={i: k for i, (_n, k, _t) in intents.items()},
        intent_type={i: dict(t) for i, (_n, _k, t) in intents.items()},
    )


def _answer(scenario, action, entities=()):
    return json.dumps({"scenario": scenario, "action": action,
                       "entities": [{"type": t, "filler": f} for t, f in entities]},
                      ensure_ascii=False, sort_keys=True)


def _run(normaliser, stats, text):
    return normaliser(text, stats=stats, table=TABLE)


V4 = dn.SlurpProjectionV4DeliveryNormaliser()
V4G = dn.SlurpProjectionV4GuardedDeliveryNormaliser()


def _kept(outcome):
    return list(parse_slu_response(outcome.text)[2])


# ---------------------------------------------------------------------------
# 1. Identity and registration.


def test_v4g_carries_its_identity_and_is_registered():
    assert V4G.id == dn.DELIVER_NORMALISE_V4G == "saea-deliver-normalise-v4g"
    assert V4G.version == dn.DELIVER_NORMALISE_V4G_VERSION == "1"
    assert V4G.rule_id == dn.V4G_RULE_ID == "slurp-use-projection-v4g"
    assert V4G.carrier_lock_key == "slurp"
    assert dn.DELIVER_NORMALISE_V4G in DELIVERY_NORMALISERS.names()
    assert isinstance(DELIVERY_NORMALISERS.resolve(dn.DELIVER_NORMALISE_V4G),
                      dn.SlurpProjectionV4GuardedDeliveryNormaliser)
    # v4 is untouched: its id, version, rule id and absence of guards.
    assert (V4.id, V4.version, V4.rule_id, V4.guards) == (dn.DELIVER_NORMALISE_V4, "1", dn.V4_RULE_ID, None)


def test_v4g_is_armed_only_by_the_nx_r5_composed_fragments():
    """v4g became the delivery normaliser of lock v2.2 (module step 7). The only config files that name it are the NX R5 composed cells'
    own fragments (registered 2026-10-09: the arm and its smoke, baseline and experiment); every other registered cell keeps v3."""

    roots = [_REPO / "configs"]
    hits = sorted(p.name for root in roots for p in root.rglob("*")
                  if p.is_file() and dn.DELIVER_NORMALISE_V4G in p.read_text(encoding="utf-8", errors="ignore"))
    assert hits and all("nx-r5-composed-dev2000-added" in name for name in hits), hits
    assert "slurp-native-stage3-nx-r5-composed-dev2000-added-baseline-v1.json" in hits
    assert "slurp-native-stage3-nx-r5-composed-dev2000-added-smoke-4-baseline-v1.json" in hits


def test_the_guard_constants_are_pinned_in_code():
    guards = dn.V4G_GUARDS
    assert guards.ti1_min_exemplars == 100
    assert guards.ee_wilson_max_upper == 0.10 == dn.V4_EE_MIN_ENTITY_RATE
    assert guards.ee_wilson_z == dn.V4G_WILSON_Z == 1.959963984540054
    assert guards.to_document() == {
        "ti-expressible": {"ti1_min_pool_exemplars": 100},
        "ee-wilson": {"max_upper_bound": 0.10, "z": 1.959963984540054, "interval": "wilson-score-upper"},
    }


def test_the_wilson_bound_matches_the_attribution_note_example():
    # The intent behind the Fold-A audio loss: 4 of 45 pool exemplars carry entities (8.9 %), upper 20.7 %.
    assert dn.wilson_upper_bound(4, 45, dn.V4G_WILSON_Z) == pytest.approx(0.207, abs=5e-4)
    assert dn.wilson_upper_bound(0, 0, dn.V4G_WILSON_Z) == 1.0


# ---------------------------------------------------------------------------
# 2. Guard ti-expressible: exactly 100 pool exemplars.

_TI_ENTITIES = (("date", "monday"),)  # type "date" is in 0 exemplars of the intent -> ti1 would drop it


@pytest.mark.parametrize("n, v4g_drops", [(99, False), (100, True), (101, True)])
def test_ti1_fires_in_v4g_only_from_100_pool_exemplars(n, v4g_drops):
    # Every exemplar carries a time entity (so ee10 stays out of the way), none carries a date.
    stats = _stats({"alarm_set": (n, n, {"time": n})})
    raw = _answer("alarm", "set", _TI_ENTITIES)
    v4 = _run(V4, stats, raw)
    v4g = _run(V4G, stats, raw)
    assert _kept(v4) == []  # v4: type share 0 < 1 % at any n
    assert v4.receipt["entity_stage_counts"]["dropped_ti1"] == 1
    assert (_kept(v4g) == []) is v4g_drops
    assert v4g.receipt["entity_stage_counts"]["dropped_ti1"] == int(v4g_drops)


def test_ti1_boundary_keeps_the_entity_untouched_below_100():
    stats = _stats({"alarm_set": (99, 99, {"time": 99})})
    raw = _answer("alarm", "set", _TI_ENTITIES)
    outcome = _run(V4G, stats, raw)
    assert _kept(outcome) == [SlotEntity(type="date", filler="monday")]
    assert outcome.changed is False


# ---------------------------------------------------------------------------
# 3. Guard ee-wilson: rate below 0.10 but Wilson upper bound above 0.10.


def test_ee10_needs_a_resolved_rate_in_v4g():
    # 4 of 45: rate 0.089 < 0.10 (v4 empties the row), Wilson upper 0.207 >= 0.10 (v4g keeps it).
    unresolved = _stats({"alarm_set": (45, 4, {"time": 4})})
    raw = _answer("alarm", "set", (("time", "six am"),))
    assert unresolved.entity_rate("alarm_set") < 0.10
    assert dn.wilson_upper_bound(4, 45, dn.V4G_WILSON_Z) >= 0.10
    v4, v4g = _run(V4, unresolved, raw), _run(V4G, unresolved, raw)
    assert _kept(v4) == [] and v4.receipt["entity_stage_counts"]["dropped_ee10"] == 1
    assert _kept(v4g) == [SlotEntity(type="time", filler="six am")]
    assert v4g.receipt["entity_stage_counts"]["dropped_ee10"] == 0
    assert v4g.changed is False


def test_ee10_fires_in_v4g_when_the_upper_bound_is_below_the_threshold():
    # 4 of 400: rate 0.01, Wilson upper ~0.026 < 0.10: v4 and v4g both empty the row.
    resolved = _stats({"alarm_set": (400, 4, {"time": 4})})
    assert dn.wilson_upper_bound(4, 400, dn.V4G_WILSON_Z) < 0.10
    raw = _answer("alarm", "set", (("time", "six am"),))
    v4, v4g = _run(V4, resolved, raw), _run(V4G, resolved, raw)
    assert _kept(v4) == _kept(v4g) == []
    assert v4g.receipt["entity_stage_counts"]["dropped_ee10"] == 1
    assert v4g.text == v4.text


def test_ee10_wilson_boundary_is_strictly_below():
    # The smallest 0-carrier pool whose Wilson upper bound is < 0.10 fires; one fewer exemplar does not.
    z = dn.V4G_WILSON_Z
    n_fire = next(n for n in range(1, 200) if dn.wilson_upper_bound(0, n, z) < 0.10)
    for n, fires in ((n_fire - 1, False), (n_fire, True)):
        stats = _stats({"general_quirky": (n, 0, {})})
        out = _run(V4G, stats, _answer("general", "quirky", (("time", "six am"),)))
        assert (_kept(out) == []) is fires
    # v4 fires on both: a zero rate is below 0.10 at any n.
    assert _kept(_run(V4, _stats({"general_quirky": (n_fire - 1, 0, {})}),
                      _answer("general", "quirky", (("time", "six am"),)))) == []


def test_an_intent_absent_from_the_pool_is_left_alone():
    stats = _stats({"alarm_set": (400, 4, {"time": 4})})
    raw = _answer("play", "music", (("time", "six am"),))
    assert _run(V4G, stats, raw).changed is False
    assert _run(V4, stats, raw).changed is False


# ---------------------------------------------------------------------------
# 4. Receipt, replay entry, and the build receipt.


def test_the_receipt_records_the_guards_and_v4_does_not():
    stats = _stats({"alarm_set": (400, 4, {"time": 4})})
    raw = _answer("alarm", "set", (("time", "six am"),))
    receipt = _run(V4G, stats, raw).receipt
    assert receipt["normaliser_id"] == dn.DELIVER_NORMALISE_V4G and receipt["rule_id"] == dn.V4G_RULE_ID
    assert receipt["guards"] == dn.V4G_GUARDS.to_document()
    assert receipt["entity_stage"] == list(dn.V4_STAGES)
    assert "guards" not in _run(V4, stats, raw).receipt


def test_v4g_equals_v4_wherever_no_guard_binds():
    stats = _stats({"alarm_set": (400, 200, {"time": 200, "date": 5})})
    for raw in (_answer("alarm", "set", (("time", "six am"), ("date", "monday"))),
                _answer("alarm", "set"), _answer("alarm", "set", (("time", "please six am"),))):
        a, b = _run(V4, stats, raw), _run(V4G, stats, raw)
        assert a.text == b.text and a.changed == b.changed


def test_the_build_receipt_agrees_with_the_code():
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert receipt["normaliser"] == {"id": dn.DELIVER_NORMALISE_V4G, "version": dn.DELIVER_NORMALISE_V4G_VERSION,
                                     "rule_id": dn.V4G_RULE_ID, "base_normaliser": dn.DELIVER_NORMALISE_V4,
                                     "entity_stage": list(dn.V4_STAGES)}
    assert receipt["guards"] == dn.V4G_GUARDS.to_document()
    assert receipt["stats_tables"] == {n: {"relpath": dn.V4_TABLE_RELPATHS[n], "sha256": dn.V4_TABLE_SHA256[n]}
                                       for n in dn.V4_TABLES}
    assert receipt["stats_sha256"] == dn.V4_STATS_SHA256
    assert receipt["new_tables"] == []  # the intent-entity-rate table already carries both Wilson counts
    assert receipt["armed_by"] == []


# ---------------------------------------------------------------------------
# 5. The data root: the registered v4g path reproduces the attribution note's guarded A2 column.

_DATA = Path(os.environ.get("SPEECHRL_DATA_DIR", "") or "/nonexistent")
_FALLBACK_LOCK = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json")
_A2_RUN = ("SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-V1",
           "attempt-slurp-native-stage3-comp1b-dev2000-added-generation-v1")
_ATTRIBUTION_A2 = "analysis/SAEA-SLURP-NX-POSTPROC-V4-AUDIO-ATTRIBUTION-V1/a2/report.json"
_ATTRIBUTION_A2_SHA = "f5e486a814a33398bce8969fac653b0488dae5bcc25e35f9ae9ba24411d950c0"


def _data_ready() -> bool:
    if not _DATA.is_dir():
        return False
    needed = [_DATA / dn.V4_TABLE_RELPATHS[n] for n in dn.V4_TABLES]
    needed += [_DATA / dn.SCOPE_RULE_TABLE_RELPATH, _DATA / _ATTRIBUTION_A2,
               _DATA / "runs" / _A2_RUN[0] / _A2_RUN[1] / f"{_A2_RUN[0]}.outputs.jsonl"]
    return all(p.is_file() for p in needed)


needs_data = pytest.mark.skipif(not _data_ready(), reason="SPEECHRL_DATA_DIR with the pinned v4 tables absent")


def _import(relpath: str, name: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _REPO / relpath)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@needs_data
def test_the_registered_v4g_path_reproduces_the_attribution_notes_guarded_a2_column(monkeypatch):
    """Byte for byte: every row's v4g text equals the text the attribution driver's guarded rule set
    (ti-expressible + ee-wilson, its own recompute over the search driver's rules) renders, and the
    column's pooled delta and CI equal the note's report (pinned by hash)."""
    import argparse

    from speech_aware_evidence_acquisition.data.lock import umbrella_lock_path
    from speech_aware_evidence_acquisition.rails.slurp_projection_v3 import render_slurp_answer

    monkeypatch.setenv("SPEECHRL_DATA_DIR", str(_DATA))
    monkeypatch.setattr(dn, "_DEFAULT_V4_STATISTICS", [])
    monkeypatch.setattr(dn, "_DEFAULT_SCOPE_RULE_TABLE", [])
    report_path = _DATA / _ATTRIBUTION_A2
    assert hashlib.sha256(report_path.read_bytes()).hexdigest() == _ATTRIBUTION_A2_SHA
    note = json.loads(report_path.read_text(encoding="utf-8"))["guards"]["ti-expressible + ee-wilson"]

    attribution = _import("scripts/analysis/slurp_nx_postproc_v4_audio_attribution.py",
                          "slurp_nx_postproc_v4_audio_attribution")
    driver = attribution.DRV
    try:
        lock = umbrella_lock_path()
    except Exception:  # noqa: BLE001 - a worktree outside the umbrella layout
        lock = _FALLBACK_LOCK
    from speech_aware_evidence_acquisition.data.lock import load_lock
    from speech_aware_evidence_acquisition.reproduction.slurp_official_eval import load_legal_intent_inventory

    inventory = load_legal_intent_inventory(load_lock(lock), _DATA)  # the real one, not the synthetic fixture
    args = argparse.Namespace(data_root=str(_DATA), lock=str(lock), row_cluster=False)
    P = driver.prepare_partA(args, "a2")
    fns = attribution.guarded_rules(("ti-expressible", "ee-wilson"))

    normaliser = DELIVERY_NORMALISERS.resolve(dn.DELIVER_NORMALISE_V4G)
    sealed = P["delivered"]["rows"]
    outputs = {str(r["sample_id"]): r.get("text") or ""
               for r in driver.iter_jsonl(_DATA / "runs" / _A2_RUN[0] / _A2_RUN[1] / f"{_A2_RUN[0]}.outputs.jsonl")}
    env = P["builder"].env
    mismatches = edited = 0
    import numpy as np

    matrix = P["base"].copy()
    for k, sid in enumerate(P["ids"]):
        row = sealed[sid]
        expected = outputs[sid]
        if row["parsed"] and row["entities"]:
            pairs, _events = attribution.trace(attribution.V4, row["entities"], P["contexts"][sid], P["stats"],
                                               env, P["gold"][sid]["entities"], fns)
            new = [e for _i, e in pairs]
            if new != list(row["entities"]):
                expected = render_slurp_answer(row["scenario"], row["action"], new)
        outcome = normaliser(outputs[sid], inventory=inventory)
        mismatches += int(outcome.text.encode("utf-8") != expected.encode("utf-8"))
        edited += int(outcome.changed)
        assert outcome.receipt["stats_tables"] == dn.V4_TABLE_SHA256
        assert outcome.receipt["guards"] == dn.V4G_GUARDS.to_document()
        scenario, action, entities, _parsed = parse_slu_response(outcome.text)
        matrix[k] = np.array(driver.score_vector(P["gold"][sid], scenario, action, list(entities)))
    assert mismatches == 0
    result = P["boot"].contrast(P["base"], matrix)
    assert result["delta_slu_pp"] == note["pooled"]["delta_slu_pp"] == pytest.approx(0.9761)
    assert result["ci95_slu_pp"] == note["pooled"]["ci95_slu_pp"] == [0.2453, 1.712]
    assert result["delta_span_pp"] == note["pooled"]["delta_span_pp"]
    assert edited == 115
