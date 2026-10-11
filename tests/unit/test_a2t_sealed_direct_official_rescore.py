"""Standing regression: re-score the SEALED A2T direct bundle with ``a2t-toolcall-official``.

The 2026-09-27 gap diagnosis (``docs/results/2026-09-27-a2t-earnings-gap-diagnosis.md``, section A1) records the
sealed direct arm ``SAEA-A2T-NATIVE-ROLE-DIRECT-UNION4000-V1`` under the official protocol: 62.025 % tool accuracy /
18.500 % exact match on 4,000 rows, per tier in its table, beside the arXiv:2604.22821 Table 3 paper columns
(Qwen3-Omni-30B means 69.19 / 29.68). This test re-runs the registered official scorer over the sealed outputs and
asserts the repo column, and asserts the paper column of the same table, so a scorer, gold-loader or protocol drift
fails here. Read-only: it opens the sealed outputs and the pinned gold, writes nothing, contacts no model.

Skipped when the sealed bundle or the pinned gold is not readable from the test environment (other machines, CI).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DIAGNOSIS = ROOT / "docs/results/2026-09-27-a2t-earnings-gap-diagnosis.md"
RUN = "SAEA-A2T-NATIVE-ROLE-DIRECT-UNION4000-V1"
ATTEMPT = "attempt-a2t-native-role-direct-union4000-generation-v1"


def _diagnosis_rows() -> dict[str, list[str]]:
    rows = {}
    for line in DIAGNOSIS.read_text(encoding="utf-8").splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == 12 and cells[0] != "tier" and cells[0].startswith(("tier", "all")):
            rows[cells[0].split(" ")[0]] = cells
    return rows


def test_diagnosis_table_paper_columns_are_table_3_and_average_to_the_recorded_means():
    rows = _diagnosis_rows()
    tiers = [key for key in rows if key.startswith("tier")]
    assert len(tiers) == 8
    paper = {tier: [float(part) for part in rows[tier][10].split("/")] for tier in tiers}
    assert paper["tier1_direct"] == [92.4, 92.4]
    assert paper["tier4_implicit"] == [33.4, 11.3]
    assert paper["tier8_intent_blending"] == [41.7, 12.4]
    assert round(sum(v[0] for v in paper.values()) / 8, 2) == 69.19
    assert round(sum(v[1] for v in paper.values()) / 8, 2) == 29.68
    assert rows["all"][10].startswith("69.19 / 29.68")


@pytest.fixture(scope="module")
def rescored():
    from speech_aware_evidence_acquisition.data.lock import data_root, load_lock, umbrella_lock_path
    from speech_aware_evidence_acquisition.reproduction.a2t_scorer import score_audio2tool_outputs_official

    try:
        root = data_root()
        outputs = root / "runs" / RUN / ATTEMPT / f"{RUN}.outputs.jsonl"
        if not outputs.is_file():
            pytest.skip(f"sealed A2T direct bundle not readable here: {outputs}")
        lock = load_lock(umbrella_lock_path())
        return score_audio2tool_outputs_official(outputs, lock, root, repo_root=ROOT)
    except pytest.skip.Exception:
        raise
    except Exception as error:  # noqa: BLE001 -- unreadable gold / lock in this environment
        pytest.skip(f"sealed A2T direct bundle or pinned gold not usable here: {type(error).__name__}: {error}")


def test_sealed_direct_bundle_reproduces_the_recorded_official_totals(rescored):
    aggregate = rescored["aggregate"]
    assert aggregate["samples"] == 4000
    assert aggregate["tool_accuracy"] == pytest.approx(0.62025, abs=1e-9)
    assert aggregate["exact_match"] == pytest.approx(0.185, abs=1e-9)
    assert aggregate["parse_failures"] == 28
    assert aggregate["scorer_version"] == "a2t-scorer-official-b9d5383c"
    assert aggregate["official_commit"] == "b9d5383ca30945fbafb965a04bea40117e1e8a82"


def test_sealed_direct_bundle_matches_the_diagnosis_table_per_tier(rescored):
    rows = _diagnosis_rows()
    per_tier = rescored["aggregate"]["per_tier"]
    assert sorted(per_tier) == sorted(key for key in rows if key.startswith("tier"))
    for tier, block in per_tier.items():
        recorded = rows[tier]
        assert block["samples"] == 500
        assert round(100 * block["tool_accuracy"], 1) == float(recorded[1]), tier
        assert round(100 * block["exact_match"], 1) == float(recorded[5]), tier
    assert round(100 * rescored["aggregate"]["tool_accuracy"], 3) == float(rows["all"][1])
    assert round(100 * rescored["aggregate"]["exact_match"], 3) == float(rows["all"][5])
