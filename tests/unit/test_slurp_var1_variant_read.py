"""Tests for the VAR-1 VARIANT READ driver (registered open items VAR1-OPEN-1 / VAR1-OPEN-2).

Everything here runs against a SYNTHETIC world under ``tmp_path``: a small roster with a per-item
gold stratum, a synthetic registered package (analysis recipe + registered facts), six synthetic
sealed run trees in the shape the reused ``slurp_plan_bad_case_bank`` loaders expect, a synthetic
exemplar release/snapshot, and a synthetic gold table injected by replacing the driver's
``load_gold`` seam. No real ``SPEECHRL_DATA_DIR`` byte is read by this file and the driver is never
pointed at the real data root.

The fixture is deliberately HONEST: every per-sample official row's tp/fp/fn counts are derived
from the same predicted/gold entity lists the outputs and the gold table carry, and each arm's
official aggregate is recomputed from its own rows, so the driver's reproduction checks (sealed
aggregate to 1e-6, per-row entity view against the sealed counts, per-TYPE totals against the
sealed totals) pass for the right reason rather than because the fixture was made agreeable.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DRIVER_PATH = REPO_ROOT / "scripts" / "analysis" / "slurp_var1_variant_read.py"

_SPEC = importlib.util.spec_from_file_location("slurp_var1_variant_read", DRIVER_PATH)
drv = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = drv
_SPEC.loader.exec_module(drv)

from speech_aware_evidence_acquisition.reproduction.slurp_scoring import SlotEntity  # noqa: E402

CARRIER = "slurp"
SENTINEL_TEXT_MARKER = "SENTINEL-DO-NOT-PERSIST-7f3a2b"

ARMS = ("plan", "planr", "exk10", "exk30", "exdiv", "perk16c5")
FRAGMENT_OF = {
    "plan": "slurp-native-stage3-var1-plan-r01c-v1",
    "planr": "slurp-native-stage3-var1-planr-r01c-v1",
    "exk10": "slurp-native-stage3-var1-ex-k10-r01c-v1",
    "exk30": "slurp-native-stage3-var1-ex-k30-r01c-v1",
    "exdiv": "slurp-native-stage3-var1-ex-div-r01c-v1",
    "perk16c5": "slurp-native-stage3-var1-per-k16c5-r01c-v1",
}
RUN_OF = {key: f"SAEA-SLURP-STAGE3-VAR1-{key.upper()}-R01C-V1" for key in ARMS}
ATTEMPT_OF = {key: f"attempt-stage3-var1-{key}-r01c-v1-generation" for key in ARMS}

SCORER_ID = "slurp-slu-official-train"
ROSTER_RELPATH = "docs/receipts/rosters/unit-var1-roster.json"
PACKAGE_RELPATH = "docs/readiness/unit-var1-package"
SPLIT_ID = "train"
EXEMPLAR_RELEASE_RELPATH = "knowledge/unit/exemplars/release.json"

#: Four scenarios x sixteen rows = 64 rows, so a state cell can clear the 60-row reportability
#: floor and every scenario carries enough rows for a leave-one-scenario-out check.
SCENARIOS = ("alarm", "calendar", "email", "weather")
ROWS_PER_SCENARIO = 16
ROWS = len(SCENARIOS) * ROWS_PER_SCENARIO


# --------------------------------------------------------------------------
# Fixture construction
# --------------------------------------------------------------------------


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )


def _row_specs() -> list[dict]:
    """One deterministic spec per row: ids, gold labels, channel, duration, state inputs."""

    specs: list[dict] = []
    for scenario_index, scenario in enumerate(SCENARIOS):
        for offset in range(ROWS_PER_SCENARIO):
            index = scenario_index * ROWS_PER_SCENARIO + offset
            utterance = f"{CARRIER}:{SPLIT_ID}:{index:06d}"
            specs.append(
                {
                    "index": index,
                    "sample_id": f"{utterance}:audio-{index}",
                    "utterance_id": utterance,
                    "scenario": scenario,
                    "action": f"act{offset % 4}",
                    "intent": f"{scenario}_act{offset % 4}",
                    "headset": offset % 8 == 0,
                    "audio_seconds": 1.0 + 0.25 * index,
                    "gold_types": (("date",) if offset % 3 == 0 else ("time", "person")),
                }
            )
    return specs


def _make_roster(repo_root: Path, specs: list[dict]) -> Path:
    items = [
        {
            "audio_seconds": spec["audio_seconds"],
            "draw_rank": spec["index"],
            "headset": spec["headset"],
            "sample_id": spec["sample_id"],
            "stratum": spec["scenario"],
            "utterance_id": spec["utterance_id"],
        }
        for spec in specs
    ]
    ids = [item["sample_id"] for item in items]
    identity = drv.prr.split_identity_hash(drv.prr.prefixed(CARRIER, sorted(ids)))
    path = repo_root / ROSTER_RELPATH
    _write_json(
        path,
        {
            "carrier_lock_key": CARRIER,
            "items": items,
            "roster_id": "UNIT-VAR1-ROSTER",
            "roster_role": "construction",
            "split_identity_hash": identity,
            "split_role": "discovery",
            "strata_counts": {name: ROWS_PER_SCENARIO for name in SCENARIOS},
        },
    )
    return path


def _predicted_entities(spec: dict, arm: str) -> list[SlotEntity]:
    """The arm's delivered entities. ``exk30`` omits one gold entity (an FN), ``exdiv`` emits a
    spurious ``place`` (an FP), everyone else matches gold exactly."""

    gold = [SlotEntity(type=name, filler=f"f{spec['index']}-{name}") for name in spec["gold_types"]]
    if arm == "exk30" and gold:
        return gold[:-1]
    if arm == "exdiv":
        return gold + [SlotEntity(type="place", filler=f"x{spec['index']}")]
    return gold


def _intent_correct(spec: dict, arm: str) -> bool:
    """A deterministic, arm-dependent correctness pattern with real structure: ``exk10`` is better
    than the plan on the far-field rows of two scenarios and ``perk16c5`` worse everywhere, so the
    advantage table has signal and a sign that can be checked for stability."""

    base = spec["index"] % 5 != 0
    if arm == "planr":
        # A request-identical replicate is NOT bit-identical: greedy decoding differs across batch
        # compositions, so a handful of rows flip. Without this the fixture's own null would be
        # exactly zero and every variant would separate from it trivially.
        return (not base) if spec["index"] % 11 == 0 else base
    if arm == "exk10":
        return base or spec["scenario"] in ("alarm", "calendar")
    if arm == "exk30":
        return base
    if arm == "exdiv":
        return base
    if arm == "perk16c5":
        return base and spec["index"] % 7 != 0
    return base


def _per_sample_row(spec: dict, arm: str, gold_entities: list[SlotEntity]) -> dict:
    predicted = _predicted_entities(spec, arm)
    remaining = list(gold_entities)
    tp = 0
    fp = 0
    for entity in predicted:
        if entity in remaining:
            tp += 1
            remaining.remove(entity)
        else:
            fp += 1
    fn = len(remaining)
    intent = 1.0 if _intent_correct(spec, arm) else 0.0
    denominator = 2 * tp + fp + fn
    slot_f1 = (2 * tp / denominator) if denominator else 1.0
    # The word/char SLU counts fold the label pair in beside the entities, exactly as the official
    # scorer's own slu-f1 does: two label tokens, both right or both wrong.
    label_tp = 2.0 * intent
    label_fp = 2.0 * (1.0 - intent)
    label_fn = 2.0 * (1.0 - intent)
    slu_tp = tp + label_tp
    slu_fp = fp + label_fp
    slu_fn = fn + label_fn
    slu_denominator = 2 * slu_tp + slu_fp + slu_fn
    slu_f1 = (2 * slu_tp / slu_denominator) if slu_denominator else 1.0
    return {
        "sample_id": spec["sample_id"],
        "parsed": 1.0,
        "scenario_action_exact": intent,
        "scenario_exact": intent,
        "action_exact": intent,
        "slot_f1_exact_f1": slot_f1,
        "slot_f1_exact_tp": float(tp),
        "slot_f1_exact_fp": float(fp),
        "slot_f1_exact_fn": float(fn),
        "slu_f1_f1": slu_f1,
        "slu_f1_word_tp": slu_tp,
        "slu_f1_word_fp": slu_fp,
        "slu_f1_word_fn": slu_fn,
        "slu_f1_char_tp": 0.0,
        "slu_f1_char_fp": 0.0,
        "slu_f1_char_fn": 0.0,
    }


def _official_aggregate(rows: list[dict]) -> dict:
    table = {row["sample_id"]: row for row in rows}
    ids = sorted(table)
    slu = drv.pooled_f1(table, ids, drv.MICRO_METRICS["slu_f1_micro"])
    span = drv.pooled_f1(table, ids, drv.MICRO_METRICS["span_f1_micro"])
    intent = sum(row["scenario_action_exact"] for row in rows) / len(rows)
    return {
        "official": {
            "action_accuracy": intent,
            "intent_accuracy": intent,
            "scenario_accuracy": intent,
            "slu_f1": slu,
            "span_f1": span,
        },
        "samples": len(ids),
        "split_id": "unit-var1",
    }


def _candidates(spec: dict, arm: str) -> list[str]:
    """Perception's own candidate list. The plan form proposes three, PER-K16C5 five -- which is
    exactly why the state keys are read off the comparator and not off the variant."""

    width = 5 if arm == "perk16c5" else 3
    intents = [spec["intent"]]
    for other in SCENARIOS:
        for action in range(2):
            candidate = f"{other}_act{action}"
            if candidate not in intents:
                intents.append(candidate)
    if spec["index"] % 4 == 0:
        # A row whose gold intent is NOT in the list: rotate it out.
        intents = intents[1:]
    return intents[:width]


def _exemplar_value_ids(spec: dict, arm: str) -> list[str]:
    count = {"exk10": 10, "exk30": 30, "exdiv": 7}.get(arm, 20)
    start = (spec["index"] * 3) % 40
    return [f"value:{1 + (start + offset) % 40}" for offset in range(count)]


def _make_arm(
    data_root: Path,
    arm: str,
    specs: list[dict],
    gold_entities: dict[str, list[SlotEntity]],
    *,
    split_identity_hash: str,
    status: str = "COMPLETED",
    ids_override: list[str] | None = None,
) -> None:
    run_id = RUN_OF[arm]
    attempt_id = ATTEMPT_OF[arm]
    run_dir = data_root / "runs" / run_id / attempt_id
    run_dir.mkdir(parents=True, exist_ok=True)

    rows = [_per_sample_row(spec, arm, gold_entities[spec["sample_id"]]) for spec in specs]

    output_lines = []
    phase_results = []
    for spec in specs:
        predicted = _predicted_entities(spec, arm)
        payload = {
            "scenario": spec["scenario"] if _intent_correct(spec, arm) else "wrongscenario",
            "action": spec["action"] if _intent_correct(spec, arm) else "wrongaction",
            "entities": [{"type": e.type, "filler": e.filler} for e in predicted],
        }
        text = json.dumps(payload)
        output_lines.append(
            json.dumps(
                {
                    "admitted": True,
                    "arm": run_id,
                    "sample_id": spec["sample_id"],
                    "text": text,
                }
            )
        )
        candidates = _candidates(spec, arm)
        phase_results.append(
            {
                "sample_id": spec["sample_id"],
                "agent_states": [
                    {
                        "state_kind": "phase:perception",
                        "content": json.dumps(
                            {
                                "candidates": [
                                    {
                                        "intent_id": intent,
                                        "distinction": f"d{rank}",
                                        "unresolved_fields": [],
                                    }
                                    for rank, intent in enumerate(candidates)
                                ]
                            }
                        ),
                    }
                ],
                "waves": [
                    {
                        "transition": {
                            "new_value_ids": [
                                f"train-exemplars::{value}"
                                for value in _exemplar_value_ids(spec, arm)
                            ]
                            + ["slot-contracts::contract:date", "slot-contracts::contract:time"]
                        }
                    }
                ],
                "native_episode_receipt": {
                    "planner_routes": [{"action": "ACCEPT", "revision_count": 0}],
                    "role_visits": [
                        {"role_id": name}
                        for name in ("perception", "solver", "reviewer", "planner")
                    ],
                    "deliver_normaliser": {
                        "applied": True,
                        "changed": False,
                        "fillers_changed": 0,
                        "labels_changed": 0,
                    },
                    "context_fit": {"compacted_contacts": 0, "slot_tokens": 24576},
                },
                "metrics": {"parsed": True, "response_chars": len(text)},
                "contacts": [{}, {}, {}, {}],
            }
        )

    outputs_path = run_dir / f"{run_id}.outputs.jsonl"
    outputs_path.write_text("\n".join(output_lines) + "\n", encoding="utf-8", newline="\n")

    _write_json(
        run_dir / f"{run_id}.phases.json",
        {
            "attempt_id": attempt_id,
            "run_id": run_id,
            "schema": "saea-flight-phase-summaries-v1",
            "phases": [
                {
                    "controller_policy_id": "saea-evidence-agent-plan-v1",
                    "knowledge_snapshot_sha256": "0" * 64,
                    "results": phase_results,
                    "run_id": run_id,
                }
            ],
        },
    )

    scores_path = run_dir / f"{run_id}.scores.json"
    _write_json(scores_path, {SCORER_ID: {"aggregate": _official_aggregate(rows), "per_sample": rows}})

    ids = ids_override if ids_override is not None else sorted(spec["sample_id"] for spec in specs)
    cost = {
        "audio_seconds_used": 40.0 * len(specs),
        "calls_used": 4 * len(specs) + {"exk30": 20, "exk10": -10}.get(arm, 0),
        "completion_tokens_total": 120 * len(specs),
        "latency_seconds_total": 2.0 * len(specs),
        "prompt_tokens_total": (12000 + {"exk30": 900, "perk16c5": 2200, "exk10": -600}.get(arm, 0))
        * len(specs),
        "tool_calls": 0,
    }
    _write_json(run_dir / f"{run_id}.generation-manifest.json", {"cost": cost, "run_id": run_id})
    _write_json(
        run_dir / f"{run_id}.run-manifest.json",
        {
            "config": {
                "config_hash": _fragment_config_hash(arm),
                "fragments": {"experiment": FRAGMENT_OF[arm]},
            },
            "protocol_hash": _fragment_protocol_hash(arm),
            "run_id": run_id,
            "scores": {"path": str(scores_path), "sha256": _sha(scores_path)},
            "split": {
                "carrier_lock_key": CARRIER,
                "count": len(ids),
                "identity_hash": split_identity_hash,
                "ids": ids,
                "role": "discovery",
            },
            "status": status,
            "study_commit": "0" * 40,
            "study_repo_dirt": [],
        },
    )
    (run_dir / "score-jobs.jsonl").write_text(
        json.dumps({"job_id": attempt_id}) + "\n", encoding="utf-8", newline="\n"
    )
    _write_json(
        run_dir / "flight-receipts.json",
        {
            "run_id": run_id,
            "schema": "saea-flight-receipts-v1",
            "stages": {
                "run_phases": {"contacts_per_second": 0.8, "wall_seconds": 900.0},
                "seal": {
                    "serving_monitor_summary": {
                        "active_seconds": 3600.0 + {"exk30": 400.0, "perk16c5": 700.0, "exk10": -300.0}.get(arm, 0.0),
                        "mean_utilization_percent": 62.0,
                        "wall_seconds": 4000.0,
                    }
                },
            },
        },
    )


def _fragment_config_hash(arm: str) -> str:
    return hashlib.sha256(f"composed::{FRAGMENT_OF[arm]}".encode("utf-8")).hexdigest()


def _fragment_protocol_hash(arm: str) -> str:
    return hashlib.sha256(f"protocol::{FRAGMENT_OF[arm]}".encode("utf-8")).hexdigest()


def _make_exemplar_release(data_root: Path) -> str:
    release_path = data_root / EXEMPLAR_RELEASE_RELPATH
    values = []
    for index in range(1, 41):
        scenario = SCENARIOS[index % len(SCENARIOS)]
        values.append(
            {
                "value_id": f"value:{index}",
                "task_target": f"{scenario}_act{index % 4}",
                "content": SENTINEL_TEXT_MARKER,
            }
        )
    _write_json(
        release_path.parent / "snapshot.json",
        {"snapshot_id": "unit-exemplars-v1", "snapshot_sha256": "0" * 64, "values": values},
    )
    _write_json(release_path, {"release_id": "unit-exemplars-v1", "values": len(values)})
    return _sha(release_path)


def _make_package(
    repo_root: Path,
    *,
    split_identity_hash: str,
    roster_sha256: str,
    exemplar_sha256: str,
    seal_pins: dict[str, dict] | None = None,
) -> None:
    arms = {}
    for arm in ARMS:
        entry = {
            "attempt_id": ATTEMPT_OF[arm],
            "run_id": RUN_OF[arm],
            "outputs_sha256": drv.PENDING,
            "run_manifest_sha256": drv.PENDING,
            "scores_sha256": drv.PENDING,
        }
        entry.update((seal_pins or {}).get(arm, {}))
        arms[arm] = entry
    _write_json(
        repo_root / PACKAGE_RELPATH / "analysis-recipe-v1.json",
        {
            "arms": arms,
            "claim_boundary": "descriptive paired read on a CONSTRUCTION roster",
            "comparator": {"arm": "plan", "run_id": RUN_OF["plan"]},
            "driver": {
                "cluster_key": "utterance_id",
                "draws": 200,
                "roster": ROSTER_RELPATH,
                "seed": 20260915,
                "split_identity_hash": split_identity_hash,
            },
            "estimators": {"paired_per_row": "analysis.paired.paired_contrast"},
            "own_null": {"left": RUN_OF["plan"], "right": RUN_OF["planr"]},
            "recipe_id": drv.RECIPE_ID,
            "resampling": {"cluster_key": "utterance_id", "draws": 200, "seed": 20260915},
            "scorer": {"id": SCORER_ID},
            "schema": "saea-paired-analysis-recipe-v1",
        },
    )
    _write_json(
        repo_root / PACKAGE_RELPATH / "registered-facts-v1.json",
        {
            "hashes": {
                FRAGMENT_OF[arm]: {
                    "composed_config_hash": _fragment_config_hash(arm),
                    "protocol_hash": _fragment_protocol_hash(arm),
                }
                for arm in ARMS
            },
            "pins": {
                "roster": {"relpath": ROSTER_RELPATH, "sha256": roster_sha256},
                "train_exemplars_release": {
                    "relpath": EXEMPLAR_RELEASE_RELPATH,
                    "sha256": exemplar_sha256,
                },
            },
            "population": {
                "rows": ROWS,
                "split_identity_hash": split_identity_hash,
            },
            "schema": "saea-var1-registered-facts-v1",
        },
    )


class _GoldRecord:
    """The three gold fields the read touches, in the shape ``data.slurp.SlurpRecord`` carries."""

    def __init__(self, spec: dict, entities: list[SlotEntity]) -> None:
        self.sample_id = spec["sample_id"]
        self.utterance_id = spec["utterance_id"]
        self.scenario = spec["scenario"]
        self.action = spec["action"]
        self.intent = spec["intent"]
        self.entities = tuple(entities)


@pytest.fixture
def world(tmp_path: Path, monkeypatch):
    repo_root = tmp_path / "repo"
    data_root = tmp_path / "data"
    specs = _row_specs()
    roster_path = _make_roster(repo_root, specs)
    roster_doc = json.loads(roster_path.read_text(encoding="utf-8"))
    split_identity_hash = roster_doc["split_identity_hash"]

    gold_entities = {
        spec["sample_id"]: [
            SlotEntity(type=name, filler=f"f{spec['index']}-{name}") for name in spec["gold_types"]
        ]
        for spec in specs
    }
    records = {spec["sample_id"]: _GoldRecord(spec, gold_entities[spec["sample_id"]]) for spec in specs}
    monkeypatch.setattr(
        drv,
        "load_gold",
        lambda lock_path, data_root, split_id: {
            "metadata_path": "synthetic",
            "metadata_sha256": "1" * 64,
            "records": records,
        },
    )

    for arm in ARMS:
        _make_arm(
            data_root,
            arm,
            specs,
            gold_entities,
            split_identity_hash=split_identity_hash,
        )
    exemplar_sha = _make_exemplar_release(data_root)
    _make_package(
        repo_root,
        split_identity_hash=split_identity_hash,
        roster_sha256=_sha(roster_path),
        exemplar_sha256=exemplar_sha,
    )
    return {
        "repo_root": repo_root,
        "data_root": data_root,
        "specs": specs,
        "gold_entities": gold_entities,
        "roster_path": roster_path,
        "split_identity_hash": split_identity_hash,
    }


def _argv(world: dict, out: Path, *extra: str) -> list[str]:
    return [
        "--repo-root",
        str(world["repo_root"]),
        "--data-root",
        str(world["data_root"]),
        "--out-root",
        str(out),
        "--package",
        PACKAGE_RELPATH,
        "--lock",
        str(world["repo_root"] / "unused-lock.json"),
        "--draws",
        "200",
        *extra,
    ]


def _run(world: dict, out: Path, *extra: str) -> int:
    return drv.main(_argv(world, out, *extra))


@pytest.fixture
def completed(world, tmp_path):
    out = tmp_path / "out"
    assert _run(world, out) == 0
    return out


def _load(out: Path, name: str) -> dict:
    return json.loads((out / name).read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# The happy path, and the order the registration fixes
# --------------------------------------------------------------------------


def test_every_registered_artefact_is_written(completed):
    for name in drv.ARTEFACTS:
        assert (completed / name).exists(), name


def test_own_null_is_read_before_the_variant_tables(completed):
    """The margin table is ABOVE the variant table in the document, and the variant artefact is
    DERIVED from the sealed own-null artefact's own bytes."""

    readme = (completed / "README.md").read_text(encoding="utf-8")
    assert readme.index(drv.SECTION_OWN_NULL) < readme.index(drv.SECTION_VARIANTS)

    own_null = _load(completed, "own-null.json")
    contrasts = _load(completed, "variant-contrasts.json")
    assert contrasts["inputs_sha256"]["own_null_content"] == drv.content_sha256(
        completed / "own-null.json"
    )
    assert own_null["inputs_sha256"]["stop_content"] == drv.content_sha256(
        completed / "stop.json"
    )
    assert contrasts["margins"] == own_null["h_cross_r01c"]
    assert own_null["h_cross_r01c"]["h_slu"] > 0.0
    # The context nulls are printed beside h_cross_r01c and are never the bar.
    assert own_null["context_only_nulls"]["h_within_roll_aa"]["h_slu"] == 0.735
    assert own_null["context_only_nulls"]["h_within_roll_aa"]["h_intent"] == 0.0


