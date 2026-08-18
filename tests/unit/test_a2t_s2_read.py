"""``analysis.a2t_s2_read``: the P-A2T Stage-2 supply-probe pinned offline
read suite.

Engineering-only, zero live model contact -- every fixture here is a
hand-authored synthetic attempt directory built on top of a small,
self-contained ``A2tS2World`` (20 headroom samples across two tiers, 5
distinct tools, one of them with an ``argument_defaults`` literal per tool
so induced-substitution can be exercised directly). This module is NEVER
pointed at the real flight attempt directory
(``$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-a2t-s2-120/``); that is a separate,
one-shot registered read.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis.a2t_s2_read import (
    RUN_ID,
    A2tS2ReadError,
    ArmPlan,
    build_a2t_s2_report,
    count_induced_substitutions,
    load_arm_plan,
    load_headroom_identity,
    main as a2t_s2_read_main,
    parse_argument_defaults,
    report_to_json,
    supplied_argument_values,
)
from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.rails.probes.a2t_s2_flight import (
    A2T_S2_ARMS,
    HEADROOM_SCHEMA,
    N0R_ARM,
    S1P_ARM,
    S2_ARM,
    S4_ARM,
)
from speech_aware_evidence_acquisition.reproduction.toolcall_scoring import ToolCall

# ---------------------------------------------------------------------------
# A2tS2World: 20 headroom samples, 2 tiers (18 + 2), 5 distinct tools, each
# tool's own registry row carrying a distinct argument_defaults literal
# ("x='default_toolNN'") -- never equal to any sample's own gold value, so a
# response using it is unambiguously an induced substitution.
# ---------------------------------------------------------------------------

TIER_A = "tier1_direct"  # 18 samples -- carries interpretive weight (>=16)
TIER_B = "tier2_parametric"  # 2 samples -- small-n caveat
TOOLS = [f"tool{i:02d}" for i in range(1, 6)]  # 5 distinct tools
# Sattolo-style cyclic derangement over the 5 tools -- no fixed points.
DERANGEMENT = {
    "tool01": "tool02",
    "tool02": "tool03",
    "tool03": "tool04",
    "tool04": "tool05",
    "tool05": "tool01",
}


def _sample_ids() -> list[str]:
    ids = [f"{TIER_A}:{i:06d}" for i in range(1, 19)]  # 18
    ids += [f"{TIER_B}:{i:06d}" for i in range(1, 3)]  # 2
    return ids  # 20 total


def _tool_for(sample_id: str) -> str:
    index = int(sample_id.split(":")[1])
    return TOOLS[(index - 1) % len(TOOLS)]


def _gold_value(sample_id: str) -> str:
    return f"gold_{sample_id.replace(':', '_')}"


def _default_value(tool_name: str) -> str:
    return f"default_{tool_name}"


class A2tS2World:
    def __init__(self, tmp_path: Path) -> None:
        self.data_root = tmp_path / "a2ts2-data"
        self.repo_root = tmp_path / "a2ts2-repo"
        self.lock_path = tmp_path / "a2ts2-lock.json"
        self.carrier_dir = self.data_root / "datasets" / "audio2tool"
        self.public = self.carrier_dir / "public"
        self.receipt_path = (
            self.repo_root / "docs" / "receipts" / "probe-samples" / "r1-a2t-s2-test.json"
        )
        self.sample_ids = _sample_ids()
        self._materialize()
        self._write_lock()

    def _materialize(self) -> None:
        entries_by_tier: dict[str, list[dict]] = {TIER_A: [], TIER_B: []}
        for sample_id in self.sample_ids:
            tier, id_str = sample_id.split(":")
            item_id = int(id_str)
            tool = _tool_for(sample_id)
            gold_value = _gold_value(sample_id)
            entries_by_tier[tier].append(
                {
                    "id": item_id,
                    "tier": tier,
                    "query_idx": item_id,
                    "query": f"do something with {tool}",
                    "domain": "test",
                    "category": "test",
                    "tool_id": TOOLS.index(tool) + 1,
                    "tool_name": tool,
                    "expected_tool_call": f"{tool}(x='{gold_value}')",
                    "extracted_params": {},
                    "additional_tool_calls": None,
                    "path": f"{tier}_audios/query_{item_id:05d}/turn.wav",
                    "duration": 0.5,
                }
            )
        for tier, entries in entries_by_tier.items():
            manifest = self.public / f"{tier}_data" / f"{tier}.json"
            manifest.parent.mkdir(parents=True, exist_ok=True)
            manifest.write_text(json.dumps(entries), encoding="utf-8")

        self.carrier_dir.mkdir(parents=True, exist_ok=True)
        fieldnames = [
            "tool_id",
            "domain",
            "category",
            "tool_name",
            "signature",
            "description",
            "argument_defaults",
            "argument_constraints",
        ]
        with (self.carrier_dir / "tools_registry.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for tool in TOOLS:
                writer.writerow(
                    {
                        "tool_id": str(TOOLS.index(tool) + 1),
                        "domain": "test",
                        "category": "test",
                        "tool_name": tool,
                        "signature": f"{tool}(x: String)",
                        "description": f"{tool} description",
                        "argument_defaults": f"x='{_default_value(tool)}'",
                        "argument_constraints": "",
                    }
                )

        from speech_aware_evidence_acquisition.reproduction.sampling import (
            split_identity_hash as compute_hash,
        )

        items = []
        for sample_id in self.sample_ids:
            tier, id_str = sample_id.split(":")
            items.append(
                {"id": int(id_str), "key": f"audio2tool:{sample_id}", "query_idx": int(id_str), "tier": tier}
            )
        payload = {
            "probe": "R1-a2t-s2-test",
            "carrier": "audio2tool",
            "seed": 1,
            "design": "synthetic a2t_s2_read test receipt",
            "pool_size": len(items),
            "strata_counts": {},
            "items": items,
            "split_identity_hash": compute_hash([item["key"] for item in items]),
            "split_role": "discovery",
        }
        self.receipt_path.parent.mkdir(parents=True, exist_ok=True)
        self.receipt_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _write_lock(self) -> None:
        document = {
            "asset_catalog": [
                {
                    "name": "audio2tool",
                    "kind": "dataset",
                    "local_subdir": "datasets/audio2tool",
                    "license": "cc-by-nc-4.0",
                    "lifecycle": "STAGE2_CANDIDATE",
                    "profiles": ["speech-aware-secondary"],
                }
            ],
            "models": [],
        }
        self.lock_path.write_text(json.dumps(document), encoding="utf-8")

    @property
    def split_identity_hash(self) -> str:
        return json.loads(self.receipt_path.read_text(encoding="utf-8"))["split_identity_hash"]


@pytest.fixture()
def a2ts2_world(tmp_path):
    return A2tS2World(tmp_path)


# ---------------------------------------------------------------------------
# Response-text builders.
# ---------------------------------------------------------------------------


def _correct_response(sample_id: str) -> str:
    tool = _tool_for(sample_id)
    return json.dumps([{"name": tool, "arguments": {"x": _gold_value(sample_id)}}])


def _wrong_value_response(sample_id: str) -> str:
    """Correct tool, a value that is NEITHER gold NOR any supplied
    default -- tool_accuracy=1, exact_match=0, induced_substitutions=0."""

    tool = _tool_for(sample_id)
    return json.dumps([{"name": tool, "arguments": {"x": "totally_unrelated_value"}}])


def _copy_supplied_default_response(sample_id: str) -> str:
    """Correct tool, value == THIS sample's own tool's supplied default --
    tool_accuracy=1, exact_match=0, induced_substitutions=1."""

    tool = _tool_for(sample_id)
    return json.dumps([{"name": tool, "arguments": {"x": _default_value(tool)}}])


def _wrong_tool_response(sample_id: str) -> str:
    """The deranged (wrong) tool, correct-looking value -- tool_accuracy=0,
    exact_match=0."""

    wrong = DERANGEMENT[_tool_for(sample_id)]
    return json.dumps([{"name": wrong, "arguments": {"x": _gold_value(sample_id)}}])


# ---------------------------------------------------------------------------
# Fixture builders: headroom.json / {RUN_ID}.arm-plan.json / outputs.jsonl /
# flight-receipt.json.
# ---------------------------------------------------------------------------


def _headroom_document(world: A2tS2World, **overrides) -> dict:
    document = {
        "schema": HEADROOM_SCHEMA,
        "note": "seeds the Stage-2 supply-probe registration",
        "attempt_dir": "attempt-a0-test",
        "split_identity_hash": world.split_identity_hash,
        "count": len(world.sample_ids),
        "sample_ids": list(world.sample_ids),
    }
    document.update(overrides)
    return document


def _write_headroom(path: Path, world: A2tS2World, **overrides) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_headroom_document(world, **overrides)), encoding="utf-8")


def _arm_plan_document(world: A2tS2World, *, n0r_sample_ids: list[str] | None = None, **overrides) -> dict:
    n0r_ids = list(world.sample_ids) if n0r_sample_ids is None else n0r_sample_ids
    selected_tools: dict[str, list[str]] = {}
    s1p: dict[str, list[str]] = {}
    s2: dict[str, list[str]] = {}
    s4_tool_name: dict[str, str] = {}
    for sample_id in world.sample_ids:
        tool = _tool_for(sample_id)
        selected_tools[sample_id] = [tool]
        s1p[sample_id] = [tool]
        distractor = TOOLS[(TOOLS.index(tool) + 1) % len(TOOLS)]
        s2[sample_id] = sorted([tool, distractor])
        s4_tool_name[sample_id] = DERANGEMENT[tool]
    document = {
        "seed": 1234,
        "headroom_ids": list(world.sample_ids),
        "n0r_sample_ids": n0r_ids,
        "selected_tools": selected_tools,
        "s1p_tool_names": s1p,
        "s2_tool_names": s2,
        "s4_derangement": dict(DERANGEMENT),
        "s4_tool_name": s4_tool_name,
    }
    document.update(overrides)
    return document


def _write_arm_plan(path: Path, world: A2tS2World, **overrides) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_arm_plan_document(world, **overrides)), encoding="utf-8")


def _row(arm: str, sample_id: str, response: str) -> dict:
    return {
        "arm": arm,
        "sample_id": sample_id,
        "supplied_tool": "unused",
        "response": response,
        "timing": {"started_at": "2026-08-18T00:00:00+00:00", "latency_seconds": 0.1},
    }


def _write_outputs_jsonl(path: Path, rows: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write((json.dumps(row) if isinstance(row, dict) else row) + "\n")


def _write_flight_receipt(
    path: Path,
    *,
    split_identity_hash: str,
    status: str = "COMPLETED",
    arms: list | None = None,
    request_failures: list | None = None,
) -> None:
    document = {
        "status": status,
        "error": None,
        "arms": arms if arms is not None else list(A2T_S2_ARMS),
        "split_identity_hash": split_identity_hash,
        "request_failures": request_failures if request_failures is not None else [],
    }
    path.write_text(json.dumps(document), encoding="utf-8")


def _build_attempt(
    tmp_path: Path,
    world: A2tS2World,
    *,
    s1p_fn,
    s2_fn,
    s4_fn,
    n0r_fn,
    n0r_ids: list[str] | None = None,
    name: str = "attempt",
    write_receipt: bool = True,
    receipt_kwargs: dict | None = None,
    write_arm_plan: bool = True,
    arm_plan_kwargs: dict | None = None,
    extra_rows: list | None = None,
) -> Path:
    attempt_dir = tmp_path / name
    n0r_ids = list(world.sample_ids) if n0r_ids is None else n0r_ids
    rows = []
    for sample_id in world.sample_ids:
        rows.append(_row(S1P_ARM, sample_id, s1p_fn(sample_id)))
        rows.append(_row(S2_ARM, sample_id, s2_fn(sample_id)))
        rows.append(_row(S4_ARM, sample_id, s4_fn(sample_id)))
    for sample_id in n0r_ids:
        rows.append(_row(N0R_ARM, sample_id, n0r_fn(sample_id)))
    if extra_rows:
        rows.extend(extra_rows)
    _write_outputs_jsonl(attempt_dir / "outputs.jsonl", rows)
    if write_receipt:
        kwargs = dict(split_identity_hash=world.split_identity_hash)
        kwargs.update(receipt_kwargs or {})
        _write_flight_receipt(attempt_dir / "flight-receipt.json", **kwargs)
    if write_arm_plan:
        kwargs = dict(n0r_sample_ids=n0r_ids)
        kwargs.update(arm_plan_kwargs or {})
        _write_arm_plan(attempt_dir / f"{RUN_ID}.arm-plan.json", world, **kwargs)
    return attempt_dir


def _headroom_path(tmp_path: Path, world: A2tS2World, name: str = "headroom.json", **overrides) -> Path:
    path = tmp_path / name
    _write_headroom(path, world, **overrides)
    return path


def _build_report(tmp_path, world, attempt_dir, headroom_path=None):
    lock = load_lock(world.lock_path)
    headroom_path = headroom_path or _headroom_path(tmp_path, world)
    return build_a2t_s2_report(
        attempt_dir, lock, world.data_root, repo_root=world.repo_root, headroom_path=headroom_path
    )


# ===========================================================================
# Branch-rule fixtures.
# ===========================================================================


def test_supply_converts_branch_fires(a2ts2_world, tmp_path):
    world = a2ts2_world
    ids = world.sample_ids
    converted = set(ids[:4])  # 4/20 = 20% >= 15%

    def s1p_fn(sample_id):
        return _correct_response(sample_id) if sample_id in converted else _wrong_value_response(sample_id)

    def s2_fn(sample_id):
        return _wrong_value_response(sample_id)  # S2 conversion = 0 -- lower than S1' -> DOSE point

    def s4_fn(sample_id):
        return _wrong_value_response(sample_id)  # correct tool, wrong value: retention 100%, conversion 0

    def n0r_fn(sample_id):
        return _wrong_value_response(sample_id)  # N0r EM-flip rate 0

    attempt_dir = _build_attempt(tmp_path, world, s1p_fn=s1p_fn, s2_fn=s2_fn, s4_fn=s4_fn, n0r_fn=n0r_fn)
    report = _build_report(tmp_path, world, attempt_dir)

    verdict = report.branch_verdict
    assert verdict.voided is False
    assert verdict.copy_trap is False
    assert verdict.schema_only is False
    assert verdict.supply_converts is True
    assert verdict.inert is False
    assert verdict.dose_point.verdict == "met"
    assert verdict.overall == "SUPPLY-CONVERTS + DOSE point (secondary, descriptive)"

    s1p_agg = report.per_arm[S1P_ARM].overall
    assert s1p_agg.em_conversion_rate == pytest.approx(0.20)
    assert s1p_agg.tool_accuracy == pytest.approx(1.0)
    s4_agg = report.per_arm[S4_ARM].overall
    assert s4_agg.em_conversion_rate == pytest.approx(0.0)
    assert s4_agg.tool_accuracy == pytest.approx(1.0)


def test_inert_branch_fires_when_no_arm_converts(a2ts2_world, tmp_path):
    world = a2ts2_world

    def flat(sample_id):
        return _wrong_value_response(sample_id)

    attempt_dir = _build_attempt(tmp_path, world, s1p_fn=flat, s2_fn=flat, s4_fn=flat, n0r_fn=flat)
    report = _build_report(tmp_path, world, attempt_dir)

    verdict = report.branch_verdict
    assert verdict.voided is False
    assert verdict.copy_trap is False
    assert verdict.schema_only is False
    assert verdict.supply_converts is False
    assert verdict.inert is True
    assert verdict.overall == "INERT"


def test_schema_only_branch_fires_when_s1p_and_s4_convert_equally(a2ts2_world, tmp_path):
    world = a2ts2_world
    ids = world.sample_ids
    converted = set(ids[:5])  # 5/20 = 25%

    def s1p_fn(sample_id):
        return _correct_response(sample_id) if sample_id in converted else _wrong_value_response(sample_id)

    def s4_fn(sample_id):
        return _correct_response(sample_id) if sample_id in converted else _wrong_value_response(sample_id)

    def s2_fn(sample_id):
        return _wrong_value_response(sample_id)

    def n0r_fn(sample_id):
        return _wrong_value_response(sample_id)

    attempt_dir = _build_attempt(tmp_path, world, s1p_fn=s1p_fn, s2_fn=s2_fn, s4_fn=s4_fn, n0r_fn=n0r_fn)
    report = _build_report(tmp_path, world, attempt_dir)

    verdict = report.branch_verdict
    assert verdict.voided is False
    assert verdict.copy_trap is False
    assert verdict.schema_only is True
    assert verdict.supply_converts is False
    assert verdict.overall.startswith("SCHEMA-ONLY")

    s1p_agg = report.per_arm[S1P_ARM].overall
    s4_agg = report.per_arm[S4_ARM].overall
    assert s1p_agg.em_conversion_rate == pytest.approx(0.25)
    assert s4_agg.em_conversion_rate == pytest.approx(0.25)


def test_copy_trap_branch_fires_on_induced_substitution(a2ts2_world, tmp_path):
    world = a2ts2_world
    ids = world.sample_ids
    flip_ids = set(ids[:2])  # 2 EM-flips
    copy_ids = set(ids[2:5])  # 3 induced substitutions -- >= 2 EM-flips

    def s1p_fn(sample_id):
        if sample_id in flip_ids:
            return _correct_response(sample_id)
        if sample_id in copy_ids:
            return _copy_supplied_default_response(sample_id)
        return _wrong_value_response(sample_id)

    def s2_fn(sample_id):
        return _wrong_value_response(sample_id)

    def s4_fn(sample_id):
        return _wrong_value_response(sample_id)

    def n0r_fn(sample_id):
        return _wrong_value_response(sample_id)

    attempt_dir = _build_attempt(tmp_path, world, s1p_fn=s1p_fn, s2_fn=s2_fn, s4_fn=s4_fn, n0r_fn=n0r_fn)
    report = _build_report(tmp_path, world, attempt_dir)

    verdict = report.branch_verdict
    assert verdict.voided is False
    assert verdict.copy_trap is True
    # S2 (flat, 0 conversions) < S1' (2/20) also trips the secondary, purely
    # descriptive DOSE point clause -- COPY-TRAP is still the PRIMARY branch.
    assert verdict.overall.startswith("COPY-TRAP")
    s1p_agg = report.per_arm[S1P_ARM].overall
    assert s1p_agg.em_flip_count == 2
    assert s1p_agg.induced_substitution_count == 3
    fired = [c for c in verdict.copy_trap_clauses if c.verdict == "met"]
    assert any("S1p" in c.clause_text for c in fired)


def test_copy_trap_branch_fires_on_s4_retention_collapse(a2ts2_world, tmp_path):
    world = a2ts2_world
    ids = world.sample_ids
    wrong_tool_ids = set(ids[:15])  # 15/20 wrong tool -> retention 5/20 = 25% < 90%

    def s1p_fn(sample_id):
        return _wrong_value_response(sample_id)

    def s2_fn(sample_id):
        return _wrong_value_response(sample_id)

    def s4_fn(sample_id):
        return _wrong_tool_response(sample_id) if sample_id in wrong_tool_ids else _wrong_value_response(sample_id)

    def n0r_fn(sample_id):
        return _wrong_value_response(sample_id)

    attempt_dir = _build_attempt(tmp_path, world, s1p_fn=s1p_fn, s2_fn=s2_fn, s4_fn=s4_fn, n0r_fn=n0r_fn)
    report = _build_report(tmp_path, world, attempt_dir)

    verdict = report.branch_verdict
    assert verdict.copy_trap is True
    assert verdict.overall == "COPY-TRAP"
    s4_agg = report.per_arm[S4_ARM].overall
    assert s4_agg.tool_accuracy == pytest.approx(0.25)
    retention_clause = next(c for c in verdict.copy_trap_clauses if "retention" in c.clause_text)
    assert retention_clause.verdict == "met"


def test_void_branch_fires_on_unstable_n0r_comparator(a2ts2_world, tmp_path):
    world = a2ts2_world
    ids = world.sample_ids
    flipped = set(ids[:6])  # 6/20 = 30% > 25%

    def n0r_fn(sample_id):
        return _correct_response(sample_id) if sample_id in flipped else _wrong_value_response(sample_id)

    def s1p_fn(sample_id):
        # Would otherwise clearly read SUPPLY-CONVERTS -- proves VOID
        # overrides every other branch regardless.
        return _correct_response(sample_id) if sample_id in set(ids[:4]) else _wrong_value_response(sample_id)

    def flat(sample_id):
        return _wrong_value_response(sample_id)

    attempt_dir = _build_attempt(tmp_path, world, s1p_fn=s1p_fn, s2_fn=flat, s4_fn=flat, n0r_fn=n0r_fn)
    report = _build_report(tmp_path, world, attempt_dir)

    verdict = report.branch_verdict
    assert verdict.voided is True
    # VOID overrides every other branch regardless of the (also purely
    # descriptive) DOSE point clause's own verdict.
    assert verdict.overall.startswith("VOID")
    n0r_agg = report.per_arm[N0R_ARM].overall
    assert n0r_agg.em_conversion_rate == pytest.approx(0.30)


# ===========================================================================
# Per-tier reporting correctness.
# ===========================================================================


def test_per_tier_table_is_mandatory_and_correctly_partitioned(a2ts2_world, tmp_path):
    world = a2ts2_world
    tier_a_ids = [sid for sid in world.sample_ids if sid.startswith(TIER_A)]
    tier_b_ids = [sid for sid in world.sample_ids if sid.startswith(TIER_B)]
    assert len(tier_a_ids) == 18
    assert len(tier_b_ids) == 2

    converted_in_a = set(tier_a_ids[:3])  # 3/18 in tier A only

    def s1p_fn(sample_id):
        return _correct_response(sample_id) if sample_id in converted_in_a else _wrong_value_response(sample_id)

    def flat(sample_id):
        return _wrong_value_response(sample_id)

    attempt_dir = _build_attempt(tmp_path, world, s1p_fn=s1p_fn, s2_fn=flat, s4_fn=flat, n0r_fn=flat)
    report = _build_report(tmp_path, world, attempt_dir)

    by_tier = report.per_arm[S1P_ARM].by_tier
    assert set(by_tier) == {TIER_A, TIER_B}
    assert by_tier[TIER_A].n_samples == 18
    assert by_tier[TIER_B].n_samples == 2
    assert by_tier[TIER_A].em_conversion_rate == pytest.approx(3 / 18)
    assert by_tier[TIER_B].em_conversion_rate == pytest.approx(0.0)
    # Pooled overall must equal the tier-weighted combination.
    overall = report.per_arm[S1P_ARM].overall
    assert overall.em_flip_count == by_tier[TIER_A].em_flip_count + by_tier[TIER_B].em_flip_count

    assert by_tier[TIER_A].interpretive_weight is True  # >= 16
    assert by_tier[TIER_B].interpretive_weight is False  # < 16

    document = report_to_json(report)
    assert set(document["per_arm"][S1P_ARM]["by_tier"]) == {TIER_A, TIER_B}


# ===========================================================================
# Harness-defect refusals.
# ===========================================================================


def _flat_fns():
    return (
        lambda sid: _wrong_value_response(sid),
        lambda sid: _wrong_value_response(sid),
        lambda sid: _wrong_value_response(sid),
        lambda sid: _wrong_value_response(sid),
    )


def test_malformed_row_is_a_harness_defect_refusal(a2ts2_world, tmp_path):
    world = a2ts2_world
    s1p_fn, s2_fn, s4_fn, n0r_fn = _flat_fns()
    attempt_dir = _build_attempt(tmp_path, world, s1p_fn=s1p_fn, s2_fn=s2_fn, s4_fn=s4_fn, n0r_fn=n0r_fn)
    lines = (attempt_dir / "outputs.jsonl").read_text(encoding="utf-8").splitlines()
    broken = json.loads(lines[0])
    del broken["response"]
    lines[0] = json.dumps(broken)
    (attempt_dir / "outputs.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")

    with pytest.raises(A2tS2ReadError, match="harness defect"):
        _build_report(tmp_path, world, attempt_dir)


def test_wrong_arm_row_count_is_a_harness_defect_refusal(a2ts2_world, tmp_path):
    world = a2ts2_world
    s1p_fn, s2_fn, s4_fn, n0r_fn = _flat_fns()
    attempt_dir = _build_attempt(tmp_path, world, s1p_fn=s1p_fn, s2_fn=s2_fn, s4_fn=s4_fn, n0r_fn=n0r_fn)
    lines = (attempt_dir / "outputs.jsonl").read_text(encoding="utf-8").splitlines()
    # Drop the first S1p row.
    first_s1p_index = next(i for i, line in enumerate(lines) if json.loads(line)["arm"] == S1P_ARM)
    del lines[first_s1p_index]
    (attempt_dir / "outputs.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")

    with pytest.raises(A2tS2ReadError, match="row count"):
        _build_report(tmp_path, world, attempt_dir)


def test_duplicate_arm_sample_pair_is_a_harness_defect_refusal(a2ts2_world, tmp_path):
    world = a2ts2_world
    s1p_fn, s2_fn, s4_fn, n0r_fn = _flat_fns()
    extra = [_row(S1P_ARM, world.sample_ids[0], _wrong_value_response(world.sample_ids[0]))]
    attempt_dir = _build_attempt(
        tmp_path, world, s1p_fn=s1p_fn, s2_fn=s2_fn, s4_fn=s4_fn, n0r_fn=n0r_fn, extra_rows=extra
    )

    with pytest.raises(A2tS2ReadError, match="duplicate row for"):
        _build_report(tmp_path, world, attempt_dir)


def test_headroom_id_set_mismatch_is_a_harness_defect_refusal(a2ts2_world, tmp_path):
    world = a2ts2_world
    s1p_fn, s2_fn, s4_fn, n0r_fn = _flat_fns()
    attempt_dir = _build_attempt(tmp_path, world, s1p_fn=s1p_fn, s2_fn=s2_fn, s4_fn=s4_fn, n0r_fn=n0r_fn)
    headroom_path = _headroom_path(tmp_path, world, sample_ids=list(world.sample_ids[:19]) + ["tier1_direct:999999"])

    with pytest.raises(A2tS2ReadError, match="does not match the frozen headroom manifest"):
        _build_report(tmp_path, world, attempt_dir, headroom_path=headroom_path)


def test_s4_derangement_fixed_point_is_a_harness_defect_refusal(a2ts2_world, tmp_path):
    world = a2ts2_world
    s1p_fn, s2_fn, s4_fn, n0r_fn = _flat_fns()
    broken_derangement = dict(DERANGEMENT)
    broken_derangement["tool01"] = "tool01"  # fixed point injected
    attempt_dir = _build_attempt(
        tmp_path,
        world,
        s1p_fn=s1p_fn,
        s2_fn=s2_fn,
        s4_fn=s4_fn,
        n0r_fn=n0r_fn,
        arm_plan_kwargs={"s4_derangement": broken_derangement},
    )

    with pytest.raises(A2tS2ReadError, match="fixed point"):
        _build_report(tmp_path, world, attempt_dir)


def test_non_completed_flight_receipt_is_a_harness_defect_refusal(a2ts2_world, tmp_path):
    world = a2ts2_world
    s1p_fn, s2_fn, s4_fn, n0r_fn = _flat_fns()
    attempt_dir = _build_attempt(
        tmp_path,
        world,
        s1p_fn=s1p_fn,
        s2_fn=s2_fn,
        s4_fn=s4_fn,
        n0r_fn=n0r_fn,
        receipt_kwargs={"status": "ABORTED"},
    )

    with pytest.raises(A2tS2ReadError, match="status='ABORTED'"):
        _build_report(tmp_path, world, attempt_dir)


def test_nonempty_request_failures_is_a_harness_defect_refusal(a2ts2_world, tmp_path):
    world = a2ts2_world
    s1p_fn, s2_fn, s4_fn, n0r_fn = _flat_fns()
    attempt_dir = _build_attempt(
        tmp_path,
        world,
        s1p_fn=s1p_fn,
        s2_fn=s2_fn,
        s4_fn=s4_fn,
        n0r_fn=n0r_fn,
        receipt_kwargs={"request_failures": [{"index": 3, "error": "TimeoutError"}]},
    )

    with pytest.raises(A2tS2ReadError, match="request_failures non-empty"):
        _build_report(tmp_path, world, attempt_dir)


def test_wrong_arms_field_is_a_harness_defect_refusal(a2ts2_world, tmp_path):
    world = a2ts2_world
    s1p_fn, s2_fn, s4_fn, n0r_fn = _flat_fns()
    attempt_dir = _build_attempt(
        tmp_path,
        world,
        s1p_fn=s1p_fn,
        s2_fn=s2_fn,
        s4_fn=s4_fn,
        n0r_fn=n0r_fn,
        receipt_kwargs={"arms": [S1P_ARM, S2_ARM]},
    )

    with pytest.raises(A2tS2ReadError, match="flight-receipt arms"):
        _build_report(tmp_path, world, attempt_dir)


def test_split_identity_hash_mismatch_is_a_harness_defect_refusal(a2ts2_world, tmp_path):
    world = a2ts2_world
    s1p_fn, s2_fn, s4_fn, n0r_fn = _flat_fns()
    attempt_dir = _build_attempt(
        tmp_path,
        world,
        s1p_fn=s1p_fn,
        s2_fn=s2_fn,
        s4_fn=s4_fn,
        n0r_fn=n0r_fn,
        receipt_kwargs={"split_identity_hash": "f" * 64},
    )

    with pytest.raises(A2tS2ReadError, match="split_identity_hash mismatch"):
        _build_report(tmp_path, world, attempt_dir)


def test_missing_flight_receipt_is_a_harness_defect_refusal(a2ts2_world, tmp_path):
    world = a2ts2_world
    s1p_fn, s2_fn, s4_fn, n0r_fn = _flat_fns()
    attempt_dir = _build_attempt(
        tmp_path, world, s1p_fn=s1p_fn, s2_fn=s2_fn, s4_fn=s4_fn, n0r_fn=n0r_fn, write_receipt=False
    )

    with pytest.raises(A2tS2ReadError, match="flight-receipt.json missing"):
        _build_report(tmp_path, world, attempt_dir)


def test_missing_arm_plan_raises_directly(a2ts2_world, tmp_path):
    world = a2ts2_world
    s1p_fn, s2_fn, s4_fn, n0r_fn = _flat_fns()
    attempt_dir = _build_attempt(
        tmp_path, world, s1p_fn=s1p_fn, s2_fn=s2_fn, s4_fn=s4_fn, n0r_fn=n0r_fn, write_arm_plan=False
    )

    with pytest.raises(A2tS2ReadError, match="arm-plan.json missing"):
        _build_report(tmp_path, world, attempt_dir)


def test_n0r_not_subset_of_headroom_is_a_harness_defect_refusal(a2ts2_world, tmp_path):
    world = a2ts2_world
    s1p_fn, s2_fn, s4_fn, n0r_fn = _flat_fns()
    bad_n0r = list(world.sample_ids[:5]) + ["tier1_direct:777777"]
    attempt_dir = tmp_path / "attempt"
    rows = []
    for sample_id in world.sample_ids:
        rows.append(_row(S1P_ARM, sample_id, s1p_fn(sample_id)))
        rows.append(_row(S2_ARM, sample_id, s2_fn(sample_id)))
        rows.append(_row(S4_ARM, sample_id, s4_fn(sample_id)))
    for sample_id in bad_n0r:
        rows.append(_row(N0R_ARM, sample_id, n0r_fn(sample_id)))
    _write_outputs_jsonl(attempt_dir / "outputs.jsonl", rows)
    _write_flight_receipt(attempt_dir / "flight-receipt.json", split_identity_hash=world.split_identity_hash)
    _write_arm_plan(attempt_dir / f"{RUN_ID}.arm-plan.json", world, n0r_sample_ids=bad_n0r)

    with pytest.raises(A2tS2ReadError, match="not a subset of headroom_ids"):
        _build_report(tmp_path, world, attempt_dir)


def test_missing_gold_for_headroom_sample_is_a_harness_defect_refusal(a2ts2_world, tmp_path):
    world = a2ts2_world
    s1p_fn, s2_fn, s4_fn, n0r_fn = _flat_fns()
    extra_id = "tier1_direct:555555"  # not in the frozen receipt/manifest
    world.sample_ids.append(extra_id)
    try:
        headroom_path = _headroom_path(tmp_path, world)
        attempt_dir = tmp_path / "attempt"
        rows = []
        for sample_id in world.sample_ids:
            rows.append(_row(S1P_ARM, sample_id, s1p_fn(sample_id)))
            rows.append(_row(S2_ARM, sample_id, s2_fn(sample_id)))
            rows.append(_row(S4_ARM, sample_id, s4_fn(sample_id)))
            rows.append(_row(N0R_ARM, sample_id, n0r_fn(sample_id)))
        _write_outputs_jsonl(attempt_dir / "outputs.jsonl", rows)
        _write_flight_receipt(attempt_dir / "flight-receipt.json", split_identity_hash=world.split_identity_hash)
        _write_arm_plan(attempt_dir / f"{RUN_ID}.arm-plan.json", world)

        with pytest.raises(A2tS2ReadError, match="no resolvable gold"):
            _build_report(tmp_path, world, attempt_dir, headroom_path=headroom_path)
    finally:
        world.sample_ids.remove(extra_id)


def test_headroom_manifest_wrong_schema_raises_directly(a2ts2_world, tmp_path):
    world = a2ts2_world
    path = _headroom_path(tmp_path, world, schema="wrong-schema-v1")

    with pytest.raises(A2tS2ReadError, match="schema must be"):
        load_headroom_identity(path)


# ===========================================================================
# Small unit-level checks.
# ===========================================================================


def test_parse_argument_defaults_blank_is_empty():
    kwargs, warning = parse_argument_defaults("toolX", "")
    assert kwargs == {}
    assert warning is None


def test_parse_argument_defaults_parses_key_value():
    kwargs, warning = parse_argument_defaults("toolX", "deviceId='light_1'")
    assert kwargs == {"deviceId": "light_1"}
    assert warning is None


def test_parse_argument_defaults_unparseable_is_informational_only():
    kwargs, warning = parse_argument_defaults("toolX", "mode: [Home, Armed_Away]")
    assert kwargs == {}
    assert warning is not None
    assert "toolX" in warning


def _canon(value):
    from speech_aware_evidence_acquisition.reproduction.toolcall_scoring import _canonical_value

    return _canonical_value(value)


def test_count_induced_substitutions_counts_only_supplied_diverging_values():
    expected = (ToolCall(name="toolA", arguments={"x": "gold"}),)
    predicted_match = (ToolCall(name="toolA", arguments={"x": "gold"}),)
    predicted_diverge_supplied = (ToolCall(name="toolA", arguments={"x": "supplied"}),)
    predicted_diverge_unsupplied = (ToolCall(name="toolA", arguments={"x": "other"}),)
    supplied = {"x": {_canon("supplied")}}

    assert count_induced_substitutions(predicted_match, expected, supplied) == 0
    assert count_induced_substitutions(predicted_diverge_supplied, expected, supplied) == 1
    assert count_induced_substitutions(predicted_diverge_unsupplied, expected, supplied) == 0


def test_count_induced_substitutions_engages_across_tool_names():
    """Note 7: key-only alignment -- a predicted call under a DIFFERENT
    tool name than gold still counts if it copies a supplied value for a
    key gold also uses (this is exactly the S4 "wrong tool's default"
    scenario)."""

    expected = (ToolCall(name="rightTool", arguments={"x": "gold"}),)
    predicted = (ToolCall(name="wrongTool", arguments={"x": "wrong_default"}),)
    supplied = {"x": {_canon("wrong_default")}}

    assert count_induced_substitutions(predicted, expected, supplied) == 1


def test_count_induced_substitutions_excludes_keys_with_no_gold_entry():
    expected = (ToolCall(name="toolA", arguments={"x": "gold"}),)
    predicted = (ToolCall(name="toolA", arguments={"y": "supplied"}),)
    supplied = {"y": {_canon("supplied")}}

    assert count_induced_substitutions(predicted, expected, supplied) == 0


def test_supplied_argument_values_reads_registry_defaults(a2ts2_world):
    from speech_aware_evidence_acquisition.data.audio2tool import load_tool_registry

    lock = load_lock(a2ts2_world.lock_path)
    registry_index = {row["tool_name"]: row for row in load_tool_registry(lock, a2ts2_world.data_root)}
    values, warnings = supplied_argument_values(("tool01",), registry_index)
    assert values == {"x": {_canon("default_tool01")}}
    assert warnings == ()


def test_load_arm_plan_rejects_malformed_document(tmp_path):
    path = tmp_path / "bad.arm-plan.json"
    path.write_text(json.dumps({"seed": "not-an-int"}), encoding="utf-8")
    with pytest.raises(A2tS2ReadError, match="'seed' must be an int"):
        load_arm_plan(path)


def test_report_to_json_shape(a2ts2_world, tmp_path):
    world = a2ts2_world
    s1p_fn, s2_fn, s4_fn, n0r_fn = _flat_fns()
    attempt_dir = _build_attempt(tmp_path, world, s1p_fn=s1p_fn, s2_fn=s2_fn, s4_fn=s4_fn, n0r_fn=n0r_fn)
    report = _build_report(tmp_path, world, attempt_dir)

    document = report_to_json(report)
    assert document["schema"] == "saea-a2t-s2-read-v1"
    assert set(document["per_arm"]) == set(A2T_S2_ARMS)
    for arm in A2T_S2_ARMS:
        assert "overall" in document["per_arm"][arm]
        assert "by_tier" in document["per_arm"][arm]
    assert document["branch_verdict"]["overall"] == "INERT"


# ===========================================================================
# CLI: end-to-end + one-shot idempotence guard.
# ===========================================================================


def _cli_repo_layout(tmp_path: Path, world: A2tS2World) -> Path:
    repo_root = tmp_path / "umbrella" / "studies" / "study"
    receipts_dir = repo_root / "docs" / "receipts" / "probe-samples"
    receipts_dir.mkdir(parents=True)
    (receipts_dir / world.receipt_path.name).write_text(
        world.receipt_path.read_text(encoding="utf-8"), encoding="utf-8"
    )
    lock_dest = tmp_path / "umbrella" / "docs" / "datasets.lock.json"
    lock_dest.parent.mkdir(parents=True, exist_ok=True)
    lock_dest.write_text(world.lock_path.read_text(encoding="utf-8"), encoding="utf-8")
    return repo_root


def test_cli_refuses_to_run_twice_against_the_same_output_dir(a2ts2_world, tmp_path, monkeypatch):
    world = a2ts2_world
    s1p_fn, s2_fn, s4_fn, n0r_fn = _flat_fns()
    attempt_dir = _build_attempt(tmp_path, world, s1p_fn=s1p_fn, s2_fn=s2_fn, s4_fn=s4_fn, n0r_fn=n0r_fn)
    headroom_path = _headroom_path(tmp_path, world)
    repo_root = _cli_repo_layout(tmp_path, world)
    monkeypatch.setenv("SPEECHRL_DATA_DIR", str(world.data_root))
    output_dir = tmp_path / "read-report"
    output_dir.mkdir()

    argv = [
        str(attempt_dir),
        "--output-dir",
        str(output_dir),
        "--headroom-manifest",
        str(headroom_path),
        "--repo-root",
        str(repo_root),
    ]

    first_exit = a2t_s2_read_main(argv)
    assert first_exit == 0
    verdict_path = output_dir / "verdict.json"
    assert verdict_path.is_file()
    assert (output_dir / "report.txt").is_file()

    second_exit = a2t_s2_read_main(argv)
    assert second_exit == 1
