"""Tests for the sealed-input G6 result analyzer."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest

from speech_aware_evidence_acquisition.reproduction.toolcall_scoring import ToolCall


REPO = Path(__file__).resolve().parents[2]
SCRIPT = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-02-a2t-g6-result-analysis/analyze.py"
)


def _module():
    spec = importlib.util.spec_from_file_location("g6_result_analysis", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _corpus() -> dict[str, object]:
    contracts = []
    families = []
    for index in range(28):
        family = f"family-{index:02d}"
        tool = f"tool{index:02d}"
        contract_id = f"contract-{index:02d}"
        contracts.append(
            {
                "contract_id": contract_id,
                "family_tag": family,
                "tool_name": tool,
                "legal_key_skeletons": [["target"]],
            }
        )
        families.append(
            {
                "tag": family,
                "contract_ids": [contract_id],
                "tool_names": [tool],
            }
        )
    return {"contracts": contracts, "families": families}


def _scan_rows(module, *, missed_tool_id: str | None = None) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for sample_id in module.G6_IDS:
        for index in range(28):
            family = f"family-{index:02d}"
            nominate = index == 0 and sample_id != missed_tool_id
            report = {
                "applicable": nominate,
                "candidates": (
                    [
                        {
                            "tool_name": "tool00",
                            "speech_spans": ["Alice"],
                            "argument_bindings": [
                                {
                                    "key": "target",
                                    "value": "Alice",
                                    "speech_span": "Alice",
                                }
                            ],
                            "unresolved_required_arguments": [],
                        }
                    ]
                    if nominate
                    else []
                ),
                "correction_evidence": [],
                "turn_evidence": [],
                "role_evidence": [],
                "ordering_evidence": [],
            }
            rows.append(
                {
                    "sample_id": sample_id,
                    "nonfinal": True,
                    "stage": "SCAN",
                    "contact": {
                        "sample_id": sample_id,
                        "contact_id": f"g6-scan-{family}",
                        "stage": "SCAN",
                        "family_tag": family,
                    },
                    "report": {
                        "family_tag": family,
                        "valid": True,
                        "status": "VALID",
                        "canonical_json": json.dumps(
                            report, separators=(",", ":"), sort_keys=True
                        ),
                    },
                }
            )
    return rows


def _score_text(tool: str = "tool00", value: str = "Alice") -> str:
    return json.dumps([{"name": tool, "arguments": {"target": value}}])


def test_frozen_roster_and_m0_identity_are_exact() -> None:
    module = _module()

    assert module.G6_IDS == (
        "tier1_direct:000077",
        "tier1_direct:004159",
        "tier2_parametric:001004",
        "tier2_parametric:002653",
        "tier3_multi_intent:001424",
        "tier3_multi_intent:003058",
        "tier4_implicit:000655",
        "tier4_implicit:001010",
        "tier5_needle:001458",
        "tier5_needle:004242",
        "tier6_correction:001764",
        "tier6_correction:002430",
        "tier7_multiturn:000440",
        "tier7_multiturn:001516",
        "tier8_intent_blending:000192",
        "tier8_intent_blending:000213",
    )
    assert module.M0_RELPATH.as_posix() == (
        "runs/SAEA-A2T-G1/attempt-20260825T100735Z-a2tg1m0/"
        "arm1-m0-outputs.jsonl"
    )
    assert module.M0_SHA256 == (
        "dea60ff1e63fd2ef11c93edf8808217062fea3f0565ed5b60f136264bc6a9467"
    )


def test_score_and_micro_aggregate_match_official_semantics() -> None:
    module = _module()
    expected = (ToolCall("tool00", {"target": "Alice"}),)

    exact = module.score_row({"text": _score_text()}, expected)
    wrong = module.score_row({"final_response_text": _score_text(value="Bob")}, expected)

    assert exact["exact"] == 1
    assert exact["tool"] == 1
    assert wrong["exact"] == 0
    assert wrong["tool"] == 1
    aggregate = module.aggregate_view([exact, wrong])
    assert aggregate["exact_count"] == 1
    assert aggregate["tool_count"] == 2
    assert aggregate["slot_true_positives"] == 1
    assert aggregate["slot_expected_total"] == 2
    assert aggregate["slot_predicted_total"] == 2
    assert aggregate["slot_f1"] == 0.5


def test_analysis_reports_pairing_tiers_scan_mediators_and_bottleneck() -> None:
    module = _module()
    expected = {
        sample_id: (ToolCall("tool00", {"target": "Alice"}),)
        for sample_id in module.G6_IDS
    }
    g6 = {sample_id: {"sample_id": sample_id, "text": _score_text()} for sample_id in module.G6_IDS}
    m0 = {
        sample_id: {
            "sample_id": sample_id,
            "final_response_text": (
                _score_text(value="Bob") if index == 0 else _score_text()
            ),
        }
        for index, sample_id in enumerate(module.G6_IDS)
    }
    missed_id = module.G6_IDS[1]
    g6[missed_id] = {"sample_id": missed_id, "text": "[]"}

    result = module.build_analysis(
        g6_rows=g6,
        m0_rows=m0,
        expected_by_id=expected,
        scan_rows=_scan_rows(module, missed_tool_id=missed_id),
        corpus_document=_corpus(),
        sources={"fixture": True},
    )

    assert result["schema"] == "saea-a2t-g6-fixed16-result-analysis-v1"
    assert result["aggregate"]["g6"]["exact_count"] == 15
    assert result["aggregate"]["paired_exact"] == {"win": 1, "loss": 1, "tie": 14}
    assert result["aggregate"]["scan"]["total"] == 448
    assert result["aggregate"]["scan"]["valid"] == 448
    assert result["aggregate"]["scan"]["applicable"] == 15
    assert result["aggregate"]["scan"]["nominations"] == 15
    assert result["aggregate"]["gold_family_coverage_rows"] == 15
    assert result["aggregate"]["selected_contract_coverage_rows"] == 15
    assert result["aggregate"]["resolver_valid_rows"] == 15
    assert result["aggregate"]["bottlenecks"] == {
        "exact": 15,
        "scan-missed-gold-family": 1,
    }
    assert set(result["aggregate"]["per_tier"]) == {
        sample_id.split(":", 1)[0] for sample_id in module.G6_IDS
    }
    first = result["rows"][0]
    assert first["gold_families"] == ["family-00"]
    assert first["gold_tools_nominated"] == [True]
    assert first["gold_contracts_selected"] == [True]
    assert first["resolver_valid"] is True


@pytest.mark.parametrize(
    ("facts", "expected"),
    [
        ({"exact": True}, "exact"),
        ({"gold_family_valid": False}, "scan-invalid-gold-family"),
        ({"gold_family_applicable": False}, "scan-missed-gold-family"),
        ({"gold_tools_selected": False}, "scan-missed-gold-tool"),
        ({"resolver_valid": False}, "resolver-invalid"),
        ({"tool": False}, "resolver-selection"),
        ({"exact": False, "tool": True}, "argument-realization"),
    ],
)
def test_bottleneck_precedence(facts: dict[str, bool], expected: str) -> None:
    module = _module()
    complete = {
        "exact": False,
        "tool": True,
        "gold_family_valid": True,
        "gold_family_applicable": True,
        "gold_tools_selected": True,
        "resolver_valid": True,
    }
    assert module.classify_bottleneck({**complete, **facts}) == expected


def test_scan_surface_fails_closed_on_missing_or_duplicate_family() -> None:
    module = _module()
    rows = _scan_rows(module)
    with pytest.raises(RuntimeError, match="448"):
        module.validate_scan_rows(rows[:-1], _corpus())

    duplicate = list(rows)
    duplicate[-1] = duplicate[-2]
    with pytest.raises(RuntimeError, match="duplicate"):
        module.validate_scan_rows(duplicate, _corpus())


def _transport_records(module, *, recovered_id: str) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for sample_id in module.G6_IDS:
        for index in range(28):
            family = f"family-{index:02d}"
            contact_id = f"g6-scan-{family}"
            base = f"{sample_id}-{contact_id}"
            raw = json.dumps(
                {
                    "applicable": False,
                    "candidates": [],
                    "correction_evidence": [],
                    "turn_evidence": [],
                    "role_evidence": [],
                    "ordering_evidence": [],
                },
                separators=(",", ":"),
            )
            if sample_id == recovered_id and index == 0:
                raw = json.dumps(
                    {
                        "applicable": True,
                        "candidates": [
                            {
                                "tool_name": "tool00",
                                "speech_spans": ["Alice"],
                                "argument_bindings": [],
                                "unresolved_required_arguments": [],
                            }
                        ],
                        "correction_evidence": [],
                        "turn_evidence": [],
                        "role_evidence": [],
                        "ordering_evidence": {},
                    },
                    separators=(",", ":"),
                )
            records.extend(
                [
                    {
                        "channel": "MODEL_REQUEST",
                        "record_id": f"{base}/request",
                        "payload": {
                            "payload": {
                                "sample_id": sample_id,
                                "history": [{"contact_id": contact_id}],
                            }
                        },
                    },
                    {
                        "channel": "MODEL_RESPONSE",
                        "record_id": f"{base}/response",
                        "payload": {"text": raw},
                    },
                    {"channel": "COST", "record_id": f"{base}/cost", "payload": {}},
                ]
            )
        base = f"{sample_id}-g6-resolve"
        records.extend(
            [
                {
                    "channel": "MODEL_REQUEST",
                    "record_id": f"{base}/request",
                    "payload": {
                        "payload": {
                            "sample_id": sample_id,
                            "history": [{"contact_id": "g6-resolve"}],
                        }
                    },
                },
                {
                    "channel": "MODEL_RESPONSE",
                    "record_id": f"{base}/response",
                    "payload": {
                        "text": '[{"name":"invented","arguments":{}}]'
                    },
                },
                {"channel": "COST", "record_id": f"{base}/cost", "payload": {}},
            ]
        )
    return records


def test_raw_transport_diagnostic_is_separate_from_official_scan_state() -> None:
    module = _module()
    recovered_id = module.G6_IDS[0]
    expected = {
        sample_id: (ToolCall("tool00", {"target": "Alice"}),)
        for sample_id in module.G6_IDS
    }

    diagnostic = module.build_raw_transport_diagnostic(
        transport_rows=_transport_records(module, recovered_id=recovered_id),
        scan_rows=_scan_rows(module, missed_tool_id=recovered_id),
        corpus_document=_corpus(),
        expected_by_id=expected,
    )

    assert diagnostic["contacts"] == {"scan": 448, "resolve": 16, "total": 464}
    assert diagnostic["nonempty_response_texts"] == 464
    assert diagnostic["scan"]["official_valid"] == 448
    assert diagnostic["scan"]["raw_applicable_true"] == 1
    assert diagnostic["scan"]["raw_candidate_count"] == 1
    assert diagnostic["scan"]["raw_registered_family_local_nominations"] == 1
    assert diagnostic["diagnostic_ceiling"]["gold_family_applicable_rows"] == 1
    assert diagnostic["diagnostic_ceiling"]["gold_tool_nominated_rows"] == 1
    assert diagnostic["diagnostic_ceiling"]["rows"][0] == {
        "sample_id": recovered_id,
        "gold_family_applicable": True,
        "gold_tool_nominated": True,
    }
    assert diagnostic["resolve"]["raw_call_count"] == 16
    assert diagnostic["resolve"]["raw_registered_call_count"] == 0
    assert diagnostic["resolve"]["raw_unregistered_call_count"] == 16
    assert diagnostic["scope_note"].startswith("Diagnostic only")


def test_transport_diagnostic_requires_complete_unique_contact_triples() -> None:
    module = _module()
    expected = {
        sample_id: (ToolCall("tool00", {"target": "Alice"}),)
        for sample_id in module.G6_IDS
    }
    records = _transport_records(module, recovered_id=module.G6_IDS[0])

    with pytest.raises(RuntimeError, match="1392"):
        module.build_raw_transport_diagnostic(
            transport_rows=records[:-1],
            scan_rows=_scan_rows(module),
            corpus_document=_corpus(),
            expected_by_id=expected,
        )


def test_cli_writes_one_source_bound_analysis(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _module()
    root = tmp_path / "data"
    repo = tmp_path / "repo"
    m0_path = root / module.M0_RELPATH
    corpus_path = repo / module.CORPUS_RELPATH
    g6_path = tmp_path / "g6.jsonl"
    scans_path = tmp_path / "scans.jsonl"
    transport_path = tmp_path / "transport.jsonl"
    out_path = tmp_path / "result" / "analysis.json"
    m0_path.parent.mkdir(parents=True)
    corpus_path.parent.mkdir(parents=True)

    def write_jsonl(path: Path, rows: object) -> None:
        path.write_text(
            "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
        )

    outputs = [
        {"sample_id": sample_id, "text": _score_text()}
        for sample_id in module.G6_IDS
    ]
    write_jsonl(g6_path, outputs)
    write_jsonl(
        m0_path,
        [
            {"sample_id": sample_id, "final_response_text": _score_text()}
            for sample_id in module.G6_IDS
        ],
    )
    write_jsonl(scans_path, _scan_rows(module))
    write_jsonl(
        transport_path,
        _transport_records(module, recovered_id=module.G6_IDS[0]),
    )
    corpus_path.write_text(json.dumps(_corpus()), encoding="utf-8")
    expected = {
        sample_id: (ToolCall("tool00", {"target": "Alice"}),)
        for sample_id in module.G6_IDS
    }
    monkeypatch.setattr(module, "REPO", repo)
    monkeypatch.setattr(module, "data_root", lambda: root)
    monkeypatch.setattr(module, "load_lock", lambda _: {})
    monkeypatch.setattr(module, "umbrella_lock_path", lambda _: tmp_path / "lock.json")
    monkeypatch.setattr(module, "load_expected_calls", lambda *args, **kwargs: expected)
    monkeypatch.setattr(
        module,
        "sha256_file",
        lambda path: (
            module.M0_SHA256
            if Path(path) == m0_path
            else module.CORPUS_SHA256
            if Path(path) == corpus_path
            else "fixture-sha256"
        ),
    )

    assert (
        module.main(
            [
                "--g6-outputs",
                str(g6_path),
                "--g6-scan-states",
                str(scans_path),
                "--transport-trace",
                str(transport_path),
                "--out",
                str(out_path),
            ]
        )
        == 0
    )
    written = json.loads(out_path.read_text(encoding="utf-8"))
    assert written["aggregate"]["g6"]["exact_count"] == 16
    assert written["raw_transport_diagnostic"]["contacts"]["total"] == 464
    with pytest.raises(RuntimeError, match="overwrite"):
        module.main(
            [
                "--g6-outputs",
                str(g6_path),
                "--g6-scan-states",
                str(scans_path),
                "--transport-trace",
                str(transport_path),
                "--out",
                str(out_path),
            ]
        )