def test_variant_stage_refuses_without_a_sealed_own_null(world, tmp_path):
    """Removing the sealed margin artefact makes the variant stage refuse rather than recompute a
    margin of its own."""

    out = tmp_path / "out"
    args = drv.parse_args(_argv(world, out))
    recipe = drv.load_json(args.repo_root / args.package_relpath / "analysis-recipe-v1.json")
    arm_specs = drv._arm_specs(recipe, args.expect_arms)
    roster = drv.load_roster(args.repo_root, args.roster_relpath, args.cluster_key)
    arms = {
        key: drv.load_arm(
            key=key,
            run_id=spec["run_id"],
            attempt_id=spec["attempt_id"],
            data_root=args.data_root,
            roster=roster,
            scorer_id=args.scorer_id,
        )
        for key, spec in arm_specs.items()
    }
    with pytest.raises(drv.Var1ReadError, match="own-null artefact is not sealed"):
        drv.stage_variants(
            arms=arms,
            roster=roster,
            args=args,
            own_null={"h_cross_r01c": {"h_slu": 1.0, "h_intent": 1.0}},
        )


def test_variant_table_carries_the_reading_flags(completed):
    contrasts = _load(completed, "variant-contrasts.json")
    assert sorted(contrasts["variants"]) == sorted(set(ARMS) - {"plan"})
    for key, block in contrasts["variants"].items():
        assert sorted(block["metrics"]) == [
            "intent_exact",
            "per_row_slu",
            "pooled_slu_f1",
            "span_f1",
        ]
        for name, entry in block["metrics"].items():
            flags = entry["read_flags"]
            assert flags["margin_key"] == drv.MARGIN_OF[name]
            low, high = entry["cluster_bootstrap"]["ci95_pp"]
            assert flags["ci95_lower_above_zero"] is (low > 0.0)
            assert flags["ci95_excludes_zero"] is (low > 0.0 or high < 0.0)
            assert flags["point_estimate_outside_margin"] is (
                abs(entry["delta_pp"]) > flags["h_cross_r01c_pp"]
            )
            assert flags["separated_from_null"] is (
                flags["ci95_excludes_zero"] and flags["point_estimate_outside_margin"]
            )
            assert entry["saves"] + entry["harms"] + entry["ties"] == ROWS
        assert block["role"].startswith("A/A") == (key == "planr")


