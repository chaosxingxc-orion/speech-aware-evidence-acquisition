"""Model-free coverage for the tier-1 official-population roster and its
config surface.

Every assertion reads only committed receipts and fragments: no data root,
no media bytes, no model, network, tokenizer or scorer contact.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts/build_a2t_tier1_official_population_roster.py"
SUPPLEMENT_SCRIPT = REPO / "scripts/build_a2t_tier1_official_population_d1_supplement.py"
ROSTER_DIR = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-04-a2t-tier1-official-population-roster"
)
ROSTER = ROSTER_DIR / "flight-roster-receipt.json"
REMAINDER = ROSTER_DIR / "flight-roster-receipt-remainder.json"
PROBE_RECEIPT = REPO / "docs/receipts/probe-samples/a2t-tier1-official-population-500.json"
D1_SUPPLEMENT = REPO / "docs/receipts/artifacts/d1-a2t-tier1-official-population-500.json"
DATASET = REPO / "configs/dataset/audio2tool-tier1-official-population-500.json"
EXPERIMENT = REPO / "configs/experiment/a2t-tier1-official-population-v1.json"
WHITESPACE = REPO / "configs/experiment/a2t-tier1-official-population-whitespace-v1.json"
SMOKE = REPO / "configs/experiment/a2t-tier1-official-population-smoke-v1.json"
WHITESPACE_SMOKE = (
    REPO / "configs/experiment/a2t-tier1-official-population-whitespace-smoke-v1.json"
)


def _module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_roster_identity_and_shape() -> None:
    module = _module(SCRIPT, "a2t_tier1_pop_roster_test")
    roster = _load(ROSTER)
    assert roster["schema"] == "saea-a2t-agentloop-flight-roster-receipt-v1"
    assert roster["carrier"] == "audio2tool"
    assert roster["split_name"] == module.SPLIT_NAMES["draw"]
    assert roster["split_role"] == "discovery"
    assert roster["part"] == "draw"
    assert roster["count"] == module.DRAW_COUNT == len(roster["items"])
    assert roster["tier_counts"] == {module.TIER: module.DRAW_COUNT}
    assert roster["contacts"] == {"audio": 0, "model": 0, "network": 0, "scorer": 0}
    assert roster["selection"]["seed"] == module.DRAW_SEED
    assert roster["selection"]["population_size"] == module.POPULATION_COUNT
    expected_keys = {
        "audio_seconds",
        "audio_sha256",
        "id",
        "key",
        "media_relpath",
        "query_idx",
        "sample_id",
        "tier",
    }
    total = 0.0
    for item in roster["items"]:
        assert set(item) == expected_keys
        assert item["tier"] == module.TIER
        assert item["key"] == f"audio2tool:{item['sample_id']}"
        assert item["sample_id"] == f"{item['tier']}:{int(item['id']):06d}"
        assert len(item["audio_sha256"]) == 64
        assert item["audio_seconds"] > 0
        assert item["media_relpath"].startswith("datasets/audio2tool/public/tier1_direct_audios/")
        total += float(item["audio_seconds"])
    assert roster["audio_seconds_total"] == pytest.approx(total, abs=1e-6)


def test_roster_carries_only_first_speaker_ids_of_distinct_queries() -> None:
    roster = _load(ROSTER)
    query_ids = [item["query_idx"] for item in roster["items"]]
    assert len(set(query_ids)) == len(query_ids), "one row per query, by construction"
    # The release ships two speakers per tier-1 query and the official rule
    # takes the first of them, which is the odd manifest id of the pair.
    assert all(int(item["id"]) % 2 == 1 for item in roster["items"])


def test_roster_identity_hashes_are_both_reproducible() -> None:
    module = _module(SCRIPT, "a2t_tier1_pop_roster_test_hashes")
    roster = _load(ROSTER)
    assert module.sha256_lines(item["key"] for item in roster["items"]) == (
        roster["split_identity_hash"]
    )
    assert module.sha256_lines(
        f"audio2tool/{item['sample_id']}" for item in roster["items"]
    ) == roster["flight_split_identity_hash"]
    assert roster["split_identity_hash"] != roster["flight_split_identity_hash"]


def test_roster_media_hash_is_reproducible() -> None:
    module = _module(SCRIPT, "a2t_tier1_pop_roster_test_media")
    roster = _load(ROSTER)
    rows = [
        {
            "sample_id": item["sample_id"],
            "media_relpath": item["media_relpath"],
            "audio_sha256": item["audio_sha256"],
            "audio_seconds": item["audio_seconds"],
        }
        for item in sorted(roster["items"], key=lambda row: row["sample_id"])
    ]
    assert module.canonical_sha256(rows) == roster["media_roster_sha256"]


def test_draw_and_remainder_partition_the_official_population() -> None:
    module = _module(SCRIPT, "a2t_tier1_pop_roster_test_partition")
    draw = _load(ROSTER)
    remainder = _load(REMAINDER)
    assert remainder["part"] == "remainder"
    assert draw["count"] + remainder["count"] == module.POPULATION_COUNT
    drawn = {item["sample_id"] for item in draw["items"]}
    rest = {item["sample_id"] for item in remainder["items"]}
    assert not (drawn & rest)
    assert len(drawn | rest) == module.POPULATION_COUNT


def test_official_rule_audit_is_recorded_and_clean() -> None:
    module = _module(SCRIPT, "a2t_tier1_pop_roster_test_audit")
    roster = _load(ROSTER)
    population = roster["population"]
    assert population["official_code_commit"] == module.OFFICIAL_CODE_COMMIT
    assert population["query_directories"] == module.POPULATION_COUNT
    audit = population["official_rule_audit"]
    assert audit["performed"] is True
    assert audit["disagreements"] == 0
    assert audit["agreements"] + len(
        audit["query_directories_whose_csv_resolves_no_shipped_wav"]
    ) == module.POPULATION_COUNT
    assert tuple(population["documented_exception"]["query_dirs"]) == (
        module.CSV_MISMATCH_QUERY_DIRS
    )


def test_probe_receipt_is_additive_and_verifiable() -> None:
    module = _module(SCRIPT, "a2t_tier1_pop_roster_test_probe")
    roster = _load(ROSTER)
    receipt = _load(PROBE_RECEIPT)
    assert receipt["carrier"] == "audio2tool"
    assert receipt["split_role"] == "discovery"
    assert receipt["seed"] == module.DRAW_SEED
    assert receipt["n_items"] == len(receipt["items"])
    assert receipt["source_roster_sha256"] == hashlib.sha256(ROSTER.read_bytes()).hexdigest()
    assert module.sha256_lines(item["key"] for item in receipt["items"]) == (
        receipt["split_identity_hash"]
    )
    receipt_ids = {item["key"] for item in receipt["items"]}
    roster_ids = {item["key"] for item in roster["items"]}
    assert receipt_ids <= roster_ids
    covered_elsewhere = {
        key
        for hits in receipt["already_covered_by_other_receipts"].values()
        for key in (f"audio2tool:{sample}" for sample in hits)
    }
    assert receipt_ids | covered_elsewhere == roster_ids
    # No id may appear twice across the committed audio2tool receipts:
    # data.audio2tool._resolve_items refuses a duplicate outright.
    others: set[str] = set()
    for path in sorted((REPO / "docs/receipts/probe-samples").glob("*.json")):
        if path == PROBE_RECEIPT:
            continue
        document = _load(path)
        if document.get("carrier") != "audio2tool":
            continue
        others |= {item["key"] for item in document["items"]}
    assert not (receipt_ids & others)


def test_d1_supplement_covers_every_new_sample_and_no_base_sample() -> None:
    supplement = _load(D1_SUPPLEMENT)
    roster = _load(ROSTER)
    assert supplement["schema"] == "saea-d1-media-supplement-v1"
    assert supplement["carrier_lock_key"] == "audio2tool"
    assert supplement["count"] == len(supplement["manifest"])
    base = _load(REPO / "docs/receipts/artifacts/d1-identity.json")
    base_ids = {
        entry["id"]
        for entry in base["carriers"]["audio2tool"]["layers"]["media"]["manifest"]
    }
    supplement_ids = {entry["id"] for entry in supplement["manifest"]}
    roster_ids = {item["sample_id"] for item in roster["items"]}
    assert not (supplement_ids & base_ids)
    assert supplement_ids | (roster_ids & base_ids) == roster_ids
    assert supplement["source_binding_sha256"] == (
        hashlib.sha256(ROSTER.read_bytes()).hexdigest()
    )
    canonical = json.dumps(
        supplement["manifest"], ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    assert supplement["manifest_sha256"] == hashlib.sha256(canonical).hexdigest()
    assert supplement["ids_sha256"] == hashlib.sha256(
        "\n".join(sorted(supplement_ids)).encode("utf-8")
    ).hexdigest()
    assert supplement["total_bytes"] == sum(
        int(entry["bytes"]) for entry in supplement["manifest"]
    )
    for entry in supplement["manifest"]:
        assert entry["roles"] == ["query"]
        # The Audio2Tool release ships 24 kHz mono 16-bit WAV throughout,
        # despite its README's "all audio is 16 kHz mono" line; the frozen
        # 400 the replication flew is the same, so the two rosters sit on
        # identical footing and the official pipeline's librosa sr=16000
        # resample has the same work to do on both.
        assert entry["sample_rate_hz"] == 24000
        assert entry["audio_seconds"] > 0


def test_dataset_fragment_pins_the_committed_bytes() -> None:
    dataset = _load(DATASET)
    roster = _load(ROSTER)
    assert dataset["carrier_lock_key"] == "audio2tool"
    assert dataset["split_id"] == roster["split_name"]
    assert dataset["a2t_calibration_subset_receipt_sha256"] == (
        hashlib.sha256(ROSTER.read_bytes()).hexdigest()
    )
    assert dataset["d1_media_supplement_sha256"] == (
        hashlib.sha256(D1_SUPPLEMENT.read_bytes()).hexdigest()
    )
    assert dataset["a2t_calibration_count"] == roster["count"]
    assert dataset["a2t_calibration_audio_seconds_total"] == roster["audio_seconds_total"]
    assert dataset["a2t_calibration_split_identity_hash"] == roster["split_identity_hash"]
    assert dataset["a2t_calibration_flight_split_identity_hash"] == (
        roster["flight_split_identity_hash"]
    )


def test_experiment_cells_fragments_and_geometry_agree() -> None:
    """The two cells fly different populations, and contracts.gate_exposure
    allows exactly one pre-registered exposure row per run id whose split
    identity hash equals the plan's -- so each cell is its own run id with
    its own fragment, plan and row."""

    t1 = _load(EXPERIMENT)
    whitespace = _load(WHITESPACE)
    assert t1["experiment_id"] == "SAEA-A2T-TIER1-OFFICIAL-POPULATION-V1"
    assert whitespace["experiment_id"] == "SAEA-A2T-TIER1-OFFICIAL-POPULATION-WHITESPACE-V1"
    assert [c["cell_id"] for c in t1["cells"]] == ["T1-official-pop-500"]
    assert [c["cell_id"] for c in whitespace["cells"]] == ["W-official-raw-yaml"]
    assert t1["companion_run"]["experiment_id"] == whitespace["experiment_id"]
    assert whitespace["companion_run"]["experiment_id"] == t1["experiment_id"]
    cells = {
        cell["cell_id"]: cell for cell in (*t1["cells"], *whitespace["cells"])
    }
    for cell in cells.values():
        baseline = _load(REPO / f"configs/baseline/{cell['baseline_fragment']}.json")
        assert baseline["arm"] == cell["arm"] == "bare-core"
        assert baseline["policy"] == "fixed"
        assert baseline["rails_arms"] == ["zero-supply"]
        assert baseline["scorers"][0] == "a2t-toolcall-official"
        assert baseline["task_instruction_template_active"] is True
        assert baseline["user_turn_text"] == "Convert this voice command to a tool call."
        assert baseline["user_turn_audio_first"] is True
        model = _load(REPO / f"configs/model/{cell['model_fragment']}.json")
        geometry = model["serving_geometry"]
        args = model["server_args"]
        assert int(args[args.index("-np") + 1]) == geometry["slots"]
        assert int(args[args.index("-c") + 1]) == geometry["slots"] * geometry["slot_tokens"]
        assert geometry["slot_tokens"] % 512 == 0
        assert geometry["max_tokens"] == 256
        assert model["decoding_params"]["temperature"] == 0


def test_the_two_cells_differ_only_where_the_experiment_says_they_do() -> None:
    """T1 varies the roster, W varies the system-prompt whitespace; neither
    varies anything else about the request."""

    default = _load(REPO / "configs/baseline/a2t-direct-official-protocol.json")
    yaml_variant = _load(REPO / "configs/baseline/a2t-direct-official-protocol-yaml-prompt.json")
    differing = {
        key
        for key in set(default) | set(yaml_variant)
        if default.get(key) != yaml_variant.get(key)
    }
    assert differing <= {
        "task_instruction_template",
        "protocol_source",
        "protocol_basis",
        "system_prompt_variant_note",
    }
    default_template = (REPO / "configs" / default["task_instruction_template"]).read_text(
        encoding="utf-8"
    )
    yaml_template = (REPO / "configs" / yaml_variant["task_instruction_template"]).read_text(
        encoding="utf-8"
    )
    assert default_template != yaml_template
    assert default_template.split() == yaml_template.split(), "whitespace-only difference"
    assert default["task_instruction_fill"] == yaml_variant["task_instruction_fill"]


def test_yaml_template_is_the_release_config_spelling() -> None:
    template = (REPO / "configs/probes/r1_audio2tool_official_yaml.txt").read_text(
        encoding="utf-8"
    )
    system_prompt = (
        "You are an AI assistant that converts voice commands into tool calls.\n"
        "Listen to the audio and determine which tool should be called.\n"
        "Output ONLY the tool call in the format: tool_name(param1=value1, param2=value2).\n"
        "If no parameters are mentioned, output: tool_name().\n"
    )
    assert hashlib.sha256(system_prompt.encode("utf-8")).hexdigest() == (
        "aa2e344ee52c59019b938926f37498e0dc9c80bd01f6521eba5c3d81309a491d"
    )
    assert template == f"{system_prompt}\n\n## Available Tools:\n" + "{tool_schemas}"
    manifest = _load(REPO / "configs/probes/manifest.json")
    assert manifest["templates"]["r1_audio2tool_official_yaml.txt"]["sha256"] == (
        hashlib.sha256(template.encode("utf-8")).hexdigest()
    )


def test_flight_and_smoke_plans_are_run_cumulative_safe() -> None:
    for path, profile in (
        (EXPERIMENT, "baseline-reproduction"),
        (WHITESPACE, "baseline-reproduction"),
        (SMOKE, "bounded-discovery-probe"),
        (WHITESPACE_SMOKE, "bounded-discovery-probe"),
    ):
        document = _load(path)
        plan = document["execution_plan"]
        assert set(plan) == {
            "execution_profile",
            "split_role",
            "planned_model_calls",
            "planned_gpu_hours",
            "planned_speech_audio_seconds",
        }
        assert plan["execution_profile"] == profile == document["execution_profile"]
        assert plan["split_role"] == "discovery"
        assert isinstance(plan["planned_model_calls"], int)
        assert isinstance(plan["planned_speech_audio_seconds"], int)
        if "populations" in document:
            populations = list(document["populations"].values())
            assert len(populations) == 1
            rows = populations[0]["count"]
            audio = populations[0]["audio_seconds_one_pass"]
        else:
            populations = list(document["smoke_populations"].values())
            assert len(populations) == 1
            rows = len(populations[0]["sample_ids"])
            audio = populations[0]["audio_seconds_one_pass"]
        assert plan["planned_model_calls"] >= rows
        assert plan["planned_speech_audio_seconds"] >= math.ceil(audio)


def test_smoke_rows_come_from_the_rosters_they_name() -> None:
    smoke = _load(SMOKE)
    whitespace_smoke = _load(WHITESPACE_SMOKE)
    roster_ids = {item["sample_id"] for item in _load(ROSTER)["items"]}
    t1 = smoke["smoke_populations"]["T1-official-pop-500"]
    assert set(t1["sample_ids"]) <= roster_ids
    by_seconds = {
        item["sample_id"]: item["audio_seconds"] for item in _load(ROSTER)["items"]
    }
    longest = max(by_seconds, key=lambda name: (by_seconds[name], name))
    assert longest in t1["sample_ids"], "the smoke must fly the roster's longest wav"
    assert t1["audio_seconds_one_pass"] == pytest.approx(
        sum(by_seconds[name] for name in t1["sample_ids"]), abs=1e-6
    )
    calibration = {
        item["sample_id"]
        for item in _load(
            REPO
            / "docs/checks/speech-aware-evidence-acquisition"
            / "2026-09-04-a2t-calibration-400-roster/flight-roster-receipt.json"
        )["items"]
    }
    assert set(
        whitespace_smoke["smoke_populations"]["W-official-raw-yaml"]["sample_ids"]
    ) <= calibration


def test_d1_supplement_builder_skips_rather_than_refuses_base_overlap() -> None:
    """The AgentLoop builder REFUSES any parent-D1 overlap because its roster
    was drawn fresh. A uniform draw over the whole tier-1 population cannot
    promise that, and contracts.gate_media_identity refuses a supplement that
    duplicates a base D1 sample, so this builder skips those ids instead."""

    module = _module(SUPPLEMENT_SCRIPT, "a2t_tier1_pop_d1_test")
    source = SUPPLEMENT_SCRIPT.read_text(encoding="utf-8")
    assert "skipped.append(sample_id)" in source
    assert module.CARRIER == "audio2tool"
    assert module.DEFAULT_OUTPUT.name == "d1-a2t-tier1-official-population-500.json"
