#!/usr/bin/env python3
"""The single registered read of SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1.

Scoring-side only: gold opens here, once, after the seal. Zero model, GPU,
tool, embedding and network contacts.

Three output sets are scored through the SAME registered scorer
(``slurp-slu-official`` -- the real, unmodified official ``evaluate.py`` at the
pinned commit, plus this study's per-sample port and their identity check):

* the closed-list arm's own sealed ``<run_id>.outputs.jsonl`` (canonical rows,
  ``text`` key, written by ``FlightRuntime.seal``);
* the sealed 2026-08-25 DEV-1000 M0 arm, and
* the sealed 2026-08-25 DEV-1000 BLEND arm.

The two sealed August arms predate ``FlightRuntime.seal`` and carry
``final_response_text`` where every registered scorer reads ``text``, so each
is read through a 1:1 KEY-RENAME PROJECTION -- exactly the pattern the
2026-09-04 alignment audit established and recorded. No response text is
altered and no row is added or dropped; both source and projection sha256 are
recorded. The closed-list arm needs no projection at all, which is the point of
having flown it through ``FlightRuntime``.
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
from speech_aware_evidence_acquisition.data.lock import data_root, load_lock, umbrella_lock_path
from speech_aware_evidence_acquisition.data.slurp import load_slurp_ontology, load_slurp_split
from speech_aware_evidence_acquisition.reproduction.slurp_official_eval import (
    score_slurp_outputs_official,
)
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import parse_slu_response

REPO = Path(
    "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition"
)
SEED = 20260807
N_REPLICATES = 10000

SEALED = {
    "M0": "SAEA-DEV1000-BASELINE-LOCK/attempt-20260825T053342Z-dev1000m0/arm1-m0-outputs.jsonl",
    "BLEND": "SAEA-DEV1000-BASELINE-LOCK/attempt-20260825T054707Z-dev1000blend/arm2-blend-outputs.jsonl",
}
PAIRED_METRICS = ("scenario_action_exact", "scenario_exact", "action_exact", "slot_f1_exact_f1")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_rows(path: Path) -> list:
    text = Path(path).read_text(encoding="utf-8")
    return [json.loads(line) for line in text.split("\n") if line.strip()]


def project(rows: list, out: Path) -> Path:
    lines = []
    for row in rows:
        text = row.get("text")
        if text is None:
            text = row.get("final_response_text")
        if not isinstance(text, str):
            raise SystemExit("row %r carries no response text" % (row.get("sample_id"),))
        lines.append(
            json.dumps({"sample_id": row["sample_id"], "text": text}, ensure_ascii=False)
        )
    out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return out


def receipt_ids(relpath: str) -> set:
    doc = json.loads((REPO / relpath).read_text(encoding="utf-8"))
    return {item["id"] for item in doc["items"]}


def percent(count: int, total: int) -> float:
    return round(100.0 * count / total, 2) if total else 0.0


def off_inventory(rows: list, ontology) -> dict:
    allowed_pair = set()
    for scenario, actions in ontology.actions_by_scenario.items():
        for action in actions:
            allowed_pair.add((scenario, action))
    allowed_scenario = set(ontology.scenarios)
    allowed_action = set(ontology.actions)
    allowed_type = set(ontology.entity_types)

    n = len(rows)
    bad_scenario = bad_action = bad_pair = unparsed = 0
    mentions = bad_type = 0
    pairs = collections.Counter()
    for row in rows:
        text = row.get("text")
        if text is None:
            text = row.get("final_response_text")
        scenario, action, entities, parsed = parse_slu_response(text or "")
        if not parsed:
            unparsed += 1
        if scenario not in allowed_scenario:
            bad_scenario += 1
        if action not in allowed_action:
            bad_action += 1
        if (scenario, action) not in allowed_pair:
            bad_pair += 1
            pairs["%s/%s" % (scenario, action)] += 1
        for entity in entities:
            mentions += 1
            if entity.type not in allowed_type:
                bad_type += 1
    return {
        "rows": n,
        "unparsed_rows": unparsed,
        "scenario_outside_the_listed_set_percent": percent(bad_scenario, n),
        "action_outside_the_listed_set_percent": percent(bad_action, n),
        "pair_not_observed_in_train_count": bad_pair,
        "pair_not_observed_in_train_percent": percent(bad_pair, n),
        "entity_mentions": mentions,
        "entity_type_outside_the_listed_set_percent": percent(bad_type, mentions),
        "top_off_inventory_pairs": pairs.most_common(8),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm-outputs", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    lock = load_lock(umbrella_lock_path())
    root = data_root()
    ontology = load_slurp_ontology(lock, root)
    runs = Path(root) / "runs"

    sources = {"CLOSED-LIST": {"path": args.arm_outputs, "rows": read_rows(args.arm_outputs)}}
    for name, relpath in SEALED.items():
        path = runs / relpath
        sources[name] = {"path": path, "rows": read_rows(path)}

    tmpdir = Path(tempfile.mkdtemp(prefix="saea-slurp-closedlist-read-", dir=str(root)))
    projections = {}
    scored = {}
    for name, entry in sources.items():
        proj = project(entry["rows"], tmpdir / ("%s.outputs.jsonl" % name))
        projections[name] = {
            "source_path": str(entry["path"]),
            "source_sha256": sha256_file(entry["path"]),
            "projection_sha256": sha256_file(proj),
            "rows": len(entry["rows"]),
            "projection_needed": name != "CLOSED-LIST",
        }
        scored[name] = score_slurp_outputs_official(proj, lock, root, split_id="devel")

    per_sample = {}
    for name, result in scored.items():
        per_sample[name] = {row["sample_id"]: row for row in result["per_sample"]}

    gold = {}
    for record in load_slurp_split(lock, root, "devel"):
        gold[record.sample_id] = record

    ids_all = sorted(per_sample["CLOSED-LIST"])
    dev500 = sorted(receipt_ids("docs/receipts/probe-samples/DEV-500.json") & set(ids_all))
    new500 = sorted(receipt_ids("docs/receipts/probe-samples/DEV-1000-NEW500.json") & set(ids_all))

    def stratum_of(sample_id: str) -> str:
        return gold[sample_id].scenario

    def contrasts(left_name, right_name, ids, metrics=PAIRED_METRICS):
        out = {}
        results = paired_contrast(
            per_sample[left_name],
            per_sample[right_name],
            metrics=metrics,
            sample_ids=list(ids),
            strata_of=stratum_of,
            seed=SEED,
            n_replicates=N_REPLICATES,
            ci_level=0.90,
        )
        for metric, contrast in results.items():
            out[metric] = contrast.as_dict()
        return out

    document = {
        "schema": "saea-slurp-closed-list-direct-read-v1",
        "study": "speech-aware-evidence-acquisition",
        "run_id": "SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1",
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "contacts": {"model": 0, "tool": 0, "embedding": 0, "network": 0, "gpu_seconds": 0},
        "split_id": "devel",
        "allow_heldout": False,
        "bootstrap": {"seed": SEED, "n_replicates": N_REPLICATES, "ci_level": 0.90},
        "inputs": projections,
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
                "rows_in_outputs": projections[name]["rows"],
                "rows_scored": len(per_sample[name]),
                "skipped": projections[name]["rows"] - len(per_sample[name]),
                "unparsed": sum(1 for row in per_sample[name].values() if not row["parsed"]),
            }
            for name in scored
        },
        "off_inventory": {
            name: off_inventory(sources[name]["rows"], ontology) for name in sources
        },
        "paired_closed_list_over_sealed_m0": {
            "pooled_1000": contrasts("M0", "CLOSED-LIST", ids_all),
            "prior_exposed_dev500": contrasts("M0", "CLOSED-LIST", dev500),
            "unexposed_new500": contrasts("M0", "CLOSED-LIST", new500),
        },
        "paired_blend_over_closed_list": {
            "pooled_1000": contrasts(
                "CLOSED-LIST", "BLEND", ids_all, metrics=("scenario_action_exact",)
            ),
            "unexposed_new500": contrasts(
                "CLOSED-LIST", "BLEND", new500, metrics=("scenario_action_exact",)
            ),
        },
        "paired_blend_over_sealed_m0": {
            "pooled_1000": contrasts(
                "M0", "BLEND", ids_all, metrics=("scenario_action_exact",)
            ),
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
    print("arm          scenario  action   intent   SLU-F1   span-F1")
    for name in ("CLOSED-LIST", "M0", "BLEND"):
        o = scored[name]["aggregate"]["official"]
        print(
            "%-12s %8.2f %8.2f %8.2f %8.2f %8.2f"
            % (
                name,
                100 * o["scenario_accuracy"],
                100 * o["action_accuracy"],
                100 * o["intent_accuracy"],
                100 * o["slu_f1"],
                100 * o["span_f1"],
            )
        )
    print()
    for label, key in (
        ("pooled 1000", "pooled_1000"),
        ("dev500 exposed", "prior_exposed_dev500"),
        ("new500 unexposed", "unexposed_new500"),
    ):
        c = document["paired_closed_list_over_sealed_m0"][key]["scenario_action_exact"]
        b = c["bootstrap"]
        print(
            "intent CL-vs-M0 (%s): n=%d  %.2f -> %.2f  delta %+.2f pp  saves %d harms %d ties %d  p=%.3g  CI90 [%+.2f, %+.2f]"
            % (
                label,
                c["n"],
                100 * c["left_mean"],
                100 * c["right_mean"],
                100 * c["delta"],
                c["saves"],
                c["harms"],
                c["ties"],
                c["sign_test_p"],
                100 * b["ci_low"],
                100 * b["ci_high"],
            )
        )
    c = document["paired_blend_over_closed_list"]["pooled_1000"]["scenario_action_exact"]
    b = c["bootstrap"]
    print(
        "intent BLEND-vs-CL (pooled 1000): %.2f -> %.2f  delta %+.2f pp  CI90 [%+.2f, %+.2f]  p=%.3g"
        % (
            100 * c["left_mean"],
            100 * c["right_mean"],
            100 * c["delta"],
            100 * b["ci_low"],
            100 * b["ci_high"],
            c["sign_test_p"],
        )
    )
    print()
    for name in ("CLOSED-LIST", "M0", "BLEND"):
        oi = document["off_inventory"][name]
        print(
            "%-12s impossible pairs %6.2f%%  unparsed %d  unlisted scenario %.2f%%  unlisted action %.2f%%"
            % (
                name,
                oi["pair_not_observed_in_train_percent"],
                oi["unparsed_rows"],
                oi["scenario_outside_the_listed_set_percent"],
                oi["action_outside_the_listed_set_percent"],
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