# --------------------------------------------------------------------------
# Per-slot-TYPE decomposition against the sealed totals
# --------------------------------------------------------------------------


def test_per_type_decomposition_reproduces_the_sealed_totals(completed, world):
    payload = _load(completed, "slot-type-decomposition.json")
    scores = {
        arm: json.loads(
            (
                world["data_root"]
                / "runs"
                / RUN_OF[arm]
                / ATTEMPT_OF[arm]
                / f"{RUN_OF[arm]}.scores.json"
            ).read_text(encoding="utf-8")
        )
        for arm in ARMS
    }
    for arm in ARMS:
        entry = payload["per_arm"][arm]
        rows = scores[arm][SCORER_ID]["per_sample"]
        for name in ("tp", "fp", "fn"):
            field = f"slot_f1_exact_{name}"
            sealed = sum(row[field] for row in rows)
            assert entry["sealed_totals"][field] == pytest.approx(sealed)
            assert entry["derived_totals"][field] == pytest.approx(sealed)
            assert sum(
                per_type[name] for per_type in entry["per_type"].values()
            ) == pytest.approx(sealed)
        assert entry["reproduces_sealed_totals"] is True

    # The fixture's own construction: exk30 drops one gold entity per multi-entity row (FN mass up)
    # and exdiv emits a spurious `place` on every row (FP mass up, in a TYPE the plan never emits).
    assert payload["delta_vs_comparator"]["exk30"]["fn_total"] > 0
    assert payload["delta_vs_comparator"]["exdiv"]["fp_total"] == ROWS
    assert payload["per_arm"]["exdiv"]["per_type"]["place"]["fp"] == ROWS
    assert payload["per_arm"]["plan"]["per_type"].get("place") is None


