#!/usr/bin/env python3
"""The single registered read of the SLURP consumption cell KU-S1c.

Scoring-side only: gold opens here, once, after the seal. Zero model, GPU,
tool, embedding and network contacts.

Everything is scored through the SAME registered scorer
(``slurp-slu-official`` -- the real, unmodified official ``evaluate.py`` at
the pinned commit, plus this study's per-sample port and their identity
check), over complete 1,000-row roster files, never sharded.

**No projection anywhere.** Unlike the KC-S1 slot cells, whose sealed rows
carry ``{"entities": [...]}`` alone and needed a model-free join to produce a
full official table, KU-S1c's sealed row is a full SLU object -- the same
shape the closed-list comparator sealed -- so every column of its official
table comes straight from its own ``<run_id>.outputs.jsonl``.

The comparator (``SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1``) is scored here
too, from its own sealed outputs, and must reproduce its verdict's numbers
exactly; that is the read's identity anchor.

Run in WSL2::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src \\
      python scripts/slurp_ku_s1c_read.py --outputs <path> --out <path>
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from speech_aware_evidence_acquisition.analysis.paired import paired_contrast
from speech_aware_evidence_acquisition.data.lock import (
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.data.slurp import load_slurp_split
from speech_aware_evidence_acquisition.reproduction.slurp_official_eval import (
    score_slurp_outputs_official,
)
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (
    parse_slu_response,
)

REPO = Path(
    "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition"
)
SEED = 20260903
N_REPLICATES = 10000
CI_LEVEL = 0.90
CLOSED_LIST_OUTPUTS = (
    "runs/SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1/attempt-20260905T060424Z-2c5596/"
    "SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1.outputs.jsonl"
)
#: Per-sample metrics paired for every contrast. ``scenario_action_exact`` is
#: the PRIMARY here (intent, the layer the equal-contact control exists to
#: probe and the one KC-S1a held identical by construction);
#: ``slot_f1_exact_f1`` is the official script's own plain ``entities`` block
#: and ``slu_f1_f1`` the per-sample form of the SLU-F1 headline.
PAIRED_METRICS = (
    "scenario_action_exact",
    "scenario_exact",
    "action_exact",
    "slot_f1_exact_f1",
    "slu_f1_f1",
    "slu_f1_word_f1",
    "slu_f1_char_f1",
    "slot_f1_exact_precision",
    "slot_f1_exact_recall",
)
#: Every metric whose both-weightings view the verdict reports.
WEIGHTED_METRICS = ("scenario_action_exact", "slot_f1_exact_f1", "slu_f1_f1")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_rows(path: Path) -> list:
    text = Path(path).read_text(encoding="utf-8")
    return [json.loads(line) for line in text.split("\n") if line.strip()]


def text_of(row) -> str:
    text = row.get("text")
    if text is None:
        text = row.get("final_response_text")
    if not isinstance(text, str):
        raise SystemExit("row %r carries no response text" % (row.get("sample_id"),))
    return text


def project_as_sealed(rows: list, out: Path) -> Path:
    """1:1 key projection: the sealed text verbatim, under the ``text`` key
    every registered scorer reads. No text altered, no row added or dropped."""

    out.write_text(
        "\n".join(
            json.dumps(
                {"sample_id": row["sample_id"], "text": text_of(row)},
                ensure_ascii=False,
                sort_keys=True,
            )
            for row in rows
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return out


def receipt_ids(relpath: str) -> set:
    doc = json.loads((REPO / relpath).read_text(encoding="utf-8"))
    return {item["id"] for item in doc["items"]}


def percent(count: int, total: int) -> float:
    return round(100.0 * count / total, 2) if total else 0.0


def entity_mentions(rows: list) -> dict:
    mentions = 0
    empty = 0
    types = collections.Counter()
    for row in rows:
        _scenario, _action, entities, _parsed = parse_slu_response(text_of(row))
        mentions += len(entities)
        if not entities:
            empty += 1
        for entity in entities:
            types[entity.type] += 1
    return {
        "predicted_entity_mentions": mentions,
        "rows_with_no_entity": empty,
        "rows_with_no_entity_percent": percent(empty, len(rows)),
        "top_predicted_types": types.most_common(12),
    }


def answer_churn(closed_by_id, arm_by_id, ids) -> dict:
    """How often the two arms' sealed answers differ at all, as bytes and as
    (scenario, action) -- the honest measure of what the second contact did,
    independent of whether it helped."""

    byte_changes = 0
    intent_changes = 0
    for sample_id in ids:
        left, right = closed_by_id[sample_id], arm_by_id[sample_id]
        if left != right:
            byte_changes += 1
        l_scen, l_act, _le, _lp = parse_slu_response(left)
        r_scen, r_act, _re, _rp = parse_slu_response(right)
        if (l_scen, l_act) != (r_scen, r_act):
            intent_changes += 1
    return {
        "rows": len(ids),
        "byte_identical_rows": len(ids) - byte_changes,
        "byte_changed_rows": byte_changes,
        "byte_changed_percent": percent(byte_changes, len(ids)),
        "intent_changed_rows": intent_changes,
        "intent_changed_percent": percent(intent_changes, len(ids)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outputs", type=Path, required=True)
    parser.add_argument("--run-manifest", type=Path, default=None)
    parser.add_argument("--flight-receipt", type=Path, default=None)
    parser.add_argument(
        "--phases",
        type=Path,
        default=None,
        help=(
            "the sealed <run_id>.phases.json. When given, the DRAFT phase's own "
            "responses are scored as a third arm, which is what separates the two "
            "things this cell changes at once: the added CONTROL turn (closed-list "
            "vs draft, one contact each) and the added CONTACT (draft vs revise)."
        ),
    )
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    lock = load_lock(umbrella_lock_path())
    root = data_root()
    sources = {
        "CLOSED-LIST": Path(root) / CLOSED_LIST_OUTPUTS,
        "KU-S1C": args.outputs,
    }
    rows = {name: read_rows(path) for name, path in sources.items()}
    for name, entries in rows.items():
        if len(entries) != 1000:
            raise SystemExit("%s carries %d rows, expected 1000" % (name, len(entries)))

    if args.phases is not None:
        phases_doc = json.loads(Path(args.phases).read_text(encoding="utf-8"))
        draft = None
        for summary in phases_doc["phases"]:
            if str(summary["controller_policy_id"]).endswith(":draft"):
                draft = {
                    result["sample_id"]: result["final_response_text"]
                    for result in summary["results"]
                }
        if draft is None or len(draft) != 1000:
            raise SystemExit("the phases file carries no complete draft phase")
        rows["KU-S1C-DRAFT"] = [
            {"sample_id": sample_id, "text": text}
            for sample_id, text in sorted(draft.items())
        ]
        sources["KU-S1C-DRAFT"] = args.phases

    tmpdir = Path(tempfile.mkdtemp(prefix="saea-slurp-kus1c-read-", dir=str(root)))
    inputs = {}
    scored = {}
    for name, path in sources.items():
        proj = project_as_sealed(rows[name], tmpdir / ("%s.as-sealed.jsonl" % name))
        inputs[name] = {
            "source_path": str(path),
            "source_sha256": sha256_file(path),
            "as_sealed_projection_sha256": sha256_file(proj),
            "rows": len(rows[name]),
        }
        scored[name] = score_slurp_outputs_official(proj, lock, root, split_id="devel")

    per_sample = {
        name: {row["sample_id"]: row for row in result["per_sample"]}
        for name, result in scored.items()
    }

    gold = {record.sample_id: record for record in load_slurp_split(lock, root, "devel")}
    ids_all = sorted(per_sample["CLOSED-LIST"])
    if sorted(per_sample["KU-S1C"]) != ids_all:
        raise SystemExit("the two arms do not cover the same sample ids")
    dev500 = sorted(receipt_ids("docs/receipts/probe-samples/DEV-500.json") & set(ids_all))
    new500 = sorted(
        receipt_ids("docs/receipts/probe-samples/DEV-1000-NEW500.json") & set(ids_all)
    )

    def stratum_of(sample_id: str) -> str:
        return gold[sample_id].scenario

    def contrasts(left, right, ids, metrics=PAIRED_METRICS):
        results = paired_contrast(
            per_sample[left],
            per_sample[right],
            metrics=metrics,
            sample_ids=list(ids),
            strata_of=stratum_of,
            seed=SEED,
            n_replicates=N_REPLICATES,
            ci_level=CI_LEVEL,
        )
        return {metric: contrast.as_dict() for metric, contrast in results.items()}

    def weightings(name, ids, metric):
        by_stratum = collections.defaultdict(list)
        for sample_id in ids:
            by_stratum[stratum_of(sample_id)].append(
                float(per_sample[name][sample_id][metric])
            )
        natural = sum(sum(v) for v in by_stratum.values()) / max(1, len(ids))
        equal = sum(sum(v) / len(v) for v in by_stratum.values()) / max(
            1, len(by_stratum)
        )
        return {
            "natural_mixture": round(100 * natural, 2),
            "equal_stratum": round(100 * equal, 2),
        }

    def per_stratum(ids, metric):
        table = []
        by_stratum = collections.defaultdict(list)
        for sample_id in ids:
            by_stratum[stratum_of(sample_id)].append(sample_id)
        for scenario in sorted(by_stratum):
            members = by_stratum[scenario]
            row = {"scenario": scenario, "n": len(members)}
            for name in ("CLOSED-LIST", "KU-S1C"):
                row[name] = round(
                    100
                    * sum(float(per_sample[name][sid][metric]) for sid in members)
                    / len(members),
                    2,
                )
            row["delta"] = round(row["KU-S1C"] - row["CLOSED-LIST"], 2)
            row["saves"] = sum(
                1
                for sid in members
                if float(per_sample["KU-S1C"][sid][metric])
                > float(per_sample["CLOSED-LIST"][sid][metric])
            )
            row["harms"] = sum(
                1
                for sid in members
                if float(per_sample["KU-S1C"][sid][metric])
                < float(per_sample["CLOSED-LIST"][sid][metric])
            )
            table.append(row)
        return table

    text_by_arm = {
        name: {row["sample_id"]: text_of(row) for row in rows[name]}
        for name in sorted(rows)
    }

    realized: dict[str, object] = {}
    if args.run_manifest is not None:
        manifest = json.loads(Path(args.run_manifest).read_text(encoding="utf-8"))
        realized["run_manifest_sha256"] = sha256_file(args.run_manifest)
        realized["cost"] = manifest.get("cost")
        realized["study_commit"] = manifest.get("study_commit")
        realized["status"] = manifest.get("status")
    if args.flight_receipt is not None:
        receipt = json.loads(Path(args.flight_receipt).read_text(encoding="utf-8"))
        stages = receipt.get("stages") or {}
        run_phases = stages.get("run_phases") or {}
        realized["attempt_id"] = receipt.get("attempt_id")
        realized["contact_count"] = run_phases.get("contact_count")
        realized["phases"] = run_phases.get("phases")
        realized["wall_seconds"] = run_phases.get("wall_seconds")
        realized["dispatch"] = run_phases.get("dispatch")
        # Two whole-roster waves, so every row took exactly two contacts.
        phase_rows = {
            int(entry.get("rows", 0)) for entry in (run_phases.get("phases") or [])
        }
        realized["contacts_per_row"] = (
            run_phases.get("contact_count", 0) / max(phase_rows) if phase_rows else None
        )

    document = {
        "schema": "saea-slurp-ku-s1c-consumption-read-v1",
        "study": "speech-aware-evidence-acquisition",
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "cells": ["KU-S1c"],
        "contacts": {
            "model": 0,
            "tool": 0,
            "embedding": 0,
            "network": 0,
            "gpu_seconds": 0,
        },
        "split_id": "devel",
        "allow_heldout": False,
        "bootstrap": {"seed": SEED, "n_replicates": N_REPLICATES, "ci_level": CI_LEVEL},
        "inputs": inputs,
        "realized_contacts": realized or None,
        "official": {
            name: {
                "aggregate": result["aggregate"]["official"],
                "port_micro": result["aggregate"]["port_micro"],
                "identity_check": result["aggregate"]["identity_check"],
                "scorer_version": result["aggregate"]["scorer_version"],
            }
            for name, result in scored.items()
        },
        "n_predicted": {
            name: {
                "rows_in_outputs": len(rows[name]),
                "rows_scored": len(per_sample[name]),
                "skipped": len(rows[name]) - len(per_sample[name]),
                "unparsed": sum(
                    1 for row in per_sample[name].values() if not row["parsed"]
                ),
            }
            for name in sorted(rows)
        },
        "entity_supply": {
            name: entity_mentions(rows[name]) for name in sorted(rows)
        },
        "answer_churn": {
            "revise_vs_closed_list_pooled_1000": answer_churn(
                text_by_arm["CLOSED-LIST"], text_by_arm["KU-S1C"], ids_all
            ),
            "revise_vs_closed_list_new500": answer_churn(
                text_by_arm["CLOSED-LIST"], text_by_arm["KU-S1C"], new500
            ),
            "revise_vs_own_draft_pooled_1000": (
                answer_churn(
                    text_by_arm["KU-S1C-DRAFT"], text_by_arm["KU-S1C"], ids_all
                )
                if "KU-S1C-DRAFT" in text_by_arm
                else None
            ),
            "draft_vs_closed_list_pooled_1000": (
                answer_churn(
                    text_by_arm["CLOSED-LIST"], text_by_arm["KU-S1C-DRAFT"], ids_all
                )
                if "KU-S1C-DRAFT" in text_by_arm
                else None
            ),
        },
        "paired_ku_s1c_over_closed_list": {
            "pooled_1000": contrasts("CLOSED-LIST", "KU-S1C", ids_all),
            "prior_exposed_dev500": contrasts("CLOSED-LIST", "KU-S1C", dev500),
            "unexposed_new500": contrasts("CLOSED-LIST", "KU-S1C", new500),
        },
        # The decomposition: this cell changes TWO things against the
        # comparator at once -- it adds a CONTROL turn and it adds a CONTACT.
        # The draft phase's own sealed responses separate them.
        "paired_draft_over_closed_list": (
            {
                "pooled_1000": contrasts("CLOSED-LIST", "KU-S1C-DRAFT", ids_all),
                "unexposed_new500": contrasts("CLOSED-LIST", "KU-S1C-DRAFT", new500),
            }
            if "KU-S1C-DRAFT" in per_sample
            else None
        ),
        "paired_revise_over_draft": (
            {
                "pooled_1000": contrasts("KU-S1C-DRAFT", "KU-S1C", ids_all),
                "unexposed_new500": contrasts("KU-S1C-DRAFT", "KU-S1C", new500),
            }
            if "KU-S1C-DRAFT" in per_sample
            else None
        ),
        "weightings": {
            metric: {
                name: {
                    "pooled_1000": weightings(name, ids_all, metric),
                    "unexposed_new500": weightings(name, new500, metric),
                }
                for name in sources
            }
            for metric in WEIGHTED_METRICS
        },
        "per_stratum": {
            "intent_pooled_1000": per_stratum(ids_all, "scenario_action_exact"),
            "intent_unexposed_new500": per_stratum(new500, "scenario_action_exact"),
            "slot_f1_pooled_1000": per_stratum(ids_all, "slot_f1_exact_f1"),
        },
        "populations": {
            "pooled": len(ids_all),
            "prior_exposed_dev500": len(dev500),
            "unexposed_new500": len(new500),
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(document, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print("wrote", args.out, sha256_file(args.out))

    print()
    print("arm           scenario  action   intent   SLU-F1  span-F1")
    for name in ("CLOSED-LIST", "KU-S1C"):
        agg = scored[name]["aggregate"]["official"]
        print(
            "%-13s %7.2f %7.2f %8.2f %7.2f %8.2f"
            % (
                name,
                100 * agg["scenario_accuracy"],
                100 * agg["action_accuracy"],
                100 * agg["intent_accuracy"],
                100 * agg["slu_f1"],
                100 * agg["span_f1"],
            )
        )
    print()
    for population in ("unexposed_new500", "pooled_1000"):
        block = document["paired_ku_s1c_over_closed_list"][population]
        print(population)
        for metric in ("scenario_action_exact", "slot_f1_exact_f1", "slu_f1_f1"):
            entry = block[metric]
            boot = entry["bootstrap"] or {}
            print(
                "  %-26s delta %+7.2f  CI90 [%+.2f, %+.2f]  saves %d harms %d p %.3g"
                % (
                    metric,
                    100 * entry["delta"],
                    100 * boot.get("ci_low", float("nan")),
                    100 * boot.get("ci_high", float("nan")),
                    entry["saves"],
                    entry["harms"],
                    entry["sign_test_p"],
                )
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
