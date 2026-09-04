#!/usr/bin/env python3
"""Zero-contact re-score of sealed Audio2Tool manifests under the extended parse.

Two questions, both answered from bytes that prior, separately-registered
runs already wrote. No model, GPU, embedding or network contact; gold enters
only through the registered scorers, exactly as it does when a flight
finalizes.

**Question 1 -- did the parse extension move anything that was already
sealed?** ``reproduction.toolcall_scoring.parse_tool_calls_text`` now reads
the released benchmark's call-string contract as well as this repository's
reconstructed JSON-array contract, JSON first. A JSON-array row therefore
parses byte-identically to before, but a row that previously failed to parse
may now succeed. This script re-scores every sealed Audio2Tool manifest with
``a2t-toolcall`` and ``a2t-toolcall-v2`` and reports, per manifest, whether
the aggregate reproduces its sealed value and by how much it moves when it
does not.

**Question 2 -- how far apart are our scorer and the official one on the same
outputs?** For the manifests that flew the published protocol, the script
tabulates the official scorer beside the extended ``a2t-toolcall-v2`` per
tier -- tool accuracy, exact match and the parameter/slot F1 each defines --
with the difference, and attributes any gap larger than the owner's 3-point
alignment band to a NAMED rule difference between the two scorers.

Usage (WSL2, model-free)::

    python scripts/a2t_parse_extension_rescore.py
    python scripts/a2t_parse_extension_rescore.py --write
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Mapping, Sequence

REPO = Path(__file__).resolve().parents[1]

OUT_DIR = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-04-a2t-parse-extension-rescore"
)

#: Sealed Audio2Tool manifests this study reads, and the output contract each
#: cell's prompt asked for.
SEALED = (
    {
        "run_id": "SAEA-A2T-OFFICIAL-PROTOCOL-REPLICATION-V1",
        "attempt": "attempt-20260904T135250Z-rofficialraw",
        "cell": "R-official-raw",
        "contract": "call-string (the released protocol)",
        "official_protocol": True,
    },
    {
        "run_id": "SAEA-A2T-DIRECT-CALIBRATION-V1",
        "attempt": "attempt-20260904T081627Z-a0primelegacyraw",
        "cell": "A0prime-legacy-raw",
        "contract": "JSON array (this repository's reconstruction)",
        "official_protocol": False,
    },
    {
        "run_id": "SAEA-A2T-DIRECT-CALIBRATION-V1",
        "attempt": "attempt-20260904T083403Z-p0legacypackets",
        "cell": "P0-legacy-packets",
        "contract": "JSON array (this repository's reconstruction)",
        "official_protocol": False,
    },
    {
        "run_id": "SAEA-A2T-DIRECT-CALIBRATION-V1",
        "attempt": "attempt-20260904T081627Z-a1nativeraw",
        "cell": "A1-native-raw",
        "contract": "native tools list; free-form text answers",
        "official_protocol": False,
    },
    {
        "run_id": "SAEA-A2T-DIRECT-CALIBRATION-V1",
        "attempt": "attempt-20260904T083403Z-p1nativepackets",
        "cell": "P1-native-packets",
        "contract": "native tools list; free-form text answers",
        "official_protocol": False,
    },
)

TIERS = (
    "tier1_direct",
    "tier2_parametric",
    "tier3_multi_intent",
    "tier4_implicit",
    "tier5_needle",
    "tier6_correction",
    "tier7_multiturn",
    "tier8_intent_blending",
)

#: The owner's 2026-09-04 alignment band, in percentage points.
ALIGNMENT_BAND_PP = 3.0

#: Every structural difference between ``a2t-toolcall-official`` and
#: ``a2t-toolcall-v2``. A gap wider than the alignment band is attributed to
#: the ones that can produce it, so the table names a rule instead of a
#: number.
SCORER_RULE_DIFFERENCES = {
    "first_call_only_vs_ordered_sequence": (
        "The official HF path never populates all_tool_calls, so the official "
        "scorer reads ONLY the first parsed call and compares it with the primary "
        "gold tool. a2t-toolcall-v2 compares the whole ORDERED sequence of "
        "predicted calls with the whole expected sequence, so a row that names "
        "the right first tool and then a second one, or names one tool where gold "
        "expects two, is correct for the official scorer and wrong for v2. This is "
        "the dominant rule on the multi-call tiers (3, 8) and on any tier where "
        "the model volunteers a second call."
    ),
    "primary_gold_tool_vs_full_expected_sequence": (
        "Official gold is data.audio2tool.load_official_gold -- the release's own "
        "QuerySample: a primary tool_name plus verbatim extracted_params, with "
        "additional_tool_calls used only by the separate multi-tool metric. v2 gold "
        "is a2t-gold-v1, which builds the full expected call sequence and may take "
        "primary arguments from the expected_tool_call CALL STRING. The two are "
        "different gold objects, not two readings of one."
    ),
    "default_argument_credit": (
        "v2 (rule V2b) DROPS a predicted argument key that no same-tool gold call "
        "carries when its value equals that tool's tools_registry.csv default; the "
        "official scorer counts every extra key as a parameter error and therefore "
        "as an exact-match failure. This is why v2 exact match runs far above the "
        "official figure on tiers whose gold is argument-free -- tier 1 above all."
    ),
    "numeric_and_boolean_coercion": (
        "v2 (rule V2d) compares a numeric-looking string to its numeric value and "
        "'true'/'false' to the matching boolean. The official normalize_parameters "
        "reaches a similar place by a different route (int/float -> str(v), "
        "everything else -> str(v).strip().lower()), so this rule rarely separates "
        "the two on its own; it is listed because it can, when gold carries a value "
        "whose str() and float() spellings differ (e.g. 50 vs 50.0)."
    ),
    "parameter_f1_definition": (
        "The official parameter F1 is per-sample precision/recall over gold KEYS "
        "and their values, averaged over samples (a macro average, despite the "
        "paper's prose). v2's slot F1 is micro over (tool, key, value) TRIPLES "
        "across the manifest, so the two numbers answer different questions and "
        "are never expected to agree; they are reported side by side, not "
        "differenced for alignment."
    ),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_dir(run_id: str, attempt: str) -> Path:
    from speech_aware_evidence_acquisition.data.lock import data_root

    return Path(data_root()) / "runs" / run_id / attempt


def _sealed_scores(run_id: str, attempt: str) -> Mapping[str, object]:
    path = run_dir(run_id, attempt) / f"{run_id}.scores.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _sealed_aggregate(scores: Mapping[str, object], scorer: str) -> Mapping[str, object] | None:
    """The sealed aggregate for one scorer, wherever the manifest keeps it."""

    def walk(node: object) -> Mapping[str, object] | None:
        if isinstance(node, Mapping):
            if scorer in node and isinstance(node[scorer], Mapping):
                candidate = node[scorer]
                if "aggregate" in candidate and isinstance(candidate["aggregate"], Mapping):
                    return candidate["aggregate"]
                return candidate
            for value in node.values():
                found = walk(value)
                if found is not None:
                    return found
        elif isinstance(node, list):
            for value in node:
                found = walk(value)
                if found is not None:
                    return found
        return None

    return walk(scores)


def rescore(run_id: str, attempt: str, scorer: str) -> Mapping[str, object]:
    from speech_aware_evidence_acquisition.data.lock import (
        data_root,
        load_lock,
        umbrella_lock_path,
    )
    from speech_aware_evidence_acquisition.core.base import SCORERS
    import speech_aware_evidence_acquisition.core.scorers  # noqa: F401  (registers)

    outputs = run_dir(run_id, attempt) / f"{run_id}.outputs.jsonl"
    return SCORERS.resolve(scorer)(outputs, load_lock(umbrella_lock_path()), data_root())


def _pct(value: object) -> float:
    return round(100.0 * float(value), 4)


def reproduction_report(entry: Mapping[str, object]) -> dict[str, object]:
    """Whether the extended parse reproduces this manifest's sealed v1/v2
    aggregates, and by how much it moves them when it does not."""

    run_id = str(entry["run_id"])
    attempt = str(entry["attempt"])
    sealed = _sealed_scores(run_id, attempt)
    rows: dict[str, object] = {}
    for scorer, keys in (
        ("a2t-toolcall", ("tool_accuracy", "exact_match", "slot_f1", "parse_failures")),
        (
            "a2t-toolcall-v2",
            ("tool_accuracy", "tool_accuracy_multiset", "exact_match", "slot_f1", "parse_failures"),
        ),
    ):
        sealed_aggregate = _sealed_aggregate(sealed, scorer)
        fresh = rescore(run_id, attempt, scorer)["aggregate"]
        comparison: dict[str, object] = {}
        for key in keys:
            before = sealed_aggregate.get(key) if sealed_aggregate else None
            after = fresh.get(key)
            comparison[key] = {
                "sealed": before,
                "extended_parse": after,
                "changed": (
                    None
                    if before is None
                    else (abs(float(before) - float(after)) > 1e-12)
                ),
            }
        rows[scorer] = {
            "sealed_aggregate_found": sealed_aggregate is not None,
            "fields": comparison,
            "reproduces_sealed": all(
                field["changed"] is False for field in comparison.values()
            ),
        }
    return {
        "cell_id": entry["cell"],
        "run_id": run_id,
        "attempt_id": attempt,
        "output_contract": entry["contract"],
        "scorers": rows,
    }


def alignment_table(entry: Mapping[str, object]) -> dict[str, object]:
    """Official scorer beside the extended v2 on the same sealed outputs."""

    run_id = str(entry["run_id"])
    attempt = str(entry["attempt"])
    official = rescore(run_id, attempt, "a2t-toolcall-official")
    v2 = rescore(run_id, attempt, "a2t-toolcall-v2")
    official_tiers = official["aggregate"]["per_tier"]
    v2_tiers = v2["aggregate"]["per_tier"]

    rows: list[dict[str, object]] = []
    for tier in TIERS:
        if tier not in official_tiers:
            continue
        o = official_tiers[tier]
        v = v2_tiers[tier]
        tool_delta = _pct(v["tool_accuracy"]) - _pct(o["tool_accuracy"])
        em_delta = _pct(v["exact_match"]) - _pct(o["exact_match"])
        rows.append(
            {
                "tier": tier,
                "samples": o["samples"],
                "official_tool_accuracy": _pct(o["tool_accuracy"]),
                "v2_tool_accuracy_ordered": _pct(v["tool_accuracy"]),
                "v2_tool_accuracy_multiset": _pct(v["tool_accuracy_multiset"]),
                "tool_accuracy_delta_v2_minus_official": round(tool_delta, 4),
                "tool_accuracy_within_band": abs(tool_delta) <= ALIGNMENT_BAND_PP,
                "official_exact_match": _pct(o["exact_match"]),
                "v2_exact_match": _pct(v["exact_match"]),
                "exact_match_delta_v2_minus_official": round(em_delta, 4),
                "exact_match_within_band": abs(em_delta) <= ALIGNMENT_BAND_PP,
                "official_param_f1_macro": _pct(o["param_f1"]),
                "official_param_f1_micro": _pct(o["param_f1_micro"]),
                "v2_slot_f1_micro": _pct(v["slot_f1"]),
                "v2_slot_f1_raw_micro": _pct(v["slot_f1_raw"]),
                "official_parse_rate": _pct(o["parse_rate"]),
                "v2_parse_failures": v["parse_failures"] if "parse_failures" in v else None,
                "official_rows_with_multiple_call_matches": o[
                    "rows_with_multiple_call_matches"
                ],
                "rules_that_can_explain_a_gap": _attribute(tool_delta, em_delta, o),
            }
        )

    overall_tool_delta = _pct(v2["aggregate"]["tool_accuracy"]) - _pct(
        official["aggregate"]["tool_accuracy"]
    )
    overall_em_delta = _pct(v2["aggregate"]["exact_match"]) - _pct(
        official["aggregate"]["exact_match"]
    )
    return {
        "cell_id": entry["cell"],
        "run_id": run_id,
        "attempt_id": attempt,
        "alignment_band_pp": ALIGNMENT_BAND_PP,
        "per_tier": rows,
        "overall": {
            "samples": official["aggregate"]["samples"],
            "official_tool_accuracy": _pct(official["aggregate"]["tool_accuracy"]),
            "v2_tool_accuracy_ordered": _pct(v2["aggregate"]["tool_accuracy"]),
            "v2_tool_accuracy_multiset": _pct(v2["aggregate"]["tool_accuracy_multiset"]),
            "tool_accuracy_delta_v2_minus_official": round(overall_tool_delta, 4),
            "official_exact_match": _pct(official["aggregate"]["exact_match"]),
            "v2_exact_match": _pct(v2["aggregate"]["exact_match"]),
            "exact_match_delta_v2_minus_official": round(overall_em_delta, 4),
            "official_param_f1_macro": _pct(official["aggregate"]["param_f1"]),
            "official_param_f1_micro": _pct(official["aggregate"]["param_f1_micro"]),
            "v2_slot_f1_micro": _pct(v2["aggregate"]["slot_f1"]),
            "official_parse_rate": _pct(official["aggregate"]["parse_rate"]),
            "v2_parse_failures": v2["aggregate"]["parse_failures"],
            "official_rows_with_multiple_call_matches": official["aggregate"][
                "rows_with_multiple_call_matches"
            ],
            "v2_extra_keys_stripped": v2["aggregate"]["extra_keys_stripped"],
            "v2_coerced_values": v2["aggregate"]["coerced_values"],
        },
        "scorer_versions": {
            "official": official["aggregate"]["scorer_version"],
            "official_commit": official["aggregate"]["official_commit"],
            "v2": v2["aggregate"]["scorer_version"],
            "parse": v2["aggregate"]["parse_version"],
            "official_gold": official["aggregate"]["gold_version"],
            "v2_gold": v2["aggregate"]["gold_version"],
        },
    }


def _attribute(
    tool_delta: float, em_delta: float, official_tier: Mapping[str, object]
) -> list[str]:
    """Which named rule differences can produce the gaps on this tier."""

    named: list[str] = []
    if abs(tool_delta) > ALIGNMENT_BAND_PP:
        named.append("first_call_only_vs_ordered_sequence")
        if int(official_tier.get("multi_tool_samples", 0)) > 0:
            named.append("primary_gold_tool_vs_full_expected_sequence")
    if abs(em_delta) > ALIGNMENT_BAND_PP:
        named.append("default_argument_credit")
        named.append("primary_gold_tool_vs_full_expected_sequence")
    seen: list[str] = []
    for name in named:
        if name not in seen:
            seen.append(name)
    return seen


def build(*, entries: Sequence[Mapping[str, object]]) -> dict[str, object]:
    reproduction = [reproduction_report(entry) for entry in entries]
    alignment = [
        alignment_table(entry) for entry in entries if entry.get("official_protocol")
    ]
    from speech_aware_evidence_acquisition.reproduction.toolcall_scoring import (
        A2T_PARSE_VERSION,
    )

    return {
        "schema": "saea-a2t-parse-extension-rescore-v1",
        "study": "speech-aware-evidence-acquisition",
        "run_id": "SAEA-A2T-MF-PARSE-EXTENSION-RESCORE-V1",
        "parse_version": A2T_PARSE_VERSION,
        "boundary": (
            "zero model, GPU, embedding and network contact. Every number is computed "
            "from outputs JSONL files that prior, separately-registered runs already "
            "sealed; gold enters only through the registered scorers, exactly as it "
            "does when a flight finalizes."
        ),
        "question_1_sealed_reproduction": {
            "claim": (
                "the extended parse tries JSON first, so a row that parsed before parses "
                "identically now; only a row that PREVIOUSLY FAILED to parse can move"
            ),
            "manifests": reproduction,
        },
        "question_2_official_vs_v2_alignment": {
            "claim": (
                "the same sealed outputs and the same rows, read by the dataset's "
                "standard scorer and by this repository's current scorer, per tier, with "
                "every gap wider than the owner's 3-point band attributed to a named rule"
            ),
            "rule_differences": SCORER_RULE_DIFFERENCES,
            "cells": alignment,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args()

    document = build(entries=SEALED)
    payload = json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.write:
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "rescore.json"
        out_path.write_text(payload, encoding="utf-8", newline="\n")
        print("written: %s (sha256 %s)" % (out_path, sha256_file(out_path)))

    for manifest in document["question_1_sealed_reproduction"]["manifests"]:
        for scorer, row in manifest["scorers"].items():
            print(
                "%-20s %-16s reproduces_sealed=%s"
                % (manifest["cell_id"], scorer, row["reproduces_sealed"])
            )
            for key, field in row["fields"].items():
                if field["changed"]:
                    print(
                        "    %-24s sealed=%s -> extended=%s"
                        % (key, field["sealed"], field["extended_parse"])
                    )
    for cell in document["question_2_official_vs_v2_alignment"]["cells"]:
        print()
        print("official vs v2 on %s (n=%s)" % (cell["cell_id"], cell["overall"]["samples"]))
        print(
            "%-24s %8s %8s %8s   %8s %8s %8s"
            % ("tier", "off TA", "v2 TA", "dTA", "off EM", "v2 EM", "dEM")
        )
        for row in cell["per_tier"]:
            print(
                "%-24s %8.1f %8.1f %+8.1f   %8.1f %8.1f %+8.1f"
                % (
                    row["tier"],
                    row["official_tool_accuracy"],
                    row["v2_tool_accuracy_ordered"],
                    row["tool_accuracy_delta_v2_minus_official"],
                    row["official_exact_match"],
                    row["v2_exact_match"],
                    row["exact_match_delta_v2_minus_official"],
                )
            )
        overall = cell["overall"]
        print(
            "%-24s %8.2f %8.2f %+8.2f   %8.2f %8.2f %+8.2f"
            % (
                "overall",
                overall["official_tool_accuracy"],
                overall["v2_tool_accuracy_ordered"],
                overall["tool_accuracy_delta_v2_minus_official"],
                overall["official_exact_match"],
                overall["v2_exact_match"],
                overall["exact_match_delta_v2_minus_official"],
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