def test_per_type_decomposition_refuses_on_a_tampered_sealed_total(world, tmp_path):
    """A sealed per-sample count that the entity lists cannot reproduce is a refusal, not a
    silently reported number."""

    run_dir = world["data_root"] / "runs" / RUN_OF["exk10"] / ATTEMPT_OF["exk10"]
    scores_path = run_dir / f"{RUN_OF['exk10']}.scores.json"
    document = json.loads(scores_path.read_text(encoding="utf-8"))
    document[SCORER_ID]["per_sample"][0]["slot_f1_exact_fp"] += 3.0
    _write_json(scores_path, document)
    manifest_path = run_dir / f"{RUN_OF['exk10']}.run-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["scores"]["sha256"] = _sha(scores_path)
    _write_json(manifest_path, manifest)

    out = tmp_path / "out"
    assert _run(world, out) == 2


# --------------------------------------------------------------------------
# Perception coverage
# --------------------------------------------------------------------------


def test_perception_coverage_joins_gold_intent_onto_the_sealed_candidates(completed, world):
    payload = _load(completed, "perception-coverage.json")
    expected_uncovered = sum(1 for spec in world["specs"] if spec["index"] % 4 == 0)
    for arm in ARMS:
        entry = payload["per_arm"][arm]
        assert entry["rows"] == ROWS
        # The fixture rotates the gold intent out of the list on every fourth row and nowhere else.
        covered = round(entry["gold_intent_in_candidate_union_rate_pct"] * ROWS / 100.0)
        assert covered == ROWS - expected_uncovered
        assert entry["distinct_candidate_ids_rate_pct"] == 100.0
        assert entry["empty_candidate_list_rows"] == 0
        assert sum(entry["taxonomy"].values()) == ROWS
        # The two intent classes partition the intent-wrong rows.
        wrong = ROWS - entry["taxonomy"]["CORRECT"] - entry["taxonomy"]["ENTITY-FN-ONLY"] \
            - entry["taxonomy"]["ENTITY-FP-ONLY"] - entry["taxonomy"]["ENTITY-MIXED"] \
            - entry["taxonomy"]["MALFORMED"]
        assert entry["intent_covered"] + entry["intent_uncovered"] == wrong

    # PER-K16C5 is the only arm whose candidate list is wider, which is the coverage lever.
    assert payload["per_arm"]["perk16c5"]["mean_candidate_width"] == 5.0
    assert payload["per_arm"]["plan"]["mean_candidate_width"] == 3.0
    assert payload["delta_vs_comparator"]["perk16c5"]["mean_candidate_width_delta"] == 2.0
    assert sorted(payload["per_arm"]["plan"]["candidate_width_histogram"]) == ["3"]


# --------------------------------------------------------------------------
# Per-scenario table
# --------------------------------------------------------------------------


def test_per_scenario_table_uses_the_gold_stratum_in_both_weightings(completed):
    payload = _load(completed, "per-scenario.json")
    assert payload["scenarios"] == sorted(SCENARIOS)
    assert all(count == ROWS_PER_SCENARIO for count in payload["row_counts"].values())
    for key, block in payload["per_variant"].items():
        assert sorted(block["per_scenario"]) == sorted(SCENARIOS)
        assert all(cell["n"] == ROWS_PER_SCENARIO for cell in block["per_scenario"].values())
        weightings = block["weightings"]
        assert set(weightings) == {"natural_mixture", "equal_scenario"}
        # Every stratum is the same size here, so the equal-stratum intent delta is arithmetically
        # the natural-mixture one; the SLU delta is a pooled ratio and need not agree.
        assert weightings["equal_scenario"]["intent_delta_pp"] == pytest.approx(
            weightings["natural_mixture"]["intent_delta_pp"]
        )
    # exk10's fixture gain is confined to two scenarios, and the table localises it.
    exk10 = payload["per_variant"]["exk10"]["per_scenario"]
    assert exk10["alarm"]["intent_delta_pp"] > 0
    assert exk10["email"]["intent_delta_pp"] == pytest.approx(0.0)


def test_read_refuses_a_roster_without_a_per_item_stratum(world, tmp_path):
    document = json.loads(world["roster_path"].read_text(encoding="utf-8"))
    for item in document["items"]:
        item.pop("stratum")
    _write_json(world["roster_path"], document)
    # Re-pin the registered facts to the edited roster so the refusal is the stratum one.
    facts_path = world["repo_root"] / PACKAGE_RELPATH / "registered-facts-v1.json"
    facts = json.loads(facts_path.read_text(encoding="utf-8"))
    facts["pins"]["roster"]["sha256"] = _sha(world["roster_path"])
    _write_json(facts_path, facts)
    out = tmp_path / "out"
    with pytest.raises(drv.Var1ReadError, match="withholds the per-item stratum"):
        drv.run(drv.parse_args(_argv(world, out)))


# --------------------------------------------------------------------------
# Group-relative advantage
# --------------------------------------------------------------------------


def test_group_relative_advantage_arithmetic_on_a_known_fixture():
    """Three arms with hand-written per-row scores: the advantage is the score minus the group
    mean on that row, in percentage points, and the advantages sum to zero over the group."""

    class _Stub:
        def __init__(self, table):
            self._table = table

        @property
        def rows_table(self):
            return self._table

    ids = ["r1", "r2"]
    arms = {
        "a": _Stub({"r1": {"m": 1.0}, "r2": {"m": 0.0}}),
        "b": _Stub({"r1": {"m": 0.0}, "r2": {"m": 0.0}}),
        "c": _Stub({"r1": {"m": 0.5}, "r2": {"m": 0.3}}),
    }
    advantage = drv._advantages(arms=arms, ids=ids, group=("a", "b", "c"), field_name="m")
    assert advantage["a"]["r1"] == pytest.approx(100 * (1.0 - 0.5))
    assert advantage["b"]["r1"] == pytest.approx(100 * (0.0 - 0.5))
    assert advantage["c"]["r1"] == pytest.approx(100 * (0.5 - 0.5))
    assert advantage["a"]["r2"] == pytest.approx(100 * (0.0 - 0.1))
    assert advantage["c"]["r2"] == pytest.approx(100 * (0.3 - 0.1))
    for row in ids:
        assert sum(advantage[key][row] for key in ("a", "b", "c")) == pytest.approx(0.0)

    # A group that excludes a member still scores that member -- the PLANR substitution relies on
    # exactly this: the baseline is the GROUP mean, not the mean over every arm present.
    narrow = drv._advantages(arms=arms, ids=ids, group=("a", "b"), field_name="m")
    assert narrow["c"]["r1"] == pytest.approx(100 * (0.5 - 0.5))
    assert narrow["a"]["r1"] == pytest.approx(100 * (1.0 - 0.5))


def test_advantage_group_excludes_the_replicate_and_reports_its_gap(completed):
    payload = _load(completed, "group-relative-advantage.json")
    primary = payload["scores"]["per_row_slu"]
    assert primary["group"] == sorted(drv.ADVANTAGE_GROUP)
    assert "planr" not in primary["group"]
    assert primary["group_replicate"] == sorted(drv.ADVANTAGE_GROUP_REPLICATE)
    assert set(payload["state_keys"]) == set(drv.STATE_KEYS)
    for state_key in payload["state_keys"]:
        cells = primary["per_state"][state_key]
        assert cells
        assert sum(entry["n"] for entry in cells.values()) == ROWS
        for entry in cells.values():
            assert sorted(entry["advantage_pp"]) == sorted(drv.ADVANTAGE_GROUP)
            assert entry["planr_minus_plan_advantage_pp"] is not None
            best = entry["best_variant"]
            assert entry["best_advantage_pp"] == pytest.approx(entry["advantage_pp"][best])
            assert entry["advantage_pp"][best] == pytest.approx(max(entry["advantage_pp"].values()))


def test_reportability_needs_sixty_rows(completed, world, tmp_path):
    """The 60-row floor is the rule, not a comment: the channel key's headset cell holds 8 rows
    here and is never reportable, while the 64-row all-rows cells can be."""

    payload = _load(completed, "group-relative-advantage.json")
    channel = payload["scores"]["per_row_slu"]["per_state"]["channel"]
    assert channel["headset"]["n"] == ROWS // 8
    assert channel["headset"]["reportable"] is False
    assert any("below the 60-row floor" in reason for reason in channel["headset"]["reasons"])
    assert channel["far_field"]["n"] == ROWS - ROWS // 8

    # Lowering the floor can only ever ADD reportable cells, and the row count decides it.
    out = tmp_path / "out-low"
    assert _run(world, out, "--min-state-rows", "4") == 0
    low = _load(out, "group-relative-advantage.json")["scores"]["per_row_slu"]["per_state"]
    assert low["channel"]["headset"]["reportable"] is (
        low["channel"]["headset"]["leave_one_scenario_out"]["sign_stable"]
    )
    assert _load(out, "policy-table.json")["min_state_rows"] == 4


def test_leave_one_scenario_out_sign_check():
    """A cell whose advantage sign depends on one scenario is not reportable; a cell whose sign
    survives every drop is."""

    scenario_of = {"a1": "alarm", "a2": "alarm", "b1": "email", "b2": "email"}
    stable = {"a1": 2.0, "a2": 3.0, "b1": 4.0, "b2": 5.0}
    result = drv._leave_one_scenario_out(
        members=sorted(scenario_of), advantage=stable, scenario_of=scenario_of
    )
    assert result["sign_stable"] is True
    assert result["scenarios_present"] == 2
    assert result["min_pp"] == pytest.approx(2.5)
    assert result["max_pp"] == pytest.approx(4.5)

    # One scenario carries the whole positive mass: dropping it flips the sign.
    fragile = {"a1": 20.0, "a2": 20.0, "b1": -5.0, "b2": -5.0}
    flipped = drv._leave_one_scenario_out(
        members=sorted(scenario_of), advantage=fragile, scenario_of=scenario_of
    )
    assert flipped["full_mean_pp"] == pytest.approx(7.5)
    assert flipped["sign_stable"] is False
    assert flipped["reason"] == "the sign flips when a scenario is dropped"

    # A single-scenario cell cannot be checked at all, so it is never reportable.
    single = drv._leave_one_scenario_out(
        members=["a1", "a2"], advantage=stable, scenario_of=scenario_of
    )
    assert single["sign_stable"] is False
    assert single["reason"] == "a leave-one-scenario-out subset is empty"

    # An exactly-zero advantage has no sign to survive.
    flat = drv._leave_one_scenario_out(
        members=sorted(scenario_of),
        advantage={key: 0.0 for key in scenario_of},
        scenario_of=scenario_of,
    )
    assert flat["sign_stable"] is False


def test_policy_table_rows_match_the_advantage_cells(completed):
    policy = _load(completed, "policy-table.json")
    advantage = _load(completed, "group-relative-advantage.json")["scores"]["per_row_slu"]
    assert policy["score"] == "per_row_slu"
    assert policy["cells"] == sum(len(cells) for cells in advantage["per_state"].values())
    assert policy["reportable_cells"] == sum(
        1 for row in policy["rows"] if row["reportable"]
    )
    for row in policy["rows"]:
        cell = advantage["per_state"][row["state_key"]][row["state_cell"]]
        assert row["best_variant"] == cell["best_variant"]
        assert row["best_advantage_pp"] == pytest.approx(cell["best_advantage_pp"])
        assert row["n"] == cell["n"]
        assert row["reportable"] is cell["reportable"]
    assert policy["rows"] == sorted(
        policy["rows"], key=lambda row: (row["state_key"], row["state_cell"])
    )


def test_states_come_from_the_comparator_not_the_variant(world):
    """VAR1-PER-K16C5 proposes five candidates and the plan three; the candidate-count state key
    must show the PLAN's widths, or the policy would be keyed on the action it is choosing."""

    args = drv.parse_args(_argv(world, world["data_root"] / "unused"))
    roster = drv.load_roster(args.repo_root, args.roster_relpath, args.cluster_key)
    facts = drv.load_json(args.repo_root / args.package_relpath / "registered-facts-v1.json")
    exemplars = drv.load_exemplar_targets(
        args.data_root,
        facts["pins"]["train_exemplars_release"]["relpath"],
        facts["pins"]["train_exemplars_release"]["sha256"],
    )
    comparator = drv.load_arm(
        key="plan",
        run_id=RUN_OF["plan"],
        attempt_id=ATTEMPT_OF["plan"],
        data_root=args.data_root,
        roster=roster,
        scorer_id=args.scorer_id,
    )
    states = drv.build_states(comparator=comparator, roster=roster, exemplars=exemplars)
    assert set(states["candidate_count"].values()) == {"candidates-3"}
    assert set(states["channel"].values()) == {"headset", "far_field"}
    assert set(states["duration_tercile"].values()) == {
        "duration-t1-short",
        "duration-t2-mid",
        "duration-t3-long",
    }
    # Contiguous terciles of the roster's own durations, near-equal by construction.
    counts = {}
    for band in states["duration_tercile"].values():
        counts[band] = counts.get(band, 0) + 1
    assert max(counts.values()) - min(counts.values()) <= 1
    assert all(name.startswith("agree-") or name == drv.AGREEMENT_NONE
               for name in states["exemplar_top_agreement"].values())


# --------------------------------------------------------------------------
# Cost
# --------------------------------------------------------------------------


def test_cost_table_and_frontier(completed):
    payload = _load(completed, "cost.json")
    assert payload["reference_rows"] == ROWS
    for arm in ARMS:
        entry = payload["per_arm"][arm]
        assert entry["rows"] == ROWS
        assert entry["contacts_per_row"] == pytest.approx(entry["contacts"] / ROWS)
        assert entry["prompt_tokens_per_row"] == pytest.approx(
            entry["prompt_tokens_total"] / ROWS
        )
        assert entry["gpu_hours"] == pytest.approx(entry["gpu_hours_per_reference_rows"])
    assert payload["per_arm"]["exk10"]["contacts_per_row"] < payload["per_arm"]["plan"]["contacts_per_row"]
    assert payload["per_arm"]["exk30"]["prompt_tokens_per_row"] > payload["per_arm"]["plan"]["prompt_tokens_per_row"]
    assert payload["pareto_frontier"]
    assert set(payload["pareto_frontier"]) <= set(ARMS)
    # The realised supply size is read from the episode's own transitions, per variant.
    supply = {arm: payload["per_arm"][arm]["supply_realisation"] for arm in ARMS}
    assert supply["exk10"]["exemplar_values_per_row_mean"] == pytest.approx(10.0)
    assert supply["exk30"]["exemplar_values_per_row_mean"] == pytest.approx(30.0)
    assert supply["plan"]["exemplar_values_per_row_mean"] == pytest.approx(20.0)


# --------------------------------------------------------------------------
# Refusals
# --------------------------------------------------------------------------


def test_refuses_an_incomplete_manifest(world, tmp_path):
    run_dir = world["data_root"] / "runs" / RUN_OF["exdiv"] / ATTEMPT_OF["exdiv"]
    path = run_dir / f"{RUN_OF['exdiv']}.run-manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["status"] = "RUNNING"
    _write_json(path, manifest)
    out = tmp_path / "out"
    with pytest.raises(drv.Var1ReadError, match="not COMPLETED"):
        drv.run(drv.parse_args(_argv(world, out)))
    assert not out.exists()


def test_refuses_a_dirty_study_tree(world, tmp_path):
    run_dir = world["data_root"] / "runs" / RUN_OF["plan"] / ATTEMPT_OF["plan"]
    path = run_dir / f"{RUN_OF['plan']}.run-manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["study_repo_dirt"] = ["scripts/analysis/x.py"]
    _write_json(path, manifest)
    with pytest.raises(drv.Var1ReadError, match="dirty study tree"):
        drv.run(drv.parse_args(_argv(world, tmp_path / "out")))


def test_refuses_a_registered_protocol_hash_disagreement(world, tmp_path):
    facts_path = world["repo_root"] / PACKAGE_RELPATH / "registered-facts-v1.json"
    facts = json.loads(facts_path.read_text(encoding="utf-8"))
    facts["hashes"][FRAGMENT_OF["exk30"]]["protocol_hash"] = "f" * 64
    _write_json(facts_path, facts)
    with pytest.raises(drv.Var1ReadError, match="registered protocol_hash"):
        drv.run(drv.parse_args(_argv(world, tmp_path / "out")))


def test_refuses_a_registered_composed_config_hash_disagreement(world, tmp_path):
    facts_path = world["repo_root"] / PACKAGE_RELPATH / "registered-facts-v1.json"
    facts = json.loads(facts_path.read_text(encoding="utf-8"))
    facts["hashes"][FRAGMENT_OF["plan"]]["composed_config_hash"] = "e" * 64
    _write_json(facts_path, facts)
    with pytest.raises(drv.Var1ReadError, match="registered composed_config_hash"):
        drv.run(drv.parse_args(_argv(world, tmp_path / "out")))


def test_refuses_an_unregistered_experiment_fragment(world, tmp_path):
    facts_path = world["repo_root"] / PACKAGE_RELPATH / "registered-facts-v1.json"
    facts = json.loads(facts_path.read_text(encoding="utf-8"))
    facts["hashes"].pop(FRAGMENT_OF["exdiv"])
    _write_json(facts_path, facts)
    with pytest.raises(drv.Var1ReadError, match="no hashes for the sealed manifest's own"):
        drv.run(drv.parse_args(_argv(world, tmp_path / "out")))


def test_refuses_a_pinned_seal_hash_disagreement(world, tmp_path):
    """A recipe seal pin left at PENDING_SEAL is recorded as unpinned; a pinned one that
    disagrees with the sealed bytes is a refusal."""

    completed_out = tmp_path / "out-pending"
    assert _run(world, completed_out) == 0
    pins = _load(completed_out, "stop.json")["arms"]["plan"]["seal_pins"]
    assert all(entry["pinned"] is False for entry in pins.values())

    recipe_path = world["repo_root"] / PACKAGE_RELPATH / "analysis-recipe-v1.json"
    recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
    recipe["arms"]["plan"]["scores_sha256"] = "a" * 64
    _write_json(recipe_path, recipe)
    with pytest.raises(drv.Var1ReadError, match="recipe pins scores_sha256"):
        drv.run(drv.parse_args(_argv(world, tmp_path / "out")))


def test_accepts_a_correct_seal_pin(world, tmp_path):
    run_dir = world["data_root"] / "runs" / RUN_OF["planr"] / ATTEMPT_OF["planr"]
    recipe_path = world["repo_root"] / PACKAGE_RELPATH / "analysis-recipe-v1.json"
    recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
    recipe["arms"]["planr"]["scores_sha256"] = _sha(run_dir / f"{RUN_OF['planr']}.scores.json")
    recipe["arms"]["planr"]["outputs_sha256"] = _sha(run_dir / f"{RUN_OF['planr']}.outputs.jsonl")
    _write_json(recipe_path, recipe)
    out = tmp_path / "out"
    assert _run(world, out) == 0
    pins = _load(out, "stop.json")["arms"]["planr"]["seal_pins"]
    assert pins["scores_sha256"]["pinned"] is True
    assert pins["outputs_sha256"]["pinned"] is True
    assert pins["run_manifest_sha256"]["pinned"] is False


def test_refuses_a_row_id_mismatch_between_the_runs(world, tmp_path):
    run_dir = world["data_root"] / "runs" / RUN_OF["exk10"] / ATTEMPT_OF["exk10"]
    path = run_dir / f"{RUN_OF['exk10']}.run-manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["split"]["ids"] = manifest["split"]["ids"][:-1] + ["slurp:train:999999:audio-999999"]
    _write_json(path, manifest)
    with pytest.raises(drv.Var1ReadError, match="does not cover the roster's"):
        drv.run(drv.parse_args(_argv(world, tmp_path / "out")))


def test_refuses_a_roster_hash_disagreement(world, tmp_path):
    facts_path = world["repo_root"] / PACKAGE_RELPATH / "registered-facts-v1.json"
    facts = json.loads(facts_path.read_text(encoding="utf-8"))
    facts["pins"]["roster"]["sha256"] = "b" * 64
    _write_json(facts_path, facts)
    with pytest.raises(drv.Var1ReadError, match="registered facts pin"):
        drv.run(drv.parse_args(_argv(world, tmp_path / "out")))


def test_refuses_a_missing_arm(world, tmp_path):
    recipe_path = world["repo_root"] / PACKAGE_RELPATH / "analysis-recipe-v1.json"
    recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
    recipe["arms"].pop("exdiv")
    _write_json(recipe_path, recipe)
    with pytest.raises(drv.Var1ReadError, match="not the expected family"):
        drv.run(drv.parse_args(_argv(world, tmp_path / "out")))


def test_refuses_a_seed_or_draw_count_the_recipe_did_not_register(world, tmp_path):
    with pytest.raises(drv.Var1ReadError, match="resampling.seed"):
        drv.run(drv.parse_args(_argv(world, tmp_path / "out", "--seed", "1")))
    with pytest.raises(drv.Var1ReadError, match="resampling.draws"):
        drv.run(drv.parse_args(_argv(world, tmp_path / "out-b", "--draws", "37")))


def test_refuses_a_stratum_that_is_not_the_gold_scenario(world, tmp_path):
    document = json.loads(world["roster_path"].read_text(encoding="utf-8"))
    document["items"][0]["stratum"] = "music"
    _write_json(world["roster_path"], document)
    facts_path = world["repo_root"] / PACKAGE_RELPATH / "registered-facts-v1.json"
    facts = json.loads(facts_path.read_text(encoding="utf-8"))
    facts["pins"]["roster"]["sha256"] = _sha(world["roster_path"])
    _write_json(facts_path, facts)
    with pytest.raises(drv.Var1ReadError, match="not the row's gold scenario"):
        drv.run(drv.parse_args(_argv(world, tmp_path / "out")))


def test_refuses_a_sharded_official_scoring_job(world, tmp_path):
    run_dir = world["data_root"] / "runs" / RUN_OF["exk30"] / ATTEMPT_OF["exk30"]
    (run_dir / "score-jobs.jsonl").write_text(
        json.dumps({"job_id": ATTEMPT_OF["exk30"]})
        + "\n"
        + json.dumps({"job_id": ATTEMPT_OF["exk30"] + "-shard-2"})
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    with pytest.raises(drv.Var1ReadError, match="exactly one official scoring job"):
        drv.run(drv.parse_args(_argv(world, tmp_path / "out")))


def test_refuses_a_tampered_exemplar_release(world, tmp_path):
    facts_path = world["repo_root"] / PACKAGE_RELPATH / "registered-facts-v1.json"
    facts = json.loads(facts_path.read_text(encoding="utf-8"))
    facts["pins"]["train_exemplars_release"]["sha256"] = "c" * 64
    _write_json(facts_path, facts)
    with pytest.raises(drv.Var1ReadError, match="pinned exemplar release"):
        drv.run(drv.parse_args(_argv(world, tmp_path / "out")))


def test_main_returns_two_and_prints_a_refusal(world, tmp_path, capsys):
    run_dir = world["data_root"] / "runs" / RUN_OF["perk16c5"] / ATTEMPT_OF["perk16c5"]
    path = run_dir / f"{RUN_OF['perk16c5']}.run-manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["status"] = "FAILED"
    _write_json(path, manifest)
    assert _run(world, tmp_path / "out") == 2
    assert "VAR-1 VARIANT READ REFUSED" in capsys.readouterr().err


# --------------------------------------------------------------------------
# Determinism and the harm rule
# --------------------------------------------------------------------------


def _strip_timestamps(text: str) -> str:
    return "\n".join(
        line
        for line in text.splitlines()
        if "generated_at_utc" not in line and not line.startswith("Generated at:")
    )


def test_two_runs_are_byte_identical_apart_from_the_timestamp(world, tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    assert _run(world, first) == 0
    assert _run(world, second) == 0
    for name in drv.ARTEFACTS:
        left = (first / name).read_text(encoding="utf-8")
        right = (second / name).read_text(encoding="utf-8")
        assert _strip_timestamps(left) == _strip_timestamps(right), name
        if name.endswith(".json"):
            # Exactly one line differs, and it is the timestamp.
            differing = [
                (a, b)
                for a, b in zip(left.splitlines(), right.splitlines())
                if a != b
            ]
            assert all("generated_at_utc" in a for a, _ in differing), name


def test_no_utterance_or_filler_text_is_persisted(completed, world):
    """The harm rule, checked against the fixture's own sentinel and its gold/predicted fillers."""

    blob = "\n".join(
        (completed / name).read_text(encoding="utf-8") for name in drv.ARTEFACTS
    )
    assert SENTINEL_TEXT_MARKER not in blob
    for spec in world["specs"]:
        for entity in world["gold_entities"][spec["sample_id"]]:
            assert entity.filler not in blob
    # The spurious filler exdiv emits must not appear either.
    assert "x0" not in blob.split()
    # Labels, slot TYPE names and ids ARE allowed and must be there.
    assert "alarm" in blob
    assert "date" in blob
    assert RUN_OF["plan"] in blob


def test_two_runs_at_different_worker_counts_are_byte_identical(world, tmp_path):
    """The read's OWN acceptance test for the 2026-09-26 fan-out.

    Every one of this read's twenty-four cluster bootstraps is an independent
    unit handed to ``analysis.parallel.map_by_key``. If a replicate sequence
    ever became a function of how many workers ran it -- a shared RNG, a
    completion-ordered collection, a mutated table -- this is the test that
    fails, and it fails on the bytes rather than on a tolerance.
    """

    one = tmp_path / "workers-1"
    four = tmp_path / "workers-4"
    assert _run(world, one, "--workers", "1") == 0
    assert _run(world, four, "--workers", "4") == 0
    for name in drv.ARTEFACTS:
        left = (one / name).read_text(encoding="utf-8")
        right = (four / name).read_text(encoding="utf-8")
        assert _strip_timestamps(left) == _strip_timestamps(right), name
        differing = [
            (a, b) for a, b in zip(left.splitlines(), right.splitlines()) if a != b
        ]
        assert all(
            "generated_at_utc" in a or a.startswith("Generated at:")
            for a, _ in differing
        ), (name, differing[:3])


def test_the_worker_count_never_reaches_a_recorded_number(world, tmp_path):
    """No artefact may record the worker count: it is not part of the read."""

    out = tmp_path / "out"
    assert _run(world, out, "--workers", "3") == 0
    blob = "\n".join((out / name).read_text(encoding="utf-8") for name in drv.ARTEFACTS)
    assert "workers" not in blob.lower()


def test_contrast_tasks_are_one_flat_batch_of_four_per_arm_pair():
    """The granularity is the BOOTSTRAP, not the arm pair: four keyed tasks per
    pair, named so the collected mapping sorts reviewably. Twenty-four of these
    keys -- four for the own null, twenty for the five variants -- are what the
    read hands to the fan-out."""

    class _Stub:
        def __init__(self, table):
            self.rows_table = table

    ids = tuple(f"row-{index:02d}" for index in range(12))
    # Every sealed count field the two pooled estimands are pooled from, taken
    # from the registry itself so the stub cannot drift from the real tables.
    fields = tuple(
        {field for _, field in drv.ROW_METRICS}
        | {
            name
            for group_key in drv.POOLED_METRICS.values()
            for group in drv.MICRO_METRICS[group_key]
            for name in group
        }
    )
    left = _Stub({sid: {field: 1.0 for field in fields} for sid in ids})
    right = _Stub({sid: {field: 2.0 for field in fields} for sid in ids})
    tasks = drv._contrast_tasks(
        left, right, ids,
        cluster_of=lambda sid: sid, seed=20260915, draws=5, prefix="planr",
    )
    assert sorted(tasks) == [
        "planr|pooled|pooled_slu_f1",
        "planr|pooled|span_f1",
        "planr|row|scenario_action_exact",
        "planr|row|slu_f1_f1",
    ]
    # Independent by construction: run them in either order and they agree.
    ascending = {key: tasks[key]() for key in sorted(tasks)}
    descending = {key: tasks[key]() for key in sorted(tasks, reverse=True)}
    assert ascending == {key: descending[key] for key in ascending}
